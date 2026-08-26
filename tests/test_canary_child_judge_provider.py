"""Contracts for canary-only, per-harness child-judge provider pins."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agency_runtime.core.canary_judge_provider import (
    CANARY_CHILD_JUDGE_PROVIDER_ENV,
    CanaryChildJudgeProviderError,
    canary_child_judge_config,
    configured_canary_child_judge_provider,
)
from agency_runtime.core.config import (
    AgencyConfig,
    CanaryConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
)
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_schema import validate_config_document
from agency_runtime.core.store.queries import project_routing_decision


def _config(*, requested: str = "codex-subscription") -> AgencyConfig:
    return AgencyConfig(
        providers=(
            ProviderEntry(name="codex-subscription", type="cli", transport="codex"),
            ProviderEntry(name="claude-subscription", type="cli", transport="claude"),
        ),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("claude", requested),),
        ),
    )


def test_canary_pin_resolves_one_exact_cli_provider_and_removes_fallbacks() -> None:
    config = _config()

    resolved = configured_canary_child_judge_provider(config, "CLAUDE")
    assert resolved is not None
    provider, transport = resolved
    assert (provider.name, transport) == ("codex-subscription", "codex")

    narrowed, requested = canary_child_judge_config(
        config,
        "claude",
        {
            "AGENCY_CANARY_MODE": "1",
            CANARY_CHILD_JUDGE_PROVIDER_ENV: "codex-subscription",
        },
    )
    assert requested == "codex-subscription"
    assert narrowed.providers == (provider,)
    assert config.providers != narrowed.providers


def test_canary_pin_mismatch_fails_without_fallback() -> None:
    with pytest.raises(CanaryChildJudgeProviderError, match="does not match"):
        canary_child_judge_config(
            _config(),
            "claude",
            {
                "AGENCY_CANARY_MODE": "1",
                CANARY_CHILD_JUDGE_PROVIDER_ENV: "claude-subscription",
            },
        )

    with pytest.raises(CanaryChildJudgeProviderError, match="no configured pin"):
        canary_child_judge_config(
            AgencyConfig(),
            "claude",
            {"AGENCY_CANARY_MODE": "1"},
        )


def test_zcode_canary_pin_resolves_one_existing_glm_profile_without_chain_mutation() -> None:
    original_chain = (
        ProviderEntry(name="codex-subscription", type="cli", transport="codex"),
        ProviderEntry(name="claude-subscription", type="cli", transport="claude"),
    )
    config = AgencyConfig(
        providers=original_chain,
        inference=InferenceConfig(
            profiles={
                "zcode-recruiter": InferenceProfile(
                    name="zcode-recruiter",
                    adapter="anthropic",
                    model="GLM-5.2",
                    base_url="https://api.z.ai/api/anthropic",
                    api_key="bounded-test-key",
                )
            }
        ),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("zcode", "zcode-recruiter"),),
        ),
    )

    resolved = configured_canary_child_judge_provider(config, "zcode")
    assert resolved is not None
    provider, transport = resolved
    assert transport == ""
    assert (provider.name, provider.type, provider.model) == (
        "zcode-recruiter",
        "anthropic",
        "GLM-5.2",
    )

    narrowed, requested = canary_child_judge_config(
        config,
        "zcode",
        {
            "AGENCY_CANARY_MODE": "1",
            CANARY_CHILD_JUDGE_PROVIDER_ENV: "zcode-recruiter",
        },
    )
    assert requested == "zcode-recruiter"
    assert narrowed.providers == (provider,)
    assert config.providers == original_chain


def test_ar299_canary_pin_resolves_one_keyless_loopback_ollama_profile() -> None:
    original_chain = (ProviderEntry(name="codex-subscription", type="cli", transport="codex"),)
    config = AgencyConfig(
        providers=original_chain,
        inference=InferenceConfig(
            profiles={
                "local-child-judge": InferenceProfile(
                    name="local-child-judge",
                    adapter="ollama",
                    model="mistral-small3.2:24b",
                    base_url="http://127.0.0.1:11434",
                )
            }
        ),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("codex", "local-child-judge"),),
        ),
    )

    resolved = configured_canary_child_judge_provider(config, "CODEX")
    assert resolved is not None
    provider, transport = resolved
    assert transport == ""
    assert (provider.name, provider.type, provider.model, provider.auth_method()) == (
        "local-child-judge",
        "ollama",
        "mistral-small3.2:24b",
        "none",
    )

    narrowed, requested = canary_child_judge_config(
        config,
        "codex",
        {
            "AGENCY_CANARY_MODE": "1",
            CANARY_CHILD_JUDGE_PROVIDER_ENV: "local-child-judge",
        },
    )
    assert requested == "local-child-judge"
    assert narrowed.providers == (provider,)
    assert config.providers == original_chain


def test_canary_pin_rejects_ambiguous_provider_and_profile_name() -> None:
    config = AgencyConfig(
        providers=(ProviderEntry(name="shared", type="cli", transport="codex"),),
        inference=InferenceConfig(
            profiles={
                "shared": InferenceProfile(
                    name="shared",
                    adapter="anthropic",
                    model="GLM-5.2",
                    base_url="https://api.z.ai/api/anthropic",
                    api_key="bounded-test-key",
                )
            }
        ),
        canary=CanaryConfig(child_judge_provider_by_host=(("zcode", "shared"),)),
    )

    with pytest.raises(CanaryChildJudgeProviderError, match="resolve exactly once"):
        configured_canary_child_judge_provider(config, "zcode")


@pytest.mark.parametrize(
    "profile",
    [
        InferenceProfile(
            name="unsupported-profile",
            adapter="openai-compatible",
            model="glm-test",
            base_url="https://example.invalid/v1",
            api_key="bounded-test-key",
        ),
        InferenceProfile(
            name="unsupported-profile",
            adapter="anthropic",
            model="GLM-5.2",
            base_url="https://api.z.ai/api/anthropic",
        ),
        InferenceProfile(
            name="unsupported-profile",
            adapter="anthropic",
            model="GLM-5.2",
            base_url="http://api.example.invalid/v1",
            api_key="bounded-test-key",
        ),
        InferenceProfile(
            name="unsupported-profile",
            adapter="ollama",
            model="mistral-small3.2:24b",
            base_url="http://api.example.invalid",
        ),
    ],
)
def test_canary_pin_rejects_unsupported_or_unavailable_inference_profile(
    profile: InferenceProfile,
) -> None:
    config = AgencyConfig(
        inference=InferenceConfig(profiles={"unsupported-profile": profile}),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("zcode", "unsupported-profile"),),
        ),
    )

    with pytest.raises(CanaryChildJudgeProviderError, match="not supported or available"):
        configured_canary_child_judge_provider(config, "zcode")


def test_noncanary_staffing_ignores_the_canary_map() -> None:
    config = _config()

    unchanged, requested = canary_child_judge_config(config, "claude", {})

    assert unchanged is config
    assert requested == ""


def test_pin_rejects_missing_or_unsupported_provider_transport() -> None:
    with pytest.raises(CanaryChildJudgeProviderError, match="resolve exactly once"):
        configured_canary_child_judge_provider(_config(requested="missing"), "claude")

    direct = replace(
        _config(requested="glm-api"),
        providers=(
            ProviderEntry(
                name="glm-api",
                type="openai-compatible",
                base_url="https://example.invalid/v1",
                api_key="secret",
            ),
        ),
    )
    with pytest.raises(CanaryChildJudgeProviderError, match="supported CLI transport"):
        configured_canary_child_judge_provider(direct, "claude")


def test_canary_mapping_schema_normalizes_hosts_and_rejects_invalid_text() -> None:
    validated = validate_config_document(
        {
            "canary": {
                "child_judge_provider_by_host": {
                    "CLAUDE": "codex-subscription",
                    "zcode": "glm-subscription",
                },
                "accepted_outcome_parent_recruiter_provider_by_host": {
                    "CLAUDE": "codex-subscription",
                },
            }
        }
    )
    assert validated["canary"]["child_judge_provider_by_host"] == {
        "claude": "codex-subscription",
        "zcode": "glm-subscription",
    }
    assert validated["canary"]["accepted_outcome_parent_recruiter_provider_by_host"] == {
        "claude": "codex-subscription",
    }

    with pytest.raises(ConfigValidationError, match="host names must be one of"):
        validate_config_document(
            {"canary": {"child_judge_provider_by_host": {"unknown": "provider"}}}
        )
    with pytest.raises(ConfigValidationError, match="contains invalid text"):
        validate_config_document(
            {"canary": {"child_judge_provider_by_host": {"claude": "bad\x1b[31m"}}}
        )


def test_routing_projection_keeps_requested_and_answering_provider_separate() -> None:
    projected, _work_units, _source = project_routing_decision(
        {
            "status": "applied",
            "source": "native_child_inference",
            "requested_provider": "codex-subscription",
            "provider": "codex-subscription (cli:codex)",
        }
    )

    assert projected["requested_provider"] == "codex-subscription"
    assert projected["provider"] == "codex-subscription (cli:codex)"
