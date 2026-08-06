"""Bounded, credential-free projections for dashboard operational views.

The dashboard consumes active roster metadata and immutable audit evidence, but
it must never materialize specialist prompt bodies, provider secrets, or free
form operator notes.  Keeping that policy in one module makes the HTTP and UI
surfaces small and gives non-browser callers the same safe projection.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Container, Mapping, Sequence
from functools import lru_cache
from typing import Any

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import AgencyConfig, ProviderEntry, _is_loopback_http_url
from agency_runtime.core.preflight_failure import PREFLIGHT_FAILURE_RECEIPT_SCHEMA
from agency_runtime.core.roster.bundled import bundled_manifest
from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.roster.review import latest_candidate_audit_from_connection
from agency_runtime.core.roster.revisions import (
    ROUTING_LIST_METADATA_FIELDS,
    ROUTING_SCALAR_METADATA_FIELDS,
    decode_revision_metadata,
)
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.roster.sync import remediation_queue_snapshot
from agency_runtime.core.selector.judge import inference_is_configured
from agency_runtime.core.store.sqlite import Store

MAX_OPERATIONAL_ROSTER_RESULTS = 100
MAX_REVISION_HISTORY = 5
MAX_REVIEW_RESULTS = 50
MAX_RECENT_FAILURES = 25
_MAX_FILTER_BYTES = 256
_FILTER_FIELDS = frozenset(
    {"query", "division", "capability", "authority", "host", "platform", "tool"}
)
_CANDIDATE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}\Z")
_FAILURE_STATES = frozenset(
    {
        "cancelled",
        "degraded",
        "error",
        "failed",
        "failure",
        "preflight_failed",
        "timed_out",
        "timeout",
    }
)
_SUCCESS_STATES = frozenset({"applied", "completed", "inferred", "ok", "success"})


def _preflight_inference_applied(record: Mapping[str, Any]) -> bool:
    """Whether every provider attempt in one preflight failure succeeded.

    A preflight failure is not evidence about inference unless inference is
    what failed.  Recorded attempts are the only thing that can distinguish
    the two, so a failure carrying none stays classified as a failure rather
    than being excused by silence.
    """

    attempts = record.get("provider_attempts")
    if not isinstance(attempts, list) or not attempts:
        return False
    return all(
        isinstance(attempt, Mapping)
        and str(attempt.get("status") or "").strip().lower() in _SUCCESS_STATES
        for attempt in attempts
    )
_SAFE_ACTIVE_FIELDS = (
    "agent_slug",
    "name",
    "division",
    "description",
    "categories",
    "capabilities",
    "authority",
    "context_mode",
    "independence_group",
    "expected_output_contract",
    "required_tools",
    "supported_hosts",
    "supported_platforms",
    "conflicts_with",
    "requires",
    "evidence_requirements",
    "model_requirements",
    "source_revision",
    "source_content_hash",
    "audit_revision",
    "audit_status",
    "findings",
    "enabled",
    "protected",
    "routing_contract_valid",
)
_SAFE_CHANGED_FIELDS = frozenset(
    {
        "name",
        "division",
        "description",
        "source_version",
        "version",
        "hash",
        "categories",
        "capabilities",
        "tool_affinity",
        "prompt_path",
    }
)


def _bounded_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{label} contains control characters")
    normalized = " ".join(value.split())
    if len(normalized.encode("utf-8")) > _MAX_FILTER_BYTES:
        raise ValueError(f"{label} exceeds {_MAX_FILTER_BYTES} UTF-8 bytes")
    return normalized


def _bounded_limit(value: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{label} must be between 1 and {maximum}")
    return value


def _normalized_filters(filters: Mapping[str, object] | None) -> dict[str, str]:
    if filters is None:
        return {}
    if not isinstance(filters, Mapping) or not set(filters).issubset(_FILTER_FIELDS):
        raise ValueError("roster filters contain unsupported fields")
    return {
        key: value
        for key, raw in filters.items()
        if (value := _bounded_text(raw, f"{key} filter")).strip()
    }


def _strings(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _decoded_active_rows(store: Store) -> tuple[int, list[dict[str, Any]]]:
    """Read one prompt-free active-roster identity in a single transaction."""

    conn = store._connect()
    try:
        conn.execute("BEGIN")
        counter = conn.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
        if counter is None or isinstance(counter["value"], bool):
            raise RuntimeError("roster generation counter is unavailable")
        rows = conn.execute(
            "SELECT a.*, v.metadata AS revision_metadata "
            "FROM agent_active AS a JOIN agent_versions AS v "
            "ON v.agent_slug = a.agent_slug AND v.version = a.version "
            "ORDER BY a.agent_slug LIMIT ?",
            (MAX_ACTIVE_ROSTER_SIZE + 1,),
        ).fetchall()
        generation = int(counter["value"])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if len(rows) > MAX_ACTIVE_ROSTER_SIZE:
        raise RuntimeError("active roster exceeds the operational dashboard bound")
    decoded: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        for field in ("categories", "capabilities", "tool_affinity"):
            try:
                value = safe_load_bounded_json(
                    str(row.get(field) or "[]"),
                    maximum_bytes=256 * 1024,
                    maximum_depth=2,
                    maximum_nodes=4_096,
                )
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"active roster {field} metadata is invalid") from exc
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise RuntimeError(f"active roster {field} metadata is invalid")
            row[field] = value
        metadata = decode_revision_metadata(row.pop("revision_metadata", None))
        row["routing_contract_valid"] = metadata is not None
        for field in ROUTING_SCALAR_METADATA_FIELDS:
            row[field] = str((metadata or {}).get(field) or "")
        for field in ROUTING_LIST_METADATA_FIELDS:
            value = (metadata or {}).get(field)
            row[field] = list(value) if isinstance(value, list) else []
        decoded.append(row)
    return generation, decoded


def _matches(agent: Mapping[str, Any], filters: Mapping[str, str]) -> bool:
    folded = {key: value.casefold() for key, value in filters.items()}
    query = folded.get("query")
    if query:
        searchable = (
            str(agent.get("agent_slug") or ""),
            str(agent.get("name") or ""),
            str(agent.get("description") or ""),
            *_strings(agent.get("categories")),
            *_strings(agent.get("capabilities")),
        )
        if not any(query in value.casefold() for value in searchable):
            return False
    scalar_fields = {
        "division": "division",
        "authority": "authority",
    }
    if any(
        str(agent.get(field) or "").casefold() != folded[key]
        for key, field in scalar_fields.items()
        if key in folded
    ):
        return False
    list_fields = {
        "capability": ("capabilities",),
        "host": ("supported_hosts",),
        "platform": ("supported_platforms",),
        "tool": ("required_tools", "tool_affinity"),
    }
    for key, fields in list_fields.items():
        if key not in folded:
            continue
        values = {item.casefold() for field in fields for item in _strings(agent.get(field))}
        if folded[key] not in values:
            return False
    return True


def _facets(agents: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    definitions = {
        "divisions": ("division",),
        "capabilities": ("capabilities",),
        "authorities": ("authority",),
        "hosts": ("supported_hosts",),
        "platforms": ("supported_platforms",),
        "tools": ("required_tools", "tool_affinity"),
    }
    facets: dict[str, list[str]] = {}
    for name, fields in definitions.items():
        values: set[str] = set()
        for agent in agents:
            for field in fields:
                raw = agent.get(field)
                if isinstance(raw, str):
                    if raw:
                        values.add(raw)
                else:
                    values.update(_strings(raw))
        facets[name] = sorted(values, key=str.casefold)
    return facets


def _revision_history(store: Store, slugs: Sequence[str]) -> dict[str, list[dict[str, Any]]]:
    if not slugs:
        return {}
    placeholders = ",".join("?" for _slug in slugs)
    conn = store._connect()
    try:
        rows = conn.execute(
            "SELECT agent_slug, version, source_version, hash, metadata, created_at "
            f"FROM agent_versions WHERE agent_slug IN ({placeholders}) "  # nosec B608
            "ORDER BY agent_slug, created_at DESC, rowid DESC",
            tuple(slugs),
        ).fetchall()
    finally:
        conn.close()
    history: dict[str, list[dict[str, Any]]] = {slug: [] for slug in slugs}
    for row in rows:
        slug = str(row["agent_slug"])
        if len(history.get(slug, ())) >= MAX_REVISION_HISTORY:
            continue
        metadata = decode_revision_metadata(row["metadata"])
        history.setdefault(slug, []).append(
            {
                "version": str(row["version"] or ""),
                "source_revision": str(
                    (metadata or {}).get("source_revision") or row["source_version"] or ""
                ),
                "content_hash": str(row["hash"] or ""),
                "audit_revision": str((metadata or {}).get("audit_revision") or ""),
                "audit_status": str((metadata or {}).get("audit_status") or "unknown"),
                "created_at": str(row["created_at"] or ""),
                "metadata_valid": metadata is not None,
            }
        )
    return history


def roster_operational_page(
    store: Store,
    *,
    disabled_agents: Container[str] = (),
    filters: Mapping[str, object] | None = None,
    limit: int = MAX_OPERATIONAL_ROSTER_RESULTS,
    after: str | None = None,
) -> dict[str, Any]:
    """Return a filtered active-roster page without loading prompt content."""

    bounded_limit = _bounded_limit(limit, MAX_OPERATIONAL_ROSTER_RESULTS, "roster result limit")
    normalized_filters = _normalized_filters(filters)
    normalized_after = normalize_agent_slug(after) if after is not None else None
    if after is not None and normalized_after != after:
        raise ValueError("agent slug cursor must already be canonical")
    generation, rows = _decoded_active_rows(store)
    total_count = len(rows)
    enabled_count = sum(
        bool(selector_roster_projection(row, disabled_agents)["enabled"]) for row in rows
    )
    projected = []
    for row in rows:
        item = selector_roster_projection(row, disabled_agents)
        item["tool_affinity"] = _strings(row.get("tool_affinity"))
        item["version"] = str(row.get("version") or "")
        item["content_hash"] = str(row.get("hash") or "")
        item["activated_at"] = str(row.get("activated_at") or "")
        if _matches(item, normalized_filters):
            projected.append(item)
    if normalized_after is not None:
        projected = [item for item in projected if str(item["agent_slug"]) > normalized_after]
    page = projected[: bounded_limit + 1]
    truncated = len(page) > bounded_limit
    page = page[:bounded_limit]
    histories = _revision_history(store, [str(item["agent_slug"]) for item in page])
    agents = [
        {
            **{field: item.get(field) for field in _SAFE_ACTIVE_FIELDS},
            "tool_affinity": list(item["tool_affinity"]),
            "version": item["version"],
            "content_hash": item["content_hash"],
            "activated_at": item["activated_at"],
            "revision_history": histories.get(str(item["agent_slug"]), []),
        }
        for item in page
    ]
    return {
        "schema_version": "agency.dashboard.roster_operations.v1",
        "agents": agents,
        "count": len(agents),
        "matched_count": len(projected),
        "total_count": total_count,
        "enabled_count": enabled_count,
        "disabled_count": total_count - enabled_count,
        "limit": bounded_limit,
        "truncated": truncated,
        "next_cursor": str(agents[-1]["agent_slug"]) if truncated and agents else None,
        "filters": normalized_filters,
        "facets": _facets(
            [
                {
                    **selector_roster_projection(row, disabled_agents),
                    "tool_affinity": _strings(row.get("tool_affinity")),
                }
                for row in rows
            ]
        ),
        "roster_generation": generation,
    }


def _audit_projection(audit: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if audit is None:
        return None
    raw_findings = audit.get("findings")
    findings = raw_findings if isinstance(raw_findings, list) else []
    return {
        "id": str(audit.get("id") or ""),
        "audit_revision": str(audit.get("audit_revision") or ""),
        "policy_hash": str(audit.get("policy_hash") or ""),
        "candidate_version": str(audit.get("candidate_version") or ""),
        "candidate_hash": str(audit.get("candidate_hash") or ""),
        "deterministic_status": str(audit.get("deterministic_status") or "unknown"),
        "inference_status": str(audit.get("inference_status") or "unknown"),
        "verdict": str(audit.get("verdict") or "unknown"),
        "provider": str(audit.get("provider") or "")[:128],
        "created_at": str(audit.get("created_at") or ""),
        "findings": [
            {
                "source": str(item.get("source") or "unknown"),
                "severity": str(item.get("severity") or "unknown"),
                "code": str(item.get("code") or "unknown")[:128],
                "evidence_hash": str(item.get("evidence_hash") or ""),
                "created_at": str(item.get("created_at") or ""),
            }
            for item in findings[:128]
            if isinstance(item, Mapping)
        ],
    }


def _status_history(conn: Any, candidate_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT event_type, from_status, to_status, reason, audit_id, created_at "
        "FROM agent_candidate_status_events WHERE candidate_id = ? "
        "ORDER BY created_at DESC, rowid DESC LIMIT 25",
        (candidate_id,),
    ).fetchall()
    return [
        {
            "event_type": str(row["event_type"] or ""),
            "from_status": str(row["from_status"] or ""),
            "to_status": str(row["to_status"] or ""),
            "reason_present": bool(row["reason"]),
            "reason_hash": (
                hashlib.sha256(str(row["reason"]).encode("utf-8")).hexdigest()
                if row["reason"]
                else ""
            ),
            "audit_id": str(row["audit_id"] or ""),
            "created_at": str(row["created_at"] or ""),
        }
        for row in rows
    ]


def _candidate_item(conn: Any, row: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(row["id"])
    active = conn.execute(
        "SELECT agent_slug, name, division, description, source_version, version, hash, "
        "categories, capabilities, tool_affinity, prompt_path, activated_at "
        "FROM agent_active WHERE agent_slug = ? LIMIT 1",
        (row["slug"],),
    ).fetchone()
    fields = (
        "name",
        "division",
        "description",
        "source_version",
        "version",
        "hash",
        "categories",
        "capabilities",
        "tool_affinity",
        "prompt_path",
    )
    changed_fields = [
        field
        for field in fields
        if field in _SAFE_CHANGED_FIELDS
        and (active is None or str(row.get(field) or "") != str(active[field] or ""))
    ]
    active_projection = (
        None
        if active is None
        else {
            "agent_slug": str(active["agent_slug"] or ""),
            "name": str(active["name"] or ""),
            "division": str(active["division"] or ""),
            "source_revision": str(active["source_version"] or ""),
            "version": str(active["version"] or ""),
            "content_hash": str(active["hash"] or ""),
            "activated_at": str(active["activated_at"] or ""),
        }
    )
    return {
        "candidate": {
            "id": candidate_id,
            "slug": str(row["slug"] or ""),
            "name": str(row["name"] or ""),
            "division": str(row["division"] or ""),
            "status": str(row["status"] or ""),
            "source_revision": str(row["source_version"] or ""),
            "version": str(row["version"] or ""),
            "content_hash": str(row["hash"] or ""),
            "quarantined_at": str(row["quarantined_at"] or ""),
        },
        "active": active_projection,
        "change": "added" if active is None else ("unchanged" if not changed_fields else "changed"),
        "changed_fields": changed_fields,
        "latest_audit": _audit_projection(
            latest_candidate_audit_from_connection(conn, candidate_id)
        ),
        "status_history": _status_history(conn, candidate_id),
    }


@lru_cache(maxsize=1)
def _packaged_source_identity() -> tuple[str, str]:
    """Hash immutable packaged metadata once instead of on every live refresh."""

    manifest = bundled_manifest()
    source = manifest.get("source") if isinstance(manifest, Mapping) else {}
    source = source if isinstance(source, Mapping) else {}
    canonical = json.dumps(
        manifest,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return str(source.get("revision") or ""), hashlib.sha256(canonical).hexdigest()


def _upstream_projection(conn: Any, queue_count: int) -> dict[str, Any]:
    packaged_revision, packaged_hash = _packaged_source_identity()
    latest_scan = conn.execute(
        "SELECT id, status, manifest_hash, entry_count, candidate_count, "
        "quarantined_count, ignored_count, created_at FROM agent_source_scans "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1"
    ).fetchone()
    latest_audit = conn.execute(
        "SELECT created_at FROM agent_candidate_audits WHERE verdict = 'passed' "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1"
    ).fetchone()
    return {
        "packaged_source_revision": packaged_revision,
        "packaged_manifest_hash": packaged_hash,
        "remote_freshness": "unverified",
        "review_queue_count": queue_count,
        "state": "review_pending" if queue_count else "audited_baseline",
        "last_successful_audit_at": (
            str(latest_audit["created_at"]) if latest_audit is not None else None
        ),
        "latest_source_scan": (
            None
            if latest_scan is None
            else {
                "id": str(latest_scan["id"]),
                "status": str(latest_scan["status"]),
                "manifest_hash": str(latest_scan["manifest_hash"]),
                "entry_count": int(latest_scan["entry_count"]),
                "candidate_count": int(latest_scan["candidate_count"]),
                "quarantined_count": int(latest_scan["quarantined_count"]),
                "ignored_count": int(latest_scan["ignored_count"]),
                "created_at": str(latest_scan["created_at"]),
            }
        ),
    }


def candidate_review_snapshot(
    store: Store,
    *,
    limit: int = 25,
    candidate_id: str | None = None,
    candidate_cursor_time: str = "",
    candidate_cursor_id: str = "",
    pending_cursor: str = "",
    history_cursor: str = "",
) -> dict[str, Any]:
    """Return a review queue or one comparison without candidate prompt content."""

    bounded_limit = _bounded_limit(limit, MAX_REVIEW_RESULTS, "candidate result limit")
    if candidate_id is not None and not _CANDIDATE_ID.fullmatch(candidate_id):
        raise ValueError("candidate id is invalid")
    cursor_time = str(candidate_cursor_time or "").strip()
    cursor_id = str(candidate_cursor_id or "").strip()
    if bool(cursor_time) != bool(cursor_id):
        raise ValueError("candidate cursor is incomplete")
    if candidate_id is not None and cursor_time:
        raise ValueError("candidate detail cannot include a collection cursor")
    conn = store._connect()
    try:
        conn.execute("BEGIN")
        remediation = remediation_queue_snapshot(
            store,
            limit=bounded_limit,
            pending_cursor=pending_cursor,
            history_cursor=history_cursor,
            _connection=conn,
        )
        remediation_attempts = remediation["pending"]
        candidate_queue_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM agent_candidates WHERE status IN ('pending', 'approved')"
            ).fetchone()[0]
        )
        remediation_count = int(remediation["pending_count"])
        queue_count = candidate_queue_count + remediation_count
        if candidate_id is None:
            cursor_where = (
                "AND (quarantined_at < ? OR (quarantined_at = ? AND id < ?)) "
                if cursor_time
                else ""
            )
            cursor_values = (cursor_time, cursor_time, cursor_id) if cursor_time else ()
            rows = conn.execute(
                "SELECT id, slug, name, description, division, categories, capabilities, "
                "tool_affinity, prompt_path, source_version, version, hash, status, "
                "quarantined_at FROM agent_candidates "
                "WHERE status IN ('pending', 'approved') "
                + cursor_where
                + "ORDER BY quarantined_at DESC, id DESC LIMIT ?",
                (*cursor_values, bounded_limit + 1),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, slug, name, description, division, categories, capabilities, "
                "tool_affinity, prompt_path, source_version, version, hash, status, "
                "quarantined_at FROM agent_candidates WHERE id = ? LIMIT 1",
                (candidate_id,),
            ).fetchall()
            if not rows:
                raise KeyError(f"candidate not found: {candidate_id}")
        projected = [_candidate_item(conn, dict(row)) for row in rows[:bounded_limit]]
        candidate_revision_rows = [
            dict(row)
            for row in conn.execute(
                "SELECT id, status, quarantined_at, hash FROM agent_candidates "
                "WHERE status IN ('pending', 'approved') "
                "ORDER BY quarantined_at DESC, id DESC"
            ).fetchall()
        ]
        upstream = _upstream_projection(conn, queue_count)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {
        "schema_version": "agency.dashboard.roster_reviews.v2",
        "candidates": projected,
        "remediation_attempts": remediation_attempts,
        "remediation_history": remediation["history"],
        "count": len(projected),
        "queue_count": queue_count,
        "candidate_queue_count": candidate_queue_count,
        "remediation_count": remediation_count,
        "remediation_history_count": int(remediation["history_count"]),
        "remediation_revision": str(remediation["remediation_revision"]),
        "remediation_stale_resolution_count": int(remediation["stale_resolution_count"]),
        "remediation_unvalidated_resolution_count": int(
            remediation["unvalidated_resolution_count"]
        ),
        "remediation_pending_has_more": bool(remediation["pending_has_more"]),
        "remediation_history_has_more": bool(remediation["history_has_more"]),
        "next_remediation_pending_cursor": str(remediation["next_pending_cursor"]),
        "next_remediation_history_cursor": str(remediation["next_history_cursor"]),
        "limit": bounded_limit,
        "truncated": candidate_id is None and len(rows) > bounded_limit,
        "filtered_count": candidate_queue_count,
        "total_count": candidate_queue_count,
        "next_candidate_time": str(projected[-1]["candidate"]["quarantined_at"])
        if candidate_id is None and len(rows) > bounded_limit and projected
        else "",
        "next_candidate_id": str(projected[-1]["candidate"]["id"])
        if candidate_id is None and len(rows) > bounded_limit and projected
        else "",
        "collection_revision": hashlib.sha256(
            (
                "roster-reviews.v1\\0"
                + json.dumps(
                    candidate_revision_rows,
                    allow_nan=False,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            ).encode()
        ).hexdigest(),
        "candidate_id": candidate_id,
        "upstream": upstream,
    }


def _provider_chain(config: AgencyConfig) -> list[ProviderEntry]:
    if config.providers:
        return list(config.providers)
    result: list[ProviderEntry] = []
    judge = config.judge
    if (
        judge.model
        and judge.base_url
        and (
            judge.ollama_mode
            or bool(judge.resolve_api_key())
            or _is_loopback_http_url(judge.base_url)
        )
    ):
        result.append(
            ProviderEntry(
                name="legacy-judge",
                type="ollama" if judge.ollama_mode else "openai-compatible",
                model=judge.model,
                base_url=judge.base_url,
                api_key=judge.api_key,
                api_key_env=judge.api_key_env,
                ollama_mode=judge.ollama_mode,
                timeout=judge.timeout,
            )
        )
    if config.ollama.enabled and config.ollama.model and config.ollama.base_url:
        result.append(
            ProviderEntry(
                name="ollama-fallback",
                type="ollama",
                model=config.ollama.model,
                base_url=config.ollama.base_url,
                ollama_mode=True,
            )
        )
    return result


def _receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "requested_model": str(receipt.get("requested_model") or "")[:256],
        "router": str(receipt.get("model_group") or "")[:256],
        "actual_provider": str(receipt.get("resolved_provider") or "")[:128],
        "actual_model": str(receipt.get("resolved_model") or "")[:256],
        "status": str(receipt.get("status") or "unknown")[:32],
        "host": str(receipt.get("host") or "unknown")[:64],
        "source": str(receipt.get("source") or "unknown")[:64],
        "recorded_at": str(
            receipt.get("recorded_at") or receipt.get("ended_at") or receipt.get("started_at") or ""
        ),
    }


def _matching_receipt(
    provider: ProviderEntry,
    receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    requested = provider.model.strip()
    for receipt in receipts:
        if requested and requested in {
            str(receipt.get("requested_model") or "").strip(),
            str(receipt.get("model_group") or "").strip(),
        }:
            return _receipt_projection(receipt)
    return None


def inference_operational_snapshot(
    config: AgencyConfig,
    activity: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    failure_limit: int = MAX_RECENT_FAILURES,
) -> dict[str, Any]:
    """Describe configured inference authority and observed evidence truthfully."""

    bounded_limit = _bounded_limit(failure_limit, MAX_RECENT_FAILURES, "failure result limit")
    raw_receipts = activity.get("receipts", ())
    receipts = [item for item in raw_receipts if isinstance(item, Mapping)]
    routing = [item for item in activity.get("routing", ()) if isinstance(item, Mapping)]
    preflight_failures = [
        item for item in activity.get("preflight_failures", ()) if isinstance(item, Mapping)
    ]
    configured = inference_is_configured(config)
    chain = []
    for index, provider in enumerate(_provider_chain(config)):
        provider_type = provider.type.strip().lower() or "unknown"
        observed = _matching_receipt(provider, receipts)
        chain.append(
            {
                "order": index + 1,
                "name": provider.name or f"provider-{index + 1}",
                "type": provider_type,
                "transport": provider.transport if provider_type == "cli" else "",
                "requested_model": provider.model,
                "router": provider.model if provider_type == "litellm" else "",
                "configuration_ready": provider.is_available(),
                "auth_method": provider.auth_method(),
                "observed_receipt": observed,
            }
        )
    failures: list[dict[str, Any]] = [
        {"kind": "model_receipt", **_receipt_projection(receipt)}
        for receipt in receipts
        if str(receipt.get("status") or "").strip().lower() in _FAILURE_STATES
    ]
    for decision in routing:
        status = str(decision.get("semantic_status") or decision.get("status") or "unknown")
        if status.strip().lower() in _FAILURE_STATES:
            failures.append(
                {
                    "kind": "routing",
                    "status": status[:32],
                    "provider": str(decision.get("provider") or "")[:128],
                    "created_at": str(decision.get("created_at") or ""),
                    "trace_id": str(decision.get("trace_id") or "")[:256],
                }
            )
    failures.extend(
        {
            "kind": "preflight_failure",
            "status": "preflight_failed",
            "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
            "stage": str(receipt.get("stage") or "")[:32],
            "reason_code": str(receipt.get("reason_code") or "")[:96],
            "invariant_code": str(receipt.get("invariant_code") or "")[:96],
            "exception_category": str(receipt.get("exception_category") or "")[:32],
            "provider_attempts": list(receipt.get("provider_attempts") or ()),
            "staffing_reason_codes": list(receipt.get("staffing_reason_codes") or ()),
            "hiring_reason_codes": list(receipt.get("hiring_reason_codes") or ()),
            "recorded_at": str(receipt.get("recorded_at") or ""),
            "trace_id": str(receipt.get("trace_id") or "")[:256],
            "host": str(receipt.get("host") or "")[:64],
        }
        for receipt in preflight_failures
    )
    failures.sort(
        key=lambda item: str(item.get("recorded_at") or item.get("created_at") or ""),
        reverse=True,
    )
    latest_routing = routing[0] if routing else None
    latest_status = (
        str(latest_routing.get("semantic_status") or latest_routing.get("status") or "unknown")
        .strip()
        .lower()
        if latest_routing is not None
        else "unknown"
    )
    latest_preflight = preflight_failures[0] if preflight_failures else None
    if latest_preflight is not None and (
        latest_routing is None
        or str(latest_preflight.get("recorded_at") or "")
        >= str(latest_routing.get("created_at") or "")
    ):
        # A preflight can fail downstream of inference -- the recruiter
        # abstaining, or no safe sufficient team -- with every provider attempt
        # applied. That is a staffing outcome. Reporting it as degraded
        # inference sends an operator to audit providers that are working, and
        # leaves the panel stuck there until some later turn happens to succeed.
        latest_status = (
            "applied" if _preflight_inference_applied(latest_preflight) else "preflight_failed"
        )
    if not configured:
        state = "not_configured"
    elif latest_status in _FAILURE_STATES:
        state = "degraded"
    elif latest_status in _SUCCESS_STATES:
        state = "operational"
    else:
        state = "unknown"
    latest_receipt = _receipt_projection(receipts[0]) if receipts else None
    return {
        "schema_version": "agency.dashboard.inference_operations.v1",
        "configured": configured,
        "required_for_eligible_turns": configured,
        "state": state,
        "evidence": (
            "configuration readiness plus recent persisted routing, model, and "
            "content-free preflight failure receipts"
        ),
        "provider_chain": chain,
        "latest_model_resolution": latest_receipt,
        "recent_failures": failures[:bounded_limit],
        "failure_count": len(failures),
        "failures_truncated": len(failures) > bounded_limit,
    }


__all__ = [
    "MAX_OPERATIONAL_ROSTER_RESULTS",
    "MAX_RECENT_FAILURES",
    "MAX_REVIEW_RESULTS",
    "MAX_REVISION_HISTORY",
    "candidate_review_snapshot",
    "inference_operational_snapshot",
    "roster_operational_page",
]
