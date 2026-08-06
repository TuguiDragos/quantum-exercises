"""Verification for exercise 03."""

from qiskit.circuit.library import HGate
from qiskit.quantum_info import Operator

from quantum_exercises.checks import (
    CheckFailed,
    assert_operator_equiv,
    matrix_artifact,
    require_circuit,
    text_artifact,
)


def check(mod):
    qc = require_circuit(mod, "qc")

    if qc.num_qubits != 1:
        raise CheckFailed(
            f"Your circuit has {qc.num_qubits} qubits, but this exercise asks for exactly 1.",
            detail="QuantumCircuit(1) creates a single-qubit circuit.",
        )

    if qc.num_clbits != 0:
        raise CheckFailed(
            f"Your circuit has {qc.num_clbits} classical bits, but this exercise asks for none.",
            detail=(
                "A classical register is only needed to store measurement results, and this "
                "exercise has no measurement. QuantumCircuit(1) with a single argument gives "
                "you zero classical bits."
            ),
        )

    if len(qc.data) == 0:
        raise CheckFailed(
            "Your circuit is empty: no gate was added.",
            detail="Creating the circuit is only half the task. Now apply the Hadamard gate.",
        )

    operator = assert_operator_equiv(
        qc,
        Operator(HGate()),
        message="Your circuit does not implement a Hadamard gate.",
    )

    return [
        text_artifact(str(qc.draw(output="text")), caption="Your circuit"),
        matrix_artifact(operator, caption="The matrix it represents"),
    ]
