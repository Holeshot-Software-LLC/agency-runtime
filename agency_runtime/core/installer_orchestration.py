"""Installer planning, registration, rollback, and host control orchestration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_contracts import (
    ADAPTER_LAUNCHER_MANIFEST,
    CODEX_HOOK_TRUST_ACTION,
    CODEX_HOOK_TRUST_COMMAND,
    CODEX_HOOK_TRUST_SURFACE,
    HOSTS,
    INSTALL_MANIFEST,
    MARKETPLACE_ID,
    MINIMUM_OPENCLAW_VERSION,
    PLUGIN_ID,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
    openclaw_version_supported,
)
from agency_runtime.core.installer_payloads import bind_launcher_artifact_paths
from agency_runtime.core.launcher_bootstrap import (
    persistent_python_executable,
    prepare_private_package_runtime,
)
from agency_runtime.core.openclaw_streaming_policy import retained_backup_status
from agency_runtime.core.process_argv import (
    PersistentArtifactIdentity,
    revalidate_persistent_artifacts,
    snapshot_persistent_artifacts,
)


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _dispatch(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(_facade(), name)(*args, **kwargs)


def _atomic_install_tree(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _dispatch("_atomic_install_tree", *args, **kwargs)


def _bool_field(*args: Any, **kwargs: Any) -> bool | None:
    return _dispatch("_bool_field", *args, **kwargs)


def _bundle_files(*args: Any, **kwargs: Any) -> tuple[dict[str, str], str]:
    return _dispatch("_bundle_files", *args, **kwargs)


def _can_execute_native(*args: Any, **kwargs: Any) -> bool:
    return _dispatch("_can_execute_native", *args, **kwargs)


def _command_environment(*args: Any, **kwargs: Any) -> dict[str, str]:
    return _dispatch("_command_environment", *args, **kwargs)


def _hermes_text_plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _dispatch("_hermes_text_plugin_record", *args, **kwargs)


def _invalidate_canary_attestation(*args: Any, **kwargs: Any) -> bool:
    return _dispatch("_invalidate_canary_attestation", *args, **kwargs)


def _inventory_command(*args: Any, **kwargs: Any) -> list[str]:
    return _dispatch("_inventory_command", *args, **kwargs)


def _json_output(*args: Any, **kwargs: Any) -> Any:
    return _dispatch("_json_output", *args, **kwargs)


def _launcher_artifact_paths(*args: Any, **kwargs: Any) -> tuple[str, str]:
    return _dispatch("_launcher_artifact_paths", *args, **kwargs)


def _native_registration_steps(
    *args: Any, **kwargs: Any
) -> tuple[list[dict[str, Any]], bool, str | None]:
    return _dispatch("_native_registration_steps", *args, **kwargs)


def _openclaw_gateway_live(*args: Any, **kwargs: Any) -> tuple[bool, NativeCommandResult]:
    return _dispatch("_openclaw_gateway_live", *args, **kwargs)


def _plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _dispatch("_plugin_record", *args, **kwargs)


def _plugin_target(*args: Any, **kwargs: Any) -> Path:
    return _dispatch("_plugin_target", *args, **kwargs)


def _plan_agent_adapter(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _dispatch("plan_agent_adapter", *args, **kwargs)


def _resolve_binary(*args: Any, **kwargs: Any) -> str | None:
    return _dispatch("_resolve_binary", *args, **kwargs)


def _resolve_install_config(*args: Any, **kwargs: Any) -> AgencyConfig:
    return _dispatch("_resolve_install_config", *args, **kwargs)


def _root_state(*args: Any, **kwargs: Any) -> tuple[bool, bool, list[str]]:
    return _dispatch("_root_state", *args, **kwargs)


def _run_native(*args: Any, **kwargs: Any) -> NativeCommandResult:
    return _dispatch("_run_native", *args, **kwargs)


def _runtime_home(*args: Any, **kwargs: Any) -> Path:
    return _dispatch("_runtime_home", *args, **kwargs)


def _utc_stamp(*args: Any, **kwargs: Any) -> str:
    return _dispatch("_utc_stamp", *args, **kwargs)


def _validate_owned_backup(*args: Any, **kwargs: Any) -> tuple[bool, str | None, str | None]:
    return _dispatch("_validate_owned_backup", *args, **kwargs)


def _unknown_host_result(host: str, *, include_supported: bool = False) -> dict[str, Any]:
    message = f"Unknown host: {host}"
    if include_supported:
        message += f". Supported: {', '.join(HOSTS)}"
    return {"ok": False, "exit_code": 2, "error": message}


def _install_gateway_guard(
    host: str,
    executable: str | None,
    target: Path,
    primary: str,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> dict[str, Any] | None:
    """Return a fail-closed OpenClaw preflight result when mutation is unsafe."""

    if host != "openclaw" or not executable:
        return None
    if not _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        return None
    version_probe = _run_native(
        [str(HOSTS[host]["binary"]), "--version"],
        host=host,
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=8,
    )
    version_step = {"name": "host_capability_version", **version_probe.to_dict()}
    if not version_probe.ok or not openclaw_version_supported(version_probe.stdout):
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "plugin_path": str(target / primary),
            "target": str(target),
            "backup_path": None,
            "native_steps": [version_step],
            "registered": None,
            "enabled": None,
            "loaded": None,
            "canary": None,
            "partial": False,
            "status": "blocked",
            "maturity": (
                "staged-registration-unverified"
                if (target / INSTALL_MANIFEST).exists()
                else "host-discovered"
            ),
            "failed_step": "host_capability_unproven",
            "error": (
                "OpenClaw hook compatibility could not be proven. Agency Runtime requires "
                f"OpenClaw {MINIMUM_OPENCLAW_VERSION} or newer (stable)."
            ),
            "recovery": "Upgrade OpenClaw to a supported stable version, then rerun install.",
            "restart_required": False,
        }
    gateway_live, gateway_probe = _openclaw_gateway_live(
        home_dir=home_dir,
        command_runner=command_runner,
    )
    if gateway_live is False:
        return None
    failed_step = (
        "host_restart_consent_required" if gateway_live is True else "gateway_status_unproven"
    )
    gateway_state = "live" if gateway_live is True else "unknown"
    return {
        "ok": False,
        "exit_code": 1,
        "host": host,
        "plugin_path": str(target / primary),
        "target": str(target),
        "backup_path": None,
        "native_steps": [
            version_step,
            {
                "name": "gateway_status",
                "gateway_state": gateway_state,
                **gateway_probe.to_dict(),
            },
        ],
        "registered": None,
        "enabled": None,
        "loaded": None,
        "canary": None,
        "partial": False,
        "status": "blocked",
        "maturity": (
            "staged-registration-unverified"
            if (target / INSTALL_MANIFEST).exists()
            else "host-discovered"
        ),
        "failed_step": failed_step,
        "error": (
            "OpenClaw gateway is live; stop it before native installation."
            if gateway_live is True
            else "OpenClaw gateway status could not be proven safe; no installation changes were made."
        ),
        "recovery": "Establish a parseable, successful gateway status showing it is stopped, then rerun.",
        "restart_required": gateway_live is True,
    }


def _new_install_result(
    host: str,
    target: Path,
    primary: str,
    filesystem: dict[str, Any],
    *,
    home_dir: str | Path | None,
) -> tuple[dict[str, Any], bool]:
    bundle_changed = not bool(filesystem.get("unchanged"))
    attestation_invalidated = (
        _invalidate_canary_attestation(host, home_dir=home_dir) if bundle_changed else False
    )
    return (
        {
            "ok": True,
            "exit_code": 0,
            "host": host,
            "plugin_path": str(target / primary),
            "target": str(target),
            "filesystem": filesystem,
            "backup_path": filesystem.get("backup_path"),
            "native_steps": [],
            "registered": False,
            "enabled": None,
            "loaded": None,
            "canary": None,
            "restart_required": bundle_changed,
            "canary_attestation_invalidated": attestation_invalidated,
        },
        bundle_changed,
    )


def _staged_install_result(
    result: dict[str, Any],
    host: str,
    executable: str | None,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> dict[str, Any] | None:
    if host == "zcode":
        return None
    if not executable:
        result.update(
            {
                "status": "staged_unverified",
                "maturity": "staged-not-registered",
                "warning": "Host state exists but no executable was discovered; native registration was not attempted.",
            }
        )
        return result
    if _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        return None
    result.update(
        {
            "status": "staged_test_boundary",
            "maturity": "staged-not-registered",
            "warning": "Explicit home boundary suppressed real native commands; inject command_runner to exercise registration.",
        }
    )
    return result


def _freeze_adapter_launcher(
    files: dict[str, str],
) -> tuple[dict[str, str], tuple[PersistentArtifactIdentity, ...]]:
    paths = _launcher_artifact_paths()
    identities = snapshot_persistent_artifacts(paths)
    marker = {
        "schema_version": 1,
        "artifacts": [identity.manifest() for identity in identities],
    }
    return {
        **files,
        ADAPTER_LAUNCHER_MANIFEST: json.dumps(marker, indent=2) + "\n",
    }, identities


def _prepare_adapter_launcher_paths() -> tuple[str, str]:
    """Return one trusted launcher pair backed by a private runtime closure."""

    paths = _launcher_artifact_paths()
    staged = prepare_private_package_runtime(paths[1])
    prepared = (persistent_python_executable(paths[0]), staged)
    snapshot_persistent_artifacts(prepared)
    return prepared


def _openclaw_failure_facts(
    steps: list[dict[str, Any]],
    failed_step: str | None,
) -> tuple[str, str, bool | None, bool | None, bool | None]:
    status = "partial_failure"
    maturity = "staged-registration-incomplete"
    registered: bool | None = False
    enabled: bool | None = None
    loaded: bool | None = None
    if failed_step in {"enable", "conversation_access", "runtime_inspect_unproven"}:
        registered = True
    elif failed_step == "install":
        existing = next(
            (step for step in steps if step.get("name") == "inspect_existing"),
            None,
        )
        registered = True if existing and existing.get("ok") is True else None
    else:
        registered = None
    if failed_step in {"conversation_access", "runtime_inspect_unproven"}:
        enabled = True
    if failed_step == "runtime_inspect_unproven":
        runtime = next(
            (step for step in steps if step.get("name") == "runtime_inspect"),
            None,
        )
        loaded = runtime.get("loaded") if runtime else None
        status = "verification_incomplete"
        maturity = "enabled-runtime-unverified"
    restoration = next(
        (step for step in reversed(steps) if step.get("name") == "final_only_delivery_restore"),
        None,
    )
    if restoration and restoration.get("plugin_disabled") is True:
        plugin_registered = restoration.get("plugin_registered")
        registered = plugin_registered if isinstance(plugin_registered, bool) else registered
        enabled = False
        loaded = False
        status = "partial_failure"
        maturity = "registered-disabled" if registered else "staged-registration-incomplete"
    return status, maturity, registered, enabled, loaded


def _registration_failure_result(
    result: dict[str, Any],
    host: str,
    steps: list[dict[str, Any]],
    failed_step: str | None,
) -> dict[str, Any]:
    facts = (
        _openclaw_failure_facts(steps, failed_step)
        if host == "openclaw"
        else ("partial_failure", "staged-registration-incomplete", False, None, None)
    )
    status, maturity, registered, enabled, loaded = facts
    policy = next(
        (step for step in reversed(steps) if step.get("name") == "final_only_delivery_policy"),
        None,
    )
    restoration = next(
        (step for step in reversed(steps) if step.get("name") == "final_only_delivery_restore"),
        None,
    )
    error = (
        "OpenClaw gateway is live; stop it before native installation."
        if failed_step == "host_restart_consent_required"
        else "OpenClaw gateway status could not be proven safe; native installation was not attempted."
        if failed_step == "gateway_status_unproven"
        else str(policy.get("error"))
        if failed_step == "final_only_delivery_policy" and policy
        else f"Native {host} registration failed at step: {failed_step}"
    )
    result.update(
        {
            "ok": False,
            "exit_code": 1,
            "partial": True,
            "status": status,
            "maturity": maturity,
            "registered": registered,
            "enabled": enabled,
            "loaded": loaded,
            "canary": None,
            "failed_step": failed_step,
            "error": error,
            "recovery": (
                str(policy.get("recovery"))
                if failed_step == "final_only_delivery_policy" and policy
                else str(restoration.get("recovery"))
                if restoration and restoration.get("ok") is not True
                else "Fix the failed native step and rerun; filesystem staging is idempotent and the backup is retained."
            ),
        }
    )
    if host == "openclaw" and policy:
        result["streaming_policy"] = {key: value for key, value in policy.items() if key != "name"}
        if restoration:
            result["streaming_policy"]["restoration"] = {
                key: value
                for key, value in restoration.items()
                if key not in {"name", "triggered_by"}
            }
    return result


def _registration_success_result(result: dict[str, Any], host: str) -> dict[str, Any]:
    zcode_inventory = (
        next(
            (
                step
                for step in reversed(result.get("native_steps", []))
                if step.get("name") == "config_inventory"
            ),
            None,
        )
        if host == "zcode"
        else None
    )
    enabled = bool(zcode_inventory.get("enabled")) if isinstance(zcode_inventory, dict) else True
    result.update(
        {
            "status": "registered",
            "maturity": (
                "runtime-verified"
                if host == "openclaw"
                else "enabled-runtime-unverified"
                if enabled
                else "registered-disabled"
            ),
            "registered": True,
            "enabled": enabled,
            "loaded": True if host == "openclaw" else None,
            # Runtime inspection proves loading only.  No supported native
            # installer command currently exercises an end-to-end canary.
            "canary": None,
            "partial": False,
        }
    )
    if host == "codex":
        result.update(
            {
                "hook_trust_status": "unverified",
                "hook_trust_action": CODEX_HOOK_TRUST_ACTION,
                "hook_trust_surface": CODEX_HOOK_TRUST_SURFACE,
                "hook_trust_command": CODEX_HOOK_TRUST_COMMAND,
            }
        )
    elif host == "openclaw":
        policy = next(
            (
                step
                for step in reversed(result.get("native_steps", []))
                if step.get("name") == "final_only_delivery_policy"
            ),
            None,
        )
        if policy:
            result["streaming_policy"] = {
                key: value for key, value in policy.items() if key != "name"
            }
    return result


def _install_agent_adapter_unlocked(
    host: str,
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
    dry_run: bool = False,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Stage and natively register Agency Runtime for one host.

    A config-only/bare explicit host root may be staged, but only a discovered
    executable is allowed to perform native registration.  Native step failures
    return ``ok=False``, ``exit_code=1``, ``partial=True``, and the exact failed
    step instead of overstating maturity.
    """
    if host not in HOSTS:
        return _unknown_host_result(host, include_supported=True)
    if dry_run:
        return _plan_agent_adapter(
            host,
            cfg,
            home_dir=home_dir,
            binary_resolver=binary_resolver,
            command_runner=command_runner,
        )

    target = _plugin_target(host, home_dir=home_dir)
    effective_cfg = _resolve_install_config(cfg, home_dir=home_dir)
    from agency_runtime.core.runtime_control import runtime_control_path

    executable = _resolve_binary(host, binary_resolver)
    root_exists, current_root, _markers = _root_state(host, home_dir=home_dir)
    if not (executable or root_exists or current_root):
        return {
            "ok": False,
            "exit_code": 2,
            "error": f"{host} is not installed on this machine",
            "host": host,
        }
    try:
        launcher_paths = _prepare_adapter_launcher_paths()
        with bind_launcher_artifact_paths(launcher_paths):
            files, primary = _bundle_files(
                host,
                effective_cfg,
                runtime_control_path_value=str(runtime_control_path(home_dir=home_dir)),
            )
            files, launcher_artifacts = _freeze_adapter_launcher(files)
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "partial": False,
            "failed_step": "launcher_identity",
            "error": f"{type(exc).__name__}: {exc}",
        }
    blocked = _install_gateway_guard(
        host,
        executable,
        target,
        primary,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    if blocked is not None:
        return blocked

    try:
        revalidate_persistent_artifacts(launcher_artifacts)
        filesystem = _atomic_install_tree(
            target,
            files,
            host=host,
            dry_run=False,
            home_dir=home_dir,
            launcher_artifacts=launcher_artifacts,
        )
    except Exception as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "partial": False,
            "failed_step": "filesystem",
            "error": f"{type(exc).__name__}: {exc}",
        }

    result, bundle_changed = _new_install_result(
        host,
        target,
        primary,
        filesystem,
        home_dir=home_dir,
    )
    staged = _staged_install_result(
        result,
        host,
        executable,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    if staged is not None:
        return staged

    try:
        revalidate_persistent_artifacts(launcher_artifacts)
    except (OSError, ValueError) as exc:
        failed = _registration_failure_result(
            result,
            host,
            [],
            "launcher_identity",
        )
        failed["error"] = (
            "Persistent launcher identity changed before native registration: "
            f"{type(exc).__name__}: {exc}"
        )
        failed["recovery"] = (
            "Restore a trusted, current interpreter and Agency Runtime bootstrap, "
            "then rerun install. The staged bundle remains reversible."
        )
        return failed
    steps, native_ok, failed_step = _native_registration_steps(
        host,
        target,
        home_dir=home_dir,
        command_runner=command_runner,
        force_refresh=bundle_changed,
    )
    result["native_steps"] = steps
    if not native_ok:
        return _registration_failure_result(result, host, steps, failed_step)
    return _registration_success_result(result, host)


def install_agent_adapter(
    host: str,
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
    dry_run: bool = False,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Plan freely, but serialize every generic host-install mutation."""

    arguments = {
        "home_dir": home_dir,
        "dry_run": dry_run,
        "binary_resolver": binary_resolver,
        "command_runner": command_runner,
    }
    if dry_run or host not in HOSTS:
        return _install_agent_adapter_unlocked(host, cfg, **arguments)
    from agency_runtime.core.host_lifecycle_lock import (
        HostLifecycleLockError,
        host_integrations_lock,
    )

    try:
        with host_integrations_lock(home_dir=home_dir):
            return _install_agent_adapter_unlocked(host, cfg, **arguments)
    except HostLifecycleLockError:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "partial": False,
            "failed_step": "lifecycle_lock",
            "error": "another host integration transaction is active",
        }


def _resolve_rollback_backup(
    host: str,
    target: Path,
    backup_root: Path,
    backup_path: str | Path | None,
) -> tuple[Path | None, str | None, str | None]:
    if backup_path is not None:
        selected = Path(backup_path).expanduser().resolve()
    else:
        candidates = (
            sorted(
                (path.resolve() for path in backup_root.iterdir() if path.is_dir()),
                reverse=True,
            )
            if backup_root.exists()
            else []
        )
        selected = next(
            (
                candidate
                for candidate in candidates
                if _validate_owned_backup(candidate, host=host, target=target)[0]
            ),
            None,
        )
    if selected is None or not selected.exists():
        return None, None, f"No valid retained backup found for {host}"
    if selected == backup_root or not selected.is_relative_to(backup_root):
        return (
            None,
            None,
            f"Backup must be inside the managed backup root: {backup_root}",
        )
    valid, validation_error, restored_version = _validate_owned_backup(
        selected,
        host=host,
        target=target,
    )
    if not valid:
        return None, None, validation_error
    return selected, restored_version, None


def _rollback_gateway_guard(
    host: str,
    executable: str | None,
    target: Path,
    selected: Path,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> dict[str, Any] | None:
    """Prove OpenClaw is stopped before moving either rollback tree."""

    if host != "openclaw":
        return None
    gateway_live: bool | None = None
    gateway_probe: NativeCommandResult | None = None
    if executable and _can_execute_native(
        home_dir=home_dir,
        command_runner=command_runner,
    ):
        gateway_live, gateway_probe = _openclaw_gateway_live(
            home_dir=home_dir,
            command_runner=command_runner,
        )
    if gateway_live is False:
        return None
    gateway_state = "live" if gateway_live is True else "unknown"
    step: dict[str, Any] = {
        "name": "gateway_status",
        "gateway_state": gateway_state,
        "ok": gateway_live is False,
    }
    if gateway_probe is not None:
        step.update(gateway_probe.to_dict())
    elif not executable:
        step["error"] = "openclaw executable is unavailable; gateway state cannot be proven"
    else:
        step["error"] = "explicit home boundary suppresses the gateway status probe"
    return {
        "ok": False,
        "exit_code": 1,
        "host": host,
        "action": "rollback_blocked",
        "target": str(target),
        "restored_from": str(selected),
        "native_steps": [step],
        "partial": False,
        "failed_step": (
            "host_restart_consent_required" if gateway_live is True else "gateway_status_unproven"
        ),
        "maturity": "rollback-not-started",
        "error": (
            "OpenClaw gateway is live; stop it before rollback."
            if gateway_live is True
            else "OpenClaw gateway status could not be proven safe; no rollback changes were made."
        ),
    }


def _replace_with_backup(
    host: str,
    target: Path,
    selected: Path,
    *,
    home_dir: str | Path | None,
) -> tuple[Path | None, dict[str, Any] | None]:
    displaced: Path | None = None
    try:
        if target.exists():
            displaced = (
                _runtime_home(home_dir=home_dir)
                / "backups"
                / host
                / f"rollback-displaced-{_utc_stamp()}"
            )
            displaced.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, displaced)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(selected, target)
    except Exception as exc:
        if displaced is not None and displaced.exists() and not target.exists():
            os.replace(displaced, target)
        return None, {
            "ok": False,
            "exit_code": 1,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return displaced, None


def _new_rollback_result(
    host: str,
    selected: Path,
    restored_version: str | None,
    displaced: Path | None,
    *,
    home_dir: str | Path | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "exit_code": 0,
        "host": host,
        "action": "rolled_back",
        "restored_from": str(selected),
        "restored_version": restored_version,
        "displaced_path": str(displaced) if displaced else None,
        "restart_required": True,
        "native_steps": [],
        "native_refreshed": False,
        "canary_attestation_invalidated": _invalidate_canary_attestation(
            host,
            home_dir=home_dir,
        ),
    }


def _refresh_rollback_registration(
    result: dict[str, Any],
    host: str,
    target: Path,
    executable: str | None,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> dict[str, Any]:
    if host != "zcode" and (
        not executable
        or not _can_execute_native(
            home_dir=home_dir,
            command_runner=command_runner,
        )
    ):
        result["maturity"] = "filesystem-restored-native-unverified"
        return result
    steps, native_ok, failed_step = _native_registration_steps(
        host,
        target,
        home_dir=home_dir,
        command_runner=command_runner,
        force_refresh=True,
    )
    result["native_steps"] = steps
    result["native_refreshed"] = native_ok
    if native_ok:
        if host == "zcode":
            inventory = next(
                (step for step in reversed(steps) if step.get("name") == "config_inventory"),
                {},
            )
            result["registered"] = True
            result["enabled"] = bool(inventory.get("enabled"))
            result["loaded"] = None
            result["maturity"] = (
                "enabled-runtime-unverified" if result["enabled"] else "registered-disabled"
            )
        else:
            result["maturity"] = (
                "runtime-verified" if host == "openclaw" else "enabled-runtime-unverified"
            )
        return result
    result.update(
        {
            "ok": False,
            "exit_code": 1,
            "partial": True,
            "failed_step": failed_step,
            "maturity": "filesystem-restored-native-refresh-incomplete",
            "error": f"Filesystem rollback succeeded but native {host} refresh failed at {failed_step}",
        }
    )
    return result


def _rollback_agent_adapter_unlocked(
    host: str,
    *,
    home_dir: str | Path | None = None,
    backup_path: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Restore a retained bundle and refresh its native host registration.

    With an explicit ``home_dir`` and no injected runner, only the owned source
    tree is restored.  The result reports that native state as unverified rather
    than calling a real host outside the fixture boundary.
    """
    if host not in HOSTS:
        return _unknown_host_result(host)
    target = _plugin_target(host, home_dir=home_dir)
    backup_root = (_runtime_home(home_dir=home_dir) / "backups" / host).resolve()
    selected, restored_version, validation_error = _resolve_rollback_backup(
        host,
        target,
        backup_root,
        backup_path,
    )
    if selected is None:
        return {"ok": False, "exit_code": 2, "error": validation_error}

    executable = _resolve_binary(host, binary_resolver)
    blocked = _rollback_gateway_guard(
        host,
        executable,
        target,
        selected,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    if blocked is not None:
        return blocked
    displaced, replacement_error = _replace_with_backup(
        host,
        target,
        selected,
        home_dir=home_dir,
    )
    if replacement_error is not None:
        return replacement_error
    result = _new_rollback_result(
        host,
        selected,
        restored_version,
        displaced,
        home_dir=home_dir,
    )
    return _refresh_rollback_registration(
        result,
        host,
        target,
        executable,
        home_dir=home_dir,
        command_runner=command_runner,
    )


def rollback_agent_adapter(
    host: str,
    *,
    home_dir: str | Path | None = None,
    backup_path: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Serialize rollback with install, toggle, and prepared uninstall."""

    if host not in HOSTS:
        return _unknown_host_result(host)
    from agency_runtime.core.host_lifecycle_lock import (
        HostLifecycleLockError,
        host_integrations_lock,
    )

    try:
        with host_integrations_lock(home_dir=home_dir):
            return _rollback_agent_adapter_unlocked(
                host,
                home_dir=home_dir,
                backup_path=backup_path,
                binary_resolver=binary_resolver,
                command_runner=command_runner,
            )
    except HostLifecycleLockError:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "failed_step": "lifecycle_lock",
            "error": "another host integration transaction is active",
        }


def _toggle_command(host: str, enabled: bool) -> list[str]:
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    binary = str(HOSTS[host]["binary"])
    if host == "zcode":
        raise ValueError("ZCode native control uses its owned config transaction")
    if host in {"hermes", "openclaw"}:
        return [binary, "plugins", "enable" if enabled else "disable", PLUGIN_ID]
    if host == "claude":
        return [
            binary,
            "plugin",
            "enable" if enabled else "disable",
            selector,
            "--scope",
            "user",
        ]
    if enabled:
        return [binary, "plugin", "add", selector, "--json"]
    return [binary, "plugin", "remove", selector, "--json"]


@dataclass(frozen=True)
class _ToggleVerification:
    inventory: NativeCommandResult | None = None
    record: dict[str, Any] | None = None
    native_flag: bool | None = None
    postcondition: bool = False
    observed_enabled: bool | None = None


def _verify_toggle(
    host: str,
    enabled: bool,
    native_step: NativeCommandResult,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> _ToggleVerification:
    if not native_step.ok:
        return _ToggleVerification()
    inventory = _run_native(
        _inventory_command(host),
        host=host,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    if not inventory.ok:
        return _ToggleVerification(inventory=inventory)
    record = (
        _hermes_text_plugin_record(inventory.stdout)
        if host == "hermes"
        else _plugin_record(_json_output(inventory))
    )
    native_flag = _bool_field(record, "enabled", "active", "isEnabled")
    if enabled:
        postcondition = record is not None and native_flag is True
        observed_enabled = native_flag
    else:
        postcondition = record is None or native_flag is False
        observed_enabled = False if postcondition else native_flag
    return _ToggleVerification(
        inventory=inventory,
        record=record,
        native_flag=native_flag,
        postcondition=postcondition,
        observed_enabled=observed_enabled,
    )


def _toggle_verification_state(
    native_step: NativeCommandResult,
    verification: _ToggleVerification,
    *,
    enabled: bool,
) -> str:
    inventory = verification.inventory
    if not native_step.ok:
        return "command_failed"
    if inventory is None or not inventory.ok:
        return "inventory_failed"
    if verification.postcondition:
        return "verified"
    if enabled and verification.record is not None and verification.native_flag is None:
        return "enablement_unverified"
    return "postcondition_mismatch"


def _toggle_error(
    host: str,
    enabled: bool,
    native_step: NativeCommandResult,
    verification: _ToggleVerification,
) -> str | None:
    if not native_step.ok:
        return (native_step.stderr or native_step.stdout or "native toggle failed").strip()[:500]
    inventory = verification.inventory
    if inventory is None or not inventory.ok:
        detail = (inventory.stderr or inventory.stdout).strip() if inventory is not None else ""
        return (detail or "native toggle inventory verification failed")[:500]
    if verification.postcondition:
        return None
    return (
        f"native toggle postcondition was not proven for {host}: "
        f"wanted enabled={enabled}, inventory={verification.record!r}"
    )[:500]


def _toggle_agency_unlocked(
    host: str,
    enabled: bool,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Toggle Agency Runtime using only the host's native lifecycle."""
    if host not in HOSTS:
        return _unknown_host_result(host)
    if host == "zcode":
        from agency_runtime.core.installer_zcode import toggle_zcode_registration

        return toggle_zcode_registration(
            _plugin_target(host, home_dir=home_dir),
            enabled,
            home_dir=home_dir,
            dry_run=dry_run,
        )
    binary_path = _resolve_binary(host, binary_resolver)
    if not binary_path:
        return {
            "ok": False,
            "exit_code": 2,
            "error": f"{host} executable is not available",
        }
    command = _toggle_command(host, enabled)
    if dry_run:
        return {
            "ok": True,
            "exit_code": 0,
            "dry_run": True,
            "host": host,
            "enabled": enabled,
            "command": command,
            "native_lifecycle": HOSTS[host]["native_lifecycle"],
        }
    if not _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        return {
            "ok": False,
            "exit_code": 2,
            "error": "Explicit home boundary requires an injected command_runner for native toggles",
        }
    result = _run_native(
        command,
        host=host,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    verification = _verify_toggle(
        host,
        enabled,
        result,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    inventory = verification.inventory
    ok = bool(result.ok and inventory is not None and inventory.ok and verification.postcondition)
    verification_state = _toggle_verification_state(
        result,
        verification,
        enabled=enabled,
    )
    error = _toggle_error(host, enabled, result, verification)
    response = {
        "ok": ok,
        "exit_code": 0 if ok else (result.returncode or 1),
        "host": host,
        "enabled": verification.observed_enabled if ok else None,
        "action": ("enabled" if enabled else "disabled") if ok else verification_state,
        "native_step": result.to_dict(),
        "verification_step": inventory.to_dict() if inventory is not None else None,
        "postcondition_verified": verification.postcondition,
        "verification_state": verification_state,
        "partial": bool(result.ok and not ok),
        "error": error,
        "restart_required": True,
    }
    if host == "openclaw":
        response["streaming_policy"] = retained_backup_status(
            runtime_home=_runtime_home(home_dir=home_dir),
            environment=_command_environment(host, home_dir=home_dir),
        )
    return response


def toggle_agency(
    host: str,
    enabled: bool,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Plan freely, but serialize every native enablement mutation."""

    arguments = {
        "home_dir": home_dir,
        "binary_resolver": binary_resolver,
        "command_runner": command_runner,
        "dry_run": dry_run,
    }
    if dry_run or host not in HOSTS:
        return _toggle_agency_unlocked(host, enabled, **arguments)
    from agency_runtime.core.host_lifecycle_lock import (
        HostLifecycleLockError,
        host_integrations_lock,
    )

    try:
        with host_integrations_lock(home_dir=home_dir):
            return _toggle_agency_unlocked(host, enabled, **arguments)
    except HostLifecycleLockError:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "enabled": None,
            "action": "blocked",
            "failed_step": "lifecycle_lock",
            "error": "another host integration transaction is active",
        }
