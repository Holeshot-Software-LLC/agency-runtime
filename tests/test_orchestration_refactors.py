"""Parity tables for selector and detection orchestration helpers."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core.cli_transport import CLIProviderStatus
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.detect import (
    DetectionResult,
    ProviderDetection,
    generate_config_from_detection,
)
from agency_runtime.core.selector.explain import _rejected_explanations
from agency_runtime.core.selector.pipeline import (
    _exact_cached_routing,
    _merge_computed_routing,
    _RouteRequest,
    _RouteSignals,
)


def _request(*, source_hash: str = "current") -> _RouteRequest:
    return _RouteRequest(
        session_id="session",
        user_message="review code",
        catalog=[{"slug": "reviewer"}],
        config=AgencyConfig(),
        policy={},
        context_fingerprint="fingerprint",
        routing_query="review code",
        cache_key="cache-key",
        source_message_hash=source_hash,
        active_ids=frozenset({"reviewer", "companion"}),
    )


@pytest.mark.parametrize(
    ("cached", "expected"),
    [
        (None, None),
        ({"source_message_hash": "old", "selected_ids": ["reviewer"]}, None),
        ({"source_message_hash": "current", "selected_ids": ["removed"]}, None),
        (
            {"source_message_hash": "current", "selected_ids": ["reviewer"]},
            "same",
        ),
        ({"source_message_hash": "current", "selected_ids": []}, "same"),
    ],
)
def test_exact_cache_parity_table(
    cached: dict[str, Any] | None,
    expected: str | None,
) -> None:
    result = _exact_cached_routing(cached, _request())

    assert ("same" if result is cached and cached is not None else None) == expected


def test_computed_routing_merge_preserves_order_and_policy_projection() -> None:
    routing = {
        "selected_ids": ["reviewer", "removed", "reviewer"],
        "confidence": 0.8,
    }
    signals = _RouteSignals(
        policy_validation={
            "valid": False,
            "errors": ["policy warning"],
            "enabled_slugs": ["companion"],
            "disabled_count": 3,
        },
        matched_actions=["CODING"],
        companion_ids=["companion", "unavailable"],
        available_companion_ids=["companion", "reviewer"],
        unavailable_companion_ids=["unavailable"],
        work_units={"delegate": True, "count": 2},
    )

    result = _merge_computed_routing(routing, _request(), signals)

    assert result is routing
    assert result["selected_ids"] == ["reviewer", "companion"]
    assert result["semantic_ids"] == ["reviewer", "reviewer"]
    assert result["companion_actions"] == ["CODING"]
    assert result["policy_validation"] == {
        "valid": False,
        "errors": ["policy warning"],
        "enabled_count": 1,
        "disabled_count": 3,
    }
    assert result["source_message_hash"] == "current"


@pytest.mark.parametrize(
    ("status", "cache_hit", "session_reused", "score", "reason"),
    [
        ("applied", True, False, 10.0, "not in cached selection"),
        ("applied", False, True, 10.0, "not in reused session selection"),
        ("applied", False, False, 0.0, "zero token overlap"),
        ("confidence_bypass", False, False, 1.0, "below confidence-bypass cutoff"),
        (
            "token_fallback",
            False,
            False,
            1.0,
            "lower token score than selected candidates",
        ),
        ("applied", False, False, 1.0, "not selected by judge"),
        (
            "abstained",
            False,
            False,
            1.0,
            "not selected by routing status 'abstained'",
        ),
    ],
)
def test_explanation_rejection_reason_parity_table(
    status: str,
    cache_hit: bool,
    session_reused: bool,
    score: float,
    reason: str,
) -> None:
    rejected = _rejected_explanations(
        [({"slug": "candidate", "name": "Candidate"}, score)],
        set(),
        status=status,
        cache_hit=cache_hit,
        session_reused=session_reused,
    )

    assert rejected[0]["reason"] == reason


def _cli_status(transport: str) -> CLIProviderStatus:
    return CLIProviderStatus(
        transport=transport,
        installed=True,
        authenticated=True,
        usable=True,
    )


def _detection(case: str) -> DetectionResult:
    if case == "nothing":
        return DetectionResult()
    if case == "ollama":
        return DetectionResult(
            providers=ProviderDetection(
                ollama_available=True,
                ollama_models=["local-model"],
            )
        )
    if case == "litellm-stack":
        return DetectionResult(
            providers=ProviderDetection(
                litellm_available=True,
                litellm_models=["proxy-model"],
                openai_key_present=True,
                openai_models=["gpt-5.4-mini"],
                anthropic_key_present=True,
                ollama_available=True,
                ollama_models=["local-model"],
            ),
            cli_providers={"codex": _cli_status("codex")},
        )
    if case == "cli-only":
        return DetectionResult(
            cli_providers={
                "codex": _cli_status("codex"),
                "claude": _cli_status("claude"),
            }
        )
    raise AssertionError(case)


@pytest.mark.parametrize(
    ("case", "profile", "provider_names", "judge_model", "judge_base"),
    [
        ("nothing", "standard", [], "qwen3.5:2b", "http://127.0.0.1:11434"),
        ("ollama", "standard", ["ollama"], "local-model", "http://127.0.0.1:11434"),
        ("ollama", "local-only", ["ollama"], "local-model", "http://127.0.0.1:11434"),
        (
            "litellm-stack",
            "standard",
            ["litellm", "openai", "anthropic", "codex-cli"],
            "proxy-model",
            "http://127.0.0.1:4000",
        ),
        ("cli-only", "standard", ["codex-cli", "claude-cli"], "", ""),
    ],
)
def test_generated_config_provider_order_parity_table(
    case: str,
    profile: str,
    provider_names: list[str],
    judge_model: str,
    judge_base: str,
) -> None:
    config = generate_config_from_detection(_detection(case), profile=profile)

    assert [provider["name"] for provider in config["providers"]] == provider_names
    assert config["judge"]["model"] == judge_model
    assert config["judge"]["base_url"] == judge_base
    assert config["profile"] == profile
    if case == "litellm-stack":
        assert config["adapters"]["litellm"]["skip_models"] == [
            "complexity_router",
            "auto_router/",
            "proxy-model",
        ]


def test_local_only_config_disables_every_adapter_and_remote_provider() -> None:
    config = generate_config_from_detection(_detection("litellm-stack"), "local-only")

    assert [provider["name"] for provider in config["providers"]] == ["ollama"]
    assert all(adapter["enabled"] == "false" for adapter in config["adapters"].values())
