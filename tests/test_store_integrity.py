"""Schema migration and foreign-key integrity tests for the canonical store."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path

import pytest

from agency_runtime.core.store.sqlite import Store


def _row(store: Store, sql: str, parameters: tuple = ()) -> sqlite3.Row:
    connection = store._connect()
    try:
        result = connection.execute(sql, parameters).fetchone()
        assert result is not None
        return result
    finally:
        connection.close()


def test_dashboard_activity_orders_use_global_timestamp_indexes(tmp_path: Path):
    store = Store(tmp_path / "indexed" / "agency.db")
    connection = store._connect()
    try:
        plans = {
            "idx_runs_recent": (
                "SELECT id FROM runs ORDER BY started_at DESC, id DESC LIMIT 100"
            ),
            "idx_receipts_recent": (
                "SELECT id FROM model_receipts "
                "ORDER BY COALESCE(ended_at, started_at) DESC, id DESC LIMIT 100"
            ),
            "idx_delegations_recent": (
                "SELECT id FROM delegation_events "
                "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT 100"
            ),
            "idx_finalization_recent": (
                "SELECT id FROM finalization_events "
                "ORDER BY created_at DESC, id DESC LIMIT 100"
            ),
            "idx_routing_recent": (
                "SELECT id FROM routing_decisions "
                "ORDER BY created_at DESC, id DESC LIMIT 100"
            ),
        }
        for index_name, sql in plans.items():
            details = " ".join(
                str(row["detail"])
                for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}")
            )
            assert index_name in details, (index_name, details)
            assert "USE TEMP B-TREE" not in details, (index_name, details)
    finally:
        connection.close()


def test_create_run_default_is_a_fixed_metadata_only_projection(
    tmp_path: Path, monkeypatch
):
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
    receipt = _row(
        migrated, "SELECT api_base FROM model_receipts WHERE id = ?", (receipt_id,)
    )
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
            "password=hunter2 "
            "https://alice:hunter2@example.test/v1?token=hunter2 " + ("z" * 4_000)
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
def test_store_repairs_private_modes_under_permissive_umask(tmp_path: Path):
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

            assert stat.S_IMODE(parent.stat().st_mode) == 0o700
            assert stat.S_IMODE(store.db_path.stat().st_mode) == 0o600
            for suffix in ("-wal", "-shm"):
                sidecar = Path(f"{store.db_path}{suffix}")
                assert sidecar.exists()
                assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
        finally:
            connection.close()
    finally:
        os.umask(old_umask)


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
        row = connection.execute(
            "SELECT work_units, decision FROM routing_decisions"
        ).fetchone()
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
        row = connection.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row["status"] == "active"
        assert row["user_message"] == ""
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM runs WHERE trace_id = 'trace-1'"
            ).fetchone()[0]
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
            migrated.execute(
                "SELECT COUNT(*) FROM runs WHERE trace_id = 'duplicate'"
            ).fetchone()[0]
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
        assert (
            migrated.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            == 4
        )
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
            row["trace_id"]
            for row in connection.execute("SELECT trace_id FROM runs").fetchall()
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
            "UPDATE delegation_events SET started_at = '2100-01-01T00:00:00+00:00' "
            "WHERE id = ?",
            (delegation_id,),
        )
        connection.commit()
    finally:
        connection.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    connection = store._connect()
    try:
        retained = {
            row["trace_id"]
            for row in connection.execute("SELECT trace_id FROM runs").fetchall()
        }
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        connection.close()
    assert retained == set(traces.values())
    assert report["tables"]["runs"]["deleted"] == 1
    assert fk_errors == []
