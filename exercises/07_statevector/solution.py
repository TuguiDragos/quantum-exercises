"""Exercise 07 - reference solution."""

from qiskit import QuantumCircuit

# H makes (|0> + |1>)/sqrt(2); S multiplies the |1> amplitude by i.
qc_a = QuantumCircuit(1)
qc_a.h(0)
qc_a.s(0)

# H again, then Z flips the sign of the |1> amplitude.
qc_b = QuantumCircuit(1)
qc_b.h(0)
qc_b.z(0)
