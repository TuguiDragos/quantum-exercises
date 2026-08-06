"""Exercise 16 - reference solution."""

import math

from qiskit.quantum_info import SparsePauliOp

observable_x = SparsePauliOp("X")


def observable_at(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[math.cos(theta), math.sin(theta)])


def to_x_basis(circuit):
    # copy(): the caller keeps using the original, and append is in place.
    rotated = circuit.copy()
    rotated.h(0)
    rotated.measure_all()
    return rotated
