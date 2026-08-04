# 08 - Gates are matrices

A gate is a unitary matrix. A circuit made of gates is the product of those
matrices. Qiskit will hand you that product:

```python
from qiskit.quantum_info import Operator

Operator(qc).data  # the matrix, as a numpy array
Operator(qc).is_unitary()  # True for anything without measurement
```

Being able to look at this is what turns "I followed a tutorial" into "I know what
my circuit does".

## Your task

Build a two-qubit circuit whose matrix is the **controlled-Z** gate, using only
`h` and `cx` gates.

Controlled-Z flips the sign of the `|11>` component and leaves everything else
alone:

```
CZ = diag(1, 1, 1, -1)
```

Qiskit has a `qc.cz(0, 1)` method, and this exercise forbids it. The point is to
discover that CZ and CNOT are the same gate wearing a different hat: a Hadamard on
the target before and after a CNOT converts one into the other.

Three gates are enough.

## The endianness trap

When you print a 4x4 matrix, the rows and columns are indexed by basis states in
the order `|00>, |01>, |10>, |11>`. In Qiskit those labels are **little-endian**:
the rightmost character is qubit 0.

So `|01>` means qubit 1 is in state 0 and qubit 0 is in state 1. This is the
opposite of most textbooks, and it is the single most common source of "my matrix
looks transposed" confusion. Exercise 09 makes you use it for real.

For controlled-Z it happens not to matter, since CZ is symmetric in its two
qubits. That is a small mercy, and it will not last.

## Run it

```bash
uv run qx run 8
```
