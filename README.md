# quantum-exercises

[![ci](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml/badge.svg)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml)
[![weekly-verify](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml/badge.svg)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml)
[![verified against qiskit](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FTuguiDragos%2Fquantum-exercises%2Fbadges%2Fbadges%2Fqiskit.json)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml)

Twelve hands-on exercises that take you from an empty laptop to a quantum circuit
running on real IBM hardware. In the style of [rustlings](https://github.com/rust-lang/rustlings):
you edit a file, you run a command, you get told exactly what is wrong.

## Why this exists

Nearly every quantum computing tutorial on the internet was written for Qiskit
0.x. None of it runs any more. `execute()` was removed, `Aer` moved to its own
package, `IBMQ` became a different thing entirely, and the way you read your
results changed shape completely.

So beginners hit an `ImportError` on line 3 and conclude they are not smart enough
for quantum computing. They were just reading instructions for software that no
longer exists.

Everything here is verified weekly against the Qiskit that actually ships today.
The badge above shows which version was last checked and when.

## Quickstart

Three commands, assuming you have [uv](https://docs.astral.sh/uv/getting-started/installation/):

```bash
git clone https://github.com/TuguiDragos/quantum-exercises
cd quantum-exercises
uv run qx doctor
```

`qx doctor` tells you exactly what is missing and how to fix it. Then:

```bash
uv run qx next
```

No IBM account is needed. No PyPI install is needed. `uv` builds the environment
from the committed lockfile on first run.

## The commands

| Command | What it does |
|---|---|
| `uv run qx doctor` | check the environment, step by step |
| `uv run qx list` | every exercise and your progress |
| `uv run qx next` | the next thing to work on |
| `uv run qx run [n]` | check an exercise |
| `uv run qx watch [n]` | re-check automatically every time you save |
| `uv run qx hint [n]` | reveal one more hint |
| `uv run qx solution [n]` | show the answer, recorded as solved rather than done |
| `uv run qx reset [n]` | restore an exercise to its starting state |

Leave the number off and the command picks the first exercise you have not
finished. Numbers, slugs and fragments all work: `qx run 9`, `qx run bell`, and
`qx run 09_bell_entanglement` are the same thing.

If you would rather type `qx` without the `uv run` prefix:

```bash
uv tool install --editable .
```

## The curriculum

**Act I - reaching a first result.** Environment, dictionaries, your first
circuit, measurement, reading counts.

**Act II - understanding what you see.** The Born rule, statevectors and global
phase, gates as matrices, Bell states and bit ordering.

**Act III - the real world.** Migrating 2021 code to 2.x, running on real
hardware, and reading a noisy result honestly.

Each exercise ends in something executed and displayed - a histogram, a matrix, a
statevector - rather than just a green tick.

## How answers are checked

Not by comparing your code to the solution. The runner inspects the objects your
code produces:

- **states** with `Statevector.equiv`, which ignores global phase, because no
  experiment can detect it
- **gates** with `Operator.equiv`, same reasoning
- **measurement counts** never for exact equality. Sampling is random. Proportions
  are checked against the binomial standard error `SE = sqrt(p(1-p)/N)` at a
  4-sigma tolerance, and whole distributions with a chi-square test

So an answer that is right for reasons the author did not anticipate still passes.

Your file runs in a separate process with a time limit, so an infinite loop or a
crash costs you one run rather than your terminal session.

## Running on real hardware

Exercise 11 is the only one that can reach out to IBM, and it degrades gracefully:

1. a real QPU, if you have an account and one is reachable
2. a local simulator with a **noise model copied from real hardware**, so the
   lesson about noise still lands
3. a plain noiseless simulator

Whichever it used is printed with the result and recorded in `qx list`. To set up
an account:

```bash
uv run qx doctor --save-account
```

The key is stored unencrypted by Qiskit at `~/.qiskit/qiskit-ibm.json`, outside
this repository, so it cannot be committed by accident. To force the offline path
even when you do have an account:

```bash
QX_OFFLINE=1 uv run qx run 11
```

CI always sets `QX_OFFLINE`, so no automated run can ever spend your free QPU
minutes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding an exercise means creating one
directory; the test suite enforces the rest.

## License

MIT. See [LICENSE](LICENSE).

Qiskit is a trademark of IBM. This project is not affiliated with or endorsed by
IBM. It is an independent set of exercises that happens to be written for Qiskit,
which is why neither the project name nor the command contains "Qiskit" or "IBM".
