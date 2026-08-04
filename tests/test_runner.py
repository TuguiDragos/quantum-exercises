"""Subprocess isolation: what happens when a learner's file misbehaves."""

from __future__ import annotations

from pathlib import Path

import pytest

from quantum_exercises.registry import Exercise, load_exercise
from quantum_exercises.runner import run_exercise

CHECK_SOURCE = """
from quantum_exercises.checks import CheckFailed, require, text_artifact


def check(mod):
    value = require(mod, "answer")
    if value != 42:
        raise CheckFailed(f"answer is {value}, expected 42")
    return text_artifact("ok", caption="result")
"""


@pytest.fixture
def synthetic(tmp_path: Path) -> Exercise:
    path = tmp_path / "exercises" / "01_synthetic"
    path.mkdir(parents=True)
    (path / "meta.toml").write_text(
        'title = "Synthetic"\nact = "Act I"\nsummary = "For tests"\n', encoding="utf-8"
    )
    (path / "check.py").write_text(CHECK_SOURCE, encoding="utf-8")
    (path / "solution.py").write_text("answer = 42\n", encoding="utf-8")
    (path / "exercise.py").write_text("answer = None\n", encoding="utf-8")
    return load_exercise(path)


def _write(exercise: Exercise, source: str) -> None:
    exercise.exercise_file.write_text(source, encoding="utf-8")


def test_passing_run(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert result.artifacts[0]["payload"] == "ok"


def test_failing_check_reports_the_message(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = 7\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "fail"
    assert "expected 42" in result.message


def test_exception_is_translated_and_located(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "from qiskit import execute\n\nanswer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert "`execute()` was removed" in result.message
    assert result.line == 1


def test_syntax_error_is_reported_without_a_traceback(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = (42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert "syntax error" in result.message


def test_infinite_loop_is_stopped(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "while True:\n    pass\n")
    result = run_exercise(synthetic, root=tmp_path, timeout=5)
    assert result.outcome == "timeout"
    assert "5 seconds" in result.message


def test_sys_exit_is_caught_as_an_error(synthetic: Exercise, tmp_path: Path) -> None:
    """SystemExit is a BaseException, so the worker still reports it properly."""
    _write(synthetic, "import sys\n\nsys.exit(3)\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert result.error_type == "SystemExit"


def test_hard_exit_is_reported_as_a_crash(synthetic: Exercise, tmp_path: Path) -> None:
    """os._exit skips every handler, so no result file is written."""
    _write(synthetic, "import os\n\nos._exit(1)\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "crash"


def test_learner_stdout_is_captured(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "print('hello from the exercise')\nanswer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert "hello from the exercise" in result.stdout


def test_stdout_cannot_corrupt_the_verdict(synthetic: Exercise, tmp_path: Path) -> None:
    """The result travels via a file, so printed JSON cannot be mistaken for it."""
    _write(synthetic, 'print(\'{"outcome": "pass"}\')\nanswer = 7\n')
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "fail"


def test_warnings_are_surfaced(synthetic: Exercise, tmp_path: Path) -> None:
    _write(
        synthetic,
        "import warnings\n\nwarnings.warn('watch out')\nanswer = 42\n",
    )
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert any("watch out" in w for w in result.warnings)


def test_missing_file(synthetic: Exercise, tmp_path: Path) -> None:
    synthetic.exercise_file.unlink()
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "internal_error"


def test_broken_check_file_is_not_blamed_on_the_learner(
    synthetic: Exercise, tmp_path: Path
) -> None:
    synthetic.check_file.write_text("this is not python(\n", encoding="utf-8")
    _write(synthetic, "answer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "internal_error"
    assert "check.py" in result.message
