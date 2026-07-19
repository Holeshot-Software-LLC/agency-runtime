"""Planning, inspection, and installation transaction coverage."""

from __future__ import annotations

import pytest

from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_inspection as inspection
from agency_runtime.core import dashboard_service_install as install


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


def test_manager_probe_suppression_linux_and_windows(tmp_path, monkeypatch):
    linux = context(tmp_path)
    assert inspection._manager_probe(linux, home_dir=tmp_path, command_runner=None) == (
        None,
        None,
        None,
    )
    monkeypatch.setattr(inspection, "_run", lambda *_a, **_kw: command())
    available, probe, state = inspection._manager_probe(
        linux,
        home_dir=None,
        command_runner=lambda *_a, **_kw: {"returncode": 0},
    )
    assert available is True and probe is not None and state is None
    windows = context(tmp_path, "windows")
    monkeypatch.setattr(
        inspection,
        "_query_windows_registration",
        lambda **_kw: ("unavailable", command(code=127)),
    )
    assert (
        inspection._manager_probe(windows, home_dir=None, command_runner=lambda *_a: None)[0]
        is False
    )


def test_linux_unit_path_read_and_plan_states(tmp_path, monkeypatch):
    windows = context(tmp_path, "windows")
    with pytest.raises(RuntimeError, match="no unit path"):
        inspection._linux_unit_path(windows)
    linux = context(tmp_path)
    snapshot = inspection._read_linux_unit(linux)
    assert not snapshot.exists and snapshot.readable
    monkeypatch.setattr(inspection, "_path_present", lambda _path: True)
    monkeypatch.setattr(
        inspection,
        "_read_systemd_unit",
        lambda _ctx: (_ for _ in ()).throw(OSError("unreadable")),
    )
    snapshot = inspection._read_linux_unit(linux)
    assert snapshot.exists and not snapshot.readable
    registration = inspection._linux_plan_registration(linux)
    assert registration.state_indeterminate and registration.commands == []


def test_windows_plan_registration_indeterminate_unowned_and_owned(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    monkeypatch.setattr(inspection, "_path_present", lambda _path: False)
    indeterminate = inspection._windows_plan_registration(ctx, probe=None, registration_state=None)
    assert indeterminate.state_indeterminate and not indeterminate.commands
    unowned = inspection._windows_plan_registration(
        ctx, probe=command(stdout="unowned"), registration_state="present"
    )
    assert unowned.ownership_blocked
    monkeypatch.setattr(inspection, "_windows_xml_owned", lambda _xml: True)
    monkeypatch.setattr(inspection, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(inspection, "_windows_definition_matches", lambda *_args: False)
    owned = inspection._windows_plan_registration(
        ctx, probe=command(stdout="owned"), registration_state="present"
    )
    assert owned.definition_drift is True and owned.commands[0][-1] == "/F"
    assert (
        inspection._plan_registration(
            ctx, probe=command(stdout="owned"), registration_state="present"
        )
        == owned
    )


@pytest.mark.parametrize(
    ("available", "blocked", "indeterminate", "platform", "code", "ready"),
    [
        (True, False, True, "linux", 1, False),
        (True, True, False, "linux", 1, False),
        (False, False, False, "linux", 1, False),
        (False, False, False, "windows", 1, False),
        (None, False, False, "linux", 0, False),
        (True, False, False, "linux", 0, True),
    ],
)
def test_plan_disposition_truth_table(available, blocked, indeterminate, platform, code, ready):
    value = inspection._plan_disposition(
        available=available,
        ownership_blocked=blocked,
        state_indeterminate=indeterminate,
        platform_name=platform,
    )
    assert value.exit_code == code and value.ready_to_install is ready


def test_render_plan_includes_probe_error_and_warning(tmp_path):
    ctx = context(tmp_path)
    registration = inspection._PlanRegistration(
        registration_path="unit",
        registration_content="content",
        commands=[],
        ownership_blocked=False,
        state_indeterminate=False,
        definition_drift=None,
    )
    unavailable = inspection._render_plan(
        ctx,
        available=False,
        probe=command(code=1, stderr="offline"),
        registration=registration,
    )
    assert unavailable["manager_probe"]["ok"] is False
    assert "unavailable" in unavailable["error"]
    suppressed = inspection._render_plan(ctx, available=None, probe=None, registration=registration)
    assert "warning" in suppressed


def test_plan_and_inspect_unsupported(tmp_path):
    assert (
        inspection.plan_dashboard_service(home_dir=tmp_path, platform_name="darwin")["supported"]
        is False
    )


def test_inspect_reports_launcher_validation_failure(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    monkeypatch.setattr(
        inspection,
        "_validate_dashboard_launcher",
        lambda _ctx: (_ for _ in ()).throw(OSError("launcher identity unavailable")),
    )

    result = inspection.inspect_dashboard_service(_ctx=ctx, _validate_launcher=True)

    assert result["ok"] is False
    assert result["error"] == "launcher identity unavailable"
    assert (
        inspection.inspect_dashboard_service(home_dir=tmp_path, platform_name="darwin")["supported"]
        is False
    )


def test_inspection_registration_linux_and_windows(tmp_path, monkeypatch):
    linux = context(tmp_path)
    monkeypatch.setattr(
        inspection,
        "_read_linux_unit",
        lambda _ctx: inspection._LinuxUnitSnapshot(
            exists=True,
            content=f"# {core.OWNER_MARKER}\nchanged",
            readable=True,
        ),
    )
    results = iter([command(stdout="enabled"), command(stdout="active")])
    monkeypatch.setattr(inspection, "_run", lambda *_a, **_kw: next(results))
    value = inspection._linux_inspection_registration(
        linux, available=True, command_runner=None, manifest_owned=True
    )
    assert value.installed and value.owned and value.definition_drift
    assert value.enabled is True and value.active is True
    assert (
        inspection._linux_inspection_registration(
            linux, available=False, command_runner=None, manifest_owned=False
        ).active
        is None
    )

    assert inspection._windows_installed_state("present") is True
    assert inspection._windows_installed_state("absent") is False
    assert inspection._windows_installed_state(None) is None
    windows = context(tmp_path, "windows")
    monkeypatch.setattr(inspection, "_windows_xml_owned", lambda _xml: True)
    monkeypatch.setattr(inspection, "_windows_definition_matches", lambda *_args: False)
    monkeypatch.setattr(
        inspection,
        "_windows_task_properties",
        lambda _xml: {"enabled": "true"},
    )
    value = inspection._windows_inspection_registration(
        windows,
        probe=command(stdout="xml"),
        registration_state="present",
        manifest_owned=True,
    )
    assert value.owned and value.enabled and value.definition_drift
    assert inspection._inspection_registration(
        windows,
        available=True,
        probe=command(stdout="xml"),
        registration_state="present",
        command_runner=None,
        manifest_owned=True,
    ).installed


def test_probe_selection_readiness_and_failed_payload(tmp_path):
    def first():
        return True

    assert (
        inspection._select_immediate_probe(reachability_probe=first, readiness_probe=None) is first
    )
    assert (
        inspection._select_immediate_probe(reachability_probe=None, readiness_probe=first) is first
    )
    with pytest.raises(ValueError, match="not both"):
        inspection._select_immediate_probe(reachability_probe=first, readiness_probe=first)
    assert inspection._readiness(None) is None
    assert inspection._readiness(lambda: 1) is True
    assert inspection._readiness(lambda: (_ for _ in ()).throw(RuntimeError("offline"))) is False
    ctx = context(tmp_path)
    rollback = core._RollbackOutcome(
        commands=[{"command": ["rollback"]}], succeeded=False, error="failed"
    )
    failed = inspection._failed("install", ctx, error="failure", commands=[], rollback=rollback)
    assert failed["rollback_succeeded"] is False
    assert failed["rollback_error"] == "failed"


@pytest.mark.parametrize(
    "state",
    [
        {"manager_available": False},
        {"manager_available": True, "installed": None},
        {
            "manager_available": True,
            "installed": True,
            "enabled": None,
            "active": True,
            "owned": True,
        },
        {"manager_available": True, "installed": True, "owned": False},
        {
            "manager_available": True,
            "installed": False,
            "manifest_owned": False,
        },
    ],
)
def test_preflight_blocks_indeterminate_unowned_and_invalid_manifest(tmp_path, monkeypatch, state):
    ctx = context(tmp_path)
    monkeypatch.setattr(inspection, "inspect_dashboard_service", lambda **_kw: state)
    monkeypatch.setattr(inspection, "_path_present", lambda _path: True)
    blocked, returned = inspection._preflight(
        "install",
        ctx,
        home_dir=tmp_path,
        command_runner=lambda *_a: None,
    )
    assert returned is state and blocked is not None and not blocked["ok"]


def test_install_public_unsupported_and_lock_error(tmp_path, monkeypatch):
    assert (
        install.install_dashboard_service(home_dir=tmp_path, platform_name="darwin")["supported"]
        is False
    )
    ctx = context(tmp_path)
    monkeypatch.setattr(install, "_context", lambda **_kw: ctx)

    class BrokenLock:
        def __enter__(self):
            raise OSError("lock failed")

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(install, "_service_lock", lambda _ctx: BrokenLock())
    result = install.install_dashboard_service(platform_name="linux")
    assert not result["ok"] and result["error"] == "lock failed"


def test_install_linux_missing_unit_invalid_utf8_and_ownership(tmp_path, monkeypatch):
    monkeypatch.setattr(install, "_revalidate_dashboard_launcher", lambda *_a: None)
    windows = context(tmp_path, "windows")
    with pytest.raises(RuntimeError, match="no unit path"):
        install._install_linux(windows, {}, command_runner=None, readiness_probe=None)
    ctx = context(tmp_path)
    assert ctx.unit_path is not None
    monkeypatch.setattr(install, "_path_present", lambda _path: True)
    monkeypatch.setattr(install, "_read_systemd_unit", lambda _ctx: b"\xff")
    monkeypatch.setattr(install, "_read_manifest_bytes", lambda _ctx: None)
    assert (
        "valid UTF-8"
        in install._install_linux(ctx, {}, command_runner=None, readiness_probe=None)["error"]
    )
    monkeypatch.setattr(install, "_read_systemd_unit", lambda _ctx: b"unowned")
    monkeypatch.setattr(install, "_manifest_owned", lambda _ctx: False)
    assert (
        "ownership changed"
        in install._install_linux(ctx, {}, command_runner=None, readiness_probe=None)["error"]
    )


@pytest.mark.parametrize(
    ("failure_command", "state", "expected"),
    [
        ("daemon-reload", {}, "daemon-reload failed"),
        ("enable", {}, "enable --now failed"),
        (
            "restart",
            {
                "manifest_current": False,
                "enabled": True,
                "active": True,
                "reachable": True,
            },
            "restart after update failed",
        ),
    ],
)
def test_install_linux_command_failures(tmp_path, monkeypatch, failure_command, state, expected):
    ctx = context(tmp_path)
    monkeypatch.setattr(install, "_path_present", lambda _path: False)
    monkeypatch.setattr(install, "_read_manifest_bytes", lambda _ctx: None)
    monkeypatch.setattr(install, "_atomic_write", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_write_manifest", lambda _ctx: True)
    monkeypatch.setattr(install, "_assert_systemd_files", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        install,
        "_run",
        lambda argv, **_kw: command(
            argv[2] if len(argv) > 2 else "command",
            code=1 if failure_command in argv else 0,
        ),
    )
    monkeypatch.setattr(
        install,
        "_restore_systemd_state",
        lambda *_a, **_kw: core._RollbackOutcome([], True),
    )
    result = install._install_linux(ctx, state, command_runner=None, readiness_probe=lambda: True)
    assert expected in result["error"] and result["rollback_succeeded"]


def test_install_linux_readiness_failure_and_idempotent_success(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    desired = install._unit_content(ctx).encode()
    monkeypatch.setattr(install, "_path_present", lambda _path: True)
    monkeypatch.setattr(install, "_read_systemd_unit", lambda _ctx: desired)
    monkeypatch.setattr(install, "_read_manifest_bytes", lambda _ctx: b"manifest")
    monkeypatch.setattr(install, "_manifest_owned", lambda _ctx: True)
    monkeypatch.setattr(install, "_write_manifest", lambda _ctx: False)
    monkeypatch.setattr(install, "_assert_systemd_files", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_run", lambda *_a, **_kw: command())
    monkeypatch.setattr(
        install,
        "_restore_systemd_state",
        lambda *_a, **_kw: core._RollbackOutcome([], True),
    )
    base = {
        "manifest_current": True,
        "enabled": True,
        "active": True,
        "reachable": True,
    }
    result = install._install_linux(ctx, base, command_runner=None, readiness_probe=lambda: True)
    assert result["ok"] and not result["changed"] and result["commands"] == []
    result = install._install_linux(
        ctx,
        {**base, "reachable": False},
        command_runner=None,
        readiness_probe=lambda: False,
    )
    assert not result["ok"] and "did not become ready" in result["error"]


def test_windows_install_helper_failures_and_success(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    monkeypatch.setattr(install, "_read_manifest_bytes", lambda _ctx: b"manifest")
    transaction = install._windows_install_transaction(
        ctx,
        {
            "installed": True,
            "definition_drift": True,
            "manifest_current": False,
            "reachable": False,
        },
    )
    monkeypatch.setattr(
        install,
        "_export_owned_windows_task",
        lambda *_a, **_kw: ("prior", command("capture")),
    )
    monkeypatch.setattr(
        install,
        "_windows_running_state",
        lambda **_kw: (None, command("state")),
    )
    with pytest.raises(RuntimeError, match="could not be determined"):
        install._capture_prior_windows_install(ctx, transaction, command_runner=None)
    transaction.installed = True
    transaction.registration_changed = True
    transaction.prior_task = None
    with pytest.raises(RuntimeError, match="could not be captured"):
        install._register_windows_install(ctx, transaction, command_runner=None)

    transaction.prior_task = "prior"
    monkeypatch.setattr(install, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(
        install,
        "_register_windows_xml",
        lambda *_a, **_kw: command(code=1),
    )
    with pytest.raises(RuntimeError, match="creation failed"):
        install._register_windows_install(ctx, transaction, command_runner=None)
    monkeypatch.setattr(install, "_write_manifest", lambda _ctx: True)
    monkeypatch.setattr(
        install,
        "_capture_owned_windows_task",
        lambda *_a, **_kw: ("current", command()),
    )
    monkeypatch.setattr(install, "_windows_definition_matches", lambda *_args: False)
    with pytest.raises(RuntimeError, match="verification failed"):
        install._write_and_verify_windows_install(ctx, transaction, command_runner=None)


def test_windows_restart_activate_and_final_verification_failures(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    transaction = install._WindowsInstallTransaction(
        prior_manifest=None,
        installed=True,
        registration_changed=True,
        runtime_changed=False,
        prior_reachable=True,
        prior_active=True,
        changed=True,
    )
    monkeypatch.setattr(install, "_assert_windows_task_unchanged", lambda *_a, **_kw: command())
    monkeypatch.setattr(install, "_run", lambda *_a, **_kw: command(code=1))
    with pytest.raises(RuntimeError, match="stop before restart failed"):
        install._restart_windows_install_if_needed(ctx, transaction, "current", command_runner=None)
    with pytest.raises(RuntimeError, match="start failed"):
        install._activate_windows_install_if_needed(
            ctx, transaction, "current", command_runner=None
        )
    monkeypatch.setattr(install, "_run", lambda *_a, **_kw: command())
    monkeypatch.setattr(
        install,
        "_wait_windows_running_state",
        lambda *_a, **_kw: (False, [command("transition")]),
    )
    with pytest.raises(RuntimeError, match="idle state"):
        install._restart_windows_install_if_needed(ctx, transaction, "current", command_runner=None)
    monkeypatch.setattr(
        install,
        "_wait_dashboard_runtime_cleared",
        lambda *_a, **_kw: core._DashboardRuntimeClearance(False, False),
    )
    with pytest.raises(RuntimeError, match="old dashboard runtime"):
        install._activate_windows_install_if_needed(
            ctx, transaction, "current", command_runner=None
        )
    monkeypatch.setattr(
        install,
        "_wait_dashboard_runtime_cleared",
        lambda *_a, **_kw: core._DashboardRuntimeClearance(
            False,
            False,
            replacement_detected=True,
        ),
    )
    with pytest.raises(RuntimeError, match="generation changed"):
        install._activate_windows_install_if_needed(
            ctx, transaction, "current", command_runner=None
        )
    monkeypatch.setattr(
        install,
        "_wait_dashboard_runtime_cleared",
        lambda *_a, **_kw: core._DashboardRuntimeClearance(True, False),
    )
    with pytest.raises(RuntimeError, match="running state"):
        install._activate_windows_install_if_needed(
            ctx, transaction, "current", command_runner=None
        )
    with pytest.raises(RuntimeError, match="did not become ready"):
        install._verify_final_windows_install(
            ctx,
            transaction,
            command_runner=None,
            readiness_probe=lambda: False,
        )
    transaction.changed = False
    transaction.prior_reachable = True
    monkeypatch.setattr(
        install,
        "_capture_owned_windows_task",
        lambda *_a, **_kw: ("changed", command()),
    )
    monkeypatch.setattr(install, "_windows_definition_matches", lambda *_args: False)
    with pytest.raises(RuntimeError, match="changed after activation"):
        install._verify_final_windows_install(
            ctx, transaction, command_runner=None, readiness_probe=None
        )


def test_windows_install_activation_waits_for_worker_generation_clearance(
    tmp_path,
    monkeypatch,
):
    ctx = context(tmp_path, "windows")
    transaction = install._WindowsInstallTransaction(
        prior_manifest=None,
        installed=True,
        registration_changed=True,
        runtime_changed=True,
        prior_reachable=True,
        prior_active=True,
        changed=True,
        prior_runtime_fingerprint="sha256:old",
    )
    cleanup_calls = []

    def pending_cleanup(_ctx, **_kwargs):
        cleanup_calls.append("cleanup")
        return False

    monkeypatch.setattr(
        core,
        "_cleanup_stale_dashboard_runtime",
        pending_cleanup,
    )
    monkeypatch.setattr(
        core,
        "_dashboard_runtime_fingerprint",
        lambda _ctx: "sha256:old",
    )
    monkeypatch.setattr(
        core,
        "_dashboard_runtime_cleared",
        lambda *_args, **_kwargs: len(cleanup_calls) >= 3,
    )
    monkeypatch.setattr(core.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        install,
        "_assert_windows_task_unchanged",
        lambda *_args, **_kwargs: command("exact"),
    )
    monkeypatch.setattr(install, "_run", lambda *_args, **_kwargs: command("run"))
    monkeypatch.setattr(
        install,
        "_wait_windows_running_state",
        lambda *_args, **_kwargs: (True, [command("state")]),
    )

    install._activate_windows_install_if_needed(
        ctx,
        transaction,
        "current-task",
        command_runner=None,
    )

    assert cleanup_calls == ["cleanup", "cleanup", "cleanup"]
    assert [item["command"][0] for item in transaction.commands] == ["exact", "run", "state"]


def test_failed_windows_install_rolls_back_only_after_mutation(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    transaction = install._WindowsInstallTransaction(
        prior_manifest=None,
        installed=False,
        registration_changed=True,
        runtime_changed=True,
        prior_reachable=False,
    )
    monkeypatch.setattr(
        install,
        "_restore_windows_state",
        lambda *_a, **_kw: core._RollbackOutcome([], True),
    )
    result = install._failed_windows_install(
        ctx, transaction, RuntimeError("before mutation"), command_runner=None
    )
    assert "rollback_succeeded" not in result
    transaction.state_mutated = True
    result = install._failed_windows_install(
        ctx, transaction, RuntimeError("after mutation"), command_runner=None
    )
    assert result["rollback_succeeded"] is True


def test_install_windows_success_and_error_wrapper(tmp_path, monkeypatch):
    monkeypatch.setattr(install, "_revalidate_dashboard_launcher", lambda *_a: None)
    ctx = context(tmp_path, "windows")
    transaction = install._WindowsInstallTransaction(
        prior_manifest=None,
        installed=False,
        registration_changed=True,
        runtime_changed=True,
        prior_reachable=False,
        changed=True,
        reachable=True,
    )
    monkeypatch.setattr(install, "_windows_install_transaction", lambda *_a: transaction)
    monkeypatch.setattr(install, "_capture_prior_windows_install", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_register_windows_install", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_write_and_verify_windows_install", lambda *_a, **_kw: "current")
    monkeypatch.setattr(install, "_restart_windows_install_if_needed", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_activate_windows_install_if_needed", lambda *_a, **_kw: None)
    monkeypatch.setattr(install, "_verify_final_windows_install", lambda *_a, **_kw: None)
    assert install._install_windows(ctx, {}, command_runner=None, readiness_probe=None)["ok"]
    monkeypatch.setattr(
        install,
        "_capture_prior_windows_install",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("capture failed")),
    )
    monkeypatch.setattr(
        install,
        "_failed_windows_install",
        lambda *_a, **_kw: {"ok": False, "error": "capture failed"},
    )
    assert not install._install_windows(ctx, {}, command_runner=None, readiness_probe=None)["ok"]
