"""Exercise 09 - interference: amplitudes that cancel.

Fill in the TODOs, then run:  qx run 9
"""

from qiskit import QuantumCircuit

# TODO: add exactly two gates so that qc_undo does nothing at all.
#       Both are the same gate. The second one undoes the first, even though
#       after the first one the qubit was in an even superposition.
qc_undo = QuantumCircuit(1)


# TODO: same two gates, with one phase gate slipped in between, so that the
#       whole circuit becomes a NOT: it turns |0> into |1> with certainty.
#       The middle gate must flip the sign of the |1> amplitude.
qc_flip = QuantumCircuit(1)


# TODO: suppose h really did just randomise the qubit, the way flipping a coin
#       randomises it. Under that wrong model, what is the probability of
#       measuring 0 after two of them? Give the number that model predicts,
#       not the number you will actually measure.
coin_model_prediction = None
