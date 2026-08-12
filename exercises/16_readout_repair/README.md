# 16 - Correcting what readout got wrong

Exercise 15 taught you to measure how far a noisy result sits from the ideal one,
and to stop treating that distance as a bug in your circuit. That was the honest
half of the job. This is the other half.

Some of that distance can be taken back, and the cheapest part of it needs no new
physics at all. It needs a 4 by 4 matrix and the linear algebra you already have.

## Where the error is

Not every error happens while the circuit runs. A sizeable share happens in the
last microsecond, when the device decides whether the qubit it just probed was a
0 or a 1. It sometimes decides wrong.

That failure has a useful property: it does not care what your circuit did. It
corrupts the reading, not the state. So you can measure it once, on its own, and
then subtract it from anything you run afterwards.

## Measuring the lie

Prepare a state you already know the answer to, measure it, and write down what
came back.

Prepare `00`, and an honest device would report `00` every single time. A real one
reports `00` about 95% of the time and something else the rest. Do that for all
four two-qubit states and you have sixteen numbers:

```
                prepared
              00    01    10    11
        00  0.95  0.04  0.02  0.00
measured 01  0.03  0.94  0.00  0.02
        10  0.02  0.00  0.95  0.04
        11  0.00  0.02  0.03  0.94
```

Read a **column**: it says what the device reports when that state was prepared.
Each column is a probability distribution, so each column adds to 1.

Call that matrix `A`. It is a complete description of how this device lies about
readout.

## Undoing it

If `true` is the distribution your circuit really produced and `observed` is what
the device reported, then

```
observed = A @ true
```

That is just the matrix saying, for each prepared state, where its shots ended up.
And a matrix equation you can read forwards, you can solve backwards:

```
true = A^-1 @ observed
```

One inversion, and you have an estimate of the distribution you would have seen
on a device with perfect readout.

## Two honest warnings

**It can return counts that are impossible.** The inverse of a noisy matrix
applied to noisy data is not guaranteed to land on a valid probability
distribution. You will see this happen on the run this exercise gives you: two
outcomes come back slightly negative, and the agreement lands a fraction past
1.0. Neither is possible for anything a real device could produce.

That is not a bug in your code. It is the method extrapolating further than four
thousand shots can support. This exercise runs on a fixed seed, so you see it
every time; across seeds it turns up in about two runs in five, which makes it
the ordinary case rather than a staged one. Production tools avoid it by fitting
the nearest valid distribution rather than inverting outright, which trades a
little bias for an answer that is always physical. The raw inverse is the version
worth meeting first, because you can see every step of it, including this one.

**It only fixes readout.** The gates were noisy too, and no amount of readout
calibration touches that. You will not land at a perfect 1.0, and the gap that
remains after correction is the part of the damage that happened while the
circuit was still running.

## Your task

`prepare` is given. It is exercise 11's endianness rule and nothing more, so you
do not write it twice: the label `"01"` means qubit 0 was measured as 1, so it is
qubit 0 that gets the `x`.

The runner does all the sampling and hands you the counts, so both your functions
are pure and you can test them by hand.

| Function | What it does |
|---|---|
| `response_matrix(columns)` | the 4 by 4 matrix above, from one counts dict per prepared state |
| `corrected(matrix, counts)` | the counts you would have seen with perfect readout |

## Run it

```bash
qx run 16
```

## What you should take away

Error mitigation is not one technique, it is a family, and this is the cheapest
member of it. IBM's Runtime offers several more that work the same way in spirit:
measure how the device deviates, then correct for it. Twirled readout error
extinction is this idea, made robust. Zero-noise extrapolation runs your circuit
at several noise levels on purpose and extrapolates back to none.

None of them make the machine perfect. All of them buy back some of the distance
you learned to measure in exercise 15.
