"""systemd-user trigger units for the harness canary battery (AR-337).

The owner interview (2026-08-30) fixed the mechanism: a dedicated oneshot
service triggered by a ``.path`` unit watching the harness install roots,
with a daily timer as a catch-all sweep, separate from the dashboard
service and without its restrictive namespace because the battery must
execute host CLIs against real profiles.

Every unit this module writes carries the Agency owner marker; install
refuses to overwrite a foreign unit and uninstall removes only
marker-bearing files. The service runs through a small refreshed shim so
the units themselves never embed a rotating runtime path.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agency_runtime.core.configuration_persistence import assert_config_namespace
from agency_runtime.core.harness_battery import (
    _VERSION_COMMANDS,
    _posture_root,
)
from agency_runtime.core.private_paths import ensure_private_directory

BATTERY_OWNER_MARKER = "# agency-runtime-owner: harness-battery"
BATTERY_SERVICE_UNIT = "agency-runtime-battery.service"
BATTERY_PATH_UNIT = "agency-runtime-battery.path"
BATTERY_TIMER_UNIT = "agency-runtime-battery.timer"
BATTERY_UNITS = (BATTERY_SERVICE_UNIT, BATTERY_PATH_UNIT, BATTERY_TIMER_UNIT)
_TRIGGER_UNITS = (BATTERY_PATH_UNIT, BATTERY_TIMER_UNIT)


def default_unit_root() -> Path:
    return Path("~/.config/systemd/user").expanduser()


def default_shim_path() -> Path:
    return Path("~/.agency-runtime/bin/agency-battery").expanduser()


def default_manifest_path() -> Path:
    return Path("~/.agency-runtime/services/battery-service.json").expanduser()


def _run(
    command: list[str],
    *,
    command_runner: Callable[..., Any],
) -> dict[str, Any]:
    try:
        completed = command_runner(
            command,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return {
            "command": command,
            "returncode": getattr(completed, "returncode", 1),
            "ok": getattr(completed, "returncode", 1) == 0,
        }
    except Exception:
        return {"command": command, "returncode": None, "ok": False}


def watched_battery_roots(
    *,
    resolver: Callable[[str], str | None] = shutil.which,
) -> tuple[str, ...]:
    """Resolve the harness install roots the path unit should watch."""

    roots: list[str] = []
    for command in _VERSION_COMMANDS.values():
        located = resolver(command[0])
        if not located:
            continue
        executable = Path(located)
        for candidate in (_posture_root(executable), executable.parent):
            text = str(candidate)
            if candidate.is_dir() and text not in roots:
                roots.append(text)
    return tuple(sorted(roots))


def _shim_content(runtime_python: Path) -> str:
    return (
        "#!/bin/sh\n"
        f"{BATTERY_OWNER_MARKER}\n"
        "# Refreshed by `agency battery --install-service`; points at the\n"
        "# runtime that installed it.\n"
        f'exec "{runtime_python}" -m agency_runtime.cli battery "$@"\n'
    )


def _service_unit(shim: Path) -> str:
    return (
        f"{BATTERY_OWNER_MARKER}\n"
        "[Unit]\n"
        "Description=Agency Runtime harness canary battery (AR-337)\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={shim}\n"
    )


def _path_unit(roots: tuple[str, ...]) -> str:
    watches = "".join(f"PathModified={root}\n" for root in roots)
    return (
        f"{BATTERY_OWNER_MARKER}\n"
        "[Unit]\n"
        "Description=Trigger the Agency harness battery on install-root changes\n"
        "\n"
        "[Path]\n"
        f"{watches}"
        f"Unit={BATTERY_SERVICE_UNIT}\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _timer_unit() -> str:
    return (
        f"{BATTERY_OWNER_MARKER}\n"
        "[Unit]\n"
        "Description=Daily sweep for the Agency harness battery\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=daily\n"
        "Persistent=true\n"
        "RandomizedDelaySec=1h\n"
        f"Unit={BATTERY_SERVICE_UNIT}\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def _refuse_foreign(path: Path) -> None:
    if not path.exists():
        return
    try:
        head = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise RuntimeError(f"unreadable existing unit: {path.name}") from exc
    if BATTERY_OWNER_MARKER not in head:
        raise RuntimeError(f"refusing to overwrite a foreign systemd unit: {path.name}")


def _write_owned(path: Path, content: str, *, executable: bool = False) -> None:
    """Write one owner-private marker-owned file (0700 executable, else 0600).

    systemd reads user units as the owning user, so nothing this module
    writes needs group or world bits; the repo posture is owner-private by
    default.
    """

    _refuse_foreign(path)
    mode = 0o700 if executable else 0o600
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        os.write(descriptor, content.encode("utf-8"))
    finally:
        os.close(descriptor)
    os.chmod(path, mode)


def install_battery_service(
    *,
    runtime_python: Path | None = None,
    unit_root: Path | None = None,
    shim_path: Path | None = None,
    manifest_path: Path | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    command_runner: Callable[..., Any] = subprocess.run,
    baseline_recorder: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Write the shim and three units, enable the triggers, seed the baseline."""

    import sys

    python = runtime_python or Path(sys.executable)
    units_root = unit_root or default_unit_root()
    shim = shim_path or default_shim_path()
    manifest = manifest_path or default_manifest_path()
    units_root.mkdir(parents=True, exist_ok=True)
    assert_config_namespace(units_root / BATTERY_SERVICE_UNIT)
    roots = watched_battery_roots(resolver=resolver)
    if not roots:
        raise RuntimeError("no harness install roots resolved; nothing to watch")

    ensure_private_directory(shim.parent)
    _write_owned(shim, _shim_content(python), executable=True)
    _write_owned(units_root / BATTERY_SERVICE_UNIT, _service_unit(shim))
    _write_owned(units_root / BATTERY_PATH_UNIT, _path_unit(roots))
    _write_owned(units_root / BATTERY_TIMER_UNIT, _timer_unit())

    commands = [_run(["systemctl", "--user", "daemon-reload"], command_runner=command_runner)]
    commands.extend(
        _run(
            ["systemctl", "--user", "enable", "--now", unit],
            command_runner=command_runner,
        )
        for unit in _TRIGGER_UNITS
    )
    if baseline_recorder is None:
        from agency_runtime.core.harness_battery import record_baseline

        baseline_recorder = record_baseline
    baseline = baseline_recorder()

    ensure_private_directory(manifest.parent)
    document = {
        "schema": "agency.battery-service.v1",
        "shim": str(shim),
        "units": [str(units_root / unit) for unit in BATTERY_UNITS],
        "watched_roots": list(roots),
    }
    descriptor = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(
            descriptor,
            (json.dumps(document, indent=1, sort_keys=True) + "\n").encode("utf-8"),
        )
    finally:
        os.close(descriptor)
    ok = all(item["ok"] for item in commands)
    return {
        "installed": ok,
        "commands": commands,
        "watched_roots": list(roots),
        "baseline": baseline,
        "manifest": str(manifest),
    }


def uninstall_battery_service(
    *,
    unit_root: Path | None = None,
    shim_path: Path | None = None,
    manifest_path: Path | None = None,
    command_runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """Disable the triggers and remove only marker-owned files."""

    units_root = unit_root or default_unit_root()
    shim = shim_path or default_shim_path()
    manifest = manifest_path or default_manifest_path()
    commands = [
        _run(
            ["systemctl", "--user", "disable", "--now", unit],
            command_runner=command_runner,
        )
        for unit in _TRIGGER_UNITS
    ]
    removed: list[str] = []
    for name in BATTERY_UNITS:
        target = units_root / name
        try:
            _refuse_foreign(target)
        except RuntimeError:
            continue
        if target.exists():
            target.unlink()
            removed.append(str(target))
    if shim.exists():
        try:
            _refuse_foreign(shim)
        except RuntimeError:
            pass
        else:
            shim.unlink()
            removed.append(str(shim))
    commands.append(_run(["systemctl", "--user", "daemon-reload"], command_runner=command_runner))
    if manifest.exists():
        manifest.unlink()
        removed.append(str(manifest))
    return {"removed": removed, "commands": commands}


def battery_service_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)
