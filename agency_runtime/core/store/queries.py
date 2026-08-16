"""Bounded query plans and row normalization for operator-facing store reads."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.host_capabilities import project_host_capability_receipt
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
        "source, recorded_at, started_at, ended_at, status FROM model_receipts "
        "ORDER BY recorded_at DESC, id DESC LIMIT ?"
    ),
    "preflight_failures": (
        "SELECT id, session_id, trace_id, host, stage, reason_code, invariant_code, "
        "exception_category, provider_attempts, staffing_reason_codes, "
        "hiring_reason_codes, eligibility_reason_codes, recorded_at "
        "FROM preflight_failure_receipts "
        "ORDER BY recorded_at DESC, id DESC LIMIT ?"
    ),
    "delegations": (
        "SELECT id, trace_id, session_id, host, work_unit_id, recommended_agent, "
        "status, backend, executed_worker_kind, executed_worker_id, native_run_id, "
        "retrieved_specialist_slug, retrieved_specialist_version, "
        "retrieved_specialist_prompt_hash, activation_receipt_id, skip_reason, "
        "started_at, completed_at "
        "FROM delegation_events "
        "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT ?"
    ),
    "finalizations": (
        "SELECT id, trace_id, host, action, missing, terminal_status, created_at "
        "FROM finalization_events ORDER BY created_at DESC, id DESC LIMIT ?"
    ),
    "specialists": (
        "SELECT specialist.id, specialist.session_id, specialist.trace_id, "
        "specialist.agent_slug AS slug, specialist.loaded_at, specialist.expired_at, "
        "CASE WHEN specialist.trace_id <> '' AND specialist.expired_at IS NULL "
        "AND run.status IN ('active', 'evidence_only') "
        "THEN 'current' ELSE 'historical' END AS state "
        "FROM specialists_loaded AS specialist LEFT JOIN runs AS run "
        "ON run.trace_id = specialist.trace_id "
        "AND run.session_id = specialist.session_id "
        "ORDER BY specialist.loaded_at DESC, specialist.id DESC LIMIT ?"
    ),
    "routing": (
        "SELECT id, trace_id, session_id, query_hash, context_fingerprint, status, "
        "source, selected_ids, semantic_ids, companion_ids, confidence, latency_ms, "
        "provider, work_units, decision, created_at FROM routing_decisions "
        "ORDER BY created_at DESC, id DESC LIMIT ?"
    ),
}

# Dashboard responses deliberately exclude optional captured delegation detail
# and routing work-unit metadata. The only decoded routing payload is the
# already-sanitized decision projection needed to preserve fallback provenance.
DASHBOARD_ACTIVITY_QUERIES: Mapping[str, str] = {
    **RECENT_ACTIVITY_QUERIES,
    "delegations": (
        "SELECT id, trace_id, session_id, host, work_unit_id, recommended_agent, "
        "status, backend, executed_worker_kind, executed_worker_id, native_run_id, "
        "retrieved_specialist_slug, retrieved_specialist_version, "
        "retrieved_specialist_prompt_hash, activation_receipt_id, "
        "started_at, completed_at FROM delegation_events "
        "ORDER BY COALESCE(completed_at, started_at) DESC, id DESC LIMIT ?"
    ),
    "routing": (
        "SELECT id, trace_id, session_id, query_hash, context_fingerprint, status, "
        "source, selected_ids, semantic_ids, companion_ids, confidence, latency_ms, "
        "provider, decision, created_at FROM routing_decisions "
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
        "semantic_status",
        "source",
        "selected_ids",
        "semantic_ids",
        "companion_actions",
        "companion_ids",
        "available_companion_ids",
        "unavailable_companion_ids",
        "fallback_companion_ids",
        "available_fallback_companion_ids",
        "unavailable_fallback_companion_ids",
        "fallback_considered",
        "fallback_applied",
        "confidence",
        "latency_ms",
        "provider",
        "candidate_count",
        # Which specialists the child judge was actually shown. `candidate_count`
        # alone cannot answer the only question a decline raises -- whether
        # anyone who could do the work was in front of it.
        "offered_agent_ids",
        "offered_agent_digest",
        # How much assignment the child was given, never what it said. Separates
        # a one-line errand, where declining is correct, from a real brief.
        "task_chars",
        "task_lines",
        "top_score",
        "cache_hit",
        "session_reused",
        "continuation_reused",
        "continuation_resolution_required",
        "source_message_hash",
        "origin_trace_id",
        "origin_query_hash",
        "origin_context_fingerprint",
        "trace_id",
        "context_fingerprint",
        "query_hash",
        "execution_context",
        "routing_receipt",
        "native_child_delivery",
        "native_child_reason",
        "inference_configured",
        "inference_required",
        "inference_attempted",
        "inference_mode",
    }
)

_ROUTING_LIST_FIELDS = frozenset(
    {
        "selected_ids",
        "semantic_ids",
        "companion_actions",
        "companion_ids",
        "available_companion_ids",
        "unavailable_companion_ids",
        "fallback_companion_ids",
        "available_fallback_companion_ids",
        "unavailable_fallback_companion_ids",
    }
)
_ROUTING_LABEL_FIELDS = frozenset(
    {"status", "semantic_status", "source", "native_child_reason", "inference_mode"}
)
_ROUTING_BOOLEAN_FIELDS = frozenset(
    {
        "fallback_considered",
        "fallback_applied",
        "cache_hit",
        "session_reused",
        "continuation_reused",
        "continuation_resolution_required",
        "inference_configured",
        "inference_required",
        "inference_attempted",
    }
)
_ROUTING_FLOAT_FIELDS = frozenset({"confidence", "top_score"})
_ROUTING_COUNT_FIELDS = frozenset({"latency_ms", "candidate_count", "task_chars", "task_lines"})
_ROUTING_DIGEST_FIELDS = frozenset(
    {
        "source_message_hash",
        "context_fingerprint",
        "query_hash",
        "origin_query_hash",
        "origin_context_fingerprint",
        "offered_agent_digest",
    }
)
# Agent slugs, not free text. A malformed id fails the field closed rather than
# crossing the content-free receipt boundary as an opaque string.
_OFFERED_AGENT_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
MAX_ROUTING_OFFERED_AGENT_CHARS = 16_384


def _bounded_routing_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value[:16]:
        normalized = str(item or "").strip()[:128]
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _bounded_routing_float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(-1_000_000.0, min(parsed, 1_000_000.0)) if math.isfinite(parsed) else 0.0


def _bounded_routing_count(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(parsed, 86_400_000))


def _bounded_offered_agent_ids(value: object) -> object:
    """Project the offered universe as one flat, slug-validated string.

    Flat, not a list: the same payload reaches readers bounded at
    ``maximum_depth=4``, and a nested list here is what broke the live evidence
    store when ``ranked_agent_ids`` shipped that way. The digest travels beside
    it over the complete set, so a value dropped here cannot be mistaken for a
    smaller universe.
    """

    if not isinstance(value, str):
        return _OMIT_ROUTING_FIELD
    normalized = value.strip()
    if not normalized or len(normalized) > MAX_ROUTING_OFFERED_AGENT_CHARS:
        return _OMIT_ROUTING_FIELD
    parts = normalized.split("~")
    if any(_OFFERED_AGENT_ID.fullmatch(part) is None for part in parts):
        return _OMIT_ROUTING_FIELD
    return normalized


def _routing_digest(value: object) -> str:
    normalized = str(value or "").strip()
    return (
        normalized
        if len(normalized) == 64
        and all(character in "0123456789abcdef" for character in normalized)
        else ""
    )


_OMIT_ROUTING_FIELD = object()


def _project_routing_field(key: str, value: object) -> object:
    if key in _ROUTING_LIST_FIELDS:
        return _bounded_routing_list(value)
    if key in _ROUTING_LABEL_FIELDS:
        return str(value or "").strip()[:64]
    if key in _ROUTING_BOOLEAN_FIELDS:
        return bool(value)
    if key in _ROUTING_FLOAT_FIELDS:
        return _bounded_routing_float(value)
    if key in _ROUTING_COUNT_FIELDS:
        return _bounded_routing_count(value)
    if key == "offered_agent_ids":
        return _bounded_offered_agent_ids(value)
    if key in _ROUTING_DIGEST_FIELDS:
        return _routing_digest(value) or _OMIT_ROUTING_FIELD
    if key == "provider":
        return str(value or "").strip()[:128]
    if key == "execution_context":
        return project_host_capability_receipt(value) or _OMIT_ROUTING_FIELD
    if key == "routing_receipt":
        from agency_runtime.core.selector.receipt_projection import (
            normalize_durable_routing_receipt,
        )

        return normalize_durable_routing_receipt(value) or _OMIT_ROUTING_FIELD
    if key == "native_child_delivery":
        from agency_runtime.core.native_child_decision import (
            project_native_child_staffing_decision,
        )

        return project_native_child_staffing_decision(value) or _OMIT_ROUTING_FIELD
    if key in {"trace_id", "origin_trace_id"}:
        return str(value or "").strip()[:256]
    return _OMIT_ROUTING_FIELD


_OPEN_TRACE_RETENTION_GUARDS: Mapping[str, str] = {
    "runs": "runs.status NOT IN ('active', 'evidence_only')",
    "preflight_failure_receipts": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = "
        "preflight_failure_receipts.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "model_receipts": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = model_receipts.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "skills_loaded": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = skills_loaded.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "specialists_loaded": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = specialists_loaded.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "delegation_activation_receipts": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = "
        "delegation_activation_receipts.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "delegation_events": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = delegation_events.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "worker_runs": (
        "NOT EXISTS (SELECT 1 FROM delegation_events "
        "JOIN runs ON runs.trace_id = delegation_events.trace_id "
        "WHERE delegation_events.id = worker_runs.delegation_event_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "finalization_events": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = finalization_events.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "routing_intent": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = routing_intent.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "routing_decisions": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE runs.trace_id = routing_decisions.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    # A completed cache entry is independent. While its singleflight lease is
    # still open, however, keep both rows with the active parent turn.
    "child_routing_cache": (
        "NOT EXISTS (SELECT 1 FROM child_routing_leases "
        "JOIN runs ON runs.trace_id = child_routing_leases.parent_trace_id "
        "WHERE child_routing_leases.cache_key = child_routing_cache.cache_key "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "child_routing_usage": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE "
        "runs.trace_id = child_routing_usage.parent_trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "child_routing_leases": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE "
        "runs.trace_id = child_routing_leases.parent_trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "native_child_parent_scopes": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE "
        "runs.trace_id = native_child_parent_scopes.parent_trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "resident_manager_bindings": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE "
        "runs.session_id = resident_manager_bindings.session_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
    "agent_performance_events": (
        "NOT EXISTS (SELECT 1 FROM runs WHERE "
        "runs.trace_id = agent_performance_events.trace_id "
        "AND runs.status IN ('active', 'evidence_only'))"
    ),
}


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
    from agency_runtime.core.selector.receipt_projection import (
        normalize_durable_routing_receipt,
    )

    for row in rows:
        decision = _decode_json_projection(
            row.pop("decision", None),
            expected_type=dict,
            fallback={},
            maximum_depth=32,
        )
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
        row["semantic_status"] = str(
            decision.get("semantic_status") or row.get("status") or "unknown"
        )
        row["fallback_applied"] = decision.get("fallback_applied") is True
        fallback_ids = decision.get("fallback_companion_ids")
        row["fallback_companion_ids"] = (
            [str(value) for value in fallback_ids if isinstance(value, str) and value]
            if isinstance(fallback_ids, list)
            else []
        )
        receipt = normalize_durable_routing_receipt(decision.get("routing_receipt"))
        row["routing_receipt"] = receipt or {}


def normalize_activity_rows(
    name: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Decode only documented JSON projections from recent activity rows."""

    if name == "finalizations":
        _normalize_finalizations(rows)
    elif name == "routing":
        _normalize_routing(rows)
    elif name == "preflight_failures":
        from agency_runtime.core.preflight_failure import (
            MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
            MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
            PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
            project_preflight_failure_receipt,
        )

        for row in rows:
            try:
                attempts = safe_load_bounded_json(
                    str(row.get("provider_attempts") or ""),
                    maximum_bytes=MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES,
                    maximum_depth=4,
                    maximum_nodes=512,
                )
                staffing_reason_codes = safe_load_bounded_json(
                    str(row.get("staffing_reason_codes") or ""),
                    maximum_bytes=MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
                    maximum_depth=2,
                    maximum_nodes=64,
                )
                hiring_reason_codes = safe_load_bounded_json(
                    str(row.get("hiring_reason_codes") or ""),
                    maximum_bytes=MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
                    maximum_depth=2,
                    maximum_nodes=64,
                )
                eligibility_reason_codes = safe_load_bounded_json(
                    # Rows written before this column existed decode as empty.
                    str(row.get("eligibility_reason_codes") or "[]"),
                    maximum_bytes=MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES,
                    maximum_depth=2,
                    maximum_nodes=64,
                )
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    "preflight failure activity failed integrity validation"
                ) from exc
            projected = project_preflight_failure_receipt(
                {
                    "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
                    "stage": row.get("stage"),
                    "reason_code": row.get("reason_code"),
                    "invariant_code": row.get("invariant_code"),
                    "exception_category": row.get("exception_category"),
                    "provider_attempts": attempts,
                    "staffing_reason_codes": staffing_reason_codes,
                    "hiring_reason_codes": hiring_reason_codes,
                    "eligibility_reason_codes": eligibility_reason_codes,
                }
            )
            if projected is None:
                raise RuntimeError("preflight failure activity failed integrity validation")
            row.update(projected)
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

    safe_decision: dict[str, Any] = {}
    for key in _ROUTING_DECISION_FIELDS:
        if key not in decision:
            continue
        projected = _project_routing_field(key, decision[key])
        if projected is not _OMIT_ROUTING_FIELD:
            safe_decision[key] = projected
    raw_work_units = decision.get("work_units")
    safe_work_units: dict[str, Any] = {}
    if isinstance(raw_work_units, dict):
        safe_work_units = {
            "delegate": bool(raw_work_units.get("delegate", False)),
            "count": min(_bounded_routing_count(raw_work_units.get("count", 0)), 16),
            "confidence": str(raw_work_units.get("confidence") or "").strip()[:32],
            "source": str(raw_work_units.get("source") or "").strip()[:64],
        }
    safe_decision["work_units"] = safe_work_units
    if safe_decision.get("cache_hit"):
        source = "cache"
    elif safe_decision.get("session_reused"):
        source = "session"
    elif safe_decision.get("source") == "policy_fallback":
        source = "policy_fallback"
    elif safe_decision.get("source") == "codex_activation_canary_inference":
        source = "codex_activation_canary_inference"
    elif safe_decision.get("source") in {
        "native_child_inference",
        "native_child_inference_failure",
        # A solicited decline is not a failure. Unlisted sources fall through to
        # "computed" below, which would label an inference abstention as a
        # deterministic decision -- so an addition here is required, not optional.
        "native_child_inference_abstained",
    }:
        source = str(safe_decision["source"])
    else:
        source = "computed"
    return safe_decision, safe_work_units, source


def retention_predicates(
    table: str,
    timestamp_expression: str,
    *,
    cutoff: str | None,
    keep_last: int | None,
) -> tuple[str, list[Any]]:
    """Build the fixed, allowlisted retention predicate for one runtime table."""

    clauses, parameters = retention_window_predicates(
        table,
        timestamp_expression,
        cutoff=cutoff,
        keep_last=keep_last,
    )
    clauses.append(_OPEN_TRACE_RETENTION_GUARDS[table])
    if table == "delegation_events":
        clauses.append(
            "NOT EXISTS (SELECT 1 FROM worker_runs "
            "WHERE worker_runs.delegation_event_id = delegation_events.id)"
        )
    elif table == "finalization_events":
        clauses.append(
            "NOT EXISTS (SELECT 1 FROM runs "
            "WHERE runs.terminal_finalization_id = finalization_events.id)"
        )
    elif table == "runs":
        clauses.extend(
            [
                "NOT EXISTS (SELECT 1 FROM model_receipts "
                "WHERE model_receipts.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM preflight_failure_receipts "
                "WHERE preflight_failure_receipts.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM skills_loaded "
                "WHERE skills_loaded.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM specialists_loaded "
                "WHERE specialists_loaded.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM delegation_activation_receipts "
                "WHERE delegation_activation_receipts.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM delegation_events "
                "WHERE delegation_events.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM finalization_events "
                "WHERE finalization_events.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM routing_decisions "
                "WHERE routing_decisions.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM routing_intent "
                "WHERE routing_intent.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM agent_performance_events "
                "WHERE agent_performance_events.trace_id = runs.trace_id)",
                "NOT EXISTS (SELECT 1 FROM native_child_parent_scopes "
                "WHERE native_child_parent_scopes.parent_trace_id = runs.trace_id)",
            ]
        )
    return " AND ".join(f"({clause})" for clause in clauses), parameters


def retention_window_predicates(
    table: str,
    timestamp_expression: str,
    *,
    cutoff: str | None,
    keep_last: int | None,
) -> tuple[list[str], list[Any]]:
    """Build only age/count eligibility clauses for an allowlisted table."""

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
    return clauses, parameters
