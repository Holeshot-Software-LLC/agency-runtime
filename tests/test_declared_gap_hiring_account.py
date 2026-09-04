"""AR-393: a declared gap always leaves a hiring account, naming the test it failed.

Measured on the live store on 2026-09-04, across 993 preflight receipts: 99
declared `no_safe_sufficient_team` and 42 of those carried empty
`hiring_reason_codes`. Every one of the 42 carried a staffing code set drawn
entirely from the verifier codes that describe why a gap is real, so these were
exactly the turns the governed hiring path exists for, and they were the ones it
said nothing about.

Two distinct halves produced that silence.

`_all_gap_units` intersected the verifier's unit ids with the plan's units. When
that intersection was empty nothing iterated, `hiring_events` was never set on
the routing projection because it is assigned only when the list is non-empty,
and `preflight_hiring_reason_codes` read the absent key as `[]` -- a receipt
declaring a capability gap and saying nothing whatsoever about hiring,
indistinguishable from a turn where hiring was never relevant.

`_hireable_gap_units` narrowed the gap units three ways and returned only the
survivors, discarding which test each casualty failed. `_complete_gap_hiring_events`
then labelled every casualty `gap_evidence_not_hireable` followed by that unit's
own verifier codes. Only the third of the three tests is self-explaining: in the
other two, every listed code is inside the hireable set, so the evidence printed
on the event disqualified nothing and the thing that actually disqualified the
unit -- a global code, or a missing declaration -- was named nowhere.

These tests pin the three shapes the issue reproduced in process, and the rule
that no event may list codes that all support the opposite conclusion.
"""

from __future__ import annotations

from types import SimpleNamespace

from agency_runtime.core.selector.pipeline import (
    _HIREABLE_GAP_CODES,
    GAP_EVIDENCE_NOT_HIREABLE,
    GAP_GLOBAL_ABSTENTION,
    GAP_HIRE_NOT_ATTEMPTED,
    GAP_NOT_DECLARED_BY_INFERENCE,
    GAP_UNIT_ABSENT_FROM_PLAN,
    _all_gap_units,
    _complete_gap_hiring_events,
    _gap_hiring_verdicts,
    _hireable_gap_units,
)

_GAP = "no_safe_sufficient_team"
_ABSTAINED = "recruiter_abstained"


def _reason(code: str, unit_id: str = "") -> SimpleNamespace:
    return SimpleNamespace(code=code, unit_id=unit_id)


def _outcome(
    *,
    plan_units: tuple[str, ...] | None,
    reasons: tuple[SimpleNamespace, ...],
    declared: tuple[str, ...],
    inference_mode: str = "inferred",
) -> SimpleNamespace:
    plan = (
        None
        if plan_units is None
        else SimpleNamespace(units=tuple(SimpleNamespace(unit_id=u) for u in plan_units))
    )
    return SimpleNamespace(
        plan=plan,
        staffing=SimpleNamespace(abstention_reasons=reasons),
        proposal=SimpleNamespace(
            units=tuple(
                SimpleNamespace(unit_id=u, abstention_reasons=("inference-declared-gap",))
                for u in declared
            )
        ),
        inference_mode=inference_mode,
        attempts=(SimpleNamespace(status="applied"),),
    )


def _events(outcome: SimpleNamespace, *, hiring_allowed: bool = True) -> list[dict]:
    return _complete_gap_hiring_events(
        outcome,
        _all_gap_units(outcome),
        {},
        hiring_allowed=hiring_allowed,
        daily_limit_reached=False,
        max_hires=3,
        workforce_changes=0,
        store_available=True,
    )


def _codes(event: dict) -> tuple[str, ...]:
    return tuple(event["reason_codes"])


# --- shape 1: the decision names a unit the plan does not contain ------------


def test_a_gap_unit_the_plan_does_not_contain_still_gets_an_event() -> None:
    # The leading candidate for the live 42: a repair re-planned the turn and
    # the retained staffing decision still refers to the first plan's unit ids.
    outcome = _outcome(plan_units=(), reasons=(_reason(_GAP, "u1"), _reason(_ABSTAINED, "u1")), declared=("u1",))

    assert _all_gap_units(outcome) == ("u1",)
    assert _hireable_gap_units(outcome) == ()

    events = _events(outcome)
    assert [event["unit_id"] for event in events] == ["u1"]
    assert _codes(events[0]) == (GAP_UNIT_ABSENT_FROM_PLAN,)


def test_an_absent_plan_is_the_same_case_as_an_empty_one() -> None:
    outcome = _outcome(plan_units=None, reasons=(_reason(_GAP, "u1"),), declared=("u1",))

    assert _all_gap_units(outcome) == ("u1",)
    assert _codes(_events(outcome)[0]) == (GAP_UNIT_ABSENT_FROM_PLAN,)


# --- shape 2: the proposal row does not declare the gap ----------------------


def test_a_unit_inference_never_declared_names_that_and_not_its_own_codes() -> None:
    outcome = _outcome(
        plan_units=("u1",),
        reasons=(_reason(_GAP, "u1"), _reason(_ABSTAINED, "u1")),
        declared=(),
    )

    assert _all_gap_units(outcome) == ("u1",)
    assert _hireable_gap_units(outcome) == ()

    codes = _codes(_events(outcome)[0])
    assert codes == (GAP_NOT_DECLARED_BY_INFERENCE,)
    # The old event listed no_safe_sufficient_team and recruiter_abstained here,
    # both inside the hireable set, so it disqualified nothing.
    assert _GAP not in codes
    assert _ABSTAINED not in codes


# --- shape 3: one global code disqualifies every unit on the turn ------------


def test_a_global_code_travels_onto_every_event_it_disqualified() -> None:
    outcome = _outcome(
        plan_units=("u1", "u2"),
        reasons=(
            _reason("selection_confidence_too_low"),
            _reason(_GAP, "u1"),
            _reason(_ABSTAINED, "u1"),
            _reason(_GAP, "u2"),
            _reason(_ABSTAINED, "u2"),
        ),
        declared=("u1", "u2"),
    )

    assert _all_gap_units(outcome) == ("u1", "u2")
    assert _hireable_gap_units(outcome) == ()

    events = _events(outcome)
    assert [event["unit_id"] for event in events] == ["u1", "u2"]
    for event in events:
        # No unit's own evidence explains this outcome, so the code that does
        # is on the event.
        assert _codes(event) == (GAP_GLOBAL_ABSTENTION, "selection_confidence_too_low")


def test_a_global_code_inside_the_hireable_set_disqualifies_nothing() -> None:
    # ADR-0198: roster_coverage_gap is exactly why the gap is real.
    outcome = _outcome(
        plan_units=("u1",),
        reasons=(_reason("roster_coverage_gap"), _reason(_GAP, "u1"), _reason(_ABSTAINED, "u1")),
        declared=("u1",),
    )

    assert _hireable_gap_units(outcome) == ("u1",)


# --- the label means what it says --------------------------------------------


def test_gap_evidence_not_hireable_appears_only_with_a_code_outside_the_set() -> None:
    outcome = _outcome(
        plan_units=("u1",),
        reasons=(
            _reason(_GAP, "u1"),
            _reason(_ABSTAINED, "u1"),
            _reason("forbidden_agent_selected", "u1"),
        ),
        declared=("u1",),
    )

    codes = _codes(_events(outcome)[0])
    assert codes[0] == GAP_EVIDENCE_NOT_HIREABLE
    assert "forbidden_agent_selected" in codes
    assert set(codes) - {GAP_EVIDENCE_NOT_HIREABLE} - _HIREABLE_GAP_CODES


def test_no_event_lists_only_codes_that_support_the_opposite_conclusion() -> None:
    """The rule the three shapes above share, stated once over all of them."""

    shapes = (
        _outcome(plan_units=(), reasons=(_reason(_GAP, "u1"),), declared=("u1",)),
        _outcome(plan_units=("u1",), reasons=(_reason(_GAP, "u1"), _reason(_ABSTAINED, "u1")), declared=()),
        _outcome(
            plan_units=("u1",),
            reasons=(_reason("selection_confidence_too_low"), _reason(_GAP, "u1")),
            declared=("u1",),
        ),
        _outcome(
            plan_units=("u1",),
            reasons=(_reason(_GAP, "u1"), _reason("forbidden_agent_selected", "u1")),
            declared=("u1",),
        ),
    )
    for outcome in shapes:
        for event in _events(outcome):
            codes = set(_codes(event))
            assert codes, "a declared gap may never be dropped silently"
            assert codes - _HIREABLE_GAP_CODES, (
                "every code on this event is one that says the gap is real, "
                "so nothing on it explains why the unit was not hired"
            )


# --- a hireable unit is not labelled with the opposite verdict ---------------


def test_a_still_hireable_unit_is_not_told_its_evidence_disqualified_it() -> None:
    # Reached with the unit in the hireable set and no limit met. The old code
    # here was gap_evidence_not_hireable, contradicting the tuple it had just
    # been computed from.
    outcome = _outcome(
        plan_units=("u1",),
        reasons=(_reason(_GAP, "u1"), _reason(_ABSTAINED, "u1")),
        declared=("u1",),
    )
    assert _hireable_gap_units(outcome) == ("u1",)

    codes = _codes(_events(outcome)[0])
    assert codes[0] == GAP_HIRE_NOT_ATTEMPTED
    assert GAP_EVIDENCE_NOT_HIREABLE not in codes


def test_hiring_not_allowed_still_reports_per_unit() -> None:
    outcome = _outcome(
        plan_units=("u1",),
        reasons=(_reason(_GAP, "u1"),),
        declared=("u1",),
        inference_mode="deterministic",
    )

    codes = _codes(_events(outcome, hiring_allowed=False)[0])
    assert codes == ("hiring_requires_inferred_gap",)


# --- the verdict map is the single source both callers read ------------------


def test_the_survivors_are_exactly_the_units_with_no_disqualifier() -> None:
    outcome = _outcome(
        plan_units=("u1", "u2", "u3"),
        reasons=(
            _reason(_GAP, "u1"),
            _reason(_GAP, "u2"),
            _reason("forbidden_agent_selected", "u2"),
            _reason(_GAP, "u3"),
        ),
        declared=("u1", "u2"),
    )
    verdicts = _gap_hiring_verdicts(outcome)

    assert set(verdicts) == {"u1", "u2", "u3"}
    assert verdicts["u1"] == ()
    assert verdicts["u2"][0] == GAP_EVIDENCE_NOT_HIREABLE
    assert verdicts["u3"] == (GAP_NOT_DECLARED_BY_INFERENCE,)
    assert _hireable_gap_units(outcome) == ("u1",)
    # Plan order, so a receipt reads in the order the turn was planned.
    assert _all_gap_units(outcome) == ("u1", "u2", "u3")
