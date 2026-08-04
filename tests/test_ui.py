"""Rendering. These assert on characters, not on how pretty the result is."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from quantum_exercises import ui


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
