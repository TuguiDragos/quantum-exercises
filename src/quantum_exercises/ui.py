"""All terminal rendering. Nothing here computes a verdict, it only shows one."""

from __future__ import annotations

import math
import re as _re
from pathlib import Path

from rich import box
from rich.console import Console, Group
from rich.markdown import CodeBlock, Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from quantum_exercises import invocation, theme
from quantum_exercises.registry import Exercise
from quantum_exercises.runner import RunResult
from quantum_exercises.state import STATE_FILENAME, State, save, state_path

# highlight=False stops rich from coloring numbers, strings and paths itself.
console = Console(highlight=False, theme=Theme(theme.RICH_OVERRIDES))

_FEW_COLORS = {"256", "standard", "windows"}


def _few_colors() -> bool:
    return console.color_system in _FEW_COLORS


def _surface(style: str) -> str:
    return theme.for_256_colors(style) if _few_colors() else style


def fit_theme(target: Console) -> None:
    """Give a console with few colors the greys its dark surfaces round to cleanly."""
    if target.color_system in _FEW_COLORS:
        overrides = {name: theme.for_256_colors(s) for name, s in theme.RICH_OVERRIDES.items()}
        target.push_theme(Theme(overrides))


fit_theme(console)


def syntax_theme():
    return theme.SYNTAX_THEME_256 if _few_colors() else theme.SYNTAX_THEME


# Rounded corners leave a visible notch on a filled background.
TABLE_BOX = box.SQUARE

BAR_WIDTH = 34

# Whole cells only: fonts draw partial blocks (U+258x) at a different height.
_FULL = "█"
_TRACK = "░"

# For consoles that cannot encode the blocks, e.g. some Windows code pages.
_ASCII_FULL = "#"
_ASCII_TRACK = "."

STATUS_STYLE = {
    "todo": ("todo", theme.STATUS_TODO),
    "done": ("done", theme.STATUS_DONE),
    "solved": ("solved", theme.STATUS_SOLVED),
}


def _supports_blocks() -> bool:
    """Whether the output encoding can carry the bar characters. Checked per call."""
    encoding = getattr(console.file, "encoding", None)
    if not encoding:
        return True  # e.g. an in-memory buffer
    try:
        (_FULL + _TRACK).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _effective_track(track: str) -> str:
    """The track character actually drawn, shared by _bar and _bar_text."""
    if track == _TRACK and not _supports_blocks():
        return _ASCII_TRACK
    return track


def _bar(fraction: float, width: int = BAR_WIDTH, track: str = " ") -> str:
    """Render a proportion as a bar of whole cells."""
    fraction = max(0.0, min(1.0, fraction))
    full = _FULL if _supports_blocks() else _ASCII_FULL
    track = _effective_track(track)

    # Rounded down, so the bar never fills before the work does.
    filled_cells = int(fraction * width)
    return full * filled_cells + track * (width - filled_cells)


def panel(*, border: str = theme.BORDER_ACTIVE, heavy: bool = False, raised: bool = False) -> dict:
    """Panel styling in one place, so no call site names a color or a box."""
    return {
        "border_style": border,
        "style": _surface(theme.RAISED if raised else theme.PANEL),
        # Square, not rounded: rounded corners notch a filled background.
        "box": box.HEAVY if heavy else box.SQUARE,
        "expand": False,
    }


def _display_path(path: Path) -> str:
    """The path relative to the working directory when shorter, absolute otherwise."""
    absolute = path.resolve()
    try:
        relative = absolute.relative_to(Path.cwd())
    except ValueError:
        return str(absolute)
    return str(relative) if len(str(relative)) < len(str(absolute)) else str(absolute)


def _bar_text(fraction: float, width: int = BAR_WIDTH, *, track: str = " ") -> Text:
    """A bar as two spans, so the track keeps its own color instead of the fill's."""
    rendered = _bar(fraction, width, track)
    used = _effective_track(track)
    filled = len(rendered.rstrip(used)) if used.strip() else len(rendered.rstrip(" "))
    return Text(rendered[:filled], style=theme.BAR) + Text(rendered[filled:], style=theme.BAR_TRACK)


def _safe(text: str) -> str:
    """Replace characters the output stream cannot encode, e.g. circuit box art."""
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
    # Floor of 1 avoids dividing by zero when every count is zero.
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
    # A malformed payload falls back to text instead of crashing a passed run.
    try:
        if kind == "counts" and isinstance(payload, dict):
            return render_counts(payload, caption)
        if kind == "statevector" and isinstance(payload, list):
            num_qubits = int(meta.get("num_qubits") or max(1, int(math.log2(max(len(payload), 1)))))
            return render_statevector(payload, caption, num_qubits)
        if kind == "matrix" and isinstance(payload, list):
            return render_matrix(payload, caption)
    except (TypeError, ValueError):
        pass
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
            # Metadata-only artifacts (e.g. ran_on) would draw an empty box.
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

    parts: list = [prose(result.message, theme.STRONG)]

    if result.line is not None:
        try:
            where = exercise.exercise_file.relative_to(root)
        except ValueError:
            where = exercise.exercise_file
        parts.append(Text(f"\nat {where}:{result.line}", style=theme.PATH))

    if result.detail:
        parts.append(prose("\n" + result.detail, theme.DETAIL))

    if result.hint:
        parts.append(Text("\nfix  ", style=theme.HEADING) + prose(result.hint, theme.BODY))

    console.print(
        Panel(
            Group(*parts),
            title=heading,
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
    # soft_wrap, not no_wrap: only soft_wrap keeps rich from cropping the path.
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


# Fixed widths so the per-act tables line up and fit 80 columns.
LIST_COLUMNS = (("#", 2), ("exercise", 20), ("title", 36), ("status", 14))

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
    # Paths go outside the panel and unwrapped so they can be copied whole.
    console.print(
        Text("\n  read  ", style=theme.DETAIL)
        + Text(_display_path(exercise.readme_file), style=theme.PATH),
        soft_wrap=True,
    )
    console.print(
        Text("  edit  ", style=theme.DETAIL)
        + Text(_display_path(exercise.exercise_file), style=theme.PATH),
        soft_wrap=True,
    )
    console.print(
        Text("  then  ", style=theme.DETAIL)
        + Text(f"{invocation()} run {exercise.number}", style=theme.COMMAND)
        + "\n"
    )


def save_progress(root: Path, state: State) -> bool:
    """Write progress, or warn instead of raising. Returns whether the write landed."""
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


_INLINE_CODE = _re.compile(r"`([^`\n]+)`")


def prose(message: str, style: str) -> Text:
    """Text whose `backticked` spans are drawn as code, or as a command when they are one."""
    text = Text(style=style)
    for index, part in enumerate(_INLINE_CODE.split(_safe(message))):
        if index % 2 == 0:
            text.append(part)
        elif part == invocation() or part.startswith((f"{invocation()} ", "qx ", "uv ", "git ")):
            text.append(part, style=theme.COMMAND)
        else:
            text.append(part, style=_surface(theme.CODE))
    return text


def indented(renderable) -> Padding:
    """Two columns in, wrapped lines included."""
    return Padding(renderable, (0, 0, 0, 2), expand=False)


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class _CodeBlock(CodeBlock):
    # rich pads code blocks with a blank row above and below, on top of the
    # paragraph gap, which doubles the space around every snippet in a hint.
    def __rich_console__(self, console, options):
        code = str(self.text).rstrip()
        yield Syntax(code, self.lexer_name, theme=self.theme, word_wrap=True, padding=(0, 1))


class _Markdown(Markdown):
    elements = {**Markdown.elements, "fence": _CodeBlock, "code_block": _CodeBlock}


def markdown(text: str) -> Markdown:
    return _Markdown(text, code_theme=syntax_theme())


def success(message: str) -> None:
    console.print(indented(prose(message, theme.STATUS_DONE)))


def info(message: str) -> None:
    console.print(indented(prose(message, theme.DETAIL)))


def warn(message: str) -> None:
    console.print(indented(prose(message, theme.DETAIL)))


def error(message: str) -> None:
    console.print(indented(prose(message, theme.CHECK_FAIL)))


__all__ = [
    "TABLE_BOX",
    "console",
    "panel",
    "error",
    "indented",
    "info",
    "markdown",
    "plural",
    "prose",
    "render_artifact",
    "render_counts",
    "render_list",
    "render_matrix",
    "render_next",
    "render_run",
    "render_statevector",
    "fit_theme",
    "save_progress",
    "syntax_theme",
    "success",
    "warn",
]
