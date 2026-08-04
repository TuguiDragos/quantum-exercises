"""The `qx` command."""

from __future__ import annotations

import os
import shutil
import warnings
from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from quantum_exercises import __version__, theme, ui
from quantum_exercises.registry import (
    Exercise,
    RegistryError,
    find_project_root,
    load_exercises,
    load_hints,
    resolve,
)
from quantum_exercises.runner import ran_on as run_result_ran_on
from quantum_exercises.runner import run_exercise
from quantum_exercises.state import State, load, save

app = typer.Typer(
    name="qx",
    help="Hands-on Qiskit exercises, from an empty laptop to real IBM hardware.",
    no_args_is_help=True,
    add_completion=False,
)

STATUS_ICON = {
    "ok": ("ok  ", theme.CHECK_OK),
    "warn": ("warn", theme.CHECK_WARN),
    "fail": ("fail", theme.CHECK_FAIL),
}


def _context() -> tuple[Path, list[Exercise], State]:
    """Resolve the repo root, the exercise list, and saved progress, or exit cleanly."""
    try:
        root = find_project_root()
        exercises = load_exercises(root)
    except RegistryError as exc:
        ui.error(str(exc))
        raise typer.Exit(code=2) from exc
    return root, exercises, load(root)


def _pick(name: str | None, exercises: list[Exercise], state: State) -> Exercise:
    """Named exercise, or the first one still outstanding."""
    if name is not None:
        try:
            return resolve(name, exercises)
        except RegistryError as exc:
            ui.error(str(exc))
            raise typer.Exit(code=2) from exc

    for exercise in exercises:
        if not state.is_complete(exercise.slug):
            return exercise

    ui.success(
        "Every exercise is complete. Run `qx list` to review, or `qx reset <name>` to redo one."
    )
    raise typer.Exit(code=0)


@app.command()
def doctor(
    online: Annotated[
        bool, typer.Option("--online", help="Also contact IBM Quantum to list available QPUs.")
    ] = False,
    save_account: Annotated[
        bool, typer.Option("--save-account", help="Save an IBM Quantum API key to ~/.qiskit.")
    ] = False,
) -> None:
    """Check that the environment is ready, step by step."""
    from quantum_exercises.doctor import run_checks

    if save_account:
        _save_account()
        return

    try:
        root: Path | None = find_project_root()
    except RegistryError:
        root = None

    checks = run_checks(root, online=online)

    table = Table(
        title="qx doctor",
        title_style=theme.TITLE,
        header_style=theme.HEADING,
        show_lines=False,
    )
    table.add_column("", width=4)
    table.add_column("check", style=theme.FIGURE)
    table.add_column("detail")

    for check in checks:
        label, style = STATUS_ICON[check.status]
        table.add_row(Text(label, style=style), check.name, check.detail)

    ui.console.print()
    ui.console.print(table)

    fixes = [c for c in checks if c.fix]
    if fixes:
        ui.console.print()
        for check in fixes:
            ui.console.print(
                Text(f"  {check.name}: ", style=theme.STRONG)
                + Text(check.fix or "", style=theme.DETAIL)
            )

    failed = [c for c in checks if c.status == "fail"]
    ui.console.print()
    if failed:
        ui.error(f"{len(failed)} blocking problem(s). Fix those before starting.")
        raise typer.Exit(code=1)
    ui.success("Environment is ready. Run `qx next` to begin.")
    ui.console.print()


def _save_account() -> None:
    """Interactive credential save. The token is read without echo and never displayed."""
    import getpass as getpass_module
    from getpass import getpass

    from quantum_exercises import doctor as doctor_module

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        ui.error("qiskit-ibm-runtime is not installed. Run `uv sync` first.")
        raise typer.Exit(code=1) from exc

    ui.console.print()
    ui.console.print(
        Panel(
            Text(
                "Get an API key from https://quantum.cloud.ibm.com\n"
                "The key is stored unencrypted in ~/.qiskit/qiskit-ibm.json, so only do this "
                "on a machine you trust.",
            ),
            title="save IBM Quantum account",
            border_style=theme.BORDER_ACTIVE,
            style=theme.PANEL,
            expand=False,
        )
    )

    # getpass falls back to a plain input() when it cannot turn echo off, and only
    # says so through a warning. Refuse rather than print someone's key on screen.
    with warnings.catch_warnings(record=True) as echoed:
        warnings.simplefilter("always", getpass_module.GetPassWarning)
        token = getpass("API key (input hidden): ").strip()
    if any(issubclass(w.category, getpass_module.GetPassWarning) for w in echoed):
        ui.error(
            "This terminal cannot hide what you type, so the key would be echoed. "
            "Nothing was saved. Run this from a normal terminal, or set the "
            "QISKIT_IBM_TOKEN environment variable instead."
        )
        raise typer.Exit(code=1)

    if not token:
        ui.warn("No key entered, nothing was saved.")
        raise typer.Exit(code=1)

    instance = input("Instance CRN (press Enter to skip): ").strip() or None

    try:
        QiskitRuntimeService.save_account(
            channel="ibm_quantum_platform",
            token=token,
            instance=instance,
            set_as_default=True,
            overwrite=True,
        )
    except Exception as exc:  # noqa: BLE001 - report rather than dump a traceback
        ui.error(f"Could not save the account: {type(exc).__name__}: {exc}")
        raise typer.Exit(code=1) from exc

    restricted = _restrict_credentials_permissions()

    ui.success("Account saved. Verify it with `qx doctor --online`.")
    if restricted:
        ui.info(f"{doctor_module.CREDENTIALS_PATH} is readable only by you.")
    else:
        ui.warn(
            f"Could not restrict permissions on {doctor_module.CREDENTIALS_PATH}. "
            "On a shared machine, tighten them yourself."
        )


def _restrict_credentials_permissions() -> bool:
    """Make the saved key owner-only.

    qiskit-ibm-runtime writes it with the process umask, normally 0644, so on a
    shared machine any other local user could read the key straight off disk.
    """
    from quantum_exercises.doctor import CREDENTIALS_PATH

    try:
        if CREDENTIALS_PATH.parent.is_dir():
            os.chmod(CREDENTIALS_PATH.parent, 0o700)
        if CREDENTIALS_PATH.is_file():
            os.chmod(CREDENTIALS_PATH, 0o600)
    except OSError:
        return False
    return True


@app.command("list")
def list_exercises() -> None:
    """Show every exercise and your progress."""
    _, exercises, state = _context()
    ui.render_list(exercises, state)


# Named next_exercise, exposed as `next`: a module-level function called `next`
# would shadow the builtin that run() relies on below.
@app.command("next")
def next_exercise() -> None:
    """Show the next exercise you have not finished."""
    _, exercises, state = _context()
    ui.render_next(_pick(None, exercises, state))


@app.command()
def run(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
    timeout: Annotated[
        int | None, typer.Option("--timeout", help="Override the per-exercise time limit.")
    ] = None,
    solution: Annotated[
        bool, typer.Option("--solution", help="Run solution.py instead of your file.")
    ] = False,
) -> None:
    """Check an exercise. With no argument, checks the next unfinished one."""
    root, exercises, state = _context()
    exercise = _pick(name, exercises, state)

    target = exercise.solution_file if solution else exercise.exercise_file
    result = run_exercise(exercise, root=root, target=target, timeout=timeout)
    ui.render_run(exercise, result, root=root)

    if result.passed and not solution:
        # Re-read before writing: a run can take minutes, and another qx process
        # that recorded progress meanwhile would be erased by this stale copy.
        state = load(root)
        was_complete = state.is_complete(exercise.slug)
        state.mark_done(exercise.slug, ran_on=run_result_ran_on(result.artifacts))
        save(root, state)
        if not was_complete:
            remaining = [e for e in exercises if not state.is_complete(e.slug)]
            if remaining:
                ui.info(f"Next up: {remaining[0].number:02d} {remaining[0].title}  (qx next)")
            else:
                ui.success("That was the last one. All exercises complete.")

    raise typer.Exit(code=0 if result.passed else 1)


@app.command()
def hint(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
    all_hints: Annotated[bool, typer.Option("--all", help="Reveal every hint at once.")] = False,
) -> None:
    """Reveal the next hint. Hints unlock one at a time and stay unlocked."""
    root, exercises, state = _context()
    exercise = _pick(name, exercises, state)
    hints = load_hints(exercise)

    if not hints:
        ui.warn(f"{exercise.slug} has no hints.")
        raise typer.Exit(code=0)

    if all_hints:
        state.get(exercise.slug).hints_revealed = len(hints)
        visible = len(hints)
    else:
        visible = state.reveal_hint(exercise.slug, len(hints))
    save(root, state)

    ui.console.print()
    for index in range(visible):
        ui.console.print(
            Panel(
                Markdown(hints[index], code_theme=theme.SYNTAX_THEME),
                title=f"hint {index + 1} of {len(hints)}",
                border_style=theme.BORDER,
                style=theme.PANEL,
                expand=False,
            )
        )

    if visible < len(hints):
        ui.info(
            f"{len(hints) - visible} more hint(s) available: run `qx hint {exercise.number}` again."
        )
    else:
        ui.info(f"That was the last hint. `qx solution {exercise.number}` shows the answer.")
    ui.console.print()


@app.command()
def solution(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")] = False,
) -> None:
    """Show the reference solution. This marks the exercise as solved, not done."""
    root, exercises, state = _context()
    exercise = _pick(name, exercises, state)

    if not yes and not state.is_complete(exercise.slug):
        confirmed = typer.confirm(
            f"Reveal the solution for {exercise.slug}? It will be recorded as solved, not done",
            default=False,
        )
        if not confirmed:
            ui.info("Nothing revealed.")
            raise typer.Exit(code=0)

    code = exercise.solution_file.read_text(encoding="utf-8")
    ui.console.print()
    ui.console.print(
        Panel(
            Syntax(
                code,
                "python",
                theme=theme.SYNTAX_THEME,
                line_numbers=False,
            ),
            title=str(exercise.solution_file),
            border_style=theme.BORDER_ACTIVE,
            style=theme.PANEL,
            expand=False,
        )
    )

    state.mark_solved(exercise.slug)
    save(root, state)
    ui.info(f"{exercise.slug} recorded as solved. Run `qx next` to continue.")
    ui.console.print()


@app.command()
def reset(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the confirmation prompt.")] = False,
) -> None:
    """Restore an exercise file to its starting state and clear its progress."""
    root, exercises, state = _context()
    exercise = _pick(name, exercises, state)

    if not exercise.template_file.is_file():
        ui.error(f"{exercise.slug} has no template.py, so it cannot be reset.")
        raise typer.Exit(code=2)

    if not yes:
        confirmed = typer.confirm(
            f"Overwrite {exercise.exercise_file.name} for {exercise.slug}? Your edits will be lost",
            default=False,
        )
        if not confirmed:
            ui.info("Nothing changed.")
            raise typer.Exit(code=0)

    shutil.copyfile(exercise.template_file, exercise.exercise_file)
    state.reset(exercise.slug)
    save(root, state)
    ui.success(f"{exercise.slug} restored to its starting state.")


@app.command()
def watch(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
) -> None:
    """Re-check an exercise every time you save it. Ctrl-C to stop."""
    from quantum_exercises.watch import watch_exercise

    root, exercises, state = _context()
    watch_exercise(_pick(name, exercises, state), root=root, exercises=exercises)


@app.command()
def version() -> None:
    """Print versions of the tool and the quantum stack it runs on."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as pkg_version

    rows = [("quantum-exercises", __version__)]
    for package in ("qiskit", "qiskit-ibm-runtime", "qiskit-aer"):
        try:
            rows.append((package, pkg_version(package)))
        except PackageNotFoundError:
            rows.append((package, "not installed"))

    ui.console.print()
    for package, installed in rows:
        ui.console.print(
            Text(f"  {package:22}", style=theme.FIGURE) + Text(installed, style=theme.BODY)
        )
    ui.console.print()


def main() -> None:
    """Console-script entry point declared in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
