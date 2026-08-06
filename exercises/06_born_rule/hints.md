## Hint 1

`THETA` is `pi/3`, so the half angle `THETA / 2` is `pi/6`. That is 30 degrees.

You need the cosine and the sine of 30 degrees, and then you need to do one more
thing to each of them.

## Hint 2

The Born rule is: probability equals the squared magnitude of the amplitude.

```
amplitude of "0" = cos(pi/6) = 0.8660...
amplitude of "1" = sin(pi/6) = 0.5
```

Those are not your answers yet. Square each one.

A good sanity check before you run: your two probabilities must add up to exactly
1. The two amplitudes above add to 1.366, which is how you can tell at a glance
that they are not probabilities.

## Hint 3

```python
predicted = {
    "0": math.cos(THETA / 2) ** 2,
    "1": math.sin(THETA / 2) ** 2,
}
```

That gives 0.75 and 0.25. Writing the literals `0.75` and `0.25` also passes, but
the expression keeps working if you change `THETA` to experiment.
