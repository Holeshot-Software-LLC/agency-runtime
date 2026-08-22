"""Per-stage inference profile schema, route resolution, and thinking-level tests.

ADR-0153 / AR-235 §3. Covers:

- route -> profile resolution
- default-profile fallback
- missing route + no default -> config error
- route references undefined profile -> config error
- invalid ``adapter`` value -> config error
- both ``api_key`` and ``api_key_env`` set -> config error
- ``thinking_level`` mapping per-adapter (5 adapters x 4 levels)
- unsupported ``thinking_level`` records ``"unsupported"`` in receipt
- default_profile + no route_key returns the default profile
"""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    HarnessInferenceConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
    WorkforceConfig,
)
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_schema import validate_config_document
from agency_runtime.core.inference_profiles import (
    INDEPENDENCE_ROUTE_TOKENS,
    ProfileResolution,
    enforce_strict_independence,
    resolve,
    route_requires_independence,
    shares_provider_with,
    translate_thinking_level,
)
from agency_runtime.core.structured_provider import (
    StructuredProviderResult,
    translate_thinking_level_for_adapter,
)
from agency_runtime.core.workforce.inference import configured_workforce_providers


def _profile(
    name: str,
    *,
    adapter: str = "litellm",
    model: str = "default-model",
    thinking_level: str = "",
    base_url: str = "https://router.example.test/v1",
    api_key_env: str = "ROUTER_KEY",
    api_key: str = "",
    capability_class: str = "",
    timeout_ms: int = 30_000,
) -> InferenceProfile:
    return InferenceProfile(
        name=name,
        adapter=adapter,
        model=model,
        thinking_level=thinking_level,
        base_url=base_url,
        api_key=api_key,
        api_key_env=api_key_env,
        capability_class=capability_class,
        timeout_ms=timeout_ms,
    )


def _config(
    profiles: dict[str, InferenceProfile] | None = None,
    routes: dict[str, str] | None = None,
    *,
    default_profile: str = "",
    strict_independence: bool = False,
) -> AgencyConfig:
    return AgencyConfig(
        providers=(
            ProviderEntry(
                name="fallback",
                type="litellm",
                model="fallback-model",
                base_url="https://fallback.example.test/v1",
                api_key="fallback",
            ),
        ),
        workforce=WorkforceConfig(),
        inference=InferenceConfig(
            default_profile=default_profile,
            strict_independence=strict_independence,
            routes=routes or {},
            profiles=profiles or {},
        ),
    )


# ── Schema validation ───────────────────────────────────────────────


def test_schema_rejects_invalid_adapter_value() -> None:
    document = {
        "inference": {
            "default_profile": "agency-default",
            "routes": {"workforce.hiring": "agency-default"},
            "profiles": {
                "agency-default": {
                    "adapter": "gpt-9000",  # invalid
                    "model": "x",
                    "thinking_level": "low",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(
        ConfigValidationError, match=r"inference\.profiles\.agency-default\.adapter"
    ):
        validate_config_document(document)


def test_schema_rejects_both_api_key_and_api_key_env() -> None:
    document = {
        "inference": {
            "default_profile": "agency-default",
            "routes": {"workforce.hiring": "agency-default"},
            "profiles": {
                "agency-default": {
                    "adapter": "openai-compatible",
                    "model": "x",
                    "thinking_level": "low",
                    "base_url": "https://router.example.test/v1",
                    "api_key": "literal",
                    "api_key_env": "ENV_VAR",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match="mutually exclusive"):
        validate_config_document(document)


def test_schema_rejects_route_referencing_undefined_profile() -> None:
    document = {
        "inference": {
            "default_profile": "",
            "routes": {"workforce.hiring": "agency-missing"},
            "profiles": {
                "agency-default": {
                    "adapter": "litellm",
                    "model": "x",
                    "thinking_level": "low",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match="routes reference undefined profile"):
        validate_config_document(document)


def test_schema_rejects_default_profile_pointing_at_missing_profile() -> None:
    document = {
        "inference": {
            "default_profile": "agency-missing",
            "routes": {},
            "profiles": {
                "agency-default": {
                    "adapter": "litellm",
                    "model": "x",
                    "thinking_level": "low",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match="default_profile"):
        validate_config_document(document)


def test_schema_rejects_invalid_thinking_level() -> None:
    document = {
        "inference": {
            "default_profile": "agency-default",
            "routes": {"workforce.hiring": "agency-default"},
            "profiles": {
                "agency-default": {
                    "adapter": "litellm",
                    "model": "x",
                    "thinking_level": "ultra",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match="thinking_level"):
        validate_config_document(document)


def test_schema_rejects_invalid_route_key_pattern() -> None:
    document = {
        "inference": {
            "default_profile": "",
            "routes": {"Hiring": "agency-default"},
            "profiles": {
                "agency-default": {
                    "adapter": "litellm",
                    "model": "x",
                    "thinking_level": "low",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match=r"inference\.routes"):
        validate_config_document(document)


# ── Route resolution ────────────────────────────────────────────────


def test_route_resolves_to_named_profile() -> None:
    hiring = _profile("agency-hiring", model="hiring-model", thinking_level="low")
    config = _config(
        profiles={"agency-hiring": hiring},
        routes={"workforce.hiring": "agency-hiring"},
    )

    resolution = resolve(config, "workforce.hiring")

    assert isinstance(resolution, ProfileResolution)
    assert resolution.route_key == "workforce.hiring"
    assert resolution.profile is hiring
    assert resolution.provider.model == "hiring-model"
    assert resolution.thinking_level_configured == "low"
    assert resolution.thinking_level_consumed == "low"


def test_default_profile_fallback_when_route_is_missing() -> None:
    default = _profile("agency-default", model="default-model", thinking_level="medium")
    config = _config(
        profiles={"agency-default": default},
        default_profile="agency-default",
    )

    resolution = resolve(config, "workforce.recruiter")

    assert resolution.profile is default
    assert resolution.provider.model == "default-model"


def test_missing_route_with_no_default_raises_config_error() -> None:
    config = _config(profiles={}, default_profile="")

    with pytest.raises(ConfigValidationError, match="no route and no default_profile"):
        resolve(config, "workforce.hiring")


def test_route_references_undefined_profile_raises_config_error() -> None:
    # The schema validator catches this at config load; the resolver also
    # guards in case the resolver is called with a profile that was
    # removed between load and resolve (e.g. in a unit test).
    config = _config(
        profiles={},
        routes={"workforce.hiring": "agency-missing"},
    )

    with pytest.raises(ConfigValidationError, match="profile 'agency-missing' is not defined"):
        resolve(config, "workforce.hiring")


def test_default_profile_references_undefined_profile_raises_config_error() -> None:
    config = _config(
        profiles={},
        default_profile="agency-missing",
    )

    with pytest.raises(ConfigValidationError, match="default_profile"):
        resolve(config, "workforce.recruiter")


# ── Thinking-level translation ──────────────────────────────────────


@pytest.mark.parametrize(
    ("adapter", "level"),
    [
        ("openai-compatible", "low"),
        ("openai-compatible", "medium"),
        ("openai-compatible", "high"),
        ("anthropic", "low"),
        ("anthropic", "medium"),
        ("anthropic", "high"),
        ("anthropic", "xhigh"),
        ("ollama", "low"),
        ("ollama", "xhigh"),
        ("litellm", "low"),
        ("litellm", "high"),
        ("cli", "xhigh"),
    ],
)
def test_translate_thinking_level_per_adapter(adapter: str, level: str) -> None:
    profile = _profile("p", adapter=adapter, thinking_level=level)
    translated = translate_thinking_level(profile)

    assert translated in {"low", "medium", "high", "xhigh", "unsupported", ""}


@pytest.mark.parametrize(
    ("adapter", "level", "expected"),
    [
        ("openai-compatible", "low", "low"),
        ("openai-compatible", "medium", "medium"),
        ("openai-compatible", "high", "high"),
        ("openai-compatible", "xhigh", "unsupported"),
        ("anthropic", "low", "low"),
        ("anthropic", "medium", "medium"),
        ("anthropic", "high", "high"),
        ("anthropic", "xhigh", "xhigh"),
        ("ollama", "low", "low"),
        ("ollama", "xhigh", "xhigh"),
        ("litellm", "low", "low"),
        ("litellm", "high", "high"),
        ("cli", "low", "low"),
        ("cli", "xhigh", "xhigh"),
    ],
)
def test_translate_thinking_level_for_adapter_specific(
    adapter: str, level: str, expected: str
) -> None:
    profile = _profile("p", adapter=adapter, thinking_level=level)
    assert translate_thinking_level(profile) == expected
    # Public adapter (structured_provider module) must agree with the
    # inference_profiles translation. Both surface the same consumed value.
    assert translate_thinking_level_for_adapter(adapter, level) == expected


def test_translate_thinking_level_empty_returns_empty() -> None:
    profile = _profile("p", adapter="anthropic", thinking_level="")
    assert translate_thinking_level(profile) == ""


def test_unsupported_thinking_level_records_unsupported_in_receipt() -> None:
    result = StructuredProviderResult(
        value={"ok": True},
        provider_name="router",
        provider_type="openai-compatible",
        transport="",
        requested_model="x",
        model_group="",
        actual_model="x",
        model_receipt_source="response.body.model",
        latency_ms=10,
        thinking_level_configured="xhigh",
        thinking_level_consumed="unsupported",
    )

    receipt = result.receipt()
    assert receipt["thinking_level_configured"] == "xhigh"
    assert receipt["thinking_level_consumed"] == "unsupported"


def test_anthropic_thinking_budgets_record_configured_and_consumed() -> None:
    # The structured provider records the configured value verbatim and the
    # consumed value as the same level for anthropic (the budget mapping is
    # applied to the request payload, not the receipt).
    result = StructuredProviderResult(
        value={"ok": True},
        provider_name="anthropic-router",
        provider_type="anthropic",
        transport="",
        requested_model="claude-x",
        model_group="",
        actual_model="claude-x-2026-07-12",
        model_receipt_source="response.body.model",
        latency_ms=12,
        thinking_level_configured="high",
        thinking_level_consumed="high",
    )
    assert result.receipt()["thinking_level_consumed"] == "high"


# ── Independence detection ──────────────────────────────────────────


def test_route_requires_independence_for_security_review_and_critic() -> None:
    assert route_requires_independence("workforce.hiring.security_review") is True
    assert route_requires_independence("workforce.hiring.critic") is True
    assert route_requires_independence("workforce.recruiter.critic") is True
    assert route_requires_independence("workforce.hiring") is False
    assert route_requires_independence("workforce.planner") is False
    assert route_requires_independence("") is False
    assert frozenset({"critic", "security_review"}) == INDEPENDENCE_ROUTE_TOKENS


def test_shares_provider_with_detects_same_adapter_and_model() -> None:
    config = _config(
        profiles={
            "a": _profile("a", adapter="litellm", model="x"),
            "b": _profile("b", adapter="litellm", model="x"),
        },
        routes={"workforce.hiring": "a", "workforce.hiring.critic": "b"},
    )
    a = resolve(config, "workforce.hiring")
    b = resolve(config, "workforce.hiring.critic")
    assert shares_provider_with(a, b) is True

    config_b = _config(
        profiles={
            "a": _profile("a", adapter="litellm", model="x"),
            "b": _profile("b", adapter="anthropic", model="y"),
        },
        routes={"workforce.hiring": "a", "workforce.hiring.critic": "b"},
    )
    a = resolve(config_b, "workforce.hiring")
    b = resolve(config_b, "workforce.hiring.critic")
    assert shares_provider_with(a, b) is False


def test_strict_independence_raises_when_critic_shares_provider_with_creator() -> None:
    config = _config(
        profiles={
            "hiring": _profile("hiring", adapter="litellm", model="x"),
            "critic": _profile("critic", adapter="litellm", model="x"),
        },
        routes={"workforce.hiring": "hiring", "workforce.hiring.critic": "critic"},
        strict_independence=True,
    )

    with pytest.raises(ConfigValidationError, match="strict_independence"):
        enforce_strict_independence(
            config,
            route_pairs={"workforce.hiring.critic": "workforce.hiring"},
        )


def test_strict_independence_passes_when_provider_differs() -> None:
    config = _config(
        profiles={
            "hiring": _profile("hiring", adapter="litellm", model="x"),
            "critic": _profile("critic", adapter="anthropic", model="y"),
        },
        routes={"workforce.hiring": "hiring", "workforce.hiring.critic": "critic"},
        strict_independence=True,
    )

    enforce_strict_independence(
        config,
        route_pairs={"workforce.hiring.critic": "workforce.hiring"},
    )


def test_strict_independence_disabled_allows_same_provider() -> None:
    config = _config(
        profiles={
            "hiring": _profile("hiring", adapter="litellm", model="x"),
            "critic": _profile("critic", adapter="litellm", model="x"),
        },
        routes={"workforce.hiring": "hiring", "workforce.hiring.critic": "critic"},
        strict_independence=False,
    )

    # Same provider is allowed when strict_independence is off. The case
    # ledger / dashboard layer will record same_provider_as_creator=true.
    enforce_strict_independence(
        config,
        route_pairs={"workforce.hiring.critic": "workforce.hiring"},
    )


def test_strict_independence_skips_pairs_outside_independence_routes() -> None:
    config = _config(
        profiles={
            "planner": _profile("planner", adapter="litellm", model="x"),
            "recruiter": _profile("recruiter", adapter="litellm", model="x"),
        },
        routes={"workforce.planner": "planner", "workforce.recruiter": "recruiter"},
        strict_independence=True,
    )

    # planner/recruiter do not require independence. Same provider is
    # allowed even when strict_independence is on.
    enforce_strict_independence(
        config,
        route_pairs={"workforce.recruiter": "workforce.planner"},
    )


# ── Default-profile fallback (no legacy knobs in this slice) ─────────


def test_default_profile_fallback_when_called_without_route_key() -> None:
    config = AgencyConfig(
        inference=InferenceConfig(
            default_profile="agency-default",
            profiles={"agency-default": _profile("agency-default", model="default-model")},
        ),
    )

    providers = configured_workforce_providers(config, stage="planner")
    assert [item.model for item in providers] == ["default-model"]


def test_no_route_no_default_falls_back_to_legacy_judge_provider() -> None:
    # When neither the routes block nor the default_profile is set, the
    # historical judge provider is the final fallback. This keeps the
    # dashboard / CLI evals that pre-date the inference block working.
    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="primary",
                type="litellm",
                model="primary-model",
                base_url="https://router.example.test/v1",
                api_key="k",
            ),
        ),
    )

    providers = configured_workforce_providers(config, stage="planner")
    assert [item.model for item in providers] == ["primary-model"]


# ── Provider projection ─────────────────────────────────────────────


def test_profile_projects_to_provider_with_timeout_in_seconds() -> None:
    profile = _profile("p", model="x", timeout_ms=45_000)
    config = _config(profiles={"p": profile}, routes={"workforce.hiring": "p"})

    resolution = resolve(config, "workforce.hiring")

    assert resolution.provider.timeout == pytest.approx(45.0)
    assert resolution.provider.reasoning_effort == ""
    assert resolution.provider.ollama_mode is False


def test_litellm_profile_projects_opaque_alias_and_reasoning_effort() -> None:
    profile = _profile(
        "router",
        adapter="litellm",
        model="task-agency-router",
        thinking_level="high",
        base_url="http://127.0.0.1:4000/v1",
    )
    config = _config(profiles={"router": profile}, routes={"workforce.planner": "router"})

    resolution = resolve(config, "workforce.planner")

    assert resolution.provider.type == "litellm"
    assert resolution.provider.model == "task-agency-router"
    assert resolution.provider.reasoning_effort == "high"
    assert resolution.thinking_level_consumed == "high"


def test_ollama_profile_sets_ollama_mode() -> None:
    profile = _profile(
        "p",
        adapter="ollama",
        model="qwen3.5:2b",
        base_url="http://127.0.0.1:11434",
        api_key_env="",
        api_key="",
    )
    config = _config(profiles={"p": profile}, routes={"workforce.hiring": "p"})

    resolution = resolve(config, "workforce.hiring")

    assert resolution.provider.ollama_mode is True
    assert resolution.provider.base_url == "http://127.0.0.1:11434"


# ── AgencyConfig round-trip ─────────────────────────────────────────


def test_agency_config_inference_defaults_round_trip() -> None:
    config = AgencyConfig()

    assert isinstance(config.inference, InferenceConfig)
    assert config.inference.default_profile == ""
    assert config.inference.routes == {}
    assert config.inference.profiles == {}
    assert config.inference.strict_independence is False


def test_agency_config_serializes_inference_block() -> None:
    from agency_runtime.core.config import config_to_yaml

    config = _config(
        profiles={"agency-hiring": _profile("agency-hiring", model="h")},
        routes={"workforce.hiring": "agency-hiring"},
    )
    rendered = config_to_yaml(config)
    parsed: dict[str, Any] = {}
    import yaml

    parsed = yaml.safe_load(rendered)  # type: ignore[assignment]

    inference = parsed["inference"]
    assert inference["routes"] == {"workforce.hiring": "agency-hiring"}
    assert "agency-hiring" in inference["profiles"]
    assert inference["profiles"]["agency-hiring"]["model"] == "h"


def test_legacy_default_config_yaml_loads_with_inference_block() -> None:
    import yaml

    from agency_runtime.core.config import _BUNDLED_DEFAULTS, _dict_to_config

    text = _BUNDLED_DEFAULTS.read_text(encoding="utf-8")
    parsed = yaml.safe_load(text) or {}
    config = _dict_to_config(parsed, config_path="")

    assert "agency-hiring" in config.inference.profiles
    assert "workforce.hiring" in config.inference.routes
    assert config.inference.routes["workforce.hiring"] == "agency-hiring"
    assert config.inference.profiles["agency-hiring"].thinking_level == "low"
    assert config.inference.profiles["agency-security"].thinking_level == "high"
    assert config.inference.profiles["agency-default"].model == "gpt5.6-luna"


# ── Harness-scoped routing + CLI transport profiles (per-harness configs) ──


def _harness_config(
    profiles: dict[str, InferenceProfile],
    *,
    routes: dict[str, str] | None = None,
    default_profile: str = "",
    harnesses: dict[str, HarnessInferenceConfig] | None = None,
) -> AgencyConfig:
    return AgencyConfig(
        providers=(
            ProviderEntry(
                name="fallback",
                type="litellm",
                model="fallback-model",
                base_url="https://fallback.example.test/v1",
                api_key="fallback",
            ),
        ),
        workforce=WorkforceConfig(),
        inference=InferenceConfig(
            default_profile=default_profile,
            routes=routes or {},
            profiles=profiles,
            harnesses=harnesses or {},
        ),
    )


def _cli_profile(
    name: str, *, transport: str, model: str, thinking_level: str = ""
) -> InferenceProfile:
    return InferenceProfile(
        name=name,
        adapter="cli",
        model=model,
        thinking_level=thinking_level,
        transport=transport,
    )


def test_cli_codex_profile_projects_transport_and_effort() -> None:
    config = _harness_config(
        {
            "codex-fast": _cli_profile(
                "codex-fast", transport="codex", model="gpt-x", thinking_level="low"
            )
        },
        routes={"workforce.planner": "codex-fast"},
    )
    provider = resolve(config, "workforce.planner").provider

    assert provider.type == "cli"
    assert provider.transport == "codex"
    assert provider.reasoning_effort == "low"


def test_cli_claude_profile_never_forwards_thinking() -> None:
    profile = _cli_profile(
        "claude-fast", transport="claude", model="haiku", thinking_level="medium"
    )
    config = _harness_config({"claude-fast": profile}, routes={"workforce.planner": "claude-fast"})
    provider = resolve(config, "workforce.planner").provider

    assert provider.transport == "claude"
    assert provider.reasoning_effort == ""
    assert translate_thinking_level(profile) == "unsupported"


def test_harness_routes_take_precedence_over_global() -> None:
    config = _harness_config(
        {
            "global-p": _profile("global-p"),
            "claude-p": _cli_profile("claude-p", transport="claude", model="haiku"),
        },
        routes={"workforce.recruiter": "global-p"},
        harnesses={
            "claude": HarnessInferenceConfig(routes={"workforce.recruiter": "claude-p"}),
        },
    )

    assert resolve(config, "workforce.recruiter", harness="claude").profile.name == "claude-p"
    assert resolve(config, "workforce.recruiter").profile.name == "global-p"


def test_harness_default_profile_beats_global_routes() -> None:
    # A harness section is a complete staffing override for that harness: its
    # default wins over a global route so a harness never silently staffs
    # from another harness's subscription.
    config = _harness_config(
        {
            "global-p": _profile("global-p"),
            "claude-p": _cli_profile("claude-p", transport="claude", model="haiku"),
        },
        routes={"workforce.recruiter": "global-p"},
        harnesses={"claude": HarnessInferenceConfig(default_profile="claude-p")},
    )

    assert resolve(config, "workforce.recruiter", harness="claude").profile.name == "claude-p"


def test_unknown_harness_falls_through_to_global() -> None:
    config = _harness_config(
        {"global-p": _profile("global-p")},
        routes={"workforce.recruiter": "global-p"},
        harnesses={"claude": HarnessInferenceConfig(default_profile="global-p")},
    )

    assert resolve(config, "workforce.recruiter", harness="hermes").profile.name == "global-p"


def test_configured_workforce_providers_uses_harness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENCY_INFERENCE_HARNESS", raising=False)
    config = _harness_config(
        {
            "claude-p": _cli_profile("claude-p", transport="claude", model="haiku"),
            "codex-p": _cli_profile("codex-p", transport="codex", model="gpt-x"),
        },
        harnesses={
            "claude": HarnessInferenceConfig(default_profile="claude-p"),
            "codex": HarnessInferenceConfig(default_profile="codex-p"),
        },
    )

    claude = configured_workforce_providers(
        config, stage="recruiter", route_key="workforce.recruiter", harness="claude"
    )
    codex = configured_workforce_providers(
        config, stage="recruiter", route_key="workforce.recruiter", harness="codex"
    )
    none = configured_workforce_providers(
        config, stage="recruiter", route_key="workforce.recruiter"
    )

    assert [p.name for p in claude] == ["claude-p"]
    assert [p.name for p in codex] == ["codex-p"]
    assert [p.name for p in none] == ["fallback"]


def test_env_override_selects_harness_for_unknown_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _harness_config(
        {"claude-p": _cli_profile("claude-p", transport="claude", model="haiku")},
        harnesses={"claude": HarnessInferenceConfig(default_profile="claude-p")},
    )
    monkeypatch.setenv("AGENCY_INFERENCE_HARNESS", "claude")

    chain = configured_workforce_providers(
        config, stage="recruiter", route_key="workforce.recruiter", harness="unknown"
    )

    assert [p.name for p in chain] == ["claude-p"]


def test_schema_accepts_cli_transport_and_harness_sections() -> None:
    document = {
        "inference": {
            "profiles": {
                "claude-fast": {"adapter": "cli", "transport": "claude", "model": "haiku"},
                "codex-fast": {
                    "adapter": "cli",
                    "transport": "codex",
                    "model": "gpt-x",
                    "thinking_level": "low",
                },
            },
            "harnesses": {
                "claude": {"default_profile": "claude-fast"},
                "codex": {
                    "default_profile": "codex-fast",
                    "routes": {"workforce.recruiter.critic": "codex-fast"},
                },
            },
        }
    }

    validated = validate_config_document(document)["inference"]

    assert validated["profiles"]["claude-fast"]["transport"] == "claude"
    assert validated["harnesses"]["claude"]["default_profile"] == "claude-fast"
    assert validated["harnesses"]["codex"]["routes"] == {"workforce.recruiter.critic": "codex-fast"}


def test_schema_rejects_cli_profile_without_transport() -> None:
    document = {
        "inference": {
            "profiles": {"bad": {"adapter": "cli", "model": "haiku"}},
        }
    }

    with pytest.raises(ConfigValidationError, match=r"inference\.profiles\.bad\.transport"):
        validate_config_document(document)


def test_schema_rejects_transport_on_http_profile() -> None:
    document = {
        "inference": {
            "profiles": {
                "bad": {
                    "adapter": "litellm",
                    "transport": "claude",
                    "model": "alias",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
        }
    }

    with pytest.raises(ConfigValidationError, match=r"inference\.profiles\.bad\.transport"):
        validate_config_document(document)


def test_schema_rejects_unknown_harness_name() -> None:
    document = {
        "inference": {
            "profiles": {
                "p": {
                    "adapter": "litellm",
                    "model": "alias",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
            "harnesses": {"vscode": {"default_profile": "p"}},
        }
    }

    with pytest.raises(ConfigValidationError, match=r"inference\.harnesses"):
        validate_config_document(document)


def test_schema_rejects_harness_route_to_undefined_profile() -> None:
    document = {
        "inference": {
            "profiles": {
                "p": {
                    "adapter": "litellm",
                    "model": "alias",
                    "base_url": "https://router.example.test/v1",
                    "api_key_env": "ROUTER_KEY",
                }
            },
            "harnesses": {"claude": {"routes": {"workforce.recruiter": "ghost"}}},
        }
    }

    with pytest.raises(ConfigValidationError, match=r"inference\.harnesses\.claude\.routes"):
        validate_config_document(document)
