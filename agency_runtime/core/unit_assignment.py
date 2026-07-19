"""Deterministic, bounded specialist assignment for detected work units."""

from __future__ import annotations

import hashlib
import math
import posixpath
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from agency_runtime.core.config import AgencyConfig, DelegationConfig, OllamaConfig
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    diagnostic_installation_capability_receipt,
)
from agency_runtime.core.resident_managers import is_resident_manager_slug

MAX_SUGGESTED_WORK_UNITS = 16
MAX_WORK_UNIT_TRANSPORT_CHARS = 16_384
MAX_WORK_UNIT_CHARS = 4_096
MAX_WORK_UNIT_PREVIEW_CHARS = 160
MAX_AGENT_SLUG_CHARS = 128
MAX_ASSIGNMENT_AGENT_NAME_CHARS = 128
MAX_ASSIGNMENT_AGENT_DESCRIPTION_CHARS = 256
MAX_ASSIGNMENT_AGENT_LABEL_CHARS = 64
MAX_ASSIGNMENT_AGENT_LABELS = 8
MAX_PLAN_LIST_ITEMS = 8
MAX_PLAN_LIST_ITEM_CHARS = 128
MAX_RESOURCE_CHARS = 512
MAX_UNIT_SELECTION_WORKERS = 4
LEGACY_UNIT_AGENT_ASSIGNMENT_VERSION = 1
_SELECTED_ONLY_UNIT_AGENT_ASSIGNMENT_VERSION = 2
_CATALOG_UNIT_AGENT_ASSIGNMENT_VERSION = 3
UNIT_AGENT_ASSIGNMENT_VERSION = 4

DELEGATION_STRENGTHS = frozenset({"optional", "preferred", "strongly_preferred"})
DELIVERABLE_KINDS = frozenset(
    {"implementation", "review", "verification", "documentation", "outcome"}
)
MUTATION_SCOPES = frozenset({"read_only", "workspace_write", "external_write"})
PARALLELIZATION_MODES = frozenset({"parallel", "sequential", "unspecified"})

_AGENT_TOKEN_RE = re.compile(r"[a-z0-9]+")
_WORK_UNIT_ID_RE = re.compile(r"unit-[0-9a-f]{10}")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}")
_RATIONALE_CODE_RE = re.compile(r"[a-z0-9][a-z0-9:_-]{0,63}")
_RESOURCE_TOKEN_RE = re.compile(
    rf'"[^"\r\n]{{1,{MAX_RESOURCE_CHARS}}}"|'
    rf"'[^'\r\n]{{1,{MAX_RESOURCE_CHARS}}}'|[^\s]+"
)
_WINDOWS_ABSOLUTE_RESOURCE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_BARE_FILE_RESOURCE_RE = re.compile(
    r"^(?:README(?:\.[A-Za-z0-9_-]+)?|Makefile|Dockerfile|"
    r"[A-Za-z0-9_.@-]+\.[A-Za-z0-9_-]{1,16})$",
    re.IGNORECASE,
)
_ACTION_PREFIX = (
    r"(?:^\s*(?:(?:please|kindly)\s+|"
    r"(?:can|could|would|will)\s+you\s+|"
    r"(?:i|we)\s+(?:need|want)\s+(?:you\s+)?to\s+|"
    r"(?:need|required)\s+to\s+)?|"
    r"(?:\b(?:and|then)\b|[,;:])\s*(?:(?:please|kindly)\s+)?)"
)
_EXTERNAL_MUTATION_RE = re.compile(
    _ACTION_PREFIX + r"(?:close\s+(?:(?:an?|the)\s+)?issue|create\s+(?:(?:an?|the)\s+)?issue|"
    r"deploy|merge|publish|push|release|send|ship)\b",
    re.IGNORECASE,
)
_WORKSPACE_MUTATION_RE = re.compile(
    _ACTION_PREFIX + r"(?:add|adding|build|building|change|changing|configure|configuring|"
    r"correct|correcting|create|creating|debug|debugging|delete|deleting|"
    r"document|documenting|edit|editing|enhance|enhancing|fix|fixing|harden|"
    r"hardening|implement|implementing|improve|improving|install|installing|"
    r"migrate|migrating|move|moving|optimi[sz]e|"
    r"optimi[sz]ing|patch|patching|refactor|refactoring|remove|removing|"
    r"rename|renaming|repair|repairing|redesign|redesigning|revise|revising|"
    r"rewrite|rewriting|secure|securing|set\s+up|split|splitting|update|updating|"
    r"write|writing)\b",
    re.IGNORECASE,
)
_REVIEW_DELIVERABLE_RE = re.compile(r"\b(?:audit|inspect|review)\b", re.IGNORECASE)
_VERIFY_DELIVERABLE_RE = re.compile(
    r"\b(?:benchmark|check|coverage|eval|measure|test|validate|verify)\b",
    re.IGNORECASE,
)
_DOC_DELIVERABLE_RE = re.compile(
    r"\b(?:document|documentation|docs|readme|write)\b",
    re.IGNORECASE,
)
_SIGNAL_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "apply",
        "for",
        "in",
        "of",
        "on",
        "or",
        "specialist",
        "the",
        "to",
        "with",
    }
)
_ROLE_SIGNALS: dict[str, frozenset[str]] = {
    "agent": frozenset({"agency", "agent", "delegate", "delegation", "orchestrate"}),
    "architect": frozenset(
        {"architect", "architecture", "design", "redesign", "structure", "workflow"}
    ),
    "data": frozenset({"data", "database", "dataset", "schema", "sql"}),
    "database": frozenset({"data", "database", "migration", "schema", "sql"}),
    "developer": frozenset(
        {"build", "change", "code", "debug", "fix", "implement", "migrate", "refactor"}
    ),
    "designer": frozenset({"animation", "dashboard", "design", "redesign", "ui", "ux"}),
    "devops": frozenset({"ci", "deploy", "install", "operations", "release"}),
    "engineer": frozenset(
        {"build", "configure", "debug", "fix", "implement", "optimize", "refactor"}
    ),
    "performance": frozenset({"benchmark", "latency", "optimize", "performance", "profile"}),
    "reviewer": frozenset(
        {"audit", "check", "inspect", "quality", "review", "test", "validate", "verify"}
    ),
    "security": frozenset(
        {
            "auth",
            "authentication",
            "harden",
            "secure",
            "security",
            "threat",
            "vulnerability",
        }
    ),
    "tester": frozenset({"coverage", "eval", "test", "validate", "verify"}),
    "testing": frozenset({"coverage", "eval", "test", "validate", "verify"}),
    "ui": frozenset({"animation", "css", "dashboard", "interface", "ui", "ux", "visual"}),
    "workflow": frozenset({"automation", "delegate", "pipeline", "process", "workflow"}),
    "writer": frozenset(
        {"document", "documentation", "docs", "readme", "write", "writer", "writing"}
    ),
}


def _clean(value: Any, maximum: int) -> str:
    if value is None:
        return ""
    return str(value).strip()[:maximum]


def _normalized_goal(value: Any) -> str:
    """Return the complete goal admitted by the per-unit transport bound."""

    raw = str(value or "")[:MAX_WORK_UNIT_TRANSPORT_CHARS]
    return " ".join(raw.split())[:MAX_WORK_UNIT_CHARS]


def _goal_preview(value: str) -> str:
    return value[:MAX_WORK_UNIT_PREVIEW_CHARS]


def _bounded_strings(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value[:MAX_ASSIGNMENT_AGENT_LABELS]:
        normalized = _clean(item, MAX_ASSIGNMENT_AGENT_LABEL_CHARS)
        identity = normalized.casefold()
        if normalized and identity not in seen:
            seen.add(identity)
            result.append(normalized)
    return result


def _bounded_agent_ids(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value[:MAX_SUGGESTED_WORK_UNITS]:
        slug = _clean(item, MAX_AGENT_SLUG_CHARS).casefold()
        if slug and slug not in seen:
            seen.add(slug)
            result.append(slug)
    return result


def _bounded_work_unit_ids(
    value: Any,
    *,
    strict: bool,
) -> list[str] | None:
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        return None if strict else []
    if strict and len(value) > MAX_SUGGESTED_WORK_UNITS:
        return None
    result: list[str] = []
    seen: set[str] = set()
    for item in value[:MAX_SUGGESTED_WORK_UNITS]:
        work_unit_id = _clean(item, 15).casefold()
        if _WORK_UNIT_ID_RE.fullmatch(work_unit_id) is None or work_unit_id in seen:
            if strict:
                return None
            continue
        seen.add(work_unit_id)
        result.append(work_unit_id)
    return result


def _project_assignment_agent(
    raw: Any,
    *,
    strict: bool,
    seen: set[str],
    claimed_primary_work_units: set[str],
) -> dict[str, Any] | None:
    """Project one bounded assignment candidate or reject strict corruption."""

    if not isinstance(raw, Mapping):
        if strict:
            raise ValueError("assignment candidate is not a mapping")
        return None
    slug = _clean(
        raw.get("slug") or raw.get("agent_slug"),
        MAX_AGENT_SLUG_CHARS,
    ).casefold()
    if is_resident_manager_slug(slug) or not slug or slug in seen:
        if strict:
            raise ValueError("assignment candidate identity is invalid")
        return None
    name = _clean(raw.get("name"), MAX_ASSIGNMENT_AGENT_NAME_CHARS)
    description = _clean(
        raw.get("description"),
        MAX_ASSIGNMENT_AGENT_DESCRIPTION_CHARS,
    )
    capabilities = _bounded_strings(raw.get("capabilities"))
    tags = _bounded_strings(raw.get("tags"))
    required_tools = _bounded_strings(raw.get("required_tools"))
    required_evidence = _bounded_strings(raw.get("evidence_requirements"))
    matched_work_unit_ids = _bounded_work_unit_ids(
        raw.get("matched_work_unit_ids"),
        strict=strict,
    )
    primary_work_unit_ids = _bounded_work_unit_ids(
        raw.get("primary_work_unit_ids"),
        strict=strict,
    )
    if (
        matched_work_unit_ids is None
        or primary_work_unit_ids is None
        or any(item not in matched_work_unit_ids for item in primary_work_unit_ids)
        or (strict and claimed_primary_work_units.intersection(primary_work_unit_ids))
    ):
        raise ValueError("assignment work-unit claims are invalid")
    if not any(
        (
            name,
            description,
            capabilities,
            tags,
            required_tools,
            required_evidence,
            matched_work_unit_ids,
        )
    ):
        return None
    seen.add(slug)
    claimed_primary_work_units.update(primary_work_unit_ids)
    projected = {
        "slug": slug,
        "name": name,
        "description": description,
        "capabilities": capabilities,
        "tags": tags,
    }
    if required_tools:
        projected["required_tools"] = required_tools
    if required_evidence:
        projected["evidence_requirements"] = required_evidence
    if matched_work_unit_ids:
        projected["matched_work_unit_ids"] = matched_work_unit_ids
    if primary_work_unit_ids:
        projected["primary_work_unit_ids"] = primary_work_unit_ids
    return projected


def project_unit_assignment_agents(
    value: Any,
    *,
    strict: bool = False,
) -> list[dict[str, Any]] | None:
    """Return the bounded metadata snapshot used by assignment and replay."""

    if not isinstance(value, (list, tuple)):
        return None if strict else []
    if strict and len(value) > MAX_SUGGESTED_WORK_UNITS:
        return None
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    claimed_primary_work_units: set[str] = set()
    try:
        for raw in value[:MAX_SUGGESTED_WORK_UNITS]:
            projected = _project_assignment_agent(
                raw,
                strict=strict,
                seen=seen,
                claimed_primary_work_units=claimed_primary_work_units,
            )
            if projected is not None:
                result.append(projected)
    except ValueError:
        return None
    return result


def _delegated_work_units(routing: Mapping[str, Any]) -> list[tuple[str, str]]:
    work_units = routing.get("work_units")
    if not isinstance(work_units, Mapping) or work_units.get("delegate") is not True:
        return []
    raw_units = work_units.get("units")
    if not isinstance(raw_units, (list, tuple)):
        return []
    if len(raw_units) > MAX_SUGGESTED_WORK_UNITS:
        return []
    units: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw_unit in raw_units:
        unit = _normalized_goal(raw_unit)
        if not unit:
            continue
        work_unit_id = work_unit_id_from_text(unit)
        if work_unit_id in seen:
            continue
        seen.add(work_unit_id)
        units.append((work_unit_id, unit))
    return units if len(units) >= 2 else []


def _selected_assignment_agents_from_catalog(
    catalog: Sequence[Mapping[str, Any]],
    routing: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Retain the selected-only snapshot for non-delegated compatibility."""

    selected = [
        slug
        for slug in _bounded_agent_ids(routing.get("selected_ids"))
        if not is_resident_manager_slug(slug)
    ]
    if not selected:
        return []
    selected_set = frozenset(selected)
    by_slug: dict[str, Mapping[str, Any]] = {}
    for raw in catalog:
        slug = _clean(
            raw.get("slug") or raw.get("agent_slug"),
            MAX_AGENT_SLUG_CHARS,
        ).casefold()
        if slug in selected_set and slug not in by_slug:
            by_slug[slug] = raw
            if len(by_slug) == len(selected_set):
                break
    candidates: list[dict[str, Any]] = []
    for slug in selected:
        raw = by_slug.get(slug)
        if raw is None:
            continue
        candidates.append(
            {
                "slug": slug,
                "name": raw.get("name"),
                "description": raw.get("description"),
                "capabilities": raw.get("capabilities"),
                "tags": [
                    *_bounded_strings(raw.get("tags")),
                    *_bounded_strings(raw.get("categories")),
                ],
                "required_tools": raw.get("required_tools"),
                "evidence_requirements": raw.get("evidence_requirements"),
            }
        )
    return project_unit_assignment_agents(candidates) or []


def _assignment_catalog(
    catalog: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Mapping[str, Any]]]:
    catalog_list = [
        dict(agent)
        for agent in catalog
        if not is_resident_manager_slug(agent.get("slug") or agent.get("agent_slug"))
    ]
    catalog_by_slug: dict[str, Mapping[str, Any]] = {}
    for raw in catalog_list:
        slug = _clean(
            raw.get("slug") or raw.get("agent_slug"),
            MAX_AGENT_SLUG_CHARS,
        ).casefold()
        if slug and slug not in catalog_by_slug:
            catalog_by_slug[slug] = raw
    return catalog_list, catalog_by_slug


def _policy_selection_for_degraded_route(
    unit_routing: Mapping[str, Any],
    selected: list[str],
) -> list[str]:
    explicit_policy = {
        *_bounded_agent_ids(unit_routing.get("selected_companion_ids")),
        *(
            _bounded_agent_ids(unit_routing.get("available_fallback_companion_ids"))
            if unit_routing.get("fallback_applied") is True
            else []
        ),
    }
    return [slug for slug in selected if slug in explicit_policy]


def _supports_unit_deliverable(unit: str, agent: Mapping[str, Any]) -> bool:
    """Keep deterministic fallback inside the specialist's reviewed authority."""

    raw_task_types = agent.get("task_types")
    task_types = (
        {str(item or "").strip().casefold() for item in raw_task_types if str(item or "").strip()}
        if isinstance(raw_task_types, (list, tuple))
        else set()
    )
    authority = str(agent.get("authority") or "").strip().casefold()
    mutation_scope = _mutation_scope(unit)
    if mutation_scope != "read_only" and authority != "modify":
        return False
    if not task_types and not authority:
        # Legacy/test catalogs without reviewed authority metadata retain their
        # explicit read-only route result. Mutation requires positive authority.
        return mutation_scope == "read_only"
    deliverable = _deliverable_kind(unit)
    if deliverable == "implementation":
        return authority == "modify" and "implementation" in task_types
    if deliverable == "documentation":
        capabilities = agent.get("capabilities")
        categories = agent.get("categories")
        metadata = " ".join(
            (
                str(agent.get("slug") or ""),
                str(agent.get("name") or ""),
                str(agent.get("description") or ""),
                *(
                    str(item)
                    for item in (capabilities if isinstance(capabilities, (list, tuple)) else ())
                ),
                *(
                    str(item)
                    for item in (categories if isinstance(categories, (list, tuple)) else ())
                ),
            )
        )
        return bool(_DOC_DELIVERABLE_RE.search(metadata))
    if deliverable == "verification":
        return bool(task_types.intersection({"review", "testing", "verification"}))
    if deliverable == "review":
        return authority == "review" or "review" in task_types
    return True


def _deterministic_unit_selection(
    unit: str,
    catalog_list: list[dict[str, Any]],
) -> list[str]:
    """Select the strongest eligible reviewed contract for one exact unit."""

    scored = [
        (_agent_score(unit, slug, agent), index, slug)
        for index, agent in enumerate(catalog_list)
        if (
            slug := _clean(
                agent.get("slug") or agent.get("agent_slug"),
                MAX_AGENT_SLUG_CHARS,
            ).casefold()
        )
        and not is_resident_manager_slug(slug)
        and _supports_unit_deliverable(unit, agent)
    ]
    winner = min(
        (item for item in scored if item[0] > 0),
        key=lambda item: (-item[0], item[1], item[2]),
        default=None,
    )
    if winner is None:
        return []
    from agency_runtime.core.selector.compatibility import enforce_compatible_set

    compatible = enforce_compatible_set([winner[2]], catalog_list, limit=1)
    return list(compatible["selected_ids"])


def _eligible_unit_catalog(
    unit_routing: Mapping[str, Any],
    catalog_list: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Mapping[str, Any]]]:
    """Rebuild the pipeline's host/tool-eligible catalog from bounded rejections."""

    rejected = {
        str(item.get("slug") or "").strip().casefold()
        for item in unit_routing.get("eligibility_rejections") or ()
        if isinstance(item, Mapping)
    }
    eligible = [
        agent
        for agent in catalog_list
        if _clean(
            agent.get("slug") or agent.get("agent_slug"),
            MAX_AGENT_SLUG_CHARS,
        ).casefold()
        not in rejected
    ]
    eligible_list, eligible_by_slug = _assignment_catalog(eligible)
    return eligible_list, eligible_by_slug


def _compatible_unit_selection(
    unit: str,
    unit_routing: Mapping[str, Any],
    catalog_list: list[dict[str, Any]],
) -> list[str]:
    from agency_runtime.core.selector.compatibility import enforce_compatible_set

    eligible_catalog, eligible_by_slug = _eligible_unit_catalog(unit_routing, catalog_list)
    selected = [
        slug
        for slug in _bounded_agent_ids(unit_routing.get("selected_ids"))
        if slug in eligible_by_slug and not is_resident_manager_slug(slug)
    ]
    inference_mode = str(unit_routing.get("inference_mode") or "")
    compatibility = unit_routing.get("compatibility")
    if unit_routing.get("inference_configured") is True and inference_mode != "inferred":
        selected = _policy_selection_for_degraded_route(unit_routing, selected)
        compatibility = enforce_compatible_set(
            selected,
            eligible_catalog,
            limit=len(selected),
        )
        selected = list(compatibility["selected_ids"])
    elif inference_mode == "heuristic" and unit_routing.get("status") == "token_fallback":
        selected = _deterministic_unit_selection(unit, eligible_catalog)
        compatibility = enforce_compatible_set(
            selected,
            eligible_catalog,
            limit=len(selected),
        )
        selected = list(compatibility["selected_ids"])
    else:
        semantic_ids = [
            slug
            for slug in _bounded_agent_ids(unit_routing.get("semantic_ids"))
            if slug in selected
        ]
        if semantic_ids:
            requested = semantic_ids[:1] if inference_mode == "heuristic" else semantic_ids
            compatibility = enforce_compatible_set(
                requested,
                eligible_catalog,
                limit=len(requested),
            )
            selected = list(compatibility["selected_ids"])
    if not isinstance(compatibility, Mapping):
        compatibility = enforce_compatible_set(
            selected,
            eligible_catalog,
            limit=len(selected),
        )
        selected = list(compatibility["selected_ids"])
    roots = (
        _bounded_agent_ids(compatibility.get("selected_root_ids"))
        if isinstance(compatibility, Mapping)
        else []
    )
    primary = next(
        (
            slug
            for slug in roots
            if slug in selected
            and (agent := eligible_by_slug.get(slug)) is not None
            and _supports_unit_deliverable(unit, agent)
        ),
        "",
    )
    return [primary, *(slug for slug in selected if slug != primary)] if primary else []


def _route_exact_unit(
    unit_entry: tuple[str, str],
    *,
    route: Any,
    catalog_list: list[dict[str, Any]],
    config: AgencyConfig,
    session_id: str,
    trace_id: str,
    host: str,
    platform: str,
    available_tools: tuple[str, ...] | None,
    capability_receipt: Mapping[str, Any] | HostCapabilityReceipt | None,
) -> tuple[str, list[str]]:
    work_unit_id, unit = unit_entry
    semantic_root_ids = tuple(
        slug
        for agent in catalog_list
        if _supports_unit_deliverable(unit, agent)
        and (
            slug := _clean(
                agent.get("slug") or agent.get("agent_slug"),
                MAX_AGENT_SLUG_CHARS,
            ).casefold()
        )
    )
    if not semantic_root_ids:
        return work_unit_id, []
    route_session_id = f"{session_id}:unit:{work_unit_id}"
    route_trace_id = f"{trace_id}:unit:{work_unit_id}" if trace_id else None
    diagnostic_receipt = (
        diagnostic_installation_capability_receipt(
            capability_receipt,
            surface=host,
            platform=platform,
        )
        if capability_receipt is not None
        else None
    )
    resolved_receipt = diagnostic_receipt or (
        capability_receipt if isinstance(capability_receipt, HostCapabilityReceipt) else None
    )
    capability_kwargs: dict[str, Any] = {}
    if resolved_receipt is not None:
        capability_kwargs = {
            "capability_receipt": resolved_receipt,
            "capability_session_id": session_id,
            "capability_trace_id": trace_id,
            "allow_installation_diagnostic": diagnostic_receipt is not None,
        }
    unit_routing = route(
        route_session_id,
        unit,
        catalog_list,
        config=config,
        store=None,
        trace_id=route_trace_id,
        host=host,
        platform=platform,
        available_tools=available_tools,
        semantic_root_ids=semantic_root_ids,
        **capability_kwargs,
    )
    return work_unit_id, _compatible_unit_selection(
        unit,
        unit_routing,
        catalog_list,
    )


def _route_unit_assignments(
    units: list[tuple[str, str]],
    *,
    catalog_list: list[dict[str, Any]],
    config: AgencyConfig,
    session_id: str,
    trace_id: str,
    host: str,
    platform: str,
    available_tools: tuple[str, ...] | None,
    capability_receipt: Mapping[str, Any] | HostCapabilityReceipt | None,
) -> list[tuple[str, list[str]]]:
    from agency_runtime.core.selector import pipeline
    from agency_runtime.core.selector.judge import inference_is_configured

    worker = partial(
        _route_exact_unit,
        route=pipeline.route,
        catalog_list=catalog_list,
        config=config,
        session_id=session_id,
        trace_id=trace_id,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
    )
    if len(units) < 2 or not inference_is_configured(config):
        return [worker(unit) for unit in units]
    with ThreadPoolExecutor(
        max_workers=min(MAX_UNIT_SELECTION_WORKERS, len(units)),
        thread_name_prefix="agency-unit-selection",
    ) as executor:
        return list(executor.map(worker, units))


def _add_assignment_candidate(
    candidates: dict[str, dict[str, Any]],
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
    slug: str,
    work_unit_id: str,
    *,
    primary: bool,
) -> None:
    winner = catalog_by_slug.get(slug)
    if winner is None:
        return
    if slug not in candidates and len(candidates) >= MAX_SUGGESTED_WORK_UNITS:
        return
    candidate = candidates.setdefault(
        slug,
        {
            "slug": slug,
            "name": winner.get("name"),
            "description": winner.get("description"),
            "capabilities": winner.get("capabilities"),
            "tags": [
                *_bounded_strings(winner.get("tags")),
                *_bounded_strings(winner.get("categories")),
            ],
            "required_tools": winner.get("required_tools"),
            "evidence_requirements": winner.get("evidence_requirements"),
            "matched_work_unit_ids": [],
            "primary_work_unit_ids": [],
        },
    )
    if work_unit_id not in candidate["matched_work_unit_ids"]:
        candidate["matched_work_unit_ids"].append(work_unit_id)
    if primary and work_unit_id not in candidate["primary_work_unit_ids"]:
        candidate["primary_work_unit_ids"].append(work_unit_id)


def _assignment_candidates(
    routed_units: list[tuple[str, list[str]]],
    catalog_by_slug: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    # Preserve one primary for every routable unit before spending the bounded
    # durable-reference budget on compatible secondary specialists.
    for work_unit_id, selected in routed_units:
        if selected:
            _add_assignment_candidate(
                candidates,
                catalog_by_slug,
                selected[0],
                work_unit_id,
                primary=True,
            )
    for work_unit_id, selected in routed_units:
        for slug in selected[1:]:
            _add_assignment_candidate(
                candidates,
                catalog_by_slug,
                slug,
                work_unit_id,
                primary=False,
            )
    return list(candidates.values())


def assignment_agents_from_catalog(
    catalog: Sequence[Mapping[str, Any]],
    routing: Mapping[str, Any],
    *,
    config: AgencyConfig | None = None,
    session_id: str = "unit-assignment",
    trace_id: str = "",
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: tuple[str, ...] | None = None,
    capability_receipt: Mapping[str, Any] | HostCapabilityReceipt | None = None,
) -> list[dict[str, Any]]:
    """Route every delegated unit through the complete eligible catalog.

    ``config=None`` deliberately constructs an unconfigured deterministic
    selector for isolated contract callers. Authoritative preflight always
    supplies its exact config and host-capability receipt.
    """

    units = _delegated_work_units(routing)
    if not units:
        return _selected_assignment_agents_from_catalog(catalog, routing)

    catalog_list, catalog_by_slug = _assignment_catalog(catalog)
    if not catalog_list:
        return []

    cfg = config or AgencyConfig(ollama=OllamaConfig(enabled=False))
    routed_units = _route_unit_assignments(
        units,
        catalog_list=catalog_list,
        config=cfg,
        session_id=session_id,
        trace_id=trace_id,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
    )
    return (
        project_unit_assignment_agents(_assignment_candidates(routed_units, catalog_by_slug)) or []
    )


def _tokens(value: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _AGENT_TOKEN_RE.findall(value.casefold())
        if token not in _SIGNAL_STOPWORDS
    )


def _signal_score(
    unit_tokens: frozenset[str],
    value: str,
    *,
    exact_weight: int,
    semantic_weight: int,
) -> int:
    signal_tokens = _tokens(value)
    exact = exact_weight * len(unit_tokens.intersection(signal_tokens))
    semantic = semantic_weight * sum(
        len(unit_tokens.intersection(_ROLE_SIGNALS.get(token, frozenset())))
        for token in signal_tokens
    )
    return exact + semantic


def _agent_score(
    unit: str,
    agent: str,
    metadata: Mapping[str, Any] | None,
) -> int:
    unit_tokens = _tokens(unit)
    if not unit_tokens:
        return 0
    score = _signal_score(
        unit_tokens,
        agent,
        exact_weight=8,
        semantic_weight=3,
    )
    if metadata is None:
        return score
    score += _signal_score(
        unit_tokens,
        str(metadata.get("name") or ""),
        exact_weight=6,
        semantic_weight=2,
    )
    score += _signal_score(
        unit_tokens,
        str(metadata.get("description") or ""),
        exact_weight=2,
        semantic_weight=1,
    )
    for capability in metadata.get("capabilities") or ():
        score += _signal_score(
            unit_tokens,
            str(capability),
            exact_weight=7,
            semantic_weight=4,
        )
    for tag in metadata.get("tags") or ():
        score += _signal_score(
            unit_tokens,
            str(tag),
            exact_weight=5,
            semantic_weight=3,
        )
    return score


def _recommended_agents(unit: str, routing: Mapping[str, Any]) -> list[str]:
    projected = project_unit_assignment_agents(routing.get("unit_assignment_agents")) or []
    catalog_assignment = any(item.get("matched_work_unit_ids") for item in projected)
    if catalog_assignment:
        work_unit_id = work_unit_id_from_text(unit)
        matched = [
            item["slug"]
            for item in projected
            if work_unit_id in item.get("matched_work_unit_ids", ())
        ]
        primary = next(
            (
                item["slug"]
                for item in projected
                if work_unit_id in item.get("primary_work_unit_ids", ())
            ),
            matched[0] if matched else "",
        )
        return [primary, *(slug for slug in matched if slug != primary)] if primary else []

    selected = [
        slug
        for slug in _bounded_agent_ids(routing.get("selected_ids"))
        if not is_resident_manager_slug(slug)
    ]
    # A routed sole specialist carries stronger domain evidence than a bounded
    # unit-token heuristic, even when its visible metadata is intentionally terse.
    if len(selected) == 1:
        return selected
    metadata = {item["slug"]: item for item in projected}
    scored = [
        (_agent_score(unit, slug, metadata.get(slug)), index, slug)
        for index, slug in enumerate(selected)
    ]
    matched = min(
        (item for item in scored if item[0] > 0),
        key=lambda item: (-item[0], item[1], item[2]),
        default=None,
    )
    return [matched[2]] if matched is not None else []


def work_unit_id_from_text(text: str) -> str:
    """Return a stable ID for a detected work-unit description."""

    normalized = _normalized_goal(text)
    digest = hashlib.sha256(normalized.encode("utf-8", errors="surrogatepass")).hexdigest()[:10]
    return f"unit-{digest}"


def _plan_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="surrogatepass")).hexdigest()


def _selection_confidence(work_units: Mapping[str, Any]) -> float:
    return {"high": 0.9, "medium": 0.7, "low": 0.5}.get(
        _clean(work_units.get("confidence"), 16).casefold(),
        0.5,
    )


def _delegation_strength(
    *,
    policy: DelegationConfig,
    unit_count: int,
    confidence: float,
) -> str:
    if policy.mode == "observe":
        return "optional"
    if policy.mode == "strong":
        return "strongly_preferred"
    if (
        unit_count >= policy.strongly_preferred_min_units
        and confidence >= policy.strongly_preferred_min_confidence
    ):
        return "strongly_preferred"
    return "preferred" if unit_count >= policy.preferred_min_units else "optional"


def _deliverable_kind(unit: str) -> str:
    if _REVIEW_DELIVERABLE_RE.search(unit):
        return "review"
    if _VERIFY_DELIVERABLE_RE.search(unit):
        return "verification"
    if _DOC_DELIVERABLE_RE.search(unit):
        return "documentation"
    if _WORKSPACE_MUTATION_RE.search(unit) or _EXTERNAL_MUTATION_RE.search(unit):
        return "implementation"
    return "outcome"


def _mutation_scope(unit: str) -> str:
    if _EXTERNAL_MUTATION_RE.search(unit):
        return "external_write"
    if _WORKSPACE_MUTATION_RE.search(unit):
        return "workspace_write"
    return "read_only"


def _resource_token_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value.lstrip("([{<").rstrip(".,:;!?)]}>")


def _looks_like_resource(value: str) -> bool:
    if not value or "://" in value:
        return False
    slash_value = value.replace("\\", "/")
    if _WINDOWS_ABSOLUTE_RESOURCE_RE.match(value):
        return True
    if slash_value.startswith(("/", "./", "../", "~/", "//")):
        return True
    if "/" in slash_value:
        return all(part not in {"", "."} for part in slash_value.split("/"))
    return _BARE_FILE_RESOURCE_RE.fullmatch(value) is not None


def _normalized_resource(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    return normalized.casefold()[:MAX_RESOURCE_CHARS]


def _likely_resources(unit: str) -> list[str]:
    resources: list[str] = []
    seen: set[str] = set()
    for match in _RESOURCE_TOKEN_RE.finditer(unit):
        value = _resource_token_value(match.group(0))
        if not _looks_like_resource(value):
            continue
        normalized = _normalized_resource(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            resources.append(normalized)
            if len(resources) >= MAX_PLAN_LIST_ITEMS:
                break
    return resources or ["repository-workspace"]


def _resource_contention_plan(
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, list[str]], set[str], bool]:
    """Build an acyclic, input-order dependency plan for overlapping resources."""

    dependencies = {str(item["work_unit_id"]): [] for item in candidates}
    contended: set[str] = set()
    unknown_mutation = any(
        item["mutation_scope"] != "read_only" and item["resources"] == ["repository-workspace"]
        for item in candidates
    )
    for index, current in enumerate(candidates):
        current_id = str(current["work_unit_id"])
        current_resources = set(current["resources"])
        if current_resources == {"repository-workspace"}:
            continue
        for previous in candidates[:index]:
            previous_resources = set(previous["resources"])
            if previous_resources == {"repository-workspace"}:
                continue
            if current_resources.isdisjoint(previous_resources):
                continue
            if (
                current["mutation_scope"] == "read_only"
                and previous["mutation_scope"] == "read_only"
            ):
                continue
            previous_id = str(previous["work_unit_id"])
            dependencies[current_id].append(previous_id)
            contended.update((current_id, previous_id))
    return dependencies, contended, unknown_mutation


def _parallelization_mode(
    candidate: Mapping[str, Any],
    *,
    contended: set[str],
    unknown_mutation: bool,
) -> str:
    work_unit_id = str(candidate["work_unit_id"])
    if work_unit_id in contended:
        return "sequential"
    if candidate["resources"] == ["repository-workspace"]:
        return "unspecified"
    if unknown_mutation and candidate["mutation_scope"] != "read_only":
        return "unspecified"
    return "parallel"


def _metadata_for_agent(routing: Mapping[str, Any], slug: str) -> Mapping[str, Any]:
    return next(
        (
            item
            for item in project_unit_assignment_agents(routing.get("unit_assignment_agents")) or []
            if item.get("slug") == slug
        ),
        {},
    )


def _metadata_union(
    routing: Mapping[str, Any],
    agents: Sequence[str],
    field: str,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for agent in agents:
        for value in _bounded_strings(_metadata_for_agent(routing, agent).get(field)):
            identity = value.casefold()
            if identity in seen:
                continue
            seen.add(identity)
            result.append(value)
            if len(result) >= MAX_ASSIGNMENT_AGENT_LABELS:
                return result
    return result


def _bounded_plan_strings(value: Any, *, digests: bool = False) -> list[str] | None:
    if not isinstance(value, list) or len(value) > MAX_PLAN_LIST_ITEMS:
        return None
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        item = str(raw or "").strip()
        if (
            not item
            or len(item) > MAX_PLAN_LIST_ITEM_CHARS
            or any(ord(character) < 32 or ord(character) == 127 for character in item)
            or (digests and _DIGEST_RE.fullmatch(item.casefold()) is None)
        ):
            return None
        normalized = item.casefold() if digests else item
        if normalized in seen:
            return None
        seen.add(normalized)
        result.append(normalized if digests else item)
    return result


def project_unit_agent_plan(
    value: Any,
    *,
    allow_legacy: bool = True,
    require_current: bool = False,
) -> list[dict[str, Any]] | None:
    """Validate one bounded durable plan without persisting task content."""

    if not isinstance(value, (list, tuple)) or len(value) > MAX_SUGGESTED_WORK_UNITS:
        return None
    result: list[dict[str, Any]] = []
    versions: set[int] = set()
    seen: set[str] = set()
    legacy_fields = {"assignment_version", "work_unit_id", "recommended_agent"}
    current_fields = {
        *legacy_fields,
        "goal_hash",
        "deliverable_kind",
        "recommended_agents",
        "selection_confidence",
        "rationale_codes",
        "depends_on",
        "parallelization",
        "mutation_scope",
        "resource_hashes",
        "required_tools",
        "required_evidence",
        "delegation_strength",
    }
    for raw in value:
        if not isinstance(raw, Mapping):
            return None
        assignment_text = str(raw.get("assignment_version") or "1").strip()
        if not assignment_text.isdecimal():
            return None
        assignment_version = int(assignment_text)
        work_unit_id = str(raw.get("work_unit_id") or "").strip().casefold()
        agent = str(raw.get("recommended_agent") or "").strip().casefold()
        if (
            _WORK_UNIT_ID_RE.fullmatch(work_unit_id) is None
            or not agent
            or len(agent) > MAX_AGENT_SLUG_CHARS
            or any(ord(character) < 32 or ord(character) == 127 for character in agent)
            or is_resident_manager_slug(agent)
            or work_unit_id in seen
        ):
            return None
        if assignment_version < UNIT_AGENT_ASSIGNMENT_VERSION:
            if require_current or not allow_legacy or set(raw) - legacy_fields:
                return None
            projected = {
                "assignment_version": str(assignment_version),
                "work_unit_id": work_unit_id,
                "recommended_agent": agent,
            }
        elif assignment_version == UNIT_AGENT_ASSIGNMENT_VERSION:
            if set(raw) != current_fields:
                return None
            goal_hash = str(raw.get("goal_hash") or "").strip().casefold()
            deliverable_kind = str(raw.get("deliverable_kind") or "").strip().casefold()
            recommended_agents = _bounded_plan_strings(raw.get("recommended_agents"))
            rationale_codes = _bounded_plan_strings(raw.get("rationale_codes"))
            depends_on = _bounded_work_unit_ids(raw.get("depends_on"), strict=True)
            resource_hashes = _bounded_plan_strings(raw.get("resource_hashes"), digests=True)
            required_tools = _bounded_plan_strings(raw.get("required_tools"))
            required_evidence = _bounded_plan_strings(raw.get("required_evidence"))
            parallelization = str(raw.get("parallelization") or "").strip().casefold()
            mutation_scope = str(raw.get("mutation_scope") or "").strip().casefold()
            strength = str(raw.get("delegation_strength") or "").strip().casefold()
            confidence = raw.get("selection_confidence")
            if (
                _DIGEST_RE.fullmatch(goal_hash) is None
                or deliverable_kind not in DELIVERABLE_KINDS
                or recommended_agents is None
                or not recommended_agents
                or recommended_agents[0].casefold() != agent
                or len({item.casefold() for item in recommended_agents}) != len(recommended_agents)
                or any(len(item) > MAX_AGENT_SLUG_CHARS for item in recommended_agents)
                or rationale_codes is None
                or not rationale_codes
                or any(_RATIONALE_CODE_RE.fullmatch(item) is None for item in rationale_codes)
                or depends_on is None
                or work_unit_id in depends_on
                or parallelization not in PARALLELIZATION_MODES
                or mutation_scope not in MUTATION_SCOPES
                or resource_hashes is None
                or required_tools is None
                or required_evidence is None
                or strength not in DELEGATION_STRENGTHS
                or isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not math.isfinite(float(confidence))
                or not 0.0 <= float(confidence) <= 1.0
            ):
                return None
            projected = {
                "assignment_version": str(assignment_version),
                "work_unit_id": work_unit_id,
                "goal_hash": goal_hash,
                "deliverable_kind": deliverable_kind,
                "recommended_agent": agent,
                "recommended_agents": [item.casefold() for item in recommended_agents],
                "selection_confidence": round(float(confidence), 6),
                "rationale_codes": rationale_codes,
                "depends_on": depends_on,
                "parallelization": parallelization,
                "mutation_scope": mutation_scope,
                "resource_hashes": resource_hashes,
                "required_tools": required_tools,
                "required_evidence": required_evidence,
                "delegation_strength": strength,
            }
        else:
            return None
        versions.add(assignment_version)
        seen.add(work_unit_id)
        result.append(projected)
    if len(versions) > 1:
        return None
    return result


_DELIVERABLE_TEXT = {
    "implementation": "Verified implementation satisfying this work unit.",
    "review": "Prioritized findings with concrete evidence and remediation.",
    "verification": "Reproducible verification results and supporting evidence.",
    "documentation": "Updated documentation with validation evidence.",
    "outcome": "Completed outcome with concise supporting evidence.",
}


def hydrate_unit_agent_plan(
    routing: Mapping[str, Any],
    plan: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Re-derive exact task/resource text from the correlated current request."""

    projected = project_unit_agent_plan(list(plan), require_current=True)
    if projected is None:
        raise RuntimeError("durable unit-agent plan is invalid")
    work_units = routing.get("work_units")
    raw_units = work_units.get("units") if isinstance(work_units, Mapping) else None
    if not isinstance(raw_units, (list, tuple)):
        raise RuntimeError("current request has no replayable work units")
    if len(raw_units) > MAX_SUGGESTED_WORK_UNITS:
        raise RuntimeError("current request exceeds the work-unit plan bound")
    tasks: dict[str, str] = {}
    for raw in raw_units:
        unit = _normalized_goal(raw)
        if unit:
            tasks.setdefault(work_unit_id_from_text(unit), unit)
    hydrated: list[dict[str, Any]] = []
    for item in projected:
        unit = tasks.get(item["work_unit_id"])
        if unit is None or _plan_hash(unit) != item["goal_hash"]:
            raise RuntimeError("durable unit-agent plan does not match the current request")
        resources = _likely_resources(unit)
        if [_plan_hash(resource) for resource in resources] != item["resource_hashes"]:
            raise RuntimeError("durable unit-agent resource plan does not match")
        rationale = (
            f"{item['delegation_strength']} native delegation; "
            f"selection confidence {item['selection_confidence']:.2f}; "
            + ", ".join(item["rationale_codes"])
        )
        hydrated.append(
            {
                **item,
                "goal": unit,
                "goal_preview": _goal_preview(unit),
                "expected_deliverable": _DELIVERABLE_TEXT[item["deliverable_kind"]],
                "compatible_specialists": list(item["recommended_agents"]),
                "confidence": item["selection_confidence"],
                "rationale": rationale[:512],
                "dependencies": list(item["depends_on"]),
                "parallelization_hints": item["parallelization"],
                "likely_files_or_resources": resources,
            }
        )
    return hydrated


def build_unit_agent_plan(
    routing: Mapping[str, Any],
    policy: DelegationConfig | None = None,
) -> list[dict[str, Any]]:
    """Return a bounded, deterministic native-host plan for each work unit."""

    work_units = routing.get("work_units")
    if not isinstance(work_units, Mapping) or not work_units.get("delegate"):
        return []
    raw_units = work_units.get("units")
    if not isinstance(raw_units, (list, tuple)):
        return []
    if len(raw_units) > MAX_SUGGESTED_WORK_UNITS:
        return []
    metadata = project_unit_assignment_agents(routing.get("unit_assignment_agents")) or []
    catalog_assignment = any(item.get("matched_work_unit_ids") for item in metadata)
    assignment_version = (
        _CATALOG_UNIT_AGENT_ASSIGNMENT_VERSION
        if catalog_assignment
        else (
            _SELECTED_ONLY_UNIT_AGENT_ASSIGNMENT_VERSION
            if metadata
            else LEGACY_UNIT_AGENT_ASSIGNMENT_VERSION
        )
    )
    active_policy = policy or DelegationConfig()
    unit_count = len(raw_units)
    confidence = _selection_confidence(work_units)
    strength = _delegation_strength(
        policy=active_policy,
        unit_count=unit_count,
        confidence=confidence,
    )
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_unit in raw_units:
        unit = _normalized_goal(raw_unit)
        if not unit:
            continue
        work_unit_id = work_unit_id_from_text(unit)
        if work_unit_id in seen:
            continue
        agents = _recommended_agents(unit, routing)
        if not agents:
            continue
        agent = agents[0]
        seen.add(work_unit_id)
        resources = _likely_resources(unit)
        candidates.append(
            {
                "work_unit_id": work_unit_id,
                "unit": unit,
                "deliverable_kind": _deliverable_kind(unit),
                "recommended_agent": agent,
                "recommended_agents": agents,
                "mutation_scope": _mutation_scope(unit),
                "resources": resources,
                "required_tools": _metadata_union(routing, agents, "required_tools"),
                "required_evidence": _metadata_union(
                    routing,
                    agents,
                    "evidence_requirements",
                ),
            }
        )
    dependencies, contended, unknown_mutation = _resource_contention_plan(candidates)
    suggestions = [
        {
            "assignment_version": str(UNIT_AGENT_ASSIGNMENT_VERSION),
            "work_unit_id": candidate["work_unit_id"],
            "goal_hash": _plan_hash(candidate["unit"]),
            "deliverable_kind": candidate["deliverable_kind"],
            "recommended_agent": candidate["recommended_agent"],
            "recommended_agents": candidate["recommended_agents"],
            "selection_confidence": confidence,
            "rationale_codes": [
                f"detected:{_clean(work_units.get('source'), 32).casefold() or 'unknown'}",
                f"assignment:v{assignment_version}",
                f"policy:{active_policy.mode}",
            ],
            "depends_on": dependencies[str(candidate["work_unit_id"])],
            "parallelization": _parallelization_mode(
                candidate,
                contended=contended,
                unknown_mutation=unknown_mutation,
            ),
            "mutation_scope": candidate["mutation_scope"],
            "resource_hashes": [_plan_hash(resource) for resource in candidate["resources"]],
            "required_tools": candidate["required_tools"],
            "required_evidence": candidate["required_evidence"],
            "delegation_strength": strength,
        }
        for candidate in candidates
    ]
    projected = project_unit_agent_plan(suggestions, require_current=True)
    if projected is None:
        raise RuntimeError("generated unit-agent plan is invalid")
    return projected


__all__ = [
    "DELEGATION_STRENGTHS",
    "LEGACY_UNIT_AGENT_ASSIGNMENT_VERSION",
    "MAX_SUGGESTED_WORK_UNITS",
    "MAX_WORK_UNIT_CHARS",
    "MAX_WORK_UNIT_PREVIEW_CHARS",
    "MAX_WORK_UNIT_TRANSPORT_CHARS",
    "UNIT_AGENT_ASSIGNMENT_VERSION",
    "assignment_agents_from_catalog",
    "build_unit_agent_plan",
    "hydrate_unit_agent_plan",
    "project_unit_agent_plan",
    "project_unit_assignment_agents",
    "work_unit_id_from_text",
]
