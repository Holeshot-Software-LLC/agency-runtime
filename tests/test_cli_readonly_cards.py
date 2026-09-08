"""Read-only cards preserve output and trust boundaries under governed TTY defaults."""

from __future__ import annotations

import argparse
from types import SimpleNamespace

import pytest

from agency_runtime.cli import _render, config_commands, roster_commands
from agency_runtime.core.config import AgencyConfig, JudgeConfig, ProviderEntry, config_to_yaml
from tests.test_cli_parser_contract import _parser


def _args(**changes):
    return argparse.Namespace(**{"card": None, "json": False, "raw": False, **changes})


@pytest.mark.parametrize(
    "argv",
    [
        ["roster", "list"],
        ["policy"],
        ["config", "show"],
        ["config", "get", "profile"],
        ["config", "provider", "list"],
    ],
)
def test_readonly_card_parser_supports_default_enable_and_disable(argv):
    parser = _parser()
    assert parser.parse_args(argv).card is None
    assert parser.parse_args([*argv, "--card"]).card is True
    assert parser.parse_args([*argv, "--no-card"]).card is False


@pytest.mark.parametrize("argv", [["policy"], ["config", "provider", "list"]])
def test_existing_json_and_card_flags_can_be_combined(argv):
    parsed = _parser().parse_args([*argv, "--card", "--json"])
    assert parsed.card is True
    assert parsed.json is True


@pytest.mark.parametrize(
    "argv",
    [
        ["config", "set", "profile", "standard"],
        ["config", "reset"],
        ["roster", "approve", "snapshot"],
        ["roster", "diff"],
    ],
)
def test_card_flag_does_not_expand_mutating_commands(argv):
    with pytest.raises(SystemExit) as raised:
        _parser().parse_args([*argv, "--card"])
    assert raised.value.code == 2


@pytest.fixture
def roster(monkeypatch):
    rows = [
        {"slug": "enabled", "name": "Enabled worker", "division": "engineering", "enabled": True},
        {"slug": "disabled", "name": "Hidden worker", "division": "operations", "enabled": False},
    ]
    monkeypatch.setattr(roster_commands, "_activation_rows", lambda: ("unused", rows))
    return rows


@pytest.mark.parametrize("tty", [False, True])
def test_roster_non_tty_and_explicit_plain_bytes(roster, monkeypatch, capsys, tty):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    assert roster_commands.cmd_roster_list(_args(card=False if tty else None)) == 0
    assert capsys.readouterr().out == "enabled\tEnabled worker\tengineering\n"


def test_roster_cards_preserve_enabled_filter(roster, capsys):
    assert roster_commands.cmd_roster_list(_args(card=True)) == 0
    output = capsys.readouterr().out
    assert _render.divider() in output
    assert "Enabled worker" in output
    assert "engineering" in output
    assert "disabled" not in output
    assert "Hidden worker" not in output


def test_empty_roster_card_does_not_fabricate_a_worker(roster, capsys):
    roster.clear()
    assert roster_commands.cmd_roster_list(_args(card=True)) == 0
    assert capsys.readouterr().out == ""


@pytest.fixture
def config_dependencies():
    config = AgencyConfig(
        judge=JudgeConfig(model="fixture-model", api_key="fixture-judge-secret"),
        providers=(ProviderEntry(name="fixture-provider", api_key="fixture-provider-secret"),),
    )
    return config_commands.ConfigurationDependencies(load_config=lambda: config)


@pytest.mark.parametrize("raw", [False, True])
def test_config_show_cards_reuse_existing_redaction(config_dependencies, capsys, raw):
    assert (
        config_commands.cmd_config_show(_args(card=True, raw=raw), dependencies=config_dependencies)
        == 0
    )
    output = capsys.readouterr().out
    assert _render.divider() in output
    assert "fixture-model" in output
    assert ("fixture-judge-secret" in output) is raw
    assert ("fixture-provider-secret" in output) is raw
    assert ("raw requested" if raw else "secrets redacted") in output


@pytest.mark.parametrize("tty", [False, True])
def test_config_show_non_tty_and_explicit_plain_bytes(
    config_dependencies, monkeypatch, capsys, tty
):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    assert (
        config_commands.cmd_config_show(
            _args(card=False if tty else None), dependencies=config_dependencies
        )
        == 0
    )
    assert capsys.readouterr().out == config_to_yaml(config_dependencies.load_config()) + "\n"


@pytest.mark.parametrize("raw", [False, True])
@pytest.mark.parametrize("key", ["judge.api_key", "providers"])
def test_config_get_cards_preserve_scalar_and_nested_secret_rules(
    config_dependencies, capsys, raw, key
):
    assert (
        config_commands.cmd_config_get(
            _args(card=True, key=key, raw=raw), dependencies=config_dependencies
        )
        == 0
    )
    output = capsys.readouterr().out
    expected = "fixture-judge-secret" if key == "judge.api_key" else "fixture-provider-secret"
    assert (expected in output) is raw
    assert _render.divider() in output
    if not raw:
        assert "***REDACTED***" in output


@pytest.mark.parametrize("card", [False, True])
def test_config_get_missing_key_keeps_error_and_exit_code(config_dependencies, capsys, card):
    assert (
        config_commands.cmd_config_get(
            _args(card=card, key="judge.not_a_key"), dependencies=config_dependencies
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Key not found: judge.not_a_key\n"


@pytest.mark.parametrize("tty", [False, True])
def test_config_get_non_tty_and_explicit_plain_bytes(config_dependencies, monkeypatch, capsys, tty):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    assert (
        config_commands.cmd_config_get(
            _args(card=False if tty else None, key="judge.api_key"),
            dependencies=config_dependencies,
        )
        == 0
    )
    assert capsys.readouterr().out == "***REDACTED***\n"


def test_config_card_truncation_is_disclosed_and_bounded(capsys):
    dependencies = config_commands.ConfigurationDependencies(
        load_config=lambda: AgencyConfig(operator_policy="x" * 5000)
    )
    assert (
        config_commands.cmd_config_get(
            _args(card=True, key="operator_policy"), dependencies=dependencies
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Display truncated; use --no-card for the complete value." in output
    assert "x" * 5000 not in output
    assert len(output.encode()) < 5000


def test_config_show_groups_every_projected_top_level_section(monkeypatch, capsys):
    monkeypatch.setattr(
        config_commands,
        "config_to_yaml",
        lambda *_args, **_kwargs: "first:\n  note: " + "x" * 5000 + "\nlast: retained\n",
    )
    dependencies = config_commands.ConfigurationDependencies(load_config=lambda: object())
    assert config_commands.cmd_config_show(_args(card=True), dependencies=dependencies) == 0
    output = capsys.readouterr().out
    assert "Display truncated" in output
    assert "last: retained" in output


@pytest.fixture
def configured_providers(monkeypatch):
    rows = [
        {
            "name": "primary",
            "type": "cli",
            "transport": "fixture-transport",
            "model": "fixture-model",
            "reasoning_effort": "high",
            "api_key": "fixture-do-not-display",
        }
    ]
    monkeypatch.setattr(
        config_commands, "read_config_state", lambda: SimpleNamespace(persisted={"providers": rows})
    )
    return rows


def test_provider_cards_only_display_existing_public_fields(configured_providers, capsys):
    assert config_commands.cmd_config_provider_list(_args(card=True)) == 0
    output = capsys.readouterr().out
    assert "fixture-model" in output
    assert "fixture-transport" in output
    assert "high" in output
    assert "fixture-do-not-display" not in output
    assert _render.divider() in output


def test_provider_json_bytes_win_over_cards(configured_providers, monkeypatch, capsys):
    monkeypatch.setattr(_render, "_isatty", lambda: True)
    assert config_commands.cmd_config_provider_list(_args(json=True)) == 0
    original = capsys.readouterr().out
    assert config_commands.cmd_config_provider_list(_args(json=True, card=True)) == 0
    assert capsys.readouterr().out == original
    assert "fixture-do-not-display" not in original


def test_empty_provider_list_keeps_original_message(configured_providers, capsys):
    configured_providers.clear()
    assert config_commands.cmd_config_provider_list(_args(card=True)) == 0
    assert capsys.readouterr().out == "No inference providers configured.\n"


@pytest.mark.parametrize("tty", [False, True])
def test_provider_non_tty_and_explicit_plain_bytes(configured_providers, monkeypatch, capsys, tty):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    assert config_commands.cmd_config_provider_list(_args(card=False if tty else None)) == 0
    assert capsys.readouterr().out == (
        "1. primary · cli · model/router=fixture-model · reasoning=high · fixture-transport\n"
    )


@pytest.fixture
def policy_projection(monkeypatch):
    policy = {
        "actions": {"review": {"always_include": [{"slug": "required"}]}},
        "division_anchors": {"engineering": []},
    }
    validation = {
        "valid": False,
        "errors": ["Required specialist is missing"],
        "mode": "roster-gated",
        "route_count": 2,
        "unique_policy_slugs": ["required", "disabled"],
        "enabled_slugs": ["required"],
        "missing_enabled": ["required"],
        "disabled_count": 1,
        "disabled_routes": [{"slug": "disabled"}],
        "routes": [{"source": "division", "group": "engineering", "slug": "disabled"}],
    }
    monkeypatch.setattr(roster_commands, "_policy_operation", lambda *_args: (policy, {"active"}))
    monkeypatch.setattr(roster_commands, "validate_policy", lambda *_args: validation)
    return validation


@pytest.mark.parametrize("valid", [False, True])
def test_policy_cards_preserve_validation_and_division_evidence(policy_projection, capsys, valid):
    policy_projection["valid"] = valid
    assert roster_commands.cmd_policy(_args(card=True)) == (0 if valid else 1)
    output = capsys.readouterr().out
    assert output.splitlines()[1].split()[-1] == ("VALID" if valid else "INVALID")
    assert "Required specialist is missing" in output
    assert "engineering" in output
    assert "disabled" in output
    assert "review" in output


def test_policy_json_bytes_win_over_cards(policy_projection, monkeypatch, capsys):
    monkeypatch.setattr(_render, "_isatty", lambda: True)
    assert roster_commands.cmd_policy(_args(json=True)) == 1
    original = capsys.readouterr().out
    assert roster_commands.cmd_policy(_args(json=True, card=True)) == 1
    assert capsys.readouterr().out == original


@pytest.mark.parametrize("tty", [False, True])
def test_policy_non_tty_and_explicit_plain_report(policy_projection, monkeypatch, capsys, tty):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    calls = []
    monkeypatch.setattr(
        roster_commands, "_print_policy_report", lambda **kwargs: calls.append(kwargs)
    )
    assert roster_commands.cmd_policy(_args(card=False if tty else None)) == 1
    assert calls[0]["validation"] is policy_projection
    assert capsys.readouterr().out == ""


def test_policy_cards_disclose_truncated_errors(policy_projection, capsys):
    policy_projection["errors"] = ["x" * 5000]
    assert roster_commands.cmd_policy(_args(card=True)) == 1
    output = capsys.readouterr().out
    assert "Validation errors truncated; use --json for complete details." in output
    assert "x" * 5000 not in output
    assert "engineering" in output


def test_policy_load_failure_never_becomes_a_healthy_card(monkeypatch, capsys):
    def unavailable(_dependencies):
        raise RuntimeError("fixture policy unavailable")

    monkeypatch.setattr(roster_commands, "_policy_operation", unavailable)
    assert roster_commands.cmd_policy(_args(card=True)) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "fixture policy unavailable" in output.err


@pytest.mark.parametrize("surface", ["roster", "policy", "config-show", "config-get", "providers"])
@pytest.mark.parametrize("card,tty", [(None, True), (True, False), (False, True), (None, False)])
def test_all_five_views_follow_card_tty_and_explicit_overrides(
    surface,
    card,
    tty,
    roster,
    policy_projection,
    config_dependencies,
    configured_providers,
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(_render, "_isatty", lambda: tty)
    arguments = _args(card=card, key="judge.api_key")
    if surface == "roster":
        result = roster_commands.cmd_roster_list(arguments)
    elif surface == "policy":
        result = roster_commands.cmd_policy(arguments)
    elif surface == "config-show":
        result = config_commands.cmd_config_show(arguments, dependencies=config_dependencies)
    elif surface == "config-get":
        result = config_commands.cmd_config_get(arguments, dependencies=config_dependencies)
    else:
        result = config_commands.cmd_config_provider_list(arguments)
    assert result == (1 if surface == "policy" else 0)
    output = capsys.readouterr().out
    assert (_render.divider() in output) is (card is True or (card is None and tty))
    assert "fixture-judge-secret" not in output
    assert "fixture-provider-secret" not in output
    assert "fixture-do-not-display" not in output
