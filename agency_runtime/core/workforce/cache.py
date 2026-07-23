"""Bounded process-local caches for version-bound workforce routing stages.

Only opaque SHA-256 identities and validated immutable results are retained.
Request text, provider secrets, and prompts are never stored in cache keys.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

WORKFORCE_CACHE_IDENTITY_VERSION = "1"
WORKFORCE_CACHE_TTL_SECONDS = 600.0
WORKFORCE_CACHE_MAX_ENTRIES_PER_STAGE = 128
_ALLOWED_STAGES = frozenset({"candidate", "critic", "plan", "recruiter"})
_MAX_IDENTITY_BYTES = 512 * 1024


@dataclass(frozen=True, slots=True)
class WorkforceCacheIdentity:
    """One stage-scoped opaque identity suitable for logs and cache lookup."""

    stage: str
    digest: str
    version: str = WORKFORCE_CACHE_IDENTITY_VERSION

    @property
    def key(self) -> str:
        return f"workforce:{self.version}:{self.stage}:{self.digest}"


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    inserted_at: float
    value: Any


_CACHE_LOCK = threading.RLock()
_STAGE_CACHES: dict[str, OrderedDict[str, _CacheEntry]] = {
    stage: OrderedDict() for stage in _ALLOWED_STAGES
}


def workforce_cache_identity(stage: str, components: dict[str, Any]) -> WorkforceCacheIdentity:
    """Hash a bounded canonical stage identity without retaining its source data."""

    normalized_stage = str(stage or "").strip().casefold()
    if normalized_stage not in _ALLOWED_STAGES:
        raise ValueError("workforce cache stage is unsupported")
    if not isinstance(components, dict):
        raise TypeError("workforce cache identity components must be a mapping")
    try:
        payload = json.dumps(
            {
                "identity_version": WORKFORCE_CACHE_IDENTITY_VERSION,
                "stage": normalized_stage,
                "components": components,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValueError("workforce cache identity is not canonical JSON") from exc
    if len(payload) > _MAX_IDENTITY_BYTES:
        raise ValueError("workforce cache identity exceeds its size bound")
    return WorkforceCacheIdentity(normalized_stage, hashlib.sha256(payload).hexdigest())


def workforce_cache_get(identity: WorkforceCacheIdentity) -> Any | None:
    """Return a detached unexpired value for one exact identity."""

    if not isinstance(identity, WorkforceCacheIdentity):
        raise TypeError("workforce cache lookup requires a cache identity")
    now = time.monotonic()
    with _CACHE_LOCK:
        cache = _STAGE_CACHES[identity.stage]
        entry = cache.get(identity.key)
        if entry is None:
            return None
        if now - entry.inserted_at > WORKFORCE_CACHE_TTL_SECONDS:
            del cache[identity.key]
            return None
        cache.move_to_end(identity.key)
        return deepcopy(entry.value)


def workforce_cache_put(identity: WorkforceCacheIdentity, value: Any) -> None:
    """Store one detached validated result in the bounded stage LRU."""

    if not isinstance(identity, WorkforceCacheIdentity):
        raise TypeError("workforce cache insertion requires a cache identity")
    detached = deepcopy(value)
    with _CACHE_LOCK:
        cache = _STAGE_CACHES[identity.stage]
        cache[identity.key] = _CacheEntry(time.monotonic(), detached)
        cache.move_to_end(identity.key)
        while len(cache) > WORKFORCE_CACHE_MAX_ENTRIES_PER_STAGE:
            cache.popitem(last=False)


def clear_workforce_caches() -> None:
    """Clear process-local stage caches for tests and explicit maintenance."""

    with _CACHE_LOCK:
        for cache in _STAGE_CACHES.values():
            cache.clear()


def workforce_cache_counts() -> dict[str, int]:
    """Return content-free bounded diagnostics for the local process."""

    with _CACHE_LOCK:
        return {stage: len(cache) for stage, cache in sorted(_STAGE_CACHES.items())}


__all__ = [
    "WORKFORCE_CACHE_IDENTITY_VERSION",
    "WORKFORCE_CACHE_MAX_ENTRIES_PER_STAGE",
    "WORKFORCE_CACHE_TTL_SECONDS",
    "WorkforceCacheIdentity",
    "clear_workforce_caches",
    "workforce_cache_counts",
    "workforce_cache_get",
    "workforce_cache_identity",
    "workforce_cache_put",
]
