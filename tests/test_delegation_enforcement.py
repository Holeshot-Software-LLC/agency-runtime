"""Regression tests for visible delegation enforcement and evals."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.header.contract import fill_header_fields
from agency_runtime.core.selector.pipeline import build_routing_context
from agency_runtime.core.store.sqlite import Store


def _valid_header(*, loaded: str = "multi-agent-systems-architect", delegated: str = "none") -> str:
    return "\n".join(
        [
            f"Agency/Agencies loaded: {loaded}",
            f"Agency/Agencies delegated: {delegated}",
            "Skills loaded: agency-specialist-routing",
            "Actual Model selected: task-chunk-planner -> test/model",
            "Why: test",
            "How it shaped outcome: test",
            "",
            "body",
        ]
    )


def test_build_routing_context_surfaces_delegation_even_without_specialist_match() -> None:
    routing = {
        "selected_ids": [],
        "confidence": 0.0,
        "status": "no_catalog",
        "work_units": {
            "delegate": True,
            "count": 2,
            "confidence": "high",
            "source": "numbered_list",
            "units": ["audit the delegation layer", "add eval coverage"],
        },
    }

    context = build_routing_context(routing)

    assert "[AGENCY PREFLIGHT] No high-confidence specialist match" in context
    assert "[DELEGATION OPPORTUNITY] 2 independent work units" in context
    assert "audit the delegation layer" in context


def test_pre_verify_accepts_trivial_turn_with_no_agency_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(loaded="none", delegated="none"),
        session_id="trivial-session",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is None


def test_pre_verify_rejects_nontrivial_turn_with_no_loaded_specialist(monkeypatch, tmp_path: Path) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    def fake_route(session_id: str, user_message: str, catalog, **kwargs):
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "no_match",
            "work_units": {"delegate": False, "count": 1},
        }

    monkeypatch.setattr(pipeline, "route", fake_route)
    adapter.pre_llm_call_handler(
        "nontrivial-session",
        "Please review this implementation",
        "task-chunk-planner",
    )

    result = adapter.pre_verify_handler(
        _valid_header(loaded="none", delegated="none"),
        session_id="nontrivial-session",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "Agency/Agencies loaded" in result["message"]


def test_pre_llm_call_seeds_starter_roster_and_records_default_specialists(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    result = adapter.pre_llm_call_handler(
        "coding-session",
        "fix the routing bug and add tests",
        "task-chunk-planner",
    )

    assert result is not None
    assert "senior-developer" in result["context"]
    assert "code-reviewer" in result["context"]
    assert len(store.get_active_roster_as_catalog()) >= 4
    loaded = store.get_specialists_for_session("coding-session")
    assert "senior-developer" in loaded
    assert "code-reviewer" in loaded


def test_pre_llm_call_records_suggested_delegations(monkeypatch, tmp_path: Path) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

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

    result = adapter.pre_llm_call_handler(
        "session-1",
        "1. audit delegation layer\n2. design eval harness",
        "task-chunk-planner",
    )

    assert result is not None
    assert "[DELEGATION OPPORTUNITY]" in result["context"]
    delegations = store.get_delegations_for_session("session-1")
    assert [row["status"] for row in delegations] == ["suggested", "suggested"]
    assert [row["recommended_agent"] for row in delegations] == [
        "multi-agent-systems-architect",
        "multi-agent-systems-architect",
    ]


def test_delegate_task_marks_suggested_delegation_executed_and_header(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"goal": "audit the delegation layer"},
        session_id="session-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "delegate_task"

    fields = fill_header_fields({}, "session-1", store, "task-chunk-planner")
    assert fields["agencies_delegated"] == "multi-agent-systems-architect via delegate_task"


def test_agency_agents_delegate_records_visible_delegation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="agency_agents_delegate",
        args={"agent": "software-architect", "task": "review the delegation design"},
        session_id="session-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert len(delegations) == 1
    assert delegations[0]["recommended_agent"] == "software-architect"
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "agency_agents_delegate"


def test_agency_agents_delegate_nested_failure_records_skipped_blocker(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="software-architect",
        status="suggested",
    )

    adapter.post_tool_call_handler(
        tool_name="agency_agents_delegate",
        args={"agent": "software-architect", "task": "review the delegation design"},
        result=(
            '{"success": true, "delegated": true, '
            '"result": "{\\"error\\": \\"delegate_task requires a parent agent context.\\"}"}'
        ),
        session_id="session-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert len(delegations) == 1
    assert delegations[0]["recommended_agent"] == "software-architect"
    assert delegations[0]["status"] == "skipped"
    assert delegations[0]["backend"] == "agency_agents_delegate"
    assert delegations[0]["skip_reason"] == "delegate_task requires a parent agent context."
    fields = fill_header_fields({}, "session-1", store, "task-chunk-planner")
    assert fields["agencies_delegated"] == "none - delegate_task requires a parent agent context."


def test_agency_agents_delegate_nested_success_false_records_skipped_blocker(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="software-architect",
        status="suggested",
    )

    adapter.post_tool_call_handler(
        tool_name="agency_agents_delegate",
        args={"agent": "software-architect", "task": "review the delegation design"},
        result=(
            '{"success": true, "delegated": true, '
            '"result": "{\\"success\\": false, \\"delegated\\": false, '
            '\\"message\\": \\"delegate depth limit reached\\"}"}'
        ),
        session_id="session-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert len(delegations) == 1
    assert delegations[0]["status"] == "skipped"
    assert delegations[0]["backend"] == "agency_agents_delegate"
    assert delegations[0]["skip_reason"] == "delegate depth limit reached"
    fields = fill_header_fields({}, "session-1", store, "task-chunk-planner")
    assert fields["agencies_delegated"] == "none - delegate depth limit reached"


@pytest.mark.parametrize(
    "delegated_header",
    [
        "none - delegate_task unavailable",
        "none; blocked because host delegate backend is unavailable",
    ],
)
def test_pre_verify_accepts_explicit_delegation_blocker(delegated_header: str, tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session-1", "multi-agent-systems-architect")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(delegated=delegated_header),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is None


def test_pre_verify_still_rejects_bare_none_delegated(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session-1", "multi-agent-systems-architect")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(delegated="none"),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "delegate_task" in result["message"]


def test_pre_verify_rejects_generated_no_delegation_explanation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session-1", "multi-agent-systems-architect")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(delegated="none - delegation suggested but not executed"),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "concrete blocker" in result["message"]


def test_pre_verify_accepts_after_delegate_task_execution(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session-1", "multi-agent-systems-architect")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)
    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"goal": "audit the delegation layer"},
        session_id="session-1",
    )

    result = adapter.pre_verify_handler(
        _valid_header(delegated="multi-agent-systems-architect via delegate_task"),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
    )

    assert result is None
