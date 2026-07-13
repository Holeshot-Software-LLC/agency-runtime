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
from agency_runtime.core.process_argv import prepare_process_argv

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


@dataclass(slots=True)
class _OwnedProcessState:
    """Mutable lifecycle state for one contained delegation process."""

    argv: list[str]
    process: subprocess.Popen[str]
    windows_job: _WindowsJob | None = None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None
    stdin_thread: threading.Thread | None = None
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


def _spawn_owned_process(
    process_argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    input_text: str | None,
) -> subprocess.Popen[str]:
    """Launch a process in a new, initially contained process group."""
    return subprocess.Popen(
        process_argv,
        cwd=cwd,
        # A real pipe with an explicit parent-side close is the only portable
        # EOF contract for every supported host. In particular, Windows
        # PowerShell's Console.In can wait indefinitely on the NUL device even
        # though native readers commonly treat it as immediate EOF.
        stdin=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        **_owned_process_kwargs(suspended=_is_windows()),
    )


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
        input_text=input_text,
        windows_job=state.windows_job,
        prime_suspended_stdin=_is_windows(),
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
) -> subprocess.CompletedProcess[str]:
    """Run argv in a killable process group, including all descendants.

    The orchestration stays in the facade because downstream tests and adapters
    patch its process preparation, Windows resume, and execution seams.
    """
    process_argv = prepare_process_argv(argv)
    process = _spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
    )
    state = _OwnedProcessState(argv=process_argv, process=process)
    try:
        _start_owned_process_io(
            state,
            stdout=stdout,
            stderr=stderr,
            input_text=input_text,
        )
        # Windows children are created suspended. Prepare stdin and its EOF
        # before assignment/resume so runtimes cannot observe an ambient or
        # not-yet-closed input source during startup.
        _establish_windows_containment(state)
        _wait_for_owned_process(state, timeout)
        _quiesce_owned_process(state)
        _raise_for_incomplete_process(state, timeout)
        return subprocess.CompletedProcess(
            process_argv,
            int(process.returncode or 0),
            stdout=stdout.read(),
            stderr=stderr.read(),
        )
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
