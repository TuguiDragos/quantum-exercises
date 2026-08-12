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
    def test_list_shows_every_exercise(self, sandbox: Path, exercises: list) -> None:
        result = _invoke("list")
        assert result.exit_code == 0
        assert exercises[0].slug in result.stdout
        assert exercises[-1].slug in result.stdout
        assert f"0/{len(exercises)}" in result.stdout

    def test_next_points_at_the_first_unfinished(self, sandbox: Path) -> None:
        result = _invoke("next")
        assert result.exit_code == 0
        assert "Your environment works" in result.stdout

    def test_next_sends_the_reader_to_the_lesson_before_the_file(self, sandbox: Path) -> None:
        """The teaching is in README.md, and this used to name exercise.py alone.

        Someone following `qx next` landed among the TODOs having read none of the
        material that explains them, which is most of what the exercise is.
        """
        output = _invoke("next").stdout

        assert "README.md" in output, "the lesson was not offered"
        assert "exercise.py" in output, "the file to edit is still needed"
        assert output.index("README.md") < output.index("exercise.py"), "read comes before edit"

    def test_version(self) -> None:
        result = _invoke("version")
        assert result.exit_code == 0
        assert "quantum-exercises" in result.stdout
        assert "qiskit" in result.stdout


class TestRunning:
    def test_untouched_exercise_fails(self, sandbox: Path) -> None:
        result = _invoke("run", "1")
        assert result.exit_code == 1

    def test_solved_exercise_passes_and_is_recorded(self, sandbox: Path, exercises: list) -> None:
        exercise = sandbox / "exercises" / "01_environment"
        shutil.copyfile(exercise / "solution.py", exercise / "exercise.py")

        result = _invoke("run", "1")
        assert result.exit_code == 0
        assert "PASS" in result.stdout

        listing = _invoke("list")
        assert f"1/{len(exercises)}" in listing.stdout

    def test_solution_flag_does_not_record_progress(self, sandbox: Path, exercises: list) -> None:
        assert _invoke("run", "1", "--solution").exit_code == 0
        assert f"0/{len(exercises)}" in _invoke("list").stdout

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

    def test_reset_clears_progress(self, sandbox: Path, exercises: list) -> None:
        _invoke("solution", "1", "--yes")
        _invoke("reset", "1", "--yes")
        assert f"0/{len(exercises)}" in _invoke("list").stdout


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


class TestRecoveryFromADeletedFile:
    """Deleting exercise.py used to break every command, including the repair."""

    @staticmethod
    def _delete(sandbox: Path, slug: str) -> Path:
        target = sandbox / "exercises" / slug / "exercise.py"
        target.unlink()
        return target

    def test_the_other_commands_keep_working(self, sandbox: Path) -> None:
        self._delete(sandbox, "01_environment")
        assert _invoke("list").exit_code == 0
        assert _invoke("next").exit_code == 0
        assert _invoke("hint", "1").exit_code == 0

    def test_run_names_the_repair(self, sandbox: Path) -> None:
        self._delete(sandbox, "01_environment")
        result = _invoke("run", "1")
        assert result.exit_code == 1
        assert "does not exist" in result.stdout
        assert "reset" in result.stdout

    def test_reset_actually_repairs_it(self, sandbox: Path) -> None:
        target = self._delete(sandbox, "01_environment")
        assert _invoke("reset", "1", "--yes").exit_code == 0
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == (
            target.with_name("template.py").read_text(encoding="utf-8")
        )

    def test_one_broken_exercise_does_not_block_the_others(self, sandbox: Path) -> None:
        """Break the last exercise, then work on the first. Found by name, not by
        number, so inserting an exercise cannot quietly turn this into a no-op."""
        last = sorted(p.name for p in (sandbox / "exercises").iterdir() if p.is_dir())[-1]
        self._delete(sandbox, last)
        shutil.copyfile(
            sandbox / "exercises" / "01_environment" / "solution.py",
            sandbox / "exercises" / "01_environment" / "exercise.py",
        )
        assert _invoke("run", "1").exit_code == 0

    def test_a_stray_directory_does_not_break_anything(self, sandbox: Path) -> None:
        (sandbox / "exercises" / "my_notes").mkdir()
        assert _invoke("list").exit_code == 0
