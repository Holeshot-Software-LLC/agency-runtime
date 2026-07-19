"""Maximum-roster correctness and performance regressions."""

from __future__ import annotations

import time
from collections.abc import Iterator
from copy import deepcopy

import pytest

from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.selector import candidate_narrow


def _catalog(size: int) -> list[dict[str, object]]:
    return [
        {
            "slug": f"agent-{index:05d}",
            "name": f"Agent {index:05d}",
            "description": "Production capacity specialist",
            "division": "engineering",
            "categories": ["performance"],
            "capabilities": ["capacity planning", f"cohort {index % 17}"],
            "tool_affinity": ["profiler"],
        }
        for index in range(size)
    ]


@pytest.fixture(autouse=True)
def _isolated_compiled_selector_cache() -> Iterator[None]:
    candidate_narrow._clear_compiled_score_caches()
    yield
    candidate_narrow._clear_compiled_score_caches()


def test_maximum_roster_reuses_compiled_catalog_without_lru_churn() -> None:
    catalog = _catalog(MAX_ACTIVE_ROSTER_SIZE)

    first, first_scores = candidate_narrow.pre_narrow(
        "production capacity planning",
        catalog,
        limit=20,
    )
    warm_info = candidate_narrow._compiled_agent_score_inputs.cache_info()
    second, second_scores = candidate_narrow.pre_narrow(
        "production capacity planning",
        catalog,
        limit=20,
    )

    assert warm_info.misses == MAX_ACTIVE_ROSTER_SIZE
    assert warm_info.currsize == MAX_ACTIVE_ROSTER_SIZE
    assert candidate_narrow._compiled_agent_score_inputs.cache_info() == warm_info
    assert [agent["slug"] for agent in second] == [agent["slug"] for agent in first]
    assert second_scores == first_scores


def test_compiled_catalog_is_content_keyed_mutation_safe_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _catalog(3)
    equivalent = deepcopy(first)
    candidate_narrow.pre_narrow("capacity planning", first, limit=1)
    warm_info = candidate_narrow._compiled_agent_score_inputs.cache_info()

    candidate_narrow.pre_narrow("capacity planning", equivalent, limit=1)
    assert candidate_narrow._compiled_agent_score_inputs.cache_info() == warm_info

    equivalent[0]["capabilities"] = ["technical writing"]
    selected, _scores = candidate_narrow.pre_narrow("technical writing", equivalent, limit=1)
    mutated_info = candidate_narrow._compiled_agent_score_inputs.cache_info()
    assert selected[0]["slug"] == "agent-00000"
    assert mutated_info.misses == warm_info.misses + 1
    assert mutated_info.hits == warm_info.hits + 2

    monkeypatch.setattr(candidate_narrow, "_COMPILED_CATALOG_CACHE_MAX_ENTRIES", 1)
    candidate_narrow.pre_narrow("capacity planning", _catalog(2), limit=1)
    assert len(candidate_narrow._COMPILED_CATALOG_CACHE) == 1


def test_narrowing_rejects_catalog_above_supported_roster_bound() -> None:
    with pytest.raises(ValueError, match="cannot contain more than 10000"):
        candidate_narrow.pre_narrow(
            "capacity planning",
            [{}] * (MAX_ACTIVE_ROSTER_SIZE + 1),
        )


def test_batched_narrowing_preserves_empty_and_roster_bounds() -> None:
    catalog = _catalog(1)

    assert candidate_narrow.pre_narrow("capacity", [], limit=1) == ([], [])
    assert candidate_narrow.pre_narrow("capacity", catalog, limit=0) == ([], [])
    assert candidate_narrow.pre_narrow_many(["one", "two"], [], limit=1) == [
        ([], []),
        ([], []),
    ]
    assert candidate_narrow.pre_narrow_many(["one"], catalog, limit=0) == [([], [])]
    with pytest.raises(ValueError, match="cannot contain more than 10000"):
        candidate_narrow.pre_narrow_many(
            ["capacity planning"],
            [{}] * (MAX_ACTIVE_ROSTER_SIZE + 1),
        )


@pytest.mark.performance
def test_maximum_roster_hot_path_is_bounded() -> None:
    catalog = _catalog(MAX_ACTIVE_ROSTER_SIZE)
    candidate_narrow.pre_narrow("production capacity planning", catalog, limit=20)

    latencies_ms = []
    for _ in range(7):
        started = time.perf_counter()
        candidate_narrow.pre_narrow("production capacity planning", catalog, limit=20)
        latencies_ms.append((time.perf_counter() - started) * 1000)

    assert sorted(latencies_ms)[len(latencies_ms) // 2] < 250.0
