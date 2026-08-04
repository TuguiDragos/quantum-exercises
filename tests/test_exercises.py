"""The contract every exercise must satisfy.

This is what the weekly CI job is really watching: if a new Qiskit release changes
an API the curriculum depends on, a reference solution stops passing and the badge
goes red.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quantum_exercises.registry import Exercise, load_hints
from quantum_exercises.runner import run_exercise


def test_solution_passes(exercise: Exercise, root: Path) -> None:
    """Every reference solution must satisfy its own check."""
    result = run_exercise(exercise, root=root, target=exercise.solution_file)
    assert result.passed, (
        f"{exercise.slug} solution failed ({result.outcome}): "
        f"{result.message}\n{result.detail or ''}"
    )


def test_template_fails(exercise: Exercise, root: Path) -> None:
    """The starting file must not already pass, or the exercise teaches nothing."""
    result = run_exercise(exercise, root=root, target=exercise.template_file)
    assert not result.passed, f"{exercise.slug} passes with the untouched template"


def test_solution_produces_artifacts(exercise: Exercise, root: Path) -> None:
    """Every exercise ends in something executed and shown, not just a green tick."""
    result = run_exercise(exercise, root=root, target=exercise.solution_file)
    assert result.artifacts, f"{exercise.slug} produced no artifact to show the learner"


def test_required_files_exist(exercise: Exercise) -> None:
    for path in (
        exercise.exercise_file,
        exercise.solution_file,
        exercise.check_file,
        exercise.hints_file,
        exercise.readme_file,
        exercise.template_file,
    ):
        assert path.is_file(), f"{exercise.slug} is missing {path.name}"


def test_template_is_valid_python(exercise: Exercise) -> None:
    source = exercise.template_file.read_text(encoding="utf-8")
    compile(source, str(exercise.template_file), "exec")


def test_template_matches_the_committed_exercise(exercise: Exercise, root: Path) -> None:
    """template.py must stay a pristine copy of exercise.py as shipped.

    Compared against git rather than the working tree, so a learner's own edits to
    exercise.py never fail this. It exists because `ruff check --fix` once stripped
    the deliberately unused imports out of template.py, which would have made
    `qx reset` hand back a file missing the imports the exercise needs.
    """
    relative = exercise.exercise_file.relative_to(root).as_posix()
    try:
        committed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), "show", f"HEAD:{relative}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):  # pragma: no cover - git-less environment
        pytest.skip("git is not available")

    if committed.returncode != 0:
        pytest.skip(f"{relative} is not committed yet")

    # Normalise line endings: git stores LF, a Windows checkout may hold CRLF.
    expected = committed.stdout.replace("\r\n", "\n")
    actual = exercise.template_file.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert actual == expected, (
        f"{exercise.slug}/template.py has drifted from the committed exercise.py. "
        f"Refresh it with: cp {relative} {exercise.template_file.relative_to(root).as_posix()}"
    )


def test_has_three_hints(exercise: Exercise) -> None:
    hints = load_hints(exercise)
    assert len(hints) == 3, f"{exercise.slug} has {len(hints)} hints, expected 3"
    for index, hint in enumerate(hints, start=1):
        assert hint.strip(), f"{exercise.slug} hint {index} is empty"


def test_metadata_is_filled_in(exercise: Exercise) -> None:
    assert exercise.title.strip()
    assert exercise.act.strip()
    assert exercise.summary.strip()
    assert exercise.timeout > 0


def test_numbering_is_contiguous(exercises: list[Exercise]) -> None:
    numbers = [e.number for e in exercises]
    assert numbers == list(range(1, len(numbers) + 1)), f"exercise numbers are {numbers}"


def test_no_hardware_exercise_outside_act_three(exercises: list[Exercise]) -> None:
    for exercise in exercises:
        if exercise.hardware:
            assert "III" in exercise.act, f"{exercise.slug} touches hardware but is not in Act III"
