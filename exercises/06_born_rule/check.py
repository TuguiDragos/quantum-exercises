"""Verification for exercise 06."""

import math

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_close,
    assert_counts_distribution,
    assert_operator_equiv,
    counts_artifact,
    require,
    require_circuit,
    text_artifact,
)

THETA = math.pi / 3
SHOTS = 4096


def _reference() -> QuantumCircuit:
    qc = QuantumCircuit(1)
    qc.ry(THETA, 0)
    return qc


def check(mod):
    qc = require_circuit(mod, "qc")

    # The prediction only means something if the circuit is still the given one.
    assert_operator_equiv(
        qc.remove_final_measurements(inplace=False),
        _reference(),
        message="The circuit was changed. Predict the given circuit rather than adjusting it.",
    )

    predicted = require(mod, "predicted", dict)

    missing = {"0", "1"} - set(predicted)
    if missing:
        raise CheckFailed(f"`predicted` is missing the outcome(s) {sorted(missing)}.")

    for outcome, value in predicted.items():
        if value is None:
            raise CheckFailed(f"`predicted[{outcome!r}]` is still None.")
        if not isinstance(value, (int, float)):
            raise CheckFailed(
                f"`predicted[{outcome!r}]` should be a number, not a {type(value).__name__}."
            )
        if not 0.0 <= float(value) <= 1.0:
            raise CheckFailed(
                f"`predicted[{outcome!r}]` is {value}, which is not a probability.",
                detail="Probabilities live between 0 and 1 inclusive.",
            )

    predicted = {k: float(v) for k, v in predicted.items()}
    _diagnose_amplitude_confusion(predicted)

    result = StatevectorSampler(seed=2026).run([qc], shots=SHOTS).result()
    counts = dict(result[0].data.meas.get_counts())

    assert_counts_close(counts, predicted)
    assert_counts_distribution(counts, predicted)

    exact = {"0": math.cos(THETA / 2) ** 2, "1": math.sin(THETA / 2) ** 2}
    summary = "\n".join(
        f"  {outcome}:  predicted {predicted[outcome]:.4f}   "
        f"measured {counts.get(outcome, 0) / SHOTS:.4f}   exact {exact[outcome]:.4f}"
        for outcome in sorted(exact)
    )

    return [
        counts_artifact(counts, caption=f"ry(pi/3) sampled {SHOTS} times"),
        text_artifact(summary, caption="Prediction against reality"),
    ]


def _diagnose_amplitude_confusion(predicted: dict[str, float]) -> None:
    """Name the mistake when the numbers look like unsquared amplitudes."""
    amplitudes = {"0": math.cos(THETA / 2), "1": math.sin(THETA / 2)}
    if all(math.isclose(predicted.get(k, -1), v, abs_tol=1e-3) for k, v in amplitudes.items()):
        raise CheckFailed(
            "Those are the amplitudes, not the probabilities.",
            detail=(
                f"cos(pi/6) = {amplitudes['0']:.4f} and sin(pi/6) = {amplitudes['1']:.4f} are the "
                "amplitudes. The Born rule squares them. Notice they sum to "
                f"{sum(amplitudes.values()):.4f} rather than 1, which is the giveaway here: "
                "it is the squared amplitudes that must always sum to 1, not the "
                "amplitudes themselves."
            ),
        )
