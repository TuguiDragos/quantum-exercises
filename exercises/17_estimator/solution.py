"""Exercise 17 - reference solution."""

from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

observable_z = SparsePauliOp("Z")


def expectation(circuit, observable):
    result = StatevectorEstimator().run([(circuit, observable)]).result()
    return float(result[0].data.evs)


def z_from_counts(counts):
    shots = sum(counts.values())
    # +1 for every "0" shot, -1 for every "1" shot, averaged over the lot.
    return (counts.get("0", 0) - counts.get("1", 0)) / shots
