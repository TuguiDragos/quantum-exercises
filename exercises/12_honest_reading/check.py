"""Verification for exercise 12."""

import math

from quantum_exercises.checks import CheckFailed, require, text_artifact

AGREEING = ("00", "11")
DISAGREEING = ("01", "10")

CASES = [
    ("ideal simulator", {"00": 512, "11": 512}),
    ("good hardware", {"00": 471, "11": 448, "01": 55, "10": 50}),
    ("poor hardware", {"00": 380, "11": 360, "01": 150, "10": 134}),
    ("no entanglement at all", {"00": 256, "01": 256, "10": 256, "11": 256}),
    ("sparse result, some outcomes absent", {"00": 600, "11": 400, "01": 24}),
]

VALID_ANSWERS = {"bug", "noise", "physics"}


def check(mod):
    agreement_rate = _callable(mod, "agreement_rate")
    disagreement_rate = _callable(mod, "disagreement_rate")

    for label, counts in CASES:
        shots = sum(counts.values())
        expected_agree = sum(counts.get(o, 0) for o in AGREEING) / shots
        expected_disagree = sum(counts.get(o, 0) for o in DISAGREEING) / shots

        actual_agree = _number(agreement_rate, counts, label)
        if not math.isclose(actual_agree, expected_agree, abs_tol=1e-9):
            raise CheckFailed(
                f"agreement_rate returned {actual_agree:.4f} for the {label} case, "
                f"expected {expected_agree:.4f}.",
                detail=(
                    f"Counts: {counts}\n"
                    f"Agreeing shots: {sum(counts.get(o, 0) for o in AGREEING)} of {shots}."
                ),
            )

        actual_disagree = _number(disagreement_rate, counts, label)
        if not math.isclose(actual_disagree, expected_disagree, abs_tol=1e-9):
            raise CheckFailed(
                f"disagreement_rate returned {actual_disagree:.4f} for the {label} case, "
                f"expected {expected_disagree:.4f}.",
                detail=f"Counts: {counts}",
            )

        if not math.isclose(actual_agree + actual_disagree, 1.0, abs_tol=1e-9):
            raise CheckFailed(
                f"For the {label} case your two rates add up to "
                f"{actual_agree + actual_disagree:.4f}, not 1.0.",
                detail="Every shot lands in exactly one of the two groups, so they must total 1.",
            )

    _check_explanation(mod)

    lines = [f"{'case':<38} {'agreement':>10} {'disagreement':>14}"]
    for label, counts in CASES:
        lines.append(
            f"{label:<38} {agreement_rate(counts):>9.2%} {disagreement_rate(counts):>13.2%}"
        )
    lines.append("")
    lines.append("Read down the agreement column. The drop from 100% to the low 90s is")
    lines.append("noise on a working machine. The drop to 50% is a circuit that never")
    lines.append("entangled anything, and that one is worth debugging.")

    return text_artifact("\n".join(lines), caption="The same question, five different results")


def _check_explanation(mod) -> None:
    answer = require(mod, "explanation", str)
    normalized = answer.strip().lower()

    if normalized not in VALID_ANSWERS:
        raise CheckFailed(
            f"`explanation` is {answer!r}, which is not one of the three options.",
            detail=f"Choose one of: {sorted(VALID_ANSWERS)}",
        )

    if normalized == "bug":
        raise CheckFailed(
            "Not a bug. The circuit that produced those counts was correct.",
            detail=(
                "92% of the shots agreed, which is exactly what a working two-qubit circuit "
                "looks like on current hardware. A genuine bug, such as a missing cx, shows up "
                "as roughly 50% agreement, not 92%."
            ),
        )

    if normalized == "physics":
        raise CheckFailed(
            "Not the physics. An ideal Bell state really does forbid 01 and 10.",
            detail=(
                "Exercise 09 was right, and simulating that circuit gives exactly zero of "
                "those outcomes. The difference between the ideal state and the counts here "
                "comes from the device, not from the theory."
            ),
        )


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value


def _number(fn, counts, label) -> float:
    try:
        value = fn(counts)
    except KeyError as exc:
        raise CheckFailed(
            f"{fn.__name__} raised KeyError({exc}) on the {label} case.",
            detail=(
                f"Counts: {counts}\n"
                "Not every outcome appears in every result. Use counts.get(outcome, 0) instead "
                "of counts[outcome]."
            ),
        ) from exc
    if not isinstance(value, (int, float)):
        raise CheckFailed(f"{fn.__name__} returned a {type(value).__name__}, expected a number.")
    return float(value)
