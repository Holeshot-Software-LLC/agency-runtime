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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from heapq import nlargest
from itertools import pairwise
from types import MappingProxyType
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
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
_FEATURE_CACHE_ENTRIES = 65_536
_TEXT_CACHE_ENTRIES = 32_768
_AgentSignature = tuple[tuple[str, tuple[str, ...]], ...]
_CatalogSignatures = tuple[_AgentSignature, ...]
_SparseItems = tuple[tuple[int, float], ...]
_SparseVector = Mapping[int, float]


@dataclass(frozen=True, slots=True)
class _CatalogIndex:
    """Immutable semantic features and collision-free support postings."""

    identities: tuple[str, ...]
    embeddings: tuple[_SparseVector, ...]
    support_postings: Mapping[str, tuple[int, ...]]
    strong_support_postings: Mapping[str, tuple[int, ...]]


class RevisionedCatalog(list[dict[str, Any]]):
    """List-compatible catalog bound to one exact routing revision."""

    __slots__ = ("revision",)

    def __init__(self, values: Iterable[dict[str, Any]], *, revision: str) -> None:
        if not isinstance(revision, str) or not revision.strip() or len(revision) > 256:
            raise ValueError("catalog revision must be non-empty text of at most 256 characters")
        super().__init__(values)
        self.revision = revision.strip()


_CATALOG_CACHE: OrderedDict[_CatalogSignatures, _CatalogIndex] = OrderedDict()
_REVISION_CATALOG_CACHE: OrderedDict[str, _CatalogIndex] = OrderedDict()
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


@lru_cache(maxsize=_TEXT_CACHE_ENTRIES)
def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in _WORD_RE.findall(text.casefold().replace("_", " ").replace("-", " "))
        if len(token) >= 2 and token not in _STOPWORDS
    )


@lru_cache(maxsize=_FEATURE_CACHE_ENTRIES)
def _feature_index(feature: str) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % _VECTOR_DIMENSIONS


def _add(vector: dict[int, float], feature: str, weight: float) -> None:
    index = _feature_index(feature)
    vector[index] = vector.get(index, 0.0) + weight


@lru_cache(maxsize=_TEXT_CACHE_ENTRIES)
def _cached_text_embedding(values: tuple[str, ...], weight: float) -> _SparseItems:
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
    return tuple(vector.items())


def _embed_texts(values: Sequence[str], *, weight: float) -> dict[int, float]:
    return dict(_cached_text_embedding(tuple(values), weight))


@lru_cache(maxsize=_TEXT_CACHE_ENTRIES)
def _support_terms(values: tuple[str, ...]) -> frozenset[str]:
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


def _agent_signature(agent: dict[str, Any]) -> _AgentSignature:
    return tuple((field, _values(agent.get(field))) for field in _SIGNATURE_FIELDS)


def _agent_embedding(
    signature: tuple[tuple[str, tuple[str, ...]], ...],
) -> _SparseVector:
    weights = dict(_FIELD_WEIGHTS)
    vector: dict[int, float] = {}
    seen_slug: tuple[str, ...] | None = None
    for field, values in signature:
        if field in {"slug", "agent_slug"}:
            if seen_slug == values:
                continue
            seen_slug = values
        _merge_vectors(vector, _embed_texts(values, weight=weights[field]))
    # Keep the compiled side addressable by feature. Warm retrieval queries are
    # normally much smaller than an agent vector, so probing the compiled map
    # avoids walking every agent feature for every candidate.
    return MappingProxyType(dict(_normalized(vector)))


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


def _postings(terms: Sequence[frozenset[str]]) -> Mapping[str, tuple[int, ...]]:
    mutable: dict[str, list[int]] = {}
    for index, row_terms in enumerate(terms):
        for term in row_terms:
            mutable.setdefault(term, []).append(index)
    return MappingProxyType({term: tuple(indexes) for term, indexes in mutable.items()})


def _compile_catalog_index(
    signatures: _CatalogSignatures,
    identities: tuple[str, ...],
) -> _CatalogIndex:
    support = tuple(_agent_support(signature) for signature in signatures)
    return _CatalogIndex(
        identities=identities,
        embeddings=tuple(_agent_embedding(signature) for signature in signatures),
        support_postings=_postings(tuple(item[0] for item in support)),
        strong_support_postings=_postings(tuple(item[1] for item in support)),
    )


def _catalog_index(
    catalog: Sequence[dict[str, Any]],
    *,
    catalog_revision: str = "",
) -> _CatalogIndex:
    """Return features keyed by exact revision or mutation-safe content.

    Production routing supplies its context fingerprint as ``catalog_revision``.
    That fingerprint already binds configuration, policy, capability context,
    and the complete roster snapshot. Direct library callers that do not have
    such an authority continue to use the full content key.
    """

    revision = catalog_revision.strip()
    identities = tuple(agent_identity(agent) for agent in catalog)
    if revision:
        with _CATALOG_CACHE_LOCK:
            cached = _REVISION_CATALOG_CACHE.get(revision)
            if cached is not None:
                if cached.identities != identities:
                    raise ValueError("catalog revision was reused with different agent identities")
                _REVISION_CATALOG_CACHE.move_to_end(revision)
                return cached

    signatures = tuple(_agent_signature(agent) for agent in catalog)
    with _CATALOG_CACHE_LOCK:
        compiled = _CATALOG_CACHE.get(signatures)
        if compiled is not None:
            _CATALOG_CACHE.move_to_end(signatures)
    if compiled is None:
        compiled = _compile_catalog_index(signatures, identities)
    elif compiled.identities != identities:
        # Identity is part of every signature, so this is only a defensive
        # collision guard against an internal cache corruption.
        raise RuntimeError("semantic catalog cache identity mismatch")

    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE[signatures] = compiled
        _CATALOG_CACHE.move_to_end(signatures)
        if revision:
            extant = _REVISION_CATALOG_CACHE.get(revision)
            if extant is not None and extant.identities != identities:
                raise ValueError("catalog revision was reused with different agent identities")
            _REVISION_CATALOG_CACHE[revision] = compiled
            _REVISION_CATALOG_CACHE.move_to_end(revision)
        while len(_CATALOG_CACHE) > _CATALOG_CACHE_ENTRIES:
            _CATALOG_CACHE.popitem(last=False)
        while len(_REVISION_CATALOG_CACHE) > _CATALOG_CACHE_ENTRIES:
            _REVISION_CATALOG_CACHE.popitem(last=False)
    return compiled


def _cosine(
    left: Mapping[int, float],
    right: Mapping[int, float],
) -> float:
    if len(left) <= len(right):
        return sum(weight * right.get(index, 0.0) for index, weight in left.items())
    return sum(weight * left.get(index, 0.0) for index, weight in right.items())


def semantic_retrieve(
    query: str,
    catalog: Sequence[dict[str, Any]],
    *,
    limit: int = 40,
    catalog_revision: str = "",
) -> tuple[list[dict[str, Any]], list[float]]:
    """Return positive deterministic embedding matches from the full roster."""

    if limit <= 0 or not catalog:
        return [], []
    if len(catalog) > MAX_ACTIVE_ROSTER_SIZE:
        raise ValueError(f"catalog cannot contain more than {MAX_ACTIVE_ROSTER_SIZE} agents")
    query_vector = dict(_normalized(_embed_texts((query,), weight=1.0)))
    query_support = _support_terms((query,))
    if not query_vector or not query_support:
        return [], []
    revision = catalog_revision or str(getattr(catalog, "revision", "") or "")
    index = _catalog_index(catalog, catalog_revision=revision)
    supported: set[int] = set()
    strongly_supported: set[int] = set()
    for term in query_support:
        supported.update(index.support_postings.get(term, ()))
        strongly_supported.update(index.strong_support_postings.get(term, ()))
    candidate_indexes = sorted(supported.intersection(strongly_supported))
    scored = [
        (score, agent_identity(agent), row_index, agent)
        for row_index in candidate_indexes
        if (
            (agent := catalog[row_index]) is not None
            and (score := _cosine(query_vector, index.embeddings[row_index])) >= _MIN_SEMANTIC_SCORE
        )
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
    lexical_ids: tuple[str, ...]
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
    return agent_identity(agent)


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
    catalog_revision: str = "",
) -> CandidateUnion:
    """Combine positive lexical and embedding recall without zero-score padding."""

    if limit <= 0 or not catalog:
        return CandidateUnion((), (), (), len(catalog), 0, 0, 0)
    inferred_revision = catalog_revision or str(getattr(catalog, "revision", "") or "")
    bounded_catalog = catalog if isinstance(catalog, list) else list(catalog)
    lexical_agents, lexical_scores = lexical_retriever(query, bounded_catalog, limit)
    lexical = [
        (agent, score)
        for agent, score in zip(lexical_agents, lexical_scores, strict=True)
        if score > 0
    ]
    lexical_ids = tuple(slug for agent, _score in lexical if (slug := _agent_id(agent)))
    semantic_agents, semantic_scores = semantic_retrieve(
        query,
        bounded_catalog,
        limit=limit,
        catalog_revision=inferred_revision,
    )
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
        lexical_ids,
        len(bounded_catalog),
        len(lexical),
        len(semantic_agents),
        len(hard_negatives),
    )


def clear_semantic_retrieval_cache() -> None:
    """Clear deterministic embedding state for tests and roster invalidation."""

    with _CATALOG_CACHE_LOCK:
        _CATALOG_CACHE.clear()
        _REVISION_CATALOG_CACHE.clear()
    _tokens.cache_clear()
    _feature_index.cache_clear()
    _cached_text_embedding.cache_clear()
    _support_terms.cache_clear()


__all__ = [
    "CandidateUnion",
    "RevisionedCatalog",
    "clear_semantic_retrieval_cache",
    "retrieve_candidate_union",
    "semantic_retrieve",
]
