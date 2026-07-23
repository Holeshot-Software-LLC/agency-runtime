from __future__ import annotations

from types import SimpleNamespace

import pytest

from agency_runtime.cli import config_commands, config_wizard, main
from agency_runtime.core.cli_transport import CLIModelCatalog, CLIModelInfo


def _state(providers, revision="rev"):
    return SimpleNamespace(persisted={"providers": providers}, revision=revision)


def _args(**values):
    defaults = {
        "json": False,
        "refresh": False,
        "timeout": 2,
        "transport": "codex",
        "name": "primary",
        "type": None,
        "model": None,
        "reasoning_effort": None,
        "base_url": None,
        "api_key_env": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_provider_commands_cover_list_and_model_catalogs(monkeypatch, capsys) -> None:
    assert config_commands._editable_providers(_state("invalid")) == []
    monkeypatch.setattr(config_commands, "read_config_state", lambda: _state([]))
    assert config_commands.cmd_config_provider_list(_args()) == 0
    assert "No inference providers" in capsys.readouterr().out

    captured = []
    monkeypatch.setattr(config_commands, "_print_json", captured.append)
    monkeypatch.setattr(
        config_commands,
        "read_config_state",
        lambda: _state(["bad", {"name": "primary", "type": "cli", "api_key": "secret"}]),
    )
    assert config_commands.cmd_config_provider_list(_args(json=True)) == 0
    assert captured == [{"providers": [{"name": "primary", "type": "cli"}]}]
    assert config_commands.cmd_config_provider_list(_args()) == 0
    assert "model/router=default" in capsys.readouterr().out

    model = CLIModelInfo("gpt-cheap", "Cheap", "Low cost", 1, "low")
    catalog = CLIModelCatalog("codex", (model,), "codex-cli", "now")
    monkeypatch.setattr(config_commands, "discover_cli_models", lambda *_a, **_k: catalog)
    assert config_commands.cmd_config_provider_models(_args(json=True)) == 0
    assert captured[-1]["models"][0]["slug"] == "gpt-cheap"
    assert config_commands.cmd_config_provider_models(_args()) == 0
    assert "Low cost" in capsys.readouterr().out

    empty = CLIModelCatalog("codex", (), "unavailable", "now", error="offline")
    monkeypatch.setattr(config_commands, "discover_cli_models", lambda *_a, **_k: empty)
    assert config_commands.cmd_config_provider_models(_args()) == 1
    assert "offline" in capsys.readouterr().out
    blank = CLIModelCatalog("codex", (), "unavailable", "now")
    monkeypatch.setattr(config_commands, "discover_cli_models", lambda *_a, **_k: blank)
    assert config_commands.cmd_config_provider_models(_args()) == 1
    assert "No visible models" in capsys.readouterr().out


def test_provider_set_update_remove_and_main_facade(monkeypatch, capsys) -> None:
    current = _state([])
    monkeypatch.setattr(config_commands, "read_config_state", lambda: current)
    with pytest.raises(ValueError, match="--type"):
        config_commands.cmd_config_provider_set(_args())

    operations = []

    def apply(items, *, expected_revision):
        operations.append((items, expected_revision))
        return SimpleNamespace(
            state=SimpleNamespace(environment_overrides={}),
            policy_enforced=False,
            restart_required=[],
        )

    monkeypatch.setattr(config_commands, "apply_config_operations", apply)
    monkeypatch.setattr(config_commands, "_config_set_notes", lambda *_a: ["restart"])
    assert (
        config_commands.cmd_config_provider_set(
            _args(
                type="cli",
                transport="codex",
                model="gpt-cheap",
                reasoning_effort="low",
                base_url="",
                api_key_env="",
                timeout=7,
            )
        )
        == 0
    )
    assert operations[-1][0][0]["value"][0]["model"] == "gpt-cheap"
    assert operations[-1][0][0]["value"][0]["reasoning_effort"] == "low"
    assert "restart" in capsys.readouterr().out

    current.persisted["providers"] = operations[-1][0][0]["value"]
    monkeypatch.setattr(config_commands, "_config_set_notes", lambda *_a: [])
    assert config_commands.cmd_config_provider_set(_args(model="gpt-updated", timeout=None)) == 0
    assert operations[-1][0][0]["value"][0]["timeout"] == 7.0
    assert operations[-1][0][0]["value"][0]["reasoning_effort"] == "low"
    primary_providers = operations[-1][0][0]["value"]

    current.persisted["providers"] = [
        {
            "name": "legacy-ollama",
            "type": "http",
            "model": "old-model",
            "base_url": "http://localhost:11434",
            "api_key_env": "",
            "ollama_mode": True,
            "timeout": 15,
        }
    ]
    assert (
        config_commands.cmd_config_provider_set(
            _args(name="legacy-ollama", model="new-model", transport=None)
        )
        == 0
    )
    assert operations[-1][0][0]["value"][0]["ollama_mode"] is True

    current.persisted["providers"] = operations[-1][0][0]["value"]
    assert (
        config_commands.cmd_config_provider_set(
            _args(name="legacy-ollama", type="cli", transport="codex", base_url="")
        )
        == 0
    )
    assert operations[-1][0][0]["value"][0]["ollama_mode"] is False
    assert operations[-1][0][0]["value"][0]["base_url"] == ""
    assert operations[-1][0][0]["value"][0]["api_key_env"] == ""
    assert operations[-1][0][1] == {
        "op": "secret",
        "path": "providers.0.api_key",
        "action": "clear",
    }

    current.persisted["providers"] = [
        {
            "name": "remote",
            "type": "litellm",
            "model": "task-router",
            "base_url": "https://router.invalid/v1",
            "api_key_env": "LITELLM_API_KEY",
        }
    ]
    assert (
        config_commands.cmd_config_provider_set(_args(name="remote", type="cli", transport="codex"))
        == 0
    )
    converted = operations[-1][0][0]["value"][0]
    assert converted["base_url"] == ""
    assert converted["api_key_env"] == ""
    assert operations[-1][0][1]["action"] == "clear"

    current.persisted["providers"] = [
        {
            "name": "subscription",
            "type": "cli",
            "transport": "codex",
            "model": "gpt-cheap",
            "base_url": "",
            "api_key_env": "",
        }
    ]
    assert (
        config_commands.cmd_config_provider_set(
            _args(
                name="subscription",
                type="openai-compatible",
                transport=None,
                base_url="https://api.example.test/v1",
                api_key_env="AGENCY_API_KEY",
            )
        )
        == 0
    )
    converted = operations[-1][0][0]["value"][0]
    assert converted["transport"] == ""
    assert converted["base_url"] == "https://api.example.test/v1"
    assert converted["api_key_env"] == "AGENCY_API_KEY"
    assert converted["reasoning_effort"] == ""

    current.persisted["providers"] = primary_providers
    assert (
        config_commands.cmd_config_provider_set(_args(name="primary", reasoning_effort="default"))
        == 0
    )
    assert operations[-1][0][0]["value"][0]["reasoning_effort"] == ""

    current.persisted["providers"] = [{"name": "claude", "type": "cli", "transport": "claude"}]
    with pytest.raises(ValueError, match="only for Codex"):
        config_commands.cmd_config_provider_set(
            _args(name="claude", transport=None, reasoning_effort="low")
        )

    current.persisted["providers"] = primary_providers
    with pytest.raises(ValueError, match="provider not found"):
        config_commands.cmd_config_provider_remove(_args(name="missing"))
    assert config_commands.cmd_config_provider_remove(_args(name="PRIMARY")) == 0
    assert operations[-1][0][0]["value"] == []
    assert "Removed provider" in capsys.readouterr().out

    calls = []
    monkeypatch.setattr(
        main._config, "cmd_config_provider_list", lambda args: calls.append(args) or 1
    )
    monkeypatch.setattr(
        main._config, "cmd_config_provider_models", lambda args: calls.append(args) or 2
    )
    monkeypatch.setattr(
        main._config, "cmd_config_provider_set", lambda args: calls.append(args) or 3
    )
    monkeypatch.setattr(
        main._config, "cmd_config_provider_remove", lambda args: calls.append(args) or 4
    )
    marker = object()
    assert main.cmd_config_provider_list(marker) == 1
    assert main.cmd_config_provider_models(marker) == 2
    assert main.cmd_config_provider_set(marker) == 3
    assert main.cmd_config_provider_remove(marker) == 4
    assert calls == [marker] * 4


def test_wizard_cli_model_picker_covers_discovery_choices(monkeypatch, capsys) -> None:
    answers = iter(("manual-one", "manual-two", "custom-model"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    dependencies = config_wizard.WizardDependencies(
        cli_model_discoverer=lambda _transport: CLIModelCatalog(
            "codex", (), "unavailable", "now", error="offline"
        )
    )
    assert config_wizard._pick_cli_model("codex", dependencies) == "manual-one"
    assert "offline" in capsys.readouterr().out
    dependencies = config_wizard.WizardDependencies(
        cli_model_discoverer=lambda _transport: CLIModelCatalog("codex", (), "unavailable", "now")
    )
    assert config_wizard._pick_cli_model("codex", dependencies) == "manual-two"

    models = (
        CLIModelInfo("cheap", "Cheap", "Low cost", 1, "low"),
        CLIModelInfo("plain", "Plain", "", 2, "medium"),
    )
    dependencies = config_wizard.WizardDependencies(
        cli_model_discoverer=lambda _transport: CLIModelCatalog("codex", models, "codex-cli", "now")
    )
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda _maximum, default: 2)
    assert config_wizard._pick_cli_model("codex", dependencies) == "cheap"
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda _maximum, default: 4)
    assert config_wizard._pick_cli_model("codex", dependencies) == "custom-model"
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda _maximum, default: 1)
    assert config_wizard._pick_cli_model("codex", dependencies) == ""
