"""Error translation, driven by exceptions that are genuinely raised.

Each test triggers the real error rather than constructing one by hand, so a
change in Qiskit's wording shows up here instead of silently disabling a rule.
"""

from __future__ import annotations

import pytest

from quantum_exercises.errors import translate


def _raised(source: str) -> BaseException:
    try:
        exec(compile(source, "<exercise>", "exec"), {})
    except BaseException as exc:  # noqa: BLE001 - capturing is the point
        return exc
    raise AssertionError(f"expected {source!r} to raise")


@pytest.mark.parametrize(
    ("source", "expected_in_message"),
    [
        ("from qiskit import execute", "`execute()` was removed"),
        ("from qiskit import Aer", "`Aer` no longer lives"),
        ("from qiskit import IBMQ", "`IBMQ` was removed"),
        ("from qiskit import BasicAer", "`BasicAer` was renamed"),
        ("import qiskit.opflow", "`qiskit.opflow` was removed"),
        ("from qiskit.tools.monitor import job_monitor", "`qiskit.tools` was removed"),
    ],
)
def test_removed_qiskit_api(source: str, expected_in_message: str) -> None:
    translation = translate(_raised(source))
    assert translation is not None
    assert expected_in_message in translation.message
    assert translation.hint


def test_mid_circuit_measurement_is_triggered_for_real() -> None:
    """The rule matches on Qiskit's own wording, so only Qiskit can confirm it.

    Tested by hand-built exception until now, which proves the rule reads the
    string it was given and nothing about the string still being that one.
    """
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorSampler\n"
            "qc = QuantumCircuit(1, 1)\n"
            "qc.h(0)\n"
            "qc.measure(0, 0)\n"
            "qc.h(0)\n"
            "qc.measure(0, 0)\n"
            "StatevectorSampler(seed=1).run([qc], shots=16).result()\n"
        )
    )
    assert translation is not None
    assert "measures partway through" in translation.message
    assert "AerSimulator" in translation.hint


def test_a_circuit_handed_to_a_primitive_bare_is_triggered_for_real() -> None:
    """`sampler.run(qc)` instead of `sampler.run([qc])`, the commonest V2 slip."""
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorSampler\n"
            "qc = QuantumCircuit(1)\n"
            "qc.measure_all()\n"
            "StatevectorSampler(seed=1).run(qc, shots=16).result()\n"
        )
    )
    assert translation is not None
    assert "instead of a list" in translation.message
    assert "square brackets" in translation.hint


def test_the_estimator_spelling_of_that_message_is_still_the_one_matched() -> None:
    """The rule carries both spellings. Only the Estimator produces this one."""
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorEstimator\n"
            "from qiskit.quantum_info import SparsePauliOp\n"
            "qc = QuantumCircuit(1)\n"
            "StatevectorEstimator().run((qc, SparsePauliOp('Z'))).result()\n"
        )
    )
    assert translation is not None
    assert "instead of a list" in translation.message


def test_missing_classical_register() -> None:
    translation = translate(
        _raised("from qiskit import QuantumCircuit\nQuantumCircuit(1).measure(0, 0)")
    )
    assert translation is not None
    assert "no wires of that kind" in translation.message
    assert "measure_all" in translation.hint


def test_empty_circuit_is_not_blamed_on_classical_bits() -> None:
    """Qiskit words the qubit case identically, so the rule must not guess.

    `QuantumCircuit().h(0)` raises the same 'out of range for size 0' as a missing
    classical register, and the reader here touched a qubit.
    """
    translation = translate(_raised("from qiskit import QuantumCircuit\nQuantumCircuit().h(0)"))
    assert translation is not None
    assert "classical bit" not in translation.message
    assert "qubit" in translation.hint


def test_qubit_index_out_of_range() -> None:
    translation = translate(_raised("from qiskit import QuantumCircuit\nQuantumCircuit(1).h(3)"))
    assert translation is not None
    assert "index 3" in translation.message
    assert "0 to 0" in translation.hint


@pytest.mark.parametrize("call", ["QuantumCircuit(2).cx(0, 0)", "QuantumCircuit(3).ccx(0, 0, 1)"])
def test_duplicate_bit_arguments(call: str) -> None:
    """Qiskit raises the same message for both, so the advice must fit both."""
    translation = translate(_raised(f"from qiskit import QuantumCircuit\n{call}"))
    assert translation is not None
    assert "same qubit more than once" in translation.message
    assert "two-qubit" not in translation.message


def test_statevector_of_measured_circuit() -> None:
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.quantum_info import Statevector\n"
            "qc = QuantumCircuit(1, 1)\n"
            "qc.measure(0, 0)\n"
            "Statevector(qc)"
        )
    )
    assert translation is not None
    assert "cannot compute a statevector" in translation.message


def test_operator_of_measured_circuit_is_not_called_a_statevector() -> None:
    """Exercise 08 is about Operator, so the wrong noun sends the reader astray."""
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.quantum_info import Operator\n"
            "qc = QuantumCircuit(1, 1)\n"
            "qc.measure(0, 0)\n"
            "Operator(qc)"
        )
    )
    assert translation is not None
    assert "matrix" in translation.message
    assert "statevector" not in translation.message


def test_primitive_given_a_bare_circuit() -> None:
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorSampler\n"
            "qc = QuantumCircuit(1)\n"
            "qc.measure_all()\n"
            "StatevectorSampler().run(qc, shots=8).result()"
        )
    )
    assert translation is not None
    assert "instead of a list" in translation.message


def test_v1_result_api() -> None:
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorSampler\n"
            "qc = QuantumCircuit(1)\n"
            "qc.measure_all()\n"
            "StatevectorSampler().run([qc], shots=8).result().get_counts()"
        )
    )
    assert translation is not None
    assert "old V1 API" in translation.message


def test_wrong_databin_field() -> None:
    translation = translate(
        _raised(
            "from qiskit import QuantumCircuit\n"
            "from qiskit.primitives import StatevectorSampler\n"
            "qc = QuantumCircuit(1)\n"
            "qc.measure_all()\n"
            "StatevectorSampler().run([qc], shots=8).result()[0].data.c.get_counts()"
        )
    )
    assert translation is not None
    assert "no classical register called `c`" in translation.message
    assert "keys()" in translation.hint


def test_circuit_method_typo() -> None:
    translation = translate(
        _raised("from qiskit import QuantumCircuit\nQuantumCircuit(1).measure_al()")
    )
    assert translation is not None
    assert "measure_all" in translation.hint


def test_syntax_error() -> None:
    translation = translate(_raised("def broken(:\n    pass"))
    assert translation is not None
    assert "syntax error" in translation.message


def test_indentation_error() -> None:
    translation = translate(_raised("def broken():\npass"))
    assert translation is not None
    assert "indentation" in translation.message


def test_name_error() -> None:
    translation = translate(_raised("undefined_thing + 1"))
    assert translation is not None
    assert "used before it is defined" in translation.message


def test_unknown_error_is_left_alone() -> None:
    """Anything without a rule keeps its raw form rather than getting a wrong gloss."""
    assert translate(_raised("1 / 0")) is None


def test_missing_third_party_package() -> None:
    translation = translate(_raised("import matplotlib_definitely_not_installed"))
    assert translation is None


def test_submodule_typo_does_not_claim_the_package_is_missing() -> None:
    """Python names the first component it could not find, so this one is a typo."""
    translation = translate(_raised("import matplotlib.pyploy"))
    assert translation is not None
    assert "not installed" not in translation.message
    assert "pyploy" in translation.message


@pytest.mark.parametrize(
    ("symbol", "expected_in_message"),
    [
        ("execute", "`execute()` was removed"),
        ("Aer", "`Aer` no longer lives"),
        ("IBMQ", "`IBMQ` was removed"),
        ("BasicAer", "`BasicAer` was renamed"),
    ],
)
def test_removed_qiskit_api_reached_by_attribute(symbol: str, expected_in_message: str) -> None:
    """`import qiskit` then `qiskit.execute(...)` is the commoner 0.x spelling.

    It raises AttributeError rather than ImportError, and used to fall through
    with no translation at all.
    """
    translation = translate(_raised(f"import qiskit\nqiskit.{symbol}"))
    assert translation is not None
    assert expected_in_message in translation.message
    assert translation.hint
