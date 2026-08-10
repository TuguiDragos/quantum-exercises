"""Exercise 18 - a device that only measures Z.

Fill in the TODOs, then run:  qx run 18
"""

import math

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp

# TODO: the X observable on a single qubit.
observable_x = None


# TODO: return cos(theta) * Z + sin(theta) * X as one observable.
#
#       SparsePauliOp takes a list of Paulis and a list of coefficients:
#           SparsePauliOp(["Z", "X"], coeffs=[a, b])
#
#       theta is in radians, which is what math.cos and math.sin want.
def observable_at(theta):
    pass


# TODO: return a NEW circuit that measures X on qubit 0.
#
#       The hardware has one measurement and it reads Z, so rotate first: H
#       swaps the X and Z axes. Then add the measurement.
#
#       Copy the circuit before you touch it. The runner hands you the same
#       object more than once, so appending to it in place corrupts later checks.
def to_x_basis(circuit):
    pass
