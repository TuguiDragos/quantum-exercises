"""Local progress tracking. One JSON file at the repo root, never committed."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

STATE_FILENAME = ".qx-state.json"
SCHEMA_VERSION = 1

UNREADABLE_SUFFIX = ".unreadable"

# A separate file: the state file is replaced, and a lock on a replaced inode is lost.
LOCK_FILENAME = ".qx-state.lock"

if os.name == "nt":  # pragma: no cover - exercised only on Windows
    import msvcrt

    def _acquire(handle: int) -> None:
        # LK_LOCK retries ten times, then raises. The byte may lie past EOF.
        msvcrt.locking(handle, msvcrt.LK_LOCK, 1)

    def _release(handle: int) -> None:
        # LK_UNLCK works from the current position, so rewind first.
        os.lseek(handle, 0, os.SEEK_SET)
        msvcrt.locking(handle, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _acquire(handle: int) -> None:
        fcntl.flock(handle, fcntl.LOCK_EX)

    def _release(handle: int) -> None:
        fcntl.flock(handle, fcntl.LOCK_UN)


Status = Literal["todo", "done", "solved"]


@dataclass
class ExerciseState:
    status: Status = "todo"
    hints_revealed: int = 0
    completed_at: str | None = None
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
        # Revealing the answer is not undone by passing later.
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
        """Advance the hint counter and return how many hints are visible, capped at ``total``."""
        entry = self.get(slug)
        if entry.hints_revealed < total:
            entry.hints_revealed += 1
        return min(entry.hints_revealed, total)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(root: Path) -> Path:
    return root / STATE_FILENAME


def _readable_exercises(raw: object) -> dict | None:
    """The exercises mapping from a parsed state file, or None if unreadable.

    The single definition of "readable" shared by load() and _preserve_unreadable().
    """
    if not isinstance(raw, dict) or raw.get("version") != SCHEMA_VERSION:
        return None
    entries = raw.get("exercises")
    if entries is None:
        return {}
    return entries if isinstance(entries, dict) else None


def load(root: Path) -> State:
    """Read state, treating any corruption as a fresh start rather than a crash."""
    path = state_path(root)
    if not path.is_file():
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return State()
    entries = _readable_exercises(raw)
    if entries is None:
        return State()

    exercises: dict[str, ExerciseState] = {}
    for slug, entry in entries.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status", "todo")
        if status not in ("todo", "done", "solved"):
            status = "todo"
        hints = entry.get("hints_revealed", 0)
        # bool is a subclass of int, so reject `true` explicitly.
        readable_hints = isinstance(hints, int) and not isinstance(hints, bool) and hints >= 0
        completed_at = entry.get("completed_at")
        ran_on = entry.get("ran_on")
        exercises[str(slug)] = ExerciseState(
            status=status,
            hints_revealed=int(hints) if readable_hints else 0,
            completed_at=completed_at if isinstance(completed_at, str) else None,
            ran_on=ran_on if isinstance(ran_on, str) else None,
        )
    return State(version=SCHEMA_VERSION, exercises=exercises)


def unreadable(root: Path) -> bool:
    """Whether a state file exists that this version cannot read, so callers can warn."""
    path = state_path(root)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True
    return _readable_exercises(raw) is None


def _preserve_unreadable(path: Path) -> Path | None:
    """Copy aside a state file this version cannot read before it is overwritten."""
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raw = None
    if _readable_exercises(raw) is not None:
        return None

    backup = path.with_name(path.name + UNREADABLE_SUFFIX)
    with contextlib.suppress(OSError):
        shutil.copyfile(path, backup)
        return backup
    return None  # pragma: no cover - only when the copy itself fails


def lock_path(root: Path) -> Path:
    return root / LOCK_FILENAME


def _open_lock(root: Path) -> int | None:
    """Take the lock, or return None when this filesystem will not give it."""
    try:
        # Some systems need a writable descriptor for an exclusive flock.
        handle = os.open(lock_path(root), os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        return None
    try:
        _acquire(handle)
    except OSError:
        os.close(handle)
        return None
    return handle


def _close_lock(handle: int) -> None:
    with contextlib.suppress(OSError):
        _release(handle)
    with contextlib.suppress(OSError):
        os.close(handle)


@contextlib.contextmanager
def locked(root: Path) -> Iterator[None]:
    """Hold the progress file for a whole read-modify-write, across qx processes.

    If the lock is unavailable (read-only clone, some network mounts), proceed
    unlocked rather than refuse to record progress.
    """
    handle = _open_lock(root)
    if handle is None:
        yield
        return
    try:
        yield
    finally:
        _close_lock(handle)


def save(root: Path, state: State) -> Path | None:
    """Write atomically so an interrupted run cannot leave a half-written file.

    Returns the path an unreadable previous file was copied to, or None when there
    was nothing to preserve.
    """
    path = state_path(root)
    preserved = _preserve_unreadable(path)
    payload = json.dumps(asdict(state), indent=2, sort_keys=True) + "\n"

    # Not a context manager: the file must outlive the block for os.replace.
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
    "LOCK_FILENAME",
    "STATE_FILENAME",
    "UNREADABLE_SUFFIX",
    "ExerciseState",
    "State",
    "Status",
    "load",
    "lock_path",
    "locked",
    "save",
    "state_path",
    "unreadable",
]
