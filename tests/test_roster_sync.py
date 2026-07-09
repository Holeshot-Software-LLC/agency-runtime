"""Tests for roster source trust and auto-approve sync behavior."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.cli.main import main
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.roster.sync import quarantine_candidate
from agency_runtime.core.store.sqlite import Store


def _agent(slug: str, description: str = "Useful specialist") -> dict[str, object]:
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": description,
        "division": "engineering",
        "body": f"You are {slug}, a useful specialist.",
    }


def _write_roster(path: Path, *agents: dict[str, object]) -> Path:
    path.write_text(json.dumps(list(agents)), encoding="utf-8")
    return path


def test_source_add_can_mark_trusted_for_auto_approve(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    source = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))

    assert main(["source", "add", str(source), "--name", "test", "--trusted-for-auto-approve"]) == 0

    sources = Store().list_agent_sources()
    assert len(sources) == 1
    assert sources[0]["url"] == str(source)
    assert sources[0]["trusted_for_auto_approve"] == 1


def test_auto_approve_rejects_untrusted_sources(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    source = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))
    store = Store()
    store.add_agent_source(str(source), "untrusted")

    assert main(["sync", "--auto-approve"]) == 1

    captured = capsys.readouterr()
    assert "not trusted" in captured.err
    assert Store().get_active_roster_as_catalog() == []


def test_auto_approve_fails_closed_on_source_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    valid = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))
    missing = tmp_path / "missing.json"
    store = Store()
    store.add_agent_source(str(valid), "valid", trusted_for_auto_approve=True)
    store.add_agent_source(str(missing), "missing", trusted_for_auto_approve=True)

    assert main(["sync", "--auto-approve"]) == 2

    assert Store().get_active_roster_as_catalog() == []


def test_auto_approve_activates_trusted_snapshot_and_prunes_removed_agents(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    source = _write_roster(tmp_path / "agents.json", _agent("new-specialist"))
    store = Store()
    store.activate_agent(_agent("obsolete-specialist"))
    store.add_agent_source(str(source), "trusted", trusted_for_auto_approve=True)

    assert main(["sync", "--auto-approve"]) == 0

    roster = Store().get_active_roster_as_catalog()
    assert [agent["slug"] for agent in roster] == ["new-specialist"]
    assert roster[0]["description"] == "Useful specialist"

    capsys.readouterr()
    assert main(["sync", "--auto-approve"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["diff"]["changed"] == {}
    assert payload["diff"]["unchanged"] == ["new-specialist"]

    conn = Store()._connect()
    try:
        snapshots = conn.execute("SELECT agent_count, manifest FROM agent_snapshots").fetchall()
    finally:
        conn.close()
    assert snapshots[-1]["agent_count"] == 1
    assert len(json.loads(snapshots[-1]["manifest"])["candidate_ids"]) == 1


def test_auto_approve_snapshot_is_scoped_to_current_sync(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    old_source = _write_roster(tmp_path / "old.json", _agent("old-pending"))
    new_source = _write_roster(tmp_path / "new.json", _agent("new-specialist"))
    store = Store()
    old_source_id = store.add_agent_source(str(old_source), "old", trusted_for_auto_approve=True)
    old_candidate = _agent("old-pending")
    old_candidate["source"] = str(old_source)
    quarantine_candidate(old_candidate, old_source_id, store)
    conn = store._connect()
    try:
        conn.execute("UPDATE agent_sources SET enabled = 0 WHERE id = ?", (old_source_id,))
        conn.commit()
    finally:
        conn.close()
    store.add_agent_source(str(new_source), "new", trusted_for_auto_approve=True)

    assert main(["sync", "--auto-approve"]) == 0

    roster = [agent["slug"] for agent in Store().get_active_roster_as_catalog()]
    assert roster == ["new-specialist"]
    conn = Store()._connect()
    try:
        old_status = conn.execute("SELECT status FROM agent_candidates WHERE slug = 'old-pending'").fetchone()["status"]
    finally:
        conn.close()
    assert old_status == "pending"


def test_starter_roster_seed_does_not_overwrite_synced_agents(tmp_path):
    store = Store(tmp_path / "agency.db")
    store.activate_agent({
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Synced upstream reviewer",
        "source": "trusted-source",
        "hash": "upstream-hash",
    })

    count = seed_starter_roster(store)

    assert count == len(STARTER_ROSTER) - 1
    code_reviewer = next(
        agent for agent in store.get_active_roster()
        if agent["agent_slug"] == "code-reviewer"
    )
    assert code_reviewer["description"] == "Synced upstream reviewer"
    assert code_reviewer["source"] == "trusted-source"
    assert code_reviewer["hash"] == "upstream-hash"
    assert seed_starter_roster(store) == 0
