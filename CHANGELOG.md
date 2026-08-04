# Changelog

Notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.2.0
[0.1.0]: https://github.com/TuguiDragos/quantum-exercises/releases/tag/v0.1.0
