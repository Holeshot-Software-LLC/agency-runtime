"""Tests for the centralized config system."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    config_to_yaml,
    load_config,
    reset_config_cache,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear agency env vars before each test."""
    for key in list(os.environ):
        if key.startswith("AGENCY_") or key in {
            "LITELLM_API_KEY",
            "TEST_ADAPTER_KEY",
            "TEST_PROVIDER_KEY",
        }:
            monkeypatch.delenv(key, raising=False)
    reset_config_cache()
    yield
    reset_config_cache()


def test_load_defaults_when_no_config():
    """Loading with no config file returns bundled defaults."""
    cfg = load_config(path="/nonexistent/path.yaml", reload=True)
    assert cfg.judge.model  # not empty — has a default
    assert "11434" in cfg.judge.base_url  # Ollama default
    assert cfg.judge.ollama_mode is True
    assert cfg.profile == "standard"


def test_config_loader_rejects_oversized_and_non_utf8_files(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.yaml"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="1 MiB"):
        load_config(oversized, reload=True)

    non_utf8 = tmp_path / "non-utf8.yaml"
    non_utf8.write_bytes(b"profile: \xff\n")
    with pytest.raises(ValueError, match="UTF-8"):
        load_config(non_utf8, reload=True)


def test_load_from_yaml_file(tmp_path: Path) -> None:
    """Config file values override defaults."""
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "judge": {
                    "model": "gpt-4o-mini",
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                    "ollama_mode": False,
                },
                "profile": "local-only",
            }
        ),
        encoding="utf-8",
    )

    cfg = load_config(path=path, reload=True)
    assert cfg.judge.model == "qwen3.5:2b"
    assert cfg.judge.base_url == "http://127.0.0.1:11434"
    assert cfg.judge.api_key_env == ""
    assert cfg.judge.ollama_mode is True
    assert cfg.profile == "local-only"


def test_env_overrides_file(tmp_path: Path) -> None:
    """Environment variables override file values."""
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump({"judge": {"model": "file-model"}}),
        encoding="utf-8",
    )

    os.environ["AGENCY_JUDGE_MODEL"] = "env-model"
    cfg = load_config(path=path, reload=True)
    assert cfg.judge.model == "env-model"


def test_env_overrides_timeout():
    """AGENCY_JUDGE_TIMEOUT overrides config."""
    os.environ["AGENCY_JUDGE_TIMEOUT"] = "30"
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.judge.timeout == 30.0


def test_env_db_path_override():
    """AGENCY_DB_PATH overrides config."""
    os.environ["AGENCY_DB_PATH"] = "/tmp/test-agency.db"
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.store.db_path == "/tmp/test-agency.db"
    assert cfg.store.resolved_path() == Path("/tmp/test-agency.db")


def test_env_auto_disables_ollama_mode():
    """Setting a non-Ollama judge base_url disables ollama_mode."""
    os.environ["AGENCY_JUDGE_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["AGENCY_JUDGE_MODEL"] = "gpt-4o-mini"
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.judge.ollama_mode is False


def test_litellm_api_key_fallback():
    """LITELLM_API_KEY is used when no direct key is set."""
    os.environ["LITELLM_API_KEY"] = "sk-test-123"
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.judge.resolve_api_key() == "sk-test-123"


def test_config_to_yaml_redacts_secrets():
    """config_to_yaml redacts api_key by default."""
    cfg = AgencyConfig(
        judge=JudgeConfig(model="test", api_key="super-secret"),
    )
    yaml_str = config_to_yaml(cfg, redact=True)
    assert "super-secret" not in yaml_str
    assert "***REDACTED***" in yaml_str

    yaml_str = config_to_yaml(cfg, redact=False)
    assert "super-secret" in yaml_str


def test_resolve_api_key_priority():
    """Direct api_key takes precedence over env var."""
    jc = JudgeConfig(api_key="direct-key", api_key_env="SOME_ENV")
    assert jc.resolve_api_key() == "direct-key"


def test_no_private_operator_defaults():
    """Ensure no private operator-specific identifiers are in defaults."""
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.judge.model != "task-agency-router"
    assert "task-agency-router" not in cfg.adapters.litellm.skip_models


def test_profile_has_no_private_operator_name():
    """Private operator profiles must not exist in the public API."""
    from agency_runtime.core.policy.profiles import PROFILES

    assert "private-operator" not in PROFILES


def test_adapter_entry_stores_api_key_directly():
    """AdapterEntryConfig can store api_key directly (config-first pattern)."""
    from agency_runtime.core.config import AdapterEntryConfig

    adapter = AdapterEntryConfig(
        enabled="true",
        base_url="http://localhost:4000",
        api_key="sk-direct-key",
    )
    assert adapter.resolve_api_key() == "sk-direct-key"


def test_adapter_entry_resolve_env_fallback():
    """AdapterEntryConfig falls back to env var when no direct key."""
    from agency_runtime.core.config import AdapterEntryConfig

    os.environ["TEST_ADAPTER_KEY"] = "sk-from-env"
    adapter = AdapterEntryConfig(api_key_env="TEST_ADAPTER_KEY")
    assert adapter.resolve_api_key() == "sk-from-env"
    del os.environ["TEST_ADAPTER_KEY"]


def test_normalize_enabled_boolean():
    """_normalize_enabled handles YAML booleans correctly."""
    from agency_runtime.core.config import _normalize_enabled

    assert _normalize_enabled(True) == "true"
    assert _normalize_enabled(False) == "false"
    assert _normalize_enabled("true") == "true"
    assert _normalize_enabled("True") == "true"
    assert _normalize_enabled("false") == "false"
    assert _normalize_enabled("auto") == "auto"
    assert _normalize_enabled("yes") == "true"
    assert _normalize_enabled("no") == "false"


def test_config_to_yaml_redacts_adapter_api_key():
    """config_to_yaml redacts adapter api_key values."""
    from agency_runtime.core.config import AdapterEntryConfig, AdaptersConfig

    cfg = AgencyConfig(
        adapters=AdaptersConfig(
            litellm=AdapterEntryConfig(
                enabled="true",
                base_url="http://localhost:4000",
                api_key="adapter-secret",
            ),
        ),
    )
    yaml_str = config_to_yaml(cfg, redact=True)
    assert "adapter-secret" not in yaml_str
    assert "***REDACTED***" in yaml_str


def test_store_expanduser_db_path():
    """Store constructor expands ~ in db_path."""
    import tempfile

    from agency_runtime.core.store.sqlite import Store

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = Store(db_path)
        assert "~" not in str(store.db_path)
        assert store.db_path.exists()


def test_wheel_includes_defaults_yaml():
    """Bundled config_defaults.yaml exists in installed package."""
    from agency_runtime.core.config import _BUNDLED_DEFAULTS

    assert _BUNDLED_DEFAULTS.exists(), f"Defaults file not found: {_BUNDLED_DEFAULTS}"


def test_provider_entry_basic():
    """ProviderEntry stores all fields and resolves API keys."""
    from agency_runtime.core.config import ProviderEntry

    p = ProviderEntry(
        name="openai",
        type="openai-compatible",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
    )
    assert p.resolve_api_key() == "sk-test"
    assert p.auth_method() == "api_key"
    assert p.is_available()


def test_provider_entry_env_key():
    """ProviderEntry resolves env var keys."""
    from agency_runtime.core.config import ProviderEntry

    os.environ["TEST_PROVIDER_KEY"] = "sk-env"
    p = ProviderEntry(
        name="openai",
        type="openai-compatible",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key_env="TEST_PROVIDER_KEY",
    )
    assert p.resolve_api_key() == "sk-env"
    assert p.auth_method() == "env_key"
    assert p.is_available()
    del os.environ["TEST_PROVIDER_KEY"]


def test_provider_entry_ollama_no_key():
    """Ollama providers don't need API keys."""
    from agency_runtime.core.config import ProviderEntry

    p = ProviderEntry(
        name="ollama",
        type="ollama",
        model="qwen3.5:2b",
        base_url="http://127.0.0.1:11434",
        ollama_mode=True,
    )
    assert p.resolve_api_key() == ""
    assert p.auth_method() == "none"
    assert p.is_available()  # model + base_url present


def test_provider_entry_unavailable():
    """Provider without model or key is not available."""
    from agency_runtime.core.config import ProviderEntry

    p = ProviderEntry(name="empty", type="openai-compatible")
    assert not p.is_available()


def test_config_parses_providers_list(tmp_path: Path) -> None:
    """Config YAML with providers list is parsed correctly."""
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "providers": [
                    {
                        "name": "litellm",
                        "type": "litellm",
                        "model": "task-general",
                        "base_url": "http://127.0.0.1:4000",
                        "api_key": "sk-test",
                    },
                    {
                        "name": "ollama",
                        "type": "ollama",
                        "model": "qwen3.5:2b",
                        "base_url": "http://localhost:11434",
                        "ollama_mode": True,
                    },
                ],
                "judge": {"model": "task-general", "base_url": "http://localhost:4000"},
            }
        ),
        encoding="utf-8",
    )

    cfg = load_config(path=path, reload=True)
    assert len(cfg.providers) == 2
    assert cfg.providers[0].name == "litellm"
    assert cfg.providers[0].type == "litellm"
    assert cfg.providers[1].name == "ollama"
    assert cfg.providers[1].ollama_mode is True


def test_load_rejects_credentialed_typed_provider_over_remote_http(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "providers": [
                    {
                        "name": "remote",
                        "type": "openai-compatible",
                        "model": "model",
                        "base_url": "http://provider.invalid/v1",
                        "api_key": "secret",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="literal loopback HTTP"):
        load_config(path, reload=True)


def test_load_rejects_credentialed_legacy_judge_over_remote_http(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "judge": {
                    "model": "model",
                    "base_url": "http://judge.invalid/v1",
                    "api_key": "secret",
                    "ollama_mode": False,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="judge credentials"):
        load_config(path, reload=True)


def test_environment_cannot_override_judge_credentials_to_remote_http() -> None:
    os.environ["AGENCY_JUDGE_BASE_URL"] = "http://judge.invalid/v1"
    os.environ["AGENCY_JUDGE_API_KEY"] = "secret"

    with pytest.raises(ValueError, match="judge credentials"):
        load_config("/nonexistent", reload=True)


def test_load_rejects_credentialed_litellm_adapter_over_remote_http(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "adapters": {
                    "litellm": {
                        "enabled": "true",
                        "base_url": "http://adapter.invalid",
                        "api_key_env": "LITELLM_API_KEY",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="LiteLLM adapter credentials"):
        load_config(path, reload=True)


def test_load_accepts_credentialed_literal_loopback_http(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "judge": {
                    "model": "model",
                    "base_url": "http://127.0.0.1:4000/v1",
                    "api_key": "secret",
                    "ollama_mode": False,
                },
            }
        ),
        encoding="utf-8",
    )

    assert load_config(path, reload=True).judge.api_key == "secret"


def test_runtime_rejects_query_bearing_credential_base_url(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "judge": {
                    "model": "model",
                    "base_url": "https://judge.invalid/v1?token=leaky",
                    "api_key": "secret",
                    "ollama_mode": False,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="judge credentials"):
        load_config(path, reload=True)


def test_config_to_yaml_includes_providers():
    """config_to_yaml serializes providers list with redaction."""
    from agency_runtime.core.config import AgencyConfig, ProviderEntry

    cfg = AgencyConfig(
        providers=(
            ProviderEntry(name="openai", model="gpt-4o", api_key="secret"),
            ProviderEntry(name="ollama", type="ollama", model="qwen3.5:2b"),
        ),
    )
    yaml_str = config_to_yaml(cfg, redact=True)
    assert "secret" not in yaml_str
    assert "***REDACTED***" in yaml_str
    assert "openai" in yaml_str
    assert "ollama" in yaml_str


def test_observability_defaults_are_privacy_preserving():
    cfg = AgencyConfig()

    assert cfg.observability.capture_content is False
    assert cfg.observability.retention_days == 30
    serialized = yaml.safe_load(config_to_yaml(cfg))
    assert serialized["observability"] == {
        "capture_content": False,
        "retention_days": 30,
    }


def test_observability_config_parses_string_false_and_retention(tmp_path):
    path = tmp_path / "agency.yaml"
    path.write_text(
        "observability:\n  capture_content: 'false'\n  retention_days: 45\n",
        encoding="utf-8",
    )

    cfg = load_config(path=path, reload=True)

    assert cfg.observability.capture_content is False
    assert cfg.observability.retention_days == 45
