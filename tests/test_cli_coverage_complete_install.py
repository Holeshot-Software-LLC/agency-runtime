"""Behavior coverage for installation and host-control CLI commands."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agency_runtime.cli import install_commands as subject


def args(**changes):
    values = {
        "agent": None,
        "all": False,
        "backup": None,
        "confirm": "",
        "db": None,
        "dry_run": False,
        "execute": False,
        "json": False,
        "native": False,
        "no_dashboard": False,
        "output": None,
        "profile": None,
        "rollback": False,
        "timeout": 5.0,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def config(profile="standard"):
    return SimpleNamespace(
        profile=profile,
        config_path="agency.yaml",
        judge=SimpleNamespace(model="judge-model", base_url="http://127.0.0.1"),
    )


def dependencies(**changes):
    emitted = []
    values = {
        "load_config": lambda: config(),
        "store_factory": lambda _config: object(),
        "emit_json": emitted.append,
        "readiness_probe": lambda: True,
    }
    values.update(changes)
    return subject.InstallDependencies(**values), emitted


def test_install_mode_profile_and_target_validation():
    with pytest.raises(ValueError, match="mutually exclusive"):
        subject._validate_install_mode(args(rollback=True, dry_run=True))
    with pytest.raises(ValueError, match="backup requires"):
        subject._validate_install_mode(args(backup="backup"))
    assert subject._validate_install_mode(args(rollback=True, backup="backup")) == (
        True,
        False,
        "backup",
    )
    with pytest.raises(ValueError, match="does not rewrite runtime policy"):
        subject._resolve_profile_name(args(profile="power"), config())
    assert subject._resolve_profile_name(args(), config()) == "standard"
    assert subject._resolve_install_targets(args(all=True), lambda: ["codex"]) == ["codex"]
    assert subject._resolve_install_targets(args(agent="claude"), lambda: []) == ["claude"]
    assert subject._resolve_install_targets(args(), lambda: ["ignored"]) == []


def test_rollback_validation_json_and_human_rendering(capsys):
    deps, emitted = dependencies()
    with pytest.raises(ValueError, match="exactly one"):
        subject._run_rollback(
            args(),
            backup=None,
            json_mode=False,
            rollback_agent_adapter=lambda *_a, **_kw: {},
            dependencies=deps,
        )
    with pytest.raises(ValueError, match="exactly one"):
        subject._run_rollback(
            args(agent="codex", all=True),
            backup=None,
            json_mode=False,
            rollback_agent_adapter=lambda *_a, **_kw: {},
            dependencies=deps,
        )
    success = {
        "ok": True,
        "restored_from": "backup",
        "maturity": "registered",
        "restart_required": True,
    }
    assert (
        subject._run_rollback(
            args(agent="codex"),
            backup="backup",
            json_mode=False,
            rollback_agent_adapter=lambda *_a, **_kw: success,
            dependencies=deps,
        )
        == 0
    )
    assert "Restart codex" in capsys.readouterr().out
    failure = {"ok": False, "error": "invalid backup", "exit_code": 3}
    assert (
        subject._run_rollback(
            args(agent="codex"),
            backup=None,
            json_mode=True,
            rollback_agent_adapter=lambda *_a, **_kw: failure,
            dependencies=deps,
        )
        == 3
    )
    assert emitted[-1] == failure
    subject._render_rollback_result("codex", failure)
    assert "invalid backup" in capsys.readouterr().out


def test_dashboard_plan_host_plan_and_dry_run_rendering(monkeypatch, capsys):
    assert subject._dashboard_opt_out_result() == {
        "ok": True,
        "exit_code": 0,
        "status": "opted_out",
        "changed": False,
    }
    assert subject._dashboard_opt_out_result(dry_run=True)["dry_run"] is True
    assert (
        subject._plan_dashboard(
            opted_out=True,
            plan_dashboard_service=lambda **_kw: pytest.fail("queried"),
        )["status"]
        == "opted_out"
    )
    monkeypatch.setattr(subject, "resolve_config_path", lambda: "agency.yaml")
    assert (
        subject._plan_dashboard(
            opted_out=False,
            plan_dashboard_service=lambda **kwargs: {"ok": True, **kwargs},
        )["config_path"]
        == "agency.yaml"
    )

    complete = {"ok": True, "executable": "codex"}
    assert subject._host_plans_complete([complete], all_hosts=True)
    assert not subject._host_plans_complete([], all_hosts=True)
    assert not subject._host_plans_complete([{"ok": True, "executable": None}], all_hosts=True)
    assert subject._host_plans_complete([{"ok": True}], all_hosts=False)
    plan = {
        "host": "codex",
        "plugin_path": "plugin",
        "native_lifecycle": "native",
        "host_discovered": True,
        "commands_will_run": True,
        "native_command_plan": [
            {"argv": ["one"], "condition": "if needed"},
            {"argv": ["two"]},
        ],
        "gateway_safety_gate": {"state": "safe", "safe_to_mutate": True},
    }
    subject._render_host_plan(plan)
    subject._render_host_plan({**plan, "gateway_safety_gate": None})
    subject._render_dashboard_plan({}, opted_out=True)
    subject._render_dashboard_plan(
        {"manager": "systemd", "registration_path": "unit", "error": "missing"},
        opted_out=False,
    )
    subject._render_dry_run(
        profile_name="standard",
        targets=[],
        plans=[plan],
        dashboard_plan={"manager": "systemd", "registration_path": "unit"},
        dashboard_opted_out=False,
    )
    output = capsys.readouterr().out
    assert "argv=['one'] [if needed]" in output
    assert "gateway=safe" in output
    assert "opted out" in output
    assert "error=missing" in output
    assert "No host adapters" in output


def test_dry_run_reports_complete_and_incomplete(monkeypatch, capsys):
    monkeypatch.setattr(subject, "resolve_config_path", lambda: "agency.yaml")
    deps, emitted = dependencies()

    def planner(host):
        return {"host": host, "ok": True, "executable": host}

    assert (
        subject._run_dry_run(
            args(all=True),
            profile_name="standard",
            targets=["codex"],
            dashboard_opted_out=False,
            json_mode=True,
            plan_agent_adapter=planner,
            plan_dashboard_service=lambda **_kw: {"ok": True},
            dependencies=deps,
        )
        == 0
    )
    assert emitted[-1]["complete"] is True
    assert (
        subject._run_dry_run(
            args(),
            profile_name="standard",
            targets=[],
            dashboard_opted_out=True,
            json_mode=False,
            plan_agent_adapter=planner,
            plan_dashboard_service=lambda **_kw: {"ok": False},
            dependencies=deps,
        )
        == 0
    )
    assert "DRY RUN" in capsys.readouterr().out
    assert (
        subject._run_dry_run(
            args(all=True),
            profile_name="standard",
            targets=["codex"],
            dashboard_opted_out=False,
            json_mode=True,
            plan_agent_adapter=lambda host: {
                "host": host,
                "ok": True,
                "executable": None,
            },
            plan_dashboard_service=lambda **_kw: {"ok": True},
            dependencies=deps,
        )
        == 1
    )


def test_no_hosts_dashboard_install_and_summary(monkeypatch, capsys):
    deps, emitted = dependencies()
    assert (
        subject._fail_no_detected_hosts(profile_name="standard", json_mode=True, dependencies=deps)
        == 1
    )
    assert emitted[-1]["dashboard"]["status"] == "not_attempted"
    assert (
        subject._fail_no_detected_hosts(profile_name="standard", json_mode=False, dependencies=deps)
        == 1
    )
    assert "No supported" in capsys.readouterr().out

    assert (
        subject._install_dashboard(
            opted_out=True,
            install_dashboard_service=lambda **_kw: pytest.fail("installed"),
            dependencies=deps,
        )["status"]
        == "opted_out"
    )
    monkeypatch.setattr(subject, "resolve_config_path", lambda: "agency.yaml")
    installed = subject._install_dashboard(
        opted_out=False,
        install_dashboard_service=lambda **kwargs: {"ok": True, **kwargs},
        dependencies=deps,
    )
    assert installed["config_path"] == "agency.yaml"
    assert installed["readiness_probe"] is deps.readiness_probe

    for opted_out, result, expected in (
        (True, {"ok": True}, "opted out"),
        (False, {"ok": True}, "installed for the current user"),
        (False, {"ok": False, "error": "denied"}, "denied"),
    ):
        subject._render_install_summary(
            profile_name="standard",
            cfg=config(),
            roster_added=2,
            dashboard_result=result,
            dashboard_opted_out=opted_out,
        )
        assert expected in capsys.readouterr().out


def test_host_completion_install_aggregation_and_seed(capsys, monkeypatch):
    complete = {"ok": True, "status": "registered", "registered": True}
    subject._mark_all_host_completion(complete)
    assert complete["complete"] is True
    incomplete = {"ok": True, "status": "staged", "registered": False}
    subject._mark_all_host_completion(incomplete)
    assert incomplete["complete"] is False and "warning" in incomplete
    results = subject._install_hosts(
        ["codex", "claude"],
        config(),
        all_hosts=True,
        json_mode=False,
        install_agent_adapter=lambda host, _cfg: {
            "host": host,
            "ok": True,
            "status": "registered",
            "registered": True,
        },
    )
    assert all(result["complete"] for result in results)
    assert "codex" in capsys.readouterr().out
    assert subject._report_complete({"ok": True}, results)
    assert not subject._report_complete({"ok": False}, results)
    assert subject._install_succeeded({"ok": True}, [], all_hosts=False)
    assert not subject._install_succeeded({"ok": True}, [], all_hosts=True)
    assert subject._install_succeeded({"ok": True}, results, all_hosts=True)

    class RosterStore:
        def __init__(self):
            self.agents = []
            self.events = []

        def get_active_roster(self):
            return [{"agent_slug": subject.STARTER_ROSTER[0]["slug"]}]

        def activate_agent(self, agent):
            self.agents.append(agent)

        def record_import_event(self, *values):
            self.events.append(values)

    store = RosterStore()
    assert subject._seed_starter_roster(store) == len(subject.STARTER_ROSTER) - 1
    assert store.events[-1][0] == "starter_roster_installed"


def test_install_result_renderer_success_and_partial_failure(capsys):
    subject._print_install_result(
        "codex",
        {
            "ok": True,
            "complete": False,
            "status": "staged",
            "plugin_path": "plugin",
            "maturity": "staged",
            "backup_path": "backup",
            "warning": "manual step",
            "hook_trust_status": "unverified",
            "hook_trust_action": "Run `/hooks`.",
            "restart_required": True,
        },
    )
    subject._print_install_result(
        "claude",
        {
            "ok": False,
            "error": "failed",
            "partial": True,
            "failed_step": "register",
            "backup_path": "backup",
        },
    )
    output = capsys.readouterr().out
    assert "Backup: backup" in output
    assert "Warning: manual step" in output
    assert "Hook trust: unverified" in output
    assert "Action: Run `/hooks`." in output
    assert "Restart codex" in output
    assert "native registration incomplete" in output
    assert "Failed step: register" in output
    assert "Backup retained" in output


@pytest.mark.parametrize(
    ("detected", "expected"),
    [(["codex"], "codex"), ([], None), (["codex", "claude"], None)],
)
def test_control_agent_discovery(monkeypatch, capsys, detected, expected):
    import agency_runtime.core.installer as installer

    monkeypatch.setattr(installer, "detect_installed_agents", lambda: detected)
    assert subject._resolve_control_agent(args(), "on") == expected
    if expected is None:
        assert capsys.readouterr().out
    assert subject._resolve_control_agent(args(agent="hermes"), "off") == "hermes"


def test_host_control_soft_native_json_and_failure(monkeypatch, capsys):
    import agency_runtime.core.host_control as host_control
    import agency_runtime.core.installer as installer

    emitted = []
    deps, _ = dependencies(store_factory=lambda _config: object(), emit_json=emitted.append)
    monkeypatch.setattr(
        host_control,
        "get_runtime_control",
        lambda _store, _agent: {
            "enabled": False,
            "updated_at": "before",
            "source": "default",
        },
    )
    monkeypatch.setattr(
        host_control,
        "set_runtime_control",
        lambda *_a, **_kw: {
            "enabled": True,
            "updated_at": "after",
            "source": "cli",
        },
    )
    assert subject._cmd_host_control(args(agent="codex"), enabled=True, dependencies=deps) == 0
    assert "enabled for codex" in capsys.readouterr().out
    assert (
        subject._cmd_host_control(
            args(agent="codex", dry_run=True), enabled=False, dependencies=deps
        )
        == 0
    )
    assert "DRY RUN" in capsys.readouterr().out
    assert (
        subject._cmd_host_control(args(agent="codex", json=True), enabled=True, dependencies=deps)
        == 0
    )
    assert emitted[-1]["runtime_enabled"] is True

    monkeypatch.setattr(
        installer,
        "toggle_agency",
        lambda *_a, **_kw: {
            "ok": False,
            "error": "native failure",
            "exit_code": 4,
        },
    )
    assert (
        subject._cmd_host_control(
            args(agent="codex", native=True), enabled=False, dependencies=deps
        )
        == 1
    )
    assert "native failure" in capsys.readouterr().out
    assert (
        subject._cmd_host_control(
            args(agent="codex", native=True, json=True),
            enabled=False,
            dependencies=deps,
        )
        == 4
    )


def test_on_off_status_and_canary_wrappers(tmp_path, monkeypatch, capsys):
    import agency_runtime.core.canary as canary
    import agency_runtime.core.host_control as host_control

    calls = []
    monkeypatch.setattr(
        subject,
        "_cmd_host_control",
        lambda _args, *, enabled, dependencies: calls.append(enabled) or 0,
    )
    deps, _emitted = dependencies(emit_json=lambda value: calls.append(value))
    assert subject.cmd_on(args(), dependencies=deps) == 0
    assert subject.cmd_off(args(), dependencies=deps) == 0
    assert calls[:2] == [True, False]

    statuses = [
        {
            "host": "codex",
            "runtime_enabled": True,
            "registered": True,
            "effective_enabled": True,
            "hook_trust_status": "unverified",
            "hook_trust_action": "Run `/hooks`.",
        },
        {
            "host": "claude",
            "runtime_enabled": False,
            "registered": False,
            "effective_enabled": False,
        },
        {"host": "hermes", "runtime_enabled": True, "registered": None, "effective_enabled": None},
    ]
    monkeypatch.setattr(host_control, "inspect_all_host_statuses", lambda _store: statuses)
    monkeypatch.setattr(host_control, "inspect_host_status", lambda _store, _host: statuses[0])
    assert subject.cmd_status(args(), dependencies=deps) == 0
    output = capsys.readouterr().out
    assert "native registered; active" in output
    assert "Hook trust: unverified" in output
    assert "Action: Run `/hooks`." in output
    assert "not registered; inactive" in output
    assert "unverified; unverified" in output
    assert subject.cmd_status(args(agent="codex", json=True), dependencies=deps) == 0
    assert calls[-1]["hosts"] == [statuses[0]]

    report = {"ready": True, "canary_passed": False}
    monkeypatch.setattr(canary, "run_canary", lambda *_a, **_kw: report)
    output_path = tmp_path / "canary.json"
    assert (
        subject.cmd_host_canary(args(agent="codex", output=str(output_path)), dependencies=deps)
        == 0
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert subject.cmd_host_canary(args(agent="codex", execute=True), dependencies=deps) == 1
