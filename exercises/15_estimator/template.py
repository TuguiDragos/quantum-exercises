"""Exercise 15 - the Estimator, and what it returns.

Fill in the TODOs, then run:  qx run 15
"""

from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

# TODO: the Z observable on a single qubit.
#       SparsePauliOp takes the Pauli as a string.
observable_z = None


# TODO: return the expectation value of `observable` on `circuit`, as a float.
#
#       StatevectorEstimator().run([(circuit, observable)]).result()
#
#       is one job carrying one (circuit, observable) pair. The number is at
#       result[0].data.evs, and it comes back as a NumPy value, so wrap it.
#
#       The circuit has no measurement, and must not get one.
def expectation(circuit, observable):
    pass


# TODO: the same number, from counts instead of from the Estimator.
#
#       Z reads +1 for outcome "0" and -1 for outcome "1", so the average over
#       every shot is P(0) - P(1). The counts dict has one-character keys here.
def z_from_counts(counts):
    pass
