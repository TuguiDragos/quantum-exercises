## Hint 1

`observable_x` is the same shape as `observable_z` was last time, with a
different letter.

For `observable_at`, `SparsePauliOp` accepts two lists that line up with each
other: one of Paulis, one of coefficients. The Paulis are `Z` and `X`, in that
order, and the coefficients are the two numbers in front of them.

For `to_x_basis`, the README names the gate. The part that is easy to forget is
that you still have to measure afterwards.

## Hint 2

```python
def observable_at(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[..., ...])
```

Fill in `math.cos(theta)` and `math.sin(theta)`, matching the order of the Paulis
above them. Sanity check before you run: `observable_at(0)` should come out as
plain `Z`, because `cos(0)` is 1 and `sin(0)` is 0.

For `to_x_basis`, three lines in this order:

```python
rotated = circuit.copy()
# rotate
# measure
return rotated
```

Without the `copy()`, `h` and `measure_all` append to the circuit you were handed
rather than to one of your own, so the caller's circuit comes back changed.

## Hint 3

```python
observable_x = SparsePauliOp("X")


def observable_at(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[math.cos(theta), math.sin(theta)])


def to_x_basis(circuit):
    rotated = circuit.copy()
    rotated.h(0)
    rotated.measure_all()
    return rotated
```

Worth sitting with: `to_x_basis` never mentions X. It applies a Hadamard and then
performs the one measurement the machine offers. "Measuring X" is not a different
instrument, it is the same instrument pointed at a state you turned first.
