"""Regression tests for authoritative runtime evidence."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.core.delegation.events import work_unit_id_from_text
from agency_runtime.core.header.contract import fill_header_fields, finalize_header, format_header
from agency_runtime.core.store.sqlite import Store


def _response(fields: dict[str, str]) -> str:
    return f"{format_header(fields)}\n\nbody"


@pytest.mark.parametrize(
    ("tool_name", "args", "result"),
    [
        ("skill_view", {"name": "graphify"}, {"success": False, "message": "skill not found"}),
        (
            "agency_agents_load",
            {"agent": "software-architect"},
            {"isError": True, "content": [{"type": "text", "text": "agent unavailable"}]},
        ),
    ],
)
def test_failed_load_tool_results_do_not_create_success_evidence(
    tool_name: str,
    args: dict[str, str],
    result: dict[str, object],
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name=tool_name,
        args=args,
        result=result,
        session_id="session-1",
    )

    assert store.get_skills_for_session("session-1") == []
    assert store.get_specialists_for_session("session-1") == []


def test_failed_delegate_correlates_explicit_work_unit_and_records_only_failure(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    for unit_id in ("unit-first", "unit-second"):
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=unit_id,
            recommended_agent="software-architect",
            status="suggested",
        )
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={
            "work_unit_id": "unit-second",
            "agent": "software-architect",
            "task": "review the design",
        },
        result={"status": "failed", "error": "worker crashed"},
        session_id="session-1",
    )

    rows = {row["work_unit_id"]: row for row in store.get_delegations_for_session("session-1")}
    assert rows["unit-first"]["status"] == "suggested"
    assert rows["unit-second"]["status"] == "skipped"
    assert rows["unit-second"]["skip_reason"] == "worker crashed"
    assert store.get_specialists_for_session("session-1") == []


def test_delegate_correlates_by_task_instead_of_first_suggestion(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    tasks = ("audit the installer", "review the evidence contract")
    for task in tasks:
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=work_unit_id_from_text(task),
            recommended_agent="software-architect",
            status="suggested",
        )
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"task": tasks[1]},
        result={"success": True, "agent_id": "worker-1", "run_id": "native-run-1"},
        session_id="session-1",
    )

    rows = {row["work_unit_id"]: row for row in store.get_delegations_for_session("session-1")}
    assert rows[work_unit_id_from_text(tasks[0])]["status"] == "suggested"
    assert rows[work_unit_id_from_text(tasks[1])]["status"] == "delegated"


def test_delegate_correlates_by_unique_agent(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    for unit_id, agent in (("unit-first", "code-reviewer"), ("unit-second", "software-architect")):
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=unit_id,
            recommended_agent=agent,
            status="suggested",
        )
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="delegate_async",
        args={"agent": "software-architect"},
        result={"ok": True, "agent_id": "worker-1", "run_id": "native-run-1"},
        session_id="session-1",
    )

    rows = {row["work_unit_id"]: row for row in store.get_delegations_for_session("session-1")}
    assert rows["unit-first"]["status"] == "suggested"
    assert rows["unit-second"]["status"] == "delegated"


def test_ambiguous_delegate_does_not_mutate_arbitrary_suggestion(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    for unit_id in ("unit-first", "unit-second"):
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=unit_id,
            recommended_agent="software-architect",
            status="suggested",
        )
    adapter = HermesAdapter(store=store)

    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"agent": "software-architect"},
        result={"success": True, "agent_id": "worker-1", "run_id": "native-run-1"},
        session_id="session-1",
    )

    rows = store.get_delegations_for_session("session-1")
    by_work_unit = {row["work_unit_id"]: row for row in rows}
    assert by_work_unit["unit-first"]["status"] == "suggested"
    assert by_work_unit["unit-second"]["status"] == "suggested"
    fallback = [row for row in rows if row["work_unit_id"] not in {"unit-first", "unit-second"}]
    assert len(rows) == 3
    assert len(fallback) == 1
    assert fallback[0]["status"] == "delegated"
    assert fallback[0]["work_unit_id"] == work_unit_id_from_text("software-architect")


def test_delegation_queries_preserve_insertion_order_when_timestamps_tie(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        Store,
        "_now",
        staticmethod(lambda: "2026-07-13T22:25:00+00:00"),
    )
    store = Store(tmp_path / "agency.db")
    events = [
        ("unit-first", "suggested", "code-reviewer"),
        ("unit-second", "suggested", "software-architect"),
        ("unit-third", "delegated", "technical-writer"),
        ("unit-fourth", "delegated", "senior-developer"),
    ]
    for work_unit_id, status, agent in events:
        store.record_delegation(
            trace_id="trace-1",
            session_id="session-1",
            work_unit_id=work_unit_id,
            recommended_agent=agent,
            status=status,
            backend="test-backend" if status == "delegated" else "",
            executed_worker_kind="generic-worker" if status == "delegated" else "",
            executed_worker_id="worker-1" if status == "delegated" else "",
            native_run_id="native-run-1" if status == "delegated" else "",
        )

    expected = [work_unit_id for work_unit_id, _status, _agent in events]
    assert [row["work_unit_id"] for row in store.get_delegations("trace-1")] == expected
    assert [
        row["work_unit_id"] for row in store.get_delegations_for_session("session-1")
    ] == expected
    assert [
        row["work_unit_id"]
        for row in store.get_delegations_for_session(
            "session-1",
            statuses=("suggested",),
        )
    ] == expected[:2]
    assert (
        fill_header_fields({}, "session-1", store, trace_id="trace-1")["agencies_delegated"]
        == "none - executed worker has no validated Agency specialist"
    )


def test_header_fill_and_finalization_overwrite_spoofed_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_specialist_loaded("session-1", "code-reviewer", trace_id="trace-1")
    store.record_skill_loaded("session-1", "repo-audit", trace_id="trace-1")
    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        work_unit_id="unit-1",
        recommended_agent="code-reviewer",
        status="delegated",
        backend="delegate_task",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )
    store.record_model_receipt(
        trace_id="trace-1",
        session_id="session-1",
        host="hermes",
        requested_model="task-general",
        resolved_provider="provider",
        resolved_model="actual-model",
        source="host",
        status="success",
    )
    spoofed = {
        "agencies_loaded": "invented-agent",
        "agencies_delegated": "invented-agent via imaginary-backend",
        "skills_loaded": "fake-admin-skill",
        "actual_model_selected": "premium-provider/fabricated-model",
    }

    filled = fill_header_fields(
        spoofed,
        "session-1",
        store,
        "task-general",
        "trace-1",
    )
    assert filled["agencies_loaded"] == "code-reviewer"
    assert (
        filled["agencies_delegated"] == "none - executed worker has no validated Agency specialist"
    )
    assert filled["skills_loaded"] == "repo-audit"
    assert filled["actual_model_selected"] == (
        "parent task: host-selected (not observable to Agency); "
        "observed execution receipt: [general] task-general -> provider/actual-model (host)"
    )

    finalized = finalize_header(
        _response(spoofed),
        "session-1",
        store,
        "task-general",
        "trace-1",
    )
    assert "Agency/Agencies loaded: code-reviewer\n" in finalized
    assert (
        "Agency/Agencies delegated: none - executed worker has no validated Agency specialist\n"
    ) in finalized
    assert "Skills loaded: repo-audit\n" in finalized
    assert (
        "Actual Model selected: parent task: host-selected (not observable to Agency); "
        "observed execution receipt: [general] task-general -> provider/actual-model (host)\n"
        in finalized
    )
    assert "invented-agent" not in finalized
    assert "fabricated-model" not in finalized
    assert "fake-admin-skill" not in finalized


def test_pre_verify_rejects_spoofed_evidence_on_later_attempt(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        host="hermes",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("session-1", "code-reviewer", trace_id="trace-1")
    store.record_skill_loaded("session-1", "repo-audit", trace_id="trace-1")
    adapter = HermesAdapter(store=store)
    spoofed = {
        "agencies_loaded": "code-reviewer, invented-agent",
        "agencies_delegated": "invented-agent via delegate_task",
        "skills_loaded": "fake-admin-skill",
        "actual_model_selected": "provider/fabricated-model",
        "recruited_via": "inference",
    }

    result = adapter.pre_verify_handler(
        _response(spoofed),
        session_id="session-1",
        model="task-general",
        attempt=2,
        trace_id="trace-1",
    )

    assert result is not None
    assert result["action"] == "continue"
    assert "DOES NOT MATCH RECORDED EVIDENCE" in result["message"]
    assert "Agency/Agencies loaded: code-reviewer" in result["message"]
    assert "Skills loaded: repo-audit" in result["message"]
    assert (
        "Actual Model selected: parent task: host-selected (not observable to Agency); "
        "requested execution alias: task-general; "
        "specialist: launch model not evidenced by this receipt" in result["message"]
    )


def test_pre_verify_accepts_exact_authoritative_evidence_on_later_attempt(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        host="hermes",
        metadata={"request_kind": "nontrivial"},
    )
    store.record_specialist_loaded("session-1", "code-reviewer", trace_id="trace-1")
    adapter = HermesAdapter(store=store)
    fields = fill_header_fields(
        {"skills_loaded": "none"},
        "session-1",
        store,
        "task-general",
        "trace-1",
    )

    result = adapter.pre_verify_handler(
        _response(fields),
        session_id="session-1",
        model="task-general",
        attempt=3,
        trace_id="trace-1",
    )

    assert result is None


def test_delegation_identifiers_are_bounded_at_store_ingress(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    event_id = store.record_delegation(
        trace_id="turn",
        session_id="session",
        host="h" * 1_000,
        work_unit_id="unit-" + ("w" * 1_000),
        recommended_agent="🔥" * 20_000,
        backend="b" * 1_000,
        status="completed",
        executed_worker_kind="k" * 1_000,
        executed_worker_id="i" * 1_000,
        native_run_id="n" * 1_000,
    )

    row = next(item for item in store.get_delegations("turn") if item["id"] == event_id)
    assert len(row["host"]) == 64
    assert len(row["work_unit_id"]) == 160
    assert len(row["recommended_agent"]) == 128
    assert len(row["backend"]) == 128
    assert len(row["executed_worker_kind"]) == 64
    assert len(row["executed_worker_id"]) == 256
    assert len(row["native_run_id"]) == 256
    with pytest.raises(ValueError, match="unsupported delegation status"):
        store.update_delegation(event_id, status="model-controlled-status")
