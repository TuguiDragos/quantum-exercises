"""Verification for exercise 20."""

import contextlib
import itertools
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector

from quantum_exercises.checks import CheckFailed, require, text_artifact

ATOL = 1e-6

# The angles that reach the quantum maximum. Verified: S = 2*sqrt(2) exactly.
A0, A1 = 0.0, math.pi / 2
B0, B1 = math.pi / 4, -math.pi / 4

TSIRELSON = 2.0 * math.sqrt(2.0)

# Deliberately asymmetric, so a joint_observable that swaps Alice and Bob is
# caught here. The Bell state itself cannot tell the two apart.
ORDER_CASES = [(0.3, 1.1), (0.0, math.pi / 2), (-0.7, 0.2)]

# Pairs for the correlation check. E(a, b) = cos(a - b) for this state.
CORRELATION_CASES = [(0.0, 0.0), (A0, B0), (A1, B1), (0.4, -1.3), (2.0, 2.0)]

# A second set of angles for chsh, deliberately nowhere near the optimum. S comes
# out at nothing memorable there, which is the point: see _check_chsh_off_optimum.
OFF_OPTIMUM = (0.3, 1.4, 0.9, -0.2)


def check(mod):
    joint_observable = _callable(mod, "joint_observable")
    correlation = _callable(mod, "correlation")
    chsh = _callable(mod, "chsh")

    _check_order(joint_observable)
    _check_correlation(correlation)
    _check_it_is_computed(mod, correlation)
    _check_chsh(chsh, correlation)

    return [text_artifact(_summary(correlation, chsh), caption="S, against the classical ceiling")]


def _single(theta):
    return SparsePauliOp(["Z", "X"], coeffs=[math.cos(theta), math.sin(theta)])


def _check_order(joint_observable):
    for alice, bob in ORDER_CASES:
        value = joint_observable(alice, bob)
        if not isinstance(value, SparsePauliOp):
            raise CheckFailed(
                f"joint_observable({alice:.4f}, {bob:.4f}) returned a "
                f"{type(value).__name__}, expected a SparsePauliOp.",
                detail="A function with no `return` gives None.",
            )
        if value.num_qubits != 2:
            raise CheckFailed(
                f"joint_observable() gave a {value.num_qubits}-qubit observable, expected 2.",
                detail="One single-qubit observable for Alice and one for Bob, combined.",
            )

        # np.kron puts its first argument on the higher-numbered qubit, matching
        # Qiskit's little-endian labels, so Bob comes first here.
        want = np.kron(_single(bob).to_matrix(), _single(alice).to_matrix())
        if np.allclose(value.to_matrix(), want, atol=ATOL):
            continue

        swapped = np.kron(_single(alice).to_matrix(), _single(bob).to_matrix())
        if np.allclose(value.to_matrix(), swapped, atol=ATOL):
            raise CheckFailed(
                "joint_observable() has Alice and Bob the wrong way round.",
                detail=(
                    "Alice measures qubit 0, and qubit 0 is the rightmost slot, the same "
                    "rule as the counts strings in exercise 11. `tensor` puts its argument "
                    "on the lower-numbered qubit, so Alice is the one you pass in:\n"
                    "  bob_side.tensor(alice_side)\n"
                    "The Bell state is symmetric, so this mistake does not change S. It "
                    "would change every result on a state that is not."
                ),
            )
        raise CheckFailed(
            f"joint_observable({alice:.4f}, {bob:.4f}) is not the observable it should be.",
            detail=(
                "Expected the tensor product of observable_at(alice_angle) on qubit 0 and "
                "observable_at(bob_angle) on qubit 1."
            ),
        )


def _check_correlation(correlation):
    for alice, bob in CORRELATION_CASES:
        value = _number(correlation, (alice, bob), f"correlation({alice:.4f}, {bob:.4f})")
        want = math.cos(alice - bob)
        if not math.isclose(value, want, abs_tol=1e-4):
            raise CheckFailed(
                f"correlation({alice:.4f}, {bob:.4f}) gave {value:+.6f}, expected {want:+.6f}.",
                detail=(
                    "For the Bell state, E(a, b) works out to cos(a - b) exactly.\n"
                    "Run the joint observable on bell() through the Estimator, the same "
                    "call as exercise 17. If every answer is 1.0, the observable is "
                    "probably not being passed through."
                ),
            )


# The angles the substitutions below are put at. Nothing turns on the pair beyond
# every replacement below giving something clearly apart from cos(a - b) there.
SUBSTITUTION_AT = (0.3, 1.1)
SUBSTITUTION_LABEL = f"correlation({SUBSTITUTION_AT[0]:.4f}, {SUBSTITUTION_AT[1]:.4f})"

# The three pieces this exercise hands the reader, and something else of the same
# kind to put in their place. |00> is a product state, and ZZ is exactly 1 on the
# Bell state, so any of them being used moves the answer well away from cos(a - b).
SUBSTITUTIONS = [
    ("bell", lambda: QuantumCircuit(2)),
    ("joint_observable", lambda *_: SparsePauliOp("ZZ")),
    ("observable_at", lambda *_: SparsePauliOp("Z")),
]


@contextlib.contextmanager
def _swapped(mod, name, replacement):
    """Put something else in the module under that name, then put the real one back."""
    original = getattr(mod, name)
    setattr(mod, name, replacement)
    try:
        yield
    finally:
        setattr(mod, name, original)


def _follows(mod, correlation, name, replacement, baseline):
    """Whether correlation's answer moves when the module's `name` does."""
    with _swapped(mod, name, replacement):
        try:
            moved = _number(correlation, SUBSTITUTION_AT, SUBSTITUTION_LABEL)
        except Exception:
            # It stopped returning that number at all, which is still a dependency.
            return True
    return not math.isclose(moved, baseline, abs_tol=1e-4)


def _kept_states(mod):
    """Module-level circuits and statevectors, which is `bell()` saved off to one side.

    Naming `bell` is not enough on its own: `_BELL = bell()` at the top of the file
    binds the circuit under some other name, and rebinding the function afterwards
    cannot reach it. These are found by type rather than by name, so whatever the
    reader called it is covered.
    """
    swaps = []
    for name, value in vars(mod).items():
        if isinstance(value, QuantumCircuit) and value.num_qubits == 2:
            swaps.append((name, QuantumCircuit(2)))
        elif isinstance(value, Statevector) and value.num_qubits == 2:
            swaps.append((name, Statevector.from_label("00")))
    return swaps


def _check_it_is_computed(mod, correlation):
    """Move a piece underneath correlation() and see whether the answer follows.

    cos(a - b) is the right answer for the Bell state, so writing it out directly
    passes every comparison above without computing anything, and no property of
    the returned number can show that. The input has to move instead.

    Several pieces are moved rather than one, and following any of them is enough.
    Swapping only the state punished a correct answer: `bell()` returns a constant,
    so caching it once at the top of the file is an ordinary thing to write, and
    such a correlation cannot see the swap however honestly it computes. Hence the
    observable as well, reached whether it is built through joint_observable or
    inline from observable_at, and hence a saved circuit being swapped by type
    rather than only by the name `bell`.

    What this establishes is narrower than it looks, and worth saying plainly: that
    the answer is a function of something this exercise handed over, not that an
    Estimator was ever called. Together with the five angle pairs checked above it
    means a number that both equals cos(a - b) and moves with the state or the
    observable it was built from. Nothing here can, or tries to, dictate which
    route was taken to it.
    """
    baseline = _number(correlation, SUBSTITUTION_AT, SUBSTITUTION_LABEL)

    for name, replacement in [*SUBSTITUTIONS, *_kept_states(mod)]:
        if hasattr(mod, name) and _follows(mod, correlation, name, replacement, baseline):
            return

    raise CheckFailed(
        "correlation() gives the same answer whatever it is handed.",
        detail=(
            f"It answered {baseline:+.6f} on the Bell state, and the same on |00>, and the "
            "same again with a different observable entirely. A value that does not move "
            "when the state and the observable both move was not computed from them.\n"
            "cos(a - b) is the right answer here, and writing it out returns the right number "
            "without measuring anything. Build the observable, hand it and bell() to the "
            "Estimator, and read what comes back."
        ),
    )


def _check_chsh(chsh, correlation):
    value = _number(chsh, (A0, A1, B0, B1), "chsh at the optimal angles")

    if math.isclose(value, TSIRELSON, abs_tol=1e-4):
        _check_chsh_off_optimum(chsh)
        return

    # At these angles every correlation is +-cos(pi/4), so across all sixteen ways of
    # signing the four terms |S| can only come out as 0, sqrt(2) or 2*sqrt(2). Those
    # are the two wrong values worth naming; 2.0 is not reachable, so there is no
    # branch for it.
    if math.isclose(abs(value), 0.0, abs_tol=1e-4):
        raise CheckFailed(
            f"chsh() at the optimal angles gave {value:+.6f}, expected {TSIRELSON:.6f}.",
            detail=(
                "Zero means the minus is on the wrong term. It belongs on E(a1, b1), the "
                "one where both parties used their second angle. Anywhere else and the four "
                "terms cancel in pairs instead of reinforcing."
            ),
        )
    if math.isclose(abs(value), math.sqrt(2.0), abs_tol=1e-4):
        raise CheckFailed(
            f"chsh() at the optimal angles gave {value:+.6f}, expected {TSIRELSON:.6f}.",
            detail=(
                "sqrt(2) is what you get with all four terms added, or with two of them "
                "subtracted. Exactly one term is subtracted, and it is the last."
            ),
        )
    raise CheckFailed(
        f"chsh() at the optimal angles gave {value:+.6f}, expected {TSIRELSON:.6f}.",
        detail=(
            "S = E(a0, b0) + E(a0, b1) + E(a1, b0) - E(a1, b1).\n"
            f"The four correlations at these angles are "
            f"{correlation(A0, B0):+.4f}, {correlation(A0, B1):+.4f}, "
            f"{correlation(A1, B0):+.4f}, {correlation(A1, B1):+.4f}.\n"
            "Check the argument order too: chsh(a0, a1, b0, b1) takes Alice's two angles "
            "first, then Bob's."
        ),
    )


def _check_chsh_off_optimum(chsh):
    """One angle set cannot tell the arithmetic apart from the answer.

    2*sqrt(2) is the number the exercise puts in front of the reader, so a chsh
    that ignores its arguments and returns it passed at the optimal angles alone.
    Here S is nothing in particular, which only the real combination produces.
    """
    a0, a1, b0, b1 = OFF_OPTIMUM
    want = math.cos(a0 - b0) + math.cos(a0 - b1) + math.cos(a1 - b0) - math.cos(a1 - b1)
    value = _number(chsh, OFF_OPTIMUM, f"chsh({a0}, {a1}, {b0}, {b1})")

    if math.isclose(value, want, abs_tol=1e-4):
        return

    raise CheckFailed(
        f"chsh({a0}, {a1}, {b0}, {b1}) gave {value:+.6f}, expected {want:+.6f}.",
        detail=(
            "The optimal angles came out right, so the combination itself is fine. "
            "This is a different set of angles, where S is nothing memorable.\n"
            "chsh() has to work S out from the four angles it is handed, rather than "
            "from the ones in the exercise text. 2*sqrt(2) is only the answer for those."
        ),
    )


def _number(function, args, label):
    value = function(*args)
    if isinstance(value, bool) or not isinstance(value, (int, float, np.floating, np.integer)):
        raise CheckFailed(
            f"{label} returned {value!r}, which is not a number.",
            detail="A function with no `return` gives None.",
        )
    return float(value)


def _best_classical():
    """The best any pre-decided set of answers can manage. Sixteen of them exist."""
    return max(
        abs(a0 * b0 + a0 * b1 + a1 * b0 - a1 * b1)
        for a0, a1, b0, b1 in itertools.product([-1, 1], repeat=4)
    )


def _summary(correlation, chsh):
    s = chsh(A0, A1, B0, B1)
    lines = [
        "Alice measures at a0 = 0 and a1 = pi/2, Bob at b0 = pi/4 and b1 = -pi/4.",
        "",
        f"  E(a0, b0) = {correlation(A0, B0):+.4f}",
        f"  E(a0, b1) = {correlation(A0, B1):+.4f}",
        f"  E(a1, b0) = {correlation(A1, B0):+.4f}",
        f"  E(a1, b1) = {correlation(A1, B1):+.4f}   (this one is subtracted)",
        "",
        f"  S = {s:.6f}",
        "",
        f"  best of all 16 pre-decided strategies : {_best_classical():.6f}",
        f"  what you just computed               : {s:.6f}",
        f"  the quantum ceiling, 2 * sqrt(2)     : {TSIRELSON:.6f}",
        "",
        "The envelopes cannot reach what you computed. That is the whole argument,",
        "and it is why exercise 11 was careful not to claim it had already been made.",
    ]
    return "\n".join(lines)


def _callable(mod, name):
    value = require(mod, name)
    if not callable(value):
        raise CheckFailed(f"`{name}` should be a function, but its type is {type(value).__name__}.")
    return value
