"""Compatibility facade for production-safe delegation backends.

The owned-process implementation lives in :mod:`agency_runtime.core.owned_process`.
This facade keeps the original public API and established private monkeypatch
seams while routing unmodified production execution through that single policy.
"""

from __future__ import annotations

import os
import shutil as shutil
import subprocess
import sys
import threading
import time as time
from collections.abc import Collection, Sequence
from types import ModuleType
from typing import Any

from agency_runtime.core import owned_process as _process
from agency_runtime.core.delegation import backend_process_compat as _compat
from agency_runtime.core.delegation import backend_security as _security
from agency_runtime.core.delegation.backend_contracts import (
    BackendError,
    BackendExecutionError,
    BackendProtocolError,
    BackendTimeoutError,
    BackendUnavailableError,
)
from agency_runtime.core.owned_process import (
    DEFAULT_MAX_INPUT_BYTES,
    BoundedBinaryProcessResult,
    BoundedProcessResult,
)
from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
)
from agency_runtime.core.process_argv import (
    freeze_persistent_process_argv as freeze_persistent_process_argv,
)
from agency_runtime.core.process_argv import (
    freeze_process_argv as freeze_process_argv,
)
from agency_runtime.core.process_argv import (
    prepare_process_argv as prepare_process_argv,
)
from agency_runtime.core.process_argv import (
    revalidate_process_argv as revalidate_process_argv,
)

# Private aliases are a historical test and integration surface.
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
_DRAIN_GRACE_SECONDS = _process._DRAIN_GRACE_SECONDS
_OwnedProcessState = _process._OwnedProcessState
_WindowsJob = _process._WindowsJob
_close_process_pipes = _process._close_process_pipes
_create_windows_job = _process._create_windows_job
_join_owned_process_io = _process._join_owned_process_io
_owned_process_kwargs = _process._owned_process_kwargs
_posix_process_group_active = _process._posix_process_group_active
_resume_windows_process = _process._resume_windows_process
_start_binary_process_io_threads = _process._start_binary_process_io_threads
_start_process_io_threads = _process._start_process_io_threads
_terminate_owned_process_tree = _process._terminate_owned_process_tree
_windows_job_has_active_processes = _process._windows_job_has_active_processes
_WINDOWS_PREFILLED_STDIN_BYTES = _process._WINDOWS_PREFILLED_STDIN_BYTES


def _facade() -> ModuleType:
    """Return this module so the compatibility adapter can resolve patched seams."""

    return sys.modules[__name__]


def _is_windows() -> bool:
    """Return whether native Windows containment is required."""

    return os.name == "nt"


def _uses_prefilled_windows_stdin(input_text: str | None) -> bool:
    """Preserve the historical injectable text-stdin decision seam."""

    return _compat.uses_prefilled_windows_stdin(_facade(), input_text)


def _uses_prefilled_windows_stdin_bytes(input_bytes: bytes | None) -> bool:
    """Preserve the historical injectable binary-stdin decision seam."""

    return _compat.uses_prefilled_windows_stdin_bytes(_facade(), input_bytes)


def _create_prefilled_stdin_pipe(input_text: str | None) -> int:
    """Create a preclosed UTF-8 stdin pipe through the shared core policy."""

    return _process._create_prefilled_stdin_pipe(input_text)


def _create_prefilled_stdin_pipe_bytes(input_bytes: bytes | None) -> int:
    """Create a preclosed binary stdin pipe through the shared core policy."""

    return _process._create_prefilled_stdin_pipe_bytes(input_bytes or b"")


def _spawn_owned_process(
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_text: str | None,
) -> subprocess.Popen[str]:
    """Launch through the core policy; compatibility seams cannot replace containment."""

    return _process._spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
    )


def _spawn_owned_binary_process(
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_bytes: bytes | None,
) -> subprocess.Popen[bytes]:
    """Launch through the core policy; compatibility seams cannot replace containment."""

    return _process._spawn_owned_binary_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
    )


def _prepare_owned_process_argv(
    argv: Sequence[str],
    *,
    forbidden_roots: Sequence[str | os.PathLike[str]],
) -> PreparedProcessArgv:
    """Preserve receipt-preparation injection while defaulting to the core."""

    if _compatibility_seams_modified(exclude={"_prepare_owned_process_argv"}):
        return _compat.prepare_owned_process_argv(
            _facade(),
            argv,
            forbidden_roots=forbidden_roots,
        )
    return _process._prepare_owned_process_argv(
        argv,
        forbidden_roots=forbidden_roots,
    )


def _quiesce_owned_process(state: _OwnedProcessState) -> None:
    """Preserve the direct legacy quiescence seam."""

    if _compatibility_seams_modified(exclude={"_quiesce_owned_process"}):
        _compat.quiesce_owned_process(_facade(), state)
        return
    _process._quiesce_owned_process(state)


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
    """Run text I/O through the core unless a legacy seam was patched."""

    if _compatibility_seams_modified(exclude={"_run_owned_process"}):
        return _compat.run_owned_process(
            _facade(),
            argv,
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            input_text=input_text,
            forbidden_roots=forbidden_roots,
        )
    return _process._run_owned_process(
        argv,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        input_text=input_text,
        forbidden_roots=forbidden_roots,
    )


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
    cancel_event: threading.Event | None = None,
) -> subprocess.CompletedProcess[bytes]:
    """Run binary I/O through the core unless a legacy seam was patched."""

    if _compatibility_seams_modified(exclude={"_run_owned_binary_process"}):
        return _compat.run_owned_binary_process(
            _facade(),
            argv,
            cwd=cwd,
            env=env,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
            input_bytes=input_bytes,
            forbidden_roots=forbidden_roots,
            cancel_event=cancel_event,
        )
    return _process._run_owned_binary_process(
        argv,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        input_bytes=input_bytes,
        forbidden_roots=forbidden_roots,
        cancel_event=cancel_event,
    )


def run_bounded_process(
    argv: Sequence[str],
    *,
    timeout: float,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
    max_output_chars: int = 64 * 1024,
) -> BoundedProcessResult:
    """Run an argv-only command with bounded capture and tree cleanup."""

    return _process.run_bounded_process(
        argv,
        process_runner=_run_owned_process,
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
    """Run a byte-exact argv command with bounded I/O and tree cleanup."""

    return _process.run_bounded_binary_process(
        argv,
        process_runner=_run_owned_binary_process,
        timeout=timeout,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
        max_input_bytes=max_input_bytes,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
        retain_output_tail=retain_output_tail,
        cancel_event=cancel_event,
    )


# When any historical dependency is monkeypatched, route the call through the
# adapter that resolves every dependency from this facade.  With the original
# bindings intact, production has one policy and goes straight to owned_process.
_COMPATIBILITY_SEAM_NAMES = (
    "_close_process_pipes",
    "_create_prefilled_stdin_pipe",
    "_create_prefilled_stdin_pipe_bytes",
    "_create_windows_job",
    "_is_windows",
    "_join_owned_process_io",
    "_owned_process_kwargs",
    "_posix_process_group_active",
    "_prepare_owned_process_argv",
    "_quiesce_owned_process",
    "_resume_windows_process",
    "_spawn_owned_binary_process",
    "_spawn_owned_process",
    "_start_binary_process_io_threads",
    "_start_process_io_threads",
    "_terminate_owned_process_tree",
    "_uses_prefilled_windows_stdin",
    "_uses_prefilled_windows_stdin_bytes",
    "_windows_job_has_active_processes",
    "freeze_persistent_process_argv",
    "freeze_process_argv",
    "prepare_process_argv",
    "revalidate_process_argv",
)
_COMPATIBILITY_DEFAULTS = {name: globals()[name] for name in _COMPATIBILITY_SEAM_NAMES}


def _compatibility_seams_modified(
    *,
    names: Collection[str] | None = None,
    exclude: set[str] | None = None,
) -> bool:
    """Return whether a historical private dependency has been replaced."""

    ignored = exclude or set()
    candidates = _COMPATIBILITY_SEAM_NAMES if names is None else names
    return any(
        name not in ignored and globals()[name] is not _COMPATIBILITY_DEFAULTS[name]
        for name in candidates
    )


__all__ = [
    "DEFAULT_MAX_INPUT_BYTES",
    "BackendError",
    "BackendExecutionError",
    "BackendProtocolError",
    "BackendTimeoutError",
    "BackendUnavailableError",
    "BoundedBinaryProcessResult",
    "BoundedProcessResult",
    "run_bounded_binary_process",
    "run_bounded_process",
]
