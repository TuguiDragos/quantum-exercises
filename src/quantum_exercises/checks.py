"""Verification primitives shared by every exercise's check.py.

Two rules drive this module:

1. Compare objects, never text. States and operators go through ``.equiv``, which
   ignores global phase - the physically meaningless part a beginner should not
   be punished for.
2. Never assert exact measurement counts. Sampling is random. Assert either the
   support of the distribution or proportions inside a statistical tolerance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from scipy.stats import chi2

# Exercise tolerance. Looser than the Qiskit defaults (atol=1e-8, rtol=1e-5,
# both verified against Statevector.atol / .rtol) so that an honest answer
# assembled in a slightly different gate order still passes.
ATOL = 1e-6

# Two-sided z threshold for proportion checks. z=4 gives a ~6.3e-5 false-negative
# rate per assertion, low enough that CI does not flake.
Z_THRESHOLD = 4.0

# Significance level for the chi-square goodness-of-fit test.
CHI2_ALPHA = 0.001


class CheckFailed(Exception):
    """Raised when a learner's answer is wrong. The message is shown verbatim."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


@dataclass
class Artifact:
    """Something to render after a passing check, so every exercise ends in a result.

    ``payload`` must be JSON-serializable: it crosses a process boundary.
    """

    kind: str  # "counts" | "matrix" | "statevector" | "text"
    caption: str
    payload: Any
    meta: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Serialization helpers (results travel to the parent process as JSON)
# --------------------------------------------------------------------------


def _c(z: complex) -> list[float]:
    return [float(np.real(z)), float(np.imag(z))]


def statevector_artifact(sv: Statevector, caption: str = "Your state") -> Artifact:
    data = np.asarray(sv.data)
    return Artifact(
        kind="statevector",
        caption=caption,
        payload=[_c(z) for z in data],
        meta={"num_qubits": int(sv.num_qubits)},
    )


def matrix_artifact(op: Operator, caption: str = "Your operator") -> Artifact:
    data = np.asarray(op.data)
    return Artifact(
        kind="matrix",
        caption=caption,
        payload=[[_c(z) for z in row] for row in data],
    )


def counts_artifact(counts: dict[str, int], caption: str = "Measurement counts") -> Artifact:
    return Artifact(
        kind="counts",
        caption=caption,
        payload={str(k): int(v) for k, v in counts.items()},
    )


def text_artifact(text: str, caption: str = "") -> Artifact:
    return Artifact(kind="text", caption=caption, payload=str(text))


# --------------------------------------------------------------------------
# Fetching the learner's work out of their module
# --------------------------------------------------------------------------


def require(
    mod: ModuleType, name: str, expected_type: type | tuple[type, ...] | None = None
) -> Any:
    """Pull a module-level name out of exercise.py with a teaching error if absent."""
    if not hasattr(mod, name):
        defined = sorted(n for n in vars(mod) if not n.startswith("_"))
        raise CheckFailed(
            f"This exercise expects a variable named `{name}` at the top level of exercise.py.",
            detail=f"Names you did define: {', '.join(defined) or '(none)'}",
        )
    value = getattr(mod, name)
    if value is None:
        raise CheckFailed(
            f"`{name}` is still None. Replace the placeholder with your answer.",
        )
    if expected_type is not None and not isinstance(value, expected_type):
        want = (
            expected_type.__name__
            if isinstance(expected_type, type)
            else " or ".join(t.__name__ for t in expected_type)
        )
        raise CheckFailed(
            f"`{name}` should be a {want}, but its type is {type(value).__name__}.",
        )
    return value


def require_circuit(mod: ModuleType, name: str = "qc") -> QuantumCircuit:
    return require(mod, name, QuantumCircuit)


# --------------------------------------------------------------------------
# State and operator checks
# --------------------------------------------------------------------------


def as_statevector(source: QuantumCircuit | Statevector) -> Statevector:
    """Build a Statevector, tolerating a circuit that already has measurements.

    Statevector(qc) raises QiskitError on any classical-bit instruction, so final
    measurements are stripped first. Verified against Qiskit 2.5.2.
    """
    if isinstance(source, Statevector):
        return source
    if not isinstance(source, QuantumCircuit):
        raise CheckFailed(f"Expected a QuantumCircuit or Statevector, got {type(source).__name__}.")

    stripped = source.remove_final_measurements(inplace=False)
    # remove_final_measurements returns None when inplace=True; guard the other path.
    circuit = source if stripped is None else stripped
    try:
        return Statevector(circuit)
    except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
        raise CheckFailed(
            "Your circuit cannot be turned into a statevector.",
            detail=(
                "This usually means a measurement sits in the middle of the circuit rather "
                f"than at the end, or the circuit contains a reset. Underlying error: {exc}"
            ),
        ) from exc


def as_operator(source: QuantumCircuit | Operator) -> Operator:
    if isinstance(source, Operator):
        return source
    if not isinstance(source, QuantumCircuit):
        raise CheckFailed(f"Expected a QuantumCircuit or Operator, got {type(source).__name__}.")
    try:
        return Operator(source)
    except Exception as exc:  # noqa: BLE001 - re-raised as a teaching message
        raise CheckFailed(
            "Your circuit has no matrix representation.",
            detail=(
                "Measurement is not a reversible operation, so a circuit containing one has no "
                f"unitary matrix. Remove the measurement for this exercise. Underlying error: {exc}"
            ),
        ) from exc


def _coerce_target_state(target: QuantumCircuit | Statevector | np.ndarray) -> Statevector:
    if isinstance(target, Statevector):
        return target
    if isinstance(target, QuantumCircuit):
        return as_statevector(target)
    return Statevector(np.asarray(target))


def _coerce_target_operator(target: QuantumCircuit | Operator | np.ndarray) -> Operator:
    if isinstance(target, Operator):
        return target
    # A QuantumCircuit must go through Operator(), never numpy: np.asarray on a
    # circuit iterates its instructions and raises on the ragged result.
    if isinstance(target, QuantumCircuit):
        return as_operator(target)
    return Operator(np.asarray(target))


def assert_state_equiv(
    actual: QuantumCircuit | Statevector,
    target: QuantumCircuit | Statevector | np.ndarray,
    *,
    atol: float = ATOL,
    message: str | None = None,
) -> Statevector:
    """Compare states up to global phase."""
    sv = as_statevector(actual)
    target_sv = _coerce_target_state(target)

    if sv.dim != target_sv.dim:
        raise CheckFailed(
            f"Wrong number of qubits: your state has {sv.num_qubits}, "
            f"the target has {target_sv.num_qubits}."
        )

    if not sv.equiv(target_sv, atol=atol):
        raise CheckFailed(
            message or "Your state is not the target state.",
            detail=(
                f"Your probabilities:   {_fmt_probs(sv)}\n"
                f"Target probabilities: {_fmt_probs(target_sv)}\n"
                "Note: global phase is ignored, so a phase difference is not the problem here."
            ),
        )
    return sv


def assert_operator_equiv(
    actual: QuantumCircuit | Operator,
    target: QuantumCircuit | Operator | np.ndarray,
    *,
    atol: float = ATOL,
    message: str | None = None,
) -> Operator:
    """Compare operators up to global phase."""
    op = as_operator(actual)
    target_op = _coerce_target_operator(target)

    if op.dim != target_op.dim:
        raise CheckFailed(
            f"Wrong dimensions: your operator is {op.dim}, the target is {target_op.dim}."
        )

    if not op.equiv(target_op, atol=atol):
        raise CheckFailed(
            message or "Your circuit does not implement the target operation.",
            detail=(
                "Global phase is ignored, so that is not the difference.\n"
                "If the matrix looks transposed or the qubits look swapped, check tensor order: "
                "Qiskit is little-endian, qubit 0 is the rightmost bit."
            ),
        )
    return op


def assert_unitary(actual: QuantumCircuit | Operator, *, message: str | None = None) -> Operator:
    op = as_operator(actual)
    if not op.is_unitary():
        raise CheckFailed(
            message or "Your operator is not unitary, so it is not a valid quantum evolution."
        )
    return op


def _fmt_probs(sv: Statevector, limit: int = 8) -> str:
    probs = sv.probabilities_dict()
    items = sorted(probs.items(), key=lambda kv: -kv[1])[:limit]
    return "{" + ", ".join(f"'{k}': {v:.4f}" for k, v in items) + "}"


# --------------------------------------------------------------------------
# Measurement-count checks
# --------------------------------------------------------------------------


def assert_counts_support(
    counts: dict[str, int],
    expected_keys: set[str],
    *,
    message: str | None = None,
) -> None:
    """Assert exactly which outcomes appear, ignoring how often. Noise-free only.

    Use this when the physics forbids an outcome outright, not on hardware, where
    noise puts a few shots almost anywhere.
    """
    seen = {k for k, v in counts.items() if v > 0}
    unexpected = seen - expected_keys
    missing = expected_keys - seen

    if unexpected or missing:
        parts = []
        if unexpected:
            parts.append(f"outcomes that should be impossible: {sorted(unexpected)}")
        if missing:
            parts.append(f"outcomes that should appear but did not: {sorted(missing)}")
        raise CheckFailed(
            message or "The set of measured outcomes is wrong.",
            detail=(
                f"Expected exactly {sorted(expected_keys)}.\n"
                f"You got {sorted(seen)}.\n" + "; ".join(parts)
            ),
        )


def assert_counts_close(
    counts: dict[str, int],
    expected_probs: dict[str, float],
    *,
    z: float = Z_THRESHOLD,
    message: str | None = None,
) -> None:
    """Per-outcome proportion test against the binomial standard error.

    SE = sqrt(p(1-p)/N); an outcome passes when |k/N - p| < z * SE.
    """
    shots = sum(counts.values())
    if shots <= 0:
        raise CheckFailed("No shots were recorded, so there is nothing to compare.")

    total_p = sum(expected_probs.values())
    if not math.isclose(total_p, 1.0, abs_tol=1e-6):
        raise CheckFailed(
            f"Your predicted probabilities sum to {total_p:.6f}, not 1.0.",
            detail="Probabilities over all possible outcomes must add up to exactly 1.",
        )

    failures: list[str] = []
    for outcome, p in expected_probs.items():
        k = counts.get(outcome, 0)
        observed = k / shots

        if p == 0.0:
            if k > 0:
                failures.append(f"'{outcome}': predicted impossible, but measured {k} times")
            continue
        if p == 1.0:
            if k != shots:
                failures.append(f"'{outcome}': predicted certain, but measured {k}/{shots}")
            continue

        se = math.sqrt(p * (1.0 - p) / shots)
        deviation = abs(observed - p)
        if deviation > z * se:
            sigma = deviation / se
            failures.append(
                f"'{outcome}': predicted {p:.4f}, measured {observed:.4f} "
                f"({k}/{shots}), off by {sigma:.1f} sigma"
            )

    # An outcome the learner never predicted still has to be accounted for.
    for outcome, k in counts.items():
        if k > 0 and outcome not in expected_probs:
            failures.append(f"'{outcome}': measured {k} times but you predicted nothing for it")

    if failures:
        raise CheckFailed(
            message or "Your predicted probabilities do not match what was measured.",
            detail=(
                f"Tolerance is {z:.0f} standard errors over {shots} shots.\n"
                + "\n".join(f"  - {f}" for f in failures)
            ),
        )


def chi_square_counts(
    counts: dict[str, int],
    expected_probs: dict[str, float],
    *,
    alpha: float = CHI2_ALPHA,
) -> tuple[float, float, int]:
    """Goodness-of-fit over the whole distribution. Returns (statistic, critical, dof)."""
    shots = sum(counts.values())
    if shots <= 0:
        raise CheckFailed("No shots were recorded, so there is nothing to compare.")

    outcomes = sorted(set(expected_probs) | {k for k, v in counts.items() if v > 0})
    statistic = 0.0
    for outcome in outcomes:
        expected = expected_probs.get(outcome, 0.0) * shots
        observed = counts.get(outcome, 0)
        if expected <= 0:
            if observed > 0:
                # An outcome with zero predicted probability that still occurred is
                # infinitely surprising under this model; report it as a hard failure.
                return float("inf"), 0.0, max(len(outcomes) - 1, 1)
            continue
        statistic += (observed - expected) ** 2 / expected

    dof = max(len(outcomes) - 1, 1)
    critical = float(chi2.ppf(1.0 - alpha, dof))
    return statistic, critical, dof


def assert_counts_distribution(
    counts: dict[str, int],
    expected_probs: dict[str, float],
    *,
    alpha: float = CHI2_ALPHA,
    message: str | None = None,
) -> None:
    """Whole-distribution check, better than per-outcome when there are many outcomes."""
    statistic, critical, dof = chi_square_counts(counts, expected_probs, alpha=alpha)
    if statistic > critical:
        raise CheckFailed(
            message or "The measured distribution does not match the expected one.",
            detail=(
                f"chi-square = {statistic:.2f}, critical value = {critical:.2f} "
                f"at alpha={alpha} with {dof} degrees of freedom.\n"
                f"Measured: {dict(sorted(counts.items()))}\n"
                f"Expected: { {k: round(v, 4) for k, v in sorted(expected_probs.items())} }"
            ),
        )


def assert_shots(counts: dict[str, int], expected: int) -> None:
    total = sum(counts.values())
    if total != expected:
        raise CheckFailed(
            f"The counts add up to {total}, but this exercise asks for {expected} shots.",
            detail=(
                "Every shot produces exactly one outcome, so the values must sum to the shot "
                "count. A total that is lower means the run used fewer shots than it was asked "
                "for, which is what leaving `shots=` off does."
            ),
        )


__all__ = [
    "ATOL",
    "CHI2_ALPHA",
    "Z_THRESHOLD",
    "Artifact",
    "CheckFailed",
    "as_operator",
    "as_statevector",
    "assert_counts_close",
    "assert_counts_distribution",
    "assert_counts_support",
    "assert_operator_equiv",
    "assert_shots",
    "assert_state_equiv",
    "assert_unitary",
    "chi_square_counts",
    "counts_artifact",
    "matrix_artifact",
    "require",
    "require_circuit",
    "statevector_artifact",
    "text_artifact",
]
