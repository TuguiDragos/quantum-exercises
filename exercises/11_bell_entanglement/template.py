"""Exercise 11 - Bell state, and which bit is which.

Fill in the TODOs, then run:  qx run 11
"""

from qiskit import QuantumCircuit

# TODO: add two gates so that qc prepares (|00> + |11>) / sqrt(2).
#       Put one qubit into superposition, then tie the second to it with a
#       controlled gate. On a definite value that gate copies. On a superposition
#       there is no value to copy, and it entangles instead.
#       Do not add measurements; the runner adds them itself.
qc = QuantumCircuit(2)


# TODO: which counts bitstring means "qubit 0 was measured as 1, qubit 1 as 0"?
#       Remember which end of the string qubit 0 lives at.
label_q0_only = None


# TODO: which outcomes can an ideal Bell state never produce?
#       Give a set of strings, for example {"00", "11"}.
impossible_outcomes = None
