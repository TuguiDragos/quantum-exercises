## Hint 1

`joint_observable` needs two calls to `observable_at`, one per angle, combined
with `tensor`.

The only thing to get right is which one goes where. Alice has qubit 0, and
`tensor` puts its **argument** on the lower-numbered qubit. So Alice is the one
inside the brackets.

`correlation` is exercise 17's Estimator call with `bell()` as the circuit and
your joint observable as the observable.

## Hint 2

```python
def joint_observable(alice_angle, bob_angle):
    return observable_at(bob_angle).tensor(observable_at(alice_angle))
```

For `correlation`, build that observable, run it, read `.data.evs`, wrap it in
`float`.

Before writing `chsh`, check one number by hand. `correlation(0, 0)` should be
exactly `1.0`: same angle on both sides, and the Bell state always agrees. If you
get `1.0` for every pair of angles instead, the observable is not reaching the
Estimator.

## Hint 3

```python
def joint_observable(alice_angle, bob_angle):
    return observable_at(bob_angle).tensor(observable_at(alice_angle))


def correlation(alice_angle, bob_angle):
    observable = joint_observable(alice_angle, bob_angle)
    result = StatevectorEstimator().run([(bell(), observable)]).result()
    return float(result[0].data.evs)


def chsh(a0, a1, b0, b1):
    return correlation(a0, b0) + correlation(a0, b1) + correlation(a1, b0) - correlation(a1, b1)
```

Three plus, one minus, and the minus is on the pair where both parties used their
second angle. Put it anywhere else and S comes out at exactly 2, which looks like
a near miss and is actually the classical answer.
