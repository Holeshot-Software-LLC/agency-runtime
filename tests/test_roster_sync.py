"""Tests for roster source trust and auto-approve sync behavior."""

from __future__ import annotations

import json
import stat
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands
from agency_runtime.cli.main import main
from agency_runtime.core.config import AgencyConfig, OllamaConfig, reset_config_cache
from agency_runtime.core.installer import seed_starter_roster
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.roster import ingress as roster_ingress
from agency_runtime.core.roster import remediation as roster_remediation
from agency_runtime.core.roster import sync as roster_sync
from agency_runtime.core.roster.sync import (
    RosterSyncError,
    activate_snapshot,
    approve_snapshot,
    create_retirement_diff,
    create_roster_diff,
    download_from_source,
    list_source_scans,
    parse_agent_file,
    quarantine_candidate,
    quarantine_manifest_import,
)
from agency_runtime.core.store.sqlite import Store


@pytest.fixture(autouse=True)
def _isolated_config_cache() -> Iterator[None]:
    reset_config_cache()
    yield
    reset_config_cache()


def _governed_payload(
    slug: str,
    description: str,
    *,
    prompt: str | None = None,
    categories: list[str] | None = None,
) -> dict[str, object]:
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": description,
        "division": "engineering",
        "categories": categories or ["engineering", "testing"],
        "capabilities": ["perform bounded fixture work"],
        "anti_capabilities": ["claim unverified completion"],
        "task_types": ["review"],
        "preferred_when": ["the bounded fixture matches"],
        "avoid_when": ["required evidence is unavailable"],
        "required_tools": [],
        "tool_affinity": [],
        "supported_hosts": ["codex"],
        "supported_platforms": ["linux", "windows"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": f"fixture-{slug}",
        "expected_output_contract": "Return bounded evidence-backed fixture output.",
        "evidence_requirements": ["cite the fixture result"],
        "model_requirements": ["instruction-adherence"],
        "source_revision": "test-revision",
        "audit_revision": "test",
        "audit_status": "approved",
        "findings": [],
        "prompt_body": prompt or f"You are {slug}, a useful specialist.",
    }


def _agent(
    slug: str,
    description: str = "Useful specialist",
    *,
    prompt: str | None = None,
    categories: list[str] | None = None,
) -> dict[str, object]:
    payload = _governed_payload(
        slug,
        description,
        prompt=prompt,
        categories=categories,
    )
    return {**payload, "content": json.dumps(payload, sort_keys=True, separators=(",", ":"))}


def _governed_markdown(
    slug: str,
    description: str,
    prompt: str,
    *,
    categories: list[str] | None = None,
) -> str:
    payload = _governed_payload(
        slug,
        description,
        prompt=prompt,
        categories=categories,
    )
    front_matter = "\n".join(
        f"{key}: {json.dumps(value)}" for key, value in payload.items() if key != "prompt_body"
    )
    return f"---\n{front_matter}\n---\n{prompt}\n"


def _write_roster(path: Path, *agents: dict[str, object]) -> Path:
    path.write_text(json.dumps(list(agents)), encoding="utf-8")
    return path


def test_documented_example_roster_passes_governed_approval_gate(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "examples" / "rosters" / "agents.json"
    downloaded = download_from_source(str(source))
    assert [agent["slug"] for agent in downloaded] == [
        "example-code-reviewer",
        "example-technical-writer",
    ]
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "documented-example")
    candidate_ids = [quarantine_candidate(agent, source_id, store) for agent in downloaded]
    snapshot = create_roster_diff(store, candidate_ids=candidate_ids)

    approve_snapshot(store, snapshot["snapshot_id"])


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


def test_auto_approve_activates_trusted_delta_and_preserves_unrelated_agents(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    monkeypatch.setattr(
        roster_commands,
        "load_config",
        lambda: AgencyConfig(ollama=OllamaConfig(enabled=False, model="")),
    )
    source = _write_roster(tmp_path / "agents.json", _agent("new-specialist"))
    store = Store()
    store._activate_prevalidated_agent(_agent("obsolete-specialist"))
    store.add_agent_source(str(source), "trusted", trusted_for_auto_approve=True)

    assert main(["sync", "--auto-approve"]) == 0

    roster = Store().get_active_roster_as_catalog()
    assert [agent["slug"] for agent in roster] == [
        "new-specialist",
        "obsolete-specialist",
    ]
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
    monkeypatch.setattr(
        roster_commands,
        "load_config",
        lambda: AgencyConfig(ollama=OllamaConfig(enabled=False, model="")),
    )
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
    source_id = store.add_agent_source("trusted-source", "trusted")
    candidate_id = quarantine_candidate(
        {
            **_agent("code-reviewer", "Synced upstream reviewer"),
            "source": "trusted-source",
        },
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, snapshot["snapshot_id"])
    activate_snapshot(store, snapshot["snapshot_id"])
    before = store.get_roster_entry("code-reviewer")

    count = seed_starter_roster(store)

    assert count == len(STARTER_ROSTER) - 1
    code_reviewer = next(
        agent for agent in store.get_active_roster() if agent["agent_slug"] == "code-reviewer"
    )
    assert code_reviewer["description"] == "Synced upstream reviewer"
    assert code_reviewer["source"] == "trusted-source"
    assert code_reviewer["hash"] == before["hash"]
    assert code_reviewer["version"] == before["version"]
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


@pytest.mark.parametrize(
    "query",
    [
        "token=PLANTED_TOKEN_QUERY",
        "key=PLANTED_KEY_QUERY",
        "api_key=PLANTED_API_KEY_QUERY",
        "signature=PLANTED_SIGNATURE_QUERY",
        "unrecognized=PLANTED_ARBITRARY_QUERY",
    ],
)
def test_http_source_keeps_query_auth_at_the_content_free_fetch_boundary(
    monkeypatch,
    query,
):
    url = f"http://127.0.0.1:9080/agents.json?{query}"
    secret = query.partition("=")[2]
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
    public_result = {
        "agents": list(agents),
        "outcomes": [outcome.public_dict() for outcome in agents.outcomes],
    }
    assert secret not in json.dumps(public_result)
    assert observed["request"].full_url == url
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


@pytest.mark.parametrize(
    "source",
    [
        "file:////fileserver/share/agents.json",
        "file:/%5cserver/share/agents.json",
        "file:%5c/server/share/agents.json",
        "file:/\\\\server/share/agents.json",
    ],
)
def test_remote_file_url_path_is_rejected_before_platform_conversion(monkeypatch, source):
    def unexpected_conversion(_path):
        raise AssertionError("remote file paths must be rejected before conversion")

    monkeypatch.setattr(
        roster_ingress.urllib.request,
        "url2pathname",
        unexpected_conversion,
    )

    with pytest.raises(RosterSyncError, match="remote file URL paths"):
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


def test_manifest_directory_imports_only_declared_agents_and_infers_identity(tmp_path):
    (tmp_path / "engineering").mkdir()
    (tmp_path / "support").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / "integrations").mkdir()
    (tmp_path / "divisions.json").write_text(
        json.dumps(
            {
                "_note": "Only these source divisions contain agents.",
                "divisions": {
                    "support": {"label": "Support"},
                    "engineering": {"label": "Engineering"},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "engineering" / "api-data.md").write_text(
        """---
name: API & Data_Engineer++
description: Designs dependable data APIs: secure, observable, and maintainable.
---
Build secure, observable data services.
""",
        encoding="utf-8",
    )
    (tmp_path / "engineering" / "explicit.md").write_text(
        """---
slug: operator-owned
name: Explicit Agent
description: Keeps explicit metadata.
division: custom
---
Preserve explicit identity fields.
""",
        encoding="utf-8",
    )
    (tmp_path / "support" / "bundle.json").write_text(
        json.dumps(
            [
                {
                    "name": "Support Responder",
                    "description": "Resolves customer incidents.",
                    "body": "Triage and resolve the support request.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "engineering" / "QUICKSTART.md").write_text(
        "# Not an agent\nThis documentation has no front matter.",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Catalog documentation", encoding="utf-8")
    (tmp_path / "examples" / "example.md").write_text(
        """---
name: Example Output
description: Must not be imported.
---
This is an orchestration example, not an agent.
""",
        encoding="utf-8",
    )
    _write_roster(tmp_path / "integrations" / "converted.json", _agent("converted-copy"))

    agents = download_from_source(str(tmp_path))

    assert {
        agent["slug"]: (agent["division"], Path(agent["prompt_path"]).name) for agent in agents
    } == {
        "api-data-engineer": ("engineering", "api-data.md"),
        "operator-owned": ("custom", "explicit.md"),
        "support-responder": ("support", "bundle.json"),
    }
    assert all(agent["source"] == str(tmp_path) for agent in agents)
    assert [
        (outcome.status, outcome.relative_path, outcome.slug) for outcome in agents.outcomes
    ] == [
        ("candidate", "engineering/api-data.md", "api-data-engineer"),
        ("candidate", "engineering/explicit.md", "operator-owned"),
        ("ignored", "engineering/QUICKSTART.md", ""),
        ("candidate", "support/bundle.json", "support-responder"),
    ]
    assert (
        next(agent for agent in agents if agent["slug"] == "api-data-engineer")["description"]
        == "Designs dependable data APIs: secure, observable, and maintainable."
    )


def test_manifest_agent_flat_front_matter_fallback_is_bounded_and_context_scoped(
    monkeypatch,
):
    content = """---
name: Developer Tooling Engineer
description: Builds developer platforms with great DX: intuitive commands and errors.
color: "#4F46E5"

---
Build dependable command-line tools.
"""
    agent = parse_agent_file(content, inferred_division="engineering")
    assert agent["slug"] == "developer-tooling-engineer"
    assert agent["division"] == "engineering"
    assert agent["description"].endswith("intuitive commands and errors.")

    with pytest.raises(RosterSyncError, match="YAML is not valid bounded data"):
        parse_agent_file(content)

    malformed_fields = (
        "missing separator",
        " nested: value",
        "not.valid: value",
        "empty:",
        "anchor: &shared",
        "name: Agent\nname: Duplicate",
    )
    for fields in malformed_fields:
        with pytest.raises(RosterSyncError, match="front matter"):
            roster_ingress._load_flat_front_matter(fields, "front matter")

    with pytest.raises(RosterSyncError, match="must not be empty"):
        roster_ingress._load_flat_front_matter("\n", "front matter")

    monkeypatch.setattr(roster_ingress, "MAX_LIST_ITEMS", 1)
    with pytest.raises(RosterSyncError, match="more than 1 fields"):
        roster_ingress._load_flat_front_matter("one: value\ntwo: value", "front matter")

    monkeypatch.setattr(roster_ingress, "MAX_LIST_ITEMS", 256)
    monkeypatch.setattr(roster_ingress, "MAX_METADATA_TEXT_BYTES", 4)
    with pytest.raises(RosterSyncError, match="field name is 5 bytes"):
        roster_ingress._load_flat_front_matter("name: Agent", "front matter")


def test_manifest_ingress_edge_outcomes_remain_bounded_and_fail_closed():
    source_document = roster_ingress._SourceDocument(
        "root/engineering/agent.md",
        "plain source",
        "engineering",
        "engineering/agent.md",
    )
    assert list(source_document) == [
        "root/engineering/agent.md",
        "plain source",
    ]
    assert roster_ingress._manifest_slug_hint("plain", "odd.name.md") == "odd-name"
    assert roster_ingress._manifest_slug_hint("plain", "---") == (
        "invalid-agent-" + roster_ingress._hash_text("---")[:12]
    )
    assert roster_ingress._manifest_slug_hint("---\n---\nPrompt", "fallback.md") == "fallback"
    assert (
        roster_ingress._manifest_slug_hint(
            "---\ndescription: No name\ncolor: blue\n---\nPrompt",
            "described.md",
        )
        == "described"
    )
    assert roster_ingress._manifest_finding("safe", ValueError("bad shape")) == (
        "invalid_agent:ValueError:bad shape"
    )

    accumulator = roster_ingress._DownloadAccumulator("source")
    accumulator._quarantine(source_document, ValueError("bad shape"))
    accumulator._quarantine(source_document, ValueError("bad shape"))
    assert len(accumulator.outcomes) == 1

    invalid_candidate_document = replace(
        source_document,
        origin="root/engineering/invalid.md",
        relative_path="engineering/invalid.md",
    )
    accumulator._append(
        {
            "slug": "x",
            "name": "X",
            "description": "Too-short slug.",
            "prompt_body": "Prompt.",
            "content": "Prompt.",
        },
        invalid_candidate_document,
    )
    assert accumulator.outcomes[-1].status == "quarantined"
    assert accumulator.outcomes[-1].finding.startswith("invalid_agent:slug must")

    malformed_json = replace(
        source_document,
        origin="root/engineering/malformed.json",
        relative_path="engineering/malformed.json",
    )
    accumulator._ingest_json(malformed_json, "{}")
    invalid_item = replace(
        malformed_json,
        origin="root/engineering/item.json",
        relative_path="engineering/item.json",
    )
    accumulator._ingest_json(invalid_item, "[1]")
    assert [outcome.status for outcome in accumulator.outcomes[-2:]] == [
        "quarantined",
        "quarantined",
    ]

    generic = roster_ingress._SourceDocument("generic.json", "{}")
    with pytest.raises(ValueError, match="must be a list"):
        accumulator._ingest_json(generic, "{}")
    with pytest.raises(ValueError, match="empty agent file"):
        accumulator._ingest_agent(roster_ingress._SourceDocument("empty.md", " "))

    invalid_flat_fallback = """---
name: Agent
description: Invalid YAML: forces the flat fallback.
 nested: rejected
---
Prompt.
"""
    with pytest.raises(RosterSyncError, match="YAML is not valid bounded data"):
        parse_agent_file(
            invalid_flat_fallback,
            inferred_division="engineering",
        )


@pytest.mark.parametrize(
    ("manifest", "reason"),
    [
        ("[]", "must be an object"),
        ("{}", "non-empty divisions object"),
        ('{"divisions":[]}', "non-empty divisions object"),
        ('{"divisions":{}}', "non-empty divisions object"),
        ('{"divisions":{"engineering":[]}}', "entry must be an object"),
        ('{"divisions":{"../escape":{}}}', "unsafe division name"),
        (
            '{"divisions":{"engineering":{},"engineering":{}}}',
            "duplicate key",
        ),
    ],
)
def test_manifest_directory_fails_closed_on_malformed_manifest(
    tmp_path,
    manifest,
    reason,
):
    (tmp_path / "engineering").mkdir()
    (tmp_path / "divisions.json").write_text(manifest, encoding="utf-8")

    with pytest.raises(RosterSyncError, match=reason):
        download_from_source(str(tmp_path))


def test_manifest_directory_rejects_missing_and_oversize_manifests(monkeypatch, tmp_path):
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"missing":{}}}',
        encoding="utf-8",
    )
    with pytest.raises(RosterSyncError, match="path is unavailable"):
        download_from_source(str(tmp_path))

    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (tmp_path / "engineering").mkdir()
    monkeypatch.setattr(roster_ingress, "MAX_DIVISION_MANIFEST_BYTES", 8)
    with pytest.raises(RosterSyncError, match=r"division manifest is .* bytes"):
        download_from_source(str(tmp_path))


def test_manifest_directory_rejects_duplicate_derived_agent_slugs(tmp_path):
    for division in ("engineering", "support"):
        path = tmp_path / division
        path.mkdir()
        (path / "agent.md").write_text(
            """---
name: Shared Specialist
description: A colliding agent identity.
---
Do specialist work.
""",
            encoding="utf-8",
        )
    (tmp_path / "divisions.json").write_text(
        json.dumps({"divisions": {"engineering": {}, "support": {}}}),
        encoding="utf-8",
    )

    with pytest.raises(RosterSyncError, match="duplicate agent slug 'shared-specialist'"):
        download_from_source(str(tmp_path))


def test_manifest_directory_quarantines_an_unsafe_agent_with_exact_evidence(tmp_path):
    division = tmp_path / "engineering"
    division.mkdir()
    corrupt = division / "corrupt-agent.md"
    corrupt.write_text(
        """---
name: Corrupt Agent
description: Contains an unsafe prompt byte.
---
Unsafe \x04 prompt.
""",
        encoding="utf-8",
    )
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )

    downloaded = download_from_source(str(tmp_path))

    assert downloaded == []
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    assert outcome.relative_path == "engineering/corrupt-agent.md"
    assert outcome.slug == "corrupt-agent"
    byte_offset = corrupt.read_bytes().find(b"\x04")
    assert outcome.finding == f"unsafe_control:U+0004x1@{byte_offset}"
    assert outcome.content == corrupt.read_bytes().decode("utf-8")
    assert outcome.content_hash == roster_ingress._hash_text(outcome.content)


@pytest.mark.parametrize(
    ("body", "finding"),
    [
        ("Unknown \x80 C1 corruption.", "unsafe_control:U+0080x1"),
        (
            "## =' Platform Integrations\nUnknown mojibake marker.",
            "suspicious_source_encoding:markdown_heading_mojibake",
        ),
        ("## ðŸš€ Feature", "suspicious_source_encoding:markdown_heading_mojibake"),
        ("## â€” Plan", "suspicious_source_encoding:markdown_heading_mojibake"),
        ("## Ã¢ Broken", "suspicious_source_encoding:markdown_heading_mojibake"),
        ("Replacement \ufffd marker", "suspicious_source_encoding:markdown_heading_mojibake"),
        ("Embedded \ufeff BOM", "unsafe_control:U+FEFFx1"),
    ],
)
def test_manifest_directory_quarantines_unknown_encoding_without_guessing(
    tmp_path,
    body,
    finding,
):
    division = tmp_path / "engineering"
    division.mkdir()
    source = division / "unknown-encoding.md"
    source.write_text(
        f"---\nname: Unknown Encoding\ndescription: Must remain quarantined.\n---\n{body}\n",
        encoding="utf-8",
    )
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )

    downloaded = download_from_source(str(tmp_path))

    assert downloaded == []
    [outcome] = downloaded.outcomes
    assert outcome.status == "quarantined"
    expected = finding
    if "\x80" in body or "\ufeff" in body:
        control = "\x80" if "\x80" in body else "\ufeff"
        expected += f"@{source.read_bytes().find(control.encode('utf-8'))}"
    assert outcome.finding == expected
    assert outcome.content == source.read_bytes().decode("utf-8")


def test_manifest_ingress_scans_each_document_once(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
):
    division = tmp_path / "engineering"
    division.mkdir()
    source = division / "unsafe.md"
    source.write_text(
        "---\nname: Unsafe\ndescription: Must remain quarantined.\n---\nInvisible \u202e marker.\n",
        encoding="utf-8",
    )
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    calls = 0
    original = roster_ingress.scan_source_text

    def counted_scan(content: str):
        nonlocal calls
        calls += 1
        return original(content)

    monkeypatch.setattr(roster_ingress, "scan_source_text", counted_scan)

    downloaded = download_from_source(str(tmp_path))

    assert downloaded == []
    assert downloaded.outcomes[0].finding.startswith("unsafe_control:U+202E")
    assert calls == 1


def test_manifest_directory_accepts_legitimate_accented_prose(tmp_path):
    division = tmp_path / "marketing"
    division.mkdir()
    (division / "accented.md").write_bytes(
        (
            "---\nname: Accented Reviewer\ndescription: Reviews localized prose.\n---\n"
            "## À propos\n## Équipe\n"
            "José reviewed São Paulo, a naïve café phrase, and the word Âge.\n"
        ).encode()
    )
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"marketing":{}}}',
        encoding="utf-8",
    )

    downloaded = download_from_source(str(tmp_path))

    assert [agent["slug"] for agent in downloaded] == ["accented-reviewer"]
    assert downloaded.outcomes[0].status == "candidate"


@pytest.mark.parametrize(
    "content",
    [
        '{"slug":"c1-json","description":"bad \\u0080","content":"bad \\u0080"}',
        "---\nname: C1 YAML\ndescription: bad \x80\n---\nPrompt",
        "# C1 Markdown\nBad \x80 prompt",
    ],
)
def test_single_agent_parsers_reject_c1_controls(content):
    with pytest.raises(RosterSyncError, match="unsafe control character"):
        parse_agent_file(content)


def test_manifest_partial_quarantine_is_atomic_idempotent_and_never_activates_rejects(
    tmp_path,
):
    source = tmp_path / "catalog"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "valid.md").write_text(
        _governed_markdown(
            "valid-builder",
            "Builds valid systems.",
            "Build the requested system.",
        ),
        encoding="utf-8",
    )
    corrupt = division / "corrupt.md"
    corrupt.write_text(
        """---
name: Corrupt Builder
description: Contains upstream corruption.
---
Broken \x04 heading and another \x04 marker.
""",
        encoding="utf-8",
    )
    (division / "README.md").write_text("# Division notes", encoding="utf-8")
    downloaded = download_from_source(str(source))
    assert [agent["slug"] for agent in downloaded] == ["valid-builder"]
    assert {(outcome.relative_path, outcome.status) for outcome in downloaded.outcomes} == {
        ("engineering/corrupt.md", "quarantined"),
        ("engineering/README.md", "ignored"),
        ("engineering/valid.md", "candidate"),
    }

    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "manifest")
    store._activate_prevalidated_agent(
        {
            **_agent("corrupt-builder"),
            "source_id": source_id,
            "source": str(source),
        }
    )
    store._activate_prevalidated_agent(_agent("unrelated-agent"))
    first_ids, first_outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    second_ids, second_outcomes = quarantine_manifest_import(
        downloaded,
        downloaded.outcomes,
        source_id,
        store,
    )
    assert second_ids == first_ids
    assert second_outcomes == first_outcomes

    conn = store._connect()
    try:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "agent_downloads",
                "agent_candidates",
                "agent_import_events",
            )
        }
        rejected = conn.execute(
            "SELECT d.content, d.hash, d.status "
            "FROM agent_downloads d "
            "LEFT JOIN agent_candidates c ON c.download_id = d.id "
            "WHERE c.id IS NULL"
        ).fetchone()
        event_types = {
            row["event_type"]
            for row in conn.execute("SELECT event_type FROM agent_import_events").fetchall()
        }
    finally:
        conn.close()
    assert counts == {
        "agent_downloads": 2,
        "agent_candidates": 1,
        "agent_import_events": 5,
    }
    assert rejected["content"] == corrupt.read_bytes().decode("utf-8")
    assert rejected["hash"] == roster_ingress._hash_text(rejected["content"])
    assert rejected["status"] == "quarantined"
    assert event_types == {
        "candidate_quarantined",
        "manifest_entry_ignored",
        "manifest_entry_quarantined",
        "manifest_entry_remediation_queued",
        "source_scan_recorded",
    }

    diff = create_roster_diff(store, candidate_ids=first_ids)
    approve_snapshot(store, diff["snapshot_id"])
    activate_snapshot(store, diff["snapshot_id"])
    assert [row["agent_slug"] for row in store.get_active_roster()] == [
        "corrupt-builder",
        "unrelated-agent",
        "valid-builder",
    ]
    assert list_source_scans(store)[0]["status"] == "partial"
    conn = store._connect()
    try:
        rejected_status = conn.execute(
            "SELECT d.status FROM agent_downloads d "
            "LEFT JOIN agent_candidates c ON c.download_id = d.id "
            "WHERE c.id IS NULL"
        ).fetchone()["status"]
    finally:
        conn.close()
    assert rejected_status == "quarantined"


def test_manifest_partial_quarantine_rolls_back_the_entire_batch(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "catalog"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "valid.md").write_text(
        """---
name: Valid Agent
description: Valid candidate.
---
Valid prompt.
""",
        encoding="utf-8",
    )
    (division / "corrupt.md").write_text(
        """---
name: Corrupt Agent
description: Invalid candidate.
---
Invalid \x04 prompt.
""",
        encoding="utf-8",
    )
    downloaded = download_from_source(str(source))
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "manifest")

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("event write failed")

    monkeypatch.setattr(roster_sync, "_record_import_event", fail_event)
    with pytest.raises(RuntimeError, match="event write failed"):
        quarantine_manifest_import(
            downloaded,
            downloaded.outcomes,
            source_id,
            store,
        )

    conn = store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_downloads").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_candidates").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM agent_import_events").fetchone()[0] == 0
    finally:
        conn.close()


def test_manifest_batch_validation_rejects_inconsistent_or_unbounded_evidence(
    monkeypatch,
):
    agent = roster_ingress._normalize_agent(_agent("valid-agent"))
    candidate = roster_ingress.ManifestImportOutcome(
        status="candidate",
        origin="root/engineering/valid.md",
        relative_path="engineering/valid.md",
        slug="valid-agent",
        content_hash=agent["hash"],
        finding="candidate_ready",
    )
    rejected_content = "unsafe \x04 content"
    rejected = roster_ingress.ManifestImportOutcome(
        status="quarantined",
        origin="root/engineering/rejected.md",
        relative_path="engineering/rejected.md",
        slug="rejected-agent",
        content_hash=roster_ingress._hash_text(rejected_content),
        finding="unsafe_control:U+0004x1",
        content=rejected_content,
        remediation_attempt=roster_remediation.remediation_attempt(
            rejected_content,
            "unsafe_control:U+0004x1",
        ),
    )
    ignored = roster_ingress.ManifestImportOutcome(
        status="ignored",
        origin="root/engineering/README.md",
        relative_path="engineering/README.md",
        slug="",
        content_hash=roster_ingress._hash_text("# Notes"),
        finding="not_agent_definition:missing_front_matter",
    )

    with monkeypatch.context() as context:
        context.setattr(roster_sync, "MAX_SOURCE_CANDIDATES", 0)
        with pytest.raises(RosterSyncError, match="more than 0 candidates"):
            roster_sync._validated_manifest_batch([agent], [candidate])
    with pytest.raises(RosterSyncError, match="invalid manifest candidate"):
        roster_sync._validated_manifest_batch(
            [{**agent, "description": ""}],
            [candidate],
        )
    with pytest.raises(RosterSyncError, match="duplicate agent slug"):
        roster_sync._validated_manifest_batch([agent, agent], [candidate])

    validation_sets = {
        "candidates_by_slug": {"valid-agent": agent},
        "candidate_outcome_slugs": set(),
        "quarantined_entries": set(),
    }
    with pytest.raises(RosterSyncError, match="invalid type"):
        roster_sync._validate_manifest_outcome(object(), **validation_sets)
    with pytest.raises(RosterSyncError, match="invalid status"):
        roster_sync._validate_manifest_outcome(
            replace(candidate, status="unknown"),
            **validation_sets,
        )
    with pytest.raises(RosterSyncError, match="unsafe relative path"):
        roster_sync._validate_manifest_outcome(
            replace(candidate, relative_path="../escape.md"),
            **validation_sets,
        )
    with pytest.raises(RosterSyncError, match="hash is invalid"):
        roster_sync._validate_manifest_outcome(
            replace(candidate, content_hash="bad"),
            **validation_sets,
        )
    with pytest.raises(RosterSyncError, match="does not match its candidate"):
        roster_sync._validate_manifest_outcome(
            replace(candidate, slug="other-agent"),
            **validation_sets,
        )
    with pytest.raises(RosterSyncError, match="may not carry source content"):
        roster_sync._validate_manifest_outcome(
            replace(ignored, content="# Notes"),
            **validation_sets,
        )
    with pytest.raises(RosterSyncError, match="content hash does not match"):
        roster_sync._validate_manifest_outcome(
            replace(rejected, content="changed"),
            **validation_sets,
        )
    duplicate_identity = {
        (
            rejected.relative_path,
            rejected.slug,
            rejected.content_hash,
        )
    }
    with pytest.raises(RosterSyncError, match="duplicate quarantined outcomes"):
        roster_sync._validate_manifest_outcome(
            rejected,
            candidates_by_slug={"valid-agent": agent},
            candidate_outcome_slugs=set(),
            quarantined_entries=duplicate_identity,
        )

    with monkeypatch.context() as context:
        context.setattr(roster_sync, "MAX_SOURCE_CANDIDATES", 0)
        context.setattr(roster_sync, "MAX_SOURCE_FILES", 0)
        with pytest.raises(RosterSyncError, match="too many entry outcomes"):
            roster_sync._validated_manifest_batch([], [ignored])
    with pytest.raises(RosterSyncError, match="candidates and entry outcomes"):
        roster_sync._validated_manifest_batch([agent], [])
    with monkeypatch.context() as context:
        context.setattr(roster_sync, "MAX_TOTAL_SOURCE_BYTES", 0)
        with pytest.raises(RosterSyncError, match="manifest import content"):
            roster_sync._validated_manifest_batch([agent], [candidate])


def test_manifest_batch_rejects_unknown_and_disabled_sources(tmp_path):
    agent = roster_ingress._normalize_agent(_agent("valid-agent"))
    candidate = roster_ingress.ManifestImportOutcome(
        status="candidate",
        origin="root/engineering/valid.md",
        relative_path="engineering/valid.md",
        slug="valid-agent",
        content_hash=agent["hash"],
        finding="candidate_ready",
    )
    store = Store(tmp_path / "agency.db")
    with pytest.raises(RosterSyncError, match="unknown source"):
        quarantine_manifest_import([agent], [candidate], "missing", store)

    source_id = store.add_agent_source("source", "source")
    conn = store._connect()
    try:
        conn.execute("UPDATE agent_sources SET enabled = 0 WHERE id = ?", (source_id,))
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="disabled source"):
        quarantine_manifest_import([agent], [candidate], source_id, store)


def test_manifest_rejection_evidence_is_path_specific_and_tamper_evident(tmp_path):
    def rejected(path, content):
        finding = "unsafe_control:U+0004x1"
        return roster_ingress.ManifestImportOutcome(
            status="quarantined",
            origin=f"root/{path}",
            relative_path=path,
            slug="same-agent",
            content_hash=roster_ingress._hash_text(content),
            finding=finding,
            content=content,
            remediation_attempt=roster_remediation.remediation_attempt(content, finding),
        )

    path_store = Store(tmp_path / "paths.db")
    path_source = path_store.add_agent_source("path-source", "path-source")
    first = rejected("engineering/first.md", "first \x04")
    second = rejected("engineering/second.md", "second \x04")
    quarantine_manifest_import([], [first], path_source, path_store)
    quarantine_manifest_import([], [second], path_source, path_store)
    conn = path_store._connect()
    try:
        assert conn.execute("SELECT COUNT(*) FROM agent_downloads").fetchone()[0] == 2
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_quarantined'"
            ).fetchone()[0]
            == 2
        )
    finally:
        conn.close()

    tamper_store = Store(tmp_path / "tamper.db")
    tamper_source = tamper_store.add_agent_source("tamper-source", "tamper-source")
    quarantine_manifest_import([], [first], tamper_source, tamper_store)
    conn = tamper_store._connect()
    try:
        conn.execute(
            "UPDATE agent_downloads SET content = 'tampered' WHERE source_id = ?",
            (tamper_source,),
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="evidence is incomplete or tampered"):
        quarantine_manifest_import([], [first], tamper_source, tamper_store)

    event_store = Store(tmp_path / "event.db")
    event_source = event_store.add_agent_source("event-source", "event-source")
    quarantine_manifest_import([], [first], event_source, event_store)
    conn = event_store._connect()
    try:
        conn.execute(
            "UPDATE agent_import_events SET detail = '[]' "
            "WHERE event_type = 'manifest_entry_quarantined'"
        )
        conn.commit()
    finally:
        conn.close()
    with pytest.raises(RosterSyncError, match="evidence is incomplete or tampered"):
        quarantine_manifest_import([], [first], event_source, event_store)


def test_cli_collects_manifest_outcomes_without_turning_rejections_into_errors(
    monkeypatch,
    tmp_path,
):
    source = tmp_path / "catalog"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    (division / "valid.md").write_text(
        """---
name: Valid Agent
description: Valid candidate.
---
Valid prompt.
""",
        encoding="utf-8",
    )
    (division / "corrupt.md").write_text(
        """---
name: Corrupt Agent
description: Invalid candidate.
---
Invalid \x04 prompt.
""",
        encoding="utf-8",
    )
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "manifest")
    source_row = {"id": source_id, "url": str(source)}

    persisted_outcomes: list[dict[str, str]] = []
    candidate_ids, errors = roster_commands._collect_sync_candidates(
        [source_row],
        store,
        dry_run=False,
        outcome_sink=persisted_outcomes,
    )
    assert len(candidate_ids) == 1
    assert errors == []
    assert {outcome["status"] for outcome in persisted_outcomes} == {
        "candidate",
        "quarantined",
    }

    dry_outcomes: list[dict[str, str]] = []
    dry_candidates, dry_errors = roster_commands._collect_sync_candidates(
        [source_row],
        store,
        dry_run=True,
        outcome_sink=dry_outcomes,
    )
    assert dry_candidates == ["valid-agent"]
    assert dry_errors == []
    assert {outcome["status"] for outcome in dry_outcomes} == {
        "candidate",
        "quarantined",
    }

    monkeypatch.setattr(
        roster_commands,
        "quarantine_manifest_import",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("batch failed")),
    )
    failed_outcomes: list[dict[str, str]] = []
    failed_ids, failed_errors = roster_commands._collect_sync_candidates(
        [source_row],
        store,
        dry_run=False,
        outcome_sink=failed_outcomes,
    )
    assert failed_ids == []
    assert failed_outcomes == []
    assert failed_errors == [{"source": str(source), "error": "batch failed"}]

    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(roster_commands, "_print_json", emitted.append)
    monkeypatch.setattr(
        roster_commands,
        "create_roster_diff",
        lambda *_args, **_kwargs: {"snapshot_id": "snapshot", "diff": {}},
    )
    result = roster_commands._complete_sync(
        SimpleNamespace(review=False, auto_approve=False),
        store,
        ["candidate"],
        [],
        [{"status": "quarantined"}],
    )
    assert result == 0
    assert emitted == [{"outcomes": [{"status": "quarantined"}]}]


def test_manifest_directory_uses_shared_discovery_budgets(monkeypatch, tmp_path):
    for division in ("engineering", "support"):
        path = tmp_path / division
        path.mkdir()
        (path / "agent.md").write_text(
            f"""---
name: {division.title()} Agent
description: A bounded agent.
---
Do bounded work.
""",
            encoding="utf-8",
        )
    (tmp_path / "divisions.json").write_text(
        json.dumps({"divisions": {"engineering": {}, "support": {}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(roster_ingress, "MAX_SOURCE_FILES", 1)
    with pytest.raises(RosterSyncError, match="more than 1 agent files"):
        download_from_source(str(tmp_path))

    monkeypatch.setattr(roster_ingress, "MAX_SOURCE_FILES", 2)
    monkeypatch.setattr(roster_ingress, "MAX_DIRECTORY_ENTRIES", 1)
    with pytest.raises(RosterSyncError, match="exceeds 1 entries"):
        download_from_source(str(tmp_path))


def test_manifest_directory_rejects_declared_division_symlink(tmp_path):
    target = tmp_path / "real-engineering"
    target.mkdir()
    try:
        (tmp_path / "engineering").symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable for this test user")
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )

    with pytest.raises(RosterSyncError, match="symbolic links"):
        download_from_source(str(tmp_path))


def test_manifest_directory_rejects_non_directory_shapes_and_excess_divisions(
    monkeypatch,
    tmp_path,
):
    manifest_directory_root = tmp_path / "manifest-directory"
    manifest_directory_root.mkdir()
    (manifest_directory_root / "divisions.json").mkdir()
    with pytest.raises(RosterSyncError, match="manifest must be a regular file"):
        download_from_source(str(manifest_directory_root))

    division_file_root = tmp_path / "division-file"
    division_file_root.mkdir()
    (division_file_root / "engineering").write_text("not a directory", encoding="utf-8")
    (division_file_root / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    with pytest.raises(RosterSyncError, match="division must be a real directory"):
        download_from_source(str(division_file_root))

    excess_root = tmp_path / "excess"
    excess_root.mkdir()
    (excess_root / "divisions.json").write_text(
        '{"divisions":{"engineering":{},"support":{}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(roster_ingress, "MAX_LIST_ITEMS", 1)
    with pytest.raises(RosterSyncError, match="more than 1 divisions"):
        download_from_source(str(excess_root))

    ordinary_file = tmp_path / "ordinary.md"
    ordinary_file.write_text("# Agent", encoding="utf-8")
    with pytest.raises(RosterSyncError, match="must be a real directory"):
        roster_ingress._directory_source_files(ordinary_file)


def test_manifest_discovery_detects_root_and_manifest_mutation(monkeypatch, tmp_path):
    def source_root(name):
        root = tmp_path / name
        root.mkdir()
        (root / "engineering").mkdir()
        (root / "divisions.json").write_text(
            '{"divisions":{"engineering":{}}}',
            encoding="utf-8",
        )
        return root

    root_changed = source_root("root-changed")
    original_load_json = roster_ingress._load_json

    def mutate_root(content, label):
        loaded = original_load_json(content, label)
        (root_changed / "appeared-during-parse.txt").write_text("changed", encoding="utf-8")
        return loaded

    with monkeypatch.context() as context:
        context.setattr(
            roster_ingress,
            "_directory_fingerprint",
            lambda _metadata: (1, 2, stat.S_IFDIR, 0, 3),
        )
        context.setattr(roster_ingress, "_load_json", mutate_root)
        with pytest.raises(RosterSyncError, match="changed during manifest discovery"):
            download_from_source(str(root_changed))

    manifest_changed = source_root("manifest-changed")

    def mutate_manifest(content, label):
        loaded = original_load_json(content, label)
        (manifest_changed / "divisions.json").write_text(
            '{ "divisions": { "engineering": {} } }',
            encoding="utf-8",
        )
        return loaded

    with monkeypatch.context() as context:
        context.setattr(roster_ingress, "_load_json", mutate_manifest)
        with pytest.raises(RosterSyncError, match="manifest changed during discovery"):
            download_from_source(str(manifest_changed))


def test_loaded_manifest_detects_later_source_changes(monkeypatch, tmp_path):
    def load_manifest(name):
        root = tmp_path / name
        root.mkdir()
        root = roster_ingress._assert_real_path_chain(root)
        (root / "engineering").mkdir()
        (root / "divisions.json").write_text(
            '{"divisions":{"engineering":{}}}',
            encoding="utf-8",
        )
        fingerprint = roster_ingress._directory_fingerprint(roster_ingress.os.lstat(root))
        manifest = roster_ingress._load_division_manifest(root, fingerprint)
        assert manifest is not None
        return root, manifest

    missing_root, missing_manifest = load_manifest("missing")
    missing_manifest.path.unlink()
    with pytest.raises(RosterSyncError, match="source changed during discovery"):
        roster_ingress._assert_division_manifest_unchanged(missing_root, missing_manifest)

    with monkeypatch.context() as context:
        context.setattr(
            roster_ingress,
            "_directory_fingerprint",
            lambda _metadata: (1, 2, stat.S_IFDIR, 0, 3),
        )
        root_changed, root_manifest = load_manifest("root")
        (root_changed / "new-entry.txt").write_text("changed", encoding="utf-8")
        with pytest.raises(RosterSyncError, match="roster directory changed"):
            roster_ingress._assert_division_manifest_unchanged(root_changed, root_manifest)

    manifest_changed, manifest_snapshot = load_manifest("manifest")
    manifest_snapshot.path.write_text(
        '{ "divisions": { "engineering": {} } }',
        encoding="utf-8",
    )
    with pytest.raises(RosterSyncError, match="division manifest changed"):
        roster_ingress._assert_division_manifest_unchanged(
            manifest_changed,
            manifest_snapshot,
        )


@pytest.mark.parametrize("mutation", ["add", "remove", "rename", "replace"])
def test_manifest_ingestion_rejects_nested_entry_changes_without_directory_mtime(
    monkeypatch,
    tmp_path,
    mutation,
):
    division = tmp_path / "engineering"
    division.mkdir()
    agent = division / "agent.md"
    agent.write_text("# Agent\nUseful prompt", encoding="utf-8")
    ignored = division / "ignored.txt"
    if mutation != "add":
        ignored.write_text("original", encoding="utf-8")
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    original_read = roster_ingress._read_local_file
    original_file_fingerprint = roster_ingress._file_fingerprint
    frozen_fingerprint = (1, 2, stat.S_IFDIR, 0, 3)

    monkeypatch.setattr(
        roster_ingress,
        "_directory_fingerprint",
        lambda _metadata: frozen_fingerprint,
    )
    monkeypatch.setattr(
        roster_ingress,
        "_file_fingerprint",
        lambda metadata: (
            (*original_file_fingerprint(metadata)[:4], 0, 0)
            if stat.S_ISDIR(metadata.st_mode)
            else original_file_fingerprint(metadata)
        ),
    )

    def mutate_after_read(path, *, expected_fingerprint=None):
        result = original_read(path, expected_fingerprint=expected_fingerprint)
        if Path(path) == agent:
            if mutation == "add":
                ignored.write_text("appeared", encoding="utf-8")
            elif mutation == "remove":
                ignored.unlink()
            elif mutation == "rename":
                ignored.rename(division / "renamed.txt")
            else:
                replacement = division / "replacement.tmp"
                replacement.write_text("replacement", encoding="utf-8")
                replacement.replace(ignored)
        return result

    monkeypatch.setattr(roster_ingress, "_read_local_file", mutate_after_read)

    with pytest.raises(RosterSyncError, match="roster directory changed"):
        download_from_source(str(tmp_path))


def test_directory_files_accept_exact_source_budget_and_preserve_walk_order(
    monkeypatch,
    tmp_path,
):
    first = tmp_path / "Alpha"
    second = tmp_path / "beta"
    first.mkdir()
    second.mkdir()
    (tmp_path / "root.md").write_text("root", encoding="utf-8")
    (first / "first.md").write_text("first", encoding="utf-8")
    (second / "second.md").write_text("second", encoding="utf-8")
    monkeypatch.setattr(roster_ingress, "MAX_DIRECTORY_ENTRIES", 5)

    files = roster_ingress._directory_files(tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path, _fingerprint in files] == [
        "root.md",
        "Alpha/first.md",
        "beta/second.md",
    ]


def test_manifest_directory_accepts_exact_source_budget(monkeypatch, tmp_path):
    division = tmp_path / "engineering"
    division.mkdir()
    (division / "agent.md").write_text("---\nname: Agent\n---\nUseful", encoding="utf-8")
    (division / "ignored.txt").write_text("ignored", encoding="utf-8")
    (tmp_path / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(roster_ingress, "MAX_DIRECTORY_ENTRIES", 4)

    files = roster_ingress._directory_source_files(tmp_path)

    assert [(path.name, division_name) for path, _fingerprint, division_name in files] == [
        ("agent.md", "engineering")
    ]


def test_directory_source_files_without_receipt_collector(tmp_path):
    (tmp_path / "agent.md").write_text("agent", encoding="utf-8")

    files = roster_ingress._directory_source_files(tmp_path)

    assert [(path.name, division_name) for path, _fingerprint, division_name in files] == [
        ("agent.md", None)
    ]


def test_directory_entry_snapshot_is_exact_ordered_and_bounded(monkeypatch, tmp_path):
    (tmp_path / "B.md").write_text("b", encoding="utf-8")
    (tmp_path / "a.md").write_text("a", encoding="utf-8")

    snapshot = roster_ingress._directory_entry_snapshot(tmp_path)

    assert [name for name, _fingerprint in snapshot] == [b"B.md", b"a.md"]
    monkeypatch.setattr(roster_ingress, "MAX_DIRECTORY_ENTRIES", 1)
    with pytest.raises(RosterSyncError, match="exceeds 1 entries"):
        roster_ingress._directory_entry_snapshot(tmp_path)


def test_directory_fingerprint_mismatch_fails_closed(tmp_path):
    with pytest.raises(RosterSyncError, match="changed during discovery"):
        roster_ingress._assert_expected_directory_fingerprint(
            tmp_path,
            (1, 1, 1, 1, 1),
            (2, 2, 2, 2, 2),
        )


def test_manifest_unavailable_os_error_is_wrapped(monkeypatch, tmp_path):
    root = roster_ingress._assert_real_path_chain(tmp_path)
    root_fingerprint = roster_ingress._directory_fingerprint(roster_ingress.os.lstat(root))
    original_lstat = roster_ingress.os.lstat
    manifest_path = root / "divisions.json"

    def deny_manifest(path):
        if Path(path) == manifest_path:
            raise PermissionError("denied")
        return original_lstat(path)

    monkeypatch.setattr(roster_ingress.os, "lstat", deny_manifest)
    with pytest.raises(RosterSyncError, match="division manifest is unavailable"):
        roster_ingress._load_division_manifest(root, root_fingerprint)


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
            **_agent(
                "revision-agent",
                "Tests immutable revisions",
                prompt=prompt,
            ),
            "version": "1.0.0",
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
    active_version = store.get_roster_entry("revision-agent")["version"]

    conn = store._connect()
    try:
        before = dict(
            conn.execute(
                "SELECT id, hash, content, created_at FROM agent_versions "
                "WHERE agent_slug = 'revision-agent' AND version = ?",
                (active_version,),
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
            "WHERE agent_slug = 'revision-agent' AND version = ?",
            (active_version,),
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert dict(rows[0]) == before


def test_changed_content_with_same_source_version_creates_new_immutable_revision(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    first_snapshot = _approved_snapshot(store, source_id, "original prompt")
    activate_snapshot(store, first_snapshot)
    first_active = store.get_roster_entry("revision-agent")
    store._activate_prevalidated_agent(
        {
            "slug": "independent-agent",
            "name": "Independent Agent",
            "description": "Must survive failed activation",
            "prompt_body": "Preserve this independent active revision.",
        }
    )
    changed_snapshot = _approved_snapshot(store, source_id, "changed prompt")
    activate_snapshot(store, changed_snapshot)
    changed_active = store.get_roster_entry("revision-agent")

    conn = store._connect()
    try:
        versions = [
            dict(row)
            for row in conn.execute(
                "SELECT version, source_version, hash, content FROM agent_versions "
                "WHERE agent_slug = 'revision-agent' ORDER BY created_at"
            ).fetchall()
        ]
        activated = conn.execute(
            "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
            (changed_snapshot,),
        ).fetchone()["activated"]
    finally:
        conn.close()
    assert first_active["version"].startswith("sha256:")
    assert changed_active["version"].startswith("sha256:")
    assert changed_active["version"] != first_active["version"]
    assert [row["source_version"] for row in versions] == ["1.0.0", "1.0.0"]
    assert {json.loads(row["content"])["prompt_body"] for row in versions} == {
        "original prompt",
        "changed prompt",
    }
    assert activated == 1
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


def test_activation_allows_unrelated_concurrent_roster_change(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    candidate_id = quarantine_candidate(_agent("reviewed-agent"), source_id, store)
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, snapshot["snapshot_id"])
    store._activate_prevalidated_agent(_agent("concurrent-agent"))
    activate_snapshot(store, snapshot["snapshot_id"])

    assert [row["agent_slug"] for row in store.get_active_roster()] == [
        "concurrent-agent",
        "reviewed-agent",
    ]
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT activated FROM agent_snapshots WHERE snapshot_id = ?",
                (snapshot["snapshot_id"],),
            ).fetchone()["activated"]
            == 1
        )
        assert (
            conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?", (candidate_id,)
            ).fetchone()["status"]
            == "activated"
        )
    finally:
        conn.close()


def test_activation_rejects_same_agent_concurrent_revision_change(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    store._activate_prevalidated_agent(_agent("reviewed-agent"))
    candidate_id = quarantine_candidate(
        _agent("reviewed-agent", prompt="reviewed replacement"),
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
    approve_snapshot(store, snapshot["snapshot_id"])
    store._activate_prevalidated_agent(
        {
            **_agent("reviewed-agent", prompt="concurrent revision"),
            "version": "2.0.0",
        }
    )

    with pytest.raises(RosterSyncError, match="different revision of reviewed-agent"):
        activate_snapshot(store, snapshot["snapshot_id"])

    assert store.get_specialist_prompt("reviewed-agent")["prompt_body"] == "concurrent revision"


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
    active_version = store.get_roster_entry("revision-agent")["version"]
    second_snapshot = _approved_snapshot(store, source_id, "stable prompt")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = 'corrupted content' "
            "WHERE agent_slug = 'revision-agent' AND version = ?",
            (active_version,),
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
                "WHERE event_type = 'snapshot_activated' "
                "AND json_valid(detail) "
                "AND json_extract(detail, '$.snapshot_id') = ?",
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


def test_retirement_requires_latest_complete_scan_and_preserves_history(tmp_path):
    source = tmp_path / "catalog"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    for slug in ("keep-agent", "retire-agent"):
        (division / f"{slug}.md").write_text(
            _governed_markdown(
                slug,
                "Complete scan fixture.",
                f"Perform {slug} work.",
            ),
            encoding="utf-8",
        )
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "manifest")
    first = download_from_source(str(source))
    candidate_ids, _outcomes = quarantine_manifest_import(
        first,
        first.outcomes,
        source_id,
        store,
    )
    activation = create_roster_diff(store, candidate_ids=candidate_ids)
    approve_snapshot(store, activation["snapshot_id"])
    activate_snapshot(store, activation["snapshot_id"])
    store._activate_prevalidated_agent(_agent("unrelated-agent"))
    retired_version = store.get_roster_entry("retire-agent")["version"]

    (division / "retire-agent.md").unlink()
    latest = download_from_source(str(source))
    quarantine_manifest_import(latest, latest.outcomes, source_id, store)
    scan = list_source_scans(store)[0]
    assert scan["status"] == "complete"
    retirement = create_retirement_diff(
        store,
        scan_id=scan["id"],
        slugs=["retire-agent"],
    )
    approve_snapshot(store, retirement["snapshot_id"])
    activate_snapshot(store, retirement["snapshot_id"])

    assert [row["agent_slug"] for row in store.get_active_roster()] == [
        "keep-agent",
        "unrelated-agent",
    ]
    conn = store._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_versions "
                "WHERE agent_slug = 'retire-agent' AND version = ?",
                (retired_version,),
            ).fetchone()[0]
            == 1
        )
        retired = conn.execute(
            "SELECT source_scan_id FROM agent_retirements WHERE agent_slug = 'retire-agent'"
        ).fetchone()
    finally:
        conn.close()
    assert retired["source_scan_id"] == scan["id"]


def test_partial_scan_cannot_authorize_retirement(tmp_path):
    source = tmp_path / "catalog"
    division = source / "engineering"
    division.mkdir(parents=True)
    (source / "divisions.json").write_text(
        '{"divisions":{"engineering":{}}}',
        encoding="utf-8",
    )
    active_path = division / "retire-agent.md"
    active_path.write_text(
        _governed_markdown(
            "retire-agent",
            "Active fixture.",
            "Original prompt.",
        ),
        encoding="utf-8",
    )
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(source), "manifest")
    initial = download_from_source(str(source))
    candidate_ids, _outcomes = quarantine_manifest_import(
        initial,
        initial.outcomes,
        source_id,
        store,
    )
    snapshot = create_roster_diff(store, candidate_ids=candidate_ids)
    approve_snapshot(store, snapshot["snapshot_id"])
    activate_snapshot(store, snapshot["snapshot_id"])

    active_path.unlink()
    (division / "corrupt.md").write_text(
        "---\nname: Corrupt Agent\ndescription: Invalid fixture.\n---\nBad \x04 prompt.\n",
        encoding="utf-8",
    )
    partial = download_from_source(str(source))
    quarantine_manifest_import(partial, partial.outcomes, source_id, store)
    scan = list_source_scans(store)[0]
    assert scan["status"] == "partial"
    with pytest.raises(RosterSyncError, match="partial and cannot authorize retirement"):
        create_retirement_diff(store, scan_id=scan["id"], slugs=["retire-agent"])
    assert store.get_roster_entry("retire-agent") is not None


def test_empty_scan_receipt_is_partial_and_cannot_authorize_mass_retirement(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "empty"), "empty")
    store._activate_prevalidated_agent(
        {
            **_agent("retire-agent"),
            "source_id": source_id,
            "source": str(tmp_path / "empty"),
        }
    )
    quarantine_manifest_import([], [], source_id, store)
    scan = list_source_scans(store)[0]
    assert scan["status"] == "partial"
    with pytest.raises(RosterSyncError, match="partial and cannot authorize retirement"):
        create_retirement_diff(store, scan_id=scan["id"], slugs=["retire-agent"])


def test_revision_rollback_is_exact_metadata_restore_with_stale_cas_rejection(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")

    def activate_revision(prompt, *, description, categories):
        candidate_id = quarantine_candidate(
            {
                **_agent(
                    "rollback-agent",
                    description,
                    prompt=prompt,
                    categories=categories,
                ),
                "version": "1.0.0",
            },
            source_id,
            store,
        )
        snapshot = create_roster_diff(store, candidate_ids=[candidate_id])
        approve_snapshot(store, snapshot["snapshot_id"])
        activate_snapshot(store, snapshot["snapshot_id"])
        return store.get_roster_entry("rollback-agent")

    first = activate_revision(
        "first prompt",
        description="First description",
        categories=["code", "security"],
    )
    second = activate_revision(
        "second prompt",
        description="Second description",
        categories=["code"],
    )
    store._activate_prevalidated_agent(_agent("unrelated-agent"))

    restored = store.rollback_agent_revision(
        "rollback-agent",
        first["version"],
        expected_current_version=second["version"],
        expected_current_hash=second["hash"],
    )
    assert restored["description"] == "First description"
    assert restored["categories"] == ["code", "security"]
    assert (
        json.loads(store.get_specialist_prompt("rollback-agent")["prompt_body"])["prompt_body"]
        == "first prompt"
    )
    assert store.get_roster_entry("unrelated-agent") is not None
    with pytest.raises(ValueError, match="active revision changed"):
        store.rollback_agent_revision(
            "rollback-agent",
            second["version"],
            expected_current_version=second["version"],
            expected_current_hash=second["hash"],
        )


def test_prompt_reads_fail_closed_when_imported_revision_content_is_tampered(tmp_path):
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source(str(tmp_path / "fixture"), "fixture")
    snapshot = _approved_snapshot(store, source_id, "stable prompt")
    activate_snapshot(store, snapshot)
    active = store.get_roster_entry("revision-agent")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_versions SET content = 'tampered' "
            "WHERE agent_slug = 'revision-agent' AND version = ?",
            (active["version"],),
        )
        conn.commit()
    finally:
        conn.close()
    assert store.get_specialist_prompt("revision-agent") is None
    assert (
        store.get_versioned_specialist_prompt(
            "revision-agent",
            active["version"],
            active["hash"],
        )
        is None
    )
