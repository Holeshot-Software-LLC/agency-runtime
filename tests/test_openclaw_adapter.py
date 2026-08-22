"""Tests for host adapter parity across Hermes and Nexus/OpenClaw."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.adapters.openclaw.plugin import (
    OpenClawAdapter,
    _authorized_native_skill_read,
)
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


def test_openclaw_generated_plugin_records_terminal_model_calls() -> None:
    source = render_openclaw_index(
        5,
        python_executable="/usr/bin/python3",
        bootstrap_path="/opt/agency/bootstrap.py",
    )

    assert "model_call_ended" in OPENCLAW_REQUIRED_HOOKS
    assert 'api.on("model_call_ended"' in source
    assert 'api.on("subagent_spawned"' in source
    assert 'api.on("subagent_ended"' in source
    assert 'action: "post_api_request"' in source
    assert 'provider.toLowerCase().includes("litellm")' in source
    assert "const requestedModel = modelId(ctx)" in source
    assert "modelGroup: requestedModel" in source
    assert 'resolvedModel: routerBacked ? "" : observedModel' in source


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
