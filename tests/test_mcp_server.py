"""Tests for the Agency Runtime MCP facade."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.mcp import MAX_INPUT_BYTES, MCP_TOOLS, handle_tool_call, run_stdio


def _seed_store(tmp_path: Path) -> Store:
    store = Store(tmp_path / "agency.db")
    store.activate_agent({
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "division": "engineering",
        "description": "Reviews code quality and security.",
        "source": "test",
        "version": "1.0",
        "hash": "abc123",
        "categories": ["code-review"],
        "capabilities": ["code-review"],
        "tool_affinity": [],
        "prompt_path": "",
    })
    return store


def test_mcp_exposes_explain_selection_tool() -> None:
    names = {tool["name"] for tool in MCP_TOOLS}

    assert "agency.explain_selection" in names


def test_mcp_load_specialist_returns_prompt_and_records_evidence(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)

    result = handle_tool_call(
        "agency.load_specialist",
        {"slug": "code-reviewer", "session_id": "session-load"},
        store=store,
    )

    assert result["slug"] == "code-reviewer"
    assert "Code Reviewer" in result["prompt"]
    assert result["trace_id"]
    assert store.get_specialists_for_session("session-load") == ["code-reviewer"]


def test_mcp_explain_selection_returns_receipt(tmp_path: Path) -> None:
    from agency_runtime.core.selector.cache import clear_cache
    from agency_runtime.core.selector.stickiness import clear_session_routing

    clear_cache()
    clear_session_routing()
    store = _seed_store(tmp_path)

    receipt = handle_tool_call(
        "agency.explain_selection",
        {"session_id": "s1", "task": "review code quality", "limit": 5},
        store=store,
    )

    assert receipt["schema_version"] == "agency.selection_explain.v1"
    assert receipt["selected"][0]["slug"] == "code-reviewer"
    assert receipt["signals"]["selection"]["roster_size"] == 1
    conn = store._connect()
    try:
        persisted = conn.execute(
            "SELECT trace_id, session_id FROM routing_decisions WHERE session_id = ?",
            ("s1",),
        ).fetchall()
    finally:
        conn.close()
    assert len(persisted) == 1
    assert dict(persisted[0]) == {
        "trace_id": receipt["routing"]["trace_id"],
        "session_id": "s1",
    }


def test_mcp_preflight_persists_authoritative_routing_trace(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)

    result = handle_tool_call(
        "agency.preflight",
        {"session_id": "preflight-session", "user_message": "Review code quality and security"},
        store=store,
    )

    assert result["context"].startswith("[AGENCY PREFLIGHT]")
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT session_id, query_hash, decision FROM routing_decisions WHERE session_id = ?",
            ("preflight-session",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    persisted = dict(row)
    assert persisted["session_id"] == "preflight-session"
    assert len(persisted["query_hash"]) == 64
    assert "code-reviewer" in persisted["decision"]


def test_mcp_finalize_returns_header_text(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)
    store.record_specialist_loaded("s1", "code-reviewer")

    result = handle_tool_call(
        "agency.finalize",
        {"session_id": "s1", "draft_text": "Done.", "model": "task-general"},
        store=store,
    )

    assert result["action"] == "accept"
    assert result["missing"] == []
    assert "Agency/Agencies loaded: code-reviewer" in result["text"]
    assert "task-general -> unavailable" in result["text"]
    assert result["text"].endswith("Done.")
    conn = store._connect()
    try:
        event = conn.execute(
            "SELECT host, action FROM finalization_events WHERE trace_id = ?",
            ("s1",),
        ).fetchone()
    finally:
        conn.close()
    assert event is not None
    assert dict(event) == {"host": "mcp", "action": "accept"}


def _transcript() -> str:
    messages = [
        "{not-json",
        json.dumps({"jsonrpc": "2.0", "id": 0, "method": "tools/list", "params": {}}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "transcript-test", "version": "1.0"},
                },
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "agency.status", "arguments": {}},
            }
        ),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"name": "agency.preflight", "arguments": {}},
            }
        ),
        json.dumps({"jsonrpc": "2.0", "id": 6, "method": "missing/method", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 4}}),
    ]
    return "\n".join(messages) + "\n"


def _run_transcript(command: list[str], tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
    env = os.environ.copy()
    env["AGENCY_DB_PATH"] = str(tmp_path / "mcp-transcript.db")
    completed = subprocess.run(
        command,
        input=_transcript(),
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
        env=env,
        timeout=30,
        check=False,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]
    return completed, responses


def _assert_transcript(completed: subprocess.CompletedProcess[str], responses: list[dict]) -> None:
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert len(responses) == 8  # Two notifications intentionally have no response.
    assert responses[0]["error"]["code"] == -32700
    assert responses[1] == {
        "jsonrpc": "2.0",
        "id": 0,
        "error": {"code": -32002, "message": "Server not initialized"},
    }
    by_id = {response.get("id"): response for response in responses if response.get("id") is not None}
    assert by_id[1]["result"]["protocolVersion"] == "2025-11-25"
    assert by_id[1]["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert by_id[2]["result"] == {}
    assert "agency.status" in {tool["name"] for tool in by_id[3]["result"]["tools"]}
    call_result = by_id[4]["result"]
    assert call_result["isError"] is False
    assert call_result["structuredContent"]["roster_count"] == 0
    assert json.loads(call_result["content"][0]["text"]) == call_result["structuredContent"]
    assert by_id[5]["result"]["isError"] is True
    assert "missing required argument" in by_id[5]["result"]["structuredContent"]["error"]
    assert by_id[6]["error"]["code"] == -32601


def test_mcp_module_runs_a_real_stdio_json_rpc_transcript(tmp_path: Path) -> None:
    completed, responses = _run_transcript(
        [sys.executable, "-m", "agency_runtime.server.mcp", "--stdio"],
        tmp_path,
    )
    _assert_transcript(completed, responses)


def test_agency_mcp_cli_runs_the_same_stdio_transport(tmp_path: Path) -> None:
    completed, responses = _run_transcript(
        [sys.executable, "-m", "agency_runtime.cli", "mcp", "--db", str(tmp_path / "cli.db")],
        tmp_path,
    )
    _assert_transcript(completed, responses)


def test_mcp_stdio_rejects_oversized_input_without_unbounded_read() -> None:
    source = io.BytesIO(b"x" * (MAX_INPUT_BYTES + 1) + b"\n")
    sink = io.BytesIO()

    status = run_stdio(input_stream=source, output_stream=sink)

    assert status == 1
    response = json.loads(sink.getvalue())
    assert response["error"]["code"] == -32700
    assert "input limit" in response["error"]["message"]
