"""Cross-platform process-containment and bounded-runner edge contracts."""

from __future__ import annotations

import io
import signal
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.delegation import backend_process


def test_close_process_pipes_skips_absent_streams() -> None:
    closed: list[str] = []
    process = SimpleNamespace(
        stdin=None,
        stdout=SimpleNamespace(close=lambda: closed.append("stdout")),
        stderr=SimpleNamespace(close=lambda: closed.append("stderr")),
    )

    backend_process._close_process_pipes(process)

    assert closed == ["stdout", "stderr"]


def test_posix_group_probe_reports_live_and_missing_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace(pid=42)
    monkeypatch.setattr(backend_process, "_IS_WINDOWS", False)
    monkeypatch.setattr(backend_process.os, "killpg", lambda _pid, _signal: None, raising=False)
    assert backend_process._posix_process_group_active(process) is True

    def missing_group(_pid: int, _signal: int) -> None:
        raise ProcessLookupError

    monkeypatch.setattr(backend_process.os, "killpg", missing_group, raising=False)
    assert backend_process._posix_process_group_active(process) is False
    assert backend_process._owned_process_kwargs(platform_name="posix") == {
        "start_new_session": True
    }


def test_reap_and_windows_job_fallback_force_root_kill(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace(poll=lambda: None)
    killed: list[Any] = []
    monkeypatch.setattr(backend_process, "_wait_for_process", lambda *_args: False)
    monkeypatch.setattr(
        backend_process,
        "_kill_and_reap_process",
        lambda proc, **_kwargs: killed.append(proc),
    )

    backend_process._ensure_process_reaped(process)

    class BrokenJob:
        def terminate(self) -> bool:
            raise OSError("job unavailable")

    backend_process._terminate_windows_job(process, BrokenJob())  # type: ignore[arg-type]
    assert killed == [process, process]


def test_windows_taskkill_launch_failure_kills_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace(pid=123)
    killed: list[Any] = []
    monkeypatch.setattr(
        backend_process.subprocess,
        "Popen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing taskkill")),
    )
    monkeypatch.setattr(backend_process, "_kill_process", killed.append)

    backend_process._request_windows_tree_termination(process)

    assert killed == [process]


def test_windows_taskkill_success_leaves_helper_and_root_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = SimpleNamespace()
    process = SimpleNamespace(pid=123)
    terminated: list[Any] = []
    killed: list[Any] = []
    monkeypatch.setattr(backend_process.subprocess, "Popen", lambda *_args, **_kwargs: helper)
    monkeypatch.setattr(backend_process, "_wait_for_process", lambda *_args: True)
    monkeypatch.setattr(backend_process, "_terminate_taskkill_helper", terminated.append)
    monkeypatch.setattr(backend_process, "_kill_process", killed.append)

    backend_process._request_windows_tree_termination(process)

    assert terminated == []
    assert killed == []


def test_posix_signal_uses_group_then_root_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backend_process.signal, "SIGKILL", 9, raising=False)
    process = SimpleNamespace(pid=9, terminate=lambda: None, kill=lambda: None)
    group_signals: list[int] = []
    monkeypatch.setattr(
        backend_process.os,
        "killpg",
        lambda _pid, signal_number: group_signals.append(signal_number),
        raising=False,
    )
    backend_process._signal_posix_process_tree(process, signal.SIGTERM)
    assert group_signals == [signal.SIGTERM]

    actions: list[str] = []

    def no_group(_pid: int, _signal: int) -> None:
        raise OSError("group gone")

    process = SimpleNamespace(
        pid=9,
        terminate=lambda: actions.append("terminate"),
        kill=lambda: actions.append("kill"),
    )
    monkeypatch.setattr(backend_process.os, "killpg", no_group, raising=False)
    backend_process._signal_posix_process_tree(process, signal.SIGTERM)
    backend_process._signal_posix_process_tree(process, signal.SIGKILL)
    assert actions == ["terminate", "kill"]

    process = SimpleNamespace(
        pid=9,
        terminate=lambda: (_ for _ in ()).throw(OSError("already gone")),
        kill=lambda: (_ for _ in ()).throw(OSError("already gone")),
    )
    backend_process._signal_posix_process_tree(process, signal.SIGTERM)
    backend_process._signal_posix_process_tree(process, signal.SIGKILL)


def test_posix_group_finish_and_tree_termination_escalate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace()
    signals: list[int] = []
    active = iter([True, True, True])
    clock = iter([0.0, 0.5, 2.0])
    monkeypatch.setattr(backend_process.signal, "SIGKILL", 9, raising=False)
    monkeypatch.setattr(
        backend_process,
        "_posix_process_group_active",
        lambda _process: next(active),
    )
    monkeypatch.setattr(backend_process.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(backend_process.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        backend_process,
        "_signal_posix_process_tree",
        lambda _process, number: signals.append(number),
    )
    backend_process._finish_posix_process_group(process)
    assert signals == [signal.SIGKILL]

    actions: list[str] = []
    monkeypatch.setattr(
        backend_process,
        "_signal_posix_process_tree",
        lambda _process, number: actions.append(f"signal:{number}"),
    )
    monkeypatch.setattr(backend_process, "_wait_for_process", lambda *_args: False)
    monkeypatch.setattr(
        backend_process,
        "_finish_posix_process_group",
        lambda _process: actions.append("finish"),
    )
    monkeypatch.setattr(
        backend_process,
        "_ensure_process_reaped",
        lambda _process: actions.append("reap"),
    )
    backend_process._terminate_posix_process_tree(process)
    assert actions == [f"signal:{signal.SIGTERM}", f"signal:{signal.SIGKILL}", "finish", "reap"]

    actions.clear()
    monkeypatch.setattr(
        backend_process,
        "_terminate_posix_process_tree",
        lambda _process: actions.append("owned-posix"),
    )
    backend_process._terminate_owned_process_tree(process, platform_name="posix")
    assert actions == ["owned-posix"]


def test_posix_group_finish_and_tree_termination_accept_clean_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = SimpleNamespace()
    signals: list[int] = []
    monkeypatch.setattr(backend_process, "_posix_process_group_active", lambda _process: False)
    monkeypatch.setattr(backend_process.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(
        backend_process,
        "_signal_posix_process_tree",
        lambda _process, signal_number: signals.append(signal_number),
    )

    backend_process._finish_posix_process_group(process)

    assert signals == []

    actions: list[str] = []
    monkeypatch.setattr(backend_process, "_wait_for_process", lambda *_args: True)
    monkeypatch.setattr(
        backend_process,
        "_finish_posix_process_group",
        lambda _process: actions.append("finish"),
    )
    monkeypatch.setattr(
        backend_process,
        "_ensure_process_reaped",
        lambda _process: actions.append("reap"),
    )

    backend_process._terminate_posix_process_tree(process)

    assert signals == [signal.SIGTERM]
    assert actions == ["finish", "reap"]


class _BrokenReadStream:
    def __init__(self) -> None:
        self.closed = False

    def read(self, _size: int) -> str:
        raise OSError("stream broke")

    def close(self) -> None:
        self.closed = True


class _BrokenWriteStream:
    def __init__(self) -> None:
        self.closed = False

    def write(self, _value: str) -> None:
        raise BrokenPipeError

    def flush(self) -> None:
        raise AssertionError("flush is unreachable after write failure")

    def close(self) -> None:
        self.closed = True


class _NonClosingBytesIO(io.BytesIO):
    def close(self) -> None:
        pass


class _ReconfigureFailureStream(io.TextIOBase):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.reconfigure_attempted = False

    def reconfigure(self, **_kwargs: Any) -> None:
        self.reconfigure_attempted = True
        raise OSError("reconfigure unavailable")

    def write(self, value: str) -> int:
        self.parts.append(value)
        return len(value)

    def flush(self) -> None:
        pass


class _TextStreamWithoutReconfigure(_ReconfigureFailureStream):
    reconfigure = None


class _NonTextStream:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.closed = False

    def reconfigure(self, **_kwargs: Any) -> None:
        raise AssertionError("non-text streams must not be reconfigured")

    def write(self, value: str) -> int:
        self.parts.append(value)
        return len(value)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def test_stream_workers_tolerate_early_child_exit() -> None:
    source = _BrokenReadStream()
    capture = backend_process._BoundedTextCapture(10)
    backend_process._drain_process_stream(source, capture)
    assert source.closed is True

    target = _BrokenWriteStream()
    process = SimpleNamespace(stdin=target)
    completed = backend_process.threading.Event()
    backend_process._write_process_stdin(process, "payload", completed)
    assert target.closed is True
    assert completed.is_set()

    backend_process._write_process_stdin(SimpleNamespace(stdin=None), "payload")


def test_stdin_writer_preserves_lf_and_tolerates_reconfigure_fallbacks() -> None:
    raw = _NonClosingBytesIO()
    translating = io.TextIOWrapper(raw, encoding="utf-8", newline="\r\n")

    backend_process._write_process_stdin(
        SimpleNamespace(stdin=translating),
        "first\nsecond",
    )

    assert raw.getvalue() == b"first\nsecond"

    fallback = _ReconfigureFailureStream()
    backend_process._write_process_stdin(SimpleNamespace(stdin=fallback), "exact\ntext")
    assert fallback.reconfigure_attempted is True
    assert fallback.parts == ["exact\ntext"]

    without_reconfigure = _TextStreamWithoutReconfigure()
    backend_process._write_process_stdin(
        SimpleNamespace(stdin=without_reconfigure),
        "exact\ntext",
    )
    assert without_reconfigure.parts == ["exact\ntext"]

    non_text = _NonTextStream()
    backend_process._write_process_stdin(SimpleNamespace(stdin=non_text), "exact\ntext")
    assert non_text.parts == ["exact\ntext"]
    assert non_text.closed is True


def test_no_input_closes_child_stdin_before_stream_workers_start() -> None:
    stdin = _NonTextStream()
    process = SimpleNamespace(
        stdin=stdin,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )

    stdout_thread, stderr_thread, stdin_thread = backend_process._start_process_io_threads(
        process,
        stdout=backend_process._BoundedTextCapture(10),
        stderr=backend_process._BoundedTextCapture(10),
        input_text=None,
        windows_job=None,
    )
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)

    assert stdin.parts == [""]
    assert stdin.closed is True
    assert stdin_thread is None


def test_input_writer_starts_before_output_drainers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[str] = []

    class RecordingThread:
        def __init__(self, name: str) -> None:
            self.name = name

        def start(self) -> None:
            started.append(self.name)

    threads = (
        RecordingThread("stdout"),
        RecordingThread("stderr"),
        RecordingThread("stdin"),
    )
    monkeypatch.setattr(
        backend_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: threads,
    )

    result = backend_process._start_process_io_threads(
        SimpleNamespace(stdin=object()),
        stdout=object(),
        stderr=object(),
        input_text="payload",
        windows_job=None,
    )

    assert result == threads
    assert started == ["stdin", "stdout", "stderr"]


def test_small_suspended_input_reaches_eof_before_output_drainers_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    class Completion:
        def __init__(self) -> None:
            self.ready = False

        def set(self) -> None:
            self.ready = True

        def wait(self, timeout: float) -> bool:
            events.append(f"wait:{timeout}")
            return self.ready

    completion = Completion()

    class RecordingThread:
        def __init__(self, name: str) -> None:
            self.name = name

        def start(self) -> None:
            events.append(self.name)
            if self.name == "stdin":
                completion.set()

    threads = (
        RecordingThread("stdout"),
        RecordingThread("stderr"),
        RecordingThread("stdin"),
    )
    monkeypatch.setattr(backend_process.threading, "Event", lambda: completion)
    monkeypatch.setattr(
        backend_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: threads,
    )

    backend_process._start_process_io_threads(
        SimpleNamespace(stdin=object()),
        stdout=object(),
        stderr=object(),
        input_text="payload",
        windows_job=None,
        prime_suspended_stdin=True,
    )

    assert events == [
        "stdin",
        f"wait:{backend_process._SUSPENDED_STDIN_PRIME_TIMEOUT_SECONDS}",
        "stdout",
        "stderr",
    ]


def test_large_suspended_input_does_not_wait_for_eof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[str] = []

    class RecordingThread:
        def __init__(self, name: str) -> None:
            self.name = name

        def start(self) -> None:
            started.append(self.name)

    threads = (
        RecordingThread("stdout"),
        RecordingThread("stderr"),
        RecordingThread("stdin"),
    )
    monkeypatch.setattr(
        backend_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: threads,
    )
    monkeypatch.setattr(
        backend_process.threading,
        "Event",
        lambda: pytest.fail("large input must not create a completion event"),
    )

    backend_process._start_process_io_threads(
        SimpleNamespace(stdin=object()),
        stdout=object(),
        stderr=object(),
        input_text="x" * (backend_process._SUSPENDED_STDIN_PRIME_BYTES + 1),
        windows_job=None,
        prime_suspended_stdin=True,
    )

    assert started == ["stdin", "stdout", "stderr"]


def test_suspended_stdin_prime_timeout_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completion:
        def wait(self, timeout: float) -> bool:
            assert timeout == backend_process._SUSPENDED_STDIN_PRIME_TIMEOUT_SECONDS
            return False

    class RecordingThread:
        def start(self) -> None:
            pass

    process = SimpleNamespace(stdin=object())
    cleaned: list[Any] = []
    monkeypatch.setattr(backend_process.threading, "Event", Completion)
    monkeypatch.setattr(
        backend_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: (
            RecordingThread(),
            RecordingThread(),
            RecordingThread(),
        ),
    )
    monkeypatch.setattr(
        backend_process,
        "_cleanup_partial_io_start",
        lambda proc, **_kwargs: cleaned.append(proc),
    )

    with pytest.raises(OSError, match="could not start process I/O workers"):
        backend_process._start_process_io_threads(
            process,
            stdout=object(),
            stderr=object(),
            input_text="payload",
            windows_job=None,
            prime_suspended_stdin=True,
        )
    assert cleaned == [process]


def test_io_thread_start_reraises_cancellation_after_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CancelThread:
        def start(self) -> None:
            raise KeyboardInterrupt

    process = SimpleNamespace(stdin=None)
    cleaned: list[Any] = []
    monkeypatch.setattr(
        backend_process,
        "_create_process_io_threads",
        lambda *_args, **_kwargs: (CancelThread(), None, None),
    )
    monkeypatch.setattr(
        backend_process,
        "_cleanup_partial_io_start",
        lambda proc, **_kwargs: cleaned.append(proc),
    )

    with pytest.raises(KeyboardInterrupt):
        backend_process._start_process_io_threads(
            process,
            stdout=object(),
            stderr=object(),
            input_text=None,
            windows_job=None,
        )
    assert cleaned == [process]


def test_stream_normalization_and_tiny_output_boundaries() -> None:
    assert backend_process._stream_text(None) == ""
    assert backend_process._stream_text(b"\xff") == "�"
    assert backend_process._bounded("abcdef", 3) == ("\n..", True)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"argv": []}, TypeError),
        ({"argv": [""]}, ValueError),
        ({"argv": ["tool"], "timeout": True}, ValueError),
        ({"argv": ["tool"], "max_output_chars": 0}, ValueError),
        ({"argv": ["tool"], "input_text": "bad\x00input"}, ValueError),
    ],
)
def test_bounded_runner_rejects_invalid_contracts(
    kwargs: dict[str, Any], error: type[Exception]
) -> None:
    parameters = {
        "argv": ["tool"],
        "process_runner": lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0),
        "timeout": 1,
        "max_output_chars": 10,
    }
    parameters.update(kwargs)
    with pytest.raises(error):
        backend_process.run_bounded_process(**parameters)


@pytest.mark.parametrize(
    ("raised", "returncode", "timed_out"),
    [
        (subprocess.TimeoutExpired("tool", 1), 124, True),
        (FileNotFoundError(), 127, False),
        (PermissionError(), 126, False),
        (OSError(), 1, False),
    ],
)
def test_bounded_runner_normalizes_process_start_failures(
    raised: Exception,
    returncode: int,
    timed_out: bool,
) -> None:
    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise raised

    result = backend_process.run_bounded_process(
        ["tool"],
        process_runner=fail,
        timeout=1,
        max_output_chars=10,
    )

    assert result.returncode == returncode
    assert result.timed_out is timed_out


def test_bounded_runner_uses_environment_copy_and_truncates_both_streams() -> None:
    observed: dict[str, Any] = {}

    def run(_argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed.update(kwargs)
        kwargs["stdout"].write("stdout-overflow")
        kwargs["stderr"].write("stderr-overflow")
        return subprocess.CompletedProcess(["tool"], 0)

    supplied_env = {"PATH": "safe"}
    result = backend_process.run_bounded_process(
        ["tool"],
        process_runner=run,
        timeout=1,
        env=supplied_env,
        max_output_chars=5,
    )

    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert observed["env"] == supplied_env
    assert observed["env"] is not supplied_env
