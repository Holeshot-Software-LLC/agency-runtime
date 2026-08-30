"""Focused state and rollback tests for dashboard transaction orchestrators."""

from __future__ import annotations

from pathlib import Path

import pytest

from agency_runtime.core import dashboard_service_install as install_module
from agency_runtime.core import dashboard_service_lifecycle as lifecycle_module
from agency_runtime.core.dashboard_service_core import (
    _CommandResult,
    _Context,
    _RollbackOutcome,
)
from agency_runtime.core.dashboard_service_install import (
    _capture_prior_windows_install,
    _failed_windows_install,
    _WindowsInstallTransaction,
)
from agency_runtime.core.dashboard_service_lifecycle import _not_installed_uninstall


def _context(tmp_path: Path, platform: str = "windows") -> _Context:
    return _Context(
        platform=platform,
        home=tmp_path,
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python.exe",
        manager="schtasks.exe" if platform == "windows" else "systemctl",
        registration="Agency Runtime Dashboard",
        unit_path=(tmp_path / "agency-dashboard.service" if platform == "linux" else None),
        manifest_path=tmp_path / "dashboard-service.json",
        worker_argv=("python", "-m", "agency_runtime.server.dashboard"),
        windows_user="S-1-5-21-test" if platform == "windows" else None,
    )


@pytest.mark.parametrize(
    (
        "installed",
        "running",
        "registration_changed",
        "runtime_changed",
        "prior_reachable",
        "activation_needed",
        "changed",
        "command_count",
    ),
    [
        (False, None, True, True, None, True, True, 0),
        (True, True, False, False, True, False, False, 2),
        (True, False, False, False, True, True, True, 2),
        (True, True, False, False, False, True, True, 2),
        (True, True, True, False, True, False, True, 2),
        (True, True, False, True, True, False, True, 2),
    ],
)
def test_windows_install_plan_state_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    installed: bool,
    running: bool | None,
    registration_changed: bool,
    runtime_changed: bool,
    prior_reachable: bool | None,
    activation_needed: bool,
    changed: bool,
    command_count: int,
) -> None:
    result = _CommandResult(("schtasks.exe",), 0)
    monkeypatch.setattr(
        install_module,
        "_export_owned_windows_task",
        lambda *_args, **_kwargs: ("<Task />", result),
    )
    monkeypatch.setattr(
        install_module,
        "_windows_running_state",
        lambda **_kwargs: (running, result),
    )
    transaction = _WindowsInstallTransaction(
        prior_manifest=None,
        installed=installed,
        registration_changed=registration_changed,
        runtime_changed=runtime_changed,
        prior_reachable=prior_reachable,
    )

    _capture_prior_windows_install(
        _context(tmp_path),
        transaction,
        command_runner=None,
    )

    assert transaction.prior_active is (running if installed else False)
    assert transaction.activation_needed is activation_needed
    assert transaction.changed is changed
    assert len(transaction.commands) == command_count


def test_windows_install_indeterminate_running_state_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _CommandResult(("schtasks.exe",), 0)
    monkeypatch.setattr(
        install_module,
        "_export_owned_windows_task",
        lambda *_args, **_kwargs: ("<Task />", result),
    )
    monkeypatch.setattr(
        install_module,
        "_windows_running_state",
        lambda **_kwargs: (None, result),
    )
    transaction = _WindowsInstallTransaction(
        prior_manifest=None,
        installed=True,
        registration_changed=False,
        runtime_changed=False,
        prior_reachable=True,
    )

    with pytest.raises(RuntimeError, match="running state could not be determined"):
        _capture_prior_windows_install(
            _context(tmp_path),
            transaction,
            command_runner=None,
        )


@pytest.mark.parametrize("state_mutated", [False, True])
def test_windows_install_rollback_is_exactly_mutation_gated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    state_mutated: bool,
) -> None:
    rollback_calls: list[dict[str, object]] = []

    def restore(*_args: object, **kwargs: object) -> _RollbackOutcome:
        rollback_calls.append(kwargs)
        return _RollbackOutcome([], True)

    monkeypatch.setattr(install_module, "_restore_windows_state", restore)
    transaction = _WindowsInstallTransaction(
        prior_manifest=b"prior",
        installed=True,
        registration_changed=True,
        runtime_changed=False,
        prior_reachable=True,
        prior_task="<Task />",
        prior_active=True,
        state_mutated=state_mutated,
    )

    result = _failed_windows_install(
        _context(tmp_path),
        transaction,
        RuntimeError("installation failed"),
        command_runner=None,
    )

    assert len(rollback_calls) == int(state_mutated)
    assert result.get("rollback_succeeded") is (True if state_mutated else None)


@pytest.mark.parametrize(
    ("manifest_owned", "manifest_removed", "descriptor_removed", "changed"),
    [
        (False, False, False, False),
        (True, False, False, False),
        (True, True, False, True),
        (False, False, True, True),
        (True, True, True, True),
    ],
)
def test_not_installed_uninstall_state_table(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    manifest_owned: bool,
    manifest_removed: bool,
    descriptor_removed: bool,
    changed: bool,
) -> None:
    unlink_calls: list[Path] = []
    monkeypatch.setattr(
        lifecycle_module,
        "_manifest_owned",
        lambda _ctx: manifest_owned,
    )

    def unlink(path: Path, **_kwargs: object) -> bool:
        unlink_calls.append(path)
        return manifest_removed

    monkeypatch.setattr(lifecycle_module, "_safe_unlink", unlink)
    monkeypatch.setattr(
        lifecycle_module,
        "_cleanup_stale_runtime",
        lambda *_args: descriptor_removed,
    )

    result = _not_installed_uninstall(_context(tmp_path), None)

    assert result["ok"] is True
    assert result["status"] == "not_installed"
    assert result["changed"] is changed
    assert result["runtime_descriptor_removed"] is descriptor_removed
    assert len(unlink_calls) == int(manifest_owned)
