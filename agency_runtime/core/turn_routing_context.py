"""Bounded same-session routing context for context-dependent turns.

The projection deliberately excludes prior user and assistant text. It carries
only correlation metadata, governed specialist-card hints, and closed workforce
unit descriptors from an already-validated preflight recipe.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from agency_runtime.core.correlation import validate_correlation_id

TURN_ROUTING_CONTEXT_VERSION = 1
TURN_ROUTING_CONTEXT_GUARD_VERSION = 1
MAX_TURN_CONTEXT_SPECIALISTS = 16
MAX_TURN_CONTEXT_CAPABILITIES = 4
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SUBJECT_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_SUBJECT_FIELDS = (
    "domains",
    "languages",
    "frameworks",
    "capability_ids",
    "platforms",
)


def _text(value: object, maximum: int) -> str:
    text = " ".join(str(value or "").split())
    text = "".join(character for character in text if character.isprintable())
    return text[:maximum]


def _capabilities(value: object) -> list[str] | None:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_TURN_CONTEXT_CAPABILITIES:
        return None
    result: list[str] = []
    for raw in value:
        item = _text(raw, 64)
        if not item or item in result:
            return None
        result.append(item)
    return result


def _specialists(value: object) -> list[dict[str, Any]] | None:
    if not isinstance(value, (list, tuple)) or len(value) > MAX_TURN_CONTEXT_SPECIALISTS:
        return None
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        slug = _text(raw.get("slug"), 128).casefold()
        capabilities = _capabilities(raw.get("capabilities", []))
        if _IDENTITY.fullmatch(slug) is None or slug in seen or capabilities is None:
            return None
        seen.add(slug)
        result.append(
            {
                "slug": slug,
                "description": _text(raw.get("description"), 256),
                "capabilities": capabilities,
            }
        )
    return result


def _subject_identifiers(value: object) -> list[str] | None:
    if not isinstance(value, (list, tuple)) or len(value) > 16:
        return None
    result: list[str] = []
    for raw in value:
        item = _text(raw, 128).casefold()
        if _SUBJECT_IDENTIFIER.fullmatch(item) is None or item in result:
            return None
        result.append(item)
    return result


def project_workforce_subject_hints(value: object) -> dict[str, list[str]] | None:
    """Validate closed semantic work-subject hints with no request prose."""

    if value in (None, {}):
        return {}
    if not isinstance(value, Mapping) or set(value) != set(_SUBJECT_FIELDS):
        return None
    projected = {field: _subject_identifiers(value.get(field)) for field in _SUBJECT_FIELDS}
    if any(item is None for item in projected.values()):
        return None
    return {field: list(projected[field] or []) for field in _SUBJECT_FIELDS}


def workforce_subject_hints_from_plan(value: object) -> dict[str, list[str]] | None:
    """Extract only typed identifier fields from one verified workforce plan."""

    if value is None:
        return {}
    if not isinstance(value, Mapping):
        return None
    raw_units = value.get("units")
    if not isinstance(raw_units, (list, tuple)) or not 1 <= len(raw_units) <= 16:
        return None
    collected = {field: [] for field in _SUBJECT_FIELDS}
    source_fields = {
        "domains": "domains",
        "languages": "languages",
        "frameworks": "frameworks",
        "capability_ids": "required_capabilities",
        "platforms": "platforms",
    }
    for raw_unit in raw_units:
        if not isinstance(raw_unit, Mapping):
            return None
        for target, source in source_fields.items():
            values = _subject_identifiers(raw_unit.get(source, []))
            if values is None:
                return None
            for item in values:
                if item not in collected[target] and len(collected[target]) < 16:
                    collected[target].append(item)
    return project_workforce_subject_hints(collected)


def project_turn_routing_context(value: object) -> dict[str, Any] | None:
    """Validate one transcript-free context projection or return ``None``."""

    from agency_runtime.core.workforce.routing_projection import (
        project_workforce_unit_descriptors,
    )

    if value in (None, {}):
        return {}
    if (
        not isinstance(value, Mapping)
        or value.get("context_version") != TURN_ROUTING_CONTEXT_VERSION
    ):
        return None
    try:
        source_trace_id = validate_correlation_id(
            str(value.get("source_trace_id") or ""),
            field="source_trace_id",
        )
    except ValueError:
        return None
    specialists = _specialists(value.get("specialists", []))
    descriptors = project_workforce_unit_descriptors(value.get("workforce_unit_descriptors", []))
    subject_hints = project_workforce_subject_hints(value.get("workforce_subject_hints", {}))
    source_status = _text(value.get("source_status"), 64).casefold()
    source_turn_kind = _text(value.get("source_turn_kind"), 32).casefold()
    if (
        specialists is None
        or descriptors is None
        or subject_hints is None
        or not source_status
        or not source_turn_kind
    ):
        return None
    return {
        "context_version": TURN_ROUTING_CONTEXT_VERSION,
        "source_trace_id": source_trace_id,
        "source_status": source_status,
        "source_turn_kind": source_turn_kind,
        "specialists": specialists,
        "workforce_unit_descriptors": descriptors,
        "workforce_subject_hints": subject_hints,
    }


def turn_routing_context_from_recipe(
    recipe: Mapping[str, Any],
    *,
    source_trace_id: str,
    source_status: str,
    source_turn_kind: str,
) -> dict[str, Any]:
    """Project context from one already-validated same-session recipe."""

    routing = recipe.get("routing")
    routing = routing if isinstance(routing, Mapping) else {}
    selected = {
        str(slug or "").strip().casefold()
        for slug in routing.get("selected_ids", [])
        if str(slug or "").strip()
    }
    raw_references = recipe.get("selection_refs")
    references = raw_references if isinstance(raw_references, list) else []
    specialists = [
        {
            "slug": str(reference.get("slug") or ""),
            "description": str(reference.get("description") or ""),
            "capabilities": list(reference.get("capabilities") or []),
        }
        for reference in references
        if isinstance(reference, Mapping)
        and str(reference.get("slug") or "").strip().casefold() in selected
    ]
    projected = project_turn_routing_context(
        {
            "context_version": TURN_ROUTING_CONTEXT_VERSION,
            "source_trace_id": source_trace_id,
            "source_status": source_status,
            "source_turn_kind": source_turn_kind,
            "specialists": specialists,
            "workforce_unit_descriptors": routing.get("workforce_unit_descriptors", []),
            "workforce_subject_hints": routing.get("workforce_subject_hints", {}),
        }
    )
    return projected or {}


def project_turn_routing_context_guard(value: object) -> dict[str, Any] | None:
    """Validate the source-state compare-and-set for contextual routing."""

    if value in (None, {}):
        return {}
    if (
        not isinstance(value, Mapping)
        or value.get("guard_version") != TURN_ROUTING_CONTEXT_GUARD_VERSION
    ):
        return None
    try:
        source_trace_id = validate_correlation_id(
            str(value.get("source_trace_id") or ""),
            field="source_trace_id",
        )
    except ValueError:
        return None
    source_turn_sequence = value.get("source_turn_sequence")
    source_evidence_revision = value.get("source_evidence_revision")
    source_roster_generation = value.get("source_roster_generation")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < minimum
        for item, minimum in (
            (source_turn_sequence, 1),
            (source_evidence_revision, 1),
            (source_roster_generation, 0),
        )
    ):
        return None
    digests = {
        field: str(value.get(field) or "").strip().casefold()
        for field in ("source_recipe_digest", "source_context_revision")
    }
    if any(re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in digests.values()):
        return None
    return {
        "guard_version": TURN_ROUTING_CONTEXT_GUARD_VERSION,
        "source_trace_id": source_trace_id,
        "source_turn_sequence": source_turn_sequence,
        "source_evidence_revision": source_evidence_revision,
        "source_roster_generation": source_roster_generation,
        **digests,
    }


def terminal_turn_context_passthrough(status: str, metadata: Mapping[str, Any]) -> bool:
    """Return whether a terminal non-work turn may not mask older work."""

    if status in {"active", "evidence_only", "abandoned"} or str(
        metadata.get("pending_interaction") or ""
    ):
        return False
    turn_kind = str(metadata.get("turn_kind") or "")
    selection_required = metadata.get("selection_required")
    execution_required = metadata.get("execution_decision_required")
    advisory = selection_required is True and execution_required is False
    legacy_nonwork = (
        turn_kind in {"acknowledgement", "conversation", "control"}
        and selection_required is not True
        and execution_required is not True
    )
    return advisory or legacy_nonwork


def turn_routing_context_revision(value: object) -> str:
    """Return the canonical digest for a valid nonempty context projection."""

    projected = project_turn_routing_context(value)
    if not projected:
        return ""
    encoded = json.dumps(
        projected,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


__all__ = [
    "MAX_TURN_CONTEXT_SPECIALISTS",
    "TURN_ROUTING_CONTEXT_GUARD_VERSION",
    "TURN_ROUTING_CONTEXT_VERSION",
    "project_turn_routing_context",
    "project_turn_routing_context_guard",
    "project_workforce_subject_hints",
    "terminal_turn_context_passthrough",
    "turn_routing_context_from_recipe",
    "turn_routing_context_revision",
    "workforce_subject_hints_from_plan",
]
