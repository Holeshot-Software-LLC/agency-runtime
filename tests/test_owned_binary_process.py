"""Focused contracts for reusable frozen argv and byte-exact owned processes."""

from __future__ import annotations

import errno
import io
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import time
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import owned_process, process_argv
from agency_runtime.core.delegation import backend_process, backends
from agency_runtime.core.owned_process_capture import OwnedProcessContainmentError
from agency_runtime.core.process_argv import PreparedProcessArgv
from tests.runtime_support import trusted_test_interpreter, wait_for_process_exit


def _owned_pipe_pair(read_descriptor: int, write_descriptor: int) -> Any:
    pair = owned_process._OwnedPipePair()
    pair._storage[0] = read_descriptor
    pair._storage[1] = write_descriptor
    return pair


class _NonClosingBytesIO(io.BytesIO):
    def close(self) -> None:
        self.flush()


class _BrokenBytesStream:
    def __init__(self) -> None:
        self.closed = False

    def write(self, _value: bytes) -> int:
        raise BrokenPipeError

    def flush(self) -> None:
        raise OSError("closed")

    def close(self) -> None:
        self.closed = True


def _write_executable(path: Path) -> Path:
    path.write_bytes(b"executable")
    if os.name != "nt":
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _frozen_interpreter(*arguments: str) -> PreparedProcessArgv:
    return backends.freeze_process_argv(
        backends.prepare_process_argv([str(trusted_test_interpreter()), *arguments])
    )


def _linux_process_children(pid: int) -> set[int]:
    try:
        payload = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="ascii")
    except OSError:
        return set()
    return {int(value) for value in payload.split()}


def _wait_for_runner_evidence(
    runner: subprocess.Popen[str],
    predicate: Any,
    *,
    timeout: float = 10,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        if runner.poll() is not None:
            stdout, stderr = runner.communicate()
            raise AssertionError(
                f"owned-process runner exited early ({runner.returncode}): {stdout!r} {stderr!r}"
            )
        time.sleep(0.01)
    raise AssertionError("timed out waiting for Linux owned-process evidence")


def _pid_files_ready(*paths: Path) -> bool:
    """Return only after every PID file contains one complete positive integer."""

    for path in paths:
        try:
            if int(path.read_text(encoding="ascii")) <= 0:
                return False
        except (OSError, UnicodeError, ValueError):
            return False
    return True


def _linux_pidfds_are_gone(descriptors: list[int]) -> bool:
    for descriptor in descriptors:
        try:
            signal.pidfd_send_signal(descriptor, 0, None, 0)
        except ProcessLookupError:
            continue
        return False
    return True


def test_prepared_argv_bind_replaces_arguments_and_preserves_receipts() -> None:
    prepared = PreparedProcessArgv(
        ["launcher", "--wrapper", "tool.py", "old"],
        artifact_paths=("launcher", "tool.py"),
    )
    transient = (object(),)
    persistent = (object(),)
    prepared.executable_identities = transient  # type: ignore[assignment]
    prepared.persistent_artifact_identities = persistent  # type: ignore[assignment]
    prepared.frozen_launcher = ("launcher", "--wrapper", "tool.py")
    prepared.frozen_platform = "posix"

    positional = prepared.bind("new", "value")
    sequence = prepared.bind(["other"])
    replaced = prepared.with_arguments([])

    assert prepared == ["launcher", "--wrapper", "tool.py", "old"]
    assert positional == ["launcher", "--wrapper", "tool.py", "new", "value"]
    assert sequence == ["launcher", "--wrapper", "tool.py", "other"]
    assert replaced == ["launcher", "--wrapper", "tool.py"]
    assert positional.executable_identities is transient
    assert positional.persistent_artifact_identities is persistent
    assert positional.frozen_launcher is prepared.frozen_launcher
    assert positional.frozen_platform == "posix"


def test_prepared_argv_bind_uses_unfrozen_prefix_and_rejects_bad_arguments() -> None:
    prepared = PreparedProcessArgv(
        ["launcher", "tool.py", "old"],
        artifact_paths=("launcher", "tool.py"),
    )

    assert prepared.with_arguments(["new"]) == ["launcher", "tool.py", "new"]
    with pytest.raises(TypeError, match="sequence of strings"):
        prepared.with_arguments("argument")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="sequence of strings"):
        prepared.bind([1])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="sequence of strings"):
        prepared.bind(["one"], "two")  # type: ignore[arg-type]
    for invalid in ("", "bad\x00argument"):
        with pytest.raises(ValueError, match="invalid item"):
            prepared.bind(invalid)


@pytest.mark.parametrize(
    ("values", "artifacts", "message"),
    [
        (["python"], (), "non-empty sequence"),
        (["python"], ("git",), "must be argv\\[0\\]"),
        (["python", "script"], ("python", "git"), "exactly once"),
        (["python", "python"], ("python",), "exactly once"),
        (
            ["python", "first", "second"],
            ("python", "second", "first"),
            "strictly increasing",
        ),
    ],
)
def test_prepared_argv_construction_rejects_ambiguous_artifact_mapping(
    values: list[str],
    artifacts: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        PreparedProcessArgv(values, artifact_paths=artifacts)


def test_prepared_argv_constructor_rejects_malformed_sequences() -> None:
    for values in ("python", [], ["python", 1]):
        with pytest.raises(TypeError, match="argv must be a non-empty sequence"):
            PreparedProcessArgv(values, artifact_paths=("python",))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="argv contains an invalid item"):
        PreparedProcessArgv(["py\x00thon"], artifact_paths=("py\x00thon",))

    for artifacts in ("python", [1]):
        with pytest.raises(TypeError, match="artifact paths must be a non-empty sequence"):
            PreparedProcessArgv(["python"], artifact_paths=artifacts)  # type: ignore[arg-type]
    for artifacts in (("",), ("git\x00",)):
        with pytest.raises(ValueError, match="artifact paths contain an invalid item"):
            PreparedProcessArgv(["python"], artifact_paths=artifacts)


def test_prepared_argv_freeze_rejects_mutated_mapping_and_boundary() -> None:
    python = str(trusted_test_interpreter())

    empty = PreparedProcessArgv([python], artifact_paths=(python,))
    empty.clear()
    with pytest.raises(ValueError, match="argv contains an invalid item"):
        process_argv.freeze_process_argv(empty)

    artifacts = PreparedProcessArgv([python], artifact_paths=(python,))
    artifacts.artifact_paths = []  # type: ignore[assignment]
    with pytest.raises(ValueError, match="artifact paths contain an invalid item"):
        process_argv.freeze_process_argv(artifacts)

    boundary = PreparedProcessArgv([python], artifact_paths=(python,))
    boundary.argument_offset = 2
    with pytest.raises(ValueError, match="artifact boundary"):
        process_argv.freeze_process_argv(boundary)


@pytest.mark.parametrize(
    "freezer",
    [
        process_argv.freeze_process_argv,
        process_argv.freeze_persistent_process_argv,
    ],
)
def test_freeze_rejects_unrelated_git_artifact_for_python_launcher(
    freezer: Any,
) -> None:
    python = str(trusted_test_interpreter())
    prepared = PreparedProcessArgv([python], artifact_paths=(python,))
    prepared.artifact_paths = ("git",)

    with pytest.raises(ValueError, match="must be argv\\[0\\]"):
        freezer(prepared)


@pytest.mark.parametrize("persistent", [False, True])
def test_revalidation_rejects_unrelated_git_identity_for_python_launcher(
    persistent: bool,
) -> None:
    python = str(trusted_test_interpreter())
    prepared = PreparedProcessArgv([python], artifact_paths=(python,))
    if persistent:
        process_argv.freeze_persistent_process_argv(prepared)
        identity = prepared.persistent_artifact_identities[0]
        prepared.persistent_artifact_identities = (
            replace(identity, lexical_path="git", resolved_path="git"),
        )
        message = "persistent executable identities do not cover"
    else:
        process_argv.freeze_process_argv(prepared)
        identity = prepared.executable_identities[0]
        prepared.executable_identities = (replace(identity, path="git"),)
        message = "executable identities do not cover"

    with pytest.raises(OSError, match=message):
        prepared.revalidate()


def test_revalidation_rejects_missing_or_changed_frozen_launcher_prefix() -> None:
    python = str(trusted_test_interpreter())
    prepared = process_argv.freeze_process_argv(
        PreparedProcessArgv([python], artifact_paths=(python,))
    )
    prepared.frozen_launcher = None
    with pytest.raises(OSError, match="no frozen launcher prefix"):
        prepared.revalidate()

    prepared.frozen_launcher = (python,)
    prepared[0] = "git"
    prepared.artifact_paths = ("git",)
    with pytest.raises(OSError, match="launcher changed"):
        prepared.revalidate()


def test_persistent_freeze_preserves_lexical_launcher_and_revalidates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_executable(tmp_path / ("python.exe" if os.name == "nt" else "python"))
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )
    prepared = PreparedProcessArgv(
        [str(executable.absolute()), "old"],
        artifact_paths=(str(executable.absolute()),),
    )

    frozen = prepared.freeze_persistent()
    bound = frozen.bind("new")
    bound.revalidate()

    assert frozen[0] == str(executable.absolute())
    assert not frozen.executable_identities
    assert frozen.persistent_artifact_identities
    assert bound.persistent_artifact_identities is frozen.persistent_artifact_identities
    bound[0] = str(executable.with_name("other"))
    with pytest.raises(OSError, match="launcher changed"):
        bound.revalidate()
    frozen.executable_identities = (object(),)  # type: ignore[assignment]
    with pytest.raises(OSError, match="conflicting frozen"):
        frozen.revalidate()


def test_persistent_freeze_enforces_forbidden_resolved_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = _write_executable(tmp_path / ("tool.exe" if os.name == "nt" else "tool"))
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )
    prepared = PreparedProcessArgv(
        [str(executable.absolute())],
        artifact_paths=(str(executable.absolute()),),
    )

    with pytest.raises(OSError, match="target repository"):
        process_argv.freeze_persistent_process_argv(
            prepared,
            platform_name=os.name,
            forbidden_roots=(tmp_path,),
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX lexical symlink contract")
@pytest.mark.parametrize("persistent", [False, True])
def test_freeze_rejects_repo_local_symlink_to_external_interpreter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persistent: bool,
) -> None:
    repository = tmp_path / "repository"
    external = tmp_path / "external"
    repository.mkdir()
    external.mkdir()
    target = _write_executable(external / "python-real")
    launcher = repository / "python"
    launcher.symlink_to(target)
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )
    prepared = PreparedProcessArgv(
        [str(launcher.absolute())],
        artifact_paths=(str(launcher.absolute()),),
    )
    freezer = (
        process_argv.freeze_persistent_process_argv
        if persistent
        else process_argv.freeze_process_argv
    )

    with pytest.raises(OSError, match="target repository"):
        freezer(
            prepared,
            platform_name="posix",
            forbidden_roots=(repository,),
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX virtualenv lexical symlink contract")
def test_persistent_freeze_keeps_posix_virtualenv_symlink_spelling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _write_executable(tmp_path / "python-real")
    launcher = tmp_path / "python"
    launcher.symlink_to(target.name)
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_a, **_kw: None)
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_a, **_kw: None,
    )
    prepared = PreparedProcessArgv(
        [str(launcher.absolute()), "-I"],
        artifact_paths=(str(launcher.absolute()),),
    )

    process_argv.freeze_persistent_process_argv(prepared, platform_name="posix")

    assert prepared[0] == str(launcher.absolute())
    assert prepared.persistent_artifact_identities[0].resolved_path == str(target.resolve())


def test_binary_stream_helpers_preserve_bytes_and_bound_storage() -> None:
    assert backend_process._stream_bytes(None) == b""
    assert backend_process._stream_bytes(b"raw") == b"raw"
    assert backend_process._stream_bytes(bytearray(b"mutable")) == b"mutable"
    assert backend_process._stream_bytes(memoryview(b"view")) == b"view"
    assert backend_process._stream_bytes("text") == b"text"
    assert backend_process._bounded_bytes(b"ok", 2) == (b"ok", False)
    assert backend_process._bounded_bytes(b"overflow", 3) == (b"\n..", True)
    assert backend_process._bounded_bytes(b"x" * 100, 40) == (
        b"x" * 9 + b"\n...[truncated by output limit]",
        True,
    )

    capture = backend_process._BoundedBytesCapture(3)
    assert capture.write(b"abcdef") == 6
    assert capture.write(b"discarded") == 9
    assert capture.read() == b"abcd"
    assert capture.read(2) == b"ab"
    assert capture.flush() is None
    assert capture.seek(0) == 0


def test_binary_stdin_writer_is_exact_and_tolerates_early_exit() -> None:
    stream = _NonClosingBytesIO()
    backend_process._write_process_stdin_bytes(SimpleNamespace(stdin=stream), b"a\x00b\n")
    assert stream.getvalue() == b"a\x00b\n"

    broken = _BrokenBytesStream()
    backend_process._write_process_stdin_bytes(SimpleNamespace(stdin=broken), b"payload")
    assert broken.closed is True
    backend_process._write_process_stdin_bytes(SimpleNamespace(stdin=None), b"payload")


def test_binary_prefilled_pipe_is_exact_and_closes_writer() -> None:
    descriptor = backends._create_prefilled_stdin_pipe_bytes(b"payload\x00")
    try:
        assert os.read(descriptor.fileno(), 100) == b"payload\x00"
        assert os.read(descriptor.fileno(), 1) == b""
    finally:
        descriptor.close()


def test_binary_prefilled_pipe_fails_closed_on_write_or_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(
        owned_process._OwnedPipePair,
        "create",
        classmethod(lambda _cls: _owned_pipe_pair(10, 11)),
    )
    monkeypatch.setattr(backends.os, "write", lambda _fd, _payload: 1)
    monkeypatch.setattr(backends.os, "close", closed.append)
    with pytest.raises(OSError, match="prefill child stdin"):
        backends._create_prefilled_stdin_pipe_bytes(b"payload")
    assert closed == [10, 11]

    closed.clear()
    monkeypatch.setattr(backends.os, "write", lambda _fd, payload: len(payload))

    def close(fd: int) -> None:
        if fd == 11:
            raise OSError("writer close failed")
        closed.append(fd)

    monkeypatch.setattr(backends.os, "close", close)
    with pytest.raises(OSError, match="writer close failed"):
        backends._create_prefilled_stdin_pipe_bytes(None)
    assert closed == [10]


def test_binary_io_threads_close_empty_stdin_and_drain_exact_bytes() -> None:
    stdin = _NonClosingBytesIO()
    stdout_source = _NonClosingBytesIO(b"stdout\x00")
    stderr_source = _NonClosingBytesIO(b"stderr\xff")
    process = SimpleNamespace(stdin=stdin, stdout=stdout_source, stderr=stderr_source)
    stdout = backend_process._BoundedBytesCapture(20)
    stderr = backend_process._BoundedBytesCapture(20)

    threads = backend_process._start_binary_process_io_threads(
        process,
        stdout=stdout,
        stderr=stderr,
        input_bytes=None,
        windows_job=None,
    )
    for thread in threads[:2]:
        thread.join(timeout=1)

    assert threads[2] is None
    assert stdin.getvalue() == b""
    assert stdout.read() == b"stdout\x00"
    assert stderr.read() == b"stderr\xff"


@pytest.mark.parametrize("interruption", [RuntimeError("thread"), KeyboardInterrupt()])
def test_binary_io_thread_start_failure_cleans_process(
    monkeypatch: pytest.MonkeyPatch,
    interruption: BaseException,
) -> None:
    class Started:
        def start(self) -> None:
            return None

    class Broken:
        def start(self) -> None:
            raise interruption

    started = Started()
    process = object()
    observed: list[tuple[object, list[object]]] = []
    monkeypatch.setattr(
        backend_process,
        "_create_binary_process_io_threads",
        lambda *_a, **_kw: (Broken(), started, None),
    )
    monkeypatch.setattr(
        backend_process,
        "_cleanup_partial_io_start",
        lambda owned, *, windows_job, started: observed.append((owned, started)),
    )

    expected = OSError if isinstance(interruption, Exception) else KeyboardInterrupt
    with pytest.raises(expected):
        backend_process._start_binary_process_io_threads(
            process,  # type: ignore[arg-type]
            stdout=object(),
            stderr=object(),
            input_bytes=b"payload",
            windows_job=None,
        )
    assert observed == [(process, [])]


def test_binary_io_thread_failure_after_one_worker_started_cleans_and_joins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Started:
        def __init__(self) -> None:
            self.started = False

        def start(self) -> None:
            self.started = True

    class Broken:
        def start(self) -> None:
            raise RuntimeError("thread")

    started = Started()
    process = object()
    observed: list[tuple[object, list[object]]] = []
    monkeypatch.setattr(
        backend_process,
        "_create_binary_process_io_threads",
        lambda *_a, **_kw: (started, Broken(), None),
    )
    monkeypatch.setattr(
        backend_process,
        "_cleanup_partial_io_start",
        lambda owned, *, windows_job, started: observed.append((owned, started)),
    )

    with pytest.raises(OSError, match="binary process I/O workers"):
        backend_process._start_binary_process_io_threads(
            process,  # type: ignore[arg-type]
            stdout=object(),
            stderr=object(),
            input_bytes=b"payload",
            windows_job=None,
        )

    assert started.started is True
    assert observed == [(process, [started])]


@pytest.mark.parametrize(
    ("changes", "error", "message"),
    [
        ({"argv": []}, TypeError, "non-empty"),
        ({"argv": [""]}, ValueError, "invalid item"),
        ({"timeout": True}, ValueError, "finite"),
        ({"max_input_bytes": 0}, ValueError, "max_input_bytes"),
        ({"max_stdout_bytes": 0}, ValueError, "max_stdout_bytes"),
        ({"max_stderr_bytes": 0}, ValueError, "max_stderr_bytes"),
        ({"input_bytes": "text"}, TypeError, "must be bytes"),
        ({"input_bytes": b"too-long", "max_input_bytes": 2}, ValueError, "exceeds"),
    ],
)
def test_bounded_binary_runner_rejects_invalid_contracts(
    changes: dict[str, Any],
    error: type[Exception],
    message: str,
) -> None:
    arguments: dict[str, Any] = {
        "argv": ["tool"],
        "process_runner": lambda *_a, **_kw: subprocess.CompletedProcess([], 0),
        "timeout": 1,
    }
    arguments.update(changes)
    with pytest.raises(error, match=message):
        backend_process.run_bounded_binary_process(**arguments)


@pytest.mark.parametrize(
    ("raised", "returncode", "timed_out", "category"),
    [
        (subprocess.TimeoutExpired("tool", 1), 124, True, "timeout"),
        (FileNotFoundError(), 127, False, "not-found"),
        (PermissionError(), 126, False, "permission"),
        (OwnedProcessContainmentError("secret"), 1, False, "containment"),
        (OSError(), 1, False, "launch"),
    ],
)
def test_bounded_binary_runner_normalizes_process_failures(
    raised: Exception,
    returncode: int,
    timed_out: bool,
    category: str,
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise raised

    result = backend_process.run_bounded_binary_process(
        ["tool"],
        process_runner=fail,
        timeout=1,
    )

    assert result.returncode == returncode
    assert result.timed_out is timed_out
    assert result.failure_category == category
    assert result.stdout == result.stderr == b""


def test_bounded_binary_runner_validates_and_propagates_cancellation() -> None:
    with pytest.raises(TypeError, match=r"threading\.Event"):
        owned_process.run_bounded_binary_process(
            ["tool"],
            process_runner=lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0),
            timeout=1,
            cancel_event=object(),  # type: ignore[arg-type]
        )

    event = threading.Event()
    observed: list[threading.Event] = []

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        observed.append(kwargs["cancel_event"])
        completed = subprocess.CompletedProcess(argv, 130)
        completed.cancelled = True
        return completed

    result = owned_process.run_bounded_binary_process(
        ["tool"],
        process_runner=run,
        timeout=1,
        cancel_event=event,
    )

    assert observed == [event]
    assert result.returncode == 130
    assert result.cancelled is True
    assert result.timed_out is False
    assert result.failure_category == "cancelled"


@pytest.mark.parametrize(
    ("payload", "limit", "tail", "truncated"),
    [
        (b"under-limit", 32, b"under-limit", False),
        (b"HEAD" + b"x" * 100 + b"TAIL", 48, b"TAIL", True),
        (b"HEAD" + b"x" * 100 + b"TAIL", 8, b"\n...[tru", True),
    ],
)
def test_public_binary_facade_opt_in_capture_retains_bounded_tail(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    limit: int,
    tail: bytes,
    truncated: bool,
) -> None:
    def strict_runner(
        argv: list[str],
        *,
        cwd: str | None,
        stdout: Any,
        stderr: Any,
        timeout: float,
        env: dict[str, str],
        input_bytes: bytes | None,
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd, timeout, env, input_bytes
        stdout.write(payload)
        stderr.write(payload)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(backends, "_run_owned_binary_process", strict_runner)
    result = backends.run_bounded_binary_process(
        ["tool"],
        timeout=1,
        max_stdout_bytes=limit,
        max_stderr_bytes=limit,
        retain_output_tail=True,
    )

    assert len(result.stdout) <= limit and len(result.stderr) <= limit
    assert result.stdout.endswith(tail) and result.stderr.endswith(tail)
    assert result.stdout_truncated is truncated
    assert result.stderr_truncated is truncated


def test_public_binary_facade_default_remains_head_only_and_legacy_runner_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def strict_runner(
        argv: list[str],
        *,
        cwd: str | None,
        stdout: Any,
        stderr: Any,
        timeout: float,
        env: dict[str, str],
        input_bytes: bytes | None,
    ) -> subprocess.CompletedProcess[bytes]:
        del cwd, timeout, env, input_bytes
        stdout.write(b"HEAD" + b"x" * 100 + b"TAIL")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(backends, "_run_owned_binary_process", strict_runner)
    result = backends.run_bounded_binary_process(
        ["tool"],
        timeout=1,
        max_stdout_bytes=48,
    )

    assert result.stdout.startswith(b"HEAD")
    assert not result.stdout.endswith(b"TAIL")
    assert result.stdout_truncated is True


def test_public_binary_facade_propagates_pre_and_inflight_cancellation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = threading.Event()
    event.set()
    pre_cancelled = backends.run_bounded_binary_process(["tool"], timeout=1, cancel_event=event)
    assert pre_cancelled.failure_category == "cancelled"

    event.clear()
    observed: list[threading.Event] = []

    def cancel_runner(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        observed.append(kwargs["cancel_event"])
        completed = subprocess.CompletedProcess(argv, 130)
        completed.cancelled = True
        return completed

    monkeypatch.setattr(backends, "_run_owned_binary_process", cancel_runner)
    in_flight = backends.run_bounded_binary_process(["tool"], timeout=1, cancel_event=event)
    assert observed == [event]
    assert in_flight.cancelled is True
    assert in_flight.failure_category == "cancelled"


def test_bounded_binary_runner_pre_cancel_does_not_spawn() -> None:
    event = threading.Event()
    event.set()

    result = owned_process.run_bounded_binary_process(
        ["tool"],
        process_runner=lambda *_args, **_kwargs: pytest.fail("cancelled call spawned"),
        timeout=1,
        cancel_event=event,
    )

    assert result.returncode == 130
    assert result.cancelled is True
    assert result.stdout == result.stderr == b""


@pytest.mark.parametrize(
    ("residual_descendants", "io_lingering"),
    [(True, False), (False, True)],
)
def test_cancelled_owned_process_rejects_failed_cleanup(
    residual_descendants: bool,
    io_lingering: bool,
) -> None:
    state = SimpleNamespace(
        timeout_error=None,
        containment_error=None,
        cancelled=True,
        descendants_detected=True,
        residual_descendants=residual_descendants,
        io_lingering=io_lingering,
    )

    with pytest.raises(OSError, match="did not quiesce"):
        owned_process._raise_for_incomplete_process(state, 1)


def test_cancelled_owned_process_allows_reaped_historical_descendant() -> None:
    state = SimpleNamespace(
        timeout_error=None,
        containment_error=None,
        cancelled=True,
        descendants_detected=True,
        residual_descendants=False,
        io_lingering=False,
    )

    owned_process._raise_for_incomplete_process(state, 1)


def test_bounded_binary_runner_copies_environment_and_truncates_exact_bytes() -> None:
    observed: dict[str, Any] = {}
    prepared = PreparedProcessArgv(["tool"], artifact_paths=("tool",))

    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        observed["argv"] = argv
        observed.update(kwargs)
        kwargs["stdout"].write(b"stdout\x00overflow")
        kwargs["stderr"].write(b"stderr\xffoverflow")
        return subprocess.CompletedProcess(argv, 7)

    environment = {"PATH": "safe"}
    result = backend_process.run_bounded_binary_process(
        prepared,
        process_runner=run,
        timeout=2,
        env=environment,
        input_bytes=b"input\x00",
        max_stdout_bytes=8,
        max_stderr_bytes=10,
    )

    assert observed["argv"] is prepared
    assert observed["env"] == environment
    assert observed["env"] is not environment
    assert observed["input_bytes"] == b"input\x00"
    assert result.returncode == 7
    assert result.stdout == b"\n...[tru"
    assert result.stderr == b"\n...[trunc"
    assert result.stdout_truncated and result.stderr_truncated


def test_public_binary_runner_executes_byte_exact_input_and_output() -> None:
    command = _frozen_interpreter(
        "-c",
        (
            "import sys; data=sys.stdin.buffer.read(); "
            "sys.stdout.buffer.write(data); sys.stderr.buffer.write(b'\\xff')"
        ),
    )

    result = backends.run_bounded_binary_process(
        command,
        timeout=10,
        input_bytes=b"payload\x00\xfe",
    )

    assert result.returncode == 0
    assert result.stdout == b"payload\x00\xfe"
    assert result.stderr == b"\xff"
    assert result.timed_out is False


def test_lightweight_owned_process_import_does_not_load_delegation_or_yaml() -> None:
    source_root = Path(__file__).resolve().parents[1]
    script = (
        "import sys;"
        f"sys.path.insert(0, {str(source_root)!r});"
        "import agency_runtime.core.owned_process;"
        "assert not any(name.startswith('agency_runtime.core.delegation') "
        "for name in sys.modules);"
        "assert 'yaml' not in sys.modules"
    )

    completed = subprocess.run(
        [str(trusted_test_interpreter()), "-I", "-S", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr


def test_lightweight_public_runner_handles_large_exact_binary_stdin() -> None:
    payload = bytes(range(256)) * 257
    command = _frozen_interpreter(
        "-c",
        "import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data)",
    )

    result = owned_process.run_bounded_binary_process(
        command,
        timeout=10,
        input_bytes=payload,
        max_stdout_bytes=len(payload) + 1,
    )

    assert len(payload) > 4096
    assert result.returncode == 0
    assert result.stdout == payload
    assert not result.stdout_truncated


def test_lightweight_public_text_runner_preserves_streams_and_exit_status() -> None:
    command = _frozen_interpreter(
        "-c",
        (
            "import sys;"
            "data=sys.stdin.read();"
            "sys.stdout.write(data);"
            "sys.stderr.write('reason\\n');"
            "raise SystemExit(37)"
        ),
    )

    result = owned_process.run_bounded_process(
        command,
        timeout=10,
        input_text="exact\ntext\n",
    )

    assert result.returncode == 37
    assert result.stdout == "exact\ntext\n"
    assert result.stderr == "reason\n"
    assert result.timed_out is False


def test_lightweight_public_runner_drains_simultaneous_over_limit_streams() -> None:
    command = _frozen_interpreter(
        "-c",
        (
            "import sys, threading;"
            "payload=b'x'*262144;"
            "a=threading.Thread(target=sys.stdout.buffer.write,args=(payload,));"
            "b=threading.Thread(target=sys.stderr.buffer.write,args=(payload,));"
            "a.start();b.start();a.join();b.join()"
        ),
    )

    result = owned_process.run_bounded_binary_process(
        command,
        timeout=10,
        max_stdout_bytes=8192,
        max_stderr_bytes=4096,
    )

    assert result.returncode == 0
    assert len(result.stdout) == 8192
    assert len(result.stderr) == 4096
    assert result.stdout_truncated and result.stderr_truncated


def test_lightweight_public_runner_times_out_while_large_stdin_is_blocked() -> None:
    command = _frozen_interpreter("-c", "import time; time.sleep(30)")
    started = time.monotonic()

    result = owned_process.run_bounded_binary_process(
        command,
        timeout=0.05,
        input_bytes=b"x" * (1024 * 1024),
    )

    assert result.returncode == 124
    assert result.timed_out is True
    assert time.monotonic() - started < 8


def test_lightweight_public_runner_cancels_after_root_exit_and_reaps_descendant(
    tmp_path: Path,
) -> None:
    child_pid_file = tmp_path / "child.pid"
    root_exit_marker = tmp_path / "root-exit.marker"
    command = _frozen_interpreter(
        "-c",
        (
            "import os,pathlib,subprocess,sys;"
            "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
            "pathlib.Path(sys.argv[1]).write_text(str(child.pid),encoding='ascii');"
            "pathlib.Path(sys.argv[2]).write_text(str(os.getpid()),encoding='ascii')"
        ),
        str(child_pid_file),
        str(root_exit_marker),
    )
    event = threading.Event()
    results: list[Any] = []
    errors: list[BaseException] = []

    def invoke() -> None:
        try:
            results.append(
                owned_process.run_bounded_binary_process(
                    command,
                    timeout=10,
                    cancel_event=event,
                )
            )
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=invoke, name="owned-process-cancellation-test")
    worker.start()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not _pid_files_ready(
        child_pid_file,
        root_exit_marker,
    ):
        time.sleep(0.01)
    assert _pid_files_ready(child_pid_file, root_exit_marker)
    child_pid = int(child_pid_file.read_text(encoding="ascii"))
    time.sleep(0.05)
    assert worker.is_alive(), "owned runner completed before cancellation was requested"

    started = time.monotonic()
    event.set()
    worker.join(timeout=8)

    assert not worker.is_alive()
    assert time.monotonic() - started < 8
    assert errors == []
    assert len(results) == 1
    result = results[0]
    assert result.returncode == 130
    assert result.cancelled is True
    assert result.timed_out is False
    assert result.failure_category == "cancelled"
    assert wait_for_process_exit(child_pid)


def test_lightweight_public_runner_rejects_descendant_held_pipe() -> None:
    command = _frozen_interpreter(
        "-c",
        (
            "import subprocess, sys;"
            "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
            "print('parent complete')"
        ),
    )

    result = owned_process.run_bounded_binary_process(command, timeout=10)

    assert result.returncode == 1
    assert b"parent complete" in result.stdout


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux subreaper contract")
def test_linux_supervisor_kills_setsid_double_fork_without_touching_unrelated_child(
    tmp_path: Path,
) -> None:
    escaped_pid_file = tmp_path / "escaped.pid"
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    command = _frozen_interpreter(
        "-c",
        (
            "import os,time;"
            "child=os.fork();"
            "\nif child==0:"
            "\n os.setsid(); grandchild=os.fork();"
            f"\n if grandchild==0: open({str(escaped_pid_file)!r},'w').write(str(os.getpid()));"
            "\n if grandchild==0: time.sleep(30); os._exit(0);"
            "\n os._exit(0);"
            "\nos.waitpid(child,0)"
        ),
    )
    try:
        result = owned_process.run_bounded_binary_process(command, timeout=10)
        assert result.returncode == 1
        assert escaped_pid_file.is_file()
        escaped_pid = int(escaped_pid_file.read_text(encoding="utf-8"))
        with pytest.raises(ProcessLookupError):
            os.kill(escaped_pid, 0)
        assert unrelated.poll() is None
    finally:
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux seccomp contract")
def test_linux_target_can_signal_its_own_children_and_process_groups() -> None:
    machine = os.uname().machine.casefold()
    ioprio_number = (
        251
        if machine in {"x86_64", "amd64"}
        else 30
        if machine in {"aarch64", "arm64", "riscv64"}
        else None
    )
    if ioprio_number is None:
        pytest.skip(f"no audited resource syscall table for {machine}")
    sched_setattr_number = 314 if machine in {"x86_64", "amd64"} else 274
    command = _frozen_interpreter(
        "-c",
        f"""
import ctypes
import os
import resource
import signal
import subprocess
import sys

direct = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
resource.prlimit(direct.pid, resource.RLIMIT_NOFILE)
os.sched_setaffinity(direct.pid, os.sched_getaffinity(direct.pid))
libc = ctypes.CDLL(None, use_errno=True)
class SchedAttr(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("policy", ctypes.c_uint32),
        ("flags", ctypes.c_uint64),
        ("nice", ctypes.c_int32),
        ("priority", ctypes.c_uint32),
        ("runtime", ctypes.c_uint64),
        ("deadline", ctypes.c_uint64),
        ("period", ctypes.c_uint64),
    ]
attribute = SchedAttr()
attribute.size = ctypes.sizeof(SchedAttr)
if libc.syscall({sched_setattr_number}, direct.pid, ctypes.byref(attribute), 0) != 0:
    raise OSError(ctypes.get_errno(), "own-child sched_setattr")
os.sched_setparam(direct.pid, os.sched_param(0))
os.sched_setscheduler(direct.pid, os.SCHED_IDLE, os.sched_param(0))
os.setpriority(os.PRIO_PROCESS, direct.pid, 10)
if libc.syscall({ioprio_number}, 1, direct.pid, (2 << 13) | 7) != 0:
    raise OSError(ctypes.get_errno(), "own-child ioprio")
os.kill(direct.pid, signal.SIGTERM)
direct.wait(timeout=5)

group = subprocess.Popen(
    [sys.executable, "-c", "import time;time.sleep(30)"],
    start_new_session=True,
)
os.killpg(group.pid, signal.SIGTERM)
group.wait(timeout=5)

pidfd_child = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
descriptor = os.pidfd_open(pidfd_child.pid, 0)
signal.pidfd_send_signal(descriptor, signal.SIGTERM, None, 0)
os.close(descriptor)
pidfd_child.wait(timeout=5)
print("ordinary-signals-ok")
""",
    )

    result = owned_process.run_bounded_binary_process(command, timeout=10)

    assert result.returncode == 0
    assert result.stdout == b"ordinary-signals-ok\n"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux two-phase launch contract")
def test_linux_target_cannot_exec_before_go_and_pre_go_interrupt_cleans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "pre-go-target-ran"
    target = _frozen_interpreter(
        "-c",
        f"from pathlib import Path;import time;Path({str(marker)!r}).write_text('ran');time.sleep(30)",
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    try:
        time.sleep(0.1)
        assert not marker.exists()
        owned_process._claim_linux_completion_owner(process)
        cleanup_error = owned_process._abort_linux_supervisor(process)
        assert cleanup_error is None
        assert process.poll() is not None
        assert not marker.exists()
        assert unrelated.poll() is None
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        unrelated.kill()
        unrelated.wait(timeout=5)

    original_start = owned_process._start_owned_binary_io

    def interrupt_before_go(*args: object, **kwargs: object) -> None:
        del args, kwargs
        assert not marker.exists()
        raise KeyboardInterrupt

    monkeypatch.setattr(owned_process, "_start_owned_binary_io", interrupt_before_go)
    with pytest.raises(KeyboardInterrupt):
        owned_process.run_bounded_binary_process(target, timeout=10)
    assert not marker.exists()
    monkeypatch.setattr(owned_process, "_start_owned_binary_io", original_start)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux two-phase launch contract")
def test_linux_post_go_interrupt_reaps_execed_double_fork_and_preserves_sibling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    direct_pid_file = tmp_path / "post-go-direct.pid"
    escaped_pid_file = tmp_path / "post-go-escaped.pid"
    target = _frozen_interpreter(
        "-c",
        (
            "import os,time;"
            f"open({str(direct_pid_file)!r},'w').write(str(os.getpid()));"
            "child=os.fork();"
            "\nif child==0:"
            "\n os.setsid(); grandchild=os.fork();"
            f"\n if grandchild==0: open({str(escaped_pid_file)!r},'w').write(str(os.getpid()));"
            "\n if grandchild==0: time.sleep(30); os._exit(0);"
            "\n os._exit(0);"
            "\ntime.sleep(30)"
        ),
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    real_write = owned_process.os.write
    real_close = owned_process.os.close
    owned_pidfds: list[int] = []
    go_descriptor = -1

    def record_go_commit(descriptor: int, payload: bytes) -> int:
        nonlocal go_descriptor
        written = real_write(descriptor, payload)
        if payload == b"GO\n":
            go_descriptor = descriptor
        return written

    def interrupt_after_commit(descriptor: int) -> None:
        real_close(descriptor)
        if descriptor != go_descriptor:
            return
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not _pid_files_ready(
            direct_pid_file,
            escaped_pid_file,
        ):
            time.sleep(0.01)
        assert _pid_files_ready(direct_pid_file, escaped_pid_file)
        owned_pidfds.extend(
            os.pidfd_open(int(path.read_text(encoding="ascii")), 0)
            for path in (direct_pid_file, escaped_pid_file)
        )
        raise KeyboardInterrupt

    monkeypatch.setattr(owned_process.os, "write", record_go_commit)
    monkeypatch.setattr(owned_process.os, "close", interrupt_after_commit)
    try:
        with pytest.raises(KeyboardInterrupt):
            owned_process.run_bounded_binary_process(target, timeout=10)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not _linux_pidfds_are_gone(owned_pidfds):
            time.sleep(0.01)
        assert len(owned_pidfds) == 2
        assert _linux_pidfds_are_gone(owned_pidfds)
        assert unrelated.poll() is None
    finally:
        for descriptor in owned_pidfds:
            with suppress(ProcessLookupError):
                signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
            os.close(descriptor)
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux two-phase launch contract")
@pytest.mark.parametrize(
    ("go_payload", "expected"),
    [
        (b"", "go-invalid"),
        (b"NO\n", "go-invalid"),
    ],
    ids=["eof", "wrong"],
)
def test_linux_malformed_go_fails_with_complete_containment_receipt(
    go_payload: bytes,
    expected: str,
) -> None:
    target = _frozen_interpreter("-c", "raise SystemExit('must not execute')")
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    owned_process._claim_linux_completion_owner(process)
    descriptor = process._agency_supervisor_go_fd
    process._agency_supervisor_go_fd = None
    try:
        if go_payload:
            assert os.write(descriptor.fileno(), go_payload) == len(go_payload)
        descriptor.close()
        process.communicate(timeout=10)
        with pytest.raises(OSError, match=expected):
            owned_process._collect_linux_supervisor_status(process)
        assert process.returncode == 125
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        owned_process._close_linux_supervisor_status(process)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux two-phase launch contract")
def test_linux_go_timeout_and_exec_failure_report_complete_containment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import owned_process_linux as linux

    monkeypatch.setattr(
        linux,
        "SUPERVISOR_SOURCE",
        linux.SUPERVISOR_SOURCE.replace("GO_SECONDS = 5.0", "GO_SECONDS = 0.05", 1),
    )
    target = _frozen_interpreter("-c", "raise SystemExit('must not execute')")
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    owned_process._claim_linux_completion_owner(process)
    go_descriptor = process._agency_supervisor_go_fd
    try:
        process.communicate(timeout=10)
        with pytest.raises(OSError, match="go-timeout"):
            owned_process._collect_linux_supervisor_status(process)
    finally:
        process._agency_supervisor_go_fd = None
        with suppress(OSError):
            go_descriptor.close()

    missing = PreparedProcessArgv(
        ["/definitely/missing/agency-target"],
        artifact_paths=("/definitely/missing/agency-target",),
    )
    failed = owned_process._spawn_linux_supervisor(
        missing,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    state = owned_process._OwnedProcessState(argv=missing, process=failed)
    owned_process._claim_linux_completion_owner(failed)
    owned_process._release_owned_process(state)
    failed.communicate(timeout=10)
    with pytest.raises(OSError, match="target-exec-"):
        owned_process._collect_linux_supervisor_status(failed)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux native signal contract")
def test_linux_native_target_restores_python_ignored_signals_before_exec() -> None:
    sleep_path = Path("/bin/sleep")
    if not sleep_path.is_file():
        pytest.skip("native sleep executable is unavailable")
    target = backends.freeze_process_argv(
        backends.prepare_process_argv([str(sleep_path.resolve()), "30"])
    )
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    owned_process._claim_linux_completion_owner(process)
    state = owned_process._OwnedProcessState(argv=target, process=process)
    target_pid = 0
    try:
        owned_process._release_owned_process(state)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            children = _linux_process_children(process.pid)
            if len(children) == 1:
                target_pid = next(iter(children))
                break
            if process.poll() is not None:
                break
            time.sleep(0.01)
        assert target_pid
        status = Path(f"/proc/{target_pid}/status").read_text(encoding="ascii")
        ignored = int(
            next(
                line.split(":", 1)[1].strip()
                for line in status.splitlines()
                if line.startswith("SigIgn:")
            ),
            16,
        )
        restored = [signal.SIGPIPE]
        file_size_signal = getattr(signal, "SIGXFSZ", getattr(signal, "SIGXFZ", None))
        if file_size_signal is not None:
            restored.append(file_size_signal)
        for signum in restored:
            assert ignored & (1 << (int(signum) - 1)) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=10)
        with suppress(OSError):
            owned_process._collect_linux_supervisor_status(process)
        owned_process._close_linux_supervisor_status(process)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux seccomp contract")
def test_linux_target_cannot_destroy_supervisor_before_escapee_cleanup(
    tmp_path: Path,
) -> None:
    attack_file = tmp_path / "attack"
    direct_pid_file = tmp_path / "guard-direct.pid"
    supervisor_pid_file = tmp_path / "guard-supervisor.pid"
    escaped_pid_file = tmp_path / "guard-escaped.pid"
    results_file = tmp_path / "guard-results.json"
    syscall_numbers = {
        "x86_64": {
            "tkill": 200,
            "tgkill": 234,
            "rt_sigqueueinfo": 129,
            "rt_tgsigqueueinfo": 297,
            "pidfd_open": 434,
            "prlimit64": 302,
            "sched_setparam": 142,
            "sched_setscheduler": 144,
            "sched_setaffinity": 203,
            "sched_setattr": 314,
            "setpriority": 141,
            "ioprio_set": 251,
        },
        "aarch64": {
            "tkill": 130,
            "tgkill": 131,
            "rt_sigqueueinfo": 138,
            "rt_tgsigqueueinfo": 240,
            "pidfd_open": 434,
            "prlimit64": 261,
            "sched_setparam": 118,
            "sched_setscheduler": 119,
            "sched_setaffinity": 122,
            "sched_setattr": 274,
            "setpriority": 140,
            "ioprio_set": 30,
        },
        "riscv64": {
            "tkill": 130,
            "tgkill": 131,
            "rt_sigqueueinfo": 138,
            "rt_tgsigqueueinfo": 240,
            "pidfd_open": 434,
            "prlimit64": 261,
            "sched_setparam": 118,
            "sched_setscheduler": 119,
            "sched_setaffinity": 122,
            "sched_setattr": 274,
            "setpriority": 140,
            "ioprio_set": 30,
        },
    }
    machine = os.uname().machine.casefold()
    machine = "x86_64" if machine == "amd64" else "aarch64" if machine == "arm64" else machine
    if machine not in syscall_numbers:
        pytest.skip(f"no audited signal syscall table for {machine}")

    target_source = f"""
import ctypes
import errno
import json
import os
import signal
import time

supervisor_pid = os.getppid()
direct_pid = os.getpid()
intermediate = os.fork()
if intermediate == 0:
    os.setsid()
    escaped = os.fork()
    if escaped == 0:
        with open({str(escaped_pid_file)!r}, "w", encoding="ascii") as stream:
            stream.write(str(os.getpid()))
        time.sleep(30)
        os._exit(0)
    os._exit(0)
os.waitpid(intermediate, 0)
while not os.path.exists({str(escaped_pid_file)!r}):
    time.sleep(0.01)
with open({str(direct_pid_file)!r}, "w", encoding="ascii") as stream:
    stream.write(str(direct_pid))
with open({str(supervisor_pid_file)!r}, "w", encoding="ascii") as stream:
    stream.write(str(supervisor_pid))
while not os.path.exists({str(attack_file)!r}):
    time.sleep(0.01)

results = {{}}
def python_signal(name, pid, signum):
    try:
        os.kill(pid, signum)
    except OSError as exc:
        results[name] = exc.errno
    else:
        results[name] = 0

libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
numbers = {syscall_numbers[machine]!r}
def raw_signal(name, *arguments):
    ctypes.set_errno(0)
    syscall_name = (
        "setpriority"
        if name.startswith("setpriority_")
        else "ioprio_set"
        if name.startswith("ioprio_")
        else name
    )
    result = libc.syscall(numbers[syscall_name], *arguments)
    results[name] = ctypes.get_errno() if result == -1 else 0

python_signal("broadcast", -1, 0)
raw_signal("rt_sigqueueinfo", supervisor_pid, signal.SIGKILL, 0)
raw_signal(
    "rt_tgsigqueueinfo",
    supervisor_pid,
    supervisor_pid,
    signal.SIGKILL,
    0,
)
python_signal("positive", supervisor_pid, signal.SIGKILL)
python_signal("process_group", -supervisor_pid, signal.SIGKILL)
raw_signal("tkill", supervisor_pid, signal.SIGKILL)
raw_signal("tgkill", supervisor_pid, supervisor_pid, signal.SIGKILL)
raw_signal("pidfd_open", supervisor_pid, 0)
raw_signal("prlimit64", supervisor_pid, 0, 0, 0)
raw_signal("sched_setparam", supervisor_pid, 0)
raw_signal("sched_setscheduler", supervisor_pid, 0, 0)
raw_signal("sched_setaffinity", supervisor_pid, 0, 0)
raw_signal("sched_setattr", supervisor_pid, 0, 0)
raw_signal("setpriority_process", 0, supervisor_pid, 19)
raw_signal("setpriority_group", 1, supervisor_pid, 19)
raw_signal("setpriority_user", 2, 0, 19)
raw_signal("ioprio_process", 1, supervisor_pid, (2 << 13) | 7)
raw_signal("ioprio_group", 2, supervisor_pid, (2 << 13) | 7)
raw_signal("ioprio_user", 3, 0, (2 << 13) | 7)
with open({str(results_file)!r}, "w", encoding="utf-8") as stream:
    json.dump(results, stream, sort_keys=True)
os._exit(0)
"""
    runner_source = (
        "import sys;"
        "from agency_runtime.core.owned_process import run_bounded_binary_process;"
        "from agency_runtime.core.process_argv import freeze_process_argv,prepare_process_argv;"
        f"target={target_source!r};"
        "command=freeze_process_argv(prepare_process_argv([sys.executable,'-c',target]));"
        "result=run_bounded_binary_process(command,timeout=60);"
        "raise SystemExit(result.returncode)"
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    runner = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", runner_source],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    owned_pidfds: list[int] = []
    try:
        _wait_for_runner_evidence(
            runner,
            lambda: _pid_files_ready(
                direct_pid_file,
                supervisor_pid_file,
                escaped_pid_file,
            ),
        )
        supervisor_pid = int(supervisor_pid_file.read_text(encoding="ascii"))
        direct_pid = int(direct_pid_file.read_text(encoding="ascii"))
        escaped_pid = int(escaped_pid_file.read_text(encoding="ascii"))
        owned_pidfds = [os.pidfd_open(pid, 0) for pid in (supervisor_pid, direct_pid, escaped_pid)]

        attack_file.write_text("attack", encoding="ascii")
        stdout, stderr = runner.communicate(timeout=10)

        assert runner.returncode == 1, (stdout, stderr)
        assert json.loads(results_file.read_text(encoding="utf-8")) == {
            "broadcast": errno.EPERM,
            "pidfd_open": errno.EPERM,
            "positive": errno.EPERM,
            "prlimit64": errno.EPERM,
            "process_group": errno.EPERM,
            "rt_sigqueueinfo": errno.EPERM,
            "rt_tgsigqueueinfo": errno.EPERM,
            "tgkill": errno.EPERM,
            "tkill": errno.EPERM,
            "sched_setaffinity": errno.EPERM,
            "sched_setattr": errno.EPERM,
            "sched_setparam": errno.EPERM,
            "sched_setscheduler": errno.EPERM,
            "setpriority_group": errno.EPERM,
            "setpriority_process": errno.EPERM,
            "setpriority_user": errno.EPERM,
            "ioprio_group": errno.EPERM,
            "ioprio_process": errno.EPERM,
            "ioprio_user": errno.EPERM,
        }
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not _linux_pidfds_are_gone(owned_pidfds):
            time.sleep(0.01)
        assert _linux_pidfds_are_gone(owned_pidfds)
        assert unrelated.poll() is None
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.communicate(timeout=5)
        for descriptor in owned_pidfds:
            with suppress(ProcessLookupError):
                signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
            os.close(descriptor)
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux parent-death contract")
def test_linux_launcher_sigkill_terminates_supervisor_target_and_escaped_descendant(
    tmp_path: Path,
) -> None:
    direct_pid_file = tmp_path / "direct.pid"
    escaped_pid_file = tmp_path / "escaped-parent-death.pid"
    target_source = (
        "import os,time;"
        f"open({str(direct_pid_file)!r},'w').write(str(os.getpid()));"
        "child=os.fork();"
        "\nif child==0:"
        "\n os.setsid(); grandchild=os.fork();"
        f"\n if grandchild==0: open({str(escaped_pid_file)!r},'w').write(str(os.getpid()));"
        "\n if grandchild==0: time.sleep(30); os._exit(0);"
        "\n os._exit(0);"
        "\ntime.sleep(30)"
    )
    runner_source = (
        "import sys;"
        "from agency_runtime.core.owned_process import run_bounded_binary_process;"
        "from agency_runtime.core.process_argv import freeze_process_argv,prepare_process_argv;"
        f"target={target_source!r};"
        "command=freeze_process_argv(prepare_process_argv([sys.executable,'-c',target]));"
        "result=run_bounded_binary_process(command,timeout=60);"
        "raise SystemExit(result.returncode)"
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    runner = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", runner_source],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    owned_pidfds: list[int] = []

    try:
        supervisor_pid = 0

        def supervisor_ready() -> bool:
            nonlocal supervisor_pid
            children = _linux_process_children(runner.pid)
            if len(children) != 1:
                return False
            supervisor_pid = next(iter(children))
            return _pid_files_ready(direct_pid_file, escaped_pid_file)

        _wait_for_runner_evidence(runner, supervisor_ready)
        direct_pid = int(direct_pid_file.read_text(encoding="utf-8"))
        escaped_pid = int(escaped_pid_file.read_text(encoding="utf-8"))
        owned_pidfds = [os.pidfd_open(pid, 0) for pid in (supervisor_pid, direct_pid, escaped_pid)]

        os.kill(runner.pid, signal.SIGKILL)
        runner.communicate(timeout=5)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not _linux_pidfds_are_gone(owned_pidfds):
            time.sleep(0.01)
        assert _linux_pidfds_are_gone(owned_pidfds)
        assert unrelated.poll() is None
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.communicate(timeout=5)
        for descriptor in owned_pidfds:
            with suppress(ProcessLookupError):
                signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
            os.close(descriptor)
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux terminal receipt contract")
def test_linux_abnormal_supervisor_exit_rejects_missing_terminal_receipt(
    tmp_path: Path,
) -> None:
    from agency_runtime.core import owned_process_linux as linux

    target_pid_file = tmp_path / "abnormal-supervisor-target.pid"
    target = _frozen_interpreter(
        "-c",
        (
            "import os,time;"
            f"open({str(target_pid_file)!r},'w').write(str(os.getpid()));"
            "time.sleep(30)"
        ),
    )
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    state = owned_process._OwnedProcessState(argv=target, process=process)
    owned_process._claim_linux_completion_owner(process)
    owned_process._release_owned_process(state)
    target_pidfd = -1
    try:
        _wait_for_runner_evidence(process, lambda: _pid_files_ready(target_pid_file))
        target_pid = int(target_pid_file.read_text(encoding="ascii"))
        target_pidfd = os.pidfd_open(target_pid, 0)

        process.kill()
        process.communicate(timeout=5)

        with pytest.raises(OSError, match="terminal completion"):
            linux.collect_status(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not _linux_pidfds_are_gone([target_pidfd]):
            time.sleep(0.01)
        assert _linux_pidfds_are_gone([target_pidfd])
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        linux.close_status(process)
        if target_pidfd >= 0:
            with suppress(ProcessLookupError):
                signal.pidfd_send_signal(target_pidfd, signal.SIGKILL, None, 0)
            os.close(target_pidfd)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux procfs contract")
def test_linux_supervisor_pinned_children_fd_survives_persistent_proc_path_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import owned_process_linux as linux

    direct_pid_file = tmp_path / "procfs-fault-direct.pid"
    escaped_pid_file = tmp_path / "procfs-fault-escaped.pid"
    proc_fault_file = tmp_path / "procfs-fault-observed"
    target = _frozen_interpreter(
        "-c",
        (
            "import os,time;"
            f"open({str(direct_pid_file)!r},'w').write(str(os.getpid()));"
            "child=os.fork();"
            "\nif child==0:"
            "\n os.setsid(); grandchild=os.fork();"
            f"\n if grandchild==0: open({str(escaped_pid_file)!r},'w').write(str(os.getpid()));"
            "\n if grandchild==0: time.sleep(30); os._exit(0);"
            "\n os._exit(0);"
            "\ntime.sleep(30)"
        ),
    )
    setup_marker = "    direct_child_pids()\nexcept OSError as exc:"
    stop_marker = '    if stop_signal:\n        emit("TERMINATED:{}".format(stop_signal))'
    assert setup_marker in linux.SUPERVISOR_SOURCE
    assert stop_marker in linux.SUPERVISOR_SOURCE
    guarded_source = linux.SUPERVISOR_SOURCE.replace(
        setup_marker,
        (
            "    direct_child_pids()\n"
            "    _path_open = open\n"
            "    _path_os_open = os.open\n"
            "    def guarded_path_open(path, *args, **kwargs):\n"
            f"        if os.path.exists({str(escaped_pid_file)!r}) and "
            "os.fspath(path).startswith('/proc'):\n"
            "            raise OSError(errno.EACCES, 'persistent-proc-path-fault')\n"
            "        return _path_open(path, *args, **kwargs)\n"
            "    def guarded_os_open(path, *args, **kwargs):\n"
            f"        if os.path.exists({str(escaped_pid_file)!r}) and "
            "os.fspath(path).startswith('/proc'):\n"
            "            raise OSError(errno.EACCES, 'persistent-proc-path-fault')\n"
            "        return _path_os_open(path, *args, **kwargs)\n"
            "    open = guarded_path_open\n"
            "    os.open = guarded_os_open\n"
            "except OSError as exc:"
        ),
        1,
    ).replace(
        stop_marker,
        (
            "    if stop_signal:\n"
            "        try:\n"
            "            open('/proc/self/status', 'rb').close()\n"
            "        except OSError as exc:\n"
            f"            open({str(proc_fault_file)!r}, 'w').write(str(exc.errno))\n"
            "        else:\n"
            "            fail('proc-path-fault-not-active')\n"
            '        emit("TERMINATED:{}".format(stop_signal))'
        ),
        1,
    )
    monkeypatch.setattr(
        linux,
        "SUPERVISOR_SOURCE",
        guarded_source,
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    process = owned_process._spawn_linux_supervisor(
        target,
        cwd=None,
        env=dict(os.environ),
        text=False,
        forbidden_roots=(),
    )
    state = owned_process._OwnedProcessState(argv=target, process=process)
    owned_process._claim_linux_completion_owner(process)
    owned_process._release_owned_process(state)
    owned_pidfds: list[int] = []
    try:
        _wait_for_runner_evidence(
            process,
            lambda: _pid_files_ready(direct_pid_file, escaped_pid_file),
        )
        direct_pid = int(direct_pid_file.read_text(encoding="utf-8"))
        escaped_pid = int(escaped_pid_file.read_text(encoding="utf-8"))
        owned_pidfds = [os.pidfd_open(pid, 0) for pid in (direct_pid, escaped_pid)]

        process.terminate()
        process.communicate(timeout=5)
        messages = linux.collect_status(process)

        assert process.returncode not in (None, 0)
        assert proc_fault_file.read_text(encoding="ascii") == str(errno.EACCES)
        assert any(message.startswith("TERMINATED:") for message in messages)
        assert messages[-1] == "COMPLETE"
        assert not any(message.startswith("ERROR:proc-children-") for message in messages)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not _linux_pidfds_are_gone(owned_pidfds):
            time.sleep(0.01)
        assert _linux_pidfds_are_gone(owned_pidfds)
        assert unrelated.poll() is None
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        linux.close_status(process)
        for descriptor in owned_pidfds:
            with suppress(ProcessLookupError):
                signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
            os.close(descriptor)
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="Windows atomic Job-at-creation contract")
def test_windows_launcher_death_kills_child_during_atomic_creation_window(
    tmp_path: Path,
) -> None:
    ready_file = tmp_path / "atomic-child.pid"
    runner_source = (
        "import time;"
        "from agency_runtime.core import owned_process_windows_atomic as atomic;"
        "from agency_runtime.core.owned_process import run_bounded_binary_process;"
        "from agency_runtime.core.process_argv import freeze_process_argv,prepare_process_argv;"
        "original=atomic._launch;"
        "\ndef paused_launch(**kwargs):"
        "\n receipt=original(**kwargs);"
        f"\n open({str(ready_file)!r},'w').write(str(receipt.process_id));"
        "\n time.sleep(30);"
        "\n return receipt;"
        "\natomic._launch=paused_launch;"
        "\ncommand=freeze_process_argv("
        "prepare_process_argv([__import__('sys').executable,'-c','import time;time.sleep(30)']));"
        "\nrun_bounded_binary_process(command,timeout=60)"
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    runner = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", runner_source],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    process_handle = None
    kernel32 = None
    try:
        _wait_for_runner_evidence(runner, lambda: _pid_files_ready(ready_file))
        child_pid = int(ready_file.read_text(encoding="utf-8"))

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        process_handle = kernel32.OpenProcess(0x00100000 | 0x1000, False, child_pid)
        assert process_handle

        runner.kill()
        runner.communicate(timeout=5)

        assert int(kernel32.WaitForSingleObject(process_handle, 10_000)) == 0
        assert unrelated.poll() is None
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.communicate(timeout=5)
        if process_handle and kernel32 is not None:
            if int(kernel32.WaitForSingleObject(process_handle, 0)) != 0:
                kernel32.TerminateProcess(process_handle, 1)
                kernel32.WaitForSingleObject(process_handle, 5_000)
            kernel32.CloseHandle(process_handle)
        unrelated.kill()
        unrelated.wait(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job descendant contract")
def test_windows_launcher_death_kills_resumed_target_and_descendant(
    tmp_path: Path,
) -> None:
    direct_pid_file = tmp_path / "windows-direct.pid"
    descendant_pid_file = tmp_path / "windows-descendant.pid"
    descendant_source = (
        "import os,time;"
        f"open({str(descendant_pid_file)!r},'w').write(str(os.getpid()));"
        "time.sleep(30)"
    )
    target_source = (
        "import os,subprocess,sys,time;"
        f"open({str(direct_pid_file)!r},'w').write(str(os.getpid()));"
        f"subprocess.Popen([sys.executable,'-c',{descendant_source!r}]);"
        "time.sleep(30)"
    )
    runner_source = (
        "import sys;"
        "from agency_runtime.core.owned_process import run_bounded_binary_process;"
        "from agency_runtime.core.process_argv import freeze_process_argv,prepare_process_argv;"
        f"target={target_source!r};"
        "command=freeze_process_argv(prepare_process_argv([sys.executable,'-c',target]));"
        "result=run_bounded_binary_process(command,timeout=60);"
        "raise SystemExit(result.returncode)"
    )
    unrelated = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", "import time;time.sleep(30)"],
    )
    runner = subprocess.Popen(
        [str(trusted_test_interpreter()), "-c", runner_source],
        cwd=Path(__file__).resolve().parents[1],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    kernel32 = None
    handles: list[Any] = []
    try:
        _wait_for_runner_evidence(
            runner,
            lambda: _pid_files_ready(direct_pid_file, descendant_pid_file),
        )

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        for path in (direct_pid_file, descendant_pid_file):
            handle = kernel32.OpenProcess(
                0x00100000 | 0x1000,
                False,
                int(path.read_text(encoding="utf-8")),
            )
            assert handle
            handles.append(handle)

        runner.kill()
        runner.communicate(timeout=5)

        assert all(int(kernel32.WaitForSingleObject(handle, 10_000)) == 0 for handle in handles)
        assert unrelated.poll() is None
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.communicate(timeout=5)
        if kernel32 is not None:
            for handle in handles:
                if int(kernel32.WaitForSingleObject(handle, 0)) != 0:
                    kernel32.TerminateProcess(handle, 1)
                    kernel32.WaitForSingleObject(handle, 5_000)
                kernel32.CloseHandle(handle)
        unrelated.kill()
        unrelated.wait(timeout=5)


def test_public_binary_runner_reports_timeout_after_owned_cleanup() -> None:
    command = _frozen_interpreter("-c", "import time; time.sleep(30)")

    result = backends.run_bounded_binary_process(command, timeout=0.05)

    assert result.returncode == 124
    assert result.timed_out is True


def test_binary_owned_preparation_reuses_persistent_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = PreparedProcessArgv(["tool", "old"], artifact_paths=("tool",))
    receipt = (object(),)
    prepared.persistent_artifact_identities = receipt  # type: ignore[assignment]
    prepared.frozen_platform = "posix"
    revalidated: list[PreparedProcessArgv] = []
    monkeypatch.setattr(backends, "revalidate_process_argv", revalidated.append)
    monkeypatch.setattr(
        backends,
        "freeze_persistent_process_argv",
        lambda candidate, **_kwargs: (
            setattr(
                candidate,
                "persistent_artifact_identities",
                receipt,
            )
            or candidate
        ),
    )

    result = backends._prepare_owned_process_argv(
        prepared,
        forbidden_roots=("workspace",),
    )

    assert result is prepared
    assert revalidated == [prepared]


def test_binary_owned_preparation_rejects_changed_persistent_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = PreparedProcessArgv(["tool"], artifact_paths=("tool",))
    prepared.persistent_artifact_identities = (object(),)  # type: ignore[assignment]
    prepared.frozen_platform = "posix"
    monkeypatch.setattr(backends, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        backends,
        "freeze_persistent_process_argv",
        lambda candidate, **_kwargs: (
            setattr(
                candidate,
                "persistent_artifact_identities",
                (object(),),
            )
            or candidate
        ),
    )

    with pytest.raises(OSError, match="persistent executable identity changed"):
        backends._prepare_owned_process_argv(
            prepared,
            forbidden_roots=("workspace",),
        )


def test_binary_spawn_requires_prepared_receipt() -> None:
    with pytest.raises(TypeError, match="frozen executable identity"):
        backends._spawn_owned_binary_process(
            ["tool"],
            cwd=None,
            env={},
            input_bytes=None,
        )


def test_binary_facade_spawn_routes_to_central_binary_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, Any] = {}
    sentinel = object()
    prepared = PreparedProcessArgv(["tool"], artifact_paths=("tool",))
    monkeypatch.setattr(backends._process, "_is_windows", lambda: False)
    monkeypatch.setattr(backends._process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        backends._process,
        "_spawn_linux_supervisor",
        lambda target, **kwargs: observed.update(target=target, **kwargs) or sentinel,
    )

    result = backends._spawn_owned_binary_process(
        prepared,
        cwd="work",
        env={"PATH": "safe"},
        input_bytes=b"x" * (backends._WINDOWS_PREFILLED_STDIN_BYTES + 1),
    )

    assert result is sentinel
    assert observed == {
        "target": prepared,
        "cwd": "work",
        "env": {"PATH": "safe"},
        "text": False,
        "forbidden_roots": (),
    }


def test_binary_spawn_cleans_prefilled_fd_on_spawn_and_close_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = PreparedProcessArgv(["tool"], artifact_paths=("tool",))
    closed: list[int] = []
    monkeypatch.setattr(backends._process, "_is_windows", lambda: True)
    monkeypatch.setattr(backends._process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        backends._process,
        "_create_prefilled_stdin_pipe_bytes",
        lambda _input: 10,
    )
    monkeypatch.setattr(backends._process.os, "close", closed.append)
    monkeypatch.setattr(
        backends._process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn failed")),
    )
    with pytest.raises(RuntimeError, match="spawn failed"):
        backends._spawn_owned_binary_process(
            prepared,
            cwd=None,
            env={},
            input_bytes=b"payload",
        )
    assert closed == [10]

    monkeypatch.setattr(
        backends._process.os,
        "close",
        lambda _fd: (_ for _ in ()).throw(OSError("cleanup close failed")),
    )
    with pytest.raises(RuntimeError, match="spawn failed"):
        backends._spawn_owned_binary_process(
            prepared,
            cwd=None,
            env={},
            input_bytes=b"payload",
        )

    process = object()
    reaped: list[object] = []
    pipes_closed: list[object] = []
    atomic_resources_closed: list[object] = []
    monkeypatch.setattr(
        backends._process,
        "_spawn_atomic_windows_process",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        backends._process.os,
        "close",
        lambda _fd: (_ for _ in ()).throw(OSError("reader close failed")),
    )
    monkeypatch.setattr(
        backends._process,
        "_kill_and_reap_process",
        reaped.append,
    )
    monkeypatch.setattr(backends._process, "_close_process_pipes", pipes_closed.append)
    monkeypatch.setattr(
        backends._process,
        "_close_atomic_windows_process_resources",
        atomic_resources_closed.append,
    )
    with pytest.raises(OSError, match="reader close failed"):
        backends._spawn_owned_binary_process(
            prepared,
            cwd=None,
            env={},
            input_bytes=b"payload",
        )
    assert reaped == [process]
    assert pipes_closed == [process]
    assert atomic_resources_closed == [process]


def test_binary_spawn_failure_without_prefilled_fd_has_no_descriptor_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = PreparedProcessArgv(["tool"], artifact_paths=("tool",))
    monkeypatch.setattr(backends._process, "_is_windows", lambda: False)
    monkeypatch.setattr(backends._process, "revalidate_process_argv", lambda _argv: None)
    monkeypatch.setattr(
        backends._process,
        "_spawn_linux_supervisor",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn failed")),
    )
    monkeypatch.setattr(
        backends._process.os,
        "close",
        lambda _fd: pytest.fail("no parent descriptor exists"),
    )

    with pytest.raises(RuntimeError, match="spawn failed"):
        backends._spawn_owned_binary_process(
            prepared,
            cwd=None,
            env={},
            input_bytes=b"payload",
        )
