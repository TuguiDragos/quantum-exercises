# 16 - A device that only measures Z

Here is a fact about every quantum computer IBM has ever built, and it is not a
detail: **the hardware can only measure Z.**

There is one measurement. It asks "is this qubit 0 or 1", which is the same as
asking for the value of `Z`. There is no button for X.

So when the last exercise computed `<X>` for you, something happened that the
Estimator did not advertise. This exercise is that something.

## Rotate the state, not the instrument

You cannot turn the detector. You can turn the state in front of it.

`H` swaps the X and Z axes. So applying `H` and then measuring Z tells you what a
measurement of X would have said:

```python
qc.h(0)  # X axis is now where Z was
qc.measure_all()  # the only measurement there is
```

Check it against something you already know. `|+>` is the state where a
measurement of X always gives +1. Apply `H` to `|+>` and you get `|0>`, which a
Z measurement reads as `0` every single time. Same answer, reached with the only
instrument the machine has.

This is the whole trick, and it is why "measuring in the X basis" and "applying H
then measuring" mean the same thing.

## An observable at any angle

Z and X are two directions. Nothing stops you asking about a direction between
them:

```
O(theta) = cos(theta) * Z + sin(theta) * X
```

At `theta = 0` that is Z. At `theta = pi/2` it is X. In between it is a genuine
observable in its own right, and its expectation value on `ry(phi)|0>` is

```
<O(theta)> = cos(theta - phi)
```

which is exactly what you would expect from two arrows and the angle between them.

A `SparsePauliOp` holds a weighted sum, so it takes a list of Paulis and a list
of coefficients:

```python
SparsePauliOp(["Z", "X"], coeffs=[0.8, 0.6])
```

Being able to name a direction is what the next exercise needs. Bell's theorem is
about what happens when two people measure along **different** angles, and until
now you had no way to write that down.

## Your task

1. `observable_x`, the `X` observable on one qubit.
2. `observable_at(theta)`, the weighted sum above.
3. `to_x_basis(circuit)`, returning a **new** circuit that measures X using the
   only measurement the hardware has.

Leave the circuit you were handed untouched. The runner reuses it.

## Run it

```bash
qx run 16
```
