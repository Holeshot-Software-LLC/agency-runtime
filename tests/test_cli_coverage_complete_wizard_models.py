"""Security and long-list coverage for wizard model discovery and selection."""

from __future__ import annotations

import json

import pytest

from agency_runtime.cli import config_wizard as subject
from agency_runtime.core.detect import ProviderDetection


def deps(**changes):
    values = {
        "detect": lambda: None,
        "secret_prompt": lambda _prompt: "secret",
        "open_url": lambda *_a, **_kw: None,
        "provider_validator": lambda *_a, **_kw: None,
        "model_fetcher": None,
    }
    values.update(changes)
    return subject.WizardDependencies(**values)


def provider(**changes):
    values = {
        "openai_models": ["detected-openai"],
        "litellm_models": ["detected-proxy"],
        "litellm_base_url": "http://127.0.0.1:4000",
    }
    values.update(changes)
    return ProviderDetection(**values)


def test_openai_picker_deduplicates_truncates_and_allows_custom(monkeypatch, capsys):
    discovered = [f"model-{index}" for index in range(17)]
    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key": "key"}, "key"),
    )
    monkeypatch.setattr(subject, "_models", lambda *_args: discovered)
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 16)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    result = subject._pick_openai_model(provider())
    assert result["model"] == "gpt-4o-mini"
    assert result["api_key"] == "key"
    assert "and" in capsys.readouterr().out

    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key_env": "OPENAI_API_KEY"}, ""),
    )
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 1)
    assert subject._pick_openai_model(provider())["model"] == "detected-openai"


def test_anthropic_picker_suggestion_and_custom_default(monkeypatch):
    from agency_runtime.core.detect import _ANTHROPIC_SUGGESTIONS

    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key_env": "ANTHROPIC_API_KEY"}, ""),
    )
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 1)
    assert subject._pick_anthropic_model()["model"] == _ANTHROPIC_SUGGESTIONS[0]
    monkeypatch.setattr(
        subject,
        "_prompt_choice",
        lambda *_a, **_kw: len(_ANTHROPIC_SUGGESTIONS) + 1,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert subject._pick_anthropic_model()["model"] == "claude-3-5-sonnet-20241022"


def test_litellm_picker_discovery_custom_and_fallback(monkeypatch, capsys):
    models = [f"group-{index}" for index in range(16)]
    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key": "key"}, "key"),
    )
    monkeypatch.setattr(subject, "_models", lambda *_args: models)
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 16)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "custom-group")
    assert subject._pick_litellm_model(provider())["model"] == "custom-group"
    assert "and 1 more" in capsys.readouterr().out

    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key_env": "LITELLM_API_KEY"}, ""),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    empty = provider(litellm_models=[])
    assert subject._pick_litellm_model(empty)["model"] == "task-general"
    assert "Couldn't discover" in capsys.readouterr().out


def test_custom_endpoint_preset_manual_discovered_and_missing(monkeypatch, capsys):
    choices = iter([4, 16])
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: next(choices))
    monkeypatch.setattr(
        subject,
        "_prompt_provider_auth",
        lambda **_kwargs: ({"api_key": ""}, ""),
    )
    monkeypatch.setattr(
        subject,
        "_models",
        lambda *_args: [f"model-{index}" for index in range(16)],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "custom-model")
    result = subject._pick_custom_endpoint()
    assert result["base_url"] == "http://127.0.0.1:1234/v1"
    assert result["model"] == "custom-model"
    assert "and 1 more" in capsys.readouterr().out

    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 5)
    monkeypatch.setattr(subject, "_models", lambda *_args: [])
    answers = iter(["https://manual.invalid/v1", "manual-model"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    result = subject._pick_custom_endpoint()
    assert result["base_url"] == "https://manual.invalid/v1"
    assert result["model"] == "manual-model"
    assert "Could not discover" in capsys.readouterr().out


def test_prompt_auth_default_environment_name(monkeypatch):
    monkeypatch.setenv("DEFAULT_KEY", "resolved")
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 1)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert subject._prompt_provider_auth(
        default_env="DEFAULT_KEY",
        base_url="https://remote.invalid",
    ) == ({"api_key_env": "DEFAULT_KEY"}, "resolved")


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _size=-1):
        return self.data


def test_model_fetch_rejects_unsafe_credential_url_without_network(monkeypatch):
    called = []
    result = subject._fetch_models_custom(
        "http://remote.invalid/v1",
        "secret",
        dependencies=deps(open_url=lambda *_a, **_kw: called.append(True)),
    )
    assert result == [] and called == []


def test_model_fetch_authenticates_normalizes_bounds_and_caps(monkeypatch):
    observed = []
    payload = {
        "data": [
            None,
            {},
            {"id": ""},
            {"id": " leading"},
            {"id": "control\x00"},
            {"id": "x" * (subject.MAX_MODEL_ID_CHARS + 1)},
            {"model": "second"},
            {"id": "first"},
            {"id": "third"},
        ]
    }

    def open_url(request, *, timeout):
        observed.append((request, timeout))
        return Response(json.dumps(payload).encode())

    monkeypatch.setattr(subject, "MAX_DISCOVERED_MODELS", 2)
    result = subject._fetch_models_custom(
        "https://safe.invalid/v1/",
        "secret",
        dependencies=deps(open_url=open_url),
    )
    assert result == ["first", "second"]
    request, timeout = observed[0]
    assert request.full_url == "https://safe.invalid/v1/models"
    assert request.get_header("Authorization") == "Bearer secret"
    assert timeout == 5


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"data": "invalid"},
        b"not-json",
    ],
)
def test_model_fetch_rejects_malformed_shapes_and_transport_errors(payload):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    assert (
        subject._fetch_models_custom(
            "http://127.0.0.1:1",
            dependencies=deps(open_url=lambda *_a, **_kw: Response(raw)),
        )
        == []
    )
    assert (
        subject._fetch_models_custom(
            "http://127.0.0.1:1",
            dependencies=deps(
                open_url=lambda *_a, **_kw: (_ for _ in ()).throw(OSError("offline"))
            ),
        )
        == []
    )


def test_model_fetch_rejects_oversized_payload(monkeypatch):
    monkeypatch.setattr(subject, "MAX_MODEL_DISCOVERY_BYTES", 8)
    assert (
        subject._fetch_models_custom(
            "http://127.0.0.1:1",
            dependencies=deps(open_url=lambda *_a, **_kw: Response(b"x" * 9)),
        )
        == []
    )
