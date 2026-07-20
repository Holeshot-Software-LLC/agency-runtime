"""Atomic Windows Job-at-creation subprocess launcher.

The public surface is intentionally narrow: Agency Runtime supplies an already
validated absolute argv, standard-stream configuration, cwd, and environment.
The launcher reuses :class:`subprocess.Popen` pipe and wait semantics while
replacing only native process creation with ``STARTUPINFOEX`` containing both a
restricted handle list and ``PROC_THREAD_ATTRIBUTE_JOB_LIST``.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from contextlib import suppress
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, cast

from agency_runtime.core.exception_notes import add_exception_note as _add_exception_note
from agency_runtime.core.owned_process_windows import WindowsJob

_IS_WINDOWS = os.name == "nt"
_CREATE_NEW_PROCESS_GROUP = 0x00000200
_CREATE_SUSPENDED = 0x00000004
_CREATE_UNICODE_ENVIRONMENT = 0x00000400
_CREATE_NO_WINDOW = 0x08000000
_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
_PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D
_STARTF_USESTDHANDLES = 0x00000100
_SUBPROCESS_HANDLE_TYPE = getattr(subprocess, "Handle", int)


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _BasicLimitInformation(ctypes.Structure):
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


class _ExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _BasicAccountingInformation(ctypes.Structure):
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


class _StartupInfoW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _StartupInfoExW(ctypes.Structure):
    _fields_ = [
        ("StartupInfo", _StartupInfoW),
        ("lpAttributeList", ctypes.c_void_p),
    ]


class _ProcessInformation(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class _OwnedJobHandleResult(ctypes.c_void_p):
    """A CreateJobObjectW result that owns itself before Python can interrupt."""

    _kernel32: Any = None

    @property
    def native_handle(self) -> int:
        return int(self.value or 0)

    def __bool__(self) -> bool:
        return bool(self.native_handle)

    def __int__(self) -> int:
        return self.native_handle

    def close_owned_handle(self) -> None:
        handle = self.native_handle
        if not handle:
            return
        self.value = None
        self._kernel32.CloseHandle(handle)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close_owned_handle()


class _LegacyJobHandleOwner:
    """Idempotent compatibility owner for injected non-ctypes native APIs."""

    __slots__ = ("_api", "_handle")

    def __init__(self, handle: Any, api: Any) -> None:
        self._api = api
        self._handle = int(handle)

    @property
    def native_handle(self) -> int:
        return self._handle

    def __bool__(self) -> bool:
        return bool(self._handle)

    def close_owned_handle(self) -> None:
        handle = self._handle
        if not handle:
            return
        self._handle = 0
        self._api.CloseHandle(handle)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close_owned_handle()


class _OwnedProcessInformation(_ProcessInformation):
    """Own CreateProcessW output handles until their shared wrappers close."""

    def __init__(self, api: _NativeApi) -> None:
        super().__init__()
        self._api = api

    def _handle(self, attribute: str) -> int:
        return int(getattr(self, attribute) or 0)

    def _close_handle(self, attribute: str) -> None:
        handle = self._handle(attribute)
        if not handle:
            return
        setattr(self, attribute, 0)
        self._api.kernel32.CloseHandle(handle)

    @property
    def process_handle(self) -> int:
        return self._handle("hProcess")

    @property
    def thread_handle(self) -> int:
        return self._handle("hThread")

    def close_process(self) -> None:
        self._close_handle("hProcess")

    def close_thread(self) -> None:
        self._close_handle("hThread")

    def close(self) -> None:
        first_error: BaseException | None = None
        try:
            self.close_thread()
        except BaseException as exc:
            first_error = exc
        try:
            self.close_process()
        except BaseException as exc:
            if first_error is None:
                first_error = exc
        if first_error is not None:
            raise first_error

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


@dataclass(slots=True)
class _NativeApi:
    kernel32: Any


def _native_api() -> _NativeApi:
    if not _IS_WINDOWS:
        raise OSError("atomic Windows process containment is unavailable")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    job_handle_type = type(
        "_NativeOwnedJobHandleResult",
        (_OwnedJobHandleResult,),
        {"_kernel32": kernel32},
    )
    kernel32.CreateJobObjectW.restype = job_handle_type
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
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
    kernel32.InitializeProcThreadAttributeList.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.InitializeProcThreadAttributeList.restype = wintypes.BOOL
    kernel32.UpdateProcThreadAttribute.argtypes = [
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    kernel32.UpdateProcThreadAttribute.restype = wintypes.BOOL
    kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    kernel32.DeleteProcThreadAttributeList.restype = None
    kernel32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(_StartupInfoW),
        ctypes.POINTER(_ProcessInformation),
    ]
    kernel32.CreateProcessW.restype = wintypes.BOOL
    kernel32.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return _NativeApi(kernel32)


def _native_error(message: str) -> OSError:
    error = ctypes.get_last_error()
    detail = ctypes.FormatError(error).strip()
    return OSError(error, f"{message}: {detail or 'Windows error'}")


def _close_pipe_fds_preserving_primary(
    process: Any,
    descriptors: tuple[Any, Any, Any, Any, Any, Any],
    primary_error: BaseException | None,
) -> None:
    """Close every child-side pipe without replacing an active failure."""

    try:
        process._close_pipe_fds(*descriptors)
    except BaseException as cleanup_error:
        if primary_error is None:
            raise
        _add_exception_note(
            primary_error,
            f"Windows child pipe cleanup failed: {cleanup_error}",
        )


def _create_job(api: _NativeApi) -> WindowsJob:
    result = api.kernel32.CreateJobObjectW(None, None)
    if not result:
        raise _native_error("could not create Windows Job Object")
    handle = (
        result
        if isinstance(result, _OwnedJobHandleResult)
        else _LegacyJobHandleOwner(result, api.kernel32)
    )
    try:
        limits = _ExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not api.kernel32.SetInformationJobObject(
            handle.native_handle,
            9,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            raise _native_error("could not configure Windows Job Object")
        return WindowsJob(handle, api.kernel32, _BasicAccountingInformation)
    except BaseException:
        handle.close_owned_handle()
        raise


@dataclass(slots=True)
class _CreationAttributes:
    api: _NativeApi
    buffer: Any
    pointer: Any
    handle_values: Any
    job_values: Any
    initialized: bool = False
    closed: bool = False

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            pointer = self.pointer
            self.pointer = None
            initialized = self.initialized
            self.initialized = False
            if initialized:
                self.api.kernel32.DeleteProcThreadAttributeList(pointer)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


def _creation_attributes(
    api: _NativeApi,
    *,
    inherited_handles: list[int],
    job: WindowsJob,
) -> _CreationAttributes:
    if not inherited_handles:
        raise OSError("atomic Windows process launch requires explicit standard handles")
    size = ctypes.c_size_t()
    api.kernel32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
    if size.value == 0:
        raise _native_error("Windows process attribute sizing failed")
    buffer = ctypes.create_string_buffer(size.value)
    pointer = ctypes.cast(buffer, ctypes.c_void_p)
    handle_values = (wintypes.HANDLE * len(inherited_handles))(*inherited_handles)
    job_values = (wintypes.HANDLE * 1)(job.native_handle)
    attributes = _CreationAttributes(
        api,
        buffer,
        pointer,
        handle_values,
        job_values,
    )
    try:
        # Arm before the native output call. If Python delivers an asynchronous
        # exception at its return boundary, the pre-existing owner will delete
        # the potentially initialized list rather than leaking it.
        attributes.initialized = True
        if not api.kernel32.InitializeProcThreadAttributeList(
            pointer,
            2,
            0,
            ctypes.byref(size),
        ):
            attributes.initialized = False
            raise _native_error("Windows process attribute initialization failed")
        if not api.kernel32.UpdateProcThreadAttribute(
            pointer,
            0,
            _PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            ctypes.cast(handle_values, ctypes.c_void_p),
            ctypes.sizeof(handle_values),
            None,
            None,
        ):
            raise _native_error("Windows standard-handle attribute failed")
        if not api.kernel32.UpdateProcThreadAttribute(
            pointer,
            0,
            _PROC_THREAD_ATTRIBUTE_JOB_LIST,
            ctypes.cast(job_values, ctypes.c_void_p),
            ctypes.sizeof(job_values),
            None,
            None,
        ):
            raise _native_error("atomic Windows Job-list attribute is unavailable")
        return attributes
    except BaseException:
        attributes.close()
        raise


def _environment_buffer(environment: dict[str, str] | None) -> Any:
    if environment is None:
        return None
    validated: list[tuple[str, str]] = []
    normalized_keys: set[str] = set()
    for key, value in environment.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("Windows process environment must contain strings")
        if not key or "\x00" in key or "=" in key or "\x00" in value:
            raise ValueError("Windows process environment contains an invalid item")
        normalized = key.upper()
        if normalized in normalized_keys:
            raise ValueError("Windows process environment contains duplicate keys")
        normalized_keys.add(normalized)
        validated.append((key, value))
    entries = [
        f"{key}={value}" for key, value in sorted(validated, key=lambda item: item[0].upper())
    ]
    # create_unicode_buffer appends its own terminator; one explicit NUL makes
    # the environment block end with the two NULs required by CreateProcessW.
    return ctypes.create_unicode_buffer("\x00".join(entries) + "\x00")


@dataclass(slots=True)
class _LaunchReceipt:
    process_handle: Any | None
    primary_thread: _PrimaryThread | None
    process_id: int
    job: WindowsJob | None
    standard_handles: tuple[Any, ...] = ()
    _armed: bool = True

    def disarm(self) -> None:
        """Commit the one-way transfer to ``AtomicWindowsPopen``."""

        if not self._armed:
            return
        self._armed = False
        self.process_handle = None
        self.primary_thread = None
        self.job = None
        self.standard_handles = ()

    def close(self) -> None:
        """Fail closed while this receipt still owns the native launch."""

        if not self._armed:
            return
        self._armed = False
        process_handle = self.process_handle
        primary_thread = self.primary_thread
        job = self.job
        standard_handles = self.standard_handles
        self.process_handle = None
        self.primary_thread = None
        self.job = None
        self.standard_handles = ()

        first_error: BaseException | None = None

        def attempt(action: Any) -> None:
            nonlocal first_error
            try:
                action()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc

        if job is not None:
            attempt(job.terminate)
            attempt(job.close)
        if primary_thread is not None:
            attempt(primary_thread.close)
        if process_handle is not None:
            attempt(process_handle.Close)
        seen: set[int] = set()
        for handle in standard_handles:
            identity = id(handle)
            if identity in seen:
                continue
            seen.add(identity)
            close = getattr(handle, "Close", None)
            if callable(close):
                attempt(close)
        if first_error is not None:
            raise first_error

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


def _process_handle_type(
    information: _OwnedProcessInformation,
) -> type[Any]:
    """Create a Handle subclass sharing the PROCESS_INFORMATION owner."""

    class _SharedProcessHandle(_SUBPROCESS_HANDLE_TYPE):
        def Close(self) -> None:
            if not getattr(self, "closed", False):
                self.closed = True
                information.close_process()

        def Detach(self) -> int:
            if getattr(self, "closed", False):
                raise ValueError("already closed")
            handle = information.process_handle
            if not handle:
                raise ValueError("already closed")
            self.closed = True
            information.hProcess = 0
            return handle

        __del__ = Close

    return _SharedProcessHandle


def _launch(
    *,
    application: str,
    command_line: str,
    cwd: str | None,
    environment: dict[str, str] | None,
    inherited_handles: list[int],
    stdin_handle: int,
    stdout_handle: int,
    stderr_handle: int,
    creation_flags: int,
    standard_handles: tuple[Any, ...] = (),
) -> _LaunchReceipt:
    api = _native_api()
    job = _create_job(api)
    attributes: _CreationAttributes | None = None
    process_information = _OwnedProcessInformation(api)
    process_handle_class: Any = None
    process_handle: Any | None = None
    primary_thread: _PrimaryThread | None = None
    try:
        primary_thread = _PrimaryThread(process_information, api)
        process_handle_class = _process_handle_type(process_information)
        attributes = _creation_attributes(
            api,
            inherited_handles=inherited_handles,
            job=job,
        )
        startup = _StartupInfoExW()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.StartupInfo.dwFlags = _STARTF_USESTDHANDLES
        startup.StartupInfo.hStdInput = wintypes.HANDLE(stdin_handle)
        startup.StartupInfo.hStdOutput = wintypes.HANDLE(stdout_handle)
        startup.StartupInfo.hStdError = wintypes.HANDLE(stderr_handle)
        startup.lpAttributeList = attributes.pointer
        command_buffer = ctypes.create_unicode_buffer(command_line)
        environment_buffer = _environment_buffer(environment)
        flags = (
            creation_flags
            | _CREATE_SUSPENDED
            | _CREATE_UNICODE_ENVIRONMENT
            | _EXTENDED_STARTUPINFO_PRESENT
        )
        environment_pointer = (
            None if environment_buffer is None else ctypes.cast(environment_buffer, ctypes.c_void_p)
        )
        if not api.kernel32.CreateProcessW(
            application,
            command_buffer,
            None,
            None,
            True,
            flags,
            environment_pointer,
            cwd,
            ctypes.byref(startup.StartupInfo),
            ctypes.byref(process_information),
        ):
            raise _native_error("atomic Windows process creation failed")
        if not process_information.process_handle or not process_information.thread_handle:
            raise OSError("atomic Windows process creation returned incomplete handles")
        process_handle = process_handle_class(process_information.process_handle)
        return _LaunchReceipt(
            process_handle,
            primary_thread,
            int(process_information.dwProcessId),
            job,
            standard_handles,
        )
    except BaseException:
        if primary_thread is not None:
            with suppress(BaseException):
                primary_thread.close()
        else:
            with suppress(BaseException):
                process_information.close_thread()
        if process_handle is not None:
            with suppress(BaseException):
                process_handle.Close()
        else:
            with suppress(BaseException):
                process_information.close_process()
        with suppress(BaseException):
            job.terminate()
        with suppress(BaseException):
            job.close()
        raise
    finally:
        if attributes is not None:
            with suppress(BaseException):
                attributes.close()


class _PrimaryThread:
    def __init__(
        self,
        handle: int | _OwnedProcessInformation,
        api: _NativeApi,
    ) -> None:
        self._information = handle if isinstance(handle, _OwnedProcessInformation) else None
        self._handle = 0 if self._information is not None else int(handle)
        self._api = api

    @property
    def native_handle(self) -> int:
        if self._information is not None:
            return self._information.thread_handle
        return self._handle

    def resume(self) -> bool:
        handle = self.native_handle
        if not handle:
            return False
        try:
            return int(self._api.kernel32.ResumeThread(handle)) == 1
        finally:
            self.close()

    def close(self) -> None:
        if self._information is not None:
            self._information.close_thread()
        elif self._handle:
            handle = self._handle
            self._handle = 0
            self._api.kernel32.CloseHandle(handle)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


class AtomicWindowsPopen(subprocess.Popen[Any]):
    """Popen-compatible process created inside its Job Object atomically."""

    _agency_atomic_windows_process = True

    def __del__(self) -> None:
        # Popen owns the process handle; this adapter additionally owns a
        # kill-on-close Job and the suspended primary thread until the caller
        # explicitly claims/resumes them.  A construction consumer can be
        # interrupted before that handoff, so object finalization must preserve
        # the same fail-closed ownership boundary.
        with suppress(BaseException):
            close_atomic_windows_process_resources(self)
        with suppress(BaseException):
            super().__del__()

    def _execute_child(
        self,
        args: Any,
        executable: Any,
        preexec_fn: Any,
        close_fds: bool,
        pass_fds: Any,
        cwd: Any,
        env: Any,
        startupinfo: Any,
        creationflags: int,
        shell: bool,
        p2cread: Any,
        p2cwrite: Any,
        c2pread: Any,
        c2pwrite: Any,
        errread: Any,
        errwrite: Any,
        unused_restore_signals: Any,
        unused_gid: Any,
        unused_gids: Any,
        unused_uid: Any,
        unused_umask: Any,
        unused_start_new_session: Any,
        unused_process_group: Any = None,
    ) -> None:
        del (
            preexec_fn,
            close_fds,
            unused_restore_signals,
            unused_gid,
            unused_gids,
            unused_uid,
            unused_umask,
            unused_start_new_session,
            unused_process_group,
        )
        receipt: _LaunchReceipt | None = None
        job: WindowsJob | None = None
        primary_thread: _PrimaryThread | None = None
        process_handle: Any | None = None
        pipe_fds_closed = False
        primary_failure = False
        pipe_descriptors = (
            p2cread,
            p2cwrite,
            c2pread,
            c2pwrite,
            errread,
            errwrite,
        )
        try:
            if pass_fds or startupinfo is not None or shell:
                raise ValueError("atomic Windows process launch received unsupported options")
            values = [os.fsdecode(value) for value in args]
            if not values or any(not value or "\x00" in value for value in values):
                raise ValueError("atomic Windows process argv contains an invalid item")
            application = os.path.abspath(os.fsdecode(executable or values[0]))
            if application != values[0] or not os.path.isabs(application):
                raise ValueError("atomic Windows process executable must be an absolute path")
            command_line = subprocess.list2cmdline(values)
            current_directory = None if cwd is None else os.fsdecode(cwd)
            if current_directory is not None and (
                not current_directory
                or "\x00" in current_directory
                or not os.path.isabs(current_directory)
            ):
                raise ValueError("atomic Windows process cwd must be an absolute path")
            inherited_handles = self._filter_handle_list(
                [int(p2cread), int(c2pwrite), int(errwrite)]
            )
            sys.audit("subprocess.Popen", application, command_line, current_directory, env)
            receipt = _launch(
                application=application,
                command_line=command_line,
                cwd=current_directory,
                environment=env,
                inherited_handles=inherited_handles,
                stdin_handle=int(p2cread),
                stdout_handle=int(c2pwrite),
                stderr_handle=int(errwrite),
                creation_flags=creationflags,
                standard_handles=(p2cread, c2pwrite, errwrite),
            )
            job = receipt.job
            primary_thread = receipt.primary_thread
            process_handle = receipt.process_handle
            if job is None or primary_thread is None or process_handle is None:
                raise OSError("atomic Windows launch receipt is incomplete")
            self._agency_windows_job = job
            self._agency_primary_thread = primary_thread
            self._handle = process_handle
            self.pid = receipt.process_id
            self._child_created = True
            self._close_pipe_fds(*pipe_descriptors)
            pipe_fds_closed = True
            receipt.disarm()
        except BaseException:
            primary_failure = True
            if receipt is not None:
                receipt_owned = receipt._armed
                with suppress(BaseException):
                    receipt.close()
                if not receipt_owned:
                    with suppress(BaseException):
                        cast(WindowsJob, job).terminate()
                    with suppress(BaseException):
                        cast(WindowsJob, job).close()
                    with suppress(BaseException):
                        cast(_PrimaryThread, primary_thread).close()
                    with suppress(BaseException):
                        cast(Any, process_handle).Close()
                object.__setattr__(self, "_agency_primary_thread", None)
                object.__setattr__(self, "_agency_windows_job", None)
                object.__setattr__(self, "_handle", None)
                object.__setattr__(self, "_child_created", False)
            raise
        finally:
            if not pipe_fds_closed:
                _close_pipe_fds_preserving_primary(
                    self,
                    pipe_descriptors,
                    sys.exc_info()[1] if primary_failure else None,
                )


def spawn_atomic_windows_process(
    argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdin: Any,
    text: bool,
) -> AtomicWindowsPopen:
    """Create a suspended child whose Job membership is already effective."""

    if not _IS_WINDOWS:
        raise OSError("atomic Windows process containment is unavailable")
    options: dict[str, Any] = {
        "cwd": cwd,
        "env": env,
        "executable": argv[0],
        "stdin": stdin,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "close_fds": True,
        "creationflags": _CREATE_NEW_PROCESS_GROUP | _CREATE_NO_WINDOW,
    }
    if text:
        options.update(text=True, encoding="utf-8", errors="replace")
    return AtomicWindowsPopen(argv, **options)


def is_atomic_windows_process(process: Any) -> bool:
    return bool(getattr(process, "_agency_atomic_windows_process", False))


def claim_atomic_windows_job(process: Any) -> WindowsJob | None:
    job = getattr(process, "_agency_windows_job", None)
    if isinstance(job, WindowsJob):
        return job
    return None


def release_atomic_windows_job(process: Any, job: WindowsJob) -> None:
    """Detach source ownership only after the destination durably stores ``job``."""

    if getattr(process, "_agency_windows_job", None) is job:
        process._agency_windows_job = None


def resume_atomic_windows_process(process: Any) -> bool:
    thread = getattr(process, "_agency_primary_thread", None)
    if not isinstance(thread, _PrimaryThread):
        return False
    try:
        return thread.resume()
    finally:
        if getattr(process, "_agency_primary_thread", None) is thread:
            process._agency_primary_thread = None


def close_atomic_windows_process_resources(process: Any) -> None:
    thread = getattr(process, "_agency_primary_thread", None)
    if isinstance(thread, _PrimaryThread):
        thread.close()
        process._agency_primary_thread = None
    job = getattr(process, "_agency_windows_job", None)
    if isinstance(job, WindowsJob):
        job.close()
        process._agency_windows_job = None


__all__ = [
    "AtomicWindowsPopen",
    "claim_atomic_windows_job",
    "close_atomic_windows_process_resources",
    "is_atomic_windows_process",
    "release_atomic_windows_job",
    "resume_atomic_windows_process",
    "spawn_atomic_windows_process",
]
