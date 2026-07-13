"""Active-roster and immutable specialist-version persistence methods."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.store.projections import project_snapshot_summary

_JSON_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")
_MAX_ACTIVE_ROSTER_LIMIT = 10_000
_MAX_ACTIVE_ROSTER_CURSOR_BYTES = 1024


def _decode_json_list(value: object) -> list[Any]:
    """Normalize one SQLite JSON projection without trusting legacy data."""

    try:
        parsed = safe_load_bounded_json(
            value or "[]",
            maximum_bytes=1024 * 1024,
            maximum_depth=16,
            maximum_nodes=1_000,
        )
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


class RosterStoreMixin:
    """Roster-domain behavior composed into the canonical SQLite store."""

    # ── Roster ─────────────────────────────────────────────────────

    def add_agent_source(
        self, url: str, name: str = "", *, trusted_for_auto_approve: bool = False
    ) -> str:
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
                    (
                        source_id,
                        url,
                        name or url,
                        self._now(),
                        1 if trusted_for_auto_approve else 0,
                    ),
                )
            conn.commit()
            return source_id
        finally:
            conn.close()

    def list_agent_sources(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM agent_sources WHERE enabled = 1 ORDER BY added_at DESC"
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def activate_agent(self, agent: dict[str, Any]) -> None:
        content = str(agent.get("prompt_body") or agent.get("content") or agent.get("body") or "")
        if not content.strip():
            identity = str(agent.get("name") or agent.get("slug") or "specialist")
            description = str(agent.get("description") or "Apply your named specialty to the task.")
            content = f"You are the {identity} specialist. {description}".strip()
        version = str(agent.get("version") or "1.0.0")
        content_hash = str(agent.get("hash") or hashlib.sha256(content.encode("utf-8")).hexdigest())
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing_version = conn.execute(
                "SELECT id, hash, content FROM agent_versions WHERE agent_slug = ? AND version = ?",
                (agent["slug"], version),
            ).fetchone()
            if existing_version is not None and (
                str(existing_version["hash"] or "") != content_hash
                or str(existing_version["content"] or "") != content
            ):
                raise ValueError(f"immutable agent version conflict for {agent['slug']}@{version}")
            if existing_version is None:
                conn.execute(
                    "INSERT INTO agent_versions "
                    "(id, agent_slug, version, hash, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        self._uuid(),
                        agent["slug"],
                        version,
                        content_hash,
                        content,
                        self._now(),
                    ),
                )
            conn.execute(
                "INSERT OR REPLACE INTO agent_active "
                "(id, agent_slug, name, division, description, source, version, hash, "
                "categories, capabilities, tool_affinity, prompt_path, activated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    agent["slug"],
                    agent.get("name", ""),
                    agent.get("division", ""),
                    agent.get("description", ""),
                    agent.get("source", ""),
                    version,
                    content_hash,
                    json.dumps(agent.get("categories", [])),
                    json.dumps(agent.get("capabilities", [])),
                    json.dumps(agent.get("tool_affinity", [])),
                    agent.get("prompt_path", ""),
                    self._now(),
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert_roster_entry(self, agent: dict[str, Any]) -> None:
        """Persist one active roster entry through the immutable-version boundary."""

        self.activate_agent(agent)

    def get_active_roster(
        self,
        *,
        limit: int | None = None,
        after: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return a stable active-roster page ordered after an optional slug cursor."""
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int):
                raise TypeError("limit must be an integer or None")
            if not 1 <= limit <= _MAX_ACTIVE_ROSTER_LIMIT:
                raise ValueError(f"limit must be between 1 and {_MAX_ACTIVE_ROSTER_LIMIT}")
        if after is not None:
            if not isinstance(after, str):
                raise TypeError("after must be a string or None")
            if not after or len(after.encode("utf-8")) > _MAX_ACTIVE_ROSTER_CURSOR_BYTES:
                raise ValueError(
                    f"after must be between 1 and {_MAX_ACTIVE_ROSTER_CURSOR_BYTES} UTF-8 bytes"
                )
        conn = self._connect()
        try:
            if after is None and limit is None:
                cur = conn.execute("SELECT * FROM agent_active ORDER BY agent_slug")
            elif after is None:
                cur = conn.execute(
                    "SELECT * FROM agent_active ORDER BY agent_slug LIMIT ?",
                    (limit,),
                )
            elif limit is None:
                cur = conn.execute(
                    "SELECT * FROM agent_active WHERE agent_slug > ? ORDER BY agent_slug",
                    (after,),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM agent_active WHERE agent_slug > ? ORDER BY agent_slug LIMIT ?",
                    (after, limit),
                )
            agents = []
            for row in cur.fetchall():
                d = dict(row)
                for field in _JSON_LIST_FIELDS:
                    d[field] = _decode_json_list(d.get(field))
                agents.append(d)
            return agents
        finally:
            conn.close()

    def count_active_roster(self) -> int:
        """Return the active roster cardinality without materializing its rows."""
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) AS count FROM agent_active").fetchone()
            return int(row["count"])
        finally:
            conn.close()

    def get_roster_entry(self, slug: str) -> dict[str, Any] | None:
        """Return one active roster entry without exposing versioned prompt content."""

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = ? LIMIT 1",
                (slug,),
            ).fetchone()
            if row is None:
                return None
            entry = dict(row)
            for field in _JSON_LIST_FIELDS:
                entry[field] = _decode_json_list(entry.get(field))
            return entry
        finally:
            conn.close()

    def get_active_roster_as_catalog(self) -> list[dict[str, Any]]:
        """Return active roster in selector-compatible format."""
        agents = self.get_active_roster()
        return [
            {
                "slug": agent["agent_slug"],
                "name": agent.get("name", ""),
                "description": agent.get("description", ""),
                "division": agent.get("division", ""),
                "categories": agent.get("categories", []),
                "capabilities": agent.get("capabilities", []),
            }
            for agent in agents
        ]

    def get_specialist_prompt(
        self,
        slug: str,
        *,
        max_chars: int = 65_536,
    ) -> dict[str, Any] | None:
        """Return one active specialist with its versioned bounded prompt."""
        bounded = max(1, min(int(max_chars), 262_144))
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT a.*, v.content AS prompt_body, v.hash AS prompt_hash "
                "FROM agent_active AS a "
                "LEFT JOIN agent_versions AS v "
                "ON v.agent_slug = a.agent_slug AND v.version = a.version "
                "WHERE a.agent_slug = ? LIMIT 1",
                (slug,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            for field in _JSON_LIST_FIELDS:
                result[field] = _decode_json_list(result.get(field))
            content = str(result.get("prompt_body") or "")
            result["prompt_body"] = content[:bounded]
            result["prompt_truncated"] = len(content) > bounded
            return result
        finally:
            conn.close()

    def deactivate_agent(self, slug: str) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM agent_active WHERE agent_slug = ?", (slug,))
            conn.commit()
        finally:
            conn.close()

    def create_snapshot(self, snapshot_id: str, manifest: dict[str, Any]) -> None:
        snapshot_agent_count = len(manifest.get("candidates", []))
        summary = project_snapshot_summary(manifest)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_snapshots "
                "(id, snapshot_id, created_at, agent_count, manifest, activated, "
                "approved, added_count, changed_count, removed_count) "
                "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    snapshot_id,
                    self._now(),
                    snapshot_agent_count,
                    json.dumps(manifest),
                    int(bool(summary["approved"])),
                    int(summary["added"]),
                    int(summary["changed"]),
                    int(summary["removed"]),
                ),
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
