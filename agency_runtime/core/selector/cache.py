"""Content-hash cache for routing results."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.agent_identity import agent_identity

_CACHE_TTL_SECONDS = float(600)
_CACHE_MAX_ENTRIES = 128

_ROUTING_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_ACTIVE_IDS_CACHE: OrderedDict[str, _ActiveIdsEntry] = OrderedDict()
_CACHE_LOCK = threading.RLock()
_FINGERPRINT_MAX_ENTRIES = 32


@dataclass(frozen=True, slots=True)
class _MutationSnapshot:
    """A detached value snapshot, with a lightweight fallback for exotic inputs."""

    value: Any
    complete: bool


@dataclass(frozen=True, slots=True)
class _FingerprintEntry:
    """Memoized fingerprint and the state that proved it is still valid."""

    catalog: list[dict[str, Any]]
    config: Any
    policy: dict[str, Any]
    catalog_snapshot: _MutationSnapshot
    policy_snapshot: _MutationSnapshot
    fingerprint: str
    active_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class _ActiveIdsEntry:
    """Active identities plus a detached collision-defense proof."""

    catalog_snapshot: _MutationSnapshot
    active_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class _RecentActiveIds:
    """One-shot active IDs proven by the immediately preceding fingerprint."""

    catalog: list[dict[str, Any]]
    active_ids: frozenset[str]


_FINGERPRINT_CACHE: OrderedDict[tuple[int, int, int], _FingerprintEntry] = OrderedDict()
_EQUIVALENT_FINGERPRINT_CACHE: OrderedDict[
    tuple[int, int],
    _FingerprintEntry,
] = OrderedDict()
_RECENT_FINGERPRINT_ACTIVE: OrderedDict[int, _RecentActiveIds] = OrderedDict()


def _active_ids(catalog: list[dict[str, Any]]) -> frozenset[str]:
    return frozenset(identity for agent in catalog if (identity := agent_identity(agent)))


def _remember_fingerprint_active(
    catalog: list[dict[str, Any]],
    active_ids: frozenset[str],
) -> None:
    """Bridge the atomic fingerprint proof to its immediate active-ID read."""

    key = id(catalog)
    with _CACHE_LOCK:
        _RECENT_FINGERPRINT_ACTIVE[key] = _RecentActiveIds(catalog, active_ids)
        _RECENT_FINGERPRINT_ACTIVE.move_to_end(key)
        while len(_RECENT_FINGERPRINT_ACTIVE) > _FINGERPRINT_MAX_ENTRIES:
            _RECENT_FINGERPRINT_ACTIVE.popitem(last=False)


def _canonicalize(value: Any) -> Any:
    """Return a stable, JSON-serializable representation for fingerprints."""
    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical = [_canonicalize(item) for item in value]
        return sorted(canonical, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _catalog_guard(catalog: list[dict[str, Any]]) -> tuple[tuple[Any, ...], ...]:
    """Detect changes to the validated, routing-relevant roster fields."""
    return tuple(
        (
            id(agent),
            len(agent),
            agent.get("slug"),
            agent.get("agent_slug"),
            agent.get("version"),
            agent.get("hash"),
            agent.get("name"),
            agent.get("description"),
            agent.get("division"),
            tuple(agent.get("categories") or ()),
            tuple(agent.get("capabilities") or ()),
            tuple(agent.get("tool_affinity") or ()),
        )
        for agent in catalog
    )


def _container_guard(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return (id(value), len(value))
    return (type(value).__name__, repr(value))


def _policy_mutation_guard(policy: dict[str, Any]) -> tuple[Any, ...]:
    """Detect structural in-place changes without walking every route leaf.

    File reloads replace the policy object. This guard additionally catches
    mapping/list replacement and append/remove mutations for callers that keep
    an in-memory policy, while preserving the sub-2 ms cache-hit contract.
    """
    actions = policy.get("actions")
    if isinstance(actions, dict):
        action_guard = (
            id(actions),
            len(actions),
            tuple(
                (
                    name,
                    id(action),
                    len(action),
                    _container_guard(action.get("triggers")),
                    _container_guard(action.get("always_include")),
                    _container_guard(action.get("conditional")),
                )
                if isinstance(action, dict)
                else (name, type(action).__name__, repr(action))
                for name, action in actions.items()
            ),
        )
    else:
        action_guard = (type(actions).__name__, repr(actions))

    divisions = policy.get("division_anchors")
    if isinstance(divisions, dict):
        division_guard = (
            id(divisions),
            len(divisions),
            tuple(
                (
                    name,
                    id(division),
                    len(division),
                    division.get("anchor"),
                    _container_guard(division.get("keywords")),
                    _container_guard(division.get("conditional")),
                )
                if isinstance(division, dict)
                else (name, type(division).__name__, repr(division))
                for name, division in divisions.items()
            ),
        )
    else:
        division_guard = (type(divisions).__name__, repr(divisions))

    availability = policy.get("specialist_availability")
    if isinstance(availability, dict):
        gated = availability.get("roster_gated")
        if isinstance(gated, dict):
            gated_guard = (
                id(gated),
                len(gated),
                gated.get("reason"),
                _container_guard(gated.get("slugs")),
            )
        else:
            gated_guard = (type(gated).__name__, repr(gated))
        availability_guard = (
            id(availability),
            len(availability),
            availability.get("schema_version"),
            _container_guard(availability.get("enabled")),
            gated_guard,
        )
    else:
        availability_guard = (type(availability).__name__, repr(availability))

    return (id(policy), len(policy), action_guard, division_guard, availability_guard)


def _mutation_snapshot(value: Any, fallback: Callable[[], Any]) -> _MutationSnapshot:
    """Copy bounded JSON-like state so unchanged checks run mostly in C.

    Production catalogs and policies are validated JSON-like containers, for
    which equality against a detached copy is both complete and substantially
    faster than rebuilding Python guard tuples on every cache hit. Direct API
    callers may still provide objects that cannot be copied; retain the former
    structural guard as a compatibility fallback for those inputs.
    """
    try:
        return _MutationSnapshot(deepcopy(value), complete=True)
    except Exception:
        return _MutationSnapshot(fallback(), complete=False)


def _snapshot_matches(
    value: Any,
    snapshot: _MutationSnapshot,
    fallback: Callable[[], Any],
) -> bool:
    """Return whether mutable state still matches a detached snapshot."""
    try:
        candidate = value if snapshot.complete else fallback()
        return bool(candidate == snapshot.value)
    except Exception:
        # Equality on an exotic caller-owned object must never make routing
        # reuse stale state. Recompute conservatively instead.
        return False


def routing_fingerprint(
    catalog: list[dict[str, Any]],
    config: Any,
    policy: dict[str, Any],
) -> str:
    """Fingerprint every input that can change a routing decision.

    Catalog order is normalized because selection is based on agent identity and
    metadata, not the order in which a store happened to return the roster.
    """
    memo_key = (id(catalog), id(config), id(policy))
    equivalent_key = (id(config), id(policy))
    with _CACHE_LOCK:
        cached = _FINGERPRINT_CACHE.get(memo_key)
    if (
        cached is not None
        and cached.catalog is catalog
        and cached.config is config
        and cached.policy is policy
        and _snapshot_matches(
            catalog,
            cached.catalog_snapshot,
            lambda: _catalog_guard(catalog),
        )
        and _snapshot_matches(
            policy,
            cached.policy_snapshot,
            lambda: _policy_mutation_guard(policy),
        )
    ):
        with _CACHE_LOCK:
            # An eviction or concurrent refresh does not invalidate the local
            # immutable entry, but only mutate LRU order when it is still live.
            if _FINGERPRINT_CACHE.get(memo_key) is cached:
                _FINGERPRINT_CACHE.move_to_end(memo_key)
        _remember_fingerprint_active(catalog, cached.active_ids)
        return cached.fingerprint

    # Eligibility filtering intentionally returns a fresh list so callers
    # cannot mutate the source roster through the projection. The rows remain
    # the same immutable agent mappings, however. Reuse the fingerprint for
    # that equivalent projection after a complete detached-value comparison;
    # this preserves in-place mutation invalidation without canonicalizing and
    # deep-copying a thousand-row roster on every cache hit.
    with _CACHE_LOCK:
        equivalent = _EQUIVALENT_FINGERPRINT_CACHE.get(equivalent_key)
    if (
        equivalent is not None
        and equivalent.config is config
        and equivalent.policy is policy
        and _snapshot_matches(
            catalog,
            equivalent.catalog_snapshot,
            lambda: _catalog_guard(catalog),
        )
        and _snapshot_matches(
            policy,
            equivalent.policy_snapshot,
            lambda: _policy_mutation_guard(policy),
        )
    ):
        with _CACHE_LOCK:
            if _EQUIVALENT_FINGERPRINT_CACHE.get(equivalent_key) is equivalent:
                _EQUIVALENT_FINGERPRINT_CACHE.move_to_end(equivalent_key)
        _remember_fingerprint_active(catalog, equivalent.active_ids)
        return equivalent.fingerprint

    roster = [_canonicalize(agent) for agent in catalog]
    roster.sort(key=lambda agent: json.dumps(agent, sort_keys=True, default=str))
    payload = {
        "catalog": roster,
        "config": _canonicalize(config),
        "policy": _canonicalize(policy),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    entry = _FingerprintEntry(
        catalog=catalog,
        config=config,
        policy=policy,
        catalog_snapshot=_mutation_snapshot(catalog, lambda: _catalog_guard(catalog)),
        policy_snapshot=_mutation_snapshot(policy, lambda: _policy_mutation_guard(policy)),
        fingerprint=fingerprint,
        active_ids=_active_ids(catalog),
    )
    with _CACHE_LOCK:
        _FINGERPRINT_CACHE[memo_key] = entry
        _FINGERPRINT_CACHE.move_to_end(memo_key)
        _EQUIVALENT_FINGERPRINT_CACHE[equivalent_key] = entry
        _EQUIVALENT_FINGERPRINT_CACHE.move_to_end(equivalent_key)
        while len(_FINGERPRINT_CACHE) > _FINGERPRINT_MAX_ENTRIES:
            _FINGERPRINT_CACHE.popitem(last=False)
        while len(_EQUIVALENT_FINGERPRINT_CACHE) > _FINGERPRINT_MAX_ENTRIES:
            _EQUIVALENT_FINGERPRINT_CACHE.popitem(last=False)
    _remember_fingerprint_active(catalog, entry.active_ids)
    return fingerprint


def cache_key(
    query: str,
    *,
    context_fingerprint: str = "",
    catalog: list[dict[str, Any]] | None = None,
    config: Any = None,
    policy: dict[str, Any] | None = None,
) -> str:
    """Return a content key scoped to the active routing context.

    The optional object arguments keep the helper convenient for callers that
    have not already calculated a shared context fingerprint. Query-only calls
    remain supported for low-level cache tests and compatibility.
    """
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    if not context_fingerprint and any(value is not None for value in (catalog, config, policy)):
        context_fingerprint = routing_fingerprint(catalog or [], config, policy or {})
    material = f"{normalized}\0{context_fingerprint}" if context_fingerprint else normalized
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def catalog_active_ids(
    catalog: list[dict[str, Any]],
    *,
    context_fingerprint: str,
) -> frozenset[str]:
    """Return active identities cached against a mutation-aware fingerprint."""
    with _CACHE_LOCK:
        recent = _RECENT_FINGERPRINT_ACTIVE.pop(id(catalog), None)
    if recent is not None and recent.catalog is catalog:
        return recent.active_ids

    key = context_fingerprint
    with _CACHE_LOCK:
        cached = _ACTIVE_IDS_CACHE.get(key)
        if cached is not None and _snapshot_matches(
            catalog,
            cached.catalog_snapshot,
            lambda: _catalog_guard(catalog),
        ):
            _ACTIVE_IDS_CACHE.move_to_end(key)
            return cached.active_ids
    active = _active_ids(catalog)
    entry = _ActiveIdsEntry(
        _mutation_snapshot(catalog, lambda: _catalog_guard(catalog)),
        active,
    )
    with _CACHE_LOCK:
        _ACTIVE_IDS_CACHE[key] = entry
        _ACTIVE_IDS_CACHE.move_to_end(key)
        while len(_ACTIVE_IDS_CACHE) > _FINGERPRINT_MAX_ENTRIES:
            _ACTIVE_IDS_CACHE.popitem(last=False)
    return active


def _clone_cache_value(value: Any) -> Any:
    """Detach JSON-like routing evidence without deepcopy bookkeeping.

    Routing results are bounded JSON-compatible containers. A specialized
    clone avoids the memo table and dynamic dispatch cost that deepcopy pays
    for every scalar on the cache-hit path, while retaining a defensive
    fallback for compatibility callers that cache an opaque value.
    """

    value_type = type(value)
    if value is None or value_type in {str, int, float, bool, bytes}:
        return value
    if value_type is list:
        return [_clone_cache_value(item) for item in value]
    if value_type is tuple:
        return tuple(_clone_cache_value(item) for item in value)
    if value_type is dict:
        return {key: _clone_cache_value(item) for key, item in value.items()}
    if value_type is set:
        return {_clone_cache_value(item) for item in value}
    if value_type is frozenset:
        return frozenset(_clone_cache_value(item) for item in value)
    return deepcopy(value)


def cache_get(key: str, ttl: float = _CACHE_TTL_SECONDS) -> dict[str, Any] | None:
    with _CACHE_LOCK:
        if key not in _ROUTING_CACHE:
            return None
        entry = _ROUTING_CACHE[key]
        age = time.monotonic() - entry["_ts"]
        if age > ttl:
            del _ROUTING_CACHE[key]
            return None
        _ROUTING_CACHE.move_to_end(key)
        result = _clone_cache_value({k: v for k, v in entry.items() if not k.startswith("_")})
    result["cache_hit"] = True
    return result


def cache_put(key: str, value: dict[str, Any], max_entries: int = _CACHE_MAX_ENTRIES) -> None:
    with _CACHE_LOCK:
        _ROUTING_CACHE[key] = {**_clone_cache_value(value), "_ts": time.monotonic()}
        _ROUTING_CACHE.move_to_end(key)
        while len(_ROUTING_CACHE) > max(0, max_entries):
            _ROUTING_CACHE.popitem(last=False)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _ROUTING_CACHE.clear()
        _FINGERPRINT_CACHE.clear()
        _EQUIVALENT_FINGERPRINT_CACHE.clear()
        _RECENT_FINGERPRINT_ACTIVE.clear()
        _ACTIVE_IDS_CACHE.clear()
