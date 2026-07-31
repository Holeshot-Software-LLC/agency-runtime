"""Maintenance and bounded operator-query methods for the runtime store."""

from __future__ import annotations

import hashlib
import json
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.store.queries import (
    DASHBOARD_ACTIVITY_QUERIES,
    RECENT_ACTIVITY_QUERIES,
    bounded_limit,
    normalize_activity_rows,
    normalize_snapshot,
    project_routing_decision,
    retention_predicates,
    retention_window_predicates,
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
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point
from agency_runtime.core.store.trace_identity import correlation_pair_digests

_DASHBOARD_ACTIVITY_PAGE_SPECS: Mapping[str, tuple[str, str, str]] = {
    "runs": ("runs", "runs.started_at", "runs.id"),
    "receipts": ("model_receipts", "model_receipts.recorded_at", "model_receipts.id"),
    "preflight_failures": (
        "preflight_failure_receipts",
        "preflight_failure_receipts.recorded_at",
        "preflight_failure_receipts.id",
    ),
    "delegations": (
        "delegation_events",
        "COALESCE(delegation_events.completed_at, delegation_events.started_at)",
        "delegation_events.id",
    ),
    "finalizations": (
        "finalization_events",
        "finalization_events.created_at",
        "finalization_events.id",
    ),
    "specialists": ("specialists_loaded", "specialist.loaded_at", "specialist.id"),
    "routing": ("routing_decisions", "routing_decisions.created_at", "routing_decisions.id"),
}


def _activity_cursor_time(name: str, row: Mapping[str, Any]) -> str:
    if name == "delegations":
        return str(row.get("completed_at") or row.get("started_at") or "")
    return str(
        row.get(
            {
                "runs": "started_at",
                "receipts": "recorded_at",
                "preflight_failures": "recorded_at",
                "finalizations": "created_at",
                "specialists": "loaded_at",
                "routing": "created_at",
            }[name]
        )
        or ""
    )


# Even an explicit age-zero trim must not reap a normal long-running agent
# turn. Open graphs become retention candidates only after a full day without
# any store write, in addition to the operator's policy cutoff.
_STALE_OPEN_MIN_INACTIVITY_SECONDS = 24 * 60 * 60


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
            "db_size_bytes": self._storage_file_size(self.db_path),
            "wal_size_bytes": self._storage_file_size(wal_path),
            "shm_size_bytes": self._storage_file_size(shm_path),
        }

    def _storage_file_size(self, path: Path) -> int:
        """Return one no-follow size, treating concurrent removal as absent."""

        metadata = self._storage_metadata(path, optional=True)
        if metadata is None:
            return 0
        if metadata_is_link_or_reparse_point(metadata):
            raise PermissionError(
                "refusing Agency Runtime database or sidecar symlink or reparse point"
            )
        if not stat.S_ISREG(metadata.st_mode):
            raise PermissionError("refusing Agency Runtime database or sidecar non-regular file")
        return int(metadata.st_size)

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

    def dashboard_activity_snapshot(self, *, limit: int = 50) -> dict[str, Any]:
        """Read every bounded dashboard activity window from one SQLite snapshot."""

        bounded = bounded_limit(limit)
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            activity: dict[str, list[dict[str, Any]]] = {}
            collections: dict[str, dict[str, Any]] = {}
            for name, sql in DASHBOARD_ACTIVITY_QUERIES.items():
                stored = [dict(row) for row in conn.execute(sql, (bounded + 1,)).fetchall()]
                page = normalize_activity_rows(name, stored[:bounded])
                table, _timestamp, _identity = _DASHBOARD_ACTIVITY_PAGE_SPECS[name]
                total = int(
                    conn.execute(
                        f"SELECT COUNT(*) AS count FROM {table}"  # nosec B608
                    ).fetchone()["count"]
                )
                truncated = len(stored) > bounded
                activity[name] = page
                collections[name] = {
                    "page_count": len(page),
                    "filtered_count": total,
                    "total_count": total,
                    "limit": bounded,
                    "truncated": truncated,
                    "next_time": _activity_cursor_time(name, page[-1])
                    if truncated and page
                    else "",
                    "next_id": str(page[-1].get("id") or "") if truncated and page else "",
                }
            conn.commit()
            return {"activity": activity, "collections": collections}
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                self._repair_storage_permissions()
            finally:
                conn.close()

    def dashboard_activity_page(
        self,
        kind: str,
        *,
        limit: int = 50,
        after_time: str = "",
        after_id: str = "",
    ) -> dict[str, Any]:
        """Return one metadata-only activity collection via a live keyset cursor."""

        name = str(kind or "").strip().casefold()
        if name not in DASHBOARD_ACTIVITY_QUERIES:
            raise ValueError("activity collection is invalid")
        bounded = bounded_limit(limit)
        cursor_time = str(after_time or "").strip()
        cursor_id = str(after_id or "").strip()
        if bool(cursor_time) != bool(cursor_id):
            raise ValueError("activity cursor is incomplete")
        base = DASHBOARD_ACTIVITY_QUERIES[name].rsplit(" ORDER BY ", 1)[0]
        table, timestamp, identity = _DASHBOARD_ACTIVITY_PAGE_SPECS[name]
        where = ""
        values: list[Any] = []
        if cursor_time:
            where = f" WHERE ({timestamp} < ? OR ({timestamp} = ? AND {identity} < ?))"  # nosec B608
            values.extend((cursor_time, cursor_time, cursor_id))
        sql = (
            base + where + f" ORDER BY {timestamp} DESC, {identity} DESC LIMIT ?"  # nosec B608
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            stored = [dict(row) for row in conn.execute(sql, (*values, bounded + 1)).fetchall()]
            total = int(
                conn.execute(
                    f"SELECT COUNT(*) AS count FROM {table}"  # nosec B608
                ).fetchone()["count"]
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                self._repair_storage_permissions()
            finally:
                conn.close()
        rows = normalize_activity_rows(name, stored[:bounded])
        truncated = len(stored) > bounded
        return {
            "rows": rows,
            "page_count": len(rows),
            "filtered_count": total,
            "total_count": total,
            "limit": bounded,
            "truncated": truncated,
            "next_time": _activity_cursor_time(name, rows[-1]) if truncated and rows else "",
            "next_id": str(rows[-1].get("id") or "") if truncated and rows else "",
        }

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
            try:
                self._repair_storage_permissions()
            finally:
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

    def roster_snapshot_page(
        self,
        *,
        limit: int = 50,
        after_created_at: str = "",
        after_snapshot_id: str = "",
    ) -> dict[str, Any]:
        """Return one newest-first roster-snapshot page with an exact total."""

        bounded = bounded_limit(limit)
        cursor_time = str(after_created_at or "").strip()
        cursor_id = str(after_snapshot_id or "").strip()
        if bool(cursor_time) != bool(cursor_id):
            raise ValueError("snapshot cursor is incomplete")
        where = ""
        values: list[Any] = []
        if cursor_time:
            where = " WHERE (created_at < ? OR (created_at = ? AND snapshot_id < ?))"
            values.extend((cursor_time, cursor_time, cursor_id))
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            total = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_snapshots").fetchone()["count"]
            )
            revision_rows = [
                dict(row)
                for row in conn.execute(
                    "SELECT snapshot_id, created_at, approved, activated, agent_count "
                    "FROM agent_snapshots ORDER BY created_at DESC, snapshot_id DESC"
                ).fetchall()
            ]
            rows = conn.execute(
                "SELECT snapshot_id, created_at, agent_count, approved, activated, "
                "added_count AS added, changed_count AS changed, removed_count AS removed "
                "FROM agent_snapshots"
                + where
                + " ORDER BY created_at DESC, snapshot_id DESC LIMIT ?",
                (*values, bounded + 1),
            ).fetchall()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        page = [normalize_snapshot(row) for row in rows[:bounded]]
        revision_document = json.dumps(
            revision_rows,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        truncated = len(rows) > bounded
        return {
            "rows": page,
            "total_count": total,
            "truncated": truncated,
            "next_created_at": str(page[-1]["created_at"]) if truncated and page else "",
            "next_snapshot_id": str(page[-1]["snapshot_id"]) if truncated and page else "",
            "collection_revision": hashlib.sha256(
                f"roster-snapshots.v1\\0{revision_document}".encode()
            ).hexdigest(),
        }

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
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_query_hash = str(query_hash or "").strip()
        normalized_context_fingerprint = str(context_fingerprint or "").strip()
        for label, digest in (
            ("query_hash", normalized_query_hash),
            ("context_fingerprint", normalized_context_fingerprint),
        ):
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"{label} must be a lowercase SHA-256 digest")
        if not isinstance(decision, Mapping):
            raise ValueError("routing decision must be a mapping")
        safe_decision, safe_work_units, source = project_routing_decision(decision)
        event_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._ensure_run(
                conn,
                trace_id=normalized_trace,
                session_id=normalized_session,
            )
            conn.execute(
                "INSERT INTO routing_decisions "
                "(id, trace_id, session_id, query_hash, context_fingerprint, status, source, "
                "selected_ids, semantic_ids, companion_ids, confidence, latency_ms, provider, "
                "work_units, decision, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "  # nosec B608
                f"{STORE_CLOCK_SQL})",
                (
                    event_id,
                    normalized_trace,
                    normalized_session,
                    normalized_query_hash,
                    normalized_context_fingerprint,
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
                ),
            )
            conn.commit()
            return event_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _delete_eligible_terminal_pairs(
        self,
        conn: Any,
        *,
        cutoff: str | None,
        keep_last: int | None,
        retired_at: str,
    ) -> tuple[int, int]:
        """Delete bound terminal event/run pairs only when both are eligible."""

        run_clauses, run_parameters = retention_window_predicates(
            "runs",
            _RUNTIME_TABLE_TIMESTAMPS["runs"],
            cutoff=cutoff,
            keep_last=keep_last,
        )
        event_clauses, event_parameters = retention_window_predicates(
            "finalization_events",
            _RUNTIME_TABLE_TIMESTAMPS["finalization_events"],
            cutoff=cutoff,
            keep_last=keep_last,
        )
        run_where = " AND ".join(f"({clause})" for clause in run_clauses)
        event_where = " AND ".join(f"({clause})" for clause in event_clauses)
        conn.execute(
            "CREATE TEMP TABLE IF NOT EXISTS agency_terminal_pair_candidates ("
            "run_id TEXT PRIMARY KEY, event_id TEXT NOT NULL UNIQUE, "
            "trace_id TEXT NOT NULL UNIQUE, session_id TEXT NOT NULL, "
            "turn_sequence INTEGER NOT NULL)"
        )
        conn.execute("DELETE FROM agency_terminal_pair_candidates")
        conn.execute(
            "WITH eligible_runs AS ("
            "SELECT id, trace_id, session_id, status, terminal_finalization_id, "
            "turn_sequence, started_at FROM runs "
            f"WHERE {run_where}"  # nosec B608
            "), eligible_events AS ("
            "SELECT id, trace_id, response_hash, terminal_status "
            "FROM finalization_events "
            f"WHERE {event_where}"  # nosec B608
            ") INSERT INTO agency_terminal_pair_candidates "
            "(run_id, event_id, trace_id, session_id, turn_sequence) "
            "SELECT run.id, event.id, run.trace_id, COALESCE(run.session_id, ''), "
            "run.turn_sequence FROM eligible_runs AS run "
            "JOIN eligible_events AS event "
            "ON event.id = run.terminal_finalization_id "
            "AND event.trace_id = run.trace_id "
            "AND event.terminal_status = run.status "
            "WHERE event.response_hash IS NOT NULL "
            "AND run.status NOT IN ('active', 'evidence_only') "
            "AND NOT EXISTS (SELECT 1 FROM model_receipts "
            "WHERE model_receipts.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM skills_loaded "
            "WHERE skills_loaded.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM specialists_loaded "
            "WHERE specialists_loaded.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM delegation_activation_receipts "
            "WHERE delegation_activation_receipts.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM delegation_events "
            "WHERE delegation_events.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM routing_decisions "
            "WHERE routing_decisions.trace_id = run.trace_id) "
            "AND NOT EXISTS (SELECT 1 FROM finalization_events AS other "
            "WHERE other.trace_id = run.trace_id AND other.id <> event.id)",
            (*run_parameters, *event_parameters),
        )
        pair_count = int(
            conn.execute("SELECT COUNT(*) FROM agency_terminal_pair_candidates").fetchone()[0]
        )
        if not pair_count:
            return 0, 0
        tombstones_created = self._record_trace_tombstones(
            conn,
            conn.execute(
                "SELECT trace_id, session_id, turn_sequence FROM agency_terminal_pair_candidates"
            ).fetchall(),
            retired_at=retired_at,
        )
        deleted_runs = conn.execute(
            "DELETE FROM runs WHERE id IN (SELECT run_id FROM agency_terminal_pair_candidates)"
        ).rowcount
        deleted_events = conn.execute(
            "DELETE FROM finalization_events WHERE id IN ("
            "SELECT event_id FROM agency_terminal_pair_candidates)"
        ).rowcount
        if deleted_runs != pair_count or deleted_events != pair_count:
            raise RuntimeError("terminal retention pair delete lost atomicity")
        return pair_count, tombstones_created

    @staticmethod
    def _record_trace_tombstones(
        conn: Any,
        rows: list[Any],
        *,
        retired_at: str,
    ) -> int:
        """Persist fixed-size anti-resurrection identities before run deletion."""

        created = 0
        for row in rows:
            trace_id = str(row["trace_id"] or "")
            session_id = str(row["session_id"] or "")
            trace_digest, session_digest = correlation_pair_digests(
                conn,
                trace_id=trace_id,
                session_id=session_id,
            )
            # Canary maturity is invalid once its raw turn graph is retired.
            # Delete the attestation rather than retaining the correlation
            # under another field or claiming a canary that can no longer be
            # audited from the runtime evidence tables.
            conn.execute(
                "DELETE FROM host_canary_attestations WHERE trace_id = ?",
                (trace_id,),
            )
            cursor = conn.execute(
                "INSERT INTO trace_tombstones "
                "(trace_digest, session_digest, turn_sequence, retired_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(trace_digest) DO NOTHING",
                (
                    trace_digest,
                    session_digest,
                    int(row["turn_sequence"]),
                    retired_at,
                ),
            )
            created += max(0, int(cursor.rowcount))
        return created

    @staticmethod
    def _retire_stale_open_runs(
        conn: Any,
        *,
        cutoff: str,
        inactivity_cutoff: str,
    ) -> int:
        """CAS-retire open graphs stale by policy and a conservative lease."""

        conn.execute(
            "CREATE TEMP TABLE IF NOT EXISTS agency_stale_open_candidates ("
            "run_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL UNIQUE)"
        )
        conn.execute("DELETE FROM agency_stale_open_candidates")
        conn.execute(
            "INSERT INTO agency_stale_open_candidates (run_id, trace_id) "
            "SELECT run.id, run.trace_id FROM runs AS run "
            "WHERE run.status IN ('active', 'evidence_only') "
            "AND run.last_activity_at < ? AND run.last_activity_at < ?",
            (cutoff, inactivity_cutoff),
        )
        candidate_count = int(
            conn.execute("SELECT COUNT(*) FROM agency_stale_open_candidates").fetchone()[0]
        )
        if not candidate_count:
            return 0
        retired = conn.execute(
            "UPDATE runs SET status = 'retention_expired', "
            "ended_at = COALESCE(ended_at, last_activity_at) "
            "WHERE id IN (SELECT run_id FROM agency_stale_open_candidates) "
            "AND status IN ('active', 'evidence_only')",
        ).rowcount
        if retired != candidate_count:
            raise RuntimeError("stale open-run retirement lost compare-and-swap")
        conn.execute(
            f"UPDATE specialists_loaded SET expired_at = "  # nosec B608
            f"COALESCE(expired_at, {STORE_CLOCK_SQL}) "
            "WHERE trace_id IN (SELECT trace_id FROM agency_stale_open_candidates)",
        )
        return candidate_count

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

        before = self.database_stats()
        deleted: dict[str, dict[str, int]] = {}
        paired_run_deletions = 0
        retired_open_runs = 0
        tombstones_created = 0
        cutoff: str | None = None
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            clock = conn.execute(
                f"SELECT {STORE_CLOCK_SQL} AS retired_at, "  # nosec B608
                "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW', ?) AS cutoff, "
                "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW', ?) "
                "AS inactivity_cutoff",
                (
                    f"-{older_than_days or 0} days",
                    f"-{_STALE_OPEN_MIN_INACTIVITY_SECONDS} seconds",
                ),
            ).fetchone()
            retired_at = str(clock["retired_at"])
            if older_than_days is not None:
                cutoff = str(clock["cutoff"])
                retired_open_runs = self._retire_stale_open_runs(
                    conn,
                    cutoff=cutoff,
                    inactivity_cutoff=str(clock["inactivity_cutoff"]),
                )
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
                if count:
                    if table == "runs":
                        rows = conn.execute(
                            f"SELECT trace_id, COALESCE(session_id, '') AS session_id, "  # nosec B608
                            f"turn_sequence FROM runs WHERE {where}",  # nosec B608
                            params,
                        ).fetchall()
                        tombstones_created += self._record_trace_tombstones(
                            conn,
                            rows,
                            retired_at=retired_at,
                        )
                    conn.execute(
                        f"DELETE FROM {table} WHERE {where}",  # nosec B608
                        params,
                    )
                if table == "finalization_events":
                    (
                        paired_run_deletions,
                        pair_tombstones,
                    ) = self._delete_eligible_terminal_pairs(
                        conn,
                        cutoff=cutoff,
                        keep_last=keep_last,
                        retired_at=retired_at,
                    )
                    tombstones_created += pair_tombstones
                    count += paired_run_deletions
                elif table == "runs":
                    count += paired_run_deletions
                deleted[table] = {"deleted": count}
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
            "retired_open_runs": retired_open_runs,
            "tombstones_created": tombstones_created,
            "tombstones_permanent": True,
            "vacuumed": bool(vacuum and not dry_run),
            "db_size_before_bytes": before["db_size_bytes"],
            "db_size_after_bytes": after["db_size_bytes"],
            "wal_size_before_bytes": before["wal_size_bytes"],
            "wal_size_after_bytes": after["wal_size_bytes"],
            "tables": deleted,
            "remaining_tables": after["tables"],
        }
