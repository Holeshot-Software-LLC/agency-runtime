"""Per-stage inference profile route resolution.

ADR-0153 / AR-235 §3. Maps a route key (e.g. ``workforce.hiring``,
``workforce.hiring.security_review``) to a resolved ``ProviderEntry`` plus the
``thinking_level`` the adapter should forward. Mirrors the conveyor project's
per-stage ``(adapter, model, thinking_level)`` profile pattern
(``conveyor/src/config/types.ts:294-310``).

The legacy flat ``workforce.*_model`` knobs are kept as a fallback. When a
route is unset and no ``default_profile`` matches, the resolver returns
``LegacyFallback`` so the existing call sites can keep working without
configuration changes. The one-time deprecation warning is emitted by the
``configured_workforce_providers`` call site (it owns the user-visible
warning); the resolver itself is silent so its behavior is testable in
isolation.

Same-provider detection: when two profiles share the same ``adapter`` and
``model`` the caller (the case ledger / dashboard layer) records
``same_provider_as_creator: true``. ``strict_independence`` enforces a
different provider for any profile whose route key contains
``security_review`` or ``critic``; mismatched provider on
config load raises ``ConfigurationError``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from agency_runtime.core.config import (
    AgencyConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
)
from agency_runtime.core.configuration_contracts import ConfigValidationError

# Route keys whose resolution must use a different provider/model than their
# creator. Sourced from the AR-235 reference doc, §"Same-provider warning".
INDEPENDENCE_ROUTE_TOKENS: Final[frozenset[str]] = frozenset({"critic", "security_review"})

# Default timeout for a profile expressed in milliseconds; the structured
# provider converts to seconds when calling urllib.
_PROFILE_DEFAULT_TIMEOUT_MS: Final[int] = 30_000


@dataclass(frozen=True, slots=True)
class ProfileResolution:
    """Result of resolving a route key to a single profile and provider entry.

    The struct intentionally separates the configured profile (which records
    what the operator asked for) from the materialized ``ProviderEntry`` (which
    the transport layer can use immediately). Callers that need to record
    evidence should keep both: the receipt's ``requested_model`` is the
    profile's configured model; the actual model still comes from the
    response body.
    """

    route_key: str
    profile: InferenceProfile
    provider: ProviderEntry
    thinking_level_configured: str
    thinking_level_consumed: str  # the consumed value after adapter translation


def _profile_to_provider(profile: InferenceProfile) -> ProviderEntry:
    """Project one ``InferenceProfile`` to a runnable ``ProviderEntry``."""

    timeout_seconds = max(0.05, min(60.0, profile.timeout_ms / 1000.0))
    return ProviderEntry(
        name=profile.name or "inference-profile",
        type=profile.adapter,
        transport="",
        model=profile.model,
        base_url=profile.base_url,
        api_key=profile.api_key,
        api_key_env=profile.api_key_env,
        ollama_mode=profile.adapter.strip().casefold() == "ollama",
        timeout=timeout_seconds,
        reasoning_effort=profile.thinking_level,
    )


def _resolve_profile(
    config: AgencyConfig,
    route_key: str,
) -> InferenceProfile | None:
    """Return the profile a route resolves to, or ``None`` when no match.

    Returns ``None`` when:
    - the route key is not present in ``inference.routes`` and no
      ``default_profile`` is configured, or
    - the named profile is missing.

    The caller (typically :func:`resolve` for a strict test or
    :func:`agency_runtime.core.workforce.inference.configured_workforce_providers`
    for production routing) decides whether ``None`` is a config error or
    a signal to fall back to the configured provider chain. The resolver
    itself stays silent so its tests do not need to know about either
    fall-back path.
    """

    inference = config.inference
    if not isinstance(inference, InferenceConfig):
        return None
    profile_name = inference.routes.get(route_key, "")
    if profile_name:
        return inference.profiles.get(profile_name)
    if inference.default_profile:
        return inference.profiles.get(inference.default_profile)
    return None


def translate_thinking_level(
    profile: InferenceProfile,
) -> str:
    """Return the consumed thinking level for the profile's adapter.

    Mirrors the per-adapter mapping in
    ``docs/roadmap/reference-workforce-inference-stages.md`` §"thinking_level
    adapter mapping". The structured provider re-applies this translation at
    transport time; here we project the consumed value so the receipt
    records what was actually forwarded.

    - ``openai-compatible``: ``xhigh`` is recorded as ``"unsupported"`` and
      omitted at call time.
    - ``anthropic``: token budgets are owned by the structured provider; this
      function only records the configured level as consumed.
    - ``ollama`` / ``cli``: recorded and ignored at call time.
    - ``litellm``: passed through as the native ``thinking`` parameter; the
      consumed value matches the configured value.
    """
    if not profile.thinking_level:
        return ""
    adapter = profile.adapter.strip().casefold()
    if adapter == "openai-compatible" and profile.thinking_level == "xhigh":
        return "unsupported"
    return profile.thinking_level


def resolve(
    config: AgencyConfig,
    route_key: str,
) -> ProfileResolution:
    """Resolve one route key to its profile, provider, and consumed thinking level.

    Raises ``ConfigValidationError`` when a route is configured but its named
    profile is missing, or when ``default_profile`` is set but its named
    profile is missing. The resolver stays silent when the route is missing
    entirely and ``default_profile`` is unset — production callers fall back
    to the configured provider chain in that case. Strict-mode callers (e.g.
    test fixtures that pin ``route_key``) want the explicit error; the
    contract is that the route + named profile must agree when both are set.
    """
    inference = config.inference
    if not isinstance(inference, InferenceConfig):
        raise ConfigValidationError(f"inference route {route_key!r}: config.inference is invalid")
    profile_name = inference.routes.get(route_key, "")
    if profile_name:
        if profile_name not in inference.profiles:
            raise ConfigValidationError(
                f"inference route {route_key!r}: profile {profile_name!r} is not defined"
            )
        profile = inference.profiles[profile_name]
    elif inference.default_profile:
        if inference.default_profile not in inference.profiles:
            raise ConfigValidationError(
                f"inference default_profile {inference.default_profile!r}: profile is not defined"
            )
        profile = inference.profiles[inference.default_profile]
    else:
        raise ConfigValidationError(
            f"inference route {route_key!r}: no route and no default_profile "
            "are configured; legacy flat workforce.*_model fallback applies"
        )
    consumed = translate_thinking_level(profile)
    provider = _profile_to_provider(profile)
    return ProfileResolution(
        route_key=route_key,
        profile=profile,
        provider=provider,
        thinking_level_configured=profile.thinking_level,
        thinking_level_consumed=consumed,
    )


def shares_provider_with(
    left: ProfileResolution,
    right: ProfileResolution,
) -> bool:
    """Return True when two resolutions share the same adapter and model."""

    return (
        left.profile.adapter.strip().casefold() == right.profile.adapter.strip().casefold()
        and left.profile.model == right.profile.model
    )


def route_requires_independence(route_key: str) -> bool:
    """Return True when a route key must use a different provider than its creator."""

    if not route_key:
        return False
    tokens = route_key.split(".")
    return any(token in INDEPENDENCE_ROUTE_TOKENS for token in tokens)


def enforce_strict_independence(
    config: AgencyConfig,
    *,
    route_pairs: Mapping[str, str],
) -> None:
    """Raise ``ConfigurationError`` when ``strict_independence`` is on and
    any (independence-required) route shares a provider with its creator.

    ``route_pairs`` maps a critique-style route key to the creator route key
    it must differ from. The call site (the case ledger on a hiring run)
    owns which pairs to pass; this helper is the single enforcement point so
    the dashboard and the case ledger cannot drift.
    """
    inference = config.inference
    if not inference.strict_independence:
        return
    if not isinstance(inference, InferenceConfig):
        return
    offenders: list[str] = []
    for critique_route, creator_route in route_pairs.items():
        if not route_requires_independence(critique_route):
            continue
        try:
            critique = resolve(config, critique_route)
            creator = resolve(config, creator_route)
        except ConfigValidationError:
            # The validation surface (missing route, missing default) is owned
            # by the resolver and the call site; strict-independence is a
            # separate, complementary check that runs only when both sides
            # are resolvable.
            continue
        if shares_provider_with(critique, creator):
            offenders.append(f"{critique_route!r} shares provider/model with {creator_route!r}")
    if offenders:
        raise ConfigValidationError("strict_independence: " + "; ".join(offenders))


__all__ = [
    "INDEPENDENCE_ROUTE_TOKENS",
    "ProfileResolution",
    "enforce_strict_independence",
    "resolve",
    "route_requires_independence",
    "shares_provider_with",
    "translate_thinking_level",
]
