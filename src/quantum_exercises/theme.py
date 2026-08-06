"""The colour palette. Every style in the tool resolves from here.

One rule governs the whole scheme: the accent appears as a line, an outline or a
run of glyphs, never as a filled background. The histogram bars are the single
exception, and they are the one place where filled area carries meaning.

Nothing outside this module names a colour.
"""

from __future__ import annotations

from pygments.style import Style as PygmentsStyle
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Token,
)

# --------------------------------------------------------------------------
# The palette
# --------------------------------------------------------------------------

BACKGROUND = "#161826"  # banners, badges, boxes
SURFACE = "#1a1e30"  # raised surfaces sitting on the background
ACCENT = "#9184d9"  # blurple: headings, figures, bars, rules
TEXT = "#e9e9ed"  # body text on a dark ground
MUTED = "#343856"  # dimmed dots and borders
OUTLINE = "#3d3f60"  # inactive outlines

# Secondary prose. Derived, not invented: TEXT blended 30% toward BACKGROUND,
# which lands at 7.6:1 contrast. The palette as specified has nothing between
# TEXT at 14.5:1 and OUTLINE at 1.7:1, and MUTED and OUTLINE are for dots and
# borders rather than words. Using the terminal's dim attribute instead made
# whole lines unreadable on a real display.
TEXT_DIM = "#aaaab1"

# --------------------------------------------------------------------------
# Semantic styles
# --------------------------------------------------------------------------

# Text. Reduced emphasis comes from TEXT_DIM, never from the terminal's dim
# attribute, which halves the intensity of whatever it is applied to and takes
# the result below the point where it can be read.
TITLE = f"bold {ACCENT}"
HEADING = f"bold {ACCENT}"
BODY = TEXT
STRONG = f"bold {TEXT}"
DETAIL = TEXT_DIM
FIGURE = ACCENT  # numbers, keys, identifiers
PATH = ACCENT  # a file the reader has to go and open
COMMAND = f"bold {TEXT}"  # something to type

# Surfaces.
PANEL = f"on {BACKGROUND}"
RAISED = f"on {SURFACE}"

# Borders. Weight and colour together carry severity, since the palette holds no
# separate error hue: an outline that is merely inactive reads as "not yet", and
# an accented one reads as "this is the result".
BORDER = OUTLINE
BORDER_ACTIVE = ACCENT
BORDER_QUIET = MUTED

# Progress and histograms, the one place the accent fills area.
BAR = ACCENT
BAR_TRACK = MUTED

# Exercise status.
STATUS_TODO = DETAIL
STATUS_DONE = f"bold {ACCENT}"
STATUS_SOLVED = TEXT_DIM  # reached, but by revealing the answer

# Environment checks.
CHECK_OK = ACCENT
CHECK_WARN = DETAIL
CHECK_FAIL = f"bold {ACCENT}"


# Rich ships its own styles for markdown, which reach the screen through `qx hint`
# and are written in named colours: markdown.code alone is "bold cyan on black".
# Every one is overridden here, or the palette would hold everywhere except the
# hints. Passed to the Console, so nothing has to remember to apply it.
RICH_OVERRIDES = {
    "markdown.block_quote": DETAIL,
    "markdown.code": f"{ACCENT} on {SURFACE}",
    "markdown.code_block": f"{TEXT} on {BACKGROUND}",
    "markdown.em": "italic",
    "markdown.emph": "italic",
    "markdown.h1": f"bold {ACCENT}",
    "markdown.h1.border": OUTLINE,
    "markdown.h2": f"bold {ACCENT}",
    "markdown.h3": f"bold {ACCENT}",
    "markdown.h4": ACCENT,
    "markdown.h5": ACCENT,
    "markdown.h6": DETAIL,
    "markdown.h7": DETAIL,
    "markdown.hr": OUTLINE,
    "markdown.item": TEXT,
    "markdown.item.bullet": ACCENT,
    "markdown.item.number": ACCENT,
    "markdown.kbd": f"bold {ACCENT}",
    "markdown.link": ACCENT,
    "markdown.link_url": f"underline {ACCENT}",
    "markdown.list": TEXT,
    "markdown.paragraph": TEXT,
    "markdown.s": "strike",
    "markdown.strong": f"bold {TEXT}",
    "markdown.table.border": OUTLINE,
    "markdown.table.header": f"bold {ACCENT}",
    "markdown.text": TEXT,
    # Table and rule chrome, so a default never shows through.
    "rule.line": ACCENT,
    "rule.text": f"bold {ACCENT}",
    "table.header": f"bold {ACCENT}",
    "table.footer": DETAIL,
    "table.title": f"bold {ACCENT}",
    "table.caption": DETAIL,
}


# Syntax highlighting for revealed solutions. A stock highlighting theme emits
# dozens of hues from outside this palette, so the highlighter is built from it
# instead: structure carries the accent, everything else is body text.
class SyntaxStyle(PygmentsStyle):
    background_color = BACKGROUND
    line_number_color = OUTLINE
    line_number_background_color = BACKGROUND

    styles = {  # noqa: RUF012 - the shape pygments requires
        Token: TEXT,
        Comment: f"italic {OUTLINE}",
        Keyword: f"bold {ACCENT}",
        Keyword.Constant: ACCENT,
        Name.Builtin: ACCENT,
        Name.Function: ACCENT,
        Name.Class: f"bold {ACCENT}",
        Name.Decorator: ACCENT,
        String: TEXT,
        String.Doc: f"italic {OUTLINE}",
        Number: ACCENT,
        Operator: OUTLINE,
        Punctuation: OUTLINE,
        Error: f"bold {ACCENT}",
    }


SYNTAX_THEME = SyntaxStyle

__all__ = [
    "RICH_OVERRIDES",
    "ACCENT",
    "BACKGROUND",
    "BAR",
    "BAR_TRACK",
    "BODY",
    "BORDER",
    "BORDER_ACTIVE",
    "BORDER_QUIET",
    "CHECK_FAIL",
    "CHECK_OK",
    "CHECK_WARN",
    "COMMAND",
    "DETAIL",
    "FIGURE",
    "HEADING",
    "MUTED",
    "OUTLINE",
    "PANEL",
    "PATH",
    "RAISED",
    "STATUS_DONE",
    "STATUS_SOLVED",
    "STATUS_TODO",
    "STRONG",
    "SURFACE",
    "SYNTAX_THEME",
    "TEXT",
    "TEXT_DIM",
    "TITLE",
]
