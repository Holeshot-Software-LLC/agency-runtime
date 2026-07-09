"""Quarantine manager for roster candidates.

Candidates downloaded from roster sources remain quarantined until an operator
approves them for a snapshot or rejects them. Activation is handled separately by
``agency_runtime.core.roster.sync``.
"""

from __future__ import annotations

import json
from typing import Any

from agency_runtime.core.store.sqlite import Store


def _connect(store: Store):
    return store._connect()  # noqa: SLF001 - Store has no public quarantine API yet.


def _now(store: Store) -> str:
    return store._now()  # noqa: SLF001


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return [str(item) for item in loaded]
        except Exception:
            return [part.strip() for part in value.split(",") if part.strip()]
    return [str(value)]


def list_quarantined(store: Store, status: str | None = None) -> list[dict[str, Any]]:
    """Return quarantined candidates, optionally filtered by status."""

    conn = _connect(store)
    try:
        sql = """
            SELECT c.*, d.content, d.downloaded_at, d.status AS download_status
            FROM agent_candidates c
            LEFT JOIN agent_downloads d ON d.id = c.download_id
        """
        params: tuple[str, ...] = ()
        if status:
            sql += " WHERE c.status = ?"
            params = (status,)
        else:
            sql += " WHERE c.status IN ('pending', 'approved', 'rejected')"
        sql += " ORDER BY c.quarantined_at DESC, c.slug ASC"
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

    for row in rows:
        row["categories"] = _json_list(row.get("categories"))
        row["capabilities"] = _json_list(row.get("capabilities"))
        row["tool_affinity"] = _json_list(row.get("tool_affinity"))
    return rows


def _set_status(store: Store, candidate_or_slug: str, status: str, reason: str = "") -> int:
    conn = _connect(store)
    try:
        cur = conn.execute(
            "UPDATE agent_candidates SET status = ? WHERE id = ? OR slug = ?",
            (status, candidate_or_slug, candidate_or_slug),
        )
        conn.execute(
            "UPDATE agent_downloads SET status = ? WHERE id IN (SELECT download_id FROM agent_candidates WHERE id = ? OR slug = ?)",
            (status, candidate_or_slug, candidate_or_slug),
        )
        affected = cur.rowcount
        conn.commit()
    finally:
        conn.close()
    if affected:
        store.record_import_event(f"candidate_{status}", candidate_or_slug, reason)
    return affected


def approve(store: Store, candidate_or_slug: str) -> bool:
    """Approve a quarantined candidate by candidate id or slug."""

    return _set_status(store, candidate_or_slug, "approved") > 0


def reject(store: Store, candidate_or_slug: str, reason: str = "") -> bool:
    """Reject a quarantined candidate by candidate id or slug."""

    return _set_status(store, candidate_or_slug, "rejected", reason) > 0
