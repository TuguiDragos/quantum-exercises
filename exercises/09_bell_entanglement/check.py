"""Verification for exercise 09."""

import math

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import Statevector

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_close,
    assert_counts_support,
    assert_state_equiv,
    counts_artifact,
    require,
    require_circuit,
    statevector_artifact,
    text_artifact,
)

INV_SQRT2 = 1 / math.sqrt(2)
BELL = Statevector([INV_SQRT2, 0, 0, INV_SQRT2])
SHOTS = 2048


def check(mod):
    qc = require_circuit(mod, "qc")

    if qc.num_qubits != 2:
        raise CheckFailed(f"Your circuit has {qc.num_qubits} qubits, but should have exactly 2.")

    if any(instruction.operation.name == "measure" for instruction in qc.data):
        raise CheckFailed(
            "Your circuit already contains a measurement.",
            detail=(
                "Leave it out. The runner needs the statevector first, and a measured "
                "circuit no longer has one. It adds the measurement itself before sampling."
            ),
        )

    state = assert_state_equiv(
        qc,
        BELL,
        message="Your circuit does not prepare (|00> + |11>) / sqrt(2).",
    )

    _check_label(mod)
    _check_impossible(mod)

    measured = qc.copy()
    measured.measure_all()
    counts = dict(
        StatevectorSampler(seed=99).run([measured], shots=SHOTS).result()[0].data.meas.get_counts()
    )

    assert_counts_support(
        counts,
        {"00", "11"},
        message="Sampling your state produced outcomes a Bell state cannot give.",
    )
    assert_counts_close(counts, {"00": 0.5, "11": 0.5})

    return [
        statevector_artifact(state, caption="Your Bell state"),
        counts_artifact(counts, caption=f"{SHOTS} shots: the two qubits always agree"),
        text_artifact(_endianness_demo(), caption="Little-endian, demonstrated"),
    ]


def _check_label(mod) -> None:
    label = require(mod, "label_q0_only", str)
    if len(label) != 2 or set(label) - {"0", "1"}:
        raise CheckFailed(
            f"`label_q0_only` is {label!r}, which is not a two-character bitstring.",
            detail='Give a string of two characters, each "0" or "1", for example "00".',
        )
    if label != "01":
        raise CheckFailed(
            f'`label_q0_only` is {label!r}, but the answer is "01".',
            detail=(
                "Qiskit is little-endian: qubit 0 is the RIGHTMOST character. So qubit 0 "
                "measured as 1 puts the 1 on the right, and qubit 1 measured as 0 puts the "
                '0 on the left, giving "01". Writing "10" is reading it the textbook way.'
            ),
        )


def _check_impossible(mod) -> None:
    value = require(mod, "impossible_outcomes")
    if not isinstance(value, (set, frozenset)):
        raise CheckFailed(
            f"`impossible_outcomes` should be a set, not a {type(value).__name__}.",
            detail='Write it with braces, for example {"00", "11"}.',
        )
    if value != {"01", "10"}:
        raise CheckFailed(
            f"`impossible_outcomes` is {value!r}, but the answer is {{'01', '10'}}.",
            detail=(
                "The Bell state is a superposition of |00> and |11> only. Those two are the "
                "outcomes you DO get. The ones you never get are the ones where the qubits "
                "disagree."
            ),
        )


def _endianness_demo() -> str:
    """Show the bit order using a circuit with a single X on qubit 0."""
    demo = QuantumCircuit(2)
    demo.x(0)
    demo.measure_all()
    counts = dict(
        StatevectorSampler(seed=3).run([demo], shots=64).result()[0].data.meas.get_counts()
    )
    outcome = max(counts, key=lambda key: counts[key])
    return (
        "A circuit with x() on qubit 0 only, and nothing on qubit 1:\n\n"
        f"    counts -> {counts}\n\n"
        f"Qubit 0 is the one that was flipped, and the 1 appears at the RIGHT\n"
        f"end of {outcome!r}. That is little-endian, and it is why the runner\n"
        "keeps reminding you about it."
    )
