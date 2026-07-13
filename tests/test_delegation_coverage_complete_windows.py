"""Windows Job Object and suspended-process fallback contracts."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.delegation import backend_windows


class _Function:
    def __init__(self, implementation: Callable[..., Any]) -> None:
        self.implementation = implementation
        self.argtypes: list[Any] = []
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.implementation(*args)


class _JobKernel:
    def __init__(
        self,
        *,
        handle: int = 123,
        configured: bool = True,
        assigned: bool = True,
        query: bool = True,
    ) -> None:
        self.closed: list[Any] = []
        self.CreateJobObjectW = _Function(lambda *_args: handle)
        self.SetInformationJobObject = _Function(lambda *_args: configured)
        self.AssignProcessToJobObject = _Function(lambda *_args: assigned)
        self.QueryInformationJobObject = _Function(lambda *_args: query)
        self.TerminateJobObject = _Function(lambda *_args: True)
        self.CloseHandle = _Function(lambda value: self.closed.append(value) or True)


def test_windows_job_handles_query_failure_empty_termination_and_close() -> None:
    import ctypes

    kernel = _JobKernel(query=False)

    class Accounting(ctypes.Structure):
        _fields_ = [("ActiveProcesses", ctypes.c_ulong)]

    job = backend_windows.WindowsJob(123, kernel, Accounting)
    assert job.active_processes() is None

    empty = backend_windows.WindowsJob(None, kernel, Accounting)
    assert empty.terminate() is False
    empty.close()
    assert kernel.closed == []

    job.close()
    assert kernel.closed == [123]
    job.close()
    assert kernel.closed == [123]


def test_create_windows_job_returns_none_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend_windows.os, "name", "posix")
    assert backend_windows.create_windows_job(SimpleNamespace()) is None


@pytest.mark.parametrize(
    ("kernel", "closed"),
    [
        (_JobKernel(handle=0), []),
        (_JobKernel(configured=False), [123]),
        (_JobKernel(assigned=False), [123]),
    ],
)
def test_create_windows_job_closes_unassigned_native_handle(
    monkeypatch: pytest.MonkeyPatch,
    kernel: _JobKernel,
    closed: list[int],
) -> None:
    import ctypes

    monkeypatch.setattr(backend_windows.os, "name", "nt")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    result = backend_windows.create_windows_job(SimpleNamespace(_handle=456))

    assert result is None
    assert kernel.closed == closed


def test_create_windows_job_closes_handle_after_native_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ctypes

    kernel = _JobKernel()
    kernel.SetInformationJobObject = _Function(
        lambda *_args: (_ for _ in ()).throw(OSError("configuration failed"))
    )
    monkeypatch.setattr(backend_windows.os, "name", "nt")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    assert backend_windows.create_windows_job(SimpleNamespace(_handle=456)) is None
    assert kernel.closed == [123]


class _ThreadKernel:
    def __init__(
        self,
        *,
        process_id: int,
        snapshot: int = 123,
        thread: int = 456,
        resume_result: int = 0,
    ) -> None:
        self.process_id = process_id
        self.closed: list[int] = []
        self.CreateToolhelp32Snapshot = _Function(lambda *_args: snapshot)

        def first(_snapshot: Any, entry_pointer: Any) -> bool:
            entry_pointer._obj.th32OwnerProcessID = process_id
            entry_pointer._obj.th32ThreadID = 7
            return True

        self.Thread32First = _Function(first)
        self.Thread32Next = _Function(lambda *_args: False)
        self.OpenThread = _Function(lambda *_args: thread)
        self.ResumeThread = _Function(lambda *_args: resume_result)
        self.CloseHandle = _Function(lambda value: self.closed.append(int(value)) or True)


def test_resume_windows_process_returns_true_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backend_windows.os, "name", "posix")
    assert backend_windows.resume_windows_process(10) is True


@pytest.mark.parametrize(
    ("kernel", "expected_closed"),
    [
        (_ThreadKernel(process_id=10, snapshot=0), []),
        (_ThreadKernel(process_id=10, thread=0), [123]),
        (_ThreadKernel(process_id=10, resume_result=0xFFFFFFFF), [456, 123]),
    ],
)
def test_resume_windows_process_fails_closed_for_native_thread_errors(
    monkeypatch: pytest.MonkeyPatch,
    kernel: _ThreadKernel,
    expected_closed: list[int],
) -> None:
    import ctypes

    monkeypatch.setattr(backend_windows.os, "name", "nt")
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    assert backend_windows.resume_windows_process(10) is False
    assert kernel.closed == expected_closed


def test_resume_windows_process_normalizes_native_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ctypes

    monkeypatch.setattr(backend_windows.os, "name", "nt")
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("native unavailable")),
        raising=False,
    )
    assert backend_windows.resume_windows_process(10) is False
