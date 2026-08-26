"""Behavior coverage for installation and host-control CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.cli import install_commands as subject
from agency_runtime.cli import main as cli_main
from agency_runtime.core.config import load_config


def args(**changes):
    values = {
        "agent": None,
        "all": False,
        "autonomous": False,
        "config": None,
        "activation_timeout": 180.0,
        "accepted_outcome": False,
        "backup": None,
        "confirm": "",
        "db": None,
        "dry_run": False,
        "execute": False,
        "json": False,
        "mode": "agency",
        "native": False,
        "no_dashboard": False,
        "output": None,
        "profile": None,
        "profile_scope": "isolated-profile",
        "production_container": False,
        "rollback": False,
        "timeout": 5.0,
        "verify_activation": False,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def config(profile="standard"):
    return SimpleNamespace(
        profile=profile,
        config_path="agency.yaml",
        judge=SimpleNamespace(model="judge-model", base_url="http://127.0.0.1"),
        store=SimpleNamespace(resolved_path=lambda: Path("agency.db")),
    )


def inference_snapshot():
    return {
        "schema_version": "agency.dashboard.inference_operations.v1",
        "configured": False,
        "required_for_eligible_turns": False,
        "state": "not_configured",
        "evidence": "configuration readiness plus recent persisted routing/model receipts",
        "provider_chain": [],
        "latest_model_resolution": None,
        "recent_failures": [],
        "failure_count": 0,
        "failures_truncated": False,
    }


def dependencies(**changes):
    emitted = []
    values = {
        "load_config": lambda *_args: config(),
        "store_factory": lambda _config: object(),
        "emit_json": emitted.append,
        "readiness_probe": lambda: True,
    }
    values.update(changes)
    return subject.InstallDependencies(**values), emitted


@pytest.mark.parametrize("timeout", [0, 601, float("nan")])
def test_verify_activation_rejects_invalid_timeout_before_install(timeout):
    parsed = cli_main.build_parser().parse_args(
        [
            "install",
            "--agent",
            "codex",
            "--verify-activation",
            "--activation-timeout",
            str(timeout),
        ]
    )
    with pytest.raises(ValueError, match="activation-timeout"):
        subject._validate_install_mode(parsed)


@pytest.mark.parametrize(
    "argv",
    [
        ["install", "--agent", "claude", "--verify-activation"],
        ["install", "--all", "--verify-activation"],
        ["install", "--agent", "codex", "--verify-activation", "--profile", "standard"],
        ["install", "--agent", "codex", "--verify-activation", "--no-dashboard"],
    ],
)
def test_verify_activation_requires_the_exact_codex_only_shape(argv):
    parsed = cli_main.build_parser().parse_args(argv)
    with pytest.raises(ValueError, match="exact --agent codex verification-only shape"):
        subject._validate_install_mode(parsed)


def test_autonomous_activation_uses_the_normal_full_install_path() -> None:
    parsed = cli_main.build_parser().parse_args(
        ["install", "--autonomous", "--verify-activation", "--json"]
    )

    assert subject._validate_install_mode(parsed) == (False, False, None)
    assert (
        subject._run_exact_install_special_mode(
            parsed,
            json_mode=True,
            dependencies=dependencies()[0],
        )
        is None
    )


def test_autonomous_mode_requires_activation_and_codex_scope() -> None:
    with pytest.raises(ValueError, match="requires --verify-activation"):
        subject._validate_install_mode(
            cli_main.build_parser().parse_args(["install", "--autonomous"])
        )
    with pytest.raises(ValueError, match="requires Codex or automatic host discovery"):
        subject._validate_install_mode(
            cli_main.build_parser().parse_args(
                ["install", "--agent", "zcode", "--autonomous", "--verify-activation"]
            )
        )


def test_production_container_requires_explicit_config_and_install_lifecycle() -> None:
    with pytest.raises(ValueError, match="requires --config"):
        subject._validate_install_mode(
            cli_main.build_parser().parse_args(
                ["install", "--agent", "codex", "--production-container"]
            )
        )
    parsed = cli_main.build_parser().parse_args(
        [
            "install",
            "--agent",
            "codex",
            "--production-container",
            "--config",
            "container-agency.yaml",
        ]
    )
    assert subject._validate_install_mode(parsed) == (False, False, None)
    with pytest.raises(ValueError, match="cannot be combined"):
        subject._validate_install_mode(
            cli_main.build_parser().parse_args(
                [
                    "install",
                    "--agent",
                    "codex",
                    "--verify-activation",
                    "--config",
                    "container-agency.yaml",
                ]
            )
        )


def test_explicit_install_config_is_loaded_and_identity_bound(tmp_path: Path) -> None:
    config_path = tmp_path / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    observed: list[Path] = []

    def loader(path: Path):
        observed.append(path)
        return SimpleNamespace(config_path=str(path), profile="standard")

    parsed = cli_main.build_parser().parse_args(
        ["install", "--agent", "claude", "--config", str(config_path)]
    )
    loaded = subject._load_install_config(
        parsed,
        subject.InstallDependencies(load_config=loader),
    )
    assert observed == [config_path.resolve()]
    assert loaded.config_path == str(config_path.resolve())


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"config_path": "relative.yaml"}, "config identity"),
        ({"config_revision": "not-a-revision"}, "config revision"),
        ({"store_path": ""}, "active Store identity"),
        ({"environment_overrides": []}, "environment identity"),
        (
            {"environment_overrides": {"store.db_path": "WRONG_VARIABLE"}},
            "Store override",
        ),
    ],
)
def test_broker_store_identity_rejects_malformed_or_mismatched_fields(
    tmp_path,
    monkeypatch,
    change,
    message,
):
    config_path = (tmp_path / "agency.yaml").resolve()
    store_path = (tmp_path / "agency.db").resolve()
    monkeypatch.setattr(subject, "resolve_config_path", lambda: config_path)
    monkeypatch.delenv("AGENCY_DB_PATH", raising=False)
    value = {
        "config_path": str(config_path),
        "config_revision": "sha256:" + ("a" * 64),
        "store_path": str(store_path),
        "desired_store_path": str(store_path),
        "store_restart_required": False,
        "environment_overrides": {},
        **change,
    }

    with pytest.raises(ValueError, match=message):
        subject._broker_store_identity(value)


def test_broker_store_identity_rejects_store_path_different_from_cli_override(
    tmp_path,
    monkeypatch,
):
    config_path = (tmp_path / "agency.yaml").resolve()
    store_path = (tmp_path / "agency.db").resolve()
    override_path = (tmp_path / "override.db").resolve()
    monkeypatch.setattr(subject, "resolve_config_path", lambda: config_path)
    monkeypatch.setenv("AGENCY_DB_PATH", str(override_path))
    value = {
        "config_path": str(config_path),
        "config_revision": "sha256:" + ("a" * 64),
        "store_path": str(store_path),
        "desired_store_path": str(store_path),
        "store_restart_required": False,
        "environment_overrides": {"store.db_path": "AGENCY_DB_PATH"},
    }

    with pytest.raises(ValueError, match="Store path"):
        subject._broker_store_identity(value)


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
    assert subject._resolve_install_targets(args(), lambda: ["codex", "zcode"]) == [
        "codex",
        "zcode",
    ]
    assert subject._require_autonomous_codex_target(args(), ["zcode"]) is False
    with pytest.raises(ValueError, match="requires a selected or detected Codex"):
        subject._require_autonomous_codex_target(args(autonomous=True), ["zcode"])


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
    assert subject._host_plans_complete([], all_hosts=True)
    assert subject._host_plans_complete([{"ok": True, "executable": None}], all_hosts=True)
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
            all_hosts=True,
            dashboard_opted_out=False,
            json_mode=True,
            plan_agent_adapter=planner,
            plan_dashboard_service=lambda **_kw: {"ok": True},
            dependencies=deps,
            cfg=config(),
            config_path=Path("agency.yaml"),
        )
        == 0
    )
    assert emitted[-1]["complete"] is True
    assert (
        subject._run_dry_run(
            args(),
            profile_name="standard",
            targets=[],
            all_hosts=True,
            dashboard_opted_out=True,
            json_mode=False,
            plan_agent_adapter=planner,
            plan_dashboard_service=lambda **_kw: {"ok": False},
            dependencies=deps,
            cfg=config(),
            config_path=Path("agency.yaml"),
        )
        == 0
    )
    assert "DRY RUN" in capsys.readouterr().out
    assert (
        subject._run_dry_run(
            args(all=True),
            profile_name="standard",
            targets=["codex"],
            all_hosts=True,
            dashboard_opted_out=False,
            json_mode=True,
            plan_agent_adapter=lambda host: {
                "host": host,
                "ok": True,
                "executable": None,
            },
            plan_dashboard_service=lambda **_kw: {"ok": True},
            dependencies=deps,
            cfg=config(),
            config_path=Path("agency.yaml"),
        )
        == 0
    )


def test_production_container_dry_run_includes_managed_policy_plan() -> None:
    deps, emitted = dependencies(
        managed_codex_planner=lambda _cfg, **kwargs: {
            "ok": True,
            "complete": True,
            "status": "planned",
            "config_path": str(kwargs["config_path"]),
        }
    )

    assert (
        subject._run_dry_run(
            args(all=True, production_container=True),
            profile_name="standard",
            targets=["codex"],
            all_hosts=True,
            dashboard_opted_out=True,
            json_mode=True,
            plan_agent_adapter=lambda host: {"host": host, "ok": True},
            plan_dashboard_service=lambda **_kwargs: pytest.fail(
                "dashboard planner must honor opt-out"
            ),
            dependencies=deps,
            cfg=config(),
            config_path=Path("container-agency.yaml"),
            production_container=True,
        )
        == 0
    )
    report = emitted[-1]
    assert report["production_container"] is True
    assert report["config_path"] == "container-agency.yaml"
    assert report["host_plans"][0]["managed_policy"]["status"] == "planned"


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
            roster_upgraded=1,
            contractors_installed=1,
            contractors_upgraded=2,
            contractors_existing=3,
            contractors_preserved=4,
            dashboard_result=result,
            dashboard_opted_out=opted_out,
        )
        output = capsys.readouterr().out
        assert expected in output
        assert "1 installed, 2 upgraded, 3 already current, 4 preserved" in output


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
    assert subject._install_succeeded({"ok": True}, [], all_hosts=True)
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


def test_codex_install_requires_current_profile_activation(capsys):
    inspected = {
        "canary": None,
        "canary_attestation_status": "absent",
        "canary_attestation": None,
        "hook_trust_status": "unverified",
    }
    results = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=False,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
        host_inspector=lambda _host: inspected,
        canary_runner=lambda *_args, **_kwargs: pytest.fail("canary should not run"),
    )

    result = results[0]
    assert result["ok"] is True
    assert result["complete"] is False
    assert result["maturity"] == "activation-required"
    assert result["activation"]["verification_command"].endswith("--verify-activation")
    assert result["activation"]["trust_bypass_used"] is False
    assert result["activation"]["approval_surface"] == "codex-terminal-tui"
    assert result["activation"]["approval_launch_command"] == "codex"
    assert result["activation"]["desktop_slash_hooks_is_trust_ui"] is False
    assert "Codex Desktop" in result["activation"]["action"]
    assert subject._install_succeeded({"ok": True}, results, all_hosts=False) is False
    assert "Agency is not active in normal sessions" in capsys.readouterr().out

    assert (
        subject._install_exit_code(
            {"ok": True},
            results,
            residual_drift=None,
            setup_accept_activation_pending=False,
        )
        == 1
    )
    assert (
        subject._install_exit_code(
            {"ok": True},
            results,
            residual_drift=None,
            setup_accept_activation_pending=True,
        )
        == 2
    )


def test_setup_activation_degradation_cannot_mask_other_install_failures() -> None:
    pending_codex = {
        "host": "codex",
        "ok": True,
        "complete": False,
        "status": "registered",
        "registered": True,
        "maturity": "activation-required",
        "activation": {
            "state": "activation_required",
            "complete": False,
            "trust_mode": "attended",
            "trust_bypass_used": False,
            "approval_surface": "codex-terminal-tui",
            "approval_launch_command": "codex",
            "desktop_slash_hooks_is_trust_ui": False,
            "verification_command": "agency install --agent codex --verify-activation",
        },
    }
    staged_host = {
        "host": "hermes",
        "ok": True,
        "complete": False,
        "status": "staged_unverified",
        "registered": False,
        "maturity": "staged-not-registered",
    }
    failed_host = {"host": "claude", "ok": False, "complete": False}
    failed_verification = {
        **pending_codex,
        "activation": {
            **pending_codex["activation"],
            "state": "verification_failed",
        },
    }

    assert (
        subject._install_exit_code(
            {"ok": False},
            [pending_codex],
            residual_drift=None,
            setup_accept_activation_pending=True,
        )
        == 1
    )
    assert (
        subject._install_exit_code(
            {"ok": True},
            [pending_codex, staged_host],
            residual_drift=None,
            setup_accept_activation_pending=True,
        )
        == 1
    )
    assert (
        subject._install_exit_code(
            {"ok": True},
            [pending_codex, failed_host],
            residual_drift=None,
            setup_accept_activation_pending=True,
        )
        == 1
    )
    assert (
        subject._install_exit_code(
            {"ok": True},
            [failed_verification],
            residual_drift=None,
            setup_accept_activation_pending=True,
        )
        == 1
    )
    assert (
        subject._install_exit_code(
            {"ok": True},
            [pending_codex],
            residual_drift={"foreign_package": True},
            setup_accept_activation_pending=True,
        )
        == 1
    )


def test_codex_install_verifies_activation_with_current_profile_canary():
    calls = []

    def canary_runner(*args, **kwargs):
        calls.append((args, kwargs))
        return {"canary_passed": True, "profile_scope": "current-profile"}

    results = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
        verify_activation=True,
        activation_timeout=42,
        host_inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
            "hook_trust_status": "trusted",
        },
        canary_runner=canary_runner,
    )

    result = results[0]
    assert result["complete"] is True
    assert result["maturity"] == "runtime-verified"
    assert result["activation"]["state"] == "ready"
    assert calls == [
        (
            ("codex",),
            {
                "execute": True,
                "confirm": "RUN LIVE codex CURRENT-PROFILE CANARY",
                "timeout": 42,
                "mode": "agency",
                "profile_scope": "current-profile",
            },
        )
    ]


def test_codex_autonomous_install_proves_bypass_without_claiming_trust() -> None:
    calls = []
    verification = {
        "schema_version": "agency.host_canary.v1",
        "profile_scope": "current-profile",
        "trust_mode": "autonomous_bypass",
        "trust_bypass_used": True,
        "live_attempted": True,
        "canary_passed": True,
        "attestation_persisted": False,
        "unmet_prerequisites": [],
    }

    def canary_runner(*args, **kwargs):
        calls.append((args, kwargs))
        return verification

    results = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=True,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
        verify_activation=True,
        activation_timeout=42,
        host_inspector=lambda _host: {"hook_trust_status": "modified"},
        canary_runner=canary_runner,
        autonomous=True,
    )

    result = results[0]
    assert result["complete"] is True
    assert result["hook_trust_status"] == "modified"
    assert result["activation"] == {
        "state": "ready",
        "complete": True,
        "trust_mode": "autonomous_bypass",
        "trust_bypass_used": True,
        "profile_scope": "current-profile",
        "persistent_profile_changed": False,
        "verification": verification,
    }
    assert calls[0] == (
        ("codex",),
        {
            "execute": True,
            "confirm": "RUN LIVE codex CURRENT-PROFILE CANARY",
            "timeout": 42,
            "mode": "agency",
            "profile_scope": "current-profile",
            "trust_mode": "autonomous_bypass",
        },
    )


def test_codex_production_container_installs_managed_policy_and_proves_normal_launch() -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    policies: list[dict[str, object]] = []
    invalidations: list[str] = []
    verification = {
        "schema_version": "agency.host_canary.v1",
        "profile_scope": "current-profile",
        "trust_mode": "managed_policy",
        "trust_bypass_used": False,
        "live_attempted": True,
        "canary_passed": True,
        "attestation_persisted": True,
        "unmet_prerequisites": [],
    }

    def canary_runner(*runner_args, **kwargs):
        calls.append((runner_args, kwargs))
        return verification

    def policy_installer(_cfg, **kwargs):
        policies.append(kwargs)
        return {
            "ok": True,
            "complete": True,
            "changed": True,
            "status": "installed",
            "trust_mode": "managed_policy",
        }

    results = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
            "changed": True,
        },
        activation_timeout=42,
        host_inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
        },
        canary_runner=canary_runner,
        production_container=True,
        config_path=Path("container-agency.yaml"),
        db_path=Path("container-agency.db"),
        managed_codex_installer=policy_installer,
        canary_attestation_invalidator=lambda host: invalidations.append(host) or True,
    )

    result = results[0]
    assert result["complete"] is True
    assert result["hook_trust_status"] == "managed"
    assert result["managed_policy"]["status"] == "installed"
    assert result["managed_policy"]["prior_attestation_invalidated"] is True
    assert result["activation"]["trust_mode"] == "managed_policy"
    assert result["activation"]["trust_bypass_used"] is False
    assert result["activation"]["system_policy_managed"] is True
    assert result["activation"]["persistent_profile_changed"] is True
    assert policies == [{"config_path": Path("container-agency.yaml")}]
    assert invalidations == ["codex"]
    assert calls == [
        (
            ("codex",),
            {
                "execute": True,
                "confirm": "RUN LIVE codex CURRENT-PROFILE CANARY",
                "timeout": 42,
                "mode": "agency",
                "profile_scope": "current-profile",
                "trust_mode": "managed_policy",
                "config_path": Path("container-agency.yaml"),
                "db_path": Path("container-agency.db"),
            },
        )
    ]


def test_codex_production_container_fails_closed_before_canary_on_policy_refusal() -> None:
    result = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
        host_inspector=lambda _host: pytest.fail("canary inspection must not run"),
        canary_runner=lambda *_args, **_kwargs: pytest.fail("canary must not run"),
        production_container=True,
        config_path=Path("container-agency.yaml"),
        managed_codex_installer=lambda *_args, **_kwargs: {
            "ok": False,
            "complete": False,
            "changed": False,
            "status": "refused",
            "error": "foreign requirements.toml",
        },
        canary_attestation_invalidator=lambda _host: False,
    )[0]

    assert result["ok"] is False
    assert result["complete"] is False
    assert result["status"] == "managed_policy_failed"
    assert result["partial"] is True
    assert result["error"] == "foreign requirements.toml"


def test_codex_production_container_invalidates_old_proof_before_policy_mutation() -> None:
    policy_called = False

    def policy_installer(*_args, **_kwargs):
        nonlocal policy_called
        policy_called = True
        return {"ok": True, "complete": True, "changed": True}

    result = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
        production_container=True,
        config_path=Path("container-agency.yaml"),
        managed_codex_installer=policy_installer,
        canary_attestation_invalidator=lambda _host: (_ for _ in ()).throw(
            RuntimeError("private Store failure")
        ),
    )[0]

    assert policy_called is False
    assert result["ok"] is False
    assert result["status"] == "managed_policy_attestation_invalidation_failed"
    assert result["error"] == "prior Codex activation proof could not be invalidated safely"
    assert "private" not in json.dumps(result)


def test_production_container_command_threads_exact_config_through_transaction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import agency_runtime.core.installer as installer

    config_path = tmp_path / "agency.yaml"
    config_path.write_text("profile: standard\n", encoding="utf-8")
    loaded_paths: list[Path] = []
    stored_configs: list[object] = []
    adapter_configs: list[object] = []
    policy_paths: list[Path] = []

    def loader(path: Path):
        loaded_paths.append(path)
        return load_config(path, reload=True)

    class RuntimeStore:
        def clear_host_canary_attestation(self, host: str) -> bool:
            assert host == "codex"
            return False

    def store_factory(cfg):
        stored_configs.append(cfg)
        return RuntimeStore()

    monkeypatch.setattr(subject, "_materialize_install_controls", lambda *_args: None)
    monkeypatch.setattr(subject, "_cli_install_drift_projection", lambda: None)
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)

    def install_adapter(_host, cfg):
        adapter_configs.append(cfg)
        return {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
            "changed": True,
        }

    monkeypatch.setattr(installer, "install_agent_adapter", install_adapter)
    deps, emitted = dependencies(
        load_config=loader,
        store_factory=store_factory,
        host_inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
        },
        canary_runner=lambda *_args, **_kwargs: {
            "schema_version": "agency.host_canary.v1",
            "profile_scope": "current-profile",
            "trust_mode": "managed_policy",
            "trust_bypass_used": False,
            "live_attempted": True,
            "canary_passed": True,
            "attestation_persisted": True,
            "unmet_prerequisites": [],
        },
        managed_codex_installer=lambda _cfg, **kwargs: (
            policy_paths.append(kwargs["config_path"])
            or {
                "ok": True,
                "complete": True,
                "changed": True,
                "status": "installed",
                "trust_mode": "managed_policy",
            }
        ),
    )
    parsed = cli_main.build_parser().parse_args(
        [
            "install",
            "--agent",
            "codex",
            "--production-container",
            "--config",
            str(config_path),
            "--no-dashboard",
            "--json",
        ]
    )

    assert subject.cmd_install(parsed, dependencies=deps) == 0
    resolved = config_path.resolve()
    assert loaded_paths == [resolved]
    assert len(stored_configs) == 1
    assert adapter_configs == stored_configs
    assert policy_paths == [resolved]
    assert emitted[-1]["ok"] is True
    assert emitted[-1]["production_container"] is True
    assert emitted[-1]["config_path"] == str(resolved)
    assert emitted[-1]["dashboard"]["status"] == "opted_out"


def test_codex_autonomous_install_does_not_claim_an_unattempted_bypass() -> None:
    result = {"host": "codex", "ok": True, "registered": True}

    subject._codex_activation_state(
        result,
        verify=True,
        timeout=1,
        inspector=lambda _host: {"hook_trust_status": "modified"},
        canary_runner=lambda *_args, **_kwargs: {
            "schema_version": "agency.host_canary.v1",
            "profile_scope": "current-profile",
            "trust_mode": "autonomous_bypass",
            "trust_bypass_used": False,
            "live_attempted": False,
            "canary_passed": False,
            "attestation_persisted": False,
            "unmet_prerequisites": ["model invocation was not attempted"],
        },
        autonomous=True,
    )

    assert result["complete"] is False
    assert result["activation"]["state"] == "verification_failed"
    assert result["activation"]["trust_mode"] == "autonomous_bypass"
    assert result["activation"]["trust_bypass_used"] is False
    assert result["hook_trust_status"] == "modified"


def test_codex_activation_failure_is_resumable_and_sanitized():
    result = {"host": "codex", "ok": True, "registered": True}

    def unavailable_canary(*_args, **_kwargs):
        raise RuntimeError("private provider detail")

    subject._codex_activation_state(
        result,
        verify=True,
        timeout=1,
        inspector=lambda _host: (_ for _ in ()).throw(RuntimeError("private profile detail")),
        canary_runner=unavailable_canary,
    )

    assert result["complete"] is False
    assert result["activation"]["state"] == "verification_failed"
    assert result["activation"]["verification"]["unmet_prerequisites"] == [
        "current-profile verification could not run safely"
    ]
    assert "private" not in json.dumps(result)


def test_codex_activation_ignores_failed_registration_and_records_failed_proof():
    untouched = {"host": "codex", "ok": False, "registered": False}
    subject._codex_activation_state(
        untouched,
        verify=True,
        timeout=1,
        inspector=lambda _host: pytest.fail("inspection must not run"),
        canary_runner=lambda *_args, **_kwargs: pytest.fail("canary must not run"),
    )
    assert "activation" not in untouched

    pending = {"host": "codex", "ok": True, "registered": True}
    subject._codex_activation_state(
        pending,
        verify=True,
        timeout=1,
        inspector=lambda _host: {
            "canary": None,
            "canary_attestation_status": "absent",
            "canary_attestation": None,
        },
        canary_runner=lambda *_args, **_kwargs: {
            "canary_passed": False,
            "profile_scope": "current-profile",
        },
    )
    assert pending["activation"]["state"] == "verification_failed"


def test_fresh_activation_failure_cannot_reuse_an_older_verified_attestation():
    result = {"host": "codex", "ok": True, "registered": True}
    subject._codex_activation_state(
        result,
        verify=True,
        timeout=1,
        inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
            "hook_trust_status": "trusted",
        },
        canary_runner=lambda *_args, **_kwargs: {
            "canary_passed": False,
            "profile_scope": "current-profile",
            "unmet_prerequisites": ["fresh activation proof failed"],
        },
    )

    assert result["complete"] is False
    assert result["maturity"] == "activation-required"
    assert result["activation"]["state"] == "verification_failed"
    assert result["activation"]["verification"]["canary_passed"] is False


@pytest.mark.parametrize("invalid_result", [None, "not-a-report"])
def test_invalid_fresh_activation_result_cannot_reuse_an_older_verified_attestation(
    invalid_result: object,
):
    result = {"host": "codex", "ok": True, "registered": True}
    subject._codex_activation_state(
        result,
        verify=True,
        timeout=1,
        inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
            "hook_trust_status": "trusted",
        },
        canary_runner=lambda *_args, **_kwargs: invalid_result,
    )

    assert result["complete"] is False
    assert result["maturity"] == "activation-required"
    assert result["activation"]["state"] == "verification_failed"
    assert result["activation"]["verification"]["canary_passed"] is False


def test_codex_activation_accepts_existing_current_profile_attestation_without_new_call():
    result = {"host": "codex", "ok": True, "registered": True}
    subject._codex_activation_state(
        result,
        verify=False,
        timeout=1,
        inspector=lambda _host: {
            "canary": True,
            "canary_attestation_status": "verified",
            "canary_attestation": {"profile_scope": "current-profile"},
        },
        canary_runner=lambda *_args, **_kwargs: pytest.fail("canary must not run"),
    )
    assert result["activation"] == {
        "state": "ready",
        "complete": True,
        "trust_mode": "attended",
        "trust_bypass_used": False,
        "profile_scope": "current-profile",
        "persistent_profile_changed": False,
    }


def test_single_host_install_without_activation_dependencies_preserves_compatibility():
    results = subject._install_hosts(
        ["codex"],
        config(),
        all_hosts=False,
        json_mode=True,
        install_agent_adapter=lambda _host, _cfg: {
            "host": "codex",
            "ok": True,
            "status": "registered",
            "registered": True,
        },
    )
    assert "complete" not in results[0]


def test_install_control_materialization_is_idempotent_and_host_complete(
    monkeypatch,
) -> None:
    master_calls = []
    host_calls = []

    class ControlStore:
        def ensure_host_control_materialized(self, host, *, source):
            host_calls.append((host, source))

    monkeypatch.setattr(
        "agency_runtime.core.runtime_control.ensure_runtime_control_materialized",
        lambda **kwargs: master_calls.append(kwargs),
    )

    subject._materialize_install_controls(
        ControlStore(),
        ["codex", "claude", "codex"],
    )

    assert master_calls == [{"source": "install"}]
    assert host_calls == [("claude", "install"), ("codex", "install")]
    subject._materialize_install_controls(object(), ["codex"])


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
    [
        (["codex"], (["codex"], False)),
        ([], ([], False)),
        (["claude", "codex", "codex"], (["codex", "claude"], False)),
    ],
)
def test_control_agent_discovery(monkeypatch, capsys, detected, expected):
    import agency_runtime.core.installer as installer

    monkeypatch.setattr(installer, "detect_installed_agents", lambda: detected)
    assert subject._resolve_control_agents(args(), "on") == expected
    if not expected[0]:
        assert capsys.readouterr().out
    assert subject._resolve_control_agents(args(agent="hermes"), "off") == (
        ["hermes"],
        True,
    )


def test_omitted_control_agent_applies_every_detected_host_in_canonical_order(
    monkeypatch,
) -> None:
    import agency_runtime.core.host_control as host_control
    import agency_runtime.core.installer as installer

    emitted = []
    transitions = []
    deps, _ = dependencies(store_factory=lambda _config: object(), emit_json=emitted.append)
    monkeypatch.setattr(
        installer,
        "detect_installed_agents",
        lambda: ["claude", "codex", "codex"],
    )
    monkeypatch.setattr(
        host_control,
        "get_runtime_control",
        lambda _store, host: {"enabled": False, "host": host},
    )

    def set_control(_store, host, **kwargs):
        transitions.append((host, kwargs))
        return {"enabled": True, "updated_at": "now", "source": "cli"}

    monkeypatch.setattr(host_control, "set_runtime_control", set_control)

    assert subject._cmd_host_control(args(json=True), enabled=True, dependencies=deps) == 0
    assert [host for host, _kwargs in transitions] == ["codex", "claude"]
    assert all(kwargs["expected_generation"] == 0 for _host, kwargs in transitions)
    assert emitted == [
        {
            "ok": True,
            "complete": True,
            "action": "on",
            "enabled": True,
            "host_count": 2,
            "hosts": [
                {
                    "ok": True,
                    "exit_code": 0,
                    "host": "codex",
                    "enabled": True,
                    "runtime_enabled": True,
                    "previous_runtime_enabled": False,
                    "generation": 0,
                    "previous_generation": 0,
                    "updated_at": "now",
                    "source": "cli",
                    "dry_run": False,
                    "native_lifecycle": "persistent soft control",
                    "restart_required": False,
                },
                {
                    "ok": True,
                    "exit_code": 0,
                    "host": "claude",
                    "enabled": True,
                    "runtime_enabled": True,
                    "previous_runtime_enabled": False,
                    "generation": 0,
                    "previous_generation": 0,
                    "updated_at": "now",
                    "source": "cli",
                    "dry_run": False,
                    "native_lifecycle": "persistent soft control",
                    "restart_required": False,
                },
            ],
            "exit_code": 0,
        }
    ]


def test_omitted_native_control_attempts_all_hosts_and_aggregates_failure(
    monkeypatch,
) -> None:
    import agency_runtime.core.installer as installer

    emitted = []
    calls = []
    deps, _ = dependencies(
        store_factory=lambda _config: (_ for _ in ()).throw(
            AssertionError("native control must not open the soft-control store")
        ),
        emit_json=emitted.append,
    )
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["claude", "codex"])

    def toggle(host, **_kwargs):
        calls.append(host)
        if host == "codex":
            return {"ok": False, "exit_code": 7, "error": "codex failed"}
        return {"ok": True, "exit_code": 0, "native_lifecycle": "native"}

    monkeypatch.setattr(installer, "toggle_agency", toggle)

    assert (
        subject._cmd_host_control(
            args(native=True, json=True),
            enabled=False,
            dependencies=deps,
        )
        == 1
    )
    assert calls == ["codex", "claude"]
    assert emitted[0]["ok"] is False
    assert emitted[0]["exit_code"] == 1
    assert [result["host"] for result in emitted[0]["hosts"]] == ["codex", "claude"]
    assert [result["ok"] for result in emitted[0]["hosts"]] == [False, True]


def test_omitted_control_renders_each_host_and_summary(monkeypatch, capsys) -> None:
    import agency_runtime.core.host_control as host_control
    import agency_runtime.core.installer as installer

    deps, _ = dependencies(store_factory=lambda _config: object())
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["claude", "codex"])
    monkeypatch.setattr(
        host_control,
        "get_runtime_control",
        lambda _store, host: {"enabled": host == "codex"},
    )

    assert (
        subject._cmd_host_control(
            args(dry_run=True),
            enabled=False,
            dependencies=deps,
        )
        == 0
    )
    assert capsys.readouterr().out == (
        "DRY RUN — would disable for codex through persistent soft control\n"
        "DRY RUN — would disable for claude through persistent soft control\n"
        "   Completed 2/2 hosts.\n"
    )


def test_omitted_native_control_text_names_every_partial_result(monkeypatch, capsys) -> None:
    import agency_runtime.core.installer as installer

    deps, _ = dependencies()
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["claude", "codex"])

    def toggle(host, **_kwargs):
        if host == "codex":
            return {"ok": False, "exit_code": 7, "error": "native failure"}
        return {"ok": True, "exit_code": 0, "native_lifecycle": "native"}

    monkeypatch.setattr(installer, "toggle_agency", toggle)

    assert (
        subject._cmd_host_control(
            args(native=True),
            enabled=False,
            dependencies=deps,
        )
        == 1
    )
    assert capsys.readouterr().out == (
        "❌ codex: native failure\n"
        "⏸️  Agency Runtime disabled for claude through native\n"
        "   Completed 1/2 hosts.\n"
    )


def test_omitted_control_with_no_detection_preserves_nonzero_guidance(
    monkeypatch,
    capsys,
) -> None:
    import agency_runtime.core.installer as installer

    deps, _ = dependencies(
        store_factory=lambda _config: (_ for _ in ()).throw(
            AssertionError("no-detection control must not open the store")
        )
    )
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: [])

    assert subject._cmd_host_control(args(), enabled=True, dependencies=deps) == 1
    assert capsys.readouterr().out == ("No agent hosts detected. Use: agency on --agent hermes\n")


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
    monkeypatch.setattr(
        host_control,
        "inspect_all_host_statuses",
        lambda _store, *, global_enabled=None: statuses,
    )
    monkeypatch.setattr(
        host_control,
        "inspect_host_status",
        lambda _store, _host, *, global_enabled=None: statuses[0],
    )
    monkeypatch.setattr(
        subject,
        "_direct_inference_snapshot",
        lambda _store, _dependencies: inference_snapshot(),
    )
    assert subject.cmd_status(args(), dependencies=deps) == 0
    output = capsys.readouterr().out
    assert "native registered; active" in output
    assert "Hook trust: unverified" in output
    assert "Action: Run `/hooks`." in output
    assert "not registered; inactive" in output
    assert "unverified; unverified" in output
    assert subject.cmd_status(args(agent="codex", json=True), dependencies=deps) == 0
    assert calls[-1]["hosts"] == [statuses[0]]
    assert calls[-1]["inference"] == inference_snapshot()

    report = {"ready": True, "canary_passed": False}
    canary_calls = []

    def run_canary(*call_args, **call_kwargs):
        canary_calls.append((call_args, call_kwargs))
        return report

    monkeypatch.setattr(canary, "run_canary", run_canary)
    output_path = tmp_path / "canary.json"
    assert (
        subject.cmd_host_canary(args(agent="codex", output=str(output_path)), dependencies=deps)
        == 0
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert canary_calls[-1][1]["require_existing_store"] is False
    assert subject.cmd_host_canary(args(agent="codex", execute=True), dependencies=deps) == 1
    assert canary_calls[-1][1]["require_existing_store"] is False
    assert (
        subject.cmd_host_canary(
            args(agent="codex", execute=True, profile_scope="current-profile"),
            dependencies=deps,
        )
        == 1
    )
    assert canary_calls[-1][1]["require_existing_store"] is True


def test_host_canary_cli_routes_explicit_accepted_outcome_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import outcome_canary

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    report = {"ready": True, "canary_passed": True}
    monkeypatch.setattr(
        outcome_canary,
        "run_accepted_outcome_canary",
        lambda *call_args, **call_kwargs: calls.append((call_args, call_kwargs)) or report,
    )
    deps, emitted = dependencies()

    assert (
        subject.cmd_host_canary(
            args(
                agent="claude",
                accepted_outcome=True,
                execute=True,
                confirm="RUN LIVE claude ACCEPTED-OUTCOME CANARY",
                timeout=420,
            ),
            dependencies=deps,
        )
        == 0
    )
    assert calls == [
        (
            ("claude",),
            {
                "execute": True,
                "confirm": "RUN LIVE claude ACCEPTED-OUTCOME CANARY",
                "db_path": None,
                "timeout": 420.0,
                "mode": "agency",
                "profile_scope": "isolated-profile",
                "require_existing_store": False,
            },
        )
    ]
    assert emitted == [report]
