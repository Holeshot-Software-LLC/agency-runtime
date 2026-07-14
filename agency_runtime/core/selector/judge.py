"""Semantic judge facade and deterministic routing fallbacks.

Provider protocols, transport execution, and ordered attempt accounting live in
small sibling modules.  This facade intentionally retains the historical names
used by callers and tests, including dynamic monkeypatch seams.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

# These imports are deliberate facade attributes.  Sibling modules resolve
# them dynamically so downstream monkeypatches keep working after the split.
from agency_runtime.core.bounded_json import safe_load_bounded_json  # noqa: F401
from agency_runtime.core.cli_transport import (  # noqa: F401
    SUPPORTED_CLI_TRANSPORTS,
    invoke_cli_judge,
)
from agency_runtime.core.config import (
    MAX_PROVIDER_CHAIN_ENTRIES,
    AgencyConfig,
    JudgeConfig,
    ProviderEntry,
    _is_loopback_http_url,
    load_config,
)
from agency_runtime.core.http_safety import open_no_redirect  # noqa: F401
from agency_runtime.core.selector import judge_attempts as _attempts
from agency_runtime.core.selector import judge_protocol as _protocol
from agency_runtime.core.selector import judge_transport as _transport
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.selector.intent_text import affirmative_intent

logger = logging.getLogger("agency_runtime.selector.judge")

_MAX_JUDGE_RESPONSE_BYTES = 256 * 1024
_MAX_PROVIDER_ATTEMPTS = MAX_PROVIDER_CHAIN_ENTRIES
_MAX_JUDGE_DEADLINE_SECONDS = 60.0
_MAX_JUDGE_CANDIDATES = 20
_MAX_SELECTED = 50
_MIN_RELATIVE_FALLBACK_SCORE = 0.30


def _agent_id(agent: dict[str, Any]) -> str:
    """Return the catalog identity accepted across selector entry points."""
    return str(agent.get("slug") or agent.get("agent_slug") or "")


def _judge_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return only identified candidates that can actually appear in a prompt."""
    return [candidate for candidate in candidates if _agent_id(candidate)][:_MAX_JUDGE_CANDIDATES]


def _validated_max_selected(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_selected must be an integer")
    if not 1 <= value <= _MAX_SELECTED:
        raise ValueError(f"max_selected must be between 1 and {_MAX_SELECTED}")
    return value


def _scored_selection(
    candidates: list[dict[str, Any]],
    scores: list[float],
    max_selected: int,
) -> list[str]:
    """Keep strong deterministic matches without padding with weak positives."""
    top_score = scores[0] if scores else 0.0
    if top_score <= 0:
        return []
    cutoff = top_score * _MIN_RELATIVE_FALLBACK_SCORE
    selected: list[str] = []
    for agent, score in zip(candidates, scores, strict=True):
        agent_id = _agent_id(agent)
        if score >= cutoff and agent_id and agent_id not in selected:
            selected.append(agent_id)
            if len(selected) >= max_selected:
                break
    return selected


def _bounded_confidence(value: Any) -> float | None:
    """Parse model confidence and constrain it to the public 0..1 contract."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(confidence):
        return None
    return max(0.0, min(1.0, confidence))


def _attempt_signature(
    base_url: str,
    model: str,
    ollama_mode: bool,
    provider_type: str = "openai-compatible",
    transport: str = "",
) -> tuple[str, str, str]:
    """Identify equivalent network attempts across new and legacy config."""
    normalized_type = provider_type.strip().lower()
    if normalized_type == "cli":
        return "cli", transport.strip().lower(), model.strip().lower()
    protocol = "ollama" if ollama_mode else normalized_type
    return protocol, base_url.rstrip("/").lower(), model.strip().lower()


def _provider_is_attemptable(provider: ProviderEntry) -> bool:
    provider_type = provider.type.strip().lower()
    if provider_type == "cli":
        return provider.transport.strip().lower() in SUPPORTED_CLI_TRANSPORTS
    if not provider.model or not provider.base_url:
        return False
    return (
        provider_type == "ollama"
        or provider.ollama_mode
        or bool(provider.resolve_api_key())
        or (
            provider_type in {"openai", "openai-compatible", "litellm"}
            and _is_loopback_http_url(provider.base_url)
        )
    )


def _network_target_signature(base_url: str, model: str) -> tuple[str, str]:
    """Identify a concrete endpoint/model independent of protocol metadata."""
    return base_url.rstrip("/").lower(), model.strip().lower()


def _bounded_duration(value: Any, *, maximum: float) -> float:
    """Return a finite positive duration constrained to *maximum*."""
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(duration) or duration <= 0:
        return 0.0
    return min(duration, maximum)


def _with_cumulative_latency(
    result: dict[str, Any],
    attempts_started: float,
) -> dict[str, Any]:
    elapsed_ms = int((time.monotonic() - attempts_started) * 1000)
    result["latency_ms"] = max(int(result.get("latency_ms", 0) or 0), elapsed_ms)
    return result


# Protocol compatibility surface.  Sibling modules resolve dependencies back
# through this facade so existing monkeypatches remain effective.
_read_json_object = _protocol.read_json_object
parse_json_response = _protocol.parse_json_response
_build_judge_prompt = _protocol.build_judge_prompt
_response_content = _protocol.response_content
_build_judge_payload = _protocol.build_judge_payload
_join_api_path = _protocol.join_api_path
_validated_decision = _protocol.validated_decision
_applied_result = _protocol.applied_result
_encoded_model_payload = _protocol.encoded_model_payload
_provider_headers = _protocol.provider_headers
_build_http_request = _protocol.build_http_request

# Provider transport compatibility surface.
_try_cli_provider = _transport.try_cli_provider
_provider_credentials_are_safe = _transport.provider_credentials_are_safe
_execute_http_request = _transport.execute_http_request
_try_http_provider = _transport.try_http_provider
_try_provider = _transport.try_provider
_try_legacy_judge = _transport.try_legacy_judge

# Ordered-attempt compatibility surface.
_AttemptState = _attempts.AttemptState
_provider_attempt_identity = _attempts.provider_attempt_identity
_try_provider_chain = _attempts.try_provider_chain
_try_legacy_fallback = _attempts.try_legacy_fallback
_try_ollama_fallback = _attempts.try_ollama_fallback


def _empty_judge_result() -> dict[str, Any]:
    return {
        "selected_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "status": "unknown",
        "error": "",
    }


def _confidence_bypass_result(
    candidates: list[dict[str, Any]],
    scores: list[float],
    *,
    max_sel: int,
    threshold: float,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any] | None:
    if top_score < threshold:
        return None
    selected_ids = _scored_selection(candidates, scores, max_sel)
    if not selected_ids:
        return None
    return {
        "selected_ids": selected_ids,
        "confidence": min(0.99, 0.7 + top_score / 100),
        "latency_ms": 0,
        "status": "confidence_bypass",
        "candidate_count": candidate_count,
        "top_score": top_score,
    }


def _fallback_result(
    state: _AttemptState,
    candidates: list[dict[str, Any]],
    scores: list[float],
    candidate_count: int,
    top_score: float,
    max_sel: int,
) -> dict[str, Any]:
    fallback = _token_only_fallback(
        candidates,
        scores,
        candidate_count,
        top_score,
        max_sel,
    )
    return _with_cumulative_latency(fallback, state.started)


def query_judge(
    task_description: str,
    catalog: list[dict[str, Any]],
    *,
    config: AgencyConfig | None = None,
    judge_config: JudgeConfig | None = None,
    max_selected: int | None = None,
) -> dict[str, Any]:
    """Query configured providers and fall back deterministically.

    A nonempty typed provider chain is authoritative.  Legacy judge and Ollama
    fallbacks are used only when no typed chain is configured.
    """
    if not isinstance(task_description, str):
        raise TypeError("task_description must be a string")
    cfg = config or load_config()
    jc = judge_config or cfg.judge
    max_sel = _validated_max_selected(jc.max_selected if max_selected is None else max_selected)
    state = _AttemptState.begin(jc.timeout)
    result = _empty_judge_result()

    if not catalog:
        result["status"] = "no_catalog"
        result["error"] = "agent catalog not loaded"
        return result

    # Lexical narrowing cannot infer negation.  Exclude high-confidence opt-out
    # clauses from scoring while retaining the complete task for the judge.
    candidates, scores = pre_narrow(affirmative_intent(task_description), catalog)
    candidate_count = len(candidates)
    top_score = scores[0] if scores else 0.0

    bypass_result = _confidence_bypass_result(
        candidates,
        scores,
        max_sel=max_sel,
        threshold=jc.confidence_bypass_threshold,
        candidate_count=candidate_count,
        top_score=top_score,
    )
    if bypass_result is not None:
        return bypass_result

    provider_result = _try_provider_chain(
        state,
        cfg.providers,
        task_description,
        candidates,
        max_sel,
        candidate_count,
        top_score,
    )
    if provider_result is not None:
        return _with_cumulative_latency(provider_result, state.started)

    if cfg.providers:
        return _fallback_result(
            state,
            candidates,
            scores,
            candidate_count,
            top_score,
            max_sel,
        )

    legacy_result = _try_legacy_fallback(
        state,
        jc,
        task_description,
        candidates,
        max_sel,
        candidate_count,
        top_score,
    )
    if legacy_result is not None:
        return _with_cumulative_latency(legacy_result, state.started)

    ollama_result = _try_ollama_fallback(
        state,
        cfg,
        task_description,
        candidates,
        max_sel,
        candidate_count,
        top_score,
    )
    if ollama_result is not None:
        return _with_cumulative_latency(ollama_result, state.started)

    return _fallback_result(
        state,
        candidates,
        scores,
        candidate_count,
        top_score,
        max_sel,
    )


def _token_only_fallback(
    candidates: list[dict[str, Any]],
    scores: list[float],
    candidate_count: int,
    top_score: float,
    max_sel: int,
) -> dict[str, Any]:
    """Return bounded token-scored candidates without an LLM call."""
    selected_ids = _scored_selection(candidates, scores, max_sel)
    has_signal = bool(selected_ids)
    return {
        "selected_ids": selected_ids,
        "confidence": 0.3 if has_signal else 0.0,
        "latency_ms": 0,
        "status": "token_fallback" if has_signal else "abstained",
        "error": "" if has_signal else "no positive routing signal",
        "candidate_count": candidate_count,
        "top_score": top_score,
    }
