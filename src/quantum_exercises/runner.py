"""Parent side of the runner: spawn the worker, interpret its verdict, update state."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from quantum_exercises import invocation
from quantum_exercises.registry import Exercise

Outcome = Literal["pass", "fail", "error", "internal_error", "timeout", "crash"]

# Enough to show a learner what their program printed, small enough that a runaway
# print loop cannot grow the parent's memory.
MAX_CAPTURED_BYTES = 64 * 1024


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


class _BoundedReader(threading.Thread):
    """Drain a pipe, keeping at most ``limit`` bytes of it.

    Draining rather than simply stopping matters: a reader that walked away would
    leave the child blocked on a full pipe buffer, so a runaway printer would look
    like a hang instead of what it is.
    """

    def __init__(self, stream, limit: int = MAX_CAPTURED_BYTES) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._limit = limit
        self._chunks: list[bytes] = []
        self.kept = 0
        self.total = 0

    def run(self) -> None:
        try:
            while True:
                chunk = self._stream.read(8192)
                if not chunk:
                    break
                self.total += len(chunk)
                if self.kept < self._limit:
                    room = self._limit - self.kept
                    self._chunks.append(chunk[:room])
                    self.kept += min(room, len(chunk))
        except (ValueError, OSError):
            pass
        finally:
            with contextlib.suppress(OSError):
                self._stream.close()

    def text(self) -> str:
        body = b"".join(self._chunks).decode("utf-8", errors="replace")
        dropped = self.total - self.kept
        if dropped > 0:
            body += f"\n... {dropped} further bytes were produced and discarded ...\n"
        return body


def _child_env() -> dict[str, str]:
    return {
        **os.environ,
        # PYTHONSAFEPATH keeps the working directory off sys.path on 3.11 and up.
        # worker.py drops it explicitly as well, which covers 3.10.
        "PYTHONSAFEPATH": "1",
        # Pin the child's own streams to UTF-8 so a circuit drawing survives a
        # console whose locale encoding cannot represent box characters.
        # No .pyc litter: the worker imports exercise.py, check.py and their
        # neighbours, which would otherwise fill every exercise directory with a
        # __pycache__ the learner sees in their editor and never asked for.
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        # Python 3.13 and later colour their own tracebacks on a terminal, and
        # anything the exercise itself prints could carry colour too. Both would
        # land inside our panels wearing hues from outside the palette.
        "PYTHON_COLORS": "0",
        "NO_COLOR": "1",
        "PYTHONUTF8": "1",
    }


def _spawn_kwargs() -> dict:
    """Put the child in its own group, so a timeout can take its children too."""
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_tree(process: subprocess.Popen) -> None:
    """Kill the worker and anything it spawned."""
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        subprocess.run(  # noqa: S603, S607 - fixed argv, no shell
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
    else:
        import signal

        with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)

    with contextlib.suppress(OSError):
        process.kill()
    # pragma: no cover - only reached if the kill above did not take
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)


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
            detail=(
                f"The exercise file is missing. `{invocation()} reset` can restore it "
                "from the template."
            ),
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

        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=root,
            stdin=subprocess.DEVNULL,  # exercise code must not eat the user's typing
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_child_env(),
            **_spawn_kwargs(),
        )

        out_reader = _BoundedReader(process.stdout)
        err_reader = _BoundedReader(process.stderr)
        out_reader.start()
        err_reader.start()

        timed_out = False
        try:
            returncode = process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_tree(process)
            returncode = process.returncode if process.returncode is not None else -1

        out_reader.join(timeout=5)
        err_reader.join(timeout=5)
        stdout, stderr = out_reader.text(), err_reader.text()
        duration = time.monotonic() - started

        # Check for a verdict even after a timeout: the worker may have finished
        # and only a process it spawned kept the clock running.
        payload = _read_payload(result_path)

        if payload is None:
            if timed_out:
                return RunResult(
                    outcome="timeout",
                    message=f"Your code did not finish within {limit} seconds, so it was stopped.",
                    detail=(
                        "An endless `while` loop is the usual cause. If this exercise genuinely "
                        "needs longer, raise `timeout` in the exercise's meta.toml."
                    ),
                    stdout=stdout,
                    stderr=stderr,
                    duration=duration,
                )
            # The worker always writes a file unless the process died outright,
            # for example os._exit or a segfault inside a native extension.
            return RunResult(
                outcome="crash",
                message="Your code stopped the whole process before it could be checked.",
                detail=(
                    f"The process exited with code {returncode}. Calling `os._exit()`, or a "
                    "crash inside a compiled extension, does this."
                ),
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )

    return RunResult(
        outcome=payload.get("outcome", "internal_error"),
        message=payload.get("message", ""),
        detail=payload.get("detail"),
        hint=payload.get("hint"),
        artifacts=[a for a in (payload.get("artifacts") or []) if isinstance(a, dict)],
        warnings=payload.get("warnings") or [],
        line=payload.get("line"),
        error_type=payload.get("error_type"),
        stdout=stdout,
        stderr=stderr,
        duration=duration,
    )


def ran_on(artifacts: list[dict]) -> str | None:
    """Which backend an exercise reported running on, if any artifact said so.

    Tolerates meta being absent or explicitly None, which a hand-written artifact
    dict can be.
    """
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue
        meta = artifact.get("meta") or {}
        if isinstance(meta, dict) and meta.get("ran_on"):
            return str(meta["ran_on"])
    return None


def _read_payload(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


__all__ = ["MAX_CAPTURED_BYTES", "Outcome", "RunResult", "ran_on", "run_exercise"]
