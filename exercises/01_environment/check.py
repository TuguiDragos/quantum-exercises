"""Verification for exercise 01."""

from importlib.metadata import version

import qiskit

from quantum_exercises.checks import CheckFailed, require, text_artifact


def check(mod):
    reported = require(mod, "qiskit_version", str)
    actual = qiskit.__version__

    if reported != actual:
        raise CheckFailed(
            f"You reported Qiskit {reported!r}, but this environment has {actual!r}.",
            detail=(
                "Read the value from the package rather than typing it in, so the answer "
                "stays true after the next `uv sync`."
            ),
        )

    return text_artifact(
        f"Qiskit SDK      {actual}\n"
        f"qiskit-aer      {_safe_version('qiskit-aer')}\n"
        f"IBM Runtime     {_safe_version('qiskit-ibm-runtime')}",
        caption="Your quantum stack",
    )


def _safe_version(package: str) -> str:
    try:
        return version(package)
    except Exception:  # noqa: BLE001 - a missing optional package is not a failure here
        return "not installed"
