"""Bounded text and binary capture for shell-free owned subprocesses."""

from __future__ import annotations

import math
import os
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.process_argv import PreparedProcessArgv

ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]
BinaryProcessRunner = Callable[..., subprocess.CompletedProcess[bytes]]
DEFAULT_MAX_INPUT_BYTES = 8 * 1024 * 1024
_TEXT_INPUT_CHUNK_CHARS = 16 * 1024


class OwnedProcessContainmentError(OSError):
    """Signal that an owned process tree could not be proven quiescent."""


def stream_text(value: Any) -> str:
    """Normalize real and mocked subprocess stream values to UTF-8 text."""

    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def bounded_text(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = "\n...[truncated by output limit]"
    if limit <= len(marker):
        return marker[:limit], True
    keep = max(0, limit - len(marker))
    return text[:keep] + marker, True


class BoundedTextCapture:
    """Thread-safe file-like sink that discards text after ``limit + 1``."""

    def __init__(self, limit: int) -> None:
        self._limit = limit + 1
        self._chunks: list[str] = []
        self._size = 0
        self._lock = threading.Lock()

    def write(self, value: Any) -> int:
        text = stream_text(value)
        with self._lock:
            remaining = self._limit - self._size
            if remaining > 0:
                retained = text[:remaining]
                self._chunks.append(retained)
                self._size += len(retained)
        return len(text)

    def read(self, limit: int = -1) -> str:
        with self._lock:
            value = "".join(self._chunks)
        return value if limit < 0 else value[:limit]

    def flush(self) -> None:
        return None

    def seek(self, _offset: int, _whence: int = 0) -> int:
        return 0


def stream_bytes(value: Any) -> bytes:
    """Normalize real and mocked binary process values without losing bytes."""

    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)
    return str(value).encode("utf-8", errors="replace")


def bounded_bytes(value: bytes, limit: int) -> tuple[bytes, bool]:
    if len(value) <= limit:
        return value, False
    marker = b"\n...[truncated by output limit]"
    if limit <= len(marker):
        return marker[:limit], True
    keep = max(0, limit - len(marker))
    return value[:keep] + marker, True


class BoundedBytesCapture:
    """Thread-safe sink that retains at most ``limit + 1`` exact bytes."""

    def __init__(self, limit: int) -> None:
        self._limit = limit + 1
        self._chunks: list[bytes] = []
        self._size = 0
        self._lock = threading.Lock()

    def write(self, value: Any) -> int:
        payload = stream_bytes(value)
        with self._lock:
            remaining = self._limit - self._size
            if remaining > 0:
                retained = payload[:remaining]
                self._chunks.append(retained)
                self._size += len(retained)
        return len(payload)

    def read(self, limit: int = -1) -> bytes:
        with self._lock:
            value = b"".join(self._chunks)
        return value if limit < 0 else value[:limit]

    def flush(self) -> None:
        return None

    def seek(self, _offset: int, _whence: int = 0) -> int:
        return 0


class BoundedHeadTailBytesCapture:
    """Thread-safe bounded sink retaining exact leading and trailing bytes."""

    _marker = b"\n...[truncated by output limit]...\n"

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._head_limit = limit // 2
        self._tail_limit = limit - self._head_limit
        self._head = bytearray()
        self._tail = bytearray()
        self._total = 0
        self._lock = threading.Lock()

    def write(self, value: Any) -> int:
        payload = stream_bytes(value)
        observed = len(payload)
        with self._lock:
            self._total += observed
            head_remaining = self._head_limit - len(self._head)
            if head_remaining > 0:
                self._head.extend(payload[:head_remaining])
                payload = payload[head_remaining:]
            if payload:
                self._tail.extend(payload)
                if len(self._tail) > self._tail_limit:
                    del self._tail[: len(self._tail) - self._tail_limit]
        return observed

    def bounded(self) -> tuple[bytes, bool]:
        with self._lock:
            head = bytes(self._head)
            tail = bytes(self._tail)
            total = self._total
        if total <= self._limit:
            return head + tail, False
        if self._limit <= len(self._marker):
            return self._marker[: self._limit], True
        retained = self._limit - len(self._marker)
        head_bytes = retained // 2
        tail_bytes = retained - head_bytes
        return head[:head_bytes] + self._marker + tail[-tail_bytes:], True

    def read(self, limit: int = -1) -> bytes:
        value, _truncated = self.bounded()
        return value if limit < 0 else value[:limit]

    def flush(self) -> None:
        return None

    def seek(self, _offset: int, _whence: int = 0) -> int:
        return 0


def read_process_stream(handle: Any, fallback: Any, limit: int) -> str:
    """Read at most one character beyond a process stream's configured cap."""

    if fallback is not None:
        return stream_text(fallback)
    handle.flush()
    handle.seek(0)
    return stream_text(handle.read(limit + 1))


def _validate_text_input(value: str | None, *, max_input_bytes: int) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError("input_text must be text without NUL bytes")
    observed = 0
    for offset in range(0, len(value), _TEXT_INPUT_CHUNK_CHARS):
        chunk = value[offset : offset + _TEXT_INPUT_CHUNK_CHARS]
        if "\x00" in chunk:
            raise ValueError("input_text must be text without NUL bytes")
        observed += len(chunk.encode("utf-8", errors="replace"))
        if observed > max_input_bytes:
            raise ValueError("input_text exceeds max_input_bytes")


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


@dataclass(frozen=True, slots=True)
class BoundedBinaryProcessResult:
    """Byte-exact bounded result for a shell-free owned subprocess."""

    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    cancelled: bool = False
    failure_category: str | None = None


def _binary_process_failure(exc: BaseException) -> tuple[int, bool, str]:
    if isinstance(exc, subprocess.TimeoutExpired):
        return 124, True, "timeout"
    if isinstance(exc, FileNotFoundError):
        return 127, False, "not-found"
    if isinstance(exc, PermissionError):
        return 126, False, "permission"
    if isinstance(exc, OwnedProcessContainmentError):
        return 1, False, "containment"
    return 1, False, "launch"


def run_bounded_text_capture(
    argv: Sequence[str],
    *,
    process_runner: ProcessRunner,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_output_chars: int = 64 * 1024,
) -> BoundedProcessResult:
    """Apply bounded text I/O around one owned process runner."""

    if isinstance(argv, (str, bytes)) or not argv:
        raise TypeError("argv must be a non-empty sequence of strings")
    normalized = argv if isinstance(argv, PreparedProcessArgv) else list(argv)
    if any(not isinstance(item, str) or not item or "\x00" in item for item in normalized):
        raise ValueError("argv contains an invalid item")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite value greater than zero")
    for name, limit in (
        ("max_input_bytes", max_input_bytes),
        ("max_output_chars", max_output_chars),
    ):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"{name} must be a positive integer")
    _validate_text_input(input_text, max_input_bytes=max_input_bytes)

    stdout_capture = BoundedTextCapture(max_output_chars)
    stderr_capture = BoundedTextCapture(max_output_chars)
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

    stdout = read_process_stream(stdout_capture, None, max_output_chars)
    stderr = read_process_stream(stderr_capture, None, max_output_chars)
    bounded_stdout, stdout_truncated = bounded_text(stdout, max_output_chars)
    bounded_stderr, stderr_truncated = bounded_text(stderr, max_output_chars)
    return BoundedProcessResult(
        returncode=returncode,
        stdout=bounded_stdout,
        stderr=bounded_stderr,
        timed_out=timed_out,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
    )


def run_bounded_binary_capture(
    argv: Sequence[str],
    *,
    process_runner: BinaryProcessRunner,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_stdout_bytes: int = 64 * 1024,
    max_stderr_bytes: int = 64 * 1024,
    retain_output_tail: bool = False,
    cancel_event: threading.Event | None = None,
) -> BoundedBinaryProcessResult:
    """Apply bounded byte-exact I/O around one owned process runner."""

    if isinstance(argv, (str, bytes)) or not argv:
        raise TypeError("argv must be a non-empty sequence of strings")
    normalized = argv if isinstance(argv, PreparedProcessArgv) else list(argv)
    if any(not isinstance(item, str) or not item or "\x00" in item for item in normalized):
        raise ValueError("argv contains an invalid item")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite value greater than zero")
    for name, limit in (
        ("max_input_bytes", max_input_bytes),
        ("max_stdout_bytes", max_stdout_bytes),
        ("max_stderr_bytes", max_stderr_bytes),
    ):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if input_bytes is not None and not isinstance(input_bytes, bytes):
        raise TypeError("input_bytes must be bytes")
    if input_bytes is not None and len(input_bytes) > max_input_bytes:
        raise ValueError("input_bytes exceeds max_input_bytes")
    if not isinstance(retain_output_tail, bool):
        raise TypeError("retain_output_tail must be a bool")
    if cancel_event is not None and not isinstance(cancel_event, threading.Event):
        raise TypeError("cancel_event must be a threading.Event")
    if cancel_event is not None and cancel_event.is_set():
        return BoundedBinaryProcessResult(
            returncode=130,
            stdout=b"",
            stderr=b"",
            cancelled=True,
            failure_category="cancelled",
        )

    capture_type = BoundedHeadTailBytesCapture if retain_output_tail else BoundedBytesCapture
    stdout_capture = capture_type(max_stdout_bytes)
    stderr_capture = capture_type(max_stderr_bytes)
    try:
        runner_kwargs = {
            "cwd": cwd,
            "stdout": stdout_capture,
            "stderr": stderr_capture,
            "timeout": float(timeout),
            "env": dict(os.environ if env is None else env),
            "input_bytes": input_bytes,
        }
        if cancel_event is not None:
            runner_kwargs["cancel_event"] = cancel_event
        completed = process_runner(normalized, **runner_kwargs)
        returncode = int(completed.returncode)
        timed_out = False
        cancelled = bool(getattr(completed, "cancelled", False))
        failure_category = "cancelled" if cancelled else None
    except (subprocess.TimeoutExpired, OSError) as exc:
        returncode, timed_out, failure_category = _binary_process_failure(exc)
        cancelled = False

    if retain_output_tail:
        assert isinstance(stdout_capture, BoundedHeadTailBytesCapture)
        assert isinstance(stderr_capture, BoundedHeadTailBytesCapture)
        bounded_stdout, stdout_truncated = stdout_capture.bounded()
        bounded_stderr, stderr_truncated = stderr_capture.bounded()
    else:
        stdout = stdout_capture.read(max_stdout_bytes + 1)
        stderr = stderr_capture.read(max_stderr_bytes + 1)
        bounded_stdout, stdout_truncated = bounded_bytes(stdout, max_stdout_bytes)
        bounded_stderr, stderr_truncated = bounded_bytes(stderr, max_stderr_bytes)
    return BoundedBinaryProcessResult(
        returncode=returncode,
        stdout=bounded_stdout,
        stderr=bounded_stderr,
        timed_out=timed_out,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        cancelled=cancelled,
        failure_category=failure_category,
    )
