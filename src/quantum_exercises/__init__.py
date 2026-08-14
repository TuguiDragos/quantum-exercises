"""qx: a command line course in quantum computing with Qiskit."""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache

__version__ = "0.8.5"


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
    # A qx inside this interpreter's own environment is the one `uv run` or an
    # activated venv puts on PATH for the moment. It is not there in the reader's
    # next shell, so answering "qx" on the strength of it would be exactly the
    # mistake this helper exists to prevent.
    #
    # So look past it: search every PATH entry and keep the first qx that is not
    # inside this environment. Finding one means a global install really is there
    # and `qx` is what the reader should type, whether or not a venv happens to be
    # active right now. Compared without resolving symlinks on purpose, because
    # `uv tool install` leaves a link in ~/.local/bin pointing back into the
    # tool's own environment, and that link is a real, permanent entry on PATH.
    prefix = os.path.normcase(os.path.abspath(sys.prefix)) + os.sep
    for directory in os.get_exec_path():
        candidate = shutil.which("qx", path=directory)
        if candidate and not os.path.normcase(os.path.abspath(candidate)).startswith(prefix):
            return "qx"
    return "uv run qx"


__all__ = ["__version__", "invocation"]
