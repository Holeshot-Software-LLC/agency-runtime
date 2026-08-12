"""Run, receipt, host-control, and delegation persistence methods."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.codex_child_tool_evidence import (
    decode_stored_codex_child_tool_evidence,
)
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    DELEGATION_STATUS_PRIORITY as _DELEGATION_STATUS_PRIORITY,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_AGENT_CHARS as _MAX_DELEGATION_AGENT_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_BACKEND_CHARS as _MAX_DELEGATION_BACKEND_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_HOST_CHARS as _MAX_DELEGATION_HOST_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_NATIVE_RUN_ID_CHARS as _MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_WORK_UNIT_ID_CHARS as _MAX_DELEGATION_WORK_UNIT_ID_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_WORKER_ID_CHARS as _MAX_DELEGATION_WORKER_ID_CHARS,
)
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_WORKER_KIND_CHARS as _MAX_DELEGATION_WORKER_KIND_CHARS,
)
from agency_runtime.core.delegation_status import (
    TERMINAL_DELEGATION_STATUSES as _TERMINAL_DELEGATION_STATUSES,
)
from agency_runtime.core.delegation_status import (
    bounded_delegation_field as _bounded_delegation_field,
)
from agency_runtime.core.delegation_status import (
    dominant_delegation_status as _dominant_delegation_status,
)
from agency_runtime.core.delegation_status import (
    normalize_delegation_status as _normalize_delegation_status,
)
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.receipts.ingress import (
    ReceiptProvenance as _ReceiptProvenance,
)
from agency_runtime.core.receipts.ingress import (
    normalize_receipt_ingress as _normalize_receipt_ingress,
)
from agency_runtime.core.roster.revisions import content_digest_identity
from agency_runtime.core.store.delegation_activation import (
    attach_consumed_activation_to_delegation,
)
from agency_runtime.core.store.preflight import (
    PreflightStoreMixin,
    _decode_preflight_failure_receipt,
    _decode_preflight_recipe,
    _request_fingerprint,
)
from agency_runtime.core.store.projections import (
    RUN_CONTENT_LIMIT as _RUN_CONTENT_LIMIT,
)
from agency_runtime.core.store.projections import (
    decode_run_metadata,
    project_delegation_detail,
    project_run_metadata,
    redact_sensitive_text,
)
from agency_runtime.core.store.queries import _ROUTING_DECISION_FIELDS
from agency_runtime.core.store.receipt_authority import MODEL_RECEIPT_AUTHORITY_ORDER_SQL
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

MAX_HOST_CONTROL_GENERATION = (2**63) - 1
# A routing payload is ids, hashes, flags and small numbers; anything larger is
# carrying something it should not be.
_ROUTING_CACHE_MAX_BYTES = 16 * 1024
# Retained intent is the one place the store keeps content, so it is bounded
# twice: per unit, so no single work unit can carry a pasted file, and in total,
# so an audit trail cannot grow into a transcript of everything ever asked.
_ROUTING_INTENT_MAX_UNITS = 16
_ROUTING_INTENT_MAX_UNIT_CHARS = 512
_ROUTING_INTENT_MAX_BYTES = 32 * 1024
_ROUTING_INTENT_MAX_ROWS = 2_000
# The same instant format STORE_CLOCK_SQL writes, shifted by a bound modifier,
# so an age comparison is between two identically shaped strings.
STORE_CLOCK_CUTOFF_SQL = "STRFTIME('%Y-%m-%dT%H:%M:%f000+00:00', 'NOW', ?)"


def _bounded_intent_units(value: object) -> list[str]:
    """Bound and de-control the planner's work-unit text before it is retained."""

    if not isinstance(value, (list, tuple)):
        return []
    units: list[str] = []
    for item in value[:_ROUTING_INTENT_MAX_UNITS]:
        if not isinstance(item, str):
            continue
        # Control characters would let retained text rewrite an operator's
        # terminal when the audit surface prints it back.
        cleaned = " ".join(item.split())
        cleaned = "".join(ch for ch in cleaned if ch.isprintable())
        if cleaned:
            units.append(cleaned[:_ROUTING_INTENT_MAX_UNIT_CHARS])
    return units


# Rule 8, as a data definition rather than a claim about the code.
#
# WITHHELD: Agency's verifier evaluated the response and rejected it, or the
# response did not match the digest bound to an already-terminal trace. These
# are the only reasons Agency may cost a user a turn, and with a full roster and
# contractor minting behind it a rejection should be rare enough that each one
# is worth reading.
_WITHHELD_RUN_STATUSES = frozenset({"response_invalid", "delegation_declined", "retry_exhausted"})
# PUBLISHED ANYWAY: Agency could not verify or persist its own evidence, so it
# got out of the way and the turn went out. Never a finding about the response
# -- but it means Agency was blind for that turn, so it still has to be visible.
_PUBLISHED_ANYWAY_RUN_STATUSES = frozenset({"verification_failed", "preflight_failed"})

WITHHELD_RUN_STATUSES = _WITHHELD_RUN_STATUSES
PUBLISHED_ANYWAY_RUN_STATUSES = _PUBLISHED_ANYWAY_RUN_STATUSES
_CANARY_ACTIVATION_SNAPSHOT_SCHEMA = "agency.canary-activation-evidence.v1"
_CANARY_ACTIVATION_MAX_ROWS = 256
MAX_NATIVE_CHILD_DELIVERY_VERIFICATION_ROWS = 4_096


class HostControlConflictError(RuntimeError):
    """A host-control compare-and-swap observed a newer generation."""


def _decode_canary_json(
    value: object,
    *,
    expected_type: type[list[Any]] | type[dict[str, Any]],
    maximum_depth: int = 8,
) -> list[Any] | dict[str, Any] | None:
    """Decode one bounded evidence projection without accepting scalar JSON."""

    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = safe_load_bounded_json(
            value,
            maximum_bytes=1024 * 1024,
            maximum_depth=maximum_depth,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, expected_type) else None


def _project_canary_strings(
    value: object,
    *,
    maximum_items: int = 64,
    maximum_chars: int = 512,
) -> list[str] | None:
    """Return a bounded string-list projection suitable for public evidence."""

    parsed = _decode_canary_json(value, expected_type=list)
    if not isinstance(parsed, list) or len(parsed) > maximum_items:
        return None
    result: list[str] = []
    for raw in parsed:
        if not isinstance(raw, str):
            return None
        item = raw.strip()
        if (
            not item
            or len(item) > maximum_chars
            or any(ord(character) < 32 or ord(character) == 127 for character in item)
        ):
            return None
        result.append(item)
    return result


def _project_native_child_staffing_row(
    row: sqlite3.Row,
    *,
    decision_id: str,
) -> dict[str, Any] | None:
    """Resolve one exact inference decision from its bounded route projection."""

    try:
        decision = safe_load_bounded_json(
            str(row["decision"] or ""),
            maximum_bytes=64 * 1024,
            maximum_depth=8,
            maximum_nodes=1_024,
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(decision, Mapping):
        return None
    from agency_runtime.core.native_child_decision import (
        project_native_child_staffing_decision,
    )

    expected = project_native_child_staffing_decision(decision.get("native_child_delivery"))
    selected = _project_canary_strings(row["selected_ids"], maximum_chars=256)
    semantic = _project_canary_strings(row["semantic_ids"], maximum_chars=256)
    companions = _project_canary_strings(row["companion_ids"], maximum_chars=256)
    expected_slugs = (
        [str(card["specialist_slug"]) for card in expected["cards"]] if expected is not None else []
    )
    context_fingerprint = str(row["context_fingerprint"] or "")
    if (
        expected is None
        or row["id"] != decision_id
        or row["status"] != "applied"
        or row["source"] != "native_child_inference"
        or row["session_id"] != expected["parent_session_id"]
        or row["trace_id"] != expected["parent_trace_id"]
        or row["query_hash"] != expected["task_sha256"]
        or content_digest_identity(context_fingerprint) != context_fingerprint
        or selected != expected_slugs
        or semantic != expected_slugs
        or companions != []
        or decision.get("status") != "applied"
        or decision.get("source") != "native_child_inference"
        or decision.get("selected_ids") != expected_slugs
        or decision.get("semantic_ids") != expected_slugs
        or decision.get("companion_ids") not in (None, [])
        or decision.get("available_companion_ids") not in (None, [])
    ):
        return None
    return {
        "decision_id": decision_id,
        "trace_id": str(row["trace_id"]),
        "session_id": str(row["session_id"]),
        "query_hash": str(row["query_hash"]),
        "context_fingerprint": context_fingerprint,
        "created_at": str(row["created_at"]),
        **expected,
    }


def _bounded_canary_native_child_join(
    conn: Any,
    *,
    host: str,
    session_id: str,
    trace_id: str,
) -> tuple[int, int, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Project one inference route and its diagnostic delivery receipt.

    Store rows cannot prove what a host-authored child artifact contained or
    whether delivery happened before child speech.  The fifth return value is
    therefore always ``None``; only an independently parsed host artifact may
    supply ``host_child_delivery`` to the canary validator.  Both candidate
    windows remain bounded at one row beyond the canary limit so ambiguity
    cannot turn into an unbounded snapshot.
    """

    route_rows = conn.execute(
        "SELECT id, trace_id, session_id, query_hash, context_fingerprint, "
        "status, source, selected_ids, semantic_ids, companion_ids, decision, created_at "
        "FROM routing_decisions WHERE session_id = ? AND trace_id = ? "
        "AND source = 'native_child_inference' ORDER BY created_at, rowid "
        "LIMIT ?",
        (session_id, trace_id, _CANARY_ACTIVATION_MAX_ROWS + 1),
    ).fetchall()
    delivery_rows = conn.execute(
        "SELECT delivery.decision_id, delivery.nonce, delivery.artifact_digest, "
        "delivery.host, delivery.parent_session_id, delivery.parent_trace_id, "
        "delivery.launch_id, delivery.binding_kind, delivery.binding_id, "
        "delivery.child_id, delivery.verified_at "
        "FROM native_child_delivery_verifications AS delivery "
        "JOIN routing_decisions AS route ON route.id = delivery.decision_id "
        "WHERE route.session_id = ? AND route.trace_id = ? "
        "AND delivery.parent_session_id = route.session_id "
        "AND delivery.parent_trace_id = route.trace_id AND delivery.host = ? "
        "ORDER BY delivery.verified_at, delivery.rowid LIMIT ?",
        (session_id, trace_id, host, _CANARY_ACTIVATION_MAX_ROWS + 1),
    ).fetchall()
    route_count = len(route_rows)
    delivery_count = len(delivery_rows)
    if route_count != 1 or delivery_count != 1:
        return route_count, delivery_count, None, None, None

    route = _project_native_child_staffing_row(
        route_rows[0],
        decision_id=str(route_rows[0]["id"] or ""),
    )
    receipt = {**dict(delivery_rows[0]), "verified_delivery": True}
    if route is None:
        return route_count, delivery_count, None, None, None
    receipt_matches = (
        receipt["decision_id"] == route["decision_id"]
        and receipt["host"] == route["host"] == host
        and receipt["parent_session_id"] == route["parent_session_id"] == session_id
        and receipt["parent_trace_id"] == route["parent_trace_id"] == trace_id
        and receipt["launch_id"] == route["launch_id"]
        and receipt["binding_kind"] == route["binding_kind"]
        and receipt["binding_id"] == route["binding_id"]
        and receipt["nonce"] == route["nonce"]
        and content_digest_identity(str(receipt["artifact_digest"] or ""))
        == receipt["artifact_digest"]
    )
    if not receipt_matches:
        return route_count, delivery_count, None, None, None

    return route_count, delivery_count, route, receipt, None


def _project_canary_work_units(value: object) -> dict[str, Any] | None:
    """Project only the content-free work-unit summary persisted for routing."""

    parsed = _decode_canary_json(value, expected_type=dict)
    if not isinstance(parsed, dict):
        return None
    delegate = parsed.get("delegate")
    count = parsed.get("count")
    confidence = parsed.get("confidence")
    source = parsed.get("source")
    if (
        not isinstance(delegate, bool)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= 16
        or not isinstance(confidence, str)
        or len(confidence) > 32
        or not isinstance(source, str)
        or len(source) > 64
    ):
        return None
    return {
        "delegate": delegate,
        "count": count,
        "confidence": confidence,
        "source": source,
    }


def _project_canary_worker_run(item: Any) -> dict[str, Any]:
    """Decode child tool counts while preserving an explicit integrity status."""

    projected = dict(item)
    try:
        projected["tool_evidence"] = decode_stored_codex_child_tool_evidence(
            schema=projected["tool_evidence_schema"],
            source=projected["tool_evidence_source"],
            recorded_at=projected["tool_evidence_recorded_at"],
            payload=projected["tool_evidence"],
        )
    except ValueError:
        projected["tool_evidence"] = None
        projected["tool_evidence_status"] = "invalid"
    else:
        projected["tool_evidence_status"] = (
            "recorded" if projected["tool_evidence"] is not None else "missing"
        )
    return projected


def _empty_canary_activation_snapshot(
    *,
    host: str,
    query_hash: str,
    route_count: int,
    reason: str,
) -> dict[str, Any]:
    """Return the stable fail-closed shape for an unresolved exact route."""

    return {
        "schema": _CANARY_ACTIVATION_SNAPSHOT_SCHEMA,
        "proven": False,
        "status": "not_proven",
        "reason": reason,
        "host": host,
        "query_hash": query_hash,
        "session_id": "",
        "trace_id": "",
        "cardinalities": {
            "routes": route_count,
            "native_child_routes": 0,
            "native_child_deliveries": 0,
            "runs": 0,
            "traces": 0,
            "delegations": 0,
            "activation_grants": 0,
            "activation_consumptions": 0,
            "worker_runs": 0,
            "specialist_loads": 0,
            "finalizations": 0,
            "preflight_failures": 0,
        },
        "run": None,
        "route": None,
        "native_child_route": None,
        "native_child_delivery": None,
        "host_child_delivery": None,
        "preflight_failure": None,
        "delegations": [],
        "activation_grants": [],
        "activation_consumptions": [],
        "worker_runs": [],
        "specialist_loads": [],
        "finalizations": [],
    }


def _failed_preflight_canary_snapshot(
    conn: Any,
    *,
    host: str,
    query_hash: str,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Resolve one exact failed preflight when no ready route was committed."""

    session_clause = "" if session_id is None else "AND run.session_id = ? "
    parameters = (host, query_hash) if session_id is None else (host, query_hash, session_id)
    rows = conn.execute(
        "SELECT run.id, run.trace_id, run.session_id, run.host, run.started_at, "
        "run.last_activity_at, run.evidence_revision, run.turn_sequence, run.ended_at, "
        "run.status, run.terminal_finalization_id, run.preflight_state, "
        "run.preflight_request_fingerprint, run.preflight_request_kind, "
        "failure.id AS failure_id, failure.stage AS failure_stage, "
        "failure.reason_code AS failure_reason_code, "
        "failure.invariant_code AS failure_invariant_code, "
        "failure.exception_category AS failure_exception_category, "
        "failure.provider_attempts AS failure_provider_attempts, "
        "failure.staffing_reason_codes AS failure_staffing_reason_codes, "
        "failure.hiring_reason_codes AS failure_hiring_reason_codes, "
        "failure.recorded_at AS failure_recorded_at "
        "FROM runs AS run JOIN preflight_failure_receipts AS failure "
        "ON failure.trace_id = run.trace_id AND failure.session_id = run.session_id "
        "WHERE run.host = ? AND run.preflight_request_fingerprint = ? "
        + session_clause
        + "AND run.status = 'preflight_failed' ORDER BY run.turn_sequence",
        parameters,
    ).fetchall()
    if len(rows) != 1:
        return None
    row = rows[0]
    session_id = validate_correlation_id(str(row["session_id"] or ""), field="session_id")
    trace_id = validate_correlation_id(str(row["trace_id"] or ""), field="trace_id")
    failure_row = {
        "id": str(row["failure_id"] or ""),
        "session_id": session_id,
        "trace_id": trace_id,
        "host": str(row["host"] or ""),
        "stage": row["failure_stage"],
        "reason_code": row["failure_reason_code"],
        "invariant_code": row["failure_invariant_code"],
        "exception_category": row["failure_exception_category"],
        "provider_attempts": row["failure_provider_attempts"],
        "staffing_reason_codes": row["failure_staffing_reason_codes"],
        "hiring_reason_codes": row["failure_hiring_reason_codes"],
        "recorded_at": str(row["failure_recorded_at"] or ""),
    }
    failure = {**failure_row, **_decode_preflight_failure_receipt(failure_row)}
    snapshot = _empty_canary_activation_snapshot(
        host=host,
        query_hash=query_hash,
        route_count=0,
        reason="preflight_failed",
    )
    snapshot.update(
        session_id=session_id,
        trace_id=trace_id,
        cardinalities={
            **snapshot["cardinalities"],
            "runs": 1,
            "traces": 1,
            "preflight_failures": 1,
        },
        run={
            "id": str(row["id"] or ""),
            "trace_id": trace_id,
            "session_id": session_id,
            "host": str(row["host"] or ""),
            "started_at": str(row["started_at"] or ""),
            "last_activity_at": str(row["last_activity_at"] or ""),
            "evidence_revision": int(row["evidence_revision"] or 0),
            "turn_sequence": int(row["turn_sequence"] or 0),
            "ended_at": row["ended_at"],
            "status": str(row["status"] or ""),
            "terminal_finalization_id": row["terminal_finalization_id"],
            "preflight_state": str(row["preflight_state"] or ""),
            "request_fingerprint": str(row["preflight_request_fingerprint"] or ""),
            "request_kind": str(row["preflight_request_kind"] or ""),
        },
        preflight_failure=failure,
    )
    return snapshot


def _canary_scope_consistent(
    *,
    session_id: str,
    trace_id: str,
    host: str,
    delegations: list[dict[str, Any]],
    activation_grants: list[dict[str, Any]],
    activation_consumptions: list[dict[str, Any]],
    worker_runs: list[dict[str, Any]],
    specialist_loads: list[dict[str, Any]],
    finalizations: list[dict[str, Any]],
) -> bool:
    correlated = (
        delegations,
        activation_grants,
        activation_consumptions,
        worker_runs,
        specialist_loads,
    )
    hosted = (
        delegations,
        activation_grants,
        activation_consumptions,
        worker_runs,
        finalizations,
    )
    return all(
        str(item.get("session_id") or "") == session_id
        and str(item.get("trace_id") or "") == trace_id
        for collection in correlated
        for item in collection
    ) and all(
        str(item.get("host") or item.get("child_host") or "") == host
        for collection in hosted
        for item in collection
    )


def _canary_resolution_reason(
    *,
    route_projection_valid: bool,
    ready_recipe: bool,
    recipe_valid: bool,
    recipe_matches: bool,
    scope_consistent: bool,
    finalization_projection_valid: bool,
    run_state_consistent: bool,
) -> str | None:
    if not route_projection_valid:
        return "route_projection_invalid"
    if not ready_recipe:
        return "preflight_not_ready"
    if not recipe_valid:
        return "preflight_recipe_invalid"
    if not recipe_matches:
        return "preflight_recipe_mismatch"
    if not scope_consistent:
        return "evidence_scope_mismatch"
    if not finalization_projection_valid:
        return "finalization_projection_invalid"
    if not run_state_consistent:
        return "run_state_inconsistent"
    return None


_EXECUTED_DELEGATION_STATUSES = frozenset({"started", "running", "delegated", "completed"})


def _matches_consumed_activation_lineage(
    conn: Any,
    existing: Any,
    *,
    worker_kind: str,
    worker_id: str,
    native_run_id: str,
) -> bool:
    """Allow correction only to lineage proven by a consumed one-use grant."""

    if str(existing["activation_receipt_id"] or ""):
        return False
    row = conn.execute(
        "SELECT consumption.worker_kind, consumption.worker_id, "
        "consumption.native_run_id FROM delegation_activation_consumptions AS consumption "
        "WHERE consumption.session_id = ? AND consumption.trace_id = ? "
        "AND consumption.work_unit_id = ? "
        "AND consumption.specialist_slug = ? LIMIT 1",
        (
            str(existing["session_id"] or ""),
            str(existing["trace_id"] or ""),
            str(existing["work_unit_id"] or ""),
            str(existing["recommended_agent"] or ""),
        ),
    ).fetchone()
    return row is not None and (
        str(row["worker_kind"] or ""),
        str(row["worker_id"] or ""),
        str(row["native_run_id"] or ""),
    ) == (worker_kind, worker_id, native_run_id)


def _bounded_metadata(value: object) -> dict[str, Any]:
    """Decode only the small content-free run metadata projection."""

    return decode_run_metadata(value)


def _projection_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _require_execution_correlation(
    *,
    status: str,
    trace_id: str,
    session_id: str,
    work_unit_id: str,
    backend: str,
    worker_kind: str,
    worker_id: str,
    native_run_id: str,
) -> None:
    """Reject positive delegation claims without complete execution identity."""

    if status not in _EXECUTED_DELEGATION_STATUSES:
        return
    missing = [
        name
        for name, value in (
            ("trace_id", trace_id),
            ("session_id", session_id),
            ("work_unit_id", work_unit_id),
            ("backend", backend),
            ("executed_worker_kind", worker_kind),
            ("executed_worker_id", worker_id),
            ("native_run_id", native_run_id),
        )
        if not str(value or "").strip()
    ]
    if missing:
        raise ValueError("executed delegation evidence requires non-empty " + ", ".join(missing))


def _prepare_delegation_transition(
    conn: Any,
    existing: Any,
    *,
    status: str,
    backend: str,
    error: str,
    recommended_agent: str,
    executed_worker_kind: str,
    executed_worker_id: str,
    native_run_id: str,
    skip_reason: str,
    host: str,
    now: str,
) -> dict[str, Any]:
    """Validate and project one transition without mutating durable state."""

    normalized_status = _normalize_delegation_status(status)
    current_status = _normalize_delegation_status(existing["status"])
    safe_host = _bounded_delegation_field(host, maximum=_MAX_DELEGATION_HOST_CHARS)
    safe_backend = _bounded_delegation_field(
        backend,
        maximum=_MAX_DELEGATION_BACKEND_CHARS,
    )
    safe_recommended_agent = _bounded_delegation_field(
        recommended_agent,
        maximum=_MAX_DELEGATION_AGENT_CHARS,
    )
    safe_worker_kind = _bounded_delegation_field(
        executed_worker_kind,
        maximum=_MAX_DELEGATION_WORKER_KIND_CHARS,
    )
    safe_worker_id = _bounded_delegation_field(
        executed_worker_id,
        maximum=_MAX_DELEGATION_WORKER_ID_CHARS,
    )
    safe_native_run_id = _bounded_delegation_field(
        native_run_id,
        maximum=_MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
    )
    incoming_receipt = (
        safe_backend,
        safe_worker_kind,
        safe_worker_id,
        safe_native_run_id,
    )
    existing_receipt = (
        str(existing["backend"] or ""),
        str(existing["executed_worker_kind"] or ""),
        str(existing["executed_worker_id"] or ""),
        str(existing["native_run_id"] or ""),
    )
    _require_execution_correlation(
        status=normalized_status,
        trace_id=str(existing["trace_id"] or ""),
        session_id=str(existing["session_id"] or ""),
        work_unit_id=str(existing["work_unit_id"] or ""),
        backend=safe_backend,
        worker_kind=safe_worker_kind,
        worker_id=safe_worker_id,
        native_run_id=safe_native_run_id,
    )
    authoritative_lineage_correction = _matches_consumed_activation_lineage(
        conn,
        existing,
        worker_kind=safe_worker_kind,
        worker_id=safe_worker_id,
        native_run_id=safe_native_run_id,
    )
    if (
        current_status in _EXECUTED_DELEGATION_STATUSES
        and normalized_status in _EXECUTED_DELEGATION_STATUSES
        and incoming_receipt != existing_receipt
        and not authoritative_lineage_correction
    ):
        raise ValueError("executed delegation correlation conflicts with existing receipt")
    effective_status = _dominant_delegation_status(current_status, normalized_status)
    recommendation_can_initialize = (
        current_status == "suggested" and normalized_status == "suggested"
    )
    incoming_wins = effective_status == normalized_status and (
        _DELEGATION_STATUS_PRIORITY.get(normalized_status, 0)
        >= _DELEGATION_STATUS_PRIORITY.get(current_status, 0)
    )
    effective_backend = (
        safe_backend or str(existing["backend"] or "")
        if incoming_wins
        else str(existing["backend"] or "")
    )
    effective_worker_kind = (
        safe_worker_kind or str(existing["executed_worker_kind"] or "")
        if incoming_wins
        else str(existing["executed_worker_kind"] or "")
    )
    effective_worker_id = (
        safe_worker_id or str(existing["executed_worker_id"] or "")
        if incoming_wins
        else str(existing["executed_worker_id"] or "")
    )
    effective_native_run_id = (
        safe_native_run_id or str(existing["native_run_id"] or "")
        if incoming_wins
        else str(existing["native_run_id"] or "")
    )
    _require_execution_correlation(
        status=effective_status,
        trace_id=str(existing["trace_id"] or ""),
        session_id=str(existing["session_id"] or ""),
        work_unit_id=str(existing["work_unit_id"] or ""),
        backend=effective_backend,
        worker_kind=effective_worker_kind,
        worker_id=effective_worker_id,
        native_run_id=effective_native_run_id,
    )
    effective_error = (
        error or str(existing["error"] or "") if incoming_wins else str(existing["error"] or "")
    )
    effective_skip_reason = (
        skip_reason or str(existing["skip_reason"] or "")
        if incoming_wins
        else str(existing["skip_reason"] or "")
    )
    completed_at = existing["completed_at"]
    if effective_status in _TERMINAL_DELEGATION_STATUSES and effective_status != current_status:
        completed_at = now
    return {
        "status": effective_status,
        "host": safe_host,
        "backend": safe_backend,
        "worker_kind": safe_worker_kind,
        "worker_id": safe_worker_id,
        "native_run_id": safe_native_run_id,
        "error": effective_error,
        "recommended_agent": safe_recommended_agent,
        "skip_reason": effective_skip_reason,
        "completed_at": completed_at,
        "incoming_wins": incoming_wins,
        "recommendation_can_initialize": recommendation_can_initialize,
    }


class EvidenceStoreMixin(PreflightStoreMixin):
    """Evidence-domain behavior composed into the canonical SQLite store."""

    # ── Host runtime controls ─────────────────────────────────────

    def get_host_control(self, host: str) -> dict[str, Any]:
        """Return persistent soft-control state without mutating the store."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT host, enabled, generation, updated_at, source "
                "FROM host_controls WHERE host = ?",
                (normalized,),
            ).fetchone()
            if row is None:
                return {
                    "host": normalized,
                    "enabled": True,
                    "generation": 0,
                    "updated_at": None,
                    "source": "default",
                }
            return {
                "host": str(row["host"]),
                "enabled": bool(row["enabled"]),
                "generation": int(row["generation"]),
                "updated_at": str(row["updated_at"]),
                "source": str(row["source"]),
            }
        finally:
            conn.close()

    def ensure_host_control_materialized(
        self,
        host: str,
        *,
        source: str = "install",
    ) -> dict[str, Any]:
        """Create an enabled generation-zero host control without changing existing state."""

        normalized = str(host or "").strip().lower()
        if not normalized:
            raise ValueError("host is required")
        normalized_source = str(source or "install").strip()[:96] or "install"
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT host, enabled, generation, updated_at, source "
                "FROM host_controls WHERE host = ?",
                (normalized,),
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO host_controls "
                    "(host, enabled, generation, updated_at, source) "
                    f"VALUES (?, 1, 0, {STORE_CLOCK_SQL}, ?)",  # nosec B608
                    (normalized, normalized_source),
                )
                current = conn.execute(
                    "SELECT host, enabled, generation, updated_at, source "
                    "FROM host_controls WHERE host = ?",
                    (normalized,),
                ).fetchone()
            if current is None:
                raise RuntimeError("host-control materialization postcondition failed")
            result = {
                "host": str(current["host"]),
                "enabled": bool(current["enabled"]),
                "generation": int(current["generation"]),
                "updated_at": str(current["updated_at"]),
                "source": str(current["source"]),
            }
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def set_host_control(
        self,
        host: str,
        *,
        enabled: bool,
        expected_generation: int,
        source: str = "runtime",
    ) -> dict[str, Any]:
        """Apply one atomic host-control compare-and-swap transition."""
        normalized = str(host or "").strip().lower()
        if not normalized:
            raise ValueError("host is required")
        if (
            isinstance(expected_generation, bool)
            or not isinstance(expected_generation, int)
            or not 0 <= expected_generation <= MAX_HOST_CONTROL_GENERATION
        ):
            raise ValueError("expected host-control generation is invalid")
        if not isinstance(enabled, bool):
            raise ValueError("host-control enabled value must be boolean")
        normalized_source = str(source or "runtime").strip()[:96] or "runtime"
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT host, enabled, generation, updated_at, source "
                "FROM host_controls WHERE host = ?",
                (normalized,),
            ).fetchone()
            observed_generation = int(current["generation"]) if current is not None else 0
            if observed_generation != expected_generation:
                raise HostControlConflictError(
                    "host-control generation changed "
                    f"(expected {expected_generation}, found {observed_generation})"
                )
            effective_enabled = bool(current["enabled"]) if current is not None else True
            if effective_enabled is enabled:
                result = (
                    {
                        "host": normalized,
                        "enabled": True,
                        "generation": 0,
                        "updated_at": None,
                        "source": "default",
                    }
                    if current is None
                    else {
                        "host": str(current["host"]),
                        "enabled": bool(current["enabled"]),
                        "generation": observed_generation,
                        "updated_at": str(current["updated_at"]),
                        "source": str(current["source"]),
                    }
                )
                conn.commit()
            else:
                if observed_generation >= MAX_HOST_CONTROL_GENERATION:
                    raise ValueError("host-control generation is exhausted")
                next_generation = observed_generation + 1
                updated_at = self._now()
                if current is None:
                    conn.execute(
                        "INSERT INTO host_controls "
                        "(host, enabled, generation, updated_at, source) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            normalized,
                            int(enabled),
                            next_generation,
                            updated_at,
                            normalized_source,
                        ),
                    )
                else:
                    updated = conn.execute(
                        "UPDATE host_controls SET enabled = ?, generation = ?, "
                        "updated_at = ?, source = ? WHERE host = ? AND generation = ?",
                        (
                            int(enabled),
                            next_generation,
                            updated_at,
                            normalized_source,
                            normalized,
                            observed_generation,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise HostControlConflictError(
                            "host-control generation changed during update"
                        )
                result = {
                    "host": normalized,
                    "enabled": enabled,
                    "generation": next_generation,
                    "updated_at": updated_at,
                    "source": normalized_source,
                }
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return result

    def get_host_canary_attestation(self, host: str) -> dict[str, Any] | None:
        """Return the latest content-free canary attestation for a host."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT host, proof_contract, proof_digest, profile_scope, "
                "platform_system, platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id "
                "FROM host_canary_attestations WHERE host = ?",
                (normalized,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()

    def record_host_canary_attestation(
        self,
        *,
        host: str,
        proof_contract: str,
        proof_digest: str,
        profile_scope: str,
        platform_system: str,
        platform_release: str,
        platform_machine: str,
        host_version: str,
        plugin_version: str,
        install_id: str,
        bundle_digest: str,
        trace_id: str,
        passed_at: str | None = None,
    ) -> dict[str, Any]:
        """Persist one bounded successful canary without prompts or output."""
        validated_trace = validate_correlation_id(trace_id, field="trace_id")
        from agency_runtime.core.installer_contracts import (
            CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        )

        normalized_digest = str(proof_digest or "").strip()
        if (
            str(proof_contract or "").strip() != CODEX_ACTIVATION_CANARY_PROOF_CONTRACT
            or len(normalized_digest) != 64
            or any(character not in "0123456789abcdef" for character in normalized_digest)
        ):
            raise ValueError("current host canary proof contract and digest are required")
        values = {
            "host": str(host or "").strip().lower()[:64],
            "proof_contract": CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
            "proof_digest": normalized_digest,
            "profile_scope": str(profile_scope or "").strip().lower()[:64],
            "platform_system": str(platform_system or "").strip()[:64],
            "platform_release": str(platform_release or "").strip()[:128],
            "platform_machine": str(platform_machine or "").strip()[:128],
            "host_version": str(host_version or "").strip()[:256],
            "plugin_version": str(plugin_version or "").strip()[:64],
            "install_id": str(install_id or "").strip()[:128],
            "bundle_digest": str(bundle_digest or "").strip()[:128],
            "trace_id": validated_trace,
            "passed_at": str(passed_at or self._now()).strip()[:64],
        }
        if any(not values[key] for key in values):
            raise ValueError("complete host canary attestation fields are required")
        if values["profile_scope"] not in {"current-profile", "isolated-profile"}:
            raise ValueError("profile_scope must be current-profile or isolated-profile")
        if values["host"] != "codex" or values["profile_scope"] != "current-profile":
            raise ValueError(
                "durable activation attestation requires a Codex current-profile canary"
            )
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO host_canary_attestations "
                "(host, proof_contract, proof_digest, profile_scope, platform_system, "
                "platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(host) DO UPDATE SET "
                "proof_contract = excluded.proof_contract, "
                "proof_digest = excluded.proof_digest, "
                "profile_scope = excluded.profile_scope, "
                "platform_system = excluded.platform_system, "
                "platform_release = excluded.platform_release, "
                "platform_machine = excluded.platform_machine, "
                "host_version = excluded.host_version, "
                "plugin_version = excluded.plugin_version, "
                "install_id = excluded.install_id, "
                "bundle_digest = excluded.bundle_digest, "
                "passed_at = excluded.passed_at, trace_id = excluded.trace_id",
                (
                    values["host"],
                    values["proof_contract"],
                    values["proof_digest"],
                    values["profile_scope"],
                    values["platform_system"],
                    values["platform_release"],
                    values["platform_machine"],
                    values["host_version"],
                    values["plugin_version"],
                    values["install_id"],
                    values["bundle_digest"],
                    values["passed_at"],
                    values["trace_id"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
        attestation = self.get_host_canary_attestation(values["host"])
        if attestation is None or any(
            attestation.get(field) != expected for field, expected in values.items()
        ):
            raise RuntimeError("canary attestation postcondition failed")
        return attestation

    def clear_host_canary_attestation(self, host: str) -> bool:
        """Invalidate a host attestation after rollback or lifecycle replacement."""
        normalized = str(host or "").strip().lower()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM host_canary_attestations WHERE host = ?",
                (normalized,),
            )
            conn.commit()
            return bool(cursor.rowcount)
        finally:
            conn.close()

    # ── Runs ───────────────────────────────────────────────────────

    def create_run(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        user_message: str = "",
        metadata: dict | None = None,
    ) -> str:
        capture_content = self._capture_content_enabled()
        trace_id = validate_correlation_id(trace_id or self._uuid(), field="trace_id")
        session_id = validate_correlation_id(
            session_id,
            field="session_id",
            required=False,
        )
        run_id = self._uuid()
        captured_message = (
            redact_sensitive_text(user_message, _RUN_CONTENT_LIMIT) if capture_content else ""
        )
        safe_metadata = project_run_metadata(metadata)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT id, session_id, status, metadata, "
                "preflight_request_fingerprint FROM runs WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["session_id"] or "") != str(session_id or ""):
                    raise ValueError("trace_id already belongs to a different session")
                status = str(existing["status"])
                if status == "active":
                    existing_fingerprint = str(
                        existing["preflight_request_fingerprint"] or ""
                    ) or _request_fingerprint(existing["metadata"])
                    requested_fingerprint = _request_fingerprint(safe_metadata)
                    if (
                        existing_fingerprint or requested_fingerprint
                    ) and existing_fingerprint != requested_fingerprint:
                        raise ValueError("active trace_id belongs to a different preflight request")
                    conn.execute(
                        f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                        "WHERE id = ?",
                        (existing["id"],),
                    )
                    conn.commit()
                    return str(existing["id"])
                if status != "evidence_only":
                    raise ValueError("trace_id belongs to a terminal turn")
                conn.execute(
                    "UPDATE runs SET host = ?, status = 'active', "
                    "user_message = ?, metadata = ?, "
                    f"last_activity_at = {STORE_CLOCK_SQL} WHERE id = ?",  # nosec B608
                    (host, captured_message, safe_metadata, existing["id"]),
                )
                conn.commit()
                return str(existing["id"])
            self._assert_trace_not_retired(conn, trace_id)
            conn.execute(
                "INSERT INTO runs (id, trace_id, session_id, host, started_at, status, user_message, metadata) "
                f"VALUES (?, ?, ?, ?, {STORE_CLOCK_SQL}, 'active', ?, ?)",  # nosec B608
                (
                    run_id,
                    trace_id,
                    session_id,
                    host,
                    captured_message,
                    safe_metadata,
                ),
            )
            conn.commit()
            return run_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def reserve_session_turn(
        self,
        *,
        session_id: str,
        trace_id: str,
        host: str = "unknown",
    ) -> dict[str, Any]:
        """Atomically reserve one current turn and abandon older open traces.

        Native hosts can miss a Stop callback after a crash. Reserving the next
        external prompt in SQLite ensures that stale open traces cannot make
        later no-turn-id callbacks ambiguous. The ``evidence_only`` reservation
        is promoted by ``create_run`` once preflight persists its request
        fingerprint and classification.
        """
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_host = str(host or "unknown").strip() or "unknown"
        if not normalized_session or not normalized_trace:
            raise ValueError("session_id and trace_id are required to reserve a turn")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT id, session_id, status, reservation_token, "
                "preflight_state FROM runs WHERE trace_id = ?",
                (normalized_trace,),
            ).fetchone()
            if existing is not None:
                if str(existing["session_id"] or "") != normalized_session:
                    raise ValueError("trace_id already belongs to a different session")
                if str(existing["status"] or "") not in {"active", "evidence_only"}:
                    raise ValueError("trace_id belongs to a terminal turn")

            abandoned = [
                str(row["trace_id"])
                for row in conn.execute(
                    "SELECT trace_id FROM runs WHERE session_id = ? AND trace_id <> ? "
                    "AND status IN ('active', 'evidence_only') ORDER BY started_at, rowid",
                    (normalized_session, normalized_trace),
                ).fetchall()
            ]
            reserved_at = self._now()
            if abandoned:
                closed = conn.execute(
                    "UPDATE runs SET ended_at = COALESCE(ended_at, ?), status = 'abandoned' "
                    "WHERE session_id = ? AND trace_id <> ? "
                    "AND status IN ('active', 'evidence_only')",
                    (reserved_at, normalized_session, normalized_trace),
                )
                if closed.rowcount != len(abandoned):
                    raise RuntimeError("abandoned-turn compare-and-swap failed")
                for abandoned_trace in abandoned:
                    conn.execute(
                        "UPDATE specialists_loaded SET expired_at = ? "
                        "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                        (reserved_at, normalized_session, abandoned_trace),
                    )

            created = existing is None
            reservation_receipt = ""
            if created:
                self._assert_trace_not_retired(conn, normalized_trace)
                reservation_receipt = self._uuid()
                reservation_metadata = project_run_metadata({"source": "hook_reservation"})
                conn.execute(
                    "INSERT INTO runs "
                    "(id, trace_id, session_id, host, started_at, last_activity_at, status, "
                    "user_message, metadata, reservation_token, preflight_state) "
                    f"VALUES (?, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
                    "'evidence_only', '', ?, ?, 'reserved')",
                    (
                        self._uuid(),
                        normalized_trace,
                        normalized_session,
                        normalized_host,
                        reserved_at,
                        reservation_metadata,
                        reservation_receipt,
                    ),
                )
            if existing is not None:
                existing_state = str(existing["preflight_state"] or "")
                if existing_state in {"reserved", "in_progress", "ready"}:
                    reservation_receipt = str(existing["reservation_token"] or "")
                conn.execute(
                    f"UPDATE runs SET last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ?",
                    (existing["id"],),
                )
            conn.commit()
            return {
                "trace_id": normalized_trace,
                "created": created,
                "abandoned": abandoned,
                "reservation_token": reservation_receipt,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def complete_run(self, run_id: str, status: str = "completed") -> None:
        """Close one unbound active run without rewriting terminal truth."""
        normalized_status = str(status or "").strip()
        if not normalized_status or normalized_status in {"active", "evidence_only"}:
            raise ValueError("run completion requires a terminal status")
        closed_at = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT trace_id, session_id FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if run is None:
                conn.commit()
                return
            closed = conn.execute(
                "UPDATE runs SET ended_at = COALESCE(ended_at, ?), status = ?, "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE id = ? AND terminal_finalization_id IS NULL "
                "AND status IN ('active', 'evidence_only')",
                (closed_at, normalized_status, run_id),
            )
            if closed.rowcount != 1:
                conn.commit()
                return
            conn.execute(
                "UPDATE specialists_loaded SET expired_at = ? "
                "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                (closed_at, str(run["session_id"] or ""), str(run["trace_id"] or "")),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fail_canary_run(
        self,
        run_id: str,
        *,
        host: str,
        request_fingerprint: str,
    ) -> bool:
        """Close one active run proven to belong to an exact canary request."""

        normalized_run = validate_correlation_id(run_id, field="run_id")
        normalized_host = str(host or "").strip().casefold()
        fingerprint = str(request_fingerprint or "").strip()
        if not normalized_host or len(normalized_host) > 64:
            raise ValueError("canary host is invalid")
        if len(fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in fingerprint
        ):
            raise ValueError("canary request fingerprint must be a lowercase SHA-256 digest")
        closed_at = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT id, trace_id, session_id FROM runs "
                "WHERE id = ? AND host = ? "
                "AND (preflight_request_fingerprint = ? OR EXISTS ("
                "SELECT 1 FROM routing_decisions AS routing "
                "WHERE routing.trace_id = runs.trace_id AND routing.query_hash = ?"
                ")) LIMIT 1",
                (normalized_run, normalized_host, fingerprint, fingerprint),
            ).fetchone()
            if run is None:
                conn.commit()
                return False
            closed = conn.execute(
                "UPDATE runs SET ended_at = COALESCE(ended_at, ?), "
                "status = 'canary_failed', "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE id = ? AND terminal_finalization_id IS NULL "
                "AND status IN ('active', 'evidence_only')",
                (closed_at, normalized_run),
            )
            if closed.rowcount != 1:
                conn.commit()
                return False
            conn.execute(
                "UPDATE specialists_loaded SET expired_at = ? "
                "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                (closed_at, str(run["session_id"] or ""), str(run["trace_id"] or "")),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fail_canary_runs_for_request(
        self,
        *,
        host: str,
        request_fingerprint: str,
    ) -> list[str]:
        """Close every still-open run bound to one exact nonce-derived request."""

        normalized_host = str(host or "").strip().casefold()
        fingerprint = str(request_fingerprint or "").strip()
        if not normalized_host or len(normalized_host) > 64:
            raise ValueError("canary host is invalid")
        if len(fingerprint) != 64 or any(
            character not in "0123456789abcdef" for character in fingerprint
        ):
            raise ValueError("canary request fingerprint must be a lowercase SHA-256 digest")
        closed_at = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT id, trace_id, session_id FROM runs WHERE host = ? "
                "AND status IN ('active', 'evidence_only') "
                "AND terminal_finalization_id IS NULL "
                "AND (preflight_request_fingerprint = ? OR EXISTS ("
                "SELECT 1 FROM routing_decisions AS routing "
                "WHERE routing.trace_id = runs.trace_id AND routing.query_hash = ?"
                ")) ORDER BY started_at, rowid LIMIT 257",
                (normalized_host, fingerprint, fingerprint),
            ).fetchall()
            if len(rows) > 256:
                raise RuntimeError("canary request matched an unsafe number of active runs")
            closed: list[str] = []
            for row in rows:
                updated = conn.execute(
                    "UPDATE runs SET ended_at = COALESCE(ended_at, ?), "
                    "status = 'canary_failed', "
                    f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                    "WHERE id = ? AND terminal_finalization_id IS NULL "
                    "AND status IN ('active', 'evidence_only')",
                    (closed_at, str(row["id"])),
                )
                if updated.rowcount != 1:
                    raise RuntimeError("canary run cleanup compare-and-swap failed")
                conn.execute(
                    "UPDATE specialists_loaded SET expired_at = ? "
                    "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                    (closed_at, str(row["session_id"] or ""), str(row["trace_id"] or "")),
                )
                closed.append(str(row["id"]))
            conn.commit()
            return closed
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Model receipts ─────────────────────────────────────────────

    def record_model_receipt(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        requested_model: str = "",
        model_group: str = "",
        resolved_provider: str = "",
        resolved_model: str = "",
        api_base: str = "",
        attempted_fallbacks: int = 0,
        model_id: str = "",
        source: str = "unknown",
        started_at: str = "",
        ended_at: str = "",
        latency_ms: int = 0,
        status: str = "success",
    ) -> str:
        """Persist bounded generic telemetry without granting router trust.

        A source value of litellm on this public/generic API is deliberately
        downgraded by the ingress normalizer. Only the callback-specific
        private method below can assign authoritative LiteLLM provenance.
        """

        return self._persist_model_receipt(
            provenance=_ReceiptProvenance.GENERIC,
            trace_id=trace_id,
            session_id=session_id,
            host=host,
            requested_model=requested_model,
            model_group=model_group,
            resolved_provider=resolved_provider,
            resolved_model=resolved_model,
            api_base=api_base,
            attempted_fallbacks=attempted_fallbacks,
            model_id=model_id,
            source=source,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
            status=status,
        )

    def _record_litellm_model_receipt(self, **values: Any) -> str:
        """Persist evidence from the installed LiteLLM terminal callback.

        This path is intentionally separate from record_model_receipt so a
        public caller cannot gain authority by supplying a source label.
        """

        values["source"] = "litellm"
        return self._persist_model_receipt(
            provenance=_ReceiptProvenance.LITELLM_CALLBACK,
            **values,
        )

    def _persist_model_receipt(
        self,
        *,
        provenance: _ReceiptProvenance,
        **values: Any,
    ) -> str:
        receipt_id = self._uuid()
        normalized = _normalize_receipt_ingress(values, provenance=provenance)
        trace_id = validate_correlation_id(
            normalized["trace_id"] or receipt_id,
            field="trace_id",
        )
        session_id = validate_correlation_id(
            normalized["session_id"],
            field="session_id",
            required=False,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._ensure_run(
                conn,
                trace_id=trace_id,
                session_id=session_id,
                host=normalized["host"],
            )
            conn.execute(
                "INSERT INTO model_receipts "
                "(id, trace_id, session_id, host, requested_model, model_group, "
                "resolved_provider, resolved_model, api_base, attempted_fallbacks, "
                "model_id, source, recorded_at, started_at, ended_at, latency_ms, status) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
                "?, ?, ?, ?)",
                (
                    receipt_id,
                    trace_id,
                    session_id,
                    normalized["host"],
                    normalized["requested_model"],
                    normalized["model_group"],
                    normalized["resolved_provider"],
                    normalized["resolved_model"],
                    normalized["api_base"],
                    normalized["attempted_fallbacks"],
                    normalized["model_id"],
                    normalized["source"],
                    normalized["started_at"] or self._now(),
                    normalized["ended_at"] or self._now(),
                    normalized["latency_ms"],
                    normalized["status"],
                ),
            )
            conn.commit()
            return receipt_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_model_receipt(self, trace_id: str) -> dict[str, Any] | None:
        """Return the strongest receipt for a trace, newest among equal evidence."""

        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE trace_id = ? "
                f"ORDER BY {MODEL_RECEIPT_AUTHORITY_ORDER_SQL} LIMIT 1",  # nosec B608
                (trace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_model_receipt_for_session(self, session_id: str) -> dict[str, Any] | None:
        """Get authoritative evidence from the session's most recently observed trace."""
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM model_receipts WHERE session_id = ? AND trace_id = ("
                "SELECT trace_id FROM model_receipts WHERE session_id = ? "
                "ORDER BY recorded_at DESC, rowid DESC LIMIT 1) "
                f"ORDER BY {MODEL_RECEIPT_AUTHORITY_ORDER_SQL} LIMIT 1",  # nosec B608
                (session_id, session_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Skills ─────────────────────────────────────────────────────

    def record_skill_loaded(
        self,
        session_id: str,
        skill_name: str,
        *,
        trace_id: str = "",
    ) -> None:
        if not session_id or not skill_name:
            return
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(
            trace_id,
            field="trace_id",
            required=False,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if trace_id:
                self._ensure_run(conn, trace_id=trace_id, session_id=session_id)
            conn.execute(
                "INSERT INTO skills_loaded (id, session_id, trace_id, skill_name, loaded_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._uuid(), session_id, trace_id, skill_name, self._now()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_skills_for_trace(self, session_id: str, trace_id: str) -> list[str]:
        """Return skill evidence belonging to exactly one correlated turn."""
        if not session_id or not trace_id:
            return []
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT skill_name FROM skills_loaded "
                "WHERE session_id = ? AND trace_id = ? ORDER BY loaded_at, rowid",
                (session_id, trace_id),
            )
            return [row["skill_name"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_skills_for_session(self, session_id: str) -> list[str]:
        """Return immutable skill-load history for a session."""
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT skill_name FROM skills_loaded "
                "WHERE session_id = ? ORDER BY loaded_at, rowid",
                (session_id,),
            )
            return [row["skill_name"] for row in cur.fetchall()]
        finally:
            conn.close()

    # ── Specialists ────────────────────────────────────────────────

    def record_specialist_loaded(
        self,
        session_id: str,
        agent_slug: str,
        *,
        trace_id: str = "",
    ) -> None:
        if not session_id or not agent_slug:
            return
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(
            trace_id,
            field="trace_id",
            required=False,
        )
        loaded_at = self._now()
        # Legacy callers remain auditable, but an uncorrelated row is closed
        # immediately and can never become active turn evidence.
        expired_at = None if trace_id else loaded_at
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if trace_id:
                self._ensure_run(conn, trace_id=trace_id, session_id=session_id)
            conn.execute(
                "INSERT INTO specialists_loaded "
                "(id, session_id, trace_id, agent_slug, loaded_at, expired_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, trace_id, agent_slug) DO NOTHING",
                (self._uuid(), session_id, trace_id, agent_slug, loaded_at, expired_at),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_active_specialists_for_trace(self, session_id: str, trace_id: str) -> list[str]:
        """Return active specialist evidence for exactly one correlated turn."""
        if not session_id or not trace_id:
            return []
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT specialist.agent_slug FROM specialists_loaded AS specialist "
                "JOIN runs AS run ON run.trace_id = specialist.trace_id "
                "AND run.session_id = specialist.session_id "
                "WHERE specialist.session_id = ? AND specialist.trace_id = ? "
                "AND specialist.expired_at IS NULL "
                "AND run.status IN ('active', 'evidence_only') "
                "ORDER BY specialist.loaded_at, specialist.rowid",
                (session_id, trace_id),
            )
            return [row["agent_slug"] for row in cur.fetchall()]
        finally:
            conn.close()

    def get_specialists_for_trace(self, session_id: str, trace_id: str) -> list[str]:
        """Return immutable specialist evidence for exactly one turn."""
        if not session_id or not trace_id:
            return []
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT agent_slug FROM specialists_loaded "
                "WHERE session_id = ? AND trace_id = ? ORDER BY loaded_at, rowid",
                (session_id, trace_id),
            ).fetchall()
            return [str(row["agent_slug"]) for row in rows]
        finally:
            conn.close()

    def get_expired_specialists_to_announce(
        self,
        session_id: str,
        current_trace_id: str,
        *,
        limit: int = 8,
    ) -> list[str]:
        """Return cards that expired with the previous turn and are not held now.

        A card cannot be retracted once injected: ``additionalContext`` is a
        one-way per-event append with no clear or replace field, so an expired
        specialist stays legible in the scroll and keeps steering the generalist
        unless the next turn says otherwise. Expiry therefore has to be *stated*.

        Only the immediately preceding turn is considered, which is what keeps
        this from becoming the context bloat it exists to prevent: each expiry is
        announced on exactly one subsequent turn instead of accumulating a
        lengthening tombstone list for the rest of the session. A card reselected
        for the current turn is live again and is never announced.
        """

        if not session_id or not current_trace_id:
            return []
        session_id = validate_correlation_id(session_id, field="session_id")
        current_trace_id = validate_correlation_id(current_trace_id, field="current_trace_id")
        bounded = max(0, min(int(limit), 32))
        if not bounded:
            return []
        conn = self._connect()
        try:
            previous = conn.execute(
                "SELECT trace_id FROM specialists_loaded "
                "WHERE session_id = ? AND trace_id != ? AND trace_id != '' "
                "ORDER BY loaded_at DESC, rowid DESC LIMIT 1",
                (session_id, current_trace_id),
            ).fetchone()
            if previous is None:
                return []
            rows = conn.execute(
                "SELECT DISTINCT expired.agent_slug FROM specialists_loaded AS expired "
                "WHERE expired.session_id = ? AND expired.trace_id = ? "
                "AND expired.expired_at IS NOT NULL "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM specialists_loaded AS current "
                "  WHERE current.session_id = expired.session_id "
                "  AND current.trace_id = ? "
                "  AND current.agent_slug = expired.agent_slug"
                ") "
                "ORDER BY expired.agent_slug LIMIT ?",
                (session_id, str(previous["trace_id"]), current_trace_id, bounded),
            ).fetchall()
            return [str(row["agent_slug"]) for row in rows]
        finally:
            conn.close()

    def get_specialists_for_session(self, session_id: str) -> list[str]:
        """Return the ordered, deduplicated specialist audit history."""
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT agent_slug FROM specialists_loaded "
                "WHERE session_id = ? ORDER BY loaded_at, rowid",
                (session_id,),
            )
            seen: set[str] = set()
            result: list[str] = []
            for row in cur.fetchall():
                slug = str(row["agent_slug"])
                if slug not in seen:
                    seen.add(slug)
                    result.append(slug)
            return result
        finally:
            conn.close()

    def get_specialist_load_history(self, session_id: str) -> list[dict[str, Any]]:
        """Return immutable per-load rows, including completed turns."""
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, session_id, trace_id, agent_slug, loaded_at, expired_at "
                "FROM specialists_loaded WHERE session_id = ? ORDER BY loaded_at, rowid",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_native_child_staffing_decision(self, decision_id: str) -> dict[str, Any] | None:
        """Return one exact Agency decision expected by host-artifact verification.

        This row proves inference selection and immutable bindings only.  It is
        never delivery evidence: callers must independently read a native host
        artifact and match every returned field before claiming Rule 4.
        """

        normalized_id = validate_correlation_id(decision_id, field="decision_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, trace_id, session_id, query_hash, context_fingerprint, "
                "status, source, selected_ids, semantic_ids, companion_ids, decision, "
                "created_at FROM routing_decisions WHERE id = ?",
                (normalized_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return _project_native_child_staffing_row(row, decision_id=normalized_id)

    def get_native_child_delivery_verification(
        self,
        decision_id: str,
    ) -> dict[str, Any] | None:
        """Return one immutable, content-free host-artifact verification receipt."""

        normalized_id = validate_correlation_id(decision_id, field="decision_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT decision_id, nonce, artifact_digest, host, parent_session_id, "
                "parent_trace_id, launch_id, binding_kind, binding_id, child_id, verified_at "
                "FROM native_child_delivery_verifications WHERE decision_id = ?",
                (normalized_id,),
            ).fetchone()
        finally:
            conn.close()
        return None if row is None else {**dict(row), "verified_delivery": True}

    def list_native_child_delivery_verifications(
        self,
        *,
        host: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return a bounded newest-first window of immutable delivery receipts."""

        if type(limit) is not int or not 1 <= limit <= MAX_NATIVE_CHILD_DELIVERY_VERIFICATION_ROWS:
            raise ValueError(
                "native child delivery verification limit must be between 1 and "
                f"{MAX_NATIVE_CHILD_DELIVERY_VERIFICATION_ROWS}"
            )
        normalized_host: str | None = None
        if host is not None:
            normalized_host = validate_correlation_id(host, field="host").casefold()
            if normalized_host not in EXECUTION_HOSTS:
                raise ValueError("host must identify a supported execution host")
        conn = self._connect()
        try:
            fields = (
                "decision_id, nonce, artifact_digest, host, parent_session_id, "
                "parent_trace_id, launch_id, binding_kind, binding_id, child_id, verified_at "
            )
            rows = (
                conn.execute(
                    "SELECT " + fields + "FROM native_child_delivery_verifications "
                    "ORDER BY verified_at DESC, rowid DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                if normalized_host is None
                else conn.execute(
                    "SELECT " + fields + "FROM native_child_delivery_verifications WHERE host = ? "
                    "ORDER BY verified_at DESC, rowid DESC LIMIT ?",
                    (normalized_host, limit),
                ).fetchall()
            )
        finally:
            conn.close()
        return [{**dict(row), "verified_delivery": True} for row in rows]

    def _record_native_child_delivery_verification(
        self,
        *,
        decision_id: str,
        nonce: str,
        artifact_digest: str,
        host: str,
        parent_session_id: str,
        parent_trace_id: str,
        launch_id: str,
        binding_kind: str,
        binding_id: str,
        child_id: str,
        cards: object,
    ) -> dict[str, Any]:
        """Atomically consume one independently parsed native-host proof.

        The caller must first establish the host-specific pre-speech artifact
        contract. This method never accepts that conclusion as a boolean. It
        only revalidates exact durable inference identity and enforces one-use.
        It is deliberately private; the public minting path is the independent
        host-artifact verifier in ``child_delivery_evidence``.
        """

        normalized_id = validate_correlation_id(decision_id, field="decision_id")
        normalized_nonce = validate_correlation_id(nonce, field="nonce")
        supplied_artifact = validate_correlation_id(
            artifact_digest,
            field="artifact_digest",
        )
        normalized_artifact = content_digest_identity(supplied_artifact)
        if normalized_artifact is None or normalized_artifact != supplied_artifact:
            raise ValueError("artifact_digest must be a lowercase SHA-256 digest")
        normalized_host = validate_correlation_id(host, field="host").casefold()
        if normalized_host not in EXECUTION_HOSTS:
            raise ValueError("host must identify a supported execution host")
        normalized_session = validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        )
        normalized_trace = validate_correlation_id(
            parent_trace_id,
            field="parent_trace_id",
        )
        normalized_launch = validate_correlation_id(launch_id, field="launch_id")
        normalized_kind = validate_correlation_id(binding_kind, field="binding_kind")
        normalized_binding = validate_correlation_id(binding_id, field="binding_id")
        normalized_child = validate_correlation_id(child_id, field="child_id")

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT route.id, route.trace_id, route.session_id, route.query_hash, "
                "route.context_fingerprint, route.status, route.source, route.selected_ids, "
                "route.semantic_ids, route.companion_ids, route.decision, route.created_at, "
                "run.host AS run_host, run.status AS run_status, run.ended_at AS run_ended_at, "
                "run.terminal_finalization_id AS run_terminal_finalization_id, "
                "finalization.id AS finalization_id, "
                "finalization.created_at AS finalization_created_at "
                "FROM routing_decisions AS route JOIN runs AS run "
                "ON run.trace_id = route.trace_id AND run.session_id = route.session_id "
                "LEFT JOIN finalization_events AS finalization "
                "ON finalization.id = run.terminal_finalization_id "
                "AND finalization.trace_id = run.trace_id "
                "WHERE route.id = ?",
                (normalized_id,),
            ).fetchone()
            expected = (
                None
                if row is None
                else _project_native_child_staffing_row(row, decision_id=normalized_id)
            )
            run_is_open = bool(
                row is not None
                and row["run_status"] in {"active", "evidence_only"}
                and row["run_ended_at"] is None
                and row["run_terminal_finalization_id"] is None
            )
            run_is_closed = bool(
                row is not None
                and row["run_status"] not in {"active", "evidence_only", "retention_expired"}
                and row["run_ended_at"] is not None
                and row["created_at"] <= row["run_ended_at"]
                and (
                    (row["run_terminal_finalization_id"] is None and row["finalization_id"] is None)
                    or (
                        row["finalization_id"] == row["run_terminal_finalization_id"]
                        and row["finalization_created_at"] is not None
                        and row["created_at"] <= row["finalization_created_at"]
                    )
                )
            )
            if (
                expected is None
                or row is None
                or not (run_is_open or run_is_closed)
                or str(row["run_host"] or "").casefold() != normalized_host
                or expected["host"] != normalized_host
                or expected["parent_session_id"] != normalized_session
                or expected["parent_trace_id"] != normalized_trace
                or expected["launch_id"] != normalized_launch
                or expected["binding_kind"] != normalized_kind
                or expected["binding_id"] != normalized_binding
                or expected["nonce"] != normalized_nonce
            ):
                raise ValueError("native child delivery verification identity does not match")
            from agency_runtime.core.native_child_decision import (
                project_native_child_staffing_decision,
            )

            decision_payload = {
                key: value
                for key, value in expected.items()
                if key
                not in {
                    "decision_id",
                    "trace_id",
                    "session_id",
                    "query_hash",
                    "context_fingerprint",
                    "created_at",
                }
            }
            observed_cards = project_native_child_staffing_decision(
                {**decision_payload, "cards": cards}
            )
            if observed_cards is None or observed_cards["cards"] != expected["cards"]:
                raise ValueError("native child delivery card identity does not match")
            if normalized_kind == "child_id":
                if normalized_binding != normalized_child:
                    raise ValueError("native child delivery child binding does not match")
            elif normalized_kind == "launch_id":
                if normalized_binding != normalized_launch:
                    raise ValueError("native child delivery launch binding does not match")
                host_launch = conn.execute(
                    "SELECT 1 FROM worker_runs WHERE host = ? AND session_id = ? "
                    "AND trace_id = ? AND worker_id = ? AND execution_tool_use_id = ? "
                    "AND execution_dispatched_at IS NOT NULL LIMIT 1",
                    (
                        normalized_host,
                        normalized_session,
                        normalized_trace,
                        normalized_child,
                        normalized_launch,
                    ),
                ).fetchone()
                if host_launch is None:
                    raise ValueError("native child delivery host launch binding is unavailable")
            else:
                raise ValueError("native child delivery binding kind is unsupported")
            conn.execute(
                "INSERT INTO native_child_delivery_verifications "
                "(decision_id, nonce, artifact_digest, host, parent_session_id, "
                "parent_trace_id, launch_id, binding_kind, binding_id, child_id, verified_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",  # nosec B608
                (
                    normalized_id,
                    normalized_nonce,
                    normalized_artifact,
                    normalized_host,
                    normalized_session,
                    normalized_trace,
                    normalized_launch,
                    normalized_kind,
                    normalized_binding,
                    normalized_child,
                ),
            )
            stored = conn.execute(
                "SELECT decision_id, nonce, artifact_digest, host, parent_session_id, "
                "parent_trace_id, launch_id, binding_kind, binding_id, child_id, verified_at "
                "FROM native_child_delivery_verifications WHERE decision_id = ?",
                (normalized_id,),
            ).fetchone()
            if stored is None:
                raise RuntimeError("native child delivery verification postcondition failed")
            conn.commit()
            return {**dict(stored), "verified_delivery": True}
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise ValueError(
                "native child delivery verification proof was already consumed"
            ) from exc
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_canary_activation_snapshot(
        self,
        *,
        host: str,
        query_hash: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Read one exact, content-free canary evidence graph in one transaction.

        ``proven`` means only that one route and its parent run were resolved and
        their ready preflight recipe passed correlation checks.  Callers must
        still evaluate the returned activation/delegation topology. When
        ``session_id`` is supplied, both ready and failed-preflight resolution
        are bound to that exact host session instead of every historical use of
        the same prompt hash. This method never turns the presence of a route
        into an activation-success claim.
        """

        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in EXECUTION_HOSTS:
            raise ValueError("host must identify a supported execution host")
        supplied_hash = str(query_hash or "").strip()
        normalized_hash = content_digest_identity(supplied_hash)
        if normalized_hash is None or normalized_hash != supplied_hash:
            raise ValueError("query_hash must be a lowercase SHA-256 digest")
        normalized_session = (
            None if session_id is None else validate_correlation_id(session_id, field="session_id")
        )
        session_clause = "" if normalized_session is None else "AND run.session_id = ? "
        route_parameters = (
            (normalized_hash, normalized_host)
            if normalized_session is None
            else (normalized_hash, normalized_host, normalized_session)
        )

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            route_count_row = conn.execute(
                "SELECT COUNT(*) AS count FROM routing_decisions AS route "
                "JOIN runs AS run ON run.trace_id = route.trace_id "
                "AND run.session_id = route.session_id "
                "WHERE route.query_hash = ? AND run.host = ? "
                + session_clause
                + "AND run.preflight_request_fingerprint = route.query_hash",
                route_parameters,
            ).fetchone()
            route_count = int(route_count_row["count"] if route_count_row is not None else 0)
            if route_count != 1:
                snapshot = (
                    _failed_preflight_canary_snapshot(
                        conn,
                        host=normalized_host,
                        query_hash=normalized_hash,
                        session_id=normalized_session,
                    )
                    if route_count == 0
                    else None
                ) or _empty_canary_activation_snapshot(
                    host=normalized_host,
                    query_hash=normalized_hash,
                    route_count=route_count,
                    reason="route_not_found" if route_count == 0 else "route_ambiguous",
                )
                if normalized_session is not None and snapshot.get("session_id") is None:
                    snapshot["session_id"] = normalized_session
                conn.commit()
                return snapshot

            row = conn.execute(
                "SELECT route.id AS route_id, route.trace_id AS route_trace_id, "
                "route.session_id AS route_session_id, route.query_hash AS route_query_hash, "
                "route.context_fingerprint AS route_context_fingerprint, "
                "route.status AS route_status, route.source AS route_source, "
                "route.selected_ids AS route_selected_ids, "
                "route.semantic_ids AS route_semantic_ids, "
                "route.companion_ids AS route_companion_ids, "
                "route.confidence AS route_confidence, "
                "route.latency_ms AS route_latency_ms, route.provider AS route_provider, "
                "route.work_units AS route_work_units, route.created_at AS route_created_at, "
                "run.id AS run_id, run.trace_id AS run_trace_id, "
                "run.session_id AS run_session_id, run.host AS run_host, "
                "run.started_at AS run_started_at, "
                "run.last_activity_at AS run_last_activity_at, "
                "run.evidence_revision AS run_evidence_revision, "
                "run.turn_sequence AS run_turn_sequence, run.ended_at AS run_ended_at, "
                "run.status AS run_status, "
                "run.terminal_finalization_id AS run_terminal_finalization_id, "
                "run.preflight_state AS run_preflight_state, "
                "run.preflight_request_fingerprint AS run_request_fingerprint, "
                "run.preflight_request_kind AS run_request_kind, "
                "run.metadata AS run_metadata, "
                "run.preflight_result AS run_preflight_result "
                "FROM routing_decisions AS route JOIN runs AS run "
                "ON run.trace_id = route.trace_id AND run.session_id = route.session_id "
                "WHERE route.query_hash = ? AND run.host = ? "
                + session_clause
                + "AND run.preflight_request_fingerprint = route.query_hash",
                route_parameters,
            ).fetchone()
            if row is None:
                raise RuntimeError("exact canary route disappeared inside its read transaction")

            normalized_session = validate_correlation_id(
                str(row["run_session_id"] or ""),
                field="session_id",
            )
            normalized_trace = validate_correlation_id(
                str(row["run_trace_id"] or ""),
                field="trace_id",
            )
            run = {
                "id": str(row["run_id"] or ""),
                "trace_id": normalized_trace,
                "session_id": normalized_session,
                "host": str(row["run_host"] or ""),
                "started_at": str(row["run_started_at"] or ""),
                "last_activity_at": str(row["run_last_activity_at"] or ""),
                "evidence_revision": int(row["run_evidence_revision"] or 0),
                "turn_sequence": int(row["run_turn_sequence"] or 0),
                "ended_at": row["run_ended_at"],
                "status": str(row["run_status"] or ""),
                "terminal_finalization_id": row["run_terminal_finalization_id"],
                "preflight_state": str(row["run_preflight_state"] or ""),
                "request_fingerprint": str(row["run_request_fingerprint"] or ""),
                "request_kind": str(row["run_request_kind"] or ""),
            }
            from agency_runtime.core.codex_activation_verification import (
                CODEX_RECONCILIATION_DIAGNOSTIC_REASONS,
            )

            run_metadata = decode_run_metadata(row["run_metadata"])
            hook_diagnostic = str(run_metadata.get("canary_hook_diagnostic") or "")
            if hook_diagnostic not in CODEX_RECONCILIATION_DIAGNOSTIC_REASONS:
                hook_diagnostic = ""

            selected_ids = _project_canary_strings(
                row["route_selected_ids"],
                maximum_chars=256,
            )
            semantic_ids = _project_canary_strings(
                row["route_semantic_ids"],
                maximum_chars=256,
            )
            companion_ids = _project_canary_strings(
                row["route_companion_ids"],
                maximum_chars=256,
            )
            work_units = _project_canary_work_units(row["route_work_units"])
            context_fingerprint = str(row["route_context_fingerprint"] or "")
            route_projection_valid = (
                selected_ids is not None
                and semantic_ids is not None
                and companion_ids is not None
                and work_units is not None
                and content_digest_identity(context_fingerprint) == context_fingerprint
            )
            route = {
                "id": str(row["route_id"] or ""),
                "trace_id": str(row["route_trace_id"] or ""),
                "session_id": str(row["route_session_id"] or ""),
                "query_hash": str(row["route_query_hash"] or ""),
                "context_fingerprint": context_fingerprint,
                "status": str(row["route_status"] or ""),
                "source": str(row["route_source"] or ""),
                "selected_ids": selected_ids or [],
                "semantic_ids": semantic_ids or [],
                "companion_ids": companion_ids or [],
                "confidence": row["route_confidence"],
                "latency_ms": row["route_latency_ms"],
                "provider": str(row["route_provider"] or ""),
                "work_units": work_units or {},
                "created_at": str(row["route_created_at"] or ""),
            }

            (
                native_child_route_count,
                native_child_delivery_count,
                native_child_route,
                native_child_delivery,
                host_child_delivery,
            ) = _bounded_canary_native_child_join(
                conn,
                host=normalized_host,
                session_id=normalized_session,
                trace_id=normalized_trace,
            )

            counts = conn.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM delegation_events WHERE trace_id = ?) "
                "AS delegations, "
                "(SELECT COUNT(*) FROM delegation_activation_receipts WHERE trace_id = ?) "
                "AS activation_grants, "
                "(SELECT COUNT(*) FROM delegation_activation_consumptions WHERE trace_id = ?) "
                "AS activation_consumptions, "
                "(SELECT COUNT(*) FROM worker_runs WHERE trace_id = ?) AS worker_runs, "
                "(SELECT COUNT(*) FROM specialists_loaded WHERE trace_id = ?) "
                "AS specialist_loads, "
                "(SELECT COUNT(*) FROM finalization_events WHERE trace_id = ?) "
                "AS finalizations",
                (normalized_trace,) * 6,
            ).fetchone()
            cardinalities = {
                "routes": 1,
                "native_child_routes": native_child_route_count,
                "native_child_deliveries": native_child_delivery_count,
                "runs": 1,
                "traces": 1,
                "delegations": int(counts["delegations"]),
                "activation_grants": int(counts["activation_grants"]),
                "activation_consumptions": int(counts["activation_consumptions"]),
                "worker_runs": int(counts["worker_runs"]),
                "specialist_loads": int(counts["specialist_loads"]),
                "finalizations": int(counts["finalizations"]),
                "preflight_failures": 0,
            }
            snapshot = _empty_canary_activation_snapshot(
                host=normalized_host,
                query_hash=normalized_hash,
                route_count=1,
                reason="exact_route_resolved",
            )
            snapshot.update(
                session_id=normalized_session,
                trace_id=normalized_trace,
                cardinalities=cardinalities,
                run=run,
                route=route,
                native_child_route=native_child_route,
                native_child_delivery=native_child_delivery,
                host_child_delivery=host_child_delivery,
                hook_diagnostic=hook_diagnostic,
            )
            if any(
                cardinalities[name] > _CANARY_ACTIVATION_MAX_ROWS
                for name in (
                    "native_child_routes",
                    "native_child_deliveries",
                    "delegations",
                    "activation_grants",
                    "activation_consumptions",
                    "worker_runs",
                    "specialist_loads",
                    "finalizations",
                )
            ):
                snapshot["reason"] = "evidence_cardinality_exceeded"
                conn.commit()
                return snapshot

            delegations = [
                dict(item)
                for item in conn.execute(
                    "SELECT id, trace_id, session_id, host, work_unit_id, "
                    "recommended_agent, status, backend, executed_worker_kind, "
                    "executed_worker_id, native_run_id, retrieved_specialist_slug, "
                    "retrieved_specialist_version, retrieved_specialist_prompt_hash, "
                    "activation_receipt_id, started_at, completed_at "
                    "FROM delegation_events WHERE trace_id = ? ORDER BY started_at, rowid",
                    (normalized_trace,),
                ).fetchall()
            ]
            activation_grants = [
                dict(item)
                for item in conn.execute(
                    "SELECT id, grant_id, grant_issued_unix, grant_expires_unix, "
                    "child_host, grant_origin, tool_use_id, session_id, trace_id, "
                    "work_unit_id, specialist_slug, "
                    "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
                    "native_run_id, created_at, consumed_at, delegation_event_id "
                    "FROM delegation_activation_receipts WHERE trace_id = ? "
                    "ORDER BY created_at, rowid",
                    (normalized_trace,),
                ).fetchall()
            ]
            activation_consumptions = [
                dict(item)
                for item in conn.execute(
                    "SELECT id, grant_id, legacy_activation_receipt_id, session_id, "
                    "trace_id, work_unit_id, child_host, specialist_slug, "
                    "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
                    "native_run_id, consumed_at, consumed_unix "
                    "FROM delegation_activation_consumptions WHERE trace_id = ? "
                    "ORDER BY consumed_at, rowid",
                    (normalized_trace,),
                ).fetchall()
            ]
            worker_runs = [
                _project_canary_worker_run(item)
                for item in conn.execute(
                    "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                    "work_unit_id, host, worker_id, native_run_id, exit_code, "
                    "started_at, execution_tool_use_id, execution_dispatched_at, "
                    "tool_evidence_schema, tool_evidence, tool_evidence_source, "
                    "tool_evidence_recorded_at, ended_at "
                    "FROM worker_runs WHERE trace_id = ? ORDER BY started_at, rowid",
                    (normalized_trace,),
                ).fetchall()
            ]
            specialist_loads = [
                dict(item)
                for item in conn.execute(
                    "SELECT id, session_id, trace_id, agent_slug, loaded_at, expired_at, "
                    "activation_receipt_id FROM specialists_loaded WHERE trace_id = ? "
                    "ORDER BY loaded_at, rowid",
                    (normalized_trace,),
                ).fetchall()
            ]
            finalizations: list[dict[str, Any]] = []
            finalization_projection_valid = True
            for item in conn.execute(
                "SELECT id, trace_id, host, action, missing, response_hash, "
                "policy_response_hash, terminal_status, created_at "
                "FROM finalization_events WHERE trace_id = ? ORDER BY created_at, rowid",
                (normalized_trace,),
            ).fetchall():
                projected = dict(item)
                raw_missing = projected.pop("missing", None)
                missing = (
                    _project_canary_strings(raw_missing, maximum_items=64) if raw_missing else []
                )
                if missing is None:
                    finalization_projection_valid = False
                    missing = []
                projected["missing"] = missing
                finalizations.append(projected)

            ready_recipe = run["preflight_state"] == "ready"
            try:
                recipe = (
                    _decode_preflight_recipe(
                        row["run_preflight_result"],
                        session_id=normalized_session,
                        trace_id=normalized_trace,
                    )
                    if ready_recipe
                    else None
                )
            except Exception:
                recipe = None
            snapshot.update(
                delegations=delegations,
                activation_grants=activation_grants,
                activation_consumptions=activation_consumptions,
                worker_runs=worker_runs,
                specialist_loads=specialist_loads,
                finalizations=finalizations,
            )

            scope_consistent = _canary_scope_consistent(
                session_id=normalized_session,
                trace_id=normalized_trace,
                host=normalized_host,
                delegations=delegations,
                activation_grants=activation_grants,
                activation_consumptions=activation_consumptions,
                worker_runs=worker_runs,
                specialist_loads=specialist_loads,
                finalizations=finalizations,
            )
            recipe_routing = recipe.get("routing") if isinstance(recipe, dict) else None
            recipe_matches = (
                isinstance(recipe, dict)
                and recipe.get("session_id") == normalized_session
                and recipe.get("trace_id") == normalized_trace
                and recipe.get("host") == normalized_host
                and isinstance(recipe_routing, dict)
                and recipe_routing.get("trace_id") == normalized_trace
                and recipe_routing.get("query_hash") == normalized_hash
                and recipe_routing.get("selected_ids") == route["selected_ids"]
                and recipe_routing.get("work_units") == route["work_units"]
            )
            run_state_consistent = not (
                run["status"] in {"active", "evidence_only"}
                and (bool(run["ended_at"]) or bool(run["terminal_finalization_id"]))
            )
            reason = _canary_resolution_reason(
                route_projection_valid=route_projection_valid,
                ready_recipe=ready_recipe,
                recipe_valid=recipe is not None,
                recipe_matches=recipe_matches,
                scope_consistent=scope_consistent,
                finalization_projection_valid=finalization_projection_valid,
                run_state_consistent=run_state_consistent,
            )
            if reason is None:
                snapshot["proven"] = True
                snapshot["status"] = "resolved"
                reason = "exact_route_resolved"
            snapshot["reason"] = reason
            conn.commit()
            return snapshot
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def close_turn_evidence(
        self,
        session_id: str,
        trace_id: str,
        *,
        status: str = "completed",
    ) -> int:
        """Atomically close one active run, returning the run CAS result."""
        if not session_id or not trace_id:
            return 0
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        normalized_status = str(status or "").strip()
        if not normalized_status or normalized_status in {"active", "evidence_only"}:
            raise ValueError("turn closure requires a terminal status")
        closed_at = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            closed = conn.execute(
                "UPDATE runs SET ended_at = COALESCE(ended_at, ?), status = ?, "
                f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
                "WHERE trace_id = ? AND session_id = ? "
                "AND status IN ('active', 'evidence_only')",
                (closed_at, normalized_status, trace_id, session_id),
            )
            if closed.rowcount != 1:
                conn.commit()
                return 0
            conn.execute(
                "UPDATE specialists_loaded SET expired_at = ? "
                "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                (closed_at, session_id, trace_id),
            )
            conn.commit()
            return int(closed.rowcount)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_run(self, trace_id: str) -> dict[str, Any] | None:
        """Return one trace parent for deterministic correlation checks."""
        if not trace_id:
            return None
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT id, trace_id, session_id, host, started_at, last_activity_at, "
                "turn_sequence, ended_at, status, preflight_state "
                "FROM runs WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_withheld_and_published_runs(
        self,
        *,
        host: str = "",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return recently closed turns that Agency withheld or observed while blind.

        Rule 8 draws exactly one line: Agency withholds a turn only when its
        verifier evaluated the response and rejected it, never because Agency
        itself was unavailable. Both sides of that line close a run with a
        distinguishable status, so this one read makes Agency's outcome
        auditable after the fact instead of leaving it a claim about the code.
        A blind status alone does not prove what the host did with the response;
        historical rows can predate the pass-through rule.

        Read-only, and deliberately not filtered to a session: a withheld turn
        is rare enough to be worth seeing across the whole store.
        """

        bounded = max(1, min(int(limit), 500))
        statuses = sorted(_WITHHELD_RUN_STATUSES | _PUBLISHED_ANYWAY_RUN_STATUSES)
        placeholders = ",".join("?" for _ in statuses)
        parameters: list[Any] = list(statuses)
        host_clause = ""
        if host:
            host_clause = " AND host = ?"
            parameters.append(host)
        parameters.append(bounded)
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT trace_id, session_id, host, started_at, ended_at, status "  # nosec B608
                f"FROM runs WHERE status IN ({placeholders}){host_clause} "
                "ORDER BY COALESCE(ended_at, started_at) DESC, rowid DESC "
                "LIMIT ?",
                tuple(parameters),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_routing_latencies(
        self,
        *,
        source: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return recent routing decisions with a recorded latency.

        ``routing_decisions.latency_ms`` is the persisted routing duration.
        Nothing previously surfaced it, so recorded routing cost was
        unanswerable without opening the database by hand.

        Zero is excluded, not counted as a fast turn.  Both writers store ``0``
        rather than NULL when no provider call was spent -- an abstained turn,
        or a contract check that never routed -- so including them would report
        routing as cheap in exact proportion to how often it did nothing.  On
        this store that alone moved p50 by tens of seconds.

        Read-only, newest first, and not filtered to a session: the question is
        what recorded routing costs in general, not what it cost once.
        """

        bounded = max(1, min(int(limit), 1000))
        parameters: list[Any] = []
        source_clause = ""
        if source:
            source_clause = " AND d.source = ?"
            parameters.append(source)
        parameters.append(bounded)
        conn = self._connect()
        try:
            rows = conn.execute(
                # The provider subtotal comes from timed receipts on the same
                # trace. The shared projection treats it as attributable only
                # when every same-trace receipt is timed and the subtotal does
                # not exceed the persisted routing duration; the remainder is
                # derived and must never be presented as independent timing.
                "SELECT d.trace_id, d.session_id, d.status, d.source, "  # nosec B608
                "d.provider, d.latency_ms, d.confidence, d.created_at, "
                "COALESCE(("
                " SELECT SUM(r.latency_ms) FROM model_receipts AS r"
                " WHERE r.trace_id = d.trace_id"
                "), 0) AS provider_ms, "
                "COALESCE(("
                " SELECT COUNT(*) FROM model_receipts AS r"
                " WHERE r.trace_id = d.trace_id"
                "), 0) AS provider_calls, "
                "COALESCE(("
                " SELECT SUM(CASE WHEN r.latency_ms > 0 THEN 1 ELSE 0 END)"
                " FROM model_receipts AS r WHERE r.trace_id = d.trace_id"
                "), 0) AS provider_timed_calls, "
                "COALESCE(("
                " SELECT SUM(CASE WHEN r.latency_ms <= 0 THEN 1 ELSE 0 END)"
                " FROM model_receipts AS r WHERE r.trace_id = d.trace_id"
                "), 0) AS provider_unknown_calls "
                "FROM routing_decisions AS d "
                f"WHERE d.latency_ms IS NOT NULL AND d.latency_ms > 0{source_clause} "
                "ORDER BY d.created_at DESC, d.rowid DESC LIMIT ?",
                tuple(parameters),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_cached_routing(
        self,
        cache_key: str,
        *,
        max_age_seconds: float = 600.0,
    ) -> dict[str, Any] | None:
        """Return a still-fresh persisted routing decision, or None.

        The in-memory cache this backs cannot hit in production -- each hook
        event is its own process -- so without a persisted copy every turn pays
        full routing.  Freshness is enforced here rather than at the call site
        so a stale row can never be served by a caller that forgot to check.
        """

        key = str(cache_key or "").strip()
        if not key:
            return None
        conn = self._connect()
        try:
            # The cutoff must be rendered in the same format the rows were
            # written in. DATETIME() yields "2026-08-11 19:33:02" while
            # STORE_CLOCK_SQL writes "2026-08-11T19:33:02.999000+00:00", and
            # 'T' sorts above ' ', so comparing across the two formats silently
            # accepts every row and the expiry does nothing at all.
            row = conn.execute(
                "SELECT routing, created_at FROM routing_cache WHERE cache_key = ? "  # nosec B608
                f"AND created_at >= {STORE_CLOCK_CUTOFF_SQL}",
                (key, f"-{max(0.0, float(max_age_seconds))} seconds"),
            ).fetchone()
        except sqlite3.Error:
            return None
        finally:
            conn.close()
        if row is None:
            return None
        try:
            value = safe_load_bounded_json(
                str(row["routing"]),
                maximum_bytes=_ROUTING_CACHE_MAX_BYTES,
                maximum_depth=6,
                maximum_nodes=512,
            )
        except (ValueError, TypeError):
            return None
        return value if isinstance(value, dict) else None

    def put_cached_routing(
        self,
        cache_key: str,
        routing: Mapping[str, Any],
        *,
        context_fingerprint: str = "",
        max_entries: int = 512,
    ) -> bool:
        """Persist one routing decision for reuse by a later hook process.

        Only fields already allowlisted for persistence are written.  The live
        routing dict also carries work-unit text and unit descriptors that the
        decision projection deliberately drops, and a cache is not a reason to
        widen what the store retains -- so what cannot be persisted is left out
        and recomputed from the live catalog when the entry is reused.
        """

        key = str(cache_key or "").strip()
        if not key or not isinstance(routing, Mapping):
            return False
        payload = {field: routing[field] for field in _ROUTING_DECISION_FIELDS if field in routing}
        if not payload.get("selected_ids"):
            return False
        encoded = json.dumps(payload, sort_keys=True, default=str)
        if len(encoded.encode("utf-8")) > _ROUTING_CACHE_MAX_BYTES:
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO routing_cache "
                "(cache_key, context_fingerprint, source_message_hash, routing, created_at) "
                f"VALUES (?, ?, ?, ?, {STORE_CLOCK_SQL}) "  # nosec B608
                "ON CONFLICT(cache_key) DO UPDATE SET "
                "context_fingerprint = excluded.context_fingerprint, "
                "source_message_hash = excluded.source_message_hash, "
                "routing = excluded.routing, created_at = excluded.created_at",
                (
                    key,
                    str(context_fingerprint or ""),
                    str(routing.get("source_message_hash") or ""),
                    encoded,
                ),
            )
            conn.execute(
                "DELETE FROM routing_cache WHERE cache_key NOT IN ("
                "SELECT cache_key FROM routing_cache ORDER BY created_at DESC, rowid DESC LIMIT ?"
                ")",
                (max(1, int(max_entries)),),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def record_routing_intent(
        self,
        routing: Mapping[str, Any],
        *,
        trace_id: str = "",
        session_id: str = "",
        max_entries: int = _ROUTING_INTENT_MAX_ROWS,
    ) -> bool:
        """Retain what the planner understood the request to be, for auditing.

        This is the one routing table that keeps content, and it exists because
        the others do not: with only ``source_message_hash`` and ``query_hash``
        persisted, no one can ask afterwards whether a turn was staffed
        sensibly.  Callers must gate this on ``selector.record_routing_intent``;
        the store does not enable retention on its own.

        Work-unit text is the planner's own restatement of the request, not the
        raw message, and it is bounded per unit and in total so one enormous
        prompt cannot turn the operator's database into a transcript.
        """

        if not isinstance(routing, Mapping):
            return False
        work_units = routing.get("work_units")
        units_value = work_units.get("units") if isinstance(work_units, Mapping) else None
        units = _bounded_intent_units(units_value)
        selected = [
            str(item)[:128]
            for item in (routing.get("selected_ids") or [])
            if isinstance(item, str) and item.strip()
        ][:32]
        if not units and not selected:
            return False
        descriptors = routing.get("workforce_unit_descriptors")
        encoded_units = json.dumps(units, sort_keys=True, default=str)
        encoded_descriptors = json.dumps(
            descriptors if isinstance(descriptors, list) else [], sort_keys=True, default=str
        )
        if (
            len(encoded_units.encode("utf-8")) + len(encoded_descriptors.encode("utf-8"))
            > _ROUTING_INTENT_MAX_BYTES
        ):
            return False
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO routing_intent "
                "(trace_id, session_id, query_hash, context_fingerprint, units, "
                "descriptors, selected_ids, source, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",  # nosec B608
                (
                    str(trace_id or routing.get("trace_id") or ""),
                    str(session_id or ""),
                    str(routing.get("query_hash") or ""),
                    str(routing.get("context_fingerprint") or ""),
                    encoded_units,
                    encoded_descriptors,
                    json.dumps(selected, default=str),
                    str(routing.get("source") or ""),
                ),
            )
            conn.execute(
                "DELETE FROM routing_intent WHERE id NOT IN ("
                "SELECT id FROM routing_intent ORDER BY id DESC LIMIT ?)",
                (max(1, int(max_entries)),),
            )
            conn.commit()
            return True
        except sqlite3.Error:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_routing_intents(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent retained intents, newest first, for the audit surface."""

        bounded = max(1, min(int(limit), 500))
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT trace_id, query_hash, units, descriptors, selected_ids, source, "
                "created_at FROM routing_intent ORDER BY id DESC LIMIT ?",
                (bounded,),
            ).fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for field in ("units", "descriptors", "selected_ids"):
                try:
                    item[field] = json.loads(item.get(field) or "[]")
                except (TypeError, ValueError):
                    item[field] = []
            result.append(item)
        return result

    def get_open_traces_for_session(self, session_id: str) -> list[str]:
        """Return deterministic, non-terminal turn traces for a session."""
        if not session_id:
            return []
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT trace_id FROM runs "
                "WHERE session_id = ? AND status IN ('active', 'evidence_only') "
                "ORDER BY started_at, rowid",
                (session_id,),
            ).fetchall()
            return [str(row["trace_id"]) for row in rows]
        finally:
            conn.close()

    def get_turn_request_kind(self, session_id: str, trace_id: str) -> str | None:
        """Return the persisted classification for exactly one correlated turn."""

        if not session_id or not trace_id:
            return None
        session_id = validate_correlation_id(session_id, field="session_id")
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COALESCE(NULLIF(preflight_request_kind, ''), "
                "CASE WHEN json_valid(metadata) "
                "THEN json_extract(metadata, '$.request_kind') ELSE NULL END) "
                "AS request_kind FROM runs WHERE session_id = ? AND trace_id = ?",
                (session_id, trace_id),
            ).fetchone()
            if row is None or row["request_kind"] not in {"trivial", "nontrivial"}:
                return None
            return str(row["request_kind"])
        finally:
            conn.close()

    def get_turn_state_context(
        self,
        session_id: str,
        *,
        before_trace_id: str = "",
    ) -> dict[str, Any]:
        """Return bounded state that can disambiguate the next external turn."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(
            before_trace_id,
            field="trace_id",
            required=False,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            previous = conn.execute(
                "SELECT trace_id, status, metadata, preflight_result "
                "FROM runs WHERE session_id = ? "
                "AND (? = '' OR trace_id <> ?) "
                "ORDER BY turn_sequence DESC LIMIT 1",
                (normalized_session, normalized_trace, normalized_trace),
            ).fetchone()
            generation_row = conn.execute(
                "SELECT value FROM store_counters WHERE name = 'roster-generation'"
            ).fetchone()
            roster_revision = str(int(generation_row["value"])) if generation_row else "0"
            if previous is None:
                conn.commit()
                return {"state_known": True, "roster_revision": roster_revision}

            previous_trace = str(previous["trace_id"] or "")
            previous_status = str(previous["status"] or "")
            metadata = _bounded_metadata(previous["metadata"])
            try:
                recipe = _decode_preflight_recipe(
                    previous["preflight_result"],
                    session_id=normalized_session,
                    trace_id=previous_trace,
                )
            except Exception:
                recipe = None
            recipe = recipe if isinstance(recipe, dict) else {}
            references = recipe.get("specialist_refs")
            references = references if isinstance(references, list) else []
            delegation_rows = [
                {
                    "work_unit_id": str(row["work_unit_id"] or ""),
                    "recommended_agent": str(row["recommended_agent"] or ""),
                    "status": str(row["status"] or ""),
                }
                for row in conn.execute(
                    "SELECT work_unit_id, recommended_agent, status "
                    "FROM delegation_events WHERE trace_id = ? "
                    "ORDER BY work_unit_id, id",
                    (previous_trace,),
                ).fetchall()
            ]
            retry_pending = (
                conn.execute(
                    "SELECT 1 FROM finalization_events WHERE trace_id = ? "
                    "AND action IN ('continue', 'validation_continue') "
                    "AND terminal_status IS NULL LIMIT 1",
                    (previous_trace,),
                ).fetchone()
                is not None
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        pending = str(metadata.get("pending_interaction") or "")
        selection_required = metadata.get("selection_required") is True
        if "selection_required" not in metadata and isinstance(recipe.get("trivial"), bool):
            selection_required = not bool(recipe["trivial"])
        incomplete_delegation = any(
            row["status"] not in _TERMINAL_DELEGATION_STATUSES for row in delegation_rows
        )
        retry_pending = bool(
            retry_pending and previous_status in {"active", "evidence_only", "abandoned"}
        )
        active_plan = bool(
            previous_status in {"active", "evidence_only", "abandoned"}
            and (selection_required or delegation_rows)
        )
        previous_turn_kind = str(metadata.get("turn_kind") or "")
        if not previous_turn_kind:
            previous_turn_kind = (
                "acknowledgement"
                if str(metadata.get("request_kind") or "") == "trivial"
                else "new_intent"
            )
        return {
            "state_known": True,
            "previous_trace_id": previous_trace,
            "previous_status": previous_status,
            "previous_turn_kind": previous_turn_kind,
            "active_plan": active_plan,
            "unfinished_work": bool(active_plan or incomplete_delegation),
            "pending_question": pending == "question",
            "pending_authorization": pending == "authorization",
            "retry_pending": retry_pending,
            "configuration_revision": str(recipe.get("policy_fingerprint") or ""),
            "roster_revision": roster_revision,
            "specialist_revision": _projection_digest(references) if references else "",
            "delegation_revision": (_projection_digest(delegation_rows) if delegation_rows else ""),
        }

    def is_nontrivial_turn(self, session_id: str, trace_id: str) -> bool | None:
        """Return tri-state durable turn complexity for fail-closed consumers."""

        kind = self.get_turn_request_kind(session_id, trace_id)
        return None if kind is None else kind == "nontrivial"

    def is_nontrivial_trace(self, session_id: str, trace_id: str) -> bool | None:
        """Compatibility alias for the exact-trace complexity query."""

        return self.is_nontrivial_turn(session_id, trace_id)

    # ── Delegation events ──────────────────────────────────────────

    def record_suggested_delegations_batch(
        self,
        *,
        trace_id: str,
        session_id: str,
        host: str = "unknown",
        suggestions: list[dict[str, str]],
    ) -> int:
        """Persist a bounded suggestion set in one correlated transaction."""

        if not trace_id or not session_id:
            raise ValueError("trace_id and session_id are required for delegation suggestions")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        normalized_session = validate_correlation_id(session_id, field="session_id")
        unique: dict[str, str] = {}
        for suggestion in suggestions[:16]:
            work_unit_id = str(suggestion.get("work_unit_id") or "").strip()[:512]
            if not work_unit_id or work_unit_id in unique:
                continue
            unique[work_unit_id] = str(suggestion.get("recommended_agent") or "").strip()[:256]
        if not unique:
            return 0

        now = self._now()
        inserted = 0
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._ensure_run(
                conn,
                trace_id=normalized_trace,
                session_id=normalized_session,
                host=host,
            )
            for work_unit_id, recommended_agent in unique.items():
                cursor = conn.execute(
                    "INSERT INTO delegation_events "
                    "(id, trace_id, session_id, host, work_unit_id, "
                    "recommended_agent, status, backend, skip_reason, error, "
                    "started_at, completed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'suggested', '', '', '', ?, NULL) "
                    "ON CONFLICT DO NOTHING",
                    (
                        self._uuid(),
                        normalized_trace,
                        normalized_session,
                        str(host or "unknown").strip() or "unknown",
                        work_unit_id,
                        recommended_agent,
                        now,
                    ),
                )
                inserted += max(0, int(cursor.rowcount))
            conn.commit()
            return inserted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record_delegation(
        self,
        *,
        trace_id: str,
        session_id: str = "",
        host: str = "unknown",
        work_unit_id: str = "",
        recommended_agent: str = "",
        status: str = "suggested",
        backend: str = "",
        executed_worker_kind: str = "",
        executed_worker_id: str = "",
        native_run_id: str = "",
        skip_reason: str = "",
        error: str = "",
    ) -> str:
        event_id = self._uuid()
        raw_trace_id = str(trace_id or "").strip()
        normalized_status = _normalize_delegation_status(status)
        trace_id = validate_correlation_id(raw_trace_id or event_id, field="trace_id")
        session_id = validate_correlation_id(
            session_id,
            field="session_id",
            required=False,
        )
        safe_host = _bounded_delegation_field(host, maximum=_MAX_DELEGATION_HOST_CHARS)
        safe_work_unit_id = _bounded_delegation_field(
            work_unit_id,
            maximum=_MAX_DELEGATION_WORK_UNIT_ID_CHARS,
        )
        safe_recommended_agent = _bounded_delegation_field(
            recommended_agent,
            maximum=_MAX_DELEGATION_AGENT_CHARS,
        )
        safe_backend = _bounded_delegation_field(
            backend,
            maximum=_MAX_DELEGATION_BACKEND_CHARS,
        )
        safe_worker_kind = _bounded_delegation_field(
            executed_worker_kind,
            maximum=_MAX_DELEGATION_WORKER_KIND_CHARS,
        )
        safe_worker_id = _bounded_delegation_field(
            executed_worker_id,
            maximum=_MAX_DELEGATION_WORKER_ID_CHARS,
        )
        safe_native_run_id = _bounded_delegation_field(
            native_run_id,
            maximum=_MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
        )
        capture_content = self._capture_content_enabled()
        safe_skip_reason = project_delegation_detail(
            skip_reason,
            field="skip_reason",
            capture_content=capture_content,
        )
        safe_error = project_delegation_detail(
            error,
            field="error",
            capture_content=capture_content,
        )
        now = self._now()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            self._ensure_run(conn, trace_id=trace_id, session_id=session_id, host=safe_host)
            _require_execution_correlation(
                status=normalized_status,
                trace_id=raw_trace_id,
                session_id=session_id,
                work_unit_id=safe_work_unit_id,
                backend=safe_backend,
                worker_kind=safe_worker_kind,
                worker_id=safe_worker_id,
                native_run_id=safe_native_run_id,
            )
            existing = None
            if safe_work_unit_id:
                existing = conn.execute(
                    "SELECT * FROM delegation_events "
                    "WHERE trace_id = ? AND work_unit_id = ? LIMIT 1",
                    (trace_id, safe_work_unit_id),
                ).fetchone()
            if existing is not None:
                self._merge_delegation_transition(
                    conn,
                    existing,
                    status=normalized_status,
                    backend=safe_backend,
                    error=safe_error,
                    recommended_agent=safe_recommended_agent,
                    executed_worker_kind=safe_worker_kind,
                    executed_worker_id=safe_worker_id,
                    native_run_id=safe_native_run_id,
                    skip_reason=safe_skip_reason,
                    host=safe_host,
                    now=now,
                )
                conn.commit()
                return str(existing["id"])
            conn.execute(
                "INSERT INTO delegation_events "
                "(id, trace_id, session_id, host, work_unit_id, recommended_agent, "
                "status, backend, executed_worker_kind, executed_worker_id, native_run_id, "
                "skip_reason, error, started_at, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    trace_id,
                    session_id,
                    safe_host,
                    safe_work_unit_id,
                    safe_recommended_agent,
                    normalized_status,
                    safe_backend,
                    safe_worker_kind,
                    safe_worker_id,
                    safe_native_run_id,
                    safe_skip_reason,
                    safe_error,
                    now,
                    now if normalized_status in _TERMINAL_DELEGATION_STATUSES else None,
                ),
            )
            attach_consumed_activation_to_delegation(
                conn,
                event_id=event_id,
                trace_id=trace_id,
                work_unit_id=safe_work_unit_id,
            )
            conn.commit()
            return event_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _merge_delegation_transition(
        conn: Any,
        existing: Any,
        *,
        status: str,
        backend: str,
        error: str,
        recommended_agent: str,
        executed_worker_kind: str,
        executed_worker_id: str,
        native_run_id: str,
        skip_reason: str,
        host: str,
        now: str,
    ) -> None:
        """Merge one callback into a canonical work-unit row."""
        transition = _prepare_delegation_transition(
            conn,
            existing,
            status=status,
            backend=backend,
            error=error,
            recommended_agent=recommended_agent,
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
            skip_reason=skip_reason,
            host=host,
            now=now,
        )
        conn.execute(
            "UPDATE delegation_events SET status = ?, "
            "host = CASE WHEN ? THEN COALESCE(NULLIF(?, ''), host) ELSE host END, "
            "backend = CASE WHEN ? THEN COALESCE(NULLIF(?, ''), backend) ELSE backend END, "
            "executed_worker_kind = CASE WHEN ? THEN "
            "COALESCE(NULLIF(?, ''), executed_worker_kind) ELSE executed_worker_kind END, "
            "executed_worker_id = CASE WHEN ? THEN "
            "COALESCE(NULLIF(?, ''), executed_worker_id) ELSE executed_worker_id END, "
            "native_run_id = CASE WHEN ? THEN "
            "COALESCE(NULLIF(?, ''), native_run_id) ELSE native_run_id END, "
            "error = ?, "
            "recommended_agent = CASE WHEN recommended_agent <> '' THEN recommended_agent "
            "WHEN ? THEN COALESCE(NULLIF(?, ''), '') ELSE recommended_agent END, "
            "skip_reason = ?, completed_at = ? WHERE id = ?",
            (
                transition["status"],
                int(transition["incoming_wins"]),
                transition["host"],
                int(transition["incoming_wins"]),
                transition["backend"],
                int(transition["incoming_wins"]),
                transition["worker_kind"],
                int(transition["incoming_wins"]),
                transition["worker_id"],
                int(transition["incoming_wins"]),
                transition["native_run_id"],
                transition["error"],
                int(transition["recommendation_can_initialize"]),
                transition["recommended_agent"],
                transition["skip_reason"],
                transition["completed_at"],
                existing["id"],
            ),
        )
        attach_consumed_activation_to_delegation(
            conn,
            event_id=str(existing["id"]),
            trace_id=str(existing["trace_id"]),
            work_unit_id=str(existing["work_unit_id"] or ""),
        )

    def update_delegation(
        self,
        event_id: str,
        *,
        status: str,
        backend: str = "",
        error: str = "",
        recommended_agent: str = "",
        executed_worker_kind: str = "",
        executed_worker_id: str = "",
        native_run_id: str = "",
        skip_reason: str = "",
        host: str = "",
    ) -> None:
        normalized_event_id = str(event_id or "").strip()
        if not normalized_event_id or len(normalized_event_id) > 128:
            raise ValueError("delegation event id is invalid")
        capture_content = self._capture_content_enabled()
        safe_skip_reason = project_delegation_detail(
            skip_reason,
            field="skip_reason",
            capture_content=capture_content,
        )
        safe_error = project_delegation_detail(
            error,
            field="error",
            capture_content=capture_content,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT delegation_events.*, runs.status AS run_status "
                "FROM delegation_events "
                "JOIN runs ON runs.trace_id = delegation_events.trace_id "
                "WHERE delegation_events.id = ?",
                (normalized_event_id,),
            ).fetchone()
            if run is None:
                raise ValueError("delegation event has no correlated run")
            if str(run["run_status"]) not in {"active", "evidence_only"}:
                raise ValueError("delegation event belongs to a terminal turn")
            self._merge_delegation_transition(
                conn,
                run,
                status=_normalize_delegation_status(status),
                backend=backend,
                error=safe_error,
                recommended_agent=recommended_agent,
                executed_worker_kind=executed_worker_kind,
                executed_worker_id=executed_worker_id,
                native_run_id=native_run_id,
                skip_reason=safe_skip_reason,
                host=host,
                now=self._now(),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_delegations(self, trace_id: str) -> list[dict[str, Any]]:
        trace_id = validate_correlation_id(trace_id, field="trace_id")
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM delegation_events WHERE trace_id = ? ORDER BY started_at, rowid",
                (trace_id,),
            )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_delegations_for_session(
        self, session_id: str, statuses: list[str] | tuple[str, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Return delegation events for a session, optionally filtered by status."""
        session_id = validate_correlation_id(session_id, field="session_id")
        conn = self._connect()
        try:
            if statuses:
                placeholders = ",".join("?" for _ in statuses)
                # SQL text added here consists only of parameter placeholders.
                cur = conn.execute(
                    f"SELECT * FROM delegation_events WHERE session_id = ? AND status IN ({placeholders}) ORDER BY started_at, rowid",  # nosec B608
                    (session_id, *statuses),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM delegation_events "
                    "WHERE session_id = ? ORDER BY started_at, rowid",
                    (session_id,),
                )
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def record_codex_canary_reconciliation_diagnostic(
        self,
        *,
        session_id: str,
        trace_id: str,
        reason: str,
    ) -> None:
        """Persist one allowlisted, content-free canary rejection reason."""

        from agency_runtime.core.codex_activation_verification import (
            CODEX_RECONCILIATION_DIAGNOSTIC_REASONS,
        )

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        if reason not in CODEX_RECONCILIATION_DIAGNOSTIC_REASONS:
            raise ValueError("Codex reconciliation diagnostic reason is invalid")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT metadata FROM runs WHERE session_id = ? AND trace_id = ? "
                "AND host = 'codex' AND status IN ('active', 'evidence_only')",
                (normalized_session, normalized_trace),
            ).fetchone()
            if row is None:
                raise ValueError("active Codex canary run is unavailable")
            metadata = decode_run_metadata(row["metadata"])
            metadata["canary_hook_diagnostic"] = reason
            cursor = conn.execute(
                "UPDATE runs SET metadata = ?, "
                f"last_activity_at = {STORE_CLOCK_SQL}, "  # nosec B608
                "evidence_revision = evidence_revision + 1 "
                "WHERE session_id = ? AND trace_id = ? "
                "AND host = 'codex' AND status IN ('active', 'evidence_only')",
                (
                    project_run_metadata(metadata),
                    normalized_session,
                    normalized_trace,
                ),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Codex canary diagnostic update lost its run")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
