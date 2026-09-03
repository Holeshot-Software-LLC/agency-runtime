"""Bounded, content-free diagnostics for terminal preflight failures."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from agency_runtime.core.workforce.plan_policy import PLAN_VALIDATION_REASON_CODES

PREFLIGHT_FAILURE_RECEIPT_SCHEMA = "agency.preflight.failure.v3"
MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES = 32 * 1024
MAX_PREFLIGHT_FAILURE_REASON_CODES = 32
MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES = 4 * 1024
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{1,95}$")
_HIRING_EVENT_STATUSES = frozenset(
    {
        "abstained",
        "amended",
        "hired",
        "not_attempted",
        "pending_approval",
        "rejected",
    }
)

PREFLIGHT_FAILURE_INVARIANTS = frozenset({"", "native_plan_scope_invalid"})

_RECRUITER_VALIDATION_REASON_CODES = frozenset(
    {
        "recruiter_candidate_classification_conflict",
        "recruiter_candidate_classification_invalid",
        "recruiter_candidate_forbidden_evidence_missing",
        "recruiter_candidate_id_unknown",
        "recruiter_candidate_negative_evidence_invalid",
        "recruiter_candidate_positive_evidence_invalid",
        "recruiter_candidate_positive_evidence_missing",
        "recruiter_candidate_row_shape_invalid",
        "recruiter_candidate_score_invalid",
        "recruiter_repair_row_outside_failed_set",
        "recruiter_response_shape_invalid",
        "recruiter_unit_row_shape_invalid",
    }
)
_CRITIC_VALIDATION_REASON_CODES = frozenset(
    {
        "critic_approval_invalid",
        "critic_approval_reasons_present",
        "critic_reason_code_invalid",
        "critic_reason_codes_invalid",
        "critic_rejection_reason_missing",
        "critic_response_shape_invalid",
    }
)


class PreflightInvariantError(ValueError):
    """Carry one fixed invariant identity without retaining rejected content."""

    def __init__(self, invariant_code: str) -> None:
        normalized = str(invariant_code or "").strip().casefold()
        if not normalized or normalized not in PREFLIGHT_FAILURE_INVARIANTS:
            raise ValueError("preflight invariant code is not allowlisted")
        self.invariant_code = normalized
        super().__init__("preflight invariant failed")


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
        "recall_embedding",
        "recall_reranker",
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


def preflight_invariant_code(error: BaseException) -> str:
    """Project a fixed invariant identity without inspecting exception text."""

    code = getattr(error, "invariant_code", "")
    normalized = str(code or "").strip().casefold()
    return normalized if normalized in PREFLIGHT_FAILURE_INVARIANTS else ""


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
    if status == "inference_abstained":
        return "substantive_specialist_unavailable"
    if not any(
        str(item or "").strip()
        for item in routing.get("selected_ids", ())
        if not isinstance(item, (dict, list, tuple, set))
    ):
        return "substantive_specialist_unavailable"
    return "routing_failed"


def _project_validation_reason_codes(value: object, *, stage: str) -> list[str]:
    """Project only bounded, runtime-owned validation codes for one stage."""

    if not isinstance(value, (list, tuple)) or len(value) > MAX_PREFLIGHT_FAILURE_REASON_CODES:
        return []
    if stage in {"combined", "planner"}:
        allowed = PLAN_VALIDATION_REASON_CODES
    elif stage == "recruiter":
        allowed = _RECRUITER_VALIDATION_REASON_CODES
    elif stage == "critic":
        allowed = _CRITIC_VALIDATION_REASON_CODES
    else:
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return []
        code = item.strip().casefold()
        if code not in allowed:
            return []
        if code not in result:
            result.append(code)
    return result


def project_preflight_provider_attempts(value: object) -> list[dict[str, Any]] | None:
    """Project model attempts while preserving only their allowlisted stage."""

    from agency_runtime.core.selector.receipt_projection import (
        project_model_receipt_attempts,
        project_nomination_failures,
        project_reply_truncation,
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
        entry: dict[str, Any] = {"stage": stage, **attempt}
        # A rejected recruiter attempt is the most common terminal failure, and
        # its reason_code alone ("provider_response_contract_invalid") does not
        # say which units failed or why. The per-unit codes are an allowlisted
        # vocabulary, not model text, so the receipt can carry them and explain
        # itself without a live re-run.
        nomination_failures = project_nomination_failures(
            source.get("validation_failures", source.get("validation_detail"))
        )
        if nomination_failures:
            entry["validation_failures"] = nomination_failures
        validation_reason_codes = _project_validation_reason_codes(
            source.get("validation_reason_codes"),
            stage=stage,
        )
        if validation_reason_codes:
            entry["validation_reason_codes"] = validation_reason_codes
        # AR-385: a rejected attempt whose reply was cut at the completion cap
        # says so with the transport's own counts, so the receipt is never
        # blank on the most common silent recruiter failure.
        truncation = project_reply_truncation(source.get("truncation", source))
        if truncation is not None:
            entry["truncation"] = truncation
        result.append(entry)
    return result


def preflight_eligibility_reason_codes(routing: Mapping[str, Any]) -> list[str]:
    """Project why candidates were filtered out before the recruiter saw them.

    When nearly the whole roster is ineligible the recruiter cannot form a team
    however well it nominates, so a terminal staffing failure is unreadable
    without this. Only the distinct reason codes are kept -- never the rejected
    slugs, which would grow with the roster and say nothing extra.
    """

    raw = routing.get("eligibility_rejections")
    rejections = raw if isinstance(raw, (list, tuple)) else ()
    codes: list[object] = []
    for item in rejections:
        if not isinstance(item, Mapping):
            continue
        code = item.get("reason")
        if code not in codes:
            codes.append(code)
        if len(codes) >= MAX_PREFLIGHT_FAILURE_REASON_CODES:
            break
    projected = project_preflight_reason_codes(codes[:MAX_PREFLIGHT_FAILURE_REASON_CODES])
    return [] if projected is None else projected


def project_preflight_reason_codes(value: object) -> list[str] | None:
    """Validate one bounded content-free reason-code list."""

    if not isinstance(value, (list, tuple)) or len(value) > MAX_PREFLIGHT_FAILURE_REASON_CODES:
        return None
    result: list[str] = []
    for item in value:
        if isinstance(item, (Mapping, list, tuple, set)):
            return None
        code = str(item or "").strip().casefold()
        if _REASON_CODE.fullmatch(code) is None:
            return None
        if code not in result:
            result.append(code)
    return result


def preflight_staffing_reason_codes(routing: Mapping[str, Any]) -> list[str]:
    """Project verifier codes from a routing result without retaining detail."""

    staffing = routing.get("workforce_staffing")
    raw_reasons = staffing.get("abstention_reasons") if isinstance(staffing, Mapping) else None
    reasons = raw_reasons if isinstance(raw_reasons, (list, tuple)) else ()
    codes = [item.get("code") for item in reasons if isinstance(item, Mapping)]
    projected = project_preflight_reason_codes(codes[:MAX_PREFLIGHT_FAILURE_REASON_CODES])
    return [] if projected is None else projected


def preflight_hiring_reason_codes(routing: Mapping[str, Any]) -> list[str]:
    """Project bounded contractor-hiring state from a routing result without content.

    A successful deferred hire has no reason codes by design. If later
    whole-team restaffing fails, atomic preflight rolls that pending hire back;
    retaining only ``reason_codes`` therefore made "hire ran and reached a
    terminal status" indistinguishable from "hiring never ran". Preserve the
    closed event status and whether inference was consumed alongside any
    existing reason codes. No worker identity, notification, or model content
    crosses this failure boundary.
    """

    raw_events = routing.get("hiring_events")
    events = raw_events if isinstance(raw_events, (list, tuple)) else ()
    codes: list[object] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        status = str(event.get("status") or "").strip().casefold()
        if status in _HIRING_EVENT_STATUSES:
            codes.append(f"hiring_status_{status}")
        calls_used = event.get("calls_used")
        if not isinstance(calls_used, bool) and isinstance(calls_used, int) and calls_used > 0:
            codes.append("hiring_inference_attempted")
        raw_codes = event.get("reason_codes")
        if not isinstance(raw_codes, (list, tuple)):
            continue
        codes.extend(raw_codes)
        if len(codes) >= MAX_PREFLIGHT_FAILURE_REASON_CODES:
            break
    projected = project_preflight_reason_codes(codes[:MAX_PREFLIGHT_FAILURE_REASON_CODES])
    return [] if projected is None else projected


def project_preflight_failure_receipt(value: object) -> dict[str, Any] | None:
    """Validate the complete durable failure receipt contract."""

    if not isinstance(value, Mapping):
        return None
    if set(value) != {
        "schema_version",
        "stage",
        "reason_code",
        "invariant_code",
        "exception_category",
        "provider_attempts",
        "staffing_reason_codes",
        "hiring_reason_codes",
        "eligibility_reason_codes",
    }:
        return None
    if value.get("schema_version") != PREFLIGHT_FAILURE_RECEIPT_SCHEMA:
        return None
    stage = str(value.get("stage") or "").strip().casefold()
    reason_code = str(value.get("reason_code") or "").strip().casefold()
    invariant_code = str(value.get("invariant_code") or "").strip().casefold()
    exception_category = str(value.get("exception_category") or "").strip().casefold()
    if (
        stage not in PREFLIGHT_FAILURE_STAGES
        or reason_code not in PREFLIGHT_FAILURE_REASONS
        or invariant_code not in PREFLIGHT_FAILURE_INVARIANTS
        or exception_category not in PREFLIGHT_FAILURE_EXCEPTION_CATEGORIES
    ):
        return None
    provider_attempts = project_preflight_provider_attempts(value.get("provider_attempts"))
    staffing_reason_codes = project_preflight_reason_codes(value.get("staffing_reason_codes"))
    hiring_reason_codes = project_preflight_reason_codes(value.get("hiring_reason_codes"))
    eligibility_reason_codes = project_preflight_reason_codes(value.get("eligibility_reason_codes"))
    if (
        provider_attempts is None
        or staffing_reason_codes is None
        or hiring_reason_codes is None
        or eligibility_reason_codes is None
    ):
        return None
    return {
        "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
        "stage": stage,
        "reason_code": reason_code,
        "invariant_code": invariant_code,
        "exception_category": exception_category,
        "provider_attempts": provider_attempts,
        "staffing_reason_codes": staffing_reason_codes,
        "hiring_reason_codes": hiring_reason_codes,
        "eligibility_reason_codes": eligibility_reason_codes,
    }


def default_preflight_failure_receipt() -> dict[str, Any]:
    """Return a content-free fallback for legacy direct cleanup callers."""

    return {
        "schema_version": PREFLIGHT_FAILURE_RECEIPT_SCHEMA,
        "stage": "lifecycle",
        "reason_code": "preflight_lifecycle_failed",
        "invariant_code": "",
        "exception_category": "unavailable",
        "provider_attempts": [],
        "staffing_reason_codes": [],
        "hiring_reason_codes": [],
        "eligibility_reason_codes": [],
    }


__all__ = [
    "MAX_PREFLIGHT_FAILURE_PROVIDER_ATTEMPTS_BYTES",
    "MAX_PREFLIGHT_FAILURE_REASON_CODES",
    "MAX_PREFLIGHT_FAILURE_REASON_CODES_BYTES",
    "PREFLIGHT_FAILURE_EXCEPTION_CATEGORIES",
    "PREFLIGHT_FAILURE_INVARIANTS",
    "PREFLIGHT_FAILURE_REASONS",
    "PREFLIGHT_FAILURE_RECEIPT_SCHEMA",
    "PREFLIGHT_FAILURE_STAGES",
    "PreflightInvariantError",
    "default_preflight_failure_reason",
    "default_preflight_failure_receipt",
    "preflight_eligibility_reason_codes",
    "preflight_exception_category",
    "preflight_hiring_reason_codes",
    "preflight_invariant_code",
    "preflight_routing_failure_reason",
    "preflight_staffing_reason_codes",
    "project_preflight_failure_receipt",
    "project_preflight_provider_attempts",
    "project_preflight_reason_codes",
]
