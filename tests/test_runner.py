"""Subprocess isolation: what happens when a learner's file misbehaves."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from quantum_exercises import runner
from quantum_exercises.registry import Exercise, load_exercise
from quantum_exercises.runner import MAX_CAPTURED_BYTES, ran_on, run_exercise

CHECK_SOURCE = """
from quantum_exercises.checks import CheckFailed, require, text_artifact


def check(mod):
    value = require(mod, "answer")
    if value != 42:
        raise CheckFailed(f"answer is {value}, expected 42")
    return text_artifact("ok", caption="result")
"""


@pytest.fixture
def synthetic(tmp_path: Path) -> Exercise:
    path = tmp_path / "exercises" / "01_synthetic"
    path.mkdir(parents=True)
    (path / "meta.toml").write_text(
        'title = "Synthetic"\nact = "Act I"\nsummary = "For tests"\n', encoding="utf-8"
    )
    (path / "check.py").write_text(CHECK_SOURCE, encoding="utf-8")
    (path / "solution.py").write_text("answer = 42\n", encoding="utf-8")
    (path / "exercise.py").write_text("answer = None\n", encoding="utf-8")
    return load_exercise(path)


def _write(exercise: Exercise, source: str) -> None:
    exercise.exercise_file.write_text(source, encoding="utf-8")


def test_passing_run(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert result.artifacts[0]["payload"] == "ok"


def test_failing_check_reports_the_message(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = 7\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "fail"
    assert "expected 42" in result.message


def test_exception_is_translated_and_located(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "from qiskit import execute\n\nanswer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert "`execute()` was removed" in result.message
    assert result.line == 1


def test_syntax_error_is_reported_without_a_traceback(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "answer = (42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert "syntax error" in result.message


def test_infinite_loop_is_stopped(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "while True:\n    pass\n")
    result = run_exercise(synthetic, root=tmp_path, timeout=5)
    assert result.outcome == "timeout"
    assert "5 seconds" in result.message


def test_sys_exit_is_caught_as_an_error(synthetic: Exercise, tmp_path: Path) -> None:
    """SystemExit is a BaseException, so the worker still reports it properly."""
    _write(synthetic, "import sys\n\nsys.exit(3)\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "error"
    assert result.error_type == "SystemExit"


def test_hard_exit_is_reported_as_a_crash(synthetic: Exercise, tmp_path: Path) -> None:
    """os._exit skips every handler, so no result file is written."""
    _write(synthetic, "import os\n\nos._exit(1)\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "crash"


def test_learner_stdout_is_captured(synthetic: Exercise, tmp_path: Path) -> None:
    _write(synthetic, "print('hello from the exercise')\nanswer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert "hello from the exercise" in result.stdout


def test_stdout_cannot_corrupt_the_verdict(synthetic: Exercise, tmp_path: Path) -> None:
    """The result travels via a file, so printed JSON cannot be mistaken for it."""
    _write(synthetic, 'print(\'{"outcome": "pass"}\')\nanswer = 7\n')
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "fail"


def test_warnings_are_surfaced(synthetic: Exercise, tmp_path: Path) -> None:
    _write(
        synthetic,
        "import warnings\n\nwarnings.warn('watch out')\nanswer = 42\n",
    )
    result = run_exercise(synthetic, root=tmp_path)
    assert result.passed
    assert any("watch out" in w for w in result.warnings)


def test_missing_file(synthetic: Exercise, tmp_path: Path) -> None:
    synthetic.exercise_file.unlink()
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "internal_error"


def test_broken_check_file_is_not_blamed_on_the_learner(
    synthetic: Exercise, tmp_path: Path
) -> None:
    synthetic.check_file.write_text("this is not python(\n", encoding="utf-8")
    _write(synthetic, "answer = 42\n")
    result = run_exercise(synthetic, root=tmp_path)
    assert result.outcome == "internal_error"
    assert "check.py" in result.message


class TestHardening:
    """Regressions for defects found by an adversarial review of the runner."""

    def test_stdin_is_closed_so_exercises_cannot_eat_your_typing(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        _write(synthetic, "answer = input('give me something: ')\n")
        result = run_exercise(synthetic, root=tmp_path, timeout=20)
        assert result.outcome == "error"
        assert result.error_type == "EOFError"

    def test_runaway_output_is_capped(self, synthetic: Exercise, tmp_path: Path) -> None:
        """A print loop must not grow the parent's memory without bound."""
        _write(
            synthetic,
            "import sys\nfor _ in range(20000):\n    sys.stdout.write('A' * 4096 + '\\n')\n"
            "answer = 42\n",
        )
        result = run_exercise(synthetic, root=tmp_path, timeout=60)
        assert result.passed
        assert len(result.stdout.encode()) < 4 * MAX_CAPTURED_BYTES
        assert "discarded" in result.stdout

    def test_a_verdict_written_before_the_timeout_is_honoured(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        """A leftover grandchild must not turn a finished run into a timeout."""
        _write(
            synthetic,
            "import subprocess, sys\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "answer = 42\n",
        )
        result = run_exercise(synthetic, root=tmp_path, timeout=15)
        assert result.passed, f"{result.outcome}: {result.message}"

    def test_a_stray_module_in_the_root_does_not_break_the_run(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        """A learner's scratch qiskit.py must not shadow the real package."""
        (tmp_path / "qiskit.py").write_text("BROKEN = True\n", encoding="utf-8")
        _write(synthetic, "answer = 42\n")
        result = run_exercise(synthetic, root=tmp_path)
        assert result.passed, f"{result.outcome}: {result.message}"

    def test_binary_on_stdout_does_not_crash_the_runner(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        _write(
            synthetic,
            "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe\\x00 hi\\n')\nanswer = 42\n",
        )
        result = run_exercise(synthetic, root=tmp_path)
        assert result.passed

    def test_a_generator_check_is_an_authoring_error_not_a_pass(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        """The worst possible failure: silently marking every answer correct."""
        synthetic.check_file.write_text(
            "from quantum_exercises.checks import CheckFailed\n\n\n"
            "def check(mod):\n    yield None\n    raise CheckFailed('wrong')\n",
            encoding="utf-8",
        )
        _write(synthetic, "answer = 999\n")
        result = run_exercise(synthetic, root=tmp_path)
        assert result.outcome == "internal_error"
        assert "generator" in result.message

    def test_an_unserializable_artifact_is_not_blamed_on_the_learner(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        synthetic.check_file.write_text(
            "from quantum_exercises.checks import Artifact\n\n\n"
            "def check(mod):\n"
            "    return Artifact(kind='text', caption='c', payload=complex(1, 2))\n",
            encoding="utf-8",
        )
        _write(synthetic, "answer = 42\n")
        result = run_exercise(synthetic, root=tmp_path)
        assert result.outcome == "internal_error"
        assert "serialized" in result.message

    def test_a_non_artifact_return_is_an_authoring_error(
        self, synthetic: Exercise, tmp_path: Path
    ) -> None:
        synthetic.check_file.write_text(
            "def check(mod):\n    return 'just a string'\n", encoding="utf-8"
        )
        _write(synthetic, "answer = 42\n")
        result = run_exercise(synthetic, root=tmp_path)
        assert result.outcome == "internal_error"


class TestRanOn:
    def test_reads_the_backend_an_exercise_reported(self) -> None:
        assert ran_on([{"meta": {"ran_on": "hardware"}}]) == "hardware"

    def test_tolerates_meta_being_none(self) -> None:
        """A hand-written artifact dict can carry meta=None; that must not crash."""
        assert ran_on([{"meta": None}, {"meta": {"ran_on": "simulator"}}]) == "simulator"

    def test_tolerates_junk_entries(self) -> None:
        assert ran_on(["not a dict", {}, {"meta": {}}]) is None


def test_read_payload_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text("{broken", encoding="utf-8")
    assert runner._read_payload(path) is None
    path.write_text('["a list, not a dict"]', encoding="utf-8")
    assert runner._read_payload(path) is None


def test_bounded_reader_survives_a_closed_stream() -> None:
    stream = io.BytesIO(b"hello")
    stream.close()
    reader = runner._BoundedReader(stream)
    reader.start()
    reader.join(timeout=5)
    assert reader.text() == ""


def test_ran_on_ignores_junk_artifacts() -> None:
    artifacts = [{"meta": None}, "not a dict", {"meta": {"ran_on": "hardware"}}]
    assert runner.ran_on(artifacts) == "hardware"
    assert runner.ran_on([{"meta": {}}]) is None
