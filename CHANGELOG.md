# Changelog

Notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-08-04

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

## [0.2.1] - 2026-08-04

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

## [0.2.0] - 2026-08-04

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

## [0.1.0] - 2026-08-04

First release. The `qx` runner and twelve exercises taking a learner from an
empty laptop to a Bell state on IBM hardware, with answers verified by inspecting
Qiskit objects rather than comparing source text, and measurement counts checked
against statistical tolerances rather than for equality.

[0.2.2]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.2.2
[0.2.1]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.2.1
[0.2.0]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.2.0
[0.1.0]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.1.0
