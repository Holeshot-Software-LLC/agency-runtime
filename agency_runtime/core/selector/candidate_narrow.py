"""Token-based candidate narrowing before LLM judge."""

from __future__ import annotations

import re
from typing import Any

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#_-]*", re.IGNORECASE)
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "be", "for", "from", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "with",
    "work", "task", "agent", "agents", "specialist", "specialists",
    "help", "need", "want", "can", "you", "me", "my", "our", "we",
})


def tokenize(text: str) -> set[str]:
    """Tokenize text for token-overlap scoring."""
    tokens: set[str] = set()
    for raw in _WORD_RE.findall(text.lower()):
        for part in re.split(r"[-_./]", raw):
            token = part.strip()
            if len(token) >= 2 and token not in _STOPWORDS:
                tokens.add(token)
    return tokens


def score_agent(agent: dict[str, Any], query_tokens: set[str]) -> float:
    """Fast in-memory token-overlap score for candidate pre-narrowing."""
    haystack = " ".join([
        agent.get("slug", ""),
        agent.get("name", ""),
        agent.get("description", ""),
        agent.get("division", ""),
    ]).lower()
    agent_tokens = tokenize(haystack)
    overlap = query_tokens & agent_tokens
    if not overlap:
        return 0.0
    score = float(len(overlap))
    name = agent.get("name", "").lower()
    desc = agent.get("description", "").lower()
    for token in query_tokens:
        if token in name:
            score += 3.0
        if token in desc:
            score += 1.5
    return score


def pre_narrow(
    query: str,
    catalog: list[dict[str, Any]],
    limit: int = 80,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Token-score the full catalog and return top-N candidates + scores."""
    query_tokens = tokenize(query)
    if not query_tokens:
        return catalog[:limit], [0.0] * min(len(catalog), limit)
    scored = [(score_agent(agent, query_tokens), agent) for agent in catalog]
    scored.sort(key=lambda item: (-item[0], item[1].get("slug", "")))
    result: list[tuple[float, dict[str, Any]]] = [
        (score, agent) for score, agent in scored if score > 0
    ]
    if len(result) < limit:
        seen = {agent.get("slug") for _, agent in result}
        for score, agent in scored:
            if agent.get("slug") not in seen:
                result.append((0.0, agent))
                if len(result) >= limit:
                    break
    result = result[:limit] if result else [(0.0, a) for a in catalog[:limit]]
    candidates = [agent for _, agent in result]
    scores = [score for score, _ in result]
    return candidates, scores
