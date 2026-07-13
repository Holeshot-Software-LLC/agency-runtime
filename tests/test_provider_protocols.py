"""Provider transport contracts for routing-judge HTTP calls."""

from __future__ import annotations

import json

from agency_runtime.core.config import ProviderEntry
from agency_runtime.core.selector import judge

CATALOG = [{"slug": "security-reviewer", "description": "Reviews application security."}]


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size: int = -1) -> bytes:
        body = json.dumps(self.payload).encode("utf-8")
        return body if size < 0 else body[:size]


def test_openai_compatible_base_v1_is_not_duplicated(monkeypatch):
    captured = {}

    def fake_urlopen(request, **kwargs):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data)
        captured["timeout"] = kwargs["timeout"]
        return _Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"selected_ids":["security-reviewer"],"confidence":0.9}'
                        }
                    }
                ],
            }
        )

    monkeypatch.setattr(judge, "open_no_redirect", fake_urlopen)
    provider = ProviderEntry(
        name="openai",
        type="openai-compatible",
        model="gpt-5.4-mini",
        base_url="https://api.openai.com/v1",
        api_key="secret",
    )

    result = judge._try_provider(provider, "review security", CATALOG, 3, 1, 5.0)

    assert result is not None
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["body"]["model"] == "gpt-5.4-mini"
    assert captured["body"]["max_completion_tokens"] == 256
    assert "max_tokens" not in captured["body"]
    assert "temperature" not in captured["body"]


def test_anthropic_provider_uses_messages_protocol(monkeypatch):
    captured = {}

    def fake_urlopen(request, **kwargs):
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads(request.data)
        return _Response(
            {
                "content": [
                    {
                        "type": "text",
                        "text": '{"selected_ids":["security-reviewer"],"confidence":0.88}',
                    }
                ],
            }
        )

    monkeypatch.setattr(judge, "open_no_redirect", fake_urlopen)
    provider = ProviderEntry(
        name="anthropic",
        type="anthropic",
        model="claude-sonnet-5",
        base_url="https://api.anthropic.com/v1",
        api_key="secret",
    )

    result = judge._try_provider(provider, "review security", CATALOG, 3, 1, 5.0)

    assert result is not None
    assert result["selected_ids"] == ["security-reviewer"]
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["headers"]["x-api-key"] == "secret"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert "authorization" not in captured["headers"]
    assert captured["body"]["model"] == "claude-sonnet-5"
    assert captured["body"]["system"].startswith("You are a semantic selector")


def test_model_discovery_does_not_duplicate_v1(monkeypatch):
    from agency_runtime.core import detect

    captured = {}

    def fake_get(url, **_kwargs):
        captured["url"] = url
        return {"data": [{"id": "gpt-5.4-mini"}]}

    monkeypatch.setattr(detect, "_http_get_json", fake_get)

    models = detect._fetch_model_list("https://api.openai.com/v1", "secret")

    assert models == ["gpt-5.4-mini"]
    assert captured["url"] == "https://api.openai.com/v1/models"


def test_detected_model_selection_prefers_supported_current_default():
    from agency_runtime.core.detect import _preferred_model

    selected = _preferred_model(
        ["aaa-experimental", "gpt-5.4", "gpt-5.4-mini"],
        ["gpt-5.4-mini", "gpt-5.4"],
        "fallback",
    )

    assert selected == "gpt-5.4-mini"


def test_local_only_config_never_selects_network_provider():
    from agency_runtime.core.detect import (
        DetectionResult,
        ProviderDetection,
        generate_config_from_detection,
    )

    detection = DetectionResult(
        providers=ProviderDetection(
            openai_key_present=True,
            openai_models=["gpt-5.4-mini"],
            anthropic_key_present=True,
            litellm_available=True,
            litellm_models=["remote-model"],
            ollama_available=False,
        )
    )

    config = generate_config_from_detection(detection, profile="local-only")

    assert config["providers"] == []
    assert config["judge"]["base_url"] == "http://127.0.0.1:11434"
    assert config["judge"]["ollama_mode"] is True
    assert all(entry["enabled"] == "false" for entry in config["adapters"].values())
