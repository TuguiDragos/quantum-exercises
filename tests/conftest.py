"""Shared fixtures.

Every test runs with QX_OFFLINE set. Without it, the hardware exercise would
submit a real job to whatever IBM account happens to be saved on the machine
running the suite, spending someone's quota.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from rich.console import Console
from rich.theme import Theme

from quantum_exercises import theme, ui
from quantum_exercises.backends import OFFLINE_ENV
from quantum_exercises.registry import Exercise, find_project_root, load_exercises

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session", autouse=True)
def force_offline() -> None:
    os.environ[OFFLINE_ENV] = "1"


@pytest.fixture(autouse=True)
def fixed_console_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Read every rendered assertion at one width, whatever terminal ran the suite.

    rich sizes itself to the terminal it finds. Tables truncate their cells to
    fit and prose wraps at a different word, so tests that assert on what the
    tool said passed in a full window and failed in a narrow pane, reporting a
    missing string rather than a width. Eighty columns is what the output is
    designed for and what CI renders at.

    A replacement console rather than a width set on the real one. rich settles
    its width the first time it renders and keeps it, so the COLUMNS variable is
    too late by then, and assigning `console.width` goes through a property whose
    getter has already resolved the terminal, which leaves monkeypatch restoring
    a fixed number onto the shared console for the rest of the session. Built
    with no file of its own, so it still follows the stdout a CliRunner installs.
    """
    monkeypatch.setattr(
        ui, "console", Console(width=80, highlight=False, theme=Theme(theme.RICH_OVERRIDES))
    )


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
