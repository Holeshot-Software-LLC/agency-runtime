"""Base adapter interface — all adapters implement this contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
from hashlib import sha256
from threading import RLock
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.store.sqlite import Store

_MAX_EMBEDDED_RESULT_BYTES = 256 * 1024
_MAX_NONTRIVIAL_SESSIONS = 4096


def _session_evidence_key(session_id: str) -> bytes:
    """Return a fixed-width digest key so raw session IDs are not retained."""
    return sha256(session_id.encode("utf-8", errors="surrogatepass")).digest()


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


_FAILURE_STATUSES = {
    "cancelled",
    "canceled",
    "error",
    "failed",
    "failure",
    "rejected",
    "skipped",
    "timed_out",
    "timeout",
}
_FALSE_FAILURE_KEYS = ("success", "ok", "delegated", "loaded")
_TRUE_FAILURE_KEYS = (
    "isError",
    "is_error",
    "cancelled",
    "canceled",
    "timed_out",
)
_EXIT_CODE_KEYS = ("returncode", "return_code", "exit_code", "exitCode")
_NESTED_RESULT_KEYS = ("result", "output", "data", "content", "text")


def _failure_message(payload: dict[str, Any], default: str = "tool call failed") -> str:
    for key in ("message", "error", "reason", "detail", "stderr"):
        value = payload.get(key)
        if value not in (None, "", False):
            if isinstance(value, dict):
                return _failure_message(value, default)
            return _clean(value, default)
    content = payload.get("content")
    if isinstance(content, (list, tuple)):
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                return _clean(item["text"], default)
    return default


def _sequence_failure_reason(result: list[Any] | tuple[Any, ...], depth: int) -> str:
    for item in result:
        reason = _tool_failure_reason(item, _depth=depth + 1)
        if reason:
            return reason
    return ""


def _text_failure_reason(result: str, depth: int) -> str:
    text = result.strip()
    if not text:
        return ""
    try:
        parsed = safe_load_bounded_json(
            text,
            maximum_bytes=_MAX_EMBEDDED_RESULT_BYTES,
            maximum_depth=32,
            maximum_nodes=5_000,
        )
    except Exception:
        if text.startswith(("{", "[")):
            return "tool call returned invalid structured output"
    else:
        # Successful JSON parsing necessarily changes the source representation:
        # containers and scalars become Python values, while JSON strings lose
        # their required quoting. Recurse directly instead of retaining an
        # unreachable parsed-equals-source branch.
        return _tool_failure_reason(parsed, _depth=depth + 1)
    if text.lower().startswith(("error:", "failed:", "failure:", "exception:", "tool error:")):
        return text
    return ""


def _direct_mapping_failure(payload: dict[str, Any]) -> str:
    if payload.get("error") not in (None, "", False):
        return _failure_message(payload)
    if any(payload.get(key) is False for key in _FALSE_FAILURE_KEYS):
        return _failure_message(payload)
    if any(payload.get(key) is True for key in _TRUE_FAILURE_KEYS):
        return _failure_message(payload)
    if _clean(payload.get("status")).lower() in _FAILURE_STATUSES:
        return _failure_message(payload)
    for key in _EXIT_CODE_KEYS:
        value = payload.get(key)
        if value not in (None, "", 0, "0"):
            return _failure_message(payload, f"tool call exited with {value}")
    return ""


def _mapping_failure_reason(payload: dict[str, Any], depth: int) -> str:
    direct = _direct_mapping_failure(payload)
    if direct:
        return direct
    for key in _NESTED_RESULT_KEYS:
        if key not in payload:
            continue
        reason = _tool_failure_reason(payload.get(key), _depth=depth + 1)
        if reason:
            return reason
    return ""


def _tool_failure_reason(result: Any, *, _depth: int = 0) -> str:
    """Return an explicit tool failure reason without guessing from prose.

    Host hooks expose several result envelopes.  Failure flags are checked at
    every structured nesting level, including JSON strings and MCP-style
    ``content`` lists.  Missing results remain backward-compatible: absence of
    telemetry is not treated as proof of failure.
    """
    if _depth > 6 or result is None or result is True:
        return ""
    if result is False:
        return "tool call returned false"
    if isinstance(result, (list, tuple)):
        return _sequence_failure_reason(result, _depth)
    if isinstance(result, str):
        return _text_failure_reason(result, _depth)
    return _mapping_failure_reason(result, _depth) if isinstance(result, dict) else ""


def _tool_result(kwargs: dict[str, Any]) -> Any:
    for key in ("result", "tool_result", "output", "response"):
        if key in kwargs and kwargs.get(key) is not None:
            return kwargs.get(key)
    return None


def _tool_call_failure_reason(kwargs: dict[str, Any]) -> str:
    for key in ("result", "tool_result", "output", "response"):
        if key in kwargs:
            reason = _tool_failure_reason(kwargs.get(key))
            if reason:
                return reason
    envelope = {
        key: kwargs[key]
        for key in (
            "error",
            "success",
            "ok",
            "delegated",
            "loaded",
            "isError",
            "is_error",
            "status",
            "returncode",
            "return_code",
            "exit_code",
            "exitCode",
            "message",
            "reason",
            "detail",
            "stderr",
        )
        if key in kwargs
    }
    return _tool_failure_reason(envelope) if envelope else ""


def _nested_value(value: Any, keys: tuple[str, ...], *, _depth: int = 0) -> Any:
    if _depth > 5:
        return None
    if isinstance(value, str):
        try:
            value = safe_load_bounded_json(
                value,
                maximum_bytes=_MAX_EMBEDDED_RESULT_BYTES,
                maximum_depth=32,
                maximum_nodes=5_000,
            )
        except Exception:
            return None
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for key in ("result", "output", "data"):
            found = _nested_value(value.get(key), keys, _depth=_depth + 1)
            if found not in (None, ""):
                return found
    return None


def _first_value(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
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
        self._nontrivial_sessions: OrderedDict[bytes, None] = OrderedDict()
        self._nontrivial_sessions_lock = RLock()

    def _remember_nontrivial_session(self, session_id: str) -> None:
        """Retain bounded, thread-safe evidence that a session required routing."""
        if not session_id:
            return
        evidence_key = _session_evidence_key(session_id)
        with self._nontrivial_sessions_lock:
            self._nontrivial_sessions[evidence_key] = None
            self._nontrivial_sessions.move_to_end(evidence_key)
            while len(self._nontrivial_sessions) > _MAX_NONTRIVIAL_SESSIONS:
                self._nontrivial_sessions.popitem(last=False)

    def _was_nontrivial_session(self, session_id: str) -> bool:
        """Return recent routing evidence without racing concurrent host callbacks."""
        if not session_id:
            return False
        evidence_key = _session_evidence_key(session_id)
        with self._nontrivial_sessions_lock:
            if evidence_key not in self._nontrivial_sessions:
                return False
            self._nontrivial_sessions.move_to_end(evidence_key)
            return True

    def runtime_enabled(self) -> bool:
        """Return the current persistent soft-control state for this host."""
        return bool(self.store.get_host_control(self.host_name).get("enabled", True))

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
        if not self.runtime_enabled():
            return draft_text
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
        if not self.runtime_enabled():
            return
        from agency_runtime.core.delegation.events import (
            mark_delegation_executed,
            mark_delegation_skipped,
        )

        tool_name = kwargs.get("tool_name") or ""
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        session_id = _clean(kwargs.get("session_id"))
        trace_id = _clean(kwargs.get("trace_id"))
        result = _tool_result(kwargs)
        failure_reason = _tool_call_failure_reason(kwargs)

        if tool_name == "skill_view":
            skill_name = args.get("name") or ""
            if skill_name and not failure_reason:
                self.store.record_skill_loaded(session_id, skill_name)

        elif tool_name in ("agency_agents_load", "agency_agents_inspect"):
            agent = args.get("agent") or args.get("slug") or ""
            if agent and not failure_reason:
                self.store.record_specialist_loaded(session_id, agent)

        elif tool_name in ("agency_agents_delegate", "delegate_task", "delegate_async"):
            agent = _clean(
                _first_value(
                    args.get("agent"),
                    args.get("slug"),
                    args.get("recommended_agent"),
                    kwargs.get("agent"),
                    kwargs.get("recommended_agent"),
                    _nested_value(result, ("agent", "slug", "recommended_agent")),
                )
            )
            goal = _clean(
                _first_value(
                    args.get("goal"),
                    args.get("task"),
                    args.get("prompt"),
                    args.get("description"),
                    kwargs.get("goal"),
                    kwargs.get("task"),
                    _nested_value(result, ("goal", "task", "prompt", "description")),
                )
            )
            work_unit_id = _clean(
                _first_value(
                    args.get("work_unit_id"),
                    args.get("workUnitId"),
                    args.get("unit_id"),
                    args.get("task_id"),
                    kwargs.get("work_unit_id"),
                    kwargs.get("workUnitId"),
                    _nested_value(result, ("work_unit_id", "workUnitId", "unit_id", "task_id")),
                )
            )
            backend = (
                "agency_agents_delegate" if tool_name == "agency_agents_delegate" else tool_name
            )
            if failure_reason:
                mark_delegation_skipped(
                    self.store,
                    session_id=session_id,
                    host=self.host_name,
                    agent=agent,
                    backend=backend,
                    goal=goal,
                    work_unit_id=work_unit_id,
                    trace_id=trace_id,
                    reason=failure_reason,
                )
            else:
                if agent:
                    self.store.record_specialist_loaded(session_id, agent)
                mark_delegation_executed(
                    self.store,
                    session_id=session_id,
                    host=self.host_name,
                    agent=agent,
                    backend=backend,
                    goal=goal,
                    work_unit_id=work_unit_id,
                    trace_id=trace_id,
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
        if not self.runtime_enabled():
            return

        import uuid

        from agency_runtime.core.receipts.normalize import normalize_host_receipt

        response = kwargs.get("response") if isinstance(kwargs.get("response"), dict) else {}
        requested_model = _clean(kwargs.get("model") or kwargs.get("requested_model"))
        session_id = _clean(kwargs.get("session_id"))
        resolved_model = _clean(
            kwargs.get("response_model") or kwargs.get("resolved_model") or response.get("model")
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

    def _selected_catalog_agents(
        self, catalog: list[dict[str, Any]], routing: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Return routed active specialists with versioned, bounded prompts."""
        selected_ids = [str(agent_id) for agent_id in routing.get("selected_ids", []) if agent_id]
        if not selected_ids:
            return []
        max_selected = 5
        active_slugs = {str(agent.get("slug") or "") for agent in catalog}
        selected: list[dict[str, Any]] = []
        for agent_id in selected_ids:
            if agent_id not in active_slugs:
                continue
            agent = self.store.get_specialist_prompt(agent_id, max_chars=12_000)
            if agent and agent.get("prompt_body") and agent not in selected:
                selected.append(agent)
            if len(selected) >= max_selected:
                break
        return selected

    def _format_loaded_specialists(self, agents: list[dict[str, Any]]) -> str:
        """Render approved versioned specialist prompts as injected context."""
        lines = ["[AGENCY LOADED] Approved specialist instructions loaded for this turn:"]
        for agent in agents:
            capabilities = (
                agent.get("capabilities") if isinstance(agent.get("capabilities"), list) else []
            )
            capability_text = (
                f" Capabilities: {', '.join(str(item) for item in capabilities[:4])}."
                if capabilities
                else ""
            )
            lines.append(
                "- "
                + str(agent.get("agent_slug") or agent.get("slug") or "")
                + ": "
                + str(agent.get("description") or agent.get("name") or "")
                + capability_text
            )
            lines.append("  Instructions: " + str(agent.get("prompt_body") or ""))
        return "\n".join(lines)

    def build_preflight_context(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Run selector preflight and persist suggested delegations."""
        if not self.runtime_enabled():
            return None
        del model
        from agency_runtime.core.delegation.events import record_suggested_delegations
        from agency_runtime.core.selector.pipeline import (
            build_routing_context,
            is_trivial,
            route,
        )
        from agency_runtime.core.selector.policy import detect_actions

        trivial = is_trivial(user_message)

        if not trivial:
            if session_id:
                self._remember_nontrivial_session(session_id)
            catalog = self.store.get_active_roster_as_catalog()
            if not catalog:
                from agency_runtime.core.installer import seed_starter_roster

                seed_starter_roster(self.store)
                catalog = self.store.get_active_roster_as_catalog()
            routing = route(
                session_id,
                user_message,
                catalog,
                store=self.store,
                trace_id=trace_id or None,
            )
            record_suggested_delegations(
                self.store, session_id=session_id, host=self.host_name, routing=routing
            )
            context = build_routing_context(routing)
            selected = self._selected_catalog_agents(catalog, routing)
            if selected:
                for agent in selected:
                    self.store.record_specialist_loaded(
                        session_id,
                        str(agent.get("agent_slug") or agent.get("slug") or ""),
                    )
                context = context + "\n\n" + self._format_loaded_specialists(selected)
            return {"context": context} if context else None

        # Trivial message: still inject DEFAULT companions so the header
        # never shows "loaded: none" when DEFAULT policy says otherwise.
        catalog = self.store.get_active_roster_as_catalog()
        active_slugs = {
            str(agent.get("slug") or agent.get("agent_slug") or "") for agent in catalog
        }
        _matched, companion_ids = detect_actions(
            user_message,
            active_slugs=active_slugs,
        )
        default_companions = [c for c in companion_ids if c]
        if default_companions:
            available = [slug for slug in default_companions if slug in active_slugs]
            if available:
                loaded_agents = [
                    prompt
                    for slug in available
                    if (prompt := self.store.get_specialist_prompt(slug, max_chars=12_000))
                    and prompt.get("prompt_body")
                ]
                loaded_slugs = [str(agent.get("agent_slug") or "") for agent in loaded_agents]
                for slug in loaded_slugs:
                    self.store.record_specialist_loaded(session_id, slug)
                if not loaded_agents:
                    return None
                agents_text = ", ".join(loaded_slugs)
                context = (
                    f"[AGENCY PREFLIGHT] Default companion specialist routing "
                    f"(deterministic, trivial message): {agents_text}\n\n"
                    + self._format_loaded_specialists(loaded_agents)
                )
                return {"context": context}

        return None

    def pre_llm_call_handler(
        self,
        session_id: str,
        user_message: str,
        model: str = "",
        trace_id: str = "",
    ) -> dict[str, Any] | None:
        """Host hook alias for pre-LLM routing context."""
        return self.build_preflight_context(
            session_id,
            user_message,
            model,
            trace_id,
        )

    def enforce_pre_verify(
        self,
        final_response: str,
        session_id: str = "",
        model: str = "",
        attempt: int = 0,
    ) -> dict[str, Any] | None:
        """Gate response completion on header, specialist, and delegation evidence."""
        if not self.runtime_enabled():
            return None
        del attempt

        from agency_runtime.core.header.contract import (
            fill_header_fields,
            parse_header,
            validate_header,
        )

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
        requires_agency_evidence = bool(
            session_id and (self._was_nontrivial_session(session_id) or specialists)
        ) or bool(open_delegations)
        if requires_agency_evidence and _is_noneish_agency_line(loaded):
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
        if open_delegations and _is_non_actionable_delegation_none(delegated):
            return {
                "action": "continue",
                "message": (
                    "DELEGATION OPPORTUNITY WAS DETECTED but agencies_delegated has no executed delegation or concrete blocker. "
                    "Dispatch at least one independent work unit via delegate_task, delegate_async, "
                    "or agency_agents_delegate, then report the executed delegation in the Agency header. "
                    "If delegation is impossible, state the concrete blocker instead of writing bare 'none'."
                ),
            }

        authoritative = fill_header_fields(parsed, session_id, self.store, model)
        evidence_fields = (
            ("agencies_loaded", "Agency/Agencies loaded"),
            ("agencies_delegated", "Agency/Agencies delegated"),
            ("skills_loaded", "Skills loaded"),
            ("actual_model_selected", "Actual Model selected"),
        )
        mismatches = [
            (label, authoritative[key])
            for key, label in evidence_fields
            if _clean(parsed.get(key)) != _clean(authoritative[key])
        ]
        if mismatches:
            corrections = "; ".join(f"{label}: {value}" for label, value in mismatches)
            return {
                "action": "continue",
                "message": (
                    "AGENCY HEADER DOES NOT MATCH RECORDED EVIDENCE. "
                    "Do not claim unrecorded specialist, delegation, or model activity. "
                    f"Rewrite these fields exactly: {corrections}"
                ),
            }

        return None

    def pre_verify_handler(
        self,
        final_response: str,
        session_id: str = "",
        model: str = "",
        attempt: int = 0,
    ) -> dict[str, Any] | None:
        """Host hook alias for final-response verification."""
        return self.enforce_pre_verify(final_response, session_id, model, attempt)
