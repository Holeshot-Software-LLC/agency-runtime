"""Bounded, content-free projections for routing and search receipts."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from agency_runtime.core.workforce.staffing_verifier import (
    REQUIREMENT_AXES as _REQUIREMENT_AXES,
)

RECEIPT_DESCRIPTION_BYTES = 4096
ROUTING_RECEIPT_VERSION = 1

_MAX_IDS = 16
_MAX_HIRING_EVENTS = 16
_MAX_STAFFING_UNITS = 16
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
_NOMINATION_UNIT_ID = re.compile(r"^unit-[a-z0-9][a-z0-9-]{0,62}$")
# Ranked agents are recorded to diagnose a ranking, so a malformed value fails
# the projection closed rather than becoming an opaque digest nobody can act on.
_NOMINATION_AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_NOMINATION_FAILURE_CODES = frozenset(
    {
        "candidate_outside_detail_cards",
        "gap_with_safe_team",
        "invalid_candidate",
        "invalid_decision",
        "invalid_ranking",
        "missing_work_unit",
        "staff_without_safe_team",
    }
)
_NOMINATION_FAILURE_PREFIX = "workforce nomination failures: "


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


def _parse_nomination_detail(value: str) -> list[dict[str, Any]] | None:
    """Split the wire detail into rows, or None when it is malformed.

    Each row is
    ``unit=code[:axis][~agent~agent][!required:executable:max][|reason]``.
    The axis, counts, and reason are closed content-free values and the agents
    are roster identities, so none carries request or model-authored prose.
    """

    parsed: list[dict[str, Any]] = []
    for item in value.removeprefix(_NOMINATION_FAILURE_PREFIX).split(","):
        unit_id, separator, remainder = item.partition("=")
        if not separator:
            return None
        remainder, _, ineligibility = remainder.partition("|")
        remainder, counts_separator, counts_text = remainder.partition("!")
        remainder, _, ranked_text = remainder.partition("~")
        reason_code, _, axis = remainder.partition(":")
        row: dict[str, Any] = {"unit_id": unit_id, "reason_code": reason_code}
        if axis:
            row["requirement_axis"] = axis
        if ranked_text:
            row["ranked_agent_ids"] = ranked_text
        if ineligibility:
            row["top_ranked_ineligibility"] = ineligibility
        if counts_separator:
            raw_counts = counts_text.split(":")
            if len(raw_counts) != 3 or any(
                not item.isascii() or not item.isdecimal() for item in raw_counts
            ):
                return None
            required_count, executable_count, maximum_selected = map(int, raw_counts)
            row.update(
                {
                    "required_agent_count": required_count,
                    "ranked_executable_count": executable_count,
                    "maximum_selected_per_unit": maximum_selected,
                }
            )
        parsed.append(row)
    return parsed


def _nomination_ranked_ids(value: object) -> list[str] | None:
    """Normalise the ranked ids, or None when the value is malformed.

    The stored form is the flat delimited string ``project_nomination_failures``
    emits, so this must round-trip through its own output; a nested list would
    push the preflight receipt past its bounded-JSON depth.
    """

    raw = value or ()
    if isinstance(raw, bytes):
        return None
    if isinstance(raw, str):
        raw = raw.split("~") if raw else ()
    elif not isinstance(raw, (list, tuple)):
        return None
    ranked = [str(item or "").strip().casefold() for item in raw]
    if len(ranked) > _MAX_IDS or any(
        _NOMINATION_AGENT_ID.fullmatch(agent_id) is None for agent_id in ranked
    ):
        return None
    return ranked


def _nomination_team_counts(item: Mapping[str, Any], reason_code: str) -> dict[str, int] | None:
    """Return an atomic bounded count triple, or None when it is malformed."""

    count_keys = {
        "required_agent_count",
        "ranked_executable_count",
        "maximum_selected_per_unit",
    }
    present_count_keys = count_keys.intersection(item)
    if not present_count_keys:
        return {}
    if present_count_keys != count_keys or reason_code != "staff_without_safe_team":
        return None
    counts: dict[str, int] = {}
    for key in count_keys:
        value = item[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 16:
            return None
        counts[key] = value
    return counts


def project_nomination_failures(value: object) -> list[dict[str, Any]]:
    """Project only the allowlisted, content-free recruiter failure contract.

    Both the routing receipt and the terminal preflight-failure receipt need
    this answer, and they must agree, so the rule lives here once rather than
    being restated per receipt.
    """

    raw: object = value
    if isinstance(value, str):
        if len(value.encode("utf-8")) > RECEIPT_DESCRIPTION_BYTES or not value.startswith(
            _NOMINATION_FAILURE_PREFIX
        ):
            return []
        parsed = _parse_nomination_detail(value)
        if parsed is None:
            return []
        raw = parsed
    if not isinstance(raw, (list, tuple)) or not 1 <= len(raw) <= _MAX_STAFFING_UNITS:
        return []
    failures: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping) or not {"unit_id", "reason_code"} <= set(item) <= {
            "unit_id",
            "reason_code",
            "requirement_axis",
            "ranked_agent_ids",
            "top_ranked_ineligibility",
            "required_agent_count",
            "ranked_executable_count",
            "maximum_selected_per_unit",
        }:
            return []
        unit_id = str(item.get("unit_id") or "").strip().casefold()
        reason_code = _code(item.get("reason_code"))
        axis = _code(item.get("requirement_axis")) if "requirement_axis" in item else ""
        ranked = _nomination_ranked_ids(item.get("ranked_agent_ids"))
        if ranked is None:
            return []
        unit_id_is_digest = unit_id.startswith("sha256:") and _DIGEST.fullmatch(
            unit_id.removeprefix("sha256:")
        )
        if (
            (_NOMINATION_UNIT_ID.fullmatch(unit_id) is None and not unit_id_is_digest)
            or reason_code not in _NOMINATION_FAILURE_CODES
            or ("requirement_axis" in item and axis not in _REQUIREMENT_AXES)
        ):
            return []
        projected_unit_id = _identity(unit_id)
        failure: dict[str, Any] = {"unit_id": projected_unit_id, "reason_code": reason_code}
        if axis:
            failure["requirement_axis"] = axis
        ineligibility = (
            _code(item.get("top_ranked_ineligibility"))
            if "top_ranked_ineligibility" in item
            else ""
        )
        if "top_ranked_ineligibility" in item and not ineligibility:
            return []
        counts = _nomination_team_counts(item, reason_code)
        if counts is None:
            return []
        if ranked:
            # Flat, not nested. A list here pushes the preflight-failure receipt
            # past its bounded-JSON depth of 4, and one over-deep row makes
            # recent_runtime_activity raise, which reads to every caller as
            # "runtime evidence store is unavailable" and blocks the canary.
            failure["ranked_agent_ids"] = "~".join(ranked)
        if ineligibility:
            failure["top_ranked_ineligibility"] = ineligibility
        failure.update(counts)
        if not projected_unit_id or failure in failures:
            return []
        failures.append(failure)
    return failures


def _provider_attempts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    attempts: list[dict[str, Any]] = []
    for ordinal, item in enumerate(value[:_MAX_PROVIDER_ATTEMPTS], start=1):
        if not isinstance(item, Mapping):
            continue
        attempt = {
            "ordinal": ordinal,
            "provider_name": _identity(item.get("provider_name")) or "unavailable",
            "provider_type": _code(item.get("provider_type")) or "unknown",
            "requested_model": _identity(item.get("requested_model")),
            "model_group": _identity(item.get("model_group")),
            "status": _code(item.get("status")) or "unknown",
            "reason_code": _reason_family(item.get("reason"))
            or _reason_family(item.get("reason_code")),
        }
        validation_failures = project_nomination_failures(
            item.get("validation_failures", item.get("validation_detail"))
        )
        if validation_failures:
            attempt["validation_failures"] = validation_failures
        attempts.append(attempt)
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


def _staffing(routing: Mapping[str, Any]) -> dict[str, Any]:
    """Project inference nominations separately from verifier-safe proposals."""

    raw_proposal = routing.get("workforce_proposal")
    raw_staffing = routing.get("workforce_staffing")
    proposal = raw_proposal if isinstance(raw_proposal, Mapping) else {}
    staffing = raw_staffing if isinstance(raw_staffing, Mapping) else {}
    raw_reasons = staffing.get("abstention_reasons")
    reasons = raw_reasons if isinstance(raw_reasons, (list, tuple)) else []
    by_unit: dict[str, list[str]] = {}
    global_reasons: list[str] = []
    for item in reasons:
        if not isinstance(item, Mapping):
            continue
        code = _code(item.get("code"))
        unit_id = _identity(item.get("unit_id"))
        if not code:
            continue
        target = by_unit.setdefault(unit_id, []) if unit_id else global_reasons
        if code not in target and len(target) < 8:
            target.append(code)

    raw_units = proposal.get("units")
    source_units = raw_units if isinstance(raw_units, (list, tuple)) else []
    units: list[dict[str, Any]] = []
    for item in source_units[:_MAX_STAFFING_UNITS]:
        if not isinstance(item, Mapping):
            continue
        unit_id = _identity(item.get("unit_id"))
        if not unit_id:
            continue
        required = item.get("required")
        acceptable = item.get("acceptable")
        nominated = [
            *(required if isinstance(required, (list, tuple)) else []),
            *(acceptable if isinstance(acceptable, (list, tuple)) else []),
        ]
        proposal_reasons = _codes(item.get("abstention_reasons"), limit=4)
        verifier_reasons = by_unit.get(unit_id, [])
        units.append(
            {
                "unit_id": unit_id,
                "nominated_ids": _ids(nominated, limit=4),
                "proposed_ids": _ids(item.get("selected"), limit=4),
                "reason_codes": _codes([*proposal_reasons, *verifier_reasons], limit=8),
            }
        )
    return {
        "status": _code(staffing.get("status")) or "unavailable",
        "units": units,
        "global_reason_codes": _codes(global_reasons, limit=8),
        "gap_count": sum(not item["proposed_ids"] for item in units),
        "truncated": len(source_units) > len(units),
    }


def _normalize_staffing(value: object) -> dict[str, Any]:
    """Canonicalize an already projected staffing receipt."""

    raw = value if isinstance(value, Mapping) else {}
    raw_units = raw.get("units")
    source_units = raw_units if isinstance(raw_units, (list, tuple)) else []
    units: list[dict[str, Any]] = []
    for item in source_units[:_MAX_STAFFING_UNITS]:
        if not isinstance(item, Mapping):
            continue
        unit_id = _identity(item.get("unit_id"))
        if not unit_id:
            continue
        units.append(
            {
                "unit_id": unit_id,
                "nominated_ids": _ids(item.get("nominated_ids"), limit=4),
                "proposed_ids": _ids(item.get("proposed_ids"), limit=4),
                "reason_codes": _codes(item.get("reason_codes"), limit=8),
            }
        )
    return {
        "status": _code(raw.get("status")) or "unavailable",
        "units": units,
        "global_reason_codes": _codes(raw.get("global_reason_codes"), limit=8),
        "gap_count": sum(not item["proposed_ids"] for item in units),
        "truncated": raw.get("truncated") is True or len(source_units) > len(units),
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


def _eligibility(
    value: object,
    retrieval: Mapping[str, Any],
    *,
    eligible_catalog_count: object = None,
) -> dict[str, Any]:
    raw = value if isinstance(value, (list, tuple)) else []
    rejected_count = len(raw)
    samples = _rejections(raw)
    eligible_count = _bounded_count(
        retrieval.get("full_roster_count")
        if eligible_catalog_count is None
        else eligible_catalog_count
    )
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
    staffing = _staffing(routing)
    for unit in staffing["units"]:
        for reason in unit["reason_codes"]:
            append(f"staffing:{_reason_family(reason)}")
    for reason in staffing["global_reason_codes"]:
        append(f"staffing:{_reason_family(reason)}")
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
    append("inference_attempted", routing.get("inference_attempted") is True)
    append("turn_context_applied", routing.get("turn_context_applied") is True)
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
    eligibility = _eligibility(
        routing.get("eligibility_rejections"),
        retrieval,
        eligible_catalog_count=routing.get("eligible_catalog_count"),
    )
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
    receipt["staffing"] = _staffing(routing)
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
    normalized["staffing"] = _normalize_staffing(value.get("staffing"))
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
    "project_nomination_failures",
    "routing_projection_digest",
]
