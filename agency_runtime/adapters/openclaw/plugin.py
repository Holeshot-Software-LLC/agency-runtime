"""OpenClaw adapter — typed plugin hooks for OpenClaw runtime.

Uses api.on(...) typed hooks for policy/final-answer behavior.
File-based internal HOOK.md hooks are for side effects only.
"""

from __future__ import annotations

import logging
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.openclaw")


class OpenClawAdapter(BaseAdapter):
    """OpenClaw/Nexus runtime adapter."""

    host_name = "openclaw"

    def is_available(self) -> bool:
        """Check if OpenClaw is running."""
        import os
        return os.path.exists(os.path.expanduser("~/.openclaw"))

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        conn = self.store._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegate_backend(self) -> str | None:
        return "sessions_spawn"

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    def on_message_received(self, session_id: str, user_message: str, model: str = "") -> dict[str, Any] | None:
        """Typed plugin hook: message received, run preflight."""
        from agency_runtime.core.selector.pipeline import is_trivial, route_and_build_context

        if is_trivial(user_message):
            return None

        catalog = self.store.get_active_roster_as_catalog()
        context = route_and_build_context(session_id, user_message, catalog)
        return {"context": context} if context else None

    def on_response_finalizing(self, draft_text: str, session_id: str = "", model: str = "") -> str:
        """Typed plugin hook: apply header finalization before response sent."""
        return self.apply_finalization(draft_text, session_id, model)
