"""Transactional installation and upgrade of dashboard services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agency_runtime.core.config import load_config
from agency_runtime.core.configuration import ConfigurationError
from agency_runtime.core.dashboard_service_core import (
    OWNER_MARKER,
    SYSTEMD_UNIT_NAME,
    WINDOWS_TASK_NAME,
    CommandRunner,
    ReadinessProbe,
    _base,
    _Context,
    _context,
    _dashboard_runtime_fingerprint,
    _dashboard_runtime_port,
    _fresh_dashboard_readiness,
    _revalidate_dashboard_launcher,
    _run,
    _unsupported,
    _validate_dashboard_launcher,
    _wait_dashboard_runtime_cleared,
    dashboard_service_environment_error,
    dashboard_service_environment_overrides,
)
from agency_runtime.core.dashboard_service_inspection import (
    _failed,
    _preflight,
    _readiness,
)
from agency_runtime.core.dashboard_service_manifest import (
    _atomic_write,
    _decode_service_file,
    _manifest_owned,
    _path_present,
    _read_manifest_bytes,
    _service_lock,
    _write_manifest,
)
from agency_runtime.core.dashboard_service_systemd import (
    _assert_systemd_files,
    _read_systemd_unit,
    _restore_systemd_state,
    _systemd_unit_root,
    _unit_content,
)
from agency_runtime.core.dashboard_service_windows import (
    _assert_windows_task_absent,
    _assert_windows_task_unchanged,
    _capture_owned_windows_task,
    _export_owned_windows_task,
    _register_windows_xml,
    _restore_windows_state,
    _wait_windows_running_state,
    _windows_definition_matches,
    _windows_running_state,
    _windows_task_content,
)
from agency_runtime.core.windows_system import windows_system_command


def install_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    """Install, enable, and start the current user's dashboard service."""
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("install", platform_name)
    try:
        config = load_config(ctx.config_path, reload=True)
        environment_overrides = dashboard_service_environment_overrides(config)
        if environment_overrides:
            result = _failed(
                "install",
                ctx,
                error=dashboard_service_environment_error(environment_overrides),
                commands=[],
            )
            result["non_durable_environment_overrides"] = list(environment_overrides)
            return result
        ctx = _validate_dashboard_launcher(ctx)
        _revalidate_dashboard_launcher(ctx)
        with _service_lock(ctx):
            blocked, state = _preflight(
                "install",
                ctx,
                home_dir=home_dir,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
                config=config,
            )
            if blocked is not None:
                return blocked
            if ctx.platform == "linux":
                return _install_linux(
                    ctx,
                    state,
                    command_runner=command_runner,
                    readiness_probe=readiness_probe,
                )
            return _install_windows(
                ctx,
                state,
                command_runner=command_runner,
                readiness_probe=readiness_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("install", ctx, error=str(exc), commands=[])


def _install_linux(
    ctx: _Context,
    state: Mapping[str, Any],
    *,
    command_runner: CommandRunner | None,
    readiness_probe: ReadinessProbe | None,
) -> dict[str, Any]:
    _revalidate_dashboard_launcher(ctx)
    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    desired = _unit_content(ctx)
    prior_unit = _read_systemd_unit(ctx) if _path_present(ctx.unit_path) else None
    prior_manifest = _read_manifest_bytes(ctx)
    expected_unit = prior_unit
    expected_manifest = prior_manifest
    try:
        prior_text = _decode_service_file(prior_unit) if prior_unit is not None else None
    except UnicodeError:
        return _failed("install", ctx, error="owned systemd unit is not valid UTF-8", commands=[])
    if prior_text is not None and (
        not prior_text.startswith(f"# {OWNER_MARKER}\n") or not _manifest_owned(ctx)
    ):
        return _failed(
            "install",
            ctx,
            error="systemd service ownership changed before mutation",
            commands=[],
        )
    registration_changed = prior_text != desired
    runtime_changed = not bool(state.get("manifest_current"))
    prior_enabled = state.get("enabled") is True
    prior_active = state.get("active") is True
    prior_reachable = state.get("reachable")
    activation_needed = not prior_enabled or not prior_active
    restart_needed = prior_active and (
        registration_changed or runtime_changed or prior_reachable is False
    )
    changed = registration_changed or runtime_changed or activation_needed or restart_needed
    commands: list[dict[str, Any]] = []
    try:
        if registration_changed:
            _atomic_write(
                ctx.unit_path,
                desired,
                trusted_root=_systemd_unit_root(ctx),
            )
            expected_unit = desired.encode("utf-8")
        manifest_changed = _write_manifest(ctx)
        expected_manifest = _read_manifest_bytes(ctx)
        _assert_systemd_files(
            ctx,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
        )
        _revalidate_dashboard_launcher(ctx)
        if registration_changed:
            reload_result = _run(
                ["systemctl", "--user", "daemon-reload"],
                command_runner=command_runner,
            )
            commands.append(reload_result.public())
            if not reload_result.ok:
                raise RuntimeError("systemd daemon-reload failed")
        _assert_systemd_files(
            ctx,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
        )
        if activation_needed:
            enable_result = _run(
                ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
            commands.append(enable_result.public())
            if not enable_result.ok:
                raise RuntimeError("systemd enable --now failed")
        elif restart_needed:
            restart_result = _run(
                ["systemctl", "--user", "restart", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
            commands.append(restart_result.public())
            if not restart_result.ok:
                raise RuntimeError("systemd restart after update failed")
        reachable = (
            _readiness(readiness_probe) if activation_needed or restart_needed else prior_reachable
        )
        if reachable is False:
            raise RuntimeError("dashboard service did not become ready")
        _assert_systemd_files(
            ctx,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
        )
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        rollback = _restore_systemd_state(
            ctx,
            prior_unit=prior_unit,
            prior_manifest=prior_manifest,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
            prior_enabled=prior_enabled,
            prior_active=prior_active,
            command_runner=command_runner,
        )
        return _failed(
            "install",
            ctx,
            error=str(exc),
            commands=commands,
            rollback=rollback,
        )
    return {
        **_base("install", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": changed or manifest_changed,
        "registration_changed": registration_changed,
        "runtime_changed": runtime_changed,
        "installed": True,
        "enabled": True,
        "active": True if reachable is True else None,
        "reachable": reachable,
        "commands": commands,
    }


@dataclass(slots=True)
class _WindowsInstallTransaction:
    prior_manifest: bytes | None
    installed: bool
    registration_changed: bool
    runtime_changed: bool
    prior_reachable: Any
    commands: list[dict[str, Any]] = field(default_factory=list)
    prior_task: str | None = None
    prior_runtime_fingerprint: str | None = None
    prior_runtime_port: int | None = None
    prior_active: bool = False
    state_mutated: bool = False
    created_registration: bool = False
    activation_needed: bool = False
    changed: bool = False
    manifest_changed: bool = False
    reachable: Any = None


def _windows_install_transaction(
    ctx: _Context,
    state: Mapping[str, Any],
) -> _WindowsInstallTransaction:
    installed = state.get("installed") is True
    return _WindowsInstallTransaction(
        prior_manifest=_read_manifest_bytes(ctx),
        installed=installed,
        registration_changed=(not installed or state.get("definition_drift") is True),
        runtime_changed=not bool(state.get("manifest_current")),
        prior_reachable=state.get("reachable"),
    )


def _capture_prior_windows_install(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    *,
    command_runner: CommandRunner | None,
) -> None:
    transaction.prior_runtime_port = _dashboard_runtime_port(ctx)
    transaction.prior_runtime_fingerprint = _dashboard_runtime_fingerprint(ctx)
    if transaction.installed:
        transaction.prior_task, ownership_query = _export_owned_windows_task(
            ctx,
            command_runner=command_runner,
        )
        transaction.commands.append(ownership_query.public())
        running, status_query = _windows_running_state(command_runner=command_runner)
        transaction.commands.append(status_query.public())
        if running is None:
            raise RuntimeError("scheduled-task running state could not be determined")
        transaction.prior_active = running
    transaction.activation_needed = (
        not transaction.installed
        or not transaction.prior_active
        or transaction.prior_reachable is False
    )
    transaction.changed = (
        transaction.registration_changed
        or transaction.runtime_changed
        or transaction.activation_needed
    )


def _register_windows_install(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    *,
    command_runner: CommandRunner | None,
) -> None:
    if not transaction.registration_changed:
        return
    if transaction.installed:
        if transaction.prior_task is None:
            raise RuntimeError("owned scheduled task could not be captured")
        exact = _assert_windows_task_unchanged(
            ctx, transaction.prior_task, command_runner=command_runner
        )
    else:
        exact = _assert_windows_task_absent(command_runner=command_runner)
    transaction.commands.append(exact.public())
    create_result = _register_windows_xml(
        ctx,
        _windows_task_content(ctx),
        force=transaction.installed,
        command_runner=command_runner,
    )
    if transaction.installed:
        transaction.state_mutated = True
    transaction.commands.append(create_result.public())
    if not create_result.ok:
        raise RuntimeError("scheduled-task creation failed")
    transaction.state_mutated = True
    transaction.created_registration = not transaction.installed


def _write_and_verify_windows_install(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    *,
    command_runner: CommandRunner | None,
) -> str:
    if transaction.runtime_changed:
        transaction.state_mutated = True
    transaction.manifest_changed = _write_manifest(ctx)
    current_task, current_query = _capture_owned_windows_task(ctx, command_runner=command_runner)
    transaction.commands.append(current_query.public())
    if not _windows_definition_matches(ctx, current_task):
        raise RuntimeError("scheduled-task registration verification failed")
    return current_task


def _stop_windows_install_task(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    current_task: str,
    *,
    command_runner: CommandRunner | None,
    failure_label: str,
) -> None:
    """Stop one exact owned task instance and wait for Task Scheduler to settle."""

    exact = _assert_windows_task_unchanged(ctx, current_task, command_runner=command_runner)
    transaction.commands.append(exact.public())
    end_result = _run(
        windows_system_command(
            "schtasks.exe",
            "/End",
            "/TN",
            WINDOWS_TASK_NAME,
            command_runner=command_runner,
        ),
        command_runner=command_runner,
    )
    transaction.state_mutated = True
    transaction.commands.append(end_result.public())
    if not end_result.ok:
        raise RuntimeError(f"{failure_label} failed")
    stopped, state_queries = _wait_windows_running_state(
        False,
        command_runner=command_runner,
    )
    transaction.commands.extend(query.public() for query in state_queries)
    if not stopped:
        raise RuntimeError(f"{failure_label} did not reach the idle state")


def _restart_windows_install_if_needed(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    current_task: str,
    *,
    command_runner: CommandRunner | None,
) -> None:
    restart_needed = (
        transaction.installed
        and transaction.prior_active
        and (transaction.registration_changed or transaction.runtime_changed)
    )
    if not restart_needed:
        return
    _stop_windows_install_task(
        ctx,
        transaction,
        current_task,
        command_runner=command_runner,
        failure_label="scheduled-task stop before restart",
    )


def _activate_windows_install_if_needed(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    current_task: str,
    *,
    command_runner: CommandRunner | None,
) -> None:
    if not transaction.changed:
        return
    clearance = _wait_dashboard_runtime_cleared(
        ctx,
        transaction.prior_runtime_fingerprint,
        previous_port=transaction.prior_runtime_port,
    )
    if clearance.replacement_detected:
        replacement_fingerprint = _dashboard_runtime_fingerprint(ctx)
        replacement_port = _dashboard_runtime_port(ctx)
        if replacement_fingerprint is None:
            raise RuntimeError(
                "dashboard runtime generation changed before activation; "
                "the replacement identity could not be verified"
            )
        replacement_running, replacement_query = _windows_running_state(
            command_runner=command_runner
        )
        transaction.commands.append(replacement_query.public())
        if replacement_running is None:
            raise RuntimeError(
                "dashboard runtime generation changed before activation; "
                "the replacement task state could not be verified"
            )
        if replacement_running:
            _stop_windows_install_task(
                ctx,
                transaction,
                current_task,
                command_runner=command_runner,
                failure_label="scheduled-task replacement stop",
            )
        clearance = _wait_dashboard_runtime_cleared(
            ctx,
            replacement_fingerprint,
            previous_port=replacement_port,
        )
        if clearance.replacement_detected:
            raise RuntimeError("dashboard runtime generation changed repeatedly before activation")
    if not clearance.cleared:
        raise RuntimeError("old dashboard runtime remained reachable before activation")
    exact = _assert_windows_task_unchanged(ctx, current_task, command_runner=command_runner)
    transaction.commands.append(exact.public())
    transaction.state_mutated = True
    run_result = _run(
        windows_system_command(
            "schtasks.exe",
            "/Run",
            "/TN",
            WINDOWS_TASK_NAME,
            command_runner=command_runner,
        ),
        command_runner=command_runner,
    )
    transaction.commands.append(run_result.public())
    if not run_result.ok:
        raise RuntimeError("scheduled-task start failed")
    started, state_queries = _wait_windows_running_state(
        True,
        command_runner=command_runner,
    )
    transaction.commands.extend(query.public() for query in state_queries)
    if not started:
        raise RuntimeError("scheduled task did not enter the running state")


def _verify_final_windows_install(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    *,
    command_runner: CommandRunner | None,
    readiness_probe: ReadinessProbe | None,
) -> None:
    transaction.reachable = (
        _fresh_dashboard_readiness(
            ctx,
            readiness_probe,
            transaction.prior_runtime_fingerprint,
        )
        if transaction.changed
        else transaction.prior_reachable
    )
    if transaction.reachable is False:
        raise RuntimeError("dashboard service did not become ready with a fresh runtime")
    final_task, final_query = _capture_owned_windows_task(ctx, command_runner=command_runner)
    transaction.commands.append(final_query.public())
    if not _windows_definition_matches(ctx, final_task):
        raise RuntimeError("scheduled-task registration changed after activation")


def _failed_windows_install(
    ctx: _Context,
    transaction: _WindowsInstallTransaction,
    exc: BaseException,
    *,
    command_runner: CommandRunner | None,
) -> dict[str, Any]:
    rollback = (
        _restore_windows_state(
            ctx,
            prior_task=transaction.prior_task,
            prior_manifest=transaction.prior_manifest,
            prior_active=transaction.prior_active,
            created_registration=transaction.created_registration,
            command_runner=command_runner,
        )
        if transaction.state_mutated
        else None
    )
    return _failed(
        "install",
        ctx,
        error=str(exc),
        commands=transaction.commands,
        rollback=rollback,
    )


def _install_windows(
    ctx: _Context,
    state: Mapping[str, Any],
    *,
    command_runner: CommandRunner | None,
    readiness_probe: ReadinessProbe | None,
) -> dict[str, Any]:
    _revalidate_dashboard_launcher(ctx)
    transaction = _windows_install_transaction(ctx, state)
    try:
        _capture_prior_windows_install(ctx, transaction, command_runner=command_runner)
        _register_windows_install(ctx, transaction, command_runner=command_runner)
        current_task = _write_and_verify_windows_install(
            ctx, transaction, command_runner=command_runner
        )
        _restart_windows_install_if_needed(
            ctx, transaction, current_task, command_runner=command_runner
        )
        _activate_windows_install_if_needed(
            ctx, transaction, current_task, command_runner=command_runner
        )
        _verify_final_windows_install(
            ctx,
            transaction,
            command_runner=command_runner,
            readiness_probe=readiness_probe,
        )
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        return _failed_windows_install(ctx, transaction, exc, command_runner=command_runner)
    return {
        **_base("install", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": transaction.changed or transaction.manifest_changed,
        "registration_changed": transaction.registration_changed,
        "runtime_changed": transaction.runtime_changed,
        "installed": True,
        "enabled": True,
        "active": True if transaction.changed else transaction.prior_active,
        "reachable": transaction.reachable,
        "commands": transaction.commands,
    }
