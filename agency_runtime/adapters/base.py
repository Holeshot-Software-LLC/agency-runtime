"""Base adapter interface — all adapters implement this contract."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from agency_runtime.core.store.sqlite import Store


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _is_noneish_agency_line(value: str) -> bool:
    text = value.strip().lower().rstrip(".!")
    return text == "none" or text.startswith(("none ", "none-", "none--"))


def _is_non_actionable_delegation_none(value: str) -> bool:
    """Return True for a none-delegation line that lacks a real blocker."""
    text = value.strip().lower().rstrip(".!")
    if text == "none":
        return True
    return text in {
        "none - no delegation executed",
        "none - delegation suggested but not executed",
    }


def _json_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _delegation_failure_reason(result: Any) -> str:
    payload = _json_dict(result)
    if not payload:
        return ""
    nested = _json_dict(payload.get("result"))
    if nested and (nested.get("error") or nested.get("success") is False or nested.get("delegated") is False):
        return _clean(nested.get("message") or nested.get("error") or "delegate_task failed")
    if payload.get("error") or payload.get("success") is False or payload.get("delegated") is False:
        return _clean(payload.get("message") or payload.get("error") or "delegate_task failed")
    return ""


class BaseAdapter(ABC):

    """Base class for host/runtime adapters.

    Adapters are thin I/O shims. They translate between host events and
    the agency-runtime core. They should NOT reimplement routing,
    categorization, or delegation policy.
    """

    host_name: str = "unknown"

    def __init__(self, store: Store | None = None):
        self.store = store or Store()
        self._nontrivial_sessions: set[str] = set()

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this adapter's runtime is installed and available."""
        ...

    @abstractmethod
    def report_skills_loaded(self, session_id: str) -> list[str]:
        """Return skills loaded in the current host session."""
        ...

    @abstractmethod
    def report_specialists_loaded(self, session_id: str) -> list[str]:
        """Return specialists loaded in the current host session."""
        ...

    @abstractmethod
    def get_delegate_backend(self) -> str | None:
        """Return the delegate backend name this adapter provides, or None."""
        ...

    @abstractmethod
    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        """Return model telemetry from the host, if available."""
        ...

    def apply_finalization(self, draft_text: str, trace_id: str, model: str = "") -> str:
        """Apply header/finalization to the final visible reply."""
        from agency_runtime.core.header.contract import finalize_header
        return finalize_header(
            draft_text,
            session_id=trace_id,
            store=self.store,
            model=model,
        )

    def _suggested_delegations(self, session_id: str) -> list[dict[str, Any]]:
        from agency_runtime.core.delegation.events import suggested_delegations
        return suggested_delegations(self.store, session_id)

    def record_tool_call(self, **kwargs: Any) -> None:
        """Record skills, specialist loads, and actual delegation tool use."""
        from agency_runtime.core.delegation.events import (
            mark_delegation_executed,
            mark_delegation_skipped,
        )

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
            failure_reason = _delegation_failure_reason(kwargs.get("result"))
            if failure_reason:
                mark_delegation_skipped(
                    self.store,
                    session_id=session_id,
                    host=self.host_name,
                    agent=agent,
                    backend="agency_agents_delegate",
                    goal=_clean(args.get("task") or args.get("goal")),
                    reason=failure_reason,
                )
            else:
                mark_delegation_executed(
                    self.store,
                    session_id=session_id,
                    host=self.host_name,
                    agent=agent,
                    backend="agency_agents_delegate",
                    goal=_clean(args.get("task") or args.get("goal")),
                )

        elif tool_name in ("delegate_task", "delegate_async"):
            agent = args.get("agent") or args.get("slug") or args.get("recommended_agent") or ""
            if agent:
                self.store.record_specialist_loaded(session_id, agent)
            mark_delegation_executed(
                self.store,
                session_id=session_id,
                host=self.host_name,
                agent=agent,
                backend=tool_name,
                goal=_clean(args.get("goal") or args.get("task")),
            )

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        """Host hook alias for tool-call evidence capture."""
        self.record_tool_call(**kwargs)

    def post_api_request_handler(self, **kwargs: Any) -> None:
        """Record a model receipt when a host exposes response telemetry.

        Hosts with richer telemetry can override this method. The default keeps
        generated plugins safe for OpenClaw, Codex, Claude, and generic wrappers:
        absent model data records an honest unavailable receipt; present
        response["model"] is stored as the concrete model that actually ran.
        """
        import uuid

        from agency_runtime.core.receipts.normalize import normalize_host_receipt

        response = kwargs.get("response") if isinstance(kwargs.get("response"), dict) else {}
        requested_model = _clean(kwargs.get("model") or kwargs.get("requested_model"))
        session_id = _clean(kwargs.get("session_id"))
        resolved_model = _clean(
            kwargs.get("response_model")
            or kwargs.get("resolved_model")
            or response.get("model")
        )
        resolved_provider = _clean(kwargs.get("resolved_provider"))
        actual_model = resolved_model
        if "/" in resolved_model:
            detected_provider, detected_model = resolved_model.split("/", 1)
            actual_model = detected_model
            if not resolved_provider:
                resolved_provider = detected_provider

        receipt_metadata = {
            "host": self.host_name,
            "session_id": session_id,
            "requested_model": requested_model,
            "model_group": _clean(kwargs.get("model_group")) or requested_model,
            "resolved_provider": resolved_provider,
            "resolved_model": actual_model,
            "api_base": _clean(kwargs.get("api_base")),
            "attempted_fallbacks": kwargs.get("attempted_fallbacks", 0),
            "model_id": _clean(kwargs.get("model_id")),
            "source": _clean(kwargs.get("source")) or "host",
            "started_at": _clean(kwargs.get("started_at")),
            "ended_at": _clean(kwargs.get("ended_at")),
            "status": _clean(kwargs.get("status")) or "success",
        }
        if not resolved_model:
            receipt_metadata.update(
                {
                    "resolved_model": "unavailable",
                    "source": "unknown",
                    "status": _clean(kwargs.get("status")) or "unavailable",
                    "model_id": _clean(kwargs.get("model_id")) or "no host response model",
                }
            )

        receipt = normalize_host_receipt(receipt_metadata)
        self.store.record_model_receipt(
            trace_id=_clean(kwargs.get("trace_id")) or str(uuid.uuid4()),
            session_id=session_id,
            host=self.host_name,
            requested_model=requested_model,
            model_group=receipt.get("model_group", ""),
            resolved_provider=receipt.get("resolved_provider", ""),
            resolved_model=receipt.get("resolved_model", ""),
            api_base=receipt.get("api_base", ""),
            attempted_fallbacks=int(receipt.get("attempted_fallbacks", 0)),
            model_id=receipt.get("model_id", ""),
            source=receipt.get("source", "host"),
            started_at=receipt.get("started_at", ""),
            ended_at=receipt.get("ended_at", ""),
            status=receipt.get("status", "success"),
        )

    def _selected_catalog_agents(self, catalog: list[dict[str, Any]], routing: dict[str, Any]) -> list[dict[str, Any]]:
        """Return routed agents that exist in the active catalog, capped for context size."""
        selected_ids = [str(agent_id) for agent_id in routing.get("selected_ids", []) if agent_id]
        if not selected_ids:
            return []
        max_selected = 5
        by_slug = {str(agent.get("slug") or ""): agent for agent in catalog}
        selected: list[dict[str, Any]] = []
        for agent_id in selected_ids:
            agent = by_slug.get(agent_id)
            if agent and agent not in selected:
                selected.append(agent)
            if len(selected) >= max_selected:
                break
        return selected

    def _format_loaded_specialists(self, agents: list[dict[str, Any]]) -> str:
        """Render selected roster entries as injected specialist context."""
        lines = ["[AGENCY LOADED] Active roster specialist context loaded for this turn:"]
        for agent in agents:
            capabilities = agent.get("capabilities") if isinstance(agent.get("capabilities"), list) else []
            capability_text = f" Capabilities: {', '.join(str(item) for item in capabilities[:4])}." if capabilities else ""
            lines.append(
                "- "
                + str(agent.get("slug") or "")
                + ": "
                + str(agent.get("description") or agent.get("name") or "")
                + capability_text
            )
        return "\n".join(lines)

    def build_preflight_context(self, session_id: str, user_message: str, model: str = "") -> dict[str, Any] | None:
        """Run selector preflight and persist suggested delegations."""
        del model
        from agency_runtime.core.delegation.events import record_suggested_delegations
        from agency_runtime.core.selector.pipeline import build_routing_context, is_trivial, route
        from agency_runtime.core.selector.policy import detect_actions

        trivial = is_trivial(user_message)

        if not trivial:
            if session_id:
                self._nontrivial_sessions.add(session_id)
            catalog = self.store.get_active_roster_as_catalog()
            if not catalog:
                from agency_runtime.core.installer import seed_starter_roster

                seed_starter_roster(self.store)
                catalog = self.store.get_active_roster_as_catalog()
            routing = route(session_id, user_message, catalog)
            record_suggested_delegations(self.store, session_id=session_id, host=self.host_name, routing=routing)
            context = build_routing_context(routing)
            selected = self._selected_catalog_agents(catalog, routing)
            if selected:
                for agent in selected:
                    self.store.record_specialist_loaded(session_id, str(agent.get("slug") or ""))
                context = context + "\n\n" + self._format_loaded_specialists(selected)
            return {"context": context} if context else None

        # Trivial message: still inject DEFAULT companions so the header
        # never shows "loaded: none" when DEFAULT policy says otherwise.
        _matched, companion_ids = detect_actions(user_message)
        default_companions = [c for c in companion_ids if c]
        if default_companions:
            catalog = self.store.get_active_roster_as_catalog()
            active_slugs = {str(agent.get("slug") or agent.get("agent_slug") or "") for agent in catalog}
            available = [slug for slug in default_companions if slug in active_slugs]
            if available:
                for slug in available:
                    self.store.record_specialist_loaded(session_id, slug)
                agents_text = ", ".join(available)
                context = (
                    f"[AGENCY PREFLIGHT] Default companion specialist routing "
                    f"(deterministic, trivial message): {agents_text}"
                )
                return {"context": context}

        return None

    def pre_llm_call_handler(self, session_id: str, user_message: str, model: str = "") -> dict[str, Any] | None:
        """Host hook alias for pre-LLM routing context."""
        return self.build_preflight_context(session_id, user_message, model)

    def enforce_pre_verify(self, final_response: str, session_id: str = "", model: str = "", attempt: int = 0) -> dict[str, Any] | None:
        """Gate response completion on header, specialist, and delegation evidence."""
        del model
        if attempt >= 2:
            return None

        from agency_runtime.core.header.contract import parse_header, validate_header
        valid, missing = validate_header(final_response)
        if not valid:
            return {
                "action": "continue",
                "message": (
                    "Your response is missing or has malformed Agency header fields: "
                    + ", ".join(missing)
                    + ". Rewrite the response starting with the exact six-line Agency header."
                ),
            }

        parsed = parse_header(final_response)
        loaded = parsed.get("agencies_loaded", "")
        delegated = parsed.get("agencies_delegated", "")

        specialists = self.report_specialists_loaded(session_id)
        open_delegations = self._suggested_delegations(session_id)
        requires_agency_evidence = bool(session_id and (session_id in self._nontrivial_sessions or specialists)) or bool(open_delegations)
        if requires_agency_evidence and _is_noneish_agency_line(loaded) and attempt < 2:
            actual = ", ".join(specialists) if specialists else "the actual loaded specialist"
            return {
                "action": "continue",
                "message": (
                    "AGENCY HEADER INVALID: This was a non-trivial turn but "
                    "Agency/Agencies loaded starts with 'none'. "
                    f"Rewrite the header with {actual}. If no specialist context is loaded, "
                    "call agency_agents_search and agency_agents_load first."
                ),
            }

        # `none - <concrete blocker>` is acceptable; generated/no-evidence
        # explanations still need a real delegation or a concrete blocker.
        if open_delegations and _is_non_actionable_delegation_none(delegated) and attempt < 2:
            return {
                "action": "continue",
                "message": (
                    "DELEGATION OPPORTUNITY WAS DETECTED but agencies_delegated has no executed delegation or concrete blocker. "
                    "Dispatch at least one independent work unit via delegate_task, delegate_async, "
                    "or agency_agents_delegate, then report the executed delegation in the Agency header. "
                    "If delegation is impossible, state the concrete blocker instead of writing bare 'none'."
                ),
            }

        return None

    def pre_verify_handler(self, final_response: str, session_id: str = "", model: str = "", attempt: int = 0) -> dict[str, Any] | None:
        """Host hook alias for final-response verification."""
        return self.enforce_pre_verify(final_response, session_id, model, attempt)
