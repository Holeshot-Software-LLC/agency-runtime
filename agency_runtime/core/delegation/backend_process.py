"""Compatibility alias for the lightweight owned-process implementation."""

from __future__ import annotations

import sys

from agency_runtime.core import owned_process as _implementation

# Preserve the historical private monkeypatch surface.  Importers of this path
# receive the implementation module itself, so patches affect function globals
# exactly as they did before the module was split out of the delegation package.
sys.modules[__name__] = _implementation
