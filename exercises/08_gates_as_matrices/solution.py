"""Exercise 08 - reference solution."""

from qiskit import QuantumCircuit

# H on the target turns the X of a CNOT into a Z, because H X H = Z.
qc = QuantumCircuit(2)
qc.h(1)
qc.cx(0, 1)
qc.h(1)
