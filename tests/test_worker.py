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


def test_main_reports_its_own_failure_rather_than_dying(tmp_path: Path, monkeypatch) -> None:
    """The parent reads a file. No file at all is reported to the learner as a crash.

    So the last resort has to be a written verdict, even when the runner itself is
    what broke.
    """
    directory = _exercise_dir(tmp_path, "def check(mod):\n    return None\n")
    out = tmp_path / "result.json"

    def boom(*args, **kwargs):
        raise RuntimeError("the runner itself broke")

    monkeypatch.setattr(worker_module, "run", boom)
    assert worker_module.main([str(directory), str(out)]) == worker_module.EXIT_OK

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["outcome"] == "internal_error"
    assert "the runner itself broke" in payload["message"]
    assert payload["error_type"] == "RuntimeError"


def test_a_file_python_cannot_import_is_an_import_error(tmp_path: Path) -> None:
    """No importer claims an unknown extension, so the spec comes back as None."""
    odd = tmp_path / "answer.txt"
    odd.write_text("answer = 42\n", encoding="utf-8")
    with pytest.raises(ImportError, match="Could not load"):
        worker_module._load_module(odd, "qx_probe_unimportable")


def test_a_syntax_error_reports_its_own_line(tmp_path: Path) -> None:
    """A SyntaxError never reaches a frame inside the learner's file.

    The file failed to compile, so no frame of it was ever executed and walking
    the traceback finds nothing. The exception carries the line instead.
    """
    source = tmp_path / "broken.py"
    source.write_text("answer = 1\nresult = (42\n", encoding="utf-8")
    try:
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
    except SyntaxError as exc:
        assert worker_module._user_line(exc, source) == 2


def test_normalize_artifacts_accepts_none_and_a_single_artifact() -> None:
    assert worker_module._normalize_artifacts(None) == []
    assert worker_module._normalize_artifacts(Artifact("text", "c", "p"))[0]["kind"] == "text"


def test_a_nested_payload_survives_json(tmp_path: Path) -> None:
    out = tmp_path / "r.json"
    worker_module._write(
        out, {"outcome": "pass", "artifacts": [{"kind": "counts", "payload": {"00": 5}}]}
    )
    assert json.loads(out.read_text(encoding="utf-8"))["artifacts"][0]["payload"] == {"00": 5}


class TestVerdictBounds:
    """The verdict file is the other way out of this process, so it has a size too.

    Clipping used to reach the top-level strings and nothing else, so an artifact
    payload travelled whole: a check returning a megabyte of text put all of it in
    the parent's memory and then on the terminal.
    """

    def test_a_giant_artifact_payload_is_clipped(self, tmp_path: Path) -> None:
        huge = "A" * (worker_module.MAX_FIELD_CHARS * 3)
        out = tmp_path / "r.json"
        worker_module._write(
            out,
            {
                "outcome": "pass",
                "artifacts": [{"kind": "text", "caption": "c", "payload": huge, "meta": {}}],
            },
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        shown = payload["artifacts"][0]["payload"]
        assert payload["outcome"] == "pass", "a long artifact is not a failed answer"
        assert "further characters were cut" in shown
        assert len(shown) < worker_module.MAX_FIELD_CHARS + 200

    def test_artifacts_too_large_as_a_whole_are_replaced(self, tmp_path: Path) -> None:
        """Clipping strings cannot shrink a dict of two hundred thousand keys."""
        out = tmp_path / "r.json"
        worker_module._write(
            out,
            {
                "outcome": "pass",
                "artifacts": [
                    {
                        "kind": "counts",
                        "caption": "c",
                        "payload": {str(index): index for index in range(200_000)},
                        "meta": {},
                    }
                ],
            },
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["outcome"] == "pass"
        assert payload["artifacts"][0]["caption"] == "artifacts too large to show"
        assert len(out.read_text(encoding="utf-8")) < worker_module.MAX_ARTIFACT_CHARS + 2000

    def test_a_self_referential_payload_does_not_recurse_forever(self) -> None:
        """Why the depth stop exists. Without it this call raises RecursionError."""
        loop: dict = {"kind": "text"}
        loop["self"] = loop
        assert worker_module._clip_strings(loop)["kind"] == "text"

    def test_a_tuple_payload_travels_as_a_list(self) -> None:
        """json writes a tuple as an array, so the clipped copy is a list too."""
        assert worker_module._clip_strings({"payload": ("a", 2, None)})["payload"] == ["a", 2, None]

    def test_a_payload_json_cannot_walk_is_reported_not_fatal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A deeply nested payload makes json.dumps raise RecursionError.

        Raised here rather than nested for real, because the depth json gives up
        at is a property of the stack, not of anything this project sets. Left
        uncaught it killed the worker before it wrote anything, and the parent
        reported that as the learner stopping the process.
        """

        def boom(payload: dict) -> dict:
            raise RecursionError("maximum recursion depth exceeded")

        monkeypatch.setattr(worker_module, "_bounded", boom)
        out = tmp_path / "r.json"
        worker_module._write(out, {"outcome": "pass", "artifacts": []})

        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["outcome"] == "internal_error"
        assert payload["error_type"] == "RecursionError"

    def test_a_deeply_nested_payload_always_leaves_a_verdict(self, tmp_path: Path) -> None:
        """The real thing, asserting only what holds at every stack size."""
        deep: list = []
        cursor = deep
        for _ in range(50_000):
            child: list = []
            cursor.append(child)
            cursor = child

        out = tmp_path / "r.json"
        worker_module._write(
            out, {"outcome": "pass", "artifacts": [{"kind": "text", "payload": deep}]}
        )
        assert json.loads(out.read_text(encoding="utf-8"))["outcome"] in ("pass", "internal_error")

    def test_a_warning_repeated_is_reported_once(self) -> None:
        """The same DeprecationWarning fires on every call inside a loop."""
        from types import SimpleNamespace

        caught = [
            SimpleNamespace(message="qiskit is deprecating something"),
            SimpleNamespace(message="qiskit is deprecating something"),
            SimpleNamespace(message="   "),
        ]
        assert worker_module._format_warnings(caught) == ["qiskit is deprecating something"]

    def test_the_fallback_cannot_be_broken_by_its_own_warnings(self, tmp_path: Path) -> None:
        """Whatever would not serialize may sit in the warnings as well."""
        out = tmp_path / "r.json"
        worker_module._write(
            out,
            {"outcome": "pass", "artifacts": [{"payload": {1, 2}}], "warnings": [{3, 4}]},
        )
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["outcome"] == "internal_error"
        assert len(payload["warnings"]) == 1
        assert "3" in payload["warnings"][0]
