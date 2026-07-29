"""Bounded, content-free projections for routing and search receipts."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

RECEIPT_DESCRIPTION_BYTES = 4096
ROUTING_RECEIPT_VERSION = 1

_MAX_IDS = 16
_MAX_HIRING_EVENTS = 16
_MAX_PROVIDER_ATTEMPTS = 16
_MAX_REJECTION_SAMPLES = 32
_MAX_REASON_COUNTS = 32
_MAX_CODES = 24
_MAX_COUNT = 1_000_000
_MAX_IDENTITY_CHARS = 128
_MAX_CODE_CHARS = 96
_CODE = re.compile(r"^[a-z0-9][a-z0-9_.:+-]{0,95}$")
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SECRET_PREFIXES = (
    "bearer",
    "ghp_",
    "github_pat_",
    "sk-",
    "sk_",
)
_SENSITIVE_MARKERS = ("credential", "password", "secret", "token")


def bounded_receipt_text(value: object, *, maximum_bytes: int) -> str:
    """Return UTF-8 text truncated only at a complete code-point boundary."""

    text = value if isinstance(value, str) else str(value or "")
    encoded = text.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return text
    return encoded[:maximum_bytes].decode("utf-8", errors="ignore")


def _bounded_count(value: object, *, maximum: int = _MAX_COUNT) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(parsed, maximum))


def _code(value: object) -> str:
    normalized = str(value or "").strip().casefold()[:_MAX_CODE_CHARS]
    return normalized if _CODE.fullmatch(normalized) is not None else ""


def _reason_family(value: object) -> str:
    """Return a stable reason code without embedding another identity."""

    code = _code(value)
    return code.split(":", 1)[0] if code else ""


def _identity(value: object) -> str:
    """Keep a routing identity or replace hostile metadata with a one-way digest."""

    normalized = str(value or "").strip()[:_MAX_IDENTITY_CHARS]
    lowered = normalized.casefold()
    unsafe = (
        not normalized
        or _IDENTITY.fullmatch(normalized) is None
        or any(lowered.startswith(prefix) for prefix in _SECRET_PREFIXES)
        or any(marker in lowered for marker in _SENSITIVE_MARKERS)
        or "=" in normalized
        or "?" in normalized
        or "#" in normalized
    )
    if not normalized:
        return ""
    if unsafe:
        digest = sha256(str(value).encode("utf-8", errors="surrogatepass")).hexdigest()
        return f"sha256:{digest}"
    return normalized


def _ids(value: object, *, limit: int = _MAX_IDS) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        identity = _identity(item)
        if identity and identity not in result:
            result.append(identity)
            if len(result) >= limit:
                break
    return result


def _codes(value: object, *, limit: int = _MAX_CODES) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    for item in value:
        code = _code(item)
        if code and code not in result:
            result.append(code)
            if len(result) >= limit:
                break
    return result


def _provider_attempts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    attempts: list[dict[str, Any]] = []
    for ordinal, item in enumerate(value[:_MAX_PROVIDER_ATTEMPTS], start=1):
        if not isinstance(item, Mapping):
            continue
        attempts.append(
            {
                "ordinal": ordinal,
                "provider_name": _identity(item.get("provider_name")) or "unavailable",
                "provider_type": _code(item.get("provider_type")) or "unknown",
                "requested_model": _identity(item.get("requested_model")),
                "model_group": _identity(item.get("model_group")),
                "status": _code(item.get("status")) or "unknown",
                "reason_code": _reason_family(item.get("reason"))
                or _reason_family(item.get("reason_code")),
            }
        )
    return attempts


def project_model_receipt_attempts(value: object) -> list[dict[str, Any]] | None:
    """Project bounded provider attempts needed for atomic model receipts."""

    if value is None:
        return []
    if not isinstance(value, (list, tuple)) or len(value) > _MAX_PROVIDER_ATTEMPTS:
        return None
    attempts: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            return None
        attempts.append(
            {
                "provider_name": _identity(item.get("provider_name")) or "unavailable",
                "provider_type": _code(item.get("provider_type")) or "unknown",
                "requested_model": _identity(item.get("requested_model")),
                "model_group": _identity(item.get("model_group")),
                "actual_model": _identity(item.get("actual_model")),
                "model_receipt_source": _code(item.get("model_receipt_source")) or "unavailable",
                "status": _code(item.get("status")) or "unknown",
                "reason_code": _reason_family(item.get("reason_code"))
                or _reason_family(item.get("reason")),
            }
        )
    return attempts


def _hiring(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, (list, tuple)) else []
    events: list[dict[str, Any]] = []
    for item in raw[:_MAX_HIRING_EVENTS]:
        if not isinstance(item, Mapping):
            continue
        unit_id = _identity(item.get("unit_id"))
        status = _code(item.get("status"))
        if not unit_id or not status:
            continue
        events.append(
            {
                "unit_id": unit_id,
                "status": status,
                "reason_codes": _codes(item.get("reason_codes")),
                "case_id": _identity(item.get("case_id")),
                "worker": _identity(item.get("worker")),
                "version": _identity(item.get("version")),
                "calls_used": _bounded_count(item.get("calls_used"), maximum=8),
            }
        )
    attempted_count = sum(item["status"] != "not_attempted" for item in events)
    workforce_changes = sum(item["status"] in {"amended", "hired"} for item in events)
    if not attempted_count:
        outcome = "no_attempt"
    elif workforce_changes == attempted_count:
        outcome = "changed"
    elif workforce_changes:
        outcome = "mixed"
    else:
        outcome = "declined"
    return {
        "outcome": outcome,
        "events": events,
        "attempted_count": attempted_count,
        "workforce_changes": workforce_changes,
        "calls_used": min(sum(item["calls_used"] for item in events), 128),
        "truncated": len(raw) > len(events),
    }


def _retrieval(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    return {
        "mode": _code(raw.get("mode")) or "unavailable",
        "full_roster_count": _bounded_count(raw.get("full_roster_count")),
        "candidate_union_count": _bounded_count(raw.get("candidate_union_count")),
        "lexical_count": _bounded_count(raw.get("lexical_count")),
        "semantic_count": _bounded_count(raw.get("semantic_count")),
        "hard_negative_count": _bounded_count(raw.get("hard_negative_count")),
    }


def _rejections(value: object, *, limit: int = _MAX_REJECTION_SAMPLES) -> list[dict[str, str]]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        slug = _identity(item.get("slug"))
        reason_code = _code(item.get("reason")) or _code(item.get("reason_code"))
        if slug and reason_code:
            result.append({"slug": slug, "reason_code": reason_code})
            if len(result) >= limit:
                break
    return result


def _reason_counts(value: object) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    if isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            code = _reason_family(item.get("reason")) or _reason_family(item.get("reason_code"))
            if code:
                counts[code] += 1
    return [
        {"reason_code": code, "count": min(count, _MAX_COUNT)}
        for code, count in sorted(counts.items())[:_MAX_REASON_COUNTS]
    ]


def _normalize_reason_counts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    merged: Counter[str] = Counter()
    for item in value:
        if not isinstance(item, Mapping):
            continue
        code = _reason_family(item.get("reason_code"))
        count = _bounded_count(item.get("count"))
        if code and count:
            merged[code] += count
    return [
        {"reason_code": code, "count": min(count, _MAX_COUNT)}
        for code, count in sorted(merged.items())[:_MAX_REASON_COUNTS]
    ]


def _compatibility(value: object) -> dict[str, Any]:
    raw = value if isinstance(value, Mapping) else {}
    raw_pairs = raw.get("separate_context_pairs")
    pairs: list[list[str]] = []
    if isinstance(raw_pairs, (list, tuple)):
        for item in raw_pairs:
            pair = _ids(item, limit=2)
            if len(pair) == 2 and pair not in pairs:
                pairs.append(pair)
                if len(pairs) >= _MAX_REJECTION_SAMPLES:
                    break
    raw_rejected = raw.get("rejected", raw.get("rejections", []))
    rejections = _rejections(raw_rejected)
    rejected_total = len(raw_rejected) if isinstance(raw_rejected, (list, tuple)) else 0
    return {
        "contract_version": _bounded_count(raw.get("contract_version"), maximum=1_000),
        "selection_limit": _bounded_count(raw.get("selection_limit"), maximum=_MAX_IDS),
        "requested_ids": _ids(raw.get("requested_ids")),
        "selected_ids": _ids(raw.get("selected_ids")),
        "selected_root_ids": _ids(raw.get("selected_root_ids")),
        "added_requirements": _ids(raw.get("added_requirements")),
        "overflow_review_ids": _ids(raw.get("overflow_review_ids")),
        "rejected_count": _bounded_count(raw.get("rejected_count", rejected_total)),
        "rejections": rejections,
        "rejection_reason_counts": _reason_counts(raw_rejected),
        "separate_context_pairs": pairs,
        "compatible": raw.get("compatible") is True,
    }


def _eligibility(value: object, retrieval: Mapping[str, Any]) -> dict[str, Any]:
    raw = value if isinstance(value, (list, tuple)) else []
    rejected_count = len(raw)
    samples = _rejections(raw)
    eligible_count = _bounded_count(retrieval.get("full_roster_count"))
    return {
        "eligible_count": eligible_count,
        "rejected_count": min(rejected_count, _MAX_COUNT),
        "evaluated_count": min(eligible_count + rejected_count, _MAX_COUNT),
        "rejections": samples,
        "rejection_reason_counts": _reason_counts(raw),
        "sample_truncated": rejected_count > len(samples),
    }


def _routing_reason_codes(
    routing: Mapping[str, Any],
    *,
    inference_mode: str,
    compatibility: Mapping[str, Any],
    eligibility: Mapping[str, Any],
) -> list[str]:
    codes: list[str] = []

    def append(code: str) -> None:
        if code and code not in codes and len(codes) < _MAX_CODES:
            codes.append(code)

    status = _code(routing.get("status"))
    turn_kind = _code(routing.get("turn_kind"))
    append(f"turn_kind:{turn_kind}" if turn_kind else "")
    append(f"routing_status:{status}" if status else "")
    append(f"inference_mode:{inference_mode}" if inference_mode else "")
    for row in compatibility.get("rejection_reason_counts", []):
        if isinstance(row, Mapping):
            family = _reason_family(row.get("reason_code"))
            append(f"compatibility:{family}" if family else "")
    for row in eligibility.get("rejection_reason_counts", []):
        if isinstance(row, Mapping):
            family = _reason_family(row.get("reason_code"))
            append(f"eligibility:{family}" if family else "")
    shadows = routing.get("disabled_candidate_shadows")
    if isinstance(shadows, (list, tuple)):
        for shadow in shadows[:4]:
            if isinstance(shadow, Mapping):
                agent_id = _code(shadow.get("agent_id"))
                append(f"disabled_candidate:{agent_id}" if agent_id else "")
    hiring = _hiring(routing.get("hiring_events"))
    for event in hiring["events"]:
        for reason in event["reason_codes"]:
            append(f"hiring:{_reason_family(reason)}")
    return codes


def _routing_effect_codes(
    routing: Mapping[str, Any],
    *,
    inference_mode: str,
    compatibility: Mapping[str, Any],
    eligibility: Mapping[str, Any],
) -> list[str]:
    codes: list[str] = []

    def append(code: str, condition: bool = True) -> None:
        if condition and code not in codes and len(codes) < _MAX_CODES:
            codes.append(code)

    selected = _ids(routing.get("selected_ids"))
    work_units = routing.get("work_units")
    append("inference_attempted", routing.get("inference_attempted") is True)
    append("inference_degraded", inference_mode == "degraded")
    append("routing_reused", routing.get("continuation_reused") is True)
    append(
        "continuation_resolution_required",
        routing.get("continuation_resolution_required") is True,
    )
    append("eligibility_exclusions_applied", bool(eligibility.get("rejected_count")))
    append("compatibility_constraints_applied", bool(compatibility.get("contract_version")))
    append("compatibility_rejections_applied", bool(compatibility.get("rejected_count")))
    append("specialists_selected", bool(selected))
    append("selection_abstained", not selected)
    append("policy_fallback_applied", routing.get("fallback_applied") is True)
    append(
        "disabled_specialist_left_unselected",
        bool(routing.get("disabled_candidate_shadows")),
    )
    append(
        "delegation_plan_prepared",
        isinstance(work_units, Mapping) and work_units.get("delegate") is True,
    )
    hiring = _hiring(routing.get("hiring_events"))
    statuses = {item["status"] for item in hiring["events"]}
    append("hiring_attempted", bool(hiring["attempted_count"]))
    append("workforce_changed", bool(hiring["workforce_changes"]))
    append(
        "hiring_not_attempted",
        hiring["outcome"] == "no_attempt" or "not_attempted" in statuses,
    )
    append("hiring_declined", bool(statuses - {"amended", "hired", "not_attempted"}))
    return codes


def routing_projection_digest(value: object) -> str:
    """Return the canonical digest shared by routing and Store projections."""

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _receipt_digest(value: object) -> str:
    """Preserve the private selector digest seam for internal callers."""

    return routing_projection_digest(value)


def project_durable_routing_receipt(routing: Mapping[str, Any]) -> dict[str, Any]:
    """Project one routing outcome into bounded metadata-only durable evidence."""

    continuation_reused = routing.get("continuation_reused") is True
    inference_mode = _code(routing.get("inference_mode")) or "unavailable"
    attempts = _provider_attempts(routing.get("provider_attempts"))
    origin_receipt_digest = ""
    if continuation_reused:
        inference_mode = "durable_reuse"
        attempts = []
        origin = normalize_durable_routing_receipt(routing.get("routing_receipt"))
        if origin is not None:
            origin_receipt_digest = _receipt_digest(origin)
    retrieval = _retrieval(routing.get("retrieval"))
    compatibility = _compatibility(routing.get("compatibility"))
    eligibility = _eligibility(routing.get("eligibility_rejections"), retrieval)
    receipt = {
        "receipt_version": ROUTING_RECEIPT_VERSION,
        "inference": {
            "configured": routing.get("inference_configured") is True,
            "required": False if continuation_reused else routing.get("inference_required") is True,
            "attempted": False
            if continuation_reused
            else routing.get("inference_attempted") is True,
            "mode": inference_mode,
            "provider_attempts": attempts,
        },
        "retrieval": retrieval,
        "compatibility": compatibility,
        "eligibility": eligibility,
    }
    receipt["reason_codes"] = _routing_reason_codes(
        routing,
        inference_mode=inference_mode,
        compatibility=compatibility,
        eligibility=eligibility,
    )
    receipt["effect_codes"] = _routing_effect_codes(
        routing,
        inference_mode=inference_mode,
        compatibility=compatibility,
        eligibility=eligibility,
    )
    receipt["hiring"] = _hiring(routing.get("hiring_events"))
    if origin_receipt_digest:
        receipt["origin_receipt_digest"] = origin_receipt_digest
    return receipt


def normalize_durable_routing_receipt(value: object) -> dict[str, Any] | None:
    """Validate and canonicalize one stored routing receipt."""

    if not isinstance(value, Mapping) or value.get("receipt_version") != ROUTING_RECEIPT_VERSION:
        return None
    raw_inference = value.get("inference")
    raw_retrieval = value.get("retrieval")
    raw_compatibility = value.get("compatibility")
    raw_eligibility = value.get("eligibility")
    if not all(
        isinstance(item, Mapping)
        for item in (raw_inference, raw_retrieval, raw_compatibility, raw_eligibility)
    ):
        return None
    inference = {
        "configured": raw_inference.get("configured") is True,
        "required": raw_inference.get("required") is True,
        "attempted": raw_inference.get("attempted") is True,
        "mode": _code(raw_inference.get("mode")) or "unavailable",
        "provider_attempts": _provider_attempts(raw_inference.get("provider_attempts")),
    }
    retrieval = _retrieval(raw_retrieval)
    compatibility = _compatibility(raw_compatibility)
    normalized_compatibility_counts = _normalize_reason_counts(
        raw_compatibility.get("rejection_reason_counts")
    )
    if normalized_compatibility_counts:
        compatibility["rejection_reason_counts"] = normalized_compatibility_counts
    raw_eligibility_rejections = raw_eligibility.get("rejections")
    eligibility_rejections = _rejections(raw_eligibility_rejections)
    raw_rejected_count = _bounded_count(raw_eligibility.get("rejected_count"))
    eligible_count = _bounded_count(raw_eligibility.get("eligible_count"))
    eligibility = {
        "eligible_count": eligible_count,
        "rejected_count": raw_rejected_count,
        "evaluated_count": min(
            _bounded_count(
                raw_eligibility.get("evaluated_count", eligible_count + raw_rejected_count)
            ),
            _MAX_COUNT,
        ),
        "rejections": eligibility_rejections,
        "rejection_reason_counts": _normalize_reason_counts(
            raw_eligibility.get("rejection_reason_counts")
        )
        or _reason_counts(eligibility_rejections),
        "sample_truncated": raw_eligibility.get("sample_truncated") is True,
    }
    normalized = {
        "receipt_version": ROUTING_RECEIPT_VERSION,
        "inference": inference,
        "retrieval": retrieval,
        "compatibility": compatibility,
        "eligibility": eligibility,
        "reason_codes": _codes(value.get("reason_codes")),
        "effect_codes": _codes(value.get("effect_codes")),
    }
    raw_hiring = value.get("hiring")
    normalized["hiring"] = _hiring(
        raw_hiring.get("events") if isinstance(raw_hiring, Mapping) else None
    )
    origin_digest = str(value.get("origin_receipt_digest") or "").strip().casefold()
    if _DIGEST.fullmatch(origin_digest) is not None:
        normalized["origin_receipt_digest"] = origin_digest
    return normalized


__all__ = [
    "RECEIPT_DESCRIPTION_BYTES",
    "ROUTING_RECEIPT_VERSION",
    "bounded_receipt_text",
    "normalize_durable_routing_receipt",
    "project_durable_routing_receipt",
    "routing_projection_digest",
]
