"""Fail-closed authority checks for active and historical roster revisions."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.bundled import bundled_manifest, bundled_roster
from agency_runtime.core.roster.ingress import (
    MAX_SHORT_TEXT_BYTES,
    RosterSyncError,
    _require_bounded_text,
)
from agency_runtime.core.roster.revisions import (
    content_digest,
    decode_revision_metadata,
    serialized_revision_metadata,
)
from agency_runtime.core.roster.snapshot_authority import (
    MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES,
    validate_snapshot_authority_detail,
)

_AUTHORITY_EVENT_LIMIT = 4
_HEX_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_REVISION_ID = re.compile(r"sha256:[a-f0-9]{64}\Z")
_ACTIVE_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")


@dataclass(frozen=True, slots=True)
class RevisionActivationAuthority:
    """Canonical identity of every record authorizing one historical revision."""

    kind: str
    projection: tuple[tuple[str, str], ...]
    digest: str


def _canonical_digest(label: str, value: object) -> str:
    document = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(label.encode("ascii") + b"\0" + document).hexdigest()


def _mapping_digest(label: str, value: Mapping[str, Any]) -> str:
    return _canonical_digest(label, dict(value))


def _authority_evidence(
    kind: str,
    values: Mapping[str, object],
) -> RevisionActivationAuthority:
    projection = tuple(sorted((str(key), str(value)) for key, value in values.items()))
    if not kind or len(projection) != len(values):  # pragma: no cover - internal contract
        raise RuntimeError("activation authority projection is invalid")
    digest = _canonical_digest(
        "agency.revision-activation-authority.v1",
        {"kind": kind, "projection": projection},
    )
    return RevisionActivationAuthority(kind=kind, projection=projection, digest=digest)


def _strict_text(
    value: object,
    *,
    label: str,
    maximum: int = MAX_SHORT_TEXT_BYTES,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} is invalid")
    try:
        text = _require_bounded_text(value, maximum, label)
    except (RosterSyncError, TypeError, UnicodeError) as exc:
        raise ValueError(f"{label} is invalid") from exc
    if not allow_empty and not text:
        raise ValueError(f"{label} is invalid")
    return text


def _timestamp(value: object) -> datetime:
    text = _strict_text(value, label="activation authority timestamp")
    try:
        timestamp = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("activation authority timestamp is invalid") from exc
    if timestamp.tzinfo is None:
        raise ValueError("activation authority timestamp is invalid")
    return timestamp


def _strict_json_string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is invalid")
    try:
        parsed = safe_load_bounded_json(
            value,
            maximum_bytes=1024 * 1024,
            maximum_depth=4,
            maximum_nodes=1_000,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is invalid") from exc
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise ValueError(f"{label} is invalid")
    return parsed


def assert_active_revision_projection(
    active: Mapping[str, Any],
    revision: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an active row to be the exact projection of its immutable revision."""

    metadata = decode_revision_metadata(revision.get("metadata"))
    slug = str(revision.get("agent_slug") or "")
    version = str(revision.get("version") or "")
    if metadata is None:
        raise ValueError(f"revision {slug}@{version} predates exact activation metadata")
    if (
        serialized_revision_metadata(metadata) != str(revision.get("metadata") or "")
        or str(revision.get("source_version") or "") != metadata["source_version"]
    ):
        raise ValueError(f"revision metadata integrity failed: {slug}@{version}")
    content = str(revision.get("content") or "")
    revision_hash = str(revision.get("hash") or "")
    if (
        not content
        or not _HEX_DIGEST.fullmatch(revision_hash)
        or content_digest(content) != revision_hash
    ):
        raise ValueError(f"revision integrity failed: {slug}@{version}")
    expected_scalars = {
        "agent_slug": slug,
        "name": metadata["name"],
        "division": metadata["division"],
        "description": metadata["description"],
        "source": metadata["source"],
        "source_id": str(revision.get("source_id") or ""),
        "source_version": str(revision.get("source_version") or metadata["source_version"]),
        "version": version,
        "hash": revision_hash,
        "prompt_path": metadata["prompt_path"],
    }
    if any(
        str(active.get(field) or "") != expected for field, expected in expected_scalars.items()
    ):
        raise ValueError(f"active revision projection failed: {slug}@{version}")
    for field in _ACTIVE_LIST_FIELDS:
        if (
            _strict_json_string_list(
                active.get(field),
                label=f"active {field}",
            )
            != metadata[field]
        ):
            raise ValueError(f"active revision projection failed: {slug}@{version}")
    return metadata


def _matches_current_bundled_revision(
    *,
    slug: str,
    revision: Mapping[str, Any],
    content: str,
) -> bool:
    for canonical in bundled_roster():
        if canonical["slug"] != slug:
            continue
        return (
            str(revision.get("version") or "") == canonical["version"]
            and str(revision.get("hash") or "") == canonical["hash"]
            and str(revision.get("source_id") or "") == canonical["source_id"]
            and str(revision.get("source_version") or "") == canonical["source_version"]
            and content == canonical["prompt_body"]
            and str(revision.get("metadata") or "") == serialized_revision_metadata(canonical)
        )
    return False


def _authority_events(
    conn: Any,
    *,
    candidate_id: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    rows = conn.execute(
        "SELECT id AS event_id, rowid AS event_rowid, event_type, from_status, to_status, "
        "reason, audit_id, created_at "
        "FROM agent_candidate_status_events "
        "WHERE candidate_id = ? AND event_type IN ('approved', 'activated') "
        "ORDER BY rowid LIMIT ?",
        (candidate_id, _AUTHORITY_EVENT_LIMIT + 1),
    ).fetchall()
    if len(rows) != 2:
        raise ValueError("candidate activation authority is missing or ambiguous")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        event["event_id"] = _strict_text(
            event.get("event_id"),
            label="candidate activation event id",
        )
        event["event_type"] = _strict_text(
            event.get("event_type"),
            label="candidate activation event type",
        )
        event["from_status"] = _strict_text(
            event.get("from_status"),
            label="candidate activation prior status",
        )
        event["to_status"] = _strict_text(
            event.get("to_status"),
            label="candidate activation status",
        )
        event["reason"] = _strict_text(
            event.get("reason"),
            label="candidate activation reason",
            maximum=2_048,
        )
        event["audit_id"] = _strict_text(
            event.get("audit_id"),
            label="candidate activation audit id",
        )
        _event_order(event, rowid_field="event_rowid")
        normalized.append(event)
    by_type = {row["event_type"]: row for row in normalized}
    if len(by_type) != 2 or set(by_type) != {"approved", "activated"}:
        raise ValueError("candidate activation authority is missing or ambiguous")
    approved = by_type["approved"]
    activated = by_type["activated"]
    approved_timestamp, approved_rowid = _event_order(approved, rowid_field="event_rowid")
    activated_timestamp, activated_rowid = _event_order(
        activated,
        rowid_field="event_rowid",
    )
    if (
        approved["from_status"] != "pending"
        or approved["to_status"] != "approved"
        or activated["from_status"] != "approved"
        or activated["to_status"] != "activated"
        or approved["reason"] != activated["reason"]
        or approved_rowid >= activated_rowid
        or approved_timestamp > activated_timestamp
    ):
        raise ValueError("candidate activation transitions are invalid")
    reason = approved["reason"]
    prefix = "snapshot_id="
    if not reason.startswith(prefix) or reason == prefix:
        raise ValueError("candidate activation snapshot binding is invalid")
    snapshot_id = _strict_text(
        reason.removeprefix(prefix),
        label="candidate activation snapshot binding",
    )
    return approved, activated, snapshot_id


def _assert_bound_audit(
    conn: Any,
    *,
    event: Mapping[str, Any],
    candidate_id: str,
    candidate_version: str,
    candidate_hash: str,
) -> Mapping[str, Any]:
    # Import lazily because roster.review imports Store during module initialization.
    from agency_runtime.core.roster.review import assert_bound_candidate_audit_from_connection

    audit_id = event["audit_id"]
    if not isinstance(audit_id, str):
        raise ValueError("candidate activation audit binding is invalid")
    try:
        audit, _policy_current = assert_bound_candidate_audit_from_connection(
            conn,
            audit_id=audit_id,
            candidate_id=candidate_id,
            candidate_version=candidate_version,
            candidate_hash=candidate_hash,
            require_current_policy=True,
        )
    except (KeyError, RosterSyncError, ValueError) as exc:
        raise ValueError("candidate activation audit binding is invalid") from exc
    if _timestamp(audit["created_at"]) > _timestamp(event["created_at"]):
        raise ValueError("candidate activation audit binding is invalid")
    return audit


def _event_order(event: Mapping[str, Any], *, rowid_field: str) -> tuple[datetime, int]:
    rowid = event[rowid_field]
    timestamp = _timestamp(event["created_at"])
    if (
        timestamp.tzinfo is None
        or isinstance(rowid, bool)
        or not isinstance(rowid, int)
        or rowid < 1
    ):
        raise ValueError("activation authority event ordering is invalid")
    return timestamp, rowid


def _snapshot_events(
    conn: Any,
    *,
    snapshot_id: str,
    manifest_json: str,
    candidate_ids: list[str],
    candidate_id: str,
    approved_audit_id: str,
    activated_audit_id: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    invalid_detail = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE event_type IN ('snapshot_approved', 'snapshot_activated') "
        "AND (typeof(detail) <> 'text' OR length(CAST(detail AS BLOB)) > ?) LIMIT 1",
        (MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES,),
    ).fetchone()
    if invalid_detail is not None:
        raise ValueError("snapshot activation authority contains unsafe event detail")
    invalid_json = conn.execute(
        "SELECT 1 FROM agent_import_events "
        "WHERE event_type IN ('snapshot_approved', 'snapshot_activated') "
        "AND NOT json_valid(detail) LIMIT 1"
    ).fetchone()
    if invalid_json is not None:
        raise ValueError("snapshot activation authority contains invalid event detail")
    rows = conn.execute(
        "SELECT id AS event_id, event_sequence AS import_event_sequence, "
        "event_type, agent_slug, "
        "detail, created_at "
        "FROM agent_import_events "
        "WHERE event_type IN ('snapshot_approved', 'snapshot_activated') "
        "AND json_extract(detail, '$.snapshot_id') = ? "
        "ORDER BY event_sequence LIMIT ?",
        (
            snapshot_id,
            _AUTHORITY_EVENT_LIMIT + 1,
        ),
    ).fetchall()
    if len(rows) != 2:
        raise ValueError("snapshot activation authority is missing or ambiguous")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        event["event_id"] = _strict_text(
            event.get("event_id"),
            label="snapshot activation event id",
        )
        event["event_type"] = _strict_text(
            event.get("event_type"),
            label="snapshot activation event type",
        )
        event["agent_slug"] = _strict_text(
            event.get("agent_slug"),
            label="snapshot activation agent slug",
            allow_empty=True,
        )
        event["detail"] = _strict_text(
            event.get("detail"),
            label="snapshot activation detail",
            maximum=MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES,
        )
        _event_order(event, rowid_field="import_event_sequence")
        normalized.append(event)
    by_type = {row["event_type"]: row for row in normalized}
    if len(by_type) != 2 or set(by_type) != {"snapshot_approved", "snapshot_activated"}:
        raise ValueError("snapshot activation authority is missing or ambiguous")
    approved = by_type["snapshot_approved"]
    activated = by_type["snapshot_activated"]
    approved_timestamp, approved_rowid = _event_order(
        approved,
        rowid_field="import_event_sequence",
    )
    activated_timestamp, activated_rowid = _event_order(
        activated,
        rowid_field="import_event_sequence",
    )
    if (
        approved["agent_slug"]
        or activated["agent_slug"]
        or approved_rowid >= activated_rowid
        or approved_timestamp > activated_timestamp
    ):
        raise ValueError("snapshot activation authority is invalid")
    try:
        approved_ids = validate_snapshot_authority_detail(
            approved["detail"],
            snapshot_id=snapshot_id,
            manifest_json=manifest_json,
            candidate_ids=candidate_ids,
        )
        activated_ids = validate_snapshot_authority_detail(
            activated["detail"],
            snapshot_id=snapshot_id,
            manifest_json=manifest_json,
            candidate_ids=candidate_ids,
        )
    except RosterSyncError as exc:
        raise ValueError("snapshot activation authority is invalid") from exc
    if (
        approved_ids.get(candidate_id) != approved_audit_id
        or activated_ids.get(candidate_id) != activated_audit_id
    ):
        raise ValueError("snapshot activation audit identities do not match")
    return approved, activated


def _assert_candidate_snapshot_authority(
    conn: Any,
    *,
    slug: str,
    revision: Mapping[str, Any],
    content: str,
) -> RevisionActivationAuthority:
    candidate_version = str(revision.get("version") or "")
    candidate_hash = str(revision.get("hash") or "")
    candidates = conn.execute(
        "SELECT id FROM agent_candidates "
        "WHERE slug = ? AND version = ? AND hash = ? AND status = 'activated' "
        "ORDER BY id LIMIT 3",
        (slug, candidate_version, candidate_hash),
    ).fetchall()
    if len(candidates) != 1:
        raise ValueError("candidate activation authority is missing or ambiguous")
    candidate_id = str(candidates[0]["id"])
    approved_event, activated_event, snapshot_id = _authority_events(
        conn,
        candidate_id=candidate_id,
    )
    approved_audit = _assert_bound_audit(
        conn,
        event=approved_event,
        candidate_id=candidate_id,
        candidate_version=candidate_version,
        candidate_hash=candidate_hash,
    )
    activated_audit = _assert_bound_audit(
        conn,
        event=activated_event,
        candidate_id=candidate_id,
        candidate_version=candidate_version,
        candidate_hash=candidate_hash,
    )

    # Import lazily because roster.sync imports Store during module initialization.
    from agency_runtime.core.roster.sync import (
        _assert_candidate_records,
        _snapshot_from_connection,
    )

    snapshot_row = conn.execute(
        "SELECT * FROM agent_snapshots WHERE snapshot_id = ? LIMIT 1",
        (snapshot_id,),
    ).fetchone()
    if snapshot_row is None or snapshot_row["approved"] != 1 or snapshot_row["activated"] != 1:
        raise ValueError("snapshot activation authority is invalid")
    try:
        manifest, activated = _snapshot_from_connection(conn, snapshot_id)
    except (KeyError, RosterSyncError) as exc:
        raise ValueError("snapshot activation authority is invalid") from exc
    if not manifest["approved"] or not activated:
        raise ValueError("snapshot activation authority is invalid")
    matches = [
        candidate
        for candidate in manifest["candidates"]
        if str(candidate.get("id") or "") == candidate_id
    ]
    if len(matches) != 1:
        raise ValueError("snapshot candidate authority is missing or ambiguous")
    candidate = matches[0]
    try:
        _assert_candidate_records(
            conn,
            [candidate],
            allowed_statuses=frozenset({"activated"}),
        )
    except RosterSyncError as exc:
        raise ValueError("snapshot candidate authority is invalid") from exc
    if (
        str(candidate.get("slug") or "") != slug
        or str(candidate.get("version") or "") != candidate_version
        or str(candidate.get("hash") or "") != candidate_hash
        or str(candidate.get("content") or "") != content
        or str(candidate.get("source_id") or "") != str(revision.get("source_id") or "")
        or str(candidate.get("source_version") or "") != str(revision.get("source_version") or "")
        or serialized_revision_metadata(candidate) != str(revision.get("metadata") or "")
        or slug not in manifest["active_basis"]
    ):
        raise ValueError("snapshot candidate authority does not match the revision")
    snapshot_approved, snapshot_activated = _snapshot_events(
        conn,
        snapshot_id=snapshot_id,
        manifest_json=str(snapshot_row["manifest"] or ""),
        candidate_ids=[str(item.get("id") or "") for item in manifest["candidates"]],
        candidate_id=candidate_id,
        approved_audit_id=str(approved_event["audit_id"] or ""),
        activated_audit_id=str(activated_event["audit_id"] or ""),
    )
    phase_timestamps = (
        _timestamp(approved_event["created_at"]),
        _timestamp(snapshot_approved["created_at"]),
        _timestamp(activated_event["created_at"]),
        _timestamp(snapshot_activated["created_at"]),
    )
    if tuple(sorted(phase_timestamps)) != phase_timestamps:
        raise ValueError("candidate and snapshot activation event order is invalid")
    candidate_row = conn.execute(
        "SELECT * FROM agent_candidates WHERE id = ? LIMIT 1",
        (candidate_id,),
    ).fetchone()
    if candidate_row is None:  # pragma: no cover - guarded by _assert_candidate_records
        raise ValueError("snapshot candidate authority is missing")
    manifest_json = str(snapshot_row["manifest"] or "")
    return _authority_evidence(
        "snapshot",
        {
            "candidate_id": candidate_id,
            "candidate_record_digest": _mapping_digest(
                "agency.activation-authority.candidate-record.v1",
                dict(candidate_row),
            ),
            "candidate_manifest_digest": _mapping_digest(
                "agency.activation-authority.candidate-manifest.v1",
                candidate,
            ),
            "candidate_approved_audit_id": str(approved_audit["id"]),
            "candidate_approved_audit_digest": _mapping_digest(
                "agency.activation-authority.candidate-audit.v1",
                approved_audit,
            ),
            "candidate_activated_audit_id": str(activated_audit["id"]),
            "candidate_activated_audit_digest": _mapping_digest(
                "agency.activation-authority.candidate-audit.v1",
                activated_audit,
            ),
            "candidate_approved_event_id": str(approved_event["event_id"]),
            "candidate_approved_event_digest": _mapping_digest(
                "agency.activation-authority.candidate-event.v1",
                approved_event,
            ),
            "candidate_activated_event_id": str(activated_event["event_id"]),
            "candidate_activated_event_digest": _mapping_digest(
                "agency.activation-authority.candidate-event.v1",
                activated_event,
            ),
            "snapshot_id": snapshot_id,
            "snapshot_manifest_digest": _canonical_digest(
                "agency.activation-authority.snapshot-manifest.v1",
                manifest_json,
            ),
            "snapshot_record_digest": _mapping_digest(
                "agency.activation-authority.snapshot-record.v1",
                dict(snapshot_row),
            ),
            "snapshot_approved_event_id": str(snapshot_approved["event_id"]),
            "snapshot_approved_event_digest": _mapping_digest(
                "agency.activation-authority.snapshot-event.v1",
                snapshot_approved,
            ),
            "snapshot_activated_event_id": str(snapshot_activated["event_id"]),
            "snapshot_activated_event_digest": _mapping_digest(
                "agency.activation-authority.snapshot-event.v1",
                snapshot_activated,
            ),
        },
    )


def assert_revision_activation_authority(
    conn: Any,
    *,
    slug: str,
    revision: Mapping[str, Any],
) -> RevisionActivationAuthority:
    """Require an exact current bundle or an activated approved snapshot candidate."""

    content = str(revision.get("content") or "")
    revision_hash = str(revision.get("hash") or "")
    version = str(revision.get("version") or "")
    if (
        not content
        or not _HEX_DIGEST.fullmatch(revision_hash)
        or not _REVISION_ID.fullmatch(version)
        or content_digest(content) != revision_hash
    ):
        raise ValueError(f"revision activation authority is invalid: {slug}@{version}")
    if _matches_current_bundled_revision(slug=slug, revision=revision, content=content):
        return _authority_evidence(
            "bundled",
            {
                "manifest_digest": _canonical_digest(
                    "agency.activation-authority.bundled-manifest.v1",
                    bundled_manifest(),
                ),
                "revision_digest": _mapping_digest(
                    "agency.activation-authority.bundled-revision.v1",
                    revision,
                ),
            },
        )
    return _assert_candidate_snapshot_authority(
        conn,
        slug=slug,
        revision=revision,
        content=content,
    )


__all__ = [
    "RevisionActivationAuthority",
    "assert_active_revision_projection",
    "assert_revision_activation_authority",
]
