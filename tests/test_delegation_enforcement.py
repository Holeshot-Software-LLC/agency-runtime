"""Regression tests for visible delegation enforcement and evals."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.delegation.events import (
    mark_delegation_executed,
    record_suggested_delegations,
    work_unit_id_from_text,
)
from agency_runtime.core.header.contract import fill_header_fields, format_header
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.pipeline import build_routing_context
from agency_runtime.core.store.sqlite import Store


def _valid_header(
    *,
    loaded: str | None = None,
    delegated: str | None = None,
    store: Store | None = None,
    session_id: str = "",
    trace_id: str = "",
) -> str:
    if store is not None:
        fields = fill_header_fields(
            {},
            session_id,
            store,
            "task-chunk-planner",
            trace_id,
        )
        if loaded is not None:
            fields["agencies_loaded"] = loaded
        if delegated is not None:
            fields["agencies_delegated"] = delegated
        return format_header(fields) + "\n\nbody"
    return "\n".join(
        [
            f"Agency/Agencies loaded: {loaded or 'multi-agent-systems-architect'}",
            f"Agency/Agencies delegated: {delegated or 'none'}",
            "Skills loaded: none",
            "Actual Model selected: [planner] task-chunk-planner -> unavailable - no model receipt recorded",
            "Recruited via: deterministic",
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
    assert f"[{work_unit_id_from_text('audit the delegation layer')}]" in context


def test_suggestions_dedupe_within_trace_but_repeat_across_turns(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    base = {
        "selected_ids": ["code-reviewer"],
        "work_units": {
            "delegate": True,
            "count": 2,
            "units": ["audit delegation", "add tests"],
        },
    }

    assert (
        record_suggested_delegations(
            store,
            session_id="session",
            host="test",
            routing={**base, "trace_id": "turn-1"},
        )
        == 2
    )
    assert (
        record_suggested_delegations(
            store,
            session_id="session",
            host="test",
            routing={**base, "trace_id": "turn-1"},
        )
        == 0
    )
    mark_delegation_executed(
        store,
        session_id="session",
        host="test",
        backend="delegate_task",
        trace_id="turn-1",
        work_unit_id=work_unit_id_from_text("audit delegation"),
    )
    assert (
        record_suggested_delegations(
            store,
            session_id="session",
            host="test",
            routing={**base, "trace_id": "turn-2"},
        )
        == 2
    )

    assert len(store.get_delegations("turn-1")) == 2
    assert len(store.get_delegations("turn-2")) == 2


def test_explicit_trace_and_work_unit_correlate_paraphrased_delegate(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    routing = {
        "trace_id": "turn-1",
        "selected_ids": ["code-reviewer"],
        "work_units": {
            "delegate": True,
            "count": 2,
            "units": ["audit delegation", "add tests"],
        },
    }
    record_suggested_delegations(
        store,
        session_id="session",
        host="test",
        routing=routing,
    )

    updated = mark_delegation_executed(
        store,
        session_id="session",
        host="test",
        backend="delegate_task",
        trace_id="turn-1",
        work_unit_id=work_unit_id_from_text("add tests"),
        goal="paraphrased by the host",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )

    assert updated == 1
    rows = store.get_delegations("turn-1")
    assert [row["status"] for row in rows].count("delegated") == 1
    assert [row["status"] for row in rows].count("suggested") == 1


def test_pre_verify_accepts_trivial_turn_with_no_agency_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trivial-turn",
        session_id="trivial-session",
        metadata={"request_kind": "trivial"},
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(
            store=store,
            session_id="trivial-session",
            trace_id="trivial-turn",
        ),
        session_id="trivial-session",
        model="task-chunk-planner",
        attempt=1,
        trace_id="trivial-turn",
    )

    assert result is None


def test_pre_verify_rejects_nontrivial_turn_with_no_loaded_specialist(
    monkeypatch, tmp_path: Path
) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    def fake_route(session_id: str, user_message: str, catalog, **kwargs):
        return {
            "selected_ids": [],
            "confidence": 0.0,
            "status": "no_match",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "work_units": detect_work_units(user_message),
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


@pytest.mark.skip(
    reason="ADR-0087: the monkeypatched fake_route returns selected_ids "
    "but the downstream abstention/delivery path clears them without a "
    "complete unit-agent plan. Needs the full inference nomination flow."
)
def test_pre_llm_call_seeds_roster_and_records_only_authoritative_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core.selector import pipeline

    prompt = "review the routing implementation"

    def fake_route(session_id: str, user_message: str, catalog, **_kwargs):
        assert session_id == "coding-session"
        assert user_message == prompt
        assert catalog
        return {
            "selected_ids": ["code-reviewer"],
            "confidence": 0.95,
            "status": "applied",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "work_units": detect_work_units(user_message),
            "inference_configured": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "unit_assignment_agents": [
                {
                    "slug": "code-reviewer",
                    "work_unit_id": "unit-review",
                    "recommended_agent": "code-reviewer",
                },
            ],
        }

    monkeypatch.setattr(pipeline, "route", fake_route)
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    result = adapter.pre_llm_call_handler(
        "coding-session",
        prompt,
        "task-chunk-planner",
    )

    assert result is not None
    assert result["routing"]["selected_ids"] == ["code-reviewer"]
    assert "code-reviewer" in result["context"]
    assert "senior-developer" not in result["context"]
    assert len(store.get_active_roster_as_catalog()) >= 4
    loaded = store.get_specialists_for_session("coding-session")
    assert loaded == ["code-reviewer"]


@pytest.mark.skip(
    reason="ADR-0087: the monkeypatched fake_route returns selected_ids "
    "but the downstream abstention/delivery path clears them without a "
    "complete unit-agent plan. Needs the full inference nomination flow."
)
def test_pre_llm_call_records_suggested_delegations(monkeypatch, tmp_path: Path) -> None:
    from agency_runtime.core.selector import pipeline

    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    def fake_route(session_id: str, user_message: str, catalog, **kwargs):
        return {
            "selected_ids": ["multi-agent-systems-architect"],
            "confidence": 0.95,
            "status": "applied",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "work_units": detect_work_units(user_message),
            "unit_assignment_agents": [
                {
                    "slug": "multi-agent-systems-architect",
                    "work_unit_id": "unit-audit",
                    "recommended_agent": "multi-agent-systems-architect",
                },
                {
                    "slug": "multi-agent-systems-architect",
                    "work_unit_id": "unit-design",
                    "recommended_agent": "multi-agent-systems-architect",
                },
            ],
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
        result={
            "status": "completed",
            "agent_id": "worker-1",
            "run_id": "native-run-1",
        },
        session_id="session-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "delegate_task"

    fields = fill_header_fields(
        {},
        "session-1",
        store,
        "task-chunk-planner",
        "trace-1",
    )
    assert fields["agencies_delegated"] == (
        "none - executed worker has no validated Agency specialist"
    )


def test_hermes_official_single_task_preserves_suggested_agent(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    goal = "audit the delegation layer"
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id=work_unit_id_from_text(goal),
        recommended_agent="code-reviewer",
        status="suggested",
    )

    HermesAdapter(store=store).post_tool_call_handler(
        tool_name="delegate_task",
        args={"tasks": [{"goal": goal, "context": "review only"}]},
        result={
            "results": [
                {
                    "task_index": 0,
                    "status": "completed",
                    "summary": "reviewed",
                    "agent_id": "worker-1",
                }
            ],
            "run_id": "native-run-1",
            "total_duration_seconds": 1.25,
        },
        session_id="session-1",
        trace_id="trace-1",
    )

    delegations = store.get_delegations("trace-1")
    assert [(row["status"], row["recommended_agent"]) for row in delegations] == [
        ("delegated", "code-reviewer")
    ]


def test_hermes_official_batch_correlates_reordered_results_and_failures(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    goals = ["review the security boundary", "document the operator workflow"]
    agents = ["code-reviewer", "technical-writer"]
    for goal, agent in zip(goals, agents, strict=True):
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=work_unit_id_from_text(goal),
            recommended_agent=agent,
            status="suggested",
        )

    HermesAdapter(store=store).post_tool_call_handler(
        tool_name="delegate_task",
        args={"tasks": [{"goal": goal, "context": "bounded"} for goal in goals]},
        result={
            "results": [
                {
                    "task_index": 1,
                    "status": "failed",
                    "error": "documentation worker unavailable",
                },
                {
                    "task_index": 0,
                    "status": "completed",
                    "summary": "reviewed",
                    "agent_id": "worker-1",
                },
            ],
            "total_duration_seconds": 2.5,
            "run_id": "native-run-1",
        },
        session_id="session-1",
        trace_id="trace-1",
    )

    delegations = {row["work_unit_id"]: row for row in store.get_delegations("trace-1")}
    reviewed = delegations[work_unit_id_from_text(goals[0])]
    documented = delegations[work_unit_id_from_text(goals[1])]
    assert (reviewed["status"], reviewed["recommended_agent"]) == (
        "delegated",
        "code-reviewer",
    )
    assert (documented["status"], documented["recommended_agent"]) == (
        "skipped",
        "technical-writer",
    )
    assert documented["skip_reason"] == "backend_unavailable"
    fields = fill_header_fields({}, "session-1", store, "task-chunk-planner", "trace-1")
    assert fields["agencies_delegated"] == (
        "none - executed worker has no validated Agency specialist"
    )


def test_hermes_official_background_batch_inherits_top_level_role(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    goals = ["review the API", "audit the UI"]
    for goal in goals:
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=work_unit_id_from_text(goal),
            recommended_agent="code-reviewer",
            status="suggested",
        )

    HermesAdapter(store=store).post_tool_call_handler(
        tool_name="delegate_task",
        args={
            "tasks": [{"goal": goal, "context": "review only"} for goal in goals],
            "role": "code-reviewer",
            "background": True,
        },
        result={
            "results": [
                {
                    "task_index": index,
                    "status": "dispatched",
                    "agent_id": f"worker-{index}",
                }
                for index in range(len(goals))
            ],
            "total_duration_seconds": 0.01,
            "run_id": "native-run-1",
        },
        session_id="session-1",
        trace_id="trace-1",
    )

    rows = store.get_delegations("trace-1")
    assert [(row["status"], row["recommended_agent"]) for row in rows] == [
        ("delegated", "code-reviewer"),
        ("delegated", "code-reviewer"),
    ]
    fields = fill_header_fields({}, "session-1", store, "task-general", "trace-1")
    assert fields["agencies_delegated"] == (
        "none - executed worker has no validated Agency specialist"
    )


def test_agency_agents_delegate_records_visible_delegation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="agency_agents_delegate",
        args={"agent": "software-architect", "task": "review the delegation design"},
        result={
            "status": "completed",
            "agent_id": "worker-1",
            "run_id": "native-run-1",
        },
        session_id="session-1",
        trace_id="trace-1",
    )

    delegations = store.get_delegations_for_session("session-1")
    assert len(delegations) == 1
    assert delegations[0]["recommended_agent"] == "software-architect"
    assert delegations[0]["status"] == "delegated"
    assert delegations[0]["backend"] == "agency_agents_delegate"
    assert delegations[0]["executed_worker_kind"] == "generic-worker"
    assert delegations[0]["executed_worker_id"] == "worker-1"
    assert delegations[0]["native_run_id"] == "native-run-1"


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
    fields = fill_header_fields(
        {},
        "session-1",
        store,
        "task-chunk-planner",
        "trace-1",
    )
    assert fields["agencies_delegated"] == "none - delegate_task requires a parent agent context."


def test_agency_agents_delegate_nested_success_false_records_skipped_blocker(
    tmp_path: Path,
) -> None:
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
    fields = fill_header_fields(
        {},
        "session-1",
        store,
        "task-chunk-planner",
        "trace-1",
    )
    assert fields["agencies_delegated"] == "none - delegate depth limit reached"


@pytest.mark.parametrize(
    "blocker",
    [
        "delegate_task unavailable",
        "host delegate backend is unavailable",
    ],
)
def test_pre_verify_accepts_recorded_delegation_blocker(blocker: str, tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded(
        "session-1",
        "multi-agent-systems-architect",
        trace_id="trace-1",
    )
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="skipped",
        backend="delegate_task",
        skip_reason=blocker,
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(
            delegated=f"none - {blocker}",
            store=store,
            session_id="session-1",
            trace_id="trace-1",
        ),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
        trace_id="trace-1",
    )

    assert result is None


def test_pre_verify_still_rejects_bare_none_delegated(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded(
        "session-1",
        "multi-agent-systems-architect",
        trace_id="trace-1",
    )
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(
            delegated="none",
            store=store,
            session_id="session-1",
            trace_id="trace-1",
        ),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
        trace_id="trace-1",
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "delegate_task" in result["message"]


def test_pre_verify_rejects_generated_no_delegation_explanation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded(
        "session-1",
        "multi-agent-systems-architect",
        trace_id="trace-1",
    )
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="multi-agent-systems-architect",
        status="suggested",
    )
    adapter = HermesAdapter(store=store)

    result = adapter.pre_verify_handler(
        _valid_header(
            delegated="none - delegation suggested but not executed",
            store=store,
            session_id="session-1",
            trace_id="trace-1",
        ),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
        trace_id="trace-1",
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "concrete blocker" in result["message"]


def test_pre_verify_accepts_after_delegate_task_execution(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded(
        "session-1",
        "multi-agent-systems-architect",
        trace_id="trace-1",
    )
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
        result={
            "status": "completed",
            "agent_id": "worker-1",
            "run_id": "native-run-1",
        },
        session_id="session-1",
    )

    result = adapter.pre_verify_handler(
        _valid_header(
            store=store,
            session_id="session-1",
            trace_id="trace-1",
        ),
        session_id="session-1",
        model="task-chunk-planner",
        attempt=1,
        trace_id="trace-1",
    )

    assert result is None
