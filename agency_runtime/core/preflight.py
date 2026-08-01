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

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.codex_native_plan_scope import build_codex_native_plan_scope
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import (
    HostCapabilityReceipt,
    current_host_capability_receipt,
)
from agency_runtime.core.preflight_failure import (
    PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
    PreflightInvariantError,
    default_preflight_failure_reason,
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
    _suggestion_recipe,
    _verified_work_units,
    preflight_delivery_policy,
)
from agency_runtime.core.resident_managers import is_resident_manager_slug
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
from agency_runtime.core.unit_assignment import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_UNIT_SELECTION_WORKERS,
    assignment_agents_from_catalog,
    hydrate_unit_agent_plan,
    native_child_activation_contract,
    project_unit_agent_plan,
    project_unit_assignment_agents,
    work_unit_goal_hash,
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
_DIRECT_NATIVE_CHILD_HOSTS = frozenset({"hermes", "openclaw"})


class _PreflightFailureDiagnostics:
    """Track only allowlisted state needed if this attempt becomes terminal."""

    __slots__ = (
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

    def enter(self, stage: str) -> None:
        self.stage = stage
        self.reason_code = default_preflight_failure_reason(stage)

    def observe_routing(self, routing: Mapping[str, Any]) -> None:
        attempts = project_preflight_provider_attempts(routing.get("provider_attempts"))
        self.provider_attempts = [] if attempts is None else attempts
        self.staffing_reason_codes = preflight_staffing_reason_codes(routing)
        self.hiring_reason_codes = preflight_hiring_reason_codes(routing)
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


def _planned_parent_unit_routing(
    store: Store,
    *,
    parent_session_id: str,
    parent_trace_id: str,
    user_message: str,
    host: str,
    catalog: list[dict[str, Any]],
    routing_fingerprint: str,
    capability_receipt: HostCapabilityReceipt,
) -> dict[str, Any] | None:
    """Reuse one exact parent unit locally before spending any child inference."""

    snapshot_reader = getattr(store, "get_completion_evidence_snapshot", None)
    if not callable(snapshot_reader):
        return None
    try:
        snapshot = snapshot_reader(parent_session_id, parent_trace_id)
    except Exception:
        return None
    run = snapshot.get("run") if isinstance(snapshot, Mapping) else None
    if (
        not isinstance(snapshot, Mapping)
        or not isinstance(run, Mapping)
        or snapshot.get("session_id") != parent_session_id
        or snapshot.get("trace_id") != parent_trace_id
        or snapshot.get("status") not in {"active", "evidence_only"}
        or snapshot.get("delivery_mode") != "isolated"
        or str(run.get("host") or "").strip().casefold() != str(host or "").strip().casefold()
    ):
        return None
    raw_plan = snapshot.get("unit_agent_plan")
    raw_references = snapshot.get("selected_specialists")
    if not isinstance(raw_plan, list) or not isinstance(raw_references, list):
        return None
    goal_hash = work_unit_goal_hash(user_message)
    matches = [
        row
        for row in raw_plan
        if isinstance(row, Mapping) and str(row.get("goal_hash") or "") == goal_hash
    ]
    if len(matches) != 1:
        return None
    source_plan = dict(matches[0])
    primary = str(source_plan.get("recommended_agent") or "").strip().casefold()
    raw_team = source_plan.get("recommended_agents")
    team = (
        [str(item or "").strip().casefold() for item in raw_team]
        if isinstance(raw_team, list)
        else [primary]
    )
    # One native unit currently has one exact child context. Multi-specialist
    # teams must be represented as separate planned units, never silently
    # collapsed to their first member.
    if not primary or team != [primary]:
        return None
    references = {
        str(item.get("slug") or "").strip().casefold(): item
        for item in raw_references
        if isinstance(item, Mapping)
    }
    reference = references.get(primary)
    catalog_by_slug = {agent_identity(item).casefold(): item for item in catalog}
    agent = catalog_by_slug.get(primary)
    if reference is None or agent is None:
        return None
    if (
        str(agent.get("version") or "").strip() != str(reference.get("version") or "").strip()
        or str(agent.get("hash") or "").strip() != str(reference.get("hash") or "").strip()
    ):
        return None

    child_plan = project_unit_agent_plan(
        [{**source_plan, "depends_on": []}],
        allow_legacy=False,
        require_current=True,
    )
    work_unit_id = str(source_plan.get("work_unit_id") or "").strip().casefold()
    tags: list[Any] = []
    for field in ("tags", "categories"):
        values = agent.get(field)
        if isinstance(values, (list, tuple)):
            tags.extend(values)
    assignment_agents = project_unit_assignment_agents(
        [
            {
                "slug": primary,
                "name": agent.get("name"),
                "description": agent.get("description"),
                "capabilities": agent.get("capabilities"),
                "tags": tags,
                "required_tools": agent.get("required_tools"),
                "evidence_requirements": agent.get("evidence_requirements"),
                "matched_work_unit_ids": [work_unit_id],
                "primary_work_unit_ids": [work_unit_id],
            }
        ],
        strict=True,
    )
    if child_plan is None or assignment_agents is None or not assignment_agents:
        return None

    from agency_runtime.core.selector.delegation_detection import detect_work_units

    work_units = {
        **detect_work_units(user_message),
        "delegate": True,
        "count": 1,
        "source": "parent_unit_reuse",
    }
    current_message_hash = sha256(user_message.encode("utf-8", errors="surrogatepass")).hexdigest()
    routing = {
        "selected_ids": [primary],
        "semantic_ids": [primary],
        "companion_ids": [],
        "confidence": float(source_plan.get("selection_confidence") or 0.0),
        "top_score": float(source_plan.get("selection_confidence") or 0.0),
        "latency_ms": 0,
        "candidate_count": len(catalog),
        "status": "parent_unit_reused",
        "source": "parent_unit_reuse",
        "work_units": work_units,
        "query_hash": current_message_hash,
        "source_message_hash": current_message_hash,
        "context_fingerprint": routing_fingerprint,
        "origin_trace_id": parent_trace_id,
        "cache_hit": False,
        "session_reused": False,
        "parent_unit_reused": True,
        "continuation_reused": False,
        "continuation_resolution_required": False,
        "fallback_considered": False,
        "fallback_applied": False,
        "inference_attempted": False,
        "inference_mode": "parent_unit_reuse",
        "child_routing_source": "parent_unit_reuse",
        "execution_context": capability_receipt.as_dict(),
        "_cached_unit_assignment_agents": assignment_agents,
        "_cached_unit_agent_plan": child_plan,
    }
    try:
        hydrate_unit_agent_plan(routing, child_plan)
    except RuntimeError:
        return None
    return routing


def _activate_direct_native_child(
    store: Store,
    result: PreflightResult,
    *,
    parent_session_id: str,
    parent_trace_id: str,
    user_message: str,
    host: str,
    worker_id: str,
    native_run_id: str,
) -> PreflightResult:
    """Consume one exact parent grant at a native child's pre-LLM boundary."""

    normalized_host = str(host or "").strip().casefold()
    if not parent_trace_id or normalized_host not in _DIRECT_NATIVE_CHILD_HOSTS:
        return result
    worker = str(worker_id or "").strip()
    native = str(native_run_id or "").strip()
    if not worker or not native:
        raise RuntimeError("direct native child activation lacks host-issued child lineage")
    if (
        result.routing.get("source") != "parent_unit_reuse"
        or result.routing.get("status") != "parent_unit_reused"
        or len(result.selected_specialists) != 1
        or len(result.delegation_plan) != 1
    ):
        raise RuntimeError("direct native child activation requires one exact parent plan row")
    slug = result.selected_specialists[0]
    plan = result.delegation_plan[0]
    if (
        plan.get("recommended_agent") != slug
        or plan.get("recommended_agents") != [slug]
        or work_unit_goal_hash(user_message) != plan.get("goal_hash")
    ):
        raise RuntimeError("direct native child activation does not match the parent assignment")
    unit = str(plan.get("work_unit_id") or "").strip()
    snapshot = store.get_completion_evidence_snapshot(parent_session_id, parent_trace_id)
    references = {
        str(item.get("slug") or "").strip(): item
        for item in snapshot.get("selected_specialists", [])
        if isinstance(item, Mapping)
    }
    reference = references.get(slug)
    if reference is None:
        raise RuntimeError("direct native child specialist reference is unavailable")
    prompt = store.get_versioned_specialist_prompt(
        slug,
        str(reference.get("version") or ""),
        str(reference.get("hash") or ""),
        max_chars=_MAX_PREFLIGHT_CONTEXT_CHARS,
    )
    prompt_body = prompt.get("prompt_body") if isinstance(prompt, Mapping) else None
    if (
        not isinstance(prompt_body, str)
        or not prompt_body
        or prompt.get("prompt_truncated") is not False
        or prompt_body not in result.context
    ):
        raise RuntimeError(
            "direct native child context lacks the exact selected specialist "
            f"(prompt_chars={len(prompt_body or '')}, context_chars={len(result.context)})"
        )
    lineage = store.get_consumed_delegation_lineage(
        session_id=parent_session_id,
        trace_id=parent_trace_id,
        specialist_slug=slug,
        work_unit_id=unit,
    )
    expected_lineage = {
        "worker_kind": "generic-worker",
        "worker_id": worker,
        "native_run_id": native,
    }
    if lineage is not None:
        if lineage != expected_lineage:
            raise RuntimeError("direct native child activation is bound to another worker")
        return result
    activation_contract = native_child_activation_contract(
        user_message,
        mutation_scope=plan.get("mutation_scope"),
        resource_hashes=plan.get("resource_hashes"),
        required_evidence=plan.get("required_evidence"),
    )
    try:
        prepared = store.prepare_delegation_activation(
            session_id=parent_session_id,
            trace_id=parent_trace_id,
            specialist_slug=slug,
            work_unit_id=unit,
            worker_kind="generic-worker",
            worker_id=worker,
            **activation_contract,
        )
        consumed = store.consume_delegation_activation(
            activation_token=prepared["activation_token"],
            session_id=parent_session_id,
            trace_id=parent_trace_id,
            specialist_slug=slug,
            work_unit_id=unit,
            worker_id=worker,
            native_run_id=native,
        )
    except ValueError as error:
        lineage = store.get_consumed_delegation_lineage(
            session_id=parent_session_id,
            trace_id=parent_trace_id,
            specialist_slug=slug,
            work_unit_id=unit,
        )
        if lineage != expected_lineage:
            raise RuntimeError("direct native child activation could not be consumed") from error
        return result
    if (
        consumed.get("slug") != slug
        or consumed.get("version") != reference.get("version")
        or consumed.get("prompt_hash") != reference.get("hash")
        or consumed.get("prompt_body") != prompt_body
    ):
        raise RuntimeError("direct native child activation receipt changed specialist identity")
    return result


def _activate_or_close_direct_native_child(
    store: Store,
    result: PreflightResult,
    *,
    child_session_id: str,
    child_trace_id: str,
    parent_session_id: str,
    parent_trace_id: str,
    user_message: str,
    host: str,
    worker_id: str,
    native_run_id: str,
) -> PreflightResult:
    """Terminalize a child whose exact pre-LLM activation cannot be proven."""

    try:
        return _activate_direct_native_child(
            store,
            result,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            user_message=user_message,
            host=host,
            worker_id=worker_id,
            native_run_id=native_run_id,
        )
    except Exception:
        if parent_trace_id and str(host or "").strip().casefold() in _DIRECT_NATIVE_CHILD_HOSTS:
            store.close_turn_evidence(
                child_session_id,
                child_trace_id,
                status="specialist_activation_failed",
            )
        raise


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

    planned_parent_unit = _planned_parent_unit_routing(
        store,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        user_message=user_message,
        host=host,
        catalog=catalog,
        routing_fingerprint=routing_fingerprint,
        capability_receipt=capability_receipt,
    )
    if planned_parent_unit is not None:
        return planned_parent_unit, None, classification

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
            cached["_cached_unit_agent_plan"] = list(decision.get("unit_agent_plan", []))
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
        return [], []
    if "_cached_unit_assignment_agents" in routing:
        return list(routing["_cached_unit_assignment_agents"]), list(
            routing.get("_cached_unit_agent_plan", [])
        )
    if continuation_snapshot is not None:
        source = continuation_snapshot["recipe"]
        return list(source.get("unit_assignment_agents", [])), list(
            source.get("unit_agent_plan", [])
        )
    workforce_assignments = routing.get("unit_assignment_agents")
    if isinstance(workforce_assignments, (list, tuple)):
        projected = project_unit_assignment_agents(workforce_assignments, strict=True)
        if projected is None:
            raise RuntimeError("verified workforce assignments are malformed")
        return projected, _suggestion_recipe(
            {**routing, "unit_assignment_agents": projected},
            config.delegation,
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


def _publish_child_routing_bundle(
    store: Store,
    routing: dict[str, Any],
    *,
    trace_id: str,
    unit_assignment_agents: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
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
                "unit_agent_plan": suggestions,
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

    if delivery_mode != "isolated":
        return
    if loaded_slugs and not suggestions:
        raise RuntimeError("isolated specialist selection lacks an exact unit-agent plan")
    if not suggestions:
        return
    planned_agents = set(_suggested_specialist_slugs(suggestions))
    missing_agents = planned_agents.difference(loaded_slugs)
    if missing_agents:
        missing = ", ".join(sorted(missing_agents))
        raise RuntimeError(f"unit-agent plan has unavailable specialist prompts: {missing}")


def _abstain_unplanned_isolated_selection(
    routing: dict[str, Any],
    unit_assignment_agents: list[dict[str, Any]],
    suggestions: list[dict[str, Any]],
    *,
    delivery_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Never present an unbound specialist as usable in a persistent parent.

    Current workforce routes produce exact unit rows. This guard contains a
    legacy, malformed, or degraded route that selected identities without a
    child-activation recipe; guessing a unit-to-specialist mapping here would
    bypass conflict and goal binding.
    """

    selected = [str(item).strip() for item in routing.get("selected_ids", []) if str(item).strip()]
    if delivery_mode != "isolated" or not selected or suggestions:
        return routing, unit_assignment_agents, suggestions
    work_units = routing.get("work_units")
    bounded_units = dict(work_units) if isinstance(work_units, Mapping) else {}
    bounded_units.update(delegate=False, source="isolated_plan_policy")
    return (
        {
            **routing,
            "selected_ids": [],
            "semantic_ids": [],
            "companion_ids": [],
            "confidence": 0.0,
            "status": "abstained",
            "source": "isolated_plan_policy",
            "work_units": bounded_units,
            "fallback_considered": False,
            "fallback_applied": False,
        },
        [],
        [],
    )


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
        "suggestions": suggestions,
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


def _codex_native_plan_scopes_for_result(
    result: PreflightResult,
    *,
    host: str,
    delivery_mode: str,
    specialist_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Project exact private path authority while plaintext goals are available."""

    if host != "codex" or delivery_mode != "isolated":
        return []
    if result.routing.get("continuation_reused") is True:
        # A continuation replays public context but does not authorize a second
        # execution of the source turn's already-issued native plan.
        return []
    references = {
        str(item.get("slug") or "").strip(): item
        for item in specialist_refs
        if isinstance(item, dict) and str(item.get("slug") or "").strip()
    }
    scopes: list[dict[str, Any]] = []
    for row in result.delegation_plan:
        goal = str(row.get("goal") or "").strip()
        slug = str(row.get("recommended_agent") or "").strip()
        reference = references.get(slug)
        if not goal or reference is None:
            raise RuntimeError("Codex native plan scope lost its exact preflight authority")
        try:
            contract = native_child_activation_contract(
                goal,
                mutation_scope=row.get("mutation_scope"),
                resource_hashes=row.get("resource_hashes"),
                required_evidence=row.get("required_evidence"),
            )
            scope = build_codex_native_plan_scope(
                work_unit_id=row.get("work_unit_id"),
                specialist_slug=slug,
                specialist_version=reference.get("version"),
                specialist_prompt_hash=reference.get("hash"),
                goal_hash=row.get("goal_hash"),
                resource_hashes=row.get("resource_hashes"),
                mutation_mode=contract["mutation_mode"],
                mutation_path_prefixes=contract["mutation_path_prefixes"],
                evidence_contract_id=contract["evidence_contract_id"],
                evidence_requirements=contract["evidence_requirements"],
            )
        except (TypeError, ValueError) as exc:
            raise PreflightInvariantError("native_plan_scope_invalid") from exc
        scopes.append(scope.as_dict())
    return scopes


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
        MAX_SPECIALIST_CONTEXT_CHARS,
        hydrate_selected_specialist_context,
        hydrate_selected_specialist_references,
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
        unit_assignment_agents, suggestions = _assignment_recipe(
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
        routing, unit_assignment_agents, suggestions = _abstain_unplanned_isolated_selection(
            routing,
            unit_assignment_agents,
            suggestions,
            delivery_mode=delivery_mode,
        )
        # Isolated delivery may reject a selected identity that lacks an exact
        # child-activation plan. Recheck the normalized route so a malformed
        # pre-plan selection cannot bypass the no-generalist boundary.
        _require_substantive_specialist(routing, classification, diagnostics)
        if diagnostics is not None:
            diagnostics.enter("context_hydration")
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
        hydration_arguments = {
            "session_id": session_id,
            "trace_id": trace_id,
            "disabled_agents": frozenset(config.agents.disabled),
        }
        loaded = (
            hydrate_selected_specialist_references(
                hydration_store,
                hydration_catalog,
                hydration_routing,
                **hydration_arguments,
            )
            if delivery_mode == "isolated"
            else hydrate_selected_specialist_context(
                hydration_store,
                hydration_catalog,
                hydration_routing,
                record_evidence=False,
                maximum_chars=specialist_budget,
                **hydration_arguments,
            )
        )
        _require_available_unit_plan_agents(
            delivery_mode=delivery_mode,
            suggestions=suggestions,
            loaded_slugs=loaded.slugs,
        )
        if diagnostics is not None:
            diagnostics.enter("context_delivery")
        routing_recipe = _content_free_routing_recipe(routing, trace_id=trace_id)
        specialist_refs, selection_refs = _recipe_revision_refs(
            hydration_store,
            hydration_catalog,
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
        validated_result = _result_from_recipe(
            hydration_store,
            recipe,
            session_id=session_id,
            trace_id=trace_id,
            user_message=user_message,
            config=config,
            pipeline=pipeline,
        )
        codex_native_plan_scopes = _codex_native_plan_scopes_for_result(
            validated_result,
            host=host,
            delivery_mode=delivery_mode,
            specialist_refs=specialist_refs,
        )
        if isinstance(cache_owner, Mapping):
            _publish_child_routing_bundle(
                store,
                routing,
                trace_id=trace_id,
                unit_assignment_agents=unit_assignment_agents,
                suggestions=suggestions,
                ttl_seconds=config.delegation.child_cache_ttl_seconds,
            )
        child_route_guard.pop_all()
        return (
            recipe,
            routing_recipe,
            suggestions,
            specialist_refs,
            classification,
            codex_native_plan_scopes,
        )


def _require_substantive_specialist(
    routing: Mapping[str, Any],
    classification: TurnClassification,
    diagnostics: _PreflightFailureDiagnostics | None = None,
) -> None:
    """Prevent a resident-only parent model from answering substantive work.

    Planning, recruitment, gap hiring, and restaffing have all completed before
    this boundary. A substantive turn that still has no non-resident identity is
    therefore terminal: continuing would silently turn the host model into the
    universal generalist ADR-0122 forbids.
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
    raise RuntimeError(
        "substantive Agency turn has no accepted specialist or contractor; "
        f"status={status}; source={source}"
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
    direct_activation_arguments = {
        "child_session_id": normalized_session,
        "child_trace_id": turn_trace_id,
        "parent_session_id": normalized_parent_session,
        "parent_trace_id": normalized_parent_trace,
        "user_message": user_message,
        "host": normalized_host,
        "worker_id": native_worker_id,
        "native_run_id": native_run_id,
    }

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
            diagnostics.enter("direct_activation")
            return _activate_or_close_direct_native_child(
                store,
                reused_result,
                **direct_activation_arguments,
            )
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
            diagnostics.enter("direct_activation")
            return _activate_or_close_direct_native_child(
                store,
                reused_result,
                **direct_activation_arguments,
            )
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
        }
        (
            recipe,
            routing_recipe,
            suggestions,
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
            suggestions=suggestions,
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
                suggestions,
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
                suggestions=suggestions,
                specialist_refs=specialist_refs,
                codex_native_plan_scopes=codex_native_plan_scopes,
                user_message=user_message,
                config=cfg,
                pipeline=pipeline,
            )
        if not isinstance(ready, dict) or ready.get("outcome") not in {
            "committed",
            "replay",
        }:
            raise RuntimeError("preflight attempt became terminal before it reached ready")
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
        diagnostics.enter("direct_activation")
        return _activate_or_close_direct_native_child(
            store,
            ready_result,
            **direct_activation_arguments,
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
                    failure_receipt=diagnostics.receipt(error),
                )
            elif not attempt_token and normalized_reservation_token:
                store.abandon_preflight_reservation(
                    session_id=normalized_session,
                    trace_id=turn_trace_id,
                    reservation_token=normalized_reservation_token,
                    status="preflight_failed",
                    failure_receipt=diagnostics.receipt(error),
                )
        except Exception as cleanup_error:
            raise error from cleanup_error
        raise


__all__ = ["MAX_PREFLIGHT_CONTEXT_CHARS", "PreflightResult", "run_preflight"]
