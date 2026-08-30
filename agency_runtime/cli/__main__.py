"""Module entry point for ``python -m agency_runtime.cli``."""

from __future__ import annotations

from agency_runtime.cli.entrypoint import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
