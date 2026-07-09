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
    store.activate_agent({"slug": "code-reviewer", "name": "Code Reviewer"})
    old_event = store.record_delegation(
        trace_id="old-trace",
        session_id="session-old",
        recommended_agent="old-agent",
        status="suggested",
    )
    recent_event = store.record_delegation(
        trace_id="new-trace",
        session_id="session-new",
        recommended_agent="new-agent",
        status="delegated",
    )

    with sqlite3.connect(db) as conn:
        conn.execute(
            "UPDATE delegation_events SET started_at = '2000-01-01T00:00:00+00:00' WHERE id = ?",
            (old_event,),
        )
        conn.execute(
            "UPDATE delegation_events SET started_at = '2100-01-01T00:00:00+00:00' WHERE id = ?",
            (recent_event,),
        )
        conn.commit()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    assert report["tables"]["delegation_events"]["deleted"] == 1
    assert [row["recommended_agent"] for row in store.get_delegations_for_session("session-new")] == ["new-agent"]
    assert store.get_delegations_for_session("session-old") == []
    assert [agent["agent_slug"] for agent in store.get_active_roster()] == ["code-reviewer"]


def test_store_trim_runtime_tables_dry_run_does_not_delete(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store.record_delegation(
        trace_id="trace",
        session_id="session",
        recommended_agent="agent",
        status="suggested",
    )

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


def test_cli_delegate_builds_noninteractive_backend_commands(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    commands: list[list[str]] = []

    def fake_which(name: str) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str]) -> int:
        commands.append(command)
        return 0

    monkeypatch.setattr("agency_runtime.cli.main.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.cli.main._run_command", fake_run)

    assert main(["delegate", "--backend", "codex", "--task", "review diff"]) == 0
    assert main(["delegate", "--backend", "claude", "--task", "review diff"]) == 0
    assert main(["delegate", "--backend", "hermes", "--task", "review diff"]) == 0

    assert commands == [
        ["/bin/codex", "exec", "review diff"],
        ["/bin/claude", "-p", "--output-format", "json", "review diff"],
        ["/bin/hermes", "-z", "review diff"],
    ]
