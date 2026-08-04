"""Exercise 12 - reference solution."""

HARDWARE_COUNTS = {"00": 471, "11": 448, "01": 55, "10": 50}

AGREEING = ("00", "11")
DISAGREEING = ("01", "10")


def agreement_rate(counts: dict[str, int]) -> float:
    shots = sum(counts.values())
    return sum(counts.get(outcome, 0) for outcome in AGREEING) / shots


def disagreement_rate(counts: dict[str, int]) -> float:
    shots = sum(counts.values())
    return sum(counts.get(outcome, 0) for outcome in DISAGREEING) / shots


# The circuit is right and the theory is right. The device is imperfect.
explanation = "noise"
