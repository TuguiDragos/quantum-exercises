# 07 - States, amplitudes, and global phase

Counts tell you what came out. A statevector tells you what the machine had before
you looked. In simulation you can inspect it directly, which is the single best
debugging tool you have, and it does not exist on real hardware.

```python
from qiskit.quantum_info import Statevector

Statevector(qc)  # the state this circuit prepares, starting from |0...0>
```

## Your task

Build two circuits, each starting from |0>:

| Circuit | Target state |
|---|---|
| `qc_a` | `(|0> + i|1>) / sqrt(2)` |
| `qc_b` | `(|0> - |1>) / sqrt(2)` |

Gates you will want: `h` puts a qubit into an even superposition, `z` flips the
sign of the `|1>` amplitude, and `s` multiplies it by `i`.

## Why the runner uses `equiv` and not `==`

Suppose you build `(|0> + i|1>)/sqrt(2)` and your neighbour builds
`(i|0> - |1>)/sqrt(2)`. Every amplitude differs, by a factor of `i` throughout.
Python's `==` says these are different states.

They are not. No measurement anywhere can distinguish them, ever. Multiplying the
whole state by a constant of magnitude 1 changes nothing observable, because the
Born rule squares magnitudes and `|i|^2 = 1`. That overall factor is called the
**global phase**, and it is not physical.

So the runner compares with `Statevector.equiv`, which ignores it:

```python
Statevector(qc).equiv(target)  # True up to global phase
Statevector(qc) == target  # False if the phases differ
```

The distinction matters: a *relative* phase, between one amplitude and another
inside the same state, is very real and shows up the moment you interfere the
parts. That is exactly the difference between `qc_a` and `qc_b` here.

## Run it

```bash
qx run 7
```
