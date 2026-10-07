"""qx: a command line course in quantum computing with Qiskit."""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache

__version__ = "1.0.0"


@lru_cache(maxsize=1)
def invocation() -> str:
    """`qx` when a global install is on PATH, otherwise `uv run qx`."""
    # Skip any qx inside this environment: `uv run` or an active venv puts it on
    # PATH only for now. Symlinks are not resolved on purpose, because
    # `uv tool install` links ~/.local/bin/qx back into its own environment.
    prefix = os.path.normcase(os.path.abspath(sys.prefix)) + os.sep
    for directory in os.get_exec_path():
        candidate = shutil.which("qx", path=directory)
        if candidate and not os.path.normcase(os.path.abspath(candidate)).startswith(prefix):
            return "qx"
    return "uv run qx"


__all__ = ["__version__", "invocation"]
