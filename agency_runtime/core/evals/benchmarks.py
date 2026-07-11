"""Small deterministic performance probes for the routing hot path."""

from __future__ import annotations

import math
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.pipeline import route
from agency_runtime.core.selector.stickiness import clear_session_routing


def generated_catalog(size: int) -> list[dict[str, Any]]:
    """Build a varied synthetic roster without copying one trivial row."""
    if size < 0:
        raise ValueError("size must be non-negative")
    domains = (
        ("security", "oauth threat modeling", "sast"),
        ("performance", "latency profiling", "benchmarks"),
        ("database", "postgres query optimization", "sql"),
        ("documentation", "technical writing runbooks", "markdown"),
        ("frontend", "dashboard component design", "browser"),
        ("operations", "kubernetes deployment reliability", "terraform"),
        ("data", "etl warehouse pipelines", "dbt"),
        ("planning", "workflow dependency mapping", "issues"),
    )
    catalog: list[dict[str, Any]] = []
    for index in range(size):
        domain, capability, tool = domains[index % len(domains)]
        catalog.append({
            "slug": f"{domain}-specialist-{index:04d}",
            "name": f"{domain.title()} Specialist {index}",
            "division": domain,
            "description": f"Handles {capability} for production systems cohort {index % 17}.",
            "categories": [domain, f"cohort-{index % 17}"],
            "capabilities": [capability, f"analysis tier {index % 5}"],
            "tool_affinity": [tool, "terminal"],
        })
    return catalog


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def run_candidate_microbenchmark(
    *,
    roster_size: int = 1000,
    iterations: int = 32,
    workers: int = 8,
) -> dict[str, Any]:
    """Measure narrowing latency and concurrent determinism at realistic size."""
    if iterations < 1:
        raise ValueError("iterations must be at least one")
    if workers < 1:
        raise ValueError("workers must be at least one")

    catalog = generated_catalog(roster_size)
    query = "profile production API latency with benchmarks"
    pre_narrow(query, catalog, limit=20)  # warm caches and the interpreter

    latencies_ms: list[float] = []
    expected: tuple[str, ...] | None = None
    consistent = True
    for _ in range(iterations):
        started = time.perf_counter()
        candidates, _scores = pre_narrow(query, catalog, limit=20)
        latencies_ms.append((time.perf_counter() - started) * 1000)
        slugs = tuple(str(candidate.get("slug", "")) for candidate in candidates)
        expected = expected or slugs
        consistent = consistent and slugs == expected

    concurrent_calls = max(workers * 2, iterations)
    active_calls = 0
    max_active_calls = 0
    active_lock = threading.Lock()

    def narrow_once(_index: int) -> tuple[str, ...]:
        nonlocal active_calls, max_active_calls
        with active_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        try:
            candidates, _scores = pre_narrow(query, catalog, limit=20)
            return tuple(str(candidate.get("slug", "")) for candidate in candidates)
        finally:
            with active_lock:
                active_calls -= 1

    concurrent_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        concurrent_results = list(executor.map(narrow_once, range(concurrent_calls)))
    concurrent_ms = (time.perf_counter() - concurrent_started) * 1000
    consistent = consistent and all(result == expected for result in concurrent_results)

    # Measure the complete pipeline cache path, including context fingerprint
    # validation and per-request trace generation. The provider chain is
    # explicitly offline so this remains deterministic and network-free.
    offline = AgencyConfig(
        providers=(),
        judge=JudgeConfig(model="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    clear_cache()
    clear_session_routing()
    warm = route("benchmark-warm", query, catalog, config=offline)
    route("benchmark-cache-warm", query, catalog, config=offline)
    cache_latencies_ms: list[float] = []
    cached_results: list[dict[str, Any]] = []
    for index in range(max(iterations, 128)):
        started = time.perf_counter()
        cached = route(f"benchmark-cache-{index}", query, catalog, config=offline)
        cache_latencies_ms.append((time.perf_counter() - started) * 1000)
        cached_results.append(cached)
    expected_ids = tuple(warm.get("selected_ids", []))
    cache_consistent = all(
        result.get("cache_hit") is True
        and tuple(result.get("selected_ids", [])) == expected_ids
        for result in cached_results
    )
    trace_ids = {str(result.get("trace_id") or "") for result in cached_results}
    unique_traces = len(trace_ids) == len(cached_results) and "" not in trace_ids

    return {
        "roster_size": roster_size,
        "iterations": iterations,
        "workers": workers,
        "p50_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(_percentile(latencies_ms, 0.95), 3),
        "max_ms": round(max(latencies_ms), 3),
        "concurrent_calls": concurrent_calls,
        "concurrent_overlap": max_active_calls,
        "concurrent_total_ms": round(concurrent_ms, 3),
        "concurrent_calls_per_second": round(
            concurrent_calls / max(concurrent_ms / 1000, 1e-9), 2
        ),
        "deterministic": consistent,
        "cache_hit_p50_ms": round(statistics.median(cache_latencies_ms), 3),
        "cache_hit_p95_ms": round(_percentile(cache_latencies_ms, 0.95), 3),
        "cache_hit_max_ms": round(max(cache_latencies_ms), 3),
        "cache_hit_deterministic": cache_consistent and unique_traces,
    }


__all__ = ["generated_catalog", "run_candidate_microbenchmark"]
