from __future__ import annotations

import platform
import sqlite3
from pathlib import Path

import pytest

from agency_runtime.core.installer_contracts import CODEX_ACTIVATION_CANARY_PROOF_CONTRACT
from agency_runtime.core.native_child_activation import CANONICAL_NATIVE_CHILD_HOSTS
from agency_runtime.core.store.schema import (
    DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES,
    NATIVE_CHILD_PARENT_SCOPE_TABLE_SQL,
    NATIVE_CHILD_PARENT_SCOPE_TRIGGER_SQL,
    SCHEMA_VERSION,
    create_delegation_activation_invariant_triggers,
)
from agency_runtime.core.store.sqlite import Store


def _insert_consumption(
    connection: sqlite3.Connection,
    *,
    child_host: str = "zcode",
) -> tuple[str, str]:
    connection.execute(
        "INSERT INTO runs "
        "(id, trace_id, session_id, host, started_at, status, user_message, metadata) "
        "VALUES ('run-v36', 'trace-v36', 'session-v36', 'zcode', "
        "'2026-07-26T00:00:00Z', 'active', '', '{}')"
    )
    connection.execute(
        "INSERT INTO delegation_activation_receipts "
        "(id, token_hash, grant_id, grant_payload, grant_issued_unix, "
        "grant_expires_unix, child_host, session_id, trace_id, work_unit_id, "
        "specialist_slug, specialist_version, specialist_prompt_hash, worker_kind, "
        "worker_id, native_run_id, created_at, consumed_at, delegation_event_id) "
        "VALUES ('receipt-v36', 'token-v36', 'ncg-00000000000000000000000000000001', "
        "'{}', 1, 10, ?, 'session-v36', 'trace-v36', 'unit-v36', "
        "'code-reviewer', 'v1', 'sha256:prompt', 'zcode-agent', '', '', "
        "'2026-07-26T00:00:00Z', NULL, NULL)",
        (child_host,),
    )
    connection.execute(
        "INSERT INTO delegation_activation_consumptions "
        "(id, grant_id, legacy_activation_receipt_id, receipt_payload, session_id, "
        "trace_id, work_unit_id, child_host, specialist_slug, specialist_version, "
        "specialist_prompt_hash, worker_kind, worker_id, native_run_id, consumed_at, "
        "consumed_unix) VALUES "
        "('consumption-v36', 'ncg-00000000000000000000000000000001', "
        "'receipt-v36', '{}', 'session-v36', 'trace-v36', 'unit-v36', ?, "
        "'code-reviewer', 'v1', 'sha256:prompt', 'zcode-agent', 'worker-v36', "
        "'native-v36', '2026-07-26T00:00:01Z', 2)",
        (child_host,),
    )
    return "receipt-v36", "consumption-v36"


def test_schema_v38_accepts_zcode_and_guards_append_only_consumption(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "v36.db")
    assert "zcode" in CANONICAL_NATIVE_CHILD_HOSTS
    connection = store._connect()
    try:
        receipt_id, consumption_id = _insert_consumption(connection)
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM delegation_activation_consumptions WHERE id = ?",
                (consumption_id,),
            )
        connection.rollback()
        connection.execute(
            "DELETE FROM delegation_activation_receipts WHERE id = ?",
            (receipt_id,),
        )
        connection.commit()
        remaining = connection.execute(
            "SELECT COUNT(*) FROM delegation_activation_consumptions WHERE id = ?",
            (consumption_id,),
        ).fetchone()[0]
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    finally:
        connection.close()
    assert remaining == 0
    assert version == SCHEMA_VERSION == 44


@pytest.mark.parametrize(
    ("grant_origin", "tool_use_id"),
    [("manual_api", "spawn-call"), ("native_hook", "")],
)
def test_schema_v38_rejects_invalid_activation_grant_provenance(
    tmp_path: Path,
    grant_origin: str,
    tool_use_id: str,
) -> None:
    store = Store(tmp_path / "invalid-provenance.db")
    connection = store._connect()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="provenance is invalid"):
            connection.execute(
                "INSERT INTO delegation_activation_receipts "
                "(id, token_hash, grant_origin, tool_use_id, session_id, trace_id, "
                "work_unit_id, specialist_slug, specialist_version, "
                "specialist_prompt_hash, worker_kind, created_at) VALUES "
                "('invalid-provenance', 'token', ?, ?, 'session', 'trace', 'unit', "
                "'code-reviewer', 'v1', 'prompt-hash', 'generic-worker', 'now')",
                (grant_origin, tool_use_id),
            )
    finally:
        connection.rollback()
        connection.close()


def test_schema_v38_upgrade_preserves_v35_activation_evidence_and_is_idempotent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "upgrade.db"
    store = Store(path)
    connection = store._connect()
    try:
        _insert_consumption(connection, child_host="claude")
        connection.commit()
        current_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' "
            "AND name = 'delegation_activation_consumptions'"
        ).fetchone()[0]
        legacy_sql = str(current_sql).replace(", 'zcode'", "")
        assert legacy_sql != current_sql
        for name in DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES:
            connection.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
        connection.execute(
            "ALTER TABLE delegation_activation_consumptions "
            "RENAME TO delegation_activation_consumptions_v35_fixture"
        )
        connection.execute(legacy_sql)
        columns = tuple(
            str(row[1])
            for row in connection.execute("PRAGMA table_info(delegation_activation_consumptions)")
        )
        projection = ", ".join(columns)
        connection.execute(
            f"INSERT INTO delegation_activation_consumptions ({projection}) "  # nosec B608
            f"SELECT {projection} "  # nosec B608
            "FROM delegation_activation_consumptions_v35_fixture"
        )
        connection.execute("DROP TABLE delegation_activation_consumptions_v35_fixture")
        connection.execute("UPDATE schema_version SET version = 35")
        connection.commit()
    finally:
        connection.close()

    for _attempt in range(2):
        reopened = Store(path)
        assert reopened._current_schema_state() == (True, True)
        connection = reopened._connect()
        try:
            row = connection.execute(
                "SELECT child_host, specialist_slug "
                "FROM delegation_activation_consumptions WHERE id = 'consumption-v36'"
            ).fetchone()
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        finally:
            connection.close()
        assert tuple(row) == ("claude", "code-reviewer")
        assert version == SCHEMA_VERSION == 44


def test_schema_v38_upgrade_adds_native_child_scope_authority_idempotently(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v36-to-v37.db"
    store = Store(path)
    connection = store._connect()
    try:
        connection.execute("DROP TABLE native_child_parent_scopes")
        connection.execute("UPDATE schema_version SET version = 36")
        connection.commit()
    finally:
        connection.close()

    for _attempt in range(2):
        reopened = Store(path)
        assert reopened._current_schema_state() == (True, True)
        connection = reopened._connect()
        try:
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(native_child_parent_scopes)")
            }
            trigger = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'trigger' "
                "AND name = 'agency_native_child_parent_scope_consume_once'"
            ).fetchone()
        finally:
            connection.close()
        assert {"token_hash", "parent_trace_id", "consumed_unix"}.issubset(columns)
        assert trigger is not None
        assert version == SCHEMA_VERSION == 44


def test_schema_v38_upgrades_v37_attestation_and_hook_provenance_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v37-to-v38.db"
    store = Store(path)
    store.record_host_canary_attestation(
        host="codex",
        proof_contract=CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        proof_digest="a" * 64,
        profile_scope="current-profile",
        platform_system=platform.system(),
        platform_release=platform.release(),
        platform_machine=platform.machine(),
        host_version="codex 0.145.0",
        plugin_version="0.1.0",
        install_id="install-v37",
        bundle_digest="b" * 64,
        trace_id="trace-v37",
        passed_at="2026-07-27T00:00:00+00:00",
    )
    connection = store._connect()
    try:
        for name in DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES:
            connection.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
        connection.execute("ALTER TABLE delegation_activation_receipts DROP COLUMN tool_use_id")
        connection.execute("ALTER TABLE delegation_activation_receipts DROP COLUMN grant_origin")
        connection.execute("ALTER TABLE host_canary_attestations DROP COLUMN proof_digest")
        connection.execute("ALTER TABLE host_canary_attestations DROP COLUMN proof_contract")
        connection.execute("UPDATE schema_version SET version = 37")
        connection.commit()
    finally:
        connection.close()

    for _attempt in range(2):
        reopened = Store(path)
        assert reopened._current_schema_state() == (True, True)
        connection = reopened._connect()
        try:
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
            grant_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(delegation_activation_receipts)")
            }
            attestation_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(host_canary_attestations)")
            }
        finally:
            connection.close()
        attestation = reopened.get_host_canary_attestation("codex")
        assert {"grant_origin", "tool_use_id"}.issubset(grant_columns)
        assert {"proof_contract", "proof_digest"}.issubset(attestation_columns)
        assert attestation is not None
        assert attestation["proof_contract"] == ""
        assert attestation["proof_digest"] == ""
        assert version == SCHEMA_VERSION == 44


def test_schema_v43_adds_codex_execution_dispatch_receipt_idempotently(
    tmp_path: Path,
) -> None:
    path = tmp_path / "v42-to-v43.db"
    store = Store(path)
    connection = store._connect()
    try:
        connection.execute("DROP INDEX idx_worker_runs_codex_execution_tool_use")
        connection.execute("ALTER TABLE worker_runs DROP COLUMN execution_dispatched_at")
        connection.execute("ALTER TABLE worker_runs DROP COLUMN execution_tool_use_id")
        connection.execute("UPDATE schema_version SET version = 42")
        connection.commit()
    finally:
        connection.close()

    for _attempt in range(2):
        reopened = Store(path)
        assert reopened._current_schema_state() == (True, True)
        connection = reopened._connect()
        try:
            columns = {
                str(row["name"]) for row in connection.execute("PRAGMA table_info(worker_runs)")
            }
            execution_index = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_worker_runs_codex_execution_tool_use'"
            ).fetchone()
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        finally:
            connection.close()
        assert {"execution_tool_use_id", "execution_dispatched_at"}.issubset(columns)
        assert execution_index is not None
        assert version == SCHEMA_VERSION == 44


def test_schema_v44_adds_codex_child_tool_evidence_idempotently(tmp_path: Path) -> None:
    path = tmp_path / "v43-to-v44.db"
    store = Store(path)
    connection = store._connect()
    try:
        connection.execute("ALTER TABLE worker_runs DROP COLUMN tool_evidence_recorded_at")
        connection.execute("ALTER TABLE worker_runs DROP COLUMN tool_evidence_source")
        connection.execute("ALTER TABLE worker_runs DROP COLUMN tool_evidence")
        connection.execute("ALTER TABLE worker_runs DROP COLUMN tool_evidence_schema")
        connection.execute("UPDATE schema_version SET version = 43")
        connection.commit()
    finally:
        connection.close()

    expected = {
        "tool_evidence_schema",
        "tool_evidence",
        "tool_evidence_source",
        "tool_evidence_recorded_at",
    }
    for _attempt in range(2):
        reopened = Store(path)
        assert reopened._current_schema_state() == (True, True)
        connection = reopened._connect()
        try:
            columns = {
                str(row["name"]) for row in connection.execute("PRAGMA table_info(worker_runs)")
            }
            version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        finally:
            connection.close()
        assert expected.issubset(columns)
        assert version == SCHEMA_VERSION == 44


@pytest.mark.parametrize(
    "statement",
    [
        "DROP TRIGGER agency_activation_consumption_insert_guard",
        "DROP INDEX idx_worker_runs_native_scope",
        "DROP TRIGGER agency_agent_sources_boolean_insert_guard",
        "DROP TRIGGER agency_native_child_parent_scope_consume_once",
        "ALTER TABLE host_canary_attestations DROP COLUMN proof_digest",
        "ALTER TABLE worker_runs DROP COLUMN execution_dispatched_at",
        "ALTER TABLE worker_runs DROP COLUMN tool_evidence_recorded_at",
        "DROP INDEX idx_worker_runs_codex_execution_tool_use",
        "DROP INDEX idx_routing_query_hash",
    ],
    ids=[
        "consumption-guard",
        "native-run-unique-index",
        "boolean-guard",
        "child-scope-guard",
        "attestation-proof-column",
        "execution-dispatch-column",
        "child-tool-evidence-column",
        "execution-dispatch-index",
        "canary-query-index",
    ],
)
def test_schema_v38_currentness_rejects_missing_critical_objects(
    tmp_path: Path,
    statement: str,
) -> None:
    store = Store(tmp_path / "tampered.db")
    assert store._current_schema_state() == (True, True)
    connection = store._connect()
    try:
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()
    assert store._current_schema_state() == (False, True)


def test_schema_v38_currentness_rejects_same_name_noop_trigger(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "altered-trigger.db")
    connection = store._connect()
    try:
        connection.execute("DROP TRIGGER agency_agent_sources_boolean_insert_guard")
        connection.execute(
            "CREATE TRIGGER agency_agent_sources_boolean_insert_guard "
            "BEFORE INSERT ON agent_sources BEGIN SELECT 1; END"
        )
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
    repaired = Store(store.db_path)
    assert repaired._current_schema_state() == (True, True)


def test_schema_v38_currentness_rejects_weakened_consumption_table(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "weakened-consumption.db")
    connection = store._connect()
    try:
        for name in DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES:
            connection.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
        connection.execute("DROP TABLE delegation_activation_consumptions")
        connection.execute(
            "CREATE TABLE delegation_activation_consumptions ("
            "id TEXT, grant_id TEXT, legacy_activation_receipt_id TEXT, "
            "receipt_payload TEXT, session_id TEXT, trace_id TEXT, work_unit_id TEXT, "
            "child_host TEXT CHECK (child_host IN "
            "('claude', 'codex', 'hermes', 'openclaw', 'zcode')), "
            "specialist_slug TEXT, specialist_version TEXT, "
            "specialist_prompt_hash TEXT, worker_kind TEXT, worker_id TEXT, "
            "native_run_id TEXT, consumed_at TEXT, consumed_unix INTEGER)"
        )
        connection.execute(
            "CREATE INDEX idx_activation_consumptions_trace "
            "ON delegation_activation_consumptions(trace_id, consumed_at)"
        )
        connection.execute(
            "CREATE INDEX idx_activation_consumptions_work_unit "
            "ON delegation_activation_consumptions(trace_id, work_unit_id, consumed_at)"
        )
        create_delegation_activation_invariant_triggers(connection)
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
    with pytest.raises(
        RuntimeError,
        match="delegation activation consumption schema is invalid",
    ):
        Store(store.db_path)


def test_schema_v38_currentness_rejects_same_name_noop_workforce_guard(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "altered-workforce-trigger.db")
    connection = store._connect()
    try:
        connection.execute("DROP TRIGGER agency_hiring_case_applied_authority")
        connection.execute(
            "CREATE TRIGGER agency_hiring_case_applied_authority "
            "BEFORE UPDATE OF status ON agent_hiring_cases BEGIN SELECT 1; END"
        )
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
    repaired = Store(store.db_path)
    assert repaired._current_schema_state() == (True, True)


def test_schema_v38_currentness_preserves_quoted_remediation_literals(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "altered-remediation-literal.db")
    trigger_name = "trg_agent_remediation_authority_candidate_update"
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (trigger_name,),
        ).fetchone()
        assert row is not None
        altered = str(row["sql"]).replace(
            "dependency.dependency_kind = 'candidate'",
            "dependency.dependency_kind = 'CANDIDATE'",
        )
        assert altered != str(row["sql"])
        connection.execute(f"DROP TRIGGER {trigger_name}")  # nosec B608
        connection.execute(altered)
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)
    repaired = Store(store.db_path)
    assert repaired._current_schema_state() == (True, True)


def test_schema_v38_currentness_accepts_keyword_case_and_whitespace_only(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "formatted-workforce-trigger.db")
    connection = store._connect()
    try:
        connection.execute("DROP TRIGGER agency_hiring_case_applied_authority")
        connection.execute(
            "create   trigger agency_hiring_case_applied_authority\n"
            "before update of status on agent_hiring_cases\n"
            "when NEW.status = 'applied' and not exists (\n"
            "select 1 from agent_version_lineage as lineage\n"
            "where lineage.hiring_case_id = NEW.id)\n"
            "begin select raise(ABORT, 'agent hiring case lacks applied lineage'); end"
        )
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (True, True)


def test_schema_v38_currentness_rejects_weakened_native_child_scope_checks(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "weakened-child-scope.db")
    weakened = NATIVE_CHILD_PARENT_SCOPE_TABLE_SQL.replace(
        "host TEXT NOT NULL CHECK (host IN ('claude', 'codex'))",
        "host TEXT NOT NULL",
    )
    assert weakened != NATIVE_CHILD_PARENT_SCOPE_TABLE_SQL
    connection = store._connect()
    try:
        connection.execute("DROP TABLE native_child_parent_scopes")
        connection.executescript(weakened)
        connection.execute(
            "CREATE INDEX idx_native_child_parent_scopes_expiry "
            "ON native_child_parent_scopes(expires_unix, consumed_unix)"
        )
        connection.execute(NATIVE_CHILD_PARENT_SCOPE_TRIGGER_SQL)
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)


def test_schema_v36_currentness_rejects_semantically_altered_unique_index(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "altered-index.db")
    connection = store._connect()
    try:
        connection.execute("DROP INDEX idx_worker_runs_native_scope")
        connection.execute(
            "CREATE UNIQUE INDEX idx_worker_runs_native_scope ON worker_runs("
            "host COLLATE NOCASE, session_id, trace_id, worker_id, native_run_id) "
            "WHERE session_id <> '' AND trace_id <> '' "
            "AND worker_id <> '' AND native_run_id <> ''"
        )
        connection.commit()
    finally:
        connection.close()

    assert store._current_schema_state() == (False, True)


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("agent_sources", "enabled"),
        ("agent_sources", "trusted_for_auto_approve"),
        ("agent_snapshots", "activated"),
        ("agent_snapshots", "approved"),
    ],
)
def test_schema_v36_rejects_invalid_boolean_domains(
    tmp_path: Path,
    table: str,
    column: str,
) -> None:
    store = Store(tmp_path / "booleans.db")
    connection = store._connect()
    try:
        if table == "agent_sources":
            connection.execute(
                "INSERT INTO agent_sources "
                "(id, url, name, added_at, enabled, trusted_for_auto_approve) "
                "VALUES ('source-v36', 'fixture://v36', '', '', 1, 0)"
            )
            predicate = "id = 'source-v36'"
        else:
            connection.execute(
                "INSERT INTO agent_snapshots "
                "(id, snapshot_id, created_at, activated, approved) "
                "VALUES ('snapshot-v36', 'snapshot-v36', '', 0, 0)"
            )
            predicate = "id = 'snapshot-v36'"
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="boolean"):
            connection.execute(
                f"UPDATE {table} SET {column} = 2 WHERE {predicate}"  # nosec B608
            )
    finally:
        connection.close()
