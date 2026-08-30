"""Bounded, denominator-explicit summaries of persisted specialist selections."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

TOP_SPECIALIST_LIMIT = 50
TOP_CONCENTRATION_LIMIT = 10


def specialist_selection_distribution(
    decisions: Iterable[Iterable[object]],
    *,
    active_roster_size: int,
) -> dict[str, Any]:
    """Summarize selection frequency without treating multi-selection turns as one occurrence.

    ``decisions_with_selections`` is the number of persisted decisions
    containing at least one selected specialist. ``selection_occurrences`` is
    the number of specialist selections across those decisions, so a multi-specialist
    decision contributes once to each selected specialist and multiple times to
    the occurrence denominator.
    """

    if (
        isinstance(active_roster_size, bool)
        or not isinstance(active_roster_size, int)
        or active_roster_size < 0
    ):
        raise ValueError("active_roster_size must be a non-negative integer")

    decisions_by_specialist: Counter[str] = Counter()
    occurrences_by_specialist: Counter[str] = Counter()
    normalized_decisions: list[tuple[str, ...]] = []
    occurrence_count = 0
    for selected_ids in decisions:
        selected = _normalized_decision_selection(selected_ids)
        if not selected:
            continue
        normalized_decisions.append(selected)
        occurrence_count += len(selected)
        for slug in selected:
            decisions_by_specialist[slug] += 1
            occurrences_by_specialist[slug] += 1

    decision_count = len(normalized_decisions)
    ranked = sorted(
        occurrences_by_specialist,
        key=lambda slug: (-occurrences_by_specialist[slug], slug),
    )
    top_slugs = ranked[:TOP_SPECIALIST_LIMIT]
    concentration_slugs = ranked[:TOP_CONCENTRATION_LIMIT]
    top_occurrence_count = sum(occurrences_by_specialist[slug] for slug in concentration_slugs)
    long_tail_slugs = ranked[TOP_SPECIALIST_LIMIT:]
    long_tail_slug_set = set(long_tail_slugs)
    long_tail_occurrence_count = sum(occurrences_by_specialist[slug] for slug in long_tail_slugs)
    long_tail_decision_count = sum(
        any(slug in long_tail_slug_set for slug in selected) for selected in normalized_decisions
    )

    return {
        "decisions_with_selections": decision_count,
        "distinct_selected_specialists": len(ranked),
        "selection_occurrences": occurrence_count,
        "active_roster_size": active_roster_size,
        "top_10_selection_occurrences": top_occurrence_count,
        "top_10_share_of_selection_occurrences": _share(top_occurrence_count, occurrence_count),
        "top_specialists": [
            {
                "slug": slug,
                "decisions_containing_specialist": decisions_by_specialist[slug],
                "share_of_decisions_with_selections": _share(
                    decisions_by_specialist[slug], decision_count
                ),
                "selection_occurrences": occurrences_by_specialist[slug],
                "share_of_selection_occurrences": _share(
                    occurrences_by_specialist[slug], occurrence_count
                ),
            }
            for slug in top_slugs
        ],
        "long_tail": {
            "specialist_count": len(long_tail_slugs),
            "decisions_containing_specialist": long_tail_decision_count,
            "share_of_decisions_with_selections": _share(long_tail_decision_count, decision_count),
            "selection_occurrences": long_tail_occurrence_count,
            "share_of_selection_occurrences": _share(long_tail_occurrence_count, occurrence_count),
        },
    }


def _normalized_decision_selection(selected_ids: Iterable[object]) -> tuple[str, ...]:
    """Keep one bounded, unique specialist identity per decision."""

    selected: list[str] = []
    for value in selected_ids:
        if not isinstance(value, str):
            continue
        slug = value.strip()
        if slug and slug not in selected:
            selected.append(slug)
    return tuple(selected)


def _share(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
