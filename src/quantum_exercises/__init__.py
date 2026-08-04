"""qx: a command line course in quantum computing with Qiskit."""

from __future__ import annotations

import shutil
from functools import lru_cache

__version__ = "0.3.4"


@lru_cache(maxsize=1)
def invocation() -> str:
    """How to spell the command in guidance the tool prints.

    `qx` once it is installed globally, `uv run qx` otherwise. The quickstart
    installs it, so every written file says plainly `qx`; this exists for the
    reader who skipped that step, so the guidance still matches what they can
    type. Printing one form unconditionally would contradict one of them.

    Lives here rather than in ui so that registry and runner can use it too,
    since ui imports both of them.
    """
    return "qx" if shutil.which("qx") else "uv run qx"


__all__ = ["__version__", "invocation"]
