# 19 - The picture behind the numbers

Exercise 17 gave you one expectation value. Exercise 18 showed you how to get one
along an axis the hardware cannot read directly. This exercise takes three of
them and turns a single qubit into a point you can look at.

## Three numbers are enough

A one-qubit state has two complex amplitudes, which is four real numbers.
Normalisation removes one, and global phase removes another, so only **two**
degrees of freedom survive. Two degrees of freedom is a surface, and the surface
is a sphere.

The three coordinates of the point are the three expectation values you already
know how to compute:

```
x = <X>        y = <Y>        z = <Z>
```

That is the whole construction. No new machinery, just the same primitive called
three times with a different Pauli each time.

## Where the familiar states land

| state | x | y | z | where |
|---|---|---|---|---|
| `\|0>` | 0 | 0 | +1 | north pole |
| `\|1>` | 0 | 0 | -1 | south pole |
| `\|+>` | +1 | 0 | 0 | equator, front |
| `\|->` | -1 | 0 | 0 | equator, back |
| `\|+i>` | 0 | +1 | 0 | equator, right |
| `\|-i>` | 0 | -1 | 0 | equator, left |

Notice what the poles are. `|0>` and `|1>` are the two outcomes your device can
report, and they sit at opposite ends of the sphere. Everything else is somewhere
in between, and "in between" is exactly what superposition means geometrically.

## Why the length is always 1

For any state a circuit without measurement can prepare,

```
x^2 + y^2 + z^2 = 1
```

The point is always **on** the surface, never inside it. Points strictly inside
exist and describe mixed states, which is what you get when the qubit is
entangled with something else or has been damaged by noise. This exercise stays
on the surface.

## Global phase, finally visible

Exercise 07 told you global phase is physically meaningless and that the runner
therefore compares with `equiv` rather than `==`. You had to take that on trust,
because every amplitude genuinely changed.

Here you can see it. Multiply the whole state by `i` and all three expectation
values come back **identical**, because the point did not move. Global phase is
one of the two degrees of freedom the sphere threw away, and a coordinate system
that does not encode it cannot be confused by it.

## The half angle, resolved

Exercise 06 made a point of `Ry(theta)` producing `cos(theta/2)` and
`sin(theta/2)`, and warned you the half was easy to miss. On the sphere the same
gate rotates by exactly `theta`, with no half in sight.

Both statements are true, and neither one causes the other. The half is in the
amplitudes before any sphere is drawn: `Ry(theta)` is `exp(-i * theta * Y / 2)`,
and the 2 sitting in that exponent is the whole of it. The sphere does not put it
there and does not take it away.

What the two do is keep different books, and you can watch them disagree. Set
`theta = 2 * pi`. The Bloch vector is back exactly where it started, so the
sphere reports a full turn and nothing to show for it. The state is now `-|0>`.
Turn again, to `4 * pi`, and the minus sign goes away too.

So the sphere comes home after one turn and the state needs two, and that is the
factor of two, stated as something you can measure. The sphere is not lying about
the first turn. It simply has no column for the sign that turn cost, because a
global phase is one of the two degrees of freedom it threw away above.

## Your task

`expectation` is given. It is exercise 17's answer, so you do not write it twice.

| Name | What it is |
|---|---|
| `observable_y` | the Y observable on one qubit |
| `bloch_vector(circuit)` | the three coordinates, as `(x, y, z)` |
| `angles(vector)` | the pair `(theta, phi)` that locates the point, in radians |

`theta` is measured **down from the north pole**, so `|0>` is 0 and the equator
is `pi/2`. That is `arccos(z / length)`.

`phi` is measured **around the equator starting from +X**, so `|+>` is 0 and
`|+i>` is `pi/2`. That is `atan2(y, x)`, and note that `math.atan2` takes `y`
first. The order looks backwards and it is the most common mistake here.

Together they place the point exactly, which is the claim this exercise makes: a
state written with four real numbers has only two that anything can measure.

`theta` is also what makes the previous section checkable. Run it on a circuit
built from `ry(theta)` and you should get `theta` back, not half of it.

## Run it

```bash
qx run 19
```

The first thing it prints is the sphere itself, drawn twice: once from the side,
where you can see how far down from `|0>` the point sits, and once from above,
where you can see which way round the equator it went. The `*` in both is placed
by your own three numbers, not by the runner's.
