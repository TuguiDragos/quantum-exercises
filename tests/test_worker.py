"""The child process, including the mistakes an exercise author can make.

An AuthoringError is never the learner's fault, so each of these has to come back
as internal_error naming check.py, not as a failed answer.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quantum_exercises import worker as worker_module
from quantum_exercises.checks import Artifact


def _exercise_dir(tmp_path: Path, check_body: str) -> Path:
    directory = tmp_path / "99_probe"
    directory.mkdir()
    (directory / "check.py").write_text(check_body, encoding="utf-8")
    (directory / "exercise.py").write_text("answer = 1\n", encoding="utf-8")
    return directory


# Never awaiting the coroutine is the point: the worker has to refuse it, not run
# it, and Python warns about the abandoned object on the way out.
@pytest.mark.filterwarnings("ignore:coroutine .* was never awaited:RuntimeWarning")
@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ("def check(mod):\n    yield 1\n", "generator function"),
        ("async def check(mod):\n    return None\n", "async"),
        ("def check(mod):\n    return 42\n", "returned a int"),
        ("def check(mod):\n    raise ValueError('author slipped')\n", "ValueError"),
        ("value = 1 / 0\n", "failed to load"),
        ("nothing = True\n", "does not define a check() function"),
    ],
)
def test_authoring_mistakes_are_reported(tmp_path: Path, body: str, fragment: str) -> None:
    directory = _exercise_dir(tmp_path, body)
    payload = worker_module.run(directory, directory / "exercise.py")
    assert payload["outcome"] in ("internal_error", "error")
    assert fragment in json.dumps(payload)


def test_artifacts_and_plain_dicts_both_travel(tmp_path: Path) -> None:
    directory = _exercise_dir(
        tmp_path,
        "from quantum_exercises.checks import text_artifact\n"
        "def check(mod):\n"
        "    return [text_artifact('hi'), {'kind': 'text', 'payload': 'raw'}]\n",
    )
    payload = worker_module.run(directory, directory / "exercise.py")
    assert payload["outcome"] == "pass"
    assert len(payload["artifacts"]) == 2


def test_an_enormous_message_is_clipped(tmp_path: Path) -> None:
    huge = "x" * (worker_module.MAX_FIELD_CHARS + 500)
    out = tmp_path / "result.json"
    worker_module._write(out, {"outcome": "fail", "message": huge, "warnings": [huge]})
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "further characters were cut" in payload["message"]
    assert len(payload["message"]) < len(huge) + 200


def test_an_unserializable_artifact_is_reported_not_raised(tmp_path: Path) -> None:
    out = tmp_path / "result.json"
    worker_module._write(out, {"outcome": "pass", "artifacts": [{"payload": {1, 2}}]})
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["outcome"] == "internal_error"
    assert "cannot be serialized" in payload["message"]


def test_warnings_reach_the_parent(tmp_path: Path) -> None:
    directory = _exercise_dir(tmp_path, "def check(mod):\n    return None\n")
    (directory / "exercise.py").write_text(
        "import warnings\nwarnings.warn('deprecated thing')\n", encoding="utf-8"
    )
    payload = worker_module.run(directory, directory / "exercise.py")
    assert "deprecated thing" in payload["warnings"]


def test_main_always_writes_a_verdict(tmp_path: Path) -> None:
    directory = _exercise_dir(tmp_path, "def check(mod):\n    return None\n")
    out = tmp_path / "result.json"
    assert worker_module.main([str(directory), str(out)]) == worker_module.EXIT_OK
    assert json.loads(out.read_text(encoding="utf-8"))["outcome"] == "pass"


def test_normalize_artifacts_accepts_none_and_a_single_artifact() -> None:
    assert worker_module._normalize_artifacts(None) == []
    assert worker_module._normalize_artifacts(Artifact("text", "c", "p"))[0]["kind"] == "text"


def test_a_nested_payload_survives_json(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    worker_module._write(
        out, {"outcome": "pass", "artifacts": [{"kind": "counts", "payload": {"00": 5}}]}
    )
    assert json.loads(out.read_text(encoding="utf-8"))["artifacts"][0]["payload"] == {"00": 5}
