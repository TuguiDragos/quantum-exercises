"""Verification for exercise 10."""

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import Operator

from quantum_exercises.checks import CheckFailed, require, text_artifact

SHOTS = 256

# name of the oracle in exercise.py, is it balanced, expected measured outcome
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
                        _balanced_diagnosis(circuit, oracle)
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

    _check_the_oracle_is_composed(deutsch)
    _check_majority(is_balanced)

    # The classical comparison, stated with the numbers just produced.
    summary = [f"{'function':<20} {'kind':<10} {'measured':<16} {'your verdict'}"]
    for name, balanced, counts, verdict in rows:
        kind = "balanced" if balanced else "constant"
        summary.append(
            f"{name:<20} {kind:<10} {str(dict(counts)):<16} {'balanced' if verdict else 'constant'}"
        )
    summary += [
        "",
        "Four functions, four correct answers, one query to each.",
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


# A simulator answers unanimously, so the four cases above never distinguish a
# majority vote from "did this outcome occur at all". Hardware always leaks a few
# shots the other way, and there the difference decides the answer.
NOISY_CASES = [
    ({"1": 231, "0": 25}, True),
    ({"0": 240, "1": 16}, False),
    ({"1": 130, "0": 126}, True),
]


def _check_majority(is_balanced) -> None:
    for counts, expected in NOISY_CASES:
        verdict = is_balanced(counts)
        if verdict != expected:
            raise CheckFailed(
                f"is_balanced({counts}) returned {verdict}, expected {expected}.",
                detail=(
                    "These are the counts a real device gives: mostly one answer, with a few "
                    "shots the other way. Deciding on whether an outcome appears at all gets "
                    "this wrong. Take the outcome that occurred most often."
                ),
            )


# What the sandwich itself contributes. Anything else in the circuit came from
# the oracle, whether it was composed in or appended as a single gate.
SCAFFOLDING = {"h", "measure", "barrier"}


def _sandwich(oracle: QuantumCircuit) -> QuantumCircuit:
    """The circuit deutsch() is asked for, without the measurement."""
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.compose(oracle, inplace=True)
    qc.h(0)
    return qc


# An angle no whole number of turns comes back to. Any rotation by a rational
# multiple of pi would: a T gate is an eighth of a turn, so nine of them are the
# same operator as one, and a deutsch() that composed the oracle nine times
# passed. One radian divides 2*pi nowhere, so U**k is equivalent to U only at
# k = 1. Checked out to k = 400.
PROBE_ANGLE = 1.0


def _probe() -> QuantumCircuit:
    """An oracle from outside the four.

    A rotation by one radian is a phase oracle for no Boolean function at all,
    which is the point: the algorithm never asks which function it was handed, so
    it has to work for anything that arrives.
    """
    qc = QuantumCircuit(1)
    qc.rz(PROBE_ANGLE, 0)
    return qc


def _check_the_oracle_is_composed(deutsch) -> None:
    """Hand deutsch() an oracle it cannot have anticipated.

    Reading one of the four and writing the answer out by hand builds the same
    circuit as composing it, gate for gate in two cases out of four, so nothing in
    the returned circuit separates the two. The separation comes from the input
    instead: composing works for any oracle, classifying works only for the four.

    The probe also has to be an oracle plain repetition cannot imitate. Every one
    of the four is its own inverse, so composing one twice is the identity and any
    odd number of times is the same operator as once; the same held for the T gate
    used here at first, where nine applications passed. One radian divides 2*pi
    nowhere, so U**k matches U only at k = 1 and stacking the probe fails.

    What that establishes, exactly: between the two Hadamards the circuit is the
    oracle applied once, up to global phase. It is not a count of how many times
    deutsch() reached for the oracle. `U ; U ; U.inverse()` is three queries whose
    product is U, and it passes; so does `U ; U.inverse() ; U`. Both were run.

    That gap is not closable from here, and deliberately so. A deutsch() that
    rebuilds the oracle from its matrix has to pass, because applying it once is
    the entire claim the algorithm makes, and by the time the oracle is a matrix
    there is nothing left in the circuit to count. Anything that counted calls
    would reject that solution too. The narrower claim is the true one, and it is
    the one that catches the answer this check exists for: a deutsch() that reads
    which of the four it was handed and writes the outcome out itself.
    """
    probe = _probe()
    try:
        circuit = deutsch(probe)
    except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
        # The four have already been through it by now, so this is not a general
        # fault: it is a deutsch() that only knows the oracles it expected.
        raise CheckFailed(
            f"deutsch() raised {type(exc).__name__} on an oracle outside the four.",
            detail=(
                "It works for the four in this file and for nothing else, which means it "
                "is reading the oracle rather than composing it. Composing does not care "
                f"what arrived.\nPython reported: {type(exc).__name__}: {exc}"
            ),
        ) from exc

    if not isinstance(circuit, QuantumCircuit) or circuit.num_qubits != 1:
        raise CheckFailed(
            "deutsch() did not return a one-qubit circuit for an oracle outside the four.",
            detail=(
                "It is handed a QuantumCircuit and has to work for any of them, because "
                "the algorithm never looks at which function it was given."
            ),
        )

    built = Operator(circuit.remove_final_measurements(inplace=False))
    if built.equiv(Operator(_sandwich(probe))):
        return

    raise CheckFailed(
        "deutsch() does not put the oracle it was handed into the circuit.",
        detail=(
            "Handed a one-qubit circuit that is none of the four, it came back with "
            "something else between the two Hadamards.\n"
            "Composing works whatever arrives. Deciding from the oracle's contents works "
            "only for the four in this file, and it answers the question classically "
            "before the circuit has run, which is precisely the query the algorithm is "
            "not allowed to make."
        ),
    )


def _oracle_missing(circuit, oracle) -> bool:
    """Whether the oracle left no trace at all in the returned circuit.

    Only conclusive for an oracle that has gates to look for. constant_zero has
    none and constant_one carries a global phase rather than a gate, so nothing
    can be said about those two, and nothing is.

    Used for the wording of a failure rather than to decide one. The check that
    the oracle is really used is _check_the_oracle_is_composed, which works by
    choosing the input rather than by inspecting the output.
    """
    if not oracle.data:
        return False
    return all(instruction.operation.name in SCAFFOLDING for instruction in circuit.data)


def _balanced_diagnosis(circuit, oracle) -> str:
    """Both ways a balanced function comes back looking constant."""
    if _oracle_missing(circuit, oracle):
        return (
            "The circuit is the two Hadamards and nothing between them, so the oracle was "
            "never put in. Insert it with qc.compose(oracle, inplace=True)."
        )
    return (
        "Getting the constant answer for a balanced function usually means the "
        "oracle was applied twice: the two sign flips cancel and the "
        "information is destroyed. Compose it exactly once."
    )


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
        raise CheckFailed(f"`{name}` should be a function, but its type is {type(value).__name__}.")
    return value
