"""AR-434 / ADR-0250: a handoff that only locates the code is documentation, not a code mutation.

Live on 2026-09-10 the request below read as a code mutation (``create`` plus
``code``), the planner's first plan was rejected for missing implementation
and test units, the repaired plan carried them, and the strict critic vetoed
the team for lacking the lifecycle assurance those units implied. The policy
and the deterministic planner now agree that a request naming a prose
artefact as the object of every change verb, whose only code nouns are
locative and which carries no strong code verb, is documentation work.
"""

from __future__ import annotations

from agency_runtime.core.workforce.fallback import deterministic_work_plan
from agency_runtime.core.workforce.plan_policy import (
    CODE_NOUN_TOKENS,
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
    assert prose_artifact_request("create a handoff and say where the code is")
    assert prose_artifact_request("update the notes for this repository")
    assert prose_artifact_request("create a handoff for the python code")
    assert not prose_artifact_request("create a handoff for the api")
    assert not prose_artifact_request("create a handoff for the patch")
    assert not prose_artifact_request("fix the code and write a handoff")
    assert not prose_artifact_request("create the code")
    assert not prose_artifact_request("the handoff mentions the code")
    assert {"code", "codebase", "repo", "repository"} == LOCATIVE_CODE_TOKENS
    assert {"async", "codebase", "patch"} <= CODE_NOUN_TOKENS
    assert "handoff" in PROSE_ARTIFACT_TOKENS and "plan" not in PROSE_ARTIFACT_TOKENS
    contract = planner_acceptance_contract()["documentation_mutation"]
    assert contract["prose_artifacts_are_documentation"] == sorted(PROSE_ARTIFACT_TOKENS)
    assert "object" in contract["prose_artifacts_are_documentation_only_when"]
    assert isinstance(_context(), StaffingContext)


_CHANGE_VERB_WITH_A_NOTE = (
    "update the auth code and add a note about the new flow",
    "update the credential handling in the code and add a note",
    "update the code and ship it, then write a handoff note",
    "update the code and write a handoff and add tests",
    "edit the code and leave a note",
    "update the python code and write a handoff note for the next agent",
)


def test_a_change_verb_that_takes_the_code_keeps_the_code_shape() -> None:
    # Review of the first draft: weak verbs beside the word "note" must not
    # turn an auth or credential change into documentation work. Every one of
    # these keeps its implementation, tests and reviews.
    for request in _CHANGE_VERB_WITH_A_NOTE:
        assert not prose_artifact_request(request), request
        plan = _plan(request)
        assert "implementation-change" in _kinds(plan), request
        assert plan_policy_violations(request, plan) == (), request
        assert "plan_missing_implementation" in plan_policy_violations(request, _plan(_OBSERVED))
    assert "review-report" in _kinds(
        _plan("update the auth code and add a note about the new flow")
    )


def test_the_policy_and_the_deterministic_planner_agree_on_every_wording() -> None:
    # AR-331 invariant extended to the prose-artefact region, to the code
    # nouns only the planner used to know (patch, async, a language), and to
    # the AR-415 disclaimer corner where the two negation strippers must run
    # in the same order for both readers (review of the second draft).
    for request in (
        _OBSERVED,
        "create a handoff for the python code",
        "create a handoff for the patch",
        "make the async code path faster and write a summary",
        "this is not a request to update the code without tests, create a handoff",
        "I am not asking you to change the code without a review, create a handoff",
        *_CHANGE_VERB_WITH_A_NOTE,
        *_PROSE_NOUN_AS_MODIFIER,
    ):
        plan = _plan(request)
        assert plan_policy_violations(request, plan) == (), request


_PROSE_NOUN_AS_MODIFIER = (
    "add a summary field to the code",
    "update the notes column in the repo",
    "create a memo parser in the repo",
    "add a handoff endpoint to the code",
    "update the summary code and the tests",
)


def test_a_prose_noun_used_as_a_modifier_is_not_the_verbs_object() -> None:
    # Review of the second draft: "add a summary field" adds a field, not a
    # summary; the prose noun must end its phrase to count as the object.
    for request in _PROSE_NOUN_AS_MODIFIER:
        assert not prose_artifact_request(request), request
        assert "implementation-change" in _kinds(_plan(request)), request
    assert prose_artifact_request("create a handoff, then ping me")
    assert prose_artifact_request("create a summary covering where the code is")
    assert prose_artifact_request("add a note about the new flow to the repo")
