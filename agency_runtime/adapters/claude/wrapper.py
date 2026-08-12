"""Claude Code adapter — observes a host Agency never drives.

Agency reaches Claude through its native hooks and MCP. It does not run
`claude -p` itself: rule 5 says the host alone decides whether to spawn.
"""

from __future__ import annotations

import logging
import shutil

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.claude")


class ClaudeAdapter(BaseAdapter):
    """Claude Code CLI wrapper adapter (optional)."""

    host_name = "claude"

    def __init__(self, store: Store | None = None, claude_cmd: str = "claude"):
        super().__init__(store)
        self.claude_cmd = claude_cmd

    def is_available(self) -> bool:
        """Check if Claude Code CLI is installed."""
        return bool(shutil.which(self.claude_cmd))
