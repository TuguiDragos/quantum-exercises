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

# Where a state file this version cannot read is copied before being replaced.
UNREADABLE_SUFFIX = ".unreadable"

# Guards the read-modify-write below. Its own file, because the state file is
# replaced rather than written in place, and a lock on a replaced inode is lost.
LOCK_FILENAME = ".qx-state.lock"

if os.name == "nt":  # pragma: no cover - exercised only on Windows
    import msvcrt

    def _acquire(handle: int) -> None:
        # LK_LOCK retries once a second, ten times, then raises. Locking one byte
        # is enough: the region may extend past the end of an empty file.
        msvcrt.locking(handle, msvcrt.LK_LOCK, 1)

    def _release(handle: int) -> None:
        # LK_UNLCK unlocks from the current position, so rewind to what was locked.
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
        """Advance the hint counter and return how many hints are now visible.

        Never more than there are. The caller indexes a list with this, and a
        counter larger than the list crashed it with an IndexError. That happened
        to anyone who had revealed every hint of an exercise that later lost one,
        with nothing edited by hand.
        """
        entry = self.get(slug)
        if entry.hints_revealed < total:
            entry.hints_revealed += 1
        return min(entry.hints_revealed, total)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(root: Path) -> Path:
    return root / STATE_FILENAME


def _readable_exercises(raw: object) -> dict | None:
    """The exercises mapping out of a parsed state file, or None if unreadable.

    One definition of "readable" for both callers below. load() turns None into a
    fresh start, and _preserve_unreadable() copies the file aside before it is
    overwritten. They used to disagree: a file whose `exercises` key held a string
    rather than an object passed the version check, so it was destroyed without a
    backup, and reading it raised AttributeError instead of starting fresh.

    A missing or null `exercises` key is readable and simply means nothing has been
    recorded yet, so it is not worth preserving.
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
        # bool is a subclass of int, so `true` would have counted as one revealed
        # hint. Registry rejects it the same way for timeout.
        readable_hints = isinstance(hints, int) and not isinstance(hints, bool) and hints >= 0
        # Both fields are declared str or None and both used to be taken as read.
        # `qx list` looks ran_on up in a dict, so a value of any unhashable type
        # raised TypeError there rather than starting fresh the way load promises.
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
    """Whether a state file exists that this version cannot read.

    load() turns that into a fresh start, which is the right call, but it is a
    silent one: every exercise came back as unfinished with nothing on screen to
    say why, and the file still sitting there intact. Saving already warns; this
    lets reading do the same.
    """
    path = state_path(root)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True
    return _readable_exercises(raw) is None


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
        # O_RDWR, not O_RDONLY: an exclusive flock needs a writable descriptor on
        # some systems, even though macOS allows it either way.
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

    The write itself was already atomic. The sequence around it was not: two runs
    finishing together each read the file, each added their own exercise, and
    whichever wrote second erased the other's. Measured at roughly one loss per
    two runs of eight concurrent commands.

    Failing to lock is not fatal. A read-only clone cannot create the file at all,
    and some network mounts refuse the lock; recording progress unserialised is
    better than refusing to record it, so both fall through to the old behaviour.

    The kernel drops the lock when the process dies, so a crash leaves nothing
    stale behind.
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
