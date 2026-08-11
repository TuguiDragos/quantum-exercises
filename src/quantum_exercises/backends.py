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

import contextlib
import logging
import os
from collections.abc import Iterator
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


@contextlib.contextmanager
def quiet_runtime() -> Iterator[list[str]]:
    """Collect the runtime client's own log lines rather than letting them print.

    It logs at WARNING while doing ordinary things, such as naming the instance it
    picked, and those lines land raw wherever the client is built: a timestamp, a
    module path and a paragraph of advice, in the middle of a table or on top of a
    question. Collecting them means the one fact worth keeping can be said in the
    tool's own words, and the rest is dropped.

    Lives here rather than in doctor because it belongs to the client, and every
    caller that builds one in this process needs it.
    """
    logger = logging.getLogger("qiskit_ibm_runtime")
    collected: list[str] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            collected.append(record.getMessage())

    handler = _Collect()
    # The client attaches its own StreamHandler to this logger at import and sets
    # propagate to False itself, so adding a handler beside it silences nothing and
    # cutting propagation silences nothing either. Its handlers come off for the
    # length of the call and go back exactly as they were, list included.
    existing = logger.handlers[:]
    propagated = logger.propagate
    logger.handlers = [handler]
    logger.propagate = False
    try:
        yield collected
    finally:
        logger.handlers = existing
        logger.propagate = propagated


def _noisy_simulator(reason: str) -> Selection:
    from qiskit_aer import AerSimulator

    try:
        from qiskit_ibm_runtime import fake_provider

        fake = getattr(fake_provider, FAKE_BACKEND)()
        backend = AerSimulator.from_backend(fake)
        return Selection(backend, "noisy_simulator", f"aer({FAKE_BACKEND})", reason)
    except Exception as exc:  # noqa: BLE001 - fall through to the noiseless simulator
        # Say that the noise went missing. This branch hands back a noiseless
        # simulator while keeping the reason it was given, which explains only why
        # the run is not on hardware. The reader was left with an exercise about
        # noise that had none, and nothing on screen connecting the two.
        return Selection(
            AerSimulator(),
            "simulator",
            "aer",
            f"{reason}; {FAKE_BACKEND} would not load either "
            f"({type(exc).__name__}: {exc}), so there is no noise model",
        )


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
        # The message, not just the class. A revoked key raises InvalidAccountError,
        # whose text says which token to go and look at; naming the class alone left
        # the reader with a word and no next step, while the branch below this one
        # had been reporting both all along.
        return _noisy_simulator(f"no usable IBM account ({type(exc).__name__}: {exc})")

    try:
        backend = service.least_busy(
            min_num_qubits=min_num_qubits, operational=True, simulator=False
        )
    except Exception as exc:  # noqa: BLE001 - network, auth, or quota failures
        return _noisy_simulator(f"could not reach a QPU ({type(exc).__name__}: {exc})")

    if backend is None:
        return _noisy_simulator("no operational QPU was available")

    return Selection(backend, "hardware", backend.name, "least busy operational QPU")


@dataclass
class Queue:
    """What the least busy QPU looks like right now, before anything is sent."""

    name: str
    pending: int


def queue_peek(*, min_num_qubits: int = 2) -> Queue | None:
    """The least busy QPU and how many jobs are waiting on it.

    Asks only for status, so it costs no QPU time and commits to nothing. Returns
    None whenever hardware is out of reach, which is every case where there is
    nothing to decide: offline, no account, no network, no operational QPU.
    """
    if offline():
        return None
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService

        # Quiet, because this one runs in the terminal the reader is looking at.
        # `get_backend` builds the same client inside the worker, whose output the
        # runner pipes, so only this call ever put the client's log on screen.
        with quiet_runtime():
            backend = QiskitRuntimeService().least_busy(
                min_num_qubits=min_num_qubits, operational=True, simulator=False
            )
            if backend is None:
                return None
            return Queue(backend.name, int(backend.status().pending_jobs))
    except Exception:  # noqa: BLE001 - a peek that fails is simply no answer
        return None


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
    "Queue",
    "Selection",
    "get_backend",
    "noise_model",
    "offline",
    "queue_peek",
    "quiet_runtime",
    "sample",
    "single_register_counts",
    "to_isa",
]
