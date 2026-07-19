"""Ordered provider-attempt accounting for the semantic judge."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from agency_runtime.core.config import AgencyConfig, JudgeConfig, ProviderEntry

logger = logging.getLogger("agency_runtime.selector.judge")


def _facade():
    """Resolve judge dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core.selector import judge

    return judge


@dataclass
class AttemptState:
    """Mutable accounting shared by one ordered judge fallback chain."""

    started: float
    deadline: float
    attempted: set[tuple[str, str, str]] = field(default_factory=set)
    attempted_targets: set[tuple[str, str]] = field(default_factory=set)
    receipts: list[dict[str, str]] = field(default_factory=list)
    count: int = 0

    @classmethod
    def begin(cls, total_timeout: float) -> AttemptState:
        facade = _facade()
        started = facade.time.monotonic()
        deadline = started + facade._bounded_duration(
            total_timeout,
            maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
        )
        return cls(started=started, deadline=deadline)

    def reserve(self, configured_timeout: float) -> float:
        """Reserve one bounded attempt and return its remaining timeout."""
        facade = _facade()
        if self.count >= facade._MAX_PROVIDER_ATTEMPTS:
            return 0.0
        remaining = self.deadline - facade.time.monotonic()
        per_attempt = facade._bounded_duration(
            configured_timeout,
            maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
        )
        timeout = min(remaining, per_attempt)
        if timeout <= 0:
            return 0.0
        self.count += 1
        return timeout

    def record(
        self,
        provider: ProviderEntry,
        *,
        status: str,
        reason: str = "",
    ) -> None:
        """Record one bounded, credential-free provider-chain outcome."""

        if len(self.receipts) >= _facade()._MAX_PROVIDER_ATTEMPTS:
            return

        def bounded(value: object, maximum: int = 128) -> str:
            return " ".join(str(value or "").split())[:maximum]

        provider_type = bounded(provider.type, 32).lower()
        receipt = {
            "provider_name": bounded(provider.name) or "unnamed",
            "provider_type": provider_type or "unknown",
            "requested_model": bounded(provider.model, 256),
            "model_group": bounded(provider.model, 256) if provider_type == "litellm" else "",
            "status": bounded(status, 32),
            "reason": bounded(reason, 128),
        }
        self.receipts.append(receipt)


def _attach_provider_identity(
    result: dict[str, Any],
    provider: ProviderEntry,
) -> dict[str, Any]:
    """Preserve provider request identity without inventing model telemetry."""

    provider_type = provider.type.strip().lower() or "unknown"
    result.setdefault("provider_name", provider.name)
    result.setdefault("provider_type", provider_type)
    result.setdefault("requested_model", provider.model)
    if provider_type == "litellm":
        result.setdefault("model_group", provider.model)
    return result


def provider_attempt_identity(
    provider: ProviderEntry,
) -> tuple[tuple[str, str, str], tuple[str, str]]:
    facade = _facade()
    signature = facade._attempt_signature(
        provider.base_url,
        provider.model,
        provider.ollama_mode,
        provider.type,
        provider.transport,
    )
    if provider.type.strip().lower() == "cli":
        target = (
            f"cli:{provider.transport.strip().lower()}",
            provider.model.strip().lower(),
        )
    else:
        target = facade._network_target_signature(provider.base_url, provider.model)
    return signature, target


def try_provider_chain(
    state: AttemptState,
    providers: tuple[ProviderEntry, ...],
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any] | None:
    facade = _facade()
    for provider in providers:
        signature, target = facade._provider_attempt_identity(provider)
        if signature in state.attempted:
            state.record(provider, status="skipped", reason="duplicate_provider")
            continue
        if not facade._provider_is_attemptable(provider):
            state.record(provider, status="failed", reason="provider_unavailable")
            continue
        configured_timeout = facade._bounded_duration(
            provider.timeout,
            maximum=facade._MAX_JUDGE_DEADLINE_SECONDS,
        )
        if configured_timeout <= 0:
            state.record(provider, status="failed", reason="invalid_timeout")
            continue
        timeout = state.reserve(configured_timeout)
        if timeout <= 0:
            state.record(provider, status="failed", reason="attempt_budget_exhausted")
            continue
        state.attempted.add(signature)
        state.attempted_targets.add(target)
        result = facade._try_provider(
            provider,
            task_description,
            candidates,
            max_sel,
            candidate_count,
            top_score,
            request_timeout=timeout,
        )
        if result is not None:
            state.record(provider, status="applied")
            return _attach_provider_identity(result, provider)
        state.record(provider, status="failed", reason="provider_call_failed")
        logger.debug("provider %s failed, trying next", provider.name)
    return None


def try_legacy_fallback(
    state: AttemptState,
    judge_config: JudgeConfig,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any] | None:
    facade = _facade()
    signature = facade._attempt_signature(
        judge_config.base_url,
        judge_config.model,
        judge_config.ollama_mode,
    )
    target = facade._network_target_signature(judge_config.base_url, judge_config.model)
    provider = ProviderEntry(
        name="legacy-judge",
        type="ollama" if judge_config.ollama_mode else "openai-compatible",
        model=judge_config.model,
        base_url=judge_config.base_url,
        api_key=judge_config.api_key,
        api_key_env=judge_config.api_key_env,
        ollama_mode=judge_config.ollama_mode,
        timeout=judge_config.timeout,
    )
    eligible = bool(
        judge_config.model
        and judge_config.base_url
        and signature not in state.attempted
        and target not in state.attempted_targets
    )
    if not eligible:
        if judge_config.model and judge_config.base_url:
            state.record(provider, status="skipped", reason="duplicate_provider")
        return None
    timeout = state.reserve(judge_config.timeout)
    if timeout <= 0:
        state.record(provider, status="failed", reason="attempt_budget_exhausted")
        return None
    state.attempted.add(signature)
    state.attempted_targets.add(target)
    result = facade._try_legacy_judge(
        judge_config,
        task_description,
        candidates,
        max_sel,
        candidate_count,
        top_score,
        request_timeout=timeout,
    )
    if result is None:
        state.record(provider, status="failed", reason="provider_call_failed")
        return None
    state.record(provider, status="applied")
    return _attach_provider_identity(result, provider)


def try_ollama_fallback(
    state: AttemptState,
    config: AgencyConfig,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any] | None:
    if not config.ollama.enabled or not config.ollama.model:
        return None
    provider = ProviderEntry(
        name="ollama-fallback",
        type="ollama",
        model=config.ollama.model,
        base_url=config.ollama.base_url,
        ollama_mode=True,
        timeout=config.judge.timeout,
    )
    facade = _facade()
    signature = facade._attempt_signature(
        provider.base_url,
        provider.model,
        provider.ollama_mode,
    )
    if signature in state.attempted:
        state.record(provider, status="skipped", reason="duplicate_provider")
        return None
    timeout = state.reserve(provider.timeout)
    if timeout <= 0:
        state.record(provider, status="failed", reason="attempt_budget_exhausted")
        return None
    state.attempted.add(signature)
    result = facade._try_provider(
        provider,
        task_description,
        candidates,
        max_sel,
        candidate_count,
        top_score,
        request_timeout=timeout,
    )
    if result is None:
        state.record(provider, status="failed", reason="provider_call_failed")
        return None
    state.record(provider, status="applied")
    return _attach_provider_identity(result, provider)


__all__ = [
    "AttemptState",
    "provider_attempt_identity",
    "try_legacy_fallback",
    "try_ollama_fallback",
    "try_provider_chain",
]
