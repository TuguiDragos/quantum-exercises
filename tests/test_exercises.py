"""The contract every exercise must satisfy.

This is what the scheduled verify job is really watching: if a new Qiskit changes
an API the curriculum depends on, a reference solution stops passing and the badge
goes red.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

import pytest

from quantum_exercises.registry import Exercise, load_hints
from quantum_exercises.runner import run_exercise
from quantum_exercises.worker import MAX_ARTIFACT_CHARS


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
    # Report the outcome, not just the empty list. An artifact list is empty either
    # because check() returned nothing or because the run never got that far, and
    # a bare assertion cannot tell those apart afterwards.
    assert result.artifacts, (
        f"{exercise.slug} produced no artifact to show the learner "
        f"({result.outcome}): {result.message}\n{result.detail or ''}\n"
        f"{result.stderr.strip()}"
    )

    # The worker bounds what a verdict may carry, so an exercise approaching that
    # bound would silently arrive clipped. Asserted on the same run rather than in
    # a test of its own, which would mean starting all twenty workers again.
    blob = json.dumps(result.artifacts)
    assert "further characters were cut" not in blob, f"{exercise.slug} had an artifact clipped"
    assert "artifacts too large" not in blob, f"{exercise.slug} had its artifacts replaced"
    assert len(blob) < MAX_ARTIFACT_CHARS // 4, (
        f"{exercise.slug} produces {len(blob)} characters of artifacts, near enough the "
        f"{MAX_ARTIFACT_CHARS} a verdict may carry to be worth raising the limit"
    )


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


def _committed(root: Path, path: Path) -> str | None:
    """Content of a file as committed at HEAD, or None if git cannot say."""
    relative = path.relative_to(root).as_posix()
    try:
        shown = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), "show", f"HEAD:{relative}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):  # pragma: no cover - git-less environment
        return None
    if shown.returncode != 0:
        return None
    # Normalise line endings: git stores LF, a Windows checkout may hold CRLF.
    return shown.stdout.replace("\r\n", "\n")


def test_template_matches_the_committed_exercise(exercise: Exercise, root: Path) -> None:
    """template.py and exercise.py must be identical in the shipped repository.

    Both sides are read from git rather than the working tree, so neither a
    learner solving an exercise nor a maintainer editing one can trip this. It
    exists because `ruff check --fix` once stripped the deliberately unused
    imports out of template.py, which would have made `qx reset` hand back a file
    missing the imports the exercise needs.
    """
    template = _committed(root, exercise.template_file)
    original = _committed(root, exercise.exercise_file)

    if template is None or original is None:
        pytest.skip(f"{exercise.slug} is not committed yet")

    assert template == original, (
        f"{exercise.slug}/template.py has drifted from exercise.py in the commit. "
        f"Refresh it with: cp {exercise.exercise_file.relative_to(root).as_posix()} "
        f"{exercise.template_file.relative_to(root).as_posix()}"
    )


def test_readme_heading_carries_the_right_number(exercise: Exercise) -> None:
    """Four READMEs drifted two behind their directory when exercises were inserted.

    Nothing else reads the heading, so nothing else noticed for four releases.
    """
    first_line = exercise.readme_file.read_text(encoding="utf-8").splitlines()[0]
    expected = f"# {exercise.number:02d} - "
    assert first_line.startswith(expected), (
        f"{exercise.slug}/README.md starts {first_line!r}, expected it to start {expected!r}"
    )


def test_has_three_hints(exercise: Exercise) -> None:
    hints = load_hints(exercise)
    assert len(hints) == 3, f"{exercise.slug} has {len(hints)} hints, expected 3"
    for index, hint in enumerate(hints, start=1):
        assert hint.strip(), f"{exercise.slug} hint {index} is empty"


def test_title_and_slug_fit_their_columns(exercise: Exercise) -> None:
    """`qx list` uses fixed widths so the per-act tables line up with each other.

    A title one character too long wraps onto a second row and the alignment the
    fixed widths exist for is gone. ui.py sizes the columns to the longest of
    each; this is the other half of that arrangement.
    """
    from quantum_exercises.ui import LIST_COLUMNS

    widths = dict(LIST_COLUMNS)
    assert len(exercise.title) <= widths["title"], (
        f"{exercise.slug} title is {len(exercise.title)} characters, "
        f"and the column is {widths['title']}: it will wrap in `qx list`"
    )
    assert len(exercise.slug) <= widths["exercise"], (
        f"{exercise.slug} is {len(exercise.slug)} characters, "
        f"and the column is {widths['exercise']}"
    )


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


# Reading the learner's file back is how a check stops testing the answer and
# starts testing the spelling. Everything that pulls source text in one way or
# another, so a rewrite through a different call is caught too.
SOURCE_READING = frozenset(
    {
        "getsource",
        "getsourcelines",
        "getsourcefile",
        "findsource",
        "read_text",
        "read_bytes",
        "readlines",
        "readline",
        "read",
    }
)

# The one exercise allowed to do it, and why. Exercise 01 asks the learner to
# read the version out of the package rather than typing the number in. Both
# produce the identical string, so no amount of object inspection can tell them
# apart, and the file itself is the only evidence there is.
SOURCE_READING_ALLOWED = frozenset({"01_environment"})


def test_check_does_not_read_the_learners_source(exercise: Exercise) -> None:
    """CONTRIBUTING promises the suite blocks this. Until now nothing looked."""
    tree = ast.parse(exercise.check_file.read_text(encoding="utf-8"))
    found = sorted(
        {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in SOURCE_READING
        }
        | {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == "open"}
    )
    if exercise.slug in SOURCE_READING_ALLOWED:
        return
    assert not found, (
        f"{exercise.slug}/check.py reads source text ({', '.join(found)}). "
        "Inspect the objects the learner's code produced instead, so an answer that is "
        "right in an unexpected way still passes."
    )


def test_check_never_compares_counts_for_equality(exercise: Exercise) -> None:
    """Sampling is random, so an exact counts comparison is a flaky test by construction."""
    tree = ast.parse(exercise.check_file.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for operator, right in zip(node.ops, node.comparators, strict=True):
            if not isinstance(operator, (ast.Eq, ast.NotEq)):
                continue
            for side in (node.left, right):
                if isinstance(side, ast.Dict) or (
                    isinstance(side, ast.Call)
                    and isinstance(side.func, ast.Attribute)
                    and side.func.attr == "get_counts"
                ):
                    offenders.append(ast.unparse(node))
    assert not offenders, (
        f"{exercise.slug}/check.py compares counts for equality: {offenders}. "
        "Use assert_counts_support, assert_counts_close or assert_counts_distribution."
    )


def test_every_cross_reference_points_at_an_exercise_that_exists(
    exercises: list[Exercise], root: Path
) -> None:
    """The READMEs refer to each other by number, and inserting one shifts them all."""
    numbers = {e.number for e in exercises}
    sources = [
        *root.glob("exercises/*/README.md"),
        *root.glob("exercises/*/hints.md"),
        *root.glob("exercises/*/*.py"),
        *root.glob("notebooks/*.ipynb"),
        root / "README.md",
    ]
    dangling = []
    for path in sources:
        for match in re.finditer(
            r"(?i)\bexercises?\s+(\d{1,2})\b", path.read_text(encoding="utf-8")
        ):
            if int(match.group(1)) not in numbers:
                dangling.append(f"{path.relative_to(root)} -> exercise {match.group(1)}")
    assert not dangling, f"references to exercises that do not exist: {dangling}"


def test_readme_table_matches_the_exercises(exercises: list[Exercise], root: Path) -> None:
    """The table in the main README is written by hand and drifts silently."""
    readme = (root / "README.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (\d{2}) \| ([^|]+?) \|", readme, re.MULTILINE))
    for exercise in exercises:
        key = f"{exercise.number:02d}"
        assert key in rows, f"the README table has no row for {exercise.slug}"
        assert rows[key].strip() == exercise.title, (
            f"README row {key} says {rows[key].strip()!r}, "
            f"{exercise.slug}/meta.toml says {exercise.title!r}"
        )
    assert len(rows) == len(exercises), (
        f"the README table has {len(rows)} rows for {len(exercises)} exercises"
    )


def test_acts_are_contiguous_and_headed_in_the_readme(
    exercises: list[Exercise], root: Path
) -> None:
    """An act split in two would put the same heading twice in `qx list`."""
    order: list[str] = []
    for exercise in exercises:
        if not order or order[-1] != exercise.act:
            order.append(exercise.act)
    assert len(order) == len(set(order)), f"an act is split into separate blocks: {order}"

    readme = (root / "README.md").read_text(encoding="utf-8")
    for act in order:
        stem = act.split(" - ")[0]
        assert f"**{stem} - " in readme, f"the README has no heading for {stem}"
