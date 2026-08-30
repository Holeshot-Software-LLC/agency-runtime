"""Tests for the centralized config system."""

from __future__ import annotations

import errno
import os
from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from agency_runtime.core import config as config_module
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    config_to_yaml,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.configuration_contracts import (
    ConfigurationError,
    ConfigValidationError,
)
from tests.runtime_support import is_agency_product_environment_key

pytestmark = pytest.mark.runtime_configuration_identity


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear agency env vars before each test."""
    original_environment = dict(os.environ)
    for key in list(os.environ):
        if is_agency_product_environment_key(key) or key in {
            "LITELLM_API_KEY",
            "TEST_ADAPTER_KEY",
            "TEST_PROVIDER_KEY",
        }:
            monkeypatch.delenv(key, raising=False)
    reset_config_cache()
    try:
        yield
    finally:
        reset_config_cache()
        os.environ.clear()
        os.environ.update(original_environment)


def test_load_defaults_when_no_config(tmp_path: Path):
    """Loading with no config file returns bundled defaults."""
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
    assert cfg.judge.model  # not empty — has a default
    assert "11434" in cfg.judge.base_url  # Ollama default
    assert cfg.judge.ollama_mode is True
    assert cfg.profile == "standard"


@pytest.mark.parametrize("content", ["[]\n", "true\n", "configuration\n"])
def test_present_non_mapping_config_root_fails_closed(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="configuration root must be a mapping"):
        load_config(path, reload=True)


@pytest.mark.parametrize("content", ["null\n", "~\n", "---\n", "# comment only\n"])
def test_present_nonempty_null_config_document_fails_closed(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigValidationError, match="configuration root must be a mapping"):
        load_config(path, reload=True)


@pytest.mark.parametrize("content", ["", " \n\t\r\n"])
def test_present_whitespace_only_config_document_uses_defaults(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(content, encoding="utf-8")

    cfg = load_config(path, reload=True)

    assert cfg.profile == "standard"
    assert cfg.config_path == str(path.resolve())


def test_cached_config_never_commits_a_repeatedly_changing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    original_load = config_module._load_config_uncached
    calls = 0

    def mutating_load(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        nonlocal calls
        loaded = original_load(config_path, environ=environ)
        calls += 1
        next_profile = "power" if calls % 2 else "standard"
        replacement = config_path.with_name(f".{config_path.name}.{calls}.tmp")
        replacement.write_text(f"profile: {next_profile}\n", encoding="utf-8")
        os.replace(replacement, config_path)
        return loaded

    monkeypatch.setattr(config_module, "_load_config_uncached", mutating_load)

    with pytest.raises(ValueError, match="inputs changed repeatedly during load"):
        load_config(reload=True)

    assert calls == config_module._CONFIG_LOAD_STABILITY_ATTEMPTS


@pytest.mark.parametrize(
    "content",
    [
        "providers: {}\n",
        "providers:\n  - invalid-entry\n",
        "observability: false\n",
        "unsupported: true\n",
    ],
)
def test_malformed_persisted_config_sections_fail_closed(
    tmp_path: Path,
    content: str,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(path, reload=True)


def test_config_loader_rejects_oversized_and_non_utf8_files(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.yaml"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="1 MiB"):
        load_config(oversized, reload=True)

    non_utf8 = tmp_path / "non-utf8.yaml"
    non_utf8.write_bytes(b"profile: \xff\n")
    with pytest.raises(ValueError, match="UTF-8"):
        load_config(non_utf8, reload=True)


def test_config_signature_reports_platform_filesystem_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "denied.yaml"
    original_lstat = Path.lstat

    def denied_lstat(path: Path, *args, **kwargs):
        if path == target:
            raise PermissionError(errno.EACCES, "denied", str(path))
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", denied_lstat)
    signature = config_module._config_file_signature(target)
    assert signature[:2] == (str(target.resolve()), "unavailable")
    assert signature[2:] == ("PermissionError", errno.EACCES)


def test_default_config_cache_reloads_atomic_changes_until_snapshot_is_stable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("agents:\n  disabled: []\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    original_loader = config_module._load_config_uncached
    calls = 0

    def changing_loader(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        nonlocal calls
        calls += 1
        loaded = original_loader(config_path, environ=environ)
        replacements = (
            "agents:\n  disabled: [code-reviewer]\n",
            "agents:\n  disabled: [code-reviewer, security-architect]\n",
        )
        if calls <= len(replacements):
            replacement = config_path.with_name(f".{config_path.name}.{calls}.tmp")
            replacement.write_text(replacements[calls - 1], encoding="utf-8")
            os.replace(replacement, config_path)
        return loaded

    monkeypatch.setattr(config_module, "_load_config_uncached", changing_loader)
    assert load_config().agents.disabled == ("code-reviewer", "security-architect")
    assert calls == 3


def test_default_config_cache_invalidates_environment_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    assert load_config().profile == "standard"
    monkeypatch.setenv("AGENCY_PROFILE", "local-only")
    assert load_config().profile == "local-only"


def test_config_load_retries_environment_change_during_materialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_PROFILE", "standard")
    original_loader = config_module._load_config_uncached
    calls = 0

    def changing_loader(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        nonlocal calls
        calls += 1
        loaded = original_loader(config_path, environ=environ)
        if calls == 1:
            monkeypatch.setenv("AGENCY_PROFILE", "local-only")
        return loaded

    monkeypatch.setattr(config_module, "_load_config_uncached", changing_loader)

    loaded = load_config(path, reload=True)

    assert calls == 2
    assert loaded.profile == "local-only"
    assert load_config(path) is loaded


def test_config_load_rejects_repeated_environment_churn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_PROFILE", "standard")
    original_loader = config_module._load_config_uncached
    calls = 0

    def changing_loader(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        nonlocal calls
        calls += 1
        loaded = original_loader(config_path, environ=environ)
        next_profile = "local-only" if calls % 2 else "standard"
        monkeypatch.setenv("AGENCY_PROFILE", next_profile)
        return loaded

    monkeypatch.setattr(config_module, "_load_config_uncached", changing_loader)

    with pytest.raises(ValueError, match="inputs changed repeatedly during load"):
        load_config(path, reload=True)

    assert calls == config_module._CONFIG_LOAD_STABILITY_ATTEMPTS


def test_config_materialization_uses_snapshot_during_dynamic_key_aba(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        "judge:\n"
        "  model: reviewed-router\n"
        "  base_url: https://router.example/v1\n"
        "  api_key_env: TEST_JUDGE_KEY\n"
        "  ollama_mode: false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LITELLM_API_KEY", "snapshot-fallback")
    monkeypatch.delenv("TEST_JUDGE_KEY", raising=False)
    original_loader = config_module._load_config_uncached

    def aba_loader(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        monkeypatch.setenv("TEST_JUDGE_KEY", "transient-key")
        try:
            return original_loader(config_path, environ=environ)
        finally:
            monkeypatch.delenv("TEST_JUDGE_KEY", raising=False)

    monkeypatch.setattr(config_module, "_load_config_uncached", aba_loader)

    loaded = load_config(path, reload=True)

    assert loaded.judge.api_key == "snapshot-fallback"
    assert loaded.judge.resolve_api_key() == "snapshot-fallback"


def test_default_config_path_change_is_linearized_per_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text("profile: standard\n", encoding="utf-8")
    second_path.write_text("profile: power\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(first_path))
    original_loader = config_module._load_config_uncached
    loaded_paths: list[Path] = []

    def changing_path_loader(
        config_path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        loaded_paths.append(config_path)
        loaded = original_loader(config_path, environ=environ)
        if len(loaded_paths) == 1:
            monkeypatch.setenv("AGENCY_CONFIG_PATH", str(second_path))
        return loaded

    monkeypatch.setattr(config_module, "_load_config_uncached", changing_path_loader)

    first = load_config(reload=True)
    second = load_config()

    assert first.profile == "standard"
    assert first.config_path == str(first_path.resolve())
    assert second.profile == "power"
    assert second.config_path == str(second_path.resolve())
    assert loaded_paths == [first_path.resolve(), second_path.resolve()]


def test_explicit_config_cache_is_identity_scoped_and_reloadable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_path = tmp_path / "first.yaml"
    second_path = tmp_path / "second.yaml"
    first_path.write_text("profile: standard\n", encoding="utf-8")
    second_path.write_text("profile: power\n", encoding="utf-8")
    original_loader = config_module._load_config_uncached
    loaded_paths: list[Path] = []

    def tracked_loader(
        path: Path,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> AgencyConfig:
        loaded_paths.append(path)
        return original_loader(path, environ=environ)

    monkeypatch.setattr(config_module, "_load_config_uncached", tracked_loader)

    first = load_config(first_path)
    assert load_config(first_path) is first
    second = load_config(second_path)
    assert load_config(second_path) is second
    assert first.profile == "standard"
    assert second.profile == "power"
    assert loaded_paths == [first_path.resolve(), second_path.resolve()]

    refreshed = load_config(first_path, reload=True)
    assert refreshed is not first
    assert refreshed.profile == "standard"
    assert loaded_paths == [first_path.resolve(), second_path.resolve(), first_path.resolve()]

    first_path.write_text("profile: local-only\n", encoding="utf-8")
    externally_changed = load_config(first_path)
    assert externally_changed.profile == "local-only"
    assert load_config(second_path) is second
    assert loaded_paths == [
        first_path.resolve(),
        second_path.resolve(),
        first_path.resolve(),
        first_path.resolve(),
    ]


def test_explicit_config_cache_is_thread_safe_and_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = [tmp_path / f"config-{index}.yaml" for index in range(3)]
    profiles = ["standard", "power", "local-only"]
    for path, profile in zip(paths, profiles, strict=True):
        path.write_text(f"profile: {profile}\n", encoding="utf-8")
    monkeypatch.setattr(config_module, "_CONFIG_CACHE_LIMIT", 2)

    with ThreadPoolExecutor(max_workers=6) as executor:
        observed = list(
            executor.map(
                lambda index: load_config(paths[index % len(paths)]).profile,
                range(30),
            )
        )

    assert observed == [profiles[index % len(paths)] for index in range(30)]
    assert len(config_module._config_cache) == 2


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AGENCY_JUDGE_TIMEOUT", "nan"),
        ("AGENCY_JUDGE_TIMEOUT", "0.01"),
        ("AGENCY_MAX_SELECTED", "0"),
        ("AGENCY_BYPASS_THRESHOLD", "101"),
        ("AGENCY_RETENTION_DAYS", "0"),
        ("AGENCY_DASHBOARD_PORT", "0"),
        ("AGENCY_DASHBOARD_PORT", "65536"),
    ],
)
def test_invalid_numeric_runtime_environment_overrides_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=rf"{name}: environment override is invalid"):
        load_config(tmp_path / "agency.yaml", reload=True)


def test_enormous_numeric_environment_override_is_safely_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submitted = "9" * 10_000
    monkeypatch.setenv("AGENCY_DASHBOARD_PORT", submitted)

    with pytest.raises(
        ConfigurationError,
        match="AGENCY_DASHBOARD_PORT: environment override is invalid",
    ) as captured:
        load_config(tmp_path / "agency.yaml", reload=True)

    assert submitted not in str(captured.value)


def test_misspelled_local_only_profile_cannot_fail_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_PROFILE", "locla-only")

    with pytest.raises(
        ConfigurationError,
        match="AGENCY_PROFILE: environment override is invalid",
    ):
        load_config(tmp_path / "agency.yaml", reload=True)


def test_invalid_content_capture_environment_override_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CAPTURE_CONTENT", "sometimes")

    with pytest.raises(
        ConfigurationError,
        match="AGENCY_CAPTURE_CONTENT: environment override is invalid",
    ):
        load_config(tmp_path / "agency.yaml", reload=True)


def test_default_config_cache_tracks_configured_judge_key_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(
        "judge:\n  api_key_env: CUSTOM_JUDGE_KEY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(path))
    monkeypatch.setenv("LITELLM_API_KEY", "fallback-key")

    initial = load_config()
    assert initial.judge.api_key == "fallback-key"
    assert initial.judge.api_key_env == "CUSTOM_JUDGE_KEY"

    monkeypatch.setenv("CUSTOM_JUDGE_KEY", "configured-key")
    refreshed = load_config()
    assert refreshed is not initial
    assert refreshed.judge.api_key == ""
    assert refreshed.judge.resolve_api_key() == "configured-key"


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


def test_env_overrides_timeout(tmp_path: Path):
    """AGENCY_JUDGE_TIMEOUT overrides config."""
    os.environ["AGENCY_JUDGE_TIMEOUT"] = "30"
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
    assert cfg.judge.timeout == 30.0


def test_env_db_path_override(tmp_path: Path):
    """AGENCY_DB_PATH overrides config."""
    configured = tmp_path / "test-agency.db"
    os.environ["AGENCY_DB_PATH"] = str(configured)
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
    expected = configured.resolve()
    assert cfg.store.db_path == str(expected)
    assert cfg.store.resolved_path() == expected


def test_relative_runtime_paths_bind_to_config_parent_across_working_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "configuration"
    config_dir.mkdir()
    config_path = config_dir / "agency.yaml"
    config_path.write_text(
        "store:\n  db_path: state/agency.db\ncompanion_policy_path: policy/companions.yaml\n",
        encoding="utf-8",
    )
    other_cwd = tmp_path / "unrelated-working-directory"
    other_cwd.mkdir()

    monkeypatch.chdir(tmp_path)
    cfg = load_config(Path("configuration") / "agency.yaml", reload=True)
    expected_db = (config_dir / "state" / "agency.db").resolve()
    expected_policy = (config_dir / "policy" / "companions.yaml").resolve()

    monkeypatch.chdir(other_cwd)
    assert cfg.store.db_path == str(expected_db)
    assert cfg.store.resolved_path() == expected_db
    assert cfg.companion_policy_path == str(expected_policy)


def test_relative_environment_db_path_uses_canonical_config_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "configuration"
    config_dir.mkdir()
    config_path = config_dir / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    monkeypatch.setenv("AGENCY_DB_PATH", "environment/state.db")

    cfg = load_config(config_path, reload=True)

    assert cfg.store.resolved_path() == (config_dir / "environment" / "state.db").resolve()


def test_missing_explicit_config_preserves_identity_and_relative_runtime_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "not-created" / "agency.yaml"
    monkeypatch.setenv("AGENCY_DB_PATH", "state/agency.db")

    cfg = load_config(config_path, reload=True)

    assert cfg.config_path == str(config_path.resolve())
    assert cfg.store.resolved_path() == (config_path.parent / "state" / "agency.db").resolve()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks are unavailable")
@pytest.mark.parametrize("link_final_component", [False, True])
def test_configured_store_path_rejects_symlink_components_before_resolution(
    tmp_path: Path,
    link_final_component: bool,
) -> None:
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    target_file = target_dir / "agency.db"
    target_file.write_bytes(b"")
    configured = tmp_path / ("linked.db" if link_final_component else "linked-parent/agency.db")
    link = configured if link_final_component else configured.parent
    target = target_file if link_final_component else target_dir
    try:
        link.symlink_to(target, target_is_directory=not link_final_component)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(
        f"store:\n  db_path: {configured.as_posix()}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="symlink or reparse point"):
        load_config(config_path, reload=True)


def test_env_auto_disables_ollama_mode(tmp_path: Path):
    """Setting a non-Ollama judge base_url disables ollama_mode."""
    os.environ["AGENCY_JUDGE_BASE_URL"] = "https://api.openai.com/v1"
    os.environ["AGENCY_JUDGE_MODEL"] = "gpt-4o-mini"
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
    assert cfg.judge.ollama_mode is False


def test_litellm_api_key_fallback(tmp_path: Path):
    """LITELLM_API_KEY is used when no direct key is set."""
    os.environ["LITELLM_API_KEY"] = "sk-test-123"
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
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


def test_no_private_operator_defaults(tmp_path: Path):
    """Ensure no private operator-specific identifiers are in defaults."""
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)
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


def test_store_expanduser_db_path_preserves_literal_tilde_in_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the leading user token is expanded; tildes in the home path are valid."""
    from agency_runtime.core.store.sqlite import Store

    home = tmp_path / "RUNNER~1"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    expected = home / "runtime" / "test.db"

    store = Store(Path("~") / "runtime" / "test.db")

    assert store.db_path == expected
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

    with pytest.raises(ValueError, match=r"judge\.base_url: credentials require HTTPS"):
        load_config(path, reload=True)


def test_environment_cannot_override_judge_credentials_to_remote_http(tmp_path: Path) -> None:
    os.environ["AGENCY_JUDGE_BASE_URL"] = "http://judge.invalid/v1"
    os.environ["AGENCY_JUDGE_API_KEY"] = "secret"

    with pytest.raises(ValueError, match="judge credentials"):
        load_config(tmp_path / "missing.yaml", reload=True)


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

    with pytest.raises(
        ValueError,
        match=r"adapters\.litellm\.base_url: credentials require HTTPS",
    ):
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

    with pytest.raises(ValueError, match=r"judge\.base_url: must be an uncredentialed"):
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


def test_workforce_default_hiring_budget_reserves_one_replacement_and_critique(
    tmp_path: Path,
) -> None:
    cfg = load_config(path=tmp_path / "missing.yaml", reload=True)

    assert cfg.workforce.hiring_call_budget == 4
    assert yaml.safe_load(config_to_yaml(cfg))["workforce"]["hiring_call_budget"] == 4


def test_observability_config_parses_false_and_retention(tmp_path):
    path = tmp_path / "agency.yaml"
    path.write_text(
        "observability:\n  capture_content: false\n  retention_days: 45\n",
        encoding="utf-8",
    )

    cfg = load_config(path=path, reload=True)

    assert cfg.observability.capture_content is False
    assert cfg.observability.retention_days == 45
