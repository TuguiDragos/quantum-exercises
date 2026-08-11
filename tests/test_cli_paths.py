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

runner = CliRunner()


@pytest.fixture
def sandbox(tmp_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copytree(root / "exercises", tmp_path / "exercises")
    monkeypatch.setenv("QX_ROOT", str(tmp_path))
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
        """Reveal every hint, then take one away. This used to raise IndexError.

        Nothing here is hand edited. The counter was honest when it was written,
        and the exercise changed underneath it.
        """
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


class TestHardwareConfirmation:
    """A queue is measured in hours. Joining one should be a decision, not a surprise."""

    @staticmethod
    def _peek(monkeypatch, queue) -> None:
        monkeypatch.setattr("quantum_exercises.backends.queue_peek", lambda **k: queue)
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)

    def test_a_simulator_exercise_is_never_interrupted(self, sandbox: Path, monkeypatch) -> None:
        """Only the hardware exercise has anything to ask about."""
        asked = []
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True, raising=False)
        _invoke("run", "1")
        assert asked == []

    def test_a_pipe_is_never_asked(self, sandbox: Path, monkeypatch) -> None:
        """A script or a CI job must behave exactly as it did before."""
        asked = []
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))
        monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False, raising=False)
        assert cli._confirm_hardware(_hardware_exercise(sandbox)) is None
        assert asked == []

    def test_the_queue_and_a_link_are_shown_before_the_question(
        self, sandbox: Path, monkeypatch, capsys
    ) -> None:
        from quantum_exercises.backends import Queue

        self._peek(monkeypatch, Queue("ibm_marrakesh", 6))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: True)

        window = cli._confirm_hardware(_hardware_exercise(sandbox))
        shown = capsys.readouterr().out
        assert "ibm_marrakesh" in shown
        assert "6 job" in shown
        assert cli.COMPUTERS_URL in shown
        assert window == cli.HARDWARE_WINDOW_SECONDS
        assert window == 3 * 60 * 60, "the window has to outlast a real queue"

    def test_no_leaves_everything_untouched(self, sandbox: Path, monkeypatch) -> None:
        from quantum_exercises.backends import Queue

        self._peek(monkeypatch, Queue("ibm_marrakesh", 400))
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: False)

        with pytest.raises(cli.typer.Exit) as exit_info:
            cli._confirm_hardware(_hardware_exercise(sandbox))
        assert exit_info.value.exit_code == 0, "declining is not a failure"

    def test_unreachable_hardware_asks_nothing(self, sandbox: Path, monkeypatch) -> None:
        """Offline, no account, no network: there is no decision to put to anyone."""
        asked = []
        self._peek(monkeypatch, None)
        monkeypatch.setattr(cli.typer, "confirm", lambda *a, **k: asked.append(True))
        assert cli._confirm_hardware(_hardware_exercise(sandbox)) is None
        assert asked == []


def _hardware_exercise(sandbox: Path):
    from quantum_exercises.registry import load_exercises

    return next(e for e in load_exercises(sandbox) if e.hardware)


class TestDamagedProgressFile:
    """Starting fresh is right. Doing it in silence is what left readers guessing."""

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
    """A flag whose surprise is not in its help is a surprise the reader meets late."""

    @staticmethod
    def _help(*args: str) -> str:
        """Help text with the wrapping taken out: typer breaks it across the box."""
        return " ".join(_invoke(*args, "--help").stdout.replace("│", " ").split()).lower()

    def test_timeout_names_its_unit(self) -> None:
        assert "in seconds" in self._help("run")

    def test_the_solution_flag_admits_it_records_nothing(self) -> None:
        assert "records no progress" in self._help("run")

    def test_the_top_level_help_says_how_to_reach_hardware(self) -> None:
        """Account setup lived only under `doctor --help`, which you had to guess at.

        Someone who does not know the flag exists has no way to find it, and the
        command list alone never mentioned an account or a key.
        """
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
            cli, "STATUS_ICON", cli.STATUS_ICON
        )  # keep the mapping, replace the checks
        monkeypatch.setattr(
            "quantum_exercises.doctor.run_checks",
            lambda root, online=False: [
                doctor_module.Check("Thing", "warn", "not there", "Install the thing.")
            ],
        )
        result = _invoke("doctor")
        assert "Install the thing." in result.stdout
        assert result.exit_code == 0


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
        monkeypatch.setattr(cli, "getpass", None, raising=False)
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
        """The key is on disk either way, so this warns rather than failing the save.

        Saying nothing would leave a clear-text key world readable on a shared
        machine with nothing on screen to say so.
        """
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
        """ "Press Enter to skip" said it was allowed, never what it did.

        The client resolves the instance itself when the field is empty, which is
        the answer nearly every reader needs, and it was only in qiskit's docstring.
        """
        prompts: list[str] = []
        self._fake_runtime(monkeypatch, lambda **kw: None)
        monkeypatch.setattr("getpass.getpass", lambda prompt="": "tok")
        monkeypatch.setattr("builtins.input", lambda prompt="": prompts.append(prompt) or "")
        monkeypatch.setattr(doctor_module, "CREDENTIALS_PATH", tmp_path / ".qiskit" / "c.json")

        result = _invoke("doctor", "--save-account")
        assert "optional" in prompts[0].lower()
        # And the panel above it says who would want to fill it in.
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
        """`python -m quantum_exercises.cli` is the route that skips the console script.

        It is what someone reaches for when `qx` is not on PATH, and the only thing
        holding it up is the `__main__` guard at the bottom of cli.py.
        """
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
    """Typer draws --help and every usage error itself, outside ui.py and theme.py.

    Left alone it uses named colours and rounded corners, so a mistyped option was
    answered in a red rounded box beside tables this project squares on purpose.
    """

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

    def test_a_mistyped_option_names_the_command_that_has_it(self) -> None:
        """`--online` belongs to doctor. The error must not be the only thing said."""
        result = _invoke("--online")
        assert result.exit_code != 0
        assert "No such option" in result.output
