"""Exercise 10 - Deutsch's algorithm in one query.

Fill in the TODOs, then run:  uv run qx run 10
"""

import math

from qiskit import QuantumCircuit

# The four possible functions, written for you as phase oracles.
# Each one flips the sign of |x> exactly when f(x) = 1.


def constant_zero() -> QuantumCircuit:
    """f(0) = 0, f(1) = 0. Nothing is negated, so the oracle is empty."""
    return QuantumCircuit(1)


def constant_one() -> QuantumCircuit:
    """f(0) = 1, f(1) = 1. Both are negated, which is an overall minus sign."""
    qc = QuantumCircuit(1)
    qc.global_phase = math.pi
    return qc


def balanced_identity() -> QuantumCircuit:
    """f(0) = 0, f(1) = 1. Only |1> is negated, which is exactly what z does."""
    qc = QuantumCircuit(1)
    qc.z(0)
    return qc


def balanced_not() -> QuantumCircuit:
    """f(0) = 1, f(1) = 0. Only |0> is negated."""
    qc = QuantumCircuit(1)
    qc.x(0)
    qc.z(0)
    qc.x(0)
    return qc


def deutsch(oracle: QuantumCircuit) -> QuantumCircuit:
    """Build the one-query circuit: H, the oracle, H, then measure.

    Insert the oracle with `qc.compose(oracle, inplace=True)`.

    Call the oracle exactly once. Calling it twice makes the two sign flips
    cancel, and the balanced answers turn into constant ones.
    """
    qc = QuantumCircuit(1)
    # TODO: Hadamard, then the oracle, then Hadamard, then measure everything.
    return qc


def is_balanced(counts: dict[str, int]) -> bool:
    """Read the verdict: True if f is balanced, False if it is constant.

    Measuring 1 means balanced, measuring 0 means constant. On a simulator every
    shot agrees, but take the majority outcome so this still works on hardware.
    """
    # TODO: decide from the counts.
    return False
