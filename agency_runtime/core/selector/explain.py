"""Explainable specialist-routing receipts.

The selector's routing path stays unchanged. This module runs the existing
pipeline once, then packages the decision evidence into a stable JSON shape for
CLI, HTTP, and MCP callers.
"""

from __future__ import annotations

from typing import Any

from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.selector.cache import cache_key
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.pipeline import refine_query, route
from agency_runtime.core.selector.policy import detect_actions

_SCHEMA_VERSION = "agency.selection_explain.v1"
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


def _get_config(config: AgencyConfig | None = None) -> AgencyConfig:
    return config or load_config()


def _clamp_limit(limit: int | None) -> int:
    try:
        value = int(limit or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        value = _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))


def _agent_slug(agent: dict[str, Any]) -> str:
    return str(agent.get("slug") or agent.get("agent_slug") or "")


def _agent_summary(agent: dict[str, Any] | None, *, score: float | None = None, selected: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if agent:
        payload.update({
            "slug": _agent_slug(agent),
            "name": str(agent.get("name", "")),
            "division": str(agent.get("division", "")),
            "description": str(agent.get("description", "")),
        })
    else:
        payload.update({"slug": "", "name": "", "division": "", "description": ""})
    if score is not None:
        payload["score"] = round(float(score), 4)
    payload["selected"] = bool(selected)
    return payload


def _domain_terms(refined_query: str, expanded_query: str) -> list[str]:
    marker = "[domain context:"
    if marker not in expanded_query or expanded_query == refined_query:
        return []
    tail = expanded_query.split(marker, 1)[1].rstrip("] ")
    return [term.strip() for term in tail.split(",") if term.strip()]


def _rejection_reason(*, status: str, score: float, cache_hit: bool, session_reused: bool) -> str:
    if cache_hit:
        return "not in cached selection"
    if session_reused:
        return "not in reused session selection"
    if score <= 0:
        return "zero token overlap"
    if status == "confidence_bypass":
        return "below confidence-bypass cutoff"
    if status == "token_fallback":
        return "lower token score than selected candidates"
    if status == "applied":
        return "not selected by judge"
    return f"not selected by routing status '{status or 'unknown'}'"


def explain_route(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    *,
    config: AgencyConfig | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Return a machine-readable explanation for one routing decision.

    The only selector side effect is the single call to ``route()``, matching the
    normal routing path. All other evidence assembly is read-only.
    """
    cfg = _get_config(config)
    catalog = catalog or []
    candidate_limit = _clamp_limit(limit)

    refined_query = refine_query(user_message, cfg)
    expanded_query = expand_query(refined_query)
    matched_actions, companion_ids = detect_actions(user_message)
    candidates, scores = pre_narrow(expanded_query, catalog, limit=candidate_limit)
    candidate_rows = list(zip(candidates, scores))

    routing = route(session_id, user_message, catalog, config=cfg)
    selected_ids = [str(slug) for slug in routing.get("selected_ids", []) if str(slug)]
    selected_set = set(selected_ids)
    status = str(routing.get("status", ""))
    cache_hit = bool(routing.get("cache_hit", False))
    session_reused = bool(routing.get("session_reused", False))

    catalog_by_slug = {_agent_slug(agent): agent for agent in catalog}
    score_by_slug = {_agent_slug(agent): float(score) for agent, score in candidate_rows}

    selected = []
    for slug in selected_ids:
        summary = _agent_summary(
            catalog_by_slug.get(slug, {"slug": slug}),
            score=score_by_slug.get(slug),
            selected=True,
        )
        summary["source"] = "companion_policy" if slug in companion_ids else "selector"
        selected.append(summary)

    considered = [
        _agent_summary(agent, score=float(score), selected=_agent_slug(agent) in selected_set)
        for agent, score in candidate_rows
    ]

    rejected = []
    for agent, score in candidate_rows:
        slug = _agent_slug(agent)
        if slug in selected_set:
            continue
        entry = _agent_summary(agent, score=float(score), selected=False)
        entry["reason"] = _rejection_reason(
            status=status,
            score=float(score),
            cache_hit=cache_hit,
            session_reused=session_reused,
        )
        rejected.append(entry)

    domain_terms = _domain_terms(refined_query, expanded_query)
    return {
        "schema_version": _SCHEMA_VERSION,
        "session_id": str(session_id or ""),
        "task": str(user_message or ""),
        "routing": routing,
        "selected": selected,
        "considered_candidates": considered,
        "rejected_candidates": rejected,
        "signals": {
            "policy": {
                "matched_actions": matched_actions,
                "companion_ids": companion_ids,
                "selected_companion_ids": [slug for slug in selected_ids if slug in companion_ids],
            },
            "domain_expansion": {
                "applied": bool(domain_terms),
                "refined_query": refined_query,
                "expanded_query": expanded_query,
                "terms": domain_terms,
            },
            "cache": {
                "key": cache_key(expanded_query),
                "hit": cache_hit,
            },
            "stickiness": {
                "session_reused": session_reused,
            },
            "selection": {
                "status": status,
                "confidence": float(routing.get("confidence", 0.0) or 0.0),
                "provider": str(routing.get("provider", "")),
                "candidate_count": int(routing.get("candidate_count", len(candidates)) or 0),
                "top_score": float(routing.get("top_score", scores[0] if scores else 0.0) or 0.0),
                "pre_narrow_limit": candidate_limit,
                "roster_size": len(catalog),
            },
            "work_units": routing.get("work_units", {}),
        },
    }


__all__ = ["explain_route"]
