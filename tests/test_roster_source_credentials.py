"""Credential-free roster-source persistence and legacy migration coverage."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.cli import roster_commands
from agency_runtime.core.roster.revisions import immutable_revision_version
from agency_runtime.core.roster.source_identity import (
    MAX_DURABLE_SOURCE_BYTES,
    MAX_DURABLE_SOURCE_COUNT,
    MAX_SOURCE_DISPLAY_NAME_BYTES,
    SourceIdentityError,
    canonical_source_identity,
    legacy_source_name_redaction,
    legacy_source_redaction,
)
from agency_runtime.core.roster.sync import remediation_queue_snapshot
from agency_runtime.core.store.schema import (
    BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL,
    BOUNDED_REMEDIATION_EVENT_DETAIL_SQL,
    SCHEMA_V1,
    SCHEMA_VERSION,
    agent_import_event_sequence_schema_is_current,
    remediation_authority_material_from_connection,
    remediation_authority_schema_is_current,
)
from agency_runtime.core.store.sqlite import Store
from tests.runtime_support import harden_private_test_file


def _resolution_detail(
    queue_event_id: str,
    *,
    resolution: str = "superseded_by_candidate",
) -> str:
    original_hash = "1" * 64
    source_hash = original_hash if resolution == "remediated_candidate" else "2" * 64
    return json.dumps(
        {
            "audit_id": "audit-" + "3" * 64,
            "audit_revision": "sha256:" + "4" * 64,
            "candidate_download_id": "candidate-download",
            "candidate_hash": "5" * 64,
            "candidate_id": "candidate",
            "download_id": "queue-download",
            "original_hash": original_hash,
            "origin": "agents/example.md",
            "policy_hash": "6" * 64,
            "queue_event_id": queue_event_id,
            "relative_path": "agents/example.md",
            "resolution": resolution,
            "scan_id": "candidate-scan",
            "source_hash": source_hash,
            "source_id": "source",
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _authority_dependencies(
    resolution_event_id: str,
    queue_event_id: str,
) -> list[dict[str, str]]:
    identities = (
        ("candidate", "candidate"),
        ("candidate_audit", "audit-" + "3" * 64),
        ("candidate_download", "candidate-download"),
        ("candidate_source_scan", "candidate-scan"),
        ("queue_download", "queue-download"),
        ("queue_event", queue_event_id),
        ("queue_source_scan", "queue-scan"),
        ("resolution_event", resolution_event_id),
        ("source", "source"),
    )
    return [
        {"kind": kind, "id": dependency_id, "hash": f"{index:064x}"}
        for index, (kind, dependency_id) in enumerate(identities, start=1)
    ]


def _authority_material(
    conn: sqlite3.Connection,
    *,
    resolution_event_id: str,
    queue_event_id: str,
    event_detail: str,
    agent_slug: str = "example",
    queue_created_at: str = "2026-07-18T00:00:00+00:00",
    resolution_created_at: str = "2026-07-18T00:00:01+00:00",
) -> tuple[str, int, str, list[dict[str, str]]]:
    dependencies = _authority_dependencies(resolution_event_id, queue_event_id)
    receipt, count, signature = remediation_authority_material_from_connection(
        conn,
        resolution_event_id=resolution_event_id,
        queue_event_id=queue_event_id,
        event_detail=event_detail,
        dependencies=dependencies,
        validated_at="2026-07-18T00:00:02+00:00",
        queue_created_at=queue_created_at,
        resolution_created_at=resolution_created_at,
        agent_slug=agent_slug,
    )
    return receipt, count, signature, dependencies


def _insert_authority(
    conn: sqlite3.Connection,
    *,
    resolution_event_id: str,
    queue_event_id: str,
    event_detail: str,
    agent_slug: str = "example",
    queue_created_at: str = "2026-07-18T00:00:00+00:00",
    resolution_created_at: str = "2026-07-18T00:00:01+00:00",
) -> tuple[str, int, str]:
    receipt, count, signature, dependencies = _authority_material(
        conn,
        resolution_event_id=resolution_event_id,
        queue_event_id=queue_event_id,
        event_detail=event_detail,
        agent_slug=agent_slug,
        queue_created_at=queue_created_at,
        resolution_created_at=resolution_created_at,
    )
    conn.execute(
        "INSERT INTO agent_remediation_resolution_authority "
        "(resolution_event_id, queue_event_id, evidence_receipt, dependency_count, "
        "authority_hmac, validated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            resolution_event_id,
            queue_event_id,
            receipt,
            count,
            signature,
            "2026-07-18T00:00:02+00:00",
        ),
    )
    conn.executemany(
        "INSERT INTO agent_remediation_resolution_dependencies "
        "(resolution_event_id, dependency_kind, dependency_id, dependency_hash) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                resolution_event_id,
                dependency["kind"],
                dependency["id"],
                dependency["hash"],
            )
            for dependency in dependencies
        ],
    )
    return receipt, count, signature


def _agent(
    slug: str,
    prompt: str,
    *,
    source_id: str,
    source: str,
) -> dict[str, object]:
    return {
        "slug": slug,
        "name": slug.replace("-", " ").title(),
        "description": "Credential migration fixture",
        "division": "engineering",
        "categories": ["engineering", "testing"],
        "capabilities": ["review bounded migration evidence"],
        "tool_affinity": [],
        "prompt_body": prompt,
        "source": source,
        "source_id": source_id,
        "source_version": "legacy-revision",
        "prompt_path": source,
    }


def _execute_replace_collision(conn: sqlite3.Connection, operation: str) -> None:
    if operation == "insert-source-url-collision":
        conn.execute(
            "INSERT OR REPLACE INTO agent_sources (id, url, name, added_at) "
            "VALUES ('source-replacement', 'https://source.test/agents', "
            "'replacement', '2026-07-18')"
        )
    elif operation == "update-source-url-collision":
        conn.execute(
            "INSERT INTO agent_sources (id, url, name, added_at) "
            "VALUES ('source-survivor', 'https://other.test/agents', "
            "'survivor', '2026-07-18')"
        )
        conn.execute(
            "UPDATE OR REPLACE agent_sources "
            "SET url = 'https://source.test/agents' "
            "WHERE id = 'source-survivor'"
        )
    elif operation == "insert-audit-identity-collision":
        conn.execute(
            "INSERT OR REPLACE INTO agent_candidate_audits "
            "(id, candidate_id, audit_revision, policy_hash, candidate_version, "
            "candidate_hash, active_basis_hash, deterministic_status, "
            "inference_status, verdict, created_at) VALUES "
            "('audit-replacement', 'candidate', 'audit-v1', 'policy', "
            "'version', 'hash', 'basis', 'passed', 'passed', 'passed', "
            "'2026-07-18')"
        )
    elif operation == "update-audit-identity-collision":
        conn.execute(
            "INSERT INTO agent_candidate_audits "
            "(id, candidate_id, audit_revision, policy_hash, candidate_version, "
            "candidate_hash, active_basis_hash, deterministic_status, "
            "inference_status, verdict, created_at) VALUES "
            "('audit-survivor', 'candidate', 'audit-v2', 'policy', "
            "'version', 'hash', 'basis', 'passed', 'passed', 'passed', "
            "'2026-07-18')"
        )
        conn.execute(
            "UPDATE OR REPLACE agent_candidate_audits "
            "SET audit_revision = 'audit-v1' WHERE id = 'audit-survivor'"
        )
    elif operation == "insert-event-id-collision":
        conn.execute(
            "INSERT OR REPLACE INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('event-victim', 'test', 'example', '{}', "
            "'2026-07-18T00:00:03+00:00')"
        )
    elif operation == "update-event-id-collision":
        conn.execute(
            "UPDATE OR REPLACE agent_import_events "
            "SET id = 'event-victim' WHERE id = 'event-survivor'"
        )
    elif operation == "insert-scan-entry-id-collision":
        conn.execute(
            "INSERT OR REPLACE INTO agent_source_scan_entries "
            "(id, scan_id, relative_path, slug, content_hash, status) VALUES "
            "('entry-victim', 'other-scan', 'agents/replacement.md', "
            "'replacement', 'replacement-hash', 'quarantined')"
        )
    elif operation == "update-scan-entry-id-collision":
        conn.execute(
            "UPDATE OR REPLACE agent_source_scan_entries "
            "SET id = 'entry-victim' WHERE id = 'entry-survivor'"
        )
    elif operation == "insert-finding-id-collision":
        conn.execute(
            "INSERT OR REPLACE INTO agent_candidate_audit_findings "
            "(id, audit_id, source, severity, code, message, "
            "evidence_hash, created_at) VALUES "
            "('finding-victim', 'audit-other', 'deterministic', 'error', "
            "'replacement', 'replacement', 'replacement-hash', '2026-07-18')"
        )
    else:
        conn.execute(
            "UPDATE OR REPLACE agent_candidate_audit_findings "
            "SET id = 'finding-victim' WHERE id = 'finding-survivor'"
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("HTTPS://Example.TEST:443/agents.json", "https://example.test:443/agents.json"),
        ("https://[2001:db8::1]:8443/agents", "https://[2001:db8::1]:8443/agents"),
        ("file:///tmp/agents.json", "file:///tmp/agents.json"),
        ("file://localhost/tmp/agents.json", "file://localhost/tmp/agents.json"),
        ("relative-filename", "relative-filename"),
        (r"C:\agents\roster.json", r"C:\agents\roster.json"),
    ],
)
def test_canonical_source_identity_accepts_only_credential_free_identities(
    value: str,
    expected: str,
) -> None:
    assert canonical_source_identity(value) == expected


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (None, "must be text"),
        ("", "may not be empty"),
        ("   ", "may not be blank"),
        ("x" * (MAX_DURABLE_SOURCE_BYTES + 1), "exceeds"),
        ("https://example.test/\x00agents", "control characters"),
        ("https://example.test/\tagents", "control characters"),
        ("https://example.test/\nagents", "control characters"),
        ("https://example.test/\ragents", "control characters"),
        ("https://example.test/\x85agents", "control characters"),
        ("https://example.test/\u202eagents", "control characters"),
        ("https://example.test/\ud800agents", "valid UTF-8"),
        ("https://user:secret@example.test/agents", "credentials"),
        ("https://example.test/agents?token=secret", "query"),
        ("https://example.test/agents#secret", "fragment"),
        ("relative/agents?token=secret", "query"),
        ("relative/agents#secret", "fragment"),
        (r"C:\agents\roster.json?token=secret", "query"),
        ("fixture://example/agents", "unsupported scheme"),
        ("ssh://example.test/agents", "unsupported scheme"),
        ("ssh:example.test/agents", "unsupported scheme"),
        ("mailto:roster@example.test", "unsupported scheme"),
        ("file://remote.test/agents", "remote file URL authorities"),
        (r"\\server\share\agents.json", "remote filesystem roster paths"),
        ("//server/share/agents.json", "remote filesystem roster paths"),
        ("https:agents", "hostname"),
        ("https://example.test:99999/agents", "invalid port"),
        ("https://example.test/agents path", "whitespace"),
        (r"https://example.test\agents", "backslash"),
        ("https://éxample.test/agents", "percent-encode"),
        ("https://[invalid/agents", "malformed"),
    ],
)
def test_canonical_source_identity_rejects_unsafe_durable_sources(
    value: object,
    message: str,
) -> None:
    with pytest.raises(SourceIdentityError, match=message):
        canonical_source_identity(value)


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
def test_canonical_source_identity_rejects_every_query_parameter(query: str) -> None:
    """Durable identity rejects all query data, not only known credential names."""

    with pytest.raises(SourceIdentityError, match="may not contain a query"):
        canonical_source_identity(f"https://example.test/agents?{query}")


def test_legacy_source_redaction_is_stable_and_only_marks_unsafe_urls() -> None:
    assert (
        legacy_source_redaction(
            "https://example.test/agents",
            source_id="source-safe",
        )
        is None
    )
    tainted = legacy_source_redaction(
        "https://user:secret@example.test/agents",
        source_id="source-tainted",
    )
    malformed = legacy_source_redaction(
        "https://[invalid",
        source_id="source-malformed",
    )
    assert tainted is not None
    assert tainted.identity.startswith("redacted://legacy-source/")
    assert tainted.reason == "credentials_or_opaque_components"
    assert tainted.purge_references is True
    assert tainted == legacy_source_redaction(
        "https://example.test/agents?token=other",
        source_id="source-tainted",
    )
    assert malformed is not None
    assert malformed.reason == "malformed_url"
    assert malformed.purge_references is True


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        r"\\server\share\agents.json",
        "//server/share/agents.json",
        "fixture://legacy/agents",
        "x" * (MAX_DURABLE_SOURCE_BYTES + 1),
    ],
)
def test_legacy_source_redaction_totally_classifies_nonsecret_invalid_sources(
    value: str,
) -> None:
    redaction = legacy_source_redaction(value, source_id="legacy-invalid")
    assert redaction is not None
    assert redaction.reason == "unsupported_or_noncanonical_source"
    assert redaction.purge_references is False


@pytest.mark.parametrize(
    "value",
    [
        "https://example.test/\tagents",
        "https://example.test/\nagents",
        "https://example.test/\ragents",
        "https://example.test/\x85agents",
        "https://example.test/\u2066agents",
    ],
)
def test_legacy_source_redaction_purges_all_durable_control_classes(value: str) -> None:
    redaction = legacy_source_redaction(value, source_id="legacy-control")
    assert redaction is not None
    assert redaction.reason == "unsafe_source_controls"
    assert redaction.purge_references is True


def test_store_rejects_secret_bearing_source_urls_before_persistence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    original = "HTTPS://Example.TEST:443/agents.json"
    source_id = store.add_agent_source(original, original)

    [source] = store.list_agent_sources()
    assert source["id"] == source_id
    assert source["url"] == "https://example.test:443/agents.json"
    assert source["name"] == source["url"]

    for unsafe in (
        "https://user:secret@example.test/agents",
        "https://example.test/agents?token=PLANTED_STORE_SECRET",
        "https://example.test/agents#secret",
    ):
        with pytest.raises(SourceIdentityError):
            store.add_agent_source(unsafe, unsafe)

    conn = store._connect()
    try:
        serialized = "\n".join(
            str(value)
            for row in conn.execute("SELECT url, name FROM agent_sources")
            for value in row
        )
    finally:
        conn.close()
    assert "PLANTED_STORE_SECRET" not in serialized
    assert "user:secret" not in serialized


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("https://user:secret@example.test/agents", "credentials"),
        ("https://example.test/agents?token=secret", "query"),
        ("https://example.test/agents#secret", "fragment"),
        ("fixture://source", "unsupported scheme"),
        ("https://[invalid", "malformed"),
        ("   ", "may not be blank"),
        ("\ud800", "valid UTF-8"),
        ("unsafe\tname", "control characters"),
        ("unsafe\nname", "control characters"),
        ("unsafe\rname", "control characters"),
        ("unsafe\x85name", "control characters"),
        ("\u202eunsafe", "control characters"),
        ("x" * (MAX_SOURCE_DISPLAY_NAME_BYTES + 1), "exceeds"),
        (object(), "must be text"),
    ],
)
def test_store_rejects_unsafe_source_display_names_before_persistence(
    tmp_path: Path,
    name: object,
    message: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(SourceIdentityError, match=message):
        store.add_agent_source("https://example.test/agents", name)  # type: ignore[arg-type]
    assert store.list_agent_sources() == []


def test_store_canonicalizes_safe_url_display_name_and_preserves_label(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    first = store.add_agent_source(
        "https://example.test/one",
        "HTTPS://EXAMPLE.TEST:443/display",
    )
    second = store.add_agent_source("https://example.test/two", "Upstream roster")
    sources = {row["id"]: row for row in store.list_agent_sources()}
    assert sources[first]["name"] == "https://example.test:443/display"
    assert sources[second]["name"] == "Upstream roster"


def test_legacy_source_name_redaction_handles_controls_and_opaque_markers() -> None:
    control = legacy_source_name_redaction(
        "unsafe\nname",
        source_id="legacy-name-control",
    )
    assert control is not None
    assert control.reason == "unsafe_source_name"
    assert control.purge_references is True
    marker = legacy_source_redaction(
        "fixture://legacy/source",
        source_id="legacy-name-marker",
    )
    assert marker is not None
    assert (
        legacy_source_name_redaction(
            marker.identity,
            source_id="legacy-name-marker",
        )
        is None
    )


def test_source_add_cli_error_never_echoes_rejected_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "PLANTED_CLI_SECRET"

    class RejectingStore:
        def add_agent_source(self, *_args, **_kwargs):
            raise SourceIdentityError("source URL may not contain a query")

    monkeypatch.setattr(roster_commands, "_store", RejectingStore)
    args = SimpleNamespace(
        url=f"https://example.test/agents?token={secret}",
        name="",
        trusted_for_auto_approve=False,
    )

    assert roster_commands.cmd_source_add(args) == 1
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert "may not contain a query" in captured.err


def _all_database_text(conn: sqlite3.Connection) -> str:
    values: list[str] = []
    tables = [
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    for table in tables:
        quoted_table = '"' + table.replace('"', '""') + '"'
        columns = [
            str(row[1])
            for row in conn.execute(f"PRAGMA table_info({quoted_table})")
            if "TEXT" in str(row[2]).upper()
        ]
        for column in columns:
            quoted_column = '"' + column.replace('"', '""') + '"'
            values.extend(
                str(row[0])
                for row in conn.execute(
                    f"SELECT {quoted_column} FROM {quoted_table} WHERE {quoted_column} IS NOT NULL"
                )
            )
    return "\n".join(values)


def _sqlite_storage_bytes(path: Path) -> bytes:
    payload = bytearray()
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            payload.extend(candidate.read_bytes())
    return bytes(payload)


def _set_schema_v29(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (29)")


def _create_non_affinity_legacy_database(
    path: Path,
    *,
    url: object,
    name: object,
) -> str:
    source_definition = (
        "CREATE TABLE IF NOT EXISTS agent_sources (\n"
        "    id TEXT PRIMARY KEY,\n"
        "    url TEXT NOT NULL UNIQUE,\n"
        "    name TEXT,"
    )
    legacy_definition = (
        "CREATE TABLE IF NOT EXISTS agent_sources (\n"
        "    id TEXT PRIMARY KEY,\n"
        "    url NOT NULL UNIQUE,\n"
        "    name,"
    )
    assert source_definition in SCHEMA_V1
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_V1.replace(source_definition, legacy_definition, 1))
        source_id = "legacy-non-affinity-source"
        conn.execute(
            "INSERT INTO agent_sources "
            "(id, url, name, added_at, enabled, trusted_for_auto_approve) "
            "VALUES (?, ?, ?, '2026-07-18', 1, 1)",
            (source_id, url, name),
        )
        conn.execute("INSERT INTO schema_version (version) VALUES (29)")
        conn.commit()
        return source_id
    finally:
        conn.close()
        harden_private_test_file(path)


@pytest.mark.parametrize(
    ("column", "tampered"),
    [
        ("url", "https://reader:secret@example.test/agents?token=PLANTED_READ_URL"),
        ("name", "Safe label\nPLANTED_READ_NAME"),
    ],
)
def test_source_reads_and_cli_fail_closed_without_echoing_post_v30_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    column: str,
    tampered: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source("https://example.test/agents", "Safe label")
    conn = store._connect()
    try:
        conn.execute(
            f"UPDATE agent_sources SET {column} = ? WHERE id = ?",  # nosec B608
            (tampered, source_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(
        SourceIdentityError,
        match="stored roster source identity is invalid",
    ) as captured:
        store.list_agent_sources()
    assert "PLANTED_READ" not in str(captured.value)

    monkeypatch.setattr(roster_commands, "_store", lambda: store)
    assert roster_commands.cmd_source_list(SimpleNamespace()) == 1
    terminal = capsys.readouterr()
    assert "PLANTED_READ" not in terminal.out
    assert "PLANTED_READ" not in terminal.err
    assert "stored roster source identity is invalid" in terminal.err


@pytest.mark.parametrize(
    ("column", "tampered"),
    [
        ("url", "https://disabled:secret@example.test/agents?token=PLANTED_DISABLED_URL"),
        ("name", "https://example.test/agents?token=PLANTED_DISABLED_NAME"),
    ],
)
def test_current_schema_startup_rejects_tampered_disabled_source_without_echo(
    tmp_path: Path,
    column: str,
    tampered: str,
) -> None:
    path = tmp_path / f"disabled-{column}.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "Safe label")
    conn = store._connect()
    try:
        conn.execute(
            f"UPDATE agent_sources SET {column} = ?, enabled = 0 WHERE id = ?",  # nosec B608
            (tampered, source_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(
        RuntimeError,
        match="stored roster source identity is invalid",
    ) as captured:
        Store(path)
    assert "PLANTED_DISABLED" not in str(captured.value)


def test_source_count_is_bounded_on_write_and_legacy_migration(tmp_path: Path) -> None:
    path = tmp_path / "source-count.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.executemany(
            "INSERT INTO agent_sources "
            "(id, url, name, added_at, enabled, trusted_for_auto_approve) "
            "VALUES (?, ?, ?, '2026-07-18', 1, 0)",
            (
                (
                    f"source-{index}",
                    f"https://source-{index}.example.test/agents",
                    f"Source {index}",
                )
                for index in range(MAX_DURABLE_SOURCE_COUNT)
            ),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(SourceIdentityError, match="source count may not exceed"):
        store.add_agent_source("https://overflow.example.test/agents", "Overflow")

    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO agent_sources "
            "(id, url, name, added_at, enabled, trusted_for_auto_approve) "
            "VALUES ('tampered-overflow', 'https://tampered.example.test/agents', "
            "'Tampered overflow', '2026-07-18', 1, 0)"
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="legacy roster source count exceeds"):
        Store(path)

    conn = sqlite3.connect(path)
    try:
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 29
        assert conn.execute("SELECT COUNT(*) FROM agent_sources").fetchone()[0] == (
            MAX_DURABLE_SOURCE_COUNT + 1
        )
    finally:
        conn.close()


def test_remediation_provenance_indexes_are_repaired_and_used(tmp_path: Path) -> None:
    path = tmp_path / "resolution-index.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute("DROP INDEX idx_agent_import_resolution_queue")
        conn.execute("DROP INDEX idx_agent_import_queue_identity")
        conn.execute("DROP INDEX idx_agent_import_candidate_provenance")
        conn.execute("DROP INDEX idx_agent_import_scan_provenance")
        conn.execute(
            "CREATE UNIQUE INDEX idx_agent_import_resolution_queue "
            "ON agent_import_events(event_type) "
            "WHERE event_type = 'manifest_entry_remediation_resolved' "
            "AND json_valid(detail) AND '$.queue_event_id' <> ''"
        )
        conn.execute(
            "CREATE INDEX idx_agent_import_queue_identity "
            "ON agent_import_events(event_type, detail, agent_slug) "
            "WHERE event_type = 'manifest_entry_remediation_queued' "
            "AND json_valid(detail) AND '$.source_id' <> '' "
            "AND '$.relative_path' <> '' AND '$.origin' <> ''"
        )
        conn.execute(
            "CREATE INDEX idx_agent_import_candidate_provenance "
            "ON agent_import_events(event_type, agent_slug, detail)"
        )
        conn.execute(
            "CREATE INDEX idx_agent_import_scan_provenance "
            "ON agent_import_events(event_type, detail)"
        )
        conn.commit()
    finally:
        conn.close()

    repaired = Store(path)
    conn = repaired._connect()
    try:
        history = []
        for index in range(512):
            history.extend(
                (
                    (
                        f"candidate-history-{index}",
                        "manifest_entry_remediated",
                        f"candidate-history-{index}",
                        json.dumps({"candidate_id": f"candidate-history-{index}"}),
                        f"2026-07-18T00:{index // 60:02d}:{index % 60:02d}+00:00",
                    ),
                    (
                        f"ignored-history-{index}",
                        "manifest_entry_ignored",
                        "",
                        json.dumps(
                            {
                                "relative_path": f"agents/history-{index}.md",
                                "scan_id": f"scan-history-{index}",
                            }
                        ),
                        f"2026-07-18T01:{index // 60:02d}:{index % 60:02d}+00:00",
                    ),
                    (
                        f"header-history-{index}",
                        "source_scan_recorded",
                        "",
                        json.dumps({"scan_id": f"scan-history-{index}"}),
                        f"2026-07-18T02:{index // 60:02d}:{index % 60:02d}+00:00",
                    ),
                )
            )
        history.extend(
            (
                (
                    "target-remediation",
                    "manifest_entry_remediated",
                    "target",
                    json.dumps({"candidate_id": "candidate-target"}),
                    "2026-07-18T03:00:00+00:00",
                ),
                (
                    "target-queued",
                    "manifest_entry_remediation_queued",
                    "target",
                    json.dumps(
                        {
                            "origin": "https://example.test/agents",
                            "relative_path": "agents/target.md",
                            "scan_id": "scan-target",
                            "source_id": "source-target",
                        }
                    ),
                    "2026-07-18T03:00:01+00:00",
                ),
                (
                    "target-ignored",
                    "manifest_entry_ignored",
                    "",
                    json.dumps(
                        {
                            "relative_path": "agents/target.md",
                            "scan_id": "scan-target",
                        }
                    ),
                    "2026-07-18T03:00:02+00:00",
                ),
                (
                    "target-header",
                    "source_scan_recorded",
                    "",
                    json.dumps({"scan_id": "scan-target"}),
                    "2026-07-18T03:00:03+00:00",
                ),
            )
        )
        conn.executemany(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            history,
        )
        conn.commit()
        conn.execute("ANALYZE")

        def query_plan(sql: str, parameters: tuple[object, ...]) -> list[str]:
            return [
                str(row["detail"])
                for row in conn.execute(
                    f"EXPLAIN QUERY PLAN {sql}",  # nosec B608
                    parameters,
                )
            ]

        resolution_plan = [
            str(row["detail"])
            for row in conn.execute(
                "EXPLAIN QUERY PLAN SELECT id FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_resolved' "
                f"AND {BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL} "
                "AND json_extract(detail, '$.queue_event_id') = ?",
                ("queue-event",),
            )
        ]
        identity_plan = [
            str(row["detail"])
            for row in conn.execute(
                "EXPLAIN QUERY PLAN SELECT id FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_queued' "
                f"AND {BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL} "
                "AND json_extract(detail, '$.source_id') = ? "
                "AND json_extract(detail, '$.relative_path') = ? "
                "AND json_extract(detail, '$.origin') = ?",
                ("source-id", "agents/example.md", "https://example.test/agents"),
            )
        ]
        candidate_plan = query_plan(
            "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
            "FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
            "'$.candidate_id') = ? "
            "ORDER BY created_at DESC, event_sequence DESC LIMIT 2",
            ("target", "candidate-target"),
        )
        anomaly_plan = query_plan(
            "SELECT 1 FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
            "AND length(CAST(detail AS BLOB)) > ? LIMIT 1",
            ("target", 256 * 1024),
        )
        queued_scan_plan = query_plan(
            "SELECT id FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_queued' "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id') = ? "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
            "'$.relative_path') = ? LIMIT 2",
            ("scan-target", "agents/target.md"),
        )
        ignored_scan_plan = query_plan(
            "SELECT id FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_ignored' "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id') = ? "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
            "'$.relative_path') = ? LIMIT 2",
            ("scan-target", "agents/target.md"),
        )
        header_plan = query_plan(
            "SELECT id FROM agent_import_events "
            "WHERE event_type = 'source_scan_recorded' "
            f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id') = ? "
            "LIMIT 2",
            ("scan-target",),
        )
        assert [
            row["id"]
            for row in conn.execute(
                "SELECT id FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediated' AND agent_slug = ? "
                f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
                "'$.candidate_id') = ? "
                "ORDER BY created_at DESC, event_sequence DESC LIMIT 2",  # nosec B608
                ("target", "candidate-target"),
            )
        ] == ["target-remediation"]
        resolution_detail = json.dumps({"queue_event_id": "queue-event"})
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('resolution-one', 'manifest_entry_remediation_resolved', "
            "'example', ?, '2026-07-18')",
            (resolution_detail,),
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('resolution-two', 'manifest_entry_remediation_resolved', "
            "'example', ?, '2026-07-18')",
            (resolution_detail,),
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'manifest_entry_remediation_resolved'"
            ).fetchone()[0]
            == 2
        )
    finally:
        conn.close()
    assert any(
        "SEARCH" in detail and "idx_agent_import_resolution_queue" in detail
        for detail in resolution_plan
    )
    assert any(
        "SEARCH" in detail and "idx_agent_import_queue_identity" in detail
        for detail in identity_plan
    )
    for plan, index_name in (
        (candidate_plan, "idx_agent_import_candidate_provenance"),
        (anomaly_plan, "idx_agent_import_candidate_provenance"),
        (queued_scan_plan, "idx_agent_import_scan_provenance"),
        (ignored_scan_plan, "idx_agent_import_scan_provenance"),
        (header_plan, "idx_agent_import_scan_provenance"),
    ):
        assert any("SEARCH" in detail and index_name in detail for detail in plan), plan
        assert not any("SCAN agent_import_events" in detail for detail in plan), plan
        assert not any("USE TEMP B-TREE" in detail for detail in plan), plan


def test_import_event_sequence_is_monotonic_immutable_and_vacuum_stable(
    tmp_path: Path,
) -> None:
    path = tmp_path / "event-sequence.db"
    store = Store(path)
    conn = store._connect()
    try:
        for index in range(3):
            conn.execute(
                "INSERT INTO agent_import_events "
                "(id, event_type, agent_slug, detail, created_at) "
                "VALUES (?, 'test', 'example', '{}', ?)",
                (
                    f"event-{index}",
                    f"2026-07-18T00:00:0{index}+00:00",
                ),
            )
        conn.commit()
        before = [
            tuple(row)
            for row in conn.execute(
                "SELECT id, event_sequence FROM agent_import_events ORDER BY event_sequence"
            )
        ]
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE agent_import_events SET event_sequence = 9 WHERE id = 'event-0'")
        with pytest.raises(sqlite3.IntegrityError, match="store-assigned"):
            conn.execute(
                "INSERT INTO agent_import_events "
                "(id, event_type, agent_slug, detail, created_at, event_sequence) "
                "VALUES ('forged', 'test', 'example', '{}', "
                "'2026-07-18T00:00:09+00:00', 9)"
            )
        with pytest.raises(sqlite3.IntegrityError, match="counter is immutable"):
            conn.execute(
                "UPDATE store_counters SET value = 0 WHERE name = 'agent-import-event-sequence'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="counter is immutable"):
            conn.execute(
                "INSERT OR REPLACE INTO store_counters (name, value) "
                "VALUES ('agent-import-event-sequence', 0)"
            )
        conn.rollback()
        conn.execute("VACUUM")
        after = [
            tuple(row)
            for row in conn.execute(
                "SELECT id, event_sequence FROM agent_import_events ORDER BY event_sequence"
            )
        ]
        assert after == before == [("event-0", 1), ("event-1", 2), ("event-2", 3)]
        assert conn.execute("PRAGMA recursive_triggers").fetchone()[0] == 1
        assert agent_import_event_sequence_schema_is_current(conn) is True
    finally:
        conn.close()


def test_resolution_authority_requires_explicit_validation_and_invalidates_on_change(
    tmp_path: Path,
) -> None:
    path = tmp_path / "resolution-authority.db"
    store = Store(path)
    conn = store._connect()
    try:
        queue_created_at = "2026-07-18T00:00:00+00:00"
        resolution_created_at = "2026-07-18T00:00:01+00:00"
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('queue-one', 'manifest_entry_remediation_queued', "
            "'example', '{}', ?)",
            (queue_created_at,),
        )
        resolution_one = _resolution_detail("queue-one")
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('resolution-one', 'manifest_entry_remediation_resolved', "
            "'example', ?, ?)",
            (resolution_one, resolution_created_at),
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        receipt, count, _signature, dependencies = _authority_material(
            conn,
            resolution_event_id="resolution-one",
            queue_event_id="queue-one",
            event_detail=resolution_one,
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO agent_remediation_resolution_authority "
                "(resolution_event_id, queue_event_id, evidence_receipt, dependency_count, "
                "authority_hmac, validated_at) VALUES "
                "('resolution-one', 'queue-one', ?, ?, ?, ?)",
                (receipt, count, "0" * 64, "2026-07-18T00:00:02+00:00"),
            )
        _insert_authority(
            conn,
            resolution_event_id="resolution-one",
            queue_event_id="queue-one",
            event_detail=resolution_one,
        )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE agent_remediation_resolution_authority "
                "SET queue_event_id = 'queue-two' "
                "WHERE resolution_event_id = 'resolution-one'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "UPDATE agent_remediation_resolution_dependencies "
                "SET dependency_hash = ? WHERE resolution_event_id = 'resolution-one'",
                ("f" * 64,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO agent_remediation_resolution_dependencies "
                "(resolution_event_id, dependency_kind, dependency_id, dependency_hash) "
                "VALUES ('resolution-one', 'candidate', 'extra', ?)",
                ("e" * 64,),
            )
        changed_resolution = json.dumps(
            json.loads(resolution_one) | {"changed": True},
            sort_keys=True,
            separators=(",", ":"),
        )
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = 'resolution-one'",
            (changed_resolution,),
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        with pytest.raises(ValueError, match="material is invalid"):
            remediation_authority_material_from_connection(
                conn,
                resolution_event_id="resolution-one",
                queue_event_id="queue-one",
                event_detail=changed_resolution,
                dependencies=dependencies,
                validated_at="2026-07-18T00:00:02+00:00",
                queue_created_at=queue_created_at,
                resolution_created_at=resolution_created_at,
                agent_slug="example",
            )
        conn.execute(
            "UPDATE agent_import_events SET detail = ? WHERE id = 'resolution-one'",
            (resolution_one,),
        )
        _insert_authority(
            conn,
            resolution_event_id="resolution-one",
            queue_event_id="queue-one",
            event_detail=resolution_one,
        )
        conn.execute(
            "UPDATE agent_import_events SET created_at = '2026-07-18T00:00:01Z' "
            "WHERE id = 'resolution-one'"
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        _insert_authority(
            conn,
            resolution_event_id="resolution-one",
            queue_event_id="queue-one",
            event_detail=resolution_one,
            resolution_created_at="2026-07-18T00:00:01Z",
        )
        conn.execute(
            "UPDATE agent_import_events SET agent_slug = 'renamed-example' "
            "WHERE id = 'resolution-one'"
        )
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        conn.execute("DELETE FROM agent_import_events WHERE id = 'resolution-one'")
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        conn.commit()
    finally:
        conn.close()

    reopened = Store(path)
    conn = reopened._connect()
    try:
        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
    finally:
        conn.close()


def test_resolution_authority_schema_repairs_forged_index_and_triggers(
    tmp_path: Path,
) -> None:
    path = tmp_path / "resolution-authority-repair.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute("DROP INDEX idx_agent_remediation_authority_validated")
        conn.execute("DROP TRIGGER trg_agent_remediation_authority_finding_update")
        conn.execute(
            "CREATE INDEX idx_agent_remediation_authority_validated "
            "ON agent_remediation_resolution_authority(resolution_event_id)"
        )
        conn.execute(
            "CREATE TRIGGER trg_agent_remediation_authority_finding_update "
            "AFTER UPDATE ON agent_candidate_audit_findings "
            "BEGIN SELECT 'forged finding authority'; END"
        )
        assert remediation_authority_schema_is_current(conn) is False
        conn.commit()
    finally:
        conn.close()

    repaired = Store(path)
    conn = repaired._connect()
    try:
        assert remediation_authority_schema_is_current(conn) is True
    finally:
        conn.close()


def test_resolution_authority_wrong_table_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "resolution-authority-wrong-table.db"
    store = Store(path)
    conn = store._connect()
    try:
        conn.execute("DROP TRIGGER trg_agent_remediation_authority_insert_validate")
        conn.execute("DROP TRIGGER trg_agent_remediation_authority_projection_update")
        conn.execute("DROP TABLE agent_remediation_resolution_dependencies")
        conn.execute("DROP TABLE agent_remediation_resolution_authority")
        conn.execute(
            "CREATE TABLE agent_remediation_resolution_authority ("
            "resolution_event_id TEXT PRIMARY KEY, queue_event_id TEXT NOT NULL UNIQUE, "
            "evidence_receipt TEXT NOT NULL, dependency_count INTEGER NOT NULL, "
            "authority_hmac TEXT NOT NULL, validated_at TEXT NOT NULL)"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(
        RuntimeError,
        match="remediation resolution authority table schema is invalid",
    ):
        Store(path)


def test_resolution_authority_hmac_survives_reopen_and_plain_sqlite_cannot_forge(
    tmp_path: Path,
) -> None:
    path = tmp_path / "resolution-authority-hmac.db"
    store = Store(path)
    detail = _resolution_detail("queue-hmac")
    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('queue-hmac', 'manifest_entry_remediation_queued', "
            "'example', '{}', '2026-07-18T00:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('resolution-hmac', 'manifest_entry_remediation_resolved', "
            "'example', ?, '2026-07-18T00:00:01+00:00')",
            (detail,),
        )
        receipt, dependency_count, digest = _insert_authority(
            conn,
            resolution_event_id="resolution-hmac",
            queue_event_id="queue-hmac",
            event_detail=detail,
        )
        authority_key = conn.execute(
            "SELECT secret FROM store_secrets WHERE name = 'remediation-authority-hmac-v1'"
        ).fetchone()["secret"]
        with pytest.raises(sqlite3.IntegrityError, match="key is immutable"):
            conn.execute(
                "INSERT OR REPLACE INTO store_secrets (name, secret, created_at) "
                "VALUES ('remediation-authority-hmac-v1', randomblob(32), "
                "'2026-07-18T00:00:03+00:00')"
            )
        assert (
            conn.execute(
                "SELECT secret FROM store_secrets WHERE name = 'remediation-authority-hmac-v1'"
            ).fetchone()["secret"]
            == authority_key
        )
        conn.commit()
    finally:
        conn.close()

    reopened = Store(path)
    conn = reopened._connect()
    try:
        row = conn.execute(
            "SELECT authority_hmac, evidence_receipt, dependency_count "
            "FROM agent_remediation_resolution_authority "
            "WHERE resolution_event_id = 'resolution-hmac'"
        ).fetchone()
        assert row["authority_hmac"] == digest
        assert row["evidence_receipt"] == receipt
        assert row["dependency_count"] == dependency_count
        conn.execute(
            "DELETE FROM agent_remediation_resolution_authority "
            "WHERE resolution_event_id = 'resolution-hmac'"
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_remediation_resolution_authority "
                "WHERE resolution_event_id = 'resolution-hmac'"
            ).fetchone()[0]
            == 0
        )
        conn.rollback()
    finally:
        conn.close()

    raw = sqlite3.connect(path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="no such function"):
            raw.execute(
                "SELECT agency_verify_remediation_authority("
                "'r','q','{}','{}',1,'2026-07-18T00:00:00+00:00',?,"
                "'2026-07-18T00:00:00+00:00','2026-07-18T00:00:01+00:00','forged')",
                (hashlib.sha256(b"forged").hexdigest(),),
            )
    finally:
        raw.close()


@pytest.mark.parametrize(
    "operation",
    (
        "insert-source-url-collision",
        "update-source-url-collision",
        "insert-audit-identity-collision",
        "update-audit-identity-collision",
        "insert-event-id-collision",
        "update-event-id-collision",
        "insert-scan-entry-id-collision",
        "update-scan-entry-id-collision",
        "insert-finding-id-collision",
        "update-finding-id-collision",
    ),
)
def test_resolution_authority_invalidates_before_replace_collision(
    tmp_path: Path,
    operation: str,
) -> None:
    path = tmp_path / f"{operation}.db"
    store = Store(path)
    detail = _resolution_detail("queue-replace")
    audit_id = "audit-" + "3" * 64
    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO agent_sources (id, url, name, added_at) "
            "VALUES ('source', 'https://source.test/agents', 'source', '2026-07-18')"
        )
        conn.execute(
            "INSERT INTO agent_candidates (id, slug, quarantined_at) "
            "VALUES ('candidate', 'candidate', '2026-07-18')"
        )
        conn.execute(
            "INSERT INTO agent_candidate_audits "
            "(id, candidate_id, audit_revision, policy_hash, candidate_version, "
            "candidate_hash, active_basis_hash, deterministic_status, "
            "inference_status, verdict, created_at) VALUES "
            "(?, 'candidate', 'audit-v1', 'policy', 'version', 'hash', 'basis', "
            "'passed', 'passed', 'passed', '2026-07-18')",
            (audit_id,),
        )
        if "event-id-collision" in operation:
            conn.execute(
                "INSERT INTO agent_import_events "
                "(id, event_type, agent_slug, detail, created_at) VALUES "
                "('event-victim', 'source_scan_recorded', 'example', ?, "
                "'2026-07-17T23:59:58+00:00')",
                (json.dumps({"scan_id": "queue-scan"}),),
            )
            if operation.startswith("update-"):
                conn.execute(
                    "INSERT INTO agent_import_events "
                    "(id, event_type, agent_slug, detail, created_at) VALUES "
                    "('event-survivor', 'test', 'example', '{}', "
                    "'2026-07-17T23:59:59+00:00')"
                )
        if "scan-entry-id-collision" in operation:
            conn.executemany(
                "INSERT INTO agent_source_scans "
                "(id, source_id, status, manifest_hash, entry_count, "
                "candidate_count, quarantined_count, ignored_count, created_at) "
                "VALUES (?, 'source', 'complete', ?, 1, 0, 1, 0, '2026-07-18')",
                (
                    ("queue-scan", "queue-manifest"),
                    ("other-scan", "other-manifest"),
                ),
            )
            conn.execute(
                "INSERT INTO agent_source_scan_entries "
                "(id, scan_id, relative_path, slug, content_hash, status) VALUES "
                "('entry-victim', 'queue-scan', 'agents/victim.md', 'victim', "
                "'victim-hash', 'quarantined')"
            )
            if operation.startswith("update-"):
                conn.execute(
                    "INSERT INTO agent_source_scan_entries "
                    "(id, scan_id, relative_path, slug, content_hash, status) VALUES "
                    "('entry-survivor', 'other-scan', 'agents/survivor.md', "
                    "'survivor', 'survivor-hash', 'quarantined')"
                )
        if "finding-id-collision" in operation:
            conn.execute(
                "INSERT INTO agent_candidate_audits "
                "(id, candidate_id, audit_revision, policy_hash, candidate_version, "
                "candidate_hash, active_basis_hash, deterministic_status, "
                "inference_status, verdict, created_at) VALUES "
                "('audit-other', 'candidate', 'audit-other', 'policy', "
                "'version', 'hash', 'basis', 'passed', 'passed', 'passed', "
                "'2026-07-18')"
            )
            conn.execute(
                "INSERT INTO agent_candidate_audit_findings "
                "(id, audit_id, source, severity, code, message, "
                "evidence_hash, created_at) VALUES "
                "('finding-victim', ?, 'deterministic', 'error', 'victim', "
                "'victim', 'victim-hash', '2026-07-18')",
                (audit_id,),
            )
            if operation.startswith("update-"):
                conn.execute(
                    "INSERT INTO agent_candidate_audit_findings "
                    "(id, audit_id, source, severity, code, message, "
                    "evidence_hash, created_at) VALUES "
                    "('finding-survivor', 'audit-other', 'deterministic', 'error', "
                    "'survivor', 'survivor', 'survivor-hash', '2026-07-18')"
                )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('queue-replace', 'manifest_entry_remediation_queued', "
            "'example', '{}', '2026-07-18T00:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('resolution-replace', 'manifest_entry_remediation_resolved', "
            "'example', ?, '2026-07-18T00:00:01+00:00')",
            (detail,),
        )
        _insert_authority(
            conn,
            resolution_event_id="resolution-replace",
            queue_event_id="queue-replace",
            event_detail=detail,
        )
        conn.execute("PRAGMA recursive_triggers=OFF")
        assert conn.execute("PRAGMA recursive_triggers").fetchone()[0] == 0

        _execute_replace_collision(conn, operation)

        assert (
            conn.execute("SELECT COUNT(*) FROM agent_remediation_resolution_authority").fetchone()[
                0
            ]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_remediation_resolution_dependencies"
            ).fetchone()[0]
            == 0
        )
        conn.commit()
    finally:
        conn.close()


def test_schema_v30_redacts_legacy_source_credentials_and_tombstones_behavior(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy-source.db"
    store = Store(path)
    safe_url = "https://example.test/agents"
    source_id = store.add_agent_source(safe_url, "legacy")
    other_source_id = store.add_agent_source("https://other.test/agents", "other")
    raw = 'https://cred_user_92:cred_pass_92@example.test/agents?token=PLANTED_SECRET_92"#fragment'
    redaction = legacy_source_redaction(raw, source_id=source_id)
    assert redaction is not None
    collision_id = "legacy-redaction-collision"
    store._activate_prevalidated_agent(
        _agent(
            "safe-active-agent",
            "Keep this clean prompt active.",
            source_id=source_id,
            source=safe_url,
        )
    )
    store._activate_prevalidated_agent(
        _agent(
            "tainted-behavior-agent",
            f"Unsafe historical prompt source: {raw}",
            source_id=source_id,
            source=safe_url,
        )
    )
    store._activate_prevalidated_agent(
        _agent(
            "unrelated-safe-agent",
            "Preserve this unrelated exact active revision.",
            source_id=other_source_id,
            source="https://other.test/agents",
        )
    )

    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO agent_sources "
            "(id, url, name, added_at, enabled, trusted_for_auto_approve) "
            "VALUES (?, ?, 'collision', '2026-07-18', 1, 0)",
            (collision_id, redaction.identity),
        )
        safe_version = conn.execute(
            "SELECT version, metadata FROM agent_versions WHERE agent_slug = 'safe-active-agent'"
        ).fetchone()
        safe_metadata = json.loads(str(safe_version["metadata"]))
        safe_metadata["source"] = raw
        safe_metadata["prompt_path"] = raw
        conn.execute(
            "UPDATE agent_versions SET metadata = ? "
            "WHERE agent_slug = 'safe-active-agent' AND version = ?",
            (
                json.dumps(safe_metadata, sort_keys=True, separators=(",", ":")),
                safe_version["version"],
            ),
        )
        conn.execute(
            "UPDATE agent_active SET source = ?, prompt_path = ? "
            "WHERE agent_slug = 'safe-active-agent'",
            (raw, raw),
        )
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ?, trusted_for_auto_approve = 1 WHERE id = ?",
            (raw, raw, source_id),
        )
        conn.execute(
            "UPDATE agent_sources SET name = ? WHERE id = ?",
            (raw, collision_id),
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES ('legacy-download', ?, 'legacy-candidate', '2026-07-18', "
            "'legacy-hash', ?, 'quarantined')",
            (source_id, json.dumps({"source": raw})),
        )
        conn.execute(
            "INSERT INTO agent_candidates "
            "(id, download_id, slug, name, description, division, categories, "
            "capabilities, tool_affinity, prompt_path, source, source_version, "
            "version, hash, status, quarantined_at) "
            "VALUES ('legacy-candidate', 'legacy-download', 'legacy-candidate', "
            "'Legacy', 'Legacy candidate', 'engineering', '[]', '[]', '[]', ?, ?, "
            "'legacy', 'legacy-version', 'legacy-hash', 'pending', '2026-07-18')",
            (raw, raw),
        )
        conn.execute(
            "INSERT INTO agent_categories "
            "(id, agent_slug, category) VALUES "
            "('orphan-category', 'legacy-candidate', 'orphan-projection')"
        )
        conn.execute(
            "INSERT INTO agent_embeddings "
            "(id, agent_slug, embedding, model, created_at) VALUES "
            "('orphan-embedding', 'legacy-candidate', '[0.2]', "
            "'orphan-model', '2026-07-18')"
        )
        conn.execute(
            "INSERT INTO agent_embeddings "
            "(id, agent_slug, embedding, model, created_at) VALUES "
            "('unrelated-embedding', 'unrelated-safe-agent', '[0.3]', "
            "'safe-model', '2026-07-18')"
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES ('orphan-download', ?, 'orphan', '2026-07-18', 'orphan-hash', "
            "?, 'quarantined')",
            (other_source_id, json.dumps({"source": raw})),
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES ('cross-download', ?, 'cross-candidate', '2026-07-18', "
            "'cross-hash', ?, 'quarantined')",
            (other_source_id, json.dumps({"source": raw})),
        )
        conn.execute(
            "INSERT INTO agent_candidates "
            "(id, download_id, slug, name, description, division, categories, "
            "capabilities, tool_affinity, prompt_path, source, source_version, "
            "version, hash, status, quarantined_at) "
            "VALUES ('cross-candidate', 'cross-download', 'cross-candidate', "
            "'Cross', 'Cross-source candidate', 'engineering', '[]', '[]', '[]', "
            "'agents/cross.md', 'https://other.test/agents', 'legacy', "
            "'cross-version', 'cross-hash', 'pending', '2026-07-18')"
        )
        conn.execute(
            "INSERT INTO agent_source_scans "
            "(id, source_id, status, manifest_hash, entry_count, candidate_count, "
            "quarantined_count, ignored_count, created_at) "
            "VALUES ('legacy-scan', ?, 'complete', 'manifest-hash', 1, 1, 0, 0, "
            "'2026-07-18')",
            (source_id,),
        )
        conn.execute(
            "INSERT INTO agent_source_scan_entries "
            "(id, scan_id, relative_path, slug, content_hash, status, candidate_id) "
            "VALUES ('legacy-entry', 'legacy-scan', ?, 'legacy-candidate', "
            "'legacy-hash', 'candidate', 'legacy-candidate')",
            (raw,),
        )
        conn.execute(
            "INSERT INTO agent_source_scans "
            "(id, source_id, status, manifest_hash, entry_count, candidate_count, "
            "quarantined_count, ignored_count, created_at) "
            "VALUES ('cross-scan', ?, 'complete', 'cross-manifest', 1, 1, 0, 0, "
            "'2026-07-18')",
            (other_source_id,),
        )
        conn.execute(
            "INSERT INTO agent_source_scan_entries "
            "(id, scan_id, relative_path, slug, content_hash, status, candidate_id) "
            "VALUES ('cross-entry', 'cross-scan', 'agents/cross.md', "
            "'cross-candidate', 'cross-hash', 'candidate', 'cross-candidate')"
        )
        conn.execute(
            "INSERT INTO agent_retirements "
            "(id, agent_slug, source_id, version, hash, source_scan_id, active_record, "
            "retired_at) VALUES ('legacy-retirement', 'legacy', ?, 'legacy-version', "
            "'legacy-hash', 'legacy-scan', ?, '2026-07-18')",
            (source_id, json.dumps({"source": raw})),
        )
        conn.execute(
            "INSERT INTO agent_snapshots "
            "(id, snapshot_id, created_at, agent_count, manifest) "
            "VALUES ('legacy-snapshot', 'legacy-snapshot', '2026-07-18', 1, ?)",
            (json.dumps({"candidate_ids": ["legacy-candidate"], "source": raw}),),
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) "
            "VALUES ('legacy-event', 'source_error', '', ?, '2026-07-18')",
            (json.dumps({"source": raw}),),
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) "
            "VALUES ('legacy-queue', 'manifest_entry_remediation_queued', "
            "'legacy-candidate', ?, '2026-07-18T00:00:00+00:00')",
            (
                json.dumps(
                    {
                        "download_id": "cross-download",
                        "origin": safe_url,
                        "receipt": {},
                        "relative_path": "agents/legacy.md",
                        "source_id": "tampered-source-id",
                    }
                ),
            ),
        )
        legacy_resolution_detail = _resolution_detail("legacy-queue")
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) "
            "VALUES ('legacy-resolution', 'manifest_entry_remediation_resolved', "
            "'legacy-candidate', ?, '2026-07-18T00:00:01+00:00')",
            (legacy_resolution_detail,),
        )
        _insert_authority(
            conn,
            resolution_event_id="legacy-resolution",
            queue_event_id="legacy-queue",
            event_detail=legacy_resolution_detail,
            agent_slug="legacy-candidate",
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (29)")
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    reopened = Store(path)

    conn = migrated._connect()
    try:
        source = dict(
            conn.execute(
                "SELECT url, name, enabled, trusted_for_auto_approve "
                "FROM agent_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        )
        collision_name = conn.execute(
            "SELECT name FROM agent_sources WHERE id = ?",
            (collision_id,),
        ).fetchone()["name"]
        events = [
            dict(row)
            for row in conn.execute(
                "SELECT event_type, detail FROM agent_import_events "
                "WHERE event_type = 'legacy_source_credentials_redacted'"
            )
        ]
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        database_text = _all_database_text(conn)
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        remaining_cross_scans = conn.execute(
            "SELECT COUNT(*) FROM agent_source_scans WHERE id = 'cross-scan'"
        ).fetchone()[0]
        remaining_authority = conn.execute(
            "SELECT COUNT(*) FROM agent_remediation_resolution_authority"
        ).fetchone()[0]
        projection_counts = {
            "unrelated_categories": conn.execute(
                "SELECT COUNT(*) FROM agent_categories WHERE agent_slug = 'unrelated-safe-agent'"
            ).fetchone()[0],
            "unrelated_embeddings": conn.execute(
                "SELECT COUNT(*) FROM agent_embeddings WHERE agent_slug = 'unrelated-safe-agent'"
            ).fetchone()[0],
            "orphan_categories": conn.execute(
                "SELECT COUNT(*) FROM agent_categories WHERE agent_slug = 'legacy-candidate'"
            ).fetchone()[0],
            "orphan_embeddings": conn.execute(
                "SELECT COUNT(*) FROM agent_embeddings WHERE agent_slug = 'legacy-candidate'"
            ).fetchone()[0],
        }
    finally:
        conn.close()

    assert version == SCHEMA_VERSION == 45
    assert source["url"].startswith(redaction.identity + "-")
    assert source["name"] == "Legacy source redacted (disabled)"
    assert source["enabled"] == 0
    assert source["trusted_for_auto_approve"] == 0
    assert collision_name == "Legacy source name redacted (disabled)"
    assert len(events) == 1
    assert "candidates_tombstoned=2" in events[0]["detail"]
    assert "versions_tombstoned=2" in events[0]["detail"]
    assert "snapshots_tombstoned=1" in events[0]["detail"]
    assert integrity == "ok"
    assert foreign_key_errors == []
    assert remaining_cross_scans == 0
    assert remaining_authority == 0
    assert "PLANTED_SECRET_92" not in database_text
    assert "cred_user_92" not in database_text
    assert "cred_pass_92" not in database_text
    assert {agent["slug"] for agent in migrated.get_active_roster_as_catalog()} == {
        "unrelated-safe-agent"
    }
    assert projection_counts == {
        "unrelated_categories": 2,
        "unrelated_embeddings": 1,
        "orphan_categories": 0,
        "orphan_embeddings": 0,
    }
    assert remediation_queue_snapshot(migrated)["pending"] == []
    assert remediation_queue_snapshot(migrated)["history"] == []
    assert remediation_queue_snapshot(reopened)["pending"] == []
    assert remediation_queue_snapshot(reopened)["history"] == []
    storage_bytes = _sqlite_storage_bytes(path)
    assert b"PLANTED_SECRET_92" not in storage_bytes
    assert b"cred_user_92" not in storage_bytes
    assert b"cred_pass_92" not in storage_bytes


@pytest.mark.parametrize("authority_kind", ["audit", "finding", "status"])
def test_schema_v30_deletes_cross_source_tainted_authority_and_full_scan(
    tmp_path: Path,
    authority_kind: str,
) -> None:
    path = tmp_path / f"cross-source-{authority_kind}.db"
    store = Store(path)
    unsafe_source_id = store.add_agent_source("https://unsafe.test/agents", "unsafe")
    other_source_id = store.add_agent_source("https://other.test/agents", "other")
    raw = (
        "https://authority_user:authority_password@unsafe.test/agents"
        f'?token=PLANTED_{authority_kind.upper()}_AUTHORITY_"'
    )
    candidate_id = f"{authority_kind}-candidate"
    download_id = f"{authority_kind}-download"
    scan_id = f"{authority_kind}-scan"
    audit_id = f"{authority_kind}-audit"

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, unsafe_source_id),
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES (?, ?, ?, '2026-07-18', 'clean-hash', ?, 'quarantined')",
            (
                download_id,
                other_source_id,
                candidate_id,
                json.dumps({"prompt_body": "Clean cross-source prompt."}),
            ),
        )
        conn.execute(
            "INSERT INTO agent_candidates "
            "(id, download_id, slug, name, description, division, categories, "
            "capabilities, tool_affinity, prompt_path, source, source_version, "
            "version, hash, status, quarantined_at) "
            "VALUES (?, ?, ?, 'Cross source', 'Clean candidate', 'engineering', "
            "'[]', '[]', '[]', 'agents/cross.md', 'https://other.test/agents', "
            "'revision', 'candidate-version', 'clean-hash', 'pending', '2026-07-18')",
            (candidate_id, download_id, candidate_id),
        )
        conn.execute(
            "INSERT INTO agent_source_scans "
            "(id, source_id, status, manifest_hash, entry_count, candidate_count, "
            "quarantined_count, ignored_count, created_at) "
            "VALUES (?, ?, 'complete', 'clean-manifest', 1, 1, 0, 0, '2026-07-18')",
            (scan_id, other_source_id),
        )
        conn.execute(
            "INSERT INTO agent_source_scan_entries "
            "(id, scan_id, relative_path, slug, content_hash, status, candidate_id) "
            "VALUES (?, ?, 'agents/cross.md', ?, 'clean-hash', 'candidate', ?)",
            (f"{authority_kind}-entry", scan_id, candidate_id, candidate_id),
        )
        if authority_kind in {"audit", "finding"}:
            inference_evidence = (
                json.dumps({"source": raw}) if authority_kind == "audit" else '{"evidence":"clean"}'
            )
            conn.execute(
                "INSERT INTO agent_candidate_audits "
                "(id, candidate_id, audit_revision, policy_hash, candidate_version, "
                "candidate_hash, active_basis_hash, deterministic_status, "
                "inference_status, verdict, provider, inference_evidence, created_at) "
                "VALUES (?, ?, 'audit-v1', 'policy-hash', 'candidate-version', "
                "'clean-hash', 'basis-hash', 'passed', 'passed', 'passed', "
                "'provider', ?, '2026-07-18')",
                (audit_id, candidate_id, inference_evidence),
            )
        if authority_kind == "finding":
            conn.execute(
                "INSERT INTO agent_candidate_audit_findings "
                "(id, audit_id, source, severity, code, message, evidence_hash, created_at) "
                "VALUES ('finding-id', ?, 'inference', 'error', 'unsafe_source', ?, "
                "'evidence-hash', '2026-07-18')",
                (audit_id, f"Finding retained a legacy source: {raw}"),
            )
        if authority_kind == "status":
            conn.execute(
                "INSERT INTO agent_candidate_status_events "
                "(id, candidate_id, event_type, from_status, to_status, reason, "
                "audit_id, created_at) VALUES ('status-id', ?, 'approved', 'pending', "
                "'approved', ?, '', '2026-07-18')",
                (candidate_id, f"Approval retained a legacy source: {raw}"),
            )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (29)")
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    reopened = Store(path)
    conn = migrated._connect()
    try:
        counts = {
            table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in (
                "agent_downloads",
                "agent_candidates",
                "agent_candidate_audits",
                "agent_candidate_audit_findings",
                "agent_candidate_status_events",
                "agent_source_scans",
                "agent_source_scan_entries",
            )
        }
        database_text = _all_database_text(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()

    assert counts == dict.fromkeys(counts, 0)
    assert f"PLANTED_{authority_kind.upper()}_AUTHORITY" not in database_text
    assert "authority_password" not in database_text
    assert integrity == "ok"
    assert foreign_key_errors == []
    assert remediation_queue_snapshot(migrated)["pending"] == []
    assert remediation_queue_snapshot(migrated)["history"] == []
    assert remediation_queue_snapshot(reopened)["pending"] == []
    assert remediation_queue_snapshot(reopened)["history"] == []


def test_schema_v30_preserves_immutable_version_and_deactivates_tainted_projection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "projection-mismatch.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    behavior_source_id = store.add_agent_source(
        "https://behavior.test/agents",
        "behavior",
    )
    raw = "https://user:password@example.test/agents?token=PLANTED_PROJECTION_SECRET"
    agent = _agent(
        "projection-agent",
        "Keep the immutable prompt byte-for-byte.",
        source_id=behavior_source_id,
        source="https://behavior.test/agents",
    )
    agent["content"] = agent["prompt_body"]
    agent["version"] = immutable_revision_version(agent)
    store._activate_prevalidated_agent(agent)

    conn = store._connect()
    try:
        before = dict(
            conn.execute(
                "SELECT version, hash, content, metadata FROM agent_versions "
                "WHERE agent_slug = 'projection-agent'"
            ).fetchone()
        )
        conn.execute(
            "INSERT INTO agent_embeddings "
            "(id, agent_slug, embedding, model, created_at) "
            "VALUES ('projection-embedding', 'projection-agent', '[0.1]', "
            "'fixture-model', '2026-07-18')"
        )
        conn.execute(
            "UPDATE agent_active SET source = ?, prompt_path = ? "
            "WHERE agent_slug = 'projection-agent'",
            (raw, raw),
        )
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (29)")
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    conn = migrated._connect()
    try:
        after = dict(
            conn.execute(
                "SELECT version, hash, content, metadata FROM agent_versions "
                "WHERE agent_slug = 'projection-agent'"
            ).fetchone()
        )
        active_count = conn.execute(
            "SELECT COUNT(*) FROM agent_active WHERE agent_slug = 'projection-agent'"
        ).fetchone()[0]
        category_count = conn.execute(
            "SELECT COUNT(*) FROM agent_categories WHERE agent_slug = 'projection-agent'"
        ).fetchone()[0]
        embedding_count = conn.execute(
            "SELECT COUNT(*) FROM agent_embeddings WHERE agent_slug = 'projection-agent'"
        ).fetchone()[0]
        database_text = _all_database_text(conn)
    finally:
        conn.close()

    reconstructed = {
        **json.loads(after["metadata"]),
        "content": after["content"],
        "hash": after["hash"],
    }
    assert after == before
    assert immutable_revision_version(reconstructed) == after["version"]
    assert active_count == 0
    assert category_count == 0
    assert embedding_count == 0
    assert "PLANTED_PROJECTION_SECRET" not in database_text


def test_schema_v30_tombstones_behavior_owned_only_by_unsafe_source_id(
    tmp_path: Path,
) -> None:
    path = tmp_path / "source-id-provenance.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    store._activate_prevalidated_agent(
        _agent(
            "source-id-only-agent",
            "This prompt and every semantic field are clean.",
            source_id=source_id,
            source="https://neutral.test/agents",
        )
    )
    raw = "https://owner:secret@example.test/agents?token=PLANTED_SOURCE_ID_ONLY"

    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO agent_embeddings "
            "(id, agent_slug, embedding, model, created_at) VALUES "
            "('source-id-embedding', 'source-id-only-agent', '[0.1]', "
            "'fixture-model', '2026-07-18')"
        )
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    conn = migrated._connect()
    try:
        counts = {
            table: int(
                conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE agent_slug = "  # nosec B608
                    "'source-id-only-agent'"
                ).fetchone()[0]
            )
            for table in ("agent_versions", "agent_active", "agent_categories", "agent_embeddings")
        }
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()

    assert counts == dict.fromkeys(counts, 0)
    assert b"PLANTED_SOURCE_ID_ONLY" not in _sqlite_storage_bytes(path)


def test_schema_v30_disables_nonsecret_unsupported_source_without_rewriting_history(
    tmp_path: Path,
) -> None:
    path = tmp_path / "unsupported-source.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    legacy_source = "fixture://legacy/agents"
    store._activate_prevalidated_agent(
        _agent(
            "legacy-visible-agent",
            "Preserve this faithful nonsecret behavior.",
            source_id=source_id,
            source=legacy_source,
        )
    )
    conn = store._connect()
    try:
        before_version = dict(
            conn.execute(
                "SELECT * FROM agent_versions WHERE agent_slug = 'legacy-visible-agent'"
            ).fetchone()
        )
        before_active = dict(
            conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = 'legacy-visible-agent'"
            ).fetchone()
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES ('visible-download', ?, 'visible-candidate', '2026-07-18', "
            "'visible-hash', ?, 'quarantined')",
            (source_id, json.dumps({"source": legacy_source})),
        )
        conn.execute(
            "INSERT INTO agent_candidates "
            "(id, download_id, slug, name, description, division, categories, "
            "capabilities, tool_affinity, prompt_path, source, source_version, "
            "version, hash, status, quarantined_at) VALUES "
            "('visible-candidate', 'visible-download', 'visible-candidate', "
            "'Visible', 'Faithful historical candidate', 'engineering', '[]', '[]', "
            "'[]', 'agents/visible.md', ?, 'legacy', 'visible-version', "
            "'visible-hash', 'pending', '2026-07-18')",
            (legacy_source,),
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('visible-event', 'source_downloaded', 'visible-candidate', ?, '2026-07-18')",
            (json.dumps({"source": legacy_source}),),
        )
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ?, trusted_for_auto_approve = 1 WHERE id = ?",
            (legacy_source, legacy_source, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    conn = migrated._connect()
    try:
        source = dict(
            conn.execute(
                "SELECT url, name, enabled, trusted_for_auto_approve "
                "FROM agent_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        )
        after_version = dict(
            conn.execute(
                "SELECT * FROM agent_versions WHERE agent_slug = 'legacy-visible-agent'"
            ).fetchone()
        )
        after_active = dict(
            conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = 'legacy-visible-agent'"
            ).fetchone()
        )
        preserved = {
            table: int(
                conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE id = ?",  # nosec B608
                    (record_id,),
                ).fetchone()[0]
            )
            for table, record_id in (
                ("agent_downloads", "visible-download"),
                ("agent_candidates", "visible-candidate"),
                ("agent_import_events", "visible-event"),
            )
        }
        purge_pending = int(
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'source-redaction-purge-pending'"
            ).fetchone()[0]
        )
    finally:
        conn.close()

    assert source["url"].startswith("redacted://legacy-source/")
    assert source["name"] == "Legacy source redacted (disabled)"
    assert source["enabled"] == 0
    assert source["trusted_for_auto_approve"] == 0
    assert after_version == before_version
    assert after_active == before_active
    assert preserved == dict.fromkeys(preserved, 1)
    assert purge_pending == 0


def test_schema_v30_purges_default_json_ascii_escaped_non_ascii_credentials(
    tmp_path: Path,
) -> None:
    path = tmp_path / "ascii-escaped-credential.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    other_source_id = store.add_agent_source("https://other.test/agents", "other")
    raw = "https://usér:päss@example.test/agents?token=秘密"
    serialized = json.dumps({"source": raw})
    assert "\\u00e9" in serialized
    assert "\\u79d8" in serialized

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES ('ascii-download', ?, 'ascii-agent', '2026-07-18', "
            "'ascii-hash', ?, 'quarantined')",
            (other_source_id, serialized),
        )
        conn.execute(
            "INSERT INTO agent_import_events "
            "(id, event_type, agent_slug, detail, created_at) VALUES "
            "('ascii-event', 'source_error', '', ?, '2026-07-18')",
            (serialized,),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    conn = migrated._connect()
    try:
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_downloads WHERE id = 'ascii-download'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events WHERE id = 'ascii-event'"
            ).fetchone()[0]
            == 0
        )
        database_text = _all_database_text(conn)
    finally:
        conn.close()

    assert "usér" not in database_text
    assert "\\u00e9" not in database_text
    storage = _sqlite_storage_bytes(path)
    assert raw.encode() not in storage
    assert serialized.encode() not in storage
    assert b"\\u00e9" not in storage
    assert b"\\u79d8" not in storage


def test_schema_v30_independently_purges_credential_bearing_source_name(
    tmp_path: Path,
) -> None:
    path = tmp_path / "credential-name.db"
    store = Store(path)
    safe_url = "https://example.test/agents"
    source_id = store.add_agent_source(safe_url, "Safe name")
    raw_name = "https://name_user:name_pass@example.test/agents?token=PLANTED_NAME_ONLY"

    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET name = ?, trusted_for_auto_approve = 1 WHERE id = ?",
            (raw_name, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    conn = migrated._connect()
    try:
        row = dict(
            conn.execute(
                "SELECT url, name, enabled, trusted_for_auto_approve "
                "FROM agent_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        )
        event_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM agent_import_events "
                "WHERE event_type = 'legacy_source_name_redacted'"
            ).fetchone()[0]
        )
    finally:
        conn.close()

    assert row == {
        "url": safe_url,
        "name": "Legacy source name redacted (disabled)",
        "enabled": 0,
        "trusted_for_auto_approve": 0,
    }
    assert event_count == 1
    assert b"PLANTED_NAME_ONLY" not in _sqlite_storage_bytes(path)
    assert Store(path).list_agent_sources() == []


@pytest.mark.parametrize("control", ["\t", "\n", "\r", "\x85", "\u2066"])
def test_schema_v30_purges_legacy_control_bearing_sources(
    tmp_path: Path,
    control: str,
) -> None:
    path = tmp_path / f"control-{ord(control):x}.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    raw = f"https://example.test/agents{control}PLANTED_CONTROL_{ord(control):X}"
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    assert migrated.list_agent_sources() == []
    assert f"PLANTED_CONTROL_{ord(control):X}".encode() not in _sqlite_storage_bytes(path)


@pytest.mark.parametrize(
    ("case", "raw"),
    [
        ("relative-query", "relative/agents?token=PLANTED_LOCAL_QUERY"),
        ("relative-fragment", "relative/agents#PLANTED_LOCAL_FRAGMENT"),
        ("windows-query", r"C:\agents\roster.json?token=PLANTED_WINDOWS_QUERY"),
    ],
)
def test_schema_v30_purges_legacy_local_source_opaque_components(
    tmp_path: Path,
    case: str,
    raw: str,
) -> None:
    path = tmp_path / f"local-opaque-{case}.db"
    store = Store(path)
    source_id = store.add_agent_source("relative/agents", "legacy")
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    migrated = Store(path)
    assert migrated.list_agent_sources() == []
    marker = raw[raw.index("PLANTED_") :].encode()
    assert marker not in _sqlite_storage_bytes(path)


@pytest.mark.parametrize(
    ("url", "name", "marker"),
    [
        (123, "Integer URL", b""),
        ("https://example.test/integer-name", 456, b""),
        (
            sqlite3.Binary(
                b"https://blob_user:blob_pass@example.test/agents?token=PLANTED_BLOB_URL"
            ),
            "BLOB URL",
            b"PLANTED_BLOB_URL",
        ),
        (
            "https://example.test/blob-name",
            sqlite3.Binary(
                b"https://blob_name:blob_pass@example.test/agents?token=PLANTED_BLOB_NAME"
            ),
            b"PLANTED_BLOB_NAME",
        ),
        (
            sqlite3.Binary(b"\xffPLANTED_NON_UTF8_SOURCE\xfe"),
            "Non-UTF8 URL",
            b"PLANTED_NON_UTF8_SOURCE",
        ),
    ],
)
def test_schema_v30_disables_non_text_legacy_source_fields_and_purges_bytes(
    tmp_path: Path,
    url: object,
    name: object,
    marker: bytes,
) -> None:
    path = tmp_path / f"non-text-{len(marker)}-{type(url).__name__}-{type(name).__name__}.db"
    source_id = _create_non_affinity_legacy_database(path, url=url, name=name)

    migrated = Store(path)
    reopened = Store(path)
    conn = migrated._connect()
    try:
        row = dict(
            conn.execute(
                "SELECT url, name, typeof(url) AS url_type, typeof(name) AS name_type, "
                "enabled, trusted_for_auto_approve FROM agent_sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        )
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()

    assert row["url_type"] == "text"
    assert row["name_type"] == "text"
    assert row["enabled"] == 0
    assert row["trusted_for_auto_approve"] == 0
    assert migrated.list_agent_sources() == []
    assert reopened.list_agent_sources() == []
    if marker:
        assert marker not in _sqlite_storage_bytes(path)


def test_store_uses_secure_delete_for_every_roster_connection(tmp_path: Path) -> None:
    store = Store(tmp_path / "secure-delete.db")
    conn = store._connect()
    try:
        assert int(conn.execute("PRAGMA secure_delete").fetchone()[0]) == 1
    finally:
        conn.close()


def test_schema_v30_retries_physical_purge_after_post_commit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "retry-purge.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    raw = "https://retry:password@example.test/agents?token=PLANTED_RETRY_PURGE"
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        _set_schema_v29(conn)
        conn.commit()
    finally:
        conn.close()

    original_purge = Store._purge_redacted_storage
    attempts = 0

    def fail_once(subject: Store, connection: sqlite3.Connection) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("forced post-commit physical purge failure")
        original_purge(subject, connection)

    monkeypatch.setattr(Store, "_purge_redacted_storage", fail_once)
    with pytest.raises(RuntimeError, match="forced post-commit physical purge failure"):
        Store(path)

    conn = sqlite3.connect(path)
    try:
        version = int(conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0])
        pending = int(
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'source-redaction-purge-pending'"
            ).fetchone()[0]
        )
        logical_text = "\n".join(
            str(value)
            for row in conn.execute("SELECT url, name FROM agent_sources")
            for value in row
        )
    finally:
        conn.close()
    assert version == SCHEMA_VERSION
    assert pending == 1
    assert "PLANTED_RETRY_PURGE" not in logical_text

    reopened = Store(path)
    conn = reopened._connect()
    try:
        assert (
            conn.execute(
                "SELECT value FROM store_counters WHERE name = 'source-redaction-purge-pending'"
            ).fetchone()[0]
            == 0
        )
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    assert attempts == 2
    assert b"PLANTED_RETRY_PURGE" not in _sqlite_storage_bytes(path)


def test_schema_v30_source_redaction_failure_rolls_back_without_echoing_secret(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rollback-source.db"
    store = Store(path)
    source_id = store.add_agent_source("https://example.test/agents", "legacy")
    raw = "https://example.test/agents?token=PLANTED_ROLLBACK_SECRET"
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE agent_sources SET url = ?, name = ? WHERE id = ?",
            (raw, raw, source_id),
        )
        conn.execute("DELETE FROM schema_version")
        conn.execute("INSERT INTO schema_version (version) VALUES (29)")
        conn.execute(
            "CREATE TRIGGER force_source_redaction_failure "
            "BEFORE UPDATE OF url ON agent_sources WHEN OLD.id = '"
            + source_id
            + "' BEGIN SELECT RAISE(ABORT, 'forced source redaction failure'); END"
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(sqlite3.IntegrityError) as captured:
        Store(path)
    assert "PLANTED_ROLLBACK_SECRET" not in str(captured.value)

    conn = sqlite3.connect(path)
    try:
        persisted_url = conn.execute(
            "SELECT url FROM agent_sources WHERE id = ?",
            (source_id,),
        ).fetchone()[0]
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM agent_import_events "
            "WHERE event_type = 'legacy_source_credentials_redacted'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert persisted_url == raw
    assert version == 29
    assert evidence_count == 0
