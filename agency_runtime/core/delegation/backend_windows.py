"""Compatibility alias for the lightweight Windows containment module."""

from __future__ import annotations

import sys

from agency_runtime.core import owned_process_windows as _implementation

sys.modules[__name__] = _implementation
