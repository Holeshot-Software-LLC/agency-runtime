"""OpenClaw adapter — typed plugin hooks for OpenClaw runtime.

Uses api.on(...) typed hooks for policy/final-answer behavior.
File-based internal HOOK.md hooks are for side effects only.
"""

from __future__ import annotations

import logging
from typing import Any

from agency_runtime.adapters.base import BaseAdapter

logger = logging.getLogger("agency_runtime.adapters.openclaw")


class OpenClawAdapter(BaseAdapter):
    """OpenClaw/Nexus runtime adapter."""

    host_name = "openclaw"

    def is_available(self) -> bool:
        """Return canonical executable or native-state discovery for OpenClaw."""

        from agency_runtime.core.installer import detect_installed_agents

        return "openclaw" in detect_installed_agents()

    def get_delegate_backend(self) -> str | None:
        return "sessions_spawn"

    def on_message_received(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Typed plugin hook: message received, run preflight."""
        return self.build_preflight_context(session_id, user_message, model, trace_id)

    def on_response_finalizing(
        self,
        draft_text: str,
        session_id: str = "",
        model: str = "",
        *,
        trace_id: str = "",
    ) -> str:
        """Typed plugin hook: apply header finalization before response sent."""
        return self.apply_finalization(
            draft_text,
            session_id,
            model,
            trace_id=trace_id,
        )
