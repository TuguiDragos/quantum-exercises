# quantum-exercises

[![ci](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml/badge.svg)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml)
[![weekly-verify](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml/badge.svg)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml)
[![verified against qiskit](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FTuguiDragos%2Fquantum-exercises%2Fbadges%2Fbadges%2Fqiskit.json)](https://github.com/TuguiDragos/quantum-exercises/actions/workflows/weekly-verify.yml)

Twelve hands-on exercises that take you from an empty laptop to a quantum circuit
running on real IBM hardware. In the style of [rustlings](https://github.com/rust-lang/rustlings):
you edit a file, you run a command, you get told exactly what is wrong.

## What it looks like

You get an answer wrong:

```
09 Bell state, and which bit is which ────────────────────────────────────────
╭───────────────────────────────── NOT YET ──────────────────────────────────╮
│ `label_q0_only` is '10', but the answer is "01".                           │
│                                                                            │
│ Qiskit is little-endian: qubit 0 is the RIGHTMOST character. So qubit 0    │
│ measured as 1 puts the 1 on the right, and qubit 1 measured as 0 puts the  │
│ 0 on the left, giving "01". Writing "10" is reading it the textbook way.   │
╰────────────────────────────────────────────────────────────────────────────╯

  next  qx hint 9 for a nudge, or edit exercise.py and run again
```

You fix it, and the exercise ends in something that actually ran:

```
09 Bell state, and which bit is which ────────────────────────────────────────
╭─────── Your Bell state ───────╮
│ basis  amplitude  probability │
│ |00>       0.707       0.5000 │
│ |01>           0       0.0000 │
│ |10>           0       0.0000 │
│ |11>       0.707       0.5000 │
╰───────────────────────────────╯
╭───────── 2048 shots: the two qubits always agree ──────────╮
│       00 ██████████████████████████████▊       972   47.5% │
│       11 ██████████████████████████████████   1076   52.5% │
│                                                            │
│    total   2048 shots                                      │
╰────────────────────────────────────────────────────────────╯
╭──────────────────── Little-endian, demonstrated ────────────────────╮
│ A circuit with x() on qubit 0 only, and nothing on qubit 1:         │
│                                                                     │
│     counts -> {'01': 64}                                            │
│                                                                     │
│ Qubit 0 is the one that was flipped, and the 1 appears at the RIGHT │
│ end of '01'. That is little-endian, and it is why the runner        │
│ keeps reminding you about it.                                       │
╰─────────────────────────────────────────────────────────────────────╯

  PASS  09_bell_entanglement
        finished in 0.61s

  Next up: 10 Code from 2021 that no longer runs  (qx next)
```

No exercise ends on a green tick alone. Every one finishes with a histogram, a
matrix or a statevector you produced.

## Why this exists

Nearly every quantum computing tutorial on the internet was written for Qiskit
0.x, and none of it runs any more. `execute()` was removed, `Aer` moved to its
own package, `IBMQ` became a different thing entirely, and the way you read your
results changed shape completely.

So beginners hit an `ImportError` on line 3 and conclude they are not smart
enough for quantum computing. They were just reading instructions for software
that no longer exists.

The nearest thing to this project, Microsoft's Quantum Katas, has been archived
read-only since August 2024, and it teaches Q# rather than Qiskit.

Everything here is verified weekly against the Qiskit that actually ships today.
The badge above shows which version was last checked, and when.

## Who this is for

You need to be able to read and write basic Python: variables, functions, and
dictionaries. Exercise 02 covers the dictionary part, because measurement results
arrive as a plain `dict` and that trips people up more often than the physics.

You need **no** quantum background, and no linear algebra beyond multiplying a
small matrix by a vector. Where a matrix shows up, the runner prints it.

Act I takes well under an hour. The whole course is an afternoon or two,
depending on how much you stop to poke at things.

## Quickstart

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), which is
the only prerequisite. It fetches the right Python itself, so you do not need
Python installed first.

macOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows, in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If the `uv` command is not found afterwards, open a new terminal so the updated
PATH takes effect. Then:

```bash
git clone https://github.com/TuguiDragos/quantum-exercises
cd quantum-exercises
uv run qx doctor
```

`qx doctor` checks every step and tells you what is missing and how to fix it.
When it is happy:

```bash
uv run qx next
```

The first run takes a minute while uv builds the environment from the committed
lockfile. After that it is instant. No IBM account needed, no PyPI install
needed. Everything works the same on macOS, Linux and Windows, all three of which
are covered by CI.

## The commands

Every command below is run as `uv run qx <command>`. If you would rather just
type `qx`, install it once with `uv tool install --editable .`.

| Command | What it does |
|---|---|
| `qx doctor` | check the environment, step by step |
| `qx list` | every exercise and your progress |
| `qx next` | the next thing to work on |
| `qx run [n]` | check an exercise |
| `qx watch [n]` | re-check automatically every time you save |
| `qx hint [n]` | reveal one more hint |
| `qx solution [n]` | show the answer, recorded as solved rather than done |
| `qx reset [n]` | restore an exercise to its starting state |
| `qx version` | versions of the tool and the quantum stack |

Leave the number off and the command picks the first exercise you have not
finished. Numbers, slugs and fragments all work, so `qx run 9`, `qx run bell` and
`qx run 09_bell_entanglement` are the same thing.

```
  quantum-exercises

  Act I - Reaching a first result
 #  exercise              title                                 status
01  01_environment        Your environment works                done
02  02_dictionaries       Counts is just a dictionary           done
03  03_first_circuit      Your first circuit                    done
04  04_measurement        Measurement, or the result is empty   done
05  05_reading_counts     Reading counts out of a V2 result     done

  Act II - Understanding what you see
 #  exercise              title                                 status
06  06_born_rule          The Born rule, on paper first         done
07  07_statevector        States, amplitudes, and global phase  todo
08  08_gates_as_matrices  Gates are matrices                    todo
09  09_bell_entanglement  Bell state, and which bit is which    solved

  Act III - The real world
 #  exercise              title                                 status
10  10_migration          Code from 2021 that no longer runs    todo
11  11_real_hardware      A Bell state on a real machine        done (noisy)
12  12_honest_reading     Reading a noisy result honestly       todo

  progress  ██████████████████▋░░░░░░░░░  8/12
```

## The twelve exercises

**Act I - reaching a first result**

| # | Exercise | What you come away with |
|---|---|---|
| 01 | Your environment works | Prove the toolchain is real, and learn the one attribute worth printing when a tutorial misbehaves |
| 02 | Counts is just a dictionary | Measurement results are a plain `dict`. Write the three helpers you will reuse all course |
| 03 | Your first circuit | Build a one-qubit circuit and see the matrix it represents |
| 04 | Measurement, or the result is empty | Forget the measurement and Qiskit hands you nothing, without raising an error. Meet that trap on purpose |
| 05 | Reading counts out of a V2 result | `result.get_counts()` is gone. Learn the three-step path that replaced it |

**Act II - understanding what you see**

| # | Exercise | What you come away with |
|---|---|---|
| 06 | The Born rule, on paper first | Predict the probabilities before running anything, checked against 4096 real shots |
| 07 | States, amplitudes, and global phase | Prepare two target states, and find out why the runner compares with `equiv` rather than `==` |
| 08 | Gates are matrices | Build a controlled-Z out of nothing but Hadamards and a CNOT |
| 09 | Bell state, and which bit is which | The state that started the argument, plus which character of the bitstring is qubit 0 |

**Act III - the real world**

| # | Exercise | What you come away with |
|---|---|---|
| 10 | Code from 2021 that no longer runs | Migrate real 0.x code to 2.x. This is the skill that unblocks every old tutorial you will ever find |
| 11 | A Bell state on a real machine | Transpile to the backend's instruction set and run, on a QPU if you have one |
| 12 | Reading a noisy result honestly | Hardware gives outcomes the theory forbids. Quantify that instead of assuming your circuit is broken |

## How answers are checked

Not by comparing your code to the solution. The runner inspects the objects your
code produces:

- **states** with `Statevector.equiv`, which ignores global phase, because no
  experiment can detect it
- **gates** with `Operator.equiv`, same reasoning
- **measurement counts** never for exact equality. Sampling is random.
  Proportions are checked against the binomial standard error
  `SE = sqrt(p(1-p)/N)` at a 4-sigma tolerance, and whole distributions with a
  chi-square test

So an answer that is right for reasons the author did not anticipate still
passes, and an answer that only looks right does not.

Your file runs in a separate process with a time limit, so an infinite loop or a
crash costs you one run rather than your terminal session.

## Running on real hardware

Exercise 11 is the only one that can reach out to IBM, and it degrades
gracefully:

1. a real QPU, if you have an account and one is reachable
2. a local simulator with a **noise model copied from real hardware**, so the
   lesson about noise still lands
3. a plain noiseless simulator

Whichever it used is printed with the result and recorded in `qx list`. To set up
an account:

```bash
uv run qx doctor --save-account
```

Qiskit stores the key unencrypted at `~/.qiskit/qiskit-ibm.json`, outside this
repository, so it cannot be committed by accident. To force the offline path even
when you do have an account:

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
