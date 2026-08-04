"""End-to-end CLI behaviour, against a throwaway copy of the repository.

Every test here runs with QX_ROOT pointed at a temporary copy, so the suite never
edits the real exercise files or the real progress file.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quantum_exercises.cli import app

runner = CliRunner()


@pytest.fixture
def sandbox(tmp_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(root / "exercises", tmp_path / "exercises")
    monkeypatch.setenv("QX_ROOT", str(tmp_path))
    return tmp_path


def _invoke(*args: str):
    return runner.invoke(app, list(args))


class TestListing:
    def test_list_shows_every_exercise(self, sandbox: Path) -> None:
        result = _invoke("list")
        assert result.exit_code == 0
        assert "01_environment" in result.stdout
        assert "12_honest_reading" in result.stdout
        assert "0/12" in result.stdout

    def test_next_points_at_the_first_unfinished(self, sandbox: Path) -> None:
        result = _invoke("next")
        assert result.exit_code == 0
        assert "Your environment works" in result.stdout

    def test_version(self) -> None:
        result = _invoke("version")
        assert result.exit_code == 0
        assert "quantum-exercises" in result.stdout
        assert "qiskit" in result.stdout


class TestRunning:
    def test_untouched_exercise_fails(self, sandbox: Path) -> None:
        result = _invoke("run", "1")
        assert result.exit_code == 1

    def test_solved_exercise_passes_and_is_recorded(self, sandbox: Path) -> None:
        exercise = sandbox / "exercises" / "01_environment"
        shutil.copyfile(exercise / "solution.py", exercise / "exercise.py")

        result = _invoke("run", "1")
        assert result.exit_code == 0
        assert "PASS" in result.stdout

        listing = _invoke("list")
        assert "1/12" in listing.stdout

    def test_solution_flag_does_not_record_progress(self, sandbox: Path) -> None:
        assert _invoke("run", "1", "--solution").exit_code == 0
        assert "0/12" in _invoke("list").stdout

    def test_next_advances_after_a_pass(self, sandbox: Path) -> None:
        exercise = sandbox / "exercises" / "01_environment"
        shutil.copyfile(exercise / "solution.py", exercise / "exercise.py")
        _invoke("run", "1")

        result = _invoke("next")
        assert "Counts is just a dictionary" in result.stdout

    def test_unknown_exercise(self, sandbox: Path) -> None:
        result = _invoke("run", "zzzz")
        assert result.exit_code == 2


class TestHints:
    def test_hints_unlock_one_at_a_time(self, sandbox: Path) -> None:
        first = _invoke("hint", "1")
        assert first.exit_code == 0
        assert "hint 1 of 3" in first.stdout
        assert "hint 2 of 3" not in first.stdout

        second = _invoke("hint", "1")
        assert "hint 1 of 3" in second.stdout
        assert "hint 2 of 3" in second.stdout

    def test_all_flag_reveals_everything(self, sandbox: Path) -> None:
        result = _invoke("hint", "1", "--all")
        assert "hint 3 of 3" in result.stdout


class TestSolutionAndReset:
    def test_solution_marks_as_solved(self, sandbox: Path) -> None:
        result = _invoke("solution", "1", "--yes")
        assert result.exit_code == 0
        assert "solved" in _invoke("list").stdout

    def test_reset_restores_the_template(self, sandbox: Path) -> None:
        exercise = sandbox / "exercises" / "01_environment"
        exercise.joinpath("exercise.py").write_text("# wrecked\n", encoding="utf-8")

        assert _invoke("reset", "1", "--yes").exit_code == 0
        assert exercise.joinpath("exercise.py").read_text(encoding="utf-8") == exercise.joinpath(
            "template.py"
        ).read_text(encoding="utf-8")

    def test_reset_clears_progress(self, sandbox: Path) -> None:
        _invoke("solution", "1", "--yes")
        _invoke("reset", "1", "--yes")
        assert "0/12" in _invoke("list").stdout


class TestDoctor:
    def test_reports_the_stack(self, sandbox: Path) -> None:
        result = _invoke("doctor")
        assert "Qiskit SDK" in result.stdout
        assert "Exercises" in result.stdout
        # An IBM account is optional, so a machine without one must still pass.
        assert result.exit_code == 0


class TestOutsideARepository:
    def test_helpful_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QX_ROOT", str(tmp_path))
        result = _invoke("list")
        assert result.exit_code == 2
