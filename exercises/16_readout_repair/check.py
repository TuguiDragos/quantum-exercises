"""Verification for exercise 16."""

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.primitives import StatevectorSampler

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_support,
    counts_artifact,
    require,
    text_artifact,
)

LABELS = ("00", "01", "10", "11")
SHOTS = 4096

# Fixed seeds everywhere: the learner's three functions are pure, so the whole
# check is reproducible and cannot flake on a resample.
CALIBRATION_SEEDS = (101, 102, 103, 104)
# Chosen so the raw inverse lands two outcomes slightly below zero, which the
# README warns about. It happens on roughly two seeds in five here, so this is
# the ordinary case rather than a staged one.
BELL_SEED = 708
TRANSPILE_SEED = 7
LAYOUT = [0, 1]

# Readout correction recovers most of the readout share and none of the gate
# share. On this device the measured gain is about 0.055, so this bar is well
# clear of noise without pretending the method is perfect.
MIN_IMPROVEMENT = 0.02

# How far A @ your_answer may sit from the counts the device reported, in shots.
# An honest solve lands within 1e-13 of them, so half a shot is twelve orders of
# margin, while an answer that never used the matrix misses by tens.
RECONSTRUCTION_TOL = 0.5


def check(mod):
    prepare = _callable(mod, "prepare")
    response_matrix = _callable(mod, "response_matrix")
    corrected = _callable(mod, "corrected")

    _check_prepares(prepare)

    noisy = _noisy_backend()
    columns = {
        label: _run(noisy, prepare(label), seed)
        for label, seed in zip(LABELS, CALIBRATION_SEEDS, strict=True)
    }
    matrix = _check_matrix(response_matrix, columns)

    bell = QuantumCircuit(2)
    bell.h(0)
    bell.cx(0, 1)
    bell.measure_all()
    observed = _run(noisy, bell, BELL_SEED)

    fixed = _check_corrected(corrected, matrix, observed)
    before = _agreement(observed)
    after = _agreement(fixed)

    if after - before < MIN_IMPROVEMENT:
        raise CheckFailed(
            f"Correction moved the agreement from {before:.4f} to {after:.4f}, "
            f"which is not the improvement this method should give.",
            detail=(
                "Solving A @ true = observed should pull most of the misread shots back "
                "where they belong. If the agreement barely moved, the matrix is probably "
                "close to the identity, which means the calibration counts were not used."
            ),
        )

    # Last, and after the improvement bar on purpose: an answer that corrects
    # nothing is better described by the message above than by this one.
    _check_it_reproduces_the_observation(matrix, fixed, observed)

    return [
        counts_artifact(
            {label: int(observed.get(label, 0)) for label in LABELS},
            caption=f"As the device reported it, {SHOTS} shots",
        ),
        text_artifact(_matrix_view(matrix), caption="How this device lies about readout"),
        text_artifact(_summary(observed, fixed, before, after), caption="Before and after"),
    ]


def _check_prepares(prepare) -> None:
    """Noiseless first: a preparation that is wrong makes every later number wrong."""
    for label in LABELS:
        circuit = prepare(label)
        if not isinstance(circuit, QuantumCircuit):
            raise CheckFailed(
                f"`prepare({label!r})` returned a {type(circuit).__name__}, "
                "expected a QuantumCircuit."
            )
        if circuit.num_qubits != 2:
            raise CheckFailed(
                f"`prepare({label!r})` has {circuit.num_qubits} qubits, but should have 2."
            )
        if not any(i.operation.name == "measure" for i in circuit.data):
            raise CheckFailed(
                f"`prepare({label!r})` has no measurement.",
                detail="Finish it with qc.measure_all(), or there is nothing to read back.",
            )

        counts = dict(
            StatevectorSampler(seed=5).run([circuit], shots=256).result()[0].data.meas.get_counts()
        )
        assert_counts_support(
            counts,
            {label},
            message=f"`prepare({label!r})` does not prepare {label!r} on a perfect simulator.",
        )


def _check_matrix(response_matrix, columns) -> np.ndarray:
    matrix = response_matrix(columns)
    if matrix is None:
        raise CheckFailed("`response_matrix` returned None. Build and return the 4x4 array.")
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (4, 4):
        raise CheckFailed(
            f"`response_matrix` returned shape {matrix.shape}, expected (4, 4).",
            detail="One row and one column for each of the four outcomes.",
        )

    reference = np.zeros((4, 4))
    for j, prepared in enumerate(LABELS):
        counts = columns[prepared]
        total = sum(counts.values())
        for i, measured in enumerate(LABELS):
            reference[i, j] = counts.get(measured, 0) / total

    if np.allclose(matrix, reference.T, atol=1e-9) and not np.allclose(
        matrix, reference, atol=1e-9
    ):
        raise CheckFailed(
            "The matrix is the right numbers the wrong way round.",
            detail=(
                "Entry [i][j] is the probability of measuring LABELS[i] when LABELS[j] was "
                "prepared, so one prepared state fills a COLUMN, not a row. As it stands "
                "your rows add up to 1 and your columns do not."
            ),
        )

    sums = matrix.sum(axis=0)
    if not np.allclose(sums, 1.0, atol=1e-6):
        raise CheckFailed(
            f"The columns should each add up to 1, but they add up to {np.round(sums, 4)}.",
            detail=(
                "Every shot of a prepared state is reported as something, so its column is "
                "a probability distribution. Divide each column by its own total."
            ),
        )

    if not np.allclose(matrix, reference, atol=1e-9):
        worst = int(np.argmax(np.abs(matrix - reference)))
        i, j = divmod(worst, 4)
        raise CheckFailed(
            "The matrix does not match the calibration counts you were given.",
            detail=(
                f"The largest disagreement is at [{i}][{j}]: you have "
                f"{matrix[i, j]:.4f}, the counts say {reference[i, j]:.4f}. That entry is "
                f"the share of the {LABELS[j]!r} shots that came back as {LABELS[i]!r}."
            ),
        )
    return matrix


def _check_corrected(corrected, matrix, observed) -> dict:
    fixed = corrected(matrix, observed)
    if fixed is None:
        raise CheckFailed("`corrected` returned None. Solve for the true distribution.")
    if not isinstance(fixed, dict):
        raise CheckFailed(f"`corrected` returned a {type(fixed).__name__}, expected a dict.")
    missing = set(LABELS) - set(fixed)
    if missing:
        raise CheckFailed(
            f"`corrected` left out the outcome(s) {sorted(missing)}.",
            detail="Return one entry per label, even when the number lands near zero.",
        )
    for label, value in fixed.items():
        if not isinstance(value, (int, float)):
            raise CheckFailed(
                f"`corrected` gave {label!r} a {type(value).__name__}, expected a number."
            )

    total = sum(fixed.values())
    if not np.isclose(total, sum(observed.values()), rtol=1e-6):
        raise CheckFailed(
            f"The corrected counts add up to {total:.1f}, but {sum(observed.values())} shots "
            "were taken.",
            detail=(
                "Correcting redistributes shots between outcomes, it does not create or "
                "destroy them. Each column of the matrix sums to 1, which is exactly what "
                "makes the total survive the solve."
            ),
        )
    return fixed


def _check_it_reproduces_the_observation(matrix, fixed, observed) -> None:
    """Put the answer back through the matrix and see if the device's counts come out.

    Everything before this asks whether the answer has the right shape and whether
    it helps. A distribution invented outright, half the shots on 00 and half on
    11, has both: it is a valid distribution, it keeps the shot total, and it
    scores a perfect agreement. Only the equation itself tells the two apart, and
    it is the equation the exercise is about.
    """
    answer = np.array([float(fixed[label]) for label in LABELS])
    reproduced = matrix @ answer
    reported = np.array([float(observed.get(label, 0)) for label in LABELS])

    gap = np.abs(reproduced - reported)
    if gap.max() <= RECONSTRUCTION_TOL:
        return

    worst = int(np.argmax(gap))
    raise CheckFailed(
        "Your corrected counts do not reproduce what the device reported.",
        detail=(
            "`observed = A @ true` is the equation being solved, so multiplying the "
            "matrix back through a correct answer has to give the observed counts "
            "again.\n"
            f"For {LABELS[worst]!r} it gives {reproduced[worst]:.1f}, while the device "
            f"reported {reported[worst]:.1f}.\n"
            "Solve the system rather than assembling a distribution that looks right: "
            "np.linalg.solve(matrix, observed_as_a_vector)."
        ),
    )


def _noisy_backend():
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2

    return AerSimulator.from_backend(FakeManilaV2())


def _run(backend, circuit, seed) -> dict:
    isa = transpile(
        circuit,
        backend,
        initial_layout=LAYOUT,
        optimization_level=1,
        seed_transpiler=TRANSPILE_SEED,
    )
    return dict(backend.run(isa, shots=SHOTS, seed_simulator=seed).result().get_counts())


def _agreement(counts) -> float:
    total = sum(counts.values())
    return (counts.get("00", 0) + counts.get("11", 0)) / total


def _matrix_view(matrix) -> str:
    header = "            " + "".join(f"{v:>10}" for v in LABELS)
    lines = ["                         prepared", header]
    for i, measured in enumerate(LABELS):
        lines.append(f"  read {measured}  " + "".join(f"{matrix[i, j]:>10.4f}" for j in range(4)))
    lines.append("")
    lines.append("Down a column: where the shots of one prepared state actually landed.")
    lines.append("The diagonal is how often the device got it right.")
    return "\n".join(lines)


def _summary(observed, fixed, before, after) -> str:
    rows = [f"{'outcome':>9}{'reported':>12}{'corrected':>12}"]
    for label in LABELS:
        rows.append(f"{label:>9}{int(observed.get(label, 0)):>12}{fixed[label]:>12.1f}")
    negative = [label for label in LABELS if fixed[label] < 0]
    tail = [
        "",
        f"agreement reported   {before:.4f}",
        f"agreement corrected  {after:.4f}",
        f"recovered            {after - before:+.4f}",
        "",
        "Readout calibration undoes readout error and nothing else. The noisy",
        "gates ran before any of this and are untouched, so a corrected result",
        "is closer to the truth rather than equal to it.",
    ]
    if negative:
        tail += [
            "",
            f"Look at {' and '.join(negative)}: negative shot counts, and an agreement",
            "just past 1.0. Neither is possible for a real distribution. They are",
            "the same overshoot seen twice, and they are not a mistake in your code:",
            "the raw inverse extrapolated further than 4096 shots can support.",
            "",
            "This is why production tools fit the nearest valid distribution instead",
            "of inverting outright. That trades a little bias for an answer that is",
            "always physical. The raw inverse is worth meeting first because you can",
            "see every step of it, including this one.",
        ]
    return "\n".join(rows + tail)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but its type is {type(value).__name__}.")
    return value
