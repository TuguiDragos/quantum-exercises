"""Watch mode: re-check on save, and advance when an exercise passes."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from watchfiles import watch

from quantum_exercises import theme, ui
from quantum_exercises.registry import Exercise
from quantum_exercises.runner import ran_on as run_result_ran_on
from quantum_exercises.runner import run_exercise
from quantum_exercises.state import load, save

# Editors save by writing a temp file and renaming it, which fires several events.
# 200 ms of quiet is enough to collapse those into one run.
DEBOUNCE_MS = 200
STEP_MS = 50


def _watched_files(exercise: Exercise) -> set[str]:
    return {str(exercise.exercise_file.resolve()), str(exercise.check_file.resolve())}


def _announce(exercise: Exercise, root: Path) -> None:
    ui.console.print()
    ui.console.print(
        Text("  watching  ", style=theme.HEADING)
        + Text(str(exercise.exercise_file.relative_to(root)), style=theme.PATH)
        + Text("   save to re-run, Ctrl-C to stop", style=theme.DETAIL)
    )


def _run_and_record(exercise: Exercise, root: Path) -> bool:
    """Check the exercise, show the result, and save progress when it passes."""
    result = run_exercise(exercise, root=root)
    ui.render_run(exercise, result, root=root)
    if not result.passed:
        return False

    state = load(root)
    state.mark_done(exercise.slug, ran_on=run_result_ran_on(result.artifacts))
    save(root, state)
    return True


def _next_unfinished(root: Path, exercises: list[Exercise]) -> Exercise | None:
    state = load(root)
    for exercise in exercises:
        if not state.is_complete(exercise.slug):
            return exercise
    return None


def watch_exercise(exercise: Exercise, *, root: Path, exercises: list[Exercise]) -> None:
    """Block until interrupted, re-running the current exercise whenever it changes."""
    current = exercise

    try:
        # One pass before watching, so a file that already passes moves on at once.
        if _run_and_record(current, root):
            following = _next_unfinished(root, exercises)
            if following is None:
                ui.success("Every exercise is complete.")
                return
            current = following

        # watch() is bound to one directory, so advancing needs a fresh watcher.
        # The outer loop is that re-registration, not recursion.
        while True:
            _announce(current, root)
            advanced_to: Exercise | None = None

            for changes in watch(current.path, debounce=DEBOUNCE_MS, step=STEP_MS):
                touched = {str(Path(path).resolve()) for _, path in changes}
                if not touched & _watched_files(current):
                    continue

                if _run_and_record(current, root):
                    following = _next_unfinished(root, exercises)
                    if following is None:
                        ui.success("Every exercise is complete.")
                        return
                    if following is not current:
                        advanced_to = following
                        break

                _announce(current, root)

            if advanced_to is None:
                # The watcher stopped on its own, for example the directory vanished.
                return

            current = advanced_to
            ui.info(f"Moving on to {current.number:02d} {current.title}")

    except KeyboardInterrupt:
        ui.console.print()
        ui.info("Stopped watching.")


__all__ = ["watch_exercise"]
