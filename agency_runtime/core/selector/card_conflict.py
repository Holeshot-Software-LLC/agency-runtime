"""Inference-checked conflict resolution for plural specialist selections.

Vision rule 3 allows multiple cards "when the job needs them and they don't
conflict". The deterministic half of that already exists in ``compatibility``:
declared ``conflicts_with`` edges, shared ``independence_group`` with the same
exclusive authority, and required separate context. What it cannot see is two
cards whose *prompts* pull in opposite directions without either card having
declared anything about the other.

Measured against the shipped roster, the declarative rules resolve 30 of 34,453
possible pairs -- 0.087%. Independence groups are near-unique (251 groups across
263 agents), so the authority rule fires on a single pair. For essentially every
real pairing, nothing was asking whether the two cards actually agree.

This module closes that gap the way the vision specifies: pairs that are not
explicitly declared companions are put to inference, and when it reports a
genuine conflict the card least suited to the current job is demoted. A cap is
not a conflict check; this is the check.

Three properties keep it from violating rule 8:

- It never blocks. Every failure -- no provider, malformed output, timeout,
  unparseable verdict -- returns the deterministic selection untouched.
- It never empties the selection. Demotion always leaves at least one card.
- It is bounded. At most ``MAX_CONFLICT_PAIRS`` pairs are examined, in one
  request, and only when a plural selection actually contains undeclared pairs.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from itertools import combinations
from typing import Any

logger = logging.getLogger("agency_runtime.selector.card_conflict")

CARD_CONFLICT_CONTRACT_VERSION = 1
MAX_CONFLICT_PAIRS = 6
MAX_CONFLICT_REASON_CHARS = 240
_MAX_TASK_CHARS = 2_000
_MAX_DESCRIPTION_CHARS = 200


def _closed_object(properties: Mapping[str, Any], required: Sequence[str]) -> dict[str, Any]:
    return {
        "additionalProperties": False,
        "properties": dict(properties),
        "required": list(required),
        "type": "object",
    }


_VERDICT_SCHEMA = _closed_object(
    {
        "left": {"maxLength": 128, "minLength": 1, "type": "string"},
        "right": {"maxLength": 128, "minLength": 1, "type": "string"},
        "conflicts": {"type": "boolean"},
        "demote": {"maxLength": 128, "type": "string"},
        "reason": {"maxLength": MAX_CONFLICT_REASON_CHARS, "type": "string"},
    },
    ("left", "right", "conflicts", "demote", "reason"),
)

CARD_CONFLICT_SCHEMA = _closed_object(
    {
        "verdicts": {
            "items": _VERDICT_SCHEMA,
            "maxItems": MAX_CONFLICT_PAIRS,
            "type": "array",
        }
    },
    ("verdicts",),
)

CARD_CONFLICT_SYSTEM_PROMPT = (
    "You decide whether two specialist instruction sets can be given to the same "
    "assistant for the same task at the same time.\n\n"
    "They CONFLICT only when following both is incoherent: they mandate opposite "
    "actions, claim the same exclusive decision authority, or impose mutually "
    "exclusive process requirements. Two specialists covering different parts of "
    "one job, or one advising while the other implements, do NOT conflict. "
    "Different subject matter is not a conflict. Overlap is not a conflict.\n\n"
    "Default to conflicts=false when unsure; a false conflict silently removes "
    "expertise the task needed. When they do conflict, set demote to whichever "
    "slug is LESS suited to the stated task, and keep the better-suited one."
)


def _slug(value: object) -> str:
    return str(value or "").strip()


def _strings(value: object) -> set[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        return set()
    return {text for item in value if (text := str(item or "").strip())}


def declared_companion_pairs(
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    policy_groups: Iterable[Iterable[str]] = (),
) -> set[frozenset[str]]:
    """Return pairs already declared to belong together.

    A declared relationship is an explicit statement by the roster that two
    cards are meant to co-occur, so re-litigating it with inference would spend
    a request to second-guess a reviewed contract. Two sources count: a
    ``requires`` edge, and co-membership of a companion-policy group.
    """

    declared: set[frozenset[str]] = set()
    for slug, agent in catalog.items():
        if not isinstance(agent, Mapping):
            continue
        for required in _strings(agent.get("requires")):
            if required != slug:
                declared.add(frozenset({slug, required}))
    for group in policy_groups or ():
        members = sorted({text for item in group if (text := _slug(item))})
        for left, right in combinations(members, 2):
            declared.add(frozenset({left, right}))
    return declared


def undeclared_pairs(
    selected_ids: Sequence[str],
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    declared: set[frozenset[str]] | None = None,
    limit: int = MAX_CONFLICT_PAIRS,
) -> list[tuple[str, str]]:
    """Return the bounded set of pairs that no declaration has already settled."""

    known = declared if declared is not None else set()
    ordered = [slug for item in selected_ids if (slug := _slug(item)) in catalog]
    bounded = max(0, min(int(limit), MAX_CONFLICT_PAIRS))
    if len(ordered) < 2 or not bounded:
        return []
    pairs: list[tuple[str, str]] = []
    for left, right in combinations(dict.fromkeys(ordered), 2):
        if frozenset({left, right}) in known:
            continue
        pairs.append((left, right))
        if len(pairs) >= bounded:
            break
    return pairs


def build_conflict_prompt(
    user_message: str,
    pairs: Sequence[tuple[str, str]],
    catalog: Mapping[str, Mapping[str, Any]],
) -> str:
    """Render one bounded request describing the task and the candidate pairs.

    Descriptions and declared behaviour hints are sent, never prompt bodies: the
    decision is about whether two roles can coexist, and four full cards would
    cost more than the selection they are adjudicating.
    """

    task = " ".join(str(user_message or "").split())[:_MAX_TASK_CHARS]
    lines = [f"TASK: {task}", "", "CANDIDATE PAIRS:"]
    for index, (left, right) in enumerate(pairs, start=1):
        lines.append(f"{index}. {left} vs {right}")
        for slug in (left, right):
            agent = catalog.get(slug) or {}
            description = " ".join(str(agent.get("description") or "").split())
            authority = _slug(agent.get("authority"))
            lines.append(
                f"   - {slug} (authority={authority or 'unspecified'}): "
                f"{description[:_MAX_DESCRIPTION_CHARS]}"
            )
            avoid = sorted(_strings(agent.get("avoid_when")))[:3]
            if avoid:
                lines.append(f"     avoid_when: {', '.join(avoid)[:_MAX_DESCRIPTION_CHARS]}")
    lines.append("")
    lines.append("Return one verdict per pair, in the same order.")
    return "\n".join(lines)


def apply_conflict_verdicts(
    selected_ids: Sequence[str],
    verdicts: Iterable[Mapping[str, Any]],
    pairs: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Demote the least-suited card of each genuinely conflicting pair.

    Order is the caller's selection order, so the outcome is reproducible from
    the same verdicts. A verdict that names a slug outside its own pair is
    ignored rather than trusted, and the last remaining card is never demoted:
    resolving a conflict must not turn into abstention.
    """

    kept = [slug for item in selected_ids if (slug := _slug(item))]
    expected = {frozenset(pair) for pair in pairs}
    demoted: list[dict[str, str]] = []
    for verdict in verdicts or ():
        if not isinstance(verdict, Mapping) or verdict.get("conflicts") is not True:
            continue
        left = _slug(verdict.get("left"))
        right = _slug(verdict.get("right"))
        demote = _slug(verdict.get("demote"))
        if frozenset({left, right}) not in expected or demote not in {left, right}:
            continue
        if demote not in kept or len(kept) <= 1:
            continue
        # Both sides must still be live, or there is no conflict left to resolve.
        if (right if demote == left else left) not in kept:
            continue
        kept.remove(demote)
        demoted.append(
            {
                "slug": demote,
                "conflicts_with": right if demote == left else left,
                "reason": " ".join(str(verdict.get("reason") or "").split())[
                    :MAX_CONFLICT_REASON_CHARS
                ],
            }
        )
    return {
        "contract_version": CARD_CONFLICT_CONTRACT_VERSION,
        "selected_ids": kept,
        "demoted": demoted,
        "checked_pairs": [list(pair) for pair in pairs],
    }


def unchecked_result(selected_ids: Sequence[str], reason: str) -> dict[str, Any]:
    """Return the deterministic selection untouched, recording why."""

    return {
        "contract_version": CARD_CONFLICT_CONTRACT_VERSION,
        "selected_ids": [slug for item in selected_ids if (slug := _slug(item))],
        "demoted": [],
        "checked_pairs": [],
        "skipped": reason,
    }


def resolve_card_conflicts(
    selected_ids: Sequence[str],
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    user_message: str,
    provider: Any = None,
    invoker: Any = None,
    declared: set[frozenset[str]] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Demote cards that inference reports as conflicting for this exact task.

    Returns the selection unchanged whenever the question cannot be answered.
    Losing the check costs a possible contradiction; failing the turn over it
    would cost the turn, and rule 8 is explicit about which of those is worse.
    """

    ordered = [slug for item in selected_ids if (slug := _slug(item))]
    if len(ordered) < 2:
        return unchecked_result(ordered, "single_card")
    pairs = undeclared_pairs(ordered, catalog, declared=declared)
    if not pairs:
        return unchecked_result(ordered, "all_pairs_declared_compatible")
    if provider is None or invoker is None:
        return unchecked_result(ordered, "inference_unavailable")
    try:
        result = invoker(
            provider,
            build_conflict_prompt(user_message, pairs, catalog),
            CARD_CONFLICT_SCHEMA,
            system_prompt=CARD_CONFLICT_SYSTEM_PROMPT,
            timeout=timeout,
        )
    except Exception:
        logger.debug(
            "card conflict inference failed; keeping the deterministic selection",
            exc_info=True,
        )
        return unchecked_result(ordered, "inference_failed")
    value = getattr(result, "value", None)
    if not isinstance(value, Mapping) or not isinstance(value.get("verdicts"), list):
        return unchecked_result(ordered, "inference_unusable")
    resolved = apply_conflict_verdicts(ordered, value["verdicts"], pairs)
    receipt = getattr(result, "receipt", None)
    if callable(receipt):
        try:
            resolved["provider_receipt"] = receipt()
        except Exception:
            logger.debug("card conflict provider receipt was unavailable", exc_info=True)
    return resolved


__all__ = [
    "CARD_CONFLICT_CONTRACT_VERSION",
    "CARD_CONFLICT_SCHEMA",
    "CARD_CONFLICT_SYSTEM_PROMPT",
    "MAX_CONFLICT_PAIRS",
    "MAX_CONFLICT_REASON_CHARS",
    "apply_conflict_verdicts",
    "build_conflict_prompt",
    "declared_companion_pairs",
    "resolve_card_conflicts",
    "unchecked_result",
    "undeclared_pairs",
]
