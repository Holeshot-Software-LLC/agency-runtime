"""Mutating dashboard service lifecycle transactions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agency_runtime.core.configuration import ConfigurationError
from agency_runtime.core.dashboard_service_core import (
    OWNER_MARKER,
    SYSTEMD_UNIT_NAME,
    WINDOWS_TASK_NAME,
    CommandRunner,
    ReadinessProbe,
    _base,
    _cleanup_stale_dashboard_runtime,
    _Context,
    _context,
    _dashboard_runtime_fingerprint,
    _DashboardRuntimeClearance,
    _fresh_dashboard_readiness,
    _revalidate_dashboard_launcher,
    _run,
    _unsupported,
    _validate_dashboard_launcher,
    _wait_dashboard_runtime_cleared,
)
from agency_runtime.core.dashboard_service_inspection import (
    _failed,
    _preflight,
    _readiness,
)
from agency_runtime.core.dashboard_service_manifest import (
    _decode_service_file,
    _manifest_owned,
    _read_manifest_bytes,
    _safe_unlink,
    _service_lock,
    _sync_parent,
)
from agency_runtime.core.dashboard_service_systemd import (
    _assert_systemd_files,
    _read_systemd_unit,
    _restore_systemd_state,
    _systemd_unit_root,
)
from agency_runtime.core.dashboard_service_windows import (
    _assert_windows_task_absent,
    _assert_windows_task_unchanged,
    _export_owned_windows_task,
    _restore_windows_state,
    _wait_windows_running_state,
    _windows_definition_matches,
    _windows_running_state,
)
from agency_runtime.core.windows_system import windows_system_command


def _cleanup_stale_runtime(
    ctx: _Context,
    _reachability_probe: ReadinessProbe | None,
) -> bool:
    return _cleanup_stale_dashboard_runtime(ctx)


def _replacement_runtime_conflict(
    action: str,
    ctx: _Context,
    clearance: _DashboardRuntimeClearance,
    *,
    commands: list[dict[str, Any]],
    changed: bool,
) -> dict[str, Any]:
    value = _failed(
        action,
        ctx,
        error=(
            "dashboard runtime generation changed during the service transition; "
            "the replacement was preserved"
        ),
        commands=commands,
    )
    value.update(
        {
            "changed": changed,
            "status": "runtime_replaced",
            "reachable": None,
            "replacement_runtime_preserved": True,
            "runtime_descriptor_removed": clearance.descriptor_removed,
        }
    )
    return value


def _runtime_clearance_failure(
    action: str,
    ctx: _Context,
    clearance: _DashboardRuntimeClearance,
    *,
    commands: list[dict[str, Any]],
    changed: bool,
    uncleared_error: str,
) -> dict[str, Any] | None:
    if clearance.replacement_detected:
        return _replacement_runtime_conflict(
            action,
            ctx,
            clearance,
            commands=commands,
            changed=changed,
        )
    if clearance.cleared:
        return None
    value = _failed(
        action,
        ctx,
        error=uncleared_error,
        commands=commands,
    )
    value["changed"] = changed
    return value


def _lifecycle_preflight(
    action: str,
    *,
    home_dir: str | Path | None,
    platform_name: str | None,
    config_path: str | Path | None,
    python_executable: str | Path | None,
    command_runner: CommandRunner | None,
    reachability_probe: ReadinessProbe | None = None,
) -> tuple[_Context | None, dict[str, Any] | None, dict[str, Any] | None]:
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return None, _unsupported(action, platform_name), None
    if action in {"start", "restart"}:
        ctx = _validate_dashboard_launcher(ctx)
    blocked, state = _preflight(
        action,
        ctx,
        home_dir=home_dir,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    return ctx, blocked, state


def _definition_drift_block(
    action: str, ctx: _Context, state: dict[str, Any]
) -> dict[str, Any] | None:
    if ctx.platform != "windows" or state.get("definition_drift") is False:
        return None
    return {
        **_base(action, ctx),
        "ok": False,
        "exit_code": 1,
        "changed": False,
        "error": "scheduled-task definition drift must be repaired by reinstalling the service",
        "commands": [],
    }


def start_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("start", platform_name)
    try:
        with _service_lock(ctx):
            return _start_dashboard_service_locked(
                home_dir=home_dir,
                platform_name=platform_name,
                config_path=config_path,
                python_executable=python_executable,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
                readiness_probe=readiness_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("start", ctx, error=str(exc), commands=[])


def _start_dashboard_service_locked(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx, blocked, state = _lifecycle_preflight(
        "start",
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    if blocked is not None:
        return blocked
    if ctx is None or state is None:
        raise RuntimeError("dashboard service preflight returned incomplete state")
    if not state.get("installed"):
        return {
            **_base("start", ctx),
            "ok": False,
            "exit_code": 1,
            "changed": False,
            "error": "dashboard service is not installed",
        }
    definition_block = _definition_drift_block("start", ctx, state)
    if definition_block is not None:
        return definition_block
    _revalidate_dashboard_launcher(ctx)
    if state.get("reachable") is True:
        return {
            **_base("start", ctx),
            "ok": True,
            "exit_code": 0,
            "changed": False,
            "status": "already_running",
            "reachable": True,
            "commands": [],
        }
    commands: list[dict[str, Any]] = []
    previous_runtime: str | None = None
    if ctx.platform == "windows":
        previous_runtime = _dashboard_runtime_fingerprint(ctx)
        task_xml, capture = _export_owned_windows_task(ctx, command_runner=command_runner)
        commands.append(capture.public())
        if not _windows_definition_matches(ctx, task_xml):
            return _failed(
                "start",
                ctx,
                error="scheduled-task definition changed after preflight; reinstall the service",
                commands=commands,
            )
        running, status_query = _windows_running_state(command_runner=command_runner)
        commands.append(status_query.public())
        if running is None:
            return _failed(
                "start",
                ctx,
                error="scheduled-task running state could not be determined",
                commands=commands,
            )
        if running:
            return _failed(
                "start",
                ctx,
                error="dashboard task is running but not reachable; restart it",
                commands=commands,
            )
        clearance = _wait_dashboard_runtime_cleared(
            ctx,
            previous_runtime,
        )
        clearance_failure = _runtime_clearance_failure(
            "start",
            ctx,
            clearance,
            commands=commands,
            changed=False,
            uncleared_error="stale dashboard runtime remained reachable before start",
        )
        if clearance_failure is not None:
            return clearance_failure
        exact = _assert_windows_task_unchanged(ctx, task_xml, command_runner=command_runner)
        commands.append(exact.public())
        command = windows_system_command(
            "schtasks.exe",
            "/Run",
            "/TN",
            WINDOWS_TASK_NAME,
            command_runner=command_runner,
        )
    else:
        command = [
            "systemctl",
            "--user",
            "restart" if state.get("active") is True else "start",
            SYSTEMD_UNIT_NAME,
        ]
    result = _run(command, command_runner=command_runner)
    commands.append(result.public())
    manager_ready = result.ok
    if ctx.platform == "windows" and result.ok:
        manager_ready, state_queries = _wait_windows_running_state(
            True,
            command_runner=command_runner,
        )
        commands.extend(query.public() for query in state_queries)
    reachable = (
        _fresh_dashboard_readiness(ctx, readiness_probe, previous_runtime)
        if manager_ready and ctx.platform == "windows"
        else _readiness(readiness_probe)
        if manager_ready
        else None
    )
    ok = manager_ready and reachable is not False
    value: dict[str, Any] = {
        **_base("start", ctx),
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "changed": result.ok,
        "reachable": reachable,
        "commands": commands,
    }
    if result.ok and not manager_ready:
        value["error"] = "scheduled task did not enter the running state"
    elif manager_ready and reachable is False:
        value["error"] = (
            "dashboard service did not become ready with a fresh runtime"
            if ctx.platform == "windows"
            else "dashboard service did not become ready"
        )
    return value


def stop_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("stop", platform_name)
    try:
        with _service_lock(ctx):
            return _stop_dashboard_service_locked(
                home_dir=home_dir,
                platform_name=platform_name,
                config_path=config_path,
                python_executable=python_executable,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("stop", ctx, error=str(exc), commands=[])


def _stop_dashboard_service_locked(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx, blocked, state = _lifecycle_preflight(
        "stop",
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    if blocked is not None:
        return blocked
    if ctx is None or state is None:
        raise RuntimeError("dashboard service preflight returned incomplete state")
    if not state.get("installed"):
        return {
            **_base("stop", ctx),
            "ok": True,
            "exit_code": 0,
            "changed": False,
            "status": "not_installed",
            "commands": [],
        }
    commands: list[dict[str, Any]] = []
    idle = ctx.platform == "linux" and state.get("active") is False
    task_xml: str | None = None
    previous_runtime: str | None = None
    if ctx.platform == "windows":
        previous_runtime = _dashboard_runtime_fingerprint(ctx)
        task_xml, capture = _export_owned_windows_task(ctx, command_runner=command_runner)
        commands.append(capture.public())
        running, status_query = _windows_running_state(command_runner=command_runner)
        commands.append(status_query.public())
        if running is None:
            return _failed(
                "stop",
                ctx,
                error="scheduled-task running state could not be determined",
                commands=commands,
            )
        idle = not running
    if idle:
        if ctx.platform == "windows":
            clearance = _wait_dashboard_runtime_cleared(
                ctx,
                previous_runtime,
            )
            descriptor_removed = clearance.descriptor_removed
            clearance_failure = _runtime_clearance_failure(
                "stop",
                ctx,
                clearance,
                commands=commands,
                changed=descriptor_removed,
                uncleared_error=(
                    "scheduled task is idle but its dashboard runtime remains reachable"
                ),
            )
            if clearance_failure is not None:
                return clearance_failure
        else:
            descriptor_removed = _cleanup_stale_runtime(ctx, reachability_probe)
        return {
            **_base("stop", ctx),
            "ok": True,
            "exit_code": 0,
            "changed": descriptor_removed,
            "status": "already_stopped",
            "reachable": False,
            "runtime_descriptor_removed": descriptor_removed,
            "commands": commands,
        }
    if ctx.platform == "windows":
        if task_xml is None:
            raise RuntimeError("owned scheduled task could not be captured")
        exact = _assert_windows_task_unchanged(ctx, task_xml, command_runner=command_runner)
        commands.append(exact.public())
        command = windows_system_command(
            "schtasks.exe",
            "/End",
            "/TN",
            WINDOWS_TASK_NAME,
            command_runner=command_runner,
        )
    else:
        command = ["systemctl", "--user", "stop", SYSTEMD_UNIT_NAME]
    result = _run(command, command_runner=command_runner)
    commands.append(result.public())
    manager_stopped = result.ok
    if ctx.platform == "windows" and result.ok:
        manager_stopped, state_queries = _wait_windows_running_state(
            False,
            command_runner=command_runner,
        )
        commands.extend(query.public() for query in state_queries)
        if not manager_stopped:
            value = _failed(
                "stop",
                ctx,
                error="scheduled task did not reach the idle state after stop",
                commands=commands,
            )
            value["changed"] = True
            return value
    if ctx.platform == "windows" and result.ok:
        clearance = _wait_dashboard_runtime_cleared(
            ctx,
            previous_runtime,
        )
        descriptor_removed = clearance.descriptor_removed
        clearance_failure = _runtime_clearance_failure(
            "stop",
            ctx,
            clearance,
            commands=commands,
            changed=True,
            uncleared_error="dashboard runtime remained reachable after scheduled task stopped",
        )
        if clearance_failure is not None:
            return clearance_failure
    else:
        descriptor_removed = result.ok and _cleanup_stale_runtime(ctx, reachability_probe)
    return {
        **_base("stop", ctx),
        "ok": manager_stopped,
        "exit_code": 0 if manager_stopped else 1,
        "changed": result.ok or descriptor_removed,
        "status": "stopped" if manager_stopped else "stop_failed",
        "runtime_descriptor_removed": descriptor_removed,
        "commands": commands,
    }


def restart_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("restart", platform_name)
    try:
        with _service_lock(ctx):
            return _restart_dashboard_service_locked(
                home_dir=home_dir,
                platform_name=platform_name,
                config_path=config_path,
                python_executable=python_executable,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
                readiness_probe=readiness_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("restart", ctx, error=str(exc), commands=[])


def _restart_dashboard_service_locked(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx, blocked, state = _lifecycle_preflight(
        "restart",
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    if blocked is not None:
        return blocked
    if ctx is None or state is None:
        raise RuntimeError("dashboard service preflight returned incomplete state")
    if not state.get("installed"):
        return {
            **_base("restart", ctx),
            "ok": False,
            "exit_code": 1,
            "changed": False,
            "error": "dashboard service is not installed",
        }
    definition_block = _definition_drift_block("restart", ctx, state)
    if definition_block is not None:
        return definition_block
    _revalidate_dashboard_launcher(ctx)
    previous_runtime: str | None = None
    if ctx.platform == "linux":
        raw_results = [
            _run(
                ["systemctl", "--user", "restart", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
        ]
        command_ok = raw_results[0].ok
    else:
        previous_runtime = _dashboard_runtime_fingerprint(ctx)
        task_xml, capture = _export_owned_windows_task(ctx, command_runner=command_runner)
        if not _windows_definition_matches(ctx, task_xml):
            return _failed(
                "restart",
                ctx,
                error="scheduled-task definition changed after preflight; reinstall the service",
                commands=[capture.public()],
            )
        running, status_query = _windows_running_state(command_runner=command_runner)
        raw_results = [capture, status_query]
        if running is None:
            return _failed(
                "restart",
                ctx,
                error="scheduled-task running state could not be determined",
                commands=[item.public() for item in raw_results],
            )
        if running:
            exact = _assert_windows_task_unchanged(ctx, task_xml, command_runner=command_runner)
            raw_results.append(exact)
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
            raw_results.append(end_result)
            if not end_result.ok:
                return _failed(
                    "restart",
                    ctx,
                    error="scheduled-task stop before restart failed",
                    commands=[item.public() for item in raw_results],
                )
            stopped, state_queries = _wait_windows_running_state(
                False,
                command_runner=command_runner,
            )
            raw_results.extend(state_queries)
            if not stopped:
                value = _failed(
                    "restart",
                    ctx,
                    error="scheduled task did not reach the idle state before restart",
                    commands=[item.public() for item in raw_results],
                )
                value["changed"] = True
                return value
        clearance = _wait_dashboard_runtime_cleared(
            ctx,
            previous_runtime,
        )
        clearance_failure = _runtime_clearance_failure(
            "restart",
            ctx,
            clearance,
            commands=[item.public() for item in raw_results],
            changed=bool(running),
            uncleared_error="old dashboard runtime remained reachable before restart",
        )
        if clearance_failure is not None:
            return clearance_failure
        exact = _assert_windows_task_unchanged(ctx, task_xml, command_runner=command_runner)
        raw_results.append(exact)
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
        raw_results.append(run_result)
        command_ok = run_result.ok
        if run_result.ok:
            command_ok, state_queries = _wait_windows_running_state(
                True,
                command_runner=command_runner,
            )
            raw_results.extend(state_queries)
    reachable = (
        _fresh_dashboard_readiness(ctx, readiness_probe, previous_runtime)
        if command_ok and ctx.platform == "windows"
        else _readiness(readiness_probe)
        if command_ok
        else None
    )
    ok = command_ok and reachable is not False
    value: dict[str, Any] = {
        **_base("restart", ctx),
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "changed": command_ok,
        "reachable": reachable,
        "commands": [item.public() for item in raw_results],
    }
    if ctx.platform == "windows" and raw_results[-1].ok and not command_ok:
        value["error"] = "scheduled task did not enter the running state"
    elif command_ok and reachable is False:
        value["error"] = (
            "dashboard service did not become ready with a fresh runtime"
            if ctx.platform == "windows"
            else "dashboard service did not become ready"
        )
    return value


def uninstall_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("uninstall", platform_name)
    try:
        with _service_lock(ctx):
            return _uninstall_dashboard_service_locked(
                home_dir=home_dir,
                platform_name=platform_name,
                config_path=config_path,
                python_executable=python_executable,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("uninstall", ctx, error=str(exc), commands=[])


@dataclass(slots=True)
class _SystemdUninstallTransaction:
    prior_unit: bytes
    prior_manifest: bytes | None
    expected_unit: bytes | None
    expected_manifest: bytes | None
    prior_enabled: bool
    prior_active: bool
    commands: list[Any] = field(default_factory=list)
    state_mutated: bool = False


@dataclass(slots=True)
class _WindowsUninstallTransaction:
    prior_manifest: bytes | None
    commands: list[Any] = field(default_factory=list)
    prior_task: str | None = None
    prior_active: bool = False
    state_mutated: bool = False


def _not_installed_uninstall(
    ctx: _Context,
    reachability_probe: ReadinessProbe | None,
) -> dict[str, Any]:
    manifest_removed = (
        _safe_unlink(ctx.manifest_path, missing_ok=True) if _manifest_owned(ctx) else False
    )
    descriptor_removed = _cleanup_stale_runtime(ctx, reachability_probe)
    return {
        **_base("uninstall", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": manifest_removed or descriptor_removed,
        "status": "not_installed",
        "runtime_descriptor_removed": descriptor_removed,
        "commands": [],
    }


def _systemd_uninstall_transaction(
    ctx: _Context,
    state: dict[str, Any],
) -> _SystemdUninstallTransaction:
    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    prior_unit = _read_systemd_unit(ctx)
    prior_manifest = _read_manifest_bytes(ctx)
    return _SystemdUninstallTransaction(
        prior_unit=prior_unit,
        prior_manifest=prior_manifest,
        expected_unit=prior_unit,
        expected_manifest=prior_manifest,
        prior_enabled=state.get("enabled") is True,
        prior_active=state.get("active") is True,
    )


def _perform_systemd_uninstall(
    ctx: _Context,
    transaction: _SystemdUninstallTransaction,
    *,
    command_runner: CommandRunner | None,
) -> None:
    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    if not _decode_service_file(transaction.prior_unit).startswith(f"# {OWNER_MARKER}\n"):
        raise RuntimeError("systemd ownership marker changed before mutation")
    if not _manifest_owned(ctx):
        raise RuntimeError("dashboard service ownership manifest changed before mutation")
    _assert_systemd_files(
        ctx,
        expected_unit=transaction.expected_unit,
        expected_manifest=transaction.expected_manifest,
    )
    disable = _run(
        ["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT_NAME],
        command_runner=command_runner,
    )
    transaction.state_mutated = True
    transaction.commands.append(disable)
    if not disable.ok:
        raise RuntimeError("systemd disable --now failed")
    _assert_systemd_files(
        ctx,
        expected_unit=transaction.expected_unit,
        expected_manifest=transaction.expected_manifest,
    )
    _safe_unlink(ctx.unit_path, trusted_root=_systemd_unit_root(ctx))
    transaction.expected_unit = None
    _safe_unlink(ctx.manifest_path)
    transaction.expected_manifest = None
    _sync_parent(ctx.unit_path)
    _sync_parent(ctx.manifest_path)
    _assert_systemd_files(ctx, expected_unit=None, expected_manifest=None)
    reload_result = _run(
        ["systemctl", "--user", "daemon-reload"],
        command_runner=command_runner,
    )
    transaction.commands.append(reload_result)
    if not reload_result.ok:
        raise RuntimeError("systemd daemon-reload failed")
    _assert_systemd_files(ctx, expected_unit=None, expected_manifest=None)


def _uninstall_systemd_service(
    ctx: _Context,
    state: dict[str, Any],
    *,
    command_runner: CommandRunner | None,
) -> list[Any] | dict[str, Any]:
    transaction = _systemd_uninstall_transaction(ctx, state)
    try:
        _perform_systemd_uninstall(ctx, transaction, command_runner=command_runner)
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        rollback = (
            _restore_systemd_state(
                ctx,
                prior_unit=transaction.prior_unit,
                prior_manifest=transaction.prior_manifest,
                expected_unit=transaction.expected_unit,
                expected_manifest=transaction.expected_manifest,
                prior_enabled=transaction.prior_enabled,
                prior_active=transaction.prior_active,
                command_runner=command_runner,
            )
            if transaction.state_mutated
            else None
        )
        return _failed(
            "uninstall",
            ctx,
            error=str(exc),
            commands=[item.public() for item in transaction.commands],
            rollback=rollback,
        )
    return transaction.commands


def _perform_windows_uninstall(
    ctx: _Context,
    transaction: _WindowsUninstallTransaction,
    *,
    command_runner: CommandRunner | None,
) -> None:
    transaction.prior_task, ownership_query = _export_owned_windows_task(
        ctx,
        command_runner=command_runner,
    )
    transaction.commands.append(ownership_query)
    running, status_query = _windows_running_state(command_runner=command_runner)
    transaction.commands.append(status_query)
    if running is None:
        raise RuntimeError("scheduled-task running state could not be determined")
    transaction.prior_active = running
    if running:
        exact = _assert_windows_task_unchanged(
            ctx, transaction.prior_task, command_runner=command_runner
        )
        transaction.commands.append(exact)
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
        transaction.commands.append(end_result)
        if not end_result.ok:
            raise RuntimeError("scheduled-task stop failed")
    exact = _assert_windows_task_unchanged(
        ctx, transaction.prior_task, command_runner=command_runner
    )
    transaction.commands.append(exact)
    delete_result = _run(
        windows_system_command(
            "schtasks.exe",
            "/Delete",
            "/TN",
            WINDOWS_TASK_NAME,
            "/F",
            command_runner=command_runner,
        ),
        command_runner=command_runner,
    )
    transaction.state_mutated = True
    transaction.commands.append(delete_result)
    if not delete_result.ok:
        raise RuntimeError("scheduled-task deletion failed")
    transaction.commands.append(_assert_windows_task_absent(command_runner=command_runner))
    _safe_unlink(ctx.manifest_path)


def _uninstall_windows_service(
    ctx: _Context,
    *,
    command_runner: CommandRunner | None,
) -> list[Any] | dict[str, Any]:
    transaction = _WindowsUninstallTransaction(prior_manifest=_read_manifest_bytes(ctx))
    try:
        _perform_windows_uninstall(ctx, transaction, command_runner=command_runner)
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        rollback = (
            _restore_windows_state(
                ctx,
                prior_task=transaction.prior_task,
                prior_manifest=transaction.prior_manifest,
                prior_active=transaction.prior_active,
                command_runner=command_runner,
            )
            if transaction.state_mutated
            else None
        )
        return _failed(
            "uninstall",
            ctx,
            error=str(exc),
            commands=[item.public() for item in transaction.commands],
            rollback=rollback,
        )
    return transaction.commands


def _uninstall_dashboard_service_locked(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    ctx, blocked, state = _lifecycle_preflight(
        "uninstall",
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    if blocked is not None:
        return blocked
    if ctx is None or state is None:
        raise RuntimeError("dashboard service preflight returned incomplete state")
    if not state.get("installed"):
        return _not_installed_uninstall(ctx, reachability_probe)
    if ctx.platform == "linux":
        outcome = _uninstall_systemd_service(ctx, state, command_runner=command_runner)
    else:
        outcome = _uninstall_windows_service(ctx, command_runner=command_runner)
    if isinstance(outcome, dict):
        return outcome
    descriptor_removed = _cleanup_stale_runtime(ctx, reachability_probe)
    return {
        **_base("uninstall", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": True,
        "installed": False,
        "runtime_descriptor_removed": descriptor_removed,
        "commands": [item.public() for item in outcome],
    }
