"""P1 regressions for correlated, deterministic delegation evidence."""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.delegation.events import (
    mark_delegation_executed,
    mark_delegation_skipped,
    record_suggested_delegations,
    suggested_delegations,
    work_unit_id_from_text,
)
from agency_runtime.core.header.contract import fill_header_fields
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.store.evidence import (
    _dominant_delegation_status,
    _request_fingerprint,
)
from agency_runtime.core.store.sqlite import Store


def test_delegation_identity_helper_edges(tmp_path: Path) -> None:
    assert _request_fingerprint(None) == ""
    assert _request_fingerprint("{broken") == ""
    assert _request_fingerprint("[]") == ""
    assert _request_fingerprint('{"request_fingerprint":7}') == ""
    assert _request_fingerprint('{"request_fingerprint":"abc"}') == "abc"
    assert _dominant_delegation_status(None, None) == "suggested"
    assert _dominant_delegation_status("delegated", "failed") == "failed"
    assert _dominant_delegation_status("failed", "completed") == "failed"

    store = Store(tmp_path / "edges.db")
    assert suggested_delegations(store, "", trace_id="turn") == []
    assert (
        mark_delegation_executed(
            store,
            session_id="",
            host="codex",
            backend="spawn_agent",
            trace_id="turn",
        )
        == 0
    )
    assert (
        mark_delegation_skipped(
            store,
            session_id="session",
            host="codex",
            backend="spawn_agent",
            reason="worker crashed",
            trace_id="",
        )
        == 0
    )

    kwargs = {
        "session_id": "session",
        "host": "codex",
        "backend": "spawn_agent",
        "agent": "code-reviewer",
        "trace_id": "turn",
        "executed_worker_kind": "generic-worker",
        "executed_worker_id": "worker-1",
        "native_run_id": "native-run-1",
    }
    assert mark_delegation_executed(store, **kwargs) == 1
    assert mark_delegation_executed(store, **kwargs) == 0


def test_preflight_requires_both_correlation_inputs(tmp_path: Path) -> None:
    store = Store(tmp_path / "preflight-inputs.db")
    with pytest.raises(ValueError, match="session_id is required"):
        run_preflight(
            store,
            session_id="",
            user_message="Review the runtime.",
            host="codex",
        )
    with pytest.raises(ValueError, match="user_message is required"):
        run_preflight(
            store,
            session_id="session",
            user_message="",
            host="codex",
        )


def test_native_response_id_reconciles_to_planned_task_and_sessions_spawn(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    routing = {
        "trace_id": "turn",
        "selected_ids": ["code-reviewer"],
        "work_units": {
            "delegate": True,
            "count": 2,
            "units": ["audit delegation", "add regression tests"],
        },
        "workforce_unit_bindings": [
            {
                "work_unit_id": work_unit_id_from_text("audit delegation"),
                "selected": ["code-reviewer"],
                "delivery": "delegate",
                "timing": "immediate",
                "depends_on": [],
                "parallelization": "parallel",
                "mutation_scope": "read_only",
                "artifact_kind": "review-report",
                "required_tools": [],
                "required_evidence": ["review-report"],
                "confidence": 1.0,
            },
            {
                "work_unit_id": work_unit_id_from_text("add regression tests"),
                "selected": ["code-reviewer"],
                "delivery": "delegate",
                "timing": "immediate",
                "depends_on": [],
                "parallelization": "parallel",
                "mutation_scope": "workspace_write",
                "artifact_kind": "test-code",
                "required_tools": [],
                "required_evidence": ["test-evidence"],
                "confidence": 1.0,
            },
        ],
    }
    assert (
        record_suggested_delegations(
            store,
            session_id="session",
            host="openclaw",
            routing=routing,
        )
        == 2
    )

    OpenClawAdapter(store=store).post_tool_call_handler(
        tool_name="sessions_spawn",
        args={"agentId": "code-reviewer", "task": "audit delegation"},
        result={
            "runId": "native-run-42",
            "agent_id": "worker-42",
            "status": "completed",
        },
        session_id="session",
        trace_id="turn",
    )

    rows = store.get_delegations("turn")
    assert len(rows) == 2
    executed = next(
        row for row in rows if row["work_unit_id"] == work_unit_id_from_text("audit delegation")
    )
    assert executed["status"] == "delegated"
    assert executed["backend"] == "sessions_spawn"
    assert all(row["work_unit_id"] != "native-run-42" for row in rows)

    # A reordered terminal failure carries the same native response ID. It
    # must update the planned task row, not create contradictory evidence.
    adapter = OpenClawAdapter(store=store)
    adapter.post_tool_call_handler(
        tool_name="sessions_spawn",
        args={"agentId": "code-reviewer", "task": "audit delegation"},
        result={
            "runId": "native-run-42",
            "agent_id": "worker-42",
            "status": "failed",
            "error": "worker crashed",
        },
        session_id="session",
        trace_id="turn",
    )
    adapter.post_tool_call_handler(
        tool_name="sessions_spawn",
        args={"agentId": "code-reviewer", "task": "audit delegation"},
        result={
            "runId": "native-run-42",
            "agent_id": "worker-42",
            "status": "completed",
        },
        session_id="session",
        trace_id="turn",
    )

    rows = store.get_delegations("turn")
    assert len(rows) == 2
    failed = next(
        row for row in rows if row["work_unit_id"] == work_unit_id_from_text("audit delegation")
    )
    assert failed["status"] == "skipped"
    assert failed["skip_reason"] == "worker crashed"
    assert all(row["work_unit_id"] != "native-run-42" for row in rows)


def test_concurrent_execution_callbacks_are_atomically_idempotent(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="turn", session_id="session", host="codex")
    workers = 12
    barrier = Barrier(workers)

    def record() -> int:
        barrier.wait()
        return mark_delegation_executed(
            store,
            session_id="session",
            host="codex",
            backend="spawn_agent",
            agent="code-reviewer",
            goal="audit delegation",
            work_unit_id="unit-audit",
            trace_id="turn",
            executed_worker_kind="generic-worker",
            executed_worker_id="worker-1",
            native_run_id="native-run-1",
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(lambda _index: record(), range(workers)))

    [row] = store.get_delegations("turn")
    assert row["work_unit_id"] == "unit-audit"
    assert row["status"] == "delegated"


def test_failure_is_sticky_and_outweighs_earlier_success_in_header(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    event_id = store.record_delegation(
        trace_id="turn",
        session_id="session",
        host="codex",
        work_unit_id="unit-audit",
        recommended_agent="code-reviewer",
        status="completed",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )

    store.update_delegation(
        event_id,
        status="failed",
        backend="spawn_agent",
        error="worker crashed",
    )
    store.update_delegation(
        event_id,
        status="completed",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-1",
        native_run_id="native-run-1",
    )

    [row] = store.get_delegations("turn")
    assert row["status"] == "failed"
    assert row["error"] == "worker crashed"
    fields = fill_header_fields({}, "session", store, trace_id="turn")
    assert fields["agencies_delegated"] == "none - worker crashed"


def test_v12_migration_collapses_conflicting_delegation_rows(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    store.record_delegation(
        trace_id="turn",
        session_id="session",
        work_unit_id="unit-audit",
        recommended_agent="code-reviewer",
        status="completed",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-2",
        native_run_id="native-run-2",
    )
    store.record_delegation(
        trace_id="turn",
        session_id="session",
        work_unit_id="unit-with-terminal-time",
        recommended_agent="code-reviewer",
        status="completed",
        backend="spawn_agent",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker-3",
        native_run_id="native-run-3",
    )
    duplicate_id = "duplicate-failure"
    worker_id = "worker-for-duplicate"
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP INDEX idx_delegations_trace_work_unit_unique")
        connection.execute(
            "INSERT INTO delegation_events "
            "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
            "status, backend, error, started_at) "
            "VALUES (?, 'turn', 'session', 'codex', 'unit-audit', "
            "'code-reviewer', 'failed', 'spawn_agent', 'execution_failed', ?)",
            (duplicate_id, "2026-07-14T01:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO delegation_events "
            "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
            "status, backend, error, started_at, completed_at) "
            "VALUES ('duplicate-with-time', 'turn', 'session', 'codex', "
            "'unit-with-terminal-time', 'code-reviewer', 'failed', "
            "'spawn_agent', 'execution_failed', ?, ?)",
            ("2026-07-14T02:00:00+00:00", "2026-07-14T02:00:01+00:00"),
        )
        connection.execute(
            "INSERT INTO worker_runs (id, delegation_event_id, backend, started_at) "
            "VALUES (?, ?, 'spawn_agent', '2026-07-14T01:00:00+00:00')",
            (worker_id, duplicate_id),
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (11)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    rows = {row["work_unit_id"]: row for row in migrated.get_delegations("turn")}
    row = rows["unit-audit"]
    assert row["status"] == "failed"
    assert rows["unit-with-terminal-time"]["status"] == "failed"
    connection = sqlite3.connect(path)
    try:
        worker_parent = connection.execute(
            "SELECT delegation_event_id FROM worker_runs WHERE id = ?",
            (worker_id,),
        ).fetchone()
        assert worker_parent == (row["id"],)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO delegation_events "
                "(id, trace_id, work_unit_id, status) "
                "VALUES ('still-duplicate', 'turn', 'unit-audit', 'delegated')"
            )
    finally:
        connection.close()


def test_preflight_trace_retry_requires_same_request_fingerprint(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    message = "Review the delegation implementation and add regression tests."

    first = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="turn",
    )
    second = run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id="turn",
    )

    assert second.trace_id == first.trace_id == "turn"
    connection = sqlite3.connect(store.db_path)
    try:
        (serialized_metadata,) = connection.execute(
            "SELECT metadata FROM runs WHERE trace_id = 'turn'"
        ).fetchone()
    finally:
        connection.close()
    metadata = json.loads(serialized_metadata)
    assert metadata["source"] == "preflight_attempt"
    assert len(metadata["request_fingerprint"]) == 64
    assert message not in serialized_metadata

    with pytest.raises(
        ValueError,
        match="active trace_id belongs to a different preflight request",
    ):
        run_preflight(
            store,
            session_id="session",
            user_message="Implement a different request.",
            host="codex",
            trace_id="turn",
        )


def test_v12_migration_closes_migrated_orphan_parent(tmp_path: Path) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    store.create_run(trace_id="orphan", session_id="session", host="legacy")
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE runs SET status = 'evidence_only', metadata = ? WHERE trace_id = 'orphan'",
            ('{"migrated":true}',),
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (11)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    run = migrated.get_run("orphan")
    assert run is not None
    assert run["status"] == "completed"
    assert run["ended_at"] is not None
    assert migrated.get_open_traces_for_session("session") == []
