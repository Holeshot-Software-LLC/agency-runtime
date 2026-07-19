"""Shared, platform-neutral dashboard service primitives.

This module owns validation, context construction, and bounded command
execution. Manifest/file transactions and platform lifecycle logic live in
cohesive sibling modules.
"""

from __future__ import annotations

import getpass
import hmac
import inspect
import math
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from agency_runtime.core.configuration_persistence import resolve_config_path
from agency_runtime.core.process_argv import (
    PersistentArtifactIdentity,
    absolute_executable_path,
    freeze_process_argv,
    isolated_python_argv,
    prepare_process_argv,
    revalidate_persistent_artifacts,
    revalidate_process_argv,
    snapshot_persistent_artifacts,
)
from agency_runtime.core.windows_acl import current_process_user_sid

OWNER_ID = "agency-runtime"
OWNER_MARKER = "Managed by Agency Runtime; owner=agency-runtime"
SERVICE_ID = "dashboard"
SYSTEMD_UNIT_NAME = "agency-runtime-dashboard.service"
WINDOWS_TASK_NAME = "Agency Runtime Dashboard"
MANIFEST_SCHEMA_VERSION = 2
WINDOWS_TASK_XML_NAMESPACE = "http://schemas.microsoft.com/windows/2004/02/mit/task"

_MAX_COMMAND_TIMEOUT_SECONDS = 300.0
_MAX_MANAGER_OUTPUT_BYTES = 1024 * 1024
_DASHBOARD_RUNTIME_CLEAR_TIMEOUT_SECONDS = 8.0
_DASHBOARD_RUNTIME_CLEAR_POLL_SECONDS = 0.1
_IS_WINDOWS = os.name == "nt"

CommandRunner = Callable[..., Any]
ReadinessProbe = Callable[[], bool]

_NON_DURABLE_SERVICE_ENVIRONMENT_NAMES = frozenset(
    {
        "AGENCY_BYPASS_THRESHOLD",
        "AGENCY_CAPTURE_CONTENT",
        "AGENCY_DASHBOARD_PORT",
        "AGENCY_DB_PATH",
        "AGENCY_JUDGE_API_KEY",
        "AGENCY_JUDGE_BASE_URL",
        "AGENCY_JUDGE_MODEL",
        "AGENCY_JUDGE_TIMEOUT",
        "AGENCY_MAX_SELECTED",
        "AGENCY_OLLAMA_FALLBACK_MODEL",
        "AGENCY_POLICY_PATH",
        "AGENCY_PROFILE",
        "AGENCY_RETENTION_DAYS",
        "LITELLM_API_KEY",
        "OLLAMA_BASE_URL",
    }
)


@dataclass(frozen=True, slots=True)
class _CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def public(self, *, include_failure_output: bool = True) -> dict[str, Any]:
        value: dict[str, Any] = {
            "command": list(self.command),
            "returncode": self.returncode,
            "ok": self.ok,
        }
        if not self.ok:
            detail = ""
            if include_failure_output:
                detail = (self.stderr or self.stdout).strip()
            detail = detail or "service-manager command failed"
            value["error"] = _terminal_safe(detail)[:500]
        return value


@dataclass(frozen=True, slots=True)
class _RollbackOutcome:
    commands: list[dict[str, Any]]
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class _DashboardRuntimeClearance:
    cleared: bool
    descriptor_removed: bool
    replacement_detected: bool = False


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
    windows_account: str | None = None
    unit_root: Path | None = None
    launcher_artifacts: tuple[PersistentArtifactIdentity, ...] = ()


def _configured_secret_environment_names(config: object | None) -> set[str]:
    """Return configured credential variable names without reading their values."""

    names: set[str] = set()

    def include(entry: object | None) -> None:
        name = str(getattr(entry, "api_key_env", "") or "").strip()
        if name and name.isascii() and name.isidentifier() and len(name) <= 128:
            names.add(name)

    if config is None:
        return names
    include(getattr(config, "judge", None))
    for provider in getattr(config, "providers", ()) or ():
        include(provider)
    adapters = getattr(config, "adapters", None)
    for adapter_name in ("litellm", "hermes", "openclaw", "codex", "claude"):
        include(getattr(adapters, adapter_name, None))
    return names


def dashboard_service_environment_overrides(
    config: object | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """List active process-only settings that cannot survive service restart.

    ``AGENCY_CONFIG_PATH`` is intentionally absent: its resolved identity is
    embedded in the service argv.  Values are never returned or copied into a
    unit, task, manifest, diagnostic, or command line.
    """

    environment = os.environ if environ is None else environ
    candidates = _dashboard_service_environment_names(config)
    return tuple(sorted(name for name in candidates if environment.get(name)))


def _dashboard_service_environment_names(config: object | None = None) -> set[str]:
    names = set(_NON_DURABLE_SERVICE_ENVIRONMENT_NAMES)
    names.update(_configured_secret_environment_names(config))
    return names


def dashboard_service_manager_environment_overrides(
    config: object | None,
    manager_output: str,
) -> tuple[str, ...]:
    """Return names-only nondurable values exported by the systemd user manager."""

    candidates = _dashboard_service_environment_names(config)
    present: set[str] = set()
    for line in manager_output.splitlines():
        name, separator, _value = line.partition("=")
        if (
            separator
            and name in candidates
            and name.isascii()
            and name.isidentifier()
            and len(name) <= 128
        ):
            present.add(name)
    return tuple(sorted(present))


def dashboard_service_environment_error(names: Sequence[str]) -> str:
    """Render an actionable names-only durability diagnostic."""

    listed = ", ".join(sorted(set(names)))
    return (
        "dashboard service installation is blocked because process-local runtime "
        f"overrides are not reboot-durable: {listed}. Unset them and persist "
        "non-secret settings in agency.yaml before retrying; secret values are never "
        "copied into the service definition"
    )


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
    validated = Path(_validate_text(str(value), label=label)).expanduser()
    return Path(os.path.abspath(validated))


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
    *,
    platform_name: str | None = None,
) -> Path:
    return resolve_config_path(
        config_path,
        home_dir=home,
        use_environment=home_dir is None,
        platform_name=platform_name,
    )


def _windows_current_user_sid() -> str | None:
    """Return the current process token SID without invoking a shell."""

    return current_process_user_sid(is_windows=_IS_WINDOWS)


def _windows_account_for_sid(sid: str) -> str | None:
    """Resolve *sid* through Windows account lookup without trusting the environment."""

    if not _IS_WINDOWS:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        sid_text = _validate_text(sid, label="Windows SID")
        advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        convert_sid = advapi32.ConvertStringSidToSidW
        convert_sid.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
        convert_sid.restype = wintypes.BOOL
        lookup_account = advapi32.LookupAccountSidW
        lookup_account.argtypes = [
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        lookup_account.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]

        sid_pointer = ctypes.c_void_p()
        if not convert_sid(sid_text, ctypes.byref(sid_pointer)):
            return None
        try:
            account_size = wintypes.DWORD()
            domain_size = wintypes.DWORD()
            sid_type = wintypes.DWORD()
            lookup_account(
                None,
                sid_pointer,
                None,
                ctypes.byref(account_size),
                None,
                ctypes.byref(domain_size),
                ctypes.byref(sid_type),
            )
            if account_size.value == 0:
                return None
            account = ctypes.create_unicode_buffer(account_size.value)
            domain_capacity = max(domain_size.value, 1)
            domain = ctypes.create_unicode_buffer(domain_capacity)
            domain_size = wintypes.DWORD(domain_capacity)
            if not lookup_account(
                None,
                sid_pointer,
                account,
                ctypes.byref(account_size),
                domain,
                ctypes.byref(domain_size),
                ctypes.byref(sid_type),
            ):
                return None
            account_name = f"{domain.value}\\{account.value}" if domain.value else account.value
            return _validate_text(account_name, label="Windows account")
        finally:
            kernel32.LocalFree(sid_pointer)
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
    argv = isolated_python_argv(
        executable,
        "agency_runtime.cli",
        "dashboard",
        "--service-mode",
        "--config",
        str(config),
    )
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
    config = _config_path(home, home_dir, config_path, platform_name=target)
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
    windows_account: str | None = None
    if target == "windows":
        manager = "schtasks"
        registration = WINDOWS_TASK_NAME
        unit_path = None
        unit_root = None
        if _IS_WINDOWS:
            windows_user = _windows_current_user_sid()
            windows_account = (
                _windows_account_for_sid(windows_user) if windows_user is not None else None
            )
            if windows_user is None or windows_account is None:
                raise RuntimeError("current Windows token identity could not be resolved safely")
        else:
            # Cross-platform planning/tests cannot access a Windows token. Keep the
            # portable fallback out of native execution paths.
            username = os.environ.get("USERNAME") or getpass.getuser()
            domain = os.environ.get("USERDOMAIN")
            account_name = f"{domain}\\{username}" if domain and domain != "." else username
            windows_account = _validate_text(account_name, label="Windows account")
            windows_user = _windows_current_user_sid() or windows_account
        windows_user = _validate_text(windows_user, label="Windows user")
        windows_account = _validate_text(windows_account, label="Windows account")
    else:
        manager = "systemd-user"
        registration = SYSTEMD_UNIT_NAME
        xdg_config = os.environ.get("XDG_CONFIG_HOME") if home_dir is None else None
        xdg_root = Path(xdg_config).expanduser() if xdg_config else None
        config_root = (
            Path(os.path.abspath(xdg_root))
            if xdg_root is not None and xdg_root.is_absolute()
            else home / ".config"
        )
        unit_path = config_root / "systemd" / "user" / SYSTEMD_UNIT_NAME
        unit_root = config_root
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
        windows_account=windows_account,
        unit_root=unit_root,
    )


def _native_launcher_platform(ctx: _Context) -> str | None:
    if ctx.platform == "windows" and os.name == "nt":
        return "nt"
    if ctx.platform == "linux" and os.name != "nt" and platform.system().lower() == "linux":
        return "posix"
    return None


def _validate_dashboard_launcher(ctx: _Context) -> _Context:
    """Freeze both persistent launcher artifacts on the native target host."""

    native_platform = _native_launcher_platform(ctx)
    if native_platform is None:
        # Foreign-platform planning and deterministic contract tests do not
        # execute the generated registration. A native install always takes
        # the validated branch above.
        return replace(ctx, launcher_artifacts=())
    if len(ctx.worker_argv) < 3:
        raise OSError("dashboard worker argv does not identify its isolated bootstrap")
    identities = snapshot_persistent_artifacts(
        (ctx.worker_argv[0], ctx.worker_argv[2]),
        platform_name=native_platform,
    )
    return replace(ctx, launcher_artifacts=identities)


def _revalidate_dashboard_launcher(ctx: _Context) -> None:
    """Recompute persistent artifact trust immediately before mutation."""

    native_platform = _native_launcher_platform(ctx)
    if native_platform is None:
        return
    revalidate_persistent_artifacts(
        ctx.launcher_artifacts,
        platform_name=native_platform,
    )


def _dashboard_runtime_fingerprint(ctx: _Context) -> str | None:
    """Capture the current worker generation without exposing its token."""

    from agency_runtime.core.dashboard_runtime import dashboard_runtime_instance_fingerprint

    return dashboard_runtime_instance_fingerprint(home_dir=ctx.home)


def _cleanup_stale_dashboard_runtime(
    ctx: _Context,
    *,
    expected_fingerprint: str | None = None,
) -> bool:
    """Remove only an unreachable descriptor still owned by its exact worker."""

    from agency_runtime.core.dashboard_runtime import (
        dashboard_service_reachable,
        read_dashboard_runtime,
        remove_dashboard_runtime,
    )

    try:
        descriptor = read_dashboard_runtime(home_dir=ctx.home)
    except ValueError:
        return False
    if expected_fingerprint is not None:
        current_fingerprint = _dashboard_runtime_fingerprint(ctx)
        if current_fingerprint is None or not hmac.compare_digest(
            current_fingerprint,
            expected_fingerprint,
        ):
            return False
    if dashboard_service_reachable(descriptor=descriptor):
        return False
    return remove_dashboard_runtime(
        home_dir=ctx.home,
        token=descriptor["token"],
        pid=descriptor["pid"],
    )


def _dashboard_runtime_cleared(
    ctx: _Context,
) -> bool:
    """Prove that no dashboard runtime descriptor remains."""

    from agency_runtime.core.dashboard_runtime import dashboard_runtime_path

    if _dashboard_runtime_fingerprint(ctx) is not None:
        return False
    return not os.path.lexists(dashboard_runtime_path(home_dir=ctx.home))


def _wait_dashboard_runtime_cleared(
    ctx: _Context,
    previous_fingerprint: str | None,
    *,
    timeout_seconds: float = _DASHBOARD_RUNTIME_CLEAR_TIMEOUT_SECONDS,
    poll_seconds: float = _DASHBOARD_RUNTIME_CLEAR_POLL_SECONDS,
) -> _DashboardRuntimeClearance:
    """Wait for one stopped worker generation to release its descriptor.

    Windows Task Scheduler can report an idle task before the worker has
    completed shutdown.  Each retry authenticates the descriptor's health and
    removes it only through the token-and-PID compare-and-remove operation.
    A responsive old generation therefore remains a hard failure when the
    bounded wait expires.
    """

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    descriptor_removed = False
    while True:
        current_fingerprint = _dashboard_runtime_fingerprint(ctx)
        replacement_present = bool(
            current_fingerprint is not None
            and (
                previous_fingerprint is None
                or not hmac.compare_digest(current_fingerprint, previous_fingerprint)
            )
        )
        if replacement_present:
            return _DashboardRuntimeClearance(
                cleared=False,
                descriptor_removed=descriptor_removed,
                replacement_detected=True,
            )
        if current_fingerprint is not None:
            descriptor_removed = (
                _cleanup_stale_dashboard_runtime(
                    ctx,
                    expected_fingerprint=previous_fingerprint,
                )
                or descriptor_removed
            )
        if _dashboard_runtime_cleared(ctx):
            return _DashboardRuntimeClearance(
                cleared=True,
                descriptor_removed=descriptor_removed,
            )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _DashboardRuntimeClearance(
                cleared=False,
                descriptor_removed=descriptor_removed,
            )
        time.sleep(min(max(0.0, poll_seconds), remaining))


def _fresh_dashboard_readiness(
    ctx: _Context,
    probe: ReadinessProbe | None,
    previous_fingerprint: str | None,
) -> bool | None:
    """Require a reachable replacement generation after a worker transition."""

    if probe is None:
        return False if previous_fingerprint is not None else None
    try:
        reachable = bool(probe())
    except Exception:
        return False
    if not reachable or previous_fingerprint is None:
        return reachable
    current = _dashboard_runtime_fingerprint(ctx)
    return bool(current is not None and not hmac.compare_digest(current, previous_fingerprint))


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
            prepared_argv = freeze_process_argv(prepare_process_argv(argv))
            with (
                tempfile.TemporaryFile() as stdout_stream,
                tempfile.TemporaryFile() as stderr_stream,
            ):
                try:
                    # Namespace permissions and artifact identity may change
                    # after discovery. Keep this as the final trust operation
                    # immediately before subprocess creates the manager child.
                    revalidate_process_argv(prepared_argv)
                    raw = subprocess.run(
                        prepared_argv,
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
    "_DashboardRuntimeClearance",
    "_RollbackOutcome",
    "_base",
    "_cleanup_stale_dashboard_runtime",
    "_context",
    "_dashboard_runtime_cleared",
    "_dashboard_runtime_fingerprint",
    "_fresh_dashboard_readiness",
    "_revalidate_dashboard_launcher",
    "_run",
    "_unsupported",
    "_validate_dashboard_launcher",
    "_validate_text",
    "_wait_dashboard_runtime_cleared",
    "build_service_worker_argv",
    "dashboard_service_environment_error",
    "dashboard_service_environment_overrides",
    "dashboard_service_manager_environment_overrides",
]
