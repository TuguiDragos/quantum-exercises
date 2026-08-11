"""Unit tests for the verification primitives.

The statistical thresholds get the most attention here: a check that is too tight
makes CI flake, and one that is too loose passes wrong answers.
"""

from __future__ import annotations

import math
from types import ModuleType

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CZGate, HGate
from qiskit.quantum_info import Operator, Statevector

from quantum_exercises import checks

INV_SQRT2 = 1 / math.sqrt(2)


def _bell() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


class TestStateChecks:
    def test_accepts_correct_state(self) -> None:
        target = Statevector([INV_SQRT2, 0, 0, INV_SQRT2])
        assert checks.assert_state_equiv(_bell(), target).num_qubits == 2

    def test_ignores_global_phase(self) -> None:
        shifted = _bell()
        shifted.global_phase += math.pi / 2
        checks.assert_state_equiv(shifted, Statevector([INV_SQRT2, 0, 0, INV_SQRT2]))

    def test_rejects_wrong_state(self) -> None:
        with pytest.raises(checks.CheckFailed):
            checks.assert_state_equiv(_bell(), Statevector([1, 0, 0, 0]))

    def test_reports_qubit_count_mismatch(self) -> None:
        with pytest.raises(checks.CheckFailed, match="Wrong number of qubits"):
            checks.assert_state_equiv(_bell(), Statevector([1, 0]))

    def test_strips_final_measurements(self) -> None:
        measured = _bell()
        measured.measure_all()
        checks.assert_state_equiv(measured, Statevector([INV_SQRT2, 0, 0, INV_SQRT2]))


class TestOperatorChecks:
    def test_accepts_matching_operator(self) -> None:
        qc = QuantumCircuit(1)
        qc.h(0)
        checks.assert_operator_equiv(qc, Operator(HGate()))

    def test_accepts_circuit_as_target(self) -> None:
        """A QuantumCircuit target must not be routed through numpy."""
        left = QuantumCircuit(1)
        left.h(0)
        right = QuantumCircuit(1)
        right.h(0)
        checks.assert_operator_equiv(left, right)

    def test_accepts_ndarray_as_target(self) -> None:
        qc = QuantumCircuit(1)
        qc.x(0)
        checks.assert_operator_equiv(qc, np.array([[0, 1], [1, 0]]))

    def test_cz_from_h_and_cx(self) -> None:
        qc = QuantumCircuit(2)
        qc.h(1)
        qc.cx(0, 1)
        qc.h(1)
        checks.assert_operator_equiv(qc, Operator(CZGate()))

    def test_rejects_measured_circuit(self) -> None:
        qc = QuantumCircuit(1, 1)
        qc.h(0)
        qc.measure(0, 0)
        with pytest.raises(checks.CheckFailed, match="no matrix representation"):
            checks.assert_operator_equiv(qc, Operator(HGate()))

    def test_unitarity(self) -> None:
        qc = QuantumCircuit(1)
        qc.h(0)
        assert checks.assert_unitary(qc).is_unitary()


class TestCountsSupport:
    def test_accepts_exact_support(self) -> None:
        checks.assert_counts_support({"00": 500, "11": 524}, {"00", "11"})

    def test_rejects_impossible_outcome(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_support({"00": 500, "11": 500, "01": 24}, {"00", "11"})
        assert "should be impossible" in excinfo.value.detail

    def test_rejects_missing_outcome(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_support({"00": 1024}, {"00", "11"})
        assert "did not" in excinfo.value.detail

    def test_zero_valued_key_is_not_present(self) -> None:
        checks.assert_counts_support({"00": 512, "11": 512, "01": 0}, {"00", "11"})


class TestCountsClose:
    def test_accepts_the_reports_example(self) -> None:
        """508 to 516 out of 1024 is about 0.25 sigma and must pass comfortably."""
        checks.assert_counts_close({"0": 508, "1": 516}, {"0": 0.5, "1": 0.5})

    def test_accepts_a_four_sigma_boundary_case(self) -> None:
        # SE at p=0.5, N=1024 is 0.015625, so 3.9 sigma is about 62 counts off.
        checks.assert_counts_close({"0": 512 - 62, "1": 512 + 62}, {"0": 0.5, "1": 0.5})

    def test_rejects_a_clearly_wrong_prediction(self) -> None:
        with pytest.raises(checks.CheckFailed):
            checks.assert_counts_close({"0": 768, "1": 256}, {"0": 0.5, "1": 0.5})

    def test_rejects_probabilities_that_do_not_sum_to_one(self) -> None:
        with pytest.raises(checks.CheckFailed, match="sum to"):
            checks.assert_counts_close({"0": 512, "1": 512}, {"0": 0.866, "1": 0.5})

    def test_rejects_impossible_outcome_that_occurred(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_close({"0": 1000, "1": 24}, {"0": 1.0, "1": 0.0})
        assert "predicted impossible" in excinfo.value.detail

    def test_rejects_unpredicted_outcome(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_close({"0": 512, "1": 500, "2": 12}, {"0": 0.5, "1": 0.5})
        assert "predicted nothing" in excinfo.value.detail

    def test_rejects_empty_counts(self) -> None:
        with pytest.raises(checks.CheckFailed, match="No shots"):
            checks.assert_counts_close({}, {"0": 1.0})

    def test_false_negative_rate_is_low(self) -> None:
        """A correct answer must survive many independent samples, or CI flakes."""
        rng = np.random.default_rng(20260804)
        shots = 1024
        for _ in range(300):
            ones = int(rng.binomial(shots, 0.5))
            checks.assert_counts_close({"0": shots - ones, "1": ones}, {"0": 0.5, "1": 0.5})


class TestChiSquare:
    def test_uniform_distribution_passes(self) -> None:
        counts = {"00": 256, "01": 250, "10": 262, "11": 256}
        checks.assert_counts_distribution(counts, {k: 0.25 for k in counts})

    def test_skewed_distribution_fails(self) -> None:
        counts = {"00": 700, "01": 100, "10": 100, "11": 124}
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_distribution(counts, {k: 0.25 for k in counts})
        assert "chi-square" in excinfo.value.detail

    def test_statistic_and_critical_value(self) -> None:
        statistic, critical, dof = checks.chi_square_counts(
            {"0": 512, "1": 512}, {"0": 0.5, "1": 0.5}
        )
        assert statistic == pytest.approx(0.0, abs=1e-9)
        assert dof == 1
        # chi-square critical value at alpha=0.001 with 1 dof is about 10.83.
        assert critical == pytest.approx(10.83, abs=0.01)

    def test_outcome_with_zero_expectation_is_infinite(self) -> None:
        statistic, _, _ = checks.chi_square_counts({"0": 1000, "1": 24}, {"0": 1.0})
        assert math.isinf(statistic)

    def test_an_outcome_predicted_impossible_that_stayed_impossible_costs_nothing(self) -> None:
        """p = 0 contributes no chi-square term when the outcome never occurred.

        Dividing by its expected count would be a division by zero, so the term is
        skipped rather than computed. Only an outcome that did occur is infinite.
        """
        statistic, _, dof = checks.chi_square_counts({"0": 1024, "1": 0}, {"0": 1.0, "1": 0.0})
        assert statistic == pytest.approx(0.0, abs=1e-9)
        assert math.isfinite(statistic)
        # "1" is predicted, so it counts toward the outcomes even at zero shots.
        assert dof == 1


class TestInvariants:
    """Properties that must hold across the whole input space, not at sampled points.

    Swept rather than randomised, so a failure names the same case every time.
    """

    SAMPLES = [
        {"0": 512, "1": 512},
        {"0": 1, "1": 1023},
        {"0": 1024},
        {"00": 250, "01": 250, "10": 250, "11": 274},
        {"00": 1, "01": 2, "10": 3, "11": 4090},
        {f"{n:03b}": n + 1 for n in range(8)},
    ]

    @pytest.mark.parametrize("counts", SAMPLES)
    def test_a_prediction_that_matches_exactly_is_never_rejected(self, counts: dict) -> None:
        """The tolerance may be as tight as you like; zero deviation must pass it."""
        shots = sum(counts.values())
        exact = {outcome: value / shots for outcome, value in counts.items()}
        checks.assert_counts_close(counts, exact)
        checks.assert_counts_distribution(counts, exact)

    @pytest.mark.parametrize("counts", SAMPLES)
    def test_chi_square_is_zero_on_a_perfect_fit(self, counts: dict) -> None:
        shots = sum(counts.values())
        exact = {outcome: value / shots for outcome, value in counts.items()}
        statistic, _, _ = checks.chi_square_counts(counts, exact)
        assert statistic == pytest.approx(0.0, abs=1e-9)

    def test_chi_square_grows_as_the_sample_drifts(self) -> None:
        """Drift one way from a perfect fit and the statistic can only rise.

        A test that fell as the answer got worse would pass wrong answers at some
        distance and reject them at others.
        """
        expected = {"0": 0.5, "1": 0.5}
        shots = 1000
        previous = -1.0
        for moved in range(0, 401, 20):
            counts = {"0": shots // 2 + moved, "1": shots // 2 - moved}
            statistic, _, _ = checks.chi_square_counts(counts, expected)
            assert statistic >= previous, f"fell at {moved} shots of drift"
            previous = statistic

    @pytest.mark.parametrize("shots", [64, 1024, 8192])
    def test_the_four_sigma_band_widens_with_the_sample(self, shots: int) -> None:
        """More shots means a tighter band in proportion, which is the point of it.

        The check is on the proportion, so the same absolute drift has to become
        less acceptable as the sample grows.
        """
        expected = {"0": 0.5, "1": 0.5}
        band = 0
        while band <= shots // 2:
            counts = {"0": shots // 2 + band, "1": shots // 2 - band}
            try:
                checks.assert_counts_close(counts, expected)
            except checks.CheckFailed:
                break
            band += 1
        # 4 sigma on a fair coin is 2 * sqrt(shots), give or take the integer step.
        assert abs(band - 2 * math.sqrt(shots)) <= 2, f"band {band} at {shots} shots"


class TestShots:
    def test_matching_total(self) -> None:
        checks.assert_shots({"0": 500, "1": 524}, 1024)

    def test_mismatched_total(self) -> None:
        with pytest.raises(checks.CheckFailed, match="add up to"):
            checks.assert_shots({"0": 500, "1": 500}, 1024)


class TestRequire:
    @staticmethod
    def _module(**names: object) -> ModuleType:
        """A real module, because require() reads vars(), not class attributes."""
        module = ModuleType("qx_test_module")
        for key, value in names.items():
            setattr(module, key, value)
        return module

    def test_missing_name_lists_what_was_defined(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.require(self._module(other=1, another=2), "qc")
        assert "expects a variable named `qc`" in excinfo.value.message
        assert "another, other" in excinfo.value.detail

    def test_missing_name_with_nothing_defined(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.require(self._module(), "qc")
        assert "(none)" in excinfo.value.detail

    def test_none_is_rejected(self) -> None:
        with pytest.raises(checks.CheckFailed, match="still None"):
            checks.require(self._module(qc=None), "qc")

    def test_wrong_type_is_rejected(self) -> None:
        with pytest.raises(checks.CheckFailed, match="should be a QuantumCircuit"):
            checks.require(self._module(qc="not a circuit"), "qc", QuantumCircuit)

    def test_correct_value_is_returned(self) -> None:
        circuit = _bell()
        assert checks.require(self._module(qc=circuit), "qc", QuantumCircuit) is circuit


class TestArtifacts:
    def test_payloads_are_json_serializable(self) -> None:
        """Artifacts cross a process boundary as JSON, so they must survive it."""
        import json

        qc = _bell()
        artifacts = [
            checks.statevector_artifact(Statevector(qc)),
            checks.matrix_artifact(Operator(qc)),
            checks.counts_artifact({"00": 512, "11": 512}),
            checks.text_artifact("hello"),
        ]
        for artifact in artifacts:
            json.dumps({"payload": artifact.payload, "meta": artifact.meta})


class TestChecksEdges:
    def test_statevector_passthrough(self) -> None:
        sv = Statevector([1, 0])
        assert checks.as_statevector(sv) is sv

    def test_as_statevector_rejects_a_stranger(self) -> None:
        with pytest.raises(checks.CheckFailed, match="Expected a QuantumCircuit"):
            checks.as_statevector("not a circuit")

    def test_as_statevector_reports_a_mid_circuit_measurement(self) -> None:
        qc = QuantumCircuit(1, 1)
        qc.measure(0, 0)
        qc.h(0)
        with pytest.raises(checks.CheckFailed, match="cannot be turned into a statevector"):
            checks.as_statevector(qc)

    def test_operator_passthrough(self) -> None:
        op = Operator(np.eye(2))
        assert checks.as_operator(op) is op

    def test_as_operator_rejects_a_stranger(self) -> None:
        with pytest.raises(checks.CheckFailed, match="Expected a QuantumCircuit"):
            checks.as_operator(3.14)

    def test_target_state_from_ndarray(self) -> None:
        qc = QuantumCircuit(1)
        qc.x(0)
        checks.assert_state_equiv(qc, np.array([0, 1]))

    def test_target_state_from_circuit(self) -> None:
        left = QuantumCircuit(1)
        left.x(0)
        checks.assert_state_equiv(left, left.copy())

    def test_operator_dimension_mismatch(self) -> None:
        qc = QuantumCircuit(1)
        qc.h(0)
        with pytest.raises(checks.CheckFailed, match="Wrong dimensions"):
            checks.assert_operator_equiv(qc, Operator(np.eye(4)))

    def test_operator_mismatch_mentions_endianness(self) -> None:
        qc = QuantumCircuit(1)
        qc.h(0)
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_operator_equiv(qc, np.eye(2))
        assert "little-endian" in excinfo.value.detail

    def test_non_unitary_is_rejected(self) -> None:
        with pytest.raises(checks.CheckFailed, match="not unitary"):
            checks.assert_unitary(Operator(np.array([[1, 0], [0, 2]])))

    def test_certain_outcome_that_did_not_happen(self) -> None:
        with pytest.raises(checks.CheckFailed) as excinfo:
            checks.assert_counts_close({"0": 900, "1": 124}, {"0": 1.0, "1": 0.0})
        assert "predicted certain" in excinfo.value.detail

    def test_impossible_outcome_that_stayed_impossible(self) -> None:
        checks.assert_counts_close({"0": 1024}, {"0": 1.0, "1": 0.0})

    def test_chi_square_rejects_empty_counts(self) -> None:
        with pytest.raises(checks.CheckFailed, match="No shots"):
            checks.chi_square_counts({}, {"0": 1.0})

    def test_require_accepts_a_type_tuple(self) -> None:
        module = ModuleType("m")
        module.value = 3
        assert checks.require(module, "value", (int, float)) == 3
        module.wrong = "s"
        with pytest.raises(checks.CheckFailed, match="int or float"):
            checks.require(module, "wrong", (int, float))
