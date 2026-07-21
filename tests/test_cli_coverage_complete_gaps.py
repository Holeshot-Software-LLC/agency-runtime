"""Targeted branch tests for the final CLI coverage edges."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agency_runtime.cli import (
    _common,
    config_commands,
    config_wizard,
    delegation_commands,
    install_commands,
    roster_commands,
    service_commands,
)
from agency_runtime.cli import main as cli
from agency_runtime.cli import parser as cli_parser
from agency_runtime.core.delegation import backends as backend_module
from agency_runtime.core.delegation.backend_contracts import BackendError
from agency_runtime.core.detect import ProviderDetection


def test_small_helper_branch_edges(monkeypatch, capsys):
    local = _common.enforce_local_only_config(
        {
            "profile": "local-only",
            "adapters": {"codex": {"preserved": True}},
        }
    )
    assert local["adapters"]["codex"] == {
        "preserved": True,
        "enabled": "false",
    }

    emitted = []
    monkeypatch.setattr(service_commands, "_print_json", emitted.append)
    import agency_runtime.core.dashboard_runtime as runtime
    import agency_runtime.core.dashboard_service as dashboard_service

    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kw: True)
    monkeypatch.setattr(
        dashboard_service,
        "inspect_dashboard_service",
        lambda **_kw: {"ok": True, "status": "running"},
    )
    assert (
        service_commands.cmd_dashboard_service(
            SimpleNamespace(
                dashboard_service_action="status",
                dry_run=False,
                json=False,
                no_open=False,
            )
        )
        == 0
    )
    assert "running" in capsys.readouterr().out


def test_delegate_preserves_nonempty_backend_error_result(monkeypatch):
    run = {"id": "run", "session_id": "", "status": "evidence_only"}

    def record_delegation(**kwargs):
        run["session_id"] = kwargs["session_id"]
        return "event"

    def complete_run(_run_id, status="completed"):
        run["status"] = status

    store = SimpleNamespace(
        record_delegation=record_delegation,
        update_delegation=lambda *_a, **_kw: None,
        get_run=lambda _trace_id: dict(run),
        complete_run=complete_run,
    )
    expected = {
        "backend": "codex",
        "status": "unavailable",
        "exit_code": 11,
        "error": "configured result",
    }

    class Candidate:
        name = "codex"

        def is_available(self):
            return True

        def delegate(self, **_kwargs):
            raise BackendError("outer", result=expected)

    emitted = []
    monkeypatch.setattr(backend_module, "CodexExecBackend", lambda **_kw: Candidate())
    monkeypatch.setattr(delegation_commands, "_store", lambda: store)
    monkeypatch.setattr(delegation_commands, "_print_json", emitted.append)
    args = SimpleNamespace(
        agent=None,
        backend="codex",
        command=None,
        json=True,
        task="task",
        timeout=None,
        workdir=None,
    )
    assert delegation_commands.cmd_delegate(args) == 11
    assert emitted[-1]["error"] == "configured result"


def test_config_and_sync_remaining_paths(monkeypatch, capsys):
    class Lookup:
        plain = object()

    deps = config_commands.ConfigurationDependencies(load_config=lambda: Lookup())
    assert (
        config_commands.cmd_config_get(
            SimpleNamespace(key="plain.extra", raw=False), dependencies=deps
        )
        == 1
    )
    assert "Key not found" in capsys.readouterr().err
    assert (
        config_commands._config_set_notes(
            "profile",
            SimpleNamespace(
                policy_enforced=False,
                restart_required=[],
                state=SimpleNamespace(environment_overrides={}),
            ),
        )
        == []
    )

    monkeypatch.setattr(roster_commands, "download_from_source", lambda _url: [])
    assert (
        roster_commands._collect_sync_candidates([{"url": "empty"}], object(), dry_run=True)[0]
        == []
    )
    assert (
        roster_commands._auto_approve_preflight(
            auto_approve=True, quarantined=["candidate"], errors=[]
        )
        is None
    )
    store = SimpleNamespace(
        list_agent_sources=lambda: [
            {"id": "source", "url": "source", "trusted_for_auto_approve": 1}
        ]
    )
    monkeypatch.setattr(roster_commands, "_store", lambda: store)
    monkeypatch.setattr(
        roster_commands,
        "_collect_sync_candidates",
        lambda *_a, **_kw: (["candidate"], []),
    )
    monkeypatch.setattr(
        roster_commands,
        "resolve_inference_audit_policy",
        lambda _config: SimpleNamespace(required=False),
    )
    completed: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def complete_sync(*args, **kwargs):
        completed.append((args, kwargs))
        return 9

    monkeypatch.setattr(roster_commands, "_complete_sync", complete_sync)
    assert roster_commands.cmd_sync(SimpleNamespace(auto_approve=False, dry_run=False)) == 9
    assert completed[0][0][4] == []
    assert completed[0][1] == {"require_inference": False}


def _wizard_detection(*, provider=None):
    return SimpleNamespace(
        providers=provider or ProviderDetection(),
        adapters=SimpleNamespace(
            hermes=False,
            openclaw=False,
            codex=False,
            claude=False,
        ),
        cli_providers={},
    )


def test_wizard_default_tuning_cli_fallback_and_choice_absence(monkeypatch):
    detected = _wizard_detection(provider=ProviderDetection(litellm_available=False))
    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"judge": {}},
    )
    monkeypatch.setattr(
        config_wizard,
        "_guided_provider_chain",
        lambda *_a, **_kw: [{"name": "codex", "type": "cli", "transport": "codex"}],
    )
    monkeypatch.setattr(config_wizard, "_print_config_summary", lambda _data: None)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    result = config_wizard._interactive_wizard(detected, "standard")
    assert result["judge"]["timeout"] == 15.0
    assert config_wizard._legacy_judge_from_chain([{"type": "cli"}], {"model": "fallback"}) == {
        "model": "",
        "base_url": "",
        "api_key": "",
        "api_key_env": "",
        "ollama_mode": False,
    }

    no_optional = _wizard_detection(
        provider=ProviderDetection(ollama_available=False, litellm_available=False)
    )
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda maximum, **_kw: maximum)
    assert config_wizard._new_provider_entry(no_optional, "standard") is None


def test_guided_chain_empty_none_limit_move_and_empty_remove(monkeypatch, capsys):
    detected = _wizard_detection()
    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": []},
    )
    choices = iter([3, 1, 4])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    monkeypatch.setattr(config_wizard, "_new_provider_entry", lambda *_a, **_kw: {"name": "one"})
    assert config_wizard._guided_provider_chain(detected, "standard") == [{"name": "one"}]
    assert "(empty" in capsys.readouterr().out

    full = [
        {"name": f"provider-{index}"} for index in range(config_wizard.MAX_PROVIDER_CHAIN_ENTRIES)
    ]
    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": full},
    )
    choices = iter([1, 4])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    assert config_wizard._guided_provider_chain(detected, "standard") == full
    assert "at most" in capsys.readouterr().out

    initial = [{"name": "one"}, {"name": "two"}]
    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": initial},
    )
    choices = iter([2, 1, 2, 4])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    assert config_wizard._guided_provider_chain(detected, "standard") == [
        {"name": "two"},
        {"name": "one"},
    ]

    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": [{"name": "one"}]},
    )
    choices = iter([1, 4])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    monkeypatch.setattr(config_wizard, "_new_provider_entry", lambda *_a, **_kw: None)
    assert config_wizard._guided_provider_chain(detected, "standard") == [{"name": "one"}]

    monkeypatch.setattr(
        config_wizard,
        "generate_config_from_detection",
        lambda *_a, **_kw: {"providers": []},
    )
    choices = iter([4, 1, 4])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    monkeypatch.setattr(config_wizard, "_new_provider_entry", lambda *_a, **_kw: {"name": "one"})
    assert config_wizard._guided_provider_chain(detected, "standard") == [{"name": "one"}]


def test_wizard_short_list_selected_and_nondefault_manual_values(monkeypatch):
    proxy = ProviderDetection(litellm_models=["one"], litellm_base_url="http://127.0.0.1:4000")
    monkeypatch.setattr(
        config_wizard,
        "_prompt_provider_auth",
        lambda **_kw: ({"api_key_env": "KEY"}, ""),
    )
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: 1)
    assert config_wizard._pick_litellm_model(proxy)["model"] == "one"
    monkeypatch.setattr("builtins.input", lambda _prompt="": "manual-group")
    assert (
        config_wizard._pick_litellm_model(ProviderDetection(litellm_models=[]))["model"]
        == "manual-group"
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "manual-ollama")
    assert (
        config_wizard._pick_ollama_model(ProviderDetection(ollama_models=[]))["model"]
        == "manual-ollama"
    )
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: 1)
    assert (
        config_wizard._pick_ollama_model(ProviderDetection(ollama_models=["selected-ollama"]))[
            "model"
        ]
        == "selected-ollama"
    )


def test_remote_picker_duplicate_and_nonempty_custom_branches(monkeypatch):
    monkeypatch.setattr(
        config_wizard,
        "_prompt_provider_auth",
        lambda **_kw: ({"api_key_env": "KEY"}, ""),
    )
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: 1)
    duplicate = ProviderDetection(openai_models=["gpt-4o-mini", "gpt-4o-mini"])
    assert config_wizard._pick_openai_model(duplicate)["model"] == "gpt-4o-mini"
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: 16)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "custom-openai")
    many = ProviderDetection(openai_models=[f"remote-{index}" for index in range(16)])
    assert config_wizard._pick_openai_model(many)["model"] == "custom-openai"

    from agency_runtime.core.detect import _ANTHROPIC_SUGGESTIONS

    monkeypatch.setattr(
        config_wizard,
        "_prompt_choice",
        lambda *_a, **_kw: len(_ANTHROPIC_SUGGESTIONS) + 1,
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "custom-anthropic")
    assert config_wizard._pick_anthropic_model()["model"] == "custom-anthropic"


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, _size=-1):
        return self.payload


def test_custom_endpoint_short_list_selection_and_empty_model_data(monkeypatch):
    choices = iter([4, 1])
    monkeypatch.setattr(config_wizard, "_prompt_choice", lambda *_a, **_kw: next(choices))
    monkeypatch.setattr(
        config_wizard,
        "_prompt_provider_auth",
        lambda **_kw: ({"api_key": ""}, ""),
    )
    monkeypatch.setattr(config_wizard, "_models", lambda *_a: ["selected"])
    assert config_wizard._pick_custom_endpoint()["model"] == "selected"
    payload = json.dumps({"data": []}).encode()
    deps = config_wizard.WizardDependencies(open_url=lambda *_a, **_kw: _Response(payload))
    assert config_wizard._fetch_models_custom("http://127.0.0.1:1", dependencies=deps) == []


def _install_args(**changes):
    values = {
        "activation_timeout": 180.0,
        "agent": None,
        "all": False,
        "backup": None,
        "dry_run": False,
        "json": False,
        "no_dashboard": False,
        "profile": None,
        "rollback": False,
        "verify_activation": False,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_cmd_install_all_modes(monkeypatch, capsys):
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer

    emitted = []
    cfg = SimpleNamespace(
        profile="standard",
        config_path="agency.yaml",
        judge=SimpleNamespace(model="model", base_url="http://127.0.0.1"),
    )
    deps = install_commands.InstallDependencies(
        load_config=lambda: cfg,
        store_factory=lambda _cfg: object(),
        emit_json=emitted.append,
        readiness_probe=lambda: True,
        host_inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
        },
        canary_runner=lambda *_args, **_kwargs: {"canary_passed": True},
    )
    monkeypatch.setattr(
        installer,
        "rollback_agent_adapter",
        lambda *_a, **_kw: {"ok": True, "restored_from": "backup"},
    )
    assert (
        install_commands.cmd_install(_install_args(agent="codex", rollback=True), dependencies=deps)
        == 0
    )
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["codex"])
    monkeypatch.setattr(
        installer,
        "plan_agent_adapter",
        lambda host: {"host": host, "ok": True, "executable": host},
    )
    monkeypatch.setattr(dashboard_service, "plan_dashboard_service", lambda **_kw: {"ok": True})
    assert (
        install_commands.cmd_install(
            _install_args(all=True, dry_run=True, json=True), dependencies=deps
        )
        == 0
    )
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: [])
    assert install_commands.cmd_install(_install_args(all=True, json=True), dependencies=deps) == 1
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 1)
    monkeypatch.setattr(
        dashboard_service,
        "install_dashboard_service",
        lambda **_kw: {"ok": True},
    )
    monkeypatch.setattr(
        installer,
        "install_agent_adapter",
        lambda host, _cfg: {
            "ok": True,
            "host": host,
            "status": "registered",
            "registered": True,
        },
    )
    assert install_commands.cmd_install(_install_args(no_dashboard=True), dependencies=deps) == 0
    assert "Run `agency install --all --dry-run`" in capsys.readouterr().out
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["codex"])
    assert install_commands.cmd_install(_install_args(all=True), dependencies=deps) == 0
    assert "Detected 1 agent host" in capsys.readouterr().out
    assert (
        install_commands.cmd_install(_install_args(agent="codex", json=True), dependencies=deps)
        == 0
    )
    assert emitted[-1]["complete"] is True


def test_install_render_nonempty_targets_and_minimal_failure(capsys):
    install_commands._render_dry_run(
        profile_name="standard",
        targets=["codex"],
        plans=[],
        dashboard_plan={},
        dashboard_opted_out=True,
    )
    install_commands._print_install_result("codex", {"ok": False})
    output = capsys.readouterr().out
    assert "No host adapters" not in output
    assert "installation failed" in output


def test_host_control_no_agent_and_restart_message(monkeypatch, capsys):
    monkeypatch.setattr(
        install_commands,
        "_resolve_control_agents",
        lambda *_a, **_kw: ([], False),
    )
    assert install_commands._cmd_host_control(SimpleNamespace(), enabled=True) == 1
    monkeypatch.setattr(
        install_commands,
        "_resolve_control_agents",
        lambda *_a, **_kw: (["codex"], True),
    )
    import agency_runtime.core.installer as installer

    monkeypatch.setattr(
        installer,
        "toggle_agency",
        lambda *_a, **_kw: {
            "ok": True,
            "restart_required": True,
            "native_lifecycle": "native",
        },
    )
    assert (
        install_commands._cmd_host_control(
            SimpleNamespace(native=True, dry_run=False, json=False), enabled=True
        )
        == 0
    )
    assert "Restart codex" in capsys.readouterr().out


def test_facade_remaining_wrappers_parser_and_error_translation(monkeypatch, capsys):
    detected = object()
    monkeypatch.setattr(cli._wizard, "_detect_for_profile", lambda *a, **kw: detected)
    monkeypatch.setattr(cli._wizard, "_interactive_wizard", lambda *a, **kw: {})
    monkeypatch.setattr(cli._wizard, "_guided_provider_chain", lambda *a, **kw: [])
    monkeypatch.setattr(cli._wizard, "_validate_interactive_provider_chain", lambda *a, **kw: True)
    monkeypatch.setattr(cli._wizard, "_pick_custom_endpoint", lambda **kw: {})
    monkeypatch.setattr(cli._wizard, "_fetch_models_custom", lambda *a, **kw: [])
    assert cli._detect_for_profile("standard") is detected
    assert cli._interactive_wizard(detected, "standard") == {}
    assert cli._guided_provider_chain(detected, "standard") == []
    assert cli._validate_interactive_provider_chain([])
    assert cli._pick_custom_endpoint() == {}
    assert cli._fetch_models_custom("http://localhost") == []

    marker = object()
    for module, names in (
        (
            cli._install,
            ("cmd_install", "cmd_on", "cmd_off", "cmd_status"),
        ),
        (
            cli._config,
            ("cmd_configure", "cmd_config_get", "cmd_config_set"),
        ),
    ):
        for name in names:
            monkeypatch.setattr(module, name, lambda *a, **kw: marker)
    request = SimpleNamespace()
    assert cli.cmd_install(request) is marker
    assert cli.cmd_on(request) is marker
    assert cli.cmd_off(request) is marker
    assert cli.cmd_status(request) is marker
    assert cli.cmd_configure(request) is marker
    assert cli.cmd_config_get(request) is marker
    assert cli.cmd_config_set(request) is marker
    monkeypatch.setattr(cli._roster, "cmd_policy", lambda *a, **kw: marker)
    assert cli.cmd_policy(request) is marker

    parser = cli.build_parser()
    assert parser.prog == "agency"
    monkeypatch.setattr(cli, "_configure_console_output", lambda: None)
    monkeypatch.setattr(
        cli,
        "build_parser",
        lambda: SimpleNamespace(parse_args=lambda _argv: SimpleNamespace(func=lambda _args: 7)),
    )
    assert cli.main([]) == 7
    monkeypatch.setattr(
        cli,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda _argv: SimpleNamespace(
                func=lambda _args: (_ for _ in ()).throw(ValueError("invalid"))
            )
        ),
    )
    assert cli.main([]) == 1
    assert "agency: error: invalid" in capsys.readouterr().err


@pytest.mark.parametrize(("value", "expected"), [("1", 1), ("27", 27)])
def test_positive_int_accepts_positive_values(value, expected):
    assert cli_parser._positive_int(value) == expected


@pytest.mark.parametrize("value", ["invalid", "0", "-1"])
def test_positive_int_rejects_invalid_and_nonpositive_values(value):
    with pytest.raises(Exception, match="positive integer"):
        cli_parser._positive_int(value)
