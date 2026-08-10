"""Exercise 19 - reference solution."""

import math

from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

observable_z = SparsePauliOp("Z")
observable_x = SparsePauliOp("X")


def expectation(circuit, observable):
    """The expectation value of `observable` on `circuit`, as a float."""
    result = StatevectorEstimator().run([(circuit, observable)]).result()
    return float(result[0].data.evs)


observable_y = SparsePauliOp("Y")


def bloch_vector(circuit):
    return (
        expectation(circuit, observable_x),
        expectation(circuit, observable_y),
        expectation(circuit, observable_z),
    )


def angles(vector):
    x, y, z = vector
    length = math.sqrt(x * x + y * y + z * z)
    # Clamping is defensive. These coordinates are exact at the poles, but acos
    # raises on anything past 1, and less exact coordinates get there.
    theta = math.acos(max(-1.0, min(1.0, z / length)))
    phi = math.atan2(y, x)
    return theta, phi
