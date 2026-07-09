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
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.hermes")


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


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

    def post_api_request_handler(self, **kwargs: Any) -> None:
        """Capture model receipt from the actual API response.

        Hermes provides kwargs:
        - response: dict with 'model', 'usage', etc.
        - model: the requested model alias (e.g. task-chunk-planner)
        - session_id: session identifier
        - started_at / ended_at: timestamps
        - response_model: the model field from the response (sometimes separate)

        The response itself carries the truth — the 'model' field in the
        response body is the resolved deployment (e.g.
        'chatgpt/gpt-5.5-pro-extended'), not the requested alias.
        LiteLLM response headers (x-litellm-model-id, x-litellm-model-group,
        x-litellm-model-api-base, x-litellm-attempted-fallbacks) provide
        additional routing truth when available.

        We never query SpendLogs — the response is the source of truth.
        """
        import uuid

        from agency_runtime.core.receipts.normalize import normalize_host_receipt

        response = kwargs.get("response") if isinstance(kwargs.get("response"), dict) else {}
        requested_model = _clean(kwargs.get("model") or "")
        session_id = _clean(kwargs.get("session_id")) or ""

        # The resolved model is in the response body — this is the dynamic
        # model that LiteLLM's complexity router or fallback chain selected.
        resolved_model = _clean(
            kwargs.get("response_model")
            or response.get("model")
            or ""
        )

        if not resolved_model:
            return

        # Split provider/model from resolved (e.g. "openai/glm-5.2")
        resolved_provider = ""
        actual_model = resolved_model
        if "/" in resolved_model:
            parts = resolved_model.split("/", 1)
            resolved_provider = parts[0]
            actual_model = parts[1]

        receipt = normalize_host_receipt({
            "host": self.host_name,
            "session_id": session_id,
            "requested_model": requested_model,
            "model_group": requested_model,  # The alias is the group
            "resolved_model": actual_model,
            "resolved_provider": resolved_provider,
            "source": "host",
            "started_at": _clean(kwargs.get("started_at")),
            "ended_at": _clean(kwargs.get("ended_at")),
            "status": "success",
        })

        self.store.record_model_receipt(
            trace_id=str(uuid.uuid4()),
            session_id=session_id,
            host=self.host_name,
            requested_model=requested_model,
            model_group=receipt.get("model_group", ""),
            resolved_provider=receipt.get("resolved_provider", ""),
            resolved_model=receipt.get("resolved_model", ""),
            api_base=receipt.get("api_base", ""),
            attempted_fallbacks=int(receipt.get("attempted_fallbacks", 0)),
            model_id=receipt.get("model_id", ""),
            source="host",
            started_at=receipt.get("started_at", ""),
            ended_at=receipt.get("ended_at", ""),
            status="success",
        )

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        """Record skills and specialists loaded via tool calls.

        Hermes exposes these tool names:
        - skill_view → skill loaded
        - agency_agents_load → specialist loaded into context
        - agency_agents_delegate → specialist delegated (worker spawned)
        - agency_agents_inspect → specialist loaded into context
        """
        tool_name = kwargs.get("tool_name") or ""
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        session_id = _clean(kwargs.get("session_id"))

        if tool_name == "skill_view":
            skill_name = args.get("name") or ""
            if skill_name:
                self.store.record_skill_loaded(session_id, skill_name)

        elif tool_name in ("agency_agents_load", "agency_agents_inspect"):
            agent = args.get("agent") or args.get("slug") or ""
            if agent:
                self.store.record_specialist_loaded(session_id, agent)

        elif tool_name == "agency_agents_delegate":
            agent = args.get("agent") or args.get("slug") or ""
            if agent:
                self.store.record_specialist_loaded(session_id, agent)

        elif tool_name == "delegate_task":
            # delegate_task has different arg structure
            goal = args.get("goal") or ""
            # Extract agent from the goal context if available
            agent = args.get("agent") or ""
            if agent:
                self.store.record_specialist_loaded(session_id, agent)

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
