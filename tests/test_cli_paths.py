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
