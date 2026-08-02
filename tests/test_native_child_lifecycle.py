"""Native child lifecycle receipts remain exact under callback reordering."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

import pytest

from agency_runtime.adapters.hermes.bridge import handle as handle_hermes_bridge
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.codex_child_tool_evidence import (
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA,
)
from agency_runtime.core.delegation.events import work_unit_id_from_text
from agency_runtime.core.native_child_activation import build_native_child_run_identity
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.store.schema import SCHEMA_VERSION
from agency_runtime.core.store.sqlite import Store

_PARENT_SCOPE = {
    "session_id": "parent-session",
    "trace_id": "parent-run",
    "work_unit_id": "unit-1",
}
_TOOL_EVIDENCE = dict.fromkeys(CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS, 0)
_TOOL_EVIDENCE.update(
    {
        "child_tool_call_count": 1,
        "child_function_tool_call_count": 1,
        "child_apply_patch_tool_call_count": 1,
        "child_completed_tool_call_count": 1,
        "child_tool_output_count": 1,
        "child_patch_apply_success_count": 1,
    }
)


def _delegation(
    store: Store,
    *,
    host: str = "openclaw",
    backend: str = "sessions_spawn",
    worker_id: str = "agent:main:subagent:child-1",
    native_run_id: str = "child-run-1",
    work_unit_id: str = "unit-1",
) -> str:
    return store.record_delegation(
        trace_id="parent-run",
        session_id="parent-session",
        host=host,
        work_unit_id=work_unit_id,
        recommended_agent="code-reviewer",
        status="delegated",
        backend=backend,
        executed_worker_kind="generic-worker",
        executed_worker_id=worker_id,
        native_run_id=native_run_id,
    )


def _agent(slug: str) -> dict[str, object]:
    return next(dict(agent) for agent in BundledRoster() if agent["slug"] == slug)


def test_native_child_start_and_end_update_reciprocal_delegation(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    event_id = _delegation(store)

    started = store.record_native_child_started(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
    )
    ended = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="ok",
    )

    assert started["delegation_event_id"] == event_id
    assert ended["delegation_event_id"] == event_id
    assert ended["exit_code"] == 0
    assert ended["ended_at"]
    assert store.get_delegations("parent-run")[0]["status"] == "completed"


def test_codex_child_execution_dispatch_is_one_use_and_tool_idempotent(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    worker_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    native_run_id = f"codex-agent:{worker_id}"
    _delegation(
        store,
        host="codex",
        backend="spawn_agent",
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        **_PARENT_SCOPE,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    claim = {
        **_PARENT_SCOPE,
        "worker_id": worker_id,
        "native_run_id": native_run_id,
    }

    assert store.claim_codex_native_child_execution(**claim, tool_use_id="followup-1")
    assert store.claim_codex_native_child_execution(**claim, tool_use_id="followup-1")
    assert not store.claim_codex_native_child_execution(**claim, tool_use_id="followup-2")
    assert HookBridge("codex", store=store)._codex_execution_claim_observed(
        session_id="parent-session",
        trace_id="parent-run",
        work_unit_id="unit-1",
        identity=build_native_child_run_identity(
            worker_kind="generic-worker",
            worker_id=worker_id,
            native_run_id=native_run_id,
        ),
    )
    store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        **_PARENT_SCOPE,
        worker_id=worker_id,
        native_run_id=native_run_id,
        outcome="ok",
    )
    assert not store.claim_codex_native_child_execution(
        **claim,
        tool_use_id="followup-1",
    )

    second_worker_id = "019fa6a6-b197-7a83-b3fb-d2c20411f608"
    second_native_run_id = f"codex-agent:{second_worker_id}"
    _delegation(
        store,
        host="codex",
        backend="spawn_agent",
        worker_id=second_worker_id,
        native_run_id=second_native_run_id,
        work_unit_id="unit-2",
    )
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="parent-session",
        trace_id="parent-run",
        work_unit_id="unit-2",
        worker_id=second_worker_id,
        native_run_id=second_native_run_id,
    )
    assert not store.claim_codex_native_child_execution(
        session_id="parent-session",
        trace_id="parent-run",
        work_unit_id="unit-2",
        worker_id=second_worker_id,
        native_run_id=second_native_run_id,
        tool_use_id="followup-1",
    )


def test_codex_child_tool_evidence_is_content_free_immutable_and_readable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    worker_id = "019fa6a6-a197-7a83-b3fb-d2c20411f608"
    native_run_id = f"codex-agent:{worker_id}"
    _delegation(
        store,
        host="codex",
        backend="spawn_agent",
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        **_PARENT_SCOPE,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        **_PARENT_SCOPE,
        worker_id=worker_id,
        native_run_id=native_run_id,
        outcome="ok",
    )

    recorded = store.record_codex_child_tool_evidence(
        **_PARENT_SCOPE,
        child_session_id=worker_id,
        evidence=_TOOL_EVIDENCE,
    )
    replay = store.record_codex_child_tool_evidence(
        **_PARENT_SCOPE,
        child_session_id=worker_id,
        evidence=dict(_TOOL_EVIDENCE),
    )
    child = store.get_native_child_run(
        host="codex",
        **_PARENT_SCOPE,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )

    assert recorded == replay
    assert recorded["schema"] == CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA
    assert recorded["source"] == "persisted_rollout"
    assert recorded["recorded_at"]
    assert recorded["tool_evidence"] == _TOOL_EVIDENCE
    assert child is not None
    assert child["tool_evidence"] == _TOOL_EVIDENCE
    assert b"private-child-prompt" not in path.read_bytes()

    changed = dict(_TOOL_EVIDENCE)
    changed["child_completed_tool_call_count"] = 0
    changed["child_unknown_tool_call_count"] = 1
    with pytest.raises(ValueError, match="conflicts with its worker receipt"):
        store.record_codex_child_tool_evidence(
            **_PARENT_SCOPE,
            child_session_id=worker_id,
            evidence=changed,
        )
    with pytest.raises(ValueError, match="fields were invalid"):
        store.record_codex_child_tool_evidence(
            **_PARENT_SCOPE,
            child_session_id=worker_id,
            evidence={**_TOOL_EVIDENCE, "private-child-prompt": "secret"},
        )
    assert b"private-child-prompt" not in path.read_bytes()


def test_native_child_completion_atomically_records_workforce_assignment(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_agent("code-reviewer"))
    worker = store.get_workforce_worker("code-reviewer", disabled_agents=())
    store.create_run(
        trace_id="parent-run",
        session_id="parent-session",
        host="openclaw",
    )
    event_id = _delegation(store)
    with closing(store._connect()) as conn, conn:
        conn.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, delegation_event_id, created_at, consumed_at) VALUES "
            "('assignment-activation', ?, 'parent-session', 'parent-run', 'unit-1', "
            "'code-reviewer', ?, ?, 'generic-worker', "
            "'agent:main:subagent:child-1', 'child-run-1', ?, "
            "'2026-07-21T00:00:00+00:00', '2026-07-21T00:00:01+00:00')",
            ("a" * 64, worker["current_version"], worker["current_hash"], event_id),
        )
        conn.execute(
            "UPDATE delegation_events SET activation_receipt_id = 'assignment-activation', "
            "retrieved_specialist_slug = 'code-reviewer', "
            "retrieved_specialist_version = ?, retrieved_specialist_prompt_hash = ? "
            "WHERE id = ?",
            (worker["current_version"], worker["current_hash"], event_id),
        )

    ended = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="ok",
    )
    replay = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="ok",
    )

    assert ended["workforce_outcome_id"]
    assert replay["workforce_outcome_id"] == ended["workforce_outcome_id"]
    detail = store.get_workforce_worker_detail("code-reviewer", disabled_agents=())
    assignments = [item for item in detail["outcomes"] if item["event_type"] == "assignment"]
    assert len(assignments) == 1
    assert assignments[0]["outcome"] == "passed"
    assert assignments[0]["activation_receipt_id"] == "assignment-activation"
    assert assignments[0]["evidence_refs"] == {
        "delegation_event_id": event_id,
        "native_worker_run_id": ended["id"],
    }


def test_hermes_official_child_hooks_create_execution_and_terminal_receipts(
    tmp_path: Path,
) -> None:
    goal = "Review the adapter"
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="parent-run",
        session_id="parent-session",
        host="hermes",
        metadata={"request_kind": "new_intent"},
    )
    event_id = store.record_delegation(
        trace_id="parent-run",
        session_id="parent-session",
        host="hermes",
        work_unit_id=work_unit_id_from_text(goal),
        recommended_agent="code-reviewer",
        status="suggested",
        backend="delegate_task",
    )
    adapter = HermesAdapter(store=store)

    assert (
        handle_hermes_bridge(
            {
                "action": "native_child_started",
                "session_id": "parent-session",
                "trace_id": "parent-run",
                "worker_id": "child-1",
                "native_run_id": "hermes-subagent:child-1",
                "goal": goal,
            },
            adapter=adapter,
        )
        is None
    )
    delegated = store.get_delegations("parent-run")[0]
    assert delegated["id"] == event_id
    assert delegated["status"] == "delegated"
    assert delegated["executed_worker_id"] == "child-1"
    assert delegated["native_run_id"] == "hermes-subagent:child-1"

    assert (
        handle_hermes_bridge(
            {
                "action": "native_child_ended",
                "session_id": "parent-session",
                "trace_id": "parent-run",
                "worker_id": "child-1",
                "native_run_id": "hermes-subagent:child-1",
                "outcome": "completed",
            },
            adapter=adapter,
        )
        is None
    )
    assert store.get_delegations("parent-run")[0]["status"] == "completed"


def test_native_child_end_before_tool_receipt_binds_and_replays(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    unbound = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="timeout",
    )
    assert unbound["delegation_event_id"] is None

    event_id = _delegation(store)
    rebound = store.record_native_child_started(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
    )

    assert rebound["delegation_event_id"] == event_id
    event = store.get_delegations("parent-run")[0]
    assert event["status"] == "failed"
    assert event["skip_reason"] == ""

    replay = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="timeout",
    )
    assert replay["exit_code"] == 124


def test_native_child_terminal_conflict_is_rejected(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="ok",
    )

    with pytest.raises(ValueError, match="conflicts"):
        store.record_native_child_ended(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
            outcome="error",
        )


def test_outcome_free_stop_can_late_bind_to_authoritative_completion(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    stopped = store.record_native_child_stopped(
        host="claude",
        backend="delegate_task",
        **_PARENT_SCOPE,
        worker_id="agent-42",
        native_run_id="claude-agent:agent-42",
    )
    assert stopped["ended_at"] is not None
    assert stopped["exit_code"] is None
    assert stopped["outcome"] == "unavailable"

    event_id = _delegation(
        store,
        host="claude",
        backend="delegate_task",
        worker_id="agent-42",
        native_run_id="claude-agent:agent-42",
    )
    completed = store.record_native_child_ended(
        host="claude",
        backend="delegate_task",
        **_PARENT_SCOPE,
        worker_id="agent-42",
        native_run_id="claude-agent:agent-42",
        outcome="ok",
    )

    assert completed["delegation_event_id"] == event_id
    assert completed["exit_code"] == 0
    assert store.get_delegations("parent-run")[0]["status"] == "completed"


def test_reused_native_ids_are_isolated_by_parent_session_and_trace(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    common = {
        "host": "codex",
        "backend": "spawn_agent",
        "worker_id": "worker-1",
        "native_run_id": "codex-agent:worker-1",
    }
    lookup = {key: value for key, value in common.items() if key != "backend"}

    first = store.record_native_child_started(
        **common,
        session_id="session-a",
        trace_id="trace-a",
    )
    second = store.record_native_child_started(
        **common,
        session_id="session-b",
        trace_id="trace-b",
    )

    assert first["id"] != second["id"]
    assert first["session_id"] == "session-a"
    assert second["session_id"] == "session-b"
    assert (
        store.get_native_child_run(
            **lookup,
            session_id="session-a",
            trace_id="trace-a",
        )["id"]
        == first["id"]
    )
    assert (
        store.get_native_child_run(
            **lookup,
            session_id="session-b",
            trace_id="trace-b",
        )["id"]
        == second["id"]
    )


def test_native_child_rejects_oversized_and_invalid_outcome_fields(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError, match="worker_id exceeds the 256-character limit"):
        store.record_native_child_started(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="w" * 257,
            native_run_id="native",
        )
    with pytest.raises(ValueError, match="outcome is invalid"):
        store.record_native_child_ended(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
            outcome="invented-success",
        )


def test_native_child_rejects_ambiguous_delegation_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    _delegation(store, work_unit_id="unit-1")
    _delegation(store, work_unit_id="unit-2")

    with pytest.raises(ValueError, match="matches multiple delegation events"):
        store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            session_id="parent-session",
            trace_id="parent-run",
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
        )


def test_native_child_rejects_tampered_persisted_identity(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    started = store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
    )
    conn = store._connect()
    try:
        conn.execute("UPDATE worker_runs SET backend = 'tampered' WHERE id = ?", (started["id"],))
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="conflicts with its scoped identity"):
        store.record_native_child_started(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
        )


def test_native_child_rejects_work_unit_and_delegation_rebinding(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    common = {
        "host": "openclaw",
        "backend": "sessions_spawn",
        "session_id": "parent-session",
        "trace_id": "parent-run",
        "worker_id": "agent:main:subagent:child-1",
        "native_run_id": "child-run-1",
    }
    first_event = _delegation(store, work_unit_id="unit-1")
    second_event = _delegation(store, work_unit_id="unit-2")
    started = store.record_native_child_started(**common, work_unit_id="unit-1")
    assert started["delegation_event_id"] == first_event

    with pytest.raises(ValueError, match="already bound to another work unit"):
        store.record_native_child_started(**common, work_unit_id="unit-2")

    conn = store._connect()
    try:
        conn.execute("UPDATE worker_runs SET work_unit_id = '' WHERE id = ?", (started["id"],))
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(ValueError, match="already bound to another delegation"):
        store.record_native_child_started(**common, work_unit_id="unit-2")
    assert second_event != first_event


def test_native_child_start_rolls_back_when_postcondition_disappears(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    conn = store._connect()
    try:
        conn.execute(
            "CREATE TRIGGER delete_native_child_after_insert AFTER INSERT ON worker_runs "
            "BEGIN DELETE FROM worker_runs WHERE id = NEW.id; END"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="start postcondition failed"):
        store.record_native_child_started(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
        )


def test_native_child_end_requires_start_and_terminal_postconditions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_store = Store(tmp_path / "missing.db")
    monkeypatch.setattr(
        missing_store,
        "record_native_child_started",
        lambda **_kwargs: {"id": "missing"},
    )
    with pytest.raises(RuntimeError, match="end has no start receipt"):
        missing_store.record_native_child_ended(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
            outcome="ok",
        )

    store = Store(tmp_path / "terminal.db")
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
    )
    conn = store._connect()
    try:
        conn.execute(
            "CREATE TRIGGER delete_native_child_after_exit AFTER UPDATE OF exit_code "
            "ON worker_runs BEGIN DELETE FROM worker_runs WHERE id = NEW.id; END"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="end postcondition failed"):
        store.record_native_child_ended(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
            outcome="ok",
        )


def test_native_child_stop_replays_terminal_outcome_and_checks_postcondition(
    tmp_path: Path,
) -> None:
    replay_store = Store(tmp_path / "replay.db")
    replay_store.record_native_child_ended(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
        outcome="ok",
    )
    replay = replay_store.record_native_child_stopped(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
    )
    assert replay["outcome"] == "ok"

    store = Store(tmp_path / "missing-stop.db")
    store.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
    )
    conn = store._connect()
    try:
        conn.execute(
            "CREATE TRIGGER delete_native_child_after_stop AFTER UPDATE OF ended_at "
            "ON worker_runs BEGIN DELETE FROM worker_runs WHERE id = NEW.id; END"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="stop postcondition failed"):
        store.record_native_child_stopped(
            host="codex",
            backend="spawn_agent",
            session_id="session",
            trace_id="trace",
            worker_id="worker",
            native_run_id="native",
        )


def _replace_worker_runs_with_v27_rows(
    store: Store,
    rows: list[tuple[object, ...]],
) -> None:
    conn = store._connect()
    try:
        conn.execute("DROP TABLE worker_runs")
        conn.execute(
            "CREATE TABLE worker_runs ("
            "id TEXT PRIMARY KEY, delegation_event_id TEXT, backend TEXT NOT NULL, "
            "workdir TEXT, exit_code INTEGER, stdout TEXT, stderr TEXT, "
            "started_at TEXT NOT NULL, ended_at TEXT)"
        )
        conn.executemany(
            "INSERT INTO worker_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (27)")
        conn.commit()
    finally:
        conn.close()


def _migrated_attached_v27_worker_store(
    path: Path,
    *,
    duplicate: bool = False,
    backend: str = "sessions_spawn",
) -> tuple[Store, str]:
    store = Store(path)
    event_id = _delegation(store)
    rows = [
        (
            "legacy-attached-1",
            event_id,
            backend,
            "",
            0,
            "",
            "",
            "then",
            "done",
        )
    ]
    if duplicate:
        rows.append(
            (
                "legacy-attached-2",
                event_id,
                backend,
                "",
                0,
                "",
                "",
                "then",
                "done",
            )
        )
    _replace_worker_runs_with_v27_rows(store, rows)
    return Store(path), event_id


def test_v27_worker_runs_migrate_to_scoped_native_identity(tmp_path: Path) -> None:
    path = tmp_path / "legacy-worker-runs.db"
    store = Store(path)
    _replace_worker_runs_with_v27_rows(
        store,
        [("legacy-run", None, "legacy", "", None, "", "", "then", None)],
    )

    migrated = Store(path)
    conn = migrated._connect()
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(worker_runs)")}
        indexes = {row[1] for row in conn.execute("PRAGMA index_list(worker_runs)")}
        legacy = conn.execute(
            "SELECT session_id, trace_id, work_unit_id, host, worker_id, native_run_id "
            "FROM worker_runs WHERE id = 'legacy-run'"
        ).fetchone()
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
    finally:
        conn.close()

    assert version == SCHEMA_VERSION
    assert {
        "session_id",
        "trace_id",
        "work_unit_id",
        "host",
        "worker_id",
        "native_run_id",
    }.issubset(columns)
    assert {"idx_worker_runs_trace", "idx_worker_runs_native_scope"}.issubset(indexes)
    assert tuple(legacy) == ("", "", "", "", "", "")

    created = migrated.record_native_child_started(
        host="codex",
        backend="spawn_agent",
        session_id="session",
        trace_id="trace",
        worker_id="worker",
        native_run_id="native",
    )
    assert created["id"] != "legacy-run"
    conn = migrated._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM worker_runs").fetchone()[0] == 2
        assert (
            conn.execute("SELECT COUNT(*) FROM worker_runs WHERE id = 'legacy-run'").fetchone()[0]
            == 1
        )
    finally:
        conn.close()


def test_v27_attached_native_child_rekeys_and_replays_same_outcome(tmp_path: Path) -> None:
    store, event_id = _migrated_attached_v27_worker_store(tmp_path / "same.db")

    replay = store.record_native_child_ended(
        host="openclaw",
        backend="sessions_spawn",
        **_PARENT_SCOPE,
        worker_id="agent:main:subagent:child-1",
        native_run_id="child-run-1",
        outcome="ok",
    )

    assert replay["delegation_event_id"] == event_id
    assert replay["id"].startswith("native-child:")
    assert replay["exit_code"] == 0
    assert store.get_delegations("parent-run")[0]["status"] == "completed"
    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM worker_runs").fetchone()[0] == 1
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM worker_runs WHERE id LIKE 'legacy-attached-%'"
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()


def test_v27_attached_native_child_rejects_conflicting_outcome(tmp_path: Path) -> None:
    store, _event_id = _migrated_attached_v27_worker_store(tmp_path / "conflict.db")

    with pytest.raises(ValueError, match="terminal outcome conflicts"):
        store.record_native_child_ended(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
            outcome="error",
        )

    assert store.get_delegations("parent-run")[0]["status"] == "completed"
    conn = store._connect()
    try:
        rows = conn.execute("SELECT id, exit_code FROM worker_runs ORDER BY id").fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["id"].startswith("native-child:")
    assert rows[0]["exit_code"] == 0


def test_v27_duplicate_or_mismatched_attached_workers_fail_closed(tmp_path: Path) -> None:
    duplicate_store, _event_id = _migrated_attached_v27_worker_store(
        tmp_path / "duplicate.db",
        duplicate=True,
    )
    with pytest.raises(ValueError, match="multiple native child receipts"):
        duplicate_store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
        )

    mismatch_store, _event_id = _migrated_attached_v27_worker_store(
        tmp_path / "mismatch.db",
        backend="different-backend",
    )
    with pytest.raises(ValueError, match="conflicts with its scoped identity"):
        mismatch_store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
        )


def test_v27_attached_worker_rejects_work_unit_conflict_and_missing_rekey(
    tmp_path: Path,
) -> None:
    unit_store, _event_id = _migrated_attached_v27_worker_store(tmp_path / "unit.db")
    conn = unit_store._connect()
    try:
        conn.execute(
            "UPDATE worker_runs SET work_unit_id = 'different-unit' WHERE id = 'legacy-attached-1'"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(ValueError, match="conflicts with its work unit"):
        unit_store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
        )

    disappearing_store, _event_id = _migrated_attached_v27_worker_store(
        tmp_path / "disappearing.db"
    )
    conn = disappearing_store._connect()
    try:
        conn.execute(
            "CREATE TRIGGER delete_legacy_native_child_after_rekey AFTER UPDATE OF id "
            "ON worker_runs BEGIN DELETE FROM worker_runs WHERE id = NEW.id; END"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RuntimeError, match="legacy rekey postcondition failed"):
        disappearing_store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            **_PARENT_SCOPE,
            worker_id="agent:main:subagent:child-1",
            native_run_id="child-run-1",
        )
