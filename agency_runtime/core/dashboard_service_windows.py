"""Windows Task Scheduler registration and rollback mechanics."""

from __future__ import annotations

import base64
import binascii
import hmac
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from xml.sax.saxutils import escape as xml_escape

from agency_runtime.core.configuration import ConfigurationError, restrict_private_file
from agency_runtime.core.dashboard_service_core import (
    OWNER_ID,
    OWNER_MARKER,
    WINDOWS_TASK_NAME,
    WINDOWS_TASK_XML_NAMESPACE,
    CommandRunner,
    _CommandResult,
    _Context,
    _RollbackOutcome,
    _run,
    _validate_text,
)
from agency_runtime.core.dashboard_service_manifest import (
    _file_matches,
    _manifest_owned,
    _prepare_private_parent,
    _restore_file,
)
from agency_runtime.core.windows_system import windows_system_command

_WINDOWS_TASK_PROBE_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$s=New-Object -ComObject Schedule.Service;$s.Connect();"
    "try{$t=$s.GetFolder('\\').GetTask('Agency Runtime Dashboard')}"
    "catch{"
    "if($_.Exception.HResult -in @(-2147024894,-2147024893)){"
    "[Console]::Out.Write('ABSENT');exit 0};throw};"
    "[Console]::Out.Write(('PRESENT:{0}' -f [int]$t.State))"
)
_WINDOWS_TASK_XML_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$s=New-Object -ComObject Schedule.Service;$s.Connect();"
    "$x=$s.GetFolder('\\').GetTask('Agency Runtime Dashboard').Xml;"
    "$b=[Text.Encoding]::UTF8.GetBytes($x);"
    "[Console]::Out.Write([Convert]::ToBase64String($b))"
)
_MAX_TASK_XML_BYTES = 512 * 1024
_MAX_TASK_XML_BASE64_BYTES = 4 * ((_MAX_TASK_XML_BYTES + 2) // 3)
_WINDOWS_TASK_FILE_ENCODING = "utf-16"
_WINDOWS_TRANSITION_ATTEMPTS = 81
_WINDOWS_TRANSITION_POLL_SECONDS = 0.1


def _windows_action(argv: Sequence[str]) -> str:
    values = [_validate_text(str(item), label="Windows task argument") for item in argv]
    return subprocess.list2cmdline(values)


def _windows_create_command(
    xml_path: str | Path,
    *,
    force: bool,
    command_runner: CommandRunner | None = None,
) -> list[str]:
    command = windows_system_command(
        "schtasks.exe",
        "/Create",
        "/TN",
        WINDOWS_TASK_NAME,
        "/XML",
        str(xml_path),
        command_runner=command_runner,
    )
    if force:
        command.append("/F")
    return command


def _windows_task_content(ctx: _Context) -> str:
    """Render the explicit, durable current-user Task Scheduler contract."""

    if ctx.windows_user is None:
        raise RuntimeError("Windows dashboard service context has no user identity")
    command = xml_escape(str(ctx.worker_argv[0]))
    arguments = xml_escape(_windows_action(ctx.worker_argv[1:]))
    current_user = xml_escape(ctx.windows_user)
    trigger_user = xml_escape(ctx.windows_account or ctx.windows_user)
    description = xml_escape(OWNER_MARKER)
    return (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        f'<Task version="1.4" xmlns="{WINDOWS_TASK_XML_NAMESPACE}">\n'
        "  <RegistrationInfo>\n"
        f"    <Description>{description}</Description>\n"
        f"    <Source>{OWNER_ID}</Source>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n"
        "    <LogonTrigger>\n"
        "      <Enabled>true</Enabled>\n"
        f"      <UserId>{trigger_user}</UserId>\n"
        "    </LogonTrigger>\n"
        "  </Triggers>\n"
        "  <Principals>\n"
        '    <Principal id="CurrentUser">\n'
        f"      <UserId>{current_user}</UserId>\n"
        "      <LogonType>InteractiveToken</LogonType>\n"
        "      <RunLevel>LeastPrivilege</RunLevel>\n"
        "    </Principal>\n"
        "  </Principals>\n"
        "  <Settings>\n"
        "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
        "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
        "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
        "    <AllowHardTerminate>true</AllowHardTerminate>\n"
        "    <StartWhenAvailable>true</StartWhenAvailable>\n"
        "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
        "    <IdleSettings>\n"
        "      <StopOnIdleEnd>false</StopOnIdleEnd>\n"
        "      <RestartOnIdle>false</RestartOnIdle>\n"
        "    </IdleSettings>\n"
        "    <AllowStartOnDemand>true</AllowStartOnDemand>\n"
        "    <Enabled>true</Enabled>\n"
        "    <Hidden>false</Hidden>\n"
        "    <RunOnlyIfIdle>false</RunOnlyIfIdle>\n"
        "    <WakeToRun>false</WakeToRun>\n"
        "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n"
        "    <Priority>7</Priority>\n"
        "    <RestartOnFailure>\n"
        "      <Interval>PT1M</Interval>\n"
        "      <Count>3</Count>\n"
        "    </RestartOnFailure>\n"
        "    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>\n"
        "  </Settings>\n"
        '  <Actions Context="CurrentUser">\n'
        "    <Exec>\n"
        f"      <Command>{command}</Command>\n"
        f"      <Arguments>{arguments}</Arguments>\n"
        "    </Exec>\n"
        "  </Actions>\n"
        "</Task>\n"
    )


def _xml_text(root: ET.Element, path: str) -> str:
    namespace = {"t": WINDOWS_TASK_XML_NAMESPACE}
    element = root.find(path, namespace)
    return (element.text or "").strip() if element is not None else ""


def _xml_attribute(root: ET.Element, path: str, name: str) -> str:
    namespace = {"t": WINDOWS_TASK_XML_NAMESPACE}
    element = root.find(path, namespace)
    return element.attrib.get(name, "").strip() if element is not None else ""


def _xml_text_or_default(root: ET.Element, path: str, default: str) -> str:
    namespace = {"t": WINDOWS_TASK_XML_NAMESPACE}
    element = root.find(path, namespace)
    if element is None:
        return default
    return (element.text or "").strip()


def _xml_children_match(
    element: ET.Element,
    *,
    required: Sequence[str],
    optional: Sequence[str] = (),
    attributes: Mapping[str, str] | None = None,
) -> bool:
    if dict(element.attrib) != dict(attributes or {}):
        return False
    namespace = "{" + WINDOWS_TASK_XML_NAMESPACE + "}"
    names: list[str] = []
    for child in element:
        if not child.tag.startswith(namespace):
            return False
        names.append(child.tag[len(namespace) :])
    return bool(
        all(names.count(name) == 1 for name in required)
        and all(names.count(name) <= 1 for name in optional)
        and set(names) <= set(required) | set(optional)
    )


def _xml_scalar_nodes_are_plain(root: ET.Element, paths: Sequence[str]) -> bool:
    namespace = {"t": WINDOWS_TASK_XML_NAMESPACE}
    for path in paths:
        nodes = root.findall(path, namespace)
        if len(nodes) != 1 or nodes[0].attrib or list(nodes[0]):
            return False
    return True


def _windows_task_properties(content: str) -> dict[str, str] | None:
    if len(content) > _MAX_TASK_XML_BYTES:
        return None
    upper_content = content.upper()
    if (
        len(content.encode("utf-8", errors="replace")) > _MAX_TASK_XML_BYTES
        or "<!DOCTYPE" in upper_content
        or "<!ENTITY" in upper_content
    ):
        return None
    try:
        # Input is byte-bounded above and DTD/entity declarations are rejected.
        root = ET.fromstring(  # nosec B314
            content
        )
    except (ET.ParseError, UnicodeError, ValueError):
        return None
    namespace = "{" + WINDOWS_TASK_XML_NAMESPACE + "}"
    root_children = (
        "RegistrationInfo",
        "Triggers",
        "Principals",
        "Settings",
        "Actions",
    )
    if root.tag != namespace + "Task" or not _xml_children_match(
        root, required=root_children, attributes={"version": "1.4"}
    ):
        return None
    ns = {"t": WINDOWS_TASK_XML_NAMESPACE}
    registration = root.find("t:RegistrationInfo", ns)
    triggers = root.find("t:Triggers", ns)
    logon = root.find("t:Triggers/t:LogonTrigger", ns)
    principals = root.find("t:Principals", ns)
    principal = root.find("t:Principals/t:Principal", ns)
    settings = root.find("t:Settings", ns)
    idle = root.find("t:Settings/t:IdleSettings", ns)
    restart = root.find("t:Settings/t:RestartOnFailure", ns)
    actions = root.find("t:Actions", ns)
    execute = root.find("t:Actions/t:Exec", ns)
    elements = (
        registration,
        triggers,
        logon,
        principals,
        principal,
        settings,
        idle,
        restart,
        actions,
        execute,
    )
    if any(element is None for element in elements):
        return None
    registration = cast(ET.Element, registration)
    triggers = cast(ET.Element, triggers)
    logon = cast(ET.Element, logon)
    principals = cast(ET.Element, principals)
    principal = cast(ET.Element, principal)
    settings = cast(ET.Element, settings)
    idle = cast(ET.Element, idle)
    restart = cast(ET.Element, restart)
    actions = cast(ET.Element, actions)
    execute = cast(ET.Element, execute)
    settings_required = (
        "MultipleInstancesPolicy",
        "DisallowStartIfOnBatteries",
        "StopIfGoingOnBatteries",
        "StartWhenAvailable",
        "IdleSettings",
        "ExecutionTimeLimit",
        "RestartOnFailure",
        "UseUnifiedSchedulingEngine",
    )
    settings_optional = (
        "AllowHardTerminate",
        "RunOnlyIfNetworkAvailable",
        "AllowStartOnDemand",
        "Enabled",
        "Hidden",
        "RunOnlyIfIdle",
        "WakeToRun",
        "Priority",
        "DisallowStartOnRemoteAppSession",
        "Volatile",
    )
    schema_ok = all(
        (
            _xml_children_match(
                registration,
                required=("Description", "Source"),
                optional=(
                    "Date",
                    "Author",
                    "Version",
                    "URI",
                    "Documentation",
                ),
            ),
            _xml_children_match(triggers, required=("LogonTrigger",)),
            _xml_children_match(logon, required=("UserId",), optional=("Enabled",)),
            _xml_children_match(principals, required=("Principal",)),
            _xml_children_match(
                principal,
                required=("UserId", "LogonType"),
                optional=("RunLevel",),
                attributes={"id": "CurrentUser"},
            ),
            _xml_children_match(settings, required=settings_required, optional=settings_optional),
            _xml_children_match(idle, required=("StopOnIdleEnd", "RestartOnIdle")),
            _xml_children_match(restart, required=("Interval", "Count")),
            _xml_children_match(actions, required=("Exec",), attributes={"Context": "CurrentUser"}),
            _xml_children_match(execute, required=("Command", "Arguments")),
        )
    )
    if not schema_ok:
        return None
    scalar_paths = (
        "t:RegistrationInfo/t:Description",
        "t:RegistrationInfo/t:Source",
        "t:Triggers/t:LogonTrigger/t:UserId",
        "t:Principals/t:Principal/t:UserId",
        "t:Principals/t:Principal/t:LogonType",
        "t:Settings/t:MultipleInstancesPolicy",
        "t:Settings/t:DisallowStartIfOnBatteries",
        "t:Settings/t:StopIfGoingOnBatteries",
        "t:Settings/t:StartWhenAvailable",
        "t:Settings/t:IdleSettings/t:StopOnIdleEnd",
        "t:Settings/t:IdleSettings/t:RestartOnIdle",
        "t:Settings/t:ExecutionTimeLimit",
        "t:Settings/t:RestartOnFailure/t:Interval",
        "t:Settings/t:RestartOnFailure/t:Count",
        "t:Settings/t:UseUnifiedSchedulingEngine",
        "t:Actions/t:Exec/t:Command",
        "t:Actions/t:Exec/t:Arguments",
    )
    if not _xml_scalar_nodes_are_plain(root, scalar_paths):
        return None
    for parent, nested in (
        (registration, frozenset()),
        (logon, frozenset()),
        (principal, frozenset()),
        (settings, frozenset({"IdleSettings", "RestartOnFailure"})),
    ):
        for child in parent:
            name = child.tag[len(namespace) :]
            if name not in nested and (child.attrib or list(child)):
                return None
    properties = {
        "description": _xml_text(root, "t:RegistrationInfo/t:Description"),
        "source": _xml_text(root, "t:RegistrationInfo/t:Source"),
        "trigger_enabled": _xml_text_or_default(
            root, "t:Triggers/t:LogonTrigger/t:Enabled", "true"
        ),
        "trigger_user": _xml_text(root, "t:Triggers/t:LogonTrigger/t:UserId"),
        "principal_user": _xml_text(root, "t:Principals/t:Principal/t:UserId"),
        "logon_type": _xml_text(root, "t:Principals/t:Principal/t:LogonType"),
        "run_level": _xml_text_or_default(
            root, "t:Principals/t:Principal/t:RunLevel", "LeastPrivilege"
        ),
        "multiple_instances": _xml_text(root, "t:Settings/t:MultipleInstancesPolicy"),
        "battery_start": _xml_text(root, "t:Settings/t:DisallowStartIfOnBatteries"),
        "battery_stop": _xml_text(root, "t:Settings/t:StopIfGoingOnBatteries"),
        "hard_terminate": _xml_text_or_default(root, "t:Settings/t:AllowHardTerminate", "true"),
        "start_when_available": _xml_text(root, "t:Settings/t:StartWhenAvailable"),
        "network_required": _xml_text_or_default(
            root, "t:Settings/t:RunOnlyIfNetworkAvailable", "false"
        ),
        "stop_on_idle_end": _xml_text(root, "t:Settings/t:IdleSettings/t:StopOnIdleEnd"),
        "restart_on_idle": _xml_text(root, "t:Settings/t:IdleSettings/t:RestartOnIdle"),
        "start_on_demand": _xml_text_or_default(root, "t:Settings/t:AllowStartOnDemand", "true"),
        "enabled": _xml_text_or_default(root, "t:Settings/t:Enabled", "true"),
        "hidden": _xml_text_or_default(root, "t:Settings/t:Hidden", "false"),
        "run_only_if_idle": _xml_text_or_default(root, "t:Settings/t:RunOnlyIfIdle", "false"),
        "wake_to_run": _xml_text_or_default(root, "t:Settings/t:WakeToRun", "false"),
        "execution_limit": _xml_text(root, "t:Settings/t:ExecutionTimeLimit"),
        "priority": _xml_text_or_default(root, "t:Settings/t:Priority", "7"),
        "restart_interval": _xml_text(root, "t:Settings/t:RestartOnFailure/t:Interval"),
        "restart_count": _xml_text(root, "t:Settings/t:RestartOnFailure/t:Count"),
        "unified_engine": _xml_text(root, "t:Settings/t:UseUnifiedSchedulingEngine"),
        "remote_session": _xml_text_or_default(
            root, "t:Settings/t:DisallowStartOnRemoteAppSession", "false"
        ),
        "volatile": _xml_text_or_default(root, "t:Settings/t:Volatile", "false"),
        "actions_context": _xml_attribute(root, "t:Actions", "Context"),
        "command": _xml_text(root, "t:Actions/t:Exec/t:Command"),
        "arguments": _xml_text(root, "t:Actions/t:Exec/t:Arguments"),
    }
    if any(
        not properties[name]
        for name in (
            "description",
            "source",
            "trigger_user",
            "principal_user",
            "command",
            "arguments",
        )
    ):
        return None
    return properties


def _windows_xml_owned(content: str) -> bool:
    properties = _windows_task_properties(content)
    return bool(
        properties
        and properties["description"] == OWNER_MARKER
        and properties["source"] == OWNER_ID
    )


def _windows_definition_matches(ctx: _Context, content: str) -> bool:
    return _windows_task_properties(content) == _windows_task_properties(_windows_task_content(ctx))


def _register_windows_xml(
    ctx: _Context,
    content: str,
    *,
    force: bool,
    command_runner: CommandRunner | None,
) -> _CommandResult:
    _prepare_private_parent(ctx.manifest_path, trusted_root=ctx.home)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".dashboard-task-",
        suffix=".xml",
        dir=str(ctx.manifest_path.parent),
    )
    temporary = Path(temporary_name)
    handle = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, 0o600)
        # Secure the empty XML file before command or argument paths are written.
        restrict_private_file(temporary)
        with os.fdopen(
            handle,
            "w",
            encoding=_WINDOWS_TASK_FILE_ENCODING,
            newline="\n",
        ) as stream:
            handle = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        return _run(
            _windows_create_command(
                temporary,
                force=force,
                command_runner=command_runner,
            ),
            command_runner=command_runner,
        )
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def _query_windows_task_probe(
    *, command_runner: CommandRunner | None, timeout: float = 10.0
) -> _CommandResult:
    return _run(
        windows_system_command(
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _WINDOWS_TASK_PROBE_SCRIPT,
            command_runner=command_runner,
        ),
        command_runner=command_runner,
        timeout=timeout,
    )


def _windows_registration_state(result: _CommandResult) -> str:
    if result.returncode == 127:
        return "unavailable"
    if not result.ok:
        return "indeterminate"
    value = result.stdout.strip()
    if value == "ABSENT":
        return "absent"
    if value in {f"PRESENT:{state}" for state in range(5)}:
        return "present"
    return "indeterminate"


def _query_windows_xml(
    *, command_runner: CommandRunner | None, timeout: float = 10.0
) -> _CommandResult:
    result = _run(
        windows_system_command(
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _WINDOWS_TASK_XML_SCRIPT,
            command_runner=command_runner,
        ),
        command_runner=command_runner,
        timeout=timeout,
    )
    if not result.ok:
        return result
    encoded = result.stdout.strip()
    try:
        encoded_bytes = encoded.encode("ascii")
    except UnicodeEncodeError:
        encoded_bytes = b""
    if not encoded_bytes or len(encoded_bytes) > _MAX_TASK_XML_BASE64_BYTES:
        return _CommandResult(
            result.command,
            125,
            "",
            "scheduled-task XML transport returned invalid bounded Base64",
        )
    try:
        content_bytes = base64.b64decode(encoded_bytes, validate=True)
    except (binascii.Error, ValueError):
        return _CommandResult(
            result.command,
            125,
            "",
            "scheduled-task XML transport returned invalid bounded Base64",
        )
    if len(content_bytes) > _MAX_TASK_XML_BYTES:
        return _CommandResult(
            result.command,
            125,
            "",
            "scheduled-task XML transport exceeded the 512 KiB limit",
        )
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _CommandResult(
            result.command,
            125,
            "",
            "scheduled-task XML transport was not valid UTF-8",
        )
    return _CommandResult(result.command, 0, content, result.stderr)


def _query_windows_registration(
    *, command_runner: CommandRunner | None
) -> tuple[str, _CommandResult]:
    presence = _query_windows_task_probe(command_runner=command_runner)
    state = _windows_registration_state(presence)
    if state != "present":
        return state, presence
    definition = _query_windows_xml(command_runner=command_runner)
    if definition.returncode == 127:
        return "unavailable", definition
    if not definition.ok:
        return "indeterminate", definition
    return "present", definition


def _windows_running_state(
    *, command_runner: CommandRunner | None
) -> tuple[bool | None, _CommandResult]:
    result = _query_windows_task_probe(command_runner=command_runner)
    if _windows_registration_state(result) != "present":
        return None, result
    task_state = result.stdout.strip().partition(":")[2]
    # Task Scheduler COM states: 0 unknown, 1 disabled, 2 queued, 3 ready,
    # 4 running. Only disabled/ready are affirmative idle evidence.
    if task_state == "4":
        return True, result
    if task_state in {"1", "3"}:
        return False, result
    return None, result


def _wait_windows_running_state(
    expected: bool,
    *,
    command_runner: CommandRunner | None,
    attempts: int = _WINDOWS_TRANSITION_ATTEMPTS,
    poll_seconds: float = _WINDOWS_TRANSITION_POLL_SECONDS,
) -> tuple[bool, list[_CommandResult]]:
    """Poll until Task Scheduler proves one exact running or idle state.

    ``schtasks /End`` is asynchronous. A successful exit code therefore is
    not evidence that ``IgnoreNew`` will accept the next ``/Run`` yet.
    Unknown and queued states remain transitional until this bounded poll is
    exhausted.
    """

    results: list[_CommandResult] = []
    bounded_attempts = max(1, attempts)
    for attempt in range(bounded_attempts):
        running, result = _windows_running_state(command_runner=command_runner)
        results.append(result)
        if running is expected:
            return True, results
        if attempt + 1 < bounded_attempts:
            time.sleep(max(0.0, poll_seconds))
    return False, results


def _capture_owned_windows_task(
    ctx: _Context, *, command_runner: CommandRunner | None
) -> tuple[str, _CommandResult]:
    if not _manifest_owned(ctx):
        raise RuntimeError("dashboard service ownership manifest changed before mutation")
    state, result = _query_windows_registration(command_runner=command_runner)
    if state != "present" or not _windows_xml_owned(result.stdout):
        raise RuntimeError("scheduled-task ownership marker changed before mutation")
    return result.stdout, result


def _assert_windows_task_unchanged(
    ctx: _Context,
    expected_xml: str,
    *,
    command_runner: CommandRunner | None,
) -> _CommandResult:
    current, result = _capture_owned_windows_task(ctx, command_runner=command_runner)
    if not hmac.compare_digest(current, expected_xml):
        raise RuntimeError("scheduled-task definition changed before mutation")
    return result


def _assert_windows_task_absent(*, command_runner: CommandRunner | None) -> _CommandResult:
    state, result = _query_windows_registration(command_runner=command_runner)
    if state != "absent":
        raise RuntimeError("scheduled-task absence could not be confirmed before mutation")
    return result


def _export_owned_windows_task(
    ctx: _Context,
    *,
    command_runner: CommandRunner | None,
) -> tuple[str, _CommandResult]:
    return _capture_owned_windows_task(ctx, command_runner=command_runner)


@dataclass(slots=True)
class _WindowsRestoreTransaction:
    """Mutable state for one fail-closed Task Scheduler rollback."""

    ctx: _Context
    prior_task: str | None
    prior_manifest: bytes | None
    prior_active: bool
    created_registration: bool
    command_runner: CommandRunner | None
    results: list[_CommandResult] = field(default_factory=list)
    mutation_results: list[_CommandResult] = field(default_factory=list)
    error: str | None = None
    restored_xml: str | None = None


def _query_restore_registration(
    transaction: _WindowsRestoreTransaction,
) -> tuple[str, _CommandResult]:
    state, result = _query_windows_registration(command_runner=transaction.command_runner)
    transaction.results.append(result)
    return state, result


def _created_registration_is_ours(
    transaction: _WindowsRestoreTransaction,
    state: str,
    result: _CommandResult,
) -> bool:
    return bool(
        state == "present"
        and _windows_xml_owned(result.stdout)
        and _windows_definition_matches(transaction.ctx, result.stdout)
    )


def _delete_created_windows_registration(
    transaction: _WindowsRestoreTransaction,
    current_state: str,
    current: _CommandResult,
) -> None:
    if not transaction.created_registration:
        return
    if not _created_registration_is_ours(transaction, current_state, current):
        transaction.error = "unsafe Windows rollback refused: created task ownership changed"
        return
    recheck_state, recheck = _query_restore_registration(transaction)
    if not (
        recheck_state == "present"
        and _windows_xml_owned(recheck.stdout)
        and hmac.compare_digest(recheck.stdout, current.stdout)
    ):
        transaction.error = "unsafe Windows rollback refused: created task changed"
        return
    deleted = _run(
        windows_system_command(
            "schtasks.exe",
            "/Delete",
            "/TN",
            WINDOWS_TASK_NAME,
            "/F",
            command_runner=transaction.command_runner,
        ),
        command_runner=transaction.command_runner,
    )
    transaction.mutation_results.append(deleted)
    if not deleted.ok:
        transaction.error = "scheduled-task rollback deletion failed"


def _existing_registration_can_be_replaced(
    transaction: _WindowsRestoreTransaction,
    current: _CommandResult,
) -> bool:
    safe = bool(_windows_xml_owned(current.stdout) and _manifest_owned(transaction.ctx))
    if not safe:
        return False
    recheck_state, recheck = _query_restore_registration(transaction)
    return bool(
        recheck_state == "present"
        and _windows_xml_owned(recheck.stdout)
        and hmac.compare_digest(recheck.stdout, current.stdout)
    )


def _select_windows_restore_force(
    transaction: _WindowsRestoreTransaction,
    current_state: str,
    current: _CommandResult,
) -> bool | None:
    if current_state == "present":
        if _existing_registration_can_be_replaced(transaction, current):
            return True
        transaction.error = "unsafe Windows rollback refused: task ownership changed"
        return None
    if current_state == "absent":
        recheck_state, _recheck = _query_restore_registration(transaction)
        if recheck_state == "absent":
            return False
        transaction.error = "unsafe Windows rollback refused: task absence changed"
        return None
    transaction.error = "unsafe Windows rollback refused: task state is indeterminate"
    return None


def _restore_prior_windows_registration(
    transaction: _WindowsRestoreTransaction,
    current_state: str,
    current: _CommandResult,
) -> None:
    force = _select_windows_restore_force(transaction, current_state, current)
    if transaction.error is not None or force is None:
        return
    restored = _register_windows_xml(
        transaction.ctx,
        cast(str, transaction.prior_task),
        force=force,
        command_runner=transaction.command_runner,
    )
    transaction.mutation_results.append(restored)
    if not restored.ok:
        transaction.error = "scheduled-task rollback registration failed"


def _restore_windows_registration(transaction: _WindowsRestoreTransaction) -> None:
    current_state, current = _query_restore_registration(transaction)
    if transaction.prior_task is None:
        _delete_created_windows_registration(transaction, current_state, current)
        return
    _restore_prior_windows_registration(transaction, current_state, current)


def _restore_windows_manifest(transaction: _WindowsRestoreTransaction) -> None:
    unsafe_conflict = bool(
        transaction.error and transaction.error.startswith("unsafe Windows rollback refused")
    )
    try:
        if unsafe_conflict and _manifest_owned(transaction.ctx):
            _restore_file(transaction.ctx.manifest_path, None)
            transaction.error = f"{transaction.error}; ownership manifest removed"
        elif not unsafe_conflict:
            _restore_file(transaction.ctx.manifest_path, transaction.prior_manifest)
    except (ConfigurationError, OSError, RuntimeError) as exc:
        transaction.error = transaction.error or str(exc)


def _prior_registration_matches(
    transaction: _WindowsRestoreTransaction,
    state: str,
    result: _CommandResult,
) -> bool:
    return bool(
        state == "present"
        and _windows_xml_owned(result.stdout)
        and _windows_task_properties(result.stdout)
        == _windows_task_properties(cast(str, transaction.prior_task))
    )


def _verify_restored_windows_registration(
    transaction: _WindowsRestoreTransaction,
) -> None:
    if transaction.prior_task is None or transaction.error is not None:
        return
    restored_state, restored = _query_restore_registration(transaction)
    if not _prior_registration_matches(transaction, restored_state, restored):
        transaction.error = "Windows rollback registration verification failed"
        return
    transaction.restored_xml = restored.stdout


def _set_restored_windows_active_state(
    transaction: _WindowsRestoreTransaction,
) -> None:
    exact = _assert_windows_task_unchanged(
        transaction.ctx,
        cast(str, transaction.restored_xml),
        command_runner=transaction.command_runner,
    )
    transaction.results.append(exact)
    active_result = _run(
        windows_system_command(
            "schtasks.exe",
            "/Run" if transaction.prior_active else "/End",
            "/TN",
            WINDOWS_TASK_NAME,
            command_runner=transaction.command_runner,
        ),
        command_runner=transaction.command_runner,
    )
    transaction.mutation_results.append(active_result)
    transaction.results.append(active_result)
    if not active_result.ok:
        transaction.error = "Windows rollback active-state restoration failed"
        return
    reached, state_queries = _wait_windows_running_state(
        transaction.prior_active,
        command_runner=transaction.command_runner,
    )
    transaction.results.extend(state_queries)
    if not reached:
        transaction.error = "Windows rollback active-state transition did not settle"


def _restore_windows_active_state(transaction: _WindowsRestoreTransaction) -> None:
    if (
        transaction.prior_task is None
        or transaction.error is not None
        or transaction.restored_xml is None
    ):
        return
    running, status_query = _windows_running_state(command_runner=transaction.command_runner)
    transaction.results.append(status_query)
    if running is None:
        transaction.error = "Windows rollback active-state verification is indeterminate"
    elif running is not transaction.prior_active:
        _set_restored_windows_active_state(transaction)


def _execute_windows_restore(transaction: _WindowsRestoreTransaction) -> None:
    try:
        _restore_windows_registration(transaction)
        _restore_windows_manifest(transaction)
        transaction.results.extend(transaction.mutation_results)
        _verify_restored_windows_registration(transaction)
        _restore_windows_active_state(transaction)
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        transaction.error = transaction.error or str(exc)


def _verify_windows_restore(
    transaction: _WindowsRestoreTransaction,
) -> _RollbackOutcome:
    verification_state, verification = _query_restore_registration(transaction)
    if transaction.prior_task is None:
        registration_ok = verification_state == "absent"
        active_ok = True
    else:
        registration_ok = _prior_registration_matches(transaction, verification_state, verification)
        active, active_query = _windows_running_state(command_runner=transaction.command_runner)
        transaction.results.append(active_query)
        active_ok = active is transaction.prior_active
    semantic_ok = bool(
        registration_ok
        and active_ok
        and _file_matches(transaction.ctx.manifest_path, transaction.prior_manifest)
    )
    succeeded = bool(
        transaction.error is None
        and all(result.ok for result in transaction.mutation_results)
        and semantic_ok
    )
    return _RollbackOutcome(
        commands=[result.public() for result in transaction.results],
        succeeded=succeeded,
        error=transaction.error or (None if succeeded else "Windows rollback verification failed"),
    )


def _restore_windows_state(
    ctx: _Context,
    *,
    prior_task: str | None,
    prior_manifest: bytes | None,
    prior_active: bool,
    created_registration: bool = False,
    command_runner: CommandRunner | None,
) -> _RollbackOutcome:
    transaction = _WindowsRestoreTransaction(
        ctx=ctx,
        prior_task=prior_task,
        prior_manifest=prior_manifest,
        prior_active=prior_active,
        created_registration=created_registration,
        command_runner=command_runner,
    )
    _execute_windows_restore(transaction)
    return _verify_windows_restore(transaction)
