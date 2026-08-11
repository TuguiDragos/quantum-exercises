"""Progress file behaviour, including the ways it can be damaged."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("status", ["todo", "done", "solved"])
@pytest.mark.parametrize("hints", [0, 1, 3])
@pytest.mark.parametrize("ran_on", [None, "hardware", "noisy_simulator", "simulator"])
def test_every_state_a_run_can_produce_survives_the_round_trip(
    tmp_path: Path, status: str, hints: int, ran_on: str | None
) -> None:
    """Saving and loading must return what went in, for every combination qx writes.

    The file is the only memory the tool has, so a field that does not survive is
    progress quietly lost.
    """
    state = state_module.State()
    entry = state.get("07_probe")
    entry.status = status
    entry.hints_revealed = hints
    entry.ran_on = ran_on
    entry.completed_at = None if status == "todo" else "2026-08-11T09:00:00+00:00"

    state_module.save(tmp_path, state)
    reloaded = state_module.load(tmp_path).get("07_probe")

    assert reloaded == entry


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


def test_a_counter_larger_than_the_hints_is_capped(tmp_path: Path) -> None:
    """The caller indexes a list with this number, so it must never exceed its length.

    Reached without anyone editing anything: reveal all three hints of an exercise,
    then let the exercise lose one. `qx hint` printed two panels and then raised
    IndexError on the third.
    """
    state = state_module.State()
    state.get("01_environment").hints_revealed = 99
    assert state.reveal_hint("01_environment", total=3) == 3
    assert state.reveal_hint("01_environment", total=0) == 0


def test_a_boolean_hint_counter_reads_as_none_revealed(tmp_path: Path) -> None:
    """bool is a subclass of int, so `true` used to mean one hint had been seen."""
    state_module.state_path(tmp_path).write_text(
        json.dumps(
            {
                "version": state_module.SCHEMA_VERSION,
                "exercises": {"01_environment": {"status": "todo", "hints_revealed": True}},
            }
        ),
        encoding="utf-8",
    )
    assert state_module.load(tmp_path).get("01_environment").hints_revealed == 0


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


@pytest.mark.parametrize("value", [{"a": 1}, ["hardware"], 3, True])
def test_a_ran_on_that_is_not_a_string_is_dropped(tmp_path: Path, value) -> None:
    """`qx list` looks this value up in a dict, so an unhashable one raised there.

    load() promises corruption becomes a fresh start rather than a crash, and both
    of these fields used to be taken exactly as written.
    """
    state_module.state_path(tmp_path).write_text(
        json.dumps(
            {
                "version": state_module.SCHEMA_VERSION,
                "exercises": {"14_real_hardware": {"status": "done", "ran_on": value}},
            }
        ),
        encoding="utf-8",
    )
    assert state_module.load(tmp_path).get("14_real_hardware").ran_on is None


def test_a_completed_at_that_is_not_a_string_is_dropped(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text(
        json.dumps(
            {
                "version": state_module.SCHEMA_VERSION,
                "exercises": {"01_environment": {"status": "done", "completed_at": 5}},
            }
        ),
        encoding="utf-8",
    )
    assert state_module.load(tmp_path).get("01_environment").completed_at is None


def test_ran_on_is_recorded(tmp_path: Path) -> None:
    state = state_module.State()
    state.mark_done("11_real_hardware", ran_on="hardware")
    state_module.save(tmp_path, state)
    assert state_module.load(tmp_path).get("11_real_hardware").ran_on == "hardware"


@pytest.mark.parametrize("value", ["nope", 123, True, [1, 2]])
def test_state_load_survives_a_wrong_typed_exercises_key(tmp_path: Path, value) -> None:
    """load() promises corruption is a fresh start, never a crash."""
    state_module.state_path(tmp_path).write_text(
        json.dumps({"version": state_module.SCHEMA_VERSION, "exercises": value}),
        encoding="utf-8",
    )
    assert state_module.load(tmp_path).exercises == {}


def test_state_load_skips_a_non_dict_entry(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text(
        json.dumps(
            {
                "version": state_module.SCHEMA_VERSION,
                "exercises": {"01_environment": "wrong", "02_dictionaries": {"status": "done"}},
            }
        ),
        encoding="utf-8",
    )
    loaded = state_module.load(tmp_path)
    assert loaded.get("01_environment").status == "todo"
    assert loaded.get("02_dictionaries").status == "done"


@pytest.mark.parametrize("payload", ['{"version": 1}', '{"version": 1, "exercises": null}'])
def test_a_file_with_nothing_recorded_is_readable(tmp_path: Path, payload: str) -> None:
    """No exercises key at all is empty progress, not corruption worth preserving."""
    state_module.state_path(tmp_path).write_text(payload, encoding="utf-8")
    assert state_module.load(tmp_path).exercises == {}
    assert state_module.save(tmp_path, state_module.State()) is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("{ not json", True),
        ('{"version": 999, "exercises": {}}', True),
        ('{"version": 1, "exercises": "wrong"}', True),
        ('{"version": 1, "exercises": {}}', False),
        ('{"version": 1}', False),
    ],
)
def test_unreadable_reports_what_load_silently_discards(
    tmp_path: Path, payload: str, expected: bool
) -> None:
    """load() starts fresh on a damaged file, and used to do it without a word.

    Saving already says so. Reading did not, so every exercise came back as
    unfinished and nothing on screen explained it.
    """
    state_module.state_path(tmp_path).write_text(payload, encoding="utf-8")
    assert state_module.unreadable(tmp_path) is expected


def test_a_missing_state_file_is_not_unreadable(tmp_path: Path) -> None:
    """Nothing recorded yet is the ordinary case, not damage."""
    assert state_module.unreadable(tmp_path) is False


def test_unparseable_json_is_preserved_before_being_replaced(tmp_path: Path) -> None:
    state_module.state_path(tmp_path).write_text("{ not json", encoding="utf-8")
    preserved = state_module.save(tmp_path, state_module.State())
    assert preserved is not None
    assert preserved.read_text(encoding="utf-8") == "{ not json"


def test_save_preserves_an_unreadable_file(tmp_path: Path) -> None:
    path = state_module.state_path(tmp_path)
    path.write_text(json.dumps({"version": 999, "exercises": {}}), encoding="utf-8")
    preserved = state_module.save(tmp_path, state_module.State())
    assert preserved is not None and preserved.exists()
    assert json.loads(preserved.read_text(encoding="utf-8"))["version"] == 999


def test_save_cleans_up_when_the_write_fails(tmp_path: Path, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(state_module.os, "replace", boom)
    with pytest.raises(OSError):
        state_module.save(tmp_path, state_module.State())
    assert [p for p in tmp_path.iterdir() if p.name.startswith(".qx-state-")] == []


class TestLocking:
    """The lock exists because the read-modify-write around the write was not atomic."""

    def test_lock_file_is_created_and_kept(self, tmp_path: Path) -> None:
        with state_module.locked(tmp_path):
            pass
        assert state_module.lock_path(tmp_path).is_file()

    def test_the_lock_is_released_afterwards(self, tmp_path: Path) -> None:
        for _ in range(3):
            with state_module.locked(tmp_path):
                pass

    def test_an_exception_inside_still_releases(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError), state_module.locked(tmp_path):
            raise ValueError("boom")
        with state_module.locked(tmp_path):
            pass

    def test_a_filesystem_that_refuses_the_lock_still_records(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Losing progress is worse than recording it unserialised."""

        def refuse(handle: int) -> None:
            raise OSError("flock not supported here")

        monkeypatch.setattr(state_module, "_acquire", refuse)
        with state_module.locked(tmp_path):
            state = state_module.State()
            state.mark_done("01_environment")
            state_module.save(tmp_path, state)
        assert state_module.load(tmp_path).is_complete("01_environment")

    def test_a_root_that_cannot_hold_the_lock_file_still_yields(self, tmp_path: Path) -> None:
        missing = tmp_path / "not-there"
        with state_module.locked(missing):
            pass
        assert not missing.exists()

    def test_concurrent_updates_do_not_erase_each_other(self, tmp_path: Path) -> None:
        """The regression test for the defect: eight writers, eight entries.

        Without the lock this lost roughly one entry every other run.
        """
        import subprocess
        import sys
        import textwrap

        writer = textwrap.dedent(
            """
            import sys
            from pathlib import Path
            from quantum_exercises.state import load, locked, save

            root, slug = Path(sys.argv[1]), sys.argv[2]
            with locked(root):
                state = load(root)
                state.mark_done(slug)
                save(root, state)
            """
        )
        slugs = [f"{n:02d}_probe" for n in range(1, 9)]
        processes = [
            subprocess.Popen([sys.executable, "-c", writer, str(tmp_path), slug]) for slug in slugs
        ]
        for process in processes:
            assert process.wait(timeout=60) == 0

        recorded = state_module.load(tmp_path)
        assert sorted(recorded.exercises) == sorted(slugs)
