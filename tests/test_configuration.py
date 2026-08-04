"""Tests for the shared transactional configuration service."""

from __future__ import annotations

import os
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

from agency_runtime.core import configuration
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.configuration import (
    ConfigConflictError,
    ConfigurationError,
    ConfigValidationError,
    apply_config_operations,
    read_config_revision,
    read_config_state,
    replace_config_document,
    resolve_config_path,
)
from tests.runtime_support import is_agency_product_environment_key

pytestmark = pytest.mark.runtime_configuration_identity


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if is_agency_product_environment_key(name) or name in {
            "LITELLM_API_KEY",
            "OLLAMA_BASE_URL",
        }:
            monkeypatch.delenv(name, raising=False)
    reset_config_cache()
    yield
    reset_config_cache()


def _write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_resolve_config_path_honors_nonexistent_environment_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "new" / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(target))

    assert not target.exists()
    assert resolve_config_path() == target
    assert read_config_state().path == str(target)
    assert not target.exists()
    assert not target.parent.exists()


def test_resolve_config_path_defaults_to_user_runtime_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import configuration_persistence as persistence

    monkeypatch.delenv("AGENCY_CONFIG_PATH", raising=False)
    monkeypatch.setattr(persistence.Path, "home", classmethod(lambda _cls: tmp_path))

    assert resolve_config_path() == tmp_path / ".agency-runtime" / "agency.yaml"


@pytest.mark.parametrize("content", [b"null\n", b"~\n", b"---\n", b"# comment only\n"])
def test_state_rejects_nonempty_null_yaml_document(
    tmp_path: Path,
    content: bytes,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_bytes(content)

    with pytest.raises(
        ConfigValidationError,
        match="configuration root must be a mapping",
    ):
        read_config_state(path)


@pytest.mark.parametrize("content", [b"", b" \n\t\r\n"])
def test_state_accepts_only_empty_or_whitespace_yaml_document(
    tmp_path: Path,
    content: bytes,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_bytes(content)

    state = read_config_state(path)

    assert state.persisted == {}
    assert state.effective["profile"] == "standard"
    assert path.read_bytes() == content


def test_default_workforce_mode_funds_one_repair_per_inference_stage(tmp_path: Path) -> None:
    workforce = load_config(tmp_path / "missing.yaml", reload=True).workforce

    assert workforce.mode == "fast"
    assert workforce.fast_call_budget == 4


def test_explicit_fast_call_budget_remains_operator_owned(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    _write(path, {"workforce": {"fast_call_budget": 2}})

    assert load_config(path, reload=True).workforce.fast_call_budget == 2


def test_legacy_partial_balanced_budget_caps_omitted_fast_default(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    document = {"workforce": {"mode": "balanced", "balanced_call_budget": 3}}
    _write(path, document)

    loaded = load_config(path, reload=True).workforce

    assert loaded.mode == "balanced"
    assert loaded.fast_call_budget == 3
    assert loaded.balanced_call_budget == 3
    assert configuration.validate_config_document(document) == document


def test_state_separates_redacted_persisted_and_effective_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(
        path,
        {
            "judge": {
                "model": "file-model",
                "base_url": "https://api.example.test/v1",
                "api_key": "top-secret",
            },
            "adapters": {
                "litellm": {
                    "enabled": "true",
                    "base_url": "http://127.0.0.1:4000",
                    "api_key": "adapter-secret",
                }
            },
        },
    )
    monkeypatch.setenv("AGENCY_JUDGE_MODEL", "environment-model")

    state = read_config_state(path)

    assert state.persisted["judge"]["model"] == "file-model"
    assert state.effective["judge"]["model"] == "environment-model"
    assert state.persisted["judge"]["api_key"] == "***REDACTED***"
    assert state.effective["judge"]["api_key"] == "***REDACTED***"
    assert state.secret_presence == {
        "judge.api_key": True,
        "adapters.litellm.api_key": True,
    }
    assert state.environment_overrides["judge.model"] == "AGENCY_JUDGE_MODEL"
    assert "server.port" in state.restart_required_paths
    assert "top-secret" not in repr(state)
    assert "adapter-secret" not in repr(state)


def test_dashboard_port_environment_override_is_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(path, {"dashboard": {"port": 7811}})
    monkeypatch.setenv("AGENCY_DASHBOARD_PORT", "7911")

    state = read_config_state(path)

    assert state.persisted["dashboard"]["port"] == 7811
    assert state.effective["dashboard"]["port"] == 7911
    assert state.environment_overrides["dashboard.port"] == "AGENCY_DASHBOARD_PORT"
    assert "dashboard.port" in state.restart_required_paths


def test_companion_policy_environment_override_is_part_of_config_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    policy_path = tmp_path / "process-policy.yaml"
    _write(path, {"companion_policy_path": "persisted-policy.yaml"})
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(policy_path))

    state = read_config_state(path)

    assert state.persisted["companion_policy_path"] == "persisted-policy.yaml"
    assert state.effective["companion_policy_path"] == str(policy_path)
    assert state.environment_overrides["companion_policy_path"] == "AGENCY_POLICY_PATH"


@pytest.mark.parametrize("invalid", ["abc", "70000"])
def test_invalid_environment_override_is_rejected_without_echoing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_DASHBOARD_PORT", invalid)

    with pytest.raises(ConfigValidationError, match="override is invalid") as captured:
        read_config_state(path)

    assert invalid not in str(captured.value)


def test_typed_update_writes_atomically_and_reloads_effective_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)

    result = apply_config_operations(
        [
            {"op": "set", "path": "judge.model", "value": "updated-model"},
            {
                "op": "set",
                "path": "judge.base_url",
                "value": "http://127.0.0.1:11434",
            },
            {"op": "set", "path": "judge.ollama_mode", "value": True},
            {"op": "set", "path": "selector.min_confidence", "value": 0.65},
            {"op": "set", "path": "server.port", "value": 7811},
            {"op": "set", "path": "dashboard.port", "value": 7911},
            {
                "op": "secret",
                "path": "judge.api_key",
                "action": "replace",
                "value": "saved-secret",
            },
        ],
        expected_revision=state.revision,
        path=path,
    )

    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["judge"]["model"] == "updated-model"
    assert written["judge"]["api_key"] == "saved-secret"
    assert written["selector"]["min_confidence"] == 0.65
    assert result.state.persisted["judge"]["api_key"] == "***REDACTED***"
    assert result.state.secret_presence["judge.api_key"] is True
    assert result.restart_required == ("server.port", "dashboard.port")
    assert result.state.revision != state.revision
    assert "saved-secret" not in repr(result)

    loaded = load_config(path, reload=True)
    assert loaded.judge.model == "updated-model"
    assert loaded.selector.min_confidence == 0.65
    assert loaded.server.port == 7811
    assert loaded.dashboard.port == 7911

    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_workforce_policy_round_trips_through_shared_cli_dashboard_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)

    result = apply_config_operations(
        [
            {"op": "set", "path": "workforce.mode", "value": "strict"},
            {"op": "set", "path": "workforce.provider", "value": "codex-oauth"},
            {"op": "set", "path": "workforce.max_hires_per_task", "value": 0},
            {"op": "set", "path": "workforce.auto_promote_successes", "value": 12},
        ],
        expected_revision=state.revision,
        path=path,
    )

    assert result.state.persisted["workforce"] == {
        "mode": "strict",
        "provider": "codex-oauth",
        "max_hires_per_task": 0,
        "auto_promote_successes": 12,
    }
    loaded = load_config(path, reload=True)
    assert loaded.workforce.mode == "strict"
    assert loaded.workforce.provider == "codex-oauth"
    assert loaded.workforce.max_hires_per_task == 0
    assert loaded.workforce.auto_promote_successes == 12


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("workforce.mode", "guess", "unsupported value"),
        ("workforce.fast_call_budget", 5, "balanced_call_budget"),
        ("workforce.max_selected_total", 3, "max_selected_per_unit"),
        ("workforce.max_hires_per_day", -1, "supported range"),
        ("workforce.provider", "unsafe\x1b[31m", "terminal control"),
    ],
)
def test_workforce_policy_rejects_unsafe_or_incoherent_updates(
    tmp_path: Path,
    path: str,
    value: object,
    message: str,
) -> None:
    config_path = tmp_path / "agency.yaml"
    state = read_config_state(config_path)

    with pytest.raises(ConfigValidationError, match=message):
        apply_config_operations(
            [{"op": "set", "path": path, "value": value}],
            expected_revision=state.revision,
            path=config_path,
        )

    assert not config_path.exists()


def test_replace_document_uses_same_validation_lock_and_redacted_result(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)

    result = replace_config_document(
        {
            "profile": "standard",
            "dashboard": {"port": 7920},
            "judge": {
                "model": "configured-model",
                "base_url": "https://api.example.test/v1",
                "api_key": "replacement-document-secret",
                "ollama_mode": False,
            },
            "providers": [
                {
                    "name": "primary",
                    "type": "openai-compatible",
                    "model": "configured-model",
                    "base_url": "https://api.example.test/v1",
                    "api_key": "provider-document-secret",
                }
            ],
        },
        expected_revision=state.revision,
        path=path,
    )

    written = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert written["dashboard"]["port"] == 7920
    assert written["judge"]["api_key"] == "replacement-document-secret"
    assert result.state.persisted["judge"]["api_key"] == "***REDACTED***"
    assert result.restart_required == ("dashboard.port",)
    assert "replacement-document-secret" not in repr(result)
    assert "provider-document-secret" not in repr(result)


def test_trusted_replacement_recovers_invalid_existing_yaml_with_revision_check(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("judge: [invalid\n", encoding="utf-8")
    revision = read_config_revision(path)

    with pytest.raises(ConfigValidationError, match="not valid UTF-8 YAML"):
        replace_config_document(
            {"profile": "standard"},
            expected_revision=revision,
            path=path,
        )

    result = replace_config_document(
        {"profile": "standard", "dashboard": {"port": 7810}},
        expected_revision=revision,
        path=path,
        recover_invalid_existing=True,
    )

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == {
        "profile": "standard",
        "dashboard": {"port": 7810},
    }
    assert result.state.revision != revision


@pytest.mark.parametrize(
    "document",
    [
        "profile: standard\nprofile: power\n",
        "base: &base {profile: standard}\ncopy: *base\n",
        "profile: .nan\n",
    ],
)
def test_config_reader_rejects_ambiguous_yaml_constructs(
    document: str,
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ConfigValidationError, match="not valid UTF-8 YAML"):
        read_config_state(path)


def test_trusted_replacement_invalid_environment_preserves_original_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("judge: [invalid\n", encoding="utf-8")
    before = path.read_bytes()
    revision = read_config_revision(path)
    monkeypatch.setenv("AGENCY_DASHBOARD_PORT", "abc")

    with pytest.raises(ConfigValidationError, match="override is invalid"):
        replace_config_document(
            {"profile": "standard", "dashboard": {"port": 7810}},
            expected_revision=revision,
            path=path,
            recover_invalid_existing=True,
        )

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_noop_replace_and_preserve_keep_the_existing_revision(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    document = {
        "judge": {
            "model": "model",
            "base_url": "https://api.example.test/v1",
            "api_key": "preserved-secret",
        }
    }
    _write(path, document)
    state = read_config_state(path)

    replaced = replace_config_document(
        document,
        expected_revision=state.revision,
        path=path,
    )
    preserved = apply_config_operations(
        [{"op": "secret", "path": "judge.api_key", "action": "preserve"}],
        expected_revision=replaced.state.revision,
        path=path,
    )

    assert replaced.changed_paths == ()
    assert replaced.state.revision == state.revision
    assert preserved.changed_paths == ()
    assert preserved.state.revision == state.revision
    assert "preserved-secret" not in repr(replaced)
    assert "preserved-secret" not in repr(preserved)


def test_stale_revision_is_rejected_without_lost_update(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    initial = read_config_state(path)
    first = apply_config_operations(
        [{"op": "set", "path": "observability.retention_days", "value": 45}],
        expected_revision=initial.revision,
        path=path,
    )

    with pytest.raises(ConfigConflictError, match="refresh before saving"):
        apply_config_operations(
            [{"op": "set", "path": "observability.retention_days", "value": 90}],
            expected_revision=initial.revision,
            path=path,
        )

    assert read_config_state(path).revision == first.state.revision
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["observability"]["retention_days"] == 45


def test_locked_precondition_runs_after_revision_check_and_before_write(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    initial = read_config_state(path)
    calls: list[str] = []

    def refuse() -> None:
        calls.append("checked")
        raise RuntimeError("Store identity changed")

    with pytest.raises(RuntimeError, match="Store identity changed"):
        apply_config_operations(
            [{"op": "set", "path": "observability.retention_days", "value": 45}],
            expected_revision=initial.revision,
            path=path,
            locked_precondition=refuse,
        )
    assert calls == ["checked"]
    assert read_config_state(path).revision == initial.revision

    changed = apply_config_operations(
        [{"op": "set", "path": "observability.retention_days", "value": 45}],
        expected_revision=initial.revision,
        path=path,
    )
    with pytest.raises(ConfigConflictError, match="refresh before saving"):
        apply_config_operations(
            [{"op": "set", "path": "observability.retention_days", "value": 90}],
            expected_revision=initial.revision,
            path=path,
            locked_precondition=lambda: calls.append("stale"),
        )
    assert calls == ["checked"]
    assert read_config_state(path).revision == changed.state.revision


@pytest.mark.parametrize(
    "operation",
    [
        {"op": "set", "path": "unknown.field", "value": "x"},
        {"op": "set", "path": "observability.capture_content", "value": "false"},
        {"op": "set", "path": "observability.retention_days", "value": 0},
        {"op": "set", "path": "server.port", "value": True},
        {"op": "set", "path": "server.port", "value": 70000},
        {"op": "set", "path": "server.host", "value": "0.0.0.0"},
        {
            "op": "set",
            "path": "judge.base_url",
            "value": "https://user:password@example.test/v1",
        },
        {"op": "set", "path": "judge.api_key_env", "value": "NOT VALID"},
        {"op": "set", "path": "judge.timeout", "value": float("nan")},
    ],
)
def test_invalid_typed_updates_never_change_the_file(
    tmp_path: Path,
    operation: dict,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(path, {"profile": "standard"})
    before = path.read_bytes()
    revision = read_config_state(path).revision

    with pytest.raises(ConfigValidationError):
        apply_config_operations([operation], expected_revision=revision, path=path)

    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("LOCALHOST", "localhost"),
        ("127.0.0.42", "127.0.0.42"),
        ("::1", "::1"),
    ],
)
def test_server_host_accepts_loopback_values_used_by_cli_and_dashboard(
    tmp_path: Path,
    value: str,
    expected: str,
) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)

    result = apply_config_operations(
        [{"op": "set", "path": "server.host", "value": value}],
        expected_revision=state.revision,
        path=path,
    )

    assert result.changed_paths == ("server.host",)
    assert result.restart_required == ("server.host",)
    assert result.state.persisted["server"]["host"] == expected
    assert load_config(path, reload=True).server.host == expected


def test_secret_operations_preserve_replace_and_clear_without_echoing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(
        path,
        {
            "judge": {
                "model": "model",
                "base_url": "https://api.example.test/v1",
                "api_key": "original-secret",
            }
        },
    )
    state = read_config_state(path)
    preserved = apply_config_operations(
        [{"op": "secret", "path": "judge.api_key", "action": "preserve"}],
        expected_revision=state.revision,
        path=path,
    )
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["judge"]["api_key"] == (
        "original-secret"
    )

    replaced = apply_config_operations(
        [
            {
                "op": "secret",
                "path": "judge.api_key",
                "action": "replace",
                "value": "replacement-secret",
            }
        ],
        expected_revision=preserved.state.revision,
        path=path,
    )
    assert "replacement-secret" not in repr(replaced)
    assert "original-secret" not in repr(replaced)
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["judge"]["api_key"] == (
        "replacement-secret"
    )

    cleared = apply_config_operations(
        [{"op": "secret", "path": "judge.api_key", "action": "clear"}],
        expected_revision=replaced.state.revision,
        path=path,
    )
    assert cleared.state.secret_presence["judge.api_key"] is False
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["judge"]["api_key"] == ""

    with pytest.raises(ConfigValidationError) as captured:
        apply_config_operations(
            [
                {
                    "op": "secret",
                    "path": "judge.api_key",
                    "action": "replace",
                    "value": "***REDACTED***",
                }
            ],
            expected_revision=cleared.state.revision,
            path=path,
        )
    assert "REDACTED" not in str(captured.value)


def test_provider_update_preserves_secret_by_name_and_supports_ordering(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(
        path,
        {
            "providers": [
                {
                    "name": "primary",
                    "type": "openai-compatible",
                    "model": "old-model",
                    "base_url": "https://api.example.test/v1",
                    "api_key": "provider-secret",
                }
            ]
        },
    )
    state = read_config_state(path)
    result = apply_config_operations(
        [
            {
                "op": "set",
                "path": "providers",
                "value": [
                    {
                        "name": "ollama",
                        "type": "ollama",
                        "model": "qwen3.5:2b",
                        "base_url": "http://127.0.0.1:11434",
                        "ollama_mode": True,
                        "timeout": 10,
                    },
                    {
                        "name": "primary",
                        "type": "openai-compatible",
                        "model": "new-model",
                        "base_url": "https://api.example.test/v1",
                        "timeout": 20,
                    },
                ],
            }
        ],
        expected_revision=state.revision,
        path=path,
    )

    providers = yaml.safe_load(path.read_text(encoding="utf-8"))["providers"]
    assert [provider["name"] for provider in providers] == ["ollama", "primary"]
    assert providers[1]["api_key"] == "provider-secret"
    assert result.state.secret_presence["providers.1.api_key"] is True
    assert "provider-secret" not in repr(result)


@pytest.mark.parametrize(
    "providers",
    [
        [
            {
                "name": "cli-provider",
                "type": "cli",
                "model": "model",
                "base_url": "https://api.example.test/v1",
                "api_key_env": "API_KEY",
            }
        ],
        [
            {
                "name": "duplicate",
                "type": "ollama",
                "model": "one",
                "base_url": "http://127.0.0.1:11434",
            },
            {
                "name": "DUPLICATE",
                "type": "ollama",
                "model": "two",
                "base_url": "http://127.0.0.1:11434",
            },
        ],
        [
            {
                "name": "inline-secret",
                "type": "openai-compatible",
                "model": "model",
                "base_url": "https://api.example.test/v1",
                "api_key": "must-use-secret-operation",
            }
        ],
    ],
)
def test_provider_editor_rejects_unsupported_ambiguous_or_inline_secret_entries(
    tmp_path: Path,
    providers: list[dict],
) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)

    with pytest.raises(ConfigValidationError):
        apply_config_operations(
            [{"op": "set", "path": "providers", "value": providers}],
            expected_revision=state.revision,
            path=path,
        )

    assert not path.exists()


def test_provider_secret_can_be_set_after_adding_provider(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)
    result = apply_config_operations(
        [
            {
                "op": "set",
                "path": "providers",
                "value": [
                    {
                        "name": "remote",
                        "type": "anthropic",
                        "model": "claude-model",
                        "base_url": "https://api.anthropic.com/v1",
                    }
                ],
            },
            {
                "op": "secret",
                "path": "providers.0.api_key",
                "action": "replace",
                "value": "provider-secret",
            },
        ],
        expected_revision=state.revision,
        path=path,
    )

    assert result.state.secret_presence["providers.0.api_key"] is True
    assert "provider-secret" not in repr(result)


def test_cli_provider_and_keyless_loopback_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)
    result = apply_config_operations(
        [
            {
                "op": "set",
                "path": "providers",
                "value": [
                    {
                        "name": "codex",
                        "type": "cli",
                        "transport": "codex",
                        "model": "",
                        "base_url": "",
                        "timeout": 3,
                        "reasoning_effort": "low",
                    },
                    {
                        "name": "lm-studio",
                        "type": "openai-compatible",
                        "model": "local-model",
                        "base_url": "http://127.0.0.1:1234/v1",
                        "timeout": 3,
                    },
                ],
            }
        ],
        expected_revision=state.revision,
        path=path,
    )

    assert result.state.persisted["providers"][0]["transport"] == "codex"
    assert result.state.persisted["providers"][0]["reasoning_effort"] == "low"
    loaded = load_config(path, reload=True)
    assert loaded.providers[0].auth_method() == "oauth"
    assert loaded.providers[0].reasoning_effort == "low"
    assert loaded.providers[0].is_available() is True
    assert loaded.providers[1].is_available() is True


def test_cli_provider_rejects_windows_batch_metacharacters_in_model(
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigValidationError, match=r"providers\.0\.model"):
        replace_config_document(
            {
                "providers": [
                    {
                        "name": "codex-cli",
                        "type": "cli",
                        "transport": "codex",
                        "model": "gpt-5&whoami",
                    }
                ],
            },
            expected_revision=read_config_state(tmp_path / "agency.yaml").revision,
            path=tmp_path / "agency.yaml",
        )


@pytest.mark.parametrize(
    "provider",
    [
        {
            "name": "claude-cli",
            "type": "cli",
            "transport": "claude",
            "reasoning_effort": "low",
        },
        {
            "name": "remote",
            "type": "openai-compatible",
            "model": "model",
            "base_url": "https://api.example.test/v1",
            "api_key_env": "AGENCY_API_KEY",
            "reasoning_effort": "low",
        },
        {
            "name": "codex-cli",
            "type": "cli",
            "transport": "codex",
            "reasoning_effort": "extreme",
        },
    ],
)
def test_reasoning_effort_is_bounded_to_supported_codex_cli_values(
    provider: dict[str, object],
    tmp_path: Path,
) -> None:
    with pytest.raises(ConfigValidationError, match="reasoning_effort"):
        replace_config_document(
            {"providers": [provider]},
            expected_revision=read_config_state(tmp_path / "agency.yaml").revision,
            path=tmp_path / "agency.yaml",
        )


def test_provider_chain_rejects_more_entries_than_runtime_can_attempt(
    tmp_path: Path,
) -> None:
    providers = [
        {
            "name": f"provider-{index}",
            "type": "ollama",
            "model": "model",
            "base_url": "http://127.0.0.1:11434",
        }
        for index in range(5)
    ]
    with pytest.raises(ConfigValidationError, match="at most 4"):
        replace_config_document(
            {"providers": providers},
            expected_revision=read_config_state(tmp_path / "agency.yaml").revision,
            path=tmp_path / "agency.yaml",
        )


@pytest.mark.parametrize("field", ["name", "model"])
def test_provider_display_tokens_reject_terminal_controls(
    field: str,
    tmp_path: Path,
) -> None:
    provider = {
        "name": "provider",
        "type": "ollama",
        "model": "model",
        "base_url": "http://127.0.0.1:11434",
    }
    provider[field] = "unsafe\x1b[31m"
    with pytest.raises(ConfigValidationError, match="terminal control"):
        replace_config_document(
            {"providers": [provider]},
            expected_revision=read_config_state(tmp_path / "agency.yaml").revision,
            path=tmp_path / "agency.yaml",
        )


def test_keyless_remote_compatible_provider_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)
    with pytest.raises(ConfigValidationError, match="authentication"):
        apply_config_operations(
            [
                {
                    "op": "set",
                    "path": "providers",
                    "value": [
                        {
                            "name": "remote",
                            "type": "openai-compatible",
                            "model": "model",
                            "base_url": "https://provider.invalid/v1",
                        }
                    ],
                }
            ],
            expected_revision=state.revision,
            path=path,
        )


@pytest.mark.parametrize(
    "document",
    [
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
        },
        {
            "judge": {
                "model": "model",
                "base_url": "http://judge.invalid/v1",
                "api_key_env": "JUDGE_KEY",
            },
        },
        {
            "adapters": {
                "litellm": {
                    "base_url": "http://adapter.invalid",
                    "api_key": "secret",
                },
            },
        },
    ],
)
def test_strict_writer_rejects_credentials_over_remote_http(
    document: dict,
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"

    with pytest.raises(ConfigValidationError, match="literal loopback HTTP"):
        replace_config_document(
            document,
            expected_revision=read_config_state(path).revision,
            path=path,
        )


def test_strict_writer_accepts_credentials_over_literal_loopback_http(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    result = replace_config_document(
        {
            "judge": {
                "model": "model",
                "base_url": "http://[::1]:4000/v1",
                "api_key": "secret",
            },
        },
        expected_revision=read_config_state(path).revision,
        path=path,
    )

    assert result.state.persisted["judge"]["api_key"] == "***REDACTED***"


def test_strict_writer_rejects_query_bearing_base_url(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"

    with pytest.raises(ConfigValidationError, match="HTTP"):
        replace_config_document(
            {
                "judge": {
                    "base_url": "https://judge.invalid/v1?token=leaky",
                    "api_key": "secret",
                },
            },
            expected_revision=read_config_state(path).revision,
            path=path,
        )


def test_local_only_profile_enforces_local_provider_and_disables_adapters(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(
        path,
        {
            "profile": "standard",
            "judge": {
                "model": "remote",
                "base_url": "https://api.example.test/v1",
                "api_key": "remote-secret",
            },
            "ollama": {
                "enabled": False,
                "base_url": "https://remote.example.test",
                "model": "local-model",
            },
            "adapters": {
                "litellm": {
                    "enabled": "true",
                    "base_url": "http://127.0.0.1:4000",
                },
                "codex": {"enabled": "true"},
            },
        },
    )
    state = read_config_state(path)
    result = apply_config_operations(
        [{"op": "set", "path": "profile", "value": "local-only"}],
        expected_revision=state.revision,
        path=path,
    )

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert result.policy_enforced is True
    assert document["profile"] == "local-only"
    assert document["judge"]["api_key"] == ""
    assert document["judge"]["base_url"] == "http://127.0.0.1:11434"
    assert [provider["type"] for provider in document["providers"]] == ["ollama"]
    assert all(entry["enabled"] == "false" for entry in document["adapters"].values())
    assert result.state.secret_presence["judge.api_key"] is False
    assert "remote-secret" not in repr(result)


def test_atomic_replace_failure_preserves_original_and_removes_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    _write(path, {"profile": "standard"})
    before = path.read_bytes()
    state = read_config_state(path)

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(configuration.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        apply_config_operations(
            [{"op": "set", "path": "profile", "value": "power"}],
            expected_revision=state.revision,
            path=path,
        )

    assert path.read_bytes() == before
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits are not Windows ACLs")
def test_environment_config_path_preserves_preexisting_parent_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "shared"
    parent.mkdir()
    parent.chmod(0o755)
    target = parent / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(target))
    revision = read_config_state().revision

    apply_config_operations(
        [{"op": "set", "path": "profile", "value": "power"}],
        expected_revision=revision,
    )

    assert stat.S_IMODE(parent.stat().st_mode) == 0o755
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_environment_config_path_never_rewrites_preexisting_parent_acl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "shared"
    parent.mkdir()
    target = parent / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(target))
    calls: list[tuple[Path, bool]] = []
    monkeypatch.setattr(configuration, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        configuration._persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )

    def allow_acl(candidate: Path, *, directory: bool = False) -> bool:
        calls.append((candidate, directory))
        return True

    monkeypatch.setattr(configuration, "_restrict_windows_acl", allow_acl)

    configuration._atomic_write_yaml(
        resolve_config_path(),
        {"profile": "power"},
    )

    assert (parent, True) not in calls
    assert calls
    assert all(candidate != parent for candidate, _directory in calls)


def test_config_hardens_a_newly_created_target_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "owned" / "runtime" / "agency.yaml"
    calls: list[tuple[Path, bool]] = []

    def observe(
        candidate: Path,
        *,
        required: bool = False,
        directory: bool = False,
    ) -> bool:
        del required
        calls.append((candidate, directory))
        return True

    # Exercise the generic creation boundary. On Windows, Codex can register
    # an identity-pinned private-path authority whose own hardening seam owns
    # this directory; the POSIX branch keeps this test focused on the generic
    # persistence callback on every test host.
    monkeypatch.setattr(configuration, "_IS_WINDOWS", False)
    monkeypatch.setattr(
        configuration._persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )
    monkeypatch.setattr(configuration, "_restrict_permissions", observe)

    configuration._atomic_write_yaml(target, {"profile": "standard"})

    assert (target.parent, True) in calls


def test_private_write_fails_before_replace_when_windows_acl_cannot_be_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "agency.yaml"
    path.write_text("profile: standard\n", encoding="utf-8")
    before = path.read_bytes()
    observed_temporary_bytes: list[bytes] = []
    replace_calls: list[tuple[Path, Path]] = []
    monkeypatch.setattr(configuration, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        configuration._persistence,
        "assert_config_namespace",
        lambda _path, **_kwargs: None,
    )

    def deny_private_acl(candidate: Path) -> bool:
        observed_temporary_bytes.append(candidate.read_bytes())
        return False

    monkeypatch.setattr(configuration, "_restrict_windows_acl", deny_private_acl)
    monkeypatch.setattr(
        configuration.os,
        "replace",
        lambda source, destination: replace_calls.append((source, destination)),
    )

    with pytest.raises(ConfigurationError, match="owner-only"):
        configuration._atomic_write_yaml(
            path,
            {"judge": {"api_key": "never-written-config-secret"}},
        )

    # Existing config privacy is now verified before even allocating a
    # candidate, so a denied ACL hardening attempt observes only the old bytes.
    assert observed_temporary_bytes == [before]
    assert replace_calls == []
    assert path.read_bytes() == before
    assert b"never-written-config-secret" not in path.read_bytes()
    assert list(tmp_path.glob(".agency.yaml.*.tmp")) == []


def test_cross_process_lock_and_revision_allow_only_one_concurrent_writer(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    revision = read_config_state(path).revision

    def update(days: int):
        return apply_config_operations(
            [{"op": "set", "path": "observability.retention_days", "value": days}],
            expected_revision=revision,
            path=path,
        )

    successes = []
    conflicts = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(update, days) for days in (30, 60)]
        for future in futures:
            try:
                successes.append(future.result(timeout=5))
            except ConfigConflictError as exc:
                conflicts.append(exc)

    assert len(successes) == 1
    assert len(conflicts) == 1
    stored_days = yaml.safe_load(path.read_text(encoding="utf-8"))["observability"][
        "retention_days"
    ]
    assert stored_days in {30, 60}


def test_config_lock_rejects_symlink_without_touching_its_target(
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.yaml"
    target = tmp_path / "unrelated.txt"
    target.write_bytes(b"unrelated")
    lock_path = tmp_path / ".agency.yaml.lock"
    try:
        lock_path.symlink_to(target)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(configuration.ConfigLockError, match="symlink or reparse"):
        apply_config_operations(
            [{"op": "set", "path": "profile", "value": "power"}],
            expected_revision=read_config_state(path).revision,
            path=path,
        )

    assert target.read_bytes() == b"unrelated"
    assert not path.exists()


def test_config_writer_rejects_symlink_target(tmp_path: Path) -> None:
    destination = tmp_path / "destination.yaml"
    destination.write_text("profile: standard\n", encoding="utf-8")
    link = tmp_path / "agency.yaml"
    try:
        link.symlink_to(destination)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ConfigurationError, match="symlink or reparse"):
        configuration._atomic_write_yaml(link, {"profile": "power"})

    assert destination.read_text(encoding="utf-8") == "profile: standard\n"
    assert link.is_symlink()


def test_config_writer_rejects_symlink_parent_directory(tmp_path: Path) -> None:
    destination = tmp_path / "destination"
    destination.mkdir()
    link = tmp_path / "redirect"
    try:
        link.symlink_to(destination, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    with pytest.raises(ConfigurationError, match="directory symlink or reparse"):
        configuration._atomic_write_yaml(
            link / "agency.yaml",
            {"profile": "power"},
        )

    assert not (destination / "agency.yaml").exists()


def test_document_validation_rejects_unknown_fields_and_string_booleans() -> None:
    with pytest.raises(ConfigValidationError, match="unsupported top-level"):
        configuration.validate_config_document({"unknown": {}})

    with pytest.raises(ConfigValidationError, match="JSON boolean"):
        configuration.validate_config_document({"observability": {"capture_content": "false"}})

    assert configuration.validate_config_document({"adapters": {"codex": {"enabled": True}}}) == {
        "adapters": {"codex": {"enabled": "true"}}
    }


def test_config_errors_do_not_include_submitted_secret_value(tmp_path: Path) -> None:
    path = tmp_path / "agency.yaml"
    state = read_config_state(path)
    secret = "do-not-echo-this-secret"

    with pytest.raises(ConfigValidationError) as captured:
        apply_config_operations(
            [
                {
                    "op": "secret",
                    "path": "unsupported.api_key",
                    "action": "replace",
                    "value": secret,
                }
            ],
            expected_revision=state.revision,
            path=path,
        )

    assert secret not in str(captured.value)
