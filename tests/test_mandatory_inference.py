"""Mandatory semantic-inference and reroute reuse contracts."""

from __future__ import annotations

from typing import Any, Literal

import pytest

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig, ProviderEntry
from agency_runtime.core.selector import judge, pipeline
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.turn_intent import (
    TurnClassification,
    TurnState,
    classify_turn_intent,
)

CATALOG = [
    {
        "slug": "security-reviewer",
        "name": "Security Reviewer",
        "description": "Reviews authentication and application security.",
    },
    {
        "slug": "code-reviewer",
        "name": "Code Reviewer",
        "description": "Reviews implementation quality.",
    },
]


def _provider(
    name: str,
    *,
    provider_type: str = "openai-compatible",
    model: str | None = None,
) -> ProviderEntry:
    return ProviderEntry(
        name=name,
        type=provider_type,
        model=model or f"{name}-model",
        base_url=f"https://{name}.invalid/v1",
        api_key="test-key",
        timeout=5.0,
    )


def _config(*providers: ProviderEntry) -> AgencyConfig:
    return AgencyConfig(
        providers=tuple(providers),
        judge=JudgeConfig(
            model="",
            base_url="",
            timeout=10.0,
            confidence_bypass_threshold=0.0,
        ),
        ollama=OllamaConfig(enabled=False, model=""),
    )


def _classification(
    kind: Literal["continuation", "new_intent", "revision"],
    *,
    reroute: bool,
    message: str,
) -> TurnClassification:
    if kind == "new_intent":
        state = TurnState(state_known=True, state_status="current")
    else:
        state = TurnState(
            previous_trace_id="prior-trace",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=not reroute,
            pending_question=reroute,
        )
    decision = classify_turn_intent(message, state)
    assert decision.turn_kind == kind
    assert decision.reroute_required is reroute
    return decision


def test_configured_chain_cannot_be_bypassed_and_preserves_model_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _provider("first")
    second = _provider("litellm-primary", provider_type="litellm", model="production-router")
    attempted: list[str] = []

    monkeypatch.setattr(judge, "pre_narrow", lambda *_args, **_kwargs: (CATALOG, [100.0, 1.0]))

    def attempt(
        provider: ProviderEntry,
        *_args: Any,
        **_kwargs: Any,
    ) -> dict[str, Any] | None:
        attempted.append(provider.name)
        if provider is first:
            return None
        return {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.97,
            "latency_ms": 2,
            "status": "applied",
            "provider": "litellm-primary (litellm)",
            "requested_model": "task-general",
            "model_group": "production-router",
            "resolved_provider": "openai",
            "resolved_model": "gpt-5.6-review",
            "candidate_count": 2,
            "top_score": 100.0,
        }

    monkeypatch.setattr(judge, "_try_provider", attempt)

    result = judge.query_judge(
        "review authentication security",
        CATALOG,
        config=_config(first, second),
    )

    assert attempted == ["first", "litellm-primary"]
    assert result["status"] == "applied"
    assert result["inference_mode"] == "inferred"
    assert result["inference_required"] is True
    assert result["requested_model"] == "task-general"
    assert result["model_group"] == "production-router"
    assert result["resolved_provider"] == "openai"
    assert result["resolved_model"] == "gpt-5.6-review"
    assert result["provider_attempts"] == [
        {
            "provider_name": "first",
            "provider_type": "openai-compatible",
            "requested_model": "first-model",
            "model_group": "",
            "status": "failed",
            "reason": "provider_call_failed",
        },
        {
            "provider_name": "litellm-primary",
            "provider_type": "litellm",
            "requested_model": "production-router",
            "model_group": "production-router",
            "status": "applied",
            "reason": "",
        },
    ]


def test_total_configured_chain_failure_is_explicitly_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = (_provider("first"), _provider("second"))
    monkeypatch.setattr(judge, "_try_provider", lambda *_args, **_kwargs: None)

    result = judge.query_judge(
        "review authentication security",
        CATALOG,
        config=_config(*providers),
    )

    assert result["status"] == "degraded"
    assert result["source"] == "degraded_inference"
    assert result["inference_mode"] == "degraded"
    assert result["inference_attempted"] is True
    assert result["selected_ids"] == []
    assert result["deterministic_candidate_ids"] == ["security-reviewer"]
    assert [entry["provider_name"] for entry in result["inference_failures"]] == [
        "first",
        "second",
    ]
    assert "inferred" not in result["status"]


def test_configured_inference_without_a_catalog_is_visible_but_not_attempted() -> None:
    result = judge.query_judge(
        "review authentication security",
        [],
        config=_config(_provider("configured")),
    )

    assert result["status"] == "degraded"
    assert result["degraded_reason"] == "no_catalog"
    assert result["deterministic_fallback_status"] == "no_catalog"
    assert result["inference_mode"] == "degraded"
    assert result["inference_required"] is True
    assert result["inference_attempted"] is False
    assert result["provider_attempts"] == []


def test_configured_local_inference_failure_is_degraded_and_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig(
        providers=(
            ProviderEntry(
                name="required-local",
                type="ollama",
                model="local-model",
                base_url="http://127.0.0.1:11434",
                ollama_mode=True,
                timeout=5.0,
            ),
        ),
        judge=JudgeConfig(model="", base_url="", timeout=5.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    monkeypatch.setattr(judge, "_try_provider", lambda *_args, **_kwargs: None)

    result = judge.query_judge("review authentication", CATALOG, config=config)

    assert result["status"] == "degraded"
    assert result["inference_mode"] == "degraded"
    assert result["provider_attempts"] == [
        {
            "provider_name": "required-local",
            "provider_type": "ollama",
            "requested_model": "local-model",
            "model_group": "",
            "status": "failed",
            "reason": "provider_call_failed",
        }
    ]


def test_optional_keyless_local_fallback_failure_uses_visible_heuristic_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig(
        judge=JudgeConfig(
            model="local-model",
            base_url="http://127.0.0.1:11434",
            ollama_mode=True,
            timeout=5.0,
            confidence_bypass_threshold=999.0,
        ),
        ollama=OllamaConfig(
            enabled=True,
            model="local-model",
            base_url="http://127.0.0.1:11434",
        ),
    )
    monkeypatch.setattr(judge, "_try_legacy_judge", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(judge, "_try_provider", lambda *_args, **_kwargs: None)

    result = judge.query_judge("review authentication", CATALOG, config=config)

    assert result["status"] == "token_fallback"
    assert result["inference_configured"] is False
    assert result["inference_required"] is False
    assert result["inference_attempted"] is True
    assert result["inference_mode"] == "heuristic"
    assert [(item["provider_name"], item["status"]) for item in result["provider_attempts"]] == [
        ("legacy-judge", "failed"),
        ("ollama-fallback", "skipped"),
    ]


def test_declared_legacy_key_environment_is_mandatory_even_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig(
        judge=JudgeConfig(
            model="legacy-model",
            base_url="https://legacy.invalid/v1",
            api_key_env="MISSING_AGENCY_TEST_KEY",
            timeout=5.0,
            confidence_bypass_threshold=0.0,
        ),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    monkeypatch.delenv("MISSING_AGENCY_TEST_KEY", raising=False)
    monkeypatch.setattr(judge, "_try_legacy_judge", lambda *_args, **_kwargs: None)

    result = judge.query_judge("review authentication", CATALOG, config=config)

    assert result["status"] == "degraded"
    assert result["inference_configured"] is True
    assert result["inference_required"] is True
    assert result["inference_mode"] == "degraded"
    assert result["provider_attempts"][0]["provider_name"] == "legacy-judge"


def test_legacy_duplicate_is_recorded_without_a_second_attempt() -> None:
    legacy = JudgeConfig(
        model="local-model",
        base_url="http://127.0.0.1:11434",
        ollama_mode=True,
        timeout=5.0,
    )
    signature = judge._attempt_signature(legacy.base_url, legacy.model, True)
    target = judge._network_target_signature(legacy.base_url, legacy.model)
    state = judge._AttemptState(
        started=0.0,
        deadline=5.0,
        attempted={signature},
        attempted_targets={target},
    )

    assert (
        judge._try_legacy_fallback(
            state,
            legacy,
            "review authentication",
            CATALOG,
            1,
            len(CATALOG),
            5.0,
        )
        is None
    )
    assert state.count == 0
    assert state.receipts[0]["status"] == "skipped"
    assert state.receipts[0]["reason"] == "duplicate_provider"


def test_usable_legacy_key_disables_lexical_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempted: list[str] = []
    config = AgencyConfig(
        judge=JudgeConfig(
            model="legacy-model",
            base_url="https://legacy.invalid/v1",
            api_key="test-key",
            confidence_bypass_threshold=0.0,
        ),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    monkeypatch.setattr(judge, "pre_narrow", lambda *_args, **_kwargs: (CATALOG, [100.0, 1.0]))

    def legacy(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        attempted.append("legacy")
        return {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
            "provider": "legacy-model",
            "candidate_count": 2,
            "top_score": 100.0,
        }

    monkeypatch.setattr(judge, "_try_legacy_judge", legacy)

    result = judge.query_judge("review authentication", CATALOG, config=config)

    assert attempted == ["legacy"]
    assert result["status"] == "applied"
    assert result["inference_mode"] == "inferred"
    assert result["requested_model"] == "legacy-model"


def test_no_configured_inference_retains_visible_heuristic_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    monkeypatch.setattr(judge, "pre_narrow", lambda *_args, **_kwargs: (CATALOG, [100.0, 1.0]))

    result = judge.query_judge("review authentication", CATALOG, config=config)

    assert result["status"] == "confidence_bypass"
    assert result["inference_configured"] is False
    assert result["inference_required"] is False
    assert result["inference_attempted"] is False
    assert result["inference_mode"] == "heuristic"
    assert result["provider_attempts"] == []


def test_exact_controls_stay_deterministic_without_turn_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("deterministic turn called inference")
        ),
    )

    result = pipeline.route(
        "session",
        "agency status",
        CATALOG,
        config=_config(_provider("configured")),
    )

    assert result["turn_kind"] == "control"
    assert result["selection_required"] is False
    assert result["inference_configured"] is True
    assert result["inference_required"] is False
    assert result["inference_attempted"] is False
    assert result["inference_mode"] == "deterministic"
    assert result["provider_attempts"] == []


@pytest.mark.parametrize("message", ["thanks", "ok"])
def test_acknowledgement_requires_explicit_current_state_to_bypass(
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("deterministic turn called inference")
        ),
    )

    result = pipeline.route(
        "session",
        message,
        CATALOG,
        config=_config(_provider("configured")),
        turn_state={"state_known": True},
    )

    assert result["selection_required"] is False
    assert result["inference_configured"] is True
    assert result["inference_required"] is False
    assert result["inference_attempted"] is False
    assert result["inference_mode"] == "deterministic"
    assert result["provider_attempts"] == []


@pytest.mark.parametrize("message", ["hello", "how's it going"])
def test_social_conversation_still_uses_configured_inference(
    message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def infer(task: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        return {
            "selected_ids": [],
            "confidence": 0.92,
            "latency_ms": 1,
            "status": "abstain",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "provider",
            "provider_attempts": ["configured"],
            "inference_failures": [],
        }

    monkeypatch.setattr(pipeline, "query_judge", infer)

    result = pipeline.route(
        "session",
        message,
        CATALOG,
        config=_config(_provider("configured")),
        turn_state={"state_known": True},
    )

    assert calls == [message]
    assert result["turn_kind"] == "conversation"
    assert result["selection_required"] is True
    assert result["inference_required"] is True
    assert result["inference_attempted"] is True


def test_detailed_continuation_requires_fresh_configured_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        pipeline,
        "cache_get",
        lambda _key: (_ for _ in ()).throw(
            AssertionError("detailed continuation read the selection cache")
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "session_check",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("detailed continuation read session stickiness")
        ),
    )

    def infer(task: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        return {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.94,
            "latency_ms": 1,
            "status": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "provider_attempts": [],
            "inference_failures": [],
        }

    monkeypatch.setattr(pipeline, "query_judge", infer)

    result = pipeline.route(
        "session",
        "Use PostgreSQL with the existing schema.",
        CATALOG,
        config=_config(_provider("configured")),
        turn_state={
            "state_known": True,
            "previous_trace_id": "prior-trace",
            "previous_status": "completed",
            "previous_turn_kind": "new_intent",
            "pending_question": True,
        },
    )

    assert calls == ["Use PostgreSQL with the existing schema."]
    assert result["turn_kind"] == "continuation"
    assert result["reroute_required"] is True
    assert result["inference_required"] is True
    assert result["inference_attempted"] is True


def test_no_state_acknowledgement_requires_configured_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def infer(task: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        return {
            "selected_ids": ["code-reviewer"],
            "confidence": 0.97,
            "latency_ms": 1,
            "status": "applied",
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "provider",
            "provider_attempts": ["configured"],
            "inference_failures": [],
        }

    monkeypatch.setattr(pipeline, "query_judge", infer)

    result = pipeline.route(
        "session",
        "thanks",
        CATALOG,
        config=_config(_provider("configured")),
    )

    assert calls == ["thanks"]
    assert result["turn_kind"] == "acknowledgement"
    assert result["selection_required"] is True
    assert result["reroute_required"] is True
    assert result["inference_required"] is True
    assert result["inference_attempted"] is True


def test_precomputed_classification_and_raw_state_are_mutually_exclusive() -> None:
    with pytest.raises(
        ValueError,
        match="turn_classification and turn_state are mutually exclusive",
    ):
        pipeline.route(
            "session",
            "fix auth",
            CATALOG,
            config=_config(),
            turn_classification=_classification(
                "new_intent",
                reroute=True,
                message="fix auth",
            ),
            turn_state={"state_known": True},
        )


def test_rerouted_intent_requires_fresh_selection_without_an_inference_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        pipeline,
        "cache_get",
        lambda _key: (_ for _ in ()).throw(AssertionError("reroute read the cache")),
    )
    monkeypatch.setattr(
        pipeline,
        "session_check",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("reroute read session stickiness")
        ),
    )

    def select(task: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        return {
            "selected_ids": ["code-reviewer"],
            "confidence": 0.8,
            "latency_ms": 0,
            "status": "token_fallback",
            "inference_configured": False,
            "inference_required": False,
            "inference_attempted": False,
            "inference_mode": "heuristic",
            "provider_attempts": [],
            "inference_failures": [],
        }

    monkeypatch.setattr(pipeline, "query_judge", select)

    result = pipeline.route(
        "session",
        "fix auth",
        CATALOG,
        config=_config(),
        turn_classification=_classification(
            "new_intent",
            reroute=True,
            message="fix auth",
        ),
    )

    assert calls == [
        "fix auth [domain context: application security, authentication, "
        "authorization, identity access management]"
    ]
    assert result["selected_ids"] == ["code-reviewer"]
    assert result["inference_mode"] == "heuristic"


def test_rerouted_intents_bypass_cache_and_stickiness_when_inference_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_cache()
    clear_session_routing()
    calls: list[str] = []
    config = _config(_provider("configured"))

    def infer(task: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append(task)
        return {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.9,
            "latency_ms": 1,
            "status": "applied",
            "provider": "configured",
            "candidate_count": 2,
            "top_score": 1.0,
            "inference_configured": True,
            "inference_required": True,
            "inference_attempted": True,
            "inference_mode": "inferred",
            "provider_attempts": [],
            "inference_failures": [],
        }

    monkeypatch.setattr(pipeline, "query_judge", infer)

    classified_messages = (
        (
            _classification(
                "new_intent",
                reroute=True,
                message="review authentication",
            ),
            "review authentication",
        ),
        (
            _classification(
                "revision",
                reroute=True,
                message="actually review authentication",
            ),
            "actually review authentication",
        ),
        (
            _classification(
                "continuation",
                reroute=True,
                message="continue",
            ),
            "continue",
        ),
    )
    for classification, message in classified_messages:
        routing = pipeline.route(
            "session",
            message,
            CATALOG,
            config=config,
            turn_classification=classification,
        )
        assert routing.get("cache_hit") is not True

    assert len(calls) == 3

    reused = pipeline.route(
        "session",
        "continue",
        CATALOG,
        config=config,
        turn_classification=_classification(
            "continuation",
            reroute=False,
            message="continue",
        ),
    )

    assert len(calls) == 3
    assert reused["cache_hit"] is True
    assert reused["inference_mode"] == "cached"
    assert reused["inference_required"] is False
    assert reused["inference_attempted"] is False
    assert reused["provider_attempts"] == []
