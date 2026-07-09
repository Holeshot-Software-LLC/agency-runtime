"""Tests for the centralized config system."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    load_config,
    reset_config_cache,
    config_to_yaml,
)


@pytest.fixture(autouse=True)
def _clean_env():
    """Clear agency env vars before each test."""
    for key in list(os.environ):
        if key.startswith("AGENCY_") or key == "LITELLM_API_KEY":
            os.environ.pop(key, None)
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


def test_load_from_yaml_file():
    """Config file values override defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({
            "judge": {
                "model": "gpt-4o-mini",
                "base_url": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
                "ollama_mode": False,
            },
            "profile": "local-only",
        }, f)
        f.flush()

    cfg = load_config(path=f.name, reload=True)
    assert cfg.judge.model == "gpt-4o-mini"
    assert cfg.judge.ollama_mode is False
    assert cfg.profile == "local-only"
    Path(f.name).unlink()


def test_env_overrides_file():
    """Environment variables override file values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"judge": {"model": "file-model"}}, f)
        f.flush()

    os.environ["AGENCY_JUDGE_MODEL"] = "env-model"
    cfg = load_config(path=f.name, reload=True)
    assert cfg.judge.model == "env-model"
    Path(f.name).unlink()


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
    assert str(cfg.store.resolved_path()) == "/tmp/test-agency.db"


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


def test_no_user_specific_defaults():
    """Ensure no Lucas-specific identifiers are in the defaults."""
    cfg = load_config(path="/nonexistent", reload=True)
    assert cfg.judge.model != "task-agency-router"
    assert "task-agency-router" not in cfg.adapters.litellm.skip_models


def test_profile_has_no_lucas():
    """LUCAS profile must not exist in the public API."""
    from agency_runtime.core.policy.profiles import PROFILES
    assert "lucas" not in PROFILES
