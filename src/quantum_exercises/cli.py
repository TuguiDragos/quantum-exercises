"""The `qx` command."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from typer import rich_utils

from quantum_exercises import __version__, invocation, theme, ui
from quantum_exercises.registry import (
    EXERCISES_DIR,
    NOTEBOOKS_DIR,
    Exercise,
    RegistryError,
    course_template,
    find_project_root,
    holds_exercises,
    load_exercises,
    load_hints,
    resolve,
)
from quantum_exercises.runner import ran_on as run_result_ran_on
from quantum_exercises.runner import run_exercise
from quantum_exercises.state import STATE_FILENAME, State, load, locked
from quantum_exercises.state import unreadable as state_unreadable


class _SquarePanel(Panel):
    """Rich's Panel with the corners this project draws everywhere else."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("box", box.SQUARE)
        super().__init__(*args, **kwargs)


def _theme_typer() -> None:
    """Put typer's help and error output on this tool's palette and square boxes.

    The color system must match ours: rich caches Style objects and the ANSI they
    first emit, so a narrower system negotiated by typer would stick for both.
    """
    rich_utils.Panel = _SquarePanel
    rich_utils.COLOR_SYSTEM = ui.console.color_system
    rich_utils.STYLE_USAGE = theme.HEADING
    rich_utils.STYLE_USAGE_COMMAND = theme.COMMAND
    rich_utils.STYLE_HELPTEXT_FIRST_LINE = theme.BODY
    rich_utils.STYLE_HELPTEXT = theme.BODY
    rich_utils.STYLE_OPTION = theme.FIGURE
    rich_utils.STYLE_SWITCH = theme.FIGURE
    rich_utils.STYLE_NEGATIVE_OPTION = theme.FIGURE
    rich_utils.STYLE_NEGATIVE_SWITCH = theme.FIGURE
    rich_utils.STYLE_TYPES = theme.DETAIL
    rich_utils.STYLE_TYPES_SEPARATOR = theme.DETAIL
    rich_utils.STYLE_OPTION_HELP = theme.BODY
    rich_utils.STYLE_OPTION_DEFAULT = theme.DETAIL
    rich_utils.STYLE_OPTION_ENVVAR = theme.DETAIL
    rich_utils.STYLE_REQUIRED_SHORT = theme.FIGURE
    rich_utils.STYLE_REQUIRED_LONG = theme.DETAIL
    rich_utils.STYLE_DEPRECATED = theme.DETAIL
    rich_utils.STYLE_DEPRECATED_COMMAND = theme.DETAIL
    rich_utils.STYLE_OPTIONS_PANEL_BORDER = theme.BORDER
    rich_utils.STYLE_COMMANDS_PANEL_BORDER = theme.BORDER
    rich_utils.STYLE_COMMANDS_TABLE_FIRST_COLUMN = theme.COMMAND
    rich_utils.STYLE_ERRORS_PANEL_BORDER = theme.BORDER_ACTIVE
    rich_utils.STYLE_ERRORS_SUGGESTION = theme.DETAIL
    rich_utils.STYLE_ABORTED = theme.DETAIL
    # Typer hardcodes this color in a string; replace it so translations survive.
    rich_utils.RICH_HELP = rich_utils.RICH_HELP.replace("[blue]", f"[{theme.ACCENT}]")


_theme_typer()


# Typer auto-accents options but not the command before them, so mark whole
# commands by hand. The epilog has no manual line breaks: help text is rewrapped.
def _typed(command: str) -> str:
    return f"[{theme.ACCENT}]{command}[/]"


EPILOG = (
    f"Start with {_typed('qx next')}. Every command takes an exercise number, slug or"
    f" fragment, and picks the first unfinished one when you leave it out, so"
    f" {_typed('qx run 11')}, {_typed('qx run bell')} and {_typed('qx run')} are all valid.\n\n"
    "Real IBM hardware is optional, and only exercise 14 reaches for it: everything"
    " runs on a local simulator without an account. To use one, create an API key at"
    f" https://cloud.ibm.com/iam/apikeys, then {_typed('qx doctor --save-account')} to store"
    f" it and {_typed('qx doctor --online')} to check that IBM still accepts it."
)

app = typer.Typer(
    name="qx",
    help="Hands-on Qiskit exercises, from an empty laptop to real IBM hardware.",
    epilog=EPILOG,
    no_args_is_help=True,
    add_completion=False,
)


def _show_version(value: bool) -> None:
    if value:
        version()
        raise typer.Exit()


@app.callback()
def _options(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print versions of the tool and the quantum stack it runs on.",
            callback=_show_version,
            is_eager=True,
        ),
    ] = False,
) -> None:
    pass


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

    if state_unreadable(root):
        ui.warn(
            f"{STATE_FILENAME} could not be read, so everything below shows as unfinished. "
            "Your file has not been touched; it is copied aside the next time progress is saved."
        )
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
        f"Every exercise is complete. Run `{invocation()} list` to review, "
        f"or `{invocation()} reset <name>` to redo one."
    )
    raise typer.Exit(code=0)


DEFAULT_COURSE_DIR = "quantum-exercises"

# What `qx init` copies. The rest of the repository is for maintainers.
COURSE_PARTS = (EXERCISES_DIR, NOTEBOOKS_DIR)

# Never touched by --refresh, not even recreated; `qx reset` restores it.
LEARNER_FILE = "exercise.py"

BACKUP_SUFFIX = ".bak"

COURSE_README = "README.md"


def _course_around(start: Path) -> Path | None:
    """The course this directory sits inside, if any.

    Narrower than find_project_root on purpose: no QX_ROOT and no installed-package
    fallback, since this picks where to write a new course.
    """
    for directory in [start, *start.parents]:
        if holds_exercises(directory):
            return directory
    return None


def _default_target() -> Path:
    """A new directory, or the course the reader is already standing in."""
    here = Path.cwd()
    found = _course_around(here.resolve())
    if found is None:
        return Path(DEFAULT_COURSE_DIR)
    return Path(".") if found == here.resolve() else found


@app.command()
def init(
    directory: Annotated[
        str | None,
        typer.Argument(help="Where to put the course. Created if it is not there yet."),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            help="Also update lesson files already copied. Never replaces your exercise.py.",
        ),
    ] = False,
) -> None:
    """Copy the exercises somewhere you can edit them. Start here after installing."""
    try:
        source = course_template()
    except RegistryError as exc:
        ui.error(
            "This copy of qx carries no course, and there is no repository around it "
            "to take one from."
        )
        raise typer.Exit(code=2) from exc

    target = Path(directory).expanduser() if directory is not None else _default_target()
    _refuse_a_target_inside_the_source(source, target)
    _refuse_an_unsuitable_target(target)
    topping_up = holds_exercises(target)

    # Owned here so a failure part way through can still report what landed.
    added: list[str] = []
    refreshed: list[str] = []
    refused: list[str] = []
    try:
        _copy_course(source, target, added, refreshed, refused, refresh=refresh)
    except OSError as exc:
        if added or refreshed:
            _report_update(target, added, refreshed, refused)
            ui.warn("That is how far it got. Fix what is below and run it again to finish.")
        ui.error(f"Could not write the course to {target}: {exc.strerror or exc}")
        raise typer.Exit(code=2) from exc

    _report_init(target, added, refreshed, refused, topping_up=topping_up)


def _refuse_a_target_inside_the_source(source: Path, target: Path) -> None:
    """Refuse a target strictly inside the source: copytree would recurse until ENAMETOOLONG.

    Equal paths are fine; that is `qx init .` at the top of a clone.
    """
    inside = target.expanduser().resolve()
    origin = source.resolve()
    if inside != origin and inside.is_relative_to(origin):
        ui.error(
            f"{target} is inside the course being copied from, so the copy would "
            "never finish. Give the course a directory of its own."
        )
        raise typer.Exit(code=2)


def _refuse_an_unsuitable_target(target: Path) -> None:
    """Anything already in the way is the reader's, so stop rather than mix into it."""
    if target.exists() and not target.is_dir():
        ui.error(f"{target} is a file, so the course cannot go there.")
        raise typer.Exit(code=2)

    if not target.is_dir() or holds_exercises(target):
        return

    try:
        occupied = any(target.iterdir())
    except OSError as exc:
        ui.error(f"Could not read {target}: {exc.strerror or exc}")
        raise typer.Exit(code=2) from exc

    if occupied:
        ui.error(
            f"{target} already holds something that is not a course, so nothing was "
            "copied. Give the course a directory of its own, or an empty one."
        )
        raise typer.Exit(code=2)


def _skippable(name: str) -> bool:
    """Bytecode, hidden files and notebook checkpoints, at any depth."""
    return name.startswith(".") or name == "__pycache__" or name.endswith(".pyc")


def _copy_course(
    source: Path,
    target: Path,
    added: list[str],
    refreshed: list[str],
    refused: list[str],
    *,
    refresh: bool = False,
) -> None:
    """Copy whatever the target lacks; with ``refresh``, also update changed lesson files."""
    for part in COURSE_PARTS:
        origin = source / part
        if not origin.is_dir():
            continue
        destination = target / part
        # Never write through a symlink: it would land outside the course.
        if destination.is_symlink():
            refused.append(part)
            continue
        destination.mkdir(parents=True, exist_ok=True)
        for entry in sorted(origin.iterdir()):
            if _skippable(entry.name):
                continue
            landing = destination / entry.name
            label = f"{part}/{entry.name}"
            # A dangling link reads as absent, and copying would create its target.
            if landing.is_symlink():
                refused.append(label)
                continue
            if not landing.exists():
                if entry.is_dir():
                    shutil.copytree(
                        entry, landing, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
                    )
                else:
                    shutil.copyfile(entry, landing)
                added.append(label)
            elif refresh:
                _refresh_entry(entry, landing, label, added, refreshed, refused)
    _place_course_readme(target, added, refreshed, refused, refresh=refresh)


def _backup_path(landing: Path) -> Path:
    """A backup path that never overwrites an earlier backup."""
    candidate = landing.with_name(landing.name + BACKUP_SUFFIX)
    index = 1
    while candidate.exists() or candidate.is_symlink():
        index += 1
        candidate = landing.with_name(f"{landing.name}{BACKUP_SUFFIX}.{index}")
    return candidate


def _copy_aside(landing: Path) -> None:
    """Back up the current file, keeping its mode so a private file stays private."""
    backup = _backup_path(landing)
    shutil.copyfile(landing, backup)
    shutil.copymode(landing, backup)


def _replace_atomically(data: bytes, landing: Path) -> None:
    """Write beside the target, then rename, so a full disk never leaves half a file."""
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 - must outlive the block for os.replace
        mode="wb", dir=landing.parent, prefix=".qx-refresh-", suffix=".tmp", delete=False
    )
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # Temp files are owner-only; keep the mode of the file being replaced.
        shutil.copymode(landing, handle.name)
        os.replace(handle.name, landing)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def _refresh_entry(
    origin: Path,
    landing: Path,
    label: str,
    added: list[str],
    refreshed: list[str],
    refused: list[str],
) -> None:
    """Bring one already-copied file, or one directory of them, back in step."""
    # Following a link here could overwrite files outside the course. The course
    # root itself may still be a link.
    if landing.is_symlink():
        refused.append(label)
        return

    if origin.is_dir():
        landing.mkdir(parents=True, exist_ok=True)
        for entry in sorted(origin.iterdir()):
            if _skippable(entry.name):
                continue
            _refresh_entry(
                entry, landing / entry.name, f"{label}/{entry.name}", added, refreshed, refused
            )
        return

    if origin.name == LEARNER_FILE:
        return

    if not landing.exists():
        shutil.copyfile(origin, landing)
        added.append(label)
        return

    if landing.read_bytes() == origin.read_bytes():
        return

    # The backup is kept even if the replacement fails.
    _copy_aside(landing)
    _replace_atomically(origin.read_bytes(), landing)
    refreshed.append(label)


COURSE_README_TITLE = "# Your quantum-exercises course"


def _place_course_readme(
    target: Path, added: list[str], refreshed: list[str], refused: list[str], *, refresh: bool
) -> None:
    """Write the course README.

    Refreshed only if it starts with our title, so `qx init .` in a clone keeps the
    project's own README. A lookalike is replaced too, but backed up first.
    """
    landing = target / COURSE_README
    body = _course_readme_text()
    if landing.is_symlink():
        refused.append(COURSE_README)
        return
    if not landing.exists():
        landing.write_text(body, encoding="utf-8")
        added.append(COURSE_README)
        return
    if not refresh:
        return

    current = landing.read_text(encoding="utf-8", errors="replace")
    if current == body or not current.startswith(COURSE_README_TITLE):
        return
    _copy_aside(landing)
    _replace_atomically(body.encode("utf-8"), landing)
    refreshed.append(COURSE_README)


def _course_readme_text() -> str:
    """The note `qx init` leaves at the top of a course."""
    qx = invocation()
    return f"""# Your quantum-exercises course

The exercises, and the labs that go with them. Everything here is yours to edit.

## Start

    {qx} doctor     check that the toolchain works
    {qx} next       the next exercise to work on
    {qx} run        check your answer
    {qx} list       every exercise, and where you are

`{qx}` on its own prints the whole command list.

## What is in here

- `{EXERCISES_DIR}/` one directory per exercise. You edit `{LEARNER_FILE}`; the rest is
  the lesson, the hints, the reference answer and the checker.
- `{NOTEBOOKS_DIR}/` labs to poke at. None of them are graded.
- `{STATE_FILENAME}` your progress. Delete it and the course forgets you.

## Keeping it current

Run these from this directory. `{qx} init` again brings across anything a newer
release added, and never touches an answer you have written. `{qx} init --refresh`
also updates the lesson files themselves, keeping a `{BACKUP_SUFFIX}` copy of any
you had changed.

    uv tool upgrade quantum-exercises
    {qx} init --refresh

https://github.com/TuguiDragos/quantum-exercises
"""


def _listed(items: list[str]) -> None:
    """One path per line, never wrapped into what looks like two paths."""
    for item in items:
        ui.console.print(Text(f"    {item}", style=theme.DETAIL), soft_wrap=True)


def _report_update(
    target: Path, added: list[str], refreshed: list[str], refused: list[str]
) -> None:
    """What happened to a course that was already there."""
    if added:
        ui.success(f"Added {ui.plural(len(added), 'thing')} to {target}:")
        _listed(added)

    if refreshed:
        ui.success(f"Brought {ui.plural(len(refreshed), 'file')} in {target} up to date:")
        _listed(refreshed)
        ui.info(f"The version you had is beside each one, with a {BACKUP_SUFFIX} suffix.")

    if refused:
        ui.warn(f"Left {len(refused)} alone, because a symlink stands where the course goes:")
        _listed(refused)
        ui.info("Following one would write outside the course. Put a real file or folder there.")

    if not added and not refreshed and not refused:
        ui.info(f"{target} already has the whole course, so nothing was copied.")
    elif refreshed:
        ui.info(f"No {LEARNER_FILE} was touched, so your answers are as you left them.")
    elif added:
        ui.info("Everything already there was left alone.")
    ui.console.print()


def _report_init(
    target: Path, added: list[str], refreshed: list[str], refused: list[str], *, topping_up: bool
) -> None:
    if topping_up or not added:
        _report_update(target, added, refreshed, refused)
        return

    exercises = sum(1 for item in added if item.startswith(f"{EXERCISES_DIR}/"))
    ui.success(f"The course is in {target}: {exercises} exercises, ready to edit.")
    ui.console.print()
    ui.console.print(
        Text("  cd    ", style=theme.DETAIL) + Text(str(target), style=theme.PATH),
        soft_wrap=True,
    )
    ui.console.print(
        Text("  then  ", style=theme.DETAIL)
        + Text(f"{invocation()} doctor", style=theme.COMMAND)
        + Text(" to check the toolchain, then ", style=theme.DETAIL)
        + Text(f"{invocation()} next", style=theme.COMMAND)
        + "\n"
    )


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
        border_style=theme.BORDER,
        box=ui.TABLE_BOX,
        show_lines=False,
    )
    table.add_column("", width=4)
    table.add_column("check", style=theme.FIGURE)
    table.add_column("detail", overflow="fold")

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
                ui.indented(
                    Text(f"{check.name}: ", style=theme.STRONG)
                    + ui.prose(check.fix or "", theme.DETAIL)
                )
            )

    failed = [c for c in checks if c.status == "fail"]
    ui.console.print()
    if failed:
        ui.error(f"{ui.plural(len(failed), 'blocking problem')}. Fix those before starting.")
        raise typer.Exit(code=1)
    ui.success(f"Environment is ready. Run `{invocation()} next` to begin.")
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
                "Create an API key at https://cloud.ibm.com/iam/apikeys and copy it "
                "straight away: it is shown once.\n"
                "The key is stored unencrypted in ~/.qiskit/qiskit-ibm.json, so only do this "
                "on a machine you trust.\n\n"
                "You will be asked for an instance CRN after the key. It is optional: left "
                "empty, the account uses whichever instance it finds. Fill it in only if you "
                "have several and want one of them by default.",
            ),
            title="save IBM Quantum account",
            **ui.panel(),
        )
    )

    # getpass falls back to echoing input with only a warning; refuse instead.
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

    instance = input("Instance CRN (optional, Enter to let the account choose): ").strip() or None

    prepared = _prepare_credentials_file()

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

    restricted = _restrict_credentials_permissions() and prepared

    ui.success(f"Account saved. Verify it with `{invocation()} doctor --online`.")
    if restricted:
        ui.info(f"{doctor_module.CREDENTIALS_PATH} is readable only by you.")
    else:
        ui.warn(
            f"Could not restrict permissions on {doctor_module.CREDENTIALS_PATH}. "
            "On a shared machine, tighten them yourself."
        )


def _prepare_credentials_file() -> bool:
    """Create the credentials file at 0600 before qiskit writes the token into it.

    qiskit-ibm-runtime uses the umask (usually 0644) and never chmods, but keeps the
    mode of a file that already exists, so this leaves no world-readable window.
    """
    from quantum_exercises.doctor import CREDENTIALS_PATH

    try:
        CREDENTIALS_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(CREDENTIALS_PATH.parent, 0o700)
        if not CREDENTIALS_PATH.exists():
            # O_EXCL never truncates a concurrent save; qiskit reads {} as no accounts.
            handle = os.open(CREDENTIALS_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(handle, b"{}")
            finally:
                os.close(handle)
        os.chmod(CREDENTIALS_PATH, 0o600)
    except OSError:
        return False
    return True


def _restrict_credentials_permissions() -> bool:
    """Make the saved key owner-only; qiskit-ibm-runtime writes it with the umask."""
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


# Not named `next`: that would shadow the builtin.
@app.command("next")
def next_exercise() -> None:
    """Show the next exercise you have not finished."""
    _, exercises, state = _context()
    ui.render_next(_pick(None, exercises, state))


@app.command()
def run(
    name: Annotated[str | None, typer.Argument(help="Exercise number, slug, or fragment.")] = None,
    timeout: Annotated[
        int | None,
        typer.Option("--timeout", help="Override the per-exercise time limit, in seconds."),
    ] = None,
    solution: Annotated[
        bool,
        typer.Option(
            "--solution", help="Run solution.py instead of your file. Records no progress."
        ),
    ] = False,
) -> None:
    """Check an exercise. With no argument, checks the next unfinished one."""
    if timeout is not None and timeout <= 0:
        ui.error("--timeout must be a positive number of seconds.")
        raise typer.Exit(code=2)

    root, exercises, state = _context()
    exercise = _pick(name, exercises, state)

    # Asked even with --timeout: a time limit is not consent.
    decision = _confirm_hardware(exercise)
    if timeout is None:
        timeout = decision.window
    if decision.window is not None:
        _announce_wait(timeout if timeout is not None else decision.window)

    target = exercise.solution_file if solution else exercise.exercise_file
    result = run_exercise(
        exercise, root=root, target=target, timeout=timeout, allow_hardware=decision.allowed
    )
    ui.render_run(exercise, result, root=root)

    if result.passed and not solution:
        # Re-read inside the lock so progress saved by another qx meanwhile survives.
        with locked(root):
            state = load(root)
            was_complete = state.is_complete(exercise.slug)
            state.mark_done(exercise.slug, ran_on=run_result_ran_on(result.artifacts))
            ui.save_progress(root, state)
        if not was_complete:
            remaining = [e for e in exercises if not state.is_complete(e.slug)]
            if remaining:
                ui.console.print(
                    Text("  next  ", style=theme.DETAIL)
                    + Text(f"{remaining[0].number:02d} {remaining[0].title}", style=theme.STRONG)
                    + Text(", with ", style=theme.DETAIL)
                    + Text(f"{invocation()} next", style=theme.COMMAND)
                    + "\n"
                )
            else:
                ui.success("That was the last one. All exercises complete.")
                ui.console.print()

    raise typer.Exit(code=0 if result.passed else 1)


# Hardware queues take hours; this limit applies only after the reader says yes.
HARDWARE_WINDOW_SECONDS = 3 * 60 * 60
COMPUTERS_URL = "https://quantum.cloud.ibm.com/computers"


@dataclass(frozen=True)
class _HardwareDecision:
    """Whether a run may reach a QPU, and the longer time limit a yes grants."""

    allowed: bool
    window: int | None = None


def _interactive() -> bool:
    """Whether stdin is a terminal; it can be None or closed, and isatty() then raises."""
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except (AttributeError, ValueError, OSError):
        return False


def _confirm_hardware(exercise: Exercise) -> _HardwareDecision:
    """Show the queue and ask before joining it. Without a terminal, stay on a simulator."""
    if not exercise.hardware:
        return _HardwareDecision(allowed=True)

    from quantum_exercises.backends import offline, queue_peek

    if offline():
        return _HardwareDecision(allowed=False)

    if not _interactive():
        ui.info(
            "No terminal here to answer in, so this runs on a local simulator. "
            f"Run `{invocation()} run {exercise.number}` from a terminal to use a real QPU."
        )
        return _HardwareDecision(allowed=False)

    ui.info("Asking IBM which QPU is free. This sends no job.")
    queue = queue_peek()
    if queue is None:
        # Fail closed: no answer is not consent to send a job.
        ui.info(
            "No QPU answered, so this runs on a local simulator. "
            f"`{invocation()} doctor --online` reports whether IBM can be reached at all."
        )
        return _HardwareDecision(allowed=False)

    ui.console.print()
    ui.console.print(
        Text("  least busy  ", style=theme.DETAIL)
        + Text(queue.name, style=theme.FIGURE)
        + Text(f"   {queue.pending} job(s) ahead of you", style=theme.BODY)
    )
    ui.console.print(
        Text("  all of them ", style=theme.DETAIL) + Text(COMPUTERS_URL, style=theme.PATH)
    )
    ui.console.print()

    if not typer.confirm("  Send it now? Answering no changes nothing and costs nothing"):
        ui.info(f"Nothing sent. Come back with `{invocation()} run {exercise.number}` any time.")
        raise typer.Exit(code=0)

    # The caller announces the wait, since --timeout may override the window.
    return _HardwareDecision(allowed=True, window=HARDWARE_WINDOW_SECONDS)


def _announce_wait(seconds: int) -> None:
    """Say how long a confirmed run will wait, in the limit it will really use."""
    if seconds == HARDWARE_WINDOW_SECONDS:
        ui.info(
            f"Waiting for the result, up to {seconds // 3600} hours. "
            "Ctrl-C stops waiting, not the job."
        )
        return
    ui.info(
        f"Waiting for the result, up to the {seconds} seconds you asked for. "
        "A queue can take hours, so the job may outlive the wait: it keeps running "
        "at IBM either way. Ctrl-C stops waiting, not the job."
    )


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

    with locked(root):
        state = load(root)
        if all_hints:
            state.get(exercise.slug).hints_revealed = len(hints)
            visible = len(hints)
        else:
            visible = state.reveal_hint(exercise.slug, len(hints))
        ui.save_progress(root, state)

    ui.console.print()
    for index in range(visible):
        ui.console.print(
            Panel(
                ui.markdown(hints[index]),
                title=f"hint {index + 1} of {len(hints)}",
                **ui.panel(border=theme.BORDER),
            )
        )

    if visible < len(hints):
        ui.info(
            f"{ui.plural(len(hints) - visible, 'more hint')} available: run "
            f"`{invocation()} hint {exercise.number}` again."
        )
    else:
        ui.info(
            f"That was the last hint. `{invocation()} solution {exercise.number}` shows the answer."
        )
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
                theme=ui.syntax_theme(),
                line_numbers=False,
            ),
            title=str(exercise.solution_file),
            **ui.panel(),
        )
    )

    # Re-read after the prompt so progress saved by another qx meanwhile survives.
    with locked(root):
        state = load(root)
        state.mark_solved(exercise.slug)
        saved = ui.save_progress(root, state)
    if saved:
        ui.info(f"{exercise.slug} recorded as solved. Run `{invocation()} next` to continue.")
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

    try:
        shutil.copyfile(exercise.template_file, exercise.exercise_file)
    except OSError as exc:
        ui.error(f"Could not restore {exercise.exercise_file}: {exc.strerror or exc}")
        raise typer.Exit(code=2) from exc

    # Re-read after the prompt, for the same reason as `solution`.
    with locked(root):
        state = load(root)
        state.reset(exercise.slug)
        saved = ui.save_progress(root, state)
    if saved:
        ui.success(f"{exercise.slug} restored to its starting state.")
    else:
        ui.warn(
            f"{exercise.exercise_file.name} was restored, but {exercise.slug} is still "
            "recorded as complete."
        )


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
