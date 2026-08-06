## Hint 1

Both functions are one line. Neither needs a loop.

Build the expression left to right, and print what you have at each step if it
helps:

```python
result  # PrimitiveResult
result[0]  # SamplerPubResult, your one circuit
result[0].data  # DataBin, the bag of classical registers
```

## Hint 2

From the `DataBin`, reach the register by name. `measure_all()` called it `meas`,
so `result[0].data.meas` gives you a `BitArray`.

A `BitArray` holds one bitstring per shot. Two useful things on it:

- `.get_counts()` tallies those bitstrings into a dict
- `.num_shots` says how many there are

If you get `AttributeError: 'DataBin' object has no attribute ...`, you guessed
the register name wrong. Run `list(result[0].data.keys())` to see the real one.

## Hint 3

```python
def read_counts(result):
    return result[0].data.meas.get_counts()


def read_shots(result):
    return result[0].data.meas.num_shots
```

`sum(read_counts(result).values())` would work just as well for the second one.
