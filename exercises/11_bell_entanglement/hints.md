## Hint 1

For the circuit: exercise 03 gave you the gate that creates superposition, and
exercise 08 used the controlled gate that flips a target when its control is 1.
You need one of each, in that order.

For `label_q0_only`: write the two characters down, then ask yourself which end of
the string qubit 0 sits at. The README has a diagram.

## Hint 2

The circuit is:

```python
qc.h(0)  # qubit 0 into superposition
qc.cx(0, 1)  # qubit 1 flips when qubit 0 is 1
```

The `cx` is what entangles them. Drop it and qubit 1 is never touched at all: it
stays `0`, you see only `00` and `01`, and knowing one qubit tells you nothing
about the other. The `cx` is what ties the two together. Note what it does not do:
qubit 0 has no definite value when `cx` runs, so nothing is copied onto qubit 1.
Copying a superposition is exactly what the no-cloning theorem forbids.

For the bitstring: qubit 0 is the **rightmost** character. So "qubit 0 is 1" means
the right character is `1`, and "qubit 1 is 0" means the left character is `0`.

For the impossible outcomes: the state is a mix of `|00>` and `|11>`. Those are the
ones you get. List the other two.

## Hint 3

```python
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

label_q0_only = "01"

impossible_outcomes = {"01", "10"}
```

Yes, `"01"` appears in both answers, and it means two different things. In
`label_q0_only` it is a bit ordering question. In `impossible_outcomes` it is a
physics question about which results the state can produce.
