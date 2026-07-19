"""Mutation-safe selector cache hot-path regressions."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy

import pytest

from agency_runtime.core.selector import cache, candidate_narrow, compatibility


@pytest.fixture(autouse=True)
def _isolated_caches():
    cache.clear_cache()
    candidate_narrow._clear_compiled_score_caches()
    compatibility.clear_eligibility_cache()
    yield
    cache.clear_cache()
    candidate_narrow._clear_compiled_score_caches()
    compatibility.clear_eligibility_cache()


def _catalog() -> list[dict[str, object]]:
    return [
        {
            "slug": "performance-benchmarker",
            "description": "Profiles API latency",
            "capabilities": ["performance profiling"],
            "supported_hosts": ["codex"],
            "supported_platforms": ["windows"],
            "required_tools": ["profiler"],
        }
    ]


class _EvictOnSecondGet(OrderedDict):
    """Model an LRU entry being replaced between validation and touch."""

    def __init__(self, source):
        super().__init__(source)
        self.calls = 0

    def get(self, key, default=None):
        self.calls += 1
        value = super().get(key, default)
        if self.calls == 2:
            super().pop(key, None)
            return default
        return value


def test_fingerprint_reuses_fresh_projection_and_detects_row_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _catalog()
    config = object()
    policy: dict[str, object] = {}
    first = cache.routing_fingerprint(list(source), config, policy)
    real_canonicalize = cache._canonicalize

    def unexpected_canonicalize(_value):
        raise AssertionError("equivalent projection should reuse its fingerprint")

    monkeypatch.setattr(cache, "_canonicalize", unexpected_canonicalize)
    assert cache.routing_fingerprint(list(source), config, policy) == first

    monkeypatch.setattr(cache, "_canonicalize", real_canonicalize)
    source[0]["description"] = "Writes documentation"
    assert cache.routing_fingerprint(list(source), config, policy) != first


def test_compiled_identity_fast_path_remains_content_and_mutation_safe() -> None:
    source = _catalog()
    candidate_narrow.pre_narrow("performance profiling", source, limit=1)
    cached = candidate_narrow._IDENTITY_CATALOG_CACHE[id(source)]

    candidate_narrow.pre_narrow("performance profiling", source, limit=1)
    assert candidate_narrow._IDENTITY_CATALOG_CACHE[id(source)] is cached

    source[0]["capabilities"] = ["technical writing"]
    selected, scores = candidate_narrow.pre_narrow("technical writing", source, limit=1)
    assert selected[0]["slug"] == "performance-benchmarker"
    assert scores[0] > 0
    assert candidate_narrow._IDENTITY_CATALOG_CACHE[id(source)] is not cached


def test_eligibility_cache_reuses_equivalent_projection_and_invalidates() -> None:
    source = _catalog()
    kwargs = {
        "host": "codex",
        "platform": "windows",
        "available_tools": {"profiler"},
    }
    first_projection = list(source)
    second_projection = list(source)
    first = compatibility.filter_eligible_catalog(first_projection, **kwargs)
    second = compatibility.filter_eligible_catalog(second_projection, **kwargs)
    assert second == first
    assert second.eligible[0] is second_projection[0]
    equivalent = deepcopy(source)
    rebound = compatibility.filter_eligible_catalog(equivalent, **kwargs)
    assert rebound == first
    assert rebound.eligible[0] is equivalent[0]
    assert id(equivalent) in {key[0] for key in compatibility._ELIGIBILITY_IDENTITY_CACHE}

    source[0]["required_tools"] = ["missing"]
    rejected = compatibility.filter_eligible_catalog(list(source), **kwargs)
    assert rejected.eligible == ()
    assert rejected.rejected == (
        {
            "slug": "performance-benchmarker",
            "reason": "unknown_tool_requirement:missing",
        },
    )


def test_equivalent_rebinding_preserves_row_eligibility_with_duplicate_slugs() -> None:
    source = [
        {"slug": "duplicate"},
        {"slug": "duplicate", "audit_status": "quarantined"},
    ]
    first = compatibility.filter_eligible_catalog(source)
    equivalent = deepcopy(source)

    rebound = compatibility.filter_eligible_catalog(equivalent)

    assert first.eligible == (source[0],)
    assert rebound.eligible == (equivalent[0],)
    assert rebound.eligible[0] is equivalent[0]
    assert rebound.rejected == ({"slug": "duplicate", "reason": "audit_status:quarantined"},)


def test_equivalent_content_catalog_still_reuses_compiled_index() -> None:
    first = _catalog()
    equivalent = deepcopy(first)
    candidate_narrow.pre_narrow("performance profiling", first, limit=1)
    warm = candidate_narrow._compiled_agent_score_inputs.cache_info()

    candidate_narrow.pre_narrow("performance profiling", equivalent, limit=1)

    assert candidate_narrow._compiled_agent_score_inputs.cache_info() == warm


def test_opaque_irrelevant_metadata_skips_identity_caches_without_failing() -> None:
    class Opaque:
        def __deepcopy__(self, _memo):
            raise TypeError("opaque")

    source = _catalog()
    source[0]["opaque"] = Opaque()

    selected, scores = candidate_narrow.pre_narrow(
        "performance profiling",
        source,
        limit=1,
    )
    eligible = compatibility.filter_eligible_catalog(
        source,
        host="codex",
        platform="windows",
        available_tools={"profiler"},
    )

    assert selected[0]["slug"] == "performance-benchmarker"
    assert scores[0] > 0
    assert eligible.eligible == tuple(source)
    assert id(source) not in candidate_narrow._IDENTITY_CATALOG_CACHE
    assert not compatibility._ELIGIBILITY_CACHE
    assert not compatibility._ELIGIBILITY_IDENTITY_CACHE


def test_selector_projection_caches_remain_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compatibility, "_ELIGIBILITY_CACHE_MAX_ENTRIES", 1)
    first = _catalog()
    second = deepcopy(first)
    second[0]["slug"] = "second"
    kwargs = {"host": "codex", "platform": "windows"}

    compatibility.filter_eligible_catalog(first, **kwargs)
    compatibility.filter_eligible_catalog(second, **kwargs)
    assert len(compatibility._ELIGIBILITY_CACHE) == 1
    assert len(compatibility._ELIGIBILITY_IDENTITY_CACHE) == 1

    equivalent = deepcopy(second)
    compatibility.filter_eligible_catalog(equivalent, **kwargs)
    assert len(compatibility._ELIGIBILITY_IDENTITY_CACHE) == 1

    monkeypatch.setattr(cache, "_FINGERPRINT_MAX_ENTRIES", 1)
    cache._RECENT_FINGERPRINT_ACTIVE.clear()
    cache.catalog_active_ids(first, context_fingerprint="first")
    cache.catalog_active_ids(second, context_fingerprint="second")
    assert list(cache._ACTIVE_IDS_CACHE) == ["second"]


def test_cache_lru_races_return_validated_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _catalog()
    config = object()
    policy: dict[str, object] = {}
    first_projection = list(source)
    fingerprint = cache.routing_fingerprint(first_projection, config, policy)
    monkeypatch.setattr(
        cache,
        "_EQUIVALENT_FINGERPRINT_CACHE",
        _EvictOnSecondGet(cache._EQUIVALENT_FINGERPRINT_CACHE),
    )
    assert cache.routing_fingerprint(list(source), config, policy) == fingerprint

    candidate_narrow.pre_narrow("performance profiling", source, limit=1)
    monkeypatch.setattr(
        candidate_narrow,
        "_IDENTITY_CATALOG_CACHE",
        _EvictOnSecondGet(candidate_narrow._IDENTITY_CATALOG_CACHE),
    )
    selected, _scores = candidate_narrow.pre_narrow(
        "performance profiling",
        source,
        limit=1,
    )
    assert selected[0]["slug"] == "performance-benchmarker"

    compatibility.filter_eligible_catalog(source, host="codex")
    monkeypatch.setattr(
        compatibility,
        "_ELIGIBILITY_IDENTITY_CACHE",
        _EvictOnSecondGet(compatibility._ELIGIBILITY_IDENTITY_CACHE),
    )
    assert compatibility.filter_eligible_catalog(source, host="codex").rejected == (
        {
            "slug": "performance-benchmarker",
            "reason": "tool_capabilities_unproven:unknown",
        },
    )

    compatibility._ELIGIBILITY_IDENTITY_CACHE.clear()
    monkeypatch.setattr(
        compatibility,
        "_ELIGIBILITY_CACHE",
        _EvictOnSecondGet(compatibility._ELIGIBILITY_CACHE),
    )
    assert compatibility.filter_eligible_catalog(deepcopy(source), host="codex").rejected == (
        {
            "slug": "performance-benchmarker",
            "reason": "tool_capabilities_unproven:unknown",
        },
    )
