# 03 - Your first circuit

A quantum circuit in Qiskit is an object you build up line by line. You create it
with a number of wires, then you call methods on it to add gates.

```python
qc = QuantumCircuit(2)  # two qubits, no classical bits
qc.h(0)  # Hadamard on qubit 0
qc.cx(0, 1)  # controlled-NOT, control 0, target 1
```

The Hadamard gate is where every course starts, because it is the cheapest way to
create superposition. Applied to a qubit sitting in state 0, it produces a state
that is equally likely to be measured as 0 or as 1.

## Your task

In `exercise.py`, build a circuit with exactly **one qubit and no classical bits**,
and apply a Hadamard gate to qubit 0. Leave the result in `qc`.

Do not add a measurement. This exercise looks at the circuit as a matrix, and a
measurement is not a matrix. Exercise 04 adds the measurement.

## Run it

```bash
uv run qx run 3
```

## What you should take away

The runner does not compare your code to the solution as text. It builds the
matrix your circuit represents and compares it to the matrix a Hadamard gate
represents, using `Operator.equiv`.

`equiv` deliberately ignores global phase. If your circuit produces a matrix that
differs from Hadamard's by an overall factor like -1 or `i`, it still passes,
because no measurement can ever distinguish those two circuits. That is physics,
not leniency. You will meet this again in exercise 07.
