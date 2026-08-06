"""Exercise 02 - reference solution."""


def total_shots(counts: dict[str, int]) -> int:
    return sum(counts.values())


def most_common(counts: dict[str, int]) -> str:
    # max() over the keys, ranked by the value each key maps to.
    return max(counts, key=lambda outcome: counts[outcome])


def outcome_probabilities(counts: dict[str, int]) -> dict[str, float]:
    shots = total_shots(counts)
    return {outcome: count / shots for outcome, count in counts.items()}
