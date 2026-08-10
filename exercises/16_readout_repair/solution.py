"""Exercise 16 - reference solution."""

import numpy as np
from qiskit import QuantumCircuit

LABELS = ("00", "01", "10", "11")


def prepare(label):
    """Given in exercise.py: exercise 11's endianness rule, nothing more."""
    qc = QuantumCircuit(2)
    if label[1] == "1":
        qc.x(0)
    if label[0] == "1":
        qc.x(1)
    qc.measure_all()
    return qc


def response_matrix(columns):
    matrix = np.zeros((len(LABELS), len(LABELS)))
    for j, prepared in enumerate(LABELS):
        counts = columns[prepared]
        total = sum(counts.values())
        for i, measured in enumerate(LABELS):
            matrix[i, j] = counts.get(measured, 0) / total
    return matrix


def corrected(matrix, counts):
    observed = np.array([counts.get(label, 0) for label in LABELS], dtype=float)
    # solve rather than inv: same answer, better conditioned, one step instead of two.
    true = np.linalg.solve(matrix, observed)
    return {label: float(value) for label, value in zip(LABELS, true, strict=True)}
