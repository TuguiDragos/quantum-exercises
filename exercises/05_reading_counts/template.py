"""Exercise 05 - reading counts out of a V2 result.

Fill in the TODOs, then run:  uv run qx run 5
"""


def read_counts(result) -> dict[str, int]:
    """Return the counts dictionary for the first circuit in a V2 sampler result.

    Every result you are given here comes from a circuit built with
    `measure_all()`, so the classical register is called `meas`.

    Expected shape: {"00": 508, "11": 516}
    """
    # TODO: walk the three steps described in the README:
    #       pick the first circuit, open its data, read the `meas` register,
    #       then tally it into counts.
    return {}


def read_shots(result) -> int:
    """Return how many shots the first circuit was run with.

    There are two honest ways to get this. Either ask the register how many shots
    it holds, or add up the counts. Both are correct.
    """
    # TODO: return the number of shots.
    return 0
