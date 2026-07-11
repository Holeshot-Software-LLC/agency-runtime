"""Dependency-light MCP server for Agency Runtime.

The stdio transport follows MCP's newline-delimited JSON-RPC contract.  Nothing
except protocol messages is ever written to stdout; diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from collections.abc import Sequence
from typing import Any, BinaryIO, TextIO

from agency_runtime import __version__

logger = logging.getLogger("agency_runtime.server.mcp")

LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = (
    LATEST_PROTOCOL_VERSION,
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
MAX_INPUT_BYTES = 1_048_576
MAX_OUTPUT_BYTES = 1_048_576
MAX_BATCH_SIZE = 64


def _schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


# MCP tool definitions.  Annotations are hints only; enforcement remains in
# the runtime and the calling host.
MCP_TOOLS = [
    {
        "name": "agency.preflight",
        "description": "Run agency specialist routing preflight for a user message.",
        "inputSchema": _schema(
            {
                "session_id": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "user_message": {"type": "string", "maxLength": 262_144},
            },
            ["user_message"],
        ),
    },
    {
        "name": "agency.search_agents",
        "description": "Search the active agent roster.",
        "inputSchema": _schema({"query": {"type": "string", "maxLength": 16_384}}, ["query"]),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "agency.explain_selection",
        "description": "Explain why specialists were selected for a task.",
        "inputSchema": _schema(
            {
                "session_id": {"type": "string", "maxLength": 512},
                "task": {"type": "string", "maxLength": 262_144},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            ["task"],
        ),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "agency.load_specialist",
        "description": "Load a specialist agent prompt.",
        "inputSchema": _schema(
            {
                "slug": {"type": "string", "maxLength": 256},
                "session_id": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
            },
            ["slug", "session_id"],
        ),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "agency.record_skill_loaded",
        "description": "Record that a skill was loaded in the current session.",
        "inputSchema": _schema(
            {
                "session_id": {"type": "string", "maxLength": 512},
                "skill_name": {"type": "string", "maxLength": 512},
            },
            ["skill_name"],
        ),
    },
    {
        "name": "agency.delegate",
        "description": "Record a delegated work unit and its backend correlation.",
        "inputSchema": _schema(
            {
                "agent": {"type": "string", "maxLength": 512},
                "task": {"type": "string", "maxLength": 262_144},
                "backend": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "session_id": {"type": "string", "maxLength": 512},
                "work_unit_id": {"type": "string", "maxLength": 512},
            },
            ["agent", "task"],
        ),
    },
    {
        "name": "agency.finalize",
        "description": "Finalize the agency header on a draft response.",
        "inputSchema": _schema(
            {
                "draft_text": {"type": "string", "maxLength": 524_288},
                "trace_id": {"type": "string", "maxLength": 512},
                "session_id": {"type": "string", "maxLength": 512},
                "host": {"type": "string", "maxLength": 128},
                "model": {"type": "string", "maxLength": 512},
            },
            ["draft_text"],
        ),
    },
    {
        "name": "agency.status",
        "description": "Get agency runtime status.",
        "inputSchema": _schema({}),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
]

_TOOLS_BY_NAME = {tool["name"]: tool for tool in MCP_TOOLS}


def handle_tool_call(tool_name: str, arguments: dict[str, Any], store=None) -> dict[str, Any]:
    """Dispatch a tool call to the existing runtime core."""
    from agency_runtime.core.store.sqlite import Store as _Store

    s = store if store is not None else _Store()

    if tool_name == "agency.preflight":
        from agency_runtime.core.selector.pipeline import route_and_build_context

        trace_id = str(arguments.get("trace_id") or uuid.uuid4())
        context = route_and_build_context(
            arguments.get("session_id", ""),
            arguments["user_message"],
            s.get_active_roster_as_catalog(),
            store=s,
            trace_id=trace_id,
        )
        return {
            "context": context or "No routing suggestion.",
            "trace_id": trace_id,
        }

    if tool_name == "agency.search_agents":
        from agency_runtime.core.selector.candidate_narrow import pre_narrow

        candidates, _scores = pre_narrow(
            arguments["query"],
            s.get_active_roster_as_catalog(),
            limit=10,
        )
        return {"agents": candidates}

    if tool_name == "agency.explain_selection":
        from agency_runtime.core.selector.explain import explain_route

        return explain_route(
            arguments.get("session_id", ""),
            arguments["task"],
            s.get_active_roster_as_catalog(),
            limit=arguments.get("limit"),
            store=s,
        )

    if tool_name == "agency.load_specialist":
        slug = str(arguments["slug"])
        session_id = str(arguments["session_id"])
        trace_id = str(arguments.get("trace_id") or uuid.uuid4())
        row = s.get_specialist_prompt(slug)
        if not row or not row.get("prompt_body"):
            return {"error": f"active agent prompt '{slug}' not found"}
        s.record_specialist_loaded(session_id, slug)
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

    if tool_name == "agency.record_skill_loaded":
        s.record_skill_loaded(arguments.get("session_id", ""), arguments["skill_name"])
        return {"status": "recorded"}

    if tool_name == "agency.delegate":
        trace_id = str(arguments.get("trace_id") or arguments.get("session_id") or uuid.uuid4())
        s.record_delegation(
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

    if tool_name == "agency.finalize":
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

    if tool_name == "agency.status":
        return {"roster_count": len(s.get_active_roster()), "db_path": str(s.db_path)}

    return {"error": f"unknown tool: {tool_name}"}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _is_request_id(value: Any) -> bool:
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def _validate_tool_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    schema = tool["inputSchema"]
    properties = schema.get("properties", {})
    for required in schema.get("required", []):
        if required not in arguments:
            return f"missing required argument: {required}"
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(arguments) - set(properties))
        if unexpected:
            return f"unexpected argument: {unexpected[0]}"
    for key, value in arguments.items():
        spec = properties.get(key, {})
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            return f"argument '{key}' must be a string"
        if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
            return f"argument '{key}' must be an integer"
        if isinstance(value, str) and len(value) > int(spec.get("maxLength", len(value))):
            return f"argument '{key}' exceeds its maximum length"
        if isinstance(value, int) and not isinstance(value, bool):
            if "minimum" in spec and value < spec["minimum"]:
                return f"argument '{key}' is below its minimum"
            if "maximum" in spec and value > spec["maximum"]:
                return f"argument '{key}' exceeds its maximum"
    return None


def _call_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }


class MCPServer:
    """Small stateful JSON-RPC dispatcher for the MCP stdio lifecycle."""

    def __init__(self, *, store=None) -> None:
        self.store = store
        self.initialize_responded = False
        self.initialized = False
        self.protocol_version = LATEST_PROTOCOL_VERSION

    def _runtime_store(self):
        """Open and migrate the SQLite store once, on the first tool call."""
        if self.store is None:
            from agency_runtime.core.store.sqlite import Store

            self.store = Store()
        return self.store

    def dispatch(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return _error(None, -32600, "Invalid Request")

        request_id = message.get("id")
        has_id = "id" in message
        if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return _error(request_id if _is_request_id(request_id) else None, -32600, "Invalid Request")
        if has_id and not _is_request_id(request_id):
            return _error(None, -32600, "Invalid Request")
        params = message.get("params", {})
        if not isinstance(params, dict):
            return None if not has_id else _error(request_id, -32602, "Invalid params")

        method = message["method"]
        if method == "initialize":
            if not has_id or self.initialize_responded:
                return None if not has_id else _error(request_id, -32600, "Invalid Request")
            requested = params.get("protocolVersion")
            capabilities = params.get("capabilities")
            client_info = params.get("clientInfo")
            if not isinstance(requested, str) or not isinstance(capabilities, dict) or not isinstance(client_info, dict):
                return _error(request_id, -32602, "Invalid initialize parameters")
            if not isinstance(client_info.get("name"), str) or not isinstance(client_info.get("version"), str):
                return _error(request_id, -32602, "Invalid clientInfo")
            self.protocol_version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
            self.initialize_responded = True
            return _result(
                request_id,
                {
                    "protocolVersion": self.protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "agency-runtime",
                        "title": "Agency Runtime",
                        "version": __version__,
                    },
                    "instructions": "Use Agency tools for specialist routing, evidence, and response finalization.",
                },
            )

        if method == "notifications/initialized":
            if not has_id and self.initialize_responded:
                self.initialized = True
            return None if not has_id else _error(request_id, -32600, "initialized must be a notification")

        # Notifications never receive JSON-RPC responses, including unknown ones.
        if not has_id:
            return None

        if method == "ping":
            return _result(request_id, {})
        if not self.initialized:
            return _error(request_id, -32002, "Server not initialized")

        if method == "tools/list":
            return _result(request_id, {"tools": MCP_TOOLS})

        if method == "tools/call":
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                return _error(request_id, -32602, "Invalid tools/call parameters")
            tool = _TOOLS_BY_NAME.get(name)
            if tool is None:
                return _error(request_id, -32602, f"Unknown tool: {name}")
            validation_error = _validate_tool_arguments(tool, arguments)
            if validation_error:
                return _result(request_id, _call_result({"error": validation_error}, is_error=True))
            try:
                payload = handle_tool_call(name, arguments, store=self._runtime_store())
            except Exception:
                logger.exception("MCP tool execution failed: %s", name)
                return _result(
                    request_id,
                    _call_result({"error": "Agency Runtime tool execution failed safely."}, is_error=True),
                )
            return _result(request_id, _call_result(payload, is_error=bool(payload.get("error"))))

        return _error(request_id, -32601, "Method not found")

    def dispatch_payload(self, payload: Any) -> dict[str, Any] | list[dict[str, Any]] | None:
        if not isinstance(payload, list):
            return self.dispatch(payload)
        if not payload or len(payload) > MAX_BATCH_SIZE:
            return _error(None, -32600, "Invalid Request")
        if any(isinstance(item, dict) and item.get("method") == "initialize" for item in payload):
            return _error(None, -32600, "initialize cannot be batched")
        responses = [response for item in payload if (response := self.dispatch(item)) is not None]
        return responses or None


def _write_json(stream: BinaryIO | TextIO, payload: Any) -> bool:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(encoded) > MAX_OUTPUT_BYTES:
        request_id = payload.get("id") if isinstance(payload, dict) else None
        encoded = json.dumps(
            _error(request_id, -32603, "Response exceeds server output limit"),
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
    try:
        stream.write(encoded)  # type: ignore[arg-type]
    except TypeError:
        stream.write(encoded.decode("utf-8"))  # type: ignore[arg-type]
    stream.flush()
    return True


def run_stdio(*, store=None, input_stream: BinaryIO | TextIO | None = None, output_stream: BinaryIO | TextIO | None = None) -> int:
    """Serve newline-delimited MCP JSON-RPC until stdin closes."""
    source = input_stream or sys.stdin.buffer
    sink = output_stream or sys.stdout.buffer
    server = MCPServer(store=store)

    while True:
        raw = source.readline(MAX_INPUT_BYTES + 1)
        if raw in (b"", ""):
            return 0
        raw_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
        if len(raw_bytes) > MAX_INPUT_BYTES:
            _write_json(sink, _error(None, -32700, "Message exceeds server input limit"))
            return 1
        if not raw_bytes.strip():
            continue
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _write_json(sink, _error(None, -32700, "Parse error"))
            continue
        response = server.dispatch_payload(payload)
        if response is not None:
            _write_json(sink, response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agency_runtime.server.mcp")
    parser.add_argument("--stdio", action="store_true", help="Serve MCP over stdin/stdout (default transport)")
    parser.add_argument("--db", default=None, help="SQLite database path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    del args.stdio  # stdio is the only supported transport today.
    store = None
    if args.db:
        from agency_runtime.core.store.sqlite import Store

        store = Store(args.db)
    return run_stdio(store=store)


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
