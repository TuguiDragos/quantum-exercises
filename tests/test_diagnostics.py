"""Every diagnosis an exercise promises a learner who gets it wrong.

The rest of the suite proves two points per exercise: the solution passes and the
untouched template does not. That leaves the most valuable code in the repository
unguarded. A `check.py` earns its keep in the branches between those two states,
where it names the misconception rather than reporting a mismatch, and nothing
noticed when one of those branches stopped firing.

Each case starts from the exercise's own `solution.py` and appends one override.
Python takes the last definition, so the result is a correct answer with exactly
one thing wrong, and the case cannot rot when a solution is rewritten. The few
cases that have to remove something rather than replace it are marked standalone
and carry their whole source.

`check()` is called in this process rather than through the runner. The subprocess
path already has its own tests, and this way a case costs milliseconds instead of
a fresh Qiskit import.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from quantum_exercises.checks import CheckFailed
from quantum_exercises.registry import Exercise

# Exercise 04 is built around this warning, so the case that reproduces it emits
# it for real. Matched on its own text, so nothing else can hide behind the filter.
pytestmark = pytest.mark.filterwarnings(
    "ignore:One of your circuits has no output classical registers:UserWarning"
)

# slug, case name, override source, fragment of the message it must produce.
# A trailing True means the override is the whole file rather than an addition.
CASES: list[tuple] = []


def case(slug: str, name: str, override: str, fragment: str, standalone: bool = False) -> None:
    CASES.append((slug, name, override, fragment, standalone))


# --------------------------------------------------------------------------
# Act I
# --------------------------------------------------------------------------

case("01_environment", "missing-name", "", "expects a variable named `qiskit_version`", True)
case("01_environment", "still-none", "qiskit_version = None", "is still None")
case("01_environment", "not-a-string", "qiskit_version = 2", "should be a str")
case(
    "01_environment",
    "typed-in-by-hand",
    'qiskit_version = "2.5.1"',
    "written in by hand rather than read from the package",
    True,
)
case(
    "01_environment",
    "wrong-version-reported",
    'qiskit_version = "0.45.0"',
    "but this environment has",
)

case(
    "02_dictionaries",
    "not-a-function",
    "total_shots = 1024",
    "`total_shots` should be a function",
)
case(
    "02_dictionaries",
    "empty-dict-is-not-zero",
    "def total_shots(counts):\n    return sum(counts.values()) or 1\n",
    "total_shots({}) should be 0",
)
case(
    "02_dictionaries",
    "counts-the-keys",
    "def total_shots(counts):\n    return len(counts)\n",
    "expected 1024",
)
case(
    "02_dictionaries",
    "returns-the-count-not-the-key",
    "def most_common(counts):\n    return max(counts.values())\n",
    "most_common",
)
case(
    "02_dictionaries",
    "probabilities-not-a-dict",
    "def outcome_probabilities(counts):\n    return list(counts.values())\n",
    "expected a dict",
)
case(
    "02_dictionaries",
    "probabilities-wrong-keys",
    'def outcome_probabilities(counts):\n    return {"x": 1.0}\n',
    "expected ['00', '11']",
)
case(
    "02_dictionaries",
    "integer-division",
    "def outcome_probabilities(counts):\n"
    "    shots = total_shots(counts)\n"
    "    return {k: v // shots for k, v in counts.items()}\n",
    "dividing with / and not //",
)

case("03_first_circuit", "two-qubits", "qc = QuantumCircuit(2)\nqc.h(0)", "but this exercise asks")
case(
    "03_first_circuit",
    "classical-bit-added",
    "qc = QuantumCircuit(1, 1)\nqc.h(0)",
    "classical bits, but this exercise asks for none",
)
case("03_first_circuit", "empty", "qc = QuantumCircuit(1)", "circuit is empty: no gate was added")
case(
    "03_first_circuit",
    "wrong-gate",
    "qc = QuantumCircuit(1)\nqc.x(0)",
    "does not implement a Hadamard gate",
)

case(
    "04_measurement",
    "measurement-forgotten",
    "qc = QuantumCircuit(1)\n"
    "qc.h(0)\n"
    "result = StatevectorSampler(seed=1234).run([qc], shots=SHOTS).result()\n",
    "still has no measurement",
)
case(
    "04_measurement",
    "job-instead-of-result",
    "result = sampler.run([qc], shots=SHOTS)",
    "holds the job, not the answer",
)
case(
    "04_measurement",
    "not-indexable",
    "result = 42",
    "cannot be indexed with [0]",
)
case(
    "04_measurement",
    "sampled-a-different-circuit",
    "_unmeasured = QuantumCircuit(1)\n"
    "_unmeasured.h(0)\n"
    "result = StatevectorSampler(seed=1234).run([_unmeasured], shots=SHOTS).result()\n",
    "no classical registers, so it holds no data",
)
case(
    "04_measurement",
    "hadamard-dropped",
    "qc = QuantumCircuit(1)\n"
    "qc.measure_all()\n"
    "result = StatevectorSampler(seed=1234).run([qc], shots=SHOTS).result()\n",
    "never appeared",
)
case(
    "04_measurement",
    "shots-left-off-the-run",
    "result = StatevectorSampler(seed=1234).run([qc]).result()\n",
    "but this exercise asks for 2048 shots",
)
case(
    "04_measurement",
    "result-from-a-different-circuit",
    "qc = QuantumCircuit(1)\n"
    "qc.x(0)\n"
    "qc.measure_all()\n"
    "_elsewhere = QuantumCircuit(1)\n"
    "_elsewhere.h(0)\n"
    "_elsewhere.measure_all()\n"
    "result = StatevectorSampler(seed=1234).run([_elsewhere], shots=SHOTS).result()\n",
    "not a sample of the circuit in `qc`",
)
case(
    "04_measurement",
    "wrong-distribution",
    "qc = QuantumCircuit(1)\n"
    "qc.ry(1.05, 0)\n"
    "qc.measure_all()\n"
    "result = StatevectorSampler(seed=1234).run([qc], shots=SHOTS).result()\n",
    "do not match what was measured",
)

case("05_reading_counts", "not-a-function", "read_counts = {}", "should be a function")
case(
    "05_reading_counts",
    "stopped-at-the-bitarray",
    "def read_counts(result):\n    return result[0].data.meas\n",
    "expected a dict",
)
case(
    "05_reading_counts",
    "hardcoded-counts",
    'def read_counts(result):\n    return {"0": 512}\n',
    "gave the wrong answer",
)
case(
    "05_reading_counts",
    "wrong-shot-count",
    "def read_shots(result):\n    return 0\n",
    "read_shots returned 0",
)

# --------------------------------------------------------------------------
# Act II
# --------------------------------------------------------------------------

case(
    "06_born_rule",
    "circuit-was-changed",
    "qc = QuantumCircuit(1)\nqc.rx(THETA, 0)\nqc.measure_all()",
    "The circuit was changed",
)
case("06_born_rule", "outcome-missing", 'predicted = {"0": 0.75}', "missing the outcome(s) ['1']")
case(
    "06_born_rule",
    "still-none",
    'predicted = {"0": None, "1": 0.25}',
    "is still None",
)
case(
    "06_born_rule",
    "not-a-number",
    'predicted = {"0": "0.75", "1": 0.25}',
    "should be a number",
)
case(
    "06_born_rule",
    "outside-zero-to-one",
    'predicted = {"0": 1.5, "1": -0.5}',
    "which is not a probability",
)
case(
    "06_born_rule",
    "amplitudes-not-probabilities",
    'predicted = {"0": math.cos(THETA / 2), "1": math.sin(THETA / 2)}',
    "Those are the amplitudes, not the probabilities",
)
case(
    "06_born_rule",
    "plausible-but-wrong",
    'predicted = {"0": 0.5, "1": 0.5}',
    "do not match what was measured",
)

case(
    "07_statevector",
    "two-qubits",
    "qc_a = QuantumCircuit(2)\nqc_a.h(0)\nqc_a.s(0)",
    "has 2 qubits, but should have exactly 1",
)
case("07_statevector", "left-empty", "qc_a = QuantumCircuit(1)", "is still empty")
case(
    "07_statevector",
    "z-instead-of-s",
    "qc_a = QuantumCircuit(1)\nqc_a.h(0)\nqc_a.z(0)",
    "does not prepare (|0> + i|1>) / sqrt(2)",
)

case(
    "08_gates_as_matrices",
    "three-qubits",
    "qc = QuantumCircuit(3)\nqc.h(1)\nqc.cx(0, 1)\nqc.h(1)",
    "but should have exactly 2",
)
case("08_gates_as_matrices", "empty", "qc = QuantumCircuit(2)", "still empty")
case(
    "08_gates_as_matrices",
    "reached-for-cz",
    "qc = QuantumCircuit(2)\nqc.cz(0, 1)",
    "allows only h and cx",
)
case(
    "08_gates_as_matrices",
    "cnot-alone",
    "qc = QuantumCircuit(2)\nqc.cx(0, 1)",
    "matrix is not controlled-Z",
)

case(
    "09_interference",
    "undo-two-qubits",
    "qc_undo = QuantumCircuit(2)\nqc_undo.h(0)\nqc_undo.h(0)",
    "`qc_undo` has 2 qubits",
)
case("09_interference", "undo-empty", "qc_undo = QuantumCircuit(1)", "`qc_undo` is still empty")
case(
    "09_interference",
    "undo-wrong-gates",
    "qc_undo = QuantumCircuit(1)\nqc_undo.x(0)\nqc_undo.x(0)",
    "should be exactly two Hadamards",
)
case(
    "09_interference",
    "flip-two-qubits",
    "qc_flip = QuantumCircuit(2)\nqc_flip.h(0)\nqc_flip.z(0)\nqc_flip.h(0)",
    "`qc_flip` has 2 qubits",
)
case(
    "09_interference",
    "flip-by-a-bare-not",
    "qc_flip = QuantumCircuit(1)\nqc_flip.x(0)",
    "should still have exactly two Hadamards",
)
case(
    "09_interference",
    "phase-outside-the-sandwich",
    "qc_flip = QuantumCircuit(1)\nqc_flip.h(0)\nqc_flip.h(0)\nqc_flip.x(0)",
    "does not sandwich a phase between the Hadamards",
)
case(
    "09_interference",
    "answered-with-reality",
    "coin_model_prediction = 1.0",
    "That is what actually happens, not what the coin model predicts",
)
case(
    "09_interference",
    "wrong-number",
    "coin_model_prediction = 0.25",
    "but the coin model predicts 0.5",
)
case(
    "09_interference",
    "prediction-not-a-number",
    'coin_model_prediction = "half"',
    "should be a number",
)
case(
    "09_interference",
    "flip-with-the-wrong-phase",
    "qc_flip = QuantumCircuit(1)\nqc_flip.h(0)\nqc_flip.s(0)\nqc_flip.h(0)\n",
    "does not come out as a NOT",
)

case(
    "10_deutsch",
    "oracle-called-twice",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "the oracle was applied twice",
)
case(
    "10_deutsch",
    "oracle-never-composed",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "never put in",
)
case(
    "10_deutsch",
    "oracle-read-instead-of-composed",
    # The one answer that cannot be caught by looking at what comes back. For two
    # of the four oracles this builds the same circuit as composing, gate for
    # gate, so it is the choice of input that gives it away rather than any
    # inspection of the output.
    "def deutsch(oracle):\n"
    "    from qiskit.quantum_info import Operator as _Operator\n"
    "    import numpy as _np\n"
    "    _matrix = _Operator(oracle).data\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    if not _np.allclose(_matrix[0, 0], _matrix[1, 1]):\n"
    "        qc.z(0)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "does not put the oracle it was handed into the circuit",
)
case(
    "10_deutsch",
    "an-unfamiliar-oracle-crashes-it",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    if oracle.data and oracle.data[0].operation.name not in ('x', 'z'):\n"
    "        raise ValueError('I only know the four')\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "raised ValueError on an oracle outside the four",
)
case(
    "10_deutsch",
    "an-unfamiliar-oracle-gets-nothing-back",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    if oracle.data and oracle.data[0].operation.name not in ('x', 'z'):\n"
    "        return None\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "did not return a one-qubit circuit",
)
case(
    "10_deutsch",
    "oracle-guessed-from-its-size",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    if len(oracle.data) in (1, 3):\n"
    "        qc.z(0)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "does not put the oracle it was handed into the circuit",
)
case(
    "10_deutsch",
    "measurement-forgotten",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.h(0)\n"
    "    return qc\n",
    "has no measurement",
)
case(
    "10_deutsch",
    "one-hadamard",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(1)\n"
    "    qc.h(0)\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "should apply exactly two Hadamards",
)
case(
    "10_deutsch",
    "returns-nothing",
    "def deutsch(oracle):\n    return None\n",
    "expected a QuantumCircuit",
)
case(
    "10_deutsch",
    "oracle-tampered-with",
    "def constant_zero():\n    return 42\n",
    "should return a QuantumCircuit",
)
case(
    "10_deutsch",
    "verdict-not-a-bool",
    "def is_balanced(counts):\n    return 1\n",
    "expected a bool",
)
case(
    "10_deutsch",
    "always-answers-constant",
    "def is_balanced(counts):\n    return False\n",
    "Measuring 1 means balanced",
)
case(
    "10_deutsch",
    "two-qubit-circuit",
    "def deutsch(oracle):\n"
    "    qc = QuantumCircuit(2)\n"
    "    qc.h(0)\n"
    "    qc.compose(oracle, inplace=True)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "expected 1",
)
case(
    "10_deutsch",
    "not-a-function",
    "deutsch = 1",
    "should be a function",
)
case(
    "10_deutsch",
    "presence-instead-of-majority",
    'def is_balanced(counts):\n    return "1" in counts\n',
    "Take the outcome that occurred most often",
)

case(
    "11_bell_entanglement",
    "three-qubits",
    "qc = QuantumCircuit(3)\nqc.h(0)\nqc.cx(0, 1)",
    "but should have exactly 2",
)
case(
    "11_bell_entanglement",
    "measured-too-early",
    "qc = QuantumCircuit(2)\nqc.h(0)\nqc.cx(0, 1)\nqc.measure_all()",
    "already contains a measurement",
)
case(
    "11_bell_entanglement",
    "no-entanglement",
    "qc = QuantumCircuit(2)\nqc.h(0)",
    "does not prepare (|00> + |11>) / sqrt(2)",
)
case(
    "11_bell_entanglement",
    "label-wrong-shape",
    'label_q0_only = "0"',
    "not a two-character bitstring",
)
case(
    "11_bell_entanglement",
    "label-read-big-endian",
    'label_q0_only = "10"',
    "qubit 0 is the RIGHTMOST character",
)
case(
    "11_bell_entanglement",
    "impossible-not-a-set",
    'impossible_outcomes = ["01", "10"]',
    "should be a set",
)
case(
    "11_bell_entanglement",
    "impossible-inverted",
    'impossible_outcomes = {"00", "11"}',
    "The ones you never get are the ones where the qubits disagree",
)

# --------------------------------------------------------------------------
# Act III
# --------------------------------------------------------------------------

case(
    "12_exponential_wall",
    "n-squared",
    "def amplitudes_for(n):\n    return n**2\n",
    "which is n squared",
)
case(
    "12_exponential_wall",
    "n-doubled",
    "def amplitudes_for(n):\n    return 2 * n\n",
    "which is n doubled",
)
case(
    "12_exponential_wall",
    "eight-bytes-per-amplitude",
    "def quantum_bytes_for(n):\n    return amplitudes_for(n) * 8\n",
    "which is half of the",
)
case(
    "12_exponential_wall",
    "capped-at-a-terabyte",
    "def quantum_bytes_for(n):\n    return min(amplitudes_for(n) * 16, 10**12)\n",
    "capped or approximated",
)
case(
    "12_exponential_wall",
    "floor-division",
    "def classical_bytes_for(n):\n    return n // BITS_PER_BYTE\n",
    "The division rounded down",
)
case(
    "12_exponential_wall",
    "multiplied-by-eight",
    "def classical_bytes_for(n):\n    return n * BITS_PER_BYTE\n",
    "which is n multiplied by eight",
)
case(
    "12_exponential_wall",
    "two-to-the-n-on-the-classical-side",
    "def classical_bytes_for(n):\n    return 2**n // BITS_PER_BYTE\n",
    "which came from 2 to the n",
)
case(
    "12_exponential_wall",
    "rounded-to-nearest",
    "def classical_bytes_for(n):\n    return round(n / BITS_PER_BYTE)\n",
    "expected 2",
)
case(
    "12_exponential_wall",
    "amplitudes-off-by-one",
    "def amplitudes_for(n):\n    return 2**n + 1\n",
    "amplitudes",
)
case(
    "12_exponential_wall",
    "seventeen-bytes-per-amplitude",
    "def quantum_bytes_for(n):\n    return amplitudes_for(n) * 17\n",
    "Its dtype is complex128",
)
case(
    "12_exponential_wall",
    "bits-reported-as-bytes",
    "def classical_bytes_for(n):\n    return n\n",
    "at eight bits per byte, rounded up",
)
case(
    "12_exponential_wall",
    "placeholder-left-in",
    "def amplitudes_for(n):\n    return None\n",
    "Replace the placeholder with a number",
)
case(
    "12_exponential_wall",
    "float-instead-of-int",
    "def amplitudes_for(n):\n    return float(2**n)\n",
    "a float, expected the whole number",
)
case(
    "12_exponential_wall",
    "not-a-number-at-all",
    'def amplitudes_for(n):\n    return "lots"\n',
    "expected a whole number",
)
case(
    "12_exponential_wall",
    "not-a-function",
    "amplitudes_for = 1024",
    "should be a function",
)

case(
    "13_migration",
    "circuit-resized",
    "qc = QuantumCircuit(3, 3)\n"
    "qc.h(0)\n"
    "qc.cx(0, 1)\n"
    "qc.measure([0, 1], [0, 1])\n"
    "result = StatevectorSampler().run([qc], shots=SHOTS).result()\n"
    "counts = result[0].data.c.get_counts()\n",
    "should stay at 2 qubits and 2 classical bits",
)
case(
    "13_migration",
    "measurement-lost",
    "qc = QuantumCircuit(2, 2)\nqc.h(0)\nqc.cx(0, 1)\n",
    "lost its measurement",
)
case(
    "13_migration",
    "old-style-result",
    "class _LegacyResult:\n"
    "    def get_counts(self):\n"
    '        return {"00": 512, "11": 512}\n'
    "\n"
    "result = _LegacyResult()\n",
    "not a V2 primitive result",
)
case(
    "13_migration",
    "not-a-v2-result",
    "result = 42",
    "does not behave like a V2 result",
)
case(
    "13_migration",
    "measure-all-changed-the-register",
    # QuantumCircuit(2) rather than (2, 2): measure_all() creates the two
    # classical bits itself, so the count still matches and only the name differs.
    "qc = QuantumCircuit(2)\n"
    "qc.h(0)\n"
    "qc.cx(0, 1)\n"
    "qc.measure_all()\n"
    "result = StatevectorSampler().run([qc], shots=SHOTS).result()\n"
    "counts = result[0].data.meas.get_counts()\n",
    "measure_all() was used",
)
case(
    "13_migration",
    "counts-typed-in-by-hand",
    'counts = {"00": 1, "11": 2}',
    "Read the counts out of the result",
)

case(
    "14_real_hardware",
    "circuit-not-transpiled",
    "def to_isa(circuit, backend):\n    return circuit\n",
    "cannot execute",
)
case(
    "14_real_hardware",
    "measurement-forgotten",
    "def build_bell():\n    qc = QuantumCircuit(2)\n    qc.h(0)\n    qc.cx(0, 1)\n    return qc\n",
    "no measurement",
)
case(
    "14_real_hardware",
    "wrong-qubit-count",
    "def build_bell():\n"
    "    qc = QuantumCircuit(3)\n"
    "    qc.h(0)\n"
    "    qc.cx(0, 1)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "expected 2",
)
case(
    "14_real_hardware",
    "build-returns-nothing",
    "def build_bell():\n    return None\n",
    "expected a QuantumCircuit",
)
case(
    "14_real_hardware",
    "isa-returns-nothing",
    "def to_isa(circuit, backend):\n    return None\n",
    "to_isa() returned a NoneType",
)
case(
    "14_real_hardware",
    "not-a-function",
    "to_isa = 1",
    "should be a function",
)
case(
    "14_real_hardware",
    "native-gate-on-unconnected-qubits",
    # Every instruction here is one the device implements. The pair is the problem:
    # FakeManilaV2 is wired as a line, so qubits 0 and 2 are not neighbours.
    "def to_isa(circuit, backend):\n"
    "    qc = QuantumCircuit(5, 2)\n"
    "    qc.cx(0, 2)\n"
    "    qc.measure(0, 0)\n"
    "    qc.measure(2, 1)\n"
    "    return qc\n",
    "not between those qubits",
)
case(
    "14_real_hardware",
    "cx-dropped",
    "def build_bell():\n"
    "    qc = QuantumCircuit(2)\n"
    "    qc.h(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "does not prepare (|00> + |11>) / sqrt(2)",
)

case(
    "13_migration",
    "bell-broken-in-the-migration",
    "qc = QuantumCircuit(2, 2)\n"
    "qc.h(0)\n"
    "qc.measure(0, 0)\n"
    "qc.measure(1, 1)\n"
    "result = StatevectorSampler(seed=7).run([qc], shots=SHOTS).result()\n"
    "counts = result[0].data.c.get_counts()\n",
    "no longer prepares a Bell state",
)
case(
    "13_migration",
    "shot-count-changed",
    "result = StatevectorSampler(seed=7).run([qc], shots=SHOTS // 2).result()\n"
    "counts = result[0].data.c.get_counts()\n",
    "but this exercise asks for 1024 shots",
)

case(
    "14_real_hardware",
    "isa-of-an-unentangled-circuit",
    "def to_isa(circuit, backend):\n"
    "    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager\n"
    "    plain = QuantumCircuit(2)\n"
    "    plain.h(0)\n"
    "    plain.h(1)\n"
    "    plain.measure_all()\n"
    "    return generate_preset_pass_manager(optimization_level=1, backend=backend).run(plain)\n",
    "had the two qubits agreeing",
)
case(
    "14_real_hardware",
    "isa-that-always-answers-00",
    "def to_isa(circuit, backend):\n"
    "    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager\n"
    "    plain = QuantumCircuit(2)\n"
    "    plain.measure_all()\n"
    "    return generate_preset_pass_manager(optimization_level=1, backend=backend).run(plain)\n",
    "expected roughly half",
)

case(
    "15_honest_reading",
    "square-bracket-lookup",
    "def disagreement_rate(counts):\n"
    "    shots = sum(counts.values())\n"
    '    return (counts["01"] + counts["10"]) / shots\n',
    "raised KeyError",
)
case(
    "15_honest_reading",
    "hardcoded-rate",
    "def agreement_rate(counts):\n    return 0.5\n",
    "agreement_rate returned 0.5000",
)
case(
    "17_estimator",
    "square-bracket-lookup",
    "def z_from_counts(counts):\n"
    "    shots = sum(counts.values())\n"
    '    return (counts["0"] - counts["1"]) / shots\n',
    "raised KeyError",
)
case(
    "18_measurement_bases",
    "two-classical-registers",
    "def to_x_basis(qc):\n"
    "    from qiskit import ClassicalRegister\n"
    "    out = qc.copy()\n"
    "    out.h(0)\n"
    '    a, b = ClassicalRegister(1, "a"), ClassicalRegister(1, "b")\n'
    "    out.add_register(a)\n"
    "    out.add_register(b)\n"
    "    out.measure(0, a[0])\n"
    "    out.measure(0, b[0])\n"
    "    return out\n",
    "could not be sampled",
)

case(
    "15_honest_reading",
    "hardcoded-denominator",
    'def agreement_rate(counts):\n    return (counts.get("00", 0) + counts.get("11", 0)) / 1024\n',
    "4096 shots case",
)
case(
    "15_honest_reading",
    "disagreement-hardcoded",
    "def disagreement_rate(counts):\n    return 0.0\n",
    "disagreement_rate returned 0.0000",
)
case(
    "15_honest_reading",
    "rate-not-a-number",
    'def agreement_rate(counts):\n    return "most"\n',
    "expected a number",
)
case(
    "15_honest_reading",
    "explanation-invalid",
    'explanation = "gremlins"',
    "not one of the three options",
)
case(
    "15_honest_reading",
    "blamed-the-circuit",
    'explanation = "bug"',
    "Not a bug",
)
case(
    "15_honest_reading",
    "blamed-the-physics",
    'explanation = "physics"',
    "Not the physics",
)
case(
    "15_honest_reading",
    "not-a-function",
    "agreement_rate = 0.9",
    "should be a function",
)

case(
    "16_readout_repair",
    "prepare-ignores-the-left-bit",
    "def prepare(label):\n"
    "    qc = QuantumCircuit(2)\n"
    '    if label[1] == "1":\n'
    "        qc.x(0)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "does not prepare '10'",
)
case(
    "16_readout_repair",
    "prepare-without-measurement",
    "def prepare(label):\n"
    "    qc = QuantumCircuit(2)\n"
    '    if label[1] == "1":\n'
    "        qc.x(0)\n"
    '    if label[0] == "1":\n'
    "        qc.x(1)\n"
    "    return qc\n",
    "has no measurement",
)
case(
    "16_readout_repair",
    "prepare-returns-nothing",
    "def prepare(label):\n    return None\n",
    "expected a QuantumCircuit",
)
case(
    "16_readout_repair",
    "prepare-wrong-width",
    "def prepare(label):\n"
    "    qc = QuantumCircuit(3)\n"
    '    if label[1] == "1":\n'
    "        qc.x(0)\n"
    '    if label[0] == "1":\n'
    "        qc.x(1)\n"
    "    qc.measure_all()\n"
    "    return qc\n",
    "but should have 2",
)
case(
    "16_readout_repair",
    "corrected-values-not-numbers",
    "def corrected(matrix, counts):\n"
    "    observed = np.array([counts.get(x, 0) for x in LABELS], dtype=float)\n"
    "    true = np.linalg.solve(matrix, observed)\n"
    '    return {label: f"{v:.1f}" for label, v in zip(LABELS, true, strict=True)}\n',
    "expected a number",
)
case(
    "16_readout_repair",
    "matrix-left-as-none",
    "def response_matrix(columns):\n    return None\n",
    "Build and return the 4x4 array",
)
case(
    "16_readout_repair",
    "matrix-wrong-shape",
    "def response_matrix(columns):\n    return np.zeros((2, 2))\n",
    "expected (4, 4)",
)
case(
    "16_readout_repair",
    "matrix-transposed",
    "def response_matrix(columns):\n"
    "    matrix = np.zeros((len(LABELS), len(LABELS)))\n"
    "    for i, prepared in enumerate(LABELS):\n"
    "        counts = columns[prepared]\n"
    "        total = sum(counts.values())\n"
    "        for j, measured in enumerate(LABELS):\n"
    "            matrix[i, j] = counts.get(measured, 0) / total\n"
    "    return matrix\n",
    "right numbers the wrong way round",
)
case(
    "16_readout_repair",
    "columns-not-normalised",
    "def response_matrix(columns):\n"
    "    matrix = np.zeros((len(LABELS), len(LABELS)))\n"
    "    for j, prepared in enumerate(LABELS):\n"
    "        counts = columns[prepared]\n"
    "        for i, measured in enumerate(LABELS):\n"
    "            matrix[i, j] = counts.get(measured, 0)\n"
    "    return matrix\n",
    "should each add up to 1",
)
case(
    "16_readout_repair",
    "identity-instead-of-calibration",
    "def response_matrix(columns):\n    return np.eye(4)\n",
    "does not match the calibration counts",
)
case(
    "16_readout_repair",
    "corrected-left-as-none",
    "def corrected(matrix, counts):\n    return None\n",
    "Solve for the true distribution",
)
case(
    "16_readout_repair",
    "corrected-not-a-dict",
    "def corrected(matrix, counts):\n"
    "    observed = np.array([counts.get(x, 0) for x in LABELS], dtype=float)\n"
    "    return list(np.linalg.solve(matrix, observed))\n",
    "expected a dict",
)
case(
    "16_readout_repair",
    "corrected-drops-an-outcome",
    "def corrected(matrix, counts):\n"
    "    observed = np.array([counts.get(x, 0) for x in LABELS], dtype=float)\n"
    "    true = np.linalg.solve(matrix, observed)\n"
    "    return {label: float(v) for label, v in zip(LABELS[:3], true, strict=False)}\n",
    "left out the outcome(s)",
)
case(
    "16_readout_repair",
    "negatives-clamped-away",
    "def corrected(matrix, counts):\n"
    "    observed = np.array([counts.get(x, 0) for x in LABELS], dtype=float)\n"
    "    true = np.clip(np.linalg.solve(matrix, observed), 0.0, None)\n"
    "    return {label: float(v) for label, v in zip(LABELS, true, strict=True)}\n",
    "shots were taken",
)
case(
    "16_readout_repair",
    "an-invented-distribution-that-never-used-the-matrix",
    "def corrected(matrix, counts):\n"
    "    shots = sum(counts.values())\n"
    '    return {"00": shots / 2, "01": 0.0, "10": 0.0, "11": shots / 2}\n',
    "do not reproduce what the device reported",
)
case(
    "16_readout_repair",
    "correction-that-corrects-nothing",
    "def corrected(matrix, counts):\n"
    "    return {label: float(counts.get(label, 0)) for label in LABELS}\n",
    "not the improvement this method should give",
)
case(
    "16_readout_repair",
    "not-a-function",
    "corrected = 0",
    "should be a function",
)

# --------------------------------------------------------------------------
# Act IV
# --------------------------------------------------------------------------

case(
    "17_estimator",
    "observable-on-two-qubits",
    'observable_z = SparsePauliOp("ZZ")',
    "expected 1",
)
case(
    "17_estimator",
    "observable-is-x",
    'observable_z = SparsePauliOp("X")',
    "is not the Z observable",
)
case(
    "17_estimator",
    "expectation-hardcoded",
    "def expectation(circuit, observable):\n    return 1.0\n",
    "hardcoded rather than measured",
)
case(
    "17_estimator",
    "observable-ignored",
    "def expectation(circuit, observable):\n"
    "    result = StatevectorEstimator().run([(circuit, observable_z)]).result()\n"
    "    return float(result[0].data.evs)\n",
    "for <X> on |+>",
)
case(
    "17_estimator",
    "expectation-returns-nothing",
    "def expectation(circuit, observable):\n    return None\n",
    "which is not a number",
)
case(
    "17_estimator",
    "counts-not-divided-by-shots",
    'def z_from_counts(counts):\n    return counts.get("0", 0) - counts.get("1", 0)\n',
    "not a probability",
)
case(
    "17_estimator",
    "not-a-function",
    "z_from_counts = 0",
    "should be a function",
)

case(
    "18_measurement_bases",
    "observable-is-z",
    'observable_x = SparsePauliOp("Z")',
    "is not the X observable",
)
case(
    "18_measurement_bases",
    "observable-on-two-qubits",
    'observable_x = SparsePauliOp("XX")',
    "expected 1",
)
case(
    "18_measurement_bases",
    "coefficients-swapped",
    "def observable_at(theta):\n"
    '    return SparsePauliOp(["Z", "X"], coeffs=[math.sin(theta), math.cos(theta)])\n',
    "the Z coefficient is the cosine",
)
case(
    "18_measurement_bases",
    "observable-at-returns-nothing",
    "def observable_at(theta):\n    return None\n",
    "expected a SparsePauliOp",
)
case(
    "18_measurement_bases",
    "circuit-mutated-in-place",
    "def to_x_basis(circuit):\n    circuit.h(0)\n    circuit.measure_all()\n    return circuit\n",
    "changed the circuit it was given",
)
case(
    "18_measurement_bases",
    "rotation-without-measurement",
    "def to_x_basis(circuit):\n"
    "    rotated = circuit.copy()\n"
    "    rotated.h(0)\n"
    "    return rotated\n",
    "no classical register",
)
case(
    "18_measurement_bases",
    "measured-before-rotating",
    "def to_x_basis(circuit):\n"
    "    rotated = circuit.copy()\n"
    "    rotated.measure_all()\n"
    "    rotated.h(0)\n"
    "    return rotated\n",
    "measures before it rotates",
)
case(
    "18_measurement_bases",
    "wrong-rotation-gate",
    "def to_x_basis(circuit):\n"
    "    rotated = circuit.copy()\n"
    "    rotated.s(0)\n"
    "    rotated.measure_all()\n"
    "    return rotated\n",
    "map the X axis onto the Z axis",
)
case(
    "18_measurement_bases",
    "to-x-basis-returns-nothing",
    "def to_x_basis(circuit):\n    circuit.copy()\n    return None\n",
    "expected a QuantumCircuit",
)
case(
    "18_measurement_bases",
    "not-a-function",
    "observable_at = 1",
    "should be a function",
)

case(
    "19_bloch_sphere",
    "minus-y",
    'observable_y = SparsePauliOp("Y", coeffs=[-1])',
    "is minus Y rather than Y",
)
case(
    "19_bloch_sphere",
    "observable-is-x",
    'observable_y = SparsePauliOp("X")',
    "is not the Y observable",
)
case(
    "19_bloch_sphere",
    "observable-on-two-qubits",
    'observable_y = SparsePauliOp("YY")',
    "expected 1",
)
case(
    "19_bloch_sphere",
    "coordinates-reversed",
    "def bloch_vector(circuit):\n"
    "    return (\n"
    "        expectation(circuit, observable_z),\n"
    "        expectation(circuit, observable_y),\n"
    "        expectation(circuit, observable_x),\n"
    "    )\n",
    "the order is not",
)
case(
    "19_bloch_sphere",
    "y-is-really-z",
    "def bloch_vector(circuit):\n"
    "    return (\n"
    "        expectation(circuit, observable_x),\n"
    "        expectation(circuit, observable_z),\n"
    "        expectation(circuit, observable_z),\n"
    "    )\n",
    "looks like <Z> rather than <Y>",
)
case(
    "19_bloch_sphere",
    "vector-simply-wrong",
    "def bloch_vector(circuit):\n    return (0.0, 0.0, 0.0)\n",
    "Each coordinate is one expectation value",
)
case(
    "19_bloch_sphere",
    "vector-left-as-none",
    "def bloch_vector(circuit):\n    return None\n",
    "returned None",
)
case(
    "19_bloch_sphere",
    "only-two-coordinates",
    "def bloch_vector(circuit):\n"
    "    return (expectation(circuit, observable_x), expectation(circuit, observable_z))\n",
    "returned 2 numbers, expected 3",
)
case(
    "19_bloch_sphere",
    "vector-not-a-tuple",
    'def bloch_vector(circuit):\n    return "x y z"\n',
    "expected a tuple of three numbers",
)
case(
    "19_bloch_sphere",
    "a-string-among-the-numbers",
    'def bloch_vector(circuit):\n    return ("0", 0.0, 1.0)\n',
    "inside the tuple",
)
case(
    "19_bloch_sphere",
    "conjugate-forgotten",
    "def bloch_vector(circuit):\n"
    "    import numpy as _np\n"
    "    from qiskit.quantum_info import Statevector as _Statevector\n"
    "\n"
    "    a, b = _np.asarray(_Statevector(circuit).data)\n"
    "    return (\n"
    "        float(2 * (a * b).real),\n"
    "        float(2 * (a * b).imag),\n"
    "        float(abs(a) ** 2 - abs(b) ** 2),\n"
    "    )\n",
    "Adding a global phase moved the point",
)
case(
    "19_bloch_sphere",
    "half-angle-again",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.acos(max(-1.0, min(1.0, z / length))) / 2, math.atan2(y, x)\n",
    "half of it",
)
case(
    "19_bloch_sphere",
    "answered-in-degrees",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    theta = math.degrees(math.acos(max(-1.0, min(1.0, z / length))))\n"
    "    return theta, math.atan2(y, x)\n",
    "in degrees",
)
case(
    "19_bloch_sphere",
    "measured-up-from-the-equator",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.asin(max(-1.0, min(1.0, z / length))), math.atan2(y, x)\n",
    "measured up from the equator",
)
case(
    "19_bloch_sphere",
    "atan2-arguments-swapped",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.acos(max(-1.0, min(1.0, z / length))), math.atan2(x, y)\n",
    "math.atan2 takes y first",
)
case(
    "19_bloch_sphere",
    "azimuth-negated",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.acos(max(-1.0, min(1.0, z / length))), math.atan2(-y, x)\n",
    "the negative of",
)
case(
    "19_bloch_sphere",
    "polar-simply-wrong",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    theta = math.acos(max(-1.0, min(1.0, z / length))) + 0.3\n"
    "    return theta, math.atan2(y, x)\n",
    "The angle down from the north pole is arccos",
)
case(
    "19_bloch_sphere",
    "azimuth-simply-wrong",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.acos(max(-1.0, min(1.0, z / length))), math.atan2(y, x) + 0.7\n",
    "the shadow it casts on the equator",
)
case(
    "19_bloch_sphere",
    "acos-not-clamped",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.acos(z / length + 1e-9), math.atan2(y, x)\n",
    "raised ValueError",
)
case(
    "19_bloch_sphere",
    "angles-left-as-none",
    "def angles(vector):\n    return None\n",
    "Return the pair (theta, phi)",
)
case(
    "19_bloch_sphere",
    "three-angles-returned",
    "def angles(vector):\n    return (0.0, 0.0, 0.0)\n",
    "expected two numbers",
)
case(
    "19_bloch_sphere",
    "pair-the-wrong-way-round",
    "def angles(vector):\n"
    "    x, y, z = vector\n"
    "    length = math.sqrt(x * x + y * y + z * z)\n"
    "    return math.atan2(y, x) - math.pi, math.acos(max(-1.0, min(1.0, z / length)))\n",
    "outside 0 to pi",
)
case(
    "19_bloch_sphere",
    "a-string-among-the-angles",
    'def angles(vector):\n    return ("0", 0.0)\n',
    "inside the pair",
)
case(
    "19_bloch_sphere",
    "not-a-function",
    "angles = 0",
    "should be a function",
)

case(
    "20_chsh",
    "alice-and-bob-swapped",
    "def joint_observable(alice_angle, bob_angle):\n"
    "    return observable_at(alice_angle).tensor(observable_at(bob_angle))\n",
    "the wrong way round",
)
case(
    "20_chsh",
    "joint-returns-nothing",
    "def joint_observable(alice_angle, bob_angle):\n    return None\n",
    "expected a SparsePauliOp",
)
case(
    "20_chsh",
    "single-qubit-observable",
    "def joint_observable(alice_angle, bob_angle):\n    return observable_at(alice_angle)\n",
    "expected 2",
)
case(
    "20_chsh",
    "angles-ignored",
    'def joint_observable(alice_angle, bob_angle):\n    return SparsePauliOp("ZZ")\n',
    "is not the observable it should be",
)
case(
    "20_chsh",
    "correlation-hardcoded",
    "def correlation(alice_angle, bob_angle):\n    return 1.0\n",
    "E(a, b) works out to cos(a - b)",
)
case(
    "20_chsh",
    "correlation-returns-nothing",
    "def correlation(alice_angle, bob_angle):\n    return None\n",
    "which is not a number",
)
case(
    "20_chsh",
    "minus-on-the-wrong-term",
    "def chsh(a0, a1, b0, b1):\n"
    "    return (\n"
    "        correlation(a0, b0)\n"
    "        - correlation(a0, b1)\n"
    "        + correlation(a1, b0)\n"
    "        + correlation(a1, b1)\n"
    "    )\n",
    "the minus is on the wrong term",
)
case(
    "20_chsh",
    "every-term-added",
    "def chsh(a0, a1, b0, b1):\n"
    "    return (\n"
    "        correlation(a0, b0)\n"
    "        + correlation(a0, b1)\n"
    "        + correlation(a1, b0)\n"
    "        + correlation(a1, b1)\n"
    "    )\n",
    "all four terms added",
)
case(
    "20_chsh",
    "chsh-simply-wrong",
    "def chsh(a0, a1, b0, b1):\n    return 2.0\n",
    "Check the argument order",
)
case(
    "20_chsh",
    "chsh-returns-nothing",
    "def chsh(a0, a1, b0, b1):\n    return None\n",
    "which is not a number",
)
case(
    "20_chsh",
    "not-a-function",
    "chsh = 2.8",
    "should be a function",
)
case(
    "20_chsh",
    "chsh-ignores-its-angles",
    "def chsh(a0, a1, b0, b1):\n    return 2 * math.sqrt(2)\n",
    "work S out from the four angles it is handed",
)


# --------------------------------------------------------------------------
# Machinery
# --------------------------------------------------------------------------


def _load_check(exercise: Exercise) -> ModuleType:
    """Import an exercise's check.py under a name of its own."""
    name = f"qx_check_{exercise.slug}"
    spec = importlib.util.spec_from_file_location(name, exercise.check_file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _learner_module(source: str, path: Path) -> ModuleType:
    """Build the module a learner's file would have produced.

    Written to disk first: exercise 01 reads the file back, which is the one
    exception the suite allows to that rule.
    """
    path.write_text(source, encoding="utf-8")
    module = ModuleType("qx_wrong_answer")
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102
    return module


@pytest.mark.parametrize(
    ("slug", "name", "override", "fragment", "standalone"),
    CASES,
    ids=[f"{slug}-{name}" for slug, name, _, _, _ in CASES],
)
def test_a_wrong_answer_gets_the_diagnosis_it_earned(
    slug: str,
    name: str,
    override: str,
    fragment: str,
    standalone: bool,
    exercises: list[Exercise],
    tmp_path: Path,
) -> None:
    exercise = next(e for e in exercises if e.slug == slug)
    base = "" if standalone else exercise.solution_file.read_text(encoding="utf-8")
    module = _learner_module(f"{base}\n\n{override}\n", tmp_path / "exercise.py")

    with pytest.raises(CheckFailed) as excinfo:
        _load_check(exercise).check(module)

    said = f"{excinfo.value.message}\n{excinfo.value.detail or ''}"
    assert fragment in said, (
        f"{slug}/{name} was rejected, but not for the reason it should be:\n{said}"
    )


def test_every_exercise_has_diagnostics_of_its_own(exercises: list[Exercise]) -> None:
    """A new exercise must arrive with its wrong answers, not only its right one."""
    covered = {slug for slug, *_ in CASES}
    missing = sorted({e.slug for e in exercises} - covered)
    assert not missing, f"no diagnostic cases for: {missing}"
