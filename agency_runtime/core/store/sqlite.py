"""SQLite canonical store for Agency Runtime.

All runtime state — runs, model receipts, skills, specialists, delegations,
roster — lives here. No loose JSON files.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

def _default_db_path() -> Path:
    """Resolve DB path from config, honoring the environment per call."""
    if env_path := os.environ.get("AGENCY_DB_PATH"):
        return Path(os.path.expanduser(env_path))
    try:
        from agency_runtime.core.config import load_config
        return load_config().store.resolved_path()
    except Exception:
        return Path.home() / ".agency-runtime" / "agency.db"

_SCHEMA_V1 = """
-- Run tracking
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
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
    activated INTEGER DEFAULT 0
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
"""

_ALL_TABLES: tuple[str, ...] = (
    "runs",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "delegation_events",
    "worker_runs",
    "finalization_events",
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

_RUNTIME_TABLE_TIMESTAMPS: dict[str, str] = {
    "runs": "COALESCE(ended_at, started_at)",
    "model_receipts": "COALESCE(ended_at, started_at)",
    "skills_loaded": "loaded_at",
    "specialists_loaded": "loaded_at",
    "delegation_events": "COALESCE(completed_at, started_at)",
    "worker_runs": "COALESCE(ended_at, started_at)",
    "finalization_events": "created_at",
}

_RUNTIME_DELETE_ORDER: tuple[str, ...] = (
    "worker_runs",
    "delegation_events",
    "model_receipts",
    "skills_loaded",
    "specialists_loaded",
    "finalization_events",
    "runs",
)


class Store:
    """SQLite-backed canonical store for Agency Runtime."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path:
            self.db_path = Path(os.path.expanduser(str(db_path)))
        else:
            self.db_path = _default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA_V1)
            self._ensure_column(
                conn,
                "agent_sources",
                "trusted_for_auto_approve",
                "INTEGER DEFAULT 0",
            )
            cur = conn.execute("SELECT version FROM schema_version WHERE version = 1")
            if cur.fetchone() is None:
                conn.execute("INSERT INTO schema_version (version) VALUES (1)")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        """Add a SQLite column when opening a database created by an older build."""
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    # ── Runs ───────────────────────────────────────────────────────

    def create_run(self, *, trace_id: str, session_id: str = "", host: str = "unknown",
                   user_message: str = "", metadata: dict | None = None) -> str:
        run_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO runs (id, trace_id, session_id, host, started_at, status, user_message, metadata) "
                "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
                (run_id, trace_id, session_id, host, self._now(),
                 user_message[:2000], json.dumps(metadata) if metadata else None),
            )
            conn.commit()
            return run_id
        finally:
            conn.close()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE runs SET ended_at = ?, status = ? WHERE id = ?",
                (self._now(), status, run_id),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Model receipts ─────────────────────────────────────────────

    def record_model_receipt(self, *, trace_id: str, session_id: str = "",
                             host: str = "unknown", requested_model: str = "",
                             model_group: str = "", resolved_provider: str = "",
                             resolved_model: str = "", api_base: str = "",
                             attempted_fallbacks: int = 0, model_id: str = "",
                             source: str = "unknown", started_at: str = "",
                             ended_at: str = "", status: str = "success") -> str:
        receipt_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO model_receipts "
                "(id, trace_id, session_id, host, requested_model, model_group, "
                "resolved_provider, resolved_model, api_base, attempted_fallbacks, "
                "model_id, source, started_at, ended_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (receipt_id, trace_id, session_id, host, requested_model, model_group,
                 resolved_provider, resolved_model, api_base, attempted_fallbacks,
                 model_id, source, started_at or self._now(), ended_at or self._now(), status),
            )
            conn.commit()
            return receipt_id
        finally:
            conn.close()

    def get_model_receipt(self, trace_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE trace_id = ? ORDER BY id DESC LIMIT 1",
                (trace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_model_receipt_for_session(self, session_id: str) -> dict[str, Any] | None:
        """Get the most recent model receipt for a session."""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE session_id = ? "
                "ORDER BY ended_at DESC, started_at DESC, id DESC LIMIT 1",
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Skills ─────────────────────────────────────────────────────

    def record_skill_loaded(self, session_id: str, skill_name: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO skills_loaded (id, session_id, skill_name, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, skill_name, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_skills_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT skill_name FROM skills_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["skill_name"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Specialists ────────────────────────────────────────────────

    def record_specialist_loaded(self, session_id: str, agent_slug: str) -> None:
        if not session_id or not agent_slug:
            return
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT 1 FROM specialists_loaded WHERE session_id = ? AND agent_slug = ? LIMIT 1",
                (session_id, agent_slug),
            ).fetchone()
            if existing:
                return
            conn.execute(
                "INSERT INTO specialists_loaded (id, session_id, agent_slug, loaded_at) "
                "VALUES (?, ?, ?, ?)",
                (self._uuid(), session_id, agent_slug, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_specialists_for_session(self, session_id: str) -> list[str]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at",
                (session_id,),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Delegation events ──────────────────────────────────────────

    def record_delegation(self, *, trace_id: str, session_id: str = "",
                          host: str = "unknown", work_unit_id: str = "",
                          recommended_agent: str = "", status: str = "suggested",
                          backend: str = "", skip_reason: str = "",
                          error: str = "") -> str:
        event_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO delegation_events "
                "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                "status, backend, skip_reason, error, started_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event_id, trace_id, session_id, host, work_unit_id,
                 recommended_agent, status, backend, skip_reason, error, self._now()),
            )
            conn.commit()
            return event_id
        finally:
            conn.close()

    def update_delegation(self, event_id: str, *, status: str,
                          backend: str = "", error: str = "",
                          recommended_agent: str = "",
                          skip_reason: str = "",
                          host: str = "") -> None:
        conn = self._connect()
        try:
            ended = self._now() if status in ("completed", "failed", "skipped") else None
            conn.execute(
                "UPDATE delegation_events "
                "SET status = ?, "
                "host = COALESCE(NULLIF(?, ''), host), "
                "backend = COALESCE(NULLIF(?, ''), backend), "
                "error = ?, "
                "recommended_agent = COALESCE(NULLIF(?, ''), recommended_agent), "
                "skip_reason = COALESCE(NULLIF(?, ''), skip_reason), "
                "completed_at = COALESCE(?, completed_at) "
                "WHERE id = ?",
                (status, host, backend, error, recommended_agent, skip_reason, ended, event_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM delegation_events WHERE trace_id = ? ORDER BY started_at",
                (trace_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegations_for_session(self, session_id: str, statuses: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        """Return delegation events for a session, optionally filtered by status."""
        conn = self._connect()
        try:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                cur = conn.execute(
                    f"SELECT * FROM delegation_events WHERE session_id = ? AND status IN ({placeholders}) ORDER BY started_at",
                    (session_id, *statuses),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM delegation_events WHERE session_id = ? ORDER BY started_at",
                    (session_id,),
                )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Maintenance ────────────────────────────────────────────────

    def runtime_table_counts(self) -> dict[str, int]:
        """Return row counts for every Agency Runtime SQLite table."""
        conn = self._connect()
        try:
            counts: dict[str, int] = {}
            for table in _ALL_TABLES:
                cur = conn.execute(f"SELECT COUNT(*) AS count FROM {table}")
                counts[table] = int(cur.fetchone()["count"])
            return counts
        finally:
            conn.close()

    def database_stats(self) -> dict[str, Any]:
        """Return database size and row-count stats for CLI maintenance."""
        wal_path = Path(f"{self.db_path}-wal")
        shm_path = Path(f"{self.db_path}-shm")
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "wal_size_bytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "shm_size_bytes": shm_path.stat().st_size if shm_path.exists() else 0,
            "tables": self.runtime_table_counts(),
        }

    def trim_runtime_tables(
        self,
        *,
        older_than_days: int | None = None,
        keep_last: int | None = None,
        dry_run: bool = False,
        vacuum: bool = True,
    ) -> dict[str, Any]:
        """Trim append-only runtime/audit tables without touching the roster.

        A retention policy is required. Use ``older_than_days`` for age-based
        cleanup, ``keep_last`` for bounded local smoke tests, or both.
        """
        if older_than_days is None and keep_last is None:
            raise ValueError("trim requires older_than_days, keep_last, or both")
        if older_than_days is not None and older_than_days < 0:
            raise ValueError("older_than_days must be >= 0")
        if keep_last is not None and keep_last < 0:
            raise ValueError("keep_last must be >= 0")

        cutoff = None
        if older_than_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()

        before = self.database_stats()
        deleted: dict[str, dict[str, int]] = {}
        conn = self._connect()
        try:
            for table in _RUNTIME_DELETE_ORDER:
                timestamp_expr = _RUNTIME_TABLE_TIMESTAMPS[table]
                clauses: list[str] = []
                params: list[Any] = []
                if cutoff is not None:
                    clauses.append(f"{timestamp_expr} < ?")
                    params.append(cutoff)
                if keep_last is not None:
                    clauses.append(
                        "rowid NOT IN ("
                        f"SELECT rowid FROM {table} "
                        f"ORDER BY {timestamp_expr} DESC, rowid DESC LIMIT ?"
                        ")"
                    )
                    params.append(keep_last)
                where = " AND ".join(f"({clause})" for clause in clauses)
                count_sql = f"SELECT COUNT(*) AS count FROM {table} WHERE {where}"
                count = int(conn.execute(count_sql, params).fetchone()["count"])
                deleted[table] = {"deleted": count}
                if count and not dry_run:
                    conn.execute(f"DELETE FROM {table} WHERE {where}", params)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        finally:
            conn.close()

        if vacuum and not dry_run:
            conn = self._connect()
            try:
                conn.execute("VACUUM")
            finally:
                conn.close()

        after = self.database_stats()
        return {
            "db_path": str(self.db_path),
            "dry_run": dry_run,
            "older_than_days": older_than_days,
            "keep_last": keep_last,
            "vacuumed": bool(vacuum and not dry_run),
            "db_size_before_bytes": before["db_size_bytes"],
            "db_size_after_bytes": after["db_size_bytes"],
            "wal_size_before_bytes": before["wal_size_bytes"],
            "wal_size_after_bytes": after["wal_size_bytes"],
            "tables": deleted,
            "remaining_tables": after["tables"],
        }

    # ── Roster ─────────────────────────────────────────────────────

    def add_agent_source(self, url: str, name: str = "", *, trusted_for_auto_approve: bool = False) -> str:
        source_id = self._uuid()
        conn = self._connect()
        try:
            existing = conn.execute("SELECT id FROM agent_sources WHERE url = ?", (url,)).fetchone()
            if existing:
                conn.execute(
                    "UPDATE agent_sources "
                    "SET name = COALESCE(NULLIF(?, ''), name), enabled = 1, "
                    "trusted_for_auto_approve = CASE WHEN ? THEN 1 ELSE trusted_for_auto_approve END "
                    "WHERE url = ?",
                    (name, 1 if trusted_for_auto_approve else 0, url),
                )
                source_id = existing["id"]
            else:
                conn.execute(
                    "INSERT INTO agent_sources (id, url, name, added_at, trusted_for_auto_approve) VALUES (?, ?, ?, ?, ?)",
                    (source_id, url, name or url, self._now(), 1 if trusted_for_auto_approve else 0),
                )
            conn.commit()
            return source_id
        finally:
            conn.close()

    def list_agent_sources(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT * FROM agent_sources WHERE enabled = 1 ORDER BY added_at DESC")
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def activate_agent(self, agent: dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO agent_active "
                "(id, agent_slug, name, division, description, source, version, hash, "
                "categories, capabilities, tool_affinity, prompt_path, activated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (self._uuid(), agent["slug"], agent.get("name", ""),
                 agent.get("division", ""), agent.get("description", ""),
                 agent.get("source", ""), agent.get("version", ""),
                 agent.get("hash", ""),
                 json.dumps(agent.get("categories", [])),
                 json.dumps(agent.get("capabilities", [])),
                 json.dumps(agent.get("tool_affinity", [])),
                 agent.get("prompt_path", ""), self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_active_roster(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT * FROM agent_active ORDER BY agent_slug")
            agents = []
            for row in cur.fetchall():
                d = dict(row)
                d["categories"] = json.loads(d.get("categories") or "[]")
                d["capabilities"] = json.loads(d.get("capabilities") or "[]")
                d["tool_affinity"] = json.loads(d.get("tool_affinity") or "[]")
                agents.append(d)
            return agents
        finally:
            conn.close()

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        """Return active roster in selector-compatible format."""
        agents = self.get_active_roster()
        catalog = []
        for a in agents:
            catalog.append({
                "slug": a["agent_slug"],
                "name": a.get("name", ""),
                "description": a.get("description", ""),
                "division": a.get("division", ""),
                "categories": a.get("categories", []),
                "capabilities": a.get("capabilities", []),
            })
        return catalog

    def deactivate_agent(self, slug: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM agent_active WHERE agent_slug = ?", (slug,))
            conn.commit()
        finally:
            conn.close()

    def create_snapshot(self, snapshot_id: str, manifest: dict[str, Any]) -> None:
        snapshot_agent_count = len(manifest.get("candidates", []))
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_snapshots (id, snapshot_id, created_at, agent_count, manifest, activated) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                (self._uuid(), snapshot_id, self._now(), snapshot_agent_count,
                 json.dumps(manifest)),
            )
            conn.commit()
        finally:
            conn.close()

    def record_import_event(self, event_type: str, agent_slug: str = "", detail: str = "") -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_import_events (id, event_type, agent_slug, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._uuid(), event_type, agent_slug, detail, self._now()),
            )
            conn.commit()
        finally:
            conn.close()

    # ── Finalization ───────────────────────────────────────────────

    def record_finalization(self, *, trace_id: str, host: str,
                            action: str, missing: list[str] | None = None) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO finalization_events (id, trace_id, host, action, missing, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._uuid(), trace_id, host, action,
                 json.dumps(missing) if missing else None, self._now()),
            )
            conn.commit()
        finally:
            conn.close()
