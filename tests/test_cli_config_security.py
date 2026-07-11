from __future__ import annotations

import builtins
import io
import os
import stat
import sys
from pathlib import Path

import pytest
import yaml

from agency_runtime.cli import main as cli
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.detect import (
    AdapterDetection,
    DetectionResult,
    ProviderDetection,
)


@pytest.fixture(autouse=True)
def _fresh_config_cache() -> None:
    reset_config_cache()
    yield
    reset_config_cache()


def test_atomic_yaml_write_is_restrictive_and_valid(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"

    cli._atomic_write_yaml(path, {"judge": {"model": "qwen:local"}})

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "judge": {"model": "qwen:local"}
    }
    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_atomic_yaml_write_preserves_original_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(cli.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        cli._atomic_write_yaml(path, {"profile": "local-only"})

    assert path.read_text(encoding="utf-8") == "profile: standard\n"
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_config_get_and_set_redact_secrets_unless_raw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    cli._atomic_write_yaml(
        path,
        {
            "profile": "standard",
            "judge": {"model": "test", "api_key": "initial-secret"},
            "providers": [
                {
                    "name": "custom",
                    "type": "openai-compatible",
                    "model": "test",
                    "base_url": "https://example.invalid/v1",
                    "api_key": "provider-secret",
                }
            ],
        },
    )

    assert cli.main(["config", "get", "judge.api_key"]) == 0
    assert capsys.readouterr().out.strip() == cli._REDACTED

    assert cli.main(["config", "get", "judge.api_key", "--raw"]) == 0
    assert capsys.readouterr().out.strip() == "initial-secret"

    assert cli.main(["config", "get", "providers"]) == 0
    provider_output = capsys.readouterr().out
    assert "provider-secret" not in provider_output
    assert cli._REDACTED in provider_output

    assert cli.main(["config", "set", "judge.api_key", "replacement-secret"]) == 0
    set_output = capsys.readouterr().out
    assert "replacement-secret" not in set_output
    assert cli._REDACTED in set_output
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["judge"]["api_key"] == (
        "replacement-secret"
    )

    assert cli.main(["config", "get", "judge.api_key", "--raw"]) == 0
    assert capsys.readouterr().out.strip() == "replacement-secret"


def test_local_only_enforcement_removes_remote_providers_and_auto_adapters() -> None:
    data = {
        "profile": "local-only",
        "judge": {
            "model": "remote-model",
            "base_url": "https://api.example.invalid/v1",
            "api_key": "must-be-removed",
            "ollama_mode": False,
        },
        "ollama": {
            "enabled": False,
            "base_url": "https://remote-ollama.invalid",
            "model": "local-model",
        },
        "providers": [
            {
                "name": "remote",
                "type": "openai-compatible",
                "base_url": "https://api.example.invalid/v1",
                "api_key": "must-be-removed",
            }
        ],
        "adapters": {
            "litellm": {"enabled": "true"},
            "codex": {"enabled": "auto"},
        },
    }

    result = cli._enforce_local_only_config(data)

    assert result["judge"] == {
        "model": "local-model",
        "base_url": "http://127.0.0.1:11434",
        "api_key": "",
        "api_key_env": "",
        "ollama_mode": True,
    }
    assert len(result["providers"]) == 1
    assert result["providers"][0]["type"] == "ollama"
    assert cli._is_loopback_url(result["providers"][0]["base_url"])
    assert all(
        entry["enabled"] == "false"
        for entry in result["adapters"].values()
    )


def test_config_set_cannot_reenable_remote_behavior_in_local_only_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    cli._atomic_write_yaml(
        path,
        {
            "profile": "standard",
            "judge": {
                "model": "remote",
                "base_url": "https://api.example.invalid/v1",
                "api_key": "secret",
            },
            "adapters": {"codex": {"enabled": "true"}},
        },
    )

    assert cli.main(["config", "set", "profile", "local-only"]) == 0
    capsys.readouterr()
    assert cli.main(["config", "set", "adapters.codex.enabled", "true"]) == 0

    output = capsys.readouterr().out
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["profile"] == "local-only"
    assert written["adapters"]["codex"]["enabled"] == "false"
    assert written["providers"][0]["type"] == "ollama"
    assert written["judge"]["api_key"] == ""
    assert "local-only policy enforced" in output


def test_local_only_detection_hides_remote_keys_before_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, str | None] = {}
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    def fake_detect_all() -> DetectionResult:
        observed["openai"] = os.environ.get("OPENAI_API_KEY")
        observed["anthropic"] = os.environ.get("ANTHROPIC_API_KEY")
        return DetectionResult(
            providers=ProviderDetection(
                openai_key_present=True,
                openai_models=["remote-model"],
                anthropic_key_present=True,
            )
        )

    monkeypatch.setattr(cli, "detect_all", fake_detect_all)
    result = cli._detect_for_profile("local-only")

    assert observed == {"openai": None, "anthropic": None}
    assert os.environ["OPENAI_API_KEY"] == "openai-secret"
    assert os.environ["ANTHROPIC_API_KEY"] == "anthropic-secret"
    assert not result.providers.openai_key_present
    assert not result.providers.anthropic_key_present
    assert result.providers.openai_models == []


def test_explicit_local_only_configure_never_exposes_remote_keys_to_detection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    observed: dict[str, str | None] = {}
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")

    def fake_detect_all() -> DetectionResult:
        observed["openai"] = os.environ.get("OPENAI_API_KEY")
        observed["anthropic"] = os.environ.get("ANTHROPIC_API_KEY")
        return DetectionResult(
            providers=ProviderDetection(
                ollama_available=True,
                ollama_models=["local-model"],
                openai_key_present=True,
                openai_models=["remote-model"],
                anthropic_key_present=True,
            ),
            adapters=AdapterDetection(codex=True, claude=True),
        )

    monkeypatch.setattr(cli, "detect_all", fake_detect_all)
    monkeypatch.setattr(cli, "_store", lambda _config: object())
    monkeypatch.setattr(cli, "_seed_starter_roster", lambda _store: 0)

    assert cli.main(
        ["configure", "--non-interactive", "--profile", "local-only"]
    ) == 0
    capsys.readouterr()

    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert observed == {"openai": None, "anthropic": None}
    assert written["profile"] == "local-only"
    assert [provider["type"] for provider in written["providers"]] == ["ollama"]
    assert all(
        adapter["enabled"] == "false"
        for adapter in written["adapters"].values()
    )
    assert os.environ["OPENAI_API_KEY"] == "openai-secret"
    assert os.environ["ANTHROPIC_API_KEY"] == "anthropic-secret"


def test_local_only_wizard_only_writes_local_provider_and_disabled_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detection = DetectionResult(
        providers=ProviderDetection(
            ollama_available=True,
            ollama_models=["local-model"],
            openai_key_present=True,
            openai_models=["remote-model"],
            anthropic_key_present=True,
            litellm_available=True,
            litellm_models=["remote-group"],
        ),
        adapters=AdapterDetection(
            hermes=True,
            openclaw=True,
            codex=True,
            claude=True,
        ),
    )
    answers = iter(["", ""])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    result = cli._interactive_wizard(detection, "local-only")

    assert result["judge"]["base_url"].startswith("http://127.0.0.1")
    assert [provider["type"] for provider in result["providers"]] == ["ollama"]
    assert all(
        adapter["enabled"] == "false"
        for adapter in result["adapters"].values()
    )


def test_anthropic_wizard_emits_typed_provider_for_messages_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detection = DetectionResult(
        providers=ProviderDetection(anthropic_key_present=True),
    )
    answers = iter(["", "", ""])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    result = cli._interactive_wizard(detection, "standard")

    assert result["providers"][0]["name"] == "anthropic"
    assert result["providers"][0]["type"] == "anthropic"
    assert result["providers"][0]["api_key_env"] == "ANTHROPIC_API_KEY"
    assert result["providers"][0]["base_url"] == "https://api.anthropic.com/v1"

    path = tmp_path / "agency.yaml"
    cli._atomic_write_yaml(path, result)
    config = load_config(path, reload=True)
    assert config.providers[0].type == "anthropic"


def test_console_output_uses_safe_encoding_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)

    cli._configure_console_output()
    print("✅━")
    stream.flush()

    assert stream.errors == "backslashreplace"
    expected = b"\\u2705\\u2501\r\n" if os.name == "nt" else b"\\u2705\\u2501\n"
    assert raw.getvalue() == expected
