# Changelog

Notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## 0.5.0 - 2026-08-05

### Added

- **Act IV: three exercises on expectation values, ending in a real Bell test.**
  Everything before this returned counts. Exercise 15 introduces the Estimator
  and has the learner compute the same number twice, once through the primitive
  and once from a counts dict, to show they agree. Exercise 16 is the fact behind
  it: the hardware measures Z and nothing else, so reading any other axis means
  rotating the state first. Exercise 17 spends both on CHSH, reaching S = 2.83
  against a classical ceiling of 2 that the runner demonstrates by trying all
  sixteen pre-decided strategies.
- Python 3.11 to the CI matrix. `pyproject.toml` had claimed support for it since
  the first release without a single job ever running it. The suite passes there.
- Tests that enforce the two `check.py` rules CONTRIBUTING says the suite
  enforces. Nothing had ever looked at a `check.py`; both rules were honoured by
  convention alone. `01_environment` is the one documented exception, because it
  has to read the learner's file to tell "asked the package" from "typed the
  number in".
- A test pinning each exercise README's heading number to its directory.
- **Three lab notebooks in `notebooks/`**, written from scratch and running
  entirely offline. `lab-1-qiskit-patterns` walks the four steps every Qiskit
  program has and shows the same answer arriving through the Sampler and the
  Estimator. `lab-2-noise` separates readout error from gate error and then
  measures which one is actually costing you: on this device readout alone
  accounts for almost the whole gap, and choosing qubits 3 and 4 over 1 and 2
  moves a Bell pair from 0.88 to 0.97 with no other change. `lab-3-dynamic-circuits`
  measures partway through, branches on the bit, and ends in teleportation,
  including the correction that looks like dead code until you measure the other
  axis and find it missing.
- The notebook tests are parametrised over `notebooks/` instead of naming one
  file, so every notebook is executed in CI and a new one is covered as soon as it
  lands. Two more checks came with that: every notebook opens with a title, and
  the ones that must exist are named so a rename cannot silently drop one.

### Fixed

- **Ctrl-C no longer orphans the worker.** The child sits in its own process
  group so the terminal cannot signal it, and the time limit is enforced by the
  parent, so an interrupt left an unkillable process spinning at 100% CPU
  forever. `qx watch` was worse: it printed "Stopped watching." and exited 0 while
  the runaway loop kept going. The spawn is now wrapped in a `finally` that kills
  the tree on any exit.
- **The "open this file" path is no longer truncated.** `no_wrap` with
  `crop=False` still measured against the console width and cut there, so a path
  two directories deep pointed at a file that does not exist. That line is the
  entire reason the failure panel exists.
- A repository that cannot be written to no longer produces a traceback. A
  read-only clone or a full disk turned a passing exercise into sixty lines of
  rich traceback, which is precisely what this tool exists not to do. All four
  commands that record progress now say what happened in one line.
- `qx solution` and `qx reset` re-read progress before writing it. Both block on
  a confirmation prompt between reading and writing, so an exercise finished in
  another terminal during that window was silently erased.
- A state file from a different schema version is copied aside instead of being
  overwritten. Running a newer qx once and then an older one destroyed every
  recorded exercise with nothing on screen to say so.
- Five error translations that were confidently wrong. `Operator()` on a measured
  circuit was reported as a statevector problem, in the exercise that teaches
  `Operator`. A typo in a submodule of an installed package was reported as the
  package being missing. `Index 0 out of range for size 0` was always blamed on a
  missing classical register, even for a qubit. `ccx` was called a two-qubit gate.
  And `qiskit.execute(...)` reached by attribute, the commoner 0.x spelling, had
  no rule at all.
- The verdict file is bounded. Learner output was capped at 64 KB, but an
  exception message crossed uncapped: a 20 MB one made qx allocate 488 MB and
  flood the terminal with 22 MB.
- The gitleaks rule now matches a key inside a notebook. A `.ipynb` stores cell
  source as JSON, so `token="..."` is on disk as `token=\"...\"`, and the rule was
  anchored to a bare quote. Confirmed against the pinned gitleaks binary, along
  with the claim in SECURITY.md that the default rule set misses these keys, which
  still holds.
- The saved API key is never world-readable, not even briefly. qiskit creates the
  file with the process umask and writes the token before anything tightens it, so
  `qx` now creates it at 0600 first.
- `timeout` in `meta.toml` is validated. A non-integer raised `ValueError` and
  took down every command at once; zero or negative parsed fine and produced "did
  not finish within -5 seconds".
- `PYTHONPATH` can no longer put the working directory back on `sys.path`. The
  filter compared strings, so any symlinked spelling of the same directory
  survived it, which on macOS is everything under `/tmp`.
- The progress bar's track is no longer painted in the fill colour on consoles
  without block glyphs, and a counts artifact of all zeros no longer divides by
  zero.
- Any directory merely named `exercises` no longer captures the search for the
  project root. A plain `~/exercises` shadowed the real repository from every
  directory beneath it, reported "No exercises found" and advised running from
  inside the repository, which is where the reader already was. It also made the
  installed-package fallback unreachable for anyone owning such a directory.
- `invocation()` no longer tells a `uv run` user to type `qx`. `uv run` puts the
  project's own bin on PATH for the length of one command, so `shutil.which`
  found a `qx` that the reader's next shell does not have, which is the single
  case the helper exists to prevent.
- The two committed `.DS_Store` files are out of the index and in `.gitignore`,
  along with the state file's `.unreadable` copy and its write-temporaries.

### Changed

- Exercise 11 no longer claims its measurement refutes hidden variables. It does
  not: perfect agreement in a single basis is exactly what a shared coin flip
  produces, and the exercise never measures a second basis. The text now says what
  the result does and does not show, and points at exercise 17, which runs the
  experiment that settles it.
- Exercise 11 stops describing `cx` as copying one qubit onto another. On a
  superposition there is no value to copy, which is what no-cloning is about, and
  the same README says two lines earlier that neither qubit has a definite value.
- Exercise 05 no longer says `result.get_counts()` "no longer exists". It exists,
  and `backends.py` calls it; what has no `get_counts` is a V2 `PrimitiveResult`.
- Exercise 06 documents the tolerance that actually binds. Two checks run, and
  with two outcomes the chi-square test rejects at about 3.3 standard errors
  rather than the four the README advertised. Its amplitude diagnostic also
  stated a false rule.
- README no longer says `uv tool install` builds the environment from the
  lockfile. It does not read `uv.lock` at all, verified by corrupting the file and
  watching the install succeed.
- README no longer says the `.vscode` settings point the Python extension at the
  project environment. They deliberately set no interpreter, and have not since
  0.2.1.
- CONTRIBUTING's package count says what it counts. 122 is the number of lockfile
  entries, not packages: there are 112 distinct ones and 105 in a 3.13
  environment. The test named after accuracy asserted the wrong quantity.
- The changelog's version headings are plain text. All twelve linked to release
  tags, and this repository has never had a tag.
- The timeout message names the knob you actually turned, `--timeout` or
  `meta.toml`.

## 0.4.1 - 2026-08-04

### Removed

- **The custom "verified against qiskit" badge.** It displayed the version and
  date the weekly run tested, which reads well, but it was the only thing in the
  project that needed anything written back to the repository: a job pushing a
  `badges` branch, and a repository-wide setting raising the ceiling on what any
  workflow's token may do. Paying that for a caption, one day after publishing a
  security policy, was the wrong trade. Every workflow is now read-only.
- The version it tested goes to the run summary page instead, so the information
  survives without a branch, a token or a moving part. The `weekly-verify` badge
  still shows pass or fail, which is the signal that actually matters: if a new
  Qiskit breaks an exercise, it turns red.

### Changed

- The README no longer claims a badge shows which version was checked, since
  that badge is gone. It says what is true instead.
- CONTRIBUTING records that GitHub disables a scheduled workflow in a public
  repository after 60 days without activity. The badge push had been doubling as
  the thing that kept the schedule alive, so removing it makes that GitHub
  behaviour something to know rather than something silently handled.

## 0.4.0 - 2026-08-04

### Added

- **A security policy**, written from verified behaviour rather than a template.
  It documents the two things worth knowing before cloning: what happens to an
  IBM API key, and the fact that `qx run` executes `check.py` from whichever
  repository you cloned, with your environment and filesystem in reach. That
  second point was confirmed by writing a `check.py` that reads the credentials
  file, so the policy states a demonstrated fact rather than a caution.
- **`qx doctor` now checks the permissions of the saved key.** qiskit writes it
  with whatever umask is in force, normally leaving it world-readable, and the
  automatic tightening added in 0.2.1 only applies to accounts saved through this
  tool afterwards. Any account saved before that, or saved by qiskit directly,
  stayed readable by every local user with nothing to say so.
- **The README shows the tool instead of describing it.** Eight screenshots
  replace the hand-copied terminal transcripts, which could not show colour and
  had to be re-verified by hand whenever output changed. Installation became a
  real walkthrough: uv per platform, clone, install, and `qx doctor` with a
  picture of the checks it runs. Every image carries alt text, so the page still
  reads without them.

## 0.3.4 - 2026-08-04

### Changed

- **One spelling for the command, everywhere.** 0.3.3 made the printed guidance
  adapt, which fixed correctness but not the contradiction: a screenshot of the
  editor still showed `uv run qx run 11` in the file while the terminal below it
  said `qx run`. The quickstart now installs `qx` with `uv tool install
  --editable .`, which takes about a second, and all 57 written references say
  plainly `qx`. The adaptive helper stays for anyone who skips that step, and
  three further messages that had hardcoded the old form now go through it. A
  test refuses the other spelling in any written file.

## 0.3.3 - 2026-08-04

### Fixed

- **The tool printed a command that contradicted its own files.** Every exercise
  file and every exercise README says `uv run qx run N`, which works straight
  from a fresh clone with nothing installed. The tool's own output said `qx run`,
  which only works after a global install. Both appeared inches apart on screen.
  The printed form is now chosen at run time: `qx` when it resolves on PATH,
  `uv run qx` otherwise, so the guidance always matches what the reader can
  actually type. Ten places printed a command; all of them go through one helper.

## 0.3.2 - 2026-08-04

### Fixed

- **An artifact carrying only metadata drew an empty box.** Exercise 13 records
  which backend it ran on by returning an artifact with no caption and no
  payload, purely as transport. It rendered as a bare two-character frame under
  the result. Such artifacts are now skipped, and the backend is still recorded.

### Changed

- `readme-assets/README.md` no longer warns that `qx doctor` exposes an account.
  Checked rather than assumed: it prints no API key, no CRN and no credentials,
  only the account label and paths containing the username, neither of which is
  a secret.

## 0.3.1 - 2026-08-04

### Fixed

- **Square corners everywhere.** Rounded corners and a filled background
  contradict each other: a filled cell is painted corner to corner, and a
  rounded glyph drawn over it leaves the cell's outer corner coloured outside
  the curve, which reads as a notch stuck to the curve. The `qx doctor` table
  looked right only because it carried no fill at all. Every panel and table now
  uses square geometry, which matches the fill exactly.
- Three panels in the CLI and the doctor table were still using rich's default
  box rather than the shared helper, so they kept rounded corners even after the
  panels were changed. All of them route through one helper now, which is also
  the only place a box is chosen.

## 0.3.0 - 2026-08-04

### Added

- **A single palette drives every colour the tool emits.** `theme.py` holds six
  values and the semantic names built from them; nothing else in the source
  names a colour. The accent appears only as a line, an outline or a run of
  glyphs, with the histogram and progress bars the one place it fills area.
- Severity is carried by border weight rather than hue, since the palette holds
  no error colour: an inactive outline reads as "not yet", an accented one as
  "this is the result", and a heavier rule marks a genuine error.
- Two layers of enforcement. A static check parses every source file and refuses
  any colour literal outside `theme.py`. A rendering check drives the real UI
  functions through a truecolour console and inspects the escape sequences that
  come out, which is the only way to catch a colour that rich contributes on the
  tool's behalf.

### Fixed

Found by that rendering check, after a first version of it reported clean:

- **rich's automatic highlighter was recolouring output.** It repaints numbers,
  strings and paths in its own named colours, laying them over styles the tool
  had chosen. Now disabled.
- **rich's default markdown styles reached the screen through `qx hint`.**
  `markdown.code` alone is "bold cyan on black". All twenty-seven markdown
  styles, and the table and rule chrome, are overridden from the palette.
- **Fenced code in hints and revealed solutions used the Monokai theme**, which
  emits dozens of hues from outside the palette. Highlighting is now built from
  the palette itself: structure carries the accent, everything else is body text.
- The bar track was drawn in the fill colour, so the empty part of every bar was
  accented. It is muted now, and the fill is the only accented area.
- **Secondary text was unreadable.** It used the terminal's dim attribute, which
  halves the intensity of whatever it is applied to; on a real display whole
  lines faded into the background. The palette as specified has nothing between
  TEXT at 14.5:1 contrast and OUTLINE at 1.7:1, and its two neutrals are meant
  for dots and borders rather than words, so one value is derived for prose:
  TEXT blended 30% toward BACKGROUND, landing at 7.6:1. The dim attribute is now
  used nowhere.
- The worker's child process is pinned colourless with `PYTHON_COLORS=0` and
  `NO_COLOR=1`. Python 3.13 and later colour their own tracebacks, and anything
  an exercise printed could carry colour of its own; either would arrive inside
  a panel wearing hues from outside the palette.
- `SURFACE` was declared and never used. The artifact panels are raised surfaces
  and now say so.

The first version of the rendering check split SGR parameters naively and read
the blue channel of `#3d3f60` as the code for bright cyan, reporting leaks that
were not there. It now walks the parameters properly.

### Changed

- A failing run prints the full path of the file to open, on its own unwrapped
  line. It printed only the bare filename, which said nothing once `qx` was
  installed globally and run from another directory. `qx next` had the path but
  wrapped it across two lines, so it could not be copied.

## 0.2.3 - 2026-08-04

### Fixed

- **A test introduced in 0.2.2 broke CI on Python 3.10.** It asserted that the
  documented version of every dependency equals the installed one, which assumed
  a single resolution across the whole matrix. There is not one: numpy resolves
  to 2.5.1 on 3.13 but 2.2.6 on 3.10, and scipy to 1.18.0 against 1.15.3, because
  their newer releases have dropped 3.10. The dependency table now states the
  interpreter it was resolved on, names the two packages that differ, and the
  test asserts only on that interpreter. The lesson was procedural: the change
  was pushed after running one interpreter rather than the matrix that CI runs.
- The badge check read the Python versions out of a percent-encoded URL without
  decoding it, so the `%20` of a separator was read as part of the next version.
- Two class-scoped fixtures were declared as instance methods, which pytest 9
  deprecates.

### Changed

- **The author's name is written without diacritics in the machine-readable
  metadata.** BibTeX keys must be ASCII, and the generator strips characters it
  cannot represent rather than transliterating them, which turned `Țugui` into
  `ugui` in the citation key. Plain `Tugui Dragos` in `CITATION.cff`,
  `pyproject.toml` and the README gives a clean `tugui_...` key. `LICENSE` still
  carries the diacritics.
- The dependency inventory moved out of the README, which now carries badges for
  the stack instead. Badges state versions, so tests check the Python badge
  against the CI matrix and the Qiskit badges against the installed versions.
- Added `readme-assets/`, for screenshots.

## 0.2.2 - 2026-08-04

Documentation and metadata only. No behaviour changed.

### Changed

- **The project is described on its own terms.** It had been introduced as a
  variant of another project in three places: the README tagline, the package
  docstring and the citation abstract. Standing on someone else's description is
  a poor way to explain what this actually does, so all three now say what the
  tool is: you edit a file, you run one command, and it tells you what is wrong
  in the language of the problem rather than as a traceback. A test keeps the
  comparison from creeping back.
- The README gained a full dependency inventory: every runtime and development
  dependency with its declared range, the version the lockfile resolves to, and
  why it is there. Tests check that inventory against `pyproject.toml`, the
  installed environment and `uv.lock`, so it cannot quietly go stale, and the
  wording avoids naming a release number for the same reason.
- The README and `CITATION.cff` now carry the author's website.

### Fixed

- **`CITATION.cff` said the course has twelve exercises.** It has had fourteen
  since the renumbering in 0.2.0. A citation file is exactly the wrong place for
  a stale number, since it is what ends up quoted in someone else's bibliography.
  The abstract has been rewritten to describe the verification approach and the
  weekly re-run as well.
- `CITATION.cff` gained `contact`, `url` and `license-url`, and the author's
  website; validated against the Citation File Format 1.2.0 schema and checked
  through its APA and BibTeX renderings.
- The author's name is now written the same way in the README as in `LICENSE`,
  `pyproject.toml` and the commit history.
- A stray reference in the dependency table pointed at hooks that were not listed
  anywhere in the README.

## 0.2.1 - 2026-08-04

An adversarial review of the finished repository, one reviewer per dimension,
each finding then re-tested by hand. Twenty-two defects confirmed by
reproduction and fixed. The worst of them made the tool lie in ways a learner
would never have noticed.

### Fixed

**The offline fallback was silently noiseless.** `sample()` built a fresh Aer
sampler and discarded the backend that had just been selected, so the noise
model copied from real hardware did nothing. Exercise 13 announced "local
simulator with a hardware noise model" and returned a flawless Bell state, zero
disagreeing shots, every time; the same circuit on the selected backend gives
about 70. Everyone without an IBM account was being shown a result that could not
happen, right before exercise 14 asked them to reason about noise.

**A check written as a generator marked every answer correct.** A `check()`
containing `yield` returns a generator and runs none of its body, so the worker
saw no exception and reported a pass. Now rejected as an authoring error, along
with async checks and non-Artifact returns.

**Exercise 13 accepted circuits a real QPU would reject.** The ISA validation
compared gate names only, so a native two-qubit gate between qubits that are not
physically connected passed. It now validates each instruction against the
backend target, qubits included. It also required only that the two qubits
agreed, which a circuit that always answers 11 does perfectly; both outcomes must
now carry a real share of the shots.

**Runaway output could exhaust memory.** Child output was captured unbounded: a
print loop reached 5 GB of buffered text and over 7 GB resident, and overshot its
own 2-second limit by 3.5x. Output is now drained by bounded readers that keep
64 KB and discard the rest, and the same run finishes inside its limit at 129 MB.

**A timeout threw away a verdict that had already been written.** A learner who
started any background process kept the pipes open, so a run that had genuinely
passed was reported as a timeout. The result file is now read even after a
timeout, the child runs in its own process group, and a timeout kills its
descendants rather than orphaning them.

**A stray file in the repository root broke every run.** `python -m` puts the
working directory on `sys.path`, so a scratch `qiskit.py` shadowed the real
package and the failure was reported as though the learner had killed the
process. The worker now drops that entry before importing anything.

Smaller, each reproduced first:

- Binary bytes on stdout crashed the whole command with a `UnicodeDecodeError`.
- An artifact payload that could not be serialized was reported to the learner as
  "you stopped the process".
- An artifact with `meta=None` crashed the CLI after printing PASS, losing the
  progress it was about to record.
- Exercise code inherited stdin and could swallow what the user typed; it now
  gets `EOFError` instead.
- Exercise 09 accepted `h, h, x`, an identity followed by a NOT, which is exactly
  the shortcut its own error message warned against, and rejected a correct
  answer that contained a barrier.
- Exercise 10 never gave `is_balanced` a mixed count dictionary, so an
  implementation that asked whether an outcome occurred at all passed despite
  being wrong on every real device.
- Exercise 07 crashed rather than failed when a correct answer also measured.
- Exercise 01 passed on a hardcoded version literal, the exact thing its own
  message told the learner not to do.
- `qx run '²'` produced a raw traceback: `isdigit()` accepts characters `int()`
  refuses.
- Two `qx` processes running at once silently overwrote each other's progress.
- The ASCII bar fallback emitted a space for partial cells, punching the gap its
  own comment said it avoided.
- A circuit drawing crashed the run on a console that could not encode box
  characters, and the child was not pinned to UTF-8.
- `.vscode/settings.json` pointed at `.venv/bin/python`, which does not exist on
  Windows.

### Security

- `qx doctor --save-account` left the plaintext IBM key at 0644, readable by any
  other local user. It is now 0600 inside a 0700 directory, and the command says
  which it did.
- It also continued silently when `getpass` could not turn echo off, which would
  print the key on screen. It now refuses and explains why.
- **gitleaks did not catch an IBM key.** Verified: a hardcoded 44-character token
  passes the default rule set untouched, so calling it "the actual safety net"
  was wrong. `.gitleaks.toml` adds a rule that does catch it, confirmed against
  a planted key. The pre-commit hook also only scans staged changes, so a
  tree-wide scan now runs in CI, where nothing is staged.
- `worker.py` described the child process as an isolation boundary. It is not a
  sandbox and the docstring now says so plainly.

## 0.2.0 - 2026-08-04

The curriculum taught the tool but not the subject: five distinct gates across
every solution, and no algorithm at all. A learner could run a Bell state on real
hardware and still not answer what a quantum computer is for. This release fixes
that, and closes the gap where the hardware path had never actually run.

### Added

- **Exercise 09, interference.** Two Hadamards undo each other, which no coin can
  do, and a phase in the middle reverses the certain answer. This is the
  mechanism behind every quantum advantage and the course did not cover it.
- **Exercise 10, Deutsch's algorithm.** One oracle query where classical needs
  two, built directly on exercise 09 and using only `h` and `z`. The first
  provable separation, and the course previously taught no algorithm.
- **`notebooks/playground.ipynb`**, an ungraded companion for changing numbers
  and seeing what moves. Every cell is executed by CI, so it cannot rot quietly.
  The repository already carried ipykernel, nbstripout and Jupyter settings for
  a notebook that did not exist.
- **`qx doctor` now runs a real circuit** rather than only importing packages, so
  an install that imports but cannot execute is caught.
- **ASCII fallback for bar rendering**, for terminals whose encoding cannot carry
  block characters.
- **A reporting path for untranslated errors.** When no rule matches, the learner
  is told that the gap is in this tool and pointed at the issue tracker.
- **Tests for the runtime hardware branch**, driven with a result built from the
  real container classes, and for backend selection, doctor and rendering.

### Changed

- **The default interpreter moves from 3.12 to 3.13.** The 3.12 choice came from
  a design note claiming it was the most mature for wheels, which was never
  rechecked. It is no longer true: the whole suite passes on 3.13 and on 3.14
  with byte-identical dependency versions. 3.13 is the default rather than 3.14
  so that a learner who later installs an unrelated package is less likely to
  meet a missing wheel. The supported floor stays at 3.10, which is where Qiskit
  2.5.1 puts its own floor, and CI now covers 3.10, 3.12, 3.13 and 3.14.
- `.pre-commit-config.yaml` no longer pins `python3.12`, which failed outright
  for a contributor who did not happen to have that exact version installed.
- **Exercises 09 to 12 are renumbered 11 to 14** to make room in Act II. This
  invalidates any existing `.qx-state.json`, whose entries are keyed by slug;
  progress on those four exercises will read as unfinished. Run
  `qx reset <name>` or simply redo them.
- `qx list` groups exercises under act headings instead of repeating the act on
  every row, which cost about thirty columns and wrapped the titles.
- The `ran_on` suffix is abbreviated: `done (noisy)` rather than
  `done (noisy_simulator)`.
- The README opens with real terminal transcripts, and gained sections on who the
  course is for, how to install uv, and a table of every exercise.

### Fixed

- The progress bar rendered a gap between the filled portion and the track when
  the fractional part rounded to zero.
- Watch mode advanced to the next exercise by calling itself, which is a loop
  written as recursion.
- `ruff check --fix` stripped the deliberately unused imports out of
  `template.py`, so `qx reset` could hand back a file missing imports the
  exercise needs. The lint ignores now cover template files and a test compares
  the two as committed.
- `assert_operator_equiv` passed a `QuantumCircuit` target to `numpy.asarray`,
  which tried to iterate the circuit's instructions.

### Verified

- The hardware path was run end to end against a real QPU for the first time:
  Bell circuit on `ibm_fez`, a 156-qubit Heron processor, 1024 shots. A real
  `RuntimeJobV2` returns the same `PrimitiveResult` / `SamplerPubResult` shape as
  the local simulator, with a single `meas` register, which is what the runner
  assumed but had never confirmed.
- Exercise 14's hardware counts are that measurement, replacing numbers that had
  been written by hand and described as real.

## 0.1.0 - 2026-08-04

First release. The `qx` runner and twelve exercises taking a learner from an
empty laptop to a Bell state on IBM hardware, with answers verified by inspecting
Qiskit objects rather than comparing source text, and measurement counts checked
against statistical tolerances rather than for equality.
