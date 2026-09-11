"""AR-437 / ADR-0249: the verifier enforces the reviewer independence the plan calls for.

Live on 2026-09-10 one ordinary-review request produced, on every host, an
analysis unit plus a review-report unit whose outcome said "independently
review" it, with ``code-reviewer`` staffed on both while other eligible
reviewers were ranked. The strict critic vetoed that shape on two hosts and
approved it on two others. The verifier now refuses the reuse as a repairable
failure when an independent covering team exists in the recruiter's own
executable ranking, so the recruiter repairs the team before the critic sees
it, and adds nothing when no such team exists.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.inference import (
    _STAFFING_VIOLATION_REPAIR_REQUIREMENTS,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.staffing_verifier import (
    ADVISORY_STAFFING_CODES,
    STAFFING_VERIFIER_REASON_CODES,
    AbstentionReason,
    verify_staffing,
)
from tests.test_workforce_inference import (
    _config,
    _context,
    _contract,
    _nominee,
    _result,
    _snapshot,
)

_ANALYSIS = "unit-defect-analysis"
_REVIEW = "unit-independent-review"
_REQUEST = "Review this function for its defects and independently review that analysis."


def _reviewer(agent_id: str):
    return replace(
        _contract(agent_id),
        archetype="reviewer",
        authority="review",
        artifact_kinds=("analysis", "review-report"),
        lifecycle_phases=("discovery", "review"),
        capability_ids=("analysis", "review"),
    )


def _plan() -> dict[str, Any]:
    return {
        "request_summary": "Analyze the function, then independently review the analysis.",
        "units": [
            {
                "unit_id": _ANALYSIS,
                "outcome": "Statically analyze the supplied function for defects",
                "artifact_kind": "analysis",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["analysis"],
                "novel_capability": "",
                "depends_on": [],
            },
            {
                "unit_id": _REVIEW,
                "outcome": "Independently review the defect analysis for correctness",
                "artifact_kind": "review-report",
                "domains": ["software-engineering"],
                "stacks": [],
                "capability_ids": ["review"],
                "novel_capability": "",
                "depends_on": [_ANALYSIS],
            },
        ],
    }


def _nomination(review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": _ANALYSIS,
                "decision": "staff",
                "ranked_semantic": [_nominee("code-reviewer", 0.99)],
            },
            {"unit_id": _REVIEW, "decision": "staff", "ranked_semantic": review_rows},
        ]
    }


def _run(*replies: dict[str, Any], contracts=None) -> tuple[Any, list[str]]:
    clear_workforce_caches()
    responses = iter((_result(_plan()), *(_result(reply) for reply in replies)))
    prompts: list[str] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
        return next(responses)

    outcome = plan_and_staff_workforce(
        _REQUEST,
        _snapshot(*(contracts or (_reviewer("code-reviewer"), _reviewer("silent-failure-hunter")))),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    return outcome, prompts


def test_the_captured_shape_is_repaired_before_the_critic_sees_it() -> None:
    reused = _nomination(
        [_nominee("code-reviewer", 0.99), _nominee("silent-failure-hunter", 0.9, "acceptable")]
    )
    repaired = _nomination(
        [_nominee("silent-failure-hunter", 0.99), _nominee("code-reviewer", 0.9, "acceptable")]
    )
    outcome, prompts = _run(reused, repaired)

    assert outcome.accepted
    assert outcome.calls_used == 3
    assert [attempt.status for attempt in outcome.attempts] == ["applied", "rejected", "applied"]
    assert outcome.attempts[1].validation_detail == (
        f"workforce staffing verification failures: {_REVIEW}=review_reviewer_reused"
    )
    feedback = json.loads(prompts[2].partition("[RUNTIME VALIDATION FEEDBACK]\n")[2])
    violation = next(row for row in feedback["staffing_violations"] if row["unit_id"] == _REVIEW)
    assert violation["code"] == "review_reviewer_reused"
    assert (
        violation["required_correction"]
        == (_STAFFING_VIOLATION_REPAIR_REQUIREMENTS["review_reviewer_reused"])
    )
    assert "not selected on any unit it reviews" in violation["required_correction"]
    # The repair names what the verifier validated: the reused worker and the
    # unit it reviews, identifiers only.
    assert violation["reused_workers"] == ["code-reviewer"]
    assert violation["reviewed_units"] == [_ANALYSIS]
    staffed = {unit.unit_id: unit.selected for unit in outcome.staffing.units}
    assert staffed == {_ANALYSIS: ("code-reviewer",), _REVIEW: ("silent-failure-hunter",)}
    assert outcome.staffing.abstention_reasons == ()


def test_the_finding_names_the_reused_worker_and_the_reviewed_unit() -> None:
    reused = _nomination(
        [_nominee("code-reviewer", 0.99), _nominee("silent-failure-hunter", 0.9, "acceptable")]
    )
    outcome, _ = _run(reused, reused)

    assert not outcome.accepted
    assert (
        AbstentionReason("review_reviewer_reused", _REVIEW, "code-reviewer", _ANALYSIS)
        in outcome.staffing.abstention_reasons
    )
    assert "review_reviewer_reused" in STAFFING_VERIFIER_REASON_CODES
    assert "review_reviewer_reused" not in ADVISORY_STAFFING_CODES


def test_without_an_independent_team_the_verifier_adds_nothing() -> None:
    # No other reviewer ranked: the team stays staffable and no code changes
    # meaning (the advisory independent_assurance_missing stays a modify-unit
    # finding, which keeps gap hiring's per-unit rule intact).
    only_reviewer = _nomination([_nominee("code-reviewer", 0.99)])
    outcome, _ = _run(only_reviewer)

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert {unit.unit_id: unit.selected for unit in outcome.staffing.units} == {
        _ANALYSIS: ("code-reviewer",),
        _REVIEW: ("code-reviewer",),
    }
    assert outcome.staffing.abstention_reasons == ()


def test_an_eligible_worker_that_cannot_cover_the_unit_alone_is_no_alternative() -> None:
    # The candidate is eligible for the review unit but covers no review-report
    # artifact, so no independent covering team exists and the reuse stands.
    partial = replace(
        _reviewer("partial-analyst"),
        artifact_kinds=("analysis",),
        lifecycle_phases=("discovery",),
    )
    reused = _nomination(
        [_nominee("code-reviewer", 0.99), _nominee("partial-analyst", 0.9, "acceptable")]
    )
    outcome, _ = _run(reused, contracts=(_reviewer("code-reviewer"), partial))

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert {unit.unit_id: unit.selected for unit in outcome.staffing.units} == {
        _ANALYSIS: ("code-reviewer",),
        _REVIEW: ("code-reviewer",),
    }
    assert outcome.staffing.abstention_reasons == ()


def test_a_forbidden_candidate_is_no_alternative() -> None:
    reused = _nomination(
        [_nominee("code-reviewer", 0.99), _nominee("silent-failure-hunter", 0.9, "forbidden")]
    )
    outcome, _ = _run(reused)

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert outcome.staffing.abstention_reasons == ()


def test_the_rule_reads_the_after_artifact_timing_like_its_siblings() -> None:
    # A verify_staffing replay with the review row's timing altered shows the
    # rule bound to the same predicate _has_assurance and _composition use.
    reused = _nomination(
        [_nominee("code-reviewer", 0.99), _nominee("silent-failure-hunter", 0.9, "acceptable")]
    )
    repaired = _nomination(
        [_nominee("silent-failure-hunter", 0.99), _nominee("code-reviewer", 0.9, "acceptable")]
    )
    outcome, _ = _run(reused, repaired)
    assert outcome.accepted
    contracts = (_reviewer("code-reviewer"), _reviewer("silent-failure-hunter"))

    def review_row(timing: str):
        row = next(item for item in outcome.proposal.units if item.unit_id == _REVIEW)
        # Put the reused reviewer back on the review unit; the ranking still
        # holds the independent alternative, so only the timing decides.
        return replace(
            row,
            selected=("code-reviewer",),
            required=("code-reviewer",),
            acceptable=("silent-failure-hunter",),
            timing=timing,
        )

    def codes(timing: str) -> set[str]:
        altered = replace(
            outcome.proposal,
            units=tuple(
                review_row(timing) if row.unit_id == _REVIEW else row
                for row in outcome.proposal.units
            ),
        )
        decision = verify_staffing(outcome.plan, altered, contracts, context=_context())
        return {reason.code for reason in decision.abstention_reasons}

    assert "review_reviewer_reused" in codes("after_artifact")
    assert "review_reviewer_reused" not in codes("immediate")


def test_an_independent_team_passes_untouched() -> None:
    independent = _nomination(
        [_nominee("silent-failure-hunter", 0.99), _nominee("code-reviewer", 0.9, "acceptable")]
    )
    outcome, _ = _run(independent)

    assert outcome.accepted
    assert outcome.calls_used == 2
    assert outcome.staffing.abstention_reasons == ()
