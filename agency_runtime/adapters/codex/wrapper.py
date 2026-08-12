"""Codex adapter — observes a host Agency never drives.

Agency reaches Codex through its native hooks and MCP. It does not run
`codex exec` itself: rule 5 says the host alone decides whether to spawn.
"""

from __future__ import annotations

import logging
import shutil

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.codex")


class CodexAdapter(BaseAdapter):
    """Codex CLI wrapper adapter."""

    host_name = "codex"

    def __init__(self, store: Store | None = None, codex_cmd: str = "codex"):
        super().__init__(store)
        self.codex_cmd = codex_cmd

    def is_available(self) -> bool:
        """Check if codex CLI is installed."""
        return bool(shutil.which(self.codex_cmd))
