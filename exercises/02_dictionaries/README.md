# 02 - Counts is just a dictionary

Every measurement result you will see in this course arrives in the same shape:

```python
{"00": 508, "11": 516}
```

Keys are the outcomes, as strings of bits. Values are how many of your shots
produced that outcome. That is the whole data structure. No quantum magic.

This exercise exists because the single most common stumbling block in the first
week is not superposition, it is reaching for `counts[0]` and getting a
`KeyError`. `"00"` is a string key, not a position. A dict is not a list.

## Your task

Implement three functions in `exercise.py`. You will use all three repeatedly for
the rest of the course.

| Function | Returns |
|---|---|
| `total_shots(counts)` | how many shots produced this result |
| `most_common(counts)` | the outcome that occurred most often |
| `outcome_probabilities(counts)` | `{outcome: estimated probability}` |

The runner calls your functions with several different dictionaries, so hardcoding
one answer will not pass.

## Run it

```bash
uv run qx run 2
```

## What you should take away

`outcome_probabilities` is doing real physics, even though it is three lines of
Python. Dividing a count by the number of shots is how you estimate a probability
from a finite sample, and it is exactly why your numbers never come out at a clean
0.5. You are sampling, not reading a value off the state.
