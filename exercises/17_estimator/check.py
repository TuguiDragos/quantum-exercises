"""Verification for exercise 17."""

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import SparsePauliOp

from quantum_exercises.checks import CheckFailed, require, text_artifact

SHOTS = 4096
ATOL = 1e-6

ESTIMATOR_HINT = "The Estimator's value lives at result[0].data.evs."
COUNTS_HINT = "Return P(0) - P(1), worked out from the dict you were handed."

# ry(theta)|0> has <Z> = cos(theta). Both poles, the equator, and two angles in
# between, so a single hardcoded number cannot satisfy the set.
ANGLES = [0.0, math.pi, math.pi / 2, math.pi / 3, 2.0]

# Counts whose answer is exact, so this half of the check never depends on
# sampling luck.
COUNT_CASES = [
    ({"0": 1024}, 1.0),
    ({"1": 1024}, -1.0),
    ({"0": 512, "1": 512}, 0.0),
    ({"0": 768, "1": 256}, 0.5),
    ({"0": 100, "1": 300}, -0.5),
]


def check(mod):
    observable_z = require(mod, "observable_z", SparsePauliOp)
    expectation = _callable(mod, "expectation")
    z_from_counts = _callable(mod, "z_from_counts")

    _check_observable(observable_z)
    _check_expectation(expectation, observable_z)
    _check_from_counts(z_from_counts)

    return [text_artifact(_summary(expectation, z_from_counts), caption="Two routes, one number")]


def _check_observable(observable):
    if observable.num_qubits != 1:
        raise CheckFailed(
            f"`observable_z` acts on {observable.num_qubits} qubits, expected 1.",
            detail='SparsePauliOp("Z") is a one-qubit observable; "ZZ" would be two.',
        )
    # Compared as a matrix, not as text: -Z and Z are different observables even
    # though they differ only by a phase, so .equiv would be the wrong tool here.
    if not np.allclose(observable.to_matrix(), SparsePauliOp("Z").to_matrix(), atol=ATOL):
        raise CheckFailed(
            "`observable_z` is not the Z observable.",
            detail=(
                f"Its matrix is\n{np.round(observable.to_matrix(), 4)}\n"
                "Z is diag(+1, -1): +1 for outcome 0, -1 for outcome 1."
            ),
        )


def _check_expectation(expectation, observable_z):
    for theta in ANGLES:
        qc = QuantumCircuit(1)
        qc.ry(theta, 0)
        value = _number(expectation, qc, observable_z, f"ry({theta:.4f})", ESTIMATOR_HINT)
        want = math.cos(theta)
        if not math.isclose(value, want, abs_tol=1e-4):
            raise CheckFailed(
                f"expectation() gave {value:.6f} for ry({theta:.4f}), expected {want:.6f}.",
                detail=(
                    "ry(theta)|0> = cos(theta/2)|0> + sin(theta/2)|1>, so\n"
                    "  <Z> = cos(theta/2)^2 - sin(theta/2)^2 = cos(theta).\n"
                    "A value that is right for one angle and wrong for the others usually "
                    "means the number was hardcoded rather than measured."
                ),
            )

    # A second observable, so expectation() cannot be a Z-only special case.
    plus = QuantumCircuit(1)
    plus.h(0)
    value = _number(expectation, plus, SparsePauliOp("X"), "h(0) with X", ESTIMATOR_HINT)
    if not math.isclose(value, 1.0, abs_tol=1e-4):
        raise CheckFailed(
            f"expectation() gave {value:.6f} for <X> on |+>, expected 1.0.",
            detail=(
                "expectation() has to pass the observable it was given through to the "
                "Estimator. |+> is the +1 eigenstate of X, so this one is exactly 1."
            ),
        )


def _check_from_counts(z_from_counts):
    for counts, want in COUNT_CASES:
        value = _number(z_from_counts, counts, None, f"counts {counts}", COUNTS_HINT)
        if not math.isclose(value, want, abs_tol=ATOL):
            raise CheckFailed(
                f"z_from_counts({counts}) returned {value:.6f}, expected {want:.6f}.",
                detail=(
                    "<Z> = P(0) - P(1). Divide each count by the total number of shots "
                    "first: the difference of the raw counts is not a probability."
                ),
            )


def _number(function, first, second, label, hint):
    """Call the learner's function and insist the answer is a real number.

    The hint is passed in rather than fixed: pointing a z_from_counts mistake at
    result[0].data.evs would send the reader to the wrong half of the exercise.
    """
    try:
        value = function(first) if second is None else function(first, second)
    except KeyError as exc:
        # The mistake hint 3 warns about. It used to escape as a raw KeyError,
        # while exercise 15 answered the identical slip with a teaching message.
        raise CheckFailed(
            f"For {label}, the function raised KeyError({exc}).",
            detail=(
                f"Something was looked up by the key {exc} and was not there. Not every "
                "outcome appears in every result: a lookup with [] raises, while "
                f"counts.get(key, 0) returns 0. {hint}"
            ),
        ) from exc
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating, np.integer)):
        raise CheckFailed(
            f"For {label}, the function returned {value!r}, which is not a number.",
            detail=f"A function with no `return` gives None. {hint}",
        )
    return float(value)


def _summary(expectation, z_from_counts):
    lines = [f"{'circuit':<16}{'<Z> estimator':>15}{'<Z> from counts':>18}{'cos(theta)':>13}"]
    for theta in (0.0, math.pi / 3, math.pi / 2, math.pi):
        qc = QuantumCircuit(1)
        qc.ry(theta, 0)
        measured = qc.copy()
        measured.measure_all()
        counts = (
            StatevectorSampler(seed=15)
            .run([measured], shots=SHOTS)
            .result()[0]
            .data.meas.get_counts()
        )
        lines.append(
            f"ry({theta:.4f})".ljust(16)
            + f"{expectation(qc, SparsePauliOp('Z')):>+15.4f}"
            + f"{z_from_counts(counts):>+18.4f}"
            + f"{math.cos(theta):>+13.4f}"
        )
    lines.append("")
    lines.append(f"The counts column is {SHOTS} shots, so it wanders. The other two do not.")
    return "\n".join(lines)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but its type is {type(value).__name__}.")
    return value
