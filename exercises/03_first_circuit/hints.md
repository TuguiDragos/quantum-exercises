## Hint 1

Two lines, replacing the two TODOs.

`QuantumCircuit(1)` and `QuantumCircuit(1, 1)` are both valid Python, but they
build different things. The second argument is the number of classical bits, and
this exercise wants none of those.

## Hint 2

Gate methods on a circuit are short and lowercase, named after the gate itself:

- `qc.h(0)` - Hadamard
- `qc.x(0)` - NOT
- `qc.z(0)` - phase flip
- `qc.cx(0, 1)` - controlled-NOT

They mutate the circuit in place, so you call `qc.h(0)` on its own line. Writing
`qc = qc.h(0)` would throw away your circuit.

## Hint 3

```python
from qiskit import QuantumCircuit

qc = QuantumCircuit(1)
qc.h(0)
```
