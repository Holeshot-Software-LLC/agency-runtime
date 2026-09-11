"""AR-438 / ADR-0251: an ordinary ask is capped at two planned units.

Measured on the 2026-09-08..11 population, recruiter omissions and coverage
forcing concentrated in three-to-ten-unit plans, and the review request that
started the investigation drew two to four units per host. The ceiling applies
to every request the plan policy does not itself expand.
"""

from __future__ import annotations

from types import SimpleNamespace

from agency_runtime.core.selector.pipeline import _workforce_planning_options
from agency_runtime.core.workforce.plan_policy import (
    ORDINARY_UNIT_CEILING,
    planning_unit_ceiling,
    request_profile,
)

_REVIEW = (
    "Review this Python function: def average(values): return sum(values) // len(values). "
    "Requirements: return the arithmetic mean for nonempty numeric sequences, including "
    "fractional results, and raise ValueError for empty input. Identify the defects using "
    "[1.0, 2.0] and []. Propose how to correct them, but do not write the corrected function yet."
)


def test_ordinary_asks_are_capped_at_two_units() -> None:
    assert ORDINARY_UNIT_CEILING == 2
    for request in (
        _REVIEW,
        "what does the finalizer do when the store is locked?",
        "merge everything to remote main and pause for a bit, need to conserve tokens",
        "can you create a handoff for the next agent and say where the code is",
        "Rewrite the repository README installation guide and independently review it.",
        "install this: https://example.test/tool and confirm it is installed",
    ):
        assert planning_unit_ceiling(request) == 2, request


def test_requests_the_policy_expands_keep_their_shape() -> None:
    for request in (
        "Fix the bug in the code and add tests.",
        "Review authentication security in this repository code.",
        "Map the codebase paths that handle uploads.",
        "Implement the DO-178C assurance review for this flight software module.",
    ):
        profile = request_profile(request)
        assert profile.shape_expanding, request
        assert planning_unit_ceiling(request) is None, request


def test_negated_scope_is_honoured_before_the_ceiling() -> None:
    assert planning_unit_ceiling("Explain the parser. Do not fix the code.") == 2


def test_a_change_verb_beside_a_code_noun_leaves_the_planner_free() -> None:
    # Review of the first draft: the policy's verb vocabulary is thin, so a
    # wording it under-reads must not lose units. Any change verb beside a
    # code noun lifts the ceiling; the policy still demands nothing.
    for request in (
        "Migrate the service to async and keep the tests green.",
        "Delete the dead code in the parser and keep the tests green.",
        "Patch the vulnerability in the auth service.",
        "Modify the api handler and write tests for it.",
    ):
        assert not request_profile(request).shape_expanding, request
        assert planning_unit_ceiling(request) is None, request
    # Without a code noun the ask stays ordinary and fits in two units.
    assert planning_unit_ceiling("Please modify the parser and write tests for it.") == 2


def test_planning_options_apply_the_ceiling_only_to_ordinary_asks() -> None:
    decision = SimpleNamespace(execution_decision_required=True)
    inquiry = SimpleNamespace(execution_decision_required=False)
    assert _workforce_planning_options(decision, activation_canary=False, request_text=_REVIEW) == {
        "max_planned_units": 2
    }
    assert (
        _workforce_planning_options(
            decision, activation_canary=False, request_text="Fix the bug in the code and add tests."
        )
        == {}
    )
    # The special contracts still win.
    assert (
        _workforce_planning_options(decision, activation_canary=True, request_text=_REVIEW)[
            "max_planned_units"
        ]
        == 1
    )
    assert _workforce_planning_options(inquiry, activation_canary=False, request_text=_REVIEW) == {
        "max_planned_units": 1,
        "required_planned_artifact_kind": "analysis",
    }
    assert _workforce_planning_options(decision, activation_canary=False) == {}


def test_the_route_passes_the_request_text_to_the_planning_options() -> None:
    # Review of the first draft: the whole live effect is one keyword argument
    # at the route; pin it so a refactor cannot drop it with a green suite.
    import inspect

    from agency_runtime.core.selector import pipeline

    source = inspect.getsource(pipeline)
    assert "request_text=request.user_message," in source
    assert source.count("_workforce_planning_options(") == 2
