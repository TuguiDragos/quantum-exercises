"""All terminal rendering. Nothing here computes a verdict, it only shows one.

The one exception is `save_progress`, which lives here because saving and saying
what happened when it fails are the same act, and both `qx run` and `qx watch`
need it. Putting it in state.py would mean state.py importing this module, and
this module already imports state.
"""

from __future__ import annotations

import math
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from quantum_exercises import invocation, theme
from quantum_exercises.registry import Exercise
from quantum_exercises.runner import RunResult
from quantum_exercises.state import STATE_FILENAME, State, save, state_path

# highlight=False: rich otherwise recolours numbers, strings and paths with its
# own default theme, laying colours over the palette that nothing here chose.
# The theme override replaces rich's built-in markdown and table styles, which
# are written in named colours and would otherwise surface through `qx hint`.
console = Console(highlight=False, theme=Theme(theme.RICH_OVERRIDES))

# Square everywhere. A filled cell is painted corner to corner, so a rounded
# glyph drawn over it leaves the cell's outer corner coloured outside the curve.
TABLE_BOX = box.SQUARE

BAR_WIDTH = 34

# Eight-step block ramp, so a bar can render fractions of a cell.
_BLOCKS = " ▏▎▍▌▋▊▉█"
_FULL = "█"
_TRACK = "░"

# Plain replacements for terminals whose encoding cannot carry the blocks above,
# which is still the default on some Windows consoles.
_ASCII_BLOCKS = "        #"
_ASCII_FULL = "#"
_ASCII_TRACK = "."

STATUS_STYLE = {
    "todo": ("todo", theme.STATUS_TODO),
    "done": ("done", theme.STATUS_DONE),
    "solved": ("solved", theme.STATUS_SOLVED),
}


def _supports_blocks() -> bool:
    """Can the current output encoding actually carry the block characters?

    Checked per call rather than at import: the stream is swapped out under tests
    and when output is piped.
    """
    encoding = getattr(console.file, "encoding", None)
    if not encoding:
        return True  # no encoding to fail against, for example an in-memory buffer
    try:
        (_BLOCKS + _TRACK).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _effective_track(track: str) -> str:
    """The track character actually drawn, after the ASCII fallback.

    Lives here rather than inside _bar so that _bar_text strips the same character
    _bar drew. When they disagreed, nothing was stripped and the empty half of the
    bar was painted in the fill colour.
    """
    if track == _TRACK and not _supports_blocks():
        return _ASCII_TRACK
    return track


def _bar(fraction: float, width: int = BAR_WIDTH, track: str = " ") -> str:
    """Render a proportion as a bar with sub-character resolution where possible."""
    fraction = max(0.0, min(1.0, fraction))
    unicode_ok = _supports_blocks()
    ramp = _BLOCKS if unicode_ok else _ASCII_BLOCKS
    full = _FULL if unicode_ok else _ASCII_FULL
    track = _effective_track(track)

    exact = fraction * width
    filled_cells = int(exact)
    remainder = exact - filled_cells

    # Any partial cell that is blank must add nothing, or it punches a hole
    # between the filled part and the track. That is ramp[0] in both ramps, and
    # ramp[1..7] in the ASCII one, which has no sub-character glyphs to offer.
    step = round(remainder * 8)
    partial = ramp[step] if step > 0 and filled_cells < width else ""
    if not partial.strip():
        partial = ""

    filled = full * filled_cells + partial
    return filled + track * (width - len(filled))


def panel(*, border: str = theme.BORDER_ACTIVE, heavy: bool = False, raised: bool = False) -> dict:
    """Panel styling in one place, so no call site names a colour or a box."""
    return {
        "border_style": border,
        "style": theme.RAISED if raised else theme.PANEL,
        # Square, not rounded: a filled cell is painted corner to corner, and a
        # rounded glyph drawn over it leaves the cell's outer corner coloured
        # outside the curve, which reads as a notch. Square geometry matches the
        # fill exactly. Rounded looks right only on an unfilled panel.
        "box": box.HEAVY if heavy else box.SQUARE,
        "expand": False,
    }


def _display_path(path: Path) -> str:
    """The shortest way to name a file the reader has to go and open.

    Relative to the working directory when that is shorter, absolute otherwise.
    `qx` is usually installed globally and run from anywhere, so a bare filename
    tells the learner nothing about where the file actually is.
    """
    absolute = path.resolve()
    try:
        relative = absolute.relative_to(Path.cwd())
    except ValueError:
        return str(absolute)
    return str(relative) if len(str(relative)) < len(str(absolute)) else str(absolute)


def _bar_text(fraction: float, width: int = BAR_WIDTH, *, track: str = " ") -> Text:
    """A bar as two spans, so the track keeps its own colour instead of the fill's."""
    rendered = _bar(fraction, width, track)
    used = _effective_track(track)
    filled = len(rendered.rstrip(used)) if used.strip() else len(rendered.rstrip(" "))
    return Text(rendered[:filled], style=theme.BAR) + Text(rendered[filled:], style=theme.BAR_TRACK)


def _safe(text: str) -> str:
    """Replace characters the output stream cannot encode, rather than crashing.

    Qiskit circuit drawings are box-drawing art. Printing one to a console on a
    legacy code page raises UnicodeEncodeError from deep inside rich, which would
    take down a run that had already succeeded.
    """
    encoding = getattr(console.file, "encoding", None)
    if not encoding:
        return text
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    return text


def _fmt_complex(re: float, im: float, places: int = 3) -> str:
    """Format a complex number, collapsing values that are zero to display precision."""
    tol = 0.5 * 10 ** (-places)
    if abs(re) < tol and abs(im) < tol:
        return "0"
    if abs(im) < tol:
        return f"{re:.{places}f}"
    if abs(re) < tol:
        return f"{im:.{places}f}i"
    sign = "+" if im >= 0 else "-"
    return f"{re:.{places}f}{sign}{abs(im):.{places}f}i"


# --------------------------------------------------------------------------
# Artifacts
# --------------------------------------------------------------------------


def render_counts(payload: dict[str, int], caption: str) -> Panel:
    total = sum(payload.values()) or 1
    # Floor of 1: a dict whose counts are all zero made peak 0 and the bar below
    # divided by it. No shipped exercise reaches that, because the count assertions
    # fail first, but this helper takes whatever an exercise author passes it.
    peak = max(1, max(payload.values(), default=1))
    body = Text()
    for outcome in sorted(payload):
        count = payload[outcome]
        share = count / total
        body.append(f"{outcome:>8} ", style=theme.FIGURE)
        body.append_text(_bar_text(count / peak))
        body.append(f" {count:>6}  {share * 100:5.1f}%\n")
    body.append(f"\n{'total':>8}   {total} shots", style=theme.DETAIL)
    return Panel(body, title=caption, **panel(raised=True))


def render_statevector(payload: list[list[float]], caption: str, num_qubits: int) -> Panel:
    table = Table(show_header=True, header_style=theme.HEADING, box=None, pad_edge=False)
    table.add_column("basis", style=theme.FIGURE)
    table.add_column("amplitude", justify="right")
    table.add_column("probability", justify="right")

    for index, (re, im) in enumerate(payload):
        probability = re * re + im * im
        # Little-endian: qubit 0 is the rightmost character of the label.
        label = f"|{index:0{num_qubits}b}>"
        style = theme.DETAIL if probability < 1e-12 else theme.BODY
        table.add_row(label, _fmt_complex(re, im), f"{probability:.4f}", style=style)

    return Panel(table, title=caption, **panel(raised=True))


def render_matrix(payload: list[list[list[float]]], caption: str) -> Panel:
    table = Table(show_header=False, box=None, pad_edge=False)
    for _ in range(len(payload[0]) if payload else 0):
        table.add_column(justify="right")
    for row in payload:
        table.add_row(*[_fmt_complex(re, im) for re, im in row])
    return Panel(table, title=caption, **panel(raised=True))


def render_artifact(artifact: dict):
    kind = artifact.get("kind")
    caption = artifact.get("caption") or ""
    payload = artifact.get("payload")
    meta = artifact.get("meta") or {}

    caption = _safe(caption)
    if kind == "counts" and isinstance(payload, dict):
        return render_counts(payload, caption)
    if kind == "statevector" and isinstance(payload, list):
        num_qubits = int(meta.get("num_qubits") or max(1, int(math.log2(max(len(payload), 1)))))
        return render_statevector(payload, caption, num_qubits)
    if kind == "matrix" and isinstance(payload, list):
        return render_matrix(payload, caption)
    return Panel(Text(_safe(str(payload))), title=caption, **panel(raised=True))


# --------------------------------------------------------------------------
# Run output
# --------------------------------------------------------------------------


def render_run(exercise: Exercise, result: RunResult, *, root: Path) -> None:
    console.print()
    console.print(
        Rule(_safe(f"{exercise.number:02d} {exercise.title}"), style=theme.ACCENT, align="left")
    )

    if result.stdout.strip():
        console.print(
            Panel(
                Text(_safe(result.stdout.rstrip()), style=theme.BODY),
                title="output from your program",
                **panel(border=theme.BORDER_QUIET),
            )
        )

    for warning in result.warnings:
        console.print(Text(_safe(f"warning  {warning}"), style=theme.DETAIL))

    if result.passed:
        for artifact in result.artifacts:
            # Some artifacts carry only metadata, such as which backend a run
            # used. With no caption and no payload they would draw an empty box.
            if not artifact.get("caption") and not artifact.get("payload"):
                continue
            console.print(render_artifact(artifact))
        console.print(Text(f"\n  PASS  {exercise.slug}", style=theme.STATUS_DONE))
        console.print(Text(f"        finished in {result.duration:.2f}s\n", style=theme.DETAIL))
        return

    _render_failure(exercise, result, root=root)


def _render_failure(exercise: Exercise, result: RunResult, *, root: Path) -> None:
    headings = {
        "fail": "NOT YET",
        "error": "ERROR",
        "timeout": "TIMED OUT",
        "crash": "STOPPED",
        "internal_error": "RUNNER PROBLEM",
    }
    heading = headings.get(result.outcome, "FAILED")

    parts: list = [Text(_safe(result.message), style=theme.STRONG)]

    if result.line is not None:
        try:
            where = exercise.exercise_file.relative_to(root)
        except ValueError:
            where = exercise.exercise_file
        parts.append(Text(f"\nat {where}:{result.line}", style=theme.PATH))

    if result.detail:
        parts.append(Text(_safe("\n" + result.detail), style=theme.DETAIL))

    if result.hint:
        parts.append(
            Text("\nfix  ", style=theme.HEADING) + Text(_safe(result.hint), style=theme.BODY)
        )

    console.print(
        Panel(
            Group(*parts),
            title=heading,
            # "not yet" is an inactive outline; anything louder gets the accent
            # and a heavier rule, since the palette carries no error hue.
            **panel(
                border=theme.BORDER if result.outcome == "fail" else theme.BORDER_ACTIVE,
                heavy=result.outcome != "fail",
            ),
        )
    )

    if result.stderr.strip() and result.outcome in ("crash", "internal_error"):
        console.print(
            Panel(
                Text(_safe(result.stderr.rstrip()), style=theme.BODY),
                title="stderr",
                **panel(border=theme.BORDER_QUIET),
            )
        )

    console.print(
        Text("\n  next  ", style=theme.DETAIL)
        + Text(f"{invocation()} hint {exercise.number}", style=theme.COMMAND)
        + Text(" for a nudge, or open", style=theme.DETAIL)
    )
    # On its own line, and soft_wrap so it survives whole. no_wrap with crop=False
    # is not enough: rich still measures against the console width and cuts there,
    # which silently hands the reader a path that does not exist. soft_wrap also
    # sets overflow to ignore, which is the part that actually keeps every character.
    console.print(
        Text(f"        {_display_path(exercise.exercise_file)}", style=theme.PATH),
        soft_wrap=True,
    )
    console.print(
        Text("        then run ", style=theme.DETAIL)
        + Text(f"{invocation()} run", style=theme.COMMAND)
        + "\n"
    )


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------


# Fixed widths so the per-act tables line up with each other. Repeating the act
# name on every row would cost this much space and squeeze the titles instead.
# The exercise column is exactly the longest slug, and the title column the
# longest title, so nothing wraps in a standard 80-column terminal.
LIST_COLUMNS = (("#", 2), ("exercise", 20), ("title", 36), ("status", 14))

# Compact forms of backends.Kind, so the status column stays narrow.
RAN_ON_LABEL = {"hardware": "QPU", "noisy_simulator": "noisy", "simulator": "sim"}


def _act_table() -> Table:
    table = Table(header_style=theme.HEADING, box=None, pad_edge=False, expand=False)
    table.add_column(
        LIST_COLUMNS[0][0], width=LIST_COLUMNS[0][1], justify="right", style=theme.DETAIL
    )
    table.add_column(LIST_COLUMNS[1][0], width=LIST_COLUMNS[1][1], style=theme.FIGURE)
    table.add_column(LIST_COLUMNS[2][0], width=LIST_COLUMNS[2][1])
    table.add_column(LIST_COLUMNS[3][0], width=LIST_COLUMNS[3][1])
    return table


def _by_act(exercises: list[Exercise]) -> list[tuple[str, list[Exercise]]]:
    """Group consecutive exercises by act, keeping the curriculum order."""
    groups: list[tuple[str, list[Exercise]]] = []
    for exercise in exercises:
        if not groups or groups[-1][0] != exercise.act:
            groups.append((exercise.act, []))
        groups[-1][1].append(exercise)
    return groups


def render_list(exercises: list[Exercise], state: State) -> None:
    console.print()
    console.print(Text("  quantum-exercises", style=theme.TITLE))

    for act, group in _by_act(exercises):
        console.print(Text(f"\n  {act}", style=theme.HEADING))
        table = _act_table()
        for exercise in group:
            entry = state.get(exercise.slug)
            label, style = STATUS_STYLE.get(entry.status, ("todo", theme.STATUS_TODO))
            if entry.status == "done" and entry.ran_on:
                label = f"done ({RAN_ON_LABEL.get(entry.ran_on, entry.ran_on)})"
            table.add_row(
                f"{exercise.number:02d}",
                exercise.slug,
                exercise.title,
                Text(label, style=style),
            )
        console.print(table)

    done = sum(1 for e in exercises if state.is_complete(e.slug))
    total = len(exercises)
    console.print(
        Text("\n  progress  ", style=theme.DETAIL)
        + _bar_text(done / total if total else 0.0, width=28, track=_TRACK)
        + Text(f"  {done}/{total}\n", style=theme.STRONG)
    )


def render_next(exercise: Exercise) -> None:
    console.print()
    console.print(
        Panel(
            Text(exercise.summary, style=theme.BODY),
            title=f"{exercise.number:02d} {exercise.title}",
            **panel(border=theme.BORDER_ACTIVE),
        )
    )
    # Outside the panel and soft-wrapped: a path with a box border through the middle
    # of it cannot be copied, and one cut off at the terminal width is worse still,
    # because nothing on screen says it was cut.
    console.print(
        Text("\n  open  ", style=theme.DETAIL)
        + Text(_display_path(exercise.exercise_file), style=theme.PATH),
        soft_wrap=True,
    )
    console.print(
        Text("  then  ", style=theme.DETAIL)
        + Text(f"{invocation()} run {exercise.number}", style=theme.COMMAND)
        + "\n"
    )


def save_progress(root: Path, state: State) -> bool:
    """Write progress, or say plainly why it could not be written.

    A read-only clone, a full disk or a directory owned by someone else must not
    turn a finished exercise into a traceback: the work happened, only the
    bookkeeping failed, and the two deserve different words.

    Returns whether the write landed, so a caller that is about to claim something
    was recorded can soften the claim instead.
    """
    try:
        preserved = save(root, state)
    except OSError as exc:
        warn(f"Progress was not saved to {state_path(root)}: {exc.strerror or exc}.")
        return False
    if preserved is not None:
        warn(
            f"The previous {STATE_FILENAME} was written by a different version of qx and "
            f"could not be read. It was copied to {preserved.name} before being replaced."
        )
    return True


def success(message: str) -> None:
    console.print(Text(f"  {message}", style=theme.STATUS_DONE))


def info(message: str) -> None:
    console.print(Text(f"  {message}", style=theme.DETAIL))


def warn(message: str) -> None:
    console.print(Text(f"  {message}", style=theme.DETAIL))


def error(message: str) -> None:
    console.print(Text(f"  {message}", style=theme.CHECK_FAIL))


__all__ = [
    "TABLE_BOX",
    "console",
    "panel",
    "error",
    "info",
    "render_artifact",
    "render_counts",
    "render_list",
    "render_matrix",
    "render_next",
    "render_run",
    "render_statevector",
    "save_progress",
    "success",
    "warn",
]
