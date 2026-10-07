"""The color palette. Every style in the tool resolves from here.

The accent appears as a line, outline or glyphs, never as a filled background,
except in histogram bars. Nothing outside this module names a color.
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

# Secondary prose: TEXT blended 30% toward BACKGROUND (7.6:1 contrast). The
# terminal's dim attribute is never used; it is unreadable on real displays.
TEXT_DIM = "#aaaab1"

# --------------------------------------------------------------------------
# Semantic styles
# --------------------------------------------------------------------------

TITLE = f"bold {ACCENT}"
HEADING = f"bold {ACCENT}"
BODY = TEXT
STRONG = f"bold {TEXT}"
DETAIL = TEXT_DIM
FIGURE = ACCENT  # numbers, keys, identifiers
PATH = ACCENT  # a file the reader has to go and open
COMMAND = f"bold {TEXT}"  # something to type

PANEL = f"on {BACKGROUND}"
RAISED = f"on {SURFACE}"

# There is no error hue: an accented border marks the result.
BORDER = OUTLINE
BORDER_ACTIVE = ACCENT
BORDER_QUIET = MUTED

BAR = ACCENT
BAR_TRACK = MUTED

STATUS_TODO = DETAIL
STATUS_DONE = f"bold {ACCENT}"
# Counts as finished, so accented like `done`, but without the bold.
STATUS_SOLVED = ACCENT

CHECK_OK = ACCENT
CHECK_WARN = DETAIL
CHECK_FAIL = f"bold {ACCENT}"


# Rich's default markdown and table styles use named colors; override them all.
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
    "rule.line": ACCENT,
    "rule.text": f"bold {ACCENT}",
    "table.header": f"bold {ACCENT}",
    "table.footer": DETAIL,
    "table.title": f"bold {ACCENT}",
    "table.caption": DETAIL,
}


# Stock Pygments themes use colors outside the palette.
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
