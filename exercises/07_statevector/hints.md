## Hint 1

Both circuits start the same way. From |0>, only one common gate gets you to an
even superposition of |0> and |1>, and you already used it in exercise 03.

After that, each circuit needs one more gate that touches only the |1> amplitude.

## Hint 2

Here is what the single-qubit phase gates do to the amplitude of |1>, leaving |0>
untouched:

| Gate | Effect on the |1> amplitude |
|---|---|
| `z` | multiply by -1 |
| `s` | multiply by i |
| `t` | multiply by e^(i pi/4) |

You want a factor of `i` for `qc_a`, and a factor of `-1` for `qc_b`.

Check your work as you go:

```bash
uv run python -c "
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
qc = QuantumCircuit(1); qc.h(0); qc.s(0)
print(Statevector(qc))
"
```

## Hint 3

```python
qc_a = QuantumCircuit(1)
qc_a.h(0)
qc_a.s(0)

qc_b = QuantumCircuit(1)
qc_b.h(0)
qc_b.z(0)
```

For `qc_b`, `qc_b.x(0)` followed by `qc_b.h(0)` also lands on the same state, and
passes for the same reason.
