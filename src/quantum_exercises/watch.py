"""Watch mode: re-check on save, and advance when an exercise passes."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text
from watchfiles import watch

from quantum_exercises import ui
from quantum_exercises.registry import Exercise
from quantum_exercises.runner import run_exercise
from quantum_exercises.state import load, save

# Editors save by writing a temp file and renaming it, which fires several events.
# 200 ms of quiet is enough to collapse those into one run.
DEBOUNCE_MS = 200
STEP_MS = 50


def _watched_files(exercise: Exercise) -> set[str]:
    return {str(exercise.exercise_file.resolve()), str(exercise.check_file.resolve())}


def watch_exercise(exercise: Exercise, *, root: Path, exercises: list[Exercise]) -> None:
    """Block until interrupted, re-running the exercise whenever its file changes."""
    current = exercise

    def announce() -> None:
        ui.console.print()
        ui.console.print(
            Text("  watching  ", style="bold blue")
            + Text(str(current.exercise_file.relative_to(root)), style="cyan")
            + Text("   save to re-run, Ctrl-C to stop", style="dim")
        )

    def check_once() -> bool:
        result = run_exercise(current, root=root)
        ui.render_run(current, result, root=root)
        if not result.passed:
            return False

        state = load(root)
        ran_on = next(
            (
                a.get("meta", {}).get("ran_on")
                for a in result.artifacts
                if a.get("meta", {}).get("ran_on")
            ),
            None,
        )
        state.mark_done(current.slug, ran_on=ran_on)
        save(root, state)
        return True

    try:
        if check_once():
            advanced = _advance(current, root, exercises)
            if advanced is None:
                ui.success("Every exercise is complete.")
                return
            current = advanced
        announce()

        # Watch the whole directory: many editors replace the file on save, which
        # would break a watch registered on the inode of the original file.
        for changes in watch(current.path, debounce=DEBOUNCE_MS, step=STEP_MS):
            touched = {str(Path(path).resolve()) for _, path in changes}
            if not touched & _watched_files(current):
                continue

            if check_once():
                advanced = _advance(current, root, exercises)
                if advanced is None:
                    ui.success("Every exercise is complete.")
                    return
                if advanced is not current:
                    current = advanced
                    ui.info(f"Moving on to {current.number:02d} {current.title}")
                    # Re-enter watch() so it follows the new exercise directory.
                    return watch_exercise(current, root=root, exercises=exercises)
            announce()

    except KeyboardInterrupt:
        ui.console.print()
        ui.info("Stopped watching.")


def _advance(current: Exercise, root: Path, exercises: list[Exercise]) -> Exercise | None:
    """First unfinished exercise after the current one, or None when all are done."""
    state = load(root)
    for exercise in exercises:
        if not state.is_complete(exercise.slug):
            return exercise
    return None


__all__ = ["watch_exercise"]
