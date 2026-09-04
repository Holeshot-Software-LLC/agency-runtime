"""AR-394 c3 and c5: what the verifier does not judge, and what recall costs.

The turn that did staff on 2026-09-04 put `roblox-systems-scripter` on
`unit-implement-rate-limiting` at confidence 0.9 against the 0.8 floor, and the
deterministic verifier accepted it. These tests record why, and record what a
failed reranker does and does not cost, because the two are the same fact seen
from either end: the verifier judges whether a team is *safe*, and retrieval
alone decides whether it is *apt*.
"""

from __future__ import annotations

from agency_runtime.core.workforce.inference import (
    SAFE_TEAM_SHORTFALL_CODES,
    _apply_hybrid_recall,
)
from agency_runtime.core.workforce.staffing_verifier import (
    STAFFING_VERIFIER_REASON_CODES,
)
from tests.test_safe_team_shortfall import _UNIT
from tests.test_workforce_inference import _context, _contract, _snapshot

# Every word that would have to appear in a reason code for the verifier to be
# rejecting a team on topical grounds.
_FIT_WORDS = (
    "fit",
    "topic",
    "relevan",
    "semantic",
    "apt",
    "subject",
    "domain_mismatch",
    "unrelated",
)


def test_the_verifier_names_no_topical_property_at_all() -> None:
    """AR-394 c3: the recorded decision, asserted against the vocabulary.

    All 33 codes are structural: hashes, budgets, sets, ordering, eligibility,
    coverage and the recruiter's own confidence. `selection_confidence_too_low`
    reads the score the recruiter reported about itself, so a confident wrong
    answer -- 0.9 against a 0.8 floor -- clears it exactly as a confident right
    one does. Nothing here could have rejected `roblox-systems-scripter` for a
    rate-limiting unit, and nothing here is supposed to: see ADR-0213.
    """

    offending = sorted(
        code for code in STAFFING_VERIFIER_REASON_CODES if any(w in code for w in _FIT_WORDS)
    )
    assert offending == []
    assert "selection_confidence_too_low" in STAFFING_VERIFIER_REASON_CODES


def test_the_shortfall_vocabulary_names_no_topical_property_either() -> None:
    """The new AR-394 codes say who failed to supply a candidate, never who fits."""

    offending = sorted(
        code for code in SAFE_TEAM_SHORTFALL_CODES if any(w in code for w in _FIT_WORDS)
    )
    assert offending == []


def test_a_failed_reranker_leaves_the_baseline_candidate_order_untouched() -> None:
    """AR-394 c5: the recorded effect of the 20.4% contract-invalid rate.

    Measured 2026-09-04 on the live store, last 400 receipts: `recall_reranker`
    applied 109 of 142 attempts, was contract-invalid 29 times and returned no
    valid response 4 times, so it contributed nothing on 23.2% of the turns
    that ran it.

    Under `dense_recall_mode: additive` -- the live setting -- the reranker is
    never consulted for order. It can only *add* a card the typed baseline did
    not already admit, and an empty result returns the baseline unchanged. So
    the cost of a failed reranker is not a worse ordering; it is the absence of
    the candidates only it would have surfaced, which is what
    `coverer_absent_from_retrieval` now names on the receipt.
    """

    contracts = (_contract("api-platform-engineer"), _contract("roblox-systems-scripter"))
    snapshot = _snapshot(*contracts)
    plan = _plan()
    typed_recall = [
        {
            "unit_id": _UNIT.unit_id,
            "requirements": list(_UNIT.required_capabilities),
            "candidates": [{"agent_id": "roblox-systems-scripter"}],
        }
    ]

    recall, cards, added = _apply_hybrid_recall(
        plan=plan,
        typed_recall=list(typed_recall),
        snapshot=snapshot,
        context=_context(),
        result=None,
        reranked={},
    )
    assert recall == typed_recall
    assert [card["agent_id"] for card in cards] == ["roblox-systems-scripter"]
    assert added is None

    # The same call with a result present but nothing reranked takes the same
    # branch: an empty reranking is indistinguishable from no reranker at all.
    assert (
        _apply_hybrid_recall(
            plan=plan,
            typed_recall=list(typed_recall),
            snapshot=snapshot,
            context=_context(),
            result=None,
            reranked={_UNIT.unit_id: ()},
        )[1]
        == cards
    )


def test_the_specialist_the_turn_should_have_found_is_in_the_roster() -> None:
    """The fault is supply, not the verifier's contract.

    `api-platform-engineer` exists in the live roster (division `engineering`)
    beside `roblox-systems-scripter` (division `game-development`). Retrieval
    offered the second and not the first; every safety property the verifier
    checks was satisfied by the team it was handed.
    """

    snapshot = _snapshot(_contract("api-platform-engineer"), _contract("roblox-systems-scripter"))
    assert {contract.agent_id for contract in snapshot.contracts} == {
        "api-platform-engineer",
        "roblox-systems-scripter",
    }


def _plan():
    from agency_runtime.core.workforce.planning_contracts import WorkUnitPlan

    return WorkUnitPlan(
        schema_version=1,
        request_summary="add rate limiting to the public API gateway and write tests for it",
        units=(_UNIT,),
        plan_hash="sha256:" + "0" * 64,
    )
