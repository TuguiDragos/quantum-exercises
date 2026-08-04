# 10 - Deutsch's algorithm in one query

Exercise 09 showed that amplitudes cancel. This is what that buys you.

## The problem

Someone hands you a function `f` that takes one bit and returns one bit. You are
not allowed to look inside it. There are exactly four such functions:

| f | f(0) | f(1) | kind |
|---|---|---|---|
| constant zero | 0 | 0 | **constant** |
| constant one | 1 | 1 | **constant** |
| identity | 0 | 1 | **balanced** |
| not | 1 | 0 | **balanced** |

You do not need to know *which* function it is. You only need to answer one
question: **is it constant, or balanced?**

Classically this takes two evaluations. You compute `f(0)`, you compute `f(1)`,
and you compare. One evaluation is provably never enough: whatever single answer
you get, two functions remain consistent with it, one constant and one balanced.

Deutsch's algorithm answers it with **one** evaluation. This is a real, provable
separation, not a speedup that better classical code might catch up to.

## How the function is handed to you

Not as Python. As a circuit that flips the sign of an amplitude:

```
U_f |x>  =  (-1)^f(x) |x>
```

So an `|x>` where `f(x) = 1` comes back with a minus sign, and an `|x>` where
`f(x) = 0` is untouched. All four are written for you in `exercise.py`. Look at
them: a constant function either does nothing or negates everything, while a
balanced one negates exactly one of the two basis states.

## The algorithm

```
H  ->  U_f  ->  H  ->  measure
```

That is the whole thing, and it is exercise 09's circuit with the oracle in the
slot where you put `z`.

Which is exactly the point. The first `H` puts the qubit into both inputs at once,
so the single oracle call sees both. The oracle writes its answer into the *signs*
rather than into the value. The second `H` interferes those signs:

- **constant**: both amplitudes get the same sign, they reinforce on `|0>` and
  cancel on `|1>`, so you measure **0**
- **balanced**: the signs disagree, the cancellation lands the other way, so you
  measure **1**

You never learn `f(0)` or `f(1)` individually. You learn a relationship between
them, which is the only thing you were asked for, and that is what fits in one
query.

## Your task

Implement two functions in `exercise.py`:

- `deutsch(oracle)` builds the circuit above, including its measurement.
  `qc.compose(oracle, inplace=True)` inserts the oracle circuit into yours.
- `is_balanced(counts)` reads the verdict off the result.

The runner tries your implementation against all four functions.

## Run it

```bash
qx run 10
```

## Honesty about the scale

One query instead of two is not going to break anyone's encryption. Deutsch's
algorithm is a proof of concept, and it was published in 1985 precisely to show
that a separation exists at all.

What matters is the mechanism, because it does not stop here. Deutsch-Jozsa
generalises this to n bits, where classical needs up to 2^(n-1) + 1 queries and
the quantum circuit still needs one. Bernstein-Vazirani, Simon's algorithm and
ultimately Shor's are the same idea applied harder: get the answer into the phases,
then interfere so the wrong answers cancel.
