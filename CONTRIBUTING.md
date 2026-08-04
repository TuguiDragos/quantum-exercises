# Contributing

## Setup

```bash
git clone https://github.com/TuguiDragos/quantum-exercises
cd quantum-exercises
uv sync --all-extras --dev
uv run pre-commit install
```

`uv run pytest` should be green before you start.

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
`uv.lock` is committed.

## Never in CI, never in tests

Nothing may submit a job to real hardware. Both workflows set `QX_OFFLINE=1` and
`tests/conftest.py` sets it for the whole session. A test that spends someone's
free QPU quota is a bug.

## Before opening a pull request

```bash
uv run pre-commit run --all-files
uv run pytest
```
