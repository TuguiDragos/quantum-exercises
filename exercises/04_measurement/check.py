"""Verification for exercise 04."""

from quantum_exercises.checks import (
    CheckFailed,
    as_statevector,
    assert_counts_close,
    assert_shots,
    counts_artifact,
    require,
    require_circuit,
)

# Deliberately not the sampler's own default of 1024. At that figure, leaving
# `shots=SHOTS` off the run entirely gave the right answer by coincidence and the
# shot count below could never catch it.
EXPECTED_SHOTS = 2048


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
    _assert_result_came_from(counts, qc)

    missing = {"0", "1"} - set(counts)
    if missing:
        raise CheckFailed(
            f"Only {sorted(counts)} came out of the measurement; {sorted(missing)} never appeared.",
            detail=(
                f"A Hadamard on a qubit in state 0 gives an even superposition, so over "
                f"{EXPECTED_SHOTS} shots both outcomes should show up roughly "
                f"{EXPECTED_SHOTS // 2} times each. Check that the Hadamard is still applied "
                "before the measurement."
            ),
        )

    # 4 sigma over 2048 shots is about plus or minus 90 counts, comfortably wide
    # for an honest answer and still tight enough to catch a wrong circuit.
    assert_counts_close(counts, {"0": 0.5, "1": 0.5})

    return counts_artifact(counts, caption=f"{EXPECTED_SHOTS} shots of a Hadamard")


def _assert_result_came_from(counts: dict[str, int], qc) -> None:
    """Tie the numbers to the circuit that was supposed to produce them.

    Nothing else here reads `qc` and `result` together, so a wrong circuit paired
    with counts from a different one passed. Compared against what `qc` itself
    predicts, at the same tolerance as the check below, because these counts are
    a sample rather than an exact distribution.
    """
    predicted = as_statevector(qc).probabilities_dict()
    shots = sum(counts.values())
    try:
        assert_counts_close(counts, predicted)
    except CheckFailed as exc:
        # Worded here rather than passed through: assert_counts_close speaks to a
        # learner who wrote the probabilities down, and these came from a circuit.
        want = ", ".join(f"'{key}': {float(value):.4f}" for key, value in sorted(predicted.items()))
        got = ", ".join(f"'{key}': {value / shots:.4f}" for key, value in sorted(counts.items()))
        raise CheckFailed(
            "The counts in `result` are not a sample of the circuit in `qc`.",
            detail=(
                "`result` has to come from running the circuit you built, so hand `qc` "
                "itself to the sampler: sampler.run([qc], shots=SHOTS).\n"
                f"qc predicts   {{{want}}}\n"
                f"result shows  {{{got}}}"
            ),
        ) from exc


def _has_measurement(qc) -> bool:
    return any(instruction.operation.name == "measure" for instruction in qc.data)
