"""Lifecycle idempotency, failure, and rollback coverage."""

from __future__ import annotations

import pytest

from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_lifecycle as subject


def context(tmp_path, platform="linux"):
    result = core._context(
        home_dir=tmp_path,
        platform_name=platform,
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert result is not None
    return result


def command(name="command", *, code=0, stdout="", stderr=""):
    return core._CommandResult((name,), code, stdout, stderr)


def test_cleanup_stale_runtime_invalid_reachable_and_removed(tmp_path, monkeypatch):
    import agency_runtime.core.dashboard_runtime as runtime

    ctx = context(tmp_path)
    monkeypatch.setattr(
        runtime,
        "read_dashboard_runtime",
        lambda **_kw: (_ for _ in ()).throw(ValueError("invalid")),
    )
    assert not subject._cleanup_stale_runtime(ctx, None)
    descriptor = {"token": "token", "pid": 7}
    monkeypatch.setattr(runtime, "read_dashboard_runtime", lambda **_kw: descriptor)
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kw: True)
    assert not subject._cleanup_stale_runtime(ctx, None)
    removed = []
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kw: False)
    monkeypatch.setattr(
        runtime,
        "remove_dashboard_runtime",
        lambda **kwargs: removed.append(kwargs) or True,
    )
    assert subject._cleanup_stale_runtime(ctx, None)
    assert removed == [{"home_dir": ctx.home, "token": "token", "pid": 7}]


def test_lifecycle_preflight_unsupported_and_forwarding(tmp_path, monkeypatch):
    unsupported = subject._lifecycle_preflight(
        "start",
        home_dir=tmp_path,
        platform_name="darwin",
        config_path=None,
        python_executable=tmp_path / "python",
        command_runner=None,
    )
    assert unsupported[0] is None and unsupported[1]["supported"] is False
    ctx = context(tmp_path)
    monkeypatch.setattr(subject, "_context", lambda **_kw: ctx)
    monkeypatch.setattr(subject, "_preflight", lambda *_a, **_kw: (None, {"ok": True}))
    assert subject._lifecycle_preflight(
        "start",
        home_dir=tmp_path,
        platform_name="linux",
        config_path=None,
        python_executable=None,
        command_runner=None,
    ) == (ctx, None, {"ok": True})


@pytest.mark.parametrize(
    "operation",
    [
        subject.start_dashboard_service,
        subject.stop_dashboard_service,
        subject.restart_dashboard_service,
        subject.uninstall_dashboard_service,
    ],
)
def test_public_lifecycle_operations_reject_unsupported_platform(operation, tmp_path):
    result = operation(home_dir=tmp_path, platform_name="darwin")
    assert result["supported"] is False and result["exit_code"] == 2


@pytest.mark.parametrize(
    ("operation", "locked_name"),
    [
        (subject.start_dashboard_service, "_start_dashboard_service_locked"),
        (subject.stop_dashboard_service, "_stop_dashboard_service_locked"),
        (subject.restart_dashboard_service, "_restart_dashboard_service_locked"),
        (subject.uninstall_dashboard_service, "_uninstall_dashboard_service_locked"),
    ],
)
def test_public_lifecycle_operations_normalize_lock_errors(
    operation, locked_name, tmp_path, monkeypatch
):
    ctx = context(tmp_path)
    monkeypatch.setattr(subject, "_context", lambda **_kw: ctx)

    class Broken:
        def __enter__(self):
            raise OSError("lock failed")

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(subject, "_service_lock", lambda _ctx: Broken())
    monkeypatch.setattr(subject, locked_name, lambda **_kw: pytest.fail("called"))
    result = operation(platform_name="linux")
    assert not result["ok"] and result["error"] == "lock failed"


def test_start_preflight_not_installed_already_running_and_incomplete(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    blocked = {"ok": False, "error": "blocked"}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (ctx, blocked, {}))
    assert subject._start_dashboard_service_locked() is blocked
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (None, None, None))
    with pytest.raises(RuntimeError, match="incomplete state"):
        subject._start_dashboard_service_locked()
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": False}),
    )
    assert "not installed" in subject._start_dashboard_service_locked()["error"]
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": True, "reachable": True}),
    )
    assert subject._start_dashboard_service_locked()["status"] == "already_running"


@pytest.mark.parametrize(
    ("running", "message"),
    [(None, "could not be determined"), (True, "running but not reachable")],
)
def test_start_windows_refuses_indeterminate_or_unreachable_running_task(
    tmp_path, monkeypatch, running, message
):
    ctx = context(tmp_path, "windows")
    monkeypatch.setattr(subject, "_revalidate_dashboard_launcher", lambda *_a: None)
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (
            ctx,
            None,
            {"installed": True, "reachable": False, "definition_drift": False},
        ),
    )
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("xml", command("capture")),
    )
    monkeypatch.setattr(subject, "_windows_definition_matches", lambda *_a: True)
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (running, command("state")),
    )
    result = subject._start_dashboard_service_locked()
    assert message in result["error"]


def test_start_linux_command_selection_failure_and_readiness(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    state = {"installed": True, "reachable": False, "active": True}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (ctx, None, state))
    commands = []
    monkeypatch.setattr(
        subject,
        "_run",
        lambda argv, **_kw: commands.append(argv) or command(code=0),
    )
    result = subject._start_dashboard_service_locked(readiness_probe=lambda: False)
    assert not result["ok"] and "did not become ready" in result["error"]
    assert "restart" in commands[0]
    state["active"] = False
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    result = subject._start_dashboard_service_locked(readiness_probe=lambda: True)
    assert not result["ok"] and result["reachable"] is None


def test_stop_preflight_not_installed_idle_and_incomplete(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    blocked = {"ok": False}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (ctx, blocked, {}))
    assert subject._stop_dashboard_service_locked() is blocked
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (None, None, None))
    with pytest.raises(RuntimeError, match="incomplete state"):
        subject._stop_dashboard_service_locked()
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": False}),
    )
    assert subject._stop_dashboard_service_locked()["status"] == "not_installed"
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": True, "active": False}),
    )
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: True)
    idle = subject._stop_dashboard_service_locked()
    assert idle["status"] == "already_stopped" and idle["changed"]


def test_stop_windows_indeterminate_missing_capture_and_command_results(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": True}),
    )
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: (None, command("capture")),
    )
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (None, command("state")),
    )
    assert "could not be determined" in subject._stop_dashboard_service_locked()["error"]
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (True, command("state")),
    )
    with pytest.raises(RuntimeError, match="could not be captured"):
        subject._stop_dashboard_service_locked()
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("xml", command("capture")),
    )
    monkeypatch.setattr(subject, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: True)
    monkeypatch.setattr(
        subject,
        "_wait_windows_running_state",
        lambda *_a, **_kw: (True, [command("transition")]),
    )
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=0))
    assert subject._stop_dashboard_service_locked()["status"] == "stopped"
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    assert subject._stop_dashboard_service_locked()["status"] == "stop_failed"


def test_restart_preflight_linux_and_windows_failures(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "_revalidate_dashboard_launcher", lambda *_a: None)
    linux = context(tmp_path)
    blocked = {"ok": False}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (linux, blocked, {}))
    assert subject._restart_dashboard_service_locked() is blocked
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (None, None, None))
    with pytest.raises(RuntimeError, match="incomplete state"):
        subject._restart_dashboard_service_locked()
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (linux, None, {"installed": False}),
    )
    assert "not installed" in subject._restart_dashboard_service_locked()["error"]
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (linux, None, {"installed": True}),
    )
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=0))
    result = subject._restart_dashboard_service_locked(readiness_probe=lambda: False)
    assert "did not become ready" in result["error"]

    windows = context(tmp_path, "windows")
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (
            windows,
            None,
            {"installed": True, "definition_drift": False},
        ),
    )
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("xml", command("capture")),
    )
    monkeypatch.setattr(subject, "_windows_definition_matches", lambda *_a: True)
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (None, command("state")),
    )
    assert "could not be determined" in subject._restart_dashboard_service_locked()["error"]
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (True, command("state")),
    )
    monkeypatch.setattr(subject, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    assert "stop before restart failed" in subject._restart_dashboard_service_locked()["error"]


def test_windows_lifecycle_transition_and_generation_failures(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    state = {"installed": True, "reachable": False, "definition_drift": False}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (ctx, None, state))
    monkeypatch.setattr(subject, "_revalidate_dashboard_launcher", lambda *_a: None)
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("xml", command("capture")),
    )
    monkeypatch.setattr(subject, "_windows_definition_matches", lambda *_a: True)
    monkeypatch.setattr(subject, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(subject, "_dashboard_runtime_fingerprint", lambda *_a: "prior")
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: False)
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command())

    monkeypatch.setattr(subject, "_windows_running_state", lambda **_kw: (False, command()))
    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", lambda *_a, **_kw: False)
    assert "remained reachable before start" in subject._start_dashboard_service_locked()["error"]

    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", lambda *_a, **_kw: True)
    monkeypatch.setattr(
        subject,
        "_wait_windows_running_state",
        lambda *_a, **_kw: (False, [command("transition")]),
    )
    assert "did not enter the running state" in subject._start_dashboard_service_locked()["error"]

    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", lambda *_a, **_kw: False)
    assert "runtime remains reachable" in subject._stop_dashboard_service_locked()["error"]

    monkeypatch.setattr(subject, "_windows_running_state", lambda **_kw: (True, command()))
    stopped = subject._stop_dashboard_service_locked()
    assert "did not reach the idle state" in stopped["error"] and stopped["changed"]

    monkeypatch.setattr(
        subject,
        "_wait_windows_running_state",
        lambda *_a, **_kw: (True, [command("transition")]),
    )
    stopped = subject._stop_dashboard_service_locked()
    assert "runtime remained reachable" in stopped["error"] and stopped["changed"]

    monkeypatch.setattr(
        subject,
        "_wait_windows_running_state",
        lambda *_a, **_kw: (False, [command("transition")]),
    )
    restarted = subject._restart_dashboard_service_locked()
    assert "did not reach the idle state" in restarted["error"] and restarted["changed"]

    monkeypatch.setattr(subject, "_windows_running_state", lambda **_kw: (False, command()))
    restarted = subject._restart_dashboard_service_locked()
    assert "old dashboard runtime remained" in restarted["error"]
    assert restarted["changed"] is False

    monkeypatch.setattr(subject, "_dashboard_runtime_cleared", lambda *_a, **_kw: True)
    restarted = subject._restart_dashboard_service_locked()
    assert "did not enter the running state" in restarted["error"]

    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    restarted = subject._restart_dashboard_service_locked()
    assert restarted["ok"] is False


def test_not_installed_uninstall_manifest_and_descriptor(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    monkeypatch.setattr(subject, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(subject, "_safe_unlink", lambda *_a, **_kw: True)
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: True)
    result = subject._not_installed_uninstall(ctx, None)
    assert result["changed"] and result["runtime_descriptor_removed"]
    monkeypatch.setattr(subject, "_manifest_owned", lambda _ctx: False)
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: False)
    assert not subject._not_installed_uninstall(ctx, None)["changed"]


def test_systemd_uninstall_preconditions_and_command_failures(tmp_path, monkeypatch):
    windows = context(tmp_path, "windows")
    with pytest.raises(RuntimeError, match="no unit path"):
        subject._systemd_uninstall_transaction(windows, {})
    transaction = subject._SystemdUninstallTransaction(
        prior_unit=b"unit",
        prior_manifest=b"manifest",
        expected_unit=b"unit",
        expected_manifest=b"manifest",
        prior_enabled=True,
        prior_active=True,
    )
    with pytest.raises(RuntimeError, match="no unit path"):
        subject._perform_systemd_uninstall(windows, transaction, command_runner=None)
    linux = context(tmp_path)
    monkeypatch.setattr(subject, "_decode_service_file", lambda _raw: "unowned")
    with pytest.raises(RuntimeError, match="ownership marker"):
        subject._perform_systemd_uninstall(linux, transaction, command_runner=None)
    monkeypatch.setattr(subject, "_decode_service_file", lambda _raw: f"# {core.OWNER_MARKER}\n")
    monkeypatch.setattr(subject, "_manifest_owned", lambda _ctx: False)
    with pytest.raises(RuntimeError, match="manifest changed"):
        subject._perform_systemd_uninstall(linux, transaction, command_runner=None)
    monkeypatch.setattr(subject, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(subject, "_assert_systemd_files", lambda *_a, **_kw: None)
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    with pytest.raises(RuntimeError, match="disable --now failed"):
        subject._perform_systemd_uninstall(linux, transaction, command_runner=None)


def test_windows_uninstall_running_and_command_failures(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    transaction = subject._WindowsUninstallTransaction(prior_manifest=None)
    monkeypatch.setattr(
        subject,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("xml", command("capture")),
    )
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (None, command("state")),
    )
    with pytest.raises(RuntimeError, match="could not be determined"):
        subject._perform_windows_uninstall(ctx, transaction, command_runner=None)
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (True, command("state")),
    )
    monkeypatch.setattr(subject, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(subject, "_run", lambda *_a, **_kw: command(code=1))
    with pytest.raises(RuntimeError, match="scheduled-task stop failed"):
        subject._perform_windows_uninstall(ctx, transaction, command_runner=None)
    monkeypatch.setattr(
        subject,
        "_windows_running_state",
        lambda **_kw: (False, command("state")),
    )
    with pytest.raises(RuntimeError, match="deletion failed"):
        subject._perform_windows_uninstall(ctx, transaction, command_runner=None)


def test_uninstall_locked_blocked_incomplete_not_installed_and_outcomes(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    blocked = {"ok": False}
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (ctx, blocked, {}))
    assert subject._uninstall_dashboard_service_locked() is blocked
    monkeypatch.setattr(subject, "_lifecycle_preflight", lambda *_a, **_kw: (None, None, None))
    with pytest.raises(RuntimeError, match="incomplete state"):
        subject._uninstall_dashboard_service_locked()
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": False}),
    )
    monkeypatch.setattr(
        subject, "_not_installed_uninstall", lambda *_a: {"status": "not_installed"}
    )
    assert subject._uninstall_dashboard_service_locked()["status"] == "not_installed"
    monkeypatch.setattr(
        subject,
        "_lifecycle_preflight",
        lambda *_a, **_kw: (ctx, None, {"installed": True}),
    )
    failure = {"ok": False, "error": "failed"}
    monkeypatch.setattr(subject, "_uninstall_systemd_service", lambda *_a, **_kw: failure)
    assert subject._uninstall_dashboard_service_locked() is failure
    monkeypatch.setattr(subject, "_uninstall_systemd_service", lambda *_a, **_kw: [command()])
    monkeypatch.setattr(subject, "_cleanup_stale_runtime", lambda *_a: True)
    success = subject._uninstall_dashboard_service_locked()
    assert success["ok"] and success["runtime_descriptor_removed"]
