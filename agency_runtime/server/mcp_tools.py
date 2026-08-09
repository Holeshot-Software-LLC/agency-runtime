"""Lazy Agency MCP tool implementations behind the public MCP facade."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.resident_managers import resident_manager_boundary_error
from agency_runtime.core.routing_snapshot import (
    bind_workforce_snapshot,
    capture_operational_routing_snapshot,
)
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.turn_correlation import active_turn_error

ToolHandler = Callable[[dict[str, Any], Any], dict[str, Any]]


def _correlation(arguments: dict[str, Any]) -> tuple[str, str] | None:
    try:
        session_id = validate_correlation_id(arguments.get("session_id"), field="session_id")
        trace_id = validate_correlation_id(arguments.get("trace_id"), field="trace_id")
    except ValueError:
        return None
    if session_id != arguments.get("session_id") or trace_id != arguments.get("trace_id"):
        return None
    return session_id, trace_id


def _noncanonical_identifier(arguments: dict[str, Any], *fields: str) -> str | None:
    """Reject identifiers the Store would otherwise normalize or truncate."""

    for field in fields:
        raw = arguments.get(field)
        if raw in (None, ""):
            continue
        if not isinstance(raw, str) or " ".join(raw.split()) != raw:
            return field
    return None


def _consume_parent_scope(
    store: Any,
    *,
    parent_scope_token: str,
    host: str,
    session_id: str,
    trace_id: str,
) -> tuple[dict[str, Any], str]:
    if not parent_scope_token:
        return {}, ""
    consumer = getattr(store, "consume_native_child_parent_scope", None)
    if not callable(consumer):
        return {}, "native child parent scope verification is unavailable"
    try:
        consumed = consumer(
            parent_scope_token=parent_scope_token,
            host=host,
            child_session_id=session_id,
            child_trace_id=trace_id,
        )
    except ValueError as exc:
        return {}, str(exc)
    except Exception:
        return {}, "native child parent scope verification is unavailable"
    if not isinstance(consumed, dict):
        return {}, "native child parent scope verification is unavailable"
    return consumed, ""


def _restore_parent_scope(
    store: Any,
    *,
    parent_scope_token: str,
    host: str,
    session_id: str,
    trace_id: str,
) -> bool:
    restorer = getattr(
        store,
        "restore_native_child_parent_scope_after_failed_preflight",
        None,
    )
    if not callable(restorer):
        return False
    try:
        restorer(
            parent_scope_token=parent_scope_token,
            host=host,
            child_session_id=session_id,
            child_trace_id=trace_id,
        )
    except Exception:
        return False
    return True


def _preflight(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.preflight import run_preflight
    from agency_runtime.core.turn_origin import native_adapter_turn_origin

    session_id = str(arguments.get("session_id") or "").strip()
    if not session_id:
        return {"error": "session_id is required for Agency preflight correlation"}
    host = str(arguments.get("host") or "").strip().casefold()
    if host not in EXECUTION_HOSTS:
        return {
            "error": "host must identify one execution host: codex, claude, openclaw, hermes, or zcode"
        }
    trace_id = str(arguments.get("trace_id") or "").strip() or str(uuid4())
    user_message = arguments.get("user_message")
    if not isinstance(user_message, str) or not user_message.strip():
        return {"error": "user_message is required for Agency preflight routing"}
    parent_scope_token = str(arguments.get("parent_scope_token") or "").strip()
    parent_scope, parent_scope_error = _consume_parent_scope(
        store,
        parent_scope_token=parent_scope_token,
        host=host,
        session_id=session_id,
        trace_id=trace_id,
    )
    if parent_scope_error:
        return {"error": parent_scope_error}
    origin_receipt = native_adapter_turn_origin(
        "external_user",
        host=host,
        event="adapter_preflight",
        session_id=session_id,
        trace_id=trace_id,
    )
    preflight_succeeded = False
    try:
        result = run_preflight(
            store,
            session_id=session_id,
            host=host,
            user_message=user_message,
            trace_id=trace_id,
            origin_receipt=origin_receipt,
            parent_session_id=str(parent_scope.get("parent_session_id") or ""),
            parent_trace_id=str(parent_scope.get("parent_trace_id") or ""),
            native_worker_id=str(parent_scope.get("worker_id") or ""),
            native_run_id=str(parent_scope.get("native_run_id") or ""),
        )
        preflight_succeeded = True
    except BaseException as exc:
        restored = (
            not parent_scope_token
            or not parent_scope
            or _restore_parent_scope(
                store,
                parent_scope_token=parent_scope_token,
                host=host,
                session_id=session_id,
                trace_id=trace_id,
            )
        )
        if not restored:
            if isinstance(exc, Exception):
                return {"error": "native child parent scope retry is unavailable"}
            raise
        if isinstance(exc, ValueError):
            return {"error": str(exc)}
        raise
    if not preflight_succeeded:  # pragma: no cover - defensive narrowing
        return {"error": "Agency preflight did not complete"}
    return {
        "context": result.context or "No routing suggestion.",
        "session_id": result.session_id,
        "trace_id": result.trace_id,
        "loaded_specialists": list(result.loaded_specialists),
        "selected_specialists": list(result.selected_specialists),
        "delegation_plan": [dict(item) for item in result.delegation_plan],
    }


def _search_agents(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.selector.candidate_narrow import pre_narrow

    candidates, _scores = pre_narrow(
        arguments["query"],
        store.get_active_roster_as_catalog(),
        limit=10,
    )
    return {"agents": candidates}


def _explain_selection(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.selector.explain import explain_route

    snapshot = capture_operational_routing_snapshot(store)
    snapshot, workforce = bind_workforce_snapshot(store, snapshot)
    return explain_route(
        arguments.get("session_id", ""),
        arguments["task"],
        snapshot.catalog,
        config=snapshot.config,
        limit=arguments.get("limit"),
        store=store,
        workforce_snapshot=workforce,
    )


def _load_specialist(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    correlation = _correlation(arguments)
    if correlation is None:
        return {"error": "session_id and trace_id are required to load active specialist evidence"}
    session_id, trace_id = correlation
    if field := _noncanonical_identifier(arguments, "slug"):
        return {"error": f"{field} must be an exact canonical identifier"}
    if error := active_turn_error(store, session_id, trace_id):
        return {"error": error}
    slug = str(arguments["slug"]).strip()
    if error := resident_manager_boundary_error(
        slug,
        operation="be loaded as an ordinary specialist",
    ):
        return {"error": error}
    # The specialist goes to whoever is already doing the work. There is no
    # token to redeem and no receipt to file: loading a card is the product.
    row = store.get_specialist_prompt(slug)
    if not row or not row.get("prompt_body"):
        return {"error": f"active agent prompt '{slug}' not found"}
    prompt = str(row["prompt_body"])
    if bool(row.get("prompt_truncated")) or len(prompt) > MAX_SPECIALIST_PROMPT_CHARS:
        return {
            "error": (
                f"active agent prompt '{slug}' exceeds the exact-delivery ceiling; "
                "no specialist evidence was recorded"
            )
        }
    store.record_specialist_loaded(session_id, slug, trace_id=trace_id)
    return {
        "trace_id": trace_id,
        "session_id": session_id,
        "slug": slug,
        "name": row.get("name", ""),
        "description": row.get("description", ""),
        "version": row.get("version", ""),
        "prompt_hash": row.get("prompt_hash") or row.get("hash") or "",
        "prompt": prompt,
        "prompt_truncated": False,
    }


def _record_skill_loaded(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    correlation = _correlation(arguments)
    if correlation is None:
        return {"error": "session_id and trace_id are required to record skill evidence"}
    session_id, trace_id = correlation
    if error := active_turn_error(store, session_id, trace_id):
        return {"error": error}
    store.record_skill_loaded(
        session_id,
        arguments["skill_name"],
        trace_id=trace_id,
    )
    return {"status": "recorded"}


def _finalize(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.header.finalize import finalize_response

    correlation = _correlation(arguments)
    if correlation is None:
        return {
            "action": "continue",
            "text": arguments["draft_text"],
            "missing": [
                name
                for name in ("session_id", "trace_id")
                if not str(arguments.get(name) or "").strip()
            ],
        }
    session_id, trace_id = correlation
    result = finalize_response(
        arguments["draft_text"],
        trace_metadata={
            "trace_id": trace_id,
            "session_id": session_id,
            "host": "mcp",
        },
        store=store,
        model="",
    )
    return dict(result)


def _status(_arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.host_control import SUPPORTED_HOSTS, get_runtime_control

    return {
        "roster_count": store.count_enabled_roster(),
        "storage": {"backend": "sqlite", "binding": "verified"},
        "hosts": {host: get_runtime_control(store, host) for host in SUPPORTED_HOSTS},
    }


def _host_status(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.host_control import inspect_host_status

    return inspect_host_status(store, str(arguments["host"]))


_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "agency.preflight": _preflight,
    "agency.search_agents": _search_agents,
    "agency.explain_selection": _explain_selection,
    "agency.load_specialist": _load_specialist,
    "agency.record_skill_loaded": _record_skill_loaded,
    "agency.finalize": _finalize,
    "agency.status": _status,
    "agency.host_status": _host_status,
}


def dispatch_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    store: Any,
) -> dict[str, Any]:
    """Execute one known tool or return the stable direct-call error shape."""

    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return {"error": f"unknown tool: {tool_name}"}
    return handler(arguments, store)


__all__ = ["dispatch_tool_call"]
