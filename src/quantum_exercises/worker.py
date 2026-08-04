"""Child process that imports a learner's file and runs its check.

Isolation matters here. Exercise code is unfinished by definition: it can raise,
loop forever, or call sys.exit. Running it in a child process means the worst it
can do is fail this one run.

The verdict is written to a file whose path is given on the command line, not to
stdout, so that anything the learner prints stays readable and cannot corrupt
the result.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
import traceback
import warnings
from pathlib import Path
from types import ModuleType
from typing import Any

from quantum_exercises.checks import Artifact, CheckFailed
from quantum_exercises.errors import UNTRANSLATED_HINT, translate

# Sentinel exit codes so the parent can tell a clean verdict from a hard crash.
EXIT_OK = 0
EXIT_NO_RESULT = 3


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
    target_str = str(target.resolve())
    line: int | None = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if (
            frame.filename
            and Path(frame.filename).resolve(strict=False).as_posix() == Path(target_str).as_posix()
        ):
            line = frame.lineno
    if line is None and isinstance(exc, SyntaxError) and exc.lineno:
        line = exc.lineno
    return line


def _normalize_artifacts(value: Any) -> list[dict]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple)) else [value]
    out: list[dict] = []
    for item in items:
        if isinstance(item, Artifact):
            out.append(dataclasses.asdict(item))
        elif isinstance(item, dict):
            out.append(item)
    return out


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
            return {
                "outcome": "internal_error",
                "message": f"The exercise's own check.py failed to load: {exc}",
                "detail": traceback.format_exc(),
                "hint": None,
                "artifacts": [],
                "warnings": _format_warnings(caught),
                "line": None,
                "error_type": type(exc).__name__,
            }

        if not hasattr(check_module, "check"):
            caught.extend(recorded)
            return {
                "outcome": "internal_error",
                "message": f"{exercise_dir.name}/check.py does not define a check() function.",
                "detail": None,
                "hint": None,
                "artifacts": [],
                "warnings": _format_warnings(caught),
                "line": None,
                "error_type": None,
            }

        try:
            artifacts = _normalize_artifacts(check_module.check(module))
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

    args.result_path.write_text(json.dumps(payload), encoding="utf-8")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
