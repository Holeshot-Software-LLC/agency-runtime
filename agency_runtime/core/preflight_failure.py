"""Bounded, content-free diagnostics for terminal preflight failures."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PREFLIGHT_FAILURE_RECEIPT_SCHEMA = "agency.preflight.failure.v1"
MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES = 32 * 1024

PREFLIGHT_FAILURE_STAGES = frozenset(
    {
        "lifecycle",
        "resident_binding",
        "routing_snapshot",
        "route_request",
        "routing",
        "assignment",
        "context_hydration",
        "context_delivery",
        "ready_commit",
        "ready_read",
        "direct_activation",
    }
)

PREFLIGHT_FAILURE_REASONS = frozenset(
    {
        "preflight_lifecycle_failed",
        "resident_binding_failed",
        "routing_snapshot_failed",
        "route_request_failed",
        "routing_failed",
        "workforce_provider_unavailable",
        "workforce_inference_failed",
        "substantive_specialist_unavailable",
        "child_routing_unavailable",
        "assignment_failed",
        "context_hydration_failed",
        "context_delivery_failed",
        "ready_commit_failed",
        "ready_read_failed",
        "direct_activation_failed",
    }
)

PREFLIGHT_FAILURE_EXCEPTION_CATEGORIES = frozenset(
    {
        "timeout",
        "validation_error",
        "permission_error",
        "host_error",
        "runtime_error",
        "internal_error",
        "unavailable",
    }
)

PREFLIGHT_PROVIDER_STAGES = frozenset(
    {
        "combined",
        "planner",
        "recruiter",
        "hiring",
        "critic",
        "selector",
        "unknown",
    }
)

_DEFAULT_REASON_BY_STAGE = {
    "lifecycle": "preflight_lifecycle_failed",
    "resident_binding": "resident_binding_failed",
    "routing_snapshot": "routing_snapshot_failed",
    "route_request": "route_request_failed",
    "routing": "routing_failed",
    "assignment": "assignment_failed",
    "context_hydration": "context_hydration_failed",
    "context_delivery": "context_delivery_failed",
    "ready_commit": "ready_commit_failed",
    "ready_read": "ready_read_failed",
    "direct_activation": "direct_activation_failed",
}


def default_preflight_failure_reason(stage: str) -> str:
    """Return the fixed failure reason associated with one allowlisted stage."""

    normalized = str(stage or "").strip().casefold()
    if normalized not in PREFLIGHT_FAILURE_STAGES:
        raise ValueError("preflight failure stage is not allowlisted")
    return _DEFAULT_REASON_BY_STAGE[normalized]


def preflight_exception_category(error: BaseException) -> str:
    """Classify an exception without retaining its message or arguments."""

    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, (ValueError, TypeError)):
        return "validation_error"
    if isinstance(error, PermissionError):
        return "permission_error"
    if isinstance(error, OSError):
        return "host_error"
    if isinstance(error, RuntimeError):
        return "runtime_error"
    return "internal_error"


def preflight_routing_failure_reason(routing: Mapping[str, Any]) -> str:
    """Derive one safe reason from fixed routing status/source values."""

    status = str(routing.get("status") or "").strip().casefold()
    source = str(routing.get("source") or "").strip().casefold()
    if status == "inference_unavailable":
        return "workforce_provider_unavailable"
    if status == "inference_invalid" or source in {
        "inference_failure",
        "workforce_inference_failure",
    }:
        return "workforce_inference_failed"
    if status == "child_budget_abstained" or source == "child_budget_policy":
        return "child_routing_unavailable"
    if not any(
        str(item or "").strip()
        for item in routing.get("selected_ids", ())
        if not isinstance(item, (dict, list, tuple, set))
    ):
        return "substantive_specialist_unavailable"
    return "routing_failed"


def project_preflight_provider_attempts(value: object) -> list[dict[str, Any]] | None:
    """Project model attempts while preserving only their allowlisted stage."""

    from agency_runtime.core.selector.receipt_projection import (
        project_model_receipt_attempts,
    )

    projected = project_model_receipt_attempts(value)
    if projected is None:
        return None
    raw = list(value) if isinstance(value, (list, tuple)) else []
    if len(raw) != len(projected):
        return None
    result: list[dict[str, Any]] = []
    for source, attempt in zip(raw, projected, strict=True):
        if not isinstance(source, Mapping):
            return None
        stage = str(source.get("stage") or "unknown").strip().casefold()
        if stage not in PREFLIGHT_PROVIDER_STAGES:
            stage = "unknown"
        result.append({"stage": stage, **attempt})
    return result


def project_preflight_failure_receipt(value: object) -> dict[str, Any] | None:
    """Validate the complete durable failure receipt contract."""

    if not isinstance(value, Mapping):
        return None
    if set(value) != {
        "schema_version",
        "stage",
        "reason_code",
        "exception_category",
        "provider_attempts",
    }:
        return None
    if value.get("schema_version") != PREFLIGHT_FAILURE_RECEIPT_SCHEMA:
        return None
    stage = str(value.get("stage") or "").strip().casefold()
    reason_code = str(value.get("reason_code") or "").strip().casefold()
    exception_category = str(value.get("exception_category") or "").strip().casefold()
    if (
        stage not in PREFLIGHT_FAILURE_STAGES
        or reason_code not in PREFLIGHT_FAILURE_REASONS
        or exception_category not in PREFLIGHT_FAILURE_EXCEPTION_CATEGORIES
    ):
        return None
    provider_attempts = project_preflight_provider_attempts(value.get("provider_attempts"))
    if provider_attempts is None:
        return None
    return {
        "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
        "stage": stage,
        "reason_code": reason_code,
        "exception_category": exception_category,
        "provider_attempts": provider_attempts,
    }


def default_preflight_failure_receipt() -> dict[str, Any]:
    """Return a content-free fallback for legacy direct cleanup callers."""

    return {
        "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
        "stage": "lifecycle",
        "reason_code": "preflight_lifecycle_failed",
        "exception_category": "unavailable",
        "provider_attempts": [],
    }


__all__ = [
    "MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES",
    "PREFLIGHT_FAILURE_EXCEPTION_CATEGORIES",
    "PREFLIGHT_FAILURE_REASONS",
    "PREFLIGHT_FAILURE_RECEIPT_SCHEMA",
    "PREFLIGHT_FAILURE_STAGES",
    "default_preflight_failure_reason",
    "default_preflight_failure_receipt",
    "preflight_exception_category",
    "preflight_routing_failure_reason",
    "project_preflight_failure_receipt",
    "project_preflight_provider_attempts",
]
