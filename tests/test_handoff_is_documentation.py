"""AR-434 / ADR-0250: a handoff that only locates the code is documentation, not a code mutation.

Live on 2026-09-10 the request below read as a code mutation (``create`` plus
``code``), the planner's first plan was rejected for missing implementation
and test units, the repaired plan carried them, and the strict critic vetoed
the team for lacking the lifecycle assurance those units implied. The policy
and the deterministic planner now agree that a request naming a prose
artefact, whose only code tokens are locative and which carries no strong
code verb, is documentation work.
"""

from __future__ import annotations

from agency_runtime.core.workforce.fallback import deterministic_work_plan
from agency_runtime.core.workforce.plan_policy import (
    LOCATIVE_CODE_TOKENS,
    PROSE_ARTIFACT_TOKENS,
    plan_policy_violations,
    planner_acceptance_contract,
    prose_artifact_request,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext
from tests.test_workforce_inference import _context

_OBSERVED = (
    "can you create a handoff, ill let another agent crank on this for a bit, include that "
    "observation, and where we left off and whats next to do, and where the code is and what "
    "branch and anything it needs to start working on this fresh"
)


def _plan(request: str):
    plan, reasons = deterministic_work_plan(request, context=_context())
    assert reasons == ()
    assert plan is not None
    return plan


def _kinds(plan) -> list[str]:
    return [unit.artifact_kind for unit in plan.units]


def test_the_observed_handoff_wording_is_documentation_work() -> None:
    plan = _plan(_OBSERVED)
    assert _kinds(plan) == ["documentation", "review-report"]
    assert plan_policy_violations(_OBSERVED, plan) == ()
    # A code-mutation plan for the same wording is now the wrong shape: the
    # policy asks for the documentation unit, never for implementation or tests.
    code_plan = _plan("Fix the bug in the code and add tests.")
    violations = plan_policy_violations(_OBSERVED, code_plan)
    assert "plan_missing_documentation_change" in violations
    assert "plan_missing_implementation" not in violations
    assert "plan_missing_test_implementation" not in violations
    assert "plan_missing_test_evidence_review" not in violations


def test_a_strong_code_verb_keeps_the_request_a_code_mutation() -> None:
    request = "fix the code and write a handoff note for the next agent"
    plan = _plan(request)
    assert "implementation-change" in _kinds(plan)
    docs_plan = _plan(_OBSERVED)
    assert "plan_missing_implementation" in plan_policy_violations(request, docs_plan)


def test_a_non_locative_code_object_keeps_the_request_a_code_mutation() -> None:
    request = "update the api and write a summary of the change"
    plan = _plan(request)
    assert "implementation-change" in _kinds(plan)
    assert "plan_missing_implementation" in plan_policy_violations(request, _plan(_OBSERVED))


def test_existing_documentation_and_code_classification_is_unchanged() -> None:
    mixed = "update the code and the docs"
    assert "implementation-change" in _kinds(_plan(mixed))
    assert "plan_missing_implementation" in plan_policy_violations(mixed, _plan(_OBSERVED))
    readme = "Rewrite the repository README installation guide and independently review it."
    assert _kinds(_plan(readme)) == ["documentation", "review-report"]
    assert plan_policy_violations(readme, _plan(readme)) == ()


def test_negated_scope_still_applies_before_the_prose_rule() -> None:
    request = "create a handoff; do not modify the code"
    assert _kinds(_plan(request)) == ["documentation", "review-report"]
    assert plan_policy_violations(request, _plan(request)) == ()


def test_the_rule_is_narrow_and_stated_to_the_planner() -> None:
    assert prose_artifact_request({"create", "handoff", "code"}, {"code"})
    assert prose_artifact_request({"update", "notes", "repository"}, {"repository"})
    assert not prose_artifact_request({"create", "handoff", "api"}, {"api"})
    assert not prose_artifact_request({"fix", "handoff", "code"}, {"code"})
    assert not prose_artifact_request({"create", "code"}, {"code"})
    assert not prose_artifact_request({"handoff", "code"}, {"code"})
    assert LOCATIVE_CODE_TOKENS == {"code", "codebase", "repo", "repository"}
    assert "handoff" in PROSE_ARTIFACT_TOKENS and "plan" not in PROSE_ARTIFACT_TOKENS
    contract = planner_acceptance_contract()["documentation_mutation"]
    assert contract["prose_artifacts_are_documentation"] == sorted(PROSE_ARTIFACT_TOKENS)
    assert isinstance(_context(), StaffingContext)
