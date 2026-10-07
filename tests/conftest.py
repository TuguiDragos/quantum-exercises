"""Shared fixtures. QX_OFFLINE is set for every test so no real IBM job is submitted."""

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
    """Render at a fixed 80 columns, whatever terminal runs the suite.

    A fresh console, because rich caches its width on first render. It has no file
    of its own, so it still follows the stdout a CliRunner installs.
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
