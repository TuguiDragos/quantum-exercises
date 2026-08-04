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


def test_missing_classical_register() -> None:
    translation = translate(
        _raised("from qiskit import QuantumCircuit\nQuantumCircuit(1).measure(0, 0)")
    )
    assert translation is not None
    assert "no classical register" in translation.message
    assert "measure_all" in translation.hint


def test_qubit_index_out_of_range() -> None:
    translation = translate(_raised("from qiskit import QuantumCircuit\nQuantumCircuit(1).h(3)"))
    assert translation is not None
    assert "index 3" in translation.message
    assert "0 to 0" in translation.hint


def test_duplicate_bit_arguments() -> None:
    translation = translate(
        _raised("from qiskit import QuantumCircuit\nQuantumCircuit(2).cx(0, 0)")
    )
    assert translation is not None
    assert "same qubit twice" in translation.message


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
