"""Installation and host-control commands."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.configuration import resolve_config_path
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.policy.profiles import get_profile
from agency_runtime.core.store.sqlite import Store

from ._common import print_json, store


@dataclass(frozen=True, slots=True)
class InstallDependencies:
    """Patchable process-boundary dependencies for install commands."""

    load_config: Callable[[], AgencyConfig] = load_config
    store_factory: Callable[[AgencyConfig | None], Any] = store
    emit_json: Callable[[Any], None] = print_json
    readiness_probe: Callable[[], bool] | None = None


DEFAULT_DEPENDENCIES = InstallDependencies()


def _validate_install_mode(args: argparse.Namespace) -> tuple[bool, bool, str | None]:
    """Return normalized mode flags after rejecting incompatible options."""
    rollback_mode = bool(getattr(args, "rollback", False))
    dry_run = bool(getattr(args, "dry_run", False))
    backup = getattr(args, "backup", None)
    if rollback_mode and dry_run:
        raise ValueError("install --rollback and --dry-run are mutually exclusive")
    if backup and not rollback_mode:
        raise ValueError("install --backup requires --rollback")
    return rollback_mode, dry_run, backup


def _render_rollback_result(host: str, result: dict[str, Any]) -> None:
    """Render one rollback result without changing its structured truth."""
    if result.get("ok"):
        print(f"✅ {host}: rollback restored {result.get('restored_from')}")
        print(f"   Maturity: {result.get('maturity', 'unknown')}")
        if result.get("restart_required"):
            print(f"   Restart {host} to load the restored integration.")
        return
    print(f"❌ {host}: {result.get('error', 'rollback failed')}")


def _run_rollback(
    args: argparse.Namespace,
    *,
    backup: str | None,
    json_mode: bool,
    rollback_agent_adapter: Callable[..., dict[str, Any]],
    dependencies: InstallDependencies,
) -> int:
    """Execute the single-host rollback mode."""
    if not args.agent or args.all:
        raise ValueError("install --rollback requires exactly one --agent")
    result = rollback_agent_adapter(args.agent, backup_path=backup)
    if json_mode:
        dependencies.emit_json(result)
    else:
        _render_rollback_result(args.agent, result)
    return int(result.get("exit_code", 0 if result.get("ok") else 1))


def _resolve_profile_name(args: argparse.Namespace, cfg: AgencyConfig) -> str:
    """Validate the requested install profile against persisted policy."""
    requested_profile = args.profile or cfg.profile
    if args.profile and args.profile != cfg.profile:
        raise ValueError(
            f"install does not rewrite runtime policy: active profile is {cfg.profile!r}, "
            f"requested {args.profile!r}; run `agency configure --profile {args.profile}` first"
        )
    return get_profile(requested_profile).name


def _resolve_install_targets(
    args: argparse.Namespace,
    detect_installed_agents: Callable[[], list[str]],
) -> list[str]:
    """Resolve explicit or discovered host targets without changing host state."""
    if args.all:
        return detect_installed_agents()
    return [args.agent] if args.agent else []


def _dashboard_opt_out_result(*, dry_run: bool = False) -> dict[str, Any]:
    """Return the stable structured result for an intentional dashboard opt-out."""
    result: dict[str, Any] = {
        "ok": True,
        "exit_code": 0,
        "status": "opted_out",
        "changed": False,
    }
    if dry_run:
        result["dry_run"] = True
    return result


def _plan_dashboard(
    *,
    opted_out: bool,
    plan_dashboard_service: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Plan dashboard lifecycle without querying it after an explicit opt-out."""
    if opted_out:
        return _dashboard_opt_out_result(dry_run=True)
    return plan_dashboard_service(config_path=resolve_config_path())


def _host_plans_complete(
    plans: list[dict[str, Any]],
    *,
    all_hosts: bool,
) -> bool:
    """Apply the stricter executable-evidence rule used by install --all."""
    if all_hosts:
        return bool(plans) and all(plan.get("ok") and plan.get("executable") for plan in plans)
    return all(plan.get("ok") for plan in plans)


def _render_host_plan(plan: dict[str, Any]) -> None:
    """Render one host plan with its native commands and safety gate."""
    print(f"  {plan['host']}: {plan.get('plugin_path')} ({plan.get('native_lifecycle')})")
    print(f"    discovered={plan.get('host_discovered')} commands={plan.get('commands_will_run')}")
    for step in plan.get("native_command_plan", []):
        condition = f" [{step['condition']}]" if step.get("condition") else ""
        print(f"    argv={step.get('argv')}{condition}")
    gate = plan.get("gateway_safety_gate")
    if gate is not None:
        print(f"    gateway={gate.get('state')} safe_to_mutate={gate.get('safe_to_mutate')}")


def _render_dashboard_plan(
    dashboard_plan: dict[str, Any],
    *,
    opted_out: bool,
) -> None:
    """Render dashboard dry-run details."""
    if opted_out:
        print("  dashboard: opted out; no service-manager query or mutation")
        return
    print(
        f"  dashboard: {dashboard_plan.get('manager')} at {dashboard_plan.get('registration_path')}"
    )
    if dashboard_plan.get("error"):
        print(f"    error={dashboard_plan['error']}")


def _render_dry_run(
    *,
    profile_name: str,
    targets: list[str],
    plans: list[dict[str, Any]],
    dashboard_plan: dict[str, Any],
    dashboard_opted_out: bool,
) -> None:
    """Render a mutation-free install preview."""
    print(
        f"DRY RUN — profile={profile_name}; would idempotently seed up to {len(STARTER_ROSTER)} starter agents"
    )
    if not targets:
        print("No host adapters selected or discovered; no files or native state would change.")
    for plan in plans:
        _render_host_plan(plan)
    _render_dashboard_plan(dashboard_plan, opted_out=dashboard_opted_out)


def _run_dry_run(
    args: argparse.Namespace,
    *,
    profile_name: str,
    targets: list[str],
    dashboard_opted_out: bool,
    json_mode: bool,
    plan_agent_adapter: Callable[[str], dict[str, Any]],
    plan_dashboard_service: Callable[..., dict[str, Any]],
    dependencies: InstallDependencies,
) -> int:
    """Build and emit the complete dry-run report."""
    plans = [plan_agent_adapter(host) for host in targets]
    dashboard_plan = _plan_dashboard(
        opted_out=dashboard_opted_out,
        plan_dashboard_service=plan_dashboard_service,
    )
    plan_complete = _host_plans_complete(plans, all_hosts=args.all) and bool(
        dashboard_plan.get("ok")
    )
    report = {
        "ok": plan_complete,
        "complete": plan_complete,
        "dry_run": True,
        "profile": profile_name,
        "starter_roster": {
            "action": "seed_missing_idempotently",
            "candidate_count": len(STARTER_ROSTER),
        },
        "detected_hosts": targets,
        "host_plans": plans,
        "dashboard": dashboard_plan,
    }
    if json_mode:
        dependencies.emit_json(report)
    else:
        _render_dry_run(
            profile_name=profile_name,
            targets=targets,
            plans=plans,
            dashboard_plan=dashboard_plan,
            dashboard_opted_out=dashboard_opted_out,
        )
    return 0 if plan_complete else 1


def _fail_no_detected_hosts(
    *,
    profile_name: str,
    json_mode: bool,
    dependencies: InstallDependencies,
) -> int:
    """Report an empty install --all without mutating local state."""
    dashboard_result = {
        "ok": False,
        "exit_code": 1,
        "status": "not_attempted",
        "changed": False,
        "reason": "no supported hosts detected",
    }
    if json_mode:
        dependencies.emit_json(
            {
                "ok": False,
                "complete": False,
                "profile": profile_name,
                "roster_added": 0,
                "hosts": [],
                "dashboard": dashboard_result,
                "error": "No supported AI agent hosts detected",
            }
        )
    else:
        print("\n⚠️  No supported AI agent hosts detected.")
        print("   Install Hermes, OpenClaw, Codex, or Claude Code first.")
        print("   No roster or dashboard-service state was changed.")
    return 1


def _install_dashboard(
    *,
    opted_out: bool,
    install_dashboard_service: Callable[..., dict[str, Any]],
    dependencies: InstallDependencies,
) -> dict[str, Any]:
    """Install the optional dashboard or return an explicit opt-out result."""
    if opted_out:
        return _dashboard_opt_out_result()
    from agency_runtime.core.dashboard_runtime import dashboard_service_reachable

    return install_dashboard_service(
        config_path=resolve_config_path(),
        reachability_probe=dashboard_service_reachable,
        readiness_probe=dependencies.readiness_probe,
    )


def _render_install_summary(
    *,
    profile_name: str,
    cfg: AgencyConfig,
    roster_added: int,
    dashboard_result: dict[str, Any],
    dashboard_opted_out: bool,
) -> None:
    """Render profile, provider, roster, and dashboard setup results."""
    print(f"✅ Agency Runtime profile: {profile_name}")
    print(f"✅ Starter roster activated: {roster_added} agents")
    print(f"   Config: {cfg.config_path or '(defaults only)'}")
    print(
        f"   Judge model: {safe_display_token(cfg.judge.model)} "
        f"({safe_display_token(cfg.judge.base_url)})"
    )
    if dashboard_opted_out:
        print("   Dashboard service: opted out (--no-dashboard)")
    elif dashboard_result.get("ok"):
        print("✅ Dashboard service: installed for the current user")
        print("   Open it with: agency dashboard service open")
    else:
        print(f"❌ Dashboard service: {dashboard_result.get('error', 'installation failed')}")


def _mark_all_host_completion(result: dict[str, Any]) -> None:
    """Attach the strict native-registration truth required by install --all."""
    result["complete"] = bool(
        result.get("ok")
        and result.get("status") == "registered"
        and result.get("registered") is True
    )
    if not result["complete"]:
        result.setdefault(
            "warning",
            "Detected host did not reach native registration; install --all is incomplete.",
        )


def _install_hosts(
    targets: list[str],
    cfg: AgencyConfig,
    *,
    all_hosts: bool,
    json_mode: bool,
    install_agent_adapter: Callable[[str, AgencyConfig], dict[str, Any]],
) -> list[dict[str, Any]]:
    """Install selected host adapters and preserve partial-failure evidence."""
    results: list[dict[str, Any]] = []
    for host in targets:
        result = install_agent_adapter(host, cfg)
        if all_hosts:
            _mark_all_host_completion(result)
        results.append(result)
        if not json_mode:
            _print_install_result(host, result)
    return results


def _report_complete(
    dashboard_result: dict[str, Any],
    host_results: list[dict[str, Any]],
) -> bool:
    """Aggregate the structured completion truth used by JSON output."""
    return bool(dashboard_result.get("ok")) and all(
        result.get("complete", result.get("ok")) for result in host_results
    )


def _install_succeeded(
    dashboard_result: dict[str, Any],
    host_results: list[dict[str, Any]],
    *,
    all_hosts: bool,
) -> bool:
    """Aggregate command success while enforcing install --all completeness."""
    successful = bool(dashboard_result.get("ok")) and all(
        result.get("ok") for result in host_results
    )
    if not all_hosts:
        return successful
    return (
        bool(host_results) and successful and all(result.get("complete") for result in host_results)
    )


def _seed_starter_roster(store: Store) -> int:
    existing_slugs = {agent.get("agent_slug") for agent in store.get_active_roster()}
    count = 0
    for agent in STARTER_ROSTER:
        if agent["slug"] in existing_slugs:
            continue
        store.activate_agent(dict(agent))
        count += 1
    store.record_import_event("starter_roster_installed", "", f"count={count}")
    return count


def cmd_install(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Install, preview, or roll back host-native Agency Runtime bundles."""
    from agency_runtime.core.dashboard_service import (
        install_dashboard_service,
        plan_dashboard_service,
    )
    from agency_runtime.core.installer import (
        detect_installed_agents,
        install_agent_adapter,
        plan_agent_adapter,
        rollback_agent_adapter,
        seed_starter_roster,
    )

    rollback_mode, dry_run, backup = _validate_install_mode(args)
    cfg = dependencies.load_config()
    json_mode = bool(getattr(args, "json", False))
    if rollback_mode:
        return _run_rollback(
            args,
            backup=backup,
            json_mode=json_mode,
            rollback_agent_adapter=rollback_agent_adapter,
            dependencies=dependencies,
        )

    profile_name = _resolve_profile_name(args, cfg)
    targets = _resolve_install_targets(args, detect_installed_agents)
    dashboard_opted_out = bool(getattr(args, "no_dashboard", False))
    if dry_run:
        return _run_dry_run(
            args,
            profile_name=profile_name,
            targets=targets,
            dashboard_opted_out=dashboard_opted_out,
            json_mode=json_mode,
            plan_agent_adapter=plan_agent_adapter,
            plan_dashboard_service=plan_dashboard_service,
            dependencies=dependencies,
        )

    if args.all and not targets:
        return _fail_no_detected_hosts(
            profile_name=profile_name,
            json_mode=json_mode,
            dependencies=dependencies,
        )

    runtime_store = dependencies.store_factory(cfg)
    count = seed_starter_roster(runtime_store)
    dashboard_result = _install_dashboard(
        opted_out=dashboard_opted_out,
        install_dashboard_service=install_dashboard_service,
        dependencies=dependencies,
    )

    if not json_mode:
        _render_install_summary(
            profile_name=profile_name,
            cfg=cfg,
            roster_added=count,
            dashboard_result=dashboard_result,
            dashboard_opted_out=dashboard_opted_out,
        )
        if args.all:
            print(f"\n🔍 Detected {len(targets)} agent host(s): {', '.join(targets)}")

    host_results = _install_hosts(
        targets,
        cfg,
        all_hosts=args.all,
        json_mode=json_mode,
        install_agent_adapter=install_agent_adapter,
    )

    if not targets and not json_mode:
        print("\n💡 Run `agency install --all --dry-run` to preview discovered host integrations.")
        print("   Run `agency dashboard` to open the local operations dashboard.")
    if json_mode:
        complete = _report_complete(dashboard_result, host_results)
        dependencies.emit_json(
            {
                "ok": complete,
                "complete": complete,
                "profile": profile_name,
                "roster_added": count,
                "hosts": host_results,
                "dashboard": dashboard_result,
            }
        )
    successful = _install_succeeded(
        dashboard_result,
        host_results,
        all_hosts=args.all,
    )
    return 0 if successful else 1


def _print_install_result(host: str, result: dict[str, Any]) -> None:
    """Print native installation maturity without overstating runtime load."""
    if result.get("ok"):
        marker = "✅" if result.get("complete", result.get("status") == "registered") else "⚠️ "
        print(
            f"{marker} {host}: {result.get('status', 'staged')} → {result.get('plugin_path', 'unknown path')}"
        )
        print(f"   Maturity: {result.get('maturity', 'unknown')}")
        if result.get("backup_path"):
            print(f"   Backup: {result['backup_path']}")
        if result.get("warning"):
            print(f"   Warning: {result['warning']}")
        if result.get("hook_trust_action"):
            print(f"   Hook trust: {result.get('hook_trust_status', 'unverified')}")
            print(f"   Action: {result['hook_trust_action']}")
        if result.get("restart_required"):
            print(f"   Restart {host} to activate the native state.")
        return
    partial = (
        " (filesystem staged; native registration incomplete)" if result.get("partial") else ""
    )
    print(f"❌ {host}: {result.get('error', 'installation failed')}{partial}")
    if result.get("failed_step"):
        print(f"   Failed step: {result['failed_step']}")
    if result.get("backup_path"):
        print(f"   Backup retained: {result['backup_path']}")


def _resolve_control_agent(args: argparse.Namespace, action: str) -> str | None:
    """Resolve an explicit or unambiguous installed host for a control action."""
    from agency_runtime.core.installer import detect_installed_agents

    agent = getattr(args, "agent", None)
    if not agent:
        detected = detect_installed_agents()
        if len(detected) == 1:
            agent = detected[0]
        elif len(detected) == 0:
            print(f"No agent hosts detected. Use: agency {action} --agent hermes")
            return None
        else:
            print(f"Multiple hosts detected: {', '.join(detected)}")
            print(f"Specify: agency {action} --agent <name>")
            return None
    return str(agent)


def _cmd_host_control(
    args: argparse.Namespace,
    *,
    enabled: bool,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Apply persistent soft control, or explicitly request native lifecycle."""
    action = "on" if enabled else "off"
    agent = _resolve_control_agent(args, action)
    if agent is None:
        return 1
    dry_run = bool(getattr(args, "dry_run", False))
    if bool(getattr(args, "native", False)):
        from agency_runtime.core.installer import toggle_agency

        result = toggle_agency(agent, enabled=enabled, dry_run=dry_run)
    else:
        from agency_runtime.core.host_control import (
            get_runtime_control,
            set_runtime_control,
        )

        runtime_store = dependencies.store_factory(None)
        previous = get_runtime_control(runtime_store, agent)
        control = (
            previous
            if dry_run
            else set_runtime_control(
                runtime_store,
                agent,
                enabled=enabled,
                source="cli",
            )
        )
        result = {
            "ok": True,
            "exit_code": 0,
            "host": agent,
            "enabled": enabled,
            "runtime_enabled": enabled if dry_run else bool(control["enabled"]),
            "previous_runtime_enabled": bool(previous["enabled"]),
            "updated_at": control.get("updated_at"),
            "source": control.get("source"),
            "dry_run": dry_run,
            "native_lifecycle": "persistent soft control",
            "restart_required": False,
        }
    if getattr(args, "json", False):
        dependencies.emit_json(result)
        return int(result.get("exit_code", 0 if result.get("ok") else 1))
    if result["ok"]:
        prefix = (
            f"DRY RUN — would {'enable' if enabled else 'disable'}"
            if result.get("dry_run")
            else ("✅ Agency Runtime enabled" if enabled else "⏸️  Agency Runtime disabled")
        )
        print(
            f"{prefix} for {agent} through {result.get('native_lifecycle', 'its native plugin lifecycle')}"
        )
        if result.get("restart_required"):
            print(f"   Restart {agent} to take effect.")
    else:
        print(f"❌ {result['error']}")
    return 0 if result["ok"] else 1


def cmd_on(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Enable Agency Runtime for a specific agent host."""
    return _cmd_host_control(args, enabled=True, dependencies=dependencies)


def cmd_off(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Disable Agency Runtime for a specific agent host."""
    return _cmd_host_control(args, enabled=False, dependencies=dependencies)


def cmd_status(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Report native installation facts and persistent runtime control."""
    from agency_runtime.core.host_control import (
        inspect_all_host_statuses,
        inspect_host_status,
    )

    runtime_store = dependencies.store_factory(None)
    statuses = (
        [inspect_host_status(runtime_store, args.agent)]
        if args.agent
        else inspect_all_host_statuses(runtime_store)
    )
    payload = {"hosts": statuses}
    if getattr(args, "json", False):
        dependencies.emit_json(payload)
        return 0
    for status in statuses:
        runtime = "on" if status["runtime_enabled"] else "off"
        native = (
            "registered"
            if status.get("registered") is True
            else "not registered"
            if status.get("registered") is False
            else "unverified"
        )
        effective_value = status.get("effective_enabled")
        effective = (
            "active"
            if effective_value is True
            else "inactive"
            if effective_value is False
            else "unverified"
        )
        print(f"{status['host']}: runtime {runtime}; native {native}; {effective}")
        if status.get("hook_trust_action"):
            print(f"  Hook trust: {status.get('hook_trust_status', 'unverified')}")
            print(f"  Action: {status['hook_trust_action']}")
    return 0


def cmd_host_canary(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Inspect readiness or run an explicitly confirmed live host canary."""
    from agency_runtime.core.canary import run_canary

    report = run_canary(
        args.agent,
        execute=bool(args.execute),
        confirm=str(args.confirm or ""),
        db_path=args.db,
        timeout=float(args.timeout),
    )
    if args.output:
        Path(args.output).expanduser().write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    dependencies.emit_json(report)
    return 0 if (report["canary_passed"] if args.execute else report["ready"]) else 1
