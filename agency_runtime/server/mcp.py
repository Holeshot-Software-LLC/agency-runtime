"""MCP server — expose Agency as MCP tools for runtimes that can use them.

MCP is one adapter surface, not the whole architecture. A model may
choose not to call tools unless a host/wrapper forces it.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("agency_runtime.server.mcp")

# MCP tool definitions — these describe the tools to MCP-capable runtimes.
# The actual tool handlers call into the agency-runtime core.

MCP_TOOLS = [
    {
        "name": "agency.preflight",
        "description": "Run agency specialist routing preflight for a user message.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "user_message": {"type": "string"},
            },
            "required": ["user_message"],
        },
    },
    {
        "name": "agency.search_agents",
        "description": "Search the active agent roster.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "agency.explain_selection",
        "description": "Explain why specialists were selected for a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "task": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "agency.load_specialist",
        "description": "Load a specialist agent prompt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "agency.record_skill_loaded",
        "description": "Record that a skill was loaded in the current session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "skill_name": {"type": "string"},
            },
            "required": ["skill_name"],
        },
    },
    {
        "name": "agency.delegate",
        "description": "Delegate a work unit to a specialist via a worker backend.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "task": {"type": "string"},
                "backend": {"type": "string"},
            },
            "required": ["agent", "task"],
        },
    },
    {
        "name": "agency.finalize",
        "description": "Finalize the agency header on a draft response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "draft_text": {"type": "string"},
                "trace_id": {"type": "string"},
                "session_id": {"type": "string"},
                "host": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["draft_text"],
        },
    },
    {
        "name": "agency.status",
        "description": "Get agency runtime status.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_tool_call(tool_name: str, arguments: dict[str, Any], store=None) -> dict[str, Any]:
    """Handle an MCP tool call by dispatching to the core.

    This is a synchronous handler. Runtimes that support MCP can call
    these tools to interact with the agency-runtime control plane.
    """
    from agency_runtime.core.store.sqlite import Store as _Store
    s = store or _Store()

    if tool_name == "agency.preflight":
        from agency_runtime.core.selector.pipeline import route_and_build_context
        context = route_and_build_context(
            arguments.get("session_id", ""),
            arguments["user_message"],
            s.get_active_roster_as_catalog(),
        )
        return {"context": context or "No routing suggestion."}

    elif tool_name == "agency.search_agents":
        from agency_runtime.core.selector.candidate_narrow import pre_narrow
        catalog = s.get_active_roster_as_catalog()
        candidates, scores = pre_narrow(arguments["query"], catalog, limit=10)
        return {"agents": candidates}

    elif tool_name == "agency.explain_selection":
        from agency_runtime.core.selector.explain import explain_route
        return explain_route(
            arguments.get("session_id", ""),
            arguments["task"],
            s.get_active_roster_as_catalog(),
            limit=arguments.get("limit"),
        )

    elif tool_name == "agency.load_specialist":
        conn = s._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = ?",
                (arguments["slug"],),
            )
            row = cur.fetchone()
            return dict(row) if row else {"error": f"agent '{arguments['slug']}' not found"}
        finally:
            conn.close()

    elif tool_name == "agency.record_skill_loaded":
        s.record_skill_loaded(arguments.get("session_id", ""), arguments["skill_name"])
        return {"status": "recorded"}

    elif tool_name == "agency.delegate":
        s.record_delegation(
            trace_id=arguments.get("trace_id", ""),
            recommended_agent=arguments["agent"],
            status="suggested",
            backend=arguments.get("backend", ""),
        )
        return {"status": "delegation suggested", "agent": arguments["agent"]}

    elif tool_name == "agency.finalize":
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
            store=s,
            model=arguments.get("model", ""),
        )
        return dict(result)

    elif tool_name == "agency.status":
        roster = s.get_active_roster()
        return {
            "roster_count": len(roster),
            "db_path": str(s.db_path),
        }

    return {"error": f"unknown tool: {tool_name}"}
