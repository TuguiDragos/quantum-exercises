# 15 - Reading a noisy result honestly

Exercise 11 told you a Bell state can never produce `01` or `10`.

Exercise 14 produced them anyway:

```
{"00": 507, "11": 448, "01": 25, "10": 44}
```

Those are not illustrative numbers. That is a real run of the exercise 14 circuit
on `ibm_fez`, a 156-qubit IBM Heron processor, 1024 shots, on 4 August 2026.
Sixty-nine of those shots came back with the two qubits disagreeing, which the
theory says is impossible.

Both of those statements are correct. The first describes an ideal Bell state, a
mathematical object. The second describes a physical device made of
superconducting metal held near absolute zero, where qubits lose coherence, gates
are slightly off, and readout sometimes reports the wrong bit.

The instinct at this point is to assume you made a mistake and go hunting through
your circuit. That instinct is wrong, and unlearning it is the last thing this
course has to teach you.

## The professional habit

You do not ask "is my result clean?" You ask "how far from ideal is it, and is
that within what this machine normally delivers?"

For a Bell state the natural measure is how often the two qubits agreed:

```
agreement = (count("00") + count("11")) / total_shots
```

An ideal Bell state gives 1.0. The real `ibm_fez` run above gives 0.933. Around
0.5 would mean the qubits were never entangled, and *that* is a real bug worth
hunting.

So the number tells you which situation you are in. Without it, you are guessing.

## Your task

Implement two functions and answer one question in `exercise.py`:

- `agreement_rate(counts)` - fraction of shots where the two qubits agreed
- `disagreement_rate(counts)` - fraction where they disagreed
- `explanation` - what accounts for the `01` and `10` shots in the counts above

The two rates must always add up to 1, because every shot falls into exactly one
of the two groups.

## Run it

```bash
qx run 15
```

## Where this goes next

Quantifying error is the entire reason the field cares about error correction. A
single physical qubit is too unreliable to compute with; the plan is to build one
reliable logical qubit out of many unreliable physical ones. Everything past this
course starts from the number you just learned to compute.
