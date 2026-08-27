"""Semantic judge facade with inference-owned specialist selection.

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
from agency_runtime.core.agent_identity import agent_identity
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
from agency_runtime.core.selector.semantic_retrieval import (
    CandidateUnion,
    retrieve_candidate_union,
)

logger = logging.getLogger("agency_runtime.selector.judge")

_MAX_JUDGE_RESPONSE_BYTES = 256 * 1024
_MAX_PROVIDER_ATTEMPTS = MAX_PROVIDER_CHAIN_ENTRIES
# Legacy ``judge.timeout`` input remains schema-capped at 60 seconds. Resolved
# provider and inference-profile entries may declare up to 120 seconds, so the
# internal transport ceiling must preserve that already-validated bound when a
# caller deliberately projects one provider timeout into the aggregate budget.
_MAX_JUDGE_DEADLINE_SECONDS = 120.0
_MAX_JUDGE_CANDIDATES = 20
_MAX_COMPLETE_CANDIDATE_PROMPT_BYTES = 1_280 * 1024
_MAX_SELECTED = 50


class _CompleteCandidateUniverse(list[dict[str, Any]]):
    """Mark an exact candidate universe that must never be narrowed."""


def _agent_id(agent: dict[str, Any]) -> str:
    """Return the catalog identity accepted across selector entry points."""
    return agent_identity(agent)


def _judge_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return only identified candidates that can actually appear in a prompt."""
    identified = [candidate for candidate in candidates if _agent_id(candidate)]
    if isinstance(candidates, _CompleteCandidateUniverse):
        return _CompleteCandidateUniverse(identified)
    return identified[:_MAX_JUDGE_CANDIDATES]


def _validated_max_selected(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("max_selected must be an integer")
    if not 1 <= value <= _MAX_SELECTED:
        raise ValueError(f"max_selected must be between 1 and {_MAX_SELECTED}")
    return value


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


def inference_is_configured(
    config: AgencyConfig,
    judge_config: JudgeConfig | None = None,
) -> bool:
    """Return whether semantic inference is an authoritative routing dependency.

    A declared typed chain is authoritative even when one of its entries is
    currently unavailable: silently treating that configuration error as
    heuristic success would hide the degraded state. A legacy credential
    declaration is authoritative even when its environment variable is
    currently absent. The bundled keyless Ollama settings remain an optional
    accelerator; operators who require local inference declare Ollama in the
    typed provider chain.
    """

    if config.providers:
        return True
    jc = judge_config or config.judge
    legacy_declared = bool(
        jc.model
        and jc.base_url
        and (jc.api_key or jc.api_key_env or jc.ollama_mode or _is_loopback_http_url(jc.base_url))
    )
    return legacy_declared


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


def _with_inference_evidence(
    result: dict[str, Any],
    state: _AttemptState,
    *,
    configured: bool,
    mode: str,
) -> dict[str, Any]:
    """Attach bounded provider-chain truth without altering model receipts."""

    enriched = dict(result)
    attempts = [dict(receipt) for receipt in state.receipts]
    enriched.update(
        inference_configured=configured,
        inference_required=True,
        inference_attempted=state.count > 0,
        inference_mode=mode,
        provider_attempts=attempts,
        inference_failures=[
            dict(receipt) for receipt in attempts if receipt.get("status") != "applied"
        ],
    )
    return enriched


def _with_retrieval_evidence(
    result: dict[str, Any],
    retrieval: CandidateUnion,
) -> dict[str, Any]:
    """Attach bounded full-roster recall evidence to every judge outcome."""

    enriched = dict(result)
    enriched["retrieval"] = retrieval.evidence()
    return enriched


def _with_complete_universe_evidence(
    result: dict[str, Any],
    *,
    candidate_count: int,
) -> dict[str, Any]:
    """Attach proof that every supplied hard-eligible card reached inference."""

    enriched = dict(result)
    enriched["retrieval"] = {
        "mode": "complete-candidate-universe",
        "full_roster_count": candidate_count,
        "candidate_union_count": candidate_count,
        "lexical_count": 0,
        "semantic_count": 0,
        "hard_negative_count": 0,
        "candidate_rows_complete": True,
    }
    return enriched


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


def _inference_failure_result(
    state: _AttemptState,
    candidate_count: int,
    top_score: float,
    *,
    configured: bool,
    detail: str = "",
) -> dict[str, Any]:
    """Fail closed without projecting a deterministic recommendation."""

    invalid = any(
        "invalid" in str(receipt.get("reason") or "").casefold()
        or "contract" in str(receipt.get("reason") or "").casefold()
        for receipt in state.receipts
    )
    status = "inference_invalid" if configured and invalid else "inference_unavailable"
    failure = {
        "selected_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "status": status,
        "source": "inference_failure",
        "error": detail or status,
        "candidate_count": candidate_count,
        "top_score": top_score,
    }
    return _with_inference_evidence(
        _with_cumulative_latency(failure, state.started),
        state,
        configured=configured,
        mode="invalid" if status == "inference_invalid" else "unavailable",
    )


def query_judge(
    task_description: str,
    catalog: list[dict[str, Any]],
    *,
    config: AgencyConfig | None = None,
    judge_config: JudgeConfig | None = None,
    max_selected: int | None = None,
    candidate_scope: str = "retrieved",
) -> dict[str, Any]:
    """Query inference providers and fail closed when none returns a decision.

    Typed, legacy, and local providers are inference transports. Deterministic
    retrieval may populate their candidate prompt, but it never selects a
    specialist when inference is missing or invalid.
    """
    if not isinstance(task_description, str):
        raise TypeError("task_description must be a string")
    if candidate_scope not in {"retrieved", "complete"}:
        raise ValueError("candidate_scope must be 'retrieved' or 'complete'")
    cfg = config or load_config()
    jc = judge_config or cfg.judge
    max_sel = _validated_max_selected(jc.max_selected if max_selected is None else max_selected)
    state = _AttemptState.begin(jc.timeout)
    result = _empty_judge_result()
    configured_inference = inference_is_configured(cfg, jc)
    complete_universe = candidate_scope == "complete"
    retrieval = (
        None
        if complete_universe
        else retrieve_candidate_union(
            affirmative_intent(task_description),
            catalog,
            lexical_retriever=pre_narrow,
        )
    )

    def finish(value: dict[str, Any]) -> dict[str, Any]:
        if complete_universe:
            return _with_complete_universe_evidence(value, candidate_count=len(catalog))
        assert retrieval is not None
        return _with_retrieval_evidence(value, retrieval)

    if not catalog:
        return finish(
            _with_inference_evidence(
                {
                    **result,
                    "status": (
                        "inference_invalid" if configured_inference else "inference_unavailable"
                    ),
                    "source": "inference_failure",
                    "error": "agent catalog not loaded",
                },
                state,
                configured=configured_inference,
                mode="invalid" if configured_inference else "unavailable",
            )
        )

    if complete_universe:
        identities = [_agent_id(candidate) for candidate in catalog]
        if any(not identity for identity in identities) or len(set(identities)) != len(identities):
            return finish(
                _inference_failure_result(
                    state,
                    len(catalog),
                    0.0,
                    configured=configured_inference,
                    detail="complete candidate universe has invalid or duplicate identities",
                )
            )
        candidates = _CompleteCandidateUniverse(catalog)
        candidate_count = len(candidates)
        top_score = 0.0
        try:
            # Preflight the shared transport before any provider attempt.  An
            # over-budget exact universe fails open; it is never truncated.
            _build_judge_prompt(task_description, candidates, max_sel)
        except (TypeError, UnicodeError, ValueError):
            return finish(
                _inference_failure_result(
                    state,
                    candidate_count,
                    top_score,
                    configured=configured_inference,
                    detail="complete candidate universe exceeds bounded inference transport",
                )
            )
    else:
        assert retrieval is not None
        # Lexical narrowing cannot infer negation.  Exclude high-confidence opt-out
        # clauses from scoring while retaining the complete task for the judge.
        candidates = list(retrieval.candidates)
        scores = list(retrieval.scores)
        candidate_count = len(candidates)
        top_score = scores[0] if scores else 0.0

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
        applied = _with_cumulative_latency(provider_result, state.started)
        return finish(
            _with_inference_evidence(
                applied,
                state,
                configured=configured_inference,
                mode="inferred",
            )
        )

    if cfg.providers:
        return finish(
            _inference_failure_result(
                state,
                candidate_count,
                top_score,
                configured=True,
                detail="configured inference providers exhausted without a valid decision",
            )
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
        applied = _with_cumulative_latency(legacy_result, state.started)
        return finish(
            _with_inference_evidence(
                applied,
                state,
                configured=configured_inference,
                mode="inferred",
            )
        )

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
        applied = _with_cumulative_latency(ollama_result, state.started)
        return finish(
            _with_inference_evidence(
                applied,
                state,
                configured=configured_inference,
                mode="inferred",
            )
        )

    if configured_inference:
        return finish(
            _inference_failure_result(
                state,
                candidate_count,
                top_score,
                configured=True,
                detail="configured inference providers exhausted without a valid decision",
            )
        )

    return finish(
        _inference_failure_result(
            state,
            candidate_count,
            top_score,
            configured=False,
            detail="no inference provider is configured",
        )
    )
