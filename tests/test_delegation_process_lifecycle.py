"""Pure lifecycle tests for contained delegation subprocesses."""

from __future__ import annotations

import io
import os
import subprocess

import pytest

from agency_runtime.core.delegation import backend_process, backends


class _Pipe:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Process:
    def __init__(self, wait_error: BaseException | None = None) -> None:
        self.pid = 4242
        self.returncode = 0
        self.stdin = _Pipe()
        self.stdout = _Pipe()
        self.stderr = _Pipe()
        self.wait_error = wait_error
        self.wait_timeouts: list[float] = []

    def wait(self, timeout: float) -> int:
        self.wait_timeouts.append(timeout)
        if self.wait_error is not None:
            raise self.wait_error
        return self.returncode


class _Thread:
    def __init__(self, *, alive: bool = False) -> None:
        self.alive = alive
        self.join_timeouts: list[float] = []

    def join(self, timeout: float) -> None:
        self.join_timeouts.append(timeout)

    def is_alive(self) -> bool:
        return self.alive


class _Job:
    def __init__(self, active: int | None = 0) -> None:
        self.active = active
        self.close_count = 0

    def active_processes(self) -> int | None:
        return self.active

    def close(self) -> None:
        self.close_count += 1


class _TerminatingProcess:
    def __init__(
        self,
        wait_outcomes: list[int | BaseException],
        *,
        pid: int,
    ) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.wait_outcomes = wait_outcomes
        self.wait_timeouts: list[float] = []
        self.kill_count = 0

    def wait(self, timeout: float) -> int:
        self.wait_timeouts.append(timeout)
        outcome = self.wait_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        self.returncode = outcome
        return outcome

    def kill(self) -> None:
        self.kill_count += 1

    def poll(self) -> int | None:
        return self.returncode


def _configure_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    process: _Process,
    *,
    windows: bool = False,
    threads: tuple[_Thread, _Thread, _Thread | None] | None = None,
    job: _Job | None = None,
) -> list[tuple[_Process, _Job | None]]:
    configured_threads = threads or (_Thread(), _Thread(), None)
    terminations: list[tuple[_Process, _Job | None]] = []

    monkeypatch.setattr(backends, "_is_windows", lambda: windows)
    monkeypatch.setattr(backends, "prepare_process_argv", lambda argv: list(argv))
    monkeypatch.setattr(
        backends,
        "_spawn_owned_process",
        lambda _argv, **_kwargs: process,
    )
    monkeypatch.setattr(
        backends,
        "_start_process_io_threads",
        lambda _process, **_kwargs: configured_threads,
    )
    monkeypatch.setattr(
        backends,
        "_posix_process_group_active",
        lambda _process: False,
    )
    monkeypatch.setattr(
        backends,
        "_terminate_owned_process_tree",
        lambda owned, *, windows_job=None: terminations.append((owned, windows_job)),
    )
    monkeypatch.setattr(backends, "_create_windows_job", lambda _process: job)
    monkeypatch.setattr(backends, "_resume_windows_process", lambda _pid: True)
    return terminations


def _run() -> subprocess.CompletedProcess[str]:
    return backends._run_owned_process(
        ["agent", "--one-shot"],
        cwd=None,
        env={"PATH": "test"},
        stdout=io.StringIO("stdout"),
        stderr=io.StringIO("stderr"),
        timeout=3,
        input_text="task",
    )


def test_spawn_uses_an_explicitly_closed_pipe_for_no_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    sentinel = object()

    def fake_popen(*args: object, **kwargs: object) -> object:
        observed["args"] = args
        observed.update(kwargs)
        return sentinel

    monkeypatch.setattr(backends.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(backends, "_is_windows", lambda: False)

    result = backends._spawn_owned_process(
        ["agent"],
        cwd=None,
        env={"PATH": "test"},
        input_text=None,
    )

    assert result is sentinel
    assert observed["stdin"] is subprocess.PIPE


@pytest.mark.parametrize(
    ("input_text", "expected"),
    [
        (None, b""),
        ("", b""),
        ("payload", b"payload"),
        ("é" * 2048, ("é" * 2048).encode()),
    ],
)
def test_windows_bounded_stdin_is_complete_before_child_creation(
    monkeypatch: pytest.MonkeyPatch,
    input_text: str | None,
    expected: bytes,
) -> None:
    observed: dict[str, object] = {}
    sentinel = object()

    def fake_popen(*_args: object, **kwargs: object) -> object:
        stdin_fd = kwargs["stdin"]
        assert isinstance(stdin_fd, int)
        observed["payload"] = os.read(stdin_fd, 8192)
        return sentinel

    monkeypatch.setattr(backends, "_is_windows", lambda: True)
    monkeypatch.setattr(backends.subprocess, "Popen", fake_popen)

    result = backends._spawn_owned_process(
        ["agent"],
        cwd=None,
        env={"PATH": "test"},
        input_text=input_text,
    )

    assert result is sentinel
    assert observed["payload"] == expected


def test_windows_large_stdin_remains_asynchronous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    sentinel = object()
    monkeypatch.setattr(backends, "_is_windows", lambda: True)
    monkeypatch.setattr(
        backends.subprocess,
        "Popen",
        lambda *_args, **kwargs: observed.update(kwargs) or sentinel,
    )

    result = backends._spawn_owned_process(
        ["agent"],
        cwd=None,
        env={"PATH": "test"},
        input_text="x" * (backends._WINDOWS_PREFILLED_STDIN_BYTES + 1),
    )

    assert result is sentinel
    assert observed["stdin"] is subprocess.PIPE


def test_windows_prefilled_stdin_fails_closed_on_partial_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(backends.os, "pipe", lambda: (10, 11))
    monkeypatch.setattr(backends.os, "write", lambda _fd, _payload: 1)
    monkeypatch.setattr(backends.os, "close", lambda fd: closed.append(fd))

    with pytest.raises(OSError, match="prefill child stdin"):
        backends._create_prefilled_stdin_pipe("payload")

    assert closed == [10, 11]


def test_windows_prefilled_stdin_requires_confirmed_writer_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(backends.os, "pipe", lambda: (10, 11))

    def close(fd: int) -> None:
        if fd == 11:
            raise OSError("writer close failed")
        closed.append(fd)

    monkeypatch.setattr(backends.os, "close", close)

    with pytest.raises(OSError, match="writer close failed"):
        backends._create_prefilled_stdin_pipe(None)

    assert closed == [10]


def test_windows_prefilled_stdin_cleans_child_when_parent_read_close_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = object()
    reaped: list[object] = []
    pipes_closed: list[object] = []
    monkeypatch.setattr(backends, "_is_windows", lambda: True)
    monkeypatch.setattr(backends, "_create_prefilled_stdin_pipe", lambda _input: 10)
    monkeypatch.setattr(backends.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(
        backends.os,
        "close",
        lambda _fd: (_ for _ in ()).throw(OSError("reader close failed")),
    )
    monkeypatch.setattr(
        backends._process,
        "_kill_and_reap_process",
        lambda owned: reaped.append(owned),
    )
    monkeypatch.setattr(backends, "_close_process_pipes", pipes_closed.append)

    with pytest.raises(OSError, match="reader close failed"):
        backends._spawn_owned_process(
            ["agent"],
            cwd=None,
            env={"PATH": "test"},
            input_text="payload",
        )

    assert reaped == [process]
    assert pipes_closed == [process]


def test_windows_prefilled_stdin_closes_parent_fd_when_spawn_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[int] = []
    monkeypatch.setattr(backends, "_is_windows", lambda: True)
    monkeypatch.setattr(backends, "_create_prefilled_stdin_pipe", lambda _input: 10)
    monkeypatch.setattr(
        backends.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn failed")),
    )
    monkeypatch.setattr(backends.os, "close", closed.append)

    with pytest.raises(RuntimeError, match="spawn failed"):
        backends._spawn_owned_process(
            ["agent"],
            cwd=None,
            env={"PATH": "test"},
            input_text="payload",
        )

    assert closed == [10]


def test_spawn_failure_without_prefilled_stdin_has_no_fd_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backends, "_is_windows", lambda: False)
    monkeypatch.setattr(
        backends.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("spawn failed")),
    )
    monkeypatch.setattr(
        backends.os,
        "close",
        lambda _fd: pytest.fail("ordinary pipe ownership belongs to Popen"),
    )

    with pytest.raises(RuntimeError, match="spawn failed"):
        backends._spawn_owned_process(
            ["agent"],
            cwd=None,
            env={"PATH": "test"},
            input_text="payload",
        )


def test_success_returns_exact_process_result_without_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    terminations = _configure_lifecycle(monkeypatch, process)

    result = _run()

    assert result.args == ["agent", "--one-shot"]
    assert result.returncode == 0
    assert result.stdout == "stdout"
    assert result.stderr == "stderr"
    assert process.wait_timeouts == [3]
    assert terminations == []


def test_windows_io_starts_before_suspended_process_resumes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    job = _Job()
    events: list[tuple[str, bool]] = []
    _configure_lifecycle(monkeypatch, process, windows=True, job=job)
    threads = (_Thread(), _Thread(), _Thread())
    monkeypatch.setattr(
        backends,
        "_start_process_io_threads",
        lambda *_args, **kwargs: events.append(("io", kwargs["input_text"] is None)) or threads,
    )
    monkeypatch.setattr(
        backends,
        "_resume_windows_process",
        lambda _pid: not events.append(("resume", True)),
    )

    result = _run()

    assert result.returncode == 0
    assert events == [("io", True), ("resume", True)]


def test_containment_setup_cancellation_cleans_the_just_spawned_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    terminations = _configure_lifecycle(monkeypatch, process, windows=True)

    def interrupted(_process: _Process) -> _Job:
        raise KeyboardInterrupt

    monkeypatch.setattr(backends, "_create_windows_job", interrupted)

    with pytest.raises(KeyboardInterrupt):
        _run()

    assert terminations == [(process, None)]
    assert process.stdin.closed
    assert process.stdout.closed
    assert process.stderr.closed


def test_resume_failure_terminates_then_closes_the_windows_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    job = _Job()
    terminations = _configure_lifecycle(
        monkeypatch,
        process,
        windows=True,
        job=job,
    )
    monkeypatch.setattr(backends, "_resume_windows_process", lambda _pid: False)

    with pytest.raises(OSError, match="contained Windows"):
        _run()

    assert terminations == [(process, job)]
    assert job.close_count == 1


def test_lingering_stdin_writer_is_treated_as_incomplete_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    stdin_thread = _Thread(alive=True)
    terminations = _configure_lifecycle(
        monkeypatch,
        process,
        threads=(_Thread(), _Thread(), stdin_thread),
    )

    with pytest.raises(OSError, match="I/O workers remained active"):
        _run()

    assert len(terminations) == 2
    assert stdin_thread.join_timeouts == [backends._DRAIN_GRACE_SECONDS, 5, 5]


def test_indeterminate_windows_job_state_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = _Process()
    job = _Job(active=None)
    terminations = _configure_lifecycle(
        monkeypatch,
        process,
        windows=True,
        job=job,
    )

    with pytest.raises(OSError, match="outlived"):
        _run()

    assert len(terminations) == 2
    assert all(terminated_job is job for _process, terminated_job in terminations)
    assert job.close_count == 1


def test_timeout_remains_a_timeout_after_tree_and_io_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = subprocess.TimeoutExpired(["agent", "--one-shot"], 3)
    process = _Process(wait_error=original)
    terminations = _configure_lifecycle(monkeypatch, process)

    with pytest.raises(subprocess.TimeoutExpired) as caught:
        _run()

    assert caught.value.cmd == ["agent", "--one-shot"]
    assert caught.value.timeout == 3
    assert caught.value.__cause__ is original
    assert len(terminations) == 2


@pytest.mark.parametrize(
    "interruption",
    [KeyboardInterrupt(), SystemExit(130)],
    ids=["keyboard-interrupt", "system-exit"],
)
def test_base_exception_during_wait_always_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
    interruption: BaseException,
) -> None:
    process = _Process(wait_error=interruption)
    stdout_thread = _Thread(alive=True)
    stderr_thread = _Thread(alive=True)
    terminations = _configure_lifecycle(
        monkeypatch,
        process,
        threads=(stdout_thread, stderr_thread, None),
    )

    with pytest.raises(type(interruption)):
        _run()

    assert terminations == [(process, None)]
    assert stdout_thread.join_timeouts == [5]
    assert stderr_thread.join_timeouts == [5]
    assert process.stdout.closed
    assert process.stderr.closed


@pytest.mark.parametrize(
    "wait_failure",
    [
        subprocess.TimeoutExpired(["taskkill.exe"], 5),
        OSError("taskkill wait failed"),
    ],
    ids=["timeout", "wait-error"],
)
def test_failed_taskkill_helper_is_killed_and_reaped(
    monkeypatch: pytest.MonkeyPatch,
    wait_failure: BaseException,
) -> None:
    helper = _TerminatingProcess(
        [wait_failure, 1],
        pid=222,
    )
    target = _TerminatingProcess([1], pid=111)
    launched: list[list[str]] = []

    def popen(argv: list[str], **_kwargs: object) -> _TerminatingProcess:
        launched.append(argv)
        return helper

    monkeypatch.setattr(backend_process.subprocess, "Popen", popen)
    monkeypatch.setattr(backend_process, "_owned_process_kwargs", lambda **_kwargs: {})

    backend_process._terminate_owned_process_tree(
        target,  # type: ignore[arg-type]
        platform_name="nt",
    )

    assert launched == [["taskkill.exe", "/PID", "111", "/T", "/F"]]
    assert helper.kill_count == 1
    assert helper.wait_timeouts == [5, 2]
    assert target.kill_count == 1
    assert target.wait_timeouts == [5]


def test_windows_job_termination_error_falls_back_to_root_kill() -> None:
    target = _TerminatingProcess([0, 0], pid=111)

    class BrokenJob:
        def terminate(self) -> bool:
            raise OSError("job handle failed")

    backend_process._terminate_owned_process_tree(
        target,  # type: ignore[arg-type]
        platform_name="nt",
        windows_job=BrokenJob(),  # type: ignore[arg-type]
    )

    assert target.kill_count == 1
    assert target.wait_timeouts == [5, 2]
