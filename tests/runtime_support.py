"""Shared test-runtime boundaries for host executable fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from agency_runtime.core.private_paths import ensure_private_directory


def trusted_test_interpreter() -> Path:
    """Return the CI-private interpreter or the local environment's base Python."""

    configured = os.environ.get("AGENCY_CI_PYTHON")
    return Path(configured or getattr(sys, "_base_executable", sys.executable)).resolve()


def ensure_private_test_directory(path: Path, *, parents: bool = False) -> Path:
    """Create an owner-private fixture directory independent of ambient umask."""

    if not parents:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    return ensure_private_directory(path)


def harden_private_test_file(path: Path) -> Path:
    """Make a fixture file satisfy the production owner-private file contract."""

    if os.name != "nt":
        path.chmod(0o600)
    return path
