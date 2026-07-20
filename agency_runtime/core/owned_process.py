"""Bounded, shell-free subprocess execution with owned-tree containment.

This module is intentionally independent from :mod:`agency_runtime.core.delegation`.
Release tooling imports it without importing backend registries, lifecycle
orchestration, or optional YAML-backed configuration.
"""

from __future__ import annotations

import ctypes
import io
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from agency_runtime.core import owned_process_capture as _capture
from agency_runtime.core import owned_process_linux as _linux
from agency_runtime.core.owned_process_capture import (
    BoundedBinaryProcessResult,
    BoundedProcessResult,
)
from agency_runtime.core.owned_process_windows import (
    WindowsJob as _WindowsJob,
)
from agency_runtime.core.owned_process_windows import (
    create_windows_job as _create_windows_job,
)
from agency_runtime.core.owned_process_windows import (
    resume_windows_process as _resume_windows_process,
)
from agency_runtime.core.owned_process_windows_atomic import (
    claim_atomic_windows_job as _claim_atomic_windows_job,
)
from agency_runtime.core.owned_process_windows_atomic import (
    close_atomic_windows_process_resources as _close_atomic_windows_process_resources,
)
from agency_runtime.core.owned_process_windows_atomic import (
    is_atomic_windows_process as _is_atomic_windows_process,
)
from agency_runtime.core.owned_process_windows_atomic import (
    release_atomic_windows_job as _release_atomic_windows_job,
)
from agency_runtime.core.owned_process_windows_atomic import (
    resume_atomic_windows_process as _resume_atomic_windows_process,
)
from agency_runtime.core.owned_process_windows_atomic import (
    spawn_atomic_windows_process as _spawn_atomic_windows_process,
)
from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
    freeze_persistent_process_argv,
    freeze_process_argv,
    prepare_process_argv,
    revalidate_process_argv,
)
from agency_runtime.core.windows_system import trusted_windows_system_executable

_DRAIN_GRACE_SECONDS = 0.5
_LINUX_SUPERVISOR_GO_ENV = _linux.GO_ENV
_LINUX_SUPERVISOR_PARENT_ENV = _linux.PARENT_ENV
_LINUX_SUPERVISOR_STATUS_ENV = _linux.STATUS_ENV
_WINDOWS_PREFILLED_STDIN_BYTES = 4096
_ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
_BinaryProcessRunner = Callable[..., subprocess.CompletedProcess[bytes]]
_IS_WINDOWS = os.name == "nt"
DEFAULT_MAX_INPUT_BYTES = _capture.DEFAULT_MAX_INPUT_BYTES

# Historical private aliases remain available through delegation.backend_process.
_BoundedBytesCapture = _capture.BoundedBytesCapture
_BoundedTextCapture = _capture.BoundedTextCapture
_bounded = _capture.bounded_text
_bounded_bytes = _capture.bounded_bytes
_read_process_stream = _capture.read_process_stream
_stream_bytes = _capture.stream_bytes
_stream_text = _capture.stream_text
_LINUX_SUPERVISOR_SOURCE = _linux.SUPERVISOR_SOURCE
_LinuxDescriptorOwner = _linux.DescriptorOwner
_cancel_linux_supervisor_go = _linux.cancel_go
_close_linux_supervisor_go_descriptor = _linux.close_go
_close_linux_supervisor_status = _linux.close_status
_collect_linux_supervisor_status = _linux.collect_status
_linux_descriptor_number = _linux.descriptor_number
_release_linux_supervisor_go = _linux.release_go
_linux_supervisor_command = _linux.supervisor_command
_read_linux_supervisor_ready = _linux.read_ready


class _OwnedPipePair:
    """Two descriptor owners populated directly by a native pipe call."""

    __slots__ = ("_read", "_storage", "_write")

    def __init__(self) -> None:
        self._read: _LinuxDescriptorOwner | None = None
        self._write: _LinuxDescriptorOwner | None = None
        self._storage = (ctypes.c_int * 2)(-1, -1)
        self._read = _LinuxDescriptorOwner.from_storage(
            self._storage,
            0,
        )
        self._write = _LinuxDescriptorOwner.from_storage(
            self._storage,
            1,
        )

    @classmethod
    def create(cls) -> _OwnedPipePair:
        pair = cls()
        try:
            pair._populate()
            return pair
        except BaseException:
            with suppress(BaseException):
                pair.close()
            raise

    def _populate(self) -> None:
        if _IS_WINDOWS:
            runtime = ctypes.CDLL("ucrtbase", use_errno=True)
            create_pipe = runtime._pipe
            create_pipe.argtypes = [
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_uint,
                ctypes.c_int,
            ]
            create_pipe.restype = ctypes.c_int
            flags = getattr(os, "O_BINARY", 0x8000) | getattr(os, "O_NOINHERIT", 0x80)
            result = create_pipe(self._storage, 4096, flags)
        else:
            runtime = ctypes.CDLL(None, use_errno=True)
            create_pipe = runtime.pipe2
            create_pipe.argtypes = [
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_int,
            ]
            create_pipe.restype = ctypes.c_int
            result = create_pipe(self._storage, getattr(os, "O_CLOEXEC", 0))
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))

    def _detach(self, attribute: str) -> _LinuxDescriptorOwner:
        owner = getattr(self, attribute)
        if owner is None:
            raise OSError("pipe descriptor was already detached")
        setattr(self, attribute, None)
        return owner

    def detach_read(self) -> _LinuxDescriptorOwner:
        return self._detach("_read")

    def detach_write(self) -> _LinuxDescriptorOwner:
        return self._detach("_write")

    def close(self) -> None:
        owners = (self._read, self._write)
        self._read = None
        self._write = None
        first_error: BaseException | None = None
        for owner in owners:
            if owner is None:
                continue
            try:
                owner.close()
            except BaseException as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    def __del__(self) -> None:
        with suppress(BaseException):
            self.close()


def _close_descriptor_owner(value: object) -> None:
    close = getattr(value, "close", None)
    if callable(close):
        close()
        return
    descriptor = _linux_descriptor_number(value)
    if descriptor is not None:
        os.close(descriptor)


def _descriptor_owner_number(value: object) -> int:
    descriptor = _linux_descriptor_number(value)
    if descriptor is None:
        raise OSError("owned descriptor is unavailable")
    return descriptor


def _add_exception_note(error: BaseException, note: str) -> None:
    add_note = getattr(error, "add_note", None)
    if callable(add_note):  # pragma: no branch - Python 3.10 compatibility
        add_note(note)


def _posix_process_group_active(process: subprocess.Popen[str]) -> bool:
    if _IS_WINDOWS:
        return False
    try:
        os.killpg(process.pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _owned_process_kwargs(
    *,
    platform_name: str | None = None,
    suspended: bool = False,
) -> dict[str, Any]:
    """Return launch flags for a process tree owned by Agency Runtime."""
    if (platform_name or os.name) == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0x08000000
        )
        if suspended:
            creationflags |= getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
        return {
            "creationflags": creationflags,
        }
    return {"start_new_session": True}


def _wait_for_process(process: subprocess.Popen[str], timeout: float) -> bool:
    """Return whether a process exited within a bounded wait."""
    try:
        process.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def _kill_process(process: subprocess.Popen[str]) -> None:
    """Request immediate root-process termination without raising."""
    with suppress(OSError):
        process.kill()


def _kill_and_reap_process(
    process: subprocess.Popen[str],
    *,
    timeout: float = 2,
) -> None:
    """Kill a root process and make one bounded attempt to reap it."""
    _kill_process(process)
    _wait_for_process(process, timeout)


def _close_linux_supervisor_go(process: subprocess.Popen[Any]) -> None:
    try:
        _cancel_linux_supervisor_go(process)
    finally:
        _close_linux_supervisor_go_descriptor(process)


def _abort_linux_supervisor(process: subprocess.Popen[Any]) -> str | None:
    """Cancel a gated launch, then gracefully drain its private subreaper."""

    failures: list[BaseException] = []

    def attempt(action: Callable[[], Any]) -> None:
        try:
            action()
        except BaseException as exc:
            failures.append(exc)

    attempt(lambda: _cancel_linux_supervisor_go(process))
    attempt(lambda: _close_linux_supervisor_go_descriptor(process))
    attempt(process.terminate)
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        attempt(process.kill)
        attempt(lambda: process.communicate(timeout=2))
    except BaseException as exc:
        failures.append(exc)
        attempt(process.kill)
        attempt(lambda: process.communicate(timeout=2))
    if getattr(process, "_agency_strong_containment", False):
        attempt(lambda: _collect_linux_supervisor_status(process))
    attempt(lambda: _close_linux_supervisor_status(process))
    attempt(lambda: _close_process_pipes(process))
    if not failures:
        return None
    return str(failures[0]) or type(failures[0]).__name__


class _UnclaimedLinuxPopen(subprocess.Popen[Any]):
    """Fail closed until the completion state atomically claims this process."""

    _agency_unclaimed_linux_process = True

    def claim_completion_owner(self) -> None:
        self._agency_unclaimed_linux_process = False

    def __del__(self) -> None:
        if getattr(self, "_agency_unclaimed_linux_process", True):
            with suppress(BaseException):
                _abort_linux_supervisor(self)
        with suppress(BaseException):
            super().__del__()


_NATIVE_POPEN = _UnclaimedLinuxPopen


def _claim_linux_completion_owner(process: subprocess.Popen[Any]) -> None:
    claim = getattr(process, "claim_completion_owner", None)
    if callable(claim):
        claim()


def _ensure_process_reaped(process: subprocess.Popen[str]) -> None:
    """Reap a root process, escalating to a kill after five seconds."""
    if not _wait_for_process(process, 5):
        _kill_and_reap_process(process)


def _terminate_windows_job(
    process: subprocess.Popen[str],
    windows_job: _WindowsJob,
) -> None:
    """Terminate and reap a process through its owning Windows Job Object."""
    try:
        terminated = windows_job.terminate()
    except (OSError, TypeError, ValueError):
        terminated = False
    if not _wait_for_process(process, 5):
        terminated = False
    if not terminated or process.poll() is None:
        _kill_and_reap_process(process)


def _terminate_taskkill_helper(helper: subprocess.Popen[str]) -> None:
    """Prevent a timed-out taskkill helper from becoming its own leak."""
    _kill_process(helper)
    with suppress(OSError):
        _wait_for_process(helper, 2)


def _request_windows_tree_termination(process: subprocess.Popen[str]) -> None:
    """Ask taskkill to terminate a Windows tree, with a bounded helper lifetime."""
    try:
        taskkill = trusted_windows_system_executable("taskkill.exe", platform_name="nt")
        helper = subprocess.Popen(
            [taskkill, "/PID", str(process.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **_owned_process_kwargs(platform_name="nt"),
        )
    except OSError:
        _kill_process(process)
        return
    try:
        helper_exited = _wait_for_process(helper, 5)
    except OSError:
        helper_exited = False
    if not helper_exited:
        _terminate_taskkill_helper(helper)
        _kill_process(process)


def _signal_posix_process_tree(
    process: subprocess.Popen[str],
    signal_number: int,
) -> None:
    """Signal the owned POSIX group, falling back to its root process."""
    try:
        os.killpg(process.pid, signal_number)
        return
    except (OSError, ProcessLookupError):
        pass
    try:
        if signal_number == signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
    except OSError:
        pass


def _finish_posix_process_group(process: subprocess.Popen[str]) -> None:
    """Wait briefly for a POSIX process group, then force any survivors down."""
    deadline = time.monotonic() + 1
    while _posix_process_group_active(process) and time.monotonic() < deadline:
        time.sleep(0.05)
    if _posix_process_group_active(process):
        _signal_posix_process_tree(process, signal.SIGKILL)


def _terminate_posix_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate an owned POSIX process group and reap its root."""
    if getattr(process, "_agency_strong_containment", False):
        _close_linux_supervisor_go(process)
        with suppress(OSError):
            process.terminate()
        if not _wait_for_process(process, 3):
            _signal_posix_process_tree(process, signal.SIGTERM)
        if not _wait_for_process(process, 2):
            _signal_posix_process_tree(process, signal.SIGKILL)
        _ensure_process_reaped(process)
        return
    _signal_posix_process_tree(process, signal.SIGTERM)
    if not _wait_for_process(process, 1):
        _signal_posix_process_tree(process, signal.SIGKILL)
    _finish_posix_process_group(process)
    _ensure_process_reaped(process)


def _terminate_windows_process_tree(
    process: subprocess.Popen[str],
    windows_job: _WindowsJob | None,
) -> None:
    """Terminate an owned Windows process tree and reap its root."""
    if windows_job is not None:
        _terminate_windows_job(process, windows_job)
        return
    _request_windows_tree_termination(process)
    _ensure_process_reaped(process)


def _terminate_owned_process_tree(
    process: subprocess.Popen[str],
    *,
    platform_name: str | None = None,
    windows_job: _WindowsJob | None = None,
) -> None:
    """Terminate the complete process tree started for one delegation."""
    platform = platform_name or os.name
    if platform == "nt":
        _terminate_windows_process_tree(process, windows_job)
        return
    _terminate_posix_process_tree(process)


def _close_process_pipes(process: subprocess.Popen[str]) -> None:
    """Close every parent-side process pipe after pre-I/O launch failures."""

    failures: list[BaseException] = []
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            try:
                stream.close()
            except BaseException as exc:
                failures.append(exc)
    try:
        _close_linux_supervisor_status(process)
    except BaseException as exc:
        failures.append(exc)
    if failures:
        raise failures[0]


def _drain_process_stream(stream: Any, capture: Any) -> None:
    """Drain one child stream while bounding storage through the capture sink."""
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            capture.write(chunk)
    except (OSError, ValueError):
        pass
    finally:
        with suppress(OSError, ValueError):
            stream.close()


def _write_process_stdin(
    process: subprocess.Popen[str],
    input_text: str,
) -> None:
    """Write exact text and close child stdin, tolerating an early child exit."""
    try:
        if process.stdin is not None:
            # TextIOWrapper otherwise translates LF to CRLF on Windows. That
            # mutates JSON/hash-bearing protocol payloads before the child sees
            # them. Reconfigure only real text streams; test doubles and binary
            # streams retain their existing contract.
            if isinstance(process.stdin, io.TextIOBase):
                reconfigure = getattr(process.stdin, "reconfigure", None)
                if callable(reconfigure):
                    with suppress(OSError, TypeError, ValueError):
                        reconfigure(newline="")
            process.stdin.write(input_text)
            process.stdin.flush()
    except (BrokenPipeError, OSError, ValueError):
        pass
    finally:
        if process.stdin is not None:
            with suppress(OSError, ValueError):
                process.stdin.close()


def _write_process_stdin_bytes(
    process: subprocess.Popen[bytes],
    input_bytes: bytes,
) -> None:
    """Write exact bytes and close child stdin, tolerating an early child exit."""

    try:
        if process.stdin is not None:
            process.stdin.write(input_bytes)
            process.stdin.flush()
    except (BrokenPipeError, OSError, ValueError):
        pass
    finally:
        if process.stdin is not None:
            with suppress(OSError, ValueError):
                process.stdin.close()


def _create_process_io_threads(
    process: subprocess.Popen[str],
    *,
    stdout: Any,
    stderr: Any,
    input_text: str | None,
) -> tuple[threading.Thread, threading.Thread, threading.Thread | None]:
    """Construct, but do not start, the workers for one child process."""
    stdout_thread = threading.Thread(
        target=_drain_process_stream,
        args=(process.stdout, stdout),
        name="agency-stdout-drain",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_process_stream,
        args=(process.stderr, stderr),
        name="agency-stderr-drain",
        daemon=True,
    )
    stdin_thread = (
        threading.Thread(
            target=_write_process_stdin,
            args=(process, input_text),
            name="agency-stdin-writer",
            daemon=True,
        )
        if input_text is not None
        else None
    )
    return stdout_thread, stderr_thread, stdin_thread


def _create_binary_process_io_threads(
    process: subprocess.Popen[bytes],
    *,
    stdout: Any,
    stderr: Any,
    input_bytes: bytes | None,
) -> tuple[threading.Thread, threading.Thread, threading.Thread | None]:
    """Construct binary pipe workers without decoding or newline translation."""

    stdout_thread = threading.Thread(
        target=_drain_process_stream,
        args=(process.stdout, stdout),
        name="agency-stdout-binary-drain",
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_drain_process_stream,
        args=(process.stderr, stderr),
        name="agency-stderr-binary-drain",
        daemon=True,
    )
    stdin_thread = (
        threading.Thread(
            target=_write_process_stdin_bytes,
            args=(process, input_bytes),
            name="agency-stdin-binary-writer",
            daemon=True,
        )
        if input_bytes is not None
        else None
    )
    return stdout_thread, stderr_thread, stdin_thread


def _cleanup_partial_io_start(
    process: subprocess.Popen[str],
    *,
    windows_job: _WindowsJob | None,
    started: list[threading.Thread],
) -> None:
    """Stop a child and join workers after thread startup fails part-way."""
    _terminate_owned_process_tree(process, windows_job=windows_job)
    for thread in started:
        thread.join(timeout=5)
    _close_process_pipes(process)


def _start_process_io_threads(
    process: subprocess.Popen[str],
    *,
    stdout: Any,
    stderr: Any,
    input_text: str | None,
    windows_job: _WindowsJob | None,
) -> tuple[threading.Thread, threading.Thread, threading.Thread | None]:
    """Start bounded pipe workers, cleaning the tree after any partial failure."""
    if input_text is None:
        # Close a real pipe instead of delegating EOF semantics to the platform
        # null device. Writing an empty payload is synchronous and cannot block,
        # while the existing helper also tolerates an early child exit.
        _write_process_stdin(process, "")
    threads = _create_process_io_threads(
        process,
        stdout=stdout,
        stderr=stderr,
        input_text=input_text,
    )
    started: list[threading.Thread] = []
    try:
        # Begin asynchronous stdin delivery first. Windows bounded payloads are
        # already present in a preclosed launch pipe and therefore arrive here
        # without an input writer; only larger payloads need this worker.
        for thread in (threads[2], threads[0], threads[1]):
            if thread is not None:
                thread.start()
                started.append(thread)
    except BaseException as exc:
        _cleanup_partial_io_start(
            process,
            windows_job=windows_job,
            started=started,
        )
        if isinstance(exc, Exception):
            raise OSError("could not start process I/O workers") from exc
        raise
    return threads


def _start_binary_process_io_threads(
    process: subprocess.Popen[bytes],
    *,
    stdout: Any,
    stderr: Any,
    input_bytes: bytes | None,
    windows_job: _WindowsJob | None,
) -> tuple[threading.Thread, threading.Thread, threading.Thread | None]:
    """Start binary pipe workers, cleaning the tree after any partial failure."""

    if input_bytes is None:
        _write_process_stdin_bytes(process, b"")
    threads = _create_binary_process_io_threads(
        process,
        stdout=stdout,
        stderr=stderr,
        input_bytes=input_bytes,
    )
    started: list[threading.Thread] = []
    try:
        for thread in (threads[2], threads[0], threads[1]):
            if thread is not None:
                thread.start()
                started.append(thread)
    except BaseException as exc:
        _cleanup_partial_io_start(
            process,
            windows_job=windows_job,
            started=started,
        )
        if isinstance(exc, Exception):
            raise OSError("could not start binary process I/O workers") from exc
        raise
    return threads


@dataclass(slots=True)
class _OwnedProcessState:
    """Mutable lifecycle state for one strongly contained subprocess."""

    argv: PreparedProcessArgv
    process: subprocess.Popen[Any]
    windows_job: _WindowsJob | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    stdin_thread: threading.Thread | None = None
    stdin_preloaded: bool = False
    timeout_error: subprocess.TimeoutExpired | None = None
    descendants_detected: bool = False
    io_lingering: bool = False
    containment_error: str | None = None

    def threads(self) -> tuple[threading.Thread, ...]:
        """Return every I/O worker created for this process."""

        return tuple(
            thread
            for thread in (self.stdin_thread, self.stdout_thread, self.stderr_thread)
            if thread is not None
        )


def _is_windows() -> bool:
    return os.name == "nt"


def _uses_prefilled_windows_stdin(input_text: str | None) -> bool:
    payload_size = len((input_text or "").encode("utf-8", errors="replace"))
    return _is_windows() and payload_size <= _WINDOWS_PREFILLED_STDIN_BYTES


def _uses_prefilled_windows_stdin_bytes(input_bytes: bytes | None) -> bool:
    return _is_windows() and len(input_bytes or b"") <= _WINDOWS_PREFILLED_STDIN_BYTES


def _create_prefilled_stdin_pipe_bytes(payload: bytes) -> _LinuxDescriptorOwner:
    """Create an exact, preclosed stdin pipe for suspended Windows children."""

    pipe = _OwnedPipePair.create()
    read_owner = pipe.detach_read()
    write_owner = pipe.detach_write()
    try:
        if payload and os.write(write_owner.fileno(), payload) != len(payload):
            raise OSError("could not prefill child stdin")
    except BaseException:
        with suppress(BaseException):
            read_owner.close()
        with suppress(BaseException):
            write_owner.close()
        raise
    try:
        write_owner.close()
    except OSError:
        with suppress(OSError):
            read_owner.close()
        raise
    return read_owner


def _create_prefilled_stdin_pipe(input_text: str | None) -> _LinuxDescriptorOwner:
    return _create_prefilled_stdin_pipe_bytes((input_text or "").encode("utf-8", errors="replace"))


def _spawn_linux_supervisor(
    target: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    text: bool,
    forbidden_roots: Sequence[str | os.PathLike[str]],
) -> subprocess.Popen[Any]:
    """Start a dedicated subreaper that owns only ``target`` and its descendants."""

    if not sys.platform.startswith("linux"):
        raise OSError("strong POSIX process containment is available only on Linux")
    supervisor = _linux_supervisor_command(target, forbidden_roots=forbidden_roots)
    status_pipe = _OwnedPipePair.create()
    status_read = status_pipe.detach_read()
    status_write = status_pipe.detach_write()
    go_read: _LinuxDescriptorOwner | None = None
    go_write: _LinuxDescriptorOwner | None = None
    child_environment = dict(env)
    child_environment[_LINUX_SUPERVISOR_PARENT_ENV] = str(os.getpid())
    child_environment[_LINUX_SUPERVISOR_STATUS_ENV] = str(status_write.fileno())
    process: subprocess.Popen[Any] | None = None
    try:
        go_pipe = _OwnedPipePair.create()
        go_read = go_pipe.detach_read()
        go_write = go_pipe.detach_write()
        status_write_fd = status_write.fileno()
        go_read_fd = go_read.fileno()
        os.set_inheritable(status_write_fd, True)
        os.set_inheritable(go_read_fd, True)
        child_environment[_LINUX_SUPERVISOR_GO_ENV] = str(go_read_fd)
        process = _NATIVE_POPEN(
            supervisor,
            cwd=cwd,
            stdin=subprocess.PIPE,
            text=text,
            encoding="utf-8" if text else None,
            errors="replace" if text else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=child_environment,
            pass_fds=(status_write_fd, go_read_fd),
            start_new_session=True,
        )
        status_write.close()
        go_read.close()
        process._agency_supervisor_status_fd = status_read
        process._agency_supervisor_go_fd = go_write
        messages, remainder = _read_linux_supervisor_ready(
            status_read.fileno(),
            process,
        )
        process._agency_supervisor_messages = messages
        process._agency_supervisor_status_buffer = remainder
        process._agency_strong_containment = True
        return process
    except BaseException as exc:
        if process is not None:
            cleanup_error = _abort_linux_supervisor(process)
            if cleanup_error:
                _add_exception_note(
                    exc,
                    f"Linux supervisor cleanup evidence: {cleanup_error}",
                )
        raise
    finally:
        with suppress(OSError):
            status_write.close()
        if go_read is not None:
            with suppress(OSError):
                go_read.close()
        if (
            process is None
            or getattr(process, "_agency_supervisor_status_fd", None) is not status_read
        ):
            with suppress(OSError):
                status_read.close()
        if go_write is not None and (
            process is None or getattr(process, "_agency_supervisor_go_fd", None) is not go_write
        ):
            with suppress(OSError):
                go_write.close()


def _spawn_owned_process(
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_text: str | None,
    forbidden_roots: Sequence[str | os.PathLike[str]] = (),
) -> subprocess.Popen[str]:
    """Launch a text process only after establishing strong containment."""

    if not isinstance(process_argv, PreparedProcessArgv):
        raise TypeError("owned process argv must carry a frozen executable identity")
    revalidate_process_argv(process_argv)
    if not _is_windows():
        return _spawn_linux_supervisor(
            process_argv,
            cwd=cwd,
            env=env,
            text=True,
            forbidden_roots=forbidden_roots,
        )
    prefilled_fd = (
        _create_prefilled_stdin_pipe(input_text)
        if _uses_prefilled_windows_stdin(input_text)
        else None
    )
    try:
        process = _spawn_atomic_windows_process(
            process_argv,
            cwd=cwd,
            env=env,
            stdin=(
                _descriptor_owner_number(prefilled_fd)
                if prefilled_fd is not None
                else subprocess.PIPE
            ),
            text=True,
        )
    except BaseException:
        if prefilled_fd is not None:
            with suppress(OSError):
                _close_descriptor_owner(prefilled_fd)
        raise
    if prefilled_fd is not None:
        try:
            _close_descriptor_owner(prefilled_fd)
        except OSError:
            _kill_and_reap_process(process)
            _close_process_pipes(process)
            _close_atomic_windows_process_resources(process)
            raise
    return process


def _spawn_owned_binary_process(
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_bytes: bytes | None,
    forbidden_roots: Sequence[str | os.PathLike[str]] = (),
) -> subprocess.Popen[bytes]:
    """Launch a binary process only after establishing strong containment."""

    if not isinstance(process_argv, PreparedProcessArgv):
        raise TypeError("owned process argv must carry a frozen executable identity")
    revalidate_process_argv(process_argv)
    if not _is_windows():
        return _spawn_linux_supervisor(
            process_argv,
            cwd=cwd,
            env=env,
            text=False,
            forbidden_roots=forbidden_roots,
        )
    prefilled_fd = (
        _create_prefilled_stdin_pipe_bytes(input_bytes or b"")
        if _uses_prefilled_windows_stdin_bytes(input_bytes)
        else None
    )
    try:
        process = _spawn_atomic_windows_process(
            process_argv,
            cwd=cwd,
            env=env,
            stdin=(
                _descriptor_owner_number(prefilled_fd)
                if prefilled_fd is not None
                else subprocess.PIPE
            ),
            text=False,
        )
    except BaseException:
        if prefilled_fd is not None:
            with suppress(OSError):
                _close_descriptor_owner(prefilled_fd)
        raise
    if prefilled_fd is not None:
        try:
            _close_descriptor_owner(prefilled_fd)
        except OSError:
            _kill_and_reap_process(process)
            _close_process_pipes(process)
            _close_atomic_windows_process_resources(process)
            raise
    return process


def _prepare_owned_process_argv(
    argv: Sequence[str],
    *,
    forbidden_roots: Sequence[str | os.PathLike[str]],
) -> PreparedProcessArgv:
    """Prepare a command once or revalidate its complete existing receipt."""

    if isinstance(argv, PreparedProcessArgv) and (
        argv.executable_identities or argv.persistent_artifact_identities
    ):
        revalidate_process_argv(argv)
        if forbidden_roots:
            candidate = PreparedProcessArgv(argv, artifact_paths=argv.artifact_paths)
            if argv.persistent_artifact_identities:
                verified = freeze_persistent_process_argv(
                    candidate,
                    platform_name=argv.frozen_platform,
                    forbidden_roots=forbidden_roots,
                )
                if verified.persistent_artifact_identities != argv.persistent_artifact_identities:
                    raise OSError("pre-frozen persistent executable identity changed")
            else:
                verified = freeze_process_argv(
                    candidate,
                    platform_name=argv.frozen_platform,
                    forbidden_roots=forbidden_roots,
                )
                if verified.executable_identities != argv.executable_identities:
                    raise OSError("pre-frozen executable identity changed")
        return argv
    prepared = prepare_process_argv(argv)
    if not isinstance(prepared, PreparedProcessArgv):
        prepared = PreparedProcessArgv(prepared, artifact_paths=(prepared[0],))
    return freeze_process_argv(prepared, forbidden_roots=forbidden_roots)


def _claim_windows_containment(state: _OwnedProcessState) -> None:
    if not _is_windows():
        return
    if _is_atomic_windows_process(state.process):
        state.windows_job = _claim_atomic_windows_job(state.process)
        if state.windows_job is None:
            raise OSError("could not claim an atomically contained Windows process")
        return
    state.windows_job = _create_windows_job(state.process)
    if state.windows_job is None:
        raise OSError("could not establish a contained Windows process group")


def _release_owned_process(state: _OwnedProcessState) -> None:
    if _is_windows():
        if _is_atomic_windows_process(state.process):
            job = state.windows_job
            if job is None or not _resume_atomic_windows_process(state.process):
                raise OSError("could not resume an atomically contained Windows process")
            _release_atomic_windows_job(state.process, job)
            return
        if not _resume_windows_process(state.process.pid):
            raise OSError("could not establish a contained Windows process group")
        return
    if not getattr(state.process, "_agency_strong_containment", False):
        return
    if _linux_descriptor_number(getattr(state.process, "_agency_supervisor_go_fd", None)) is None:
        raise OSError("Linux process supervisor GO gate is unavailable")
    _release_linux_supervisor_go(state.process)


def _establish_windows_containment(state: _OwnedProcessState) -> None:
    """Compatibility helper retaining the historical claim-and-resume surface."""

    _claim_windows_containment(state)
    if _is_windows():
        _release_owned_process(state)


def _wait_for_owned_process(state: _OwnedProcessState, timeout: float) -> None:
    try:
        state.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_owned_process_tree(state.process, windows_job=state.windows_job)
        state.timeout_error = exc


def _join_owned_process_io(state: _OwnedProcessState, timeout: float) -> None:
    for thread in state.threads():
        if not hasattr(thread, "ident") or thread.ident is not None:
            thread.join(timeout=timeout)


def _windows_job_has_active_processes(job: _WindowsJob | None) -> bool:
    if job is None:
        return False
    active_processes = job.active_processes()
    deadline = time.monotonic() + _DRAIN_GRACE_SECONDS
    while active_processes and time.monotonic() < deadline:
        time.sleep(0.02)
        active_processes = job.active_processes()
    return active_processes is None or active_processes > 0


def _record_supervisor_outcome(state: _OwnedProcessState) -> None:
    if not getattr(state.process, "_agency_strong_containment", False):
        return
    try:
        messages = _collect_linux_supervisor_status(state.process)
    except OSError as exc:
        state.containment_error = str(exc)
        return
    if "DESCENDANTS" in messages:
        state.descendants_detected = True
    errors = [message for message in messages if message.startswith("ERROR:")]
    if errors:
        state.containment_error = errors[-1]


def _quiesce_owned_process(state: _OwnedProcessState) -> None:
    state.descendants_detected = bool(
        state.descendants_detected
        or (
            not getattr(state.process, "_agency_strong_containment", False)
            and _posix_process_group_active(state.process)
        )
    )
    if state.timeout_error is None and not _is_windows() and state.descendants_detected:
        _terminate_owned_process_tree(state.process)
    _join_owned_process_io(state, _DRAIN_GRACE_SECONDS)
    _record_supervisor_outcome(state)
    state.descendants_detected = bool(
        state.descendants_detected or _windows_job_has_active_processes(state.windows_job)
    )
    state.io_lingering = any(thread.is_alive() for thread in state.threads())
    if state.descendants_detected or state.io_lingering or state.containment_error:
        _terminate_owned_process_tree(state.process, windows_job=state.windows_job)
        _join_owned_process_io(state, 5)


def _raise_for_incomplete_process(state: _OwnedProcessState, timeout: float) -> None:
    if state.timeout_error is not None:
        raise subprocess.TimeoutExpired(state.argv, timeout) from state.timeout_error
    if state.containment_error:
        raise OSError(f"owned process containment failed: {state.containment_error}")
    if state.descendants_detected or state.io_lingering:
        raise OSError(
            "owned process descendants outlived the parent process or I/O workers remained active"
        )


def _cleanup_owned_process(state: _OwnedProcessState) -> None:
    errors: list[BaseException] = []
    for cleanup in (
        lambda: _cancel_linux_supervisor_go(state.process),
        lambda: _close_linux_supervisor_go_descriptor(state.process),
        lambda: _terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        ),
        lambda: _close_atomic_windows_process_resources(state.process),
        lambda: _join_owned_process_io(state, 5),
        lambda: _close_process_pipes(state.process),
    ):
        try:
            cleanup()
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise errors[0]


def _complete_owned_process(
    state: _OwnedProcessState,
    *,
    stdout: Any,
    stderr: Any,
    timeout: float,
    start_io: Callable[[], None],
) -> subprocess.CompletedProcess[Any]:
    try:
        _claim_linux_completion_owner(state.process)
        _claim_windows_containment(state)
        start_io()
        _release_owned_process(state)
        _wait_for_owned_process(state, timeout)
        _quiesce_owned_process(state)
        _raise_for_incomplete_process(state, timeout)
        completed = subprocess.CompletedProcess(
            state.argv,
            int(state.process.returncode or 0),
            stdout=stdout.read(),
            stderr=stderr.read(),
        )
        completed.process_id = int(state.process.pid)
        return completed
    except BaseException as exc:
        try:
            _cleanup_owned_process(state)
        except BaseException as cleanup_exc:
            _add_exception_note(exc, f"owned process cleanup failed: {cleanup_exc}")
        raise
    finally:
        with suppress(BaseException):
            _close_linux_supervisor_status(state.process)
        with suppress(BaseException):
            _close_atomic_windows_process_resources(state.process)
        if state.windows_job is not None:
            with suppress(BaseException):
                state.windows_job.close()


def _run_owned_process(
    argv: Sequence[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdout: Any,
    stderr: Any,
    timeout: float,
    input_text: str | None = None,
    forbidden_roots: Sequence[str | os.PathLike[str]] = (),
) -> subprocess.CompletedProcess[str]:
    process_argv = _prepare_owned_process_argv(argv, forbidden_roots=forbidden_roots)
    process = _spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
        forbidden_roots=forbidden_roots,
    )
    state = _OwnedProcessState(
        argv=process_argv,
        process=process,
        stdin_preloaded=_uses_prefilled_windows_stdin(input_text),
    )
    return _complete_owned_process(
        state,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        start_io=lambda: _start_owned_text_io(
            state,
            stdout=stdout,
            stderr=stderr,
            input_text=input_text,
        ),
    )


def _start_owned_text_io(
    state: _OwnedProcessState,
    *,
    stdout: Any,
    stderr: Any,
    input_text: str | None,
) -> None:
    threads = _create_process_io_threads(
        state.process,
        stdout=stdout,
        stderr=stderr,
        input_text=None if state.stdin_preloaded else input_text,
    )
    state.stdout_thread, state.stderr_thread, state.stdin_thread = threads
    try:
        if input_text is None or state.stdin_preloaded:
            _write_process_stdin(state.process, "")
        for thread in (state.stdin_thread, state.stdout_thread, state.stderr_thread):
            if thread is not None:
                thread.start()
    except BaseException as exc:
        with suppress(BaseException):
            _terminate_owned_process_tree(state.process, windows_job=state.windows_job)
        with suppress(BaseException):
            _join_owned_process_io(state, 5)
        with suppress(BaseException):
            _close_process_pipes(state.process)
        if isinstance(exc, Exception):
            raise OSError("could not start process I/O workers") from exc
        raise


def _run_owned_binary_process(
    argv: Sequence[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdout: Any,
    stderr: Any,
    timeout: float,
    input_bytes: bytes | None = None,
    forbidden_roots: Sequence[str | os.PathLike[str]] = (),
) -> subprocess.CompletedProcess[bytes]:
    process_argv = _prepare_owned_process_argv(argv, forbidden_roots=forbidden_roots)
    process = _spawn_owned_binary_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
        forbidden_roots=forbidden_roots,
    )
    state = _OwnedProcessState(
        argv=process_argv,
        process=process,
        stdin_preloaded=_uses_prefilled_windows_stdin_bytes(input_bytes),
    )
    return _complete_owned_process(
        state,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        start_io=lambda: _start_owned_binary_io(
            state,
            stdout=stdout,
            stderr=stderr,
            input_bytes=input_bytes,
        ),
    )


def _start_owned_binary_io(
    state: _OwnedProcessState,
    *,
    stdout: Any,
    stderr: Any,
    input_bytes: bytes | None,
) -> None:
    threads = _create_binary_process_io_threads(
        state.process,
        stdout=stdout,
        stderr=stderr,
        input_bytes=None if state.stdin_preloaded else input_bytes,
    )
    state.stdout_thread, state.stderr_thread, state.stdin_thread = threads
    try:
        if input_bytes is None or state.stdin_preloaded:
            _write_process_stdin_bytes(state.process, b"")
        for thread in (state.stdin_thread, state.stdout_thread, state.stderr_thread):
            if thread is not None:
                thread.start()
    except BaseException as exc:
        with suppress(BaseException):
            _terminate_owned_process_tree(state.process, windows_job=state.windows_job)
        with suppress(BaseException):
            _join_owned_process_io(state, 5)
        with suppress(BaseException):
            _close_process_pipes(state.process)
        if isinstance(exc, Exception):
            raise OSError("could not start binary process I/O workers") from exc
        raise


def run_bounded_process(
    argv: Sequence[str],
    *,
    process_runner: _ProcessRunner | None = None,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_output_chars: int = 64 * 1024,
) -> BoundedProcessResult:
    """Run an argv-only command with bounded capture and process-tree cleanup."""

    return _capture.run_bounded_text_capture(
        argv,
        process_runner=process_runner or _run_owned_process,
        timeout=timeout,
        cwd=cwd,
        env=env,
        input_text=input_text,
        max_input_bytes=max_input_bytes,
        max_output_chars=max_output_chars,
    )


def run_bounded_binary_process(
    argv: Sequence[str],
    *,
    process_runner: _BinaryProcessRunner | None = None,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_stdout_bytes: int = 64 * 1024,
    max_stderr_bytes: int = 64 * 1024,
) -> BoundedBinaryProcessResult:
    """Run an argv-only command with bounded byte-exact input and output."""

    return _capture.run_bounded_binary_capture(
        argv,
        process_runner=process_runner or _run_owned_binary_process,
        timeout=timeout,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
        max_input_bytes=max_input_bytes,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
    )


run_bounded_text_process = run_bounded_process

__all__ = [
    "DEFAULT_MAX_INPUT_BYTES",
    "BoundedBinaryProcessResult",
    "BoundedProcessResult",
    "run_bounded_binary_process",
    "run_bounded_process",
    "run_bounded_text_process",
]
