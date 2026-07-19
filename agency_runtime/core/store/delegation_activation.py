"""One-use specialist activation receipts for delegated work units.

Preflight selection is a plan, not evidence that a specialist prompt shaped a
worker.  This store domain turns one exact ready-recipe reference into a
single-use grant and records the immutable version only when the grant is
consumed.
"""

from __future__ import annotations

import hmac
import re
import secrets
from collections.abc import Sequence
from hashlib import sha256
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_AGENT_CHARS,
    MAX_DELEGATION_WORK_UNIT_ID_CHARS,
)
from agency_runtime.core.native_child_activation import (
    MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS,
    NativeChildActivationGrant,
    build_native_child_activation_grant,
    build_native_child_activation_receipt,
    build_native_child_evidence_contract,
    build_native_child_mutation_scope,
    build_native_child_run_identity,
    build_native_child_specialist_identity,
    build_native_child_worker_binding,
    deserialize_native_child_activation_grant,
    serialize_native_child_activation_grant,
    serialize_native_child_activation_receipt,
)
from agency_runtime.core.roster.revisions import content_identity_matches
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.preflight import _decode_preflight_recipe
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

_MAX_WORKER_KIND_CHARS = 64
_MAX_WORKER_ID_CHARS = 256
_MAX_NATIVE_RUN_ID_CHARS = 256
_MAX_ACTIVATION_TOKEN_CHARS = 256
_WORK_UNIT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")
_STORE_UNIX_SQL = "CAST(STRFTIME('%s', 'NOW') AS INTEGER)"
_DEFAULT_ACTIVATION_TTL_SECONDS = 10 * 60
_DEFAULT_EVIDENCE_CONTRACT_ID = "agency-native-child-v1"
_DEFAULT_EVIDENCE_REQUIREMENTS = ("delegation-execution", "specialist-load")


def _identity(value: object, *, maximum: int, field: str, required: bool = False) -> str:
    normalized = " ".join(str(value or "").split())[:maximum]
    if required and not normalized:
        raise ValueError(f"{field} is required")
    return normalized


def _work_unit_identity(value: object, *, required: bool) -> str:
    normalized = _identity(
        value,
        maximum=MAX_DELEGATION_WORK_UNIT_ID_CHARS,
        field="work_unit_id",
        required=required,
    )
    if normalized and _WORK_UNIT_PATTERN.fullmatch(normalized) is None:
        raise ValueError("work_unit_id must be a stable content-free identifier")
    return normalized


def _activation_ttl(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("ttl_seconds must be an integer")
    if not 1 <= value <= MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS:
        raise ValueError(
            f"ttl_seconds must be between 1 and {MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS}"
        )
    return value


def _contract_items(value: object, *, field: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a list")
    return tuple(value)


def _stored_public_grant(row: Any) -> NativeChildActivationGrant:
    required_fields = (
        "grant_id",
        "grant_payload",
        "session_id",
        "trace_id",
        "work_unit_id",
        "child_host",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "grant_issued_unix",
        "grant_expires_unix",
        "worker_kind",
        "worker_id",
        "native_run_id",
        "consumed_at",
    )
    try:
        stored = {field: row[field] for field in required_fields}
    except (IndexError, KeyError, TypeError) as exc:
        raise ValueError("activation grant record is incomplete") from exc
    payload = str(stored["grant_payload"] or "")
    if not str(stored["grant_id"] or "") or not payload:
        raise ValueError(
            "legacy activation grant has no authoritative TTL; start a fresh Agency preflight"
        )
    try:
        grant = deserialize_native_child_activation_grant(payload)
    except ValueError as exc:
        raise ValueError("activation grant failed integrity verification") from exc
    expected = {
        "grant_id": grant.grant_id,
        "session_id": grant.parent_session_id,
        "trace_id": grant.parent_trace_id,
        "work_unit_id": grant.work_unit_id,
        "child_host": grant.host,
        "specialist_slug": grant.specialist.slug,
        "specialist_version": grant.specialist.version,
        "specialist_prompt_hash": grant.specialist.content_hash,
        "grant_issued_unix": grant.issued_at,
        "grant_expires_unix": grant.expires_at,
    }
    if any(stored[field] != expected_value for field, expected_value in expected.items()):
        raise ValueError("activation grant failed integrity verification")
    binding = grant.worker_binding
    if binding is not None:
        if str(stored["worker_kind"] or "") != binding.worker_kind:
            raise ValueError("activation grant failed worker binding integrity verification")
        stored_worker = str(stored["worker_id"] or "")
        if binding.mode == "prebound":
            if not hmac.compare_digest(stored_worker, binding.worker_id):
                raise ValueError("activation grant failed worker binding integrity verification")
        elif stored["consumed_at"] is None and stored_worker:
            raise ValueError("late-bound activation grant was rebound before consumption")
    if stored["consumed_at"] is None and str(stored["native_run_id"] or ""):
        raise ValueError("activation grant native run was rebound before consumption")
    return grant


def _consume_worker_binding(
    row: Any,
    grant: NativeChildActivationGrant,
    *,
    worker_id: str,
) -> tuple[str, str]:
    """Validate the authenticated binding and return CAS expectations."""

    stored_worker = str(row["worker_id"] or "")
    binding = grant.worker_binding
    expected_worker = (
        binding.worker_id
        if binding is not None and binding.mode == "prebound"
        else stored_worker or worker_id
    )
    if not hmac.compare_digest(worker_id, expected_worker):
        raise ValueError("activation token is bound to a different worker_id")
    worker_kind = binding.worker_kind if binding is not None else str(row["worker_kind"])
    return worker_kind, stored_worker


def attach_consumed_activation_to_delegation(
    conn: Any,
    *,
    event_id: str,
    trace_id: str,
    work_unit_id: str,
) -> None:
    """Link one consumed exact-version receipt to its executed work unit.

    A work unit can project one primary specialist in the compact delegation
    row.  Every consumed specialist still remains independently auditable in
    ``delegation_activation_receipts`` and completion validates the full set.
    """

    if not event_id or not trace_id or not work_unit_id:
        return
    event = conn.execute(
        "SELECT recommended_agent, executed_worker_kind, executed_worker_id, "
        "native_run_id, activation_receipt_id FROM delegation_events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if event is None or str(event["activation_receipt_id"] or ""):
        return
    receipt = conn.execute(
        "SELECT grant.id, grant.grant_id, grant.specialist_slug, "
        "grant.specialist_version, grant.specialist_prompt_hash, "
        "grant.worker_kind, grant.worker_id, grant.native_run_id "
        "FROM delegation_activation_receipts AS grant "
        "LEFT JOIN delegation_activation_consumptions AS consumption "
        "ON consumption.legacy_activation_receipt_id = grant.id "
        "AND consumption.grant_id = grant.grant_id "
        "WHERE grant.trace_id = ? AND grant.work_unit_id = ? "
        "AND grant.consumed_at IS NOT NULL AND grant.delegation_event_id IS NULL "
        "AND (grant.grant_id = '' OR consumption.id IS NOT NULL) "
        "ORDER BY CASE WHEN grant.specialist_slug = ? THEN 0 ELSE 1 END, "
        "grant.created_at, grant.rowid "
        "LIMIT 1",
        (trace_id, work_unit_id, str(event["recommended_agent"] or "")),
    ).fetchone()
    if receipt is None:
        return
    event_lineage = (
        str(event["executed_worker_kind"] or ""),
        str(event["executed_worker_id"] or ""),
        str(event["native_run_id"] or ""),
    )
    receipt_lineage = (
        str(receipt["worker_kind"] or ""),
        str(receipt["worker_id"] or ""),
        str(receipt["native_run_id"] or ""),
    )
    is_public_grant = bool(str(receipt["grant_id"] or ""))
    if is_public_grant and (not all(event_lineage) or event_lineage != receipt_lineage):
        return
    worker_kind, worker_id, native_run_id = receipt_lineage
    if not is_public_grant:
        worker_kind, worker_id, native_run_id = tuple(
            event_value or receipt_value
            for event_value, receipt_value in zip(
                event_lineage,
                receipt_lineage,
                strict=True,
            )
        )
    conn.execute(
        "UPDATE delegation_events SET retrieved_specialist_slug = ?, "
        "retrieved_specialist_version = ?, retrieved_specialist_prompt_hash = ?, "
        "activation_receipt_id = ?, executed_worker_kind = ?, "
        "executed_worker_id = ?, native_run_id = ? WHERE id = ? "
        "AND (activation_receipt_id IS NULL OR activation_receipt_id = '')",
        (
            receipt["specialist_slug"],
            receipt["specialist_version"],
            receipt["specialist_prompt_hash"],
            receipt["id"],
            worker_kind,
            worker_id,
            native_run_id,
            event_id,
        ),
    )
    if is_public_grant:
        conn.execute(
            "UPDATE delegation_activation_receipts SET delegation_event_id = ? "
            "WHERE id = ? AND delegation_event_id IS NULL",
            (event_id, receipt["id"]),
        )
    else:
        conn.execute(
            "UPDATE delegation_activation_receipts SET delegation_event_id = ?, "
            "worker_kind = COALESCE(NULLIF(?, ''), worker_kind), "
            "worker_id = COALESCE(NULLIF(?, ''), worker_id), "
            "native_run_id = COALESCE(NULLIF(?, ''), native_run_id) "
            "WHERE id = ? AND delegation_event_id IS NULL",
            (event_id, worker_kind, worker_id, native_run_id, receipt["id"]),
        )


class DelegationActivationStoreMixin:
    """Persistence API for exact, one-use delegated specialist grants."""

    def _reject_disabled_specialist(
        self,
        conn: Any,
        *,
        session_id: str,
        trace_id: str,
        specialist_slug: str,
    ) -> None:
        """Atomically terminalize a ready turn whose selected agent was disabled."""

        if agent_is_enabled(specialist_slug, self.get_disabled_agent_slugs()):
            return
        closed_at = self._now()
        closed = conn.execute(
            "UPDATE runs SET ended_at = COALESCE(ended_at, ?), "
            "status = 'specialist_disabled', "
            f"last_activity_at = {STORE_CLOCK_SQL} "  # nosec B608
            "WHERE session_id = ? AND trace_id = ? "
            "AND status IN ('active', 'evidence_only')",
            (closed_at, session_id, trace_id),
        )
        if closed.rowcount == 1:
            conn.execute(
                "UPDATE specialists_loaded SET expired_at = ? "
                "WHERE session_id = ? AND trace_id = ? AND expired_at IS NULL",
                (closed_at, session_id, trace_id),
            )
        conn.commit()
        raise ValueError(
            f"specialist '{specialist_slug}' is disabled; start a fresh Agency preflight"
        )

    def requires_delegation_activation(
        self,
        *,
        session_id: str,
        trace_id: str,
        specialist_slug: str,
    ) -> bool:
        """Return whether this host forbids every tokenless prompt load."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT host, status, preflight_state, preflight_result FROM runs "
                "WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if row is None or str(row["status"] or "") not in {"active", "evidence_only"}:
                return False
            if str(row["host"] or "").strip().casefold() in {"codex", "claude"}:
                return True
            if str(row["preflight_state"] or "") != "ready":
                return False
            recipe = _decode_preflight_recipe(
                row["preflight_result"],
                session_id=normalized_session,
                trace_id=normalized_trace,
            )
            return bool(recipe and recipe["delivery_mode"] == "isolated")
        finally:
            conn.close()

    def prepare_delegation_activation(
        self,
        *,
        session_id: str,
        trace_id: str,
        specialist_slug: str,
        work_unit_id: str,
        worker_kind: str = "generic-worker",
        worker_id: str = "",
        ttl_seconds: int = _DEFAULT_ACTIVATION_TTL_SECONDS,
        mutation_mode: str = "read_only",
        mutation_path_prefixes: Sequence[str] = (),
        evidence_contract_id: str = _DEFAULT_EVIDENCE_CONTRACT_ID,
        evidence_requirements: Sequence[str] = _DEFAULT_EVIDENCE_REQUIREMENTS,
    ) -> dict[str, Any]:
        """Issue a bearer grant for one selected immutable prompt reference."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        slug = _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        unit = _work_unit_identity(work_unit_id, required=True)
        kind = _identity(
            worker_kind,
            maximum=_MAX_WORKER_KIND_CHARS,
            field="worker_kind",
            required=True,
        )
        if kind != "generic-worker":
            raise ValueError("delegated specialist retrieval uses generic-worker attribution")
        worker = _identity(worker_id, maximum=_MAX_WORKER_ID_CHARS, field="worker_id")
        ttl = _activation_ttl(ttl_seconds)
        mutation_scope = build_native_child_mutation_scope(
            mode=mutation_mode,
            path_prefixes=_contract_items(
                mutation_path_prefixes,
                field="mutation_path_prefixes",
            ),
        )
        evidence_contract = build_native_child_evidence_contract(
            contract_id=evidence_contract_id,
            requirements=_contract_items(
                evidence_requirements,
                field="evidence_requirements",
            ),
        )

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            run = conn.execute(
                "SELECT host, status, preflight_state, preflight_result FROM runs "
                "WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if (
                run is None
                or str(run["status"] or "") not in {"active", "evidence_only"}
                or str(run["preflight_state"] or "") != "ready"
            ):
                raise ValueError("specialist activation requires one ready active Agency turn")
            recipe = _decode_preflight_recipe(
                run["preflight_result"],
                session_id=normalized_session,
                trace_id=normalized_trace,
            )
            if recipe is None:
                raise ValueError("ready specialist recipe could not be verified")
            reference = next(
                (item for item in recipe["specialist_refs"] if item["slug"] == slug),
                None,
            )
            if reference is None:
                raise ValueError("specialist is not selected by this turn's ready recipe")
            unit_agent_plan = recipe.get("unit_agent_plan", [])
            has_unit_plan = bool(unit_agent_plan)
            if has_unit_plan:
                planned = any(
                    item.get("work_unit_id") == unit and item.get("recommended_agent") == slug
                    for item in unit_agent_plan
                    if isinstance(item, dict)
                )
                if not planned:
                    raise ValueError(
                        "specialist and work_unit_id do not match the persisted unit-agent plan"
                    )
            elif unit != f"specialist:{slug}":
                raise ValueError("work_unit_id must match the selected specialist binding")
            self._reject_disabled_specialist(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                specialist_slug=slug,
            )
            prompt = conn.execute(
                "SELECT versioned.content FROM agent_versions AS versioned "
                "WHERE versioned.agent_slug = ? AND versioned.version = ? "
                "AND versioned.hash = ? AND EXISTS (SELECT 1 FROM agent_active AS active "
                "WHERE active.agent_slug = versioned.agent_slug "
                "AND active.version = versioned.version AND active.hash = versioned.hash) "
                "LIMIT 1",
                (slug, reference["version"], reference["hash"]),
            ).fetchone()
            if prompt is None:
                raise ValueError("selected specialist prompt version is unavailable or inactive")
            if len(str(prompt["content"] or "")) > MAX_SPECIALIST_PROMPT_CHARS:
                raise ValueError("selected specialist prompt exceeds the exact-delivery ceiling")
            if not content_identity_matches(prompt["content"], reference["hash"]):
                raise ValueError("selected specialist prompt version failed integrity verification")
            prior = conn.execute(
                "SELECT id, consumed_at, grant_expires_unix "
                "FROM delegation_activation_receipts "
                "WHERE trace_id = ? AND work_unit_id = ? AND specialist_slug = ? "
                "AND specialist_version = ? AND specialist_prompt_hash = ? LIMIT 1",
                (
                    normalized_trace,
                    unit,
                    slug,
                    reference["version"],
                    reference["hash"],
                ),
            ).fetchone()
            if prior is not None and prior["consumed_at"] is not None:
                raise ValueError(
                    "selected specialist already has a consumed activation receipt "
                    "for this work unit"
                )
            if prior is not None:
                raise ValueError(
                    "selected specialist already has an unconsumed activation grant "
                    "for this work unit; consume it or start a fresh Agency preflight"
                )
            clock = conn.execute(
                f"SELECT {_STORE_UNIX_SQL} AS unix_time"  # nosec B608
            ).fetchone()
            issued_at = int(clock["unix_time"])
            specialist = build_native_child_specialist_identity(
                slug=slug,
                version=reference["version"],
                content_hash=reference["hash"],
            )
            worker_binding = build_native_child_worker_binding(
                mode="prebound" if worker else "late_bound",
                worker_kind=kind,
                worker_id=worker,
            )
            grant = build_native_child_activation_grant(
                parent_session_id=normalized_session,
                parent_trace_id=normalized_trace,
                work_unit_id=unit,
                host=run["host"],
                specialist=specialist,
                mutation_scope=mutation_scope,
                evidence_contract=evidence_contract,
                worker_binding=worker_binding,
                issued_at=issued_at,
                expires_at=issued_at + ttl,
            )
            grant_payload = serialize_native_child_activation_grant(grant)
            token = secrets.token_urlsafe(32)
            token_hash = sha256(token.encode("ascii")).hexdigest()
            receipt_id = self._uuid()
            conn.execute(
                "INSERT INTO delegation_activation_receipts "
                "(id, token_hash, grant_id, grant_payload, grant_issued_unix, "
                "grant_expires_unix, child_host, session_id, trace_id, work_unit_id, "
                "specialist_slug, specialist_version, specialist_prompt_hash, "
                "worker_kind, worker_id, native_run_id, created_at, consumed_at, "
                "delegation_event_id) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', "  # nosec B608
                f"{STORE_CLOCK_SQL}, NULL, NULL)",  # nosec B608
                (
                    receipt_id,
                    token_hash,
                    grant.grant_id,
                    grant_payload,
                    grant.issued_at,
                    grant.expires_at,
                    grant.host,
                    normalized_session,
                    normalized_trace,
                    unit,
                    slug,
                    reference["version"],
                    reference["hash"],
                    kind,
                    worker,
                ),
            )
            conn.commit()
            return {
                "activation_token": token,
                "receipt_id": receipt_id,
                "grant_id": grant.grant_id,
                "activation_grant": grant.as_dict(),
                "session_id": normalized_session,
                "trace_id": normalized_trace,
                "work_unit_id": unit,
                "slug": slug,
                "version": reference["version"],
                "prompt_hash": reference["hash"],
                "worker_kind": kind,
                "worker_id": worker,
                "worker_binding": worker_binding.as_dict(),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def consume_delegation_activation(
        self,
        *,
        activation_token: str,
        session_id: str,
        trace_id: str,
        specialist_slug: str,
        work_unit_id: str = "",
        worker_id: str = "",
        native_run_id: str = "",
    ) -> dict[str, Any]:
        """Consume one grant and return its exact immutable prompt atomically."""

        token = str(activation_token or "").strip()
        if not token or len(token) > _MAX_ACTIVATION_TOKEN_CHARS:
            raise ValueError("activation_token is invalid")
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        slug = _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        expected_unit = _work_unit_identity(work_unit_id, required=True)
        if not str(worker_id or "").strip() or not str(native_run_id or "").strip():
            raise ValueError(
                "token-backed specialist activation requires complete child lineage: "
                "worker_id and native_run_id"
            )
        worker = _identity(
            worker_id,
            maximum=_MAX_WORKER_ID_CHARS,
            field="worker_id",
            required=True,
        )
        native = _identity(
            native_run_id,
            maximum=_MAX_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
            required=True,
        )
        token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            receipt = conn.execute(
                "SELECT receipt.*, run.status AS run_status, "
                "run.preflight_state AS run_preflight_state, run.host AS run_host, "
                f"{_STORE_UNIX_SQL} AS store_now_unix FROM "  # nosec B608
                "delegation_activation_receipts AS receipt JOIN runs AS run "
                "ON run.trace_id = receipt.trace_id AND run.session_id = receipt.session_id "
                "WHERE receipt.token_hash = ? AND receipt.session_id = ? "
                "AND receipt.trace_id = ? AND receipt.specialist_slug = ? "
                "AND receipt.consumed_at IS NULL LIMIT 1",
                (token_hash, normalized_session, normalized_trace, slug),
            ).fetchone()
            if receipt is None:
                raise ValueError("activation token is invalid, expired, or already consumed")
            if (
                str(receipt["run_status"] or "") not in {"active", "evidence_only"}
                or str(receipt["run_preflight_state"] or "") != "ready"
            ):
                raise ValueError("activation token belongs to a non-ready or terminal turn")
            if expected_unit != str(receipt["work_unit_id"]):
                raise ValueError("activation token belongs to a different work unit")
            grant = _stored_public_grant(receipt)
            if str(receipt["run_host"] or "").strip().casefold() != grant.host:
                raise ValueError("activation grant failed integrity verification")
            worker_kind, expected_stored_worker = _consume_worker_binding(
                receipt,
                grant,
                worker_id=worker,
            )
            consumed_unix = int(receipt["store_now_unix"])
            if consumed_unix > grant.expires_at:
                raise ValueError("activation token expired; start a fresh Agency preflight")
            self._reject_disabled_specialist(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                specialist_slug=slug,
            )
            prompt = conn.execute(
                "SELECT agent_slug, version, hash, content FROM agent_versions "
                "WHERE agent_slug = ? AND version = ? AND hash = ? LIMIT 1",
                (
                    receipt["specialist_slug"],
                    receipt["specialist_version"],
                    receipt["specialist_prompt_hash"],
                ),
            ).fetchone()
            if prompt is None or not str(prompt["content"] or "").strip():
                raise ValueError("authorized specialist prompt version is unavailable")
            if len(str(prompt["content"])) > MAX_SPECIALIST_PROMPT_CHARS:
                raise ValueError("authorized specialist prompt exceeds the exact-delivery ceiling")
            if not content_identity_matches(prompt["content"], prompt["hash"]):
                raise ValueError("authorized specialist prompt failed integrity verification")
            child_run = build_native_child_run_identity(
                worker_kind=worker_kind,
                worker_id=worker,
                native_run_id=native,
            )
            public_receipt = build_native_child_activation_receipt(
                grant,
                child_run=child_run,
                consumed_at=consumed_unix,
            )
            public_receipt_payload = serialize_native_child_activation_receipt(
                public_receipt,
                grant=grant,
            )
            conn.execute(
                "INSERT INTO delegation_activation_consumptions "
                "(id, grant_id, legacy_activation_receipt_id, receipt_payload, "
                "session_id, trace_id, work_unit_id, child_host, specialist_slug, "
                "specialist_version, specialist_prompt_hash, worker_kind, worker_id, "
                "native_run_id, consumed_at, consumed_unix) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "  # nosec B608
                f"{STORE_CLOCK_SQL}, ?)",  # nosec B608
                (
                    public_receipt.receipt_id,
                    grant.grant_id,
                    receipt["id"],
                    public_receipt_payload,
                    normalized_session,
                    normalized_trace,
                    expected_unit,
                    grant.host,
                    grant.specialist.slug,
                    grant.specialist.version,
                    grant.specialist.content_hash,
                    child_run.worker_kind,
                    child_run.worker_id,
                    child_run.native_run_id,
                    consumed_unix,
                ),
            )
            consumed = conn.execute(
                "UPDATE delegation_activation_receipts SET "
                f"consumed_at = {STORE_CLOCK_SQL}, "  # nosec B608
                "worker_id = ?, native_run_id = ? "
                "WHERE id = ? AND consumed_at IS NULL "
                "AND grant_id = ? AND grant_issued_unix <= ? "
                "AND grant_expires_unix >= ? AND worker_kind = ? "
                "AND worker_id = ? AND native_run_id = ''",
                (
                    worker,
                    native,
                    receipt["id"],
                    grant.grant_id,
                    consumed_unix,
                    consumed_unix,
                    worker_kind,
                    expected_stored_worker,
                ),
            )
            if consumed.rowcount != 1:
                raise ValueError("activation token is invalid, expired, or already consumed")
            conn.execute(
                "INSERT INTO specialists_loaded "
                "(id, session_id, trace_id, agent_slug, loaded_at, expired_at, "
                "activation_receipt_id) "
                f"VALUES (?, ?, ?, ?, {STORE_CLOCK_SQL}, NULL, ?) "  # nosec B608
                "ON CONFLICT(session_id, trace_id, agent_slug) DO UPDATE SET "
                "activation_receipt_id = excluded.activation_receipt_id, "
                "loaded_at = excluded.loaded_at, expired_at = NULL",
                (
                    self._uuid(),
                    normalized_session,
                    normalized_trace,
                    slug,
                    receipt["id"],
                ),
            )
            event = conn.execute(
                "SELECT id FROM delegation_events WHERE trace_id = ? "
                "AND work_unit_id = ? AND status IN "
                "('started', 'running', 'delegated', 'completed') "
                "ORDER BY started_at, rowid LIMIT 1",
                (normalized_trace, receipt["work_unit_id"]),
            ).fetchone()
            if event is not None:
                attach_consumed_activation_to_delegation(
                    conn,
                    event_id=str(event["id"]),
                    trace_id=normalized_trace,
                    work_unit_id=str(receipt["work_unit_id"]),
                )
            consumed_row = conn.execute(
                "SELECT * FROM delegation_activation_receipts WHERE id = ?",
                (receipt["id"],),
            ).fetchone()
            conn.commit()
            prompt_body = str(prompt["content"])
            return {
                **dict(consumed_row),
                "grant_id": grant.grant_id,
                "activation_grant": grant.as_dict(),
                "consumption_receipt_id": public_receipt.receipt_id,
                "activation_receipt": public_receipt.as_dict(),
                "slug": str(prompt["agent_slug"]),
                "version": str(prompt["version"]),
                "prompt_hash": str(prompt["hash"]),
                "prompt_body": prompt_body,
                "prompt_truncated": False,
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


__all__ = [
    "DelegationActivationStoreMixin",
    "attach_consumed_activation_to_delegation",
]
