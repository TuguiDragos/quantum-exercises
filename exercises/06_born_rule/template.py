"""Exercise 06 - the Born rule, on paper first.

Fill in the TODOs, then run:  uv run qx run 6
"""

import math

from qiskit import QuantumCircuit

THETA = math.pi / 3

# Given. Do not change this circuit: the runner checks it is still the one you
# were asked to predict.
qc = QuantumCircuit(1)
qc.ry(THETA, 0)
qc.measure_all()

# TODO: fill in the probability of each outcome, worked out on paper.
#
#       Ry(theta)|0> = cos(theta/2)|0> + sin(theta/2)|1>
#
#       Those two numbers are amplitudes. The Born rule turns an amplitude into a
#       probability, and it is not the identity function.
#
#       math.cos and math.sin take radians, which is what THETA already is.
predicted = {
    "0": None,
    "1": None,
}
