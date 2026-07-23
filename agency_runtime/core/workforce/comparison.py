"""Deterministic, read-only workforce overlap and consolidation evidence."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.workforce.contract import WorkforceContract

_TOKENS = re.compile(r"[a-z0-9]+")
_RESIDENTS = frozenset({"agents-orchestrator", "chief-of-staff"})


def _tokens(*values: str) -> frozenset[str]:
    return frozenset(
        token
        for value in values
        for token in _TOKENS.findall(str(value).casefold())
        if len(token) > 1
    )


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _set_score(left: Sequence[str], right: Sequence[str]) -> float:
    return _jaccard(frozenset(left), frozenset(right))


@dataclass(frozen=True, slots=True)
class WorkforceComparison:
    left: str
    right: str
    score: float
    recommendation: str
    coherent_amendment: bool
    merge_review_candidate: bool
    reasons: tuple[str, ...]
    dimensions: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "score": self.score,
            "recommendation": self.recommendation,
            "coherent_amendment": self.coherent_amendment,
            "merge_review_candidate": self.merge_review_candidate,
            "reasons": list(self.reasons),
            "dimensions": dict(self.dimensions),
        }


def compare_workers(
    left: WorkforceContract,
    right: WorkforceContract,
) -> WorkforceComparison:
    """Compare two exact contracts without authorizing a lifecycle mutation."""

    if left.agent_id == right.agent_id or left.worker_id == right.worker_id:
        raise ValueError("workforce comparison requires distinct workers")
    dimensions = {
        "domains": _set_score(left.domains, right.domains),
        "stacks": _set_score(left.stacks, right.stacks),
        "artifacts": _set_score(left.artifact_kinds, right.artifact_kinds),
        "lifecycles": _set_score(left.lifecycle_phases, right.lifecycle_phases),
        "outcomes": _jaccard(_tokens(*left.outcomes), _tokens(*right.outcomes)),
        "qualifiers": _jaccard(
            _tokens(*left.scope_qualifiers),
            _tokens(*right.scope_qualifiers),
        ),
        "not_for": _jaccard(_tokens(*left.not_for), _tokens(*right.not_for)),
    }
    score = round(
        (0.20 * dimensions["domains"])
        + (0.15 * dimensions["stacks"])
        + (0.15 * dimensions["artifacts"])
        + (0.10 * dimensions["lifecycles"])
        + (0.25 * dimensions["outcomes"])
        + (0.10 * dimensions["qualifiers"])
        + (0.05 * dimensions["not_for"]),
        6,
    )
    same_shape = left.archetype == right.archetype and left.authority == right.authority
    domain_coherent = dimensions["domains"] > 0
    artifact_coherent = dimensions["artifacts"] > 0
    stacks_coherent = left.stacks == right.stacks
    conflicts = (
        right.agent_id in left.composition.same_context_conflicts
        or left.agent_id in right.composition.same_context_conflicts
        or right.agent_id in left.composition.selection_exclusive
        or left.agent_id in right.composition.selection_exclusive
    )
    resident = bool({left.agent_id, right.agent_id} & _RESIDENTS)
    explicit_substitution = bool(
        right.agent_id in left.composition.substitutes_for
        or left.agent_id in right.composition.substitutes_for
        or (
            left.composition.substitution_group
            and left.composition.substitution_group == right.composition.substitution_group
        )
    )
    coherent_amendment = bool(
        same_shape
        and domain_coherent
        and artifact_coherent
        and not conflicts
        and not resident
        and score >= 0.55
    )
    merge_review_candidate = bool(
        coherent_amendment
        and stacks_coherent
        and score >= 0.80
        and (
            explicit_substitution
            or left.employment != right.employment
            or left.origin == right.origin == "agency"
        )
    )
    reasons: list[str] = []
    if not same_shape:
        reasons.append("different archetype or authority")
    if not domain_coherent:
        reasons.append("no shared normalized domain")
    if not artifact_coherent:
        reasons.append("no shared artifact kind")
    if not stacks_coherent:
        reasons.append("different stack ownership")
    if conflicts:
        reasons.append("typed conflict requires separation")
    if resident:
        reasons.append("resident managers are protected")
    if explicit_substitution:
        reasons.append("typed substitution relationship exists")
    if merge_review_candidate:
        recommendation = "review_merge"
        reasons.append("high contract overlap; human evidence review required")
    elif coherent_amendment:
        recommendation = "review_amendment"
        reasons.append("scope may fit a governed version amendment")
    else:
        recommendation = "keep_distinct"
        reasons.append("contract evidence does not justify consolidation")
    return WorkforceComparison(
        left.agent_id,
        right.agent_id,
        score,
        recommendation,
        coherent_amendment,
        merge_review_candidate,
        tuple(dict.fromkeys(reasons)),
        dimensions,
    )


def nearest_workers(
    target: WorkforceContract,
    contracts: Sequence[WorkforceContract],
    *,
    limit: int = 10,
) -> tuple[WorkforceComparison, ...]:
    """Return bounded deterministic neighbors across every lifecycle state."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("workforce comparison limit must be from 1 through 100")
    comparisons = [
        compare_workers(target, candidate)
        for candidate in contracts
        if candidate.agent_id != target.agent_id
    ]
    comparisons.sort(key=lambda item: (-item.score, item.right))
    return tuple(comparisons[:limit])


def consolidation_candidates(
    contracts: Sequence[WorkforceContract],
    *,
    limit: int = 25,
) -> tuple[WorkforceComparison, ...]:
    """Return bounded review recommendations; never mutate or auto-merge."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("workforce consolidation limit must be from 1 through 100")
    rows = [
        comparison
        for index, left in enumerate(contracts)
        for right in contracts[index + 1 :]
        if (comparison := compare_workers(left, right)).coherent_amendment
    ]
    rows.sort(
        key=lambda item: (
            item.recommendation != "review_merge",
            -item.score,
            item.left,
            item.right,
        )
    )
    return tuple(rows[:limit])


__all__ = [
    "WorkforceComparison",
    "compare_workers",
    "consolidation_candidates",
    "nearest_workers",
]
