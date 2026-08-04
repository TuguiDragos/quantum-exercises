"""Project metadata that is easy to update in one place and forget in another."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

import quantum_exercises

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib


@pytest.fixture(scope="module")
def pyproject(root: Path) -> dict:
    with (root / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_version_agrees_across_every_file(pyproject: dict, root: Path) -> None:
    """Three files carry the version. They drift the moment one is forgotten."""
    declared = pyproject["project"]["version"]

    assert quantum_exercises.__version__ == declared, (
        "src/quantum_exercises/__init__.py disagrees with pyproject.toml"
    )

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)\s*$", citation, re.MULTILINE)
    assert match is not None, "CITATION.cff has no version field"
    assert match.group(1) == declared, "CITATION.cff disagrees with pyproject.toml"


def test_changelog_documents_the_current_version(pyproject: dict, root: Path) -> None:
    declared = pyproject["project"]["version"]
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{declared}]" in changelog, f"CHANGELOG.md has no entry for {declared}"


def test_entry_point_is_importable(pyproject: dict) -> None:
    """`qx` must resolve to something callable, or the console script is dead."""
    target = pyproject["project"]["scripts"]["qx"]
    module_name, _, attribute = target.partition(":")

    module = __import__(module_name, fromlist=[attribute])
    assert callable(getattr(module, attribute))


def test_python_floor_matches_the_pinned_interpreter(pyproject: dict, root: Path) -> None:
    """.python-version must satisfy requires-python, or `uv sync` picks a bad one."""
    requires = pyproject["project"]["requires-python"]
    pinned = (root / ".python-version").read_text(encoding="utf-8").strip()

    floor = tuple(int(part) for part in requires.removeprefix(">=").split("."))
    chosen = tuple(int(part) for part in pinned.split(".")[:2])
    assert chosen >= floor, f".python-version is {pinned}, below requires-python {requires}"
