"""Shared controlled capability vocabulary for planning and recruitment."""

from __future__ import annotations

import re
from collections.abc import Sequence

# A governed specialist can own several lifecycle and assurance capabilities
# without becoming generic. Keep the projection tightly bounded while allowing
# cross-cutting audited roles to retain every independently verified controlled
# capability instead of dropping one at the contract boundary.
MAX_CAPABILITY_IDS = 12
_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9-]{0,127}")

# These are the stable cross-roster task capabilities currently produced by
# the audit/ingestion pipeline. Agency-owned contractors may add a new bounded
# identifier only through the governed gap/admission path; it then becomes
# part of the versioned roster ontology for subsequent plans.
CORE_CAPABILITY_IDS = frozenset(
    {
        "advice",
        "analysis",
        "architecture",
        "audit",
        "automation",
        "coaching",
        "communication",
        "coordination",
        "data-analysis",
        "design",
        "documentation",
        "generation-preparation",
        "governance",
        "ideation",
        "implementation",
        "investigation",
        "operations",
        "planning",
        "research",
        "review",
        "risk-analysis",
        "routing",
        "simulation",
        "testing",
        "threat-modeling",
        "translation",
        "verification",
    }
)

CAPABILITY_ALIASES = {
    "implementation-change": "implementation",
    "review-report": "review",
    "test-code": "testing",
    "test-evidence": "testing",
    "writing": "documentation",
}

ARTIFACT_CAPABILITY = {
    "analysis": "analysis",
    "architecture-record": "architecture",
    "documentation": "documentation",
    "implementation-change": "implementation",
    "plan": "planning",
    "review-report": "review",
    "test-code": "testing",
    "test-evidence": "testing",
}


def normalize_capability_id(value: object) -> str:
    """Normalize one bounded capability identifier without hiding novel gaps."""

    capability = str(value or "").strip().casefold().replace("_", "-")
    capability = CAPABILITY_ALIASES.get(capability, capability)
    if _IDENTIFIER.fullmatch(capability) is None:
        raise ValueError("workforce capability id must be a normalized identifier")
    return capability


def normalize_capability_ids(
    values: object,
    *,
    artifact_kinds: Sequence[str] = (),
    archetype: str = "",
) -> tuple[str, ...]:
    """Return deduplicated task capabilities plus artifact-owned defaults."""

    if values is None:
        values = ()
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError("workforce capability ids must be a sequence")
    result: list[str] = []
    for raw in values:
        item = normalize_capability_id(raw)
        if item not in result:
            result.append(item)
    for artifact in artifact_kinds:
        item = ARTIFACT_CAPABILITY.get(str(artifact).casefold())
        if item and item not in result:
            result.append(item)
    if archetype == "writer" and "documentation" not in result:
        result.append("documentation")
    if archetype == "tester" and "testing" not in result:
        result.append("testing")
    if archetype == "resident-manager" and "coordination" not in result:
        result.append("coordination")
    if not result or len(result) > MAX_CAPABILITY_IDS:
        raise ValueError(f"workforce capability ids must contain 1..{MAX_CAPABILITY_IDS} values")
    return tuple(result)


def artifact_capability(artifact_kind: str) -> str:
    """Return the required broad task capability for one artifact kind."""

    try:
        return ARTIFACT_CAPABILITY[artifact_kind]
    except KeyError as exc:
        raise ValueError("unsupported artifact capability") from exc


__all__ = [
    "ARTIFACT_CAPABILITY",
    "CAPABILITY_ALIASES",
    "CORE_CAPABILITY_IDS",
    "MAX_CAPABILITY_IDS",
    "artifact_capability",
    "normalize_capability_id",
    "normalize_capability_ids",
]
