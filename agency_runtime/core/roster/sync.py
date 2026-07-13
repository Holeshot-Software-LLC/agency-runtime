"""Two-phase quarantine, approval, and activation for roster candidates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from agency_runtime.core.roster.ingress import (
    _LIST_FIELDS,
    _METADATA_FIELDS,
    MAX_AGENT_CONTENT_BYTES,
    MAX_SHORT_TEXT_BYTES,
    MAX_SNAPSHOT_MANIFEST_BYTES,
    MAX_SOURCE_CANDIDATES,
    MAX_TOTAL_SOURCE_BYTES,
    RosterSyncError,
    _hash_text,
    _json_list,
    _load_json,
    _normalize_agent,
    _require_bounded_text,
    _utf8_size,
    categorize_agent,
    download_from_source,
    parse_agent_file,
    validate_agent,
)
from agency_runtime.core.store.projections import project_snapshot_summary
from agency_runtime.core.store.sqlite import Store

__all__ = [
    "RosterSyncError",
    "activate_snapshot",
    "approve_snapshot",
    "categorize_agent",
    "create_roster_diff",
    "download_from_source",
    "parse_agent_file",
    "quarantine_candidate",
    "validate_agent",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid(store: Store) -> str:
    return store._uuid()


def _connect(store: Store):
    return store._connect()


def quarantine_candidate(agent: dict[str, Any], source_id: str, store: Store) -> str:
    """Write a validated candidate and its raw download record to quarantine."""

    normalized = _normalize_agent(agent)
    ok, reason = validate_agent(normalized)
    if not ok:
        raise ValueError(f"invalid agent {normalized.get('slug') or '<missing>'}: {reason}")
    source_id = _require_bounded_text(source_id, MAX_SHORT_TEXT_BYTES, "source id")

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        source = conn.execute(
            "SELECT enabled FROM agent_sources WHERE id = ?", (source_id,)
        ).fetchone()
        if source is None:
            raise RosterSyncError("cannot quarantine a candidate for an unknown source")
        if not int(source["enabled"] or 0):
            raise RosterSyncError("cannot quarantine a candidate for a disabled source")
        download_id = _uuid(store)
        candidate_id = _uuid(store)
        now = _now()
        content = normalized.get("content") or normalized.get("prompt_body", "")
        conn.execute(
            "INSERT INTO agent_downloads (id, source_id, slug, downloaded_at, hash, content, status) VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
            (
                download_id,
                source_id,
                normalized["slug"],
                now,
                normalized["hash"],
                content,
            ),
        )
        conn.execute(
            "INSERT INTO agent_candidates (id, download_id, slug, name, division, categories, capabilities, tool_affinity, prompt_path, source, version, hash, status, quarantined_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (
                candidate_id,
                download_id,
                normalized["slug"],
                normalized.get("name", ""),
                normalized.get("division", ""),
                json.dumps(normalized.get("categories", [])),
                json.dumps(normalized.get("capabilities", [])),
                json.dumps(normalized.get("tool_affinity", [])),
                normalized.get("prompt_path", ""),
                normalized.get("source", ""),
                normalized.get("version", "1.0.0"),
                normalized["hash"],
                now,
            ),
        )
        _record_import_event(
            conn,
            store,
            "candidate_quarantined",
            normalized["slug"],
            f"candidate_id={candidate_id}",
            now=now,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return candidate_id


def _record_import_event(
    conn: Any,
    store: Store,
    event_type: str,
    agent_slug: str,
    detail: str,
    *,
    now: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO agent_import_events "
        "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (_uuid(store), event_type, agent_slug, detail, now or _now()),
    )


def _load_candidate_agents(
    store: Store,
    candidate_ids: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    requested_ids: list[str] | None = None
    if candidate_ids is not None:
        requested_ids = [
            _require_bounded_text(item, MAX_SHORT_TEXT_BYTES, "candidate id")
            for item in candidate_ids
        ]
        if len(requested_ids) > MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(
                f"snapshot contains more than {MAX_SOURCE_CANDIDATES} candidate ids"
            )
        if len(set(requested_ids)) != len(requested_ids):
            raise RosterSyncError("snapshot candidate ids must be unique")
    conn = _connect(store)
    try:
        if requested_ids is None:
            cur = conn.execute(
                """
                SELECT c.*, d.content, d.hash AS download_hash,
                       d.status AS download_status
                FROM agent_candidates c
                LEFT JOIN agent_downloads d ON d.id = c.download_id
                WHERE c.status IN ('approved', 'pending')
                ORDER BY CASE c.status WHEN 'approved' THEN 0 ELSE 1 END,
                         c.quarantined_at DESC
                LIMIT ?
                """,
                (MAX_SOURCE_CANDIDATES + 1,),
            )
        else:
            if not requested_ids:
                return []
            conn.execute(
                "CREATE TEMP TABLE requested_roster_candidates (id TEXT PRIMARY KEY) WITHOUT ROWID"
            )
            conn.executemany(
                "INSERT INTO requested_roster_candidates (id) VALUES (?)",
                ((item,) for item in requested_ids),
            )
            cur = conn.execute(
                """
                SELECT c.*, d.content, d.hash AS download_hash,
                       d.status AS download_status
                FROM requested_roster_candidates requested
                JOIN agent_candidates c ON c.id = requested.id
                LEFT JOIN agent_downloads d ON d.id = c.download_id
                WHERE c.status IN ('approved', 'pending')
                ORDER BY CASE c.status WHEN 'approved' THEN 0 ELSE 1 END,
                         c.quarantined_at DESC
                LIMIT ?
                """,
                (MAX_SOURCE_CANDIDATES + 1,),
            )
        rows = cur.fetchall()
        if len(rows) > MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(f"snapshot contains more than {MAX_SOURCE_CANDIDATES} candidates")
        if requested_ids is not None:
            found_ids = {str(row["id"]) for row in rows}
            missing = [item for item in requested_ids if item not in found_ids]
            if missing:
                raise RosterSyncError(
                    "snapshot candidate ids are missing or no longer pending/approved"
                )
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = dict(row)
            content = _require_bounded_text(
                item.get("content"),
                MAX_AGENT_CONTENT_BYTES,
                f"quarantined agent {item.get('slug') or '<missing>'} content",
            )
            try:
                parsed = parse_agent_file(content) if content else {}
            except RosterSyncError:
                raise
            except Exception as exc:
                raise RosterSyncError(
                    f"quarantined agent {item.get('slug') or '<missing>'} cannot be parsed"
                ) from exc
            item = {**parsed, **item}
            item["description"] = str(item.get("description") or parsed.get("description") or "")
            item["categories"] = _json_list(
                item.get("categories") or parsed.get("categories"),
                label="agent categories",
            )
            item["capabilities"] = _json_list(
                item.get("capabilities") or parsed.get("capabilities"),
                label="agent capabilities",
            )
            item["tool_affinity"] = _json_list(
                item.get("tool_affinity") or parsed.get("tool_affinity"),
                label="agent tool affinity",
            )
            item["prompt_body"] = str(parsed.get("prompt_body") or content)
            item["content"] = content
            normalized = _normalize_agent(item)
            if str(item.get("hash") or "") != normalized["hash"]:
                raise RosterSyncError(
                    f"quarantined agent {normalized['slug']} content hash does not match"
                )
            if str(item.get("download_hash") or "") != normalized["hash"]:
                raise RosterSyncError(
                    f"quarantined download for {normalized['slug']} content hash does not match"
                )
            normalized.pop("download_hash", None)
            normalized.pop("download_status", None)
            if requested_ids is not None and normalized["slug"] in latest:
                raise RosterSyncError(
                    f"snapshot contains duplicate agent slug {normalized['slug']}"
                )
            latest.setdefault(normalized["slug"], normalized)
        return list(latest.values())
    finally:
        conn.close()


def _active_by_slug(store: Store) -> dict[str, dict[str, Any]]:
    return {agent["agent_slug"]: agent for agent in store.get_active_roster()}


def _active_fingerprint(active: Mapping[str, Mapping[str, Any]]) -> str:
    rows: list[dict[str, Any]] = []
    for slug, agent in sorted(active.items()):
        rows.append(
            {
                "slug": slug,
                "name": str(agent.get("name") or ""),
                "division": str(agent.get("division") or ""),
                "description": str(agent.get("description") or ""),
                "source": str(agent.get("source") or ""),
                "version": str(agent.get("version") or ""),
                "hash": str(agent.get("hash") or ""),
                "categories": sorted(
                    _json_list(agent.get("categories"), label="active categories")
                ),
                "capabilities": sorted(
                    _json_list(agent.get("capabilities"), label="active capabilities")
                ),
                "tool_affinity": sorted(
                    _json_list(agent.get("tool_affinity"), label="active tool affinity")
                ),
                "prompt_path": str(agent.get("prompt_path") or ""),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return _hash_text(canonical)


def _active_from_connection(conn: Any) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT * FROM agent_active ORDER BY agent_slug").fetchall()
    return {str(row["agent_slug"]): dict(row) for row in rows}


def create_roster_diff(
    store: Store, candidate_ids: list[str] | tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Create a snapshot diff of quarantined/approved candidates vs active roster."""

    candidates = _load_candidate_agents(store, candidate_ids=candidate_ids)
    if len(candidates) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(
            f"snapshot contains {len(candidates)} candidates; limit is {MAX_SOURCE_CANDIDATES}"
        )
    candidate_content_bytes = sum(
        _utf8_size(str(agent.get("content") or ""))
        + _utf8_size(str(agent.get("prompt_body") or ""))
        for agent in candidates
    )
    if candidate_content_bytes > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(
            f"snapshot candidate content is {candidate_content_bytes} bytes; "
            f"limit is {MAX_TOTAL_SOURCE_BYTES} bytes"
        )
    active = _active_by_slug(store)
    candidate_by_slug = {agent["slug"]: agent for agent in candidates}
    added: list[str] = []
    removed: list[str] = []
    changed: dict[str, dict[str, Any]] = {}
    unchanged: list[str] = []

    for slug, candidate in candidate_by_slug.items():
        current = active.get(slug)
        if current is None:
            added.append(slug)
            continue
        prompt_changed = candidate.get("hash") != current.get("hash")
        metadata_changes = {
            field: {"from": current.get(field), "to": candidate.get(field)}
            for field in _METADATA_FIELDS
            if current.get(field) != candidate.get(field)
        }
        old_categories = sorted(_json_list(current.get("categories")))
        new_categories = sorted(_json_list(candidate.get("categories")))
        category_changes = (
            {"from": old_categories, "to": new_categories}
            if old_categories != new_categories
            else None
        )
        if prompt_changed or metadata_changes or category_changes:
            changed[slug] = {
                "prompt_body_changed": prompt_changed,
                "hash": {"from": current.get("hash"), "to": candidate.get("hash")},
                "metadata_changes": metadata_changes,
                "category_changes": category_changes,
            }
        else:
            unchanged.append(slug)

    removed.extend(slug for slug in active if slug not in candidate_by_slug)

    snapshot_id = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": _now(),
        "approved": False,
        "active_basis": _active_fingerprint(active),
        "candidate_ids": [str(agent.get("id")) for agent in candidates if agent.get("id")],
        "candidates": candidates,
        "diff": {
            "added": sorted(added),
            "removed": sorted(removed),
            "changed": changed,
            "unchanged": sorted(unchanged),
        },
    }
    try:
        manifest_json = json.dumps(manifest, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RosterSyncError("snapshot manifest is not JSON serializable") from exc
    manifest_size = _utf8_size(manifest_json)
    if manifest_size > MAX_SNAPSHOT_MANIFEST_BYTES:
        raise RosterSyncError(
            f"snapshot manifest is {manifest_size} bytes; limit is {MAX_SNAPSHOT_MANIFEST_BYTES} bytes"
        )

    created_at = manifest["created_at"]
    summary = project_snapshot_summary(manifest)
    conn = _connect(store)
    try:
        conn.execute(
            "INSERT INTO agent_snapshots "
            "(id, snapshot_id, created_at, agent_count, manifest, activated, "
            "approved, added_count, changed_count, removed_count) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
            (
                _uuid(store),
                snapshot_id,
                created_at,
                len(candidates),
                manifest_json,
                int(bool(summary["approved"])),
                int(summary["added"]),
                int(summary["changed"]),
                int(summary["removed"]),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return manifest


def _snapshot_manifest_lists(
    value: Any,
    *,
    snapshot_id: str,
    agent_count: int,
) -> tuple[dict[str, Any], list[Any], list[Any]]:
    if not isinstance(value, dict):
        raise RosterSyncError(f"snapshot {snapshot_id} manifest must be an object")
    if value.get("snapshot_id") != snapshot_id:
        raise RosterSyncError(f"snapshot {snapshot_id} manifest identity does not match")
    if not isinstance(value.get("approved"), bool):
        raise RosterSyncError(f"snapshot {snapshot_id} approval state is invalid")
    raw_candidates = value.get("candidates")
    raw_ids = value.get("candidate_ids")
    if not isinstance(raw_candidates, list) or not isinstance(raw_ids, list):
        raise RosterSyncError(f"snapshot {snapshot_id} candidate manifest is invalid")
    if len(raw_candidates) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(
            f"snapshot contains {len(raw_candidates)} candidates; limit is {MAX_SOURCE_CANDIDATES}"
        )
    if agent_count != len(raw_candidates):
        raise RosterSyncError(f"snapshot {snapshot_id} agent count does not match its manifest")
    return value, raw_candidates, raw_ids


def _validated_manifest_candidate(
    raw_candidate: Any,
    *,
    snapshot_id: str,
) -> tuple[dict[str, Any], str, int]:
    if not isinstance(raw_candidate, dict):
        raise RosterSyncError(f"snapshot {snapshot_id} contains a non-object candidate")
    supplied_hash = str(raw_candidate.get("hash") or "")
    supplied_slug = str(raw_candidate.get("slug") or "")
    candidate = _normalize_agent(raw_candidate)
    ok, reason = validate_agent(candidate)
    if not ok:
        raise RosterSyncError(
            f"snapshot {snapshot_id} contains invalid agent "
            f"{candidate.get('slug') or '<missing>'}: {reason}"
        )
    if supplied_slug != candidate["slug"] or supplied_hash != candidate["hash"]:
        raise RosterSyncError(
            f"snapshot {snapshot_id} candidate identity or content hash does not match"
        )
    candidate_id = _require_bounded_text(
        candidate.get("id"), MAX_SHORT_TEXT_BYTES, "snapshot candidate id"
    )
    if not candidate_id:
        raise RosterSyncError(f"snapshot {snapshot_id} candidate id is missing")
    content_bytes = _utf8_size(candidate["content"]) + _utf8_size(candidate["prompt_body"])
    return candidate, candidate_id, content_bytes


def _validated_manifest_candidates(
    raw_candidates: Sequence[Any],
    *,
    snapshot_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    candidate_ids: list[str] = []
    content_bytes = 0
    for raw_candidate in raw_candidates:
        candidate, candidate_id, candidate_bytes = _validated_manifest_candidate(
            raw_candidate,
            snapshot_id=snapshot_id,
        )
        candidate_ids.append(candidate_id)
        candidates.append(candidate)
        content_bytes += candidate_bytes
    if content_bytes > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(
            f"snapshot candidate content is {content_bytes} bytes; "
            f"limit is {MAX_TOTAL_SOURCE_BYTES} bytes"
        )
    return candidates, candidate_ids


def _validate_manifest_candidate_identity(
    candidates: Sequence[dict[str, Any]],
    candidate_ids: list[str],
    raw_ids: Sequence[Any],
    *,
    snapshot_id: str,
) -> None:
    manifest_ids = [
        _require_bounded_text(item, MAX_SHORT_TEXT_BYTES, "snapshot candidate id")
        for item in raw_ids
    ]
    if manifest_ids != candidate_ids:
        raise RosterSyncError(f"snapshot {snapshot_id} candidate ids do not match its candidates")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise RosterSyncError(f"snapshot {snapshot_id} contains duplicate candidate ids")
    slugs = [candidate["slug"] for candidate in candidates]
    if len(set(slugs)) != len(slugs):
        raise RosterSyncError(f"snapshot {snapshot_id} contains duplicate agents")


def _validate_manifest_active_basis(value: Mapping[str, Any], snapshot_id: str) -> None:
    active_basis = value.get("active_basis")
    if active_basis is not None and not re.fullmatch(r"[a-f0-9]{64}", str(active_basis)):
        raise RosterSyncError(f"snapshot {snapshot_id} active basis is invalid")


def _validated_snapshot_manifest(
    value: Any,
    *,
    snapshot_id: str,
    agent_count: int,
) -> dict[str, Any]:
    manifest, raw_candidates, raw_ids = _snapshot_manifest_lists(
        value,
        snapshot_id=snapshot_id,
        agent_count=agent_count,
    )
    candidates, candidate_ids = _validated_manifest_candidates(
        raw_candidates,
        snapshot_id=snapshot_id,
    )
    _validate_manifest_candidate_identity(
        candidates,
        candidate_ids,
        raw_ids,
        snapshot_id=snapshot_id,
    )
    _validate_manifest_active_basis(manifest, snapshot_id)
    return {**manifest, "candidate_ids": candidate_ids, "candidates": candidates}


def _snapshot_from_connection(conn: Any, snapshot_id: str) -> tuple[dict[str, Any], bool]:
    snapshot_id = _require_bounded_text(snapshot_id, MAX_SHORT_TEXT_BYTES, "snapshot id")
    row = conn.execute(
        "SELECT manifest, agent_count, activated FROM agent_snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"snapshot not found: {snapshot_id}")
    manifest_text = _require_bounded_text(
        row["manifest"] or "", MAX_SNAPSHOT_MANIFEST_BYTES, "snapshot manifest"
    )
    manifest = _load_json(manifest_text, f"snapshot {snapshot_id} manifest")
    agent_count = row["agent_count"]
    activated = row["activated"]
    if isinstance(agent_count, bool) or not isinstance(agent_count, int) or agent_count < 0:
        raise RosterSyncError(f"snapshot {snapshot_id} agent count is invalid")
    if isinstance(activated, bool) or not isinstance(activated, int) or activated not in {0, 1}:
        raise RosterSyncError(f"snapshot {snapshot_id} activation state is invalid")
    validated = _validated_snapshot_manifest(
        manifest,
        snapshot_id=snapshot_id,
        agent_count=agent_count,
    )
    return validated, bool(activated)


def _candidate_records(conn: Any, candidate_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS snapshot_candidate_ids (id TEXT PRIMARY KEY) WITHOUT ROWID"
    )
    conn.execute("DELETE FROM snapshot_candidate_ids")
    conn.executemany(
        "INSERT INTO snapshot_candidate_ids (id) VALUES (?)",
        ((item,) for item in candidate_ids),
    )
    rows = conn.execute(
        "SELECT c.*, d.content AS download_content, d.hash AS download_hash, "
        "d.status AS download_status "
        "FROM snapshot_candidate_ids requested "
        "JOIN agent_candidates c ON c.id = requested.id "
        "LEFT JOIN agent_downloads d ON d.id = c.download_id"
    ).fetchall()
    return {str(row["id"]): dict(row) for row in rows}


def _assert_candidate_records(
    conn: Any,
    candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_statuses: frozenset[str],
) -> None:
    candidate_ids = [str(candidate["id"]) for candidate in candidates]
    records = _candidate_records(conn, candidate_ids)
    if set(records) != set(candidate_ids):
        raise RosterSyncError("snapshot candidate records are missing")
    for candidate in candidates:
        candidate_id = str(candidate["id"])
        record = records[candidate_id]
        if str(record.get("status") or "") not in allowed_statuses:
            raise RosterSyncError(f"snapshot candidate {candidate_id} is not in an allowed state")
        candidate_status = str(record.get("status") or "")
        expected_download_status = "activated" if candidate_status == "activated" else "quarantined"
        if str(record.get("download_status") or "") != expected_download_status:
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} download is not in an allowed state"
            )
        scalar_fields = (
            "download_id",
            "slug",
            "name",
            "division",
            "prompt_path",
            "source",
            "version",
            "hash",
        )
        if any(
            str(record.get(field) or "") != str(candidate.get(field) or "")
            for field in scalar_fields
        ):
            raise RosterSyncError(f"snapshot candidate {candidate_id} no longer matches quarantine")
        for field in _LIST_FIELDS:
            if _json_list(record.get(field), label=f"candidate {field}") != list(
                candidate.get(field) or []
            ):
                raise RosterSyncError(
                    f"snapshot candidate {candidate_id} no longer matches quarantine"
                )
        content = str(candidate.get("content") or "")
        if str(record.get("download_content") or "") != content or str(
            record.get("download_hash") or ""
        ) != _hash_text(content):
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} download content no longer matches"
            )


def _serialized_manifest(manifest: Mapping[str, Any]) -> str:
    try:
        value = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise RosterSyncError("snapshot manifest is not JSON serializable") from exc
    size = _utf8_size(value)
    if size > MAX_SNAPSHOT_MANIFEST_BYTES:
        raise RosterSyncError(
            f"snapshot manifest is {size} bytes; limit is {MAX_SNAPSHOT_MANIFEST_BYTES} bytes"
        )
    return value


def approve_snapshot(store: Store, snapshot_id: str) -> None:
    """Mark only the candidates captured by a roster snapshot as approved."""

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        manifest, activated = _snapshot_from_connection(conn, snapshot_id)
        if activated:
            raise RosterSyncError(f"snapshot {snapshot_id} is already activated")
        candidates = manifest["candidates"]
        if not candidates:
            raise RosterSyncError(f"snapshot {snapshot_id} contains no agents to approve")
        if manifest["approved"]:
            _assert_candidate_records(conn, candidates, allowed_statuses=frozenset({"approved"}))
            conn.commit()
            return
        _assert_candidate_records(conn, candidates, allowed_statuses=frozenset({"pending"}))
        manifest["approved"] = True
        conn.execute(
            "UPDATE agent_snapshots SET manifest = ?, approved = 1 WHERE snapshot_id = ?",
            (_serialized_manifest(manifest), snapshot_id),
        )
        conn.executemany(
            "UPDATE agent_candidates SET status = 'approved' WHERE id = ? AND status = 'pending'",
            ((candidate["id"],) for candidate in candidates),
        )
        _record_import_event(conn, store, "snapshot_approved", "", snapshot_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def activate_snapshot(store: Store, snapshot_id: str) -> None:
    """Activate all agents in an approved snapshot."""

    conn = _connect(store)
    try:
        # Lock before the immutable-version preflight. No active roster or
        # snapshot state is changed unless every candidate can be installed.
        conn.execute("BEGIN IMMEDIATE")
        manifest, previously_activated = _snapshot_from_connection(conn, snapshot_id)
        if not manifest["approved"]:
            raise RosterSyncError(f"snapshot {snapshot_id} must be approved before activation")
        candidates = manifest["candidates"]
        if not candidates:
            raise RosterSyncError(f"snapshot {snapshot_id} contains no agents to activate")
        _assert_candidate_records(
            conn,
            candidates,
            allowed_statuses=frozenset({"approved", "activated"}),
        )
        current_active = _active_from_connection(conn)
        current_fingerprint = _active_fingerprint(current_active)
        target_active = {candidate["slug"]: candidate for candidate in candidates}
        target_fingerprint = _active_fingerprint(target_active)
        active_basis = manifest.get("active_basis")
        if previously_activated and current_fingerprint == target_fingerprint:
            conn.commit()
            return
        if active_basis is not None and current_fingerprint != active_basis:
            raise RosterSyncError(
                f"snapshot {snapshot_id} was reviewed against a different active roster; "
                "create and approve a new diff"
            )
        existing_versions: set[tuple[str, str]] = set()
        for agent in candidates:
            version = str(agent.get("version") or "1.0.0")
            row = conn.execute(
                "SELECT hash, content FROM agent_versions WHERE agent_slug = ? AND version = ?",
                (agent["slug"], version),
            ).fetchone()
            if row is None:
                continue
            existing_versions.add((agent["slug"], version))
            existing_hash = str(row["hash"] or "")
            existing_content = str(row["content"] or "")
            candidate_hash = str(agent.get("hash") or "")
            candidate_content = str(agent.get("content") or "")
            if (
                existing_hash != candidate_hash
                or existing_content != candidate_content
                or existing_hash != _hash_text(existing_content)
            ):
                raise RosterSyncError(
                    f"refusing to replace immutable agent version "
                    f"{agent['slug']}@{version}: existing hash {existing_hash}, "
                    f"candidate hash {candidate_hash}"
                )

        # The snapshot is a complete roster, so a full transactional rebuild is
        # both simpler and immune to variable-limit or identifier-list bugs.
        conn.execute("DELETE FROM agent_active")
        # Categories are a complete projection of the activated snapshot. A
        # per-slug upsert would retain categories removed by a newer version.
        conn.execute("DELETE FROM agent_categories")
        for agent in candidates:
            version = str(agent.get("version") or "1.0.0")
            conn.execute(
                "INSERT OR REPLACE INTO agent_active "
                "(id, agent_slug, name, division, description, source, version, hash, categories, capabilities, tool_affinity, prompt_path, activated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _uuid(store),
                    agent["slug"],
                    agent.get("name", ""),
                    agent.get("division", ""),
                    agent.get("description", ""),
                    agent.get("source", ""),
                    version,
                    agent.get("hash", ""),
                    json.dumps(agent.get("categories", [])),
                    json.dumps(agent.get("capabilities", [])),
                    json.dumps(agent.get("tool_affinity", [])),
                    agent.get("prompt_path", ""),
                    _now(),
                ),
            )
            if (agent["slug"], version) not in existing_versions:
                conn.execute(
                    "INSERT INTO agent_versions (id, agent_slug, version, hash, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        _uuid(store),
                        agent["slug"],
                        version,
                        agent.get("hash", ""),
                        agent.get("content", ""),
                        _now(),
                    ),
                )
            for category in _json_list(agent.get("categories")):
                conn.execute(
                    "INSERT OR IGNORE INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
                    (_uuid(store), agent["slug"], category),
                )
        conn.executemany(
            "UPDATE agent_candidates SET status = 'activated' WHERE id = ?",
            ((candidate["id"],) for candidate in candidates),
        )
        conn.executemany(
            "UPDATE agent_downloads SET status = 'activated' WHERE id = ?",
            ((candidate["download_id"],) for candidate in candidates),
        )
        conn.execute(
            "UPDATE agent_snapshots SET activated = 1 WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        _record_import_event(conn, store, "snapshot_activated", "", snapshot_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
