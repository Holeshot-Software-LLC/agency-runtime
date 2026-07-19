"""Deterministic full-roster metadata embeddings and candidate union.

The local embedding is intentionally dependency-free and reproducible.  It
projects curated routing contracts into a sparse concept/word/subword vector,
so every enabled agent participates even when no external embedding provider
is configured.  It is recall evidence, not an inference receipt; the semantic
judge remains the authority whenever inference is configured.
"""

from __future__ import annotations

import hashlib
import math
import re
import threading
from collections import OrderedDict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from heapq import nlargest
from itertools import pairwise
from typing import Any

from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.selector.candidate_narrow import pre_narrow

_WORD_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "for",
        "from",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
        "agent",
        "help",
        "need",
        "specialist",
        "work",
    }
)
_CONCEPT_ALIASES: dict[str, tuple[str, ...]] = {
    "api": ("backend", "integration", "interface"),
    "auth": ("authentication", "authorization", "identity", "security"),
    "bug": ("debug", "defect", "diagnosis", "testing"),
    "ci": ("automation", "deployment", "pipeline", "testing"),
    "cli": ("command", "interface", "terminal"),
    "database": ("data", "postgres", "query", "sql", "storage"),
    "docs": ("documentation", "technical", "writing"),
    "frontend": ("accessibility", "design", "interface", "ui"),
    "incident": ("operations", "reliability", "response", "security"),
    "latency": ("optimization", "performance", "profiling"),
    "marketing": ("campaign", "content", "growth", "seo"),
    "mobile": ("android", "ios", "application"),
    "payment": ("billing", "commerce", "finance", "transaction"),
    "privacy": ("compliance", "data", "governance", "security"),
    "review": ("analysis", "audit", "quality"),
    "test": ("automation", "quality", "verification"),
    "ui": ("accessibility", "design", "frontend", "interface", "ux"),
}
_FIELD_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("slug", 3.0),
    ("agent_slug", 3.0),
    ("name", 3.0),
    ("capabilities", 3.0),
    ("categories", 2.5),
    ("task_types", 2.5),
    ("preferred_when", 2.0),
    ("description", 1.5),
    ("division", 1.0),
    ("tool_affinity", 1.0),
    ("required_tools", 1.0),
    ("expected_output_contract", 1.0),
)
_SIGNATURE_FIELDS = tuple(field for field, _weight in _FIELD_WEIGHTS)
_STRONG_SUPPORT_FIELDS = frozenset(
    {
        "slug",
        "agent_slug",
        "name",
        "capabilities",
        "categories",
        "task_types",
        "preferred_when",
        "tool_affinity",
        "required_tools",
    }
)
_VECTOR_DIMENSIONS = 2_048
_MIN_SEMANTIC_SCORE = 0.08
_CATALOG_CACHE_ENTRIES = 2
_CATALOG_CACHE: OrderedDict[
    tuple[tuple[tuple[str, tuple[str, ...]], ...], ...],
    tuple[
        tuple[tuple[tuple[int, float], ...], ...],
        tuple[frozenset[str], ...],
        tuple[frozenset[str], ...],
    ],
] = OrderedDict()
_CATALOG_CACHE_LOCK = threading.RLock()


def _values(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item or "").strip())
    if isinstance(value, dict):
        return ()
    if isinstance(value, Iterable) and not isinstance(value, bytes):
        return tuple(str(item) for item in value if str(item or "").strip())
    return (str(value),)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in _WORD_RE.findall(text.casefold().replace("_", " ").replace("-", " "))
        if len(token) >= 2 and token not in _STOPWORDS
    )


def _feature_index(feature: str) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % _VECTOR_DIMENSIONS


def _add(vector: dict[int, float], feature: str, weight: float) -> None:
    index = _feature_index(feature)
    vector[index] = vector.get(index, 0.0) + weight


def _embed_texts(values: Sequence[str], *, weight: float) -> dict[int, float]:
    vector: dict[int, float] = {}
    for value in values:
        ordered = _tokens(value)
        for token in ordered:
            _add(vector, f"w:{token}", weight)
            for alias in _CONCEPT_ALIASES.get(token, ()):
                _add(vector, f"w:{alias}", weight * 0.65)
            padded = f"^{token}$"
            for index in range(max(0, len(padded) - 2)):
                _add(vector, f"g:{padded[index : index + 3]}", weight * 0.12)
        for left, right in pairwise(ordered):
            _add(vector, f"b:{left}:{right}", weight * 0.8)
    return vector


def _support_terms(values: Sequence[str]) -> frozenset[str]:
    """Return collision-free evidence that can support one semantic match.

    Character n-grams improve ranking once a real relationship is present, but
    they are not independently meaningful. For example, ``cook`` shares
    ``ook`` with ``runbook`` and ``weekend`` shares ``end`` with other words.
    Requiring an exact word, declared concept alias, or stable word prefix keeps
    feature-hash and incidental substring collisions from manufacturing routing
    signal while retaining bounded morphology-aware recall.
    """

    terms: set[str] = set()
    for value in values:
        for token in _tokens(value):
            terms.add(f"word:{token}")
            terms.update(f"word:{alias}" for alias in _CONCEPT_ALIASES.get(token, ()))
            if len(token) >= 6:
                terms.add(f"prefix:{token[:5]}")
    return frozenset(terms)


def _merge_vectors(target: dict[int, float], source: dict[int, float]) -> None:
    for index, weight in source.items():
        target[index] = target.get(index, 0.0) + weight


def _normalized(vector: dict[int, float]) -> tuple[tuple[int, float], ...]:
    magnitude = math.sqrt(sum(weight * weight for weight in vector.values()))
    if magnitude <= 0:
        return ()
    return tuple(sorted((index, weight / magnitude) for index, weight in vector.items()))


def _agent_signature(agent: dict[str, Any]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((field, _values(agent.get(field))) for field in _SIGNATURE_FIELDS)


def _agent_embedding(
    signature: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[tuple[int, float], ...]:
    weights = dict(_FIELD_WEIGHTS)
    vector: dict[int, float] = {}
    seen_slug: tuple[str, ...] | None = None
    for field, values in signature:
        if field in {"slug", "agent_slug"}:
            if seen_slug == values:
                continue
            seen_slug = values
        _merge_vectors(vector, _embed_texts(values, weight=weights[field]))
    return _normalized(vector)


def _agent_support(
    signature: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[frozenset[str], frozenset[str]]:
    terms: set[str] = set()
    strong_terms: set[str] = set()
    seen_slug: tuple[str, ...] | None = None
    for field, values in signature:
        if field in {"slug", "agent_slug"}:
            if seen_slug == values:
                continue
            seen_slug = values
        field_terms = _support_terms(values)
        terms.update(field_terms)
        if field in _STRONG_SUPPORT_FIELDS:
            strong_terms.update(field_terms)
    return frozenset(terms), frozenset(strong_terms)


def _catalog_embeddings(
    catalog: Sequence[dict[str, Any]],
) -> tuple[
    tuple[tuple[tuple[int, float], ...], ...],
    tuple[frozenset[str], ...],
    tuple[frozenset[str], ...],
]:
    signatures = tuple(_agent_signature(agent) for agent in catalog)
    with _CATALOG_CACHE_LOCK:
        cached = _CATALOG_CACHE.get(signatures)
        if cached is not None:
            _CATALOG_CACHE.move_to_end(signatures)
            return cached
    support = tuple(_agent_support(signature) for signature in signatures)
    compiled = (
        tuple(_agent_embedding(signature) for signature in signatures),
        tuple(item[0] for item in support),
        tuple(item[1] for item in support),
    )
    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE[signatures] = compiled
        _CATALOG_CACHE.move_to_end(signatures)
        while len(_CATALOG_CACHE) > _CATALOG_CACHE_ENTRIES:
            _CATALOG_CACHE.popitem(last=False)
    return compiled


def _cosine(
    left: tuple[tuple[int, float], ...],
    right: tuple[tuple[int, float], ...],
) -> float:
    left_map = dict(left)
    return sum(left_map.get(index, 0.0) * weight for index, weight in right)


def semantic_retrieve(
    query: str,
    catalog: Sequence[dict[str, Any]],
    *,
    limit: int = 40,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Return positive deterministic embedding matches from the full roster."""

    if limit <= 0 or not catalog:
        return [], []
    if len(catalog) > MAX_ACTIVE_ROSTER_SIZE:
        raise ValueError(f"catalog cannot contain more than {MAX_ACTIVE_ROSTER_SIZE} agents")
    query_vector = _normalized(_embed_texts((query,), weight=1.0))
    query_support = _support_terms((query,))
    if not query_vector or not query_support:
        return [], []
    embeddings, support_terms, strong_support_terms = _catalog_embeddings(catalog)
    scored = [
        (score, str(agent.get("slug") or agent.get("agent_slug") or ""), index, agent)
        for index, (agent, vector, support, strong_support) in enumerate(
            zip(
                catalog,
                embeddings,
                support_terms,
                strong_support_terms,
                strict=True,
            )
        )
        if not query_support.isdisjoint(support)
        # A lone word in narrative prose or an output template is too weak to
        # establish domain intent. It may improve ranking only after the query
        # also matches an identity, capability, category, task, preference, or
        # tool field. This rejects polysemes such as food "cook" matching an
        # Unreal build receipt while preserving "Unreal cook pipeline".
        if not query_support.isdisjoint(strong_support)
        if (score := _cosine(query_vector, vector)) >= _MIN_SEMANTIC_SCORE
    ]
    ranked = nlargest(
        min(limit, len(scored)),
        scored,
        key=lambda item: (item[0], item[1], -item[2]),
    )
    return [agent for _score, _slug, _index, agent in ranked], [
        round(score, 6) for score, _slug, _index, _agent in ranked
    ]


@dataclass(frozen=True, slots=True)
class CandidateUnion:
    """One bounded retrieval union and explainable source counts."""

    candidates: tuple[dict[str, Any], ...]
    scores: tuple[float, ...]
    full_roster_count: int
    lexical_count: int
    semantic_count: int
    hard_negative_count: int

    def evidence(self) -> dict[str, int | str]:
        return {
            "mode": "lexical+deterministic-metadata-embedding+hard-negatives",
            "full_roster_count": self.full_roster_count,
            "candidate_union_count": len(self.candidates),
            "lexical_count": self.lexical_count,
            "semantic_count": self.semantic_count,
            "hard_negative_count": self.hard_negative_count,
        }


def _agent_id(agent: dict[str, Any]) -> str:
    return str(agent.get("slug") or agent.get("agent_slug") or "").strip()


def _hard_negatives(
    catalog: Sequence[dict[str, Any]],
    selected_ids: set[str],
    anchors: Sequence[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    anchor_divisions = {str(agent.get("division") or "") for agent in anchors}
    anchor_categories = {
        str(category) for agent in anchors for category in _values(agent.get("categories"))
    }
    negatives: list[dict[str, Any]] = []
    for agent in catalog:
        slug = _agent_id(agent)
        if not slug or slug in selected_ids:
            continue
        categories = set(_values(agent.get("categories")))
        if str(agent.get("division") or "") in anchor_divisions or categories.intersection(
            anchor_categories
        ):
            negatives.append(agent)
            selected_ids.add(slug)
            if len(negatives) >= limit:
                break
    return negatives


def retrieve_candidate_union(
    query: str,
    catalog: Sequence[dict[str, Any]],
    *,
    limit: int = 80,
    lexical_retriever: Callable[
        [str, list[dict[str, Any]], int],
        tuple[list[dict[str, Any]], list[float]],
    ] = pre_narrow,
) -> CandidateUnion:
    """Combine positive lexical and embedding recall without zero-score padding."""

    if limit <= 0 or not catalog:
        return CandidateUnion((), (), len(catalog), 0, 0, 0)
    bounded_catalog = list(catalog)
    lexical_agents, lexical_scores = lexical_retriever(query, bounded_catalog, limit)
    lexical = [
        (agent, score)
        for agent, score in zip(lexical_agents, lexical_scores, strict=True)
        if score > 0
    ]
    semantic_agents, semantic_scores = semantic_retrieve(query, bounded_catalog, limit=limit)
    combined: dict[str, tuple[dict[str, Any], float, bool, bool]] = {}
    for agent, score in lexical:
        slug = _agent_id(agent)
        if slug:
            combined[slug] = (agent, score, True, False)
    for agent, score in zip(semantic_agents, semantic_scores, strict=True):
        slug = _agent_id(agent)
        if not slug:
            continue
        current = combined.get(slug)
        semantic_weight = score * 12.0
        if current is None:
            combined[slug] = (agent, semantic_weight, False, True)
        else:
            combined[slug] = (
                current[0],
                current[1] + semantic_weight,
                current[2],
                True,
            )
    ranked_all = sorted(
        combined.items(),
        key=lambda item: (-item[1][1], item[0]),
    )
    hard_negative_budget = min(8, max(1, limit // 5)) if limit >= 3 else 0
    positive_limit = max(1, limit - hard_negative_budget)
    ranked = ranked_all[:positive_limit]
    candidates = [item[1][0] for item in ranked]
    scores = [round(item[1][1], 6) for item in ranked]
    selected_ids = {item[0] for item in ranked}
    hard_negatives = _hard_negatives(
        bounded_catalog,
        selected_ids,
        candidates[:8],
        limit=hard_negative_budget,
    )
    candidates.extend(hard_negatives)
    scores.extend(0.0 for _agent in hard_negatives)
    if len(candidates) < limit:
        for slug, item in ranked_all[positive_limit:]:
            if slug in selected_ids:
                continue
            candidates.append(item[0])
            scores.append(round(item[1], 6))
            selected_ids.add(slug)
            if len(candidates) >= limit:
                break
    return CandidateUnion(
        tuple(candidates),
        tuple(scores),
        len(bounded_catalog),
        len(lexical),
        len(semantic_agents),
        len(hard_negatives),
    )


def clear_semantic_retrieval_cache() -> None:
    """Clear deterministic embedding state for tests and roster invalidation."""

    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE.clear()


__all__ = [
    "CandidateUnion",
    "clear_semantic_retrieval_cache",
    "retrieve_candidate_union",
    "semantic_retrieve",
]
