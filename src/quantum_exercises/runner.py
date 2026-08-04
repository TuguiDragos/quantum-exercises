"""Parent side of the runner: spawn the worker, interpret its verdict, update state."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from quantum_exercises.registry import Exercise

Outcome = Literal["pass", "fail", "error", "internal_error", "timeout", "crash"]


@dataclass
class RunResult:
    outcome: Outcome
    message: str = ""
    detail: str | None = None
    hint: str | None = None
    artifacts: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    line: int | None = None
    error_type: str | None = None
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0

    @property
    def passed(self) -> bool:
        return self.outcome == "pass"


def run_exercise(
    exercise: Exercise,
    *,
    root: Path,
    target: Path | None = None,
    timeout: int | None = None,
) -> RunResult:
    """Run one exercise in a child process and return a structured verdict."""
    target = target or exercise.exercise_file
    if not target.is_file():
        return RunResult(
            outcome="internal_error",
            message=f"{target} does not exist.",
            detail="The exercise file is missing. `qx reset` can restore it from the template.",
        )

    limit = timeout if timeout is not None else exercise.timeout
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="qx-run-") as tmp:
        result_path = Path(tmp) / "result.json"
        command = [
            sys.executable,
            "-m",
            "quantum_exercises.worker",
            str(exercise.path),
            str(result_path),
            "--file",
            str(target),
        ]

        try:
            completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=limit,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            return RunResult(
                outcome="timeout",
                message=f"Your code did not finish within {limit} seconds, so it was stopped.",
                detail=(
                    "An endless `while` loop is the usual cause. If this exercise genuinely "
                    "needs longer, raise `timeout` in the exercise's meta.toml."
                ),
                stdout=_as_text(expired.stdout),
                stderr=_as_text(expired.stderr),
                duration=time.monotonic() - started,
            )

        duration = time.monotonic() - started

        if not result_path.is_file():
            # The worker always writes a file unless the process died outright,
            # for example a segfault inside a native extension or a sys.exit call.
            return RunResult(
                outcome="crash",
                message="Your code stopped the whole process before it could be checked.",
                detail=(
                    f"The process exited with code {completed.returncode}. "
                    "Calling `exit()`, `quit()` or `sys.exit()` in exercise.py does this."
                ),
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
            )

        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return RunResult(
                outcome="internal_error",
                message="The runner could not read the result of your run.",
                detail=str(exc),
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration=duration,
            )

    return RunResult(
        outcome=payload.get("outcome", "internal_error"),
        message=payload.get("message", ""),
        detail=payload.get("detail"),
        hint=payload.get("hint"),
        artifacts=payload.get("artifacts") or [],
        warnings=payload.get("warnings") or [],
        line=payload.get("line"),
        error_type=payload.get("error_type"),
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration=duration,
    )


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


__all__ = ["Outcome", "RunResult", "run_exercise"]
