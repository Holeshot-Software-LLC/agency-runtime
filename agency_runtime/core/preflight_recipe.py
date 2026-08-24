"""Content-free durable preflight recipes and exact read-only replay."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from hashlib import sha256
from time import monotonic, sleep
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.bounded_values import bounded_unique_strings
from agency_runtime.core.config import AgencyConfig, DelegationConfig
from agency_runtime.core.host_capabilities import project_host_capability_receipt
from agency_runtime.core.operator_policy import render_operator_policy
from agency_runtime.core.preflight_versions import (
    PREFLIGHT_CONTEXT_POLICY_VERSION,
    PREFLIGHT_REPLAY_RECIPE_VERSION,
    SUPPORTED_PREFLIGHT_RECIPE_VERSIONS,
)
from agency_runtime.core.resident_manager_binding import (
    PERSISTENT_RESIDENT_MANAGER_HOSTS,
    REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS,
    RESIDENT_MANAGER_BINDING_VERSION,
    ResidentManagerBinding,
    canonical_resident_manager_host,
    resident_manager_turn_reference_context,
    validate_resident_manager_binding,
)
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_REFERENCE,
    RESIDENT_MANAGER_SLUGS,
    is_current_resident_manager_kernel_reference,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import (
    TURN_CLASSIFIER_VERSION,
    TURN_KINDS,
    TurnClassification,
)

MAX_PREFLIGHT_CONTEXT_CHARS = 32_000
LITELLM_PREFLIGHT_CONTEXT_CHARS = 16_384
PERSISTENT_HOST_CONTEXT_CHARS = MAX_PREFLIGHT_CONTEXT_CHARS
PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES = 48_000
_SUPPORTED_PREFLIGHT_RECIPE_VERSIONS = SUPPORTED_PREFLIGHT_RECIPE_VERSIONS
_PREFLIGHT_OBSERVER_INITIAL_POLL_SECONDS = 0.025
_PREFLIGHT_OBSERVER_MAX_POLL_SECONDS = 0.25
_MAX_ROUTING_IDS = 16
_MAX_ROUTING_ID_CHARS = 128
_MAX_ROUTING_LABEL_CHARS = 64
_MAX_ROUTING_COUNT = 1_000_000


_bounded_unique_strings = partial(
    bounded_unique_strings,
    limit=_MAX_ROUTING_IDS,
    chars=_MAX_ROUTING_ID_CHARS,
)


def _bounded_label(value: Any) -> str:
    return str(value or "").strip()[:_MAX_ROUTING_LABEL_CHARS]


def _bounded_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(-1_000_000.0, min(parsed, 1_000_000.0)) if math.isfinite(parsed) else 0.0


def _bounded_count(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(parsed, _MAX_ROUTING_COUNT))


def _digest(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return (
        normalized
        if len(normalized) == 64 and all(char in "0123456789abcdef" for char in normalized)
        else ""
    )


def _work_unit_metadata(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        "delegate": bool(raw.get("delegate")),
        "count": min(_bounded_count(raw.get("count")), 16),
        "confidence": _bounded_label(raw.get("confidence")),
        "source": _bounded_label(raw.get("source")),
    }


def _workforce_unit_descriptors(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    from agency_runtime.core.workforce.routing_projection import (
        project_workforce_unit_descriptors,
    )

    result = project_workforce_unit_descriptors(value)
    if result is None:
        raise RuntimeError("workforce unit descriptors are malformed")
    return result


def _workforce_routing_recipe_fields(routing: Mapping[str, Any]) -> dict[str, Any]:
    """Project bounded workforce fields without widening routing retention."""

    from agency_runtime.core.activation_canary_contract import (
        CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
    )
    from agency_runtime.core.turn_routing_context import (
        workforce_subject_hints_from_plan,
    )
    from agency_runtime.core.workforce.routing_projection import (
        project_workforce_unit_bindings,
    )

    descriptors = _workforce_unit_descriptors(routing.get("workforce_unit_descriptors"))
    source = str(routing.get("source") or "")
    activation_canary = source == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
    if not (descriptors or source.startswith("workforce_") or activation_canary):
        return {}

    projected: dict[str, Any] = {}
    if not activation_canary:
        projected["workforce_unit_descriptors"] = descriptors
        subject_hints = workforce_subject_hints_from_plan(routing.get("workforce_plan"))
        if subject_hints is None:
            raise RuntimeError("workforce subject hints are malformed")
        if subject_hints:
            projected["workforce_subject_hints"] = subject_hints
    bindings = project_workforce_unit_bindings(routing.get("workforce_unit_bindings"))
    if bindings is None:
        raise RuntimeError("workforce unit bindings are malformed")
    projected["workforce_unit_bindings"] = bindings
    return projected


def _content_free_routing_recipe(
    routing: dict[str, Any],
    *,
    trace_id: str,
) -> dict[str, Any]:
    """Project only bounded fields needed for audit and context replay."""
    from agency_runtime.core.selector.receipt_projection import (
        project_durable_routing_receipt,
        project_model_receipt_attempts,
    )

    projected: dict[str, Any] = {
        "trace_id": trace_id,
        "selected_ids": _bounded_unique_strings(routing.get("selected_ids")),
        "semantic_ids": _bounded_unique_strings(routing.get("semantic_ids")),
        "companion_actions": _bounded_unique_strings(routing.get("companion_actions")),
        "companion_ids": _bounded_unique_strings(routing.get("companion_ids")),
        "available_companion_ids": _bounded_unique_strings(routing.get("available_companion_ids")),
        "unavailable_companion_ids": _bounded_unique_strings(
            routing.get("unavailable_companion_ids")
        ),
        "fallback_companion_ids": _bounded_unique_strings(routing.get("fallback_companion_ids")),
        "available_fallback_companion_ids": _bounded_unique_strings(
            routing.get("available_fallback_companion_ids")
        ),
        "unavailable_fallback_companion_ids": _bounded_unique_strings(
            routing.get("unavailable_fallback_companion_ids")
        ),
        "status": _bounded_label(routing.get("status")),
        "source": _bounded_label(routing.get("source")),
        "confidence": _bounded_float(routing.get("confidence")),
        "top_score": _bounded_float(routing.get("top_score")),
        "latency_ms": _bounded_count(routing.get("latency_ms")),
        "candidate_count": _bounded_count(routing.get("candidate_count")),
        "cache_hit": bool(routing.get("cache_hit")),
        "session_reused": bool(routing.get("session_reused")),
        "continuation_reused": bool(routing.get("continuation_reused")),
        "continuation_resolution_required": bool(routing.get("continuation_resolution_required")),
        "fallback_considered": bool(routing.get("fallback_considered")),
        "fallback_applied": bool(routing.get("fallback_applied")),
        "work_units": _work_unit_metadata(routing.get("work_units")),
        "routing_receipt": project_durable_routing_receipt(routing),
    }
    model_receipt_attempts = project_model_receipt_attempts(routing.get("provider_attempts"))
    if model_receipt_attempts is None:
        raise RuntimeError("routing provider attempts are malformed or unbounded")
    if model_receipt_attempts:
        projected["model_receipt_attempts"] = model_receipt_attempts
    pending_hiring = routing.get("_pending_hiring_commits")
    if pending_hiring is not None:
        from agency_runtime.core.workforce.hiring import PendingHiringCommit

        if (
            not isinstance(pending_hiring, list)
            or len(pending_hiring) > 16
            or any(not isinstance(item, PendingHiringCommit) for item in pending_hiring)
        ):
            raise RuntimeError("pending hiring commits are malformed or unbounded")
        if pending_hiring:
            projected["_pending_hiring_commits"] = list(pending_hiring)
    projected.update(_workforce_routing_recipe_fields(routing))
    raw_execution_context = routing.get("execution_context")
    if raw_execution_context is not None:
        execution_context = project_host_capability_receipt(raw_execution_context)
        if execution_context is None:
            raise RuntimeError("routing capability receipt is malformed")
        projected["execution_context"] = execution_context
    for field in (
        "query_hash",
        "context_fingerprint",
        "source_message_hash",
        "origin_query_hash",
        "origin_context_fingerprint",
        "turn_context_revision",
    ):
        digest = _digest(routing.get(field))
        if digest:
            projected[field] = digest
    origin_trace_id = str(routing.get("origin_trace_id") or "").strip()[:128]
    if origin_trace_id:
        projected["origin_trace_id"] = origin_trace_id
    turn_context_source = str(routing.get("turn_context_source_trace_id") or "").strip()[:128]
    if turn_context_source:
        projected["turn_context_source_trace_id"] = turn_context_source
    projected["turn_context_applied"] = routing.get("turn_context_applied") is True
    return projected


def _shared_delegation_goal_prefix(goals: list[str]) -> str:
    """Return the exact request prefix repeated by typed workforce unit goals."""

    if len(goals) < 2 or any(not isinstance(goal, str) or not goal for goal in goals):
        return ""
    marker = ". Work unit "
    marker_at = goals[0].rfind(marker)
    if marker_at < 0:
        return ""
    prefix = goals[0][: marker_at + len(marker)]
    if len(prefix) < 128 or any(
        not goal.startswith(prefix) or len(goal) == len(prefix) for goal in goals
    ):
        return ""
    return prefix


def _continuation_context(routing: dict[str, Any]) -> str:
    """Explain a reused recipe; the native session history owns prior task text.

    The unit-binding block this used to append was Job B. The rest is not: a
    continuation recipe genuinely carries no prior prompt, and without this the
    host would treat the opaque continuation token as the task.
    """

    origin = str(routing.get("origin_trace_id") or "").strip()
    return "\n".join(
        [
            "[AGENCY CONTINUATION] This turn reuses a validated immediate-prior routing recipe "
            f"from trace {origin}.",
            "The durable recipe intentionally contains no prior task or prompt body. Resolve "
            "the goal from the native parent session; never use the literal continuation token "
            "as a worker task. If that native context is unavailable, ask the user to restate "
            "instead of selecting, judging, or launching duplicate work.",
        ]
    )


def _continuation_abstention_context() -> str:
    return (
        "[AGENCY CONTINUATION UNAVAILABLE] The immediate prior routing recipe could not be "
        "validated against current configuration, roster, specialist revisions, or delegation "
        "state. Resident managers must abstain from specialist selection and worker launch. "
        "Use trustworthy native session context if it fully identifies the requested work; "
        "otherwise ask the user to restate the task."
    )


def preflight_delivery_policy(
    host: str,
    *,
    native_child: bool = False,
) -> tuple[str, int]:
    """Return the truthful specialist delivery mode and context ceiling for a host."""

    normalized = str(host or "unknown").strip().casefold()
    if normalized in {"openclaw", "hermes"} and native_child:
        return "direct", MAX_PREFLIGHT_CONTEXT_CHARS
    if normalized in {"codex", "claude", "openclaw", "hermes", "zcode"}:
        return "direct", PERSISTENT_HOST_CONTEXT_CHARS
    if normalized == "litellm":
        return "direct", LITELLM_PREFLIGHT_CONTEXT_CHARS
    return "direct", MAX_PREFLIGHT_CONTEXT_CHARS


def _combine_context(
    routing_context: str,
    specialist_context: str,
    *,
    maximum_chars: int = MAX_PREFLIGHT_CONTEXT_CHARS,
) -> str:
    """Combine two already-bounded projections under one hard prompt ceiling."""
    maximum = max(0, int(maximum_chars))
    routing = str(routing_context or "")
    specialist = str(specialist_context or "")
    if len(routing) > maximum:
        raise RuntimeError("routing context exceeds the host delivery ceiling")
    if not specialist:
        return routing
    if not routing:
        if len(specialist) > maximum:
            raise RuntimeError("specialist context exceeds the host delivery ceiling")
        return specialist
    combined = f"{routing}\n\n{specialist}"
    if len(combined) > maximum:
        raise RuntimeError("combined context exceeds the host delivery ceiling")
    return combined


def _persistent_host_context_output_bytes(context: str) -> int:
    """Return the exact context-only UserPromptSubmit envelope size."""

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": str(context or ""),
        }
    }
    return (
        len(
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        + 1
    )


def _require_persistent_host_context_output(context: str) -> None:
    """Reject any context that cannot fit the bounded hook envelope.

    This ceiling is a property of the hook transport, not of a delivery mode.
    It was previously enforced for isolated delivery only, which left the
    encoded envelope unguarded once direct became the only mode: the character
    limit permits 32k characters, and multibyte content can encode to well over
    the byte ceiling. Applied unconditionally, so the bound follows the
    transport it actually protects.
    """

    if _persistent_host_context_output_bytes(context) > PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES:
        raise RuntimeError("specialist recipe exceeds the encoded host delivery ceiling")


def _context_policy_fingerprint(
    config: AgencyConfig,
    pipeline: Any,
    *,
    delivery_mode: str = "direct",
    context_limit: int = MAX_PREFLIGHT_CONTEXT_CHARS,
    recipe_version: int = PREFLIGHT_REPLAY_RECIPE_VERSION,
    context_policy_version: int | None = None,
) -> str:
    """Bind replay to every resolved input that controls context rendering.

    The two policy version constants must be bumped whenever routing,
    specialist, or combined-context formatting semantics change.
    """
    effective_context_version = (
        int(context_policy_version)
        if context_policy_version is not None
        else int(PREFLIGHT_CONTEXT_POLICY_VERSION)
    )
    policy = {
        "recipe_version": int(recipe_version),
        "context_policy_version": effective_context_version,
        "selector_min_confidence": float(config.selector.min_confidence),
        "routing_context_limit": int(pipeline.MAX_ROUTING_CONTEXT_CHARS),
        "combined_context_limit": MAX_PREFLIGHT_CONTEXT_CHARS,
        "delivery_mode": delivery_mode,
        "host_context_limit": int(context_limit),
        "header_instruction_hash": sha256(
            str(pipeline.HEADER_INSTRUCTION).encode("utf-8")
        ).hexdigest(),
    }
    if effective_context_version >= 7:
        policy["resident_manager_kernel"] = RESIDENT_MANAGER_KERNEL_REFERENCE.as_dict()
    if effective_context_version >= 8:
        policy["resident_manager_binding_version"] = RESIDENT_MANAGER_BINDING_VERSION
        policy["persistent_resident_manager_hosts"] = list(PERSISTENT_RESIDENT_MANAGER_HOSTS)
        policy["request_resident_manager_hosts"] = list(REQUEST_SCOPED_RESIDENT_MANAGER_HOSTS)
    if effective_context_version >= 11:
        policy["delegation"] = {
            "mode": config.delegation.mode,
            "preferred_min_units": config.delegation.preferred_min_units,
            "strongly_preferred_min_units": config.delegation.strongly_preferred_min_units,
            "strongly_preferred_min_confidence": (
                config.delegation.strongly_preferred_min_confidence
            ),
            "child_inference_budget": config.delegation.child_inference_budget,
            "child_inference_concurrency": config.delegation.child_inference_concurrency,
            "child_cache_ttl_seconds": config.delegation.child_cache_ttl_seconds,
        }
    if effective_context_version >= 13:
        policy["persistent_host_context_output_bytes"] = PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


def _recipe_turn_classification(
    recipe: dict[str, Any],
    *,
    trivial: bool,
    session_id: str,
    trace_id: str,
    user_message: str,
) -> TurnClassification:
    """Read v6 state evidence or derive a bounded v5 compatibility decision."""

    version = recipe.get("recipe_version")
    if version == 5:
        state_revision = sha256(
            f"legacy-v5\0{session_id}\0{trace_id}\0{int(trivial)}".encode()
        ).hexdigest()
        return TurnClassification(
            turn_kind="acknowledgement" if trivial else "new_intent",
            selection_required=not trivial,
            reroute_required=not trivial,
            execution_decision_required=not trivial,
            continuation_of="",
            confidence=1.0,
            reason_codes=("legacy_v5_projection",),
            state_revision=state_revision,
            classifier_version=1,
            message_fingerprint=sha256(
                user_message.encode("utf-8", errors="surrogatepass")
            ).hexdigest(),
        )

    raw = recipe.get("turn_classification")
    if not isinstance(raw, dict):
        raise RuntimeError("ready preflight turn classification is missing")
    turn_kind = str(raw.get("turn_kind") or "")
    state_revision = _digest(raw.get("state_revision"))
    continuation_of = str(raw.get("continuation_of") or "").strip()
    classifier_version = raw.get("classifier_version")
    message_fingerprint = str(raw.get("message_fingerprint") or "").strip()
    expected_message_fingerprint = sha256(
        user_message.encode("utf-8", errors="surrogatepass")
    ).hexdigest()
    confidence = raw.get("confidence")
    reason_codes = raw.get("reason_codes")
    boolean_fields = {
        field: raw.get(field)
        for field in (
            "selection_required",
            "reroute_required",
            "execution_decision_required",
        )
    }
    if (
        turn_kind not in TURN_KINDS
        or not state_revision
        or isinstance(classifier_version, bool)
        or not isinstance(classifier_version, int)
        or not 1 <= classifier_version <= TURN_CLASSIFIER_VERSION
        or any(not isinstance(value, bool) for value in boolean_fields.values())
        or not isinstance(reason_codes, list)
        or len(reason_codes) > 8
        or any(not isinstance(reason, str) or not reason for reason in reason_codes)
        or (continuation_of and len(continuation_of) > 128)
    ):
        raise RuntimeError("ready preflight turn classification is malformed")
    if message_fingerprint and message_fingerprint != expected_message_fingerprint:
        raise RuntimeError("ready preflight turn classification message does not match")
    if classifier_version >= 3 and not message_fingerprint:
        raise RuntimeError("ready preflight turn classification message does not match")
    if not message_fingerprint:
        message_fingerprint = expected_message_fingerprint
    try:
        return TurnClassification(
            turn_kind=turn_kind,
            selection_required=boolean_fields["selection_required"],
            reroute_required=boolean_fields["reroute_required"],
            execution_decision_required=boolean_fields["execution_decision_required"],
            continuation_of=continuation_of,
            confidence=_bounded_float(confidence),
            reason_codes=tuple(reason_codes),
            state_revision=state_revision,
            classifier_version=classifier_version,
            message_fingerprint=message_fingerprint,
        )
    except ValueError as exc:
        raise RuntimeError("ready preflight turn classification is malformed") from exc


def _recipe_resident_binding(
    recipe: dict[str, Any],
    *,
    session_id: str,
) -> ResidentManagerBinding | None:
    """Validate the v9+ control-bound session receipt while preserving legacy replay."""

    version = recipe.get("recipe_version")
    raw_binding = recipe.get("resident_manager_binding")
    if isinstance(version, int) and version < 8:
        if raw_binding is not None:
            raise RuntimeError("legacy preflight recipe cannot bind a resident-manager host")
        return None
    try:
        binding = validate_resident_manager_binding(raw_binding, session_id=session_id)
    except ValueError as exc:
        raise RuntimeError("ready preflight resident-manager binding is invalid") from exc
    if binding.host != canonical_resident_manager_host(recipe.get("host")):
        raise RuntimeError("ready preflight resident-manager host does not match")
    return binding


def _recipe_resident_managers(
    recipe: dict[str, Any],
    *,
    binding: ResidentManagerBinding | None,
) -> tuple[str, ...]:
    """Verify the compact manager binding for v7+ while preserving old replay."""

    version = recipe.get("recipe_version")
    if isinstance(version, int) and version < 7:
        if recipe.get("resident_manager_kernel") is not None:
            raise RuntimeError("legacy preflight recipe cannot bind a resident-manager kernel")
        return ()
    if version == 7:
        reference = recipe.get("resident_manager_kernel")
        if not is_current_resident_manager_kernel_reference(reference):
            raise RuntimeError("ready preflight resident-manager kernel is invalid")
    elif recipe.get("resident_manager_kernel") is not None or binding is None:
        raise RuntimeError("ready preflight resident-manager binding is invalid")
    return RESIDENT_MANAGER_SLUGS


def _resident_manager_context(
    binding: ResidentManagerBinding,
    *,
    session_id: str,
    trace_id: str,
) -> str:
    """Render a full injection only when the host binding lifecycle requires it."""

    reference = resident_manager_turn_reference_context(
        binding,
        session_id=session_id,
        trace_id=trace_id,
    )
    return (
        f"{RESIDENT_MANAGER_KERNEL}\n\n{reference}"
        if binding.requires_kernel_injection
        else reference
    )


def _verified_work_units(recipe_routing: dict[str, Any], user_message: str) -> dict[str, Any]:
    """Re-derive transient unit text and verify its content-free metadata."""
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    expected = recipe_routing.get("work_units")
    if not isinstance(expected, dict):
        raise RuntimeError("ready preflight is missing work-unit metadata")
    descriptors = _workforce_unit_descriptors(recipe_routing.get("workforce_unit_descriptors"))
    if "workforce_unit_descriptors" in recipe_routing:
        from agency_runtime.core.workforce.routing_projection import (
            workforce_work_units_from_descriptors,
        )

        units = workforce_work_units_from_descriptors(user_message, descriptors)
        detected = {
            "delegate": bool(expected.get("delegate")),
            "count": len(units),
            "confidence": expected.get("confidence"),
            "source": expected.get("source"),
            "units": units,
        }
    elif expected.get("source") == "activation-canary-contract":
        from agency_runtime.core.activation_canary_contract import (
            CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
            CODEX_ACTIVATION_CANARY_WORK_UNIT,
            is_exact_codex_activation_canary_task,
        )

        execution_context = project_host_capability_receipt(recipe_routing.get("execution_context"))
        routing_receipt = recipe_routing.get("routing_receipt")
        inference = (
            routing_receipt.get("inference") if isinstance(routing_receipt, Mapping) else None
        )
        if (
            recipe_routing.get("source") != CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
            or not isinstance(inference, Mapping)
            or inference.get("required") is not True
            or inference.get("attempted") is not True
            or not inference.get("provider_attempts")
            or execution_context is None
            or not is_exact_codex_activation_canary_task(
                user_message,
                host=execution_context.get("execution_host"),
                capability_status=execution_context.get("status"),
            )
        ):
            raise RuntimeError("activation canary work-unit replay is not exact and authorized")
        detected = {
            "delegate": True,
            "count": 1,
            "confidence": "high",
            "source": "activation-canary-contract",
            "units": [CODEX_ACTIVATION_CANARY_WORK_UNIT],
        }
    else:
        detected = detect_work_units(user_message)
    detected_metadata = _work_unit_metadata(detected)
    if detected_metadata != expected:
        raise RuntimeError(
            "ready preflight work-unit recipe does not match the request: "
            f"expected={expected!r}, actual={detected_metadata!r}"
        )
    return {
        **expected,
        "units": [
            str(unit)
            for unit in detected.get("units", [])
            if isinstance(unit, str) and unit.strip()
        ],
    }


def _replay_routing_from_recipe(
    routing: dict[str, Any],
    *,
    trace_id: str,
    user_message: str,
    unit_assignment_agents: list[dict[str, Any]],
    delegation: DelegationConfig,
) -> dict[str, Any]:
    """Restore transient units only for an exact same-message replay."""

    continuation = bool(
        routing.get("continuation_reused") is True
        or routing.get("continuation_resolution_required") is True
    )
    replay = dict(routing)
    replay["trace_id"] = trace_id
    replay["work_units"] = (
        {**routing.get("work_units", {}), "units": []}
        if continuation
        else _verified_work_units(replay, user_message)
    )
    replay["unit_assignment_agents"] = unit_assignment_agents
    if continuation:
        return replay
    # Agency no longer builds a unit plan, so there is nothing to re-derive and
    # compare. Stored recipes that still carry one replay without it rather than
    # failing the comparison against an empty rebuild.
    return replay


def _result_from_recipe(
    store: Store,
    recipe: dict[str, Any],
    *,
    session_id: str,
    trace_id: str,
    user_message: str,
    config: AgencyConfig,
    pipeline: Any,
    require_committed_binding: bool = False,
) -> PreflightResult:
    """Rebuild one ready result without selector or evidence-writing side effects."""
    recipe_version = recipe.get("recipe_version")
    if recipe_version not in _SUPPORTED_PREFLIGHT_RECIPE_VERSIONS:
        raise RuntimeError("ready preflight recipe version is unsupported")
    if recipe.get("session_id") != session_id or recipe.get("trace_id") != trace_id:
        raise RuntimeError("ready preflight recipe correlation does not match")
    routing = recipe.get("routing")
    references = recipe.get("specialist_refs")
    selection_refs = recipe.get("selection_refs", [])
    unit_assignment_agents = recipe.get("unit_assignment_agents", [])
    delivery_mode = recipe.get("delivery_mode")
    context_limit = recipe.get("context_limit")
    trivial = recipe.get("trivial")
    roster_size = recipe.get("roster_size")
    roster_generation = recipe.get("roster_generation", 0)
    if (
        not isinstance(routing, dict)
        or not isinstance(references, list)
        or not isinstance(selection_refs, list)
        or not isinstance(unit_assignment_agents, list)
        or delivery_mode != "direct"
        or isinstance(context_limit, bool)
        or not isinstance(context_limit, int)
        or not 256 <= context_limit <= MAX_PREFLIGHT_CONTEXT_CHARS
        or not isinstance(trivial, bool)
        or isinstance(roster_size, bool)
        or not isinstance(roster_size, int)
        or roster_size < 0
        or isinstance(roster_generation, bool)
        or not isinstance(roster_generation, int)
        or roster_generation < 0
        or (recipe_version >= 10 and "selection_refs" not in recipe)
        or (recipe_version >= 10 and "roster_generation" not in recipe)
    ):
        raise RuntimeError("ready preflight recipe is malformed")
    if recipe.get("policy_fingerprint") != _context_policy_fingerprint(
        config,
        pipeline,
        delivery_mode=str(delivery_mode),
        context_limit=context_limit,
        recipe_version=int(recipe_version),
        context_policy_version=int(recipe_version),
    ):
        raise RuntimeError("ready preflight policy fingerprint does not match")

    classification = _recipe_turn_classification(
        recipe,
        trivial=trivial,
        session_id=session_id,
        trace_id=trace_id,
        user_message=user_message,
    )
    resident_binding = _recipe_resident_binding(recipe, session_id=session_id)
    if resident_binding is not None and require_committed_binding:
        validator = getattr(store, "validate_committed_resident_manager_binding", None)
        if (
            not callable(validator)
            or validator(
                session_id=session_id,
                trace_id=trace_id,
                binding=resident_binding,
            )
            is not True
        ):
            raise RuntimeError("ready preflight resident-manager binding is no longer replayable")
    resident_managers = _recipe_resident_managers(recipe, binding=resident_binding)
    resident_context = (
        _resident_manager_context(
            resident_binding,
            session_id=session_id,
            trace_id=trace_id,
        )
        if resident_binding is not None
        else (RESIDENT_MANAGER_KERNEL if resident_managers else "")
    )
    # Operator house rules follow Agency's own frame, never precede it. If the
    # context budget forces a cut, the product contract is what survives — and the
    # rendered block already tells its reader that it yields to the user's request.
    resident_context = _combine_context(
        resident_context,
        render_operator_policy(config.operator_policy),
        maximum_chars=context_limit,
    )

    disabled = frozenset(config.agents.disabled)
    for reference in references:
        if not isinstance(reference, dict):
            continue
        slug = str(reference.get("slug") or "").strip()
        if slug and not agent_is_enabled(slug, disabled):
            store.close_turn_evidence(
                session_id,
                trace_id,
                status="specialist_disabled",
            )
            raise RuntimeError(
                f"selected specialist '{slug}' is disabled; start a fresh Agency preflight"
            )

    continuation_abstained = routing.get("continuation_resolution_required") is True
    replay_routing = _replay_routing_from_recipe(
        routing,
        trace_id=trace_id,
        user_message=user_message,
        unit_assignment_agents=unit_assignment_agents,
        delegation=config.delegation,
    )

    from agency_runtime.core.specialist_context import rebuild_versioned_specialist_context

    if continuation_abstained:
        selected = rebuild_versioned_specialist_context(
            store,
            [],
            disabled_agents=disabled,
        )
        context = _combine_context(
            resident_context,
            _continuation_abstention_context(),
            maximum_chars=context_limit,
        )
        loaded_slugs = ()
    else:
        routing_context = pipeline.build_routing_context(replay_routing, config)
        if replay_routing.get("continuation_reused") is True:
            routing_context = _combine_context(
                routing_context,
                _continuation_context(replay_routing),
                maximum_chars=context_limit,
            )
        manager_routing_context = _combine_context(
            resident_context,
            routing_context,
            maximum_chars=context_limit,
        )
        specialist_budget = max(0, context_limit - len(manager_routing_context) - 2)
        selected = rebuild_versioned_specialist_context(
            store,
            references,
            maximum_chars=specialist_budget,
            disabled_agents=disabled,
        )
        context = _combine_context(
            manager_routing_context,
            selected.context,
            maximum_chars=context_limit,
        )
        loaded_slugs = selected.slugs
    _require_persistent_host_context_output(context)
    return PreflightResult(
        session_id=session_id,
        trace_id=trace_id,
        routing=replay_routing,
        context=context,
        loaded_specialists=loaded_slugs,
        selected_specialists=selected.slugs,
        trivial=trivial,
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
        resident_manager_delivery_mode=(
            resident_binding.delivery_mode if resident_binding is not None else ""
        ),
        resident_manager_host_mode=(
            resident_binding.host_mode if resident_binding is not None else ""
        ),
    )


def _read_ready_result(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    attempt_token: str,
    user_message: str,
    config: AgencyConfig,
    pipeline: Any,
) -> PreflightResult:
    getter = getattr(store, "get_ready_preflight_result", None)
    if not callable(getter):
        raise RuntimeError("evidence store cannot read a ready preflight recipe")
    recipe = getter(
        session_id=session_id,
        trace_id=trace_id,
        attempt_token=attempt_token,
    )
    if not isinstance(recipe, dict):
        raise RuntimeError("ready preflight recipe is unavailable")
    return _result_from_recipe(
        store,
        recipe,
        session_id=session_id,
        trace_id=trace_id,
        user_message=user_message,
        config=config,
        pipeline=pipeline,
        require_committed_binding=True,
    )


def _await_ready_result(
    store: Store,
    *,
    session_id: str,
    trace_id: str,
    attempt_token: str,
    user_message: str,
    config: AgencyConfig,
    pipeline: Any,
    timeout_seconds: float,
) -> PreflightResult:
    """Observe a shared attempt without duplicating or terminalizing its work."""
    observer = getattr(store, "observe_preflight_attempt", None)
    if not callable(observer):
        raise RuntimeError("evidence store cannot observe a shared preflight attempt")
    deadline = monotonic() + max(0.0, float(timeout_seconds))
    poll_seconds = _PREFLIGHT_OBSERVER_INITIAL_POLL_SECONDS
    while True:
        observation = observer(
            session_id=session_id,
            trace_id=trace_id,
            attempt_token=attempt_token,
        )
        if not isinstance(observation, dict):
            raise RuntimeError("shared preflight attempt observation is unavailable")
        recipe = observation.get("recipe")
        if isinstance(recipe, dict):
            return _result_from_recipe(
                store,
                recipe,
                session_id=session_id,
                trace_id=trace_id,
                user_message=user_message,
                config=config,
                pipeline=pipeline,
                require_committed_binding=True,
            )
        if str(observation.get("run_status") or "") != "active":
            raise RuntimeError("shared preflight attempt became terminal before ready")
        if observation.get("attempt_matches", True) is not True:
            raise RuntimeError("shared preflight attempt ownership changed before ready")
        state = str(observation.get("preflight_state") or "")
        if state == "ready":
            raise RuntimeError("ready preflight recipe is unavailable")
        if state != "in_progress":
            raise RuntimeError("shared preflight attempt state is invalid")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise RuntimeError("shared preflight attempt is still in progress")
        sleep(min(poll_seconds, remaining))
        poll_seconds = min(poll_seconds * 2, _PREFLIGHT_OBSERVER_MAX_POLL_SECONDS)


@dataclass(frozen=True, slots=True)
class PreflightResult:
    """One correlated routing decision and the prompt context it activated."""

    session_id: str
    trace_id: str
    routing: dict[str, Any]
    context: str
    loaded_specialists: tuple[str, ...]
    selected_specialists: tuple[str, ...]
    trivial: bool
    roster_size: int
    turn_kind: str = ""
    selection_required: bool = True
    reroute_required: bool = True
    execution_decision_required: bool = True
    continuation_of: str = ""
    classifier_version: int = 0
    state_revision: str = ""
    resident_managers: tuple[str, ...] = ()
    resident_manager_kernel_version: int = 0
    resident_manager_kernel_hash: str = ""
    resident_manager_binding: dict[str, Any] | None = None
    resident_manager_delivery_mode: str = ""
    resident_manager_host_mode: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the stable public projection used by host adapters."""
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "routing": self.routing,
            "context": self.context,
            "loaded_specialists": list(self.loaded_specialists),
            "selected_specialists": list(self.selected_specialists),
            "trivial": self.trivial,
            "roster_size": self.roster_size,
            "turn_kind": self.turn_kind,
            "selection_required": self.selection_required,
            "reroute_required": self.reroute_required,
            "execution_decision_required": self.execution_decision_required,
            "continuation_of": self.continuation_of,
            "classifier_version": self.classifier_version,
            "state_revision": self.state_revision,
            "resident_managers": list(self.resident_managers),
            "resident_manager_kernel_version": self.resident_manager_kernel_version,
            "resident_manager_kernel_hash": self.resident_manager_kernel_hash,
            "resident_manager_binding": self.resident_manager_binding,
            "resident_manager_delivery_mode": self.resident_manager_delivery_mode,
            "resident_manager_host_mode": self.resident_manager_host_mode,
        }
