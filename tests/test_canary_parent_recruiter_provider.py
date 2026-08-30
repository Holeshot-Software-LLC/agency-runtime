"""Contracts for the accepted-outcome parent-recruiter provider pin."""

from __future__ import annotations

import pytest

from agency_runtime.core.canary_judge_provider import (
    configured_canary_child_judge_provider,
)
from agency_runtime.core.canary_parent_recruiter_provider import (
    ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV,
    CanaryParentRecruiterProviderError,
    accepted_outcome_parent_recruiter_provider,
    configured_accepted_outcome_parent_recruiter_provider,
)
from agency_runtime.core.config import (
    AgencyConfig,
    CanaryConfig,
    HarnessInferenceConfig,
    InferenceConfig,
    InferenceProfile,
    ProviderEntry,
)
from agency_runtime.core.workforce.inference import configured_workforce_providers


def _config(*, parent_requested: str = "codex-subscription") -> AgencyConfig:
    return AgencyConfig(
        providers=(
            ProviderEntry(
                name="codex-subscription",
                type="cli",
                transport="codex",
                model="gpt-test",
            ),
            ProviderEntry(
                name="claude-subscription",
                type="cli",
                transport="claude",
                model="sonnet",
            ),
        ),
        canary=CanaryConfig(
            child_judge_provider_by_host=(("claude", "claude-subscription"),),
            accepted_outcome_parent_recruiter_provider_by_host=(("claude", parent_requested),),
        ),
        inference=InferenceConfig(
            profiles={
                "claude-haiku": InferenceProfile(
                    name="claude-haiku",
                    adapter="cli",
                    transport="claude",
                    model="haiku",
                ),
                "claude-sonnet": InferenceProfile(
                    name="claude-sonnet",
                    adapter="cli",
                    transport="claude",
                    model="sonnet",
                ),
            },
            harnesses={
                "claude": HarnessInferenceConfig(
                    default_profile="claude-haiku",
                    routes={"workforce.recruiter": "claude-sonnet"},
                )
            },
        ),
    )


def test_parent_and_child_pins_resolve_as_separate_roles() -> None:
    config = _config()

    parent = configured_accepted_outcome_parent_recruiter_provider(config, "CLAUDE")
    child = configured_canary_child_judge_provider(config, "claude")

    assert parent is not None and child is not None
    assert (parent[0].name, parent[1]) == ("codex-subscription", "codex")
    assert (child[0].name, child[1]) == ("claude-subscription", "claude")


def test_only_projected_accepted_outcome_recruiter_uses_the_pin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()

    ordinary = configured_workforce_providers(
        config,
        stage="recruiter",
        route_key="workforce.recruiter",
        harness="claude",
    )
    monkeypatch.setenv("AGENCY_CANARY_MODE", "1")
    activation_canary = configured_workforce_providers(
        config,
        stage="recruiter",
        route_key="workforce.recruiter",
        harness="claude",
    )
    monkeypatch.setenv(
        ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV,
        "codex-subscription",
    )
    accepted_outcome_recruiter = configured_workforce_providers(
        config,
        stage="recruiter",
        route_key="workforce.recruiter",
        harness="claude",
    )
    accepted_outcome_planner = configured_workforce_providers(
        config,
        stage="planner",
        route_key="workforce.planner",
        harness="claude",
    )

    assert [provider.name for provider in ordinary] == ["claude-sonnet"]
    assert [provider.name for provider in activation_canary] == ["claude-sonnet"]
    assert [provider.name for provider in accepted_outcome_recruiter] == ["codex-subscription"]
    assert [provider.name for provider in accepted_outcome_planner] == ["claude-haiku"]


def test_parent_recruiter_projection_mismatch_fails_without_fallback() -> None:
    config = _config()

    with pytest.raises(CanaryParentRecruiterProviderError, match="does not match"):
        accepted_outcome_parent_recruiter_provider(
            config,
            "claude",
            {
                "AGENCY_CANARY_MODE": "1",
                ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV: "claude-subscription",
            },
        )

    assert (
        accepted_outcome_parent_recruiter_provider(
            config,
            "claude",
            {"AGENCY_CANARY_MODE": "1"},
        )
        is None
    )


def test_parent_recruiter_pin_rejects_missing_or_unsupported_provider() -> None:
    with pytest.raises(CanaryParentRecruiterProviderError, match="resolve exactly once"):
        configured_accepted_outcome_parent_recruiter_provider(
            _config(parent_requested="missing"),
            "claude",
        )

    config = _config(parent_requested="http-provider")
    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="http-provider",
                type="openai-compatible",
                base_url="https://example.invalid/v1",
                api_key="test",
            ),
        ),
        canary=config.canary,
    )
    with pytest.raises(CanaryParentRecruiterProviderError, match="supported CLI transport"):
        configured_accepted_outcome_parent_recruiter_provider(config, "claude")
