# 05 - Reading counts out of a V2 result

You have a result object. Your counts are inside it. Getting them out is the step
where almost every tutorial written before 2024 will lead you astray.

The old way, which no longer exists:

```python
counts = result.get_counts()  # AttributeError on Qiskit 2.x
```

The current way:

```python
counts = result[0].data.meas.get_counts()
```

That line is doing three separate things, and it is worth pulling apart rather
than memorising:

| Step | What it means |
|---|---|
| `result[0]` | pick the first circuit you submitted; V2 always runs a list |
| `.data` | open the bag of classical registers that circuit wrote to |
| `.meas` | the register named `meas`, which `measure_all()` created |
| `.get_counts()` | tally the raw per-shot bits into the dict you know |

## About that register name

`meas` is not a magic word. It is the name `measure_all()` happens to give the
register it creates. If you build your own register with
`ClassicalRegister(2, "output")`, your data lives at `.output` instead.

When you are unsure, ask:

```python
list(result[0].data.keys())  # ['meas']
```

An empty list means the circuit had no measurement, which is exercise 04's trap.

## Your task

Implement `read_counts` and `read_shots` in `exercise.py`. The runner calls them
with results from several different circuits, all built with `measure_all()`.

## Run it

```bash
uv run qx run 5
```

## What you should take away

`.get_counts()` is a convenience on top of the real data. The register holds one
bitstring per shot, in order; counts are just a tally of that list. If you ever
need per-shot data, for example to look at how results drift over a long run, it
is still there in the same object.
