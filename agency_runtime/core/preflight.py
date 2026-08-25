"""Shared, trace-scoped specialist preflight orchestration."""

from __future__ import annotations

import copy
import os
import time
import uuid
from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
from inspect import signature
from math import ceil
from threading import Event, Thread, current_thread
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.content_redaction import redact_content
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    current_host_capability_receipt,
)
from agency_runtime.core.preflight_failure import (
    PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
    default_preflight_failure_reason,
    preflight_eligibility_reason_codes,
    preflight_exception_category,
    preflight_hiring_reason_codes,
    preflight_invariant_code,
    preflight_routing_failure_reason,
    preflight_staffing_reason_codes,
    project_preflight_provider_attempts,
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
    _verified_work_units,
    preflight_delivery_policy,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL_REFERENCE,
    RESIDENT_MANAGER_SLUGS,
    is_resident_manager_slug,
)
from agency_runtime.core.routing_snapshot import (
    bind_workforce_snapshot,
    capture_routing_snapshot,
    catalog_for_routing,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.store.version_identity import is_valid_version_identity
from agency_runtime.core.turn_intent import (
    TurnClassification,
    TurnState,
    classify_turn_intent,
    force_fresh_turn_reroute,
)
from agency_runtime.core.turn_origin import TurnOriginReceipt, current_turn_origin
from agency_runtime.core.turn_routing_context import (
    project_turn_routing_context,
    project_turn_routing_context_guard,
    turn_routing_context_revision,
)
from agency_runtime.core.unit_assignment import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_UNIT_SELECTION_WORKERS,
    assignment_agents_from_catalog,
    project_unit_assignment_agents,
)
from agency_runtime.core.workforce.cache import WORKFORCE_CACHE_IDENTITY_VERSION
from agency_runtime.core.workforce.planning_contracts import (
    PLAN_SCHEMA_VERSION,
    RECRUITMENT_SCHEMA_VERSION,
)

MAX_PREFLIGHT_CONTEXT_CHARS = _MAX_PREFLIGHT_CONTEXT_CHARS
_MAX_CHILD_ROUTE_TIMEOUT_SECONDS = 60.0
_CHILD_ROUTE_LEASE_MARGIN_SECONDS = 5.0
_CHILD_ROUTE_BUNDLE_VERSION = 2


class SubstantiveSpecialistUnavailable(RuntimeError):
    """A substantive turn produced no accepted specialist or contractor.

    Raised by ``_require_substantive_specialist`` so the existing failure-receipt
    persistence path records the exact cause. ``run_preflight`` catches it
    separately to fail open: it persists the receipt (so the dashboard and logs
    stay diagnosable) and returns an honest zero-specialist ``PreflightResult``
    instead of blocking the parent model. See the ADR-0122 update.

    Carries the routing dict's inference fields so the fail-open result can
    report the real cause (inference attempted vs not, plan-policy veto vs
    provider failure) instead of hard-coding ``inference_attempted=True``.
    """

    def __init__(
        self,
        message: str,
        *,
        routing: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        r = routing or {}
        self.inference_attempted = bool(r.get("inference_attempted", True))
        self.inference_mode = str(r.get("inference_mode") or "degraded")
        self.routing_error = str(r.get("error") or "")
        self.inference_failures: tuple[str, ...] = tuple(r.get("inference_failures") or ())
        self.routing = dict(r)


class _PreflightFailureDiagnostics:
    """Track only allowlisted state needed if this attempt becomes terminal."""

    __slots__ = (
        "eligibility_reason_codes",
        "hiring_reason_codes",
        "provider_attempts",
        "reason_code",
        "staffing_reason_codes",
        "stage",
    )

    def __init__(self) -> None:
        self.stage = "lifecycle"
        self.reason_code = default_preflight_failure_reason(self.stage)
        self.provider_attempts: list[dict[str, Any]] = []
        self.staffing_reason_codes: list[str] = []
        self.hiring_reason_codes: list[str] = []
        self.eligibility_reason_codes: list[str] = []

    def enter(self, stage: str) -> None:
        self.stage = stage
        self.reason_code = default_preflight_failure_reason(stage)

    def observe_routing(self, routing: Mapping[str, Any]) -> None:
        attempts = project_preflight_provider_attempts(routing.get("provider_attempts"))
        self.provider_attempts = [] if attempts is None else attempts
        self.staffing_reason_codes = preflight_staffing_reason_codes(routing)
        self.hiring_reason_codes = preflight_hiring_reason_codes(routing)
        self.eligibility_reason_codes = preflight_eligibility_reason_codes(routing)
        self.reason_code = preflight_routing_failure_reason(routing)

    def mark_substantive_specialist_unavailable(self, routing: Mapping[str, Any]) -> None:
        reason = preflight_routing_failure_reason(routing)
        self.reason_code = (
            reason
            if reason
            in {
                "workforce_provider_unavailable",
                "workforce_inference_failed",
                "child_routing_unavailable",
            }
            else "substantive_specialist_unavailable"
        )

    def receipt(self, error: BaseException) -> dict[str, Any]:
        return {
            "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
            "stage": self.stage,
            "reason_code": self.reason_code,
            "invariant_code": preflight_invariant_code(error),
            "exception_category": preflight_exception_category(error),
            "provider_attempts": self.provider_attempts,
            "staffing_reason_codes": self.staffing_reason_codes,
            "hiring_reason_codes": self.hiring_reason_codes,
            "eligibility_reason_codes": self.eligibility_reason_codes,
        }


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


def _child_route_coordination_timeout(config: AgencyConfig) -> float:
    """Bound one top-level route plus every possible parallel unit-routing wave."""

    inference_waves = 1 + ceil(MAX_SUGGESTED_WORK_UNITS / MAX_UNIT_SELECTION_WORKERS)
    return _child_route_timeout(config) * inference_waves + _CHILD_ROUTE_LEASE_MARGIN_SECONDS


def _start_child_route_heartbeat(
    store: Store,
    *,
    cache_key: str,
    owner_token: str,
    lease_seconds: float,
) -> tuple[Event, Thread]:
    """Keep a live owner lease current while bounded unit routing is in progress."""

    stopped = Event()
    interval = max(0.25, min(10.0, lease_seconds / 3.0))

    def renew() -> None:
        while not stopped.wait(interval):
            if not store.renew_child_routing(
                cache_key=cache_key,
                owner_token=owner_token,
                lease_seconds=lease_seconds,
            ):
                return

    thread = Thread(target=renew, name="agency-child-route-lease", daemon=True)
    thread.start()
    return stopped, thread


def _stop_child_route_heartbeat(cache_owner: Mapping[str, Any]) -> None:
    stopped = cache_owner.get("heartbeat_stop")
    thread = cache_owner.get("heartbeat_thread")
    if isinstance(stopped, Event):
        stopped.set()
    if isinstance(thread, Thread) and thread is not current_thread():
        thread.join(timeout=1.0)


def _turn_state_for_preflight(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    host: str,
) -> tuple[TurnState, dict[str, Any], dict[str, Any]]:
    """Read durable prior-turn state or fail closed when it is unavailable."""

    getter = getattr(store, "get_turn_state_context", None)
    if not callable(getter):
        return TurnState(state_known=False, state_status="missing"), {}, {}
    try:
        value = getter(session_id, before_trace_id=trace_id, host=host)
    except Exception:
        return TurnState(state_known=False, state_status="missing"), {}, {}
    if not isinstance(value, Mapping):
        return TurnState(state_known=False, state_status="corrupt"), {}, {}
    routing_context = project_turn_routing_context(value.get("turn_routing_context"))
    context_guard = project_turn_routing_context_guard(value.get("turn_routing_context_guard"))
    if (
        not routing_context
        or not context_guard
        or routing_context.get("source_trace_id") != context_guard.get("source_trace_id")
        or turn_routing_context_revision(routing_context)
        != context_guard.get("source_context_revision")
    ):
        routing_context = {}
        context_guard = {}
    return TurnState.from_mapping(value), routing_context, context_guard


def _catalog_with_policy(store: Store, disabled_agents: frozenset[str]) -> list[dict]:
    """Read a policy-filtered catalog without breaking legacy Store facades."""

    return catalog_for_routing(
        store,
        disabled_agents,
        signature_reader=signature,
    )


def _specialist_hydration_routing(routing: dict[str, Any]) -> dict[str, Any]:
    """Choose prompt bodies that share the caller's host context.

    Every specialist the recruiter selected is hydrated. How many may be selected
    belongs to the staffing budget and how large they may be belongs to the host
    context limit; neither ceiling is re-imposed here. Resident managers use their
    own compact parent kernel and are never hydrated as ordinary specialists.
    """

    selected = [str(slug).strip() for slug in routing.get("selected_ids", []) if str(slug).strip()]
    selected = [slug for slug in selected if not is_resident_manager_slug(slug)]
    if selected == routing.get("selected_ids"):
        return routing
    return {**routing, "selected_ids": selected}


def _pending_hiring_specialist_view(
    store: Store,
    catalog: list[dict[str, Any]],
    routing: Mapping[str, Any],
) -> tuple[Store, list[dict[str, Any]]]:
    """Expose validated pending specialists before their ready-CAS commit."""

    commits = routing.get("_pending_hiring_commits")
    if not isinstance(commits, list) or not commits:
        return store, catalog
    from agency_runtime.core.workforce.hiring import PendingHiringCommit

    if any(not isinstance(item, PendingHiringCommit) for item in commits):
        raise RuntimeError("pending hiring specialist view is malformed")
    agents = {
        str(item.agent.get("slug") or "").strip(): dict(item.agent)
        for item in commits
        if str(item.agent.get("slug") or "").strip() and item.projected_worker is not None
    }
    if not agents:
        return store, catalog
    active_catalog = [item for item in catalog if str(item.get("slug") or "").strip() not in agents]
    active_catalog.extend(agents.values())
    view = copy.copy(store)
    stored_getter = store.get_specialist_prompt
    stored_versioned_getter = store.get_versioned_specialist_prompt

    def get_specialist_prompt(slug: str, **kwargs: Any) -> dict[str, Any] | None:
        pending = agents.get(str(slug or "").strip())
        if pending is None:
            return stored_getter(slug, **kwargs)
        prompt = dict(pending)
        prompt["prompt_hash"] = str(prompt.get("hash") or "")
        prompt["prompt_truncated"] = False
        return prompt

    def get_versioned_specialist_prompt(
        slug: str,
        version: str,
        content_hash: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        pending = agents.get(str(slug or "").strip())
        if pending is None:
            return stored_versioned_getter(slug, version, content_hash, **kwargs)
        if (
            str(pending.get("version") or "") != str(version or "").strip()
            or str(pending.get("hash") or "") != str(content_hash or "").strip()
        ):
            return None
        prompt_body = str(pending.get("prompt_body") or "")
        maximum = max(1, min(int(kwargs.get("max_chars", 65_536)), 262_144))
        return {
            "slug": str(pending.get("slug") or ""),
            "version": str(pending.get("version") or ""),
            "hash": str(pending.get("hash") or ""),
            "prompt_body": prompt_body[:maximum],
            "prompt_truncated": len(prompt_body) > maximum,
        }

    view.get_specialist_prompt = get_specialist_prompt
    view.get_versioned_specialist_prompt = get_versioned_specialist_prompt
    return view, active_catalog


def _selection_refs_for_recipe(
    store: Store,
    catalog: list[dict[str, Any]],
    routing: dict[str, Any],
    specialist_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Bind every nonresident selection/assignment to its active revision."""

    ordered_slugs: list[str] = []
    for raw_slug in [
        *routing.get("selected_ids", []),
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
        if not is_valid_version_identity(version) or not is_valid_version_identity(content_hash):
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
    reconcile_packaged_contractors: Any,
) -> Any:
    """Refresh the atomic roster snapshot after any required bootstrap mutation."""

    from agency_runtime.core.codex_activation_verification import (
        is_restricted_codex_activation_canary_environment,
    )

    if is_restricted_codex_activation_canary_environment(os.environ):
        return routing_snapshot

    if not routing_snapshot.catalog:
        seed_starter_roster(store)
        return capture_routing_snapshot(store, config)
    contractors_installed, _contractors_existing = reconcile_packaged_contractors(store)
    if ensure_no_match_fallback_roster(store) or contractors_installed:
        return capture_routing_snapshot(store, config)
    return routing_snapshot


def _route_arguments(
    *,
    store: Store,
    config: AgencyConfig,
    trace_id: str,
    classification: TurnClassification,
    host: str,
    platform: str,
    available_tools: tuple[str, ...],
    capability_receipt: HostCapabilityReceipt,
    workforce_snapshot: Any,
    route_request: Any = None,
) -> dict[str, Any]:
    """Build the route() kwargs shared by every fresh-turn route site.

    PERF-01: when a pre-built ``route_request`` is available it is forwarded so
    ``route()`` skips the expensive catalog/policy/fingerprint rebuild. The
    caller is responsible for popping ``request`` before swapping in a
    different config (see the deterministic-config path below).
    """

    arguments: dict[str, Any] = {
        "config": config,
        "store": store,
        "preflight_atomic": True,
        "trace_id": trace_id,
        "turn_classification": classification,
        "host": host,
        "platform": platform,
        "available_tools": available_tools,
        "capability_receipt": capability_receipt,
        "workforce_snapshot": workforce_snapshot,
    }
    if route_request is not None:
        arguments["request"] = route_request
    return arguments


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
    workforce_snapshot: Any = None,
    parent_session_id: str = "",
    parent_trace_id: str = "",
    route_request: Any = None,
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
    route_arguments = _route_arguments(
        store=store,
        config=config,
        trace_id=trace_id,
        classification=classification,
        host=host,
        platform=platform,
        available_tools=available_tools,
        capability_receipt=capability_receipt,
        workforce_snapshot=workforce_snapshot,
        route_request=route_request,
    )
    if not parent_trace_id:
        return (
            pipeline.route(session_id, user_message, catalog, **route_arguments),
            None,
            classification,
        )

    from agency_runtime.core.selector.judge import inference_is_configured

    if not inference_is_configured(config):
        routing = pipeline.route(session_id, user_message, catalog, **route_arguments)
        routing.update(
            selected_ids=[],
            semantic_ids=[],
            status="inference_unavailable",
            source="inference_failure",
            error="no inference provider is configured for child routing",
            inference_configured=False,
            inference_required=True,
            inference_mode="unavailable",
            child_routing_source="inference_unavailable",
        )
        return routing, None, classification

    workforce_contract_fingerprint = str(
        getattr(workforce_snapshot, "contract_fingerprint", "") or ""
    )
    workforce_recruiter_fingerprint = str(
        getattr(workforce_snapshot, "recruiter_fingerprint", "") or ""
    )
    cache_material = "\0".join(
        (
            "agency-child-route-v2",
            str(_CHILD_ROUTE_BUNDLE_VERSION),
            str(PREFLIGHT_REPLAY_RECIPE_VERSION),
            WORKFORCE_CACHE_IDENTITY_VERSION,
            str(PLAN_SCHEMA_VERSION),
            str(RECRUITMENT_SCHEMA_VERSION),
            parent_session_id,
            parent_trace_id,
            sha256(user_message.encode("utf-8", errors="surrogatepass")).hexdigest(),
            routing_fingerprint,
            policy_fingerprint,
            str(roster_generation),
            workforce_contract_fingerprint,
            workforce_recruiter_fingerprint,
            classification.turn_kind,
            str(classification.classifier_version),
            str(classification.state_revision),
            host,
            platform,
            str(getattr(capability_receipt, "surface", "") or ""),
            str(getattr(capability_receipt, "inference_surface", "") or ""),
            str(getattr(capability_receipt, "status", "") or ""),
            "\x1f".join(available_tools),
            "\x1f".join(tuple(getattr(capability_receipt, "unknown_tools", ()) or ())),
        )
    )
    child_cache_key = sha256(cache_material.encode("utf-8")).hexdigest()
    route_timeout = _child_route_timeout(config)
    coordination_timeout = _child_route_coordination_timeout(config)
    reservation = store.reserve_child_routing(
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        cache_key=child_cache_key,
        budget=config.delegation.child_inference_budget,
        concurrency=config.delegation.child_inference_concurrency,
        lease_seconds=route_timeout + _CHILD_ROUTE_LEASE_MARGIN_SECONDS,
    )
    if reservation["status"] == "coalescing":
        deadline = time.monotonic() + coordination_timeout
        while time.monotonic() < deadline:
            cached = store.read_child_routing_cache(child_cache_key)
            if cached is not None:
                reservation = {"status": "cached", "decision": cached}
                break
            time.sleep(0.05)
    if reservation["status"] == "cached":
        decision = dict(reservation["decision"])
        bundled_routing = decision.get("routing")
        if isinstance(bundled_routing, Mapping):
            cached = dict(bundled_routing)
            cached["_cached_unit_assignment_agents"] = list(
                decision.get("unit_assignment_agents", [])
            )
        else:
            cached = decision
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
        except BaseException:
            store.abort_child_routing(cache_key=child_cache_key, owner_token=owner_token)
            raise
        routing["_child_cache_owner"] = {
            "cache_key": child_cache_key,
            "owner_token": owner_token,
        }
        try:
            heartbeat_stop, heartbeat_thread = _start_child_route_heartbeat(
                store,
                cache_key=child_cache_key,
                owner_token=owner_token,
                lease_seconds=route_timeout + _CHILD_ROUTE_LEASE_MARGIN_SECONDS,
            )
        except BaseException:
            store.abort_child_routing(cache_key=child_cache_key, owner_token=owner_token)
            raise
        routing["_child_cache_owner"].update(
            heartbeat_stop=heartbeat_stop,
            heartbeat_thread=heartbeat_thread,
        )
        routing["child_routing_source"] = "parent_budgeted_inference"
        return routing, None, classification

    inference_unavailable_config = replace(
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
    route_arguments["config"] = inference_unavailable_config
    # PERF-01 carve-out: the pre-built request was constructed against the
    # original config; the no-inference config changes the policy
    # fingerprint baked into the request, so it cannot be reused here.
    route_arguments.pop("request", None)
    routing = pipeline.route(session_id, user_message, catalog, **route_arguments)
    routing.update(
        selected_ids=[],
        semantic_ids=[],
        confidence=0.0,
        status="child_budget_abstained",
        source="child_budget_policy",
        inference_mode="unavailable",
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
        return []
    if "_cached_unit_assignment_agents" in routing:
        return list(routing["_cached_unit_assignment_agents"])
    if continuation_snapshot is not None:
        return list(continuation_snapshot["recipe"].get("unit_assignment_agents", []))
    workforce_assignments = routing.get("unit_assignment_agents")
    if isinstance(workforce_assignments, (list, tuple)):
        projected = project_unit_assignment_agents(workforce_assignments, strict=True)
        if projected is None:
            raise RuntimeError("verified workforce assignments are malformed")
        return projected
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
    return assignment_agents


def _publish_child_routing_bundle(
    store: Store,
    routing: dict[str, Any],
    *,
    trace_id: str,
    unit_assignment_agents: list[dict[str, Any]],
    ttl_seconds: float,
) -> None:
    """Publish one complete content-free route and release its singleflight lease."""

    cache_owner = routing.get("_child_cache_owner")
    if not isinstance(cache_owner, Mapping):
        return
    try:
        completed = store.complete_child_routing(
            cache_key=str(cache_owner["cache_key"]),
            owner_token=str(cache_owner["owner_token"]),
            decision={
                "version": _CHILD_ROUTE_BUNDLE_VERSION,
                "routing": _content_free_routing_recipe(routing, trace_id=trace_id),
                "unit_assignment_agents": unit_assignment_agents,
            },
            ttl_seconds=ttl_seconds,
        )
    finally:
        _stop_child_route_heartbeat(cache_owner)
    if not completed:
        raise RuntimeError("child routing ownership expired before assignment publish")


def _abort_child_routing_bundle(store: Store, routing: Mapping[str, Any]) -> None:
    """Release a pending bundle lease after any preparation failure."""

    cache_owner = routing.get("_child_cache_owner")
    if not isinstance(cache_owner, Mapping):
        return
    try:
        store.abort_child_routing(
            cache_key=str(cache_owner["cache_key"]),
            owner_token=str(cache_owner["owner_token"]),
        )
    finally:
        _stop_child_route_heartbeat(cache_owner)


def _recipe_revision_refs(
    store: Store,
    catalog: list[dict[str, Any]],
    routing: dict[str, Any],
    loaded: Any,
    continuation_snapshot: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    specialist_refs = [reference.as_dict() for reference in loaded.references]
    if continuation_snapshot is None:
        return specialist_refs, _selection_refs_for_recipe(
            store,
            catalog,
            routing,
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


def _persist_preflight_failure(
    store: Store,
    *,
    diagnostics: _PreflightFailureDiagnostics,
    error: BaseException,
    session_id: str,
    trace_id: str,
    attempt_token: str,
    attempt_owner: bool,
    reservation_token: str,
) -> None:
    """Persist the failure receipt for a terminal preflight attempt.

    Cleanup is an exact-token compare-and-set. A concurrent successful caller may
    already own a ready attempt, and must never be closed by this caller's
    failure path. A cleanup error re-raises the original error so the real cause
    is never masked.
    """

    try:
        if attempt_token and attempt_owner:
            store.fail_preflight_attempt(
                session_id=session_id,
                trace_id=trace_id,
                attempt_token=attempt_token,
                status="preflight_failed",
                failure_receipt=diagnostics.receipt(error),
            )
        elif not attempt_token and reservation_token:
            store.abandon_preflight_reservation(
                session_id=session_id,
                trace_id=trace_id,
                reservation_token=reservation_token,
                status="preflight_failed",
                failure_receipt=diagnostics.receipt(error),
            )
    except Exception as cleanup_error:
        raise error from cleanup_error


def _fail_open_preflight_result(
    *,
    session_id: str,
    trace_id: str,
    resident_binding: Any,
    resident_context: str,
    roster_size: int,
    host: str,
    classification: TurnClassification,
    source_routing: Mapping[str, Any] | None = None,
    inference_attempted: bool = True,
    inference_mode: str = "degraded",
    routing_error: str = "",
    inference_failures: tuple[str, ...] = (),
) -> PreflightResult:
    """Build the honest zero-specialist result returned on a fail-open turn.

    ADR-0122 update: when a substantive turn cannot produce an accepted
    specialist, the turn proceeds as a generalist answer with the resident
    manager kernel bound and a ``Recruited via: none`` header. The routing dict
    carries the real ``inference_attempted``/``inference_mode`` from the
    SubstantiveSpecialistUnavailable exception so the header and dashboard stay
    truthful about why no specialist was selected.
    """

    resident_managers = RESIDENT_MANAGER_SLUGS
    error_detail = ", ".join(s for s in (routing_error, *inference_failures) if s.strip())
    routing = {
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "status": "no_specialist_fail_open",
        "source": "workforce_inference",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": inference_attempted,
        "inference_mode": inference_mode,
        "stage_latencies": {},
        "total_inference_calls": 0,
        "provider": "deterministic",
        "trace_id": trace_id,
        "error": error_detail or "no accepted specialist route; the host answers as a generalist",
        "turn_kind": classification.turn_kind,
        "selection_required": classification.selection_required,
        "reroute_required": classification.reroute_required,
        "execution_decision_required": classification.execution_decision_required,
        "continuation_of": classification.continuation_of,
        "classifier_version": classification.classifier_version,
        "state_revision": classification.state_revision,
    }
    prior_routing = source_routing if isinstance(source_routing, Mapping) else {}
    if prior_routing.get("turn_context_applied") is True:
        routing.update(
            turn_context_applied=True,
            turn_context_source_trace_id=str(
                prior_routing.get("turn_context_source_trace_id") or ""
            ),
            turn_context_revision=str(prior_routing.get("turn_context_revision") or ""),
        )
    return PreflightResult(
        session_id=session_id,
        trace_id=trace_id,
        routing=routing,
        context=resident_context,
        loaded_specialists=resident_managers,
        selected_specialists=(),
        trivial=False,
        roster_size=roster_size,
        turn_kind=classification.turn_kind,
        selection_required=classification.selection_required,
        reroute_required=classification.reroute_required,
        execution_decision_required=classification.execution_decision_required,
        continuation_of=classification.continuation_of,
        classifier_version=classification.classifier_version,
        state_revision=classification.state_revision,
        resident_managers=resident_managers,
        resident_manager_kernel_version=(
            RESIDENT_MANAGER_KERNEL_REFERENCE.version if resident_managers else 0
        ),
        resident_manager_kernel_hash=(
            RESIDENT_MANAGER_KERNEL_REFERENCE.content_hash if resident_managers else ""
        ),
        resident_manager_binding=(
            resident_binding.as_dict() if resident_binding is not None else None
        ),
        resident_manager_delivery_mode=(getattr(resident_binding, "delivery_mode", "") or ""),
        resident_manager_host_mode=(getattr(resident_binding, "host_mode", "") or ""),
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
    specialist_refs: list[dict[str, Any]],
    codex_native_plan_scopes: list[dict[str, Any]],
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
        "specialist_refs": specialist_refs,
        "codex_native_plan_scopes": codex_native_plan_scopes,
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


def _require_ready_commit(ready: object) -> None:
    """Reject stale contextual evidence and every non-ready CAS outcome."""

    if isinstance(ready, dict) and ready.get("outcome") == "turn_context_guard_conflict":
        raise RuntimeError("turn routing context changed before ready commit")
    if not isinstance(ready, dict) or ready.get("outcome") not in {
        "committed",
        "replay",
    }:
        raise RuntimeError("preflight attempt became terminal before it reached ready")


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
    workforce_snapshot: Any,
    delivery_mode: str,
    context_limit: int,
    resident_binding: Any,
    resident_context: str,
    pipeline: Any,
    turn_context_guard: Mapping[str, Any] | None = None,
    parent_session_id: str = "",
    parent_trace_id: str = "",
    route_request: Any = None,
    diagnostics: _PreflightFailureDiagnostics | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    TurnClassification,
    list[dict[str, Any]],
]:
    """Build one replay-safe recipe without committing its lifecycle state."""

    from agency_runtime.core.specialist_context import (
        hydrate_selected_specialist_context,
    )

    if diagnostics is not None:
        diagnostics.enter("routing")
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
        workforce_snapshot=workforce_snapshot,
        pipeline=pipeline,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        route_request=route_request,
    )
    routing = dict(routing)
    routing["trace_id"] = trace_id
    if diagnostics is not None:
        diagnostics.observe_routing(routing)
    _require_substantive_specialist(routing, classification, diagnostics)
    hydration_store, hydration_catalog = _pending_hiring_specialist_view(
        store,
        catalog,
        routing,
    )
    cache_owner = routing.get("_child_cache_owner")
    with ExitStack() as child_route_guard:
        if isinstance(cache_owner, Mapping):
            child_route_guard.callback(_abort_child_routing_bundle, store, routing)
        if diagnostics is not None:
            diagnostics.enter("assignment")
        unit_assignment_agents = _assignment_recipe(
            hydration_catalog,
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
        _require_substantive_specialist(routing, classification, diagnostics)
        if diagnostics is not None:
            diagnostics.enter("context_hydration")
        routing_context = pipeline.build_routing_context(routing, config)
        manager_routing_context = _combine_context(
            resident_context,
            routing_context,
            maximum_chars=context_limit,
        )
        specialist_budget = max(0, context_limit - len(manager_routing_context) - 2)
        hydration_routing = _specialist_hydration_routing(routing)
        loaded = hydrate_selected_specialist_context(
            hydration_store,
            hydration_catalog,
            hydration_routing,
            record_evidence=False,
            maximum_chars=specialist_budget,
            session_id=session_id,
            trace_id=trace_id,
            disabled_agents=frozenset(config.agents.disabled),
        )
        if diagnostics is not None:
            diagnostics.enter("context_delivery")
        routing_recipe = _content_free_routing_recipe(routing, trace_id=trace_id)
        specialist_refs, selection_refs = _recipe_revision_refs(
            hydration_store,
            hydration_catalog,
            routing,
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
            "trivial": not classification.selection_required,
            "turn_classification": classification.as_dict(),
            "resident_manager_binding": resident_binding.as_dict(),
            "roster_size": len(catalog),
            "roster_generation": roster_generation,
        }
        if continuation_snapshot is not None:
            recipe["continuation_guard"] = continuation_snapshot["guard"]
        if turn_context_guard:
            recipe["turn_context_guard"] = dict(turn_context_guard)
        # Replayed for its validation side effects: it raises if the recipe cannot
        # rebuild the exact result being committed. The rebuilt value itself is
        # unused now that no delivery mode derives private plan scopes from it.
        _result_from_recipe(
            hydration_store,
            recipe,
            session_id=session_id,
            trace_id=trace_id,
            user_message=user_message,
            config=config,
            pipeline=pipeline,
        )
        codex_native_plan_scopes: list[dict[str, Any]] = []
        if isinstance(cache_owner, Mapping):
            _publish_child_routing_bundle(
                store,
                routing,
                trace_id=trace_id,
                unit_assignment_agents=unit_assignment_agents,
                ttl_seconds=config.delegation.child_cache_ttl_seconds,
            )
        child_route_guard.pop_all()
        return (
            recipe,
            routing_recipe,
            specialist_refs,
            classification,
            codex_native_plan_scopes,
        )


def _require_substantive_specialist(
    routing: Mapping[str, Any],
    classification: TurnClassification,
    diagnostics: _PreflightFailureDiagnostics | None = None,
) -> None:
    """Raise when a substantive turn produced no accepted specialist.

    Planning, recruitment, gap hiring, and restaffing have all completed before
    this boundary. A substantive turn that still has no non-resident identity
    raises ``SubstantiveSpecialistUnavailable`` so the existing receipt-
    persistence path records the exact cause. ``run_preflight`` then fails open:
    it persists the receipt and returns an honest zero-specialist result so the
    host can answer as a generalist with a ``Recruited via: none`` header instead
    of blocking the operator out of the host (ADR-0122 update).
    """

    if not classification.selection_required:
        return
    selected = tuple(
        dict.fromkeys(
            slug
            for item in routing.get("selected_ids", ())
            if (slug := str(item or "").strip().casefold()) and not is_resident_manager_slug(slug)
        )
    )
    if selected:
        return
    if diagnostics is not None:
        diagnostics.mark_substantive_specialist_unavailable(routing)
    status = " ".join(str(routing.get("status") or "unavailable").split())[:64]
    source = " ".join(str(routing.get("source") or "unavailable").split())[:64]
    inference_mode = " ".join(str(routing.get("inference_mode") or "").split())[:32]
    detail = ", ".join(
        str(item)
        for item in (routing.get("error"), *routing.get("inference_failures", ()))
        if str(item or "").strip()
    )[:200]
    raise SubstantiveSpecialistUnavailable(
        f"no accepted specialist route; status={status}; source={source}; "
        f"inference_mode={inference_mode}; reason={detail or 'none'}",
        routing=routing,
    )


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
    list[dict[str, Any]],
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
    native_worker_id: str = "",
    native_run_id: str = "",
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
        reconcile_packaged_contractors,
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
    diagnostics = _PreflightFailureDiagnostics()
    try:
        diagnostics.enter("routing_snapshot")
        routing_snapshot = capture_routing_snapshot(store, config)
        cfg = routing_snapshot.config
        delivery_mode, context_limit = preflight_delivery_policy(
            normalized_host,
            native_child=bool(normalized_parent_trace),
        )
        (
            turn_state,
            prior_turn_routing_context,
            prior_turn_context_guard,
        ) = _turn_state_for_preflight(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            host=normalized_host,
        )
        classification = classify_turn_intent(user_message, turn_state)
        if current_origin is None:
            classification = force_fresh_turn_reroute(
                classification,
                "adapter_origin_untrusted",
                untrusted_origin=True,
            )
        turn_routing_context = prior_turn_routing_context
        turn_context_guard = prior_turn_context_guard
        if classification.continuation_of and (
            not turn_routing_context
            or turn_routing_context.get("source_trace_id") != classification.continuation_of
        ):
            turn_routing_context = {}
            turn_context_guard = {}
        if not (
            classification.selection_required
            and classification.reroute_required
            and (
                not classification.execution_decision_required
                or classification.turn_kind in {"continuation", "revision"}
            )
        ):
            turn_routing_context = {}
            turn_context_guard = {}
        request_kind = classification.legacy_request_kind
        request_fingerprint = sha256(
            str(user_message).encode("utf-8", errors="surrogatepass")
        ).hexdigest()
        # Redact here, not only at the caller. `persisted_user_message` was the
        # redaction seam and the LiteLLM callback was its only supplier, so every
        # native host-hook turn wrote the raw message. Redacting an already
        # redacted excerpt is idempotent, so the LiteLLM path is unaffected.
        persisted_source = (
            user_message if persisted_user_message is None else persisted_user_message
        )
        persisted_message = (
            redact_content(persisted_source) if cfg.observability.capture_content else ""
        )
        lease_seconds = hook_timeout_seconds(cfg)
        diagnostics.enter("lifecycle")
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
            diagnostics.enter("ready_read")
            reused_result = _read_ready_result(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
            )
            return reused_result
        if outcome == "reused_in_progress":
            diagnostics.enter("ready_read")
            reused_result = _await_ready_result(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
                timeout_seconds=lease_seconds,
            )
            return reused_result
        attempt_owner = outcome in {"started", "recovered_started"}
        diagnostics.enter("resident_binding")
        resident_binding, resident_context = _resident_binding_for_preflight(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            host=normalized_host,
        )
        diagnostics.enter("routing_snapshot")
        routing_snapshot = _ensure_preflight_catalog(
            store,
            cfg,
            routing_snapshot,
            seed_starter_roster=seed_starter_roster,
            ensure_no_match_fallback_roster=ensure_no_match_fallback_roster,
            reconcile_packaged_contractors=reconcile_packaged_contractors,
        )
        routing_snapshot, workforce_snapshot = bind_workforce_snapshot(store, routing_snapshot)
        catalog = routing_snapshot.catalog

        # PERF-01: build the routing request ONCE per fresh turn and reuse its
        # context fingerprint AND the request itself downstream in route().
        # Previously routing_context_fingerprint built the full _RouteRequest
        # (catalog eligibility walk, policy load, canonicalize+sha256) just to
        # discard everything but the fingerprint string, then route() rebuilt
        # it identically. The request is valid for reuse because catalog, cfg,
        # host/platform/capabilities, and capability_receipt are the same
        # objects threaded by alias into the eventual route() call.
        diagnostics.enter("route_request")
        route_request = pipeline.build_route_request(
            normalized_session,
            user_message,
            catalog,
            cfg,
            trace_id=turn_trace_id,
            host=normalized_host,
            platform=runtime_platform,
            available_tools=runtime_capabilities.capabilities,
            capability_receipt=runtime_capabilities,
            workforce_snapshot=workforce_snapshot,
            turn_routing_context=turn_routing_context,
        )
        routing_fingerprint = route_request.context_fingerprint
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
            "route_request": route_request,
            "policy_fingerprint": policy_fingerprint,
            "roster_generation": routing_snapshot.roster_generation,
            "workforce_snapshot": workforce_snapshot,
            "delivery_mode": delivery_mode,
            "context_limit": context_limit,
            "resident_binding": resident_binding,
            "resident_context": resident_context,
            "pipeline": pipeline,
            "parent_session_id": normalized_parent_session,
            "parent_trace_id": normalized_parent_trace,
            "diagnostics": diagnostics,
            "turn_context_guard": turn_context_guard,
        }
        (
            recipe,
            routing_recipe,
            specialist_refs,
            classification,
            codex_native_plan_scopes,
        ) = _prepare_with_bounded_continuation_reroute(
            store,
            classification=classification,
            prepare_arguments=prepare_arguments,
        )
        diagnostics.enter("ready_commit")
        ready = _mark_ready_with_binding_replan(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            attempt_token=attempt_token,
            recipe=recipe,
            host=normalized_host,
            routing_recipe=routing_recipe,
            specialist_refs=specialist_refs,
            codex_native_plan_scopes=codex_native_plan_scopes,
            user_message=user_message,
            config=cfg,
            pipeline=pipeline,
        )
        if isinstance(ready, dict) and ready.get("outcome") == "continuation_guard_conflict":
            classification = force_fresh_turn_reroute(
                classification,
                "continuation_guard_changed_before_commit",
            )
            (
                recipe,
                routing_recipe,
                specialist_refs,
                classification,
                codex_native_plan_scopes,
            ) = _prepare_preflight_evidence(
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
                workforce_snapshot=workforce_snapshot,
                delivery_mode=delivery_mode,
                context_limit=context_limit,
                resident_binding=resident_binding,
                resident_context=resident_context,
                pipeline=pipeline,
                parent_session_id=normalized_parent_session,
                parent_trace_id=normalized_parent_trace,
                diagnostics=diagnostics,
            )
            diagnostics.enter("ready_commit")
            ready = _mark_ready_with_binding_replan(
                store,
                session_id=normalized_session,
                trace_id=turn_trace_id,
                attempt_token=attempt_token,
                recipe=recipe,
                host=normalized_host,
                routing_recipe=routing_recipe,
                specialist_refs=specialist_refs,
                codex_native_plan_scopes=codex_native_plan_scopes,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
            )
        _require_ready_commit(ready)
        diagnostics.enter("ready_read")
        ready_result = _read_ready_result(
            store,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            attempt_token=attempt_token,
            user_message=user_message,
            config=cfg,
            pipeline=pipeline,
        )
        return ready_result
    except Exception as error:
        # Cleanup is an exact-token compare-and-set. A concurrent successful
        # caller may already own a ready attempt, and must never be closed by
        # this caller's failure path.
        _persist_preflight_failure(
            store,
            diagnostics=diagnostics,
            error=error,
            session_id=normalized_session,
            trace_id=turn_trace_id,
            attempt_token=attempt_token,
            attempt_owner=attempt_owner,
            reservation_token=normalized_reservation_token,
        )
        if isinstance(error, SubstantiveSpecialistUnavailable):
            # ADR-0122 update: a substantive turn that produced no accepted
            # specialist fails open. The receipt above already persisted the
            # exact cause for the dashboard and logs; return an honest
            # zero-specialist PreflightResult so the host answers as a generalist
            # with a "Recruited via: none" header instead of blocking the
            # operator out of the host. The resident-manager kernel still binds
            # evidence, scope, and the truthful header.
            return _fail_open_preflight_result(
                session_id=normalized_session,
                trace_id=turn_trace_id,
                resident_binding=resident_binding,
                resident_context=resident_context,
                roster_size=len(catalog),
                host=normalized_host,
                classification=classification,
                source_routing=error.routing,
                inference_attempted=error.inference_attempted,
                inference_mode=error.inference_mode,
                routing_error=error.routing_error,
                inference_failures=error.inference_failures,
            )
        raise


__all__ = ["MAX_PREFLIGHT_CONTEXT_CHARS", "PreflightResult", "run_preflight"]
