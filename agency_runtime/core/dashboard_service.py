"""User-scoped lifecycle management for the local operations dashboard.

The service manager owns registration only. Dashboard credentials remain
process-local and never appear in service definitions, manifests, argv, command
results, or logs.

Every public function accepts injectable home, platform, Python executable, and
command runner boundaries. An explicit home without a runner suppresses native
commands, matching the host installer safety contract.
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence
from xml.sax.saxutils import escape as xml_escape

from agency_runtime import __version__ as PACKAGE_VERSION
from agency_runtime.core.configuration import ConfigurationError, restrict_private_file


OWNER_ID = "agency-runtime"
OWNER_MARKER = "Managed by Agency Runtime; owner=agency-runtime"
SERVICE_ID = "dashboard"
SYSTEMD_UNIT_NAME = "agency-runtime-dashboard.service"
WINDOWS_TASK_NAME = "Agency Runtime Dashboard"
MANIFEST_SCHEMA_VERSION = 1
WINDOWS_TASK_XML_NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"
_SERVICE_LOCK_TIMEOUT_SECONDS = 5.0
_WINDOWS_TASK_PROBE_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$s=New-Object -ComObject Schedule.Service;$s.Connect();"
    "try{$t=$s.GetFolder('\\').GetTask('Agency Runtime Dashboard')}"
    "catch{"
    "if($_.Exception.HResult -in @(-2147024894,-2147024893)){"
    "[Console]::Out.Write('ABSENT');exit 0};throw};"
    "[Console]::Out.Write(('PRESENT:{0}' -f [int]$t.State))"
)

CommandRunner = Callable[..., Any]
ReadinessProbe = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class _CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def public(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "command": list(self.command),
            "returncode": self.returncode,
            "ok": self.ok,
        }
        if not self.ok:
            detail = (
                self.stderr or self.stdout or "service-manager command failed"
            ).strip()
            value["error"] = detail[:500]
        return value


@dataclass(frozen=True, slots=True)
class _RollbackOutcome:
    commands: list[dict[str, Any]]
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class _Context:
    platform: str
    home: Path
    config_path: Path
    python_executable: Path
    manager: str
    registration: str
    unit_path: Path | None
    manifest_path: Path
    worker_argv: tuple[str, ...]
    windows_user: str | None


def _validate_text(value: str, *, label: str) -> str:
    text = str(value)
    if not text:
        raise ValueError(f"{label} must not be empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in text):
        raise ValueError(f"{label} contains a forbidden control character")
    return text


def _normalise_platform(value: str | None) -> str:
    name = _validate_text(value or platform.system(), label="platform").strip().lower()
    if name in {"windows", "win32", "nt"}:
        return "windows"
    if name in {"linux", "gnu/linux"}:
        return "linux"
    return name


def _resolved_path(value: str | Path, *, label: str) -> Path:
    return Path(_validate_text(str(value), label=label)).expanduser().resolve()


def _home(home_dir: str | Path | None) -> Path:
    return _resolved_path(
        home_dir if home_dir is not None else Path.home(), label="home directory"
    )


def _config_path(
    home: Path,
    home_dir: str | Path | None,
    config_path: str | Path | None,
) -> Path:
    if config_path is not None:
        return _resolved_path(config_path, label="config path")
    if home_dir is None and os.environ.get("AGENCY_CONFIG_PATH"):
        return _resolved_path(os.environ["AGENCY_CONFIG_PATH"], label="config path")
    return _resolved_path(home / ".agency-runtime" / "agency.yaml", label="config path")


def _windows_current_user_sid() -> str | None:
    """Return the current process token SID without invoking a shell."""

    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

        class TokenUser(ctypes.Structure):
            _fields_ = [("User", SidAndAttributes)]

        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        open_token = advapi32.OpenProcessToken
        open_token.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.HANDLE),
        ]
        open_token.restype = wintypes.BOOL
        get_token = advapi32.GetTokenInformation
        get_token.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_token.restype = wintypes.BOOL
        convert_sid = advapi32.ConvertSidToStringSidW
        convert_sid.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        convert_sid.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]

        token = wintypes.HANDLE()
        if not open_token(kernel32.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
            return None
        sid_string = wintypes.LPWSTR()
        try:
            required = wintypes.DWORD()
            get_token(token, 1, None, 0, ctypes.byref(required))  # TokenUser
            if required.value == 0:
                return None
            buffer = ctypes.create_string_buffer(required.value)
            if not get_token(token, 1, buffer, required, ctypes.byref(required)):
                return None
            token_user = ctypes.cast(buffer, ctypes.POINTER(TokenUser)).contents
            if not convert_sid(token_user.User.Sid, ctypes.byref(sid_string)):
                return None
            return str(sid_string.value)
        finally:
            if sid_string:
                kernel32.LocalFree(sid_string)
            kernel32.CloseHandle(token)
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def build_service_worker_argv(
    *,
    home_dir: str | Path | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
) -> list[str]:
    """Build the credential-free dashboard worker command.

    The service-mode CLI loads the configured dashboard port from the resolved
    config file; the registration therefore does not duplicate mutable config.
    """
    home = _home(home_dir)
    executable = _resolved_path(
        python_executable if python_executable is not None else sys.executable,
        label="Python executable",
    )
    config = _config_path(home, home_dir, config_path)
    argv = [
        str(executable),
        "-m",
        "agency_runtime.cli",
        "dashboard",
        "--service-mode",
        "--config",
        str(config),
    ]
    return [_validate_text(item, label="service argument") for item in argv]


def _context(
    *,
    home_dir: str | Path | None,
    platform_name: str | None,
    config_path: str | Path | None,
    python_executable: str | Path | None,
) -> _Context | None:
    target = _normalise_platform(platform_name)
    if target not in {"windows", "linux"}:
        return None
    home = _home(home_dir)
    config = _config_path(home, home_dir, config_path)
    executable = _resolved_path(
        python_executable if python_executable is not None else sys.executable,
        label="Python executable",
    )
    worker = tuple(
        build_service_worker_argv(
            home_dir=home,
            config_path=config,
            python_executable=executable,
        )
    )
    runtime_root = home / ".agency-runtime"
    windows_user: str | None = None
    if target == "windows":
        manager = "schtasks"
        registration = WINDOWS_TASK_NAME
        unit_path = None
        username = os.environ.get("USERNAME") or getpass.getuser()
        domain = os.environ.get("USERDOMAIN")
        account_name = f"{domain}\\{username}" if domain and domain != "." else username
        windows_user = _validate_text(
            _windows_current_user_sid() or account_name,
            label="Windows user",
        )
    else:
        manager = "systemd-user"
        registration = SYSTEMD_UNIT_NAME
        xdg_config = os.environ.get("XDG_CONFIG_HOME") if home_dir is None else None
        xdg_root = Path(xdg_config).expanduser() if xdg_config else None
        config_root = (
            xdg_root.resolve()
            if xdg_root is not None and xdg_root.is_absolute()
            else home / ".config"
        )
        unit_path = config_root / "systemd" / "user" / SYSTEMD_UNIT_NAME
    return _Context(
        platform=target,
        home=home,
        config_path=config,
        python_executable=executable,
        manager=manager,
        registration=registration,
        unit_path=unit_path,
        manifest_path=runtime_root / "services" / "dashboard-service.json",
        worker_argv=worker,
        windows_user=windows_user,
    )


def _run(
    command: Sequence[str],
    *,
    command_runner: CommandRunner | None,
    timeout: float = 30.0,
) -> _CommandResult:
    argv = tuple(
        _validate_text(str(item), label="service-manager argument") for item in command
    )
    try:
        if command_runner is None:
            raw = subprocess.run(  # noqa: S603 - fixed argv, never a shell
                list(argv),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        else:
            try:
                raw = command_runner(list(argv), timeout=timeout)
            except TypeError:
                raw = command_runner(list(argv))
    except subprocess.TimeoutExpired as exc:
        return _CommandResult(
            argv, 124, str(exc.stdout or ""), "service-manager command timed out"
        )
    except OSError as exc:
        return _CommandResult(argv, 127, "", f"{type(exc).__name__}: {exc}")
    if isinstance(raw, _CommandResult):
        return _CommandResult(argv, raw.returncode, raw.stdout, raw.stderr)
    if isinstance(raw, Mapping):
        return _CommandResult(
            argv,
            int(raw.get("returncode", raw.get("exit_code", 0))),
            str(raw.get("stdout", "") or ""),
            str(raw.get("stderr", raw.get("error", "")) or ""),
        )
    return _CommandResult(
        argv,
        int(getattr(raw, "returncode", 0)),
        str(getattr(raw, "stdout", "") or ""),
        str(getattr(raw, "stderr", "") or ""),
    )


def _systemd_quote(value: str) -> str:
    text = _validate_text(value, label="systemd argument")
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("%", "%%")
        .replace("$", "$$")
    )
    return f'"{escaped}"'


def _windows_action(argv: Sequence[str]) -> str:
    values = [_validate_text(str(item), label="Windows task argument") for item in argv]
    return subprocess.list2cmdline(values)


def _windows_create_command(xml_path: str | Path, *, force: bool) -> list[str]:
    command = [
        "schtasks.exe",
        "/Create",
        "/TN",
        WINDOWS_TASK_NAME,
        "/XML",
        str(xml_path),
    ]
    if force:
        command.append("/F")
    return command


def _windows_task_content(ctx: _Context) -> str:
    """Render the explicit, durable current-user Task Scheduler contract."""

    assert ctx.windows_user is not None
    command = xml_escape(str(ctx.worker_argv[0]))
    arguments = xml_escape(_windows_action(ctx.worker_argv[1:]))
    current_user = xml_escape(ctx.windows_user)
    description = xml_escape(OWNER_MARKER)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<Task version="1.4" xmlns="{WINDOWS_TASK_XML_NAMESPACE}">\n'
        "  <RegistrationInfo>\n"
        f"    <Description>{description}</Description>\n"
        f"    <Source>{OWNER_ID}</Source>\n"
        "  </RegistrationInfo>\n"
        "  <Triggers>\n"
        "    <LogonTrigger>\n"
        "      <Enabled>true</Enabled>\n"
        f"      <UserId>{current_user}</UserId>\n"
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
    try:
        root = ET.fromstring(content)
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
    assert all(element is not None for element in elements)
    settings_required = (
        "MultipleInstancesPolicy",
        "DisallowStartIfOnBatteries",
        "StopIfGoingOnBatteries",
        "AllowHardTerminate",
        "StartWhenAvailable",
        "RunOnlyIfNetworkAvailable",
        "IdleSettings",
        "AllowStartOnDemand",
        "Enabled",
        "Hidden",
        "RunOnlyIfIdle",
        "WakeToRun",
        "ExecutionTimeLimit",
        "Priority",
        "RestartOnFailure",
    )
    default_false_settings = (
        "DisallowStartOnRemoteAppSession",
        "UseUnifiedSchedulingEngine",
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
            _xml_children_match(logon, required=("Enabled", "UserId")),
            _xml_children_match(principals, required=("Principal",)),
            _xml_children_match(
                principal,
                required=("UserId", "LogonType", "RunLevel"),
                attributes={"id": "CurrentUser"},
            ),
            _xml_children_match(
                settings, required=settings_required, optional=default_false_settings
            ),
            _xml_children_match(idle, required=("StopOnIdleEnd", "RestartOnIdle")),
            _xml_children_match(restart, required=("Interval", "Count")),
            _xml_children_match(
                actions, required=("Exec",), attributes={"Context": "CurrentUser"}
            ),
            _xml_children_match(execute, required=("Command", "Arguments")),
        )
    )
    if not schema_ok:
        return None
    scalar_paths = (
        "t:RegistrationInfo/t:Description",
        "t:RegistrationInfo/t:Source",
        "t:Triggers/t:LogonTrigger/t:Enabled",
        "t:Triggers/t:LogonTrigger/t:UserId",
        "t:Principals/t:Principal/t:UserId",
        "t:Principals/t:Principal/t:LogonType",
        "t:Principals/t:Principal/t:RunLevel",
        "t:Settings/t:MultipleInstancesPolicy",
        "t:Settings/t:DisallowStartIfOnBatteries",
        "t:Settings/t:StopIfGoingOnBatteries",
        "t:Settings/t:AllowHardTerminate",
        "t:Settings/t:StartWhenAvailable",
        "t:Settings/t:RunOnlyIfNetworkAvailable",
        "t:Settings/t:IdleSettings/t:StopOnIdleEnd",
        "t:Settings/t:IdleSettings/t:RestartOnIdle",
        "t:Settings/t:AllowStartOnDemand",
        "t:Settings/t:Enabled",
        "t:Settings/t:Hidden",
        "t:Settings/t:RunOnlyIfIdle",
        "t:Settings/t:WakeToRun",
        "t:Settings/t:ExecutionTimeLimit",
        "t:Settings/t:Priority",
        "t:Settings/t:RestartOnFailure/t:Interval",
        "t:Settings/t:RestartOnFailure/t:Count",
        "t:Actions/t:Exec/t:Command",
        "t:Actions/t:Exec/t:Arguments",
    )
    if not _xml_scalar_nodes_are_plain(root, scalar_paths):
        return None
    for parent, nested in (
        (registration, frozenset()),
        (settings, frozenset({"IdleSettings", "RestartOnFailure"})),
    ):
        for child in parent:
            name = child.tag[len(namespace) :]
            if name not in nested and (child.attrib or list(child)):
                return None
    for name in default_false_settings:
        node = settings.find(namespace + name)
        if node is not None and (node.text or "").strip().casefold() != "false":
            return None
    return {
        "description": _xml_text(root, "t:RegistrationInfo/t:Description"),
        "source": _xml_text(root, "t:RegistrationInfo/t:Source"),
        "trigger_enabled": _xml_text(root, "t:Triggers/t:LogonTrigger/t:Enabled"),
        "trigger_user": _xml_text(root, "t:Triggers/t:LogonTrigger/t:UserId"),
        "principal_user": _xml_text(root, "t:Principals/t:Principal/t:UserId"),
        "logon_type": _xml_text(root, "t:Principals/t:Principal/t:LogonType"),
        "run_level": _xml_text(root, "t:Principals/t:Principal/t:RunLevel"),
        "multiple_instances": _xml_text(root, "t:Settings/t:MultipleInstancesPolicy"),
        "battery_start": _xml_text(root, "t:Settings/t:DisallowStartIfOnBatteries"),
        "battery_stop": _xml_text(root, "t:Settings/t:StopIfGoingOnBatteries"),
        "hard_terminate": _xml_text(root, "t:Settings/t:AllowHardTerminate"),
        "start_when_available": _xml_text(root, "t:Settings/t:StartWhenAvailable"),
        "network_required": _xml_text(root, "t:Settings/t:RunOnlyIfNetworkAvailable"),
        "stop_on_idle_end": _xml_text(
            root, "t:Settings/t:IdleSettings/t:StopOnIdleEnd"
        ),
        "restart_on_idle": _xml_text(root, "t:Settings/t:IdleSettings/t:RestartOnIdle"),
        "start_on_demand": _xml_text(root, "t:Settings/t:AllowStartOnDemand"),
        "enabled": _xml_text(root, "t:Settings/t:Enabled"),
        "hidden": _xml_text(root, "t:Settings/t:Hidden"),
        "run_only_if_idle": _xml_text(root, "t:Settings/t:RunOnlyIfIdle"),
        "wake_to_run": _xml_text(root, "t:Settings/t:WakeToRun"),
        "execution_limit": _xml_text(root, "t:Settings/t:ExecutionTimeLimit"),
        "priority": _xml_text(root, "t:Settings/t:Priority"),
        "restart_interval": _xml_text(root, "t:Settings/t:RestartOnFailure/t:Interval"),
        "restart_count": _xml_text(root, "t:Settings/t:RestartOnFailure/t:Count"),
        "actions_context": _xml_attribute(root, "t:Actions", "Context"),
        "command": _xml_text(root, "t:Actions/t:Exec/t:Command"),
        "arguments": _xml_text(root, "t:Actions/t:Exec/t:Arguments"),
    }


def _windows_xml_owned(content: str) -> bool:
    properties = _windows_task_properties(content)
    return bool(
        properties
        and properties["description"] == OWNER_MARKER
        and properties["source"] == OWNER_ID
    )


def _windows_definition_matches(ctx: _Context, content: str) -> bool:
    return _windows_task_properties(content) == _windows_task_properties(
        _windows_task_content(ctx)
    )


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


def _runtime_fingerprint(ctx: _Context) -> str:
    payload = json.dumps(
        {
            "package_version": PACKAGE_VERSION,
            "python_executable": str(ctx.python_executable),
            "worker_argv": list(ctx.worker_argv),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _manifest_value(ctx: _Context) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "owner": OWNER_ID,
        "service": SERVICE_ID,
        "platform": ctx.platform,
        "manager": ctx.manager,
        "registration": ctx.registration,
        "worker_argv": list(ctx.worker_argv),
        "config_path": str(ctx.config_path),
        "package_version": PACKAGE_VERSION,
        "runtime_fingerprint": _runtime_fingerprint(ctx),
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_manifest(ctx: _Context) -> dict[str, Any] | None:
    try:
        value = json.loads(ctx.manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _manifest_owned(ctx: _Context, value: Mapping[str, Any] | None = None) -> bool:
    candidate = value if value is not None else _read_manifest(ctx)
    return bool(
        candidate
        and candidate.get("schema_version") == MANIFEST_SCHEMA_VERSION
        and candidate.get("owner") == OWNER_ID
        and candidate.get("service") == SERVICE_ID
        and candidate.get("platform") == ctx.platform
        and candidate.get("manager") == ctx.manager
        and candidate.get("registration") == ctx.registration
    )


def _manifest_current(ctx: _Context, value: Mapping[str, Any] | None = None) -> bool:
    candidate = value if value is not None else _read_manifest(ctx)
    return bool(
        _manifest_owned(ctx, candidate)
        and candidate is not None
        and candidate.get("worker_argv") == list(ctx.worker_argv)
        and candidate.get("config_path") == str(ctx.config_path)
        and candidate.get("package_version") == PACKAGE_VERSION
        and candidate.get("runtime_fingerprint") == _runtime_fingerprint(ctx)
    )


def _atomic_write(path: Path, content: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    handle = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, mode)
        restrict_private_file(temporary)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            handle = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        os.replace(temporary, path)
        restrict_private_file(path)
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


@contextmanager
def _service_lock(
    ctx: _Context, *, timeout: float = _SERVICE_LOCK_TIMEOUT_SECONDS
) -> Iterator[None]:
    """Serialize service ownership checks and mutations across processes."""

    ctx.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        ctx.manifest_path.parent.chmod(0o700)
    lock_path = ctx.manifest_path.with_name(".dashboard-service.lock")
    handle = open(lock_path, "a+b")
    locked = False
    try:
        # A newly created lock remains empty until its owner-only policy is set.
        restrict_private_file(lock_path)
        if lock_path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        restrict_private_file(lock_path)
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "dashboard service is busy; retry the operation"
                    ) from exc
                time.sleep(0.025)
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _restore_file(path: Path, prior: bytes | None) -> None:
    if prior is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    handle = descriptor
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(handle, 0o600)
        restrict_private_file(temporary)
        with os.fdopen(handle, "wb") as stream:
            handle = -1
            stream.write(prior)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        os.replace(temporary, path)
        restrict_private_file(path)
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def _write_manifest(ctx: _Context) -> bool:
    current = _read_manifest(ctx)
    if ctx.manifest_path.exists() and not _manifest_owned(ctx, current):
        raise RuntimeError(
            "refusing to replace an invalid dashboard service ownership manifest"
        )
    if _manifest_current(ctx, current):
        return False
    _atomic_write(ctx.manifest_path, json.dumps(_manifest_value(ctx), indent=2) + "\n")
    return True


def _register_windows_xml(
    ctx: _Context,
    content: str,
    *,
    force: bool,
    command_runner: CommandRunner | None,
) -> _CommandResult:
    ctx.manifest_path.parent.mkdir(parents=True, exist_ok=True)
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
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            handle = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        return _run(
            _windows_create_command(temporary, force=force),
            command_runner=command_runner,
        )
    finally:
        if handle >= 0:
            os.close(handle)
        temporary.unlink(missing_ok=True)


def _base(action: str, ctx: _Context) -> dict[str, Any]:
    return {
        "action": action,
        "platform": ctx.platform,
        "manager": ctx.manager,
        "registration": ctx.registration,
        "manifest_path": str(ctx.manifest_path),
        "worker_argv": list(ctx.worker_argv),
    }


def _unsupported(action: str, platform_name: str | None) -> dict[str, Any]:
    target = _normalise_platform(platform_name)
    return {
        "ok": False,
        "exit_code": 2,
        "action": action,
        "platform": target,
        "supported": False,
        "error": f"dashboard services are supported only on Windows and Linux, not {target}",
    }


def _query_windows_task_probe(
    *, command_runner: CommandRunner | None, timeout: float = 10.0
) -> _CommandResult:
    return _run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _WINDOWS_TASK_PROBE_SCRIPT,
        ],
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
    return _run(
        ["schtasks.exe", "/Query", "/TN", WINDOWS_TASK_NAME, "/XML"],
        command_runner=command_runner,
        timeout=timeout,
    )


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


def _capture_owned_windows_task(
    ctx: _Context, *, command_runner: CommandRunner | None
) -> tuple[str, _CommandResult]:
    if not _manifest_owned(ctx):
        raise RuntimeError(
            "dashboard service ownership manifest changed before mutation"
        )
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


def _assert_windows_task_absent(
    *, command_runner: CommandRunner | None
) -> _CommandResult:
    state, result = _query_windows_registration(command_runner=command_runner)
    if state != "absent":
        raise RuntimeError(
            "scheduled-task absence could not be confirmed before mutation"
        )
    return result


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
    available, probe, registration_state = _manager_probe(
        ctx, home_dir=home_dir, command_runner=command_runner
    )
    ownership_blocked = False
    state_indeterminate = False
    definition_drift: bool | None = None
    if ctx.platform == "linux":
        assert ctx.unit_path is not None
        unit_exists = ctx.unit_path.exists()
        try:
            existing_unit = (
                ctx.unit_path.read_text(encoding="utf-8") if unit_exists else ""
            )
        except (OSError, UnicodeError):
            existing_unit = ""
            state_indeterminate = True
        unit_owned = bool(
            unit_exists
            and existing_unit.startswith(f"# {OWNER_MARKER}\n")
            and _manifest_owned(ctx)
        )
        ownership_blocked = bool(
            (unit_exists and not unit_owned and not state_indeterminate)
            or (ctx.manifest_path.exists() and not _manifest_owned(ctx))
        )
        if unit_owned:
            definition_drift = existing_unit != _unit_content(ctx)
        commands = (
            []
            if ownership_blocked or state_indeterminate
            else [
                ["systemctl", "--user", "daemon-reload"],
                ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME],
            ]
        )
        registration_path = str(ctx.unit_path)
        content: str | None = _unit_content(ctx)
    else:
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
            or (ctx.manifest_path.exists() and not _manifest_owned(ctx))
        )
        if task_owned and probe is not None:
            definition_drift = not _windows_definition_matches(ctx, probe.stdout)
        commands = (
            []
            if ownership_blocked or state_indeterminate
            else [
                _windows_create_command("<owner-private-task-xml>", force=task_exists),
                ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK_NAME],
            ]
        )
        registration_path = WINDOWS_TASK_NAME
        content = _windows_task_content(ctx)
    value: dict[str, Any] = {
        **_base("plan", ctx),
        "ok": available is not False
        and not ownership_blocked
        and not state_indeterminate,
        "exit_code": 1
        if available is False or ownership_blocked or state_indeterminate
        else 0,
        "supported": True,
        "dry_run": True,
        "manager_available": available,
        "ready_to_install": available is True
        and not ownership_blocked
        and not state_indeterminate,
        "definition_drift": definition_drift,
        "registration_path": registration_path,
        "registration_content": content,
        "commands": commands,
    }
    if state_indeterminate:
        value["error"] = "service registration state could not be determined"
    elif ownership_blocked:
        value["error"] = (
            "refusing to overwrite a same-name service registration without both "
            "the Agency Runtime definition marker and ownership manifest"
        )
    elif available is False:
        value["manager_probe"] = probe.public() if probe is not None else None
        value["error"] = (
            "the systemd user manager is unavailable"
            if ctx.platform == "linux"
            else "Windows Task Scheduler is unavailable"
        )
    elif available is None:
        value["warning"] = (
            "native manager probing is suppressed for an explicit home without a runner"
        )
    return value


def inspect_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    """Separate registration, ownership, manager, and reachability truth."""
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("inspect", platform_name)
    available, probe, registration_state = _manager_probe(
        ctx, home_dir=home_dir, command_runner=command_runner
    )
    manifest = _read_manifest(ctx)
    manifest_owned = _manifest_owned(ctx, manifest)
    if reachability_probe is not None and readiness_probe is not None:
        raise ValueError(
            "pass reachability_probe, not both reachability and readiness probes"
        )
    immediate_probe = reachability_probe or readiness_probe
    enabled: bool | None = None
    active: bool | None = None
    registration_owned = False
    definition_drift: bool | None = None
    if ctx.platform == "linux":
        assert ctx.unit_path is not None
        installed: bool | None = ctx.unit_path.exists()
        try:
            unit = ctx.unit_path.read_text(encoding="utf-8") if installed else ""
        except (OSError, UnicodeError):
            unit = ""
        registration_owned = bool(installed and unit.startswith(f"# {OWNER_MARKER}\n"))
        owned = bool(registration_owned and manifest_owned)
        definition_drift = (
            bool(registration_owned and unit != _unit_content(ctx))
            if installed
            else None
        )
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
    else:
        query_state = registration_state or "indeterminate"
        installed = (
            True
            if query_state == "present"
            else False
            if query_state == "absent"
            else None
        )
        task_xml = probe.stdout if installed and probe is not None else ""
        registration_owned = bool(installed and _windows_xml_owned(task_xml))
        owned = bool(registration_owned and manifest_owned)
        if registration_owned:
            definition_drift = not _windows_definition_matches(ctx, task_xml)
            properties = _windows_task_properties(task_xml)
            enabled = bool(
                properties and properties.get("enabled").casefold() == "true"
            )
    reachable: bool | None = None
    if immediate_probe is not None:
        try:
            reachable = bool(immediate_probe())
        except Exception:
            reachable = False
    if ctx.platform == "windows":
        active = reachable
    return {
        **_base("inspect", ctx),
        "ok": True,
        "exit_code": 0,
        "supported": True,
        "manager_available": available,
        "installed": installed,
        "owned": owned,
        "manifest_owned": manifest_owned,
        "manifest_current": _manifest_current(ctx, manifest),
        "registration_owned": registration_owned,
        "definition_drift": definition_drift,
        "enabled": enabled,
        "active": active,
        "reachable": reachable,
        "registration_path": str(ctx.unit_path)
        if ctx.unit_path is not None
        else WINDOWS_TASK_NAME,
    }


def _preflight(
    action: str,
    ctx: _Context,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    reachability_probe: ReadinessProbe | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    state = inspect_dashboard_service(
        home_dir=home_dir,
        platform_name=ctx.platform,
        config_path=ctx.config_path,
        python_executable=ctx.python_executable,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
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
        not state.get("installed")
        and ctx.manifest_path.exists()
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


def _file_matches(path: Path, expected: bytes | None) -> bool:
    try:
        return (
            path.read_bytes() == expected if expected is not None else not path.exists()
        )
    except OSError:
        return False


def _restore_systemd_state(
    ctx: _Context,
    *,
    prior_unit: bytes | None,
    prior_manifest: bytes | None,
    prior_enabled: bool,
    prior_active: bool,
    command_runner: CommandRunner | None,
) -> _RollbackOutcome:
    assert ctx.unit_path is not None
    results: list[_CommandResult] = []
    mutation_results: list[_CommandResult] = []
    restore_error: str | None = None
    try:
        if prior_unit is None:
            mutation_results.append(
                _run(
                    ["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT_NAME],
                    command_runner=command_runner,
                )
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
        True
        if prior_unit is None
        else _systemd_enabled_state(enabled_query) is prior_enabled
    )
    semantic_ok = bool(
        registration_ok
        and enabled_ok
        and _systemd_active_state(active_query) is prior_active
    )
    succeeded = bool(
        restore_error is None
        and all(result.ok for result in mutation_results)
        and semantic_ok
    )
    error = restore_error or (
        None if succeeded else "systemd rollback verification failed"
    )
    return _RollbackOutcome(
        commands=[result.public() for result in results],
        succeeded=succeeded,
        error=error,
    )


def _export_owned_windows_task(
    ctx: _Context,
    *,
    command_runner: CommandRunner | None,
) -> tuple[str, _CommandResult]:
    return _capture_owned_windows_task(ctx, command_runner=command_runner)


def _restore_windows_state(
    ctx: _Context,
    *,
    prior_task: str | None,
    prior_manifest: bytes | None,
    prior_active: bool,
    created_registration: bool = False,
    command_runner: CommandRunner | None,
) -> _RollbackOutcome:
    results: list[_CommandResult] = []
    mutation_results: list[_CommandResult] = []
    error: str | None = None
    restored_xml: str | None = None
    try:
        current_state, current = _query_windows_registration(
            command_runner=command_runner
        )
        results.append(current)
        if prior_task is None:
            if created_registration:
                safe_created = bool(
                    current_state == "present"
                    and _windows_xml_owned(current.stdout)
                    and _windows_definition_matches(ctx, current.stdout)
                )
                if not safe_created:
                    error = "unsafe Windows rollback refused: created task ownership changed"
                else:
                    recheck_state, recheck = _query_windows_registration(
                        command_runner=command_runner
                    )
                    results.append(recheck)
                    if not (
                        recheck_state == "present"
                        and _windows_xml_owned(recheck.stdout)
                        and hmac.compare_digest(recheck.stdout, current.stdout)
                    ):
                        error = "unsafe Windows rollback refused: created task changed"
                    else:
                        deleted = _run(
                            [
                                "schtasks.exe",
                                "/Delete",
                                "/TN",
                                WINDOWS_TASK_NAME,
                                "/F",
                            ],
                            command_runner=command_runner,
                        )
                        mutation_results.append(deleted)
                        if not deleted.ok:
                            error = "scheduled-task rollback deletion failed"
        else:
            force = current_state == "present"
            if force:
                safe_current = bool(
                    _windows_xml_owned(current.stdout) and _manifest_owned(ctx)
                )
                if safe_current:
                    recheck_state, recheck = _query_windows_registration(
                        command_runner=command_runner
                    )
                    results.append(recheck)
                    safe_current = bool(
                        recheck_state == "present"
                        and _windows_xml_owned(recheck.stdout)
                        and hmac.compare_digest(recheck.stdout, current.stdout)
                    )
                if not safe_current:
                    error = "unsafe Windows rollback refused: task ownership changed"
            elif current_state == "absent":
                recheck_state, recheck = _query_windows_registration(
                    command_runner=command_runner
                )
                results.append(recheck)
                if recheck_state != "absent":
                    error = "unsafe Windows rollback refused: task absence changed"
            else:
                error = "unsafe Windows rollback refused: task state is indeterminate"
            if error is None:
                restored = _register_windows_xml(
                    ctx,
                    prior_task,
                    force=force,
                    command_runner=command_runner,
                )
                mutation_results.append(restored)
                if not restored.ok:
                    error = "scheduled-task rollback registration failed"
        try:
            _restore_file(ctx.manifest_path, prior_manifest)
        except (ConfigurationError, OSError, RuntimeError) as exc:
            error = error or str(exc)
        results.extend(mutation_results)
        if prior_task is not None and error is None:
            restored_state, restored = _query_windows_registration(
                command_runner=command_runner
            )
            results.append(restored)
            if not (
                restored_state == "present"
                and _windows_xml_owned(restored.stdout)
                and _windows_task_properties(restored.stdout)
                == _windows_task_properties(prior_task)
            ):
                error = "Windows rollback registration verification failed"
            else:
                restored_xml = restored.stdout
        if prior_task is not None and error is None and restored_xml is not None:
            running, status_query = _windows_running_state(
                command_runner=command_runner
            )
            results.append(status_query)
            if running is None:
                error = "Windows rollback active-state verification is indeterminate"
            elif running is not prior_active:
                exact = _assert_windows_task_unchanged(
                    ctx, restored_xml, command_runner=command_runner
                )
                results.append(exact)
                active_result = _run(
                    [
                        "schtasks.exe",
                        "/Run" if prior_active else "/End",
                        "/TN",
                        WINDOWS_TASK_NAME,
                    ],
                    command_runner=command_runner,
                )
                mutation_results.append(active_result)
                results.append(active_result)
                if not active_result.ok:
                    error = "Windows rollback active-state restoration failed"
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        error = error or str(exc)
    verification_state, verification = _query_windows_registration(
        command_runner=command_runner
    )
    results.append(verification)
    if prior_task is None:
        registration_ok = verification_state == "absent"
        active_ok = True
    else:
        registration_ok = bool(
            verification_state == "present"
            and _windows_xml_owned(verification.stdout)
            and _windows_task_properties(verification.stdout)
            == _windows_task_properties(prior_task)
        )
        active, active_query = _windows_running_state(command_runner=command_runner)
        results.append(active_query)
        active_ok = active is prior_active
    semantic_ok = bool(
        registration_ok
        and active_ok
        and _file_matches(ctx.manifest_path, prior_manifest)
    )
    succeeded = bool(
        error is None and all(result.ok for result in mutation_results) and semantic_ok
    )
    return _RollbackOutcome(
        commands=[result.public() for result in results],
        succeeded=succeeded,
        error=error or (None if succeeded else "Windows rollback verification failed"),
    )


def _cleanup_stale_runtime(
    ctx: _Context,
    _reachability_probe: ReadinessProbe | None,
) -> bool:
    from agency_runtime.core.dashboard_runtime import (
        dashboard_service_reachable,
        read_dashboard_runtime,
        remove_dashboard_runtime,
    )

    try:
        descriptor = read_dashboard_runtime(home_dir=ctx.home)
    except ValueError:
        return False
    if dashboard_service_reachable(descriptor=descriptor):
        return False
    return remove_dashboard_runtime(
        home_dir=ctx.home,
        token=descriptor["token"],
        pid=descriptor["pid"],
    )


def install_dashboard_service(
    *,
    home_dir: str | Path | None = None,
    platform_name: str | None = None,
    config_path: str | Path | None = None,
    python_executable: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    reachability_probe: ReadinessProbe | None = None,
    readiness_probe: ReadinessProbe | None = None,
) -> dict[str, Any]:
    """Install, enable, and start the current user's dashboard service."""
    ctx = _context(
        home_dir=home_dir,
        platform_name=platform_name,
        config_path=config_path,
        python_executable=python_executable,
    )
    if ctx is None:
        return _unsupported("install", platform_name)
    try:
        with _service_lock(ctx):
            blocked, state = _preflight(
                "install",
                ctx,
                home_dir=home_dir,
                command_runner=command_runner,
                reachability_probe=reachability_probe,
            )
            if blocked is not None:
                return blocked
            if ctx.platform == "linux":
                return _install_linux(
                    ctx,
                    state,
                    command_runner=command_runner,
                    readiness_probe=readiness_probe,
                )
            return _install_windows(
                ctx,
                state,
                command_runner=command_runner,
                readiness_probe=readiness_probe,
            )
    except (ConfigurationError, OSError, RuntimeError) as exc:
        return _failed("install", ctx, error=str(exc), commands=[])


def _install_linux(
    ctx: _Context,
    state: Mapping[str, Any],
    *,
    command_runner: CommandRunner | None,
    readiness_probe: ReadinessProbe | None,
) -> dict[str, Any]:
    assert ctx.unit_path is not None
    desired = _unit_content(ctx)
    prior_unit = ctx.unit_path.read_bytes() if ctx.unit_path.exists() else None
    prior_manifest = (
        ctx.manifest_path.read_bytes() if ctx.manifest_path.exists() else None
    )
    try:
        prior_text = prior_unit.decode("utf-8") if prior_unit is not None else None
    except UnicodeError:
        return _failed(
            "install", ctx, error="owned systemd unit is not valid UTF-8", commands=[]
        )
    if prior_text is not None and (
        not prior_text.startswith(f"# {OWNER_MARKER}\n") or not _manifest_owned(ctx)
    ):
        return _failed(
            "install",
            ctx,
            error="systemd service ownership changed before mutation",
            commands=[],
        )
    registration_changed = prior_text != desired
    runtime_changed = not bool(state.get("manifest_current"))
    prior_enabled = state.get("enabled") is True
    prior_active = state.get("active") is True
    prior_reachable = state.get("reachable")
    activation_needed = not prior_enabled or not prior_active
    restart_needed = prior_active and (
        registration_changed or runtime_changed or prior_reachable is False
    )
    changed = (
        registration_changed or runtime_changed or activation_needed or restart_needed
    )
    commands: list[dict[str, Any]] = []
    try:
        if registration_changed:
            _atomic_write(ctx.unit_path, desired)
        manifest_changed = _write_manifest(ctx)
        if registration_changed:
            reload_result = _run(
                ["systemctl", "--user", "daemon-reload"],
                command_runner=command_runner,
            )
            commands.append(reload_result.public())
            if not reload_result.ok:
                raise RuntimeError("systemd daemon-reload failed")
        if activation_needed:
            enable_result = _run(
                ["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
            commands.append(enable_result.public())
            if not enable_result.ok:
                raise RuntimeError("systemd enable --now failed")
        elif restart_needed:
            restart_result = _run(
                ["systemctl", "--user", "restart", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
            commands.append(restart_result.public())
            if not restart_result.ok:
                raise RuntimeError("systemd restart after update failed")
        reachable = (
            _readiness(readiness_probe)
            if activation_needed or restart_needed
            else prior_reachable
        )
        if reachable is False:
            raise RuntimeError("dashboard service did not become ready")
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        rollback = _restore_systemd_state(
            ctx,
            prior_unit=prior_unit,
            prior_manifest=prior_manifest,
            prior_enabled=prior_enabled,
            prior_active=prior_active,
            command_runner=command_runner,
        )
        return _failed(
            "install",
            ctx,
            error=str(exc),
            commands=commands,
            rollback=rollback,
        )
    return {
        **_base("install", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": changed or manifest_changed,
        "registration_changed": registration_changed,
        "runtime_changed": runtime_changed,
        "installed": True,
        "enabled": True,
        "active": True if reachable is True else None,
        "reachable": reachable,
        "commands": commands,
    }


def _install_windows(
    ctx: _Context,
    state: Mapping[str, Any],
    *,
    command_runner: CommandRunner | None,
    readiness_probe: ReadinessProbe | None,
) -> dict[str, Any]:
    prior_manifest = (
        ctx.manifest_path.read_bytes() if ctx.manifest_path.exists() else None
    )
    installed = state.get("installed") is True
    registration_changed = not installed or state.get("definition_drift") is True
    runtime_changed = not bool(state.get("manifest_current"))
    prior_reachable = state.get("reachable")
    commands: list[dict[str, Any]] = []
    prior_task: str | None = None
    prior_active = False
    state_mutated = False
    created_registration = False
    try:
        if installed:
            prior_task, ownership_query = _export_owned_windows_task(
                ctx,
                command_runner=command_runner,
            )
            commands.append(ownership_query.public())
            running, status_query = _windows_running_state(
                command_runner=command_runner
            )
            commands.append(status_query.public())
            if running is None:
                raise RuntimeError(
                    "scheduled-task running state could not be determined"
                )
            prior_active = running
        activation_needed = (
            not installed or not prior_active or prior_reachable is False
        )
        changed = registration_changed or runtime_changed or activation_needed
        if registration_changed:
            if installed:
                assert prior_task is not None
                exact = _assert_windows_task_unchanged(
                    ctx, prior_task, command_runner=command_runner
                )
            else:
                exact = _assert_windows_task_absent(command_runner=command_runner)
            commands.append(exact.public())
            create_result = _register_windows_xml(
                ctx,
                _windows_task_content(ctx),
                force=installed,
                command_runner=command_runner,
            )
            if installed:
                # A failed forced update may have partially changed an owned task.
                state_mutated = True
            commands.append(create_result.public())
            if not create_result.ok:
                raise RuntimeError("scheduled-task creation failed")
            state_mutated = True
            created_registration = not installed
        if runtime_changed:
            state_mutated = True
        manifest_changed = _write_manifest(ctx)
        current_task, current_query = _capture_owned_windows_task(
            ctx, command_runner=command_runner
        )
        commands.append(current_query.public())
        if not _windows_definition_matches(ctx, current_task):
            raise RuntimeError("scheduled-task registration verification failed")
        if installed and prior_active and (registration_changed or runtime_changed):
            exact = _assert_windows_task_unchanged(
                ctx, current_task, command_runner=command_runner
            )
            commands.append(exact.public())
            end_result = _run(
                ["schtasks.exe", "/End", "/TN", WINDOWS_TASK_NAME],
                command_runner=command_runner,
            )
            state_mutated = True
            commands.append(end_result.public())
            if not end_result.ok:
                raise RuntimeError("scheduled-task stop before restart failed")
        if changed:
            exact = _assert_windows_task_unchanged(
                ctx, current_task, command_runner=command_runner
            )
            commands.append(exact.public())
            state_mutated = True
            run_result = _run(
                ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK_NAME],
                command_runner=command_runner,
            )
            commands.append(run_result.public())
            if not run_result.ok:
                raise RuntimeError("scheduled-task start failed")
        reachable = _readiness(readiness_probe) if changed else prior_reachable
        if reachable is False:
            raise RuntimeError("dashboard service did not become ready")
    except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
        rollback = (
            _restore_windows_state(
                ctx,
                prior_task=prior_task,
                prior_manifest=prior_manifest,
                prior_active=prior_active,
                created_registration=created_registration,
                command_runner=command_runner,
            )
            if state_mutated
            else None
        )
        return _failed(
            "install",
            ctx,
            error=str(exc),
            commands=commands,
            rollback=rollback,
        )
    return {
        **_base("install", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": changed or manifest_changed,
        "registration_changed": registration_changed,
        "runtime_changed": runtime_changed,
        "installed": True,
        "enabled": True,
        "active": True if changed else prior_active,
        "reachable": reachable,
        "commands": commands,
    }


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
    blocked, state = _preflight(
        action,
        ctx,
        home_dir=home_dir,
        command_runner=command_runner,
        reachability_probe=reachability_probe,
    )
    return ctx, blocked, state


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
    assert ctx is not None and state is not None
    if not state.get("installed"):
        return {
            **_base("start", ctx),
            "ok": False,
            "exit_code": 1,
            "changed": False,
            "error": "dashboard service is not installed",
        }
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
    if ctx.platform == "windows":
        task_xml, capture = _export_owned_windows_task(
            ctx, command_runner=command_runner
        )
        commands.append(capture.public())
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
        exact = _assert_windows_task_unchanged(
            ctx, task_xml, command_runner=command_runner
        )
        commands.append(exact.public())
        command = ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK_NAME]
    else:
        command = [
            "systemctl",
            "--user",
            "restart" if state.get("active") is True else "start",
            SYSTEMD_UNIT_NAME,
        ]
    result = _run(command, command_runner=command_runner)
    commands.append(result.public())
    reachable = _readiness(readiness_probe) if result.ok else None
    ok = result.ok and reachable is not False
    value: dict[str, Any] = {
        **_base("start", ctx),
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "changed": result.ok,
        "reachable": reachable,
        "commands": commands,
    }
    if result.ok and reachable is False:
        value["error"] = "dashboard service did not become ready"
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
    assert ctx is not None and state is not None
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
    if ctx.platform == "windows":
        task_xml, capture = _export_owned_windows_task(
            ctx, command_runner=command_runner
        )
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
        assert task_xml is not None
        exact = _assert_windows_task_unchanged(
            ctx, task_xml, command_runner=command_runner
        )
        commands.append(exact.public())
        command = ["schtasks.exe", "/End", "/TN", WINDOWS_TASK_NAME]
    else:
        command = ["systemctl", "--user", "stop", SYSTEMD_UNIT_NAME]
    result = _run(command, command_runner=command_runner)
    commands.append(result.public())
    descriptor_removed = result.ok and _cleanup_stale_runtime(ctx, reachability_probe)
    return {
        **_base("stop", ctx),
        "ok": result.ok,
        "exit_code": 0 if result.ok else 1,
        "changed": result.ok or descriptor_removed,
        "status": "stopped" if result.ok else "stop_failed",
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
    assert ctx is not None and state is not None
    if not state.get("installed"):
        return {
            **_base("restart", ctx),
            "ok": False,
            "exit_code": 1,
            "changed": False,
            "error": "dashboard service is not installed",
        }
    if ctx.platform == "linux":
        raw_results = [
            _run(
                ["systemctl", "--user", "restart", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
        ]
        command_ok = raw_results[0].ok
    else:
        task_xml, capture = _export_owned_windows_task(
            ctx, command_runner=command_runner
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
            exact = _assert_windows_task_unchanged(
                ctx, task_xml, command_runner=command_runner
            )
            raw_results.append(exact)
            end_result = _run(
                ["schtasks.exe", "/End", "/TN", WINDOWS_TASK_NAME],
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
        exact = _assert_windows_task_unchanged(
            ctx, task_xml, command_runner=command_runner
        )
        raw_results.append(exact)
        run_result = _run(
            ["schtasks.exe", "/Run", "/TN", WINDOWS_TASK_NAME],
            command_runner=command_runner,
        )
        raw_results.append(run_result)
        command_ok = run_result.ok
    reachable = _readiness(readiness_probe) if command_ok else None
    ok = command_ok and reachable is not False
    value: dict[str, Any] = {
        **_base("restart", ctx),
        "ok": ok,
        "exit_code": 0 if ok else 1,
        "changed": command_ok,
        "reachable": reachable,
        "commands": [item.public() for item in raw_results],
    }
    if command_ok and reachable is False:
        value["error"] = "dashboard service did not become ready"
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
    assert ctx is not None and state is not None
    if not state.get("installed"):
        manifest_removed = False
        if _manifest_owned(ctx):
            manifest_removed = ctx.manifest_path.exists()
            ctx.manifest_path.unlink(missing_ok=True)
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
    if ctx.platform == "linux":
        assert ctx.unit_path is not None
        prior_unit = ctx.unit_path.read_bytes()
        prior_manifest = (
            ctx.manifest_path.read_bytes() if ctx.manifest_path.exists() else None
        )
        prior_enabled = state.get("enabled") is True
        prior_active = state.get("active") is True
        commands = []
        state_mutated = False
        try:
            if not prior_unit.decode("utf-8").startswith(f"# {OWNER_MARKER}\n"):
                raise RuntimeError("systemd ownership marker changed before mutation")
            if not _manifest_owned(ctx):
                raise RuntimeError(
                    "dashboard service ownership manifest changed before mutation"
                )
            disable = _run(
                ["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT_NAME],
                command_runner=command_runner,
            )
            state_mutated = True
            commands.append(disable)
            if not disable.ok:
                raise RuntimeError("systemd disable --now failed")
            ctx.unit_path.unlink()
            ctx.manifest_path.unlink()
            reload_result = _run(
                ["systemctl", "--user", "daemon-reload"],
                command_runner=command_runner,
            )
            commands.append(reload_result)
            if not reload_result.ok:
                raise RuntimeError("systemd daemon-reload failed")
        except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
            rollback = (
                _restore_systemd_state(
                    ctx,
                    prior_unit=prior_unit,
                    prior_manifest=prior_manifest,
                    prior_enabled=prior_enabled,
                    prior_active=prior_active,
                    command_runner=command_runner,
                )
                if state_mutated
                else None
            )
            return _failed(
                "uninstall",
                ctx,
                error=str(exc),
                commands=[item.public() for item in commands],
                rollback=rollback,
            )
    else:
        prior_manifest = (
            ctx.manifest_path.read_bytes() if ctx.manifest_path.exists() else None
        )
        commands = []
        prior_task: str | None = None
        prior_active = False
        state_mutated = False
        try:
            prior_task, ownership_query = _export_owned_windows_task(
                ctx,
                command_runner=command_runner,
            )
            commands.append(ownership_query)
            running, status_query = _windows_running_state(
                command_runner=command_runner
            )
            commands.append(status_query)
            if running is None:
                raise RuntimeError(
                    "scheduled-task running state could not be determined"
                )
            prior_active = running
            if running:
                exact = _assert_windows_task_unchanged(
                    ctx, prior_task, command_runner=command_runner
                )
                commands.append(exact)
                end_result = _run(
                    ["schtasks.exe", "/End", "/TN", WINDOWS_TASK_NAME],
                    command_runner=command_runner,
                )
                state_mutated = True
                commands.append(end_result)
                if not end_result.ok:
                    raise RuntimeError("scheduled-task stop failed")
            exact = _assert_windows_task_unchanged(
                ctx, prior_task, command_runner=command_runner
            )
            commands.append(exact)
            delete_result = _run(
                ["schtasks.exe", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"],
                command_runner=command_runner,
            )
            state_mutated = True
            commands.append(delete_result)
            if not delete_result.ok:
                raise RuntimeError("scheduled-task deletion failed")
            ctx.manifest_path.unlink()
        except (ConfigurationError, OSError, RuntimeError, UnicodeError) as exc:
            rollback = (
                _restore_windows_state(
                    ctx,
                    prior_task=prior_task,
                    prior_manifest=prior_manifest,
                    prior_active=prior_active,
                    command_runner=command_runner,
                )
                if state_mutated
                else None
            )
            return _failed(
                "uninstall",
                ctx,
                error=str(exc),
                commands=[item.public() for item in commands],
                rollback=rollback,
            )
    descriptor_removed = _cleanup_stale_runtime(ctx, reachability_probe)
    return {
        **_base("uninstall", ctx),
        "ok": True,
        "exit_code": 0,
        "changed": True,
        "installed": False,
        "runtime_descriptor_removed": descriptor_removed,
        "commands": [item.public() for item in commands],
    }


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "OWNER_ID",
    "OWNER_MARKER",
    "SYSTEMD_UNIT_NAME",
    "WINDOWS_TASK_NAME",
    "build_service_worker_argv",
    "inspect_dashboard_service",
    "install_dashboard_service",
    "plan_dashboard_service",
    "restart_dashboard_service",
    "start_dashboard_service",
    "stop_dashboard_service",
    "uninstall_dashboard_service",
]
