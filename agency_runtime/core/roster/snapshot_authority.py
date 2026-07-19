"""Canonical content-free authority receipts for roster snapshot transitions."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.ingress import (
    MAX_SHORT_TEXT_BYTES,
    MAX_SNAPSHOT_MANIFEST_BYTES,
    MAX_SOURCE_CANDIDATES,
    RosterSyncError,
    _require_bounded_text,
)

SNAPSHOT_AUTHORITY_RECEIPT_SCHEMA = "agency.roster.snapshot_authority.v1"
MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES = 512 * 1024
_AUDIT_ID = re.compile(r"audit-[a-f0-9]{64}\Z")
_HEX_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_FIELDS = frozenset({"audit_ids", "manifest_hash", "receipt_schema", "snapshot_id"})


def _token(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise RosterSyncError(f"{label} must be text")
    token = _require_bounded_text(value, MAX_SHORT_TEXT_BYTES, label)
    if not token:
        raise RosterSyncError(f"{label} must not be empty")
    return token


def snapshot_manifest_hash(manifest_json: object) -> str:
    """Hash the exact bounded persisted manifest representation."""

    if not isinstance(manifest_json, str):
        raise RosterSyncError("snapshot manifest representation must be text")
    try:
        encoded = manifest_json.encode("utf-8")
    except UnicodeError as exc:
        raise RosterSyncError("snapshot manifest representation is invalid") from exc
    if not encoded or len(encoded) > MAX_SNAPSHOT_MANIFEST_BYTES:
        raise RosterSyncError("snapshot manifest representation is invalid or unbounded")
    return hashlib.sha256(encoded).hexdigest()


def _audit_id_map(
    audit_ids: Mapping[str, str],
    *,
    candidate_ids: Sequence[str] | None = None,
) -> dict[str, str]:
    if not isinstance(audit_ids, Mapping) or len(audit_ids) > MAX_SOURCE_CANDIDATES:
        raise RosterSyncError("snapshot authority audit identities are invalid or unbounded")
    normalized: dict[str, str] = {}
    for raw_candidate_id, raw_audit_id in audit_ids.items():
        candidate_id = _token(raw_candidate_id, "snapshot authority candidate id")
        audit_id = _token(raw_audit_id, "snapshot authority audit id")
        if not _AUDIT_ID.fullmatch(audit_id) or candidate_id in normalized:
            raise RosterSyncError("snapshot authority audit identities are invalid")
        normalized[candidate_id] = audit_id
    if candidate_ids is not None:
        if not isinstance(candidate_ids, Sequence) or isinstance(
            candidate_ids,
            (str, bytes, bytearray),
        ):
            raise RosterSyncError("snapshot authority candidate identities are invalid")
        expected = [_token(item, "snapshot candidate id") for item in candidate_ids]
        if len(expected) != len(set(expected)) or set(normalized) != set(expected):
            raise RosterSyncError("snapshot authority candidate identities do not match")
    return dict(sorted(normalized.items()))


def snapshot_authority_detail(
    *,
    snapshot_id: object,
    manifest_json: object,
    audit_ids: Mapping[str, str],
) -> str:
    """Serialize one canonical approval or activation authority receipt."""

    detail = {
        "audit_ids": _audit_id_map(audit_ids),
        "manifest_hash": snapshot_manifest_hash(manifest_json),
        "receipt_schema": SNAPSHOT_AUTHORITY_RECEIPT_SCHEMA,
        "snapshot_id": _token(snapshot_id, "snapshot authority id"),
    }
    serialized = json.dumps(
        detail,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if len(serialized.encode("utf-8")) > MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES:
        raise RosterSyncError("snapshot authority receipt exceeds its bound")
    return serialized


def validate_snapshot_authority_detail(
    value: object,
    *,
    snapshot_id: object,
    manifest_json: object,
    candidate_ids: Sequence[str],
) -> dict[str, str]:
    """Validate an exact receipt and return its candidate-to-audit bindings."""

    if not isinstance(value, str):
        raise RosterSyncError("snapshot authority receipt must be canonical text")
    try:
        detail = safe_load_bounded_json(
            value,
            maximum_bytes=MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES,
            maximum_depth=4,
            maximum_nodes=(MAX_SOURCE_CANDIDATES * 2) + 16,
        )
    except (TypeError, ValueError) as exc:
        raise RosterSyncError("snapshot authority receipt is invalid") from exc
    expected_snapshot_id = _token(snapshot_id, "snapshot authority id")
    if (
        not isinstance(detail, dict)
        or set(detail) != _FIELDS
        or detail.get("receipt_schema") != SNAPSHOT_AUTHORITY_RECEIPT_SCHEMA
        or detail.get("snapshot_id") != expected_snapshot_id
        or not isinstance(detail.get("manifest_hash"), str)
        or not _HEX_DIGEST.fullmatch(detail["manifest_hash"])
        or detail.get("manifest_hash") != snapshot_manifest_hash(manifest_json)
    ):
        raise RosterSyncError("snapshot authority receipt does not match its snapshot")
    raw_audit_ids = detail.get("audit_ids")
    if not isinstance(raw_audit_ids, Mapping):
        raise RosterSyncError("snapshot authority audit identities are invalid")
    audit_ids = _audit_id_map(
        raw_audit_ids,
        candidate_ids=candidate_ids,
    )
    canonical = snapshot_authority_detail(
        snapshot_id=expected_snapshot_id,
        manifest_json=manifest_json,
        audit_ids=audit_ids,
    )
    if value != canonical:
        raise RosterSyncError("snapshot authority receipt is not canonical")
    return audit_ids


__all__ = [
    "MAX_SNAPSHOT_AUTHORITY_RECEIPT_BYTES",
    "SNAPSHOT_AUTHORITY_RECEIPT_SCHEMA",
    "snapshot_authority_detail",
    "snapshot_manifest_hash",
    "validate_snapshot_authority_detail",
]
