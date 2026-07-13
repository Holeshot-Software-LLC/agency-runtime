"""Tests for SQLite runtime-table maintenance commands."""

from __future__ import annotations

import json
import sqlite3
import subprocess
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
        conn.commit()
    finally:
        conn.close()

    report = store.trim_runtime_tables(older_than_days=1, vacuum=False)

    assert report["tables"]["delegation_events"]["deleted"] == 1
    assert [
        row["recommended_agent"] for row in store.get_delegations_for_session("session-new")
    ] == ["new-agent"]
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
    commands: list[tuple[list[str], str | None]] = []

    def fake_which(name: str, **_kwargs: object) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        input_text = kwargs.get("input_text")
        commands.append(
            (
                command,
                input_text if isinstance(input_text, str) else None,
            )
        )
        stdout = kwargs["stdout"]
        if command[0].endswith("codex"):
            stdout.write(
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "done"},
                    }
                )
                + "\n"
            )
            stdout.write(json.dumps({"type": "turn.completed"}) + "\n")
        elif command[0].endswith("claude"):
            stdout.write(json.dumps({"type": "result", "is_error": False, "result": "done"}))
        else:
            stdout.write("done")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", fake_run)

    assert main(["delegate", "--backend", "codex", "--task", "review diff"]) == 0
    assert main(["delegate", "--backend", "claude", "--task", "review diff"]) == 0
    assert main(["delegate", "--backend", "hermes", "--task", "review diff"]) == 0

    assert commands == [
        (["/bin/codex", "exec", "--json", "--color", "never"], "review diff"),
        (["/bin/claude", "-p", "--output-format", "json"], "review diff"),
        (["/bin/hermes", "-z", "review diff"], None),
    ]


def test_cli_delegate_timeout_marks_delegation_skipped(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    def fake_which(name: str, **_kwargs: object) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[:2] == ["/bin/hermes", "-z"]
        assert "code-reviewer" in command[-1]
        assert kwargs["timeout"] == 0.01
        raise subprocess.TimeoutExpired(command, 0.01)

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", fake_run)

    code = main(
        [
            "delegate",
            "--backend",
            "hermes",
            "--agent",
            "code-reviewer",
            "--task",
            "review diff",
            "--timeout",
            "0.01",
        ]
    )

    assert code == 124
    assert "timed out after 0.01s" in capsys.readouterr().err
    store = Store(db)
    [metadata] = store.recent_runtime_activity()["delegations"]
    [event] = store.get_delegations(metadata["trace_id"])
    assert event["status"] == "skipped"
    assert event["backend"] == "hermes"
    assert event["skip_reason"] == "backend command timed out after 0.01s"
    assert event["error"] == "backend command timed out after 0.01s"


def test_cli_delegate_exit_124_remains_failed(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    def fake_which(name: str, **_kwargs: object) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["timeout"] == 0.01
        return subprocess.CompletedProcess(command, 124)

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", fake_run)

    code = main(
        [
            "delegate",
            "--backend",
            "hermes",
            "--agent",
            "code-reviewer",
            "--task",
            "review diff",
            "--timeout",
            "0.01",
        ]
    )

    assert code == 124
    store = Store(db)
    [metadata] = store.recent_runtime_activity()["delegations"]
    [event] = store.get_delegations(metadata["trace_id"])
    assert event["status"] == "failed"
    assert "exited with 124" in event["error"]
    assert event["skip_reason"] == ""


def test_cli_delegate_json_success_reports_event(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))
    calls: list[tuple[list[str], float | None]] = []

    def fake_which(name: str, **_kwargs: object) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs.get("timeout")))
        kwargs["stdout"].write("done")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", fake_run)

    code = main(
        [
            "delegate",
            "--backend",
            "hermes",
            "--agent",
            "code-reviewer",
            "--task",
            "review diff",
            "--timeout",
            "2",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "completed"
    assert payload["exit_code"] == 0
    assert payload["trace_id"].startswith("cli-delegate-")
    assert payload["backend"] == "hermes"
    assert payload["agent"] == "code-reviewer"
    assert payload["timeout_seconds"] == 2.0
    assert len(calls) == 1
    assert calls[0][0][:2] == ["/bin/hermes", "-z"]
    assert "code-reviewer" in calls[0][0][-1]
    assert calls[0][1] == 2.0
    [event] = Store(db).get_delegations(payload["trace_id"])
    assert event["status"] == "completed"


def test_cli_delegate_json_timeout_reports_skipped(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    def fake_which(name: str, **_kwargs: object) -> str:
        return f"/bin/{name}"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, float(kwargs["timeout"]))

    monkeypatch.setattr("agency_runtime.core.delegation.backends.shutil.which", fake_which)
    monkeypatch.setattr("agency_runtime.core.delegation.backends._run_owned_process", fake_run)

    code = main(
        [
            "delegate",
            "--backend",
            "hermes",
            "--agent",
            "code-reviewer",
            "--task",
            "review diff",
            "--timeout",
            "0.01",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 124
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "skipped"
    assert payload["exit_code"] == 124
    assert payload["skip_reason"] == "backend command timed out after 0.01s"
    [event] = Store(db).get_delegations(payload["trace_id"])
    assert event["status"] == "skipped"
    assert event["skip_reason"] == "backend command timed out after 0.01s"


def test_cli_delegate_rejects_nonpositive_timeout(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    code = main(["delegate", "--backend", "hermes", "--task", "review diff", "--timeout", "0"])

    assert code == 2
    assert "--timeout must be a finite value greater than 0" in capsys.readouterr().err
    assert Store(db).runtime_table_counts()["delegation_events"] == 0


def test_cli_delegate_rejects_nonfinite_timeout(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    code = main(["delegate", "--backend", "hermes", "--task", "review diff", "--timeout", "nan"])

    assert code == 2
    assert "--timeout must be a finite value greater than 0" in capsys.readouterr().err
    assert Store(db).runtime_table_counts()["delegation_events"] == 0


def test_cli_delegate_json_rejects_bad_timeout_as_json(monkeypatch, tmp_path: Path, capsys) -> None:
    db = tmp_path / "agency.db"
    monkeypatch.setenv("AGENCY_DB_PATH", str(db))

    code = main(
        ["delegate", "--backend", "hermes", "--task", "review diff", "--timeout", "inf", "--json"]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "error": "--timeout must be a finite value greater than 0",
        "exit_code": 2,
        "status": "error",
    }
    assert Store(db).runtime_table_counts()["delegation_events"] == 0
