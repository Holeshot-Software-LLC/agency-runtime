"""AR-441 / ADR-0254: the recruiter is asked for at most two units per call.

A five-unit code mutation produced 77-95 KB recruiter prompts on
2026-09-11 whose first reply did not carry every row, and since 2026-09-08
``missing_work_unit`` was the recruiter's most frequent rejection. These
tests pin the batch split and its order, the sliced batch prompt, the rows
of earlier batches riding along, the single assembly and verification of
the whole team, the per-unit repairs inside a batch and after the last one,
the budget-driven widening, and that a one- or two-unit plan is recruited
exactly as before.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.inference import (
    RECRUITER_UNITS_PER_CALL,
    _CallBudget,
    _recruiter_batches,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from tests.test_workforce_inference import (
    _config,
    _context,
    _contract,
    _nominee,
    _result,
    _snapshot,
)

_REQUEST = "Fix the off-by-one bug in the tokenizer, add tests for the boundary, and run them."
_UNITS = (
    ("unit-discovery", "analysis", "software-engineering", "analysis", []),
    (
        "unit-implementation",
        "implementation-change",
        "software-engineering",
        "implementation",
        ["unit-discovery"],
    ),
    ("unit-tests", "test-code", "quality-assurance", "testing", ["unit-implementation"]),
    ("unit-review", "review-report", "software-engineering", "review", ["unit-tests"]),
    ("unit-evidence", "test-evidence", "quality-assurance", "testing", ["unit-tests"]),
)
_SELECTED = {
    "unit-discovery": "codebase-archaeologist",
    "unit-implementation": "python-engineer",
    "unit-tests": "test-author",
    "unit-review": "code-reviewer",
    "unit-evidence": "test-results-analyzer",
}


def _plan(units: tuple[tuple[str, str, str, str, list[str]], ...] = _UNITS) -> dict[str, Any]:
    return {
        "request_summary": "Fix the tokenizer with tests and evidence.",
        "units": [
            {
                "unit_id": unit_id,
                "outcome": f"{unit_id.replace('unit-', '').replace('-', ' ')} of the tokenizer",
                "artifact_kind": artifact,
                "domains": [domain],
                "stacks": [],
                "capability_ids": [capability],
                "novel_capability": "",
                "depends_on": depends_on,
            }
            for unit_id, artifact, domain, capability, depends_on in units
        ],
    }


def _specialist(
    agent_id: str,
    *,
    artifact: str,
    lifecycle: str,
    domain: str,
    capability: str,
    authority: str,
    tools: tuple[str, ...] = ("repository-read", "repository-write", "code-execution"),
):
    return replace(
        _contract(agent_id),
        archetype="reviewer" if authority == "review" else "implementer",
        outcomes=(f"Own {artifact} work",),
        capability_ids=(capability,),
        artifact_kinds=(artifact,),
        lifecycle_phases=(lifecycle,),
        domains=(domain,),
        authority=authority,
        tool_classes=tools,
    )


def _roster():
    return _snapshot(
        _specialist(
            "codebase-archaeologist",
            artifact="analysis",
            lifecycle="discovery",
            domain="software-engineering",
            capability="analysis",
            authority="advise",
        ),
        _specialist(
            "python-engineer",
            artifact="implementation-change",
            lifecycle="implementation",
            domain="software-engineering",
            capability="implementation",
            authority="modify",
        ),
        _specialist(
            "test-author",
            artifact="test-code",
            lifecycle="testing",
            domain="quality-assurance",
            capability="testing",
            authority="modify",
            tools=("repository-read", "repository-write", "code-execution", "test-execution"),
        ),
        _specialist(
            "code-reviewer",
            artifact="review-report",
            lifecycle="review",
            domain="software-engineering",
            capability="review",
            authority="review",
        ),
        _specialist(
            "silent-failure-hunter",
            artifact="review-report",
            lifecycle="review",
            domain="software-engineering",
            capability="review",
            authority="review",
        ),
        _specialist(
            "test-results-analyzer",
            artifact="test-evidence",
            lifecycle="testing",
            domain="quality-assurance",
            capability="testing",
            authority="review",
        ),
    )


def _rows(unit_ids: list[str], selected: dict[str, str] = _SELECTED) -> dict[str, Any]:
    return {
        "units": [
            {
                "unit_id": unit_id,
                "decision": "staff",
                "ranked_semantic": [_nominee(selected[unit_id], 0.98)],
            }
            for unit_id in unit_ids
        ]
    }


def _run(
    replies: list[dict[str, Any]],
    *,
    budget: int = 8,
    plan: dict[str, Any] | None = None,
    request: str = _REQUEST,
    roster: Any = None,
):
    clear_workforce_caches()
    responses = iter((_result(plan or _plan()), *(_result(reply) for reply in replies)))
    prompts: list[str] = []

    def invoke(_provider, prompt, _schema, **_kwargs):
        prompts.append(prompt)
        return next(responses)

    outcome = plan_and_staff_workforce(
        request,
        roster or _roster(),
        config=_config(mode="balanced", balanced_call_budget=budget),
        context=_context(),
        invoker=invoke,
    )
    return outcome, prompts


def _document(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.partition("\n\n[RUNTIME VALIDATION FEEDBACK]\n")[0])


def _feedback(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.partition("[RUNTIME VALIDATION FEEDBACK]\n")[2])


# --- the split -----------------------------------------------------------------


def test_the_split_is_two_units_in_plan_order_and_widens_to_the_budget() -> None:
    plan = parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "five units",
            "units": [
                {
                    **unit,
                    "lifecycle_phase": "review",
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["review"],
                    "authority": "review",
                    "mutation_scope": "read_only",
                    "risks": [],
                    "trust_boundaries": ["repository"],
                    "claims": [],
                    "resources": ["request"],
                    "required_tools": ["repository-read"],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["evidence"],
                    "parallelization": "unspecified",
                    "artifact_kind": "review-report",
                }
                for unit in (
                    {
                        "unit_id": f"unit-{i}",
                        "outcome": f"unit {i}",
                        "domains": ["x"],
                        "depends_on": [],
                    }
                    for i in range(1, 6)
                )
            ],
        }
    )
    assert RECRUITER_UNITS_PER_CALL == 2
    assert _recruiter_batches(plan, _CallBudget(8), 1) == (
        ("unit-1", "unit-2"),
        ("unit-3", "unit-4"),
        ("unit-5",),
    )
    # Every batch must afford one repair beside the critic's reserve: five
    # remaining calls less the reserve afford two batches, widened evenly.
    budget = _CallBudget(8)
    for _ in range(3):
        budget.consume()
    assert _recruiter_batches(plan, budget, 1) == (
        ("unit-1", "unit-2", "unit-3"),
        ("unit-4", "unit-5"),
    )
    # The shipped default strict budget (5) leaves the single call main made.
    default = _CallBudget(5)
    default.consume()
    assert _recruiter_batches(plan, default, 1) == (
        ("unit-1", "unit-2", "unit-3", "unit-4", "unit-5"),
    )
    # Nothing affordable still asks once; the stage refuses on budget as before.
    for _ in range(5):
        budget.consume()
    assert _recruiter_batches(plan, budget, 1) == (
        ("unit-1", "unit-2", "unit-3", "unit-4", "unit-5"),
    )


# --- batched recruitment ------------------------------------------------------------


def test_a_five_unit_plan_is_recruited_in_three_sliced_batches() -> None:
    outcome, prompts = _run(
        [
            _rows(["unit-discovery", "unit-implementation"]),
            _rows(["unit-tests", "unit-review"]),
            _rows(["unit-evidence"]),
        ]
    )
    assert outcome.accepted
    assert outcome.calls_used == 4
    assert [attempt.stage for attempt in outcome.attempts] == [
        "planner",
        "recruiter",
        "recruiter",
        "recruiter",
    ]
    assert all(attempt.status == "applied" for attempt in outcome.attempts)
    documents = [_document(prompt) for prompt in prompts[1:]]
    assert [d["recruiter_batch"]["unit_ids"] for d in documents] == [
        ["unit-discovery", "unit-implementation"],
        ["unit-tests", "unit-review"],
        ["unit-evidence"],
    ]
    assert [
        (d["recruiter_batch"]["ordinal"], d["recruiter_batch"]["count"]) for d in documents
    ] == [
        (1, 3),
        (2, 3),
        (3, 3),
    ]
    for document in documents:
        batch = document["recruiter_batch"]["unit_ids"]
        assert document["response_contract"]["exact_unit_ids_in_order"] == batch
        assert [row["unit_id"] for row in document["typed_recall"]] == batch
        # The whole plan stays for context; the cards are only the batch's.
        assert [unit["unit_id"] for unit in document["plan"]["units"]] == list(_SELECTED)
        shown = {card["agent_id"] for card in document["detail_cards"]}
        eligible = {
            agent_id
            for row in document["typed_recall"]
            for agent_id in row["eligible_candidate_ids"]
        }
        assert eligible <= shown
    # Earlier batches ride along so the recruiter can keep a reviewer independent.
    assert documents[0]["recruiter_batch"]["earlier_batches"] == []
    assert [row["unit_id"] for row in documents[1]["recruiter_batch"]["earlier_batches"]] == [
        "unit-discovery",
        "unit-implementation",
    ]
    assert documents[1]["recruiter_batch"]["earlier_batches"][1]["required"] == ["python-engineer"]
    assert [row["unit_id"] for row in documents[2]["recruiter_batch"]["earlier_batches"]] == [
        "unit-discovery",
        "unit-implementation",
        "unit-tests",
        "unit-review",
    ]
    # The whole team is one proposal the verifier judged.
    assert [unit.unit_id for unit in outcome.proposal.units] == list(_SELECTED)
    assert outcome.staffing.accepted
    # The batch prompts are each well under the single-call size.
    single = len(json.dumps({**documents[0], "typed_recall": None, "detail_cards": None}))
    assert all(len(prompt) < 2 * single + 20_000 for prompt in prompts[1:])


def test_a_batch_reply_that_carries_other_units_is_read_only_for_its_own() -> None:
    full = _rows(list(_SELECTED))
    outcome, _prompts = _run([full, full, full])
    assert outcome.accepted
    assert outcome.calls_used == 4
    assert [attempt.status for attempt in outcome.attempts] == ["applied"] * 4


def test_a_two_unit_plan_is_recruited_exactly_as_before() -> None:
    review = (
        ("unit-discovery", "analysis", "software-engineering", "analysis", []),
        ("unit-review", "review-report", "software-engineering", "review", ["unit-discovery"]),
    )
    outcome, prompts = _run(
        [_rows(["unit-discovery", "unit-review"])],
        plan=_plan(review),
        request="Review this function for defects and say how to correct them.",
    )
    assert outcome.accepted
    assert outcome.calls_used == 2
    document = _document(prompts[1])
    assert "recruiter_batch" not in document
    assert document["response_contract"]["exact_unit_ids_in_order"] == [
        "unit-discovery",
        "unit-review",
    ]


def test_an_omitted_unit_inside_a_batch_is_repaired_for_that_unit_only() -> None:
    outcome, prompts = _run(
        [
            _rows(["unit-discovery"]),
            _rows(["unit-implementation"]),
            _rows(["unit-tests", "unit-review"]),
            _rows(["unit-evidence"]),
        ]
    )
    assert outcome.accepted
    assert outcome.calls_used == 5
    assert [attempt.status for attempt in outcome.attempts] == [
        "applied",
        "rejected",
        "applied",
        "applied",
        "applied",
    ]
    assert outcome.attempts[1].validation_detail == (
        "workforce nomination failures: unit-implementation=missing_work_unit"
    )
    feedback = _feedback(prompts[2])
    assert [row["unit_id"] for row in feedback["failed_units"]] == ["unit-implementation"]
    # The repair is asked inside the first batch's document.
    assert _document(prompts[2])["recruiter_batch"]["ordinal"] == 1


def test_a_verifier_finding_after_the_last_batch_re_asks_only_its_units() -> None:
    # The review unit comes last; code-reviewer can also do discovery, so
    # staffing it on both is the AR-437 reuse the verifier refuses when an
    # independent reviewer (silent-failure-hunter) is ranked.
    review_last = (
        _UNITS[0],
        _UNITS[1],
        _UNITS[2],
        ("unit-evidence", "test-evidence", "quality-assurance", "testing", ["unit-tests"]),
        ("unit-review", "review-report", "software-engineering", "review", ["unit-tests"]),
    )
    roster = _snapshot(
        *[c for c in _roster().contracts if c.agent_id != "code-reviewer"],
        replace(
            _specialist(
                "code-reviewer",
                artifact="review-report",
                lifecycle="review",
                domain="software-engineering",
                capability="review",
                authority="review",
            ),
            artifact_kinds=("analysis", "review-report"),
            lifecycle_phases=("discovery", "review"),
            capability_ids=("analysis", "review"),
        ),
    )
    selected = {**_SELECTED, "unit-discovery": "code-reviewer"}
    outcome, prompts = _run(
        [
            _rows(["unit-discovery", "unit-implementation"], selected),
            _rows(["unit-tests", "unit-evidence"], selected),
            {
                "units": [
                    {
                        "unit_id": "unit-review",
                        "decision": "staff",
                        "ranked_semantic": [
                            _nominee("code-reviewer", 0.99),
                            _nominee("silent-failure-hunter", 0.9, "acceptable"),
                        ],
                    }
                ]
            },
            {
                "units": [
                    {
                        "unit_id": "unit-review",
                        "decision": "staff",
                        "ranked_semantic": [
                            _nominee("silent-failure-hunter", 0.99),
                            _nominee("code-reviewer", 0.9, "acceptable"),
                        ],
                    }
                ]
            },
        ],
        plan=_plan(review_last),
        roster=roster,
    )
    assert outcome.accepted, outcome.abstention_codes
    statuses = [attempt.status for attempt in outcome.attempts if attempt.stage == "recruiter"]
    assert statuses == ["applied", "applied", "rejected", "applied"]
    rejected = next(a for a in outcome.attempts if a.status == "rejected")
    assert rejected.validation_detail == (
        "workforce staffing verification failures: unit-review=review_reviewer_reused"
    )
    feedback = _feedback(prompts[4])
    assert feedback["failed_units"] == [
        {"unit_id": "unit-review", "codes": ["review_reviewer_reused"]}
    ]
    assert "listed failed unit only" in feedback["required_action"]
    repair_document = _document(prompts[4])
    assert repair_document["recruiter_batch"]["unit_ids"] == ["unit-review"]
    assert repair_document["recruiter_batch"]["repair_after_whole_team_verification"] is True
    # The repair shows the failed unit's own recall row and cards.
    assert [row["unit_id"] for row in repair_document["typed_recall"]] == ["unit-review"]
    assert {card["agent_id"] for card in repair_document["detail_cards"]} >= {
        "code-reviewer",
        "silent-failure-hunter",
    }
    assert [unit.unit_id for unit in outcome.proposal.units] == [u[0] for u in review_last]
    assert outcome.proposal.units[-1].selected == ("silent-failure-hunter",)


def test_a_verifier_finding_on_an_earlier_batch_is_repaired_with_that_units_cards() -> None:
    # The review unit sits in the second batch and the evidence unit last;
    # code-reviewer also covers discovery, so reusing it on the review is the
    # AR-437 finding the whole-team verification raises after batch three.
    roster = _snapshot(
        *[c for c in _roster().contracts if c.agent_id != "code-reviewer"],
        replace(
            _specialist(
                "code-reviewer",
                artifact="review-report",
                lifecycle="review",
                domain="software-engineering",
                capability="review",
                authority="review",
            ),
            artifact_kinds=("analysis", "review-report"),
            lifecycle_phases=("discovery", "review"),
            capability_ids=("analysis", "review"),
        ),
    )
    selected = {**_SELECTED, "unit-discovery": "code-reviewer"}
    outcome, prompts = _run(
        [
            _rows(["unit-discovery", "unit-implementation"], selected),
            {
                "units": [
                    _rows(["unit-tests"])["units"][0],
                    {
                        "unit_id": "unit-review",
                        "decision": "staff",
                        "ranked_semantic": [
                            _nominee("code-reviewer", 0.99),
                            _nominee("silent-failure-hunter", 0.9, "acceptable"),
                        ],
                    },
                ]
            },
            _rows(["unit-evidence"]),
            {
                "units": [
                    {
                        "unit_id": "unit-review",
                        "decision": "staff",
                        "ranked_semantic": [
                            _nominee("silent-failure-hunter", 0.99),
                            _nominee("code-reviewer", 0.9, "acceptable"),
                        ],
                    }
                ]
            },
        ],
        roster=roster,
    )
    assert outcome.accepted, outcome.abstention_codes
    assert outcome.calls_used == 5
    statuses = [attempt.status for attempt in outcome.attempts if attempt.stage == "recruiter"]
    # The last batch's reply completed a team the verifier refused: recorded
    # rejected with the verifier's row, then one scoped repair.
    assert statuses == ["applied", "applied", "rejected", "applied"]
    rejected = next(a for a in outcome.attempts if a.status == "rejected")
    assert rejected.validation_detail == (
        "workforce staffing verification failures: unit-review=review_reviewer_reused"
    )
    repair_document = _document(prompts[4])
    assert repair_document["recruiter_batch"]["unit_ids"] == ["unit-review"]
    assert [row["unit_id"] for row in repair_document["typed_recall"]] == ["unit-review"]
    assert "silent-failure-hunter" in {c["agent_id"] for c in repair_document["detail_cards"]}
    assert [row["unit_id"] for row in repair_document["recruiter_batch"]["earlier_batches"]] == [
        "unit-discovery",
        "unit-implementation",
        "unit-tests",
        "unit-evidence",
    ]
    assert outcome.proposal.units[3].selected == ("silent-failure-hunter",)


def test_the_budget_widens_the_batches_instead_of_failing_them() -> None:
    # Budget 5: the planner spends one, four calls remain, which afford two
    # batches with a repair each, so three and two units instead of three
    # batches.
    outcome, prompts = _run(
        [
            _rows(["unit-discovery", "unit-implementation", "unit-tests"]),
            _rows(["unit-review", "unit-evidence"]),
        ],
        budget=5,
    )
    assert outcome.accepted
    assert outcome.calls_used == 3
    documents = [_document(prompt) for prompt in prompts[1:]]
    assert [d["recruiter_batch"]["unit_ids"] for d in documents] == [
        ["unit-discovery", "unit-implementation", "unit-tests"],
        ["unit-review", "unit-evidence"],
    ]


def test_a_batch_that_cannot_be_answered_ends_the_stage_with_its_failure() -> None:
    outcome, _ = _run(
        [
            _rows(["unit-discovery", "unit-implementation"]),
            {"units": []},
            {"units": []},
        ]
    )
    assert not outcome.accepted
    assert outcome.status == "inference_invalid"
    statuses = [attempt.status for attempt in outcome.attempts if attempt.stage == "recruiter"]
    assert statuses == ["applied", "rejected", "rejected"]
    assert "unit-tests=missing_work_unit" in outcome.attempts[-1].validation_detail
    assert "unit-evidence" not in outcome.attempts[-1].validation_detail


def test_a_cached_proposal_is_reused_whole() -> None:
    clear_workforce_caches()
    replies = iter(
        (
            _result(_plan()),
            _result(_rows(["unit-discovery", "unit-implementation"])),
            _result(_rows(["unit-tests", "unit-review"])),
            _result(_rows(["unit-evidence"])),
        )
    )

    def invoke(_provider, _prompt, _schema, **_kwargs):
        return next(replies)

    config = _config(mode="balanced", balanced_call_budget=8)
    first = plan_and_staff_workforce(
        _REQUEST, _roster(), config=config, context=_context(), invoker=invoke
    )
    assert first.accepted
    # A second run with the same identity spends no call: both stages hit.
    second = plan_and_staff_workforce(
        _REQUEST, _roster(), config=config, context=_context(), invoker=invoke
    )
    assert second.accepted
    assert second.cache_hits == ("plan", "recruiter")
    assert second.calls_used == 0
