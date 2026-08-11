"""The palette holds everywhere, and nothing outside theme.py names a colour.

Two layers. The static one reads the source and refuses any colour literal
outside the palette module. The rendering one drives the real UI functions
through a truecolour console and inspects the escape sequences that come out,
which is the only way to catch a colour rich supplies on our behalf: its default
markdown styles and its automatic highlighter both did exactly that.
"""

from __future__ import annotations

import ast
import io
import re
from pathlib import Path

import pytest
from rich.color import ANSI_COLOR_NAMES
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

from quantum_exercises import theme, ui
from quantum_exercises.runner import RunResult

PALETTE = {
    theme.BACKGROUND: "BACKGROUND",
    theme.SURFACE: "SURFACE",
    theme.ACCENT: "ACCENT",
    theme.TEXT: "TEXT",
    theme.MUTED: "MUTED",
    theme.OUTLINE: "OUTLINE",
    theme.TEXT_DIM: "TEXT_DIM",
}
PALETTE_RGB = {
    tuple(int(hex_colour[i : i + 2], 16) for i in (1, 3, 5)): name
    for hex_colour, name in PALETTE.items()
}

# Basic and bright SGR colour codes. Anything here means a named colour reached
# the terminal, which is what the palette is meant to have replaced.
LEGACY_SGR = set(range(30, 38)) | set(range(40, 48)) | set(range(90, 98)) | set(range(100, 108))

HEX_COLOUR = re.compile(r"#[0-9a-fA-F]{6}\b")


def _parse_sgr(data: bytes) -> tuple[set[tuple[int, int, int]], set[int], set[int]]:
    """Walk SGR parameters properly: 38 and 48 consume their own arguments.

    Splitting naively reads the blue channel of #3d3f60 as the code for bright
    cyan, which is how an earlier version of this check reported false leaks.
    """
    truecolour: set[tuple[int, int, int]] = set()
    legacy: set[int] = set()
    indexed: set[int] = set()

    for match in re.finditer(rb"\x1b\[([\d;]*)m", data):
        params = [int(p) for p in match.group(1).split(b";") if p != b""]
        index = 0
        while index < len(params):
            code = params[index]
            if code in (38, 48) and index + 1 < len(params):
                mode = params[index + 1]
                if mode == 2 and index + 4 < len(params):
                    truecolour.add(tuple(params[index + 2 : index + 5]))
                    index += 5
                    continue
                if mode == 5 and index + 2 < len(params):
                    indexed.add(params[index + 2])
                    index += 3
                    continue
            if code in LEGACY_SGR:
                legacy.add(code)
            index += 1
    return truecolour, legacy, indexed


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> Console:
    """A console that emits truecolour into a buffer, styled like the real one."""
    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    console = Console(
        file=stream,
        force_terminal=True,
        color_system="truecolor",
        width=100,
        highlight=False,
        theme=Theme(theme.RICH_OVERRIDES),
    )
    monkeypatch.setattr(ui, "console", console)
    return console


def _emitted(console: Console) -> bytes:
    console.file.flush()
    return console.file.buffer.getvalue()


def _assert_palette_only(console: Console, what: str) -> None:
    truecolour, legacy, indexed = _parse_sgr(_emitted(console))

    strangers = {
        f"#{r:02x}{g:02x}{b:02x}" for r, g, b in truecolour if (r, g, b) not in PALETTE_RGB
    }
    assert not strangers, f"{what} emitted colours outside the palette: {sorted(strangers)}"
    assert not legacy, f"{what} emitted named SGR colours: {sorted(legacy)}"
    assert not indexed, f"{what} emitted 256-colour codes: {sorted(indexed)}"


class TestNothingOutsideThemeNamesAColour:
    """Static: no colour literal may appear anywhere but the palette module."""

    def test_source_contains_no_colour_literals(self, root: Path) -> None:
        colour_names = set(ANSI_COLOR_NAMES)
        offenders: list[str] = []

        for path in sorted((root / "src").rglob("*.py")):
            if path.name == "theme.py":
                continue  # the one place colours are allowed to be written down
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                literal = node.value
                if HEX_COLOUR.search(literal):
                    offenders.append(f"{path.name}:{node.lineno} hex colour in {literal!r}")
                    continue
                # A style string is a short run of words; prose is not.
                words = literal.split()
                if 0 < len(words) <= 4 and any(w.lower() in colour_names for w in words):
                    offenders.append(f"{path.name}:{node.lineno} named colour in {literal!r}")

        assert not offenders, "colours named outside theme.py:\n  " + "\n  ".join(offenders)

    def test_the_palette_is_a_closed_set(self) -> None:
        """Seven values: the six specified, plus one derived for secondary prose."""
        assert len(PALETTE) == 7
        for hex_colour in PALETTE:
            assert HEX_COLOUR.fullmatch(hex_colour), hex_colour


class TestRenderedOutputUsesOnlyThePalette:
    def test_the_progress_listing(self, captured: Console, exercises: list, root: Path) -> None:
        from quantum_exercises.state import State

        state = State()
        state.mark_done(exercises[0].slug)
        state.mark_solved(exercises[1].slug)
        state.mark_done(exercises[2].slug, ran_on="hardware")
        ui.render_list(exercises, state)
        _assert_palette_only(captured, "qx list")

    def test_a_passing_run_with_every_artifact_kind(
        self, captured: Console, exercises: list, root: Path
    ) -> None:
        result = RunResult(
            outcome="pass",
            artifacts=[
                {"kind": "counts", "caption": "c", "payload": {"00": 512, "11": 512}, "meta": {}},
                {
                    "kind": "statevector",
                    "caption": "s",
                    "payload": [[0.707, 0.0], [0.0, 0.707]],
                    "meta": {"num_qubits": 1},
                },
                {"kind": "matrix", "caption": "m", "payload": [[[1.0, 0.0]]], "meta": {}},
                {"kind": "text", "caption": "t", "payload": "plain", "meta": {}},
                {"kind": "unknown", "caption": "u", "payload": 7, "meta": {}},
            ],
            stdout="something the learner printed\n",
            duration=0.5,
        )
        ui.render_run(exercises[0], result, root=root)
        _assert_palette_only(captured, "a passing run")

    @pytest.mark.parametrize("outcome", ["fail", "error", "timeout", "crash", "internal_error"])
    def test_every_failure_shape(
        self, outcome: str, captured: Console, exercises: list, root: Path
    ) -> None:
        result = RunResult(
            outcome=outcome,
            message="something went wrong",
            detail="a longer explanation",
            hint="try this instead",
            line=3,
            stderr="a traceback would go here",
            warnings=["a warning"],
        )
        ui.render_run(exercises[0], result, root=root)
        _assert_palette_only(captured, f"a {outcome} run")

    def test_the_next_panel(self, captured: Console, exercises: list) -> None:
        ui.render_next(exercises[0])
        _assert_palette_only(captured, "qx next")

    def test_the_plain_message_helpers(self, captured: Console) -> None:
        ui.success("done")
        ui.info("noted")
        ui.warn("careful")
        ui.error("broken")
        _assert_palette_only(captured, "the message helpers")

    def test_hint_markdown_including_fenced_code(self, captured: Console, exercises: list) -> None:
        """rich styles markdown in named colours by default, and hints are markdown."""
        from quantum_exercises.registry import load_hints

        for hint in load_hints(exercises[0]):
            captured.print(Markdown(hint, code_theme=theme.SYNTAX_THEME))
        _assert_palette_only(captured, "a rendered hint")

    def test_every_hint_in_the_course(self, captured: Console, exercises: list) -> None:
        from quantum_exercises.registry import load_hints

        for exercise in exercises:
            for hint in load_hints(exercise):
                captured.print(Markdown(hint, code_theme=theme.SYNTAX_THEME))
        _assert_palette_only(captured, "the hints of every exercise")

    def test_revealed_solution_syntax_highlighting(
        self, captured: Console, exercises: list
    ) -> None:
        from rich.syntax import Syntax

        for exercise in exercises:
            code = exercise.solution_file.read_text(encoding="utf-8")
            captured.print(Syntax(code, "python", theme=theme.SYNTAX_THEME, line_numbers=False))
        _assert_palette_only(captured, "a revealed solution")


class TestBarColouring:
    def test_the_track_is_not_the_fill_colour(self, captured: Console) -> None:
        """The accent fills area only where it means something: the bar itself."""
        bar = ui._bar_text(0.5, width=20, track=ui._TRACK)
        captured.print(bar)
        truecolour, _, _ = _parse_sgr(_emitted(captured))
        names = {PALETTE_RGB[rgb] for rgb in truecolour if rgb in PALETTE_RGB}
        assert "ACCENT" in names, "the filled part should carry the accent"
        assert "MUTED" in names, "the empty track should be muted, not accented"

    # The two shapes the tool actually draws: a histogram row and the progress bar.
    @pytest.mark.parametrize(("width", "track"), [(34, " "), (28, ui._TRACK)])
    @pytest.mark.parametrize("numerator", range(0, 21))
    def test_the_colour_changes_exactly_where_the_fill_ends(
        self, captured: Console, width: int, track: str, numerator: int
    ) -> None:
        """Off by one here paints a cell of track in the fill colour, or the reverse.

        The count is worked out here rather than read back off the bar. Deriving it
        from _bar would only prove the drawing agrees with itself, and a bar that
        filled one cell too many would satisfy that happily.
        """
        fraction = numerator / 20
        filled = int(fraction * width)
        drawn = ui._bar(fraction, width=width, track=track)
        assert drawn.count(ui._FULL) == filled, f"{drawn!r} does not fill {filled} cells"

        captured.print(ui._bar_text(fraction, width=width, track=track))
        emitted = _emitted(captured).decode("utf-8")

        def sgr(colour: str) -> str:
            red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
            return f"\x1b[38;2;{red};{green};{blue}m"

        # Whatever rich does with spans, the visible run of fill has to be this long
        # and the track has to be recoloured the moment it stops.
        if filled:
            assert sgr(theme.ACCENT) in emitted
            assert ui._FULL * filled in emitted
        if filled < width:
            assert sgr(theme.MUTED) in emitted, "the track must not stay in the fill colour"
            assert ui._FULL * (filled + 1) not in emitted, "one cell too many is filled"


class TestStatusColours:
    """Three states, three appearances. Two of them used to look identical."""

    def test_every_status_is_told_apart_from_the_others(self) -> None:
        styles = {label: style for label, (_, style) in ui.STATUS_STYLE.items()}
        assert len(set(styles.values())) == 3, (
            f"two statuses share a style, so `qx list` cannot show them apart: {styles}"
        )

    def test_solved_reads_between_todo_and_done(self) -> None:
        """It counts toward the progress bar, so it must not look unstarted.

        It was reached by revealing the answer, so it does not get the weight
        that `done` carries either.
        """
        assert theme.ACCENT in theme.STATUS_SOLVED, "solved counts as finished"
        assert theme.ACCENT not in theme.STATUS_TODO, "todo does not"
        assert "bold" in theme.STATUS_DONE and "bold" not in theme.STATUS_SOLVED
