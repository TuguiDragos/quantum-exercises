"""Exercise 08 - gates are matrices.

Fill in the TODOs, then run:  uv run qx run 8
"""

from qiskit import QuantumCircuit

# TODO: add gates so that qc implements a controlled-Z, i.e. diag(1, 1, 1, -1).
#
#       Allowed gates: h and cx only. Using qc.cz(...) defeats the exercise and
#       the runner rejects it.
#
#       Three gates are enough. Think about what a Hadamard does to the target
#       qubit of a CNOT, before and after.
qc = QuantumCircuit(2)
