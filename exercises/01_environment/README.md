# 01 - Your environment works

Before any quantum mechanics, one boring question has to be settled: does code you
write in this repository actually run, against the Qiskit that is actually installed?

Plenty of quantum tutorials fail at this step and never say so. You get an error
about `execute` or `Aer`, you assume you misunderstood the physics, and you stop.
You did not misunderstand anything. You were reading instructions for a version of
the library that no longer exists.

So the first exercise checks the ground you are standing on.

## Your task

Open `exercise.py` and do two things:

1. Import the `qiskit` package.
2. Set `qiskit_version` to the version string Qiskit reports about itself.

The runner compares your answer against the version genuinely installed in this
project's virtual environment. Copying a number from a blog post will not pass.

## Run it

```bash
qx run 1
```

## What you should take away

A Python package usually exposes its own version as `package.__version__`. That
attribute is the single most useful thing to print when something behaves
differently from a tutorial, because almost every "this doesn't work" in the
Qiskit world is a version mismatch.
