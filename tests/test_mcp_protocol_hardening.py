"""Adversarial unit coverage for the bounded MCP JSON-RPC boundary."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import agency_runtime.server.mcp as mcp
from agency_runtime.core.store.sqlite import Store


def _initialize(server: mcp.MCPServer, *, version: str = mcp.LATEST_PROTOCOL_VERSION) -> None:
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1"},
            },
        }
    )
    assert response is not None and response["result"]["protocolVersion"]
    assert (
        server.dispatch({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        is None
    )


def _ready_turn(store: Store, *, session_id: str, trace_id: str) -> None:
    store.create_run(trace_id=trace_id, session_id=session_id, host="mcp")
    connection = store._connect()
    try:
        changed = connection.execute(
            "UPDATE runs SET preflight_state = 'ready' WHERE trace_id = ?",
            (trace_id,),
        )
        connection.commit()
    finally:
        connection.close()
    assert changed.rowcount == 1
    run = store.get_run(trace_id)
    assert run is not None and run["preflight_state"] == "ready"


@pytest.mark.parametrize(
    "message",
    [
        None,
        [],
        "request",
        {},
        {"jsonrpc": "1.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1, "method": 7},
        {"jsonrpc": "2.0", "id": True, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1.5, "method": "ping"},
        {"jsonrpc": "2.0", "id": None, "method": "ping"},
    ],
)
def test_dispatch_rejects_invalid_request_envelopes(message: object) -> None:
    response = mcp.MCPServer(store=object()).dispatch(message)

    assert response is not None
    assert response["error"]["code"] == -32600


def test_stdio_rejects_duplicate_json_rpc_fields_as_parse_error() -> None:
    source = io.BytesIO(b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}\n')
    sink = io.BytesIO()

    assert mcp.run_stdio(store=object(), input_stream=source, output_stream=sink) == 0

    response = json.loads(sink.getvalue())
    assert response["error"] == {"code": -32700, "message": "Parse error"}


def test_stdio_rejects_nonfinite_response_values() -> None:
    sink = io.BytesIO()

    assert mcp._write_json(sink, {"id": 7, "result": float("nan")}) is True

    response = json.loads(sink.getvalue())
    assert response["id"] == 7
    assert response["error"] == {
        "code": -32603,
        "message": "Response is not valid JSON",
    }


def test_invalid_notification_params_never_receive_a_response() -> None:
    server = mcp.MCPServer(store=object())

    assert server.dispatch({"jsonrpc": "2.0", "method": "unknown", "params": []}) is None
    response = server.dispatch({"jsonrpc": "2.0", "id": 1, "method": "unknown", "params": []})
    assert response is not None and response["error"]["code"] == -32602


@pytest.mark.parametrize(
    "params,error_message",
    [
        ({}, "Invalid initialize parameters"),
        (
            {"protocolVersion": 1, "capabilities": {}, "clientInfo": {}},
            "Invalid initialize parameters",
        ),
        (
            {
                "protocolVersion": "future",
                "capabilities": [],
                "clientInfo": {},
            },
            "Invalid initialize parameters",
        ),
        (
            {
                "protocolVersion": "future",
                "capabilities": {},
                "clientInfo": {"name": "client"},
            },
            "Invalid clientInfo",
        ),
    ],
)
def test_initialize_validates_every_required_client_field(
    params: dict[str, object], error_message: str
) -> None:
    response = mcp.MCPServer(store=object()).dispatch(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": params}
    )

    assert response is not None
    assert response["error"] == {"code": -32602, "message": error_message}


def test_initialize_is_single_use_and_negotiates_unknown_versions() -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server, version="2099-01-01")

    assert server.protocol_version == mcp.LATEST_PROTOCOL_VERSION
    repeated = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "initialize",
            "params": {
                "protocolVersion": mcp.LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "again", "version": "1"},
            },
        }
    )
    assert repeated is not None and repeated["error"]["code"] == -32600
    assert (
        server.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "notifications/initialized",
                "params": {},
            }
        )["error"]["code"]
        == -32600
    )  # type: ignore[index]


def test_initialize_notification_is_ignored_and_ping_precedes_initialization() -> None:
    server = mcp.MCPServer(store=object())

    assert (
        server.dispatch(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": mcp.LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "notification", "version": "1"},
                },
            }
        )
        is None
    )
    assert server.initialize_responded is False
    assert server.dispatch({"jsonrpc": "2.0", "id": 9, "method": "ping", "params": {}}) == {
        "jsonrpc": "2.0",
        "id": 9,
        "result": {},
    }


def test_tools_require_initialized_notification() -> None:
    server = mcp.MCPServer(store=object())
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": mcp.LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        }
    )
    assert response is not None

    premature = server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert premature is not None and premature["error"]["code"] == -32002


def test_tool_schemas_do_not_claim_mutating_selection_calls_are_read_only() -> None:
    tools = {tool["name"]: tool for tool in mcp.MCP_TOOLS}

    assert "annotations" not in tools["agency.explain_selection"]
    assert "annotations" not in tools["agency.load_specialist"]
    assert tools["agency.search_agents"]["annotations"]["readOnlyHint"] is True


def test_argument_validator_supports_permissive_and_in_range_schemas() -> None:
    permissive = {
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
        }
    }
    bounded = {
        "inputSchema": {
            "type": "object",
            "properties": {"value": {"type": "integer", "minimum": 1, "maximum": 10}},
            "additionalProperties": False,
        }
    }

    assert mcp._validate_tool_arguments(permissive, {"extension": "ok"}) == (
        "argument 'extension' has no defined maximum length"
    )
    assert mcp._validate_tool_arguments(bounded, {"value": 5}) is None


@pytest.mark.parametrize(
    "name,arguments,fragment",
    [
        (
            "agency.preflight",
            {"session_id": "s", "user_message": "route this"},
            "missing required argument: host",
        ),
        ("agency.status", {"extra": 1}, "unexpected argument"),
        (
            "agency.preflight",
            {"session_id": "s", "host": "codex", "user_message": 1},
            "must be a string",
        ),
        ("agency.explain_selection", {"task": "x", "limit": True}, "must be an integer"),
        ("agency.host_status", {"host": "missing"}, "must be one of"),
        (
            "agency.preflight",
            {"session_id": "s", "host": "codex", "user_message": "x" * 262_145},
            "maximum length",
        ),
        ("agency.explain_selection", {"task": "x", "limit": 0}, "below its minimum"),
        ("agency.explain_selection", {"task": "x", "limit": 101}, "exceeds its maximum"),
    ],
)
def test_tool_argument_validation_returns_bounded_tool_errors(
    name: str, arguments: dict[str, object], fragment: str
) -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert fragment in result["structuredContent"]["error"]


@pytest.mark.parametrize(
    "params,fragment",
    [
        ({}, "Invalid tools/call parameters"),
        ({"name": 1, "arguments": {}}, "Invalid tools/call parameters"),
        ({"name": "agency.status", "arguments": []}, "Invalid tools/call parameters"),
        ({"name": "agency.missing", "arguments": {}}, "Unknown tool"),
    ],
)
def test_tools_call_rejects_invalid_dispatch_params(
    params: dict[str, object], fragment: str
) -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    response = server.dispatch(
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": params}
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert fragment in response["error"]["message"]


def test_every_published_string_is_bounded_and_hosts_share_one_vocabulary() -> None:
    host_enums: list[tuple[str, ...]] = []
    for tool in mcp.MCP_TOOLS:
        for spec in tool["inputSchema"]["properties"].values():
            if spec.get("type") == "string":
                assert isinstance(spec.get("maxLength"), int) and spec["maxLength"] > 0
            if "enum" in spec and set(spec["enum"]) == set(mcp.SUPPORTED_HOSTS):
                host_enums.append(tuple(spec["enum"]))

    assert host_enums
    assert all(values == tuple(mcp.SUPPORTED_HOSTS) for values in host_enums)


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        (
            "agency.preflight",
            {"session_id": "session", "host": "codex", "user_message": "review this"},
        ),
        ("agency.host_status", {"host": "zcode"}),
    ],
)
def test_valid_host_tools_reach_protocol_dispatch(
    name: str,
    arguments: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, dict[str, object]]] = []

    def handle(tool_name: str, values: dict[str, object], *_args: object, **_kwargs: object):
        observed.append((tool_name, values))
        return {"ok": True}

    monkeypatch.setattr(mcp, "handle_tool_call", handle)
    server = mcp.MCPServer(store=object())
    _initialize(server)
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )

    assert response is not None
    assert response["result"]["isError"] is False
    assert observed == [(name, arguments)]


def test_mutation_tool_and_finalize_identity_spoofing_fail_at_protocol_boundary() -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    mutation = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "agency.host_control", "arguments": {}},
        }
    )
    assert mutation is not None
    assert mutation["error"]["code"] == -32602
    assert "Unknown tool" in mutation["error"]["message"]

    spoof = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "agency.finalize",
                "arguments": {
                    "session_id": "session",
                    "trace_id": "trace",
                    "draft_text": "done",
                    "host": "spoofed",
                    "model": "spoofed",
                },
            },
        }
    )
    assert spoof is not None
    assert spoof["result"]["isError"] is True
    assert "unexpected argument" in spoof["result"]["structuredContent"]["error"]


def test_tool_exceptions_are_logged_and_sanitized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    def explode(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("secret-provider-token")

    monkeypatch.setattr(mcp, "handle_tool_call", explode)
    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "agency.status", "arguments": {}},
        }
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "failed safely" in result["structuredContent"]["error"]
    assert "secret-provider-token" not in result["content"][0]["text"]
    assert "MCP tool execution failed" in caplog.text


def test_successful_tool_dispatch_lazily_opens_the_default_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "default-mcp.db"))
    server = mcp.MCPServer()
    _initialize(server)

    response = server.dispatch(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "agency.status", "arguments": {}},
        }
    )

    assert response is not None
    assert response["result"]["isError"] is False
    assert response["result"]["structuredContent"]["roster_count"] == 0
    assert isinstance(server.store, Store)


def test_tools_list_unknown_method_and_notifications() -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    listed = server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert listed is not None and listed["result"]["tools"] == mcp.MCP_TOOLS
    assert server.dispatch({"jsonrpc": "2.0", "method": "tools/list", "params": {}}) is None
    missing = server.dispatch({"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}})
    assert missing is not None and missing["error"]["code"] == -32601


def test_batch_validation_and_notification_only_batches() -> None:
    server = mcp.MCPServer(store=object())

    assert server.dispatch_payload([])["error"]["code"] == -32600  # type: ignore[index]
    assert server.dispatch_payload([{}] * (mcp.MAX_BATCH_SIZE + 1))["error"]["code"] == -32600  # type: ignore[index]
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": mcp.LATEST_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "batch", "version": "1"},
        },
    }
    assert server.dispatch_payload([initialize])["error"]["code"] == -32600  # type: ignore[index]
    assert (
        server.dispatch_payload(
            [{"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}}]
        )
        is None
    )


def test_mixed_batch_preserves_only_request_responses() -> None:
    server = mcp.MCPServer(store=object())
    _initialize(server)

    response = server.dispatch_payload(
        [
            {"jsonrpc": "2.0", "id": "a", "method": "ping", "params": {}},
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {}},
            {"jsonrpc": "2.0", "id": "b", "method": "missing", "params": {}},
        ]
    )

    assert isinstance(response, list)
    assert [item["id"] for item in response] == ["a", "b"]


def test_write_json_supports_binary_and_text_streams_and_caps_output() -> None:
    binary = io.BytesIO()
    text = io.StringIO()
    payload = {"jsonrpc": "2.0", "id": 1, "result": {}}

    assert mcp._write_json(binary, payload) is True
    assert mcp._write_json(text, payload) is True
    assert json.loads(binary.getvalue()) == payload
    assert json.loads(text.getvalue()) == payload

    oversized = io.BytesIO()
    mcp._write_json(
        oversized,
        {"jsonrpc": "2.0", "id": "bounded", "result": {"text": "x" * mcp.MAX_OUTPUT_BYTES}},
    )
    error = json.loads(oversized.getvalue())
    assert error["id"] == "bounded"
    assert error["error"]["code"] == -32603


def test_stdio_handles_text_streams_blank_lines_and_parse_errors() -> None:
    source = io.StringIO(
        "\nnot-json\n"
        + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
        + "\n"
    )
    sink = io.StringIO()

    assert mcp.run_stdio(store=object(), input_stream=source, output_stream=sink) == 0
    responses = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert responses[1] == {"jsonrpc": "2.0", "id": 1, "result": {}}


def test_stdio_rejects_invalid_utf8_and_continues() -> None:
    source = io.BytesIO(
        b"\xff\n"
        + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}).encode("utf-8")
        + b"\n"
    )
    sink = io.BytesIO()

    assert mcp.run_stdio(store=object(), input_stream=source, output_stream=sink) == 0
    assert [json.loads(line)["id"] for line in sink.getvalue().splitlines()] == [None, 1]


def test_stdio_notification_only_input_emits_no_output() -> None:
    source = io.BytesIO(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {},
            }
        ).encode("utf-8")
        + b"\n"
    )
    sink = io.BytesIO()

    assert mcp.run_stdio(store=object(), input_stream=source, output_stream=sink) == 0
    assert sink.getvalue() == b""


def test_direct_tool_handlers_cover_status_search_record_and_errors(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    status = mcp.handle_tool_call("agency.status", {}, store)
    assert status["roster_count"] == 0
    assert set(status["hosts"]) == {"hermes", "openclaw", "codex", "claude", "zcode"}
    assert (
        mcp.handle_tool_call("agency.search_agents", {"query": "security"}, store)["agents"] == []
    )
    _ready_turn(store, session_id="s", trace_id="turn")
    assert (
        "not found"
        in mcp.handle_tool_call(
            "agency.load_specialist",
            {"slug": "missing", "session_id": "s", "trace_id": "turn"},
            store,
        )["error"]
    )
    assert mcp.handle_tool_call(
        "agency.record_skill_loaded",
        {"session_id": "s", "trace_id": "turn", "skill_name": "audit"},
        store,
    ) == {"status": "recorded"}
    delegated = mcp.handle_tool_call(
        "agency.delegate",
        {
            "agent": "reviewer",
            "task": "review",
            "session_id": "s",
            "trace_id": "turn",
            "work_unit_id": "u1",
            "backend": "test",
            "worker_kind": "test-worker",
            "worker_id": "worker-1",
            "native_run_id": "test:run-1",
        },
        store,
    )
    assert delegated["trace_id"] == "turn"
    assert delegated["work_unit_id"] == "u1"
    assert "unknown tool" in mcp.handle_tool_call("agency.missing", {}, store)["error"]


def test_main_defers_explicit_store_and_runs_stdio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}

    def fake_stdio(**kwargs: object) -> int:
        observed.update(kwargs)
        return 23

    monkeypatch.setattr(mcp, "run_stdio", fake_stdio)

    assert mcp.main(["--stdio", "--db", str(tmp_path / "mcp.db")]) == 23
    assert observed == {"db_path": str(tmp_path / "mcp.db"), "config_path": None}


def test_main_uses_lazy_default_store_when_db_is_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    def fake_stdio(**kwargs: object) -> int:
        observed.update(kwargs)
        return 0

    monkeypatch.setattr(mcp, "run_stdio", fake_stdio)

    assert mcp.main([]) == 0
    assert observed == {"db_path": None, "config_path": None}


def test_main_defers_store_from_explicit_config_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    config_path = tmp_path / "operator config" / "agency runtime.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        'store:\n  db_path: "runtime data/mcp.db"\n',
        encoding="utf-8",
    )

    def fake_stdio(**kwargs: object) -> int:
        observed.update(kwargs)
        return 19

    monkeypatch.setattr(mcp, "run_stdio", fake_stdio)

    assert mcp.main(["--stdio", "--config", str(config_path)]) == 19
    assert observed == {"db_path": None, "config_path": str(config_path)}
