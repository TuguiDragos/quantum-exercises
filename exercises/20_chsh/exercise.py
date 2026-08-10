"""Exercise 20 - CHSH, the experiment that settles it.

Fill in the TODOs, then run:  qx run 20
"""

import math

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp


# Given: exercise 18's answer.
def observable_at(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[math.cos(theta), math.sin(theta)])


# Given: exercise 11's answer. Alice holds qubit 0, Bob holds qubit 1.
def bell():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


# TODO: one two-qubit observable, Alice's angle on qubit 0 and Bob's on qubit 1.
#
#       `tensor` puts its argument on the lower-numbered qubit, so the one you
#       pass in is the one that lands on qubit 0:
#           bob_side.tensor(alice_side)
def joint_observable(alice_angle, bob_angle):
    pass


# TODO: the expectation value of that observable on the Bell state, as a float.
#       Same Estimator call as exercise 17, with bell() as the circuit.
def correlation(alice_angle, bob_angle):
    pass


# TODO: combine four correlations into S.
#
#       S = E(a0, b0) + E(a0, b1) + E(a1, b0) - E(a1, b1)
#
#       Mind the minus sign. It is on the last term, and it is the only reason
#       the whole thing is bounded by 2 for pre-decided answers.
def chsh(a0, a1, b0, b1):
    pass
