"""Exercise 02 - counts is just a dictionary.

Fill in the TODOs, then run:  qx run 2
"""


def total_shots(counts: dict[str, int]) -> int:
    """Return how many shots produced this result.

    That is the sum of all the values. An empty dict must return 0.

    >>> total_shots({"00": 500, "11": 524})
    1024
    """
    # TODO: replace this with the sum of the dictionary's values.
    return 0


def most_common(counts: dict[str, int]) -> str:
    """Return the outcome that occurred most often.

    `counts` always has at least one entry, and there is never a tie.

    >>> most_common({"00": 500, "11": 524})
    '11'
    """
    # TODO: return the key whose value is the largest.
    return ""


def outcome_probabilities(counts: dict[str, int]) -> dict[str, float]:
    """Return each outcome's share of the shots.

    `counts` always has at least one entry and at least one shot.

    >>> outcome_probabilities({"0": 750, "1": 250})
    {'0': 0.75, '1': 0.25}
    """
    # TODO: build a new dict mapping each outcome to count / total.
    return {}
