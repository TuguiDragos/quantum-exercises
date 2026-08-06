"""Exercise 14 - reading a noisy result honestly.

Fill in the TODOs, then run:  qx run 14
"""

# A real measurement, not an illustration: Bell circuit on ibm_fez, 1024 shots,
# 4 August 2026, job d9p0u0jbvhrs73a21710.
HARDWARE_COUNTS = {"00": 507, "11": 448, "01": 25, "10": 44}

AGREEING = ("00", "11")
DISAGREEING = ("01", "10")


def agreement_rate(counts: dict[str, int]) -> float:
    """Fraction of shots where the two qubits gave the same answer.

    An ideal Bell state gives 1.0. Real hardware gives a bit less.

    >>> agreement_rate({"00": 500, "11": 500})
    1.0
    """
    # TODO: add up the shots on the agreeing outcomes and divide by the total.
    #       Outcomes may be missing from the dict entirely, so reaching for
    #       counts["01"] can raise KeyError. counts.get("01", 0) cannot.
    return 0.0


def disagreement_rate(counts: dict[str, int]) -> float:
    """Fraction of shots where the two qubits disagreed.

    Every shot is in exactly one of the two groups, so this and agreement_rate
    must always add up to 1.
    """
    # TODO
    return 0.0


# TODO: in HARDWARE_COUNTS above, what accounts for the 01 and 10 shots?
#       Choose one string:
#         "bug"      - the circuit is wrong and needs fixing
#         "noise"    - the hardware is imperfect
#         "physics"  - Bell states genuinely produce these outcomes
explanation = None
