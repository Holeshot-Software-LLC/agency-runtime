"""Complete provider, host, and model-discovery branch coverage."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core import detect
from agency_runtime.core.cli_transport import CLIProviderStatus


class _Response:
    def __init__(self, status: int, payload: bytes = b"{}") -> None:
        self.status = status
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _size: int) -> bytes:
        return self.payload


def test_detection_compatibility_properties_and_aggregate_flags() -> None:
    providers = detect.ProviderDetection(openai_key_present=True, anthropic_key_present=True)
    assert providers.openai_key is True
    assert providers.anthropic_key is True
    result = detect.DetectionResult(providers=providers)
    assert result.has_any_provider is True
    assert result.has_any_adapter is False
    result.adapters.codex = True
    assert result.has_any_adapter is True

    cli_only = detect.DetectionResult(
        cli_providers={
            "codex": CLIProviderStatus(
                transport="codex",
                installed=True,
                authenticated=True,
                usable=True,
            )
        }
    )
    assert cli_only.has_any_provider is True


def test_http_helpers_handle_status_nonobject_and_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(detect, "open_no_redirect", lambda *_args, **_kwargs: _Response(204))
    assert detect._http_check("https://example.invalid") is False
    monkeypatch.setattr(detect, "open_no_redirect", lambda *_args, **_kwargs: _Response(200))
    assert detect._http_check("https://example.invalid") is True
    assert detect._http_get_json("https://example.invalid") == {}
    monkeypatch.setattr(
        detect,
        "open_no_redirect",
        lambda *_args, **_kwargs: _Response(200, b"[]"),
    )
    assert detect._http_get_json("https://example.invalid") is None
    monkeypatch.setattr(
        detect,
        "open_no_redirect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    assert detect._http_check("https://example.invalid") is False
    assert detect._http_get_json("https://example.invalid") is None


def test_model_list_rejects_invalid_payload_shapes_and_identifiers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(detect, "_http_get_json", lambda *_args, **_kwargs: None)
    assert detect._fetch_model_list("https://example.invalid") == []
    monkeypatch.setattr(detect, "_http_get_json", lambda *_args, **_kwargs: {"data": {}})
    assert detect._fetch_model_list("https://example.invalid") == []
    monkeypatch.setattr(
        detect,
        "_http_get_json",
        lambda *_args, **_kwargs: {
            "data": [
                "invalid",
                {"id": 1},
                {"id": " valid-whitespace "},
                {"id": "bad\x7fcontrol"},
                {"model": "valid-model"},
            ]
        },
    )
    assert detect._fetch_model_list("https://example.invalid") == ["valid-model"]


def test_provider_detection_filters_invalid_ollama_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def get_json(url: str, **_kwargs: Any) -> dict[str, Any]:
        assert url.endswith("/api/tags")
        return {
            "models": [
                "invalid",
                {"name": 1},
                {"name": " valid "},
                {"name": "   "},
                {"model": "fallback"},
            ]
        }

    monkeypatch.setattr(detect, "_http_get_json", get_json)
    monkeypatch.setattr(detect, "_http_check", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(detect, "_fetch_model_list", lambda *_args, **_kwargs: [])
    result = detect.detect_providers()
    assert result.ollama_available is True
    assert result.ollama_models == ["fallback", "valid"]


@pytest.mark.parametrize("tags", [None, {"models": {}}])
def test_provider_detection_handles_absent_or_invalid_ollama_model_lists(
    monkeypatch: pytest.MonkeyPatch,
    tags: dict[str, Any] | None,
) -> None:
    monkeypatch.setattr(detect, "_http_get_json", lambda *_args, **_kwargs: tags)
    monkeypatch.setattr(detect, "_http_check", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(detect, "_fetch_model_list", lambda *_args, **_kwargs: ["judge"])
    result = detect.detect_providers()
    assert result.ollama_available is (tags is not None)
    assert result.ollama_models == []
    assert result.litellm_available is True
    assert result.litellm_models == ["judge"]


def test_adapter_detection_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from agency_runtime.core import installer

    monkeypatch.setattr(
        installer,
        "detect_installed_agents",
        lambda: (_ for _ in ()).throw(OSError("inventory unavailable")),
    )
    assert detect.detect_adapters() == detect.AdapterDetection()


def test_cli_provider_detection_preserves_transport_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(detect, "SUPPORTED_CLI_TRANSPORTS", {"codex", "claude"})
    monkeypatch.setattr(
        detect,
        "inspect_cli_transport",
        lambda name: CLIProviderStatus(
            transport=name,
            installed=True,
            authenticated=False,
            usable=False,
        ),
    )
    statuses = detect.detect_cli_providers()
    assert list(statuses) == ["claude", "codex"]
    assert all(status.transport == name for name, status in statuses.items())


def test_detect_all_runs_independent_probes_and_preserves_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers = detect.ProviderDetection(ollama_available=True)
    adapters = detect.AdapterDetection(codex=True)
    cli = {
        "codex": CLIProviderStatus(
            transport="codex",
            installed=True,
            authenticated=True,
            usable=True,
        )
    }
    monkeypatch.setattr(detect, "detect_providers", lambda: providers)
    monkeypatch.setattr(detect, "detect_adapters", lambda: adapters)
    monkeypatch.setattr(detect, "detect_cli_providers", lambda: cli)
    assert detect.detect_all() == detect.DetectionResult(providers, adapters, cli)


def test_litellm_generation_handles_duplicate_skip_and_missing_model() -> None:
    providers = detect.ProviderDetection(
        litellm_available=True,
        litellm_base_url="http://127.0.0.1:4000",
    )
    assert detect._litellm_provider(providers, {}) is None
    duplicate = detect._litellm_skip_models(
        providers,
        {"base_url": providers.litellm_base_url, "model": "complexity_router"},
    )
    assert duplicate == ["complexity_router", "auto_router/"]
    appended = detect._litellm_skip_models(
        providers,
        {"base_url": providers.litellm_base_url, "model": "judge"},
    )
    assert appended[-1] == "judge"
