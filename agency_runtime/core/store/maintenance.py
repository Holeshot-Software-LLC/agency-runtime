"""Maintenance and bounded operator-query methods for the runtime store."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.store.queries import (
    DASHBOARD_ACTIVITY_QUERIES,
    RECENT_ACTIVITY_QUERIES,
    bounded_limit,
    normalize_activity_rows,
    normalize_snapshot,
    project_routing_decision,
    retention_predicates,
)
from agency_runtime.core.store.schema import (
    ALL_TABLES as _ALL_TABLES,
)
from agency_runtime.core.store.schema import (
    RUNTIME_DELETE_ORDER as _RUNTIME_DELETE_ORDER,
)
from agency_runtime.core.store.schema import (
    RUNTIME_TABLE_TIMESTAMPS as _RUNTIME_TABLE_TIMESTAMPS,
)


class MaintenanceStoreMixin:
    """Operational reads and retention behavior composed into the store."""

    # ── Maintenance ────────────────────────────────────────────────

    def runtime_table_counts(self) -> dict[str, int]:
        """Return row counts for every Agency Runtime SQLite table."""
        conn = self._connect()
        try:
            counts: dict[str, int] = {}
            for table in _ALL_TABLES:
                # Table is drawn from the immutable schema allowlist.
                cur = conn.execute(
                    f"SELECT COUNT(*) AS count FROM {table}"  # nosec B608
                )
                counts[table] = int(cur.fetchone()["count"])
            return counts
        finally:
            conn.close()

    def database_stats(self) -> dict[str, Any]:
        """Return database size and row-count stats for CLI maintenance."""

        return {
            **self.database_sizes(),
            "tables": self.runtime_table_counts(),
        }

    def database_sizes(self) -> dict[str, Any]:
        """Return cheap database and sidecar sizes without scanning tables."""

        self._assert_storage_paths_safe()
        wal_path = Path(f"{self.db_path}-wal")
        shm_path = Path(f"{self.db_path}-shm")
        return {
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "wal_size_bytes": wal_path.stat().st_size if wal_path.exists() else 0,
            "shm_size_bytes": shm_path.stat().st_size if shm_path.exists() else 0,
        }

    def recent_runtime_activity(self, *, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
        """Return bounded metadata-only activity for operator surfaces.

        Raw prompts, worker stdout/stderr, API bases, and other potentially
        sensitive content are deliberately excluded. Content capture is an
        explicit opt-in concern, not a dashboard side effect.
        """
        return self._recent_activity(RECENT_ACTIVITY_QUERIES, limit=limit)

    def recent_dashboard_activity(self, *, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
        """Return the narrower metadata projection used by dashboard APIs."""

        return self._recent_activity(DASHBOARD_ACTIVITY_QUERIES, limit=limit)

    def _recent_activity(
        self,
        queries: Mapping[str, str],
        *,
        limit: int,
    ) -> dict[str, list[dict[str, Any]]]:
        """Execute one fixed family of bounded recent-activity queries."""

        bounded = bounded_limit(limit)
        conn = self._connect()
        try:
            activity: dict[str, list[dict[str, Any]]] = {}
            for name, sql in queries.items():
                rows = [dict(row) for row in conn.execute(sql, (bounded,)).fetchall()]
                activity[name] = normalize_activity_rows(name, rows)
            return activity
        finally:
            self._repair_storage_permissions()
            conn.close()

    def list_roster_snapshots(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded snapshot metadata without candidate prompt content."""
        bounded = bounded_limit(limit)
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT snapshot_id, created_at, agent_count, approved, activated, "
                "added_count AS added, changed_count AS changed, "
                "removed_count AS removed "
                "FROM agent_snapshots ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (bounded,),
            ).fetchall()
            return [normalize_snapshot(row) for row in rows]
        finally:
            conn.close()

    def record_routing_decision(
        self,
        *,
        trace_id: str,
        session_id: str,
        query_hash: str,
        context_fingerprint: str,
        decision: dict[str, Any],
    ) -> str:
        """Persist one metadata-only authoritative routing projection."""
        safe_decision, safe_work_units, source = project_routing_decision(decision)
        event_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO routing_decisions "
                "(id, trace_id, session_id, query_hash, context_fingerprint, status, source, "
                "selected_ids, semantic_ids, companion_ids, confidence, latency_ms, provider, "
                "work_units, decision, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    session_id,
                    query_hash,
                    context_fingerprint,
                    str(safe_decision.get("status") or "unknown"),
                    source,
                    json.dumps(safe_decision.get("selected_ids") or []),
                    json.dumps(safe_decision.get("semantic_ids") or []),
                    json.dumps(safe_decision.get("available_companion_ids") or []),
                    float(safe_decision.get("confidence") or 0.0),
                    int(safe_decision.get("latency_ms") or 0),
                    str(safe_decision.get("provider") or ""),
                    json.dumps(safe_work_units),
                    json.dumps(safe_decision, sort_keys=True, default=str),
                    self._now(),
                ),
            )
            conn.commit()
            return event_id
        finally:
            conn.close()

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
                where, params = retention_predicates(
                    table,
                    timestamp_expr,
                    cutoff=cutoff,
                    keep_last=keep_last,
                )
                # The helper rejects table/timestamp pairs outside the allowlist.
                count_sql = f"SELECT COUNT(*) AS count FROM {table} WHERE {where}"  # nosec B608
                count = int(conn.execute(count_sql, params).fetchone()["count"])
                deleted[table] = {"deleted": count}
                if count:
                    conn.execute(
                        f"DELETE FROM {table} WHERE {where}",  # nosec B608
                        params,
                    )
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
