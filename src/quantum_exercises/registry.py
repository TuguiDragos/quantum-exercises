"""Discover exercises on disk and read their metadata.

Ordering comes from the numeric directory prefix, so adding an exercise means
creating one directory. There is no central index file to forget to update.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from quantum_exercises import invocation

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib

EXERCISES_DIR = "exercises"
SLUG_PATTERN = re.compile(r"^(\d{2})_[a-z0-9_]+$")

# Files that make up one exercise.
EXERCISE_FILE = "exercise.py"
SOLUTION_FILE = "solution.py"
CHECK_FILE = "check.py"
HINTS_FILE = "hints.md"
README_FILE = "README.md"
META_FILE = "meta.toml"
TEMPLATE_FILE = "template.py"


class RegistryError(RuntimeError):
    """The exercises directory is missing or an exercise is malformed."""


# Generous enough for a slow first Qiskit import, short enough that an infinite
# loop in exercise.py does not hang the terminal. Overridable per exercise.
DEFAULT_TIMEOUT = 120


@dataclass(frozen=True)
class Exercise:
    slug: str
    number: int
    path: Path
    title: str
    act: str
    summary: str
    hardware: bool
    timeout: int

    @property
    def exercise_file(self) -> Path:
        return self.path / EXERCISE_FILE

    @property
    def solution_file(self) -> Path:
        return self.path / SOLUTION_FILE

    @property
    def check_file(self) -> Path:
        return self.path / CHECK_FILE

    @property
    def hints_file(self) -> Path:
        return self.path / HINTS_FILE

    @property
    def readme_file(self) -> Path:
        return self.path / README_FILE

    @property
    def template_file(self) -> Path:
        """Pristine copy of exercise.py, used by `qx reset`."""
        return self.path / TEMPLATE_FILE


def _holds_exercises(directory: Path) -> bool:
    """Whether this directory is a project root, rather than merely near one.

    An `exercises/` directory alone is not enough. Anyone can have `~/exercises`
    for something else, and it used to shadow the real repository from every
    directory beneath it: the walk stopped there, reported "No exercises found",
    and told the reader to run from inside the repository, which is what they
    thought they were doing. It also made the installed-package fallback below
    unreachable for anyone with such a directory in their home.
    """
    base = directory / EXERCISES_DIR
    try:
        return base.is_dir() and any(
            entry.is_dir() and SLUG_PATTERN.match(entry.name) for entry in base.iterdir()
        )
    except OSError:  # unreadable directory, treat as not a root
        return False


def find_project_root(start: Path | None = None) -> Path:
    """Locate the repo root: the nearest ancestor whose exercises/ directory holds one.

    Holding the directory is not enough. A plain `~/exercises` used to swallow the
    search from everything beneath it, so a candidate only counts when at least one
    numbered exercise sits inside. See _holds_exercises.

    QX_ROOT overrides the search, which is what the test suite uses.
    """
    override = os.environ.get("QX_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / EXERCISES_DIR).is_dir():
            raise RegistryError(
                f"QX_ROOT is set to {root}, but it has no {EXERCISES_DIR}/ directory."
            )
        return root

    candidates = [start or Path.cwd()]
    # Fall back to the installed package location, which covers `qx` run from
    # an unrelated directory after `uv tool install --editable .`.
    candidates.append(Path(__file__).resolve().parent)

    for candidate in candidates:
        for directory in [candidate.resolve(), *candidate.resolve().parents]:
            if _holds_exercises(directory):
                return directory

    raise RegistryError(
        "Could not find the exercises/ directory. Run this from inside the "
        "quantum-exercises repository, or set QX_ROOT to point at it."
    )


def _read_meta(path: Path) -> dict:
    meta_file = path / META_FILE
    if not meta_file.is_file():
        raise RegistryError(f"{path.name} is missing {META_FILE}.")
    try:
        with meta_file.open("rb") as handle:
            return tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise RegistryError(f"{meta_file} is not valid TOML: {exc}") from exc


def load_exercise(path: Path) -> Exercise:
    match = SLUG_PATTERN.match(path.name)
    if not match:
        raise RegistryError(
            f"'{path.name}' is not a valid exercise directory name. "
            "Expected two digits, an underscore, then lowercase words, e.g. 03_first_circuit."
        )
    meta = _read_meta(path)

    for required in (EXERCISE_FILE, SOLUTION_FILE, CHECK_FILE):
        if not (path / required).is_file():
            raise RegistryError(f"{path.name} is missing {required}.")

    missing_keys = {"title", "act", "summary"} - meta.keys()
    if missing_keys:
        raise RegistryError(f"{path.name}/{META_FILE} is missing keys: {sorted(missing_keys)}")

    # The one conversion that used to be unguarded. int() on a string raises
    # ValueError rather than RegistryError, and load_exercises() reads every
    # exercise, so one typo took down every command at once. A zero or negative
    # value parsed fine and produced "did not finish within -5 seconds".
    # bool is a subclass of int, so `timeout = true` needs excluding by hand.
    timeout = meta.get("timeout", DEFAULT_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
        raise RegistryError(
            f"{path.name}/{META_FILE} has timeout = {timeout!r}. "
            "It must be a positive whole number of seconds."
        )

    return Exercise(
        slug=path.name,
        number=int(match.group(1)),
        path=path,
        title=str(meta["title"]),
        act=str(meta["act"]),
        summary=str(meta["summary"]),
        hardware=bool(meta.get("hardware", False)),
        timeout=timeout,
    )


def load_exercises(root: Path | None = None) -> list[Exercise]:
    """Return every exercise, ordered by its numeric prefix."""
    root = root or find_project_root()
    base = root / EXERCISES_DIR
    if not base.is_dir():
        raise RegistryError(f"No exercises directory at {base}.")

    exercises = [
        load_exercise(entry)
        for entry in sorted(base.iterdir())
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    if not exercises:
        raise RegistryError(f"No exercises found in {base}.")

    numbers = [e.number for e in exercises]
    duplicates = {n for n in numbers if numbers.count(n) > 1}
    if duplicates:
        raise RegistryError(f"Duplicate exercise numbers: {sorted(duplicates)}")

    return exercises


HINT_HEADING = re.compile(r"^##\s*Hint\s*\d+\s*$", re.IGNORECASE | re.MULTILINE)


def load_hints(exercise: Exercise) -> list[str]:
    """Split hints.md on `## Hint N` headings. Missing file means no hints."""
    if not exercise.hints_file.is_file():
        return []
    text = exercise.hints_file.read_text(encoding="utf-8")
    parts = HINT_HEADING.split(text)
    # The first chunk is whatever precedes the first heading, usually nothing.
    return [chunk.strip() for chunk in parts[1:] if chunk.strip()]


def resolve(name: str, exercises: list[Exercise]) -> Exercise:
    """Look up an exercise by number, slug, or unique substring."""
    # isdecimal, not isdigit: isdigit accepts characters like the superscript two
    # that int() then refuses, which would surface as a raw traceback.
    if name.isdecimal():
        wanted = int(name)
        for exercise in exercises:
            if exercise.number == wanted:
                return exercise
        raise RegistryError(f"There is no exercise number {wanted}.")

    for exercise in exercises:
        if exercise.slug == name:
            return exercise

    matches = [e for e in exercises if name.lower() in e.slug.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RegistryError(
            f"'{name}' matches several exercises: {', '.join(m.slug for m in matches)}"
        )
    raise RegistryError(f"No exercise matches '{name}'. Run `{invocation()} list` to see them all.")


__all__ = [
    "Exercise",
    "RegistryError",
    "find_project_root",
    "load_exercise",
    "load_exercises",
    "resolve",
]
