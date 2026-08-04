## Hint 1

Three built-ins do almost all the work here: `sum`, `max`, and a dict
comprehension.

For `total_shots`, remember that a dict has three views: `.keys()`, `.values()`
and `.items()`. You want the one holding the numbers.

## Hint 2

`max(counts)` alone gives the largest **key** in alphabetical order, which is not
what you want. `max` takes a `key=` argument telling it what to rank by:

```python
max(counts, key=lambda outcome: counts[outcome])
```

Read that as: go through the outcomes, and rank each one by the number it maps to.

For the probabilities, a dict comprehension has the shape
`{k: f(v) for k, v in counts.items()}`.

## Hint 3

```python
def total_shots(counts):
    return sum(counts.values())


def most_common(counts):
    return max(counts, key=lambda outcome: counts[outcome])


def outcome_probabilities(counts):
    shots = total_shots(counts)
    return {outcome: count / shots for outcome, count in counts.items()}
```

Note `/` and not `//`. Integer division would turn every probability into 0.
