## Hint 1

`SparsePauliOp` takes the Pauli as a plain string, the same way `QuantumCircuit`
takes a number of qubits:

```python
observable_z = SparsePauliOp("Z")
```

For `expectation`, look at the shape of the Sampler call you already know. The
Estimator is the same shape, except each item in the list is a tuple of
`(circuit, observable)` rather than a bare circuit.

## Hint 2

The Estimator call, spelled out:

```python
result = StatevectorEstimator().run([(circuit, observable)]).result()
```

`result[0]` picks your one pair, exactly as `result[0]` picked your one circuit
with the Sampler. From there the value is `.data.evs`, not `.data.meas`: nothing
was measured into a classical register, so there is no register to name.

For `z_from_counts`, write down what you are averaging. Each `"0"` shot
contributes +1 and each `"1"` shot contributes -1, and you divide by the total.

## Hint 3

```python
observable_z = SparsePauliOp("Z")


def expectation(circuit, observable):
    result = StatevectorEstimator().run([(circuit, observable)]).result()
    return float(result[0].data.evs)


def z_from_counts(counts):
    shots = sum(counts.values())
    return (counts.get("0", 0) - counts.get("1", 0)) / shots
```

`counts.get("0", 0)` rather than `counts["0"]`: an outcome that never occurred is
absent from the dict, not present with a zero, which is the trap exercise 02 set
up for exactly this moment.
