"""Deterministic contract evaluation for the complete packaged roster.

This evaluator answers four bounded questions:

* did every approved and enabled routing card participate in both retrieval
  paths;
* can identity-free, semantically perturbed probes recover their target cards;
* do curated hard-negative, abstention, compatibility, and requirement cases
  obey the deterministic contracts; and
* do short continuation phrases retain their state-aware meaning.

The result is contract-only evidence.  It does not execute specialist work,
grade task outcomes, call an inference provider, or support a superiority
claim.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any, Final

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.evals.full_roster_cases import (
    COMPATIBILITY_CASES,
    RETRIEVAL_CASES,
    TURN_CASES,
)
from agency_runtime.core.roster.bundled import bundled_manifest
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.compatibility import (
    compile_compatibility_catalog,
    enforce_compatible_set,
)
from agency_runtime.core.selector.semantic_retrieval import (
    retrieve_candidate_union,
    semantic_retrieve,
)
from agency_runtime.core.turn_intent import classify_turn_intent
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import known_contractor_package

SCHEMA: Final[str] = "agency-runtime.full-roster-selection-eval"
VERSION: Final[str] = "2.0.0"
EVIDENCE_KIND: Final[str] = "contract_only"
DEFAULT_CANDIDATE_LIMIT: Final[int] = 40
MIN_CANDIDATE_LIMIT: Final[int] = 8
MAX_CANDIDATE_LIMIT: Final[int] = 80

THRESHOLDS: Final[dict[str, tuple[str, float]]] = {
    "lexical_participation_rate": (">=", 1.0),
    "semantic_participation_rate": (">=", 1.0),
    "target_candidate_recall": (">=", 1.0),
    "target_recall_at_10": (">=", 0.99),
    "curated_case_accuracy": (">=", 1.0),
    "abstention_accuracy": (">=", 1.0),
    "compatibility_case_accuracy": (">=", 1.0),
    "pairwise_composition_accuracy": (">=", 1.0),
    "turn_case_accuracy": (">=", 1.0),
    "identity_leak_rate": ("<=", 0.0),
    "preferred_sentence_copy_rate": ("<=", 0.0),
}

_WORD_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_PROBE_FIELDS = ("categories", "capabilities", "task_types", "description")
_PROBE_STOPWORDS = frozenset(
    {
        "agent",
        "analysis",
        "and",
        "application",
        "bounded",
        "create",
        "data",
        "design",
        "develop",
        "ensure",
        "expert",
        "for",
        "from",
        "implementation",
        "into",
        "needs",
        "product",
        "produce",
        "review",
        "specialist",
        "system",
        "task",
        "testing",
        "that",
        "the",
        "their",
        "through",
        "with",
        "work",
    }
)
# Fixed probe wording must be retrieval-neutral. Every non-placeholder word is
# a stopword in both deterministic retrievers, so the evaluation measures the
# routing card's identity-free concepts instead of generic response scaffolding.
_PROBE_QUERY_TEMPLATE = "I need help with {first} and {second} for {paraphrased}."
_PARAPHRASES = {
    "accessibility": "inclusive access",
    "analytics": "measured insight",
    "architecture": "system structure",
    "audit": "independent inspection",
    "automation": "repeatable machinery",
    "compliance": "governance assurance",
    "debug": "fault diagnosis",
    "documentation": "reader guidance",
    "engineering": "technical delivery",
    "extraction": "source harvesting",
    "finance": "financial control",
    "marketing": "audience growth",
    "performance": "runtime efficiency",
    "planning": "sequenced preparation",
    "security": "risk reduction",
    "strategy": "direction setting",
    "support": "customer resolution",
    "verification": "evidence checking",
}


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 1.0


def _agent_id(agent: Mapping[str, Any]) -> str:
    return agent_identity(agent)


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value if str(item or "").strip())


def _words(value: object) -> tuple[str, ...]:
    return tuple(
        token
        for token in _WORD_RE.findall(str(value or "").casefold().replace("_", " "))
        if len(token) >= 2 and token not in _PROBE_STOPWORDS
    )


def _phrase(value: object) -> str:
    return " ".join(_WORD_RE.findall(str(value or "").casefold().replace("_", " ")))


def _routing_cards() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = bundled_manifest()
    cards: list[dict[str, Any]] = []
    for entry in manifest["agents"]:
        if entry["audit_status"] != "approved":
            continue
        source = {
            **entry,
            "agent_slug": entry["slug"],
            "name": entry["display_name"],
        }
        cards.append(selector_roster_projection(source))
    cards.extend(
        selector_roster_projection(known_contractor_package(slug).agent)
        for slug in sorted(KNOWN_CONTRACTORS_BY_SLUG)
    )
    return manifest, cards


class _TrackedAgent(dict[str, Any]):
    """Record whether a real retrieval path inspected this routing card."""

    def __init__(self, source: Mapping[str, Any], touched: set[str]) -> None:
        super().__init__(source)
        self._agent_id = _agent_id(source)
        self._touched = touched

    def get(self, key: str, default: Any = None) -> Any:
        self._touched.add(self._agent_id)
        return super().get(key, default)


def _retrieval_participation(cards: Sequence[dict[str, Any]]) -> dict[str, Any]:
    query = "inspect bounded reliability evidence and operational failure recovery"
    expected = {_agent_id(agent) for agent in cards}
    lexical_touched: set[str] = set()
    lexical_cards = [_TrackedAgent(agent, lexical_touched) for agent in cards]
    pre_narrow(query, lexical_cards, limit=1)

    semantic_touched: set[str] = set()
    semantic_cards = [_TrackedAgent(agent, semantic_touched) for agent in cards]
    semantic_retrieve(query, semantic_cards, limit=1)
    lexical_missing = sorted(expected.difference(lexical_touched))
    semantic_missing = sorted(expected.difference(semantic_touched))
    return {
        "approved_enabled_count": len(expected),
        "prompt_body_field_count": sum("prompt_body" in agent for agent in cards),
        "lexical_participation_count": len(expected.intersection(lexical_touched)),
        "lexical_participation_rate": _ratio(
            len(expected.intersection(lexical_touched)),
            len(expected),
        ),
        "lexical_missing_agent_ids": lexical_missing,
        "semantic_participation_count": len(expected.intersection(semantic_touched)),
        "semantic_participation_rate": _ratio(
            len(expected.intersection(semantic_touched)),
            len(expected),
        ),
        "semantic_missing_agent_ids": semantic_missing,
        "proof_method": (
            "field-access instrumentation over the real lexical and deterministic "
            "metadata-embedding retrieval paths"
        ),
    }


def _card_terms(card: Mapping[str, Any]) -> set[str]:
    values = (
        text
        for field in _PROBE_FIELDS
        for value in _strings(card.get(field))
        for text in _words(value)
    )
    identity = set(_words(f"{_agent_id(card)} {card.get('name', '')}"))
    return set(values).difference(identity)


def _probe_queries(cards: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    terms_by_id = {_agent_id(card): _card_terms(card) for card in cards}
    document_frequency = Counter(term for terms in terms_by_id.values() for term in terms)
    probes: list[dict[str, Any]] = []
    for card in cards:
        slug = _agent_id(card)
        ranked = sorted(
            terms_by_id[slug],
            key=lambda term: (document_frequency[term], -len(term), term),
        )
        if len(ranked) < 3:
            raise ValueError(f"routing card cannot produce an identity-free probe: {slug}")
        first, second, concept = ranked[:3]
        paraphrased = _PARAPHRASES.get(concept, f"{concept} assurance")
        query = _PROBE_QUERY_TEMPLATE.format(
            first=first,
            second=second,
            paraphrased=paraphrased,
        )
        normalized_query = _phrase(query)
        identity_phrases = {
            phrase
            for value in (slug.replace("-", " "), card.get("name", ""))
            if (phrase := _phrase(value))
        }
        preferred_phrases = {
            phrase for value in _strings(card.get("preferred_when")) if (phrase := _phrase(value))
        }
        probes.append(
            {
                "slug": slug,
                "division": str(card.get("division") or ""),
                "categories": sorted(_strings(card.get("categories"))),
                "query": query,
                "identity_leak": any(phrase in normalized_query for phrase in identity_phrases),
                "preferred_sentence_copy": any(
                    phrase in normalized_query for phrase in preferred_phrases
                ),
                "anchors": [first, second],
                "paraphrased_concept": concept,
            }
        )
    return probes


def _gap_groups(
    results: Sequence[dict[str, Any]],
    field: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        values = (
            result.get(field, ())
            if isinstance(result.get(field), list)
            else (result.get(field, ""),)
        )
        for value in values:
            label = str(value or "").strip()
            if label:
                grouped[label].append(result)
    return {
        label: {
            "agent_count": len(items),
            "target_hits": sum(bool(item["target_hit"]) for item in items),
            "target_recall": _ratio(
                sum(bool(item["target_hit"]) for item in items),
                len(items),
            ),
            "missed_agent_ids": sorted(
                str(item["slug"]) for item in items if not item["target_hit"]
            ),
            "top_10_hits": sum(bool(item["target_top_10_hit"]) for item in items),
            "top_10_recall": _ratio(
                sum(bool(item["target_top_10_hit"]) for item in items),
                len(items),
            ),
            "top_10_missed_agent_ids": sorted(
                str(item["slug"]) for item in items if not item["target_top_10_hit"]
            ),
        }
        for label, items in sorted(grouped.items())
    }


def _probe_retrieval(
    cards: Sequence[dict[str, Any]],
    *,
    candidate_limit: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    probes = _probe_queries(cards)
    results: list[dict[str, Any]] = []
    positive_union_ids: set[str] = set()
    complete_union_ids: set[str] = set()
    for probe in probes:
        union = retrieve_candidate_union(
            str(probe["query"]),
            cards,
            limit=candidate_limit,
        )
        ranked_ids = [_agent_id(agent) for agent in union.candidates]
        score_by_id = dict(zip(ranked_ids, union.scores, strict=True))
        positive_ids = [
            agent_id for agent_id, score in zip(ranked_ids, union.scores, strict=True) if score > 0
        ]
        positive_union_ids.update(positive_ids)
        complete_union_ids.update(ranked_ids)
        target = str(probe["slug"])
        target_rank = positive_ids.index(target) + 1 if target in positive_ids else None
        results.append(
            {
                **probe,
                "target_hit": target_rank is not None,
                "target_top_10_hit": target_rank is not None and target_rank <= 10,
                "target_rank": target_rank,
                "target_score": score_by_id.get(target, 0.0),
                "positive_candidate_count": len(positive_ids),
                "candidate_union_count": len(ranked_ids),
                "lexical_count": union.lexical_count,
                "semantic_count": union.semantic_count,
                "hard_negative_count": union.hard_negative_count,
                "top_candidate_ids": ranked_ids[:10],
            }
        )

    target_hits = sum(bool(item["target_hit"]) for item in results)
    top_ten_hits = sum(
        isinstance(item["target_rank"], int) and item["target_rank"] <= 10 for item in results
    )
    identity_leaks = sum(bool(item["identity_leak"]) for item in results)
    preferred_copies = sum(bool(item["preferred_sentence_copy"]) for item in results)
    count = len(results)
    metrics = {
        "probe_count": count,
        "unique_probe_count": len({str(item["query"]) for item in results}),
        "target_hits": target_hits,
        "target_candidate_recall": _ratio(target_hits, count),
        "target_recall_at_10": _ratio(top_ten_hits, count),
        "mean_reciprocal_rank": round(
            sum(
                1.0 / int(item["target_rank"])
                for item in results
                if isinstance(item["target_rank"], int)
            )
            / count,
            6,
        )
        if count
        else 1.0,
        "positive_candidate_identity_count": len(positive_union_ids),
        "positive_candidate_identity_coverage": _ratio(
            len(positive_union_ids),
            count,
        ),
        "complete_candidate_identity_count": len(complete_union_ids),
        "complete_candidate_identity_coverage": _ratio(
            len(complete_union_ids),
            count,
        ),
        "mean_candidate_union_count": round(
            sum(int(item["candidate_union_count"]) for item in results) / count,
            4,
        )
        if count
        else 0.0,
        "mean_positive_candidate_count": round(
            sum(int(item["positive_candidate_count"]) for item in results) / count,
            4,
        )
        if count
        else 0.0,
        "identity_leak_count": identity_leaks,
        "identity_leak_rate": _ratio(identity_leaks, count),
        "preferred_sentence_copy_count": preferred_copies,
        "preferred_sentence_copy_rate": _ratio(preferred_copies, count),
        "missed_agent_ids": sorted(str(item["slug"]) for item in results if not item["target_hit"]),
        "top_10_missed_agent_ids": sorted(
            str(item["slug"]) for item in results if not item["target_top_10_hit"]
        ),
        "positive_candidate_gaps": sorted(
            {_agent_id(card) for card in cards}.difference(positive_union_ids)
        ),
        "division_gaps": _gap_groups(results, "division"),
        "category_gaps": _gap_groups(results, "categories"),
    }
    return metrics, results


def _curated_retrieval(
    cards: Sequence[dict[str, Any]],
    *,
    candidate_limit: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    details: list[dict[str, Any]] = []
    abstain_cases = 0
    abstain_hits = 0
    for case in RETRIEVAL_CASES:
        union = retrieve_candidate_union(
            str(case["query"]),
            cards,
            limit=candidate_limit,
        )
        scores = {
            _agent_id(agent): score
            for agent, score in zip(union.candidates, union.scores, strict=True)
        }
        positive_ids = [agent_id for agent_id, score in scores.items() if score > 0]
        required = {str(item) for item in case["required"]}
        forbidden = {str(item) for item in case["forbidden_above_required"]}
        max_required_rank = int(case["max_required_rank"])
        abstain = bool(case.get("abstain", False))
        if abstain:
            abstain_cases += 1
            abstain_hits += int(not positive_ids)
        required_score = min((scores.get(item, 0.0) for item in required), default=0.0)
        forbidden_above = sorted(
            item
            for item in forbidden
            if scores.get(item, 0.0) > 0 and scores[item] >= required_score
        )
        required_ranks = {
            item: positive_ids.index(item) + 1 if item in positive_ids else None
            for item in sorted(required)
        }
        ranks_pass = all(
            isinstance(rank, int) and rank <= max_required_rank for rank in required_ranks.values()
        )
        passed = (
            not positive_ids if abstain else required.issubset(positive_ids) and ranks_pass
        ) and not forbidden_above
        details.append(
            {
                "id": case["id"],
                "kind": case["kind"],
                "required": sorted(required),
                "required_scores": {item: scores.get(item, 0.0) for item in sorted(required)},
                "required_ranks": required_ranks,
                "max_required_rank": max_required_rank,
                "forbidden_above_required": forbidden_above,
                "positive_candidate_ids": positive_ids[:16],
                "candidate_union": union.evidence(),
                "passed": passed,
            }
        )
    return {
        "cases": len(details),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "curated_case_accuracy": _ratio(
            sum(bool(item["passed"]) for item in details),
            len(details),
        ),
        "abstention_cases": abstain_cases,
        "abstention_accuracy": _ratio(abstain_hits, abstain_cases),
    }, details


def _compatibility_eval(
    cards: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    details: list[dict[str, Any]] = []
    for case in COMPATIBILITY_CASES:
        result = enforce_compatible_set(case["requested"], cards)
        rejected = tuple(str(item["slug"]) for item in result["rejected"])
        expected_pair = tuple(str(item) for item in case["expected_separate_pair"])
        pair_present = not expected_pair or list(expected_pair) in result["separate_context_pairs"]
        passed = (
            tuple(result["selected_ids"]) == tuple(case["expected_selected"])
            and tuple(result["added_requirements"]) == tuple(case["expected_added"])
            and rejected == tuple(case["expected_rejected"])
            and pair_present
        )
        details.append(
            {
                "id": case["id"],
                "requested_ids": list(case["requested"]),
                "selected_ids": result["selected_ids"],
                "added_requirements": result["added_requirements"],
                "rejected": result["rejected"],
                "separate_context_pairs": result["separate_context_pairs"],
                "passed": passed,
            }
        )
    return {
        "cases": len(details),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "compatibility_case_accuracy": _ratio(
            sum(bool(item["passed"]) for item in details),
            len(details),
        ),
    }, details


def _pairwise_composition_eval(
    cards: Sequence[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Exercise every two-worker request and reject any unsafe resulting team."""

    ids = tuple(sorted(_agent_id(card) for card in cards))
    by_id = {_agent_id(card): card for card in cards}
    compatibility_catalog = compile_compatibility_catalog(cards)
    failures: list[dict[str, Any]] = []
    pair_count = 0
    direct_conflict_pairs = 0
    for left, right in combinations(ids, 2):
        pair_count += 1
        left_conflicts = set(_strings(by_id[left].get("conflicts_with")))
        right_conflicts = set(_strings(by_id[right].get("conflicts_with")))
        direct_conflict = right in left_conflicts or left in right_conflicts
        direct_conflict_pairs += int(direct_conflict)
        result = enforce_compatible_set((left, right), compatibility_catalog, limit=16)
        selected = set(result["selected_ids"])
        violations: list[str] = []
        if direct_conflict and {left, right} <= selected:
            violations.append("direct_conflict_survived")
        for selected_id in selected:
            conflicts = set(_strings(by_id[selected_id].get("conflicts_with")))
            overlap = sorted(conflicts.intersection(selected))
            if overlap:
                violations.append(f"selected_conflict:{selected_id}:{','.join(overlap)}")
        if violations:
            failures.append(
                {
                    "requested": [left, right],
                    "selected": list(result["selected_ids"]),
                    "violations": violations,
                }
            )
    passed = pair_count - len(failures)
    return {
        "worker_count": len(ids),
        "pair_count": pair_count,
        "direct_conflict_pairs": direct_conflict_pairs,
        "passed_pairs": passed,
        "failed_pairs": len(failures),
        "pairwise_composition_accuracy": _ratio(passed, pair_count),
    }, failures


def _turn_eval() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    details: list[dict[str, Any]] = []
    for case in TURN_CASES:
        decision = classify_turn_intent(
            str(case["message"]),
            case["state"],  # type: ignore[arg-type]
        )
        passed = (
            decision.turn_kind == case["turn_kind"]
            and decision.selection_required is case["selection_required"]
            and decision.reroute_required is case["reroute_required"]
        )
        details.append(
            {
                "id": case["id"],
                "turn_kind": decision.turn_kind,
                "selection_required": decision.selection_required,
                "reroute_required": decision.reroute_required,
                "reason_codes": list(decision.reason_codes),
                "passed": passed,
            }
        )
    return {
        "cases": len(details),
        "passed_cases": sum(bool(item["passed"]) for item in details),
        "turn_case_accuracy": _ratio(
            sum(bool(item["passed"]) for item in details),
            len(details),
        ),
    }, details


def _gate_results(values: Mapping[str, float]) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for metric, (operator, threshold) in THRESHOLDS.items():
        value = float(values[metric])
        passed = value >= threshold if operator == ">=" else value <= threshold
        gates.append(
            {
                "metric": metric,
                "value": value,
                "operator": operator,
                "threshold": threshold,
                "passed": passed,
            }
        )
    return gates


def run_full_roster_selection_eval(
    *,
    candidate_limit: int = DEFAULT_CANDIDATE_LIMIT,
) -> dict[str, Any]:
    """Run the bounded, offline, complete-roster contract evaluation."""

    if (
        isinstance(candidate_limit, bool)
        or not isinstance(candidate_limit, int)
        or not MIN_CANDIDATE_LIMIT <= candidate_limit <= MAX_CANDIDATE_LIMIT
    ):
        raise ValueError(
            f"candidate_limit must be an integer from {MIN_CANDIDATE_LIMIT} "
            f"through {MAX_CANDIDATE_LIMIT}"
        )
    manifest, cards = _routing_cards()
    participation = _retrieval_participation(cards)
    probe_metrics, probe_details = _probe_retrieval(
        cards,
        candidate_limit=candidate_limit,
    )
    curated_metrics, curated_details = _curated_retrieval(
        cards,
        candidate_limit=candidate_limit,
    )
    compatibility_metrics, compatibility_details = _compatibility_eval(cards)
    pairwise_metrics, pairwise_failures = _pairwise_composition_eval(cards)
    turn_metrics, turn_details = _turn_eval()

    values = {
        "lexical_participation_rate": participation["lexical_participation_rate"],
        "semantic_participation_rate": participation["semantic_participation_rate"],
        "target_candidate_recall": probe_metrics["target_candidate_recall"],
        "target_recall_at_10": probe_metrics["target_recall_at_10"],
        "curated_case_accuracy": curated_metrics["curated_case_accuracy"],
        "abstention_accuracy": curated_metrics["abstention_accuracy"],
        "compatibility_case_accuracy": compatibility_metrics["compatibility_case_accuracy"],
        "pairwise_composition_accuracy": pairwise_metrics["pairwise_composition_accuracy"],
        "turn_case_accuracy": turn_metrics["turn_case_accuracy"],
        "identity_leak_rate": probe_metrics["identity_leak_rate"],
        "preferred_sentence_copy_rate": probe_metrics["preferred_sentence_copy_rate"],
    }
    gates = _gate_results(values)
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "evidence": {
            "kind": EVIDENCE_KIND,
            "network_used": False,
            "inference_used": False,
            "live_host_used": False,
            "task_outcomes_measured": False,
            "superiority_claimed": False,
            "limitation": (
                "This report measures packaged routing contracts and deterministic "
                "control behavior only. It cannot establish task quality or "
                "superiority over a native host or another router."
            ),
        },
        "roster": {
            "manifest_total": manifest["counts"]["total"],
            "manifest_approved": manifest["counts"]["approved"],
            "manifest_quarantined": manifest["counts"]["quarantined"],
            "manifest_retired": manifest["counts"]["retired"],
            "packaged_contractors": len(KNOWN_CONTRACTORS_BY_SLUG),
            "workforce_total": len(cards),
            "approved_enabled": len(cards),
            "division_count": len({str(card["division"]) for card in cards}),
            "source_revision": manifest["source"]["revision"],
        },
        "candidate_limit": candidate_limit,
        "metrics": {
            "participation": participation,
            "probe_retrieval": probe_metrics,
            "curated_retrieval": curated_metrics,
            "compatibility": compatibility_metrics,
            "pairwise_composition": pairwise_metrics,
            "turn_state": turn_metrics,
        },
        "thresholds": {
            metric: {"operator": operator, "threshold": threshold}
            for metric, (operator, threshold) in THRESHOLDS.items()
        },
        "gates": gates,
        "passed": all(bool(gate["passed"]) for gate in gates),
        "details": {
            "probe_retrieval": probe_details,
            "curated_retrieval": curated_details,
            "compatibility": compatibility_details,
            "pairwise_composition_failures": pairwise_failures,
            "turn_state": turn_details,
        },
    }


__all__ = [
    "DEFAULT_CANDIDATE_LIMIT",
    "EVIDENCE_KIND",
    "MAX_CANDIDATE_LIMIT",
    "MIN_CANDIDATE_LIMIT",
    "SCHEMA",
    "THRESHOLDS",
    "VERSION",
    "run_full_roster_selection_eval",
]
