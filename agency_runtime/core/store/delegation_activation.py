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
from agency_runtime.core.codex_native_plan_scope import (
    CodexNativePlanScope,
    deserialize_codex_native_plan_scope,
)
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.delegation_status import (
    MAX_DELEGATION_AGENT_CHARS,
    MAX_DELEGATION_NATIVE_RUN_ID_CHARS,
    MAX_DELEGATION_WORK_UNIT_ID_CHARS,
    MAX_DELEGATION_WORKER_ID_CHARS,
    MAX_DELEGATION_WORKER_KIND_CHARS,
)
from agency_runtime.core.native_child_activation import (
    MAX_NATIVE_CHILD_ACTIVATION_TTL_SECONDS,
    NATIVE_CHILD_ACTIVATION_TOKEN_BYTES,
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
from agency_runtime.core.roster.revisions import (
    content_digest_identity,
    content_identity_matches,
)
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.preflight import _decode_preflight_recipe
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.store.version_identity import normalize_version_identity
from agency_runtime.core.unit_assignment import native_child_evidence_requirements

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


def _clean_launch_model(value: object) -> str:
    """Normalize an explicitly requested launch model, or return "".

    A model the host never echoes back is caller-supplied text on an evidence
    row, so it is bounded and shape-checked rather than stored verbatim.  An
    unrecognisable value degrades to "" -- the same state as "no model was
    requested" -- because the header must never present unvalidated input as
    an observed fact.
    """

    normalized = " ".join(str(value or "").split())[:_MAX_LAUNCH_MODEL_CHARS]
    return normalized if _LAUNCH_MODEL_PATTERN.fullmatch(normalized) else ""


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


def _activation_grant_provenance(
    grant_origin: object,
    tool_use_id: object,
) -> tuple[str, str]:
    """Validate the immutable authority and native tool-call correlation."""

    if not isinstance(grant_origin, str):
        raise ValueError("grant_origin must be a string")
    origin = grant_origin.strip()
    if origin not in _ACTIVATION_GRANT_ORIGINS:
        raise ValueError("grant_origin must identify a supported activation authority")
    tool_use = validate_correlation_id(
        tool_use_id,
        field="tool_use_id",
        required=False,
    )
    if origin == "native_hook" and not tool_use:
        raise ValueError("native_hook activation requires the exact tool_use_id")
    if origin != "native_hook" and tool_use:
        raise ValueError("tool_use_id is reserved for native_hook activation")
    return origin, tool_use


def _contract_items(value: object, *, field: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a list")
    return tuple(value)


def _codex_native_scope_from_recipe(
    conn: Any,
    *,
    session_id: str,
    trace_id: str,
    recipe: dict[str, Any],
    work_unit_id: str,
    specialist_slug: str,
    specialist_version: str,
    specialist_prompt_hash: str,
) -> CodexNativePlanScope:
    """Read and verify one private path capability against its ready recipe."""

    planned = [
        item
        for item in recipe.get("unit_agent_plan", [])
        if isinstance(item, dict)
        and item.get("work_unit_id") == work_unit_id
        and item.get("recommended_agent") == specialist_slug
    ]
    references = [
        item
        for item in recipe.get("specialist_refs", [])
        if isinstance(item, dict) and item.get("slug") == specialist_slug
    ]
    if len(planned) != 1 or len(references) != 1:
        raise ValueError("Codex native plan scope does not match one ready plan row")
    plan = planned[0]
    reference = references[0]
    row = conn.execute(
        "SELECT session_id, trace_id, work_unit_id, scope_payload "
        "FROM codex_native_plan_scopes WHERE session_id = ? AND trace_id = ? "
        "AND work_unit_id = ? LIMIT 1",
        (session_id, trace_id, work_unit_id),
    ).fetchone()
    if row is None:
        raise ValueError("Codex native plan scope is unavailable")
    scope = deserialize_codex_native_plan_scope(str(row["scope_payload"] or ""))
    expected_evidence = build_native_child_evidence_contract(
        contract_id="agency-native-child-plan-v1",
        requirements=native_child_evidence_requirements(plan.get("required_evidence")),
    )
    if (
        str(row["session_id"] or "") != session_id
        or str(row["trace_id"] or "") != trace_id
        or str(row["work_unit_id"] or "") != scope.work_unit_id
        or scope.work_unit_id != work_unit_id
        or scope.specialist.slug != specialist_slug
        or scope.specialist.version != specialist_version
        or scope.specialist.content_hash != specialist_prompt_hash
        or reference.get("version") != specialist_version
        or reference.get("hash") != specialist_prompt_hash
        or plan.get("goal_hash") != scope.goal_hash
        or tuple(plan.get("resource_hashes") or ()) != scope.resource_hashes
        or plan.get("mutation_scope") != scope.mutation_scope.mode
        or expected_evidence != scope.evidence_contract
    ):
        raise ValueError("Codex native plan scope failed ready-plan verification")
    return scope


def _verified_codex_native_hook_scope(
    conn: Any,
    *,
    run_host: str,
    origin: str,
    allow_opaque_replay: bool,
    session_id: str,
    trace_id: str,
    recipe: dict[str, Any],
    work_unit_id: str,
    specialist_slug: str,
    specialist_version: str,
    specialist_prompt_hash: str,
    mutation_scope: Any,
    evidence_contract: Any,
) -> CodexNativePlanScope | None:
    """Require exact staged authority for every Codex native-hook grant."""

    if origin != "native_hook" or run_host != "codex":
        if allow_opaque_replay:
            raise ValueError("opaque replay is reserved for exact Codex native-hook grants")
        return None
    scope = _codex_native_scope_from_recipe(
        conn,
        session_id=session_id,
        trace_id=trace_id,
        recipe=recipe,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    if mutation_scope != scope.mutation_scope or evidence_contract != scope.evidence_contract:
        raise ValueError("Codex native-hook activation exceeds its exact preflight plan scope")
    return scope


def _existing_activation_outcome(
    conn: Any,
    *,
    prior: Any,
    allow_opaque_replay: bool,
    planned_codex_scope: CodexNativePlanScope | None,
    session_id: str,
    trace_id: str,
    work_unit_id: str,
    specialist_slug: str,
    specialist_version: str,
    specialist_prompt_hash: str,
    worker_kind: str,
    origin: str,
    tool_use_id: str,
) -> dict[str, Any] | None:
    """Return one exact opaque replay or reject every conflicting prior grant."""

    if prior is None:
        return None
    if prior["consumed_at"] is not None:
        raise ValueError(
            "selected specialist already has a consumed activation receipt for this work unit"
        )
    if not allow_opaque_replay:
        raise ValueError(
            "selected specialist already has an unconsumed activation grant "
            "for this work unit; consume it or start a fresh Agency preflight"
        )
    inflight = conn.execute(
        "SELECT id FROM delegation_activation_receipts "
        "WHERE session_id = ? AND trace_id = ? AND child_host = 'codex' "
        "AND grant_origin = 'native_hook' AND consumed_at IS NULL "
        "ORDER BY created_at, rowid LIMIT 2",
        (session_id, trace_id),
    ).fetchall()
    grant = _stored_public_grant(prior)
    store_now = int(
        conn.execute(
            f"SELECT {_STORE_UNIX_SQL} AS unix_time"  # nosec B608
        ).fetchone()["unix_time"]
    )
    if (
        len(inflight) != 1
        or str(inflight[0]["id"] or "") != str(prior["id"] or "")
        or str(prior["grant_origin"] or "") != "native_hook"
        or str(prior["tool_use_id"] or "") != tool_use_id
        or planned_codex_scope is None
        or grant.mutation_scope != planned_codex_scope.mutation_scope
        or grant.evidence_contract != planned_codex_scope.evidence_contract
        or store_now < grant.issued_at
        or store_now > grant.expires_at
    ):
        raise ValueError("opaque Codex activation replay is unavailable or ambiguous")
    return {
        "activation_token": "",
        "receipt_id": str(prior["id"]),
        "grant_id": grant.grant_id,
        "activation_grant": grant.as_dict(),
        "session_id": session_id,
        "trace_id": trace_id,
        "work_unit_id": work_unit_id,
        "slug": specialist_slug,
        "version": specialist_version,
        "prompt_hash": specialist_prompt_hash,
        "worker_kind": worker_kind,
        "worker_id": str(prior["worker_id"] or ""),
        "grant_origin": origin,
        "tool_use_id": tool_use_id,
        "worker_binding": grant.worker_binding.as_dict()
        if grant.worker_binding is not None
        else {},
        "replayed": True,
    }


def _require_open_codex_native_hook_slot(
    conn: Any,
    *,
    planned_scope: CodexNativePlanScope | None,
    opaque_launch: bool,
    session_id: str,
    trace_id: str,
) -> None:
    """Serialize opaque launches through child-start grant consumption."""

    if planned_scope is None or not opaque_launch:
        return
    inflight = conn.execute(
        "SELECT 1 FROM delegation_activation_receipts "
        "WHERE session_id = ? AND trace_id = ? AND child_host = 'codex' "
        "AND grant_origin = 'native_hook' AND consumed_at IS NULL LIMIT 1",
        (session_id, trace_id),
    ).fetchone()
    if inflight is not None:
        raise ValueError(
            "a prior opaque Codex child must start and consume its grant "
            "before another planned child can launch"
        )


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


def _consumption_lineage(
    conn: Any,
    *,
    require_native_child_started: bool,
    receipt: Any,
    host: str,
    session_id: str,
    trace_id: str,
    work_unit_id: str,
    worker_id: str,
    native_run_id: str,
    match_native_child_identity: bool,
) -> tuple[str, str]:
    """Atomically select one unclaimed lifecycle identity when V2 requires it."""

    if type(require_native_child_started) is not bool:
        raise TypeError("require_native_child_started must be a boolean")
    if type(match_native_child_identity) is not bool:
        raise TypeError("match_native_child_identity must be a boolean")
    if not require_native_child_started:
        return worker_id, native_run_id
    child_rows = conn.execute(
        "SELECT child.worker_id, child.native_run_id FROM worker_runs AS child "
        "WHERE child.host = ? AND child.session_id = ? AND child.trace_id = ? "
        "AND child.started_at >= ? "
        "AND (child.work_unit_id = '' OR child.work_unit_id = ?) "
        "AND (? = 0 OR (child.worker_id = ? AND child.native_run_id = ?)) "
        "AND NOT EXISTS (SELECT 1 FROM delegation_activation_consumptions "
        "AS consumed WHERE consumed.child_host = child.host "
        "AND consumed.session_id = child.session_id "
        "AND consumed.trace_id = child.trace_id "
        "AND consumed.worker_id = child.worker_id "
        "AND consumed.native_run_id = child.native_run_id) "
        "ORDER BY child.started_at, child.rowid LIMIT 2",
        (
            host,
            session_id,
            trace_id,
            str(receipt["created_at"]),
            work_unit_id,
            int(match_native_child_identity),
            worker_id,
            native_run_id,
        ),
    ).fetchall()
    if len(child_rows) != 1:
        raise ValueError("activation requires one unclaimed native-child lifecycle receipt")
    return str(child_rows[0]["worker_id"]), str(child_rows[0]["native_run_id"])


def _activation_receipt_for_consumption(
    conn: Any,
    *,
    token_hash: str,
    native_tool_use: str,
    session_id: str,
    trace_id: str,
    specialist_slug: str,
    work_unit_id: str,
) -> Any:
    """Select one pending bearer or exact native-hook activation receipt."""

    projection = (
        "SELECT receipt.*, run.status AS run_status, "
        "run.preflight_state AS run_preflight_state, run.host AS run_host, "
        f"{_STORE_UNIX_SQL} AS store_now_unix FROM "  # nosec B608
        "delegation_activation_receipts AS receipt JOIN runs AS run "
        "ON run.trace_id = receipt.trace_id AND run.session_id = receipt.session_id "
    )
    if native_tool_use:
        return conn.execute(
            projection + "WHERE receipt.session_id = ? AND receipt.trace_id = ? "
            "AND receipt.specialist_slug = ? AND receipt.work_unit_id = ? "
            "AND receipt.grant_origin = 'native_hook' "
            "AND receipt.tool_use_id = ? AND receipt.consumed_at IS NULL LIMIT 1",
            (
                session_id,
                trace_id,
                specialist_slug,
                work_unit_id,
                native_tool_use,
            ),
        ).fetchone()
    return conn.execute(
        projection + "WHERE receipt.token_hash = ? AND receipt.session_id = ? "
        "AND receipt.trace_id = ? AND receipt.specialist_slug = ? "
        "AND receipt.consumed_at IS NULL LIMIT 1",
        (token_hash, session_id, trace_id, specialist_slug),
    ).fetchone()


def _validated_consumption_authority(
    activation_token: object,
    native_hook_tool_use_id: object,
    *,
    require_native_child_started: object,
) -> tuple[str, str, str]:
    """Validate one bearer or internal native-hook consumption authority."""

    token = str(activation_token or "").strip()
    native_tool_use = validate_correlation_id(
        native_hook_tool_use_id,
        field="native_hook_tool_use_id",
        required=False,
    )
    if not token and not native_tool_use:
        raise ValueError("activation_token is invalid")
    if token and native_tool_use:
        raise ValueError("supply exactly one of activation_token or native_hook_tool_use_id")
    if token and len(token) > _MAX_ACTIVATION_TOKEN_CHARS:
        raise ValueError("activation_token is invalid")
    if native_tool_use and require_native_child_started is not True:
        raise ValueError("native-hook activation requires native-child lifecycle evidence")
    token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()
    return token, native_tool_use, token_hash


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

    def get_consumed_delegation_lineage(
        self,
        *,
        session_id: str,
        trace_id: str,
        specialist_slug: str,
        work_unit_id: str,
        activation_token: str = "",
        tool_use_id: str = "",
    ) -> dict[str, str] | None:
        """Return authoritative native-child lineage for one consumed grant."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        slug = _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        unit = _work_unit_identity(work_unit_id, required=True)
        token = str(activation_token or "").strip()
        tool_use = validate_correlation_id(
            tool_use_id,
            field="tool_use_id",
            required=False,
        )
        if token and not tool_use:
            raise ValueError("tool_use_id is required with activation_token for replay proof")
        if token and len(token) > _MAX_ACTIVATION_TOKEN_CHARS:
            raise ValueError("activation_token is invalid")
        token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()
        conn = self._connect()
        try:
            if token:
                row = conn.execute(
                    "SELECT consumed.worker_kind, consumed.worker_id, "
                    "consumed.native_run_id "
                    "FROM delegation_activation_consumptions AS consumed "
                    "JOIN delegation_activation_receipts AS grant "
                    "ON grant.id = consumed.legacy_activation_receipt_id "
                    "AND grant.grant_id = consumed.grant_id "
                    "WHERE consumed.session_id = ? AND consumed.trace_id = ? "
                    "AND consumed.work_unit_id = ? AND consumed.specialist_slug = ? "
                    "AND grant.token_hash = ? AND grant.tool_use_id = ? LIMIT 1",
                    (
                        normalized_session,
                        normalized_trace,
                        unit,
                        slug,
                        token_hash,
                        tool_use,
                    ),
                ).fetchone()
            elif tool_use:
                row = conn.execute(
                    "SELECT consumed.worker_kind, consumed.worker_id, "
                    "consumed.native_run_id "
                    "FROM delegation_activation_consumptions AS consumed "
                    "JOIN delegation_activation_receipts AS grant "
                    "ON grant.id = consumed.legacy_activation_receipt_id "
                    "AND grant.grant_id = consumed.grant_id "
                    "WHERE consumed.session_id = ? AND consumed.trace_id = ? "
                    "AND consumed.work_unit_id = ? AND consumed.specialist_slug = ? "
                    "AND grant.grant_origin = 'native_hook' "
                    "AND grant.tool_use_id = ? LIMIT 1",
                    (
                        normalized_session,
                        normalized_trace,
                        unit,
                        slug,
                        tool_use,
                    ),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT worker_kind, worker_id, native_run_id "
                    "FROM delegation_activation_consumptions "
                    "WHERE session_id = ? AND trace_id = ? AND work_unit_id = ? "
                    "AND specialist_slug = ? LIMIT 1",
                    (normalized_session, normalized_trace, unit, slug),
                ).fetchone()
            if row is None:
                return None
            return {
                "worker_kind": str(row["worker_kind"]),
                "worker_id": str(row["worker_id"]),
                "native_run_id": str(row["native_run_id"]),
            }
        finally:
            conn.close()

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

    def get_codex_native_plan_scope(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        specialist_slug: str,
        specialist_version: str,
        specialist_prompt_hash: str,
        goal_hash: str,
        resource_hashes: Sequence[str],
        required_evidence: Sequence[str],
    ) -> dict[str, Any]:
        """Return one exact preflight-staged Codex mutation/evidence contract."""

        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        unit = _work_unit_identity(work_unit_id, required=True)
        slug = _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        version = str(specialist_version or "").strip()
        prompt_hash = str(specialist_prompt_hash or "").strip().casefold()
        normalized_goal_hash = str(goal_hash or "").strip().casefold()
        normalized_resource_hashes = tuple(
            str(item or "").strip().casefold()
            for item in _contract_items(
                resource_hashes,
                field="resource_hashes",
            )
        )
        normalized_required_evidence = tuple(
            str(item or "").strip()
            for item in _contract_items(
                required_evidence,
                field="required_evidence",
            )
        )
        if (
            not version
            or normalize_version_identity(version) != version
            or content_digest_identity(prompt_hash) is None
            or _DIGEST_PATTERN.fullmatch(normalized_goal_hash) is None
            or not normalized_resource_hashes
            or any(_DIGEST_PATTERN.fullmatch(item) is None for item in normalized_resource_hashes)
        ):
            raise ValueError("Codex native plan scope identity is invalid")
        conn = self._connect()
        try:
            run = conn.execute(
                "SELECT host, status, preflight_state, preflight_result FROM runs "
                "WHERE session_id = ? AND trace_id = ?",
                (normalized_session, normalized_trace),
            ).fetchone()
            if (
                run is None
                or str(run["host"] or "").strip().casefold() != "codex"
                or str(run["status"] or "") not in {"active", "evidence_only"}
                or str(run["preflight_state"] or "") != "ready"
            ):
                raise ValueError("Codex native plan scope requires one ready active turn")
            recipe = _decode_preflight_recipe(
                run["preflight_result"],
                session_id=normalized_session,
                trace_id=normalized_trace,
            )
            if recipe is None:
                raise ValueError("ready specialist recipe could not be verified")
            scope = _codex_native_scope_from_recipe(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                recipe=recipe,
                work_unit_id=unit,
                specialist_slug=slug,
                specialist_version=version,
                specialist_prompt_hash=prompt_hash,
            )
            plan = next(
                item
                for item in recipe["unit_agent_plan"]
                if item["work_unit_id"] == unit and item["recommended_agent"] == slug
            )
            if (
                scope.goal_hash != normalized_goal_hash
                or scope.resource_hashes != normalized_resource_hashes
                or tuple(plan.get("required_evidence") or ()) != normalized_required_evidence
            ):
                raise ValueError("Codex native plan scope does not match the hook assignment")
            return {
                "mutation_mode": scope.mutation_scope.mode,
                "mutation_path_prefixes": list(scope.mutation_scope.path_prefixes),
                "evidence_contract_id": scope.evidence_contract.contract_id,
                "evidence_requirements": list(scope.evidence_contract.requirements),
            }
        finally:
            conn.close()

    def prepare_codex_opaque_native_child_activation(
        self,
        *,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        specialist_slug: str,
        specialist_version: str,
        specialist_prompt_hash: str,
        goal_hash: str,
        resource_hashes: Sequence[str],
        required_evidence: Sequence[str],
        tool_use_id: str,
    ) -> dict[str, Any]:
        """Issue or replay one serialized opaque Codex native-hook grant."""

        contract = self.get_codex_native_plan_scope(
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=work_unit_id,
            specialist_slug=specialist_slug,
            specialist_version=specialist_version,
            specialist_prompt_hash=specialist_prompt_hash,
            goal_hash=goal_hash,
            resource_hashes=resource_hashes,
            required_evidence=required_evidence,
        )
        return self.prepare_delegation_activation(
            session_id=session_id,
            trace_id=trace_id,
            specialist_slug=specialist_slug,
            work_unit_id=work_unit_id,
            worker_kind="generic-worker",
            grant_origin="native_hook",
            tool_use_id=tool_use_id,
            _allow_codex_opaque_replay=True,
            **contract,
        )

    def get_pending_native_hook_delivery(
        self,
        *,
        host: str,
        session_id: str,
        trace_id: str,
        worker_id: str,
        native_run_id: str,
    ) -> dict[str, Any] | None:
        """Return one exact prompt for a just-started native-hook child.

        Codex keeps collaboration messages encrypted at the parent tool boundary.
        The child-start hook therefore retrieves only a single unconsumed grant
        whose issue time precedes this exact persisted lifecycle identity.  Any
        concurrent or otherwise ambiguous candidate fails closed.
        """

        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in {"codex", "claude", "zcode"}:
            raise ValueError("native child host is unsupported")
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
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
                "SELECT receipt.*, run.status AS run_status, "
                "run.preflight_state AS run_preflight_state, run.host AS run_host, "
                f"{_STORE_UNIX_SQL} AS store_now_unix "  # nosec B608
                "FROM delegation_activation_receipts AS receipt "
                "JOIN runs AS run ON run.trace_id = receipt.trace_id "
                "AND run.session_id = receipt.session_id "
                "JOIN worker_runs AS child ON child.host = receipt.child_host "
                "AND child.session_id = receipt.session_id "
                "AND child.trace_id = receipt.trace_id "
                "AND child.worker_id = ? AND child.native_run_id = ? "
                "AND child.started_at >= receipt.created_at "
                "AND (child.work_unit_id = '' OR child.work_unit_id = receipt.work_unit_id) "
                "WHERE receipt.child_host = ? AND receipt.session_id = ? "
                "AND receipt.trace_id = ? AND receipt.grant_origin = 'native_hook' "
                "AND receipt.consumed_at IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM delegation_activation_consumptions "
                "AS consumed WHERE consumed.child_host = child.host "
                "AND consumed.session_id = child.session_id "
                "AND consumed.trace_id = child.trace_id "
                "AND consumed.worker_id = child.worker_id "
                "AND consumed.native_run_id = child.native_run_id) "
                "ORDER BY receipt.created_at, receipt.rowid LIMIT 2",
                (
                    worker,
                    native,
                    normalized_host,
                    normalized_session,
                    normalized_trace,
                ),
            ).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                raise ValueError("native child prompt delivery is ambiguous")
            receipt = rows[0]
            if (
                str(receipt["run_status"] or "") not in {"active", "evidence_only"}
                or str(receipt["run_preflight_state"] or "") != "ready"
                or str(receipt["run_host"] or "").strip().casefold() != normalized_host
            ):
                raise ValueError("native child prompt belongs to a non-ready turn")
            grant = _stored_public_grant(receipt)
            store_now = int(receipt["store_now_unix"])
            if store_now < grant.issued_at or store_now > grant.expires_at:
                raise ValueError("native child prompt delivery grant expired")
            self._reject_disabled_specialist(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                specialist_slug=grant.specialist.slug,
            )
            prompt = conn.execute(
                "SELECT agent_slug, version, hash, content FROM agent_versions "
                "WHERE agent_slug = ? AND version = ? AND hash = ? LIMIT 1",
                (
                    grant.specialist.slug,
                    grant.specialist.version,
                    grant.specialist.content_hash,
                ),
            ).fetchone()
            if (
                prompt is None
                or not str(prompt["content"] or "").strip()
                or len(str(prompt["content"])) > MAX_SPECIALIST_PROMPT_CHARS
                or not content_identity_matches(prompt["content"], prompt["hash"])
            ):
                raise ValueError("authorized specialist prompt is unavailable or invalid")
            return {
                "session_id": normalized_session,
                "trace_id": normalized_trace,
                "tool_use_id": str(receipt["tool_use_id"]),
                "work_unit_id": grant.work_unit_id,
                "slug": grant.specialist.slug,
                "version": grant.specialist.version,
                "prompt_hash": grant.specialist.content_hash,
                "prompt_body": str(prompt["content"]),
            }
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
        grant_origin: str = "manual_api",
        tool_use_id: str = "",
        launch_model: str = "",
        ttl_seconds: int = _DEFAULT_ACTIVATION_TTL_SECONDS,
        mutation_mode: str = "read_only",
        mutation_path_prefixes: Sequence[str] = (),
        evidence_contract_id: str = _DEFAULT_EVIDENCE_CONTRACT_ID,
        evidence_requirements: Sequence[str] = _DEFAULT_EVIDENCE_REQUIREMENTS,
        _allow_codex_opaque_replay: bool = False,
    ) -> dict[str, Any]:
        """Issue a bearer grant for one selected immutable prompt reference."""

        if type(_allow_codex_opaque_replay) is not bool:
            raise TypeError("_allow_codex_opaque_replay must be a boolean")

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
            maximum=MAX_DELEGATION_WORKER_KIND_CHARS,
            field="worker_kind",
            required=True,
        )
        if kind != "generic-worker":
            raise ValueError("delegated specialist retrieval uses generic-worker attribution")
        worker = _identity(worker_id, maximum=MAX_DELEGATION_WORKER_ID_CHARS, field="worker_id")
        origin, tool_use = _activation_grant_provenance(grant_origin, tool_use_id)
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
            run_host = str(run["host"] or "").strip().casefold()
            planned_codex_scope = _verified_codex_native_hook_scope(
                conn,
                run_host=run_host,
                origin=origin,
                allow_opaque_replay=_allow_codex_opaque_replay,
                session_id=normalized_session,
                trace_id=normalized_trace,
                recipe=recipe,
                work_unit_id=unit,
                specialist_slug=slug,
                specialist_version=str(reference["version"]),
                specialist_prompt_hash=str(reference["hash"]),
                mutation_scope=mutation_scope,
                evidence_contract=evidence_contract,
            )
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
                "SELECT * "
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
            replay = _existing_activation_outcome(
                conn,
                prior=prior,
                allow_opaque_replay=_allow_codex_opaque_replay,
                planned_codex_scope=planned_codex_scope,
                session_id=normalized_session,
                trace_id=normalized_trace,
                work_unit_id=unit,
                specialist_slug=slug,
                specialist_version=str(reference["version"]),
                specialist_prompt_hash=str(reference["hash"]),
                worker_kind=kind,
                origin=origin,
                tool_use_id=tool_use,
            )
            if replay is not None:
                conn.commit()
                return replay
            _require_open_codex_native_hook_slot(
                conn,
                planned_scope=planned_codex_scope,
                opaque_launch=_allow_codex_opaque_replay,
                session_id=normalized_session,
                trace_id=normalized_trace,
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
            token = secrets.token_urlsafe(NATIVE_CHILD_ACTIVATION_TOKEN_BYTES)
            token_hash = sha256(token.encode("ascii")).hexdigest()
            receipt_id = self._uuid()
            conn.execute(
                "INSERT INTO delegation_activation_receipts "
                "(id, token_hash, grant_id, grant_payload, grant_issued_unix, "
                "grant_expires_unix, child_host, grant_origin, tool_use_id, "
                "session_id, trace_id, work_unit_id, "
                "specialist_slug, specialist_version, specialist_prompt_hash, "
                "worker_kind, worker_id, native_run_id, launch_model, created_at, "
                "consumed_at, delegation_event_id) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, "  # nosec B608
                f"{STORE_CLOCK_SQL}, NULL, NULL)",  # nosec B608
                (
                    receipt_id,
                    token_hash,
                    grant.grant_id,
                    grant_payload,
                    grant.issued_at,
                    grant.expires_at,
                    grant.host,
                    origin,
                    tool_use,
                    normalized_session,
                    normalized_trace,
                    unit,
                    slug,
                    reference["version"],
                    reference["hash"],
                    kind,
                    worker,
                    _clean_launch_model(launch_model),
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
                "grant_origin": origin,
                "tool_use_id": tool_use,
                "worker_binding": worker_binding.as_dict(),
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def verify_pending_delegation_activation(
        self,
        *,
        activation_token: str,
        host: str,
        session_id: str,
        trace_id: str,
        work_unit_id: str,
        specialist_slug: str,
        specialist_version: str,
        specialist_prompt_hash: str,
        grant_origin: str = "manual_api",
        tool_use_id: str = "",
    ) -> bool:
        """Authenticate one current unconsumed grant without consuming it."""

        token = str(activation_token or "").strip()
        if not token or len(token) > _MAX_ACTIVATION_TOKEN_CHARS:
            raise ValueError("activation_token is invalid")
        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in {"codex", "claude", "zcode"}:
            raise ValueError("native child host is unsupported")
        normalized_session = validate_correlation_id(session_id, field="session_id")
        normalized_trace = validate_correlation_id(trace_id, field="trace_id")
        unit = _work_unit_identity(work_unit_id, required=True)
        slug = _identity(
            specialist_slug,
            maximum=MAX_DELEGATION_AGENT_CHARS,
            field="specialist_slug",
            required=True,
        )
        version = str(specialist_version or "").strip()
        if not version or normalize_version_identity(version) != version:
            raise ValueError("specialist_version is invalid")
        prompt_hash = str(specialist_prompt_hash or "").strip()
        if content_digest_identity(prompt_hash) is None:
            raise ValueError("specialist_prompt_hash is invalid")
        origin, tool_use = _activation_grant_provenance(grant_origin, tool_use_id)
        token_hash = sha256(token.encode("utf-8", errors="surrogatepass")).hexdigest()

        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT receipt.*, run.status AS run_status, "
                "run.preflight_state AS run_preflight_state, run.host AS run_host, "
                f"{_STORE_UNIX_SQL} AS store_now_unix FROM "  # nosec B608
                "delegation_activation_receipts AS receipt JOIN runs AS run "
                "ON run.trace_id = receipt.trace_id AND run.session_id = receipt.session_id "
                "WHERE receipt.session_id = ? AND receipt.trace_id = ? "
                "AND receipt.work_unit_id = ? AND receipt.specialist_slug = ? "
                "AND receipt.specialist_version = ? AND receipt.specialist_prompt_hash = ? "
                "AND receipt.child_host = ? AND receipt.grant_origin = ? "
                "AND receipt.tool_use_id = ? AND receipt.consumed_at IS NULL "
                "ORDER BY receipt.rowid LIMIT 2",
                (
                    normalized_session,
                    normalized_trace,
                    unit,
                    slug,
                    version,
                    prompt_hash,
                    normalized_host,
                    origin,
                    tool_use,
                ),
            ).fetchall()
            if len(rows) != 1:
                return False
            receipt = rows[0]
            if not hmac.compare_digest(str(receipt["token_hash"] or ""), token_hash):
                return False
            if (
                str(receipt["run_status"] or "") not in {"active", "evidence_only"}
                or str(receipt["run_preflight_state"] or "") != "ready"
                or str(receipt["run_host"] or "").strip().casefold() != normalized_host
            ):
                return False
            grant = _stored_public_grant(receipt)
            store_now = int(receipt["store_now_unix"])
            if store_now < grant.issued_at or store_now > grant.expires_at:
                return False
            if (
                grant.host != normalized_host
                or grant.parent_session_id != normalized_session
                or grant.parent_trace_id != normalized_trace
                or grant.work_unit_id != unit
                or grant.specialist.slug != slug
                or grant.specialist.version != version
                or grant.specialist.content_hash != prompt_hash
            ):
                return False
            self._reject_disabled_specialist(
                conn,
                session_id=normalized_session,
                trace_id=normalized_trace,
                specialist_slug=slug,
            )
            return True
        finally:
            conn.close()

    def consume_delegation_activation(
        self,
        *,
        activation_token: str = "",
        native_hook_tool_use_id: str = "",
        session_id: str,
        trace_id: str,
        specialist_slug: str,
        work_unit_id: str = "",
        worker_id: str = "",
        native_run_id: str = "",
        require_native_child_started: bool = False,
        match_native_child_identity: bool = False,
    ) -> dict[str, Any]:
        """Consume one grant and return its exact immutable prompt atomically."""

        _token, native_tool_use, token_hash = _validated_consumption_authority(
            activation_token,
            native_hook_tool_use_id,
            require_native_child_started=require_native_child_started,
        )
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
            conn.execute("BEGIN IMMEDIATE")
            receipt = _activation_receipt_for_consumption(
                conn,
                token_hash=token_hash,
                native_tool_use=native_tool_use,
                session_id=normalized_session,
                trace_id=normalized_trace,
                specialist_slug=slug,
                work_unit_id=expected_unit,
            )
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
            worker, native = _consumption_lineage(
                conn,
                require_native_child_started=require_native_child_started,
                receipt=receipt,
                host=grant.host,
                session_id=normalized_session,
                trace_id=normalized_trace,
                work_unit_id=expected_unit,
                worker_id=worker,
                native_run_id=native,
                match_native_child_identity=match_native_child_identity,
            )
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
