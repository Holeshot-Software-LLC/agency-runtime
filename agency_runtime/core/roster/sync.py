"""Two-phase quarantine, approval, and activation for roster candidates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.roster.ingress import (
    _LIST_FIELDS,
    _METADATA_FIELDS,
    MAX_AGENT_CONTENT_BYTES,
    MAX_METADATA_TEXT_BYTES,
    MAX_PATH_TEXT_BYTES,
    MAX_SHORT_TEXT_BYTES,
    MAX_SNAPSHOT_MANIFEST_BYTES,
    MAX_SOURCE_CANDIDATES,
    MAX_SOURCE_FILES,
    MAX_TOTAL_SOURCE_BYTES,
    ManifestImportOutcome,
    RosterSyncError,
    _hash_text,
    _json_list,
    _load_json,
    _normalize_agent,
    _require_bounded_text,
    _utf8_size,
    categorize_agent,
    download_from_source,
    parse_agent_file,
    validate_agent,
)
from agency_runtime.core.roster.remediation import (
    RemediationAttemptReceipt,
    RosterRemediationError,
    is_registered_encoding_intermediate,
    normalize_remediation_attempt,
)
from agency_runtime.core.roster.review import (
    assert_bound_candidate_audit_from_connection,
    assert_candidate_audits_current,
    audit_candidate_in_connection,
    candidate_record_from_connection,
    candidate_remediation_evidence_from_connection,
    record_candidate_status_event,
    refresh_candidate_audit_basis_in_connection,
)
from agency_runtime.core.roster.revisions import (
    serialized_revision_metadata,
)
from agency_runtime.core.roster.semantic_projection import (
    contract_for_projected_candidate,
    contract_for_source_hash,
    verify_projected_candidate_contract,
    verify_projected_remediation,
)
from agency_runtime.core.roster.snapshot_authority import snapshot_authority_detail
from agency_runtime.core.roster.source_safety import scan_source_text
from agency_runtime.core.store.projections import project_snapshot_summary
from agency_runtime.core.store.schema import (
    BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL,
    BOUNDED_REMEDIATION_EVENT_DETAIL_SQL,
    REMEDIATION_AUTHORITY_DEPENDENCY_KINDS,
    agent_import_event_sequence_schema_is_current,
    canonical_remediation_authority_receipt,
    ensure_remediation_authority_key_integrity,
    remediation_authority_material_from_connection,
    remediation_authority_schema_is_current,
    remediation_indexes_are_current,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.workforce import (
    retire_ingested_workforce_worker,
    synchronize_active_workforce_worker,
)
from agency_runtime.core.workforce.contract import project_workforce_contract

__all__ = [
    "RosterSyncError",
    "activate_snapshot",
    "approve_snapshot",
    "categorize_agent",
    "create_retirement_diff",
    "create_roster_diff",
    "download_from_source",
    "list_remediation_queue",
    "list_source_scans",
    "parse_agent_file",
    "quarantine_candidate",
    "quarantine_manifest_import",
    "reconcile_manifest_remediation_resolutions",
    "remediation_queue_snapshot",
    "validate_agent",
]

_REMEDIATION_RESOLUTIONS = frozenset({"remediated_candidate", "superseded_by_candidate"})
_SOURCE_SCAN_RECEIPT_SCHEMA = "agency.roster.source_scan.v2"
_REMEDIATION_QUEUE_SCHEMA = "agency.roster.remediation_queue.v2"
MAX_REMEDIATION_EVENT_BYTES = 256 * 1024
MAX_REMEDIATION_RESOLUTIONS_PER_SYNC = 1_000
_BOUNDED_QUEUED_REMEDIATION_DETAIL_PREDICATE_SQL = (
    BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL.replace(
        "detail",
        "queued.detail",
    )
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _event_timestamp(value: Any, label: str) -> datetime:
    text = _require_bounded_text(value, MAX_SHORT_TEXT_BYTES, label)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RosterSyncError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise RosterSyncError(f"{label} is invalid")
    return parsed.astimezone(timezone.utc)


def _assert_scan_provenance_precedes_header(
    *,
    event_order: Any,
    event_created_at: Any,
    header_order: int,
    scan_created_at: str,
    label: str,
) -> None:
    if (
        isinstance(event_order, bool)
        or not isinstance(event_order, int)
        or event_order <= 0
        or event_order >= header_order
        or _event_timestamp(event_created_at, f"{label} timestamp")
        > _event_timestamp(scan_created_at, "source scan timestamp")
    ):
        raise RosterSyncError(f"{label} does not precede its source scan header")


def _uuid(store: Store) -> str:
    return store._uuid()


def _connect(store: Store):
    return store._connect()


def _assert_remediation_authority_available(conn: Any) -> None:
    if (
        not agent_import_event_sequence_schema_is_current(conn)
        or not remediation_indexes_are_current(conn)
        or not remediation_authority_schema_is_current(conn)
    ):
        raise RosterSyncError("remediation resolution authority schema is invalid")
    ensure_remediation_authority_key_integrity(conn, allow_initialize=False)


def _assert_bounded_import_event_types(conn: Any, event_types: Sequence[str]) -> None:
    if not event_types:
        return
    placeholders = ",".join("?" for _ in event_types)
    oversized = conn.execute(
        "SELECT id FROM agent_import_events "
        f"WHERE event_type IN ({placeholders}) "  # nosec B608
        "AND (typeof(detail) != 'text' "
        "OR length(CAST(detail AS BLOB)) > ?) LIMIT 1",
        (*event_types, MAX_REMEDIATION_EVENT_BYTES),
    ).fetchone()
    if oversized is not None:
        raise RosterSyncError("roster import event detail exceeds its integrity bound")


def _bounded_event_detail(row: Any, label: str) -> str:
    detail = row["detail"]
    if not isinstance(detail, str) or len(detail.encode("utf-8")) > MAX_REMEDIATION_EVENT_BYTES:
        raise RosterSyncError(f"{label} exceeds its integrity bound")
    return detail


def _stored_receipt_text(
    value: Any,
    maximum: int,
    label: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise RosterSyncError(f"{label} must be text")
    text = _require_bounded_text(value, maximum, label)
    if not allow_empty and not text:
        raise RosterSyncError(f"{label} must not be empty")
    return text


def _bounded_evidence_hash(value: Any, label: str) -> str:
    try:
        serialized = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RosterSyncError(f"{label} is not canonical evidence") from exc
    if _utf8_size(serialized) > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(f"{label} exceeds its integrity bound")
    return _hash_text(serialized)


def _remediation_evidence_identity(evidence: Any) -> dict[str, Any]:
    return {
        "candidate_download_id": evidence.candidate_download_id,
        "candidate_hash": evidence.candidate_hash,
        "candidate_id": evidence.candidate_id,
        "event_created_at": evidence.event_created_at,
        "event_id": evidence.event_id,
        "event_order": evidence.event_order,
        "origin": evidence.origin,
        "receipt": evidence.receipt.public_dict(),
        "relative_path": evidence.relative_path,
        "source_content_hash": _hash_text(evidence.source_content),
        "source_download_id": evidence.source_download_id,
        "source_hash": evidence.source_hash,
        "source_id": evidence.source_id,
        "source_slug": evidence.source_slug,
        "source_status": evidence.source_status,
    }


def _authority_dependency(kind: str, dependency_id: str, evidence: Any) -> dict[str, str]:
    dependency_id = _stored_receipt_text(
        dependency_id,
        MAX_PATH_TEXT_BYTES,
        f"remediation authority {kind} dependency id",
    )
    return {
        "kind": kind,
        "id": dependency_id,
        "hash": _bounded_evidence_hash(
            evidence,
            f"remediation authority {kind} dependency",
        ),
    }


def _candidate_authority_identity(candidate: Mapping[str, Any]) -> dict[str, Any]:
    identity = {
        field: candidate.get(field)
        for field in (
            "capabilities",
            "categories",
            "description",
            "division",
            "download_id",
            "hash",
            "id",
            "name",
            "prompt_path",
            "slug",
            "source",
            "source_version",
            "tool_affinity",
            "version",
        )
    }
    identity["status_valid"] = candidate.get("status") in {
        "activated",
        "approved",
        "pending",
        "rejected",
    }
    return identity


def _canonical_authority_receipt(
    dependencies: Sequence[Mapping[str, str]],
) -> tuple[str, list[dict[str, str]]]:
    by_identity: dict[tuple[str, str], dict[str, str]] = {}
    for item in dependencies:
        normalized_item = {
            "hash": item["hash"],
            "id": item["id"],
            "kind": item["kind"],
        }
        identity = (normalized_item["kind"], normalized_item["id"])
        prior = by_identity.get(identity)
        if prior is not None and prior != normalized_item:
            raise RosterSyncError("remediation authority contains conflicting dependencies")
        by_identity[identity] = normalized_item
    normalized = sorted(by_identity.values(), key=lambda item: (item["kind"], item["id"]))
    transformation_count = sum(item["kind"] == "transformation_event" for item in normalized)
    expected_counts = {
        "candidate": 1,
        "candidate_audit": 1,
        "candidate_download": 1,
        "candidate_slug": transformation_count,
        "queue_event": 1,
        "queue_download": 1,
        "queue_source_scan": 1,
        "resolution_event": 1,
        "source": 1,
        "source_download": transformation_count,
        "candidate_source_scan": 1,
        "transformation_event": transformation_count,
    }
    observed_counts = {
        kind: sum(item["kind"] == kind for item in normalized) for kind in expected_counts
    }
    if (
        len(normalized) > 12
        or transformation_count > 1
        or any(item["kind"] not in REMEDIATION_AUTHORITY_DEPENDENCY_KINDS for item in normalized)
        or observed_counts != expected_counts
        or any(re.fullmatch(r"[a-f0-9]{64}", item["hash"]) is None for item in normalized)
    ):
        raise RosterSyncError("remediation authority dependency closure is invalid")
    try:
        receipt = canonical_remediation_authority_receipt(normalized)
    except ValueError as exc:
        raise RosterSyncError("remediation authority dependency closure is invalid") from exc
    if _utf8_size(receipt) > MAX_REMEDIATION_EVENT_BYTES:
        raise RosterSyncError("remediation authority evidence receipt exceeds its bound")
    return receipt, normalized


def quarantine_candidate(
    agent: dict[str, Any],
    source_id: str,
    store: Store,
    *,
    require_inference: bool = False,
) -> str:
    """Write a validated candidate and its raw download record to quarantine."""

    normalized = _normalize_agent(agent)
    ok, reason = validate_agent(normalized)
    if not ok:
        raise ValueError(f"invalid agent {normalized.get('slug') or '<missing>'}: {reason}")
    source_id = _require_bounded_text(source_id, MAX_SHORT_TEXT_BYTES, "source id")

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        source = conn.execute(
            "SELECT enabled FROM agent_sources WHERE id = ?", (source_id,)
        ).fetchone()
        if source is None:
            raise RosterSyncError("cannot quarantine a candidate for an unknown source")
        if not int(source["enabled"] or 0):
            raise RosterSyncError("cannot quarantine a candidate for a disabled source")
        download_id = _uuid(store)
        candidate_id = _uuid(store)
        now = _now()
        content = normalized.get("content") or normalized.get("prompt_body", "")
        conn.execute(
            "INSERT INTO agent_downloads (id, source_id, slug, downloaded_at, hash, content, status) VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
            (
                download_id,
                source_id,
                normalized["slug"],
                now,
                normalized["hash"],
                content,
            ),
        )
        conn.execute(
            "INSERT INTO agent_candidates (id, download_id, slug, name, description, division, categories, capabilities, tool_affinity, prompt_path, source, source_version, version, hash, status, quarantined_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (
                candidate_id,
                download_id,
                normalized["slug"],
                normalized.get("name", ""),
                normalized.get("description", ""),
                normalized.get("division", ""),
                json.dumps(normalized.get("categories", [])),
                json.dumps(normalized.get("capabilities", [])),
                json.dumps(normalized.get("tool_affinity", [])),
                normalized.get("prompt_path", ""),
                normalized.get("source", ""),
                normalized.get("source_version", "1.0.0"),
                normalized["version"],
                normalized["hash"],
                now,
            ),
        )
        _record_import_event(
            conn,
            store,
            "candidate_quarantined",
            normalized["slug"],
            f"candidate_id={candidate_id}",
            now=now,
        )
        record_candidate_status_event(
            conn,
            store,
            candidate_id,
            event_type="quarantined",
            from_status="",
            to_status="pending",
            reason="bounded_ingress_passed",
            created_at=now,
        )
        audit_candidate_in_connection(
            conn,
            store,
            candidate_id,
            require_inference=require_inference,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return candidate_id


def _record_import_event(
    conn: Any,
    store: Store,
    event_type: str,
    agent_slug: str,
    detail: str,
    *,
    now: str | None = None,
) -> str:
    event_id = _uuid(store)
    conn.execute(
        "INSERT INTO agent_import_events "
        "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
        (event_id, event_type, agent_slug, detail, now or _now()),
    )
    return event_id


def _normalized_manifest_agents(
    agents: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str], int]:
    if len(agents) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(
            f"manifest import contains more than {MAX_SOURCE_CANDIDATES} candidates"
        )
    normalized_agents: list[dict[str, Any]] = []
    slugs: set[str] = set()
    content_bytes = 0
    for agent in agents:
        normalized = _normalize_agent(agent)
        ok, reason = validate_agent(normalized)
        if not ok:
            raise RosterSyncError(
                f"invalid manifest candidate {normalized.get('slug') or '<missing>'}: {reason}"
            )
        if normalized["slug"] in slugs:
            raise RosterSyncError(
                f"manifest import contains duplicate agent slug {normalized['slug']}"
            )
        slugs.add(normalized["slug"])
        content_bytes += _utf8_size(normalized["content"])
        normalized_agents.append(normalized)
    return normalized_agents, slugs, content_bytes


def _validate_candidate_remediation(
    outcome: ManifestImportOutcome,
    candidate: Mapping[str, Any],
) -> int:
    if outcome.remediation is None:
        if outcome.source_content:
            raise RosterSyncError(
                "unremediated manifest candidate carries unexpected source content"
            )
        return 0
    if not outcome.source_content:
        raise RosterSyncError("remediated manifest candidate is missing original source content")
    if _hash_text(outcome.source_content) != outcome.content_hash:
        raise RosterSyncError("remediated manifest source content hash does not match")
    try:
        receipt = verify_projected_remediation(
            outcome.source_content,
            str(candidate.get("content") or ""),
            outcome.remediation,
            relative_path=outcome.relative_path,
        )
        verify_projected_candidate_contract(
            candidate,
            source_hash=outcome.content_hash,
            relative_path=outcome.relative_path,
        )
    except RosterRemediationError as exc:
        raise RosterSyncError("remediated manifest candidate evidence is invalid") from exc
    if candidate.get("prompt_path") != outcome.origin:
        raise RosterSyncError("remediated manifest candidate origin does not match")
    if (
        receipt.original_hash != outcome.content_hash
        or receipt.transformed_hash != candidate.get("hash")
        or candidate.get("source_content_hash") != outcome.content_hash
    ):
        raise RosterSyncError("remediated manifest candidate identity does not match its receipt")
    return _utf8_size(outcome.source_content)


def _validate_manifest_outcome(
    outcome: ManifestImportOutcome,
    *,
    candidates_by_slug: Mapping[str, Mapping[str, Any]],
    candidate_outcome_slugs: set[str],
    quarantined_entries: set[tuple[str, str, str]],
) -> int:
    if not isinstance(outcome, ManifestImportOutcome):
        raise RosterSyncError("manifest import outcome has an invalid type")
    if outcome.status not in {"candidate", "ignored", "quarantined"}:
        raise RosterSyncError(f"manifest import outcome has invalid status {outcome.status!r}")
    relative_path = _require_bounded_text(
        outcome.relative_path,
        MAX_PATH_TEXT_BYTES,
        "manifest outcome relative path",
    )
    if (
        not relative_path
        or relative_path.startswith("/")
        or "\\" in relative_path
        or ".." in relative_path.split("/")
    ):
        raise RosterSyncError("manifest outcome has an unsafe relative path")
    _require_bounded_text(outcome.origin, MAX_PATH_TEXT_BYTES, "manifest outcome origin")
    _require_bounded_text(
        outcome.finding,
        MAX_METADATA_TEXT_BYTES,
        "manifest outcome finding",
    )
    _require_bounded_text(outcome.slug, MAX_SHORT_TEXT_BYTES, "manifest outcome slug")
    if not re.fullmatch(r"[a-f0-9]{64}", outcome.content_hash):
        raise RosterSyncError("manifest outcome hash is invalid")
    if outcome.status == "candidate":
        if outcome.remediation_attempt is not None:
            raise RosterSyncError("manifest candidate outcome carries a remediation attempt")
        candidate = candidates_by_slug.get(outcome.slug)
        if candidate is None or outcome.content:
            raise RosterSyncError("manifest candidate outcome does not match its candidate")
        candidate_outcome_slugs.add(outcome.slug)
        return _validate_candidate_remediation(outcome, candidate)
    if outcome.status == "ignored":
        if (
            outcome.content
            or outcome.source_content
            or outcome.remediation is not None
            or outcome.remediation_attempt is not None
        ):
            raise RosterSyncError("ignored manifest outcomes may not carry source content")
        return 0
    if outcome.source_content or outcome.remediation is not None:
        raise RosterSyncError("quarantined manifest outcome carries remediation evidence")
    try:
        attempt = normalize_remediation_attempt(outcome.remediation_attempt)
    except RosterRemediationError as exc:
        raise RosterSyncError("quarantined manifest remediation attempt is invalid") from exc
    if attempt.original_hash != outcome.content_hash or attempt.finding != outcome.finding:
        raise RosterSyncError("quarantined manifest remediation attempt is not source-bound")
    if _hash_text(outcome.content) != outcome.content_hash:
        raise RosterSyncError("quarantined manifest entry content hash does not match")
    identity = (relative_path, outcome.slug, outcome.content_hash)
    if identity in quarantined_entries:
        raise RosterSyncError("manifest import contains duplicate quarantined outcomes")
    quarantined_entries.add(identity)
    return _utf8_size(outcome.content)


def _validated_manifest_batch(
    agents: Sequence[dict[str, Any]],
    outcomes: Sequence[ManifestImportOutcome],
) -> tuple[list[dict[str, Any]], list[ManifestImportOutcome]]:
    normalized_agents, slugs, content_bytes = _normalized_manifest_agents(agents)
    if len(outcomes) > MAX_SOURCE_CANDIDATES + MAX_SOURCE_FILES:
        raise RosterSyncError("manifest import contains too many entry outcomes")

    candidate_outcome_slugs: set[str] = set()
    quarantined_entries: set[tuple[str, str, str]] = set()
    relative_paths: set[str] = set()
    validated_outcomes: list[ManifestImportOutcome] = []
    for outcome in outcomes:
        if outcome.relative_path in relative_paths:
            raise RosterSyncError(
                f"manifest import contains duplicate relative path {outcome.relative_path!r}"
            )
        relative_paths.add(outcome.relative_path)
        content_bytes += _validate_manifest_outcome(
            outcome,
            candidates_by_slug={agent["slug"]: agent for agent in normalized_agents},
            candidate_outcome_slugs=candidate_outcome_slugs,
            quarantined_entries=quarantined_entries,
        )
        validated_outcomes.append(outcome)
    if candidate_outcome_slugs != slugs:
        raise RosterSyncError("manifest candidates and entry outcomes do not match")
    if content_bytes > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(
            f"manifest import content is {content_bytes} bytes; "
            f"limit is {MAX_TOTAL_SOURCE_BYTES} bytes"
        )
    return normalized_agents, validated_outcomes


def _existing_manifest_candidate(
    conn: Any,
    source_id: str,
    agent: Mapping[str, Any],
    content: str,
) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT c.id, c.download_id FROM agent_candidates c "
        "JOIN agent_downloads d ON d.id = c.download_id "
        "WHERE d.source_id = ? AND c.slug = ? AND c.hash = ? "
        "AND d.hash = ? AND d.content = ? AND c.prompt_path = ? "
        "AND c.source = ? AND c.description = ? AND c.division = ? "
        "AND c.source_version = ? AND c.version = ? "
        "AND c.status IN ('pending', 'approved') "
        "ORDER BY c.quarantined_at DESC LIMIT 1",
        (
            source_id,
            agent["slug"],
            agent["hash"],
            agent["hash"],
            content,
            agent.get("prompt_path", ""),
            agent.get("source", ""),
            agent.get("description", ""),
            agent.get("division", ""),
            agent.get("source_version", "1.0.0"),
            agent["version"],
        ),
    ).fetchone()
    if row is None:
        return None
    return str(row["id"]), str(row["download_id"])


def _insert_manifest_candidate(
    conn: Any,
    store: Store,
    source_id: str,
    agent: Mapping[str, Any],
    *,
    now: str,
) -> tuple[tuple[str, str], bool]:
    content = str(agent.get("content") or agent.get("prompt_body") or "")
    existing = _existing_manifest_candidate(conn, source_id, agent, content)
    if existing is not None:
        return existing, False
    download_id = _uuid(store)
    candidate_id = _uuid(store)
    conn.execute(
        "INSERT INTO agent_downloads "
        "(id, source_id, slug, downloaded_at, hash, content, status) "
        "VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
        (
            download_id,
            source_id,
            agent["slug"],
            now,
            agent["hash"],
            content,
        ),
    )
    conn.execute(
        "INSERT INTO agent_candidates "
        "(id, download_id, slug, name, description, division, categories, capabilities, "
        "tool_affinity, prompt_path, source, source_version, version, hash, status, quarantined_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
        (
            candidate_id,
            download_id,
            agent["slug"],
            agent.get("name", ""),
            agent.get("description", ""),
            agent.get("division", ""),
            json.dumps(agent.get("categories", [])),
            json.dumps(agent.get("capabilities", [])),
            json.dumps(agent.get("tool_affinity", [])),
            agent.get("prompt_path", ""),
            agent.get("source", ""),
            agent.get("source_version", "1.0.0"),
            agent["version"],
            agent["hash"],
            now,
        ),
    )
    _record_import_event(
        conn,
        store,
        "candidate_quarantined",
        str(agent["slug"]),
        f"candidate_id={candidate_id}",
        now=now,
    )
    record_candidate_status_event(
        conn,
        store,
        candidate_id,
        event_type="quarantined",
        from_status="",
        to_status="pending",
        reason="manifest_ingress_passed",
        created_at=now,
    )
    return (candidate_id, download_id), True


def _persist_rejected_manifest_entry(
    conn: Any,
    store: Store,
    source_id: str,
    outcome: ManifestImportOutcome,
    *,
    scan_id: str,
    now: str,
) -> str:
    try:
        attempt = normalize_remediation_attempt(outcome.remediation_attempt)
    except RosterRemediationError as exc:
        raise RosterSyncError("manifest remediation queue receipt is invalid") from exc
    identity = json.dumps(
        {
            "finding": outcome.finding,
            "hash": outcome.content_hash,
            "relative_path": outcome.relative_path,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    download_id = f"manifest-reject-{_hash_text(identity)}"
    detail = json.dumps(
        {
            "download_id": download_id,
            "finding": outcome.finding,
            "hash": outcome.content_hash,
            "relative_path": outcome.relative_path,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    queue_detail = json.dumps(
        {
            "binding_hash": _hash_text(
                json.dumps(
                    {
                        "hash": outcome.content_hash,
                        "origin": outcome.origin,
                        "relative_path": outcome.relative_path,
                        "scan_id": scan_id,
                        "source_id": source_id,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
            ),
            "download_id": download_id,
            "origin": outcome.origin,
            "receipt": attempt.public_dict(),
            "relative_path": outcome.relative_path,
            "scan_id": scan_id,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    row = conn.execute(
        "SELECT d.id FROM agent_downloads d "
        "LEFT JOIN agent_candidates c ON c.download_id = d.id "
        "WHERE d.id = ? AND d.source_id = ? AND d.slug = ? AND d.hash = ? "
        "AND d.content = ? AND d.status = 'quarantined' AND c.id IS NULL",
        (
            download_id,
            source_id,
            outcome.slug,
            outcome.content_hash,
            outcome.content,
        ),
    ).fetchone()
    event = conn.execute(
        "SELECT id FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_quarantined' "
        "AND agent_slug = ? AND detail = ? LIMIT 1",
        (outcome.slug, detail),
    ).fetchone()
    queue_event = conn.execute(
        "SELECT id FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediation_queued' "
        "AND agent_slug = ? AND detail = ? LIMIT 1",
        (outcome.slug, queue_detail),
    ).fetchone()
    if queue_event is not None and (row is None or event is None):
        raise RosterSyncError("manifest quarantine evidence is incomplete or tampered")
    if row is not None or event is not None:
        if row is None or event is None:
            raise RosterSyncError("manifest quarantine evidence is incomplete or tampered")
    else:
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
            (
                download_id,
                source_id,
                outcome.slug,
                now,
                outcome.content_hash,
                outcome.content,
            ),
        )
        _record_import_event(
            conn,
            store,
            "manifest_entry_quarantined",
            outcome.slug,
            detail,
            now=now,
        )
    if queue_event is None:
        recorded_scan = conn.execute(
            "SELECT 1 FROM agent_source_scans WHERE id = ?",
            (scan_id,),
        ).fetchone()
        if recorded_scan is not None:
            raise RosterSyncError("manifest quarantine evidence is incomplete or tampered")
        _record_import_event(
            conn,
            store,
            "manifest_entry_remediation_queued",
            outcome.slug,
            queue_detail,
            now=now,
        )
    return download_id


def _persist_remediated_manifest_source(
    conn: Any,
    store: Store,
    source_id: str,
    outcome: ManifestImportOutcome,
    *,
    candidate_id: str,
    candidate_download_id: str,
    candidate_is_new: bool,
    now: str,
) -> str:
    """Preserve exact pre-repair bytes and a hash-chained transformation receipt."""

    if outcome.remediation is None:
        raise RosterSyncError("remediated manifest source is missing its receipt")
    receipt = outcome.remediation.public_dict()
    identity = json.dumps(
        {
            "hash": outcome.content_hash,
            "relative_path": outcome.relative_path,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    source_download_id = f"manifest-remediation-source-{_hash_text(identity)}"
    detail = json.dumps(
        {
            "candidate_download_id": candidate_download_id,
            "candidate_id": candidate_id,
            "origin": outcome.origin,
            "receipt": receipt,
            "relative_path": outcome.relative_path,
            "source_download_id": source_download_id,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    row = conn.execute(
        "SELECT d.id FROM agent_downloads d "
        "LEFT JOIN agent_candidates c ON c.download_id = d.id "
        "WHERE d.id = ? AND d.source_id = ? AND d.slug = ? AND d.hash = ? "
        "AND d.content = ? AND d.status = 'quarantined' AND c.id IS NULL",
        (
            source_download_id,
            source_id,
            outcome.slug,
            outcome.content_hash,
            outcome.source_content,
        ),
    ).fetchone()
    event = conn.execute(
        "SELECT id FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediated' "
        "AND agent_slug = ? AND detail = ? LIMIT 1",
        (outcome.slug, detail),
    ).fetchone()
    if row is not None or event is not None:
        if row is None:
            raise RosterSyncError("manifest remediation evidence is incomplete or tampered")
        if event is not None:
            return str(row["id"])
        if not candidate_is_new:
            raise RosterSyncError("manifest remediation evidence is incomplete or tampered")
    else:
        conn.execute(
            "INSERT INTO agent_downloads "
            "(id, source_id, slug, downloaded_at, hash, content, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'quarantined')",
            (
                source_download_id,
                source_id,
                outcome.slug,
                now,
                outcome.content_hash,
                outcome.source_content,
            ),
        )
    _record_import_event(
        conn,
        store,
        "manifest_entry_remediated",
        outcome.slug,
        detail,
        now=now,
    )
    return source_download_id


def _record_ignored_manifest_entry(
    conn: Any,
    store: Store,
    source_id: str,
    outcome: ManifestImportOutcome,
    *,
    scan_id: str,
    now: str,
) -> None:
    detail = json.dumps(
        {
            "finding": outcome.finding,
            "hash": outcome.content_hash,
            "origin": outcome.origin,
            "relative_path": outcome.relative_path,
            "scan_id": scan_id,
            "source_id": source_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    row = conn.execute(
        "SELECT id FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_ignored' AND agent_slug = '' AND detail = ? "
        "LIMIT 1",
        (detail,),
    ).fetchone()
    if row is None:
        _record_import_event(
            conn,
            store,
            "manifest_entry_ignored",
            "",
            detail,
            now=now,
        )


def _source_scan_manifest_rows(
    outcomes: Sequence[ManifestImportOutcome],
) -> list[dict[str, str]]:
    return sorted(
        (
            {
                "hash": outcome.content_hash,
                "origin_hash": _hash_text(outcome.origin),
                "relative_path": outcome.relative_path,
                "slug": outcome.slug,
                "status": outcome.status,
            }
            for outcome in outcomes
        ),
        key=lambda item: item["relative_path"],
    )


def _source_scan_manifest_hash(rows: Sequence[Mapping[str, str]]) -> str:
    return _hash_text(json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _prepared_source_scan_id(
    conn: Any,
    store: Store,
    source_id: str,
    outcomes: Sequence[ManifestImportOutcome],
) -> str:
    """Reuse only the latest identical receipt; otherwise allocate a fresh scan."""

    manifest_hash = _source_scan_manifest_hash(_source_scan_manifest_rows(outcomes))
    latest = conn.execute(
        "SELECT id, manifest_hash FROM agent_source_scans WHERE source_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    if latest is not None and str(latest["manifest_hash"]) == manifest_hash:
        return str(latest["id"])
    return f"scan-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}-{_uuid(store)}"


def _record_source_scan(
    conn: Any,
    store: Store,
    source_id: str,
    outcomes: Sequence[ManifestImportOutcome],
    candidate_records: Mapping[str, tuple[str, str]],
    *,
    scan_id: str,
    now: str,
) -> str:
    """Persist one immutable scan receipt; quarantines make it non-authoritative."""

    rows = _source_scan_manifest_rows(outcomes)
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in ("candidate", "quarantined", "ignored")
    }
    status = "partial" if not rows or counts["quarantined"] else "complete"
    manifest_hash = _source_scan_manifest_hash(rows)
    existing = conn.execute(
        "SELECT id FROM agent_source_scans WHERE id = ?",
        (scan_id,),
    ).fetchone()
    if existing is not None:
        _validated_source_scan(
            conn,
            scan_id,
            require_latest=True,
            require_enabled=True,
        )
        return scan_id
    conn.execute(
        "INSERT INTO agent_source_scans "
        "(id, source_id, status, manifest_hash, entry_count, candidate_count, "
        "quarantined_count, ignored_count, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            scan_id,
            source_id,
            status,
            manifest_hash,
            len(rows),
            counts["candidate"],
            counts["quarantined"],
            counts["ignored"],
            now,
        ),
    )
    for row in rows:
        candidate_id = candidate_records[row["slug"]][0] if row["status"] == "candidate" else None
        conn.execute(
            "INSERT INTO agent_source_scan_entries "
            "(id, scan_id, relative_path, slug, content_hash, status, candidate_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid(store),
                scan_id,
                row["relative_path"],
                row["slug"],
                row["hash"],
                row["status"],
                candidate_id,
            ),
        )
    _record_import_event(
        conn,
        store,
        "source_scan_recorded",
        "",
        json.dumps(
            {
                "manifest_hash": manifest_hash,
                "receipt_schema": _SOURCE_SCAN_RECEIPT_SCHEMA,
                "scan_id": scan_id,
                "source_id": source_id,
                "status": status,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        now=now,
    )
    return scan_id


def _candidate_scan_origin(
    conn: Any,
    scan: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    scan_id: str,
    relative_path: str,
    content_hash: str,
    header_order: int,
    scan_created_at: str,
) -> tuple[str, str, list[dict[str, str]]]:
    try:
        candidate = candidate_record_from_connection(
            conn,
            str(entry.get("candidate_id") or ""),
        )
    except (KeyError, RosterSyncError) as exc:
        raise RosterSyncError(f"source scan {scan_id} candidate provenance is invalid") from exc
    if str(candidate["source_id"]) != str(scan["source_id"]) or str(candidate["slug"]) != str(
        entry.get("slug") or ""
    ):
        raise RosterSyncError(f"source scan {scan_id} candidate provenance is invalid")
    remediation_identity: dict[str, Any] | None = None
    dependencies: list[dict[str, str]] = []
    if str(candidate["hash"]) != content_hash:
        evidence = candidate_remediation_evidence_from_connection(conn, candidate)
        if (
            evidence is None
            or evidence.source_hash != content_hash
            or evidence.relative_path != relative_path
        ):
            raise RosterSyncError(f"source scan {scan_id} candidate provenance is invalid")
        _assert_scan_provenance_precedes_header(
            event_order=evidence.event_order,
            event_created_at=evidence.event_created_at,
            header_order=header_order,
            scan_created_at=scan_created_at,
            label=f"source scan {scan_id} candidate transformation",
        )
        remediation_identity = _remediation_evidence_identity(evidence)
        dependencies.extend(
            (
                _authority_dependency(
                    "transformation_event",
                    evidence.event_id,
                    remediation_identity,
                ),
                _authority_dependency(
                    "source_download",
                    evidence.source_download_id,
                    {
                        "content": evidence.source_content,
                        "hash": evidence.source_hash,
                        "id": evidence.source_download_id,
                        "slug": evidence.source_slug,
                        "source_id": evidence.source_id,
                        "status": evidence.source_status,
                    },
                ),
                _authority_dependency(
                    "candidate_slug",
                    str(candidate["slug"]),
                    {
                        "event_ids": [evidence.event_id],
                        "slug": str(candidate["slug"]),
                    },
                ),
            )
        )
    origin = _stored_receipt_text(
        candidate["prompt_path"],
        MAX_PATH_TEXT_BYTES,
        f"source scan {scan_id} candidate origin",
    )
    return (
        origin,
        _bounded_evidence_hash(
            {
                "candidate": _candidate_authority_identity(candidate),
                "candidate_download": {
                    "content": candidate["content"],
                    "hash": candidate["download_hash"],
                    "id": candidate["download_id"],
                    "slug": candidate["slug"],
                    "source_id": candidate["source_id"],
                },
                "remediation": remediation_identity,
            },
            f"source scan {scan_id} candidate provenance",
        ),
        dependencies,
    )


def _quarantined_scan_origin(
    conn: Any,
    scan: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    scan_id: str,
    relative_path: str,
    content_hash: str,
    header_order: int,
    scan_created_at: str,
) -> tuple[str, str, list[dict[str, str]]]:
    queued_rows = conn.execute(
        "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
        "FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_remediation_queued' "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id') = ? "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
        "'$.relative_path') = ? LIMIT 2",  # nosec B608
        (scan_id, relative_path),
    ).fetchall()
    if len(queued_rows) != 1:
        raise RosterSyncError(f"source scan {scan_id} quarantine provenance is invalid")
    queued = _validated_remediation_queue_item_base(conn, queued_rows[0])
    if (
        queued["source_id"] != str(scan["source_id"])
        or queued["slug"] != str(entry.get("slug") or "")
        or queued["relative_path"] != relative_path
        or queued["receipt"]["original_hash"] != content_hash
    ):
        raise RosterSyncError(f"source scan {scan_id} quarantine provenance is invalid")
    _assert_scan_provenance_precedes_header(
        event_order=queued["_event_order"],
        event_created_at=queued["created_at"],
        header_order=header_order,
        scan_created_at=scan_created_at,
        label=f"source scan {scan_id} quarantine provenance",
    )
    return (
        str(queued["origin"]),
        _bounded_evidence_hash(
            {
                "created_at": queued["created_at"],
                "download_id": queued["download_id"],
                "event_id": queued["event_id"],
                "origin": queued["origin"],
                "receipt": queued["receipt"],
                "relative_path": queued["relative_path"],
                "scan_id": queued["scan_id"],
                "slug": queued["slug"],
                "source_content_hash": _hash_text(queued["_source_content"]),
                "source_id": queued["source_id"],
            },
            f"source scan {scan_id} quarantine provenance",
        ),
        [],
    )


def _ignored_scan_origin(
    conn: Any,
    scan: Mapping[str, Any],
    *,
    scan_id: str,
    relative_path: str,
    content_hash: str,
    header_order: int,
    scan_created_at: str,
) -> tuple[str, str, list[dict[str, str]]]:
    ignored_rows = conn.execute(
        "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
        "FROM agent_import_events "
        "WHERE event_type = 'manifest_entry_ignored' "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, '$.scan_id') = ? "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
        "'$.relative_path') = ? LIMIT 2",  # nosec B608
        (scan_id, relative_path),
    ).fetchall()
    if len(ignored_rows) != 1:
        raise RosterSyncError(f"source scan {scan_id} ignored provenance is invalid")
    ignored = _load_json(
        _bounded_event_detail(
            ignored_rows[0],
            f"source scan {scan_id} ignored provenance",
        ),
        f"source scan {scan_id} ignored provenance",
    )
    if not isinstance(ignored, dict) or set(ignored) != {
        "finding",
        "hash",
        "origin",
        "relative_path",
        "scan_id",
        "source_id",
    }:
        raise RosterSyncError(f"source scan {scan_id} ignored provenance is invalid")
    origin = _stored_receipt_text(
        ignored["origin"],
        MAX_PATH_TEXT_BYTES,
        f"source scan {scan_id} ignored origin",
    )
    finding = _stored_receipt_text(
        ignored["finding"],
        MAX_METADATA_TEXT_BYTES,
        f"source scan {scan_id} ignored finding",
    )
    ignored_hash = _stored_receipt_text(
        ignored["hash"],
        64,
        f"source scan {scan_id} ignored hash",
    )
    ignored_relative_path = _stored_receipt_text(
        ignored["relative_path"],
        MAX_PATH_TEXT_BYTES,
        f"source scan {scan_id} ignored relative path",
    )
    ignored_scan_id = _stored_receipt_text(
        ignored["scan_id"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} ignored scan id",
    )
    ignored_source_id = _stored_receipt_text(
        ignored["source_id"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} ignored source id",
    )
    event_slug = _stored_receipt_text(
        ignored_rows[0]["agent_slug"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} ignored agent slug",
        allow_empty=True,
    )
    event_created_at = _stored_receipt_text(
        ignored_rows[0]["created_at"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} ignored timestamp",
    )
    if (
        event_slug
        or event_created_at != scan["created_at"]
        or ignored_scan_id != scan_id
        or ignored_source_id != scan["source_id"]
        or ignored_relative_path != relative_path
        or ignored_hash != content_hash
        or not finding
    ):
        raise RosterSyncError(f"source scan {scan_id} ignored provenance is invalid")
    _assert_scan_provenance_precedes_header(
        event_order=ignored_rows[0]["event_order"],
        event_created_at=event_created_at,
        header_order=header_order,
        scan_created_at=scan_created_at,
        label=f"source scan {scan_id} ignored provenance",
    )
    return (
        origin,
        _bounded_evidence_hash(
            {
                "created_at": event_created_at,
                "detail": ignored,
                "event_id": ignored_rows[0]["id"],
                "event_slug": event_slug,
            },
            f"source scan {scan_id} ignored provenance",
        ),
        [],
    )


def _source_scan_entry_origin(
    conn: Any,
    scan: Mapping[str, Any],
    entry: Mapping[str, Any],
    *,
    scan_id: str,
    status: str,
    relative_path: str,
    content_hash: str,
    header_order: int,
    scan_created_at: str,
) -> tuple[str, str, list[dict[str, str]]]:
    if status == "candidate":
        return _candidate_scan_origin(
            conn,
            scan,
            entry,
            scan_id=scan_id,
            relative_path=relative_path,
            content_hash=content_hash,
            header_order=header_order,
            scan_created_at=scan_created_at,
        )
    if status == "quarantined":
        return _quarantined_scan_origin(
            conn,
            scan,
            entry,
            scan_id=scan_id,
            relative_path=relative_path,
            content_hash=content_hash,
            header_order=header_order,
            scan_created_at=scan_created_at,
        )
    return _ignored_scan_origin(
        conn,
        scan,
        scan_id=scan_id,
        relative_path=relative_path,
        content_hash=content_hash,
        header_order=header_order,
        scan_created_at=scan_created_at,
    )


def _validated_source_scan_header(
    conn: Any,
    scan: Mapping[str, Any],
    *,
    scan_id: str,
    expected_status: str,
) -> Any:
    header_rows = conn.execute(
        "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
        "FROM agent_import_events WHERE event_type = 'source_scan_recorded' "
        f"AND json_extract({BOUNDED_REMEDIATION_EVENT_DETAIL_SQL}, "
        "'$.scan_id') = ? LIMIT 2",  # nosec B608
        (scan_id,),
    ).fetchall()
    if len(header_rows) != 1:
        raise RosterSyncError(f"source scan {scan_id} receipt header is invalid")
    header_row = header_rows[0]
    header = _load_json(
        _bounded_event_detail(header_row, f"source scan {scan_id} receipt header"),
        f"source scan {scan_id} receipt header",
    )
    if not isinstance(header, dict) or set(header) != {
        "manifest_hash",
        "receipt_schema",
        "scan_id",
        "source_id",
        "status",
    }:
        raise RosterSyncError(f"source scan {scan_id} receipt header is invalid")
    manifest_hash = _stored_receipt_text(
        header["manifest_hash"],
        64,
        f"source scan {scan_id} header manifest hash",
    )
    receipt_schema = _stored_receipt_text(
        header["receipt_schema"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header receipt schema",
    )
    header_scan_id = _stored_receipt_text(
        header["scan_id"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header scan id",
    )
    source_id = _stored_receipt_text(
        header["source_id"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header source id",
    )
    status = _stored_receipt_text(
        header["status"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header status",
    )
    agent_slug = _stored_receipt_text(
        header_row["agent_slug"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header agent slug",
        allow_empty=True,
    )
    created_at = _stored_receipt_text(
        header_row["created_at"],
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} header timestamp",
    )
    if (
        agent_slug
        or created_at != scan["created_at"]
        or receipt_schema != _SOURCE_SCAN_RECEIPT_SCHEMA
        or header_scan_id != scan_id
        or source_id != scan["source_id"]
        or status != expected_status
        or manifest_hash != scan["manifest_hash"]
    ):
        raise RosterSyncError(f"source scan {scan_id} receipt header is invalid")
    return header_row


def _source_scan_structural_evidence(
    scan: Mapping[str, Any],
    header_row: Any,
    *,
    scan_id: str,
) -> dict[str, Any]:
    """Return the scan commitment shared by full and entry-local validation."""

    header_order = header_row["event_order"]
    if isinstance(header_order, bool) or not isinstance(header_order, int) or header_order <= 0:
        raise RosterSyncError(f"source scan {scan_id} receipt header order is invalid")
    return {
        "header": {
            "agent_slug": header_row["agent_slug"],
            "created_at": header_row["created_at"],
            "detail": _bounded_event_detail(
                header_row,
                f"source scan {scan_id} receipt header",
            ),
            "event_id": header_row["id"],
            "event_order": header_order,
        },
        "scan": {
            field: scan[field]
            for field in (
                "candidate_count",
                "created_at",
                "entry_count",
                "id",
                "ignored_count",
                "manifest_hash",
                "quarantined_count",
                "source_id",
                "status",
            )
        },
    }


def _source_scan_entry_authority_evidence(
    entry: Mapping[str, Any],
    *,
    origin: str,
    provenance_hash: str,
) -> dict[str, Any]:
    """Return the selected-entry commitment carried by a scan authority edge."""

    return {
        "entry": {
            field: entry.get(field)
            for field in (
                "candidate_id",
                "content_hash",
                "relative_path",
                "slug",
                "status",
            )
        },
        "origin_hash": _hash_text(origin),
        "provenance_hash": provenance_hash,
    }


def _validated_source_scan_declaration(
    scan: Mapping[str, Any],
    *,
    scan_id: str,
) -> tuple[dict[str, int], str]:
    counts: dict[str, int] = {}
    for field in ("entry_count", "candidate_count", "quarantined_count", "ignored_count"):
        value = scan.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= MAX_SOURCE_FILES
        ):
            raise RosterSyncError(f"source scan {scan_id} counts are invalid")
        counts[field] = value
    expected_status = (
        "partial" if not counts["entry_count"] or counts["quarantined_count"] else "complete"
    )
    if (
        counts["candidate_count"] + counts["quarantined_count"] + counts["ignored_count"]
        != counts["entry_count"]
        or scan["status"] != expected_status
    ):
        raise RosterSyncError(f"source scan {scan_id} counts are invalid")
    return counts, expected_status


def _validated_source_scan(
    conn: Any,
    scan_id: str,
    *,
    require_latest: bool,
    require_enabled: bool = True,
) -> dict[str, Any]:
    scan_id = _require_bounded_text(scan_id, MAX_SHORT_TEXT_BYTES, "source scan id")
    row = conn.execute(
        "SELECT scan.*, source.enabled AS source_enabled FROM agent_source_scans AS scan "
        "JOIN agent_sources AS source ON source.id = scan.source_id WHERE scan.id = ?",
        (scan_id,),
    ).fetchone()
    if row is None:
        raise RosterSyncError(f"source scan not found: {scan_id}")
    scan = dict(row)
    stored_scan_id = _stored_receipt_text(
        scan.get("id"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} stored id",
    )
    source_id = _stored_receipt_text(
        scan.get("source_id"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} source id",
    )
    stored_status = _stored_receipt_text(
        scan.get("status"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} status",
    )
    manifest_hash = _stored_receipt_text(
        scan.get("manifest_hash"),
        64,
        f"source scan {scan_id} manifest hash",
    )
    created_at = _stored_receipt_text(
        scan.get("created_at"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} timestamp",
    )
    if stored_scan_id != scan_id or not re.fullmatch(r"[a-f0-9]{64}", manifest_hash):
        raise RosterSyncError(f"source scan {scan_id} identity is invalid")
    scan.update(
        {
            "id": stored_scan_id,
            "source_id": source_id,
            "status": stored_status,
            "manifest_hash": manifest_hash,
            "created_at": created_at,
        }
    )
    declared_counts, expected_status = _validated_source_scan_declaration(
        scan,
        scan_id=scan_id,
    )
    header_row = _validated_source_scan_header(
        conn,
        scan,
        scan_id=scan_id,
        expected_status=expected_status,
    )
    header_order = header_row["event_order"]
    if isinstance(header_order, bool) or not isinstance(header_order, int) or header_order <= 0:
        raise RosterSyncError(f"source scan {scan_id} receipt header order is invalid")
    entries = [
        dict(item)
        for item in conn.execute(
            "SELECT relative_path, slug, content_hash, status, candidate_id "
            "FROM agent_source_scan_entries WHERE scan_id = ? ORDER BY relative_path "
            "LIMIT ?",
            (scan_id, MAX_SOURCE_FILES + 1),
        ).fetchall()
    ]
    if len(entries) > MAX_SOURCE_FILES:
        raise RosterSyncError(f"source scan {scan_id} contains too many entries")
    manifest_rows: list[dict[str, str]] = []
    entry_authority_evidence: dict[str, dict[str, Any]] = {}
    counts = {"candidate": 0, "quarantined": 0, "ignored": 0}
    for entry in entries:
        status = _stored_receipt_text(
            entry.get("status"),
            MAX_SHORT_TEXT_BYTES,
            f"source scan {scan_id} entry status",
        )
        relative_path = _stored_receipt_text(
            entry.get("relative_path"),
            MAX_PATH_TEXT_BYTES,
            f"source scan {scan_id} relative path",
        )
        slug = _stored_receipt_text(
            entry.get("slug"),
            MAX_SHORT_TEXT_BYTES,
            f"source scan {scan_id} slug",
            allow_empty=True,
        )
        content_hash = _stored_receipt_text(
            entry.get("content_hash"),
            64,
            f"source scan {scan_id} content hash",
        )
        candidate_id = entry.get("candidate_id")
        if status == "candidate":
            candidate_id = _stored_receipt_text(
                candidate_id,
                MAX_SHORT_TEXT_BYTES,
                f"source scan {scan_id} candidate id",
            )
        if (
            status not in counts
            or (status == "ignored" and slug)
            or (status != "ignored" and not slug)
            or not re.fullmatch(r"[a-f0-9]{64}", content_hash)
            or (status != "candidate" and candidate_id is not None)
        ):
            raise RosterSyncError(f"source scan {scan_id} entry evidence is invalid")
        entry.update(
            {
                "relative_path": relative_path,
                "slug": slug,
                "content_hash": content_hash,
                "status": status,
                "candidate_id": candidate_id,
            }
        )
        origin, provenance_hash, _provenance_dependencies = _source_scan_entry_origin(
            conn,
            scan,
            entry,
            scan_id=scan_id,
            status=status,
            relative_path=relative_path,
            content_hash=content_hash,
            header_order=header_order,
            scan_created_at=created_at,
        )
        entry_authority_evidence[relative_path] = _source_scan_entry_authority_evidence(
            entry,
            origin=origin,
            provenance_hash=provenance_hash,
        )
        counts[status] += 1
        manifest_rows.append(
            {
                "hash": content_hash,
                "origin_hash": _hash_text(origin),
                "relative_path": relative_path,
                "slug": slug,
                "status": status,
            }
        )
    expected_counts = {
        "entry_count": len(entries),
        "candidate_count": counts["candidate"],
        "quarantined_count": counts["quarantined"],
        "ignored_count": counts["ignored"],
    }
    if expected_counts != declared_counts:
        raise RosterSyncError(f"source scan {scan_id} counts do not match its entries")
    if manifest_hash != _source_scan_manifest_hash(manifest_rows):
        raise RosterSyncError(f"source scan {scan_id} integrity is invalid")
    if require_enabled and not int(scan.get("source_enabled") or 0):
        raise RosterSyncError(f"source scan {scan_id} belongs to a disabled source")
    if require_latest:
        latest = conn.execute(
            "SELECT id FROM agent_source_scans WHERE source_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            (scan["source_id"],),
        ).fetchone()
        if (
            latest is None
            or _stored_receipt_text(
                latest["id"],
                MAX_SHORT_TEXT_BYTES,
                f"source scan {scan_id} latest id",
            )
            != scan_id
        ):
            raise RosterSyncError(
                f"source scan {scan_id} is no longer the latest evidence for its source"
            )
    scan["entries"] = entries
    structural_evidence = _source_scan_structural_evidence(
        scan,
        header_row,
        scan_id=scan_id,
    )
    scan["_event_order"] = structural_evidence["header"]["event_order"]
    scan["_structural_evidence"] = structural_evidence
    scan["_structural_hash"] = _bounded_evidence_hash(
        structural_evidence,
        f"source scan {scan_id} authority evidence",
    )
    scan["_authority_hash"] = _bounded_evidence_hash(
        {
            **structural_evidence,
            "entries": entries,
        },
        f"source scan {scan_id} full authority evidence",
    )
    scan["_entry_authority_evidence"] = entry_authority_evidence
    scan["_authority_dependencies"] = []
    return scan


def _validated_source_scan_entry(
    conn: Any,
    scan_id: str,
    relative_path: str,
) -> dict[str, Any]:
    """Validate one scan entry and its committed header without walking sibling entries."""

    scan_id = _require_bounded_text(scan_id, MAX_SHORT_TEXT_BYTES, "source scan id")
    relative_path = _require_bounded_text(
        relative_path,
        MAX_PATH_TEXT_BYTES,
        "source scan relative path",
    )
    row = conn.execute(
        "SELECT scan.*, source.enabled AS source_enabled FROM agent_source_scans AS scan "
        "JOIN agent_sources AS source ON source.id = scan.source_id WHERE scan.id = ?",
        (scan_id,),
    ).fetchone()
    if row is None:
        raise RosterSyncError(f"source scan not found: {scan_id}")
    scan = dict(row)
    for field, maximum in (
        ("id", MAX_SHORT_TEXT_BYTES),
        ("source_id", MAX_SHORT_TEXT_BYTES),
        ("status", MAX_SHORT_TEXT_BYTES),
        ("manifest_hash", 64),
        ("created_at", MAX_SHORT_TEXT_BYTES),
    ):
        scan[field] = _stored_receipt_text(
            scan.get(field),
            maximum,
            f"source scan {scan_id} {field}",
        )
    if scan["id"] != scan_id or re.fullmatch(r"[a-f0-9]{64}", scan["manifest_hash"]) is None:
        raise RosterSyncError(f"source scan {scan_id} identity is invalid")
    _counts, expected_status = _validated_source_scan_declaration(
        scan,
        scan_id=scan_id,
    )
    header_row = _validated_source_scan_header(
        conn,
        scan,
        scan_id=scan_id,
        expected_status=expected_status,
    )
    structural_evidence = _source_scan_structural_evidence(
        scan,
        header_row,
        scan_id=scan_id,
    )
    header_order = structural_evidence["header"]["event_order"]
    entry_rows = conn.execute(
        "SELECT relative_path, slug, content_hash, status, candidate_id "
        "FROM agent_source_scan_entries WHERE scan_id = ? AND relative_path = ? LIMIT 2",
        (scan_id, relative_path),
    ).fetchall()
    if len(entry_rows) != 1:
        raise RosterSyncError(f"source scan {scan_id} entry evidence is invalid")
    entry = dict(entry_rows[0])
    status = _stored_receipt_text(
        entry.get("status"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} entry status",
    )
    slug = _stored_receipt_text(
        entry.get("slug"),
        MAX_SHORT_TEXT_BYTES,
        f"source scan {scan_id} slug",
        allow_empty=True,
    )
    content_hash = _stored_receipt_text(
        entry.get("content_hash"),
        64,
        f"source scan {scan_id} content hash",
    )
    stored_path = _stored_receipt_text(
        entry.get("relative_path"),
        MAX_PATH_TEXT_BYTES,
        f"source scan {scan_id} relative path",
    )
    candidate_id = entry.get("candidate_id")
    if status == "candidate":
        candidate_id = _stored_receipt_text(
            candidate_id,
            MAX_SHORT_TEXT_BYTES,
            f"source scan {scan_id} candidate id",
        )
    if (
        stored_path != relative_path
        or status not in {"candidate", "quarantined", "ignored"}
        or (status == "ignored" and slug)
        or (status != "ignored" and not slug)
        or re.fullmatch(r"[a-f0-9]{64}", content_hash) is None
        or (status != "candidate" and candidate_id is not None)
    ):
        raise RosterSyncError(f"source scan {scan_id} entry evidence is invalid")
    entry.update(
        {
            "candidate_id": candidate_id,
            "content_hash": content_hash,
            "relative_path": stored_path,
            "slug": slug,
            "status": status,
        }
    )
    origin, provenance_hash, provenance_dependencies = _source_scan_entry_origin(
        conn,
        scan,
        entry,
        scan_id=scan_id,
        status=status,
        relative_path=relative_path,
        content_hash=content_hash,
        header_order=header_order,
        scan_created_at=scan["created_at"],
    )
    selected_entry_evidence = _source_scan_entry_authority_evidence(
        entry,
        origin=origin,
        provenance_hash=provenance_hash,
    )
    scan["entries"] = [entry]
    scan["_event_order"] = structural_evidence["header"]["event_order"]
    scan["_structural_evidence"] = structural_evidence
    scan["_structural_hash"] = _bounded_evidence_hash(
        structural_evidence,
        f"source scan {scan_id} entry authority evidence",
    )
    scan["_selected_entry_evidence"] = selected_entry_evidence
    scan["_selected_entry_hash"] = _bounded_evidence_hash(
        selected_entry_evidence,
        f"source scan {scan_id} selected entry authority evidence",
    )
    scan["_authority_dependencies"] = provenance_dependencies
    return scan


def list_source_scans(store: Store, *, limit: int = 50) -> list[dict[str, Any]]:
    """List bounded, fully validated source-scan receipts without entry content."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1_000:
        raise ValueError("source scan limit must be between 1 and 1000")
    conn = _connect(store)
    try:
        conn.execute("BEGIN")
        rows = conn.execute(
            "SELECT id FROM agent_source_scans ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for row in rows:
            scan = _validated_source_scan(
                conn,
                str(row["id"]),
                require_latest=False,
                require_enabled=False,
            )
            result.append(
                {
                    field: scan[field]
                    for field in (
                        "id",
                        "source_id",
                        "status",
                        "manifest_hash",
                        "entry_count",
                        "candidate_count",
                        "quarantined_count",
                        "ignored_count",
                        "created_at",
                    )
                }
            )
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _remediation_queue_binding_hash(
    *,
    source_id: str,
    scan_id: str,
    relative_path: str,
    origin: str,
    content_hash: str,
) -> str:
    return _hash_text(
        json.dumps(
            {
                "hash": content_hash,
                "origin": origin,
                "relative_path": relative_path,
                "scan_id": scan_id,
                "source_id": source_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def _validated_remediation_queue_item_base(conn: Any, row: Any) -> dict[str, Any]:
    detail = _load_json(
        _bounded_event_detail(row, "remediation queue event"),
        "remediation queue event",
    )
    if not isinstance(detail, dict) or set(detail) != {
        "binding_hash",
        "download_id",
        "origin",
        "receipt",
        "relative_path",
        "scan_id",
        "source_id",
    }:
        raise RosterSyncError("remediation queue event fields are invalid")
    try:
        receipt: RemediationAttemptReceipt = normalize_remediation_attempt(detail["receipt"])
    except RosterRemediationError as exc:
        raise RosterSyncError("remediation queue receipt is invalid") from exc
    download_id = _stored_receipt_text(
        detail["download_id"], MAX_SHORT_TEXT_BYTES, "remediation queue download id"
    )
    source_id = _stored_receipt_text(
        detail["source_id"], MAX_SHORT_TEXT_BYTES, "remediation queue source id"
    )
    scan_id = _stored_receipt_text(
        detail["scan_id"], MAX_SHORT_TEXT_BYTES, "remediation queue scan id"
    )
    origin = _stored_receipt_text(detail["origin"], MAX_PATH_TEXT_BYTES, "remediation queue origin")
    relative_path = _stored_receipt_text(
        detail["relative_path"], MAX_PATH_TEXT_BYTES, "remediation queue relative path"
    )
    binding_hash = detail["binding_hash"]
    if (
        not isinstance(binding_hash, str)
        or not re.fullmatch(r"[a-f0-9]{64}", binding_hash)
        or binding_hash
        != _remediation_queue_binding_hash(
            source_id=source_id,
            scan_id=scan_id,
            relative_path=relative_path,
            origin=origin,
            content_hash=receipt.original_hash,
        )
    ):
        raise RosterSyncError("remediation queue scan binding is invalid")
    download = conn.execute(
        "SELECT d.source_id, d.slug, d.hash, d.content, d.status, c.id AS candidate_id "
        "FROM agent_downloads d LEFT JOIN agent_candidates c ON c.download_id = d.id "
        "WHERE d.id = ?",
        (download_id,),
    ).fetchone()
    if download is not None:
        download_source_id = _stored_receipt_text(
            download["source_id"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue download source id",
        )
        download_slug = _stored_receipt_text(
            download["slug"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue download slug",
        )
        download_hash = _stored_receipt_text(
            download["hash"],
            64,
            "remediation queue download hash",
        )
        download_status = _stored_receipt_text(
            download["status"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue download status",
        )
        if not isinstance(download["content"], str):
            raise RosterSyncError("remediation queue download content must be text")
    else:
        download_source_id = download_slug = download_hash = download_status = ""
    if (
        download is None
        or download_source_id != source_id
        or download_slug
        != _stored_receipt_text(
            row["agent_slug"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue agent slug",
        )
        or download_hash != receipt.original_hash
        or download_status != "quarantined"
        or download["candidate_id"] is not None
    ):
        raise RosterSyncError("remediation queue download binding is invalid")
    event_order = row["event_order"]
    if isinstance(event_order, bool) or not isinstance(event_order, int):
        raise RosterSyncError("remediation queue event order is invalid")
    return {
        "event_id": _stored_receipt_text(
            row["id"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue event id",
        ),
        "slug": _stored_receipt_text(
            row["agent_slug"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue agent slug",
        ),
        "download_id": download_id,
        "source_id": source_id,
        "scan_id": scan_id,
        "origin": origin,
        "relative_path": relative_path,
        "created_at": _stored_receipt_text(
            row["created_at"],
            MAX_SHORT_TEXT_BYTES,
            "remediation queue timestamp",
        ),
        "receipt": receipt.public_dict(),
        "_event_order": event_order,
        "_source_content": download["content"],
        "_authority_dependencies": [
            _authority_dependency(
                "queue_event",
                row["id"],
                {
                    "agent_slug": row["agent_slug"],
                    "created_at": row["created_at"],
                    "detail": _bounded_event_detail(row, "remediation queue event"),
                    "event_order": event_order,
                    "id": row["id"],
                },
            ),
            _authority_dependency(
                "queue_download",
                download_id,
                {
                    "candidate_id": download["candidate_id"],
                    "content": download["content"],
                    "hash": download_hash,
                    "id": download_id,
                    "slug": download_slug,
                    "source_id": download_source_id,
                    "status": download_status,
                },
            ),
            _authority_dependency(
                "source",
                source_id,
                {"id": source_id},
            ),
        ],
    }


def _cached_remediation_source_scan(
    conn: Any,
    scan_id: str,
    relative_path: str,
    scan_cache: dict[tuple[str, str], dict[str, Any]] | None,
) -> dict[str, Any]:
    cache_key = (scan_id, relative_path)
    if scan_cache is None:
        return _validated_source_scan_entry(conn, scan_id, relative_path)
    if cache_key not in scan_cache:
        scan_cache[cache_key] = _validated_source_scan_entry(
            conn,
            scan_id,
            relative_path,
        )
    return scan_cache[cache_key]


def _cached_full_remediation_source_scan(
    conn: Any,
    scan_id: str,
    full_scan_cache: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if full_scan_cache is None:
        return _validated_source_scan(
            conn,
            scan_id,
            require_latest=False,
            require_enabled=False,
        )
    if scan_id not in full_scan_cache:
        full_scan_cache[scan_id] = _validated_source_scan(
            conn,
            scan_id,
            require_latest=False,
            require_enabled=False,
        )
    return full_scan_cache[scan_id]


def _assert_local_scan_entry_matches_full_scan(
    local_scan: Mapping[str, Any],
    full_scan: Mapping[str, Any],
    *,
    scan_id: str,
    relative_path: str,
) -> Mapping[str, Any]:
    full_entry = next(
        (entry for entry in full_scan["entries"] if entry["relative_path"] == relative_path),
        None,
    )
    if full_entry is None:
        raise RosterSyncError("remediation authority source scan entry is unavailable")
    full_entry_evidence = full_scan["_entry_authority_evidence"].get(relative_path)
    if (
        local_scan["_structural_evidence"] != full_scan["_structural_evidence"]
        or local_scan["_structural_hash"] != full_scan["_structural_hash"]
        or full_entry_evidence is None
        or local_scan["_selected_entry_evidence"] != full_entry_evidence
        or local_scan["_selected_entry_hash"]
        != _bounded_evidence_hash(
            full_entry_evidence,
            f"source scan {scan_id} selected entry authority evidence",
        )
    ):
        raise RosterSyncError("remediation authority source scan commitment changed")
    return full_entry


def _cached_scan_entry(
    scan: Mapping[str, Any],
    relative_path: str,
    entry_cache: dict[str, dict[str, Mapping[str, Any]]] | None,
) -> Mapping[str, Any] | None:
    del entry_cache
    return next(
        (entry for entry in scan["entries"] if entry["relative_path"] == relative_path),
        None,
    )


def _validated_remediation_queue_item(
    conn: Any,
    row: Any,
    *,
    scan_cache: dict[tuple[str, str], dict[str, Any]] | None = None,
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] | None = None,
    full_scan_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    item = _validated_remediation_queue_item_base(conn, row)
    scan = _cached_remediation_source_scan(
        conn,
        item["scan_id"],
        item["relative_path"],
        scan_cache,
    )
    entry = _cached_scan_entry(
        scan,
        item["relative_path"],
        scan_entry_cache,
    )
    if (
        scan["source_id"] != item["source_id"]
        or entry is None
        or entry["slug"] != item["slug"]
        or entry["content_hash"] != item["receipt"]["original_hash"]
        or entry["status"] != "quarantined"
        or entry.get("candidate_id") is not None
        or scan["created_at"] != item["created_at"]
        or int(scan["_event_order"]) <= int(item["_event_order"])
    ):
        raise RosterSyncError("remediation queue source scan binding is invalid")
    if full_scan_cache is not None:
        full_scan = _cached_full_remediation_source_scan(
            conn,
            item["scan_id"],
            full_scan_cache,
        )
        _assert_local_scan_entry_matches_full_scan(
            scan,
            full_scan,
            scan_id=item["scan_id"],
            relative_path=item["relative_path"],
        )
    item["_authority_dependencies"].append(
        _authority_dependency(
            "queue_source_scan",
            scan["id"],
            {
                "relative_path": item["relative_path"],
                "selected_entry_hash": scan["_selected_entry_hash"],
                "structural_hash": scan["_structural_hash"],
            },
        )
    )
    item["_authority_dependencies"].extend(scan["_authority_dependencies"])
    return item


def _validate_remediated_resolution_provenance(
    conn: Any,
    row: Any,
    detail: Mapping[str, Any],
    queue: Mapping[str, Any],
    candidate: Any,
) -> Any:
    try:
        evidence = candidate_remediation_evidence_from_connection(conn, candidate)
    except RosterSyncError as exc:
        raise RosterSyncError("remediation resolution transformation evidence is invalid") from exc
    if evidence is None:
        raise RosterSyncError("remediation resolution transformation evidence is invalid")
    queue_timestamp = _event_timestamp(
        queue["created_at"],
        "remediation queue timestamp",
    )
    evidence_timestamp = _event_timestamp(
        evidence.event_created_at,
        "candidate remediation timestamp",
    )
    resolution_timestamp = _event_timestamp(
        row["created_at"],
        "remediation resolution timestamp",
    )
    if (
        evidence.event_order <= int(queue["_event_order"])
        or evidence.event_order >= int(row["event_order"])
        or evidence_timestamp < queue_timestamp
        or evidence_timestamp > resolution_timestamp
        or evidence.candidate_download_id != detail["candidate_download_id"]
        or evidence.candidate_hash != detail["candidate_hash"]
        or evidence.source_id != queue["source_id"]
        or evidence.source_slug != queue["slug"]
        or evidence.source_hash != detail["original_hash"]
        or evidence.source_content != queue["_source_content"]
        or evidence.source_status != "quarantined"
        or evidence.origin != queue["origin"]
        or evidence.relative_path != queue["relative_path"]
    ):
        raise RosterSyncError("remediation resolution transformation evidence is invalid")
    return evidence


def _validated_remediation_resolution_detail(
    row: Any,
    loaded_detail: Any,
) -> dict[str, Any]:
    detail = (
        _load_json(
            _bounded_event_detail(row, "remediation resolution event"),
            "remediation resolution event",
        )
        if loaded_detail is None
        else loaded_detail
    )
    expected = {
        "audit_id",
        "audit_revision",
        "candidate_download_id",
        "candidate_hash",
        "candidate_id",
        "download_id",
        "original_hash",
        "origin",
        "policy_hash",
        "queue_event_id",
        "relative_path",
        "resolution",
        "scan_id",
        "source_hash",
        "source_id",
    }
    if not isinstance(detail, dict) or set(detail) != expected:
        raise RosterSyncError("remediation resolution event fields are invalid")
    for field, maximum in (
        ("audit_id", MAX_SHORT_TEXT_BYTES),
        ("audit_revision", MAX_SHORT_TEXT_BYTES),
        ("candidate_download_id", MAX_SHORT_TEXT_BYTES),
        ("candidate_id", MAX_SHORT_TEXT_BYTES),
        ("download_id", MAX_SHORT_TEXT_BYTES),
        ("origin", MAX_PATH_TEXT_BYTES),
        ("policy_hash", 64),
        ("queue_event_id", MAX_SHORT_TEXT_BYTES),
        ("relative_path", MAX_PATH_TEXT_BYTES),
        ("resolution", MAX_SHORT_TEXT_BYTES),
        ("scan_id", MAX_SHORT_TEXT_BYTES),
        ("source_id", MAX_SHORT_TEXT_BYTES),
    ):
        detail[field] = _stored_receipt_text(
            detail[field],
            maximum,
            f"remediation resolution {field}",
        )
    for field in ("candidate_hash", "original_hash", "policy_hash", "source_hash"):
        if not isinstance(detail[field], str) or not re.fullmatch(r"[a-f0-9]{64}", detail[field]):
            raise RosterSyncError(f"remediation resolution {field} is invalid")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", detail["audit_revision"]):
        raise RosterSyncError("remediation resolution audit_revision is invalid")
    if detail["resolution"] not in _REMEDIATION_RESOLUTIONS:
        raise RosterSyncError("remediation resolution type is invalid")
    return detail


def _cached_resolution_candidate_audit(
    conn: Any,
    detail: Mapping[str, str],
    candidate_cache: dict[str, dict[str, Any]] | None,
    audit_cache: dict[tuple[str, str, str, str], tuple[dict[str, Any], bool]] | None,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    candidate_id = detail["candidate_id"]
    try:
        if candidate_cache is not None and candidate_id in candidate_cache:
            candidate = candidate_cache[candidate_id]
        else:
            candidate = candidate_record_from_connection(conn, candidate_id)
            if candidate_cache is not None:
                candidate_cache[candidate_id] = candidate
    except (KeyError, RosterSyncError) as exc:
        raise RosterSyncError("remediation resolution candidate evidence is invalid") from exc
    audit_key = (
        detail["audit_id"],
        str(candidate["id"]),
        str(candidate["version"]),
        str(candidate["hash"]),
    )
    try:
        if audit_cache is not None and audit_key in audit_cache:
            audit, policy_current = audit_cache[audit_key]
        else:
            audit, policy_current = assert_bound_candidate_audit_from_connection(
                conn,
                audit_id=detail["audit_id"],
                candidate_id=str(candidate["id"]),
                candidate_version=str(candidate["version"]),
                candidate_hash=str(candidate["hash"]),
                require_current_policy=False,
            )
            if audit_cache is not None:
                audit_cache[audit_key] = (audit, policy_current)
    except (KeyError, RosterSyncError) as exc:
        raise RosterSyncError("remediation resolution candidate evidence is invalid") from exc
    return candidate, audit, policy_current


def _validated_remediation_resolution(
    conn: Any,
    row: Any,
    queue: Mapping[str, Any],
    *,
    loaded_detail: Any = None,
    scan_cache: dict[tuple[str, str], dict[str, Any]] | None = None,
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] | None = None,
    candidate_cache: dict[str, dict[str, Any]] | None = None,
    audit_cache: dict[tuple[str, str, str, str], tuple[dict[str, Any], bool]] | None = None,
) -> dict[str, Any]:
    detail = _validated_remediation_resolution_detail(row, loaded_detail)
    event_id = _stored_receipt_text(
        row["id"],
        MAX_SHORT_TEXT_BYTES,
        "remediation resolution event id",
    )
    event_slug = _stored_receipt_text(
        row["agent_slug"],
        MAX_SHORT_TEXT_BYTES,
        "remediation resolution agent slug",
    )
    event_created_at = _stored_receipt_text(
        row["created_at"],
        MAX_SHORT_TEXT_BYTES,
        "remediation resolution timestamp",
    )
    event_order = row["event_order"]
    if isinstance(event_order, bool) or not isinstance(event_order, int):
        raise RosterSyncError("remediation resolution event order is invalid")
    if (
        event_slug != queue["slug"]
        or event_order <= int(queue["_event_order"])
        or detail["queue_event_id"] != queue["event_id"]
        or detail["download_id"] != queue["download_id"]
        or detail["source_id"] != queue["source_id"]
        or detail["origin"] != queue["origin"]
        or detail["relative_path"] != queue["relative_path"]
        or detail["original_hash"] != queue["receipt"]["original_hash"]
    ):
        raise RosterSyncError("remediation resolution queue binding is invalid")
    expected_resolution = (
        "remediated_candidate"
        if detail["source_hash"] == detail["original_hash"]
        else "superseded_by_candidate"
    )
    if detail["resolution"] != expected_resolution:
        raise RosterSyncError("remediation resolution disposition is invalid")
    candidate, audit, audit_policy_current = _cached_resolution_candidate_audit(
        conn,
        detail,
        candidate_cache,
        audit_cache,
    )
    resolution_timestamp = _event_timestamp(
        event_created_at,
        "remediation resolution timestamp",
    )
    audit_precedes_resolution = (
        _event_timestamp(
            audit["created_at"],
            "candidate audit timestamp",
        )
        <= resolution_timestamp
    )
    scan = _cached_remediation_source_scan(
        conn,
        detail["scan_id"],
        detail["relative_path"],
        scan_cache,
    )
    scan_entry = _cached_scan_entry(
        scan,
        detail["relative_path"],
        scan_entry_cache,
    )
    if (
        str(candidate["download_id"]) != detail["candidate_download_id"]
        or str(candidate["hash"]) != detail["candidate_hash"]
        or str(candidate["download_hash"]) != detail["candidate_hash"]
        or str(candidate["source_id"]) != detail["source_id"]
        or str(candidate["prompt_path"]) != detail["origin"]
        or str(audit["audit_revision"]) != detail["audit_revision"]
        or str(audit["policy_hash"]) != detail["policy_hash"]
        or not audit_precedes_resolution
        or _event_timestamp(
            queue["created_at"],
            "remediation queue timestamp",
        )
        > resolution_timestamp
        or scan["source_id"] != detail["source_id"]
        or scan_entry is None
        or scan_entry["content_hash"] != detail["source_hash"]
        or scan_entry["status"] != "candidate"
        or scan_entry["candidate_id"] != detail["candidate_id"]
        or event_order <= int(scan["_event_order"])
        or _event_timestamp(
            scan["created_at"],
            "candidate source scan timestamp",
        )
        > resolution_timestamp
    ):
        raise RosterSyncError("remediation resolution candidate evidence is invalid")
    remediation_evidence = None
    if detail["resolution"] == "remediated_candidate":
        remediation_evidence = _validate_remediated_resolution_provenance(
            conn,
            row,
            detail,
            queue,
            candidate,
        )
    dependencies = list(queue["_authority_dependencies"])
    dependencies.extend(scan["_authority_dependencies"])
    dependencies.extend(
        (
            _authority_dependency(
                "resolution_event",
                event_id,
                {
                    "agent_slug": event_slug,
                    "created_at": event_created_at,
                    "detail": _bounded_event_detail(row, "remediation resolution event"),
                    "event_order": event_order,
                    "id": event_id,
                },
            ),
            _authority_dependency(
                "candidate",
                detail["candidate_id"],
                _candidate_authority_identity(candidate),
            ),
            _authority_dependency(
                "candidate_download",
                detail["candidate_download_id"],
                {
                    "content": candidate["content"],
                    "hash": candidate["download_hash"],
                    "id": candidate["download_id"],
                    "slug": candidate["slug"],
                    "source_id": candidate["source_id"],
                },
            ),
            _authority_dependency(
                "candidate_source_scan",
                scan["id"],
                {
                    "relative_path": detail["relative_path"],
                    "selected_entry_hash": scan["_selected_entry_hash"],
                    "structural_hash": scan["_structural_hash"],
                },
            ),
            _authority_dependency(
                "candidate_audit",
                detail["audit_id"],
                audit,
            ),
        )
    )
    if remediation_evidence is not None:
        remediation_identity = _remediation_evidence_identity(remediation_evidence)
        dependencies.extend(
            (
                _authority_dependency(
                    "transformation_event",
                    remediation_evidence.event_id,
                    remediation_identity,
                ),
                _authority_dependency(
                    "source_download",
                    remediation_evidence.source_download_id,
                    {
                        "content": remediation_evidence.source_content,
                        "hash": remediation_evidence.source_hash,
                        "id": remediation_evidence.source_download_id,
                        "slug": remediation_evidence.source_slug,
                        "source_id": remediation_evidence.source_id,
                        "status": remediation_evidence.source_status,
                    },
                ),
                _authority_dependency(
                    "candidate_slug",
                    queue["slug"],
                    {
                        "event_ids": [remediation_evidence.event_id],
                        "slug": queue["slug"],
                    },
                ),
            )
        )
    evidence_receipt, normalized_dependencies = _canonical_authority_receipt(dependencies)
    return {
        "event_id": event_id,
        "queue_event_id": queue["event_id"],
        "slug": queue["slug"],
        "download_id": queue["download_id"],
        "source_id": queue["source_id"],
        "relative_path": queue["relative_path"],
        "original_hash": detail["original_hash"],
        "resolution": detail["resolution"],
        "candidate_id": detail["candidate_id"],
        "candidate_hash": detail["candidate_hash"],
        "source_hash": detail["source_hash"],
        "audit_id": detail["audit_id"],
        "audit_revision": detail["audit_revision"],
        "policy_hash": detail["policy_hash"],
        "audit_policy_current": audit_policy_current,
        "created_at": event_created_at,
        "_authority_dependencies": normalized_dependencies,
        "_authority_evidence_receipt": evidence_receipt,
    }


def _prepare_remediation_resolution_authority(
    conn: Any,
    row: Any,
    queued: Mapping[str, Any],
    *,
    scan_cache: dict[tuple[str, str], dict[str, Any]] | None = None,
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] | None = None,
    candidate_cache: dict[str, dict[str, Any]] | None = None,
    audit_cache: dict[tuple[str, str, str, str], tuple[dict[str, Any], bool]] | None = None,
    full_scan_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validated = _validated_remediation_resolution(
        conn,
        row,
        queued,
        scan_cache=scan_cache,
        scan_entry_cache=scan_entry_cache,
        candidate_cache=candidate_cache,
        audit_cache=audit_cache,
    )
    resolution_detail = _validated_remediation_resolution_detail(row, None)
    scan_roles = (
        (
            "queue_source_scan",
            queued["scan_id"],
            queued["relative_path"],
        ),
        (
            "candidate_source_scan",
            resolution_detail["scan_id"],
            resolution_detail["relative_path"],
        ),
    )
    full_scan_dependencies: list[dict[str, str]] = []
    for kind, scan_id, relative_path in scan_roles:
        local_scan = _cached_remediation_source_scan(
            conn,
            scan_id,
            relative_path,
            scan_cache,
        )
        full_scan = _cached_full_remediation_source_scan(
            conn,
            scan_id,
            full_scan_cache,
        )
        full_entry = _assert_local_scan_entry_matches_full_scan(
            local_scan,
            full_scan,
            scan_id=scan_id,
            relative_path=relative_path,
        )
        if kind == "queue_source_scan":
            entry_matches = (
                full_entry["status"] == "quarantined"
                and full_entry["slug"] == queued["slug"]
                and full_entry["content_hash"] == queued["receipt"]["original_hash"]
            )
        else:
            entry_matches = (
                full_entry["status"] == "candidate"
                and full_entry["candidate_id"] == resolution_detail["candidate_id"]
                and full_entry["content_hash"] == resolution_detail["source_hash"]
            )
        if not entry_matches:
            raise RosterSyncError("remediation authority source scan entry changed")
        full_scan_dependencies.append(
            _authority_dependency(
                kind,
                scan_id,
                {
                    "authority_hash": full_scan["_authority_hash"],
                    "entry": full_entry,
                    "relative_path": relative_path,
                },
            )
        )
    provisional_scan_roles = {(kind, scan_id) for kind, scan_id, _relative_path in scan_roles}
    authority_dependencies = [
        dependency
        for dependency in validated["_authority_dependencies"]
        if (dependency["kind"], dependency["id"]) not in provisional_scan_roles
    ]
    authority_dependencies.extend(full_scan_dependencies)
    evidence_receipt, normalized_dependencies = _canonical_authority_receipt(authority_dependencies)
    validated["_authority_dependencies"] = normalized_dependencies
    validated["_authority_evidence_receipt"] = evidence_receipt
    return validated


def _persist_remediation_resolution_authority(
    conn: Any,
    store: Store,
    row: Any,
    queued: Mapping[str, Any],
    validated: Mapping[str, Any],
) -> None:
    event_detail = _bounded_event_detail(row, "remediation resolution event")
    validated_at = store._now()
    if _event_timestamp(
        validated_at,
        "remediation authority validation timestamp",
    ) < _event_timestamp(
        validated["created_at"],
        "remediation resolution timestamp",
    ):
        raise RosterSyncError("remediation authority validation predates its resolution evidence")
    evidence_receipt, dependency_count, authority_hmac = (
        remediation_authority_material_from_connection(
            conn,
            resolution_event_id=validated["event_id"],
            queue_event_id=validated["queue_event_id"],
            event_detail=event_detail,
            dependencies=validated["_authority_dependencies"],
            validated_at=validated_at,
            queue_created_at=queued["created_at"],
            resolution_created_at=validated["created_at"],
            agent_slug=validated["slug"],
        )
    )
    conn.execute(
        "DELETE FROM agent_remediation_resolution_authority "
        "WHERE resolution_event_id = ? OR queue_event_id = ?",
        (validated["event_id"], validated["queue_event_id"]),
    )
    conn.execute(
        "INSERT INTO agent_remediation_resolution_authority "
        "(resolution_event_id, queue_event_id, evidence_receipt, dependency_count, "
        "authority_hmac, validated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            validated["event_id"],
            validated["queue_event_id"],
            evidence_receipt,
            dependency_count,
            authority_hmac,
            validated_at,
        ),
    )
    conn.executemany(
        "INSERT INTO agent_remediation_resolution_dependencies "
        "(resolution_event_id, dependency_kind, dependency_id, dependency_hash) "
        "VALUES (?, ?, ?, ?)",
        [
            (
                validated["event_id"],
                dependency["kind"],
                dependency["id"],
                dependency["hash"],
            )
            for dependency in validated["_authority_dependencies"]
        ],
    )


def _authorize_remediation_resolution(
    conn: Any,
    store: Store,
    row: Any,
    queued: Mapping[str, Any],
    *,
    scan_cache: dict[tuple[str, str], dict[str, Any]] | None = None,
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] | None = None,
    candidate_cache: dict[str, dict[str, Any]] | None = None,
    audit_cache: dict[tuple[str, str, str, str], tuple[dict[str, Any], bool]] | None = None,
    full_scan_cache: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    validated = _prepare_remediation_resolution_authority(
        conn,
        row,
        queued,
        scan_cache=scan_cache,
        scan_entry_cache=scan_entry_cache,
        candidate_cache=candidate_cache,
        audit_cache=audit_cache,
        full_scan_cache=full_scan_cache,
    )
    _persist_remediation_resolution_authority(
        conn,
        store,
        row,
        queued,
        validated,
    )
    return validated


def _public_remediation_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def _authorized_resolution_integrity_sql(
    authority_alias: str,
    resolution_alias: str,
    queue_alias: str,
) -> str:
    allowed = {"authority", "resolution", "queue_event", "queued"}
    if {authority_alias, resolution_alias, queue_alias} - allowed:
        raise ValueError("unsupported remediation authority SQL alias")
    return (
        "agency_verify_remediation_authority("
        f"{resolution_alias}.id, {authority_alias}.queue_event_id, "
        f"{resolution_alias}.detail, {authority_alias}.evidence_receipt, "
        f"{authority_alias}.dependency_count, {authority_alias}.validated_at, "
        f"{authority_alias}.authority_hmac, {queue_alias}.created_at, "
        f"{resolution_alias}.created_at, {resolution_alias}.agent_slug) = 1 "
        f"AND {authority_alias}.dependency_count = (SELECT COUNT(*) "
        "FROM agent_remediation_resolution_dependencies AS dependency "
        f"WHERE dependency.resolution_event_id = {authority_alias}.resolution_event_id) "
        "AND NOT EXISTS (SELECT 1 "
        "FROM agent_remediation_resolution_dependencies AS dependency "
        f"WHERE dependency.resolution_event_id = {authority_alias}.resolution_event_id "
        "AND agency_remediation_receipt_has_dependency("
        f"{authority_alias}.evidence_receipt, dependency.dependency_kind, "
        "dependency.dependency_id, dependency.dependency_hash) != 1)"
    )


def _authorized_resolution_exists_sql(queue_alias: str) -> str:
    if queue_alias not in {"queued", "queue_event"}:
        raise ValueError("unsupported remediation queue SQL alias")
    integrity = _authorized_resolution_integrity_sql(
        "authority",
        "resolution",
        queue_alias,
    )
    return (
        "EXISTS (SELECT 1 FROM agent_remediation_resolution_authority AS authority "
        "JOIN agent_import_events AS resolution "
        "ON resolution.id = authority.resolution_event_id "
        f"WHERE authority.queue_event_id = {queue_alias}.id "
        "AND resolution.event_type = 'manifest_entry_remediation_resolved' "
        "AND resolution.event_sequence > "
        f"{queue_alias}.event_sequence "
        f"AND resolution.agent_slug = {queue_alias}.agent_slug "
        f"AND {integrity})"
    )


def _remediation_cursor_order(
    conn: Any,
    cursor: str,
    *,
    event_type: str,
    label: str,
) -> int | None:
    if not cursor:
        return None
    cursor = _require_bounded_text(cursor, MAX_SHORT_TEXT_BYTES, label)
    if event_type == "manifest_entry_remediation_resolved":
        integrity = _authorized_resolution_integrity_sql(
            "authority",
            "resolution",
            "queue_event",
        )
        row = conn.execute(
            "SELECT resolution.event_sequence AS event_order "
            "FROM agent_remediation_resolution_authority AS authority "
            "JOIN agent_import_events AS resolution "
            "ON resolution.id = authority.resolution_event_id "
            "JOIN agent_import_events AS queue_event "
            "ON queue_event.id = authority.queue_event_id "
            "WHERE resolution.id = ? "
            "AND resolution.event_type = 'manifest_entry_remediation_resolved' "
            "AND queue_event.event_type = 'manifest_entry_remediation_queued' "
            "AND resolution.event_sequence > queue_event.event_sequence "
            "AND resolution.agent_slug = queue_event.agent_slug "
            f"AND {integrity}",  # nosec B608
            (cursor,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT event_sequence AS event_order FROM agent_import_events "
            "WHERE id = ? AND event_type = ?",
            (cursor, event_type),
        ).fetchone()
    if row is None:
        raise ValueError(f"{label} does not identify a {event_type} event")
    return int(row["event_order"])


def _remediation_queue_snapshot(
    conn: Any,
    *,
    limit: int,
    pending_cursor: str = "",
    history_cursor: str = "",
) -> dict[str, Any]:
    _assert_remediation_authority_available(conn)
    scan_cache: dict[tuple[str, str], dict[str, Any]] = {}
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] = {}
    pending_full_scan_cache: dict[str, dict[str, Any]] = {}
    candidate_cache: dict[str, dict[str, Any]] = {}
    audit_cache: dict[
        tuple[str, str, str, str],
        tuple[dict[str, Any], bool],
    ] = {}
    queue_cache: dict[str, dict[str, Any]] = {}
    pending_before = _remediation_cursor_order(
        conn,
        pending_cursor,
        event_type="manifest_entry_remediation_queued",
        label="pending remediation cursor",
    )
    history_before = _remediation_cursor_order(
        conn,
        history_cursor,
        event_type="manifest_entry_remediation_resolved",
        label="history remediation cursor",
    )
    pending_filter = "" if pending_before is None else "AND queued.event_sequence < ? "
    pending_parameters: tuple[Any, ...] = (() if pending_before is None else (pending_before,)) + (
        limit + 1,
    )
    pending_resolution_predicate = _authorized_resolution_exists_sql("queued")
    pending_rows = conn.execute(
        "SELECT queued.event_sequence AS event_order, queued.id, queued.agent_slug, "
        "queued.detail, queued.created_at FROM agent_import_events AS queued "
        "WHERE queued.event_type = 'manifest_entry_remediation_queued' "
        f"AND NOT {pending_resolution_predicate} "
        f"{pending_filter}ORDER BY queued.event_sequence DESC LIMIT ?",  # nosec B608
        pending_parameters,
    ).fetchall()
    history_filter = "" if history_before is None else "AND resolution.event_sequence < ? "
    history_parameters: tuple[Any, ...] = (() if history_before is None else (history_before,)) + (
        limit + 1,
    )
    history_integrity = _authorized_resolution_integrity_sql(
        "authority",
        "resolution",
        "queue_event",
    )
    history_rows = conn.execute(
        "SELECT resolution.event_sequence AS event_order, resolution.id, "
        "resolution.agent_slug, resolution.detail, resolution.created_at "
        "FROM agent_remediation_resolution_authority AS authority "
        "JOIN agent_import_events AS resolution "
        "ON resolution.id = authority.resolution_event_id "
        "JOIN agent_import_events AS queue_event "
        "ON queue_event.id = authority.queue_event_id "
        "WHERE resolution.event_type = 'manifest_entry_remediation_resolved' "
        "AND queue_event.event_type = 'manifest_entry_remediation_queued' "
        "AND resolution.event_sequence > queue_event.event_sequence "
        "AND resolution.agent_slug = queue_event.agent_slug "
        f"AND {history_integrity} "
        f"{history_filter}ORDER BY resolution.event_sequence DESC LIMIT ?",  # nosec B608
        history_parameters,
    ).fetchall()
    pending_page = [
        _validated_remediation_queue_item(
            conn,
            row,
            scan_cache=scan_cache,
            scan_entry_cache=scan_entry_cache,
            full_scan_cache=pending_full_scan_cache,
        )
        for row in pending_rows[:limit]
    ]
    history_page: list[dict[str, Any]] = []
    for row in history_rows[:limit]:
        detail = _load_json(
            _bounded_event_detail(row, "remediation resolution event"),
            "remediation resolution event",
        )
        if (
            not isinstance(detail, dict)
            or not isinstance(detail.get("queue_event_id"), str)
            or not detail["queue_event_id"]
        ):
            raise RosterSyncError("remediation resolution queue binding is invalid")
        queue_event_id = detail["queue_event_id"]
        if queue_event_id in queue_cache:
            queued = queue_cache[queue_event_id]
        else:
            queued_row = conn.execute(
                "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
                "FROM agent_import_events "
                "WHERE id = ? AND event_type = 'manifest_entry_remediation_queued'",
                (queue_event_id,),
            ).fetchone()
            if queued_row is None:
                raise RosterSyncError("remediation resolution references an unknown queue event")
            queued = _validated_remediation_queue_item(
                conn,
                queued_row,
                scan_cache=scan_cache,
                scan_entry_cache=scan_entry_cache,
            )
            queue_cache[queue_event_id] = queued
        history_page.append(
            _public_remediation_item(
                _validated_remediation_resolution(
                    conn,
                    row,
                    queued,
                    loaded_detail=detail,
                    scan_cache=scan_cache,
                    scan_entry_cache=scan_entry_cache,
                    candidate_cache=candidate_cache,
                    audit_cache=audit_cache,
                )
            )
        )
    pending_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM agent_import_events AS queued "
            "WHERE queued.event_type = 'manifest_entry_remediation_queued' "
            f"AND NOT {pending_resolution_predicate}"  # nosec B608
        ).fetchone()[0]
    )
    history_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM agent_remediation_resolution_authority AS authority "
            "JOIN agent_import_events AS resolution "
            "ON resolution.id = authority.resolution_event_id "
            "JOIN agent_import_events AS queue_event "
            "ON queue_event.id = authority.queue_event_id "
            "WHERE resolution.event_type = 'manifest_entry_remediation_resolved' "
            "AND queue_event.event_type = 'manifest_entry_remediation_queued' "
            "AND resolution.event_sequence > queue_event.event_sequence "
            "AND resolution.agent_slug = queue_event.agent_slug "
            f"AND {history_integrity}"  # nosec B608
        ).fetchone()[0]
    )
    raw_resolution_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM agent_import_events "
            "WHERE event_type = 'manifest_entry_remediation_resolved'"
        ).fetchone()[0]
    )
    return {
        "schema_version": _REMEDIATION_QUEUE_SCHEMA,
        "pending": [_public_remediation_item(item) for item in pending_page],
        "pending_count": pending_count,
        "pending_has_more": len(pending_rows) > limit,
        "next_pending_cursor": (
            pending_page[-1]["event_id"] if len(pending_rows) > limit and pending_page else ""
        ),
        "history": history_page,
        "history_count": history_count,
        "unvalidated_resolution_count": max(0, raw_resolution_count - history_count),
        "history_has_more": len(history_rows) > limit,
        "next_history_cursor": (
            history_page[-1]["event_id"] if len(history_rows) > limit and history_page else ""
        ),
    }


def remediation_queue_snapshot(
    store: Store,
    *,
    limit: int = 50,
    pending_cursor: str = "",
    history_cursor: str = "",
    _connection: Any | None = None,
) -> dict[str, Any]:
    """Return bounded pending and immutable resolved remediation evidence."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1_000:
        raise ValueError("remediation queue limit must be between 1 and 1000")
    owns_connection = _connection is None
    conn = _connect(store) if owns_connection else _connection
    try:
        if owns_connection:
            conn.execute("BEGIN")
        result = _remediation_queue_snapshot(
            conn,
            limit=limit,
            pending_cursor=pending_cursor,
            history_cursor=history_cursor,
        )
        if owns_connection:
            conn.commit()
        return result
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


def list_remediation_queue(
    store: Store,
    *,
    limit: int = 50,
    _connection: Any | None = None,
) -> list[dict[str, Any]]:
    """Return only pending source-bound, non-executable remediation attempts."""

    return remediation_queue_snapshot(store, limit=limit, _connection=_connection)["pending"]


def _eligible_remediation_candidate_identities(
    conn: Any,
    source_id: str,
    outcomes: Sequence[ManifestImportOutcome],
    candidates: Mapping[str, Mapping[str, Any]],
    candidate_records: Mapping[str, tuple[str, str]],
    audits: Mapping[str, Mapping[str, Any]],
) -> dict[
    tuple[str, str, str],
    tuple[ManifestImportOutcome, Mapping[str, Any], str, str, Mapping[str, Any]],
]:
    result: dict[
        tuple[str, str, str],
        tuple[ManifestImportOutcome, Mapping[str, Any], str, str, Mapping[str, Any]],
    ] = {}
    for outcome in outcomes:
        if outcome.status != "candidate":
            continue
        candidate_id, candidate_download_id = candidate_records[outcome.slug]
        audit = audits[candidate_id]
        if audit.get("verdict") != "passed":
            continue
        result[(source_id, outcome.relative_path, outcome.origin)] = (
            outcome,
            candidates[outcome.slug],
            candidate_id,
            candidate_download_id,
            audit,
        )
    audit_candidates = [
        candidate_record_from_connection(conn, candidate_id)
        for _outcome, _candidate, candidate_id, _download_id, _audit in result.values()
    ]
    current_audit_ids = assert_candidate_audits_current(
        conn,
        audit_candidates,
        require_inference=False,
    )
    for _outcome, _candidate, candidate_id, _download_id, audit in result.values():
        if current_audit_ids.get(candidate_id) != str(audit["id"]):
            raise RosterSyncError(
                "remediation resolution requires the candidate's current audit basis"
            )
    return result


def _record_candidate_remediation_resolutions(
    conn: Any,
    store: Store,
    source_id: str,
    outcomes: Sequence[ManifestImportOutcome],
    candidates: Mapping[str, Mapping[str, Any]],
    candidate_records: Mapping[str, tuple[str, str]],
    audits: Mapping[str, Mapping[str, Any]],
    *,
    scan_id: str,
) -> bool:
    _assert_remediation_authority_available(conn)
    candidates_by_identity = _eligible_remediation_candidate_identities(
        conn,
        source_id,
        outcomes,
        candidates,
        candidate_records,
        audits,
    )
    if not candidates_by_identity:
        return False
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS current_remediation_identities ("
        "source_id TEXT NOT NULL, relative_path TEXT NOT NULL, origin TEXT NOT NULL, "
        "PRIMARY KEY (source_id, relative_path, origin)) WITHOUT ROWID"
    )
    conn.execute("DELETE FROM current_remediation_identities")
    conn.executemany(
        "INSERT INTO current_remediation_identities "
        "(source_id, relative_path, origin) VALUES (?, ?, ?)",
        sorted(candidates_by_identity),
    )
    pending_resolution_predicate = _authorized_resolution_exists_sql("queued")
    pending_rows = conn.execute(
        "SELECT queued.event_sequence AS event_order, queued.id, queued.agent_slug, "
        "queued.detail, queued.created_at "
        "FROM current_remediation_identities AS identity "
        "JOIN agent_import_events AS queued "
        "INDEXED BY idx_agent_import_queue_identity "
        "ON queued.event_type = 'manifest_entry_remediation_queued' "
        f"AND {_BOUNDED_QUEUED_REMEDIATION_DETAIL_PREDICATE_SQL} "
        "AND json_extract(queued.detail, '$.source_id') = identity.source_id "
        "AND json_extract(queued.detail, '$.relative_path') = identity.relative_path "
        "AND json_extract(queued.detail, '$.origin') = identity.origin "
        f"AND NOT {pending_resolution_predicate} "
        "ORDER BY queued.event_sequence LIMIT ?",
        (MAX_REMEDIATION_RESOLUTIONS_PER_SYNC + 1,),
    ).fetchall()
    has_more = len(pending_rows) > MAX_REMEDIATION_RESOLUTIONS_PER_SYNC
    scan_cache: dict[tuple[str, str], dict[str, Any]] = {}
    scan_entry_cache: dict[str, dict[str, Mapping[str, Any]]] = {}
    candidate_cache: dict[str, dict[str, Any]] = {}
    audit_cache: dict[
        tuple[str, str, str, str],
        tuple[dict[str, Any], bool],
    ] = {}
    full_scan_cache: dict[str, dict[str, Any]] = {}
    for row in pending_rows[:MAX_REMEDIATION_RESOLUTIONS_PER_SYNC]:
        queued = _validated_remediation_queue_item(
            conn,
            row,
            scan_cache=scan_cache,
            scan_entry_cache=scan_entry_cache,
        )
        identity = (queued["source_id"], queued["relative_path"], queued["origin"])
        selected = candidates_by_identity.get(identity)
        if selected is None:
            raise RosterSyncError("remediation identity query returned an unbound queue item")
        outcome, candidate, candidate_id, candidate_download_id, audit = selected
        original_hash = str(queued["receipt"]["original_hash"])
        if outcome.content_hash == original_hash and outcome.remediation is None:
            continue
        resolution = (
            "remediated_candidate"
            if outcome.content_hash == original_hash
            else "superseded_by_candidate"
        )
        detail = json.dumps(
            {
                "audit_id": str(audit["id"]),
                "audit_revision": str(audit["audit_revision"]),
                "candidate_download_id": candidate_download_id,
                "candidate_hash": str(candidate["hash"]),
                "candidate_id": candidate_id,
                "download_id": queued["download_id"],
                "original_hash": original_hash,
                "origin": queued["origin"],
                "policy_hash": str(audit["policy_hash"]),
                "queue_event_id": queued["event_id"],
                "relative_path": queued["relative_path"],
                "resolution": resolution,
                "scan_id": scan_id,
                "source_hash": outcome.content_hash,
                "source_id": source_id,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        resolution_created_at = store._now()
        candidate_scan_row = conn.execute(
            "SELECT created_at FROM agent_source_scans WHERE id = ?",
            (scan_id,),
        ).fetchone()
        if candidate_scan_row is None:
            raise RosterSyncError("remediation candidate source scan is unavailable")
        minimum_resolution_times = (
            str(audit["created_at"]),
            queued["created_at"],
            _stored_receipt_text(
                candidate_scan_row["created_at"],
                MAX_SHORT_TEXT_BYTES,
                "candidate source scan timestamp",
            ),
        )
        resolution_timestamp = _event_timestamp(
            resolution_created_at,
            "remediation resolution timestamp",
        )
        for minimum_time in minimum_resolution_times:
            if resolution_timestamp < _event_timestamp(
                minimum_time,
                "remediation dependency timestamp",
            ):
                raise RosterSyncError("remediation dependency timestamp is in the future")
        existing_resolutions = conn.execute(
            "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
            "FROM agent_import_events INDEXED BY idx_agent_import_resolution_queue "
            "WHERE event_type = 'manifest_entry_remediation_resolved' "
            f"AND {BOUNDED_REMEDIATION_EVENT_DETAIL_PREDICATE_SQL} "
            "AND json_extract(detail, '$.queue_event_id') = ? "
            "AND detail = ? ORDER BY event_sequence LIMIT 3",  # nosec B608
            (queued["event_id"], detail),
        ).fetchall()
        validated_matches: list[tuple[Any, dict[str, Any]]] = []
        for existing_resolution in existing_resolutions:
            try:
                validated_match = _prepare_remediation_resolution_authority(
                    conn,
                    existing_resolution,
                    queued,
                    scan_cache=scan_cache,
                    scan_entry_cache=scan_entry_cache,
                    candidate_cache=candidate_cache,
                    audit_cache=audit_cache,
                    full_scan_cache=full_scan_cache,
                )
            except RosterSyncError:
                continue
            validated_matches.append((existing_resolution, validated_match))
        if len(existing_resolutions) < 3 and len(validated_matches) == 1:
            selected_row, selected_resolution = validated_matches[0]
            _persist_remediation_resolution_authority(
                conn,
                store,
                selected_row,
                queued,
                selected_resolution,
            )
            continue
        resolution_event_id = _record_import_event(
            conn,
            store,
            "manifest_entry_remediation_resolved",
            queued["slug"],
            detail,
            now=resolution_created_at,
        )
        resolution_row = conn.execute(
            "SELECT event_sequence AS event_order, id, agent_slug, detail, created_at "
            "FROM agent_import_events WHERE id = ?",
            (resolution_event_id,),
        ).fetchone()
        if resolution_row is None:
            raise RosterSyncError("remediation resolution event was not persisted")
        _authorize_remediation_resolution(
            conn,
            store,
            resolution_row,
            queued,
            scan_cache=scan_cache,
            scan_entry_cache=scan_entry_cache,
            candidate_cache=candidate_cache,
            audit_cache=audit_cache,
            full_scan_cache=full_scan_cache,
        )
    if has_more:
        _record_import_event(
            conn,
            store,
            "manifest_remediation_resolution_batch_deferred",
            "",
            json.dumps(
                {
                    "limit": MAX_REMEDIATION_RESOLUTIONS_PER_SYNC,
                    "scan_id": scan_id,
                    "source_id": source_id,
                },
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
        )
    return has_more


def reconcile_manifest_remediation_resolutions(
    agents: Sequence[dict[str, Any]],
    outcomes: Sequence[ManifestImportOutcome],
    source_id: str,
    store: Store,
    *,
    candidate_ids: Sequence[str],
    audits: Sequence[Mapping[str, Any]],
    scan_id: str,
) -> bool:
    """Resolve queued remediation after the authoritative audit pass completes."""

    normalized_agents, validated_outcomes = _validated_manifest_batch(agents, outcomes)
    source_id = _require_bounded_text(source_id, MAX_SHORT_TEXT_BYTES, "source id")
    scan_id = _require_bounded_text(scan_id, MAX_SHORT_TEXT_BYTES, "source scan id")
    if isinstance(candidate_ids, (str, bytes, bytearray)) or len(candidate_ids) != len(
        normalized_agents
    ):
        raise RosterSyncError("remediation reconciliation candidate ids do not match the import")
    normalized_ids = [
        _require_bounded_text(candidate_id, MAX_SHORT_TEXT_BYTES, "candidate id")
        for candidate_id in candidate_ids
    ]
    if len(set(normalized_ids)) != len(normalized_ids) or len(audits) != len(normalized_ids):
        raise RosterSyncError("remediation reconciliation audit batch does not match the import")
    audit_map: dict[str, Mapping[str, Any]] = {}
    for candidate_id, audit in zip(normalized_ids, audits, strict=True):
        if not isinstance(audit, Mapping) or str(audit.get("candidate_id") or "") != candidate_id:
            raise RosterSyncError("remediation reconciliation audit is not candidate-bound")
        audit_map[candidate_id] = audit

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        scan = conn.execute(
            "SELECT scan.source_id, scan.manifest_hash, source.enabled "
            "FROM agent_source_scans AS scan JOIN agent_sources AS source "
            "ON source.id = scan.source_id WHERE scan.id = ?",
            (scan_id,),
        ).fetchone()
        if (
            scan is None
            or not int(scan["enabled"] or 0)
            or str(scan["source_id"]) != source_id
            or str(scan["manifest_hash"])
            != _source_scan_manifest_hash(_source_scan_manifest_rows(validated_outcomes))
        ):
            raise RosterSyncError("remediation reconciliation scan does not match the import")
        scan_candidates = {
            str(entry["slug"]): str(entry["candidate_id"])
            for entry in conn.execute(
                "SELECT slug, candidate_id FROM agent_source_scan_entries "
                "WHERE scan_id = ? AND status = 'candidate'",
                (scan_id,),
            ).fetchall()
        }
        expected_candidates = {
            agent["slug"]: candidate_id
            for agent, candidate_id in zip(normalized_agents, normalized_ids, strict=True)
        }
        if scan_candidates != expected_candidates:
            raise RosterSyncError("remediation reconciliation candidates do not match the scan")

        candidate_records: dict[str, tuple[str, str]] = {}
        hydrated_candidates: list[dict[str, Any]] = []
        for agent, candidate_id in zip(normalized_agents, normalized_ids, strict=True):
            record = candidate_record_from_connection(conn, candidate_id)
            candidate_records[agent["slug"]] = (candidate_id, str(record["download_id"]))
            hydrated_candidates.append(
                {
                    **agent,
                    "id": candidate_id,
                    "download_id": str(record["download_id"]),
                    "source_id": source_id,
                    "content": str(agent.get("content") or agent.get("prompt_body") or ""),
                }
            )
        _assert_candidate_records(
            conn,
            hydrated_candidates,
            allowed_statuses=frozenset({"pending", "approved", "activated"}),
        )
        has_more = _record_candidate_remediation_resolutions(
            conn,
            store,
            source_id,
            validated_outcomes,
            {agent["slug"]: agent for agent in normalized_agents},
            candidate_records,
            audit_map,
            scan_id=scan_id,
        )
        conn.commit()
        return has_more
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def quarantine_manifest_import(
    agents: Sequence[dict[str, Any]],
    outcomes: Sequence[ManifestImportOutcome],
    source_id: str,
    store: Store,
    *,
    require_inference: bool = False,
) -> tuple[list[str], list[dict[str, str]]]:
    """Atomically persist a manifest import while isolating rejected entries."""

    normalized_agents, validated_outcomes = _validated_manifest_batch(agents, outcomes)
    source_id = _require_bounded_text(source_id, MAX_SHORT_TEXT_BYTES, "source id")
    conn = _connect(store)
    candidate_records: dict[str, tuple[str, str]] = {}
    new_candidate_ids: set[str] = set()
    persisted_outcomes: list[dict[str, str]] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        source = conn.execute(
            "SELECT enabled FROM agent_sources WHERE id = ?",
            (source_id,),
        ).fetchone()
        if source is None:
            raise RosterSyncError("cannot quarantine a manifest for an unknown source")
        if not int(source["enabled"] or 0):
            raise RosterSyncError("cannot quarantine a manifest for a disabled source")
        now = _now()
        scan_id = _prepared_source_scan_id(
            conn,
            store,
            source_id,
            validated_outcomes,
        )
        for agent in normalized_agents:
            candidate_record, created = _insert_manifest_candidate(
                conn,
                store,
                source_id,
                agent,
                now=now,
            )
            candidate_records[agent["slug"]] = candidate_record
            if created:
                new_candidate_ids.add(candidate_record[0])
        for outcome in validated_outcomes:
            public = outcome.public_dict()
            public["scan_id"] = scan_id
            if outcome.status == "candidate":
                candidate_id, download_id = candidate_records[outcome.slug]
                public.update(
                    {
                        "candidate_id": candidate_id,
                        "download_id": download_id,
                    }
                )
                if outcome.remediation is not None:
                    public["source_download_id"] = _persist_remediated_manifest_source(
                        conn,
                        store,
                        source_id,
                        outcome,
                        candidate_id=candidate_id,
                        candidate_download_id=download_id,
                        candidate_is_new=candidate_id in new_candidate_ids,
                        now=now,
                    )
            elif outcome.status == "quarantined":
                public["download_id"] = _persist_rejected_manifest_entry(
                    conn,
                    store,
                    source_id,
                    outcome,
                    scan_id=scan_id,
                    now=now,
                )
            else:
                _record_ignored_manifest_entry(
                    conn,
                    store,
                    source_id,
                    outcome,
                    scan_id=scan_id,
                    now=now,
                )
            persisted_outcomes.append(public)
        audits: dict[str, dict[str, Any]] = {}
        for candidate_id, _download_id in candidate_records.values():
            audits[candidate_id] = audit_candidate_in_connection(
                conn,
                store,
                candidate_id,
                require_inference=require_inference,
            )
        _record_source_scan(
            conn,
            store,
            source_id,
            validated_outcomes,
            candidate_records,
            scan_id=scan_id,
            now=now,
        )
        _record_candidate_remediation_resolutions(
            conn,
            store,
            source_id,
            validated_outcomes,
            {agent["slug"]: agent for agent in normalized_agents},
            candidate_records,
            audits,
            scan_id=scan_id,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    candidate_ids = [candidate_records[agent["slug"]][0] for agent in normalized_agents]
    return candidate_ids, persisted_outcomes


def _with_projected_contract(item: Mapping[str, Any]) -> dict[str, Any]:
    projected = contract_for_projected_candidate(
        str(item.get("slug") or ""),
        str(item.get("hash") or ""),
    )
    if projected is None:
        return dict(item)
    hydrated = {**projected, **item}
    for field in _LIST_FIELDS:
        hydrated[field] = _json_list(hydrated.get(field), label=f"candidate {field}")
    try:
        verify_projected_candidate_contract(
            hydrated,
            source_hash=str(projected["source_content_hash"]),
            relative_path=str(projected["relative_path"]),
        )
    except RosterRemediationError as exc:
        raise RosterSyncError("projected candidate metadata is invalid") from exc
    return hydrated


def _verify_registered_projection(candidate: Mapping[str, Any]) -> None:
    projected = contract_for_projected_candidate(
        str(candidate.get("slug") or ""),
        str(candidate.get("hash") or ""),
    )
    source_hash = str(candidate.get("source_content_hash") or "")
    if projected is not None:
        source_hash = str(projected["source_content_hash"])
    contract = contract_for_source_hash(source_hash)
    if contract is None:
        return
    try:
        verify_projected_candidate_contract(
            candidate,
            source_hash=source_hash,
            relative_path=str(candidate.get("relative_path") or contract["relative_path"]),
        )
    except RosterRemediationError as exc:
        raise RosterSyncError("registered projected candidate contract is invalid") from exc


def _normalized_candidate_row(row: Any) -> dict[str, Any]:
    persisted = dict(row)
    content = _require_bounded_text(
        persisted.get("content"),
        MAX_AGENT_CONTENT_BYTES,
        f"quarantined agent {persisted.get('slug') or '<missing>'} content",
    )
    try:
        parsed = (
            parse_agent_file(
                content,
                inferred_division=str(persisted.get("division") or "") or None,
            )
            if content
            else {}
        )
    except RosterSyncError:
        raise
    except Exception as exc:
        raise RosterSyncError(
            f"quarantined agent {persisted.get('slug') or '<missing>'} cannot be parsed"
        ) from exc
    if (
        contract_for_projected_candidate(
            str(persisted.get("slug") or ""),
            str(persisted.get("hash") or ""),
        )
        is None
    ):
        item = {**parsed, **persisted}
    else:
        item = _with_projected_contract(persisted)
    item["description"] = str(item.get("description") or parsed.get("description") or "")
    for field in _LIST_FIELDS:
        item[field] = _json_list(
            item.get(field) or parsed.get(field),
            label=f"agent {field}",
        )
    item["prompt_body"] = str(item.get("prompt_body") or parsed.get("prompt_body") or content)
    item["content"] = content
    normalized = _normalize_agent(item)
    if str(item.get("hash") or "") != normalized["hash"]:
        raise RosterSyncError(f"quarantined agent {normalized['slug']} content hash does not match")
    if str(item.get("download_hash") or "") != normalized["hash"]:
        raise RosterSyncError(
            f"quarantined download for {normalized['slug']} content hash does not match"
        )
    normalized.pop("download_hash", None)
    normalized.pop("download_status", None)
    return normalized


def _load_candidate_agents(
    store: Store,
    candidate_ids: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    requested_ids: list[str] | None = None
    if candidate_ids is not None:
        requested_ids = [
            _require_bounded_text(item, MAX_SHORT_TEXT_BYTES, "candidate id")
            for item in candidate_ids
        ]
        if len(requested_ids) > MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(
                f"snapshot contains more than {MAX_SOURCE_CANDIDATES} candidate ids"
            )
        if len(set(requested_ids)) != len(requested_ids):
            raise RosterSyncError("snapshot candidate ids must be unique")
    conn = _connect(store)
    try:
        if requested_ids is None:
            cur = conn.execute(
                """
                SELECT c.*, d.source_id AS source_id, d.content, d.hash AS download_hash,
                       d.status AS download_status
                FROM agent_candidates c
                LEFT JOIN agent_downloads d ON d.id = c.download_id
                WHERE c.status IN ('approved', 'pending')
                ORDER BY CASE c.status WHEN 'approved' THEN 0 ELSE 1 END,
                         c.quarantined_at DESC
                LIMIT ?
                """,
                (MAX_SOURCE_CANDIDATES + 1,),
            )
        else:
            if not requested_ids:
                return []
            conn.execute(
                "CREATE TEMP TABLE requested_roster_candidates (id TEXT PRIMARY KEY) WITHOUT ROWID"
            )
            conn.executemany(
                "INSERT INTO requested_roster_candidates (id) VALUES (?)",
                ((item,) for item in requested_ids),
            )
            cur = conn.execute(
                """
                SELECT c.*, d.source_id AS source_id, d.content, d.hash AS download_hash,
                       d.status AS download_status
                FROM requested_roster_candidates requested
                JOIN agent_candidates c ON c.id = requested.id
                LEFT JOIN agent_downloads d ON d.id = c.download_id
                WHERE c.status IN ('approved', 'pending')
                ORDER BY CASE c.status WHEN 'approved' THEN 0 ELSE 1 END,
                         c.quarantined_at DESC
                LIMIT ?
                """,
                (MAX_SOURCE_CANDIDATES + 1,),
            )
        rows = cur.fetchall()
        if len(rows) > MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(f"snapshot contains more than {MAX_SOURCE_CANDIDATES} candidates")
        if requested_ids is not None:
            found_ids = {str(row["id"]) for row in rows}
            missing = [item for item in requested_ids if item not in found_ids]
            if missing:
                raise RosterSyncError(
                    "snapshot candidate ids are missing or no longer pending/approved"
                )
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            normalized = _normalized_candidate_row(row)
            if requested_ids is not None and normalized["slug"] in latest:
                raise RosterSyncError(
                    f"snapshot contains duplicate agent slug {normalized['slug']}"
                )
            latest.setdefault(normalized["slug"], normalized)
        return list(latest.values())
    finally:
        conn.close()


def _active_by_slug(store: Store) -> dict[str, dict[str, Any]]:
    return {agent["agent_slug"]: agent for agent in store.get_active_roster()}


def _active_fingerprint(active: Mapping[str, Mapping[str, Any]]) -> str:
    rows: list[dict[str, Any]] = []
    for slug, agent in sorted(active.items()):
        rows.append(
            {
                "slug": slug,
                "name": str(agent.get("name") or ""),
                "division": str(agent.get("division") or ""),
                "description": str(agent.get("description") or ""),
                "source": str(agent.get("source") or ""),
                "source_id": str(agent.get("source_id") or ""),
                "source_version": str(agent.get("source_version") or ""),
                "version": str(agent.get("version") or ""),
                "hash": str(agent.get("hash") or ""),
                "categories": sorted(
                    _json_list(agent.get("categories"), label="active categories")
                ),
                "capabilities": sorted(
                    _json_list(agent.get("capabilities"), label="active capabilities")
                ),
                "tool_affinity": sorted(
                    _json_list(agent.get("tool_affinity"), label="active tool affinity")
                ),
                "prompt_path": str(agent.get("prompt_path") or ""),
            }
        )
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return _hash_text(canonical)


def _active_agent_fingerprint(agent: Mapping[str, Any] | None) -> str | None:
    if agent is None:
        return None
    slug = agent_identity(agent)
    if not slug:
        raise RosterSyncError("active agent fingerprint requires a slug")
    return _active_fingerprint({slug: agent})


def _active_from_connection(conn: Any) -> dict[str, dict[str, Any]]:
    rows = conn.execute("SELECT * FROM agent_active ORDER BY agent_slug").fetchall()
    return {str(row["agent_slug"]): dict(row) for row in rows}


def _persist_snapshot_manifest(store: Store, manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        manifest_json = json.dumps(manifest, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise RosterSyncError("snapshot manifest is not JSON serializable") from exc
    manifest_size = _utf8_size(manifest_json)
    if manifest_size > MAX_SNAPSHOT_MANIFEST_BYTES:
        raise RosterSyncError(
            f"snapshot manifest is {manifest_size} bytes; "
            f"limit is {MAX_SNAPSHOT_MANIFEST_BYTES} bytes"
        )
    summary = project_snapshot_summary(manifest)
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise RosterSyncError("snapshot candidates must be a list")
    conn = _connect(store)
    try:
        conn.execute(
            "INSERT INTO agent_snapshots "
            "(id, snapshot_id, created_at, agent_count, manifest, activated, "
            "approved, added_count, changed_count, removed_count) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
            (
                _uuid(store),
                manifest["snapshot_id"],
                manifest["created_at"],
                len(candidates),
                manifest_json,
                int(bool(summary["approved"])),
                int(summary["added"]),
                int(summary["changed"]),
                int(summary["removed"]),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return manifest


def create_roster_diff(
    store: Store, candidate_ids: list[str] | tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Create a snapshot diff of quarantined/approved candidates vs active roster."""

    candidates = _load_candidate_agents(store, candidate_ids=candidate_ids)
    if len(candidates) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(
            f"snapshot contains {len(candidates)} candidates; limit is {MAX_SOURCE_CANDIDATES}"
        )
    candidate_content_bytes = sum(
        _utf8_size(str(agent.get("content") or ""))
        + _utf8_size(str(agent.get("prompt_body") or ""))
        for agent in candidates
    )
    if candidate_content_bytes > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(
            f"snapshot candidate content is {candidate_content_bytes} bytes; "
            f"limit is {MAX_TOTAL_SOURCE_BYTES} bytes"
        )
    active = _active_by_slug(store)
    candidate_by_slug = {agent["slug"]: agent for agent in candidates}
    added: list[str] = []
    removed: list[str] = []
    changed: dict[str, dict[str, Any]] = {}
    unchanged: list[str] = []

    for slug, candidate in candidate_by_slug.items():
        current = active.get(slug)
        if current is None:
            added.append(slug)
            continue
        prompt_changed = candidate.get("hash") != current.get("hash")
        metadata_changes = {
            field: {"from": current.get(field), "to": candidate.get(field)}
            for field in (*_METADATA_FIELDS, "source_id")
            if current.get(field) != candidate.get(field)
        }
        old_categories = sorted(_json_list(current.get("categories")))
        new_categories = sorted(_json_list(candidate.get("categories")))
        category_changes = (
            {"from": old_categories, "to": new_categories}
            if old_categories != new_categories
            else None
        )
        if prompt_changed or metadata_changes or category_changes:
            changed[slug] = {
                "prompt_body_changed": prompt_changed,
                "hash": {"from": current.get("hash"), "to": candidate.get("hash")},
                "metadata_changes": metadata_changes,
                "category_changes": category_changes,
            }
        else:
            unchanged.append(slug)

    snapshot_id = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    touched_basis = {
        slug: _active_agent_fingerprint(active.get(slug)) for slug in sorted(candidate_by_slug)
    }
    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": _now(),
        "approved": False,
        "active_basis": touched_basis,
        "candidate_ids": [str(agent.get("id")) for agent in candidates if agent.get("id")],
        "candidates": candidates,
        "retirements": [],
        "diff": {
            "added": sorted(added),
            "removed": sorted(removed),
            "changed": changed,
            "unchanged": sorted(unchanged),
        },
    }
    return _persist_snapshot_manifest(store, manifest)


def create_retirement_diff(
    store: Store,
    *,
    scan_id: str,
    slugs: Sequence[str],
) -> dict[str, Any]:
    """Create a reviewed retirement delta from latest complete scan evidence."""

    requested = [
        _require_bounded_text(slug, MAX_SHORT_TEXT_BYTES, "retirement slug").strip()
        for slug in slugs
    ]
    if not requested:
        raise RosterSyncError("retirement requires at least one agent slug")
    if len(requested) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError("retirement contains too many agent slugs")
    if len(set(requested)) != len(requested):
        raise RosterSyncError("retirement agent slugs must be unique")

    conn = _connect(store)
    try:
        conn.execute("BEGIN")
        scan = _validated_source_scan(conn, scan_id, require_latest=True)
        if str(scan.get("status") or "") != "complete":
            raise RosterSyncError(
                f"source scan {scan_id} is partial and cannot authorize retirement"
            )
        present_slugs = {
            str(entry.get("slug") or "") for entry in scan["entries"] if entry.get("slug")
        }
        active = _active_from_connection(conn)
        retirements: list[dict[str, str]] = []
        basis: dict[str, str] = {}
        for slug in sorted(requested):
            current = active.get(slug)
            if current is None:
                raise RosterSyncError(f"cannot retire inactive agent {slug}")
            if str(current.get("source_id") or "") != str(scan["source_id"]):
                raise RosterSyncError(f"agent {slug} is not owned by source scan {scan_id}")
            if slug in present_slugs:
                raise RosterSyncError(f"agent {slug} is still present in source scan {scan_id}")
            fingerprint = _active_agent_fingerprint(current)
            if fingerprint is None:
                raise RosterSyncError(f"agent {slug} has no active revision identity")
            basis[slug] = fingerprint
            retirements.append(
                {
                    "hash": str(current.get("hash") or ""),
                    "scan_id": str(scan["id"]),
                    "slug": slug,
                    "source_id": str(scan["source_id"]),
                    "version": str(current.get("version") or ""),
                }
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    snapshot_id = f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    return _persist_snapshot_manifest(
        store,
        {
            "snapshot_id": snapshot_id,
            "created_at": _now(),
            "approved": False,
            "active_basis": basis,
            "candidate_ids": [],
            "candidates": [],
            "retirements": retirements,
            "diff": {
                "added": [],
                "removed": sorted(requested),
                "changed": {},
                "unchanged": [],
            },
        },
    )


def _snapshot_manifest_lists(
    value: Any,
    *,
    snapshot_id: str,
    agent_count: int,
) -> tuple[dict[str, Any], list[Any], list[Any], list[Any]]:
    if not isinstance(value, dict):
        raise RosterSyncError(f"snapshot {snapshot_id} manifest must be an object")
    if value.get("snapshot_id") != snapshot_id:
        raise RosterSyncError(f"snapshot {snapshot_id} manifest identity does not match")
    if not isinstance(value.get("approved"), bool):
        raise RosterSyncError(f"snapshot {snapshot_id} approval state is invalid")
    raw_candidates = value.get("candidates")
    raw_ids = value.get("candidate_ids")
    raw_retirements = value.get("retirements", [])
    if not isinstance(raw_candidates, list) or not isinstance(raw_ids, list):
        raise RosterSyncError(f"snapshot {snapshot_id} candidate manifest is invalid")
    if not isinstance(raw_retirements, list):
        raise RosterSyncError(f"snapshot {snapshot_id} retirement manifest is invalid")
    if len(raw_candidates) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(
            f"snapshot contains {len(raw_candidates)} candidates; limit is {MAX_SOURCE_CANDIDATES}"
        )
    if agent_count != len(raw_candidates):
        raise RosterSyncError(f"snapshot {snapshot_id} agent count does not match its manifest")
    if len(raw_retirements) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError(f"snapshot {snapshot_id} contains too many retirements")
    return value, raw_candidates, raw_ids, raw_retirements


def _validated_manifest_candidate(
    raw_candidate: Any,
    *,
    snapshot_id: str,
) -> tuple[dict[str, Any], str, int]:
    if not isinstance(raw_candidate, dict):
        raise RosterSyncError(f"snapshot {snapshot_id} contains a non-object candidate")
    supplied_hash = str(raw_candidate.get("hash") or "")
    supplied_slug = str(raw_candidate.get("slug") or "")
    candidate = _normalize_agent(raw_candidate)
    _verify_registered_projection(candidate)
    ok, reason = validate_agent(candidate)
    if not ok:
        raise RosterSyncError(
            f"snapshot {snapshot_id} contains invalid agent "
            f"{candidate.get('slug') or '<missing>'}: {reason}"
        )
    if supplied_slug != candidate["slug"] or supplied_hash != candidate["hash"]:
        raise RosterSyncError(
            f"snapshot {snapshot_id} candidate identity or content hash does not match"
        )
    candidate_id = _require_bounded_text(
        candidate.get("id"), MAX_SHORT_TEXT_BYTES, "snapshot candidate id"
    )
    if not candidate_id:
        raise RosterSyncError(f"snapshot {snapshot_id} candidate id is missing")
    content_bytes = _utf8_size(candidate["content"]) + _utf8_size(candidate["prompt_body"])
    return candidate, candidate_id, content_bytes


def _validated_manifest_candidates(
    raw_candidates: Sequence[Any],
    *,
    snapshot_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    candidate_ids: list[str] = []
    content_bytes = 0
    for raw_candidate in raw_candidates:
        candidate, candidate_id, candidate_bytes = _validated_manifest_candidate(
            raw_candidate,
            snapshot_id=snapshot_id,
        )
        candidate_ids.append(candidate_id)
        candidates.append(candidate)
        content_bytes += candidate_bytes
    if content_bytes > MAX_TOTAL_SOURCE_BYTES:
        raise RosterSyncError(
            f"snapshot candidate content is {content_bytes} bytes; "
            f"limit is {MAX_TOTAL_SOURCE_BYTES} bytes"
        )
    return candidates, candidate_ids


def _validate_manifest_candidate_identity(
    candidates: Sequence[dict[str, Any]],
    candidate_ids: list[str],
    raw_ids: Sequence[Any],
    *,
    snapshot_id: str,
) -> None:
    manifest_ids = [
        _require_bounded_text(item, MAX_SHORT_TEXT_BYTES, "snapshot candidate id")
        for item in raw_ids
    ]
    if manifest_ids != candidate_ids:
        raise RosterSyncError(f"snapshot {snapshot_id} candidate ids do not match its candidates")
    if len(set(candidate_ids)) != len(candidate_ids):
        raise RosterSyncError(f"snapshot {snapshot_id} contains duplicate candidate ids")
    slugs = [candidate["slug"] for candidate in candidates]
    if len(set(slugs)) != len(slugs):
        raise RosterSyncError(f"snapshot {snapshot_id} contains duplicate agents")


def _validated_manifest_retirements(
    raw_retirements: Sequence[Any],
    *,
    snapshot_id: str,
) -> list[dict[str, str]]:
    retirements: list[dict[str, str]] = []
    slugs: set[str] = set()
    for raw in raw_retirements:
        if not isinstance(raw, Mapping):
            raise RosterSyncError(f"snapshot {snapshot_id} contains an invalid retirement")
        retirement = {
            field: _require_bounded_text(
                raw.get(field),
                MAX_SHORT_TEXT_BYTES,
                f"snapshot retirement {field}",
            )
            for field in ("hash", "scan_id", "slug", "source_id", "version")
        }
        if (
            not retirement["slug"]
            or not retirement["scan_id"]
            or not retirement["source_id"]
            or not retirement["version"]
            or not re.fullmatch(r"[a-f0-9]{64}", retirement["hash"])
        ):
            raise RosterSyncError(f"snapshot {snapshot_id} retirement identity is invalid")
        if retirement["slug"] in slugs:
            raise RosterSyncError(f"snapshot {snapshot_id} contains duplicate retirements")
        slugs.add(retirement["slug"])
        retirements.append(retirement)
    return retirements


def _validate_manifest_active_basis(
    value: Mapping[str, Any],
    snapshot_id: str,
    *,
    touched_slugs: set[str] | None = None,
) -> dict[str, str | None]:
    active_basis = value.get("active_basis")
    if not isinstance(active_basis, Mapping):
        raise RosterSyncError(f"snapshot {snapshot_id} active basis is invalid")
    normalized: dict[str, str | None] = {}
    for raw_slug, raw_fingerprint in active_basis.items():
        slug = _require_bounded_text(raw_slug, MAX_SHORT_TEXT_BYTES, "active basis slug")
        if raw_fingerprint is None:
            normalized[slug] = None
        elif re.fullmatch(r"[a-f0-9]{64}", str(raw_fingerprint)):
            normalized[slug] = str(raw_fingerprint)
        else:
            raise RosterSyncError(f"snapshot {snapshot_id} active basis is invalid")
    if touched_slugs is not None and set(normalized) != touched_slugs:
        raise RosterSyncError(f"snapshot {snapshot_id} active basis does not match its delta")
    return normalized


def _validated_snapshot_manifest(
    value: Any,
    *,
    snapshot_id: str,
    agent_count: int,
) -> dict[str, Any]:
    manifest, raw_candidates, raw_ids, raw_retirements = _snapshot_manifest_lists(
        value,
        snapshot_id=snapshot_id,
        agent_count=agent_count,
    )
    candidates, candidate_ids = _validated_manifest_candidates(
        raw_candidates,
        snapshot_id=snapshot_id,
    )
    _validate_manifest_candidate_identity(
        candidates,
        candidate_ids,
        raw_ids,
        snapshot_id=snapshot_id,
    )
    retirements = _validated_manifest_retirements(
        raw_retirements,
        snapshot_id=snapshot_id,
    )
    candidate_slugs = {candidate["slug"] for candidate in candidates}
    retirement_slugs = {retirement["slug"] for retirement in retirements}
    if candidate_slugs & retirement_slugs:
        raise RosterSyncError(f"snapshot {snapshot_id} both activates and retires an agent")
    active_basis = _validate_manifest_active_basis(
        manifest,
        snapshot_id,
        touched_slugs=candidate_slugs | retirement_slugs,
    )
    return {
        **manifest,
        "active_basis": active_basis,
        "candidate_ids": candidate_ids,
        "candidates": candidates,
        "retirements": retirements,
    }


def _snapshot_from_connection(conn: Any, snapshot_id: str) -> tuple[dict[str, Any], bool]:
    snapshot_id = _require_bounded_text(snapshot_id, MAX_SHORT_TEXT_BYTES, "snapshot id")
    row = conn.execute(
        "SELECT manifest, agent_count, activated FROM agent_snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"snapshot not found: {snapshot_id}")
    manifest_text = _require_bounded_text(
        row["manifest"] or "", MAX_SNAPSHOT_MANIFEST_BYTES, "snapshot manifest"
    )
    manifest = _load_json(manifest_text, f"snapshot {snapshot_id} manifest")
    agent_count = row["agent_count"]
    activated = row["activated"]
    if isinstance(agent_count, bool) or not isinstance(agent_count, int) or agent_count < 0:
        raise RosterSyncError(f"snapshot {snapshot_id} agent count is invalid")
    if isinstance(activated, bool) or not isinstance(activated, int) or activated not in {0, 1}:
        raise RosterSyncError(f"snapshot {snapshot_id} activation state is invalid")
    validated = _validated_snapshot_manifest(
        manifest,
        snapshot_id=snapshot_id,
        agent_count=agent_count,
    )
    return validated, bool(activated)


def _candidate_records(conn: Any, candidate_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS snapshot_candidate_ids (id TEXT PRIMARY KEY) WITHOUT ROWID"
    )
    conn.execute("DELETE FROM snapshot_candidate_ids")
    conn.executemany(
        "INSERT INTO snapshot_candidate_ids (id) VALUES (?)",
        ((item,) for item in candidate_ids),
    )
    rows = conn.execute(
        "SELECT c.*, d.source_id AS download_source_id, "
        "d.content AS download_content, d.hash AS download_hash, "
        "d.status AS download_status "
        "FROM snapshot_candidate_ids requested "
        "JOIN agent_candidates c ON c.id = requested.id "
        "LEFT JOIN agent_downloads d ON d.id = c.download_id"
    ).fetchall()
    return {str(row["id"]): dict(row) for row in rows}


def _assert_candidate_records(
    conn: Any,
    candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_statuses: frozenset[str],
) -> None:
    candidate_ids = [str(candidate["id"]) for candidate in candidates]
    records = _candidate_records(conn, candidate_ids)
    if set(records) != set(candidate_ids):
        raise RosterSyncError("snapshot candidate records are missing")
    for candidate in candidates:
        candidate_id = str(candidate["id"])
        record = records[candidate_id]
        if str(record.get("status") or "") not in allowed_statuses:
            raise RosterSyncError(f"snapshot candidate {candidate_id} is not in an allowed state")
        candidate_status = str(record.get("status") or "")
        expected_download_status = "activated" if candidate_status == "activated" else "quarantined"
        if str(record.get("download_status") or "") != expected_download_status:
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} download is not in an allowed state"
            )
        scalar_fields = (
            "download_id",
            "slug",
            "name",
            "description",
            "division",
            "prompt_path",
            "source",
            "source_version",
            "version",
            "hash",
        )
        scalar_mismatches = [
            field
            for field in scalar_fields
            if str(record.get(field) or "") != str(candidate.get(field) or "")
        ]
        if scalar_mismatches:
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} no longer matches quarantine: "
                f"{', '.join(scalar_mismatches)}"
            )
        if str(record.get("download_source_id") or "") != str(candidate.get("source_id") or ""):
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} source no longer matches quarantine"
            )
        for field in _LIST_FIELDS:
            if _json_list(record.get(field), label=f"candidate {field}") != list(
                candidate.get(field) or []
            ):
                raise RosterSyncError(
                    f"snapshot candidate {candidate_id} no longer matches quarantine"
                )
        content = str(candidate.get("content") or "")
        if str(record.get("download_content") or "") != content or str(
            record.get("download_hash") or ""
        ) != _hash_text(content):
            raise RosterSyncError(
                f"snapshot candidate {candidate_id} download content no longer matches"
            )


def _assert_retirement_evidence(
    conn: Any,
    retirements: Sequence[Mapping[str, str]],
) -> None:
    scans: dict[str, dict[str, Any]] = {}
    for retirement in retirements:
        scan_id = retirement["scan_id"]
        scan = scans.get(scan_id)
        if scan is None:
            scan = _validated_source_scan(conn, scan_id, require_latest=True)
            scans[scan_id] = scan
        if str(scan.get("status") or "") != "complete":
            raise RosterSyncError(
                f"source scan {scan_id} is partial and cannot authorize retirement"
            )
        if str(scan.get("source_id") or "") != retirement["source_id"]:
            raise RosterSyncError(f"retirement source does not match source scan {scan_id}")
        if any(str(entry.get("slug") or "") == retirement["slug"] for entry in scan["entries"]):
            raise RosterSyncError(
                f"agent {retirement['slug']} is still present in source scan {scan_id}"
            )
        active = conn.execute(
            "SELECT source_id, version, hash FROM agent_active WHERE agent_slug = ?",
            (retirement["slug"],),
        ).fetchone()
        if active is None:
            raise RosterSyncError(f"cannot retire inactive agent {retirement['slug']}")
        if (
            str(active["source_id"] or "") != retirement["source_id"]
            or str(active["version"] or "") != retirement["version"]
            or str(active["hash"] or "") != retirement["hash"]
        ):
            raise RosterSyncError(
                f"agent {retirement['slug']} no longer matches its retirement review"
            )


def _serialized_manifest(manifest: Mapping[str, Any]) -> str:
    try:
        value = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise RosterSyncError("snapshot manifest is not JSON serializable") from exc
    size = _utf8_size(value)
    if size > MAX_SNAPSHOT_MANIFEST_BYTES:
        raise RosterSyncError(
            f"snapshot manifest is {size} bytes; limit is {MAX_SNAPSHOT_MANIFEST_BYTES} bytes"
        )
    return value


def approve_snapshot(
    store: Store,
    snapshot_id: str,
    *,
    require_inference: bool = False,
) -> None:
    """Mark only the candidates captured by a roster snapshot as approved."""

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        manifest, activated = _snapshot_from_connection(conn, snapshot_id)
        if activated:
            raise RosterSyncError(f"snapshot {snapshot_id} is already activated")
        candidates = manifest["candidates"]
        retirements = manifest.get("retirements", [])
        if not candidates and not retirements:
            raise RosterSyncError(f"snapshot {snapshot_id} contains no agents or retirements")
        _assert_retirement_evidence(conn, retirements)
        if manifest["approved"]:
            if candidates:
                _assert_candidate_records(
                    conn,
                    candidates,
                    allowed_statuses=frozenset({"approved"}),
                )
                assert_candidate_audits_current(
                    conn,
                    candidates,
                    require_inference=require_inference,
                )
            conn.commit()
            return
        audit_ids: dict[str, str] = {}
        if candidates:
            _assert_candidate_records(conn, candidates, allowed_statuses=frozenset({"pending"}))
            audit_ids = assert_candidate_audits_current(
                conn,
                candidates,
                require_inference=require_inference,
            )
        manifest["approved"] = True
        manifest_json = _serialized_manifest(manifest)
        conn.execute(
            "UPDATE agent_snapshots SET manifest = ?, approved = 1 WHERE snapshot_id = ?",
            (manifest_json, snapshot_id),
        )
        for candidate in candidates:
            candidate_id = str(candidate["id"])
            conn.execute(
                "UPDATE agent_candidates SET status = 'approved' "
                "WHERE id = ? AND status = 'pending'",
                (candidate_id,),
            )
            record_candidate_status_event(
                conn,
                store,
                candidate_id,
                event_type="approved",
                from_status="pending",
                to_status="approved",
                reason=f"snapshot_id={snapshot_id}",
                audit_id=audit_ids[candidate_id],
            )
        _record_import_event(
            conn,
            store,
            "snapshot_approved",
            "",
            snapshot_authority_detail(
                snapshot_id=snapshot_id,
                manifest_json=manifest_json,
                audit_ids=audit_ids,
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _snapshot_targets_are_current(
    current_active: Mapping[str, Mapping[str, Any]],
    target_fingerprints: Mapping[str, str | None],
    retirements: Sequence[Mapping[str, str]],
) -> bool:
    return all(
        _active_agent_fingerprint(current_active.get(slug)) == fingerprint
        for slug, fingerprint in target_fingerprints.items()
    ) and all(retirement["slug"] not in current_active for retirement in retirements)


def _assert_snapshot_active_basis(
    snapshot_id: str,
    active_basis: Mapping[str, str | None],
    current_active: Mapping[str, Mapping[str, Any]],
) -> None:
    for slug, expected in active_basis.items():
        if _active_agent_fingerprint(current_active.get(slug)) != expected:
            raise RosterSyncError(
                f"snapshot {snapshot_id} was reviewed against a different revision of "
                f"{slug}; create and approve a new diff"
            )


def _preflight_candidate_versions(
    conn: Any,
    candidates: Sequence[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    existing_versions: set[tuple[str, str]] = set()
    for agent in candidates:
        slug = str(agent["slug"])
        version = str(agent["version"])
        if is_registered_encoding_intermediate(str(agent.get("content") or "")):
            raise RosterSyncError(f"refusing unprojected registered encoding repair for {slug}")
        safety = scan_source_text(str(agent.get("content") or ""))
        if safety.controls or safety.suspicious_encoding:
            raise RosterSyncError(f"refusing unsafe or corrupt roster content for {slug}")
        _verify_registered_projection(agent)
        row = conn.execute(
            "SELECT hash, content, metadata FROM agent_versions "
            "WHERE agent_slug = ? AND version = ?",
            (slug, version),
        ).fetchone()
        if row is None:
            continue
        existing_versions.add((slug, version))
        existing_hash = str(row["hash"] or "")
        candidate_hash = str(agent.get("hash") or "")
        if (
            existing_hash != candidate_hash
            or str(row["content"] or "") != str(agent.get("content") or "")
            or existing_hash != _hash_text(str(row["content"] or ""))
            or str(row["metadata"] or "") != serialized_revision_metadata(agent)
        ):
            raise RosterSyncError(
                f"refusing to replace immutable agent version {slug}@{version}: "
                f"existing hash {existing_hash}, candidate hash {candidate_hash}"
            )
    return existing_versions


def _apply_candidate_delta(
    conn: Any,
    store: Store,
    candidates: Sequence[Mapping[str, Any]],
    current_active: Mapping[str, Mapping[str, Any]],
    target_fingerprints: Mapping[str, str | None],
    existing_versions: set[tuple[str, str]],
) -> bool:
    changed = False
    for agent in candidates:
        slug = str(agent["slug"])
        version = str(agent["version"])
        if (slug, version) not in existing_versions:
            agent_version_id = _uuid(store)
            conn.execute(
                "INSERT INTO agent_versions "
                "(id, agent_slug, version, source_version, source_id, hash, content, "
                "metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_version_id,
                    slug,
                    version,
                    agent.get("source_version", ""),
                    agent.get("source_id", ""),
                    agent.get("hash", ""),
                    agent.get("content", ""),
                    serialized_revision_metadata(agent),
                    _now(),
                ),
            )
        else:
            agent_version_id = str(
                conn.execute(
                    "SELECT id FROM agent_versions WHERE agent_slug = ? AND version = ?",
                    (slug, version),
                ).fetchone()["id"]
            )
        if _active_agent_fingerprint(current_active.get(slug)) == target_fingerprints[slug]:
            continue
        changed = True
        conn.execute(
            "INSERT OR REPLACE INTO agent_active "
            "(id, agent_slug, name, division, description, source, source_id, "
            "source_version, version, hash, categories, capabilities, tool_affinity, "
            "prompt_path, activated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid(store),
                slug,
                agent.get("name", ""),
                agent.get("division", ""),
                agent.get("description", ""),
                agent.get("source", ""),
                agent.get("source_id", ""),
                agent.get("source_version", ""),
                version,
                agent.get("hash", ""),
                json.dumps(agent.get("categories", [])),
                json.dumps(agent.get("capabilities", [])),
                json.dumps(agent.get("tool_affinity", [])),
                agent.get("prompt_path", ""),
                _now(),
            ),
        )
        conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (slug,))
        conn.executemany(
            "INSERT INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
            ((_uuid(store), slug, category) for category in _json_list(agent.get("categories"))),
        )
        workforce_contract = project_workforce_contract(
            {
                **agent,
                "origin": "upstream",
                "employment": "employee",
                "enabled": True,
                "version_hash": str(agent.get("hash") or ""),
            },
            origin="upstream",
        )
        synchronize_active_workforce_worker(
            conn,
            agent_slug=slug,
            display_name=str(agent.get("name") or agent.get("display_name") or slug),
            origin="upstream",
            employment_class="employee",
            agent_version_id=agent_version_id,
            version=version,
            version_hash=str(agent.get("hash") or ""),
            recruitment_contract=json.dumps(
                workforce_contract.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
    return changed


def _apply_retirement_delta(
    conn: Any,
    store: Store,
    retirements: Sequence[Mapping[str, str]],
    current_active: Mapping[str, Mapping[str, Any]],
) -> bool:
    for retirement in retirements:
        slug = retirement["slug"]
        conn.execute(
            "INSERT INTO agent_retirements "
            "(id, agent_slug, source_id, version, hash, source_scan_id, "
            "active_record, retired_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid(store),
                slug,
                retirement["source_id"],
                retirement["version"],
                retirement["hash"],
                retirement["scan_id"],
                json.dumps(current_active[slug], sort_keys=True, separators=(",", ":")),
                _now(),
            ),
        )
        conn.execute("DELETE FROM agent_active WHERE agent_slug = ?", (slug,))
        conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (slug,))
        retire_ingested_workforce_worker(
            conn,
            agent_slug=slug,
            reason=f"upstream source retirement scan {retirement['scan_id']}",
        )
        _record_import_event(
            conn,
            store,
            "agent_retired",
            slug,
            json.dumps(
                {
                    "hash": retirement["hash"],
                    "scan_id": retirement["scan_id"],
                    "version": retirement["version"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    return bool(retirements)


def activate_snapshot(
    store: Store,
    snapshot_id: str,
    *,
    require_inference: bool = False,
) -> None:
    """Apply one approved per-agent delta without replacing unrelated roster state."""

    conn = _connect(store)
    try:
        conn.execute("BEGIN IMMEDIATE")
        manifest, previously_activated = _snapshot_from_connection(conn, snapshot_id)
        if not manifest["approved"]:
            raise RosterSyncError(f"snapshot {snapshot_id} must be approved before activation")
        candidates = manifest["candidates"]
        retirements = manifest.get("retirements", [])
        if not candidates and not retirements:
            raise RosterSyncError(f"snapshot {snapshot_id} contains no agents or retirements")
        if candidates:
            _assert_candidate_records(
                conn,
                candidates,
                allowed_statuses=frozenset({"approved", "activated"}),
            )
        current_active = _active_from_connection(conn)
        target_fingerprints = {
            candidate["slug"]: _active_agent_fingerprint(candidate) for candidate in candidates
        }
        if previously_activated:
            if _snapshot_targets_are_current(
                current_active,
                target_fingerprints,
                retirements,
            ):
                conn.commit()
                return
            raise RosterSyncError(
                f"snapshot {snapshot_id} is already activated but its touched agents changed"
            )
        audit_ids: dict[str, str] = {}
        if candidates:
            for candidate in candidates:
                refresh_candidate_audit_basis_in_connection(
                    conn,
                    store,
                    str(candidate["id"]),
                )
            try:
                audit_ids = assert_candidate_audits_current(
                    conn,
                    candidates,
                    require_inference=require_inference,
                )
            except RosterSyncError:
                # Persist the refreshed, immutable findings so operators can
                # inspect why activation stopped. No roster mutation has run.
                conn.commit()
                raise
        _assert_retirement_evidence(conn, retirements)
        _assert_snapshot_active_basis(snapshot_id, manifest["active_basis"], current_active)
        existing_versions = _preflight_candidate_versions(conn, candidates)
        changed = _apply_candidate_delta(
            conn,
            store,
            candidates,
            current_active,
            target_fingerprints,
            existing_versions,
        )
        changed |= _apply_retirement_delta(conn, store, retirements, current_active)
        for candidate in candidates:
            status_row = conn.execute(
                "SELECT status FROM agent_candidates WHERE id = ?",
                (candidate["id"],),
            ).fetchone()
            prior_status = str(status_row["status"] if status_row is not None else "")
            conn.execute(
                "UPDATE agent_candidates SET status = 'activated' WHERE id = ?",
                (candidate["id"],),
            )
            if prior_status != "activated":
                record_candidate_status_event(
                    conn,
                    store,
                    str(candidate["id"]),
                    event_type="activated",
                    from_status=prior_status,
                    to_status="activated",
                    reason=f"snapshot_id={snapshot_id}",
                    audit_id=audit_ids[str(candidate["id"])],
                )
        conn.executemany(
            "UPDATE agent_downloads SET status = 'activated' WHERE id = ?",
            ((candidate["download_id"],) for candidate in candidates),
        )
        conn.execute(
            "UPDATE agent_snapshots SET activated = 1 WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        manifest_row = conn.execute(
            "SELECT manifest FROM agent_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        if manifest_row is None:
            raise RosterSyncError(f"snapshot {snapshot_id} disappeared during activation")
        manifest_json = _require_bounded_text(
            manifest_row["manifest"] or "",
            MAX_SNAPSHOT_MANIFEST_BYTES,
            "snapshot manifest",
        )
        _record_import_event(
            conn,
            store,
            "snapshot_activated",
            "",
            snapshot_authority_detail(
                snapshot_id=snapshot_id,
                manifest_json=manifest_json,
                audit_ids=audit_ids,
            ),
        )
        if changed:
            conn.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
