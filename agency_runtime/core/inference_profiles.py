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


def provider_from_profile(profile: InferenceProfile) -> ProviderEntry:
    """Project one ``InferenceProfile`` to a runnable ``ProviderEntry``."""

    timeout_seconds = max(0.05, min(120.0, profile.timeout_ms / 1000.0))
    adapter = profile.adapter.strip().casefold()
    transport = profile.transport.strip().casefold() if adapter == "cli" else ""
    # The codex CLI forwards thinking as model_reasoning_effort; the claude CLI
    # has no per-call thinking flag and rejects a non-empty effort, so its
    # configured level is recorded but never forwarded.
    reasoning_effort = "" if transport == "claude" else profile.thinking_level
    return ProviderEntry(
        name=profile.name or "inference-profile",
        type=profile.adapter,
        transport=transport,
        model=profile.model,
        base_url=profile.base_url,
        api_key=profile.api_key,
        api_key_env=profile.api_key_env,
        ollama_mode=adapter == "ollama",
        timeout=timeout_seconds,
        reasoning_effort=reasoning_effort,
        dimensions=profile.dimensions,
    )


def _named_profile(
    config: AgencyConfig,
    route_key: str,
    harness: str,
) -> tuple[str, str]:
    """Return ``(profile_name, origin)`` for a route, or ``("", "")``.

    Precedence: harness routes -> harness default_profile -> global routes ->
    global default_profile. A harness section only participates when the
    caller supplies a harness that has a configured section, so installs
    without harness sections behave exactly as before. ``origin`` names the
    table that supplied the profile ("route" or "default_profile", with a
    harness prefix when harness-scoped) so error messages stay exact.
    """

    inference = config.inference
    if not isinstance(inference, InferenceConfig):
        return "", ""
    harness_key = harness.strip().casefold()
    harness_config = inference.harnesses.get(harness_key) if harness_key else None
    if harness_config is not None:
        if name := harness_config.routes.get(route_key, ""):
            return name, f"harnesses.{harness_key}.routes"
        if harness_config.default_profile:
            return harness_config.default_profile, f"harnesses.{harness_key}.default_profile"
    if name := inference.routes.get(route_key, ""):
        return name, "route"
    return inference.default_profile, "default_profile" if inference.default_profile else ""


def _resolve_profile(
    config: AgencyConfig,
    route_key: str,
    harness: str = "",
) -> InferenceProfile | None:
    """Return the profile a route resolves to, or ``None`` when no match.

    Returns ``None`` when:
    - the route key is not present in any participating route table and no
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
    profile_name, _ = _named_profile(config, route_key, harness)
    if profile_name:
        return inference.profiles.get(profile_name)
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
    - ``cli`` + ``codex`` transport: forwarded as ``model_reasoning_effort``.
    - ``cli`` + ``claude`` transport: recorded as ``"unsupported"`` — the
      claude CLI has no per-call thinking control, so a configured level is
      never forwarded.
    - ``ollama``: recorded and ignored at call time.
    - ``litellm``: forwarded as the standardized ``reasoning_effort``
      parameter so LiteLLM can translate it for the routed provider/model; the
      consumed value matches the configured value.
    """
    if not profile.thinking_level:
        return ""
    adapter = profile.adapter.strip().casefold()
    if adapter == "openai-compatible" and profile.thinking_level == "xhigh":
        return "unsupported"
    if adapter == "cli" and profile.transport.strip().casefold() == "claude":
        return "unsupported"
    return profile.thinking_level


def resolve(
    config: AgencyConfig,
    route_key: str,
    harness: str = "",
) -> ProfileResolution:
    """Resolve one route key to its profile, provider, and consumed thinking level.

    ``harness`` scopes resolution to that harness's route section when one is
    configured; unresolved keys fall through to the global routes and default.

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
    profile_name, origin = _named_profile(config, route_key, harness)
    if profile_name:
        if profile_name not in inference.profiles:
            if origin.endswith("default_profile"):
                raise ConfigValidationError(
                    f"inference {origin} {profile_name!r}: profile is not defined"
                )
            raise ConfigValidationError(
                f"inference route {route_key!r}: profile {profile_name!r} is not defined"
            )
        profile = inference.profiles[profile_name]
    else:
        raise ConfigValidationError(
            f"inference route {route_key!r}: no route and no default_profile "
            "are configured; legacy flat workforce.*_model fallback applies"
        )
    consumed = translate_thinking_level(profile)
    provider = provider_from_profile(profile)
    return ProfileResolution(
        route_key=route_key,
        profile=profile,
        provider=provider,
        thinking_level_configured=profile.thinking_level,
        thinking_level_consumed=consumed,
    )


def resolve_content_fallback(
    config: AgencyConfig,
    route_key: str,
) -> ProfileResolution | None:
    """Resolve the optional content-fallback profile for one route key.

    A content fallback exists for completions that succeed at the transport
    but fail the stage's structured contract: the router-level order-2
    fallback only observes transport failures, so a 200-with-invalid-content
    primary would otherwise end the stage under the zero-retry doctrine. The
    mapping is global and deliberately not harness-scoped; it names one
    profile that the stage loop tries after the primary's content is
    rejected. Returns ``None`` when no fallback is configured for the key,
    and raises ``ConfigValidationError`` when the mapping names a profile
    that is not defined.
    """

    inference = config.inference
    if not isinstance(inference, InferenceConfig):
        return None
    profile_name = inference.content_fallback_routes.get(route_key, "").strip()
    if not profile_name:
        return None
    profile = inference.profiles.get(profile_name)
    if profile is None:
        raise ConfigValidationError(
            f"inference content_fallback_routes {route_key!r}: "
            f"profile {profile_name!r} is not defined"
        )
    return ProfileResolution(
        route_key=route_key,
        profile=profile,
        provider=provider_from_profile(profile),
        thinking_level_configured=profile.thinking_level,
        thinking_level_consumed=translate_thinking_level(profile),
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


def resolve_explicit_capability_route(
    config: AgencyConfig,
    route_key: str,
    *,
    capability_class: str,
    harness: str = "",
) -> ProfileResolution | None:
    """Resolve only an explicitly mapped capability route.

    Optional capability-specific payloads must never inherit a harness or
    global ``default_profile``. In particular, embedding inputs must not be
    sent to a generic text model merely because one is the default.
    """

    return resolve_explicit_capability_route_any(
        config,
        route_key,
        capability_classes=(capability_class,),
        harness=harness,
    )


def resolve_explicit_capability_route_any(
    config: AgencyConfig,
    route_key: str,
    *,
    capability_classes: tuple[str, ...],
    harness: str = "",
) -> ProfileResolution | None:
    """Resolve an explicit route that accepts one of several capabilities."""

    inference = config.inference
    if not isinstance(inference, InferenceConfig):
        raise ConfigValidationError(f"inference route {route_key!r}: config.inference is invalid")
    harness_key = harness.strip().casefold()
    harness_config = inference.harnesses.get(harness_key) if harness_key else None
    profile_name = ""
    origin = ""
    if harness_config is not None and route_key in harness_config.routes:
        profile_name = harness_config.routes[route_key]
        origin = f"harnesses.{harness_key}.routes"
    elif route_key in inference.routes:
        profile_name = inference.routes[route_key]
        origin = "routes"
    if not profile_name:
        return None
    profile = inference.profiles.get(profile_name)
    if profile is None:
        raise ConfigValidationError(
            f"inference {origin} route {route_key!r}: profile {profile_name!r} is not defined"
        )
    required = tuple(
        dict.fromkeys(item.strip().casefold() for item in capability_classes if item.strip())
    )
    actual = profile.capability_class.strip().casefold()
    if not required or actual not in required:
        expected = " or ".join(repr(item) for item in sorted(required))
        raise ConfigValidationError(
            f"inference route {route_key!r}: profile {profile_name!r} must declare "
            f"capability_class {expected}"
        )
    return ProfileResolution(
        route_key=route_key,
        profile=profile,
        provider=provider_from_profile(profile),
        thinking_level_configured=profile.thinking_level,
        thinking_level_consumed=translate_thinking_level(profile),
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
    "provider_from_profile",
    "resolve",
    "resolve_content_fallback",
    "resolve_explicit_capability_route",
    "route_requires_independence",
    "shares_provider_with",
    "translate_thinking_level",
]
