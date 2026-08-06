## Hint 1

CNOT applies an X to the target when the control is 1. You want something that
applies a Z to the target when the control is 1.

So the question becomes: how do you turn an X into a Z?

## Hint 2

The Hadamard gate swaps the X and Z axes. Concretely:

```
H X H = Z
```

So if you sandwich the target qubit of your CNOT between two Hadamards, the X that
CNOT applies becomes a Z.

Sandwich means one `h` before the `cx` and one after, both on the **target**
qubit, not the control.

Watch the matrix change as you experiment:

```bash
uv run python -c "
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
qc = QuantumCircuit(2); qc.cx(0,1)
print(Operator(qc).data.real)
"
```

## Hint 3

```python
qc = QuantumCircuit(2)
qc.h(1)
qc.cx(0, 1)
qc.h(1)
```

Because CZ is symmetric, `qc.h(0); qc.cx(1, 0); qc.h(0)` gives the same matrix and
passes too.
