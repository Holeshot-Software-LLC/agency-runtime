"""Focused contracts for judge transport validation and ordered fallback."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.selector import judge

CATALOG = [
    {
        "slug": "security-reviewer",
        "description": "Reviews authentication and application security.",
    },
    {
        "slug": "code-reviewer",
        "description": "Reviews implementation quality.",
    },
]


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        body = json.dumps(self.payload).encode("utf-8")
        return body if size < 0 else body[:size]


def _provider(name: str, *, timeout: float = 10.0) -> ProviderEntry:
    return ProviderEntry(
        name=name,
        model=f"{name}-model",
        base_url=f"https://{name}.invalid/v1",
        api_key="test-key",
        timeout=timeout,
    )


def test_validated_decision_rejects_malformed_and_unknown_selections() -> None:
    assert judge._validated_decision(None, CATALOG, 2) is None
    assert (
        judge._validated_decision(
            {"selected_ids": "security-reviewer", "confidence": 0.8},
            CATALOG,
            2,
        )
        is None
    )
    assert (
        judge._validated_decision(
            {"selected_ids": ["unknown"], "confidence": 0.8},
            CATALOG,
            2,
        )
        is None
    )
    assert (
        judge._validated_decision(
            {"selected_ids": ["security-reviewer"], "confidence": "invalid"},
            CATALOG,
            2,
        )
        is None
    )

    assert judge._validated_decision(
        {
            "selected_ids": [
                "security-reviewer",
                "security-reviewer",
                "code-reviewer",
            ],
            "confidence": 5,
        },
        CATALOG,
        1,
    ) == (["security-reviewer"], 1.0)

    assert judge._validated_decision(
        {"selected_ids": [], "confidence": 0.91},
        CATALOG,
        2,
    ) == ([], 0.91)


def test_legacy_success_preserves_request_and_result_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    clock = iter([1.0, 1.25])

    def open_response(request: Any, **kwargs: Any) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data)
        captured["timeout"] = kwargs["timeout"]
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "selected_ids": ["security-reviewer"],
                                    "confidence": 0.75,
                                }
                            ),
                        },
                    }
                ],
            }
        )

    monkeypatch.setattr(judge.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(judge, "open_no_redirect", open_response)
    config = JudgeConfig(
        model="gpt-5-legacy",
        base_url="https://legacy.invalid/v1",
        api_key="test-key",
        timeout=4,
        ollama_mode=False,
    )

    result = judge._try_legacy_judge(
        config,
        "review authentication",
        CATALOG,
        1,
        2,
        4.0,
    )

    assert result == {
        "selected_ids": ["security-reviewer"],
        "confidence": 0.75,
        "latency_ms": 250,
        "status": "applied",
        "error": "",
        "provider": "gpt-5-legacy",
        "candidate_count": 2,
        "top_score": 4.0,
    }
    assert list(result) == [
        "selected_ids",
        "confidence",
        "latency_ms",
        "status",
        "error",
        "provider",
        "candidate_count",
        "top_score",
    ]
    assert captured["url"] == "https://legacy.invalid/v1/chat/completions"
    assert captured["headers"] == {
        "Content-type": "application/json",
        "Authorization": "Bearer test-key",
    }
    assert captured["timeout"] == 4.0
    body = captured["body"]
    assert body["model"] == "gpt-5-legacy"
    assert body["max_completion_tokens"] == 256
    assert body["stream"] is False
    assert "max_tokens" not in body
    assert "temperature" not in body


def test_provider_chain_preserves_order_and_remaining_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = {"value": 0.0}
    attempts: list[tuple[str, float]] = []
    expected = {
        "selected_ids": ["security-reviewer"],
        "confidence": 0.9,
        "latency_ms": 0,
        "status": "applied",
        "provider": "second (openai-compatible)",
        "candidate_count": 2,
        "top_score": 4.0,
    }

    monkeypatch.setattr(judge.time, "monotonic", lambda: now["value"])

    def attempt(
        provider: ProviderEntry,
        _task: str,
        _candidates: list[dict[str, Any]],
        _max_sel: int,
        _candidate_count: int,
        _top_score: float,
        request_timeout: float | None = None,
    ) -> dict[str, Any] | None:
        assert request_timeout is not None
        attempts.append((provider.name, request_timeout))
        if provider.name == "first":
            now["value"] = 4.0
            return None
        return expected

    monkeypatch.setattr(judge, "_try_provider", attempt)
    state = judge._AttemptState(started=0.0, deadline=6.0)

    result = judge._try_provider_chain(
        state,
        (_provider("first"), _provider("second")),
        "review authentication",
        CATALOG,
        2,
        2,
        4.0,
    )

    assert result is expected
    assert attempts == [("first", 6.0), ("second", 2.0)]
    assert state.count == 2


def test_legacy_failure_falls_through_to_ollama_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[tuple[str, float]] = []
    config = AgencyConfig(
        providers=(),
        judge=JudgeConfig(
            model="legacy-model",
            base_url="https://legacy.invalid/v1",
            timeout=5,
            confidence_bypass_threshold=999,
        ),
        ollama=OllamaConfig(
            enabled=True,
            model="local-model",
            base_url="http://127.0.0.1:11434",
        ),
    )

    def fail_legacy(
        _config: JudgeConfig,
        _task: str,
        _candidates: list[dict[str, Any]],
        _max_sel: int,
        _candidate_count: int,
        _top_score: float,
        request_timeout: float | None = None,
    ) -> None:
        assert request_timeout is not None
        attempts.append(("legacy", request_timeout))
        return None

    def succeed_ollama(
        provider: ProviderEntry,
        _task: str,
        _candidates: list[dict[str, Any]],
        _max_sel: int,
        candidate_count: int,
        top_score: float,
        request_timeout: float | None = None,
    ) -> dict[str, Any]:
        assert request_timeout is not None
        attempts.append((provider.name, request_timeout))
        return {
            "selected_ids": ["security-reviewer"],
            "confidence": 0.8,
            "latency_ms": 0,
            "status": "applied",
            "provider": "ollama-fallback (ollama)",
            "candidate_count": candidate_count,
            "top_score": top_score,
        }

    monkeypatch.setattr(judge, "_try_legacy_judge", fail_legacy)
    monkeypatch.setattr(judge, "_try_provider", succeed_ollama)

    result = judge.query_judge(
        "review authentication security",
        CATALOG,
        config=config,
    )

    assert result["provider"] == "ollama-fallback (ollama)"
    assert [name for name, _timeout in attempts] == ["legacy", "ollama-fallback"]
    assert all(0 < timeout <= 5 for _name, timeout in attempts)


def test_typed_provider_failure_never_enters_hidden_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig(
        providers=(_provider("configured"),),
        judge=JudgeConfig(
            model="legacy-model",
            base_url="https://legacy.invalid/v1",
            timeout=5,
            confidence_bypass_threshold=999,
        ),
        ollama=OllamaConfig(
            enabled=True,
            model="local-model",
            base_url="http://127.0.0.1:11434",
        ),
    )
    attempted: list[str] = []

    def fail_provider(provider: ProviderEntry, *_args: Any, **_kwargs: Any) -> None:
        attempted.append(provider.name)
        return None

    def unexpected_legacy(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("typed provider chain entered legacy fallback")

    monkeypatch.setattr(judge, "_try_provider", fail_provider)
    monkeypatch.setattr(judge, "_try_legacy_judge", unexpected_legacy)

    result = judge.query_judge(
        "review authentication security",
        CATALOG,
        config=config,
    )

    assert attempted == ["configured"]
    assert result["status"] == "degraded"
    assert result["inference_mode"] == "degraded"
    assert result["inference_required"] is True
    assert result["selected_ids"] == []
