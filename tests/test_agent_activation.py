"""End-to-end contracts for reversible per-agent routing availability."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from agency_runtime.cli import main as cli_main
from agency_runtime.cli import roster_commands
from agency_runtime.core.agent_activation import (
    MAX_DISABLED_AGENTS,
    PROTECTED_AGENT_SLUGS,
    agent_is_enabled,
    normalize_agent_slug,
    normalize_disabled_agents,
    updated_disabled_agents,
)
from agency_runtime.core.config import load_config, reset_config_cache
from agency_runtime.core.configuration import (
    ConfigValidationError,
    apply_config_operations,
    read_config_state,
    validate_config_document,
)
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.store.sqlite import Store


def _agent(slug: str) -> dict[str, object]:
    return next(dict(agent) for agent in BundledRoster() if agent["slug"] == slug)


@pytest.fixture()
def activation_runtime(tmp_path, monkeypatch):
    config_path = tmp_path / "agency.yaml"
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    reset_config_cache()
    store = Store(tmp_path / "agency.db")
    for slug in ("agents-orchestrator", "chief-of-staff", "code-reviewer"):
        store._activate_prevalidated_agent(_agent(slug))
    monkeypatch.setattr(roster_commands, "_store", lambda *_args: store)
    try:
        yield store, config_path
    finally:
        reset_config_cache()


def test_activation_normalization_is_bounded_and_protects_coordinators() -> None:
    assert normalize_agent_slug("  Code-Reviewer ") == "code-reviewer"
    assert normalize_agent_slug("Code.Reviewer_V2") == "code.reviewer_v2"
    for invalid in (None, "", "a", "not valid", "/leading", "a" * 129):
        with pytest.raises(ValueError):
            normalize_agent_slug(invalid)
    assert normalize_disabled_agents(["z-agent", "a-agent"]) == ("a-agent", "z-agent")
    with pytest.raises(ValueError, match="list"):
        normalize_disabled_agents("code-reviewer")
    with pytest.raises(ValueError, match="duplicates"):
        normalize_disabled_agents(["code-reviewer", "code-reviewer"])
    with pytest.raises(ValueError, match="at most"):
        normalize_disabled_agents([f"agent-{index}" for index in range(MAX_DISABLED_AGENTS + 1)])
    for slug in PROTECTED_AGENT_SLUGS:
        with pytest.raises(ValueError, match="protected coordinator"):
            normalize_disabled_agents([slug])
        with pytest.raises(ValueError, match="protected coordinator"):
            updated_disabled_agents([], slug, enabled=False)
        assert agent_is_enabled(slug, [slug]) is True
    with pytest.raises(ValueError, match="boolean"):
        updated_disabled_agents([], "code-reviewer", enabled=1)  # type: ignore[arg-type]


def test_config_schema_patch_and_raw_loader_share_protected_policy(
    activation_runtime,
) -> None:
    _store, config_path = activation_runtime
    assert validate_config_document({"agents": {"disabled": ["code-reviewer"]}}) == {
        "agents": {"disabled": ["code-reviewer"]}
    }
    with pytest.raises(ConfigValidationError, match="protected coordinator"):
        validate_config_document({"agents": {"disabled": ["chief-of-staff"]}})
    with pytest.raises(ConfigValidationError, match="unsupported fields"):
        validate_config_document({"agents": {"disabled": [], "unknown": True}})

    state = read_config_state()
    result = apply_config_operations(
        [{"op": "set", "path": "agents.disabled", "value": ["code-reviewer"]}],
        expected_revision=state.revision,
    )
    assert result.state.effective["agents"]["disabled"] == ["code-reviewer"]
    assert yaml.safe_load(config_path.read_text(encoding="utf-8"))["agents"] == {
        "disabled": ["code-reviewer"]
    }
    reset_config_cache()
    assert load_config().agents.disabled == ("code-reviewer",)

    config_path.write_text("agents:\n  disabled: [agents-orchestrator]\n", encoding="utf-8")
    reset_config_cache()
    with pytest.raises(ValueError, match="protected coordinator"):
        load_config()


def test_store_excludes_disabled_agents_without_deleting_roster(
    activation_runtime,
) -> None:
    store, _config_path = activation_runtime
    assert store.count_enabled_roster() == store.count_active_roster() == 3
    state = read_config_state()
    apply_config_operations(
        [{"op": "set", "path": "agents.disabled", "value": ["code-reviewer"]}],
        expected_revision=state.revision,
    )

    assert {row["agent_slug"] for row in store.get_active_roster()} == {
        "agents-orchestrator",
        "chief-of-staff",
        "code-reviewer",
    }
    assert {row["agent_slug"] for row in store.get_enabled_roster()} == {
        "agents-orchestrator",
        "chief-of-staff",
    }
    assert {row["slug"] for row in store.get_active_roster_as_catalog()} == {
        "agents-orchestrator",
        "chief-of-staff",
    }
    assert store.count_active_roster() == 3
    assert store.count_enabled_roster() == 2
    assert store.get_specialist_prompt("code-reviewer") is None
    assert store.get_roster_entry("code-reviewer") is not None
    assert len(store.get_enabled_roster(limit=1)) == 1
    with pytest.raises(TypeError):
        store.get_enabled_roster(limit=True)
    with pytest.raises(ValueError):
        store.get_enabled_roster(limit=0)

    _config_path.write_text("agents:\n  disabled: []\n", encoding="utf-8")
    assert store.count_enabled_roster() == 3


def test_activation_policy_cache_reparses_only_after_external_change(
    activation_runtime,
    monkeypatch,
) -> None:
    store, config_path = activation_runtime
    from agency_runtime.core import config as config_module

    original_load_yaml = config_module._load_yaml
    loaded_paths: list[Path] = []

    def tracked_load_yaml(path: Path) -> dict[str, object]:
        loaded_paths.append(path)
        return original_load_yaml(path)

    monkeypatch.setattr(config_module, "_load_yaml", tracked_load_yaml)
    reset_config_cache()

    assert store.count_enabled_roster() == 3
    initial_load_count = len(loaded_paths)
    # The loader reads both bundled defaults and the configured identity. It
    # deliberately opens the latter directly instead of adding a racy exists()
    # pre-check, even while the first-run file is still absent.
    assert initial_load_count == 2
    assert store.get_active_roster_as_catalog()
    assert store.get_specialist_prompt("code-reviewer") is not None
    assert len(loaded_paths) == initial_load_count

    config_path.write_text(
        "agents:\n  disabled: [code-reviewer]\n",
        encoding="utf-8",
    )
    assert store.count_enabled_roster() == 2
    assert len(loaded_paths) == initial_load_count + 2
    assert store.get_specialist_prompt("code-reviewer") is None
    assert len(loaded_paths) == initial_load_count + 2


def test_cli_lists_toggles_and_reenables_preserved_agent(
    activation_runtime,
    capsys,
) -> None:
    store, _config_path = activation_runtime
    assert roster_commands.cmd_agents_list(SimpleNamespace(json=False)) == 0
    listed = capsys.readouterr().out
    assert "config\t" in listed
    assert "protected\tagents-orchestrator" in listed

    assert roster_commands.cmd_agent_disable(SimpleNamespace(slug="code-reviewer")) == 0
    assert "code-reviewer is disabled" in capsys.readouterr().out
    assert store.get_roster_entry("code-reviewer") is not None
    assert roster_commands.cmd_agent_disable(SimpleNamespace(slug="code-reviewer")) == 0
    assert "already disabled" in capsys.readouterr().out
    assert roster_commands.cmd_agent_enable(SimpleNamespace(slug="code-reviewer")) == 0
    assert "code-reviewer is enabled" in capsys.readouterr().out
    assert roster_commands.cmd_agent_enable(SimpleNamespace(slug="code-reviewer")) == 0
    assert "already enabled" in capsys.readouterr().out

    assert roster_commands.cmd_agents_list(SimpleNamespace(json=True)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config_path"].endswith("agency.yaml")
    assert (
        next(row for row in payload["agents"] if row["slug"] == "code-reviewer")["enabled"] is True
    )
    with pytest.raises(ValueError, match="protected coordinator"):
        roster_commands.cmd_agent_disable(SimpleNamespace(slug="chief-of-staff"))
    with pytest.raises(ValueError, match="not present"):
        roster_commands.cmd_agent_disable(SimpleNamespace(slug="missing-agent"))


def test_cli_parser_executes_agent_toggle_and_reports_protected_error(
    activation_runtime,
    capsys,
) -> None:
    _store, _config_path = activation_runtime
    assert cli_main.main(["agents", "disable", "code-reviewer"]) == 0
    assert "code-reviewer is disabled" in capsys.readouterr().out
    assert cli_main.main(["agents", "enable", "code-reviewer"]) == 0
    assert "code-reviewer is enabled" in capsys.readouterr().out
    assert cli_main.main(["agents", "disable", "agents-orchestrator"]) == 1
    assert "protected coordinator" in capsys.readouterr().err


def test_cli_agent_controls_accept_explicit_config_and_report_its_identity(
    activation_runtime,
    capsys,
) -> None:
    _store, config_path = activation_runtime

    assert cli_main.main(["agents", "disable", "code-reviewer", "--config", str(config_path)]) == 0
    disabled = capsys.readouterr().out
    assert f"config\t{config_path}" in disabled
    assert "code-reviewer is disabled" in disabled

    assert cli_main.main(["agents", "list", "--config", str(config_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["config_path"] == str(config_path)
    reviewer = next(row for row in payload["agents"] if row["slug"] == "code-reviewer")
    assert reviewer["enabled"] is False

    assert cli_main.main(["agents", "enable", "code-reviewer", "--config", str(config_path)]) == 0
    enabled = capsys.readouterr().out
    assert f"config\t{config_path}" in enabled
    assert "code-reviewer is enabled" in enabled
