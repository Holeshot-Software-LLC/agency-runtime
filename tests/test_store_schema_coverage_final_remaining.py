"""Final adversarial branch coverage for the canonical SQLite schema helpers."""

from __future__ import annotations

import builtins
import json
import sqlite3
from collections.abc import Iterator

import pytest

from agency_runtime.core.roster.source_identity import SourceIdentityError
from agency_runtime.core.store import schema


class _FetchResult:
    def __init__(
        self,
        *,
        one: object = None,
        rows: tuple[dict[str, object], ...] = (),
    ) -> None:
        self._one = one
        self._rows = rows

    def fetchone(self) -> object:
        return self._one

    def fetchall(self) -> tuple[dict[str, object], ...]:
        return self._rows

    def __iter__(self) -> Iterator[dict[str, object]]:
        return iter(self._rows)


class _RowsConnection:
    def __init__(self, rows: tuple[dict[str, object], ...]) -> None:
        self.rows = rows

    def execute(self, _sql: str, _parameters: object = ()) -> _FetchResult:
        return _FetchResult(rows=self.rows)


class _SequenceConnection:
    def __init__(
        self,
        *,
        authority_exists: bool = False,
        invalid: object = None,
        duplicate: object = None,
        maximum: int = 0,
        counter: object = None,
    ) -> None:
        self.authority_exists = authority_exists
        self.invalid = invalid
        self.duplicate = duplicate
        self.maximum = maximum
        self.counter = counter
        self.statements: list[str] = []

    def execute(self, sql: str, _parameters: object = ()) -> _FetchResult:
        self.statements.append(sql)
        if "sqlite_master" in sql and "agent_remediation_resolution_authority" in sql:
            return _FetchResult(one=object() if self.authority_exists else None)
        if "WHERE typeof(event_sequence)" in sql:
            return _FetchResult(one=self.invalid)
        if "GROUP BY event_sequence" in sql:
            return _FetchResult(one=self.duplicate)
        if "COALESCE(MAX(event_sequence)" in sql:
            return _FetchResult(one={"maximum": self.maximum})
        if "WHERE name = 'agent-import-event-sequence'" in sql:
            return _FetchResult(one=self.counter)
        return _FetchResult()


@pytest.fixture
def base_connection() -> Iterator[sqlite3.Connection]:
    """Create the v1 baseline without involving the higher-level Store wrapper."""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(schema.SCHEMA_V1)
    try:
        yield connection
    finally:
        connection.close()


def _resolution_detail_data(
    queue_event_id: str = "queue-event",
    *,
    resolution: str = "superseded_by_candidate",
) -> dict[str, object]:
    return {
        "audit_id": "audit-" + "3" * 64,
        "audit_revision": "sha256:" + "4" * 64,
        "candidate_download_id": "candidate-download",
        "candidate_hash": "5" * 64,
        "candidate_id": "candidate",
        "download_id": "queue-download",
        "original_hash": "1" * 64,
        "origin": "agents/example.md",
        "policy_hash": "6" * 64,
        "queue_event_id": queue_event_id,
        "relative_path": "agents/example.md",
        "resolution": resolution,
        "scan_id": "candidate-scan",
        "source_hash": "2" * 64,
        "source_id": "source",
    }


def _resolution_detail(
    queue_event_id: str = "queue-event",
    *,
    resolution: str = "superseded_by_candidate",
) -> str:
    return json.dumps(
        _resolution_detail_data(queue_event_id, resolution=resolution),
        sort_keys=True,
        separators=(",", ":"),
    )


def _authority_dependencies(
    resolution_event_id: str = "resolution-event",
    queue_event_id: str = "queue-event",
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
        {"hash": f"{index:064x}", "id": dependency_id, "kind": kind}
        for index, (kind, dependency_id) in enumerate(identities, start=1)
    ]


def _minimal_key_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE store_secrets (
            name TEXT PRIMARY KEY,
            secret BLOB NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE agent_remediation_resolution_authority (
            resolution_event_id TEXT PRIMARY KEY
        );
        """
    )
    return connection


def _create_tombstone_authority_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE agent_remediation_resolution_authority (
            resolution_event_id TEXT PRIMARY KEY,
            queue_event_id TEXT NOT NULL,
            evidence_receipt TEXT NOT NULL,
            authority_hmac TEXT NOT NULL,
            validated_at TEXT NOT NULL
        )
        """
    )


def test_v30_import_events_without_event_sequence_upgrade_atomically() -> None:
    """A real pre-v31 table must gain its column before v31 indexes are parsed."""

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE agent_import_events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            agent_slug TEXT,
            detail TEXT,
            created_at TEXT NOT NULL
        );
        INSERT INTO agent_import_events
            (id, event_type, agent_slug, detail, created_at)
        VALUES
            ('legacy-one', 'legacy', '', '{}', '2026-07-18T00:00:00+00:00'),
            ('legacy-two', 'legacy', '', '{}', '2026-07-18T00:00:01+00:00');
        CREATE TABLE schema_version (version INTEGER PRIMARY KEY);
        INSERT INTO schema_version (version) VALUES (30);
        """
    )
    try:
        purge_pending = schema.migrate_schema(
            connection,
            now=lambda: "2026-07-18T00:00:02+00:00",
            capture_content=lambda: False,
        )

        assert purge_pending is False
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT id, event_sequence FROM agent_import_events ORDER BY event_sequence"
            )
        ] == [("legacy-one", 1), ("legacy-two", 2)]
        assert schema.agent_import_event_sequence_schema_is_current(connection) is True
        assert schema.remediation_indexes_are_current(connection) is True
        assert (
            connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            == schema.SCHEMA_VERSION
        )
    finally:
        connection.close()


def test_bounded_text_and_timestamp_reject_malformed_inputs() -> None:
    surrogate = "\ud800"

    assert schema._bounded_utf8_text(surrogate, 8) is None
    assert schema._aware_timestamp(None) is None
    assert schema._aware_timestamp("not-a-timestamp") is None
    assert schema._aware_timestamp("2026-07-18T00:00:00") is None
    assert schema._aware_timestamp("2026-07-18T00:00:00Z") == schema._aware_timestamp(
        "2026-07-18T00:00:00+00:00"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("audit_id", ""),
        ("origin", ""),
        ("queue_event_id", "wrong-queue"),
        ("resolution", "invented"),
        ("audit_revision", "sha256:not-a-hash"),
        ("candidate_hash", "not-a-hash"),
    ],
)
def test_resolution_detail_rejects_each_bounded_authority_violation(
    field: str,
    value: object,
) -> None:
    loaded = _resolution_detail_data()
    loaded[field] = value
    encoded = json.dumps(loaded, sort_keys=True, separators=(",", ":"))

    assert schema._remediation_resolution_detail(encoded, queue_event_id="queue-event") is None


def test_resolution_detail_rejects_non_text_and_malformed_json() -> None:
    assert schema._remediation_resolution_detail(None, queue_event_id="queue-event") is None
    assert schema._remediation_resolution_detail("{", queue_event_id="queue-event") is None


def test_dependency_normalization_rejects_shape_content_order_and_duplicates() -> None:
    dependencies = _authority_dependencies()

    assert schema._normalized_authority_dependencies(None) is None
    assert schema._normalized_authority_dependencies([{"kind": "candidate"}]) is None
    assert (
        schema._normalized_authority_dependencies(
            [{"hash": "0" * 64, "id": "candidate", "kind": "invented"}]
        )
        is None
    )
    assert schema._normalized_authority_dependencies(list(reversed(dependencies))) is None
    assert schema._normalized_authority_dependencies([dependencies[0], dependencies[0]]) is None


def test_dependency_closure_rejects_each_incomplete_or_ambiguous_graph() -> None:
    dependencies = _authority_dependencies()
    arguments: dict[str, str | None] = {
        "resolution_event_id": "resolution-event",
        "queue_event_id": "queue-event",
        "resolution": "superseded_by_candidate",
        "agent_slug": "example",
    }

    assert (
        schema._authority_dependency_closure_is_valid(
            dependencies,
            **(arguments | {"resolution_event_id": "wrong-resolution"}),
        )
        is False
    )
    assert (
        schema._authority_dependency_closure_is_valid(
            dependencies,
            **(arguments | {"queue_event_id": "wrong-queue"}),
        )
        is False
    )
    assert (
        schema._authority_dependency_closure_is_valid(
            [item for item in dependencies if item["kind"] != "candidate_audit"],
            **arguments,
        )
        is False
    )

    duplicate_transform = [
        *dependencies,
        {"hash": "a" * 64, "id": "source-download-a", "kind": "source_download"},
        {"hash": "b" * 64, "id": "source-download-b", "kind": "source_download"},
    ]
    assert schema._authority_dependency_closure_is_valid(duplicate_transform, **arguments) is False
    partial_transform = [
        *dependencies,
        {"hash": "a" * 64, "id": "source-download", "kind": "source_download"},
    ]
    assert schema._authority_dependency_closure_is_valid(partial_transform, **arguments) is False
    assert (
        schema._authority_dependency_closure_is_valid(
            dependencies,
            **(arguments | {"resolution": "remediated_candidate"}),
        )
        is False
    )
    complete_transform = [
        *dependencies,
        {"hash": "a" * 64, "id": "different-agent", "kind": "candidate_slug"},
        {"hash": "b" * 64, "id": "source-download", "kind": "source_download"},
        {"hash": "c" * 64, "id": "transform", "kind": "transformation_event"},
    ]
    assert schema._authority_dependency_closure_is_valid(complete_transform, **arguments) is False


def test_receipt_parser_rejects_bounded_schema_canonicalization_and_closure_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = _authority_dependencies()
    canonical = schema.canonical_remediation_authority_receipt(dependencies)
    loaded = json.loads(canonical)

    assert schema._parsed_remediation_authority_receipt(None) is None
    assert schema._parsed_remediation_authority_receipt("{") is None
    assert (
        schema._parsed_remediation_authority_receipt(
            json.dumps(loaded | {"schema": "wrong"}, sort_keys=True, separators=(",", ":"))
        )
        is None
    )
    invalid_dependencies = loaded | {"dependencies": []}
    assert (
        schema._parsed_remediation_authority_receipt(
            json.dumps(invalid_dependencies, sort_keys=True, separators=(",", ":"))
        )
        is None
    )
    assert schema._parsed_remediation_authority_receipt(json.dumps(loaded, indent=2)) is None
    assert (
        schema._parsed_remediation_authority_receipt(
            canonical,
            resolution_event_id="wrong-resolution",
        )
        is None
    )

    def fail_dump(*_args: object, **_kwargs: object) -> str:
        raise TypeError("forced serialization failure")

    monkeypatch.setattr(schema.json, "dumps", fail_dump)
    assert schema._parsed_remediation_authority_receipt(canonical) is None


def test_canonical_receipt_rejects_an_empty_dependency_graph() -> None:
    with pytest.raises(ValueError, match="dependencies are invalid"):
        schema.canonical_remediation_authority_receipt([])


def test_authority_hmac_rejects_type_encoding_and_bound_violations() -> None:
    values: dict[str, object] = {
        "resolution_event_id": "resolution-event",
        "queue_event_id": "queue-event",
        "event_detail": _resolution_detail(),
        "evidence_receipt": schema.canonical_remediation_authority_receipt(
            _authority_dependencies()
        ),
        "dependency_count": 9,
        "validated_at": "2026-07-18T00:00:02+00:00",
    }

    assert schema._remediation_authority_hmac(b"short", **values) == ""
    assert (
        schema._remediation_authority_hmac(b"k" * 32, **(values | {"dependency_count": True})) == ""
    )
    assert (
        schema._remediation_authority_hmac(
            b"k" * 32,
            **(values | {"resolution_event_id": object()}),
        )
        == ""
    )
    assert (
        schema._remediation_authority_hmac(
            b"k" * 32,
            **(values | {"resolution_event_id": "\ud800"}),
        )
        == ""
    )
    assert (
        schema._remediation_authority_hmac(
            b"k" * 32,
            **(values | {"resolution_event_id": ""}),
        )
        == ""
    )


def test_verify_authority_rejects_invalid_chronology_after_parsing() -> None:
    dependencies = _authority_dependencies()
    receipt = schema.canonical_remediation_authority_receipt(dependencies)

    assert (
        schema.verify_remediation_authority(
            b"k" * 32,
            "resolution-event",
            "queue-event",
            _resolution_detail(),
            receipt,
            len(dependencies),
            "2026-07-18T00:00:02+00:00",
            "0" * 64,
            "invalid-queued-at",
            "2026-07-18T00:00:01+00:00",
            "example",
        )
        == 0
    )


def test_authority_material_refuses_a_missing_store_key() -> None:
    connection = _minimal_key_connection()
    try:
        with pytest.raises(RuntimeError, match="authority key is unavailable"):
            schema.remediation_authority_material_from_connection(
                connection,
                resolution_event_id="resolution-event",
                queue_event_id="queue-event",
                event_detail=_resolution_detail(),
                dependencies=_authority_dependencies(),
                validated_at="2026-07-18T00:00:02+00:00",
                queue_created_at="2026-07-18T00:00:00+00:00",
                resolution_created_at="2026-07-18T00:00:01+00:00",
                agent_slug="example",
            )
    finally:
        connection.close()


def test_receipt_membership_and_scan_id_fail_closed_on_malformed_json() -> None:
    assert schema.remediation_receipt_has_dependency("{", "candidate", "id", "0" * 64) == 0
    assert schema.remediation_scan_id(None) == ""
    assert schema.remediation_scan_id("{") == ""
    assert schema.remediation_scan_id("[]") == ""


def test_authority_key_integrity_rejects_missing_mistyped_and_wrong_length_keys() -> None:
    missing = _minimal_key_connection()
    try:
        with pytest.raises(RuntimeError, match="key is unavailable"):
            schema.ensure_remediation_authority_key_integrity(
                missing,
                allow_initialize=False,
            )
    finally:
        missing.close()

    used = _minimal_key_connection()
    try:
        used.execute(
            "INSERT INTO agent_remediation_resolution_authority (resolution_event_id) "
            "VALUES ('resolution')"
        )
        with pytest.raises(RuntimeError, match="key is unavailable"):
            schema.ensure_remediation_authority_key_integrity(used, allow_initialize=True)
    finally:
        used.close()

    text_key = _minimal_key_connection()
    try:
        text_key.execute(
            "INSERT INTO store_secrets (name, secret, created_at) VALUES (?, ?, '')",
            (schema.REMEDIATION_AUTHORITY_KEY_NAME, "not-bytes"),
        )
        with pytest.raises(RuntimeError, match="key is invalid"):
            schema.ensure_remediation_authority_key_integrity(
                text_key,
                allow_initialize=False,
            )
    finally:
        text_key.close()

    short_key = _minimal_key_connection()
    try:
        short_key.execute(
            "INSERT INTO store_secrets (name, secret, created_at) VALUES (?, ?, '')",
            (schema.REMEDIATION_AUTHORITY_KEY_NAME, b"x" * 31),
        )
        with pytest.raises(RuntimeError, match="key is invalid"):
            schema.ensure_remediation_authority_key_integrity(
                short_key,
                allow_initialize=False,
            )
    finally:
        short_key.close()


def test_event_sequence_current_check_rejects_column_and_object_drift(
    base_connection: sqlite3.Connection,
) -> None:
    wrong_column = sqlite3.connect(":memory:")
    wrong_column.row_factory = sqlite3.Row
    try:
        wrong_column.execute(
            "CREATE TABLE agent_import_events (event_sequence TEXT NOT NULL DEFAULT '0')"
        )
        assert schema.agent_import_event_sequence_schema_is_current(wrong_column) is False
    finally:
        wrong_column.close()

    schema.create_agent_import_event_sequence_schema(base_connection, allow_backfill=True)
    base_connection.execute("DROP INDEX idx_agent_import_event_sequence")
    assert schema.agent_import_event_sequence_schema_is_current(base_connection) is False


def test_event_sequence_repair_rejects_invalid_rows_after_clearing_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = _SequenceConnection(authority_exists=True, invalid=object())
    monkeypatch.setattr(schema, "ensure_column", lambda *_args: None)
    monkeypatch.setattr(
        schema,
        "agent_import_event_sequence_schema_is_current",
        lambda _connection: False,
    )

    with pytest.raises(RuntimeError, match="sequence integrity is invalid"):
        schema.create_agent_import_event_sequence_schema(
            connection,  # type: ignore[arg-type]
            allow_backfill=False,
        )
    assert "DELETE FROM agent_remediation_resolution_authority" in connection.statements


def test_event_sequence_repair_rejects_exhaustion_and_invalid_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(schema, "ensure_column", lambda *_args: None)
    monkeypatch.setattr(
        schema,
        "agent_import_event_sequence_schema_is_current",
        lambda _connection: False,
    )
    exhausted = _SequenceConnection(maximum=9223372036854775807)
    with pytest.raises(RuntimeError, match="sequence is exhausted"):
        schema.create_agent_import_event_sequence_schema(
            exhausted,  # type: ignore[arg-type]
            allow_backfill=True,
        )

    bad_counter = _SequenceConnection(counter=None)
    with pytest.raises(RuntimeError, match="counter integrity is invalid"):
        schema.create_agent_import_event_sequence_schema(
            bad_counter,  # type: ignore[arg-type]
            allow_backfill=False,
        )


def test_event_sequence_repair_fails_when_postcondition_remains_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    states = iter((False, False))
    connection = _SequenceConnection(
        counter={"value": 0, "value_type": "integer"},
    )
    monkeypatch.setattr(schema, "ensure_column", lambda *_args: None)
    monkeypatch.setattr(
        schema,
        "agent_import_event_sequence_schema_is_current",
        lambda _connection: next(states),
    )

    with pytest.raises(RuntimeError, match="schema repair failed"):
        schema.create_agent_import_event_sequence_schema(
            connection,  # type: ignore[arg-type]
            allow_backfill=False,
        )


def test_schema_identity_and_authority_drop_cover_invalid_and_all_object_kinds(
    base_connection: sqlite3.Connection,
) -> None:
    with pytest.raises(RuntimeError, match="schema object is invalid"):
        schema._schema_object_identity("SELECT 1")

    schema.create_remediation_authority_schema(base_connection)
    assert schema.remediation_authority_schema_is_current(base_connection) is True
    schema._drop_remediation_authority_schema(base_connection)
    assert schema.remediation_authority_schema_is_current(base_connection) is False


def test_authority_schema_rebuilds_mismatched_tables_when_explicitly_allowed(
    base_connection: sqlite3.Connection,
) -> None:
    base_connection.executescript(
        """
        CREATE TABLE agent_remediation_resolution_authority (
            resolution_event_id TEXT PRIMARY KEY
        );
        CREATE TABLE agent_remediation_resolution_dependencies (
            resolution_event_id TEXT
        );
        """
    )

    schema.create_remediation_authority_schema(base_connection, allow_rebuild=True)

    assert schema.remediation_authority_schema_is_current(base_connection) is True


def test_authority_schema_repair_requires_a_true_postcondition(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        schema,
        "remediation_authority_schema_is_current",
        lambda _connection: False,
    )

    with pytest.raises(RuntimeError, match="schema repair failed"):
        schema.create_remediation_authority_schema(base_connection)


def test_reference_replacement_skips_empty_and_already_redacted_needles() -> None:
    connection = _SequenceConnection()

    schema._replace_legacy_source_references(
        connection,  # type: ignore[arg-type]
        table="events",
        column="detail",
        needles=("", "redacted", "secret"),
        replacement="redacted",
    )

    assert len(connection.statements) == 1
    assert "UPDATE events" in connection.statements[0]


def test_legacy_identity_allocator_fails_after_bounded_collisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CollisionConnection:
        def execute(self, _sql: str, _parameters: object = ()) -> _FetchResult:
            return _FetchResult(one={"id": "different-source"})

    monkeypatch.setattr(schema, "_LEGACY_SOURCE_REDACTION_COLLISION_LIMIT", 2)
    with pytest.raises(RuntimeError, match="identity space is exhausted"):
        schema._allocate_legacy_source_identity(
            CollisionConnection(),  # type: ignore[arg-type]
            source_id="source",
            base_identity="redacted://legacy-source/base",
        )


def test_taint_candidate_closure_refuses_nonconvergence(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_tombstone_authority_table(base_connection)
    closure_limit = schema._LEGACY_SOURCE_TAINT_CLOSURE_LIMIT

    def empty_closure_range(*arguments: int) -> range | tuple[()]:
        if arguments == (closure_limit,):
            return ()
        return builtins.range(*arguments)

    monkeypatch.setattr(schema, "range", empty_closure_range, raising=False)
    with pytest.raises(RuntimeError, match="taint closure did not converge"):
        schema._tombstone_legacy_source_behavior(
            base_connection,
            source_id="source",
            needles=(),
            include_source_records=False,
        )


def test_taint_event_closure_refuses_nonconvergence(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_tombstone_authority_table(base_connection)
    closure_limit = schema._LEGACY_SOURCE_TAINT_CLOSURE_LIMIT
    closure_calls = 0

    def second_empty_closure_range(*arguments: int) -> range | tuple[()]:
        nonlocal closure_calls
        if arguments == (closure_limit,):
            closure_calls += 1
            if closure_calls == 2:
                return ()
        return builtins.range(*arguments)

    monkeypatch.setattr(schema, "range", second_empty_closure_range, raising=False)
    with pytest.raises(RuntimeError, match="event taint closure did not converge"):
        schema._tombstone_legacy_source_behavior(
            base_connection,
            source_id="source",
            needles=(),
            include_source_records=False,
        )


def test_taint_event_closure_follows_queue_event_dependencies(
    base_connection: sqlite3.Connection,
) -> None:
    _create_tombstone_authority_table(base_connection)
    base_connection.executemany(
        "INSERT INTO agent_import_events "
        "(id, event_type, agent_slug, detail, created_at) VALUES (?, 'legacy', '', ?, '')",
        (
            ("tainted", "secret"),
            ("dependent", '{"queue_event_id":"tainted"}'),
        ),
    )

    schema._tombstone_legacy_source_behavior(
        base_connection,
        source_id="source",
        needles=("secret",),
        include_source_records=False,
    )

    assert base_connection.execute("SELECT COUNT(*) FROM agent_import_events").fetchone()[0] == 0


def test_legacy_source_assertion_detects_taint_and_broken_references(
    base_connection: sqlite3.Connection,
) -> None:
    base_connection.execute(
        "INSERT INTO agent_sources (id, url, name, added_at) VALUES ('source', ?, '', '')",
        ("https://example.test/secret",),
    )
    with pytest.raises(RuntimeError, match="redaction was incomplete"):
        schema._assert_legacy_source_removed(base_connection, needles=("secret",))
    base_connection.execute("DELETE FROM agent_sources")

    base_connection.execute(
        "INSERT INTO agent_active (id, agent_slug, version, activated_at) "
        "VALUES ('active', 'missing', '1', '')"
    )
    with pytest.raises(RuntimeError, match="invalid active roster reference"):
        schema._assert_legacy_source_removed(base_connection, needles=("absent",))
    base_connection.execute("DELETE FROM agent_active")

    base_connection.execute(
        "INSERT INTO agent_candidates (id, download_id, slug, quarantined_at) "
        "VALUES ('candidate', 'missing', 'agent', '')"
    )
    with pytest.raises(RuntimeError, match="invalid candidate reference"):
        schema._assert_legacy_source_removed(base_connection, needles=("absent",))


def _active_projection_row() -> dict[str, object]:
    metadata = {
        "capabilities": [],
        "categories": [],
        "description": "Description",
        "division": "Division",
        "name": "Agent",
        "prompt_path": "agents/agent.md",
        "source": "Source",
        "source_version": "1",
        "tool_affinity": [],
    }
    return {
        "agent_slug": "agent",
        "capabilities": "[]",
        "categories": "[]",
        "description": "Description",
        "division": "Division",
        "hash": "hash",
        "immutable_hash": "hash",
        "immutable_metadata": json.dumps(metadata),
        "immutable_source_id": "source",
        "immutable_source_version": "1",
        "name": "Agent",
        "prompt_path": "agents/agent.md",
        "source": "Source",
        "source_id": "source",
        "source_version": "1",
        "tool_affinity": "[]",
    }


def test_active_projection_integrity_rejects_every_material_mismatch() -> None:
    for field, value, message in (
        ("hash", "wrong", "hash does not match"),
        ("source_id", "wrong", "source does not match"),
        ("source_version", "wrong", "source revision does not match"),
    ):
        row = _active_projection_row()
        row[field] = value
        with pytest.raises(RuntimeError, match=message):
            schema._assert_active_roster_projection_integrity(
                _RowsConnection((row,)),  # type: ignore[arg-type]
            )

    legacy_row = _active_projection_row()
    legacy_row["immutable_metadata"] = "{}"
    schema._assert_active_roster_projection_integrity(
        _RowsConnection((legacy_row,)),  # type: ignore[arg-type]
    )

    metadata_revision = _active_projection_row()
    metadata = json.loads(str(metadata_revision["immutable_metadata"]))
    metadata["source_version"] = "different"
    metadata_revision["immutable_metadata"] = json.dumps(metadata)
    with pytest.raises(RuntimeError, match="projection does not match"):
        schema._assert_active_roster_projection_integrity(
            _RowsConnection((metadata_revision,)),  # type: ignore[arg-type]
        )

    scalar = _active_projection_row()
    scalar["name"] = "Different"
    with pytest.raises(RuntimeError, match="projection does not match"):
        schema._assert_active_roster_projection_integrity(
            _RowsConnection((scalar,)),  # type: ignore[arg-type]
        )

    malformed_list = _active_projection_row()
    malformed_list["categories"] = "{"
    with pytest.raises(RuntimeError, match="projection does not match"):
        schema._assert_active_roster_projection_integrity(
            _RowsConnection((malformed_list,)),  # type: ignore[arg-type]
        )


def test_source_purge_marker_and_stored_identity_validation_fail_closed(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_connection.execute(
        "UPDATE store_counters SET value = 'invalid' WHERE name = 'source-redaction-purge-pending'"
    )
    with pytest.raises(RuntimeError, match="purge state is invalid"):
        schema.source_redaction_purge_pending(base_connection)

    too_many = tuple(
        {"enabled": 1, "name": "name", "url": "https://example.test"}
        for _index in range(schema.MAX_DURABLE_SOURCE_COUNT + 1)
    )
    with pytest.raises(RuntimeError, match="source count is invalid"):
        schema.validate_stored_source_identities(  # type: ignore[arg-type]
            _RowsConnection(too_many)
        )

    invalid_enabled = ({"enabled": 2, "name": "name", "url": "https://example.test"},)
    with pytest.raises(RuntimeError, match="source identity is invalid"):
        schema.validate_stored_source_identities(  # type: ignore[arg-type]
            _RowsConnection(invalid_enabled)
        )

    monkeypatch.setattr(schema, "canonical_source_identity", lambda _value: "canonical")
    monkeypatch.setattr(
        schema,
        "canonical_source_display_name",
        lambda *_args, **_kwargs: "name",
    )
    noncanonical = ({"enabled": 1, "name": "name", "url": "stored"},)
    with pytest.raises(RuntimeError, match="source identity is invalid"):
        schema.validate_stored_source_identities(  # type: ignore[arg-type]
            _RowsConnection(noncanonical)
        )


def test_legacy_source_name_repairs_missing_names_and_defers_credentialed_urls(
    base_connection: sqlite3.Connection,
) -> None:
    base_connection.executemany(
        "INSERT INTO agent_sources (id, url, name, added_at) VALUES (?, ?, NULL, '')",
        (
            ("safe", "https://example.test/agents"),
            ("credentialed", "https://user:secret@example.test/agents"),
        ),
    )
    safe = base_connection.execute("SELECT * FROM agent_sources WHERE id = 'safe'").fetchone()
    credentialed = base_connection.execute(
        "SELECT * FROM agent_sources WHERE id = 'credentialed'"
    ).fetchone()

    assert schema._migrate_legacy_source_name(base_connection, safe, now=lambda: "") == (
        False,
        None,
    )
    assert schema._migrate_legacy_source_name(
        base_connection,
        credentialed,
        now=lambda: "",
    ) == (False, None)
    assert (
        base_connection.execute("SELECT name FROM agent_sources WHERE id = 'safe'").fetchone()[0]
        == "https://example.test/agents"
    )
    assert (
        base_connection.execute(
            "SELECT name FROM agent_sources WHERE id = 'credentialed'"
        ).fetchone()[0]
        is None
    )


def test_legacy_source_name_rejects_inconsistent_validation(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_connection.execute(
        "INSERT INTO agent_sources (id, url, name, added_at) "
        "VALUES ('source', 'https://example.test/agents', 'Friendly', '')"
    )
    row = base_connection.execute("SELECT * FROM agent_sources WHERE id = 'source'").fetchone()

    def fail_identity(_value: object) -> str:
        raise SourceIdentityError("forced")

    monkeypatch.setattr(schema, "canonical_source_identity", fail_identity)
    with pytest.raises(RuntimeError, match="validation was inconsistent"):
        schema._migrate_legacy_source_name(base_connection, row, now=lambda: "")


def test_legacy_source_name_persists_normalized_display_name(
    base_connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_connection.execute(
        "INSERT INTO agent_sources (id, url, name, added_at) "
        "VALUES ('source', 'https://example.test/agents', 'Original', '')"
    )
    row = base_connection.execute("SELECT * FROM agent_sources WHERE id = 'source'").fetchone()
    monkeypatch.setattr(
        schema,
        "canonical_source_display_name",
        lambda *_args, **_kwargs: "Normalized",
    )

    assert schema._migrate_legacy_source_name(base_connection, row, now=lambda: "") == (
        False,
        None,
    )
    assert (
        base_connection.execute("SELECT name FROM agent_sources WHERE id = 'source'").fetchone()[0]
        == "Normalized"
    )


def test_activation_grant_rebuild_refuses_existing_consumption_receipts() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE delegation_activation_receipts (id TEXT PRIMARY KEY);
        CREATE TABLE delegation_activation_consumptions (id TEXT PRIMARY KEY);
        INSERT INTO delegation_activation_consumptions (id) VALUES ('consumed');
        """
    )
    try:
        with pytest.raises(RuntimeError, match="consumption receipts present"):
            schema.migrate_delegation_activation_unit_identity(connection)
    finally:
        connection.close()


def test_activation_grant_rebuild_drops_an_empty_consumption_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyConsumptionConnection:
        def __init__(self) -> None:
            self.statements: list[str] = []

        def execute(self, sql: str, _parameters: object = ()) -> _FetchResult:
            self.statements.append(sql)
            if "PRAGMA index_list(delegation_activation_receipts)" in sql:
                return _FetchResult(rows=())
            if "sqlite_master" in sql and "delegation_activation_consumptions" in sql:
                return _FetchResult(one=object())
            if "SELECT COUNT(*) FROM delegation_activation_consumptions" in sql:
                return _FetchResult(one=(0,))
            return _FetchResult()

    connection = EmptyConsumptionConnection()
    monkeypatch.setattr(schema, "ensure_column", lambda *_args: None)

    schema.migrate_delegation_activation_unit_identity(  # type: ignore[arg-type]
        connection
    )

    assert "DROP TABLE delegation_activation_consumptions" in connection.statements
