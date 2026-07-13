"""Shared, platform-neutral dashboard service primitives.

This module owns validation, context construction, and bounded command
execution. Manifest/file transactions and platform lifecycle logic live in
cohesive sibling modules.
"""

from __future__ import annotations

import getpass
import inspect
import math
import os
import platform
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from agency_runtime.core.process_argv import absolute_executable_path

OWNER_ID = "agency-runtime"
OWNER_MARKER = "Managed by Agency Runtime; owner=agency-runtime"
SERVICE_ID = "dashboard"
SYSTEMD_UNIT_NAME = "agency-runtime-dashboard.service"
WINDOWS_TASK_NAME = "Agency Runtime Dashboard"
MANIFEST_SCHEMA_VERSION = 1
WINDOWS_TASK_XML_NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"

_MAX_COMMAND_TIMEOUT_SECONDS = 300.0
_MAX_MANAGER_OUTPUT_BYTES = 1024 * 1024

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
            detail = (self.stderr or self.stdout or "service-manager command failed").strip()
            value["error"] = _terminal_safe(detail)[:500]
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


def _terminal_safe(value: str) -> str:
    return "".join(
        character
        if character in "\n\t" or (ord(character) >= 32 and ord(character) != 127)
        else "?"
        for character in value
    )


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


def _executable_path(value: str | Path) -> Path:
    """Return an absolute executable path without dereferencing virtualenv shims."""

    validated = _validate_text(str(value), label="Python executable")
    return Path(absolute_executable_path(validated))


def _home(home_dir: str | Path | None) -> Path:
    return _resolved_path(home_dir if home_dir is not None else Path.home(), label="home directory")


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
            get_token(token, 1, None, 0, ctypes.byref(required))
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
    """Build the exact credential-free dashboard worker command."""

    home = _home(home_dir)
    executable = _executable_path(
        python_executable if python_executable is not None else sys.executable
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
    executable = _executable_path(
        python_executable if python_executable is not None else sys.executable
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


def _bounded_text(value: Any) -> tuple[str, bool]:
    if isinstance(value, bytes):
        raw = value
    else:
        raw = str(value or "").encode("utf-8", errors="replace")
    too_large = len(raw) > _MAX_MANAGER_OUTPUT_BYTES
    return raw[:_MAX_MANAGER_OUTPUT_BYTES].decode("utf-8", errors="replace"), too_large


def _read_command_stream(stream: Any) -> tuple[str, bool]:
    stream.seek(0)
    raw = stream.read(_MAX_MANAGER_OUTPUT_BYTES + 1)
    too_large = len(raw) > _MAX_MANAGER_OUTPUT_BYTES
    return raw[:_MAX_MANAGER_OUTPUT_BYTES].decode("utf-8", errors="replace"), too_large


def _invoke_runner(runner: CommandRunner, argv: tuple[str, ...], *, timeout: float) -> Any:
    """Invoke an injected runner once, including legacy one-argument runners."""

    arguments = list(argv)
    try:
        signature = inspect.signature(runner)
    except (TypeError, ValueError):
        return runner(arguments, timeout=timeout)
    try:
        signature.bind(arguments, timeout=timeout)
    except TypeError:
        return runner(arguments)
    return runner(arguments, timeout=timeout)


def _coerce_returncode(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError("service-manager return code must be an integer")
    result = int(value)
    if result < -(2**31) or result > 2**31 - 1:
        raise ValueError("service-manager return code is out of range")
    return result


def _run(
    command: Sequence[str],
    *,
    command_runner: CommandRunner | None,
    timeout: float = 30.0,
) -> _CommandResult:
    """Execute one fixed-argv manager command with bounded time and output."""

    argv = tuple(_validate_text(str(item), label="service-manager argument") for item in command)
    if not argv:
        raise ValueError("service-manager command must not be empty")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, Real)
        or not math.isfinite(float(timeout))
        or not 0 < float(timeout) <= _MAX_COMMAND_TIMEOUT_SECONDS
    ):
        raise ValueError("service-manager timeout must be finite and between 0 and 300 seconds")
    bounded_timeout = float(timeout)
    try:
        if command_runner is None:
            with (
                tempfile.TemporaryFile() as stdout_stream,
                tempfile.TemporaryFile() as stderr_stream,
            ):
                try:
                    raw = subprocess.run(
                        list(argv),
                        stdin=subprocess.DEVNULL,
                        stdout=stdout_stream,
                        stderr=stderr_stream,
                        timeout=bounded_timeout,
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    stdout, _ = _read_command_stream(stdout_stream)
                    return _CommandResult(argv, 124, stdout, "service-manager command timed out")
                stdout, stdout_limited = _read_command_stream(stdout_stream)
                stderr, stderr_limited = _read_command_stream(stderr_stream)
                returncode = _coerce_returncode(raw.returncode)
        else:
            raw = _invoke_runner(command_runner, argv, timeout=bounded_timeout)
            if inspect.isawaitable(raw):
                if inspect.iscoroutine(raw):
                    raw.close()
                raise TypeError("service-manager runner must be synchronous")
            if isinstance(raw, _CommandResult):
                returncode = _coerce_returncode(raw.returncode)
                stdout, stdout_limited = _bounded_text(raw.stdout)
                stderr, stderr_limited = _bounded_text(raw.stderr)
            elif isinstance(raw, Mapping):
                returncode = _coerce_returncode(raw.get("returncode", raw.get("exit_code", 0)))
                stdout, stdout_limited = _bounded_text(raw.get("stdout", ""))
                stderr, stderr_limited = _bounded_text(raw.get("stderr", raw.get("error", "")))
            else:
                returncode = _coerce_returncode(getattr(raw, "returncode", 0))
                stdout, stdout_limited = _bounded_text(getattr(raw, "stdout", ""))
                stderr, stderr_limited = _bounded_text(getattr(raw, "stderr", ""))
    except subprocess.TimeoutExpired as exc:
        stdout, _ = _bounded_text(exc.stdout)
        return _CommandResult(argv, 124, stdout, "service-manager command timed out")
    except OSError as exc:
        return _CommandResult(argv, 127, "", f"{type(exc).__name__}: {exc}")
    except (TypeError, ValueError) as exc:
        return _CommandResult(
            argv, 125, "", f"invalid service-manager result: {type(exc).__name__}"
        )
    except Exception as exc:  # runner boundary; never expose arbitrary details
        return _CommandResult(argv, 127, "", f"service-manager runner failed: {type(exc).__name__}")
    if stdout_limited or stderr_limited:
        return _CommandResult(
            argv,
            returncode if returncode else 125,
            stdout,
            "service-manager output exceeded the 1 MiB limit",
        )
    return _CommandResult(argv, returncode, stdout, stderr)


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


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "OWNER_ID",
    "OWNER_MARKER",
    "SYSTEMD_UNIT_NAME",
    "WINDOWS_TASK_NAME",
    "WINDOWS_TASK_XML_NAMESPACE",
    "CommandRunner",
    "ReadinessProbe",
    "_CommandResult",
    "_Context",
    "_RollbackOutcome",
    "_base",
    "_context",
    "_run",
    "_unsupported",
    "_validate_text",
    "build_service_worker_argv",
]
