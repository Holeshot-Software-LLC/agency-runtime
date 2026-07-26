"""Lightweight installed-console entry point.

The full compatibility facade intentionally imports every command module so
downstream callers can patch historical names.  The installed executable does
not need that graph to answer the process-health ``--version`` probe used by
installers and hooks.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from agency_runtime import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the version probe without importing the complete CLI graph."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        print(f"agency {__version__}")
        return 0

    from agency_runtime.cli.main import main as full_main

    return full_main(arguments)


__all__ = ["main"]
