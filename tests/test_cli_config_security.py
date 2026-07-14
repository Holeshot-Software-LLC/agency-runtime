from __future__ import annotations

import builtins
import io
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

from agency_runtime.cli import main as cli
from agency_runtime.core.cli_transport import CLIProviderStatus
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.configuration import (
    read_config_state,
    replace_config_document,
)
from agency_runtime.core.detect import (
    AdapterDetection,
    DetectionResult,
    ProviderDetection,
)
from agency_runtime.core.provider_validation import ProviderValidationResult


@pytest.fixture(autouse=True)
def _fresh_config_cache() -> None:
    reset_config_cache()
    yield
    reset_config_cache()


def _write_config(path: Path, document: dict) -> None:
    replace_config_document(
        document,
        expected_revision=read_config_state(path).revision,
        path=path,
    )


def test_config_get_and_set_redact_secrets_unless_raw(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    _write_config(
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

    monkeypatch.setattr(sys, "stdin", io.StringIO("replacement-secret\n"))
    assert cli.main(["config", "set", "judge.api_key", "--stdin"]) == 0
    set_output = capsys.readouterr().out
    assert "replacement-secret" not in set_output
    assert cli._REDACTED in set_output
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["judge"]["api_key"] == (
        "replacement-secret"
    )

    assert cli.main(["config", "get", "judge.api_key", "--raw"]) == 0
    assert capsys.readouterr().out.strip() == "replacement-secret"


def test_config_set_rejects_ambiguous_positional_and_stdin_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    monkeypatch.setattr(sys, "stdin", io.StringIO("power\n"))

    assert cli.main(["config", "set", "profile", "standard", "--stdin"]) == 1

    assert "either a positional value or --stdin" in capsys.readouterr().err
    assert not path.exists()


@pytest.mark.parametrize(
    ("key", "payload"),
    [
        ("judge.api_key", "s" * 4097 + "\n"),
        ("profile", "s" * (1024 * 1024 + 1)),
    ],
    ids=("secret", "non-secret"),
)
def test_config_set_bounds_standard_input_before_parsing_or_writing(
    key: str,
    payload: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))

    assert cli.main(["config", "set", key, "--stdin"]) == 1

    assert "standard input exceeds the size limit" in capsys.readouterr().err
    assert not path.exists()


def test_config_set_reports_restart_required_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))

    assert cli.main(["config", "set", "dashboard.port", "7915"]) == 0

    output = capsys.readouterr().out
    assert "restart required: dashboard.port" in output
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["dashboard"]["port"] == 7915


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
    assert all(entry["enabled"] == "false" for entry in result["adapters"].values())


def test_config_set_cannot_reenable_remote_behavior_in_local_only_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    _write_config(
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

    assert cli.main(["configure", "--non-interactive", "--profile", "local-only"]) == 0
    capsys.readouterr()

    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert observed == {"openai": None, "anthropic": None}
    assert written["profile"] == "local-only"
    assert [provider["type"] for provider in written["providers"]] == ["ollama"]
    assert all(adapter["enabled"] == "false" for adapter in written["adapters"].values())
    assert os.environ["OPENAI_API_KEY"] == "openai-secret"
    assert os.environ["ANTHROPIC_API_KEY"] == "anthropic-secret"


def test_configure_force_recovers_invalid_existing_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("judge: [invalid\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    monkeypatch.setattr(cli, "_detect_for_profile", lambda _profile: DetectionResult())
    monkeypatch.setattr(cli, "_store", lambda _config: object())
    monkeypatch.setattr(cli, "_seed_starter_roster", lambda _store: 0)

    assert cli.main(["configure", "--non-interactive", "--profile", "standard", "--force"]) == 0

    output = capsys.readouterr().out
    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert "Config written" in output
    assert written["profile"] == "standard"
    assert isinstance(written["providers"], list)


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
    assert all(adapter["enabled"] == "false" for adapter in result["adapters"].values())


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
    _write_config(path, result)
    config = load_config(path, reload=True)
    assert config.providers[0].type == "anthropic"


def test_guided_provider_chain_reorders_suggested_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detection = DetectionResult(
        providers=ProviderDetection(
            ollama_available=True,
            ollama_models=["local-model"],
            openai_key_present=True,
            openai_models=["remote-model"],
        )
    )
    answers = iter(["2", "1", "2", "4"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    providers = cli._guided_provider_chain(detection, "standard")

    assert [provider["name"] for provider in providers] == ["ollama", "openai"]


def test_guided_provider_chain_explains_four_entry_limit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    detection = DetectionResult(
        providers=ProviderDetection(
            litellm_available=True,
            litellm_models=["proxy-model"],
            openai_key_present=True,
            openai_models=["openai-model"],
            anthropic_key_present=True,
            ollama_available=True,
            ollama_models=["local-model"],
        ),
        cli_providers={
            "codex": CLIProviderStatus("codex", True, True, True),
        },
    )
    answers = iter(["1", "4"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    providers = cli._guided_provider_chain(detection, "standard")

    assert len(providers) == 4
    assert "support at most 4 entries; remove one first" in capsys.readouterr().out


def test_cli_only_chain_disables_legacy_judge_fallback() -> None:
    legacy = cli._legacy_judge_from_chain(
        [{"name": "codex", "type": "cli", "transport": "codex"}],
        {
            "model": "removed",
            "base_url": "https://removed.invalid/v1",
            "api_key": "secret",
            "ollama_mode": False,
        },
    )

    assert legacy == {
        "model": "",
        "base_url": "",
        "api_key": "",
        "api_key_env": "",
        "ollama_mode": False,
    }


def test_wizard_applies_timeout_to_every_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detection = DetectionResult(
        providers=ProviderDetection(
            ollama_available=True,
            ollama_models=["local-model"],
            openai_key_present=True,
            openai_models=["remote-model"],
        )
    )
    answers = iter(["", "n", "7", "2", "15"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    result = cli._interactive_wizard(detection, "standard")

    assert len(result["providers"]) == 2
    assert {provider["timeout"] for provider in result["providers"]} == {7.0}


def test_local_only_chain_can_bootstrap_ollama_when_detection_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(["1", "1", "local-model", "4"])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))

    providers = cli._guided_provider_chain(DetectionResult(), "local-only")

    assert [provider["type"] for provider in providers] == ["ollama"]
    assert providers[0]["model"] == "local-model"
    assert cli._is_loopback_url(providers[0]["base_url"])


def test_custom_provider_authenticates_before_discovery_and_hides_direct_key(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: list[tuple[str, str | None]] = []
    answers = iter(["5", "https://provider.example/v1", "2", ""])
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(answers))
    monkeypatch.setattr(cli.getpass, "getpass", lambda _prompt="": "direct-secret")
    monkeypatch.setattr(
        cli,
        "_fetch_models_custom",
        lambda url, key=None: captured.append((url, key)) or ["model-a"],
    )

    provider = cli._pick_custom_endpoint()

    assert captured == [("https://provider.example/v1", "direct-secret")]
    assert provider["api_key"] == "direct-secret"
    assert provider["model"] == "model-a"
    assert "direct-secret" not in capsys.readouterr().out


def test_custom_model_discovery_rejects_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_sizes: list[int] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            read_sizes.append(size)
            return b"x" * (cli._MAX_MODEL_DISCOVERY_BYTES + 1)

    monkeypatch.setattr(cli, "open_no_redirect", lambda *_a, **_kw: Response())

    assert cli._fetch_models_custom("http://127.0.0.1:1234/v1") == []
    assert read_sizes == [cli._MAX_MODEL_DISCOVERY_BYTES + 1]


@pytest.mark.parametrize(
    "base_url",
    [
        "http://provider.invalid/v1",
        "https://provider.invalid/v1?token=leaky",
    ],
)
def test_custom_model_discovery_never_sends_credentials_to_unsafe_base(
    base_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("credentialed discovery attempted")

    monkeypatch.setattr(cli, "open_no_redirect", unexpected_call)

    assert cli._fetch_models_custom(base_url, "secret") == []


def test_remote_model_ids_are_count_length_and_terminal_safe(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payload = json.dumps(
        {
            "data": [
                {"id": "\x1b[31mhostile"},
                {"id": "x" * (cli._MAX_MODEL_ID_CHARS + 1)},
                *({"id": f"safe-{index:04d}"} for index in range(1200)),
            ],
        }
    ).encode()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int = -1) -> bytes:
            return payload

    monkeypatch.setattr(cli, "open_no_redirect", lambda *_a, **_kw: Response())
    models = cli._fetch_models_custom("http://127.0.0.1:1234/v1")

    assert len(models) == cli._MAX_DISCOVERED_MODELS
    assert all("\x1b" not in model for model in models)
    assert all(len(model) <= cli._MAX_MODEL_ID_CHARS for model in models)
    assert "\x1b" not in capsys.readouterr().out


def test_interactive_chain_validation_reports_ordered_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seen: list[str] = []

    def validate(provider, **_kwargs):
        seen.append(provider.name)
        usable = provider.name == "first"
        return ProviderValidationResult(
            provider.name,
            provider.type,
            usable,
            usable,
            "authentication unavailable" if not usable else "",
        )

    monkeypatch.setattr(cli, "validate_provider", validate)
    providers = [
        {
            "name": "first",
            "type": "cli",
            "transport": "codex",
            "model": "",
            "base_url": "",
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": False,
        },
        {
            "name": "second",
            "type": "cli",
            "transport": "claude",
            "model": "",
            "base_url": "",
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": False,
        },
    ]

    assert cli._validate_interactive_provider_chain(providers) is False

    output = capsys.readouterr().out
    assert seen == ["first", "second"]
    assert "providers.0 (first): usable" in output
    assert "providers.1 (second): authentication unavailable" in output


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
