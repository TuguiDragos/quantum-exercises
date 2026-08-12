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
your circuit. That instinct is wrong, and unlearning it is the last thing Act III
has to teach you.

## The professional habit

You do not ask "is my result clean?" You ask "how far from ideal is it, and is
that within what this machine normally delivers?"

For a Bell state the natural measure is how often the two qubits agreed:

```
agreement = (count("00") + count("11")) / total_shots
```

An ideal Bell state gives 1.0. The real `ibm_fez` run above gives 0.933. Around
0.5 would mean the two qubits came out uncorrelated, which for this circuit means
the `cx` never ran, and *that* is a real bug worth hunting.

Read the number in one direction only. A low one tells you something is broken. A
high one does **not** tell you the qubits were entangled: exercise 11's sealed
envelopes agree every time too, and a device that simply reported `00` and `11`
in turn would score 1.0 without anything quantum happening at all. Settling that
question takes correlations along different axes, which is exercise 20.

What this number measures is distance from the ideal on the one axis you looked
at. That is the question this exercise asks, and without it you are guessing.

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
