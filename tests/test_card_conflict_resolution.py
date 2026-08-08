"""Multiple cards are allowed only when they do not conflict (vision rule 3).

The declarative rules in ``compatibility`` resolve 30 of 34,453 possible pairs
across the shipped roster. For everything else, two cards that contradict each
other were being handed to the same assistant with nothing to notice. These
tests pin the check that closes that, and -- more importantly -- pin the
guarantees that stop it from becoming a way to lose specialists or turns.
"""

from __future__ import annotations

from typing import Any

from agency_runtime.core.selector.card_conflict import (
    CARD_CONFLICT_SCHEMA,
    MAX_CONFLICT_PAIRS,
    apply_conflict_verdicts,
    build_conflict_prompt,
    declared_companion_pairs,
    resolve_card_conflicts,
    undeclared_pairs,
)

_CATALOG: dict[str, dict[str, Any]] = {
    "implementer": {
        "slug": "implementer",
        "authority": "modify",
        "description": "Writes and changes production code.",
    },
    "independent-reviewer": {
        "slug": "independent-reviewer",
        "authority": "review",
        "description": "Reviews changes without authoring them.",
        "avoid_when": ["authoring the change under review"],
    },
    "minimal-change-engineer": {
        "slug": "minimal-change-engineer",
        "authority": "modify",
        "description": "Makes the smallest possible change.",
    },
    "rapid-prototyper": {
        "slug": "rapid-prototyper",
        "authority": "modify",
        "description": "Builds throwaway prototypes quickly.",
    },
    "doc-writer": {
        "slug": "doc-writer",
        "authority": "advise",
        "description": "Writes documentation.",
        "requires": ["implementer"],
    },
}


class _Result:
    def __init__(self, value: Any, receipt: Any = None) -> None:
        self.value = value
        self._receipt = receipt or {"provider_name": "test", "actual_model": "test-model"}

    def receipt(self) -> dict[str, Any]:
        return self._receipt


def _invoker(verdicts: list[dict[str, Any]]) -> Any:
    def invoke(*_args: Any, **_kwargs: Any) -> Any:
        return _Result({"verdicts": verdicts})

    return invoke


def test_conflicting_pair_demotes_the_card_least_suited_to_the_job() -> None:
    resolved = resolve_card_conflicts(
        ["minimal-change-engineer", "rapid-prototyper"],
        _CATALOG,
        user_message="Make the smallest safe fix to the billing bug.",
        provider=object(),
        invoker=_invoker(
            [
                {
                    "left": "minimal-change-engineer",
                    "right": "rapid-prototyper",
                    "conflicts": True,
                    "demote": "rapid-prototyper",
                    "reason": "throwaway prototyping contradicts a minimal safe fix",
                }
            ]
        ),
    )

    assert resolved["selected_ids"] == ["minimal-change-engineer"]
    assert resolved["demoted"][0]["slug"] == "rapid-prototyper"
    assert resolved["demoted"][0]["conflicts_with"] == "minimal-change-engineer"
    assert "prototyping" in resolved["demoted"][0]["reason"]


def test_non_conflicting_pair_keeps_both_cards() -> None:
    """Plural delivery is the product. The check exists to protect it, not trim it."""

    resolved = resolve_card_conflicts(
        ["implementer", "independent-reviewer"],
        _CATALOG,
        user_message="Implement and independently review the change.",
        provider=object(),
        invoker=_invoker(
            [
                {
                    "left": "implementer",
                    "right": "independent-reviewer",
                    "conflicts": False,
                    "demote": "",
                    "reason": "different parts of one job",
                }
            ]
        ),
    )

    assert resolved["selected_ids"] == ["implementer", "independent-reviewer"]
    assert resolved["demoted"] == []


def test_a_declared_requires_pair_is_never_sent_to_inference() -> None:
    """The roster already stated these belong together; do not pay to re-ask."""

    declared = declared_companion_pairs(_CATALOG)

    def _explode(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("declared companions must not reach inference")

    resolved = resolve_card_conflicts(
        ["doc-writer", "implementer"],
        _CATALOG,
        user_message="Document the new endpoint.",
        provider=object(),
        invoker=_explode,
        declared=declared,
    )

    assert resolved["selected_ids"] == ["doc-writer", "implementer"]
    assert resolved["skipped"] == "all_pairs_declared_compatible"


def test_companion_policy_groups_count_as_declared() -> None:
    declared = declared_companion_pairs(
        _CATALOG,
        policy_groups=[["implementer", "independent-reviewer"]],
    )

    assert frozenset({"implementer", "independent-reviewer"}) in declared
    assert undeclared_pairs(["implementer", "independent-reviewer"], _CATALOG, declared=declared) == []


def test_a_single_card_is_never_checked() -> None:
    resolved = resolve_card_conflicts(
        ["implementer"],
        _CATALOG,
        user_message="Fix it.",
        provider=object(),
        invoker=_invoker([]),
    )

    assert resolved["selected_ids"] == ["implementer"]
    assert resolved["skipped"] == "single_card"


def test_conflict_resolution_never_empties_the_selection() -> None:
    """Resolving a conflict must not collapse into abstention."""

    resolved = resolve_card_conflicts(
        ["implementer", "rapid-prototyper"],
        _CATALOG,
        user_message="Ship something.",
        provider=object(),
        invoker=_invoker(
            [
                {
                    "left": "implementer",
                    "right": "rapid-prototyper",
                    "conflicts": True,
                    "demote": "rapid-prototyper",
                    "reason": "one",
                },
                # A second verdict naming the survivor must not empty the set.
                {
                    "left": "implementer",
                    "right": "rapid-prototyper",
                    "conflicts": True,
                    "demote": "implementer",
                    "reason": "two",
                },
            ]
        ),
    )

    assert resolved["selected_ids"] == ["implementer"]


def test_a_verdict_naming_a_card_outside_its_pair_is_ignored() -> None:
    """Inference proposes; it does not get to demote something it was not asked about."""

    resolved = apply_conflict_verdicts(
        ["implementer", "rapid-prototyper", "doc-writer"],
        [
            {
                "left": "implementer",
                "right": "rapid-prototyper",
                "conflicts": True,
                "demote": "doc-writer",
                "reason": "not a member of this pair",
            }
        ],
        [("implementer", "rapid-prototyper")],
    )

    assert resolved["selected_ids"] == ["implementer", "rapid-prototyper", "doc-writer"]
    assert resolved["demoted"] == []


def test_a_verdict_for_an_unrequested_pair_is_ignored() -> None:
    resolved = apply_conflict_verdicts(
        ["implementer", "rapid-prototyper"],
        [
            {
                "left": "implementer",
                "right": "doc-writer",
                "conflicts": True,
                "demote": "implementer",
                "reason": "pair was never submitted",
            }
        ],
        [("implementer", "rapid-prototyper")],
    )

    assert resolved["selected_ids"] == ["implementer", "rapid-prototyper"]


def test_inference_failure_keeps_the_deterministic_selection() -> None:
    """Rule 8: losing the check costs a contradiction; failing costs the turn."""

    def _explode(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("provider is down")

    resolved = resolve_card_conflicts(
        ["implementer", "rapid-prototyper"],
        _CATALOG,
        user_message="Ship something.",
        provider=object(),
        invoker=_explode,
    )

    assert resolved["selected_ids"] == ["implementer", "rapid-prototyper"]
    assert resolved["skipped"] == "inference_failed"


def test_missing_provider_keeps_the_deterministic_selection() -> None:
    resolved = resolve_card_conflicts(
        ["implementer", "rapid-prototyper"],
        _CATALOG,
        user_message="Ship something.",
        provider=None,
        invoker=None,
    )

    assert resolved["selected_ids"] == ["implementer", "rapid-prototyper"]
    assert resolved["skipped"] == "inference_unavailable"


def test_unusable_inference_output_keeps_the_deterministic_selection() -> None:
    def _garbage(*_args: Any, **_kwargs: Any) -> Any:
        return _Result({"unexpected": True})

    resolved = resolve_card_conflicts(
        ["implementer", "rapid-prototyper"],
        _CATALOG,
        user_message="Ship something.",
        provider=object(),
        invoker=_garbage,
    )

    assert resolved["selected_ids"] == ["implementer", "rapid-prototyper"]
    assert resolved["skipped"] == "inference_unusable"


def test_pair_count_is_bounded() -> None:
    catalog = {f"agent-{index}": {"slug": f"agent-{index}"} for index in range(12)}
    pairs = undeclared_pairs(list(catalog), catalog)

    assert len(pairs) == MAX_CONFLICT_PAIRS


def test_prompt_carries_the_task_and_identities_but_never_a_prompt_body() -> None:
    catalog = {
        "implementer": {**_CATALOG["implementer"], "prompt_body": "SECRET-CARD-BODY"},
        "rapid-prototyper": {**_CATALOG["rapid-prototyper"], "prompt_body": "OTHER-CARD-BODY"},
    }
    prompt = build_conflict_prompt(
        "Make the smallest safe fix.",
        [("implementer", "rapid-prototyper")],
        catalog,
    )

    assert "Make the smallest safe fix." in prompt
    assert "implementer" in prompt and "rapid-prototyper" in prompt
    assert "authority=modify" in prompt
    # Adjudicating two roles must not cost more than delivering them.
    assert "SECRET-CARD-BODY" not in prompt
    assert "OTHER-CARD-BODY" not in prompt


def test_schema_is_closed_and_bounded() -> None:
    assert CARD_CONFLICT_SCHEMA["additionalProperties"] is False
    verdicts = CARD_CONFLICT_SCHEMA["properties"]["verdicts"]
    assert verdicts["maxItems"] == MAX_CONFLICT_PAIRS
    assert verdicts["items"]["additionalProperties"] is False
    assert set(verdicts["items"]["required"]) == {
        "left",
        "right",
        "conflicts",
        "demote",
        "reason",
    }
