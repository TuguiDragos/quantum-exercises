"""Rendering. These assert on characters, not on how pretty the result is."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from quantum_exercises import registry, ui


def _console_with_encoding(encoding: str) -> Console:
    return Console(file=io.TextIOWrapper(io.BytesIO(), encoding=encoding), width=80)


class TestBar:
    def test_uses_blocks_when_the_encoding_allows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ui, "console", _console_with_encoding("utf-8"))
        assert "█" in ui._bar(0.5, width=10)

    def test_falls_back_to_ascii(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A terminal that cannot encode blocks must still get a readable bar."""
        monkeypatch.setattr(ui, "console", _console_with_encoding("ascii"))
        bar = ui._bar(0.5, width=10, track=ui._TRACK)
        assert "█" not in bar
        assert "░" not in bar
        bar.encode("ascii")  # the point of the fallback: this must not raise

    def test_width_is_exact_in_both_modes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for encoding in ("utf-8", "ascii"):
            monkeypatch.setattr(ui, "console", _console_with_encoding(encoding))
            for fraction in (0.0, 0.13, 0.5, 0.99, 1.0):
                assert len(ui._bar(fraction, width=20, track=ui._TRACK)) == 20, (
                    f"{encoding} at {fraction}"
                )

    def test_width_holds_for_every_fraction(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A bar that is one cell short or long breaks the alignment of `qx list`.

        Swept rather than sampled: the partial cell is picked by rounding, so the
        interesting fractions are the ones between the five above.
        """
        for encoding in ("utf-8", "ascii"):
            monkeypatch.setattr(ui, "console", _console_with_encoding(encoding))
            for width in (1, 7, 20, 34):
                for step in range(201):
                    fraction = step / 200
                    rendered = ui._bar(fraction, width=width, track=ui._TRACK)
                    assert len(rendered) == width, f"{encoding} w={width} at {fraction}"

    def test_clamps_out_of_range_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ui, "console", _console_with_encoding("utf-8"))
        assert len(ui._bar(-5.0, width=8)) == 8
        assert ui._bar(9.0, width=8).strip() == "█" * 8


class TestComplexFormatting:
    @pytest.mark.parametrize(
        ("real", "imaginary", "expected"),
        [
            (0.0, 0.0, "0"),
            (1e-12, -1e-12, "0"),
            (0.7071, 0.0, "0.707"),
            (0.0, 0.7071, "0.707i"),
            (0.0, -0.7071, "-0.707i"),
            (0.5, 0.5, "0.500+0.500i"),
            (0.5, -0.5, "0.500-0.500i"),
        ],
    )
    def test_formats(self, real: float, imaginary: float, expected: str) -> None:
        assert ui._fmt_complex(real, imaginary) == expected


class TestArtifactRendering:
    def test_every_artifact_kind_renders(self, monkeypatch: pytest.MonkeyPatch) -> None:
        console = _console_with_encoding("utf-8")
        monkeypatch.setattr(ui, "console", console)
        artifacts = [
            {"kind": "counts", "caption": "c", "payload": {"00": 5, "11": 3}, "meta": {}},
            {
                "kind": "statevector",
                "caption": "s",
                "payload": [[0.707, 0.0], [0.0, 0.707]],
                "meta": {"num_qubits": 1},
            },
            {"kind": "matrix", "caption": "m", "payload": [[[1.0, 0.0], [0.0, 0.0]]], "meta": {}},
            {"kind": "text", "caption": "t", "payload": "hello", "meta": {}},
            {"kind": "unknown-kind", "caption": "u", "payload": 42, "meta": {}},
        ]
        for artifact in artifacts:
            console.print(ui.render_artifact(artifact))

    def test_counts_panel_reports_the_total(self, monkeypatch: pytest.MonkeyPatch) -> None:
        console = _console_with_encoding("utf-8")
        monkeypatch.setattr(ui, "console", console)
        console.print(ui.render_counts({"0": 400, "1": 624}, "caption"))
        console.file.flush()
        rendered = console.file.buffer.getvalue().decode("utf-8")
        assert "1024 shots" in rendered
        assert "39.1%" in rendered  # 400 / 1024


class TestBarHasNoGaps:
    """A partial cell that renders as blank punches a hole in the bar."""

    @pytest.mark.parametrize("encoding", ["utf-8", "ascii"])
    def test_no_blank_between_the_fill_and_the_track(
        self, encoding: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ui, "console", _console_with_encoding(encoding))
        for numerator in range(0, 15):
            bar = ui._bar(numerator / 14, width=28, track=ui._TRACK)
            assert " " not in bar, f"{encoding} at {numerator}/14: {bar!r}"
            assert len(bar) == 28


class TestMetadataOnlyArtifacts:
    """An artifact can carry only metadata. It must not draw an empty box."""

    def test_a_marker_artifact_renders_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from quantum_exercises.registry import Exercise
        from quantum_exercises.runner import RunResult

        console = _console_with_encoding("utf-8")
        monkeypatch.setattr(ui, "console", console)

        exercise = Exercise(
            slug="01_demo",
            number=1,
            path=Path("/tmp/01_demo"),
            title="Demo",
            act="Act I",
            summary="s",
            hardware=False,
            timeout=10,
        )
        result = RunResult(
            outcome="pass",
            artifacts=[
                {"kind": "text", "caption": "", "payload": "", "meta": {"ran_on": "hardware"}},
            ],
        )
        ui.render_run(exercise, result, root=Path("/tmp"))
        console.file.flush()
        rendered = console.file.buffer.getvalue().decode("utf-8")
        assert "┌" not in rendered, "a metadata-only artifact drew a box"
        assert "PASS" in rendered


def test_safe_replaces_unencodable_characters(monkeypatch) -> None:
    monkeypatch.setattr(ui.console, "file", SimpleNamespace(encoding="ascii"))
    assert "?" in ui._safe("box → drawing")


def test_safe_passes_text_through_without_an_encoding(monkeypatch) -> None:
    """An in-memory buffer has no encoding to fail against, so nothing is replaced."""
    monkeypatch.setattr(ui.console, "file", SimpleNamespace(encoding=None))
    assert ui._safe("box → drawing") == "box → drawing"


def test_supports_blocks_without_an_encoding(monkeypatch) -> None:
    monkeypatch.setattr(ui.console, "file", SimpleNamespace(encoding=None))
    assert ui._supports_blocks() is True


@pytest.mark.parametrize(
    ("encoding", "supported"),
    [
        ("utf-8", True),
        # The default code page of a legacy Windows console. It carries both of
        # the characters the bar draws, and only failed this before because the
        # question asked about a ramp of partial cells the bar no longer uses.
        ("cp437", True),
        ("cp850", True),
        ("latin-1", False),
        ("ascii", False),
    ],
)
def test_supports_blocks_asks_only_about_what_is_drawn(
    monkeypatch, encoding: str, supported: bool
) -> None:
    monkeypatch.setattr(ui.console, "file", SimpleNamespace(encoding=encoding))
    assert ui._supports_blocks() is supported
    # Whatever the answer, the bar has to be encodable in that terminal.
    monkeypatch.setattr(ui, "console", _console_with_encoding(encoding))
    ui._bar(0.5, width=10, track=ui._TRACK).encode(encoding)


def test_save_progress_reports_an_unwritable_root(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises.state import State

    monkeypatch.setattr(
        "quantum_exercises.ui.save",
        lambda root, state: (_ for _ in ()).throw(OSError(13, "Permission denied")),
    )
    assert ui.save_progress(tmp_path, State()) is False


def test_save_progress_warns_about_a_preserved_file(tmp_path: Path, monkeypatch) -> None:
    from quantum_exercises.state import State

    monkeypatch.setattr(
        "quantum_exercises.ui.save", lambda root, state: tmp_path / ".qx-state.json.unreadable"
    )
    assert ui.save_progress(tmp_path, State()) is True


def test_display_path_falls_back_to_absolute(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    other = Path("/usr/local/share/qx/exercise.py")
    assert ui._display_path(other) == str(other.resolve())


def test_render_failure_handles_a_path_outside_the_root(tmp_path: Path, root: Path) -> None:
    from quantum_exercises.runner import RunResult

    exercise = registry.load_exercises(root)[0]
    result = RunResult(outcome="error", message="boom", line=3)
    ui.render_run(exercise, result, root=tmp_path)  # root unrelated to the exercise path


def test_render_artifact_falls_back_to_text() -> None:
    panel = ui.render_artifact({"kind": "mystery", "caption": "c", "payload": {"a": 1}})
    assert panel is not None


@pytest.mark.parametrize(
    "artifact",
    [
        {"kind": "matrix", "caption": "m", "payload": [1, 2, 3]},
        {"kind": "statevector", "caption": "s", "payload": [1, 2]},
        {"kind": "counts", "caption": "c", "payload": {"00": "many"}},
        {
            "kind": "statevector",
            "caption": "s",
            "payload": [[0.0, 0.0]],
            "meta": {"num_qubits": "x"},
        },
    ],
    ids=["matrix-rows", "statevector-scalars", "counts-strings", "meta-not-a-number"],
)
def test_a_misshapen_payload_is_shown_rather_than_raised(artifact: dict) -> None:
    """The check already passed. A bad artifact must not turn that into a traceback.

    Every case here raised TypeError or ValueError out of the renderer and reached
    the learner's terminal as one.
    """
    assert ui.render_artifact(artifact) is not None


def test_render_counts_with_all_zero_values() -> None:
    assert ui.render_counts({"00": 0, "11": 0}, "empty") is not None


def test_bar_clamps_out_of_range_fractions() -> None:
    assert ui._bar(-1.0).strip() == ""
    assert ui._bar(2.0).count("█") == ui.BAR_WIDTH
