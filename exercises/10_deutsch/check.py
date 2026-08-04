"""Verification for exercise 10."""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

from quantum_exercises.checks import CheckFailed, require, text_artifact

SHOTS = 256

# name, oracle factory, is it balanced, expected measured outcome
FUNCTIONS = [
    ("constant_zero", False, "0"),
    ("constant_one", False, "0"),
    ("balanced_identity", True, "1"),
    ("balanced_not", True, "1"),
]


def check(mod):
    deutsch = _callable(mod, "deutsch")
    is_balanced = _callable(mod, "is_balanced")

    rows = []
    for name, balanced, expected in FUNCTIONS:
        oracle = _callable(mod, name)()
        if not isinstance(oracle, QuantumCircuit):
            raise CheckFailed(
                f"{name}() should return a QuantumCircuit. Leave the oracles as they are."
            )

        circuit = deutsch(oracle)
        _validate_circuit(circuit, name)

        counts = _sample(circuit)
        measured = max(counts, key=lambda outcome: counts[outcome])

        if measured != expected:
            raise CheckFailed(
                f"With {name}, which is {'balanced' if balanced else 'constant'}, "
                f"your circuit measured {measured!r} but should measure {expected!r}.",
                detail=(
                    f"Counts: {counts}\n"
                    + (
                        "Getting the constant answer for a balanced function usually means the "
                        "oracle was applied twice: the two sign flips cancel and the "
                        "information is destroyed. Compose it exactly once."
                        if balanced
                        else "Check the order: Hadamard, then the oracle, then Hadamard."
                    )
                ),
            )

        verdict = is_balanced(counts)
        if not isinstance(verdict, bool):
            raise CheckFailed(
                f"is_balanced returned a {type(verdict).__name__} for {name}, expected a bool."
            )
        if verdict != balanced:
            raise CheckFailed(
                f"is_balanced({counts}) returned {verdict}, expected {balanced}.",
                detail="Measuring 1 means balanced. Measuring 0 means constant.",
            )

        rows.append((name, balanced, counts, verdict))

    # The classical comparison, stated with the numbers just produced.
    summary = [f"{'function':<20} {'kind':<10} {'measured':<16} {'your verdict'}"]
    for name, balanced, counts, verdict in rows:
        kind = "balanced" if balanced else "constant"
        summary.append(
            f"{name:<20} {kind:<10} {str(dict(counts)):<16} {'balanced' if verdict else 'constant'}"
        )
    summary += [
        "",
        "Four functions, four correct answers, one oracle call each.",
        "",
        "Classically this needs two calls, and that is not a matter of writing",
        "smarter code: after a single classical evaluation, two functions are",
        "still consistent with what you saw, one constant and one balanced.",
        "",
        "You never learned f(0) or f(1) on their own. You learned whether they",
        "agree, which is all the question asked for, and that is what fits in",
        "a single query.",
    ]

    return text_artifact("\n".join(summary), caption="One query, four functions")


def _validate_circuit(circuit, name: str) -> None:
    if not isinstance(circuit, QuantumCircuit):
        raise CheckFailed(
            f"deutsch() returned a {type(circuit).__name__} for {name}, expected a QuantumCircuit."
        )
    if circuit.num_qubits != 1:
        raise CheckFailed(
            f"deutsch() built a circuit with {circuit.num_qubits} qubits, expected 1."
        )

    ops = dict(circuit.count_ops())
    if not any(op == "measure" for op in ops):
        raise CheckFailed(
            "The circuit deutsch() returns has no measurement.",
            detail="Finish it with qc.measure_all(), or there is nothing to read.",
        )
    if ops.get("h", 0) != 2:
        raise CheckFailed(
            f"deutsch() should apply exactly two Hadamards, but it applies {ops.get('h', 0)}.",
            detail=(
                "One before the oracle to put the qubit into both inputs at once, and one "
                "after to interfere the results. That sandwich is the algorithm."
            ),
        )


def _sample(circuit) -> dict[str, int]:
    result = StatevectorSampler(seed=23).run([circuit], shots=SHOTS).result()
    fields = list(result[0].data.keys())
    if not fields:
        raise CheckFailed(
            "The circuit produced no data, so it has no measurement.",
            detail="Add qc.measure_all() at the end of deutsch().",
        )
    return dict(getattr(result[0].data, fields[0]).get_counts())


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value
