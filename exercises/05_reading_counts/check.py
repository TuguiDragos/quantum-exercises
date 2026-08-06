"""Verification for exercise 05."""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

from quantum_exercises.checks import CheckFailed, counts_artifact, require

# Seeded, so the expected counts are exact rather than statistical.
CASES = [
    ("one qubit, Hadamard", 1, [("h", 0)], 512),
    ("two qubits, Bell state", 2, [("h", 0), ("cx", (0, 1))], 1024),
    ("three qubits, GHZ state", 3, [("h", 0), ("cx", (0, 1)), ("cx", (1, 2))], 256),
]


def _build(num_qubits, gates) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    for name, target in gates:
        if name == "h":
            qc.h(target)
        elif name == "cx":
            qc.cx(*target)
    qc.measure_all()
    return qc


def check(mod):
    read_counts = _callable(mod, "read_counts")
    read_shots = _callable(mod, "read_shots")

    artifacts = []
    for label, num_qubits, gates, shots in CASES:
        result = StatevectorSampler(seed=7).run([_build(num_qubits, gates)], shots=shots).result()
        expected_counts = dict(result[0].data.meas.get_counts())
        expected_shots = int(result[0].data.meas.num_shots)

        actual_counts = read_counts(result)
        if not isinstance(actual_counts, dict):
            raise CheckFailed(
                f"read_counts returned a {type(actual_counts).__name__}, expected a dict.",
                detail=(
                    "If you stopped at result[0].data.meas you have the register itself, not "
                    "the tally. Call .get_counts() on it."
                ),
            )
        if dict(actual_counts) != expected_counts:
            raise CheckFailed(
                f"read_counts gave the wrong answer for the {label} case.",
                detail=f"You returned {dict(actual_counts)}\nExpected      {expected_counts}",
            )

        actual_shots = read_shots(result)
        if actual_shots != expected_shots:
            raise CheckFailed(
                f"read_shots returned {actual_shots!r} for the {label} case, "
                f"expected {expected_shots}.",
                detail=(
                    "Either result[0].data.meas.num_shots, or the sum of the counts. "
                    "Both give the same number."
                ),
            )

        artifacts.append(
            counts_artifact(expected_counts, caption=f"{label} ({expected_shots} shots)")
        )

    return artifacts


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value
