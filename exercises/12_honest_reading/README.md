# 12 - Reading a noisy result honestly

Exercise 09 told you a Bell state can never produce `01` or `10`.

Exercise 11 produced them anyway:

```
{"00": 471, "11": 448, "01": 55, "10": 50}
```

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

An ideal Bell state gives 1.0. A working IBM QPU in 2026 typically gives somewhere
around 0.90 to 0.98 for this circuit. Around 0.5 means the qubits were never
entangled, and *that* is a real bug worth hunting.

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
uv run qx run 12
```

## Where this goes next

Quantifying error is the entire reason the field cares about error correction. A
single physical qubit is too unreliable to compute with; the plan is to build one
reliable logical qubit out of many unreliable physical ones. Everything past this
course starts from the number you just learned to compute.
