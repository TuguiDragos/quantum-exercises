"""Exercise 09 - reference solution."""

from qiskit import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

# Little-endian: qubit 0 is the rightmost character.
label_q0_only = "01"

# The two qubits always agree, so the disagreeing outcomes never occur.
impossible_outcomes = {"01", "10"}
