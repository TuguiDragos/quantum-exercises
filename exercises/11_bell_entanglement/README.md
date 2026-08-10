# 11 - Bell state, and which bit is which

Two gates give you the most important two-qubit state there is:

```
(|00> + |11>) / sqrt(2)
```

Measure it and you get `00` about half the time and `11` about half the time. You
never get `01` or `10`. Not rarely: never, in the ideal case.

It is worth being careful about what that proves, because this is the single most
misquoted result in the subject.

Perfect agreement on its own is not mysterious. Flip one coin, seal the answer in
two envelopes, hand one to each person: they agree every time, and nothing quantum
happened. Everything you measure in this exercise is reproducible that way, so
nothing here rules out the two qubits having simply agreed in advance.

What no pair of envelopes can reproduce is the pattern that appears when the two
qubits are measured along **different** axes. That is Bell's theorem, it is why
this state carries his name, and exercise 20 is where you actually measure it.

## The endianness trap

Qiskit orders bits **little-endian**. In a counts key like `"01"`:

```
  "01"
   ||
   |+--- qubit 0   (rightmost)
   +---- qubit 1
```

The rightmost character is qubit 0. Most textbooks write it the other way round,
so this is the number one source of "my gates are on the wrong qubit" confusion.

Concretely: apply `x` to qubit 0 of a fresh two-qubit circuit, measure, and the
counts key you get back is `"01"`, not `"10"`.

## Your task

1. Build `qc`, a circuit preparing `(|00> + |11>) / sqrt(2)`. Two gates.
2. Set `label_q0_only` to the counts bitstring meaning "qubit 0 measured 1, qubit
   1 measured 0".
3. Set `impossible_outcomes` to the set of bitstrings that an ideal Bell state can
   never produce.

Do not add measurements to `qc`; the runner adds them when it needs them.

## Run it

```bash
qx run 11
```

## Looking ahead

Point 3 is true for a perfect simulator. On real hardware in exercise 14 you will
see `01` and `10` anyway, at a few percent. Those are not a mistake in your
circuit and not a violation of the physics. They are noise, and exercise 15 is
about reading them honestly.
