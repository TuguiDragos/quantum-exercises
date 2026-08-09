"""Exercise discovery and lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from quantum_exercises import registry
from quantum_exercises.registry import (
    DEFAULT_TIMEOUT,
    Exercise,
    RegistryError,
    find_project_root,
    load_exercise,
    load_exercises,
    load_hints,
    resolve,
)


def _write_exercise(base: Path, name: str, *, meta: str | None = None) -> Path:
    path = base / name
    path.mkdir(parents=True)
    (path / "exercise.py").write_text("qc = None\n", encoding="utf-8")
    (path / "solution.py").write_text("qc = 1\n", encoding="utf-8")
    (path / "check.py").write_text("def check(mod):\n    return None\n", encoding="utf-8")
    (path / "meta.toml").write_text(
        meta if meta is not None else 'title = "T"\nact = "Act I"\nsummary = "S"\n',
        encoding="utf-8",
    )
    return path


class TestDiscovery:
    def test_finds_every_exercise(self, exercises: list[Exercise], root: Path) -> None:
        # Derived from disk, so adding an exercise does not fail this test.
        on_disk = [p for p in (root / "exercises").iterdir() if p.is_dir()]
        assert len(exercises) == len(on_disk)
        assert exercises[0].slug == "01_environment"
        assert exercises[-1].number == len(exercises)

    def test_ordered_by_number(self, exercises: list[Exercise]) -> None:
        assert [e.number for e in exercises] == sorted(e.number for e in exercises)

    def test_qx_root_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        _write_exercise(tmp_path / "exercises", "01_demo")
        monkeypatch.setenv("QX_ROOT", str(tmp_path))
        assert find_project_root() == tmp_path.resolve()

    def test_qx_root_without_exercises_dir_is_an_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QX_ROOT", str(tmp_path))
        with pytest.raises(RegistryError, match="no exercises/ directory"):
            find_project_root()

    @pytest.mark.parametrize("contents", [[], ["algebra"], ["chapter_one", "notes"]])
    def test_an_unrelated_exercises_directory_does_not_hijack_the_search(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, root: Path, contents: list[str]
    ) -> None:
        """A plain `~/exercises` used to swallow the search from anywhere beneath it.

        The walk stopped at the first directory merely named `exercises`, reported
        "No exercises found" and advised running from inside the repository, which
        is where the reader already was. It also made the installed-package
        fallback below unreachable for anyone owning such a directory.
        """
        monkeypatch.delenv("QX_ROOT", raising=False)
        decoy = tmp_path / "exercises"
        decoy.mkdir()
        for name in contents:
            (decoy / name).mkdir()

        # Nothing that looks like a curriculum sits anywhere above this.
        start = tmp_path / "some" / "working" / "directory"
        start.mkdir(parents=True)

        found = find_project_root(start)
        assert found != tmp_path.resolve(), "the decoy captured the search"
        assert found == root, "the installed-package fallback should have answered"

    def test_a_directory_holding_real_exercises_is_a_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("QX_ROOT", raising=False)
        _write_exercise(tmp_path / "exercises", "01_demo")
        assert find_project_root(tmp_path) == tmp_path.resolve()


class TestMalformedExercises:
    def test_bad_directory_name(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "not_numbered")
        with pytest.raises(RegistryError, match="not a valid exercise directory name"):
            load_exercise(path)

    def test_missing_check_file(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo")
        (path / "check.py").unlink()
        with pytest.raises(RegistryError, match="missing check.py"):
            load_exercise(path)

    def test_missing_meta_keys(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo", meta='title = "only"\n')
        with pytest.raises(RegistryError, match="missing keys"):
            load_exercise(path)

    def test_invalid_toml(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo", meta="title = = =\n")
        with pytest.raises(RegistryError, match="not valid TOML"):
            load_exercise(path)

    def test_duplicate_numbers(self, tmp_path: Path) -> None:
        base = tmp_path / "exercises"
        _write_exercise(base, "01_one")
        _write_exercise(base, "01_two")
        with pytest.raises(RegistryError, match="Duplicate exercise numbers"):
            load_exercises(tmp_path)

    def test_default_timeout_applied(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo")
        assert load_exercise(path).timeout == DEFAULT_TIMEOUT


class TestResolve:
    def test_by_number(self, exercises: list[Exercise]) -> None:
        assert resolve("3", exercises).slug == "03_first_circuit"

    def test_by_slug(self, exercises: list[Exercise]) -> None:
        assert resolve("03_first_circuit", exercises).number == 3

    def test_by_unique_fragment(self, exercises: list[Exercise]) -> None:
        expected = next(e for e in exercises if "bell" in e.slug)
        assert resolve("bell", exercises) is expected

    def test_ambiguous_fragment(self, exercises: list[Exercise]) -> None:
        with pytest.raises(RegistryError, match="matches several"):
            resolve("e", exercises)

    def test_unknown_number(self, exercises: list[Exercise]) -> None:
        with pytest.raises(RegistryError, match="no exercise number 99"):
            resolve("99", exercises)

    def test_unknown_name(self, exercises: list[Exercise]) -> None:
        with pytest.raises(RegistryError, match="No exercise matches"):
            resolve("zzzz", exercises)


class TestHints:
    def test_three_hints_per_exercise(self, exercises: list[Exercise]) -> None:
        for exercise in exercises:
            assert len(load_hints(exercise)) == 3, exercise.slug

    def test_missing_hints_file_is_not_an_error(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo")
        assert load_hints(load_exercise(path)) == []


class TestNumericLookup:
    def test_superscript_digits_do_not_crash(self, exercises: list[Exercise]) -> None:
        """'²'.isdigit() is True but int('²') raises, which used to escape as a traceback."""
        with pytest.raises(RegistryError, match="No exercise matches"):
            resolve("²", exercises)

    def test_plain_digits_still_work(self, exercises: list[Exercise]) -> None:
        assert resolve("1", exercises).number == 1


def test_holds_exercises_survives_an_unreadable_directory(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "exercises").mkdir()
    monkeypatch.setattr(
        Path, "iterdir", lambda self: (_ for _ in ()).throw(OSError("permission denied"))
    )
    assert registry._holds_exercises(tmp_path) is False


def test_find_project_root_gives_up_with_guidance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("QX_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(registry, "_holds_exercises", lambda directory: False)
    with pytest.raises(registry.RegistryError, match="Could not find the exercises"):
        registry.find_project_root()


def test_qx_root_without_an_exercises_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QX_ROOT", str(tmp_path))
    with pytest.raises(registry.RegistryError, match="no exercises/ directory"):
        registry.find_project_root()


def test_missing_meta_is_named(tmp_path: Path) -> None:
    directory = tmp_path / "01_probe"
    directory.mkdir()
    with pytest.raises(registry.RegistryError, match="missing meta.toml"):
        registry.load_exercise(directory)


def test_empty_exercises_directory(tmp_path: Path) -> None:
    (tmp_path / "exercises").mkdir()
    with pytest.raises(registry.RegistryError, match="No exercises found"):
        registry.load_exercises(tmp_path)


def test_no_exercises_directory_at_all(tmp_path: Path) -> None:
    with pytest.raises(registry.RegistryError, match="No exercises directory"):
        registry.load_exercises(tmp_path)


def test_duplicate_numbers_are_rejected(tmp_path: Path, root: Path) -> None:
    import shutil

    base = tmp_path / "exercises"
    base.mkdir()
    source = root / "exercises" / "01_environment"
    shutil.copytree(source, base / "01_environment")
    shutil.copytree(source, base / "01_duplicate")
    with pytest.raises(registry.RegistryError, match="Duplicate exercise numbers"):
        registry.load_exercises(tmp_path)


class TestStrayDirectories:
    """A folder a learner leaves in exercises/ used to break every command."""

    @pytest.mark.parametrize("name", ["my_notes", "__pycache__", "scratch", ".hidden"])
    def test_a_directory_that_is_not_an_exercise_is_skipped(
        self, tmp_path: Path, name: str
    ) -> None:
        base = tmp_path / "exercises"
        _write_exercise(base, "01_demo")
        (base / name).mkdir()
        assert [e.slug for e in load_exercises(tmp_path)] == ["01_demo"]

    def test_a_loose_file_is_skipped(self, tmp_path: Path) -> None:
        base = tmp_path / "exercises"
        _write_exercise(base, "01_demo")
        (base / "README.txt").write_text("notes\n", encoding="utf-8")
        assert len(load_exercises(tmp_path)) == 1

    def test_a_misnamed_exercise_still_raises_rather_than_vanishing(self, tmp_path: Path) -> None:
        """Carrying a meta.toml is what marks it as a broken exercise, not a stray."""
        base = tmp_path / "exercises"
        _write_exercise(base, "01_demo")
        _write_exercise(base, "3_wrong_prefix")
        with pytest.raises(RegistryError, match="not a valid exercise directory name"):
            load_exercises(tmp_path)

    def test_a_hidden_directory_is_skipped_even_with_meta(self, tmp_path: Path) -> None:
        base = tmp_path / "exercises"
        _write_exercise(base, "01_demo")
        _write_exercise(base, ".backup")
        assert [e.slug for e in load_exercises(tmp_path)] == ["01_demo"]


class TestMissingExerciseFile:
    """exercise.py is the learner's file, so losing it must stay recoverable."""

    def test_the_exercise_still_loads(self, tmp_path: Path) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo")
        (path / "exercise.py").unlink()
        assert load_exercise(path).slug == "01_demo"

    def test_the_rest_of_the_course_is_unaffected(self, tmp_path: Path) -> None:
        base = tmp_path / "exercises"
        _write_exercise(base, "01_demo")
        second = _write_exercise(base, "02_other")
        (second / "exercise.py").unlink()
        assert len(load_exercises(tmp_path)) == 2

    @pytest.mark.parametrize("filename", ["solution.py", "check.py"])
    def test_repository_files_are_still_mandatory(self, tmp_path: Path, filename: str) -> None:
        path = _write_exercise(tmp_path / "exercises", "01_demo")
        (path / filename).unlink()
        with pytest.raises(RegistryError, match=f"missing {filename}"):
            load_exercise(path)
