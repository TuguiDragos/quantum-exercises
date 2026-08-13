"""Verification for exercise 19."""

import itertools
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Pauli, SparsePauliOp, Statevector

from quantum_exercises.checks import (
    ATOL,
    CheckFailed,
    require,
    text_artifact,
)

# Tolerance for a number the Estimator computed exactly rather than sampled.
TOL = 1e-9

RY_ANGLES = (math.pi / 6, math.pi / 3, math.pi / 2, 2 * math.pi / 3)


def _state(*gates) -> QuantumCircuit:
    qc = QuantumCircuit(1)
    for gate in gates:
        getattr(qc, gate)(0)
    return qc


# Name, circuit, and where on the sphere it belongs.
CARDINAL = (
    ("|0>", _state(), "north pole"),
    ("|1>", _state("x"), "south pole"),
    ("|+>", _state("h"), "equator, front"),
    ("|->", _state("x", "h"), "equator, back"),
    ("|+i>", _state("h", "s"), "equator, right"),
    ("|-i>", _state("h", "sdg"), "equator, left"),
)

# Azimuth is what separates the four points around the equator, so each one is
# checked by name rather than left to the polar angle alone.
AZIMUTHS = (
    ("|+>", _state("h"), 0.0),
    ("|+i>", _state("h", "s"), math.pi / 2),
    ("|->", _state("x", "h"), math.pi),
    ("|-i>", _state("h", "sdg"), -math.pi / 2),
)


def check(mod):
    _check_observable(mod)
    bloch_vector = _callable(mod, "bloch_vector")
    angles = _callable(mod, "angles")

    _check_cardinals(bloch_vector)
    _check_length(bloch_vector)
    _check_global_phase(bloch_vector)
    _check_polar(bloch_vector, angles)
    _check_polar_uses_the_length(angles)
    _check_azimuth(bloch_vector, angles)

    return [
        text_artifact(_drawing(bloch_vector, angles), caption="Where your qubit is pointing"),
        text_artifact(_cardinal_table(bloch_vector, angles), caption="Six states, six points"),
        text_artifact(_phase_demo(bloch_vector), caption="Global phase, finally visible"),
        text_artifact(_half_angle_table(bloch_vector, angles), caption="The half angle, resolved"),
    ]


def _reference(circuit: QuantumCircuit) -> tuple[float, float, float]:
    """The three coordinates, computed without touching the learner's code."""
    state = Statevector(circuit)
    return tuple(float(np.real(state.expectation_value(Pauli(axis)))) for axis in "XYZ")


def _check_observable(mod) -> None:
    observable = require(mod, "observable_y", SparsePauliOp)
    matrix = np.asarray(observable.to_matrix())
    if matrix.shape != (2, 2):
        raise CheckFailed(
            f"`observable_y` acts on {int(math.log2(matrix.shape[0]))} qubits, expected 1."
        )
    if np.allclose(matrix, -Pauli("Y").to_matrix(), atol=ATOL):
        raise CheckFailed(
            "`observable_y` is minus Y rather than Y.",
            detail="Y is [[0, -i], [i, 0]]. The sign matters: an observable is not a state, "
            "so a phase in front of it is not free the way a global phase on a state is.",
        )
    if not np.allclose(matrix, Pauli("Y").to_matrix(), atol=ATOL):
        raise CheckFailed(
            "`observable_y` is not the Y observable.",
            detail='Build it the same way the two given ones are built: SparsePauliOp("Y").',
        )


def _check_cardinals(bloch_vector) -> None:
    for name, circuit, where in CARDINAL:
        got = _vector(bloch_vector, circuit, name)
        want = _reference(circuit)
        if np.allclose(got, want, atol=TOL):
            continue

        # The single most likely slip: the three numbers in the wrong order.
        label = _ordering_used(bloch_vector)
        if label is not None:
            raise CheckFailed(
                f"For {name} the three numbers are right but the order is not.",
                detail=(
                    f"You returned them as {label}. The convention here is (x, y, z), "
                    "so <X> first and <Z> last."
                ),
            )
        if math.isclose(got[1], want[2], abs_tol=TOL) and not math.isclose(
            want[1], want[2], abs_tol=TOL
        ):
            raise CheckFailed(
                f"For {name} the y coordinate looks like <Z> rather than <Y>.",
                detail="Each axis needs its own observable. Check that `observable_y` is "
                "what you passed for the middle number.",
            )
        raise CheckFailed(
            f"`bloch_vector` gives {_fmt(got)} for {name}, expected {_fmt(want)} ({where}).",
            detail=(
                "Each coordinate is one expectation value: x is <X>, y is <Y>, z is <Z>, "
                "all on the same circuit."
            ),
        )


# Every wrong ordering, written as the positions to read first, second and third
# to get (x, y, z) back.
_ORDERINGS = tuple(order for order in itertools.permutations((0, 1, 2)) if order != (0, 1, 2))


def _ordering_used(bloch_vector) -> str | None:
    """Name the order a learner returned the coordinates in, or None if unclear.

    Weighed against all six cardinal states rather than the one that failed. For
    |0>, which is (0, 0, 1), several orderings fit the numbers equally well, and
    naming the wrong one sends the reader to inspect a line that is correct.
    """
    measured = [
        (_vector(bloch_vector, circuit, name), _reference(circuit)) for name, circuit, _ in CARDINAL
    ]
    fits = [
        order
        for order in _ORDERINGS
        if all(np.allclose([got[i] for i in order], want, atol=TOL) for got, want in measured)
    ]
    if len(fits) != 1:
        return None
    # Reading position order[0] first means that position is where x ended up.
    axes = ["", "", ""]
    for position, axis in zip(fits[0], "xyz", strict=True):
        axes[position] = axis
    return "(" + ", ".join(axes) + ")"


def _check_length(bloch_vector) -> None:
    for name, circuit, _ in CARDINAL:
        vector = _vector(bloch_vector, circuit, name)
        length = math.sqrt(sum(component**2 for component in vector))
        if not math.isclose(length, 1.0, abs_tol=1e-6):
            raise CheckFailed(
                f"The vector for {name} has length {length:.6f}, expected 1.",
                detail=(
                    "Every state a measurement-free circuit can prepare sits on the surface "
                    "of the sphere. A shorter vector means one of the three coordinates is "
                    "not the expectation value it should be."
                ),
            )


def _check_global_phase(bloch_vector) -> None:
    """The claim exercise 07 asked the learner to take on trust."""
    plain = _state("h", "t")
    shifted = plain.copy()
    shifted.global_phase += math.pi / 2

    before = _vector(bloch_vector, plain, "the phase test circuit")
    after = _vector(bloch_vector, shifted, "the phase test circuit")
    if not np.allclose(before, after, atol=TOL):
        raise CheckFailed(
            "Adding a global phase moved the point, and it must not.",
            detail=(
                f"Before {_fmt(before)}, after {_fmt(after)}. An expectation value of a "
                "Pauli cannot see a global phase, so if these differ the coordinates are "
                "coming from somewhere other than the Estimator."
            ),
        )


def _check_polar(bloch_vector, angles) -> None:
    for theta in RY_ANGLES:
        circuit = QuantumCircuit(1)
        circuit.ry(theta, 0)
        vector = _vector(bloch_vector, circuit, f"ry({theta:.4f})")
        got_theta, _ = _angles(angles, vector, f"ry({theta:.4f})")

        if math.isclose(got_theta, theta, abs_tol=1e-6):
            continue
        if math.isclose(got_theta, theta / 2, abs_tol=1e-6):
            raise CheckFailed(
                f"`angles` gave theta = {got_theta:.6f} for ry({theta:.6f}), half of it.",
                detail=(
                    "The half angle belongs to the amplitudes, not to the sphere. "
                    "Ry(theta) makes amplitudes cos(theta/2) and sin(theta/2), and the very "
                    "same gate turns the Bloch vector by the full theta. Read z straight out "
                    "of the vector rather than going back through the amplitudes."
                ),
            )
        # Kept for an angle small enough that its degree form is still under pi.
        # For every angle in RY_ANGLES the range guard in _angles answers first.
        if math.isclose(got_theta, math.degrees(theta), abs_tol=1e-6):
            raise CheckFailed(
                f"`angles` gave theta = {got_theta:.4f}, which is {theta:.4f} in degrees.",
                detail="math.acos already returns radians. Nothing needs converting.",
            )
        if math.isclose(got_theta, math.pi / 2 - theta, abs_tol=1e-6):
            raise CheckFailed(
                f"`angles` gave theta = {got_theta:.6f}, measured up from the equator.",
                detail=(
                    "theta is measured down from the +Z axis, so |0> is 0 and the equator "
                    "is pi/2. That is arccos(z), not arcsin(z)."
                ),
            )
        raise CheckFailed(
            f"`angles` gave theta = {got_theta:.6f} for ry({theta:.6f}), expected {theta:.6f}.",
            detail="The angle down from the north pole is arccos(z / length).",
        )


# A point inside the sphere rather than on it, which is what a mixed state gives.
# Length 0.5, so theta is arccos(0.4 / 0.5) and not arccos(0.4).
INSIDE = (0.3, 0.0, 0.4)


def _check_polar_uses_the_length(angles) -> None:
    """The README asks for arccos(z / length), and every vector above has length 1.

    On the surface the division changes nothing, so `arccos(z)` passed all of it.
    A point inside the sphere is where the two part company, and it is a state a
    real device produces: every mixed state sits in there.
    """
    got_theta, _ = _angles(angles, INSIDE, "a point inside the sphere")
    want = math.acos(INSIDE[2] / math.sqrt(sum(c * c for c in INSIDE)))
    if math.isclose(got_theta, want, abs_tol=1e-6):
        return

    if math.isclose(got_theta, math.acos(INSIDE[2]), abs_tol=1e-6):
        raise CheckFailed(
            f"`angles` gave theta = {got_theta:.6f} for {_fmt(INSIDE)}, expected {want:.6f}.",
            detail=(
                "That is arccos(z) without the division. Every state checked so far sits on "
                "the surface, where the length is 1 and the division cannot be seen. This one "
                "is inside, which is where a mixed state lands, and there theta is "
                "arccos(z / length)."
            ),
        )
    raise CheckFailed(
        f"`angles` gave theta = {got_theta:.6f} for {_fmt(INSIDE)}, expected {want:.6f}.",
        detail="theta is arccos(z / length), and this vector has length 0.5 rather than 1.",
    )


def _check_azimuth(bloch_vector, angles) -> None:
    for name, circuit, want in AZIMUTHS:
        vector = _vector(bloch_vector, circuit, name)
        _, got = _angles(angles, vector, name)

        if _same_angle(got, want):
            continue
        if _same_angle(got, math.pi / 2 - want):
            raise CheckFailed(
                f"For {name} phi came out as {got:+.6f}, expected {want:+.6f}.",
                detail=(
                    "Two mistakes land on that number. The usual one is atan2 with its "
                    "arguments the wrong way round, which measures from the Y axis instead "
                    "of from X: math.atan2 takes y first, as atan2(y, x). The other is "
                    "plain atan(y / x) with a guard for x = 0, which cannot tell +X from "
                    "-X and gives up exactly on the Y axis, where this state sits."
                ),
            )
        if _same_angle(got, -want) and not _same_angle(want, 0.0):
            raise CheckFailed(
                f"For {name} phi came out as {got:+.6f}, the negative of {want:+.6f}.",
                detail="Check the argument order in atan2, and that y is not being negated.",
            )
        raise CheckFailed(
            f"For {name} phi came out as {got:+.6f}, expected {want:+.6f}.",
            detail=(
                f"Its vector is {_fmt(_reference(circuit))}, and phi is the angle of the "
                "shadow it casts on the equator, starting from +X and turning toward +Y."
            ),
        )


def _same_angle(left: float, right: float) -> bool:
    """Compare on the circle, so pi and -pi are the same direction."""
    return abs((left - right + math.pi) % (2 * math.pi) - math.pi) < 1e-6


def _vector(bloch_vector, circuit, name) -> tuple[float, float, float]:
    value = bloch_vector(circuit)
    if value is None:
        raise CheckFailed(f"`bloch_vector` returned None for {name}.")
    if not isinstance(value, (tuple, list)):
        raise CheckFailed(
            f"`bloch_vector` returned a {type(value).__name__}, expected a tuple of three numbers."
        )
    if len(value) != 3:
        raise CheckFailed(
            f"`bloch_vector` returned {len(value)} numbers, expected 3.",
            detail="One per axis: <X>, <Y> and <Z>, in that order.",
        )
    for component in value:
        if not isinstance(component, (int, float)):
            raise CheckFailed(
                f"`bloch_vector` returned a {type(component).__name__} inside the tuple, "
                "expected numbers.",
                detail="The Estimator hands back a NumPy value, so wrap each one in float().",
            )
    return tuple(float(component) for component in value)


def _angles(angles, vector, name) -> tuple[float, float]:
    try:
        value = angles(vector)
    except ValueError as exc:
        raise CheckFailed(
            f"`angles` raised ValueError({exc}) on {name}.",
            detail=(
                "math.acos refuses anything outside [-1, 1], and a ratio computed from "
                "floats can land a whisker past 1. Clamp it into range before calling acos."
            ),
        ) from exc
    if value is None:
        raise CheckFailed("`angles` returned None. Return the pair (theta, phi).")
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise CheckFailed(
            f"`angles` returned {type(value).__name__} for {name}, expected two numbers.",
            detail="Return them in the order (theta, phi): down from the pole, then around.",
        )
    for component in value:
        if not isinstance(component, (int, float)):
            raise CheckFailed(
                f"`angles` returned a {type(component).__name__} inside the pair, expected numbers."
            )
    theta, phi = (float(component) for component in value)
    if theta < -1e-9 or theta > math.pi + 1e-9:
        # An answer in degrees lands here, not in the rule below in _check_polar:
        # every angle this exercise asks about is past pi once converted, so the
        # range guard reaches it first. Saying "the pair is swapped" to someone who
        # only forgot the units sends them to rewrite the wrong line.
        # The 2*pi floor keeps a merely out of range radian out of this branch.
        if theta > 2 * math.pi and math.radians(theta) <= math.pi:
            raise CheckFailed(
                f"`angles` gave theta = {theta:.4f} for {name}, which is that angle in degrees.",
                detail="math.acos already returns radians. Nothing needs converting.",
            )
        raise CheckFailed(
            f"`angles` gave theta = {theta:.6f} for {name}, which is outside 0 to pi.",
            detail=(
                "theta runs from 0 at the north pole to pi at the south, and arccos already "
                "returns exactly that range. A value outside it means the pair is swapped: "
                "the order is (theta, phi)."
            ),
        )
    return theta, phi


def _fmt(vector) -> str:
    return "(" + ", ".join(f"{component:+.3f}" for component in vector) + ")"


# --------------------------------------------------------------------------
# The picture
# --------------------------------------------------------------------------

VIEW_WIDTH = 25
VIEW_HEIGHT = 13


def _view(across: float, up: float) -> list[str]:
    """One orthographic view of the sphere, with the point marked.

    Twice as wide as tall, because a terminal cell is about twice as tall as it
    is wide and a square grid would draw an egg.
    """
    rows = []
    for row in range(VIEW_HEIGHT):
        vertical = 1 - 2 * row / (VIEW_HEIGHT - 1)
        line = []
        for column in range(VIEW_WIDTH):
            horizontal = -1 + 2 * column / (VIEW_WIDTH - 1)
            if math.hypot(horizontal - across, vertical - up) < 0.11:
                line.append("*")
            elif abs(math.hypot(horizontal, vertical) - 1) < 0.06:
                line.append(".")
            elif abs(vertical) < 1e-9 and abs(horizontal) < 1:
                line.append("-")
            elif abs(horizontal) < 1e-9 and abs(vertical) < 1:
                line.append("|")
            else:
                line.append(" ")
        rows.append("".join(line))
    return rows


def _drawing(bloch_vector, angles) -> str:
    circuit = _state("h", "t")
    x, y, z = _vector(bloch_vector, circuit, "the drawn circuit")
    theta, phi = _angles(angles, (x, y, z), "the drawn circuit")

    side = _view(x, z)
    top = _view(x, y)
    lines = [
        "The state h then t, seen twice. The * is your own three numbers.",
        "",
        f"  {'side on: Z up, X right':<{VIEW_WIDTH + 8}}{'from above: Y up, X right'}",
    ]
    for left, right in zip(side, top, strict=True):
        lines.append(f"  {left:<{VIEW_WIDTH + 8}}{right}")
    lines += [
        "",
        "  |0> is the top of the left circle, |1> the bottom, |+> its right edge.",
        "",
        f"  vector   ({x:+.3f}, {y:+.3f}, {z:+.3f})",
        f"  theta    {theta:.4f} rad, {math.degrees(theta):.1f} degrees down from |0>",
        f"  phi      {phi:.4f} rad, {math.degrees(phi):.1f} degrees around from |+>",
        "",
        "Two angles are enough to place it, which is the whole claim: a state with",
        "four real numbers in it has only two that anything can measure.",
    ]
    return "\n".join(lines)


def _cardinal_table(bloch_vector, angles) -> str:
    rows = [f"{'state':>7}{'x':>8}{'y':>8}{'z':>8}{'theta':>9}{'phi':>9}   where"]
    for name, circuit, where in CARDINAL:
        x, y, z = _vector(bloch_vector, circuit, name)
        theta, phi = _angles(angles, (x, y, z), name)
        rows.append(f"{name:>7}{x:>8.3f}{y:>8.3f}{z:>8.3f}{theta:>9.3f}{phi:>9.3f}   {where}")
    rows += [
        "",
        "The two poles are the two outcomes your device can report. Everything",
        "else sits between them, and that is what superposition looks like as a",
        "position rather than as a pair of numbers.",
        "",
        "At the poles phi is meaningless: there is no shadow on the equator to",
        "measure an angle from, and atan2(0, 0) answers 0 for want of anything",
        "better. Every other row has a phi that genuinely locates it.",
    ]
    return "\n".join(rows)


def _phase_demo(bloch_vector) -> str:
    plain = _state("h", "t")
    shifted = plain.copy()
    shifted.global_phase += math.pi / 2

    before_state = np.asarray(Statevector(plain).data)
    after_state = np.asarray(Statevector(shifted).data)
    return (
        "The same circuit, with the whole state multiplied by i:\n\n"
        f"    amplitudes before   {_amplitudes(before_state)}\n"
        f"    amplitudes after    {_amplitudes(after_state)}\n"
        f"    both amplitudes changed\n\n"
        f"    Bloch vector before {_fmt(bloch_vector(plain))}\n"
        f"    Bloch vector after  {_fmt(bloch_vector(shifted))}\n"
        f"    the point did not move\n\n"
        "Exercise 07 asked you to accept that global phase is meaningless and that\n"
        "this is why the runner compares states with equiv rather than ==. This is\n"
        "that claim, shown rather than asserted: the sphere has no coordinate for\n"
        "the thing that changed."
    )


def _amplitudes(data) -> str:
    return "[" + ", ".join(f"{value.real:+.3f}{value.imag:+.3f}i" for value in data) + "]"


# One full turn, kept out of RY_ANGLES because the checks there compare the angle
# the sphere reports against the angle asked for, and the sphere reports 0 here.
# That is the entire point of the last row of the table below.
FULL_TURN = 2 * math.pi


def _half_angle_row(bloch_vector, angles, theta) -> str:
    circuit = QuantumCircuit(1)
    circuit.ry(theta, 0)
    amplitude = float(np.real(np.asarray(Statevector(circuit).data)[0]))
    return (
        f"{theta:>10.4f}{angles(bloch_vector(circuit))[0]:>12.4f}"
        f"{math.cos(theta / 2):>15.4f}{amplitude:>19.4f}"
    )


def _half_angle_table(bloch_vector, angles) -> str:
    rows = [f"{'ry angle':>10}{'theta':>12}{'cos(theta/2)':>15}{'amplitude of |0>':>19}"]
    rows += [_half_angle_row(bloch_vector, angles, theta) for theta in RY_ANGLES]
    rows += [
        "",
        "Column two is the full theta. Column three is the half that exercise 06",
        "warned you about, and column four confirms it is really the amplitude.",
        "",
        "Both are correct, and neither one explains the other. The half is already",
        "in the amplitudes: Ry(theta) is exp(-i * theta * Y / 2), and the 2 in that",
        "exponent is where it comes from. Drawing a sphere neither adds it nor",
        "removes it. One more row shows where the two part company:",
        "",
        _half_angle_row(bloch_vector, angles, FULL_TURN),
        "",
        "That is a full turn. The sphere says theta = 0, and so does everything you",
        "could measure here: same three components, same state. The amplitude reads",
        "-1 because the statevector is one representative of that state and this one",
        "carries a sign. At 4 * pi it carries the other.",
        "",
        "Which makes the factor of two unmeasurable on a lone qubit, for the reason",
        "the panel above this one gave. It becomes measurable when the turn is given",
        "to one branch of a superposition and not the other: a sign that was global",
        "to that branch is then relative between the two, and that is the same minus",
        "sign that separates |+> from |->.",
    ]
    return "\n".join(rows)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but its type is {type(value).__name__}.")
    return value
