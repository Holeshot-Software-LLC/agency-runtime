"""Small deterministic performance probes for the routing hot path."""

from __future__ import annotations

import math
import statistics
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.compatibility import clear_eligibility_cache
from agency_runtime.core.selector.pipeline import route
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent

_BENCHMARK_BATCHES = 5
_WARMUP_CALLS = 4
_MIN_CACHE_SAMPLES = 128
_CONCURRENCY_PROBE_TIMEOUT_SECONDS = 5.0


@dataclass
class _ConcurrencyProbe:
    """Synchronize workers from inside candidate narrowing's scoring path."""

    workers: int
    timeout_seconds: float
    barrier: threading.Barrier = field(init=False)
    lock: threading.Lock = field(default_factory=threading.Lock)
    slug_accesses: dict[int, int] = field(default_factory=dict)
    arrived_threads: set[int] = field(default_factory=set)
    active: int = 0
    max_overlap: int = 0
    broken: bool = False

    def __post_init__(self) -> None:
        self.barrier = threading.Barrier(self.workers)

    def touch_slug(self) -> None:
        """Wait when a worker reaches scoring after catalog compilation.

        Candidate narrowing reads the first agent's slug once while compiling
        its metadata and again after scoring it. Synchronizing on the second
        read proves that each worker progressed inside the real narrowing
        function; a lock serializing that function breaks the barrier instead
        of yielding a false overlap success.
        """
        thread_id = threading.get_ident()
        with self.lock:
            access_count = self.slug_accesses.get(thread_id, 0) + 1
            self.slug_accesses[thread_id] = access_count
            if access_count != 2:
                return
            self.arrived_threads.add(thread_id)
            self.active += 1
            self.max_overlap = max(self.max_overlap, self.active)
        try:
            self.barrier.wait(timeout=self.timeout_seconds)
        except threading.BrokenBarrierError:
            with self.lock:
                self.broken = True
        finally:
            with self.lock:
                self.active -= 1

    @property
    def synchronized(self) -> bool:
        return (
            not self.broken
            and len(self.arrived_threads) == self.workers
            and self.max_overlap == self.workers
        )


class _ProbeAgent(dict[str, Any]):
    """First catalog row instrumented without changing production narrowing."""

    def __init__(self, source: dict[str, Any], probe: _ConcurrencyProbe) -> None:
        super().__init__(source)
        self._probe = probe

    def get(self, key: str, default: Any = None) -> Any:
        if key == "slug":
            self._probe.touch_slug()
        return super().get(key, default)


def _run_concurrency_probe(
    *,
    query: str,
    catalog: list[dict[str, Any]],
    concurrent_calls: int,
    workers: int,
    narrow: Callable[
        [str, list[dict[str, Any]], int],
        tuple[list[dict[str, Any]], list[float]],
    ] = pre_narrow,
    timeout_seconds: float = _CONCURRENCY_PROBE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if not catalog:
        raise ValueError("concurrency probe requires a non-empty catalog")
    probe = _ConcurrencyProbe(workers=workers, timeout_seconds=timeout_seconds)
    probe_catalog: list[dict[str, Any]] = [
        _ProbeAgent(catalog[0], probe),
        *catalog[1:],
    ]

    def narrow_once(_index: int) -> tuple[str, ...]:
        candidates, _scores = narrow(query, probe_catalog, 20)
        return tuple(str(candidate.get("slug", "")) for candidate in candidates)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(narrow_once, range(concurrent_calls)))
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "results": results,
        "elapsed_ms": elapsed_ms,
        "overlap": probe.max_overlap,
        "threads": len(probe.arrived_threads),
        "synchronized": probe.synchronized,
    }


def generated_catalog(size: int) -> list[dict[str, Any]]:
    """Build a varied synthetic roster without copying one trivial row."""
    if size < 0:
        raise ValueError("size must be non-negative")
    resident_managers = (
        {
            "slug": "agents-orchestrator",
            "name": "Agents Orchestrator",
            "division": "operations",
            "description": "Routes work to the best available specialists.",
            "categories": ["orchestration", "routing"],
            "capabilities": ["agent selection", "delegation planning"],
            "tool_affinity": ["terminal"],
        },
        {
            "slug": "chief-of-staff",
            "name": "Chief of Staff",
            "division": "operations",
            "description": "Coordinates execution across active work.",
            "categories": ["coordination", "planning"],
            "capabilities": ["execution coordination", "work tracking"],
            "tool_affinity": ["terminal"],
        },
    )
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
    manager_count = min(size, len(resident_managers))
    catalog: list[dict[str, Any]] = [dict(agent) for agent in resident_managers[:manager_count]]
    for index in range(size - manager_count):
        domain, capability, tool = domains[index % len(domains)]
        catalog.append(
            {
                "slug": f"{domain}-specialist-{index:04d}",
                "name": f"{domain.title()} Specialist {index}",
                "division": domain,
                "description": f"Handles {capability} for production systems cohort {index % 17}.",
                "categories": [domain, f"cohort-{index % 17}"],
                "capabilities": [capability, f"analysis tier {index % 5}"],
                "tool_affinity": [tool, "terminal"],
            }
        )
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
    """Measure narrowing latency and concurrent determinism at realistic size.

    Timing uses the median p95 from independent batches. A 32-call nearest-rank
    p95 is otherwise determined by its second-slowest sample, so one brief OS
    scheduler interruption can turn a healthy hot path into a false failure.
    Aggregate p95 and observed maxima remain in the report for visibility, and
    sustained regressions still affect a majority of batches and fail the gate.
    """
    if iterations < 1:
        raise ValueError("iterations must be at least one")
    if workers < 1:
        raise ValueError("workers must be at least one")
    if roster_size < 1:
        raise ValueError("roster_size must be at least one")

    catalog = generated_catalog(roster_size)
    # Benchmark runs may share a process with earlier evals. Start from a
    # defined eligibility-cache generation so a prior equivalent catalog does
    # not make the hot-path sample depend on test or command ordering.
    clear_eligibility_cache()
    query = "profile production API latency with benchmarks"
    for _ in range(_WARMUP_CALLS):
        pre_narrow(query, catalog, limit=20)  # warm caches and the interpreter

    latencies_ms: list[float] = []
    latency_batch_p95_ms: list[float] = []
    expected: tuple[str, ...] | None = None
    consistent = True
    for _batch in range(_BENCHMARK_BATCHES):
        batch_latencies_ms: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            candidates, _scores = pre_narrow(query, catalog, limit=20)
            elapsed_ms = (time.perf_counter() - started) * 1000
            batch_latencies_ms.append(elapsed_ms)
            slugs = tuple(str(candidate.get("slug", "")) for candidate in candidates)
            expected = expected or slugs
            consistent = consistent and slugs == expected
        latencies_ms.extend(batch_latencies_ms)
        latency_batch_p95_ms.append(_percentile(batch_latencies_ms, 0.95))

    concurrent_calls = max(workers * 2, iterations)
    concurrency = _run_concurrency_probe(
        query=query,
        catalog=catalog,
        concurrent_calls=concurrent_calls,
        workers=workers,
    )
    concurrent_results = concurrency["results"]
    concurrent_ms = float(concurrency["elapsed_ms"])
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
    cache_query = "continue"
    validated_continuation = classify_turn_intent(
        cache_query,
        TurnState(
            previous_trace_id="benchmark-warm",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=True,
        ),
    )
    cache_warm = route(
        "benchmark-cache-warm",
        cache_query,
        catalog,
        config=offline,
        turn_classification=validated_continuation,
    )
    cache_probe = route(
        "benchmark-cache-probe",
        cache_query,
        catalog,
        config=offline,
        turn_classification=validated_continuation,
    )
    expected_ids = tuple(cache_warm.get("selected_ids", []))
    if not expected_ids:
        raise RuntimeError("cache benchmark warm-up did not produce a cacheable selection")
    if cache_probe.get("cache_hit") is not True:
        raise RuntimeError("cache benchmark warm-up was not reused by the probe request")
    if tuple(cache_probe.get("selected_ids", [])) != expected_ids:
        raise RuntimeError("cache benchmark probe changed the warm-up selection")
    cache_iterations = max(iterations, _MIN_CACHE_SAMPLES)
    cache_latencies_ms: list[float] = []
    cache_latency_batch_p95_ms: list[float] = []
    cached_results: list[dict[str, Any]] = []
    for batch in range(_BENCHMARK_BATCHES):
        batch_latencies_ms = []
        for index in range(cache_iterations):
            started = time.perf_counter()
            cached = route(
                f"benchmark-cache-{batch}-{index}",
                cache_query,
                catalog,
                config=offline,
                turn_classification=validated_continuation,
            )
            batch_latencies_ms.append((time.perf_counter() - started) * 1000)
            cached_results.append(cached)
        cache_latencies_ms.extend(batch_latencies_ms)
        cache_latency_batch_p95_ms.append(_percentile(batch_latencies_ms, 0.95))
    cache_consistent = all(
        result.get("cache_hit") is True and tuple(result.get("selected_ids", [])) == expected_ids
        for result in cached_results
    )
    trace_ids = {str(result.get("trace_id") or "") for result in cached_results}
    unique_traces = len(trace_ids) == len(cached_results) and "" not in trace_ids

    return {
        "roster_size": roster_size,
        "iterations": iterations,
        "benchmark_batches": _BENCHMARK_BATCHES,
        "latency_samples": len(latencies_ms),
        "workers": workers,
        "p50_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(statistics.median(latency_batch_p95_ms), 3),
        "aggregate_p95_ms": round(_percentile(latencies_ms, 0.95), 3),
        "p95_batches_ms": [round(value, 3) for value in latency_batch_p95_ms],
        "max_ms": round(max(latencies_ms), 3),
        "concurrent_calls": concurrent_calls,
        "concurrent_overlap": concurrency["overlap"],
        "concurrent_probe_threads": concurrency["threads"],
        "concurrent_probe_synchronized": concurrency["synchronized"],
        "concurrent_total_ms": round(concurrent_ms, 3),
        "concurrent_calls_per_second": round(concurrent_calls / max(concurrent_ms / 1000, 1e-9), 2),
        "deterministic": consistent,
        "cache_hit_samples": len(cache_latencies_ms),
        "cache_hit_p50_ms": round(statistics.median(cache_latencies_ms), 3),
        "cache_hit_p95_ms": round(
            statistics.median(cache_latency_batch_p95_ms),
            3,
        ),
        "cache_hit_aggregate_p95_ms": round(
            _percentile(cache_latencies_ms, 0.95),
            3,
        ),
        "cache_hit_p95_batches_ms": [round(value, 3) for value in cache_latency_batch_p95_ms],
        "cache_hit_max_ms": round(max(cache_latencies_ms), 3),
        "cache_hit_deterministic": cache_consistent and unique_traces,
    }


__all__ = ["generated_catalog", "run_candidate_microbenchmark"]
