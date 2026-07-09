"""Two-phase roster synchronization for Agency Runtime.

Remote or local agent definitions are never activated directly. They are first
parsed into candidate dictionaries, validated, written to quarantine, diffed
against the active roster, approved as a snapshot, and only then activated.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from agency_runtime.core.store.sqlite import Store

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#_-]*", re.IGNORECASE)
_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")
_METADATA_FIELDS = (
    "name",
    "division",
    "description",
    "source",
    "version",
    "prompt_path",
    "capabilities",
    "tool_affinity",
)


class RosterSyncError(RuntimeError):
    """Raised when roster sync cannot safely continue."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid(store: Store) -> str:
    return store._uuid()  # noqa: SLF001 - Store exposes no public UUID helper yet.


def _connect(store: Store):
    return store._connect()  # noqa: SLF001 - roster tables currently require direct SQL.


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return [str(item) for item in loaded if str(item).strip()]
        except Exception:
            return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _normalize_agent(agent: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(agent)
    slug = str(normalized.get("slug") or normalized.get("id") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug).strip("-._")
    normalized["slug"] = slug
    normalized.setdefault("name", slug.replace("-", " ").title() if slug else "")
    normalized.setdefault("description", "")
    normalized.setdefault("division", "general")
    normalized.setdefault("version", "1.0.0")
    normalized.setdefault("source", "")
    normalized.setdefault("prompt_path", "")
    for field in _LIST_FIELDS:
        normalized[field] = _json_list(normalized.get(field))
    if not normalized.get("categories"):
        normalized["categories"] = categorize_agent(normalized)
    body = str(
        normalized.get("prompt_body")
        or normalized.get("prompt")
        or normalized.get("body")
        or normalized.get("content")
        or ""
    )
    normalized["prompt_body"] = body
    normalized["content"] = str(normalized.get("content") or body or json.dumps(normalized, sort_keys=True))
    normalized["hash"] = str(normalized.get("hash") or _hash_text(normalized["content"]))
    return normalized


def parse_agent_file(content: str) -> dict[str, Any]:
    """Parse a JSON/YAML/Markdown agent file into a normalized dict."""

    text = content.strip()
    if not text:
        raise ValueError("empty agent file")

    data: dict[str, Any]
    body = text
    if text.startswith("{"):
        loaded = json.loads(text)
        if not isinstance(loaded, dict):
            raise ValueError("agent JSON must be an object")
        data = loaded
        body = str(loaded.get("prompt_body") or loaded.get("prompt") or loaded.get("content") or text)
    elif text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) < 3:
            raise ValueError("unterminated YAML front matter")
        loaded = yaml.safe_load(parts[1]) or {}
        if not isinstance(loaded, dict):
            raise ValueError("front matter must be a mapping")
        data = loaded
        body = parts[2].strip()
    elif re.match(r"^[\w-]+:\s", text):
        loaded = yaml.safe_load(text)
        if not isinstance(loaded, dict):
            raise ValueError("YAML agent file must be a mapping")
        data = loaded
        body = str(loaded.get("prompt_body") or loaded.get("prompt") or loaded.get("content") or text)
    else:
        heading = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), "")
        slug = re.sub(r"[^a-z0-9._-]+", "-", heading.lower()).strip("-._") if heading else ""
        data = {"slug": slug, "name": heading or "Imported Agent", "description": "Imported Markdown agent"}
        body = text

    data = dict(data)
    data["content"] = content
    data.setdefault("prompt_body", body)
    return _normalize_agent(data)


def _read_url(url: str) -> list[tuple[str, str]]:
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - user-controlled roster source by design.
            data = response.read().decode("utf-8")
        if data.lstrip().lower().startswith(("<!doctype html", "<html")):
            raise RosterSyncError("roster source returned HTML; use a raw file, local directory, or generated agents.json")
        return [(url, data)]

    path = Path(parsed.path if parsed.scheme == "file" else url).expanduser()
    if path.is_dir():
        items: list[tuple[str, str]] = []
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() in {".md", ".json", ".yaml", ".yml"} and child.is_file():
                items.append((str(child), child.read_text(encoding="utf-8")))
        return items
    if path.is_file():
        return [(str(path), path.read_text(encoding="utf-8"))]
    raise FileNotFoundError(f"roster source not found: {url}")


def download_from_source(url: str) -> list[dict[str, Any]]:
    """Download and parse candidates from an HTTP(S), file, or directory source."""

    candidates: list[dict[str, Any]] = []
    for origin, content in _read_url(url):
        stripped = content.strip()
        if stripped.startswith("["):
            loaded = json.loads(stripped)
            if not isinstance(loaded, list):
                raise ValueError(f"JSON roster at {origin} must be a list")
            for item in loaded:
                if not isinstance(item, dict):
                    raise ValueError(f"JSON roster item at {origin} is not an object")
                item = dict(item)
                item.setdefault("content", json.dumps(item, sort_keys=True))
                item.setdefault("source", url)
                item.setdefault("prompt_path", origin)
                candidates.append(_normalize_agent(item))
        else:
            agent = parse_agent_file(content)
            agent.setdefault("source", url)
            agent.setdefault("prompt_path", origin)
            candidates.append(agent)
    return candidates


def validate_agent(agent_dict: dict[str, Any]) -> tuple[bool, str]:
    """Validate an agent candidate shape and return ``(ok, reason)``."""

    agent = _normalize_agent(agent_dict)
    if not agent.get("slug") or not _SLUG_RE.match(agent["slug"]):
        return False, "slug must be 2-128 lowercase letters/digits plus dot, underscore, or dash"
    if not str(agent.get("name", "")).strip():
        return False, "name is required"
    if not str(agent.get("description", "")).strip():
        return False, "description is required"
    if not str(agent.get("prompt_body", "")).strip():
        return False, "prompt_body/content is required"
    return True, "ok"


def categorize_agent(agent: dict[str, Any]) -> list[str]:
    """Infer broad categories from an agent's metadata and prompt."""

    explicit = _json_list(agent.get("categories"))
    if explicit:
        return sorted(dict.fromkeys(item.lower() for item in explicit))

    text = " ".join(str(agent.get(key, "")) for key in ("slug", "name", "division", "description", "prompt_body"))
    tokens = set(_WORD_RE.findall(text.lower()))
    buckets = {
        "code": {"code", "developer", "engineering", "python", "javascript", "bug", "debug", "review"},
        "documentation": {"docs", "documentation", "writer", "writing", "readme", "runbook"},
        "planning": {"plan", "planning", "architect", "workflow", "orchestration", "strategy"},
        "research": {"research", "analysis", "market", "paper", "literature"},
        "operations": {"ops", "devops", "deploy", "runtime", "incident", "monitor"},
        "design": {"design", "ux", "ui", "visual", "frontend"},
    }
    categories = [name for name, words in buckets.items() if tokens & words]
    return categories or [str(agent.get("division") or "general").lower()]


def quarantine_candidate(agent: dict[str, Any], source_id: str, store: Store) -> str:
    """Write a validated candidate and its raw download record to quarantine."""

    normalized = _normalize_agent(agent)
    ok, reason = validate_agent(normalized)
    if not ok:
        raise ValueError(f"invalid agent {normalized.get('slug') or '<missing>'}: {reason}")

    conn = _connect(store)
    try:
        download_id = _uuid(store)
        candidate_id = _uuid(store)
        now = _now()
        content = normalized.get("content") or normalized.get("prompt_body", "")
        conn.execute(
            "INSERT INTO agent_downloads (id, source_id, slug, downloaded_at, hash, content, status) VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
            (download_id, source_id, normalized["slug"], now, normalized["hash"], content),
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
        conn.commit()
    finally:
        conn.close()
    store.record_import_event("candidate_quarantined", normalized["slug"], f"candidate_id={candidate_id}")
    return candidate_id


def _load_candidate_agents(
    store: Store,
    statuses: tuple[str, ...] = ("approved", "pending"),
    candidate_ids: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    conn = _connect(store)
    try:
        if candidate_ids is None:
            placeholders = ",".join("?" for _ in statuses)
            where = f"c.status IN ({placeholders})"
            params: tuple[Any, ...] = statuses
        else:
            if not candidate_ids:
                return []
            placeholders = ",".join("?" for _ in candidate_ids)
            where = f"c.id IN ({placeholders})"
            params = tuple(candidate_ids)
        cur = conn.execute(
            f"""
            SELECT c.*, d.content
            FROM agent_candidates c
            LEFT JOIN agent_downloads d ON d.id = c.download_id
            WHERE {where}
            ORDER BY CASE c.status WHEN 'approved' THEN 0 ELSE 1 END, c.quarantined_at DESC
            """,
            params,
        )
        latest: dict[str, dict[str, Any]] = {}
        for row in cur.fetchall():
            item = dict(row)
            content = str(item.get("content") or "")
            try:
                parsed = parse_agent_file(content) if content else {}
            except Exception:
                parsed = {}
            item = {**parsed, **item}
            item["description"] = str(item.get("description") or parsed.get("description") or "")
            item["categories"] = _json_list(item.get("categories") or parsed.get("categories"))
            item["capabilities"] = _json_list(item.get("capabilities") or parsed.get("capabilities"))
            item["tool_affinity"] = _json_list(item.get("tool_affinity") or parsed.get("tool_affinity"))
            item["prompt_body"] = str(parsed.get("prompt_body") or content)
            item["content"] = content
            latest.setdefault(item["slug"], item)
        return list(latest.values())
    finally:
        conn.close()


def _active_by_slug(store: Store) -> dict[str, dict[str, Any]]:
    return {agent["agent_slug"]: agent for agent in store.get_active_roster()}


def create_roster_diff(store: Store, candidate_ids: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    """Create a snapshot diff of quarantined/approved candidates vs active roster."""

    candidates = _load_candidate_agents(store, candidate_ids=candidate_ids)
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
        category_changes = {"from": old_categories, "to": new_categories} if old_categories != new_categories else None
        if prompt_changed or metadata_changes or category_changes:
            changed[slug] = {
                "prompt_body_changed": prompt_changed,
                "hash": {"from": current.get("hash"), "to": candidate.get("hash")},
                "metadata_changes": metadata_changes,
                "category_changes": category_changes,
            }
        else:
            unchanged.append(slug)

    for slug in active:
        if slug not in candidate_by_slug:
            removed.append(slug)

    snapshot_id = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": _now(),
        "approved": False,
        "candidate_ids": [str(agent.get("id")) for agent in candidates if agent.get("id")],
        "candidates": candidates,
        "diff": {
            "added": sorted(added),
            "removed": sorted(removed),
            "changed": changed,
            "unchanged": sorted(unchanged),
        },
    }
    conn = _connect(store)
    try:
        conn.execute(
            "INSERT INTO agent_snapshots (id, snapshot_id, created_at, agent_count, manifest, activated) VALUES (?, ?, ?, ?, ?, 0)",
            (_uuid(store), snapshot_id, _now(), len(candidates), json.dumps(manifest, sort_keys=True)),
        )
        conn.commit()
    finally:
        conn.close()
    return manifest


def _get_snapshot(store: Store, snapshot_id: str) -> dict[str, Any]:
    conn = _connect(store)
    try:
        cur = conn.execute("SELECT manifest FROM agent_snapshots WHERE snapshot_id = ?", (snapshot_id,))
        row = cur.fetchone()
        if row is None:
            raise KeyError(f"snapshot not found: {snapshot_id}")
        return json.loads(row["manifest"] or "{}")
    finally:
        conn.close()


def approve_snapshot(store: Store, snapshot_id: str) -> None:
    """Mark only the candidates captured by a roster snapshot as approved."""

    manifest = _get_snapshot(store, snapshot_id)
    manifest["approved"] = True
    candidate_ids = [str(item) for item in manifest.get("candidate_ids", []) if item]
    conn = _connect(store)
    try:
        conn.execute("UPDATE agent_snapshots SET manifest = ? WHERE snapshot_id = ?", (json.dumps(manifest, sort_keys=True), snapshot_id))
        if candidate_ids:
            placeholders = ",".join("?" for _ in candidate_ids)
            conn.execute(f"UPDATE agent_candidates SET status = 'approved' WHERE id IN ({placeholders})", candidate_ids)
        else:
            slugs = [str(agent.get("slug")) for agent in manifest.get("candidates", []) if agent.get("slug")]
            if slugs:
                placeholders = ",".join("?" for _ in slugs)
                conn.execute(
                    f"UPDATE agent_candidates SET status = 'approved' WHERE slug IN ({placeholders}) AND status = 'pending'",
                    slugs,
                )
        conn.commit()
    finally:
        conn.close()
    store.record_import_event("snapshot_approved", "", snapshot_id)


def activate_snapshot(store: Store, snapshot_id: str) -> None:
    """Activate all agents in an approved snapshot."""

    manifest = _get_snapshot(store, snapshot_id)
    if not manifest.get("approved"):
        raise RosterSyncError(f"snapshot {snapshot_id} must be approved before activation")
    candidates = [_normalize_agent(agent) for agent in manifest.get("candidates", [])]
    if not candidates:
        raise RosterSyncError(f"snapshot {snapshot_id} contains no agents to activate")
    candidate_ids = [str(item) for item in manifest.get("candidate_ids", []) if item]
    active_slugs = [agent["slug"] for agent in candidates]
    placeholders = ",".join("?" for _ in active_slugs)
    id_placeholders = ",".join("?" for _ in candidate_ids)
    conn = _connect(store)
    try:
        conn.execute(f"DELETE FROM agent_active WHERE agent_slug NOT IN ({placeholders})", active_slugs)
        conn.execute(f"DELETE FROM agent_categories WHERE agent_slug NOT IN ({placeholders})", active_slugs)
        for agent in candidates:
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
                    agent.get("version", "1.0.0"),
                    agent.get("hash", ""),
                    json.dumps(agent.get("categories", [])),
                    json.dumps(agent.get("capabilities", [])),
                    json.dumps(agent.get("tool_affinity", [])),
                    agent.get("prompt_path", ""),
                    _now(),
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO agent_versions (id, agent_slug, version, hash, content, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (_uuid(store), agent["slug"], agent.get("version", "1.0.0"), agent.get("hash", ""), agent.get("content", ""), _now()),
            )
            for category in _json_list(agent.get("categories")):
                conn.execute(
                    "INSERT OR IGNORE INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
                    (_uuid(store), agent["slug"], category),
                )
            if not candidate_ids:
                conn.execute("UPDATE agent_candidates SET status = 'activated' WHERE slug = ?", (agent["slug"],))
            conn.execute("UPDATE agent_downloads SET status = 'activated' WHERE slug = ?", (agent["slug"],))
        if candidate_ids:
            conn.execute(f"UPDATE agent_candidates SET status = 'activated' WHERE id IN ({id_placeholders})", candidate_ids)
        conn.execute("UPDATE agent_snapshots SET activated = 1 WHERE snapshot_id = ?", (snapshot_id,))
        conn.commit()
    finally:
        conn.close()
    store.record_import_event("snapshot_activated", "", snapshot_id)
