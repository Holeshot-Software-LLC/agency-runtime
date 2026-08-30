"""Tests for SQLite runtime-table maintenance commands."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from agency_runtime.cli.main import main
from agency_runtime.core.store.sqlite import Store


def test_store_trim_runtime_tables_keeps_roster_and_recent_rows(tmp_path: Path) -> None:
    db = tmp_path / "agency.db"
    store = Store(db)
    store._activate_prevalidated_agent(
        {
            "slug": "trim-code-reviewer",
            "name": "Trim Code Reviewer",
            "prompt_body": "Review retained runtime evidence.",
        }
    )
    old_event = store.record_delegation(
        trace_id="old-trace",
        session_id="session-old",
        recommended_agent="old-agent",
        status="suggested",
    )
    recent_event = store.record_delegation(
        trace_id="new-trace",
        session_id="session-new",
        work_unit_id="unit-new",
        recommended_agent="new-agent",
        status="delegated",
        backend="test-worker",
        executed_worker_kind="test-worker",
        executed_worker_id="worker-new",
        native_run_id="native-new",
    )
    store.close_turn_evidence("session-old", "old-trace")
    store.close_turn_evidence("session-new", "new-trace")

    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "UPDATE delegation_events SET started_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (old_event,),
        )
        conn.execute(
            "UPDATE delegation_events SET started_at = '2100-01-01T00:00:00+00:00' WHERE id = ?",
            (recent_event,),
        )
        conn.execute(
            "UPDATE runs SET last_activity_at = '2000-01-01T00:00:00+00:00' "
            "WHERE trace_id = 'old-trace'"
        )
        conn.commit()
    finally:
        conn.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    assert report["tables"]["delegation_events"]["deleted"] == 1
    assert [
        row["recommended_agent"] for row in store.get_delegations_for_session("session-new")
    ] == ["new-agent"]
    assert store.get_delegations_for_session("session-old") == []
    assert [agent["agent_slug"] for agent in store.get_active_roster()] == ["trim-code-reviewer"]


def test_store_trim_runtime_tables_dry_run_does_not_delete(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        recommended_agent="agent",
        status="suggested",
    )
    store.close_turn_evidence("session", "trace")

    report = store.trim_runtime_tables(keep_last=0, dry_run=True)

    assert report["dry_run"] is True
    assert report["tables"]["delegation_events"]["deleted"] == 1
    assert len(store.get_delegations_for_session("session")) == 1


def test_store_trim_runtime_tables_requires_policy(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")

    try:
        store.trim_runtime_tables()
    except ValueError as exc:
        assert "older_than_days" in str(exc)
    else:
        raise AssertionError("trim without a retention policy should fail")


def test_cli_db_trim_json(tmp_path: Path, monkeypatch, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    store = Store(db)
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        recommended_agent="agent",
        status="suggested",
    )
    store.close_turn_evidence("session", "trace")

    code = main(["db", "trim", "--keep-last", "0", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tables"]["delegation_events"]["deleted"] == 1
    assert store.get_delegations_for_session("session") == []


def test_cli_db_stats_json(tmp_path: Path, monkeypatch, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    Store(db).record_delegation(
        trace_id="trace",
        session_id="session",
        recommended_agent="agent",
        status="suggested",
    )

    code = main(["db", "stats", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["tables"]["delegation_events"] == 1
    assert payload["db_size_bytes"] > 0
