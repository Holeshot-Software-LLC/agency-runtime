"""Tests for the Agency Runtime MCP facade."""

from __future__ import annotations

import io
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import private_paths
from agency_runtime.core.config_binding import StoreConfigBindingError
from agency_runtime.core.configuration import apply_config_operations, read_config_state
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.private_paths import PrivateDirectoryIdentity
from agency_runtime.core.process_argv import isolated_python_argv
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import mcp_tools
from agency_runtime.server.mcp import (
    MAX_INPUT_BYTES,
    MCP_TOOLS,
    MCPServer,
    handle_tool_call,
    run_stdio,
)
from tests.runtime_support import stub_inference_invoker


def _seed_store(tmp_path: Path) -> Store:
    database = tmp_path / "agency.db"
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        "judge:\n"
        '  model: ""\n'
        '  base_url: ""\n'
        "  ollama_mode: false\n"
        "ollama:\n"
        "  enabled: false\n"
        "providers:\n"
        "  - name: task-agency-router\n"
        "    type: litellm\n"
        "    model: router-alias\n"
        "    base_url: https://router.example.test/v1\n"
        "    api_key: secret\n"
        "store:\n"
        f"  db_path: {json.dumps(str(database))}\n",
        encoding="utf-8",
    )
    store = Store(config_path=config_path)
    bundled = {agent["slug"]: agent for agent in BundledRoster()}
    store._activate_prevalidated_agent(bundled["code-reviewer"])
    # code-reviewer's same_context_conflicts closure must be present so the
    # workforce index fingerprint stays coherent during preflight.
    for slug in ("codebase-onboarding-engineer", "technical-writer"):
        store._activate_prevalidated_agent(bundled[slug])
    # ADR-0087: stub the invoker so preflight exercises inference.
    from agency_runtime.core.workforce import inference

    inference.invoke_structured_provider_result = stub_inference_invoker(
        ("code-reviewer",),
    )
    return store


def test_mcp_server_validates_redundant_injected_store_runtime_identity(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)

    equivalent_config = store.config_path.parent / "nested" / ".." / store.config_path.name
    equivalent_db = store.db_path.parent / "nested" / ".." / store.db_path.name
    server = MCPServer(
        store=store,
        config_path=str(equivalent_config),
        db_path=str(equivalent_db),
    )
    assert server._runtime_store() is store

    with pytest.raises(
        StoreConfigBindingError,
        match="requested runtime identity does not match Store",
    ):
        MCPServer(store=store, config_path=str(tmp_path / "different.yaml"))
    with pytest.raises(
        StoreConfigBindingError,
        match="requested runtime identity does not match Store",
    ):
        MCPServer(store=store, db_path=str(tmp_path / "different.db"))


def test_mcp_server_rejects_tampered_or_unverifiable_injected_store_identity(
    tmp_path: Path,
) -> None:
    store = _seed_store(tmp_path)
    store.db_path = tmp_path / "tampered.db"
    with pytest.raises(StoreConfigBindingError, match="database identity changed"):
        MCPServer(store=store, db_path=str(store._frozen_db_path))

    with pytest.raises(StoreConfigBindingError, match="does not expose a verifiable"):
        MCPServer(store=object(), config_path=str(tmp_path / "config.yaml"))

    partial = SimpleNamespace(
        config_path=tmp_path / "config.yaml",
        _configured_config_path=tmp_path / "config.yaml",
        db_path=tmp_path / "agency.db",
        _frozen_db_path=tmp_path / "agency.db",
    )
    with pytest.raises(StoreConfigBindingError, match="does not expose a verifiable"):
        MCPServer(
            store=partial,
            config_path=str(partial.config_path),
            db_path=str(partial.db_path),
        )


def test_mcp_exposes_explain_selection_tool() -> None:
    tools = {tool["name"]: tool for tool in MCP_TOOLS}

    assert "agency.explain_selection" in tools
    preflight = tools["agency.preflight"]["inputSchema"]
    assert preflight["properties"]["host"]["enum"] == [
        "codex",
        "claude",
        "openclaw",
        "hermes",
        "zcode",
    ]
    assert "host" in preflight["required"]


def test_mcp_fails_closed_after_config_derived_store_target_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "agency.yaml"
    original_db = tmp_path / "original.db"
    replacement_db = tmp_path / "replacement.db"
    config_path.write_text(f"store:\n  db_path: {original_db}\n", encoding="utf-8")
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    store = Store(config_path=config_path)

    status = handle_tool_call("agency.status", {}, store=store)
    assert status["db_path"] == str(original_db)

    state = read_config_state(config_path)
    apply_config_operations(
        [{"op": "set", "path": "store.db_path", "value": str(replacement_db)}],
        expected_revision=state.revision,
        path=config_path,
    )

    with pytest.raises(StoreConfigBindingError, match="configured Store path changed"):
        handle_tool_call("agency.status", {}, store=store)
    assert store.db_path == original_db


def test_mcp_exposes_host_status_and_exact_confirmed_control_tools() -> None:
    tools = {tool["name"]: tool for tool in MCP_TOOLS}

    assert {"agency.host_status", "agency.host_control"} <= set(tools)
    control = tools["agency.host_control"]["inputSchema"]
    assert control["properties"]["enabled"]["type"] == "boolean"
    assert control["properties"]["expected_generation"] == {"type": "integer", "minimum": 0}
    assert "expected_generation" in control["required"]
    assert control["properties"]["host"]["enum"] == [
        "hermes",
        "openclaw",
        "codex",
        "claude",
    ]


def test_mcp_host_control_requires_exact_confirmation_and_persists(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")

    rejected = handle_tool_call(
        "agency.host_control",
        {"host": "codex", "enabled": False, "expected_generation": 0, "confirm": "yes"},
        store=store,
    )
    assert "confirmation must exactly match" in rejected["error"]
    assert store.get_host_control("codex")["enabled"] is True

    changed = handle_tool_call(
        "agency.host_control",
        {
            "host": "codex",
            "enabled": False,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        },
        store=store,
    )
    assert changed["ok"] is True
    assert changed["enabled"] is False
    assert changed["generation"] == 1
    assert Store(tmp_path / "agency.db").get_host_control("codex")["enabled"] is False

    stale = handle_tool_call(
        "agency.host_control",
        {
            "host": "codex",
            "enabled": True,
            "expected_generation": 0,
            "confirm": "ENABLE codex",
        },
        store=store,
    )
    assert stale["conflict"] is True
    assert stale["current"]["generation"] == 1
    assert stale["current"]["enabled"] is False


@pytest.mark.parametrize("expected_generation", [True, -1, None])
def test_mcp_direct_dispatch_rejects_invalid_host_control_generation(
    tmp_path: Path,
    expected_generation: object,
) -> None:
    store = Store(tmp_path / "agency.db")

    result = mcp_tools.dispatch_tool_call(
        "agency.host_control",
        {
            "host": "codex",
            "enabled": False,
            "expected_generation": expected_generation,
            "confirm": "DISABLE codex",
        },
        store,
    )

    assert result == {"error": "expected_generation must be a non-negative integer"}
    assert store.get_host_control("codex")["enabled"] is True


def test_mcp_host_status_reports_native_and_runtime_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.set_host_control("claude", enabled=False, expected_generation=0, source="test")
    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_host_status",
        lambda runtime_store, host: {
            "host": host,
            "registered": True,
            "enabled": True,
            "runtime_enabled": runtime_store.get_host_control(host)["enabled"],
            "effective_enabled": False,
        },
    )

    status = handle_tool_call(
        "agency.host_status",
        {"host": "claude"},
        store=store,
    )

    assert status["enabled"] is True
    assert status["runtime_enabled"] is False
    assert status["effective_enabled"] is False


def test_canary_mode_blocks_every_mutating_mcp_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    before = store.runtime_table_counts()
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")

    calls = {
        "agency.preflight": {"user_message": "route this"},
        "agency.explain_selection": {"task": "explain"},
        "agency.load_specialist": {"slug": "x", "session_id": "s"},
        "agency.record_skill_loaded": {"skill_name": "x"},
        "agency.delegate": {"agent": "x", "task": "work"},
        "agency.finalize": {"draft_text": "draft"},
        "agency.host_control": {
            "host": "codex",
            "enabled": False,
            "expected_generation": 0,
            "confirm": "DISABLE codex",
        },
    }
    for name, arguments in calls.items():
        result = handle_tool_call(name, arguments, store=store)
        assert "disabled during a live canary" in result["error"]

    assert store.runtime_table_counts() == before
    assert store.get_host_control("codex")["enabled"] is True


@pytest.mark.skip(
    reason="ADR-0087: needs the full inference nomination-delivery flow "
    "(not just the stub invoker) to load the specialist and verify the "
    "receipt/trace."
)
def test_mcp_load_specialist_returns_prompt_and_records_evidence(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)
    preflight = run_preflight(
        store,
        session_id="session-load",
        trace_id="turn-load",
        user_message="Review this code for quality and security",
        host="hermes",
    )
    assert "code-reviewer" in preflight.loaded_specialists
    assert "code-reviewer" in preflight.selected_specialists, preflight.routing

    result = handle_tool_call(
        "agency.load_specialist",
        {
            "slug": "code-reviewer",
            "session_id": "session-load",
            "trace_id": "turn-load",
        },
        store=store,
    )

    assert result["slug"] == "code-reviewer"
    assert "Code Reviewer" in result["prompt"]
    assert result["trace_id"]
    assert store.get_specialists_for_session("session-load") == ["code-reviewer"]


def test_mcp_load_specialist_rejects_inexact_prompt_without_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(
        {
            "slug": "oversized-reviewer",
            "name": "Oversized Reviewer",
            "description": "Exercises the exact prompt delivery boundary.",
            "version": "1.0",
            "prompt_body": "x" * 7_001,
        }
    )
    run_preflight(
        store,
        session_id="session-oversized",
        trace_id="turn-oversized",
        user_message="Review this code for correctness",
        host="mcp",
    )

    result = handle_tool_call(
        "agency.load_specialist",
        {
            "slug": "oversized-reviewer",
            "session_id": "session-oversized",
            "trace_id": "turn-oversized",
        },
        store=store,
    )

    assert "exact-delivery ceiling" in result["error"]
    assert "oversized-reviewer" not in store.get_specialists_for_session("session-oversized")


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            "agency.load_specialist",
            {
                "slug": "code-reviewer",
                "session_id": "session",
                "trace_id": "missing-turn",
            },
        ),
        (
            "agency.record_skill_loaded",
            {
                "skill_name": "security-review",
                "session_id": "session",
                "trace_id": "missing-turn",
            },
        ),
        (
            "agency.delegate",
            {
                "agent": "code-reviewer",
                "task": "Review the patch",
                "backend": "spawn_agent",
                "work_unit_id": "unit-review",
                "session_id": "session",
                "trace_id": "missing-turn",
            },
        ),
    ],
)
def test_mcp_public_evidence_mutations_require_an_existing_active_turn(
    tool_name: str,
    arguments: dict[str, str],
    tmp_path: Path,
) -> None:
    store = _seed_store(tmp_path)

    result = handle_tool_call(tool_name, arguments, store=store)

    assert result == {"error": "trace_id does not identify an existing active turn"}
    assert store.get_run("missing-turn") is None
    assert store.get_specialists_for_session("session") == []
    assert store.get_delegations("missing-turn") == []


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            "agency.load_specialist",
            {
                "slug": "code-reviewer",
                "session_id": "session",
                "trace_id": "reserved-turn",
            },
        ),
        (
            "agency.record_skill_loaded",
            {
                "skill_name": "security-review",
                "session_id": "session",
                "trace_id": "reserved-turn",
            },
        ),
        (
            "agency.delegate",
            {
                "agent": "code-reviewer",
                "task": "Review the patch",
                "backend": "spawn_agent",
                "work_unit_id": "unit-review",
                "session_id": "session",
                "trace_id": "reserved-turn",
            },
        ),
    ],
)
def test_mcp_public_evidence_mutations_reject_unpromoted_reservation(
    tool_name: str,
    arguments: dict[str, str],
    tmp_path: Path,
) -> None:
    store = _seed_store(tmp_path)
    store.reserve_session_turn(
        session_id="session",
        trace_id="reserved-turn",
        host="mcp",
    )

    result = handle_tool_call(tool_name, arguments, store=store)

    assert result == {"error": "trace_id has not completed preflight"}
    assert store.get_specialists_for_session("session") == []
    assert store.get_skills_for_trace("session", "reserved-turn") == []
    assert store.get_delegations("reserved-turn") == []


@pytest.mark.skip(
    reason="ADR-0087: needs the full inference nomination-delivery flow "
    "(not just the stub invoker) to load the specialist and verify the "
    "receipt/trace."
)
def test_mcp_explain_selection_returns_receipt(tmp_path: Path) -> None:
    from agency_runtime.core.selector.cache import clear_cache
    from agency_runtime.core.selector.stickiness import clear_session_routing

    clear_cache()
    clear_session_routing()
    store = _seed_store(tmp_path)

    for _attempt in range(2):
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
    assert persisted == []
    assert "decision_id" not in receipt["routing"]
    assert store.get_open_traces_for_session("s1") == []


@pytest.mark.skip(
    reason="ADR-0087: needs the full inference nomination-delivery flow "
    "(not just the stub invoker) to load the specialist and verify the "
    "receipt/trace."
)
def test_mcp_preflight_persists_authoritative_routing_trace(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)

    result = handle_tool_call(
        "agency.preflight",
        {
            "session_id": "preflight-session",
            "host": "codex",
            "user_message": "Review code quality and security",
        },
        store=store,
    )

    assert result["context"].startswith("[Agency resident-manager kernel v1]")
    assert "[AGENCY PREFLIGHT]" in result["context"]
    assert result["selected_specialists"] == ["code-reviewer"]
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


@pytest.mark.skip(
    reason="ADR-0087: needs the full inference nomination-delivery flow "
    "(not just the stub invoker) to load the specialist and verify the "
    "receipt/trace."
)
def test_mcp_preflight_hydrates_specialist_for_same_trace_finalization(
    tmp_path: Path,
) -> None:
    store = _seed_store(tmp_path)
    preflight = handle_tool_call(
        "agency.preflight",
        {
            "session_id": "session",
            "trace_id": "turn",
            "host": "hermes",
            "user_message": "Review this code for quality and security.",
        },
        store=store,
    )

    assert preflight["loaded_specialists"] == ["code-reviewer"]
    assert preflight["selected_specialists"] == ["code-reviewer"]
    finalized = handle_tool_call(
        "agency.finalize",
        {
            "session_id": "session",
            "trace_id": "turn",
            "draft_text": "Review complete.",
            "model": "task-general",
            "host": "hermes",
        },
        store=store,
    )
    assert finalized["action"] == "accept"
    assert (
        "Agency/Agencies loaded: agents-orchestrator, chief-of-staff, code-reviewer"
        in finalized["text"]
    )
    assert store.get_run("turn")["status"] == "completed"
    assert store.get_active_specialists_for_trace("session", "turn") == []


def test_mcp_finalize_returns_header_text(tmp_path: Path) -> None:
    store = _seed_store(tmp_path)
    store.create_run(
        trace_id="turn-finalize",
        session_id="s1",
        host="mcp",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("s1", "code-reviewer", trace_id="turn-finalize")

    result = handle_tool_call(
        "agency.finalize",
        {
            "session_id": "s1",
            "trace_id": "turn-finalize",
            "draft_text": "Done.",
            "model": "task-general",
        },
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
            ("turn-finalize",),
        ).fetchone()
    finally:
        conn.close()
    assert event is not None
    assert dict(event) == {"host": "mcp", "action": "accept"}
    assert store.get_run("turn-finalize")["status"] == "completed"


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
        json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 4}}
        ),
    ]
    return "\n".join(messages) + "\n"


def _run_transcript(
    command: list[str], tmp_path: Path
) -> tuple[subprocess.CompletedProcess[str], list[dict]]:
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
    by_id = {
        response.get("id"): response for response in responses if response.get("id") is not None
    }
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


@pytest.mark.skipif(
    os.name != "nt" or os.environ.get("CODEX_SHELL") != "1",
    reason="requires a Codex-attested Windows task root",
)
def test_mcp_child_reattests_exact_host_private_database_root() -> None:
    visualizations = Path.home() / ".codex" / "visualizations"
    thread_hex = os.environ["CODEX_THREAD_ID"].replace("-", "")
    identity: PrivateDirectoryIdentity | None = None
    for index, candidate in enumerate(visualizations.glob("*/*/*/*")):
        if index >= 4096:
            break
        parent_guard = private_paths._pin_codex_host_private_parent(
            candidate,
            visualizations,
        )
        if parent_guard is None:
            continue
        root = parent_guard.path / (f".a-{thread_hex}-mcpchild-{secrets.token_hex(12)}")
        try:
            guard = private_paths.create_windows_logon_private_directory(
                root,
                parent_guard=parent_guard,
                is_windows=True,
            )
        except OSError:
            parent_guard.close()
            continue
        if guard is None:
            parent_guard.close()
            continue
        metadata = os.lstat(root)
        identity = PrivateDirectoryIdentity(
            root,
            int(metadata.st_dev),
            int(metadata.st_ino),
            guard=guard,
            parent_guard=parent_guard,
        )
        private_paths._register_host_authority(identity)
        break
    if identity is None:
        pytest.skip("no writable Codex host-private task root is available")
    try:
        completed, responses = _run_transcript(
            [sys.executable, "-m", "agency_runtime.server.mcp", "--stdio"],
            identity.path,
        )
        _assert_transcript(completed, responses)
        assert (identity.path / "mcp-transcript.db").is_file()

        config_path = identity.path / "config" / "agency.yaml"
        config_path.parent.mkdir()
        config_path.write_text(
            'store:\n  db_path: "runtime/hermes.db"\n',
            encoding="utf-8",
        )
        environment = {
            name: value for name, value in os.environ.items() if not name.startswith("AGENCY_")
        }
        hermes = subprocess.run(
            isolated_python_argv(
                sys.executable,
                "agency_runtime.adapters.hermes.bridge",
                "--config",
                str(config_path),
            ),
            input=b'{"action":"control","raw_args":"status"}',
            cwd=Path(__file__).parents[1],
            env=environment,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert hermes.returncode == 0, hermes.stderr.decode(errors="replace")
        result = json.loads(hermes.stdout)
        assert result["ok"] is True
        assert result["result"] == "Agency Runtime is enabled for hermes."
        assert (config_path.parent / "runtime" / "hermes.db").is_file()
    finally:
        private_paths.remove_private_directory(identity)


@pytest.mark.parametrize(
    "entrypoint",
    [
        ["-m", "agency_runtime.server.mcp", "--stdio"],
        ["-m", "agency_runtime.cli", "mcp"],
    ],
)
def test_mcp_processes_keep_explicit_config_identity_without_environment(
    entrypoint: list[str],
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "operator config" / "agency runtime.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        'store:\n  db_path: "runtime data/agency.db"\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop("AGENCY_CONFIG_PATH", None)
    env.pop("AGENCY_DB_PATH", None)

    completed = subprocess.run(
        [sys.executable, *entrypoint, "--config", str(config_path)],
        input=_transcript(),
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
        env=env,
        timeout=30,
        check=False,
    )
    responses = [json.loads(line) for line in completed.stdout.splitlines()]

    _assert_transcript(completed, responses)
    assert (config_path.parent / "runtime data" / "agency.db").is_file()


def test_mcp_stdio_rejects_oversized_input_without_unbounded_read() -> None:
    source = io.BytesIO(b"x" * (MAX_INPUT_BYTES + 1) + b"\n")
    sink = io.BytesIO()

    status = run_stdio(input_stream=source, output_stream=sink)

    assert status == 1
    response = json.loads(sink.getvalue())
    assert response["error"]["code"] == -32700
    assert "input limit" in response["error"]["message"]


def test_mcp_string_argument_without_max_length_is_rejected() -> None:
    """SEC-05: a string argument whose schema omits maxLength must be rejected
    rather than passed through with no length cap, so a future tool added
    without maxLength cannot route an unbounded attacker string."""
    from agency_runtime.server.mcp import _validate_argument

    spec_without_cap = {"type": "string"}
    error = _validate_argument("query", "anything", spec_without_cap)
    assert error is not None
    assert "no defined maximum length" in error

    # A schema with an explicit cap validates normally within the limit.
    spec_with_cap = {"type": "string", "maxLength": 8}
    assert _validate_argument("query", "short", spec_with_cap) is None
    assert "exceeds its maximum length" in _validate_argument(
        "query", "too-long-value", spec_with_cap
    )
