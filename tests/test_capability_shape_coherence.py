"""AR-439 / ADR-0252: a unit's mandatory capabilities are bound to its own shape.

Every recruiter rejection recorded as ``staff_without_safe_team`` since
2026-09-08 was on the capability axis: the verifier made each planner-named
capability a mandatory typed requirement, and when the capability belonged to
another unit shape (``implementation`` on a read-only review, ``analysis`` on
a test-code unit, ``coordination`` on a merge) the only coverers were the
wrong specialists, which the recruiter rightly left out. The unit keeps
every planner-named capability for recall and eligibility; only the
artifact-owned capability, a specialty outside the shape vocabulary and a
declared novelty are typed coverage. These tests pin that split, the
requirements the verifier derives, the detail the applied planner attempt
records, and the closed row both durable receipts project from it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.preflight_failure import project_preflight_provider_attempts
from agency_runtime.core.selector.receipt_projection import (
    PLAN_ADVISORY_DETAIL_PREFIX,
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
    project_nomination_failures,
)
from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.capability_ontology import (
    ARTIFACT_CAPABILITY,
    CORE_CAPABILITY_IDS,
)
from agency_runtime.core.workforce.inference import (
    _advisory_capability_detail,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.intent import COMPACT_INTENT_SYSTEM
from agency_runtime.core.workforce.planning_contracts import WorkUnit
from agency_runtime.core.workforce.routing_projection import _provider_attempts
from agency_runtime.core.workforce.staffing_verifier import (
    _CAPABILITY_RULES,
    _SHAPE_CAPABILITIES,
    advisory_capabilities,
    mandatory_capabilities,
    typed_staffing_coverage_gaps,
    typed_staffing_requirements,
)
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


def _unit(artifact: str, lifecycle: str, authority: str, *capabilities: str) -> WorkUnit:
    return WorkUnit(
        unit_id="unit-shape",
        outcome="Shape probe",
        artifact_kind=artifact,
        lifecycle_phase=lifecycle,
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=tuple(capabilities),
        authority=authority,
        mutation_scope="read_only",
        risks=(),
        trust_boundaries=("repository",),
        claims=(),
        depends_on=(),
        resources=("request",),
        required_tools=("repository-read",),
        platforms=("linux",),
        acceptance_evidence=("evidence",),
        parallelization="unspecified",
    )


def _reviewer() -> Any:
    return _contract(
        "code-reviewer",
        authority="review",
        artifact="review-report",
        lifecycle="review",
        domains=("software-engineering",),
        capabilities=("review",),
    )


# --- the split -----------------------------------------------------------------


def test_the_shape_vocabulary_is_exactly_what_the_typed_fields_decide() -> None:
    # The two readings outside `_CAPABILITY_RULES` that `_supports_planning_capability`
    # still decides from a card's typed fields and identity tokens.
    assert frozenset(_CAPABILITY_RULES) | {"architecture", "risk-analysis"} == _SHAPE_CAPABILITIES
    assert _SHAPE_CAPABILITIES <= CORE_CAPABILITY_IDS
    # Every artifact-owned capability is a shape capability, so "owned" is the
    # one exception the split needs.
    assert set(ARTIFACT_CAPABILITY.values()) <= _SHAPE_CAPABILITIES


@pytest.mark.parametrize(
    ("artifact", "lifecycle", "authority", "named", "mandatory", "advisory"),
    [
        # The four observed shapes: a method of another shape is advisory.
        (
            "review-report",
            "review",
            "review",
            ("review", "implementation"),
            ("review",),
            ("implementation",),
        ),
        ("test-code", "testing", "modify", ("testing", "analysis"), ("testing",), ("analysis",)),
        (
            "implementation-change",
            "implementation",
            "modify",
            ("implementation", "coordination"),
            ("implementation",),
            ("coordination",),
        ),
        ("analysis", "discovery", "advise", ("analysis", "planning"), ("analysis",), ("planning",)),
        # A specialty and a declared novelty stay mandatory beside the owned one.
        (
            "review-report",
            "review",
            "review",
            ("review", "threat-modeling"),
            ("review", "threat-modeling"),
            (),
        ),
        # risk-analysis is read from authority and identity tokens, so it is a
        # shape capability too: a review that names it is not forced onto a
        # risk specialist (the live openclaw shape of 2026-09-11).
        (
            "review-report",
            "review",
            "review",
            ("review", "risk-analysis"),
            ("review",),
            ("risk-analysis",),
        ),
        (
            "implementation-change",
            "implementation",
            "modify",
            ("implementation", "risk-analysis"),
            ("implementation",),
            ("risk-analysis",),
        ),
        (
            "review-report",
            "review",
            "review",
            ("review", "quantum-key-audit"),
            ("review", "quantum-key-audit"),
            (),
        ),
        # Even a second method the shape could carry is advisory: the shape
        # requirements already prove it.
        (
            "review-report",
            "review",
            "review",
            ("review", "verification", "audit"),
            ("review",),
            ("verification", "audit"),
        ),
        (
            "analysis",
            "discovery",
            "advise",
            ("analysis", "investigation"),
            ("analysis",),
            ("investigation",),
        ),
        (
            "plan",
            "planning",
            "plan",
            ("planning", "operations", "simulation"),
            ("planning", "simulation"),
            ("operations",),
        ),
    ],
)
def test_only_the_owned_capability_specialties_and_novelties_are_mandatory(
    artifact: str,
    lifecycle: str,
    authority: str,
    named: tuple[str, ...],
    mandatory: tuple[str, ...],
    advisory: tuple[str, ...],
) -> None:
    unit = _unit(artifact, lifecycle, authority, *named)
    assert mandatory_capabilities(unit) == mandatory
    assert advisory_capabilities(unit) == advisory
    # The unit itself is untouched: every planner-named capability stays on it.
    assert unit.required_capabilities == named


def test_the_verifier_requires_only_the_mandatory_capabilities() -> None:
    unit = _unit("review-report", "review", "review", "review", "implementation", "threat-modeling")
    assert typed_staffing_requirements(unit) == (
        "artifact:review-report",
        "lifecycle:review",
        "capability:review",
        "capability:threat-modeling",
        "authority:review",
    )


def test_a_lone_reviewer_now_covers_a_review_that_named_implementation() -> None:
    # The live shape: the recruiter ranked code-reviewer alone for a review
    # unit whose plan also named implementation, and the gate rejected it.
    unit = _unit("review-report", "review", "review", "review", "implementation")
    gaps = typed_staffing_coverage_gaps(unit, [_reviewer()], _context())
    assert gaps.uncovered == ()


def test_a_specialty_nobody_declares_is_still_a_gap_for_hiring() -> None:
    unit = _unit("review-report", "review", "review", "review", "quantum-key-audit")
    gaps = typed_staffing_coverage_gaps(unit, [_reviewer()], _context())
    assert gaps.uncovered == ("capability:quantum-key-audit",)
    assert gaps.unknown == ("capability:quantum-key-audit",)


# --- the compiler is untouched -------------------------------------------------------


def test_the_compiler_keeps_every_planner_named_capability_on_the_unit() -> None:
    plan = _compile(
        _intent(artifact="review-report", capabilities=["review", "implementation"]),
        request="Review this function and propose how to correct it.",
    )
    assert plan.units[0].required_capabilities == ("review", "implementation")
    assert advisory_capabilities(plan.units[0]) == ("implementation",)


def test_the_older_per_token_drops_still_hold() -> None:
    generic = _compile(_intent(capabilities=["implementation", "design"]))
    assert generic.units[0].required_capabilities == ("implementation",)
    analysis = _compile(_intent(artifact="analysis", capabilities=["analysis", "data-analysis"]))
    assert analysis.units[0].required_capabilities == ("analysis",)


# --- the detail the applied planner attempt records ------------------------------


def _staff(plan: dict[str, Any]) -> Any:
    clear_workforce_caches()
    replies = iter(
        (_result(plan), _result(_NOMINATION), _result({"approved": True, "reason_codes": []}))
    )
    return plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=lambda *args, **kwargs: next(replies),
    )


def test_the_advisory_rows_ride_the_applied_planner_attempt_into_both_receipts() -> None:
    plan = json.loads(json.dumps(_PLAN))
    plan["units"][0]["capability_ids"] = ["planning", "implementation"]
    outcome = _staff(plan)
    assert outcome.accepted
    planner = outcome.attempts[0]
    assert (planner.stage, planner.status) == ("planner", "applied")
    assert planner.validation_detail == PLAN_ADVISORY_DETAIL_PREFIX + f"{_UNIT}=implementation"
    # The unit keeps the capability; the requirement set does not force it.
    assert outcome.plan.units[0].required_capabilities == ("planning", "implementation")
    assert "capability:implementation" not in typed_staffing_requirements(outcome.plan.units[0])
    row = {
        "unit_id": _UNIT,
        "reason_code": "plan_capability_advisory",
        "advisory_capability_ids": "implementation",
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


def test_the_fixture_plan_records_its_own_advisory_operations() -> None:
    # The strict-critic fixture names planning, operations and simulation on
    # a plan unit: planning is owned, simulation a specialty, operations advisory.
    outcome = _staff(_PLAN)
    assert outcome.accepted
    assert outcome.attempts[0].stage == "planner"
    assert outcome.attempts[0].validation_detail == (
        PLAN_ADVISORY_DETAIL_PREFIX + f"{_UNIT}=operations"
    )


def test_a_plan_with_no_advisory_capability_records_no_detail() -> None:
    plan = _compile(_intent(capabilities=["implementation"]))
    assert _advisory_capability_detail(plan) == ""


# --- the closed row ----------------------------------------------------------------


def test_the_wire_form_projects_one_row_per_unit() -> None:
    detail = (
        PLAN_ADVISORY_DETAIL_PREFIX
        + "unit-review=implementation,unit-merge=coordination~operations"
    )
    assert project_nomination_failures(detail) == [
        {
            "unit_id": "unit-review",
            "reason_code": "plan_capability_advisory",
            "advisory_capability_ids": "implementation",
        },
        {
            "unit_id": "unit-merge",
            "reason_code": "plan_capability_advisory",
            "advisory_capability_ids": "coordination~operations",
        },
    ]


@pytest.mark.parametrize(
    "detail",
    [
        PLAN_ADVISORY_DETAIL_PREFIX,
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review",
        PLAN_ADVISORY_DETAIL_PREFIX + "review=implementation",
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=",
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=implementation~implementation",
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=a~b~c~d",
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=Implementation Change",
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=" + "a" * 129,
        PLAN_ADVISORY_DETAIL_PREFIX + "unit-review=implementation,unit-review=coordination",
        PLAN_ADVISORY_DETAIL_PREFIX + ",".join(f"unit-{i}=implementation" for i in range(17)),
    ],
)
def test_a_malformed_wire_form_projects_the_whole_attempt_blank(detail: str) -> None:
    assert project_nomination_failures(detail) == []


def test_an_ontology_length_identifier_is_admitted() -> None:
    long_id = "a" * 128
    assert project_nomination_failures(PLAN_ADVISORY_DETAIL_PREFIX + f"unit-review={long_id}") == [
        {
            "unit_id": "unit-review",
            "reason_code": "plan_capability_advisory",
            "advisory_capability_ids": long_id,
        }
    ]


def test_the_row_is_exactly_its_three_keys_with_the_closed_code() -> None:
    row: dict[str, Any] = {
        "unit_id": "unit-review",
        "reason_code": "plan_capability_advisory",
        "advisory_capability_ids": "implementation",
    }
    assert project_nomination_failures([row]) == [row]
    # The ids are admitted on no other row, and the code needs its ids.
    assert project_nomination_failures([{**row, "reason_code": "missing_work_unit"}]) == []
    assert project_nomination_failures([{**row, "requirement_axis": "capability"}]) == []
    assert (
        project_nomination_failures(
            [{"unit_id": "unit-review", "reason_code": "plan_capability_advisory"}]
        )
        == []
    )


def test_the_planner_is_told_which_methods_are_mandatory() -> None:
    assert "a preference the recruiter weighs" in COMPACT_INTENT_SYSTEM
    assert "a read-only review-report cannot carry implementation" in COMPACT_INTENT_SYSTEM
    # risk-analysis is a shape capability, so the prompt must not cite it as
    # a mandatory specialty.
    assert "such as threat-modeling or simulation" in COMPACT_INTENT_SYSTEM
    assert "specialty such as risk-analysis" not in COMPACT_INTENT_SYSTEM
