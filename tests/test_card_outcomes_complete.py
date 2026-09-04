"""AR-390 / ADR-0206: the cards the recruiter and the critic read carry every outcome.

Measured 2026-09-04 on the eleven install wordings: the recruiter's compact
card carried a contract's first two outcomes only, and every enabled contract
declares at least three. The cross-platform release verifier's third and
fifth outcomes, installed-artifact smoke testing and upgrade and uninstall
verification, named the install-verification unit's work exactly and never
reached the recruiter; it required the evidence collector alone and the strict
critic vetoed the team. Replayed with every outcome on the cards, the
recruiter required the release verifier. These cases pin the card shape: every
outcome and every not_for line, bounded only by the contract's own limits.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from agency_runtime.core.workforce.contract import MAX_OUTCOMES
from agency_runtime.core.workforce.inference import (
    _compact_recruiter_card,
    _critic_neighbourhood_card,
    plan_and_staff_workforce,
)
from tests.test_strict_critic_doctrine import (
    _PLAN,
    _config,
    _context,
    _contract,
    _desktop_engineer,
    _result,
    _snapshot,
)

_OUTCOMES = (
    "evidence-backed release readiness",
    "verified installed-product portability",
    "installed-artifact smoke testing",
    "cross-platform configuration validation",
    "upgrade and uninstall verification",
)


def _verifier() -> Any:
    return replace(
        _contract("operations-manager"),
        outcomes=_OUTCOMES,
        not_for=("mobile store metadata", "anything outside installed-artifact verification"),
    )


def test_the_recruiter_card_carries_every_outcome_and_not_for_line() -> None:
    card = _compact_recruiter_card(_verifier())

    assert card["outcomes"] == list(_OUTCOMES)
    assert card["not_for"] == [
        "mobile store metadata",
        "anything outside installed-artifact verification",
    ]
    assert set(card) == {"agent_id", "display_name", "outcomes", "scope_qualifiers", "not_for"}


def test_the_critic_card_carries_the_same_outcomes_and_not_for_lines() -> None:
    card = _critic_neighbourhood_card(_verifier())

    assert card["outcomes"] == list(_OUTCOMES)
    assert card["not_for"] == [
        "mobile store metadata",
        "anything outside installed-artifact verification",
    ]


def test_the_contract_bound_is_the_only_bound_on_a_card_s_outcomes() -> None:
    eight = tuple(f"outcome {index}" for index in range(MAX_OUTCOMES))
    card = _compact_recruiter_card(replace(_contract("operations-manager"), outcomes=eight))

    assert len(card["outcomes"]) == MAX_OUTCOMES
    assert card["outcomes"] == list(eight)


def test_the_recruiter_document_shows_every_outcome_on_the_detail_card() -> None:
    prompts: list[dict[str, Any]] = []
    replies = iter(
        (
            _result(_PLAN),
            _result(
                {
                    "units": [
                        {
                            "unit_id": _PLAN["units"][0]["unit_id"],
                            "decision": "staff",
                            "ranked_semantic": [
                                {
                                    "agent_id": "operations-manager",
                                    "score": 0.9,
                                    "classification": "required",
                                    "positive_evidence": ["installed-artifact-smoke-test"],
                                    "negative_evidence": [],
                                }
                            ],
                        }
                    ]
                }
            ),
            _result({"approved": True, "reason_codes": []}),
        )
    )

    def invoke(*args: Any, **_kwargs: Any) -> Any:
        prompts.append(json.loads(str(args[1]).split("\n\n[RUNTIME", 1)[0]))
        return next(replies)

    outcome = plan_and_staff_workforce(
        "Put this editor on my machine.",
        _snapshot(_verifier(), _desktop_engineer()),
        config=_config(),
        context=_context(),
        invoker=invoke,
    )

    assert outcome.accepted
    cards = {card["agent_id"]: card for card in prompts[1]["detail_cards"]}
    assert cards["operations-manager"]["outcomes"] == list(_OUTCOMES)
    critic_cards = {
        card["agent_id"]: card
        for unit in prompts[2]["eligible_neighbourhood"].values()
        for card in unit["ranked_eligible_cards"]
    }
    assert critic_cards["operations-manager"]["outcomes"] == list(_OUTCOMES)
