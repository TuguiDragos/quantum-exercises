"""Exercise 05 - reference solution."""


def read_counts(result) -> dict[str, int]:
    return result[0].data.meas.get_counts()


def read_shots(result) -> int:
    return result[0].data.meas.num_shots
