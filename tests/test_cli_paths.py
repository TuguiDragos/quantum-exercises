"""The CLI branches no existing test reaches: refusals, failures, and --save-account."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from typer.testing import CliRunner

from quantum_exercises import cli
from quantum_exercises import doctor as doctor_module
from quantum_exercises.backends import OFFLINE_ENV

runner = CliRunner()


@pytest.fixture
def sandbox(tmp_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(root / "exercises", tmp_path / "exercises")
    monkeypatch.setenv("QX_ROOT", str(tmp_path))
    # Isolated from the real saved account, which `qx doctor` reads.
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / "no-account.json")
    return tmp_path


def _invoke(*args: str, **kwargs):
    return runner.invoke(cli.app, list(args), **kwargs)


def _solve_all(sandbox: Path) -> None:
    for directory in (sandbox / "exercises").iterdir():
        if directory.is_dir():
            shutil.copyfile(directory / "solution.py", directory / "exercise.py")


class TestRunGuards:
    @pytest.mark.parametrize("value", ["0", "-5"])
    def test_non_positive_timeout_is_refused(self, sandbox: Path, value: str) -> None:
        result = _invoke("run", "1", "--timeout", value)
        assert result.exit_code == 2
        assert "positive number of seconds" in result.stdout

    def test_finishing_the_last_exercise_says_so(self, sandbox: Path) -> None:
        _solve_all(sandbox)
        exercises = sorted(p.name for p in (sandbox / "exercises").iterdir() if p.is_dir())
        for slug in exercises[:-1]:
            _invoke("run", slug)
        result = _invoke("run", exercises[-1])
        assert "That was the last one" in result.stdout

    def test_passing_one_that_was_already_done_says_nothing_about_what_is_next(
        self, sandbox: Path
    ) -> None:
        shutil.copyfile(
            sandbox / "exercises" / "01_environment" / "solution.py",
            sandbox / "exercises" / "01_environment" / "exercise.py",
        )
        first = _invoke("run", "1")
        assert "next  02 Counts is just a dictionary, with qx next" in first.stdout

        again = _invoke("run", "1")
        assert again.exit_code == 0
        assert "PASS" in again.stdout
        assert "next  " not in again.stdout

    def test_run_with_everything_complete_exits_zero(self, sandbox: Path) -> None:
        _solve_all(sandbox)
        for slug in sorted(p.name for p in (sandbox / "exercises").iterdir() if p.is_dir()):
            _invoke("run", slug)
        result = _invoke("run")
        assert result.exit_code == 0
        assert "Every exercise is complete" in result.stdout


class TestHintGuards:
    def test_exercise_without_hints(self, sandbox: Path) -> None:
        (sandbox / "exercises" / "01_environment" / "hints.md").unlink()
        result = _invoke("hint", "1")
        assert result.exit_code == 0
        assert "has no hints" in result.stdout

    def test_an_exercise_that_lost_a_hint_does_not_crash(self, sandbox: Path) -> None:
        import json

        hints = sandbox / "exercises" / "01_environment" / "hints.md"
        hints.write_text(hints.read_text(encoding="utf-8").split("## Hint 3")[0], encoding="utf-8")
        (sandbox / ".qx-state.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "exercises": {"01_environment": {"status": "todo", "hints_revealed": 3}},
                }
            ),
            encoding="utf-8",
        )

        result = _invoke("hint", "1")
        assert result.exit_code == 0, result.output
        assert result.exception is None
        assert "hint 2 of 2" in result.stdout
        assert "That was the last hint" in result.stdout

    def test_a_hint_added_after_all_were_revealed_shows_up(self, sandbox: Path) -> None:
        hints = sandbox / "exercises" / "01_environment" / "hints.md"
        _invoke("hint", "1", "--all")
        hints.write_text(
            hints.read_text(encoding="utf-8") + "\n## Hint 4\n\nOne the release added.\n",
            encoding="utf-8",
        )

        result = _invoke("hint", "1")

        assert result.exit_code == 0, result.output
        assert "hint 4 of 4" in result.stdout
        assert "One the release added." in result.stdout


class TestHardwareConfirmation:
    """Whether a run may reach a QPU, and the longer time limit a confirmed one needs."""

    @staticmethod
    def _peek(monkeypatch, queue) -> None:
        # conftest sets QX_OFFLINE, which would answer before the queue is consulted.
        monkeypatch.delenv(OFFLINE_ENV, raising=False)
        monkeypatch.setattr("quantum_exercises.backends.queue_peek", lambda **k: queue)
        # The seam rather than sys.stdin: CliRunner swaps the stream during an invoke.
        monkeypatch.setattr(cli, "_interactive", lambda: True)

    def test_a_simulator_exercise_is_never_interrupted(self, sandbox: Path, monkeypatch) -> None:
        """Only the hardware exercise has anything to ask about."""
        asked = []
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
        _invoke("run", "1")
        assert asked == []

    def test_a_simulator_exercise_is_always_allowed(self, sandbox: Path) -> None:
        """Nothing is fenced off for an exercise that cannot reach IBM anyway."""
        simulator = next(e for e in _all_exercises(sandbox) if not e.hardware)
        assert cli._confirm_hardware(simulator) == cli._HardwareDecision(allowed=True, window=None)

    def test_a_pipe_is_never_asked_and_never_sends(
        self, sandbox: Path, monkeypatch, capsys
    ) -> None:
        asked = []
        monkeypatch.delenv(OFFLINE_ENV, raising=False)
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False, raising=False)

        decision = cli._confirm_hardware(_hardware_exercise(sandbox))

        assert decision.allowed is False
        assert decision.window is None
        assert asked == []
        # One word: "local simulator" can wrap across lines in a narrow pane.
        assert "simulator" in capsys.readouterr().out, "silence would look like a QPU run"

    def test_stdin_that_cannot_answer_at_all_is_not_a_terminal(self, monkeypatch) -> None:
        """A closed or absent stdin raises on isatty rather than returning False."""

        class Closed:
            def isatty(self) -> bool:
                raise ValueError("I/O operation on closed file")

        monkeypatch.setattr(cli.sys, "stdin", Closed())
        assert cli._interactive() is False
        monkeypatch.setattr(cli.sys, "stdin", None)
        assert cli._interactive() is False

    def test_a_terminal_is_recognised_as_one(self, monkeypatch) -> None:
        class Terminal:
            def isatty(self) -> bool:
                return True

        monkeypatch.setattr(cli.sys, "stdin", Terminal())
        assert cli._interactive() is True

    def test_offline_settles_it_without_a_word(self, sandbox: Path, monkeypatch, capsys) -> None:
        """QX_OFFLINE already answered. Saying so on every CI run would be noise."""
        monkeypatch.setenv(OFFLINE_ENV, "1")
        decision = cli._confirm_hardware(_hardware_exercise(sandbox))
        assert decision.allowed is False
        assert capsys.readouterr().out == ""

    def test_the_queue_and_a_link_are_shown_before_the_question(
        self, sandbox: Path, monkeypatch, capsys
    ) -> None:
        from quantum_exercises.backends import Queue

        self._peek(monkeypatch, Queue("ibm_marrakesh", 6))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)

        decision = cli._confirm_hardware(_hardware_exercise(sandbox))
        shown = capsys.readouterr().out
        assert "ibm_marrakesh" in shown
        assert "6 job" in shown
        assert cli.COMPUTERS_URL in shown
        assert decision.allowed is True
        assert decision.window == cli.HARDWARE_WINDOW_SECONDS
        assert decision.window == 3 * 60 * 60, "the window has to outlast a real queue"

    def test_no_leaves_everything_untouched(self, sandbox: Path, monkeypatch) -> None:
        from quantum_exercises.backends import Queue

        self._peek(monkeypatch, Queue("ibm_marrakesh", 400))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: False)

        with pytest.raises(cli.typer.Exit) as exit_info:
            cli._confirm_hardware(_hardware_exercise(sandbox))
        assert exit_info.value.exit_code == 0, "declining is not a failure"

    def test_a_queue_that_cannot_be_read_fails_closed(
        self, sandbox: Path, monkeypatch, capsys
    ) -> None:
        """queue_peek answers None on any failure, which must not read as consent."""
        asked = []
        self._peek(monkeypatch, None)
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))

        decision = cli._confirm_hardware(_hardware_exercise(sandbox))

        assert decision.allowed is False, "a peek that failed cannot stand in for a yes"
        assert decision.window is None
        assert asked == []
        assert "simulator" in capsys.readouterr().out


class TestHardwareWiring:
    """The answer has to reach the run. Asking and then ignoring it is worse than not asking."""

    @staticmethod
    def _record(monkeypatch) -> dict:
        """Stop at run_exercise and keep the arguments it was called with."""
        from quantum_exercises.runner import RunResult

        recorded: dict = {}

        def fake(exercise, **kwargs):
            recorded.update(kwargs)
            return RunResult(outcome="fail", message="stopped before running anything")

        monkeypatch.setattr(cli, "run_exercise", fake)
        return recorded

    def test_a_confirmed_run_carries_both_the_permission_and_the_window(
        self, sandbox: Path, monkeypatch
    ) -> None:
        from quantum_exercises.backends import Queue

        recorded = self._record(monkeypatch)
        TestHardwareConfirmation._peek(monkeypatch, Queue("ibm_marrakesh", 2))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)

        _invoke("run", "14")

        assert recorded["allow_hardware"] is True
        assert recorded["timeout"] == cli.HARDWARE_WINDOW_SECONDS

    def test_an_explicit_timeout_does_not_waive_the_question(
        self, sandbox: Path, monkeypatch
    ) -> None:
        from quantum_exercises.backends import Queue

        asked = []
        recorded = self._record(monkeypatch)
        TestHardwareConfirmation._peek(monkeypatch, Queue("ibm_marrakesh", 2))

        def confirm(*args, **kwargs) -> bool:
            asked.append(True)
            return True

        monkeypatch.setattr(cli.typer, "confirm", confirm)

        _invoke("run", "14", "--timeout", "30")

        assert asked == [True], "the question has to be put even with an explicit limit"
        assert recorded["timeout"] == 30, "the reader's own limit wins over the queue window"
        assert recorded["allow_hardware"] is True

    def test_the_wait_that_is_announced_is_the_wait_that_happens(
        self, sandbox: Path, monkeypatch, capsys
    ) -> None:
        from quantum_exercises.backends import Queue

        self._record(monkeypatch)
        TestHardwareConfirmation._peek(monkeypatch, Queue("ibm_marrakesh", 2))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)

        result = _invoke("run", "14", "--timeout", "30")
        # Whitespace collapsed, so a line break cannot split the number from its unit.
        said = " ".join(result.stdout.split())

        assert "30 seconds" in said
        assert "3 hours" not in said, "it announced a wait it was not going to make"

    def test_a_confirmed_run_with_no_limit_of_its_own_announces_the_queue_window(
        self, sandbox: Path, monkeypatch
    ) -> None:
        from quantum_exercises.backends import Queue

        self._record(monkeypatch)
        TestHardwareConfirmation._peek(monkeypatch, Queue("ibm_marrakesh", 2))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)

        said = " ".join(_invoke("run", "14").stdout.split())

        assert f"up to {cli.HARDWARE_WINDOW_SECONDS // 3600} hours" in said
        assert "Ctrl-C stops waiting, not the job" in said

    def test_ctrl_c_at_the_question_sends_nothing(self, sandbox: Path, monkeypatch) -> None:
        """typer raises Abort, which must exit cleanly with nothing submitted."""
        from quantum_exercises.backends import Queue

        recorded = self._record(monkeypatch)
        TestHardwareConfirmation._peek(monkeypatch, Queue("ibm_marrakesh", 2))

        def interrupted(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(cli.typer, "confirm", interrupted)

        result = _invoke("run", "14")

        assert result.exit_code != 0
        assert recorded == {}, "the exercise must not have been run at all"

    def test_a_run_nobody_confirmed_is_not_allowed_hardware(
        self, sandbox: Path, monkeypatch
    ) -> None:
        recorded = self._record(monkeypatch)
        monkeypatch.delenv(OFFLINE_ENV, raising=False)
        monkeypatch.setattr(cli, "_interactive", lambda: False)

        _invoke("run", "14")

        assert recorded["allow_hardware"] is False
        assert recorded["timeout"] is None, "the exercise keeps its own limit"


def _all_exercises(sandbox: Path):
    from quantum_exercises.registry import load_exercises

    return load_exercises(sandbox)


def _hardware_exercise(sandbox: Path):
    return next(e for e in _all_exercises(sandbox) if e.hardware)


class TestDamagedProgressFile:
    """A damaged progress file starts fresh, and says so."""

    def test_every_command_says_the_file_could_not_be_read(self, sandbox: Path) -> None:
        (sandbox / ".qx-state.json").write_text("{ not json at all", encoding="utf-8")
        for command in (["list"], ["next"], ["hint", "1"]):
            result = _invoke(*command)
            assert result.exit_code == 0, result.output
            assert "could not be read" in result.stdout, f"qx {' '.join(command)} said nothing"
            assert "has not been touched" in result.stdout

    def test_a_healthy_file_says_nothing(self, sandbox: Path) -> None:
        import json

        (sandbox / ".qx-state.json").write_text(
            json.dumps({"version": 1, "exercises": {}}), encoding="utf-8"
        )
        assert "could not be read" not in _invoke("list").stdout


class TestOptionHelp:
    """A flag's surprising effects belong in its help."""

    @staticmethod
    def _help(*args: str) -> str:
        """Help text with the wrapping taken out: typer breaks it across the box."""
        return " ".join(_invoke(*args, "--help").stdout.replace("│", " ").split()).lower()

    def test_timeout_names_its_unit(self) -> None:
        assert "in seconds" in self._help("run")

    def test_the_solution_flag_admits_it_records_nothing(self) -> None:
        assert "records no progress" in self._help("run")

    def test_the_top_level_help_says_how_to_reach_hardware(self) -> None:
        top = self._help()
        assert "cloud.ibm.com/iam/apikeys" in top, "nothing says where a key comes from"
        assert "--save-account" in top
        assert "--online" in top
        assert "qx next" in top, "nothing says where to begin"


class TestSolutionAndResetRefusals:
    def test_declining_the_solution_reveals_nothing(self, sandbox: Path) -> None:
        result = _invoke("solution", "1", input="n\n")
        assert result.exit_code == 0
        assert "Nothing revealed" in result.stdout
        assert not (sandbox / ".qx-state.json").exists()

    def test_accepting_the_solution_records_it(self, sandbox: Path) -> None:
        result = _invoke("solution", "1", input="y\n")
        assert result.exit_code == 0
        assert "recorded as solved" in result.stdout

    def test_declining_the_reset_changes_nothing(self, sandbox: Path) -> None:
        target = sandbox / "exercises" / "01_environment" / "exercise.py"
        target.write_text("# mine\n", encoding="utf-8")
        result = _invoke("reset", "1", input="n\n")
        assert "Nothing changed" in result.stdout
        assert target.read_text(encoding="utf-8") == "# mine\n"

    def test_reset_without_a_template_is_refused(self, sandbox: Path) -> None:
        (sandbox / "exercises" / "01_environment" / "template.py").unlink()
        result = _invoke("reset", "1", "--yes")
        assert result.exit_code == 2
        assert "has no template.py" in result.stdout

    def test_reset_reports_a_copy_failure(self, sandbox: Path, monkeypatch) -> None:
        def boom(*args, **kwargs):
            raise OSError(13, "Permission denied")

        monkeypatch.setattr(cli.shutil, "copyfile", boom)
        result = _invoke("reset", "1", "--yes")
        assert result.exit_code == 2
        assert "Could not restore" in result.stdout

    def test_reset_warns_when_only_the_bookkeeping_fails(self, sandbox: Path, monkeypatch) -> None:
        monkeypatch.setattr(cli.ui, "save_progress", lambda root, state: False)
        result = _invoke("reset", "1", "--yes")
        assert "still" in result.stdout and "recorded as complete" in result.stdout

    def test_answering_yes_at_the_prompt_restores_the_file(self, sandbox: Path) -> None:
        """--yes has its own tests. This is the reader typing it."""
        target = sandbox / "exercises" / "01_environment" / "exercise.py"
        template = (sandbox / "exercises" / "01_environment" / "template.py").read_text(
            encoding="utf-8"
        )
        target.write_text("# mine\n", encoding="utf-8")

        result = _invoke("reset", "1", input="y\n")

        assert result.exit_code == 0, result.output
        assert "restored to its starting state" in result.stdout
        assert target.read_text(encoding="utf-8") == template

    def test_a_solution_that_could_not_be_recorded_does_not_claim_it_was(
        self, sandbox: Path, monkeypatch
    ) -> None:
        """The answer is on screen either way. Only the bookkeeping failed."""
        monkeypatch.setattr(cli.ui, "save_progress", lambda root, state: False)
        result = _invoke("solution", "1", "--yes")
        assert result.exit_code == 0, result.output
        assert "recorded as solved" not in result.stdout


class TestDoctorBranches:
    def test_outside_a_repository_reports_a_blocking_problem(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("QX_ROOT", str(tmp_path / "nowhere"))
        result = _invoke("doctor")
        assert result.exit_code == 1
        assert "blocking problem" in result.stdout

    def test_fix_lines_are_printed(self, sandbox: Path, monkeypatch) -> None:
        monkeypatch.setattr(
            "quantum_exercises.doctor.run_checks",
            lambda root, online=False: [
                doctor_module.Check("Thing", "warn", "not there", "Install the thing.")
            ],
        )
        result = _invoke("doctor")
        assert "Install the thing." in result.stdout
        assert result.exit_code == 0


class TestDoctorOnlineFlag:
    """`--online` decides whether IBM is contacted, so cli.py must pass it through."""

    @staticmethod
    def _fake_service(monkeypatch) -> None:
        module = ModuleType("qiskit_ibm_runtime")
        module.QiskitRuntimeService = lambda *a, **k: SimpleNamespace(
            backends=lambda **k: [SimpleNamespace(name="ibm_probe", num_qubits=156)]
        )
        monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

    def test_the_flag_reaches_the_checks(self, sandbox: Path, monkeypatch) -> None:
        self._fake_service(monkeypatch)
        result = _invoke("doctor", "--online")
        assert result.exit_code == 0, result.output
        assert "IBM Quantum connection" in result.stdout
        assert "ibm_probe" in result.stdout

    def test_without_the_flag_nothing_is_contacted(self, sandbox: Path, monkeypatch) -> None:
        def explode(*args, **kwargs):
            raise AssertionError("plain `qx doctor` must never reach the network")

        module = ModuleType("qiskit_ibm_runtime")
        module.QiskitRuntimeService = explode
        monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

        result = _invoke("doctor")
        assert result.exit_code == 0, result.output
        assert "IBM Quantum connection" not in result.stdout

    def test_the_account_row_stops_pointing_at_the_command_just_run(
        self, sandbox: Path, monkeypatch, tmp_path: Path
    ) -> None:
        """Printed directly above the answer, that pointer sends the reader in a circle."""
        self._fake_service(monkeypatch)
        account = tmp_path / "qiskit-ibm.json"
        account.write_text(
            '{"default": {"channel": "ibm_quantum_platform"}}',
            encoding="utf-8",
        )
        account.chmod(0o600)
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", account)

        assert "doctor --online` does that" in _invoke("doctor").stdout
        assert "doctor --online` does that" not in _invoke("doctor", "--online").stdout


class TestVersionCommand:
    def test_absent_package_is_reported(self, monkeypatch) -> None:
        import importlib.metadata as md

        def missing(name):
            raise md.PackageNotFoundError(name)

        monkeypatch.setattr(md, "version", missing)
        result = _invoke("version")
        assert "not installed" in result.stdout


class TestWatchCommand:
    def test_watch_delegates_to_the_watcher(self, sandbox: Path, monkeypatch) -> None:
        seen: dict = {}

        def fake(exercise, *, root, exercises):
            seen["slug"] = exercise.slug

        monkeypatch.setattr("quantum_exercises.watch.watch_exercise", fake)
        assert _invoke("watch", "3").exit_code == 0
        assert seen["slug"] == "03_first_circuit"


class TestSaveAccount:
    @staticmethod
    def _fake_runtime(monkeypatch, saver) -> None:
        module = ModuleType("qiskit_ibm_runtime")
        module.QiskitRuntimeService = SimpleNamespace(save_account=saver)
        monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

    def test_empty_token_saves_nothing(self, monkeypatch) -> None:
        calls = []
        self._fake_runtime(monkeypatch, lambda **kw: calls.append(kw))
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "   ")

        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 1
        assert "nothing was saved" in result.stdout
        assert calls == []

    def test_a_token_is_saved_and_never_echoed(self, tmp_path: Path, monkeypatch) -> None:
        calls = []
        self._fake_runtime(monkeypatch, lambda **kw: calls.append(kw))
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "SECRET-TOKEN-123")
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")

        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 0
        assert "Account saved" in result.stdout
        assert "SECRET-TOKEN-123" not in result.stdout
        assert calls[0]["token"] == "SECRET-TOKEN-123"
        assert calls[0]["channel"] == "ibm_quantum_platform"

    def test_permissions_that_cannot_be_tightened_are_reported(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The key is saved either way, so loose permissions warn rather than fail."""
        self._fake_runtime(monkeypatch, lambda **kw: None)
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "tok")
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")
        monkeypatch.setattr(cli, "_restrict_credentials_permissions", lambda: False)

        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 0
        assert "Account saved" in result.stdout
        assert "Could not restrict permissions" in result.stdout

    def test_the_instance_prompt_says_what_skipping_it_means(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        prompts: list[str] = []
        self._fake_runtime(monkeypatch, lambda **kw: None)
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "tok")
        monkeypatch.setattr("builtins.input", lambda prompt="": prompts.append(prompt) or "")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")

        result = _invoke("doctor", "--save-account")
        assert "optional" in prompts[0].lower()
        assert "optional" in result.stdout.lower()
        assert "several" in result.stdout

    def test_an_instance_crn_is_passed_through(self, tmp_path: Path, monkeypatch) -> None:
        calls = []
        self._fake_runtime(monkeypatch, lambda **kw: calls.append(kw))
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "tok")
        monkeypatch.setattr("builtins.input", lambda prompt="": "crn:v1:bluemix:public")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")

        _invoke("doctor", "--save-account")
        assert calls[0]["instance"] == "crn:v1:bluemix:public"

    def test_a_save_failure_is_reported_without_a_traceback(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        def boom(**kwargs):
            raise RuntimeError("service refused")

        self._fake_runtime(monkeypatch, boom)
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "tok")
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")

        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 1
        assert "Could not save the account" in result.stdout
        assert "service refused" in result.stdout

    def test_an_echoing_terminal_refuses_to_read_the_key(self, monkeypatch) -> None:
        """getpass warns when it cannot hide input; the key must not be read at all."""
        import getpass as getpass_module

        calls = []
        self._fake_runtime(monkeypatch, lambda **kw: calls.append(kw))

        def warns(prompt=""):
            import warnings

            warnings.warn("Can not control echo", getpass_module.GetPassWarning, stacklevel=1)
            return "leaked-token"

        monkeypatch.setattr("getpass.getpass", warns)

        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 1
        assert "cannot hide what you type" in result.stdout
        assert calls == []

    def test_missing_runtime_package_is_reported(self, monkeypatch) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "qiskit_ibm_runtime":
                raise ImportError("no module")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = _invoke("doctor", "--save-account")
        assert result.exit_code == 1
        assert "qiskit-ibm-runtime is not installed" in result.stdout


class TestEntryPoint:
    def test_main_is_callable(self, monkeypatch) -> None:
        called = []
        monkeypatch.setattr(cli, "app", lambda: called.append(True))
        cli.main()
        assert called == [True]

    def test_the_module_runs_as_a_script(self) -> None:
        """The fallback when `qx` is not on PATH, relying on the `__main__` guard in cli.py."""
        import subprocess

        finished = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, "-m", "quantum_exercises.cli", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stderr
        assert "quantum-exercises" in finished.stdout


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
def test_prepare_credentials_file_creates_it_owner_only(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises import cli

    target = tmp_path / ".qiskit" / "qiskit-ibm.json"
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", target)

    assert cli._prepare_credentials_file() is True
    assert target.read_text(encoding="utf-8") == "{}"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_tightening_permissions_on_a_file_that_is_not_there_is_not_a_failure(
    tmp_path: Path, monkeypatch
) -> None:
    """Nothing to tighten is not a failure, so no warning about a loose key."""
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / "gone" / "qiskit-ibm.json")
    assert cli._restrict_credentials_permissions() is True


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
def test_prepare_does_not_truncate_an_existing_file(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises import cli

    target = tmp_path / ".qiskit" / "qiskit-ibm.json"
    target.parent.mkdir(parents=True)
    target.write_text('{"default": {}}', encoding="utf-8")
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", target)

    assert cli._prepare_credentials_file() is True
    assert target.read_text(encoding="utf-8") == '{"default": {}}'


def test_prepare_reports_failure(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises import cli

    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / "x" / "creds.json")
    monkeypatch.setattr(cli.Path, "mkdir", lambda *a, **k: (_ for _ in ()).throw(OSError("denied")))
    assert cli._prepare_credentials_file() is False


@pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
def test_restrict_permissions_tightens_both(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises import cli

    target = tmp_path / ".qiskit" / "qiskit-ibm.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")
    target.chmod(0o644)
    target.parent.chmod(0o755)
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", target)

    assert cli._restrict_credentials_permissions() is True
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700


def test_restrict_reports_failure(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises import cli

    target = tmp_path / "creds.json"
    target.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", target)
    monkeypatch.setattr(cli.os, "chmod", lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
    assert cli._restrict_credentials_permissions() is False


class TestTyperChrome:
    """Typer draws --help and usage errors itself, so it must match our styling."""

    def test_every_panel_typer_draws_has_square_corners(self) -> None:
        from rich import box
        from typer import rich_utils

        panel = rich_utils.Panel("body")
        assert panel.box is box.SQUARE

    def test_an_explicit_box_still_wins(self) -> None:
        """setdefault, not an override: a caller asking for a box must get it."""
        from rich import box
        from typer import rich_utils

        assert rich_utils.Panel("body", box=box.HEAVY).box is box.HEAVY

    def test_no_style_typer_prints_names_a_colour_outside_the_palette(self) -> None:
        from typer import rich_utils

        from quantum_exercises import theme

        allowed = {
            theme.ACCENT,
            theme.TEXT,
            theme.TEXT_DIM,
            theme.MUTED,
            theme.OUTLINE,
            theme.BACKGROUND,
            theme.SURFACE,
        }
        for name in dir(rich_utils):
            if not name.startswith("STYLE_"):
                continue
            value = getattr(rich_utils, name)
            if not isinstance(value, str) or not value:
                continue
            words = [w for w in value.split() if w not in ("bold", "italic", "dim", "on")]
            for word in words:
                assert word in allowed, f"{name} = {value!r} names {word!r}"

    def test_the_help_suggestion_is_not_left_blue(self) -> None:
        from typer import rich_utils

        from quantum_exercises import theme

        assert "[blue]" not in rich_utils.RICH_HELP
        assert theme.ACCENT in rich_utils.RICH_HELP
        # The placeholders survive, or the sentence formats into a traceback.
        assert "{command_path}" in rich_utils.RICH_HELP
        assert "{help_option}" in rich_utils.RICH_HELP

    def test_a_mistyped_option_is_answered_with_the_option_itself(self) -> None:
        result = _invoke("--online")
        assert result.exit_code == 2
        assert "No such option: --online" in result.output
        assert "Usage: qx" in result.output
        assert "--help" in result.output

    def test_typer_renders_in_the_same_colour_system_as_the_rest(self) -> None:
        """Not cosmetic: rich shares one cached Style object across consoles.

        Whichever console renders first fixes the ANSI codes for every later print.
        """
        from typer import rich_utils

        from quantum_exercises import ui

        assert ui.console.color_system == rich_utils.COLOR_SYSTEM

    def test_the_trap_that_makes_the_guard_above_necessary(self) -> None:
        """Reproduces rich's Style caching. If this fails, the guard can be relaxed."""
        from rich.color import ColorSystem
        from rich.style import Style

        from quantum_exercises import theme

        Style.parse.cache_clear()
        try:
            first = Style.parse(theme.ACCENT)
            assert Style.parse(theme.ACCENT) is first, "one object per colour, for every console"

            narrow = first.render("x", color_system=ColorSystem.STANDARD)
            wide = first.render("x", color_system=ColorSystem.TRUECOLOR)
            assert wide == narrow, (
                "rich no longer freezes a Style's codes; the colour system guard "
                "above is no longer load bearing"
            )
        finally:
            # Or every later assertion on exact codes inherits what was just cached.
            Style.parse.cache_clear()
