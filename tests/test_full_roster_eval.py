"""Contract tests for complete-roster deterministic selection evidence."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.evals.full_roster import (
    DEFAULT_CANDIDATE_LIMIT,
    SCHEMA,
    THRESHOLDS,
    VERSION,
    _gap_groups,
    _probe_queries,
    run_full_roster_selection_eval,
)


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return run_full_roster_selection_eval()


def test_full_roster_eval_is_truthfully_contract_only(report: dict[str, Any]) -> None:
    assert report["schema"] == SCHEMA
    assert report["version"] == VERSION
    assert report["candidate_limit"] == DEFAULT_CANDIDATE_LIMIT
    assert report["evidence"] == {
        "kind": "contract_only",
        "network_used": False,
        "inference_used": False,
        "live_host_used": False,
        "task_outcomes_measured": False,
        "superiority_claimed": False,
        "limitation": (
            "This report measures packaged routing contracts and deterministic "
            "control behavior only. It cannot establish task quality or "
            "superiority over a native host or another router."
        ),
    }
    assert report["roster"]["manifest_total"] == 263
    assert report["roster"]["manifest_approved"] == 263
    assert report["roster"]["manifest_quarantined"] == 0
    assert report["roster"]["manifest_retired"] == 0
    assert report["roster"]["approved_enabled"] == 263
    assert report["roster"]["division_count"] == 17


def test_every_approved_enabled_agent_participates_in_both_retrievers(
    report: dict[str, Any],
) -> None:
    participation = report["metrics"]["participation"]
    assert participation["approved_enabled_count"] == 263
    assert participation["prompt_body_field_count"] == 0
    assert participation["lexical_participation_count"] == 263
    assert participation["lexical_participation_rate"] == 1.0
    assert participation["lexical_missing_agent_ids"] == []
    assert participation["semantic_participation_count"] == 263
    assert participation["semantic_participation_rate"] == 1.0
    assert participation["semantic_missing_agent_ids"] == []
    assert "field-access instrumentation" in participation["proof_method"]


def test_identity_free_probes_report_agent_and_category_gaps(
    report: dict[str, Any],
) -> None:
    metrics = report["metrics"]["probe_retrieval"]
    details = report["details"]["probe_retrieval"]
    assert metrics["probe_count"] == 263
    assert metrics["unique_probe_count"] == 263
    assert metrics["target_hits"] == 263
    assert metrics["target_candidate_recall"] == 1.0
    assert metrics["target_recall_at_10"] >= THRESHOLDS["target_recall_at_10"][1]
    assert metrics["positive_candidate_identity_count"] == 263
    assert metrics["positive_candidate_identity_coverage"] == 1.0
    assert metrics["complete_candidate_identity_count"] == 263
    assert metrics["complete_candidate_identity_coverage"] == 1.0
    assert metrics["identity_leak_count"] == 0
    assert metrics["preferred_sentence_copy_count"] == 0
    assert metrics["missed_agent_ids"] == []
    assert metrics["positive_candidate_gaps"] == []

    top_ten_misses = {detail["slug"] for detail in details if not detail["target_top_10_hit"]}
    assert top_ten_misses == set(metrics["top_10_missed_agent_ids"])
    assert all(detail["target_hit"] for detail in details)
    assert all(not detail["identity_leak"] for detail in details)
    assert all(not detail["preferred_sentence_copy"] for detail in details)
    assert all(len(detail["anchors"]) == 2 for detail in details)

    divisions = metrics["division_gaps"]
    categories = metrics["category_gaps"]
    assert len(divisions) == 17
    assert categories
    assert all(group["target_recall"] == 1.0 for group in divisions.values())
    assert all(group["target_recall"] == 1.0 for group in categories.values())
    grouped_top_ten_misses = {
        slug for group in categories.values() for slug in group["top_10_missed_agent_ids"]
    }
    assert top_ten_misses.issubset(grouped_top_ten_misses)


def test_curated_retrieval_covers_hard_negatives_multi_intent_and_abstention(
    report: dict[str, Any],
) -> None:
    metrics = report["metrics"]["curated_retrieval"]
    details = {detail["id"]: detail for detail in report["details"]["curated_retrieval"]}
    assert metrics == {
        "cases": 7,
        "passed_cases": 7,
        "curated_case_accuracy": 1.0,
        "abstention_cases": 1,
        "abstention_accuracy": 1.0,
    }
    assert all(detail["passed"] for detail in details.values())
    assert all(
        all(rank <= detail["max_required_rank"] for rank in detail["required_ranks"].values())
        for detail in details.values()
    )
    assert details["ambiguous-accessibility-neighbor"]["forbidden_above_required"] == []
    assert details["incident-not-offensive-testing"]["forbidden_above_required"] == []
    assert set(details["multi-intent-accessibility-performance"]["required"]) == {
        "accessibility-auditor",
        "performance-benchmarker",
    }
    assert details["out-of-domain-abstention"]["positive_candidate_ids"] == []
    assert details["out-of-domain-abstention"]["candidate_union"]["full_roster_count"] == 263


def test_compatibility_eval_enforces_conflicts_requirements_and_isolation(
    report: dict[str, Any],
) -> None:
    assert report["metrics"]["compatibility"] == {
        "cases": 4,
        "passed_cases": 4,
        "compatibility_case_accuracy": 1.0,
    }
    details = {detail["id"]: detail for detail in report["details"]["compatibility"]}
    conflict = details["explicit-conflict-rejected"]
    assert conflict["selected_ids"] == ["application-security-engineer"]
    assert conflict["rejected"] == [
        {
            "slug": "ai-generated-code-security-auditor",
            "reason": "conflicts_with:application-security-engineer",
        }
    ]
    requirement = details["requirement-closure-is-dependency-first"]
    assert requirement["selected_ids"] == [
        "accessibility-auditor",
        "ui-designer",
    ]
    assert requirement["added_requirements"] == ["accessibility-auditor"]
    assert ["accessibility-auditor", "ui-designer"] in requirement["separate_context_pairs"]
    assert all(detail["passed"] for detail in details.values())


def test_state_eval_keeps_short_replies_bound_to_durable_context(
    report: dict[str, Any],
) -> None:
    assert report["metrics"]["turn_state"] == {
        "cases": 8,
        "passed_cases": 8,
        "turn_case_accuracy": 1.0,
    }
    details = {detail["id"]: detail for detail in report["details"]["turn_state"]}
    assert details["pure-acknowledgement-with-current-empty-state"]["selection_required"] is False
    assert details["acknowledgement-cannot-bypass-active-plan"]["turn_kind"] == ("continuation")
    assert details["yes-grants-pending-authorization"]["turn_kind"] == "continuation"
    assert details["continue-resumes-active-work"]["turn_kind"] == "continuation"
    assert details["ship-it-is-contextual-mutation"]["turn_kind"] == "continuation"
    assert details["go-without-trusted-state-reroutes"]["reroute_required"] is True
    assert details["constraint-change-is-revision"]["turn_kind"] == "revision"
    assert details["exact-control-uses-control-path"]["turn_kind"] == "control"
    assert all(detail["passed"] for detail in details.values())


def test_full_roster_eval_gates_are_deterministic(report: dict[str, Any]) -> None:
    assert THRESHOLDS["target_candidate_recall"] == (">=", 1.0)
    assert THRESHOLDS["target_recall_at_10"] == (">=", 0.99)
    assert report["thresholds"] == {
        metric: {"operator": operator, "threshold": threshold}
        for metric, (operator, threshold) in THRESHOLDS.items()
    }
    assert [gate["metric"] for gate in report["gates"]] == list(THRESHOLDS)
    assert all(gate["passed"] for gate in report["gates"])
    assert report["passed"] is True


@pytest.mark.parametrize("candidate_limit", [True, 7, 81, 40.0, "40"])
def test_full_roster_eval_rejects_invalid_candidate_limits(
    candidate_limit: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="candidate_limit must be an integer from 8 through 80",
    ):
        run_full_roster_selection_eval(candidate_limit=candidate_limit)  # type: ignore[arg-type]


def test_full_roster_eval_internal_input_defenses() -> None:
    with pytest.raises(
        ValueError,
        match="routing card cannot produce an identity-free probe: sparse-card",
    ):
        _probe_queries(
            [
                {
                    "agent_slug": "sparse-card",
                    "name": "Sparse Card",
                    "division": "testing",
                    "categories": None,
                    "capabilities": [],
                    "task_types": (),
                    "description": "",
                }
            ]
        )
    assert (
        _gap_groups(
            [
                {
                    "slug": "empty-label",
                    "division": "",
                    "target_hit": True,
                    "target_top_10_hit": True,
                }
            ],
            "division",
        )
        == {}
    )
