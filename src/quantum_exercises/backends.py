"""Backend selection with graceful degradation.

The hardware exercise must be finishable by someone with no IBM account, no
network, or an exhausted free quota. This module answers "give me the most real
backend available right now" and says honestly which one you got.

Order of preference:
  1. A real IBM QPU, when an account exists and a QPU is reachable.
  2. AerSimulator with a noise model copied from a fake backend, so the lesson
     about noise still works.
  3. A plain noiseless AerSimulator.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

Kind = Literal["hardware", "noisy_simulator", "simulator"]

# Set to any non-empty value to keep every exercise off real hardware. CI sets it.
OFFLINE_ENV = "QX_OFFLINE"

# A 5-qubit Falcon snapshot: small, always present in qiskit-ibm-runtime, and
# realistic enough that a Bell state shows visible 01/10 leakage.
FAKE_BACKEND = "FakeManilaV2"


@dataclass
class Selection:
    backend: Any
    kind: Kind
    name: str
    reason: str

    @property
    def is_hardware(self) -> bool:
        return self.kind == "hardware"

    def describe(self) -> str:
        labels = {
            "hardware": "real QPU",
            "noisy_simulator": "local simulator with a hardware noise model",
            "simulator": "local noiseless simulator",
        }
        return f"{labels[self.kind]}: {self.name}"


def offline() -> bool:
    return bool(os.environ.get(OFFLINE_ENV))


def _noisy_simulator(reason: str) -> Selection:
    from qiskit_aer import AerSimulator

    try:
        from qiskit_ibm_runtime import fake_provider

        fake = getattr(fake_provider, FAKE_BACKEND)()
        backend = AerSimulator.from_backend(fake)
        return Selection(backend, "noisy_simulator", f"aer({FAKE_BACKEND})", reason)
    except Exception:  # noqa: BLE001 - fall through to the noiseless simulator
        return Selection(AerSimulator(), "simulator", "aer", reason)


def get_backend(*, min_num_qubits: int = 2, prefer_hardware: bool = True) -> Selection:
    """Return the most realistic backend currently available."""
    if not prefer_hardware:
        from qiskit_aer import AerSimulator

        return Selection(AerSimulator(), "simulator", "aer", "hardware was not requested")

    if offline():
        return _noisy_simulator(f"{OFFLINE_ENV} is set, so no network call was made")

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:
        return _noisy_simulator("qiskit-ibm-runtime is not installed")

    try:
        service = QiskitRuntimeService()
    except Exception as exc:  # noqa: BLE001 - AccountNotFoundError and friends
        return _noisy_simulator(f"no usable IBM account ({type(exc).__name__})")

    try:
        backend = service.least_busy(
            min_num_qubits=min_num_qubits, operational=True, simulator=False
        )
    except Exception as exc:  # noqa: BLE001 - network, auth, or quota failures
        return _noisy_simulator(f"could not reach a QPU ({type(exc).__name__}: {exc})")

    if backend is None:
        return _noisy_simulator("no operational QPU was available")

    return Selection(backend, "hardware", backend.name, "least busy operational QPU")


def to_isa(circuit, backend, *, optimization_level: int = 1):
    """Transpile to the backend's instruction set.

    Hardware rejects any circuit that is not already expressed in its native
    gates and connectivity, so this step is mandatory rather than an optimization.
    """
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    pass_manager = generate_preset_pass_manager(
        optimization_level=optimization_level, backend=backend
    )
    return pass_manager.run(circuit)


def sample(circuit, selection: Selection, *, shots: int = 1024) -> dict[str, int]:
    """Run an ISA circuit on the selected backend and return counts."""
    if selection.is_hardware:
        from qiskit_ibm_runtime import SamplerV2

        result = SamplerV2(mode=selection.backend).run([circuit], shots=shots).result()
        return single_register_counts(result[0])

    # Run on the backend we actually chose. A fresh qiskit_aer SamplerV2() would
    # ignore it and sample noiselessly, so the noise model copied from hardware
    # would silently do nothing and the whole point of the fallback would be lost.
    counts = selection.backend.run(circuit, shots=shots).result().get_counts()
    return _normalize_counts(counts)


def _normalize_counts(counts) -> dict[str, int]:
    """Plain dict of str to int, rejecting the multi-register case like the V2 path."""
    normalized: dict[str, int] = {}
    for key, value in dict(counts).items():
        label = str(key)
        if " " in label:
            raise ValueError(
                f"The circuit has several classical registers (outcome {label!r}); "
                "this helper expects exactly one."
            )
        normalized[label] = int(value)
    return normalized


def single_register_counts(pub_result) -> dict[str, int]:
    """Read counts without hardcoding a register name.

    `measure_all()` names its register `meas`; an explicit ClassicalRegister keeps
    its own name. Discovering the field avoids guessing wrong.
    """
    fields = list(pub_result.data.keys())
    if not fields:
        raise ValueError(
            "The result carries no classical register, which means the circuit had no "
            "measurement. Add qc.measure_all() before running it."
        )
    if len(fields) > 1:
        raise ValueError(
            f"The circuit has several classical registers ({fields}); "
            "pick one explicitly with result[0].data.<name>.get_counts()."
        )
    return dict(getattr(pub_result.data, fields[0]).get_counts())


def noise_model(selection: Selection):
    """The noise model actually in force, or None for a noiseless backend."""
    options = getattr(selection.backend, "options", None)
    return getattr(options, "noise_model", None)


__all__ = [
    "FAKE_BACKEND",
    "OFFLINE_ENV",
    "Kind",
    "Selection",
    "get_backend",
    "noise_model",
    "offline",
    "sample",
    "single_register_counts",
    "to_isa",
]
