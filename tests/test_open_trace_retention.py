"""Retention leases for abandoned open turn graphs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
from typing import Any

import pytest

from agency_runtime.core.runtime_control import RuntimeControlSnapshot
from agency_runtime.core.store import resident_binding as resident_binding_store
from agency_runtime.core.store.schema import RUNTIME_DELETE_ORDER
from agency_runtime.core.store.sqlite import Store

_OLD = "2000-01-01T00:00:00+00:00"
_FUTURE = "2100-01-01T00:00:00+00:00"


@pytest.fixture(autouse=True)
def _stable_materialized_master_control(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = RuntimeControlSnapshot(
        schema_version=1,
        enabled=True,
        generation=0,
        updated_at="2026-07-18T00:00:00Z",
        source="retention-test",
        materialized=True,
    )
    monkeypatch.setattr(
        resident_binding_store,
        "read_effective_runtime_control_snapshot",
        lambda **_kwargs: snapshot,
    )


def _seed_open_graph(store: Store, *, status: str) -> None:
    store.set_host_control(
        "claude",
        enabled=False,
        expected_generation=0,
        source="retention-test",
    )
    store.set_host_control(
        "claude",
        enabled=True,
        expected_generation=1,
        source="retention-test",
    )
    if status == "active":
        store.create_run(trace_id="trace", session_id="session")
    store.record_model_receipt(
        trace_id="trace",
        session_id="session",
        host="test",
    )
    assert store.get_run("trace")["status"] == status
    store.record_skill_loaded("session", "repo-audit", trace_id="trace")
    store.record_specialist_loaded("session", "reviewer", trace_id="trace")
    delegation_id = store.record_delegation(
        trace_id="trace",
        session_id="session",
        host="test",
        work_unit_id="unit",
        recommended_agent="reviewer",
        status="delegated",
        backend="test",
        executed_worker_kind="generic-worker",
        executed_worker_id="worker",
        native_run_id="test:run",
    )
    store.record_finalization(
        trace_id="trace",
        host="test",
        action="continue",
        missing=["response"],
    )
    store.record_routing_decision(
        trace_id="trace",
        session_id="session",
        query_hash="a" * 64,
        context_fingerprint="b" * 64,
        decision={"status": "selected", "selected_ids": ["reviewer"]},
    )
    resident_binding = store.plan_resident_manager_binding(
        session_id="session",
        host="claude",
    )
    connection = store._connect()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO worker_runs "
            "(id, delegation_event_id, backend, started_at, ended_at) "
            "VALUES ('worker', ?, 'test', ?, ?)",
            (delegation_id, _OLD, _OLD),
        )
        connection.execute(
            "INSERT INTO delegation_activation_receipts "
            "(id, token_hash, session_id, trace_id, work_unit_id, specialist_slug, "
            "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
            "native_run_id, created_at, consumed_at, delegation_event_id) "
            "VALUES ('activation', ?, 'session', 'trace', 'unit', 'reviewer', "
            "'1.0.0', ?, 'generic-worker', 'worker', 'test:run', ?, ?, ?)",
            ("c" * 64, "d" * 64, _OLD, _OLD, delegation_id),
        )
        connection.execute(
            "UPDATE specialists_loaded SET activation_receipt_id = 'activation' "
            "WHERE trace_id = 'trace'"
        )
        connection.execute(
            "UPDATE delegation_events SET activation_receipt_id = 'activation', "
            "executed_worker_kind = 'generic-worker', executed_worker_id = 'worker', "
            "native_run_id = 'test:run', "
            "retrieved_specialist_slug = 'reviewer', "
            "retrieved_specialist_version = '1.0.0', "
            "retrieved_specialist_prompt_hash = ? WHERE trace_id = 'trace'",
            ("d" * 64,),
        )
        connection.execute(
            "UPDATE runs SET started_at = ?, ended_at = NULL WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.execute(
            "UPDATE model_receipts SET started_at = ?, ended_at = ? WHERE trace_id = 'trace'",
            (_OLD, _OLD),
        )
        connection.execute(
            "UPDATE skills_loaded SET loaded_at = ? WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.execute(
            "UPDATE specialists_loaded SET loaded_at = ?, expired_at = NULL "
            "WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.execute(
            "UPDATE delegation_events SET started_at = ?, completed_at = NULL "
            "WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.execute(
            "UPDATE finalization_events SET created_at = ? WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.execute(
            "UPDATE routing_decisions SET created_at = ? WHERE trace_id = 'trace'",
            (_OLD,),
        )
        assert store._commit_resident_manager_binding(
            connection,
            session_id="session",
            trace_id="trace",
            binding=resident_binding,
        )
        connection.execute(
            "UPDATE resident_manager_bindings SET bound_at = ?, updated_at = ? "
            "WHERE session_id = 'session' AND host = 'claude'",
            (_OLD, _OLD),
        )
        connection.execute(
            "INSERT INTO child_routing_cache "
            "(cache_key, decision, expires_at, created_at) VALUES (?, '{}', ?, ?)",
            ("e" * 64, 4_102_444_800.0, _OLD),
        )
        connection.execute(
            "INSERT INTO child_routing_usage "
            "(parent_trace_id, parent_session_id, inference_calls, updated_at) "
            "VALUES ('trace', 'session', 1, ?)",
            (_OLD,),
        )
        connection.execute(
            "INSERT INTO child_routing_leases "
            "(cache_key, parent_trace_id, owner_token, expires_at, created_at) "
            "VALUES (?, 'trace', 'lease-token', ?, ?)",
            ("e" * 64, 4_102_444_800.0, _OLD),
        )
        connection.execute(
            "INSERT INTO native_child_parent_scopes "
            "(id, token_hash, host, parent_session_id, parent_trace_id, work_unit_id, "
            "worker_kind, worker_id, native_run_id, child_session_id, child_trace_id, "
            "issued_unix, expires_unix, created_at, consumed_at, consumed_unix) "
            "VALUES ('scope', ?, 'claude', 'session', 'trace', 'unit', "
            "'generic-worker', 'scope-worker', 'claude-agent:scope-worker', "
            "'claude-child:scope-worker', '', 1, 601, ?, NULL, NULL)",
            ("9" * 64, _OLD),
        )
        connection.execute(
            "INSERT INTO agent_workers "
            "(worker_id, agent_slug, display_name, origin, employment_class, standing, "
            "current_agent_version_id, current_version, current_hash, revision, "
            "created_at, updated_at) VALUES "
            "('workforce-worker', 'reviewer', 'Reviewer', 'upstream', 'employee', "
            "'active', 'version-id', '1.0.0', ?, 0, ?, ?)",
            ("d" * 64, _OLD, _OLD),
        )
        connection.execute(
            "INSERT INTO agent_performance_events "
            "(id, idempotency_key, worker_id, version, version_hash, session_id, trace_id, "
            "work_unit_id, activation_receipt_id, event_type, outcome, score, evidence_hash, "
            "evidence_refs, created_at) VALUES "
            "('performance', ?, 'workforce-worker', '1.0.0', ?, 'session', 'trace', "
            "'unit', 'activation', 'acceptance', 'passed', 1.0, ?, '{}', ?)",
            ("f" * 64, "d" * 64, "a" * 64, _OLD),
        )
        # Store-clock ingestion activity, not caller-owned semantic timestamps,
        # is the sole stale-open lease authority. Backdate it only after every
        # child mutation so the fixture represents an abandoned graph.
        connection.execute(
            "UPDATE runs SET last_activity_at = ? WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.commit()
    finally:
        connection.close()


def _assert_full_graph(store: Store, *, status: str) -> None:
    assert store.get_run("trace")["status"] == status
    assert store.get_skills_for_trace("session", "trace") == ["repo-audit"]
    connection = store._connect()
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in RUNTIME_DELETE_ORDER
        }
    finally:
        connection.close()
    assert counts == dict.fromkeys(RUNTIME_DELETE_ORDER, 1)


@pytest.mark.parametrize("status", ["active", "evidence_only"])
@pytest.mark.parametrize("dry_run", [False, True], ids=["delete", "dry-run"])
def test_keep_last_never_retires_open_turn_graph(
    tmp_path: Path,
    status: str,
    dry_run: bool,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status=status)

    report = store.trim_runtime_tables(
        keep_last=0,
        dry_run=dry_run,
        vacuum=False,
    )

    assert report["retired_open_runs"] == 0
    for table in RUNTIME_DELETE_ORDER:
        assert report["tables"][table]["deleted"] == 0
        assert report["remaining_tables"][table] == 1
    _assert_full_graph(store, status=status)


@pytest.mark.parametrize("status", ["active", "evidence_only"])
@pytest.mark.parametrize("dry_run", [False, True], ids=["delete", "dry-run"])
def test_age_retention_retires_stale_open_turn_graph(
    tmp_path: Path,
    status: str,
    dry_run: bool,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status=status)

    report = store.trim_runtime_tables(
        older_than_days=1,
        dry_run=dry_run,
        vacuum=False,
    )

    assert report["retired_open_runs"] == 1
    for table in RUNTIME_DELETE_ORDER:
        assert report["tables"][table]["deleted"] == 1
        assert report["remaining_tables"][table] == int(dry_run)
    if dry_run:
        _assert_full_graph(store, status=status)
    else:
        assert store.get_run("trace") is None


def test_null_legacy_child_activity_falls_back_to_stale_parent_start(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status="active")
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE model_receipts SET started_at = NULL, ended_at = NULL WHERE trace_id = 'trace'"
        )
        connection.execute(
            "UPDATE delegation_events SET started_at = NULL, completed_at = NULL "
            "WHERE trace_id = 'trace'"
        )
        connection.execute(
            "UPDATE runs SET last_activity_at = ? WHERE trace_id = 'trace'",
            (_OLD,),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(
        older_than_days=1,
        dry_run=False,
        vacuum=False,
    )

    assert report["retired_open_runs"] == 1
    assert store.get_run("trace") is None


@pytest.mark.parametrize("status", ["active", "evidence_only"])
@pytest.mark.parametrize("fresh_table", ["routing_decisions", "worker_runs"])
def test_fresh_child_activity_preserves_open_turn_graph(
    tmp_path: Path,
    status: str,
    fresh_table: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status=status)
    connection = store._connect()
    try:
        column = "created_at" if fresh_table == "routing_decisions" else "ended_at"
        connection.execute(
            f"UPDATE {fresh_table} SET {column} = ?",  # nosec B608
            (_FUTURE,),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(
        older_than_days=1,
        dry_run=False,
        vacuum=False,
    )

    assert report["retired_open_runs"] == 0
    for table in RUNTIME_DELETE_ORDER:
        assert report["tables"][table]["deleted"] == 0
        assert report["remaining_tables"][table] == 1
    _assert_full_graph(store, status=status)


@pytest.mark.parametrize("status", ["active", "evidence_only"])
@pytest.mark.parametrize("dry_run", [False, True], ids=["retain", "dry-run"])
def test_age_and_keep_last_retires_but_keeps_graph(
    tmp_path: Path,
    status: str,
    dry_run: bool,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status=status)

    report = store.trim_runtime_tables(
        older_than_days=1,
        keep_last=1,
        dry_run=dry_run,
        vacuum=False,
    )

    assert report["retired_open_runs"] == 1
    for table in RUNTIME_DELETE_ORDER:
        assert report["tables"][table]["deleted"] == 0
        assert report["remaining_tables"][table] == 1
    expected_status = status if dry_run else "retention_expired"
    assert store.get_run("trace")["status"] == expected_status
    connection = store._connect()
    try:
        specialist = connection.execute(
            "SELECT expired_at FROM specialists_loaded WHERE trace_id = 'trace'"
        ).fetchone()
    finally:
        connection.close()
    assert (specialist["expired_at"] is None) is dry_run


class _BeginSignalConnection:
    def __init__(self, connection: Any, attempt: Event):
        self._connection = connection
        self._attempt = attempt

    def execute(self, sql: str, *args: Any) -> Any:
        if sql == "BEGIN IMMEDIATE":
            self._attempt.set()
        return self._connection.execute(sql, *args)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


def test_writer_activity_serializes_before_stale_open_trim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status="active")
    original_connect = store._connect
    writer = original_connect()
    trim_attempted = Event()
    connect_lock = Lock()
    connect_count = 0

    def tracked_connect() -> Any:
        nonlocal connect_count
        connection = original_connect()
        with connect_lock:
            connect_count += 1
            current = connect_count
        # trim_runtime_tables reads pre-trim stats first, then opens its writer.
        if current == 2:
            return _BeginSignalConnection(connection, trim_attempted)
        return connection

    writer.execute("BEGIN IMMEDIATE")
    writer.execute(
        "UPDATE routing_decisions SET created_at = ? WHERE trace_id = 'trace'",
        (_FUTURE,),
    )
    monkeypatch.setattr(store, "_connect", tracked_connect)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                store.trim_runtime_tables,
                older_than_days=1,
                dry_run=False,
                vacuum=False,
            )
            assert trim_attempted.wait(timeout=5)
            assert not pending.done()
            writer.commit()
            report = pending.result(timeout=10)
    finally:
        if writer.in_transaction:
            writer.rollback()
        writer.close()

    assert report["retired_open_runs"] == 0
    for table in RUNTIME_DELETE_ORDER:
        assert report["tables"][table]["deleted"] == 0
        assert report["remaining_tables"][table] == 1
    _assert_full_graph(store, status="active")


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM store_secrets WHERE name = 'retired-trace-hmac-v1'",
        "UPDATE store_secrets SET secret = x'00' WHERE name = 'retired-trace-hmac-v1'",
        "UPDATE store_secrets SET secret = randomblob(32) WHERE name = 'retired-trace-hmac-v1'",
    ],
    ids=["missing", "truncated", "replaced"],
)
def test_retired_trace_key_corruption_fails_closed_on_reopen(
    tmp_path: Path,
    mutation: str,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    run_id = store.create_run(
        trace_id="low-entropy-retired-trace",
        session_id="low-entropy-retired-session",
    )
    store.record_host_canary_attestation(
        host="codex",
        proof_contract="agency.codex-activation-canary.v2",
        proof_digest="a" * 64,
        profile_scope="current-profile",
        platform_system="Windows",
        platform_release="test",
        platform_machine="x86_64",
        host_version="test",
        plugin_version="test",
        install_id="test-install",
        bundle_digest="a" * 64,
        trace_id="low-entropy-retired-trace",
    )
    store.complete_run(run_id)
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET last_activity_at = ? WHERE trace_id = ?",
            (_OLD, "low-entropy-retired-trace"),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(
        older_than_days=1,
        vacuum=False,
    )
    assert report["tombstones_created"] == 1
    assert store.get_host_canary_attestation("codex") is None
    with pytest.raises(ValueError, match="permanently retired"):
        store.create_run(
            trace_id="low-entropy-retired-trace",
            session_id="new-session",
        )

    connection = store._connect()
    try:
        for table_row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            table = str(table_row["name"])
            text_columns = [
                str(column["name"])
                for column in connection.execute(f"PRAGMA table_info({table})")  # nosec B608
                if "TEXT" in str(column["type"]).upper()
            ]
            if not text_columns:
                continue
            projection = ", ".join(f'"{column}"' for column in text_columns)
            for row in connection.execute(
                f"SELECT {projection} FROM {table}"  # nosec B608
            ).fetchall():
                values = {str(value) for value in row if value is not None}
                assert "low-entropy-retired-trace" not in values
                assert "low-entropy-retired-session" not in values
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="retired-trace integrity key"):
        Store(path)


def test_turn_sequence_recovers_from_counter_reset_without_reuse(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    first = store.create_run(trace_id="first", session_id="session")
    store.complete_run(first)
    connection = store._connect()
    try:
        first_sequence = int(
            connection.execute(
                "SELECT turn_sequence FROM runs WHERE trace_id = 'first'"
            ).fetchone()[0]
        )
        connection.execute(
            "UPDATE runs SET last_activity_at = ? WHERE trace_id = 'first'",
            (_OLD,),
        )
        connection.commit()
    finally:
        connection.close()
    store.trim_runtime_tables(older_than_days=1, vacuum=False)

    connection = store._connect()
    try:
        connection.execute("UPDATE store_counters SET value = 0 WHERE name = 'turn-sequence'")
        connection.commit()
    finally:
        connection.close()
    store.create_run(trace_id="second", session_id="session")
    second = store.get_run("second")
    assert int(second["turn_sequence"]) > first_sequence


@pytest.mark.parametrize("status", ["active", "evidence_only"])
def test_old_semantic_timestamps_do_not_age_fresh_open_activity(
    tmp_path: Path,
    status: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    _seed_open_graph(store, status=status)
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET last_activity_at = "
            "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW') "
            "WHERE trace_id = 'trace'"
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(
        older_than_days=0,
        vacuum=False,
    )
    assert report["retired_open_runs"] == 0
    _assert_full_graph(store, status=status)
