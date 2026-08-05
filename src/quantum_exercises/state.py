"""Local progress tracking. One JSON file at the repo root, never committed."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

STATE_FILENAME = ".qx-state.json"
SCHEMA_VERSION = 1

# Where a state file this version cannot read is copied before being replaced.
UNREADABLE_SUFFIX = ".unreadable"

Status = Literal["todo", "done", "solved"]


@dataclass
class ExerciseState:
    status: Status = "todo"
    hints_revealed: int = 0
    completed_at: str | None = None
    # Set for the hardware exercise so `qx list` can say simulator versus QPU.
    ran_on: str | None = None


@dataclass
class State:
    version: int = SCHEMA_VERSION
    exercises: dict[str, ExerciseState] = field(default_factory=dict)

    def get(self, slug: str) -> ExerciseState:
        return self.exercises.setdefault(slug, ExerciseState())

    def is_complete(self, slug: str) -> bool:
        return self.get(slug).status in ("done", "solved")

    def mark_done(self, slug: str, *, ran_on: str | None = None) -> None:
        entry = self.get(slug)
        # A solved exercise stays solved: revealing the answer is not undone by
        # later passing the check.
        if entry.status != "solved":
            entry.status = "done"
        entry.completed_at = _now()
        if ran_on:
            entry.ran_on = ran_on

    def mark_solved(self, slug: str) -> None:
        entry = self.get(slug)
        entry.status = "solved"
        entry.completed_at = _now()

    def reset(self, slug: str) -> None:
        self.exercises[slug] = ExerciseState()

    def reveal_hint(self, slug: str, total: int) -> int:
        """Advance the hint counter and return the 1-based index now visible."""
        entry = self.get(slug)
        if entry.hints_revealed < total:
            entry.hints_revealed += 1
        return entry.hints_revealed


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(root: Path) -> Path:
    return root / STATE_FILENAME


def load(root: Path) -> State:
    """Read state, treating any corruption as a fresh start rather than a crash."""
    path = state_path(root)
    if not path.is_file():
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return State()
    if not isinstance(raw, dict) or raw.get("version") != SCHEMA_VERSION:
        return State()

    exercises: dict[str, ExerciseState] = {}
    for slug, entry in (raw.get("exercises") or {}).items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "todo")
        if status not in ("todo", "done", "solved"):
            status = "todo"
        hints = entry.get("hints_revealed", 0)
        exercises[str(slug)] = ExerciseState(
            status=status,
            hints_revealed=int(hints) if isinstance(hints, int) and hints >= 0 else 0,
            completed_at=entry.get("completed_at"),
            ran_on=entry.get("ran_on"),
        )
    return State(version=SCHEMA_VERSION, exercises=exercises)


def _preserve_unreadable(path: Path) -> Path | None:
    """Copy aside a state file this version cannot read, and say where it went.

    Treating an unknown schema version or a corrupt file as a fresh start is the
    right call for reading. Writing over it afterwards was not: running a newer qx
    once and then an older one destroyed every recorded exercise, permanently and
    with nothing on screen to say it had happened.
    """
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raw = None
    if isinstance(raw, dict) and raw.get("version") == SCHEMA_VERSION:
        return None

    backup = path.with_name(path.name + UNREADABLE_SUFFIX)
    with contextlib.suppress(OSError):
        shutil.copyfile(path, backup)
        return backup
    return None  # pragma: no cover - only when the copy itself fails


def save(root: Path, state: State) -> Path | None:
    """Write atomically so an interrupted run cannot leave a half-written file.

    Returns the path an unreadable previous file was copied to, or None when there
    was nothing to preserve.
    """
    path = state_path(root)
    preserved = _preserve_unreadable(path)
    payload = json.dumps(asdict(state), indent=2, sort_keys=True) + "\n"

    # Not a context manager: the file has to outlive the block so os.replace can
    # move it into place, which is what makes the write atomic.
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".qx-state-",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise
    return preserved


__all__ = [
    "STATE_FILENAME",
    "UNREADABLE_SUFFIX",
    "ExerciseState",
    "State",
    "Status",
    "load",
    "save",
    "state_path",
]
