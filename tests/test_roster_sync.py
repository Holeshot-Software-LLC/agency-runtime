"""Tests for roster source trust and auto-approve sync behavior."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.cli.main import main
from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.roster import ingress as roster_ingress
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


@pytest.fixture(autouse=True)
def _isolated_config_cache() -> Iterator[None]:
    reset_config_cache()
    yield
    reset_config_cache()


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
    source = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))

    assert (
        main(
            [
                "source",
                "add",
                str(source),
                "--name",
                "test",
                "--trusted-for-auto-approve",
            ]
        )
        == 0
    )

    sources = Store().list_agent_sources()
    assert len(sources) == 1
    assert sources[0]["url"] == str(source)
    assert sources[0]["trusted_for_auto_approve"] == 1


def test_auto_approve_rejects_untrusted_sources(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    source = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))
    store = Store()
    store.add_agent_source(str(source), "untrusted")

    assert main(["sync", "--auto-approve"]) == 1

    captured = capsys.readouterr()
    assert "not trusted" in captured.err
    assert Store().get_active_roster_as_catalog() == []


def test_auto_approve_fails_closed_on_source_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    valid = _write_roster(tmp_path / "agents.json", _agent("code-reviewer"))
    missing = tmp_path / "missing.json"
    store = Store()
    store.add_agent_source(str(valid), "valid", trusted_for_auto_approve=True)
    store.add_agent_source(str(missing), "missing", trusted_for_auto_approve=True)

    assert main(["sync", "--auto-approve"]) == 2

    assert Store().get_active_roster_as_catalog() == []


def test_auto_approve_activates_trusted_snapshot_and_prunes_removed_agents(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
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
        old_status = conn.execute(
            "SELECT status FROM agent_candidates WHERE slug = 'old-pending'"
        ).fetchone()["status"]
    finally:
        conn.close()
    assert old_status == "pending"


def test_starter_roster_seed_does_not_overwrite_synced_agents(tmp_path):
    store = Store(tmp_path / "agency.db")
    store.activate_agent(
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "description": "Synced upstream reviewer",
            "source": "trusted-source",
            "hash": "upstream-hash",
        }
    )

    count = seed_starter_roster(store)

    assert count == len(STARTER_ROSTER) - 1
    code_reviewer = next(
        agent for agent in store.get_active_roster() if agent["agent_slug"] == "code-reviewer"
    )
    assert code_reviewer["description"] == "Synced upstream reviewer"
    assert code_reviewer["source"] == "trusted-source"
    assert code_reviewer["hash"] == "upstream-hash"
    assert seed_starter_roster(store) == 0


class _HTTPResponse:
    def __init__(
        self,
        data: bytes,
        content_length: str | None = None,
        *,
        status: int = 200,
        content_type: str = "application/json",
        url: str = "https://example.invalid/agents.json",
    ) -> None:
        self._data = data
        self._offset = 0
        self.status = status
        self.url = url
        self.headers = {"Content-Type": content_type}
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
        chunk = self._data[self._offset : end]
        self._offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self.url


def test_http_source_rejects_declared_oversize_before_read(monkeypatch):
    response = _HTTPResponse(b"[]", content_length="33")
    monkeypatch.setattr(roster_ingress, "MAX_HTTP_SOURCE_BYTES", 32)
    monkeypatch.setattr(roster_ingress, "open_no_redirect", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match="declares 33 bytes"):
        download_from_source("https://example.invalid/agents.json")

    assert response.read_calls == []


def test_http_source_streams_and_rejects_undeclared_oversize(monkeypatch):
    response = _HTTPResponse(b"x" * 33)
    monkeypatch.setattr(roster_ingress, "MAX_HTTP_SOURCE_BYTES", 32)
    monkeypatch.setattr(roster_ingress, "HTTP_READ_CHUNK_BYTES", 7)
    monkeypatch.setattr(roster_ingress, "open_no_redirect", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match="exceeds 32 bytes"):
        download_from_source("https://example.invalid/agents.json")

    assert response.read_calls
    assert max(response.read_calls) <= 7


def test_http_source_enforces_total_deadline_across_slow_reads(monkeypatch):
    clock = [0.0]

    class SlowResponse(_HTTPResponse):
        def read(self, size: int = -1) -> bytes:
            clock[0] += 3.0
            return super().read(size)

    response = SlowResponse(b"[]" * 10)
    monkeypatch.setattr(roster_ingress, "HTTP_READ_CHUNK_BYTES", 2)
    monkeypatch.setattr(roster_ingress, "HTTP_TOTAL_DEADLINE_SECONDS", 5)
    monkeypatch.setattr(roster_ingress, "monotonic", lambda: clock[0])
    monkeypatch.setattr(roster_ingress, "open_no_redirect", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match="total deadline"):
        download_from_source("https://example.invalid/agents.json")

    assert len(response.read_calls) == 2


def test_http_source_preserves_explicit_loopback_and_sanitizes_query_metadata(
    monkeypatch,
):
    url = "http://127.0.0.1:9080/agents.json?token=do-not-persist"
    response = _HTTPResponse(
        json.dumps([_agent("local-reviewer")]).encode(),
        url=url,
    )
    observed = {}

    def open_source(request, *, timeout):
        observed["request"] = request
        observed["timeout"] = timeout
        return response

    monkeypatch.setattr(roster_ingress, "open_no_redirect", open_source)

    agents = download_from_source(url)

    assert [agent["slug"] for agent in agents] == ["local-reviewer"]
    assert agents[0]["source"] == "http://127.0.0.1:9080/agents.json"
    assert agents[0]["prompt_path"] == "http://127.0.0.1:9080/agents.json"
    assert "do-not-persist" not in json.dumps(agents)
    assert observed["request"].get_header("Accept-encoding") == "identity"
    assert observed["request"].get_header("Authorization") is None
    assert observed["timeout"] == roster_ingress.HTTP_TIMEOUT_SECONDS


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("", "may not be empty"),
        ("ftp://example.invalid/agents.json", "unsupported roster source scheme"),
        (
            "https://user:secret@example.invalid/agents.json",
            "may not contain credentials",
        ),
        ("https://example.invalid/agents.json#secret", "may not contain a fragment"),
        ("https://example.invalid:99999/agents.json", "invalid port"),
        ("file://fileserver/share/agents.json", "remote file URL authorities"),
        ("file:////fileserver/share/agents.json", "remote file URL paths"),
        ("https://example.invalid/agents\n.json", "control characters"),
    ],
)
def test_source_spec_rejects_ambiguous_or_credentialed_inputs(source, message):
    with pytest.raises(RosterSyncError, match=message):
        download_from_source(source)


def test_http_network_error_message_redacts_query_and_underlying_detail(monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("transport leaked do-not-show")

    monkeypatch.setattr(roster_ingress, "open_no_redirect", fail)

    with pytest.raises(RosterSyncError) as captured:
        download_from_source("https://example.invalid/private/agents.json?token=super-secret")

    message = str(captured.value)
    assert "https://example.invalid/private/agents.json" in message
    assert "super-secret" not in message
    assert "do-not-show" not in message


@pytest.mark.parametrize(
    ("response_kwargs", "extra_headers", "message"),
    [
        ({"status": 404}, {}, "status 404"),
        ({"content_type": "image/svg+xml"}, {}, "unsupported media type"),
        ({}, {"Content-Encoding": "gzip"}, "unsupported content encoding"),
        ({}, {"Content-Length": "+2"}, "invalid Content-Length"),
        (
            {"url": "https://other.invalid/agents.json"},
            {},
            "changed URL unexpectedly",
        ),
    ],
)
def test_http_response_contract_fails_closed(monkeypatch, response_kwargs, extra_headers, message):
    response = _HTTPResponse(b"[]", **response_kwargs)
    response.headers.update(extra_headers)
    monkeypatch.setattr(roster_ingress, "open_no_redirect", lambda *_args, **_kwargs: response)

    with pytest.raises(RosterSyncError, match=message):
        download_from_source("https://example.invalid/agents.json")


def test_remote_agent_cannot_spoof_source_path_or_content_hash(monkeypatch):
    url = "https://example.invalid/agents.json?signature=secret"
    supplied = {
        **_agent("hash-reviewer"),
        "source": "https://attacker.invalid/",
        "prompt_path": "C:/secret",
        "hash": "0" * 64,
    }
    response = _HTTPResponse(json.dumps([supplied]).encode(), url=url)
    monkeypatch.setattr(roster_ingress, "open_no_redirect", lambda *_args, **_kwargs: response)

    [agent] = download_from_source(url)

    assert agent["source"] == "https://example.invalid/agents.json"
    assert agent["prompt_path"] == "https://example.invalid/agents.json"
    assert agent["hash"] == roster_ingress._hash_text(agent["content"])
    assert agent["hash"] != supplied["hash"]


def test_json_and_yaml_parsers_reject_ambiguous_or_explosive_structures():
    with pytest.raises(RosterSyncError, match="duplicate key"):
        parse_agent_file('{"slug":"agent-one","slug":"agent-two","description":"Useful"}')

    nested = (
        '{"value":' * (roster_ingress.MAX_DOCUMENT_DEPTH + 1)
        + "0"
        + "}" * (roster_ingress.MAX_DOCUMENT_DEPTH + 1)
    )
    with pytest.raises(RosterSyncError, match="nesting depth"):
        parse_agent_file(nested)

    aliased = """---
slug: alias-agent
name: &shared Alias Agent
description: *shared
---
Useful prompt
"""
    with pytest.raises(RosterSyncError, match="aliases"):
        parse_agent_file(aliased)

    duplicate_yaml = """---
slug: first-agent
slug: second-agent
description: Useful
---
Useful prompt
"""
    with pytest.raises(RosterSyncError, match="duplicate mapping key"):
        parse_agent_file(duplicate_yaml)

    merge_yaml = """---
slug: merge-agent
description: Useful
metadata: {<<: {hidden: true}}
---
Useful prompt
"""
    with pytest.raises(RosterSyncError, match="merge keys"):
        parse_agent_file(merge_yaml)

    with pytest.raises(RosterSyncError, match="non-finite number"):
        parse_agent_file(
            '{"slug":"finite-agent","description":"Useful","prompt":"work","weight":NaN}'
        )

    non_finite_yaml = """---
slug: finite-agent
description: Useful
weight: .inf
---
Useful prompt
"""
    with pytest.raises(RosterSyncError, match="non-finite number"):
        parse_agent_file(non_finite_yaml)


def test_agent_metadata_and_list_items_are_bounded(monkeypatch):
    monkeypatch.setattr(roster_ingress, "MAX_SHORT_TEXT_BYTES", 16)
    with pytest.raises(RosterSyncError, match="name is 17 bytes"):
        roster_ingress._normalize_agent(
            {
                **_agent("aa"),
                "division": "eng",
                "name": "12345678901234567",
            }
        )

    monkeypatch.setattr(roster_ingress, "MAX_SHORT_TEXT_BYTES", 512)
    monkeypatch.setattr(roster_ingress, "MAX_LIST_ITEMS", 1)
    with pytest.raises(RosterSyncError, match="more than 1 items"):
        roster_ingress._normalize_agent(
            {
                **_agent("bounded-agent"),
                "capabilities": ["one", "two"],
            }
        )


def test_file_url_is_portable_for_local_sources(tmp_path):
    source = _write_roster(tmp_path / "agents.json", _agent("file-url-agent"))

    agents = download_from_source(source.as_uri())

    assert [agent["slug"] for agent in agents] == ["file-url-agent"]


def test_directory_source_rejects_file_changed_after_discovery(monkeypatch, tmp_path):
    source = tmp_path / "agents"
    source.mkdir()
    agent_file = source / "agent.md"
    agent_file.write_text("# Original Agent\nUseful prompt", encoding="utf-8")
    original = roster_ingress._read_local_file

    def replace_before_read(path, *, expected_fingerprint=None):
        path.write_text("# Replacement Agent\nDifferent and longer prompt", encoding="utf-8")
        return original(path, expected_fingerprint=expected_fingerprint)

    monkeypatch.setattr(roster_ingress, "_read_local_file", replace_before_read)

    with pytest.raises(RosterSyncError, match="changed during discovery"):
        download_from_source(str(source))


def test_local_source_rejects_file_replaced_during_open(monkeypatch, tmp_path):
    source = tmp_path / "agent.md"
    replacement = tmp_path / "replacement.md"
    source.write_text("# Original Agent\nUseful prompt", encoding="utf-8")
    replacement.write_text("# Replacement Agent\nDifferent prompt", encoding="utf-8")
    real_open = roster_ingress.os.open
    replaced = False

    def replace_then_open(path, flags, *args, **kwargs):
        nonlocal replaced
        if not replaced and Path(path) == source:
            replaced = True
            source.unlink()
            replacement.rename(source)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(roster_ingress.os, "open", replace_then_open)

    with pytest.raises(RosterSyncError, match="changed while being opened"):
        download_from_source(str(source))


def test_local_source_rejects_in_place_mutation_while_reading(monkeypatch, tmp_path):
    source = tmp_path / "agent.md"
    source.write_text("# Stable Agent\nUseful prompt", encoding="utf-8")
    real_fstat = roster_ingress.os.fstat
    calls = 0

    def changed_second_fstat(descriptor):
        nonlocal calls
        calls += 1
        metadata = real_fstat(descriptor)
        if calls != 2:
            return metadata
        return SimpleNamespace(
            st_dev=metadata.st_dev,
            st_ino=metadata.st_ino,
            st_mode=metadata.st_mode,
            st_file_attributes=getattr(metadata, "st_file_attributes", 0),
            st_size=metadata.st_size,
            st_mtime=metadata.st_mtime,
            st_mtime_ns=metadata.st_mtime_ns + 1,
        )

    monkeypatch.setattr(roster_ingress.os, "fstat", changed_second_fstat)

    with pytest.raises(RosterSyncError, match="changed while being read"):
        download_from_source(str(source))


@pytest.mark.parametrize(
    "source",
    [
        "https://[malformed/agents.json",
        "local\nsource.json",
        r"\\server\share\agents.json",
        "//server/share/agents.json",
    ],
)
def test_malformed_or_log_injecting_source_is_rejected_safely(source):
    with pytest.raises(RosterSyncError, match=r"malformed|control characters|remote filesystem"):
        download_from_source(source)


def test_local_source_rejects_oversize_before_parse(monkeypatch, tmp_path):
    source = tmp_path / "agent.md"
    source.write_bytes(b"x" * 33)
    monkeypatch.setattr(roster_ingress, "MAX_LOCAL_FILE_BYTES", 32)

    with pytest.raises(RosterSyncError, match="local roster file is 33 bytes"):
        download_from_source(str(source))


def test_directory_source_caps_files_and_total_bytes(monkeypatch, tmp_path):
    (tmp_path / "a.md").write_text("# Alpha\nOne", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Beta\nTwo", encoding="utf-8")
    monkeypatch.setattr(roster_ingress, "MAX_SOURCE_FILES", 1)

    with pytest.raises(RosterSyncError, match="more than 1 agent files"):
        download_from_source(str(tmp_path))

    monkeypatch.setattr(roster_ingress, "MAX_SOURCE_FILES", 2)
    monkeypatch.setattr(roster_ingress, "MAX_TOTAL_SOURCE_BYTES", 12)
    with pytest.raises(RosterSyncError, match="total limit of 12 bytes"):
        download_from_source(str(tmp_path))


def test_directory_source_rejects_deep_recursion(monkeypatch, tmp_path):
    nested = tmp_path / "one" / "two"
    nested.mkdir(parents=True)
    (nested / "agent.md").write_text("# Agent\nPrompt", encoding="utf-8")
    monkeypatch.setattr(roster_ingress, "MAX_DIRECTORY_DEPTH", 1)

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
    monkeypatch.setattr(roster_ingress, "MAX_SOURCE_CANDIDATES", 1)
    monkeypatch.setattr(
        roster_ingress,
        "_normalize_agent",
        lambda _agent: pytest.fail("candidate normalization must not run after count rejection"),
    )

    with pytest.raises(RosterSyncError, match="more than 1 candidates"):
        download_from_source(str(source))


def test_prompt_is_bounded_before_agent_parsing(monkeypatch):
    monkeypatch.setattr(roster_ingress, "MAX_AGENT_PROMPT_BYTES", 4)

    with pytest.raises(RosterSyncError, match="prompt is 5 bytes"):
        parse_agent_file('{"slug":"agent","name":"Agent","description":"Useful","prompt":"12345"}')


def test_snapshot_rechecks_prompt_bound_before_manifest_duplication(monkeypatch, tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("bounded-agent"), source_id, store)
    monkeypatch.setattr(roster_ingress, "MAX_AGENT_PROMPT_BYTES", 4)

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
    assert version["hash"] == roster_ingress._hash_text("original prompt")
    assert activated == 0
    assert {agent["agent_slug"] for agent in store.get_active_roster()} == {
        "independent-agent",
        "revision-agent",
    }


def test_quarantine_requires_enabled_known_source_and_rolls_back_audit_failure(
    monkeypatch, tmp_path
):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    conn = store._connect()
    try:
        conn.execute("UPDATE agent_sources SET enabled = 0 WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RosterSyncError, match="disabled source"):
        quarantine_candidate(_agent("disabled-source-agent"), source_id, store)
    with pytest.raises(RosterSyncError, match="unknown source"):
        quarantine_candidate(_agent("unknown-source-agent"), "missing", store)

    conn = store._connect()
    try:
        conn.execute("UPDATE agent_sources SET enabled = 1 WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        conn.close()

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(roster_sync, "_record_import_event", fail_event)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        quarantine_candidate(_agent("atomic-agent"), source_id, store)

    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_downloads").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_candidates").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_import_events").fetchone()[0] == 0
    finally:
        conn.close()


def test_explicit_snapshot_requires_exact_unique_candidate_ids_and_slugs(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    first = quarantine_candidate(_agent("duplicate-agent"), source_id, store)
    second = quarantine_candidate(_agent("duplicate-agent"), source_id, store)

    with pytest.raises(RosterSyncError, match="candidate ids must be unique"):
        create_roster_diff(store, candidate_ids=[first, first])
    with pytest.raises(RosterSyncError, match="missing or no longer"):
        create_roster_diff(store, candidate_ids=["missing"])
    with pytest.raises(RosterSyncError, match="duplicate agent slug"):
        create_roster_diff(store, candidate_ids=[first, second])


def test_approval_rejects_tampered_quarantine_and_is_fully_atomic(monkeypatch, tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("approval-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])

    def fail_approval_event(_conn, _store, event_type, *_args, **_kwargs):
        if event_type == "snapshot_approved":
            raise RuntimeError("approval audit failed")

    monkeypatch.setattr(roster_sync, "_record_import_event", fail_approval_event)
    with pytest.raises(RuntimeError, match="approval audit failed"):
        approve_snapshot(store, snapshot["snapshot_id"])

    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        persisted = json.loads(
            conn.execute(
                "SELECT manifest FROM agent_snapshots WHERE snapshot_id = ?",
                (snapshot["snapshot_id"],),
            ).fetchone()["manifest"]
        )
    finally:
        conn.close()
    assert row["status"] == "pending"
    assert persisted["approved"] is False

    monkeypatch.undo()
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_downloads SET content = 'tampered' "
            "WHERE id = (SELECT download_id FROM agent_candidates WHERE id = ?)",
            (candidate_id,),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="download content no longer matches"):
        approve_snapshot(store, snapshot["snapshot_id"])


def test_activation_rejects_stale_review_without_mutating_roster(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("reviewed-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, snapshot["snapshot_id"])
    store.activate_agent(_agent("concurrent-agent"))

    with pytest.raises(RosterSyncError, match="different active roster"):
        activate_snapshot(store, snapshot["snapshot_id"])

    assert [row["agent_slug"] for row in store.get_active_roster()] == ["concurrent-agent"]
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
                (snapshot["snapshot_id"],),
            ).fetchone()["activated"]
            == 0
        )
        assert (
            conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()["status"]
            == "approved"
        )
    finally:
        conn.close()


def test_activation_rolls_back_every_projection_when_audit_write_fails(monkeypatch, tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("rollback-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, snapshot["snapshot_id"])

    def fail_activation_event(_conn, _store, event_type, *_args, **_kwargs):
        if event_type == "snapshot_activated":
            raise RuntimeError("activation audit failed")

    monkeypatch.setattr(roster_sync, "_record_import_event", fail_activation_event)
    with pytest.raises(RuntimeError, match="activation audit failed"):
        activate_snapshot(store, snapshot["snapshot_id"])

    assert store.get_active_roster() == []
    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_versions").fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
                (snapshot["snapshot_id"],),
            ).fetchone()["activated"]
            == 0
        )
        assert (
            conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()["status"]
            == "approved"
        )
    finally:
        conn.close()


def test_activation_updates_only_snapshot_downloads_for_duplicate_historical_slug(
    tmp_path,
):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    historical_id = quarantine_candidate(_agent("shared-agent"), source_id, store)
    selected_id = quarantine_candidate(_agent("shared-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[selected_id])
    approve_snapshot(store, snapshot["snapshot_id"])
    activate_snapshot(store, snapshot["snapshot_id"])

    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT c.id, c.status AS candidate_status, d.status AS download_status "
            "FROM agent_candidates c JOIN agent_downloads d ON d.id = c.download_id "
            "WHERE c.id IN (?, ?)",
            (historical_id, selected_id),
        ).fetchall()
    finally:
        conn.close()
    statuses = {row["id"]: (row["candidate_status"], row["download_status"]) for row in rows}
    assert statuses[historical_id] == ("pending", "quarantined")
    assert statuses[selected_id] == ("activated", "activated")


def test_existing_version_content_is_verified_even_when_hash_column_matches(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    first_snapshot = _approved_snapshot(store, source_id, "stable prompt")
    activate_snapshot(store, first_snapshot)
    second_snapshot = _approved_snapshot(store, source_id, "stable prompt")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = 'corrupted content' "
            "WHERE agent_slug = 'revision-agent' AND version = '1.0.0'"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RosterSyncError, match="immutable agent version"):
        activate_snapshot(store, second_snapshot)

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
                (second_snapshot,),
            ).fetchone()["activated"]
            == 0
        )
    finally:
        conn.close()


def test_repeated_activation_is_idempotent_and_does_not_duplicate_audit_event(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    snapshot_id = _approved_snapshot(store, source_id, "stable prompt")

    activate_snapshot(store, snapshot_id)
    activate_snapshot(store, snapshot_id)

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'snapshot_activated' AND detail = ?",
                (snapshot_id,),
            ).fetchone()[0]
            == 1
        )
        assert conn.execute("SELECT COUNT(*) FROM agent_versions").fetchone()[0] == 1
    finally:
        conn.close()


def test_approval_rejects_tampered_snapshot_candidate_mapping(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("manifest-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    conn = store._connect()
    try:
        manifest = json.loads(
            conn.execute(
                "SELECT manifest FROM agent_snapshots WHERE snapshot_id = ?",
                (snapshot["snapshot_id"],),
            ).fetchone()["manifest"]
        )
        manifest["candidate_ids"] = []
        conn.execute(
            "UPDATE agent_snapshots SET manifest = ? WHERE snapshot_id = ?",
            (json.dumps(manifest), snapshot["snapshot_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RosterSyncError, match="candidate ids do not match"):
        approve_snapshot(store, snapshot["snapshot_id"])

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()["status"]
            == "pending"
        )
    finally:
        conn.close()


def test_approval_rejects_tampered_download_state(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("state-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_downloads SET status = 'rejected' "
            "WHERE id = (SELECT download_id FROM agent_candidates WHERE id = ?)",
            (candidate_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RosterSyncError, match="download is not in an allowed state"):
        approve_snapshot(store, snapshot["snapshot_id"])

    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()["status"]
            == "pending"
        )
    finally:
        conn.close()


def test_snapshot_rejects_invalid_persisted_activation_state(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("state-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_snapshots SET activated = 2 WHERE snapshot_id = ?",
            (snapshot["snapshot_id"],),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RosterSyncError, match="activation state is invalid"):
        approve_snapshot(store, snapshot["snapshot_id"])


def test_activation_rebuilds_category_projection_without_stale_values(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    initial = {**_agent("category-agent"), "categories": ["code", "security"]}
    initial_id = quarantine_candidate(initial, source_id, store)
    initial_snapshot = create_roster_diff(store, candidate_ids=[initial_id])
    approve_snapshot(store, initial_snapshot["snapshot_id"])
    activate_snapshot(store, initial_snapshot["snapshot_id"])

    replacement = {**_agent("category-agent"), "categories": ["code"]}
    replacement_id = quarantine_candidate(replacement, source_id, store)
    replacement_snapshot = create_roster_diff(store, candidate_ids=[replacement_id])
    approve_snapshot(store, replacement_snapshot["snapshot_id"])
    activate_snapshot(store, replacement_snapshot["snapshot_id"])

    conn = store._connect()
    try:
        categories = conn.execute(
            "SELECT category FROM agent_categories "
            "WHERE agent_slug = 'category-agent' ORDER BY category"
        ).fetchall()
    finally:
        conn.close()
    assert [row["category"] for row in categories] == ["code"]
