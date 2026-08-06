"""Progress file behaviour, including the ways it can be damaged."""

from __future__ import annotations

import json
from pathlib import Path

from quantum_exercises import state as state_module


def test_missing_file_gives_empty_state(tmp_path: Path) -> None:
    assert state_module.load(tmp_path).exercises == {}


def test_round_trip(tmp_path: Path) -> None:
    state = state_module.State()
    state.mark_done("01_environment")
    state.reveal_hint("02_dictionaries", total=3)
    state_module.save(tmp_path, state)

    reloaded = state_module.load(tmp_path)
    assert reloaded.get("01_environment").status == "done"
    assert reloaded.get("01_environment").completed_at is not None
    assert reloaded.get("02_dictionaries").hints_revealed == 1


def test_solved_survives_a_later_pass(tmp_path: Path) -> None:
    """Revealing the answer is not undone by passing the check afterwards."""
    state = state_module.State()
    state.mark_solved("03_first_circuit")
    state.mark_done("03_first_circuit")
    assert state.get("03_first_circuit").status == "solved"


def test_hint_counter_stops_at_the_total(tmp_path: Path) -> None:
    state = state_module.State()
    for _ in range(10):
        state.reveal_hint("01_environment", total=3)
    assert state.get("01_environment").hints_revealed == 3


def test_reset_clears_everything_for_one_exercise(tmp_path: Path) -> None:
    state = state_module.State()
    state.mark_solved("01_environment")
    state.reveal_hint("01_environment", total=3)
    state.mark_done("02_dictionaries")

    state.reset("01_environment")

    assert state.get("01_environment").status == "todo"
    assert state.get("01_environment").hints_revealed == 0
    assert state.get("02_dictionaries").status == "done"


def test_corrupt_file_is_treated_as_empty(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text("{not json at all", encoding="utf-8")
    assert state_module.load(tmp_path).exercises == {}


def test_unknown_schema_version_is_discarded(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text(
        json.dumps({"version": 999, "exercises": {"01_environment": {"status": "done"}}}),
        encoding="utf-8",
    )
    assert state_module.load(tmp_path).exercises == {}


def test_invalid_status_falls_back_to_todo(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text(
        json.dumps(
            {
                "version": state_module.SCHEMA_VERSION,
                "exercises": {"01_environment": {"status": "banana", "hints_revealed": -5}},
            }
        ),
        encoding="utf-8",
    )
    entry = state_module.load(tmp_path).get("01_environment")
    assert entry.status == "todo"
    assert entry.hints_revealed == 0


def test_save_leaves_no_temporary_files(tmp_path: Path) -> None:
    state = state_module.State()
    state.mark_done("01_environment")
    state_module.save(tmp_path, state)
    leftovers = [p.name for p in tmp_path.iterdir() if p.name.startswith(".qx-state-")]
    assert leftovers == []


def test_ran_on_is_recorded(tmp_path: Path) -> None:
    state = state_module.State()
    state.mark_done("11_real_hardware", ran_on="hardware")
    state_module.save(tmp_path, state)
    assert state_module.load(tmp_path).get("11_real_hardware").ran_on == "hardware"
