"""Installation and host-control commands."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import atomic_write_text
from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.configuration import resolve_config_path
from agency_runtime.core.dashboard_service_core import dashboard_service_environment_overrides
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
    CODEX_HOOK_TRUST_ACTION,
    CODEX_HOOK_TRUST_COMMAND,
    CODEX_HOOK_TRUST_SURFACE,
)
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
    canary_runner: Callable[..., dict[str, Any]] | None = None
    host_inspector: Callable[[str], dict[str, Any]] | None = None
    prepared_codex_installer: Callable[[AgencyConfig], dict[str, Any]] | None = None


DEFAULT_DEPENDENCIES = InstallDependencies()


@dataclass(frozen=True, slots=True)
class _BrokerStoreIdentity:
    config_path: str
    config_revision: str
    store_path: str
    environment_overrides: tuple[tuple[str, str], ...]


def _same_absolute_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _broker_store_identity(value: Mapping[str, Any]) -> _BrokerStoreIdentity:
    """Validate one dashboard Store identity against this CLI environment."""

    config_path = value.get("config_path")
    revision = value.get("config_revision")
    store_path = value.get("store_path")
    desired_path = value.get("desired_store_path")
    overrides = value.get("environment_overrides")
    if (
        not isinstance(config_path, str)
        or not config_path
        or len(config_path.encode("utf-8")) > 4096
        or not Path(config_path).is_absolute()
        or not _same_absolute_path(config_path, resolve_config_path())
    ):
        raise ValueError("dashboard host response config identity does not match the CLI")
    if (
        not isinstance(revision, str)
        or not revision.startswith("sha256:")
        or len(revision) != 71
        or any(character not in "0123456789abcdef" for character in revision[7:])
    ):
        raise ValueError("dashboard host response has invalid config revision")
    if (
        not isinstance(store_path, str)
        or not isinstance(desired_path, str)
        or not store_path
        or not desired_path
        or len(store_path.encode("utf-8")) > 4096
        or len(desired_path.encode("utf-8")) > 4096
        or not Path(store_path).is_absolute()
        or not Path(desired_path).is_absolute()
        or not _same_absolute_path(store_path, desired_path)
        or value.get("store_restart_required") is not False
    ):
        raise ValueError("dashboard host response has invalid active Store identity")
    if (
        not isinstance(overrides, Mapping)
        or len(overrides) > 64
        or any(
            not isinstance(path, str)
            or not isinstance(variable, str)
            or not path
            or not variable
            or len(path.encode("utf-8")) > 256
            or len(variable.encode("utf-8")) > 256
            for path, variable in overrides.items()
        )
    ):
        raise ValueError("dashboard host response has invalid environment identity")
    service_db_override = overrides.get("store.db_path")
    local_db_override = os.environ.get("AGENCY_DB_PATH", "").strip()
    if bool(service_db_override) is not bool(local_db_override) or (
        service_db_override and service_db_override != "AGENCY_DB_PATH"
    ):
        raise ValueError("dashboard host response Store override does not match the CLI")
    if local_db_override and not _same_absolute_path(
        store_path,
        Path(local_db_override).expanduser(),
    ):
        raise ValueError("dashboard host response Store path does not match the CLI override")
    return _BrokerStoreIdentity(
        config_path=config_path,
        config_revision=revision,
        store_path=store_path,
        environment_overrides=tuple(sorted(overrides.items())),
    )


def _validate_install_mode(args: argparse.Namespace) -> tuple[bool, bool, str | None]:
    """Return normalized mode flags after rejecting incompatible options."""
    rollback_mode = bool(getattr(args, "rollback", False))
    dry_run = bool(getattr(args, "dry_run", False))
    backup = getattr(args, "backup", None)
    verify_activation = bool(getattr(args, "verify_activation", False))
    autonomous = bool(getattr(args, "autonomous", False))
    if rollback_mode and dry_run:
        raise ValueError("install --rollback and --dry-run are mutually exclusive")
    if backup is not None and not rollback_mode:
        raise ValueError("install --backup requires --rollback")
    if autonomous and not verify_activation:
        raise ValueError("install --autonomous requires --verify-activation")
    if verify_activation:
        if rollback_mode or dry_run or backup is not None:
            raise ValueError(
                "install --verify-activation cannot be combined with install or rollback modes"
            )
        if autonomous:
            if getattr(args, "agent", None) not in {None, "codex"}:
                raise ValueError(
                    "install --autonomous --verify-activation requires Codex or automatic host "
                    "discovery"
                )
        elif (
            getattr(args, "agent", None) != "codex"
            or bool(getattr(args, "all", False))
            or getattr(args, "profile", None) is not None
            or bool(getattr(args, "no_dashboard", False))
        ):
            raise ValueError(
                "install --verify-activation requires the exact --agent codex verification-only "
                "shape"
            )
        activation_timeout = float(getattr(args, "activation_timeout", 180.0))
        if not math.isfinite(activation_timeout) or not 0 < activation_timeout <= 600:
            raise ValueError("install --activation-timeout must be greater than 0 and at most 600")
        from agency_runtime.core.codex_activation_verification import (
            is_exact_codex_activation_verification,
        )

        if not autonomous and not is_exact_codex_activation_verification(args):
            raise ValueError("install --verify-activation shape is invalid")
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
    """Resolve one explicit host or auto-discover every installed host by default."""
    if args.all or not args.agent:
        return detect_installed_agents()
    return [args.agent]


def _require_autonomous_codex_target(
    args: argparse.Namespace,
    targets: list[str],
) -> bool:
    """Return autonomous mode after proving that Codex is in its exact scope."""

    autonomous = bool(getattr(args, "autonomous", False))
    if autonomous and "codex" not in targets:
        raise ValueError(
            "install --autonomous --verify-activation requires a selected or detected Codex host"
        )
    return autonomous


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
    """Require every selected native plan to be valid, including config-native hosts."""
    del all_hosts
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
    all_hosts: bool,
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
    plan_complete = _host_plans_complete(plans, all_hosts=all_hosts) and bool(
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
                "roster_upgraded": 0,
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
    roster_upgraded: int,
    dashboard_result: dict[str, Any],
    dashboard_opted_out: bool,
    contractors_installed: int = 0,
    contractors_upgraded: int = 0,
    contractors_existing: int = 0,
    contractors_preserved: int = 0,
) -> None:
    """Render profile, provider, roster, and dashboard setup results."""
    print(f"✅ Agency Runtime profile: {profile_name}")
    print(f"✅ Starter roster added: {roster_added} agents")
    print(f"✅ Legacy bundled contracts upgraded: {roster_upgraded} agents")
    print(
        "✅ Governed contractors: "
        f"{contractors_installed} installed, {contractors_upgraded} upgraded, "
        f"{contractors_existing} already current, {contractors_preserved} preserved"
    )
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


def _codex_activation_required(
    *,
    trust_mode: str = "attended",
    trust_bypass_used: bool = False,
) -> dict[str, Any]:
    """Return the resumable, user-approved activation contract for Codex."""

    if trust_mode == "autonomous_bypass":
        return {
            "state": "activation_required",
            "complete": False,
            "trust_mode": "autonomous_bypass",
            "trust_bypass_used": trust_bypass_used,
            "persistent_profile_changed": False,
            "approval_surface": None,
            "approval_launch_command": None,
            "desktop_slash_hooks_is_trust_ui": False,
            "action": (
                "Autonomous bypass activation was not proven; inspect the named failure stage. "
                "No persistent Codex trust state was changed."
            ),
            "verification_command": "agency install --autonomous --verify-activation --json",
        }
    return {
        "state": "activation_required",
        "complete": False,
        "trust_mode": "attended",
        "trust_bypass_used": False,
        "approval_surface": CODEX_HOOK_TRUST_SURFACE,
        "approval_launch_command": CODEX_HOOK_TRUST_COMMAND,
        "desktop_slash_hooks_is_trust_ui": False,
        "action": CODEX_HOOK_TRUST_ACTION,
        "verification_command": "agency install --agent codex --verify-activation",
    }


def _codex_activation_state(
    result: dict[str, Any],
    *,
    verify: bool,
    timeout: float,
    inspector: Callable[[str], dict[str, Any]],
    canary_runner: Callable[..., dict[str, Any]],
    autonomous: bool = False,
) -> None:
    """Attach current-profile readiness without mutating Codex trust state."""

    if not result.get("ok") or result.get("registered") is not True:
        return
    verification: dict[str, Any] | None = None
    trust_mode = "autonomous_bypass" if autonomous else "attended"
    if verify:
        try:
            canary_kwargs: dict[str, Any] = {
                "execute": True,
                "confirm": "RUN LIVE codex CURRENT-PROFILE CANARY",
                "timeout": timeout,
                "mode": "agency",
                "profile_scope": "current-profile",
            }
            if autonomous:
                canary_kwargs["trust_mode"] = trust_mode
            candidate = canary_runner("codex", **canary_kwargs)
            verification = (
                dict(candidate)
                if isinstance(candidate, Mapping)
                else {
                    "canary_passed": False,
                    "profile_scope": "current-profile",
                    "unmet_prerequisites": [
                        "current-profile verification returned an invalid result"
                    ],
                }
            )
        except Exception:
            verification = {
                "canary_passed": False,
                "profile_scope": "current-profile",
                "unmet_prerequisites": ["current-profile verification could not run safely"],
            }
    try:
        inspected = inspector("codex")
    except Exception:
        inspected = {}
    attestation = inspected.get("canary_attestation")
    if autonomous:
        ready = bool(
            verify
            and isinstance(verification, Mapping)
            and verification.get("schema_version") == "agency.host_canary.v1"
            and verification.get("profile_scope") == "current-profile"
            and verification.get("trust_mode") == trust_mode
            and verification.get("trust_bypass_used") is True
            and verification.get("live_attempted") is True
            and verification.get("canary_passed") is True
            and verification.get("attestation_persisted") is False
            and verification.get("unmet_prerequisites") == []
        )
    else:
        latest_verification_passed = not verify or bool(
            isinstance(verification, Mapping) and verification.get("canary_passed") is True
        )
        ready = bool(
            latest_verification_passed
            and inspected.get("canary") is True
            and inspected.get("canary_attestation_status") == "verified"
            and isinstance(attestation, Mapping)
            and attestation.get("profile_scope") == "current-profile"
        )
    if ready:
        hook_trust_status = (
            inspected.get("hook_trust_status") or "unverified" if autonomous else "trusted"
        )
        result.update(
            {
                "complete": True,
                "maturity": "runtime-verified",
                "canary": True,
                "hook_trust_status": hook_trust_status,
                "hook_trust_action": None,
                "activation": {
                    "state": "ready",
                    "complete": True,
                    "trust_mode": trust_mode,
                    "trust_bypass_used": autonomous,
                    "profile_scope": "current-profile",
                    "persistent_profile_changed": False,
                },
            }
        )
        if verification is not None:
            result["activation"]["verification"] = verification
        return
    activation = _codex_activation_required(
        trust_mode=trust_mode,
        trust_bypass_used=bool(
            isinstance(verification, Mapping) and verification.get("trust_bypass_used") is True
        ),
    )
    if verification is not None:
        activation["state"] = "verification_failed"
        activation["verification"] = verification
    result.update(
        {
            "complete": False,
            "maturity": "activation-required",
            "canary": False,
            "hook_trust_status": inspected.get("hook_trust_status") or "unverified",
            "hook_trust_action": activation["action"],
            "activation": activation,
            "warning": (
                "Codex files are installed, but bypass-mode activation was not proven."
                if autonomous
                else "Codex files are installed, but Agency is not active in normal sessions."
            ),
        }
    )


def _install_hosts(
    targets: list[str],
    cfg: AgencyConfig,
    *,
    all_hosts: bool,
    json_mode: bool,
    install_agent_adapter: Callable[[str, AgencyConfig], dict[str, Any]],
    verify_activation: bool = False,
    activation_timeout: float = 180.0,
    host_inspector: Callable[[str], dict[str, Any]] | None = None,
    canary_runner: Callable[..., dict[str, Any]] | None = None,
    autonomous: bool = False,
) -> list[dict[str, Any]]:
    """Install selected host adapters and preserve partial-failure evidence."""
    results: list[dict[str, Any]] = []
    for host in targets:
        try:
            result = install_agent_adapter(host, cfg)
        except Exception as exc:
            result = {
                "ok": False,
                "complete": False,
                "exit_code": 1,
                "host": host,
                "status": "failed_before_commit",
                "changed": False,
                "error": f"{type(exc).__name__}: {safe_display_token(str(exc), limit=500)}",
            }
        if host == "codex" and host_inspector is not None and canary_runner is not None:
            _codex_activation_state(
                result,
                verify=verify_activation,
                timeout=activation_timeout,
                inspector=host_inspector,
                canary_runner=canary_runner,
                autonomous=autonomous,
            )
        elif all_hosts:
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
    if not host_results:
        return successful
    return successful and all(result.get("complete", result.get("ok")) for result in host_results)


def _setup_activation_pending_only(
    dashboard_result: Mapping[str, Any],
    host_results: list[dict[str, Any]],
) -> bool:
    """Recognize the one incomplete state setup may continue as degraded."""

    if dashboard_result.get("ok") is not True or not host_results:
        return False
    pending: list[Mapping[str, Any]] = []
    for result in host_results:
        if result.get("ok") is not True:
            return False
        if result.get("complete", result.get("ok")) is True:
            continue
        pending.append(result)
    if len(pending) != 1:
        return False

    result = pending[0]
    activation = result.get("activation")
    return bool(
        result.get("host") == "codex"
        and result.get("status") == "registered"
        and result.get("registered") is True
        and result.get("maturity") == "activation-required"
        and isinstance(activation, Mapping)
        and activation.get("state") == "activation_required"
        and activation.get("complete") is False
        and activation.get("trust_mode") == "attended"
        and activation.get("trust_bypass_used") is False
        and activation.get("approval_surface") == CODEX_HOOK_TRUST_SURFACE
        and activation.get("approval_launch_command") == CODEX_HOOK_TRUST_COMMAND
        and activation.get("desktop_slash_hooks_is_trust_ui") is False
        and activation.get("verification_command")
        == "agency install --agent codex --verify-activation"
    )


def _install_exit_code(
    dashboard_result: dict[str, Any],
    host_results: list[dict[str, Any]],
    *,
    residual_drift: dict[str, Any] | None,
    setup_accept_activation_pending: bool,
    all_hosts: bool = False,
) -> int:
    """Reduce install evidence without weakening standalone completion."""

    if _install_succeeded(dashboard_result, host_results, all_hosts=all_hosts):
        return 0
    if (
        setup_accept_activation_pending
        and residual_drift is None
        and _setup_activation_pending_only(dashboard_result, host_results)
    ):
        return 2
    return 1


def _seed_starter_roster(store: Store) -> int:
    from agency_runtime.core.installer import seed_starter_roster

    result = seed_starter_roster(store)
    store.record_import_event("starter_roster_installed", "", f"count={int(result)}")
    if result.upgraded:
        store.record_import_event(
            "starter_roster_upgraded",
            "",
            f"count={result.upgraded}",
        )
    if result.contractors_installed:
        store.record_import_event(
            "packaged_contractors_installed",
            "",
            f"count={result.contractors_installed}",
        )
    if result.contractors_upgraded:
        store.record_import_event(
            "packaged_contractors_upgraded",
            "",
            f"count={result.contractors_upgraded}",
        )
    if result.contractors_preserved:
        store.record_import_event(
            "packaged_contractors_preserved",
            "",
            f"count={result.contractors_preserved}",
        )
    return result


def _materialize_install_controls(store: object, hosts: list[str]) -> None:
    """Create durable enabled defaults before installing persistent host bindings."""

    ensure_host = getattr(store, "ensure_host_control_materialized", None)
    if not callable(ensure_host):
        return
    from agency_runtime.core.runtime_control import ensure_runtime_control_materialized

    ensure_runtime_control_materialized(source="install")
    for host in sorted(set(hosts)):
        ensure_host(host, source="install")


def _run_prepared_codex_refresh(
    *,
    json_mode: bool,
    dependencies: InstallDependencies,
) -> int:
    """Run the exact Codex-only prepared refresh without touching other state."""

    from agency_runtime.core.prepared_codex_install import refresh_existing_codex_adapter

    installer = dependencies.prepared_codex_installer or refresh_existing_codex_adapter
    cfg: AgencyConfig | None = None
    try:
        cfg = dependencies.load_config()
        host_result = installer(cfg)
    except Exception as exc:
        host_result = {
            "ok": False,
            "complete": False,
            "host": "codex",
            "status": "failed_before_commit",
            "maturity": "activation-required",
            "partial": False,
            "manual_recovery_required": False,
            "state_preserved": True,
            "transaction_complete": False,
            "activation_complete": False,
            "activation_required": True,
            "error": (f"{type(exc).__name__}: " + safe_display_token(str(exc), limit=500)),
            "loaded": None,
            "canary": None,
            "hook_trust_status": "unverified",
        }
    dashboard_result = _dashboard_opt_out_result()
    complete = bool(host_result.get("ok") and host_result.get("complete"))
    report = {
        "ok": complete,
        "complete": complete,
        "transaction_complete": complete,
        "activation_complete": bool(host_result.get("activation_complete", False)),
        "activation_required": bool(host_result.get("activation_required", True)),
        "profile": cfg.profile if cfg is not None else None,
        "roster_added": 0,
        "roster_upgraded": 0,
        "contractors_installed": 0,
        "contractors_existing": 0,
        "roster_action": "unchanged_prepared_codex_refresh",
        "hosts": [host_result],
        "dashboard": dashboard_result,
    }
    if json_mode:
        dependencies.emit_json(report)
    else:
        if complete:
            print("✅ Codex adapter refresh transaction completed")
        else:
            print("❌ Codex adapter refresh did not complete")
        _print_install_result("codex", host_result)
        if complete:
            print("   Activation: unverified; restart Codex and run the live host canary.")
    return 0 if complete else 1


_ACTIVATION_IDENTITY_FIELDS = (
    "host_version",
    "install_id",
    "bundle_digest",
    "managed_plugin_version",
)
_ACTIVATION_ATTESTATION_FIELDS = (
    "host",
    "proof_contract",
    "proof_digest",
    "profile_scope",
    "platform_system",
    "platform_release",
    "platform_machine",
    "host_version",
    "plugin_version",
    "install_id",
    "bundle_digest",
    "trace_id",
    "passed_at",
)


def _bounded_utf8_text(value: object, *, limit: int) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        return None
    return value if size <= limit else None


def _codex_activation_identity(value: object) -> dict[str, str] | None:
    """Return a bounded identity only for an exact active managed Codex install."""

    if not isinstance(value, Mapping) or value.get("host") != "codex":
        return None
    for field in (
        "current_native_root",
        "enabled",
        "executable_discovered",
        "launcher_artifacts_current",
        "marketplace_registered",
        "registered",
        "staged",
    ):
        if value.get(field) is not True:
            return None
    identity: dict[str, str] = {}
    for field in _ACTIVATION_IDENTITY_FIELDS:
        item = _bounded_utf8_text(value.get(field), limit=512)
        if item is None:
            return None
        identity[field] = item
    return identity


def _bounded_unmet_prerequisites(value: object) -> list[str]:
    if value == []:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return ["fresh current-profile verification returned an invalid result"]
    return ["fresh current-profile canary reported unmet prerequisites"]


def _activation_verification_now() -> datetime:
    """Return an aware wall-clock sample for fresh-proof binding."""

    return datetime.now(timezone.utc)


def _parse_activation_timestamp(value: object) -> datetime | None:
    bounded = _bounded_utf8_text(value, limit=64)
    if bounded is None:
        return None
    try:
        parsed = datetime.fromisoformat(bounded)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _fresh_activation_attestation(
    value: object,
    *,
    expected_identity: Mapping[str, str],
    not_before: datetime,
    not_after: datetime,
    prior_attestation: object,
) -> dict[str, str] | None:
    """Bind success to this invocation's exact current-profile attestation."""

    if not isinstance(value, Mapping):
        return None
    if (
        value.get("schema_version") != "agency.host_canary.v1"
        or value.get("host") != "codex"
        or value.get("mode") != "agency"
        or value.get("profile_scope") != "current-profile"
        or value.get("live_attempted") is not True
        or value.get("canary_passed") is not True
        or value.get("attestation_persisted") is not True
        or value.get("unmet_prerequisites") != []
    ):
        return None
    candidate = value.get("attestation")
    if not isinstance(candidate, Mapping):
        return None
    sampled_at = value.get("sampled_at")
    sampled_timestamp = _parse_activation_timestamp(sampled_at)
    if (
        sampled_timestamp is None
        or sampled_timestamp < not_before.astimezone(timezone.utc)
        or sampled_timestamp > not_after.astimezone(timezone.utc)
    ):
        return None
    attestation: dict[str, str] = {}
    for field in _ACTIVATION_ATTESTATION_FIELDS:
        item = _bounded_utf8_text(candidate.get(field), limit=512)
        if item is None:
            return None
        attestation[field] = item
    if (
        attestation["host"] != "codex"
        or attestation["proof_contract"] != CODEX_ACTIVATION_CANARY_PROOF_CONTRACT
        or len(attestation["proof_digest"]) != 64
        or any(character not in "0123456789abcdef" for character in attestation["proof_digest"])
        or attestation["profile_scope"] != "current-profile"
        or attestation["host_version"] != expected_identity["host_version"]
        or attestation["plugin_version"] != expected_identity["managed_plugin_version"]
        or attestation["install_id"] != expected_identity["install_id"]
        or attestation["bundle_digest"] != expected_identity["bundle_digest"]
        or attestation["passed_at"] != sampled_at
    ):
        return None
    if isinstance(prior_attestation, Mapping) and any(
        isinstance(prior_attestation.get(field), str)
        and prior_attestation.get(field) == attestation[field]
        for field in ("proof_digest", "trace_id")
    ):
        return None
    return attestation


def _final_activation_matches(
    value: object,
    *,
    expected_identity: Mapping[str, str],
    fresh_attestation: Mapping[str, str],
) -> bool:
    """Require the final inventory to expose this invocation's exact proof."""

    identity = _codex_activation_identity(value)
    if identity != dict(expected_identity) or not isinstance(value, Mapping):
        return False
    final_attestation = value.get("canary_attestation")
    return bool(
        value.get("canary") is True
        and value.get("canary_attestation_status") == "verified"
        and value.get("hook_trust_status") == "trusted"
        and isinstance(final_attestation, Mapping)
        and all(
            final_attestation.get(field) == fresh_attestation[field]
            for field in _ACTIVATION_ATTESTATION_FIELDS
        )
    )


def _activation_verification_projection(value: object) -> dict[str, Any]:
    """Expose only bounded, non-content canary outcome fields."""

    if not isinstance(value, Mapping):
        return {
            "schema_version": None,
            "host": "codex",
            "mode": "agency",
            "profile_scope": "current-profile",
            "live_attempted": False,
            "canary_passed": False,
            "attestation_persisted": False,
            "unmet_prerequisites": [
                "fresh current-profile verification returned an invalid result"
            ],
        }
    projected = {
        "schema_version": (
            "agency.host_canary.v1"
            if value.get("schema_version") == "agency.host_canary.v1"
            else None
        ),
        "host": "codex" if value.get("host") == "codex" else None,
        "mode": "agency" if value.get("mode") == "agency" else None,
        "profile_scope": (
            "current-profile" if value.get("profile_scope") == "current-profile" else None
        ),
        "live_attempted": value.get("live_attempted") is True,
        "canary_passed": value.get("canary_passed") is True,
        "attestation_persisted": value.get("attestation_persisted") is True,
        "unmet_prerequisites": _bounded_unmet_prerequisites(value.get("unmet_prerequisites")),
    }
    invocation = value.get("invocation")
    if isinstance(invocation, Mapping):
        from agency_runtime.core.canary_proof import CANARY_INVOCATION_FAILURE_REASONS
        from agency_runtime.core.codex_hook_trust import (
            sanitize_codex_hook_trust_report,
        )

        invocation_projection: dict[str, Any] = {}
        failure_reason = invocation.get("failure_reason")
        if isinstance(failure_reason, str) and failure_reason in CANARY_INVOCATION_FAILURE_REASONS:
            invocation_projection["failure_reason"] = failure_reason
        if type(invocation.get("model_invocation_attempted")) is bool:
            invocation_projection["model_invocation_attempted"] = invocation[
                "model_invocation_attempted"
            ]
        if isinstance(invocation.get("hook_trust"), Mapping):
            invocation_projection["hook_trust"] = sanitize_codex_hook_trust_report(
                invocation["hook_trust"]
            )
        if invocation_projection:
            projected["invocation"] = invocation_projection
    return projected


def _activation_verification_result(
    *,
    complete: bool,
    verification: Mapping[str, Any],
    identity: Mapping[str, str] | None,
    reason: str | None,
    fresh_attestation: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return one truthful, bounded verification-only host result."""

    activation: dict[str, Any]
    if complete:
        activation = {
            "state": "ready",
            "complete": True,
            "trust_bypass_used": False,
            "profile_scope": "current-profile",
            "verification": dict(verification),
        }
    else:
        activation = _codex_activation_required()
        activation.update(state="verification_failed", verification=dict(verification))
        invocation = verification.get("invocation")
        hook_trust = invocation.get("hook_trust") if isinstance(invocation, Mapping) else None
        if isinstance(hook_trust, Mapping):
            from agency_runtime.core.installer_contracts import codex_hook_trust_action

            # Trusted-but-disabled hooks never show a startup trust review;
            # match the remediation to the observed per-hook state instead of
            # sending the operator to a ceremony that will not appear.
            activation["action"] = codex_hook_trust_action(hook_trust.get("status"))
    if fresh_attestation is not None:
        activation["fresh_attestation"] = dict(fresh_attestation)
    result: dict[str, Any] = {
        "ok": complete,
        "complete": complete,
        "host": "codex",
        "status": "runtime_verified" if complete else "activation_verification_failed",
        "maturity": "runtime-verified" if complete else "activation-required",
        "verification_only": True,
        "installation_attempted": False,
        "installation_changed": False,
        "hook_trust_action": None if complete else activation["action"],
        "activation": activation,
    }
    if identity is not None:
        result["installation_identity"] = dict(identity)
    if reason:
        result["error"] = reason
    return result


def _render_activation_verification(host_result: Mapping[str, Any]) -> None:
    """Render activation-only truth without implying an installation attempt."""

    if host_result.get("complete") is True:
        print("✅ Codex current-profile activation verified")
        return
    print("❌ Codex current-profile activation was not verified")
    error = host_result.get("error")
    if error:
        print(f"   {safe_display_token(str(error), limit=500)}")
    activation = host_result.get("activation")
    if not isinstance(activation, Mapping):
        return
    verification = activation.get("verification")
    if isinstance(verification, Mapping):
        unmet = verification.get("unmet_prerequisites")
        if isinstance(unmet, list):
            for item in unmet[:8]:
                print(f"   Unmet: {safe_display_token(str(item), limit=500)}")
        invocation = verification.get("invocation")
        if isinstance(invocation, Mapping):
            failure_reason = invocation.get("failure_reason")
            if failure_reason:
                print(f"   Cause: {safe_display_token(str(failure_reason), limit=200)}")
            hook_trust = invocation.get("hook_trust")
            if isinstance(hook_trust, Mapping):
                summary = (
                    f"status={hook_trust.get('status')}"
                    f" observed={hook_trust.get('observed_count')}"
                    f" trusted={hook_trust.get('trusted_count')}"
                    f" disabled={hook_trust.get('disabled_count')}"
                    f" untrusted={hook_trust.get('untrusted_count')}"
                    f" missing={hook_trust.get('missing_count')}"
                )
                if hook_trust.get("error"):
                    summary += f" error={hook_trust.get('error')}"
                print(f"   Hook trust: {safe_display_token(summary, limit=300)}")
    action = activation.get("action")
    if action:
        print(f"   Action: {safe_display_token(str(action), limit=1000)}")


def _run_codex_activation_verification(
    *,
    json_mode: bool,
    timeout: float,
    dependencies: InstallDependencies,
) -> int:
    """Verify an existing Codex adapter without entering generic install work."""

    from agency_runtime.core.canary import run_canary
    from agency_runtime.core.installer import inspect_host_installation

    inspector = dependencies.host_inspector or inspect_host_installation
    canary_runner = dependencies.canary_runner or run_canary
    try:
        initial = inspector("codex")
    except Exception:
        initial = None
    identity = _codex_activation_identity(initial)
    if identity is None:
        host_result = _activation_verification_result(
            complete=False,
            verification=_activation_verification_projection(None),
            identity=None,
            reason=(
                "an existing, current, registered, enabled Codex installation could not be "
                "proven; no activation canary was attempted"
            ),
        )
    else:
        prior_attestation = (
            initial.get("canary_attestation") if isinstance(initial, Mapping) else None
        )
        verification_started_at = _activation_verification_now()
        try:
            candidate = canary_runner(
                "codex",
                execute=True,
                confirm="RUN LIVE codex CURRENT-PROFILE CANARY",
                timeout=timeout,
                mode="agency",
                profile_scope="current-profile",
                require_existing_store=True,
            )
        except Exception:
            candidate = None
        verification_completed_at = _activation_verification_now()
        try:
            final = inspector("codex")
        except Exception:
            final = None
        fresh_attestation = _fresh_activation_attestation(
            candidate,
            expected_identity=identity,
            not_before=verification_started_at,
            not_after=verification_completed_at,
            prior_attestation=prior_attestation,
        )
        complete = bool(
            fresh_attestation is not None
            and _final_activation_matches(
                final,
                expected_identity=identity,
                fresh_attestation=fresh_attestation,
            )
        )
        reason = None
        if fresh_attestation is None:
            reason = "the fresh current-profile canary did not produce a complete bound attestation"
        elif not complete:
            reason = "final Codex inspection did not expose the fresh bound attestation"
        host_result = _activation_verification_result(
            complete=complete,
            verification=_activation_verification_projection(candidate),
            identity=identity,
            reason=reason,
            fresh_attestation=fresh_attestation,
        )

    complete = host_result.get("complete") is True
    report = {
        "ok": complete,
        "complete": complete,
        "verification_only": True,
        "installation_attempted": False,
        "profile_scope": "current-profile",
        "allowed_effects": [
            "one bounded Codex canary invocation",
            "nonce-correlated runtime evidence",
            "activation-attestation replacement",
        ],
        "untouched": [
            "configuration",
            "runtime and host controls",
            "roster and workforce governance",
            "dashboard service",
            "Codex adapter and trust store",
        ],
        "roster_added": 0,
        "roster_upgraded": 0,
        "contractors_installed": 0,
        "contractors_existing": 0,
        "roster_action": "unchanged_activation_verification",
        "hosts": [host_result],
        "dashboard": {
            "ok": None,
            "exit_code": None,
            "attempted": False,
            "status": "not_applicable_activation_verification",
            "changed": False,
        },
    }
    if json_mode:
        dependencies.emit_json(report)
    else:
        _render_activation_verification(host_result)
    return 0 if complete else 1


def _run_exact_install_special_mode(
    args: argparse.Namespace,
    *,
    json_mode: bool,
    dependencies: InstallDependencies,
) -> int | None:
    """Dispatch the two exact install-parser modes before generic install work."""

    if bool(getattr(args, "verify_activation", False)) and not bool(
        getattr(args, "autonomous", False)
    ):
        return _run_codex_activation_verification(
            json_mode=json_mode,
            timeout=float(getattr(args, "activation_timeout", 180.0)),
            dependencies=dependencies,
        )
    from agency_runtime.core.prepared_codex_install import is_exact_prepared_codex_install

    if is_exact_prepared_codex_install(args):
        return _run_prepared_codex_refresh(
            json_mode=json_mode,
            dependencies=dependencies,
        )
    return None


def _restricted_install_failure(
    exc: Exception,
    *,
    message: str,
    profile_name: str,
    roster_counts: int | None,
    json_mode: bool,
    dependencies: InstallDependencies,
) -> int:
    """Report a restricted-token install failure that mutated no native host.

    Both call sites in ``cmd_install`` reported this identically; the only
    difference is whether roster counts are known (``0``) or indeterminate
    (``None`` after a partial seed). ``require_restricted_windows_token``
    re-raises anything that is not a restricted-token failure, so this stays a
    narrow report rather than a general exception sink.
    """

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    require_restricted_windows_token(exc)
    error = safe_display_token(message, limit=500)
    result = {
        "ok": False,
        "complete": False,
        "profile": profile_name,
        "roster_added": roster_counts,
        "roster_upgraded": roster_counts,
        "hosts": [],
        "dashboard": None,
        "error": error,
    }
    if json_mode:
        dependencies.emit_json(result)
    else:
        print(f"❌ {error}")
    return 1


def _operator_policy_refusal(
    cfg: AgencyConfig,
    *,
    json_mode: bool,
    dependencies: InstallDependencies,
) -> int | None:
    """Refuse to install against house rules that will never be applied.

    Nobody need be watching for this to be the right place. Install is where the
    operator's decision is expressed -- the config templated into the image -- and
    its exit code is what a provisioning step reads. Refusing here turns a silently
    dropped guardrail into a container that fails to provision, which an
    orchestrator can see. Every later read stays lenient on purpose: a running
    container must not stop answering over a typo in a string.

    Strict where the config is chosen, lenient where it is merely read. The failure
    an operator can act on is the one at provisioning time, not the one buried in a
    running fleet.
    """

    if not cfg.operator_policy_error:
        return None
    message = f"operator_policy cannot be applied: {cfg.operator_policy_error}"
    if json_mode:
        dependencies.emit_json({"status": "error", "error": message, "exit_code": 2})
    else:
        print(f"Install refused: {message}")
    return 2


def cmd_install(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Install, preview, or roll back host-native Agency Runtime bundles."""
    rollback_mode, dry_run, backup = _validate_install_mode(args)
    json_mode = bool(getattr(args, "json", False))
    special_result = _run_exact_install_special_mode(
        args,
        json_mode=json_mode,
        dependencies=dependencies,
    )
    if special_result is not None:
        return special_result
    cfg = dependencies.load_config()
    refusal = _operator_policy_refusal(cfg, json_mode=json_mode, dependencies=dependencies)
    if refusal is not None:
        return refusal
    from agency_runtime.core.canary import run_canary
    from agency_runtime.core.dashboard_service import (
        install_dashboard_service,
        plan_dashboard_service,
    )
    from agency_runtime.core.installer import (
        detect_installed_agents,
        inspect_host_installation,
        install_agent_adapter,
        plan_agent_adapter,
        rollback_agent_adapter,
        seed_starter_roster,
    )

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
    autonomous = _require_autonomous_codex_target(args, targets)
    all_hosts = args.agent is None
    dashboard_opted_out = bool(getattr(args, "no_dashboard", False))
    if dry_run:
        return _run_dry_run(
            args,
            profile_name=profile_name,
            targets=targets,
            all_hosts=all_hosts,
            dashboard_opted_out=dashboard_opted_out,
            json_mode=json_mode,
            plan_agent_adapter=plan_agent_adapter,
            plan_dashboard_service=plan_dashboard_service,
            dependencies=dependencies,
        )

    dashboard_preflight: dict[str, Any] | None = None
    if not dashboard_opted_out and dashboard_service_environment_overrides(cfg):
        dashboard_preflight = plan_dashboard_service(config_path=resolve_config_path())

    try:
        runtime_store = dependencies.store_factory(cfg)
    except Exception as exc:
        return _restricted_install_failure(
            exc,
            message=(
                "starter roster Store is unavailable from this restricted process; no dashboard "
                "service or native host mutation was attempted"
            ),
            profile_name=profile_name,
            roster_counts=0,
            json_mode=json_mode,
            dependencies=dependencies,
        )
    try:
        _materialize_install_controls(runtime_store, targets)
        roster_added = seed_starter_roster(runtime_store)
        roster_upgraded = int(getattr(roster_added, "upgraded", 0))
        contractors_installed = int(getattr(roster_added, "contractors_installed", 0))
        contractors_upgraded = int(getattr(roster_added, "contractors_upgraded", 0))
        contractors_existing = int(getattr(roster_added, "contractors_existing", 0))
        contractors_preserved = int(getattr(roster_added, "contractors_preserved", 0))
    except Exception as exc:
        return _restricted_install_failure(
            exc,
            message=(
                "starter roster initialization was interrupted by the restricted process token; "
                "roster changes may be partial, but no dashboard service or native host mutation "
                "was attempted"
            ),
            profile_name=profile_name,
            roster_counts=None,
            json_mode=json_mode,
            dependencies=dependencies,
        )
    host_results = _install_hosts(
        targets,
        cfg,
        all_hosts=all_hosts,
        json_mode=json_mode,
        install_agent_adapter=install_agent_adapter,
        verify_activation=bool(getattr(args, "verify_activation", False)),
        activation_timeout=float(getattr(args, "activation_timeout", 180.0)),
        host_inspector=dependencies.host_inspector or inspect_host_installation,
        canary_runner=dependencies.canary_runner or run_canary,
        autonomous=autonomous,
    )

    if dashboard_preflight is not None:
        dashboard_result = dashboard_preflight
    else:
        try:
            dashboard_result = _install_dashboard(
                opted_out=dashboard_opted_out,
                install_dashboard_service=install_dashboard_service,
                dependencies=dependencies,
            )
        except Exception as exc:
            dashboard_result = {
                "ok": False,
                "complete": False,
                "exit_code": 1,
                "status": "failed_before_commit",
                "changed": False,
                "error": f"{type(exc).__name__}: {safe_display_token(str(exc), limit=500)}",
            }

    # Checked after the hosts are staged: a completed install should have
    # published this CLI's projection, so surviving drift means the install
    # reported success without actually publishing anything. A foreign-package
    # report cannot survive an install from this package, so it would mean the
    # pointer was not rewritten -- still worth reporting, not filtered out.
    residual_drift = _cli_install_drift_projection()
    if not json_mode:
        _render_install_summary(
            profile_name=profile_name,
            cfg=cfg,
            roster_added=int(roster_added),
            roster_upgraded=roster_upgraded,
            contractors_installed=contractors_installed,
            contractors_upgraded=contractors_upgraded,
            contractors_existing=contractors_existing,
            contractors_preserved=contractors_preserved,
            dashboard_result=dashboard_result,
            dashboard_opted_out=dashboard_opted_out,
        )
        if residual_drift is not None:
            print(
                "\n⚠️  Install finished but the published projection still differs from "
                "this CLI; your hooks did not pick up this source."
            )
            print(f"   {residual_drift['message']}")
            print(f"   This CLI runs from: {residual_drift['package_root']}")
        if all_hosts:
            detected = ", ".join(targets) if targets else "none"
            print(f"\n🔍 Auto-detected {len(targets)} agent host(s): {detected}")

    if not targets and not json_mode:
        print("\n💡 No supported host harnesses were detected; other requested components ran.")
        print("   Run `agency dashboard` to open the local operations dashboard.")
    if json_mode:
        complete = _report_complete(dashboard_result, host_results)
        dependencies.emit_json(
            {
                "ok": complete,
                "complete": complete,
                "profile": profile_name,
                "roster_added": int(roster_added),
                "roster_upgraded": roster_upgraded,
                "contractors_installed": contractors_installed,
                "contractors_upgraded": contractors_upgraded,
                "contractors_existing": contractors_existing,
                "contractors_preserved": contractors_preserved,
                "selected_hosts": "all_detected" if all_hosts else "explicit",
                "hosts": host_results,
                "dashboard": dashboard_result,
                "runtime_drift": residual_drift,
                "partial": not complete
                and bool(
                    dashboard_result.get("ok") or any(item.get("ok") for item in host_results)
                ),
            }
        )
    return _install_exit_code(
        dashboard_result,
        host_results,
        residual_drift=residual_drift,
        setup_accept_activation_pending=bool(
            getattr(args, "_setup_accept_activation_pending", False)
        ),
        all_hosts=all_hosts,
    )


def _cli_install_drift_projection() -> dict[str, Any] | None:
    """Project CLI-side install drift without letting a report break a command.

    Reporting drift is advisory: a status or install run that cannot compute
    the comparison must still deliver everything else it was asked for.
    """

    reports = _cli_install_drift_projections()
    return reports[0] if reports else None


def _cli_install_drift_projections() -> list[dict[str, Any]]:
    """Project every host's install drift, newest-installed last.

    One entry per stale host: a single report cannot describe a box where one
    host is current and another is behind, and collapsing them is what let a
    current Codex install be reported as stale under Claude's digest.
    """

    try:
        from agency_runtime.core.runtime_staleness import cli_install_drift_reports

        reports = cli_install_drift_reports()
    except Exception:
        return []
    return [
        {
            "source_digest": drift.source_digest,
            "installed_digest": drift.installed_digest,
            "package_root": drift.package_root,
            "installed_source_root": drift.installed_source_root,
            "foreign_package": drift.foreign_package,
            "host": drift.host,
            "message": drift.message,
        }
        for drift in reports
    ]


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
    if result.get("status"):
        print(f"   Status: {result['status']}")
    _print_install_recovery(result)


def _print_install_recovery(result: Mapping[str, Any]) -> None:
    """Render recovery state without inferring it from a generic failure."""

    compensation = result.get("compensation")
    if isinstance(compensation, Mapping):
        if compensation.get("manual_recovery_required"):
            print("   Manual recovery: required")
        if compensation.get("error"):
            print(f"   Recovery error: {compensation['error']}")
        if compensation.get("displaced_path"):
            print(f"   Displaced target: {compensation['displaced_path']}")
        if compensation.get("stage_path"):
            print(f"   Retained stage: {compensation['stage_path']}")
    elif result.get("manual_recovery_required"):
        print("   Manual recovery: required")
    elif result.get("state_preserved"):
        print("   State: no incomplete mutation was retained")


def _resolve_control_agents(args: argparse.Namespace, action: str) -> tuple[list[str], bool]:
    """Resolve an explicit host or every detected host in canonical order."""
    from agency_runtime.core.host_control import SUPPORTED_HOSTS
    from agency_runtime.core.installer import detect_installed_agents

    agent = getattr(args, "agent", None)
    if agent:
        return [str(agent)], True
    detected = {
        str(host).strip().lower() for host in detect_installed_agents() if str(host).strip()
    }
    if not detected:
        print(f"No agent hosts detected. Use: agency {action} --agent hermes")
        return [], False
    ordered = [host for host in SUPPORTED_HOSTS if host in detected]
    ordered.extend(sorted(detected.difference(SUPPORTED_HOSTS)))
    return ordered, False


def _soft_control_result(
    runtime_store: Any,
    agent: str,
    *,
    enabled: bool,
    dry_run: bool,
) -> dict[str, Any]:
    """Apply or preview one persistent soft-control transition."""
    from agency_runtime.core.host_control import (
        get_runtime_control,
        set_runtime_control,
    )

    previous = get_runtime_control(runtime_store, agent)
    previous_generation = int(previous.get("generation", 0))
    control = (
        previous
        if dry_run
        else set_runtime_control(
            runtime_store,
            agent,
            enabled=enabled,
            source="cli",
            expected_generation=previous_generation,
        )
    )
    return {
        "ok": True,
        "exit_code": 0,
        "host": agent,
        "enabled": enabled,
        "runtime_enabled": enabled if dry_run else bool(control["enabled"]),
        "previous_runtime_enabled": bool(previous["enabled"]),
        "generation": int(control.get("generation", previous_generation)),
        "previous_generation": previous_generation,
        "updated_at": control.get("updated_at"),
        "source": control.get("source"),
        "dry_run": dry_run,
        "native_lifecycle": "persistent soft control",
        "restart_required": False,
    }


def _broker_generation(value: Mapping[str, Any], field: str) -> int:
    """Return one strict non-boolean host-control generation."""

    generation = value.get(field)
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise ValueError(f"dashboard host response has invalid {field}")
    return generation


def _broker_host_status(value: Any, *, expected_host: str) -> dict[str, Any]:
    """Validate the control-bearing portion of one dashboard host projection."""

    from agency_runtime.core.host_control import SUPPORTED_HOSTS

    if not isinstance(value, Mapping):
        raise ValueError("dashboard host status must be a JSON object")
    host = value.get("host")
    if not isinstance(host, str) or host not in SUPPORTED_HOSTS or host != expected_host:
        raise ValueError("dashboard host status identity is invalid")
    runtime_enabled = value.get("runtime_enabled")
    master_enabled = value.get("master_enabled")
    effective_enabled = value.get("effective_enabled")
    if not isinstance(runtime_enabled, bool) or not isinstance(master_enabled, bool):
        raise ValueError("dashboard host status controls must be JSON booleans")
    if effective_enabled is not None and not isinstance(effective_enabled, bool):
        raise ValueError("dashboard effective host status must be boolean or null")
    if effective_enabled is True and (not runtime_enabled or not master_enabled):
        raise ValueError("dashboard effective host status is internally inconsistent")
    _broker_generation(value, "runtime_control_generation")
    return dict(value)


def _dashboard_host_snapshot_with_identity(
    agent: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], _BrokerStoreIdentity]:
    """Read and validate one complete authenticated host-control snapshot."""

    from agency_runtime.core.dashboard_runtime import dashboard_api_request
    from agency_runtime.core.host_control import SUPPORTED_HOSTS, normalize_host
    from agency_runtime.core.runtime_control import validate_runtime_control_document

    response = dashboard_api_request("/api/hosts")
    identity = _broker_store_identity(response)
    raw_hosts = response.get("hosts")
    if not isinstance(raw_hosts, list) or len(raw_hosts) != len(SUPPORTED_HOSTS):
        raise ValueError("dashboard host response must contain every supported host exactly once")
    by_host: dict[str, dict[str, Any]] = {}
    for raw in raw_hosts:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("host"), str):
            raise ValueError("dashboard host response contains an invalid entry")
        host = str(raw["host"])
        if host in by_host:
            raise ValueError("dashboard host response contains a duplicate host")
        by_host[host] = _broker_host_status(raw, expected_host=host)
    master = validate_runtime_control_document(response.get("master"))
    master_enabled = bool(master["enabled"])
    if any(status["master_enabled"] is not master_enabled for status in by_host.values()):
        raise ValueError("dashboard host response disagrees with its master snapshot")
    selected = (
        [by_host[normalize_host(agent)]] if agent else [by_host[host] for host in SUPPORTED_HOSTS]
    )
    return selected, master, identity


def _dashboard_host_snapshot(
    agent: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    statuses, master, _identity = _dashboard_host_snapshot_with_identity(agent)
    return statuses, master


def _dashboard_inference_snapshot_with_identity() -> tuple[dict[str, Any], _BrokerStoreIdentity]:
    """Read one redacted inference projection from the authenticated broker."""

    from agency_runtime.cli.status_projection import project_brokered_inference
    from agency_runtime.core.dashboard_runtime import dashboard_api_request

    response = dashboard_api_request("/api/inference")
    return project_brokered_inference(response), _broker_store_identity(response)


def _direct_inference_snapshot(
    runtime_store: Any,
    dependencies: InstallDependencies,
) -> dict[str, Any]:
    """Build the same bounded inference projection consumed by the dashboard."""

    from agency_runtime.cli.status_projection import direct_inference_snapshot

    return direct_inference_snapshot(runtime_store, dependencies.load_config())


def _dashboard_soft_control_preview(
    agent: str,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Preview one host transition through the read-only authenticated broker."""

    from agency_runtime.core.host_control import normalize_host

    host = normalize_host(agent)
    statuses, _master, _identity = _dashboard_host_snapshot_with_identity(host)
    previous = statuses[0]
    previous_generation = _broker_generation(previous, "runtime_control_generation")
    return {
        "ok": True,
        "exit_code": 0,
        "host": host,
        "enabled": enabled,
        "runtime_enabled": bool(previous["runtime_enabled"]),
        "previous_runtime_enabled": bool(previous["runtime_enabled"]),
        "generation": previous_generation,
        "previous_generation": previous_generation,
        "updated_at": previous.get("runtime_control_updated_at"),
        "source": previous.get("runtime_control_source"),
        "dry_run": True,
        "transport": "dashboard",
        "native_lifecycle": "persistent soft control",
        "restart_required": False,
    }


def _restricted_aware_soft_control_result(
    runtime_store: Any,
    agent: str,
    *,
    enabled: bool,
    dry_run: bool,
    restricted_store: bool,
) -> dict[str, Any]:
    """Keep restricted model-facing processes read-only at the control boundary."""

    from agency_runtime.core.windows_acl import require_restricted_windows_token

    if restricted_store:
        if dry_run:
            return _dashboard_soft_control_preview(agent, enabled=enabled)
        raise RuntimeError(
            "host mutation is unavailable from a restricted model-facing process; "
            "use the owner-authenticated dashboard UI or run this command from a normal user shell"
        )
    try:
        return _soft_control_result(runtime_store, agent, enabled=enabled, dry_run=dry_run)
    except Exception as exc:
        require_restricted_windows_token(exc)
        if dry_run:
            return _dashboard_soft_control_preview(agent, enabled=enabled)
        raise RuntimeError(
            "host mutation is unavailable from a restricted model-facing process; "
            "use the owner-authenticated dashboard UI or run this command from a normal user shell"
        ) from exc


def _failed_control_result(agent: str, exc: Exception) -> dict[str, Any]:
    """Project one host-local failure without aborting remaining targets."""
    message = safe_display_token(str(exc).strip() or type(exc).__name__, limit=500)
    return {
        "ok": False,
        "exit_code": 1,
        "host": agent,
        "error": message,
        "restart_required": False,
    }


def _print_control_result(agent: str, result: dict[str, Any], *, enabled: bool) -> None:
    """Render one host result while preserving the existing single-host wording."""
    if result.get("ok"):
        prefix = (
            f"DRY RUN — would {'enable' if enabled else 'disable'}"
            if result.get("dry_run")
            else ("✅ Agency Runtime enabled" if enabled else "⏸️  Agency Runtime disabled")
        )
        print(
            f"{prefix} for {agent} through "
            f"{result.get('native_lifecycle', 'its native plugin lifecycle')}"
        )
        if result.get("restart_required"):
            print(f"   Restart {agent} to take effect.")
        return
    print(f"❌ {agent}: {result.get('error', 'control failed')}")


def _read_master_control_with_broker() -> tuple[dict[str, Any], str]:
    """Read global state directly or through the authenticated local service."""

    from agency_runtime.core.runtime_control import (
        RuntimeControlBrokerError,
        RuntimeControlError,
        read_authoritative_runtime_control,
    )

    try:
        return read_authoritative_runtime_control()
    except RuntimeControlBrokerError as direct_error:
        raise RuntimeError(
            "global Agency control is inaccessible from this process and the dashboard "
            "service could not broker it; run the command from a normal user shell or "
            "start/install the dashboard service"
        ) from direct_error
    except RuntimeControlError as direct_error:
        raise RuntimeError(
            "global Agency control could not be read securely; dashboard brokerage is "
            "limited to the canonical identity of a proven restricted Windows process"
        ) from direct_error


def _global_control_result(
    args: argparse.Namespace,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Apply or preview the durable cross-host master switch."""

    from agency_runtime.core.runtime_control import (
        RuntimeControlSecurityError,
        set_master_enabled,
    )

    if bool(getattr(args, "native", False)):
        raise ValueError("--global cannot be combined with --native")
    current, reader = _read_master_control_with_broker()
    dry_run = bool(getattr(args, "dry_run", False))
    if dry_run:
        master = current
        writer = reader
    elif reader == "dashboard":
        raise RuntimeError(
            "global mutation is unavailable from a restricted model-facing process; "
            "use the owner-authenticated dashboard UI or run this command from a normal user shell"
        )
    else:
        try:
            master = set_master_enabled(
                enabled,
                expected_generation=int(current["generation"]),
                source="cli",
            )
            writer = "direct"
        except RuntimeControlSecurityError as exc:
            raise RuntimeError(
                "global mutation is unavailable from a restricted model-facing process; "
                "use the owner-authenticated dashboard UI or run this command from a normal user shell"
            ) from exc
        expected_generation = int(current["generation"]) + (
            1 if bool(current["enabled"]) is not enabled else 0
        )
        if master["enabled"] is not enabled or int(master["generation"]) != expected_generation:
            raise ValueError("master-control response is internally inconsistent")
    return {
        "ok": True,
        "exit_code": 0,
        "scope": "global",
        "enabled": enabled if dry_run else bool(master["enabled"]),
        "previous_enabled": bool(current["enabled"]),
        "changed": bool(current["enabled"]) != enabled and not dry_run,
        "dry_run": dry_run,
        "transport": writer,
        "master": master,
        "fresh_session_required": not dry_run,
    }


def _print_global_control_result(result: dict[str, Any]) -> None:
    if not result.get("ok"):
        print(f"❌ global Agency control: {result.get('error', 'control failed')}")
        return
    desired = "enable" if result.get("enabled") else "disable"
    if result.get("dry_run"):
        print(f"DRY RUN — would {desired} Agency Runtime globally")
        return
    state = "enabled" if result.get("enabled") else "disabled"
    print(f"✅ Agency Runtime globally {state} through {result.get('transport', 'direct')} control")
    print("   Start a fresh host session before comparing Agency-on and Agency-off behavior.")


def _cmd_host_control(
    args: argparse.Namespace,
    *,
    enabled: bool,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Apply persistent soft control, or explicitly request native lifecycle."""
    if bool(getattr(args, "global_control", False)):
        try:
            result = _global_control_result(args, enabled=enabled)
        except Exception as exc:
            result = {
                "ok": False,
                "exit_code": 1,
                "scope": "global",
                "error": safe_display_token(str(exc).strip() or type(exc).__name__, limit=500),
            }
        if getattr(args, "json", False):
            dependencies.emit_json(result)
        else:
            _print_global_control_result(result)
        return int(result.get("exit_code", 0 if result.get("ok") else 1))
    action = "on" if enabled else "off"
    agents, explicit = _resolve_control_agents(args, action)
    if not agents:
        return 1
    dry_run = bool(getattr(args, "dry_run", False))
    native = bool(getattr(args, "native", False))
    runtime_store = None
    restricted_store = False
    from agency_runtime.core.windows_acl import require_restricted_windows_token

    if not native:
        try:
            runtime_store = dependencies.store_factory(None)
        except Exception as exc:
            require_restricted_windows_token(exc)
            restricted_store = True
    results: list[dict[str, Any]] = []
    if native:
        from agency_runtime.core.installer import toggle_agency

    for agent in agents:
        try:
            result = (
                toggle_agency(agent, enabled=enabled, dry_run=dry_run)
                if native
                else _restricted_aware_soft_control_result(
                    runtime_store,
                    agent,
                    enabled=enabled,
                    dry_run=dry_run,
                    restricted_store=restricted_store,
                )
            )
            result = dict(result)
            result.setdefault("host", agent)
        except Exception as exc:
            result = _failed_control_result(agent, exc)
        results.append(result)

    if explicit:
        result = results[0]
        if getattr(args, "json", False):
            dependencies.emit_json(result)
            return int(result.get("exit_code", 0 if result.get("ok") else 1))
        _print_control_result(agents[0], result, enabled=enabled)
        return 0 if result.get("ok") else 1

    successful = all(result.get("ok") is True for result in results)
    aggregate = {
        "ok": successful,
        "complete": successful,
        "action": action,
        "enabled": enabled,
        "host_count": len(results),
        "hosts": results,
        "exit_code": 0 if successful else 1,
    }
    if getattr(args, "json", False):
        dependencies.emit_json(aggregate)
    else:
        for agent, result in zip(agents, results, strict=True):
            _print_control_result(agent, result, enabled=enabled)
        print(
            f"   Completed {sum(result.get('ok') is True for result in results)}/{len(results)} hosts."
        )
    return aggregate["exit_code"]


def cmd_on(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Enable one explicit host or every detected host."""
    return _cmd_host_control(args, enabled=True, dependencies=dependencies)


def cmd_off(
    args: argparse.Namespace,
    *,
    dependencies: InstallDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Disable one explicit host or every detected host."""
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

    try:
        master, master_transport = _read_master_control_with_broker()
    except RuntimeError as exc:
        from agency_runtime.core.runtime_control import master_enabled

        master = {
            "schema_version": 1,
            "enabled": master_enabled(),
            "generation": 0,
            "updated_at": "",
            "source": "fail-enabled",
            "diagnostic_error": safe_display_token(str(exc), limit=500),
        }
        master_transport = "fail-enabled"
    from agency_runtime.core.windows_acl import require_restricted_windows_token

    try:
        runtime_store = dependencies.store_factory(None)
        statuses = (
            [inspect_host_status(runtime_store, args.agent, global_enabled=bool(master["enabled"]))]
            if args.agent
            else inspect_all_host_statuses(runtime_store, global_enabled=bool(master["enabled"]))
        )
        inference = _direct_inference_snapshot(runtime_store, dependencies)
    except Exception as exc:
        require_restricted_windows_token(exc)
        try:
            statuses, master, host_identity = _dashboard_host_snapshot_with_identity(args.agent)
            inference, inference_identity = _dashboard_inference_snapshot_with_identity()
            if inference_identity != host_identity:
                raise ValueError(
                    "dashboard status changed configuration or Store identity between reads"
                )
            master_transport = "dashboard"
        except (OSError, RuntimeError, ValueError) as broker_error:
            message = safe_display_token(
                "host status is inaccessible from this restricted process and the dashboard "
                f"service could not broker it: {broker_error}",
                limit=500,
            )
            payload = {
                "ok": False,
                "exit_code": 1,
                "error": message,
                "master": master,
                "master_transport": master_transport,
                "hosts": [],
            }
            if getattr(args, "json", False):
                dependencies.emit_json(payload)
            else:
                print(f"❌ {message}")
            return 1
    drifts = _cli_install_drift_projections()
    drift = drifts[0] if drifts else None
    payload = {
        "master": master,
        "master_transport": master_transport,
        "hosts": statuses,
        "inference": inference,
        "runtime_drift": drift,
        "runtime_drift_hosts": drifts,
    }
    if getattr(args, "json", False):
        dependencies.emit_json(payload)
        return 0
    global_state = "on" if master["enabled"] else "off"
    print(
        f"global: {global_state}; generation {master.get('generation', 0)}; "
        f"source {master.get('source', 'unknown')}"
    )
    for report in drifts:
        print(f"runtime [{report['host'] or 'unattributed'}]: {report['message']}")
    if drifts:
        print(f"  This CLI runs from: {drifts[0]['package_root']}")
    print(
        f"inference: {inference['state']}; {len(inference['provider_chain'])} provider entries; "
        f"eligible-turn inference "
        f"{'required' if inference['required_for_eligible_turns'] else 'not required'}"
    )
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
    accepted_outcome = bool(getattr(args, "accepted_outcome", False))
    if accepted_outcome:
        from agency_runtime.core.outcome_canary import (
            run_accepted_outcome_canary as run_selected_canary,
        )
    else:
        from agency_runtime.core.canary import run_canary as run_selected_canary

    report = run_selected_canary(
        args.agent,
        execute=bool(args.execute),
        confirm=str(args.confirm or ""),
        db_path=args.db,
        timeout=float(args.timeout),
        mode=str(args.mode),
        profile_scope=str(getattr(args, "profile_scope", "isolated-profile")),
        require_existing_store=(
            not accepted_outcome
            and args.agent == "codex"
            and bool(args.execute)
            and str(args.mode) == "agency"
            and str(getattr(args, "profile_scope", "isolated-profile")) == "current-profile"
        ),
    )
    if args.output:
        atomic_write_text(
            Path(args.output),
            json.dumps(report, indent=2, sort_keys=True) + "\n",
        )
    dependencies.emit_json(report)
    return 0 if (report["canary_passed"] if args.execute else report["ready"]) else 1
