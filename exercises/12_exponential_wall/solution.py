"""Exercise 12 - reference solution."""

import math

BUDGET_BYTES = 8 * 1024**3

BYTES_PER_AMPLITUDE = 16

BITS_PER_BYTE = 8


def amplitudes_for(n):
    return 2**n


def quantum_bytes_for(n):
    return amplitudes_for(n) * BYTES_PER_AMPLITUDE


def classical_bytes_for(n):
    # Rounds up: nine bits need two bytes, not one and a fraction.
    return math.ceil(n / BITS_PER_BYTE)
