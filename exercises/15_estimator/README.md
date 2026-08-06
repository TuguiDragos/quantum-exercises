# 15 - The Estimator, and what it returns

Every exercise so far ended in a histogram. You ran a circuit, shots came back,
you counted them. That is the Sampler, and it answers one question: what comes
out?

There is a second primitive, and almost every serious quantum algorithm is built
on it rather than on counts.

## What an expectation value is

Pick something you can measure. Give each outcome a number. The expectation value
is the average of that number over the shots.

The simplest observable is `Z`. It reads **+1** for outcome `0` and **-1** for
outcome `1`, so its average is

```
<Z> = P(0) * (+1) + P(1) * (-1) = P(0) - P(1)
```

One number, saying where the qubit sits between the two poles:

```
state    P(0)   P(1)    <Z>
|0>       1      0      +1
|1>       0      1      -1
|+>      0.5    0.5       0
```

`<Z> = 0` for `|+>` is not an absence of information. It says the two outcomes
cancel exactly, which is a strong claim, not an empty one.

## Why a separate primitive

You could sample and average it yourself, and in this exercise you will, to prove
the two agree. The Estimator exists because on hardware it does more than divide.
It breaks an observable into measurements the device can actually perform, runs
them, and recombines the results. For anything past a single Pauli, that
bookkeeping is the whole job.

An observable is a `SparsePauliOp`:

```python
from qiskit.quantum_info import SparsePauliOp

SparsePauliOp("Z")
```

and a run looks like the Sampler, except each item is a `(circuit, observable)`
pair rather than a bare circuit:

```python
result = StatevectorEstimator().run([(circuit, observable)]).result()
value = float(result[0].data.evs)
```

Note `.evs`, not `.meas`. There is no classical register, because nothing was
measured into one. So do **not** call `measure_all()` on a circuit you hand to the
Estimator. The observable is what says what to measure, and a leftover measurement
only gets in the way.

`evs` arrives as a NumPy value rather than a Python `float`. It prints the same
and compares the same, but `float()` around it keeps the rest of your code
predictable.

## Your task

1. `observable_z`, the `Z` observable on one qubit.
2. `expectation(circuit, observable)`, returning the value as a plain `float`.
3. `z_from_counts(counts)`, the same number worked out from a counts dict.

The third one is the point of the exercise. Two routes, one number.

## Run it

```bash
qx run 15
```
