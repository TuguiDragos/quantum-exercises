"""Exercise 19 - the picture behind the numbers.

Fill in the TODOs, then run:  qx run 19
"""

import math

from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

# Given: exercise 17's answer, so you do not write it a second time.
observable_z = SparsePauliOp("Z")
observable_x = SparsePauliOp("X")


def expectation(circuit, observable):
    """The expectation value of `observable` on `circuit`, as a float."""
    result = StatevectorEstimator().run([(circuit, observable)]).result()
    return float(result[0].data.evs)


# TODO: the Y observable on a single qubit, the same way the other two are built.
observable_y = None


# TODO: return the three Bloch coordinates of `circuit` as (x, y, z).
#
#       Each one is an expectation value: x is <X>, y is <Y>, z is <Z>. Call
#       `expectation` once per axis and return the three numbers in that order.
#
#       The circuit has no measurement, and must not get one.
def bloch_vector(circuit):
    return None


# TODO: return the two angles that locate the point, as (theta, phi).
#
#       theta is the polar angle, measured down from the +Z axis, so |0> is 0
#       and |1> is pi. It depends only on the height and the length:
#
#           theta = arccos(z / length)
#
#       phi is the azimuth, measured around the equator starting from +X, so
#       |+> is 0 and |+i> is pi/2. It is the angle of the shadow the point casts
#       on the equator:
#
#           phi = atan2(y, x)
#
#       math.atan2 takes y FIRST. That order looks backwards and is the single
#       most common mistake here. It returns a value between -pi and pi, which
#       is what the runner expects, so do not shift it.
def angles(vector):
    return None
