"""Deterministic metadata-aware candidate narrowing before the LLM judge.

The narrower's job is recall: retain the specialists that a semantic judge may
need while keeping obviously unrelated agents out of its context.  Matching is
limited to complete tokens and phrases.  In particular, short identifiers such
as ``pr`` and ``ui`` never match substrings such as ``spring`` or ``build``.
"""

from __future__ import annotations

import re
import threading
from collections import OrderedDict
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from heapq import nsmallest
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE

_WORD_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "work",
        "agent",
        "agents",
        "specialist",
        "specialists",
        "help",
        "need",
        "want",
        "can",
        "you",
        "me",
        "my",
        "our",
        "we",
    }
)
_TOKEN_ALIASES = {
    "benchmarking": "benchmark",
    "benchmarks": "benchmark",
    "builds": "build",
    "coordinates": "coordinate",
    "components": "component",
    "debugging": "debug",
    "dependencies": "dependency",
    "decomposes": "decompose",
    "designs": "design",
    "docs": "document",
    "documentation": "document",
    "endpoints": "endpoint",
    "features": "feature",
    "fixes": "fix",
    "forecasting": "forecast",
    "forecasts": "forecast",
    "analyze": "analysis",
    "analyzes": "analysis",
    "analyzing": "analysis",
    "implementation": "implement",
    "implements": "implement",
    "interactions": "interaction",
    "optimizes": "optimize",
    "paths": "path",
    "pipelines": "pipeline",
    "prioritizes": "prioritize",
    "profiles": "profile",
    "profiling": "profile",
    "refactoring": "refactor",
    "requirements": "requirement",
    "reviews": "review",
    "results": "result",
    "runbooks": "runbook",
    "servers": "server",
    "testing": "test",
    "tests": "test",
    "tools": "tool",
    "transports": "transport",
    "vulnerabilities": "vulnerability",
    "workflows": "workflow",
    "writing": "write",
    "writes": "write",
}
_AMBIGUOUS_SINGLE_TOKENS = frozenset(
    {
        "component",
        "design",
        "layout",
        "plan",
        "review",
        "test",
    }
)

# Field weights reflect how deliberately each piece of roster metadata is
# curated.  Capabilities and names carry more signal than prose descriptions.
_FIELD_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("slug", 4.0),
    ("agent_slug", 4.0),
    ("name", 4.0),
    ("capabilities", 3.0),
    ("categories", 2.5),
    ("tool_affinity", 2.0),
    ("division", 1.5),
    ("description", 1.0),
)

_AgentSignature = tuple[tuple[str, tuple[str, ...]], ...]
_CompiledScoreInputs = tuple[
    tuple[tuple[str, float], ...],
    frozenset[str],
    tuple[tuple[tuple[str, ...], float], ...],
]
_CatalogSignatures = tuple[_AgentSignature, ...]
_CompiledCatalog = tuple[_CompiledScoreInputs, ...]

# Keep the current and immediately preceding catalog revisions. A content key
# lets independently materialized Store snapshots reuse the same compiled index
# while exact signatures make in-place caller mutations invalidate safely.
_COMPILED_CATALOG_CACHE_MAX_ENTRIES = 2
_COMPILED_CATALOG_CACHE: OrderedDict[_CatalogSignatures, _CompiledCatalog] = OrderedDict()
_COMPILED_CATALOG_CACHE_LOCK = threading.RLock()
_IDENTITY_CATALOG_CACHE_MAX_ENTRIES = 4


@dataclass(frozen=True, slots=True)
class _IdentityCatalogEntry:
    """Mutation-safe fast path for one repeatedly used catalog object."""

    catalog: list[dict[str, Any]]
    snapshot: list[dict[str, Any]]
    compiled: _CompiledCatalog


_IDENTITY_CATALOG_CACHE: OrderedDict[int, _IdentityCatalogEntry] = OrderedDict()


@lru_cache(maxsize=8192)
def _ordered_tokens(text: str) -> tuple[str, ...]:
    """Return normalized tokens while preserving their order."""
    return tuple(
        _TOKEN_ALIASES.get(token, token)
        for token in _WORD_RE.findall(text.lower())
        if len(token) >= 2 and token not in _STOPWORDS
    )


@lru_cache(maxsize=32768)
def _normalized_field_tokens(value: str) -> tuple[str, ...]:
    """Normalize immutable roster metadata once across routing requests."""
    return _ordered_tokens(value.replace("_", " ").replace("-", " "))


def tokenize(text: str) -> set[str]:
    """Tokenize text into complete, normalized terms for overlap scoring."""
    return set(_ordered_tokens(text.replace("_", " ").replace("-", " ")))


def _field_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    # Roster metadata overwhelmingly uses lists and tuples. Keep that hot path
    # ahead of the comparatively expensive generic ``Iterable`` ABC check;
    # callers with other iterable types retain the existing behavior below.
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if item is not None)
    if isinstance(value, dict):
        return ()
    if isinstance(value, Iterable) and not isinstance(value, bytes):
        return tuple(str(item) for item in value if item is not None)
    return (str(value),)


def _agent_signature(
    agent: dict[str, Any],
) -> _AgentSignature:
    """Build a stable, mutation-aware key for routing-relevant metadata."""
    return tuple((field, _field_values(agent.get(field))) for field, _weight in _FIELD_WEIGHTS)


@lru_cache(maxsize=MAX_ACTIVE_ROSTER_SIZE)
def _compiled_agent_score_inputs(
    signature: _AgentSignature,
) -> _CompiledScoreInputs:
    """Compile immutable token weights and phrase bonuses for one agent."""
    weights = dict(_FIELD_WEIGHTS)
    token_weights: dict[str, float] = {}
    strong_single_tokens: set[str] = set()
    phrases: list[tuple[tuple[str, ...], float]] = []
    seen_fields: set[tuple[str, tuple[str, ...]]] = set()
    seen_slug_aliases: set[tuple[str, ...]] = set()

    for field, values in signature:
        weight = weights[field]
        field_tokens_seen: set[str] = set()
        for value in values:
            field_order = _normalized_field_tokens(value)
            if not field_order or (field, field_order) in seen_fields:
                continue
            if field in {"slug", "agent_slug"} and field_order in seen_slug_aliases:
                continue
            seen_fields.add((field, field_order))
            if field in {"slug", "agent_slug"}:
                seen_slug_aliases.add(field_order)
            for token in set(field_order):
                if token not in field_tokens_seen:
                    token_weights[token] = token_weights.get(token, 0.0) + weight
                    field_tokens_seen.add(token)
            if len(field_order) > 1:
                phrases.append((field_order, weight * min(len(field_order), 3) * 0.75))
            elif field != "description" and field_order[0] not in _AMBIGUOUS_SINGLE_TOKENS:
                strong_single_tokens.add(field_order[0])

    return (
        tuple(token_weights.items()),
        frozenset(strong_single_tokens),
        tuple(phrases),
    )


def _compiled_catalog_score_inputs(
    catalog: list[dict[str, Any]],
) -> _CompiledCatalog:
    """Return a bounded, content-keyed compiled selector index.

    Per-agent caching alone is insufficient at the supported 10,000-agent
    boundary: an undersized LRU evicts the start of the same roster before the
    next request reaches it. Catalog signatures provide one mutation-safe
    lookup per request and also work when Store materializes a fresh list.
    """

    # Plain validated roster dictionaries can use an identity fast path. Keep
    # mapping subclasses on the content path because callers may attach custom
    # access semantics (the concurrency probe intentionally does so).
    identity_cacheable = all(type(agent) is dict for agent in catalog)
    identity_key = id(catalog)
    if identity_cacheable:
        with _COMPILED_CATALOG_CACHE_LOCK:
            identity_entry = _IDENTITY_CATALOG_CACHE.get(identity_key)
        if (
            identity_entry is not None
            and identity_entry.catalog is catalog
            and catalog == identity_entry.snapshot
        ):
            with _COMPILED_CATALOG_CACHE_LOCK:
                if _IDENTITY_CATALOG_CACHE.get(identity_key) is identity_entry:
                    _IDENTITY_CATALOG_CACHE.move_to_end(identity_key)
            return identity_entry.compiled

    signatures = tuple(_agent_signature(agent) for agent in catalog)
    with _COMPILED_CATALOG_CACHE_LOCK:
        cached = _COMPILED_CATALOG_CACHE.get(signatures)
        if cached is not None:
            _COMPILED_CATALOG_CACHE.move_to_end(signatures)
    compiled = cached or tuple(_compiled_agent_score_inputs(signature) for signature in signatures)
    snapshot = None
    if identity_cacheable:
        try:
            snapshot = deepcopy(catalog)
        except Exception:
            # Direct callers may attach opaque values outside the routing
            # fields. They remain routable but cannot use identity reuse.
            snapshot = None
    with _COMPILED_CATALOG_CACHE_LOCK:
        _COMPILED_CATALOG_CACHE[signatures] = compiled
        _COMPILED_CATALOG_CACHE.move_to_end(signatures)
        if snapshot is not None:
            _IDENTITY_CATALOG_CACHE[identity_key] = _IdentityCatalogEntry(
                catalog,
                snapshot,
                compiled,
            )
            _IDENTITY_CATALOG_CACHE.move_to_end(identity_key)
        while len(_COMPILED_CATALOG_CACHE) > _COMPILED_CATALOG_CACHE_MAX_ENTRIES:
            _COMPILED_CATALOG_CACHE.popitem(last=False)
        while len(_IDENTITY_CATALOG_CACHE) > _IDENTITY_CATALOG_CACHE_MAX_ENTRIES:
            _IDENTITY_CATALOG_CACHE.popitem(last=False)
    return compiled


def _clear_compiled_score_caches() -> None:
    """Clear narrowing compilation state for deterministic tests and evals."""

    with _COMPILED_CATALOG_CACHE_LOCK:
        _COMPILED_CATALOG_CACHE.clear()
        _IDENTITY_CATALOG_CACHE.clear()
    _compiled_agent_score_inputs.cache_clear()


def _contains_phrase(query: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    """Return whether ``phrase`` occurs contiguously in ``query``."""
    if len(phrase) < 2 or len(phrase) > len(query):
        return False
    width = len(phrase)
    return any(query[index : index + width] == phrase for index in range(len(query) - width + 1))


def score_agent(
    agent: dict[str, Any],
    query_tokens: set[str],
    *,
    query_text: str | None = None,
    _compiled_inputs: _CompiledScoreInputs | None = None,
    _query_phrases: frozenset[tuple[str, ...]] | None = None,
) -> float:
    """Score an agent using exact metadata tokens and contiguous phrases.

    ``query_tokens`` remains part of the public signature for compatibility.
    ``pre_narrow`` also supplies ``query_text`` so multi-word capabilities such
    as ``code review`` receive a phrase bonus without using substring matches.
    """
    if not query_tokens:
        return 0.0

    query_order = _ordered_tokens(query_text) if query_text is not None else ()
    weighted_tokens, strong_single_tokens, phrases = (
        _compiled_inputs
        if _compiled_inputs is not None
        else _compiled_agent_score_inputs(_agent_signature(agent))
    )
    matched_tokens: set[str] = set()
    score = 0.0
    for token, weight in weighted_tokens:
        if token in query_tokens:
            matched_tokens.add(token)
            score += weight
    strong_match = bool(strong_single_tokens.intersection(query_tokens))

    # A curated multi-token value is more specific than its individual terms.
    # Phrase bonuses are precomputed so the request hot path only compares the
    # short normalized token tuples.
    for phrase, bonus in phrases:
        if (
            phrase in _query_phrases
            if _query_phrases is not None
            else _contains_phrase(query_order, phrase)
        ):
            score += bonus
            strong_match = True

    # A lone generic word buried in a longer value (for example ``design`` in
    # ``warehouse design``) is insufficient evidence.  Require either two
    # distinct query terms or an exact curated value/phrase.
    if len(matched_tokens) < 2 and not strong_match:
        return 0.0
    return round(score, 4)


def _pre_narrow_compiled(
    query: str,
    catalog: list[dict[str, Any]],
    compiled: _CompiledCatalog,
    limit: int,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Narrow one query against an already compiled catalog."""
    query_tokens = tokenize(query)
    if not query_tokens:
        selected = catalog[:limit]
        return selected, [0.0] * len(selected)

    query_order = _ordered_tokens(query)
    phrase_lengths = {
        len(phrase)
        for _weighted, _single, phrases in compiled
        for phrase, _bonus in phrases
        if len(phrase) <= len(query_order)
    }
    query_phrases = frozenset(
        query_order[index : index + width]
        for width in phrase_lengths
        for index in range(len(query_order) - width + 1)
    )
    positive: list[tuple[float, str, int, dict[str, Any]]] = []
    unmatched: list[tuple[str, int, dict[str, Any]]] = []
    for index, (agent, score_inputs) in enumerate(zip(catalog, compiled, strict=True)):
        score = score_agent(
            agent,
            query_tokens,
            query_text=query,
            _compiled_inputs=score_inputs,
            _query_phrases=query_phrases,
        )
        slug = agent_identity(agent)
        if score > 0:
            positive.append((score, slug, index, agent))
        else:
            unmatched.append((slug, index, agent))

    # A unit assignment usually needs only one winner. ``nsmallest`` preserves
    # the exact score/slug/catalog-order contract without sorting every
    # positive row in a 10,000-agent roster.
    ranked_positive = nsmallest(
        limit,
        positive,
        key=lambda item: (-item[0], item[1], item[2]),
    )
    result = [(score, agent) for score, _slug, _index, agent in ranked_positive]
    if len(result) < limit:
        ranked_unmatched = nsmallest(
            limit - len(result),
            unmatched,
            key=lambda item: (item[0], item[1]),
        )
        result.extend((0.0, agent) for _slug, _index, agent in ranked_unmatched)
    return [agent for _, agent in result], [score for score, _ in result]


def pre_narrow(
    query: str,
    catalog: list[dict[str, Any]],
    limit: int = 80,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Return the highest-scoring candidates and aligned deterministic scores."""
    if limit <= 0 or not catalog:
        return [], []
    if len(catalog) > MAX_ACTIVE_ROSTER_SIZE:
        raise ValueError(f"catalog cannot contain more than {MAX_ACTIVE_ROSTER_SIZE} agents")
    return _pre_narrow_compiled(
        query,
        catalog,
        _compiled_catalog_score_inputs(catalog),
        limit,
    )


def retrieval_has_signal(query: str, catalog: list[dict[str, Any]]) -> bool:
    """Return whether lexical narrowing scored any card above zero.

    AR-370 / ADR-0197: an operational wording such as ``configure the gateway``
    scores 0.0 against every card, so the ranked list degenerates to slug order.
    That zero is the exact, non-inferential trigger for spending one typed
    classification call before planning; a query that already scores pays
    nothing. Kept here so the CLI diagnostic and the routing pipeline cannot
    drift apart on what "no signal" means.
    """

    if not catalog:
        return False
    _, scores = pre_narrow(query, catalog, limit=1)
    return bool(scores) and max(scores) > 0.0
