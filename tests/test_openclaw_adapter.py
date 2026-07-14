"""Tests for host adapter parity across Hermes and Nexus/OpenClaw."""

from __future__ import annotations

from pathlib import Path

from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.store.sqlite import Store


def test_openclaw_message_preflight_records_suggested_delegations(
    monkeypatch, tmp_path: Path
) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)

    def fake_route(session_id: str, user_message: str, catalog, **kwargs):
        return {
            "selected_ids": ["multi-agent-systems-architect"],
            "confidence": 0.95,
            "status": "applied",
            "work_units": {
                "delegate": True,
                "count": 2,
                "confidence": "high",
                "source": "numbered_list",
                "units": ["audit delegation layer", "design eval harness"],
            },
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
        session_id="nexus-session",
    )

    delegations = store.get_delegations_for_session("nexus-session")
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "delegate_task"
    assert delegations[0]["host"] == "openclaw"


def test_openclaw_pre_verify_blocks_open_suggestions(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = OpenClawAdapter(store=store)
    store.record_specialist_loaded("nexus-session", "multi-agent-systems-architect")
    store.record_delegation(
        trace_id="trace-1",
        session_id="nexus-session",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    final_response = "\n".join(
        [
            "Agency/Agencies loaded: multi-agent-systems-architect",
            "Agency/Agencies delegated: none",
            "Skills loaded: agency-specialist-routing",
            "Actual Model selected: task-chunk-planner -> test/model",
            "Why: test",
            "How it shaped outcome: test",
            "",
            "body",
        ]
    )

    result = adapter.pre_verify_handler(
        final_response=final_response,
        session_id="nexus-session",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "DELEGATION OPPORTUNITY" in result["message"]
