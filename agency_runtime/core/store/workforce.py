"""Durable workforce identity, hiring, lineage, lifecycle, and outcome evidence."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Collection, Container, Mapping
from contextlib import closing
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled, normalize_agent_slug
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.workforce.contract import (
    parse_workforce_contract,
    project_workforce_contract,
)
from agency_runtime.core.workforce.identity import stable_worker_id
from agency_runtime.core.workforce.promotion import promotion_readiness

MAX_WORKFORCE_DOCUMENT_BYTES = 256 * 1024
MAX_WORKFORCE_PAGE = 1_000
MAX_HIRING_SUMMARY_PAGE = 200
MAX_HIRING_COLLECTION_RESPONSE_BYTES = 1024 * 1024
_HIRING_COLLECTION_METADATA_RESERVE_BYTES = 16 * 1024
_MAX_WORKFORCE_SLUG_LOOKUP = 64
_EMPLOYMENT_CLASSES = frozenset({"contractor", "employee"})
_STANDINGS = frozenset({"active", "suspended", "retired", "merged"})
_CASE_TYPES = frozenset({"hire", "amend"})
_CASE_STATUSES = frozenset({"proposed", "audited", "rejected", "applied", "folded"})
_RISK_TIERS = frozenset({"low", "standard", "high"})
_CASE_TRANSITIONS = {
    "proposed": frozenset({"audited", "rejected", "folded"}),
    "audited": frozenset({"rejected", "folded"}),
}
_HIRING_CASE_SUMMARY_FIELDS = (
    "id",
    "case_type",
    "status",
    "proposed_slug",
    "target_worker_id",
    "work_unit_id",
    "risk_tier",
    "human_approval_required",
    "human_approved_by",
    "human_approved_at",
    "created_at",
    "decided_at",
    "applied_at",
)
_ACTIVATION_BOUND_OUTCOMES = frozenset(
    {"assignment", "artifact", "review", "test", "acceptance", "failure"}
)


class WorkforcePayloadBudgetError(RuntimeError):
    """Signal that an internal bounded workforce projection exceeded its contract."""


def _collection_revision(label: str, rows: list[dict[str, Any]]) -> str:
    """Hash the observable identity of one collection snapshot."""

    document = json.dumps(
        rows,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(f"{label}\\0{document}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkforceContractDivergence:
    """One packaged worker whose stored revision is no longer the packaged one.

    Repair authority deliberately stops at these rows, which is correct: the
    package must never overwrite an amendment somebody made on purpose. What was
    missing is that stopping was also silent, so a contractor amending an
    ``origin=upstream`` worker left no trace anywhere. This is the trace, and it
    is evidence only -- reporting a divergence never repairs or reverts it.
    """

    agent_slug: str
    reason: str
    expected_origin: str
    actual_origin: str
    expected_version: str
    actual_version: str

    def to_dict(self) -> dict[str, str]:
        return {
            "agent_slug": self.agent_slug,
            "reason": self.reason,
            "expected_origin": self.expected_origin,
            "actual_origin": self.actual_origin,
            "expected_version": self.expected_version,
            "actual_version": self.actual_version,
        }


@dataclass(frozen=True, slots=True)
class WorkforceContractReconciliation:
    """Result of re-projecting exact package-owned active revisions."""

    inspected: int
    updated: int
    divergent: tuple[WorkforceContractDivergence, ...] = ()


def _identity(value: object, *, field: str) -> str:
    return validate_correlation_id(value, field=field)


def _bounded_text(
    value: object,
    *,
    field: str,
    maximum: int = 256,
    required: bool = True,
) -> str:
    text = str(value or "").strip()
    if (required and not text) or len(text.encode("utf-8")) > maximum:
        raise ValueError(f"{field} is invalid")
    return text


def _digest(value: object, *, field: str, required: bool = True) -> str:
    digest = str(value or "").strip().casefold()
    if not digest and not required:
        return ""
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError(f"{field} must be a SHA-256 digest")
    return digest


def _document(value: object, *, field: str, allow_empty: bool = True) -> str:
    if value is None and allow_empty:
        value = {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field} must be an object")
    document = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(document.encode("utf-8")) > MAX_WORKFORCE_DOCUMENT_BYTES:
        raise ValueError(f"{field} exceeds the workforce evidence limit")
    if not allow_empty and document == "{}":
        raise ValueError(f"{field} is required")
    return document


def _document_hash(document: str) -> str:
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def _required_evidence(value: object, *, field: str) -> str:
    return _document(value, field=field, allow_empty=False)


def _hiring_case_key(
    *,
    case_type: str,
    proposed_slug: str,
    target_worker_id: str | None,
    work_unit_id: str,
    request_hash: str,
) -> str:
    identity = "\0".join(
        (case_type, proposed_slug, target_worker_id or "", work_unit_id, request_hash)
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _decoded(document: object) -> dict[str, Any]:
    try:
        value = safe_load_bounded_json(
            str(document or "{}"),
            maximum_bytes=MAX_WORKFORCE_DOCUMENT_BYTES,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("stored workforce evidence is invalid") from exc
    if not isinstance(value, dict):
        raise RuntimeError("stored workforce evidence is invalid")
    return value


def _display_state(row: Mapping[str, Any], disabled: Container[str]) -> str:
    standing = str(row["standing"])
    if standing != "active":
        return standing
    if not agent_is_enabled(row["agent_slug"], disabled):
        return "disabled"
    return str(row["employment_class"])


def _worker_projection(row: Mapping[str, Any], disabled: Container[str] = ()) -> dict[str, Any]:
    result = dict(row)
    result["state"] = _display_state(result, disabled)
    result["enabled"] = result["state"] in _EMPLOYMENT_CLASSES
    result["display_label"] = (
        f"Contractor · {result['display_name']}"
        if result["employment_class"] == "contractor"
        else str(result["display_name"])
    )
    return result


def _hiring_case_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    """Project bounded lifecycle metadata; exact-case APIs own full evidence."""

    result = {field: row[field] for field in _HIRING_CASE_SUMMARY_FIELDS}
    result["human_approval_required"] = bool(result["human_approval_required"])
    result["evidence_included"] = False
    return result


def _case_evidence_is_auditable(row: Mapping[str, Any]) -> bool:
    from agency_runtime.core.workforce.known_installer import (
        packaged_hiring_case_is_auditable,
    )

    if packaged_hiring_case_is_auditable(row):
        return True
    contract = _decoded(row["contract_evidence"])
    critic = _decoded(row["critic_evidence"])
    model = _decoded(row["model_evidence"])
    if not contract or _document_hash(str(row["contract_evidence"])) != row["contract_hash"]:
        return False
    receipts = model.get("receipts")
    return (
        critic.get("approved") is True
        and isinstance(critic.get("receipt"), Mapping)
        and bool(critic["receipt"])
        and isinstance(receipts, list)
        and bool(receipts)
        and all(_auditable_model_receipt(receipt) for receipt in receipts)
    )


def _auditable_model_receipt(value: object) -> bool:
    """Accept actual-model evidence or an explicitly requested CLI model, never a guess."""

    if not isinstance(value, Mapping):
        return False
    provider = str(value.get("provider") or "").strip()
    receipt_id = str(value.get("receipt_id") or "").strip()
    actual = str(value.get("actual_model") or "").strip()
    requested = str(value.get("requested_model") or "").strip()
    source = str(value.get("model_receipt_source") or "").strip()
    if not provider or not receipt_id:
        return False
    if actual:
        return source not in {"", "unavailable"}
    return bool(requested and source == "cli.explicit_model_argument")


def _next_event_sequence(conn: Any) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(event_sequence), 0) + 1 FROM agent_worker_events"
    ).fetchone()
    return int(row[0])


def _transition_state(
    conn: Any,
    row: Mapping[str, Any],
    *,
    action: str,
    target: str | None,
) -> tuple[str, str, str | None]:
    employment = str(row["employment_class"])
    standing = str(row["standing"])
    if standing in {"retired", "merged"}:
        raise ValueError("terminal workforce state cannot transition")
    if action == "promote":
        if employment != "contractor" or standing != "active":
            raise ValueError("only an active contractor can be promoted")
        return "employee", standing, None
    if action == "suspend":
        if standing != "active":
            raise ValueError("only an active worker can be suspended")
        return employment, "suspended", None
    if action == "resume":
        if standing != "suspended":
            raise ValueError("only a suspended worker can resume")
        return employment, "active", None
    if action == "retire":
        return employment, "retired", None
    if target is None or target == str(row["worker_id"]):
        raise ValueError("merge target is invalid")
    target_row = conn.execute(
        "SELECT standing, merged_into_worker_id FROM agent_workers WHERE worker_id = ?",
        (target,),
    ).fetchone()
    if target_row is None or str(target_row["standing"]) != "active":
        raise ValueError("merge target must be an active worker")
    cursor = target
    seen = {str(row["worker_id"])}
    while cursor:
        if cursor in seen:
            raise ValueError("workforce merge would create a cycle")
        seen.add(cursor)
        next_row = conn.execute(
            "SELECT merged_into_worker_id FROM agent_workers WHERE worker_id = ?", (cursor,)
        ).fetchone()
        cursor = str(next_row[0] or "") if next_row else ""
    return employment, "merged", target


def _record_worker_event(
    conn: Any,
    *,
    worker_id: str,
    event_type: str,
    from_class: str = "",
    to_class: str = "",
    from_standing: str = "",
    to_standing: str = "",
    version: str = "",
    merged_into_worker_id: str | None = None,
    hiring_case_id: str | None = None,
    actor: str = "",
    surface: str = "",
    session_id: str = "",
    trace_id: str = "",
    reason: str = "",
    evidence: str = "{}",
) -> None:
    conn.execute(
        "INSERT INTO agent_worker_events "
        "(id, event_sequence, worker_id, event_type, from_class, to_class, "
        "from_standing, to_standing, version, merged_into_worker_id, hiring_case_id, "
        "actor, surface, session_id, trace_id, reason, evidence, created_at) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
        (
            str(uuid.uuid4()),
            _next_event_sequence(conn),
            worker_id,
            event_type,
            from_class,
            to_class,
            from_standing,
            to_standing,
            version,
            merged_into_worker_id,
            hiring_case_id,
            actor,
            surface,
            session_id,
            trace_id,
            reason,
            evidence,
        ),
    )


def _outcome_promotion_policy(
    store: Any,
    configured_successes: int | None,
    disabled_agents: Container[str] | None,
) -> tuple[int, frozenset[str], int]:
    if configured_successes is None:
        from agency_runtime.core.config_binding import config_for_store

        config = config_for_store(store)
        return (
            config.workforce.auto_promote_successes,
            frozenset(config.agents.disabled),
            config.workforce.contractor_review_days,
        )
    if (
        isinstance(configured_successes, bool)
        or not isinstance(configured_successes, int)
        or configured_successes < 0
    ):
        raise ValueError("auto promotion successes must be a non-negative integer")
    disabled = (
        store.get_disabled_agent_slugs() if disabled_agents is None else frozenset(disabled_agents)
    )
    return configured_successes, disabled, 0


def _bind_outcome_activation(
    conn: Any,
    worker: Mapping[str, Any],
    *,
    activation_id: str,
    session: str,
    trace: str,
    unit: str,
) -> tuple[str, str, str, str, str]:
    version = str(worker["current_version"])
    version_hash = str(worker["current_hash"])
    if not activation_id:
        return version, version_hash, session, trace, unit
    activation = conn.execute(
        "SELECT * FROM delegation_activation_receipts WHERE id = ?",
        (activation_id,),
    ).fetchone()
    if activation is None or activation["consumed_at"] is None:
        raise ValueError("outcome activation receipt is missing or unconsumed")
    if str(activation["specialist_slug"]) != str(worker["agent_slug"]):
        raise ValueError("outcome activation receipt belongs to another worker")
    for supplied, recorded, field in (
        (session, str(activation["session_id"]), "session_id"),
        (trace, str(activation["trace_id"]), "trace_id"),
        (unit, str(activation["work_unit_id"]), "work_unit_id"),
    ):
        if supplied and supplied != recorded:
            raise ValueError(f"outcome {field} does not match activation receipt")
    return (
        str(activation["specialist_version"]),
        str(activation["specialist_prompt_hash"]),
        str(activation["session_id"]),
        str(activation["trace_id"]),
        str(activation["work_unit_id"]),
    )


def _validated_outcome_evidence(
    conn: Any,
    worker: Mapping[str, Any],
    *,
    event: str,
    session: str,
    trace: str,
    evidence_refs: Mapping[str, Any],
) -> str:
    normalized = dict(evidence_refs)
    normalized.pop("independent_verification_validated", None)
    verifier_id = str(normalized.get("independent_verifier_worker_id") or "").strip()
    receipt_id = str(normalized.get("independent_verification_receipt_id") or "").strip()
    if bool(verifier_id) != bool(receipt_id):
        raise ValueError("independent verification evidence is incomplete")
    if not verifier_id:
        return _document(normalized, field="evidence_refs")
    if event != "acceptance":
        raise ValueError("independent verification evidence is valid only for acceptance")
    verification = conn.execute(
        "SELECT receipt.*, workforce.worker_id AS verifier_worker_id "
        "FROM delegation_activation_receipts AS receipt "
        "JOIN agent_workers AS workforce "
        "ON workforce.agent_slug = receipt.specialist_slug "
        "WHERE receipt.id = ? LIMIT 1",
        (receipt_id,),
    ).fetchone()
    if verification is None or verification["consumed_at"] is None:
        raise ValueError("independent verification receipt is missing or unconsumed")
    if str(verification["verifier_worker_id"]) != verifier_id:
        raise ValueError("independent verifier identity does not match receipt")
    if verifier_id == str(worker["worker_id"]):
        raise ValueError("independent verifier must be a different worker")
    if str(verification["session_id"]) != session or str(verification["trace_id"]) != trace:
        raise ValueError("independent verification receipt belongs to another turn")
    normalized["independent_verification_validated"] = True
    return _document(normalized, field="evidence_refs")


def _auto_promote_if_ready(
    conn: Any,
    worker: Mapping[str, Any],
    *,
    disabled: Container[str],
    required_successes: int,
    review_window_days: int = 0,
) -> None:
    performance_rows = conn.execute(
        "SELECT * FROM agent_performance_events WHERE worker_id = ? ORDER BY created_at, rowid",
        (worker["worker_id"],),
    ).fetchall()
    state = (
        "disabled"
        if str(worker["agent_slug"]) in disabled
        else str(worker["employment_class"])
        if str(worker["standing"]) == "active"
        else str(worker["standing"])
    )
    readiness = promotion_readiness(
        {
            "worker_id": str(worker["worker_id"]),
            "state": state,
            "created_at": dict(worker).get("created_at"),
        },
        [
            {**dict(item), "evidence_refs": _decoded(item["evidence_refs"])}
            for item in performance_rows
        ],
        required_successes=required_successes,
        review_window_days=review_window_days,
    )
    if not readiness["eligible_for_automatic_promotion"]:
        return
    revision = int(worker["revision"]) + 1
    conn.execute(
        "UPDATE agent_workers SET employment_class = 'employee', "
        f"revision = ?, updated_at = {STORE_CLOCK_SQL} WHERE worker_id = ?",
        (revision, worker["worker_id"]),
    )
    _record_worker_event(
        conn,
        worker_id=str(worker["worker_id"]),
        event_type="promote",
        from_class="contractor",
        to_class="employee",
        from_standing=str(worker["standing"]),
        to_standing=str(worker["standing"]),
        version=str(worker["current_version"]),
        actor="promotion-policy",
        surface="outcome-recorder",
        reason=(
            "automatic promotion after "
            f"{readiness['verified_successes']} independently verified successful assignments"
        ),
        evidence=_document(readiness, field="automatic promotion evidence"),
    )
    conn.execute("UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'")


def record_native_assignment_outcome(
    conn: Any,
    *,
    delegation: Mapping[str, Any],
    worker_run_id: str,
    outcome: str,
    store: Any | None = None,
) -> str | None:
    """Atomically bind one native child result to its consumed specialist receipt.

    When ``store`` is supplied, the configured automatic-promotion policy runs
    in the same transaction after the event is recorded — the live outcome
    path participates in promotion readiness exactly like the mixin recorder.
    Assignment events carry no independent-verifier evidence, so promotion
    fires only once verified acceptance events exist for the worker.
    """

    receipt_id = str(delegation["activation_receipt_id"] or "")
    if not receipt_id:
        return None
    receipt = conn.execute(
        "SELECT receipt.*, workforce.worker_id AS workforce_worker_id "
        "FROM delegation_activation_receipts AS receipt "
        "JOIN agent_workers AS workforce "
        "ON workforce.agent_slug = receipt.specialist_slug "
        "WHERE receipt.id = ? LIMIT 1",
        (receipt_id,),
    ).fetchone()
    if receipt is None or receipt["consumed_at"] is None:
        raise RuntimeError("native assignment lacks a consumed workforce activation receipt")
    normalized_outcome = "passed" if outcome == "ok" else "failed"
    evidence_refs = {
        "delegation_event_id": str(delegation["id"]),
        "native_worker_run_id": worker_run_id,
    }
    evidence_document = _document(evidence_refs, field="evidence_refs")
    evidence_hash = _document_hash(evidence_document)
    key = hashlib.sha256(
        (
            "native-assignment\0"
            + str(delegation["id"])
            + "\0"
            + worker_run_id
            + "\0"
            + normalized_outcome
        ).encode("utf-8")
    ).hexdigest()
    existing = conn.execute(
        "SELECT * FROM agent_performance_events WHERE idempotency_key = ?",
        (key,),
    ).fetchone()
    expected = {
        "worker_id": str(receipt["workforce_worker_id"]),
        "version": str(receipt["specialist_version"]),
        "version_hash": str(receipt["specialist_prompt_hash"]),
        "session_id": str(delegation["session_id"]),
        "trace_id": str(delegation["trace_id"]),
        "work_unit_id": str(delegation["work_unit_id"]),
        "activation_receipt_id": receipt_id,
        "event_type": "assignment",
        "outcome": normalized_outcome,
        "score": 1.0 if normalized_outcome == "passed" else 0.0,
        "evidence_hash": evidence_hash,
        "evidence_refs": evidence_document,
    }
    if existing is not None:
        if any(existing[field] != value for field, value in expected.items()):
            raise RuntimeError("native assignment outcome evidence conflicts with its replay")
        return str(existing["id"])
    event_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO agent_performance_events "
        "(id, idempotency_key, worker_id, version, version_hash, session_id, trace_id, "
        "work_unit_id, activation_receipt_id, event_type, outcome, score, evidence_hash, "
        "evidence_refs, created_at) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
        (
            event_id,
            key,
            expected["worker_id"],
            expected["version"],
            expected["version_hash"],
            expected["session_id"],
            expected["trace_id"],
            expected["work_unit_id"],
            expected["activation_receipt_id"],
            expected["event_type"],
            expected["outcome"],
            expected["score"],
            expected["evidence_hash"],
            expected["evidence_refs"],
        ),
    )
    if store is not None:
        worker = conn.execute(
            "SELECT * FROM agent_workers WHERE worker_id = ?",
            (expected["worker_id"],),
        ).fetchone()
        if worker is not None:
            successes, disabled, review_window_days = _outcome_promotion_policy(store, None, None)
            _auto_promote_if_ready(
                conn,
                worker,
                disabled=disabled,
                required_successes=successes,
                review_window_days=review_window_days,
            )
    return event_id


def _validate_worker_registration(
    conn: Any,
    *,
    slug: str,
    version_id: str,
    parent_id: str | None,
    relation: str,
    case_id: str | None,
    contract_hash: str,
    require_active: bool,
) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    version = conn.execute(
        "SELECT * FROM agent_versions WHERE id = ?",
        (version_id,),
    ).fetchone()
    if version is None or str(version["agent_slug"]) != slug:
        raise ValueError("agent version does not belong to the worker slug")
    active = conn.execute(
        "SELECT version, hash FROM agent_active WHERE agent_slug = ?",
        (slug,),
    ).fetchone()
    if require_active and active is None:
        raise ValueError("worker registration requires an active agent revision")
    if active is not None and (
        str(active["version"]) != str(version["version"])
        or str(active["hash"]) != str(version["hash"])
    ):
        raise ValueError("worker registration requires the exact active agent revision")
    if conn.execute("SELECT 1 FROM agent_workers WHERE agent_slug = ?", (slug,)).fetchone():
        raise ValueError(f"workforce worker already exists: {slug}")
    if parent_id:
        parent = conn.execute(
            "SELECT agent_slug FROM agent_versions WHERE id = ?",
            (parent_id,),
        ).fetchone()
        if parent is None or str(parent["agent_slug"]) != slug:
            raise ValueError("parent version does not belong to the worker slug")
    if relation == "generated" and parent_id:
        raise ValueError("generated lineage cannot have a parent version")
    if relation != "generated" and not parent_id:
        raise ValueError("non-generated lineage requires a parent version")
    case = None
    if case_id:
        case = conn.execute(
            "SELECT * FROM agent_hiring_cases WHERE id = ?",
            (case_id,),
        ).fetchone()
        if case is None or str(case["status"]) != "audited":
            raise ValueError("hiring case must be audited before registration")
        if (
            str(case["case_type"]) != "hire"
            or str(case["proposed_slug"]) != slug
            or case["target_worker_id"] is not None
            or str(case["contract_hash"]) != contract_hash
        ):
            raise ValueError("hiring case does not authorize this worker contract")
    return version, case


def _activate_staged_agency_version(
    conn: Any,
    version: Mapping[str, Any],
    *,
    replace: bool = False,
) -> None:
    metadata = _decoded(version["metadata"])
    slug = str(version["agent_slug"])
    statement = "INSERT OR REPLACE INTO agent_active " if replace else "INSERT INTO agent_active "
    conn.execute(
        statement
        + "(id, agent_slug, name, division, description, source, source_id, source_version, "
        "version, hash, categories, capabilities, tool_affinity, prompt_path, activated_at) "
        f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
        (
            str(uuid.uuid4()),
            slug,
            str(metadata.get("name") or slug),
            str(metadata.get("division") or "specialized"),
            str(metadata.get("description") or ""),
            str(metadata.get("source") or "agency"),
            str(version["source_id"] or ""),
            str(version["source_version"] or metadata.get("source_version") or ""),
            str(version["version"]),
            str(version["hash"]),
            json.dumps(metadata.get("categories") or []),
            json.dumps(metadata.get("capabilities") or []),
            json.dumps(metadata.get("tool_affinity") or []),
            str(metadata.get("prompt_path") or ""),
        ),
    )
    conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (slug,))
    conn.executemany(
        "INSERT INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
        (
            (str(uuid.uuid4()), slug, str(category))
            for category in metadata.get("categories") or []
            if str(category)
        ),
    )


def synchronize_active_workforce_worker(
    conn: Any,
    *,
    agent_slug: str,
    display_name: str,
    origin: str,
    employment_class: str,
    agent_version_id: str,
    version: str,
    version_hash: str,
    recruitment_contract: str,
) -> bool:
    """Synchronize one governed active revision into the workforce overlay.

    Upstream activations bootstrap or advance employees automatically. Agency-
    owned workers stay unroutable until a hiring case registers them, and later
    amendments must use their own audited case instead of this ingestion seam.
    """

    slug = normalize_agent_slug(agent_slug)
    normalized_origin = str(origin or "").strip().casefold()
    employment = str(employment_class or "").strip().casefold()
    worker_id = stable_worker_id(slug)
    contract_hash = _document_hash(recruitment_contract)
    row = conn.execute(
        "SELECT * FROM agent_workers WHERE agent_slug = ?",
        (slug,),
    ).fetchone()
    if row is None:
        if normalized_origin == "agency":
            return False
        if normalized_origin != "upstream" or employment != "employee":
            raise ValueError("automatic workforce bootstrap is limited to upstream employees")
        conn.execute(
            "INSERT INTO agent_workers "
            "(worker_id, agent_slug, display_name, origin, employment_class, standing, "
            "current_agent_version_id, current_version, current_hash, revision, "
            "created_at, updated_at) "
            f"VALUES (?, ?, ?, 'upstream', 'employee', 'active', ?, ?, ?, 0, "
            f"{STORE_CLOCK_SQL}, {STORE_CLOCK_SQL})",
            (worker_id, slug, display_name, agent_version_id, version, version_hash),
        )
        conn.execute(
            "INSERT INTO agent_version_lineage "
            "(id, worker_id, agent_version_id, parent_version_id, relation, "
            "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
            f"VALUES (?, ?, ?, NULL, 'generated', ?, ?, NULL, {STORE_CLOCK_SQL})",
            (str(uuid.uuid4()), worker_id, agent_version_id, recruitment_contract, contract_hash),
        )
        _record_worker_event(
            conn,
            worker_id=worker_id,
            event_type="registered",
            to_class="employee",
            to_standing="active",
            version=version,
            actor="roster-ingestion",
            surface="ingestion",
        )
        return True
    if str(row["current_agent_version_id"]) == agent_version_id:
        return True
    lineage = conn.execute(
        "SELECT worker_id FROM agent_version_lineage WHERE agent_version_id = ?",
        (agent_version_id,),
    ).fetchone()
    if (str(row["origin"]) != "upstream" or normalized_origin != "upstream") and lineage is None:
        raise ValueError("Agency-owned workforce updates require an audited amendment")
    current_lineage = conn.execute(
        "SELECT relation FROM agent_version_lineage WHERE agent_version_id = ?",
        (row["current_agent_version_id"],),
    ).fetchone()
    if (
        lineage is None
        and current_lineage is not None
        and str(current_lineage["relation"]) == "agency_amendment"
    ):
        raise ValueError(
            "upstream update requires governed reconciliation with the active Agency amendment"
        )
    event_type = "revision_restored" if lineage is not None else "upstream_update"
    if lineage is not None and str(lineage["worker_id"]) != str(row["worker_id"]):
        raise ValueError("agent version lineage belongs to another worker")
    if lineage is None:
        conn.execute(
            "INSERT INTO agent_version_lineage "
            "(id, worker_id, agent_version_id, parent_version_id, relation, "
            "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
            f"VALUES (?, ?, ?, ?, 'upstream_update', ?, ?, NULL, {STORE_CLOCK_SQL})",
            (
                str(uuid.uuid4()),
                row["worker_id"],
                agent_version_id,
                row["current_agent_version_id"],
                recruitment_contract,
                contract_hash,
            ),
        )
    revision = int(row["revision"]) + 1
    updated = conn.execute(
        "UPDATE agent_workers SET current_agent_version_id = ?, current_version = ?, "
        f"current_hash = ?, revision = ?, updated_at = {STORE_CLOCK_SQL} "
        "WHERE worker_id = ? AND revision = ?",
        (
            agent_version_id,
            version,
            version_hash,
            revision,
            row["worker_id"],
            row["revision"],
        ),
    )
    if updated.rowcount != 1:
        raise RuntimeError("workforce revision conflict")
    _record_worker_event(
        conn,
        worker_id=str(row["worker_id"]),
        event_type=event_type,
        from_class=str(row["employment_class"]),
        to_class=str(row["employment_class"]),
        from_standing=str(row["standing"]),
        to_standing=str(row["standing"]),
        version=version,
        actor="roster-ingestion",
        surface="ingestion",
    )
    return True


def retire_ingested_workforce_worker(conn: Any, *, agent_slug: str, reason: str) -> bool:
    """Retire one upstream worker in the same transaction as roster removal."""

    slug = normalize_agent_slug(agent_slug)
    row = conn.execute(
        "SELECT * FROM agent_workers WHERE agent_slug = ?",
        (slug,),
    ).fetchone()
    if row is None or str(row["standing"]) == "retired":
        return False
    if str(row["standing"]) == "merged":
        raise ValueError("merged workforce identity cannot be retired by ingestion")
    revision = int(row["revision"]) + 1
    updated = conn.execute(
        "UPDATE agent_workers SET standing = 'retired', revision = ?, "
        f"updated_at = {STORE_CLOCK_SQL} WHERE worker_id = ? AND revision = ?",
        (revision, row["worker_id"], row["revision"]),
    )
    if updated.rowcount != 1:
        raise RuntimeError("workforce revision conflict")
    _record_worker_event(
        conn,
        worker_id=str(row["worker_id"]),
        event_type="retired",
        from_class=str(row["employment_class"]),
        to_class=str(row["employment_class"]),
        from_standing=str(row["standing"]),
        to_standing="retired",
        version=str(row["current_version"]),
        actor="roster-ingestion",
        surface="ingestion",
        reason=_bounded_text(reason, field="reason", maximum=2_048),
    )
    return True


def backfill_workforce_identity(conn: Any) -> int:
    """Idempotently create employee identities for governed pre-v33 roster rows."""

    rows = conn.execute(
        "SELECT a.*, v.id AS agent_version_id, v.metadata AS revision_metadata "
        "FROM agent_active AS a JOIN agent_versions AS v "
        "ON v.agent_slug = a.agent_slug AND v.version = a.version "
        "LEFT JOIN agent_workers AS worker ON worker.agent_slug = a.agent_slug "
        "WHERE worker.worker_id IS NULL ORDER BY a.agent_slug"
    ).fetchall()
    created = 0
    for row in rows:
        metadata = _decoded(row["revision_metadata"])
        projection = {
            **metadata,
            "slug": str(row["agent_slug"]),
            "display_name": str(row["name"] or row["agent_slug"]),
            "division": str(row["division"] or "specialized"),
            "description": str(row["description"] or ""),
            "version": str(row["version"]),
            "version_hash": str(row["hash"]),
            "origin": "upstream",
            "employment": "employee",
            "enabled": True,
        }
        contract = project_workforce_contract(projection, origin="upstream")
        document = json.dumps(
            contract.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        created += int(
            synchronize_active_workforce_worker(
                conn,
                agent_slug=str(row["agent_slug"]),
                display_name=str(row["name"] or row["agent_slug"]),
                origin="upstream",
                employment_class="employee",
                agent_version_id=str(row["agent_version_id"]),
                version=str(row["version"]),
                version_hash=str(row["hash"]),
                recruitment_contract=document,
            )
        )
    if created:
        conn.execute(
            "UPDATE store_counters SET value = value + ? WHERE name = 'roster-generation'",
            (created,),
        )
    return created


def _packaged_workforce_authorities() -> dict[str, tuple[dict[str, Any], str]]:
    """Load exact package-owned revisions eligible for derived-contract repair."""

    from agency_runtime.core.roster.bundled import BundledRoster
    from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
    from agency_runtime.core.workforce.known_installer import known_contractor_agent

    authorities = {str(agent["slug"]): (dict(agent), "upstream") for agent in BundledRoster()}
    for contract in KNOWN_CONTRACTORS_BY_SLUG.values():
        agent = known_contractor_agent(contract)
        slug = str(agent["slug"])
        if slug in authorities:
            raise RuntimeError(f"packaged workforce identity collision: {slug}")
        authorities[slug] = (agent, "agency")
    return authorities


def _exact_packaged_revision(row: Mapping[str, Any], agent: Mapping[str, Any]) -> bool:
    """Prove that a stored immutable revision is the exact packaged source."""

    expected_metadata = {serialized_revision_metadata(agent)}
    if str(agent.get("origin") or "").strip().casefold() == "agency":
        from agency_runtime.core.workforce.known_installer import (
            known_contractor_revision_metadata_authorities,
        )

        expected_metadata.update(
            known_contractor_revision_metadata_authorities(str(agent.get("slug") or ""))
        )
    return (
        str(row["current_version"]) == str(agent.get("version") or "")
        and str(row["current_hash"]) == str(agent.get("hash") or "")
        and str(row["version_id"]) == str(row["current_agent_version_id"])
        and str(row["version"]) == str(agent.get("version") or "")
        and str(row["version_hash"]) == str(agent.get("hash") or "")
        and str(row["content"]) == str(agent.get("prompt_body") or agent.get("content") or "")
        and str(row["metadata"]) in expected_metadata
    )


def _workforce_hash_matches_version(stored_hash: str, version_hash: str) -> bool:
    """Compare the contract's canonical digest with a version identity."""

    return stored_hash.removeprefix("sha256:") == version_hash.removeprefix("sha256:")


class WorkforceStoreMixin:
    """Persist workforce overlays without rewriting governed prompt revisions."""

    def reconcile_packaged_workforce_contracts(self) -> WorkforceContractReconciliation:
        """Re-project stale derived contracts for exact active packaged revisions.

        Prompt bodies, immutable version rows, lifecycle state, and provenance
        never change. Unknown, modified, inactive, or externally supplied
        revisions are deliberately outside this repair authority.
        """

        authorities = _packaged_workforce_authorities()
        inspected = 0
        updated = 0
        divergent: list[WorkforceContractDivergence] = []
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT worker.*, version.id AS version_id, version.version, "
                "version.hash AS version_hash, version.content, version.metadata, "
                "lineage.id AS lineage_id, "
                "COALESCE(projection.recruitment_contract, "
                "lineage.recruitment_contract) AS recruitment_contract, "
                "COALESCE(projection.recruitment_contract_hash, "
                "lineage.recruitment_contract_hash) AS recruitment_contract_hash "
                "FROM agent_workers AS worker JOIN agent_versions AS version "
                "ON version.id = worker.current_agent_version_id "
                "JOIN agent_version_lineage AS lineage "
                "ON lineage.worker_id = worker.worker_id "
                "AND lineage.agent_version_id = worker.current_agent_version_id "
                "LEFT JOIN agent_recruitment_contract_projections AS projection "
                "ON projection.id = ("
                "SELECT candidate.id "
                "FROM agent_recruitment_contract_projections AS candidate "
                "WHERE candidate.worker_id = worker.worker_id "
                "AND candidate.agent_version_id = worker.current_agent_version_id "
                "ORDER BY candidate.projection_sequence DESC LIMIT 1"
                ") "
                "WHERE worker.standing = 'active' ORDER BY worker.agent_slug"
            ).fetchall()
            sequence = int(
                conn.execute(
                    "SELECT COALESCE(MAX(projection_sequence), 0) "
                    "FROM agent_recruitment_contract_projections"
                ).fetchone()[0]
            )
            for row in rows:
                authority = authorities.get(str(row["agent_slug"]))
                if authority is None:
                    # Not package-owned at all -- a minted contractor or an
                    # externally supplied worker. Outside this authority by
                    # design, and not a divergence worth reporting.
                    continue
                agent, expected_origin = authority
                actual_origin = str(row["origin"])
                if actual_origin != expected_origin:
                    divergent.append(
                        WorkforceContractDivergence(
                            agent_slug=str(row["agent_slug"]),
                            reason="origin_drift",
                            expected_origin=expected_origin,
                            actual_origin=actual_origin,
                            expected_version=str(agent.get("version") or ""),
                            actual_version=str(row["current_version"]),
                        )
                    )
                    continue
                if not _exact_packaged_revision(row, agent):
                    # The amendment case rule 6 cares about: this worker is
                    # package-owned but its active revision is not the packaged
                    # one, so repair stops here and says so.
                    divergent.append(
                        WorkforceContractDivergence(
                            agent_slug=str(row["agent_slug"]),
                            reason="revision_modified",
                            expected_origin=expected_origin,
                            actual_origin=actual_origin,
                            expected_version=str(agent.get("version") or ""),
                            actual_version=str(row["current_version"]),
                        )
                    )
                    continue
                inspected += 1
                current_document = str(row["recruitment_contract"])
                current_hash = str(row["recruitment_contract_hash"])
                if _document_hash(current_document) != current_hash:
                    raise RuntimeError(
                        f"stored workforce recruitment contract hash is invalid: "
                        f"{row['agent_slug']}"
                    )
                try:
                    current = parse_workforce_contract(
                        safe_load_bounded_json(
                            current_document,
                            maximum_bytes=MAX_WORKFORCE_DOCUMENT_BYTES,
                            maximum_depth=16,
                            maximum_nodes=10_000,
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise RuntimeError(
                        f"stored workforce recruitment contract is invalid: {row['agent_slug']}"
                    ) from exc
                if (
                    current.worker_id != str(row["worker_id"])
                    or current.agent_id != str(row["agent_slug"])
                    or current.version != str(row["current_version"])
                    or not _workforce_hash_matches_version(
                        current.version_hash,
                        str(row["current_hash"]),
                    )
                ):
                    raise RuntimeError(
                        f"stored workforce recruitment contract identity is invalid: "
                        f"{row['agent_slug']}"
                    )
                projected = project_workforce_contract(
                    {
                        **agent,
                        "worker_id": str(row["worker_id"]),
                        "origin": str(row["origin"]),
                        "employment": str(row["employment_class"]),
                        "enabled": True,
                        "version": str(row["current_version"]),
                        "version_hash": str(row["current_hash"]),
                    },
                    origin=str(row["origin"]),
                )
                document = json.dumps(
                    projected.to_dict(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                contract_hash = _document_hash(document)
                if document == current_document and contract_hash == current_hash:
                    continue
                sequence += 1
                conn.execute(
                    "INSERT INTO agent_recruitment_contract_projections "
                    "(id, projection_sequence, worker_id, agent_version_id, "
                    "parent_contract_hash, recruitment_contract, "
                    "recruitment_contract_hash, projection_authority, created_at) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, 'agency-runtime-package', "
                    f"{STORE_CLOCK_SQL})",
                    (
                        str(uuid.uuid4()),
                        sequence,
                        row["worker_id"],
                        row["current_agent_version_id"],
                        current_hash,
                        document,
                        contract_hash,
                    ),
                )
                _record_worker_event(
                    conn,
                    worker_id=str(row["worker_id"]),
                    event_type="recruitment_contract_reprojected",
                    from_class=str(row["employment_class"]),
                    to_class=str(row["employment_class"]),
                    from_standing=str(row["standing"]),
                    to_standing=str(row["standing"]),
                    version=str(row["current_version"]),
                    actor="agency-runtime",
                    surface="package-upgrade",
                    reason="derived recruitment contract projection changed",
                    evidence=_document(
                        {
                            "from_contract_hash": current_hash,
                            "to_contract_hash": contract_hash,
                            "version_hash": str(row["current_hash"]),
                        },
                        field="evidence",
                    ),
                )
                updated += 1
            if updated:
                conn.execute(
                    "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
                )
            conn.commit()
        return WorkforceContractReconciliation(
            inspected=inspected,
            updated=updated,
            divergent=tuple(sorted(divergent, key=lambda item: item.agent_slug)),
        )

    def create_hiring_case(
        self,
        *,
        case_type: str,
        proposed_slug: str,
        work_unit_id: str,
        request_hash: str,
        gap_evidence: Mapping[str, Any],
        duplicate_evidence: Mapping[str, Any],
        contract_evidence: Mapping[str, Any] | None = None,
        critic_evidence: Mapping[str, Any] | None = None,
        model_evidence: Mapping[str, Any] | None = None,
        contract_hash: str = "",
        target_worker_id: str = "",
        session_id: str = "",
        trace_id: str = "",
        idempotency_key: str = "",
        risk_tier: str = "standard",
        human_approval_required: bool = False,
    ) -> dict[str, Any]:
        normalized_type = str(case_type or "").strip().casefold()
        if normalized_type not in _CASE_TYPES:
            raise ValueError("hiring case type is invalid")
        slug = normalize_agent_slug(proposed_slug)
        unit = _identity(work_unit_id, field="work_unit_id")
        request_digest = _digest(request_hash, field="request_hash")
        contract_document = _required_evidence(
            contract_evidence,
            field="contract_evidence",
        )
        contract_digest = _digest(contract_hash, field="contract_hash")
        if contract_digest != _document_hash(contract_document):
            raise ValueError("contract_hash does not match contract_evidence")
        gap_document = _required_evidence(gap_evidence, field="gap_evidence")
        duplicate_document = _required_evidence(
            duplicate_evidence,
            field="duplicate_evidence",
        )
        critic_document = _required_evidence(critic_evidence, field="critic_evidence")
        model_document = _required_evidence(model_evidence, field="model_evidence")
        target = _identity(target_worker_id, field="target_worker_id") if target_worker_id else None
        session = _identity(session_id, field="session_id") if session_id else ""
        trace = _identity(trace_id, field="trace_id") if trace_id else ""
        if bool(session) != bool(trace):
            raise ValueError("session_id and trace_id must be supplied together")
        if normalized_type == "amend" and target is None:
            raise ValueError("amend hiring cases require a target worker")
        if normalized_type == "hire" and target is not None:
            raise ValueError("hire cases cannot target an existing worker")
        normalized_risk = str(risk_tier or "").strip().casefold()
        if normalized_risk not in {"low", "standard", "high"}:
            raise ValueError("risk_tier is invalid")
        if not isinstance(human_approval_required, bool):
            raise TypeError("human_approval_required must be a boolean")
        if normalized_risk == "high" and not human_approval_required:
            raise ValueError("high-risk hiring requires human approval")
        key = (
            _digest(idempotency_key, field="idempotency_key")
            if idempotency_key
            else _hiring_case_key(
                case_type=normalized_type,
                proposed_slug=slug,
                target_worker_id=target,
                work_unit_id=unit,
                request_hash=request_digest,
            )
        )
        case_id = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM agent_hiring_cases WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing is not None:
                expected = {
                    "case_type": normalized_type,
                    "proposed_slug": slug,
                    "target_worker_id": target,
                    "session_id": session,
                    "trace_id": trace,
                    "work_unit_id": unit,
                    "request_hash": request_digest,
                    "gap_evidence": gap_document,
                    "duplicate_evidence": duplicate_document,
                    "contract_evidence": contract_document,
                    "critic_evidence": critic_document,
                    "model_evidence": model_document,
                    "contract_hash": contract_digest,
                    "risk_tier": normalized_risk,
                    "human_approval_required": int(human_approval_required),
                }
                if any(existing[field] != value for field, value in expected.items()):
                    raise ValueError("hiring idempotency key was reused with different evidence")
                case_id = str(existing["id"])
                return self.get_hiring_case(case_id)
            conn.execute(
                "INSERT INTO agent_hiring_cases "
                "(id, idempotency_key, case_type, status, proposed_slug, target_worker_id, session_id, trace_id, "
                "work_unit_id, request_hash, gap_evidence, duplicate_evidence, contract_evidence, "
                "critic_evidence, model_evidence, contract_hash, risk_tier, "
                "human_approval_required, created_at) "
                f"VALUES (?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
                (
                    case_id,
                    key,
                    normalized_type,
                    slug,
                    target,
                    session,
                    trace,
                    unit,
                    request_digest,
                    gap_document,
                    duplicate_document,
                    contract_document,
                    critic_document,
                    model_document,
                    contract_digest,
                    normalized_risk,
                    int(human_approval_required),
                ),
            )
        return self.get_hiring_case(case_id)

    def approve_hiring_case(self, case_id: str, *, approved_by: str) -> dict[str, Any]:
        """Record the explicit operator approval required by a high-risk hire."""

        normalized_id = _identity(case_id, field="case_id")
        operator = _bounded_text(approved_by, field="approved_by", maximum=128)
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT status, human_approval_required, human_approved_by, human_approved_at "
                "FROM agent_hiring_cases WHERE id = ?",
                (normalized_id,),
            ).fetchone()
            if row is None:
                raise KeyError("hiring case not found")
            if not bool(row["human_approval_required"]):
                raise ValueError("hiring case does not require human approval")
            if row["human_approved_at"] is not None:
                if str(row["human_approved_by"]) != operator:
                    raise ValueError("hiring case was already approved by another operator")
                if str(row["status"]) in {"proposed", "audited", "applied"}:
                    return self.get_hiring_case(normalized_id)
                raise ValueError("approved hiring case is no longer actionable")
            if str(row["status"]) != "proposed":
                raise ValueError("only a proposed hiring case can be approved")
            if row["human_approved_at"] is None:
                conn.execute(
                    "UPDATE agent_hiring_cases SET human_approved_by = ?, "
                    f"human_approved_at = {STORE_CLOCK_SQL} WHERE id = ?",
                    (operator, normalized_id),
                )
        return self.get_hiring_case(normalized_id)

    def transition_hiring_case(self, case_id: str, *, status: str) -> dict[str, Any]:
        normalized_id = _identity(case_id, field="case_id")
        target_status = str(status or "").strip().casefold()
        if target_status not in _CASE_STATUSES:
            raise ValueError("hiring case status is invalid")
        if target_status == "applied":
            raise ValueError("applied status is reserved for atomic workforce changes")
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_hiring_cases WHERE id = ?", (normalized_id,)
            ).fetchone()
            if row is None:
                raise KeyError("hiring case not found")
            current = str(row["status"])
            if target_status not in _CASE_TRANSITIONS.get(current, frozenset()):
                raise ValueError(f"invalid hiring case transition: {current} -> {target_status}")
            if target_status == "audited":
                if not _case_evidence_is_auditable(row):
                    raise ValueError("hiring case lacks validated critic and model evidence")
                if bool(row["human_approval_required"]) and not (
                    row["human_approved_at"] and str(row["human_approved_by"] or "").strip()
                ):
                    raise ValueError("hiring case requires explicit human approval")
            decided = (
                STORE_CLOCK_SQL
                if target_status in {"audited", "rejected", "folded"}
                else "decided_at"
            )
            applied = STORE_CLOCK_SQL if target_status == "applied" else "applied_at"
            conn.execute(
                f"UPDATE agent_hiring_cases SET status = ?, decided_at = {decided}, "
                f"applied_at = {applied} WHERE id = ?",
                (target_status, normalized_id),
            )
        return self.get_hiring_case(normalized_id)

    def get_hiring_case(self, case_id: str) -> dict[str, Any]:
        normalized = _identity(case_id, field="case_id")
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM agent_hiring_cases WHERE id = ?", (normalized,)
            ).fetchone()
        if row is None:
            raise KeyError("hiring case not found")
        result = dict(row)
        for field in (
            "gap_evidence",
            "duplicate_evidence",
            "contract_evidence",
            "critic_evidence",
            "model_evidence",
        ):
            result[field] = _decoded(result[field])
        result["human_approval_required"] = bool(result["human_approval_required"])
        result["evidence_included"] = True
        return result

    def list_hiring_cases(
        self,
        *,
        status: str = "",
        case_type: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return bounded newest-first hiring evidence for operator surfaces."""

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("hiring case limit must be an integer")
        if not 1 <= limit <= MAX_WORKFORCE_PAGE:
            raise ValueError("hiring case limit is invalid")
        normalized_status = str(status or "").strip().casefold()
        normalized_type = str(case_type or "").strip().casefold()
        if normalized_status and normalized_status not in _CASE_STATUSES:
            raise ValueError("hiring case status is invalid")
        if normalized_type and normalized_type not in _CASE_TYPES:
            raise ValueError("hiring case type is invalid")
        clauses: list[str] = []
        values: list[Any] = []
        if normalized_status:
            clauses.append("status = ?")
            values.append(normalized_status)
        if normalized_type:
            clauses.append("case_type = ?")
            values.append(normalized_type)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM agent_hiring_cases"
                + where
                + " ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (*values, limit),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for stored in rows:
            item = dict(stored)
            for field in (
                "gap_evidence",
                "duplicate_evidence",
                "contract_evidence",
                "critic_evidence",
                "model_evidence",
            ):
                item[field] = _decoded(item[field])
            item["human_approval_required"] = bool(item["human_approval_required"])
            item["evidence_included"] = True
            result.append(item)
        return result

    def get_hiring_cases_page_snapshot(
        self,
        *,
        status: str = "",
        case_type: str = "",
        risk_tier: str = "",
        limit: int = 100,
        after_created_at: str = "",
        after_id: str = "",
    ) -> dict[str, Any]:
        """Return one newest-first fixed-field summary page with snapshot-derived totals."""

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("hiring case limit must be an integer")
        if not 1 <= limit <= MAX_HIRING_SUMMARY_PAGE:
            raise ValueError("hiring case limit is invalid")
        normalized_status = str(status or "").strip().casefold()
        normalized_type = str(case_type or "").strip().casefold()
        normalized_risk = str(risk_tier or "").strip().casefold()
        if normalized_status and normalized_status not in _CASE_STATUSES:
            raise ValueError("hiring case status is invalid")
        if normalized_type and normalized_type not in _CASE_TYPES:
            raise ValueError("hiring case type is invalid")
        if normalized_risk and normalized_risk not in _RISK_TIERS:
            raise ValueError("hiring case risk_tier is invalid")
        cursor_time = str(after_created_at or "").strip()
        cursor_id = str(after_id or "").strip()
        if bool(cursor_time) != bool(cursor_id):
            raise ValueError("hiring cursor is incomplete")

        clauses: list[str] = []
        values: list[Any] = []
        if normalized_status:
            clauses.append("status = ?")
            values.append(normalized_status)
        if normalized_type:
            clauses.append("case_type = ?")
            values.append(normalized_type)
        if normalized_risk:
            clauses.append("risk_tier = ?")
            values.append(normalized_risk)
        filter_where = " WHERE " + " AND ".join(clauses) if clauses else ""
        page_clauses = list(clauses)
        page_values = list(values)
        if cursor_time:
            page_clauses.append("(created_at < ? OR (created_at = ? AND id < ?))")
            page_values.extend((cursor_time, cursor_time, cursor_id))
        page_where = " WHERE " + " AND ".join(page_clauses) if page_clauses else ""

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            total_count = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_hiring_cases").fetchone()["count"]
            )
            filtered_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM agent_hiring_cases" + filter_where,
                    values,
                ).fetchone()["count"]
            )
            status_counts = {
                str(row["status"]): int(row["count"])
                for row in conn.execute(
                    "SELECT status, COUNT(*) AS count FROM agent_hiring_cases GROUP BY status"
                ).fetchall()
            }
            type_counts = {
                str(row["case_type"]): int(row["count"])
                for row in conn.execute(
                    "SELECT case_type, COUNT(*) AS count FROM agent_hiring_cases GROUP BY case_type"
                ).fetchall()
            }
            risk_tier_counts = {
                str(row["risk_tier"]): int(row["count"])
                for row in conn.execute(
                    "SELECT risk_tier, COUNT(*) AS count FROM agent_hiring_cases GROUP BY risk_tier"
                ).fetchall()
            }
            revision_rows = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, status, case_type, proposed_slug, target_worker_id, "
                    "created_at, decided_at, applied_at, human_approved_at "
                    "FROM agent_hiring_cases ORDER BY created_at DESC, id DESC"
                ).fetchall()
            ]
            stored_rows = conn.execute(
                "SELECT id, case_type, status, proposed_slug, target_worker_id, "
                "work_unit_id, risk_tier, human_approval_required, human_approved_by, "
                "human_approved_at, created_at, decided_at, applied_at "
                "FROM agent_hiring_cases"
                + page_where
                + " ORDER BY created_at DESC, id DESC LIMIT ?",
                (*page_values, limit + 1),
            ).fetchall()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        cases = [_hiring_case_summary(stored) for stored in stored_rows[:limit]]
        serialized_cases = json.dumps(
            cases,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(serialized_cases) > (
            MAX_HIRING_COLLECTION_RESPONSE_BYTES - _HIRING_COLLECTION_METADATA_RESERVE_BYTES
        ):
            raise WorkforcePayloadBudgetError(
                "hiring collection summary exceeds its response budget"
            )
        return {
            "rows": cases,
            "total_count": total_count,
            "filtered_count": filtered_count,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "risk_tier_counts": risk_tier_counts,
            "truncated": len(stored_rows) > limit,
            "next_created_at": str(cases[-1]["created_at"])
            if len(stored_rows) > limit and cases
            else "",
            "next_id": str(cases[-1]["id"]) if len(stored_rows) > limit and cases else "",
            "collection_revision": _collection_revision("hiring.v1", revision_rows),
        }

    def register_workforce_worker(
        self,
        *,
        agent_slug: str,
        display_name: str,
        origin: str,
        employment_class: str,
        agent_version_id: str,
        recruitment_contract: Mapping[str, Any],
        relation: str,
        hiring_case_id: str = "",
        parent_version_id: str = "",
    ) -> dict[str, Any]:
        slug = normalize_agent_slug(agent_slug)
        name = _bounded_text(display_name, field="display_name")
        normalized_origin = str(origin or "").strip().casefold()
        employment = str(employment_class or "").strip().casefold()
        if normalized_origin not in {"upstream", "agency"}:
            raise ValueError("origin must be upstream or agency")
        if employment not in _EMPLOYMENT_CLASSES:
            raise ValueError("employment_class is invalid")
        version_id = _identity(agent_version_id, field="agent_version_id")
        parent_id = (
            _identity(parent_version_id, field="parent_version_id") if parent_version_id else None
        )
        case_id = _identity(hiring_case_id, field="hiring_case_id") if hiring_case_id else None
        normalized_relation = str(relation or "").strip().casefold()
        if normalized_relation not in {"generated", "upstream_update", "agency_amendment", "merge"}:
            raise ValueError("version relation is invalid")
        contract = _document(recruitment_contract, field="recruitment_contract", allow_empty=False)
        contract_hash = _document_hash(contract)
        if normalized_origin == "upstream" and employment != "employee":
            raise ValueError("upstream workers must enter as employees")
        if normalized_origin == "agency" and not case_id:
            raise ValueError("Agency-owned workers require an audited hiring case")
        worker_id = stable_worker_id(slug)
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            version, _case = _validate_worker_registration(
                conn,
                slug=slug,
                version_id=version_id,
                parent_id=parent_id,
                relation=normalized_relation,
                case_id=case_id,
                contract_hash=contract_hash,
                require_active=normalized_origin != "agency",
            )
            conn.execute(
                "INSERT INTO agent_workers "
                "(worker_id, agent_slug, display_name, origin, employment_class, standing, "
                "current_agent_version_id, current_version, current_hash, revision, "
                "created_at, updated_at) "
                f"VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?, 0, {STORE_CLOCK_SQL}, {STORE_CLOCK_SQL})",
                (
                    worker_id,
                    slug,
                    name,
                    normalized_origin,
                    employment,
                    version_id,
                    version["version"],
                    version["hash"],
                ),
            )
            conn.execute(
                "INSERT INTO agent_version_lineage "
                "(id, worker_id, agent_version_id, parent_version_id, relation, "
                "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
                f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
                (
                    str(uuid.uuid4()),
                    worker_id,
                    version_id,
                    parent_id,
                    normalized_relation,
                    contract,
                    contract_hash,
                    case_id,
                ),
            )
            if case_id:
                applied = conn.execute(
                    "UPDATE agent_hiring_cases SET status = 'applied', "
                    f"applied_at = {STORE_CLOCK_SQL} WHERE id = ? AND status = 'audited'",
                    (case_id,),
                )
                if applied.rowcount != 1:
                    raise RuntimeError("hiring case was already consumed")
            if normalized_origin == "agency":
                _activate_staged_agency_version(conn, version)
            _record_worker_event(
                conn,
                worker_id=worker_id,
                event_type="registered",
                to_class=employment,
                to_standing="active",
                version=str(version["version"]),
                hiring_case_id=case_id,
            )
            conn.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
        return self.get_workforce_worker(worker_id)

    def apply_workforce_amendment(
        self,
        worker_id_or_slug: str,
        *,
        expected_revision: int,
        agent_version_id: str,
        recruitment_contract: Mapping[str, Any],
        hiring_case_id: str,
    ) -> dict[str, Any]:
        """Apply one audited Agency amendment without rewriting upstream history."""

        identity = _bounded_text(worker_id_or_slug, field="worker identity", maximum=256)
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise TypeError("expected_revision must be an integer")
        if expected_revision < 0:
            raise ValueError("expected_revision is invalid")
        version_id = _identity(agent_version_id, field="agent_version_id")
        case_id = _identity(hiring_case_id, field="hiring_case_id")
        contract = _document(recruitment_contract, field="recruitment_contract", allow_empty=False)
        contract_hash = _document_hash(contract)
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            worker = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (identity, identity.casefold()),
            ).fetchone()
            if worker is None:
                raise KeyError("workforce worker not found")
            if int(worker["revision"]) != expected_revision:
                raise RuntimeError("workforce revision conflict")
            if str(worker["standing"]) in {"retired", "merged"}:
                raise ValueError("terminal workforce state cannot be amended")
            version = conn.execute(
                "SELECT * FROM agent_versions WHERE id = ?",
                (version_id,),
            ).fetchone()
            if version is None or str(version["agent_slug"]) != str(worker["agent_slug"]):
                raise ValueError("amendment version does not belong to the worker")
            if conn.execute(
                "SELECT 1 FROM agent_version_lineage WHERE agent_version_id = ?",
                (version_id,),
            ).fetchone():
                raise ValueError("amendment version already has governed lineage")
            case = conn.execute(
                "SELECT * FROM agent_hiring_cases WHERE id = ?",
                (case_id,),
            ).fetchone()
            if case is None or str(case["status"]) != "audited":
                raise ValueError("amendment hiring case must be audited")
            if (
                str(case["case_type"]) != "amend"
                or str(case["proposed_slug"]) != str(worker["agent_slug"])
                or str(case["target_worker_id"] or "") != str(worker["worker_id"])
                or str(case["contract_hash"]) != contract_hash
            ):
                raise ValueError("hiring case does not authorize this amendment")
            conn.execute(
                "INSERT INTO agent_version_lineage "
                "(id, worker_id, agent_version_id, parent_version_id, relation, "
                "recruitment_contract, recruitment_contract_hash, hiring_case_id, created_at) "
                f"VALUES (?, ?, ?, ?, 'agency_amendment', ?, ?, ?, {STORE_CLOCK_SQL})",
                (
                    str(uuid.uuid4()),
                    worker["worker_id"],
                    version_id,
                    worker["current_agent_version_id"],
                    contract,
                    contract_hash,
                    case_id,
                ),
            )
            revision = int(worker["revision"]) + 1
            updated = conn.execute(
                "UPDATE agent_workers SET current_agent_version_id = ?, current_version = ?, "
                f"current_hash = ?, revision = ?, updated_at = {STORE_CLOCK_SQL} "
                "WHERE worker_id = ? AND revision = ?",
                (
                    version_id,
                    version["version"],
                    version["hash"],
                    revision,
                    worker["worker_id"],
                    expected_revision,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("workforce revision conflict")
            _activate_staged_agency_version(conn, version, replace=True)
            applied = conn.execute(
                "UPDATE agent_hiring_cases SET status = 'applied', "
                f"applied_at = {STORE_CLOCK_SQL} WHERE id = ? AND status = 'audited'",
                (case_id,),
            )
            if applied.rowcount != 1:
                raise RuntimeError("amendment hiring case was already consumed")
            _record_worker_event(
                conn,
                worker_id=str(worker["worker_id"]),
                event_type="amended",
                from_class=str(worker["employment_class"]),
                to_class=str(worker["employment_class"]),
                from_standing=str(worker["standing"]),
                to_standing=str(worker["standing"]),
                version=str(version["version"]),
                hiring_case_id=case_id,
                actor="hiring-pipeline",
                surface="inference",
                reason="validated capability amendment",
            )
            conn.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
        return self.get_workforce_worker(str(worker["worker_id"]))

    def get_workforce_worker(
        self,
        worker_id_or_slug: str,
        *,
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any]:
        value = _bounded_text(worker_id_or_slug, field="worker identity", maximum=256)
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (value, value.casefold()),
            ).fetchone()
        if row is None:
            raise KeyError("workforce worker not found")
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        return _worker_projection(row, disabled)

    def get_workforce_workers_by_slugs(
        self,
        slugs: Collection[str],
        *,
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Return one bounded worker snapshot keyed by exact canonical slug."""

        if isinstance(slugs, (str, bytes, bytearray, Mapping)) or not isinstance(slugs, Collection):
            raise TypeError("workforce slugs must be a collection of strings")
        if len(slugs) > _MAX_WORKFORCE_SLUG_LOOKUP:
            raise ValueError(
                f"workforce slugs must contain at most {_MAX_WORKFORCE_SLUG_LOOKUP} entries"
            )
        normalized = tuple(normalize_agent_slug(slug) for slug in slugs)
        if len(normalized) != len(set(normalized)):
            raise ValueError("workforce slugs must not contain duplicates")
        if not normalized:
            return {}
        ordered = tuple(sorted(normalized))
        placeholders = ",".join("?" for _slug in ordered)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM agent_workers "
                f"WHERE agent_slug IN ({placeholders}) ORDER BY agent_slug",  # nosec B608
                ordered,
            ).fetchall()
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        return {str(row["agent_slug"]): _worker_projection(row, disabled) for row in rows}

    def get_workforce_worker_detail(
        self,
        worker_id_or_slug: str,
        *,
        evidence_limit: int = 100,
        disabled_agents: Container[str] | None = None,
        include_history_documents: bool = True,
    ) -> dict[str, Any]:
        """Return one worker with newest bounded evidence and exact collection totals."""

        if isinstance(evidence_limit, bool) or not isinstance(evidence_limit, int):
            raise TypeError("workforce evidence limit must be an integer")
        if not 1 <= evidence_limit <= MAX_WORKFORCE_PAGE:
            raise ValueError("workforce evidence limit is invalid")
        if not isinstance(include_history_documents, bool):
            raise TypeError("include_history_documents must be a boolean")
        value = _bounded_text(worker_id_or_slug, field="worker identity", maximum=256)
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        with closing(self._connect()) as conn:
            conn.execute("BEGIN")
            worker_row = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (value, value.casefold()),
            ).fetchone()
            if worker_row is None:
                raise KeyError("workforce worker not found")
            worker = _worker_projection(worker_row, disabled)
            worker_id = str(worker["worker_id"])
            slug = str(worker["agent_slug"])
            current = conn.execute(
                "SELECT COALESCE(projection.recruitment_contract, "
                "lineage.recruitment_contract) AS recruitment_contract, "
                "COALESCE(projection.recruitment_contract_hash, "
                "lineage.recruitment_contract_hash) AS recruitment_contract_hash "
                "FROM agent_workers AS workforce JOIN agent_version_lineage AS lineage "
                "ON lineage.worker_id = workforce.worker_id "
                "AND lineage.agent_version_id = workforce.current_agent_version_id "
                "LEFT JOIN agent_recruitment_contract_projections AS projection "
                "ON projection.id = (SELECT candidate.id "
                "FROM agent_recruitment_contract_projections AS candidate "
                "WHERE candidate.worker_id = workforce.worker_id "
                "AND candidate.agent_version_id = workforce.current_agent_version_id "
                "ORDER BY candidate.projection_sequence DESC LIMIT 1) "
                "WHERE workforce.worker_id = ?",
                (worker_id,),
            ).fetchone()
            if current is None:
                raise RuntimeError("workforce current-version lineage is incomplete")
            contract = _decoded(current["recruitment_contract"])
            if _document_hash(str(current["recruitment_contract"])) != str(
                current["recruitment_contract_hash"]
            ):
                raise RuntimeError("stored workforce recruitment contract hash is invalid")
            lineage_source = (
                " FROM agent_version_lineage AS lineage "
                "INNER JOIN agent_versions AS version ON version.id = lineage.agent_version_id "
                "WHERE lineage.worker_id = ?"
            )
            lineage_total_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count" + lineage_source,
                    (worker_id,),
                ).fetchone()["count"]
            )
            lineage = [
                dict(row)
                for row in conn.execute(
                    "SELECT lineage.id, lineage.agent_version_id, lineage.parent_version_id, "
                    "lineage.relation, lineage.recruitment_contract_hash, "
                    "lineage.hiring_case_id, lineage.created_at, version.version, version.hash "
                    + lineage_source
                    + " "
                    "ORDER BY lineage.created_at DESC, lineage.rowid DESC LIMIT ?",
                    (worker_id, evidence_limit),
                ).fetchall()
            ]
            events_total_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM agent_worker_events WHERE worker_id = ?",
                    (worker_id,),
                ).fetchone()["count"]
            )
            if include_history_documents:
                events = []
                for row in conn.execute(
                    "SELECT * FROM agent_worker_events WHERE worker_id = ? "
                    "ORDER BY event_sequence DESC LIMIT ?",
                    (worker_id, evidence_limit),
                ).fetchall():
                    item = dict(row)
                    item["evidence"] = _decoded(item["evidence"])
                    events.append(item)
            else:
                events = []
                for row in conn.execute(
                    "SELECT id, event_sequence, worker_id, event_type, from_class, "
                    "to_class, from_standing, to_standing, version, "
                    "merged_into_worker_id, hiring_case_id, actor, surface, session_id, "
                    "trace_id, reason, created_at FROM agent_worker_events "
                    "WHERE worker_id = ? ORDER BY event_sequence DESC LIMIT ?",
                    (worker_id, evidence_limit),
                ).fetchall():
                    item = dict(row)
                    reason = str(item.pop("reason") or "")
                    item["reason_present"] = bool(reason)
                    events.append(item)
            outcomes_total_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM agent_performance_events WHERE worker_id = ?",
                    (worker_id,),
                ).fetchone()["count"]
            )
            if include_history_documents:
                outcomes = []
                for row in conn.execute(
                    "SELECT * FROM agent_performance_events WHERE worker_id = ? "
                    "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (worker_id, evidence_limit),
                ).fetchall():
                    item = dict(row)
                    item["evidence_refs"] = _decoded(item["evidence_refs"])
                    outcomes.append(item)
            else:
                outcomes = []
                for row in conn.execute(
                    "SELECT id, worker_id, version, version_hash, session_id, trace_id, "
                    "work_unit_id, activation_receipt_id, event_type, outcome, score, "
                    "evidence_hash, created_at, CASE WHEN "
                    "NULLIF(TRIM(CAST(json_extract(evidence_refs, "
                    "'$.independent_verifier_worker_id') AS TEXT)), '') IS NOT NULL "
                    "AND TRIM(CAST(json_extract(evidence_refs, "
                    "'$.independent_verifier_worker_id') AS TEXT)) <> worker_id "
                    "AND NULLIF(TRIM(CAST(json_extract(evidence_refs, "
                    "'$.independent_verification_receipt_id') AS TEXT)), '') IS NOT NULL "
                    "AND json_type(evidence_refs, "
                    "'$.independent_verification_validated') = 'true' "
                    "THEN 1 ELSE 0 END AS _promotion_evidence_qualified "
                    "FROM agent_performance_events WHERE worker_id = ? "
                    "ORDER BY created_at DESC, rowid DESC LIMIT ?",
                    (worker_id, evidence_limit),
                ).fetchall():
                    item = dict(row)
                    item["_promotion_evidence_qualified"] = bool(
                        item["_promotion_evidence_qualified"]
                    )
                    outcomes.append(item)
            case_where = (
                " WHERE hiring.target_worker_id = ? OR hiring.proposed_slug = ? "
                "OR EXISTS (SELECT 1 FROM agent_version_lineage AS lineage "
                "WHERE lineage.worker_id = ? AND lineage.hiring_case_id = hiring.id)"
            )
            case_values = (worker_id, slug, worker_id)
            hiring_cases_total_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS count FROM agent_hiring_cases AS hiring" + case_where,
                    case_values,
                ).fetchone()["count"]
            )
            cases = [
                _hiring_case_summary(row)
                for row in conn.execute(
                    "SELECT hiring.id, hiring.case_type, hiring.status, hiring.proposed_slug, "
                    "hiring.target_worker_id, hiring.work_unit_id, hiring.risk_tier, "
                    "hiring.human_approval_required, hiring.human_approved_by, "
                    "hiring.human_approved_at, hiring.created_at, hiring.decided_at, "
                    "hiring.applied_at FROM agent_hiring_cases AS hiring"
                    + case_where
                    + " ORDER BY hiring.created_at DESC, hiring.rowid DESC LIMIT ?",
                    (*case_values, evidence_limit),
                ).fetchall()
            ]
            conn.commit()
        return {
            "worker": worker,
            "recruitment_contract": contract,
            "evidence_limit": evidence_limit,
            "lineage": lineage,
            "lineage_total_count": lineage_total_count,
            "lineage_truncated": lineage_total_count > len(lineage),
            "events": events,
            "events_total_count": events_total_count,
            "events_truncated": events_total_count > len(events),
            "outcomes": outcomes,
            "outcomes_total_count": outcomes_total_count,
            "outcomes_truncated": outcomes_total_count > len(outcomes),
            "hiring_cases": cases,
            "hiring_cases_total_count": hiring_cases_total_count,
            "hiring_cases_truncated": hiring_cases_total_count > len(cases),
        }

    def list_workforce_workers(
        self,
        *,
        state: str = "",
        limit: int = 100,
        after_slug: str = "",
        disabled_agents: Container[str] | None = None,
    ) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("workforce limit must be an integer")
        if not 1 <= limit <= MAX_WORKFORCE_PAGE:
            raise ValueError("workforce limit is invalid")
        normalized_state = str(state or "").strip().casefold()
        allowed_states = _STANDINGS | _EMPLOYMENT_CLASSES | {"disabled"}
        if normalized_state and normalized_state not in allowed_states:
            raise ValueError("workforce state is invalid")
        after = normalize_agent_slug(after_slug) if after_slug else ""
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        result: list[dict[str, Any]] = []
        cursor = after
        with closing(self._connect()) as conn:
            while len(result) < limit:
                rows = conn.execute(
                    "SELECT * FROM agent_workers WHERE agent_slug > ? ORDER BY agent_slug LIMIT ?",
                    (cursor, min(MAX_WORKFORCE_PAGE, max(limit * 2, 32))),
                ).fetchall()
                if not rows:
                    break
                cursor = str(rows[-1]["agent_slug"])
                for row in rows:
                    projected = _worker_projection(row, disabled)
                    if not normalized_state or projected["state"] == normalized_state:
                        result.append(projected)
                        if len(result) == limit:
                            break
        return result

    def get_workforce_page_snapshot(
        self,
        *,
        state: str = "",
        limit: int = 100,
        after_slug: str = "",
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any]:
        """Return one stable slug-keyset workforce page and complete facets."""

        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("workforce limit must be an integer")
        if not 1 <= limit <= MAX_WORKFORCE_PAGE:
            raise ValueError("workforce limit is invalid")
        normalized_state = str(state or "").strip().casefold()
        allowed_states = _STANDINGS | _EMPLOYMENT_CLASSES | {"disabled"}
        if normalized_state and normalized_state not in allowed_states:
            raise ValueError("workforce state is invalid")
        after = normalize_agent_slug(after_slug) if after_slug else ""
        disabled = (
            self.get_disabled_agent_slugs()
            if disabled_agents is None
            else frozenset(disabled_agents)
        )

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            projected = [
                _worker_projection(row, disabled)
                for row in conn.execute(
                    "SELECT * FROM agent_workers ORDER BY agent_slug"
                ).fetchall()
            ]
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        counts: dict[str, int] = {}
        for item in projected:
            key = str(item["state"])
            counts[key] = counts.get(key, 0) + 1
        filtered = [
            item for item in projected if not normalized_state or item["state"] == normalized_state
        ]
        remaining = [item for item in filtered if str(item["agent_slug"]) > after]
        page = remaining[: limit + 1]
        rows = page[:limit]
        revision_rows = [
            {
                "agent_slug": str(item["agent_slug"]),
                "current_version": str(item["current_version"]),
                "revision": int(item["revision"]),
                "state": str(item["state"]),
                "worker_id": str(item["worker_id"]),
            }
            for item in projected
        ]
        return {
            "rows": rows,
            "total_count": len(projected),
            "filtered_count": len(filtered),
            "counts": counts,
            "truncated": len(page) > limit,
            "next_slug": str(rows[-1]["agent_slug"]) if len(page) > limit and rows else "",
            "collection_revision": _collection_revision("workforce.v1", revision_rows),
        }

    def transition_workforce_worker(
        self,
        worker_id_or_slug: str,
        *,
        action: str,
        expected_revision: int,
        reason: str,
        merged_into_worker_id: str = "",
        actor: str = "operator",
        surface: str = "cli",
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any]:
        value = _bounded_text(worker_id_or_slug, field="worker identity", maximum=256)
        normalized_action = str(action or "").strip().casefold()
        if normalized_action not in {"promote", "suspend", "resume", "retire", "merge"}:
            raise ValueError("workforce action is invalid")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise TypeError("expected_revision must be an integer")
        if expected_revision < 0:
            raise ValueError("expected_revision is invalid")
        normalized_reason = _bounded_text(reason, field="reason", maximum=2_048)
        target_identity = (
            _bounded_text(
                merged_into_worker_id,
                field="merged_into_worker_id",
                maximum=256,
            )
            if merged_into_worker_id
            else None
        )
        disabled = (
            self.get_disabled_agent_slugs()
            if disabled_agents is None
            else frozenset(disabled_agents)
        )
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (value, value.casefold()),
            ).fetchone()
            if row is None:
                raise KeyError("workforce worker not found")
            if int(row["revision"]) != int(expected_revision):
                raise RuntimeError("workforce revision conflict")
            if normalized_action == "promote" and str(row["agent_slug"]) in disabled:
                raise ValueError("a disabled contractor must be enabled before promotion")
            target = None
            if target_identity:
                target_row = conn.execute(
                    "SELECT worker_id, agent_slug FROM agent_workers "
                    "WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                    (target_identity, target_identity.casefold()),
                ).fetchone()
                if target_row is None:
                    raise ValueError("merge target is invalid")
                if str(target_row["agent_slug"]) in disabled:
                    raise ValueError("merge target must be enabled")
                target = str(target_row["worker_id"])
            before_class = str(row["employment_class"])
            before_standing = str(row["standing"])
            employment, standing, target = _transition_state(
                conn,
                row,
                action=normalized_action,
                target=target,
            )
            revision = int(row["revision"]) + 1
            updated = conn.execute(
                "UPDATE agent_workers SET employment_class = ?, standing = ?, "
                f"merged_into_worker_id = ?, revision = ?, updated_at = {STORE_CLOCK_SQL} "
                "WHERE worker_id = ? AND revision = ?",
                (employment, standing, target, revision, row["worker_id"], expected_revision),
            )
            if updated.rowcount != 1:
                raise RuntimeError("workforce revision conflict")
            _record_worker_event(
                conn,
                worker_id=str(row["worker_id"]),
                event_type=normalized_action,
                from_class=before_class,
                to_class=employment,
                from_standing=before_standing,
                to_standing=standing,
                version=str(row["current_version"]),
                merged_into_worker_id=target,
                actor=_bounded_text(actor, field="actor", maximum=128),
                surface=_bounded_text(surface, field="surface", maximum=64),
                reason=normalized_reason,
            )
            conn.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
        return self.get_workforce_worker(str(row["worker_id"]))

    def record_workforce_enablement(
        self,
        worker_id_or_slug: str,
        *,
        enabled: bool,
        config_revision: str,
        reason: str,
        actor: str = "operator",
        surface: str = "cli",
    ) -> None:
        """Append idempotent operator evidence for an activation-policy change."""

        if not isinstance(enabled, bool):
            raise TypeError("enabled must be a boolean")
        identity = _bounded_text(worker_id_or_slug, field="worker identity", maximum=256)
        revision = _bounded_text(config_revision, field="config revision", maximum=128)
        normalized_reason = _bounded_text(reason, field="reason", maximum=2_048)
        evidence = _document(
            {"config_revision": revision, "enabled": enabled},
            field="enablement evidence",
        )
        event_type = "enable" if enabled else "disable"
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (identity, identity.casefold()),
            ).fetchone()
            if row is None:
                raise KeyError("workforce worker not found")
            existing = conn.execute(
                "SELECT 1 FROM agent_worker_events "
                "WHERE worker_id = ? AND event_type = ? AND evidence = ? LIMIT 1",
                (row["worker_id"], event_type, evidence),
            ).fetchone()
            if existing is not None:
                return
            _record_worker_event(
                conn,
                worker_id=str(row["worker_id"]),
                event_type=event_type,
                from_class=str(row["employment_class"]),
                to_class=str(row["employment_class"]),
                from_standing=str(row["standing"]),
                to_standing=str(row["standing"]),
                version=str(row["current_version"]),
                actor=_bounded_text(actor, field="actor", maximum=128),
                surface=_bounded_text(surface, field="surface", maximum=64),
                reason=normalized_reason,
                evidence=evidence,
            )

    def record_workforce_outcome(
        self,
        worker_id_or_slug: str,
        *,
        idempotency_key: str,
        event_type: str,
        outcome: str,
        evidence_hash: str,
        evidence_refs: Mapping[str, Any],
        score: float | None = None,
        session_id: str = "",
        trace_id: str = "",
        work_unit_id: str = "",
        activation_receipt_id: str = "",
        auto_promote_successes: int | None = None,
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any]:
        worker_identity = _bounded_text(
            worker_id_or_slug,
            field="worker identity",
            maximum=256,
        )
        key = _digest(idempotency_key, field="idempotency_key")
        event = _bounded_text(event_type, field="event_type", maximum=64).casefold()
        result = _bounded_text(outcome, field="outcome", maximum=64).casefold()
        evidence_digest = _digest(evidence_hash, field="evidence_hash")
        if score is not None and (isinstance(score, bool) or not 0.0 <= float(score) <= 1.0):
            raise ValueError("score must be between 0 and 1")
        session = _identity(session_id, field="session_id") if session_id else ""
        trace = _identity(trace_id, field="trace_id") if trace_id else ""
        if bool(session) != bool(trace):
            raise ValueError("session_id and trace_id must be supplied together")
        unit = _identity(work_unit_id, field="work_unit_id") if work_unit_id else ""
        activation_id = (
            _identity(activation_receipt_id, field="activation_receipt_id")
            if activation_receipt_id
            else ""
        )
        if event in _ACTIVATION_BOUND_OUTCOMES and not activation_id:
            raise ValueError(f"{event} outcomes require an activation receipt")
        auto_promote_successes, disabled, review_window_days = _outcome_promotion_policy(
            self,
            auto_promote_successes,
            disabled_agents,
        )
        event_id = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            worker = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (worker_identity, worker_identity.casefold()),
            ).fetchone()
            if worker is None:
                raise KeyError("workforce worker not found")
            version, version_hash, session, trace, unit = _bind_outcome_activation(
                conn,
                worker,
                activation_id=activation_id,
                session=session,
                trace=trace,
                unit=unit,
            )
            evidence_document = _validated_outcome_evidence(
                conn,
                worker,
                event=event,
                session=session,
                trace=trace,
                evidence_refs=evidence_refs,
            )
            existing = conn.execute(
                "SELECT * FROM agent_performance_events WHERE idempotency_key = ?", (key,)
            ).fetchone()
            if existing is not None:
                expected = {
                    "worker_id": str(worker["worker_id"]),
                    "version": version,
                    "version_hash": version_hash,
                    "session_id": session,
                    "trace_id": trace,
                    "work_unit_id": unit,
                    "activation_receipt_id": activation_id,
                    "event_type": event,
                    "outcome": result,
                    "score": score,
                    "evidence_hash": evidence_digest,
                    "evidence_refs": evidence_document,
                }
                if any(existing[field] != value for field, value in expected.items()):
                    raise ValueError(
                        "performance idempotency key was reused with different evidence"
                    )
                row = existing
            else:
                conn.execute(
                    "INSERT INTO agent_performance_events "
                    "(id, idempotency_key, worker_id, version, version_hash, session_id, trace_id, "
                    "work_unit_id, activation_receipt_id, event_type, outcome, score, evidence_hash, "
                    "evidence_refs, created_at) "
                    f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, {STORE_CLOCK_SQL})",
                    (
                        event_id,
                        key,
                        worker["worker_id"],
                        version,
                        version_hash,
                        session,
                        trace,
                        unit,
                        activation_id,
                        event,
                        result,
                        score,
                        evidence_digest,
                        evidence_document,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM agent_performance_events WHERE id = ?",
                    (event_id,),
                ).fetchone()
            _auto_promote_if_ready(
                conn,
                worker,
                disabled=disabled,
                required_successes=auto_promote_successes,
                review_window_days=review_window_days,
            )
        projection = dict(row)
        projection["evidence_refs"] = _decoded(projection["evidence_refs"])
        return projection


__all__ = [
    "MAX_HIRING_COLLECTION_RESPONSE_BYTES",
    "MAX_HIRING_SUMMARY_PAGE",
    "MAX_WORKFORCE_DOCUMENT_BYTES",
    "MAX_WORKFORCE_PAGE",
    "WorkforcePayloadBudgetError",
    "WorkforceStoreMixin",
    "record_native_assignment_outcome",
    "stable_worker_id",
]
