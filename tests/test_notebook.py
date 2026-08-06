"""Every notebook under notebooks/.

A notebook that is never executed rots quietly. These tests run every code cell of
every notebook, so a Qiskit change that breaks one fails CI like anything else.

Parametrised over the directory rather than naming a single file. The labs were
added after the playground, and a test that only knew about the playground would
have let them rot while still reporting green.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NOTEBOOKS_DIR = "notebooks"

# Named so that deleting or renaming one is a failure rather than a silent drop
# from the suite, which is the way this kind of test usually stops working.
EXPECTED = frozenset(
    {"playground", "lab-1-qiskit-patterns", "lab-2-noise", "lab-3-dynamic-circuits"}
)


def _notebook_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / NOTEBOOKS_DIR).glob("*.ipynb")
        if ".ipynb_checkpoints" not in path.parts
    )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """One case per notebook on disk, named after the file."""
    if "notebook_path" not in metafunc.fixturenames:
        return
    from quantum_exercises.registry import find_project_root

    found = _notebook_paths(find_project_root(Path(__file__).resolve().parent.parent))
    metafunc.parametrize("notebook_path", found, ids=[path.stem for path in found])


@pytest.fixture
def notebook(notebook_path: Path) -> dict:
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def test_every_expected_notebook_is_present(root: Path) -> None:
    names = {path.stem for path in _notebook_paths(root)}
    assert names >= EXPECTED, f"missing from {NOTEBOOKS_DIR}/: {sorted(EXPECTED - names)}"


def test_is_a_valid_notebook(notebook: dict) -> None:
    assert notebook["nbformat"] == 4
    assert notebook["cells"]
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"


def test_carries_no_outputs(notebook: dict) -> None:
    """What nbstripout exists to guarantee: no stored outputs, no stray job ids."""
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        assert cell["outputs"] == [], f"cell {index} has stored output"
        assert cell["execution_count"] is None, f"cell {index} has an execution count"


def test_opens_with_a_title(notebook: dict) -> None:
    """The first cell names the notebook, so it does not open as a wall of code."""
    first = notebook["cells"][0]
    assert first["cell_type"] == "markdown"
    assert "".join(first["source"]).lstrip().startswith("# ")


def test_every_code_cell_runs(
    notebook: dict, notebook_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib

    # Headless: the notebooks draw figures and there is no display in CI.
    matplotlib.use("Agg")
    monkeypatch.chdir(root)

    name = notebook_path.name
    namespace: dict = {"__name__": "__notebook__"}
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        try:
            exec(compile(source, f"<{name} cell {index}>", "exec"), namespace)  # noqa: S102
        except Exception as exc:  # noqa: BLE001 - reported with the offending cell
            pytest.fail(f"{name} cell {index} failed: {type(exc).__name__}: {exc}\n\n{source}")
