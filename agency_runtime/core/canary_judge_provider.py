"""Fail-closed child-judge provider selection for live host canaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from agency_runtime.core.config import AgencyConfig, ProviderEntry

CANARY_CHILD_JUDGE_PROVIDER_ENV = "AGENCY_CANARY_CHILD_JUDGE_PROVIDER"
_SUPPORTED_CLI_TRANSPORTS = frozenset({"claude", "codex"})


class CanaryChildJudgeProviderError(ValueError):
    """The canary's requested child-judge provider cannot be proven."""


def configured_canary_child_judge_provider(
    config: AgencyConfig,
    host: str,
) -> tuple[ProviderEntry, str] | None:
    """Resolve one host pin to its exact configured CLI provider and transport."""

    requested = config.canary.child_judge_provider(host)
    if not requested:
        return None
    matches = [
        provider
        for provider in config.providers
        if provider.name.strip().casefold() == requested.casefold()
    ]
    if len(matches) != 1:
        raise CanaryChildJudgeProviderError(
            "the canary child-judge provider does not resolve exactly once"
        )
    provider = matches[0]
    transport = provider.transport.strip().casefold()
    if provider.type != "cli" or transport not in _SUPPORTED_CLI_TRANSPORTS:
        raise CanaryChildJudgeProviderError(
            "the canary child-judge provider is not a supported CLI transport"
        )
    return provider, transport


def canary_child_judge_config(
    config: AgencyConfig,
    host: str,
    environ: Mapping[str, str],
) -> tuple[AgencyConfig, str]:
    """Narrow a canary judge to one projected provider, without fallback."""

    if environ.get("AGENCY_CANARY_MODE") != "1":
        return config, ""
    resolved = configured_canary_child_judge_provider(config, host)
    projected = str(environ.get(CANARY_CHILD_JUDGE_PROVIDER_ENV) or "").strip()
    if resolved is None:
        raise CanaryChildJudgeProviderError(
            "the canary child-judge provider projection has no configured pin"
        )
    provider, _transport = resolved
    if projected != provider.name:
        raise CanaryChildJudgeProviderError(
            "the canary child-judge provider projection does not match its configured pin"
        )
    return replace(config, providers=(provider,)), provider.name


__all__ = [
    "CANARY_CHILD_JUDGE_PROVIDER_ENV",
    "CanaryChildJudgeProviderError",
    "canary_child_judge_config",
    "configured_canary_child_judge_provider",
]
