"""Completed execution must not erase the subject of an ordinary follow-up."""

from __future__ import annotations

import pytest

from agency_runtime.core import preflight
from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent


def _completed(**changes: object) -> TurnState:
    return TurnState.from_mapping(
        {
            "state_known": True,
            "previous_trace_id": "review",
            "previous_status": "completed",
            "previous_turn_kind": "new_intent",
            **changes,
        }
    )


@pytest.mark.parametrize("message", ["go for it", "GO FOR IT!", "go ahead", "do it", "yes"])
def test_completed_followup_requires_fresh_correlated_staffing(message: str) -> None:
    decision = classify_turn_intent(message, _completed())

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "review"
    assert decision.selection_required
    assert decision.reroute_required
    assert decision.execution_decision_required
    assert "completed_task_context" in decision.reason_codes


def test_completed_revision_requires_fresh_correlated_staffing() -> None:
    decision = classify_turn_intent("make it shorter", _completed())

    assert decision.turn_kind == "revision"
    assert decision.continuation_of == "review"
    assert decision.reroute_required


@pytest.mark.parametrize("status", ["missing", "stale", "ambiguous", "corrupt"])
def test_untrusted_completed_state_cannot_supply_correlation(status: str) -> None:
    decision = classify_turn_intent("go for it", _completed(state_status=status))

    assert decision.turn_kind == "new_intent"
    assert not decision.continuation_of
    assert decision.selection_required
    assert decision.reroute_required


@pytest.mark.parametrize("status", ["preflight_failed", "failed", "interrupted"])
def test_failed_terminal_state_is_not_completed_context(status: str) -> None:
    decision = classify_turn_intent("go for it", _completed(previous_status=status))

    assert not decision.continuation_of
    assert decision.reroute_required


@pytest.mark.parametrize("message", ["Review the database schema", "Implement a Go HTTP server"])
def test_explicit_new_request_does_not_inherit_completed_subject(message: str) -> None:
    decision = classify_turn_intent(message, _completed())

    assert decision.turn_kind == "new_intent"
    assert not decision.continuation_of
    assert decision.reroute_required


@pytest.mark.parametrize("message", ["thanks", "hello", "agency status"])
def test_nonwork_turn_does_not_restart_completed_execution(message: str) -> None:
    decision = classify_turn_intent(message, _completed())

    assert not decision.continuation_of
    assert not decision.execution_decision_required


def test_real_preflight_passes_completed_subject_to_fresh_route(tmp_path, monkeypatch) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        session_id="sample",
        trace_id="review",
        host="codex",
        metadata={"turn_kind": "new_intent", "selection_required": True},
    )
    with store._connect() as connection:
        connection.execute("UPDATE runs SET status = 'completed' WHERE trace_id = 'review'")

    captured: dict[str, object] = {}

    class ReachedFreshRoute(Exception):
        pass

    def inspect_request(*_args, **kwargs):
        captured.update(kwargs)
        raise ReachedFreshRoute

    def reject_replay(**_kwargs):
        raise AssertionError("completed specialist assignments must never be replayed")

    monkeypatch.setattr(pipeline, "build_route_request", inspect_request)
    monkeypatch.setattr(store, "resolve_durable_continuation", reject_replay)
    with pytest.raises(ReachedFreshRoute):
        preflight.run_preflight(
            store,
            session_id="sample",
            trace_id="followup",
            host="codex",
            user_message="go for it",
        )

    context = captured["turn_routing_context"]
    assert context["source_trace_id"] == "review"
    assert context["source_status"] == "completed"
    assert set(context) == {
        "context_version",
        "source_trace_id",
        "source_status",
        "source_turn_kind",
        "specialists",
        "workforce_unit_descriptors",
        "workforce_subject_hints",
    }
