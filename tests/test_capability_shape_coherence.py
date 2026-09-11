"""AR-439 / ADR-0252: a unit's mandatory capabilities are bound to its own shape.

Every terminal ``staff_without_safe_team`` since 2026-09-08 was on the
capability axis: the compiler made each planner-named capability a mandatory
typed requirement, and when the capability belonged to another unit shape
(``implementation`` on a read-only review, ``analysis`` on a test-code unit,
``coordination`` on a merge) the only coverers were the wrong specialists,
which the recruiter rightly left out. These tests pin the shape rule, what
the compiler keeps and drops, the demotion the applied planner attempt
records, and the closed row both durable receipts project from it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
from agency_runtime.core.selector.receipt_projection import (
    PLAN_DEMOTION_DETAIL_PREFIX,
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
    project_nomination_failures,
)
from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.inference import (
    _capability_demotion_detail,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.intent import COMPACT_INTENT_SYSTEM, compile_intent_plan
from agency_runtime.core.workforce.routing_projection import _provider_attempts
from agency_runtime.core.workforce.staffing_verifier import planning_capability_coherent
from tests.test_strict_critic_doctrine import (
    _NOMINATION,
    _PLAN,
    _UNIT,
    _config,
    _context,
    _contract,
    _desktop_engineer,
    _result,
    _routing,
    _snapshot,
)
from tests.test_workforce_intent import _compile, _intent

_KNOWN_CAPABILITIES = (
    "analysis",
    "architecture",
    "audit",
    "coordination",
    "design",
    "documentation",
    "implementation",
    "investigation",
    "operations",
    "planning",
    "review",
    "simulation",
    "testing",
    "threat-modeling",
    "verification",
)


def _compile_known(value: dict[str, object], *, request: str):
    return compile_intent_plan(
        value,
        request=request,
        context=_context(),
        known_domains=("operations", "security", "software-engineering", "quality-assurance"),
        known_stacks=("python",),
        known_capability_ids=_KNOWN_CAPABILITIES,
    )


# --- the shape rule ----------------------------------------------------------


@pytest.mark.parametrize(
    ("capability", "artifact", "lifecycle", "authority", "coherent"),
    [
        # The four observed shapes: a method that belongs to another unit.
        ("implementation", "review-report", "review", "review", False),
        ("analysis", "test-code", "testing", "modify", False),
        ("coordination", "implementation-change", "implementation", "modify", False),
        ("planning", "analysis", "discovery", "advise", False),
        # Methods a card of the unit's own shape carries under the rules.
        ("verification", "review-report", "review", "review", True),
        ("audit", "review-report", "review", "review", True),
        ("investigation", "analysis", "discovery", "advise", True),
        ("testing", "test-evidence", "testing", "review", True),
        ("review", "test-evidence", "testing", "review", True),
        ("architecture", "architecture-record", "design", "plan", True),
        ("design", "plan", "planning", "plan", True),
        # A specialty outside the shape vocabulary is coherent on any shape,
        # including one whose heuristic reading is authority-keyed.
        ("threat-modeling", "review-report", "review", "review", True),
        ("simulation", "plan", "planning", "plan", True),
        ("risk-analysis", "implementation-change", "implementation", "modify", True),
        # Audit, review and verification belong to the review and test-evidence
        # shapes; an analysis unit keeps analysis and investigation.
        ("audit", "analysis", "discovery", "advise", False),
        ("review", "analysis", "discovery", "advise", False),
        ("verification", "analysis", "discovery", "advise", False),
        ("analysis", "review-report", "review", "review", True),
        # Documentation is owned by the documentation shape alone.
        ("documentation", "review-report", "review", "review", False),
        ("documentation", "documentation", "documentation", "modify", True),
    ],
)
def test_the_rule_reads_the_unit_shape_the_verifier_reads(
    capability: str, artifact: str, lifecycle: str, authority: str, coherent: bool
) -> None:
    assert (
        planning_capability_coherent(
            capability, artifact_kind=artifact, lifecycle_phase=lifecycle, authority=authority
        )
        is coherent
    )


def test_a_domain_can_make_operations_coherent_on_a_check() -> None:
    kwargs = {"artifact_kind": "test-evidence", "lifecycle_phase": "testing", "authority": "review"}
    assert not planning_capability_coherent("operations", **kwargs)
    assert planning_capability_coherent("operations", domains=("operations",), **kwargs)


def test_an_empty_capability_is_never_coherent() -> None:
    assert not planning_capability_coherent(
        "", artifact_kind="plan", lifecycle_phase="planning", authority="plan"
    )


# --- what the compiler keeps and drops ------------------------------------------


def test_the_compiler_drops_a_method_of_another_shape_from_each_observed_unit() -> None:
    review = _compile_known(
        _intent(
            artifact="review-report",
            domains=["software-engineering"],
            stacks=[],
            capabilities=["review", "implementation"],
        ),
        request="Review this function and propose how to correct it.",
    )
    assert review.units[0].required_capabilities == ("review",)

    tests = _compile_known(
        _intent(
            artifact="test-code",
            domains=["quality-assurance"],
            stacks=[],
            capabilities=["testing", "analysis"],
        ),
        request="Write the tests for the average function.",
    )
    assert tests.units[0].required_capabilities == ("testing",)

    merge = _compile_known(
        _intent(
            artifact="implementation-change",
            domains=["operations"],
            stacks=[],
            capabilities=["implementation", "coordination"],
        ),
        request="Merge every local branch into main and push.",
    )
    assert merge.units[0].required_capabilities == ("implementation",)

    analysis = _compile_known(
        _intent(
            artifact="analysis",
            domains=["software-engineering"],
            stacks=[],
            capabilities=["analysis", "planning"],
        ),
        request="Map the relevant code paths and say what to do next.",
    )
    assert analysis.units[0].required_capabilities == ("analysis",)


def test_the_compiler_keeps_a_coherent_method_a_specialty_and_a_declared_novelty() -> None:
    review = _compile_known(
        _intent(
            artifact="review-report",
            domains=["security"],
            stacks=[],
            capabilities=["review", "verification", "threat-modeling"],
        ),
        request="Review the authentication service for security defects.",
    )
    assert review.units[0].required_capabilities == ("review", "verification", "threat-modeling")

    incident = _compile_known(
        _intent(
            artifact="analysis",
            domains=["security"],
            stacks=[],
            capabilities=["analysis", "investigation"],
        ),
        request="Investigate the incident and reconstruct the breach timeline.",
    )
    assert incident.units[0].required_capabilities == ("analysis", "investigation")

    novel = _compile_known(
        _intent(
            artifact="review-report",
            domains=["security"],
            stacks=[],
            capabilities=["review"],
            novel="quantum-key-audit",
        ),
        request="Audit the quantum key exchange.",
    )
    assert novel.units[0].required_capabilities == ("review", "quantum-key-audit")


def test_the_older_per_token_drops_still_hold() -> None:
    # The shape rule sits beside the existing compiler drops, not instead of them.
    assert _compile(_intent(capabilities=["implementation", "design"])).units[
        0
    ].required_capabilities == ("implementation",)
    assert _compile(_intent(artifact="analysis", capabilities=["analysis", "data-analysis"])).units[
        0
    ].required_capabilities == ("analysis",)


# --- the demotion the compiler records --------------------------------------------


def test_the_sink_names_every_known_capability_the_compiler_dropped() -> None:
    sink: list[tuple[str, tuple[str, ...]]] = [("stale", ("stale",))]
    compile_intent_plan(
        _intent(
            artifact="review-report",
            domains=["software-engineering"],
            stacks=[],
            capabilities=["review", "implementation", "coordination"],
        ),
        request="Review this function and propose how to correct it.",
        context=_context(),
        known_domains=("software-engineering",),
        known_stacks=(),
        known_capability_ids=_KNOWN_CAPABILITIES,
        demotion_sink=sink,
    )
    assert sink == [("unit-primary", ("implementation", "coordination"))]


def test_the_sink_is_emptied_when_nothing_is_dropped_and_ignores_misplaced_labels() -> None:
    sink: list[tuple[str, tuple[str, ...]]] = [("stale", ("stale",))]
    compile_intent_plan(
        _intent(
            artifact="review-report",
            domains=["security"],
            stacks=[],
            capabilities=["review", "security"],
        ),
        request="Review the service for security defects.",
        context=_context(),
        known_domains=("security",),
        known_stacks=(),
        known_capability_ids=_KNOWN_CAPABILITIES,
        demotion_sink=sink,
    )
    # ``security`` was a domain misplaced on the capability axis, never a capability.
    assert sink == []


def test_the_demotion_rides_the_applied_planner_attempt_into_both_receipts() -> None:
    clear_workforce_caches()
    plan = json.loads(json.dumps(_PLAN))
    plan["units"][0]["capability_ids"] = ["planning", "implementation"]
    replies = iter(
        (_result(plan), _result(_NOMINATION), _result({"approved": True, "reason_codes": []}))
    )

    def invoke(*args, **_kwargs):
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    assert outcome.accepted
    planner = outcome.attempts[0]
    assert (planner.stage, planner.status) == ("planner", "applied")
    assert planner.validation_detail == PLAN_DEMOTION_DETAIL_PREFIX + f"{_UNIT}=implementation"
    assert outcome.plan.units[0].required_capabilities == ("planning",)
    row = {
        "unit_id": _UNIT,
        "reason_code": "plan_capability_demoted",
        "demoted_capability_ids": "implementation",
    }
    # Both durable receipts read the same attempt projection ...
    attempts = _provider_attempts(outcome)
    receipt = project_durable_routing_receipt({**_routing(outcome), "provider_attempts": attempts})
    planner_attempts = [
        a for a in receipt["inference"]["provider_attempts"] if a["stage"] == "planner"
    ]
    assert planner_attempts and planner_attempts[0]["validation_failures"] == [row]
    assert normalize_durable_routing_receipt(receipt) == receipt
    # ... and the terminal preflight-failure receipt projects the same row.
    projected = project_preflight_provider_attempts(attempts)
    assert projected is not None
    assert projected[0]["stage"] == "planner"
    assert projected[0]["validation_failures"] == [row]


def test_a_plan_without_a_drop_records_no_detail() -> None:
    clear_workforce_caches()
    replies = iter(
        (_result(_PLAN), _result(_NOMINATION), _result({"approved": True, "reason_codes": []}))
    )
    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=lambda *args, **kwargs: next(replies),
    )
    assert outcome.accepted
    assert outcome.attempts[0].stage == "planner"
    assert outcome.attempts[0].validation_detail == ""


# --- the closed row ----------------------------------------------------------------


def test_the_wire_form_projects_one_row_per_unit() -> None:
    detail = _capability_demotion_detail(
        [("unit-review", ("implementation",)), ("unit-merge", ("coordination", "operations"))]
    )
    assert detail == (
        PLAN_DEMOTION_DETAIL_PREFIX
        + "unit-review=implementation,unit-merge=coordination~operations"
    )
    assert project_nomination_failures(detail) == [
        {
            "unit_id": "unit-review",
            "reason_code": "plan_capability_demoted",
            "demoted_capability_ids": "implementation",
        },
        {
            "unit_id": "unit-merge",
            "reason_code": "plan_capability_demoted",
            "demoted_capability_ids": "coordination~operations",
        },
    ]


@pytest.mark.parametrize(
    "detail",
    [
        PLAN_DEMOTION_DETAIL_PREFIX,
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review",
        PLAN_DEMOTION_DETAIL_PREFIX + "review=implementation",
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review=",
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review=implementation~implementation",
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review=a~b~c~d",
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review=Implementation Change",
        PLAN_DEMOTION_DETAIL_PREFIX + "unit-review=implementation,unit-review=coordination",
        PLAN_DEMOTION_DETAIL_PREFIX + ",".join(f"unit-{i}=implementation" for i in range(17)),
    ],
)
def test_a_malformed_wire_form_projects_the_whole_attempt_blank(detail: str) -> None:
    assert project_nomination_failures(detail) == []


def test_the_row_is_exactly_its_three_keys_with_the_closed_code() -> None:
    row: dict[str, Any] = {
        "unit_id": "unit-review",
        "reason_code": "plan_capability_demoted",
        "demoted_capability_ids": "implementation",
    }
    assert project_nomination_failures([row]) == [row]
    # The ids are admitted on no other row, and the code needs its ids.
    assert project_nomination_failures([{**row, "reason_code": "missing_work_unit"}]) == []
    assert project_nomination_failures([{**row, "requirement_axis": "capability"}]) == []
    assert (
        project_nomination_failures(
            [{"unit_id": "unit-review", "reason_code": "plan_capability_demoted"}]
        )
        == []
    )


def test_the_planner_is_told_which_methods_a_shape_carries() -> None:
    assert "a read-only review-report cannot carry implementation" in COMPACT_INTENT_SYSTEM
    assert "dropped from the unit and recorded" in COMPACT_INTENT_SYSTEM
