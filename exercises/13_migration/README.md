# 13 - Code from 2021 that no longer runs

This is the exercise that pays for the whole course.

Search for a Qiskit tutorial and most of what you find was written before 2024.
It will not run. You will get an `ImportError` about `execute` or `Aer`, and
without knowing what changed, it is genuinely hard to tell whether the tutorial is
broken or you are.

The tutorial is broken. Here is how to fix it.

## What changed

Qiskit 1.0 removed a lot of what 0.x code takes for granted.

| 2021 code | Qiskit 2.x |
|---|---|
| `from qiskit import execute` | gone; use a primitive, or `transpile` plus `backend.run` |
| `from qiskit import Aer` | separate package: `from qiskit_aer import AerSimulator` |
| `from qiskit import IBMQ` | `from qiskit_ibm_runtime import QiskitRuntimeService` |
| `from qiskit import BasicAer` | `qiskit.providers.basic_provider` |
| `qiskit.opflow` | `qiskit.quantum_info` |
| `result.get_counts()` | `result[0].data.<register>.get_counts()` |

## Your task

`exercise.py` contains a real piece of 2021 code. Run it once before you change
anything, just to see how the runner reports the failure:

```bash
qx run 13
```

Then modernise it so that it does the same thing on Qiskit 2.x:

- keep the same circuit: a Bell state on two qubits, measured into two classical
  bits
- keep 1024 shots
- leave the finished V2 result in `result`
- leave the counts dictionary in `counts`

## The register name, again

The original code builds `QuantumCircuit(2, 2)`. That constructor names its
classical register `c`, not `meas`, because `measure_all()` is not involved.

So the counts live at `result[0].data.c.get_counts()`.

If you are ever unsure, do not guess:

```python
list(result[0].data.keys())  # ['c']
```

## Which replacement to pick

`execute()` did two things at once: transpile, then run. The modern equivalents
split those apart, which is more honest about what is happening.

For a local simulation like this one, `StatevectorSampler` from
`qiskit.primitives` is the shortest path and needs no extra package. It is exactly
what you used in exercises 04 and 05.
