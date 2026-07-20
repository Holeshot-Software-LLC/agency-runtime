"""Fault-injection contracts for atomic Windows process creation."""

from __future__ import annotations

import gc
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import owned_process_windows_atomic as atomic
from agency_runtime.core.owned_process_windows import WindowsJob


class _Kernel:
    def __init__(self) -> None:
        self.job_handle = 700
        self.configure_job = True
        self.attribute_size = 256
        self.initialize_attributes = True
        self.update_results = [True, True]
        self.create_process = True
        self.created_process_handle = 701
        self.created_thread_handle = 702
        self.created_process_id = 703
        self.resume_result = 1
        self.closed: list[int] = []
        self.terminated: list[int] = []
        self.deleted_attributes = 0
        self.updated_attributes: list[int] = []

    def CreateJobObjectW(self, *_args: Any) -> int:
        return self.job_handle

    def SetInformationJobObject(self, *_args: Any) -> bool:
        return self.configure_job

    def QueryInformationJobObject(self, *_args: Any) -> bool:
        return True

    def TerminateJobObject(self, handle: Any, *_args: Any) -> bool:
        self.terminated.append(int(handle))
        return True

    def InitializeProcThreadAttributeList(
        self,
        pointer: Any,
        _count: int,
        _flags: int,
        size_pointer: Any,
    ) -> bool:
        if pointer is None:
            size_pointer._obj.value = self.attribute_size
            return False
        return self.initialize_attributes

    def UpdateProcThreadAttribute(
        self,
        _pointer: Any,
        _flags: int,
        attribute: int,
        *_args: Any,
    ) -> bool:
        self.updated_attributes.append(int(attribute))
        return self.update_results.pop(0)

    def DeleteProcThreadAttributeList(self, _pointer: Any) -> None:
        self.deleted_attributes += 1

    def CreateProcessW(
        self,
        _application: Any,
        _command_line: Any,
        _process_attributes: Any,
        _thread_attributes: Any,
        _inherit_handles: Any,
        _creation_flags: Any,
        _environment: Any,
        _cwd: Any,
        _startup: Any,
        process_information_pointer: Any,
    ) -> bool:
        if self.created_process_handle:
            process_information_pointer._obj.hProcess = self.created_process_handle
        if self.created_thread_handle:
            process_information_pointer._obj.hThread = self.created_thread_handle
        process_information_pointer._obj.dwProcessId = self.created_process_id
        return self.create_process

    def ResumeThread(self, _handle: Any) -> int:
        return self.resume_result

    def CloseHandle(self, handle: Any) -> bool:
        self.closed.append(int(handle))
        return True


class _WrappedHandle:
    def __init__(self, value: int, kernel: _Kernel | None = None) -> None:
        self.value = value
        self.kernel = kernel
        self.closed = False
        self.close_calls = 0

    def Close(self) -> None:
        self.close_calls += 1
        if not self.closed:
            self.closed = True
            if self.kernel is not None:
                self.kernel.CloseHandle(self.value)

    def __int__(self) -> int:
        return self.value


def _job(kernel: _Kernel, handle: int | None = None) -> WindowsJob:
    return WindowsJob(
        kernel.job_handle if handle is None else handle,
        kernel,
        atomic._BasicAccountingInformation,
    )


def _receipt(
    kernel: _Kernel,
    *,
    standard_handles: tuple[Any, ...] = (),
) -> atomic._LaunchReceipt:
    api = atomic._NativeApi(kernel)
    return atomic._LaunchReceipt(
        _WrappedHandle(701, kernel),
        atomic._PrimaryThread(702, api),
        703,
        _job(kernel),
        standard_handles,
    )


def _bare_popen(
    *,
    cls: type[atomic.AtomicWindowsPopen] = atomic.AtomicWindowsPopen,
) -> atomic.AtomicWindowsPopen:
    process = object.__new__(cls)
    process._child_created = False
    process._closed_pipe_fds = []

    def close_pipe_fds(*values: Any) -> None:
        process._closed_pipe_fds.extend(values)
        for handle in (values[0], values[3], values[5]):
            close = getattr(handle, "Close", None)
            if callable(close):
                close()

    process._close_pipe_fds = close_pipe_fds
    process._filter_handle_list = lambda values: values
    return process


def _execute_child(
    process: atomic.AtomicWindowsPopen,
    *,
    args: Any = None,
    executable: Any = None,
    pass_fds: Any = (),
    cwd: Any = None,
    startupinfo: Any = None,
    shell: bool = False,
    include_process_group: bool = True,
    pipes: tuple[Any, Any, Any, Any, Any, Any] = (10, 11, 12, 13, 14, 15),
) -> None:
    application = os.path.abspath(sys.executable)
    arguments = [
        [application, "-V"] if args is None else args,
        application if executable is None else executable,
        None,
        True,
        pass_fds,
        cwd,
        {},
        startupinfo,
        0,
        shell,
        *pipes,
        True,
        None,
        None,
        None,
        -1,
        False,
    ]
    if include_process_group:
        arguments.append(-1)
    atomic.AtomicWindowsPopen._execute_child(process, *arguments)


def test_native_platform_guard_and_error_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_IS_WINDOWS", False)
    with pytest.raises(OSError, match="unavailable"):
        atomic._native_api()

    monkeypatch.setattr(atomic.ctypes, "get_last_error", lambda: 5, raising=False)
    monkeypatch.setattr(
        atomic.ctypes,
        "FormatError",
        lambda _error: " access denied ",
        raising=False,
    )
    error = atomic._native_error("operation failed")
    assert error.errno == 5
    assert "operation failed: access denied" in str(error)

    monkeypatch.setattr(atomic.ctypes, "FormatError", lambda _error: "")
    assert "Windows error" in str(atomic._native_error("operation failed"))


def test_native_api_configures_the_complete_kernel_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    function_names = (
        "CreateJobObjectW",
        "SetInformationJobObject",
        "QueryInformationJobObject",
        "TerminateJobObject",
        "InitializeProcThreadAttributeList",
        "UpdateProcThreadAttribute",
        "DeleteProcThreadAttributeList",
        "CreateProcessW",
        "ResumeThread",
        "CloseHandle",
    )
    kernel = SimpleNamespace(
        **{name: SimpleNamespace() for name in function_names},
    )
    observed: dict[str, Any] = {}

    def load_library(name: str, *, use_last_error: bool) -> Any:
        observed.update(name=name, use_last_error=use_last_error)
        return kernel

    monkeypatch.setattr(atomic, "_IS_WINDOWS", True)
    monkeypatch.setattr(atomic.ctypes, "WinDLL", load_library, raising=False)

    api = atomic._native_api()

    assert api.kernel32 is kernel
    assert observed == {"name": "kernel32", "use_last_error": True}
    assert kernel.CreateJobObjectW.restype._kernel32 is kernel
    for name in function_names:
        function = getattr(kernel, name)
        assert hasattr(function, "argtypes")
        assert hasattr(function, "restype")


def test_create_job_fails_closed_and_releases_partial_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_native_error", lambda message: OSError(message))
    kernel = _Kernel()
    kernel.job_handle = 0
    with pytest.raises(OSError, match="create Windows Job"):
        atomic._create_job(atomic._NativeApi(kernel))

    kernel.job_handle = 700
    kernel.configure_job = False
    with pytest.raises(OSError, match="configure Windows Job"):
        atomic._create_job(atomic._NativeApi(kernel))
    assert kernel.closed == [700]

    kernel.closed.clear()
    kernel.configure_job = True
    job = atomic._create_job(atomic._NativeApi(kernel))
    assert job.native_handle == 700
    job.close()
    assert kernel.closed == [700]


def test_owned_job_result_and_wrapper_return_interruption_close_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _AdoptionAbort(BaseException):
        pass

    kernel = _Kernel()
    result_type = type(
        "_TestOwnedJobResult",
        (atomic._OwnedJobHandleResult,),
        {"_kernel32": kernel},
    )
    result = result_type(700)
    kernel.CreateJobObjectW = lambda *_args: result  # type: ignore[method-assign]
    real_windows_job = atomic.WindowsJob

    def interrupted_wrapper(*args: Any) -> WindowsJob:
        job = real_windows_job(*args)
        try:
            return job
        finally:
            raise _AdoptionAbort

    monkeypatch.setattr(atomic, "WindowsJob", interrupted_wrapper)
    with pytest.raises(_AdoptionAbort):
        atomic._create_job(atomic._NativeApi(kernel))
    gc.collect()

    assert int(result) == 0
    assert kernel.closed == [700]
    result.close_owned_handle()
    assert kernel.closed == [700]


def test_creation_attributes_validate_and_release_every_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_native_error", lambda message: OSError(message))
    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    job = _job(kernel)

    with pytest.raises(OSError, match="explicit standard handles"):
        atomic._creation_attributes(api, inherited_handles=[], job=job)

    kernel.attribute_size = 0
    with pytest.raises(OSError, match="attribute sizing"):
        atomic._creation_attributes(api, inherited_handles=[10], job=job)

    kernel.attribute_size = 256
    kernel.initialize_attributes = False
    with pytest.raises(OSError, match="attribute initialization"):
        atomic._creation_attributes(api, inherited_handles=[10], job=job)

    kernel.initialize_attributes = True
    kernel.update_results = [False]
    with pytest.raises(OSError, match="standard-handle attribute"):
        atomic._creation_attributes(api, inherited_handles=[10], job=job)
    assert kernel.deleted_attributes == 1

    kernel.update_results = [True, False]
    with pytest.raises(OSError, match="Job-list attribute"):
        atomic._creation_attributes(api, inherited_handles=[10], job=job)
    assert kernel.deleted_attributes == 2

    kernel.update_results = [True, True]
    attributes = atomic._creation_attributes(api, inherited_handles=[10, 11], job=job)
    assert kernel.updated_attributes[-2:] == [
        atomic._PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
        atomic._PROC_THREAD_ATTRIBUTE_JOB_LIST,
    ]
    attributes.close()
    attributes.close()
    assert kernel.deleted_attributes == 3


def test_creation_attributes_own_native_initialization_and_return_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _InitializationAbort(BaseException):
        pass

    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    job = _job(kernel)
    initialize = kernel.InitializeProcThreadAttributeList

    def interrupted_initialize(*args: Any) -> bool:
        result = initialize(*args)
        if args[0] is not None:
            raise _InitializationAbort
        return result

    kernel.InitializeProcThreadAttributeList = interrupted_initialize  # type: ignore[method-assign]
    with pytest.raises(_InitializationAbort):
        atomic._creation_attributes(api, inherited_handles=[10], job=job)
    assert kernel.deleted_attributes == 1

    kernel.InitializeProcThreadAttributeList = initialize  # type: ignore[method-assign]

    def interrupted_return() -> atomic._CreationAttributes:
        try:
            return atomic._creation_attributes(api, inherited_handles=[10], job=job)
        finally:
            raise _InitializationAbort

    with pytest.raises(_InitializationAbort):
        interrupted_return()
    gc.collect()
    assert kernel.deleted_attributes == 2

    kernel.update_results = [True, True]
    attributes = atomic._creation_attributes(api, inherited_handles=[10], job=job)

    def delete_then_interrupt(_pointer: Any) -> None:
        kernel.deleted_attributes += 1
        raise _InitializationAbort

    monkeypatch.setattr(kernel, "DeleteProcThreadAttributeList", delete_then_interrupt)
    with pytest.raises(_InitializationAbort):
        attributes.close()
    attributes.close()
    assert kernel.deleted_attributes == 3


def test_process_information_shared_owners_close_attempt_all_and_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CloseAbort(BaseException):
        pass

    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    information = atomic._OwnedProcessInformation(api)
    information.hProcess = 701
    information.hThread = 702

    def close(handle: Any) -> bool:
        value = int(handle)
        assert information.thread_handle == 0 if value == 702 else information.process_handle == 0
        kernel.closed.append(value)
        if value == 702:
            raise _CloseAbort
        return True

    monkeypatch.setattr(kernel, "CloseHandle", close)
    with pytest.raises(_CloseAbort):
        information.close()
    information.close()

    assert kernel.closed == [702, 701]
    assert information.thread_handle == 0
    assert information.process_handle == 0

    for thread_raises in (False, True):
        other_kernel = _Kernel()
        other_information = atomic._OwnedProcessInformation(atomic._NativeApi(other_kernel))
        other_information.hProcess = 801
        other_information.hThread = 802

        def close_other(
            handle: Any,
            *,
            fail_thread: bool = thread_raises,
            target_kernel: _Kernel = other_kernel,
        ) -> bool:
            value = int(handle)
            target_kernel.closed.append(value)
            if value == 801 or fail_thread:
                raise _CloseAbort
            return True

        monkeypatch.setattr(other_kernel, "CloseHandle", close_other)
        with pytest.raises(_CloseAbort):
            other_information.close()
        assert other_kernel.closed == [802, 801]


def test_process_handle_adoption_return_interruption_and_detach_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _AdoptionAbort(BaseException):
        pass

    kernel = _Kernel()
    information = atomic._OwnedProcessInformation(atomic._NativeApi(kernel))
    information.hProcess = 701
    handle_type = atomic._process_handle_type(information)

    def interrupted_return() -> Any:
        handle = handle_type(information.process_handle)
        try:
            return handle
        finally:
            raise _AdoptionAbort

    with pytest.raises(_AdoptionAbort):
        interrupted_return()
    gc.collect()
    assert kernel.closed == [701]
    information.close_process()
    assert kernel.closed == [701]

    detached_information = atomic._OwnedProcessInformation(atomic._NativeApi(kernel))
    detached_information.hProcess = 703
    detached = atomic._process_handle_type(detached_information)(703)
    assert detached.Detach() == 703
    assert detached_information.process_handle == 0
    with pytest.raises(ValueError, match="already closed"):
        detached.Detach()
    detached.Close()
    assert kernel.closed == [701]

    empty_information = atomic._OwnedProcessInformation(atomic._NativeApi(kernel))
    empty = atomic._process_handle_type(empty_information)(0)
    with pytest.raises(ValueError, match="already closed"):
        empty.Detach()
    empty.Close()


def test_create_process_return_interruption_closes_native_outputs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CreationAbort(BaseException):
        pass

    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    monkeypatch.setattr(atomic, "_native_api", lambda: api)
    create_process = kernel.CreateProcessW

    def interrupted_create(*args: Any) -> bool:
        create_process(*args)
        raise _CreationAbort

    kernel.CreateProcessW = interrupted_create  # type: ignore[method-assign]
    with pytest.raises(_CreationAbort):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )

    assert kernel.terminated == [700]
    assert kernel.closed == [702, 701, 700]
    assert kernel.deleted_attributes == 1
    assert all(kernel.closed.count(handle) == 1 for handle in kernel.closed)


def test_launch_rejects_incomplete_native_handles_and_constructor_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    monkeypatch.setattr(atomic, "_native_api", lambda: api)
    kernel.created_thread_handle = 0

    with pytest.raises(OSError, match="incomplete handles"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.closed == [701, 700]
    assert kernel.terminated == [700]

    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    monkeypatch.setattr(atomic, "_native_api", lambda: api)
    monkeypatch.setattr(
        atomic,
        "_PrimaryThread",
        lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(KeyboardInterrupt):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.closed == [700]
    assert kernel.terminated == [700]


@pytest.mark.parametrize(
    "environment",
    [
        {1: "value"},
        {"NAME": 1},
    ],
)
def test_environment_buffer_rejects_non_text_before_sorting(environment: Any) -> None:
    with pytest.raises(TypeError, match="must contain strings"):
        atomic._environment_buffer(environment)


@pytest.mark.parametrize(
    "environment",
    [
        {"": "value"},
        {"=": "value"},
        {"A=B": "value"},
        {"A\x00B": "value"},
        {"NAME": "bad\x00value"},
    ],
)
def test_environment_buffer_rejects_invalid_items(environment: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="invalid item"):
        atomic._environment_buffer(environment)


def test_environment_buffer_is_sorted_and_rejects_case_duplicates() -> None:
    assert atomic._environment_buffer(None) is None
    buffer = atomic._environment_buffer({"z": "last", "A": "first"})
    assert buffer[:] == "A=first\x00z=last\x00\x00"
    with pytest.raises(ValueError, match="duplicate keys"):
        atomic._environment_buffer({"Path": "one", "PATH": "two"})


def test_launch_receipt_and_create_failure_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_native_error", lambda message: OSError(message))
    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    monkeypatch.setattr(atomic, "_native_api", lambda: api)

    receipt = atomic._launch(
        application=os.path.abspath(sys.executable),
        command_line="python -V",
        cwd=None,
        environment=None,
        inherited_handles=[10, 11, 12],
        stdin_handle=10,
        stdout_handle=11,
        stderr_handle=12,
        creation_flags=0,
    )
    assert int(receipt.process_handle) == 701
    assert receipt.primary_thread.native_handle == 702
    assert receipt.process_id == 703
    assert kernel.deleted_attributes == 1
    receipt.close()
    receipt.close()
    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701]

    kernel.closed.clear()
    kernel.terminated.clear()
    kernel.create_process = False
    kernel.update_results = [True, True]
    with pytest.raises(OSError, match="process creation"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=os.path.abspath(os.curdir),
            environment={"NAME": "value"},
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.closed == [702, 701, 700]
    assert kernel.terminated == [700]

    kernel.closed.clear()
    kernel.terminated.clear()
    kernel.created_process_handle = 0
    kernel.created_thread_handle = 0
    kernel.update_results = [True, True]
    with pytest.raises(OSError, match="process creation"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.closed == [700]
    assert kernel.terminated == [700]

    kernel.closed.clear()
    kernel.terminated.clear()
    monkeypatch.setattr(
        atomic,
        "_creation_attributes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("attributes")),
    )
    with pytest.raises(OSError, match="attributes"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.closed == [700]
    assert kernel.terminated == [700]


def test_launch_receipt_disarm_is_idempotent_and_transfers_without_closing() -> None:
    kernel = _Kernel()
    receipt = _receipt(kernel)
    process_handle = receipt.process_handle
    primary_thread = receipt.primary_thread
    job = receipt.job

    receipt.disarm()
    receipt.disarm()
    receipt.close()

    assert receipt.process_handle is None
    assert receipt.primary_thread is None
    assert receipt.job is None
    assert kernel.closed == []
    assert kernel.terminated == []
    primary_thread.close()
    job.close()
    process_handle.Close()
    assert kernel.closed == [702, 700, 701]


def test_launch_receipt_closes_every_owner_when_cleanup_raises() -> None:
    class _CleanupAbort(BaseException):
        pass

    class _RaisingHandle(_WrappedHandle):
        def Close(self) -> None:
            super().Close()
            raise _CleanupAbort("standard handle")

    kernel = _Kernel()
    process_handle = _WrappedHandle(701, kernel)
    primary_thread = atomic._PrimaryThread(702, atomic._NativeApi(kernel))
    job = _job(kernel)
    standard_handle = _RaisingHandle(704, kernel)
    job.terminate = lambda: (_ for _ in ()).throw(_CleanupAbort("terminate"))
    receipt = atomic._LaunchReceipt(
        process_handle,
        primary_thread,
        703,
        job,
        (standard_handle, standard_handle, object()),
    )

    with pytest.raises(_CleanupAbort, match="terminate"):
        receipt.close()
    receipt.close()

    assert kernel.closed == [700, 702, 701, 704]
    assert process_handle.close_calls == 1
    assert standard_handle.close_calls == 1


def test_launch_receipt_without_optional_owners_closes_cleanly() -> None:
    receipt = atomic._LaunchReceipt(None, None, 703, None)

    receipt.close()

    assert receipt._armed is False


def test_launch_closes_wrapped_owners_if_post_creation_transfer_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_native_error", lambda message: OSError(message))
    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    monkeypatch.setattr(atomic, "_native_api", lambda: api)

    original_process_handle_type = atomic._process_handle_type
    monkeypatch.setattr(
        atomic,
        "_process_handle_type",
        lambda _information: lambda _value: (_ for _ in ()).throw(OSError("process wrapper")),
    )
    with pytest.raises(OSError, match="process wrapper"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.terminated == [700]
    assert kernel.closed == [702, 701, 700]

    kernel.closed.clear()
    kernel.terminated.clear()
    kernel.update_results = [True, True]
    monkeypatch.setattr(
        atomic,
        "_process_handle_type",
        original_process_handle_type,
    )
    monkeypatch.setattr(
        atomic,
        "_LaunchReceipt",
        lambda *_args: (_ for _ in ()).throw(OSError("receipt wrapper")),
    )
    with pytest.raises(OSError, match="receipt wrapper"):
        atomic._launch(
            application=os.path.abspath(sys.executable),
            command_line="python -V",
            cwd=None,
            environment=None,
            inherited_handles=[10, 11, 12],
            stdin_handle=10,
            stdout_handle=11,
            stderr_handle=12,
            creation_flags=0,
        )
    assert kernel.terminated == [700]
    assert kernel.closed == [702, 701, 700]


def test_execute_child_call_to_store_abort_closes_launch_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _CallToStoreAbort(BaseException):
        pass

    kernel = _Kernel()
    standard_handles = (
        _WrappedHandle(710, kernel),
        _WrappedHandle(711, kernel),
        _WrappedHandle(712, kernel),
    )

    def interrupted_launch(**_kwargs: Any) -> atomic._LaunchReceipt:
        receipt = _receipt(kernel, standard_handles=standard_handles)
        try:
            return receipt
        finally:
            raise _CallToStoreAbort

    monkeypatch.setattr(atomic, "_launch", interrupted_launch)
    process = _bare_popen()

    with pytest.raises(_CallToStoreAbort):
        _execute_child(process)

    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701, 710, 711, 712]
    assert all(kernel.closed.count(value) == 1 for value in kernel.closed)


@pytest.mark.parametrize(
    ("boundary", "after_store"),
    [
        ("_agency_windows_job", False),
        ("_agency_windows_job", True),
        ("_agency_primary_thread", False),
        ("_agency_primary_thread", True),
        ("_handle", False),
        ("_handle", True),
        ("pid", False),
        ("pid", True),
        ("_child_created", False),
        ("_child_created", True),
    ],
)
def test_execute_child_baseexception_at_every_receipt_transfer_boundary(
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    after_store: bool,
) -> None:
    class _TransferAbort(BaseException):
        pass

    kernel = _Kernel()
    standard_handles = (
        _WrappedHandle(710, kernel),
        _WrappedHandle(711, kernel),
        _WrappedHandle(712, kernel),
    )
    receipt = _receipt(kernel, standard_handles=standard_handles)
    process_handle = receipt.process_handle
    primary_thread = receipt.primary_thread
    job = receipt.job

    class _FaultingPopen(atomic.AtomicWindowsPopen):
        _faulted = False

        def __setattr__(self, name: str, value: Any) -> None:
            is_transfer = (
                (name == "_agency_windows_job" and value is job)
                or (name == "_agency_primary_thread" and value is primary_thread)
                or (name == "_handle" and value is process_handle)
                or (name == "pid" and value == 703)
                or (name == "_child_created" and value is True)
            )
            if name == boundary and is_transfer and not self._faulted:
                object.__setattr__(self, "_faulted", True)
                if not after_store:
                    raise _TransferAbort(boundary)
                super().__setattr__(name, value)
                raise _TransferAbort(boundary)
            super().__setattr__(name, value)

    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    process = _bare_popen(cls=_FaultingPopen)

    with pytest.raises(_TransferAbort, match=boundary):
        _execute_child(process)

    assert receipt._armed is False
    assert kernel.terminated == [700]
    assert sorted(kernel.closed) == [700, 701, 702, 710, 711, 712]
    assert all(kernel.closed.count(value) == 1 for value in kernel.closed)
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None
    assert process._handle is None
    assert process._child_created is False


def test_execute_child_baseexception_after_receipt_disarm_closes_popen_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _DisarmAbort(BaseException):
        pass

    kernel = _Kernel()
    receipt = _receipt(kernel)
    original_disarm = atomic._LaunchReceipt.disarm

    def interrupted_disarm(candidate: atomic._LaunchReceipt) -> None:
        original_disarm(candidate)
        raise _DisarmAbort

    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    monkeypatch.setattr(atomic._LaunchReceipt, "disarm", interrupted_disarm)
    process = _bare_popen()

    with pytest.raises(_DisarmAbort):
        _execute_child(process)

    assert receipt._armed is False
    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701]
    assert all(kernel.closed.count(value) == 1 for value in kernel.closed)
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None
    assert process._handle is None
    assert process._child_created is False


def test_execute_child_pipe_close_failure_keeps_receipt_armed_until_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _Kernel()
    receipt = _receipt(kernel)
    process = _bare_popen()
    calls = 0

    def close_pipe_fds(*_values: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("pipe close")

    process._close_pipe_fds = close_pipe_fds
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)

    with pytest.raises(OSError, match="pipe close"):
        _execute_child(process)

    assert calls == 2
    assert receipt._armed is False
    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701]
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None
    assert process._handle is None
    assert process._child_created is False


def test_execute_child_preserves_validation_error_when_pipe_cleanup_fails() -> None:
    process = _bare_popen()
    calls = 0

    def close_pipe_fds(*_values: Any) -> None:
        nonlocal calls
        calls += 1
        raise OSError("cleanup-close")

    process._close_pipe_fds = close_pipe_fds
    with pytest.raises(ValueError, match="unsupported options") as caught:
        _execute_child(process, pass_fds=(1,))

    assert calls == 1
    assert any("cleanup-close" in note for note in caught.value.__notes__)


def test_execute_child_preserves_keyboard_interrupt_when_pipe_cleanup_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    primary = KeyboardInterrupt("stop")
    process = _bare_popen()
    process._close_pipe_fds = lambda *_values: (_ for _ in ()).throw(OSError("cleanup-close"))
    monkeypatch.setattr(
        atomic,
        "_launch",
        lambda **_kwargs: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(KeyboardInterrupt) as caught:
        _execute_child(process)

    assert caught.value is primary
    assert any("cleanup-close" in note for note in primary.__notes__)


def test_execute_child_persistent_pipe_retry_preserves_first_cleanup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _Kernel()
    receipt = _receipt(kernel)
    process = _bare_popen()
    failures = iter((OSError("first-close"), OSError("retry-close")))
    calls = 0

    def close_pipe_fds(*_values: Any) -> None:
        nonlocal calls
        calls += 1
        raise next(failures)

    process._close_pipe_fds = close_pipe_fds
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)

    with pytest.raises(OSError, match="first-close") as caught:
        _execute_child(process)

    assert calls == 2
    assert any("retry-close" in note for note in caught.value.__notes__)
    assert receipt._armed is False
    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701]


def test_pipe_cleanup_failure_raises_when_no_primary_error() -> None:
    process = SimpleNamespace(
        _close_pipe_fds=lambda *_values: (_ for _ in ()).throw(SystemExit("cleanup"))
    )

    with pytest.raises(SystemExit, match="cleanup"):
        atomic._close_pipe_fds_preserving_primary(
            process,
            (10, 11, 12, 13, 14, 15),
            None,
        )


def test_primary_thread_is_single_use_and_closes_on_all_results() -> None:
    kernel = _Kernel()
    api = atomic._NativeApi(kernel)
    assert atomic._PrimaryThread(0, api).resume() is False

    thread = atomic._PrimaryThread(702, api)
    assert thread.resume() is True
    thread.close()
    assert kernel.closed == [702]

    kernel.resume_result = 0
    assert atomic._PrimaryThread(703, api).resume() is False
    assert kernel.closed == [702, 703]


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"pass_fds": (1,)}, "unsupported options"),
        ({"startupinfo": object()}, "unsupported options"),
        ({"shell": True}, "unsupported options"),
        ({"args": []}, "invalid item"),
        ({"args": [""]}, "invalid item"),
        ({"args": ["bad\x00argument"]}, "invalid item"),
        ({"args": ["relative.exe"], "executable": "relative.exe"}, "absolute path"),
        ({"cwd": ""}, "cwd must be an absolute path"),
        ({"cwd": "relative"}, "cwd must be an absolute path"),
        ({"cwd": "bad\x00cwd"}, "cwd must be an absolute path"),
    ],
)
def test_execute_child_rejects_ambiguous_launch_inputs(
    options: dict[str, Any],
    message: str,
) -> None:
    process = _bare_popen()
    with pytest.raises(ValueError, match=message):
        _execute_child(process, **options)
    assert process._closed_pipe_fds == [10, 11, 12, 13, 14, 15]


def test_execute_child_transfers_receipt_and_public_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _Kernel()
    pipes = tuple(_WrappedHandle(value, kernel) for value in range(710, 716))
    receipt = _receipt(
        kernel,
        standard_handles=(pipes[0], pipes[3], pipes[5]),
    )
    job_owner = receipt.job
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    process = _bare_popen()

    _execute_child(process, cwd=Path.cwd(), pipes=pipes)

    assert process.pid == 703
    assert process._child_created is True
    assert atomic.is_atomic_windows_process(process) is True
    job = atomic.claim_atomic_windows_job(process)
    assert job is job_owner
    assert atomic.claim_atomic_windows_job(process) is job
    assert atomic.resume_atomic_windows_process(process) is True
    assert atomic.resume_atomic_windows_process(process) is False
    assert kernel.closed == [710, 713, 715, 702]
    atomic.release_atomic_windows_job(process, job)
    assert atomic.claim_atomic_windows_job(process) is None
    job.close()
    process._handle.Close()
    assert kernel.closed == [710, 713, 715, 702, 700, 701]
    process._child_created = False


def test_execute_child_accepts_python_310_call_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _Kernel()
    receipt = _receipt(kernel)
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    process = _bare_popen()

    _execute_child(process, include_process_group=False)

    assert process.pid == 703
    atomic.close_atomic_windows_process_resources(process)
    process._handle.Close()
    process._child_created = False


@pytest.mark.parametrize("missing_owner", ["process", "thread", "job"])
def test_execute_child_closes_incomplete_receipt(
    monkeypatch: pytest.MonkeyPatch,
    missing_owner: str,
) -> None:
    kernel = _Kernel()
    process_handle = None if missing_owner == "process" else _WrappedHandle(701, kernel)
    primary_thread = (
        None if missing_owner == "thread" else atomic._PrimaryThread(702, atomic._NativeApi(kernel))
    )
    job = None if missing_owner == "job" else _job(kernel)
    receipt = atomic._LaunchReceipt(process_handle, primary_thread, 703, job)
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    process = _bare_popen()

    with pytest.raises(OSError, match="receipt is incomplete"):
        _execute_child(process)

    expected_closed = {
        "process": [700, 702],
        "thread": [700, 701],
        "job": [702, 701],
    }[missing_owner]
    assert kernel.closed == expected_closed
    assert kernel.terminated == ([] if missing_owner == "job" else [700])


def test_execute_child_closes_wrapped_receipt_when_transfer_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FailPid(atomic.AtomicWindowsPopen):
        def __setattr__(self, name: str, value: Any) -> None:
            if name == "pid":
                raise RuntimeError("pid transfer")
            super().__setattr__(name, value)

    kernel = _Kernel()
    receipt = _receipt(kernel)
    wrapped = receipt.process_handle
    monkeypatch.setattr(atomic, "_launch", lambda **_kwargs: receipt)
    process = _bare_popen(cls=_FailPid)

    with pytest.raises(RuntimeError, match="pid transfer"):
        _execute_child(process)

    assert wrapped.closed is True
    assert kernel.terminated == [700]
    assert kernel.closed == [700, 702, 701]
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None


def test_spawn_options_resource_cleanup_and_abandoned_finalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(atomic, "_IS_WINDOWS", False)
    with pytest.raises(OSError, match="unavailable"):
        atomic.spawn_atomic_windows_process(
            ["C:\\tool.exe"],
            cwd=None,
            env={},
            stdin=None,
            text=False,
        )

    observed: dict[str, Any] = {}
    sentinel = object()
    atomic_type = atomic.AtomicWindowsPopen
    monkeypatch.setattr(atomic, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        atomic,
        "AtomicWindowsPopen",
        lambda argv, **options: observed.update(argv=argv, options=options) or sentinel,
    )
    assert (
        atomic.spawn_atomic_windows_process(
            ["C:\\tool.exe", "argument"],
            cwd="C:\\work",
            env={"NAME": "value"},
            stdin=10,
            text=True,
        )
        is sentinel
    )
    assert observed["options"]["executable"] == "C:\\tool.exe"
    assert observed["options"]["text"] is True
    assert observed["options"]["encoding"] == "utf-8"

    observed.clear()
    assert (
        atomic.spawn_atomic_windows_process(
            ["C:\\tool.exe"],
            cwd=None,
            env={},
            stdin=None,
            text=False,
        )
        is sentinel
    )
    assert "text" not in observed["options"]

    kernel = _Kernel()
    process = _bare_popen()
    process._agency_windows_job = _job(kernel)
    process._agency_primary_thread = atomic._PrimaryThread(702, atomic._NativeApi(kernel))
    process.__del__()
    assert kernel.closed == [702, 700]
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None

    process_without_popen_state = object.__new__(atomic_type)
    process_without_popen_state.__del__()


def test_finalizer_suppresses_native_cleanup_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _bare_popen()
    monkeypatch.setattr(
        atomic,
        "close_atomic_windows_process_resources",
        lambda _process: (_ for _ in ()).throw(OSError("close")),
    )
    process.__del__()


def test_resource_helpers_ignore_foreign_values_and_close_owned_values() -> None:
    process = SimpleNamespace(
        _agency_windows_job=object(),
        _agency_primary_thread=object(),
    )
    assert atomic.is_atomic_windows_process(process) is False
    assert atomic.claim_atomic_windows_job(process) is None
    assert atomic.resume_atomic_windows_process(process) is False
    atomic.close_atomic_windows_process_resources(process)

    kernel = _Kernel()
    process._agency_windows_job = _job(kernel)
    process._agency_primary_thread = atomic._PrimaryThread(
        702,
        atomic._NativeApi(kernel),
    )
    atomic.close_atomic_windows_process_resources(process)
    assert kernel.closed == [702, 700]
    assert process._agency_windows_job is None
    assert process._agency_primary_thread is None
