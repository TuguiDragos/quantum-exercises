"""Exercise 13 - reference solution."""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

SHOTS = 1024

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

# execute() split into two explicit steps: pick a runner, then run.
sampler = StatevectorSampler()
result = sampler.run([qc], shots=SHOTS).result()

# QuantumCircuit(2, 2) names its classical register "c", so the data is at .c
counts = result[0].data.c.get_counts()
