# 20 - CHSH, the inequality that settles it

Exercise 11 left a debt. You built the Bell state, you saw the two qubits agree
every single time, and the README told you plainly that this proves nothing:

> Flip one coin, seal the answer in two envelopes, hand one to each person: they
> agree every time, and nothing quantum happened.

Everything you measured there, a shared coin reproduces. This exercise is where
that stops being true.

## The idea

Two people, Alice and Bob, one qubit each, from the same Bell pair. Each picks
one of two measurement angles and writes down the answer, `+1` or `-1`.

Run it many times and you can compute, for any pair of angles, the average of
Alice's answer times Bob's:

```
E(a, b) = <A(a) x B(b)>
```

Now combine four of those, two angles each:

```
S = E(a0, b0) + E(a0, b1) + E(a1, b0) - E(a1, b1)
```

That combination is chosen for one reason. Suppose the answers were decided in
advance, so that `A0`, `A1`, `B0`, `B1` are just numbers, each `+1` or `-1`,
sitting in envelopes before anyone measures. Factor the expression:

```
S = A0(B0 + B1) + A1(B0 - B1)
```

`B0` and `B1` are each `+1` or `-1`, so one of those brackets is always `0` and
the other is always `+2` or `-2`. Whatever is in the envelopes,

```
|S| <= 2
```

There are only sixteen ways to fill four envelopes. The runner tries all sixteen
and shows you the best any of them manages.

## What quantum mechanics does

For the Bell state, `E(a, b)` works out to `cos(a - b)`. Take

```
a0 = 0        a1 = pi/2
b0 = pi/4     b1 = -pi/4
```

and three of the four terms are `+cos(pi/4)` while the fourth subtracts a
`-cos(pi/4)`. They all add up rather than cancelling:

```
S = 4 * cos(pi/4) = 2 * sqrt(2) = 2.828...
```

Past 2. Not by a rounding error, by 40%. No set of envelopes can do that, which
means the answers were not in envelopes.

This is Bell's theorem, in the form John Clauser, Michael Horne, Abner Shimony
and Richard Holt put it in 1969 so that it could actually be run in a lab. It has
been run, with steadily fewer loopholes, and the 2022 Nobel Prize in Physics went
to Aspect, Clauser and Zeilinger for doing it.

## What you compute here, exactly

Worth being precise, in an exercise about being precise. `correlation` asks
`StatevectorEstimator` for an expectation value, and that is worked out from the
state vector rather than sampled from it: no shots, no error bars, and `S` comes
back as `2.828427...` on every run.

So what you produce is the quantum prediction, calculated exactly. A real Bell
test measures instead: it repeats each of the four angle pairs, ends up with a
number carrying a statistical uncertainty, and then has to shut the doors that
would let the envelopes back in. Two of those are detectors that miss too many
events, and two sides near enough that a signal could pass between them in time.
Closing both in one experiment was first done in 2015, by three groups within
months of each other.

That is not the last door. Whether the measurement settings were themselves free
of any prior influence is a loophole of its own, and it stayed open in 2015;
later experiments narrowed it by taking the settings from light that left distant
stars, and then quasars, long before the apparatus existed.

What this exercise settles is the arithmetic. The prediction is past 2, and no
assignment of answers in advance can reach it. That the world agrees with the
prediction is what the laboratories established, and it is why the names above
are on a Nobel citation rather than on a preprint.

## Building the observable

Alice measures qubit 0 and Bob measures qubit 1, so you need a two-qubit
observable that applies one single-qubit observable to each.

`tensor` puts its argument on the lower-numbered qubit:

```python
bob_observable.tensor(alice_observable)
```

which is the same little-endian rule as the counts strings in exercise 11. The
one written on the right is qubit 0.

## Your task

`observable_at` and the Bell circuit are given; they are exercise 18's answer and
exercise 11's answer.

1. `joint_observable(alice_angle, bob_angle)`, Alice on qubit 0.
2. `correlation(alice_angle, bob_angle)`, its expectation value on the Bell state.
3. `chsh(a0, a1, b0, b1)`, the four-term combination above.

## Run it

```bash
qx run 20
```
