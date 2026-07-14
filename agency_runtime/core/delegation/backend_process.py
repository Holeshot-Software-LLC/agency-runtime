"""Bounded subprocess capture and cross-platform process-tree containment."""

from __future__ import annotations

import io
import math
import os
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.delegation.backend_windows import WindowsJob as _WindowsJob

_DRAIN_GRACE_SECONDS = 0.5
_ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
_IS_WINDOWS = os.name == "nt"


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
        helper = subprocess.Popen(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
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
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            with suppress(OSError, ValueError):
                stream.close()


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
    process_runner: _ProcessRunner,
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
    if (
        isinstance(max_output_chars, bool)
        or not isinstance(max_output_chars, int)
        or max_output_chars <= 0
    ):
        raise ValueError("max_output_chars must be a positive integer")
    if input_text is not None and (not isinstance(input_text, str) or "\x00" in input_text):
        raise ValueError("input_text must be text without NUL bytes")

    stdout_capture = _BoundedTextCapture(max_output_chars)
    stderr_capture = _BoundedTextCapture(max_output_chars)
    try:
        completed = process_runner(
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
