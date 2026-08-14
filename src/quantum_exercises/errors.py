"""Translate Python and Qiskit exceptions into the language of the domain.

Every pattern here was produced by actually triggering the error against the
pinned stack, not guessed from memory. When you add a rule, trigger the error
first and paste the real message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quantum_exercises import invocation

ISSUES_URL = "https://github.com/TuguiDragos/quantum-exercises/issues"

# Shown whenever no rule matched. The rules below only cover mistakes that could
# be anticipated, and the long tail is exactly the part that cannot be. Asking
# for the ones we missed is the only way this file improves.
UNTRANSLATED_HINT = (
    "This error does not have a plain-language explanation yet. If it left you stuck, "
    f"paste it into an issue at {ISSUES_URL} and it will get one."
)


@dataclass
class Translation:
    """A beginner-readable replacement for a raw traceback."""

    message: str
    hint: str | None = None


# Symbols removed from the qiskit namespace, with what replaced them.
_REMOVED_FROM_QISKIT = {
    "execute": (
        "`execute()` was removed in Qiskit 1.0.",
        "Use a primitive instead: `StatevectorSampler().run([qc], shots=1024)` for local work, "
        "or `transpile(qc, backend)` followed by `backend.run(...)` for the low-level path.",
    ),
    "Aer": (
        "`Aer` no longer lives in the `qiskit` package.",
        "It moved to its own package: `from qiskit_aer import AerSimulator`.",
    ),
    "IBMQ": (
        "`IBMQ` was removed. It was replaced by the runtime service.",
        "Use `from qiskit_ibm_runtime import QiskitRuntimeService`, then "
        "`service = QiskitRuntimeService()`.",
    ),
    "BasicAer": (
        "`BasicAer` was renamed.",
        "Use `from qiskit.providers.basic_provider import BasicSimulator`, or better, "
        "`from qiskit.primitives import StatevectorSampler`.",
    ),
}

# Modules deleted or relocated between Qiskit 0.x and 2.x.
_REMOVED_MODULES = {
    "qiskit.opflow": (
        "`qiskit.opflow` was removed in Qiskit 1.0.",
        "Its job is done by `qiskit.quantum_info` now: `SparsePauliOp`, `Operator`, `Statevector`.",
    ),
    "qiskit.tools": (
        "`qiskit.tools` was removed in Qiskit 1.0.",
        "`job_monitor` is gone; a runtime job exposes `job.status()` and `job.result()` directly.",
    ),
    "qiskit.providers.aer": (
        "`qiskit.providers.aer` was replaced by a standalone package.",
        "Use `from qiskit_aer import AerSimulator`.",
    ),
}

# Names people reach for that QuantumCircuit does not have, and what they meant.
# Module level like the tables above, so a test can walk it: a mapping built
# inside the rule reads as covered the moment the rule runs once.
_CIRCUIT_TYPOS = {
    "measure_al": "measure_all",
    "measureall": "measure_all",
    "meausre_all": "measure_all",
    "hadamard": "h",
    "cnot": "cx",
    "toffoli": "ccx",
}

# Third-party imports whose absence has a specific, actionable fix.
_MISSING_PACKAGES = {
    "matplotlib": (
        "matplotlib is not installed, so drawing is unavailable.",
        "Plain `qiskit` does not ship plotting. Install the extra: "
        "`uv add 'qiskit[visualization]'`. Meanwhile `qc.draw()` with no argument "
        "prints a text diagram and always works.",
    ),
    "pylatexenc": (
        "pylatexenc is not installed, so LaTeX-style gate labels are unavailable.",
        "It comes with `uv add 'qiskit[visualization]'`.",
    ),
    "qiskit_aer": (
        "qiskit-aer is not installed.",
        "Aer is a separate package from the Qiskit SDK: `uv add qiskit-aer`.",
    ),
    "qiskit_ibm_runtime": (
        "qiskit-ibm-runtime is not installed.",
        "It is the package that talks to IBM hardware: `uv add qiskit-ibm-runtime`.",
    ),
}


def translate(exc: BaseException) -> Translation | None:
    """Return a domain-language rewrite of ``exc``, or None to keep the raw error."""
    for rule in (
        _syntax,
        _import_from_qiskit,
        _qiskit_attribute,
        _missing_module,
        _circuit_index,
        _duplicate_bits,
        _classical_bits_in_conversion,
        _mid_circuit_measurement,
        _primitive_pub,
        _v1_result_api,
        _databin_field,
        _circuit_attribute,
        _account_problem,
        _name_error,
    ):
        result = rule(exc)
        if result is not None:
            return result
    return None


def _syntax(exc: BaseException) -> Translation | None:
    if not isinstance(exc, SyntaxError):
        return None
    where = f"line {exc.lineno}" if exc.lineno else "somewhere in the file"
    if isinstance(exc, IndentationError):
        return Translation(
            f"Python could not parse your file: the indentation is off at {where}.",
            "Python uses indentation the way other languages use braces. Every line inside a "
            "block needs the same number of leading spaces.",
        )
    return Translation(
        f"Python could not parse your file: there is a syntax error at {where}.",
        f"The parser said: {exc.msg}. A missing closing bracket or colon on the line above "
        "is the usual cause.",
    )


def _import_from_qiskit(exc: BaseException) -> Translation | None:
    if not isinstance(exc, ImportError) or isinstance(exc, ModuleNotFoundError):
        return None
    # Real message: cannot import name 'execute' from 'qiskit' (/path/__init__.py)
    match = re.search(r"cannot import name '(\w+)' from '([\w.]+)'", str(exc))
    if not match:
        return None
    symbol, module = match.group(1), match.group(2)
    if module == "qiskit" and symbol in _REMOVED_FROM_QISKIT:
        message, hint = _REMOVED_FROM_QISKIT[symbol]
        return Translation(message, hint)
    return Translation(
        f"`{symbol}` does not exist in `{module}` on this version of Qiskit.",
        "This is usually code written for Qiskit 0.x. Check the migration guide for the "
        "current name.",
    )


def _qiskit_attribute(exc: BaseException) -> Translation | None:
    """The other half of the 0.x import: `import qiskit` then `qiskit.execute(...)`.

    Real message: module 'qiskit' has no attribute 'execute'. The `from qiskit
    import execute` spelling raises ImportError and is handled above; this one
    raises AttributeError and used to fall through untranslated, even though it is
    the more common form in old tutorials.
    """
    if not isinstance(exc, AttributeError):
        return None
    match = re.search(r"module 'qiskit' has no attribute '(\w+)'", str(exc))
    if not match:
        return None
    symbol = match.group(1)
    if symbol in _REMOVED_FROM_QISKIT:
        message, hint = _REMOVED_FROM_QISKIT[symbol]
        return Translation(message, hint)
    return Translation(
        f"`qiskit.{symbol}` does not exist on this version of Qiskit.",
        "This is usually code written for Qiskit 0.x. Check the migration guide for the "
        "current name.",
    )


def _missing_module(exc: BaseException) -> Translation | None:
    if not isinstance(exc, ModuleNotFoundError):
        return None
    name = exc.name or ""
    if name in _REMOVED_MODULES:
        message, hint = _REMOVED_MODULES[name]
        return Translation(message, hint)
    root = name.split(".")[0]
    # Only claim the package is absent when the package itself is what failed.
    # Python names the first component it could not find, so `name == root` means
    # the install is missing, while a longer name means the package imported fine
    # and a submodule under it did not. Saying "matplotlib is not installed" to
    # someone who typed `matplotlib.pyploy` sends them to reinstall what they have.
    if root in _MISSING_PACKAGES and name == root:
        message, hint = _MISSING_PACKAGES[root]
        return Translation(message, hint)
    if root in _MISSING_PACKAGES:
        return Translation(
            f"`{root}` is installed, but it has no submodule `{name.split('.', 1)[1]}`.",
            "That is a typo in the import rather than a missing package.",
        )
    if name.startswith("qiskit."):
        return Translation(
            f"`{name}` does not exist in Qiskit 2.x.",
            "This module was removed or moved. Code from before Qiskit 1.0 often imports it.",
        )
    return None


def _circuit_index(exc: BaseException) -> Translation | None:
    # Real message: 'Index 3 out of range for size 1.'
    match = re.search(r"Index (\d+) out of range for size (\d+)", str(exc))
    if not match:
        return None
    index, size = int(match.group(1)), int(match.group(2))
    if size == 0:
        # Qiskit words this identically for a qubit and for a classical bit, so the
        # rule cannot tell them apart. Lead with the common case, name the other.
        return Translation(
            f"You addressed index {index}, but the circuit has no wires of that kind at all.",
            "Usually this is a missing classical register: measurement needs somewhere to "
            "write its result, so build the circuit as `QuantumCircuit(n, n)`, or call "
            "`qc.measure_all()`, which adds one for you. If you meant a qubit, note that "
            "`QuantumCircuit()` with no arguments has none.",
        )
    return Translation(
        f"You referred to index {index}, but the circuit only has {size} "
        f"{'wire' if size == 1 else 'wires'} of that kind.",
        f"Indices start at 0, so the valid range here is 0 to {size - 1}.",
    )


def _duplicate_bits(exc: BaseException) -> Translation | None:
    if "duplicate bit arguments" not in str(exc):
        return None
    # Qiskit does not name the gate, and the same message covers ccx, so neither
    # does this: "two-qubit gate, use cx" is wrong advice half the time.
    return Translation(
        "A gate was given the same qubit more than once.",
        "`qc.cx(0, 0)` and `qc.ccx(0, 0, 1)` are not valid operations. Every qubit a gate "
        "acts on has to be a different one, for example `qc.cx(0, 1)`.",
    )


def _classical_bits_in_conversion(exc: BaseException) -> Translation | None:
    """Name the object the learner actually asked for.

    Verified against Qiskit 2.5.2: `Operator()` raises "Cannot apply operation with
    classical bits" (operator.py), while `Statevector()`, `DensityMatrix()` and the
    Pauli and Clifford paths raise "instruction". Exercise 08 is about `Operator`,
    so reporting a statevector problem there points at the wrong line entirely.
    """
    match = re.search(
        r"Cannot apply (instruction|operation) with classical bits", str(exc), re.IGNORECASE
    )
    if not match:
        return None
    if match.group(1).lower() == "operation":
        return Translation(
            "You cannot build a matrix for a circuit that contains a measurement.",
            "Measurement is not reversible, so a circuit containing one has no unitary "
            "matrix. Remove the measurement for this exercise, or strip it with "
            "`qc.remove_final_measurements(inplace=False)`.",
        )
    return Translation(
        "You cannot compute a statevector for a circuit that contains a measurement.",
        "Measurement collapses the state, so there is no single vector left to describe. "
        "For this exercise, build the circuit without measurement, or strip it with "
        "`qc.remove_final_measurements(inplace=False)`.",
    )


def _mid_circuit_measurement(exc: BaseException) -> Translation | None:
    # Real message: 'StatevectorSampler cannot handle mid-circuit measurements'
    if "mid-circuit measurement" not in str(exc):
        return None
    return Translation(
        "This sampler cannot run a circuit that measures partway through.",
        "A measurement followed by more gates is a mid-circuit measurement, and "
        "`StatevectorSampler` only handles measurements at the very end. Move the "
        "measurement last, or run it on `AerSimulator`, which does support them. That "
        "is what the dynamic circuits lab uses.",
    )


def _primitive_pub(exc: BaseException) -> Translation | None:
    if "invalid Sampler pub-like" not in str(exc) and "invalid Estimator pub-like" not in str(exc):
        return None
    return Translation(
        "The primitive was handed a circuit directly instead of a list.",
        "V2 primitives always take a list of jobs: write `sampler.run([qc], shots=1024)`, "
        "with the square brackets.",
    )


def _v1_result_api(exc: BaseException) -> Translation | None:
    # Real message: 'PrimitiveResult' object has no attribute 'get_counts'
    if not isinstance(exc, AttributeError):
        return None
    if "'PrimitiveResult' object has no attribute 'get_counts'" not in str(exc):
        return None
    return Translation(
        "`result.get_counts()` is the old V1 API and no longer exists.",
        "A V2 result is a list of per-circuit results. Reach the counts in three steps: "
        "`result[0]` picks your circuit, `.data` opens its classical registers, then "
        "`.meas.get_counts()` reads the register that `measure_all()` created.",
    )


def _databin_field(exc: BaseException) -> Translation | None:
    # Real message: 'DataBin' object has no attribute 'c'
    if not isinstance(exc, AttributeError):
        return None
    match = re.search(r"'DataBin' object has no attribute '(\w+)'", str(exc))
    if not match:
        return None
    return Translation(
        f"The result has no classical register called `{match.group(1)}`.",
        "The field is named after the register in your circuit. `qc.measure_all()` creates one "
        "called `meas`; an explicit `ClassicalRegister(2, 'name')` creates one called `name`. "
        "You can always list them with `list(result[0].data.keys())`. An empty list means the "
        "circuit had no measurement at all.",
    )


def _circuit_attribute(exc: BaseException) -> Translation | None:
    if not isinstance(exc, AttributeError):
        return None
    match = re.search(r"'QuantumCircuit' object has no attribute '(\w+)'", str(exc))
    if not match:
        return None
    attr = match.group(1)
    if attr in _CIRCUIT_TYPOS:
        return Translation(
            f"`QuantumCircuit` has no method `{attr}`.",
            f"You probably meant `qc.{_CIRCUIT_TYPOS[attr]}(...)`.",
        )
    return Translation(
        f"`QuantumCircuit` has no method `{attr}`.",
        "Gate methods are short and lowercase: `h`, `x`, `z`, `cx`, `ccx`, `rz`. "
        "Measurement is `measure(qubit, clbit)` or `measure_all()`.",
    )


def _account_problem(exc: BaseException) -> Translation | None:
    """Two ways an account fails, and they need different advice.

    Matched by class name rather than by import, so this module never depends on
    qiskit-ibm-runtime being installed.
    """
    name = type(exc).__name__
    if name == "AccountNotFoundError":
        return Translation(
            "No IBM Quantum account is saved on this machine.",
            f"Run `{invocation()} doctor` to see the setup steps. This exercise falls back to "
            "a local simulator, so you can still finish it without an account.",
        )
    if name == "InvalidAccountError":
        return Translation(
            "The saved IBM Quantum account is no longer accepted.",
            f"The file is there and well formed, which is why `{invocation()} doctor` reports "
            "it as saved: that check never contacts IBM. The key behind it has expired or been "
            f"revoked. Get a new one and run `{invocation()} doctor --save-account`, then "
            f"confirm with `{invocation()} doctor --online`.",
        )
    return None


def _name_error(exc: BaseException) -> Translation | None:
    if not isinstance(exc, NameError):
        return None
    match = re.search(r"name '(\w+)' is not defined", str(exc))
    if not match:
        return None
    name = match.group(1)
    if name in _REMOVED_FROM_QISKIT:
        message, hint = _REMOVED_FROM_QISKIT[name]
        return Translation(message, hint)
    return Translation(
        f"`{name}` is used before it is defined.",
        "Either it is a typo, or the import that provides it is missing from the top of the file.",
    )


__all__ = ["Translation", "translate"]
