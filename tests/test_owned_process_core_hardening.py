"""Branch-complete contracts for lightweight owned-process internals."""

from __future__ import annotations

import ast
import base64
import ctypes
import errno
import gc
import io
import json
import os
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import owned_process, process_argv
from agency_runtime.core import owned_process_capture as capture
from agency_runtime.core import owned_process_linux as linux
from agency_runtime.core.delegation import backend_process_compat as compat
from agency_runtime.core.delegation import backends
from agency_runtime.core.process_argv import PreparedProcessArgv


def _prepared(*arguments: str) -> PreparedProcessArgv:
    value = PreparedProcessArgv(["tool", *arguments], artifact_paths=("tool",))
    value.executable_identities = (object(),)  # type: ignore[assignment]
    value.frozen_launcher = ("tool",)
    value.frozen_platform = os.name
    return value


def _owned_pipe_pair(read_descriptor: int, write_descriptor: int) -> Any:
    pair = owned_process._OwnedPipePair()
    pair._storage[0] = read_descriptor
    pair._storage[1] = write_descriptor
    return pair


def test_owned_process_kwargs_include_the_explicit_suspended_flag() -> None:
    options = owned_process._owned_process_kwargs(platform_name="nt", suspended=True)
    assert options["creationflags"] & getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)


def test_descriptor_owner_clears_before_close_and_cannot_close_recycled_fd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        linux.DescriptorOwner(-1)

    read_descriptor, write_descriptor = os.pipe()
    owner = linux.DescriptorOwner(read_descriptor)
    real_close = os.close
    recycled: list[int] = []

    def close_and_recycle(descriptor: int) -> None:
        real_close(descriptor)
        replacement = os.open(os.devnull, os.O_RDONLY)
        assert replacement == descriptor
        recycled.append(replacement)

    monkeypatch.setattr(linux.os, "close", close_and_recycle)
    owner.close()
    owner.close()
    assert len(recycled) == 1
    assert os.fstat(recycled[0])
    with pytest.raises(OSError, match="closed"):
        owner.fileno()

    monkeypatch.setattr(linux.os, "close", real_close)
    real_close(recycled[0])
    real_close(write_descriptor)


@pytest.mark.parametrize("after_store", [False, True])
def test_descriptor_process_clear_interruption_never_recloses_owner(
    monkeypatch: pytest.MonkeyPatch,
    after_store: bool,
) -> None:
    class _ClearAbort(BaseException):
        pass

    owner = linux.DescriptorOwner(10)
    closed: list[int] = []

    class Process:
        _agency_supervisor_status_fd: object = owner
        faulted = False

        def __setattr__(self, name: str, value: object) -> None:
            if name == "_agency_supervisor_status_fd" and value is None and not self.faulted:
                object.__setattr__(self, "faulted", True)
                if not after_store:
                    raise _ClearAbort
                object.__setattr__(self, name, value)
                raise _ClearAbort
            object.__setattr__(self, name, value)

    process = Process()
    monkeypatch.setattr(linux.os, "close", closed.append)

    with pytest.raises(_ClearAbort):
        linux.close_status(process)  # type: ignore[arg-type]
    owner.close()
    assert closed == [10]
    object.__setattr__(process, "_agency_supervisor_status_fd", None)


def test_cleanup_retries_go_close_after_pretry_fileno_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FilenoAbort(BaseException):
        pass

    class FaultingOwner(linux.DescriptorOwner):
        faulted = False

        def fileno(self) -> int:
            if not self.faulted:
                self.faulted = True
                raise _FilenoAbort("fileno")
            return super().fileno()

    owner = FaultingOwner(10)
    process = _Process()
    process._agency_supervisor_go_fd = owner
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    closed: list[int] = []
    events: list[str] = []
    monkeypatch.setattr(linux.os, "close", closed.append)
    monkeypatch.setattr(
        owned_process,
        "_terminate_owned_process_tree",
        lambda *_args, **_kwargs: events.append("terminate"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_atomic_windows_process_resources",
        lambda _process: events.append("atomic"),
    )
    monkeypatch.setattr(
        owned_process,
        "_join_owned_process_io",
        lambda *_args: events.append("join"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_process_pipes",
        lambda _process: events.append("pipes"),
    )

    with pytest.raises(_FilenoAbort, match="fileno"):
        owned_process._cleanup_owned_process(state)

    assert closed == [10]
    assert process._agency_supervisor_go_fd is None
    assert events == ["terminate", "atomic", "join", "pipes"]


def test_close_process_pipes_attempts_streams_and_status_after_baseexception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _StreamAbort(BaseException):
        pass

    events: list[str] = []

    class Stream:
        def __init__(self, name: str) -> None:
            self.name = name

        def close(self) -> None:
            events.append(self.name)
            if self.name == "stdin":
                raise _StreamAbort(self.name)

    process = SimpleNamespace(
        stdin=Stream("stdin"),
        stdout=Stream("stdout"),
        stderr=Stream("stderr"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_status",
        lambda _process: events.append("status"),
    )

    with pytest.raises(_StreamAbort, match="stdin"):
        owned_process._close_process_pipes(process)

    assert events == ["stdin", "stdout", "stderr", "status"]

    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_status",
        lambda _process: (_ for _ in ()).throw(_StreamAbort("status")),
    )
    with pytest.raises(_StreamAbort, match="status"):
        owned_process._close_process_pipes(SimpleNamespace(stdin=None, stdout=None, stderr=None))

    foreign = SimpleNamespace(_agency_supervisor_status_fd=object())
    linux._clear_process_descriptor(
        foreign,
        "_agency_supervisor_status_fd",
        object(),
    )
    with pytest.raises(OSError, match="GO gate"):
        linux.release_go(SimpleNamespace(_agency_supervisor_go_fd=None))


@pytest.mark.parametrize("platform_name", ["nt", "posix"])
def test_owned_pipe_pair_native_factory_and_detach_contracts(
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
) -> None:
    class NativePipe:
        def __init__(self) -> None:
            self.argtypes: object = None
            self.restype: object = None

        def __call__(self, storage: Any, *_args: Any) -> int:
            storage[0] = 10
            storage[1] = 11
            return 0

    native = NativePipe()
    runtime = SimpleNamespace(_pipe=native, pipe2=native)
    monkeypatch.setattr(owned_process, "_IS_WINDOWS", platform_name == "nt")
    monkeypatch.setattr(owned_process.ctypes, "CDLL", lambda *_args, **_kwargs: runtime)
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    pair = owned_process._OwnedPipePair.create()
    read_owner = pair.detach_read()
    write_owner = pair.detach_write()
    with pytest.raises(OSError, match="already detached"):
        pair.detach_read()
    pair.close()
    read_owner.close()
    write_owner.close()

    assert closed == [10, 11]
    assert native.argtypes is not None
    assert native.restype is ctypes.c_int


def test_owned_pipe_pair_failure_and_cleanup_are_attempt_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NativePipe:
        argtypes: object = None
        restype: object = None

        def __call__(self, storage: Any, *_args: Any) -> int:
            storage[0] = 10
            storage[1] = 11
            return -1

    native = NativePipe()
    monkeypatch.setattr(owned_process, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        owned_process.ctypes,
        "CDLL",
        lambda *_args, **_kwargs: SimpleNamespace(_pipe=native),
    )
    monkeypatch.setattr(owned_process.ctypes, "get_errno", lambda: errno.EMFILE)
    closed: list[int] = []

    def close(descriptor: int) -> None:
        closed.append(descriptor)
        if descriptor in {10, 20, 21}:
            raise KeyboardInterrupt

    monkeypatch.setattr(owned_process.os, "close", close)
    with pytest.raises(OSError, match=os.strerror(errno.EMFILE)):
        owned_process._OwnedPipePair.create()
    assert closed == [10, 11]

    pair = _owned_pipe_pair(20, 21)
    with pytest.raises(KeyboardInterrupt):
        pair.close()
    assert closed[-2:] == [20, 21]
    pair.close()

    owned_process._close_descriptor_owner(object())
    with pytest.raises(OSError, match="unavailable"):
        owned_process._descriptor_owner_number(object())


@pytest.mark.parametrize("after_store", [False, True])
def test_owned_pipe_detach_interruption_closes_each_end_once(
    monkeypatch: pytest.MonkeyPatch,
    after_store: bool,
) -> None:
    class _DetachAbort(BaseException):
        pass

    class FaultingPair(owned_process._OwnedPipePair):
        faulted = False
        fault_enabled = False

        def __init__(self) -> None:
            super().__init__()
            self.fault_enabled = True

        def __setattr__(self, name: str, value: object) -> None:
            if name == "_read" and value is None and self.fault_enabled and not self.faulted:
                object.__setattr__(self, "faulted", True)
                if not after_store:
                    raise _DetachAbort
                object.__setattr__(self, name, value)
                raise _DetachAbort
            object.__setattr__(self, name, value)

    pair = FaultingPair()
    pair._storage[0] = 10
    pair._storage[1] = 11
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    with pytest.raises(_DetachAbort):
        pair.detach_read()
    pair.close()
    gc.collect()
    assert sorted(closed) == [10, 11]
    assert all(closed.count(descriptor) == 1 for descriptor in closed)


def test_owned_pipe_return_interruption_finalizers_own_both_ends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ReturnAbort(BaseException):
        pass

    pair = _owned_pipe_pair(10, 11)
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: pair),
    )
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    def interrupted_return() -> Any:
        owner = owned_process._OwnedPipePair.create().detach_read()
        try:
            return owner
        finally:
            raise _ReturnAbort

    with pytest.raises(_ReturnAbort):
        interrupted_return()
    pair.close()
    gc.collect()
    assert sorted(closed) == [10, 11]


def test_forbidden_root_helpers_cover_native_relative_and_resolved_paths(
    tmp_path: Path,
) -> None:
    child = tmp_path / "child" / "tool"
    assert process_argv._is_within(str(child), tmp_path) is True

    relative = process_argv._absolute_lexical_path(
        os.path.join("relative", "tool"),
        platform_name=os.name,
    )
    assert os.path.isabs(relative)
    assert relative.endswith(os.path.join("relative", "tool"))

    foreign_platform = "posix" if os.name == "nt" else "nt"
    with pytest.raises(ValueError, match="relative paths require the native platform"):
        process_argv._absolute_lexical_path(
            os.path.join("relative", "tool"),
            platform_name=foreign_platform,
        )


class _Process:
    def __init__(self, *, returncode: int | None = None) -> None:
        self.returncode = returncode
        self.pid = 123
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.stderr = io.BytesIO()
        self.terminated = 0
        self.killed = 0

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated += 1

    def kill(self) -> None:
        self.killed += 1

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            raise subprocess.TimeoutExpired("tool", 1)
        return self.returncode


def test_capture_remaining_branches() -> None:
    assert capture.bounded_text("x" * 100, 40) == (
        "x" * 9 + "\n...[truncated by output limit]",
        True,
    )
    text = capture.BoundedTextCapture(2)
    assert text.write("abc") == 3
    assert text.write("ignored") == 7
    assert text.read(1) == "a"
    assert capture.read_process_stream(io.StringIO(), "fallback", 2) == "fallback"


def test_supervisor_command_wraps_plain_preparation_and_prefers_active_interpreter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}
    monkeypatch.setattr(linux.sys, "executable", "/trusted/python")
    monkeypatch.setattr(linux.sys, "_base_executable", "/shared/python", raising=False)
    monkeypatch.setattr(linux, "prepare_process_argv", lambda argv: list(argv))

    def freeze(argv: PreparedProcessArgv, **kwargs: Any) -> PreparedProcessArgv:
        observed["argv"] = argv
        observed.update(kwargs)
        argv.executable_identities = (object(),)  # type: ignore[assignment]
        argv.frozen_launcher = (argv[0],)
        argv.frozen_platform = "posix"
        return argv

    monkeypatch.setattr(linux, "freeze_process_argv", freeze)
    target = _prepared("--version")

    result = linux.supervisor_command(target, forbidden_roots=("/workspace",))

    assert observed["argv"] == ["/trusted/python"]
    assert observed["forbidden_roots"] == ("/workspace",)
    assert result[:5] == ["/trusted/python", "-I", "-S", "-c", linux.SUPERVISOR_SOURCE]
    assert json.loads(base64.urlsafe_b64decode(result[5])) == target
    assert result.executable_identities


def test_supervisor_command_falls_back_when_active_interpreter_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(linux.sys, "executable", "")
    monkeypatch.setattr(linux.sys, "_base_executable", "/trusted/base-python", raising=False)
    monkeypatch.setattr(
        linux,
        "prepare_process_argv",
        lambda argv: observed.extend(argv) or _prepared(),
    )
    monkeypatch.setattr(linux, "freeze_process_argv", lambda value, **_kwargs: value)

    linux.supervisor_command(_prepared("--version"), forbidden_roots=())

    assert observed == ["/trusted/base-python"]


def test_supervisor_command_never_falls_back_from_an_untrusted_active_interpreter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    monkeypatch.setattr(linux.sys, "executable", "/untrusted/active-python")
    monkeypatch.setattr(linux.sys, "_base_executable", "/trusted/base-python", raising=False)
    monkeypatch.setattr(
        linux,
        "prepare_process_argv",
        lambda argv: observed.extend(argv) or _prepared(),
    )

    def reject_active(_value: PreparedProcessArgv, **_kwargs: Any) -> PreparedProcessArgv:
        raise PermissionError("active interpreter is not trusted")

    monkeypatch.setattr(linux, "freeze_process_argv", reject_active)

    with pytest.raises(PermissionError, match="active interpreter is not trusted"):
        linux.supervisor_command(_prepared("--version"), forbidden_roots=())

    assert observed == ["/untrusted/active-python"]


def test_supervisor_command_preserves_prepared_interpreter_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interpreter = _prepared()
    monkeypatch.setattr(linux, "prepare_process_argv", lambda _argv: interpreter)
    monkeypatch.setattr(linux, "freeze_process_argv", lambda value, **_kwargs: value)

    result = linux.supervisor_command(_prepared("--version"), forbidden_roots=())

    assert result.executable_identities == interpreter.executable_identities
    assert result[:5] == ["tool", "-I", "-S", "-c", linux.SUPERVISOR_SOURCE]
    assert json.loads(base64.urlsafe_b64decode(result[5])) == ["tool", "--version"]


@pytest.mark.parametrize(
    ("clock", "readable", "payload", "message"),
    [
        ([1.0, 7.0], True, b"READY\n", "did not become ready"),
        ([1.0, 1.1], False, b"READY\n", "did not become ready"),
        ([1.0, 1.1], True, b"", "exited before containment"),
        ([1.0, 1.1], True, b"\xff\n", "invalid status"),
        ([1.0, 1.1], True, b"ERROR:nope\n", "failed closed"),
    ],
)
def test_linux_ready_receipt_rejects_invalid_protocol(
    monkeypatch: pytest.MonkeyPatch,
    clock: list[float],
    readable: bool,
    payload: bytes,
    message: str,
) -> None:
    monkeypatch.setattr(linux.time, "monotonic", lambda: clock.pop(0))
    monkeypatch.setattr(
        linux.select,
        "select",
        lambda *_args: ([10] if readable else [], [], []),
    )
    monkeypatch.setattr(linux.os, "read", lambda *_args: payload)

    with pytest.raises(OSError, match=message):
        linux.read_ready(10, _Process())


def test_linux_ready_receipt_rejects_limit_and_dead_supervisor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(linux, "STATUS_LIMIT", 3)
    monkeypatch.setattr(linux.time, "monotonic", lambda: 1.0)
    monkeypatch.setattr(linux.select, "select", lambda *_args: ([10], [], []))
    monkeypatch.setattr(linux.os, "read", lambda *_args: b"abc")
    with pytest.raises(OSError, match="exceeded"):
        linux.read_ready(10, _Process())

    monkeypatch.setattr(linux, "STATUS_LIMIT", 4096)
    monkeypatch.setattr(linux.os, "read", lambda *_args: b"READY\nremainder")
    with pytest.raises(OSError, match="exited during"):
        linux.read_ready(10, _Process(returncode=7))

    process = _Process(returncode=0)
    messages, remainder = linux.read_ready(10, process)
    assert messages == ["READY"]
    assert remainder == b"remainder"


def test_linux_status_close_and_collect_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    process._agency_supervisor_messages = ["READY", "COMPLETE"]
    assert linux.collect_status(process) == ("READY", "COMPLETE")

    process._agency_supervisor_status_fd = 10
    process._agency_supervisor_status_buffer = b"DESC"
    process._agency_supervisor_messages = ["READY"]
    reads = iter((b"ENDANTS\nCOMPLETE\n", b""))
    monkeypatch.setattr(linux.os, "read", lambda *_args: next(reads))
    closed: list[int] = []
    monkeypatch.setattr(linux.os, "close", closed.append)
    assert linux.collect_status(process) == ("READY", "DESCENDANTS", "COMPLETE")
    assert closed == [10]
    assert process._agency_supervisor_status_fd is None
    assert process._agency_supervisor_status_buffer == b""

    process._agency_supervisor_status_fd = 11
    process._agency_supervisor_status_buffer = b"\xff\n"
    monkeypatch.setattr(linux.os, "read", lambda *_args: b"")
    with pytest.raises(OSError, match="invalid status"):
        linux.collect_status(process)

    process._agency_supervisor_status_fd = 12
    process._agency_supervisor_status_buffer = b"x" * linux.STATUS_LIMIT
    with pytest.raises(OSError, match="exceeded"):
        linux.collect_status(process)

    process._agency_supervisor_status_fd = 13
    monkeypatch.setattr(
        linux.os,
        "close",
        lambda _fd: (_ for _ in ()).throw(OSError("already closed")),
    )
    linux.close_status(process)
    assert process._agency_supervisor_status_fd is None


def test_linux_status_collects_empty_closed_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    process._agency_supervisor_messages = ["READY"]
    process._agency_supervisor_status_fd = 10
    process._agency_supervisor_status_buffer = b""
    monkeypatch.setattr(linux.os, "read", lambda *_args: b"")
    monkeypatch.setattr(linux.os, "close", lambda _fd: None)

    with pytest.raises(OSError, match="terminal completion"):
        linux.collect_status(process)
    assert process._agency_supervisor_status_buffer == b""


@pytest.mark.parametrize(
    ("messages", "match"),
    [
        ((), "unique READY"),
        (("COMPLETE",), "unique READY"),
        (("READY", "READY", "COMPLETE"), "unique READY"),
        (("READY", "ERROR:cleanup"), "terminal completion"),
        (("READY", "ERROR:cleanup", "COMPLETE"), "failed closed"),
        (("READY", "COMPLETE", "DESCENDANTS"), "terminal status sequence"),
        (("READY", "COMPLETE", "COMPLETE"), "terminal status sequence"),
        (("READY", "UNKNOWN", "COMPLETE"), "invalid status"),
        (
            ("READY", "DESCENDANTS", "DESCENDANTS", "COMPLETE"),
            "duplicate informational",
        ),
        (("READY", "TERMINATED:nope", "COMPLETE"), "invalid status"),
    ],
)
def test_linux_status_protocol_rejects_missing_or_malformed_terminal_receipts(
    messages: tuple[str, ...],
    match: str,
) -> None:
    process = _Process()
    process._agency_supervisor_messages = list(messages)

    with pytest.raises(OSError, match=match):
        linux.collect_status(process)


def test_linux_status_protocol_accepts_defined_terminal_information() -> None:
    process = _Process()
    process._agency_supervisor_messages = [
        "READY",
        "TERMINATED:15",
        "DESCENDANTS",
        "COMPLETE",
    ]

    assert linux.collect_status(process) == (
        "READY",
        "TERMINATED:15",
        "DESCENDANTS",
        "COMPLETE",
    )


def test_linux_status_protocol_rejects_truncated_terminal_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    process._agency_supervisor_messages = ["READY"]
    process._agency_supervisor_status_fd = 10
    process._agency_supervisor_status_buffer = b"COMP"
    monkeypatch.setattr(linux.os, "read", lambda *_args: b"")
    monkeypatch.setattr(linux.os, "close", lambda _fd: None)

    with pytest.raises(OSError, match="truncated"):
        linux.collect_status(process)


def test_linux_supervisor_spawn_is_fail_closed_off_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owned_process.sys, "platform", "darwin")
    with pytest.raises(OSError, match="only on Linux"):
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )


def test_linux_supervisor_go_pipe_factory_failure_closes_status_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def create(_cls: type[object]) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _owned_pipe_pair(10, 11)
        raise OSError("go pipe")

    monkeypatch.setattr(owned_process.sys, "platform", "linux")
    monkeypatch.setattr(
        owned_process,
        "_linux_supervisor_command",
        lambda target, **_kwargs: target,
    )
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(create),
    )
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    with pytest.raises(OSError, match="go pipe"):
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )

    assert sorted(closed) == [10, 11]


def test_linux_supervisor_spawn_receipt_and_cleanup_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owned_process.sys, "platform", "linux")
    monkeypatch.setattr(
        owned_process,
        "_linux_supervisor_command",
        lambda target, **_kwargs: target,
    )
    pipes = iter(
        (
            _owned_pipe_pair(10, 11),
            _owned_pipe_pair(20, 21),
            _owned_pipe_pair(30, 31),
            _owned_pipe_pair(40, 41),
            _owned_pipe_pair(50, 51),
            _owned_pipe_pair(60, 61),
        )
    )
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: next(pipes)),
    )
    inheritable: list[tuple[int, bool]] = []
    monkeypatch.setattr(
        owned_process.os,
        "set_inheritable",
        lambda fd, value: inheritable.append((fd, value)),
    )
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)
    process = _Process()
    observed: dict[str, Any] = {}

    def popen(*_args: Any, **kwargs: Any) -> _Process:
        observed.update(kwargs)
        return process

    monkeypatch.setattr(owned_process, "_NATIVE_POPEN", popen)
    monkeypatch.setattr(
        owned_process,
        "_read_linux_supervisor_ready",
        lambda *_args: (["READY"], b"tail"),
    )

    result = owned_process._spawn_linux_supervisor(
        _prepared(),
        cwd="/work",
        env={"PATH": "safe"},
        text=True,
        forbidden_roots=(),
    )

    assert result is process
    assert inheritable == [(11, True), (20, True)]
    assert closed == [11, 20]
    assert observed["env"]["PATH"] == "safe"
    assert observed["env"][linux.STATUS_ENV] == "11"
    assert observed["env"][linux.GO_ENV] == "20"
    assert observed["pass_fds"] == (11, 20)
    assert linux.descriptor_number(process._agency_supervisor_status_fd) == 10
    assert process._agency_supervisor_status_buffer == b"tail"
    assert process._agency_strong_containment is True
    assert linux.descriptor_number(process._agency_supervisor_go_fd) == 21
    monkeypatch.setattr(owned_process.os, "write", lambda _fd, payload: len(payload))
    owned_process._close_linux_supervisor_status(process)
    owned_process._close_linux_supervisor_go(process)

    aborted: list[_Process] = []

    def abort(candidate: _Process) -> str:
        aborted.append(candidate)
        owned_process._close_linux_supervisor_status(candidate)
        owned_process._close_linux_supervisor_go(candidate)
        return "missing COMPLETE"

    monkeypatch.setattr(
        owned_process,
        "_abort_linux_supervisor",
        abort,
    )
    monkeypatch.setattr(
        owned_process,
        "_read_linux_supervisor_ready",
        lambda *_args: (_ for _ in ()).throw(OSError("bad receipt")),
    )
    with pytest.raises(OSError, match="bad receipt") as caught:
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )
    assert aborted == [process]
    assert any("missing COMPLETE" in note for note in caught.value.__notes__)
    assert 31 in closed and 40 in closed

    monkeypatch.setattr(
        owned_process,
        "_NATIVE_POPEN",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("spawn")),
    )
    with pytest.raises(OSError, match="spawn"):
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )
    assert all(descriptor in closed for descriptor in (50, 51, 60, 61))


def test_linux_spawn_setup_error_with_clean_abort_preserves_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owned_process.sys, "platform", "linux")
    monkeypatch.setattr(
        owned_process,
        "_linux_supervisor_command",
        lambda target, **_kwargs: target,
    )
    pipes = iter((_owned_pipe_pair(10, 11), _owned_pipe_pair(20, 21)))
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: next(pipes)),
    )
    monkeypatch.setattr(owned_process.os, "set_inheritable", lambda *_args: None)
    monkeypatch.setattr(owned_process.os, "close", lambda *_args: None)
    monkeypatch.setattr(owned_process.os, "write", lambda _fd, payload: len(payload))
    monkeypatch.setattr(owned_process, "_NATIVE_POPEN", lambda *_args, **_kwargs: _Process())
    monkeypatch.setattr(
        owned_process,
        "_read_linux_supervisor_ready",
        lambda *_args: (_ for _ in ()).throw(OSError("original")),
    )

    def abort(process: _Process) -> None:
        owned_process._close_linux_supervisor_status(process)
        owned_process._close_linux_supervisor_go(process)

    monkeypatch.setattr(owned_process, "_abort_linux_supervisor", abort)

    with pytest.raises(OSError, match="original") as caught:
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )
    assert getattr(caught.value, "__notes__", []) == []


@pytest.mark.parametrize(
    ("boundary", "after_store"),
    [
        ("_agency_supervisor_status_fd", False),
        ("_agency_supervisor_status_fd", True),
        ("_agency_supervisor_go_fd", False),
        ("_agency_supervisor_go_fd", True),
    ],
)
def test_linux_supervisor_fd_transfer_interruption_closes_every_end_once(
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    after_store: bool,
) -> None:
    # Drain finalizers from preceding fault-injection cases before replacing
    # os.close with this test's descriptor ledger.
    gc.collect()

    class _TransferAbort(BaseException):
        pass

    class Process(_Process):
        faulted = False

        def __setattr__(self, name: str, value: object) -> None:
            if name == boundary and isinstance(value, linux.DescriptorOwner) and not self.faulted:
                object.__setattr__(self, "faulted", True)
                if not after_store:
                    raise _TransferAbort
                object.__setattr__(self, name, value)
                raise _TransferAbort
            object.__setattr__(self, name, value)

        def communicate(self, *, timeout: float) -> tuple[bytes, bytes]:
            del timeout
            self.returncode = 125
            return b"", b""

    pipes = iter((_owned_pipe_pair(10, 11), _owned_pipe_pair(20, 21)))
    monkeypatch.setattr(owned_process.sys, "platform", "linux")
    monkeypatch.setattr(
        owned_process,
        "_linux_supervisor_command",
        lambda target, **_kwargs: target,
    )
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: next(pipes)),
    )
    monkeypatch.setattr(owned_process.os, "set_inheritable", lambda *_args: None)
    monkeypatch.setattr(owned_process.os, "write", lambda _fd, payload: len(payload))
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)
    monkeypatch.setattr(owned_process, "_NATIVE_POPEN", lambda *_args, **_kwargs: Process())
    monkeypatch.setattr(owned_process, "_close_process_pipes", lambda _process: None)

    with pytest.raises(_TransferAbort):
        owned_process._spawn_linux_supervisor(
            _prepared(),
            cwd=None,
            env={},
            text=False,
            forbidden_roots=(),
        )

    gc.collect()
    assert sorted(closed) == [10, 11, 20, 21]
    assert all(closed.count(descriptor) == 1 for descriptor in closed)


def _supervisor_guard_namespace() -> dict[str, Any]:
    tree = ast.parse(linux.SUPERVISOR_SOURCE)
    selected_names = {
        "SockFilter",
        "bpf_statement",
        "bpf_jump",
        "guarded_process_handler",
        "guarded_selector_handler",
    }
    selected_constants = {
        "BPF_LD_W_ABS",
        "BPF_JMP_JEQ_K",
        "BPF_RET_K",
        "SECCOMP_ARGUMENT_OFFSET",
        "SECCOMP_RET_ALLOW",
        "SECCOMP_RET_ERRNO",
    }
    body: list[ast.stmt] = []
    for node in tree.body:
        named_definition = (
            isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in selected_names
        )
        selected_assignment = isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in selected_constants
            for target in node.targets
        )
        if named_definition or selected_assignment:
            body.append(node)
    namespace = {
        "ctypes": ctypes,
        "errno": errno,
        "supervisor_pid": 4242,
    }
    exec(compile(ast.Module(body=body, type_ignores=[]), "<guard-test>", "exec"), namespace)
    return namespace


def _run_guard(handler: list[Any], *arguments: int) -> int:
    accumulator = 0
    program_counter = 0
    while True:
        instruction = handler[program_counter]
        if instruction.code == 0x20:
            argument_index = (instruction.k - 16) // 8
            accumulator = arguments[argument_index] & 0xFFFFFFFF
            program_counter += 1
        elif instruction.code == 0x15:
            offset = instruction.jt if accumulator == instruction.k else instruction.jf
            program_counter += offset + 1
        elif instruction.code == 0x06:
            return instruction.k
        else:  # pragma: no cover - helper rejects unexpected generated opcodes
            raise AssertionError(f"unexpected BPF opcode: {instruction.code}")


def test_linux_seccomp_resource_tables_and_selector_conjunctions() -> None:
    tree = ast.parse(linux.SUPERVISOR_SOURCE)
    table_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "PROCESS_CONTROL_SYSCALLS"
            for target in node.targets
        )
    )
    table = ast.literal_eval(table_node.value)
    required = {
        "prlimit64",
        "sched_setparam",
        "sched_setscheduler",
        "sched_setaffinity",
        "sched_setattr",
        "setpriority",
        "ioprio_set",
    }
    for architecture in ("x86_64", "amd64", "aarch64", "arm64", "riscv64"):
        assert required <= table[architecture][1].keys()

    namespace = _supervisor_guard_namespace()
    denied = namespace["SECCOMP_RET_ERRNO"] | errno.EPERM
    allowed = namespace["SECCOMP_RET_ALLOW"]
    supervisor_pid = namespace["supervisor_pid"]
    direct = namespace["guarded_process_handler"](0, (supervisor_pid,))
    assert _run_guard(direct, supervisor_pid) == denied
    assert _run_guard(direct, 0) == allowed
    assert _run_guard(direct, supervisor_pid + 1) == allowed

    setpriority = namespace["guarded_selector_handler"](
        selector_index=0,
        process_index=1,
        process_selector=0,
        group_selector=1,
        user_selector=2,
    )
    ioprio = namespace["guarded_selector_handler"](
        selector_index=0,
        process_index=1,
        process_selector=1,
        group_selector=2,
        user_selector=3,
    )
    for handler, process_selector, group_selector, user_selector in (
        (setpriority, 0, 1, 2),
        (ioprio, 1, 2, 3),
    ):
        assert _run_guard(handler, process_selector, supervisor_pid) == denied
        assert _run_guard(handler, group_selector, supervisor_pid) == denied
        assert _run_guard(handler, user_selector, 0) == denied
        assert _run_guard(handler, user_selector, supervisor_pid + 1) == denied
        assert _run_guard(handler, process_selector, 0) == allowed
        assert _run_guard(handler, process_selector, supervisor_pid + 1) == allowed
        assert _run_guard(handler, group_selector, 0) == allowed
        assert _run_guard(handler, group_selector, supervisor_pid + 1) == allowed


@pytest.mark.parametrize(
    ("payload", "outcome"),
    [
        (b"GO\n", None),
        (b"GO", OSError),
        (KeyboardInterrupt(), KeyboardInterrupt),
    ],
)
def test_linux_go_release_is_one_way_and_always_closes(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes | BaseException,
    outcome: type[BaseException] | None,
) -> None:
    process = _Process()
    process._agency_strong_containment = True
    process._agency_supervisor_go_fd = 21
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    writes: list[tuple[int, bytes]] = []
    closed: list[int] = []
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)

    def write(descriptor: int, value: bytes) -> int:
        writes.append((descriptor, value))
        if isinstance(payload, BaseException):
            raise payload
        return len(payload)

    monkeypatch.setattr(owned_process.os, "write", write)
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    if outcome is None:
        owned_process._release_owned_process(state)
    else:
        with pytest.raises(outcome):
            owned_process._release_owned_process(state)

    assert writes == [(21, b"GO\n")]
    assert closed == [21]
    assert process._agency_supervisor_go_fd is None


def test_linux_gate_cancellation_and_completion_claim_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writes: list[tuple[int, bytes]] = []
    closed: list[int] = []
    process = _Process()
    process._agency_supervisor_go_fd = 21
    monkeypatch.setattr(
        owned_process.os,
        "write",
        lambda descriptor, payload: writes.append((descriptor, payload)) or len(payload),
    )
    monkeypatch.setattr(owned_process.os, "close", closed.append)

    owned_process._close_linux_supervisor_go(process)
    assert writes == [(21, b"CANCEL\n")]
    assert closed == [21]
    assert process._agency_supervisor_go_fd is None

    process._agency_supervisor_go_fd = 22
    monkeypatch.setattr(
        owned_process.os,
        "write",
        lambda *_args: (_ for _ in ()).throw(OSError("write")),
    )
    monkeypatch.setattr(
        owned_process.os,
        "close",
        lambda *_args: (_ for _ in ()).throw(OSError("close")),
    )
    owned_process._close_linux_supervisor_go(process)
    assert process._agency_supervisor_go_fd is None

    claims: list[object] = []
    owned_process._claim_linux_completion_owner(
        SimpleNamespace(claim_completion_owner=lambda: claims.append(object()))
    )
    owned_process._claim_linux_completion_owner(object())
    assert len(claims) == 1


@pytest.mark.parametrize("failure", ["timeout", "interrupt", "status"])
def test_linux_supervisor_abort_drains_all_failure_paths(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    events: list[str] = []

    class Process:
        _agency_strong_containment = failure == "status"

        def terminate(self) -> None:
            events.append("terminate")
            if failure == "interrupt":
                raise KeyboardInterrupt

        def kill(self) -> None:
            events.append("kill")

        def communicate(self, *, timeout: float) -> None:
            events.append(f"communicate:{timeout}")
            if failure == "timeout" and timeout == 5:
                raise subprocess.TimeoutExpired("supervisor", timeout)
            if failure == "interrupt" and timeout == 5:
                raise KeyboardInterrupt

    process = Process()
    monkeypatch.setattr(
        owned_process,
        "_cancel_linux_supervisor_go",
        lambda _process: events.append("cancel"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_go_descriptor",
        lambda _process: events.append("gate-close"),
    )
    monkeypatch.setattr(
        owned_process,
        "_collect_linux_supervisor_status",
        lambda _process: (_ for _ in ()).throw(OSError("missing COMPLETE")),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_status",
        lambda _process: events.append("status-close"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_process_pipes",
        lambda _process: events.append("pipes-close"),
    )

    result = owned_process._abort_linux_supervisor(process)  # type: ignore[arg-type]

    assert events[0] == "cancel"
    assert events[-2:] == ["status-close", "pipes-close"]
    if failure in {"timeout", "interrupt"}:
        assert "kill" in events
        assert "communicate:2" in events
    if failure == "timeout":
        assert result is None
    elif failure == "interrupt":
        assert result == "KeyboardInterrupt"
    else:
        assert result == "missing COMPLETE"


@pytest.mark.parametrize(
    "failure",
    [
        "cancel",
        "gate-close",
        "terminate",
        "communicate:5",
        "kill",
        "communicate:2",
        "status",
        "status-close",
        "pipes-close",
    ],
)
def test_linux_supervisor_abort_attempts_every_cleanup_after_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    class _CleanupAbort(BaseException):
        pass

    events: list[str] = []

    def event(name: str) -> None:
        events.append(name)
        if failure == name:
            raise _CleanupAbort(name)

    class Process:
        _agency_strong_containment = True
        alive = True

        def terminate(self) -> None:
            event("terminate")

        def kill(self) -> None:
            event("kill")
            self.alive = False

        def communicate(self, *, timeout: float) -> None:
            name = f"communicate:{timeout:g}"
            event(name)
            if timeout == 5 and failure in {
                "communicate:5",
                "kill",
                "communicate:2",
            }:
                raise subprocess.TimeoutExpired("supervisor", timeout)
            self.alive = False

    process = Process()
    monkeypatch.setattr(
        owned_process,
        "_cancel_linux_supervisor_go",
        lambda _process: event("cancel"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_go_descriptor",
        lambda _process: event("gate-close"),
    )
    monkeypatch.setattr(
        owned_process,
        "_collect_linux_supervisor_status",
        lambda _process: event("status"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_status",
        lambda _process: event("status-close"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_process_pipes",
        lambda _process: event("pipes-close"),
    )

    result = owned_process._abort_linux_supervisor(process)  # type: ignore[arg-type]

    assert result == failure
    assert events[-2:] == ["status-close", "pipes-close"]
    assert "status" in events
    assert process.alive is False
    if failure in {"communicate:5", "kill", "communicate:2"}:
        assert "kill" in events
        assert "communicate:2" in events


def test_linux_release_rejects_missing_gate_but_ignores_foreign_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)
    process = _Process()
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    owned_process._release_owned_process(state)

    process._agency_strong_containment = True
    with pytest.raises(OSError, match="GO gate"):
        owned_process._release_owned_process(state)


def test_cleanup_preserves_keyboard_interrupt_and_attempts_every_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process())
    events: list[str] = []

    def failure(name: str) -> None:
        events.append(name)
        raise OSError(name)

    monkeypatch.setattr(
        owned_process,
        "_terminate_owned_process_tree",
        lambda *_args, **_kwargs: failure("terminate"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_atomic_windows_process_resources",
        lambda *_args: failure("atomic"),
    )
    monkeypatch.setattr(
        owned_process,
        "_join_owned_process_io",
        lambda *_args: failure("join"),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_process_pipes",
        lambda *_args: failure("pipes"),
    )
    with pytest.raises(OSError, match="terminate"):
        owned_process._cleanup_owned_process(state)
    assert events == ["terminate", "atomic", "join", "pipes"]

    monkeypatch.setattr(
        owned_process,
        "_claim_windows_containment",
        lambda _state: None,
    )
    monkeypatch.setattr(
        owned_process,
        "_cleanup_owned_process",
        lambda _state: (_ for _ in ()).throw(OSError("cleanup")),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_linux_supervisor_status",
        lambda *_args: (_ for _ in ()).throw(SystemExit(2)),
    )
    monkeypatch.setattr(
        owned_process,
        "_close_atomic_windows_process_resources",
        lambda *_args: (_ for _ in ()).throw(SystemExit(3)),
    )
    state.windows_job = SimpleNamespace(close=lambda: failure("job-close"))

    with pytest.raises(KeyboardInterrupt) as caught:
        owned_process._complete_owned_process(
            state,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
            start_io=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    assert any("cleanup failed: cleanup" in note for note in caught.value.__notes__)
    assert events[-1] == "job-close"


@pytest.mark.parametrize("binary", [False, True], ids=["text", "binary"])
@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (KeyboardInterrupt(), KeyboardInterrupt),
        (RuntimeError("thread"), OSError),
    ],
    ids=["interrupt", "exception"],
)
def test_state_owned_io_workers_preserve_start_failure(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
    failure: BaseException,
    expected: type[BaseException],
) -> None:
    class Thread:
        ident = None

        def __init__(self, *, fail: bool = False) -> None:
            self.fail = fail

        def start(self) -> None:
            if self.fail:
                raise failure

    stdout_thread = Thread()
    stderr_thread = Thread()
    stdin_thread = Thread(fail=True)
    factory_name = "_create_binary_process_io_threads" if binary else "_create_process_io_threads"
    monkeypatch.setattr(
        owned_process,
        factory_name,
        lambda *_args, **_kwargs: (stdout_thread, stderr_thread, stdin_thread),
    )
    monkeypatch.setattr(
        owned_process,
        "_write_process_stdin_bytes" if binary else "_write_process_stdin",
        lambda *_args: None,
    )
    for cleanup_name in (
        "_terminate_owned_process_tree",
        "_join_owned_process_io",
        "_close_process_pipes",
    ):
        monkeypatch.setattr(
            owned_process,
            cleanup_name,
            lambda *_args, **_kwargs: (_ for _ in ()).throw(SystemExit(2)),
        )
    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process())
    starter = owned_process._start_owned_binary_io if binary else owned_process._start_owned_text_io
    kwargs = {"input_bytes": b"x"} if binary else {"input_text": "x"}

    with pytest.raises(expected):
        starter(
            state,
            stdout=io.BytesIO() if binary else io.StringIO(),
            stderr=io.BytesIO() if binary else io.StringIO(),
            **kwargs,
        )
    assert state.stdout_thread is stdout_thread
    assert state.stderr_thread is stderr_thread
    assert state.stdin_thread is stdin_thread


def test_unclaimed_linux_popen_finalizer_is_armed_until_completion_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aborted: list[int] = []
    monkeypatch.setattr(
        owned_process,
        "_abort_linux_supervisor",
        lambda process: aborted.append(id(process)),
    )

    abandoned = object.__new__(owned_process._UnclaimedLinuxPopen)
    abandoned.__del__()
    assert aborted == [id(abandoned)]

    claimed = object.__new__(owned_process._UnclaimedLinuxPopen)
    claimed.claim_completion_owner()
    claimed.__del__()
    assert aborted == [id(abandoned)]


@pytest.mark.parametrize("binary", [False, True], ids=["text", "binary"])
@pytest.mark.parametrize("fault", ["pre-state", "pre-complete"])
def test_linux_unclaimed_spawn_is_finalized_across_call_store_gaps(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
    fault: str,
) -> None:
    aborted: list[int] = []
    monkeypatch.setattr(
        owned_process, "_prepare_owned_process_argv", lambda *_args, **_kwargs: _prepared()
    )
    monkeypatch.setattr(
        owned_process,
        "_abort_linux_supervisor",
        lambda process: aborted.append(id(process)),
    )
    spawn_name = "_spawn_owned_binary_process" if binary else "_spawn_owned_process"
    monkeypatch.setattr(
        owned_process,
        spawn_name,
        lambda *_args, **_kwargs: object.__new__(owned_process._UnclaimedLinuxPopen),
    )
    if fault == "pre-state":
        monkeypatch.setattr(
            owned_process,
            "_OwnedProcessState",
            lambda **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    else:
        monkeypatch.setattr(
            owned_process,
            "_complete_owned_process",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
        )

    runner = owned_process._run_owned_binary_process if binary else owned_process._run_owned_process
    capture_type = io.BytesIO if binary else io.StringIO
    kwargs = {"input_bytes": b"x"} if binary else {"input_text": "x"}
    with pytest.raises(KeyboardInterrupt):
        runner(
            ["tool"],
            cwd=None,
            env={},
            stdout=capture_type(),
            stderr=capture_type(),
            timeout=1,
            **kwargs,
        )
    gc.collect()
    assert len(aborted) == 1


def test_compat_linux_gate_release_and_cleanup_error_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = SimpleNamespace(_is_windows=lambda: False)
    process = _Process()
    process._agency_strong_containment = True
    process._agency_supervisor_go_fd = 21
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    writes: list[tuple[int, bytes]] = []
    closed: list[int] = []
    monkeypatch.setattr(
        compat.os,
        "write",
        lambda descriptor, payload: writes.append((descriptor, payload)) or len(payload),
    )
    monkeypatch.setattr(compat.os, "close", closed.append)

    compat._release_owned_process(api, state)
    assert writes == [(21, b"GO\n")]
    assert closed == [21]

    process._agency_supervisor_go_fd = None
    with pytest.raises(OSError, match="GO gate"):
        compat._release_owned_process(api, state)
    process._agency_supervisor_go_fd = 22
    monkeypatch.setattr(compat.os, "write", lambda *_args: 1)
    monkeypatch.setattr(
        compat.os,
        "close",
        lambda *_args: (_ for _ in ()).throw(OSError("close")),
    )
    with pytest.raises(OSError, match="partial"):
        compat._release_owned_process(api, state)

    process._agency_strong_containment = False
    compat._release_owned_process(api, state)
    compat._establish_windows_containment(api, state)

    cleanup_events: list[str] = []

    def fail(name: str) -> None:
        cleanup_events.append(name)
        raise OSError(name)

    cleanup_api = SimpleNamespace(
        _close_process_pipes=lambda _process: fail("pipes"),
        _join_owned_process_io=lambda _state, _timeout: fail("join"),
        _terminate_owned_process_tree=lambda _process, **_kwargs: fail("terminate"),
    )
    with pytest.raises(OSError, match="terminate"):
        compat._cleanup_owned_process(cleanup_api, state)
    assert cleanup_events == ["terminate", "join", "pipes"]


def test_compat_completion_preserves_interrupt_when_cleanup_fails() -> None:
    process = _Process(returncode=0)
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    api = SimpleNamespace(
        _is_windows=lambda: False,
        _process=None,
        _close_process_pipes=lambda _process: (_ for _ in ()).throw(OSError("cleanup")),
        _join_owned_process_io=lambda *_args: None,
        _quiesce_owned_process=lambda _state: None,
        _terminate_owned_process_tree=lambda *_args, **_kwargs: None,
    )

    with pytest.raises(KeyboardInterrupt) as caught:
        compat._complete_owned_process(
            api,
            state,
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
            start_io=lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
        )
    assert any("cleanup failed: cleanup" in note for note in caught.value.__notes__)


def test_core_completion_cancels_while_target_is_still_gated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process(returncode=-1)
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    event = threading.Event()
    releases: list[object] = []
    terminations: list[object] = []
    monkeypatch.setattr(owned_process, "_claim_linux_completion_owner", lambda _process: None)
    monkeypatch.setattr(owned_process, "_claim_windows_containment", lambda _state: None)
    monkeypatch.setattr(
        owned_process,
        "_release_owned_process",
        lambda owned: releases.append(owned.process),
    )
    monkeypatch.setattr(
        owned_process,
        "_terminate_owned_process_tree",
        lambda target, **_kwargs: terminations.append(target),
    )
    monkeypatch.setattr(
        owned_process,
        "_quiesce_owned_process",
        lambda _state, *, cancel_event: None,
    )
    monkeypatch.setattr(owned_process, "_close_linux_supervisor_status", lambda _process: None)
    monkeypatch.setattr(
        owned_process,
        "_close_atomic_windows_process_resources",
        lambda _process: None,
    )

    completed = owned_process._complete_owned_process(
        state,
        stdout=io.BytesIO(),
        stderr=io.BytesIO(),
        timeout=1,
        start_io=event.set,
        cancel_event=event,
    )

    assert releases == []
    assert terminations == [process]
    assert completed.returncode == 130
    assert completed.cancelled is True


@pytest.mark.parametrize("binary", [False, True], ids=["text", "binary"])
def test_compat_production_path_uses_state_owned_core_workers(binary: bool) -> None:
    process = _Process(returncode=0)
    starts: list[str] = []

    def legacy_starter(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("legacy starter used")

    process_core = SimpleNamespace(
        _claim_linux_completion_owner=lambda _process: None,
        _close_atomic_windows_process_resources=lambda _process: None,
        _close_linux_supervisor_status=lambda _process: None,
        _start_binary_process_io_threads=legacy_starter,
        _start_owned_binary_io=lambda *_args, **_kwargs: starts.append("binary"),
        _start_owned_text_io=lambda *_args, **_kwargs: starts.append("text"),
        _start_process_io_threads=legacy_starter,
    )
    common = {
        "_OwnedProcessState": owned_process._OwnedProcessState,
        "_close_process_pipes": lambda _process: None,
        "_is_windows": lambda: False,
        "_join_owned_process_io": lambda _state, _timeout: None,
        "_prepare_owned_process_argv": lambda _argv, **_kwargs: _prepared(),
        "_process": process_core,
        "_quiesce_owned_process": lambda _state: None,
        "_start_binary_process_io_threads": process_core._start_binary_process_io_threads,
        "_start_process_io_threads": process_core._start_process_io_threads,
        "_terminate_owned_process_tree": lambda _process, **_kwargs: None,
        "_uses_prefilled_windows_stdin": lambda _payload: False,
        "_uses_prefilled_windows_stdin_bytes": lambda _payload: False,
    }
    if binary:
        api = SimpleNamespace(
            **common,
            _spawn_owned_binary_process=lambda *_args, **_kwargs: process,
        )
        result = compat.run_owned_binary_process(
            api,
            ["tool"],
            cwd=None,
            env={},
            stdout=io.BytesIO(b"out"),
            stderr=io.BytesIO(b"err"),
            timeout=1,
        )
    else:
        api = SimpleNamespace(
            **common,
            _spawn_owned_process=lambda *_args, **_kwargs: process,
        )
        result = compat.run_owned_process(
            api,
            ["tool"],
            cwd=None,
            env={},
            stdout=io.StringIO("out"),
            stderr=io.StringIO("err"),
            timeout=1,
        )
    assert result.returncode == 0
    assert starts == ["binary" if binary else "text"]


def test_strong_supervisor_termination_escalates_boundedly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(owned_process.signal, "SIGKILL", 9, raising=False)
    process = _Process()
    process._agency_strong_containment = True
    waits = iter((False, False, True))
    signals: list[int] = []
    reaped: list[_Process] = []
    monkeypatch.setattr(owned_process, "_wait_for_process", lambda *_args: next(waits))
    monkeypatch.setattr(
        owned_process,
        "_signal_posix_process_tree",
        lambda _process, signum: signals.append(signum),
    )
    monkeypatch.setattr(owned_process, "_ensure_process_reaped", reaped.append)

    owned_process._terminate_posix_process_tree(process)

    assert process.terminated == 1
    assert signals == [owned_process.signal.SIGTERM, owned_process.signal.SIGKILL]
    assert reaped == [process]

    process.terminate = lambda: (_ for _ in ()).throw(OSError("gone"))  # type: ignore[method-assign]
    monkeypatch.setattr(owned_process, "_wait_for_process", lambda *_args: True)
    owned_process._terminate_posix_process_tree(process)


def test_central_prefilled_pipe_failure_contracts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: _owned_pipe_pair(10, 11)),
    )
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)
    monkeypatch.setattr(owned_process.os, "write", lambda *_args: 1)
    with pytest.raises(OSError, match="prefill child stdin"):
        owned_process._create_prefilled_stdin_pipe_bytes(b"payload")
    assert closed == [10, 11]

    closed.clear()
    monkeypatch.setattr(owned_process.os, "write", lambda _fd, value: len(value))

    def close(fd: int) -> None:
        if fd == 11:
            raise OSError("close")
        closed.append(fd)

    monkeypatch.setattr(owned_process.os, "close", close)
    with pytest.raises(OSError, match="close"):
        owned_process._create_prefilled_stdin_pipe_bytes(b"")
    assert closed == [10]


def test_central_text_io_partial_start_uses_real_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Started:
        def __init__(self) -> None:
            self.joined: list[float] = []

        def start(self) -> None:
            return None

        def join(self, timeout: float) -> None:
            self.joined.append(timeout)

    class Broken:
        def start(self) -> None:
            raise RuntimeError("thread")

    started = Started()
    process = _Process()
    terminated: list[_Process] = []
    closed: list[_Process] = []
    monkeypatch.setattr(
        owned_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: (started, Broken(), None),
    )
    monkeypatch.setattr(
        owned_process,
        "_terminate_owned_process_tree",
        lambda child, **_kwargs: terminated.append(child),
    )
    monkeypatch.setattr(owned_process, "_close_process_pipes", closed.append)

    with pytest.raises(OSError, match="process I/O workers"):
        owned_process._start_process_io_threads(
            process,  # type: ignore[arg-type]
            stdout=object(),
            stderr=object(),
            input_text="payload",
            windows_job=None,
        )

    assert terminated == [process]
    assert closed == [process]
    assert started.joined == [5]


@pytest.mark.parametrize("binary", [False, True])
def test_central_spawn_rejects_plain_argv_and_routes_posix(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    spawn = (
        owned_process._spawn_owned_binary_process if binary else owned_process._spawn_owned_process
    )
    keyword = {"input_bytes": None} if binary else {"input_text": None}
    with pytest.raises(TypeError, match="frozen executable identity"):
        spawn(  # type: ignore[arg-type]
            ["tool"],
            cwd=None,
            env={},
            **keyword,
        )

    sentinel = object()
    observed: dict[str, Any] = {}
    monkeypatch.setattr(owned_process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)
    monkeypatch.setattr(
        owned_process,
        "_spawn_linux_supervisor",
        lambda target, **kwargs: observed.update(target=target, **kwargs) or sentinel,
    )
    prepared = _prepared()
    assert (
        spawn(
            prepared,
            cwd="/work",
            env={"PATH": "safe"},
            forbidden_roots=("/repo",),
            **keyword,
        )
        is sentinel
    )
    assert observed["target"] is prepared
    assert observed["text"] is (not binary)
    assert observed["forbidden_roots"] == ("/repo",)


@pytest.mark.parametrize("binary", [False, True])
def test_central_windows_spawn_cleans_prefilled_descriptor_failures(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    spawn = (
        owned_process._spawn_owned_binary_process if binary else owned_process._spawn_owned_process
    )
    keyword = {"input_bytes": b"payload"} if binary else {"input_text": "payload"}
    pipe_name = "_create_prefilled_stdin_pipe_bytes" if binary else "_create_prefilled_stdin_pipe"
    monkeypatch.setattr(owned_process, "_is_windows", lambda: True)
    monkeypatch.setattr(owned_process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        owned_process,
        pipe_name,
        lambda _payload: linux.DescriptorOwner(10),
    )
    closed: list[int] = []
    monkeypatch.setattr(owned_process.os, "close", closed.append)
    monkeypatch.setattr(
        owned_process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn")),
    )
    with pytest.raises(RuntimeError, match="spawn"):
        spawn(_prepared(), cwd=None, env={}, **keyword)
    assert closed == [10]

    process = _Process()
    reaped: list[_Process] = []
    pipes_closed: list[_Process] = []
    atomic_resources_closed: list[_Process] = []
    monkeypatch.setattr(
        owned_process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        owned_process.os,
        "close",
        lambda _fd: (_ for _ in ()).throw(OSError("reader close")),
    )
    monkeypatch.setattr(owned_process, "_kill_and_reap_process", reaped.append)
    monkeypatch.setattr(owned_process, "_close_process_pipes", pipes_closed.append)
    monkeypatch.setattr(
        owned_process,
        "_close_atomic_windows_process_resources",
        atomic_resources_closed.append,
    )
    with pytest.raises(OSError, match="reader close"):
        spawn(_prepared(), cwd=None, env={}, **keyword)
    assert reaped == [process]
    assert pipes_closed == [process]
    assert atomic_resources_closed == [process]


@pytest.mark.parametrize("binary", [False, True])
def test_central_windows_spawn_without_prefilled_descriptor(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    spawn = (
        owned_process._spawn_owned_binary_process if binary else owned_process._spawn_owned_process
    )
    keyword = {"input_bytes": b"x" * 5000} if binary else {"input_text": "x" * 5000}
    predicate = "_uses_prefilled_windows_stdin_bytes" if binary else "_uses_prefilled_windows_stdin"
    monkeypatch.setattr(owned_process, "_is_windows", lambda: True)
    monkeypatch.setattr(owned_process, predicate, lambda _payload: False)
    monkeypatch.setattr(owned_process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        owned_process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn")),
    )
    with pytest.raises(RuntimeError, match="spawn"):
        spawn(_prepared(), cwd=None, env={}, **keyword)

    process = _Process()
    monkeypatch.setattr(
        owned_process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: process,
    )

    assert spawn(_prepared(), cwd=None, env={}, **keyword) is process


@pytest.mark.parametrize("binary", [False, True])
def test_central_windows_spawn_ignores_process_wide_popen_wrappers(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    spawn = (
        owned_process._spawn_owned_binary_process if binary else owned_process._spawn_owned_process
    )
    keyword = {"input_bytes": None} if binary else {"input_text": None}
    process = _Process()
    observed: list[dict[str, Any]] = []
    monkeypatch.setattr(owned_process, "_is_windows", lambda: True)
    monkeypatch.setattr(owned_process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        owned_process.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("process-wide Popen wrapper must not select legacy containment")
        ),
    )
    monkeypatch.setattr(
        owned_process,
        "_spawn_atomic_windows_process",
        lambda *_args, **kwargs: observed.append(kwargs) or process,
    )

    assert spawn(_prepared(), cwd=None, env={}, **keyword) is process
    assert observed[0]["text"] is (not binary)


@pytest.mark.parametrize("binary", [False, True])
def test_facade_unrelated_monkeypatches_do_not_select_legacy_spawn(
    monkeypatch: pytest.MonkeyPatch,
    binary: bool,
) -> None:
    facade_spawn = backends._spawn_owned_binary_process if binary else backends._spawn_owned_process
    core_name = "_spawn_owned_binary_process" if binary else "_spawn_owned_process"
    compat_name = "spawn_owned_binary_process" if binary else "spawn_owned_process"
    keyword = {"input_bytes": None} if binary else {"input_text": None}
    sentinel = object()

    monkeypatch.setattr(backends, "prepare_process_argv", lambda argv: argv)
    monkeypatch.setattr(backends, "_start_process_io_threads", object())
    monkeypatch.setattr(backends, "_create_windows_job", object())
    monkeypatch.setattr(backends, "_resume_windows_process", object())
    monkeypatch.setattr(
        backends._process,
        core_name,
        lambda *_args, **_kwargs: sentinel,
    )
    monkeypatch.setattr(
        compat,
        compat_name,
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("unrelated seams must not select legacy process creation")
        ),
    )

    assert facade_spawn(_prepared(), cwd=None, env={}, **keyword) is sentinel


def test_compat_lifecycle_claims_atomic_job_instead_of_reassigning_process() -> None:
    process = SimpleNamespace()
    job = object()
    state = SimpleNamespace(process=process, windows_job=None)
    api = SimpleNamespace(
        _is_windows=lambda: True,
        _create_windows_job=lambda _process: (_ for _ in ()).throw(
            AssertionError("atomic child must not be assigned to a second Job")
        ),
        _resume_windows_process=lambda _pid: (_ for _ in ()).throw(
            AssertionError("atomic child must resume through its retained thread handle")
        ),
        _process=SimpleNamespace(
            _is_atomic_windows_process=lambda candidate: candidate is process,
            _claim_atomic_windows_job=lambda candidate: job if candidate is process else None,
            _resume_atomic_windows_process=lambda candidate: candidate is process,
        ),
    )

    compat._establish_windows_containment(api, state)

    assert state.windows_job is job


@pytest.mark.parametrize(("claimed_job", "resumed"), [(None, True), (object(), False)])
def test_compat_lifecycle_fails_closed_when_atomic_handoff_is_incomplete(
    claimed_job: object | None,
    resumed: bool,
) -> None:
    process = SimpleNamespace()
    state = SimpleNamespace(process=process, windows_job=None)
    api = SimpleNamespace(
        _is_windows=lambda: True,
        _process=SimpleNamespace(
            _is_atomic_windows_process=lambda _process: True,
            _claim_atomic_windows_job=lambda _process: claimed_job,
            _resume_atomic_windows_process=lambda _process: resumed,
        ),
    )

    with pytest.raises(OSError, match="atomically contained"):
        compat._establish_windows_containment(api, state)


def test_compat_lifecycle_rejects_non_atomic_windows_process_without_late_assignment() -> None:
    process = SimpleNamespace()
    state = SimpleNamespace(process=process, windows_job=None)
    api = SimpleNamespace(
        _is_windows=lambda: True,
        _create_windows_job=lambda _process: pytest.fail("late Job assignment is forbidden"),
        _resume_windows_process=lambda _pid: pytest.fail("late thread resume is forbidden"),
        _process=SimpleNamespace(
            _is_atomic_windows_process=lambda _process: False,
        ),
    )

    with pytest.raises(OSError, match="did not provide atomic Windows containment"):
        compat._establish_windows_containment(api, state)
    assert state.windows_job is None


def test_compat_cleanup_releases_unclaimed_atomic_resources() -> None:
    process = SimpleNamespace()
    state = SimpleNamespace(process=process, windows_job=None)
    observed: list[tuple[str, Any]] = []
    api = SimpleNamespace(
        _terminate_owned_process_tree=lambda candidate, **_kwargs: observed.append(
            ("terminate", candidate)
        ),
        _join_owned_process_io=lambda candidate, timeout: observed.append(
            ("join", (candidate, timeout))
        ),
        _close_process_pipes=lambda candidate: observed.append(("pipes", candidate)),
        _process=SimpleNamespace(
            _close_atomic_windows_process_resources=lambda candidate: observed.append(
                ("atomic", candidate)
            )
        ),
    )

    compat._cleanup_owned_process(api, state)

    assert observed == [
        ("terminate", process),
        ("atomic", process),
        ("join", (state, 5)),
        ("pipes", process),
    ]

    observed.clear()
    del api._process
    compat._cleanup_owned_process(api, state)
    assert observed == [
        ("terminate", process),
        ("join", (state, 5)),
        ("pipes", process),
    ]


def test_central_preparation_retains_and_compares_receipts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepared()
    revalidated: list[PreparedProcessArgv] = []
    monkeypatch.setattr(owned_process, "revalidate_process_argv", revalidated.append)
    monkeypatch.setattr(
        owned_process,
        "freeze_process_argv",
        lambda candidate, **_kwargs: (
            setattr(candidate, "executable_identities", prepared.executable_identities) or candidate
        ),
    )
    assert (
        owned_process._prepare_owned_process_argv(
            prepared,
            forbidden_roots=("/workspace",),
        )
        is prepared
    )
    assert revalidated == [prepared]

    persistent = _prepared()
    persistent.executable_identities = ()
    persistent.persistent_artifact_identities = (object(),)  # type: ignore[assignment]
    monkeypatch.setattr(
        owned_process,
        "freeze_persistent_process_argv",
        lambda candidate, **_kwargs: (
            setattr(
                candidate,
                "persistent_artifact_identities",
                persistent.persistent_artifact_identities,
            )
            or candidate
        ),
    )
    assert (
        owned_process._prepare_owned_process_argv(
            persistent,
            forbidden_roots=("/workspace",),
        )
        is persistent
    )

    monkeypatch.setattr(
        owned_process,
        "freeze_persistent_process_argv",
        lambda candidate, **_kwargs: (
            setattr(candidate, "persistent_artifact_identities", (object(),)) or candidate
        ),
    )
    with pytest.raises(OSError, match="persistent executable identity changed"):
        owned_process._prepare_owned_process_argv(
            persistent,
            forbidden_roots=("/workspace",),
        )

    monkeypatch.setattr(
        owned_process,
        "freeze_process_argv",
        lambda candidate, **_kwargs: (
            setattr(candidate, "executable_identities", (object(),)) or candidate
        ),
    )
    with pytest.raises(OSError, match="pre-frozen executable identity changed"):
        owned_process._prepare_owned_process_argv(
            prepared,
            forbidden_roots=("/workspace",),
        )

    plain = ["tool"]
    converted = _prepared()
    monkeypatch.setattr(owned_process, "prepare_process_argv", lambda _argv: plain)
    monkeypatch.setattr(
        owned_process,
        "freeze_process_argv",
        lambda candidate, **_kwargs: (
            converted
            if isinstance(candidate, PreparedProcessArgv)
            else pytest.fail("receipt was not constructed")
        ),
    )
    assert (
        owned_process._prepare_owned_process_argv(
            plain,
            forbidden_roots=(),
        )
        is converted
    )

    already_prepared = _prepared("--prepared")
    monkeypatch.setattr(
        owned_process,
        "prepare_process_argv",
        lambda _argv: already_prepared,
    )
    monkeypatch.setattr(
        owned_process,
        "freeze_process_argv",
        lambda candidate, **_kwargs: candidate,
    )
    assert (
        owned_process._prepare_owned_process_argv(
            ["tool", "--prepared"],
            forbidden_roots=(),
        )
        is already_prepared
    )


def test_central_containment_outcome_and_incomplete_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process())
    owned_process._record_supervisor_outcome(state)
    assert state.containment_error is None

    state.process._agency_strong_containment = True
    monkeypatch.setattr(
        owned_process,
        "_collect_linux_supervisor_status",
        lambda _process: ("READY", "DESCENDANTS", "ERROR:failed"),
    )
    owned_process._record_supervisor_outcome(state)
    assert state.descendants_detected is True
    assert state.containment_error == "ERROR:failed"
    with pytest.raises(OSError, match="containment failed"):
        owned_process._raise_for_incomplete_process(state, 1)

    state.containment_error = None
    state.descendants_detected = False
    monkeypatch.setattr(
        owned_process,
        "_collect_linux_supervisor_status",
        lambda _process: (_ for _ in ()).throw(OSError("receipt")),
    )
    owned_process._record_supervisor_outcome(state)
    assert state.containment_error == "receipt"

    state.containment_error = None
    monkeypatch.setattr(
        owned_process,
        "_collect_linux_supervisor_status",
        lambda _process: ("READY",),
    )
    owned_process._record_supervisor_outcome(state)
    assert state.containment_error is None


def test_central_containment_platform_and_quiescence_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process())
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)
    owned_process._establish_windows_containment(state)
    assert state.windows_job is None

    monkeypatch.setattr(owned_process, "_is_windows", lambda: True)
    monkeypatch.setattr(owned_process, "_is_atomic_windows_process", lambda _process: True)
    monkeypatch.setattr(owned_process, "_claim_atomic_windows_job", lambda _process: None)
    with pytest.raises(OSError, match="atomically contained"):
        owned_process._establish_windows_containment(state)

    atomic_job = object()
    monkeypatch.setattr(
        owned_process,
        "_claim_atomic_windows_job",
        lambda _process: atomic_job,
    )
    monkeypatch.setattr(
        owned_process,
        "_resume_atomic_windows_process",
        lambda _process: False,
    )
    with pytest.raises(OSError, match="atomically contained"):
        owned_process._establish_windows_containment(state)
    assert state.windows_job is atomic_job

    monkeypatch.setattr(
        owned_process,
        "_resume_atomic_windows_process",
        lambda _process: True,
    )
    owned_process._establish_windows_containment(state)
    assert state.windows_job is atomic_job

    monkeypatch.setattr(owned_process, "_is_atomic_windows_process", lambda _process: False)
    monkeypatch.setattr(owned_process, "_create_windows_job", lambda _process: None)
    with pytest.raises(OSError, match="could not establish"):
        owned_process._establish_windows_containment(state)

    job = object()
    monkeypatch.setattr(owned_process, "_create_windows_job", lambda _process: job)
    monkeypatch.setattr(owned_process, "_resume_windows_process", lambda _pid: False)
    with pytest.raises(OSError, match="could not establish"):
        owned_process._establish_windows_containment(state)
    monkeypatch.setattr(owned_process, "_resume_windows_process", lambda _pid: True)
    owned_process._establish_windows_containment(state)
    assert state.windows_job is job
    assert owned_process._windows_job_has_active_processes(None) is False

    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process(returncode=0))
    terminated: list[_Process] = []
    joins: list[float] = []
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)
    monkeypatch.setattr(owned_process, "_posix_process_group_active", lambda _process: True)
    monkeypatch.setattr(
        owned_process,
        "_terminate_owned_process_tree",
        lambda process, **_kwargs: terminated.append(process),
    )
    monkeypatch.setattr(
        owned_process,
        "_join_owned_process_io",
        lambda _state, timeout: joins.append(timeout),
    )
    monkeypatch.setattr(
        owned_process,
        "_windows_job_has_active_processes",
        lambda _job: False,
    )
    monkeypatch.setattr(owned_process, "_record_supervisor_outcome", lambda _state: None)

    owned_process._quiesce_owned_process(state)

    assert state.descendants_detected is True
    assert terminated == [state.process, state.process]
    assert joins == [owned_process._DRAIN_GRACE_SECONDS, 5]


def test_non_cancel_quiescence_preserves_initial_lingering_io_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SettlingThread:
        ident = 1

        def __init__(self) -> None:
            self.probes = 0

        def join(self, *, timeout: float) -> None:
            assert timeout in {owned_process._DRAIN_GRACE_SECONDS, 5}

        def is_alive(self) -> bool:
            self.probes += 1
            return self.probes == 1

    state = owned_process._OwnedProcessState(argv=_prepared(), process=_Process(returncode=0))
    state.stdout_thread = SettlingThread()  # type: ignore[assignment]
    monkeypatch.setattr(owned_process, "_is_windows", lambda: False)
    monkeypatch.setattr(owned_process, "_posix_process_group_active", lambda _process: False)
    monkeypatch.setattr(owned_process, "_record_supervisor_outcome", lambda _state: None)
    monkeypatch.setattr(
        owned_process,
        "_windows_job_has_active_processes",
        lambda _job: False,
    )
    monkeypatch.setattr(owned_process, "_terminate_owned_process_tree", lambda *_a, **_kw: None)

    owned_process._quiesce_owned_process(state)

    assert state.io_lingering is True
    with pytest.raises(OSError, match="I/O workers remained active"):
        owned_process._raise_for_incomplete_process(state, 1)


@pytest.mark.parametrize("binary", [False, True])
def test_compat_spawn_rejects_plain_argv_and_delegates_to_core_policy(
    binary: bool,
) -> None:
    spawn = compat.spawn_owned_binary_process if binary else compat.spawn_owned_process
    keyword = {"input_bytes": None} if binary else {"input_text": None}
    with pytest.raises(TypeError, match="frozen executable identity"):
        spawn(SimpleNamespace(), ["tool"], cwd=None, env={}, **keyword)

    sentinel = object()
    observed: dict[str, Any] = {}
    core_name = "_spawn_owned_binary_process" if binary else "_spawn_owned_process"

    def core_spawn(target: PreparedProcessArgv, **kwargs: Any) -> object:
        observed.update(target=target, **kwargs)
        return sentinel

    api = SimpleNamespace(
        _process=SimpleNamespace(**{core_name: core_spawn}),
    )
    prepared = _prepared()

    assert spawn(api, prepared, cwd="/work", env={"PATH": "safe"}, **keyword) is sentinel
    assert observed["target"] is prepared
    assert observed["cwd"] == "/work"
    assert observed["env"] == {"PATH": "safe"}


def test_compat_preparation_covers_transient_receipt_paths() -> None:
    prepared = _prepared()
    receipt = prepared.executable_identities
    revalidated: list[PreparedProcessArgv] = []

    def freeze(candidate: PreparedProcessArgv, **_kwargs: Any) -> PreparedProcessArgv:
        candidate.executable_identities = receipt
        return candidate

    api = SimpleNamespace(
        revalidate_process_argv=revalidated.append,
        freeze_process_argv=freeze,
        freeze_persistent_process_argv=lambda value, **_kwargs: value,
        prepare_process_argv=lambda value: list(value),
    )

    assert compat.prepare_owned_process_argv(api, prepared, forbidden_roots=()) is prepared
    assert (
        compat.prepare_owned_process_argv(api, prepared, forbidden_roots=("/workspace",))
        is prepared
    )
    assert revalidated == [prepared, prepared]

    def changed(candidate: PreparedProcessArgv, **_kwargs: Any) -> PreparedProcessArgv:
        candidate.executable_identities = (object(),)
        return candidate

    api.freeze_process_argv = changed
    with pytest.raises(OSError, match="pre-frozen executable identity changed"):
        compat.prepare_owned_process_argv(
            api,
            prepared,
            forbidden_roots=("/workspace",),
        )

    newly_prepared = _prepared("--new")
    api.prepare_process_argv = lambda _argv: newly_prepared
    api.freeze_process_argv = lambda value, **_kwargs: value
    assert (
        compat.prepare_owned_process_argv(
            api,
            ["tool", "--new"],
            forbidden_roots=(),
        )
        is newly_prepared
    )


def test_compat_quiescence_records_strong_supervisor_outcomes() -> None:
    terminated: list[tuple[Any, Any]] = []
    joins: list[float] = []

    def api_for(status: Any) -> SimpleNamespace:
        def collect(_process: Any) -> tuple[str, ...]:
            if isinstance(status, BaseException):
                raise status
            return status

        return SimpleNamespace(
            _DRAIN_GRACE_SECONDS=0.25,
            _is_windows=lambda: False,
            _join_owned_process_io=lambda _state, timeout: joins.append(timeout),
            _posix_process_group_active=lambda _process: False,
            _process=SimpleNamespace(_collect_linux_supervisor_status=collect),
            _terminate_owned_process_tree=lambda process, windows_job=None: terminated.append(
                (process, windows_job)
            ),
            _windows_job_has_active_processes=lambda _job: False,
        )

    process = _Process(returncode=0)
    process._agency_strong_containment = True
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    compat.quiesce_owned_process(
        api_for(("READY", "DESCENDANTS", "ERROR:failed")),
        state,
    )
    assert state.descendants_detected is True
    assert state.containment_error == "ERROR:failed"
    assert terminated == [(process, None)]
    assert joins == [0.25, 5]

    terminated.clear()
    joins.clear()
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    compat.quiesce_owned_process(api_for(OSError("receipt")), state)
    assert state.containment_error == "receipt"
    assert terminated == [(process, None)]

    state.containment_error = "failed"
    with pytest.raises(OSError, match="containment failed"):
        compat._raise_for_incomplete_process(state, 1)

    terminated.clear()
    joins.clear()
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    compat.quiesce_owned_process(api_for(("READY",)), state)
    assert state.descendants_detected is False
    assert state.containment_error is None
    assert terminated == []
    assert joins == [0.25]


def test_compat_quiescence_terminates_detected_posix_group_before_drain() -> None:
    process = _Process(returncode=0)
    state = owned_process._OwnedProcessState(argv=_prepared(), process=process)
    terminations: list[Any] = []
    api = SimpleNamespace(
        _DRAIN_GRACE_SECONDS=0.25,
        _is_windows=lambda: False,
        _join_owned_process_io=lambda _state, _timeout: None,
        _posix_process_group_active=lambda _process: True,
        _terminate_owned_process_tree=lambda candidate, **_kwargs: terminations.append(candidate),
        _windows_job_has_active_processes=lambda _job: False,
    )

    compat.quiesce_owned_process(api, state)

    assert state.descendants_detected is True
    assert terminations == [process, process]


def test_compat_binary_run_preserves_exact_io_and_process_identity() -> None:
    process = _Process(returncode=4)
    prepared = _prepared("--binary")
    observed: dict[str, Any] = {}

    def start_io(_process: Any, **kwargs: Any) -> tuple[None, None, None]:
        observed.update(kwargs)
        return None, None, None

    api = SimpleNamespace(
        _OwnedProcessState=owned_process._OwnedProcessState,
        _close_process_pipes=lambda _process: None,
        _create_windows_job=lambda _process: None,
        _is_windows=lambda: False,
        _join_owned_process_io=lambda _state, _timeout: None,
        _prepare_owned_process_argv=lambda _argv, **_kwargs: prepared,
        _quiesce_owned_process=lambda _state: None,
        _resume_windows_process=lambda _pid: True,
        _spawn_owned_binary_process=lambda _argv, **_kwargs: process,
        _start_binary_process_io_threads=start_io,
        _terminate_owned_process_tree=lambda _process, **_kwargs: None,
        _uses_prefilled_windows_stdin_bytes=lambda _payload: True,
    )

    result = compat.run_owned_binary_process(
        api,
        ["tool"],
        cwd=None,
        env={},
        stdout=io.BytesIO(b"out"),
        stderr=io.BytesIO(b"err"),
        timeout=1,
        input_bytes=b"input",
    )

    assert result.args is prepared
    assert result.returncode == 4
    assert result.stdout == b"out"
    assert result.stderr == b"err"
    assert result.process_id == process.pid
    assert observed["input_bytes"] is None


def test_backends_default_core_routes_and_binary_compatibility_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert backends._is_windows() is (os.name == "nt")
    prepared = _prepared()
    monkeypatch.setattr(
        backends._process,
        "_prepare_owned_process_argv",
        lambda _argv, **_kwargs: prepared,
    )
    assert backends._prepare_owned_process_argv(["tool"], forbidden_roots=()) is prepared

    state = owned_process._OwnedProcessState(argv=prepared, process=_Process(returncode=0))
    observed: list[Any] = []
    monkeypatch.setattr(
        backends._process,
        "_quiesce_owned_process",
        observed.append,
    )
    backends._quiesce_owned_process(state)
    assert observed == [state]

    completed = subprocess.CompletedProcess(prepared, 0, stdout="out", stderr="err")
    monkeypatch.setattr(
        backends._process,
        "_run_owned_process",
        lambda *_args, **_kwargs: completed,
    )
    assert (
        backends._run_owned_process(
            ["tool"],
            cwd=None,
            env={},
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
        )
        is completed
    )

    bounded = object()
    bounded_kwargs: dict[str, Any] = {}

    def bounded_run(*_args: Any, **kwargs: Any) -> object:
        bounded_kwargs.update(kwargs)
        return bounded

    monkeypatch.setattr(
        backends._process,
        "run_bounded_process",
        bounded_run,
    )
    assert (
        backends.run_bounded_process(
            ["tool"],
            timeout=1,
            max_input_bytes=123,
        )
        is bounded
    )
    assert bounded_kwargs["max_input_bytes"] == 123

    sentinel = object()
    monkeypatch.setattr(backends, "_is_windows", lambda: True)
    assert backends._uses_prefilled_windows_stdin_bytes(b"payload") is True
    assert (
        backends._uses_prefilled_windows_stdin_bytes(
            b"x" * (backends._WINDOWS_PREFILLED_STDIN_BYTES + 1)
        )
        is False
    )
    monkeypatch.setattr(
        backends._compat,
        "run_owned_binary_process",
        lambda *_args, **_kwargs: sentinel,
    )
    assert (
        backends._run_owned_binary_process(
            ["tool"],
            cwd=None,
            env={},
            stdout=io.BytesIO(),
            stderr=io.BytesIO(),
            timeout=1,
        )
        is sentinel
    )
