"""Exercise 20 - reference solution."""

import math

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp


def observable_at(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[math.cos(theta), math.sin(theta)])


def bell():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


def joint_observable(alice_angle, bob_angle):
    # tensor() takes the low-qubit operand as its argument, so Alice goes inside.
    return observable_at(bob_angle).tensor(observable_at(alice_angle))


def correlation(alice_angle, bob_angle):
    observable = joint_observable(alice_angle, bob_angle)
    result = StatevectorEstimator().run([(bell(), observable)]).result()
    return float(result[0].data.evs)


def chsh(a0, a1, b0, b1):
    return correlation(a0, b0) + correlation(a0, b1) + correlation(a1, b0) - correlation(a1, b1)
