"""AR-374: a planned unit may only require tools this host has proven.

A unit's ``required_tools`` are derived from its ``artifact_kind`` by
``intent._required_tools``; the compact planner never authors them. Until this
rule nothing checked the derived result against the host, and the cost of
skipping that check is disproportionate: eligibility on
this axis is unit-scoped, so one unproven tool fails ``unit.required_tools <=
context.available_tools`` against *every* worker at once. Staffing then
abstains with ``no_safe_sufficient_team`` and the receipt carries
``agent_tools_missing``, which reads as a roster problem — the misdiagnosis
AR-374 was originally filed on.

Rejecting the plan instead routes it into the existing planner repair loop with
a named code, so the planner gets one chance to author a plan this host can
actually staff.
"""

from __future__ import annotations

from agency_runtime.core.workforce.plan_policy import (
    PLAN_POLICY_VIOLATION_CODES,
    plan_policy_repair_guidance,
    plan_policy_violations,
)
from agency_runtime.core.workforce.planning_contracts import WorkUnit, WorkUnitPlan

_CODE = "plan_unit_required_tools_unproven"
_PROVEN = frozenset({"repository-read", "shell-execution", "test-execution"})
_REQUEST = "Install the tool and verify it works."


def _unit(unit_id: str, *, required_tools: tuple[str, ...]) -> WorkUnit:
    return WorkUnit(
        unit_id=unit_id,
        outcome="Install the tool",
        artifact_kind="analysis",
        lifecycle_phase="discovery",
        domains=("software-engineering",),
        languages=(),
        frameworks=(),
        required_capabilities=("analysis",),
        authority="advise",
        mutation_scope="none",
        risks=(),
        trust_boundaries=(),
        claims=(),
        depends_on=(),
        resources=(),
        required_tools=required_tools,
        platforms=("linux",),
        acceptance_evidence=("The tool runs",),
        parallelization="sequential",
    )


def _plan(*units: WorkUnit) -> WorkUnitPlan:
    return WorkUnitPlan(
        schema_version=1,
        request_summary="Install the tool",
        units=units,
        plan_hash="sha256:" + "c" * 64,
    )


def test_a_unit_inside_the_proven_set_is_accepted() -> None:
    plan = _plan(_unit("unit-install", required_tools=("repository-read", "test-execution")))

    assert plan_policy_violations(_REQUEST, plan, available_tools=_PROVEN) == ()


def test_a_unit_demanding_an_unproven_tool_is_rejected() -> None:
    plan = _plan(_unit("unit-install", required_tools=("repository-read", "ci-runner")))

    assert _CODE in plan_policy_violations(_REQUEST, plan, available_tools=_PROVEN)


def test_only_the_offending_unit_needs_to_be_wrong() -> None:
    plan = _plan(
        _unit("unit-one", required_tools=("repository-read",)),
        _unit("unit-two", required_tools=("browser-interaction",)),
    )

    assert _CODE in plan_policy_violations(_REQUEST, plan, available_tools=_PROVEN)


def test_an_indivisible_plan_is_still_held_to_the_host_contract() -> None:
    """The tools invariant is topology-independent, unlike the completeness rules."""

    plan = _plan(_unit("unit-install", required_tools=("ci-runner",)))

    violations = plan_policy_violations(
        _REQUEST, plan, available_tools=_PROVEN, explicit_indivisible_unit=True
    )

    assert _CODE in violations


def test_an_unproven_host_defers_to_the_staffing_gate() -> None:
    """An empty proven set means the host proved nothing, not that it can do nothing."""

    plan = _plan(_unit("unit-install", required_tools=("ci-runner",)))

    assert plan_policy_violations(_REQUEST, plan, available_tools=frozenset()) == ()
    assert plan_policy_violations(_REQUEST, plan) == ()


def test_the_rejection_is_repairable_by_the_planner() -> None:
    """A code with no repair guidance would fail the plan without telling it why."""

    assert _CODE in PLAN_POLICY_VIOLATION_CODES

    guidance = {
        row["code"]: row["required_correction"] for row in plan_policy_repair_guidance((_CODE,))
    }

    # The planner authors artifact_kind, never required_tools (those are derived
    # by intent._required_tools), so guidance naming required_tools is unactionable.
    assert "artifact_kind" in guidance[_CODE]
