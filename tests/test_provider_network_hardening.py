"""Deterministic production-boundary tests for provider networking."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from agency_runtime.core import detect, doctor, provider_validation
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
    StoreConfig,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.doctor import CheckResult, DoctorReport, run_doctor
from agency_runtime.core.selector import judge
from agency_runtime.core.store.sqlite import Store

CATALOG = [
    {
        "slug": "security-reviewer",
        "description": "Reviews authentication and application security.",
    }
]


@pytest.fixture(autouse=True)
def _isolated_config_cache() -> Iterator[None]:
    reset_config_cache()
    yield
    reset_config_cache()


class _Response:
    def __init__(self, body: bytes = b"{}", *, status: int = 200) -> None:
        self.body = body
        self.status = status
        self.read_sizes: list[int] = []

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.body if size < 0 else self.body[:size]


def _provider(index: int, *, timeout: float = 10.0) -> ProviderEntry:
    return ProviderEntry(
        name=f"provider-{index}",
        model=f"judge-{index}",
        base_url=f"https://provider-{index}.invalid/v1",
        api_key="key",
        timeout=timeout,
    )


def test_local_only_is_enforced_after_file_and_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "profile": "standard",
                "judge": {
                    "model": "remote-judge",
                    "base_url": "https://judge.example/v1",
                    "api_key": "file-secret",
                    "ollama_mode": False,
                },
                "ollama": {
                    "enabled": True,
                    "base_url": "https://remote-ollama.example",
                    "model": "local-model",
                },
                "providers": [
                    {
                        "name": "remote",
                        "type": "openai-compatible",
                        "model": "remote-model",
                        "base_url": "https://provider.example/v1",
                        "api_key": "provider-secret",
                    }
                ],
                "adapters": {
                    name: {"enabled": True}
                    for name in ("litellm", "hermes", "openclaw", "codex", "claude")
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_PROFILE", "local-only")
    monkeypatch.setenv("AGENCY_JUDGE_BASE_URL", "https://env-judge.example/v1")
    monkeypatch.setenv("AGENCY_JUDGE_API_KEY", "env-secret")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://env-ollama.example")
    cfg = load_config(config_path, reload=True)

    assert cfg.profile == "local-only"
    assert cfg.judge.base_url == "http://127.0.0.1:11434"
    assert cfg.judge.model == "local-model"
    assert cfg.judge.api_key == cfg.judge.api_key_env == ""
    assert cfg.judge.ollama_mode is True
    assert cfg.providers == ()
    assert all(
        entry.enabled == "false"
        for entry in (
            cfg.adapters.litellm,
            cfg.adapters.hermes,
            cfg.adapters.openclaw,
            cfg.adapters.codex,
            cfg.adapters.claude,
        )
    )


def test_detection_bounds_response_bytes_and_model_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized = _Response(b"x" * (detect._MAX_HTTP_JSON_BYTES + 10))
    monkeypatch.setattr(detect, "open_no_redirect", lambda *_a, **_kw: oversized)

    assert detect._http_get_json("https://models.invalid") is None
    assert oversized.read_sizes == [detect._MAX_HTTP_JSON_BYTES + 1]

    monkeypatch.setattr(
        detect,
        "_http_get_json",
        lambda *_a, **_kw: {"data": [{"id": f"model-{index:04d}"} for index in range(1200)]},
    )
    models = detect._fetch_model_list("https://models.invalid")
    assert len(models) == detect._MAX_DISCOVERED_MODELS
    assert models == sorted(models)


@pytest.mark.parametrize(
    "base_url",
    [
        "http://provider.invalid/v1",
        "https://provider.invalid/v1?token=leaky",
    ],
)
def test_shared_detection_never_sends_credentials_to_unsafe_base(
    base_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_args: Any, **_kwargs: Any) -> _Response:
        raise AssertionError("credentialed discovery attempted")

    monkeypatch.setattr(detect, "open_no_redirect", unexpected_call)

    assert detect._fetch_model_list(base_url, "secret") == []


def test_judge_caps_provider_attempts_and_fails_without_a_fallback_team(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail(request: Any, **_kwargs: Any) -> _Response:
        calls.append(request.full_url)
        raise TimeoutError("offline")

    monkeypatch.setattr(judge, "open_no_redirect", fail)
    cfg = AgencyConfig(
        providers=tuple(_provider(index) for index in range(10)),
        judge=JudgeConfig(model="", timeout=60, confidence_bypass_threshold=999),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    result = judge.query_judge("review authentication security", CATALOG, config=cfg)

    assert len(calls) == judge._MAX_PROVIDER_ATTEMPTS
    assert result["status"] == "inference_unavailable"
    assert result["inference_mode"] == "unavailable"
    assert result["selected_ids"] == []
    assert "deterministic_candidate_ids" not in result
    assert len(result["provider_attempts"]) == judge._MAX_PROVIDER_ATTEMPTS


def test_judge_uses_only_remaining_end_to_end_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = {"value": 0.0}
    timeouts: list[float] = []

    monkeypatch.setattr(judge.time, "monotonic", lambda: now["value"])

    def fail(_request: Any, **kwargs: Any) -> _Response:
        timeout = float(kwargs["timeout"])
        timeouts.append(timeout)
        now["value"] += min(6.0, timeout)
        raise TimeoutError("deadline")

    monkeypatch.setattr(judge, "open_no_redirect", fail)
    cfg = AgencyConfig(
        providers=tuple(_provider(index) for index in range(3)),
        judge=JudgeConfig(model="", timeout=10, confidence_bypass_threshold=999),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    result = judge.query_judge("review authentication security", CATALOG, config=cfg)

    assert timeouts == pytest.approx([10.0, 4.0])
    assert result["status"] == "inference_unavailable"
    assert result["inference_attempted"] is True
    assert result["latency_ms"] == 10_000


def test_typed_provider_failure_does_not_retry_as_wrong_legacy_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail(request: Any, **_kwargs: Any) -> _Response:
        calls.append(request.full_url)
        raise TimeoutError("offline")

    monkeypatch.setattr(judge, "open_no_redirect", fail)
    provider = ProviderEntry(
        name="anthropic",
        type="anthropic",
        model="claude-test",
        base_url="https://api.anthropic.invalid/v1",
        api_key="secret",
    )
    cfg = AgencyConfig(
        providers=(provider,),
        judge=JudgeConfig(
            model=provider.model,
            base_url=provider.base_url,
            api_key="secret",
            timeout=10,
            confidence_bypass_threshold=999,
        ),
        ollama=OllamaConfig(enabled=False, model=""),
    )

    result = judge.query_judge("review authentication security", CATALOG, config=cfg)

    assert calls == ["https://api.anthropic.invalid/v1/messages"]
    assert result["status"] == "inference_unavailable"
    assert result["provider_attempts"] == [
        {
            "provider_name": "anthropic",
            "provider_type": "anthropic",
            "requested_model": "claude-test",
            "model_group": "",
            "status": "failed",
            "reason": "provider_call_failed",
        }
    ]


def test_judge_rejects_oversized_provider_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _Response(b"x" * (judge._MAX_JUDGE_RESPONSE_BYTES + 10))
    monkeypatch.setattr(judge, "open_no_redirect", lambda *_a, **_kw: response)

    result = judge._try_provider(
        _provider(1),
        "review authentication security",
        CATALOG,
        3,
        1,
        5.0,
    )

    assert result is None
    assert response.read_sizes == [judge._MAX_JUDGE_RESPONSE_BYTES + 1]


def test_programmatic_provider_and_legacy_judge_never_send_credentials_over_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_args: Any, **_kwargs: Any) -> _Response:
        raise AssertionError("unsafe authenticated request attempted")

    monkeypatch.setattr(judge, "open_no_redirect", unexpected_call)
    provider = ProviderEntry(
        name="remote",
        model="model",
        base_url="http://provider.invalid/v1",
        api_key="secret",
    )
    legacy = JudgeConfig(
        model="model",
        base_url="http://judge.invalid/v1",
        api_key="secret",
        ollama_mode=False,
    )

    assert judge._try_provider(provider, "task", CATALOG, 1, 1, 1.0) is None
    assert judge._try_legacy_judge(legacy, "task", CATALOG, 1, 1, 1.0) is None
    validation = provider_validation.validate_provider(
        provider,
        opener=unexpected_call,
    )
    assert validation.usable is False
    assert "HTTPS" in validation.reason
    assert doctor._http_check_authed(
        "http://adapter.invalid/v1/models",
        "secret",
    ) == (
        False,
        "credential transport requires HTTPS or literal loopback HTTP",
    )


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///tmp/provider",
        "https://provider.invalid/v1?probe=unsafe",
        "https://provider.invalid:not-a-port/v1",
    ],
)
def test_provider_validation_rejects_malformed_endpoints_before_network(
    base_url: str,
) -> None:
    def unexpected_call(*_args: Any, **_kwargs: Any) -> _Response:
        raise AssertionError("malformed endpoint reached the network")

    result = provider_validation.validate_provider(
        ProviderEntry(
            name="invalid",
            model="model",
            base_url=base_url,
            api_key="secret",
        ),
        opener=unexpected_call,
    )

    assert result.usable is False
    assert "HTTP(S)" in result.reason


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True])
def test_provider_validation_rejects_invalid_timeout_before_network(
    timeout: object,
) -> None:
    def unexpected_call(*_args: Any, **_kwargs: Any) -> _Response:
        raise AssertionError("invalid timeout reached the network")

    result = provider_validation.validate_provider(
        _provider(1),
        timeout=timeout,  # type: ignore[arg-type]
        opener=unexpected_call,
    )

    assert result.usable is False
    assert result.reason == "validation timeout is invalid"


@pytest.mark.parametrize(
    "response_status,expected_authenticated",
    [(200, True), (401, False), (403, False), (500, None)],
)
def test_provider_validation_reports_only_proven_authentication_state(
    response_status: int,
    expected_authenticated: bool | None,
) -> None:
    result = provider_validation.validate_provider(
        _provider(1),
        opener=lambda *_a, **_kw: _Response(status=response_status),
    )

    assert result.authenticated is expected_authenticated
    assert result.usable is (response_status == 200)


def test_provider_network_failure_does_not_claim_authentication() -> None:
    def fail(*_args: Any, **_kwargs: Any) -> _Response:
        raise TimeoutError("offline")

    result = provider_validation.validate_provider(_provider(1), opener=fail)

    assert result.usable is False
    assert result.authenticated is None


def test_doctor_probes_anthropic_with_typed_headers_and_redacts_urls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: list[tuple[str, dict[str, str]]] = []

    def respond(request: Any, **_kwargs: Any) -> _Response:
        captured.append(
            (
                request.full_url,
                {key.lower(): value for key, value in request.header_items()},
            )
        )
        return _Response(status=200)

    monkeypatch.setattr(doctor, "open_no_redirect", respond)
    monkeypatch.setattr(doctor, "inspect_host_installations", lambda **_kw: [])
    provider = ProviderEntry(
        name="anthropic",
        type="anthropic",
        model="claude-test",
        base_url="https://api.anthropic.invalid/v1",
        api_key="anthropic-secret",
    )
    cfg = AgencyConfig(
        providers=(provider,),
        judge=JudgeConfig(model="", confidence_bypass_threshold=999),
        ollama=OllamaConfig(enabled=False, model=""),
        store=StoreConfig(db_path=str(tmp_path / "doctor.db")),
    )
    Store(cfg.store.resolved_path())

    report = run_doctor(cfg)

    anthropic_calls = [item for item in captured if "api.anthropic.invalid" in item[0]]
    assert len(anthropic_calls) == 1
    url, headers = anthropic_calls[0]
    assert url.endswith("/v1/models")
    assert headers["x-api-key"] == "anthropic-secret"
    assert headers["anthropic-version"] == "2023-06-01"
    assert "authorization" not in headers
    rendered = json.dumps(report.to_dict())
    assert "anthropic-secret" not in rendered


def test_doctor_report_sanitizes_credential_bearing_diagnostics() -> None:
    report = DoctorReport(
        checks=[
            CheckResult(
                "network",
                "fail",
                "failed at https://user:password@example.invalid/v1?token=hidden",
                "https://user:password@example.invalid/detail#secret",
            )
        ]
    )

    rendered = json.dumps(report.to_dict())

    assert "user:password" not in rendered
    assert "token=hidden" not in rendered
    assert "#secret" not in rendered
    assert "https://example.invalid" in rendered
