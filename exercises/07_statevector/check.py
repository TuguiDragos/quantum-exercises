"""Verification for exercise 07."""

import math

from qiskit.quantum_info import Statevector

from quantum_exercises.checks import (
    CheckFailed,
    assert_state_equiv,
    require_circuit,
    statevector_artifact,
    text_artifact,
)

INV_SQRT2 = 1 / math.sqrt(2)

TARGETS = {
    "qc_a": (Statevector([INV_SQRT2, 1j * INV_SQRT2]), "(|0> + i|1>) / sqrt(2)"),
    "qc_b": (Statevector([INV_SQRT2, -INV_SQRT2]), "(|0> - |1>) / sqrt(2)"),
}


def check(mod):
    artifacts = []
    artifacts_state = {}

    for name, (target, description) in TARGETS.items():
        qc = require_circuit(mod, name)

        if qc.num_qubits != 1:
            raise CheckFailed(f"`{name}` has {qc.num_qubits} qubits, but should have exactly 1.")

        if len(qc.data) == 0:
            raise CheckFailed(
                f"`{name}` is still empty, so it prepares |0> rather than {description}.",
                detail="Add gates to the circuit that is already created for you.",
            )

        state = assert_state_equiv(
            qc,
            target,
            message=f"`{name}` does not prepare {description}.",
        )
        artifacts_state[name] = state
        artifacts.append(statevector_artifact(state, caption=f"{name} = {description}"))

    # Show that global phase really is ignored, using the learner's own state.
    # Built from the Statevector the comparison already produced, so a circuit
    # that also contains a measurement cannot break the demonstration.
    state_a = artifacts_state["qc_a"]
    rotated = Statevector(state_a.data * 1j)  # multiplies the whole state by i

    same = rotated.equiv(state_a)
    identical = rotated == state_a
    if not same or identical:
        raise CheckFailed(
            "Internal check failed: global phase did not behave as expected.",
            detail=f"equiv returned {same}, == returned {identical}.",
        )

    artifacts.append(
        text_artifact(
            "Multiplying your qc_a by i throughout gives a state where every\n"
            "amplitude differs:\n\n"
            "    Statevector(rotated) == Statevector(qc_a)      -> False\n"
            "    Statevector(rotated).equiv(Statevector(qc_a))  -> True\n\n"
            "No experiment can tell those two apart, which is why equiv is the\n"
            "honest comparison and == is not.",
            caption="Global phase, demonstrated on your circuit",
        )
    )

    return artifacts
