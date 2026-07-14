"""Credential-safe CLI and HTTP transports for semantic judge providers."""

from __future__ import annotations

import logging
import urllib.request
from typing import Any

from agency_runtime.core.config import (
    JudgeConfig,
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
)

logger = logging.getLogger("agency_runtime.selector.judge")


def _facade():
    """Resolve judge dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core.selector import judge

    return judge


def try_cli_provider(
    provider: ProviderEntry,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None,
) -> dict[str, Any] | None:
    facade = _facade()
    timeout = facade._bounded_duration(
        provider.timeout if request_timeout is None else request_timeout,
        maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
    )
    if timeout <= 0:
        return None
    prompt = facade._build_judge_prompt(task_description, candidates, max_sel)
    started = facade.time.monotonic()
    try:
        parsed = facade.invoke_cli_judge(provider, prompt, timeout=timeout)
    except Exception as exc:
        logger.debug(
            "provider %s failed (%s)",
            provider.name[:80],
            type(exc).__name__,
        )
        return None
    decision = facade._validated_decision(parsed, candidates, max_sel)
    if decision is None:
        return None
    return facade._applied_result(
        decision,
        latency_ms=int((facade.time.monotonic() - started) * 1000),
        provider=f"{provider.name} (cli:{provider.transport.strip().lower()})",
        candidate_count=candidate_count,
        top_score=top_score,
    )


def provider_credentials_are_safe(
    provider: ProviderEntry,
    *,
    provider_type: str,
    ollama_mode: bool,
    api_key: str,
) -> bool:
    if not provider.model or not provider.base_url:
        logger.debug("provider %s: model or base URL missing, skipping", provider.name)
        return False
    keyless_loopback = provider_type in {
        "openai",
        "openai-compatible",
        "litellm",
    } and _is_loopback_http_url(provider.base_url)
    if not ollama_mode and not api_key and not keyless_loopback:
        logger.debug("provider %s: no api key, skipping", provider.name)
        return False
    if api_key and not is_safe_credential_url(provider.base_url):
        logger.debug("provider %s: unsafe credential transport, skipping", provider.name)
        return False
    return True


def execute_http_request(
    request: urllib.request.Request,
    *,
    timeout: float,
    log_name: str,
) -> tuple[dict[str, Any], float] | None:
    facade = _facade()
    started = facade.time.monotonic()
    try:
        with facade.open_no_redirect(request, timeout=timeout) as response:
            data = facade._read_json_object(response)
    except Exception as exc:
        logger.debug("%s failed (%s)", log_name, type(exc).__name__)
        return None
    if data is None:
        logger.debug("%s returned an invalid or oversized response", log_name)
        return None
    return data, facade.time.monotonic() - started


def try_http_provider(
    provider: ProviderEntry,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None,
    *,
    api_key: str,
    provider_type: str,
    ollama_mode: bool,
) -> dict[str, Any] | None:
    facade = _facade()
    if not facade._provider_credentials_are_safe(
        provider,
        provider_type=provider_type,
        ollama_mode=ollama_mode,
        api_key=api_key,
    ):
        return None
    request = facade._build_http_request(
        task_description=task_description,
        candidates=candidates,
        max_sel=max_sel,
        base_url=provider.base_url,
        model=provider.model,
        ollama_mode=ollama_mode,
        provider_type=provider_type,
        api_key=api_key,
        use_completion_tokens=provider_type in {"openai", "openai-compatible"},
    )
    timeout = facade._bounded_duration(
        provider.timeout if request_timeout is None else request_timeout,
        maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
    )
    if timeout <= 0:
        return None
    response = facade._execute_http_request(
        request,
        timeout=timeout,
        log_name=f"provider {provider.name[:80]}",
    )
    if response is None:
        return None
    data, elapsed = response
    decision = facade._validated_decision(
        facade.parse_json_response(
            facade._response_content(
                data,
                provider_type=provider_type,
                ollama_mode=ollama_mode,
            )
        ),
        candidates,
        max_sel,
    )
    if decision is None:
        return None
    return facade._applied_result(
        decision,
        latency_ms=int(elapsed * 1000),
        provider=f"{provider.name} ({provider_type})",
        candidate_count=candidate_count,
        top_score=top_score,
    )


def try_provider(
    provider: ProviderEntry,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Try one configured provider and return only a validated result."""
    facade = _facade()
    prompted_candidates = facade._judge_candidates(candidates)
    if not prompted_candidates:
        return None

    declared_type = provider.type.strip().lower()
    if declared_type == "cli":
        return facade._try_cli_provider(
            provider,
            task_description,
            prompted_candidates,
            max_sel,
            candidate_count,
            top_score,
            request_timeout,
        )

    api_key = provider.resolve_api_key()
    ollama_mode = provider.ollama_mode or declared_type == "ollama"
    provider_type = "ollama" if ollama_mode else declared_type
    return facade._try_http_provider(
        provider,
        task_description,
        prompted_candidates,
        max_sel,
        candidate_count,
        top_score,
        request_timeout,
        api_key=api_key,
        provider_type=provider_type,
        ollama_mode=ollama_mode,
    )


def try_legacy_judge(
    judge_config: JudgeConfig,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Try the backward-compatible judge configuration."""
    facade = _facade()
    api_key = judge_config.resolve_api_key()
    if not judge_config.model or not judge_config.base_url:
        return None
    prompted_candidates = facade._judge_candidates(candidates)
    if not prompted_candidates:
        return None
    if api_key and not is_safe_credential_url(judge_config.base_url):
        logger.debug("legacy judge: unsafe credential transport, skipping")
        return None

    ollama_mode = judge_config.ollama_mode
    request = facade._build_http_request(
        task_description=task_description,
        candidates=prompted_candidates,
        max_sel=max_sel,
        base_url=judge_config.base_url,
        model=judge_config.model,
        ollama_mode=ollama_mode,
        provider_type="openai-compatible",
        api_key=api_key,
        use_completion_tokens=not ollama_mode,
    )
    timeout = facade._bounded_duration(
        judge_config.timeout if request_timeout is None else request_timeout,
        maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
    )
    if timeout <= 0:
        return None
    response = facade._execute_http_request(
        request,
        timeout=timeout,
        log_name="legacy judge",
    )
    if response is None:
        return None
    data, elapsed = response
    decision = facade._validated_decision(
        facade.parse_json_response(
            facade._response_content(
                data,
                provider_type="ollama" if ollama_mode else "openai-compatible",
                ollama_mode=ollama_mode,
            )
        ),
        prompted_candidates,
        max_sel,
    )
    if decision is None:
        return None
    selected_ids, confidence = decision
    return {
        "selected_ids": selected_ids,
        "confidence": confidence,
        "latency_ms": int(elapsed * 1000),
        "status": "applied",
        "error": "",
        "provider": judge_config.model,
        "candidate_count": candidate_count,
        "top_score": top_score,
    }


__all__ = [
    "execute_http_request",
    "provider_credentials_are_safe",
    "try_cli_provider",
    "try_http_provider",
    "try_legacy_judge",
    "try_provider",
]
