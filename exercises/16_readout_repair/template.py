"""Exercise 16 - correcting what readout got wrong.

Fill in the TODOs, then run:  qx run 16
"""

import numpy as np
from qiskit import QuantumCircuit

# The four two-qubit outcomes, in the order the matrix rows and columns use.
LABELS = ("00", "01", "10", "11")


def prepare(label):
    """A circuit preparing that computational basis state, measured.

    Given: this is exercise 11's endianness rule and nothing else. The label
    "01" means qubit 0 was measured as 1, so the character on the RIGHT is the
    one that decides whether qubit 0 gets flipped.
    """
    qc = QuantumCircuit(2)
    if label[1] == "1":
        qc.x(0)
    if label[0] == "1":
        qc.x(1)
    qc.measure_all()
    return qc


# TODO: build the response matrix.
#
#       `columns` is a dict: prepared label -> the counts that came back.
#       Entry [i][j] is the probability of MEASURING LABELS[i] when LABELS[j] was
#       prepared, so column j is the counts for LABELS[j] divided by its own total.
#
#       Write the outer loop over the PREPARED label and the inner one over the
#       measured label, and the indices land the right way round.
#
#       Return a 4x4 numpy array. Each column should add up to 1.
def response_matrix(columns):
    return None


# TODO: undo the readout error.
#
#       Put `counts` into a vector in LABELS order, solve A @ true = observed for
#       true, and return the result as a dict label -> number.
#
#       np.linalg.solve(matrix, vector) does the solving.
#
#       Return the numbers as they come out. Do not clamp a negative entry to
#       zero: a negative is the raw method being honest about what the data
#       supports, the artifact points it out, and clamping it breaks the shot
#       total the runner checks.
def corrected(matrix, counts):
    return None
