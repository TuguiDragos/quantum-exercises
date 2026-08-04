# 04 - Measurement, or the result is empty

Exercise 03 built a circuit and looked at its matrix. That is the god's-eye view.
It is not what an experiment gives you.

To get numbers out, you have to measure, and measurement is not a gate. It is the
irreversible step where the quantum state stops being a superposition and becomes
one classical bit you can print. Everything before it is reversible; measurement
is not.

## The trap in this exercise

If you forget the measurement, Qiskit does **not** raise an error. It runs your
circuit and hands back a result with no data in it, along with a warning that is
very easy to scroll past:

> UserWarning: One of your circuits has no output classical registers and so the
> result will be empty. Did you mean to add measurement instructions?

You then spend twenty minutes wondering why your counts are missing. This is worth
meeting once, on purpose, in an exercise that tells you what happened.

## Your task

In `exercise.py`:

1. Add measurement to the circuit.
2. Run it with the sampler for `SHOTS` shots, and put the finished result in
   `result`.

Two details about the V2 API that catch everyone:

- `sampler.run(...)` takes a **list** of circuits. `run(qc)` fails; `run([qc])`
  works.
- `sampler.run(...)` returns a **job**, not an answer. You still have to ask the
  job for its result.

## Run it

```bash
uv run qx run 4
```

## What you should take away

`qc.measure_all()` is the quick way to measure everything: it adds a classical
register sized to your qubits and wires each qubit to it. The register it creates
is named `meas`, which matters in exercise 05 when you go looking for your data.
