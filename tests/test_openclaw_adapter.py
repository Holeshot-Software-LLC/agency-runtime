"""Tests for host adapter parity across Hermes and Nexus/OpenClaw."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.adapters.openclaw.plugin import (
    OpenClawAdapter,
    _authorized_native_skill_read,
)
from agency_runtime.core.header.contract import fill_header_fields
from agency_runtime.core.installer_contracts import OPENCLAW_REQUIRED_HOOKS
from agency_runtime.core.installer_payload_openclaw import render_openclaw_index
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.store.sqlite import Store


@pytest.mark.skip(
    reason="ADR-0087: needs full inference nomination-delivery flow for delegation recording"
)
def test_openclaw_message_preflight_records_suggested_delegations(
    monkeypatch, tmp_path: Path
) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)

    def fake_route(session_id: str, user_message: str, catalog, **kwargs):
        selected = (
            "code-reviewer" if user_message.casefold().startswith("audit ") else "senior-developer"
        )
        return {
            "selected_ids": [selected],
            "confidence": 0.95,
            "status": "applied",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "work_units": detect_work_units(user_message),
        }

    monkeypatch.setattr(pipeline, "route", fake_route)

    result = adapter.on_message_received(
        "nexus-session",
        "1. audit delegation layer\n2. design eval harness",
        "task-chunk-planner",
    )

    assert result is not None
    assert "[DELEGATION OPPORTUNITY]" in result["context"]
    delegations = store.get_delegations_for_session("nexus-session")
    assert [row["status"] for row in delegations] == ["suggested", "suggested"]
    assert {row["host"] for row in delegations} == {"openclaw"}


def test_openclaw_post_tool_call_records_delegate_task(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    store.record_delegation(
        trace_id="trace-1",
        session_id="nexus-session",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )

    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"goal": "audit delegation layer"},
        result={"agent_id": "worker-1", "run_id": "native-run-1"},
        session_id="nexus-session",
    )

    delegations = store.get_delegations_for_session("nexus-session")
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "delegate_task"
    assert delegations[0]["host"] == "openclaw"
    assert delegations[0]["executed_worker_kind"] == "generic-worker"
    assert delegations[0]["executed_worker_id"] == "worker-1"
    assert delegations[0]["native_run_id"] == "native-run-1"


def test_openclaw_model_call_receipt_is_bound_to_exact_child_trace(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    store.create_run(
        trace_id="child-run-1",
        session_id="agent-main-subagent-child-1",
        host="openclaw",
        metadata={"request_kind": "new_intent"},
    )

    result = node_bridge.handle(
        {
            "action": "post_api_request",
            "sessionId": "agent-main-subagent-child-1",
            "traceId": "child-run-1",
            "requestedModel": "gpt-5-mini",
            "modelGroup": "gpt-5-mini",
            "resolvedProvider": "openai",
            "resolvedModel": "gpt-5-mini-2026-06-01",
            "modelId": "call-1",
            "source": "openclaw-model-call",
            "status": "completed",
        },
        adapter=adapter,
    )

    assert result == {}
    receipt = store.get_model_receipt("child-run-1")
    assert receipt is not None
    assert receipt["session_id"] == "agent-main-subagent-child-1"
    assert receipt["requested_model"] == "gpt-5-mini"
    assert receipt["resolved_provider"] == "openai"
    assert receipt["resolved_model"] == "gpt-5-mini-2026-06-01"
    # Generic host telemetry is deliberately normalized to the bounded host
    # provenance class; it cannot forge LiteLLM callback authority.
    assert receipt["source"] == "host"


def test_openclaw_alias_only_router_hook_does_not_mutate_header_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    store.create_run(
        trace_id="router-turn",
        session_id="router-session",
        host="openclaw",
        metadata={"request_kind": "trivial"},
    )
    before = fill_header_fields(
        {},
        "router-session",
        store,
        "task-general",
        "router-turn",
    )["actual_model_selected"]

    result = node_bridge.handle(
        {
            "action": "post_api_request",
            "sessionId": "router-session",
            "traceId": "router-turn",
            "requestedModel": "task-general",
            "modelGroup": "task-general",
            "resolvedProvider": "",
            "resolvedModel": "",
            "modelId": "call-alias-only",
            "source": "openclaw-litellm-router",
            "status": "completed",
        },
        adapter=adapter,
    )

    after = fill_header_fields(
        {},
        "router-session",
        store,
        "task-general",
        "router-turn",
    )["actual_model_selected"]
    assert result == {}
    assert store.get_model_receipt("router-turn") is None
    assert before == after == "requested execution alias: task-general"


def test_openclaw_generated_plugin_records_terminal_model_calls() -> None:
    source = render_openclaw_index(
        5,
        python_executable="/usr/bin/python3",
        bootstrap_path="/opt/agency/bootstrap.py",
    )

    assert "model_call_ended" in OPENCLAW_REQUIRED_HOOKS
    assert "agent_end" in OPENCLAW_REQUIRED_HOOKS
    assert 'api.on("model_call_ended"' in source
    assert 'api.on("agent_end"' in source
    assert 'api.on("subagent_spawned"' in source
    assert 'api.on("subagent_ended"' in source
    assert 'action: "post_api_request"' in source
    assert 'provider.toLowerCase().includes("litellm")' in source
    assert "const requestedModel = modelId(ctx)" in source
    assert "modelGroup: requestedModel" in source
    assert 'resolvedModel: routerBacked ? "" : observedModel' in source


def test_openclaw_generated_plugin_seals_exact_native_child_completion() -> None:
    source = render_openclaw_index(
        5,
        python_executable="/usr/bin/python3",
        bootstrap_path="/opt/agency/bootstrap.py",
    )

    assert "function nativeChildCompletionRunId" in source
    assert "`announce:v1:${boundedSession}:${boundedRun}`" in source
    assert "function resolveNativeChildCompletionState" in source
    assert 'match.state?.completionDeliveryState !== "pending"' in source
    assert "async function authorizeNativeChildCompletionMessage" in source
    assert 'action: "native_child_completion_prepare"' in source
    assert 'action: "native_child_completion_finalize"' in source
    assert "canonicalOutboundPayload({ text })" in source
    assert "gate?.terminalBound === true" in source
    assert '"child_completion"' in source
    assert "markNativeChildCompletionConsumed(session, authorized.runId)" in source


def test_openclaw_outbound_gate_marks_only_exact_terminal_allowance_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = SimpleNamespace(runtime_enabled=lambda: True, store=object())
    payload = json.dumps({"text": "bounded completion"}, separators=(",", ":"))
    common = {
        "adapter": adapter,
        "session_id": "completion-session",
        "trace_id": "completion-run",
        "final_response": "bounded completion",
        "outbound_payload": payload,
        "model": "litellm/task-general",
    }

    monkeypatch.setattr(
        node_bridge,
        "_exact_outbound_terminal_state",
        lambda *_args, **_kwargs: "completed",
    )
    authoritative = node_bridge._handle_outbound_gate(**common)
    monkeypatch.setattr(
        node_bridge,
        "_exact_outbound_terminal_state",
        lambda *_args, **_kwargs: "unavailable",
    )
    blind = node_bridge._handle_outbound_gate(**common)

    assert authoritative["action"] == "allow"
    assert authoritative["turnId"] == "completion-run"
    assert authoritative["authoritative"] is True
    assert authoritative["terminalBound"] is True
    assert authoritative["terminalStatus"] == "completed"
    assert blind["action"] == "allow"
    assert blind["turnId"] == "completion-run"
    assert "authoritative" not in blind
    assert "terminalBound" not in blind
    assert "terminalStatus" not in blind


def test_openclaw_outbound_gate_marks_only_committed_accept_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = SimpleNamespace(store=object())
    common = {
        "adapter": adapter,
        "decision": {"action": "accept"},
        "digest": "a" * 64,
        "session_id": "completion-session",
        "effective_trace": "completion-run",
        "final_response": "bounded completion",
        "binding": json.dumps({"text": "bounded completion"}),
        "revision": 1,
    }

    monkeypatch.setattr(
        node_bridge,
        "_commit_terminal_outcome",
        lambda *_args, **_kwargs: "committed",
    )
    committed = node_bridge._outbound_evaluated_decision(**common)
    monkeypatch.setattr(
        node_bridge,
        "_commit_terminal_outcome",
        lambda *_args, **_kwargs: "unavailable",
    )
    unavailable = node_bridge._outbound_evaluated_decision(**common)

    assert committed["authoritative"] is True
    assert committed["terminalBound"] is True
    assert committed["terminalStatus"] == "completed"
    assert "authoritative" not in unavailable
    assert "terminalBound" not in unavailable
    assert "terminalStatus" not in unavailable


def test_sessions_spawn_uses_child_session_as_worker_not_runtime_agent(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    store.record_delegation(
        trace_id="parent-run",
        session_id="parent-session",
        host="openclaw",
        work_unit_id="unit-review",
        recommended_agent="code-reviewer",
        status="suggested",
    )

    adapter.post_tool_call_handler(
        tool_name="sessions_spawn",
        args={
            "task": "Review the patch",
            "taskName": "unit-review",
            "agentId": "configured-openclaw-profile",
            "recommended_agent": "code-reviewer",
        },
        result={
            "status": "accepted",
            "agentId": "configured-openclaw-profile",
            "childSessionKey": "agent:main:subagent:child-1",
            "runId": "child-run-1",
        },
        session_id="parent-session",
        trace_id="parent-run",
    )

    event = store.get_delegations("parent-run")[0]
    assert event["recommended_agent"] == "code-reviewer"
    assert event["work_unit_id"] == "unit-review"
    assert event["executed_worker_id"] == "agent:main:subagent:child-1"
    assert event["native_run_id"] == "child-run-1"
    child = store.get_native_child_run(
        host="openclaw",
        session_id="parent-session",
        trace_id="parent-run",
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        work_unit_id="unit-review",
    )
    assert child is not None
    assert child["delegation_event_id"] == event["id"]


def test_openclaw_bridge_prepares_sessions_spawn_against_exact_parent_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core import native_child_install_identity, native_child_staffing

    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="parent-run",
        session_id="parent-session",
        host="openclaw",
        user_message="Review restart safety",
    )
    adapter = OpenClawAdapter(store=store)
    install = object()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        native_child_install_identity,
        "current_managed_host_install_identity",
        lambda host: install if host == "openclaw" else None,
    )

    def staff(_store: object, **kwargs: object) -> SimpleNamespace:
        observed.update(kwargs)
        return SimpleNamespace(
            staffed=True,
            rewritten_task="Review restart safety\n\n[AGENCY INFERENCE TEAM v6]\ncard",
            decision_id="native-child-decision-one",
        )

    monkeypatch.setattr(native_child_staffing, "staff_native_child", staff)

    result = node_bridge.handle(
        {
            "action": "native_child_prepare",
            "sessionId": "parent-session",
            "traceId": "parent-run",
            "launchId": "spawn-call-one",
            "goal": "Review restart safety",
        },
        adapter=adapter,
    )

    assert result == {
        "staffed": True,
        "rewrittenTask": "Review restart safety\n\n[AGENCY INFERENCE TEAM v6]\ncard",
        "decisionId": "native-child-decision-one",
        "runtimeEnabled": True,
    }
    delivery_validator = observed.pop("delivery_validator")
    assert callable(delivery_validator)
    assert delivery_validator("ascii delivery") is True
    assert delivery_validator("😀" * node_bridge.MAX_PREFLIGHT_CONTEXT_CHARS) is False
    assert observed == {
        "host": "openclaw",
        "task": "Review restart safety",
        "parent_session_id": "parent-session",
        "parent_trace_id": "parent-run",
        "launch_id": "spawn-call-one",
        "binding_kind": "launch_id",
        "binding_id": "spawn-call-one",
        "install_identity": install,
        "install_identity_reader": native_child_install_identity.current_managed_host_install_identity,
        "maximum_delivery_bytes": node_bridge.MAX_PREFLIGHT_CONTEXT_CHARS,
    }


def test_openclaw_bridge_binds_real_sessions_spawn_result_to_launch(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="parent-run",
        session_id="parent-session",
        host="openclaw",
        user_message="Review restart safety",
    )
    adapter = OpenClawAdapter(store=store)

    result = node_bridge.handle(
        {
            "action": "native_child_started",
            "sessionId": "parent-session",
            "traceId": "parent-run",
            "launchId": "spawn-call-one",
            "workUnitId": "restart-review",
            "workerId": "agent:main:subagent:child-one",
            "nativeRunId": "child-run-one",
            "goal": "Review restart safety",
        },
        adapter=adapter,
    )

    assert result == {
        "recorded": True,
        "launchBound": True,
        "workUnitId": "restart-review",
    }
    child = store.get_native_child_run(
        host="openclaw",
        session_id="parent-session",
        trace_id="parent-run",
        work_unit_id="restart-review",
        worker_id="agent:main:subagent:child-one",
        native_run_id="child-run-one",
    )
    assert child is not None
    assert child["execution_tool_use_id"] == "spawn-call-one"
    assert child["execution_dispatched_at"] is not None

    ended = node_bridge.handle(
        {
            "action": "native_child_ended",
            "sessionId": "parent-session",
            "traceId": "parent-run",
            "workUnitId": "restart-review",
            "workerId": "agent:main:subagent:child-one",
            "nativeRunId": "child-run-one",
            "outcome": "ok",
        },
        adapter=adapter,
    )
    assert ended == {"recorded": True}


def test_openclaw_bridge_prepares_and_finalizes_completion_against_parent_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="completion-parent-run",
        session_id="completion-parent-session",
        host="openclaw",
    )
    store.record_delegation(
        trace_id="completion-parent-run",
        session_id="completion-parent-session",
        host="openclaw",
        work_unit_id="completion-unit",
        recommended_agent="code-reviewer",
        status="delegated",
        backend="sessions_spawn",
        executed_worker_kind="generic-worker",
        executed_worker_id="completion-child",
        native_run_id="completion-child-run",
    )
    store.record_native_child_started(
        host="openclaw",
        backend="sessions_spawn",
        session_id="completion-parent-session",
        trace_id="completion-parent-run",
        work_unit_id="completion-unit",
        worker_id="completion-child",
        native_run_id="completion-child-run",
    )
    assert store.bind_native_child_launch(
        host="openclaw",
        session_id="completion-parent-session",
        trace_id="completion-parent-run",
        worker_id="completion-child",
        native_run_id="completion-child-run",
        launch_id="completion-launch",
    )
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE runs SET preflight_state = 'ready' WHERE trace_id = 'completion-parent-run'"
        )
        conn.commit()
    finally:
        conn.close()
    adapter = OpenClawAdapter(store=store)
    completion_run = "announce:v1:completion-child:completion-child-run"
    context = (
        "[AGENCY NATIVE CHILD COMPLETION CONTRACT]\n"
        'message(action="send", message=<header+body>)\n'
        "Agency/Agencies loaded: agency-steward\n"
        "Agency/Agencies delegated: code-reviewer\n"
        "Skills loaded: none\n"
        "Actual Model selected: workforce inference: task-agency-router\n"
        "Recruited via: inference\n"
        "Do not emit a natural visible final response or NO_REPLY."
    )
    monkeypatch.setattr(
        node_bridge,
        "_native_child_completion_context",
        lambda *_args, **_kwargs: context,
    )
    common = {
        "sessionId": "completion-parent-session",
        "traceId": completion_run,
        "parentSessionId": "completion-parent-session",
        "parentTraceId": "completion-parent-run",
        "workerId": "completion-child",
        "nativeRunId": "completion-child-run",
        "launchId": "completion-launch",
        "workUnitId": "completion-unit",
        "model": "litellm/task-general",
    }

    prepared = node_bridge.handle(
        {"action": "native_child_completion_prepare", **common},
        adapter=adapter,
    )

    assert prepared["prepared"] is True
    assert prepared["context"] == context
    assert prepared["headerContextHash"] == node_bridge.response_hash(context)
    assert prepared["parentTraceId"] == "completion-parent-run"
    assert store.get_run(completion_run) is None

    observed: dict[str, object] = {}

    def gate(_adapter: object, **kwargs: object) -> dict[str, object]:
        observed.update(kwargs)
        return {
            "action": "allow",
            "authoritative": True,
            "terminalBound": True,
            "terminalStatus": "completed",
            "responseHash": node_bridge.response_hash(str(kwargs["outbound_payload"])),
            "turnId": str(kwargs["trace_id"]),
        }

    monkeypatch.setattr(node_bridge, "_handle_outbound_gate", gate)
    final_text = (
        "Agency/Agencies loaded: agency-steward\n"
        "Agency/Agencies delegated: code-reviewer\n"
        "Skills loaded: none\n"
        "Actual Model selected: workforce inference: task-agency-router\n"
        "Recruited via: inference\n\nBounded child result."
    )
    outbound = json.dumps({"text": final_text}, separators=(",", ":"))
    finalized = node_bridge.handle(
        {
            "action": "native_child_completion_finalize",
            **common,
            "headerContextHash": prepared["headerContextHash"],
            "finalResponse": final_text,
            "outboundPayload": outbound,
        },
        adapter=adapter,
    )

    assert finalized["authoritative"] is True
    assert finalized["turnId"] == "completion-parent-run"
    assert finalized["completionRunId"] == completion_run
    assert observed["session_id"] == "completion-parent-session"
    assert observed["trace_id"] == "completion-parent-run"
    assert store.get_run(completion_run) is None

    rejected = node_bridge.handle(
        {
            "action": "native_child_completion_finalize",
            **common,
            "headerContextHash": "0" * 64,
            "finalResponse": final_text,
            "outboundPayload": outbound,
        },
        adapter=adapter,
    )
    assert rejected["action"] == "replace"


def test_openclaw_bridge_reconciles_native_child_end_after_plugin_restart(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="restart-parent-run",
        session_id="restart-parent-session",
        host="openclaw",
    )
    store.record_delegation(
        trace_id="restart-parent-run",
        session_id="restart-parent-session",
        host="openclaw",
        work_unit_id="restart-review",
        recommended_agent="code-reviewer",
        status="delegated",
        backend="sessions_spawn",
        executed_worker_kind="generic-worker",
        executed_worker_id="restart-child-session",
        native_run_id="restart-child-run",
    )
    store.record_native_child_started(
        host="openclaw",
        backend="sessions_spawn",
        session_id="restart-parent-session",
        trace_id="restart-parent-run",
        work_unit_id="restart-review",
        worker_id="restart-child-session",
        native_run_id="restart-child-run",
    )
    assert store.bind_native_child_launch(
        host="openclaw",
        session_id="restart-parent-session",
        trace_id="restart-parent-run",
        worker_id="restart-child-session",
        native_run_id="restart-child-run",
        launch_id="restart-launch",
    )
    adapter = OpenClawAdapter(store=store)

    missing = node_bridge.handle(
        {
            "action": "native_child_ended",
            "sessionId": "wrong-parent-session",
            "workerId": "restart-child-session",
            "nativeRunId": "restart-child-run",
            "outcome": "ok",
        },
        adapter=adapter,
    )
    reconciled = node_bridge.handle(
        {
            "action": "native_child_ended",
            "sessionId": "restart-parent-session",
            "workerId": "restart-child-session",
            "nativeRunId": "restart-child-run",
            "outcome": "ok",
        },
        adapter=adapter,
    )

    assert missing == {"recorded": False}
    assert reconciled == {"recorded": True}
    child = store.get_native_child_run(
        host="openclaw",
        session_id="restart-parent-session",
        trace_id="restart-parent-run",
        work_unit_id="restart-review",
        worker_id="restart-child-session",
        native_run_id="restart-child-run",
    )
    assert child is not None
    assert child["exit_code"] == 0
    assert child["ended_at"]


def test_openclaw_inventory_authorized_native_read_records_skill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.adapters.openclaw import plugin as openclaw_plugin

    skill_path = "/opt/openclaw/skills/weather/SKILL.md"
    observed: list[dict[str, object]] = []

    def authorize(args: dict[str, object]) -> str:
        observed.append(dict(args))
        return "weather"

    monkeypatch.setattr(
        openclaw_plugin,
        "_authorized_native_skill_read",
        authorize,
        raising=False,
    )
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    adapter.post_tool_call_handler(
        tool_name="read",
        args={"path": skill_path},
        result={"ok": True},
        session_id="openclaw-session",
        trace_id="openclaw-trace",
    )

    assert observed == [{"path": skill_path}]
    assert store.get_skills_for_session("openclaw-session") == ["weather"]


def _native_skill_inventory(path: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "weather",
        "skillKey": "weather",
        "filePath": path,
        "baseDir": os.path.dirname(path),
        "eligible": True,
        "modelVisible": True,
        "disabled": False,
        "blockedByAllowlist": False,
        "blockedByAgentFilter": False,
        "platformIncompatible": False,
    }
    payload.update(overrides)
    return payload


def test_openclaw_native_skill_read_requires_exact_native_inventory() -> None:
    skill_path = "/opt/openclaw/skills/weather/SKILL.md"
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs: object) -> dict[str, object]:
        calls.append((list(command), dict(kwargs)))
        return {
            "returncode": 0,
            "stdout": json.dumps(_native_skill_inventory(skill_path)),
        }

    assert (
        _authorized_native_skill_read(
            {"path": skill_path},
            command_runner=runner,
        )
        == "weather"
    )
    assert [command for command, _kwargs in calls] == [
        ["openclaw", "skills", "info", "weather", "--json"]
    ]
    environment = calls[0][1]["env"]
    assert isinstance(environment, dict)
    assert "OPENCLAW_HOME" in environment
    assert "CODEX_HOME" not in environment
    assert "CLAUDE_CONFIG_DIR" not in environment
    assert "HERMES_HOME" not in environment


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("eligible", False),
        ("modelVisible", False),
        ("disabled", True),
        ("blockedByAllowlist", True),
        ("blockedByAgentFilter", True),
        ("platformIncompatible", True),
    ],
)
def test_openclaw_native_skill_read_rejects_ineligible_inventory(
    field: str,
    value: object,
) -> None:
    skill_path = "/opt/openclaw/skills/weather/SKILL.md"

    def runner(_command: list[str], **_kwargs: object) -> dict[str, object]:
        return {
            "returncode": 0,
            "stdout": json.dumps(_native_skill_inventory(skill_path, **{field: value})),
        }

    assert not _authorized_native_skill_read(
        {"path": skill_path},
        command_runner=runner,
    )


@pytest.mark.parametrize(
    "receipt",
    [
        {"returncode": 1, "stdout": ""},
        {"returncode": 0, "stdout": "{"},
        {
            "returncode": 0,
            "stdout": json.dumps(
                _native_skill_inventory(
                    "/opt/openclaw/skills/other/SKILL.md",
                )
            ),
        },
        {
            "returncode": 0,
            "stdout": json.dumps(
                _native_skill_inventory(
                    "/opt/openclaw/skills/weather/SKILL.md",
                    name="other",
                )
            ),
        },
    ],
)
def test_openclaw_native_skill_read_rejects_unproven_inventory(
    receipt: dict[str, object],
) -> None:
    assert not _authorized_native_skill_read(
        {"path": "/opt/openclaw/skills/weather/SKILL.md"},
        command_runner=lambda _command, **_kwargs: receipt,
    )


@pytest.mark.parametrize(
    "path",
    [
        "/opt/openclaw/skills/weather/README.md",
        "/opt/openclaw/skills/../SKILL.md",
        "skills/weather/SKILL.md",
        "/opt/openclaw/skills/.hidden/SKILL.md",
    ],
)
def test_openclaw_native_skill_read_rejects_non_skill_paths(path: str) -> None:
    def unexpected_runner(_command: list[str], **_kwargs: object) -> object:
        raise AssertionError("non-skill paths must not invoke OpenClaw")

    assert not _authorized_native_skill_read(
        {"path": path},
        command_runner=unexpected_runner,
    )


def test_openclaw_native_skill_read_failure_is_not_recorded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.adapters.openclaw import plugin as openclaw_plugin

    monkeypatch.setattr(
        openclaw_plugin,
        "_authorized_native_skill_read",
        lambda _args: "weather",
    )
    store = Store(tmp_path / "agency.db")
    OpenClawAdapter(store=store).post_tool_call_handler(
        tool_name="read",
        args={"path": "/opt/openclaw/skills/weather/SKILL.md"},
        result={"ok": False},
        session_id="openclaw-session",
        trace_id="openclaw-trace",
    )

    assert store.get_skills_for_session("openclaw-session") == []
