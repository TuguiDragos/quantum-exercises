"""Verification for exercise 09."""

import math

from qiskit.circuit.library import IGate, XGate
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import Operator

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_support,
    assert_operator_equiv,
    counts_artifact,
    require,
    require_circuit,
    text_artifact,
)

SHOTS = 512


def check(mod):
    qc_undo = require_circuit(mod, "qc_undo")
    qc_flip = require_circuit(mod, "qc_flip")

    _check_undo(qc_undo)
    _check_flip(qc_flip)
    _check_prediction(mod)

    undo_counts = _sample(qc_undo)
    flip_counts = _sample(qc_flip)

    assert_counts_support(
        undo_counts,
        {"0"},
        message="Two Hadamards should leave the qubit at 0 every single time.",
    )
    assert_counts_support(
        flip_counts,
        {"1"},
        message="With the phase gate in the middle, the answer should be 1 every single time.",
    )

    return [
        counts_artifact(undo_counts, caption=f"qc_undo, {SHOTS} shots"),
        counts_artifact(flip_counts, caption=f"qc_flip, {SHOTS} shots"),
        text_artifact(
            f"A coin randomised twice is still a coin: that model predicts\n"
            f"P(0) = {require(mod, 'coin_model_prediction'):.2f} for qc_undo.\n\n"
            f"Measured: P(0) = 1.00, in {SHOTS} out of {SHOTS} shots.\n\n"
            "The model is not slightly off, it is wrong about the kind of thing\n"
            "a qubit is. After the first Hadamard nothing was decided yet, so the\n"
            "second one had two routes to interfere rather than one outcome to\n"
            "re-randomise. On the |1> outcome those routes arrived with opposite\n"
            "signs and cancelled exactly.\n\n"
            "Probabilities only ever add. Amplitudes can subtract. Exercise 10\n"
            "turns that into an algorithm.",
            caption="The coin model, refuted",
        ),
    ]


def _gate_names(qc) -> list[str]:
    """Instruction names in order, ignoring barriers, which change nothing."""
    return [i.operation.name for i in qc.data if i.operation.name != "barrier"]


def _check_undo(qc) -> None:
    if qc.num_qubits != 1:
        raise CheckFailed(f"`qc_undo` has {qc.num_qubits} qubits, but should have exactly 1.")

    names = _gate_names(qc)
    if not names:
        raise CheckFailed(
            "`qc_undo` is still empty.",
            detail=(
                "An empty circuit also does nothing, but it does not show you anything. "
                "The exercise wants two gates that visibly cancel each other out."
            ),
        )
    if names != ["h", "h"]:
        raise CheckFailed(
            f"`qc_undo` should be exactly two Hadamards, but it contains {names}.",
            detail="Apply qc_undo.h(0) twice, on the same qubit.",
        )

    assert_operator_equiv(
        qc,
        Operator(IGate()),
        message="`qc_undo` does not come out as the identity.",
    )


def _check_flip(qc) -> None:
    if qc.num_qubits != 1:
        raise CheckFailed(f"`qc_flip` has {qc.num_qubits} qubits, but should have exactly 1.")

    names = _gate_names(qc)
    if names.count("h") != 2:
        raise CheckFailed(
            f"`qc_flip` should still have exactly two Hadamards, but it has {names.count('h')}.",
            detail=(
                "The point is what a phase does BETWEEN the two Hadamards. Reaching for "
                "qc_flip.x(0) gives the right matrix while skipping the lesson."
            ),
        )

    # Position matters, not just the tally: h, h, x also has two Hadamards and
    # also equals X, but it is an identity followed by a NOT and teaches nothing
    # about a phase interfering with anything.
    middle = names[1:-1]
    if names[0] != "h" or names[-1] != "h" or not any(name != "h" for name in middle):
        raise CheckFailed(
            f"`qc_flip` is {names}, which does not sandwich a phase between the Hadamards.",
            detail=(
                "The circuit has to be: Hadamard, then a gate that flips the sign of the |1> "
                "amplitude, then Hadamard. Putting the extra gate outside that sandwich gives "
                "the right matrix by a different route and skips the whole point."
            ),
        )

    assert_operator_equiv(
        qc,
        Operator(XGate()),
        message="`qc_flip` does not come out as a NOT.",
    )


def _check_prediction(mod) -> None:
    value = require(mod, "coin_model_prediction")
    if not isinstance(value, (int, float)):
        raise CheckFailed(
            f"`coin_model_prediction` should be a number, not a {type(value).__name__}."
        )
    value = float(value)

    if math.isclose(value, 1.0, abs_tol=1e-9):
        raise CheckFailed(
            "That is what actually happens, not what the coin model predicts.",
            detail=(
                "The question is deliberately about the WRONG model. If h simply randomised "
                "the qubit, doing it twice would leave it random, so that model says 0.5. "
                "Reality says 1.0, and the gap between the two numbers is the whole exercise."
            ),
        )
    if not math.isclose(value, 0.5, abs_tol=1e-9):
        raise CheckFailed(
            f"`coin_model_prediction` is {value}, but the coin model predicts 0.5.",
            detail="Randomising a coin twice leaves it 50/50, the same as randomising it once.",
        )


def _sample(qc) -> dict[str, int]:
    measured = qc.copy()
    measured.measure_all()
    result = StatevectorSampler(seed=17).run([measured], shots=SHOTS).result()
    return dict(result[0].data.meas.get_counts())
