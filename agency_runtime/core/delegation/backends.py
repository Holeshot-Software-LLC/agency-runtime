"""Production-safe subprocess delegation backends.

Each backend uses a documented, non-interactive host CLI surface.  Commands are
always executed as argv (never through a shell), successful structured output is
validated, and process failures remain failures instead of becoming synthetic
delegation evidence.
"""

from __future__ import annotations

import json
import math
import os
import signal
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Protocol, Sequence, runtime_checkable

from agency_runtime.core.process_argv import prepare_process_argv


_ERROR_PREVIEW_CHARS = 2_000
_DRAIN_GRACE_SECONDS = 0.5
_MAX_TASK_CHARS = 16 * 1024
_MAX_SPECIALIST_CHARS = 256
_TASK_REDACTION = "<task>"
_SAFE_DELEGATION_ENVIRONMENT_NAMES = frozenset({
    "ALL_PROXY",
    "COMSPEC",
    "CURL_CA_BUNDLE",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOGNAME",
    "NODE_EXTRA_CA_CERTS",
    "NO_PROXY",
    "PATH",
    "PATHEXT",
    "PROGRAMDATA",
    "REQUESTS_CA_BUNDLE",
    "SHELL",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USER",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
})
_AUTH_HOME_BY_BACKEND = {
    "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
    "codex": ("CODEX_HOME", ".codex"),
    "hermes": ("HERMES_HOME", ".hermes"),
    "openclaw": ("OPENCLAW_HOME", ".openclaw"),
}


def _delegation_environment(
    backend_name: str,
    extra_env: Mapping[str, str],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the least-privilege environment required by one host CLI."""
    source = os.environ if environ is None else environ
    safe = {
        key: value
        for key, value in source.items()
        if key.upper() in _SAFE_DELEGATION_ENVIRONMENT_NAMES
        and isinstance(value, str)
    }
    auth_home = _AUTH_HOME_BY_BACKEND.get(backend_name.strip().lower())
    if auth_home is not None:
        variable, default_name = auth_home
        user_home = (
            source.get("USERPROFILE")
            or source.get("HOME")
            or str(Path.home())
        )
        safe[variable] = source.get(variable, str(Path(user_home) / default_name))
    safe["NO_COLOR"] = "1"
    safe.update(extra_env)
    return safe


def _sensitive_variants(values: Iterable[str]) -> tuple[str, ...]:
    variants: set[str] = set()
    for value in values:
        if not value:
            continue
        variants.add(value)
        variants.add(json.dumps(value, ensure_ascii=True)[1:-1])
        variants.add(json.dumps(value, ensure_ascii=False)[1:-1])
    variants.discard("")
    return tuple(sorted(variants, key=len, reverse=True))


def _redact_text(value: str, sensitive: Iterable[str]) -> str:
    redacted = value
    for variant in _sensitive_variants(sensitive):
        redacted = redacted.replace(variant, _TASK_REDACTION)
    return redacted


def _redact_value(value: Any, sensitive: Iterable[str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, sensitive)
    if isinstance(value, list):
        return [_redact_value(item, sensitive) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item, sensitive) for item in value)
    if isinstance(value, dict):
        return {
            _redact_value(key, sensitive): _redact_value(item, sensitive)
            for key, item in value.items()
        }
    return value


class _WindowsJob:
    """Small kill-on-close Job Object wrapper; constructed only on Windows."""

    def __init__(self, handle: Any, kernel32: Any, accounting_type: Any) -> None:
        self._handle = handle
        self._kernel32 = kernel32
        self._accounting_type = accounting_type

    def active_processes(self) -> int | None:
        import ctypes

        accounting = self._accounting_type()
        returned = ctypes.c_ulong()
        if not self._kernel32.QueryInformationJobObject(
            self._handle,
            1,
            ctypes.byref(accounting),
            ctypes.sizeof(accounting),
            ctypes.byref(returned),
        ):
            return None
        return int(accounting.ActiveProcesses)

    def terminate(self) -> bool:
        if self._handle:
            return bool(self._kernel32.TerminateJobObject(self._handle, 1))
        return False

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = None


def _create_windows_job(process: subprocess.Popen[str]) -> _WindowsJob | None:
    """Assign a child to a kill-on-close Job Object when native APIs permit."""
    if os.name != "nt":
        return None
    handle: Any = None
    kernel32: Any = None
    try:
        import ctypes
        from ctypes import wintypes

        class IoCounters(ctypes.Structure):
            _fields_ = [
                ("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong),
            ]

        class BasicLimitInformation(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class ExtendedLimitInformation(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BasicLimitInformation),
                ("IoInfo", IoCounters),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        class BasicAccountingInformation(ctypes.Structure):
            _fields_ = [
                ("TotalUserTime", ctypes.c_longlong),
                ("TotalKernelTime", ctypes.c_longlong),
                ("ThisPeriodTotalUserTime", ctypes.c_longlong),
                ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
                ("TotalPageFaultCount", wintypes.DWORD),
                ("TotalProcesses", wintypes.DWORD),
                ("ActiveProcesses", wintypes.DWORD),
                ("TotalTerminatedProcesses", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            return None
        limits = ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = 0x00002000
        configured = kernel32.SetInformationJobObject(
            handle,
            9,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        )
        assigned = configured and kernel32.AssignProcessToJobObject(
            handle,
            wintypes.HANDLE(int(process._handle)),
        )
        if not assigned:
            return None
        job = _WindowsJob(handle, kernel32, BasicAccountingInformation)
        handle = None
        return job
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    finally:
        if handle and kernel32 is not None:
            kernel32.CloseHandle(handle)


def _posix_process_group_active(process: subprocess.Popen[str]) -> bool:
    if os.name == "nt":
        return False
    try:
        os.killpg(process.pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _resume_windows_process(process_id: int) -> bool:
    """Resume every initial thread in a process launched with CREATE_SUSPENDED."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        from ctypes import wintypes

        class ThreadEntry32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", wintypes.LONG),
                ("tpDeltaPri", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
        ]
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.Thread32First.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ThreadEntry32),
        ]
        kernel32.Thread32First.restype = wintypes.BOOL
        kernel32.Thread32Next.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ThreadEntry32),
        ]
        kernel32.Thread32Next.restype = wintypes.BOOL
        kernel32.OpenThread.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenThread.restype = wintypes.HANDLE
        kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
        kernel32.ResumeThread.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
        invalid_handle = ctypes.c_void_p(-1).value
        if not snapshot or int(snapshot) == invalid_handle:
            return False
        resumed = 0
        failed = False
        try:
            entry = ThreadEntry32()
            entry.dwSize = ctypes.sizeof(entry)
            found = bool(kernel32.Thread32First(snapshot, ctypes.byref(entry)))
            while found:
                if int(entry.th32OwnerProcessID) == process_id:
                    thread = kernel32.OpenThread(
                        0x0002,
                        False,
                        entry.th32ThreadID,
                    )
                    if not thread:
                        failed = True
                    else:
                        try:
                            if int(kernel32.ResumeThread(thread)) == 0xFFFFFFFF:
                                failed = True
                            else:
                                resumed += 1
                        finally:
                            kernel32.CloseHandle(thread)
                found = bool(kernel32.Thread32Next(snapshot, ctypes.byref(entry)))
        finally:
            kernel32.CloseHandle(snapshot)
        return resumed > 0 and not failed
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _owned_process_kwargs(
    *,
    platform_name: str | None = None,
    suspended: bool = False,
) -> dict[str, Any]:
    """Return launch flags for a process tree owned by Agency Runtime."""
    if (platform_name or os.name) == "nt":
        creationflags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        if suspended:
            creationflags |= getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        return {
            "creationflags": creationflags,
        }
    return {"start_new_session": True}


def _terminate_owned_process_tree(
    process: subprocess.Popen[str],
    *,
    platform_name: str | None = None,
    windows_job: _WindowsJob | None = None,
) -> None:
    """Terminate the complete process tree started for one delegation."""
    platform = platform_name or os.name
    if platform == "nt":
        if windows_job is not None:
            terminated = windows_job.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                terminated = False
            if not terminated or process.poll() is None:
                try:
                    process.kill()
                except OSError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            return
        try:
            killer = subprocess.Popen(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_owned_process_kwargs(platform_name="nt"),
            )
            killer.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    process.kill()
                except OSError:
                    pass
        deadline = time.monotonic() + 1
        while _posix_process_group_active(process) and time.monotonic() < deadline:
            time.sleep(0.05)
        if _posix_process_group_active(process):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _start_process_io_threads(
    process: subprocess.Popen[str],
    *,
    stdout: Any,
    stderr: Any,
    input_text: str | None,
    windows_job: _WindowsJob | None,
) -> tuple[threading.Thread, threading.Thread, threading.Thread | None]:
    """Start bounded pipe workers, cleaning the tree after any partial failure."""

    def drain(stream: Any, capture: Any) -> None:
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                capture.write(chunk)
        except (OSError, ValueError):
            pass
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    def write_stdin() -> None:
        try:
            if process.stdin is not None:
                process.stdin.write(input_text or "")
                process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            try:
                if process.stdin is not None:
                    process.stdin.close()
            except (OSError, ValueError):
                pass

    stdout_thread = threading.Thread(
        target=drain,
        args=(process.stdout, stdout),
        name="agency-stdout-drain",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=drain,
        args=(process.stderr, stderr),
        name="agency-stderr-drain",
        daemon=True,
    )
    stdin_thread = (
        threading.Thread(
            target=write_stdin,
            name="agency-stdin-writer",
            daemon=True,
        )
        if input_text is not None
        else None
    )
    started: list[threading.Thread] = []
    try:
        for thread in (stdout_thread, stderr_thread, stdin_thread):
            if thread is not None:
                thread.start()
                started.append(thread)
    except Exception as exc:
        _terminate_owned_process_tree(process, windows_job=windows_job)
        for thread in started:
            thread.join(timeout=5)
        raise OSError("could not start process I/O workers") from exc
    except BaseException:
        _terminate_owned_process_tree(process, windows_job=windows_job)
        for thread in started:
            thread.join(timeout=5)
        raise
    return stdout_thread, stderr_thread, stdin_thread


def _run_owned_process(
    argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdout: Any,
    stderr: Any,
    timeout: float,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run argv in a killable process group, including all descendants."""
    process_argv = prepare_process_argv(argv)
    process = subprocess.Popen(
        process_argv,
        cwd=cwd,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        **_owned_process_kwargs(suspended=os.name == "nt"),
    )
    windows_job: _WindowsJob | None = None
    if os.name == "nt":
        windows_job = _create_windows_job(process)
        if windows_job is None or not _resume_windows_process(process.pid):
            if windows_job is not None:
                _terminate_owned_process_tree(process, windows_job=windows_job)
                windows_job.close()
            else:
                try:
                    process.kill()
                except OSError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    pass
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            raise OSError("could not establish a contained Windows process group")
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    stdin_thread: threading.Thread | None = None
    try:
        stdout_thread, stderr_thread, stdin_thread = _start_process_io_threads(
            process,
            stdout=stdout,
            stderr=stderr,
            input_text=input_text,
            windows_job=windows_job,
        )
        timeout_error: subprocess.TimeoutExpired | None = None
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            _terminate_owned_process_tree(process, windows_job=windows_job)
            timeout_error = exc

        descendants_detected = _posix_process_group_active(process)
        if timeout_error is None and os.name != "nt":
            # Deliberate policy: descendants are cleaned and the delegation
            # fails, because the nominally successful parent violated ownership.
            _terminate_owned_process_tree(process)

        if stdin_thread is not None:
            stdin_thread.join(timeout=_DRAIN_GRACE_SECONDS)
        assert stdout_thread is not None
        assert stderr_thread is not None
        stdout_thread.join(timeout=_DRAIN_GRACE_SECONDS)
        stderr_thread.join(timeout=_DRAIN_GRACE_SECONDS)

        active_processes = (
            windows_job.active_processes() if windows_job is not None else None
        )
        if active_processes:
            settle_deadline = time.monotonic() + _DRAIN_GRACE_SECONDS
            while active_processes and time.monotonic() < settle_deadline:
                time.sleep(0.02)
                active_processes = (
                    windows_job.active_processes()
                    if windows_job is not None
                    else None
                )
        descendants_detected = bool(
            descendants_detected
            or (active_processes is not None and active_processes > 0)
        )
        drains_lingering = stdout_thread.is_alive() or stderr_thread.is_alive()
        if descendants_detected or drains_lingering:
            _terminate_owned_process_tree(process, windows_job=windows_job)
            if stdin_thread is not None:
                stdin_thread.join(timeout=5)
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

        if timeout_error is not None:
            raise subprocess.TimeoutExpired(process_argv, timeout) from timeout_error
        if descendants_detected or drains_lingering:
            raise OSError("owned process descendants outlived the parent process")
        return subprocess.CompletedProcess(
            process_argv,
            int(process.returncode or 0),
            stdout=stdout.read(),
            stderr=stderr.read(),
        )
    except BaseException:
        _terminate_owned_process_tree(process, windows_job=windows_job)
        for thread in (stdin_thread, stdout_thread, stderr_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)
        raise
    finally:
        if windows_job is not None:
            windows_job.close()


def _stream_text(value: Any) -> str:
    """Normalize real and mocked subprocess stream values to UTF-8 text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = "\n...[truncated by output limit]"
    if limit <= len(marker):
        return marker[:limit], True
    keep = max(0, limit - len(marker))
    return text[:keep] + marker, True


class _BoundedTextCapture:
    """Thread-safe file-like sink that discards text after ``limit + 1``."""

    def __init__(self, limit: int) -> None:
        self._limit = limit + 1
        self._chunks: list[str] = []
        self._size = 0
        self._lock = threading.Lock()

    def write(self, value: Any) -> int:
        text = _stream_text(value)
        with self._lock:
            remaining = self._limit - self._size
            if remaining > 0:
                retained = text[:remaining]
                self._chunks.append(retained)
                self._size += len(retained)
        return len(text)

    def read(self, _limit: int = -1) -> str:
        with self._lock:
            value = "".join(self._chunks)
        return value if _limit < 0 else value[:_limit]

    def flush(self) -> None:
        return None

    def seek(self, _offset: int, _whence: int = 0) -> int:
        return 0


def _read_process_stream(handle: Any, fallback: Any, limit: int) -> str:
    """Read at most one character beyond a process stream's configured cap."""
    if fallback is not None:
        return _stream_text(fallback)
    handle.flush()
    handle.seek(0)
    return _stream_text(handle.read(limit + 1))


@dataclass(frozen=True, slots=True)
class BoundedProcessResult:
    """Content-bounded result for a shell-free owned subprocess.

    The result deliberately omits argv, stdin, and environment data so callers
    can safely use it for credential-backed status probes and routing prompts.
    """

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False


def run_bounded_process(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    max_output_chars: int = 64 * 1024,
) -> BoundedProcessResult:
    """Run an argv-only command with bounded capture and process-tree cleanup."""

    if isinstance(argv, (str, bytes)) or not argv:
        raise TypeError("argv must be a non-empty sequence of strings")
    normalized = list(argv)
    if any(not isinstance(item, str) or not item or "\x00" in item for item in normalized):
        raise ValueError("argv contains an invalid item")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite value greater than zero")
    if isinstance(max_output_chars, bool) or not isinstance(max_output_chars, int) or max_output_chars <= 0:
        raise ValueError("max_output_chars must be a positive integer")
    if input_text is not None and (not isinstance(input_text, str) or "\x00" in input_text):
        raise ValueError("input_text must be text without NUL bytes")

    stdout_capture = _BoundedTextCapture(max_output_chars)
    stderr_capture = _BoundedTextCapture(max_output_chars)
    try:
        completed = _run_owned_process(
            normalized,
            cwd=cwd,
            stdout=stdout_capture,
            stderr=stderr_capture,
            timeout=float(timeout),
            env=dict(os.environ if env is None else env),
            input_text=input_text,
        )
        returncode = int(completed.returncode)
        timed_out = False
    except subprocess.TimeoutExpired:
        returncode = 124
        timed_out = True
    except FileNotFoundError:
        returncode = 127
        timed_out = False
    except PermissionError:
        returncode = 126
        timed_out = False
    except OSError:
        returncode = 1
        timed_out = False

    stdout = _read_process_stream(stdout_capture, None, max_output_chars)
    stderr = _read_process_stream(stderr_capture, None, max_output_chars)
    bounded_stdout, stdout_truncated = _bounded(stdout, max_output_chars)
    bounded_stderr, stderr_truncated = _bounded(stderr, max_output_chars)
    return BoundedProcessResult(
        returncode=returncode,
        stdout=bounded_stdout,
        stderr=bounded_stderr,
        timed_out=timed_out,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


def _specialist_prompt(task: str, recommended_agent: str | None) -> str:
    """Add Agency expertise context without treating a roster slug as a host id."""
    if not recommended_agent:
        return task
    specialist = recommended_agent.strip()
    if not specialist:
        return task
    if "\x00" in specialist:
        raise ValueError("recommended_agent must not contain NUL bytes")
    if len(specialist) > _MAX_SPECIALIST_CHARS:
        raise ValueError(
            "recommended_agent exceeds the delegation display-token limit"
        )
    return (
        f"Agency specialist perspective requested: {specialist}\n\n"
        f"Delegated task:\n{task}"
    )


class BackendError(RuntimeError):
    """Base error carrying the normalized process result, when available."""

    def __init__(self, message: str, *, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result or {}


class BackendUnavailableError(BackendError):
    """The configured executable cannot be launched on this host."""


class BackendTimeoutError(BackendError):
    """The host process exceeded the configured delegation deadline."""


class BackendExecutionError(BackendError):
    """The host process exited unsuccessfully."""


class BackendProtocolError(BackendError):
    """The host claimed process success but emitted an invalid response."""


@runtime_checkable
class DelegateBackend(Protocol):
    """Protocol implemented by delegation runtime adapters."""

    name: str

    def is_available(self) -> bool:
        """Return True when this backend can run on the current host."""

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Dispatch one work unit and return backend-specific result data."""


@dataclass(slots=True)
class CommandBackend:
    """Generic subprocess-backed delegation backend.

    ``command`` is an argv prefix, not a shell command string.  This distinction
    is intentional: shell parsing differs between Windows and POSIX and would
    make task text executable.
    """

    command: Sequence[str]
    name: str = "command"
    timeout: float = 3600
    extra_env: dict[str, str] = field(default_factory=dict)
    output_format: Literal["text", "json", "jsonl"] = "text"
    max_output_chars: int = 2_000_000

    def __post_init__(self) -> None:
        if isinstance(self.command, (str, bytes)):
            raise TypeError("command must be an argv sequence, not a shell command string")
        self.command = tuple(self.command)
        if not isinstance(self.name, str) or not self.name.strip() or "\x00" in self.name:
            raise ValueError("backend name must be a non-empty string")
        if self.output_format not in {"text", "json", "jsonl"}:
            raise ValueError("output_format must be text, json, or jsonl")
        if (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise ValueError("timeout must be a finite value greater than zero")
        if (
            isinstance(self.max_output_chars, bool)
            or not isinstance(self.max_output_chars, int)
            or self.max_output_chars <= 0
        ):
            raise ValueError("max_output_chars must be a positive integer")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self.extra_env.items()):
            raise TypeError("extra_env keys and values must be strings")
        if any("\x00" in key or "=" in key or "\x00" in value for key, value in self.extra_env.items()):
            raise ValueError("extra_env contains an invalid environment key or value")
        for value in self.command:
            if not isinstance(value, str) or not value:
                raise ValueError("every command argv item must be a non-empty string")
            if "\x00" in value:
                raise ValueError("command argv must not contain NUL bytes")

    def executable_path(self) -> str | None:
        """Resolve the configured executable without spawning a process."""
        if not self.command:
            return None
        try:
            search_path = self.extra_env.get("PATH") or self.extra_env.get("Path")
            if search_path is None:
                return shutil.which(self.command[0])
            return shutil.which(self.command[0], path=search_path)
        except (OSError, TypeError, ValueError):
            return None

    def availability(self) -> dict[str, Any]:
        """Return a truthful, diagnostic availability record."""
        if not self.command:
            return {
                "backend": self.name,
                "available": False,
                "executable": None,
                "reason": "no command configured",
            }
        executable = self.executable_path()
        return {
            "backend": self.name,
            "available": bool(executable),
            "executable": executable,
            "reason": "" if executable else f"executable not found: {self.command[0]}",
        }

    def is_available(self) -> bool:
        return bool(self.executable_path())

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        """Return argv for a task. Subclasses override for native CLIs."""
        del recommended_agent
        return [*self.command, task]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str | None:
        """Return optional stdin for a task. CLI-specific backends may override."""
        del task, recommended_agent
        return None

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        """Parse successful output according to the configured wire format."""
        if self.output_format == "text":
            return stdout, {}
        if self.output_format == "json":
            try:
                return json.loads(stdout), {}
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON output at character {exc.pos}") from exc

        events: list[Any] = []
        for line_number, line in enumerate(stdout.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL output on line {line_number}") from exc
        if not events:
            raise ValueError("JSONL output contained no events")
        return events, {"events": events}

    def _validate_task(self, task: str) -> str:
        if not isinstance(task, str):
            raise TypeError("task must be a string")
        if not task.strip():
            raise ValueError("task must not be empty")
        if "\x00" in task:
            raise ValueError("task must not contain NUL bytes")
        if len(task) > _MAX_TASK_CHARS:
            raise ValueError(
                f"task exceeds the {_MAX_TASK_CHARS}-character delegation limit"
            )
        return task

    def _resolve_workdir(self, workdir: str | None) -> str | None:
        if workdir is None:
            return None
        path = Path(workdir).expanduser()
        if not path.exists():
            raise ValueError(f"workdir does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"workdir is not a directory: {path}")
        return str(path.resolve())

    def _result(
        self,
        *,
        argv: list[str],
        executable: str | None,
        workdir: str | None,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        status: str,
        error: str = "",
        sensitive: Iterable[str] = (),
    ) -> dict[str, Any]:
        bounded_stdout, stdout_truncated = _bounded(
            _redact_text(stdout, sensitive),
            self.max_output_chars,
        )
        bounded_stderr, stderr_truncated = _bounded(
            _redact_text(stderr, sensitive),
            self.max_output_chars,
        )
        result: dict[str, Any] = {
            "backend": self.name,
            "status": status,
            "exit_code": exit_code,
            "stdout": bounded_stdout,
            "stderr": bounded_stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "command": _redact_value(argv, sensitive),
            "executable": executable,
            "workdir": workdir or "",
        }
        if error:
            result["error"] = _redact_text(error, sensitive)
        return result

    def execute(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        check: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run and normalize a host process.

        With ``check=True`` (the delegation default), unavailable, timed-out,
        non-zero, and malformed-success responses raise ``BackendError``.
        Wrappers that historically return records can use ``check=False``.
        """
        del kwargs
        task = self._validate_task(task)
        delegation_prompt = _specialist_prompt(task, recommended_agent)
        sensitive = (delegation_prompt, task)
        cwd = self._resolve_workdir(workdir)
        if not self.command:
            result = self._result(
                argv=[],
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error="no command configured",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: no command configured",
                result=result,
            )
            if check:
                raise error
            return result
        argv = self.build_command(task, recommended_agent=recommended_agent)
        input_text = self.build_input(task, recommended_agent=recommended_agent)
        if not argv:
            raise BackendUnavailableError(f"backend {self.name} has no command configured")
        if any(not isinstance(value, str) or not value or "\x00" in value for value in argv):
            raise ValueError("built command contains an invalid argv item")
        if input_text is not None and (
            not isinstance(input_text, str) or "\x00" in input_text
        ):
            raise ValueError("built input must be text without NUL bytes")

        executable = self.executable_path()
        if not executable:
            result = self._result(
                argv=argv,
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error=f"executable not found: {self.command[0] if self.command else '<unconfigured>'}",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: {result['error']}",
                result=result,
            )
            if check:
                raise error
            return result
        argv[0] = executable

        env = _delegation_environment(self.name, self.extra_env)
        stdout_capture = _BoundedTextCapture(self.max_output_chars)
        stderr_capture = _BoundedTextCapture(self.max_output_chars)
        try:
            completed = _run_owned_process(
                argv,
                cwd=cwd,
                stdout=stdout_capture,
                stderr=stderr_capture,
                timeout=self.timeout,
                env=env,
                input_text=input_text,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _read_process_stream(
                stdout_capture,
                exc.stdout if exc.stdout is not None else exc.output,
                self.max_output_chars,
            )
            stderr = _read_process_stream(
                stderr_capture,
                exc.stderr,
                self.max_output_chars,
            )
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                status="timed_out",
                error=f"backend command timed out after {self.timeout:g}s",
                sensitive=sensitive,
            )
            error = BackendTimeoutError(result["error"], result=result)
            if check:
                raise error
            return result
        except FileNotFoundError:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error=f"resolved executable disappeared before launch: {executable}",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(result["error"], result=result)
            if check:
                raise error
            return result
        except PermissionError as exc:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=126,
                status="failed",
                error=f"executable permission denied: {exc}",
                sensitive=sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            if check:
                raise error
            return result
        except OSError as exc:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=1,
                status="failed",
                error=f"could not launch backend {self.name}: {exc}",
                sensitive=sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            if check:
                raise error
            return result

        stdout = _read_process_stream(
            stdout_capture,
            completed.stdout,
            self.max_output_chars,
        )
        stderr = _read_process_stream(
            stderr_capture,
            completed.stderr,
            self.max_output_chars,
        )
        result = self._result(
            argv=argv,
            executable=executable,
            workdir=cwd,
            exit_code=int(completed.returncode),
            stdout=stdout,
            stderr=stderr,
            status="completed" if completed.returncode == 0 else "failed",
            sensitive=sensitive,
        )
        if completed.returncode != 0:
            preview = (
                result["stderr"].strip()
                or result["stdout"].strip()
                or "no process output"
            )
            preview, _ = _bounded(preview, _ERROR_PREVIEW_CHARS)
            result["error"] = _redact_text(
                f"backend {self.name} exited with {completed.returncode}: {preview}",
                sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            if check:
                raise error
            return result

        try:
            if self.output_format != "text" and len(stdout) > self.max_output_chars:
                raise ValueError(
                    f"structured output exceeded the {self.max_output_chars}-character limit"
                )
            output, metadata = self.parse_stdout(stdout)
        except ValueError as exc:
            result["status"] = "failed"
            result["process_exit_code"] = 0
            result["exit_code"] = 1
            result["error"] = _redact_text(
                f"backend {self.name} returned an invalid success response: {exc}",
                sensitive,
            )
            error = BackendProtocolError(result["error"], result=result)
            if check:
                raise error
            return result
        # Do not return a second unbounded copy of text output. Structured
        # responses were size-checked before parsing above.
        result["output"] = (
            result["stdout"]
            if self.output_format == "text"
            else _redact_value(output, sensitive)
        )
        result.update(_redact_value(metadata, sensitive))
        return result

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the backend and require both process and protocol success."""
        return self.execute(
            task=task,
            workdir=workdir,
            recommended_agent=recommended_agent,
            check=True,
            **kwargs,
        )


@dataclass(slots=True)
class HermesDelegateBackend(CommandBackend):
    """Hermes' documented, plain-text scripted one-shot interface."""

    command: Sequence[str] = ("hermes", "-z")
    name: str = "hermes"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        if not stdout.strip():
            raise ValueError("Hermes produced no final response text")
        return stdout, {}


@dataclass(slots=True)
class OpenClawSessionsBackend(CommandBackend):
    """OpenClaw agent-turn backend (legacy class name kept for API compatibility).

    ``sessions_spawn`` is an in-agent tool, not an OpenClaw CLI command.  The
    supported subprocess contract is ``openclaw agent``.  Agency roster slugs
    are prompt context; ``agent_id`` is the configured OpenClaw runtime id.
    """

    command: Sequence[str] = ("openclaw", "agent")
    name: str = "openclaw"
    output_format: Literal["text", "json", "jsonl"] = "json"
    agent_id: str = "main"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        agent_id = self.agent_id.strip()
        if not agent_id or "\x00" in agent_id:
            raise ValueError("OpenClaw agent_id must be a non-empty value without NUL bytes")
        return [
            *self.command,
            "--agent",
            agent_id,
            "--message",
            _specialist_prompt(task, recommended_agent),
            "--json",
        ]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        payload, _ = CommandBackend.parse_stdout(self, stdout)
        if not isinstance(payload, dict):
            raise ValueError("OpenClaw JSON response must be an object")
        if payload.get("error"):
            raise ValueError(f"OpenClaw reported an error: {payload['error']}")
        status = str(payload.get("status") or "").strip().lower()
        if status and status not in {"completed", "done", "ok", "succeeded", "success"}:
            raise ValueError(f"OpenClaw reported non-terminal status {status!r}")
        texts = [
            str(item.get("text"))
            for item in payload.get("payloads", [])
            if isinstance(item, dict) and item.get("text") is not None
        ]
        if not any(text.strip() for text in texts):
            raise ValueError("OpenClaw returned no terminal response payload")
        return "\n".join(texts), {"response": payload}


# Preferred truthful name; the legacy import remains supported above.
OpenClawAgentBackend = OpenClawSessionsBackend


@dataclass(slots=True)
class CodexExecBackend(CommandBackend):
    """OpenAI Codex CLI backend using stable non-interactive JSONL exec mode."""

    command: Sequence[str] = ("codex", "exec")
    name: str = "codex"
    output_format: Literal["text", "json", "jsonl"] = "jsonl"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        del task, recommended_agent
        return [
            *self.command,
            "--json",
            "--color",
            "never",
        ]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str:
        return _specialist_prompt(task, recommended_agent)

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        events, metadata = CommandBackend.parse_stdout(self, stdout)
        assert isinstance(events, list)
        event_types = {
            str(event.get("type") or "")
            for event in events
            if isinstance(event, dict)
        }
        failure = next(
            (
                event
                for event in events
                if isinstance(event, dict) and str(event.get("type") or "") in {"error", "turn.failed"}
            ),
            None,
        )
        if failure is not None:
            raise ValueError(f"Codex emitted a failure event: {failure.get('type')}")
        if "turn.completed" not in event_types:
            raise ValueError("Codex JSONL stream ended without turn.completed")

        messages: list[str] = []
        for event in events:
            if not isinstance(event, dict) or event.get("type") != "item.completed":
                continue
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message" and item.get("text") is not None:
                messages.append(str(item["text"]))
        metadata["events"] = events
        return messages[-1] if messages else events, metadata


@dataclass(slots=True)
class ClaudeExecBackend(CommandBackend):
    """Claude Code backend using documented print-mode JSON output."""

    command: Sequence[str] = ("claude", "-p", "--output-format", "json")
    name: str = "claude"
    output_format: Literal["text", "json", "jsonl"] = "json"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        del task, recommended_agent
        return [*self.command]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str:
        return _specialist_prompt(task, recommended_agent)

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        payload, _ = CommandBackend.parse_stdout(self, stdout)
        if not isinstance(payload, dict):
            raise ValueError("Claude JSON response must be an object")
        if payload.get("error"):
            raise ValueError(f"Claude reported an error: {payload['error']}")
        if payload.get("is_error") is True:
            raise ValueError("Claude reported is_error=true")
        subtype = str(payload.get("subtype") or "").strip().lower()
        if subtype and subtype not in {"completed", "done", "success", "succeeded"}:
            raise ValueError(f"Claude reported non-terminal subtype {subtype!r}")
        result = payload.get("result")
        if not isinstance(result, (str, list, dict)) or not result:
            raise ValueError("Claude returned no terminal result")
        return result, {"response": payload}


@dataclass(slots=True)
class GenericCLIBackend(CommandBackend):
    """Explicitly configured fallback for an otherwise unsupported agent CLI."""

    command: Sequence[str] = ()
    name: str = "generic"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]


class BackendRegistry:
    """Ordered registry of pluggable delegation backends."""

    def __init__(self, backends: Iterable[DelegateBackend] | None = None) -> None:
        self._backends: list[DelegateBackend] = list(backends or [])

    def register(self, backend: DelegateBackend) -> DelegateBackend:
        """Register a backend and return it for decorator-style use."""
        self._backends.append(backend)
        return backend

    def unregister(self, name: str) -> None:
        """Remove all backends with the given name."""
        self._backends = [backend for backend in self._backends if backend.name != name]

    def available_backends(self) -> list[DelegateBackend]:
        """Return currently available backends in selection order."""
        return [backend for backend in self._backends if backend.is_available()]

    def select_backend(self, *, preferred: str | None = None) -> DelegateBackend:
        """Select the first available backend, optionally constrained by name."""
        candidates = self._backends
        if preferred:
            candidates = [backend for backend in candidates if backend.name == preferred]
        for backend in candidates:
            if backend.is_available():
                return backend
        requested = f" named {preferred!r}" if preferred else ""
        details: list[str] = []
        for backend in candidates:
            availability = getattr(backend, "availability", None)
            if callable(availability):
                record = availability()
                details.append(f"{backend.name}: {record.get('reason') or 'unavailable'}")
            else:
                details.append(f"{backend.name}: unavailable")
        suffix = f" ({'; '.join(details)})" if details else ""
        raise BackendUnavailableError(f"No available delegation backend{requested}{suffix}")

    def delegate_func(self, *, preferred: str | None = None):
        """Return a delegate_func-compatible callable for lifecycle dispatch."""
        backend = self.select_backend(preferred=preferred)

        def _delegate(**kwargs: Any) -> Any:
            return backend.delegate(**kwargs)

        setattr(_delegate, "backend_name", backend.name)
        return _delegate


DEFAULT_REGISTRY = BackendRegistry(
    [
        HermesDelegateBackend(),
        OpenClawSessionsBackend(),
        CodexExecBackend(),
        ClaudeExecBackend(),
        GenericCLIBackend(),
    ]
)


def register_backend(backend: DelegateBackend) -> DelegateBackend:
    """Register a backend in the process-wide default registry."""
    return DEFAULT_REGISTRY.register(backend)


def get_delegate_func(*, preferred: str | None = None, registry: BackendRegistry | None = None):
    """Return a lifecycle-compatible delegate callable from a registry."""
    return (registry or DEFAULT_REGISTRY).delegate_func(preferred=preferred)


__all__ = [
    "BoundedProcessResult",
    "BackendError",
    "BackendExecutionError",
    "BackendProtocolError",
    "BackendRegistry",
    "BackendTimeoutError",
    "BackendUnavailableError",
    "ClaudeExecBackend",
    "CodexExecBackend",
    "CommandBackend",
    "DEFAULT_REGISTRY",
    "DelegateBackend",
    "GenericCLIBackend",
    "HermesDelegateBackend",
    "OpenClawAgentBackend",
    "OpenClawSessionsBackend",
    "get_delegate_func",
    "register_backend",
    "run_bounded_process",
]
