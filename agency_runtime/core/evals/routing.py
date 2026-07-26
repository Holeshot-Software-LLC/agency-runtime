"""Versioned quantitative evaluation for routing, policy, and delegation."""

from __future__ import annotations

from typing import Any

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig
from agency_runtime.core.delegation.lifecycle import (
    build_dependency_graph,
    normalize_work_units,
)
from agency_runtime.core.evals.benchmarks import (
    CLI_VERSION_STARTUP_P50_MS_MAX,
    SEMANTIC_RETRIEVAL_BUDGETS,
    run_candidate_microbenchmark,
    run_cli_version_startup_benchmark,
    run_semantic_retrieval_scale_benchmark,
)
from agency_runtime.core.evals.data.routing_v1 import (
    CATALOG,
    DELEGATION_CASES,
    POLICY_CASES,
    ROUTING_CASES,
)
from agency_runtime.core.evals.data.routing_v1 import (
    SCHEMA as CORPUS_SCHEMA,
)
from agency_runtime.core.evals.data.routing_v1 import (
    VERSION as CORPUS_VERSION,
)
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.pipeline import route
from agency_runtime.core.selector.policy import detect_actions, load_bundled_policy
from agency_runtime.core.selector.semantic_retrieval import clear_semantic_retrieval_cache
from agency_runtime.core.selector.stickiness import clear_session_routing

SCHEMA = "agency-runtime.routing-eval"
VERSION = "1.3.0"
TOP_K = 3

THRESHOLDS: dict[str, dict[str, float]] = {
    "routing": {
        "precision_at_3_min": 0.75,
        "required_recall_at_3_min": 0.97,
        "top_k_accuracy_min": 0.95,
        "top_1_accuracy_min": 0.90,
        "forbidden_case_rate_max": 0.0,
        "abstain_accuracy_min": 1.0,
    },
    "policy": {
        "macro_f1_min": 0.95,
        "required_recall_min": 0.95,
        "case_accuracy_min": 0.95,
        "forbidden_case_rate_max": 0.0,
        "companion_required_recall_min": 1.0,
        "companion_case_accuracy_min": 1.0,
    },
    "delegation": {
        "precision_min": 0.95,
        "recall_min": 0.90,
        "decision_accuracy_min": 0.94,
        "count_accuracy_min": 0.90,
        "source_accuracy_min": 0.90,
        "graph_accuracy_min": 1.0,
    },
    "performance": {
        # Warm deterministic narrowing of a 1,000-agent roster. This leaves
        # headroom for loaded Windows/Linux CI workers while still catching a
        # material regression in the request hot path.
        "p95_ms_max": 20.0,
        "cache_hit_p95_ms_max": 2.0,
        "concurrent_calls_per_second_min": 40.0,
        "concurrent_overlap_min": 2.0,
        "concurrent_probe_synchronized_min": 1.0,
        "deterministic_min": 1.0,
        "cache_hit_deterministic_min": 1.0,
    },
    "retrieval_scale": {
        **{
            f"agents_{size}_{metric}": threshold
            for size, budget in SEMANTIC_RETRIEVAL_BUDGETS.items()
            for metric, threshold in budget.items()
        },
        **{f"agents_{size}_correct_min": 1.0 for size in SEMANTIC_RETRIEVAL_BUDGETS},
    },
    "cli_startup": {
        "version_p50_ms_max": CLI_VERSION_STARTUP_P50_MS_MAX,
        "output_valid_min": 1.0,
    },
}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _routing_metrics() -> tuple[dict[str, float | int], list[dict[str, Any]]]:
    relevant_hits = 0
    predictions = 0
    required_hits = 0
    required_total = 0
    top_one_hits = 0
    top_k_hits = 0
    required_cases = 0
    forbidden_cases = 0
    abstain_hits = 0
    abstain_cases = 0
    details: list[dict[str, Any]] = []

    offline = AgencyConfig(
        providers=(),
        judge=JudgeConfig(model="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    for case in ROUTING_CASES:
        clear_cache()
        clear_session_routing()
        decision = route(
            f"eval-{case['id']}",
            str(case["query"]),
            CATALOG,
            config=offline,
        )
        predicted = [
            str(item) for item in decision.get("semantic_ids", decision.get("selected_ids", []))
        ][:TOP_K]
        required = {str(item) for item in case.get("required", [])}
        acceptable = {str(item) for item in case.get("acceptable", [])}
        forbidden = {str(item) for item in case.get("forbidden", [])}
        relevant = required | acceptable
        abstain = bool(case.get("abstain", False))

        if abstain:
            abstain_cases += 1
            abstain_hits += int(not predicted)
        else:
            predictions += len(predicted)
            relevant_hits += sum(item in relevant for item in predicted)
        if required:
            required_cases += 1
            required_total += len(required)
            required_hits += len(required.intersection(predicted))
            top_k_hits += int(required.issubset(predicted))
            top_one_hits += int(bool(predicted) and predicted[0] in relevant)
        forbidden_hit = bool(forbidden.intersection(predicted))
        forbidden_cases += int(forbidden_hit)

        passed = (
            required.issubset(predicted) and not forbidden_hit and (not abstain or not predicted)
        )
        details.append(
            {
                "id": case["id"],
                "predicted": predicted,
                "required": sorted(required),
                "acceptable": sorted(acceptable),
                "forbidden_hit": sorted(forbidden.intersection(predicted)),
                "final_selected": list(decision.get("selected_ids", [])),
                "status": decision.get("status"),
                "trace_id": decision.get("trace_id"),
                "passed": passed,
            }
        )

    total_cases = len(ROUTING_CASES)
    return {
        "cases": total_cases,
        "precision_at_3": _ratio(relevant_hits, predictions),
        "required_recall_at_3": _ratio(required_hits, required_total),
        "top_k_accuracy": _ratio(top_k_hits, required_cases),
        "top_1_accuracy": _ratio(top_one_hits, required_cases),
        "forbidden_case_rate": _ratio(forbidden_cases, total_cases),
        "abstain_accuracy": _ratio(abstain_hits, abstain_cases),
    }, details


def _policy_metrics() -> tuple[dict[str, float | int], list[dict[str, Any]]]:
    # Local user policy must not change the reproducible production baseline.
    bundled = load_bundled_policy()
    required_hits = 0
    required_total = 0
    passed_cases = 0
    forbidden_cases = 0
    companion_required_hits = 0
    companion_required_total = 0
    companion_passed_cases = 0
    companion_cases = 0
    details: list[dict[str, Any]] = []
    by_action: dict[str, dict[str, int]] = {}
    active_slugs = {str(item["slug"]) for item in STARTER_ROSTER}
    for case in POLICY_CASES:
        matched, companions = detect_actions(
            str(case["message"]),
            bundled,
            active_slugs=active_slugs,
        )
        predicted = set(matched)
        predicted_companions = set(companions)
        required = {str(item) for item in case.get("required", [])}
        required_companions = {str(item) for item in case.get("required_companions", [])}
        forbidden = {str(item) for item in case.get("forbidden", [])}
        required_total += len(required)
        required_hits += len(required.intersection(predicted))
        forbidden_hit = forbidden.intersection(predicted)
        for action in required | predicted:
            counts = by_action.setdefault(action, {"tp": 0, "fp": 0, "fn": 0, "support": 0})
            if action in required:
                counts["support"] += 1
                if action in predicted:
                    counts["tp"] += 1
                else:
                    counts["fn"] += 1
            else:
                # ``action`` comes from required | predicted. If it is not
                # required, it is necessarily a false-positive prediction.
                counts["fp"] += 1
        forbidden_cases += int(bool(forbidden_hit))
        if required_companions:
            companion_cases += 1
            companion_required_total += len(required_companions)
            companion_required_hits += len(required_companions.intersection(predicted_companions))
            companion_passed_cases += int(required_companions.issubset(predicted_companions))
        passed = (
            required.issubset(predicted)
            and required_companions.issubset(predicted_companions)
            and not forbidden_hit
        )
        passed_cases += int(passed)
        details.append(
            {
                "id": case["id"],
                "predicted": matched,
                "predicted_companions": companions,
                "required": sorted(required),
                "required_companions": sorted(required_companions),
                "forbidden_hit": sorted(forbidden_hit),
                "passed": passed,
            }
        )
    total = len(POLICY_CASES)
    action_f1 = []
    for counts in by_action.values():
        if not counts["support"]:
            continue
        denominator = (2 * counts["tp"]) + counts["fp"] + counts["fn"]
        action_f1.append((2 * counts["tp"]) / denominator if denominator else 0.0)
    return {
        "cases": total,
        "macro_f1": round(sum(action_f1) / len(action_f1), 4) if action_f1 else 1.0,
        "required_recall": _ratio(required_hits, required_total),
        "case_accuracy": _ratio(passed_cases, total),
        "forbidden_case_rate": _ratio(forbidden_cases, total),
        "companion_required_recall": _ratio(
            companion_required_hits,
            companion_required_total,
        ),
        "companion_case_accuracy": _ratio(
            companion_passed_cases,
            companion_cases,
        ),
    }, details


def _delegation_metrics() -> tuple[dict[str, float | int], list[dict[str, Any]]]:
    decision_hits = 0
    count_hits = 0
    source_hits = 0
    graph_hits = 0
    details: list[dict[str, Any]] = []
    true_positive = false_positive = false_negative = 0
    for case in DELEGATION_CASES:
        result = detect_work_units(str(case["message"]))
        decision_match = bool(result["delegate"]) is bool(case["delegate"])
        count_match = int(result["count"]) == int(case["count"])
        source_match = str(result["source"]) == str(case["source"])
        units = normalize_work_units(case.get("graph_units", result.get("units", [])))
        unit_indexes = {unit.id: index for index, unit in enumerate(units)}
        graph_error = ""
        try:
            graph = build_dependency_graph(units)
            actual_edges = sorted(
                (unit_indexes[source], unit_indexes[target])
                for source, targets in graph.edges.items()
                for target in targets
            )
        except ValueError as exc:
            actual_edges = []
            graph_error = str(exc)
        expected_edges = sorted(
            tuple(int(index) for index in edge) for edge in case.get("edges", [])
        )
        expected_graph_error = str(case.get("graph_error", ""))
        graph_match = (
            expected_graph_error in graph_error
            if expected_graph_error
            else not graph_error and actual_edges == expected_edges
        )
        decision_hits += int(decision_match)
        expected_delegate = bool(case["delegate"])
        actual_delegate = bool(result["delegate"])
        true_positive += int(expected_delegate and actual_delegate)
        false_positive += int(not expected_delegate and actual_delegate)
        false_negative += int(expected_delegate and not actual_delegate)
        count_hits += int(count_match)
        source_hits += int(source_match)
        graph_hits += int(graph_match)
        details.append(
            {
                "id": case["id"],
                "actual": {
                    "delegate": result["delegate"],
                    "count": result["count"],
                    "source": result["source"],
                    "edges": [list(edge) for edge in actual_edges],
                },
                "expected": {
                    "delegate": case["delegate"],
                    "count": case["count"],
                    "source": case["source"],
                    "edges": [list(edge) for edge in expected_edges],
                },
                "passed": decision_match and count_match and source_match and graph_match,
            }
        )
    total = len(DELEGATION_CASES)
    return {
        "cases": total,
        "precision": _ratio(true_positive, true_positive + false_positive),
        "recall": _ratio(true_positive, true_positive + false_negative),
        "decision_accuracy": _ratio(decision_hits, total),
        "count_accuracy": _ratio(count_hits, total),
        "source_accuracy": _ratio(source_hits, total),
        "graph_accuracy": _ratio(graph_hits, total),
    }, details


def _gates(metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for area, thresholds in THRESHOLDS.items():
        for threshold_name, threshold in thresholds.items():
            if threshold_name.endswith("_min"):
                metric_name = threshold_name[:-4]
                operator = ">="
                passed = float(metrics[area][metric_name]) >= threshold
            elif threshold_name.endswith("_max"):
                metric_name = threshold_name[:-4]
                operator = "<="
                passed = float(metrics[area][metric_name]) <= threshold
            else:  # pragma: no cover - constant schema defense
                raise ValueError(f"invalid threshold name: {threshold_name}")
            results.append(
                {
                    "area": area,
                    "metric": metric_name,
                    "value": metrics[area][metric_name],
                    "operator": operator,
                    "threshold": threshold,
                    "passed": passed,
                }
            )
    return results


def _retrieval_scale_metrics(report: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "benchmark_version": report["version"],
        "query_sha256": report["query_sha256"],
        "cold_includes_tracemalloc": report["cold_includes_tracemalloc"],
        "tiers": report["tiers"],
    }
    for row in report["tiers"]:
        size = int(row["roster_size"])
        metrics[f"agents_{size}_cold_ms"] = row["cold_ms"]
        metrics[f"agents_{size}_warm_p95_ms"] = row["warm_p95_ms"]
        metrics[f"agents_{size}_peak_mib"] = row["peak_mib"]
        metrics[f"agents_{size}_correct"] = bool(row["deterministic"] and row["correctness"])
    return metrics


def run_routing_eval(*, include_details: bool = True) -> dict[str, Any]:
    """Run the offline deterministic routing evaluation and performance probe."""
    clear_semantic_retrieval_cache()
    routing, routing_details = _routing_metrics()
    policy, policy_details = _policy_metrics()
    delegation, delegation_details = _delegation_metrics()
    benchmark = run_candidate_microbenchmark()
    retrieval_benchmark = run_semantic_retrieval_scale_benchmark()
    cli_benchmark = run_cli_version_startup_benchmark()
    performance = dict(benchmark)
    metrics = {
        "routing": routing,
        "policy": policy,
        "delegation": delegation,
        "performance": performance,
        "retrieval_scale": _retrieval_scale_metrics(retrieval_benchmark),
        "cli_startup": {
            "benchmark_version": cli_benchmark["version"],
            "iterations": cli_benchmark["iterations"],
            "version_p50_ms": cli_benchmark["p50_ms"],
            "version_p95_ms": cli_benchmark["p95_ms"],
            "samples_ms": cli_benchmark["samples_ms"],
            "output_valid": cli_benchmark["output_valid"],
        },
    }
    gates = _gates(metrics)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "corpus": {
            "schema": CORPUS_SCHEMA,
            "version": CORPUS_VERSION,
            "routing_cases": len(ROUTING_CASES),
            "policy_cases": len(POLICY_CASES),
            "delegation_cases": len(DELEGATION_CASES),
        },
        "top_k": TOP_K,
        "metrics": metrics,
        "thresholds": THRESHOLDS,
        "gates": gates,
        "passed": all(gate["passed"] for gate in gates),
    }
    if include_details:
        report["details"] = {
            "routing": routing_details,
            "policy": policy_details,
            "delegation": delegation_details,
        }
    return report


__all__ = ["SCHEMA", "THRESHOLDS", "VERSION", "run_routing_eval"]
