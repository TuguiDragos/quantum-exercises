"""Exercise 06 - reference solution."""

import math

from qiskit import QuantumCircuit

THETA = math.pi / 3

qc = QuantumCircuit(1)
qc.ry(THETA, 0)
qc.measure_all()

# Amplitudes are cos(theta/2) and sin(theta/2); the Born rule squares them.
predicted = {
    "0": math.cos(THETA / 2) ** 2,
    "1": math.sin(THETA / 2) ** 2,
}
