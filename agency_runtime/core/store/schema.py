"""SQLite schema definition and transactional migration helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.store.projections import (
    RUN_CONTENT_LIMIT,
    project_delegation_detail,
    project_run_metadata,
    project_snapshot_summary,
    redact_sensitive_text,
    sanitize_api_base,
)

SCHEMA_VERSION = 10

SCHEMA_V1 = """
-- Run tracking
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL UNIQUE,
    session_id TEXT,
    host TEXT NOT NULL DEFAULT 'unknown',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    user_message TEXT,
    metadata TEXT
);

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
    started_at TEXT,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Skills loaded per session
CREATE TABLE IF NOT EXISTS skills_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);

-- Specialists loaded per session
CREATE TABLE IF NOT EXISTS specialists_loaded (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_slug TEXT NOT NULL,
    loaded_at TEXT NOT NULL
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
    skip_reason TEXT,
    error TEXT,
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (trace_id) REFERENCES runs(trace_id)
);

-- Worker runs (delegation execution records)
CREATE TABLE IF NOT EXISTS worker_runs (
    id TEXT PRIMARY KEY,
    delegation_event_id TEXT,
    backend TEXT NOT NULL,
    workdir TEXT,
    exit_code INTEGER,
    stdout TEXT,
    stderr TEXT,
    started_at TEXT NOT NULL,
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
    created_at TEXT NOT NULL
);

-- Roster tables
CREATE TABLE IF NOT EXISTS agent_sources (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    added_at TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    trusted_for_auto_approve INTEGER DEFAULT 0
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
    division TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    source TEXT,
    version TEXT,
    hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    quarantined_at TEXT NOT NULL,
    FOREIGN KEY (download_id) REFERENCES agent_downloads(id)
);

CREATE TABLE IF NOT EXISTS agent_versions (
    id TEXT PRIMARY KEY,
    agent_slug TEXT NOT NULL,
    version TEXT NOT NULL,
    hash TEXT NOT NULL,
    content TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(agent_slug, version)
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
    activated INTEGER DEFAULT 0,
    approved INTEGER NOT NULL DEFAULT 0,
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
    version TEXT,
    hash TEXT,
    categories TEXT,
    capabilities TEXT,
    tool_affinity TEXT,
    prompt_path TEXT,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_import_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    agent_slug TEXT,
    detail TEXT,
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

-- Persistent, host-scoped soft control. Native plugins remain registered so
-- their control surface can turn the runtime back on without an installer.
CREATE TABLE IF NOT EXISTS host_controls (
    host TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    updated_at TEXT NOT NULL,
    source TEXT NOT NULL
);

-- Last successful content-free live canary for each host contract.
CREATE TABLE IF NOT EXISTS host_canary_attestations (
    host TEXT PRIMARY KEY,
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

-- Read-path indexes used by hooks, the dashboard, and retention jobs.
CREATE INDEX IF NOT EXISTS idx_runs_trace_id ON runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_recent ON runs(started_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_trace_id ON model_receipts(trace_id);
CREATE INDEX IF NOT EXISTS idx_receipts_session_ended ON model_receipts(session_id, ended_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_recent ON model_receipts(COALESCE(ended_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_skills_session_loaded ON skills_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_specialists_session_loaded ON specialists_loaded(session_id, loaded_at);
CREATE INDEX IF NOT EXISTS idx_delegations_trace_id ON delegation_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_delegations_session_started ON delegation_events(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_delegations_recent ON delegation_events(COALESCE(completed_at, started_at) DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_worker_runs_event ON worker_runs(delegation_event_id);
CREATE INDEX IF NOT EXISTS idx_finalization_trace_created ON finalization_events(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_finalization_recent ON finalization_events(created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_routing_trace_created ON routing_decisions(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_session_created ON routing_decisions(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_routing_recent ON routing_decisions(created_at DESC, id DESC);
"""

ALL_TABLES: tuple[str, ...] = (
    "runs",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "delegation_events",
    "worker_runs",
    "finalization_events",
    "routing_decisions",
    "host_controls",
    "host_canary_attestations",
    "agent_sources",
    "agent_downloads",
    "agent_candidates",
    "agent_versions",
    "agent_categories",
    "agent_embeddings",
    "agent_snapshots",
    "agent_active",
    "agent_import_events",
    "schema_version",
)

RUNTIME_TABLE_TIMESTAMPS: dict[str, str] = {
    "runs": "COALESCE(ended_at, started_at)",
    "model_receipts": "COALESCE(ended_at, started_at)",
    "skills_loaded": "loaded_at",
    "specialists_loaded": "loaded_at",
    "delegation_events": "COALESCE(completed_at, started_at)",
    "worker_runs": "COALESCE(ended_at, started_at)",
    "finalization_events": "created_at",
    "routing_decisions": "created_at",
}

RUNTIME_DELETE_ORDER: tuple[str, ...] = (
    "worker_runs",
    "delegation_events",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "finalization_events",
    "routing_decisions",
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
            "host TEXT NOT NULL DEFAULT 'unknown', started_at TEXT NOT NULL, ended_at TEXT, "
            "status TEXT NOT NULL DEFAULT 'active', user_message TEXT, metadata TEXT)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO runs_v2 "
            "(id, trace_id, session_id, host, started_at, ended_at, status, user_message, metadata) "
            "SELECT id, trace_id, session_id, host, started_at, ended_at, status, user_message, metadata "
            "FROM runs ORDER BY started_at, rowid"
        )
        conn.execute("DROP TABLE runs")
        conn.execute("ALTER TABLE runs_v2 RENAME TO runs")

    for source_table in ("model_receipts", "delegation_events"):
        conn.execute(
            "INSERT OR IGNORE INTO runs "
            "(id, trace_id, session_id, host, started_at, status, user_message, metadata) "
            f"SELECT lower(hex(randomblob(16))), trace_id, COALESCE(session_id, ''), "  # nosec B608
            f"COALESCE(host, 'unknown'), COALESCE(MIN(started_at), ?), "
            "'evidence_only', '', '{\"migrated\":true}' "
            f"FROM {source_table} WHERE trace_id IS NOT NULL GROUP BY trace_id",
            (now(),),
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


def migrate_schema(
    conn: sqlite3.Connection,
    *,
    now: Callable[[], str],
    capture_content: Callable[[], bool],
) -> None:
    """Apply all schema and privacy migrations inside the caller transaction."""

    conn.executescript("BEGIN IMMEDIATE;\n" + SCHEMA_V1)
    ensure_column(
        conn,
        "agent_sources",
        "trusted_for_auto_approve",
        "INTEGER DEFAULT 0",
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
    migrate_trace_integrity(conn, now=now)
    version_row = conn.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
    current_version = int(version_row["version"] or 0)
    if current_version < 4:
        migrate_private_projections(conn, capture_content=capture_content())
    if current_version < 10:
        migrate_snapshot_projections(conn)
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
