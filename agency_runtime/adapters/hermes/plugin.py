"""Hermes adapter — plugin for Hermes Agent runtime.

When Hermes is the host, this adapter:
- imports core selector;
- provides fallback when LiteLLM is down;
- reports actual skills loaded via Hermes skill loader events;
- uses delegate_task, delegate_async, and Agency tools where available;
- integrates with pre_verify or equivalent final response gate;
- records delegation events and exact failures.
"""

from __future__ import annotations

import logging
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.hermes")


class HermesAdapter(BaseAdapter):
    """Hermes Agent runtime adapter."""

    host_name = "hermes"

    def is_available(self) -> bool:
        """Check if Hermes is the current host."""
        import sys
        return any("hermes" in module for module in sys.modules)

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
        return "delegate_task"

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    def pre_llm_call_handler(self, session_id: str, user_message: str, model: str = "") -> dict[str, Any] | None:
        """Pre-LLM call handler for Hermes plugin system."""
        from agency_runtime.adapters.litellm.callback import litellm_health_check
        from agency_runtime.core.selector.pipeline import is_trivial, route_and_build_context

        if litellm_health_check():
            return None  # LiteLLM callback handles it

        if is_trivial(user_message):
            return None

        catalog = self.store.get_active_roster_as_catalog()
        context = route_and_build_context(session_id, user_message, catalog)
        return {"context": context} if context else None

    def pre_verify_handler(self, final_response: str, session_id: str = "", model: str = "", attempt: int = 0) -> dict[str, Any] | None:
        """Pre-verify handler — gate response completion on agency header."""
        import re

        if attempt >= 2:
            return None

        from agency_runtime.core.header.contract import validate_header
        valid, missing = validate_header(final_response)
        if valid:
            return None

        skills = ", ".join(self.report_skills_loaded(session_id)) or "none"
        return {
            "action": "continue",
            "message": (
                "AGENCY HEADER REQUIRED: Your response must begin with this complete "
                "Agency observability header before any other content:\n\n"
                "Agency/Agencies loaded: <agent-id> (or 'none')\n"
                "Agency/Agencies delegated: <agent-id> (or 'none')\n"
                f"Skills loaded: {skills}\n"
                "Actual Model selected: <model>\n"
                "Why: <one line>\n"
                "How it shaped outcome: <one line>\n"
            ),
        }
