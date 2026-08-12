"""Verification for exercise 13."""

import math

from qiskit.quantum_info import Statevector

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_close,
    assert_counts_support,
    assert_shots,
    assert_state_equiv,
    counts_artifact,
    require,
    require_circuit,
    text_artifact,
)

INV_SQRT2 = 1 / math.sqrt(2)
BELL = Statevector([INV_SQRT2, 0, 0, INV_SQRT2])
SHOTS = 1024


def check(mod):
    qc = require_circuit(mod, "qc")

    if qc.num_qubits != 2 or qc.num_clbits != 2:
        raise CheckFailed(
            f"The circuit should stay at 2 qubits and 2 classical bits, "
            f"but it has {qc.num_qubits} and {qc.num_clbits}.",
            detail="Only the way the circuit is run needed changing, not the circuit itself.",
        )

    if not any(instruction.operation.name == "measure" for instruction in qc.data):
        raise CheckFailed("The circuit lost its measurement during the rewrite.")

    assert_state_equiv(
        qc,
        BELL,
        message="The circuit no longer prepares a Bell state.",
    )

    result = require(mod, "result")
    if hasattr(result, "get_counts"):
        raise CheckFailed(
            "`result` has a .get_counts() method, so it is not a V2 primitive result.",
            detail=(
                "That is what `backend.run(...).result()` hands back, and it is a current "
                "API rather than a dead one: exercise 14 reads a hardware result exactly "
                "that way. execute() had two replacements, and the one practised here is "
                "the primitive, whose result is indexed per circuit. Build it with "
                "StatevectorSampler."
            ),
        )

    try:
        fields = list(result[0].data.keys())
    except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
        raise CheckFailed(
            f"`result` is a {type(result).__name__} and does not behave like a V2 result.",
            detail=f"Expected something indexable with [0]. Underlying error: {exc}",
        ) from exc

    if fields != ["c"]:
        raise CheckFailed(
            f"The result's classical registers are {fields}, expected ['c'].",
            detail=(
                "QuantumCircuit(2, 2) creates a register named 'c'. Getting 'meas' instead "
                "means measure_all() was used, which changes the circuit you were asked to keep."
            ),
        )

    counts = require(mod, "counts", dict)
    reference = dict(result[0].data.c.get_counts())

    if dict(counts) != reference:
        raise CheckFailed(
            "`counts` does not match what `result` actually contains.",
            detail=(
                f"You set     {dict(counts)}\n"
                f"result has  {reference}\n"
                "Read the counts out of the result rather than writing them in by hand."
            ),
        )

    assert_shots(counts, SHOTS)
    assert_counts_support(
        counts,
        {"00", "11"},
        message="A Bell state cannot produce outcomes where the two qubits disagree.",
    )
    assert_counts_close(counts, {"00": 0.5, "11": 0.5})

    return [
        counts_artifact(counts, caption=f"2021 code, running on Qiskit 2.x ({SHOTS} shots)"),
        text_artifact(
            "What execute() used to hide:\n\n"
            "  execute(qc, backend, shots=1024)\n"
            "      = transpile(qc, backend)  then  backend.run(..., shots=1024)\n\n"
            "The V2 primitives split those steps apart on purpose. For local work\n"
            "StatevectorSampler does both for you; for hardware, exercise 14 makes\n"
            "you do the transpile step yourself, because there it is not optional.",
            caption="Why the API changed",
        ),
    ]
