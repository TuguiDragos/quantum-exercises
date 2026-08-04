## Hint 1

`deutsch` is four lines and you have written three of them before. It is exercise
09's `qc_flip` with the oracle where the `z` used to be.

```python
qc.h(0)
# oracle goes here
qc.h(0)
qc.measure_all()
```

`is_balanced` is one line. Exercise 02 gave you the pattern for finding the key
with the largest value.

## Hint 2

Inserting one circuit into another:

```python
qc.compose(oracle, inplace=True)
```

`inplace=True` modifies `qc` rather than returning a new circuit. Without it,
nothing happens to `qc` and every function looks constant.

Exactly one `compose` call. If you write two, the two sign flips undo each other
and both balanced functions come back looking constant. That is worth trying once
on purpose, so you see what a wasted query costs.

For `is_balanced`, measuring `1` is the balanced verdict:

```python
max(counts, key=lambda outcome: counts[outcome]) == "1"
```

## Hint 3

```python
def deutsch(oracle: QuantumCircuit) -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.compose(oracle, inplace=True)
    qc.h(0)
    qc.measure_all()
    return qc


def is_balanced(counts: dict[str, int]) -> bool:
    return max(counts, key=lambda outcome: counts[outcome]) == "1"
```

Once it passes, try printing `Statevector` before the final Hadamard for a
constant and a balanced oracle. The two states differ only by which amplitude
carries the minus sign, and that sign is the entire answer.
