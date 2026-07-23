"""Behavior coverage for interactive provider wizard branches."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from agency_runtime.cli import config_wizard as subject
from agency_runtime.core.detect import ProviderDetection


def provider(**changes):
    values = {
        "ollama_available": True,
        "ollama_models": ["local-model"],
        "ollama_base_url": "http://127.0.0.1:11434",
        "openai_models": ["openai-model"],
        "litellm_available": True,
        "litellm_models": ["proxy-model"],
        "litellm_base_url": "http://127.0.0.1:4000",
    }
    values.update(changes)
    return ProviderDetection(**values)


def detection(**changes):
    values = {
        "providers": provider(),
        "adapters": SimpleNamespace(
            hermes=True,
            openclaw=False,
            codex=True,
            claude=False,
        ),
        "cli_providers": {
            "codex": SimpleNamespace(installed=True, usable=True),
            "claude": SimpleNamespace(installed=True, usable=False),
        },
    }
    values.update(changes)
    return SimpleNamespace(**values)


def dependencies(**changes):
    values = {
        "detect": lambda: detection(),
        "secret_prompt": lambda _prompt: "secret",
        "open_url": lambda *_a, **_kw: None,
        "provider_validator": lambda *_a, **_kw: SimpleNamespace(usable=True, reason=""),
        "model_fetcher": None,
    }
    values.update(changes)
    return subject.WizardDependencies(**values)


def test_model_boundary_and_profile_prompt(monkeypatch, capsys):
    fetched = []
    deps = dependencies(model_fetcher=lambda url, key: fetched.append((url, key)) or ["model"])
    assert subject._models("http://localhost", "key", deps) == ["model"]
    assert fetched == [("http://localhost", "key")]
    monkeypatch.setattr(
        subject,
        "_fetch_models_custom",
        lambda url, key, **_kw: [f"{url}:{key}"],
    )
    assert subject._models("http://fallback", None, dependencies()) == ["http://fallback:None"]
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 4)
    assert subject._prompt_install_profile() == "yolo"
    assert "Install Profile" in capsys.readouterr().out


def test_detection_profile_restores_present_keys_and_leaves_absent_keys_absent(
    monkeypatch,
):
    observed = []
    monkeypatch.setenv("OPENAI_API_KEY", "openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    detected = detection()

    def detect():
        observed.append((os.environ.get("OPENAI_API_KEY"), os.environ.get("ANTHROPIC_API_KEY")))
        return detected

    assert (
        subject._detect_for_profile("standard", dependencies=dependencies(detect=detect))
        is detected
    )
    assert observed.pop() == ("openai", None)
    assert (
        subject._detect_for_profile("local-only", dependencies=dependencies(detect=detect))
        is detected
    )
    assert observed == [(None, None)]
    assert os.environ["OPENAI_API_KEY"] == "openai"
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert detected.providers.openai_models == []
    assert not detected.providers.openai_key_present
    assert not detected.providers.anthropic_key_present


def test_detection_restores_environment_even_when_detector_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai")
    with pytest.raises(RuntimeError, match="detector failed"):
        subject._detect_for_profile(
            "local-only",
            dependencies=dependencies(
                detect=lambda: (_ for _ in ()).throw(RuntimeError("detector failed"))
            ),
        )
    assert os.environ["OPENAI_API_KEY"] == "openai"


def test_interactive_wizard_advanced_tuning_and_litellm_recursion_guard(
    monkeypatch,
):
    detected = detection()
    generated = {
        "judge": {
            "model": "proxy-model",
            "base_url": detected.providers.litellm_base_url,
        }
    }
    chain = [
        {
            "name": "litellm",
            "type": "litellm",
            "model": "proxy-model",
            "base_url": detected.providers.litellm_base_url,
        }
    ]
    answers = iter(["n", "7", "4", "9"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(
        subject,
        "generate_config_from_detection",
        lambda *_a, **_kw: generated,
    )
    monkeypatch.setattr(subject, "_guided_provider_chain", lambda *_a, **_kw: chain)
    monkeypatch.setattr(subject, "_print_config_summary", lambda _data: None)
    result = subject._interactive_wizard(detected, "standard")
    assert result["judge"]["timeout"] == 7.0
    assert result["judge"]["max_selected"] == 4
    assert result["judge"]["confidence_bypass_threshold"] == 9.0
    assert result["providers"][0]["timeout"] == 7.0
    assert "proxy-model" in result["adapters"]["litellm"]["skip_models"]
    assert result["adapters"]["hermes"]["enabled"] == "true"
    assert result["adapters"]["openclaw"]["enabled"] == "auto"


def test_interactive_wizard_gives_subscription_cli_a_realistic_default_timeout(
    monkeypatch,
):
    detected = detection()
    chain = [
        {
            "name": "codex-subscription",
            "type": "cli",
            "transport": "codex",
            "model": "gpt-cheap",
        },
        {
            "name": "local",
            "type": "ollama",
            "model": "local-model",
            "base_url": "http://127.0.0.1:11434",
        },
    ]
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    monkeypatch.setattr(subject, "_guided_provider_chain", lambda *_a, **_kw: chain)
    monkeypatch.setattr(subject, "_print_config_summary", lambda _data: None)

    result = subject._interactive_wizard(detected, "standard")

    assert result["judge"]["timeout"] == subject.DEFAULT_PROVIDER_TIMEOUT
    assert result["providers"][0]["timeout"] == subject.DEFAULT_CLI_PROVIDER_TIMEOUT
    assert result["providers"][1]["timeout"] == subject.DEFAULT_PROVIDER_TIMEOUT


def test_legacy_judge_and_provider_entry_variants():
    http = {
        "model": "model",
        "base_url": "http://localhost",
        "api_key": "key",
        "api_key_env": "KEY",
        "ollama_mode": True,
    }
    assert subject._legacy_judge_from_chain([{"type": "cli"}, http], {"model": "fallback"}) == http
    assert subject._legacy_judge_from_chain([], {"model": "fallback"}) == {"model": "fallback"}
    entry = subject._provider_entry(
        "codex-cli", "cli", {"model": "override", "timeout": 3}, transport="codex"
    )
    assert entry["transport"] == "codex"
    assert entry["timeout"] == 3.0


@pytest.mark.parametrize(
    ("choice", "expected_type", "expected_transport"),
    [
        (1, "ollama", ""),
        (2, "openai-compatible", ""),
        (3, "anthropic", ""),
        (4, "litellm", ""),
        (5, "cli", "codex"),
        (6, "cli", "claude"),
        (7, "openai-compatible", ""),
    ],
)
def test_new_provider_dispatches_every_standard_provider(
    monkeypatch, choice, expected_type, expected_transport
):
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: choice)
    monkeypatch.setattr(subject, "_pick_ollama_model", lambda _p: {"model": "ollama"})
    monkeypatch.setattr(subject, "_pick_openai_model", lambda *_a, **_kw: {"model": "openai"})
    monkeypatch.setattr(subject, "_pick_anthropic_model", lambda **_kw: {"model": "anthropic"})
    monkeypatch.setattr(subject, "_pick_litellm_model", lambda *_a, **_kw: {"model": "litellm"})
    monkeypatch.setattr(
        subject,
        "_pick_custom_endpoint",
        lambda **_kw: {"model": "custom", "base_url": "https://custom.invalid"},
    )
    answers = iter(["override", "custom-name"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    result = subject._new_provider_entry(detection(), "standard")
    assert result is not None
    assert result["type"] == expected_type
    assert result["transport"] == expected_transport


def test_new_provider_cancel_local_loopback_gate_and_custom_name(monkeypatch, capsys):
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 3)
    assert subject._new_provider_entry(detection(), "local-only") is None
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 2)
    monkeypatch.setattr(
        subject,
        "_pick_custom_endpoint",
        lambda **_kw: {"model": "remote", "base_url": "https://remote.invalid"},
    )
    assert subject._new_provider_entry(detection(), "local-only") is None
    assert "literal loopback" in capsys.readouterr().out
    monkeypatch.setattr(
        subject,
        "_pick_custom_endpoint",
        lambda **_kw: {"model": "local", "base_url": "http://127.0.0.1:1"},
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert subject._new_provider_entry(detection(), "local-only")["name"] == "custom"


def test_guided_chain_add_duplicate_move_remove_and_done(monkeypatch, capsys):
    detected = detection()
    monkeypatch.setattr(
        subject,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": [{"name": "first", "type": "cli"}]},
    )
    choices = iter([2, 1, 1, 3, 1, 4])
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: next(choices))
    entries = iter(
        [
            {"name": "first", "type": "cli"},
            {"name": "second", "type": "cli"},
        ]
    )
    monkeypatch.setattr(subject, "_new_provider_entry", lambda *_a, **_kw: next(entries))
    result = subject._guided_provider_chain(detected, "standard")
    assert result == [{"name": "second", "type": "cli"}]
    output = capsys.readouterr().out
    assert "at least two" in output
    assert "already exists" in output


def test_provider_chain_validation_usable_unavailable_and_invalid(monkeypatch, capsys):
    results = iter(
        [
            SimpleNamespace(usable=True, reason=""),
            SimpleNamespace(usable=False, reason="offline"),
        ]
    )
    deps = dependencies(provider_validator=lambda *_a, **_kw: next(results))
    providers = [
        {"name": "first", "type": "cli", "transport": "codex", "timeout": 10},
        {"name": "second", "type": "cli", "transport": "claude", "timeout": 3},
        {"unexpected": "invalid"},
    ]
    assert not subject._validate_interactive_provider_chain(providers, dependencies=deps)
    output = capsys.readouterr().out
    assert "providers.0 (first): usable" in output
    assert "providers.1 (second): offline" in output
    assert "providers.2: invalid configuration" in output


def test_ollama_picker_manual_discovered_truncated_and_custom(monkeypatch, capsys):
    manual = provider(ollama_models=[])
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    assert subject._pick_ollama_model(manual)["model"] == "qwen3.5:2b"
    discovered = provider(ollama_models=[f"model-{index}" for index in range(16)])
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 1)
    assert subject._pick_ollama_model(discovered)["model"] == "model-0"
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 16)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "custom")
    assert subject._pick_ollama_model(discovered)["model"] == "custom"
    assert "and 1 more" in capsys.readouterr().out


def test_prompt_auth_direct_loopback_env_and_empty_rejection(monkeypatch):
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 2)
    assert subject._prompt_provider_auth(
        default_env="KEY",
        base_url="https://remote.invalid",
        dependencies=dependencies(secret_prompt=lambda _prompt: " direct "),
    ) == ({"api_key": "direct"}, "direct")
    with pytest.raises(ValueError, match="must not be empty"):
        subject._prompt_provider_auth(
            default_env="KEY",
            base_url="https://remote.invalid",
            dependencies=dependencies(secret_prompt=lambda _prompt: " "),
        )
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 3)
    assert subject._prompt_provider_auth(
        default_env="KEY", base_url="http://127.0.0.1", dependencies=dependencies()
    ) == ({"api_key": ""}, "")
    monkeypatch.setenv("CUSTOM_KEY", "resolved")
    monkeypatch.setattr(subject, "_prompt_choice", lambda *_a, **_kw: 1)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "CUSTOM_KEY")
    assert subject._prompt_provider_auth(
        default_env="KEY",
        base_url="https://remote.invalid",
        dependencies=dependencies(),
    ) == ({"api_key_env": "CUSTOM_KEY"}, "resolved")


def test_config_summary_and_prompt_choice_paths(monkeypatch, capsys):
    for judge, expected in (
        ({"api_key_env": "KEY"}, "from $KEY"),
        ({"api_key": "direct"}, "stored in config"),
        ({}, "none (free/local)"),
    ):
        subject._print_config_summary({"judge": judge, "profile": "standard"})
        assert expected in capsys.readouterr().out
    answers = iter(["not-a-number", "9", "2", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    assert subject._prompt_choice(3) == 2
    assert "Enter a number" in capsys.readouterr().out
    assert subject._prompt_choice(3, default=3) == 3
