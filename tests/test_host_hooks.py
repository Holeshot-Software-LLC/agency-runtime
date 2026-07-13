"""Native Codex and Claude Code hook bridge contracts."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from agency_runtime.adapters.hooks import (
    MAX_HOOK_INPUT_BYTES,
    HookBridge,
    _write_output,
    run_hook_stdio,
)
from agency_runtime.core.store.sqlite import Store


class FakeStore:
    def __init__(self) -> None:
        self.finalizations: list[dict[str, Any]] = []

    def record_finalization(self, **kwargs: Any) -> None:
        self.finalizations.append(kwargs)


class FakeAdapter:
    def __init__(self) -> None:
        self.preflight_calls: list[dict[str, Any]] = []
        self.tool_calls: list[dict[str, Any]] = []
        self.verify_calls: list[dict[str, Any]] = []
        self.verify_result: dict[str, Any] | None = None

    def pre_llm_call_handler(self, **kwargs: Any) -> dict[str, str]:
        self.preflight_calls.append(kwargs)
        return {"context": "Use the security reviewer."}

    def post_tool_call_handler(self, **kwargs: Any) -> None:
        self.tool_calls.append(kwargs)

    def pre_verify_handler(self, final_response: str, **kwargs: Any) -> dict[str, Any] | None:
        self.verify_calls.append({"final_response": final_response, **kwargs})
        return self.verify_result


def test_codex_user_prompt_maps_to_native_additional_context() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("codex", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "model": "gpt-5.6-codex",
            "prompt": "Review the authentication flow",
        }
    )

    assert result == {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "Use the security reviewer.",
        }
    }
    assert adapter.preflight_calls == [
        {
            "session_id": "session-1",
            "user_message": "Review the authentication flow",
            "model": "gpt-5.6-codex",
            "trace_id": "turn-1",
        }
    ]


def test_realistic_prompt_to_stop_sequence_uses_one_turn_trace(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("codex", store=store)
    turn_id = "turn-correlated-1"

    prompt = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-correlated",
            "turn_id": turn_id,
            "model": "gpt-5.6-codex",
            "prompt": "Review the authentication architecture and deployment controls.",
        }
    )
    stopped = bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session-correlated",
            "turn_id": turn_id,
            "model": "gpt-5.6-codex",
            "stop_hook_active": False,
            "last_assistant_message": "Draft without the required header.",
        }
    )

    assert prompt["hookSpecificOutput"]["additionalContext"]
    assert stopped["decision"] == "block"
    activity = store.recent_runtime_activity(limit=20)
    assert activity["routing"][0]["trace_id"] == turn_id
    assert activity["finalizations"][0]["trace_id"] == turn_id


def test_missing_turn_id_uses_only_the_unambiguous_open_routing_trace(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("claude", store=store)

    bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "shared-session",
            "prompt": "Review the authentication architecture.",
        }
    )
    bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "shared-session",
            "stop_hook_active": False,
            "last_assistant_message": "Draft.",
        }
    )

    activity = store.recent_runtime_activity(limit=20)
    assert activity["routing"]
    routing_trace = activity["routing"][0]["trace_id"]
    assert routing_trace != "shared-session"
    assert activity["finalizations"][0]["trace_id"] == routing_trace


def test_missing_turn_id_stays_uncorrelated_when_open_turns_are_ambiguous(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("claude", store=store)
    for trace_id, query_hash in (("turn-a", "a" * 64), ("turn-b", "b" * 64)):
        store.record_routing_decision(
            trace_id=trace_id,
            session_id="shared-session",
            query_hash=query_hash,
            context_fingerprint="c" * 64,
            decision={"status": "applied", "selected_ids": []},
        )

    bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "shared-session",
            "stop_hook_active": False,
            "last_assistant_message": "Draft.",
        }
    )

    assert store.recent_runtime_activity(limit=20)["finalizations"] == []


def test_stop_continuation_prompt_is_not_routed_as_a_new_user_request() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("codex", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session-1",
            "turn_id": "turn-continued",
            "model": "gpt-5.6-codex",
            "prompt": "AGENCY HEADER INVALID: rewrite the evidence fields.",
        }
    )

    assert result == {}
    assert adapter.preflight_calls == []


def test_codex_post_tool_preserves_all_correlation_fields() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("codex", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    result = bridge.handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "session-2",
            "turn_id": "turn-8",
            "model": "gpt-5.6-codex",
            "tool_name": "mcp__agency__agency_agents_delegate",
            "tool_use_id": "call-9",
            "tool_input": {
                "agent": "security-reviewer",
                "task": "Audit auth",
                "workUnitId": "unit-auth",
            },
            "tool_response": {"ok": True},
        }
    )

    assert result == {}
    call = adapter.tool_calls[0]
    assert call["tool_name"] == "agency_agents_delegate"
    assert call["session_id"] == "session-2"
    assert call["trace_id"] == "turn-8"
    assert call["turn_id"] == "turn-8"
    assert call["work_unit_id"] == "unit-auth"
    assert call["model"] == "gpt-5.6-codex"
    assert call["tool_use_id"] == "call-9"


def test_claude_agent_tool_maps_to_delegation_and_agent_work_unit() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("claude", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    bridge.handle(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "claude-session",
            "tool_name": "Agent",
            "tool_use_id": "toolu-1",
            "tool_input": {
                "subagent_type": "security-reviewer",
                "prompt": "Audit authentication",
            },
            "tool_response": {
                "agentId": "agent-42",
                "resolvedModel": "claude-sonnet-5",
                "status": "completed",
            },
        }
    )

    call = adapter.tool_calls[0]
    assert call["tool_name"] == "delegate_task"
    assert call["args"]["agent"] == "security-reviewer"
    assert call["args"]["goal"] == "Audit authentication"
    assert call["args"]["work_unit_id"] == "agent-42"
    assert call["work_unit_id"] == "agent-42"
    assert call["trace_id"] == "toolu-1"


def test_claude_failed_delegation_is_forwarded_as_failure_evidence() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("claude", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    bridge.handle(
        {
            "hook_event_name": "PostToolUseFailure",
            "session_id": "claude-session",
            "tool_name": "Agent",
            "tool_use_id": "toolu-failed",
            "tool_input": {"subagent_type": "reviewer", "prompt": "Review"},
            "error": "worker timed out",
            "is_interrupt": False,
        }
    )

    call = adapter.tool_calls[0]
    assert call["tool_name"] == "delegate_task"
    assert call["result"]["status"] == "failed"
    assert call["result"]["error"] == "worker timed out"


def test_stop_verification_uses_host_continuation_shape_and_turn_trace() -> None:
    adapter = FakeAdapter()
    adapter.verify_result = {
        "action": "continue",
        "message": "Correct the evidence header.",
    }
    store = FakeStore()
    bridge = HookBridge("codex", store=store, adapter=adapter)  # type: ignore[arg-type]

    result = bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session-stop",
            "turn_id": "turn-stop",
            "model": "gpt-5.6-codex",
            "stop_hook_active": False,
            "last_assistant_message": "Draft response",
        }
    )

    assert result == {"decision": "block", "reason": "Correct the evidence header."}
    assert adapter.verify_calls[0]["session_id"] == "session-stop"
    assert adapter.verify_calls[0]["model"] == "gpt-5.6-codex"
    assert store.finalizations[0]["trace_id"] == "turn-stop"
    assert store.finalizations[0]["host"] == "codex"
    assert store.finalizations[0]["action"] == "continue"


def test_stop_hook_active_prevents_an_infinite_continuation_loop() -> None:
    adapter = FakeAdapter()
    bridge = HookBridge("claude", store=FakeStore(), adapter=adapter)  # type: ignore[arg-type]

    result = bridge.handle(
        {
            "hook_event_name": "Stop",
            "session_id": "session-stop",
            "stop_hook_active": True,
            "last_assistant_message": "Still incomplete",
        }
    )

    assert result == {}
    assert adapter.verify_calls == []


def _run_hook(host: str, db_path: Path, payload: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "agency_runtime.cli",
            "hook",
            host,
            "--db",
            str(db_path),
        ],
        input=payload,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
        timeout=30,
        check=False,
    )


def test_agency_hook_codex_runs_as_an_actual_stdin_process(tmp_path: Path) -> None:
    db_path = tmp_path / "codex-hook.db"
    store = Store(db_path)
    store.activate_agent({"slug": "agents-orchestrator", "name": "Agents Orchestrator"})
    store.activate_agent({"slug": "chief-of-staff", "name": "Chief of Staff"})
    event = json.dumps(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "real-codex",
            "turn_id": "turn-1",
            "model": "gpt-5.6-codex",
            "prompt": "ping",
        }
    )

    completed = _run_hook("codex", db_path, event)

    assert completed.returncode == 0
    assert completed.stderr == ""
    output = json.loads(completed.stdout)
    assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert (
        "agents-orchestrator, chief-of-staff" in output["hookSpecificOutput"]["additionalContext"]
    )


def test_agency_hook_claude_records_real_tool_evidence_from_stdin(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "claude-hook.db"
    event = json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "session_id": "real-claude",
            "tool_name": "Skill",
            "tool_input": {"skill": "security-review"},
            "tool_response": {"success": True},
            "tool_use_id": "toolu-skill",
        }
    )

    completed = _run_hook("claude", db_path, event)

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {}
    assert Store(db_path).get_skills_for_session("real-claude") == ["security-review"]


def test_hook_boundary_fails_open_with_valid_json_for_bad_input(tmp_path: Path) -> None:
    completed = _run_hook("codex", tmp_path / "bad-hook.db", "{not-json")

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == {}
    assert "host operation continues" in completed.stderr


def test_hook_boundary_bounds_input_and_output() -> None:
    source = io.BytesIO(b"x" * (MAX_HOOK_INPUT_BYTES + 1))
    sink = io.BytesIO()
    errors = io.StringIO()

    status = run_hook_stdio(
        "codex",
        input_stream=source,
        output_stream=sink,
        error_stream=errors,
    )

    assert status == 0
    assert json.loads(sink.getvalue()) == {}
    assert "size limit" in errors.getvalue()


def test_hook_boundary_fails_open_on_duplicate_json_fields() -> None:
    source = io.BytesIO(b'{"action":"before","action":"after"}')
    sink = io.BytesIO()
    errors = io.StringIO()

    status = run_hook_stdio(
        "codex",
        input_stream=source,
        output_stream=sink,
        error_stream=errors,
    )

    assert status == 0
    assert json.loads(sink.getvalue()) == {}
    assert "duplicate object key" in errors.getvalue()


def test_hook_boundary_never_emits_nonfinite_json() -> None:
    sink = io.BytesIO()

    _write_output(sink, {"value": float("nan")})

    assert sink.getvalue() == b"{}\n"
