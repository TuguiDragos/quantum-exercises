"""Backend selection and the two sampling branches.

The hardware branch cannot run in CI, so it is driven here with a result built
from the real container classes. The shape and the counts below were taken from
an actual job: Bell circuit on ibm_fez, 1024 shots, 4 August 2026, job
d9p0u0jbvhrs73a21710. That run returned PrimitiveResult / SamplerPubResult with
a single DataBin field named `meas`, which is exactly what is reconstructed here.
"""

from __future__ import annotations

import pytest
from qiskit import QuantumCircuit
from qiskit.primitives.containers import BitArray, DataBin, PrimitiveResult, SamplerPubResult

from quantum_exercises import backends

# Verbatim from the ibm_fez run described above.
FEZ_COUNTS = {"00": 507, "11": 448, "01": 25, "10": 44}


def runtime_shaped_result(counts: dict[str, int], field: str = "meas") -> PrimitiveResult:
    """A result with the same classes and layout a real QPU returns."""
    return PrimitiveResult([SamplerPubResult(DataBin(**{field: BitArray.from_counts(counts)}))])


class FakeRuntimeJob:
    def __init__(self, result: PrimitiveResult) -> None:
        self._result = result

    def result(self) -> PrimitiveResult:
        return self._result


class RecordingSampler:
    """Stands in for qiskit_ibm_runtime.SamplerV2, recording how it was used."""

    calls: list[dict] = []

    def __init__(self, mode=None, options=None) -> None:
        self.mode = mode
        RecordingSampler.calls.append({"mode": mode, "options": options})

    def run(self, pubs, shots=None):
        RecordingSampler.calls[-1]["pubs"] = pubs
        RecordingSampler.calls[-1]["shots"] = shots
        return FakeRuntimeJob(runtime_shaped_result(FEZ_COUNTS))


class TestSingleRegisterCounts:
    def test_reads_a_runtime_shaped_result(self) -> None:
        result = runtime_shaped_result(FEZ_COUNTS)
        assert backends.single_register_counts(result[0]) == FEZ_COUNTS

    def test_finds_a_register_that_is_not_called_meas(self) -> None:
        """An explicit ClassicalRegister keeps its own name, so nothing is hardcoded."""
        result = runtime_shaped_result({"0": 10, "1": 6}, field="readout")
        assert backends.single_register_counts(result[0]) == {"0": 10, "1": 6}

    def test_rejects_a_result_with_no_register(self) -> None:
        empty = PrimitiveResult([SamplerPubResult(DataBin())])
        with pytest.raises(ValueError, match="measure_all"):
            backends.single_register_counts(empty[0])

    def test_rejects_a_result_with_several_registers(self) -> None:
        both = PrimitiveResult(
            [
                SamplerPubResult(
                    DataBin(
                        a=BitArray.from_counts({"0": 4}),
                        b=BitArray.from_counts({"1": 4}),
                    )
                )
            ]
        )
        with pytest.raises(ValueError, match="several classical registers"):
            backends.single_register_counts(both[0])


class TestSampleBranches:
    def test_hardware_branch_uses_the_runtime_sampler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        RecordingSampler.calls = []
        monkeypatch.setattr("qiskit_ibm_runtime.SamplerV2", RecordingSampler)

        sentinel = object()
        selection = backends.Selection(sentinel, "hardware", "ibm_fez", "test")
        circuit = QuantumCircuit(2)

        counts = backends.sample(circuit, selection, shots=1024)

        assert counts == FEZ_COUNTS
        assert len(RecordingSampler.calls) == 1
        call = RecordingSampler.calls[0]
        # A QPU is addressed through mode=, not backend=.
        assert call["mode"] is sentinel
        assert call["shots"] == 1024
        assert call["pubs"] == [circuit]

    def test_simulator_branch_does_not_touch_the_runtime_sampler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def explode(*args, **kwargs):
            raise AssertionError("the simulator branch must not reach qiskit_ibm_runtime")

        monkeypatch.setattr("qiskit_ibm_runtime.SamplerV2", explode)

        selection = backends.get_backend(prefer_hardware=False)
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        counts = backends.sample(circuit, selection, shots=256)
        assert sum(counts.values()) == 256
        assert set(counts) <= {"00", "11"}


class TestBackendSelection:
    def test_offline_never_reaches_the_network(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def explode(*args, **kwargs):
            raise AssertionError("QX_OFFLINE must prevent any service construction")

        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", explode)
        monkeypatch.setenv(backends.OFFLINE_ENV, "1")

        selection = backends.get_backend()
        assert selection.kind in ("noisy_simulator", "simulator")
        assert backends.OFFLINE_ENV in selection.reason

    def test_no_account_falls_back_to_a_noisy_simulator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from qiskit_ibm_runtime.accounts import AccountNotFoundError

        def no_account(*args, **kwargs):
            raise AccountNotFoundError("no account here")

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", no_account)

        selection = backends.get_backend()
        assert selection.kind == "noisy_simulator"
        assert "AccountNotFoundError" in selection.reason
        assert not selection.is_hardware

    def test_exhausted_quota_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A valid account with no QPU time left must not break the exercise."""

        class QuotaExhausted:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def least_busy(self, *args, **kwargs):
                raise RuntimeError("job quota exceeded for this instance")

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", QuotaExhausted)

        selection = backends.get_backend()
        assert selection.kind == "noisy_simulator"
        assert "quota exceeded" in selection.reason

    def test_no_operational_qpu_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class NothingAvailable:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def least_busy(self, *args, **kwargs):
                return None

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", NothingAvailable)

        selection = backends.get_backend()
        assert selection.kind == "noisy_simulator"
        assert "no operational QPU" in selection.reason

    def test_hardware_is_selected_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The one path that cannot be reached offline: a QPU is returned as-is."""

        class FakeQPU:
            name = "ibm_fez"
            num_qubits = 156

        class ServiceWithQPU:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def least_busy(self, **kwargs):
                assert kwargs["operational"] is True
                assert kwargs["simulator"] is False
                return FakeQPU()

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", ServiceWithQPU)

        selection = backends.get_backend(min_num_qubits=2)
        assert selection.kind == "hardware"
        assert selection.is_hardware
        assert selection.name == "ibm_fez"
        assert "real QPU" in selection.describe()

    def test_prefer_hardware_false_skips_the_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def explode(*args, **kwargs):
            raise AssertionError("prefer_hardware=False must not construct a service")

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", explode)

        selection = backends.get_backend(prefer_hardware=False)
        assert selection.kind == "simulator"


class TestIsaTranspilation:
    def test_produces_only_native_instructions(self) -> None:
        """The check exercise 11 performs, run against the offline fallback."""
        selection = backends.get_backend()
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        isa = backends.to_isa(circuit, selection.backend)
        native = set(selection.backend.target.operation_names)
        assert set(isa.count_ops()) - {"barrier", "delay"} <= native

    def test_rewrites_gates_the_backend_lacks(self) -> None:
        """A Hadamard is not native anywhere, so transpiling must change the circuit."""
        selection = backends.get_backend()
        circuit = QuantumCircuit(1)
        circuit.h(0)

        isa = backends.to_isa(circuit, selection.backend)
        assert "h" not in isa.count_ops()


class TestNoiseModelIsActuallyUsed:
    """The offline fallback promises hardware-like noise. It has to deliver it."""

    def test_the_fallback_backend_carries_a_noise_model(self) -> None:
        selection = backends.get_backend(min_num_qubits=2)
        assert selection.kind == "noisy_simulator"
        assert backends.noise_model(selection) is not None

    def test_sampling_shows_that_noise(self) -> None:
        selection = backends.get_backend(min_num_qubits=2)
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        isa = backends.to_isa(circuit, selection.backend)

        # A Bell state forbids 01 and 10. A noise-modelled backend produces them
        # anyway, which is the entire point of exercises 13 and 14. Sampling with
        # a default Aer sampler instead would silently give a perfect result.
        disagreeing = 0
        for _ in range(3):
            counts = backends.sample(isa, selection, shots=1024)
            assert sum(counts.values()) == 1024
            disagreeing += counts.get("01", 0) + counts.get("10", 0)
        assert disagreeing > 0, "the noise model was not applied"

    def test_a_noiseless_backend_stays_noiseless(self) -> None:
        selection = backends.get_backend(prefer_hardware=False)
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        counts = backends.sample(circuit, selection, shots=512)
        assert set(counts) <= {"00", "11"}
