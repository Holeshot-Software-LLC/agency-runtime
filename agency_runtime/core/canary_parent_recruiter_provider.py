"""Fail-closed parent-recruiter provider selection for accepted-outcome canaries."""

from __future__ import annotations

from collections.abc import Mapping

from agency_runtime.core.config import AgencyConfig, ProviderEntry

ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV = "AGENCY_ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER"
_SUPPORTED_CLI_TRANSPORTS = frozenset({"claude", "codex"})


class CanaryParentRecruiterProviderError(ValueError):
    """The accepted-outcome parent recruiter pin cannot be proven."""


def configured_accepted_outcome_parent_recruiter_provider(
    config: AgencyConfig,
    host: str,
) -> tuple[ProviderEntry, str] | None:
    """Resolve one host's accepted-outcome recruiter pin to one CLI provider."""

    requested = config.canary.accepted_outcome_parent_recruiter_provider(host)
    if not requested:
        return None
    matches = [
        provider
        for provider in config.providers
        if provider.name.strip().casefold() == requested.casefold()
    ]
    if len(matches) != 1:
        raise CanaryParentRecruiterProviderError(
            "the accepted-outcome parent-recruiter provider does not resolve exactly once"
        )
    provider = matches[0]
    transport = provider.transport.strip().casefold()
    if provider.type != "cli" or transport not in _SUPPORTED_CLI_TRANSPORTS:
        raise CanaryParentRecruiterProviderError(
            "the accepted-outcome parent-recruiter provider is not a supported CLI transport"
        )
    return provider, transport


def accepted_outcome_parent_recruiter_provider(
    config: AgencyConfig,
    host: str,
    environ: Mapping[str, str],
) -> ProviderEntry | None:
    """Return the projected canary recruiter provider, or preserve ordinary routing."""

    if environ.get("AGENCY_CANARY_MODE") != "1":
        return None
    projected = str(environ.get(ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV) or "").strip()
    if not projected:
        return None
    resolved = configured_accepted_outcome_parent_recruiter_provider(config, host)
    if resolved is None:
        raise CanaryParentRecruiterProviderError(
            "the accepted-outcome parent-recruiter projection has no configured pin"
        )
    provider, _transport = resolved
    if projected != provider.name:
        raise CanaryParentRecruiterProviderError(
            "the accepted-outcome parent-recruiter projection does not match its configured pin"
        )
    return provider


__all__ = [
    "ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV",
    "CanaryParentRecruiterProviderError",
    "accepted_outcome_parent_recruiter_provider",
    "configured_accepted_outcome_parent_recruiter_provider",
]
