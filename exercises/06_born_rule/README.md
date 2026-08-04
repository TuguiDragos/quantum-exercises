# 06 - The Born rule, on paper first

Up to now you ran a circuit and looked at what came out. This exercise reverses
the order: you predict the numbers first, and only then does the runner sample.

That reversal is the whole point. If you can predict the histogram, you understand
the state. If you can only recognise it afterwards, you do not yet.

## The rule

A single qubit's state is two complex amplitudes:

```
|psi> = a|0> + b|1>
```

The Born rule says the probability of measuring an outcome is the **squared
magnitude** of its amplitude:

```
P(0) = |a|^2        P(1) = |b|^2
```

Squared. This is the step people skip. An amplitude of 0.866 does not mean an 87%
chance, it means a 75% chance. Amplitudes are not probabilities, and unlike
probabilities they can be negative or complex.

The circuit in `exercise.py` applies `ry(pi/3)` to a qubit starting in state 0.
The `ry` gate rotates by an angle in a plane, and it produces:

```
Ry(theta)|0> = cos(theta/2)|0> + sin(theta/2)|1>
```

Note the **half angle**. That trips people up too.

## Your task

Fill in `predicted` with the probability of each outcome. Work it out on paper.

The runner then samples the circuit 4096 times and compares your prediction
against what actually came out, at a tolerance of four standard errors.

## About that tolerance

Your prediction is never compared for exact equality against the counts, because
sampling is random. With N shots, a proportion p has a standard error of

```
SE = sqrt(p(1-p)/N)
```

At 4096 shots and p = 0.75, that is about 0.0068, so roughly 28 counts. The runner
accepts anything within four of those. A correct answer passes essentially always;
a wrong one, like confusing amplitude with probability, is off by far more.

## Run it

```bash
uv run qx run 6
```
