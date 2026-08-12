# 14 - A Bell state on a real machine

Two qubits, two gates, one measurement. It is the smallest circuit that is worth
putting on real hardware: it takes seconds of QPU time, and what comes back is a
correlation you can read straight off the histogram together with the noise sitting
on top of it. The runner checks the state you built before anything is sent, so
you know it is the entangled one; the counts themselves prove correlation rather
than entanglement, and exercise 20 is where that distinction is settled.

## You do not need an IBM account

The runner picks the most real backend it can reach, in this order:

1. a real IBM QPU, if you have an account and one is available
2. a local simulator carrying a **noise model copied from real hardware**, so the
   results still look like an experiment
3. a plain noiseless simulator

Whichever it lands on is printed with your result, and `qx list` records it. You
can finish this exercise on a plane. To set up an account, see
`qx doctor --save-account`.

To force the offline path even when you do have an account:

```bash
QX_OFFLINE=1 qx run 14
```

## The step that is not optional

On a simulator you can hand over any circuit and it works. Hardware is not like
that. A QPU implements a small fixed set of physical operations, and its qubits
are not all connected to each other. Your circuit has to be rewritten into that
instruction set first. The result is called an **ISA circuit**, for Instruction
Set Architecture.

Submit a non-ISA circuit and it is rejected. There is no automatic fallback.

`h` is a good example: no IBM QPU implements a Hadamard directly. Transpiling
turns it into a sequence of `rz` and `sx` rotations that produce the same effect.
You can watch it happen:

```bash
QX_OFFLINE=1 uv run python -c "
from quantum_exercises.backends import get_backend, to_isa
from qiskit import QuantumCircuit
b = get_backend().backend
qc = QuantumCircuit(2); qc.h(0); qc.cx(0,1); qc.measure_all()
print('before:', dict(qc.count_ops()))
print('after :', dict(to_isa(qc, b).count_ops()))
"
```

## Your task

Implement two functions in `exercise.py`:

- `build_bell()` returns a two-qubit Bell circuit **with measurement**
- `to_isa(circuit, backend)` rewrites a circuit into that backend's instruction set

For the second one you want `generate_preset_pass_manager`, which builds a
transpiler configured for a specific backend, and then `.run()` on the circuit.

## Run it

```bash
qx run 14
```

If a real QPU picks up the job, this can sit in a queue for a while. The time
limit is 15 minutes; raise it with `qx run 14 --timeout 3600`.

## What you should expect to see

If you land on real hardware or the noise-modelled simulator, `01` and `10` will
show up, at a few percent. Exercise 11 said an ideal Bell state can never produce
those. Both statements are true, and reconciling them is exercise 15.
