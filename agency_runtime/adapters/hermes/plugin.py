"""Hermes adapter — plugin for Hermes Agent runtime.

When Hermes is the host, this adapter:
- imports core selector;
- provides fallback when LiteLLM is down;
- reports actual skills loaded via Hermes skill loader events;
- uses delegate_task, delegate_async, and Agency tools where available;
- integrates with pre_verify or equivalent final response gate;
- records delegation events and exact failures;
- captures model receipts from response data (not SpendLogs).
"""

from __future__ import annotations

import logging
from typing import Any

from agency_runtime.adapters.base import BaseAdapter

logger = logging.getLogger("agency_runtime.adapters.hermes")


class HermesAdapter(BaseAdapter):
    """Hermes Agent runtime adapter."""

    host_name = "hermes"

    def is_available(self) -> bool:
        """Return canonical executable or native-state discovery for Hermes."""

        from agency_runtime.core.installer import detect_installed_agents

        return "hermes" in detect_installed_agents()

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return self.store.get_specialists_for_session(session_id)

    def get_delegate_backend(self) -> str | None:
        return "delegate_task"

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        return {}

    # BaseAdapter.post_api_request_handler records the canonical host receipt
    # for all host adapters, including honest unavailable receipts when the
    # hook lacks model telemetry.

    def _suggested_delegations(self, session_id: str) -> list[dict[str, Any]]:
        from agency_runtime.core.delegation.events import suggested_delegations

        return suggested_delegations(self.store, session_id)

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        """Record skills, specialist loads, and actual delegation tool use."""
        self.record_tool_call(**kwargs)

    def pre_llm_call_handler(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Pre-LLM call handler for Hermes plugin system.

        ALWAYS runs routing and injects specialist suggestions, even when
        LiteLLM is healthy. The LiteLLM callback handles request-level
        routing (model selection), but the agent still needs specialist-
        loading context to know which agents to call.

        This is the critical path: without this injection, the agent never
        sees [AGENCY PREFLIGHT] suggestions and writes 'loaded: none' on
        every turn — making the entire plugin broken from the start.
        """
        return self.build_preflight_context(session_id, user_message, model, trace_id)

    def pre_verify_handler(
        self,
        final_response: str,
        session_id: str = "",
        model: str = "",
        attempt: int = 0,
    ) -> dict[str, Any] | None:
        """Pre-verify handler — gate response completion on agency header.

        Two checks:
        1. Header exists and is complete (all six fields present)
        2. On non-trivial turns, at least one specialist was consulted
           (agencies_loaded must not be 'none' unless the turn was trivial)
        """
        return self.enforce_pre_verify(final_response, session_id, model, attempt)
