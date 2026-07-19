"""Read-only planning, inspection, and lifecycle preflight."""

from __future__ import annotations

from dataclasses import dataclass
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
    _CommandResult,
    _Context,
    _context,
    _RollbackOutcome,
    _run,
    _unsupported,
    _validate_dashboard_launcher,
    dashboard_service_environment_error,
    dashboard_service_environment_overrides,
    dashboard_service_manager_environment_overrides,
)
from agency_runtime.core.dashboard_service_manifest import (
    _decode_service_file,
    _manifest_current,
    _manifest_owned,
    _path_present,
    _read_manifest,
)
from agency_runtime.core.dashboard_service_systemd import (
    _assert_systemd_unit_namespace,
    _read_systemd_unit,
    _systemd_active_state,
    _systemd_enabled_state,
    _unit_content,
)
from agency_runtime.core.dashboard_service_windows import (
    _query_windows_registration,
    _windows_create_command,
    _windows_definition_matches,
    _windows_task_content,
    _windows_task_properties,
    _windows_xml_owned,
)
from agency_runtime.core.windows_system import windows_system_command


def _manager_probe(
    ctx: _Context,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> tuple[bool | None, _CommandResult | None, str | None]:
    if home_dir is not None and command_runner is None:
        return None, None, None
    if ctx.platform == "linux":
        result = _run(
            ["systemctl", "--user", "show-environment"],
            command_runner=command_runner,
            timeout=10,
        )
        return result.ok, result, None
    state, result = _query_windows_registration(command_runner=command_runner)
    return state != "unavailable", result, state


@dataclass(frozen=True, slots=True)
class _LinuxUnitSnapshot:
    exists: bool
    content: str
    readable: bool


@dataclass(frozen=True, slots=True)
class _PlanRegistration:
    registration_path: str
    registration_content: str
    commands: list[list[str]]
    ownership_blocked: bool
    state_indeterminate: bool
    definition_drift: bool | None


@dataclass(frozen=True, slots=True)
class _PlanDisposition:
    ok: bool
    exit_code: int
    ready_to_install: bool
    error: str | None = None
    warning: str | None = None
    include_manager_probe: bool = False


@dataclass(frozen=True, slots=True)
class _InspectionRegistration:
    installed: bool | None
    owned: bool
    registration_owned: bool
    definition_drift: bool | None
    enabled: bool | None = None
    active: bool | None = None


def _linux_unit_path(ctx: _Context) -> Path:
    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    return ctx.unit_path


def _read_linux_unit(ctx: _Context) -> _LinuxUnitSnapshot:
    path = _linux_unit_path(ctx)
    try:
        _assert_systemd_unit_namespace(ctx)
    except (ConfigurationError, OSError):
        return _LinuxUnitSnapshot(
            exists=_path_present(path),
            content="",
            readable=False,
        )
    exists = _path_present(path)
    if not exists:
        return _LinuxUnitSnapshot(exists=False, content="", readable=True)
    try:
        content = _decode_service_file(_read_systemd_unit(ctx))
    except (ConfigurationError, OSError, UnicodeError):
        return _LinuxUnitSnapshot(exists=True, content="", readable=False)
    return _LinuxUnitSnapshot(exists=True, content=content, readable=True)


def _linux_plan_registration(ctx: _Context) -> _PlanRegistration:
    unit = _read_linux_unit(ctx)
    unit_owned = bool(
        unit.exists and unit.content.startswith(f"# {OWNER_MARKER}\n") and _manifest_owned(ctx)
    )
    ownership_blocked = bool(
        (unit.exists and unit.readable and not unit_owned)
        or (_path_present(ctx.manifest_path) and not _manifest_owned(ctx))
    )
    state_indeterminate = not unit.readable
    can_register = not ownership_blocked and not state_indeterminate
    commands = (
        [
            ["systemctl", "--user", "daemon-reload"],
            ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME],
        ]
        if can_register
        else []
    )
    return _PlanRegistration(
        registration_path=str(_linux_unit_path(ctx)),
        registration_content=_unit_content(ctx),
        commands=commands,
        ownership_blocked=ownership_blocked,
        state_indeterminate=state_indeterminate,
        definition_drift=unit.content != _unit_content(ctx) if unit_owned else None,
    )


def _windows_plan_registration(
    ctx: _Context,
    *,
    probe: _CommandResult | None,
    registration_state: str | None,
    command_runner: CommandRunner | None = None,
) -> _PlanRegistration:
    query_state = registration_state or "indeterminate"
    state_indeterminate = query_state == "indeterminate"
    task_exists = query_state == "present"
    task_owned = bool(
        task_exists
        and probe is not None
        and _windows_xml_owned(probe.stdout)
        and _manifest_owned(ctx)
    )
    ownership_blocked = bool(
        (task_exists and not task_owned)
        or (_path_present(ctx.manifest_path) and not _manifest_owned(ctx))
    )
    can_register = not ownership_blocked and not state_indeterminate
    commands = (
        [
            _windows_create_command(
                "<owner-private-task-xml>",
                force=task_exists,
                command_runner=command_runner,
            ),
            windows_system_command(
                "schtasks.exe",
                "/Run",
                "/TN",
                WINDOWS_TASK_NAME,
                command_runner=command_runner,
            ),
        ]
        if can_register
        else []
    )
    definition_drift = (
        not _windows_definition_matches(ctx, probe.stdout)
        if task_owned and probe is not None
        else None
    )
    return _PlanRegistration(
        registration_path=WINDOWS_TASK_NAME,
        registration_content=_windows_task_content(ctx),
        commands=commands,
        ownership_blocked=ownership_blocked,
        state_indeterminate=state_indeterminate,
        definition_drift=definition_drift,
    )


def _plan_registration(
    ctx: _Context,
    *,
    probe: _CommandResult | None,
    registration_state: str | None,
    command_runner: CommandRunner | None = None,
) -> _PlanRegistration:
    if ctx.platform == "linux":
        return _linux_plan_registration(ctx)
    return _windows_plan_registration(
        ctx,
        probe=probe,
        registration_state=registration_state,
        command_runner=command_runner,
    )


def _plan_disposition(
    *,
    available: bool | None,
    ownership_blocked: bool,
    state_indeterminate: bool,
    platform_name: str,
) -> _PlanDisposition:
    """Resolve plan truth and diagnostics without performing I/O."""

    if state_indeterminate:
        return _PlanDisposition(
            ok=False,
            exit_code=1,
            ready_to_install=False,
            error="service registration state could not be determined",
        )
    if ownership_blocked:
        return _PlanDisposition(
            ok=False,
            exit_code=1,
            ready_to_install=False,
            error=(
                "refusing to overwrite a same-name service registration without both "
                "the Agency Runtime definition marker and ownership manifest"
            ),
        )
    if available is False:
        manager = (
            "the systemd user manager" if platform_name == "linux" else "Windows Task Scheduler"
        )
        return _PlanDisposition(
            ok=False,
            exit_code=1,
            ready_to_install=False,
            error=f"{manager} is unavailable",
            include_manager_probe=True,
        )
    if available is None:
        return _PlanDisposition(
            ok=True,
            exit_code=0,
            ready_to_install=False,
            warning=("native manager probing is suppressed for an explicit home without a runner"),
        )
    return _PlanDisposition(ok=True, exit_code=0, ready_to_install=True)


def _render_plan(
    ctx: _Context,
    *,
    available: bool | None,
    probe: _CommandResult | None,
    registration: _PlanRegistration,
    manager_environment_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    disposition = _plan_disposition(
        available=available,
        ownership_blocked=registration.ownership_blocked,
        state_indeterminate=registration.state_indeterminate,
        platform_name=ctx.platform,
    )
    value: dict[str, Any] = {
        **_base("plan", ctx),
        "ok": disposition.ok,
        "exit_code": disposition.exit_code,
        "supported": True,
        "dry_run": True,
        "manager_available": available,
        "ready_to_install": disposition.ready_to_install,
        "definition_drift": registration.definition_drift,
        "registration_path": registration.registration_path,
        "registration_content": registration.registration_content,
        "commands": registration.commands,
    }
    if disposition.include_manager_probe:
        if probe is None:
            value["manager_probe"] = None
        else:
            # A failed ``show-environment`` may echo environment values on
            # either stream. Keep the fixed command and return code useful,
            # but never serialize those streams across the public boundary.
            public_probe = probe.public(include_failure_output=ctx.platform != "linux")
            if ctx.platform == "linux" and not probe.ok:
                public_probe["error"] = (
                    "systemd user manager environment probe failed; output redacted"
                )
                if manager_environment_names:
                    public_probe["reported_environment_names"] = list(manager_environment_names)
            value["manager_probe"] = public_probe
    if disposition.error is not None:
        value["error"] = disposition.error
    if disposition.warning is not None:
        value["warning"] = disposition.warning
    return value


def plan_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Return an exact, write-free service registration plan."""
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("plan", platform_name)
    config = load_config(ctx.config_path, reload=True)
    environment_overrides = dashboard_service_environment_overrides(config)
    if environment_overrides:
        result = _failed(
            "plan",
            ctx,
            error=dashboard_service_environment_error(environment_overrides),
            commands=[],
        )
        result["dry_run"] = True
        result["non_durable_environment_overrides"] = list(environment_overrides)
        return result
    available, probe, registration_state = _manager_probe(
        ctx, home_dir=home_dir, command_runner=command_runner
    )
    manager_environment_names: tuple[str, ...] = ()
    if ctx.platform == "linux" and probe is not None:
        manager_output = probe.stdout if probe.ok else f"{probe.stdout}\n{probe.stderr}"
        manager_environment_names = dashboard_service_manager_environment_overrides(
            config,
            manager_output,
        )
    manager_overrides = manager_environment_names if probe is not None and probe.ok else ()
    if manager_overrides:
        result = _failed(
            "plan",
            ctx,
            error=dashboard_service_environment_error(manager_overrides),
            commands=[],
        )
        result["dry_run"] = True
        result["non_durable_manager_environment_overrides"] = list(manager_overrides)
        return result
    registration = _plan_registration(
        ctx,
        probe=probe,
        registration_state=registration_state,
        command_runner=command_runner,
    )
    return _render_plan(
        ctx,
        available=available,
        probe=probe,
        registration=registration,
        manager_environment_names=manager_environment_names,
    )


def _linux_inspection_registration(
    ctx: _Context,
    *,
    available: bool | None,
    command_runner: CommandRunner | None,
    manifest_owned: bool,
) -> _InspectionRegistration:
    unit = _read_linux_unit(ctx)
    installed = unit.exists if unit.readable else None
    registration_owned = bool(installed and unit.content.startswith(f"# {OWNER_MARKER}\n"))
    definition_drift = (
        bool(registration_owned and unit.content != _unit_content(ctx)) if installed else None
    )
    enabled: bool | None = None
    active: bool | None = None
    if available:
        enabled_result = _run(
            ["systemctl", "--user", "is-enabled", SYSTEMD_UNIT_NAME],
            command_runner=command_runner,
            timeout=10,
        )
        active_result = _run(
            ["systemctl", "--user", "is-active", SYSTEMD_UNIT_NAME],
            command_runner=command_runner,
            timeout=10,
        )
        enabled = _systemd_enabled_state(enabled_result)
        active = _systemd_active_state(active_result)
    return _InspectionRegistration(
        installed=installed,
        owned=bool(registration_owned and manifest_owned),
        registration_owned=registration_owned,
        definition_drift=definition_drift,
        enabled=enabled,
        active=active,
    )


def _windows_installed_state(registration_state: str | None) -> bool | None:
    return {"present": True, "absent": False}.get(registration_state or "indeterminate")


def _windows_inspection_registration(
    ctx: _Context,
    *,
    probe: _CommandResult | None,
    registration_state: str | None,
    manifest_owned: bool,
) -> _InspectionRegistration:
    installed = _windows_installed_state(registration_state)
    task_xml = probe.stdout if installed and probe is not None else ""
    registration_owned = bool(installed and _windows_xml_owned(task_xml))
    definition_drift: bool | None = None
    enabled: bool | None = None
    if registration_owned:
        definition_drift = not _windows_definition_matches(ctx, task_xml)
        properties = _windows_task_properties(task_xml)
        enabled = bool(properties and properties.get("enabled").casefold() == "true")
    return _InspectionRegistration(
        installed=installed,
        owned=bool(registration_owned and manifest_owned),
        registration_owned=registration_owned,
        definition_drift=definition_drift,
        enabled=enabled,
    )


def _inspection_registration(
    ctx: _Context,
    *,
    available: bool | None,
    probe: _CommandResult | None,
    registration_state: str | None,
    command_runner: CommandRunner | None,
    manifest_owned: bool,
) -> _InspectionRegistration:
    if ctx.platform == "linux":
        return _linux_inspection_registration(
            ctx,
            available=available,
            command_runner=command_runner,
            manifest_owned=manifest_owned,
        )
    return _windows_inspection_registration(
        ctx,
        probe=probe,
        registration_state=registration_state,
        manifest_owned=manifest_owned,
    )


def _select_immediate_probe(
    *,
    reachability_probe: ReadinessProbe | None,
    readiness_probe: ReadinessProbe | None,
) -> ReadinessProbe | None:
    if reachability_probe is not None and readiness_probe is not None:
        raise ValueError("pass reachability_probe, not both reachability and readiness probes")
    return reachability_probe or readiness_probe


def _render_inspection(
    ctx: _Context,
    *,
    available: bool | None,
    manifest: dict[str, Any] | None,
    manifest_owned: bool,
    registration: _InspectionRegistration,
    reachable: bool | None,
) -> dict[str, Any]:
    manifest_current = _manifest_current(ctx, manifest)
    stale_manifest = bool(manifest_owned and registration.installed is False)
    return {
        **_base("inspect", ctx),
        "ok": True,
        "exit_code": 0,
        "supported": True,
        "manager_available": available,
        "installed": registration.installed,
        "owned": registration.owned,
        "manifest_owned": manifest_owned,
        "manifest_current": manifest_current,
        "stale_manifest": stale_manifest,
        "repair_recommended": bool(
            stale_manifest
            or (
                registration.owned
                and (
                    registration.definition_drift is True
                    or not manifest_current
                    or reachable is False
                )
            )
        ),
        "registration_owned": registration.registration_owned,
        "definition_drift": registration.definition_drift,
        "enabled": registration.enabled,
        "active": reachable if ctx.platform == "windows" else registration.active,
        "reachable": reachable,
        "registration_path": str(_linux_unit_path(ctx))
        if ctx.platform == "linux"
        else WINDOWS_TASK_NAME,
    }


def inspect_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
    _config: object | None = None,
    _ctx: _Context | None = None,
    _validate_launcher: bool = True,
) -> dict[str, Any]:
    """Separate registration, ownership, manager, and reachability truth."""
    ctx = _ctx or _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("inspect", platform_name)
    if _validate_launcher and not ctx.launcher_artifacts:
        try:
            ctx = _validate_dashboard_launcher(ctx)
        except OSError as exc:
            return _failed("inspect", ctx, error=str(exc), commands=[])
    config = _config if _config is not None else load_config(ctx.config_path)
    available, probe, registration_state = _manager_probe(
        ctx, home_dir=home_dir, command_runner=command_runner
    )
    manager_overrides = (
        dashboard_service_manager_environment_overrides(config, probe.stdout)
        if ctx.platform == "linux" and probe is not None and probe.ok
        else ()
    )
    if manager_overrides:
        result = _failed(
            "inspect",
            ctx,
            error=dashboard_service_environment_error(manager_overrides),
            # systemctl's stdout contains the environment values. Only names
            # may cross this response boundary.
            commands=[],
        )
        result["manager_available"] = available
        result["manager_environment_durable"] = False
        result["non_durable_manager_environment_overrides"] = list(manager_overrides)
        return result
    manifest = _read_manifest(ctx)
    manifest_owned = _manifest_owned(ctx, manifest)
    immediate_probe = _select_immediate_probe(
        reachability_probe=reachability_probe,
        readiness_probe=readiness_probe,
    )
    registration = _inspection_registration(
        ctx,
        available=available,
        probe=probe,
        registration_state=registration_state,
        command_runner=command_runner,
        manifest_owned=manifest_owned,
    )
    result = _render_inspection(
        ctx,
        available=available,
        manifest=manifest,
        manifest_owned=manifest_owned,
        registration=registration,
        reachable=_readiness(immediate_probe),
    )
    result["manager_environment_durable"] = not bool(manager_overrides)
    result["non_durable_manager_environment_overrides"] = list(manager_overrides)
    return result


def _preflight(
    action: str,
    ctx: _Context,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    reachability_probe: ReadinessProbe | None = None,
    config: object | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    state = inspect_dashboard_service(
        home_dir=home_dir,
        platform_name=ctx.platform,
        config_path=ctx.config_path,
        python_executable=ctx.python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
        _config=config,
        _ctx=ctx,
        _validate_launcher=action in {"install", "start", "restart"},
    )
    manager_overrides = state.get("non_durable_manager_environment_overrides") or []
    if manager_overrides:
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": dashboard_service_environment_error(manager_overrides),
                "non_durable_manager_environment_overrides": list(manager_overrides),
                "commands": [],
            },
            state,
        )
    if state.get("manager_available") is not True:
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "manager_available": state.get("manager_available"),
                "error": "native service-manager calls are unavailable or suppressed",
            },
            state,
        )
    if state.get("installed") is None:
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": "service registration state could not be determined",
            },
            state,
        )
    if (
        ctx.platform == "linux"
        and state.get("installed") is True
        and (state.get("enabled") is None or state.get("active") is None)
    ):
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": "systemd enablement or active state could not be determined",
            },
            state,
        )
    if state.get("installed") and not state.get("owned"):
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": "refusing to modify a dashboard service registration not owned by Agency Runtime",
            },
            state,
        )
    if (
        action in {"start", "restart"}
        and state.get("installed")
        and not state.get("manifest_current")
    ):
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": (
                    "dashboard launcher identity drift must be repaired by reinstalling the service"
                ),
                "commands": [],
            },
            state,
        )
    if (
        not state.get("installed")
        and _path_present(ctx.manifest_path)
        and not state.get("manifest_owned")
    ):
        return (
            {
                **_base(action, ctx),
                "ok": False,
                "exit_code": 1,
                "changed": False,
                "error": "refusing to replace an invalid dashboard service ownership manifest",
            },
            state,
        )
    return None, state


def _readiness(probe: ReadinessProbe | None) -> bool | None:
    if probe is None:
        return None
    try:
        return bool(probe())
    except Exception:
        return False


def _failed(
    action: str,
    ctx: _Context,
    *,
    error: str,
    commands: list[dict[str, Any]],
    rollback: _RollbackOutcome | None = None,
) -> dict[str, Any]:
    value = {
        **_base(action, ctx),
        "ok": False,
        "exit_code": 1,
        "changed": False,
        "error": error,
        "commands": commands,
    }
    if rollback is not None:
        value["rollback_commands"] = rollback.commands
        value["rollback_succeeded"] = rollback.succeeded
        if rollback.error is not None:
            value["rollback_error"] = rollback.error
    return value
