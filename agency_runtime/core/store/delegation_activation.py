"""One-use specialist activation receipts for delegated work units.

Preflight selection is a plan, not evidence that a specialist prompt shaped a
worker.  This store domain turns one exact ready-recipe reference into a
single-use grant and records the immutable version only when the grant is
consumed.
"""

from __future__ import annotations

import re
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
    MAX_DELEGATION_WORK_UNIT_ID_CHARS,
    MAX_DELEGATION_WORKER_ID_CHARS,
)
from agency_runtime.core.store.schema import STORE_CLOCK_SQL

_MAX_ACTIVATION_TOKEN_CHARS = 256
_WORK_UNIT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")
_STORE_UNIX_SQL = "CAST(STRFTIME('%s', 'NOW') AS INTEGER)"
_DEFAULT_ACTIVATION_TTL_SECONDS = 10 * 60
_DEFAULT_EVIDENCE_CONTRACT_ID = "agency-native-child-v1"
_DEFAULT_EVIDENCE_REQUIREMENTS = ("delegation-execution", "specialist-load")
_ACTIVATION_GRANT_ORIGINS = frozenset({"manual_api", "native_hook"})
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MAX_LAUNCH_MODEL_CHARS = 128
_LAUNCH_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$")


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
        "SELECT trace_id, session_id, host, work_unit_id, recommended_agent, backend, "
        "executed_worker_kind, executed_worker_id, native_run_id, "
        "activation_receipt_id FROM delegation_events WHERE id = ?",
        (event_id,),
    ).fetchone()
    if event is None or str(event["activation_receipt_id"] or ""):
        return
    receipt = conn.execute(
        "SELECT grant.id, grant.grant_id, grant.specialist_slug, "
        "grant.specialist_version, grant.specialist_prompt_hash, "
        "grant.worker_kind, grant.worker_id, grant.native_run_id, grant.child_host, "
        "grant.grant_origin, grant.tool_use_id, grant.session_id, grant.trace_id, "
        "grant.work_unit_id "
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
    promoted_child = None
    if is_public_grant and (not all(event_lineage) or event_lineage != receipt_lineage):
        # Keep the Store layer importable before the delegation package finishes
        # initializing; that package's ledger imports Store for its public API.
        from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit

        task_name = codex_task_name_for_work_unit(work_unit_id)
        synthetic_lineage = (
            str(receipt["worker_kind"] or ""),
            f"task:{task_name}",
            f"codex-task:{task_name}",
        )
        exact_codex_promotion = bool(
            str(receipt["child_host"] or "") == "codex"
            and str(receipt["grant_origin"] or "") == "native_hook"
            and str(receipt["tool_use_id"] or "")
            and str(receipt["session_id"] or "") == str(event["session_id"] or "")
            and str(receipt["trace_id"] or "") == str(event["trace_id"] or "")
            and str(receipt["work_unit_id"] or "") == str(event["work_unit_id"] or "")
            and str(event["host"] or "") == "codex"
            and str(event["backend"] or "") == "spawn_agent"
            and str(event["recommended_agent"] or "") == str(receipt["specialist_slug"] or "")
            and event_lineage == synthetic_lineage
            and all(receipt_lineage)
            and not receipt_lineage[1].startswith("task:")
            and receipt_lineage[2] == f"codex-agent:{receipt_lineage[1]}"
        )
        if not exact_codex_promotion:
            return
        children = conn.execute(
            "SELECT id, delegation_event_id, work_unit_id FROM worker_runs "
            "WHERE session_id = ? AND trace_id = ? AND host = 'codex' "
            "AND worker_id = ? AND native_run_id = ? ORDER BY rowid LIMIT 2",
            (
                receipt["session_id"],
                receipt["trace_id"],
                receipt["worker_id"],
                receipt["native_run_id"],
            ),
        ).fetchall()
        if len(children) != 1:
            return
        promoted_child = children[0]
        if str(promoted_child["delegation_event_id"] or "") not in ("", event_id):
            return
        if str(promoted_child["work_unit_id"] or "") not in ("", work_unit_id):
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
    updated = conn.execute(
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
    if updated.rowcount != 1:
        raise RuntimeError("delegation activation attachment postcondition failed")
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
    if promoted_child is not None:
        bound = conn.execute(
            "UPDATE worker_runs SET delegation_event_id = ?, work_unit_id = ? "
            "WHERE id = ? AND (delegation_event_id IS NULL OR delegation_event_id = '') "
            "AND (work_unit_id = '' OR work_unit_id = ?)",
            (event_id, work_unit_id, promoted_child["id"], work_unit_id),
        )
        if bound.rowcount != 1:
            raise RuntimeError("Codex child delegation promotion postcondition failed")


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

    def get_consumed_codex_spawn_tool_use_id(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        worker_id: str,
        native_run_id: str,
    ) -> str | None:
        """Return the sole native-hook spawn identity for one consumed Codex grant."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        unit = _work_unit_identity(work_unit_id, required=True)
        worker = _identity(
            worker_id,
            maximum=MAX_DELEGATION_WORKER_ID_CHARS,
            field="worker_id",
            required=True,
        )
        native = _identity(
            native_run_id,
            maximum=MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
            field="native_run_id",
            required=True,
        )
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT grant.tool_use_id "
                "FROM delegation_activation_consumptions AS consumed "
                "JOIN delegation_activation_receipts AS grant "
                "ON grant.id = consumed.legacy_activation_receipt_id "
                "AND grant.grant_id = consumed.grant_id "
                "WHERE consumed.session_id = ? AND consumed.trace_id = ? "
                "AND consumed.work_unit_id = ? AND consumed.child_host = 'codex' "
                "AND consumed.worker_id = ? AND consumed.native_run_id = ? "
                "AND grant.grant_origin = 'native_hook' "
                "AND grant.consumed_at IS NOT NULL LIMIT 2",
                (normalized_session, normalized_trace, unit, worker, native),
            ).fetchall()
            if len(rows) != 1:
                return None
            return validate_correlation_id(rows[0]["tool_use_id"], field="tool_use_id")
        finally:
            conn.close()
