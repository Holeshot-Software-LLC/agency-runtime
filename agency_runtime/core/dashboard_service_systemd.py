"""Linux systemd-user registration and rollback mechanics."""

from __future__ import annotations

from agency_runtime.core.configuration import ConfigurationError
from agency_runtime.core.dashboard_service_core import (
    OWNER_MARKER,
    SYSTEMD_UNIT_NAME,
    CommandRunner,
    _CommandResult,
    _Context,
    _RollbackOutcome,
    _run,
    _validate_text,
)
from agency_runtime.core.dashboard_service_manifest import (
    _file_matches,
    _restore_file,
)


def _systemd_quote(value: str) -> str:
    text = _validate_text(value, label="systemd argument")
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$")
    return f'"{escaped}"'


def _unit_content(ctx: _Context) -> str:
    exec_start = " ".join(_systemd_quote(item) for item in ctx.worker_argv)
    return (
        f"# {OWNER_MARKER}\n"
        "[Unit]\n"
        "Description=Agency Runtime local operations dashboard\n"
        "After=network.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"ExecStart={exec_start}\n"
        "Restart=on-failure\n"
        "RestartSec=3s\n"
        "UMask=0077\n"
        "NoNewPrivileges=true\n"
        "PrivateTmp=true\n"
        "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _systemd_enabled_state(result: _CommandResult) -> bool | None:
    value = result.stdout.strip().casefold()
    if result.ok and value == "enabled":
        return True
    if value in {"disabled", "masked", "static", "indirect", "generated"}:
        return False
    return None


def _systemd_active_state(result: _CommandResult) -> bool | None:
    value = result.stdout.strip().casefold()
    if result.ok and value == "active":
        return True
    if value in {"inactive", "failed", "dead"}:
        return False
    return None


def _assert_systemd_files(
    ctx: _Context,
    *,
    expected_unit: bytes | None,
    expected_manifest: bytes | None,
) -> None:
    """Fail closed if registration state changed outside the held service lock."""

    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    if not _file_matches(ctx.unit_path, expected_unit) or not _file_matches(
        ctx.manifest_path, expected_manifest
    ):
        raise RuntimeError("systemd service files changed before mutation")


def _restore_systemd_state(
    ctx: _Context,
    *,
    prior_unit: bytes | None,
    prior_manifest: bytes | None,
    expected_unit: bytes | None,
    expected_manifest: bytes | None,
    prior_enabled: bool,
    prior_active: bool,
    command_runner: CommandRunner | None,
) -> _RollbackOutcome:
    """Restore a systemd transaction only while its exact snapshots remain."""

    if ctx.unit_path is None:
        raise RuntimeError("Linux dashboard service context has no unit path")
    results: list[_CommandResult] = []
    mutation_results: list[_CommandResult] = []
    restore_error: str | None = None
    try:
        _assert_systemd_files(
            ctx,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
        )
        if prior_unit is None:
            mutation_results.append(
                _run(
                    ["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT_NAME],
                    command_runner=command_runner,
                )
            )
        _assert_systemd_files(
            ctx,
            expected_unit=expected_unit,
            expected_manifest=expected_manifest,
        )
        _restore_file(ctx.unit_path, prior_unit)
        _restore_file(ctx.manifest_path, prior_manifest)
        mutation_results.append(
            _run(
                ["systemctl", "--user", "daemon-reload"],
                command_runner=command_runner,
            )
        )
        if prior_unit is not None:
            mutation_results.append(
                _run(
                    [
                        "systemctl",
                        "--user",
                        "enable" if prior_enabled else "disable",
                        SYSTEMD_UNIT_NAME,
                    ],
                    command_runner=command_runner,
                )
            )
            mutation_results.append(
                _run(
                    [
                        "systemctl",
                        "--user",
                        "restart" if prior_active else "stop",
                        SYSTEMD_UNIT_NAME,
                    ],
                    command_runner=command_runner,
                )
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        restore_error = str(exc)
        if restore_error == "systemd service files changed before mutation" and _file_matches(
            ctx.manifest_path, expected_manifest
        ):
            try:
                _restore_file(ctx.manifest_path, None)
                restore_error = (
                    "unsafe systemd rollback refused: service files changed; "
                    "ownership manifest removed"
                )
            except (ConfigurationError, OSError, RuntimeError):
                restore_error = (
                    "unsafe systemd rollback refused: service files and ownership manifest changed"
                )
    results.extend(mutation_results)
    enabled_query = _run(
        ["systemctl", "--user", "is-enabled", SYSTEMD_UNIT_NAME],
        command_runner=command_runner,
    )
    active_query = _run(
        ["systemctl", "--user", "is-active", SYSTEMD_UNIT_NAME],
        command_runner=command_runner,
    )
    results.extend((enabled_query, active_query))
    registration_ok = _file_matches(ctx.unit_path, prior_unit) and _file_matches(
        ctx.manifest_path, prior_manifest
    )
    enabled_ok = (
        True if prior_unit is None else _systemd_enabled_state(enabled_query) is prior_enabled
    )
    semantic_ok = bool(
        registration_ok and enabled_ok and _systemd_active_state(active_query) is prior_active
    )
    succeeded = bool(
        restore_error is None and all(result.ok for result in mutation_results) and semantic_ok
    )
    error = restore_error or (None if succeeded else "systemd rollback verification failed")
    return _RollbackOutcome(
        commands=[result.public() for result in results],
        succeeded=succeeded,
        error=error,
    )


__all__ = [
    "_assert_systemd_files",
    "_restore_systemd_state",
    "_systemd_active_state",
    "_systemd_enabled_state",
    "_unit_content",
]
