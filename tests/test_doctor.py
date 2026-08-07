"""Environment diagnosis, including the credential states that are hard to hit."""

from __future__ import annotations

import json
import os
from pathlib import Path

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
