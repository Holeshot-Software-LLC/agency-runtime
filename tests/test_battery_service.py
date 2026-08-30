"""AR-337: systemd-user trigger units for the harness battery.

The service package's contract is ownership honesty: every written file
carries the Agency marker, install refuses to overwrite foreign units,
uninstall removes only marker-owned files, and the path unit watches
exactly the resolved harness install roots.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import battery_service as subject


def _runner_log() -> tuple[list[list[str]], Any]:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: Any) -> SimpleNamespace:
        calls.append(list(command))
        return SimpleNamespace(returncode=0)

    return calls, runner


@pytest.fixture(autouse=True)
def _relaxed_private_dirs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "ensure_private_directory",
        lambda path, **_kwargs: Path(path).mkdir(parents=True, exist_ok=True) or Path(path),
    )
    monkeypatch.setattr(subject, "assert_config_namespace", lambda _path: None)


def _harness_tree(tmp_path: Path) -> Any:
    package = tmp_path / "node_modules" / "openclaw"
    package.mkdir(parents=True)
    binary = package / "cli.js"
    binary.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    launcher = tmp_path / "bin" / "openclaw"
    launcher.parent.mkdir(exist_ok=True)
    launcher.symlink_to(binary)
    return lambda name: str(launcher) if name == "openclaw" else None


def test_install_writes_marker_owned_units_triggers_and_baseline(
    tmp_path: Path,
) -> None:
    resolver = _harness_tree(tmp_path)
    calls, runner = _runner_log()
    baseline_calls: list[bool] = []

    report = subject.install_battery_service(
        runtime_python=tmp_path / "venv" / "bin" / "python",
        unit_root=tmp_path / "systemd",
        shim_path=tmp_path / "bin" / "agency-battery",
        manifest_path=tmp_path / "services" / "battery-service.json",
        resolver=resolver,
        command_runner=runner,
        baseline_recorder=lambda: baseline_calls.append(True) or {"baseline": {}},
    )

    assert report["installed"] is True
    assert baseline_calls == [True]
    service = (tmp_path / "systemd" / subject.BATTERY_SERVICE_UNIT).read_text("utf-8")
    path_unit = (tmp_path / "systemd" / subject.BATTERY_PATH_UNIT).read_text("utf-8")
    timer = (tmp_path / "systemd" / subject.BATTERY_TIMER_UNIT).read_text("utf-8")
    shim = tmp_path / "bin" / "agency-battery"
    assert subject.BATTERY_OWNER_MARKER in service
    assert str(shim) in service
    assert f"PathModified={tmp_path / 'node_modules' / 'openclaw'}" in path_unit
    assert f"PathModified={tmp_path / 'bin'}" in path_unit
    assert "OnCalendar=daily" in timer and "Persistent=true" in timer
    assert subject.battery_service_mode(shim) == 0o700
    assert calls[0] == ["systemctl", "--user", "daemon-reload"]
    assert ["systemctl", "--user", "enable", "--now", subject.BATTERY_PATH_UNIT] in calls
    assert ["systemctl", "--user", "enable", "--now", subject.BATTERY_TIMER_UNIT] in calls
    manifest = json.loads((tmp_path / "services" / "battery-service.json").read_text("utf-8"))
    assert manifest["schema"] == "agency.battery-service.v1"
    assert len(manifest["units"]) == 3


def test_install_refuses_to_overwrite_a_foreign_unit(tmp_path: Path) -> None:
    resolver = _harness_tree(tmp_path)
    unit_root = tmp_path / "systemd"
    unit_root.mkdir()
    foreign = unit_root / subject.BATTERY_SERVICE_UNIT
    foreign.write_text("[Unit]\nDescription=someone else's unit\n", encoding="utf-8")
    _calls, runner = _runner_log()

    with pytest.raises(RuntimeError, match="foreign systemd unit"):
        subject.install_battery_service(
            runtime_python=tmp_path / "python",
            unit_root=unit_root,
            shim_path=tmp_path / "bin" / "agency-battery",
            manifest_path=tmp_path / "services" / "battery-service.json",
            resolver=resolver,
            command_runner=runner,
            baseline_recorder=lambda: {},
        )

    assert "someone else's unit" in foreign.read_text("utf-8")


def test_uninstall_removes_only_marker_owned_files(tmp_path: Path) -> None:
    resolver = _harness_tree(tmp_path)
    calls, runner = _runner_log()
    subject.install_battery_service(
        runtime_python=tmp_path / "python",
        unit_root=tmp_path / "systemd",
        shim_path=tmp_path / "bin" / "agency-battery",
        manifest_path=tmp_path / "services" / "battery-service.json",
        resolver=resolver,
        command_runner=runner,
        baseline_recorder=lambda: {},
    )
    foreign = tmp_path / "systemd" / subject.BATTERY_TIMER_UNIT
    foreign.write_text("[Unit]\nDescription=replaced by operator\n", encoding="utf-8")

    report = subject.uninstall_battery_service(
        unit_root=tmp_path / "systemd",
        shim_path=tmp_path / "bin" / "agency-battery",
        manifest_path=tmp_path / "services" / "battery-service.json",
        command_runner=runner,
    )

    removed = {Path(item).name for item in report["removed"]}
    assert subject.BATTERY_SERVICE_UNIT in removed
    assert subject.BATTERY_PATH_UNIT in removed
    assert "agency-battery" in removed
    assert subject.BATTERY_TIMER_UNIT not in removed
    assert foreign.exists()
    assert not (tmp_path / "services" / "battery-service.json").exists()
    assert ["systemctl", "--user", "disable", "--now", subject.BATTERY_PATH_UNIT] in calls


def test_watched_roots_deduplicate_and_sort(tmp_path: Path) -> None:
    resolver = _harness_tree(tmp_path)

    roots = subject.watched_battery_roots(resolver=resolver)

    assert roots == tuple(
        sorted({str(tmp_path / "node_modules" / "openclaw"), str(tmp_path / "bin")})
    )


def test_install_requires_at_least_one_watchable_root(tmp_path: Path) -> None:
    _calls, runner = _runner_log()
    with pytest.raises(RuntimeError, match="nothing to watch"):
        subject.install_battery_service(
            runtime_python=tmp_path / "python",
            unit_root=tmp_path / "systemd",
            shim_path=tmp_path / "bin" / "agency-battery",
            manifest_path=tmp_path / "services" / "m.json",
            resolver=lambda _name: None,
            command_runner=runner,
            baseline_recorder=lambda: {},
        )


def test_all_written_files_are_owner_private(tmp_path: Path) -> None:
    resolver = _harness_tree(tmp_path)
    _calls, runner = _runner_log()
    subject.install_battery_service(
        runtime_python=tmp_path / "python",
        unit_root=tmp_path / "systemd",
        shim_path=tmp_path / "bin" / "agency-battery",
        manifest_path=tmp_path / "services" / "battery-service.json",
        resolver=resolver,
        command_runner=runner,
        baseline_recorder=lambda: {},
    )

    for name in subject.BATTERY_UNITS:
        assert subject.battery_service_mode(tmp_path / "systemd" / name) == 0o600
    assert subject.battery_service_mode(tmp_path / "bin" / "agency-battery") == 0o700
    assert subject.battery_service_mode(tmp_path / "services" / "battery-service.json") == 0o600
