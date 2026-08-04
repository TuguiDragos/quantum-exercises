"""Exercise 09 - reference solution."""

from qiskit import QuantumCircuit

# H is its own inverse: the second one interferes the two routes back together.
qc_undo = QuantumCircuit(1)
qc_undo.h(0)
qc_undo.h(0)

# Z flips the sign of the |1> amplitude, so the cancellation lands on |0> instead.
qc_flip = QuantumCircuit(1)
qc_flip.h(0)
qc_flip.z(0)
qc_flip.h(0)

# A coin randomised twice is still a coin.
coin_model_prediction = 0.5
