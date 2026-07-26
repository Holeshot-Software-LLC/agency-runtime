"""Explainable specialist-routing receipts.

The selector's routing path stays unchanged. This module runs the existing
pipeline once, then packages the decision evidence into a stable JSON shape for
CLI, HTTP, and MCP callers.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.config_binding import config_for_store
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    diagnostic_installation_capability_receipt,
)
from agency_runtime.core.selector.cache import cache_key, routing_fingerprint
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.pipeline import refine_query, route
from agency_runtime.core.selector.policy import (
    detect_actions,
    detect_fallback_companions,
    load_policy,
    policy_path_for_config,
)
from agency_runtime.core.selector.receipt_projection import (
    RECEIPT_DESCRIPTION_BYTES,
    bounded_receipt_text,
)
from agency_runtime.core.turn_intent import classify_turn_intent

if TYPE_CHECKING:
    from agency_runtime.core.store.sqlite import Store

_SCHEMA_VERSION = "agency.selection_explain.v1"
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50


def _get_config(
    config: AgencyConfig | None = None,
    store: Store | None = None,
) -> AgencyConfig:
    return config_for_store(store, config)


def _clamp_limit(limit: int | None) -> int:
    try:
        value = int(limit or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        value = _DEFAULT_LIMIT
    return max(1, min(value, _MAX_LIMIT))


def _agent_summary(
    agent: dict[str, Any] | None, *, score: float | None = None, selected: bool = False
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if agent:
        payload.update(
            {
                "slug": agent_identity(agent),
                "name": str(agent.get("name", "")),
                "division": str(agent.get("division", "")),
                "description": bounded_receipt_text(
                    agent.get("description", ""),
                    maximum_bytes=RECEIPT_DESCRIPTION_BYTES,
                ),
            }
        )
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


def _selected_explanations(
    selected_ids: list[str],
    catalog: list[dict[str, Any]],
    candidate_rows: list[tuple[dict[str, Any], float]],
    companion_ids: list[str],
    fallback_ids: list[str],
) -> list[dict[str, Any]]:
    catalog_by_slug = {agent_identity(agent): agent for agent in catalog}
    score_by_slug = {agent_identity(agent): float(score) for agent, score in candidate_rows}
    selected: list[dict[str, Any]] = []
    for slug in selected_ids:
        summary = _agent_summary(
            catalog_by_slug.get(slug, {"slug": slug}),
            score=score_by_slug.get(slug),
            selected=True,
        )
        if slug in fallback_ids:
            summary["source"] = "policy_fallback"
        elif slug in companion_ids:
            summary["source"] = "companion_policy"
        else:
            summary["source"] = "selector"
        selected.append(summary)
    return selected


def _considered_explanations(
    candidate_rows: list[tuple[dict[str, Any], float]],
    selected_ids: set[str],
) -> list[dict[str, Any]]:
    return [
        _agent_summary(
            agent,
            score=float(score),
            selected=agent_identity(agent) in selected_ids,
        )
        for agent, score in candidate_rows
    ]


def _rejected_explanations(
    candidate_rows: list[tuple[dict[str, Any], float]],
    selected_ids: set[str],
    *,
    status: str,
    cache_hit: bool,
    session_reused: bool,
) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for agent, score in candidate_rows:
        if agent_identity(agent) in selected_ids:
            continue
        entry = _agent_summary(agent, score=float(score), selected=False)
        entry["reason"] = _rejection_reason(
            status=status,
            score=float(score),
            cache_hit=cache_hit,
            session_reused=session_reused,
        )
        rejected.append(entry)
    return rejected


def _explanation_signals(
    *,
    routing: dict[str, Any],
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
    policy: dict[str, Any],
    refined_query: str,
    expanded_query: str,
    candidates: list[dict[str, Any]],
    scores: list[float],
    selected_ids: list[str],
    matched_actions: list[str],
    companion_ids: list[str],
    candidate_limit: int,
) -> dict[str, Any]:
    status = str(routing.get("status", ""))
    cache_hit = bool(routing.get("cache_hit", False))
    session_reused = bool(routing.get("session_reused", False))
    domain_terms = _domain_terms(refined_query, expanded_query)
    return {
        "policy": {
            "matched_actions": matched_actions,
            "companion_ids": companion_ids,
            "selected_companion_ids": [slug for slug in selected_ids if slug in companion_ids],
            "fallback_companion_ids": list(routing.get("fallback_companion_ids", [])),
            "fallback_applied": bool(routing.get("fallback_applied", False)),
        },
        "domain_expansion": {
            "applied": bool(domain_terms),
            "refined_query": refined_query,
            "expanded_query": expanded_query,
            "terms": domain_terms,
        },
        "cache": {
            "key": cache_key(
                expanded_query,
                context_fingerprint=routing_fingerprint(catalog, config, policy),
            ),
            "hit": cache_hit,
        },
        "stickiness": {"session_reused": session_reused},
        "selection": {
            "status": status,
            "source": str(routing.get("source", "")),
            "semantic_status": str(routing.get("semantic_status", status)),
            "semantic_ids": list(routing.get("semantic_ids", [])),
            "confidence": float(routing.get("confidence", 0.0) or 0.0),
            "provider": str(routing.get("provider", "")),
            "candidate_count": int(routing.get("candidate_count", len(candidates)) or 0),
            "top_score": float(routing.get("top_score", scores[0] if scores else 0.0) or 0.0),
            "pre_narrow_limit": candidate_limit,
            "roster_size": len(catalog),
            "disabled_candidate_shadows": list(routing.get("disabled_candidate_shadows", [])),
            "unavailable_candidate_shadows": list(routing.get("unavailable_candidate_shadows", [])),
        },
        "work_units": routing.get("work_units", {}),
    }


def explain_route(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    *,
    config: AgencyConfig | None = None,
    limit: int | None = None,
    store: Store | None = None,
    trace_id: str | None = None,
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: tuple[str, ...] | None = None,
    capability_receipt: Mapping[str, Any] | HostCapabilityReceipt | None = None,
    workforce_snapshot: Any = None,
) -> dict[str, Any]:
    """Return a machine-readable explanation for one routing decision.

    Routing explanations are diagnostic projections. They retain generated
    trace identity in the response but never create durable turn evidence;
    ``run_preflight`` exclusively owns that lifecycle.
    """
    cfg = _get_config(config, store)
    catalog = catalog or []
    if store is not None and workforce_snapshot is None:
        from agency_runtime.core.routing_snapshot import (
            bind_workforce_snapshot,
            capture_routing_snapshot,
        )

        bound = capture_routing_snapshot(store, cfg)
        if bound.catalog == catalog:
            _bound, workforce_snapshot = bind_workforce_snapshot(store, bound)
    candidate_limit = _clamp_limit(limit)

    refined_query = refine_query(user_message, cfg)
    expanded_query = expand_query(refined_query)
    policy = load_policy(policy_path_for_config(cfg))
    active_slugs = {agent_identity(agent) for agent in catalog}
    matched_actions, companion_ids = detect_actions(
        user_message,
        policy,
        active_slugs=active_slugs,
    )
    # DEFAULT coordinators are a policy fallback, not semantic candidates. Keep
    # them out of the candidate receipt so an abstention cannot look like a
    # semantic match simply because fallback prompts are installed.
    policy_fallbacks = set(detect_fallback_companions(policy))
    semantic_catalog = [agent for agent in catalog if agent_identity(agent) not in policy_fallbacks]
    # Route Lab and CLI explanations are diagnostic turns, but they still need
    # an authoritative statement that the absence of prior state is known. A
    # bare classifier call represents *missing/untrusted* state and therefore
    # must route conservatively; using it here made a fresh ``hello`` consume
    # the configured provider timeout even though this surface can prove that
    # no continuation is pending.
    turn_state = (
        store.get_turn_state_context(session_id)
        if store is not None
        else {"state_known": True, "state_status": "current"}
    )
    turn_classification = classify_turn_intent(user_message, turn_state)
    if not turn_classification.selection_required:
        candidates, scores = [], []
    else:
        candidates, scores = pre_narrow(
            expanded_query,
            semantic_catalog,
            limit=candidate_limit,
        )
    candidate_rows = list(zip(candidates, scores, strict=True))

    diagnostic_receipt = None
    if capability_receipt is not None:
        raw_receipt = (
            capability_receipt.as_dict()
            if isinstance(capability_receipt, HostCapabilityReceipt)
            else capability_receipt
        )
        diagnostic_receipt = diagnostic_installation_capability_receipt(
            raw_receipt,
            surface=host,
            platform=platform,
        )
        if diagnostic_receipt is None:
            raise ValueError("diagnostic host capability receipt is invalid or unverified")

    routing = route(
        session_id,
        user_message,
        catalog,
        config=cfg,
        trace_id=trace_id,
        turn_classification=turn_classification,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=diagnostic_receipt,
        allow_installation_diagnostic=diagnostic_receipt is not None,
        workforce_snapshot=workforce_snapshot,
    )
    selected_ids = [str(slug) for slug in routing.get("selected_ids", []) if str(slug)]
    decision_companion_ids = [
        str(slug) for slug in routing.get("companion_ids", companion_ids) if str(slug)
    ]
    fallback_ids = [str(slug) for slug in routing.get("fallback_companion_ids", []) if str(slug)]
    selected_set = set(selected_ids)
    return {
        "schema_version": _SCHEMA_VERSION,
        "session_id": str(session_id or ""),
        "task": str(user_message or ""),
        "routing": routing,
        "selected": _selected_explanations(
            selected_ids,
            catalog,
            candidate_rows,
            decision_companion_ids,
            fallback_ids,
        ),
        "considered_candidates": _considered_explanations(candidate_rows, selected_set),
        "rejected_candidates": _rejected_explanations(
            candidate_rows,
            selected_set,
            status=str(routing.get("status", "")),
            cache_hit=bool(routing.get("cache_hit", False)),
            session_reused=bool(routing.get("session_reused", False)),
        ),
        "signals": _explanation_signals(
            routing=routing,
            catalog=catalog,
            config=cfg,
            policy=policy,
            refined_query=refined_query,
            expanded_query=expanded_query,
            candidates=candidates,
            scores=scores,
            selected_ids=selected_ids,
            matched_actions=matched_actions,
            companion_ids=decision_companion_ids,
            candidate_limit=candidate_limit,
        ),
    }


__all__ = ["explain_route"]
