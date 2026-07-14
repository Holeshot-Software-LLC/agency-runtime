"""Full 8-layer routing pipeline — the core selector.

Uses centralized config for all tunable values.

Layer 0: Companion policy (deterministic action→agent mapping, <1ms)
Layer 1: Domain context expansion
Layer 2: LRU cache (content-hash + TTL)
Layer 3: Session stickiness (token overlap reuse)
Layer 4: Confidence bypass (skip LLM when token score ≥ threshold)
Layer 5: Token pre-narrow + LLM judge
Layer 6: Token-only fallback (if LLM unavailable)
Layer 7: Union companion policy results with semantic results
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.delegation.events import work_unit_id_from_text
from agency_runtime.core.selector.cache import (
    cache_get,
    cache_key,
    cache_put,
    catalog_active_ids,
    routing_fingerprint,
)
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.intent_text import affirmative_intent
from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.selector.policy import (
    detect_actions,
    load_policy,
    validate_policy,
)
from agency_runtime.core.selector.stickiness import session_check, session_put

logger = logging.getLogger("agency_runtime.selector.pipeline")

if TYPE_CHECKING:
    from agency_runtime.core.store.sqlite import Store


def _get_config(config: AgencyConfig | None = None) -> AgencyConfig:
    return config or load_config()


def refine_query(user_message: str, config: AgencyConfig | None = None) -> str:
    """Lightweight query refinement without an LLM call."""
    cfg = _get_config(config)
    msg = user_message.strip()
    msg = re.sub(r"^(?:Hermes|Mentor|Nexus|OpenClaw)\s*[:,-]?\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"https?://\S+", "", msg)
    msg = re.sub(r"/(?:home|usr|opt|var|tmp)/\S+", "", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    max_len = cfg.selector.max_user_msg_len
    if len(msg) > max_len:
        msg = msg[:max_len]
    return msg


def is_trivial(message: str, config: AgencyConfig | None = None) -> bool:
    """Check if a message is too trivial to warrant agency routing."""
    cfg = _get_config(config)
    msg = message.strip()
    if len(msg) < cfg.selector.trivial_msg_threshold:
        return True
    return bool(_TRIVIAL_PATTERNS.match(msg))


_TRIVIAL_PATTERNS = re.compile(
    r"^(?:yes|no|ok|okay|sure|thanks|done|got ?it|cool|nice|great|"
    r"perfect|exactly|right|correct|yep|nope|true|false|"
    r"continue|proceed|go|stop|wait|hold|skip|retry|"
    r"hello|hi|hey|sup|yo|test|ping|heartbeat"
    r"|/\\w+|ack|k|thx|ty|np|lol|haha|👍|❤️|🙌|✅|💀|😂)\s*[!.?]*$",
    re.IGNORECASE,
)


def _available_companions(
    companion_ids: list[str], active_slugs: set[str] | frozenset[str]
) -> tuple[list[str], list[str]]:
    """Split policy companion slugs into active-roster and unavailable lists."""
    available: list[str] = []
    unavailable: list[str] = []
    for companion_id in companion_ids:
        if companion_id in active_slugs:
            available.append(companion_id)
        else:
            unavailable.append(companion_id)
    return available, unavailable


def _refresh_reused_routing(
    routing: dict[str, Any],
    *,
    active_ids: set[str] | frozenset[str],
    matched_actions: list[str],
    companion_ids: list[str],
    available_companion_ids: list[str],
    unavailable_companion_ids: list[str],
    work_units: dict[str, Any],
) -> dict[str, Any] | None:
    """Validate reusable state and attach signals from the current message."""
    semantic_ids = routing.get("semantic_ids")
    if not isinstance(semantic_ids, list):
        previous_companions = set(routing.get("available_companion_ids", []))
        semantic_ids = [
            slug for slug in routing.get("selected_ids", []) if slug not in previous_companions
        ]
    validated_semantic_ids = [str(slug) for slug in semantic_ids if str(slug) in active_ids]
    if semantic_ids and not validated_semantic_ids:
        # The cached decision no longer exists in this catalog. Re-run routing
        # instead of turning a stale selection into a misleading abstention.
        return None

    merged = list(dict.fromkeys(validated_semantic_ids))
    for companion_id in available_companion_ids:
        if companion_id not in merged:
            merged.append(companion_id)

    routing["semantic_ids"] = validated_semantic_ids
    routing["selected_ids"] = merged
    routing["companion_actions"] = matched_actions
    routing["companion_ids"] = companion_ids
    routing["available_companion_ids"] = available_companion_ids
    routing["unavailable_companion_ids"] = unavailable_companion_ids
    routing["work_units"] = work_units
    return routing


def _finalize_decision(
    routing: dict[str, Any],
    *,
    session_id: str,
    user_message: str,
    context_fingerprint: str,
    store: Store | None,
    trace_id: str | None,
) -> dict[str, Any]:
    """Attach per-request identity and optionally persist a safe projection."""
    decision_trace_id = trace_id or str(uuid.uuid4())
    routing["trace_id"] = decision_trace_id
    routing["context_fingerprint"] = context_fingerprint
    query_hash = hashlib.sha256(user_message.encode("utf-8")).hexdigest()
    routing["query_hash"] = query_hash
    if store is not None:
        try:
            routing["decision_id"] = store.record_routing_decision(
                trace_id=decision_trace_id,
                session_id=session_id,
                query_hash=query_hash,
                context_fingerprint=context_fingerprint,
                decision=routing,
            )
        except Exception as exc:  # routing must survive an observability outage
            logger.warning("failed to persist routing decision: %s", type(exc).__name__)
    return routing


@dataclass(frozen=True, slots=True)
class _RouteRequest:
    session_id: str
    user_message: str
    catalog: list[dict[str, Any]]
    config: AgencyConfig
    policy: dict[str, Any]
    context_fingerprint: str
    routing_query: str
    cache_key: str
    source_message_hash: str
    active_ids: frozenset[str]


@dataclass(frozen=True, slots=True)
class _RouteSignals:
    policy_validation: dict[str, Any]
    matched_actions: list[str]
    companion_ids: list[str]
    available_companion_ids: list[str]
    unavailable_companion_ids: list[str]
    work_units: dict[str, Any]


def _route_request(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
) -> _RouteRequest:
    policy = load_policy()
    fingerprint = routing_fingerprint(catalog, config, policy)
    refined = refine_query(user_message, config)
    routing_query = expand_query(affirmative_intent(refined))
    return _RouteRequest(
        session_id=session_id,
        user_message=user_message,
        catalog=catalog,
        config=config,
        policy=policy,
        context_fingerprint=fingerprint,
        routing_query=routing_query,
        cache_key=cache_key(routing_query, context_fingerprint=fingerprint),
        source_message_hash=hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        active_ids=catalog_active_ids(catalog, context_fingerprint=fingerprint),
    )


def _route_signals(request: _RouteRequest) -> _RouteSignals:
    validation = validate_policy(request.policy, request.active_ids)
    matched_actions, companion_ids = detect_actions(
        request.user_message,
        request.policy,
        active_slugs=request.active_ids,
    )
    available, unavailable = _available_companions(
        companion_ids,
        request.active_ids,
    )
    return _RouteSignals(
        policy_validation=validation,
        matched_actions=matched_actions,
        companion_ids=companion_ids,
        available_companion_ids=available,
        unavailable_companion_ids=unavailable,
        work_units=detect_work_units(request.user_message),
    )


def _finalize_request(
    routing: dict[str, Any],
    request: _RouteRequest,
    *,
    store: Store | None,
    trace_id: str | None,
) -> dict[str, Any]:
    return _finalize_decision(
        routing,
        session_id=request.session_id,
        user_message=request.user_message,
        context_fingerprint=request.context_fingerprint,
        store=store,
        trace_id=trace_id,
    )


def _exact_cached_routing(
    cached: dict[str, Any] | None,
    request: _RouteRequest,
) -> dict[str, Any] | None:
    if cached is None or cached.get("source_message_hash") != request.source_message_hash:
        return None
    cached_ids = cached.get("selected_ids", [])
    return cached if all(str(slug) in request.active_ids for slug in cached_ids) else None


def _reuse_routing(
    routing: dict[str, Any] | None,
    request: _RouteRequest,
    signals: _RouteSignals,
) -> dict[str, Any] | None:
    if routing is None:
        return None
    refreshed = _refresh_reused_routing(
        routing,
        active_ids=request.active_ids,
        matched_actions=signals.matched_actions,
        companion_ids=signals.companion_ids,
        available_companion_ids=signals.available_companion_ids,
        unavailable_companion_ids=signals.unavailable_companion_ids,
        work_units=signals.work_units,
    )
    if refreshed is not None:
        refreshed["source_message_hash"] = request.source_message_hash
    return refreshed


def _merge_computed_routing(
    routing: dict[str, Any],
    request: _RouteRequest,
    signals: _RouteSignals,
) -> dict[str, Any]:
    semantic_ids = [
        str(slug) for slug in routing.get("selected_ids", []) if str(slug) in request.active_ids
    ]
    merged_ids = list(dict.fromkeys(semantic_ids))
    for companion_id in signals.available_companion_ids:
        if companion_id not in merged_ids:
            merged_ids.append(companion_id)
    validation = signals.policy_validation
    routing.update(
        selected_ids=merged_ids,
        semantic_ids=semantic_ids,
        companion_actions=signals.matched_actions,
        companion_ids=signals.companion_ids,
        available_companion_ids=signals.available_companion_ids,
        unavailable_companion_ids=signals.unavailable_companion_ids,
        policy_validation={
            "valid": validation["valid"],
            "errors": validation["errors"],
            "enabled_count": len(validation["enabled_slugs"]),
            "disabled_count": validation["disabled_count"],
        },
        work_units=signals.work_units,
        source_message_hash=request.source_message_hash,
    )
    return routing


def _remember_routing(routing: dict[str, Any], request: _RouteRequest) -> None:
    if not routing.get("selected_ids"):
        return
    cache_put(request.cache_key, routing)
    session_put(
        request.session_id,
        request.routing_query,
        routing,
        context_fingerprint=request.context_fingerprint,
    )


def route(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    *,
    config: AgencyConfig | None = None,
    store: Store | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Run the full 8-layer routing pipeline.

    Args:
        session_id: Session identifier for stickiness.
        user_message: The user's raw message text.
        catalog: Agent catalog to route against. If None, caller must provide.
        config: Optional config override.

    Returns:
        Routing dict with keys: selected_ids, confidence, latency_ms, status,
        companion_actions, companion_ids, work_units, and possibly cache_hit,
        session_reused.
    """
    cfg = _get_config(config)
    request = _route_request(
        session_id,
        user_message,
        catalog if catalog is not None else [],
        cfg,
    )
    cached = cache_get(request.cache_key)
    exact = _exact_cached_routing(cached, request)
    if exact is not None:
        return _finalize_request(exact, request, store=store, trace_id=trace_id)
    signals = _route_signals(request)
    reused = _reuse_routing(cached, request, signals)
    if reused is not None:
        return _finalize_request(reused, request, store=store, trace_id=trace_id)
    session_result = session_check(
        request.session_id,
        request.routing_query,
        context_fingerprint=request.context_fingerprint,
        valid_ids=request.active_ids,
    )
    reused = _reuse_routing(session_result, request, signals)
    if reused is not None:
        return _finalize_request(reused, request, store=store, trace_id=trace_id)
    routing = query_judge(request.routing_query, request.catalog, config=cfg)
    routing = _merge_computed_routing(routing, request, signals)
    _remember_routing(routing, request)
    return _finalize_request(
        routing,
        request,
        store=store,
        trace_id=trace_id,
    )


def build_routing_context(routing: dict[str, Any], config: AgencyConfig | None = None) -> str:
    """Build the [AGENCY PREFLIGHT] context string from a routing result."""
    cfg = _get_config(config)
    selected = routing.get("selected_ids", [])
    confidence = routing.get("confidence", 0.0)
    cache_hit = routing.get("cache_hit", False)
    session_reused = routing.get("session_reused", False)
    status = routing.get("status", "unknown")

    source = "llm"
    if cache_hit:
        source = "cache"
    elif session_reused:
        source = "session"

    parts: list[str] = []

    if not selected or confidence < cfg.selector.min_confidence:
        if selected:
            agents_list = ", ".join(selected)
            parts.append(
                f"[AGENCY PREFLIGHT] Default specialist routing suggestion "
                f"(confidence={confidence:.1f}, source={source}, status={status}): {agents_list}"
            )
        else:
            parts.append(
                f"[AGENCY PREFLIGHT] No high-confidence specialist match found "
                f"(status={status}). You must still query "
                "agency_agents_search before any non-trivial work and include "
                "the Agency header in your response."
            )
    else:
        agents_list = ", ".join(selected)
        parts.append(
            f"[AGENCY PREFLIGHT] Specialist routing suggestion "
            f"(confidence={confidence:.1f}, source={source}): {agents_list}"
        )

    work_units = routing.get("work_units", {})
    if work_units.get("delegate", False) and work_units.get("count", 1) >= 2:
        unit_count = work_units["count"]
        unit_source = work_units.get("source", "unknown")
        unit_confidence = work_units.get("confidence", "low")
        units_list = work_units.get("units", [])

        nudge = (
            f"\n\n[DELEGATION OPPORTUNITY] {unit_count} independent work units "
            f"detected (confidence={unit_confidence}, source={unit_source}). "
            "PRIORITY: delegate parallel work via delegate_task or delegate_async. "
            "Keep the main session available for the user."
        )
        if units_list:
            nudge += "\n  Detected work units:"
            for i, unit in enumerate(units_list, 1):
                unit_text = str(unit)
                unit_id = work_unit_id_from_text(unit_text)
                nudge += f"\n    {i}. [{unit_id}] {unit_text}"
            nudge += "\n  Pass the bracketed work_unit_id unchanged to the delegation tool."
        parts.append(nudge)

    parts.append(HEADER_INSTRUCTION)
    return "\n".join(parts)


def route_and_build_context(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    config: AgencyConfig | None = None,
    store: Store | None = None,
    trace_id: str | None = None,
) -> str | None:
    """Run the full pipeline and return the context string. None if trivial."""
    cfg = _get_config(config)
    if is_trivial(user_message, cfg):
        return None
    routing = route(
        session_id,
        user_message,
        catalog,
        config=cfg,
        store=store,
        trace_id=trace_id,
    )
    return build_routing_context(routing, cfg)


HEADER_INSTRUCTION = (
    "\n  You MUST call agency_agents_search and/or agency_agents_load "
    "for the relevant specialist(s) before starting non-trivial work, "
    "and include the Agency header in your response:\n"
    "  Agency/Agencies loaded: <agent-id>\n"
    "  Agency/Agencies delegated: <agent-id>\n"
    "  Skills loaded: <skill-id[, skill-id...] or none>\n"
    "  Actual Model selected: <requested alias> -> <resolved provider/model>\n"
    "  Why: <one line>\n"
    "  How it shaped outcome: <one line>"
)
