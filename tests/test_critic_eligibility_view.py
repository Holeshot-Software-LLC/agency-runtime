"""AR-389 / ADR-0205: show the critic the eligible neighbourhood it judges against.

Measured 2026-09-03 on eleven install wordings under strict mode: three
verifier-accepted teams were lost to the strict critic's
``wrong-neighbor-selection`` veto, and the critic's document carried the
plan, the proposal, the verified staffing and the selected workers' contracts
but nothing about who else the runtime could have staffed on each unit. A
wrong-neighbor veto is a claim that a better-fitting eligible card existed,
and the critic could not check it. These cases pin the replacement view: per
unit, the verifier's complete eligible identity list, compact cards for the
eligible workers the recruiter ranked or selected, the count, and whether the
selected workers are the whole neighbourhood; the contract and the prompt say
a wrong-neighbor veto must point at a card in that list.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from agency_runtime.core.workforce.inference import (
    _CRITIC_SYSTEM,
    _MAX_CRITIC_NEIGHBOURHOOD_CARDS,
    _MAX_CRITIC_NEIGHBOURHOOD_IDS,
    plan_and_staff_workforce,
)
from tests.test_strict_critic_doctrine import (
    _PLAN,
    _UNIT,
    _config,
    _context,
    _contract,
    _desktop_engineer,
    _result,
    _run,
    _snapshot,
)


def _run_with(
    snapshot: Any, nominate: Callable[[dict[str, Any]], dict[str, Any]]
) -> list[dict[str, Any]]:
    """Drive planner, recruiter and critic; the recruiter reply is built from its prompt."""

    prompts: list[dict[str, Any]] = []

    def invoke(*args: Any, **_kwargs: Any) -> Any:
        # A repair prompt appends runtime feedback after the JSON document.
        document = json.loads(str(args[1]).split("\n\n[RUNTIME", 1)[0])
        prompts.append(document)
        if "planning_taxonomy" in document:
            return _result(_PLAN)
        if "detail_cards" in document:
            return _result(nominate(document))
        return _result({"approved": True, "reason_codes": []})

    plan_and_staff_workforce(
        "Put this editor on my machine.",
        snapshot,
        config=_config(),
        context=_context(),
        invoker=invoke,
    )
    return prompts


def _ranked(agent_ids: list[str], *, required: int) -> dict[str, Any]:
    rows = [
        {
            "agent_id": agent_id,
            "score": round(0.9 - index * 0.01, 2),
            "classification": "required" if index < required else "acceptable",
            "positive_evidence": ["operations-planning-coverage"],
            "negative_evidence": [],
        }
        for index, agent_id in enumerate(agent_ids)
    ]
    return {"units": [{"unit_id": _UNIT, "decision": "staff", "ranked_semantic": rows}]}


def test_the_critic_sees_the_complete_eligible_neighbourhood_per_unit() -> None:
    outcome, prompts = _run({"approved": True, "reason_codes": []})

    assert outcome.accepted
    neighbourhood = prompts[2]["eligible_neighbourhood"]
    assert list(neighbourhood) == [_UNIT]
    unit = neighbourhood[_UNIT]
    # The desktop engineer was ranked acceptable but carries modify authority on
    # a plan unit: ineligible, so it is neither an id nor a card here.
    assert unit["eligible_candidate_ids"] == ["operations-manager"]
    assert unit["eligible_count"] == 1
    assert [card["agent_id"] for card in unit["ranked_eligible_cards"]] == ["operations-manager"]
    assert unit["ranked_eligible_cards"][0] == {
        "agent_id": "operations-manager",
        "display_name": "Operations Manager",
        "archetype": "planner",
        "authority": "plan",
        "domains": ["operations"],
        "outcomes": ["operations-manager outcome"],
        "not_for": [],
    }
    assert unit["selected_are_whole_neighbourhood"] is True


def test_unranked_eligible_cards_are_ids_only_and_the_list_is_complete() -> None:
    planners = [f"planner-{index:02d}" for index in range(70)]
    snapshot = _snapshot(*(_contract(agent_id) for agent_id in planners), _desktop_engineer())
    ranked: list[str] = []

    def nominate(document: dict[str, Any]) -> dict[str, Any]:
        # Rank a bounded handful of the cards the recruiter was actually shown,
        # plus the ineligible desktop engineer when it is among them.
        shown = [card["agent_id"] for card in document["detail_cards"]]
        ranked.extend(sorted(item for item in shown if item.startswith("planner-"))[:6])
        if "desktop-app-engineer" in shown:
            ranked.append("desktop-app-engineer")
        return _ranked(ranked, required=1)

    prompts = _run_with(snapshot, nominate)

    assert len(prompts) == 3, [sorted(item)[:3] for item in prompts]
    unit = prompts[2]["eligible_neighbourhood"][_UNIT]
    # Complete: every eligible planner is named, in identity order, with the
    # count agreeing; the only bound on the list is the roster's own size.
    assert unit["eligible_count"] == len(planners)
    assert unit["eligible_candidate_ids"] == sorted(planners)
    assert len(planners) <= _MAX_CRITIC_NEIGHBOURHOOD_IDS
    cards = [card["agent_id"] for card in unit["ranked_eligible_cards"]]
    assert cards == sorted(item for item in ranked if item != "desktop-app-engineer")
    assert 0 < len(cards) <= _MAX_CRITIC_NEIGHBOURHOOD_CARDS
    assert "desktop-app-engineer" not in cards
    assert unit["selected_are_whole_neighbourhood"] is False


def test_the_contract_and_the_prompt_state_the_neighbourhood_boundary() -> None:
    _outcome, prompts = _run({"approved": True, "reason_codes": []})

    contract = prompts[2]["critic_contract"]
    assert contract["wrong_neighbor_must_name_an_eligible_card"] is True
    assert contract["eligible_neighbourhood_is_complete_per_unit"] is True
    for phrase in (
        "eligible_neighbourhood lists, per unit, every card the runtime could staff",
        "can never be the right neighbor",
        "A wrong-neighbor veto must point at a card in that unit's eligible_neighbourhood",
        "wrong-neighbor selection cannot apply to it",
    ):
        assert phrase in _CRITIC_SYSTEM, phrase
