"""All terminal rendering. Nothing here computes a verdict, it only shows one."""

from __future__ import annotations

import math
from pathlib import Path

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from quantum_exercises.registry import Exercise
from quantum_exercises.runner import RunResult
from quantum_exercises.state import State

console = Console()

BAR_WIDTH = 34
# Eight-step block ramp, so a bar can render fractions of a cell.
_BLOCKS = " ▏▎▍▌▋▊▉█"

STATUS_STYLE = {
    "todo": ("todo", "dim"),
    "done": ("done", "bold green"),
    "solved": ("solved", "yellow"),
}


def _bar(fraction: float, width: int = BAR_WIDTH, track: str = " ") -> str:
    """Render a proportion as a block bar with sub-character resolution."""
    fraction = max(0.0, min(1.0, fraction))
    exact = fraction * width
    full = int(exact)
    remainder = exact - full
    partial = _BLOCKS[round(remainder * 8)] if full < width else ""
    filled = "█" * full + partial
    return filled + track * (width - len(filled))


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
    peak = max(payload.values()) if payload else 1
    body = Text()
    for outcome in sorted(payload):
        count = payload[outcome]
        share = count / total
        body.append(f"{outcome:>8} ", style="bold cyan")
        body.append(_bar(count / peak), style="green")
        body.append(f" {count:>6}  {share * 100:5.1f}%\n")
    body.append(f"\n{'total':>8}   {total} shots", style="dim")
    return Panel(body, title=caption, border_style="cyan", expand=False)


def render_statevector(payload: list[list[float]], caption: str, num_qubits: int) -> Panel:
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("basis", style="cyan")
    table.add_column("amplitude", justify="right")
    table.add_column("probability", justify="right")

    for index, (re, im) in enumerate(payload):
        probability = re * re + im * im
        # Little-endian: qubit 0 is the rightmost character of the label.
        label = f"|{index:0{num_qubits}b}>"
        style = "dim" if probability < 1e-12 else ""
        table.add_row(label, _fmt_complex(re, im), f"{probability:.4f}", style=style)

    return Panel(table, title=caption, border_style="cyan", expand=False)


def render_matrix(payload: list[list[list[float]]], caption: str) -> Panel:
    table = Table(show_header=False, box=None, pad_edge=False)
    for _ in range(len(payload[0]) if payload else 0):
        table.add_column(justify="right")
    for row in payload:
        table.add_row(*[_fmt_complex(re, im) for re, im in row])
    return Panel(table, title=caption, border_style="cyan", expand=False)


def render_artifact(artifact: dict):
    kind = artifact.get("kind")
    caption = artifact.get("caption") or ""
    payload = artifact.get("payload")
    meta = artifact.get("meta") or {}

    if kind == "counts" and isinstance(payload, dict):
        return render_counts(payload, caption)
    if kind == "statevector" and isinstance(payload, list):
        num_qubits = int(meta.get("num_qubits") or max(1, int(math.log2(max(len(payload), 1)))))
        return render_statevector(payload, caption, num_qubits)
    if kind == "matrix" and isinstance(payload, list):
        return render_matrix(payload, caption)
    return Panel(Text(str(payload)), title=caption, border_style="cyan", expand=False)


# --------------------------------------------------------------------------
# Run output
# --------------------------------------------------------------------------


def render_run(exercise: Exercise, result: RunResult, *, root: Path) -> None:
    console.print()
    console.print(
        Rule(f"[bold]{exercise.number:02d} {exercise.title}[/bold]", style="blue", align="left")
    )

    if result.stdout.strip():
        console.print(
            Panel(
                Text(result.stdout.rstrip()),
                title="output from your program",
                border_style="dim",
                expand=False,
            )
        )

    for warning in result.warnings:
        console.print(Text(f"warning  {warning}", style="yellow"))

    if result.passed:
        for artifact in result.artifacts:
            console.print(render_artifact(artifact))
        console.print(Text(f"\n  PASS  {exercise.slug}", style="bold green"))
        console.print(Text(f"        finished in {result.duration:.2f}s\n", style="dim"))
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

    parts: list = [Text(result.message, style="bold")]

    if result.line is not None:
        try:
            where = exercise.exercise_file.relative_to(root)
        except ValueError:
            where = exercise.exercise_file
        parts.append(Text(f"\nat {where}:{result.line}", style="cyan"))

    if result.detail:
        parts.append(Text("\n" + result.detail, style="dim"))

    if result.hint:
        parts.append(Text("\nfix  ", style="bold yellow") + Text(result.hint))

    console.print(
        Panel(
            Group(*parts),
            title=heading,
            border_style="red" if result.outcome != "fail" else "yellow",
            expand=False,
        )
    )

    if result.stderr.strip() and result.outcome in ("crash", "internal_error"):
        console.print(
            Panel(Text(result.stderr.rstrip()), title="stderr", border_style="dim", expand=False)
        )

    console.print(
        Text("\n  next  ", style="dim")
        + Text(f"qx hint {exercise.number}", style="bold")
        + Text(" for a nudge, or edit ", style="dim")
        + Text(str(exercise.exercise_file.name), style="cyan")
        + Text(" and run again\n", style="dim")
    )


# --------------------------------------------------------------------------
# Progress
# --------------------------------------------------------------------------


def render_list(exercises: list[Exercise], state: State) -> None:
    table = Table(title="quantum-exercises", title_style="bold", header_style="bold")
    table.add_column("#", justify="right", style="dim")
    table.add_column("exercise", style="cyan")
    table.add_column("title")
    table.add_column("status")
    table.add_column("act", style="dim")

    current_act: str | None = None
    for exercise in exercises:
        if exercise.act != current_act:
            table.add_section()
            current_act = exercise.act
        entry = state.get(exercise.slug)
        label, style = STATUS_STYLE.get(entry.status, ("todo", "dim"))
        if entry.status == "done" and entry.ran_on:
            label = f"done ({entry.ran_on})"
        table.add_row(
            f"{exercise.number:02d}",
            exercise.slug,
            exercise.title,
            Text(label, style=style),
            exercise.act,
        )

    console.print()
    console.print(table)

    done = sum(1 for e in exercises if state.is_complete(e.slug))
    total = len(exercises)
    bar = _bar(done / total if total else 0.0, width=28, track="░")
    console.print(
        Text("\n  progress  ", style="dim")
        + Text(bar, style="green")
        + Text(f"  {done}/{total}\n", style="bold")
    )


def render_next(exercise: Exercise) -> None:
    body = Text()
    body.append(exercise.summary + "\n\n")
    body.append("file  ", style="dim")
    body.append(f"{exercise.exercise_file}\n", style="cyan")
    body.append("run   ", style="dim")
    body.append(f"uv run qx run {exercise.number}", style="bold")
    console.print()
    console.print(
        Panel(
            body, title=f"{exercise.number:02d} {exercise.title}", border_style="blue", expand=False
        )
    )
    console.print()


def success(message: str) -> None:
    console.print(Text(f"  {message}", style="bold green"))


def info(message: str) -> None:
    console.print(Text(f"  {message}", style="dim"))


def warn(message: str) -> None:
    console.print(Text(f"  {message}", style="yellow"))


def error(message: str) -> None:
    console.print(Text(f"  {message}", style="bold red"))


__all__ = [
    "console",
    "error",
    "info",
    "render_artifact",
    "render_counts",
    "render_list",
    "render_matrix",
    "render_next",
    "render_run",
    "render_statevector",
    "success",
    "warn",
]
