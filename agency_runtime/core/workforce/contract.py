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
from typing import Any

from agency_runtime.core.workforce.identity import stable_worker_id

WORKFORCE_CONTRACT_SCHEMA_VERSION = "1"
MAX_CONTRACT_BYTES = 8_192
MAX_TEXT_BYTES = 192
MAX_OUTCOMES = 4
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
_HOSTS = frozenset({"claude", "codex", "hermes", "openclaw"})
_PLATFORMS = frozenset({"linux", "windows"})
_RESIDENTS = frozenset({"agents-orchestrator", "chief-of-staff"})

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

_TOOL_CLASS_MARKERS = (
    ("browser", ("browser", "playwright", "cypress", "web-test")),
    ("repository", ("repository", "source-code", "code-reader", "architecture-document")),
    ("filesystem", ("file-", "filesystem", "document-reader", "artifact-reader")),
    ("source-control", ("git", "source-control", "ci-reader", "ci-runner")),
    ("shell", ("shell", "terminal", "command-runner")),
    ("package-manager", ("package-manager", "dependency")),
    ("test-runner", ("test", "coverage", "profiler", "benchmark")),
    ("security", ("security", "scanner", "threat", "credential", "secret")),
    ("research", ("research", "documentation-search", "policy", "legal")),
    ("data", ("database", "data-reader", "analytics", "spreadsheet", "sql")),
    ("communications", ("crm", "ticket", "email", "communications", "community")),
    ("media", ("media", "audio", "video", "image", "asset")),
    ("geospatial", ("gis", "geospatial", "scene", "spatial", "map")),
    ("build-toolchain", ("build", "compiler", "sdk", "runtime", "toolchain")),
    ("cloud", ("cloud", "monitoring", "infrastructure", "deployment")),
)


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
    if "architecture" in task_types:
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
    if "architecture" in tasks:
        result.append("architecture-record")
    if "implementation" in tasks and archetype == "implementer":
        result.append("implementation-change")
    if "planning" in tasks:
        result.append("plan")
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
    if archetype == "resident-manager":
        phases.insert(0, "coordination")
    return tuple(dict.fromkeys(phases)) or ("discovery",)


def _domains(agent: Mapping[str, Any], division: str) -> tuple[str, ...]:
    if "domains" in agent:
        return _items(agent["domains"], field="domains", identifiers=True)
    return (_DIVISION_DOMAINS.get(division, division or "specialist-services"),)


def _tool_classes(agent: Mapping[str, Any]) -> tuple[str, ...]:
    if "tool_classes" in agent:
        return _items(agent["tool_classes"], field="tool_classes", identifiers=True)
    classes: list[str] = []
    for raw in agent.get("required_tools", ()):
        tool = str(raw).casefold()
        matched = next(
            (name for name, markers in _TOOL_CLASS_MARKERS if any(x in tool for x in markers)),
            "specialized-tool",
        )
        if matched not in classes:
            classes.append(matched)
    return tuple(classes[:MAX_TAXONOMY_ITEMS])


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

    agent_id = _identifier(
        agent.get("agent_slug") or agent.get("slug"),
        field="agent_id",
    )
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
        artifact_kinds=_artifact_kinds(agent, archetype),
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
        origin=_identifier(agent.get("origin", origin), field="origin"),
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
    expected = set(WorkforceContract.__dataclass_fields__)
    if set(value) != expected:
        raise ValueError("stored workforce contract has an unsupported shape")
    composition = value.get("composition")
    audit = value.get("audit")
    if not isinstance(composition, Mapping) or set(composition) != set(
        CompositionContract.__dataclass_fields__
    ):
        raise ValueError("stored workforce composition has an unsupported shape")
    if not isinstance(audit, Mapping) or set(audit) != set(AuditContract.__dataclass_fields__):
        raise ValueError("stored workforce audit has an unsupported shape")
    projected = project_workforce_contract(
        {
            "slug": value["agent_id"],
            "worker_id": value["worker_id"],
            "display_name": value["display_name"],
            "division": "specialized",
            "archetype": value["archetype"],
            "outcomes": value["outcomes"],
            "artifact_kinds": value["artifact_kinds"],
            "lifecycle_phases": value["lifecycle_phases"],
            "domains": value["domains"],
            "stacks": value["stacks"],
            "scope_qualifiers": value["scope_qualifiers"],
            "not_for": value["not_for"],
            "authority": value["authority"],
            "context_mode": value["context_mode"],
            "tool_classes": value["tool_classes"],
            "supported_hosts": value["hosts"],
            "supported_platforms": value["platforms"],
            "composition": composition,
            "audit_status": audit["status"],
            "audit_revision": audit["revision"],
            "routing_contract_valid": audit["contract_valid"],
            "version": value["version"],
            "version_hash": value["version_hash"],
            "enabled": value["enabled"],
            "employment": value["employment"],
            "origin": value["origin"],
        },
        origin=str(value["origin"]),
    )
    if projected.schema_version != value["schema_version"]:
        raise ValueError("stored workforce contract schema_version is unsupported")
    return projected


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
    "WORKFORCE_CONTRACT_SCHEMA_VERSION",
    "AuditContract",
    "CompositionContract",
    "WorkforceContract",
    "parse_workforce_contract",
    "project_workforce_contract",
    "workforce_index_fingerprint",
]
