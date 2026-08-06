"""Verification for exercise 02."""

import math

from quantum_exercises.checks import CheckFailed, require, text_artifact

# Several inputs, so a hardcoded answer to one of them fails on the others.
# No ties in any case, so most_common has a single correct answer.
CASES = [
    {"00": 500, "11": 524},
    {"0": 750, "1": 250},
    {"000": 10, "001": 30, "111": 60},
    {"1010": 4096},
]


def check(mod):
    total_shots = _callable(mod, "total_shots")
    most_common = _callable(mod, "most_common")
    outcome_probabilities = _callable(mod, "outcome_probabilities")

    if total_shots({}) != 0:
        raise CheckFailed(
            "total_shots({}) should be 0.",
            detail="Summing an empty collection gives 0. Python's sum() already does this.",
        )

    for counts in CASES:
        expected_total = sum(counts.values())
        actual_total = total_shots(counts)
        if actual_total != expected_total:
            raise CheckFailed(
                f"total_shots({counts}) returned {actual_total!r}, expected {expected_total}.",
                detail="Add up the values, not the keys. counts.values() gives you the numbers.",
            )

        expected_common = max(counts, key=lambda outcome: counts[outcome])
        actual_common = most_common(counts)
        if actual_common != expected_common:
            raise CheckFailed(
                f"most_common({counts}) returned {actual_common!r}, expected {expected_common!r}.",
                detail=(
                    "Return the outcome itself, the key, not how many times it happened. "
                    f"Here {expected_common!r} occurred {counts[expected_common]} times."
                ),
            )

        expected_probs = {k: v / expected_total for k, v in counts.items()}
        actual_probs = outcome_probabilities(counts)
        _compare_probs(counts, actual_probs, expected_probs)

    lines = []
    for counts in CASES[:2]:
        probs = outcome_probabilities(counts)
        rendered = ", ".join(f"{k}: {v:.3f}" for k, v in sorted(probs.items()))
        lines.append(
            f"{counts}\n  -> {total_shots(counts)} shots, most common {most_common(counts)!r}"
        )
        lines.append(f"  -> probabilities {{{rendered}}}")

    return text_artifact("\n".join(lines), caption="Your functions on real data")


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value


def _compare_probs(counts, actual, expected):
    if not isinstance(actual, dict):
        raise CheckFailed(
            f"outcome_probabilities({counts}) returned a {type(actual).__name__}, expected a dict.",
        )
    if set(actual) != set(expected):
        raise CheckFailed(
            f"outcome_probabilities({counts}) returned keys {sorted(actual)}, "
            f"expected {sorted(expected)}.",
            detail="Keep the same outcomes as the input; only the values change.",
        )
    for outcome, want in expected.items():
        got = actual[outcome]
        if not isinstance(got, (int, float)) or not math.isclose(float(got), want, abs_tol=1e-9):
            raise CheckFailed(
                f"outcome_probabilities({counts})[{outcome!r}] is {got!r}, expected {want}.",
                detail=(
                    "Divide each count by the total number of shots. If you got a whole number, "
                    "check that you are dividing with / and not //."
                ),
            )
