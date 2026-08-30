"""Fail-closed child-judge provider selection for live host canaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from agency_runtime.core.config import AgencyConfig, ProviderEntry, is_safe_credential_url
from agency_runtime.core.inference_profiles import provider_from_profile

CANARY_CHILD_JUDGE_PROVIDER_ENV = "AGENCY_CANARY_CHILD_JUDGE_PROVIDER"
_SUPPORTED_CLI_TRANSPORTS = frozenset({"claude", "codex"})
_SUPPORTED_PROFILE_ADAPTERS = frozenset({"anthropic", "litellm", "ollama"})


class CanaryChildJudgeProviderError(ValueError):
    """The canary's requested child-judge provider cannot be proven."""


def configured_canary_child_judge_provider(
    config: AgencyConfig,
    host: str,
) -> tuple[ProviderEntry, str] | None:
    """Resolve one host pin to one exact provider or canary-only profile."""

    requested = config.canary.child_judge_provider(host)
    if not requested:
        return None
    provider_matches = [
        provider
        for provider in config.providers
        if provider.name.strip().casefold() == requested.casefold()
    ]
    profile_matches = [
        profile
        for name, profile in config.inference.profiles.items()
        if name.strip().casefold() == requested.casefold()
    ]
    if len(provider_matches) + len(profile_matches) != 1:
        raise CanaryChildJudgeProviderError(
            "the canary child-judge provider does not resolve exactly once"
        )
    if profile_matches:
        provider = provider_from_profile(profile_matches[0])
        if provider.name.strip().casefold() != requested.casefold():
            raise CanaryChildJudgeProviderError(
                "the canary child-judge provider does not resolve exactly once"
            )
        adapter = provider.type.strip().casefold()
        transport = provider.transport.strip().casefold()
        if adapter == "cli" and transport in _SUPPORTED_CLI_TRANSPORTS:
            return provider, transport
        if (
            adapter not in _SUPPORTED_PROFILE_ADAPTERS
            or (adapter == "litellm" and not (provider.api_key or provider.api_key_env))
            or not is_safe_credential_url(provider.base_url)
            or not provider.is_available()
        ):
            raise CanaryChildJudgeProviderError(
                "the canary child-judge inference profile is not supported or available"
            )
        return provider, ""

    provider = provider_matches[0]
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
    return (
        replace(
            config,
            judge=replace(config.judge, timeout=provider.timeout),
            providers=(provider,),
        ),
        provider.name,
    )


__all__ = [
    "CANARY_CHILD_JUDGE_PROVIDER_ENV",
    "CanaryChildJudgeProviderError",
    "canary_child_judge_config",
    "configured_canary_child_judge_provider",
]
