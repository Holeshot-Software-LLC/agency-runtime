"""Run, receipt, host-control, and delegation persistence methods."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
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
from agency_runtime.core.store.receipt_authority import MODEL_RECEIPT_AUTHORITY_ORDER_SQL
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

MAX_HOST_CONTROL_GENERATION = (2**63) - 1
_CANARY_ACTIVATION_SNAPSHOT_SCHEMA = "agency.canary-activation-evidence.v1"
_CANARY_ACTIVATION_MAX_ROWS = 256


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
            "runs": 0,
            "traces": 0,
            "unit_agent_plan": 0,
            "delegations": 0,
            "activation_grants": 0,
            "activation_consumptions": 0,
            "worker_runs": 0,
            "specialist_loads": 0,
            "finalizations": 0,
        },
        "run": None,
        "route": None,
        "unit_agent_plan": [],
        "delegations": [],
        "activation_grants": [],
        "activation_consumptions": [],
        "worker_runs": [],
        "specialist_loads": [],
        "finalizations": [],
    }


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
                "model_id, source, recorded_at, started_at, ended_at, status) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL}, "  # nosec B608
                "?, ?, ?)",
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

    def get_canary_activation_snapshot(
        self,
        *,
        host: str,
        query_hash: str,
    ) -> dict[str, Any]:
        """Read one exact, content-free canary evidence graph in one transaction.

        ``proven`` means only that one route and its parent run were resolved and
        their ready preflight recipe passed correlation checks.  Callers must
        still evaluate the returned activation/delegation topology; this method
        never turns the presence of a route into an activation-success claim.
        """

        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in EXECUTION_HOSTS:
            raise ValueError("host must identify a supported execution host")
        supplied_hash = str(query_hash or "").strip()
        normalized_hash = content_digest_identity(supplied_hash)
        if normalized_hash is None or normalized_hash != supplied_hash:
            raise ValueError("query_hash must be a lowercase SHA-256 digest")

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            route_count_row = conn.execute(
                "SELECT COUNT(*) AS count FROM routing_decisions AS route "
                "JOIN runs AS run ON run.trace_id = route.trace_id "
                "AND run.session_id = route.session_id "
                "WHERE route.query_hash = ? AND run.host = ? "
                "AND run.preflight_request_fingerprint = route.query_hash",
                (normalized_hash, normalized_host),
            ).fetchone()
            route_count = int(route_count_row["count"] if route_count_row is not None else 0)
            if route_count != 1:
                snapshot = _empty_canary_activation_snapshot(
                    host=normalized_host,
                    query_hash=normalized_hash,
                    route_count=route_count,
                    reason="route_not_found" if route_count == 0 else "route_ambiguous",
                )
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
                "AND run.preflight_request_fingerprint = route.query_hash",
                (normalized_hash, normalized_host),
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
                "runs": 1,
                "traces": 1,
                "unit_agent_plan": 0,
                "delegations": int(counts["delegations"]),
                "activation_grants": int(counts["activation_grants"]),
                "activation_consumptions": int(counts["activation_consumptions"]),
                "worker_runs": int(counts["worker_runs"]),
                "specialist_loads": int(counts["specialist_loads"]),
                "finalizations": int(counts["finalizations"]),
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
                hook_diagnostic=hook_diagnostic,
            )
            if any(
                cardinalities[name] > _CANARY_ACTIVATION_MAX_ROWS
                for name in (
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
                dict(item)
                for item in conn.execute(
                    "SELECT id, delegation_event_id, backend, session_id, trace_id, "
                    "work_unit_id, host, worker_id, native_run_id, exit_code, "
                    "started_at, ended_at FROM worker_runs WHERE trace_id = ? "
                    "ORDER BY started_at, rowid",
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
            unit_agent_plan = (
                [dict(item) for item in recipe.get("unit_agent_plan", [])]
                if isinstance(recipe, dict)
                else []
            )
            cardinalities["unit_agent_plan"] = len(unit_agent_plan)
            snapshot.update(
                unit_agent_plan=unit_agent_plan,
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
