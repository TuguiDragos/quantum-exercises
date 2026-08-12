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
from quantum_exercises.backends import OFFLINE_ENV
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
                # read1, not read: a buffered read(n) waits for n bytes or EOF, so a
                # single short line sat in this buffer until the pipe closed. When
                # something the exercise spawned kept the write end open, that meant
                # the learner's output was reported as empty.
                chunk = self._stream.read1(8192)
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


def _child_env(exercise: Exercise, *, allow_hardware: bool) -> dict[str, str]:
    env = {
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
    if exercise.hardware and not allow_hardware:
        # Nobody agreed to this run reaching a QPU, so the child is kept off one.
        # The decision belongs to the caller: `qx run` sets it from the question
        # it asked, and everything else, watch mode included, gets the safe
        # answer by default. An existing QX_OFFLINE is never cleared here.
        env[OFFLINE_ENV] = "1"
    return env


def _spawn_kwargs() -> dict:
    """Put the child in its own group, so a timeout can take its children too."""
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _process_group(process: subprocess.Popen) -> int | None:
    """The child's process group, read while the child is certainly still alive.

    Read once, up front. Asking later races with the child exiting, and a pid that
    has been reused would hand back a group belonging to something else entirely.
    """
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        return None
    try:
        return os.getpgid(process.pid)
    except (ProcessLookupError, PermissionError, OSError):  # pragma: no cover
        return None


def _kill_tree(process: subprocess.Popen, pgid: int | None = None) -> None:
    """Kill the worker and anything it spawned."""
    if os.name == "nt":  # pragma: no cover - exercised only on Windows
        subprocess.run(  # noqa: S603, S607 - fixed argv, no shell
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
    else:
        import signal

        group = pgid if pgid is not None else _process_group(process)
        if group is not None:
            with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
                os.killpg(group, signal.SIGKILL)

    with contextlib.suppress(OSError):
        process.kill()
    # Reap it, so a signal that has not landed yet cannot leave a zombie behind.
    # The timeout is suppressed because a child that ignores SIGKILL is the
    # kernel's problem rather than something this runner can do anything about.
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)


def run_exercise(
    exercise: Exercise,
    *,
    root: Path,
    target: Path | None = None,
    timeout: int | None = None,
    allow_hardware: bool = False,
) -> RunResult:
    """Run one exercise in a child process and return a structured verdict.

    ``allow_hardware`` defaults to False so that a caller which has not thought
    about it cannot spend someone's QPU quota. Only `qx run`, holding an answer
    to the question it asked, passes True.
    """
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
            env=_child_env(exercise, allow_hardware=allow_hardware),
            **_spawn_kwargs(),
        )

        # Read the group now, while the child is certainly alive, so the cleanup
        # below cannot race the pid being reused.
        pgid = _process_group(process)

        # Everything below runs under a finally that kills the whole group. The child
        # sits in its own group precisely so the terminal cannot signal it, which also
        # means Ctrl-C reaches only this process. Without the finally the parent
        # unwinds and the worker is orphaned, and since the time limit is enforced
        # here rather than in the child, nothing would ever stop it again.
        #
        # The kill is unconditional rather than guarded on the worker still running:
        # a worker can exit cleanly having left something of its own behind, and that
        # something holds the write end of these pipes open. Killing the group is what
        # closes them, which is what lets the joins below return.
        try:
            out_reader = _BoundedReader(process.stdout)
            err_reader = _BoundedReader(process.stderr)
            out_reader.start()
            err_reader.start()

            timed_out = False
            try:
                returncode = process.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(process, pgid)
                returncode = process.returncode if process.returncode is not None else -1
            else:
                # The worker is done, so nothing it left running has anything more to
                # say. Close the pipes by killing the group before waiting on the
                # readers, or a stray grandchild holds them open and the joins below
                # burn their full timeout and return nothing.
                _kill_tree(process, pgid)

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
                        message=(
                            f"Your code did not finish within {limit} seconds, so it was stopped."
                        ),
                        detail=_timeout_detail(exercise, explicit=timeout is not None),
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
        finally:
            _kill_tree(process, pgid)

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


def _timeout_detail(exercise: Exercise, *, explicit: bool) -> str:
    """Point at the knob the reader actually turned, not the other one.

    The number of seconds is already in the message this detail sits under, so it
    is deliberately not repeated here.
    """
    where = (
        "pass a larger `--timeout`" if explicit else f"raise `timeout` in {exercise.slug}/meta.toml"
    )
    return (
        "An endless `while` loop is the usual cause. If this exercise genuinely "
        f"needs longer, {where}."
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
