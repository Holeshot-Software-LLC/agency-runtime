"""Tests for roster source trust and auto-approve sync behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agency_runtime.cli.main import main
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.roster import sync as roster_sync
from agency_runtime.core.roster.sync import (
    RosterSyncError,
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    download_from_source,
    parse_agent_file,
    quarantine_candidate,
)
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


class _HTTPResponse:
    def __init__(self, data: bytes, content_length: str | None = None) -> None:
        self._data = data
        self._offset = 0
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = content_length
        self.read_calls: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int = -1) -> bytes:
        self.read_calls.append(size)
        if self._offset >= len(self._data):
            return b""
        end = len(self._data) if size < 0 else self._offset + size
        chunk = self._data[self._offset:end]
        self._offset += len(chunk)
        return chunk


def test_http_source_rejects_declared_oversize_before_read(monkeypatch):
    response = _HTTPResponse(b"[]", content_length="33")
    monkeypatch.setattr(roster_sync, "MAX_HTTP_SOURCE_BYTES", 32)
    monkeypatch.setattr(roster_sync.urllib.request, "urlopen", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match="declares 33 bytes"):
        download_from_source("https://example.invalid/agents.json")

    assert response.read_calls == []


def test_http_source_streams_and_rejects_undeclared_oversize(monkeypatch):
    response = _HTTPResponse(b"x" * 33)
    monkeypatch.setattr(roster_sync, "MAX_HTTP_SOURCE_BYTES", 32)
    monkeypatch.setattr(roster_sync, "HTTP_READ_CHUNK_BYTES", 7)
    monkeypatch.setattr(roster_sync.urllib.request, "urlopen", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match="exceeds 32 bytes"):
        download_from_source("https://example.invalid/agents.json")

    assert response.read_calls
    assert max(response.read_calls) <= 7


def test_local_source_rejects_oversize_before_parse(monkeypatch, tmp_path):
    source = tmp_path / "agent.md"
    source.write_bytes(b"x" * 33)
    monkeypatch.setattr(roster_sync, "MAX_LOCAL_FILE_BYTES", 32)

    with pytest.raises(RosterSyncError, match="local roster file is 33 bytes"):
        download_from_source(str(source))


def test_directory_source_caps_files_and_total_bytes(monkeypatch, tmp_path):
    (tmp_path / "a.md").write_text("# Alpha\nOne", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Beta\nTwo", encoding="utf-8")
    monkeypatch.setattr(roster_sync, "MAX_SOURCE_FILES", 1)

    with pytest.raises(RosterSyncError, match="more than 1 agent files"):
        download_from_source(str(tmp_path))

    monkeypatch.setattr(roster_sync, "MAX_SOURCE_FILES", 2)
    monkeypatch.setattr(roster_sync, "MAX_TOTAL_SOURCE_BYTES", 12)
    with pytest.raises(RosterSyncError, match="total limit of 12 bytes"):
        download_from_source(str(tmp_path))


def test_directory_source_rejects_deep_recursion(monkeypatch, tmp_path):
    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    (nested / "agent.md").write_text("# Agent\nPrompt", encoding="utf-8")
    monkeypatch.setattr(roster_sync, "MAX_DIRECTORY_DEPTH", 1)

    with pytest.raises(RosterSyncError, match="recursion depth 1"):
        download_from_source(str(tmp_path))


def test_directory_source_rejects_symbolic_links(tmp_path):
    target = tmp_path / "target"
    source = tmp_path / "source"
    target.mkdir()
    source.mkdir()
    (target / "agent.md").write_text("# Agent\nPrompt", encoding="utf-8")
    try:
        (source / "linked").symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable for this test user")

    with pytest.raises(RosterSyncError, match="symbolic links"):
        download_from_source(str(source))


def test_source_candidate_count_is_checked_before_normalization(monkeypatch, tmp_path):
    source = _write_roster(tmp_path / "agents.json", _agent("agent-one"), _agent("agent-two"))
    monkeypatch.setattr(roster_sync, "MAX_SOURCE_CANDIDATES", 1)
    monkeypatch.setattr(
        roster_sync,
        "_normalize_agent",
        lambda _agent: pytest.fail("candidate normalization must not run after count rejection"),
    )

    with pytest.raises(RosterSyncError, match="more than 1 candidates"):
        download_from_source(str(source))


def test_prompt_is_bounded_before_agent_parsing(monkeypatch):
    monkeypatch.setattr(roster_sync, "MAX_AGENT_PROMPT_BYTES", 4)

    with pytest.raises(RosterSyncError, match="prompt is 5 bytes"):
        parse_agent_file('{"slug":"agent","name":"Agent","description":"Useful","prompt":"12345"}')


def test_snapshot_rechecks_prompt_bound_before_manifest_duplication(monkeypatch, tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("bounded-agent"), source_id, store)
    monkeypatch.setattr(roster_sync, "MAX_AGENT_PROMPT_BYTES", 4)

    with pytest.raises(RosterSyncError, match="prompt"):
        create_roster_diff(store, candidate_ids=[candidate_id])

    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_snapshots").fetchone()[0] == 0
    finally:
        conn.close()


def test_snapshot_manifest_limit_is_checked_before_persistence(monkeypatch, tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("manifest-agent"), source_id, store)
    monkeypatch.setattr(roster_sync, "MAX_SNAPSHOT_MANIFEST_BYTES", 1)

    with pytest.raises(RosterSyncError, match="snapshot manifest"):
        create_roster_diff(store, candidate_ids=[candidate_id])

    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_snapshots").fetchone()[0] == 0
    finally:
        conn.close()


def _approved_snapshot(store: Store, source_id: str, prompt: str) -> str:
    candidate_id = quarantine_candidate(
        {
            "slug": "revision-agent",
            "name": "Revision Agent",
            "description": "Tests immutable revisions",
            "version": "1.0.0",
            "prompt_body": prompt,
            "content": prompt,
        },
        source_id,
        store,
    )
    manifest = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, manifest["snapshot_id"])
    return manifest["snapshot_id"]


def test_same_agent_version_and_hash_is_idempotent(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    first_snapshot = _approved_snapshot(store, source_id, "stable prompt")
    activate_snapshot(store, first_snapshot)

    conn = store._connect()
    try:
        before = dict(
            conn.execute(
                "SELECT id, hash, content, created_at FROM agent_versions "
                "WHERE agent_slug = 'revision-agent' AND version = '1.0.0'"
            ).fetchone()
        )
    finally:
        conn.close()

    second_snapshot = _approved_snapshot(store, source_id, "stable prompt")
    activate_snapshot(store, second_snapshot)

    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT id, hash, content, created_at FROM agent_versions "
            "WHERE agent_slug = 'revision-agent' AND version = '1.0.0'"
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert dict(rows[0]) == before


def test_changed_hash_cannot_replace_immutable_agent_version(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    first_snapshot = _approved_snapshot(store, source_id, "original prompt")
    activate_snapshot(store, first_snapshot)
    store.activate_agent(
        {
            "slug": "independent-agent",
            "name": "Independent Agent",
            "description": "Must survive failed activation",
        }
    )
    changed_snapshot = _approved_snapshot(store, source_id, "changed prompt")

    with pytest.raises(RosterSyncError, match="refusing to replace immutable agent version"):
        activate_snapshot(store, changed_snapshot)

    conn = store._connect()
    try:
        version = dict(
            conn.execute(
                "SELECT hash, content FROM agent_versions "
                "WHERE agent_slug = 'revision-agent' AND version = '1.0.0'"
            ).fetchone()
        )
        activated = conn.execute(
            "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
            (changed_snapshot,),
        ).fetchone()["activated"]
    finally:
        conn.close()
    assert version["content"] == "original prompt"
    assert version["hash"] == roster_sync._hash_text("original prompt")
    assert activated == 0
    assert {agent["agent_slug"] for agent in store.get_active_roster()} == {
        "independent-agent",
        "revision-agent",
    }
