"""Compatibility facade for production-safe subprocess delegation backends.

Implementation lives in focused backend modules. This facade intentionally
retains the original public API and established private monkeypatch seams.
"""

from __future__ import annotations

import os
import shutil as shutil
import subprocess
import threading
import time
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.delegation import backend_process as _process
from agency_runtime.core.delegation import backend_security as _security
from agency_runtime.core.delegation.backend_command import CommandBackend
from agency_runtime.core.delegation.backend_contracts import (
    BackendError,
    BackendExecutionError,
    BackendProtocolError,
    BackendRegistry,
    BackendTimeoutError,
    BackendUnavailableError,
    DelegateBackend,
)
from agency_runtime.core.delegation.backend_hosts import (
    ClaudeExecBackend,
    CodexExecBackend,
    GenericCLIBackend,
    HermesDelegateBackend,
    OpenClawAgentBackend,
    OpenClawSessionsBackend,
)
from agency_runtime.core.delegation.backend_process import (
    _DRAIN_GRACE_SECONDS,
    BoundedProcessResult,
    _close_process_pipes,
    _owned_process_kwargs,
    _posix_process_group_active,
    _start_process_io_threads,
    _terminate_owned_process_tree,
)
from agency_runtime.core.delegation.backend_process import (
    run_bounded_process as _run_bounded_process,
)
from agency_runtime.core.delegation.backend_windows import (
    WindowsJob as _WindowsJob,
)
from agency_runtime.core.delegation.backend_windows import (
    create_windows_job as _create_windows_job,
)
from agency_runtime.core.delegation.backend_windows import (
    resume_windows_process as _resume_windows_process,
)
from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
    freeze_process_argv,
    prepare_process_argv,
    revalidate_process_argv,
)

# Private aliases are part of the historical test/integration surface. Keep
# them centralized here while the implementation remains in cohesive modules.
_AUTH_HOME_BY_BACKEND = _security.AUTH_HOME_BY_BACKEND
_ERROR_PREVIEW_CHARS = _security.ERROR_PREVIEW_CHARS
_MAX_SPECIALIST_CHARS = _security.MAX_SPECIALIST_CHARS
_MAX_TASK_CHARS = _security.MAX_TASK_CHARS
_SAFE_DELEGATION_ENVIRONMENT_NAMES = _security.SAFE_DELEGATION_ENVIRONMENT_NAMES
_TASK_REDACTION = _security.TASK_REDACTION
_delegation_environment = _security.delegation_environment
_redact_text = _security.redact_text
_redact_value = _security.redact_value
_sensitive_variants = _security.sensitive_variants
_specialist_prompt = _security.specialist_prompt
_BoundedTextCapture = _process._BoundedTextCapture
_bounded = _process._bounded
_read_process_stream = _process._read_process_stream
_stream_text = _process._stream_text
_WINDOWS_PREFILLED_STDIN_BYTES = 4096


@dataclass(slots=True)
class _OwnedProcessState:
    """Mutable lifecycle state for one contained delegation process."""

    argv: list[str]
    process: subprocess.Popen[str]
    windows_job: _WindowsJob | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    stdin_thread: threading.Thread | None = None
    stdin_preloaded: bool = False
    timeout_error: subprocess.TimeoutExpired | None = None
    descendants_detected: bool = False
    io_lingering: bool = False

    def threads(self) -> tuple[threading.Thread, ...]:
        """Return every I/O worker that has been created."""
        return tuple(
            thread
            for thread in (self.stdin_thread, self.stdout_thread, self.stderr_thread)
            if thread is not None
        )


def _is_windows() -> bool:
    """Return whether native Windows containment is required."""
    return os.name == "nt"


def _uses_prefilled_windows_stdin(input_text: str | None) -> bool:
    """Return whether stdin can be complete before a Windows child exists."""
    size = len((input_text or "").encode("utf-8", errors="replace"))
    return _is_windows() and size <= _WINDOWS_PREFILLED_STDIN_BYTES


def _create_prefilled_stdin_pipe(input_text: str | None) -> int:
    """Return a read descriptor whose bounded UTF-8 payload is already at EOF."""
    payload = (input_text or "").encode("utf-8", errors="replace")
    read_fd, write_fd = os.pipe()
    try:
        if payload and os.write(write_fd, payload) != len(payload):
            raise OSError("could not prefill child stdin")
    except BaseException:
        with suppress(OSError):
            os.close(read_fd)
        with suppress(OSError):
            os.close(write_fd)
        raise
    try:
        os.close(write_fd)
    except OSError:
        with suppress(OSError):
            os.close(read_fd)
        raise
    return read_fd


def _spawn_owned_process(
    process_argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    input_text: str | None,
) -> subprocess.Popen[str]:
    """Launch a process in a new, initially contained process group."""
    if not isinstance(process_argv, PreparedProcessArgv):
        raise TypeError("owned process argv must carry a frozen executable identity")
    prefilled_fd = (
        _create_prefilled_stdin_pipe(input_text)
        if _uses_prefilled_windows_stdin(input_text)
        else None
    )
    try:
        # This is deliberately the final operation before constructing the
        # child. Discovery and approval are not durable across filesystem races.
        revalidate_process_argv(process_argv)
        process = subprocess.Popen(
            process_argv,
            cwd=cwd,
            # Bounded Windows input uses a prefilled, preclosed anonymous pipe.
            # Other launches keep a writable pipe for asynchronous delivery.
            stdin=prefilled_fd if prefilled_fd is not None else subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **_owned_process_kwargs(suspended=_is_windows()),
        )
    except BaseException:
        if prefilled_fd is not None:
            with suppress(OSError):
                os.close(prefilled_fd)
        raise
    if prefilled_fd is not None:
        try:
            os.close(prefilled_fd)
        except OSError:
            _process._kill_and_reap_process(process)
            _close_process_pipes(process)
            raise
    return process


def _establish_windows_containment(state: _OwnedProcessState) -> None:
    """Assign and resume a suspended Windows process, failing closed."""
    if not _is_windows():
        return
    state.windows_job = _create_windows_job(state.process)
    if state.windows_job is None or not _resume_windows_process(state.process.pid):
        raise OSError("could not establish a contained Windows process group")


def _start_owned_process_io(
    state: _OwnedProcessState,
    *,
    stdout: Any,
    stderr: Any,
    input_text: str | None,
) -> None:
    """Create the bounded drain and optional stdin workers."""
    (
        state.stdout_thread,
        state.stderr_thread,
        state.stdin_thread,
    ) = _start_process_io_threads(
        state.process,
        stdout=stdout,
        stderr=stderr,
        input_text=None if state.stdin_preloaded else input_text,
        windows_job=state.windows_job,
    )


def _wait_for_owned_process(state: _OwnedProcessState, timeout: float) -> None:
    """Wait for the root process and terminate the tree on timeout."""
    try:
        state.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
        state.timeout_error = exc


def _join_owned_process_io(state: _OwnedProcessState, timeout: float) -> None:
    """Join every worker without ever exceeding the per-worker grace period."""
    for thread in state.threads():
        thread.join(timeout=timeout)


def _windows_job_has_active_processes(job: _WindowsJob | None) -> bool:
    """Wait briefly for a Windows job to quiesce; uncertainty fails closed."""
    if job is None:
        return False
    active_processes = job.active_processes()
    deadline = time.monotonic() + _DRAIN_GRACE_SECONDS
    while active_processes and time.monotonic() < deadline:
        time.sleep(0.02)
        active_processes = job.active_processes()
    return active_processes is None or active_processes > 0


def _quiesce_owned_process(state: _OwnedProcessState) -> None:
    """Drain I/O and reject process trees that outlive their root."""
    state.descendants_detected = _posix_process_group_active(state.process)
    if state.timeout_error is None and not _is_windows() and state.descendants_detected:
        _terminate_owned_process_tree(state.process)

    _join_owned_process_io(state, _DRAIN_GRACE_SECONDS)
    state.descendants_detected = bool(
        state.descendants_detected or _windows_job_has_active_processes(state.windows_job)
    )
    state.io_lingering = any(thread.is_alive() for thread in state.threads())
    if state.descendants_detected or state.io_lingering:
        _terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
        _join_owned_process_io(state, 5)


def _raise_for_incomplete_process(state: _OwnedProcessState, timeout: float) -> None:
    """Convert non-quiescent lifecycle outcomes to stable subprocess errors."""
    if state.timeout_error is not None:
        raise subprocess.TimeoutExpired(state.argv, timeout) from state.timeout_error
    if state.descendants_detected or state.io_lingering:
        raise OSError(
            "owned process descendants outlived the parent process or I/O workers remained active"
        )


def _cleanup_owned_process(state: _OwnedProcessState) -> None:
    """Best-effort cleanup used for cancellation and every exceptional exit."""
    try:
        _terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
    finally:
        _join_owned_process_io(state, 5)
        _close_process_pipes(state.process)


def _run_owned_process(
    argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdout: Any,
    stderr: Any,
    timeout: float,
    input_text: str | None = None,
    forbidden_roots: Sequence[str | os.PathLike[str]] = (),
) -> subprocess.CompletedProcess[str]:
    """Run argv in a killable process group, including all descendants.

    The orchestration stays in the facade because downstream tests and adapters
    patch its process preparation, Windows resume, and execution seams.
    """
    if isinstance(argv, PreparedProcessArgv) and argv.executable_identities:
        # A security-sensitive caller may freeze one executable identity once
        # and reuse it for several bounded probes. Preserve that exact identity
        # instead of resolving PATH again between approval and invocation.
        revalidate_process_argv(argv)
        if forbidden_roots:
            verified = freeze_process_argv(
                PreparedProcessArgv(argv, artifact_paths=argv.artifact_paths),
                forbidden_roots=forbidden_roots,
            )
            if verified.executable_identities != argv.executable_identities:
                raise OSError("pre-frozen executable identity changed")
        process_argv = argv
    else:
        process_argv = prepare_process_argv(argv)
        if not isinstance(process_argv, PreparedProcessArgv):
            process_argv = PreparedProcessArgv(
                process_argv,
                artifact_paths=(process_argv[0],),
            )
        process_argv = freeze_process_argv(
            process_argv,
            forbidden_roots=forbidden_roots,
        )
    process = _spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
    )
    state = _OwnedProcessState(
        argv=process_argv,
        process=process,
        stdin_preloaded=_uses_prefilled_windows_stdin(input_text),
    )
    try:
        _start_owned_process_io(
            state,
            stdout=stdout,
            stderr=stderr,
            input_text=input_text,
        )
        # Windows children are created suspended. Bounded stdin and EOF were
        # frozen before launch; a larger asynchronous writer is already active.
        # Establish containment before any child instruction can execute.
        _establish_windows_containment(state)
        _wait_for_owned_process(state, timeout)
        _quiesce_owned_process(state)
        _raise_for_incomplete_process(state, timeout)
        completed = subprocess.CompletedProcess(
            process_argv,
            int(process.returncode or 0),
            stdout=stdout.read(),
            stderr=stderr.read(),
        )
        # Preserve the identity of the process Agency actually launched. The
        # completed process object is an internal transport between the owned
        # launcher and CommandBackend; exposing the PID here lets evidence
        # callers correlate an observed CLI execution without borrowing a
        # requested specialist slug or fabricating a host-returned run ID.
        completed.process_id = int(process.pid)
        return completed
    except BaseException:
        _cleanup_owned_process(state)
        raise
    finally:
        if state.windows_job is not None:
            state.windows_job.close()


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
    return _run_bounded_process(
        argv,
        process_runner=_run_owned_process,
        timeout=timeout,
        cwd=cwd,
        env=env,
        input_text=input_text,
        max_output_chars=max_output_chars,
    )


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


def get_delegate_func(
    *,
    preferred: str | None = None,
    registry: BackendRegistry | None = None,
):
    """Return a lifecycle-compatible delegate callable from a registry."""
    return (registry or DEFAULT_REGISTRY).delegate_func(preferred=preferred)


__all__ = [
    "DEFAULT_REGISTRY",
    "BackendError",
    "BackendExecutionError",
    "BackendProtocolError",
    "BackendRegistry",
    "BackendTimeoutError",
    "BackendUnavailableError",
    "BoundedProcessResult",
    "ClaudeExecBackend",
    "CodexExecBackend",
    "CommandBackend",
    "DelegateBackend",
    "GenericCLIBackend",
    "HermesDelegateBackend",
    "OpenClawAgentBackend",
    "OpenClawSessionsBackend",
    "get_delegate_func",
    "register_backend",
    "run_bounded_process",
]
