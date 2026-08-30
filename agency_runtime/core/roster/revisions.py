"""Deterministic identities and metadata for immutable roster revisions."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json

IMMUTABLE_REVISION_PREFIX = "sha256:"
_REVISION_PATTERN = re.compile(r"sha256:[a-f0-9]{64}\Z")
_CONTENT_DIGEST_PATTERN = re.compile(r"(?:sha256:)?([a-f0-9]{64})\Z")
_LEGACY_SCALAR_METADATA_FIELDS = (
    "name",
    "division",
    "description",
    "source",
    "prompt_path",
)
_ROUTING_SCALAR_METADATA_FIELDS = (
    "authority",
    "context_mode",
    "independence_group",
    "expected_output_contract",
    "source_revision",
    "source_content_hash",
    "audit_revision",
    "audit_status",
)
_SCALAR_METADATA_FIELDS = (
    *_LEGACY_SCALAR_METADATA_FIELDS,
    *_ROUTING_SCALAR_METADATA_FIELDS,
)
_LEGACY_LIST_METADATA_FIELDS = ("categories", "capabilities", "tool_affinity")
_ROUTING_LIST_METADATA_FIELDS = (
    "anti_capabilities",
    "task_types",
    "preferred_when",
    "avoid_when",
    "required_tools",
    "optional_tools",
    "supported_hosts",
    "supported_platforms",
    "conflicts_with",
    "requires",
    "evidence_requirements",
    "model_requirements",
    "findings",
)
_LIST_METADATA_FIELDS = (
    *_LEGACY_LIST_METADATA_FIELDS,
    *_ROUTING_LIST_METADATA_FIELDS,
)
ROUTING_SCALAR_METADATA_FIELDS = _ROUTING_SCALAR_METADATA_FIELDS
ROUTING_LIST_METADATA_FIELDS = _ROUTING_LIST_METADATA_FIELDS
_MAX_METADATA_BYTES = 1024 * 1024
_json_dumps = json.dumps


def content_digest(content: object) -> str:
    """Return the canonical UTF-8 SHA-256 digest for prompt content."""

    return hashlib.sha256(str(content or "").encode("utf-8")).hexdigest()


def content_digest_identity(identity: object) -> str | None:
    """Return the bare digest from either supported SHA-256 identity form."""

    match = _CONTENT_DIGEST_PATTERN.fullmatch(str(identity or ""))
    return match.group(1) if match is not None else None


def content_identity_matches(content: object, identity: object) -> bool:
    """Verify digest-shaped identities while preserving legacy opaque tokens."""

    digest = content_digest_identity(identity)
    return digest is None or content_digest(content) == digest


def source_version(agent: Mapping[str, Any]) -> str:
    """Preserve an upstream semantic version separately from revision identity."""

    explicit = str(agent.get("source_version") or "").strip()
    if explicit:
        return explicit
    supplied = str(agent.get("version") or "").strip()
    if supplied and not _REVISION_PATTERN.fullmatch(supplied):
        return supplied
    return "1.0.0"


def revision_metadata(agent: Mapping[str, Any]) -> dict[str, Any]:
    """Project the behavior-bearing metadata needed for exact rollback."""

    projected: dict[str, Any] = {
        field: str(agent.get(field) or "") for field in _SCALAR_METADATA_FIELDS
    }
    projected["source_version"] = source_version(agent)
    for field in _LIST_METADATA_FIELDS:
        raw = agent.get(field)
        if isinstance(raw, (list, tuple)):
            projected[field] = [str(item) for item in raw if str(item)]
        elif isinstance(raw, str) and raw:
            projected[field] = [raw]
        else:
            projected[field] = []
    # Preserve every pre-optional-tools revision identity. An absent or empty
    # optional list has no behavior, so only contracts that declare optional
    # tools gain the new behavior-bearing metadata key.
    if not projected["optional_tools"]:
        projected.pop("optional_tools")
    return projected


def serialized_revision_metadata(agent: Mapping[str, Any]) -> str:
    """Serialize rollback metadata in a deterministic, bounded shape."""

    return _json_dumps(
        revision_metadata(agent),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def immutable_revision_version(agent: Mapping[str, Any]) -> str:
    """Derive an immutable revision identity from prompt and routing metadata."""

    identity = {
        "content_hash": str(agent.get("hash") or content_digest(agent.get("content"))),
        "metadata": revision_metadata(agent),
    }
    canonical = _json_dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return IMMUTABLE_REVISION_PREFIX + content_digest(canonical)


def decode_revision_metadata(value: object) -> dict[str, Any] | None:
    """Decode complete current metadata and safely project legacy revisions."""

    try:
        parsed = safe_load_bounded_json(
            value or "{}",
            maximum_bytes=_MAX_METADATA_BYTES,
            maximum_depth=8,
            maximum_nodes=1_000,
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    if any(field not in parsed for field in (*_LEGACY_SCALAR_METADATA_FIELDS, "source_version")):
        return None
    if any(not isinstance(parsed.get(field), str) for field in _LEGACY_SCALAR_METADATA_FIELDS):
        return None
    if not isinstance(parsed.get("source_version"), str):
        return None
    for field in _LEGACY_LIST_METADATA_FIELDS:
        items = parsed.get(field)
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            return None
    result = {
        field: parsed[field]
        for field in (
            *_LEGACY_SCALAR_METADATA_FIELDS,
            "source_version",
            *_LEGACY_LIST_METADATA_FIELDS,
        )
    }
    for field in _ROUTING_SCALAR_METADATA_FIELDS:
        item = parsed.get(field, "")
        if not isinstance(item, str):
            return None
        result[field] = item
    for field in _ROUTING_LIST_METADATA_FIELDS:
        items = parsed.get(field, [])
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            return None
        result[field] = items
    return result


__all__ = [
    "IMMUTABLE_REVISION_PREFIX",
    "ROUTING_LIST_METADATA_FIELDS",
    "ROUTING_SCALAR_METADATA_FIELDS",
    "content_digest",
    "content_identity_matches",
    "decode_revision_metadata",
    "immutable_revision_version",
    "revision_metadata",
    "serialized_revision_metadata",
    "source_version",
]
