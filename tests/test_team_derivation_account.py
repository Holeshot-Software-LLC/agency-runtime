"""AR-391 / ADR-0207: tell the recruiter how its ranking becomes the team.

Captured 2026-09-04 on the eleven install wordings: on a review unit whose
``capability:risk-analysis`` was covered by exactly one eligible card, the
recruiter's faithful answer ranked the owner first and that coverer fourth or
fifth. The runtime added the coverer as a typed-coverage complement, read the
unit's confidence from the coverer's rank score (0.7 or 0.6 against a 0.8
minimum) and rejected the team as ``selection_confidence_too_low`` with the
code alone as feedback. The repair inverted the team, the coverer alone was
selected, and the strict critic vetoed it as a wrong neighbour. Nothing the
recruiter read said that acceptable candidates join only for typed coverage,
that a ranking is read as order alone, or that the lowest selected rank sets
the confidence. These cases pin the account: the contract carries the
derivation facts with the verifier's own numbers, both prompts state them,
the scorer and the contract share one step, and a whole-team rejection shows
the derived team beside the correction the recruiter can make.
"""

from __future__ import annotations

import json
from typing import Any

from agency_runtime.core.workforce.contract import WorkforceContract
from agency_runtime.core.workforce.inference import (
    _RECRUITER_REPAIR_SYSTEM,
    _RECRUITER_SYSTEM,
    _STAFFING_VIOLATION_REPAIR_REQUIREMENTS,
    _calibrated_rankings,
    _rank_score_step,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.staffing_verifier import STAFFING_VERIFIER_REASON_CODES
from tests.test_strict_critic_doctrine import _config, _context, _contract, _result, _snapshot

_PLAN_UNIT = "unit-install-plan"
_REVIEW_UNIT = "unit-install-review"
_PLAN = {
    "request_summary": "Install the editor and review the approach.",
    "units": [
        {
            "unit_id": _PLAN_UNIT,
            "outcome": "Plan the editor install using the supported method.",
            "artifact_kind": "plan",
            "domains": ["operations"],
            "stacks": [],
            "capability_ids": ["planning", "operations"],
            "novel_capability": "",
            "depends_on": [],
        },
        {
            "unit_id": _REVIEW_UNIT,
            "outcome": "Review the install approach for configuration and PATH risk.",
            "artifact_kind": "review-report",
            "domains": ["quality-assurance"],
            "stacks": [],
            "capability_ids": ["review", "risk-analysis"],
            "novel_capability": "",
            "depends_on": [_PLAN_UNIT],
        },
    ],
}


def _reviewer(agent_id: str, *capabilities: str) -> WorkforceContract:
    return _contract(
        agent_id,
        authority="review",
        artifact="review-report",
        lifecycle="review",
        domains=("quality-assurance",),
        capabilities=("review", *capabilities),
    )


def _roster() -> Any:
    # One planner for the plan unit; four reviewers for the review unit, of
    # which only the analyzer covers risk-analysis: the captured shape.
    return _snapshot(
        _contract("operations-manager"),
        _reviewer("release-verifier"),
        _reviewer("code-reviewer"),
        _reviewer("reality-checker"),
        _reviewer("test-results-analyzer", "risk-analysis"),
    )


def _row(agent_id: str, classification: str, score: float) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "score": score,
        "classification": classification,
        "positive_evidence": ["fit"],
        "negative_evidence": [],
    }


def _nomination(review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": _PLAN_UNIT,
                "decision": "staff",
                "ranked_semantic": [_row("operations-manager", "required", 0.9)],
            },
            {"unit_id": _REVIEW_UNIT, "decision": "staff", "ranked_semantic": review_rows},
        ]
    }


# The faithful answer as captured: the owner first, the sole coverer fourth.
_OWNER_FIRST_COVERER_FOURTH = [
    _row("release-verifier", "required", 0.9),
    _row("code-reviewer", "acceptable", 0.7),
    _row("reality-checker", "acceptable", 0.6),
    _row("test-results-analyzer", "acceptable", 0.4),
]
# The same team ranked in team order: the coverer directly after the owner.
_OWNER_THEN_COVERER = [
    _row("release-verifier", "required", 0.9),
    _row("test-results-analyzer", "acceptable", 0.8),
    _row("code-reviewer", "acceptable", 0.7),
    _row("reality-checker", "acceptable", 0.6),
]


def _run(*recruiter_replies: dict[str, Any]) -> tuple[Any, list[dict[str, Any]], list[str]]:
    replies = iter(recruiter_replies)
    prompts: list[dict[str, Any]] = []
    raw_prompts: list[str] = []

    def invoke(*args: Any, **_kwargs: Any) -> Any:
        raw_prompts.append(str(args[1]))
        document = json.loads(str(args[1]).split("\n\n[RUNTIME", 1)[0])
        prompts.append(document)
        if "planning_taxonomy" in document:
            return _result(_PLAN)
        if "detail_cards" in document:
            return _result(next(replies))
        return _result({"approved": True, "reason_codes": []})

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _roster(),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    return outcome, prompts, raw_prompts


def test_the_contract_states_the_derivation_with_the_verifier_s_own_numbers() -> None:
    _outcome, prompts, _raw = _run(_nomination(_OWNER_THEN_COVERER))

    contract = prompts[1]["response_contract"]
    config = _config()
    assert contract["acceptable_candidates_join_only_for_typed_coverage"] is True
    assert contract["ranking_is_read_as_order_only"] is True
    assert contract["confidence_is_the_lowest_selected_rank_score"] is True
    assert contract["margin_is_against_the_best_alternative_team"] is True
    assert contract["minimum_confidence"] == config.workforce.min_confidence
    assert contract["minimum_margin"] == config.workforce.min_margin
    assert contract["rank_score_step"] == _rank_score_step(config.workforce.min_margin)
    # The older flags keep their meaning beside the new account.
    assert contract["required_candidates_are_mandatory"] is True
    assert contract["acceptable_candidates_are_optional"] is True


def test_each_recall_row_names_the_requirements_only_one_eligible_card_covers() -> None:
    _outcome, prompts, _raw = _run(_nomination(_OWNER_THEN_COVERER))

    rows = {row["unit_id"]: row for row in prompts[1]["typed_recall"]}
    # Four reviewers cover the review unit; risk-analysis is the analyzer's alone.
    assert rows[_REVIEW_UNIT]["sole_eligible_coverers"] == {
        "capability:risk-analysis": "test-results-analyzer"
    }
    assert "test-results-analyzer" in rows[_REVIEW_UNIT]["eligible_candidate_ids"]
    # One planner covers the plan unit, so every requirement there is its alone.
    plan_row = rows[_PLAN_UNIT]
    assert set(plan_row["sole_eligible_coverers"]) == set(plan_row["requirements"])
    assert set(plan_row["sole_eligible_coverers"].values()) == {"operations-manager"}


def test_the_scorer_and_the_contract_share_one_rank_score_step() -> None:
    step = _rank_score_step(0.1)
    ranked = _calibrated_rankings({"a": 0.95, "b": 0.5, "c": 0.4, "d": 0.05}, minimum_margin=0.1)
    assert [score for _agent, score in ranked] == [1.0, 0.9, 0.8, 0.7]
    assert all(score == round(1.0 - index * step, 6) for index, (_a, score) in enumerate(ranked))
    # The step never falls below the floor the scorer keeps.
    assert _rank_score_step(0.0) == 0.01


def test_both_prompts_state_how_the_ranking_becomes_the_team() -> None:
    for phrase in (
        "acceptable: a substitute the runtime adds only when the required candidates leave a "
        "typed_recall requirement uncovered",
        "it never adds one for fit",
        "reads your ranking as order alone",
        "response_contract.rank_score_step",
        "A unit's confidence is the rank score of its lowest-ranked selected worker",
        "response_contract.minimum_confidence",
        "rank in team order",
        "sole_eligible_coverers names every requirement that exactly one eligible card covers",
        "that card is on every safe team for the unit",
        "keep the faithful owner required and rank that coverer directly after the team it completes",
        "Required is the team, not an emphasis label",
        "a card whose not_for line names the unit's work is not a faithful owner",
    ):
        assert phrase in _RECRUITER_SYSTEM, phrase
    for phrase in (
        "acceptable candidates join only as typed-coverage complements in your rank order, never for fit",
        "reads your ranking as order alone",
        "rank score of its lowest-ranked selected worker, coverage complements included",
        "rank in team order with every coverage complement directly after the team it completes",
        "typed_recall.sole_eligible_coverers names the cards every safe team must hold",
    ):
        assert phrase in _RECRUITER_REPAIR_SYSTEM, phrase
    assert "Do not label every strong candidate required" not in _RECRUITER_SYSTEM


def test_a_whole_team_rejection_shows_the_derived_team_and_the_correction() -> None:
    outcome, prompts, raw_prompts = _run(
        _nomination(_OWNER_FIRST_COVERER_FOURTH), _nomination(_OWNER_THEN_COVERER)
    )

    # The captured mechanism: the coverer added at rank four sets the confidence.
    statuses = [attempt.status for attempt in outcome.attempts if attempt.stage == "recruiter"]
    assert statuses == ["rejected", "applied"]
    rejected = next(attempt for attempt in outcome.attempts if attempt.status == "rejected")
    assert "unit-install-review=selection_confidence_too_low" in rejected.validation_detail
    feedback = json.loads(raw_prompts[2].split("[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])
    violation = feedback["staffing_violations"][0]
    assert violation["unit_id"] == _REVIEW_UNIT
    assert violation["code"] == "selection_confidence_too_low"
    assert (
        violation["required_correction"]
        == _STAFFING_VIOLATION_REPAIR_REQUIREMENTS["selection_confidence_too_low"]
    )
    assert violation["derived_team"] == {
        "selected": ["release-verifier", "test-results-analyzer"],
        "required": ["release-verifier"],
        "runtime_added_for_typed_coverage": ["test-results-analyzer"],
        "confidence": 0.7,
        "margin": 0.7,
        "lowest_ranked_selected": {
            "agent_id": "test-results-analyzer",
            "rank": 4,
            "rank_score": 0.7,
        },
    }
    assert feedback["team_derivation"] == {
        "minimum_confidence": _config().workforce.min_confidence,
        "minimum_margin": _config().workforce.min_margin,
        "confidence_is_the_lowest_selected_rank_score": True,
        "acceptable_candidates_join_only_for_typed_coverage": True,
    }
    # The same team in team order passes: the coverer at rank two scores 0.9.
    assert outcome.accepted
    review = next(unit for unit in outcome.staffing.units if unit.unit_id == _REVIEW_UNIT)
    assert review.selected == ("release-verifier", "test-results-analyzer")
    row = next(unit for unit in outcome.proposal.units if unit.unit_id == _REVIEW_UNIT)
    assert row.confidence == 0.9
    # The repair document is the recruiter's own document again, not a merge.
    assert prompts[2]["response_contract"]["confidence_is_the_lowest_selected_rank_score"] is True


def test_every_named_correction_is_a_verifier_code_and_a_bare_code_stays_bare() -> None:
    assert set(_STAFFING_VIOLATION_REPAIR_REQUIREMENTS) <= set(STAFFING_VERIFIER_REASON_CODES)
    assert "plan_hash_mismatch" not in _STAFFING_VIOLATION_REPAIR_REQUIREMENTS
