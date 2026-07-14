"""Bounded query plans and row normalization for operator-facing store reads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.store.projections import project_snapshot_summary
from agency_runtime.core.store.schema import RUNTIME_TABLE_TIMESTAMPS

RECENT_ACTIVITY_QUERIES: Mapping[str, str] = {
    "runs": (
        "SELECT id, trace_id, session_id, host, started_at, ended_at, status "
        "FROM runs ORDER BY started_at DESC, id DESC LIMIT ?"
    ),
    "receipts": (
        "SELECT id, trace_id, session_id, host, requested_model, model_group, "
        "resolved_provider, resolved_model, attempted_fallbacks, model_id, "
        "source, started_at, ended_at, status FROM model_receipts "
        "ORDER BY COALESCE(ended_at, started_at) DESC, id DESC LIMIT ?"
    ),
    "delegations": (
        "SELECT id, trace_id, session_id, host, work_unit_id, recommended_agent, "
        "status, backend, skip_reason, started_at, completed_at "
        "FROM delegation_events "
        "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT ?"
    ),
    "finalizations": (
        "SELECT id, trace_id, host, action, missing, created_at "
        "FROM finalization_events ORDER BY created_at DESC, id DESC LIMIT ?"
    ),
    "routing": (
        "SELECT id, trace_id, session_id, query_hash, context_fingerprint, status, "
        "source, selected_ids, semantic_ids, companion_ids, confidence, latency_ms, "
        "provider, work_units, created_at FROM routing_decisions "
        "ORDER BY created_at DESC, id DESC LIMIT ?"
    ),
}

# Dashboard responses deliberately exclude optional captured delegation detail
# and routing work-unit metadata. Keeping that projection in SQL avoids moving,
# decoding, copying, and then discarding those fields on every live poll.
DASHBOARD_ACTIVITY_QUERIES: Mapping[str, str] = {
    **RECENT_ACTIVITY_QUERIES,
    "delegations": (
        "SELECT id, trace_id, session_id, host, work_unit_id, recommended_agent, "
        "status, backend, started_at, completed_at FROM delegation_events "
        "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT ?"
    ),
    "routing": (
        "SELECT id, trace_id, session_id, query_hash, context_fingerprint, status, "
        "source, selected_ids, semantic_ids, companion_ids, confidence, latency_ms, "
        "provider, created_at FROM routing_decisions "
        "ORDER BY created_at DESC, id DESC LIMIT ?"
    ),
}

_ROUTING_JSON_FIELDS = (
    "selected_ids",
    "semantic_ids",
    "companion_ids",
    "work_units",
)

_ROUTING_DECISION_FIELDS = frozenset(
    {
        "status",
        "selected_ids",
        "semantic_ids",
        "companion_actions",
        "companion_ids",
        "available_companion_ids",
        "unavailable_companion_ids",
        "confidence",
        "latency_ms",
        "provider",
        "candidate_count",
        "top_score",
        "cache_hit",
        "session_reused",
        "source_message_hash",
        "trace_id",
        "context_fingerprint",
        "query_hash",
    }
)


def bounded_limit(value: int, *, maximum: int = 200) -> int:
    """Clamp a caller-supplied result limit to a useful, safe range."""

    return max(1, min(int(value), maximum))


def _decode_json_projection(
    raw_value: object,
    *,
    expected_type: type[list[Any]] | type[dict[str, Any]],
    fallback: list[Any] | dict[str, Any],
    maximum_depth: int,
) -> list[Any] | dict[str, Any]:
    if not isinstance(raw_value, str) or not raw_value:
        return fallback
    try:
        parsed = safe_load_bounded_json(
            raw_value,
            maximum_bytes=1024 * 1024,
            maximum_depth=maximum_depth,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError):
        return fallback
    return parsed if isinstance(parsed, expected_type) else fallback


def _normalize_finalizations(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        row["missing"] = _decode_json_projection(
            row.get("missing"),
            expected_type=list,
            fallback=["unparseable"] if row.get("missing") else [],
            maximum_depth=32,
        )


def _normalize_routing(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        for field in _ROUTING_JSON_FIELDS:
            if field not in row:
                continue
            is_work_units = field == "work_units"
            row[field] = _decode_json_projection(
                row.get(field),
                expected_type=dict if is_work_units else list,
                fallback={} if is_work_units else [],
                maximum_depth=64,
            )


def normalize_activity_rows(
    name: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Decode only documented JSON projections from recent activity rows."""

    if name == "finalizations":
        _normalize_finalizations(rows)
    elif name == "routing":
        _normalize_routing(rows)
    return rows


def normalize_snapshot(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project a snapshot row without exposing candidate prompt content."""

    item = dict(row)
    raw_manifest = item.pop("manifest", None)
    summary = project_snapshot_summary(raw_manifest) if raw_manifest is not None else {}
    item["approved"] = bool(item.get("approved", summary.get("approved", False)))
    item["activated"] = bool(item.get("activated"))
    for field in ("added", "changed", "removed"):
        value = item.get(field, summary.get(field, 0))
        item[field] = max(0, value) if isinstance(value, int) and not isinstance(value, bool) else 0
    return item


def project_routing_decision(
    decision: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return the metadata-only decision, work-unit projection, and source."""

    safe_decision = {
        key: value for key, value in decision.items() if key in _ROUTING_DECISION_FIELDS
    }
    raw_work_units = decision.get("work_units")
    safe_work_units: dict[str, Any] = {}
    if isinstance(raw_work_units, dict):
        safe_work_units = {
            key: raw_work_units[key]
            for key in ("delegate", "count", "confidence", "source")
            if key in raw_work_units
        }
    safe_decision["work_units"] = safe_work_units
    source = (
        "cache"
        if safe_decision.get("cache_hit")
        else ("session" if safe_decision.get("session_reused") else "computed")
    )
    return safe_decision, safe_work_units, source


def retention_predicates(
    table: str,
    timestamp_expression: str,
    *,
    cutoff: str | None,
    keep_last: int | None,
) -> tuple[str, list[Any]]:
    """Build the fixed, allowlisted retention predicate for one runtime table."""

    if RUNTIME_TABLE_TIMESTAMPS.get(table) != timestamp_expression:
        raise ValueError("retention table and timestamp expression must be allowlisted")

    clauses: list[str] = []
    parameters: list[Any] = []
    if cutoff is not None:
        clauses.append(f"{timestamp_expression} < ?")
        parameters.append(cutoff)
    if keep_last is not None:
        clauses.append(
            "rowid NOT IN ("
            f"SELECT rowid FROM {table} "  # nosec B608
            f"ORDER BY {timestamp_expression} DESC, rowid DESC LIMIT ?"
            ")"
        )
        parameters.append(keep_last)
    if table == "delegation_events":
        clauses.append(
            "NOT EXISTS (SELECT 1 FROM worker_runs "
            "WHERE worker_runs.delegation_event_id = delegation_events.id)"
        )
    elif table == "runs":
        clauses.extend(
            [
                "NOT EXISTS (SELECT 1 FROM model_receipts "
                "WHERE model_receipts.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM delegation_events "
                "WHERE delegation_events.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM finalization_events "
                "WHERE finalization_events.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM routing_decisions "
                "WHERE routing_decisions.trace_id = runs.trace_id)",
            ]
        )
    return " AND ".join(f"({clause})" for clause in clauses), parameters
