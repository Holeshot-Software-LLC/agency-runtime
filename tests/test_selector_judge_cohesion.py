from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, JudgeConfig, OllamaConfig, ProviderEntry
from agency_runtime.core.selector import judge

CATALOG = [
    {
        "slug": "security-reviewer",
        "description": "Reviews authentication and application security.",
    }
]


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int = -1) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_query_reports_empty_catalog_and_never_bypasses_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = AgencyConfig(
        judge=JudgeConfig(confidence_bypass_threshold=0.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    empty = judge.query_judge("review security", [], config=config)
    assert empty["selected_ids"] == []
    assert empty["status"] == "inference_unavailable"
    assert empty["error"] == "agent catalog not loaded"
    assert empty["inference_required"] is True

    monkeypatch.setattr(judge, "pre_narrow", lambda *_args: (CATALOG, [10.0]))
    bypass = judge.query_judge("review security", CATALOG, config=config)
    assert bypass["status"] == "inference_unavailable"
    assert bypass["selected_ids"] == []


def test_duplicate_ollama_fallback_is_not_retried() -> None:
    config = AgencyConfig(
        judge=JudgeConfig(timeout=5.0),
        ollama=OllamaConfig(
            enabled=True,
            model="judge-model",
            base_url="http://127.0.0.1:11434",
        ),
    )
    signature = judge._attempt_signature(
        config.ollama.base_url,
        config.ollama.model,
        True,
    )
    state = judge._AttemptState(
        started=0.0,
        deadline=5.0,
        attempted={signature},
    )

    assert judge._try_ollama_fallback(state, config, "work", CATALOG, 1, 1, 0.0) is None
    assert state.count == 0


def test_cli_provider_rejects_invalid_timeout_and_clamps_direct_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ProviderEntry(
        name="codex",
        type="cli",
        transport="codex",
        timeout=600.0,
    )
    called: list[float] = []

    def invoke(
        _provider: ProviderEntry,
        _prompt: str,
        *,
        timeout: float,
    ) -> dict[str, Any]:
        called.append(timeout)
        return {"selected_ids": ["security-reviewer"], "confidence": 0.9}

    monkeypatch.setattr(judge, "invoke_cli_judge", invoke)
    assert (
        judge._try_cli_provider(
            provider,
            "work",
            CATALOG,
            1,
            1,
            0.0,
            float("nan"),
        )
        is None
    )
    assert called == []

    result = judge._try_cli_provider(provider, "work", CATALOG, 1, 1, 0.0, None)
    assert result is not None
    assert result["provider"] == "codex (cli:codex)"
    assert called == [judge._MAX_JUDGE_DEADLINE_SECONDS]


def test_attempt_budget_preserves_profile_maximum_and_clamps_above_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(judge.time, "monotonic", lambda: 0.0)

    ordinary = judge._AttemptState.begin(60.0)

    assert ordinary.reserve(120.0) == 60.0

    state = judge._AttemptState.begin(120.0)

    assert state.deadline == 120.0
    assert state.reserve(120.0) == 120.0

    clamped = judge._AttemptState.begin(600.0)

    assert clamped.deadline == 120.0
    assert judge._MAX_JUDGE_DEADLINE_SECONDS == 120.0


def test_legacy_transport_contains_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(judge, "_execute_http_request", lambda *_args, **_kwargs: None)
    config = JudgeConfig(
        model="legacy-model",
        base_url="https://legacy.invalid/v1",
        timeout=5.0,
    )

    assert (
        judge._try_legacy_judge(
            config,
            "work",
            CATALOG,
            1,
            1,
            0.0,
            request_timeout=1.0,
        )
        is None
    )


def test_ollama_mode_overrides_conflicting_anthropic_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    decision = {"selected_ids": ["security-reviewer"], "confidence": 0.86}

    def respond(request: Any, **kwargs: Any) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads(request.data)
        captured["timeout"] = kwargs["timeout"]
        return _Response({"message": {"content": json.dumps(decision)}})

    monkeypatch.setattr(judge, "open_no_redirect", respond)
    provider = ProviderEntry(
        name="mixed-mode",
        type="anthropic",
        model="local-model",
        base_url="https://provider.invalid",
        api_key="secret",
        ollama_mode=True,
        timeout=3.0,
    )

    result = judge._try_provider(provider, "work", CATALOG, 1, 1, 0.0)

    assert result is not None
    assert result["provider"] == "mixed-mode (ollama)"
    assert result["selected_ids"] == ["security-reviewer"]
    assert captured["url"] == "https://provider.invalid/api/chat"
    assert captured["headers"]["authorization"] == "Bearer secret"
    assert "x-api-key" not in captured["headers"]
    assert captured["body"]["format"] == "json"
    assert captured["timeout"] == 3.0
