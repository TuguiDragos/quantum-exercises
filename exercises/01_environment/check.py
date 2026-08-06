"""Verification for exercise 01."""

from importlib.metadata import version
from pathlib import Path

import qiskit

from quantum_exercises.checks import CheckFailed, require, text_artifact


def check(mod):
    reported = require(mod, "qiskit_version", str)
    actual = qiskit.__version__

    _require_asking_the_package(mod)

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


def _require_asking_the_package(mod) -> None:
    """Typing the right number in also matches, and stops being right next sync.

    The exercise is about asking the package, so read the file and insist on it.
    """
    source_file = getattr(mod, "__file__", None)
    if not source_file:
        return
    try:
        source = Path(source_file).read_text(encoding="utf-8")
    except OSError:
        return

    if "__version__" in source or "importlib" in source:
        return

    raise CheckFailed(
        "The version is written in by hand rather than read from the package.",
        detail=(
            "A literal is right until the next `uv sync` and then quietly wrong, which is the "
            "exact failure this exercise is about. Ask qiskit what version it is."
        ),
    )


def _safe_version(package: str) -> str:
    try:
        return version(package)
    except Exception:  # noqa: BLE001 - a missing optional package is not a failure here
        return "not installed"
