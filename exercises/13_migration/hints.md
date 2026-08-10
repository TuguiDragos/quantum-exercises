## Hint 1

Work top to bottom.

The import line needs `QuantumCircuit` kept, and `Aer` and `execute` dropped. What
you add instead is the sampler you already used in exercises 04 and 05.

Then the last three lines collapse into two: create a sampler, run it, read the
counts.

## Hint 2

The shape you are aiming for:

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

...

sampler = StatevectorSampler()
result = sampler.run([qc], shots=SHOTS).result()
counts = result[0].data.???.get_counts()
```

For the `???`, the circuit is `QuantumCircuit(2, 2)`, so the register was created
by the constructor rather than by `measure_all()`. Its name is not `meas`. Print
`list(result[0].data.keys())` and read it off.

Note there is no `backend` variable any more. `StatevectorSampler` simulates
directly, so nothing needs to be chosen or fetched.

## Hint 3

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

SHOTS = 1024

qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

sampler = StatevectorSampler()
result = sampler.run([qc], shots=SHOTS).result()
counts = result[0].data.c.get_counts()
```

Using `AerSimulator` from `qiskit_aer` instead is also a legitimate migration, but
then you are on the `backend.run()` path and have to transpile first. The sampler
is the shorter road for a local run.
