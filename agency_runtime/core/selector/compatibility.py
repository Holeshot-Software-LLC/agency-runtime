"""Hard eligibility and compatible specialist-set construction.

Inference proposes expertise.  This module remains the deterministic authority
for host/platform/tool eligibility, explicit requirements, and prompt-level
conflicts before any specialist body is hydrated.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Container, Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.host_capabilities import (
    EXECUTION_HOSTS,
    INFERENCE_SURFACES,
    SUPPORTED_PLATFORMS,
    canonicalize_tool_capabilities,
    execution_contract_projection,
    expand_compatible_hosts,
)

COMPATIBILITY_CONTRACT_VERSION = 1
MAX_COMPATIBLE_SPECIALISTS = 16
_KNOWN_HOSTS = frozenset(EXECUTION_HOSTS)
_KNOWN_INFERENCE_SURFACES = frozenset(INFERENCE_SURFACES)
_KNOWN_PLATFORMS = frozenset(SUPPORTED_PLATFORMS)
_EXCLUSIVE_AUTHORITIES = frozenset({"modify", "approve"})
_ELIGIBILITY_CACHE_MAX_ENTRIES = 4
_EligibilityAgentKey = tuple[Any, ...]
_EligibilityContentKey = tuple[
    tuple[_EligibilityAgentKey, ...],
    str,
    str,
    str,
    str,
    tuple[str, ...] | None,
]
_EligibilityIdentityKey = tuple[int, str, str, str, str, tuple[str, ...] | None]


def _slug(agent: dict[str, Any]) -> str:
    return agent_identity(agent)


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(text for item in value if (text := str(item or "").strip())))


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    """One bounded full-roster hard-filter projection."""

    eligible: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, str], ...]
    eligible_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class CompatibilityCatalog:
    """Pre-indexed immutable catalog for exhaustive or repeated composition checks."""

    by_slug: Mapping[str, dict[str, Any]]


def compile_compatibility_catalog(
    catalog: Sequence[dict[str, Any]],
) -> CompatibilityCatalog:
    """Validate unique identities once and reuse the deterministic composition index."""

    by_slug = {_slug(agent): agent for agent in catalog if _slug(agent)}
    if len(by_slug) != sum(bool(_slug(agent)) for agent in catalog):
        raise ValueError("compatibility catalog contains duplicate specialist identities")
    return CompatibilityCatalog(MappingProxyType(by_slug))


@dataclass(frozen=True, slots=True)
class _EligibilityCacheEntry:
    """Complete detached content proof for one eligibility projection."""

    catalog: Sequence[dict[str, Any]]
    snapshot: Sequence[dict[str, Any]]
    result: EligibilityResult
    eligible_positions: tuple[int, ...]


_ELIGIBILITY_CACHE: OrderedDict[_EligibilityContentKey, _EligibilityCacheEntry] = OrderedDict()
_ELIGIBILITY_IDENTITY_CACHE: OrderedDict[
    _EligibilityIdentityKey,
    _EligibilityCacheEntry,
] = OrderedDict()
_ELIGIBILITY_CACHE_LOCK = threading.RLock()


def _cache_eligibility_result(
    catalog: Sequence[dict[str, Any]],
    *,
    cache_key: _EligibilityContentKey,
    identity_key: _EligibilityIdentityKey,
    result: EligibilityResult,
) -> EligibilityResult:
    try:
        snapshot = deepcopy(catalog)
    except Exception:
        # Eligibility reads only the bounded contract fields. Opaque caller
        # metadata must not make an otherwise valid route fail; skip reuse when
        # no detached proof can be created.
        return result
    eligible_identities = {id(agent) for agent in result.eligible}
    entry = _EligibilityCacheEntry(
        catalog,
        snapshot,
        result,
        tuple(index for index, agent in enumerate(catalog) if id(agent) in eligible_identities),
    )
    with _ELIGIBILITY_CACHE_LOCK:
        _ELIGIBILITY_CACHE[cache_key] = entry
        _ELIGIBILITY_CACHE.move_to_end(cache_key)
        _ELIGIBILITY_IDENTITY_CACHE[identity_key] = entry
        _ELIGIBILITY_IDENTITY_CACHE.move_to_end(identity_key)
        while len(_ELIGIBILITY_CACHE) > _ELIGIBILITY_CACHE_MAX_ENTRIES:
            _ELIGIBILITY_CACHE.popitem(last=False)
        while len(_ELIGIBILITY_IDENTITY_CACHE) > _ELIGIBILITY_CACHE_MAX_ENTRIES:
            _ELIGIBILITY_IDENTITY_CACHE.popitem(last=False)
    return result


def _eligibility_contract_key(
    agent: dict[str, Any],
) -> _EligibilityAgentKey:
    """Project every field that can change hard eligibility."""

    operational = execution_contract_projection(agent)
    return (
        _slug(agent),
        agent.get("routing_contract_valid") is False,
        str(agent.get("audit_status") or "").strip().casefold(),
        str(agent.get("authority") or "").strip().casefold(),
        str(agent.get("context_mode") or "").strip().casefold(),
        tuple(operational["required_capabilities"]),
        tuple(operational["unknown_required_tools"]),
        tuple(operational["supported_execution_hosts"]),
        tuple(operational["supported_inference_surfaces"]),
        tuple(operational["unknown_supported_surfaces"]),
        tuple(operational["supported_reasoning_platforms"]),
        tuple(operational["supported_tool_platforms"]),
    )


def _bind_equivalent_identity(
    catalog: Sequence[dict[str, Any]],
    *,
    identity_key: _EligibilityIdentityKey,
    cached: _EligibilityCacheEntry,
) -> EligibilityResult:
    """Rebind a content-equivalent result to the caller's agent mappings."""

    result = EligibilityResult(
        tuple(catalog[index] for index in cached.eligible_positions),
        cached.result.rejected,
        cached.result.eligible_ids,
    )
    entry = _EligibilityCacheEntry(
        catalog,
        cached.snapshot,
        result,
        cached.eligible_positions,
    )
    with _ELIGIBILITY_CACHE_LOCK:
        _ELIGIBILITY_IDENTITY_CACHE[identity_key] = entry
        _ELIGIBILITY_IDENTITY_CACHE.move_to_end(identity_key)
        while len(_ELIGIBILITY_IDENTITY_CACHE) > _ELIGIBILITY_CACHE_MAX_ENTRIES:
            _ELIGIBILITY_IDENTITY_CACHE.popitem(last=False)
    return result


@dataclass(frozen=True, slots=True)
class _EligibilityContext:
    host: str
    platform: str
    inference_surface: str
    tools: frozenset[str] | None
    capability_status: str


def _inference_surface_reason(
    agent: dict[str, Any],
    operational: dict[str, list[str]],
    context: _EligibilityContext,
) -> str:
    surface = context.inference_surface
    authority = str(agent.get("authority") or "").strip().casefold()
    context_mode = str(agent.get("context_mode") or "").strip().casefold()
    if surface not in _KNOWN_INFERENCE_SURFACES:
        return f"unknown_inference_surface:{surface}"
    if surface not in operational["supported_inference_surfaces"]:
        return f"unsupported_inference_surface:{surface}"
    if context_mode != "direct_safe" or authority in _EXCLUSIVE_AUTHORITIES:
        return f"inference_surface_requires_isolation:{surface}"
    if _strings(agent.get("required_tools")):
        return "inference_surface_has_no_execution_tools"
    if (
        context.platform in _KNOWN_PLATFORMS
        and operational["supported_reasoning_platforms"]
        and context.platform not in operational["supported_reasoning_platforms"]
    ):
        return f"unsupported_reasoning_platform:{context.platform}"
    return ""


def _tool_requirement_reason(
    operational: dict[str, list[str]],
    context: _EligibilityContext,
) -> str:
    if context.host not in _KNOWN_HOSTS:
        return "execution_host_unproven"
    # ADR-0087: a host that reuses another host's hook model (zcode reuses
    # codex/claude) is eligible for any specialist declaring the compatible
    # host. Expand before the membership test so existing contracts need not
    # list every new host.
    supported = expand_compatible_hosts(operational["supported_execution_hosts"])
    if operational["supported_execution_hosts"] and context.host not in supported:
        return f"unsupported_execution_host:{context.host}"
    if (
        context.platform in _KNOWN_PLATFORMS
        and operational["supported_tool_platforms"]
        and context.platform not in operational["supported_tool_platforms"]
    ):
        return f"unsupported_tool_platform:{context.platform}"
    if operational["unknown_required_tools"]:
        return "unknown_tool_requirement:" + ",".join(sorted(operational["unknown_required_tools"]))
    if context.tools is None or context.capability_status in {
        "unknown",
        "explicit-tools-without-execution-host",
    }:
        return f"tool_capabilities_unproven:{context.capability_status}"
    missing = set(operational["required_capabilities"]).difference(context.tools)
    return "missing_capabilities:" + ",".join(sorted(missing)) if missing else ""


def _reasoning_reason(
    agent: dict[str, Any],
    operational: dict[str, list[str]],
    context: _EligibilityContext,
) -> str:
    if (
        context.host in _KNOWN_HOSTS
        and operational["supported_execution_hosts"]
        and context.host not in expand_compatible_hosts(operational["supported_execution_hosts"])
    ):
        return f"unsupported_execution_host:{context.host}"
    context_mode = str(agent.get("context_mode") or "").strip().casefold()
    if context.host not in _KNOWN_HOSTS and context_mode == "isolated_only":
        return "execution_host_unproven"
    if (
        context.platform in _KNOWN_PLATFORMS
        and operational["supported_reasoning_platforms"]
        and context.platform not in operational["supported_reasoning_platforms"]
    ):
        return f"unsupported_reasoning_platform:{context.platform}"
    return ""


def _eligibility_reason(agent: dict[str, Any], context: _EligibilityContext) -> str:
    slug = _slug(agent)
    audit_status = str(agent.get("audit_status") or "").strip().casefold()
    operational = execution_contract_projection(agent)
    if not slug:
        return "missing_slug"
    if agent.get("routing_contract_valid") is False:
        return "invalid_routing_contract"
    if audit_status and audit_status != "approved":
        return f"audit_status:{audit_status}"
    if operational["unknown_supported_surfaces"]:
        return "unknown_supported_surface:" + ",".join(
            sorted(operational["unknown_supported_surfaces"])
        )
    if context.inference_surface:
        return _inference_surface_reason(agent, operational, context)
    if _strings(agent.get("required_tools")):
        return _tool_requirement_reason(operational, context)
    return _reasoning_reason(agent, operational, context)


def filter_eligible_catalog(
    catalog: Sequence[dict[str, Any]],
    *,
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: Container[str] | None = None,
    inference_surface: str = "",
    capability_status: str = "",
) -> EligibilityResult:
    """Apply deterministic execution and reasoning constraints before scoring.

    ``available_tools=None`` means that tool capability is unproven.  An empty
    container is a known empty set.  The distinction is intentional and keeps
    tool-dependent specialists fail closed while leaving tool-free reasoning
    specialists routable.
    """

    normalized_host = str(host or "unknown").strip().casefold()
    normalized_platform = str(platform or "unknown").strip().casefold()
    normalized_inference_surface = str(inference_surface or "").strip().casefold()
    if normalized_host in _KNOWN_INFERENCE_SURFACES and not normalized_inference_surface:
        normalized_inference_surface = normalized_host
        normalized_host = "unknown"
    normalized_tools: frozenset[str] | None
    if available_tools is None:
        normalized_tools = None
    else:
        canonical_tools, _unknown_available = canonicalize_tool_capabilities(available_tools)
        normalized_tools = frozenset(canonical_tools)
    normalized_capability_status = str(capability_status or "").strip().casefold()
    if not normalized_capability_status:
        normalized_capability_status = "explicit" if available_tools is not None else "unknown"
    eligibility_context = _EligibilityContext(
        host=normalized_host,
        platform=normalized_platform,
        inference_surface=normalized_inference_surface,
        tools=normalized_tools,
        capability_status=normalized_capability_status,
    )
    tools_key = tuple(sorted(normalized_tools)) if normalized_tools is not None else None
    identity_key = (
        id(catalog),
        normalized_host,
        normalized_platform,
        normalized_inference_surface,
        normalized_capability_status,
        tools_key,
    )
    with _ELIGIBILITY_CACHE_LOCK:
        identity_cached = _ELIGIBILITY_IDENTITY_CACHE.get(identity_key)
    if (
        identity_cached is not None
        and identity_cached.catalog is catalog
        and identity_cached.snapshot == catalog
    ):
        with _ELIGIBILITY_CACHE_LOCK:
            if _ELIGIBILITY_IDENTITY_CACHE.get(identity_key) is identity_cached:
                _ELIGIBILITY_IDENTITY_CACHE.move_to_end(identity_key)
        return identity_cached.result

    cache_key = (
        tuple(_eligibility_contract_key(agent) for agent in catalog),
        normalized_host,
        normalized_platform,
        normalized_inference_surface,
        normalized_capability_status,
        tools_key,
    )
    with _ELIGIBILITY_CACHE_LOCK:
        cached = _ELIGIBILITY_CACHE.get(cache_key)
    if cached is not None and cached.catalog == catalog and cached.snapshot == catalog:
        with _ELIGIBILITY_CACHE_LOCK:
            if _ELIGIBILITY_CACHE.get(cache_key) is cached:
                _ELIGIBILITY_CACHE.move_to_end(cache_key)
        return _bind_equivalent_identity(
            catalog,
            identity_key=identity_key,
            cached=cached,
        )

    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    eligible_ids: set[str] = set()
    for agent in catalog:
        agent_slug = _slug(agent)
        reason = _eligibility_reason(agent, eligibility_context)
        if reason:
            rejected.append({"slug": agent_slug, "reason": reason})
        else:
            eligible.append(agent)
            eligible_ids.add(agent_slug)
    return _cache_eligibility_result(
        catalog,
        cache_key=cache_key,
        identity_key=identity_key,
        result=EligibilityResult(
            tuple(eligible),
            tuple(rejected),
            frozenset(eligible_ids),
        ),
    )


def clear_eligibility_cache() -> None:
    """Clear bounded eligibility projections for tests and roster reloads."""

    with _ELIGIBILITY_CACHE_LOCK:
        _ELIGIBILITY_CACHE.clear()
        _ELIGIBILITY_IDENTITY_CACHE.clear()


def _explicit_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_slug = _slug(left)
    right_slug = _slug(right)
    return right_slug in _strings(left.get("conflicts_with")) or left_slug in _strings(
        right.get("conflicts_with")
    )


def _authority_conflict(left: dict[str, Any], right: dict[str, Any]) -> bool:
    group = str(left.get("independence_group") or "").strip()
    if not group or group != str(right.get("independence_group") or "").strip():
        return False
    left_authority = str(left.get("authority") or "").strip().casefold()
    right_authority = str(right.get("authority") or "").strip().casefold()
    return left_authority == right_authority and left_authority in _EXCLUSIVE_AUTHORITIES


def _separate_context_required(left: dict[str, Any], right: dict[str, Any]) -> bool:
    authorities = {
        str(left.get("authority") or "").strip().casefold(),
        str(right.get("authority") or "").strip().casefold(),
    }
    return (
        str(left.get("context_mode") or "").strip().casefold() == "isolated_only"
        or str(right.get("context_mode") or "").strip().casefold() == "isolated_only"
        or authorities == {"modify", "review"}
    )


def _requested_priority(
    requested: Sequence[str],
    by_slug: dict[str, dict[str, Any]],
) -> list[str]:
    """Consider dependents before requested identities they already require."""

    dependency_ids: set[str] = set()
    for root in requested:
        pending = list(_strings(by_slug.get(root, {}).get("requires")))
        seen: set[str] = set()
        while pending:
            dependency = pending.pop()
            if dependency in seen:
                continue
            seen.add(dependency)
            dependency_ids.add(dependency)
            pending.extend(_strings(by_slug.get(dependency, {}).get("requires")))
    return [slug for slug in requested if slug not in dependency_ids] + [
        slug for slug in requested if slug in dependency_ids
    ]


def _requirement_closure(
    root: str,
    by_slug: dict[str, dict[str, Any]],
) -> tuple[list[str], str]:
    """Resolve one root's dependency-first closure without mutating selection."""

    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(slug: str) -> str:
        if slug in visited:
            return ""
        if slug in visiting:
            return f"requirement_cycle:{slug}"
        agent = by_slug.get(slug)
        if agent is None:
            return f"missing_requirement:{slug}"
        visiting.add(slug)
        for dependency in _strings(agent.get("requires")):
            reason = visit(dependency)
            if reason:
                visiting.discard(slug)
                return reason
        visiting.remove(slug)
        visited.add(slug)
        ordered.append(slug)
        return ""

    reason = visit(root)
    return ([] if reason else ordered), reason


def _closure_conflict(
    closure: Sequence[str],
    accepted: Sequence[str],
    by_slug: dict[str, dict[str, Any]],
) -> str:
    """Return the first accepted or intra-closure conflict for an atomic root."""

    staged = list(accepted)
    for slug in closure:
        if slug in staged:
            continue
        agent = by_slug[slug]
        conflict = next(
            (
                staged_slug
                for staged_slug in staged
                if _explicit_conflict(agent, by_slug[staged_slug])
                or _authority_conflict(agent, by_slug[staged_slug])
            ),
            "",
        )
        if conflict:
            return conflict
        staged.append(slug)
    return ""


def enforce_compatible_set(
    selected_ids: Iterable[object],
    catalog: Sequence[dict[str, Any]] | CompatibilityCatalog,
    *,
    limit: int = MAX_COMPATIBLE_SPECIALISTS,
    review_overflow_ids: Iterable[object] = (),
) -> dict[str, Any]:
    """Return the smallest deterministic compatible closure of one proposal.

    ``limit`` bounds requested specialists. Explicit ``requires`` closure does
    not consume that budget, because dropping a declared dependency would make
    the selected root unusable. At most one explicitly authorized review root
    may exceed the budget, and only when it must run separately from an already
    accepted non-review root. The absolute safety bound remains
    ``MAX_COMPATIBLE_SPECIALISTS``.
    """

    maximum = max(0, min(int(limit), MAX_COMPATIBLE_SPECIALISTS))
    requested = list(
        dict.fromkeys(str(item or "").strip() for item in selected_ids if str(item or "").strip())
    )[:MAX_COMPATIBLE_SPECIALISTS]
    review_overflow = {
        str(item or "").strip() for item in review_overflow_ids if str(item or "").strip()
    }
    by_slug = (
        catalog.by_slug
        if isinstance(catalog, CompatibilityCatalog)
        else {_slug(agent): agent for agent in catalog if _slug(agent)}
    )
    rejected: list[dict[str, str]] = []
    added_requirements: list[str] = []
    accepted: list[str] = []
    accepted_requested: list[str] = []
    overflow_reviews: list[str] = []
    for slug in _requested_priority(requested, by_slug):
        if slug in accepted:
            # A higher-priority accepted root already carries this requested
            # identity as a requirement; adding it again cannot add value.
            continue
        closure, requirement_error = _requirement_closure(slug, by_slug)
        if requirement_error:
            rejected.append({"slug": slug, "reason": requirement_error})
            continue
        conflict = _closure_conflict(closure, accepted, by_slug)
        if conflict:
            rejected.append({"slug": slug, "reason": f"conflicts_with:{conflict}"})
            continue
        agent = by_slug[slug]
        over_budget = len(accepted_requested) >= maximum
        review_exception = bool(
            over_budget
            and not overflow_reviews
            and slug in review_overflow
            and str(agent.get("authority") or "").strip().casefold() == "review"
            and any(
                str(by_slug[accepted_slug].get("authority") or "").strip().casefold() != "review"
                and _separate_context_required(by_slug[accepted_slug], agent)
                for accepted_slug in accepted_requested
            )
        )
        if over_budget and not review_exception:
            rejected.append({"slug": slug, "reason": "compatible_set_limit"})
            continue
        new_ids = [closure_slug for closure_slug in closure if closure_slug not in accepted]
        if len(accepted) + len(new_ids) > MAX_COMPATIBLE_SPECIALISTS:
            rejected.append({"slug": slug, "reason": "compatible_set_limit"})
            continue
        accepted.extend(new_ids)
        accepted_requested.append(slug)
        for dependency in closure:
            if (
                dependency != slug
                and dependency not in requested
                and dependency not in added_requirements
            ):
                added_requirements.append(dependency)
        if review_exception:
            overflow_reviews.append(slug)

    separate_context_pairs = [
        [left, right]
        for index, left in enumerate(accepted)
        for right in accepted[index + 1 :]
        if _separate_context_required(by_slug[left], by_slug[right])
    ]
    return {
        "contract_version": COMPATIBILITY_CONTRACT_VERSION,
        "requested_ids": requested,
        "selected_ids": accepted,
        "selection_limit": maximum,
        "selected_root_ids": accepted_requested,
        "added_requirements": added_requirements,
        "overflow_review_ids": overflow_reviews,
        "rejected": rejected,
        "separate_context_pairs": separate_context_pairs,
        "compatible": not rejected,
    }


__all__ = [
    "COMPATIBILITY_CONTRACT_VERSION",
    "MAX_COMPATIBLE_SPECIALISTS",
    "CompatibilityCatalog",
    "EligibilityResult",
    "clear_eligibility_cache",
    "compile_compatibility_catalog",
    "enforce_compatible_set",
    "filter_eligible_catalog",
]
