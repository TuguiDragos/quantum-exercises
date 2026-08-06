"""Verification for exercise 08."""

from qiskit.circuit.library import CZGate
from qiskit.quantum_info import Operator

from quantum_exercises.checks import (
    CheckFailed,
    assert_operator_equiv,
    assert_unitary,
    matrix_artifact,
    require_circuit,
    text_artifact,
)

ALLOWED_GATES = {"h", "cx", "barrier"}


def check(mod):
    qc = require_circuit(mod, "qc")

    if qc.num_qubits != 2:
        raise CheckFailed(f"Your circuit has {qc.num_qubits} qubits, but should have exactly 2.")

    if len(qc.data) == 0:
        raise CheckFailed(
            "Your circuit is still empty, so its matrix is the identity, not controlled-Z.",
        )

    used = {instruction.operation.name for instruction in qc.data}
    forbidden = used - ALLOWED_GATES
    if forbidden:
        raise CheckFailed(
            f"This exercise allows only h and cx, but your circuit uses: {sorted(forbidden)}.",
            detail=(
                "Reaching for cz directly gives the right matrix without showing you why "
                "CZ and CNOT are the same gate in disguise. Build it from h and cx."
            ),
        )

    assert_unitary(qc)
    operator = assert_operator_equiv(
        qc,
        Operator(CZGate()),
        message="Your circuit's matrix is not controlled-Z.",
    )

    return [
        text_artifact(str(qc.draw(output="text")), caption="Your circuit"),
        matrix_artifact(operator, caption="Its matrix, in basis |00>, |01>, |10>, |11>"),
        text_artifact(
            "Only the |11> entry carries a minus sign. Every other basis state is\n"
            "left untouched, which is exactly what 'controlled' means: the Z acts\n"
            "only when the control qubit is 1.\n\n"
            "The identity you just used is H X H = Z. Conjugating the target of a\n"
            "CNOT by Hadamards turns its X into a Z, and a CNOT becomes a CZ.",
            caption="What you just built",
        ),
    ]
