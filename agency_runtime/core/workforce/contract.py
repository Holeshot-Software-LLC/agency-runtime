"""Immutable, compact workforce contracts for whole-roster recruitment.

The audited roster remains the execution authority.  This module deliberately
projects only recruitment facts: it never exposes source prompts, source paths,
raw findings, or provenance payloads to an inference provider.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Container, Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.resident_managers import RESIDENT_MANAGER_SLUG_SET
from agency_runtime.core.workforce.capability_ontology import (
    CORE_CAPABILITY_IDS,
    normalize_capability_ids,
)
from agency_runtime.core.workforce.identity import stable_worker_id

WORKFORCE_CONTRACT_SCHEMA_VERSION = "2"
MAX_CONTRACT_BYTES = 8_192
MAX_TEXT_BYTES = 192
MAX_OUTCOMES = 8
MAX_TAXONOMY_ITEMS = 8
MAX_RELATIONSHIPS = 16

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_CONTENT_HASH = re.compile(r"(?:sha256:)?[a-f0-9]{64}\Z")
_AUTHORITIES = frozenset({"advise", "modify", "plan", "review"})
_CONTEXT_MODES = frozenset({"direct_safe", "isolated_only"})
_EMPLOYMENT_STATES = frozenset(
    {"contractor", "disabled", "employee", "merged", "retired", "suspended"}
)
_AUDIT_STATES = frozenset({"approved", "quarantined", "retired"})
_HOSTS = frozenset({"claude", "codex", "hermes", "openclaw", "zcode"})
_PLATFORMS = frozenset({"linux", "windows"})
_RESIDENTS = RESIDENT_MANAGER_SLUG_SET

_DIVISION_DOMAINS = {
    "academic": "research",
    "design": "design",
    "engineering": "software-engineering",
    "finance": "finance",
    "game-development": "game-development",
    "gis": "geospatial",
    "healthcare": "healthcare",
    "marketing": "marketing",
    "paid-media": "marketing",
    "product": "product",
    "project-management": "project-delivery",
    "sales": "sales",
    "security": "security",
    "spatial-computing": "spatial-computing",
    "specialized": "specialist-services",
    "support": "customer-operations",
    "testing": "quality-assurance",
}


@dataclass(frozen=True, slots=True)
class CompositionContract:
    """Typed relationships used after semantic recruitment."""

    substitution_group: str = ""
    substitutes_for: tuple[str, ...] = ()
    complements: tuple[str, ...] = ()
    same_context_conflicts: tuple[str, ...] = ()
    selection_exclusive: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    must_follow: tuple[str, ...] = ()
    must_review_independently: tuple[str, ...] = ()
    independence_class: str = ""


@dataclass(frozen=True, slots=True)
class AuditContract:
    """Non-provenance audit facts safe to expose to a recruiter."""

    status: str
    revision: str
    contract_valid: bool


@dataclass(frozen=True, slots=True)
class WorkforceContract:
    """One immutable, versioned recruitment record."""

    schema_version: str
    worker_id: str
    agent_id: str
    display_name: str
    archetype: str
    outcomes: tuple[str, ...]
    capability_ids: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    lifecycle_phases: tuple[str, ...]
    domains: tuple[str, ...]
    stacks: tuple[str, ...]
    scope_qualifiers: tuple[str, ...]
    not_for: tuple[str, ...]
    authority: str
    context_mode: str
    tool_classes: tuple[str, ...]
    hosts: tuple[str, ...]
    platforms: tuple[str, ...]
    composition: CompositionContract
    audit: AuditContract
    version: str
    version_hash: str
    enabled: bool
    employment: str
    origin: str

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical JSON-compatible representation."""

        return asdict(self)


def _text(value: object, *, field: str, maximum: int = MAX_TEXT_BYTES) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if len(text.encode("utf-8")) > maximum:
        raise ValueError(f"workforce {field} exceeds {maximum} bytes")
    return text


def _identifier(value: object, *, field: str, required: bool = True) -> str:
    text = _text(value, field=field, maximum=128).casefold()
    if not text and not required:
        return ""
    if _IDENTIFIER.fullmatch(text) is None:
        raise ValueError(f"workforce {field} must be a normalized identifier")
    return text


def _content_hash(value: object) -> str:
    digest = _text(value, field="version_hash", maximum=71).casefold()
    if _CONTENT_HASH.fullmatch(digest) is None:
        raise ValueError("workforce version_hash must be an exact SHA-256 identity")
    return digest.removeprefix("sha256:")


def _items(
    value: object,
    *,
    field: str,
    maximum_items: int = MAX_TAXONOMY_ITEMS,
    identifiers: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"workforce {field} must be a sequence")
    result: list[str] = []
    for item in value:
        normalized = _identifier(item, field=field) if identifiers else _text(item, field=field)
        if normalized and normalized not in result:
            result.append(normalized)
        if len(result) > maximum_items:
            raise ValueError(f"workforce {field} exceeds {maximum_items} items")
    return tuple(result)


def _explicit_items(
    agent: Mapping[str, Any],
    field: str,
    fallback: object,
    *,
    maximum_items: int = MAX_TAXONOMY_ITEMS,
    identifiers: bool = False,
) -> tuple[str, ...]:
    return _items(
        agent.get(field, fallback),
        field=field,
        maximum_items=maximum_items,
        identifiers=identifiers,
    )


def _archetype(agent_id: str, authority: str, division: str, agent: Mapping[str, Any]) -> str:
    if "archetype" in agent:
        return _identifier(agent["archetype"], field="archetype")
    task_types = {str(item).casefold() for item in agent.get("task_types", ())}
    categories = {str(item).casefold() for item in agent.get("categories", ())}
    if agent_id in _RESIDENTS:
        return "resident-manager"
    if division == "testing":
        return "tester"
    if {"documentation", "technical-writing"} & categories or {
        "documentation",
        "writing",
    } & task_types:
        return "writer"
    if authority == "modify":
        return "implementer"
    if authority == "review":
        return "reviewer"
    if authority == "advise":
        return "advisor"
    if "architecture" in task_types or any(
        category == "architecture" or category.endswith("-architecture") for category in categories
    ):
        return "architect"
    return "planner"


def _artifact_kinds(agent: Mapping[str, Any], archetype: str) -> tuple[str, ...]:
    if "artifact_kinds" in agent:
        return _items(agent["artifact_kinds"], field="artifact_kinds", identifiers=True)
    tasks = {str(item).casefold() for item in agent.get("task_types", ())}
    result: list[str] = []
    if archetype == "writer":
        result.append("documentation")
    if archetype == "tester":
        result.append("test-evidence")
        if str(agent.get("authority", "")).casefold() == "modify":
            result.append("test-code")
    if "architecture" in tasks or archetype == "architect":
        result.append("architecture-record")
    if "implementation" in tasks and archetype == "implementer":
        result.append("implementation-change")
    if "planning" in tasks:
        result.append("plan")
    if {"analysis", "research"} & tasks:
        result.append("analysis")
    if "review" in tasks:
        result.append("review-report")
    if not result:
        result.append("analysis")
    return tuple(dict.fromkeys(result))


def _lifecycle_phases(agent: Mapping[str, Any], archetype: str) -> tuple[str, ...]:
    if "lifecycle_phases" in agent:
        return _items(agent["lifecycle_phases"], field="lifecycle_phases", identifiers=True)
    mapping = {
        "analysis": "discovery",
        "research": "discovery",
        "planning": "planning",
        "architecture": "design",
        "design": "design",
        "implementation": "implementation",
        "review": "review",
        "testing": "testing",
        "documentation": "documentation",
        "writing": "documentation",
    }
    phases = [
        mapping[item]
        for raw in agent.get("task_types", ())
        if (item := str(raw).casefold()) in mapping
    ]
    # Some upstream technical-writing roles describe document creation with a
    # generic "implementation" task type.  Their audited category is the
    # stronger lifecycle signal.  Do not apply this to read-only discovery
    # roles that may also produce documentation-shaped analysis artifacts.
    categories = {str(item).casefold() for item in agent.get("categories", ())}
    if archetype == "writer" and "technical-writing" in categories:
        phases.insert(0, "documentation")
    if archetype == "tester":
        phases.insert(0, "testing")
    if archetype == "architect":
        phases.insert(0, "design")
    if archetype == "resident-manager":
        phases.insert(0, "coordination")
    return tuple(dict.fromkeys(phases)) or ("discovery",)


def _domains(agent: Mapping[str, Any], division: str) -> tuple[str, ...]:
    if "domains" in agent:
        return _items(agent["domains"], field="domains", identifiers=True)
    result = [_DIVISION_DOMAINS.get(division, division or "specialist-services")]
    categories = {str(item).casefold() for item in agent.get("categories", ())}
    owned_text = " ".join(str(item) for item in agent.get("capabilities", ())).casefold()
    if "security" in owned_text and "security" not in result:
        result.append("security")
    if "quality" in categories and "quality-assurance" not in result:
        result.append("quality-assurance")
    if (
        categories & {"accessibility", "inclusive-testing", "wcag"}
        and "accessibility" not in result
    ):
        result.append("accessibility")
    if categories & {"accounts-payable", "finance"} and "finance" not in result:
        result.append("finance")
    if categories & {"code-intelligence", "lsp"} and "software-engineering" not in result:
        result.append("software-engineering")
    # Application-security and secure-code-review workers own software artifacts as well as
    # security outcomes. Keeping them security-only makes an inferred unit that correctly names
    # both domains impossible to staff, even when the exact specialist is present and eligible.
    if (
        division == "security"
        and categories & {"application-security", "code-review"}
        and "software-engineering" not in result
    ):
        result.append("software-engineering")
    return tuple(result)


def _tool_classes(agent: Mapping[str, Any]) -> tuple[str, ...]:
    from agency_runtime.core.host_capabilities import canonicalize_tool_capabilities

    # Eligibility is an executable minimum, not a worker's complete affinity
    # profile. Audited records may advertise optional tools (for example a
    # browser for one integration-verification scenario) in tool_classes
    # while excluding them from required_tools. Preferring the broad list here
    # incorrectly made every optional surface mandatory and could remove the
    # strongest specialist from an otherwise executable unit.
    raw = agent.get("required_tools", agent.get("tool_classes", ()))
    values = raw if isinstance(raw, (list, tuple)) else ()
    canonical, unknown = canonicalize_tool_capabilities(values)
    # Unknown reviewed labels stay explicit so eligibility rejects a host that
    # cannot prove them; never collapse them into a broad pseudo-capability.
    return tuple((*canonical, *unknown)[:MAX_TAXONOMY_ITEMS])


def _composition(agent: Mapping[str, Any]) -> CompositionContract:
    raw = agent.get("composition", {})
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ValueError("workforce composition must be an object")

    def relation(field: str, fallback: object = ()) -> tuple[str, ...]:
        return _items(
            raw.get(field, fallback),
            field=f"composition.{field}",
            maximum_items=MAX_RELATIONSHIPS,
            identifiers=True,
        )

    return CompositionContract(
        substitution_group=_identifier(
            raw.get("substitution_group", ""),
            field="composition.substitution_group",
            required=False,
        ),
        substitutes_for=relation("substitutes_for"),
        complements=relation("complements"),
        same_context_conflicts=relation(
            "same_context_conflicts",
            agent.get("conflicts_with", ()),
        ),
        selection_exclusive=relation("selection_exclusive"),
        requires=relation("requires", agent.get("requires", ())),
        must_follow=relation("must_follow"),
        must_review_independently=relation("must_review_independently"),
        independence_class=_identifier(
            raw.get("independence_class", agent.get("independence_group", "")),
            field="composition.independence_class",
            required=False,
        ),
    )


def project_workforce_contract(
    agent: Mapping[str, Any],
    *,
    disabled: Container[str] = (),
    origin: str = "upstream",
) -> WorkforceContract:
    """Project one audited roster record into a bounded recruitment contract."""

    agent_id = _identifier(agent_identity(agent), field="agent_id")
    authority = _identifier(agent.get("authority"), field="authority")
    context_mode = _identifier(agent.get("context_mode"), field="context_mode")
    if authority not in _AUTHORITIES:
        raise ValueError(f"unsupported workforce authority: {authority}")
    if context_mode not in _CONTEXT_MODES:
        raise ValueError(f"unsupported workforce context mode: {context_mode}")
    division = _identifier(agent.get("division"), field="division")
    archetype = _archetype(agent_id, authority, division, agent)
    enabled_value = agent.get("enabled", agent_id not in disabled or agent_id in _RESIDENTS)
    if not isinstance(enabled_value, bool):
        raise ValueError("workforce enabled must be a boolean")
    enabled = enabled_value or agent_id in _RESIDENTS
    employment = "employee" if enabled else "disabled"
    employment = _identifier(
        agent.get("employment", employment),
        field="employment",
    )
    if employment not in _EMPLOYMENT_STATES:
        raise ValueError(f"unsupported workforce employment state: {employment}")
    expected_enabled = employment in {"contractor", "employee"}
    if enabled != expected_enabled:
        raise ValueError("workforce employment must agree with enabled state")

    hosts = _items(agent.get("supported_hosts", ()), field="hosts", identifiers=True)
    platforms = _items(
        agent.get("supported_platforms", ()),
        field="platforms",
        identifiers=True,
    )
    if not hosts or not set(hosts) <= _HOSTS:
        raise ValueError("workforce hosts must be non-empty supported host identifiers")
    if not platforms or not set(platforms) <= _PLATFORMS:
        raise ValueError("workforce platforms must be non-empty supported platform identifiers")
    audit_status = _identifier(agent.get("audit_status"), field="audit.status")
    if audit_status not in _AUDIT_STATES:
        raise ValueError(f"unsupported workforce audit status: {audit_status}")

    artifact_kinds = _artifact_kinds(agent, archetype)
    contract_origin = _identifier(agent.get("origin", origin), field="origin")
    capability_ids = normalize_capability_ids(
        agent.get("capability_ids", agent.get("task_types", ())),
        artifact_kinds=artifact_kinds,
        archetype=archetype,
    )
    if contract_origin != "agency" and not set(capability_ids) <= CORE_CAPABILITY_IDS:
        unknown = sorted(set(capability_ids) - CORE_CAPABILITY_IDS)
        raise ValueError(
            "external workforce capability ids require ontology review: " + ",".join(unknown)
        )
    contract = WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=_identifier(
            agent.get("worker_id", stable_worker_id(agent_id)),
            field="worker_id",
        ),
        agent_id=agent_id,
        display_name=_text(
            agent.get("name") or agent.get("display_name") or agent_id,
            field="display_name",
            maximum=128,
        ),
        archetype=archetype,
        outcomes=_explicit_items(
            agent,
            "outcomes",
            agent.get("capabilities", ()),
            maximum_items=MAX_OUTCOMES,
        ),
        capability_ids=capability_ids,
        artifact_kinds=artifact_kinds,
        lifecycle_phases=_lifecycle_phases(agent, archetype),
        domains=_domains(agent, division),
        stacks=_explicit_items(agent, "stacks", (), identifiers=True),
        scope_qualifiers=_explicit_items(
            agent,
            "scope_qualifiers",
            agent.get("preferred_when", ()),
            maximum_items=4,
        ),
        not_for=_explicit_items(
            agent,
            "not_for",
            agent.get("avoid_when", ()),
            maximum_items=4,
        ),
        authority=authority,
        context_mode=context_mode,
        tool_classes=_tool_classes(agent),
        hosts=hosts,
        platforms=platforms,
        composition=_composition(agent),
        audit=AuditContract(
            status=audit_status,
            revision=_text(agent.get("audit_revision"), field="audit.revision", maximum=32),
            contract_valid=bool(agent.get("routing_contract_valid", True)),
        ),
        version=_text(agent.get("version"), field="version", maximum=96),
        version_hash=_content_hash(
            agent.get("version_hash")
            or agent.get("hash")
            or agent.get("prompt_hash")
            or agent.get("source_content_hash")
        ),
        enabled=enabled,
        employment=employment,
        origin=contract_origin,
    )
    if not contract.outcomes:
        raise ValueError("workforce outcomes must not be empty")
    if not contract.hosts or not contract.platforms:
        raise ValueError("workforce hosts and platforms must not be empty")
    if not contract.audit.revision or not contract.version:
        raise ValueError("workforce audit revision and version must not be empty")
    payload = _canonical_json(contract)
    if len(payload) > MAX_CONTRACT_BYTES:
        raise ValueError(f"workforce contract exceeds {MAX_CONTRACT_BYTES} bytes")
    return contract


def parse_workforce_contract(value: object) -> WorkforceContract:
    """Validate and rehydrate one canonical stored recruitment contract."""

    if not isinstance(value, Mapping):
        raise ValueError("stored workforce contract must be an object")
    document = dict(value)
    expected = set(WorkforceContract.__dataclass_fields__)
    legacy = expected - {"capability_ids"}
    if set(document) == legacy and document.get("schema_version") == "1":
        document["schema_version"] = WORKFORCE_CONTRACT_SCHEMA_VERSION
        document["capability_ids"] = normalize_capability_ids(
            (),
            artifact_kinds=tuple(document.get("artifact_kinds") or ()),
            archetype=str(document.get("archetype") or ""),
        )
    if set(document) != expected:
        raise ValueError("stored workforce contract has an unsupported shape")
    composition = document.get("composition")
    audit = document.get("audit")
    if not isinstance(composition, Mapping) or set(composition) != set(
        CompositionContract.__dataclass_fields__
    ):
        raise ValueError("stored workforce composition has an unsupported shape")
    if not isinstance(audit, Mapping) or set(audit) != set(AuditContract.__dataclass_fields__):
        raise ValueError("stored workforce audit has an unsupported shape")
    projected = project_workforce_contract(
        {
            "slug": document["agent_id"],
            "worker_id": document["worker_id"],
            "display_name": document["display_name"],
            "division": "specialized",
            "archetype": document["archetype"],
            "outcomes": document["outcomes"],
            "capability_ids": document["capability_ids"],
            "artifact_kinds": document["artifact_kinds"],
            "lifecycle_phases": document["lifecycle_phases"],
            "domains": document["domains"],
            "stacks": document["stacks"],
            "scope_qualifiers": document["scope_qualifiers"],
            "not_for": document["not_for"],
            "authority": document["authority"],
            "context_mode": document["context_mode"],
            "tool_classes": document["tool_classes"],
            "supported_hosts": document["hosts"],
            "supported_platforms": document["platforms"],
            "composition": composition,
            "audit_status": audit["status"],
            "audit_revision": audit["revision"],
            "routing_contract_valid": audit["contract_valid"],
            "version": document["version"],
            "version_hash": document["version_hash"],
            "enabled": document["enabled"],
            "employment": document["employment"],
            "origin": document["origin"],
        },
        origin=str(document["origin"]),
    )
    if projected.schema_version != document["schema_version"]:
        raise ValueError("stored workforce contract schema_version is unsupported")
    return projected


@lru_cache(maxsize=512)
def _canonical_json(contract: WorkforceContract) -> bytes:
    return json.dumps(
        contract.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def workforce_index_fingerprint(contracts: Sequence[WorkforceContract]) -> str:
    """Return a stable digest over a complete, duplicate-free workforce index."""

    ordered = sorted(contracts, key=lambda item: (item.worker_id, item.agent_id))
    worker_ids = [item.worker_id for item in ordered]
    agent_ids = [item.agent_id for item in ordered]
    if len(worker_ids) != len(set(worker_ids)):
        raise ValueError("workforce index contains duplicate worker ids")
    if len(agent_ids) != len(set(agent_ids)):
        raise ValueError("workforce index contains duplicate agent ids")
    known = set(agent_ids)
    for contract in ordered:
        if contract.schema_version != WORKFORCE_CONTRACT_SCHEMA_VERSION:
            raise ValueError("workforce index contains an unsupported schema version")
        relationships = contract.composition
        for field in (
            "substitutes_for",
            "complements",
            "same_context_conflicts",
            "selection_exclusive",
            "requires",
            "must_follow",
            "must_review_independently",
        ):
            targets = getattr(relationships, field)
            if contract.agent_id in targets:
                raise ValueError(f"workforce {field} relationship cannot target self")
            missing = set(targets) - known
            if missing:
                raise ValueError(f"workforce {field} relationship targets unknown agents")
    payload = b"[" + b",".join(_canonical_json(item) for item in ordered) + b"]"
    return "sha256:" + hashlib.sha256(payload).hexdigest()


__all__ = [
    "MAX_CONTRACT_BYTES",
    "MAX_OUTCOMES",
    "MAX_TAXONOMY_ITEMS",
    "MAX_TEXT_BYTES",
    "WORKFORCE_CONTRACT_SCHEMA_VERSION",
    "AuditContract",
    "CompositionContract",
    "WorkforceContract",
    "parse_workforce_contract",
    "project_workforce_contract",
    "workforce_index_fingerprint",
]
