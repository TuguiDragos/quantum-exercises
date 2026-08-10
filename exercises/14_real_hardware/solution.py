"""Exercise 14 - reference solution."""

from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager


def build_bell() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    return qc


def to_isa(circuit: QuantumCircuit, backend) -> QuantumCircuit:
    pass_manager = generate_preset_pass_manager(optimization_level=1, backend=backend)
    return pass_manager.run(circuit)
