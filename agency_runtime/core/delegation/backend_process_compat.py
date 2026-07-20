"""Legacy process-lifecycle adapter for the delegation facade.

Production execution belongs to :mod:`agency_runtime.core.owned_process`.
This module preserves non-launch lifecycle seams on ``delegation.backends``.
Process creation always delegates to the core launcher, and Windows completion
accepts only its atomic Job-at-creation receipt. Tests and downstream
integrations may still replace an entire private runner explicitly, but changing
one legacy helper can no longer select weaker containment.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from contextlib import suppress
from typing import Any

from agency_runtime.core import owned_process_linux as _linux
from agency_runtime.core.process_argv import PreparedProcessArgv


def _add_exception_note(error: BaseException, note: str) -> None:
    add_note = getattr(error, "add_note", None)
    if callable(add_note):  # pragma: no branch - Python 3.10 compatibility
        add_note(note)


def uses_prefilled_windows_stdin(api: Any, input_text: str | None) -> bool:
    """Return whether text stdin can be frozen before a Windows child exists."""

    payload_size = len((input_text or "").encode("utf-8", errors="replace"))
    return api._is_windows() and payload_size <= api._WINDOWS_PREFILLED_STDIN_BYTES


def uses_prefilled_windows_stdin_bytes(api: Any, input_bytes: bytes | None) -> bool:
    """Return whether binary stdin can be frozen before a Windows child exists."""

    return api._is_windows() and len(input_bytes or b"") <= api._WINDOWS_PREFILLED_STDIN_BYTES


def spawn_owned_process(
    api: Any,
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_text: str | None,
) -> subprocess.Popen[str]:
    """Launch text I/O without allowing compatibility seams to weaken containment."""

    if not isinstance(process_argv, PreparedProcessArgv):
        raise TypeError("owned process argv must carry a frozen executable identity")
    return api._process._spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
    )


def spawn_owned_binary_process(
    api: Any,
    process_argv: PreparedProcessArgv,
    *,
    cwd: str | None,
    env: dict[str, str],
    input_bytes: bytes | None,
) -> subprocess.Popen[bytes]:
    """Launch binary I/O without allowing compatibility seams to weaken containment."""

    if not isinstance(process_argv, PreparedProcessArgv):
        raise TypeError("owned process argv must carry a frozen executable identity")
    return api._process._spawn_owned_binary_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
    )


def prepare_owned_process_argv(
    api: Any,
    argv: Sequence[str],
    *,
    forbidden_roots: Sequence[str | os.PathLike[str]],
) -> PreparedProcessArgv:
    """Prepare once or revalidate the complete receipt through facade seams."""

    if isinstance(argv, PreparedProcessArgv) and (
        argv.executable_identities or argv.persistent_artifact_identities
    ):
        api.revalidate_process_argv(argv)
        if forbidden_roots:
            candidate = PreparedProcessArgv(argv, artifact_paths=argv.artifact_paths)
            if argv.persistent_artifact_identities:
                verified = api.freeze_persistent_process_argv(
                    candidate,
                    platform_name=argv.frozen_platform,
                    forbidden_roots=forbidden_roots,
                )
                if verified.persistent_artifact_identities != argv.persistent_artifact_identities:
                    raise OSError("pre-frozen persistent executable identity changed")
            else:
                verified = api.freeze_process_argv(
                    candidate,
                    platform_name=argv.frozen_platform,
                    forbidden_roots=forbidden_roots,
                )
                if verified.executable_identities != argv.executable_identities:
                    raise OSError("pre-frozen executable identity changed")
        return argv
    prepared = api.prepare_process_argv(argv)
    if not isinstance(prepared, PreparedProcessArgv):
        prepared = PreparedProcessArgv(prepared, artifact_paths=(prepared[0],))
    return api.freeze_process_argv(prepared, forbidden_roots=forbidden_roots)


def quiesce_owned_process(api: Any, state: Any) -> None:
    """Drain legacy-injected I/O and reject a non-quiescent process tree."""

    strongly_contained = getattr(state.process, "_agency_strong_containment", False)
    state.descendants_detected = bool(
        state.descendants_detected
        or (not strongly_contained and api._posix_process_group_active(state.process))
    )
    if state.timeout_error is None and not api._is_windows() and state.descendants_detected:
        api._terminate_owned_process_tree(state.process)
    api._join_owned_process_io(state, api._DRAIN_GRACE_SECONDS)
    if strongly_contained:
        try:
            messages = api._process._collect_linux_supervisor_status(state.process)
        except OSError as exc:
            state.containment_error = str(exc)
        else:
            state.descendants_detected = bool(
                state.descendants_detected or "DESCENDANTS" in messages
            )
            failures = [message for message in messages if message.startswith("ERROR:")]
            if failures:
                state.containment_error = failures[-1]
    state.descendants_detected = bool(
        state.descendants_detected or api._windows_job_has_active_processes(state.windows_job)
    )
    state.io_lingering = any(thread.is_alive() for thread in state.threads())
    if state.descendants_detected or state.io_lingering or state.containment_error:
        api._terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
        api._join_owned_process_io(state, 5)


def _claim_windows_containment(api: Any, state: Any) -> None:
    if not api._is_windows():
        return
    if api._process._is_atomic_windows_process(state.process):
        state.windows_job = api._process._claim_atomic_windows_job(state.process)
        if state.windows_job is None:
            raise OSError("could not claim an atomically contained Windows process")
        return
    raise OSError("compatibility process launcher did not provide atomic Windows containment")


def _release_owned_process(api: Any, state: Any) -> None:
    if api._is_windows():
        job = state.windows_job
        if job is None or not api._process._resume_atomic_windows_process(state.process):
            raise OSError("could not resume an atomically contained Windows process")
        release = getattr(api._process, "_release_atomic_windows_job", None)
        if callable(release):
            release(state.process, job)
        return
    if not getattr(state.process, "_agency_strong_containment", False):
        return
    if _linux.descriptor_number(getattr(state.process, "_agency_supervisor_go_fd", None)) is None:
        raise OSError("Linux process supervisor GO gate is unavailable")
    _linux.release_go(state.process)


def _establish_windows_containment(api: Any, state: Any) -> None:
    """Compatibility helper retaining the historical claim-and-resume surface."""

    _claim_windows_containment(api, state)
    if api._is_windows():
        _release_owned_process(api, state)


def _wait_for_owned_process(api: Any, state: Any, timeout: float) -> None:
    try:
        state.process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        api._terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
        state.timeout_error = exc


def _raise_for_incomplete_process(state: Any, timeout: float) -> None:
    if state.timeout_error is not None:
        raise subprocess.TimeoutExpired(state.argv, timeout) from state.timeout_error
    if state.containment_error:
        raise OSError(f"owned process containment failed: {state.containment_error}")
    if state.descendants_detected or state.io_lingering:
        raise OSError(
            "owned process descendants outlived the parent process or I/O workers remained active"
        )


def _cleanup_owned_process(api: Any, state: Any) -> None:
    process_core = getattr(api, "_process", None)
    cleanups: list[Callable[[], None]] = []
    if process_core is not None:
        cancel_go = getattr(process_core, "_cancel_linux_supervisor_go", None)
        close_go = getattr(
            process_core,
            "_close_linux_supervisor_go_descriptor",
            None,
        )
        if callable(cancel_go):
            cleanups.append(lambda: cancel_go(state.process))
        if callable(close_go):
            cleanups.append(lambda: close_go(state.process))
    cleanups.append(
        lambda: api._terminate_owned_process_tree(
            state.process,
            windows_job=state.windows_job,
        )
    )
    if process_core is not None:
        cleanups.append(
            lambda: process_core._close_atomic_windows_process_resources(state.process),
        )
    cleanups.extend(
        [
            lambda: api._join_owned_process_io(state, 5),
            lambda: api._close_process_pipes(state.process),
        ]
    )
    errors: list[BaseException] = []
    for cleanup in cleanups:
        try:
            cleanup()
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise errors[0]


def _complete_owned_process(
    api: Any,
    state: Any,
    *,
    stdout: Any,
    stderr: Any,
    timeout: float,
    start_io: Callable[[], None],
) -> subprocess.CompletedProcess[Any]:
    try:
        process_core = getattr(api, "_process", None)
        claim = getattr(process_core, "_claim_linux_completion_owner", None)
        if callable(claim):
            claim(state.process)
        _claim_windows_containment(api, state)
        start_io()
        _release_owned_process(api, state)
        _wait_for_owned_process(api, state, timeout)
        api._quiesce_owned_process(state)
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
            _cleanup_owned_process(api, state)
        except BaseException as cleanup_exc:
            _add_exception_note(exc, f"owned process cleanup failed: {cleanup_exc}")
        raise
    finally:
        process_core = getattr(api, "_process", None)
        if process_core is not None:
            with suppress(BaseException):
                process_core._close_linux_supervisor_status(state.process)
            with suppress(BaseException):
                process_core._close_atomic_windows_process_resources(state.process)
        if state.windows_job is not None:
            with suppress(BaseException):
                state.windows_job.close()


def run_owned_process(
    api: Any,
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
    """Run text I/O using only explicitly injected legacy facade seams."""

    process_argv = api._prepare_owned_process_argv(
        argv,
        forbidden_roots=forbidden_roots,
    )
    process = api._spawn_owned_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_text=input_text,
    )
    state = api._OwnedProcessState(
        argv=process_argv,
        process=process,
        stdin_preloaded=api._uses_prefilled_windows_stdin(input_text),
    )

    def start_io() -> None:
        process_core = getattr(api, "_process", None)
        core_start = getattr(process_core, "_start_owned_text_io", None)
        if (
            callable(core_start)
            and api._start_process_io_threads is process_core._start_process_io_threads
        ):
            core_start(
                state,
                stdout=stdout,
                stderr=stderr,
                input_text=input_text,
            )
            return
        (
            state.stdout_thread,
            state.stderr_thread,
            state.stdin_thread,
        ) = api._start_process_io_threads(
            state.process,
            stdout=stdout,
            stderr=stderr,
            input_text=None if state.stdin_preloaded else input_text,
            windows_job=state.windows_job,
        )

    return _complete_owned_process(
        api,
        state,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        start_io=start_io,
    )


def run_owned_binary_process(
    api: Any,
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
    """Run binary I/O using only explicitly injected legacy facade seams."""

    process_argv = api._prepare_owned_process_argv(
        argv,
        forbidden_roots=forbidden_roots,
    )
    process = api._spawn_owned_binary_process(
        process_argv,
        cwd=cwd,
        env=env,
        input_bytes=input_bytes,
    )
    state = api._OwnedProcessState(
        argv=process_argv,
        process=process,
        stdin_preloaded=api._uses_prefilled_windows_stdin_bytes(input_bytes),
    )

    def start_io() -> None:
        process_core = getattr(api, "_process", None)
        core_start = getattr(process_core, "_start_owned_binary_io", None)
        if (
            callable(core_start)
            and api._start_binary_process_io_threads
            is process_core._start_binary_process_io_threads
        ):
            core_start(
                state,
                stdout=stdout,
                stderr=stderr,
                input_bytes=input_bytes,
            )
            return
        (
            state.stdout_thread,
            state.stderr_thread,
            state.stdin_thread,
        ) = api._start_binary_process_io_threads(
            state.process,
            stdout=stdout,
            stderr=stderr,
            input_bytes=None if state.stdin_preloaded else input_bytes,
            windows_job=state.windows_job,
        )

    return _complete_owned_process(
        api,
        state,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
        start_io=start_io,
    )
