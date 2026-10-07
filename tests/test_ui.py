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
        """A bar a cell short or long breaks `qx list` alignment."""
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


def _console_reporting(encoding: str | None) -> SimpleNamespace:
    """A stand-in console whose file claims one encoding.

    Patching `file` on the real console would pin it to the current stdout on
    teardown and break later CliRunner captures.
    """
    return SimpleNamespace(file=SimpleNamespace(encoding=encoding))


def test_safe_replaces_unencodable_characters(monkeypatch) -> None:
    monkeypatch.setattr(ui, "console", _console_reporting("ascii"))
    assert "?" in ui._safe("box → drawing")


def test_safe_passes_text_through_without_an_encoding(monkeypatch) -> None:
    """An in-memory buffer has no encoding to fail against, so nothing is replaced."""
    monkeypatch.setattr(ui, "console", _console_reporting(None))
    assert ui._safe("box → drawing") == "box → drawing"


def test_supports_blocks_without_an_encoding(monkeypatch) -> None:
    monkeypatch.setattr(ui, "console", _console_reporting(None))
    assert ui._supports_blocks() is True


def test_patching_the_console_file_does_not_outlive_the_test(monkeypatch) -> None:
    """The trap the helper above avoids. If rich stops doing this, the helper can go."""
    console = ui.console
    assert console._file is None, "the shared console must follow sys.stdout"

    monkeypatch.setattr(console, "file", SimpleNamespace(encoding=None))
    monkeypatch.undo()

    assert console._file is not None, "rich no longer pins the file; _console_reporting can go"
    console._file = None  # put it back, or every later test writes to the wrong stream


@pytest.mark.parametrize(
    ("encoding", "supported"),
    [
        ("utf-8", True),
        # The default code page of a legacy Windows console; it carries both bar characters.
        ("cp437", True),
        ("cp850", True),
        ("latin-1", False),
        ("ascii", False),
    ],
)
def test_supports_blocks_asks_only_about_what_is_drawn(
    monkeypatch, encoding: str, supported: bool
) -> None:
    monkeypatch.setattr(ui, "console", _console_reporting(encoding))
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


def test_render_failure_handles_a_path_outside_the_root(
    tmp_path: Path, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """relative_to raises outside the root, so the full absolute path is shown instead."""
    console = Console(file=io.StringIO(), width=200)
    monkeypatch.setattr(ui, "console", console)
    from quantum_exercises.runner import RunResult

    exercise = registry.load_exercises(root)[0]
    ui.render_run(exercise, RunResult(outcome="error", message="boom", line=3), root=tmp_path)

    shown = console.file.getvalue()
    assert f"{exercise.exercise_file}:3" in shown


def test_render_artifact_falls_back_to_text() -> None:
    """A kind no renderer knows still has to draw, and to carry its payload."""
    panel = ui.render_artifact({"kind": "mystery", "caption": "c", "payload": {"a": 1}})
    console = Console(file=io.StringIO(), width=200)
    console.print(panel)
    shown = console.file.getvalue()
    assert "'a': 1" in shown
    assert "c" in shown


class TestTheBackendALearnerReached:
    """`qx list` says which backend exercise 14 ran on."""

    @staticmethod
    def _listing(kind: str | None, root: Path, monkeypatch) -> str:
        from quantum_exercises.state import State

        console = Console(file=io.StringIO(), width=200)
        monkeypatch.setattr(ui, "console", console)
        exercises = registry.load_exercises(root)
        state = State()
        state.mark_done(exercises[13].slug, ran_on=kind)
        ui.render_list(exercises, state)
        return console.file.getvalue()

    def test_a_real_qpu_is_named_as_one(self, root: Path, monkeypatch) -> None:
        assert "done (QPU)" in self._listing("hardware", root, monkeypatch)

    def test_a_noisy_simulator_is_told_apart_from_a_plain_one(
        self, root: Path, monkeypatch
    ) -> None:
        assert "done (noisy)" in self._listing("noisy_simulator", root, monkeypatch)
        assert "done (sim)" in self._listing("simulator", root, monkeypatch)

    def test_a_backend_nobody_recognises_is_shown_as_it_came(self, root: Path, monkeypatch) -> None:
        """RAN_ON_LABEL is a shortening, not a filter: an unknown kind still shows."""
        assert "done (ibm_fez)" in self._listing("ibm_fez", root, monkeypatch)

    def test_an_exercise_that_never_reached_a_backend_says_only_done(
        self, root: Path, monkeypatch
    ) -> None:
        listing = self._listing(None, root, monkeypatch)
        assert "done" in listing
        assert "done (" not in listing


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
    """The check already passed. A bad artifact must not turn that into a traceback."""
    assert ui.render_artifact(artifact) is not None


def test_render_counts_with_all_zero_values() -> None:
    assert ui.render_counts({"00": 0, "11": 0}, "empty") is not None


def test_bar_clamps_out_of_range_fractions() -> None:
    assert ui._bar(-1.0).strip() == ""
    assert ui._bar(2.0).count("█") == ui.BAR_WIDTH


class TestProse:
    def test_backticks_become_styles_not_characters(self) -> None:
        text = ui.prose("Run `qx next`, then set `qiskit_version`.", "plain")
        assert text.plain == "Run qx next, then set qiskit_version."
        styles = {text.plain[span.start : span.end]: span.style for span in text.spans}
        assert styles == {"qx next": ui.theme.COMMAND, "qiskit_version": ui.theme.CODE}

    @pytest.mark.parametrize(
        "command", ["qx", "qx hint 3", "uv run qx", "uv run qx next", "uv sync", "git status"]
    )
    def test_commands_are_drawn_as_commands(self, command: str) -> None:
        text = ui.prose(f"`{command}`", "plain")
        assert [span.style for span in text.spans] == [ui.theme.COMMAND]

    def test_a_lone_backtick_is_left_alone(self) -> None:
        assert ui.prose("it's a ` mark", "plain").plain == "it's a ` mark"


def test_wrapped_messages_keep_their_indent(monkeypatch: pytest.MonkeyPatch) -> None:
    console = Console(file=io.StringIO(), width=30)
    monkeypatch.setattr(ui, "console", console)
    ui.info("one two three four five six seven eight nine ten")
    lines = console.file.getvalue().splitlines()
    assert len(lines) > 1
    assert all(line.startswith("  ") and not line.startswith("   ") for line in lines)


def test_plural() -> None:
    assert (ui.plural(1, "hint"), ui.plural(2, "hint"), ui.plural(0, "file")) == (
        "1 hint",
        "2 hints",
        "0 files",
    )


def test_hint_code_blocks_have_no_padding_rows() -> None:
    console = Console(file=io.StringIO(), width=40)
    console.print(ui.markdown("Before.\n\n```python\nx = 1\n```\n\nAfter."))
    lines = console.file.getvalue().splitlines()
    code = next(i for i, line in enumerate(lines) if "x = 1" in line)
    assert lines[code - 1].strip() == "" and lines[code - 2].strip() == "Before."
    assert lines[code + 1].strip() == "" and lines[code + 2].strip() == "After."


class TestFewColors:
    """A 256-color terminal rounds the two dark surfaces to black and navy."""

    @staticmethod
    def _console(system: str) -> Console:
        return Console(file=io.StringIO(), force_terminal=True, color_system=system)

    def test_truecolor_keeps_the_palette(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ui, "console", self._console("truecolor"))
        assert ui.panel()["style"] == ui.theme.PANEL
        assert ui.panel(raised=True)["style"] == ui.theme.RAISED
        assert ui.syntax_theme() is ui.theme.SYNTAX_THEME

    def test_256_colors_get_the_greys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ui, "console", self._console("256"))
        assert ui.panel()["style"] == f"on {ui.theme.BACKGROUND_256}"
        assert ui.panel(raised=True)["style"] == f"on {ui.theme.SURFACE_256}"
        assert ui.syntax_theme() is ui.theme.SYNTAX_THEME_256
        code = ui.prose("`x`", "plain").spans[0].style
        assert ui.theme.SURFACE_256 in code and ui.theme.SURFACE not in code

    def test_the_greys_land_on_the_256_ramp_as_is(self) -> None:
        console = self._console("256")
        for grey, index in ((ui.theme.BACKGROUND_256, 234), (ui.theme.SURFACE_256, 235)):
            console.print("x", style=f"on {grey}")
            assert f"48;5;{index}m" in console.file.getvalue()

    @pytest.mark.parametrize("system", ["truecolor", "256"])
    def test_fit_theme_touches_only_consoles_with_few_colors(self, system: str) -> None:
        console = self._console(system)
        ui.fit_theme(console)
        code_block = str(console.get_style("markdown.code_block"))
        assert (ui.theme.BACKGROUND_256 in code_block) == (system == "256")
