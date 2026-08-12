"""Proof-of-concept coverage for watch.py, the one module with no tests at all.

watchfiles.watch() is a blocking generator, so it is replaced with a scripted one.
That is enough to drive every branch of watch_exercise without real file events.
"""

from __future__ import annotations

import inspect
import shutil
from pathlib import Path

import pytest

from quantum_exercises import watch as watch_module
from quantum_exercises.registry import load_exercises
from quantum_exercises.runner import run_exercise
from quantum_exercises.state import load as load_state


@pytest.fixture
def sandbox(tmp_path: Path, root: Path) -> Path:
    shutil.copytree(root / "exercises", tmp_path / "exercises")
    return tmp_path


def _solve(sandbox: Path, slug: str) -> None:
    directory = sandbox / "exercises" / slug
    shutil.copyfile(directory / "solution.py", directory / "exercise.py")


def _fake_watch(events_per_call: list[list[set]], monkeypatch: pytest.MonkeyPatch) -> list:
    """Replace watchfiles.watch with a generator that yields scripted change sets."""
    calls: list = []

    def fake(path, debounce=0, step=0):
        calls.append(Path(path))
        yield from (events_per_call.pop(0) if events_per_call else [])

    monkeypatch.setattr(watch_module, "watch", fake)
    return calls


class TestWatchedFiles:
    def test_tracks_exercise_and_check(self, sandbox: Path) -> None:
        exercise = load_exercises(sandbox)[0]
        watched = watch_module._watched_files(exercise)
        assert str(exercise.exercise_file.resolve()) in watched
        assert str(exercise.check_file.resolve()) in watched


class TestNextUnfinished:
    def test_returns_the_first_outstanding(self, sandbox: Path) -> None:
        exercises = load_exercises(sandbox)
        assert watch_module._next_unfinished(sandbox, exercises) is exercises[0]

    def test_returns_none_when_all_complete(self, sandbox: Path) -> None:
        exercises = load_exercises(sandbox)
        state = load_state(sandbox)
        for exercise in exercises:
            state.mark_done(exercise.slug)
        from quantum_exercises.state import save

        save(sandbox, state)
        assert watch_module._next_unfinished(sandbox, exercises) is None


class TestHardware:
    """Watch mode re-runs on every save, so it must never be a way onto a QPU."""

    def test_a_watched_run_is_never_allowed_hardware(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """It asks nobody anything, so it has to take the safe default."""
        from quantum_exercises.runner import RunResult

        recorded: dict = {}

        def fake(exercise, **kwargs):
            recorded.update(kwargs)
            return RunResult(outcome="fail", message="not run for real")

        monkeypatch.setattr(watch_module, "run_exercise", fake)
        watch_module._run_and_record(load_exercises(sandbox)[0], sandbox)

        # Two halves, because watch passes nothing and leans on the default. The
        # first assertion alone would be satisfied by its own fallback.
        assert recorded.get("allow_hardware", False) is False
        assert inspect.signature(run_exercise).parameters["allow_hardware"].default is False

    def test_the_hardware_exercise_says_why_it_stays_on_a_simulator(
        self, sandbox: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """The panel names the backend, not the reason this mode could pick no other."""
        hardware = next(e for e in load_exercises(sandbox) if e.hardware)
        watch_module._announce(hardware, sandbox)
        # One word: the console wraps to whatever terminal it finds, and
        # "local simulator" splits across the break in a narrow pane.
        assert "simulator" in capsys.readouterr().out

    def test_a_simulator_exercise_says_nothing_extra(
        self, sandbox: Path, capsys: pytest.CaptureFixture
    ) -> None:
        watch_module._announce(load_exercises(sandbox)[0], sandbox)
        assert "simulator" not in capsys.readouterr().out


class TestRunAndRecord:
    def test_failing_exercise_is_not_recorded(self, sandbox: Path) -> None:
        exercise = load_exercises(sandbox)[0]
        assert watch_module._run_and_record(exercise, sandbox) is False
        assert load_state(sandbox).is_complete(exercise.slug) is False

    def test_passing_exercise_is_recorded(self, sandbox: Path) -> None:
        _solve(sandbox, "01_environment")
        exercise = load_exercises(sandbox)[0]
        assert watch_module._run_and_record(exercise, sandbox) is True
        assert load_state(sandbox).is_complete(exercise.slug) is True


class TestWatchExercise:
    def test_first_pass_advances_without_any_file_event(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An exercise that already passes must move on before watching begins."""
        _solve(sandbox, "01_environment")
        exercises = load_exercises(sandbox)
        calls = _fake_watch([[]], monkeypatch)

        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)

        assert load_state(sandbox).is_complete("01_environment")
        # The watcher was registered on the SECOND exercise, not the first.
        assert calls == [exercises[1].path]

    def test_every_exercise_complete_stops_immediately(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Completion is decided by recorded state, not by what sits on disk."""
        from quantum_exercises.state import save

        exercises = load_exercises(sandbox)
        _solve(sandbox, "01_environment")
        state = load_state(sandbox)
        for exercise in exercises[1:]:
            state.mark_done(exercise.slug)
        save(sandbox, state)
        calls = _fake_watch([[]], monkeypatch)

        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)
        assert calls == []  # never started watching: nothing was left to do

    def test_unrelated_change_is_ignored(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exercises = load_exercises(sandbox)
        noise = {(1, str(exercises[0].path / "README.md"))}
        _fake_watch([[noise]], monkeypatch)

        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)
        assert load_state(sandbox).is_complete("01_environment") is False

    def test_saving_a_correct_answer_passes_and_advances(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exercises = load_exercises(sandbox)
        target = exercises[0].exercise_file

        def fake(path, debounce=0, step=0):
            calls.append(Path(path))
            if len(calls) == 1:
                _solve(sandbox, "01_environment")
                yield {(2, str(target))}

        calls: list = []
        monkeypatch.setattr(watch_module, "watch", fake)

        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)

        assert load_state(sandbox).is_complete("01_environment")
        assert calls[-1] == exercises[1].path  # re-registered on the next exercise

    def test_failing_save_re_announces_and_keeps_watching(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A save that still fails must re-announce rather than advance."""
        exercises = load_exercises(sandbox)
        target = exercises[0].exercise_file
        announced: list = []
        monkeypatch.setattr(watch_module, "_announce", lambda ex, root: announced.append(ex.slug))

        def fake(path, debounce=0, step=0):
            yield {(2, str(target))}

        monkeypatch.setattr(watch_module, "watch", fake)
        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)

        # Announced once on entry, once again after the failing re-run.
        assert announced == ["01_environment", "01_environment"]

    def test_a_pass_that_could_not_be_recorded_stays_on_the_same_exercise(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A read-only clone runs the check happily and cannot write the result.

        The watcher asks the state file what to do next, so it is handed back the
        exercise that just passed. Advancing to it would mean announcing a move to
        where it already is, on every save, for as long as the file stays unwritable.
        """
        _solve(sandbox, "01_environment")
        exercises = load_exercises(sandbox)
        announced: list[str] = []
        monkeypatch.setattr(watch_module, "_announce", lambda ex, root: announced.append(ex.slug))
        monkeypatch.setattr(watch_module.ui, "save_progress", lambda root, state: False)

        def fake(path, debounce=0, step=0):
            yield {(2, str(exercises[0].exercise_file))}

        monkeypatch.setattr(watch_module, "watch", fake)
        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)

        assert announced == ["01_environment", "01_environment"]
        assert load_state(sandbox).is_complete("01_environment") is False

    def test_last_exercise_passing_inside_the_loop_ends_the_session(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from quantum_exercises.state import save

        exercises = load_exercises(sandbox)
        last = exercises[-1]
        state = load_state(sandbox)
        for exercise in exercises[:-1]:
            state.mark_done(exercise.slug)
        save(sandbox, state)

        def fake(path, debounce=0, step=0):
            _solve(sandbox, last.slug)
            yield {(2, str(last.exercise_file))}

        monkeypatch.setattr(watch_module, "watch", fake)
        watch_module.watch_exercise(last, root=sandbox, exercises=exercises)

        assert load_state(sandbox).is_complete(last.slug)

    def test_keyboard_interrupt_exits_cleanly(
        self, sandbox: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        exercises = load_exercises(sandbox)

        def fake(path, debounce=0, step=0):
            raise KeyboardInterrupt
            yield  # pragma: no cover

        monkeypatch.setattr(watch_module, "watch", fake)
        watch_module.watch_exercise(exercises[0], root=sandbox, exercises=exercises)  # must return
