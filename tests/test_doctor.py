"""Environment diagnosis, including the credential states that are hard to hit."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from quantum_exercises import doctor


class TestSmokeTest:
    def test_a_working_install_passes(self) -> None:
        check = doctor.check_smoke()
        assert check.status == "ok", check.detail
        assert "64 shots" in check.detail


class TestPython:
    def test_current_interpreter_is_supported(self) -> None:
        assert doctor.check_python().status == "ok"


class TestCredentials:
    def test_absent_account_is_a_warning_not_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No account must never block anyone: the course works without one."""
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", tmp_path / "missing.json")
        check = doctor.check_credentials()
        assert check.status == "warn"
        assert "simulator" in check.fix

    def test_valid_account_is_reported_without_the_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret = "a" * 44
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps(
                {
                    "default-ibm-quantum-platform": {
                        "channel": "ibm_quantum_platform",
                        "token": secret,
                        "instance": "crn:v1:bluemix:public:quantum-computing:us-east:a/x:y::",
                    }
                }
            ),
            encoding="utf-8",
        )
        path.chmod(0o600)  # permissions are a separate check; this one is about content
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

        check = doctor.check_credentials()
        assert check.status == "ok"
        assert "ibm_quantum_platform" in check.detail
        # The whole point: diagnosis must never echo the key.
        assert secret not in check.detail
        assert secret not in (check.fix or "")

    def test_the_ok_does_not_claim_the_key_still_works(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Every test above this one reads the file. None of them asks IBM.

        A key that has since been revoked passes all of them, so an unqualified ok
        beside the account name reads as a promise this check never made.
        """
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps({"acct": {"channel": "ibm_quantum_platform", "token": "b" * 44}}),
            encoding="utf-8",
        )
        path.chmod(0o600)
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

        check = doctor.check_credentials()
        assert check.status == "ok"
        assert "not tested" in check.detail
        assert "--online" in check.detail

    def test_retired_channel_is_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Accounts saved on ibm_quantum stopped working when Classic was retired."""
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps({"default": {"channel": "ibm_quantum", "token": "x" * 44}}),
            encoding="utf-8",
        )
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

        check = doctor.check_credentials()
        assert check.status == "fail"
        assert "ibm_quantum" in check.detail
        assert "ibm_quantum_platform" in check.fix

    @pytest.mark.parametrize("channel", ["ibm_quantumm", "ibm-quantum-platform", None])
    def test_unrecognised_channel_is_a_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, channel: str | None
    ) -> None:
        """A typo used to be reported as a healthy account.

        Only the retired list was consulted, so anything that was neither current
        nor known-retired fell through to "ok". VALID_CHANNELS existed for this and
        was never read.
        """
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps({"default": {"channel": channel, "token": "x" * 44}}), encoding="utf-8"
        )
        path.chmod(0o600)
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

        check = doctor.check_credentials()
        assert check.status == "warn"
        assert "not recognised" in check.detail
        assert "ibm_quantum_platform" in (check.fix or "")

    @pytest.mark.parametrize("channel", sorted(doctor.VALID_CHANNELS))
    def test_every_valid_channel_is_accepted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, channel: str
    ) -> None:
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps({"default": {"channel": channel, "token": "x" * 44}}), encoding="utf-8"
        )
        path.chmod(0o600)
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

        assert doctor.check_credentials().status == "ok"

    def test_corrupt_file_is_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "qiskit-ibm.json"
        path.write_text("{ not json", encoding="utf-8")
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)
        assert doctor.check_credentials().status == "fail"

    def test_empty_file_is_a_failure(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "qiskit-ibm.json"
        path.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)
        assert doctor.check_credentials().status == "fail"


class TestFullRun:
    def test_no_blocking_failures_in_this_environment(
        self, root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", tmp_path / "missing.json")
        checks = doctor.run_checks(root, online=False)
        failures = [c for c in checks if c.status == "fail"]
        assert not failures, [(c.name, c.detail) for c in failures]

    def test_online_check_is_opt_in(self, root: Path) -> None:
        names = {c.name for c in doctor.run_checks(root, online=False)}
        assert "IBM Quantum connection" not in names


class TestCredentialPermissions:
    """A clear-text key is only as private as the file holding it."""

    def _write_account(self, tmp_path: Path, mode: int) -> Path:
        path = tmp_path / "qiskit-ibm.json"
        path.write_text(
            json.dumps({"default": {"channel": "ibm_quantum_platform", "token": "t" * 44}}),
            encoding="utf-8",
        )
        path.chmod(mode)
        return path

    # _loose_permissions returns None on Windows: there are no group or other bits.
    @pytest.mark.skipif(os.name == "nt", reason="POSIX modes")
    def test_world_readable_key_is_a_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", self._write_account(tmp_path, 0o644))
        check = doctor.check_credentials()
        assert check.status == "warn"
        assert "other local users" in check.detail
        assert "chmod 600" in check.fix

    @pytest.mark.skipif(os.name == "nt", reason="POSIX modes")
    def test_group_readable_key_is_a_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", self._write_account(tmp_path, 0o640))
        assert doctor.check_credentials().status == "warn"

    def test_owner_only_key_passes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", self._write_account(tmp_path, 0o600))
        check = doctor.check_credentials()
        assert check.status == "ok"

    def test_the_warning_never_contains_the_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", self._write_account(tmp_path, 0o644))
        check = doctor.check_credentials()
        assert "t" * 44 not in check.detail
        assert "t" * 44 not in (check.fix or "")


def test_check_online_reports_available_qpus(monkeypatch) -> None:
    class FakeService:
        def backends(self, **kwargs):
            return [SimpleNamespace(name="ibm_probe", num_qubits=127)]

    module = ModuleType("qiskit_ibm_runtime")
    module.QiskitRuntimeService = lambda *a, **k: FakeService()
    monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

    check = doctor.check_online()
    assert check.status == "ok"
    assert "ibm_probe" in check.detail


class TestOnlineNoise:
    """The runtime client logs at WARNING while doing ordinary things.

    Two paragraphs of it, with a timestamp and a module path, used to land in the
    middle of the doctor table. That is library noise in a tool whose whole claim
    is that you never have to read any.
    """

    @staticmethod
    def _service(monkeypatch, messages: list[str]) -> None:
        def talkative(*args, **kwargs):
            logger = logging.getLogger("qiskit_ibm_runtime")
            for message in messages:
                logger.warning(message)
            return SimpleNamespace(
                backends=lambda **k: [SimpleNamespace(name="ibm_probe", num_qubits=156)]
            )

        module = ModuleType("qiskit_ibm_runtime")
        module.QiskitRuntimeService = talkative
        monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

    def test_the_clients_warnings_never_reach_the_screen(self, monkeypatch) -> None:
        """Proved against a real handler on the root logger, which is what prints.

        Asserting on captured stdout proves nothing here: under pytest the root
        logger has no stream handler, so the line would go nowhere either way.
        """
        import io

        stream = io.StringIO()
        printer = logging.StreamHandler(stream)
        root = logging.getLogger()
        root.addHandler(printer)
        previous = root.level
        root.setLevel(logging.WARNING)
        try:
            self._service(monkeypatch, ["Instance was not set at service instantiation."])
            doctor.check_online()
        finally:
            root.removeHandler(printer)
            root.setLevel(previous)

        assert stream.getvalue() == "", f"the client printed: {stream.getvalue()!r}"

    def test_it_silences_the_handler_the_client_attaches_to_itself(self, monkeypatch) -> None:
        """The setup the library really has, which the root-logger test above misses.

        qiskit_ibm_runtime calls setup_logger on import: a StreamHandler on its own
        logger, and propagate already False. Nothing higher up is involved, so
        cutting propagation and adding a second handler leaves the first one
        printing, which is exactly what `qx doctor --online` did.
        """
        import io

        stream = io.StringIO()
        logger = logging.getLogger("qiskit_ibm_runtime")
        printer = logging.StreamHandler(stream)
        printer.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        handlers = logger.handlers[:]
        propagate, level = logger.propagate, logger.level
        logger.handlers = [printer]
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        try:
            self._service(monkeypatch, ["Instance was not set at service instantiation."])
            check = doctor.check_online()
        finally:
            logger.handlers = handlers
            logger.propagate = propagate
            logger.setLevel(level)

        assert stream.getvalue() == "", f"the client printed: {stream.getvalue()!r}"
        assert check.status == "ok"

    def test_the_instance_it_settled_on_is_reported_in_our_own_words(self, monkeypatch) -> None:
        self._service(monkeypatch, ["Loading instance: open-instance, plan: open"])
        check = doctor.check_online()
        assert check.status == "ok"
        assert "open-instance (open plan)" in check.detail
        assert "Loading instance" not in check.detail

    def test_a_silent_client_simply_omits_the_clause(self, monkeypatch) -> None:
        """Upstream may reword or drop that line. Losing it must cost the clause only."""
        self._service(monkeypatch, [])
        check = doctor.check_online()
        assert check.status == "ok"
        assert "ibm_probe" in check.detail
        assert " on " not in check.detail

    def test_the_logger_is_left_as_it_was_found(self, monkeypatch) -> None:
        logger = logging.getLogger("qiskit_ibm_runtime")
        before = (logger.propagate, len(logger.handlers))
        self._service(monkeypatch, ["Loading instance: open-instance, plan: open"])
        doctor.check_online()
        assert (logger.propagate, len(logger.handlers)) == before


def test_check_online_with_no_operational_qpu(monkeypatch) -> None:
    module = ModuleType("qiskit_ibm_runtime")
    module.QiskitRuntimeService = lambda *a, **k: SimpleNamespace(backends=lambda **k: [])
    monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)
    assert doctor.check_online().status == "warn"


def test_check_online_survives_a_network_failure(monkeypatch) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("no route to host")

    module = ModuleType("qiskit_ibm_runtime")
    module.QiskitRuntimeService = explode
    monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

    check = doctor.check_online()
    assert check.status == "warn"
    assert "could not reach IBM" in check.detail


def test_check_python_rejects_an_old_interpreter(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "MIN_PYTHON", (99, 0))
    assert doctor.check_python().status == "fail"


def test_check_uv_when_absent(monkeypatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    assert doctor.check_uv().status == "warn"


def test_check_exercises_without_a_root() -> None:
    assert doctor.check_exercises(None).status == "fail"


def test_check_exercises_with_a_broken_root(tmp_path: Path) -> None:
    (tmp_path / "exercises").mkdir()
    check = doctor.check_exercises(tmp_path)
    assert check.status == "fail"


def test_package_check_reports_a_missing_package() -> None:
    check = doctor._package("definitely-not-installed", "Ghost", "install it")
    assert check.status == "fail" and check.detail == "not installed"


def test_run_checks_includes_online_only_when_asked(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "check_online", lambda: doctor.Check("x", "ok", ""))
    assert len(doctor.run_checks(None, online=True)) == len(doctor.run_checks(None)) + 1


class TestCredentialChecks:
    @staticmethod
    def _point_at(monkeypatch, path: Path) -> None:
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", path)

    def test_missing_file_is_a_warning(self, tmp_path: Path, monkeypatch) -> None:
        self._point_at(monkeypatch, tmp_path / "absent.json")
        assert doctor.check_credentials().status == "warn"

    def test_unreadable_file_fails(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text("{not json", encoding="utf-8")
        self._point_at(monkeypatch, path)
        assert doctor.check_credentials().status == "fail"

    def test_empty_file_fails(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text("{}", encoding="utf-8")
        self._point_at(monkeypatch, path)
        assert doctor.check_credentials().status == "fail"

    def test_retired_channel_fails(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text(json.dumps({"default": {"channel": "ibm_quantum"}}), encoding="utf-8")
        path.chmod(0o600)
        self._point_at(monkeypatch, path)
        check = doctor.check_credentials()
        assert check.status == "fail" and "retired" in check.detail

    def test_typo_channel_warns(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text(json.dumps({"default": {"channel": "ibm_clod"}}), encoding="utf-8")
        path.chmod(0o600)
        self._point_at(monkeypatch, path)
        assert "not recognised" in doctor.check_credentials().detail

    @pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
    def test_world_readable_key_warns(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text(
            json.dumps({"default": {"channel": "ibm_quantum_platform"}}), encoding="utf-8"
        )
        path.chmod(0o644)
        self._point_at(monkeypatch, path)
        check = doctor.check_credentials()
        assert check.status == "warn" and "readable by other local users" in check.detail

    @pytest.mark.skipif(os.name == "nt", reason="POSIX modes only")
    def test_owner_only_key_is_ok(self, tmp_path: Path, monkeypatch) -> None:
        path = tmp_path / "creds.json"
        path.write_text(
            json.dumps({"default": {"channel": "ibm_quantum_platform"}}), encoding="utf-8"
        )
        path.chmod(0o600)
        self._point_at(monkeypatch, path)
        assert doctor.check_credentials().status == "ok"


def test_doctor_reports_a_broken_smoke_test(monkeypatch) -> None:
    module = ModuleType("qiskit.primitives")

    class Exploding:
        def __init__(self, *a, **k):
            raise RuntimeError("compiled extension mismatch")

    module.StatevectorSampler = Exploding
    monkeypatch.setitem(sys.modules, "qiskit.primitives", module)
    check = doctor.check_smoke()
    assert check.status == "fail"


def test_doctor_reports_a_wrong_hadamard(monkeypatch) -> None:
    module = ModuleType("qiskit.primitives")

    class Liar:
        def __init__(self, *a, **k): ...

        def run(self, *a, **k):
            counts = SimpleNamespace(get_counts=lambda: {"0": 3})
            data = SimpleNamespace(meas=counts)
            return SimpleNamespace(result=lambda: [SimpleNamespace(data=data)])

    module.StatevectorSampler = Liar
    monkeypatch.setitem(sys.modules, "qiskit.primitives", module)
    assert doctor.check_smoke().status == "fail"


def test_doctor_reports_missing_visualization(monkeypatch) -> None:
    def fake_import(name):
        raise ImportError(name)

    monkeypatch.setattr(doctor, "import_module", fake_import)
    check = doctor.check_visualization()
    assert check.status == "warn" and "matplotlib" in check.detail


def test_doctor_reports_qiskit_that_will_not_import(monkeypatch) -> None:
    def fake_import(name):
        raise ImportError(name)

    monkeypatch.setattr(doctor, "import_module", fake_import)
    assert doctor.check_qiskit().status == "fail"


def test_check_online_without_the_runtime_package(monkeypatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qiskit_ibm_runtime":
            raise ImportError("absent")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert doctor.check_online().status == "fail"


class TestAccountRowWording:
    """The row has to name a command someone can actually type."""

    def test_it_names_the_whole_command_not_the_bare_flag(self, monkeypatch, tmp_path) -> None:
        """`--online` alone reads as an option of qx, which sent a reader to `qx --online`."""
        creds = tmp_path / "qiskit-ibm.json"
        creds.write_text('{"default": {"channel": "ibm_quantum_platform"}}', encoding="utf-8")
        creds.chmod(0o600)  # a loose mode is reported first and would hide the wording
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", creds)

        detail = doctor.check_credentials().detail
        assert "doctor --online" in detail
        assert "(--online does that)" not in detail

    def test_the_pointer_is_dropped_once_online_has_run(self, monkeypatch, tmp_path) -> None:
        creds = tmp_path / "qiskit-ibm.json"
        creds.write_text('{"default": {"channel": "ibm_quantum_platform"}}', encoding="utf-8")
        creds.chmod(0o600)  # a loose mode is reported first and would hide the wording
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", creds)

        detail = doctor.check_credentials(tested_online=True).detail
        assert "--online" not in detail
        assert detail.endswith("saved")

    def test_run_checks_passes_the_flag_through(self, monkeypatch, tmp_path) -> None:
        creds = tmp_path / "qiskit-ibm.json"
        creds.write_text('{"default": {"channel": "ibm_quantum_platform"}}', encoding="utf-8")
        creds.chmod(0o600)  # a loose mode is reported first and would hide the wording
        monkeypatch.setattr(doctor, "CREDENTIALS_PATH", creds)
        module = ModuleType("qiskit_ibm_runtime")
        module.QiskitRuntimeService = lambda *a, **k: SimpleNamespace(
            backends=lambda **k: [SimpleNamespace(name="ibm_probe", num_qubits=156)]
        )
        monkeypatch.setitem(sys.modules, "qiskit_ibm_runtime", module)

        offline = {c.name: c.detail for c in doctor.run_checks(None)}
        online = {c.name: c.detail for c in doctor.run_checks(None, online=True)}
        assert "--online" in offline["IBM Quantum account"]
        assert "--online" not in online["IBM Quantum account"]
