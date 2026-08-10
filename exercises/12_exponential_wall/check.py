"""Verification for exercise 12."""

import time

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from quantum_exercises.checks import (
    CheckFailed,
    require,
    text_artifact,
)

# Sizes the runner actually builds. 22 qubits is 64 MiB and about half a second;
# the point of the exercise is that going much past this is not a matter of
# patience, so nothing here tries.
MEASURED = (1, 5, 10, 20)

# The ladder shown to the learner. Two qubits apart, so each rung is four times
# the one below and the growth is visible rather than asserted.
LADDER = (14, 16, 18, 20, 22)

# Sizes checked by arithmetic alone, because allocating them is the thing the
# exercise is about.
ARITHMETIC = (30, 40, 50, 100)

BUDGET_BYTES = 8 * 1024**3

# Rounding up is the whole difficulty of classical_bytes_for, so the cases that
# separate a correct answer from a floor division are all here.
#
# 9 leads deliberately. At n=1 a floor division and a stray 2**n both give 0, so
# the first failure would be reported with the wrong cause; at n=9 they give 1
# and 64, which tell the two mistakes apart.
CLASSICAL_CASES = ((9, 2), (1, 1), (7, 1), (8, 1), (16, 2), (17, 3), (50, 7), (100, 13))

# Roughly the number of atoms in the observable universe, to one order of
# magnitude. Used for a single line of perspective, never for a pass or a fail.
ATOMS_IN_THE_UNIVERSE = 1e80


def check(mod):
    amplitudes_for = _callable(mod, "amplitudes_for")
    quantum_bytes_for = _callable(mod, "quantum_bytes_for")
    classical_bytes_for = _callable(mod, "classical_bytes_for")

    _check_amplitudes(amplitudes_for)
    _check_quantum_bytes(quantum_bytes_for, amplitudes_for)
    _check_classical_bytes(classical_bytes_for)

    return [
        text_artifact(
            _contrast(amplitudes_for, quantum_bytes_for, classical_bytes_for),
            caption="Two ways to write down n bits",
        ),
        text_artifact(_timed_ladder(quantum_bytes_for), caption="The doubling, timed"),
        text_artifact(
            _perspective(amplitudes_for, quantum_bytes_for), caption="Where that leaves you"
        ),
    ]


def _check_amplitudes(amplitudes_for) -> None:
    """Compare against a statevector actually built, not against a formula."""
    for n in MEASURED:
        got = _number(amplitudes_for, n, "amplitudes_for")
        want = Statevector(_spread(n)).data.size
        if got == want:
            continue
        if got == n**2:
            raise CheckFailed(
                f"`amplitudes_for({n})` returned {got}, which is n squared.",
                detail=(
                    "It is 2 to the power n, not n to the power 2. Two qubits have four "
                    "outcomes and three have eight, so the count doubles with every qubit "
                    "rather than growing with the square."
                ),
            )
        if got == 2 * n:
            raise CheckFailed(
                f"`amplitudes_for({n})` returned {got}, which is n doubled.",
                detail=(
                    "What doubles is the number of amplitudes, once per qubit added. "
                    "Adding a qubit to a 4-amplitude state gives 8, not 6."
                ),
            )
        raise CheckFailed(
            f"`amplitudes_for({n})` returned {got}, but a real {n}-qubit statevector "
            f"has {want} amplitudes.",
            detail="The runner built that statevector to get the number it compared against.",
        )


def _check_quantum_bytes(quantum_bytes_for, amplitudes_for) -> None:
    for n in MEASURED:
        got = _number(quantum_bytes_for, n, "quantum_bytes_for")
        want = Statevector(_spread(n)).data.nbytes
        if got == want:
            continue
        if got * 2 == want:
            raise CheckFailed(
                f"`quantum_bytes_for({n})` returned {got}, which is half of the {want} bytes "
                "numpy actually used.",
                detail=(
                    "Eight bytes is one float. An amplitude is complex, so it carries two "
                    "of them, a real part and an imaginary part, for sixteen bytes in total."
                ),
            )
        raise CheckFailed(
            f"`quantum_bytes_for({n})` returned {got}, but a real {n}-qubit statevector "
            f"occupies {want} bytes.",
            detail=(
                f"Its dtype is complex128, so it is amplitudes_for({n}) = "
                f"{amplitudes_for(n)} multiplied by 16."
            ),
        )

    for n in ARITHMETIC:
        got = _number(quantum_bytes_for, n, "quantum_bytes_for")
        want = 2**n * 16
        if got != want:
            raise CheckFailed(
                f"`quantum_bytes_for({n})` returned {got}, expected {want}.",
                detail=(
                    "This one is not built, only calculated. If the small sizes passed and "
                    "this did not, the formula is probably capped or approximated somewhere."
                ),
            )


def _check_classical_bytes(classical_bytes_for) -> None:
    for n, want in CLASSICAL_CASES:
        got = _number(classical_bytes_for, n, "classical_bytes_for")
        if got == want:
            continue
        if got == n // 8:
            raise CheckFailed(
                f"`classical_bytes_for({n})` returned {got}, expected {want}.",
                detail=(
                    "The division rounded down. Nine bits do not fit in one byte, they need "
                    "two, with seven bits of the second one spare. Round up: "
                    "math.ceil(n / 8), or -(-n // 8) without an import."
                ),
            )
        if got == n * 8:
            raise CheckFailed(
                f"`classical_bytes_for({n})` returned {got}, which is n multiplied by eight.",
                detail="A byte holds eight bits, so bits are divided by eight, not multiplied.",
            )
        if got == 2**n // 8:
            raise CheckFailed(
                f"`classical_bytes_for({n})` returned {got}, which came from 2 to the n.",
                detail=(
                    "This is the classical side of the comparison, and it has no 2^n in it. "
                    "A classical register of n bits holds one value, so it costs n bits."
                ),
            )
        raise CheckFailed(
            f"`classical_bytes_for({n})` returned {got}, expected {want}.",
            detail=f"{n} bits at eight bits per byte, rounded up, is {want}.",
        )


def _spread(n: int) -> QuantumCircuit:
    """A circuit whose statevector has every amplitude populated."""
    qc = QuantumCircuit(n)
    qc.h(range(n))
    return qc


def _contrast(amplitudes_for, quantum_bytes_for, classical_bytes_for) -> str:
    rows = [f"{'qubits':>7}{'amplitudes':>22}{'to simulate':>14}{'classical':>12}{'ratio':>12}"]
    # Stops at 50. Past that the amplitude count runs to thirty digits and every
    # column loses its alignment, so the hundred-qubit case is prose below.
    for n in (10, 20, 30, 40, 50):
        quantum = quantum_bytes_for(n)
        classical = classical_bytes_for(n)
        rows.append(
            f"{n:>7}{amplitudes_for(n):>22,}{_human(quantum):>14}"
            f"{_human(classical):>12}{quantum / classical:>12.1e}"
        )
    hundred_classical = classical_bytes_for(100)
    rows += [
        "",
        "The right column is the whole exercise. Both sides describe writing",
        "something down, and only one of them doubles.",
        "",
        f"A hundred classical bits fit in {hundred_classical} bytes, which is a sentence in a",
        f"text message. Simulating a hundred qubits needs {quantum_bytes_for(100):.1e} bytes,",
        f"which is {quantum_bytes_for(100) / hundred_classical:.0e} times more and does not fit "
        "in the observable universe.",
    ]
    return "\n".join(rows)


def _timed_ladder(quantum_bytes_for) -> str:
    rows = [f"{'qubits':>7}{'memory':>12}{'time to build':>16}{'vs the rung below':>20}"]
    previous = None
    for n in LADDER:
        circuit = _spread(n)
        started = time.perf_counter()
        Statevector(circuit)
        elapsed = time.perf_counter() - started
        change = f"{elapsed / previous:.1f}x" if previous else "-"
        rows.append(
            f"{n:>7}{_human(quantum_bytes_for(n)):>12}{elapsed * 1000:>13.1f} ms{change:>20}"
        )
        previous = elapsed
    rows += [
        "",
        "Two qubits apart, so each rung is four times the memory of the one below.",
        "The timings are from this machine, just now, and they wobble: they are here",
        "to be felt rather than measured, and nothing passes or fails on them.",
        "",
        "Read up the ladder and ask where it ends. Two more rungs is a gigabyte.",
        "Ten more is a terabyte. Twenty more is beyond any machine that exists.",
    ]
    return "\n".join(rows)


def _perspective(amplitudes_for, quantum_bytes_for) -> str:
    fits = max(n for n in range(1, 200) if quantum_bytes_for(n) <= BUDGET_BYTES)
    universe = next(n for n in range(1, 400) if amplitudes_for(n) > ATOMS_IN_THE_UNIVERSE)
    return (
        f"In 8 GiB of memory your own formula fits {fits} qubits, and not {fits + 1}.\n"
        f"At {universe} qubits the amplitudes outnumber the atoms in the observable\n"
        "universe, so no machine built out of matter could hold them written down.\n\n"
        "IBM runs processors above a hundred qubits today.\n\n"
        "What that proves is narrow and worth stating carefully: past a few dozen\n"
        "qubits, nobody can check your answer by simulating it. It does not by\n"
        "itself prove a quantum computer solves anything useful faster, which is a\n"
        "separate question the field has not finished answering.\n\n"
        "It does mean the safety net is gone. The next four exercises are about\n"
        "working without it."
    )


def _human(size) -> str:
    """Binary units throughout, because the budget is 8 GiB rather than 8 GB.

    Mixing the two is how a table ends up saying 16 and 17 for the same number.
    """
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if size < 1024 or unit == "PiB":
            return f"{size} B" if unit == "B" else f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.0f} PiB"  # pragma: no cover - the loop always returns first


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value


def _number(function, n, label) -> int:
    value = function(n)
    if value is None:
        raise CheckFailed(f"`{label}({n})` returned None. Replace the placeholder with a number.")
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, float) and value == int(value):
            raise CheckFailed(
                f"`{label}({n})` returned {value}, a float, "
                f"expected the whole number {int(value)}.",
                detail=(
                    "A plain / in Python always gives a float. These are exact counts, so "
                    "use math.ceil, or // for a division that is already exact."
                ),
            )
        raise CheckFailed(
            f"`{label}({n})` returned a {type(value).__name__}, expected a whole number.",
            detail="These counts are exact, so they are integers rather than floats.",
        )
    return value
