"""qx: a command line course in quantum computing with Qiskit."""

from __future__ import annotations

import shutil
from functools import lru_cache

__version__ = "0.3.3"


@lru_cache(maxsize=1)
def invocation() -> str:
    """How to spell the command in guidance the tool prints.

    `qx` once it is installed globally, `uv run qx` otherwise. Printing one form
    unconditionally contradicts whichever the reader is actually using: the
    exercise files say `uv run qx run N`, which works straight from a fresh clone
    with nothing installed, while a global install makes the bare `qx` natural.

    Lives here rather than in ui so that registry and runner can use it too,
    since ui imports both of them.
    """
    return "qx" if shutil.which("qx") else "uv run qx"


__all__ = ["__version__", "invocation"]
