"""Exercise 04 - measurement, or the result is empty.

Fill in the TODOs, then run:  qx run 4
"""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

SHOTS = 1024

qc = QuantumCircuit(1)
qc.h(0)

# TODO: add measurement to the circuit.
#       One method call measures every qubit and creates the classical register
#       for you. Without it the sampler returns an empty result and only warns.


# The seed makes this run reproducible, so the same code gives the same counts.
sampler = StatevectorSampler(seed=1234)

# TODO: run the circuit for SHOTS shots and assign the finished result.
#       Two traps: run() takes a LIST of circuits, and it returns a job rather
#       than the answer, so you still have to ask that job for its result.
result = None
