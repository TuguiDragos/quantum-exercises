# 09 - Interference: amplitudes that cancel

Everything so far could be explained away by a sceptic. A qubit in superposition
gives 0 half the time and 1 half the time, and so does a coin. Nothing you have
measured yet rules out "it was secretly a random bit all along".

This exercise ends that argument, and it is the most important one in the course.

## The experiment

Apply a Hadamard to |0>. You get a 50/50 state. Now apply a **second** Hadamard.

If `h` really did randomise the qubit, then randomising something twice leaves it
random, and you would still see 50/50. That is what a coin does.

Instead you get `0`, every single time. The randomness undoes itself.

## Why

Track the amplitudes rather than the probabilities:

```
|0>  --H-->  ( |0> + |1> ) / sqrt(2)
```

Apply H again, to each part separately:

```
H|0>  =  ( |0> + |1> ) / sqrt(2)
H|1>  =  ( |0> - |1> ) / sqrt(2)
```

Add them up and divide by sqrt(2):

```
|0> component:  (1/2) + (1/2)  =  1     amplitudes reinforce
|1> component:  (1/2) - (1/2)  =  0     amplitudes cancel
```

The `|1>` outcome does not become unlikely. It becomes **impossible**, because two
routes to it arrive with opposite signs and annihilate.

Probabilities can only ever add up. Amplitudes can subtract. That difference is
the entire reason a quantum computer can do anything a classical one cannot, and
you use it directly in exercise 10.

## The lever

Slip a `z` between the two Hadamards and you flip the sign of the `|1>` part
midway. Now the cancellation lands on the other outcome: you get `1` every time,
never `0`. One phase gate, applied when nothing was certain, and the certain
answer flips completely.

## Your task

In `exercise.py`:

1. `qc_undo`: two gates, so that the circuit does nothing at all.
2. `qc_flip`: the same, with one phase gate in the middle so it becomes a NOT.
3. `coin_model_prediction`: if `h` really were "randomise the qubit", what
   probability would you give the outcome `0` after two of them?

The runner runs both circuits and shows you what actually comes out.

## Run it

```bash
qx run 9
```
