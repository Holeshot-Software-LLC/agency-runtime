"""Full 8-layer routing pipeline — the core selector.

Uses centralized config for all tunable values.

Layer 0: Companion policy (deterministic action→agent mapping, <1ms)
Layer 1: Domain context expansion
Layer 2: LRU cache (content-hash + TTL)
Layer 3: Session stickiness (token overlap reuse)
Layer 4: Confidence bypass (only when no inference provider is configured)
Layer 5: Token pre-narrow + LLM judge
Layer 6: Token-only fallback (if LLM unavailable)
Layer 7: Union companion policy results with semantic results
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.config_binding import config_for_store
from agency_runtime.core.delegation.events import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_WORK_UNIT_CHARS,
    work_unit_id_from_text,
)
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    current_host_capability_receipt,
)
from agency_runtime.core.host_guidance import (
    NATIVE_DELEGATION_GUIDANCE,
    SPECIALIST_TOOL_GUIDANCE,
    WORK_UNIT_CORRELATION_GUIDANCE,
)
from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.selector import policy as policy_module
from agency_runtime.core.selector.cache import (
    cache_get,
    cache_key,
    cache_put,
    catalog_active_ids,
    routing_fingerprint,
)
from agency_runtime.core.selector.compatibility import (
    COMPATIBILITY_CONTRACT_VERSION,
    MAX_COMPATIBLE_SPECIALISTS,
    enforce_compatible_set,
    filter_eligible_catalog,
)
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.intent_text import affirmative_intent
from agency_runtime.core.selector.judge import inference_is_configured, query_judge
from agency_runtime.core.selector.policy import (
    detect_actions,
    detect_fallback_companions,
    policy_path_for_config,
    validate_policy,
)
from agency_runtime.core.selector.stickiness import session_check, session_put
from agency_runtime.core.turn_intent import (
    TurnClassification,
    TurnState,
    authoritative_turn_classification,
    classify_turn_intent,
)
from agency_runtime.core.unit_assignment import MAX_WORK_UNIT_PREVIEW_CHARS

logger = logging.getLogger("agency_runtime.selector.pipeline")

MAX_ROUTING_SIGNAL_CHARS = 16_384
MAX_ROUTING_CONTEXT_CHARS = 8_000
MAX_ROUTING_SIGNAL_ITEMS = 32
MAX_ROUTING_TOKEN_CHARS = 128
_EXPLICIT_REVIEW_RE = re.compile(
    r"\b(?:audit|critiqu|inspect|review|validat|verif)\w*\b",
    re.IGNORECASE,
)

if TYPE_CHECKING:
    from agency_runtime.core.store.sqlite import Store


def load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Keep the historic patch seam while resolving the live policy module."""

    if policy_path is None:
        return policy_module.load_policy()
    return policy_module.load_policy(policy_path)


def _get_config(
    config: AgencyConfig | None = None,
    store: Store | None = None,
) -> AgencyConfig:
    return config_for_store(store, config)


def _bounded_signal_text(value: Any, limit: int = MAX_ROUTING_SIGNAL_CHARS) -> str:
    return str(value or "")[: max(0, limit)]


def _bounded_unique_strings(
    values: Any,
    *,
    limit: int = MAX_ROUTING_SIGNAL_ITEMS,
    chars: int = MAX_ROUTING_TOKEN_CHARS,
) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in values[:limit]:
        value = " ".join(str(item or "").split())[:chars]
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _bounded_work_units(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {
            "count": 1,
            "confidence": "low",
            "source": "unknown",
            "units": [""],
            "delegate": False,
        }
    units = _bounded_unique_strings(
        value.get("units"),
        limit=MAX_SUGGESTED_WORK_UNITS,
        chars=MAX_WORK_UNIT_CHARS,
    )
    try:
        declared_count = int(value.get("count") or 1)
    except (TypeError, ValueError, OverflowError):
        declared_count = 1
    bounded_count = len(units) if units else max(1, min(declared_count, MAX_SUGGESTED_WORK_UNITS))
    return {
        "count": bounded_count,
        "confidence": _bounded_signal_text(value.get("confidence") or "low", 32),
        "source": _bounded_signal_text(value.get("source") or "unknown", 64),
        "units": units or [""],
        "delegate": bool(value.get("delegate") is True and bounded_count >= 2),
    }


def refine_query(user_message: str, config: AgencyConfig | None = None) -> str:
    """Lightweight query refinement without an LLM call."""
    cfg = _get_config(config)
    hard_limit = min(max(1, int(cfg.selector.max_user_msg_len)), MAX_ROUTING_SIGNAL_CHARS)
    msg = _bounded_signal_text(user_message, hard_limit).strip()
    msg = re.sub(r"^(?:Hermes|Mentor|Nexus|OpenClaw)\s*[:,-]?\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"https?://\S+", "", msg)
    msg = re.sub(r"/(?:home|usr|opt|var|tmp)/\S+", "", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg


def is_trivial(
    message: str,
    config: AgencyConfig | None = None,
    *,
    turn_state: TurnState | Mapping[str, Any] | None = None,
) -> bool:
    """Compatibility alias for callers that have not adopted turn intent yet.

    The selector threshold is intentionally ignored. This projection is not an
    authority boundary; only the state-aware classifier decides whether
    specialist selection is required. Missing state is conservative, so only
    only exact controls or a proven pure acknowledgement under explicitly
    current, no-pending state can return true.
    """

    del config
    return not classify_turn_intent(
        _bounded_signal_text(message),
        turn_state,
    ).selection_required


def _turn_classification(
    user_message: str,
    *,
    turn_classification: TurnClassification | None,
    turn_state: TurnState | Mapping[str, Any] | None,
) -> TurnClassification:
    """Resolve one classifier result without mixing state and precomputed evidence."""

    if turn_classification is not None and turn_state is not None:
        raise ValueError("turn_classification and turn_state are mutually exclusive")
    if turn_classification is not None:
        authoritative = authoritative_turn_classification(turn_classification, user_message)
        if authoritative is None:
            raise ValueError("turn_classification is not authoritative for this message")
        return authoritative
    return classify_turn_intent(user_message, turn_state)


def _available_companions(
    companion_ids: list[str], active_slugs: set[str] | frozenset[str]
) -> tuple[list[str], list[str]]:
    """Split policy companion slugs into active-roster and unavailable lists."""
    available: list[str] = []
    unavailable: list[str] = []
    for companion_id in _bounded_unique_strings(companion_ids):
        if companion_id in active_slugs:
            available.append(companion_id)
        else:
            unavailable.append(companion_id)
    return available, unavailable


def _explicit_review_requested(message: str) -> bool:
    """Return whether affirmative user intent explicitly asks for review."""

    return bool(_EXPLICIT_REVIEW_RE.search(affirmative_intent(message)))


def _refresh_reused_routing(
    routing: dict[str, Any],
    *,
    active_ids: set[str] | frozenset[str],
    matched_actions: list[str],
    companion_ids: list[str],
    available_companion_ids: list[str],
    unavailable_companion_ids: list[str],
    work_units: dict[str, Any],
    catalog: list[dict[str, Any]] | None = None,
    max_selected: int = MAX_COMPATIBLE_SPECIALISTS,
    user_message: str = "",
) -> dict[str, Any] | None:
    """Validate reusable state and attach signals from the current message."""
    if routing.get("fallback_applied"):
        # A no-match decision is safe for an identical cache hit, but must not
        # become sticky evidence that a related message also has no match.
        return None
    semantic_ids = routing.get("semantic_ids")
    if not isinstance(semantic_ids, list):
        previous_companions = set(routing.get("available_companion_ids", []))
        semantic_ids = [
            slug for slug in routing.get("selected_ids", []) if slug not in previous_companions
        ]
    validated_semantic_ids = [
        slug for slug in _bounded_unique_strings(semantic_ids) if slug in active_ids
    ]
    if semantic_ids and not validated_semantic_ids:
        # The cached decision no longer exists in this catalog. Re-run routing
        # instead of turning a stale selection into a misleading abstention.
        return None

    merged = list(dict.fromkeys(validated_semantic_ids))
    for companion_id in available_companion_ids:
        if companion_id not in merged:
            merged.append(companion_id)
    compatibility: dict[str, Any] | None = None
    if catalog is not None:
        compatibility = enforce_compatible_set(
            merged,
            catalog,
            limit=max_selected,
            review_overflow_ids=(
                available_companion_ids if _explicit_review_requested(user_message) else ()
            ),
        )
        merged = list(compatibility["selected_ids"])
    if not merged:
        return None

    routing["semantic_ids"] = [slug for slug in validated_semantic_ids if slug in merged]
    routing["selected_ids"] = merged
    routing["selected_companion_ids"] = [slug for slug in available_companion_ids if slug in merged]
    if compatibility is not None:
        routing["compatibility"] = compatibility
    routing["companion_actions"] = _bounded_unique_strings(matched_actions)
    routing["companion_ids"] = _bounded_unique_strings(companion_ids)
    routing["available_companion_ids"] = _bounded_unique_strings(available_companion_ids)
    routing["unavailable_companion_ids"] = _bounded_unique_strings(unavailable_companion_ids)
    routing["work_units"] = _bounded_work_units(work_units)
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
    surface: str = "unknown"
    host: str = "unknown"
    inference_surface: str = ""
    platform: str = "unknown"
    available_tools: tuple[str, ...] = ()
    capability_status: str = "unknown"
    capability_receipt: dict[str, Any] = field(default_factory=dict)
    eligibility_rejections: tuple[dict[str, str], ...] = ()
    semantic_root_ids: frozenset[str] | None = None


@dataclass(frozen=True, slots=True)
class _RouteSignals:
    policy_validation: dict[str, Any]
    matched_actions: list[str]
    companion_ids: list[str]
    available_companion_ids: list[str]
    unavailable_companion_ids: list[str]
    work_units: dict[str, Any]
    fallback_companion_ids: list[str] = field(default_factory=list)
    available_fallback_companion_ids: list[str] = field(default_factory=list)
    unavailable_fallback_companion_ids: list[str] = field(default_factory=list)


def _route_request(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
    *,
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: tuple[str, ...] | None = None,
    trace_id: str = "",
    capability_receipt: HostCapabilityReceipt | None = None,
    capability_session_id: str = "",
    capability_trace_id: str = "",
    allow_installation_diagnostic: bool = False,
    semantic_root_ids: tuple[str, ...] | None = None,
) -> _RouteRequest:
    user_message = _bounded_signal_text(user_message)
    capabilities = current_host_capability_receipt(
        capability_receipt,
        surface=host,
        platform=platform,
        session_id=capability_session_id or session_id or "route",
        trace_id=capability_trace_id or trace_id or "route",
        allow_installation_diagnostic=allow_installation_diagnostic,
    )
    receipt = capabilities.as_dict()
    normalized_host = capabilities.execution_host or "unknown"
    normalized_platform = capabilities.platform
    normalized_tools = capabilities.capabilities
    eligibility = filter_eligible_catalog(
        catalog,
        host=normalized_host,
        platform=normalized_platform,
        available_tools=normalized_tools,
        inference_surface=capabilities.inference_surface,
        capability_status=capabilities.status,
    )
    eligible_catalog = list(eligibility.eligible)
    eligible_slugs = {
        str(agent.get("slug") or agent.get("agent_slug") or "").strip()
        for agent in eligible_catalog
    }
    bounded_semantic_roots = (
        None
        if semantic_root_ids is None
        else frozenset(
            slug
            for item in semantic_root_ids[:MAX_ACTIVE_ROSTER_SIZE]
            if (slug := str(item or "").strip()[:MAX_ROUTING_TOKEN_CHARS])
            and slug in eligible_slugs
        )
    )
    policy = load_policy(policy_path_for_config(config))
    base_fingerprint = routing_fingerprint(eligible_catalog, config, policy)
    fingerprint = hashlib.sha256(
        "\0".join(
            (
                base_fingerprint,
                capabilities.surface,
                normalized_host,
                capabilities.inference_surface,
                normalized_platform,
                capabilities.status,
                "*" if bounded_semantic_roots is None else ",".join(sorted(bounded_semantic_roots)),
                *normalized_tools,
                *capabilities.unknown_tools,
            )
        ).encode("utf-8")
    ).hexdigest()
    refined = refine_query(user_message, config)
    routing_query = expand_query(affirmative_intent(refined))
    return _RouteRequest(
        session_id=session_id,
        user_message=user_message,
        catalog=eligible_catalog,
        config=config,
        policy=policy,
        context_fingerprint=fingerprint,
        routing_query=routing_query,
        cache_key=cache_key(routing_query, context_fingerprint=fingerprint),
        source_message_hash=hashlib.sha256(user_message.encode("utf-8")).hexdigest(),
        active_ids=catalog_active_ids(eligible_catalog, context_fingerprint=fingerprint),
        surface=capabilities.surface,
        host=normalized_host,
        inference_surface=capabilities.inference_surface,
        platform=normalized_platform,
        available_tools=normalized_tools,
        capability_status=capabilities.status,
        capability_receipt=receipt,
        eligibility_rejections=eligibility.rejected,
        semantic_root_ids=bounded_semantic_roots,
    )


def routing_context_fingerprint(
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
    *,
    session_id: str = "fingerprint",
    trace_id: str = "fingerprint",
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: tuple[str, ...] | None = None,
    capability_receipt: HostCapabilityReceipt | None = None,
) -> str:
    """Return the exact policy/config/catalog identity used by routing."""

    return _route_request(
        session_id,
        "fingerprint",
        catalog,
        config,
        trace_id=trace_id,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
    ).context_fingerprint


def _route_signals(request: _RouteRequest) -> _RouteSignals:
    validation = validate_policy(request.policy, request.active_ids)
    matched_actions, companion_ids = detect_actions(
        request.user_message,
        request.policy,
        active_slugs=request.active_ids,
    )
    matched_actions = _bounded_unique_strings(matched_actions)
    companion_ids = _bounded_unique_strings(companion_ids)
    fallback_ids = _bounded_unique_strings(detect_fallback_companions(request.policy))
    available, unavailable = _available_companions(
        companion_ids,
        request.active_ids,
    )
    available_fallbacks, unavailable_fallbacks = _available_companions(
        fallback_ids,
        request.active_ids,
    )
    return _RouteSignals(
        policy_validation=validation,
        matched_actions=matched_actions,
        companion_ids=companion_ids,
        available_companion_ids=available,
        unavailable_companion_ids=unavailable,
        work_units=_bounded_work_units(detect_work_units(request.user_message)),
        fallback_companion_ids=fallback_ids,
        available_fallback_companion_ids=available_fallbacks,
        unavailable_fallback_companion_ids=unavailable_fallbacks,
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


def _finalize_classified_request(
    routing: dict[str, Any],
    request: _RouteRequest,
    classification: TurnClassification,
    *,
    store: Store | None,
    trace_id: str | None,
) -> dict[str, Any]:
    """Attach current-turn intent without mutating cached routing evidence."""

    classified = dict(routing)
    reused = bool(classified.get("cache_hit") or classified.get("session_reused"))
    if reused:
        # A valid continuation may reuse a prior decision, but the provider
        # attempts belong to the earlier turn and must not become current-turn
        # evidence merely because the selection was cached.
        classified.update(
            inference_required=False,
            inference_attempted=False,
            inference_mode="cached",
            provider_attempts=[],
            inference_failures=[],
        )
    classified.update(
        turn_kind=classification.turn_kind,
        selection_required=classification.selection_required,
        reroute_required=classification.reroute_required,
        execution_decision_required=classification.execution_decision_required,
        continuation_of=classification.continuation_of,
        classifier_version=classification.classifier_version,
        state_revision=classification.state_revision,
    )
    return _finalize_request(classified, request, store=store, trace_id=trace_id)


def _exact_cached_routing(
    cached: dict[str, Any] | None,
    request: _RouteRequest,
) -> dict[str, Any] | None:
    if cached is None or cached.get("source_message_hash") != request.source_message_hash:
        return None
    cached_ids = cached.get("selected_ids", [])
    return cached if all(str(slug) in request.active_ids for slug in cached_ids) else None


def _compatibility_projection_is_current(
    routing: dict[str, Any],
    request: _RouteRequest,
) -> bool:
    """Prove an exact cache hit already satisfies the live set contract."""

    receipt = routing.get("compatibility")
    if not isinstance(receipt, dict):
        return False
    if receipt.get("contract_version") != COMPATIBILITY_CONTRACT_VERSION:
        return False
    if receipt.get("selection_limit") != max(
        0,
        min(int(request.config.judge.max_selected), MAX_COMPATIBLE_SPECIALISTS),
    ):
        return False
    selected_ids = _bounded_unique_strings(routing.get("selected_ids"))
    compatible_ids = _bounded_unique_strings(receipt.get("selected_ids"))
    if routing.get("fallback_applied"):
        fallback_ids = set(_bounded_unique_strings(routing.get("fallback_companion_ids")))
        return (
            not compatible_ids and bool(selected_ids) and set(selected_ids).issubset(fallback_ids)
        )
    return selected_ids == compatible_ids


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
        catalog=request.catalog,
        max_selected=request.config.judge.max_selected,
        user_message=request.user_message,
    )
    if refreshed is not None:
        refreshed["source_message_hash"] = request.source_message_hash
    return refreshed


def _semantic_catalog(
    request: _RouteRequest,
    signals: _RouteSignals,
) -> list[dict[str, Any]]:
    """Exclude DEFAULT-only identities from ordinary semantic selection."""
    fallback_ids = set(signals.fallback_companion_ids)
    return [
        agent
        for agent in request.catalog
        if (
            (slug := str(agent.get("slug") or agent.get("agent_slug") or "")) not in fallback_ids
            and (request.semantic_root_ids is None or slug in request.semantic_root_ids)
        )
    ]


def _merge_computed_routing(
    routing: dict[str, Any],
    request: _RouteRequest,
    signals: _RouteSignals,
) -> dict[str, Any]:
    fallback_ids = set(signals.fallback_companion_ids)
    proposed_semantic_ids = [
        slug
        for slug in _bounded_unique_strings(routing.get("selected_ids"))
        if slug in request.active_ids and slug not in fallback_ids
    ]
    proposed_ids = list(proposed_semantic_ids)
    for companion_id in signals.available_companion_ids:
        if companion_id not in proposed_ids:
            proposed_ids.append(companion_id)
    semantic_status = str(routing.get("status") or "unknown")
    routing["selected_ids"] = proposed_ids
    routing = _apply_compatible_selection(
        routing,
        request.catalog,
        limit=request.config.judge.max_selected,
        review_overflow_ids=(
            tuple(signals.available_companion_ids)
            if _explicit_review_requested(request.user_message)
            else ()
        ),
    )
    merged_ids = list(routing["selected_ids"])
    semantic_ids = [slug for slug in proposed_semantic_ids if slug in merged_ids]
    selected_companion_ids = [
        slug for slug in signals.available_companion_ids if slug in merged_ids
    ]
    fallback_considered = not merged_ids
    fallback_applied = fallback_considered and bool(signals.available_fallback_companion_ids)
    if fallback_applied:
        merged_ids.extend(
            slug for slug in signals.available_fallback_companion_ids if slug not in merged_ids
        )

    companion_ids = list(signals.companion_ids)
    available_companion_ids = list(signals.available_companion_ids)
    unavailable_companion_ids = list(signals.unavailable_companion_ids)
    if fallback_considered:
        companion_ids.extend(
            slug for slug in signals.available_fallback_companion_ids if slug not in companion_ids
        )
        available_companion_ids.extend(
            slug
            for slug in signals.available_fallback_companion_ids
            if slug not in available_companion_ids
        )
        unavailable_companion_ids.extend(
            slug
            for slug in signals.unavailable_fallback_companion_ids
            if slug not in unavailable_companion_ids
        )
    if fallback_applied:
        routing["semantic_status"] = semantic_status
        routing["status"] = "policy_fallback"
        routing["source"] = "policy_fallback"
    validation = signals.policy_validation
    routing.update(
        selected_ids=merged_ids,
        semantic_ids=semantic_ids,
        companion_actions=_bounded_unique_strings(signals.matched_actions),
        companion_ids=_bounded_unique_strings(companion_ids),
        available_companion_ids=_bounded_unique_strings(available_companion_ids),
        unavailable_companion_ids=_bounded_unique_strings(unavailable_companion_ids),
        selected_companion_ids=_bounded_unique_strings(selected_companion_ids),
        fallback_companion_ids=_bounded_unique_strings(signals.fallback_companion_ids),
        fallback_considered=fallback_considered,
        fallback_applied=fallback_applied,
        policy_validation={
            "valid": validation["valid"],
            "errors": _bounded_unique_strings(
                validation["errors"],
                limit=16,
                chars=160,
            ),
            "enabled_count": len(validation["enabled_slugs"]),
            "disabled_count": validation["disabled_count"],
        },
        work_units=_bounded_work_units(signals.work_units),
        source_message_hash=request.source_message_hash,
        execution_context=dict(request.capability_receipt),
        eligibility_rejections=[dict(item) for item in request.eligibility_rejections],
    )
    return routing


def _apply_compatible_selection(
    routing: dict[str, Any],
    catalog: list[dict[str, Any]],
    *,
    limit: int = MAX_COMPATIBLE_SPECIALISTS,
    review_overflow_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Enforce explicit requirements and conflicts on one judge proposal."""

    compatible = enforce_compatible_set(
        routing.get("selected_ids", []),
        catalog,
        limit=limit,
        review_overflow_ids=review_overflow_ids,
    )
    routing["selected_ids"] = list(compatible["selected_ids"])
    routing["compatibility"] = compatible
    if compatible["requested_ids"] and not compatible["selected_ids"]:
        routing["status"] = "abstained"
        routing["error"] = "selected specialists failed compatibility constraints"
    return routing


def _remember_routing(routing: dict[str, Any], request: _RouteRequest) -> None:
    if not routing.get("selected_ids"):
        return
    cache_put(request.cache_key, routing)
    if routing.get("fallback_applied"):
        return
    session_put(
        request.session_id,
        request.routing_query,
        routing,
        context_fingerprint=request.context_fingerprint,
    )


def _requires_fresh_selection(classification: TurnClassification) -> bool:
    """Return whether current intent must bypass cache and session stickiness."""

    rerouted_intent = classification.reroute_required or classification.turn_kind in {
        "new_intent",
        "revision",
    }
    return bool(classification.selection_required and rerouted_intent)


def route(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    *,
    config: AgencyConfig | None = None,
    store: Store | None = None,
    trace_id: str | None = None,
    turn_classification: TurnClassification | None = None,
    turn_state: TurnState | Mapping[str, Any] | None = None,
    host: str = "unknown",
    platform: str = "unknown",
    available_tools: tuple[str, ...] | None = None,
    capability_receipt: HostCapabilityReceipt | None = None,
    capability_session_id: str = "",
    capability_trace_id: str = "",
    allow_installation_diagnostic: bool = False,
    semantic_root_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Run the full 8-layer routing pipeline.

    Args:
        session_id: Session identifier for stickiness.
        user_message: The user's raw message text.
        catalog: Agent catalog to route against. If None, caller must provide.
        config: Optional config override.
        turn_classification: Precomputed classification from the owning turn lifecycle.
        turn_state: Durable state used only when no precomputed classification is supplied.

    Returns:
        Routing dict with keys: selected_ids, confidence, latency_ms, status,
        companion_actions, companion_ids, work_units, and possibly cache_hit,
        session_reused.
    """
    cfg = _get_config(config, store)
    classification = _turn_classification(
        user_message,
        turn_classification=turn_classification,
        turn_state=turn_state,
    )
    request = _route_request(
        session_id,
        user_message,
        catalog if catalog is not None else [],
        cfg,
        trace_id=trace_id or "route",
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
        capability_session_id=capability_session_id,
        capability_trace_id=capability_trace_id,
        allow_installation_diagnostic=allow_installation_diagnostic,
        semantic_root_ids=semantic_root_ids,
    )
    if not classification.selection_required:
        # Exact controls and a proven pure acknowledgement backed by explicitly
        # current, no-pending state do not require semantic specialist
        # selection. Social conversation still considers the roster. Resolve
        # deterministic policy directly without spending a provider call or
        # inheriting stale session stickiness.
        routing = _merge_computed_routing(
            {
                "selected_ids": [],
                "confidence": 0.0,
                "latency_ms": 0,
                "status": "abstained",
                "error": "turn kind does not require semantic specialist selection",
                "candidate_count": 0,
                "top_score": 0.0,
                "inference_configured": inference_is_configured(cfg),
                "inference_required": False,
                "inference_attempted": False,
                "inference_mode": "deterministic",
                "provider_attempts": [],
                "inference_failures": [],
            },
            request,
            _route_signals(request),
        )
        return _finalize_classified_request(
            routing,
            request,
            classification,
            store=store,
            trace_id=trace_id,
        )
    fresh_selection_required = _requires_fresh_selection(classification)
    cached = None if fresh_selection_required else cache_get(request.cache_key)
    exact = _exact_cached_routing(cached, request)
    signals: _RouteSignals | None = None
    if exact is not None:
        if _compatibility_projection_is_current(exact, request):
            return _finalize_classified_request(
                exact,
                request,
                classification,
                store=store,
                trace_id=trace_id,
            )
        signals = _route_signals(request)
        exact = _reuse_routing(exact, request, signals)
        if exact is not None:
            _remember_routing(exact, request)
            return _finalize_classified_request(
                exact,
                request,
                classification,
                store=store,
                trace_id=trace_id,
            )
    signals = signals or _route_signals(request)
    reused = _reuse_routing(cached, request, signals)
    if reused is not None:
        return _finalize_classified_request(
            reused,
            request,
            classification,
            store=store,
            trace_id=trace_id,
        )
    session_result = None
    if not fresh_selection_required:
        session_result = session_check(
            request.session_id,
            request.routing_query,
            context_fingerprint=request.context_fingerprint,
            valid_ids=request.active_ids,
        )
    reused = _reuse_routing(session_result, request, signals)
    if reused is not None:
        return _finalize_classified_request(
            reused,
            request,
            classification,
            store=store,
            trace_id=trace_id,
        )
    # `query_judge` makes inference mandatory when configured and otherwise
    # performs a visible deterministic fallback. Both modes operate on a fresh
    # selection for new, revised, or explicitly rerouted intent.
    semantic_catalog = _semantic_catalog(request, signals)
    routing = query_judge(
        request.routing_query,
        semantic_catalog,
        config=cfg,
    )
    routing = _merge_computed_routing(routing, request, signals)
    _remember_routing(routing, request)
    return _finalize_classified_request(
        routing,
        request,
        classification,
        store=store,
        trace_id=trace_id,
    )


def build_routing_context(routing: dict[str, Any], config: AgencyConfig | None = None) -> str:
    """Build the [AGENCY PREFLIGHT] context string from a routing result."""
    cfg = _get_config(config)
    selected = _bounded_unique_strings(routing.get("selected_ids"), limit=16)
    try:
        confidence = float(routing.get("confidence", 0.0))
    except (TypeError, ValueError, OverflowError):
        confidence = 0.0
    confidence = confidence if math.isfinite(confidence) else 0.0
    cache_hit = routing.get("cache_hit", False)
    session_reused = routing.get("session_reused", False)
    status = _bounded_signal_text(routing.get("status") or "unknown", 64)

    source = _bounded_signal_text(routing.get("source") or "llm", 64)
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
                f"(status={status}). Preserve this explicit abstention unless materially "
                f"new expertise is needed; if it is, {SPECIALIST_TOOL_GUIDANCE}, then "
                "include the Agency header in your response."
            )
    else:
        agents_list = ", ".join(selected)
        parts.append(
            f"[AGENCY PREFLIGHT] Specialist routing suggestion "
            f"(confidence={confidence:.1f}, source={source}): {agents_list}"
        )

    work_units = _bounded_work_units(routing.get("work_units"))
    if work_units.get("delegate", False) and work_units.get("count", 1) >= 2:
        unit_count = work_units["count"]
        unit_source = work_units.get("source", "unknown")
        unit_confidence = work_units.get("confidence", "low")
        units_list = [unit for unit in work_units.get("units", []) if str(unit).strip()]

        delegation_mode = cfg.delegation.mode
        if delegation_mode == "observe":
            policy_text = (
                "OBSERVE ONLY: expose the plan to the native host without an Agency "
                "delegation correction."
            )
        elif delegation_mode == "strong":
            policy_text = "STRONGLY PREFER native delegation for every eligible row."
        else:
            policy_text = "PREFER native delegation according to the bounded plan strength."
        nudge = (
            f"\n\n[DELEGATION OPPORTUNITY] {unit_count} independent work units "
            f"detected (confidence={unit_confidence}, source={unit_source}). "
            f"{policy_text} {NATIVE_DELEGATION_GUIDANCE} "
            "Keep the main session available for the user."
        )
        if units_list:
            nudge += "\n  Detected work units:"
            for i, unit in enumerate(units_list, 1):
                unit_text = _bounded_signal_text(unit, MAX_WORK_UNIT_CHARS)
                unit_id = work_unit_id_from_text(unit_text)
                unit_preview = _bounded_signal_text(unit_text, MAX_WORK_UNIT_PREVIEW_CHARS)
                nudge += f"\n    {i}. [{unit_id}] {unit_preview}"
            nudge += f"\n  {WORK_UNIT_CORRELATION_GUIDANCE}"
        parts.append(nudge)

    parts.append(HEADER_INSTRUCTION)
    return "\n".join(parts)[:MAX_ROUTING_CONTEXT_CHARS]


def route_and_build_context(
    session_id: str,
    user_message: str,
    catalog: list[dict[str, Any]] | None = None,
    config: AgencyConfig | None = None,
    store: Store | None = None,
    trace_id: str | None = None,
    turn_classification: TurnClassification | None = None,
    turn_state: TurnState | Mapping[str, Any] | None = None,
) -> str:
    """Run the full pipeline and return its routing context projection."""
    cfg = _get_config(config)
    routing = route(
        session_id,
        user_message,
        catalog,
        config=cfg,
        store=store,
        trace_id=trace_id,
        turn_classification=turn_classification,
        turn_state=turn_state,
    )
    return build_routing_context(routing, cfg)


HEADER_INSTRUCTION = (
    "\n  Treat the current [AGENCY LOADED] capsule as the authoritative "
    "specialist context for this turn. Earlier-turn specialist capsules are "
    "expired. Only use the host's installed Agency specialist tools "
    "(`agency.search_agents` and `agency.load_specialist` on MCP surfaces) when "
    "the current capsule is absent or additional expertise is materially needed. "
    "Include the Agency header in your response:\n"
    "  Agency/Agencies loaded: <agent-id>\n"
    "  Agency/Agencies delegated: <agent-id>\n"
    "  Skills loaded: <skill-id[, skill-id...] or none>\n"
    "  Actual Model selected: <requested alias> -> <resolved provider/model>\n"
    "  Why: <one line>\n"
    "  How it shaped outcome: <one line>"
)
