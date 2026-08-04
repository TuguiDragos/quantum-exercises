"""Exercise discovery and lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

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
