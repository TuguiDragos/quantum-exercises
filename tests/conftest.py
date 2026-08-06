"""Shared fixtures.

Every test runs with QX_OFFLINE set. Without it, the hardware exercise would
submit a real job to whatever IBM account happens to be saved on the machine
running the suite, spending someone's quota.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from quantum_exercises.backends import OFFLINE_ENV
from quantum_exercises.registry import Exercise, find_project_root, load_exercises

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def force_offline() -> None:
    os.environ[OFFLINE_ENV] = "1"


@pytest.fixture(scope="session")
def root() -> Path:
    return find_project_root(ROOT)


@pytest.fixture(scope="session")
def exercises(root: Path) -> list[Exercise]:
    return load_exercises(root)


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Give tests that ask for `exercise` one case per exercise on disk."""
    if "exercise" not in metafunc.fixturenames:
        return
    found = load_exercises(find_project_root(ROOT))
    metafunc.parametrize("exercise", found, ids=[e.slug for e in found])
