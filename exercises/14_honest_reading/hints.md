## Hint 1

Both functions have the same shape: add up the shots on some outcomes, then divide
by the total number of shots.

`AGREEING` and `DISAGREEING` are already defined at the top of the file, so you do
not need to write the outcome names out again.

For `explanation`, ask yourself what would have to be true for each of the three
answers, and check it against the numbers. 93% of the shots agreed.

## Hint 2

The one trap is missing keys. Look at the last test case in the runner's output:
some results simply do not contain `10` at all. `counts["10"]` raises `KeyError`;
`counts.get("10", 0)` returns 0.

```python
shots = sum(counts.values())
agreed = sum(counts.get(outcome, 0) for outcome in AGREEING)
return agreed / shots
```

For the question: if the circuit were wrong, agreement would be near 50%, not 93%.
If an ideal Bell state genuinely produced those outcomes, a noiseless simulator
would show them too, and it does not.

## Hint 3

```python
def agreement_rate(counts):
    shots = sum(counts.values())
    return sum(counts.get(outcome, 0) for outcome in AGREEING) / shots


def disagreement_rate(counts):
    shots = sum(counts.values())
    return sum(counts.get(outcome, 0) for outcome in DISAGREEING) / shots


explanation = "noise"
```

`1 - agreement_rate(counts)` also works for the second one, and makes the "they
must add to 1" property obvious.
