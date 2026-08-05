"""Environment diagnosis. Every step of Act Zero has a check here.

Nothing in this module reaches the network unless explicitly asked to, and it
never prints a token.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from dataclasses import dataclass
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal

from quantum_exercises import invocation

CREDENTIALS_PATH = Path.home() / ".qiskit" / "qiskit-ibm.json"

# Channels qiskit-ibm-runtime still accepts. `ibm_quantum` was retired with the
# Classic platform and a saved account on it is unusable.
VALID_CHANNELS = {"ibm_quantum_platform", "ibm_cloud"}
RETIRED_CHANNELS = {"ibm_quantum"}

MIN_PYTHON = (3, 10)

Status = Literal["ok", "warn", "fail"]


@dataclass
class Check:
    name: str
    status: Status
    detail: str
    fix: str | None = None


def _package(name: str, label: str, fix: str) -> Check:
    try:
        installed = version(name)
    except PackageNotFoundError:
        return Check(label, "fail", "not installed", fix)
    return Check(label, "ok", f"version {installed}")


def check_python() -> Check:
    current = sys.version_info
    text = f"{current.major}.{current.minor}.{current.micro}"
    if (current.major, current.minor) < MIN_PYTHON:
        return Check(
            "Python",
            "fail",
            f"{text} is too old",
            f"Qiskit needs at least {MIN_PYTHON[0]}.{MIN_PYTHON[1]}. "
            "Run `uv python install 3.12`, then `uv sync`.",
        )
    return Check("Python", "ok", f"{text} at {sys.executable}")


def check_uv() -> Check:
    path = shutil.which("uv")
    if path is None:
        return Check(
            "uv",
            "warn",
            "not on PATH",
            "You are clearly running Python somehow, but the documented workflow uses uv. "
            "Install it from https://docs.astral.sh/uv, then reopen your terminal so PATH updates.",
        )
    return Check("uv", "ok", path)


def check_qiskit() -> Check:
    try:
        qiskit = import_module("qiskit")
    except ImportError:
        return Check("Qiskit SDK", "fail", "cannot be imported", "Run `uv sync`.")
    return Check("Qiskit SDK", "ok", f"version {qiskit.__version__}")


def check_smoke() -> Check:
    """Build and run a real circuit.

    Importing a package proves the files are on disk. It does not prove the
    compiled extensions underneath actually work, which is the failure mode of a
    half-finished install or a mismatched architecture.
    """
    try:
        from qiskit import QuantumCircuit
        from qiskit.primitives import StatevectorSampler

        qc = QuantumCircuit(1)
        qc.h(0)
        qc.measure_all()
        result = StatevectorSampler(seed=1).run([qc], shots=64).result()
        counts = dict(result[0].data.meas.get_counts())
    except Exception as exc:  # noqa: BLE001 - any failure is the answer
        return Check(
            "Circuit smoke test",
            "fail",
            f"{type(exc).__name__}: {exc}",
            "The packages import but cannot run. Try `uv sync --reinstall`.",
        )

    if sum(counts.values()) != 64 or set(counts) - {"0", "1"}:
        return Check(
            "Circuit smoke test",
            "fail",
            f"a Hadamard produced {counts}, which is not what it should",
            "This environment is inconsistent. Try `uv sync --reinstall`.",
        )
    return Check("Circuit smoke test", "ok", f"ran a Hadamard on 64 shots: {counts}")


def check_visualization() -> Check:
    """qiskit[visualization] is a separate extra; without it draw('mpl') fails."""
    missing = []
    for module in ("matplotlib", "pylatexenc"):
        try:
            import_module(module)
        except ImportError:
            missing.append(module)
    if missing:
        return Check(
            "Qiskit visualization extra",
            "warn",
            f"missing {', '.join(missing)}",
            "Text drawing still works. For `qc.draw('mpl')` and `plot_histogram`, run "
            "`uv add 'qiskit[visualization]'`.",
        )
    return Check("Qiskit visualization extra", "ok", "matplotlib and pylatexenc present")


def check_credentials() -> Check:
    """Inspect the saved IBM account locally. Never reads or prints the token."""
    if not CREDENTIALS_PATH.is_file():
        return Check(
            "IBM Quantum account",
            "warn",
            "no saved account",
            "Optional. Every exercise runs on a local simulator without one. To use real "
            "hardware, get an API key from https://quantum.cloud.ibm.com and run "
            f"`{invocation()} doctor --save-account`.",
        )

    try:
        raw = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return Check(
            "IBM Quantum account",
            "fail",
            f"{CREDENTIALS_PATH} is unreadable ({type(exc).__name__})",
            "Delete the file and save the account again.",
        )

    if not isinstance(raw, dict) or not raw:
        return Check(
            "IBM Quantum account",
            "fail",
            "the credentials file is empty",
            f"Save the account again with `{invocation()} doctor --save-account`.",
        )

    accounts: list[str] = []
    retired: list[str] = []
    unknown: list[str] = []
    for name, entry in raw.items():
        channel = entry.get("channel") if isinstance(entry, dict) else None
        accounts.append(f"{name} (channel: {channel or 'unset'})")
        if channel in RETIRED_CHANNELS:
            retired.append(name)
        elif channel not in VALID_CHANNELS:
            unknown.append(f"{name} ({channel or 'unset'})")

    if retired:
        return Check(
            "IBM Quantum account",
            "fail",
            f"saved on the retired `ibm_quantum` channel: {', '.join(retired)}",
            "That channel was switched off with IBM Quantum Platform Classic and those "
            "credentials no longer work. Save again on `ibm_quantum_platform`.",
        )

    if unknown:
        # Neither current nor known-retired. A typo lands here, and used to be
        # reported as a healthy account because only the retired list was checked.
        return Check(
            "IBM Quantum account",
            "warn",
            f"channel not recognised: {', '.join(unknown)}",
            f"Expected one of {sorted(VALID_CHANNELS)}. A typo in the channel name means "
            "qiskit cannot route the request, and the failure appears later as a "
            f"connection error. Save the account again with `{invocation()} doctor "
            "--save-account`.",
        )

    loose = _loose_permissions()
    if loose:
        return Check(
            "IBM Quantum account",
            "warn",
            f"{'; '.join(accounts)} - but the file is readable by other local users ({loose})",
            "The key is stored in clear text. Tighten it with "
            f"`chmod 600 {CREDENTIALS_PATH}` and `chmod 700 {CREDENTIALS_PATH.parent}`. "
            "Accounts saved through this tool are tightened automatically; older ones "
            "kept whatever umask was in force when qiskit wrote them.",
        )

    return Check("IBM Quantum account", "ok", "; ".join(accounts))


def _loose_permissions() -> str | None:
    """Report the mode when the saved key is readable beyond its owner.

    A long-lived API key in clear text is only as private as the file holding it,
    and qiskit writes it with whatever umask happens to be in force.
    """
    if os.name == "nt":  # pragma: no cover - POSIX modes do not apply
        return None
    try:
        mode = CREDENTIALS_PATH.stat().st_mode
    except OSError:  # pragma: no cover - the caller has already read the file
        return None
    if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
        return stat.filemode(mode)
    return None


def check_online() -> Check:
    """Contact IBM and list backends. Costs no QPU time, but needs the network."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:
        return Check(
            "IBM Quantum connection",
            "fail",
            "qiskit-ibm-runtime is not installed",
            "Run `uv sync`.",
        )

    try:
        service = QiskitRuntimeService()
        backends = service.backends(operational=True, simulator=False)
    except Exception as exc:  # noqa: BLE001 - any failure is reported, never fatal
        return Check(
            "IBM Quantum connection",
            "warn",
            f"could not reach IBM ({type(exc).__name__}: {exc})",
            "Check your network and that the saved account is still valid.",
        )

    if not backends:
        return Check(
            "IBM Quantum connection", "warn", "connected, but no operational QPU is visible"
        )
    names = ", ".join(f"{b.name} ({b.num_qubits}q)" for b in backends[:4])
    return Check("IBM Quantum connection", "ok", f"{len(backends)} QPUs available: {names}")


def check_exercises(root: Path | None) -> Check:
    if root is None:
        return Check(
            "Exercises",
            "fail",
            "the exercises/ directory was not found",
            "Run this from inside the cloned repository.",
        )
    from quantum_exercises.registry import RegistryError, load_exercises

    try:
        exercises = load_exercises(root)
    except RegistryError as exc:
        return Check(
            "Exercises", "fail", str(exc), "The repository looks incomplete; try `git status`."
        )
    return Check("Exercises", "ok", f"{len(exercises)} exercises found in {root / 'exercises'}")


def run_checks(root: Path | None, *, online: bool = False) -> list[Check]:
    checks = [
        check_python(),
        check_uv(),
        check_qiskit(),
        _package("qiskit-aer", "Aer simulator", "Run `uv sync`."),
        _package("qiskit-ibm-runtime", "IBM Runtime client", "Run `uv sync`."),
        check_smoke(),
        check_visualization(),
        check_exercises(root),
        check_credentials(),
    ]
    if online:
        checks.append(check_online())
    return checks


__all__ = [
    "CREDENTIALS_PATH",
    "Check",
    "RETIRED_CHANNELS",
    "VALID_CHANNELS",
    "check_smoke",
    "run_checks",
]
