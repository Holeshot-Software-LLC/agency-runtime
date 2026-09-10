"""AR-433 / ADR-0246: a wrong-neighbour veto names its neighbour, and the runtime checks it.

Between 2026-09-08 and 2026-09-10 the strict critic vetoed 30 turns across
five hosts and used ``wrong-neighbor-selection`` on 27 of them; not one
durable receipt could say which card the critic preferred, because the
critic's schema carried codes alone. The contract now requires a
``wrong_neighbors`` pointer beside that code, the runtime verifies the
pointer against the eligible neighbourhood it showed the critic (ADR-0205),
an unverifiable claim gets one bounded repair and then fails the stage as a
contract failure rather than a veto, and a verified pointer rides the applied
critic attempt into both durable receipts.
"""

from __future__ import annotations

import json
from typing import Any

from agency_runtime.core.preflight_failure import (
    preflight_staffing_reason_codes,
    project_preflight_provider_attempts,
)
from agency_runtime.core.selector.receipt_projection import (
    CRITIC_POINTER_DETAIL_PREFIX,
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
    project_nomination_failures,
)
from agency_runtime.core.workforce.cache import clear_workforce_caches
from agency_runtime.core.workforce.inference import (
    CRITIC_RESPONSE_SCHEMA,
    MAX_CRITIC_WRONG_NEIGHBOR_POINTERS,
    WrongNeighborPointer,
    plan_and_staff_workforce,
)
from agency_runtime.core.workforce.routing_projection import project_workforce_routing
from agency_runtime.core.workforce.staffing_verifier import AbstentionReason
from tests.test_strict_critic_doctrine import (
    _NEIGHBOUR,
    _NOMINATION,
    _PLAN,
    _POINTER,
    _UNIT,
    _config,
    _context,
    _contract,
    _desktop_engineer,
    _result,
    _routing,
    _run,
    _run_neighbourhood,
    _snapshot,
)

_VETO = {"approved": False, "reason_codes": ["wrong-neighbor-selection"]}
_APPROVAL = {"approved": True, "reason_codes": []}


def _run_replies(*critic_replies: dict[str, Any]) -> tuple[Any, list[str]]:
    """Drive the neighbourhood snapshot with a sequence of critic replies.

    Returns the outcome and the raw prompt texts so a repair prompt's runtime
    feedback can be read exactly as the critic received it.
    """

    # Plan and recruiter replies are cached per request within a process, and
    # several checks below run this same request more than once in one test.
    clear_workforce_caches()
    replies = iter((_result(_PLAN), _result(_NOMINATION), *(_result(r) for r in critic_replies)))
    prompts: list[str] = []

    def invoke(*args, **_kwargs):
        prompts.append(str(args[1]))
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _contract(_NEIGHBOUR), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    return outcome, prompts


def _feedback(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.split("\n\n[RUNTIME VALIDATION FEEDBACK]\n", 1)[1])


def test_the_schema_contract_and_prompt_require_a_verifiable_pointer() -> None:
    pointer = CRITIC_RESPONSE_SCHEMA["properties"]["wrong_neighbors"]
    assert pointer["maxItems"] == MAX_CRITIC_WRONG_NEIGHBOR_POINTERS == 8
    assert pointer["items"]["required"] == ["unit_id", "selected_agent_id", "neighbor_agent_id"]
    assert pointer["items"]["additionalProperties"] is False
    # The pointer is optional at the schema level: every other ground omits it.
    assert CRITIC_RESPONSE_SCHEMA["required"] == ["approved", "reason_codes"]

    outcome, prompts = _run_neighbourhood(_APPROVAL)
    assert outcome.accepted
    contract = prompts[2]["critic_contract"]
    assert contract["wrong_neighbor_pointer_required"] is True
    assert contract["wrong_neighbor_pointer_fields"] == [
        "unit_id",
        "selected_agent_id",
        "neighbor_agent_id",
    ]
    assert contract["wrong_neighbor_pointer_verified_by_runtime"] is True
    neighbourhood = prompts[2]["eligible_neighbourhood"][_UNIT]
    assert neighbourhood["eligible_candidate_ids"] == [_NEIGHBOUR, "operations-manager"]
    assert neighbourhood["selected_are_whole_neighbourhood"] is False


def test_a_verified_pointer_keeps_the_veto_and_reaches_both_durable_receipts() -> None:
    outcome, _ = _run_neighbourhood({**_VETO, "wrong_neighbors": [_POINTER]})

    assert not outcome.accepted
    assert outcome.status == "inference_invalid"
    assert outcome.abstention_codes == (
        "inference_invalid",
        "staffing_critic_rejected",
        "wrong-neighbor-selection",
    )
    assert outcome.staffing.abstention_reasons == (
        AbstentionReason("staffing_critic_rejected"),
        AbstentionReason("critic_wrong_neighbor_selection"),
    )
    critic = outcome.attempts[-1]
    assert (critic.stage, critic.status) == ("critic", "applied")
    assert critic.validation_detail == (
        CRITIC_POINTER_DETAIL_PREFIX + f"{_UNIT}=operations-manager>{_NEIGHBOUR}"
    )
    row = {
        "unit_id": _UNIT,
        "reason_code": "critic_wrong_neighbor_selection",
        "selected_agent_id": "operations-manager",
        "neighbor_agent_id": _NEIGHBOUR,
    }
    # The routing receipt projects the pointer row on the critic attempt ...
    routing = project_workforce_routing(
        outcome,
        [],
        request="Put this editor on my machine.",
        roster_count=3,
        contract_fingerprint="c" * 64,
    )
    receipt = project_durable_routing_receipt({**_routing(outcome), **routing})
    critic_attempts = [
        a for a in receipt["inference"]["provider_attempts"] if a["stage"] == "critic"
    ]
    assert critic_attempts and critic_attempts[-1]["validation_failures"] == [row]
    assert normalize_durable_routing_receipt(receipt) == receipt
    # ... and so does the terminal preflight-failure receipt, from the same source.
    projected = project_preflight_provider_attempts(routing["provider_attempts"])
    assert projected is not None
    assert projected[-1]["stage"] == "critic"
    assert projected[-1]["validation_failures"] == [row]
    assert preflight_staffing_reason_codes({**_routing(outcome), **routing}) == [
        "staffing_critic_rejected",
        "critic_wrong_neighbor_selection",
    ]


def test_the_pointer_wire_form_is_closed_and_fails_whole() -> None:
    good = CRITIC_POINTER_DETAIL_PREFIX + "unit-a=lead>other,unit-b=lead>third"
    assert project_nomination_failures(good) == [
        {
            "unit_id": "unit-a",
            "reason_code": "critic_wrong_neighbor_selection",
            "selected_agent_id": "lead",
            "neighbor_agent_id": "other",
        },
        {
            "unit_id": "unit-b",
            "reason_code": "critic_wrong_neighbor_selection",
            "selected_agent_id": "lead",
            "neighbor_agent_id": "third",
        },
    ]
    # A projected row re-projects to itself, which every reader relies on.
    assert project_nomination_failures(project_nomination_failures(good)) == (
        project_nomination_failures(good)
    )
    for bad in (
        CRITIC_POINTER_DETAIL_PREFIX + "unit-a=lead",
        CRITIC_POINTER_DETAIL_PREFIX + "unit-a=lead>lead",
        CRITIC_POINTER_DETAIL_PREFIX + "unit-a=lead>Has Space",
        CRITIC_POINTER_DETAIL_PREFIX + "notaunit=lead>other",
        CRITIC_POINTER_DETAIL_PREFIX + "unit-a=lead>other,unit-a=lead>other",
        CRITIC_POINTER_DETAIL_PREFIX + ",".join(f"unit-{i}=lead>other" for i in range(9)),
    ):
        assert project_nomination_failures(bad) == []
    # The identities are admitted on no other row shape.
    assert (
        project_nomination_failures(
            [{"unit_id": "unit-a", "reason_code": "invalid_ranking", "neighbor_agent_id": "x"}]
        )
        == []
    )


def test_an_unnamed_claim_is_repaired_once_and_an_approval_then_stands() -> None:
    outcome, prompts = _run_replies(_VETO, _APPROVAL)

    assert outcome.accepted
    assert [(a.stage, a.status, a.reason_code) for a in outcome.attempts[-2:]] == [
        ("critic", "rejected", "provider_response_contract_invalid"),
        ("critic", "applied", "structured_response_applied"),
    ]
    assert outcome.attempts[-2].validation_reason_codes == ("critic_wrong_neighbor_unnamed",)
    feedback = _feedback(prompts[3])
    assert feedback["validation_reason_codes"] == ["critic_wrong_neighbor_unnamed"]
    assert "names no wrong_neighbors pointer" in feedback["deterministic_validation_detail"]
    assert "do not use that ground" in feedback["required_action"]
    # The repair re-sends the same document: the neighbourhood was already there.
    assert prompts[3].split("\n\n[RUNTIME", 1)[0] == prompts[2]


def test_an_unnamed_claim_repaired_with_a_verified_pointer_is_a_veto() -> None:
    outcome, _ = _run_replies(_VETO, {**_VETO, "wrong_neighbors": [_POINTER]})

    assert not outcome.accepted
    assert outcome.abstention_codes[-2:] == ("staffing_critic_rejected", "wrong-neighbor-selection")
    assert outcome.attempts[-1].validation_detail.startswith(CRITIC_POINTER_DETAIL_PREFIX)


def test_a_claim_that_stays_unnamed_fails_the_stage_and_is_never_a_veto() -> None:
    outcome, _ = _run_replies(_VETO, _VETO)

    assert not outcome.accepted
    assert outcome.status == "inference_invalid"
    assert "staffing_critic_rejected" not in outcome.abstention_codes
    assert outcome.abstention_codes[-1] == "workforce_inference_failed"
    assert [a.validation_reason_codes for a in outcome.attempts[-2:]] == [
        ("critic_wrong_neighbor_unnamed",),
        ("critic_wrong_neighbor_unnamed",),
    ]
    routing = project_workforce_routing(
        outcome,
        [],
        request="Put this editor on my machine.",
        roster_count=3,
        contract_fingerprint="c" * 64,
    )
    projected = project_preflight_provider_attempts(routing["provider_attempts"])
    assert projected is not None
    assert [a.get("validation_reason_codes") for a in projected[-2:]] == [
        ["critic_wrong_neighbor_unnamed"],
        ["critic_wrong_neighbor_unnamed"],
    ]


def test_each_unverifiable_pointer_is_named_by_the_check_it_failed() -> None:
    cases = {
        "names a unit the plan does not contain": {**_POINTER, "unit_id": "unit-other"},
        "the runtime did not select": {**_POINTER, "selected_agent_id": _NEIGHBOUR},
        "already selected": {**_POINTER, "neighbor_agent_id": "operations-manager"},
        # The desktop engineer was ranked but is ineligible on a plan unit.
        "outside the eligible neighbourhood": {
            **_POINTER,
            "neighbor_agent_id": "desktop-app-engineer",
        },
    }
    for phrase, pointer in cases.items():
        outcome, prompts = _run_replies({**_VETO, "wrong_neighbors": [pointer]}, _APPROVAL)
        assert outcome.accepted, phrase
        assert outcome.attempts[-2].validation_reason_codes == (
            "critic_wrong_neighbor_unverified",
        ), phrase
        detail = _feedback(prompts[3])["deterministic_validation_detail"]
        assert phrase in detail, (phrase, detail)
        # The detail echoes only the runtime's own identities, never the claim.
        assert "unit-other" not in detail


def test_a_whole_neighbourhood_admits_no_wrong_neighbour_claim() -> None:
    # ``_run``'s snapshot selects its whole eligible neighbourhood; the desktop
    # engineer it names is ineligible, so no pointer can verify.
    replies = iter(
        (
            _result(_PLAN),
            _result(_NOMINATION),
            _result({**_VETO, "wrong_neighbors": [{**_POINTER, "neighbor_agent_id": "x"}]}),
            _result(_APPROVAL),
        )
    )
    prompts: list[str] = []
    clear_workforce_caches()

    def invoke(*args, **_kwargs):
        prompts.append(str(args[1]))
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_contract("operations-manager"), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    assert outcome.accepted
    assert (
        "whole eligible neighbourhood" in _feedback(prompts[3])["deterministic_validation_detail"]
    )


def test_pointer_shape_failures_are_their_own_code() -> None:
    for reply in (
        {**_VETO, "wrong_neighbors": "not-a-list"},
        {**_VETO, "wrong_neighbors": [{"unit_id": _UNIT}]},
        {**_VETO, "wrong_neighbors": [_POINTER, _POINTER]},
        {**_VETO, "wrong_neighbors": [_POINTER] * (MAX_CRITIC_WRONG_NEIGHBOR_POINTERS + 1)},
        # Pointers without the ground they belong to.
        {
            "approved": False,
            "reason_codes": ["unsupported-confidence"],
            "wrong_neighbors": [_POINTER],
        },
    ):
        outcome, _ = _run_replies(reply, _APPROVAL)
        assert outcome.accepted
        assert outcome.attempts[-2].validation_reason_codes == (
            "critic_wrong_neighbor_shape_invalid",
        ), reply
    # An approval that carries pointers is the existing approval-with-reasons failure.
    outcome, _ = _run_replies({**_APPROVAL, "wrong_neighbors": [_POINTER]}, _APPROVAL)
    assert outcome.accepted
    assert outcome.attempts[-2].validation_reason_codes == ("critic_approval_reasons_present",)


def test_other_grounds_need_no_pointer_and_a_qualified_code_still_counts_as_the_ground() -> None:
    outcome, _ = _run_neighbourhood(
        {"approved": False, "reason_codes": ["missing-lifecycle-assurance-the-plan-calls-for"]}
    )
    assert not outcome.accepted
    assert outcome.abstention_codes[-1] == "missing-lifecycle-assurance-the-plan-calls-for"
    assert outcome.attempts[-1].validation_detail == ""

    outcome, _ = _run_replies(
        {**_VETO, "reason_codes": [f"wrong-neighbor-selection-{_NEIGHBOUR}"]}, _APPROVAL
    )
    assert outcome.accepted
    assert outcome.attempts[-2].validation_reason_codes == ("critic_wrong_neighbor_unnamed",)

    # The single-card runner is unchanged for grounds that need no pointer.
    outcome, _ = _run({"approved": False, "reason_codes": ["unsupported-confidence"]})
    assert outcome.abstention_codes[-1] == "unsupported-confidence"


def test_the_pointer_record_is_a_frozen_identity_triple() -> None:
    pointer = WrongNeighborPointer(_UNIT, "operations-manager", _NEIGHBOUR)
    assert pointer == WrongNeighborPointer(_UNIT, "operations-manager", _NEIGHBOUR)
    assert pointer.neighbor_agent_id == _NEIGHBOUR
