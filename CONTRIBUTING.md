# Contributing

## Setup

```bash
git clone https://github.com/TuguiDragos/quantum-exercises
cd quantum-exercises
uv sync --all-extras --dev
uv run pre-commit install
```

`uv run pytest` should be green before you start.

## The dependencies

Nine runtime dependencies. `pyproject.toml` declares a tested range for each,
and the committed `uv.lock` pins exact versions, so `uv sync` reproduces this
environment byte for byte.

The right-hand column is what the lockfile resolves to **on Python 3.13**, the
default interpreter. It is not universal: older interpreters resolve some
packages lower, because newer releases drop support for them. On 3.10 numpy
resolves to 2.2.6 and scipy to 1.15.3. A test keeps this table in step with a
3.13 environment and skips elsewhere.

| Dependency | Range | On 3.13 | Why it is here |
|---|---|---|---|
| [qiskit](https://pypi.org/project/qiskit/) `[visualization]` | `>=2.5,<3` | 2.5.1 | the SDK itself. The extra adds matplotlib, pydot, Pillow, pylatexenc, seaborn and sympy, which plain `qiskit` does not install and `draw("mpl")` needs |
| [qiskit-ibm-runtime](https://pypi.org/project/qiskit-ibm-runtime/) | `>=0.48,<1` | 0.48.0 | talks to IBM hardware, and supplies the fake backends the offline noise model is copied from |
| [qiskit-aer](https://pypi.org/project/qiskit-aer/) | `>=0.17,<1` | 0.17.2 | local simulation, including noise models taken from real devices |
| [typer](https://pypi.org/project/typer/) | `>=0.27,<1` | 0.27.1 | the `qx` command and its subcommands |
| [rich](https://pypi.org/project/rich/) | `>=15,<16` | 15.0.0 | histograms, matrices and panels in the terminal |
| [watchfiles](https://pypi.org/project/watchfiles/) | `>=1.2,<2` | 1.2.0 | `qx watch`, which re-runs an exercise on save |
| [numpy](https://pypi.org/project/numpy/) | `>=2.0,<3` | 2.5.1 | imported directly by the verification code, so it is declared rather than inherited from Qiskit |
| [scipy](https://pypi.org/project/scipy/) | `>=1.14` | 1.18.0 | chi-square critical values for the distribution checks |
| [tomli](https://pypi.org/project/tomli/) | `>=2.0.1` | 3.10 only | reads `meta.toml`. Conditional: `tomllib` is in the standard library from 3.11, so this is installed only on 3.10 |

Development, installed by `uv sync` and not needed to take the course:

| Dependency | Range | On 3.13 | Why it is here |
|---|---|---|---|
| [pytest](https://pypi.org/project/pytest/) | `>=9,<10` | 9.1.1 | the test suite |
| [ruff](https://pypi.org/project/ruff/) | `>=0.16,<0.17` | 0.16.1 | linting and formatting, including the notebook |
| [pre-commit](https://pypi.org/project/pre-commit/) | `>=4,<5` | 4.6.1 | runs the lint, format, notebook and secret-scan hooks before each commit |
| [nbstripout](https://pypi.org/project/nbstripout/) | `>=0.9,<1` | 0.9.1 | strips notebook outputs, which can carry IBM job ids |
| [ipykernel](https://pypi.org/project/ipykernel/) | `>=7,<8` | 7.3.0 | the kernel the playground notebook runs on |

Counting everything those pull in, the locked environment is 122 packages.
Two more tools are fetched by pre-commit and CI rather than installed into the
environment: [gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 for secret
scanning, and the hooks from
[pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) 6.0.0.

Python 3.10 or newer, which is the same floor Qiskit sets. CI runs the suite on
3.10, 3.12, 3.13 and 3.14; `uv` installs 3.13 by default.

## Adding an exercise

Create one directory under `exercises/`. There is no central index to update:
ordering comes from the numeric prefix, and the test suite enforces everything
else.

```
exercises/13_your_topic/
├── meta.toml       # title, act, summary; optional hardware and timeout
├── README.md       # the teaching text
├── exercise.py     # what the learner edits
├── template.py     # pristine copy of exercise.py, used by `qx reset`
├── solution.py     # reference answer
├── check.py        # verification, exposing check(mod)
└── hints.md        # exactly three `## Hint N` sections
```

`template.py` starts as a byte-identical copy of `exercise.py`:

```bash
cp exercises/13_your_topic/exercise.py exercises/13_your_topic/template.py
```

### Writing `check.py`

`check(mod)` receives the learner's module. Raise `CheckFailed` to reject an
answer, return an `Artifact` or a list of them to show on success.

```python
from quantum_exercises.checks import assert_state_equiv, require_circuit, statevector_artifact


def check(mod):
    qc = require_circuit(mod, "qc")
    state = assert_state_equiv(qc, TARGET, message="Your circuit does not prepare ...")
    return statevector_artifact(state, caption="Your state")
```

Two rules the test suite will not let you break:

1. **Compare objects, never source text.** Use `assert_state_equiv` and
   `assert_operator_equiv`, which go through `.equiv` and therefore ignore global
   phase. An answer that is right in an unexpected way must still pass.
2. **Never assert exact counts.** Use `assert_counts_support` for which outcomes
   are possible, `assert_counts_close` for proportions at 4 sigma, or
   `assert_counts_distribution` for a chi-square test over the whole distribution.

Artifacts cross a process boundary as JSON, so their payloads must be
JSON-serializable. The helpers in `checks.py` already handle that for states,
matrices and counts.

### Error messages

Say what is wrong in the language of the problem, then how to fix it. Compare:

> `AttributeError: 'PrimitiveResult' object has no attribute 'get_counts'`

with

> `result.get_counts()` is the old V1 API and no longer exists. A V2 result is a
> list of per-circuit results.

New translations go in `errors.py`. **Trigger the real exception first and paste
its actual message** - never write a pattern from memory. `tests/test_errors.py`
raises each error for real, so a guessed pattern fails immediately.

## The notebook

`notebooks/playground.ipynb` is executed cell by cell in CI, so treat it as code:
if you change an API it uses, the suite tells you. Outputs are stripped on commit
by nbstripout, which matters because notebook output can carry IBM job ids and
account details.

## Releasing

The version appears in three files and a test enforces that they agree:
`pyproject.toml`, `src/quantum_exercises/__init__.py`, and `CITATION.cff`. Add
the change to `CHANGELOG.md` in the same commit.

## What CI checks

For every exercise:

- `solution.py` passes its own check
- `template.py` fails, so the exercise teaches something
- the solution produces at least one artifact
- there are exactly three hints
- `meta.toml` is complete

Plus lint, format, and the unit tests, on Python 3.10, 3.12, 3.13 and 3.14.

`weekly-verify.yml` additionally resolves to the newest Qiskit the version ranges
allow and runs everything again. That job is the early warning for a breaking
release, which is why dependencies are ranges rather than exact pins even though
`uv.lock` is committed. It writes the version it tested to the run summary.

One thing to watch: GitHub disables a scheduled workflow in a public repository
after 60 days with no repository activity, and emails the owner when it does. Any
commit re-arms it, and the workflow can be re-enabled from the Actions tab. No
workflow in this project writes anything back to the repository, so none of them
needs write access and nothing keeps the schedule alive on its own.

## Never in CI, never in tests

Nothing may submit a job to real hardware. Both workflows set `QX_OFFLINE=1` and
`tests/conftest.py` sets it for the whole session. A test that spends someone's
free QPU quota is a bug.

## Before opening a pull request

```bash
uv run pre-commit run --all-files
uv run pytest
```
