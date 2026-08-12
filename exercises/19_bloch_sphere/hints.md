## Hint 1

`observable_y` is built exactly like the two given above it. One letter changes.

For `bloch_vector`, you already have everything: `expectation` is sitting in the
file, and you have three observables. Call it three times on the same circuit,
once per axis, and return the answers in the order `(x, y, z)`.

Check yourself before moving on. An empty one-qubit circuit is the state `|0>`,
and it should come back as `(0, 0, 1)`. If your z is not 1, it is not `<Z>` you
are computing.

## Hint 2

```python
observable_y = SparsePauliOp("Y")


def bloch_vector(circuit):
    return (
        expectation(circuit, observable_x),
        expectation(circuit, observable_y),
        expectation(circuit, observable_z),
    )
```

For `angles`, take the two halves separately.

`theta` comes from the height: unpack the triple, get the length with Pythagoras
in three dimensions, and take `math.acos` of `z / length`. Do not assume the
length is 1. It is 1 for every state here, but computing it costs one line and
keeps the function honest.

`phi` comes from the shadow the point casts on the equator, which is just the
`(x, y)` pair. The angle of a two-dimensional vector is `math.atan2`, and it
wants `y` before `x`.

## Hint 3

```python
def angles(vector):
    x, y, z = vector
    length = math.sqrt(x * x + y * y + z * z)
    theta = math.acos(max(-1.0, min(1.0, z / length)))
    phi = math.atan2(y, x)
    return theta, phi
```

Three things worth knowing about that last line.

`math.atan2(y, x)` and not `atan2(x, y)`. Swapping them measures the angle from
the Y axis instead of from X, so `|+>` comes back as `pi/2` where it should be
`0`. The two orders agree only where `x` and `y` are equal.

Do not reach for `atan(y / x)`. It cannot tell `|+>` from `|->`, because both
have `y / x` equal to zero, and it divides by zero on the Y axis. `atan2` keeps
the two signs apart and handles the axes.

The clamping in `acos` is defensive. On the states this exercise uses the
Estimator returns an exact 1 and -1 at the poles, so the ratio lands in range on
its own. It stops being guaranteed the moment the numbers come from anywhere
less exact, a sampled estimator for instance, and `math.acos` raises `ValueError`
rather than returning something slightly wrong.
