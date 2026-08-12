"""`qx init`, which is how a course reaches someone who installed rather than cloned.

The tool ships the exercises inside the wheel, and this is the command that copies
them somewhere writable. Two properties carry the feature: it never overwrites
anything, so running it again is how a reader picks up an exercise a new release
added, and the bundled copy is never mistaken for the working one.
"""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from quantum_exercises import cli, registry

runner = CliRunner()


def _invoke(*args: str):
    return runner.invoke(cli.app, list(args))


def _fail_writing(monkeypatch: pytest.MonkeyPatch, doomed: Path) -> None:
    """Refuse to replace one particular file, leaving every other write alone.

    The refusal sits on the rename, because that is where a replacement lands: the
    new bytes go to a neighbouring temporary file first. A read-only file would
    stop the backup instead, which is the wrong half, and would behave differently
    on Windows.
    """
    real = cli.os.replace

    def guarded(source, destination, *args, **kwargs):
        if Path(destination) == doomed:
            raise OSError(28, "No space left on device")
        return real(source, destination, *args, **kwargs)

    monkeypatch.setattr(cli.os, "replace", guarded)


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

    def test_standing_in_a_course_means_this_one(self, tmp_path: Path, monkeypatch) -> None:
        """The documented upgrade line is run from inside the course.

        With the default target fixed to a name, it built a second course one
        level down and said the course was ready, while the one the reader was
        standing in went untouched.
        """
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        monkeypatch.chdir(target)
        (target / "exercises" / "01_environment" / "hints.md").write_text("x", encoding="utf-8")

        result = _invoke("init", "--refresh")

        assert not (target / cli.DEFAULT_COURSE_DIR).exists(), "it made a course inside the course"
        assert "up to date" in " ".join(result.stdout.split())

    def test_a_path_whose_parents_do_not_exist_yet_is_made(self, tmp_path: Path) -> None:
        """`qx init work/quantum/course` on a machine with none of those directories."""
        target = tmp_path / "work" / "quantum" / "course"

        assert _invoke("init", str(target)).exit_code == 0
        assert registry.holds_exercises(target)

    def test_a_symlink_to_a_directory_is_followed(self, tmp_path: Path) -> None:
        """A course kept on another disk and linked to from home."""
        real = tmp_path / "elsewhere"
        real.mkdir()
        link = tmp_path / "course"
        link.symlink_to(real, target_is_directory=True)

        assert _invoke("init", str(link)).exit_code == 0
        assert (real / "exercises" / "01_environment").is_dir()


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


class TestTheCourseReadme:
    def test_a_fresh_course_gets_one(self, tmp_path: Path) -> None:
        target = tmp_path / "my-course"
        _invoke("init", str(target))

        said = (target / cli.COURSE_README).read_text(encoding="utf-8")
        assert said.startswith("# Your quantum-exercises course")
        assert f"{registry.EXERCISES_DIR}/" in said
        assert cli.LEARNER_FILE in said

    def test_a_readme_this_command_did_not_write_is_never_replaced(self, tmp_path: Path) -> None:
        """`qx init .` in a clone would otherwise overwrite the project's own README."""
        target = tmp_path / "my-course"
        target.mkdir()
        (target / cli.COURSE_README).write_text("mine\n", encoding="utf-8")

        _invoke("init", str(target))
        _invoke("init", str(target), "--refresh")

        assert (target / cli.COURSE_README).read_text(encoding="utf-8") == "mine\n"

    def test_a_readme_that_is_a_symlink_is_left_where_it_points(self, tmp_path: Path) -> None:
        """Writing through it would land outside the course, as it did for lesson files."""
        outside = tmp_path / "somewhere-else.md"
        outside.write_text("not the course's to write\n", encoding="utf-8")
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        readme = target / cli.COURSE_README
        readme.unlink()
        readme.symlink_to(outside)

        _invoke("init", str(target), "--refresh")

        assert outside.read_text(encoding="utf-8") == "not the course's to write\n"

    def test_one_this_command_wrote_is_brought_up_to_date(self, tmp_path: Path) -> None:
        """Its instructions age with the tool, and a stale one keeps sending people wrong.

        Recognised by the title line, so only a note this command wrote is
        replaced. Everything else there belongs to whoever put it there.
        """
        target = tmp_path / "my-course"
        _invoke("init", str(target))
        readme = target / cli.COURSE_README
        readme.write_text(cli.COURSE_README_TITLE + "\n\nwritten by an older release\n", "utf-8")

        result = _invoke("init", str(target), "--refresh")

        assert readme.read_text(encoding="utf-8") == cli._course_readme_text()
        assert "written by an older release" in (
            readme.with_name(readme.name + cli.BACKUP_SUFFIX).read_text(encoding="utf-8")
        )
        assert cli.COURSE_README in " ".join(result.stdout.split())


class TestRefresh:
    """`--refresh` is how a correction to a lesson reaches a course already copied.

    Plain `qx init` skips anything that is already there, which keeps answers safe
    and also means a fixed `check.py` never arrives. This brings those across while
    keeping the one promise that matters: `exercise.py` is not touched.
    """

    @pytest.fixture
    def target(self, tmp_path: Path) -> Path:
        course = tmp_path / "my-course"
        _invoke("init", str(course))
        return course

    def test_an_edited_lesson_file_is_brought_up_to_date(self, target: Path) -> None:
        hints = target / "exercises" / "01_environment" / "hints.md"
        current = hints.read_text(encoding="utf-8")
        hints.write_text("stale\n", encoding="utf-8")

        result = _invoke("init", str(target), "--refresh")

        assert result.exit_code == 0, result.output
        assert hints.read_text(encoding="utf-8") == current
        assert "exercises/01_environment/hints.md" in " ".join(result.stdout.split())

    def test_what_was_replaced_is_kept_beside_it(self, target: Path) -> None:
        checker = target / "exercises" / "01_environment" / "check.py"
        checker.write_text("# mine\n", encoding="utf-8")

        _invoke("init", str(target), "--refresh")

        backup = checker.with_name(checker.name + cli.BACKUP_SUFFIX)
        assert backup.read_text(encoding="utf-8") == "# mine\n"
        assert checker.read_text(encoding="utf-8") != "# mine\n"

    def test_an_answer_is_never_touched(self, target: Path) -> None:
        """The promise that makes the flag safe to run at any point in the course."""
        mine = target / "exercises" / "01_environment" / cli.LEARNER_FILE
        mine.write_text("qiskit_version = 'mine'\n", encoding="utf-8")
        # Something to actually update, so the run has work to do around the answer.
        (target / "exercises" / "01_environment" / "hints.md").write_text("x", encoding="utf-8")

        result = _invoke("init", str(target), "--refresh")

        assert mine.read_text(encoding="utf-8") == "qiskit_version = 'mine'\n"
        assert not mine.with_name(mine.name + cli.BACKUP_SUFFIX).exists()
        assert cli.LEARNER_FILE in " ".join(result.stdout.split())

    def test_a_deleted_lesson_file_comes_back(self, target: Path) -> None:
        hints = target / "exercises" / "02_dictionaries" / "hints.md"
        hints.unlink()

        _invoke("init", str(target), "--refresh")

        assert hints.is_file()

    def test_a_deleted_answer_stays_deleted(self, target: Path) -> None:
        """`qx reset` restores that one, out of a template.py this does keep current."""
        mine = target / "exercises" / "02_dictionaries" / cli.LEARNER_FILE
        mine.unlink()

        _invoke("init", str(target), "--refresh")

        assert not mine.exists()

    def test_nothing_to_do_says_so(self, target: Path) -> None:
        result = _invoke("init", str(target), "--refresh")
        assert "nothing was copied" in " ".join(result.stdout.split())

    def test_running_it_twice_changes_nothing_the_second_time(self, target: Path) -> None:
        (target / "exercises" / "01_environment" / "README.md").write_text("x", encoding="utf-8")

        first = _invoke("init", str(target), "--refresh")
        second = _invoke("init", str(target), "--refresh")

        assert "up to date" in " ".join(first.stdout.split())
        assert "nothing was copied" in " ".join(second.stdout.split())

    def test_it_reports_what_it_added_and_what_it_replaced_together(self, target: Path) -> None:
        shutil.rmtree(target / "exercises" / "02_dictionaries")
        (target / "exercises" / "01_environment" / "meta.toml").write_text("x", encoding="utf-8")

        said = " ".join(_invoke("init", str(target), "--refresh").stdout.split())

        assert "Added 1" in said and "exercises/02_dictionaries" in said
        assert "up to date" in said and "exercises/01_environment/meta.toml" in said

    def test_bytecode_in_the_template_is_still_left_behind(
        self, course: Path, target: Path
    ) -> None:
        """The skip has to hold at every depth, not just at the top of exercises/."""
        stale = course / registry.EXERCISES_DIR / "01_environment" / "__pycache__"
        stale.mkdir()
        (stale / "check.cpython-313.pyc").write_bytes(b"\x00")
        (course / registry.EXERCISES_DIR / "01_environment" / "check.pyc").write_bytes(b"\x00")

        _invoke("init", str(target), "--refresh")

        assert not list(target.rglob("__pycache__"))
        assert not list(target.rglob("*.pyc"))

    def test_a_run_that_stops_part_way_says_what_it_had_already_done(
        self, target: Path, monkeypatch
    ) -> None:
        """A course left part new, reported as a flat failure, is unreadable.

        The reader has no way to tell whether anything changed, and the honest
        answer is that some of it did. Naming it is also what keeps the promise in
        SECURITY.md that no lesson file is ever replaced silently.
        """
        first = target / "exercises" / "01_environment" / "hints.md"
        later = target / "exercises" / "02_dictionaries" / "hints.md"
        first.write_text("stale\n", encoding="utf-8")
        later.write_text("stale\n", encoding="utf-8")
        _fail_writing(monkeypatch, later)

        result = _invoke("init", str(target), "--refresh")
        said = " ".join(result.stdout.split())

        assert result.exit_code == 2
        assert "exercises/01_environment/hints.md" in said, "the work it did must not vanish"
        assert "run it again" in said
        assert "Could not write the course" in said
        assert first.read_text(encoding="utf-8") != "stale\n"

    def test_a_replacement_that_fails_keeps_both_copies(self, target: Path, monkeypatch) -> None:
        """The one case where an update can destroy work, and it did.

        A plain copy truncates the destination before it writes, so a disk filling
        up part way through left a half written lesson file. The backup was then
        removed, on the reasoning that a failed replacement had not earned one, and
        the learner's edit was gone from both places. Proved on a real full disk.
        """
        hints = target / "exercises" / "01_environment" / "hints.md"
        hints.write_text("hours of my own notes\n", encoding="utf-8")
        _fail_writing(monkeypatch, hints)

        result = _invoke("init", str(target), "--refresh")

        assert result.exit_code == 2
        assert hints.read_text(encoding="utf-8") == "hours of my own notes\n", (
            "the file has to hold the old bytes or the new ones, never half of each"
        )
        assert hints.with_name(hints.name + cli.BACKUP_SUFFIX).exists(), (
            "the backup is the second copy, and a failure is when it is needed"
        )
        assert not list(hints.parent.glob(".qx-refresh-*")), "a temporary file was left behind"

    @pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
    def test_a_refreshed_file_keeps_the_permissions_it_had(self, target: Path) -> None:
        """The replacement writes a neighbour and renames it into place.

        A temporary file is created readable by its owner alone, so the rename
        handed a lesson file 0600 where the rest of the course sits at 0644. On a
        machine where the course is shared read-only with anyone else, a refresh
        would have taken it away from them.
        """
        hints = target / "exercises" / "01_environment" / "hints.md"
        untouched = target / "exercises" / "02_dictionaries" / "hints.md"
        hints.chmod(0o644)
        hints.write_text("stale\n", encoding="utf-8")

        _invoke("init", str(target), "--refresh")

        assert hints.stat().st_mode & 0o777 == untouched.stat().st_mode & 0o777

    def test_a_second_refresh_does_not_write_over_the_first_backup(self, target: Path) -> None:
        """Two rounds of edits, two backups. The first used to be overwritten."""
        hints = target / "exercises" / "01_environment" / "hints.md"

        hints.write_text("the first thing I wrote\n", encoding="utf-8")
        _invoke("init", str(target), "--refresh")
        hints.write_text("the second thing I wrote\n", encoding="utf-8")
        _invoke("init", str(target), "--refresh")

        kept = sorted(p.read_text(encoding="utf-8") for p in hints.parent.glob("hints.md.bak*"))
        assert kept == ["the first thing I wrote\n", "the second thing I wrote\n"]

    def test_a_symlink_in_place_of_a_lesson_file_is_refused(self, target: Path, tmp_path) -> None:
        """Following one writes outside the course, which it did.

        A link left where `hints.md` belongs was enough to overwrite a file
        elsewhere on the machine, and the run reported success.
        """
        outside = tmp_path / "not-mine.txt"
        outside.write_text("someone else's file\n", encoding="utf-8")
        hints = target / "exercises" / "01_environment" / "hints.md"
        hints.unlink()
        hints.symlink_to(outside)

        result = _invoke("init", str(target), "--refresh")
        said = " ".join(result.stdout.split())

        assert outside.read_text(encoding="utf-8") == "someone else's file\n"
        assert "symlink" in said
        assert "exercises/01_environment/hints.md" in said
        assert hints.is_symlink(), "the link itself is the learner's, so it stays"

    def test_a_directory_a_release_adds_inside_an_exercise_arrives(self, course: Path) -> None:
        """The recursion used to copy into a directory it had not made yet."""
        target = course.parent / "with-new-data"
        _invoke("init", str(target))
        added = course / registry.EXERCISES_DIR / "01_environment" / "data"
        added.mkdir()
        (added / "table.csv").write_text("shipped later\n", encoding="utf-8")

        result = _invoke("init", str(target), "--refresh")

        assert result.exit_code == 0, result.output
        assert (target / "exercises" / "01_environment" / "data" / "table.csv").is_file()

    def test_the_names_it_lists_survive_a_narrow_terminal(self, target: Path, monkeypatch) -> None:
        """A path broken across two lines reads as two files, and says nothing.

        The longest label the shipped course produces is over forty characters, so
        this is not a hypothetical width.
        """
        from rich.console import Console

        from quantum_exercises import ui

        console = Console(file=io.StringIO(), width=30)
        monkeypatch.setattr(ui, "console", console)
        checker = target / "exercises" / "02_dictionaries" / "check.py"
        checker.write_text("stale\n", encoding="utf-8")

        _invoke("init", str(target), "--refresh")

        assert "exercises/02_dictionaries/check.py" in console.file.getvalue()

    def test_without_the_flag_none_of_this_happens(self, target: Path) -> None:
        hints = target / "exercises" / "01_environment" / "hints.md"
        hints.write_text("stale\n", encoding="utf-8")

        _invoke("init", str(target))

        assert hints.read_text(encoding="utf-8") == "stale\n"
        assert not hints.with_name(hints.name + cli.BACKUP_SUFFIX).exists()


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
