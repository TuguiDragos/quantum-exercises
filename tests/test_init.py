"""`qx init`, which is how a course reaches someone who installed rather than cloned.

The tool ships the exercises inside the wheel, and this is the command that copies
them somewhere writable. Two properties carry the feature: it never overwrites
anything, so running it again is how a reader picks up an exercise a new release
added, and the bundled copy is never mistaken for the working one.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quantum_exercises import cli, registry

runner = CliRunner()


def _invoke(*args: str):
    return runner.invoke(cli.app, list(args))


@pytest.fixture
def course(tmp_path: Path, root: Path) -> Path:
    """A template to copy from, standing in for the one inside a wheel."""
    template = tmp_path / "template"
    (template / registry.EXERCISES_DIR).mkdir(parents=True)
    for slug in ("01_environment", "02_dictionaries"):
        # Without the ignore this picks up whatever bytecode the repository has
        # lying about, which is exactly what one of the tests below puts there on
        # purpose, and it would then be there before that test started.
        shutil.copytree(
            root / "exercises" / slug,
            template / registry.EXERCISES_DIR / slug,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    (template / registry.NOTEBOOKS_DIR).mkdir()
    (template / registry.NOTEBOOKS_DIR / "playground.ipynb").write_text("{}", encoding="utf-8")
    return template


@pytest.fixture(autouse=True)
def bundled(course: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(registry, "BUNDLED_COURSE", course)
    return course


class TestWhereTheTemplateComesFrom:
    def test_the_bundled_course_wins_when_there_is_one(self, course: Path) -> None:
        assert registry.course_template() == course

    def test_a_clone_uses_itself(self, tmp_path: Path, root: Path, monkeypatch) -> None:
        """A checkout carries no bundle, and its own exercises are the template.

        Which is what a contributor wants: `qx init` from a working copy hands
        over the exercises in that working copy, edits included.
        """
        monkeypatch.setattr(registry, "BUNDLED_COURSE", tmp_path / "not-here")
        monkeypatch.setenv("QX_ROOT", str(root))
        assert registry.course_template() == root

    def test_the_bundled_course_is_never_found_by_the_root_search(self, root: Path) -> None:
        """The whole reason it sits below the package directory.

        find_project_root walks up from the package looking for `exercises/` in
        each ancestor. A course nested inside the package is never on that path,
        so an installed read-only copy cannot be picked up as the one to edit.
        Were it beside the package instead, `qx run` would try to check answers in
        site-packages and `qx reset` would try to write there.
        """
        package = Path(registry.__file__).resolve().parent
        for directory in [package, *package.parents]:
            assert not registry.holds_exercises(directory) or directory == root


class TestFirstRun:
    def test_it_copies_the_whole_course(self, tmp_path: Path) -> None:
        target = tmp_path / "my-course"
        result = _invoke("init", str(target))

        assert result.exit_code == 0, result.output
        assert sorted(p.name for p in (target / "exercises").iterdir()) == [
            "01_environment",
            "02_dictionaries",
        ]
        assert (target / "notebooks" / "playground.ipynb").is_file()
        assert (target / "exercises" / "01_environment" / "check.py").is_file()

    def test_the_copy_is_a_course_the_tool_can_find(self, tmp_path: Path) -> None:
        """The point of the command. A directory that discovery does not accept
        would leave the reader with files and no way to run them."""
        target = tmp_path / "my-course"
        _invoke("init", str(target))

        assert registry.holds_exercises(target)
        assert registry.find_project_root(target) == target
        assert len(registry.load_exercises(target)) == 2

    def test_it_says_where_to_go_next(self, tmp_path: Path) -> None:
        result = _invoke("init", str(tmp_path / "my-course"))
        said = " ".join(result.stdout.split())
        assert "2 exercises" in said
        assert "doctor" in said and "next" in said

    def test_an_empty_directory_is_fine(self, tmp_path: Path) -> None:
        target = tmp_path / "empty"
        target.mkdir()
        assert _invoke("init", str(target)).exit_code == 0
        assert (target / "exercises" / "01_environment").is_dir()

    def test_a_default_name_is_used_when_none_is_given(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        assert _invoke("init").exit_code == 0
        assert (tmp_path / cli.DEFAULT_COURSE_DIR / "exercises").is_dir()


class TestRunningItAgain:
    def test_nothing_is_copied_when_the_course_is_complete(self, tmp_path: Path) -> None:
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        result = _invoke("init", str(target))

        assert result.exit_code == 0
        assert "nothing was copied" in " ".join(result.stdout.split())

    def test_an_answer_already_written_is_never_overwritten(self, tmp_path: Path) -> None:
        """The property the whole command rests on.

        A reader upgrades to pick up a new exercise, and the twelve they have
        already solved have to survive it untouched.
        """
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        mine = target / "exercises" / "01_environment" / "exercise.py"
        mine.write_text("qiskit_version = 'mine'\n", encoding="utf-8")

        _invoke("init", str(target))

        assert mine.read_text(encoding="utf-8") == "qiskit_version = 'mine'\n"

    def test_only_what_is_missing_is_added(self, tmp_path: Path) -> None:
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        shutil.rmtree(target / "exercises" / "02_dictionaries")
        (target / "notebooks" / "playground.ipynb").unlink()

        result = _invoke("init", str(target))
        said = " ".join(result.stdout.split())

        assert "Added 2" in said
        assert "exercises/02_dictionaries" in said
        assert "notebooks/playground.ipynb" in said
        assert (target / "exercises" / "02_dictionaries" / "check.py").is_file()


class TestRefusals:
    def test_a_directory_holding_something_else_is_left_alone(self, tmp_path: Path) -> None:
        target = tmp_path / "notes"
        target.mkdir()
        (target / "notes.txt").write_text("mine\n", encoding="utf-8")

        result = _invoke("init", str(target))

        assert result.exit_code == 2
        assert "not a course" in " ".join(result.stdout.split())
        assert (target / "notes.txt").read_text(encoding="utf-8") == "mine\n"
        assert not (target / "exercises").exists()

    def test_a_file_is_refused(self, tmp_path: Path) -> None:
        target = tmp_path / "afile"
        target.write_text("x", encoding="utf-8")

        result = _invoke("init", str(target))

        assert result.exit_code == 2
        assert "is a file" in result.stdout
        assert target.read_text(encoding="utf-8") == "x"

    def test_a_directory_that_cannot_be_read_is_reported(self, tmp_path: Path, monkeypatch) -> None:
        target = tmp_path / "locked"
        target.mkdir()

        def denied(self):
            raise OSError(13, "Permission denied")

        monkeypatch.setattr(Path, "iterdir", denied)
        result = _invoke("init", str(target))

        assert result.exit_code == 2
        assert "Could not read" in result.stdout

    def test_a_copy_that_fails_is_reported_rather_than_raised(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        def boom(*args, **kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(cli.shutil, "copytree", boom)
        result = _invoke("init", str(tmp_path / "my-course"))

        assert result.exit_code == 2
        assert "Could not write the course" in result.stdout

    def test_no_course_anywhere_says_so(self, tmp_path: Path, monkeypatch) -> None:
        """Neither bundled nor cloned, which is not a state a release can be in.

        It is reachable by running a source checkout with the exercises moved
        away, and the message has to name the situation rather than the
        traceback.
        """
        monkeypatch.setattr(registry, "BUNDLED_COURSE", tmp_path / "not-here")
        monkeypatch.setenv("QX_ROOT", str(tmp_path / "also-not-here"))

        result = _invoke("init", str(tmp_path / "my-course"))

        assert result.exit_code == 2
        assert "no course" in " ".join(result.stdout.split())


class TestWhatIsCopied:
    def test_bytecode_and_hidden_files_are_left_behind(self, course: Path, tmp_path: Path) -> None:
        """An in-process import of a check.py leaves __pycache__ in the tree it
        was imported from, and none of that belongs in a fresh course."""
        (course / registry.EXERCISES_DIR / "01_environment" / "__pycache__").mkdir()
        (course / registry.EXERCISES_DIR / "__pycache__").mkdir()
        (course / registry.EXERCISES_DIR / ".DS_Store").write_text("", encoding="utf-8")

        target = tmp_path / "my-course"
        _invoke("init", str(target))

        assert not list(target.rglob("__pycache__"))
        assert not list(target.rglob(".DS_Store"))

    def test_a_missing_part_of_the_template_is_skipped(self, course: Path, tmp_path: Path) -> None:
        """A template with no notebooks still yields a working course."""
        shutil.rmtree(course / registry.NOTEBOOKS_DIR)

        target = tmp_path / "my-course"
        assert _invoke("init", str(target)).exit_code == 0
        assert not (target / registry.NOTEBOOKS_DIR).exists()
        assert registry.holds_exercises(target)
