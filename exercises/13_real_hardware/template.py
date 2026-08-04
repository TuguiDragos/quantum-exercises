"""Exercise 13 - a Bell state on a real machine.

Fill in the TODOs, then run:  uv run qx run 13
"""

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager


def build_bell() -> QuantumCircuit:
    """Return a two-qubit Bell circuit, including its measurement.

    Same two gates as exercise 11, but this time the measurement belongs in the
    circuit: hardware has no statevector to inspect, only counts.
    """
    qc = QuantumCircuit(2)
    # TODO: add the two gates, then the measurement.
    return qc


def to_isa(circuit: QuantumCircuit, backend) -> QuantumCircuit:
    """Rewrite `circuit` into the instruction set of `backend`.

    Two steps:
      1. build a pass manager for this backend with generate_preset_pass_manager,
         passing optimization_level=1 and backend=backend
      2. run the circuit through it, and return what comes back
    """
    # TODO: replace this. Returning the circuit untouched is exactly the mistake
    #       that gets a job rejected by a real QPU.
    return circuit
