"""Deterministic metadata-aware candidate narrowing before the LLM judge.

The narrower's job is recall: retain the specialists that a semantic judge may
need while keeping obviously unrelated agents out of its context.  Matching is
limited to complete tokens and phrases.  In particular, short identifiers such
as ``pr`` and ``ui`` never match substrings such as ``spring`` or ``build``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

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
    "runbooks": "runbook",
    "servers": "server",
    "testing": "test",
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
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Build a stable, mutation-aware key for routing-relevant metadata."""
    return tuple((field, _field_values(agent.get(field))) for field, _weight in _FIELD_WEIGHTS)


@lru_cache(maxsize=8192)
def _compiled_agent_score_inputs(
    signature: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[
    tuple[tuple[str, float], ...],
    frozenset[str],
    tuple[tuple[tuple[str, ...], float], ...],
]:
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
    _compiled_inputs: tuple[
        tuple[tuple[str, float], ...],
        frozenset[str],
        tuple[tuple[tuple[str, ...], float], ...],
    ]
    | None = None,
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


def pre_narrow(
    query: str,
    catalog: list[dict[str, Any]],
    limit: int = 80,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Return the highest-scoring candidates and aligned deterministic scores."""
    if limit <= 0 or not catalog:
        return [], []

    query_tokens = tokenize(query)
    if not query_tokens:
        selected = catalog[:limit]
        return selected, [0.0] * len(selected)

    query_order = _ordered_tokens(query)
    compiled = [_compiled_agent_score_inputs(_agent_signature(agent)) for agent in catalog]
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
    positive: list[tuple[float, str, dict[str, Any]]] = []
    unmatched: list[tuple[str, dict[str, Any]]] = []
    for agent, score_inputs in zip(catalog, compiled, strict=True):
        score = score_agent(
            agent,
            query_tokens,
            query_text=query,
            _compiled_inputs=score_inputs,
            _query_phrases=query_phrases,
        )
        slug = str(agent.get("slug") or agent.get("agent_slug") or "")
        if score > 0:
            positive.append((score, slug, agent))
        else:
            unmatched.append((slug, agent))

    # Most large rosters contain many zero-score agents. Sorting those rows is
    # unnecessary unless they are needed to pad a short positive result.
    positive.sort(key=lambda item: (-item[0], item[1]))
    result = [(score, agent) for score, _slug, agent in positive[:limit]]
    if len(result) < limit:
        unmatched.sort(key=lambda item: item[0])
        result.extend((0.0, agent) for _slug, agent in unmatched[: limit - len(result)])
    return [agent for _, agent in result], [score for score, _ in result]
