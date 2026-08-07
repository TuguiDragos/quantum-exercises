<img src="readme-assets/hero.svg" alt="quantum-exercises: from an empty laptop to a quantum circuit on real IBM hardware. A qx session runs doctor, two exercises and list, beside a panel that fills one bar per act while a ring counts toward seventeen." width="100%">

<p align="center">
  <a href="https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml"><img alt="ci" src="https://github.com/TuguiDragos/quantum-exercises/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://github.com/TuguiDragos/quantum-exercises/actions/workflows/verify.yml"><img alt="verify" src="https://github.com/TuguiDragos/quantum-exercises/actions/workflows/verify.yml/badge.svg" /></a>
</p>

<p align="center">
  <a href="https://pypi.org/project/qiskit/"><img alt="qiskit 2.5.1" src="https://img.shields.io/badge/qiskit-2.5.1-161826?style=flat&labelColor=161826&logo=qiskit&logoColor=9184D9" /></a>
  <a href="https://pypi.org/project/qiskit-ibm-runtime/"><img alt="qiskit-ibm-runtime 0.48.0" src="https://img.shields.io/badge/qiskit--ibm--runtime-0.48.0-161826?style=flat&labelColor=161826&logo=qiskit&logoColor=9184D9" /></a>
  <a href="https://pypi.org/project/qiskit-aer/"><img alt="qiskit-aer 0.17.2" src="https://img.shields.io/badge/qiskit--aer-0.17.2-161826?style=flat&labelColor=161826&logo=qiskit&logoColor=9184D9" /></a>
  <a href="https://github.com/astral-sh/uv"><img alt="uv" src="https://img.shields.io/badge/uv-161826?style=flat&labelColor=161826&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTE4NEQ5IiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMTIgMy4yIDMuOCA3LjR2OS4yTDEyIDIwLjhsOC4yLTQuMlY3LjR6Ii8%2BPHBhdGggZD0iTTMuOCA3LjQgMTIgMTEuNmw4LjItNC4yTTEyIDExLjZ2OS4yIi8%2BPC9nPjwvc3ZnPg%3D%3D" /></a>
  <a href="https://github.com/astral-sh/ruff"><img alt="ruff" src="https://img.shields.io/badge/ruff-161826?style=flat&labelColor=161826&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTE4NEQ5IiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMy42IDYuMmgxNi44TTMuNiAxMmg5LjZNMy42IDE3LjhoNiIvPjxwYXRoIGQ9Im0xNS40IDE2LjYgMi4zIDIuMyA0LjQtNC43Ii8%2BPC9nPjwvc3ZnPg%3D%3D" /></a>
  <a href="LICENSE"><img alt="license MIT" src="https://img.shields.io/badge/license-MIT-161826?style=flat&labelColor=161826&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTE4NEQ5IiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMTIgMy40djE3LjJNNy40IDIwLjZoOS4yTTMuOCA3LjJoMTYuNE0xMiAzLjkgMy44IDcuMk0xMiAzLjlsOC4yIDMuMyIvPjxwYXRoIGQ9Ik0zLjggNy42IDEuNSAxMy4yYTIuNyAyLjcgMCAwIDAgNC42IDB6TTIwLjIgNy42bC0yLjMgNS42YTIuNyAyLjcgMCAwIDAgNC42IDB6Ii8%2BPC9nPjwvc3ZnPg%3D%3D" /></a>
  <a href="https://tuguidragos.com"><img alt="tuguidragos.com" src="https://img.shields.io/badge/tuguidragos.com-161826?style=flat&labelColor=161826&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI%2BPGcgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTE4NEQ5IiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48Y2lyY2xlIGN4PSIxMiIgY3k9IjEyIiByPSI4LjYiLz48cGF0aCBkPSJNMy40IDEyaDE3LjIiLz48cGF0aCBkPSJNMTIgMy40YTEzLjQgMTMuNCAwIDAgMSAwIDE3LjIgMTMuNCAxMy40IDAgMCAxIDAtMTcuMiIvPjwvZz48L3N2Zz4%3D" /></a>
  <a href="https://www.python.org/"><img alt="python 3.10 | 3.11 | 3.12 | 3.13 | 3.14" src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-161826?style=flat&labelColor=161826&logo=python&logoColor=9184D9" /></a>
</p>

---

Seventeen hands-on exercises that take you from an empty laptop to a quantum
circuit on real IBM hardware, and then to a Bell test that no classical
explanation survives.

You edit a file, you run one command, and it tells you exactly what is wrong in
the language of the problem rather than as a Python traceback.

## What it looks like

### You get something wrong

![A failing run of exercise 11. The panel reads: Your circuit does not prepare (|00> + |11>) / sqrt(2), and shows your probabilities, {'00': 1.0000}, against the target, {'00': 0.5000, '11': 0.5000}, with a note that global phase is ignored so a phase difference is not the problem.](readme-assets/02-qx-run-fail.png)

That is the whole idea. No traceback, no line number pointing at library code, no
guessing. The runner knows which concept you tripped over, so it explains the
concept.

### You fix it, and something actually runs

![A passing run showing three panels: the statevector with amplitudes and probabilities, a histogram of 2048 shots split between 00 and 11, and a demonstration of little-endian bit order.](readme-assets/03-qx-run-pass.png)

No exercise ends on a green tick alone. Each one finishes with something your own
code produced and the runner rendered: a state, a matrix, a histogram, or the
numbers themselves. Seeing the object is the point.

### You always know where you are

![The qx list command showing the exercises grouped by act, each row carrying its number, slug, title and status, under a progress bar.](readme-assets/01-qx-list.png)

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

Everything here is verified on the 1st and the 15th of every month against the
Qiskit that actually ships today, not against the version this was written for.
Every reference solution is re-run, and the run reports which version it tested.
If a new Qiskit release breaks an exercise, the verify badge above turns red.

## Who this is for

You need to be able to read and write basic Python: variables, functions, and
dictionaries. Exercise 02 covers the dictionary part, because measurement results
arrive as a plain `dict` and that trips people up more often than the physics.

You need **no** quantum background, and no linear algebra beyond multiplying a
small matrix by a vector. Where a matrix shows up, the runner prints it.

Act I takes well under an hour. The whole course is an afternoon or two,
depending on how much you stop to poke at things.

## Installation

### 1. Install uv

[uv](https://docs.astral.sh/uv/) is the only prerequisite. It fetches the right
Python itself, so you do not need Python installed first.

macOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows, in PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

If `uv` is not found afterwards, open a new terminal so the updated PATH takes
effect.

### 2. Clone and install

```bash
git clone https://github.com/TuguiDragos/quantum-exercises
```

```bash
cd quantum-exercises
```

```bash
uv tool install --editable .
```

That last command takes about a second. It resolves the dependency ranges declared
in `pyproject.toml` and puts `qx` on your PATH, so every command below works from
any directory. `--editable` keeps it pointed at this clone, so it follows your
edits and finds the exercises wherever you run it from.

If you want the exact versions this repository is tested against rather than a
fresh resolution, use `uv sync --locked` instead: `uv tool install` does not read
`uv.lock` at all, and has no flag that makes it.

### 3. Check that it worked

```bash
qx doctor
```

![qx doctor listing nine checks, all reading ok: Python, uv, the Qiskit SDK, the Aer simulator, the IBM Runtime client, a circuit smoke test, the visualization extra, the exercises, and the IBM Quantum account.](readme-assets/04-qx-doctor.png)

Every check names the problem and the fix when something is wrong. The circuit
smoke test actually builds a Hadamard and samples it, so an install that imports
but cannot execute is caught here rather than three exercises later.

An IBM Quantum account is **optional**. Every exercise runs on a local simulator
without one.

### 4. Start

```bash
qx next
```

That prints the first unfinished exercise and the path to the file you edit. Open
that file, fill in the TODOs, save, and run `qx run`.

## The commands

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
finished. Numbers, slugs and fragments all work, so `qx run 11`, `qx run bell`
and `qx run 11_bell_entanglement` are the same thing.

If you skipped the install step, everything still works as `uv run qx <command>`
from inside the repository, and the tool prints whichever form applies to you.

## The seventeen exercises

**Act I - reaching a first result**

| # | Exercise | What you come away with |
|---|---|---|
| 01 | Your environment works | Prove the toolchain is real, and learn the one attribute worth printing when a tutorial misbehaves |
| 02 | Counts is just a dictionary | Measurement results are a plain `dict`. Write the three helpers you will reuse all course |
| 03 | Your first circuit | Build a one-qubit circuit and see the matrix it represents |
| 04 | Measurement, or the result is empty | Forget the measurement and Qiskit hands you nothing, without raising an error. Meet that trap on purpose |
| 05 | Reading counts out of a V2 result | A V2 result has no `get_counts()`. Learn the three-step path that replaces it |

**Act II - understanding what you see**

| # | Exercise | What you come away with |
|---|---|---|
| 06 | The Born rule, on paper first | Predict the probabilities before running anything, checked against 4096 real shots |
| 07 | States, amplitudes, and global phase | Prepare two target states, and find out why the runner compares with `equiv` rather than `==` |
| 08 | Gates are matrices | Build a controlled-Z out of nothing but Hadamards and a CNOT |
| 09 | Interference: amplitudes that cancel | Two Hadamards undo each other, which no coin can do. This is where the power comes from |
| 10 | Deutsch's algorithm in one query | Turn that cancellation into the first algorithm that provably beats every classical one |
| 11 | Bell state, and which bit is which | The state that started the argument, plus which character of the bitstring is qubit 0 |

**Act III - the real world**

| # | Exercise | What you come away with |
|---|---|---|
| 12 | Code from 2021 that no longer runs | Migrate real 0.x code to 2.x. This is the skill that unblocks every old tutorial you will ever find |
| 13 | A Bell state on a real machine | Transpile to the backend's instruction set and run, on a QPU if you have one |
| 14 | Reading a noisy result honestly | Hardware gives outcomes the theory forbids. Quantify that instead of assuming your circuit is broken |

**Act IV - expectation values, and a real Bell test**

Everything so far ends in counts. There is a second primitive that returns a
number instead, and it is the one every serious algorithm is built on. Three
exercises to reach it, and then to spend it on the experiment exercise 11
deliberately did not claim to have run.

| # | Exercise | What you come away with |
|---|---|---|
| 15 | The Estimator, and what it returns | Expectation values instead of shots, computed two ways and shown to agree |
| 16 | A device that only measures Z | Hardware reads one axis. Measuring any other means rotating the state first |
| 17 | CHSH, the experiment that settles it | Measure along different axes and reach S = 2.83, past the 2 that any pre-agreed answer is stuck below |

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

## Working in an editor

Open the repository folder and you get the exercise on one side and the verdict
on the other.

```bash
code .
```

![VS Code with exercise.py open on the left and the integrated terminal on the right, showing a passing run of exercise 11.](readme-assets/05-vscode-split.png)

The `.vscode` settings in this repository turn on pytest, activate the environment
in new terminals, and set ruff as the formatter. They deliberately do **not**
hardcode an interpreter path, because `uv` puts it in `.venv/bin` on macOS and
Linux and `.venv/Scripts` on Windows; the Python extension discovers `.venv` on
its own. If it picks the wrong one, choose it from the status bar.

Editing and rerunning by hand gets old quickly, so there is a watch mode:

```bash
qx watch
```

![Watch mode running in the VS Code terminal, showing a failed check followed by the line: watching exercises/11_bell_entanglement/exercise.py, save to re-run, Ctrl-C to stop.](readme-assets/07-qx-watch.png)

It re-runs on every save and moves to the next exercise on its own when one
passes.

## The notebooks

Four of them, none graded, all meant to be poked at. CI executes every cell of
every one, so none of them can quietly rot.

| Notebook | What it is for |
|---|---|
| `playground.ipynb` | scratch space. Change numbers, see what moves |
| `lab-1-qiskit-patterns.ipynb` | the four steps every Qiskit program has: map, optimize, execute, post-process |
| `lab-2-noise.ipynb` | readout error against gate error, measured on a real device's published rates. Readout wins by more than most people expect |
| `lab-3-dynamic-circuits.ipynb` | measuring partway through and branching on the result, ending in teleportation |

The exercises are where you are checked. The labs are where you are shown, at a
length an exercise cannot afford. Everything runs on a local simulator.

![The noise lab open in VS Code, showing an executed cell that runs the same Bell pair on three different pairs of physical qubits, and a table where the measured fidelity, 0.94, 0.88 and 0.97, tracks what the published readout rates predict.](readme-assets/06-vscode-notebook.png)

In VS Code the notebook kernel is a **separate** setting from the Python
interpreter. If `qx doctor` passes but the notebook cannot import qiskit, that is
the cause: pick the kernel inside `.venv` from the picker in the top right.

## Running on real hardware

Exercise 13 is the only one that can reach out to IBM, and it degrades
gracefully:

1. a real QPU, if you have an account and one is reachable
2. a local simulator with a **noise model copied from real hardware**, so the
   lesson about noise still lands
3. a plain noiseless simulator

Whichever it used is printed with the result and recorded in `qx list`.

![Exercise 13 run on ibm_fez, a real IBM QPU. The histogram shows 1024 shots: 00 at 48.8 percent, 11 at 44.9 percent, and 01 and 10 together at 6.25 percent. The summary reports the circuit as submitted, its ISA form, and that the disagreeing shots are noise rather than a bug.](readme-assets/08-real-hardware.png)

Those `01` and `10` shots are the point of the exercise that follows. An ideal
Bell state forbids them; a real machine produces them anyway, and exercise 14 is
about quantifying that instead of assuming your circuit is broken.

To set up an account:

```bash
qx doctor --save-account
```

Qiskit stores the key unencrypted at `~/.qiskit/qiskit-ibm.json`, outside this
repository, so it cannot be committed by accident, and `qx` tightens the file to
be readable only by you.

To force the offline path even when you do have an account:

```bash
QX_OFFLINE=1 qx run 13
```

CI always sets `QX_OFFLINE`, so no automated run can ever spend your free QPU
minutes.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding an exercise means creating one
directory; the test suite enforces the rest. The full dependency inventory, with
the reason each one is present, lives there too.

## Security

Reporting, and what the tool does with your IBM API key, are in
[SECURITY.md](SECURITY.md). The short version: an account is optional, the key
never reaches this repository, and `qx run` executes `check.py` from whichever
copy you cloned, so clone from a source you trust.

## Author

Tugui Dragos, [tuguidragos.com](https://tuguidragos.com).

If you use this project in written work, [CITATION.cff](CITATION.cff) has the
metadata; GitHub turns it into a formatted citation from the sidebar.

### The notebook

Everything I learn about quantum computing, written down in order, at [tuguidragos.com](https://tuguidragos.com). Five notes, picked fresh on the 1st and the 15th:

<!-- NOTES:START -->
- [My IBM Quantum node for n8n is now live](https://tuguidragos.com/ibm-quantum-node-for-n8n/)
- [How I use AI as a tutor without letting it lie to me](https://tuguidragos.com/how-i-use-ai-as-a-tutor-without-letting-it-lie-to-me/)
- [The version trap that cost me an evening (Qiskit 2.x)](https://tuguidragos.com/the-version-trap-that-cost-me-an-evening-qiskit-2-x/)
- [Six defects in a verified n8n node for IBM Quantum](https://tuguidragos.com/six-defects-verified-n8n-node-ibm-quantum/)
- [Running Quantum Circuits on Real IBM Hardware from n8n](https://tuguidragos.com/quantum-circuits-ibm-hardware-n8n/)
<!-- NOTES:END -->

<br>

## License

MIT. See [LICENSE](LICENSE).

Qiskit is a trademark of IBM. This project is not affiliated with or endorsed by
IBM. It is an independent set of exercises that happens to be written for Qiskit,
which is why neither the project name nor the command contains "Qiskit" or "IBM".
