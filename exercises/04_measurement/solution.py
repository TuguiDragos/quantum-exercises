"""Exercise 04 - reference solution."""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

SHOTS = 2048

qc = QuantumCircuit(1)
qc.h(0)
qc.measure_all()

sampler = StatevectorSampler(seed=1234)
result = sampler.run([qc], shots=SHOTS).result()
