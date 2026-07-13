"""Provider, parser, deadline, and fallback edge contracts for the selector judge."""

from __future__ import annotations

import math
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig, ProviderEntry
from agency_runtime.core.selector import judge

CATALOG = [{"slug": "security", "description": "Reviews application security."}]


def _provider(
    name: str,
    *,
    timeout: float = 5.0,
    api_key: str = "key",
) -> ProviderEntry:
    return ProviderEntry(
        name=name,
        type="openai-compatible",
        model=f"{name}-model",
        base_url=f"https://{name}.invalid/v1",
        api_key=api_key,
        timeout=timeout,
    )


def test_numeric_and_provider_preflight_reject_nonfinite_or_incomplete_values() -> None:
    assert judge._bounded_confidence(math.nan) is None
    assert judge._bounded_duration(object(), maximum=10.0) == 0.0
    assert judge._bounded_duration(math.inf, maximum=10.0) == 0.0
    assert judge._bounded_duration(-1, maximum=10.0) == 0.0
    assert judge._provider_is_attemptable(ProviderEntry(name="missing")) is False


def test_json_parser_handles_fences_embedded_objects_and_nonobject_loader_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert judge.parse_json_response('```json\n{"selected_ids": []}\n```') == {"selected_ids": []}
    assert judge.parse_json_response('model said: {"confidence": 0.5} done') == {"confidence": 0.5}
    assert judge.parse_json_response("[]") is None

    monkeypatch.setattr(judge, "safe_load_bounded_json", lambda *_args, **_kwargs: [])
    assert judge.parse_json_response("prefix {} suffix") is None


def test_response_content_rejects_wrong_shapes_and_extracts_ollama_message() -> None:
    assert (
        judge._response_content(
            {"content": {"type": "text", "text": "ignored"}},
            provider_type="anthropic",
            ollama_mode=False,
        )
        == ""
    )
    assert (
        judge._response_content(
            {"message": {"content": "ollama response"}},
            provider_type="ollama",
            ollama_mode=True,
        )
        == "ollama response"
    )


def test_cli_provider_exception_is_a_normal_fallback_signal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ProviderEntry(name="codex", type="cli", transport="codex", model="")
    monkeypatch.setattr(
        judge,
        "invoke_cli_judge",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("cli unavailable")),
    )

    assert (
        judge._try_cli_provider(
            provider,
            "review security",
            CATALOG,
            1,
            1,
            5.0,
            1.0,
        )
        is None
    )


def test_http_provider_preflight_rejects_missing_identity_key_and_deadline() -> None:
    assert (
        judge._provider_credentials_are_safe(
            ProviderEntry(name="missing"),
            provider_type="openai-compatible",
            ollama_mode=False,
            api_key="",
        )
        is False
    )
    assert (
        judge._provider_credentials_are_safe(
            _provider("keyless", api_key=""),
            provider_type="openai-compatible",
            ollama_mode=False,
            api_key="",
        )
        is False
    )
    provider = _provider("deadline")
    assert (
        judge._try_http_provider(
            provider,
            "review security",
            CATALOG,
            1,
            1,
            5.0,
            0.0,
            api_key="key",
            provider_type="openai-compatible",
            ollama_mode=False,
        )
        is None
    )


def test_provider_and_legacy_paths_reject_empty_prompt_catalogs_and_bad_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert judge._try_provider(_provider("empty"), "work", [{}], 1, 1, 0.0) is None
    assert judge._try_legacy_judge(JudgeConfig(), "work", CATALOG, 1, 1, 0.0) is None

    legacy = JudgeConfig(
        model="legacy-model",
        base_url="https://legacy.invalid/v1",
        timeout=5.0,
    )
    assert judge._try_legacy_judge(legacy, "work", [{}], 1, 1, 0.0) is None
    assert (
        judge._try_legacy_judge(
            legacy,
            "work",
            CATALOG,
            1,
            1,
            0.0,
            request_timeout=0.0,
        )
        is None
    )

    monkeypatch.setattr(judge, "_execute_http_request", lambda *_args, **_kwargs: ({}, 0.1))
    assert (
        judge._try_legacy_judge(
            legacy,
            "work",
            CATALOG,
            1,
            1,
            0.0,
            request_timeout=1.0,
        )
        is None
    )


def test_provider_chain_skips_duplicates_unavailable_entries_and_invalid_timeouts() -> None:
    duplicate = _provider("duplicate")
    unavailable = ProviderEntry(name="unavailable")
    invalid_timeout = _provider("invalid-timeout", timeout=0.0)
    duplicate_signature, _target = judge._provider_attempt_identity(duplicate)
    state = judge._AttemptState(
        started=0.0,
        deadline=100.0,
        attempted={duplicate_signature},
    )

    assert (
        judge._try_provider_chain(
            state,
            (duplicate, unavailable, invalid_timeout),
            "work",
            CATALOG,
            1,
            1,
            0.0,
        )
        is None
    )
    assert state.count == 0


def test_legacy_fallback_respects_exhausted_attempt_budget() -> None:
    state = judge._AttemptState(
        started=0.0,
        deadline=100.0,
        count=judge._MAX_PROVIDER_ATTEMPTS,
    )
    legacy = JudgeConfig(
        model="legacy-model",
        base_url="https://legacy.invalid/v1",
        timeout=5.0,
    )
    assert (
        judge._try_legacy_fallback(
            state,
            legacy,
            "work",
            CATALOG,
            1,
            1,
            0.0,
        )
        is None
    )

    cfg = AgencyConfig(
        judge=legacy,
        ollama=OllamaConfig(
            enabled=True,
            base_url="http://127.0.0.1:11434",
            model="local-model",
        ),
    )
    assert (
        judge._try_ollama_fallback(
            state,
            cfg,
            "work",
            CATALOG,
            1,
            1,
            0.0,
        )
        is None
    )


def test_confidence_bypass_requires_an_identified_scored_candidate() -> None:
    assert (
        judge._confidence_bypass_result(
            [{}],
            [10.0],
            max_sel=1,
            threshold=1.0,
            candidate_count=1,
            top_score=10.0,
        )
        is None
    )


def test_query_judge_returns_successful_legacy_fallback_with_cumulative_latency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_result: dict[str, Any] = {
        "selected_ids": ["security"],
        "confidence": 0.8,
        "latency_ms": 0,
        "status": "applied",
        "provider": "legacy",
        "candidate_count": 1,
        "top_score": 1.0,
    }
    cfg = AgencyConfig(
        providers=(),
        judge=JudgeConfig(
            model="legacy",
            base_url="https://legacy.invalid/v1",
            timeout=5.0,
            confidence_bypass_threshold=999.0,
        ),
    )
    monkeypatch.setattr(judge, "pre_narrow", lambda *_args, **_kwargs: (CATALOG, [1.0]))
    monkeypatch.setattr(judge, "_try_legacy_fallback", lambda *_args, **_kwargs: legacy_result)

    result = judge.query_judge("review security", CATALOG, config=cfg)

    assert result["status"] == "applied"
    assert result["selected_ids"] == ["security"]
