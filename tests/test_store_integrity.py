"""Schema migration and foreign-key integrity tests for the canonical store."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

import agency_runtime.core.store.queries as store_queries
import agency_runtime.core.store.sqlite as sqlite_store
from agency_runtime.core.store.queries import retention_predicates
from agency_runtime.core.store.sqlite import Store


def _row(store: Store, sql: str, parameters: tuple = ()) -> sqlite3.Row:
    connection = store._connect()
    try:
        result = connection.execute(sql, parameters).fetchone()
        assert result is not None
        return result
    finally:
        connection.close()


def test_concurrent_legacy_store_migration_is_serialized_and_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-concurrent.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (5);
        CREATE TABLE host_canary_attestations (
            host TEXT PRIMARY KEY,
            platform_system TEXT NOT NULL,
            platform_release TEXT NOT NULL,
            platform_machine TEXT NOT NULL,
            plugin_version TEXT NOT NULL,
            passed_at TEXT NOT NULL,
            trace_id TEXT NOT NULL
        );
        """
    )
    connection.close()

    def open_store(_index: int) -> tuple[bool, int]:
        store = Store(path)
        return (
            store.get_host_control("codex")["enabled"],
            store.runtime_table_counts()["host_canary_attestations"],
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(open_store, range(24)))

    assert results == [(True, 0)] * 24
    migrated = sqlite3.connect(path)
    try:
        columns = {
            row[1] for row in migrated.execute("PRAGMA table_info(host_canary_attestations)")
        }
        version = migrated.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    finally:
        migrated.close()
    assert {"profile_scope", "host_version", "install_id", "bundle_digest"} <= columns
    assert version == 10


def test_current_schema_store_opens_while_another_connection_holds_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "current.db"
    store = Store(path)
    writer = store._connect()
    writer.execute("BEGIN IMMEDIATE")
    monkeypatch.setattr(
        Store,
        "_init_schema",
        lambda _self: pytest.fail("current schema must not enter migration"),
    )
    try:
        reopened = Store(path)
        reader = reopened._connect()
        try:
            assert reader.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 10
        finally:
            reader.close()
    finally:
        writer.rollback()
        writer.close()


def test_newer_schema_is_refused_without_rewriting_version(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    store = Store(path)
    connection = store._connect()
    try:
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (11)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(RuntimeError, match="schema is newer"):
        Store(path)

    unchanged = sqlite3.connect(path)
    try:
        assert unchanged.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 11
    finally:
        unchanged.close()


def test_dashboard_activity_orders_use_global_timestamp_indexes(tmp_path: Path):
    store = Store(tmp_path / "indexed" / "agency.db")
    connection = store._connect()
    try:
        plans = {
            "idx_runs_recent": ("SELECT id FROM runs ORDER BY started_at DESC, id DESC LIMIT 100"),
            "idx_receipts_recent": (
                "SELECT id FROM model_receipts "
                "ORDER BY COALESCE(ended_at, started_at) DESC, id DESC LIMIT 100"
            ),
            "idx_delegations_recent": (
                "SELECT id FROM delegation_events "
                "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT 100"
            ),
            "idx_finalization_recent": (
                "SELECT id FROM finalization_events ORDER BY created_at DESC, id DESC LIMIT 100"
            ),
            "idx_routing_recent": (
                "SELECT id FROM routing_decisions ORDER BY created_at DESC, id DESC LIMIT 100"
            ),
        }
        for index_name, sql in plans.items():
            details = " ".join(
                str(row["detail"]) for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}")
            )
            assert index_name in details, (index_name, details)
            assert "USE TEMP B-TREE" not in details, (index_name, details)
    finally:
        connection.close()


def test_dashboard_activity_projection_is_five_queries_without_discarded_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_delegation(
        trace_id="dashboard-query-count",
        session_id="session",
        host="codex",
        skip_reason="policy_denied",
    )
    store.record_routing_decision(
        trace_id="dashboard-query-count",
        session_id="session",
        query_hash="a" * 64,
        context_fingerprint="b" * 64,
        decision={
            "status": "selected",
            "selected_ids": ["reviewer"],
            "work_units": {"delegate": True, "count": 1},
        },
    )
    statements: list[str] = []
    original_connect = store._connect

    def traced_connect() -> sqlite3.Connection:
        connection = original_connect()
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(store, "_connect", traced_connect)

    activity = store.recent_dashboard_activity(limit=200)

    selects = [
        statement for statement in statements if statement.lstrip().upper().startswith("SELECT")
    ]
    assert len(selects) == 5
    assert "skip_reason" not in activity["delegations"][0]
    assert "work_units" not in activity["routing"][0]
    delegation_sql = next(statement for statement in selects if "delegation_events" in statement)
    routing_sql = next(statement for statement in selects if "routing_decisions" in statement)
    assert "skip_reason" not in delegation_sql
    assert "work_units" not in routing_sql


def test_snapshot_listing_uses_materialized_prompt_free_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    secret = "candidate-prompt-must-not-enter-dashboard-read"
    store.create_snapshot(
        "snapshot-summary",
        {
            "approved": True,
            "candidates": [{"id": "candidate", "content": secret}],
            "diff": {
                "added": ["one", "two"],
                "changed": {"three": {"prompt_body_changed": True}},
                "removed": ["four"],
            },
        },
    )
    statements: list[str] = []
    original_connect = store._connect

    def traced_connect() -> sqlite3.Connection:
        connection = original_connect()
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(store, "_connect", traced_connect)
    monkeypatch.setattr(
        store_queries,
        "project_snapshot_summary",
        lambda _value: pytest.fail("snapshot reads must not parse manifests"),
    )

    [snapshot] = store.list_roster_snapshots()

    assert snapshot["approved"] is True
    assert snapshot["added"] == 2
    assert snapshot["changed"] == 1
    assert snapshot["removed"] == 1
    assert secret not in repr(snapshot)
    selects = [
        statement for statement in statements if statement.lstrip().upper().startswith("SELECT")
    ]
    assert len(selects) == 1
    assert "manifest" not in selects[0].casefold()


def test_schema_v10_materializes_nested_snapshot_diff_once(tmp_path: Path) -> None:
    path = tmp_path / "legacy-snapshot.db"
    manifest = {
        "approved": True,
        "candidates": [{"id": "candidate", "content": "private prompt"}],
        "diff": {
            "added": ["one", "two"],
            "changed": {"three": {}},
            "removed": ["four"],
        },
    }
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (9);
        CREATE TABLE agent_snapshots (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            agent_count INTEGER,
            manifest TEXT,
            activated INTEGER DEFAULT 0
        );
        """
    )
    connection.execute(
        "INSERT INTO agent_snapshots "
        "(id, snapshot_id, created_at, agent_count, manifest, activated) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("row", "legacy", "2026-07-12T00:00:00Z", 1, json.dumps(manifest), 0),
    )
    connection.commit()
    connection.close()

    store = Store(path)
    [snapshot] = store.list_roster_snapshots()

    assert snapshot["approved"] is True
    assert snapshot["added"] == 2
    assert snapshot["changed"] == 1
    assert snapshot["removed"] == 1
    migrated = store._connect()
    try:
        row = migrated.execute(
            "SELECT approved, added_count, changed_count, removed_count "
            "FROM agent_snapshots WHERE snapshot_id = 'legacy'"
        ).fetchone()
        version = migrated.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    finally:
        migrated.close()
    assert tuple(row) == (1, 2, 1, 1)
    assert version == 10


def test_operator_activity_normalizes_invalid_json_projection_shapes(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_routing_decision(
        trace_id="trace-invalid-shapes",
        session_id="session-invalid-shapes",
        query_hash="a" * 64,
        context_fingerprint="b" * 64,
        decision={"status": "selected", "selected_ids": ["reviewer"]},
    )
    store.record_finalization(
        trace_id="trace-invalid-shapes",
        host="codex",
        action="continue",
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE routing_decisions SET selected_ids = ?, work_units = ?",
            (json.dumps("not-a-list"), json.dumps(["not-a-mapping"])),
        )
        connection.execute(
            "UPDATE finalization_events SET missing = ?",
            (json.dumps({"not": "a-list"}),),
        )
        connection.commit()
    finally:
        connection.close()

    activity = store.recent_runtime_activity()

    assert activity["routing"][0]["selected_ids"] == []
    assert activity["routing"][0]["work_units"] == {}
    assert activity["finalizations"][0]["missing"] == ["unparseable"]


@pytest.mark.parametrize(
    "manifest",
    [
        ["not-a-mapping"],
        {"added": None, "changed": "not-a-list", "removed": {}},
    ],
)
def test_roster_snapshot_reads_tolerate_invalid_manifest_shapes(
    tmp_path: Path,
    manifest: object,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_snapshot("invalid-shape", {"candidates": []})
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE agent_snapshots SET manifest = ? WHERE snapshot_id = ?",
            (json.dumps(manifest), "invalid-shape"),
        )
        connection.commit()
    finally:
        connection.close()

    snapshot = store.list_roster_snapshots()[0]

    assert snapshot["approved"] is False
    assert snapshot["added"] == 0
    assert snapshot["changed"] == 0
    assert snapshot["removed"] == 0


@pytest.mark.parametrize(
    ("table", "timestamp_expression"),
    [
        ("runs; DROP TABLE runs", "COALESCE(ended_at, started_at)"),
        ("runs", "started_at); DROP TABLE runs"),
    ],
)
def test_retention_query_builder_rejects_non_allowlisted_identifiers(
    table: str,
    timestamp_expression: str,
) -> None:
    with pytest.raises(ValueError, match="must be allowlisted"):
        retention_predicates(
            table,
            timestamp_expression,
            cutoff=None,
            keep_last=1,
        )


def test_create_run_default_is_a_fixed_metadata_only_projection(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "agency_runtime.core.store.sqlite._capture_content_enabled",
        lambda: False,
    )
    store = Store(tmp_path / "private" / "agency.db")

    run_id = store.create_run(
        trace_id="trace-private",
        session_id="session-private",
        host="codex",
        user_message="customer secret prompt",
        metadata={
            "callback": "agency-runtime-litellm",
            "content_capture": False,
            "source": "hook",
            "prompt": "must never persist",
            "nested": {"api_key": "must never persist"},
            "request_kind": "contains spaces and secret prose",
        },
    )

    row = _row(store, "SELECT user_message, metadata FROM runs WHERE id = ?", (run_id,))
    assert row["user_message"] == ""
    assert json.loads(row["metadata"]) == {
        "callback": "agency-runtime-litellm",
        "content_capture": False,
        "source": "hook",
    }
    assert "must never persist" not in row["metadata"]


def test_opt_in_run_content_is_bounded_and_redacted(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "agency_runtime.core.store.sqlite._capture_content_enabled",
        lambda: True,
    )
    store = Store(tmp_path / "agency.db")
    secret = "sk-private-123"
    run_id = store.create_run(
        trace_id="trace-captured",
        user_message=(
            f"Authorization: Bearer {secret} "
            f"https://alice:password@example.test/v1?api_key={secret} " + ("x" * 4_000)
        ),
        metadata={"source": "hook", "arbitrary": secret},
    )

    row = _row(store, "SELECT user_message, metadata FROM runs WHERE id = ?", (run_id,))
    assert secret not in row["user_message"]
    assert "alice:password" not in row["user_message"]
    assert "?api_key" not in row["user_message"]
    assert len(row["user_message"]) <= 2_000
    assert json.loads(row["metadata"]) == {"source": "hook"}


def test_model_receipt_strips_api_base_credentials_query_and_fragment(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(
        trace_id="trace-endpoint",
        api_base="https://alice:password@[2001:db8::1]:8443/v1?api_key=secret#token",
    )

    receipt = store.get_model_receipt("trace-endpoint")
    assert receipt is not None
    assert receipt["api_base"] == "https://[2001:db8::1]:8443/v1"
    assert "alice" not in receipt["api_base"]
    assert "secret" not in receipt["api_base"]


def test_schema_upgrade_scrubs_legacy_private_fields(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "agency_runtime.core.store.sqlite._capture_content_enabled",
        lambda: False,
    )
    path = tmp_path / "agency.db"
    store = Store(path)
    store.create_run(trace_id="legacy-trace")
    receipt_id = store.record_model_receipt(trace_id="legacy-trace")
    event_id = store.record_delegation(trace_id="legacy-trace")
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE runs SET user_message = ?, metadata = ? WHERE trace_id = ?",
            (
                "legacy customer content",
                json.dumps({"source": "hook", "prompt": "legacy secret"}),
                "legacy-trace",
            ),
        )
        connection.execute(
            "UPDATE model_receipts SET api_base = ? WHERE id = ?",
            ("https://user:password@example.test/v1?api_key=legacy", receipt_id),
        )
        connection.execute(
            "UPDATE delegation_events SET skip_reason = ?, error = ? WHERE id = ?",
            ("customer ACME could not run", "password=legacy", event_id),
        )
        connection.execute("DELETE FROM schema_version")
        connection.execute("INSERT INTO schema_version (version) VALUES (3)")
        connection.commit()
    finally:
        connection.close()

    migrated = Store(path)
    run = _row(
        migrated,
        "SELECT user_message, metadata FROM runs WHERE trace_id = ?",
        ("legacy-trace",),
    )
    receipt = _row(migrated, "SELECT api_base FROM model_receipts WHERE id = ?", (receipt_id,))
    event = _row(
        migrated,
        "SELECT skip_reason, error FROM delegation_events WHERE id = ?",
        (event_id,),
    )
    assert run["user_message"] == ""
    assert json.loads(run["metadata"]) == {"source": "hook"}
    assert receipt["api_base"] == "https://example.test/v1"
    assert dict(event) == {
        "skip_reason": "unspecified_skip",
        "error": "execution_failed",
    }


def test_delegation_details_are_projected_by_default_and_redacted_when_opted_in(
    tmp_path: Path,
    monkeypatch,
):
    capture = False
    monkeypatch.setattr(
        "agency_runtime.core.store.sqlite._capture_content_enabled",
        lambda: capture,
    )
    store = Store(tmp_path / "agency.db")
    event_id = store.record_delegation(
        trace_id="trace-default-detail",
        skip_reason="Cannot run customer ACME-492 payload",
        error="request failed password=hunter2 for Jane Customer",
    )
    projected = _row(
        store,
        "SELECT skip_reason, error FROM delegation_events WHERE id = ?",
        (event_id,),
    )
    assert projected["skip_reason"] == "unspecified_skip"
    assert projected["error"] == "execution_failed"

    capture = True
    event_id = store.record_delegation(
        trace_id="trace-captured-detail",
        skip_reason="backend command timed out after 1s",
        error=(
            "password=hunter2 https://alice:hunter2@example.test/v1?token=hunter2 " + ("z" * 4_000)
        ),
    )
    captured = _row(
        store,
        "SELECT skip_reason, error FROM delegation_events WHERE id = ?",
        (event_id,),
    )
    assert captured["skip_reason"] == "backend command timed out after 1s"
    assert "hunter2" not in captured["error"]
    assert "alice:" not in captured["error"]
    assert "?token" not in captured["error"]
    assert len(captured["error"]) <= 2_000


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not Windows ACLs")
def test_store_preserves_preexisting_parent_mode_but_hardens_owned_files(
    tmp_path: Path,
) -> None:
    parent = tmp_path / "runtime"
    parent.mkdir(mode=0o777)
    parent.chmod(0o755)
    old_umask = os.umask(0o022)
    try:
        store = Store(parent / "agency.db")
        connection = store._connect()
        try:
            connection.execute(
                "INSERT INTO skills_loaded (id, session_id, skill_name, loaded_at) "
                "VALUES ('mode-test', 'session', 'skill', '2026-07-11T00:00:00+00:00')"
            )
            connection.commit()
            store._repair_storage_permissions()

            assert stat.S_IMODE(parent.stat().st_mode) == 0o755
            assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600
            for suffix in ("-wal", "-shm"):
                sidecar = Path(f"{store.db_path}{suffix}")
                assert sidecar.exists()
                assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
        finally:
            connection.close()
    finally:
        os.umask(old_umask)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not Windows ACLs")
def test_store_hardens_newly_created_dedicated_parent(tmp_path: Path) -> None:
    parent = tmp_path / "owned" / "runtime"

    store = Store(parent / "agency.db")

    assert stat.S_IMODE(parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600


def test_store_never_sends_preexisting_arbitrary_parent_to_permission_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "shared"
    parent.mkdir()
    calls: list[tuple[Path, bool]] = []

    def observe(path: Path, *, directory: bool) -> None:
        calls.append((path, directory))

    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", observe)

    Store(parent / "agency.db")

    assert (parent, True) not in calls
    assert (parent / "agency.db", False) in calls


def test_storage_permission_repair_is_serialized_process_wide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stores = [Store.__new__(Store), Store.__new__(Store)]
    target = tmp_path / "shared.db-shm"
    first_entered = threading.Event()
    second_started = threading.Event()
    second_entered = threading.Event()
    release_first = threading.Event()
    call_lock = threading.Lock()
    calls = 0

    def observe_repair(
        _self: Store,
        _path: Path,
        *,
        directory: bool,
        optional_sidecar: bool,
    ) -> bool:
        nonlocal calls
        assert directory is False
        assert optional_sidecar is True
        with call_lock:
            calls += 1
            call = calls
        if call == 1:
            first_entered.set()
            assert release_first.wait(timeout=2.0)
        else:
            second_entered.set()
        return False

    monkeypatch.setattr(Store, "_repair_storage_target_once", observe_repair)

    def repair_second() -> None:
        second_started.set()
        stores[1]._repair_storage_target(
            target,
            directory=False,
            optional_sidecar=True,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(
            stores[0]._repair_storage_target,
            target,
            directory=False,
            optional_sidecar=True,
        )
        assert first_entered.wait(timeout=2.0)
        second = executor.submit(repair_second)
        assert second_started.wait(timeout=2.0)
        assert not second_entered.wait(timeout=0.2)
        release_first.set()
        first.result(timeout=2.0)
        second.result(timeout=2.0)

    assert second_entered.is_set()


def test_optional_sidecar_acl_failure_tolerates_disappearance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store.__new__(Store)
    store._permission_fingerprints = {}
    sidecar = tmp_path / "agency.db-shm"
    sidecar.write_bytes(b"sidecar")
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )

    def disappear(path: Path, *, directory: bool) -> None:
        assert directory is False
        path.unlink()
        raise PermissionError("sidecar disappeared during ACL repair")

    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", disappear)

    store._repair_storage_target(
        sidecar,
        directory=False,
        optional_sidecar=True,
    )

    assert not sidecar.exists()
    assert store._permission_fingerprints == {}


def test_optional_sidecar_acl_failure_retries_only_after_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store.__new__(Store)
    store._permission_fingerprints = {}
    sidecar = tmp_path / "agency.db-shm"
    original = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=1, st_ino=2)
    replacement = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=3, st_ino=4)
    metadata = iter((original, replacement, replacement, replacement))
    repair_attempts = 0
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )
    monkeypatch.setattr(store, "_storage_metadata", lambda *_args, **_kwargs: next(metadata))

    def replace_once(_path: Path, *, directory: bool) -> None:
        nonlocal repair_attempts
        assert directory is False
        repair_attempts += 1
        if repair_attempts == 1:
            raise PermissionError("original sidecar was replaced")

    monkeypatch.setattr(sqlite_store, "_restrict_path_permissions", replace_once)

    store._repair_storage_target(
        sidecar,
        directory=False,
        optional_sidecar=True,
    )

    assert repair_attempts == 2
    assert store._permission_fingerprints[sidecar] == (3, 4)


@pytest.mark.parametrize("optional_sidecar", [False, True])
def test_acl_failure_for_stable_storage_identity_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    optional_sidecar: bool,
) -> None:
    store = Store.__new__(Store)
    store._permission_fingerprints = {}
    sidecar = tmp_path / "agency.db-shm"
    sidecar.write_bytes(b"sidecar")
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("stable ACL failure")),
    )

    with pytest.raises(PermissionError, match="stable ACL failure"):
        store._repair_storage_target(
            sidecar,
            directory=False,
            optional_sidecar=optional_sidecar,
        )


def test_optional_sidecar_acl_failure_rejects_replacement_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store.__new__(Store)
    store._permission_fingerprints = {}
    sidecar = tmp_path / "agency.db-shm"
    regular = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_dev=1, st_ino=2)
    replacement_link = SimpleNamespace(st_mode=stat.S_IFLNK | 0o777, st_dev=3, st_ino=4)
    metadata = iter((regular, replacement_link))
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda observed: observed is replacement_link,
    )
    monkeypatch.setattr(store, "_storage_metadata", lambda *_args, **_kwargs: next(metadata))
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            PermissionError("original sidecar was replaced")
        ),
    )

    with pytest.raises(PermissionError, match="symlink or reparse"):
        store._repair_storage_target(
            sidecar,
            directory=False,
            optional_sidecar=True,
        )


def test_windows_file_acl_hardening_fails_closed_when_dacl_restriction_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.db"
    path.write_bytes(b"")
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(sqlite_store.os, "chmod", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_windows_acl",
        lambda _path, *, directory: False,
    )

    with pytest.raises(PermissionError, match="private Windows ACL"):
        sqlite_store._restrict_path_permissions(path, directory=False)


def test_store_rejects_preexisting_database_symlink_before_permission_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target.db"
    target.write_bytes(b"not-a-database")
    link = tmp_path / "agency.db"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    calls: list[Path] = []
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, *, directory: calls.append(path),
    )

    with pytest.raises(PermissionError, match="symlink or reparse"):
        Store(link)

    assert calls == []
    assert target.read_bytes() == b"not-a-database"


@pytest.mark.parametrize("suffix", ["-journal", "-wal", "-shm"])
def test_store_rejects_preexisting_sqlite_sidecar_symlinks(
    tmp_path: Path,
    suffix: str,
) -> None:
    path = tmp_path / "agency.db"
    target = tmp_path / "unrelated.txt"
    target.write_bytes(b"unrelated")
    sidecar = Path(f"{path}{suffix}")
    try:
        sidecar.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(PermissionError, match="sidecar symlink"):
        Store(path)

    assert target.read_bytes() == b"unrelated"
    assert not path.exists()


@pytest.mark.parametrize("suffix", ["", "-journal", "-wal", "-shm"])
def test_store_rejects_nonregular_database_paths_before_permission_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    path = tmp_path / "agency.db"
    unsafe_path = path if not suffix else Path(f"{path}{suffix}")
    unsafe_path.mkdir()
    permission_repairs: list[tuple[Path, bool]] = []
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda candidate, *, directory: permission_repairs.append((candidate, directory)),
    )

    with pytest.raises(PermissionError, match="non-regular file"):
        Store(path)

    assert permission_repairs == []
    assert unsafe_path.is_dir()
    if suffix:
        assert not path.exists()


def test_connect_closes_connection_when_setup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")

    class Connection:
        row_factory = None
        closed = False

        def execute(self, _sql: str) -> Connection:
            return self

        def close(self) -> None:
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(sqlite_store.sqlite3, "connect", lambda *_a, **_kw: connection)
    monkeypatch.setattr(
        store,
        "_repair_storage_permissions",
        lambda: (_ for _ in ()).throw(PermissionError("hardening failed")),
    )

    with pytest.raises(PermissionError, match="hardening failed"):
        store._connect()

    assert connection.closed is True


def test_agent_versions_are_immutable_and_idempotent(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    content = "You are a production security specialist."
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    agent = {
        "slug": "security-reviewer",
        "name": "Security Reviewer",
        "version": "2.0.0",
        "hash": content_hash,
        "prompt_body": content,
    }

    store.activate_agent(agent)
    first = _row(
        store,
        "SELECT id, hash, content, created_at FROM agent_versions "
        "WHERE agent_slug = ? AND version = ?",
        (agent["slug"], agent["version"]),
    )
    store.activate_agent(dict(agent))
    second = _row(
        store,
        "SELECT id, hash, content, created_at FROM agent_versions "
        "WHERE agent_slug = ? AND version = ?",
        (agent["slug"], agent["version"]),
    )
    assert dict(second) == dict(first)

    with pytest.raises(ValueError, match="immutable agent version conflict"):
        store.activate_agent({**agent, "prompt_body": "changed content"})
    with pytest.raises(ValueError, match="immutable agent version conflict"):
        store.activate_agent({**agent, "hash": "f" * 64})

    prompt = store.get_specialist_prompt(agent["slug"])
    assert prompt is not None
    assert prompt["prompt_body"] == content
    count = _row(
        store,
        "SELECT COUNT(*) FROM agent_versions WHERE agent_slug = ? AND version = ?",
        (agent["slug"], agent["version"]),
    )
    assert count[0] == 1


def test_routing_decision_projection_excludes_raw_work_unit_text(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    sensitive = "rotate customer ACME-SECRET-492 credentials"

    store.record_routing_decision(
        trace_id="trace-routing",
        session_id="session-routing",
        query_hash="a" * 64,
        context_fingerprint="b" * 64,
        decision={
            "status": "token_fallback",
            "selected_ids": ["security-reviewer"],
            "confidence": 0.8,
            "work_units": {
                "delegate": True,
                "count": 2,
                "confidence": "high",
                "source": "numbered_list",
                "units": [sensitive, "update the runbook"],
            },
            "untrusted_extra": sensitive,
        },
    )

    connection = store._connect()
    try:
        row = connection.execute("SELECT work_units, decision FROM routing_decisions").fetchone()
    finally:
        connection.close()

    assert sensitive not in row["work_units"]
    assert sensitive not in row["decision"]
    assert "units" not in json.loads(row["work_units"])
    assert "untrusted_extra" not in json.loads(row["decision"])


def test_store_enables_foreign_keys_and_creates_evidence_parent(tmp_path: Path):
    store = Store(tmp_path / "agency.db")

    store.record_delegation(
        trace_id="trace-1",
        session_id="session-1",
        host="test",
        recommended_agent="security-reviewer",
    )

    connection = store._connect()
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        parent = connection.execute(
            "SELECT trace_id, session_id, status FROM runs WHERE trace_id = ?",
            ("trace-1",),
        ).fetchone()
        assert dict(parent) == {
            "trace_id": "trace-1",
            "session_id": "session-1",
            "status": "evidence_only",
        }
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO model_receipts (id, trace_id, host, source, status) "
                "VALUES ('orphan', 'missing-trace', 'test', 'test', 'success')"
            )
    finally:
        connection.close()


def test_create_run_promotes_implicit_evidence_parent(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    store = Store(tmp_path / "agency.db")
    store.record_model_receipt(trace_id="trace-1", session_id="session-1", host="codex")

    run_id = store.create_run(
        trace_id="trace-1",
        session_id="session-1",
        host="codex",
        user_message="sensitive prompt",
        metadata={"source": "hook"},
    )

    connection = store._connect()
    try:
        row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "active"
        assert row["user_message"] == ""
        assert (
            connection.execute("SELECT COUNT(*) FROM runs WHERE trace_id = 'trace-1'").fetchone()[0]
            == 1
        )
    finally:
        connection.close()
        reset_config_cache()


def test_legacy_orphans_and_duplicate_runs_are_migrated(tmp_path: Path):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE runs (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown',
            started_at TEXT NOT NULL,
            ended_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            user_message TEXT,
            metadata TEXT
        );
        CREATE TABLE model_receipts (
            id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            session_id TEXT,
            host TEXT NOT NULL DEFAULT 'unknown',
            requested_model TEXT,
            model_group TEXT,
            resolved_provider TEXT,
            resolved_model TEXT,
            api_base TEXT,
            attempted_fallbacks INTEGER DEFAULT 0,
            model_id TEXT,
            source TEXT NOT NULL DEFAULT 'unknown',
            started_at TEXT,
            ended_at TEXT,
            status TEXT NOT NULL DEFAULT 'unknown',
            FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
        );
        INSERT INTO runs (id, trace_id, host, started_at) VALUES
            ('run-a', 'duplicate', 'test', '2026-01-01T00:00:00+00:00'),
            ('run-b', 'duplicate', 'test', '2026-01-02T00:00:00+00:00');
        INSERT INTO model_receipts
            (id, trace_id, session_id, host, source, started_at, status)
        VALUES
            ('receipt-a', 'orphan-trace', 'session-a', 'codex', 'legacy',
             '2026-01-03T00:00:00+00:00', 'success');
    """)
    connection.commit()
    connection.close()

    store = Store(path)

    migrated = store._connect()
    try:
        assert (
            migrated.execute("SELECT COUNT(*) FROM runs WHERE trace_id = 'duplicate'").fetchone()[0]
            == 1
        )
        orphan_parent = migrated.execute(
            "SELECT session_id, host, status FROM runs WHERE trace_id = 'orphan-trace'"
        ).fetchone()
        assert dict(orphan_parent) == {
            "session_id": "session-a",
            "host": "codex",
            "status": "evidence_only",
        }
        assert migrated.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 10
        recent_plan = " ".join(
            str(row["detail"])
            for row in migrated.execute(
                "EXPLAIN QUERY PLAN SELECT id FROM runs ORDER BY started_at DESC, id DESC LIMIT 100"
            )
        )
        assert "idx_runs_recent" in recent_plan
        assert "USE TEMP B-TREE" not in recent_plan
        assert migrated.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        migrated.close()


def test_retention_preserves_parents_of_retained_child_evidence(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="trace-with-child", host="test")
    store.create_run(trace_id="trace-without-child", host="test")
    store.record_model_receipt(
        trace_id="trace-with-child",
        host="test",
        ended_at="2100-01-03T00:00:00+00:00",
    )
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET started_at = '2000-01-01T00:00:00+00:00'")
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    connection = store._connect()
    try:
        traces = {
            row["trace_id"] for row in connection.execute("SELECT trace_id FROM runs").fetchall()
        }
    finally:
        connection.close()
    assert traces == {"trace-with-child"}
    assert report["tables"]["runs"]["deleted"] == 1


def test_keep_last_never_orphans_newer_child_from_older_parent(tmp_path: Path):
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="older-parent", host="test")
    store.create_run(trace_id="newer-parent", host="test")
    store.record_model_receipt(
        trace_id="older-parent",
        host="test",
        ended_at="2100-01-03T00:00:00+00:00",
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE runs SET started_at = '2000-01-01T00:00:00+00:00' "
            "WHERE trace_id = 'older-parent'"
        )
        connection.execute(
            "UPDATE runs SET started_at = '2100-01-02T00:00:00+00:00' "
            "WHERE trace_id = 'newer-parent'"
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(keep_last=1, vacuum=False)

    assert report["tables"]["runs"]["deleted"] == 0
    assert store.runtime_table_counts()["runs"] == 2
    assert store.runtime_table_counts()["model_receipts"] == 1


def test_retention_preserves_old_parents_across_mixed_fresh_child_tables(
    tmp_path: Path,
):
    store = Store(tmp_path / "agency.db")
    traces = {
        "receipt": "trace-receipt",
        "delegation": "trace-delegation",
        "finalization": "trace-finalization",
        "routing": "trace-routing",
    }
    for trace_id in (*traces.values(), "trace-no-child"):
        store.create_run(trace_id=trace_id, host="test")
    store.record_model_receipt(
        trace_id=traces["receipt"],
        host="test",
        ended_at="2100-01-01T00:00:00+00:00",
    )
    delegation_id = store.record_delegation(
        trace_id=traces["delegation"],
        host="test",
    )
    store.record_finalization(
        trace_id=traces["finalization"],
        host="test",
        action="accept",
    )
    store.record_routing_decision(
        trace_id=traces["routing"],
        session_id="session-routing",
        query_hash="a" * 64,
        context_fingerprint="b" * 64,
        decision={"status": "selected", "selected_ids": ["reviewer"]},
    )
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET started_at = '2000-01-01T00:00:00+00:00'")
        connection.execute(
            "UPDATE delegation_events SET started_at = '2100-01-01T00:00:00+00:00' WHERE id = ?",
            (delegation_id,),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    connection = store._connect()
    try:
        retained = {
            row["trace_id"] for row in connection.execute("SELECT trace_id FROM runs").fetchall()
        }
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        connection.close()
    assert retained == set(traces.values())
    assert report["tables"]["runs"]["deleted"] == 1
    assert fk_errors == []


def test_get_roster_entry_returns_one_normalized_active_record(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.activate_agent(
        {
            "slug": "security-reviewer",
            "name": "Security Reviewer",
            "description": "Reviews trust boundaries",
            "categories": ["security"],
            "capabilities": ["threat-modeling"],
            "tool_affinity": ["git"],
        }
    )

    assert store.get_roster_entry("missing") is None
    entry = store.get_roster_entry("security-reviewer")
    assert entry is not None
    assert entry["agent_slug"] == "security-reviewer"
    assert entry["categories"] == ["security"]
    assert entry["capabilities"] == ["threat-modeling"]
    assert entry["tool_affinity"] == ["git"]


def test_roster_reads_normalize_corrupt_legacy_json_projections(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.activate_agent(
        {
            "slug": "legacy-reviewer",
            "name": "Legacy Reviewer",
            "description": "Exercises legacy SQLite projections",
            "categories": ["security"],
            "capabilities": ["review"],
            "tool_affinity": ["git"],
            "prompt_body": "Review the supplied change.",
        }
    )
    connection = store._connect()
    try:
        connection.execute(
            "UPDATE agent_active SET categories = ?, capabilities = ?, "
            "tool_affinity = ? WHERE agent_slug = ?",
            ("{not-json", '{"unexpected":"mapping"}', "7", "legacy-reviewer"),
        )
        connection.commit()
    finally:
        connection.close()

    roster_entry = store.get_active_roster()[0]
    direct_entry = store.get_roster_entry("legacy-reviewer")
    prompt_entry = store.get_specialist_prompt("legacy-reviewer")
    catalog_entry = store.get_active_roster_as_catalog()[0]

    assert direct_entry is not None
    assert prompt_entry is not None
    for entry in (roster_entry, direct_entry, prompt_entry):
        assert entry["categories"] == []
        assert entry["capabilities"] == []
        assert entry["tool_affinity"] == []
    assert catalog_entry["categories"] == []
    assert catalog_entry["capabilities"] == []
