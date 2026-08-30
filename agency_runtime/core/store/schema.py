"""SQLite schema definition and transactional migration helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.delegation_status import (
    DELEGATION_STATUS_PRIORITY as _DELEGATION_STATUS_PRIORITY,
)
from agency_runtime.core.delegation_status import (
    TERMINAL_DELEGATION_STATUSES as _TERMINAL_DELEGATION_STATUSES,
)
from agency_runtime.core.roster.revisions import decode_revision_metadata
from agency_runtime.core.roster.source_identity import (
    MAX_DURABLE_SOURCE_COUNT,
    SourceIdentityError,
    canonical_source_display_name,
    canonical_source_identity,
    is_legacy_source_redaction_identity,
    legacy_source_name_redaction,
    legacy_source_redaction,
)
from agency_runtime.core.store.projections import (
    RUN_CONTENT_LIMIT,
    project_delegation_detail,
    project_run_metadata,
    project_snapshot_summary,
    redact_sensitive_text,
    sanitize_api_base,
)
from agency_runtime.core.store.trace_identity import (
    correlation_digest,
    ensure_correlation_key_integrity,
)

SCHEMA_VERSION = 48

# Columns an already-created activation receipts table gains by migration.
#
# The startup staleness predicate derives its required columns from this tuple
# rather than restating them.  A column added here but not there would leave
# every existing database stamped current, skip the migration that adds it, and
# fail at query time on exactly the installs that needed migrating -- while a
# fresh test database, created from the full DDL, passes.
DELEGATION_ACTIVATION_RECEIPT_MIGRATED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("grant_id", "TEXT NOT NULL DEFAULT ''"),
    ("grant_payload", "TEXT NOT NULL DEFAULT ''"),
    ("grant_issued_unix", "INTEGER NOT NULL DEFAULT 0"),
    ("grant_expires_unix", "INTEGER NOT NULL DEFAULT 0"),
    ("child_host", "TEXT NOT NULL DEFAULT ''"),
    (
        "grant_origin",
        "TEXT NOT NULL DEFAULT 'manual_api' CHECK (grant_origin IN ('manual_api', 'native_hook'))",
    ),
    ("tool_use_id", "TEXT NOT NULL DEFAULT ''"),
    # Empty means the launch requested no explicit model, which is a fact
    # about the call, not a gap in the evidence.
    ("launch_model", "TEXT NOT NULL DEFAULT ''"),
)

# Columns an already-created model receipts table gains by migration, declared
# the same single-source way and for the same reason as the tuple above.
#
# ``latency_ms`` is how long the provider call took.  The value was always
# measured -- ``StructuredProviderResult.latency_ms`` -- and then dropped on the
# floor, because the receipt had nowhere to put it and the two timestamp columns
# were both stamped at record time.  427 of 433 receipts on the first box to be
# checked had ``started_at == ended_at``, so "what does Agency cost a turn"
# could be answered only in total, never per call.
#
# Deliberately a duration rather than a reconstructed span: writing
# ``ended_at - latency`` into a timestamp column would put a fabricated absolute
# time next to real ones.
MODEL_RECEIPT_MIGRATED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("latency_ms", "INTEGER NOT NULL DEFAULT 0"),
)

# A native host may report that a child agent ended before it reports whether
# the child's user-visible completion was delivered. Keep that observation on
# the still-open worker row so a restarted host can fail only known pending
# completions without interfering with children the host can resume.
NATIVE_CHILD_TERMINAL_MIGRATED_COLUMNS: tuple[tuple[str, str], ...] = (
    (
        "native_terminal_outcome",
        "TEXT NOT NULL DEFAULT '' CHECK (native_terminal_outcome IN "
        "('', 'ok', 'error', 'timeout', 'killed', 'reset', 'deleted', 'unknown'))",
    ),
    (
        "native_delivery_status",
        "TEXT NOT NULL DEFAULT '' CHECK (native_delivery_status IN "
        "('', 'pending', 'delivered', 'failed', 'interrupted'))",
    ),
    ("native_terminal_observed_at", "TEXT"),
    ("native_delivery_observed_at", "TEXT"),
)

STORE_CLOCK_SQL = "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW')"
_STORE_CLOCK_VALUE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}000\+00:00$"
)


def store_clock_value_is_canonical(value: object) -> bool:
    """Return whether ``value`` has the exact valid timestamp shape SQLite writes."""

    if not isinstance(value, str) or _STORE_CLOCK_VALUE.fullmatch(value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat(timespec="microseconds") == value


NATIVE_WORKER_SCOPE_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_worker_runs_native_scope "
    "ON worker_runs(host, session_id, trace_id, worker_id, native_run_id) "
    "WHERE session_id <> '' AND trace_id <> '' "
    "AND worker_id <> '' AND native_run_id <> ''"
)
CODEX_EXECUTION_TOOL_USE_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_worker_runs_codex_execution_tool_use "
    "ON worker_runs(session_id, trace_id, execution_tool_use_id) "
    "WHERE host = 'codex' AND session_id <> '' AND trace_id <> '' "
    "AND execution_tool_use_id <> ''"
)
_MAX_REMEDIATION_AUTHORITY_ID_BYTES = 512
_MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES = 256 * 1024
_MAX_REMEDIATION_AUTHORITY_RECEIPT_BYTES = 256 * 1024
_MAX_REMEDIATION_AUTHORITY_DEPENDENCY_ID_BYTES = 32 * 1024
_MAX_REMEDIATION_AUTHORITY_DEPENDENCIES = 32
REMEDIATION_AUTHORITY_KEY_NAME = "remediation-authority-hmac-v1"
REMEDIATION_AUTHORITY_EVIDENCE_SCHEMA = "agency.roster.remediation-authority-evidence.v1"
REMEDIATION_AUTHORITY_VALIDATOR_REVISION = "sync-resolution-closure-v1"
REMEDIATION_AUTHORITY_DEPENDENCY_KINDS = frozenset(
    {
        "queue_event",
        "resolution_event",
        "queue_download",
        "candidate_download",
        "source_download",
        "candidate",
        "source",
        "queue_source_scan",
        "candidate_source_scan",
        "candidate_audit",
        "transformation_event",
        "candidate_slug",
    }
)

BOUNDED_REMEDIATION_EVENT_DETAIL_SQL = (
    "CASE WHEN typeof(detail) = 'text' THEN "
    "CASE WHEN length(CAST(detail AS BLOB)) BETWEEN 2 AND 262144 THEN "
    "CASE WHEN json_valid(detail) THEN detail ELSE NULL END "
    "ELSE NULL END ELSE NULL END"
)
BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL = (
    "CASE WHEN typeof(detail) = 'text' THEN "
    "CASE WHEN length(CAST(detail AS BLOB)) BETWEEN 2 AND 262144 "
    "THEN json_valid(detail) ELSE 0 END ELSE 0 END"
)
_REMEDIATION_RESOLUTION_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_import_resolution_queue "
    "ON agent_import_events(json_extract(detail, '$.queue_event_id')) "
    "WHERE event_type = 'manifest_entry_remediation_resolved' "
    f"AND {BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL}"
)
_REMEDIATION_QUEUE_IDENTITY_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_import_queue_identity ON agent_import_events("
    "json_extract(detail, '$.source_id'), "
    "json_extract(detail, '$.relative_path'), "
    "json_extract(detail, '$.origin')) "
    "WHERE event_type = 'manifest_entry_remediation_queued' "
    f"AND {BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL}"
)
_REMEDIATION_CANDIDATE_PROVENANCE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_import_candidate_provenance "
    "ON agent_import_events(event_type, agent_slug, "
    f"json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.candidate_id'), "
    "created_at DESC, event_sequence DESC)"
)
_REMEDIATION_SCAN_PROVENANCE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_import_scan_provenance "
    "ON agent_import_events(event_type, "
    f"json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id'), "
    f"json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.relative_path'))"
)
_AGENT_IMPORT_EVENT_SEQUENCE_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_import_event_sequence "
    "ON agent_import_events(event_sequence)"
)
_AGENT_IMPORT_EVENT_SEQUENCE_INSERT_GUARD_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_insert_guard "
    "BEFORE INSERT ON agent_import_events WHEN NEW.event_sequence != 0 BEGIN "
    "SELECT RAISE(ABORT, 'agent import event sequence is store-assigned'); END"
)
_AGENT_IMPORT_EVENT_SEQUENCE_ALLOCATE_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_allocate "
    "AFTER INSERT ON agent_import_events WHEN NEW.event_sequence = 0 BEGIN "
    "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM store_counters "
    "WHERE name = 'agent-import-event-sequence' AND typeof(value) = 'integer' "
    "AND value >= 0 AND value < 9223372036854775807) "
    "THEN RAISE(ABORT, 'agent import event sequence counter unavailable') END; "
    "UPDATE store_counters SET value = value + 1 "
    "WHERE name = 'agent-import-event-sequence'; "
    "UPDATE agent_import_events SET event_sequence = (SELECT value FROM store_counters "
    "WHERE name = 'agent-import-event-sequence') WHERE id = NEW.id; END"
)
_AGENT_IMPORT_EVENT_SEQUENCE_UPDATE_GUARD_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_update_guard "
    "BEFORE UPDATE OF event_sequence ON agent_import_events "
    "WHEN OLD.event_sequence != 0 OR NEW.event_sequence <= 0 BEGIN "
    "SELECT RAISE(ABORT, 'agent import event sequence is immutable'); END"
)
_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_INSERT_GUARD_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_counter_insert "
    "BEFORE INSERT ON store_counters "
    "WHEN NEW.name = 'agent-import-event-sequence' "
    "AND EXISTS (SELECT 1 FROM store_counters "
    "WHERE name = 'agent-import-event-sequence') BEGIN "
    "SELECT RAISE(ABORT, 'agent import event sequence counter is immutable'); END"
)
_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_UPDATE_GUARD_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_counter_update "
    "BEFORE UPDATE OF name, value ON store_counters "
    "WHEN OLD.name = 'agent-import-event-sequence' "
    "OR NEW.name = 'agent-import-event-sequence' BEGIN "
    "SELECT CASE WHEN NEW.name != OLD.name "
    "OR typeof(NEW.value) != 'integer' OR NEW.value != OLD.value + 1 "
    "OR OLD.value >= 9223372036854775807 "
    "THEN RAISE(ABORT, 'agent import event sequence counter is immutable') END; END"
)
_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_DELETE_GUARD_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_import_event_sequence_counter_delete "
    "BEFORE DELETE ON store_counters "
    "WHEN OLD.name = 'agent-import-event-sequence' BEGIN "
    "SELECT RAISE(ABORT, 'agent import event sequence counter is immutable'); END"
)
_REMEDIATION_AUTHORITY_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS agent_remediation_resolution_authority ("
    "resolution_event_id TEXT PRIMARY KEY CHECK (typeof(resolution_event_id) = 'text' "
    "AND length(CAST(resolution_event_id AS BLOB)) BETWEEN 1 AND 512), "
    "queue_event_id TEXT NOT NULL UNIQUE CHECK (typeof(queue_event_id) = 'text' "
    "AND length(CAST(queue_event_id AS BLOB)) BETWEEN 1 AND 512), "
    "evidence_receipt TEXT NOT NULL CHECK (typeof(evidence_receipt) = 'text' "
    "AND length(CAST(evidence_receipt AS BLOB)) BETWEEN 2 AND 262144), "
    "dependency_count INTEGER NOT NULL CHECK (typeof(dependency_count) = 'integer' "
    "AND dependency_count BETWEEN 1 AND 32), "
    "authority_hmac TEXT NOT NULL CHECK (typeof(authority_hmac) = 'text' "
    "AND length(authority_hmac) = 64 "
    "AND authority_hmac NOT GLOB '*[^0-9a-f]*'), "
    "validated_at TEXT NOT NULL CHECK (typeof(validated_at) = 'text' "
    "AND length(CAST(validated_at AS BLOB)) BETWEEN 1 AND 128), "
    "FOREIGN KEY (resolution_event_id) REFERENCES agent_import_events(id) "
    "ON DELETE CASCADE, "
    "FOREIGN KEY (queue_event_id) REFERENCES agent_import_events(id) "
    "ON DELETE CASCADE)"
)
_REMEDIATION_AUTHORITY_DEPENDENCY_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS agent_remediation_resolution_dependencies ("
    "resolution_event_id TEXT NOT NULL CHECK (typeof(resolution_event_id) = 'text' "
    "AND length(CAST(resolution_event_id AS BLOB)) BETWEEN 1 AND 512), "
    "dependency_kind TEXT NOT NULL CHECK (dependency_kind IN ("
    "'queue_event','resolution_event','queue_download','candidate_download',"
    "'source_download','candidate','source','queue_source_scan',"
    "'candidate_source_scan','candidate_audit',"
    "'transformation_event','candidate_slug')), "
    "dependency_id TEXT NOT NULL CHECK (typeof(dependency_id) = 'text' "
    "AND length(CAST(dependency_id AS BLOB)) BETWEEN 1 AND 32768), "
    "dependency_hash TEXT NOT NULL CHECK (typeof(dependency_hash) = 'text' "
    "AND length(dependency_hash) = 64 "
    "AND dependency_hash NOT GLOB '*[^0-9a-f]*'), "
    "PRIMARY KEY (resolution_event_id, dependency_kind, dependency_id), "
    "FOREIGN KEY (resolution_event_id) "
    "REFERENCES agent_remediation_resolution_authority(resolution_event_id) "
    "ON DELETE CASCADE)"
)
_REMEDIATION_AUTHORITY_VALIDATED_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_remediation_authority_validated "
    "ON agent_remediation_resolution_authority(validated_at, resolution_event_id)"
)
_REMEDIATION_AUTHORITY_DEPENDENCY_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_agent_remediation_dependency_lookup "
    "ON agent_remediation_resolution_dependencies("
    "dependency_kind, dependency_id, resolution_event_id)"
)
_REMEDIATION_AUTHORITY_INSERT_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_insert_validate "
    "BEFORE INSERT ON agent_remediation_resolution_authority BEGIN "
    "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM agent_import_events AS resolution "
    "JOIN agent_import_events AS queued ON queued.id = NEW.queue_event_id "
    "WHERE resolution.id = NEW.resolution_event_id "
    "AND resolution.event_type = 'manifest_entry_remediation_resolved' "
    "AND queued.event_type = 'manifest_entry_remediation_queued' "
    "AND resolution.event_sequence > queued.event_sequence "
    "AND typeof(resolution.agent_slug) = 'text' "
    "AND length(CAST(resolution.agent_slug AS BLOB)) BETWEEN 1 AND 512 "
    "AND typeof(queued.agent_slug) = 'text' "
    "AND length(CAST(queued.agent_slug AS BLOB)) BETWEEN 1 AND 512 "
    "AND typeof(resolution.created_at) = 'text' "
    "AND length(CAST(resolution.created_at AS BLOB)) BETWEEN 1 AND 512 "
    "AND typeof(queued.created_at) = 'text' "
    "AND length(CAST(queued.created_at AS BLOB)) BETWEEN 1 AND 512 "
    "AND typeof(resolution.detail) = 'text' "
    "AND length(CAST(resolution.detail AS BLOB)) BETWEEN 1 AND 262144 "
    "AND resolution.agent_slug = queued.agent_slug "
    "AND agency_verify_remediation_authority("
    "NEW.resolution_event_id, NEW.queue_event_id, resolution.detail, "
    "NEW.evidence_receipt, NEW.dependency_count, NEW.validated_at, "
    "NEW.authority_hmac, queued.created_at, resolution.created_at, "
    "resolution.agent_slug) = 1) "
    "THEN RAISE(ABORT, 'invalid remediation resolution authority') END; END"
)
_REMEDIATION_AUTHORITY_PROJECTION_UPDATE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_projection_update "
    "BEFORE UPDATE ON agent_remediation_resolution_authority BEGIN "
    "SELECT RAISE(ABORT, 'remediation resolution authority is immutable'); END"
)
_REMEDIATION_AUTHORITY_PROJECTION_DELETE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_projection_delete "
    "BEFORE DELETE ON agent_remediation_resolution_authority BEGIN "
    "DELETE FROM agent_remediation_resolution_dependencies "
    "WHERE resolution_event_id = OLD.resolution_event_id; END"
)
_REMEDIATION_AUTHORITY_DEPENDENCY_INSERT_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_dependency_insert_validate "
    "BEFORE INSERT ON agent_remediation_resolution_dependencies BEGIN "
    "SELECT CASE WHEN NOT EXISTS (SELECT 1 "
    "FROM agent_remediation_resolution_authority AS authority "
    "WHERE authority.resolution_event_id = NEW.resolution_event_id "
    "AND agency_remediation_receipt_has_dependency("
    "authority.evidence_receipt, NEW.dependency_kind, "
    "NEW.dependency_id, NEW.dependency_hash) = 1) "
    "THEN RAISE(ABORT, 'invalid remediation authority dependency') END; END"
)
_REMEDIATION_AUTHORITY_DEPENDENCY_UPDATE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_dependency_update "
    "BEFORE UPDATE ON agent_remediation_resolution_dependencies BEGIN "
    "SELECT RAISE(ABORT, 'remediation authority dependency is immutable'); END"
)
_REMEDIATION_AUTHORITY_KEY_INSERT_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_key_insert "
    "BEFORE INSERT ON store_secrets "
    "WHEN NEW.name = 'remediation-authority-hmac-v1' "
    "AND EXISTS (SELECT 1 FROM store_secrets "
    "WHERE name = 'remediation-authority-hmac-v1') BEGIN "
    "SELECT RAISE(ABORT, 'remediation authority key is immutable'); END"
)
_REMEDIATION_AUTHORITY_KEY_UPDATE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_key_update "
    "BEFORE UPDATE ON store_secrets "
    "WHEN OLD.name = 'remediation-authority-hmac-v1' "
    "OR NEW.name = 'remediation-authority-hmac-v1' BEGIN "
    "SELECT RAISE(ABORT, 'remediation authority key is immutable'); END"
)
_REMEDIATION_AUTHORITY_KEY_DELETE_TRIGGER_SQL = (
    "CREATE TRIGGER IF NOT EXISTS trg_agent_remediation_authority_key_delete "
    "BEFORE DELETE ON store_secrets "
    "WHEN OLD.name = 'remediation-authority-hmac-v1' BEGIN "
    "SELECT RAISE(ABORT, 'remediation authority key is immutable'); END"
)


def _remediation_invalidation_trigger_sql(
    name: str,
    operation: str,
    table: str,
    predicate: str,
    *,
    columns: str = "",
    timing: str = "AFTER",
    when: str = "",
) -> str:
    update_columns = f" OF {columns}" if operation == "UPDATE" and columns else ""
    when_clause = f" WHEN {when}" if when else ""
    return (
        f"CREATE TRIGGER IF NOT EXISTS {name} {timing} {operation}{update_columns} ON {table}"
        f"{when_clause} BEGIN DELETE FROM agent_remediation_resolution_authority "
        "WHERE resolution_event_id IN (SELECT dependency.resolution_event_id "
        "FROM agent_remediation_resolution_dependencies AS dependency "
        f"WHERE {predicate}); END"
    )


_EVENT_DEPENDENCY_KINDS_SQL = "'queue_event','resolution_event','transformation_event'"
_SCAN_PROVENANCE_EVENT_KINDS_SQL = (
    "'source_scan_recorded','manifest_entry_ignored','manifest_entry_remediation_queued'"
)
_REMEDIATION_AUTHORITY_INVALIDATION_TRIGGER_SQLS = (
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_import_insert",
        "INSERT",
        "agent_import_events",
        f"(dependency.dependency_kind IN ({_EVENT_DEPENDENCY_KINDS_SQL}) "
        "AND dependency.dependency_id = NEW.id) "
        "OR (dependency.dependency_kind = 'candidate_slug' "
        "AND NEW.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = NEW.agent_slug) "
        "OR (dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        f"AND NEW.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(NEW.detail))",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_import_insert_collision",
        "INSERT",
        "agent_import_events",
        "EXISTS (SELECT 1 FROM agent_import_events AS existing "
        "WHERE existing.id = NEW.id AND ("
        f"(dependency.dependency_kind IN ({_EVENT_DEPENDENCY_KINDS_SQL}) "
        "AND dependency.dependency_id = existing.id) "
        "OR (dependency.dependency_kind = 'candidate_slug' "
        "AND existing.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = existing.agent_slug) "
        "OR (dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        f"AND existing.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(existing.detail))))",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_import_update",
        "UPDATE",
        "agent_import_events",
        f"(dependency.dependency_kind IN ({_EVENT_DEPENDENCY_KINDS_SQL}) "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)) "
        "OR (dependency.dependency_kind = 'candidate_slug' "
        "AND ((OLD.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = OLD.agent_slug) "
        "OR (NEW.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = NEW.agent_slug))) "
        "OR (dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        f"AND ((OLD.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(OLD.detail)) "
        f"OR (NEW.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(NEW.detail))))",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_import_update_collision",
        "UPDATE",
        "agent_import_events",
        "EXISTS (SELECT 1 FROM agent_import_events AS existing "
        "WHERE existing.id = NEW.id AND existing.id != OLD.id AND ("
        f"(dependency.dependency_kind IN ({_EVENT_DEPENDENCY_KINDS_SQL}) "
        "AND dependency.dependency_id = existing.id) "
        "OR (dependency.dependency_kind = 'candidate_slug' "
        "AND existing.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = existing.agent_slug) "
        "OR (dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        f"AND existing.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(existing.detail))))",
        columns="id",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_import_delete",
        "DELETE",
        "agent_import_events",
        f"(dependency.dependency_kind IN ({_EVENT_DEPENDENCY_KINDS_SQL}) "
        "AND dependency.dependency_id = OLD.id) "
        "OR (dependency.dependency_kind = 'candidate_slug' "
        "AND OLD.event_type = 'manifest_entry_remediated' "
        "AND dependency.dependency_id = OLD.agent_slug) "
        "OR (dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        f"AND OLD.event_type IN ({_SCAN_PROVENANCE_EVENT_KINDS_SQL}) "
        "AND dependency.dependency_id = agency_remediation_scan_id(OLD.detail))",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_download_insert",
        "INSERT",
        "agent_downloads",
        "dependency.dependency_kind IN "
        "('queue_download','candidate_download','source_download') "
        "AND dependency.dependency_id = NEW.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_download_update",
        "UPDATE",
        "agent_downloads",
        "dependency.dependency_kind IN "
        "('queue_download','candidate_download','source_download') "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)",
        columns="id, source_id, slug, hash, content",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_download_status",
        "UPDATE",
        "agent_downloads",
        "dependency.dependency_kind IN ('queue_download','source_download') "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)",
        columns="status",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_download_delete",
        "DELETE",
        "agent_downloads",
        "dependency.dependency_kind IN "
        "('queue_download','candidate_download','source_download') "
        "AND dependency.dependency_id = OLD.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_candidate_insert",
        "INSERT",
        "agent_candidates",
        "(dependency.dependency_kind = 'candidate' "
        "AND dependency.dependency_id = NEW.id) "
        "OR (dependency.dependency_kind IN ('queue_download','source_download') "
        "AND dependency.dependency_id = NEW.download_id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_candidate_update",
        "UPDATE",
        "agent_candidates",
        "(dependency.dependency_kind = 'candidate' "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)) "
        "OR (dependency.dependency_kind IN ('queue_download','source_download') "
        "AND dependency.dependency_id IN (OLD.download_id, NEW.download_id))",
        columns=(
            "id, download_id, slug, name, description, division, categories, "
            "capabilities, tool_affinity, prompt_path, source, source_version, version, hash"
        ),
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_candidate_status",
        "UPDATE",
        "agent_candidates",
        "dependency.dependency_kind = 'candidate' AND dependency.dependency_id IN (OLD.id, NEW.id)",
        columns="status",
        when="NEW.status NOT IN ('pending','approved','activated','rejected')",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_candidate_delete",
        "DELETE",
        "agent_candidates",
        "(dependency.dependency_kind = 'candidate' "
        "AND dependency.dependency_id = OLD.id) "
        "OR (dependency.dependency_kind IN ('queue_download','source_download') "
        "AND dependency.dependency_id = OLD.download_id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_source_insert",
        "INSERT",
        "agent_sources",
        "dependency.dependency_kind = 'source' AND dependency.dependency_id = NEW.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_source_insert_collision",
        "INSERT",
        "agent_sources",
        "dependency.dependency_kind = 'source' "
        "AND (dependency.dependency_id = NEW.id "
        "OR dependency.dependency_id IN "
        "(SELECT existing.id FROM agent_sources AS existing "
        "WHERE existing.url = NEW.url))",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_source_update",
        "UPDATE",
        "agent_sources",
        "dependency.dependency_kind = 'source' AND dependency.dependency_id IN (OLD.id, NEW.id)",
        columns="id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_source_update_collision",
        "UPDATE",
        "agent_sources",
        "dependency.dependency_kind = 'source' "
        "AND dependency.dependency_id IN "
        "(SELECT existing.id FROM agent_sources AS existing "
        "WHERE existing.url = NEW.url AND existing.id != OLD.id)",
        columns="id, url",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_source_delete",
        "DELETE",
        "agent_sources",
        "dependency.dependency_kind = 'source' AND dependency.dependency_id = OLD.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_insert",
        "INSERT",
        "agent_source_scans",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id = NEW.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_update",
        "UPDATE",
        "agent_source_scans",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_delete",
        "DELETE",
        "agent_source_scans",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id = OLD.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_entry_insert",
        "INSERT",
        "agent_source_scan_entries",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id = NEW.scan_id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_entry_insert_collision",
        "INSERT",
        "agent_source_scan_entries",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id IN "
        "(SELECT existing.scan_id FROM agent_source_scan_entries AS existing "
        "WHERE existing.id = NEW.id)",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_entry_update",
        "UPDATE",
        "agent_source_scan_entries",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id IN (OLD.scan_id, NEW.scan_id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_entry_update_collision",
        "UPDATE",
        "agent_source_scan_entries",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id IN "
        "(SELECT existing.scan_id FROM agent_source_scan_entries AS existing "
        "WHERE existing.id = NEW.id AND existing.id != OLD.id)",
        columns="id",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_scan_entry_delete",
        "DELETE",
        "agent_source_scan_entries",
        "dependency.dependency_kind IN ('queue_source_scan','candidate_source_scan') "
        "AND dependency.dependency_id = OLD.scan_id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_audit_insert",
        "INSERT",
        "agent_candidate_audits",
        "dependency.dependency_kind = 'candidate_audit' AND dependency.dependency_id = NEW.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_audit_insert_collision",
        "INSERT",
        "agent_candidate_audits",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND (dependency.dependency_id = NEW.id "
        "OR dependency.dependency_id IN "
        "(SELECT existing.id FROM agent_candidate_audits AS existing "
        "WHERE existing.candidate_id = NEW.candidate_id "
        "AND existing.audit_revision = NEW.audit_revision))",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_audit_update",
        "UPDATE",
        "agent_candidate_audits",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id IN (OLD.id, NEW.id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_audit_update_collision",
        "UPDATE",
        "agent_candidate_audits",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id IN "
        "(SELECT existing.id FROM agent_candidate_audits AS existing "
        "WHERE existing.candidate_id = NEW.candidate_id "
        "AND existing.audit_revision = NEW.audit_revision "
        "AND existing.id != OLD.id)",
        columns="id, candidate_id, audit_revision",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_audit_delete",
        "DELETE",
        "agent_candidate_audits",
        "dependency.dependency_kind = 'candidate_audit' AND dependency.dependency_id = OLD.id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_finding_insert",
        "INSERT",
        "agent_candidate_audit_findings",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id = NEW.audit_id",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_finding_insert_collision",
        "INSERT",
        "agent_candidate_audit_findings",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id IN "
        "(SELECT existing.audit_id FROM agent_candidate_audit_findings AS existing "
        "WHERE existing.id = NEW.id)",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_finding_update",
        "UPDATE",
        "agent_candidate_audit_findings",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id IN (OLD.audit_id, NEW.audit_id)",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_finding_update_collision",
        "UPDATE",
        "agent_candidate_audit_findings",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id IN "
        "(SELECT existing.audit_id FROM agent_candidate_audit_findings AS existing "
        "WHERE existing.id = NEW.id AND existing.id != OLD.id)",
        columns="id",
        timing="BEFORE",
    ),
    _remediation_invalidation_trigger_sql(
        "trg_agent_remediation_authority_finding_delete",
        "DELETE",
        "agent_candidate_audit_findings",
        "dependency.dependency_kind = 'candidate_audit' "
        "AND dependency.dependency_id = OLD.audit_id",
    ),
)

DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS delegation_activation_consumptions (
    id TEXT PRIMARY KEY,
    grant_id TEXT NOT NULL UNIQUE,
    legacy_activation_receipt_id TEXT NOT NULL UNIQUE,
    receipt_payload TEXT NOT NULL,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    work_unit_id TEXT NOT NULL,
    child_host TEXT NOT NULL
        CHECK (child_host IN ('claude', 'codex', 'hermes', 'openclaw', 'zcode')),
    specialist_slug TEXT NOT NULL,
    specialist_version TEXT NOT NULL,
    specialist_prompt_hash TEXT NOT NULL,
    worker_kind TEXT NOT NULL CHECK (worker_kind <> ''),
    worker_id TEXT NOT NULL CHECK (worker_id <> ''),
    native_run_id TEXT NOT NULL CHECK (native_run_id <> ''),
    consumed_at TEXT NOT NULL,
    consumed_unix INTEGER NOT NULL CHECK (consumed_unix > 0),
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
    FOREIGN KEY (legacy_activation_receipt_id)
        REFERENCES delegation_activation_receipts(id) ON DELETE CASCADE
)
"""
_LEGACY_DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL = (
    DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL.replace(", 'zcode'", "")
)

NATIVE_CHILD_PARENT_SCOPE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS native_child_parent_scopes (
    id TEXT PRIMARY KEY
        CHECK (typeof(id) = 'text' AND length(CAST(id AS BLOB)) BETWEEN 1 AND 128),
    token_hash TEXT NOT NULL UNIQUE
        CHECK (typeof(token_hash) = 'text' AND length(token_hash) = 64
               AND token_hash NOT GLOB '*[^0-9a-f]*'),
    host TEXT NOT NULL CHECK (host IN ('claude', 'codex')),
    parent_session_id TEXT NOT NULL
        CHECK (typeof(parent_session_id) = 'text'
               AND length(CAST(parent_session_id AS BLOB)) BETWEEN 1 AND 512),
    parent_trace_id TEXT NOT NULL
        CHECK (typeof(parent_trace_id) = 'text'
               AND length(CAST(parent_trace_id AS BLOB)) BETWEEN 1 AND 512),
    work_unit_id TEXT NOT NULL DEFAULT ''
        CHECK (typeof(work_unit_id) = 'text'
               AND length(CAST(work_unit_id AS BLOB)) <= 160),
    worker_kind TEXT NOT NULL CHECK (worker_kind = 'generic-worker'),
    worker_id TEXT NOT NULL
        CHECK (typeof(worker_id) = 'text'
               AND length(CAST(worker_id AS BLOB)) BETWEEN 1 AND 256),
    native_run_id TEXT NOT NULL
        CHECK (typeof(native_run_id) = 'text'
               AND length(CAST(native_run_id AS BLOB)) BETWEEN 1 AND 256),
    child_session_id TEXT NOT NULL
        CHECK (typeof(child_session_id) = 'text'
               AND length(CAST(child_session_id AS BLOB)) BETWEEN 1 AND 512),
    child_trace_id TEXT NOT NULL DEFAULT ''
        CHECK (typeof(child_trace_id) = 'text'
               AND length(CAST(child_trace_id AS BLOB)) <= 512),
    issued_unix INTEGER NOT NULL CHECK (typeof(issued_unix) = 'integer'),
    expires_unix INTEGER NOT NULL
        CHECK (typeof(expires_unix) = 'integer'
               AND expires_unix > issued_unix
               AND expires_unix <= issued_unix + 600),
    created_at TEXT NOT NULL,
    consumed_at TEXT,
    consumed_unix INTEGER,
    CHECK (
        (consumed_at IS NULL AND consumed_unix IS NULL AND child_trace_id = '')
        OR
        (consumed_at IS NOT NULL AND typeof(consumed_unix) = 'integer'
         AND child_trace_id != '' AND consumed_unix >= issued_unix
         AND consumed_unix <= expires_unix)
    ),
    UNIQUE(host, parent_trace_id, worker_id, native_run_id),
    FOREIGN KEY (parent_trace_id) REFERENCES runs(trace_id) ON DELETE CASCADE
);
"""

NATIVE_CHILD_DELIVERY_VERIFICATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS native_child_delivery_verifications (
    decision_id TEXT PRIMARY KEY
        CHECK (typeof(decision_id) = 'text'
               AND length(CAST(decision_id AS BLOB)) BETWEEN 1 AND 512),
    nonce TEXT NOT NULL UNIQUE
        CHECK (typeof(nonce) = 'text'
               AND length(CAST(nonce AS BLOB)) BETWEEN 1 AND 512),
    artifact_digest TEXT NOT NULL UNIQUE
        CHECK (typeof(artifact_digest) = 'text' AND length(artifact_digest) = 64
               AND artifact_digest NOT GLOB '*[^0-9a-f]*'),
    host TEXT NOT NULL
        CHECK (host IN ('claude', 'codex', 'hermes', 'openclaw', 'zcode')),
    parent_session_id TEXT NOT NULL
        CHECK (typeof(parent_session_id) = 'text'
               AND length(CAST(parent_session_id AS BLOB)) BETWEEN 1 AND 512),
    parent_trace_id TEXT NOT NULL
        CHECK (typeof(parent_trace_id) = 'text'
               AND length(CAST(parent_trace_id AS BLOB)) BETWEEN 1 AND 512),
    launch_id TEXT NOT NULL
        CHECK (typeof(launch_id) = 'text'
               AND length(CAST(launch_id AS BLOB)) BETWEEN 1 AND 512),
    binding_kind TEXT NOT NULL
        CHECK (typeof(binding_kind) = 'text'
               AND length(CAST(binding_kind AS BLOB)) BETWEEN 2 AND 32
               AND substr(binding_kind, 1, 1) GLOB '[a-z]'
               AND binding_kind NOT GLOB '*[^a-z0-9_]*'),
    binding_id TEXT NOT NULL
        CHECK (typeof(binding_id) = 'text'
               AND length(CAST(binding_id AS BLOB)) BETWEEN 1 AND 512),
    child_id TEXT NOT NULL
        CHECK (typeof(child_id) = 'text'
               AND length(CAST(child_id AS BLOB)) BETWEEN 1 AND 512),
    verified_at TEXT NOT NULL
        CHECK (typeof(verified_at) = 'text'
               AND length(CAST(verified_at AS BLOB)) BETWEEN 20 AND 40),
    UNIQUE (
        host,
        parent_session_id,
        parent_trace_id,
        launch_id,
        binding_kind,
        binding_id
    ),
    UNIQUE (host, child_id),
    FOREIGN KEY (decision_id) REFERENCES routing_decisions(id) ON DELETE CASCADE
);
"""

NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL: dict[str, str] = {
    "agency_native_child_delivery_verifications_immutable_update": (
        "CREATE TRIGGER agency_native_child_delivery_verifications_immutable_update "
        "BEFORE UPDATE ON native_child_delivery_verifications BEGIN "
        "SELECT RAISE(ABORT, 'native child delivery verification is immutable'); END"
    ),
}

# The one content-carrying lane for a native child's assignment, kept OUT of
# the content-free routing-decision projection on purpose. Rows are written
# only while observability.capture_content is true and the text has already
# passed redact_content — the same write-side gate runs.user_message uses;
# turning the flag off stops new rows and existing ones age out with their
# owning routing decision via ON DELETE CASCADE, exactly like user_message
# ages out with its run.
NATIVE_CHILD_CAPTURED_ASSIGNMENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS native_child_captured_assignments (
    diagnostic_id TEXT PRIMARY KEY
        CHECK (typeof(diagnostic_id) = 'text'
               AND length(CAST(diagnostic_id AS BLOB)) BETWEEN 1 AND 512),
    host TEXT NOT NULL
        CHECK (host IN ('claude', 'codex', 'hermes', 'openclaw', 'zcode')),
    parent_session_id TEXT NOT NULL
        CHECK (typeof(parent_session_id) = 'text'
               AND length(CAST(parent_session_id AS BLOB)) BETWEEN 1 AND 512),
    parent_trace_id TEXT NOT NULL
        CHECK (typeof(parent_trace_id) = 'text'
               AND length(CAST(parent_trace_id AS BLOB)) BETWEEN 1 AND 512),
    task_sha256 TEXT NOT NULL
        CHECK (typeof(task_sha256) = 'text' AND length(task_sha256) = 64
               AND task_sha256 NOT GLOB '*[^0-9a-f]*'),
    captured_task TEXT NOT NULL
        CHECK (typeof(captured_task) = 'text'
               AND length(CAST(captured_task AS BLOB)) BETWEEN 1 AND 8192),
    created_at TEXT NOT NULL
        CHECK (typeof(created_at) = 'text'
               AND length(CAST(created_at AS BLOB)) BETWEEN 20 AND 40),
    FOREIGN KEY (diagnostic_id) REFERENCES routing_decisions(id) ON DELETE CASCADE
);
"""

CODEX_NATIVE_PLAN_SCOPE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS codex_native_plan_scopes (
    id TEXT PRIMARY KEY
        CHECK (typeof(id) = 'text' AND length(CAST(id AS BLOB)) BETWEEN 1 AND 128),
    session_id TEXT NOT NULL
        CHECK (typeof(session_id) = 'text'
               AND length(CAST(session_id AS BLOB)) BETWEEN 1 AND 512),
    trace_id TEXT NOT NULL
        CHECK (typeof(trace_id) = 'text'
               AND length(CAST(trace_id AS BLOB)) BETWEEN 1 AND 512),
    work_unit_id TEXT NOT NULL
        CHECK (typeof(work_unit_id) = 'text'
               AND length(CAST(work_unit_id AS BLOB)) BETWEEN 1 AND 160),
    scope_payload TEXT NOT NULL
        CHECK (typeof(scope_payload) = 'text'
               AND length(CAST(scope_payload AS BLOB)) BETWEEN 1 AND 8192),
    created_at TEXT NOT NULL,
    UNIQUE(trace_id, work_unit_id),
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id) ON DELETE CASCADE
);
"""

SCHEMA_V1 = (
    """
-- Run tracking
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL UNIQUE,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    started_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL DEFAULT '',
    evidence_revision INTEGER NOT NULL DEFAULT 0,
    turn_sequence INTEGER NOT NULL DEFAULT 0,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    user_message TEXT,
    metadata TEXT,
    terminal_finalization_id TEXT,
    reservation_token TEXT,
    preflight_attempt_token TEXT,
    preflight_state TEXT NOT NULL DEFAULT '',
    preflight_lease_expires_at TEXT NOT NULL DEFAULT '',
    preflight_request_fingerprint TEXT NOT NULL DEFAULT '',
    preflight_request_kind TEXT NOT NULL DEFAULT '',
    preflight_result TEXT NOT NULL DEFAULT ''
);

-- One immutable, content-free diagnostic for every terminal preflight failure.
CREATE TABLE IF NOT EXISTS preflight_failure_receipts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL UNIQUE,
    host TEXT NOT NULL DEFAULT 'unknown'
        CHECK (typeof(host) = 'text'
               AND length(CAST(host AS BLOB)) BETWEEN 1 AND 64),
    stage TEXT NOT NULL CHECK (stage IN (
        'lifecycle', 'resident_binding', 'routing_snapshot', 'route_request',
        'routing', 'assignment', 'context_hydration', 'context_delivery',
        'ready_commit', 'ready_read', 'direct_activation'
    )),
    reason_code TEXT NOT NULL CHECK (reason_code IN (
        'preflight_lifecycle_failed', 'resident_binding_failed',
        'routing_snapshot_failed', 'route_request_failed', 'routing_failed',
        'workforce_provider_unavailable', 'workforce_inference_failed',
        'substantive_specialist_unavailable', 'child_routing_unavailable',
        'assignment_failed', 'context_hydration_failed',
        'context_delivery_failed', 'ready_commit_failed', 'ready_read_failed',
        'direct_activation_failed'
    )),
    invariant_code TEXT NOT NULL DEFAULT ''
        CHECK (invariant_code IN ('', 'native_plan_scope_invalid')),
    exception_category TEXT NOT NULL CHECK (exception_category IN (
        'timeout', 'validation_error', 'permission_error', 'host_error',
        'runtime_error', 'internal_error', 'unavailable'
    )),
    provider_attempts TEXT NOT NULL DEFAULT '[]'
        CHECK (typeof(provider_attempts) = 'text'
               AND length(CAST(provider_attempts AS BLOB)) BETWEEN 2 AND 32768
               AND json_valid(provider_attempts)
               AND json_type(provider_attempts) = 'array'
               AND json_array_length(provider_attempts) <= 16),
    staffing_reason_codes TEXT NOT NULL DEFAULT '[]'
        CHECK (typeof(staffing_reason_codes) = 'text'
               AND length(CAST(staffing_reason_codes AS BLOB)) BETWEEN 2 AND 4096
               AND json_valid(staffing_reason_codes)
               AND json_type(staffing_reason_codes) = 'array'
               AND json_array_length(staffing_reason_codes) <= 32),
    hiring_reason_codes TEXT NOT NULL DEFAULT '[]'
        CHECK (typeof(hiring_reason_codes) = 'text'
               AND length(CAST(hiring_reason_codes AS BLOB)) BETWEEN 2 AND 4096
               AND json_valid(hiring_reason_codes)
               AND json_type(hiring_reason_codes) = 'array'
               AND json_array_length(hiring_reason_codes) <= 32),
    -- Why candidates were filtered out before the recruiter ever saw them.
    -- Without it a terminal staffing failure cannot be told apart from an
    -- ineligible roster, which cost two live re-runs to diagnose once.
    eligibility_reason_codes TEXT NOT NULL DEFAULT '[]'
        CHECK (typeof(eligibility_reason_codes) = 'text'
               AND length(CAST(eligibility_reason_codes AS BLOB)) BETWEEN 2 AND 4096
               AND json_valid(eligibility_reason_codes)
               AND json_type(eligibility_reason_codes) = 'array'
               AND json_array_length(eligibility_reason_codes) <= 32),
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS agency_preflight_failure_scope_insert
BEFORE INSERT ON preflight_failure_receipts
WHEN NOT EXISTS (
    SELECT 1 FROM runs WHERE runs.trace_id = NEW.trace_id
    AND COALESCE(runs.session_id, '') = NEW.session_id AND runs.host = NEW.host
    AND runs.status = 'preflight_failed'
)
BEGIN
    SELECT RAISE(ABORT, 'preflight failure receipt scope mismatch');
END;

CREATE TRIGGER IF NOT EXISTS agency_preflight_failure_immutable
BEFORE UPDATE ON preflight_failure_receipts
BEGIN
    SELECT RAISE(ABORT, 'preflight failure receipt is immutable');
END;

-- Model receipts (what actually ran)
CREATE TABLE IF NOT EXISTS model_receipts (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    requested_model TEXT,
    model_group TEXT,
    resolved_provider TEXT,
    resolved_model TEXT,
    api_base TEXT,
    attempted_fallbacks INTEGER DEFAULT 0,
    model_id TEXT,
    source TEXT NOT NULL DEFAULT 'unknown',
    recorded_at TEXT NOT NULL DEFAULT '',
    started_at TEXT,
    ended_at TEXT,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Skills loaded per session
CREATE TABLE IF NOT EXISTS skills_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL DEFAULT '',
    skill_name TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);

-- Specialist loads are immutable audit rows. expired_at only closes the
-- turn-scoped active projection; it never removes the historical load.
CREATE TABLE IF NOT EXISTS specialists_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL DEFAULT '',
    agent_slug TEXT NOT NULL,
    loaded_at TEXT NOT NULL,
    expired_at TEXT,
    activation_receipt_id TEXT
);

-- Compact parent-manager contracts are bound once per persistent host session.
-- Prompt bodies never enter this table; ready preflight recipes keep only the
-- current content-free binding receipt.
CREATE TABLE IF NOT EXISTS resident_manager_bindings (
    session_id TEXT NOT NULL,
    host TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    binding_version INTEGER NOT NULL,
    kernel_version INTEGER NOT NULL,
    kernel_hash TEXT NOT NULL,
    restore_generation INTEGER NOT NULL DEFAULT 0 CHECK (restore_generation >= 0),
    applied_restore_generation INTEGER NOT NULL DEFAULT 0
        CHECK (applied_restore_generation >= 0),
    pending_restore_generation INTEGER NOT NULL DEFAULT 0
        CHECK (pending_restore_generation >= 0),
    master_control_generation INTEGER,
    master_control_materialized INTEGER NOT NULL DEFAULT 0
        CHECK (master_control_materialized IN (0, 1)),
    host_control_generation INTEGER NOT NULL DEFAULT 0
        CHECK (host_control_generation >= 0),
    host_control_materialized INTEGER NOT NULL DEFAULT 0
        CHECK (host_control_materialized IN (0, 1)),
    bound_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_trace_id TEXT NOT NULL DEFAULT '',
    delivery_state TEXT NOT NULL DEFAULT 'acknowledged'
        CHECK (delivery_state IN ('pending', 'acknowledged')),
    pending_delivery_mode TEXT NOT NULL DEFAULT ''
        CHECK (pending_delivery_mode IN ('', 'injected', 'restored')),
    pending_trace_id TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (session_id, host),
    CHECK (
        applied_restore_generation <= pending_restore_generation
        AND pending_restore_generation <= restore_generation
    ),
    CHECK (
        (master_control_materialized = 1 AND master_control_generation >= 0)
        OR
        (
            master_control_materialized = 0
            AND (master_control_generation IS NULL OR master_control_generation = 0)
        )
    ),
    CHECK (host_control_materialized = 1 OR host_control_generation = 0),
    CHECK (
        (
            delivery_state = 'pending'
            AND pending_delivery_mode = 'injected'
            AND pending_trace_id <> ''
            AND pending_restore_generation = applied_restore_generation
        )
        OR
        (
            delivery_state = 'pending'
            AND pending_delivery_mode = 'restored'
            AND pending_trace_id <> ''
            AND pending_restore_generation > applied_restore_generation
        )
        OR
        (
            delivery_state = 'acknowledged'
            AND pending_delivery_mode = ''
            AND pending_trace_id = ''
            AND pending_restore_generation = applied_restore_generation
        )
    )
);

-- Delegation events
CREATE TABLE IF NOT EXISTS delegation_events (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    work_unit_id TEXT,
    recommended_agent TEXT,
    status TEXT NOT NULL DEFAULT 'suggested',
    backend TEXT,
    executed_worker_kind TEXT NOT NULL DEFAULT '',
    executed_worker_id TEXT NOT NULL DEFAULT '',
    native_run_id TEXT NOT NULL DEFAULT '',
    retrieved_specialist_slug TEXT NOT NULL DEFAULT '',
    retrieved_specialist_version TEXT NOT NULL DEFAULT '',
    retrieved_specialist_prompt_hash TEXT NOT NULL DEFAULT '',
    activation_receipt_id TEXT,
    skip_reason TEXT,
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Compatibility projection for one exact selected prompt grant. New rows keep
-- the immutable public capsule beside (but never inside) the bearer digest;
-- successful child consumption is appended to the separate ledger below.
CREATE TABLE IF NOT EXISTS delegation_activation_receipts (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    grant_id TEXT NOT NULL DEFAULT '',
    grant_payload TEXT NOT NULL DEFAULT '',
    grant_issued_unix INTEGER NOT NULL DEFAULT 0,
    grant_expires_unix INTEGER NOT NULL DEFAULT 0,
    child_host TEXT NOT NULL DEFAULT '',
    grant_origin TEXT NOT NULL DEFAULT 'manual_api'
        CHECK (grant_origin IN ('manual_api', 'native_hook')),
    tool_use_id TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    work_unit_id TEXT NOT NULL,
    specialist_slug TEXT NOT NULL,
    specialist_version TEXT NOT NULL,
    specialist_prompt_hash TEXT NOT NULL,
    worker_kind TEXT NOT NULL,
    worker_id TEXT NOT NULL DEFAULT '',
    native_run_id TEXT NOT NULL DEFAULT '',
    launch_model TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    consumed_at TEXT,
    delegation_event_id TEXT,
    UNIQUE(
        trace_id,
        work_unit_id,
        specialist_slug,
        specialist_version,
        specialist_prompt_hash
    ),
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
    FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
);

-- Append-only public consumption receipts. The legacy activation row above
-- remains the compatibility projection used by older evidence queries; its
-- public grant fields are immutable and its bearer digest never enters either
-- public payload.
CREATE TABLE IF NOT EXISTS delegation_activation_consumptions (
    id TEXT PRIMARY KEY,
    grant_id TEXT NOT NULL UNIQUE,
    legacy_activation_receipt_id TEXT NOT NULL UNIQUE,
    receipt_payload TEXT NOT NULL,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    work_unit_id TEXT NOT NULL,
    child_host TEXT NOT NULL
        CHECK (child_host IN ('claude', 'codex', 'hermes', 'openclaw', 'zcode')),
    specialist_slug TEXT NOT NULL,
    specialist_version TEXT NOT NULL,
    specialist_prompt_hash TEXT NOT NULL,
    worker_kind TEXT NOT NULL CHECK (worker_kind <> ''),
    worker_id TEXT NOT NULL CHECK (worker_id <> ''),
    native_run_id TEXT NOT NULL CHECK (native_run_id <> ''),
    consumed_at TEXT NOT NULL,
    consumed_unix INTEGER NOT NULL CHECK (consumed_unix > 0),
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
    FOREIGN KEY (legacy_activation_receipt_id)
        REFERENCES delegation_activation_receipts(id) ON DELETE CASCADE
);

-- Worker runs (delegation execution records)
CREATE TABLE IF NOT EXISTS worker_runs (
    id TEXT PRIMARY KEY,
    delegation_event_id TEXT,
    backend TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    work_unit_id TEXT NOT NULL DEFAULT '',
    host TEXT NOT NULL DEFAULT '',
    worker_id TEXT NOT NULL DEFAULT '',
    native_run_id TEXT NOT NULL DEFAULT '',
    workdir TEXT,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    started_at TEXT NOT NULL,
    execution_tool_use_id TEXT NOT NULL DEFAULT '',
    execution_dispatched_at TEXT,
    tool_evidence_schema TEXT NOT NULL DEFAULT '',
    tool_evidence TEXT NOT NULL DEFAULT '',
    tool_evidence_source TEXT NOT NULL DEFAULT '',
    tool_evidence_recorded_at TEXT,
    native_terminal_outcome TEXT NOT NULL DEFAULT ''
        CHECK (native_terminal_outcome IN
            ('', 'ok', 'error', 'timeout', 'killed', 'reset', 'deleted', 'unknown')),
    native_delivery_status TEXT NOT NULL DEFAULT ''
        CHECK (native_delivery_status IN ('', 'pending', 'delivered', 'failed', 'interrupted')),
    native_terminal_observed_at TEXT,
    native_delivery_observed_at TEXT,
    ended_at TEXT,
    FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
);

-- Finalization events
CREATE TABLE IF NOT EXISTS finalization_events (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    host TEXT NOT NULL,
    action TEXT NOT NULL,
    missing TEXT,
    response_hash TEXT,
    policy_response_hash TEXT,
    terminal_status TEXT,
    created_at TEXT NOT NULL
);

-- Roster tables
CREATE TABLE IF NOT EXISTS agent_sources (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    added_at TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    trusted_for_auto_approve INTEGER NOT NULL DEFAULT 0
        CHECK (trusted_for_auto_approve IN (0, 1))
);

CREATE TABLE IF NOT EXISTS agent_downloads (
    id TEXT PRIMARY KEY,
    source_id TEXT,
    slug TEXT NOT NULL,
    downloaded_at TEXT NOT NULL,
    hash TEXT,
    content TEXT,
    status TEXT NOT NULL DEFAULT 'quarantined',
    FOREIGN KEY (source_id) REFERENCES agent_sources(id)
);

CREATE TABLE IF NOT EXISTS agent_candidates (
    id TEXT PRIMARY KEY,
    download_id TEXT,
    slug TEXT NOT NULL,
    name TEXT,
    description TEXT,
    division TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    source TEXT,
    source_version TEXT NOT NULL DEFAULT '',
    version TEXT,
    hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    quarantined_at TEXT NOT NULL,
    FOREIGN KEY (download_id) REFERENCES agent_downloads(id)
);

CREATE TABLE IF NOT EXISTS agent_candidate_audits (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    audit_revision TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    candidate_version TEXT NOT NULL,
    candidate_hash TEXT NOT NULL,
    active_basis_hash TEXT NOT NULL,
    deterministic_status TEXT NOT NULL
        CHECK (deterministic_status IN ('passed', 'failed')),
    inference_status TEXT NOT NULL
        CHECK (inference_status IN ('not_requested', 'passed', 'failed', 'unavailable')),
    verdict TEXT NOT NULL
        CHECK (verdict IN ('passed', 'failed', 'degraded')),
    provider TEXT NOT NULL DEFAULT '',
    inference_evidence TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(candidate_id, audit_revision),
    FOREIGN KEY (candidate_id) REFERENCES agent_candidates(id)
);

CREATE TABLE IF NOT EXISTS agent_candidate_audit_findings (
    id TEXT PRIMARY KEY,
    audit_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('deterministic', 'conflict', 'inference')),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    code TEXT NOT NULL,
    message TEXT NOT NULL,
    evidence_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(audit_id, source, code, evidence_hash),
    FOREIGN KEY (audit_id) REFERENCES agent_candidate_audits(id)
);

CREATE TABLE IF NOT EXISTS agent_candidate_status_events (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    audit_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (candidate_id) REFERENCES agent_candidates(id)
);

CREATE TABLE IF NOT EXISTS agent_versions (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    version TEXT NOT NULL,
    source_version TEXT NOT NULL DEFAULT '',
    source_id TEXT NOT NULL DEFAULT '',
    hash TEXT NOT NULL,
    content TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(agent_slug, version)
);

CREATE TABLE IF NOT EXISTS agent_source_scans (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('complete', 'partial')),
    manifest_hash TEXT NOT NULL,
    entry_count INTEGER NOT NULL,
    candidate_count INTEGER NOT NULL,
    quarantined_count INTEGER NOT NULL,
    ignored_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES agent_sources(id)
);

CREATE TABLE IF NOT EXISTS agent_source_scan_entries (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    slug TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'quarantined', 'ignored')),
    candidate_id TEXT,
    UNIQUE(scan_id, relative_path),
    FOREIGN KEY (scan_id) REFERENCES agent_source_scans(id),
    FOREIGN KEY (candidate_id) REFERENCES agent_candidates(id)
);

CREATE TABLE IF NOT EXISTS agent_categories (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    category TEXT NOT NULL,
    UNIQUE(agent_slug, category)
);

CREATE TABLE IF NOT EXISTS agent_embeddings (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL UNIQUE,
    embedding TEXT,
    model TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_snapshots (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    agent_count INTEGER,
    manifest TEXT,
    activated INTEGER NOT NULL DEFAULT 0 CHECK (activated IN (0, 1)),
    approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
    added_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    removed_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS agent_active (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL UNIQUE,
    name TEXT,
    division TEXT,
    description TEXT,
    source TEXT,
    source_id TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT '',
    version TEXT,
    hash TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_retirements (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    source_id TEXT NOT NULL,
    version TEXT NOT NULL,
    hash TEXT NOT NULL,
    source_scan_id TEXT NOT NULL,
    active_record TEXT NOT NULL,
    retired_at TEXT NOT NULL,
    FOREIGN KEY (source_scan_id) REFERENCES agent_source_scans(id)
);

CREATE TABLE IF NOT EXISTS agent_import_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    agent_slug TEXT,
    detail TEXT,
    created_at TEXT NOT NULL,
    event_sequence INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(event_sequence) = 'integer' AND event_sequence >= 0)
);

-- Agency-owned workforce identity and lifecycle overlays. Upstream prompt
-- revisions remain immutable in agent_versions; these tables never rewrite
-- source provenance.
CREATE TABLE IF NOT EXISTS agent_workers (
    worker_id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('upstream', 'agency')),
    employment_class TEXT NOT NULL
        CHECK (employment_class IN ('contractor', 'employee')),
    standing TEXT NOT NULL DEFAULT 'active'
        CHECK (standing IN ('active', 'suspended', 'retired', 'merged')),
    current_agent_version_id TEXT NOT NULL,
    current_version TEXT NOT NULL,
    current_hash TEXT NOT NULL,
    merged_into_worker_id TEXT,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (standing = 'merged' AND merged_into_worker_id IS NOT NULL)
        OR (standing <> 'merged' AND merged_into_worker_id IS NULL)
    ),
    FOREIGN KEY (merged_into_worker_id) REFERENCES agent_workers(worker_id)
);

CREATE TABLE IF NOT EXISTS agent_hiring_cases (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    case_type TEXT NOT NULL CHECK (case_type IN ('hire', 'amend')),
    status TEXT NOT NULL
        CHECK (status IN ('proposed', 'audited', 'rejected', 'applied', 'folded')),
    proposed_slug TEXT NOT NULL,
    target_worker_id TEXT,
    session_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    work_unit_id TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    gap_evidence TEXT NOT NULL,
    duplicate_evidence TEXT NOT NULL,
    contract_evidence TEXT NOT NULL DEFAULT '{}',
    critic_evidence TEXT NOT NULL DEFAULT '{}',
    model_evidence TEXT NOT NULL DEFAULT '{}',
    contract_hash TEXT NOT NULL DEFAULT '',
    risk_tier TEXT NOT NULL DEFAULT 'standard'
        CHECK (risk_tier IN ('low', 'standard', 'high')),
    human_approval_required INTEGER NOT NULL DEFAULT 0
        CHECK (human_approval_required IN (0, 1)),
    human_approved_by TEXT NOT NULL DEFAULT '',
    human_approved_at TEXT,
    created_at TEXT NOT NULL,
    decided_at TEXT,
    applied_at TEXT,
    FOREIGN KEY (target_worker_id) REFERENCES agent_workers(worker_id)
);

CREATE TABLE IF NOT EXISTS agent_version_lineage (
    id TEXT PRIMARY KEY,
    worker_id TEXT NOT NULL,
    agent_version_id TEXT NOT NULL UNIQUE,
    parent_version_id TEXT,
    relation TEXT NOT NULL
        CHECK (relation IN ('generated', 'upstream_update', 'agency_amendment', 'merge')),
    recruitment_contract TEXT NOT NULL,
    recruitment_contract_hash TEXT NOT NULL,
    hiring_case_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id),
    FOREIGN KEY (hiring_case_id) REFERENCES agent_hiring_cases(id)
);

CREATE TABLE IF NOT EXISTS agent_recruitment_contract_projections (
    id TEXT PRIMARY KEY,
    projection_sequence INTEGER NOT NULL UNIQUE CHECK (projection_sequence > 0),
    worker_id TEXT NOT NULL,
    agent_version_id TEXT NOT NULL,
    parent_contract_hash TEXT NOT NULL,
    recruitment_contract TEXT NOT NULL,
    recruitment_contract_hash TEXT NOT NULL,
    projection_authority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id),
    FOREIGN KEY (agent_version_id) REFERENCES agent_versions(id)
);

CREATE TABLE IF NOT EXISTS agent_worker_events (
    id TEXT PRIMARY KEY,
    event_sequence INTEGER NOT NULL UNIQUE CHECK (event_sequence > 0),
    worker_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    from_class TEXT NOT NULL DEFAULT '',
    to_class TEXT NOT NULL DEFAULT '',
    from_standing TEXT NOT NULL DEFAULT '',
    to_standing TEXT NOT NULL DEFAULT '',
    version TEXT NOT NULL DEFAULT '',
    merged_into_worker_id TEXT,
    hiring_case_id TEXT,
    actor TEXT NOT NULL DEFAULT '',
    surface TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id),
    FOREIGN KEY (merged_into_worker_id) REFERENCES agent_workers(worker_id),
    FOREIGN KEY (hiring_case_id) REFERENCES agent_hiring_cases(id)
);

CREATE TABLE IF NOT EXISTS agent_performance_events (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    worker_id TEXT NOT NULL,
    version TEXT NOT NULL,
    version_hash TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    trace_id TEXT NOT NULL DEFAULT '',
    work_unit_id TEXT NOT NULL DEFAULT '',
    activation_receipt_id TEXT NOT NULL DEFAULT '',
    event_type TEXT NOT NULL,
    outcome TEXT NOT NULL,
    score REAL,
    evidence_hash TEXT NOT NULL,
    evidence_refs TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    CHECK (score IS NULL OR (score >= 0.0 AND score <= 1.0)),
    FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id)
);

-- Cross-process routing reuse.
--
-- The in-memory routing cache cannot hit in production: every hook event runs
-- as its own short-lived process, so the module-level dict is constructed
-- empty and destroyed on every turn.  This table is the same cache with a
-- lifetime the hook model actually provides.
--
-- Payload is restricted to the routing fields already allowlisted for
-- persistence.  The live routing dict also carries work-unit text and unit
-- descriptors, which the decision projection deliberately drops; a cache is
-- not a reason to widen what the store retains.  Anything a reuse needs but
-- cannot be persisted -- the compatibility receipt above all -- is recomputed
-- from the live catalog on read, which is deterministic and local.
CREATE TABLE IF NOT EXISTS routing_cache (
    cache_key TEXT PRIMARY KEY,
    context_fingerprint TEXT NOT NULL DEFAULT '',
    source_message_hash TEXT NOT NULL DEFAULT '',
    routing TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Opt-in audit trail for selection quality.
--
-- Every other routing table is content-free on purpose, and that is exactly
-- why selection quality could not be audited: the store keeps
-- source_message_hash and query_hash but never what was asked, so "did this
-- turn get the right specialists?" is unanswerable after the fact.  Measured
-- 2026-08-11, frontend-developer was staffed on a turn that excluded frontend
-- work and skipped on a turn that was entirely frontend work -- a finding that
-- only existed because two humans remembered the prompts.
--
-- This table therefore holds retained content and is the one place that does.
-- It is written only when selector.record_routing_intent is enabled, never by
-- default, is bounded per row and in total, and is purged with the rest of the
-- runtime evidence.  work_units text is what the planner derived from the
-- message, not the message itself.
CREATE TABLE IF NOT EXISTS routing_intent (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT NOT NULL DEFAULT '',
    session_id TEXT NOT NULL DEFAULT '',
    query_hash TEXT NOT NULL DEFAULT '',
    context_fingerprint TEXT NOT NULL DEFAULT '',
    units TEXT NOT NULL DEFAULT '[]',
    descriptors TEXT NOT NULL DEFAULT '[]',
    selected_ids TEXT NOT NULL DEFAULT '[]',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

-- Schema version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

-- Immutable routing decision projections. Raw prompt content is omitted by
-- default; query_hash supports correlation without content capture.
CREATE TABLE IF NOT EXISTS routing_decisions (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    session_id TEXT,
    query_hash TEXT NOT NULL,
    context_fingerprint TEXT,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    selected_ids TEXT,
    semantic_ids TEXT,
    companion_ids TEXT,
    confidence REAL,
    latency_ms INTEGER,
    provider TEXT,
    work_units TEXT,
    decision TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Store-local material for content-free integrity identities and monotonic
-- turn ordering. Neither table contains prompt, response, or trace content.
CREATE TABLE IF NOT EXISTS store_secrets (
    name TEXT PRIMARY KEY,
    secret BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS store_counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);

INSERT OR IGNORE INTO store_counters (name, value) VALUES ('turn-sequence', 0);
INSERT OR IGNORE INTO store_counters (name, value) VALUES ('roster-generation', 0);
INSERT OR IGNORE INTO store_counters (name, value)
VALUES ('source-redaction-purge-pending', 0);

-- Permanent, fixed-size anti-resurrection markers. HMAC identities prevent
-- low-entropy caller trace/session values from being stored or exposed as
-- plain unsalted hashes after the runtime evidence graph is deleted.
CREATE TABLE IF NOT EXISTS trace_tombstones (
    trace_digest TEXT PRIMARY KEY,
    session_digest TEXT NOT NULL,
    turn_sequence INTEGER NOT NULL,
    retired_at TEXT NOT NULL
);

-- Persistent, host-scoped soft control. Native plugins remain registered so
-- their control surface can turn the runtime back on without an installer.
CREATE TABLE IF NOT EXISTS host_controls (
    host TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    generation INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0),
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL
);

-- Last successful content-free live canary for each host contract.
CREATE TABLE IF NOT EXISTS host_canary_attestations (
    host TEXT PRIMARY KEY,
    proof_contract TEXT NOT NULL,
    proof_digest TEXT NOT NULL,
    profile_scope TEXT NOT NULL,
    platform_system TEXT NOT NULL,
    platform_release TEXT NOT NULL,
    platform_machine TEXT NOT NULL,
    host_version TEXT NOT NULL,
    plugin_version TEXT NOT NULL,
    install_id TEXT NOT NULL,
    bundle_digest TEXT NOT NULL,
    passed_at TEXT NOT NULL,
    trace_id TEXT NOT NULL
);

-- Cross-process routing protection for native children. Assignment text is
-- represented only by a keyed hash; cache values contain content-free routing
-- projections and expire automatically.
CREATE TABLE IF NOT EXISTS child_routing_cache (
    cache_key TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    expires_at REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS child_routing_usage (
    parent_trace_id TEXT PRIMARY KEY,
    parent_session_id TEXT NOT NULL,
    inference_calls INTEGER NOT NULL CHECK (inference_calls >= 0),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS child_routing_leases (
    cache_key TEXT PRIMARY KEY,
    parent_trace_id TEXT NOT NULL,
    owner_token TEXT NOT NULL UNIQUE,
    expires_at REAL NOT NULL,
    created_at TEXT NOT NULL
);

-- Single-use bearer receipts transfer exact parent scope across independent
-- native-hook/MCP processes. Prompt and assignment content never enter this
-- projection.
CREATE TABLE IF NOT EXISTS native_child_parent_scopes (
    id TEXT PRIMARY KEY
        CHECK (typeof(id) = 'text' AND length(CAST(id AS BLOB)) BETWEEN 1 AND 128),
    token_hash TEXT NOT NULL UNIQUE
        CHECK (typeof(token_hash) = 'text' AND length(token_hash) = 64
               AND token_hash NOT GLOB '*[^0-9a-f]*'),
    host TEXT NOT NULL CHECK (host IN ('claude', 'codex')),
    parent_session_id TEXT NOT NULL
        CHECK (typeof(parent_session_id) = 'text'
               AND length(CAST(parent_session_id AS BLOB)) BETWEEN 1 AND 512),
    parent_trace_id TEXT NOT NULL
        CHECK (typeof(parent_trace_id) = 'text'
               AND length(CAST(parent_trace_id AS BLOB)) BETWEEN 1 AND 512),
    work_unit_id TEXT NOT NULL DEFAULT ''
        CHECK (typeof(work_unit_id) = 'text'
               AND length(CAST(work_unit_id AS BLOB)) <= 160),
    worker_kind TEXT NOT NULL CHECK (worker_kind = 'generic-worker'),
    worker_id TEXT NOT NULL
        CHECK (typeof(worker_id) = 'text'
               AND length(CAST(worker_id AS BLOB)) BETWEEN 1 AND 256),
    native_run_id TEXT NOT NULL
        CHECK (typeof(native_run_id) = 'text'
               AND length(CAST(native_run_id AS BLOB)) BETWEEN 1 AND 256),
    child_session_id TEXT NOT NULL
        CHECK (typeof(child_session_id) = 'text'
               AND length(CAST(child_session_id AS BLOB)) BETWEEN 1 AND 512),
    child_trace_id TEXT NOT NULL DEFAULT ''
        CHECK (typeof(child_trace_id) = 'text'
               AND length(CAST(child_trace_id AS BLOB)) <= 512),
    issued_unix INTEGER NOT NULL CHECK (typeof(issued_unix) = 'integer'),
    expires_unix INTEGER NOT NULL
        CHECK (typeof(expires_unix) = 'integer'
               AND expires_unix > issued_unix
               AND expires_unix <= issued_unix + 600),
    created_at TEXT NOT NULL,
    consumed_at TEXT,
    consumed_unix INTEGER,
    CHECK (
        (consumed_at IS NULL AND consumed_unix IS NULL AND child_trace_id = '')
        OR
        (consumed_at IS NOT NULL AND typeof(consumed_unix) = 'integer'
         AND child_trace_id != '' AND consumed_unix >= issued_unix
         AND consumed_unix <= expires_unix)
    ),
    UNIQUE(host, parent_trace_id, worker_id, native_run_id),
    FOREIGN KEY (parent_trace_id) REFERENCES runs(trace_id) ON DELETE CASCADE
);

-- Private, ephemeral path authority for exact Codex plan rows. Unlike the
-- content-free ready recipe, this table is never a public evidence projection;
-- terminalization removes every unconsumed scope for the turn.
CREATE TABLE IF NOT EXISTS codex_native_plan_scopes (
    id TEXT PRIMARY KEY
        CHECK (typeof(id) = 'text' AND length(CAST(id AS BLOB)) BETWEEN 1 AND 128),
    session_id TEXT NOT NULL
        CHECK (typeof(session_id) = 'text'
               AND length(CAST(session_id AS BLOB)) BETWEEN 1 AND 512),
    trace_id TEXT NOT NULL
        CHECK (typeof(trace_id) = 'text'
               AND length(CAST(trace_id AS BLOB)) BETWEEN 1 AND 512),
    work_unit_id TEXT NOT NULL
        CHECK (typeof(work_unit_id) = 'text'
               AND length(CAST(work_unit_id AS BLOB)) BETWEEN 1 AND 160),
    scope_payload TEXT NOT NULL
        CHECK (typeof(scope_payload) = 'text'
               AND length(CAST(scope_payload AS BLOB)) BETWEEN 1 AND 8192),
    created_at TEXT NOT NULL,
    UNIQUE(trace_id, work_unit_id),
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id) ON DELETE CASCADE
);

-- Read-path indexes used by hooks, the dashboard, and retention jobs.
CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_recent ON runs(started_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_trace_id ON model_receipts(trace_id);
CREATE INDEX IF NOT EXISTS idx_receipts_session_ended ON model_receipts(session_id, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_recent ON model_receipts(COALESCE(ended_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_skills_session_loaded ON skills_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_specialists_session_loaded ON specialists_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_specialists_recent ON specialists_loaded(loaded_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_resident_manager_bindings_updated
    ON resident_manager_bindings(updated_at DESC, session_id, host);
CREATE INDEX IF NOT EXISTS idx_delegations_trace_id ON delegation_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_delegations_session_started ON delegation_events(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_delegations_recent ON delegation_events(COALESCE(completed_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_activation_receipts_trace ON delegation_activation_receipts(trace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_activation_receipts_work_unit ON delegation_activation_receipts(trace_id, work_unit_id, consumed_at);
CREATE INDEX IF NOT EXISTS idx_activation_consumptions_trace
ON delegation_activation_consumptions(trace_id, consumed_at);
CREATE INDEX IF NOT EXISTS idx_activation_consumptions_work_unit
ON delegation_activation_consumptions(trace_id, work_unit_id, consumed_at);
CREATE INDEX IF NOT EXISTS idx_worker_runs_event ON worker_runs(delegation_event_id);
CREATE INDEX IF NOT EXISTS idx_finalization_trace_created ON finalization_events(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_finalization_trace_action ON finalization_events(trace_id, action);
CREATE INDEX IF NOT EXISTS idx_finalization_recent ON finalization_events(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_routing_trace_created ON routing_decisions(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_session_created ON routing_decisions(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_recent ON routing_decisions(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_routing_query_hash ON routing_decisions(query_hash, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trace_tombstones_retired ON trace_tombstones(retired_at);
CREATE INDEX IF NOT EXISTS idx_child_routing_cache_expiry ON child_routing_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_child_routing_leases_parent
ON child_routing_leases(parent_trace_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_native_child_parent_scopes_expiry
ON native_child_parent_scopes(expires_unix, consumed_unix);
CREATE INDEX IF NOT EXISTS idx_codex_native_plan_scopes_trace
ON codex_native_plan_scopes(trace_id, work_unit_id);
CREATE INDEX IF NOT EXISTS idx_agent_source_scans_source_created
ON agent_source_scans(source_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_source_scan_entries_slug
ON agent_source_scan_entries(scan_id, slug);
CREATE INDEX IF NOT EXISTS idx_agent_retirements_slug
ON agent_retirements(agent_slug, retired_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_audits_candidate_created
ON agent_candidate_audits(candidate_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_audit_findings_audit
ON agent_candidate_audit_findings(audit_id, severity, code);
CREATE INDEX IF NOT EXISTS idx_candidate_status_events_candidate_created
ON agent_candidate_status_events(candidate_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_import_events_type_created
ON agent_import_events(event_type, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_agent_workers_state
ON agent_workers(standing, employment_class, agent_slug);
CREATE INDEX IF NOT EXISTS idx_agent_workers_current_version
ON agent_workers(current_agent_version_id);
CREATE INDEX IF NOT EXISTS idx_agent_hiring_cases_created
ON agent_hiring_cases(created_at DESC, id DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_lineage_hiring_case_once
ON agent_version_lineage(hiring_case_id) WHERE hiring_case_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agent_worker_events_worker_sequence
ON agent_worker_events(worker_id, event_sequence DESC);
CREATE INDEX IF NOT EXISTS idx_agent_contract_projections_worker_sequence
ON agent_recruitment_contract_projections(
    worker_id, agent_version_id, projection_sequence DESC
);
CREATE INDEX IF NOT EXISTS idx_agent_performance_worker_created
ON agent_performance_events(worker_id, created_at DESC, id DESC);
CREATE TRIGGER IF NOT EXISTS agency_version_lineage_immutable_update
BEFORE UPDATE ON agent_version_lineage BEGIN
SELECT RAISE(ABORT, 'agent version lineage is immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_version_lineage_immutable_delete
BEFORE DELETE ON agent_version_lineage BEGIN
SELECT RAISE(ABORT, 'agent version lineage is immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_contract_projections_immutable_update
BEFORE UPDATE ON agent_recruitment_contract_projections BEGIN
SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_contract_projections_immutable_delete
BEFORE DELETE ON agent_recruitment_contract_projections BEGIN
SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_worker_events_immutable_update
BEFORE UPDATE ON agent_worker_events BEGIN
SELECT RAISE(ABORT, 'agent worker events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_worker_events_immutable_delete
BEFORE DELETE ON agent_worker_events BEGIN
SELECT RAISE(ABORT, 'agent worker events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_performance_events_immutable_update
BEFORE UPDATE ON agent_performance_events BEGIN
SELECT RAISE(ABORT, 'agent performance events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_workers_immutable_delete
BEFORE DELETE ON agent_workers BEGIN
SELECT RAISE(ABORT, 'agent workforce identity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_hiring_case_evidence_immutable
BEFORE UPDATE ON agent_hiring_cases
WHEN OLD.id IS NOT NEW.id
  OR OLD.idempotency_key IS NOT NEW.idempotency_key
  OR OLD.case_type IS NOT NEW.case_type
  OR OLD.proposed_slug IS NOT NEW.proposed_slug
  OR OLD.target_worker_id IS NOT NEW.target_worker_id
  OR OLD.session_id IS NOT NEW.session_id
  OR OLD.trace_id IS NOT NEW.trace_id
  OR OLD.work_unit_id IS NOT NEW.work_unit_id
  OR OLD.request_hash IS NOT NEW.request_hash
  OR OLD.gap_evidence IS NOT NEW.gap_evidence
  OR OLD.duplicate_evidence IS NOT NEW.duplicate_evidence
  OR OLD.contract_evidence IS NOT NEW.contract_evidence
  OR OLD.critic_evidence IS NOT NEW.critic_evidence
  OR OLD.model_evidence IS NOT NEW.model_evidence
  OR OLD.contract_hash IS NOT NEW.contract_hash
  OR OLD.risk_tier IS NOT NEW.risk_tier
  OR OLD.human_approval_required IS NOT NEW.human_approval_required
  OR OLD.created_at IS NOT NEW.created_at
BEGIN SELECT RAISE(ABORT, 'agent hiring evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_hiring_cases_immutable_delete
BEFORE DELETE ON agent_hiring_cases BEGIN
SELECT RAISE(ABORT, 'agent hiring evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS agency_hiring_case_status_transition
BEFORE UPDATE OF status ON agent_hiring_cases
WHEN NEW.status != OLD.status AND NOT (
    (OLD.status = 'proposed' AND NEW.status IN ('audited', 'rejected', 'folded'))
    OR (OLD.status = 'audited' AND NEW.status IN ('applied', 'rejected', 'folded'))
)
BEGIN SELECT RAISE(ABORT, 'invalid agent hiring status transition'); END;
CREATE TRIGGER IF NOT EXISTS agency_hiring_case_applied_authority
BEFORE UPDATE OF status ON agent_hiring_cases
WHEN NEW.status = 'applied' AND NOT EXISTS (
    SELECT 1 FROM agent_version_lineage AS lineage
    WHERE lineage.hiring_case_id = NEW.id
)
BEGIN SELECT RAISE(ABORT, 'agent hiring case lacks applied lineage'); END;
CREATE TRIGGER IF NOT EXISTS agency_hiring_case_human_approval_once
BEFORE UPDATE OF human_approved_by, human_approved_at ON agent_hiring_cases
WHEN (NEW.human_approved_by IS NOT OLD.human_approved_by
      OR NEW.human_approved_at IS NOT OLD.human_approved_at)
  AND NOT (
      OLD.status = 'proposed'
      AND OLD.human_approval_required = 1
      AND OLD.human_approved_by = ''
      AND OLD.human_approved_at IS NULL
      AND NEW.human_approved_by != ''
      AND NEW.human_approved_at IS NOT NULL
  )
BEGIN SELECT RAISE(ABORT, 'agent hiring approval is immutable'); END;
"""
    + "\n"
    + NATIVE_CHILD_DELIVERY_VERIFICATION_TABLE_SQL
    + "\n"
    + NATIVE_CHILD_CAPTURED_ASSIGNMENT_TABLE_SQL
    + "\n"
    + "\n".join(
        statement.replace("CREATE TRIGGER ", "CREATE TRIGGER IF NOT EXISTS ", 1) + ";"
        for statement in NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL.values()
    )
    + "\n"
    + "\n".join(
        (
            _REMEDIATION_RESOLUTION_INDEX_SQL + ";",
            _REMEDIATION_QUEUE_IDENTITY_INDEX_SQL + ";",
            # This index is installed by create_remediation_indexes() after legacy
            # agent_import_events rows gain their v31 event_sequence column.
            _REMEDIATION_SCAN_PROVENANCE_INDEX_SQL + ";",
        )
    )
)

ALL_TABLES: tuple[str, ...] = (
    "runs",
    "preflight_failure_receipts",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "resident_manager_bindings",
    "delegation_activation_receipts",
    "delegation_activation_consumptions",
    "delegation_events",
    "worker_runs",
    "finalization_events",
    "routing_decisions",
    "native_child_delivery_verifications",
    "native_child_captured_assignments",
    "store_secrets",
    "store_counters",
    "trace_tombstones",
    "host_controls",
    "host_canary_attestations",
    "child_routing_cache",
    "child_routing_usage",
    "child_routing_leases",
    "native_child_parent_scopes",
    "codex_native_plan_scopes",
    "agent_sources",
    "agent_downloads",
    "agent_candidates",
    "agent_candidate_audits",
    "agent_candidate_audit_findings",
    "agent_candidate_status_events",
    "agent_versions",
    "agent_source_scans",
    "agent_source_scan_entries",
    "agent_categories",
    "agent_embeddings",
    "agent_snapshots",
    "agent_active",
    "agent_retirements",
    "agent_import_events",
    "agent_workers",
    "agent_hiring_cases",
    "agent_version_lineage",
    "agent_recruitment_contract_projections",
    "agent_worker_events",
    "agent_performance_events",
    "agent_remediation_resolution_dependencies",
    "agent_remediation_resolution_authority",
    "schema_version",
)

RUNTIME_TABLE_TIMESTAMPS: dict[str, str] = {
    "runs": "last_activity_at",
    "preflight_failure_receipts": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = preflight_failure_receipts.trace_id), "
        "preflight_failure_receipts.recorded_at)"
    ),
    "model_receipts": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = model_receipts.trace_id), '')"
    ),
    "skills_loaded": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = skills_loaded.trace_id), skills_loaded.loaded_at)"
    ),
    "specialists_loaded": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = specialists_loaded.trace_id), "
        "specialists_loaded.loaded_at)"
    ),
    "delegation_activation_receipts": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = delegation_activation_receipts.trace_id), "
        "delegation_activation_receipts.created_at)"
    ),
    "delegation_events": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = delegation_events.trace_id), '')"
    ),
    "worker_runs": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = worker_runs.trace_id), "
        "(SELECT activity.last_activity_at FROM delegation_events AS activity_event "
        "JOIN runs AS activity ON activity.trace_id = activity_event.trace_id "
        "WHERE activity_event.id = worker_runs.delegation_event_id), '')"
    ),
    "finalization_events": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = finalization_events.trace_id), '')"
    ),
    "routing_decisions": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = routing_decisions.trace_id), '')"
    ),
    "routing_intent": (
        "COALESCE((SELECT activity.last_activity_at FROM runs AS activity "
        "WHERE activity.trace_id = routing_intent.trace_id), routing_intent.created_at)"
    ),
    "child_routing_cache": "child_routing_cache.created_at",
    "child_routing_usage": "child_routing_usage.updated_at",
    "child_routing_leases": "child_routing_leases.created_at",
    "native_child_parent_scopes": "native_child_parent_scopes.created_at",
    "resident_manager_bindings": "resident_manager_bindings.updated_at",
    "agent_performance_events": "agent_performance_events.created_at",
}

RUNTIME_DELETE_ORDER: tuple[str, ...] = (
    "agent_performance_events",
    "delegation_activation_receipts",
    "worker_runs",
    "delegation_events",
    "preflight_failure_receipts",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "resident_manager_bindings",
    "native_child_parent_scopes",
    "child_routing_leases",
    "child_routing_cache",
    "child_routing_usage",
    "routing_intent",
    "routing_decisions",
    "finalization_events",
    "runs",
)


def ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    """Add a SQLite column when opening a database created by an older build."""

    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


_WORKFORCE_INVARIANT_SCHEMA_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_lineage_hiring_case_once "
    "ON agent_version_lineage(hiring_case_id) WHERE hiring_case_id IS NOT NULL",
    "CREATE TRIGGER IF NOT EXISTS agency_version_lineage_immutable_update "
    "BEFORE UPDATE ON agent_version_lineage BEGIN "
    "SELECT RAISE(ABORT, 'agent version lineage is immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_version_lineage_immutable_delete "
    "BEFORE DELETE ON agent_version_lineage BEGIN "
    "SELECT RAISE(ABORT, 'agent version lineage is immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_contract_projections_immutable_update "
    "BEFORE UPDATE ON agent_recruitment_contract_projections BEGIN "
    "SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_contract_projections_immutable_delete "
    "BEFORE DELETE ON agent_recruitment_contract_projections BEGIN "
    "SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_worker_events_immutable_update "
    "BEFORE UPDATE ON agent_worker_events BEGIN "
    "SELECT RAISE(ABORT, 'agent worker events are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_worker_events_immutable_delete "
    "BEFORE DELETE ON agent_worker_events BEGIN "
    "SELECT RAISE(ABORT, 'agent worker events are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_performance_events_immutable_update "
    "BEFORE UPDATE ON agent_performance_events BEGIN "
    "SELECT RAISE(ABORT, 'agent performance events are immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_workers_immutable_delete "
    "BEFORE DELETE ON agent_workers BEGIN "
    "SELECT RAISE(ABORT, 'agent workforce identity is immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_hiring_case_evidence_immutable "
    "BEFORE UPDATE ON agent_hiring_cases "
    "WHEN OLD.id IS NOT NEW.id "
    "OR OLD.idempotency_key IS NOT NEW.idempotency_key "
    "OR OLD.case_type IS NOT NEW.case_type "
    "OR OLD.proposed_slug IS NOT NEW.proposed_slug "
    "OR OLD.target_worker_id IS NOT NEW.target_worker_id "
    "OR OLD.session_id IS NOT NEW.session_id "
    "OR OLD.trace_id IS NOT NEW.trace_id "
    "OR OLD.work_unit_id IS NOT NEW.work_unit_id "
    "OR OLD.request_hash IS NOT NEW.request_hash "
    "OR OLD.gap_evidence IS NOT NEW.gap_evidence "
    "OR OLD.duplicate_evidence IS NOT NEW.duplicate_evidence "
    "OR OLD.contract_evidence IS NOT NEW.contract_evidence "
    "OR OLD.critic_evidence IS NOT NEW.critic_evidence "
    "OR OLD.model_evidence IS NOT NEW.model_evidence "
    "OR OLD.contract_hash IS NOT NEW.contract_hash "
    "OR OLD.risk_tier IS NOT NEW.risk_tier "
    "OR OLD.human_approval_required IS NOT NEW.human_approval_required "
    "OR OLD.created_at IS NOT NEW.created_at "
    "BEGIN SELECT RAISE(ABORT, 'agent hiring evidence is immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_hiring_cases_immutable_delete "
    "BEFORE DELETE ON agent_hiring_cases BEGIN "
    "SELECT RAISE(ABORT, 'agent hiring evidence is immutable'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_hiring_case_status_transition "
    "BEFORE UPDATE OF status ON agent_hiring_cases "
    "WHEN NEW.status != OLD.status AND NOT ("
    "(OLD.status = 'proposed' AND NEW.status IN ('audited', 'rejected', 'folded')) "
    "OR (OLD.status = 'audited' AND NEW.status IN ('applied', 'rejected', 'folded'))) "
    "BEGIN SELECT RAISE(ABORT, 'invalid agent hiring status transition'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_hiring_case_applied_authority "
    "BEFORE UPDATE OF status ON agent_hiring_cases "
    "WHEN NEW.status = 'applied' AND NOT EXISTS ("
    "SELECT 1 FROM agent_version_lineage AS lineage "
    "WHERE lineage.hiring_case_id = NEW.id) "
    "BEGIN SELECT RAISE(ABORT, 'agent hiring case lacks applied lineage'); END",
    "CREATE TRIGGER IF NOT EXISTS agency_hiring_case_human_approval_once "
    "BEFORE UPDATE OF human_approved_by, human_approved_at ON agent_hiring_cases "
    "WHEN (NEW.human_approved_by IS NOT OLD.human_approved_by "
    "OR NEW.human_approved_at IS NOT OLD.human_approved_at) "
    "AND NOT (OLD.status = 'proposed' "
    "AND OLD.human_approval_required = 1 "
    "AND OLD.human_approved_by = '' "
    "AND OLD.human_approved_at IS NULL "
    "AND NEW.human_approved_by != '' "
    "AND NEW.human_approved_at IS NOT NULL) "
    "BEGIN SELECT RAISE(ABORT, 'agent hiring approval is immutable'); END",
)


def _workforce_invariant_schema_is_current(conn: sqlite3.Connection) -> bool:
    expected = {
        _schema_object_identity(statement): _canonical_schema_sql(statement)
        for statement in _WORKFORCE_INVARIANT_SCHEMA_SQL
    }
    names = tuple(name for _kind, name in expected)
    placeholders = ",".join("?" for _name in names)
    observed = {
        (str(row["type"]), str(row["name"])): _canonical_schema_sql(row["sql"])
        for row in conn.execute(
            f"SELECT type, name, sql FROM sqlite_master WHERE name IN ({placeholders})",  # nosec B608
            names,
        )
    }
    return observed == expected


def create_workforce_invariant_schema(conn: sqlite3.Connection) -> None:
    """Install the exact append-only and hiring-authority schema objects."""

    for kind, name in reversed(
        tuple(_schema_object_identity(statement) for statement in _WORKFORCE_INVARIANT_SCHEMA_SQL)
    ):
        if kind == "trigger":
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
        elif kind == "index":
            conn.execute(f"DROP INDEX IF EXISTS {name}")  # nosec B608
    for statement in _WORKFORCE_INVARIANT_SCHEMA_SQL:
        conn.execute(statement)


def workforce_schema_is_current(conn: sqlite3.Connection) -> bool:
    """Return whether durable workforce structures and active bindings are complete."""

    required_columns = {
        "agent_workers": {
            "worker_id",
            "agent_slug",
            "employment_class",
            "standing",
            "current_agent_version_id",
            "current_version",
            "current_hash",
            "revision",
        },
        "agent_hiring_cases": {
            "idempotency_key",
            "contract_evidence",
            "critic_evidence",
            "model_evidence",
            "contract_hash",
            "risk_tier",
            "human_approval_required",
        },
        "agent_version_lineage": {
            "worker_id",
            "agent_version_id",
            "recruitment_contract",
            "recruitment_contract_hash",
            "hiring_case_id",
        },
        "agent_recruitment_contract_projections": {
            "projection_sequence",
            "worker_id",
            "agent_version_id",
            "parent_contract_hash",
            "recruitment_contract",
            "recruitment_contract_hash",
            "projection_authority",
        },
        "agent_worker_events": {"event_sequence", "worker_id", "event_type", "evidence"},
        "agent_performance_events": {
            "idempotency_key",
            "worker_id",
            "version",
            "version_hash",
            "activation_receipt_id",
            "evidence_hash",
        },
    }
    for table, expected in required_columns.items():
        columns = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})")}
        if not expected.issubset(columns):
            return False
    if not recruitment_contract_projection_history_is_current(conn):
        return False
    if not _workforce_invariant_schema_is_current(conn):
        return False
    mismatch = conn.execute(
        "SELECT 1 FROM agent_active AS active "
        "JOIN agent_versions AS version ON version.agent_slug = active.agent_slug "
        "AND version.version = active.version "
        "LEFT JOIN agent_workers AS worker ON worker.agent_slug = active.agent_slug "
        "WHERE worker.worker_id IS NULL "
        "OR worker.current_agent_version_id != version.id "
        "OR worker.current_version != active.version "
        "OR worker.current_hash != active.hash LIMIT 1"
    ).fetchone()
    return mismatch is None


def _canonical_schema_sql(value: object) -> str:
    """Normalize SQL syntax while preserving quoted literal and identifier bytes."""

    source = str(value or "").strip()
    normalized: list[str] = []
    quote_end = ""
    index = 0
    while index < len(source):
        character = source[index]
        if not quote_end:
            if character.isspace():
                index += 1
                continue
            optional_clause = re.match(
                r"if\s+not\s+exists(?![a-z0-9_])",
                source[index:],
                flags=re.IGNORECASE,
            )
            if optional_clause is not None and (
                index == 0 or not (source[index - 1].isalnum() or source[index - 1] == "_")
            ):
                index += optional_clause.end()
                continue
            if character in {"'", '"', "`", "["}:
                quote_end = "]" if character == "[" else character
                normalized.append(character)
            else:
                normalized.append(character.casefold())
            index += 1
            continue

        normalized.append(character)
        if character == quote_end:
            if index + 1 < len(source) and source[index + 1] == quote_end:
                normalized.append(source[index + 1])
                index += 2
                continue
            quote_end = ""
        index += 1
    return "".join(normalized)


def recruitment_contract_projection_history_is_current(
    conn: sqlite3.Connection,
) -> bool:
    """Return whether the append-only projection ledger permits A-B-A history.

    Contract projections are immutable events, not a set of unique contract
    bodies. A package can legitimately restore an earlier derived projection
    after an intervening release, so content hashes cannot be globally unique
    for one worker revision.
    """

    row = conn.execute(
        "SELECT sql FROM sqlite_master "
        "WHERE type = 'table' AND name = 'agent_recruitment_contract_projections'"
    ).fetchone()
    if row is None:
        return False
    sql = str(row["sql"] if isinstance(row, sqlite3.Row) else row[0])
    legacy_constraint = re.search(
        r"unique\s*\(\s*worker_id\s*,\s*agent_version_id\s*,"
        r"\s*recruitment_contract_hash\s*\)",
        sql,
        flags=re.IGNORECASE,
    )
    return legacy_constraint is None


def migrate_recruitment_contract_projection_history(conn: sqlite3.Connection) -> None:
    """Remove the legacy content-uniqueness constraint without losing history."""

    if recruitment_contract_projection_history_is_current(conn):
        return
    before = int(
        conn.execute("SELECT COUNT(*) FROM agent_recruitment_contract_projections").fetchone()[0]
    )
    conn.execute("DROP TRIGGER IF EXISTS agency_contract_projections_immutable_update")
    conn.execute("DROP TRIGGER IF EXISTS agency_contract_projections_immutable_delete")
    conn.execute("DROP INDEX IF EXISTS idx_agent_contract_projections_worker_sequence")
    conn.execute(
        "ALTER TABLE agent_recruitment_contract_projections "
        "RENAME TO agent_recruitment_contract_projections_legacy_unique"
    )
    conn.execute(
        "CREATE TABLE agent_recruitment_contract_projections ("
        "id TEXT PRIMARY KEY, "
        "projection_sequence INTEGER NOT NULL UNIQUE CHECK (projection_sequence > 0), "
        "worker_id TEXT NOT NULL, "
        "agent_version_id TEXT NOT NULL, "
        "parent_contract_hash TEXT NOT NULL, "
        "recruitment_contract TEXT NOT NULL, "
        "recruitment_contract_hash TEXT NOT NULL, "
        "projection_authority TEXT NOT NULL, "
        "created_at TEXT NOT NULL, "
        "FOREIGN KEY (worker_id) REFERENCES agent_workers(worker_id), "
        "FOREIGN KEY (agent_version_id) REFERENCES agent_versions(id))"
    )
    columns = (
        "id, projection_sequence, worker_id, agent_version_id, "
        "parent_contract_hash, recruitment_contract, recruitment_contract_hash, "
        "projection_authority, created_at"
    )
    conn.execute(
        "INSERT INTO agent_recruitment_contract_projections "
        f"({columns}) SELECT {columns} "
        "FROM agent_recruitment_contract_projections_legacy_unique "
        "ORDER BY projection_sequence"
    )
    after = int(
        conn.execute("SELECT COUNT(*) FROM agent_recruitment_contract_projections").fetchone()[0]
    )
    if after != before:
        raise RuntimeError("agent recruitment projection migration lost history")
    conn.execute("DROP TABLE agent_recruitment_contract_projections_legacy_unique")
    conn.execute(
        "CREATE INDEX idx_agent_contract_projections_worker_sequence "
        "ON agent_recruitment_contract_projections("
        "worker_id, agent_version_id, projection_sequence DESC)"
    )
    conn.execute(
        "CREATE TRIGGER agency_contract_projections_immutable_update "
        "BEFORE UPDATE ON agent_recruitment_contract_projections BEGIN "
        "SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END"
    )
    conn.execute(
        "CREATE TRIGGER agency_contract_projections_immutable_delete "
        "BEFORE DELETE ON agent_recruitment_contract_projections BEGIN "
        "SELECT RAISE(ABORT, 'agent recruitment contract projections are immutable'); END"
    )


def _bounded_utf8_text(value: object, maximum: int) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return None
    return value if 0 < size <= maximum else None


def _aware_timestamp(value: object, maximum: int = 128) -> datetime | None:
    text = _bounded_utf8_text(value, maximum)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(f"{text[:-1]}+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _remediation_resolution_detail(
    value: object,
    *,
    queue_event_id: str,
) -> dict[str, Any] | None:
    text = _bounded_utf8_text(value, _MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES)
    if text is None:
        return None
    try:
        loaded = safe_load_bounded_json(
            text,
            maximum_bytes=_MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES,
            maximum_depth=4,
            maximum_nodes=128,
        )
    except (TypeError, ValueError):
        return None
    expected = {
        "audit_id",
        "audit_revision",
        "candidate_download_id",
        "candidate_hash",
        "candidate_id",
        "download_id",
        "original_hash",
        "origin",
        "policy_hash",
        "queue_event_id",
        "relative_path",
        "resolution",
        "scan_id",
        "source_hash",
        "source_id",
    }
    if not isinstance(loaded, dict) or set(loaded) != expected:
        return None
    for field in (
        "audit_id",
        "candidate_download_id",
        "candidate_id",
        "download_id",
        "queue_event_id",
        "scan_id",
        "source_id",
    ):
        if _bounded_utf8_text(loaded[field], _MAX_REMEDIATION_AUTHORITY_ID_BYTES) is None:
            return None
    for field in ("origin", "relative_path"):
        if (
            _bounded_utf8_text(loaded[field], _MAX_REMEDIATION_AUTHORITY_DEPENDENCY_ID_BYTES)
            is None
        ):
            return None
    if loaded["queue_event_id"] != queue_event_id:
        return None
    if loaded["resolution"] not in {"remediated_candidate", "superseded_by_candidate"}:
        return None
    if (
        not isinstance(loaded["audit_revision"], str)
        or re.fullmatch(r"sha256:[a-f0-9]{64}", loaded["audit_revision"]) is None
    ):
        return None
    if any(
        not isinstance(loaded[field], str) or re.fullmatch(r"[a-f0-9]{64}", loaded[field]) is None
        for field in ("candidate_hash", "original_hash", "policy_hash", "source_hash")
    ):
        return None
    return loaded


def _normalized_authority_dependencies(value: object) -> list[dict[str, str]] | None:
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= _MAX_REMEDIATION_AUTHORITY_DEPENDENCIES
    ):
        return None
    dependencies: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"kind", "id", "hash"}:
            return None
        kind = item["kind"]
        dependency_id = item["id"]
        dependency_hash = item["hash"]
        if (
            kind not in REMEDIATION_AUTHORITY_DEPENDENCY_KINDS
            or _bounded_utf8_text(
                dependency_id,
                _MAX_REMEDIATION_AUTHORITY_DEPENDENCY_ID_BYTES,
            )
            is None
            or not isinstance(dependency_hash, str)
            or re.fullmatch(r"[a-f0-9]{64}", dependency_hash) is None
        ):
            return None
        dependencies.append({"hash": dependency_hash, "id": dependency_id, "kind": kind})
    ordered = sorted(dependencies, key=lambda item: (item["kind"], item["id"]))
    if ordered != dependencies or len({(item["kind"], item["id"]) for item in ordered}) != len(
        ordered
    ):
        return None
    return dependencies


def _authority_dependency_closure_is_valid(
    dependencies: list[dict[str, str]],
    *,
    resolution_event_id: str | None,
    queue_event_id: str | None,
    resolution: str | None,
    agent_slug: str | None,
) -> bool:
    by_kind: dict[str, list[str]] = {}
    for item in dependencies:
        by_kind.setdefault(item["kind"], []).append(item["id"])
    if resolution_event_id is not None and by_kind.get("resolution_event") != [resolution_event_id]:
        return False
    if queue_event_id is not None and by_kind.get("queue_event") != [queue_event_id]:
        return False
    required_singletons = (
        "queue_download",
        "candidate_download",
        "candidate",
        "source",
        "queue_source_scan",
        "candidate_source_scan",
        "candidate_audit",
    )
    if any(len(by_kind.get(kind, ())) != 1 for kind in required_singletons):
        return False
    transformation_kinds = ("source_download", "transformation_event", "candidate_slug")
    if any(len(by_kind.get(kind, ())) > 1 for kind in transformation_kinds):
        return False
    transformation_presence = [bool(by_kind.get(kind)) for kind in transformation_kinds]
    if any(transformation_presence) and not all(transformation_presence):
        return False
    if resolution == "remediated_candidate" and not all(transformation_presence):
        return False
    return not (
        agent_slug is not None
        and any(slug != agent_slug for slug in by_kind.get("candidate_slug", ()))
    )


def _parsed_remediation_authority_receipt(
    value: object,
    *,
    resolution_event_id: str | None = None,
    queue_event_id: str | None = None,
    resolution: str | None = None,
    agent_slug: str | None = None,
) -> tuple[dict[str, str], ...] | None:
    text = _bounded_utf8_text(value, _MAX_REMEDIATION_AUTHORITY_RECEIPT_BYTES)
    if text is None:
        return None
    try:
        loaded = safe_load_bounded_json(
            text,
            maximum_bytes=_MAX_REMEDIATION_AUTHORITY_RECEIPT_BYTES,
            maximum_depth=5,
            maximum_nodes=4 * _MAX_REMEDIATION_AUTHORITY_DEPENDENCIES + 8,
        )
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(loaded, dict)
        or set(loaded) != {"schema", "validator_revision", "dependencies"}
        or loaded["schema"] != REMEDIATION_AUTHORITY_EVIDENCE_SCHEMA
        or loaded["validator_revision"] != REMEDIATION_AUTHORITY_VALIDATOR_REVISION
    ):
        return None
    dependencies = _normalized_authority_dependencies(loaded["dependencies"])
    if dependencies is None:
        return None
    try:
        canonical = json.dumps(
            loaded,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return None
    if canonical != text:
        return None
    if not _authority_dependency_closure_is_valid(
        dependencies,
        resolution_event_id=resolution_event_id,
        queue_event_id=queue_event_id,
        resolution=resolution,
        agent_slug=agent_slug,
    ):
        return None
    return tuple(dependencies)


def canonical_remediation_authority_receipt(
    dependencies: list[dict[str, str]] | tuple[dict[str, str], ...],
) -> str:
    """Return one bounded canonical v31 dependency-closure receipt."""

    loaded = {
        "dependencies": [
            {"hash": item["hash"], "id": item["id"], "kind": item["kind"]}
            for item in sorted(dependencies, key=lambda item: (item["kind"], item["id"]))
        ],
        "schema": REMEDIATION_AUTHORITY_EVIDENCE_SCHEMA,
        "validator_revision": REMEDIATION_AUTHORITY_VALIDATOR_REVISION,
    }
    receipt = json.dumps(
        loaded,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if _parsed_remediation_authority_receipt(receipt) is None:
        raise ValueError("remediation authority dependencies are invalid")
    return receipt


def _remediation_authority_hmac(
    secret: object,
    *,
    resolution_event_id: object,
    queue_event_id: object,
    event_detail: object,
    evidence_receipt: object,
    dependency_count: object,
    validated_at: object,
) -> str:
    if not isinstance(secret, bytes) or len(secret) != 32:
        return ""
    if isinstance(dependency_count, bool) or not isinstance(dependency_count, int):
        return ""
    values = (
        resolution_event_id,
        queue_event_id,
        event_detail,
        evidence_receipt,
        str(dependency_count),
        validated_at,
    )
    if not all(isinstance(value, str) for value in values):
        return ""
    try:
        fields = tuple(value.encode("utf-8") for value in values)
    except UnicodeEncodeError:
        return ""
    limits = (
        _MAX_REMEDIATION_AUTHORITY_ID_BYTES,
        _MAX_REMEDIATION_AUTHORITY_ID_BYTES,
        _MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES,
        _MAX_REMEDIATION_AUTHORITY_RECEIPT_BYTES,
        8,
        128,
    )
    if any(not 0 < len(field) <= maximum for field, maximum in zip(fields, limits, strict=True)):
        return ""
    payload = bytearray(b"agency-remediation-authority-v2\x00")
    for field in fields:
        payload.extend(len(field).to_bytes(8, "big"))
        payload.extend(field)
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify_remediation_authority(
    secret: object,
    resolution_event_id: object,
    queue_event_id: object,
    event_detail: object,
    evidence_receipt: object,
    dependency_count: object,
    validated_at: object,
    authority_hmac: object,
    queue_created_at: object,
    resolution_created_at: object,
    agent_slug: object,
) -> int:
    """Return one only when a current, bounded authority receipt verifies."""

    resolution_id = _bounded_utf8_text(
        resolution_event_id,
        _MAX_REMEDIATION_AUTHORITY_ID_BYTES,
    )
    queue_id = _bounded_utf8_text(queue_event_id, _MAX_REMEDIATION_AUTHORITY_ID_BYTES)
    slug = _bounded_utf8_text(agent_slug, _MAX_REMEDIATION_AUTHORITY_ID_BYTES)
    detail = (
        _remediation_resolution_detail(event_detail, queue_event_id=queue_id)
        if queue_id is not None
        else None
    )
    authority_validated_at = _aware_timestamp(validated_at)
    if (
        resolution_id is None
        or queue_id is None
        or slug is None
        or detail is None
        or isinstance(dependency_count, bool)
        or not isinstance(dependency_count, int)
        or not 1 <= dependency_count <= _MAX_REMEDIATION_AUTHORITY_DEPENDENCIES
        or authority_validated_at is None
    ):
        return 0
    queued_at = _aware_timestamp(queue_created_at, _MAX_REMEDIATION_AUTHORITY_ID_BYTES)
    resolved_at = _aware_timestamp(
        resolution_created_at,
        _MAX_REMEDIATION_AUTHORITY_ID_BYTES,
    )
    dependencies = _parsed_remediation_authority_receipt(
        evidence_receipt,
        resolution_event_id=resolution_id,
        queue_event_id=queue_id,
        resolution=str(detail["resolution"]),
        agent_slug=slug,
    )
    if (
        queued_at is None
        or resolved_at is None
        or queued_at > resolved_at
        or resolved_at > authority_validated_at
        or dependencies is None
        or len(dependencies) != dependency_count
        or not isinstance(authority_hmac, str)
        or re.fullmatch(r"[a-f0-9]{64}", authority_hmac) is None
    ):
        return 0
    expected = _remediation_authority_hmac(
        secret,
        resolution_event_id=resolution_id,
        queue_event_id=queue_id,
        event_detail=event_detail,
        evidence_receipt=evidence_receipt,
        dependency_count=dependency_count,
        validated_at=validated_at,
    )
    return int(bool(expected) and hmac.compare_digest(expected, authority_hmac))


def remediation_authority_material_from_connection(
    conn: sqlite3.Connection,
    *,
    resolution_event_id: str,
    queue_event_id: str,
    event_detail: str,
    dependencies: list[dict[str, str]] | tuple[dict[str, str], ...],
    validated_at: str,
    queue_created_at: str,
    resolution_created_at: str,
    agent_slug: str,
) -> tuple[str, int, str]:
    """Sign closure material only after its caller completes full DB validation."""

    evidence_receipt = canonical_remediation_authority_receipt(dependencies)
    dependency_count = len(dependencies)
    row = conn.execute(
        "SELECT secret, typeof(secret) AS secret_type FROM store_secrets WHERE name = ?",
        (REMEDIATION_AUTHORITY_KEY_NAME,),
    ).fetchone()
    if (
        row is None
        or row["secret_type"] != "blob"
        or not isinstance(row["secret"], bytes)
        or len(row["secret"]) != 32
    ):
        raise RuntimeError("remediation resolution authority key is unavailable")
    signature = _remediation_authority_hmac(
        row["secret"],
        resolution_event_id=resolution_event_id,
        queue_event_id=queue_event_id,
        event_detail=event_detail,
        evidence_receipt=evidence_receipt,
        dependency_count=dependency_count,
        validated_at=validated_at,
    )
    if (
        verify_remediation_authority(
            row["secret"],
            resolution_event_id,
            queue_event_id,
            event_detail,
            evidence_receipt,
            dependency_count,
            validated_at,
            signature,
            queue_created_at,
            resolution_created_at,
            agent_slug,
        )
        != 1
    ):
        raise ValueError("remediation resolution authority material is invalid")
    return evidence_receipt, dependency_count, signature


def remediation_receipt_has_dependency(
    evidence_receipt: object,
    dependency_kind: object,
    dependency_id: object,
    dependency_hash: object,
) -> int:
    dependencies = _parsed_remediation_authority_receipt(evidence_receipt)
    if dependencies is None:
        return 0
    return int(
        {
            "kind": dependency_kind,
            "id": dependency_id,
            "hash": dependency_hash,
        }
        in dependencies
    )


def remediation_scan_id(event_detail: object) -> str:
    text = _bounded_utf8_text(event_detail, _MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES)
    if text is None:
        return ""
    try:
        loaded = safe_load_bounded_json(
            text,
            maximum_bytes=_MAX_REMEDIATION_AUTHORITY_DETAIL_BYTES,
            maximum_depth=5,
            maximum_nodes=256,
        )
    except (TypeError, ValueError):
        return ""
    if not isinstance(loaded, dict):
        return ""
    return (
        _bounded_utf8_text(
            loaded.get("scan_id"),
            _MAX_REMEDIATION_AUTHORITY_ID_BYTES,
        )
        or ""
    )


def ensure_remediation_authority_key_integrity(
    conn: sqlite3.Connection,
    *,
    allow_initialize: bool,
) -> None:
    """Require one stable private HMAC key before authority can be trusted."""

    row = conn.execute(
        "SELECT secret, typeof(secret) AS secret_type FROM store_secrets WHERE name = ?",
        (REMEDIATION_AUTHORITY_KEY_NAME,),
    ).fetchone()
    if row is None:
        authority_exists = conn.execute(
            "SELECT 1 FROM agent_remediation_resolution_authority LIMIT 1"
        ).fetchone()
        if not allow_initialize or authority_exists is not None:
            raise RuntimeError("remediation resolution authority key is unavailable")
        conn.execute(
            "INSERT INTO store_secrets (name, secret, created_at) VALUES (?, randomblob(32), "
            f"{STORE_CLOCK_SQL})",  # nosec B608
            (REMEDIATION_AUTHORITY_KEY_NAME,),
        )
        return
    if row["secret_type"] != "blob" or not isinstance(row["secret"], bytes):
        raise RuntimeError("remediation resolution authority key is invalid")
    if len(row["secret"]) != 32:
        raise RuntimeError("remediation resolution authority key is invalid")


def agent_import_event_sequence_schema_is_current(conn: sqlite3.Connection) -> bool:
    columns = {
        str(row["name"]): row for row in conn.execute("PRAGMA table_info(agent_import_events)")
    }
    column = columns.get("event_sequence")
    if (
        column is None
        or str(column["type"]).casefold() != "integer"
        or int(column["notnull"]) != 1
        or str(column["dflt_value"]) not in {"0", "'0'", '"0"'}
    ):
        return False
    sql_values = (
        _AGENT_IMPORT_EVENT_SEQUENCE_INDEX_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_INSERT_GUARD_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_ALLOCATE_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_UPDATE_GUARD_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_INSERT_GUARD_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_UPDATE_GUARD_SQL,
        _AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_DELETE_GUARD_SQL,
    )
    expected = {_schema_object_identity(sql): _canonical_schema_sql(sql) for sql in sql_values}
    names = tuple(name for _kind, name in expected)
    placeholders = ",".join("?" for _name in names)
    actual = {
        (str(row["type"]), str(row["name"])): _canonical_schema_sql(row["sql"])
        for row in conn.execute(
            f"SELECT type, name, sql FROM sqlite_master WHERE name IN ({placeholders})",  # nosec B608
            names,
        )
    }
    if actual != expected:
        return False
    invalid = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE typeof(event_sequence) != 'integer' OR event_sequence <= 0 LIMIT 1"
    ).fetchone()
    duplicate = conn.execute(
        "SELECT 1 FROM agent_import_events GROUP BY event_sequence HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    counter = conn.execute(
        "SELECT value, typeof(value) AS value_type FROM store_counters "
        "WHERE name = 'agent-import-event-sequence'"
    ).fetchone()
    maximum = int(
        conn.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) AS maximum FROM agent_import_events"
        ).fetchone()["maximum"]
    )
    return (
        invalid is None
        and duplicate is None
        and counter is not None
        and counter["value_type"] == "integer"
        and int(counter["value"]) >= maximum
        and int(counter["value"]) < 9223372036854775807
    )


def create_agent_import_event_sequence_schema(
    conn: sqlite3.Connection,
    *,
    allow_backfill: bool,
) -> None:
    """Install immutable monotonic import-event identity, backfilling by old rowid."""

    ensure_column(
        conn,
        "agent_import_events",
        "event_sequence",
        "INTEGER NOT NULL DEFAULT 0 "
        "CHECK (typeof(event_sequence) = 'integer' AND event_sequence >= 0)",
    )
    if not allow_backfill and agent_import_event_sequence_schema_is_current(conn):
        return
    authority_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' "
        "AND name = 'agent_remediation_resolution_authority'"
    ).fetchone()
    if not allow_backfill and authority_table is not None:
        conn.execute("DELETE FROM agent_remediation_resolution_authority")
    for name in (
        "trg_agent_import_event_sequence_insert_guard",
        "trg_agent_import_event_sequence_allocate",
        "trg_agent_import_event_sequence_update_guard",
        "trg_agent_import_event_sequence_counter_insert",
        "trg_agent_import_event_sequence_counter_update",
        "trg_agent_import_event_sequence_counter_delete",
    ):
        conn.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
    conn.execute("DROP INDEX IF EXISTS idx_agent_import_event_sequence")
    if allow_backfill:
        conn.execute(
            "WITH ordered AS (SELECT id, ROW_NUMBER() OVER (ORDER BY rowid) AS sequence "
            "FROM agent_import_events) UPDATE agent_import_events "
            "SET event_sequence = (SELECT sequence FROM ordered "
            "WHERE ordered.id = agent_import_events.id)"
        )
    invalid = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE typeof(event_sequence) != 'integer' OR event_sequence <= 0 LIMIT 1"
    ).fetchone()
    duplicate = conn.execute(
        "SELECT 1 FROM agent_import_events GROUP BY event_sequence HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if invalid is not None or duplicate is not None:
        raise RuntimeError("agent import event sequence integrity is invalid")
    maximum = int(
        conn.execute(
            "SELECT COALESCE(MAX(event_sequence), 0) AS maximum FROM agent_import_events"
        ).fetchone()["maximum"]
    )
    if maximum >= 9223372036854775807:
        raise RuntimeError("agent import event sequence is exhausted")
    if allow_backfill:
        conn.execute(
            "INSERT INTO store_counters (name, value) VALUES "
            "('agent-import-event-sequence', ?) "
            "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            (maximum,),
        )
    else:
        counter = conn.execute(
            "SELECT value, typeof(value) AS value_type FROM store_counters "
            "WHERE name = 'agent-import-event-sequence'"
        ).fetchone()
        if (
            counter is None
            or counter["value_type"] != "integer"
            or not maximum <= int(counter["value"]) < 9223372036854775807
        ):
            raise RuntimeError("agent import event sequence counter integrity is invalid")
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_INDEX_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_INSERT_GUARD_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_ALLOCATE_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_UPDATE_GUARD_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_INSERT_GUARD_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_UPDATE_GUARD_SQL)
    conn.execute(_AGENT_IMPORT_EVENT_SEQUENCE_COUNTER_DELETE_GUARD_SQL)
    if not agent_import_event_sequence_schema_is_current(conn):
        raise RuntimeError("agent import event sequence schema repair failed")


def remediation_indexes_are_current(conn: sqlite3.Connection) -> bool:
    """Return whether remediation identity and provenance lookups are indexed."""

    expected_sql = (
        _REMEDIATION_RESOLUTION_INDEX_SQL,
        _REMEDIATION_QUEUE_IDENTITY_INDEX_SQL,
        _REMEDIATION_CANDIDATE_PROVENANCE_INDEX_SQL,
        _REMEDIATION_SCAN_PROVENANCE_INDEX_SQL,
    )
    expected = {_schema_object_identity(sql)[1]: _canonical_schema_sql(sql) for sql in expected_sql}
    names = tuple(expected)
    placeholders = ",".join("?" for _name in names)
    rows = {
        str(row["name"]): _canonical_schema_sql(row["sql"])
        for row in conn.execute(
            f"SELECT name, sql FROM sqlite_master WHERE type = 'index' "
            f"AND name IN ({placeholders})",  # nosec B608
            names,
        )
    }
    return rows == expected


def create_remediation_indexes(conn: sqlite3.Connection) -> None:
    """Install canonical remediation identity and provenance indexes."""

    for sql in (
        _REMEDIATION_RESOLUTION_INDEX_SQL,
        _REMEDIATION_QUEUE_IDENTITY_INDEX_SQL,
        _REMEDIATION_CANDIDATE_PROVENANCE_INDEX_SQL,
        _REMEDIATION_SCAN_PROVENANCE_INDEX_SQL,
    ):
        _kind, name = _schema_object_identity(sql)
        conn.execute(f"DROP INDEX IF EXISTS {name}")  # nosec B608
        conn.execute(sql)


def _schema_object_identity(sql: str) -> tuple[str, str]:
    match = re.match(
        r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX|TRIGGER)\s+IF\s+NOT\s+EXISTS\s+([a-z0-9_]+)",
        sql,
        re.IGNORECASE,
    )
    if match is None:
        raise RuntimeError("canonical remediation authority schema object is invalid")
    return match.group(1).casefold(), match.group(2)


def _remediation_authority_schema_objects() -> dict[tuple[str, str], str]:
    sql_values = (
        _REMEDIATION_AUTHORITY_TABLE_SQL,
        _REMEDIATION_AUTHORITY_DEPENDENCY_TABLE_SQL,
        _REMEDIATION_AUTHORITY_VALIDATED_INDEX_SQL,
        _REMEDIATION_AUTHORITY_DEPENDENCY_INDEX_SQL,
        _REMEDIATION_AUTHORITY_INSERT_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_PROJECTION_UPDATE_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_PROJECTION_DELETE_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_DEPENDENCY_INSERT_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_DEPENDENCY_UPDATE_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_KEY_INSERT_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_KEY_UPDATE_TRIGGER_SQL,
        _REMEDIATION_AUTHORITY_KEY_DELETE_TRIGGER_SQL,
        *_REMEDIATION_AUTHORITY_INVALIDATION_TRIGGER_SQLS,
    )
    return {_schema_object_identity(sql): _canonical_schema_sql(sql) for sql in sql_values}


def remediation_authority_schema_is_current(conn: sqlite3.Connection) -> bool:
    """Return whether durable resolution authority has its exact fail-closed schema."""

    expected = _remediation_authority_schema_objects()
    names = tuple(name for _kind, name in expected)
    placeholders = ",".join("?" for _name in names)
    rows = {
        (str(row["type"]), str(row["name"])): _canonical_schema_sql(row["sql"])
        for row in conn.execute(
            f"SELECT type, name, sql FROM sqlite_master WHERE name IN ({placeholders})",  # nosec B608
            names,
        )
    }
    return rows == expected


def _drop_remediation_authority_schema(conn: sqlite3.Connection) -> None:
    expected = _remediation_authority_schema_objects()
    legacy_names = (
        "trg_agent_remediation_authority_event_update",
        "trg_agent_remediation_authority_event_delete",
    )
    for kind, name in reversed(tuple(expected)):
        if kind == "trigger":
            conn.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
        elif kind == "index":
            conn.execute(f"DROP INDEX IF EXISTS {name}")  # nosec B608
    for name in legacy_names:
        conn.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
    conn.execute("DROP TABLE IF EXISTS agent_remediation_resolution_dependencies")
    conn.execute("DROP TABLE IF EXISTS agent_remediation_resolution_authority")


def create_remediation_authority_schema(
    conn: sqlite3.Connection,
    *,
    allow_rebuild: bool = False,
) -> None:
    """Create/repair v31 authority schema, clearing trust before any repair."""

    expected = _remediation_authority_schema_objects()
    tables = {
        str(row["name"]): _canonical_schema_sql(row["sql"])
        for row in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name IN "
            "('agent_remediation_resolution_authority', "
            "'agent_remediation_resolution_dependencies')"
        )
    }
    expected_tables = {name: sql for (kind, name), sql in expected.items() if kind == "table"}
    if allow_rebuild:
        if "agent_remediation_resolution_dependencies" in tables:
            conn.execute("DELETE FROM agent_remediation_resolution_dependencies")
        if "agent_remediation_resolution_authority" in tables:
            conn.execute("DELETE FROM agent_remediation_resolution_authority")
    table_mismatch = any(
        name in tables and tables[name] != sql for name, sql in expected_tables.items()
    )
    if table_mismatch and not allow_rebuild:
        raise RuntimeError("remediation resolution authority table schema is invalid")
    if table_mismatch:
        _drop_remediation_authority_schema(conn)
        tables = {}
    if "agent_remediation_resolution_authority" not in tables:
        conn.execute(_REMEDIATION_AUTHORITY_TABLE_SQL)
    if "agent_remediation_resolution_dependencies" not in tables:
        conn.execute(_REMEDIATION_AUTHORITY_DEPENDENCY_TABLE_SQL)

    if not remediation_authority_schema_is_current(conn):
        conn.execute("DELETE FROM agent_remediation_resolution_authority")
        for kind, name in reversed(tuple(expected)):
            if kind == "trigger":
                conn.execute(f"DROP TRIGGER IF EXISTS {name}")  # nosec B608
            elif kind == "index":
                conn.execute(f"DROP INDEX IF EXISTS {name}")  # nosec B608
        for sql in (
            _REMEDIATION_AUTHORITY_VALIDATED_INDEX_SQL,
            _REMEDIATION_AUTHORITY_DEPENDENCY_INDEX_SQL,
            _REMEDIATION_AUTHORITY_INSERT_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_PROJECTION_UPDATE_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_PROJECTION_DELETE_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_DEPENDENCY_INSERT_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_DEPENDENCY_UPDATE_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_KEY_INSERT_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_KEY_UPDATE_TRIGGER_SQL,
            _REMEDIATION_AUTHORITY_KEY_DELETE_TRIGGER_SQL,
            *_REMEDIATION_AUTHORITY_INVALIDATION_TRIGGER_SQLS,
        ):
            conn.execute(sql)
    if not remediation_authority_schema_is_current(conn):
        raise RuntimeError("remediation resolution authority schema repair failed")


_ROSTER_TABLES: tuple[str, ...] = (
    "agent_sources",
    "agent_downloads",
    "agent_candidates",
    "agent_candidate_audits",
    "agent_candidate_audit_findings",
    "agent_candidate_status_events",
    "agent_versions",
    "agent_source_scans",
    "agent_source_scan_entries",
    "agent_categories",
    "agent_embeddings",
    "agent_snapshots",
    "agent_active",
    "agent_retirements",
    "agent_import_events",
    "agent_remediation_resolution_dependencies",
    "agent_remediation_resolution_authority",
)
_LEGACY_SOURCE_PROVENANCE_COLUMNS: tuple[tuple[str, str], ...] = (("agent_sources", "name"),)
_LEGACY_SOURCE_REDACTION_COLLISION_LIMIT = 1_024
_LEGACY_SOURCE_TAINT_CLOSURE_LIMIT = 1_024

_DOWNLOAD_TAINT_COLUMNS = ("slug", "hash", "content", "status")
_CANDIDATE_TAINT_COLUMNS = (
    "slug",
    "name",
    "description",
    "division",
    "categories",
    "capabilities",
    "tool_affinity",
    "prompt_path",
    "source",
    "source_version",
    "version",
    "hash",
    "status",
)
_AUDIT_TAINT_COLUMNS = (
    "audit_revision",
    "policy_hash",
    "candidate_version",
    "candidate_hash",
    "active_basis_hash",
    "provider",
    "inference_evidence",
)
_FINDING_TAINT_COLUMNS = ("code", "message", "evidence_hash")
_STATUS_EVENT_TAINT_COLUMNS = (
    "event_type",
    "from_status",
    "to_status",
    "reason",
    "audit_id",
)
_SOURCE_SCAN_TAINT_COLUMNS = ("status", "manifest_hash")
_SOURCE_SCAN_ENTRY_TAINT_COLUMNS = (
    "relative_path",
    "slug",
    "content_hash",
    "status",
)
_ACTIVE_SEMANTIC_TAINT_COLUMNS = (
    "agent_slug",
    "name",
    "division",
    "description",
    "source",
    "source_id",
    "source_version",
    "version",
    "hash",
    "categories",
    "capabilities",
    "tool_affinity",
    "prompt_path",
)
_IMPORT_EVENT_TAINT_COLUMNS = ("event_type", "agent_slug", "detail")


def _legacy_source_needles(raw_source: str) -> tuple[str, ...]:
    unicode_escaped = json.dumps(raw_source, ensure_ascii=False)[1:-1]
    ascii_escaped = json.dumps(raw_source, ensure_ascii=True)[1:-1]
    variants = (raw_source, unicode_escaped, ascii_escaped)
    slash_escaped = tuple(value.replace("/", "\\/") for value in variants)
    return tuple(value for value in dict.fromkeys((*variants, *slash_escaped)) if value)


def _legacy_source_search_text(value: object) -> str:
    """Return only a detectable text projection for legacy taint matching."""

    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return ""
    return str(value or "")


def _legacy_source_predicate(column: str, needle_count: int) -> str:
    if needle_count == 0:
        return "0"
    return " OR ".join(f"INSTR(COALESCE({column}, ''), ?) > 0" for _ in range(needle_count))


def _legacy_source_columns_predicate(
    alias: str,
    columns: tuple[str, ...],
    needles: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    prefix = f"{alias}." if alias else ""
    predicate = " OR ".join(
        _legacy_source_predicate(f"{prefix}{column}", len(needles)) for column in columns
    )
    parameters = tuple(needle for _column in columns for needle in needles)
    return predicate, parameters


def _replace_legacy_source_references(
    conn: sqlite3.Connection,
    *,
    table: str,
    column: str,
    needles: tuple[str, ...],
    replacement: str,
) -> None:
    for needle in needles:
        if not needle or needle == replacement:
            continue
        conn.execute(
            f"UPDATE {table} SET {column} = REPLACE({column}, ?, ?) "
            f"WHERE INSTR(COALESCE({column}, ''), ?) > 0",  # nosec B608
            (needle, replacement, needle),
        )


def _allocate_legacy_source_identity(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    base_identity: str,
) -> str:
    for collision in range(_LEGACY_SOURCE_REDACTION_COLLISION_LIMIT):
        identity = base_identity if collision == 0 else f"{base_identity}-{collision}"
        existing = conn.execute(
            "SELECT id FROM agent_sources WHERE url = ?",
            (identity,),
        ).fetchone()
        if existing is None or str(existing["id"]) == source_id:
            return identity
    raise RuntimeError("legacy source redaction identity space is exhausted")


def _tombstone_legacy_source_behavior(
    conn: sqlite3.Connection,
    *,
    source_id: str,
    needles: tuple[str, ...],
    include_source_records: bool,
) -> tuple[int, int, int]:
    temp_tables = {
        "agency_tainted_source_downloads": "(id TEXT PRIMARY KEY)",
        "agency_tainted_source_candidates": (
            "(id TEXT PRIMARY KEY, download_id TEXT NOT NULL, slug TEXT NOT NULL, "
            "version TEXT NOT NULL, hash TEXT NOT NULL)"
        ),
        "agency_tainted_source_scans": "(id TEXT PRIMARY KEY)",
        "agency_tainted_source_versions": (
            "(id TEXT PRIMARY KEY, agent_slug TEXT NOT NULL, version TEXT NOT NULL)"
        ),
        "agency_tainted_source_snapshots": ("(id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL)"),
        "agency_tainted_source_events": "(id TEXT PRIMARY KEY)",
        "agency_tainted_source_active": ("(agent_slug TEXT PRIMARY KEY, version TEXT NOT NULL)"),
    }
    for table, columns in temp_tables.items():
        conn.execute(
            f"CREATE TEMP TABLE IF NOT EXISTS {table} {columns} WITHOUT ROWID"  # nosec B608
        )
        conn.execute(f"DELETE FROM {table}")  # nosec B608

    download_predicate, download_parameters = _legacy_source_columns_predicate(
        "download",
        _DOWNLOAD_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_downloads (id) "
        "SELECT download.id FROM agent_downloads AS download "
        f"WHERE (? AND download.source_id = ?) OR ({download_predicate})",  # nosec B608
        (1 if include_source_records else 0, source_id, *download_parameters),
    )

    candidate_predicate, candidate_parameters = _legacy_source_columns_predicate(
        "candidate",
        _CANDIDATE_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_candidates "
        "(id, download_id, slug, version, hash) "
        "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
        "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
        "FROM agent_candidates AS candidate "
        f"WHERE {candidate_predicate}",  # nosec B608
        candidate_parameters,
    )
    audit_predicate, audit_parameters = _legacy_source_columns_predicate(
        "audit",
        _AUDIT_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_candidates "
        "(id, download_id, slug, version, hash) "
        "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
        "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
        "FROM agent_candidates AS candidate JOIN agent_candidate_audits AS audit "
        "ON audit.candidate_id = candidate.id "
        f"WHERE {audit_predicate}",  # nosec B608
        audit_parameters,
    )
    finding_predicate, finding_parameters = _legacy_source_columns_predicate(
        "finding",
        _FINDING_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_candidates "
        "(id, download_id, slug, version, hash) "
        "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
        "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
        "FROM agent_candidates AS candidate JOIN agent_candidate_audits AS audit "
        "ON audit.candidate_id = candidate.id "
        "JOIN agent_candidate_audit_findings AS finding ON finding.audit_id = audit.id "
        f"WHERE {finding_predicate}",  # nosec B608
        finding_parameters,
    )
    status_predicate, status_parameters = _legacy_source_columns_predicate(
        "status_event",
        _STATUS_EVENT_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_candidates "
        "(id, download_id, slug, version, hash) "
        "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
        "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
        "FROM agent_candidates AS candidate "
        "JOIN agent_candidate_status_events AS status_event "
        "ON status_event.candidate_id = candidate.id "
        f"WHERE {status_predicate}",  # nosec B608
        status_parameters,
    )

    scan_predicate, scan_parameters = _legacy_source_columns_predicate(
        "scan",
        _SOURCE_SCAN_TAINT_COLUMNS,
        needles,
    )
    entry_predicate, entry_parameters = _legacy_source_columns_predicate(
        "entry",
        _SOURCE_SCAN_ENTRY_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_scans (id) "
        "SELECT scan.id FROM agent_source_scans AS scan "
        "WHERE (? AND scan.source_id = ?) "
        f"OR ({scan_predicate}) OR EXISTS ("  # nosec B608
        "SELECT 1 FROM agent_source_scan_entries AS entry WHERE entry.scan_id = scan.id "
        f"AND ({entry_predicate}))",  # nosec B608
        (
            1 if include_source_records else 0,
            source_id,
            *scan_parameters,
            *entry_parameters,
        ),
    )

    for _iteration in range(_LEGACY_SOURCE_TAINT_CLOSURE_LIMIT):
        before = tuple(
            int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # nosec B608
            for table in (
                "agency_tainted_source_downloads",
                "agency_tainted_source_candidates",
                "agency_tainted_source_scans",
            )
        )
        conn.execute(
            "INSERT OR IGNORE INTO agency_tainted_source_candidates "
            "(id, download_id, slug, version, hash) "
            "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
            "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
            "FROM agent_candidates AS candidate WHERE candidate.download_id IN "
            "(SELECT id FROM agency_tainted_source_downloads)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO agency_tainted_source_scans (id) "
            "SELECT DISTINCT entry.scan_id FROM agent_source_scan_entries AS entry "
            "WHERE entry.candidate_id IN "
            "(SELECT id FROM agency_tainted_source_candidates)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO agency_tainted_source_candidates "
            "(id, download_id, slug, version, hash) "
            "SELECT candidate.id, COALESCE(candidate.download_id, ''), candidate.slug, "
            "COALESCE(candidate.version, ''), COALESCE(candidate.hash, '') "
            "FROM agent_candidates AS candidate "
            "JOIN agent_source_scan_entries AS entry ON entry.candidate_id = candidate.id "
            "WHERE entry.scan_id IN (SELECT id FROM agency_tainted_source_scans)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO agency_tainted_source_downloads (id) "
            "SELECT DISTINCT download_id FROM agency_tainted_source_candidates "
            "WHERE download_id <> ''"
        )
        after = tuple(
            int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])  # nosec B608
            for table in (
                "agency_tainted_source_downloads",
                "agency_tainted_source_candidates",
                "agency_tainted_source_scans",
            )
        )
        if after == before:
            break
    else:
        raise RuntimeError("legacy source taint closure did not converge")

    version_predicate, version_parameters = _legacy_source_columns_predicate(
        "version",
        ("agent_slug", "version", "source_version", "source_id", "hash", "content", "metadata"),
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_versions (id, agent_slug, version) "
        "SELECT version.id, version.agent_slug, version.version "
        "FROM agent_versions AS version "
        f"WHERE (? AND version.source_id = ?) OR ({version_predicate})",  # nosec B608
        (1 if include_source_records else 0, source_id, *version_parameters),
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_versions (id, agent_slug, version) "
        "SELECT version.id, version.agent_slug, version.version "
        "FROM agent_versions AS version "
        "JOIN agency_tainted_source_candidates AS candidate "
        "ON candidate.slug = version.agent_slug AND candidate.version = version.version"
    )

    active_predicate, active_parameters = _legacy_source_columns_predicate(
        "active",
        _ACTIVE_SEMANTIC_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_active (agent_slug, version) "
        "SELECT active.agent_slug, COALESCE(active.version, '') "
        "FROM agent_active AS active "
        f"WHERE (? AND active.source_id = ?) OR ({active_predicate}) OR EXISTS ("  # nosec B608
        "SELECT 1 FROM agent_categories AS category "
        "WHERE category.agent_slug = active.agent_slug AND "
        f"({_legacy_source_predicate('category.category', len(needles))}))",  # nosec B608
        (1 if include_source_records else 0, source_id, *active_parameters, *needles),
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_active (agent_slug, version) "
        "SELECT active.agent_slug, COALESCE(active.version, '') "
        "FROM agent_active AS active "
        "JOIN agency_tainted_source_versions AS version "
        "ON version.agent_slug = active.agent_slug AND version.version = active.version"
    )

    snapshot_predicate, snapshot_parameters = _legacy_source_columns_predicate(
        "snapshot",
        ("snapshot_id", "manifest"),
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_snapshots (id, snapshot_id) "
        "SELECT snapshot.id, snapshot.snapshot_id FROM agent_snapshots AS snapshot "
        f"WHERE {snapshot_predicate} OR EXISTS ("  # nosec B608
        "SELECT 1 FROM agency_tainted_source_candidates AS candidate "
        "WHERE INSTR(COALESCE(snapshot.manifest, ''), candidate.id) > 0)",
        snapshot_parameters,
    )
    candidate_count = int(
        conn.execute("SELECT COUNT(*) FROM agency_tainted_source_candidates").fetchone()[0]
    )
    version_count = int(
        conn.execute("SELECT COUNT(*) FROM agency_tainted_source_versions").fetchone()[0]
    )
    snapshot_count = int(
        conn.execute("SELECT COUNT(*) FROM agency_tainted_source_snapshots").fetchone()[0]
    )

    event_predicate, event_parameters = _legacy_source_columns_predicate(
        "event",
        _IMPORT_EVENT_TAINT_COLUMNS,
        needles,
    )
    conn.execute(
        "INSERT OR IGNORE INTO agency_tainted_source_events (id) "
        "SELECT event.id FROM agent_import_events AS event "
        f"WHERE {event_predicate} OR (json_valid(event.detail) AND ("  # nosec B608
        "(? AND json_extract(event.detail, '$.source_id') = ?) OR EXISTS ("
        "SELECT 1 FROM agency_tainted_source_downloads AS download WHERE "
        "download.id = json_extract(event.detail, '$.download_id') OR "
        "download.id = json_extract(event.detail, '$.candidate_download_id') OR "
        "download.id = json_extract(event.detail, '$.source_download_id')) OR EXISTS ("
        "SELECT 1 FROM agency_tainted_source_candidates AS candidate WHERE "
        "candidate.id = json_extract(event.detail, '$.candidate_id')) OR EXISTS ("
        "SELECT 1 FROM agency_tainted_source_scans AS scan WHERE "
        "scan.id = json_extract(event.detail, '$.scan_id') OR "
        "scan.id = json_extract(event.detail, '$.source_scan_id') OR "
        "scan.id = json_extract(event.detail, '$.candidate_scan_id')) OR EXISTS ("
        "SELECT 1 FROM agency_tainted_source_snapshots AS snapshot WHERE "
        "snapshot.snapshot_id = json_extract(event.detail, '$.snapshot_id')))) "
        "OR EXISTS (SELECT 1 FROM agency_tainted_source_candidates AS candidate "
        "WHERE candidate.slug = event.agent_slug)",
        (*event_parameters, 1 if include_source_records else 0, source_id),
    )
    for _iteration in range(_LEGACY_SOURCE_TAINT_CLOSURE_LIMIT):
        before = int(
            conn.execute("SELECT COUNT(*) FROM agency_tainted_source_events").fetchone()[0]
        )
        conn.execute(
            "INSERT OR IGNORE INTO agency_tainted_source_events (id) "
            "SELECT event.id FROM agent_import_events AS event "
            "WHERE json_valid(event.detail) AND EXISTS ("
            "SELECT 1 FROM agency_tainted_source_events AS captured "
            "WHERE captured.id = json_extract(event.detail, '$.queue_event_id'))"
        )
        after = int(conn.execute("SELECT COUNT(*) FROM agency_tainted_source_events").fetchone()[0])
        if after == before:
            break
    else:
        raise RuntimeError("legacy source event taint closure did not converge")

    retirement_predicate, retirement_parameters = _legacy_source_columns_predicate(
        "retirement",
        ("agent_slug", "version", "hash", "active_record"),
        needles,
    )
    conn.execute(
        "DELETE FROM agent_retirements AS retirement "
        "WHERE (? AND retirement.source_id = ?) "
        "OR retirement.source_scan_id IN (SELECT id FROM agency_tainted_source_scans) "
        f"OR ({retirement_predicate})",  # nosec B608
        (1 if include_source_records else 0, source_id, *retirement_parameters),
    )
    conn.execute(
        "DELETE FROM agent_snapshots WHERE id IN (SELECT id FROM agency_tainted_source_snapshots)"
    )
    authority_predicate, authority_parameters = _legacy_source_columns_predicate(
        "authority",
        (
            "resolution_event_id",
            "queue_event_id",
            "evidence_receipt",
            "authority_hmac",
            "validated_at",
        ),
        needles,
    )
    conn.execute(
        "DELETE FROM agent_remediation_resolution_authority AS authority "
        "WHERE authority.resolution_event_id IN "
        "(SELECT id FROM agency_tainted_source_events) "
        "OR authority.queue_event_id IN "
        "(SELECT id FROM agency_tainted_source_events) "
        f"OR ({authority_predicate})",  # nosec B608
        authority_parameters,
    )
    conn.execute(
        "DELETE FROM agent_import_events WHERE id IN (SELECT id FROM agency_tainted_source_events)"
    )
    conn.execute(
        "DELETE FROM agent_source_scan_entries WHERE scan_id IN "
        "(SELECT id FROM agency_tainted_source_scans)"
    )
    conn.execute(
        "DELETE FROM agent_source_scans WHERE id IN (SELECT id FROM agency_tainted_source_scans)"
    )
    conn.execute(
        "DELETE FROM agent_candidate_audit_findings WHERE audit_id IN ("
        "SELECT audit.id FROM agent_candidate_audits AS audit "
        "WHERE audit.candidate_id IN "
        "(SELECT id FROM agency_tainted_source_candidates))"
    )
    conn.execute(
        "DELETE FROM agent_candidate_audits WHERE candidate_id IN "
        "(SELECT id FROM agency_tainted_source_candidates)"
    )
    conn.execute(
        "DELETE FROM agent_candidate_status_events WHERE candidate_id IN "
        "(SELECT id FROM agency_tainted_source_candidates)"
    )
    conn.execute(
        "DELETE FROM agent_candidates WHERE id IN (SELECT id FROM agency_tainted_source_candidates)"
    )
    conn.execute(
        "DELETE FROM agent_downloads WHERE id IN (SELECT id FROM agency_tainted_source_downloads)"
    )
    from agency_runtime.core.store.workforce import retire_ingested_workforce_worker

    for tainted in conn.execute(
        "SELECT agent_slug FROM agency_tainted_source_active ORDER BY agent_slug"
    ).fetchall():
        retire_ingested_workforce_worker(
            conn,
            agent_slug=str(tainted["agent_slug"]),
            reason="source privacy redaction removed the governed prompt revision",
        )
    conn.execute(
        "DELETE FROM agent_active WHERE agent_slug IN "
        "(SELECT agent_slug FROM agency_tainted_source_active)"
    )
    conn.execute(
        "DELETE FROM agent_versions WHERE id IN (SELECT id FROM agency_tainted_source_versions)"
    )
    category_predicate = _legacy_source_predicate("category", len(needles))
    conn.execute(
        "DELETE FROM agent_categories WHERE agent_slug IN "
        "(SELECT agent_slug FROM agency_tainted_source_active) "
        "OR (agent_slug IN ("
        "SELECT slug FROM agency_tainted_source_candidates "
        "UNION SELECT agent_slug FROM agency_tainted_source_versions"
        ") AND NOT EXISTS ("
        "SELECT 1 FROM agent_active AS surviving "
        "WHERE surviving.agent_slug = agent_categories.agent_slug)) "
        f"OR {category_predicate}",  # nosec B608
        needles,
    )
    embedding_predicate, embedding_parameters = _legacy_source_columns_predicate(
        "embedding",
        ("agent_slug", "embedding", "model"),
        needles,
    )
    conn.execute(
        "DELETE FROM agent_embeddings AS embedding WHERE embedding.agent_slug IN "
        "(SELECT agent_slug FROM agency_tainted_source_active) "
        "OR (embedding.agent_slug IN ("
        "SELECT slug FROM agency_tainted_source_candidates "
        "UNION SELECT agent_slug FROM agency_tainted_source_versions"
        ") AND NOT EXISTS ("
        "SELECT 1 FROM agent_active AS surviving "
        "WHERE surviving.agent_slug = embedding.agent_slug)) "
        f"OR {embedding_predicate}",  # nosec B608
        embedding_parameters,
    )
    return candidate_count, version_count, snapshot_count


def _assert_legacy_source_removed(
    conn: sqlite3.Connection,
    *,
    needles: tuple[str, ...],
) -> None:
    for table in _ROSTER_TABLES:
        text_columns = tuple(
            str(row["name"])
            for row in conn.execute(f"PRAGMA table_info({table})")  # nosec B608
            if "TEXT" in str(row["type"] or "").upper()
        )
        predicate, parameters = _legacy_source_columns_predicate(
            "",
            text_columns,
            needles,
        )
        if (
            predicate
            and conn.execute(
                f"SELECT 1 FROM {table} WHERE {predicate} LIMIT 1",  # nosec B608
                parameters,
            ).fetchone()
            is not None
        ):
            raise RuntimeError(f"legacy source credential redaction was incomplete in {table}")
    if (
        conn.execute(
            "SELECT 1 FROM agent_active AS active LEFT JOIN agent_versions AS version "
            "ON version.agent_slug = active.agent_slug AND version.version = active.version "
            "WHERE version.id IS NULL LIMIT 1"
        ).fetchone()
        is not None
    ):
        raise RuntimeError("legacy source redaction left an invalid active roster reference")
    if (
        conn.execute(
            "SELECT 1 FROM agent_candidates AS candidate LEFT JOIN agent_downloads AS download "
            "ON download.id = candidate.download_id WHERE download.id IS NULL LIMIT 1"
        ).fetchone()
        is not None
    ):
        raise RuntimeError("legacy source redaction left an invalid candidate reference")
    _assert_active_roster_projection_integrity(conn)


def _assert_active_roster_projection_integrity(conn: sqlite3.Connection) -> None:
    """Verify surviving active rows still project their immutable revisions."""

    rows = conn.execute(
        "SELECT active.*, version.hash AS immutable_hash, "
        "version.source_id AS immutable_source_id, "
        "version.source_version AS immutable_source_version, "
        "version.metadata AS immutable_metadata "
        "FROM agent_active AS active JOIN agent_versions AS version "
        "ON version.agent_slug = active.agent_slug AND version.version = active.version"
    ).fetchall()
    for row in rows:
        if str(row["hash"] or "") != str(row["immutable_hash"] or ""):
            raise RuntimeError("active roster hash does not match its immutable revision")
        if str(row["source_id"] or "") != str(row["immutable_source_id"] or ""):
            raise RuntimeError("active roster source does not match its immutable revision")
        if str(row["source_version"] or "") != str(row["immutable_source_version"] or ""):
            raise RuntimeError(
                "active roster source revision does not match its immutable revision"
            )
        metadata = decode_revision_metadata(row["immutable_metadata"])
        if metadata is None:
            continue
        if str(row["source_version"] or "") != str(metadata["source_version"] or ""):
            raise RuntimeError("active roster projection does not match its immutable revision")
        for field in ("name", "division", "description", "source", "prompt_path"):
            if str(row[field] or "") != str(metadata[field] or ""):
                raise RuntimeError("active roster projection does not match its immutable revision")
        for field in ("categories", "capabilities", "tool_affinity"):
            try:
                projected = safe_load_bounded_json(
                    row[field] or "[]",
                    maximum_bytes=1024 * 1024,
                    maximum_depth=4,
                    maximum_nodes=10_000,
                )
            except (TypeError, ValueError):
                projected = None
            if projected != metadata[field]:
                raise RuntimeError("active roster projection does not match its immutable revision")


def source_redaction_purge_pending(conn: sqlite3.Connection) -> bool:
    """Read and validate the crash-consistent physical-purge marker."""

    row = conn.execute(
        "SELECT value, typeof(value) AS value_type FROM store_counters "
        "WHERE name = 'source-redaction-purge-pending'"
    ).fetchone()
    if row is None or row["value_type"] != "integer" or int(row["value"]) not in (0, 1):
        raise RuntimeError("source redaction purge state is invalid")
    return int(row["value"]) == 1


def validate_stored_source_identities(conn: sqlite3.Connection) -> None:
    """Fail closed when any current source row is not display-safe."""

    rows = conn.execute(
        "SELECT url, name, enabled FROM agent_sources ORDER BY id LIMIT ?",
        (MAX_DURABLE_SOURCE_COUNT + 1,),
    ).fetchall()
    if len(rows) > MAX_DURABLE_SOURCE_COUNT:
        raise RuntimeError("stored roster source count is invalid")
    for row in rows:
        try:
            stored_url = row["url"]
            stored_name = row["name"]
            enabled = row["enabled"]
            if not isinstance(enabled, int) or enabled not in (0, 1):
                raise SourceIdentityError("source enabled state is invalid")
            if not enabled and is_legacy_source_redaction_identity(stored_url):
                source_identity = stored_url
            else:
                source_identity = canonical_source_identity(stored_url)
            source_name = canonical_source_display_name(
                stored_name,
                source_identity=source_identity,
                source_input=stored_url,
            )
            if source_identity != stored_url or source_name != stored_name:
                raise SourceIdentityError("source identity is not canonical")
        except SourceIdentityError:
            raise RuntimeError("stored roster source identity is invalid") from None


def _migrate_legacy_source_url(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    now: Callable[[], str],
) -> tuple[bool, tuple[str, ...] | None]:
    source_id = str(row["id"])
    raw_source_value = row["url"]
    raw_source = _legacy_source_search_text(raw_source_value)
    redaction = legacy_source_redaction(raw_source_value, source_id=source_id)
    if redaction is None:
        return False, None
    identity = _allocate_legacy_source_identity(
        conn,
        source_id=source_id,
        base_identity=redaction.identity,
    )
    counts = (0, 0, 0)
    needles = _legacy_source_needles(raw_source)
    if redaction.purge_references:
        counts = _tombstone_legacy_source_behavior(
            conn,
            source_id=source_id,
            needles=needles,
            include_source_records=True,
        )
        for table, column in _LEGACY_SOURCE_PROVENANCE_COLUMNS:
            _replace_legacy_source_references(
                conn,
                table=table,
                column=column,
                needles=needles,
                replacement=identity,
            )
    conn.execute(
        "UPDATE agent_sources SET url = ?, name = ?, enabled = 0, "
        "trusted_for_auto_approve = 0 WHERE id = ?",
        (identity, "Legacy source redacted (disabled)", source_id),
    )
    evidence_key = identity.rsplit("/", 1)[-1]
    event_type = (
        "legacy_source_credentials_redacted"
        if redaction.purge_references
        else "legacy_source_identity_disabled"
    )
    conn.execute(
        "INSERT OR IGNORE INTO agent_import_events "
        "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, '', ?, ?)",
        (
            f"migration:source-redaction:{evidence_key}",
            event_type,
            f"reason={redaction.reason};identity={identity};"
            f"candidates_tombstoned={counts[0]};"
            f"versions_tombstoned={counts[1]};"
            f"snapshots_tombstoned={counts[2]}",
            now(),
        ),
    )
    return redaction.purge_references, needles if redaction.purge_references else None


def _migrate_legacy_source_name(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    now: Callable[[], str],
) -> tuple[bool, tuple[str, ...] | None]:
    source_id = str(row["id"])
    raw_source_value = row["url"]
    raw_name_value = row["name"]
    raw_name = _legacy_source_search_text(raw_name_value)
    url_redaction = legacy_source_redaction(raw_source_value, source_id=source_id)
    if raw_name_value in (None, ""):
        if url_redaction is None:
            current_url = str(
                conn.execute(
                    "SELECT url FROM agent_sources WHERE id = ?",
                    (source_id,),
                ).fetchone()["url"]
            )
            conn.execute(
                "UPDATE agent_sources SET name = ? WHERE id = ?",
                (current_url, source_id),
            )
        return False, None
    if raw_name_value == raw_source_value:
        return False, None
    redaction = legacy_source_name_redaction(raw_name_value, source_id=source_id)
    if redaction is None:
        if url_redaction is not None:
            return False, None
        try:
            current_url = str(
                conn.execute(
                    "SELECT url FROM agent_sources WHERE id = ?",
                    (source_id,),
                ).fetchone()["url"]
            )
            normalized_name = canonical_source_display_name(
                raw_name,
                source_identity=canonical_source_identity(current_url),
                source_input=None,
            )
        except SourceIdentityError:
            raise RuntimeError("legacy source name validation was inconsistent") from None
        if normalized_name != raw_name:
            conn.execute(
                "UPDATE agent_sources SET name = ? WHERE id = ?",
                (normalized_name, source_id),
            )
        return False, None

    counts = (0, 0, 0)
    needles = _legacy_source_needles(raw_name)
    if redaction.purge_references:
        counts = _tombstone_legacy_source_behavior(
            conn,
            source_id=source_id,
            needles=needles,
            include_source_records=False,
        )
        for table, column in _LEGACY_SOURCE_PROVENANCE_COLUMNS:
            _replace_legacy_source_references(
                conn,
                table=table,
                column=column,
                needles=needles,
                replacement=redaction.identity,
            )
    conn.execute(
        "UPDATE agent_sources SET name = ?, enabled = 0, trusted_for_auto_approve = 0 WHERE id = ?",
        ("Legacy source name redacted (disabled)", source_id),
    )
    evidence_key = redaction.identity.rsplit("/", 1)[-1]
    conn.execute(
        "INSERT OR IGNORE INTO agent_import_events "
        "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, '', ?, ?)",
        (
            f"migration:source-name-redaction:{evidence_key}",
            "legacy_source_name_redacted",
            f"reason={redaction.reason};identity={redaction.identity};"
            f"candidates_tombstoned={counts[0]};"
            f"versions_tombstoned={counts[1]};"
            f"snapshots_tombstoned={counts[2]}",
            now(),
        ),
    )
    return redaction.purge_references, needles if redaction.purge_references else None


def migrate_legacy_source_credentials(
    conn: sqlite3.Connection,
    *,
    now: Callable[[], str],
) -> bool:
    """Disable and redact unsafe durable source URLs without rewriting prompts."""

    purge_pending = source_redaction_purge_pending(conn)

    source_count = int(conn.execute("SELECT COUNT(*) FROM agent_sources").fetchone()[0])
    if source_count > MAX_DURABLE_SOURCE_COUNT:
        raise RuntimeError(f"legacy roster source count exceeds {MAX_DURABLE_SOURCE_COUNT}")
    rows = conn.execute("SELECT id, url, name FROM agent_sources").fetchall()
    ordered = sorted(
        rows,
        key=lambda row: (
            -len(_legacy_source_search_text(row["url"])),
            str(row["id"]),
        ),
    )
    sensitive_needles: list[tuple[str, ...]] = []
    for row in ordered:
        purged, needles = _migrate_legacy_source_url(conn, row, now=now)
        purge_pending = purge_pending or purged
        if needles is not None:
            sensitive_needles.append(needles)
    for row in ordered:
        purged, needles = _migrate_legacy_source_name(conn, row, now=now)
        purge_pending = purge_pending or purged
        if needles is not None:
            sensitive_needles.append(needles)
    if purge_pending:
        conn.execute(
            "UPDATE store_counters SET value = 1 WHERE name = 'source-redaction-purge-pending'"
        )
    for needles in sensitive_needles:
        _assert_legacy_source_removed(conn, needles=needles)
    return purge_pending


def ensure_migration_correlation_key_integrity(
    conn: sqlite3.Connection,
    *,
    current_version: int,
) -> None:
    """Initialize key state only when no retired barrier could depend on it."""

    key = conn.execute(
        "SELECT 1 FROM store_secrets WHERE name = 'retired-trace-hmac-v1'"
    ).fetchone()
    if key is None:
        retired = conn.execute("SELECT 1 FROM trace_tombstones LIMIT 1").fetchone()
        if retired is not None:
            raise RuntimeError("retired-trace integrity key is unavailable for legacy tombstones")
        conn.execute(
            "INSERT INTO store_secrets (name, secret, created_at) "
            "VALUES ('retired-trace-hmac-v1', randomblob(32), "
            f"{STORE_CLOCK_SQL})"  # nosec B608
        )
    ensure_correlation_key_integrity(
        conn,
        allow_initialize=current_version < SCHEMA_VERSION,
    )


def retired_barrier_integrity_error(conn: sqlite3.Connection) -> str | None:
    """Return the first content-free tombstone/sequence integrity violation."""

    invalid = conn.execute(
        "SELECT 1 FROM trace_tombstones WHERE trace_digest IS NULL "
        "OR length(trace_digest) <> 64 OR trace_digest GLOB '*[^0-9a-f]*' "
        "OR session_digest IS NULL OR length(session_digest) <> 64 "
        "OR session_digest GLOB '*[^0-9a-f]*' "
        "OR typeof(turn_sequence) <> 'integer' OR turn_sequence <= 0 "
        "OR retired_at IS NULL OR retired_at = '' LIMIT 1"
    ).fetchone()
    if invalid is not None:
        return "retired-trace barrier integrity is invalid"
    duplicate = conn.execute(
        "SELECT 1 FROM (SELECT turn_sequence FROM runs UNION ALL "
        "SELECT turn_sequence FROM trace_tombstones) GROUP BY turn_sequence "
        "HAVING COUNT(*) > 1 LIMIT 1"
    ).fetchone()
    if duplicate is not None:
        return "turn sequence uniqueness is invalid"
    return None


def migrate_trace_tombstone_identity(conn: sqlite3.Connection) -> None:
    """Backfill the v17 session/sequence barrier without losing v16 tombstones.

    Schema v16 retained only the trace HMAC and retirement time. Its historical
    rows cannot be attributed to a session after the fact, so they receive the
    domain-separated uncorrelated-session digest. Assigning their monotonic
    sequences after every live run is deliberately conservative: an anonymous
    session cannot recover a response across an older retired barrier, while
    named sessions remain unaffected.
    """

    uncorrelated_session = correlation_digest(conn, "", domain="session")
    conn.execute(
        "UPDATE trace_tombstones SET session_digest = ? WHERE session_digest = ''",
        (uncorrelated_session,),
    )
    counter = conn.execute(
        "SELECT value, typeof(value) AS value_type FROM store_counters WHERE name = 'turn-sequence'"
    ).fetchone()
    if counter["value_type"] != "integer" or int(counter["value"]) < 0:
        raise RuntimeError("legacy turn sequence counter integrity is invalid")
    maximum = int(
        conn.execute(
            "SELECT MAX(sequence) AS sequence FROM ("
            "SELECT MAX(turn_sequence) AS sequence FROM runs "
            "WHERE typeof(turn_sequence) = 'integer' AND turn_sequence > 0 "
            "UNION ALL SELECT MAX(turn_sequence) AS sequence FROM trace_tombstones "
            "WHERE typeof(turn_sequence) = 'integer' AND turn_sequence > 0 "
            "UNION ALL SELECT value AS sequence FROM store_counters "
            "WHERE name = 'turn-sequence')"
        ).fetchone()["sequence"]
        or 0
    )
    conn.execute(
        "WITH pending AS (SELECT trace_digest, ROW_NUMBER() OVER "
        "(ORDER BY retired_at, trace_digest) AS sequence FROM trace_tombstones "
        "WHERE typeof(turn_sequence) <> 'integer' OR turn_sequence <= 0) "
        "UPDATE trace_tombstones SET turn_sequence = ? + "
        "(SELECT sequence FROM pending WHERE pending.trace_digest = "
        "trace_tombstones.trace_digest) WHERE trace_digest IN "
        "(SELECT trace_digest FROM pending)",
        (maximum,),
    )
    integrity_error = retired_barrier_integrity_error(conn)
    if integrity_error is not None:
        raise RuntimeError(f"legacy {integrity_error}")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_trace_tombstones_turn_sequence_unique "
        "ON trace_tombstones(turn_sequence)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_trace_tombstones_session_sequence "
        "ON trace_tombstones(session_digest, turn_sequence DESC)"
    )


def runs_trace_is_unique(conn: sqlite3.Connection) -> bool:
    """Return whether the runs table enforces unique trace identifiers."""

    for index in conn.execute("PRAGMA index_list(runs)").fetchall():
        if not bool(index["unique"]):
            continue
        columns = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                (index["name"],),
            ).fetchall()
        ]
        if columns == ["trace_id"]:
            return True
    return False


def trace_tombstone_turn_sequence_is_unique(conn: sqlite3.Connection) -> bool:
    """Return whether retired turn sequences have a dedicated unique index."""

    for index in conn.execute("PRAGMA index_list(trace_tombstones)").fetchall():
        if not bool(index["unique"]):
            continue
        columns = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                (index["name"],),
            ).fetchall()
        ]
        if columns == ["turn_sequence"]:
            return True
    return False


def migrate_trace_integrity(
    conn: sqlite3.Connection,
    *,
    now: Callable[[], str],
) -> None:
    """Upgrade legacy stores so evidence foreign keys can be enforced."""

    if not runs_trace_is_unique(conn):
        conn.execute("DROP TABLE IF EXISTS runs_v2")
        conn.execute(
            "CREATE TABLE runs_v2 ("
            "id TEXT PRIMARY KEY, trace_id TEXT NOT NULL UNIQUE, session_id TEXT, "
            "host TEXT NOT NULL DEFAULT 'unknown', started_at TEXT NOT NULL, "
            "last_activity_at TEXT NOT NULL DEFAULT '', "
            "evidence_revision INTEGER NOT NULL DEFAULT 0, "
            "turn_sequence INTEGER NOT NULL DEFAULT 0, ended_at TEXT, "
            "status TEXT NOT NULL DEFAULT 'active', user_message TEXT, metadata TEXT, "
            "terminal_finalization_id TEXT, reservation_token TEXT, "
            "preflight_attempt_token TEXT, preflight_state TEXT NOT NULL DEFAULT '', "
            "preflight_lease_expires_at TEXT NOT NULL DEFAULT '', "
            "preflight_request_fingerprint TEXT NOT NULL DEFAULT '', "
            "preflight_request_kind TEXT NOT NULL DEFAULT '', "
            "preflight_result TEXT NOT NULL DEFAULT '')"
        )
        conn.execute(
            "INSERT OR IGNORE INTO runs_v2 "
            "(id, trace_id, session_id, host, started_at, last_activity_at, "
            "evidence_revision, turn_sequence, ended_at, "
            "status, user_message, metadata, terminal_finalization_id, reservation_token, "
            "preflight_attempt_token, preflight_state, preflight_request_fingerprint, "
            "preflight_request_kind, preflight_result, preflight_lease_expires_at) "
            "SELECT id, trace_id, session_id, host, started_at, last_activity_at, "
            "evidence_revision, turn_sequence, ended_at, "
            "status, user_message, metadata, terminal_finalization_id, reservation_token, "
            "preflight_attempt_token, preflight_state, preflight_request_fingerprint, "
            "preflight_request_kind, preflight_result, preflight_lease_expires_at "
            "FROM runs ORDER BY started_at, rowid"
        )
        conn.execute("DROP TABLE runs")
        conn.execute("ALTER TABLE runs_v2 RENAME TO runs")

    for source_table in ("model_receipts", "delegation_events"):
        conn.execute(
            "INSERT OR IGNORE INTO runs "
            "(id, trace_id, session_id, host, started_at, last_activity_at, ended_at, "
            "status, user_message, metadata) "
            f"SELECT lower(hex(randomblob(16))), trace_id, COALESCE(session_id, ''), "  # nosec B608
            f"COALESCE(host, 'unknown'), COALESCE(MIN(started_at), ?), "
            "?, COALESCE(MIN(started_at), ?), "
            "'completed', '', '{\"migrated\":true}' "
            f"FROM {source_table} WHERE trace_id IS NOT NULL GROUP BY trace_id",
            (now(), now(), now()),
        )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_recent ON runs(started_at DESC, id DESC)")


def migrate_private_projections(
    conn: sqlite3.Connection,
    *,
    capture_content: bool,
) -> None:
    """Sanitize legacy content once when upgrading to the private schema."""

    for row in conn.execute("SELECT id, user_message, metadata FROM runs").fetchall():
        try:
            metadata = (
                safe_load_bounded_json(
                    row["metadata"],
                    maximum_bytes=1024 * 1024,
                    maximum_depth=32,
                    maximum_nodes=10_000,
                )
                if row["metadata"]
                else None
            )
        except (TypeError, ValueError):
            metadata = None
        message = (
            redact_sensitive_text(row["user_message"], RUN_CONTENT_LIMIT) if capture_content else ""
        )
        conn.execute(
            "UPDATE runs SET user_message = ?, metadata = ? WHERE id = ?",
            (message, project_run_metadata(metadata), row["id"]),
        )

    for row in conn.execute("SELECT id, api_base FROM model_receipts").fetchall():
        conn.execute(
            "UPDATE model_receipts SET api_base = ? WHERE id = ?",
            (sanitize_api_base(row["api_base"]), row["id"]),
        )

    for row in conn.execute("SELECT id, skip_reason, error FROM delegation_events").fetchall():
        conn.execute(
            "UPDATE delegation_events SET skip_reason = ?, error = ? WHERE id = ?",
            (
                project_delegation_detail(
                    row["skip_reason"],
                    field="skip_reason",
                    capture_content=capture_content,
                ),
                project_delegation_detail(
                    row["error"],
                    field="error",
                    capture_content=capture_content,
                ),
                row["id"],
            ),
        )


def migrate_snapshot_projections(conn: sqlite3.Connection) -> None:
    """Materialize prompt-free snapshot summaries for bounded dashboard reads."""

    for row in conn.execute("SELECT id, manifest FROM agent_snapshots").fetchall():
        summary = project_snapshot_summary(row["manifest"])
        conn.execute(
            "UPDATE agent_snapshots SET approved = ?, added_count = ?, "
            "changed_count = ?, removed_count = ? WHERE id = ?",
            (
                int(bool(summary["approved"])),
                int(summary["added"]),
                int(summary["changed"]),
                int(summary["removed"]),
                row["id"],
            ),
        )


def migrate_delegation_identity(conn: sqlite3.Connection) -> None:
    """Collapse legacy duplicates and enforce one row per traced work unit."""
    duplicate_keys = conn.execute(
        "SELECT trace_id, work_unit_id FROM delegation_events "
        "WHERE work_unit_id IS NOT NULL AND work_unit_id <> '' "
        "GROUP BY trace_id, work_unit_id HAVING COUNT(*) > 1"
    ).fetchall()
    for key in duplicate_keys:
        rows = conn.execute(
            "SELECT rowid, * FROM delegation_events "
            "WHERE trace_id = ? AND work_unit_id = ? "
            "ORDER BY started_at, rowid",
            (key["trace_id"], key["work_unit_id"]),
        ).fetchall()
        canonical = rows[0]

        def rank(row: sqlite3.Row) -> tuple[int, str, int]:
            return (
                _DELEGATION_STATUS_PRIORITY.get(str(row["status"] or ""), 0),
                str(row["completed_at"] or row["started_at"] or ""),
                int(row["rowid"]),
            )

        ranked = sorted(rows, key=rank, reverse=True)
        dominant = ranked[0]
        status = str(dominant["status"] or "suggested")

        def latest_value(
            field: str,
            candidates: tuple[sqlite3.Row, ...] = tuple(ranked),
        ) -> str:
            return next(
                (str(row[field]) for row in candidates if row[field]),
                "",
            )

        completed_at = dominant["completed_at"]
        if status in _TERMINAL_DELEGATION_STATUSES and not completed_at:
            completed_at = dominant["started_at"]
        conn.execute(
            "UPDATE delegation_events SET session_id = ?, host = ?, "
            "recommended_agent = ?, status = ?, backend = ?, skip_reason = ?, "
            "error = ?, completed_at = ? WHERE id = ?",
            (
                latest_value("session_id"),
                latest_value("host") or "unknown",
                latest_value("recommended_agent"),
                status,
                latest_value("backend"),
                latest_value("skip_reason"),
                latest_value("error"),
                completed_at,
                canonical["id"],
            ),
        )
        for duplicate in rows[1:]:
            conn.execute(
                "UPDATE worker_runs SET delegation_event_id = ? WHERE delegation_event_id = ?",
                (canonical["id"], duplicate["id"]),
            )
            conn.execute(
                "DELETE FROM delegation_events WHERE id = ?",
                (duplicate["id"],),
            )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_delegations_trace_work_unit_unique "
        "ON delegation_events(trace_id, work_unit_id) "
        "WHERE work_unit_id IS NOT NULL AND work_unit_id <> ''"
    )


def migrate_specialist_identity(conn: sqlite3.Connection) -> None:
    """Collapse legacy duplicate turn loads and enforce stable identities."""

    duplicate_keys = conn.execute(
        "SELECT session_id, trace_id, agent_slug FROM specialists_loaded "
        "GROUP BY session_id, trace_id, agent_slug HAVING COUNT(*) > 1"
    ).fetchall()
    for key in duplicate_keys:
        rows = conn.execute(
            "SELECT rowid, id, loaded_at, expired_at FROM specialists_loaded "
            "WHERE session_id = ? AND trace_id = ? AND agent_slug = ? "
            "ORDER BY loaded_at, rowid",
            (key["session_id"], key["trace_id"], key["agent_slug"]),
        ).fetchall()
        canonical = rows[0]
        expirations = [str(row["expired_at"]) for row in rows if row["expired_at"]]
        expired_at = None if len(expirations) != len(rows) else max(expirations)
        conn.execute(
            "UPDATE specialists_loaded SET loaded_at = ?, expired_at = ? WHERE id = ?",
            (str(canonical["loaded_at"]), expired_at, canonical["id"]),
        )
        conn.executemany(
            "DELETE FROM specialists_loaded WHERE id = ?",
            [(row["id"],) for row in rows[1:]],
        )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_specialists_turn_agent_unique "
        "ON specialists_loaded(session_id, trace_id, agent_slug)"
    )


def migrate_delegation_activation_unit_identity(conn: sqlite3.Connection) -> None:
    """Scope exact specialist activation uniqueness to one planned work unit."""

    for column, definition in DELEGATION_ACTIVATION_RECEIPT_MIGRATED_COLUMNS:
        ensure_column(conn, "delegation_activation_receipts", column, definition)

    expected = (
        "trace_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
    )
    unique_column_sets = {
        tuple(
            str(column["name"])
            for column in conn.execute(
                f"PRAGMA index_info({row['name']})"  # nosec B608
            )
        )
        for row in conn.execute("PRAGMA index_list(delegation_activation_receipts)")
        if int(row["unique"] or 0) == 1
    }
    if expected in unique_column_sets:
        return

    drop_delegation_activation_invariant_triggers(conn)
    consumption_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' "
        "AND name = 'delegation_activation_consumptions'"
    ).fetchone()
    if consumption_table is not None:
        consumption_count = int(
            conn.execute("SELECT COUNT(*) FROM delegation_activation_consumptions").fetchone()[0]
        )
        if consumption_count:
            raise RuntimeError(
                "cannot rebuild legacy activation grants with consumption receipts present"
            )
        conn.execute("DROP TABLE delegation_activation_consumptions")

    legacy_table = "delegation_activation_receipts_pre_v20"
    conn.execute(f"DROP TABLE IF EXISTS {legacy_table}")  # nosec B608
    conn.execute(
        f"ALTER TABLE delegation_activation_receipts RENAME TO {legacy_table}"  # nosec B608
    )
    conn.execute(
        """
        CREATE TABLE delegation_activation_receipts (
            id TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL UNIQUE,
            grant_id TEXT NOT NULL DEFAULT '',
            grant_payload TEXT NOT NULL DEFAULT '',
            grant_issued_unix INTEGER NOT NULL DEFAULT 0,
            grant_expires_unix INTEGER NOT NULL DEFAULT 0,
            child_host TEXT NOT NULL DEFAULT '',
            grant_origin TEXT NOT NULL DEFAULT 'manual_api'
                CHECK (grant_origin IN ('manual_api', 'native_hook')),
            tool_use_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL,
            trace_id TEXT NOT NULL,
            work_unit_id TEXT NOT NULL,
            specialist_slug TEXT NOT NULL,
            specialist_version TEXT NOT NULL,
            specialist_prompt_hash TEXT NOT NULL,
            worker_kind TEXT NOT NULL,
            worker_id TEXT NOT NULL DEFAULT '',
            native_run_id TEXT NOT NULL DEFAULT '',
            launch_model TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            consumed_at TEXT,
            delegation_event_id TEXT,
            UNIQUE(
                trace_id,
                work_unit_id,
                specialist_slug,
                specialist_version,
                specialist_prompt_hash
            ),
            FOREIGN KEY (trace_id) REFERENCES runs(trace_id),
            FOREIGN KEY (delegation_event_id) REFERENCES delegation_events(id)
        )
        """
    )
    columns = (
        "id, token_hash, grant_id, grant_payload, grant_issued_unix, "
        "grant_expires_unix, child_host, grant_origin, tool_use_id, session_id, "
        "trace_id, work_unit_id, "
        "specialist_slug, specialist_version, specialist_prompt_hash, worker_kind, "
        "worker_id, native_run_id, launch_model, created_at, consumed_at, "
        "delegation_event_id"
    )
    conn.execute(
        f"INSERT INTO delegation_activation_receipts ({columns}) "  # nosec B608
        f"SELECT {columns} FROM {legacy_table}"  # nosec B608
    )
    conn.execute(f"DROP TABLE {legacy_table}")  # nosec B608
    conn.execute(
        "CREATE INDEX idx_activation_receipts_trace "
        "ON delegation_activation_receipts(trace_id, created_at)"
    )
    conn.execute(
        "CREATE INDEX idx_activation_receipts_work_unit "
        "ON delegation_activation_receipts(trace_id, work_unit_id, consumed_at)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX idx_activation_grants_public_id "
        "ON delegation_activation_receipts(grant_id) WHERE grant_id <> ''"
    )
    create_delegation_activation_consumption_schema(conn)


def create_delegation_activation_consumption_schema(conn: sqlite3.Connection) -> None:
    """Create the append-only public child-consumption ledger."""

    conn.execute(DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_activation_consumptions_trace "
        "ON delegation_activation_consumptions(trace_id, consumed_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_activation_consumptions_work_unit "
        "ON delegation_activation_consumptions(trace_id, work_unit_id, consumed_at)"
    )


def migrate_delegation_activation_consumption_host_domain(
    conn: sqlite3.Connection,
) -> None:
    """Add every canonical native-child host without discarding receipts."""

    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' "
        "AND name = 'delegation_activation_consumptions'"
    ).fetchone()
    if row is None:
        create_delegation_activation_consumption_schema(conn)
        return
    normalized = _canonical_schema_sql(row["sql"])
    if normalized == _canonical_schema_sql(DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL):
        return
    if normalized != _canonical_schema_sql(_LEGACY_DELEGATION_ACTIVATION_CONSUMPTION_TABLE_SQL):
        raise RuntimeError("delegation activation consumption schema is invalid")

    legacy_table = "delegation_activation_consumptions_pre_v36"
    if (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (legacy_table,),
        ).fetchone()
        is not None
    ):
        raise RuntimeError("stale v36 activation-consumption migration table exists")

    drop_delegation_activation_invariant_triggers(conn)
    conn.execute("DROP INDEX IF EXISTS idx_activation_consumptions_trace")
    conn.execute("DROP INDEX IF EXISTS idx_activation_consumptions_work_unit")
    conn.execute(
        "ALTER TABLE delegation_activation_consumptions "
        "RENAME TO delegation_activation_consumptions_pre_v36"
    )
    create_delegation_activation_consumption_schema(conn)
    columns = (
        "id, grant_id, legacy_activation_receipt_id, receipt_payload, session_id, "
        "trace_id, work_unit_id, child_host, specialist_slug, specialist_version, "
        "specialist_prompt_hash, worker_kind, worker_id, native_run_id, consumed_at, "
        "consumed_unix"
    )
    conn.execute(
        f"INSERT INTO delegation_activation_consumptions ({columns}) "  # nosec B608
        f"SELECT {columns} FROM {legacy_table}"  # nosec B608
    )
    conn.execute(f"DROP TABLE {legacy_table}")  # nosec B608


_VALID_ACTIVATION_RECEIPT_SQL = (
    "SELECT 1 FROM delegation_activation_receipts AS grant "
    "LEFT JOIN delegation_activation_consumptions AS consumption "
    "ON consumption.legacy_activation_receipt_id = grant.id "
    "AND consumption.grant_id = grant.grant_id "
    "WHERE grant.id = NEW.activation_receipt_id AND grant.consumed_at IS NOT NULL "
    "AND (grant.grant_id = '' OR consumption.id IS NOT NULL)"
)


def _delegation_activation_invariant_trigger_sql() -> dict[str, str]:
    statements = {
        "agency_activation_grant_provenance_insert_guard": (
            "CREATE TRIGGER agency_activation_grant_provenance_insert_guard "
            "BEFORE INSERT ON delegation_activation_receipts WHEN NOT ("
            "typeof(NEW.grant_origin) = 'text' AND typeof(NEW.tool_use_id) = 'text' "
            "AND ((NEW.grant_origin = 'manual_api' AND NEW.tool_use_id = '') "
            "OR (NEW.grant_origin = 'native_hook' "
            "AND length(CAST(NEW.tool_use_id AS BLOB)) BETWEEN 1 AND 512))) BEGIN "
            "SELECT RAISE(ABORT, 'activation grant provenance is invalid'); END"
        ),
        "agency_activation_grant_provenance_update_guard": (
            "CREATE TRIGGER agency_activation_grant_provenance_update_guard "
            "BEFORE UPDATE OF grant_origin, tool_use_id ON delegation_activation_receipts "
            "WHEN NOT (typeof(NEW.grant_origin) = 'text' "
            "AND typeof(NEW.tool_use_id) = 'text' "
            "AND ((NEW.grant_origin = 'manual_api' AND NEW.tool_use_id = '') "
            "OR (NEW.grant_origin = 'native_hook' "
            "AND length(CAST(NEW.tool_use_id AS BLOB)) BETWEEN 1 AND 512))) BEGIN "
            "SELECT RAISE(ABORT, 'activation grant provenance is invalid'); END"
        ),
        "agency_activation_grant_public_immutable": (
            "CREATE TRIGGER agency_activation_grant_public_immutable "
            "BEFORE UPDATE OF token_hash, grant_id, grant_payload, grant_issued_unix, "
            "grant_expires_unix, child_host, grant_origin, tool_use_id "
            "ON delegation_activation_receipts "
            "WHEN OLD.grant_id <> '' BEGIN "
            "SELECT RAISE(ABORT, 'public activation grant is immutable'); END"
        ),
        "agency_activation_consumption_insert_guard": (
            "CREATE TRIGGER agency_activation_consumption_insert_guard "
            "BEFORE INSERT ON delegation_activation_consumptions WHEN NOT EXISTS ("
            "SELECT 1 FROM delegation_activation_receipts AS grant "
            "WHERE grant.id = NEW.legacy_activation_receipt_id "
            "AND grant.grant_id = NEW.grant_id AND grant.grant_id <> '' "
            "AND grant.session_id = NEW.session_id AND grant.trace_id = NEW.trace_id "
            "AND grant.work_unit_id = NEW.work_unit_id "
            "AND grant.child_host = NEW.child_host "
            "AND grant.specialist_slug = NEW.specialist_slug "
            "AND grant.specialist_version = NEW.specialist_version "
            "AND grant.specialist_prompt_hash = NEW.specialist_prompt_hash "
            "AND grant.worker_kind = NEW.worker_kind AND grant.consumed_at IS NULL "
            "AND NEW.consumed_unix >= grant.grant_issued_unix "
            "AND NEW.consumed_unix <= grant.grant_expires_unix) BEGIN "
            "SELECT RAISE(ABORT, 'activation consumption does not match an active grant'); END"
        ),
        "agency_activation_consumption_immutable_update": (
            "CREATE TRIGGER agency_activation_consumption_immutable_update "
            "BEFORE UPDATE ON delegation_activation_consumptions BEGIN "
            "SELECT RAISE(ABORT, 'activation consumption receipt is immutable'); END"
        ),
        "agency_activation_consumption_guarded_delete": (
            "CREATE TRIGGER agency_activation_consumption_guarded_delete "
            "BEFORE DELETE ON delegation_activation_consumptions WHEN EXISTS ("
            "SELECT 1 FROM delegation_activation_receipts AS grant "
            "WHERE grant.id = OLD.legacy_activation_receipt_id "
            "AND grant.grant_id = OLD.grant_id) BEGIN "
            "SELECT RAISE(ABORT, 'activation consumption receipt is append-only'); END"
        ),
        "agency_activation_consumed_requires_receipt": (
            "CREATE TRIGGER agency_activation_consumed_requires_receipt "
            "BEFORE UPDATE OF consumed_at ON delegation_activation_receipts "
            "WHEN OLD.grant_id <> '' AND OLD.consumed_at IS NULL "
            "AND NEW.consumed_at IS NOT NULL AND NOT EXISTS ("
            "SELECT 1 FROM delegation_activation_consumptions AS consumption "
            "WHERE consumption.legacy_activation_receipt_id = OLD.id "
            "AND consumption.grant_id = OLD.grant_id) BEGIN "
            "SELECT RAISE(ABORT, 'activation evidence requires a consumption receipt'); END"
        ),
    }
    for table, prefix in (
        ("specialists_loaded", "specialist"),
        ("delegation_events", "delegation"),
    ):
        for operation in ("INSERT", "UPDATE OF activation_receipt_id"):
            operation_name = "insert" if operation == "INSERT" else "update"
            name = f"agency_{prefix}_activation_{operation_name}_receipt_guard"
            statements[name] = (
                f"CREATE TRIGGER {name} BEFORE {operation} ON {table} "
                "WHEN NEW.activation_receipt_id IS NOT NULL "
                "AND NEW.activation_receipt_id <> '' "
                f"AND NOT EXISTS ({_VALID_ACTIVATION_RECEIPT_SQL}) BEGIN "
                "SELECT RAISE(ABORT, 'activation evidence requires a valid receipt'); END"
            )
    return statements


DELEGATION_ACTIVATION_INVARIANT_TRIGGER_SQL = _delegation_activation_invariant_trigger_sql()
DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES = tuple(DELEGATION_ACTIVATION_INVARIANT_TRIGGER_SQL)


def drop_delegation_activation_invariant_triggers(conn: sqlite3.Connection) -> None:
    """Remove cross-table guards before rebuilding either activation ledger."""

    for trigger_name in DELEGATION_ACTIVATION_INVARIANT_TRIGGER_NAMES:
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")  # nosec B608


def create_delegation_activation_invariant_triggers(conn: sqlite3.Connection) -> None:
    """Enforce immutable public receipts and evidence-gated projections."""

    drop_delegation_activation_invariant_triggers(conn)
    for statement in DELEGATION_ACTIVATION_INVARIANT_TRIGGER_SQL.values():
        conn.execute(statement)


NATIVE_CHILD_PARENT_SCOPE_TRIGGER_NAME = "agency_native_child_parent_scope_consume_once"
NATIVE_CHILD_PARENT_SCOPE_TRIGGER_SQL = (
    "CREATE TRIGGER agency_native_child_parent_scope_consume_once "
    "BEFORE UPDATE ON native_child_parent_scopes WHEN NOT ("
    "NEW.id IS OLD.id AND NEW.token_hash IS OLD.token_hash "
    "AND NEW.host IS OLD.host "
    "AND NEW.parent_session_id IS OLD.parent_session_id "
    "AND NEW.parent_trace_id IS OLD.parent_trace_id "
    "AND NEW.work_unit_id IS OLD.work_unit_id "
    "AND NEW.worker_kind IS OLD.worker_kind AND NEW.worker_id IS OLD.worker_id "
    "AND NEW.native_run_id IS OLD.native_run_id "
    "AND NEW.child_session_id IS OLD.child_session_id "
    "AND NEW.issued_unix IS OLD.issued_unix "
    "AND NEW.expires_unix IS OLD.expires_unix "
    "AND NEW.created_at IS OLD.created_at AND (("
    "OLD.consumed_at IS NULL AND OLD.consumed_unix IS NULL "
    "AND OLD.child_trace_id = '' AND NEW.consumed_at IS NOT NULL "
    "AND typeof(NEW.consumed_unix) = 'integer' AND NEW.child_trace_id != ''"
    ") OR ("
    "OLD.consumed_at IS NOT NULL AND typeof(OLD.consumed_unix) = 'integer' "
    "AND OLD.child_trace_id != '' AND NEW.consumed_at IS NULL "
    "AND NEW.consumed_unix IS NULL AND NEW.child_trace_id = '' AND ("
    "NOT EXISTS (SELECT 1 FROM runs WHERE session_id = OLD.child_session_id "
    "AND trace_id = OLD.child_trace_id) OR EXISTS (SELECT 1 FROM runs "
    "WHERE session_id = OLD.child_session_id AND trace_id = OLD.child_trace_id "
    "AND status = 'preflight_failed'))"
    "))) BEGIN "
    "SELECT RAISE(ABORT, 'native child parent scope is immutable or consumed'); END"
)


def create_native_child_parent_scope_trigger(conn: sqlite3.Connection) -> None:
    """Allow one success or an exact failed-preflight retry transition."""

    conn.execute(f"DROP TRIGGER IF EXISTS {NATIVE_CHILD_PARENT_SCOPE_TRIGGER_NAME}")
    conn.execute(NATIVE_CHILD_PARENT_SCOPE_TRIGGER_SQL)


def create_native_child_delivery_verification_schema(conn: sqlite3.Connection) -> None:
    """Create the immutable, content-free native child delivery ledger."""

    conn.execute(NATIVE_CHILD_DELIVERY_VERIFICATION_TABLE_SQL)
    conn.execute(
        "DROP TRIGGER IF EXISTS agency_native_child_delivery_verifications_immutable_delete"
    )
    for trigger_name in NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL:
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")  # nosec B608
    for statement in NATIVE_CHILD_DELIVERY_VERIFICATION_TRIGGER_SQL.values():
        conn.execute(statement)


CODEX_NATIVE_PLAN_SCOPE_TRIGGER_SQL: dict[str, str] = {
    "agency_codex_native_plan_scope_insert_guard": (
        "CREATE TRIGGER agency_codex_native_plan_scope_insert_guard "
        "BEFORE INSERT ON codex_native_plan_scopes WHEN NOT EXISTS ("
        "SELECT 1 FROM runs WHERE session_id = NEW.session_id "
        "AND trace_id = NEW.trace_id AND host = 'codex' AND status = 'active' "
        "AND preflight_state = 'ready') BEGIN "
        "SELECT RAISE(ABORT, 'Codex native plan scope requires one ready turn'); END"
    ),
    "agency_codex_native_plan_scope_immutable_update": (
        "CREATE TRIGGER agency_codex_native_plan_scope_immutable_update "
        "BEFORE UPDATE ON codex_native_plan_scopes BEGIN "
        "SELECT RAISE(ABORT, 'Codex native plan scope is immutable'); END"
    ),
    "agency_codex_native_plan_scope_active_delete_guard": (
        "CREATE TRIGGER agency_codex_native_plan_scope_active_delete_guard "
        "BEFORE DELETE ON codex_native_plan_scopes WHEN EXISTS ("
        "SELECT 1 FROM runs WHERE trace_id = OLD.trace_id "
        "AND session_id = OLD.session_id AND status IN ('active', 'evidence_only')) BEGIN "
        "SELECT RAISE(ABORT, 'active Codex native plan scope cannot be deleted'); END"
    ),
    "agency_codex_native_plan_scope_terminal_cleanup": (
        "CREATE TRIGGER agency_codex_native_plan_scope_terminal_cleanup "
        "AFTER UPDATE OF status ON runs WHEN NEW.status NOT IN ('active', 'evidence_only') "
        "BEGIN DELETE FROM codex_native_plan_scopes WHERE trace_id = NEW.trace_id; END"
    ),
}
CODEX_NATIVE_PLAN_SCOPE_TRIGGER_NAMES: tuple[str, ...] = tuple(CODEX_NATIVE_PLAN_SCOPE_TRIGGER_SQL)


def create_codex_native_plan_scope_triggers(conn: sqlite3.Connection) -> None:
    """Keep private Codex plan authority immutable and turn-scoped."""

    for trigger_name in CODEX_NATIVE_PLAN_SCOPE_TRIGGER_NAMES:
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")  # nosec B608
    for statement in CODEX_NATIVE_PLAN_SCOPE_TRIGGER_SQL.values():
        conn.execute(statement)


def _boolean_domain_trigger_sql() -> dict[str, str]:
    statements: dict[str, str] = {}
    for operation in ("INSERT", "UPDATE OF enabled, trusted_for_auto_approve"):
        suffix = "insert" if operation == "INSERT" else "update"
        name = f"agency_agent_sources_boolean_{suffix}_guard"
        statements[name] = (
            f"CREATE TRIGGER {name} BEFORE {operation} ON agent_sources "
            "WHEN NEW.enabled IS NULL OR NEW.enabled NOT IN (0, 1) "
            "OR NEW.trusted_for_auto_approve IS NULL "
            "OR NEW.trusted_for_auto_approve NOT IN (0, 1) BEGIN "
            "SELECT RAISE(ABORT, 'agent source boolean is invalid'); END"
        )
    for operation in ("INSERT", "UPDATE OF activated, approved"):
        suffix = "insert" if operation == "INSERT" else "update"
        name = f"agency_agent_snapshots_boolean_{suffix}_guard"
        statements[name] = (
            f"CREATE TRIGGER {name} BEFORE {operation} ON agent_snapshots "
            "WHEN NEW.activated IS NULL OR NEW.activated NOT IN (0, 1) "
            "OR NEW.approved IS NULL OR NEW.approved NOT IN (0, 1) BEGIN "
            "SELECT RAISE(ABORT, 'agent snapshot boolean is invalid'); END"
        )
    return statements


BOOLEAN_DOMAIN_TRIGGER_SQL = _boolean_domain_trigger_sql()
BOOLEAN_DOMAIN_TRIGGER_NAMES: tuple[str, ...] = tuple(BOOLEAN_DOMAIN_TRIGGER_SQL)


def create_boolean_domain_triggers(conn: sqlite3.Connection) -> None:
    """Enforce legacy boolean domains without a destructive table rewrite."""

    invalid = conn.execute(
        "SELECT 1 FROM agent_sources WHERE enabled IS NULL OR enabled NOT IN (0, 1) "
        "OR trusted_for_auto_approve IS NULL OR trusted_for_auto_approve NOT IN (0, 1) "
        "UNION ALL SELECT 1 FROM agent_snapshots WHERE activated IS NULL "
        "OR activated NOT IN (0, 1) OR approved IS NULL OR approved NOT IN (0, 1) "
        "LIMIT 1"
    ).fetchone()
    if invalid is not None:
        raise RuntimeError("legacy roster boolean domain is invalid")

    for trigger_name in BOOLEAN_DOMAIN_TRIGGER_NAMES:
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")  # nosec B608
    for statement in BOOLEAN_DOMAIN_TRIGGER_SQL.values():
        conn.execute(statement)


def create_activity_triggers(conn: sqlite3.Connection) -> None:
    """Install store-clock activity triggers for every correlated write path."""

    trigger_names = [
        "agency_runs_insert_sequence",
        "agency_runs_insert_sequence_guard",
        "agency_runs_update_sequence_guard",
        "agency_runs_insert_revision",
        "agency_runs_insert_activity",
        "agency_runs_update_activity",
    ]
    correlated_tables = {
        "preflight_failure_receipts": "NEW.trace_id",
        "model_receipts": "NEW.trace_id",
        "skills_loaded": "NEW.trace_id",
        "specialists_loaded": "NEW.trace_id",
        "delegation_activation_receipts": "NEW.trace_id",
        "delegation_activation_consumptions": "NEW.trace_id",
        "delegation_events": "NEW.trace_id",
        "finalization_events": "NEW.trace_id",
        "routing_decisions": "NEW.trace_id",
    }
    for table in correlated_tables:
        trigger_names.extend(
            [
                f"agency_{table}_insert_activity",
                f"agency_{table}_update_activity",
            ]
        )
    trigger_names.extend(
        [
            "agency_worker_runs_insert_activity",
            "agency_worker_runs_update_activity",
        ]
    )
    for trigger_name in trigger_names:
        conn.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")  # nosec B608

    conn.execute(
        "CREATE TRIGGER agency_runs_insert_sequence_guard BEFORE INSERT ON runs "
        "WHEN typeof(NEW.turn_sequence) <> 'integer' OR NEW.turn_sequence < 0 BEGIN "
        "SELECT RAISE(ABORT, 'invalid turn sequence'); END"
    )
    conn.execute(
        "CREATE TRIGGER agency_runs_update_sequence_guard BEFORE UPDATE OF turn_sequence ON runs "
        "WHEN typeof(NEW.turn_sequence) <> 'integer' OR NEW.turn_sequence <= 0 BEGIN "
        "SELECT RAISE(ABORT, 'invalid turn sequence'); END"
    )
    conn.execute(
        "CREATE TRIGGER agency_runs_insert_sequence AFTER INSERT ON runs "
        "WHEN NEW.turn_sequence <= 0 BEGIN "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM store_counters "
        "WHERE name = 'turn-sequence') THEN RAISE(ABORT, 'turn sequence counter unavailable') END; "
        "UPDATE store_counters SET value = MAX(value, "
        "COALESCE((SELECT MAX(turn_sequence) FROM runs WHERE id <> NEW.id), 0), "
        "COALESCE((SELECT MAX(turn_sequence) FROM trace_tombstones), 0)) + 1 "
        "WHERE name = 'turn-sequence'; "
        "UPDATE runs SET turn_sequence = (SELECT value FROM store_counters "
        "WHERE name = 'turn-sequence') WHERE id = NEW.id; END"
    )
    conn.execute(
        "CREATE TRIGGER agency_runs_insert_revision AFTER INSERT ON runs "
        "WHEN NEW.evidence_revision <= 0 BEGIN "
        "UPDATE runs SET evidence_revision = 1 WHERE id = NEW.id; END"
    )
    conn.execute(
        "CREATE TRIGGER agency_runs_insert_activity AFTER INSERT ON runs "
        "WHEN NEW.last_activity_at = '' BEGIN "
        f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
        "WHERE id = NEW.id; END"
    )
    conn.execute(
        "CREATE TRIGGER agency_runs_update_activity AFTER UPDATE OF "
        "session_id, host, started_at, ended_at, status, user_message, metadata, "
        "terminal_finalization_id, reservation_token, preflight_attempt_token, "
        "preflight_state, preflight_request_fingerprint, preflight_request_kind, "
        "preflight_result, preflight_lease_expires_at ON runs "
        "WHEN NEW.status <> 'retention_expired' BEGIN "
        f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL}, "  # nosec B608
        "evidence_revision = evidence_revision + 1 WHERE id = NEW.id; END"
    )
    for table, trace_expression in correlated_tables.items():
        for operation in ("INSERT", "UPDATE"):
            conn.execute(
                f"CREATE TRIGGER agency_{table}_{operation.lower()}_activity "  # nosec B608
                f"AFTER {operation} ON {table} BEGIN "  # nosec B608
                f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL}, "
                "evidence_revision = evidence_revision + 1 "
                f"WHERE trace_id = {trace_expression} "
                "AND status <> 'retention_expired'; END"
            )
    for operation in ("INSERT", "UPDATE"):
        conn.execute(
            f"CREATE TRIGGER agency_worker_runs_{operation.lower()}_activity "  # nosec B608
            f"AFTER {operation} ON worker_runs BEGIN "  # nosec B608
            f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL}, "
            "evidence_revision = evidence_revision + 1 "
            "WHERE trace_id = COALESCE(NULLIF(NEW.trace_id, ''), "
            "(SELECT delegation.trace_id FROM delegation_events AS delegation "
            "WHERE delegation.id = NEW.delegation_event_id)) "
            "AND status <> 'retention_expired'; END"
        )


def migrate_schema(
    conn: sqlite3.Connection,
    *,
    now: Callable[[], str],
    capture_content: Callable[[], bool],
) -> bool:
    """Apply all schema and privacy migrations inside the caller transaction."""

    conn.executescript("BEGIN IMMEDIATE;\n" + SCHEMA_V1)
    version_row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    current_version = int(version_row["version"] or 0)
    ensure_migration_correlation_key_integrity(
        conn,
        current_version=current_version,
    )
    ensure_column(
        conn,
        "trace_tombstones",
        "session_digest",
        "TEXT NOT NULL DEFAULT ''",
    )
    for column, definition in MODEL_RECEIPT_MIGRATED_COLUMNS:
        ensure_column(conn, "model_receipts", column, definition)
    ensure_column(
        conn,
        "trace_tombstones",
        "turn_sequence",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "agent_sources",
        "trusted_for_auto_approve",
        "INTEGER DEFAULT 0",
    )
    ensure_column(
        conn,
        "host_controls",
        "generation",
        "INTEGER NOT NULL DEFAULT 0 CHECK (generation >= 0)",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "profile_scope",
        "TEXT NOT NULL DEFAULT 'current-profile'",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "proof_contract",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "proof_digest",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "host_version",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_snapshots",
        "approved",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "agent_candidates",
        "description",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_candidates",
        "source_version",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_candidate_audits",
        "inference_evidence",
        "TEXT NOT NULL DEFAULT '{}'",
    )
    ensure_column(
        conn,
        "agent_versions",
        "source_version",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_versions",
        "source_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_versions",
        "metadata",
        "TEXT NOT NULL DEFAULT '{}'",
    )
    ensure_column(
        conn,
        "agent_active",
        "source_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_active",
        "source_version",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "agent_snapshots",
        "added_count",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "agent_snapshots",
        "changed_count",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "agent_snapshots",
        "removed_count",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "install_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "host_canary_attestations",
        "bundle_digest",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "skills_loaded", "trace_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "specialists_loaded", "trace_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "specialists_loaded", "expired_at", "TEXT")
    ensure_column(conn, "specialists_loaded", "activation_receipt_id", "TEXT")
    ensure_column(
        conn,
        "resident_manager_bindings",
        "delivery_state",
        "TEXT NOT NULL DEFAULT 'acknowledged'",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "pending_delivery_mode",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "pending_trace_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "pending_restore_generation",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "master_control_generation",
        "INTEGER",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "master_control_materialized",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "host_control_generation",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "resident_manager_bindings",
        "host_control_materialized",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "delegation_events",
        "executed_worker_kind",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_events",
        "executed_worker_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "delegation_events", "native_run_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(
        conn,
        "delegation_events",
        "retrieved_specialist_slug",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_events",
        "retrieved_specialist_version",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_events",
        "retrieved_specialist_prompt_hash",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "delegation_events", "activation_receipt_id", "TEXT")
    ensure_column(conn, "worker_runs", "session_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "worker_runs", "trace_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "worker_runs", "work_unit_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "worker_runs", "host", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "worker_runs", "worker_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "worker_runs", "native_run_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(
        conn,
        "worker_runs",
        "execution_tool_use_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "worker_runs", "execution_dispatched_at", "TEXT")
    ensure_column(
        conn,
        "worker_runs",
        "tool_evidence_schema",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "worker_runs",
        "tool_evidence",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "worker_runs",
        "tool_evidence_source",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "worker_runs", "tool_evidence_recorded_at", "TEXT")
    for column, definition in NATIVE_CHILD_TERMINAL_MIGRATED_COLUMNS:
        ensure_column(conn, "worker_runs", column, definition)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_worker_runs_trace ON worker_runs(session_id, trace_id)"
    )
    conn.execute(NATIVE_WORKER_SCOPE_INDEX_SQL)
    conn.execute(CODEX_EXECUTION_TOOL_USE_INDEX_SQL)
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "grant_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "grant_payload",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "grant_issued_unix",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "grant_expires_unix",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "child_host",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "grant_origin",
        "TEXT NOT NULL DEFAULT 'manual_api' CHECK (grant_origin IN ('manual_api', 'native_hook'))",
    )
    ensure_column(
        conn,
        "delegation_activation_receipts",
        "tool_use_id",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "model_receipts",
        "recorded_at",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "runs", "last_activity_at", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "runs", "evidence_revision", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "runs", "turn_sequence", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "runs", "terminal_finalization_id", "TEXT")
    ensure_column(conn, "runs", "reservation_token", "TEXT")
    ensure_column(conn, "runs", "preflight_attempt_token", "TEXT")
    ensure_column(conn, "runs", "preflight_state", "TEXT NOT NULL DEFAULT ''")
    ensure_column(
        conn,
        "runs",
        "preflight_lease_expires_at",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "runs",
        "preflight_request_fingerprint",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(
        conn,
        "runs",
        "preflight_request_kind",
        "TEXT NOT NULL DEFAULT ''",
    )
    ensure_column(conn, "runs", "preflight_result", "TEXT NOT NULL DEFAULT ''")
    ensure_column(
        conn,
        "preflight_failure_receipts",
        "invariant_code",
        "TEXT NOT NULL DEFAULT '' CHECK (invariant_code IN ('', 'native_plan_scope_invalid'))",
    )
    ensure_column(
        conn,
        "preflight_failure_receipts",
        "staffing_reason_codes",
        "TEXT NOT NULL DEFAULT '[]' CHECK (typeof(staffing_reason_codes) = 'text' "
        "AND length(CAST(staffing_reason_codes AS BLOB)) BETWEEN 2 AND 4096 "
        "AND json_valid(staffing_reason_codes) "
        "AND json_type(staffing_reason_codes) = 'array' "
        "AND json_array_length(staffing_reason_codes) <= 32)",
    )
    ensure_column(
        conn,
        "preflight_failure_receipts",
        "hiring_reason_codes",
        "TEXT NOT NULL DEFAULT '[]' CHECK (typeof(hiring_reason_codes) = 'text' "
        "AND length(CAST(hiring_reason_codes AS BLOB)) BETWEEN 2 AND 4096 "
        "AND json_valid(hiring_reason_codes) "
        "AND json_type(hiring_reason_codes) = 'array' "
        "AND json_array_length(hiring_reason_codes) <= 32)",
    )
    ensure_column(
        conn,
        "preflight_failure_receipts",
        "eligibility_reason_codes",
        "TEXT NOT NULL DEFAULT '[]' CHECK (typeof(eligibility_reason_codes) = 'text' "
        "AND length(CAST(eligibility_reason_codes AS BLOB)) BETWEEN 2 AND 4096 "
        "AND json_valid(eligibility_reason_codes) "
        "AND json_type(eligibility_reason_codes) = 'array' "
        "AND json_array_length(eligibility_reason_codes) <= 32)",
    )
    conn.execute(
        "INSERT OR IGNORE INTO preflight_failure_receipts "
        "(id, session_id, trace_id, host, stage, reason_code, exception_category, "
        "provider_attempts, recorded_at) "
        "SELECT 'migration:preflight-failure:' || id, COALESCE(session_id, ''), "
        "trace_id, host, 'lifecycle', 'preflight_lifecycle_failed', "
        "'unavailable', '[]', COALESCE(ended_at, NULLIF(last_activity_at, ''), started_at) "
        "FROM runs WHERE status = 'preflight_failed'"
    )
    ensure_column(conn, "finalization_events", "response_hash", "TEXT")
    ensure_column(conn, "finalization_events", "policy_response_hash", "TEXT")
    ensure_column(conn, "finalization_events", "terminal_status", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_finalization_trace_response "
        "ON finalization_events(trace_id, action, response_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_finalization_trace_policy_response "
        "ON finalization_events(trace_id, action, policy_response_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_skills_trace_loaded "
        "ON skills_loaded(session_id, trace_id, loaded_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_specialists_active_trace "
        "ON specialists_loaded(session_id, trace_id, expired_at, loaded_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_specialists_recent "
        "ON specialists_loaded(loaded_at DESC, id DESC)"
    )
    migrate_trace_integrity(conn, now=now)
    migration_activity_at = str(
        conn.execute(
            f"SELECT {STORE_CLOCK_SQL} AS recorded_at"  # nosec B608
        ).fetchone()["recorded_at"]
    )
    conn.execute(
        "UPDATE runs SET last_activity_at = ? "
        "WHERE last_activity_at IS NULL OR last_activity_at = ''",
        (migration_activity_at,),
    )
    conn.execute(
        "UPDATE runs SET evidence_revision = 1 "
        "WHERE evidence_revision IS NULL OR evidence_revision <= 0"
    )
    conn.execute(
        "UPDATE model_receipts SET recorded_at = ? WHERE recorded_at IS NULL OR recorded_at = ''",
        (migration_activity_at,),
    )
    conn.execute(
        "WITH ordered AS (SELECT id, ROW_NUMBER() OVER "
        "(ORDER BY started_at, rowid) AS sequence FROM runs) "
        "UPDATE runs SET turn_sequence = "
        "(SELECT sequence FROM ordered WHERE ordered.id = runs.id) "
        "WHERE turn_sequence IS NULL OR turn_sequence <= 0"
    )
    migrate_trace_tombstone_identity(conn)
    conn.execute(
        "UPDATE store_counters SET value = MAX(value, "
        "COALESCE((SELECT MAX(turn_sequence) FROM runs), 0), "
        "COALESCE((SELECT MAX(turn_sequence) FROM trace_tombstones), 0)) "
        "WHERE name = 'turn-sequence'"
    )
    conn.execute(
        "INSERT OR IGNORE INTO store_counters (name, value) VALUES ('roster-generation', 0)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_turn_sequence_unique "
        "ON runs(turn_sequence) WHERE turn_sequence > 0"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_last_activity ON runs(last_activity_at DESC, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_session_turn_sequence "
        "ON runs(session_id, turn_sequence DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_receipts_trace_recorded "
        "ON model_receipts(trace_id, recorded_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_receipts_session_recorded "
        "ON model_receipts(session_id, recorded_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_routing_query_hash "
        "ON routing_decisions(query_hash, created_at DESC)"
    )
    conn.execute("DROP INDEX IF EXISTS idx_receipts_recent")
    conn.execute("CREATE INDEX idx_receipts_recent ON model_receipts(recorded_at DESC, id DESC)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_terminal_finalization_unique "
        "ON runs(terminal_finalization_id) WHERE terminal_finalization_id IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_session_terminal "
        "ON runs(session_id, terminal_finalization_id) "
        "WHERE terminal_finalization_id IS NOT NULL"
    )
    if current_version < 12:
        # Do this before legacy privacy projection can discard the marker.
        conn.execute(
            "UPDATE runs SET status = 'completed', "
            "ended_at = COALESCE(ended_at, started_at) "
            "WHERE status = 'evidence_only' AND "
            "CASE WHEN json_valid(metadata) "
            "THEN json_extract(metadata, '$.migrated') ELSE 0 END = 1"
        )
    if current_version < 4:
        migrate_private_projections(conn, capture_content=capture_content())
    if current_version < 10:
        migrate_snapshot_projections(conn)
    if current_version < 11:
        # Pre-v11 rows have no deterministic turn identity. Preserve them as
        # session audit history, but never expose them as active evidence.
        conn.execute(
            "UPDATE specialists_loaded SET expired_at = COALESCE(expired_at, loaded_at) "
            "WHERE trace_id = ''"
        )
    if current_version < 12:
        migrate_delegation_identity(conn)
    else:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_delegations_trace_work_unit_unique "
            "ON delegation_events(trace_id, work_unit_id) "
            "WHERE work_unit_id IS NOT NULL AND work_unit_id <> ''"
        )
    migrate_specialist_identity(conn)
    migrate_delegation_activation_unit_identity(conn)
    migrate_delegation_activation_consumption_host_domain(conn)
    create_delegation_activation_consumption_schema(conn)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_activation_grants_public_id "
        "ON delegation_activation_receipts(grant_id) WHERE grant_id <> ''"
    )
    if current_version < 19:
        conn.execute(
            "UPDATE delegation_events SET executed_worker_kind = "
            "'legacy-unverified-worker' WHERE executed_worker_kind = '' "
            "AND status IN ('started', 'running', 'delegated', 'completed')"
        )
    create_delegation_activation_invariant_triggers(conn)
    create_native_child_parent_scope_trigger(conn)
    create_native_child_delivery_verification_schema(conn)
    create_codex_native_plan_scope_triggers(conn)
    create_boolean_domain_triggers(conn)
    create_activity_triggers(conn)
    create_agent_import_event_sequence_schema(
        conn,
        allow_backfill=current_version < 31,
    )
    create_remediation_indexes(conn)
    create_remediation_authority_schema(
        conn,
        allow_rebuild=current_version < 31,
    )
    ensure_remediation_authority_key_integrity(
        conn,
        allow_initialize=current_version < 31,
    )
    if current_version < 26:
        conn.execute(
            "INSERT OR IGNORE INTO agent_candidate_status_events "
            "(id, candidate_id, event_type, from_status, to_status, reason, audit_id, created_at) "
            "SELECT 'migration:' || id || ':' || status, id, 'migration_observed', '', "
            "status, 'schema_v26_status_baseline', '', quarantined_at FROM agent_candidates"
        )
    purge_pending = (
        migrate_legacy_source_credentials(conn, now=now)
        if current_version < 30
        else source_redaction_purge_pending(conn)
    )
    migrate_recruitment_contract_projection_history(conn)

    from agency_runtime.core.store.workforce import backfill_workforce_identity

    backfill_workforce_identity(conn)
    create_workforce_invariant_schema(conn)
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    return purge_pending
