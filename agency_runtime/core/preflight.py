"""Shared, trace-scoped specialist preflight orchestration."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Mapping
from dataclasses import replace
from hashlib import sha256
from inspect import signature
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    current_host_capability_receipt,
)
from agency_runtime.core.preflight_recipe import (
    MAX_PREFLIGHT_CONTEXT_CHARS as _MAX_PREFLIGHT_CONTEXT_CHARS,
)
from agency_runtime.core.preflight_recipe import (
    PREFLIGHT_REPLAY_RECIPE_VERSION,
    PreflightResult,
    _await_ready_result,
    _combine_context,
    _content_free_routing_recipe,
    _context_policy_fingerprint,
    _read_ready_result,
    _resident_manager_context,
    _result_from_recipe,
    _suggestion_recipe,
    _verified_work_units,
    preflight_delivery_policy,
)
from agency_runtime.core.resident_managers import is_resident_manager_slug
from agency_runtime.core.routing_snapshot import (
    capture_routing_snapshot,
    catalog_for_routing,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import (
    TurnClassification,
    TurnState,
    classify_turn_intent,
    force_fresh_turn_reroute,
)
from agency_runtime.core.turn_origin import TurnOriginReceipt, current_turn_origin
from agency_runtime.core.unit_assignment import assignment_agents_from_catalog

MAX_PREFLIGHT_CONTEXT_CHARS = _MAX_PREFLIGHT_CONTEXT_CHARS
_MAX_CHILD_ROUTE_TIMEOUT_SECONDS = 60.0
_CHILD_ROUTE_LEASE_MARGIN_SECONDS = 5.0


def _normalize_parent_correlation(
    parent_session_id: object,
    parent_trace_id: object,
) -> tuple[str, str]:
    """Validate optional native-child parent correlation as one atomic pair."""

    if bool(parent_session_id) != bool(parent_trace_id):
        raise ValueError("parent_session_id and parent_trace_id must be supplied together")
    if not parent_session_id:
        return "", ""
    return (
        validate_correlation_id(parent_session_id, field="parent_session_id"),
        validate_correlation_id(parent_trace_id, field="parent_trace_id"),
    )


def _child_route_timeout(config: AgencyConfig) -> float:
    """Cover the longest configured inference attempt within the judge deadline."""

    configured = [float(config.judge.timeout)]
    configured.extend(float(provider.timeout) for provider in config.providers)
    return min(_MAX_CHILD_ROUTE_TIMEOUT_SECONDS, max(1.0, *configured))


def _suggested_specialist_slugs(suggestions: list[dict[str, Any]]) -> list[str]:
    """Flatten bounded compatible sets while preserving primary-first order."""

    result: list[str] = []
    for suggestion in suggestions:
        raw = suggestion.get("recommended_agents")
        candidates = raw if isinstance(raw, list) and raw else [suggestion.get("recommended_agent")]
        for value in candidates:
            slug = str(value or "").strip()
            if slug and slug not in result:
                result.append(slug)
                if len(result) == 16:
                    return result
    return result


def _turn_state_for_preflight(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
) -> TurnState:
    """Read durable prior-turn state or fail closed when it is unavailable."""

    getter = getattr(store, "get_turn_state_context", None)
    if not callable(getter):
        return TurnState(state_known=False, state_status="missing")
    try:
        value = getter(session_id, before_trace_id=trace_id)
    except Exception:
        return TurnState(state_known=False, state_status="missing")
    if not isinstance(value, Mapping):
        return TurnState(state_known=False, state_status="corrupt")
    return TurnState.from_mapping(value)


def _catalog_with_policy(store: Store, disabled_agents: frozenset[str]) -> list[dict]:
    """Read a policy-filtered catalog without breaking legacy Store facades."""

    return catalog_for_routing(
        store,
        disabled_agents,
        signature_reader=signature,
    )


def _specialist_hydration_routing(
    routing: dict[str, Any],
    *,
    delivery_mode: str,
    suggestions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Choose prompt bodies that may safely share one host context.

    Isolated hosts prepare every planned specialist for a separate native child.
    Direct hosts have no equivalent context boundary, so they receive one
    directive specialist by default. Resident managers use their own compact
    parent kernel and are never hydrated as ordinary specialists. Other selected
    identities remain visible as routing suggestions without having their raw
    instructions concatenated.
    """

    if delivery_mode == "isolated":
        if not suggestions:
            selected = list(routing.get("selected_ids", []))
        else:
            selected = _suggested_specialist_slugs(suggestions)
    else:
        selected = [
            str(slug).strip() for slug in routing.get("selected_ids", []) if str(slug).strip()
        ]
    selected = [slug for slug in selected if not is_resident_manager_slug(slug)]
    if delivery_mode != "isolated":
        selected = selected[:1]
    if selected == routing.get("selected_ids"):
        return routing
    return {**routing, "selected_ids": selected}


def _selection_refs_for_recipe(
    store: Store,
    catalog: list[dict[str, Any]],
    routing: dict[str, Any],
    suggestions: list[dict[str, Any]],
    specialist_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Bind every nonresident selection/assignment to its active revision."""

    ordered_slugs: list[str] = []
    for raw_slug in [
        *routing.get("selected_ids", []),
        *_suggested_specialist_slugs(suggestions),
        *(item.get("slug") for item in specialist_refs),
    ]:
        slug = str(raw_slug or "").strip()
        if slug and not is_resident_manager_slug(slug) and slug not in ordered_slugs:
            ordered_slugs.append(slug)
    if len(ordered_slugs) > 16:
        raise RuntimeError("continuation selection exceeds the durable reference limit")
    catalog_by_slug = {str(item.get("slug") or ""): item for item in catalog}
    hydrated_by_slug = {str(item.get("slug") or ""): item for item in specialist_refs}
    result: list[dict[str, Any]] = []
    for slug in ordered_slugs:
        catalog_entry = catalog_by_slug.get(slug, {})
        hydrated = hydrated_by_slug.get(slug, {})
        active = catalog_entry
        if not active.get("version") or not active.get("hash"):
            active = store.get_roster_entry(slug) or {}
        version = str(active.get("version") or hydrated.get("version") or "").strip()
        content_hash = str(active.get("hash") or hydrated.get("hash") or "").strip()
        if (
            not version
            or len(content_hash) != 64
            or any(character not in "0123456789abcdef" for character in content_hash)
        ):
            raise RuntimeError(f"selected specialist '{slug}' lacks an active revision identity")
        capabilities = hydrated.get("capabilities", catalog_entry.get("capabilities", []))
        result.append(
            {
                "slug": slug,
                "version": version,
                "hash": content_hash,
                "description": str(
                    hydrated.get("description") or catalog_entry.get("description") or ""
                )[:256],
                "capabilities": [
                    str(capability)[:64]
                    for capability in (capabilities if isinstance(capabilities, list) else [])[:4]
                    if str(capability).strip()
                ],
            }
        )
    return result


def _reused_continuation_routing(
    source_routing: dict[str, Any],
    *,
    trace_id: str,
    user_message: str,
    context_fingerprint: str,
) -> dict[str, Any]:
    """Copy only the validated source selection under current-turn identities."""

    current_hash = sha256(user_message.encode("utf-8", errors="surrogatepass")).hexdigest()
    return {
        **source_routing,
        "trace_id": trace_id,
        "query_hash": current_hash,
        "source_message_hash": current_hash,
        "context_fingerprint": context_fingerprint,
        "origin_trace_id": str(source_routing.get("trace_id") or ""),
        "origin_query_hash": str(source_routing.get("query_hash") or ""),
        "origin_context_fingerprint": str(source_routing.get("context_fingerprint") or ""),
        "status": "continuation_reused",
        "source": "durable_continuation",
        "latency_ms": 0,
        "cache_hit": False,
        "session_reused": False,
        "continuation_reused": True,
        "continuation_resolution_required": False,
    }


def _ensure_preflight_catalog(
    store: Store,
    config: AgencyConfig,
    routing_snapshot: Any,
    *,
    seed_starter_roster: Any,
    ensure_no_match_fallback_roster: Any,
) -> Any:
    """Refresh the atomic roster snapshot after any required bootstrap mutation."""

    if not routing_snapshot.catalog:
        seed_starter_roster(store)
        return capture_routing_snapshot(store, config)
    if ensure_no_match_fallback_roster(store):
        return capture_routing_snapshot(store, config)
    return routing_snapshot


def _resolve_preflight_routing(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    user_message: str,
    host: str,
    platform: str,
    available_tools: tuple[str, ...],
    capability_receipt: HostCapabilityReceipt,
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
    classification: TurnClassification,
    routing_fingerprint: str,
    policy_fingerprint: str,
    roster_generation: int,
    pipeline: Any,
    parent_session_id: str = "",
    parent_trace_id: str = "",
) -> tuple[dict[str, Any], dict[str, Any] | None, TurnClassification]:
    """Reuse one validated source recipe or produce a safe current route."""

    continuation_snapshot: dict[str, Any] | None = None
    continuation_resolver = getattr(store, "resolve_durable_continuation", None)
    if (
        classification.turn_kind == "continuation"
        and not classification.reroute_required
        and classification.continuation_of
        and callable(continuation_resolver)
    ):
        continuation_snapshot = continuation_resolver(
            session_id=session_id,
            trace_id=trace_id,
            source_trace_id=classification.continuation_of,
            host=host,
            routing_fingerprint=routing_fingerprint,
            context_policy_fingerprint=policy_fingerprint,
            roster_generation=roster_generation,
        )
    if continuation_snapshot is not None:
        reused = _reused_continuation_routing(
            continuation_snapshot["recipe"]["routing"],
            trace_id=trace_id,
            user_message=user_message,
            context_fingerprint=routing_fingerprint,
        )
        reused["execution_context"] = capability_receipt.as_dict()
        return reused, continuation_snapshot, classification
    if classification.turn_kind == "continuation" and not classification.reroute_required:
        classification = force_fresh_turn_reroute(
            classification,
            "continuation_guard_invalid",
        )
    route_arguments = {
        "config": config,
        "store": None,
        "trace_id": trace_id,
        "turn_classification": classification,
        "host": host,
        "platform": platform,
        "available_tools": available_tools,
        "capability_receipt": capability_receipt,
    }
    if not parent_trace_id:
        return (
            pipeline.route(session_id, user_message, catalog, **route_arguments),
            None,
            classification,
        )

    from agency_runtime.core.selector.judge import inference_is_configured

    if not inference_is_configured(config):
        routing = pipeline.route(session_id, user_message, catalog, **route_arguments)
        routing["child_routing_source"] = "deterministic_unconfigured"
        return routing, None, classification

    cache_material = "\0".join(
        (
            "agency-child-route-v1",
            sha256(user_message.encode("utf-8", errors="surrogatepass")).hexdigest(),
            routing_fingerprint,
            policy_fingerprint,
            str(roster_generation),
            host,
            platform,
            "\x1f".join(available_tools),
        )
    )
    child_cache_key = sha256(cache_material.encode("utf-8")).hexdigest()
    route_timeout = _child_route_timeout(config)
    reservation = store.reserve_child_routing(
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        cache_key=child_cache_key,
        budget=config.delegation.child_inference_budget,
        concurrency=config.delegation.child_inference_concurrency,
        lease_seconds=route_timeout + _CHILD_ROUTE_LEASE_MARGIN_SECONDS,
    )
    if reservation["status"] == "coalescing":
        deadline = time.monotonic() + route_timeout + _CHILD_ROUTE_LEASE_MARGIN_SECONDS
        while time.monotonic() < deadline:
            cached = store.read_child_routing_cache(child_cache_key)
            if cached is not None:
                reservation = {"status": "cached", "decision": cached}
                break
            time.sleep(0.05)
    if reservation["status"] == "cached":
        cached = dict(reservation["decision"])
        current_hash = sha256(user_message.encode("utf-8", errors="surrogatepass")).hexdigest()
        cached.update(
            trace_id=trace_id,
            query_hash=current_hash,
            source_message_hash=current_hash,
            context_fingerprint=routing_fingerprint,
            source="durable_child_cache",
            status="child_cache_reused",
            latency_ms=0,
            cache_hit=True,
            session_reused=False,
            child_routing_source="shared_cache",
        )
        cached["execution_context"] = capability_receipt.as_dict()
        cached["work_units"] = _verified_work_units(cached, user_message)
        return cached, None, classification
    if reservation["status"] == "owner":
        owner_token = str(reservation["owner_token"])
        try:
            routing = pipeline.route(session_id, user_message, catalog, **route_arguments)
            store.complete_child_routing(
                cache_key=child_cache_key,
                owner_token=owner_token,
                decision=_content_free_routing_recipe(routing, trace_id=trace_id),
                ttl_seconds=config.delegation.child_cache_ttl_seconds,
            )
        except BaseException:
            store.abort_child_routing(cache_key=child_cache_key, owner_token=owner_token)
            raise
        routing["child_routing_source"] = "parent_budgeted_inference"
        return routing, None, classification

    deterministic_config = replace(
        config,
        providers=(),
        judge=replace(
            config.judge,
            model="",
            base_url="",
            api_key="",
            api_key_env="",
            ollama_mode=False,
        ),
        ollama=replace(config.ollama, enabled=False),
    )
    route_arguments["config"] = deterministic_config
    routing = pipeline.route(session_id, user_message, catalog, **route_arguments)
    deterministic_candidates = list(routing.get("selected_ids", []))
    routing.update(
        selected_ids=[],
        confidence=0.0,
        status="child_budget_abstained",
        source="child_budget_policy",
        deterministic_candidate_ids=deterministic_candidates,
        child_routing_source=str(reservation["status"]),
        child_inference_budget_exhausted=reservation["status"] == "budget_exhausted",
    )
    return routing, None, classification


def _assignment_recipe(
    catalog: list[dict[str, Any]],
    routing: dict[str, Any],
    continuation_snapshot: dict[str, Any] | None,
    config: AgencyConfig,
    *,
    session_id: str,
    trace_id: str,
    host: str,
    platform: str,
    available_tools: tuple[str, ...],
    capability_receipt: HostCapabilityReceipt,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if routing.get("status") == "child_budget_abstained":
        return [], []
    if continuation_snapshot is not None:
        source = continuation_snapshot["recipe"]
        return list(source.get("unit_assignment_agents", [])), list(
            source.get("unit_agent_plan", [])
        )
    assignment_agents = assignment_agents_from_catalog(
        catalog,
        routing,
        config=config,
        session_id=session_id,
        trace_id=trace_id,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
    )
    return assignment_agents, _suggestion_recipe(
        {**routing, "unit_assignment_agents": assignment_agents},
        config.delegation,
    )


def _recipe_revision_refs(
    store: Store,
    catalog: list[dict[str, Any]],
    routing: dict[str, Any],
    suggestions: list[dict[str, Any]],
    loaded: Any,
    continuation_snapshot: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specialist_refs = [reference.as_dict() for reference in loaded.references]
    if continuation_snapshot is None:
        return specialist_refs, _selection_refs_for_recipe(
            store,
            catalog,
            routing,
            suggestions,
            specialist_refs,
        )
    source = continuation_snapshot["recipe"]
    source_specialist_refs = list(source.get("specialist_refs", []))
    identity_fields = ("slug", "version", "hash")
    if [
        tuple(reference.get(field) for field in identity_fields) for reference in specialist_refs
    ] != [
        tuple(reference.get(field) for field in identity_fields)
        for reference in source_specialist_refs
    ]:
        raise RuntimeError("continuation specialist revisions changed during hydration")
    return source_specialist_refs, list(source.get("selection_refs", []))


def _require_available_unit_plan_agents(
    *,
    delivery_mode: str,
    suggestions: list[dict[str, Any]],
    loaded_slugs: tuple[str, ...],
) -> None:
    """Fail before ready commit when any persisted assignment is unpreparable."""

    if delivery_mode != "isolated" or not suggestions:
        return
    planned_agents = set(_suggested_specialist_slugs(suggestions))
    missing_agents = planned_agents.difference(loaded_slugs)
    if missing_agents:
        missing = ", ".join(sorted(missing_agents))
        raise RuntimeError(f"unit-agent plan has unavailable specialist prompts: {missing}")


def _resident_binding_for_preflight(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    host: str,
) -> tuple[Any, str]:
    """Plan one binding and render its exact current-turn manager context."""

    binding_planner = getattr(store, "plan_resident_manager_binding", None)
    if not callable(binding_planner):
        raise RuntimeError("evidence store cannot bind resident managers")
    binding = binding_planner(session_id=session_id, host=host)
    return binding, _resident_manager_context(
        binding,
        session_id=session_id,
        trace_id=trace_id,
    )


def _mark_ready_with_binding_replan(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    attempt_token: str,
    recipe: dict[str, Any],
    host: str,
    routing_recipe: dict[str, Any],
    suggestions: list[dict[str, Any]],
    specialist_refs: list[dict[str, Any]],
    user_message: str,
    config: AgencyConfig,
    pipeline: Any,
) -> dict[str, str]:
    """Commit ready evidence, replanning one stale manager binding at most once."""

    arguments = {
        "session_id": session_id,
        "trace_id": trace_id,
        "attempt_token": attempt_token,
        "recipe": recipe,
        "host": host,
        "routing_evidence": routing_recipe,
        "suggestions": suggestions,
        "specialist_refs": specialist_refs,
    }
    ready = store.mark_preflight_ready(**arguments)
    if not isinstance(ready, dict) or ready.get("outcome") != "binding_conflict":
        return ready

    resident_binding, _resident_context = _resident_binding_for_preflight(
        store,
        session_id=session_id,
        trace_id=trace_id,
        host=host,
    )
    recipe["resident_manager_binding"] = resident_binding.as_dict()
    _result_from_recipe(
        store,
        recipe,
        session_id=session_id,
        trace_id=trace_id,
        user_message=user_message,
        config=config,
        pipeline=pipeline,
    )
    return store.mark_preflight_ready(**arguments)


def _prepare_preflight_evidence(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    user_message: str,
    host: str,
    platform: str,
    runtime_capabilities: HostCapabilityReceipt,
    catalog: list[dict[str, Any]],
    config: AgencyConfig,
    classification: TurnClassification,
    routing_fingerprint: str,
    policy_fingerprint: str,
    roster_generation: int,
    delivery_mode: str,
    context_limit: int,
    resident_binding: Any,
    resident_context: str,
    pipeline: Any,
    parent_session_id: str = "",
    parent_trace_id: str = "",
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    TurnClassification,
]:
    """Build one replay-safe recipe without committing its lifecycle state."""

    from agency_runtime.core.specialist_context import (
        MAX_SPECIALIST_CONTEXT_CHARS,
        hydrate_selected_specialist_context,
    )

    routing, continuation_snapshot, classification = _resolve_preflight_routing(
        store,
        session_id=session_id,
        trace_id=trace_id,
        user_message=user_message,
        host=host,
        platform=platform,
        available_tools=runtime_capabilities.capabilities,
        capability_receipt=runtime_capabilities,
        catalog=catalog,
        config=config,
        classification=classification,
        routing_fingerprint=routing_fingerprint,
        policy_fingerprint=policy_fingerprint,
        roster_generation=roster_generation,
        pipeline=pipeline,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
    )
    routing = dict(routing)
    routing["trace_id"] = trace_id
    unit_assignment_agents, suggestions = _assignment_recipe(
        catalog,
        routing,
        continuation_snapshot,
        config,
        session_id=session_id,
        trace_id=trace_id,
        host=host,
        platform=platform,
        available_tools=runtime_capabilities.capabilities,
        capability_receipt=runtime_capabilities,
    )
    if delivery_mode == "isolated":
        specialist_budget = MAX_SPECIALIST_CONTEXT_CHARS
    else:
        routing_context = pipeline.build_routing_context(routing, config)
        manager_routing_context = _combine_context(
            resident_context,
            routing_context,
            maximum_chars=context_limit,
        )
        specialist_budget = max(0, context_limit - len(manager_routing_context) - 2)
    hydration_routing = _specialist_hydration_routing(
        routing,
        delivery_mode=delivery_mode,
        suggestions=suggestions,
    )
    loaded = hydrate_selected_specialist_context(
        store,
        catalog,
        hydration_routing,
        session_id=session_id,
        trace_id=trace_id,
        record_evidence=False,
        maximum_chars=specialist_budget,
        disabled_agents=frozenset(config.agents.disabled),
    )
    _require_available_unit_plan_agents(
        delivery_mode=delivery_mode,
        suggestions=suggestions,
        loaded_slugs=loaded.slugs,
    )
    routing_recipe = _content_free_routing_recipe(routing, trace_id=trace_id)
    specialist_refs, selection_refs = _recipe_revision_refs(
        store,
        catalog,
        routing,
        suggestions,
        loaded,
        continuation_snapshot,
    )
    recipe: dict[str, Any] = {
        "recipe_version": PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": policy_fingerprint,
        "session_id": session_id,
        "trace_id": trace_id,
        "host": host,
        "delivery_mode": delivery_mode,
        "context_limit": context_limit,
        "routing": routing_recipe,
        "specialist_refs": specialist_refs,
        "selection_refs": selection_refs,
        "unit_assignment_agents": unit_assignment_agents,
        "unit_agent_plan": suggestions,
        "trivial": not classification.selection_required,
        "turn_classification": classification.as_dict(),
        "resident_manager_binding": resident_binding.as_dict(),
        "roster_size": len(catalog),
        "roster_generation": roster_generation,
    }
    if continuation_snapshot is not None:
        recipe["continuation_guard"] = continuation_snapshot["guard"]
    _result_from_recipe(
        store,
        recipe,
        session_id=session_id,
        trace_id=trace_id,
        user_message=user_message,
        config=config,
        pipeline=pipeline,
    )
    return recipe, routing_recipe, suggestions, specialist_refs, classification


def _prepare_with_bounded_continuation_reroute(
    store: Store,
    *,
    classification: TurnClassification,
    prepare_arguments: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    TurnClassification,
]:
    """Retry one invalid durable continuation as a current fresh route."""

    try:
        return _prepare_preflight_evidence(
            store,
            classification=classification,
            **prepare_arguments,
        )
    except RuntimeError:
        if classification.turn_kind != "continuation" or classification.reroute_required:
            raise
    fresh = force_fresh_turn_reroute(
        classification,
        "continuation_recipe_invalid",
    )
    return _prepare_preflight_evidence(
        store,
        classification=fresh,
        **prepare_arguments,
    )


def run_preflight(
    store: Store,
    *,
    session_id: str,
    user_message: str,
    host: str,
    trace_id: str = "",
    config: AgencyConfig | None = None,
    persisted_user_message: str | None = None,
    reservation_token: str = "",
    capability_receipt: HostCapabilityReceipt | None = None,
    origin_receipt: TurnOriginReceipt | None = None,
    parent_session_id: str = "",
    parent_trace_id: str = "",
) -> PreflightResult:
    """Create one turn, route it, hydrate prompts, and persist exact evidence."""
    normalized_session = validate_correlation_id(session_id, field="session_id")
    normalized_parent_session, normalized_parent_trace = _normalize_parent_correlation(
        parent_session_id,
        parent_trace_id,
    )
    if not str(user_message or "").strip():
        raise ValueError("user_message is required for Agency preflight routing")

    from agency_runtime.core.installer import (
        ensure_no_match_fallback_roster,
        seed_starter_roster,
    )
    from agency_runtime.core.installer_payloads import hook_timeout_seconds
    from agency_runtime.core.selector import pipeline

    turn_trace_id = validate_correlation_id(
        trace_id or str(uuid.uuid4()),
        field="trace_id",
    )
    normalized_host = str(host or "unknown").strip() or "unknown"
    current_origin = current_turn_origin(
        origin_receipt,
        host=normalized_host,
        session_id=normalized_session,
        trace_id=turn_trace_id,
    )
    if current_origin is not None and current_origin.origin != "external_user":
        raise ValueError(
            "internal adapter lifecycle events must reuse or revalidate their exact turn; "
            "they cannot start Agency preflight"
        )
    runtime_platform = "windows" if os.name == "nt" else "linux"
    runtime_capabilities = current_host_capability_receipt(
        capability_receipt,
        surface=normalized_host,
        platform=runtime_platform,
        session_id=normalized_session,
        trace_id=turn_trace_id,
    )
    normalized_reservation_token = str(reservation_token or "").strip()
    attempt_token = ""
    attempt_owner = False
    try:
        routing_snapshot = capture_routing_snapshot(store, config)
        cfg = routing_snapshot.config
        delivery_mode, context_limit = preflight_delivery_policy(normalized_host)
        turn_state = _turn_state_for_preflight(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
        )
        classification = classify_turn_intent(user_message, turn_state)
        if current_origin is None:
            classification = force_fresh_turn_reroute(
                classification,
                "adapter_origin_untrusted",
                untrusted_origin=True,
            )
        request_kind = classification.legacy_request_kind
        request_fingerprint = sha256(
            str(user_message).encode("utf-8", errors="surrogatepass")
        ).hexdigest()
        persisted_source = (
            user_message if persisted_user_message is None else persisted_user_message
        )
        persisted_message = persisted_source if cfg.observability.capture_content else ""
        lease_seconds = hook_timeout_seconds(cfg)
        lifecycle = store.begin_preflight_attempt(
            trace_id=turn_trace_id,
            session_id=normalized_session,
            host=normalized_host,
            user_message=persisted_message,
            reservation_token=normalized_reservation_token,
            request_fingerprint=request_fingerprint,
            request_kind=request_kind,
            lease_seconds=lease_seconds,
            turn_classification=classification.as_dict(),
        )
        outcome = str(lifecycle.get("outcome") or "")
        if outcome == "conflict":
            raise ValueError("active trace_id belongs to a different preflight request")
        if outcome not in {
            "started",
            "recovered_started",
            "reused_in_progress",
            "reused_ready",
        }:
            raise RuntimeError(f"preflight attempt could not start: {outcome or 'unknown'}")
        attempt_token = str(lifecycle.get("attempt_token") or "")
        if not attempt_token:
            raise RuntimeError("preflight attempt identity was not persisted")
        if outcome == "reused_ready":
            return _read_ready_result(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
            )
        if outcome == "reused_in_progress":
            return _await_ready_result(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
                timeout_seconds=lease_seconds,
            )
        attempt_owner = outcome in {"started", "recovered_started"}
        resident_binding, resident_context = _resident_binding_for_preflight(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            host=normalized_host,
        )
        routing_snapshot = _ensure_preflight_catalog(
            store,
            cfg,
            routing_snapshot,
            seed_starter_roster=seed_starter_roster,
            ensure_no_match_fallback_roster=ensure_no_match_fallback_roster,
        )
        catalog = routing_snapshot.catalog

        routing_fingerprint = pipeline.routing_context_fingerprint(
            catalog,
            cfg,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            host=normalized_host,
            platform=runtime_platform,
            available_tools=runtime_capabilities.capabilities,
            capability_receipt=runtime_capabilities,
        )
        policy_fingerprint = _context_policy_fingerprint(
            cfg,
            pipeline,
            delivery_mode=delivery_mode,
            context_limit=context_limit,
        )
        prepare_arguments = {
            "session_id": normalized_session,
            "trace_id": turn_trace_id,
            "user_message": user_message,
            "host": normalized_host,
            "platform": runtime_platform,
            "runtime_capabilities": runtime_capabilities,
            "catalog": catalog,
            "config": cfg,
            "routing_fingerprint": routing_fingerprint,
            "policy_fingerprint": policy_fingerprint,
            "roster_generation": routing_snapshot.roster_generation,
            "delivery_mode": delivery_mode,
            "context_limit": context_limit,
            "resident_binding": resident_binding,
            "resident_context": resident_context,
            "pipeline": pipeline,
            "parent_session_id": normalized_parent_session,
            "parent_trace_id": normalized_parent_trace,
        }
        recipe, routing_recipe, suggestions, specialist_refs, classification = (
            _prepare_with_bounded_continuation_reroute(
                store,
                classification=classification,
                prepare_arguments=prepare_arguments,
            )
        )
        ready = _mark_ready_with_binding_replan(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            attempt_token=attempt_token,
            recipe=recipe,
            host=normalized_host,
            routing_recipe=routing_recipe,
            suggestions=suggestions,
            specialist_refs=specialist_refs,
            user_message=user_message,
            config=cfg,
            pipeline=pipeline,
        )
        if isinstance(ready, dict) and ready.get("outcome") == "continuation_guard_conflict":
            classification = force_fresh_turn_reroute(
                classification,
                "continuation_guard_changed_before_commit",
            )
            recipe, routing_recipe, suggestions, specialist_refs, classification = (
                _prepare_preflight_evidence(
                    store,
                    session_id=normalized_session,
                    trace_id=turn_trace_id,
                    user_message=user_message,
                    host=normalized_host,
                    platform=runtime_platform,
                    runtime_capabilities=runtime_capabilities,
                    catalog=catalog,
                    config=cfg,
                    classification=classification,
                    routing_fingerprint=routing_fingerprint,
                    policy_fingerprint=policy_fingerprint,
                    roster_generation=routing_snapshot.roster_generation,
                    delivery_mode=delivery_mode,
                    context_limit=context_limit,
                    resident_binding=resident_binding,
                    resident_context=resident_context,
                    pipeline=pipeline,
                    parent_session_id=normalized_parent_session,
                    parent_trace_id=normalized_parent_trace,
                )
            )
            ready = _mark_ready_with_binding_replan(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                recipe=recipe,
                host=normalized_host,
                routing_recipe=routing_recipe,
                suggestions=suggestions,
                specialist_refs=specialist_refs,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
            )
        if not isinstance(ready, dict) or ready.get("outcome") not in {
            "committed",
            "replay",
        }:
            raise RuntimeError("preflight attempt became terminal before it reached ready")
        return _read_ready_result(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            attempt_token=attempt_token,
            user_message=user_message,
            config=cfg,
            pipeline=pipeline,
        )
    except Exception as error:
        # Cleanup is an exact-token compare-and-set. A concurrent successful
        # caller may already own a ready attempt, and must never be closed by
        # this caller's failure path.
        try:
            if attempt_token and attempt_owner:
                store.fail_preflight_attempt(
                    session_id=normalized_session,
                    trace_id=turn_trace_id,
                    attempt_token=attempt_token,
                    status="preflight_failed",
                )
            elif not attempt_token and normalized_reservation_token:
                store.abandon_preflight_reservation(
                    session_id=normalized_session,
                    trace_id=turn_trace_id,
                    reservation_token=normalized_reservation_token,
                    status="preflight_failed",
                )
        except Exception as cleanup_error:
            raise error from cleanup_error
        raise


__all__ = ["MAX_PREFLIGHT_CONTEXT_CHARS", "PreflightResult", "run_preflight"]
