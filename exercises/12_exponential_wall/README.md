# 12 - Why the simulator runs out

Everything you have run so far ran on your laptop. That should bother you.

If a laptop can do it, why is anyone building refrigerators the size of a room
and cooling them to fifteen millikelvin? This exercise is the answer, and it is
arithmetic rather than physics.

## Two ways to write down n bits

A classical register of `n` bits is `n` bits. Fifty of them is fifty bits, which
is seven bytes, which is nothing. The register holds one value at a time, and to
write it down you write down that one value.

A quantum state of `n` qubits is not one value. It is an amplitude for **every**
outcome at once:

```
n qubits  ->  2^n amplitudes
```

One qubit has two outcomes, two qubits have four, three have eight. Each
amplitude is a complex number, and Qiskit stores it as `complex128`: two 64-bit
floats, one real and one imaginary, so **16 bytes each**.

```
classical:  n bits          ->  n / 8 bytes
quantum:    2^n amplitudes  ->  2^n * 16 bytes
```

At fifty, that is seven bytes against sixteen pebibytes. The gap is not large. It
is a different kind of number.

## Sixteen bytes makes the table tidy

Every ten qubits the figure stays 16 and only the unit moves up:

| qubits | amplitudes | to simulate | classical register |
|---|---|---|---|
| 10 | 1024 | 16 KiB | 2 bytes |
| 20 | about a million | 16 MiB | 3 bytes |
| 30 | about a billion | 16 GiB | 4 bytes |
| 40 | about a trillion | 16 TiB | 5 bytes |
| 50 | about a quadrillion | 16 PiB | 7 bytes |

Every qubit you add doubles the left column and adds one bit to the right one.

The units above are binary: a kibibyte is 1024 bytes rather than 1000. That is
also how `BUDGET_BYTES` is written in `exercise.py`, so the two never disagree by
a few percent the way GB and GiB do.

## The sentence people get wrong

It is tempting to conclude that a quantum computer "stores 2^n numbers at once",
and that this is where the power comes from. It is not, and the difference
matters.

The exponential cost above is the cost of **simulating** the state on a classical
machine, because a classical machine has to write every amplitude down. The
quantum computer does not write them down. It is in that state, and when you
measure it you get **one** outcome, not 2^n numbers. The amplitudes are not
readable storage.

So what does the arithmetic prove? Only that past a few dozen qubits nobody can
check your answer by simulation any more. That is a genuine and important fact,
and it is not the same claim as "a quantum computer is exponentially faster",
which is a separate and much harder question the field has not finished
answering.

## What it changes for you

Up to here you could always check your work against a simulator that knew
everything. Exercise 07 printed the whole statevector. Exercise 08 printed the
whole matrix.

Past a few dozen qubits, that safety net is gone, and there is no replacement for
it. The rest of Act III is about working without it: running on a real device,
reading a noisy result honestly, and correcting what can be corrected.

## Your task

In `exercise.py`, fill in three functions.

| Name | What it returns |
|---|---|
| `amplitudes_for(n)` | how many amplitudes a statevector of `n` qubits has |
| `quantum_bytes_for(n)` | how many bytes those amplitudes occupy |
| `classical_bytes_for(n)` | how many bytes an `n`-bit classical register needs |

The last one is the one to be careful with. Bytes hold eight bits, and a register
of nine bits still needs two bytes rather than one and an eighth, so it rounds
**up**.

The runner checks the first two against a statevector it actually builds, at
sizes small enough to be safe, and everything larger by arithmetic alone. Nothing
here allocates gigabytes, on your machine or in CI.

It also times those builds, so you can watch the doubling happen rather than take
it on faith.

## Run it

```bash
qx run 12
```

## What you should take away

When someone tells you they simulated a quantum algorithm, the first useful
question is how many qubits. Under about 30 it runs on a laptop. Above about 50
nothing is holding the whole state, so either the claim needs another look or
they used a method that never stores it. Tensor networks and their relatives do
reach further, by exploiting the structure of one particular circuit rather than
writing down every amplitude, and that is a narrower claim than it first sounds.
