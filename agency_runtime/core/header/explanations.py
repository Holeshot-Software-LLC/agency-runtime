"""Human-readable projections of bounded routing evidence codes.

The durable receipt remains the machine-readable source of truth. This module
only controls the six-line response header shown to people.
"""

from __future__ import annotations

from collections.abc import Iterable

_REASON_TEXT = {
    "requested_question_task_or_output": "the request asked for a substantive answer or action",
    "authorization_response": "the request supplied authorization for the active work",
    "question_response": "the request asked a question that needed a new response",
    "continuation_reply_requires_reroute": "the continuation contained new work and was routed again",
    "roster_consideration_required": "the request was substantial enough to consider specialist help",
    "turn_state_missing": "no reusable turn state was available",
    "turn_state_stale": "the earlier turn state was stale",
    "turn_state_corrupt": "the earlier turn state could not be trusted",
    "acknowledgement_cannot_bypass_active_state": "an acknowledgement did not bypass active work",
}

_PREFIX_TEXT = {
    "turn_kind:new_intent": "this was a new request",
    "turn_kind:continuation": "this continued the active request",
    "routing_status:policy_fallback": (
        "no confident specialist match remained, so Agency used its default coordinator policy"
    ),
    "routing_status:token_fallback": (
        "inference did not return a decision, so Agency used deterministic matching"
    ),
    "routing_status:confidence_bypass": "deterministic matching was already confident",
    "routing_status:abstained": "Agency found no defensible specialist match",
    "routing_status:abstained_low_confidence": (
        "Agency rejected a specialist proposal that was not confident enough"
    ),
    "routing_status:degraded": (
        "configured inference was unavailable, so specialist selection stopped"
    ),
    "inference_mode:heuristic": "routing used deterministic matching",
    "inference_mode:inferred": "routing used the configured inference provider",
    "inference_mode:degraded": (
        "the configured inference provider did not produce a valid decision"
    ),
    "inference_mode:durable_reuse": "routing reused verified evidence from this continuing turn",
    "eligibility:missing_capabilities": (
        "some specialists were excluded because this host did not prove their required capabilities"
    ),
    "eligibility:unsupported_tool_platform": (
        "some specialists were excluded because their tools do not support this platform"
    ),
    "eligibility:unsupported_execution_host": (
        "some specialists were excluded because they do not support this agent host"
    ),
    "eligibility:execution_host_unproven": (
        "some specialists were excluded because the execution host was not proven"
    ),
    "compatibility:conflict": "conflicting specialists were kept out of the same context",
    "compatibility:requires": "specialist dependency requirements constrained the final set",
}

_EFFECT_TEXT = {
    "inference_attempted": "Agency attempted inference",
    "inference_degraded": "the unavailable inference provider prevented an inferred selection",
    "routing_reused": "verified routing from this continuing turn was reused",
    "continuation_resolution_required": "the continuation was routed as new work",
    "eligibility_exclusions_applied": "host and tool eligibility exclusions were applied",
    "compatibility_constraints_applied": "compatibility constraints were applied",
    "compatibility_rejections_applied": "incompatible specialists were rejected",
    "specialists_selected": "the best remaining compatible specialists were selected",
    "selection_abstained": "no specialist was selected",
    "policy_fallback_applied": "the default coordinators were used as the safe fallback",
    "disabled_specialist_left_unselected": (
        "a stronger disabled specialist was left out and the enabled fallback was used"
    ),
    "delegation_plan_prepared": "a delegation plan was prepared",
    "specialist_context_loaded": "selected specialist instructions were loaded for this turn",
    "skill_context_loaded": "selected skill instructions were loaded for this turn",
    "model_receipt_recorded": "the responding model was reconciled from runtime evidence",
    "delegated_specialist_executed": "a delegated specialist actually executed",
}


def _fallback_text(code: str) -> str:
    family, separator, value = code.partition(":")
    if family == "disabled_candidate" and separator:
        specialist = value.replace("_", " ").replace("-", " ").strip()
        return f"disabled specialist {specialist} would have ranked higher"
    words = (value if separator else family).replace("_", " ").replace("-", " ").strip()
    if separator:
        label = family.replace("_", " ").replace("-", " ").strip()
        return f"{label} was {words}"
    return words


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).strip().rstrip(".")
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _sentence(values: list[str], *, unavailable: str) -> str:
    if not values:
        return unavailable
    text = "; ".join(values)
    return text[:1].upper() + text[1:] + "."


def humanize_reason_codes(codes: Iterable[str]) -> str:
    """Render authoritative reason codes as one readable header sentence."""

    phrases = _dedupe(
        _REASON_TEXT.get(code) or _PREFIX_TEXT.get(code) or _fallback_text(code) for code in codes
    )
    return _sentence(
        phrases,
        unavailable="Unavailable - no authoritative explanation was recorded for this turn.",
    )


def humanize_effect_codes(codes: Iterable[str]) -> str:
    """Render authoritative effect codes as one readable header sentence."""

    phrases = _dedupe(_EFFECT_TEXT.get(code) or _fallback_text(code) for code in codes)
    return _sentence(
        phrases,
        unavailable="Unavailable - no authoritative routing effect was recorded for this turn.",
    )


__all__ = ["humanize_effect_codes", "humanize_reason_codes"]
