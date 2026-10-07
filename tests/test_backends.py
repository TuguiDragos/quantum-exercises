"""Backend selection and the two sampling branches.

The hardware branch is driven with a result shaped like a real ibm_fez Bell job
(1024 shots, job d9p0u0jbvhrs73a21710): one DataBin field named `meas`.
"""

from __future__ import annotations

import warnings
from types import SimpleNamespace

import pytest
from qiskit import QuantumCircuit
from qiskit.primitives.containers import BitArray, DataBin, PrimitiveResult, SamplerPubResult

from quantum_exercises import backends

# Verbatim from that ibm_fez job.
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
    """Stands in for the runtime's executor Sampler, recording how it was used."""

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
        monkeypatch.setattr("qiskit_ibm_runtime.executor_sampler.Sampler", RecordingSampler)

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

    def test_the_real_hardware_sampler_runs_without_a_deprecation(self) -> None:
        """Unstubbed, on a fake device: the worker shows every warning to the learner."""
        from qiskit_ibm_runtime.fake_provider import FakeManilaV2

        fake = FakeManilaV2()
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        selection = backends.Selection(fake, "hardware", fake.name, "test")

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            counts = backends.sample(backends.to_isa(circuit, fake), selection, shots=256)

        assert sum(counts.values()) == 256
        assert set(counts) <= {"00", "01", "10", "11"}

    def test_simulator_branch_does_not_touch_the_runtime_sampler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def explode(*args, **kwargs):
            raise AssertionError("the simulator branch must not reach qiskit_ibm_runtime")

        monkeypatch.setattr("qiskit_ibm_runtime.executor_sampler.Sampler", explode)

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
        assert "no account here" in selection.reason, "the message is the actionable half"
        assert not selection.is_hardware


class TestQueuePeek:
    """Looking at the queue must never be the thing that submits, or that fails."""

    def test_offline_never_reaches_the_network(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(backends.OFFLINE_ENV, "1")

        def forbidden(*args, **kwargs):
            raise AssertionError("a peek must not contact IBM while offline")

        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", forbidden)
        assert backends.queue_peek() is None

    def test_it_reports_the_least_busy_and_its_depth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = SimpleNamespace(name="ibm_probe", status=lambda: SimpleNamespace(pending_jobs=6))
        service = SimpleNamespace(least_busy=lambda **kwargs: backend)
        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", lambda *a, **k: service)

        queue = backends.queue_peek()
        assert queue == backends.Queue("ibm_probe", 6)

    def test_no_operational_qpu_is_no_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        service = SimpleNamespace(least_busy=lambda **kwargs: None)
        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", lambda *a, **k: service)
        assert backends.queue_peek() is None

    @pytest.mark.parametrize("failure", [RuntimeError("no network"), ValueError("odd reply")])
    def test_a_peek_that_fails_is_simply_no_answer(
        self, monkeypatch: pytest.MonkeyPatch, failure: Exception
    ) -> None:
        """It runs before a decision, so it may never become the reason for one."""

        def broken(*args, **kwargs):
            raise failure

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", broken)
        assert backends.queue_peek() is None


class TestBackendSelectionContinued:
    def test_a_revoked_key_says_what_ibm_said(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An expired or revoked key shows IBM's own sentence, which says what to fix."""
        from qiskit_ibm_runtime.accounts import InvalidAccountError

        told = "Unable to retrieve instances. Please check that you are using a valid API token."

        def refused(*args, **kwargs):
            raise InvalidAccountError(told)

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", refused)

        selection = backends.get_backend()
        assert selection.kind == "noisy_simulator"
        assert "InvalidAccountError" in selection.reason
        assert "valid API token" in selection.reason

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

        asked: dict = {}

        class ServiceWithQPU:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def least_busy(self, **kwargs):
                asked.update(kwargs)
                return FakeQPU()

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", ServiceWithQPU)

        selection = backends.get_backend(min_num_qubits=2)

        # Asserted here, not in the fake: get_backend swallows exceptions from that call.
        assert asked["operational"] is True
        assert asked["simulator"] is False
        # Without it a one-qubit QPU could be offered for a two-qubit circuit.
        assert asked["min_num_qubits"] == 2
        assert selection.kind == "hardware"
        assert selection.is_hardware
        assert selection.name == "ibm_fez"
        assert "real QPU" in selection.describe()

    @pytest.mark.hardware
    def test_a_bell_pair_on_a_real_qpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The one test that reaches IBM. Deselected by default; opt in with -m hardware."""
        from qiskit import QuantumCircuit

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        selection = backends.get_backend(min_num_qubits=2)
        if not selection.is_hardware:
            pytest.skip(f"no QPU within reach: {selection.reason}")

        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()
        counts = backends.sample(backends.to_isa(circuit, selection.backend), selection, shots=1024)

        assert sum(counts.values()) == 1024
        agreed = counts.get("00", 0) + counts.get("11", 0)
        assert agreed / 1024 > 0.6, f"{selection.name} gave {counts}"

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

        # A Bell state forbids 01 and 10; only a noisy backend produces them.
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


def test_normalize_counts_rejects_multiple_registers() -> None:
    with pytest.raises(ValueError, match="several classical registers"):
        backends._normalize_counts({"00 11": 5})


def test_single_register_counts_rejects_an_empty_result() -> None:
    fake = SimpleNamespace(data=SimpleNamespace(keys=lambda: []))
    with pytest.raises(ValueError, match="no classical register"):
        backends.single_register_counts(fake)


def test_get_backend_without_hardware_is_a_plain_simulator() -> None:
    selection = backends.get_backend(prefer_hardware=False)
    assert selection.kind == "simulator"
    assert "not requested" in selection.reason


def test_get_backend_falls_back_when_runtime_is_absent(monkeypatch) -> None:
    monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "qiskit_ibm_runtime":
            raise ImportError("absent")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    selection = backends.get_backend()
    assert selection.kind in ("noisy_simulator", "simulator")
    assert "not installed" in selection.reason


def test_selection_describe_covers_every_kind() -> None:
    for kind in ("hardware", "noisy_simulator", "simulator"):
        assert backends.Selection(None, kind, "n", "r").describe()


class TestPeekIsQuiet:
    """The peek prints in the reader's terminal, so the client's log must stay quiet."""

    @staticmethod
    def _talkative(monkeypatch: pytest.MonkeyPatch) -> None:
        import logging

        def service(*args, **kwargs):
            logger = logging.getLogger("qiskit_ibm_runtime")
            logger.warning("Instance was not set at service instantiation. Free and trial ...")
            logger.warning("Loading instance: open-instance, plan: open")
            backend = SimpleNamespace(
                name="ibm_marrakesh", status=lambda: SimpleNamespace(pending_jobs=6)
            )
            return SimpleNamespace(least_busy=lambda **k: backend)

        monkeypatch.delenv(backends.OFFLINE_ENV, raising=False)
        monkeypatch.setattr("qiskit_ibm_runtime.QiskitRuntimeService", service)

    def test_the_client_log_never_reaches_the_screen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Against the handler the client really installs: its own, propagate off."""
        import io
        import logging

        stream = io.StringIO()
        logger = logging.getLogger("qiskit_ibm_runtime")
        printer = logging.StreamHandler(stream)
        printer.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        handlers = logger.handlers[:]
        propagate, level = logger.propagate, logger.level
        logger.handlers = [printer]
        logger.propagate = False
        logger.setLevel(logging.WARNING)
        try:
            self._talkative(monkeypatch)
            queue = backends.queue_peek()
        finally:
            logger.handlers = handlers
            logger.propagate = propagate
            logger.setLevel(level)

        assert stream.getvalue() == "", f"the client printed: {stream.getvalue()!r}"
        assert queue == backends.Queue("ibm_marrakesh", 6)

    def test_the_logger_is_left_as_it_was_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import logging

        logger = logging.getLogger("qiskit_ibm_runtime")
        before = (logger.propagate, list(logger.handlers))
        self._talkative(monkeypatch)
        backends.queue_peek()
        assert (logger.propagate, list(logger.handlers)) == before
