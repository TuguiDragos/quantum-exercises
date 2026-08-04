"""The playground notebook.

A notebook that is never executed rots quietly. These tests run every code cell,
so a Qiskit change that breaks the notebook fails CI like anything else.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

NOTEBOOK = Path("notebooks/playground.ipynb")


@pytest.fixture(scope="module")
def notebook(root: Path) -> dict:
    path = root / NOTEBOOK
    assert path.is_file(), f"{NOTEBOOK} is missing"
    return json.loads(path.read_text(encoding="utf-8"))


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


def test_every_code_cell_runs(notebook: dict, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import matplotlib

    # Headless: the notebook draws figures and there is no display in CI.
    matplotlib.use("Agg")
    monkeypatch.chdir(root)

    namespace: dict = {"__name__": "__notebook__"}
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        try:
            exec(compile(source, f"<cell {index}>", "exec"), namespace)  # noqa: S102
        except Exception as exc:  # noqa: BLE001 - reported with the offending cell
            pytest.fail(f"cell {index} failed: {type(exc).__name__}: {exc}\n\n{source}")
