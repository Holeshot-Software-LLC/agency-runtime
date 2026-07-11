"""Regression tests for quantitative routing and delegation accuracy."""

from __future__ import annotations

from agency_runtime.core.evals.benchmarks import run_candidate_microbenchmark
from agency_runtime.core.delegation.lifecycle import (
    build_dependency_graph,
    normalize_work_units,
)
from agency_runtime.core.evals.data.routing_v1 import (
    DELEGATION_CASES,
    POLICY_CASES,
    ROUTING_CASES,
)
from agency_runtime.core.evals.routing import run_routing_eval
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.selector.candidate_narrow import (
    pre_narrow,
    score_agent,
    tokenize,
)
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.policy import detect_actions, load_bundled_policy


def test_metadata_fields_contribute_to_weighted_routing() -> None:
    catalog = [
        {
            "slug": "alpha",
            "name": "Alpha",
            "description": "General specialist",
            "categories": ["security"],
            "capabilities": ["oauth threat modeling"],
            "tool_affinity": ["sast"],
        },
        {
            "slug": "beta",
            "name": "Beta",
            "description": "General specialist",
            "categories": ["writing"],
            "capabilities": ["technical editing"],
            "tool_affinity": ["markdown"],
        },
    ]

    candidates, scores = pre_narrow("threat modeling with sast", catalog)

    assert candidates[0]["slug"] == "alpha"
    assert scores[0] > 0
    assert score_agent(catalog[1], tokenize("threat modeling with sast")) == 0.0


def test_common_inflections_route_to_starter_roster_metadata() -> None:
    candidates, scores = pre_narrow(
        "Design task dependencies",
        STARTER_ROSTER,
        limit=4,
    )

    assert candidates[0]["slug"] == "workflow-architect"
    assert scores[0] > 0


def test_short_tokens_do_not_match_inside_unrelated_words() -> None:
    policy = {
        "actions": {
            "GITHUB": {"triggers": ["pr", "git"], "always_include": []},
            "UI": {"triggers": ["ui"], "always_include": []},
        }
    }

    assert detect_actions("spring flowers and digital cameras", policy)[0] == []
    assert detect_actions("open a PR with git", policy)[0] == ["GITHUB"]
    assert detect_actions("review the UI", policy)[0] == ["UI"]


def test_policy_phrases_allow_punctuation_but_not_noncontiguous_words() -> None:
    policy = {
        "actions": {
            "DELIVERY": {
                "triggers": ["pull request", "ci/cd"],
                "always_include": [],
            }
        }
    }

    assert detect_actions("Create a pull-request", policy)[0] == ["DELIVERY"]
    assert detect_actions("Repair the CI/CD pipeline", policy)[0] == ["DELIVERY"]
    assert detect_actions("Pull the latest request log", policy)[0] == []


def test_policy_reload_cache_is_keyed_by_resolved_path(
    tmp_path,
    monkeypatch,
) -> None:
    from agency_runtime.core.selector import policy as policy_module

    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text(
        "actions:\n  FIRST:\n    triggers: [alpha]\n",
        encoding="utf-8",
    )
    second_path.write_text(
        "actions:\n  SECOND:\n    triggers: [beta]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(policy_module, "_COMPANION_POLICY", None)
    monkeypatch.setattr(policy_module, "_POLICY_MTIME", 0.0)
    monkeypatch.setattr(policy_module, "_POLICY_PATH", None)

    first = policy_module.load_policy(first_path)
    second = policy_module.load_policy(second_path)
    missing = policy_module.load_policy(tmp_path / "missing.yaml")

    assert set(first["actions"]) == {"FIRST"}
    assert set(second["actions"]) == {"SECOND"}
    assert "CODING" in missing["actions"]


def test_status_mixture_and_cross_platform_paths_are_decomposed() -> None:
    status_mix = detect_work_units(
        "Give me status. Also, fix the API. Separately, update the docs."
    )
    windows = detect_work_units(
        r"Fix C:\repo\src\auth.py and update D:\repo\docs\README.md"
    )

    assert status_mix["delegate"] is True
    assert status_mix["count"] == 2
    assert windows["delegate"] is True
    assert windows["source"] == "imperatives_and_paths"


def test_choices_and_sequential_steps_do_not_request_parallel_delegation() -> None:
    choices = detect_work_units("Choose one:\n1. PostgreSQL\n2. SQLite")
    sequential = detect_work_units("Fix the schema, then run the migration tests")

    assert choices["delegate"] is False
    assert choices["count"] == 1
    assert sequential["delegate"] is False
    assert sequential["count"] == 2
    assert sequential["source"] == "sequential_steps"
    assert sequential["units"] == [
        "Fix the schema",
        "then run the migration tests",
    ]
    units = normalize_work_units(sequential)
    graph = build_dependency_graph(units)
    assert graph.edges[units[0].id] == {units[1].id}


def test_bundled_policy_avoids_generic_design_collisions() -> None:
    actions, companions = detect_actions(
        "Review the authentication design, then document the deployment workflow.",
        load_bundled_policy(),
    )

    assert {"ORCHESTRATION", "DEVOPS_INFRA", "DOCUMENTATION", "SECURITY"}.issubset(
        actions
    )
    assert "UI_UX" not in actions
    assert "multi-agent-systems-architect" not in companions


def test_versioned_corpus_is_nontrivial_and_has_unique_cases() -> None:
    all_cases = ROUTING_CASES + POLICY_CASES + DELEGATION_CASES
    ids = [str(case["id"]) for case in all_cases]
    routing_queries = [str(case["query"]) for case in ROUTING_CASES]

    assert len(ROUTING_CASES) >= 30
    assert len(POLICY_CASES) >= 20
    assert len(DELEGATION_CASES) >= 15
    assert len(ids) == len(set(ids))
    assert len(routing_queries) == len(set(routing_queries))
    assert sum(bool(case.get("abstain")) for case in ROUTING_CASES) >= 4
    assert all("required" in case and "forbidden" in case for case in ROUTING_CASES)


def test_routing_eval_meets_published_thresholds() -> None:
    report = run_routing_eval()

    assert report["schema"] == "agency-runtime.routing-eval"
    assert report["version"] == "1.1.0"
    assert report["corpus"]["version"] == "1.1.0"
    assert report["passed"] is True
    assert all(gate["passed"] for gate in report["gates"])
    assert report["metrics"]["routing"]["required_recall_at_3"] >= 0.97
    assert report["metrics"]["routing"]["top_k_accuracy"] >= 0.95
    assert report["metrics"]["routing"]["abstain_accuracy"] == 1.0
    assert report["metrics"]["policy"]["forbidden_case_rate"] == 0.0
    assert report["metrics"]["policy"]["macro_f1"] >= 0.95
    assert report["metrics"]["delegation"]["decision_accuracy"] >= 0.94
    assert report["metrics"]["delegation"]["precision"] >= 0.95
    assert report["metrics"]["delegation"]["recall"] >= 0.90
    assert report["metrics"]["delegation"]["graph_accuracy"] == 1.0
    assert report["metrics"]["performance"]["p95_ms"] < 20.0
    assert report["metrics"]["performance"]["cache_hit_p95_ms"] < 2.0
    assert report["metrics"]["performance"]["concurrent_calls"] >= 32
    assert report["metrics"]["performance"]["concurrent_overlap"] >= 2


def test_microbenchmark_is_concurrent_deterministic_and_production_bounded() -> None:
    result = run_candidate_microbenchmark(
        roster_size=1000,
        iterations=32,
        workers=8,
    )

    assert result["roster_size"] == 1000
    assert result["benchmark_batches"] >= 3
    assert result["latency_samples"] == (
        result["iterations"] * result["benchmark_batches"]
    )
    assert result["cache_hit_samples"] >= (128 * result["benchmark_batches"])
    assert len(result["p95_batches_ms"]) == result["benchmark_batches"]
    assert len(result["cache_hit_p95_batches_ms"]) == result["benchmark_batches"]
    assert result["concurrent_calls"] >= 32
    assert result["concurrent_overlap"] >= 2
    assert result["deterministic"] is True
    assert result["cache_hit_deterministic"] is True
    assert result["p95_ms"] < 20.0
    assert result["cache_hit_p95_ms"] < 2.0
