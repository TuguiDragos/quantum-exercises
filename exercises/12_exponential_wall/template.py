"""Exercise 12 - why the simulator runs out.

Fill in the TODOs, then run:  qx run 12
"""

# Imported for you: classical_bytes_for has to round up, and math.ceil is the
# clearest way to say that.
import math

# The memory budget the artifact measures your answers against. Exactly 8 GiB,
# so there is no rounding to argue about.
BUDGET_BYTES = 8 * 1024**3

# Qiskit stores each amplitude as complex128: a real and an imaginary float, of
# eight bytes each.
BYTES_PER_AMPLITUDE = 16

BITS_PER_BYTE = 8


# TODO: how many amplitudes does a statevector of n qubits have?
#
#       One qubit has two outcomes, two qubits have four, three have eight.
#       Every qubit you add doubles it.
def amplitudes_for(n):
    return None


# TODO: how many bytes do those amplitudes occupy?
#
#       Use amplitudes_for and BYTES_PER_AMPLITUDE rather than repeating the
#       formula, so the two answers cannot drift apart.
def quantum_bytes_for(n):
    return None


# TODO: how many bytes does a CLASSICAL register of n bits need?
#
#       This is the other half of the comparison, and it is the one that makes
#       the exercise mean something. A classical register holds one value, so it
#       needs one bit per bit.
#
#       Careful at the edges: a byte holds eight bits, and nine bits still need
#       two whole bytes. It rounds up, never down. In Python, -(-n // 8) rounds
#       up without importing anything, and math.ceil(n / 8) says it more plainly.
def classical_bytes_for(n):
    return None
