"""Exercise 10 - reference solution."""

import math

from qiskit import QuantumCircuit


def constant_zero() -> QuantumCircuit:
    return QuantumCircuit(1)


def constant_one() -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.global_phase = math.pi
    return qc


def balanced_identity() -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.z(0)
    return qc


def balanced_not() -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.x(0)
    qc.z(0)
    qc.x(0)
    return qc


def deutsch(oracle: QuantumCircuit) -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.h(0)
    # One call. The single query sees both inputs because of the Hadamard above.
    qc.compose(oracle, inplace=True)
    qc.h(0)
    qc.measure_all()
    return qc


def is_balanced(counts: dict[str, int]) -> bool:
    return max(counts, key=lambda outcome: counts[outcome]) == "1"
