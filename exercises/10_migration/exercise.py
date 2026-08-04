"""Exercise 10 - code from 2021 that no longer runs.

Run it once as-is to see how it fails, then modernise it:

    uv run qx run 10

Requirements for your rewrite:
  - same circuit: a Bell state on two qubits, measured into two classical bits
  - same shot count: SHOTS
  - leave the finished V2 result in `result`
  - leave the counts dictionary in `counts`
"""

# TODO: these imports no longer exist on Qiskit 2.x. Replace them.
from qiskit import Aer, QuantumCircuit, execute

SHOTS = 1024

# This part still works unchanged. Leave the circuit as it is.
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

# TODO: replace these three lines with the Qiskit 2.x way of running a circuit.
#       `result` should hold the finished V2 result, and `counts` the dictionary.
backend = Aer.get_backend("qasm_simulator")
job = execute(qc, backend, shots=SHOTS)
result = job.result()
counts = result.get_counts()
