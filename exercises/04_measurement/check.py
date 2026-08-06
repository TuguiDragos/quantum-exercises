"""Verification for exercise 04."""

from quantum_exercises.checks import (
    CheckFailed,
    assert_counts_close,
    assert_shots,
    counts_artifact,
    require,
    require_circuit,
)

EXPECTED_SHOTS = 1024


def check(mod):
    qc = require_circuit(mod, "qc")

    if not _has_measurement(qc):
        raise CheckFailed(
            "Your circuit still has no measurement.",
            detail=(
                "Without one, the sampler has nothing to report. Qiskit does not treat this "
                "as an error, it just warns and returns an empty result. Add qc.measure_all()."
            ),
        )

    result = require(mod, "result")

    # The most common mistake: assigning the job instead of its result.
    if hasattr(result, "result") and callable(result.result):
        raise CheckFailed(
            "`result` holds the job, not the answer.",
            detail=(
                "sampler.run(...) hands back a job that may still be running. Call .result() "
                "on it to wait for the answer: sampler.run([qc], shots=SHOTS).result()"
            ),
        )

    try:
        pub_result = result[0]
    except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
        raise CheckFailed(
            f"`result` is a {type(result).__name__}, which cannot be indexed with [0].",
            detail=(
                "A V2 result is a sequence with one entry per circuit you submitted. "
                f"Underlying error: {exc}"
            ),
        ) from exc

    fields = list(pub_result.data.keys())
    if not fields:
        raise CheckFailed(
            "The result came back with no classical registers, so it holds no data.",
            detail=(
                "This is exactly the trap described in the README. The circuit ran, but nothing "
                "was measured, so there was nothing to record. Add qc.measure_all() before "
                "running it."
            ),
        )

    counts = dict(getattr(pub_result.data, fields[0]).get_counts())

    assert_shots(counts, EXPECTED_SHOTS)

    missing = {"0", "1"} - set(counts)
    if missing:
        raise CheckFailed(
            f"Only {sorted(counts)} came out of the measurement; {sorted(missing)} never appeared.",
            detail=(
                "A Hadamard on a qubit in state 0 gives an even superposition, so over 1024 "
                "shots both outcomes should show up roughly 512 times each. Check that the "
                "Hadamard is still applied before the measurement."
            ),
        )

    # 4 sigma over 1024 shots is about plus or minus 64 counts, comfortably wide
    # for an honest answer and still tight enough to catch a wrong circuit.
    assert_counts_close(counts, {"0": 0.5, "1": 0.5})

    return counts_artifact(counts, caption=f"{EXPECTED_SHOTS} shots of a Hadamard")


def _has_measurement(qc) -> bool:
    return any(instruction.operation.name == "measure" for instruction in qc.data)
