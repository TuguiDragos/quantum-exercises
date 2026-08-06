## Hint 1

The first TODO is a single method call on `qc`, with no arguments. Its name says
exactly what it does: measure all of them.

The second TODO is one line with three parts: run, wait, assign.

## Hint 2

For the run, build it up in your head from the inside out:

```python
sampler.run([qc], shots=SHOTS)  # a job, still not the answer
sampler.run([qc], shots=SHOTS).result()  # the answer
```

The square brackets are not decoration. V2 primitives are designed to submit many
circuits in one go, so the argument is always a list, even when there is only one
circuit in it.

## Hint 3

```python
qc.measure_all()

sampler = StatevectorSampler(seed=1234)
result = sampler.run([qc], shots=SHOTS).result()
```

If you want to see the trap for yourself, comment out `qc.measure_all()` and run
again. You will get a warning rather than an error, and an empty result.
