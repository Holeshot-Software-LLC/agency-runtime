"""Content-hash cache for routing results."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

_CACHE_TTL_SECONDS = float(600)
_CACHE_MAX_ENTRIES = int(128)

_ROUTING_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_ACTIVE_IDS_CACHE: OrderedDict[
    tuple[int, str], tuple[list[dict[str, Any]], frozenset[str]]
] = OrderedDict()
_FINGERPRINT_CACHE: OrderedDict[
    tuple[int, int, int],
    tuple[
        list[dict[str, Any]],
        Any,
        dict[str, Any],
        tuple[tuple[Any, ...], ...],
        str,
    ],
] = OrderedDict()
_CACHE_LOCK = threading.RLock()
_FINGERPRINT_MAX_ENTRIES = 32


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
            agent.get("name"),
            agent.get("description"),
            agent.get("division"),
            tuple(agent.get("categories") or ()),
            tuple(agent.get("capabilities") or ()),
            tuple(agent.get("tool_affinity") or ()),
        )
        for agent in catalog
    )


def routing_fingerprint(
    catalog: list[dict[str, Any]],
    config: Any,
    policy: dict[str, Any],
) -> str:
    """Fingerprint every input that can change a routing decision.

    Catalog order is normalized because selection is based on agent identity and
    metadata, not the order in which a store happened to return the roster.
    """
    guard = _catalog_guard(catalog)
    memo_key = (id(catalog), id(config), id(policy))
    with _CACHE_LOCK:
        cached = _FINGERPRINT_CACHE.get(memo_key)
        if (
            cached is not None
            and cached[0] is catalog
            and cached[1] is config
            and cached[2] is policy
            and cached[3] == guard
        ):
            _FINGERPRINT_CACHE.move_to_end(memo_key)
            return cached[4]

    roster = [_canonicalize(agent) for agent in catalog]
    roster.sort(key=lambda agent: json.dumps(agent, sort_keys=True, default=str))
    payload = {
        "catalog": roster,
        "config": _canonicalize(config),
        "policy": _canonicalize(policy),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    fingerprint = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    with _CACHE_LOCK:
        _FINGERPRINT_CACHE[memo_key] = (catalog, config, policy, guard, fingerprint)
        _FINGERPRINT_CACHE.move_to_end(memo_key)
        while len(_FINGERPRINT_CACHE) > _FINGERPRINT_MAX_ENTRIES:
            _FINGERPRINT_CACHE.popitem(last=False)
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
    if not context_fingerprint and any(
        value is not None for value in (catalog, config, policy)
    ):
        context_fingerprint = routing_fingerprint(catalog or [], config, policy or {})
    material = f"{normalized}\0{context_fingerprint}" if context_fingerprint else normalized
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def catalog_active_ids(
    catalog: list[dict[str, Any]],
    *,
    context_fingerprint: str,
) -> frozenset[str]:
    """Return active identities cached against a mutation-aware fingerprint."""
    key = (id(catalog), context_fingerprint)
    with _CACHE_LOCK:
        cached = _ACTIVE_IDS_CACHE.get(key)
        if cached is not None and cached[0] is catalog:
            _ACTIVE_IDS_CACHE.move_to_end(key)
            return cached[1]
    active = frozenset(
        str(agent.get("slug") or agent.get("agent_slug") or "")
        for agent in catalog
        if agent.get("slug") or agent.get("agent_slug")
    )
    with _CACHE_LOCK:
        _ACTIVE_IDS_CACHE[key] = (catalog, active)
        _ACTIVE_IDS_CACHE.move_to_end(key)
        while len(_ACTIVE_IDS_CACHE) > _FINGERPRINT_MAX_ENTRIES:
            _ACTIVE_IDS_CACHE.popitem(last=False)
    return active


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
        result = deepcopy({k: v for k, v in entry.items() if not k.startswith("_")})
    result["cache_hit"] = True
    return result


def cache_put(key: str, value: dict[str, Any], max_entries: int = _CACHE_MAX_ENTRIES) -> None:
    with _CACHE_LOCK:
        _ROUTING_CACHE[key] = {**deepcopy(value), "_ts": time.monotonic()}
        _ROUTING_CACHE.move_to_end(key)
        while len(_ROUTING_CACHE) > max(0, max_entries):
            _ROUTING_CACHE.popitem(last=False)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _ROUTING_CACHE.clear()
        _FINGERPRINT_CACHE.clear()
        _ACTIVE_IDS_CACHE.clear()
