"""Verification for exercise 18."""

import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit.quantum_info import SparsePauliOp

from quantum_exercises.backends import single_register_counts
from quantum_exercises.checks import CheckFailed, require, text_artifact

SHOTS = 8192
ATOL = 1e-6

# Seeded, so this check is reproducible rather than merely probable. Verified
# empirically: the worst of the four phis below lands 0.009 from the exact value, so the
# tolerance below has a factor of five of headroom.
SEED = 16
SAMPLING_TOL = 0.05

# The angles observable_at is asked about. 0 and pi/2 pin it to Z and X; the
# others make a hardcoded pair of coefficients impossible.
ANGLES = [0.0, math.pi / 2, math.pi / 3, 1.2, -0.4]

# ry(phi)|0> has <X> = sin(phi). Includes phi = 0, where <X> is 0 and the two
# outcomes have to come out even.
PHIS = [0.0, math.pi / 2, math.pi / 3, 2.0]


def check(mod):
    observable_x = require(mod, "observable_x", SparsePauliOp)
    observable_at = _callable(mod, "observable_at")
    to_x_basis = _callable(mod, "to_x_basis")

    _check_observable_x(observable_x)
    _check_observable_at(observable_at)
    _check_rotation(to_x_basis)

    return [text_artifact(_summary(to_x_basis), caption="One instrument, two axes")]


def _check_observable_x(observable):
    if observable.num_qubits != 1:
        raise CheckFailed(
            f"`observable_x` acts on {observable.num_qubits} qubits, expected 1.",
        )
    if not np.allclose(observable.to_matrix(), SparsePauliOp("X").to_matrix(), atol=ATOL):
        raise CheckFailed(
            "`observable_x` is not the X observable.",
            detail=f"Its matrix is\n{np.round(observable.to_matrix(), 4)}\nX is [[0, 1], [1, 0]].",
        )


def _check_observable_at(observable_at):
    for theta in ANGLES:
        value = observable_at(theta)
        if not isinstance(value, SparsePauliOp):
            raise CheckFailed(
                f"observable_at({theta:.4f}) returned a {type(value).__name__}, "
                "expected a SparsePauliOp.",
                detail="A function with no `return` gives None.",
            )
        want = math.cos(theta) * SparsePauliOp("Z").to_matrix()
        want = want + math.sin(theta) * SparsePauliOp("X").to_matrix()
        if not np.allclose(value.to_matrix(), want, atol=ATOL):
            raise CheckFailed(
                f"observable_at({theta:.4f}) is not cos(theta) Z + sin(theta) X.",
                detail=(
                    f"You returned\n{np.round(value.to_matrix(), 4)}\n"
                    f"expected\n{np.round(want, 4)}\n"
                    f"cos({theta:.4f}) = {math.cos(theta):.4f}, "
                    f"sin({theta:.4f}) = {math.sin(theta):.4f}. Check the order: the Z "
                    "coefficient is the cosine."
                ),
            )


def _check_rotation(to_x_basis):
    for phi in PHIS:
        original = QuantumCircuit(1)
        original.ry(phi, 0)
        before = original.data.copy()

        rotated = to_x_basis(original)

        if original.data != before:
            raise CheckFailed(
                "to_x_basis() changed the circuit it was given.",
                detail=(
                    "`qc.h(0)` appends in place, so the caller's circuit grows every time "
                    "the function runs. Start with `circuit.copy()` and work on that."
                ),
            )
        if not isinstance(rotated, QuantumCircuit):
            raise CheckFailed(
                f"to_x_basis() returned a {type(rotated).__name__}, expected a QuantumCircuit.",
                detail="A function with no `return` gives None.",
            )
        if rotated.num_clbits == 0:
            raise CheckFailed(
                "to_x_basis() returned a circuit with no classical register, so nothing "
                "is measured.",
                detail="Rotating is only half of it. Add `measure_all()` after the rotation.",
            )

        try:
            measured = _sampled_z(rotated)
        except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
            # Measuring before the rotation makes it a mid-circuit measurement, which
            # this sampler refuses outright. Without this the reader gets the raw
            # Qiskit error instead of being told which half they put first.
            raise CheckFailed(
                "Your circuit measures before it rotates.",
                detail=(
                    "The rotation has to happen while the qubit is still a quantum state. "
                    "Once it is measured there is nothing left for `h` to turn, and this "
                    f"sampler rejects the circuit outright.\nQiskit said: {exc}"
                ),
            ) from exc
        exact = _exact(original, SparsePauliOp("X"))
        if abs(measured - exact) > SAMPLING_TOL:
            raise CheckFailed(
                f"For ry({phi:.4f}), your rotated circuit gives <Z> = {measured:+.4f}, "
                f"but <X> on the original is {exact:+.4f}.",
                detail=(
                    "The rotation has to map the X axis onto the Z axis, which is what H "
                    "does. A different gate turns the state somewhere else, and the number "
                    "you get back is that other axis rather than X.\n"
                    f"Sampled over {SHOTS} shots, so a gap of {SAMPLING_TOL} or less is noise."
                ),
            )


def _sampled_z(circuit):
    result = StatevectorSampler(seed=SEED).run([circuit], shots=SHOTS).result()
    counts = single_register_counts(result[0])
    shots = sum(counts.values())
    plus = sum(value for outcome, value in counts.items() if outcome.endswith("0"))
    return (2 * plus - shots) / shots


def _exact(circuit, observable):
    return float(StatevectorEstimator().run([(circuit, observable)]).result()[0].data.evs)


def _summary(to_x_basis):
    lines = [f"{'state':<16}{'<X> exactly':>14}{'<Z> after your rotation':>26}"]
    for phi in PHIS:
        qc = QuantumCircuit(1)
        qc.ry(phi, 0)
        lines.append(
            f"ry({phi:.4f})|0>".ljust(16)
            + f"{_exact(qc, SparsePauliOp('X')):>+14.4f}"
            + f"{_sampled_z(to_x_basis(qc)):>+26.4f}"
        )
    lines.append("")
    lines.append(
        f"The right-hand column is {SHOTS} shots through a Z measurement, which is the\n"
        "only measurement the hardware has. It agrees because H put X where Z was."
    )
    return "\n".join(lines)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but it is a {type(value).__name__}.")
    return value
