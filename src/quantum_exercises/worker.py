"""Child process that imports a learner's file and runs its check.

What the child process buys: a crash, a `sys.exit`, an `os._exit` or an endless
loop in exercise.py costs one run instead of the whole CLI session, and the
verdict travels back over a file so nothing the learner prints can corrupt it.

What it does not buy: this is not a sandbox. The worker inherits the environment,
the filesystem and the network. exercise.py is written by the person running it,
and check.py is repository code reviewed like any other source file.
"""

from __future__ import annotations

import os
import sys

# Drop the working directory from sys.path before importing anything else.
# `python -m` puts it at the front, so a scratch file named qiskit.py or json.py
# in the repository root would shadow the real module and break every run, with
# the failure landing on the learner. PYTHONSAFEPATH handles this on 3.11 and up;
# doing it here covers 3.10 as well.
#
# Compared by real path, not by string: PYTHONSAFEPATH does not filter PYTHONPATH,
# and an entry naming this same directory through a symlink is a different string.
# On macOS everything under /tmp is reached that way, so a string comparison would
# quietly let the directory back in.
_CWD = os.path.realpath(os.getcwd())
sys.path[:] = [
    entry for entry in sys.path if entry not in ("", ".") and os.path.realpath(entry) != _CWD
]

import argparse  # noqa: E402
import dataclasses  # noqa: E402
import importlib.util  # noqa: E402
import inspect  # noqa: E402
import json  # noqa: E402
import traceback  # noqa: E402
import warnings  # noqa: E402
from pathlib import Path  # noqa: E402
from types import ModuleType  # noqa: E402
from typing import Any  # noqa: E402

from quantum_exercises.checks import Artifact, CheckFailed  # noqa: E402
from quantum_exercises.errors import UNTRANSLATED_HINT, translate  # noqa: E402

EXIT_OK = 0

# The parent bounds stdout and stderr at 64 KB each. The verdict file is the other
# way out of this process, and it was not bounded at all: an exception whose string
# form is enormous, say a large array interpolated into a message, travelled whole,
# was held in the parent's memory and printed in full. Generous enough that no real
# message is ever touched.
MAX_FIELD_CHARS = 8000


def _clip(text: str, limit: int = MAX_FIELD_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... {len(text) - limit} further characters were cut ...\n"


class AuthoringError(Exception):
    """The exercise's own check.py is wrong, which is never the learner's fault."""


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses and pickling inside the file resolve.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _user_line(exc: BaseException, target: Path) -> int | None:
    """Find the last line inside the learner's own file, skipping library frames."""
    wanted = Path(target).resolve(strict=False).as_posix()
    line: int | None = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename and Path(frame.filename).resolve(strict=False).as_posix() == wanted:
            line = frame.lineno
    if line is None and isinstance(exc, SyntaxError) and exc.lineno:
        line = exc.lineno
    return line


def _normalize_artifacts(value: Any) -> list[dict]:
    """Turn whatever check() returned into JSON-ready dicts, or say why it cannot."""
    if value is None:
        return []

    if inspect.isgenerator(value) or inspect.isasyncgen(value):
        raise AuthoringError(
            "check() is a generator function: its body contains `yield`, so calling it "
            "returns a generator and runs none of the checks. Remove the yield."
        )
    if inspect.iscoroutine(value):
        raise AuthoringError("check() is async, but the runner calls it synchronously.")

    items = value if isinstance(value, (list, tuple)) else [value]
    out: list[dict] = []
    for item in items:
        if isinstance(item, Artifact):
            out.append(dataclasses.asdict(item))
        elif isinstance(item, dict):
            out.append(item)
        else:
            raise AuthoringError(
                f"check() returned a {type(item).__name__}. It must return None, an "
                "Artifact, or a list of Artifacts."
            )
    return out


def _internal_error(message: str, detail: str | None, caught: list) -> dict:
    return {
        "outcome": "internal_error",
        "message": message,
        "detail": detail,
        "hint": None,
        "artifacts": [],
        "warnings": _format_warnings(caught),
        "line": None,
        "error_type": None,
    }


def run(exercise_dir: Path, target: Path) -> dict:
    caught: list[warnings.WarningMessage] = []

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")

        try:
            module = _load_module(target, "qx_learner_solution")
        except BaseException as exc:  # noqa: BLE001 - any failure is a teachable result
            caught.extend(recorded)
            return _failure_payload(exc, target, caught, stage="import")

        try:
            check_module = _load_module(exercise_dir / "check.py", "qx_exercise_check")
        except BaseException as exc:  # noqa: BLE001
            caught.extend(recorded)
            return _internal_error(
                f"The exercise's own check.py failed to load: {exc}",
                traceback.format_exc(),
                caught,
            )

        if not hasattr(check_module, "check"):
            caught.extend(recorded)
            return _internal_error(
                f"{exercise_dir.name}/check.py does not define a check() function.", None, caught
            )

        try:
            returned = check_module.check(module)
        except CheckFailed as exc:
            caught.extend(recorded)
            return {
                "outcome": "fail",
                "message": exc.message,
                "detail": exc.detail,
                "hint": None,
                "artifacts": [],
                "warnings": _format_warnings(caught),
                "line": None,
                "error_type": None,
            }
        except BaseException as exc:  # noqa: BLE001
            caught.extend(recorded)
            return _failure_payload(exc, target, caught, stage="check")

        try:
            artifacts = _normalize_artifacts(returned)
        except AuthoringError as exc:
            caught.extend(recorded)
            return _internal_error(f"{exercise_dir.name}/check.py is broken: {exc}", None, caught)

        caught.extend(recorded)

    return {
        "outcome": "pass",
        "message": "",
        "detail": None,
        "hint": None,
        "artifacts": artifacts,
        "warnings": _format_warnings(caught),
        "line": None,
        "error_type": None,
    }


def _failure_payload(exc: BaseException, target: Path, caught: list, *, stage: str) -> dict:
    translation = translate(exc)
    raw = f"{type(exc).__name__}: {exc}"
    if translation is not None:
        message, hint = translation.message, translation.hint
        detail = f"Python reported: {raw}"
    else:
        # No rule matched, so the learner gets the raw error. Tell them that is a
        # gap in this tool rather than in their understanding.
        message, hint = raw, UNTRANSLATED_HINT
        detail = None

    return {
        "outcome": "error",
        "message": message,
        "detail": detail,
        "hint": hint,
        "artifacts": [],
        "warnings": _format_warnings(caught),
        "line": _user_line(exc, target),
        "error_type": type(exc).__name__,
        "stage": stage,
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }


def _format_warnings(caught: list) -> list[str]:
    seen: list[str] = []
    for item in caught:
        text = str(item.message).strip()
        if text and text not in seen:
            seen.append(text)
    return seen


def _write(path: Path, payload: dict) -> None:
    """Serialize defensively: an artifact that cannot be JSON is an authoring bug.

    Without this, the write raises, no file is produced, and the parent reports it
    as though the learner had killed the process.
    """
    payload = {
        key: _clip(value)
        if isinstance(value, str)
        else [_clip(item) for item in value]
        if key == "warnings" and isinstance(value, list)
        else value
        for key, value in payload.items()
    }
    try:
        text = json.dumps(payload)
    except (TypeError, ValueError) as exc:
        text = json.dumps(
            {
                "outcome": "internal_error",
                "message": "The exercise's check.py returned something that cannot be serialized.",
                "detail": (
                    f"{type(exc).__name__}: {exc}\nArtifact payloads must be JSON-ready: "
                    "plain numbers, strings, lists and dicts."
                ),
                "hint": None,
                "artifacts": [],
                "warnings": payload.get("warnings", []),
                "line": None,
                "error_type": type(exc).__name__,
            }
        )
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quantum_exercises.worker")
    parser.add_argument("exercise_dir", type=Path)
    parser.add_argument("result_path", type=Path)
    parser.add_argument(
        "--file", type=Path, default=None, help="File to check, defaults to exercise.py"
    )
    args = parser.parse_args(argv)

    target = args.file or (args.exercise_dir / "exercise.py")

    try:
        payload = run(args.exercise_dir, target)
    except BaseException as exc:  # noqa: BLE001 - never let the worker die silently
        payload = {
            "outcome": "internal_error",
            "message": f"The exercise runner itself failed: {exc}",
            "detail": traceback.format_exc(),
            "hint": None,
            "artifacts": [],
            "warnings": [],
            "line": None,
            "error_type": type(exc).__name__,
        }

    _write(args.result_path, payload)
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
