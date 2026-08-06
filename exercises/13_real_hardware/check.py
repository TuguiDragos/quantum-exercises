"""Verification for exercise 13.

This is the one exercise that may talk to a real QPU. It never does so silently:
the backend that was used is printed with the result and recorded in `qx list`.
"""

import math

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from quantum_exercises.backends import get_backend, sample
from quantum_exercises.checks import (
    Artifact,
    CheckFailed,
    assert_shots,
    assert_state_equiv,
    counts_artifact,
    require,
    text_artifact,
)

INV_SQRT2 = 1 / math.sqrt(2)
BELL = Statevector([INV_SQRT2, 0, 0, INV_SQRT2])
SHOTS = 1024

# Instructions that are legal in an ISA circuit without appearing in the
# backend's operation list.
STRUCTURAL_OPS = {"barrier", "delay"}

# Well below what any working QPU gives for a Bell state, and well above the 0.5
# you would get from an unentangled circuit.
MIN_AGREEMENT = 0.6

# Each of 00 and 11 should be near half. Loose enough for real readout bias,
# tight enough to reject a circuit that always answers the same thing.
MIN_SHARE = 0.25


def check(mod):
    build_bell = _callable(mod, "build_bell")
    to_isa = _callable(mod, "to_isa")

    bell = build_bell()
    if not isinstance(bell, QuantumCircuit):
        raise CheckFailed(
            f"build_bell() returned a {type(bell).__name__}, expected a QuantumCircuit."
        )
    if bell.num_qubits != 2:
        raise CheckFailed(
            f"build_bell() returned a circuit with {bell.num_qubits} qubits, expected 2."
        )
    if not any(instruction.operation.name == "measure" for instruction in bell.data):
        raise CheckFailed(
            "build_bell() returned a circuit with no measurement.",
            detail=(
                "Hardware has no statevector to inspect. Counts are the only output, so the "
                "measurement has to be part of the circuit. qc.measure_all() adds it."
            ),
        )

    assert_state_equiv(
        bell,
        BELL,
        message="build_bell() does not prepare (|00> + |11>) / sqrt(2).",
    )

    selection = get_backend(min_num_qubits=2)
    target = selection.backend.target

    isa = to_isa(bell, selection.backend)
    if not isinstance(isa, QuantumCircuit):
        raise CheckFailed(f"to_isa() returned a {type(isa).__name__}, expected a QuantumCircuit.")

    _assert_executable(isa, target, selection.name)

    counts = sample(isa, selection, shots=SHOTS)
    assert_shots(counts, SHOTS)

    agreed = counts.get("00", 0) + counts.get("11", 0)
    disagreed = counts.get("01", 0) + counts.get("10", 0)
    agreement = agreed / SHOTS

    if agreement < MIN_AGREEMENT:
        raise CheckFailed(
            f"Only {agreement:.1%} of shots had the two qubits agreeing, expected well above "
            f"{MIN_AGREEMENT:.0%}.",
            detail=(
                f"Counts: {dict(sorted(counts.items()))}\n"
                "A Bell state should give almost entirely 00 and 11. Around 50% suggests the "
                "cx is missing, so the qubits were never entangled."
            ),
        )

    # Agreeing is not enough on its own: a circuit that always answers 11 also
    # agrees every time. A Bell state has to be genuinely undecided between the
    # two, so require a real share of each.
    for outcome in ("00", "11"):
        share = counts.get(outcome, 0) / SHOTS
        if share < MIN_SHARE:
            raise CheckFailed(
                f"Only {share:.1%} of shots came out as {outcome!r}, expected roughly half.",
                detail=(
                    f"Counts: {dict(sorted(counts.items()))}\n"
                    "A Bell state is an even superposition of |00> and |11>, so both should "
                    "appear about as often. One outcome dominating means the circuit prepares "
                    "a definite value rather than an entangled one."
                ),
            )

    return [
        counts_artifact(counts, caption=f"{SHOTS} shots on {selection.describe()}"),
        text_artifact(_summary(selection, bell, isa, agreed, disagreed), caption="What happened"),
        # Recorded in the state file so `qx list` can show hardware versus simulator.
        Artifact(kind="text", caption="", payload="", meta={"ran_on": selection.kind}),
    ]


def _assert_executable(circuit: QuantumCircuit, target, backend_name: str) -> None:
    """Every instruction must be one this backend can run, on those exact qubits.

    Checking the gate names alone is not enough: a QPU's qubits are not all wired
    to each other, so a native two-qubit gate on an unconnected pair is rejected
    just as firmly as a gate the machine does not implement.
    """
    unsupported: list[str] = []
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in STRUCTURAL_OPS:
            continue
        qargs = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        if not target.instruction_supported(name, qargs):
            rendered = f"{name}({', '.join(str(index) for index in qargs)})"
            if rendered not in unsupported:
                unsupported.append(rendered)

    if not unsupported:
        return

    native = sorted(set(target.operation_names) - STRUCTURAL_OPS)
    gate_names = {u.split("(")[0] for u in unsupported}
    foreign_names = sorted(gate_names - set(target.operation_names))

    if foreign_names:
        detail = (
            f"{backend_name} implements only {native}.\n"
            "A real QPU rejects anything else outright rather than transpiling it for you."
        )
    else:
        detail = (
            f"Those gates exist on {backend_name}, but not between those qubits: its qubits "
            "are not all connected to each other. A pass manager built for the backend routes "
            "the circuit onto pairs that are."
        )

    raise CheckFailed(
        f"{backend_name} cannot execute {unsupported[:6]} as written.",
        detail=(
            f"{detail}\nBuild a pass manager with generate_preset_pass_manager("
            "optimization_level=1, backend=backend) and run the circuit through it."
        ),
    )


def _summary(selection, bell, isa, agreed, disagreed) -> str:
    lines = [
        f"backend      {selection.name}",
        f"chosen why   {selection.reason}",
        "",
        f"your circuit {dict(bell.count_ops())}",
        f"as ISA       {dict(isa.count_ops())}",
        "",
        f"agreed  (00 or 11)   {agreed:>5} of {SHOTS}   {agreed / SHOTS:6.2%}",
        f"disagreed (01 or 10) {disagreed:>5} of {SHOTS}   {disagreed / SHOTS:6.2%}",
    ]
    if selection.kind == "simulator":
        lines += [
            "",
            "This was a noiseless simulator, so the disagreement count is 0.",
            "Exercise 14 works either way.",
        ]
    elif disagreed:
        lines += [
            "",
            "Those disagreeing shots are not a bug in your circuit. Exercise 14 is",
            "about reading them honestly.",
        ]
    return "\n".join(lines)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value
