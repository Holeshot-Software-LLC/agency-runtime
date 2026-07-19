"""Complete private dashboard descriptor validation and lock coverage."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import dashboard_runtime as runtime
from agency_runtime.core.bounded_io import FileSizeLimitError


def _descriptor(**changes: Any) -> dict[str, Any]:
    value = {
        "schema_version": 1,
        "pid": 1,
        "port": 7810,
        "token": "x" * 32,
        "started_at": "2026-07-12T00:00:00+00:00",
    }
    value.update(changes)
    return value


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "invalid"),
        (_descriptor(schema_version=2), "version"),
        (_descriptor(pid=True), "PID"),
        (_descriptor(pid=0), "PID"),
        (_descriptor(port=True), "port"),
        (_descriptor(port=70000), "port"),
        (_descriptor(token=1), "token"),
        (_descriptor(token="short"), "token"),
        (_descriptor(token="x" * 31 + "\n"), "token"),
        (_descriptor(started_at=""), "timestamp"),
        (_descriptor(started_at=1), "timestamp"),
    ],
)
def test_runtime_descriptor_rejects_each_invalid_field(value: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        runtime._validate_descriptor(value)


def test_runtime_lock_retries_then_succeeds_on_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "dashboard.json"
    calls: list[int] = []
    fake_msvcrt = SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2)

    def locking(descriptor: int, mode: int, size: int) -> None:
        calls.append(mode)
        if mode == fake_msvcrt.LK_NBLCK and calls.count(fake_msvcrt.LK_NBLCK) == 1:
            raise OSError("busy")

    fake_msvcrt.locking = locking
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    real_os = runtime.os

    class _WindowsOS:
        name = "nt"

        def __getattr__(self, name: str) -> Any:
            return getattr(real_os, name)

    monkeypatch.setattr(runtime, "os", _WindowsOS())
    monkeypatch.setattr(runtime.time, "sleep", lambda seconds: calls.append(int(seconds * 1000)))
    with runtime._runtime_lock(target, timeout=1):
        assert target.parent.exists()
    assert 25 in calls
    assert fake_msvcrt.LK_UNLCK in calls


def test_runtime_lock_timeout_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda *_args: (_ for _ in ()).throw(OSError("busy")),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    real_os = runtime.os

    class _WindowsOS:
        name = "nt"

        def __getattr__(self, name: str) -> Any:
            return getattr(real_os, name)

    monkeypatch.setattr(runtime, "os", _WindowsOS())
    with (
        pytest.raises(RuntimeError, match="busy"),
        runtime._runtime_lock(tmp_path / "dashboard.json", timeout=0),
    ):
        pass


def test_runtime_lock_and_publish_posix_paths_without_platform_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations: list[int] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda _descriptor, operation: operations.append(operation),
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    real_os = runtime.os
    repairs: list[tuple[Path, bool]] = []
    repaired_descriptors: set[int] = set()

    class _PosixOS:
        name = "posix"

        def fchmod(self, descriptor: int, mode: int) -> None:
            assert mode == 0o600
            repaired_descriptors.add(descriptor)

        def fstat(self, descriptor: int) -> os.stat_result:
            metadata = real_os.fstat(descriptor)
            if descriptor not in repaired_descriptors:
                return metadata
            values = list(metadata)
            values[0] = (metadata.st_mode & ~0o777) | 0o600
            return os.stat_result(values)

        def __getattr__(self, name: str) -> Any:
            return getattr(real_os, name)

    monkeypatch.setattr(runtime, "os", _PosixOS())
    monkeypatch.setattr(
        runtime,
        "restrict_posix_path_permissions",
        lambda path, *, directory: repairs.append((Path(path), directory)),
    )
    target = tmp_path / "dashboard.json"
    with runtime._runtime_lock(target):
        pass
    runtime._publish_dashboard_runtime(target, _descriptor())
    assert operations == [fake_fcntl.LOCK_EX | fake_fcntl.LOCK_NB, fake_fcntl.LOCK_UN]
    assert repairs == [(tmp_path, True), (tmp_path, True)]
    assert runtime.read_dashboard_runtime(path=target) == _descriptor()


@pytest.mark.parametrize("timeout", [True, -1, math.nan, math.inf, 301])
def test_runtime_lock_rejects_invalid_timeouts(tmp_path: Path, timeout: object) -> None:
    with (
        pytest.raises(ValueError, match="finite"),
        runtime._runtime_lock(tmp_path / "dashboard.json", timeout=timeout),  # type: ignore[arg-type]
    ):
        pass


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_runtime_lock_rejects_symlink_without_mutating_target(tmp_path: Path) -> None:
    target = tmp_path / "dashboard.json"
    victim = tmp_path / "victim"
    victim.write_bytes(b"do-not-touch")
    target.with_name(".dashboard.json.lock").symlink_to(victim)

    with pytest.raises(OSError, match="regular non-link"), runtime._runtime_lock(target):
        pass

    assert victim.read_bytes() == b"do-not-touch"


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_runtime_lock_detects_symlink_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "dashboard.json"
    lock_path = target.with_name(".dashboard.json.lock")
    lock_path.write_bytes(b"original-lock")
    victim = tmp_path / "victim"
    victim.write_bytes(b"do-not-touch")
    real_open = runtime.os.open
    swapped = False

    def swap_then_open(path: str | Path, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal swapped
        if Path(path) == lock_path and not swapped:
            swapped = True
            lock_path.unlink()
            lock_path.symlink_to(victim)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(runtime.os, "open", swap_then_open)
    with pytest.raises(OSError, match="opened safely"), runtime._runtime_lock(target):
        pass

    assert victim.read_bytes() == b"do-not-touch"


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics")
def test_runtime_publish_rejects_linked_parent_before_token_write(tmp_path: Path) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    token = "must-not-leak-" + "x" * 32

    with pytest.raises(OSError, match="real directories"):
        runtime._publish_dashboard_runtime(
            linked_parent / "dashboard.json",
            _descriptor(token=token),
        )

    assert token.encode() not in b"".join(
        path.read_bytes() for path in real_parent.iterdir() if path.is_file()
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory substitution semantics")
def test_runtime_publish_detects_parent_swap_before_serialization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = tmp_path / "state"
    parent.mkdir()
    original_parent = tmp_path / "state-original"
    target = parent / "dashboard.json"
    token = "must-not-leak-" + "y" * 32
    real_mkstemp = runtime.tempfile.mkstemp

    def swapped_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
        parent.rename(original_parent)
        parent.mkdir()
        return real_mkstemp(*args, **kwargs)

    monkeypatch.setattr(runtime.tempfile, "mkstemp", swapped_mkstemp)
    with pytest.raises(OSError, match="directory changed"):
        runtime._publish_dashboard_runtime(target, _descriptor(token=token))

    payloads = [
        path.read_bytes()
        for root in (parent, original_parent)
        for path in root.iterdir()
        if path.is_file()
    ]
    assert all(token.encode() not in payload for payload in payloads)


def test_runtime_publish_supports_platforms_without_fchmod(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_os = runtime.os

    class _NoFchmodOS:
        name = real_os.name

        def __getattr__(self, name: str) -> Any:
            if name == "fchmod":
                raise AttributeError(name)
            return getattr(real_os, name)

    monkeypatch.setattr(runtime, "os", _NoFchmodOS())
    target = tmp_path / "dashboard.json"
    runtime._publish_dashboard_runtime(target, _descriptor())
    assert runtime.read_dashboard_runtime(path=target) == _descriptor()


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (FileSizeLimitError("large"), "size limit"),
        (PermissionError("denied"), "could not be read"),
    ],
)
def test_runtime_read_translates_bounded_io_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError,
    message: str,
) -> None:
    monkeypatch.setattr(
        runtime,
        "read_bounded_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error),
    )
    with pytest.raises(ValueError, match=message):
        runtime.read_dashboard_runtime(path="unused")


def test_runtime_remove_handles_busy_invalid_or_missing_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime,
        "read_dashboard_runtime",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    assert runtime.remove_dashboard_runtime(token="x" * 32, pid=1, path=tmp_path / "one") is False


def test_open_dashboard_reports_missing_unreachable_and_no_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = runtime.open_dashboard_service(path=tmp_path / "missing.json")
    assert missing["ok"] is False
    assert "no runtime descriptor" in missing["error"]

    monkeypatch.setattr(runtime, "read_dashboard_runtime", lambda **_kwargs: _descriptor())
    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: False)
    assert runtime.open_dashboard_service()["reachable"] is False

    monkeypatch.setattr(runtime, "dashboard_service_reachable", lambda **_kwargs: True)
    monkeypatch.setattr(
        runtime.webbrowser,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("browser opened")),
    )
    result = runtime.open_dashboard_service(open_browser=False)
    assert result["ok"] is True
    assert result["url"] == "http://127.0.0.1:7810/"
