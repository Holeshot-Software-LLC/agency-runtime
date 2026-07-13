"""Lazy Agency MCP tool implementations behind the public MCP facade."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

ToolHandler = Callable[[dict[str, Any], Any], dict[str, Any]]


def _preflight(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.selector.pipeline import route_and_build_context

    trace_id = str(arguments.get("trace_id") or uuid.uuid4())
    context = route_and_build_context(
        arguments.get("session_id", ""),
        arguments["user_message"],
        store.get_active_roster_as_catalog(),
        store=store,
        trace_id=trace_id,
    )
    return {"context": context or "No routing suggestion.", "trace_id": trace_id}


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

    return explain_route(
        arguments.get("session_id", ""),
        arguments["task"],
        store.get_active_roster_as_catalog(),
        limit=arguments.get("limit"),
        store=store,
    )


def _load_specialist(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    slug = str(arguments["slug"])
    session_id = str(arguments["session_id"])
    trace_id = str(arguments.get("trace_id") or uuid.uuid4())
    row = store.get_specialist_prompt(slug)
    if not row or not row.get("prompt_body"):
        return {"error": f"active agent prompt '{slug}' not found"}
    store.record_specialist_loaded(session_id, slug)
    return {
        "trace_id": trace_id,
        "session_id": session_id,
        "slug": slug,
        "name": row.get("name", ""),
        "description": row.get("description", ""),
        "version": row.get("version", ""),
        "prompt_hash": row.get("prompt_hash") or row.get("hash") or "",
        "prompt": row["prompt_body"],
        "prompt_truncated": bool(row.get("prompt_truncated")),
    }


def _record_skill_loaded(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    store.record_skill_loaded(arguments.get("session_id", ""), arguments["skill_name"])
    return {"status": "recorded"}


def _delegate(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    trace_id = str(arguments.get("trace_id") or arguments.get("session_id") or uuid.uuid4())
    store.record_delegation(
        trace_id=trace_id,
        session_id=arguments.get("session_id", ""),
        host="mcp",
        work_unit_id=arguments.get("work_unit_id", ""),
        recommended_agent=arguments["agent"],
        status="suggested",
        backend=arguments.get("backend", ""),
    )
    return {
        "status": "delegation suggested",
        "agent": arguments["agent"],
        "trace_id": trace_id,
        "work_unit_id": arguments.get("work_unit_id", ""),
    }


def _finalize(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.header.finalize import finalize_response

    trace_id = arguments.get("trace_id") or arguments.get("session_id", "")
    session_id = arguments.get("session_id") or trace_id
    result = finalize_response(
        arguments["draft_text"],
        trace_metadata={
            "trace_id": trace_id,
            "session_id": session_id,
            "host": arguments.get("host") or "mcp",
        },
        store=store,
        model=arguments.get("model", ""),
    )
    return dict(result)


def _status(_arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.host_control import SUPPORTED_HOSTS, get_runtime_control

    return {
        "roster_count": store.count_active_roster(),
        "db_path": str(store.db_path),
        "hosts": {host: get_runtime_control(store, host) for host in SUPPORTED_HOSTS},
    }


def _host_status(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.host_control import inspect_host_status

    return inspect_host_status(store, str(arguments["host"]))


def _host_control(arguments: dict[str, Any], store: Any) -> dict[str, Any]:
    from agency_runtime.core.host_control import set_runtime_control

    host = str(arguments["host"])
    enabled = bool(arguments["enabled"])
    expected = f"{'ENABLE' if enabled else 'DISABLE'} {host}"
    if arguments["confirm"] != expected:
        return {"error": f"confirmation must exactly match: {expected}"}
    control = set_runtime_control(store, host, enabled=enabled, source="mcp")
    return {"ok": True, **control}


_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "agency.preflight": _preflight,
    "agency.search_agents": _search_agents,
    "agency.explain_selection": _explain_selection,
    "agency.load_specialist": _load_specialist,
    "agency.record_skill_loaded": _record_skill_loaded,
    "agency.delegate": _delegate,
    "agency.finalize": _finalize,
    "agency.status": _status,
    "agency.host_status": _host_status,
    "agency.host_control": _host_control,
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
