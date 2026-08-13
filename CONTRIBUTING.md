<img src="readme-assets/banner-contributing.svg" alt="Contributing: format, lint, secrets and test, each one drawn as it passes." width="100%">

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
| [qiskit-ibm-runtime](https://pypi.org/project/qiskit-ibm-runtime/) | `>=0.48,<1` | 0.49.0 | talks to IBM hardware, and supplies the fake backends the offline noise model is copied from |
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
| [ruff](https://pypi.org/project/ruff/) | `>=0.16,<0.17` | 0.16.1 | linting and formatting, including the notebooks |
| [pre-commit](https://pypi.org/project/pre-commit/) | `>=4,<5` | 4.6.1 | runs the lint, format, notebook and secret-scan hooks before each commit |
| [nbstripout](https://pypi.org/project/nbstripout/) | `>=0.9,<1` | 0.9.1 | strips notebook outputs, which can carry IBM job ids |
| [ipykernel](https://pypi.org/project/ipykernel/) | `>=7,<8` | 7.3.0 | the kernel the notebooks run on |

Counting everything those pull in, `uv.lock` records 122 package entries. That is
not the size of any one environment: the lockfile carries a separate entry per
resolution, so numpy, scipy and six others appear more than once. It names 112
distinct packages, and a 3.13 environment on Linux ends up with 104 installed.
A mac has exactly one more: `ipykernel` pulls `appnope` there and nowhere else,
which is why that last figure names a platform and the other two do not.
Two more tools are fetched by pre-commit and CI rather than installed into the
environment: [gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 for secret
scanning, and the hooks from
[pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) 6.0.0.

Python 3.10 or newer, which is the same floor Qiskit sets. CI runs the suite on
3.10, 3.11, 3.12, 3.13 and 3.14; `uv` installs 3.13 by default.

## How the course reaches a reader

Two ways, and they need different things from the build.

A contributor clones, and the exercises are simply there. A reader installs
`quantum-exercises` and gets them inside the wheel, at
`quantum_exercises/_course/`, from where `qx init` copies them somewhere
writable. The depth is deliberate. `find_project_root` walks up from the working
directory looking for `<ancestor>/exercises`, so a course nested that far inside
the package is invisible to it, and an installed read-only copy can never be
picked up as the one to edit. Move it one level up and `qx run` would start
checking answers inside `site-packages` and `qx reset` would try to write there.

`qx init` never overwrites. That is what makes it the upgrade path as well as the
first step: a release that adds an exercise adds it to an existing course and
leaves every answer alone.

That leaves the case it cannot serve, which is a release that *corrects* an
exercise: the files are already there, so they are skipped, and the correction
never reaches anyone who copied the course out earlier. `qx init --refresh` is
that path. It compares every file the course owns against the one shipped,
replaces what differs, and keeps the old one beside it as `.bak`. `exercise.py`
is excluded outright rather than compared, so no answer can be lost to it, and
`template.py` staying current is what keeps `qx reset` honest afterwards. The
course README at the top is refreshed only when it is one this command wrote,
recognised by its title line, because `qx init .` in a clone would otherwise
overwrite this repository's own README and anything a reader put there instead is
theirs. A symlink in place of any of these is refused rather than followed, so a
link left where a course file belongs cannot send a write outside the course.

The packaging lives in `[tool.hatch.build.targets.wheel]`. `force-include` maps
`exercises` and `notebooks` under the package; `exclude` keeps out the
`__pycache__` an in-process import of a `check.py` leaves behind. `readme-assets`
is not included, which is seven megabytes a reader never opens.

## Adding an exercise

Create one directory under `exercises/`. There is no central index to update:
ordering comes from the numeric prefix, and the test suite enforces everything
else.

```
exercises/21_your_topic/
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
cp exercises/21_your_topic/exercise.py exercises/21_your_topic/template.py
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

Two rules the test suite will not let you break. Both are checked by walking the
syntax tree of every `check.py`, in `tests/test_exercises.py`:

1. **Compare objects, never source text.** Use `assert_state_equiv` and
   `assert_operator_equiv`, which go through `.equiv` and therefore ignore global
   phase. An answer that is right in an unexpected way must still pass.
2. **Never assert exact counts.** Use `assert_counts_support` for which outcomes
   are possible, `assert_counts_close` for proportions at 4 sigma, or
   `assert_counts_distribution` for a chi-square test over the whole distribution.

There is exactly one exception to the first rule, and it is named in the test:
`01_environment` reads the learner's file. That exercise is about asking the
package for its version rather than typing the number in, and both routes produce
the same string, so no object inspection can tell them apart. If you need a
second exception, you almost certainly want a different exercise instead.

Artifacts cross a process boundary as JSON, so their payloads must be
JSON-serializable. The helpers in `checks.py` already handle that for states,
matrices and counts.

### Wrong answers, in `tests/test_diagnostics.py`

Passing the solution and failing the template says nothing about the branches
between them, and those branches are the reason a `check.py` is worth writing. So
every misconception a check names gets a case there, and a new exercise with no
cases fails the suite.

A case is one line. It starts from that exercise's own `solution.py` and appends
an override, so the answer is correct except for the single thing being tested,
and it keeps working when the solution is rewritten:

```python
case(
    "11_bell_entanglement",
    "label-read-big-endian",
    'label_q0_only = "10"',
    "qubit 0 is the RIGHTMOST character",
)
```

The last argument is matched against the message and its detail together. Match on
the sentence that names the mistake, not on a number that may drift.

`check()` is called in-process there rather than through the runner, so a case
costs milliseconds. The subprocess path has its own tests in
`tests/test_runner.py`.

### Error messages

Say what is wrong in the language of the problem, then how to fix it. Compare:

> `AttributeError: 'PrimitiveResult' object has no attribute 'get_counts'`

with

> `result.get_counts()` is the old V1 API and no longer exists. A V2 result is a
> list of per-circuit results.

New translations go in `errors.py`. **Trigger the real exception first and paste
its actual message** - never write a pattern from memory. `tests/test_errors.py`
raises each error for real, so a guessed pattern fails immediately.

## The notebooks

Everything in `notebooks/` is executed cell by cell in CI, so treat it as code: if
you change an API it uses, the suite tells you. The test is parametrised over the
directory, so a new notebook is covered the moment it lands, and
`tests/test_notebook.py` names the ones that must exist so a rename cannot quietly
drop one from the suite.

Outputs are stripped on commit by nbstripout, which matters because notebook
output can carry IBM job ids and account details.

Labs are not graded and must run offline. If a cell needs a real QPU, it belongs
in a fenced markdown block showing the code rather than in a cell that runs.

## Releasing

The version appears in **four** files, and tests enforce that they agree:

- `pyproject.toml`
- `src/quantum_exercises/__init__.py`
- `CITATION.cff`
- `uv.lock`, which records this project as a package like any other

The fourth is the one that bites. Editing the first three and stopping leaves the
lockfile behind, and then every CI job that runs `uv sync --locked` refuses to
start, for a reason nothing in the diff points at. So after bumping:

```bash
uv lock
```

It rewrites one line.

What changed in a version goes in the notes of the GitHub release for its tag,
where it sits next to the download and cannot describe a version that was never
published.

Publishing the release is what uploads to PyPI. `publish.yml` fires on a
published release, builds both distributions, refuses to upload a wheel carrying
fewer than twenty exercises, and pushes them with trusted publishing, so there is
no token in this repository to leak or rotate. PyPI has to be told once to trust
that workflow, under the project's Publishing settings, naming the repository,
`publish.yml` and the `pypi` environment. Until that is done the job fails at the
upload step and nothing else happens.

One ordering rule, because the README documents `uv tool install
quantum-exercises` as the way in: that sentence is only true once the version is
on PyPI. Publish the release, let `publish.yml` finish, and check the version is
actually there before pointing anyone at it.

## What CI checks

For every exercise:

- `solution.py` passes its own check
- `template.py` fails, so the exercise teaches something
- the solution produces at least one artifact
- there are exactly three hints
- `meta.toml` is complete
- the diagnoses it promises are reached, in `tests/test_diagnostics.py`

`ci.yml` has six jobs. `test` runs the suite once per interpreter in the matrix.
`lint` runs `ruff check` and `ruff format --check` as two steps on 3.13. `secrets`
runs gitleaks over the tree and uses no Python at all. `coverage` runs the suite
once more under coverage and fails below 100% of `src/`. `install` installs the
tool the way the README tells a reader to, then runs it from outside the
repository, which is the only check that the editable install still finds the
exercises from any directory. `wheel` is the other install: it builds the wheel,
puts it in an environment of its own with no repository anywhere, and takes a
learner from `qx init` through a passing exercise, then runs `qx init` and
`qx init --refresh` again to prove the answer survives both. That job is the only
thing standing between a packaging slip and a reader whose `pip install` gives
them a tool with no course.

Its steps live in `.github/scripts/wheel-smoke.sh` rather than in the workflow,
because `verify.yml` runs the same ones on macOS and Windows and two copies would
drift. The script is written for bash, which Windows runners have as Git Bash,
and it looks for the console script in `bin` and then in `Scripts`.

`coverage` needs four settings, and they all live under `[tool.coverage]` in
`pyproject.toml`. `patch = ["subprocess"]` measures the worker, which runs in a
child process and would otherwise read as untouched; it needs coverage 7.10 or
newer. `parallel = true` gives each of those processes its own data file, which
is what the `combine` step below exists to gather. `branch = true` counts both
arms of every condition, not just the lines, which is what catches a guard whose
false arm nothing ever takes. `fail_under = 100` is the gate itself.

All four are declared in the file rather than passed as flags, so that the
command below and the command CI runs measure the same thing. A flag would also
work, since `patch = ["subprocess"]` hands the whole live configuration down to
each child, but then the gate would live in the CI job instead of in the
repository, and running it locally would mean remembering the flags.

coverage is not a dependency. The job adds it for its own commands with
`uv run --with coverage`, so `uv.lock` and the package counts above stay as they
are. To run the same gate locally:

```bash
uv run --with coverage python -m coverage run -m pytest -q
```

```bash
uv run --with coverage python -m coverage combine && uv run --with coverage python -m coverage report
```

The triggers are every pull request, every push to `main`, and a manual
`workflow_dispatch`. A push to a side branch runs nothing until a pull request
exists for it.

Everything scheduled in this repository fires on the 1st and the 15th, so the
calendar holds two dates rather than a scatter of weekdays.

`verify.yml` has four jobs. `latest` resolves to the newest Qiskit the
version ranges allow and runs everything again: it is the early warning for a
breaking release, which is why dependencies are ranges rather than exact pins
even though `uv.lock` is committed, and it writes the version it tested to the
run summary. `preview` installs over the `<3` ceiling those ranges impose,
because the release most likely to break an exercise is the one `latest` cannot
see; it is quiet until a 3.x exists and never reddens the badge. Both run on
both dates.

`locked` installs the exact versions in `uv.lock` across three operating systems,
and runs on the 1st only. Pinned versions do not change inside a month, and this
job costs more than everything else here put together: macOS alone is billed at
ten times the Linux rate while the repository is private.

`wheel` is the same three operating systems and the same date, running the smoke
script `ci.yml` runs on Linux for every push. What it adds is the half the test
suite cannot see: a wheel unpacking wrongly, or `uv` putting the console script
somewhere else, is a Windows problem that no amount of green tests would have
caught before a release.

The workflow declares two cron entries rather than one `1,15`, because a single
entry reports the same string to `github.event.schedule` on both days and the
`if` on `locked` would have nothing to tell them apart by. A manual run does
everything, since the field is empty on `workflow_dispatch`.

Three tests assert that the installed environment is the one the documentation
describes. They are true of a locked install and false by construction in a job
that installs something newer on purpose, so `latest` and `preview` deselect them
through `PYTEST_ADDOPTS`. Without that, the first Qiskit patch release turns the
badge red over a stale badge rather than a broken exercise.

One thing to watch: GitHub disables a scheduled workflow in a public repository
after 60 days with no repository activity, and emails the owner when it does. Any
commit re-arms it, and the workflow can be re-enabled from the Actions tab.
`rotate-notes.yml` is what keeps the clock from getting close: it rewrites the
block between the NOTES markers in the README on the 1st and the 15th and commits
the result. Twice a month rather than monthly so that two consecutive failed runs
still leave the gap under sixty days. It is the only workflow here with
`contents: write`, and the only one that changes anything in the repository.

Those titles arrive from a feed rather than from this repository, so the block
between the markers is exempt from the two tests that scan written files for a
bare string, and a square bracket in a title is escaped rather than trusted. A
commit pushed with `GITHUB_TOKEN` creates no workflow run, so nothing checks the
rotation at the moment it lands; without both guards a post title could sit in
the README until an unrelated pull request failed for it.

## Never in CI, never in tests

Nothing may submit a job to real hardware. `ci.yml` and `verify.yml` set
`QX_OFFLINE=1` and `tests/conftest.py` sets it for the whole session. A test that
spends someone's free QPU quota is a bug. `rotate-notes.yml` runs no Python and
touches nothing quantum.

There is one exception, and it is opt-in. A test marked `@pytest.mark.hardware`
does reach IBM, and `addopts` carries `-m 'not hardware'` so an ordinary run never
collects it. That `-m` is what makes the promise real: the marker was declared
long before anything deselected it, so the first test to carry one would have run
everywhere, CI included. To run them on purpose:

```bash
uv run pytest -m hardware
```

`run_exercise` holds the other half of this. For the one exercise marked
`hardware = true` it hands the child an offline environment unless the caller
passes `allow_hardware`, and `qx run` is the only caller that ever does. Watch
mode and every test take the default, which is not to. The other nineteen
exercises never reach for a backend, so their environment is left alone.

## Before opening a pull request

```bash
uv run pre-commit run --all-files
uv run pytest
```
