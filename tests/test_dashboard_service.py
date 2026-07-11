"""Deterministic platform-contract tests for the dashboard user service."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.dashboard_service import (
    OWNER_ID,
    OWNER_MARKER,
    SYSTEMD_UNIT_NAME,
    build_service_worker_argv,
    inspect_dashboard_service,
    install_dashboard_service,
    plan_dashboard_service,
    restart_dashboard_service,
    start_dashboard_service,
    stop_dashboard_service,
    uninstall_dashboard_service,
)


class FakeSystemd:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.enabled = False
        self.active = False
        self.ambiguous_status = False
        self.missing_unit_status = False
        self.commands: list[list[str]] = []
        self.fail_once: set[tuple[str, ...]] = set()

    def __call__(self, argv: list[str], **_kwargs: Any) -> dict[str, Any]:
        self.commands.append(list(argv))
        assert argv[:2] == ["systemctl", "--user"]
        operation = argv[2:]
        operation_key = tuple(operation)
        if operation_key in self.fail_once:
            self.fail_once.remove(operation_key)
            return {"returncode": 1, "stderr": "injected systemd failure"}
        if operation == ["show-environment"]:
            return {"returncode": 0 if self.available else 1, "stderr": "no user bus"}
        if operation == ["is-enabled", SYSTEMD_UNIT_NAME]:
            if self.ambiguous_status:
                return {"returncode": 1}
            if self.missing_unit_status:
                return {"returncode": 4, "stdout": "not-found\n"}
            return {
                "returncode": 0 if self.enabled else 1,
                "stdout": "enabled\n" if self.enabled else "disabled\n",
            }
        if operation == ["is-active", SYSTEMD_UNIT_NAME]:
            if self.ambiguous_status:
                return {"returncode": 3}
            return {
                "returncode": 0 if self.active else 3,
                "stdout": "active\n" if self.active else "inactive\n",
            }
        if operation == ["daemon-reload"]:
            return {"returncode": 0}
        if operation == ["enable", "--now", SYSTEMD_UNIT_NAME]:
            self.enabled = True
            self.active = True
            return {"returncode": 0}
        if operation == ["enable", SYSTEMD_UNIT_NAME]:
            self.enabled = True
            return {"returncode": 0}
        if operation == ["disable", SYSTEMD_UNIT_NAME]:
            self.enabled = False
            return {"returncode": 0}
        if operation == ["disable", "--now", SYSTEMD_UNIT_NAME]:
            self.enabled = False
            self.active = False
            return {"returncode": 0}
        if operation == ["start", SYSTEMD_UNIT_NAME]:
            self.active = True
            return {"returncode": 0}
        if operation == ["stop", SYSTEMD_UNIT_NAME]:
            self.active = False
            return {"returncode": 0}
        if operation == ["restart", SYSTEMD_UNIT_NAME]:
            self.active = True
            return {"returncode": 0}
        raise AssertionError(f"unexpected systemctl command: {argv}")


class FakeTaskScheduler:
    def __init__(self, *, task_exists: bool = False, task_xml: str = "") -> None:
        self.task_exists = task_exists
        self.active = False
        self.action = ""
        self.task_xml = task_xml or (
            "<Task><RegistrationInfo><Description>unowned task</Description>"
            "</RegistrationInfo></Task>"
        )
        self.commands: list[list[str]] = []
        self.create_count = 0
        self.restore_count = 0
        self.fail_delete_once = False
        self.fail_end_once = False
        self.fail_run_once = False

    def __call__(self, argv: list[str], **_kwargs: Any) -> dict[str, Any]:
        self.commands.append(list(argv))
        if argv[0] == "powershell.exe":
            assert argv[1:4] == ["-NoProfile", "-NonInteractive", "-Command"]
            assert len(argv) == 5
            assert "Schedule.Service" in argv[4]
            if not self.task_exists:
                return {"returncode": 0, "stdout": "ABSENT"}
            state = "4" if self.active else "3"
            return {"returncode": 0, "stdout": f"PRESENT:{state}"}
        assert argv[0] == "schtasks.exe"
        operation = argv[1]
        if operation == "/Query":
            if not self.task_exists:
                return {
                    "returncode": 1,
                    "stderr": "ERROR: The system cannot find the file specified.",
                }
            if "/XML" in argv:
                return {
                    "returncode": 0,
                    "stdout": self.task_xml,
                }
            if "/FO" in argv and argv[argv.index("/FO") + 1] == "LIST":
                status = "Running" if self.active else "Ready"
                return {"returncode": 0, "stdout": f"Status: {status}\n"}
            raise AssertionError(f"unexpected task query: {argv}")
        if operation == "/Create":
            if "/XML" in argv:
                content = Path(argv[argv.index("/XML") + 1]).read_text(encoding="utf-8")
                if self.task_exists:
                    self.restore_count += 1
                self.create_count += 1
                self.task_exists = True
                self.task_xml = content
                self.action = content
                return {"returncode": 0}
            raise AssertionError("dashboard tasks must be registered from explicit XML")
        if operation == "/Run":
            if self.fail_run_once:
                self.fail_run_once = False
                return {"returncode": 1, "stderr": "injected start failure"}
            if not self.task_exists:
                return {"returncode": 1, "stderr": "task does not exist"}
            self.active = True
            return {"returncode": 0}
        if operation == "/End":
            if self.fail_end_once:
                self.fail_end_once = False
                return {"returncode": 1, "stderr": "injected stop failure"}
            if not self.task_exists or not self.active:
                return {"returncode": 1, "stderr": "task is not running"}
            self.active = False
            return {"returncode": 0}
        if operation == "/Delete":
            if self.fail_delete_once:
                self.fail_delete_once = False
                return {"returncode": 1, "stderr": "injected delete failure"}
            if not self.task_exists:
                return {"returncode": 1, "stderr": "task does not exist"}
            self.task_exists = False
            self.active = False
            return {"returncode": 0}
        raise AssertionError(f"unexpected schtasks command: {argv}")


def _paths(tmp_path: Path) -> tuple[Path, Path]:
    python = tmp_path / "Python Runtime" / "python.exe"
    config = tmp_path / "config $% space" / "agency.yaml"
    return python, config


def test_worker_argv_is_exact_strict_and_credential_free(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    argv = build_service_worker_argv(
        home_dir=tmp_path,
        config_path=config,
        python_executable=python,
    )

    assert argv == [
        str(python.resolve()),
        "-m",
        "agency_runtime.cli",
        "dashboard",
        "--service-mode",
        "--config",
        str(config.resolve()),
    ]
    assert "token" not in json.dumps(argv).lower()

    with pytest.raises(ValueError, match="control character"):
        build_service_worker_argv(
            home_dir=tmp_path,
            config_path=config,
            python_executable=f"{python}\n--unsafe",
        )


def test_linux_plan_quotes_systemd_specifiers_and_writes_nothing(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()

    plan = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config,
        python_executable=python,
        command_runner=manager,
    )

    assert plan["ok"] is True
    assert plan["manager_available"] is True
    assert plan["dry_run"] is True
    assert plan["commands"] == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME],
    ]
    unit = plan["registration_content"]
    assert unit.startswith(f"# {OWNER_MARKER}\n")
    assert '"agency_runtime.cli"' in unit
    assert '"--service-mode"' in unit
    assert "$$" in unit
    assert "%%" in unit
    serialized_plan = json.dumps(plan).lower()
    assert "bearer " not in serialized_plan
    assert "#token=" not in serialized_plan
    assert not (tmp_path / ".config").exists()
    assert manager.commands == [["systemctl", "--user", "show-environment"]]


def test_linux_plan_reports_unavailable_or_suppressed_user_manager(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    unavailable = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config,
        python_executable=python,
        command_runner=FakeSystemd(available=False),
    )
    assert unavailable["ok"] is False
    assert unavailable["manager_available"] is False
    assert "systemd user manager is unavailable" in unavailable["error"]
    assert not (tmp_path / ".config").exists()

    suppressed = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config,
        python_executable=python,
    )
    assert suppressed["ok"] is True
    assert suppressed["manager_available"] is None
    assert suppressed["ready_to_install"] is False


def test_linux_plan_refuses_unowned_unit_and_reports_owned_drift(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    unowned_home = tmp_path / "unowned"
    unowned_unit = unowned_home / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    unowned_unit.parent.mkdir(parents=True)
    unowned_unit.write_text("[Service]\nExecStart=/unrelated\n", encoding="utf-8")
    refused = plan_dashboard_service(
        home_dir=unowned_home,
        platform_name="linux",
        config_path=config,
        python_executable=python,
        command_runner=FakeSystemd(),
    )
    assert refused["ok"] is False
    assert refused["ready_to_install"] is False
    assert refused["commands"] == []
    assert "refusing to overwrite" in refused["error"]

    owned_home = tmp_path / "owned"
    manager = FakeSystemd()
    common = {
        "home_dir": owned_home,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert install_dashboard_service(**common)["ok"] is True
    owned_unit = owned_home / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    owned_unit.write_text(
        owned_unit.read_text(encoding="utf-8").replace(
            "RestartSec=3s", "RestartSec=9s"
        ),
        encoding="utf-8",
    )
    repair = plan_dashboard_service(**common)
    assert repair["ok"] is True
    assert repair["definition_drift"] is True
    assert repair["commands"]


def test_windows_plan_fails_closed_when_task_query_is_indeterminate(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)

    def denied(argv: list[str], **_kwargs: Any) -> dict[str, Any]:
        assert argv[0] == "powershell.exe"
        return {"returncode": 2, "stderr": "Zugriff verweigert"}

    plan = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=denied,
    )
    assert plan["ok"] is False
    assert plan["ready_to_install"] is False
    assert plan["commands"] == []
    assert "could not be determined" in plan["error"]


def test_linux_install_is_owned_idempotent_and_json_safe(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()
    kwargs = {
        "home_dir": tmp_path,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
        "readiness_probe": lambda: True,
    }

    first = install_dashboard_service(**kwargs)
    unit_path = tmp_path / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    manifest_path = tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    unit_before = unit_path.read_bytes()
    manifest_before = manifest_path.read_bytes()

    assert first["ok"] is True
    assert first["changed"] is True
    assert first["reachable"] is True
    assert unit_before.decode().startswith(f"# {OWNER_MARKER}\n")
    manifest = json.loads(manifest_before)
    assert manifest["owner"] == OWNER_ID
    assert manifest["worker_argv"] == first["worker_argv"]
    assert "token" not in manifest_before.decode().lower()

    second = install_dashboard_service(**kwargs)
    assert second["ok"] is True
    assert second["changed"] is False
    assert unit_path.read_bytes() == unit_before
    assert manifest_path.read_bytes() == manifest_before
    assert manager.commands.count(["systemctl", "--user", "daemon-reload"]) == 1
    json.dumps(first)
    json.dumps(second)

    inspected = inspect_dashboard_service(**kwargs)
    assert inspected["installed"] is True
    assert inspected["owned"] is True
    assert inspected["enabled"] is True
    assert inspected["active"] is True
    assert inspected["reachable"] is True


def test_linux_install_refuses_unowned_unit(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()
    unit_path = tmp_path / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    unit_path.parent.mkdir(parents=True)
    unit_path.write_text("[Service]\nExecStart=/unrelated\n", encoding="utf-8")

    result = install_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config,
        python_executable=python,
        command_runner=manager,
    )

    assert result["ok"] is False
    assert "not owned" in result["error"]
    assert unit_path.read_text(encoding="utf-8") == "[Service]\nExecStart=/unrelated\n"
    assert ["systemctl", "--user", "daemon-reload"] not in manager.commands


def test_linux_readiness_failure_rolls_back_new_registration(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()

    def fail_after_install() -> bool:
        manager.missing_unit_status = True
        return False

    result = install_dashboard_service(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=config,
        python_executable=python,
        command_runner=manager,
        readiness_probe=fail_after_install,
    )

    assert result["ok"] is False
    assert result["rollback_succeeded"] is True
    assert "did not become ready" in result["error"]
    assert not (tmp_path / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME).exists()
    assert not (
        tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    ).exists()
    assert manager.enabled is False
    assert manager.active is False


def test_linux_lifecycle_and_uninstall_preserve_config(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    config.parent.mkdir(parents=True)
    config.write_text("dashboard:\n  port: 7810\n", encoding="utf-8")
    manager = FakeSystemd()
    common = {
        "home_dir": tmp_path,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert install_dashboard_service(**common)["ok"] is True
    assert stop_dashboard_service(**common)["ok"] is True
    assert manager.active is False
    assert start_dashboard_service(**common, readiness_probe=lambda: True)["ok"] is True
    assert (
        restart_dashboard_service(**common, readiness_probe=lambda: True)["ok"] is True
    )
    removed = uninstall_dashboard_service(**common)

    assert removed["ok"] is True
    assert removed["installed"] is False
    assert config.read_text(encoding="utf-8") == "dashboard:\n  port: 7810\n"
    assert not (tmp_path / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME).exists()
    assert not (
        tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    ).exists()


def test_windows_plan_install_and_lifecycle_are_current_user_and_idempotent(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }

    plan = plan_dashboard_service(**common)
    create_plan = plan["commands"][0]
    assert plan["manager_available"] is True
    assert create_plan[create_plan.index("/XML") + 1] == "<owner-private-task-xml>"
    assert "/F" not in create_plan
    task_xml = plan["registration_content"]
    assert "<LogonType>InteractiveToken</LogonType>" in task_xml
    assert "<RunLevel>LeastPrivilege</RunLevel>" in task_xml
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in task_xml
    assert "<RestartOnFailure>" in task_xml
    assert "<Interval>PT1M</Interval>" in task_xml
    assert "<Count>3</Count>" in task_xml
    assert "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>" in task_xml
    assert "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>" in task_xml
    assert "SYSTEM" not in task_xml
    serialized_plan = json.dumps(plan).lower()
    assert "bearer " not in serialized_plan
    assert "#token=" not in serialized_plan

    first = install_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: manager.active,
    )
    manifest_path = tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    manifest_before = manifest_path.read_bytes()
    assert first["ok"] is True
    assert first["changed"] is True
    assert manager.task_exists is True
    assert manager.active is True
    assert manager.create_count == 1
    assert "--service-mode" in manager.action
    assert "bearer " not in manager.action.lower()
    assert "#token=" not in manager.action.lower()

    second = install_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: (_ for _ in ()).throw(
            AssertionError("idempotent install must not wait for readiness")
        ),
    )
    assert second["ok"] is True
    assert second["changed"] is False
    assert manager.create_count == 1
    assert manifest_path.read_bytes() == manifest_before

    inspected = inspect_dashboard_service(
        **common, reachability_probe=lambda: manager.active
    )
    assert inspected["installed"] is True
    assert inspected["owned"] is True
    assert inspected["reachable"] is True

    assert (
        stop_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    assert (
        start_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    assert (
        restart_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    removed = uninstall_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
    )
    assert removed["ok"] is True
    assert manager.task_exists is False
    assert not manifest_path.exists()


def test_windows_refuses_unowned_existing_task(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler(task_exists=True)

    result = install_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=manager,
    )

    assert result["ok"] is False
    assert "not owned" in result["error"]
    assert manager.create_count == 0
    assert manager.task_exists is True


def test_windows_failed_owned_update_restores_task_and_manifest(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            config_path=config,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    manifest_path = tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    prior_manifest = manifest_path.read_bytes()

    failed = install_dashboard_service(
        **common,
        config_path=tmp_path / "changed" / "agency.yaml",
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: False,
    )

    assert failed["ok"] is False
    assert manager.restore_count == 2
    assert manager.task_exists is True
    assert manager.active is True
    assert manifest_path.read_bytes() == prior_manifest
    assert not (manifest_path.parent / ".dashboard-task-rollback.xml").exists()


def test_windows_idle_start_and_stop_are_truthful_and_idempotent(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )

    first_stop = stop_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
    )
    end_count = sum(command[1] == "/End" for command in manager.commands)
    second_stop = stop_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
    )
    assert first_stop["changed"] is True
    assert second_stop["ok"] is True
    assert second_stop["changed"] is False
    assert second_stop["status"] == "already_stopped"
    assert sum(command[1] == "/End" for command in manager.commands) == end_count

    first_start = start_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: manager.active,
    )
    run_count = sum(command[1] == "/Run" for command in manager.commands)
    second_start = start_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: (_ for _ in ()).throw(
            AssertionError("already-running start must not wait")
        ),
    )
    assert first_start["changed"] is True
    assert second_start["changed"] is False
    assert second_start["status"] == "already_running"
    assert sum(command[1] == "/Run" for command in manager.commands) == run_count


def test_windows_owned_drift_is_repaired_but_replaced_task_is_refused(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    manager.task_xml = manager.task_xml.replace(
        "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>",
        "<ExecutionTimeLimit>PT72H</ExecutionTimeLimit>",
    )

    drift = inspect_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
    )
    assert drift["owned"] is True
    assert drift["definition_drift"] is True
    repaired = install_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: manager.active,
    )
    assert repaired["ok"] is True
    assert repaired["registration_changed"] is True
    assert "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>" in manager.task_xml

    manager.task_xml = "<Task><RegistrationInfo><Description>replacement</Description></RegistrationInfo></Task>"
    before = list(manager.commands)
    refused_plan = plan_dashboard_service(**common)
    refused_install = install_dashboard_service(**common)
    refused_uninstall = uninstall_dashboard_service(**common)
    assert refused_plan["ok"] is False
    assert refused_plan["ready_to_install"] is False
    assert refused_plan["commands"] == []
    assert "refusing to overwrite" in refused_plan["error"]
    assert refused_install["ok"] is False
    assert refused_uninstall["ok"] is False
    assert not any(
        command[1] in {"/Create", "/Delete"}
        for command in manager.commands[len(before) :]
    )
    assert manager.task_exists is True


def test_windows_ownership_is_rechecked_immediately_before_mutation(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    base = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **base,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    query_count = 0

    def replaced_between_checks(argv: list[str], **kwargs: Any) -> dict[str, Any]:
        nonlocal query_count
        if argv[1] == "/Query":
            query_count += 1
            if query_count == 2:
                manager.task_xml = (
                    "<Task><RegistrationInfo><Description>replacement</Description>"
                    "</RegistrationInfo></Task>"
                )
        return manager(argv, **kwargs)

    failed = install_dashboard_service(
        **{
            **base,
            "config_path": tmp_path / "changed.yaml",
            "command_runner": replaced_between_checks,
        },
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: manager.active,
    )
    assert failed["ok"] is False
    assert "ownership marker changed" in failed["error"]
    assert failed.get("rollback_commands") is None
    assert manager.task_exists is True
    assert "replacement" in manager.task_xml
    assert not any(command[1] == "/Delete" for command in manager.commands)


def test_windows_failed_create_never_deletes_a_colliding_unowned_task(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()

    def collide_during_create(argv: list[str], **kwargs: Any) -> dict[str, Any]:
        if argv[1] != "/Create":
            return manager(argv, **kwargs)
        manager.commands.append(list(argv))
        manager.task_exists = True
        manager.task_xml = (
            "<Task><RegistrationInfo><Description>other application</Description>"
            "</RegistrationInfo></Task>"
        )
        return {"returncode": 1, "stderr": "same-name task appeared"}

    result = install_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=collide_during_create,
        reachability_probe=lambda: False,
        readiness_probe=lambda: False,
    )

    assert result["ok"] is False
    assert "scheduled-task creation failed" in result["error"]
    assert result.get("rollback_commands") is None
    assert manager.task_exists is True
    assert "other application" in manager.task_xml
    assert not any(command[1] == "/Delete" for command in manager.commands)
    assert not (
        tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    ).exists()


def test_windows_end_failure_requires_proven_manager_idle_state(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    manager.fail_end_once = True
    failed_stop = stop_dashboard_service(**common, reachability_probe=lambda: False)
    manager.fail_end_once = True
    failed_restart = restart_dashboard_service(
        **common, reachability_probe=lambda: False, readiness_probe=lambda: True
    )
    assert failed_stop["ok"] is False
    assert failed_restart["ok"] is False

    manager.active = False
    idle_stop = stop_dashboard_service(**common)
    idle_restart = restart_dashboard_service(
        **common, readiness_probe=lambda: manager.active
    )
    assert idle_stop["ok"] is True
    assert idle_stop["status"] == "already_stopped"
    assert idle_restart["ok"] is True
    assert manager.task_exists is True


def test_successful_stop_removes_unreachable_runtime_descriptor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core import dashboard_runtime

    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    descriptor = tmp_path / ".agency-runtime" / "run" / "dashboard.json"
    dashboard_runtime.write_dashboard_runtime(
        home_dir=tmp_path, token="t" * 32, port=7810, pid=4242
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_service_reachable",
        lambda **_kwargs: False,
    )

    stopped = stop_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
    )
    assert stopped["ok"] is True
    assert stopped["runtime_descriptor_removed"] is True
    assert not descriptor.exists()


def test_windows_definition_comparison_accepts_scheduler_xml_canonicalization(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    # Task Scheduler commonly rewrites whitespace and namespace prefixes while
    # retaining the same current-user SID and semantic definition.
    manager.task_xml = manager.task_xml.replace("  ", "").replace("\n", "")
    result = install_dashboard_service(
        **common,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: (_ for _ in ()).throw(
            AssertionError("semantic no-op must not wait")
        ),
    )
    assert result["ok"] is True
    assert result["changed"] is False
    assert result["registration_changed"] is False


def test_failed_install_restores_idle_state_on_both_managers(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    systemd = FakeSystemd()
    linux = {
        "home_dir": tmp_path / "linux",
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": systemd,
    }
    assert install_dashboard_service(**linux)["ok"] is True
    systemd.enabled = False
    systemd.active = False
    failed_linux = install_dashboard_service(
        **{**linux, "config_path": tmp_path / "changed-linux.yaml"},
        readiness_probe=lambda: False,
    )
    assert failed_linux["ok"] is False
    assert systemd.enabled is False
    assert systemd.active is False

    windows_home = tmp_path / "windows"
    scheduler = FakeTaskScheduler()
    windows = {
        "home_dir": windows_home,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": scheduler,
    }
    assert (
        install_dashboard_service(
            **windows,
            reachability_probe=lambda: scheduler.active,
            readiness_probe=lambda: scheduler.active,
        )["ok"]
        is True
    )
    assert (
        stop_dashboard_service(
            **windows,
            reachability_probe=lambda: scheduler.active,
        )["ok"]
        is True
    )
    failed_windows = install_dashboard_service(
        **{**windows, "config_path": tmp_path / "changed-windows.yaml"},
        reachability_probe=lambda: scheduler.active,
        readiness_probe=lambda: False,
    )
    assert failed_windows["ok"] is False
    assert scheduler.task_exists is True
    assert scheduler.active is False


def test_failed_uninstall_restores_registration_enablement_and_running_state(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    systemd = FakeSystemd()
    linux = {
        "home_dir": tmp_path / "linux",
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": systemd,
    }
    assert install_dashboard_service(**linux)["ok"] is True
    systemd.fail_once.add(("daemon-reload",))
    failed_linux = uninstall_dashboard_service(**linux)
    assert failed_linux["ok"] is False
    assert systemd.enabled is True
    assert systemd.active is True
    assert (
        tmp_path / "linux" / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    ).exists()

    scheduler = FakeTaskScheduler()
    windows = {
        "home_dir": tmp_path / "windows",
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": scheduler,
    }
    assert (
        install_dashboard_service(
            **windows,
            reachability_probe=lambda: scheduler.active,
            readiness_probe=lambda: scheduler.active,
        )["ok"]
        is True
    )
    scheduler.fail_delete_once = True
    failed_windows = uninstall_dashboard_service(
        **windows,
        reachability_probe=lambda: scheduler.active,
    )
    assert failed_windows["ok"] is False
    assert scheduler.task_exists is True
    assert scheduler.active is True
    assert (
        tmp_path / "windows" / ".agency-runtime" / "services" / "dashboard-service.json"
    ).exists()


def test_package_upgrade_restarts_worker_without_replacing_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.dashboard_service as service

    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
        "reachability_probe": lambda: manager.active,
        "readiness_probe": lambda: manager.active,
    }
    assert install_dashboard_service(**common)["ok"] is True
    create_count = manager.create_count
    monkeypatch.setattr(service, "PACKAGE_VERSION", "0.1.1-test")

    upgraded = install_dashboard_service(**common)
    manifest = json.loads(
        (
            tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
        ).read_text(encoding="utf-8")
    )
    assert upgraded["ok"] is True
    assert upgraded["runtime_changed"] is True
    assert upgraded["registration_changed"] is False
    assert manager.create_count == create_count
    assert manifest["package_version"] == "0.1.1-test"
    assert manager.active is True


def test_xdg_config_home_controls_real_home_systemd_unit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    xdg = (tmp_path / "xdg-config").resolve()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    plan = plan_dashboard_service(
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
        command_runner=FakeSystemd(),
    )
    assert plan["registration_path"] == str(
        xdg / "systemd" / "user" / SYSTEMD_UNIT_NAME
    )


def test_windows_acl_failure_rolls_back_new_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.dashboard_service as service
    from agency_runtime.core.configuration import ConfigurationError

    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    calls = 0

    def fail_manifest(_path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ConfigurationError(
                "owner-only file permissions could not be enforced"
            )

    monkeypatch.setattr(service, "restrict_private_file", fail_manifest)
    result = install_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=manager,
        reachability_probe=lambda: manager.active,
        readiness_probe=lambda: manager.active,
    )
    assert result["ok"] is False
    assert "owner-only file permissions" in result["error"]
    assert manager.task_exists is False
    assert not (
        tmp_path / ".agency-runtime" / "services" / "dashboard-service.json"
    ).exists()


def test_windows_xml_rejects_wrong_schema_and_extra_triggers_or_actions(
    tmp_path: Path,
) -> None:
    import agency_runtime.core.dashboard_service as service

    python, config = _paths(tmp_path)
    xml = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=FakeTaskScheduler(),
    )["registration_content"]
    duplicate_trigger = xml.replace(
        "  </Triggers>",
        "    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>\n  </Triggers>",
    )
    duplicate_action = xml.replace(
        "  </Actions>",
        "    <Exec><Command>other.exe</Command><Arguments>x</Arguments></Exec>\n"
        "  </Actions>",
    )
    wrong_schema = xml.replace(f' xmlns="{service.WINDOWS_TASK_XML_NAMESPACE}"', "")

    behavior_changes = (
        xml.replace(
            "    </Exec>",
            "      <WorkingDirectory>C:\\\\other</WorkingDirectory>\n    </Exec>",
        ),
        xml.replace(
            "    </LogonTrigger>", "      <Delay>PT5M</Delay>\n    </LogonTrigger>"
        ),
        xml.replace(
            "    </LogonTrigger>",
            "      <StartBoundary>2030-01-01T00:00:00</StartBoundary>\n"
            "    </LogonTrigger>",
        ),
        xml.replace(
            "    </LogonTrigger>",
            "      <Repetition><Interval>PT1M</Interval></Repetition>\n"
            "    </LogonTrigger>",
        ),
        xml.replace(
            "  </Settings>",
            "    <DeleteExpiredTaskAfter>PT1H</DeleteExpiredTaskAfter>\n  </Settings>",
        ),
        xml.replace(
            "  </RegistrationInfo>",
            "    <SecurityDescriptor>D:(A;;FA;;;WD)</SecurityDescriptor>\n"
            "  </RegistrationInfo>",
        ),
        xml.replace("    <Exec>", '    <Exec unexpected="true">'),
        xml.replace("    <LogonTrigger>", '    <LogonTrigger unexpected="true">'),
    )
    assert service._windows_task_properties(duplicate_trigger) is None
    assert service._windows_task_properties(duplicate_action) is None
    assert service._windows_task_properties(wrong_schema) is None
    assert all(
        service._windows_task_properties(candidate) is None
        for candidate in behavior_changes
    )


def test_windows_probe_catches_directory_not_found_by_exact_hresult() -> None:
    import agency_runtime.core.dashboard_service as service

    script = service._WINDOWS_TASK_PROBE_SCRIPT
    assert "catch{" in script
    assert "catch [System.Runtime.InteropServices.COMException]" not in script
    assert "-2147024894" in script  # 0x80070002
    assert "-2147024893" in script  # 0x80070003 / DirectoryNotFoundException
    assert script.count("Exception.HResult") == 1


def test_windows_returncode_one_access_denied_is_not_absence(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)

    def denied(argv: list[str], **_kwargs: Any) -> dict[str, Any]:
        if argv[0] == "powershell.exe":
            return {"returncode": 0, "stdout": "PRESENT:3"}
        assert argv[1:2] == ["/Query"]
        return {"returncode": 1, "stderr": "FEHLER: Zugriff verweigert."}

    result = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
        command_runner=denied,
    )
    assert result["ok"] is False
    assert result["commands"] == []
    assert "could not be determined" in result["error"]


def test_windows_absence_ignores_localized_schtasks_text(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    calls: list[list[str]] = []

    def absent(argv: list[str], **_kwargs: Any) -> dict[str, Any]:
        calls.append(list(argv))
        if argv[0] == "powershell.exe":
            return {"returncode": 0, "stdout": "ABSENT"}
        raise AssertionError("absent tasks must not query schtasks XML")

    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": absent,
    }
    assert plan_dashboard_service(**common)["ready_to_install"] is True
    assert inspect_dashboard_service(**common)["installed"] is False
    assert calls and all(command[0] == "powershell.exe" for command in calls)


def test_linux_ambiguous_manager_state_blocks_owned_mutation(tmp_path: Path) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()
    common = {
        "home_dir": tmp_path,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert install_dashboard_service(**common)["ok"] is True
    manager.ambiguous_status = True
    state = inspect_dashboard_service(**common)
    before = len(manager.commands)
    result = install_dashboard_service(
        **{**common, "config_path": tmp_path / "changed.yaml"}
    )
    subsequent = manager.commands[before:]
    assert state["enabled"] is None
    assert state["active"] is None
    assert result["ok"] is False
    assert "could not be determined" in result["error"]
    assert not any(
        command[2] in {"daemon-reload", "enable", "disable", "start", "stop", "restart"}
        for command in subsequent
    )


def test_mutating_lifecycles_hold_service_lock_during_preflight_and_commands(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.dashboard_service as service

    held = False

    @contextmanager
    def observed_lock(_ctx: Any):
        nonlocal held
        assert held is False
        held = True
        try:
            yield
        finally:
            held = False

    manager = FakeSystemd()

    def guarded(argv: list[str], **kwargs: Any) -> dict[str, Any]:
        assert held is True
        return manager(argv, **kwargs)

    monkeypatch.setattr(service, "_service_lock", observed_lock)
    python, config = _paths(tmp_path)
    common = {
        "home_dir": tmp_path,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": guarded,
    }
    assert install_dashboard_service(**common)["ok"] is True
    assert stop_dashboard_service(**common)["ok"] is True
    assert start_dashboard_service(**common, readiness_probe=lambda: True)["ok"] is True
    assert (
        restart_dashboard_service(**common, readiness_probe=lambda: True)["ok"] is True
    )
    assert uninstall_dashboard_service(**common)["ok"] is True
    assert held is False


def test_each_windows_mutation_has_an_immediate_exact_xml_requery(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
        "reachability_probe": lambda: manager.active,
        "readiness_probe": lambda: manager.active,
    }
    assert install_dashboard_service(**common)["ok"] is True
    manager.task_xml = manager.task_xml.replace(
        "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>",
        "<ExecutionTimeLimit>PT1H</ExecutionTimeLimit>",
    )
    assert install_dashboard_service(**common)["ok"] is True
    assert (
        uninstall_dashboard_service(
            **{key: value for key, value in common.items() if key != "readiness_probe"}
        )["ok"]
        is True
    )

    mutations = {"/Create", "/Run", "/End", "/Delete"}
    for index, command in enumerate(manager.commands):
        if command[1] not in mutations:
            continue
        assert index > 0
        previous = manager.commands[index - 1]
        if command[1] == "/Create" and "/F" not in command:
            assert previous[0] == "powershell.exe"
        else:
            assert previous[1] == "/Query"
            assert "/XML" in previous


def test_systemd_rollback_uses_restart_and_semantic_verification(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeSystemd()
    common = {
        "home_dir": tmp_path,
        "platform_name": "linux",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert install_dashboard_service(**common)["ok"] is True

    def fail_after_preflight() -> bool:
        manager.ambiguous_status = True
        return False

    result = install_dashboard_service(
        **{**common, "config_path": tmp_path / "changed.yaml"},
        readiness_probe=fail_after_preflight,
    )
    assert result["ok"] is False
    assert result["rollback_succeeded"] is False
    assert result["rollback_error"] == "systemd rollback verification failed"
    assert ["systemctl", "--user", "restart", SYSTEMD_UNIT_NAME] in manager.commands


def test_unsafe_windows_restore_is_reported_false_and_never_overwrites(
    tmp_path: Path,
) -> None:
    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
        "reachability_probe": lambda: manager.active,
    }
    assert (
        install_dashboard_service(**common, readiness_probe=lambda: manager.active)[
            "ok"
        ]
        is True
    )

    replacement = (
        "<Task><RegistrationInfo><Description>replacement</Description>"
        "</RegistrationInfo></Task>"
    )

    def replace_before_rollback() -> bool:
        manager.task_xml = replacement
        return False

    result = install_dashboard_service(
        **{**common, "config_path": tmp_path / "changed.yaml"},
        readiness_probe=replace_before_rollback,
    )
    assert result["ok"] is False
    assert result["rollback_succeeded"] is False
    assert "unsafe Windows rollback refused" in result["rollback_error"]
    assert manager.task_xml == replacement


def test_service_files_are_private_while_empty_before_payload_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.dashboard_service as service

    python, config = _paths(tmp_path)
    ctx = service._context(
        home_dir=tmp_path,
        platform_name="windows",
        config_path=config,
        python_executable=python,
    )
    assert ctx is not None
    snapshots: dict[str, list[bytes]] = {}

    def observe(path: Path) -> None:
        snapshots.setdefault(path.name, []).append(path.read_bytes())

    monkeypatch.setattr(service, "restrict_private_file", observe)
    manager = FakeTaskScheduler()
    task_result = service._register_windows_xml(
        ctx, service._windows_task_content(ctx), force=False, command_runner=manager
    )
    restored = tmp_path / "restore.bin"
    service._restore_file(restored, b"private payload")
    with service._service_lock(ctx):
        pass

    task_snapshots = next(
        values
        for name, values in snapshots.items()
        if name.startswith(".dashboard-task-")
    )
    restore_snapshots = next(
        values for name, values in snapshots.items() if name.startswith(".restore.bin.")
    )
    lock_snapshots = snapshots[".dashboard-service.lock"]
    assert task_result.ok is True
    assert task_snapshots[0] == b""
    assert b"<Task" in task_snapshots[-1]
    assert restore_snapshots == [b"", b"private payload"]
    assert lock_snapshots[0] == b""
    assert lock_snapshots[-1] == b"\0"


def test_stale_runtime_cleanup_uses_descriptor_compare_and_remove(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from agency_runtime.core import dashboard_runtime

    python, config = _paths(tmp_path)
    manager = FakeTaskScheduler()
    common = {
        "home_dir": tmp_path,
        "platform_name": "windows",
        "config_path": config,
        "python_executable": python,
        "command_runner": manager,
    }
    assert (
        install_dashboard_service(
            **common,
            reachability_probe=lambda: manager.active,
            readiness_probe=lambda: manager.active,
        )["ok"]
        is True
    )
    manager.active = False
    dashboard_runtime.write_dashboard_runtime(
        home_dir=tmp_path, token="a" * 32, port=7810, pid=111
    )

    def rotate_while_probing(**_kwargs: Any) -> bool:
        dashboard_runtime.write_dashboard_runtime(
            home_dir=tmp_path, token="b" * 32, port=7811, pid=222
        )
        return False

    monkeypatch.setattr(
        dashboard_runtime, "dashboard_service_reachable", rotate_while_probing
    )
    result = stop_dashboard_service(**common)
    current = dashboard_runtime.read_dashboard_runtime(home_dir=tmp_path)
    assert result["ok"] is True
    assert result["runtime_descriptor_removed"] is False
    assert current["token"] == "b" * 32
    assert current["pid"] == 222


def test_unsupported_platform_result_is_json_safe(tmp_path: Path) -> None:
    result = plan_dashboard_service(
        home_dir=tmp_path,
        platform_name="darwin",
        python_executable=tmp_path / "python",
    )
    assert result["ok"] is False
    assert result["supported"] is False
    assert result["exit_code"] == 2
    json.dumps(result)


def test_dashboard_service_cli_status_is_machine_readable_without_tokens(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as service
    from agency_runtime.cli.main import main

    monkeypatch.setattr(
        service,
        "inspect_dashboard_service",
        lambda **_kwargs: {
            "ok": True,
            "exit_code": 0,
            "action": "inspect",
            "installed": True,
            "active": True,
            "reachable": True,
        },
    )

    assert main(["dashboard", "service", "status", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["installed"] is True
    assert "token" not in json.dumps(result).lower()


def test_dashboard_service_cli_passes_immediate_and_bounded_probes_separately(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as service
    from agency_runtime.cli import main as cli

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        service,
        "start_dashboard_service",
        lambda **kwargs: (
            calls.append(kwargs)
            or {"ok": True, "exit_code": 0, "action": "start", "reachable": True}
        ),
    )

    assert cli.main(["dashboard", "service", "start", "--json"]) == 0
    capsys.readouterr()
    assert len(calls) == 1
    assert callable(calls[0]["reachability_probe"])
    assert callable(calls[0]["readiness_probe"])
    assert calls[0]["reachability_probe"] is not calls[0]["readiness_probe"]


def test_dashboard_service_cli_dry_run_never_installs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as service
    from agency_runtime.cli.main import main

    monkeypatch.setattr(
        service,
        "plan_dashboard_service",
        lambda **_kwargs: {
            "ok": True,
            "exit_code": 0,
            "action": "plan",
            "dry_run": True,
        },
    )
    monkeypatch.setattr(
        service,
        "install_dashboard_service",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must not install")
        ),
    )

    assert main(["dashboard", "service", "install", "--dry-run", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
