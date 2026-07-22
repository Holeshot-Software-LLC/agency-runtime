"""Durable workforce identity, hiring, lineage, lifecycle, and outcome evidence."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Container, Mapping
from contextlib import closing
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled, normalize_agent_slug
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.store.schema import STORE_CLOCK_SQL
from agency_runtime.core.workforce.contract import project_workforce_contract
from agency_runtime.core.workforce.identity import stable_worker_id

MAX_WORKFORCE_DOCUMENT_BYTES = 256 * 1024
MAX_WORKFORCE_PAGE = 1_000
_EMPLOYMENT_CLASSES = frozenset({"contractor", "employee"})
_STANDINGS = frozenset({"active", "suspended", "retired", "merged"})
_CASE_TYPES = frozenset({"hire", "amend"})
_CASE_STATUSES = frozenset({"proposed", "audited", "rejected", "applied", "folded"})
_CASE_TRANSITIONS = {
    "proposed": frozenset({"audited", "rejected", "folded"}),
    "audited": frozenset({"rejected", "folded"}),
}
_ACTIVATION_BOUND_OUTCOMES = frozenset(
    {"assignment", "artifact", "review", "test", "acceptance", "failure"}
)


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
        value = json.loads(str(document or "{}"))
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


def _case_evidence_is_auditable(row: Mapping[str, Any]) -> bool:
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
        and all(
            isinstance(receipt, Mapping)
            and bool(str(receipt.get("provider") or "").strip())
            and bool(str(receipt.get("actual_model") or "").strip())
            and bool(str(receipt.get("receipt_id") or "").strip())
            for receipt in receipts
        )
    )


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


class WorkforceStoreMixin:
    """Persist workforce overlays without rewriting governed prompt revisions."""

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
            if str(row["status"]) != "proposed":
                raise ValueError("only a proposed hiring case can be approved")
            if row["human_approved_at"] is None:
                conn.execute(
                    "UPDATE agent_hiring_cases SET human_approved_by = ?, "
                    f"human_approved_at = {STORE_CLOCK_SQL} WHERE id = ?",
                    (operator, normalized_id),
                )
            elif str(row["human_approved_by"]) != operator:
                raise ValueError("hiring case was already approved by another operator")
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
        return result

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
        target = (
            _identity(merged_into_worker_id, field="merged_into_worker_id")
            if merged_into_worker_id
            else None
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
        evidence_document = _document(evidence_refs, field="evidence_refs")
        event_id = str(uuid.uuid4())
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            worker = conn.execute(
                "SELECT * FROM agent_workers WHERE worker_id = ? OR agent_slug = ? LIMIT 1",
                (worker_identity, worker_identity.casefold()),
            ).fetchone()
            if worker is None:
                raise KeyError("workforce worker not found")
            version = str(worker["current_version"])
            version_hash = str(worker["current_hash"])
            if activation_id:
                activation = conn.execute(
                    "SELECT * FROM delegation_activation_receipts WHERE id = ?",
                    (activation_id,),
                ).fetchone()
                if activation is None or activation["consumed_at"] is None:
                    raise ValueError("outcome activation receipt is missing or unconsumed")
                if str(activation["specialist_slug"]) != str(worker["agent_slug"]):
                    raise ValueError("outcome activation receipt belongs to another worker")
                version = str(activation["specialist_version"])
                version_hash = str(activation["specialist_prompt_hash"])
                for supplied, recorded, field in (
                    (session, str(activation["session_id"]), "session_id"),
                    (trace, str(activation["trace_id"]), "trace_id"),
                    (unit, str(activation["work_unit_id"]), "work_unit_id"),
                ):
                    if supplied and supplied != recorded:
                        raise ValueError(f"outcome {field} does not match activation receipt")
                session = str(activation["session_id"])
                trace = str(activation["trace_id"])
                unit = str(activation["work_unit_id"])
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
        projection = dict(row)
        projection["evidence_refs"] = _decoded(projection["evidence_refs"])
        return projection


__all__ = [
    "MAX_WORKFORCE_DOCUMENT_BYTES",
    "MAX_WORKFORCE_PAGE",
    "WorkforceStoreMixin",
    "stable_worker_id",
]
