"""Dependency-light MCP server for Agency Runtime.

The stdio transport follows MCP's newline-delimited JSON-RPC contract.  Nothing
except protocol messages is ever written to stdout; diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, BinaryIO, TextIO

from agency_runtime import __version__
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json

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
_CANARY_MUTATING_TOOLS = frozenset(
    {
        "agency.preflight",
        "agency.explain_selection",
        "agency.prepare_delegation",
        "agency.load_specialist",
        "agency.record_skill_loaded",
        "agency.delegate",
        "agency.decline_delegation",
        "agency.finalize",
        "agency.host_control",
    }
)


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
                "parent_session_id": {"type": "string", "maxLength": 512},
                "parent_trace_id": {"type": "string", "maxLength": 512},
                "host": {
                    "type": "string",
                    "enum": ["codex", "claude", "openclaw", "hermes"],
                },
                "user_message": {"type": "string", "maxLength": 262_144},
            },
            ["session_id", "host", "user_message"],
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
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            ["task"],
        ),
    },
    {
        "name": "agency.prepare_delegation",
        "description": (
            "Issue a one-use work-unit grant for an exact selected specialist version."
        ),
        "inputSchema": _schema(
            {
                "slug": {"type": "string", "maxLength": 128},
                "session_id": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "work_unit_id": {"type": "string", "maxLength": 160},
                "worker_kind": {"type": "string", "maxLength": 64},
                "worker_id": {"type": "string", "maxLength": 256},
            },
            ["slug", "session_id", "trace_id", "work_unit_id"],
        ),
    },
    {
        "name": "agency.load_specialist",
        "description": "Consume an isolated activation grant or load a direct specialist prompt.",
        "inputSchema": _schema(
            {
                "slug": {"type": "string", "maxLength": 256},
                "session_id": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "activation_token": {"type": "string", "maxLength": 256},
                "work_unit_id": {"type": "string", "maxLength": 160},
                "worker_id": {"type": "string", "maxLength": 256},
                "native_run_id": {"type": "string", "maxLength": 256},
            },
            ["slug", "session_id", "trace_id"],
        ),
    },
    {
        "name": "agency.record_skill_loaded",
        "description": "Record that a skill was loaded in the current session.",
        "inputSchema": _schema(
            {
                "session_id": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "skill_name": {"type": "string", "maxLength": 512},
            },
            ["session_id", "trace_id", "skill_name"],
        ),
    },
    {
        "name": "agency.delegate",
        "description": "Record an observed delegation executed by a named backend.",
        "inputSchema": _schema(
            {
                "agent": {"type": "string", "maxLength": 512},
                "task": {"type": "string", "maxLength": 262_144},
                "backend": {"type": "string", "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "session_id": {"type": "string", "maxLength": 512},
                "work_unit_id": {"type": "string", "maxLength": 512},
                "worker_kind": {"type": "string", "maxLength": 64},
                "worker_id": {"type": "string", "maxLength": 256},
                "native_run_id": {"type": "string", "maxLength": 256},
            },
            [
                "agent",
                "task",
                "backend",
                "session_id",
                "trace_id",
                "work_unit_id",
                "worker_kind",
                "worker_id",
                "native_run_id",
            ],
        ),
    },
    {
        "name": "agency.decline_delegation",
        "description": (
            "Record an explicit native-host decision not to execute one exact suggested "
            "delegation. This never launches a worker."
        ),
        "inputSchema": _schema(
            {
                "agent": {"type": "string", "maxLength": 128},
                "reason": {"type": "string", "minLength": 1, "maxLength": 512},
                "trace_id": {"type": "string", "maxLength": 512},
                "session_id": {"type": "string", "maxLength": 512},
                "work_unit_id": {"type": "string", "maxLength": 160},
            },
            ["agent", "reason", "session_id", "trace_id", "work_unit_id"],
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
            ["draft_text", "session_id", "trace_id"],
        ),
    },
    {
        "name": "agency.status",
        "description": "Get agency runtime status.",
        "inputSchema": _schema({}),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "agency.host_status",
        "description": "Inspect native and soft-control state for one supported host.",
        "inputSchema": _schema(
            {
                "host": {
                    "type": "string",
                    "enum": ["hermes", "openclaw", "codex", "claude"],
                }
            },
            ["host"],
        ),
        "annotations": {"readOnlyHint": True, "idempotentHint": True},
    },
    {
        "name": "agency.host_control",
        "description": "Enable or disable Agency Runtime for one host after exact confirmation.",
        "inputSchema": _schema(
            {
                "host": {
                    "type": "string",
                    "enum": ["hermes", "openclaw", "codex", "claude"],
                },
                "enabled": {"type": "boolean"},
                "expected_generation": {"type": "integer", "minimum": 0},
                "confirm": {"type": "string", "maxLength": 128},
            },
            ["host", "enabled", "expected_generation", "confirm"],
        ),
        "annotations": {"idempotentHint": True},
    },
]

_TOOLS_BY_NAME = {tool["name"]: tool for tool in MCP_TOOLS}
_STORE_CONTROL_PLANE_TOOLS = frozenset({"agency.host_status", "agency.host_control"})


def _runtime_disabled_tool_result(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    master: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stable no-evidence result without constructing the Store."""

    if tool_name == "agency.finalize":
        return {
            "action": "bypass",
            "text": str(arguments.get("draft_text") or ""),
            "runtime_enabled": False,
            "bypassed": True,
        }
    if tool_name == "agency.status":
        if master is None:
            from agency_runtime.core.runtime_control import read_enforcement_runtime_control

            master, _master_transport = read_enforcement_runtime_control()
        return {"runtime_enabled": False, "bypassed": True, "master": master}
    return {"runtime_enabled": False, "bypassed": True}


def handle_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    store=None,
    *,
    _master: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch a tool call to the existing runtime core."""
    from agency_runtime.core.runtime_control import read_enforcement_runtime_control

    master = _master
    if master is None:
        master, _master_transport = read_enforcement_runtime_control()
    if not master["enabled"] and tool_name not in _STORE_CONTROL_PLANE_TOOLS:
        return _runtime_disabled_tool_result(tool_name, arguments, master=master)
    if os.environ.get("AGENCY_CANARY_MODE") == "1" and tool_name in _CANARY_MUTATING_TOOLS:
        return {"error": "mutating Agency tools are disabled during a live canary"}
    from agency_runtime.core.store.sqlite import Store as _Store
    from agency_runtime.server.mcp_tools import dispatch_tool_call

    s = store if store is not None else _Store()
    from agency_runtime.core.config_binding import assert_store_config_binding

    assert_store_config_binding(s)
    return dispatch_tool_call(tool_name, arguments, s)


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _is_request_id(value: Any) -> bool:
    return isinstance(value, (str, int)) and not isinstance(value, bool)


def _validate_argument(key: str, value: Any, spec: dict[str, Any]) -> str | None:
    expected = spec.get("type")
    if expected == "string" and not isinstance(value, str):
        return f"argument '{key}' must be a string"
    if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        return f"argument '{key}' must be an integer"
    if expected == "boolean" and not isinstance(value, bool):
        return f"argument '{key}' must be a boolean"
    if "enum" in spec and value not in spec["enum"]:
        return f"argument '{key}' must be one of: {', '.join(spec['enum'])}"
    if isinstance(value, str) and len(value) > int(spec.get("maxLength", len(value))):
        return f"argument '{key}' exceeds its maximum length"
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if "minimum" in spec and value < spec["minimum"]:
        return f"argument '{key}' is below its minimum"
    if "maximum" in spec and value > spec["maximum"]:
        return f"argument '{key}' exceeds its maximum"
    return None


def _validate_tool_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    schema = tool["inputSchema"]
    properties = schema.get("properties", {})
    missing = next(
        (name for name in schema.get("required", []) if name not in arguments),
        None,
    )
    if missing is not None:
        return f"missing required argument: {missing}"
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(arguments) - set(properties))
        if unexpected:
            return f"unexpected argument: {unexpected[0]}"
    for key, value in arguments.items():
        if error := _validate_argument(key, value, properties.get(key, {})):
            return error
    return None


def _call_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }


@dataclass(frozen=True, slots=True)
class _RequestEnvelope:
    request_id: Any
    has_id: bool
    method: str
    params: dict[str, Any]


def _parse_request_envelope(
    message: Any,
) -> tuple[_RequestEnvelope | None, dict[str, Any] | None]:
    if not isinstance(message, dict):
        return None, _error(None, -32600, "Invalid Request")
    request_id = message.get("id")
    has_id = "id" in message
    method = message.get("method")
    if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
        response_id = request_id if _is_request_id(request_id) else None
        return None, _error(response_id, -32600, "Invalid Request")
    if has_id and not _is_request_id(request_id):
        return None, _error(None, -32600, "Invalid Request")
    params = message.get("params", {})
    if not isinstance(params, dict):
        response = None if not has_id else _error(request_id, -32602, "Invalid params")
        return None, response
    return _RequestEnvelope(request_id, has_id, method, params), None


_INITIALIZED_REQUEST_HANDLERS = {
    "tools/list": "_dispatch_tools_list",
    "tools/call": "_dispatch_tools_call",
}


class MCPServer:
    """Small stateful JSON-RPC dispatcher for the MCP stdio lifecycle."""

    def __init__(
        self,
        *,
        store=None,
        db_path: str | None = None,
        config_path: str | None = None,
    ) -> None:
        if store is not None and (db_path is not None or config_path is not None):
            from agency_runtime.core.config_binding import (
                assert_store_requested_runtime_identity,
            )

            assert_store_requested_runtime_identity(
                store,
                config_path=config_path,
                db_path=db_path,
            )
        self.store = store
        self._db_path = db_path
        self._config_path = config_path
        self.initialize_responded = False
        self.initialized = False
        self.protocol_version = LATEST_PROTOCOL_VERSION

    def _runtime_store(self):
        """Open and migrate the SQLite store once, on the first tool call."""
        if self.store is None:
            from agency_runtime.core.store.sqlite import Store

            self.store = (
                Store(self._db_path, config_path=self._config_path)
                if self._config_path
                else Store(self._db_path)
            )
        return self.store

    def _dispatch_initialize(
        self,
        request: _RequestEnvelope,
    ) -> dict[str, Any] | None:
        if not request.has_id:
            return None
        if self.initialize_responded:
            return _error(request.request_id, -32600, "Invalid Request")
        requested = request.params.get("protocolVersion")
        capabilities = request.params.get("capabilities")
        client_info = request.params.get("clientInfo")
        if not all(
            (
                isinstance(requested, str),
                isinstance(capabilities, dict),
                isinstance(client_info, dict),
            )
        ):
            return _error(request.request_id, -32602, "Invalid initialize parameters")
        if not isinstance(client_info.get("name"), str) or not isinstance(
            client_info.get("version"), str
        ):
            return _error(request.request_id, -32602, "Invalid clientInfo")
        self.protocol_version = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        self.initialize_responded = True
        return _result(
            request.request_id,
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

    def _dispatch_initialized(
        self,
        request: _RequestEnvelope,
    ) -> dict[str, Any] | None:
        if request.has_id:
            return _error(
                request.request_id,
                -32600,
                "initialized must be a notification",
            )
        if self.initialize_responded:
            self.initialized = True
        return None

    @staticmethod
    def _dispatch_tools_list(request: _RequestEnvelope) -> dict[str, Any]:
        return _result(request.request_id, {"tools": MCP_TOOLS})

    def _dispatch_tools_call(self, request: _RequestEnvelope) -> dict[str, Any]:
        name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(request.request_id, -32602, "Invalid tools/call parameters")
        tool = _TOOLS_BY_NAME.get(name)
        if tool is None:
            return _error(request.request_id, -32602, f"Unknown tool: {name}")
        from agency_runtime.core.runtime_control import read_enforcement_runtime_control

        master, _master_transport = read_enforcement_runtime_control()
        if not master["enabled"] and name not in _STORE_CONTROL_PLANE_TOOLS:
            payload = _runtime_disabled_tool_result(name, arguments, master=master)
            return _result(request.request_id, _call_result(payload))
        validation_error = _validate_tool_arguments(tool, arguments)
        if validation_error:
            result = _call_result({"error": validation_error}, is_error=True)
            return _result(request.request_id, result)
        try:
            runtime_store = self._runtime_store()
            payload = handle_tool_call(
                name,
                arguments,
                store=runtime_store,
                _master=master,
            )
        except Exception:
            logger.exception("MCP tool execution failed: %s", name)
            payload = {"error": "Agency Runtime tool execution failed safely."}
        return _result(
            request.request_id,
            _call_result(payload, is_error=bool(payload.get("error"))),
        )

    def dispatch(self, message: Any) -> dict[str, Any] | None:
        request, error = _parse_request_envelope(message)
        if request is None:
            return error
        if request.method == "initialize":
            return self._dispatch_initialize(request)
        if request.method == "notifications/initialized":
            return self._dispatch_initialized(request)
        # Notifications never receive JSON-RPC responses, including unknown ones.
        if not request.has_id:
            return None
        if request.method == "ping":
            return _result(request.request_id, {})
        if not self.initialized:
            return _error(request.request_id, -32002, "Server not initialized")
        handler_name = _INITIALIZED_REQUEST_HANDLERS.get(request.method)
        if handler_name is None:
            return _error(request.request_id, -32601, "Method not found")
        handler = getattr(self, handler_name)
        return handler(request)

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
    try:
        encoded = (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError):
        request_id = payload.get("id") if isinstance(payload, dict) else None
        encoded = (
            json.dumps(
                _error(request_id, -32603, "Response is not valid JSON"),
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    if len(encoded) > MAX_OUTPUT_BYTES:
        request_id = payload.get("id") if isinstance(payload, dict) else None
        encoded = (
            json.dumps(
                _error(request_id, -32603, "Response exceeds server output limit"),
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    try:
        stream.write(encoded)  # type: ignore[arg-type]
    except TypeError:
        stream.write(encoded.decode("utf-8"))  # type: ignore[arg-type]
    stream.flush()
    return True


def run_stdio(
    *,
    store=None,
    db_path: str | None = None,
    config_path: str | None = None,
    input_stream: BinaryIO | TextIO | None = None,
    output_stream: BinaryIO | TextIO | None = None,
) -> int:
    """Serve newline-delimited MCP JSON-RPC until stdin closes."""
    source = input_stream or sys.stdin.buffer
    sink = output_stream or sys.stdout.buffer
    server = MCPServer(
        store=store,
        db_path=db_path,
        config_path=config_path,
    )

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
            payload = safe_load_bounded_json(raw_bytes)
        except (BoundedJSONError, UnicodeDecodeError):
            _write_json(sink, _error(None, -32700, "Parse error"))
            continue
        response = server.dispatch_payload(payload)
        if response is not None:
            _write_json(sink, response)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agency_runtime.server.mcp")
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Serve MCP over stdin/stdout (default transport)",
    )
    parser.add_argument("--db", default=None, help="SQLite database path")
    parser.add_argument("--config", default=None, help="Agency YAML configuration path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    del args.stdio  # stdio is the only supported transport today.
    return run_stdio(db_path=args.db, config_path=args.config)


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    raise SystemExit(main())
