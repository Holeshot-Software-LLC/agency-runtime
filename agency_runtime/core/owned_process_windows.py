"""Windows Job Object containment for shell-free owned subprocess trees."""

from __future__ import annotations

import os
import subprocess
from contextlib import suppress
from typing import Any

_IS_WINDOWS = os.name == "nt"


class WindowsJob:
    """Small kill-on-close Job Object wrapper; constructed only on Windows."""

    def __init__(self, handle: Any, kernel32: Any, accounting_type: Any) -> None:
        self._handle = handle
        self._kernel32 = kernel32
        self._accounting_type = accounting_type

    @property
    def native_handle(self) -> Any:
        """Return the non-inherited native handle for process-creation attributes."""

        return getattr(self._handle, "native_handle", self._handle)

    def active_processes(self) -> int | None:
        import ctypes

        accounting = self._accounting_type()
        returned = ctypes.c_ulong()
        if not self._kernel32.QueryInformationJobObject(
            self.native_handle,
            1,
            ctypes.byref(accounting),
            ctypes.sizeof(accounting),
            ctypes.byref(returned),
        ):
            return None
        return int(accounting.ActiveProcesses)

    def terminate(self) -> bool:
        if self._handle:
            return bool(self._kernel32.TerminateJobObject(self.native_handle, 1))
        return False

    def close(self) -> None:
        if self._handle:
            handle = self._handle
            self._handle = None
            close_owned_handle = getattr(handle, "close_owned_handle", None)
            if callable(close_owned_handle):
                close_owned_handle()
            else:
                self._kernel32.CloseHandle(handle)

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


def create_windows_job(process: subprocess.Popen[str]) -> WindowsJob | None:
    """Assign a child to a kill-on-close Job Object when native APIs permit."""
    if not _IS_WINDOWS:
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
        job = WindowsJob(handle, kernel32, BasicAccountingInformation)
        handle = None
        return job
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    finally:
        if handle and kernel32 is not None:
            kernel32.CloseHandle(handle)


def resume_windows_process(process_id: int) -> bool:
    """Resume the sole primary thread created by CREATE_SUSPENDED."""
    if not _IS_WINDOWS:
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
        kernel32.GetProcessIdOfThread.argtypes = [wintypes.HANDLE]
        kernel32.GetProcessIdOfThread.restype = wintypes.DWORD
        kernel32.SetLastError.argtypes = [wintypes.DWORD]
        kernel32.SetLastError.restype = None
        kernel32.GetLastError.argtypes = []
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
        invalid_handle = ctypes.c_void_p(-1).value
        if not snapshot or int(snapshot) == invalid_handle:
            return False
        thread_ids: list[int] = []
        try:
            entry = ThreadEntry32()
            entry.dwSize = ctypes.sizeof(entry)
            kernel32.SetLastError(0)
            found = bool(kernel32.Thread32First(snapshot, ctypes.byref(entry)))
            while found:
                if int(entry.th32OwnerProcessID) == process_id:
                    thread_ids.append(int(entry.th32ThreadID))
                kernel32.SetLastError(0)
                found = bool(kernel32.Thread32Next(snapshot, ctypes.byref(entry)))
            enumeration_error = int(kernel32.GetLastError())
        finally:
            kernel32.CloseHandle(snapshot)
        # CREATE_SUSPENDED owns exactly the primary thread's one suspension.
        # Any additional thread was created or injected by another actor. Check
        # the complete snapshot before mutation so failure cannot partially
        # resume a debugger- or endpoint-security-owned thread.
        if enumeration_error != 18 or len(thread_ids) != 1:
            return False
        thread = kernel32.OpenThread(0x0002 | 0x0800, False, thread_ids[0])
        if not thread:
            return False
        try:
            # The snapshot does not pin a TID. Verify the opened handle still
            # belongs to this process before touching a potentially reused ID.
            if int(kernel32.GetProcessIdOfThread(thread)) != process_id:
                return False
            # Zero means containment was established too late; greater than one
            # includes a suspension owned by another actor. Only release the
            # exact count Agency Runtime created.
            return int(kernel32.ResumeThread(thread)) == 1
        finally:
            kernel32.CloseHandle(thread)
    except (AttributeError, OSError, TypeError, ValueError):
        return False


# Compatibility aliases preserve the former private type/function names.
_WindowsJob = WindowsJob
_create_windows_job = create_windows_job
_resume_windows_process = resume_windows_process
