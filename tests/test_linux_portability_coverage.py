"""Cross-platform coverage that must remain deterministic on Linux runners.

These tests use module-local platform seams and OS facades.  They deliberately
never mutate process-wide ``os.name`` or remove attributes from the shared
``os`` module.
"""

from __future__ import annotations

import ctypes
import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import (
    configuration,
    dashboard_runtime,
    dashboard_service_core,
    doctor,
    installer_native,
    process_argv,
)
from agency_runtime.core import configuration_persistence as persistence
from agency_runtime.core import dashboard_service_manifest as manifest
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.delegation import backend_process, backend_windows, backends
from agency_runtime.core.roster import ingress
from agency_runtime.core.store import security
from agency_runtime.core.store import sqlite as sqlite_store
from agency_runtime.core.store.sqlite import Store


class _OSFacade:
    """Delegate to the real OS module while exposing only local overrides."""

    def __init__(
        self,
        real_os: Any,
        *,
        missing: frozenset[str] = frozenset(),
        **overrides: Any,
    ) -> None:
        self._real_os = real_os
        self._missing = missing
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._missing:
            raise AttributeError(name)
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._real_os, name)


def test_configuration_windows_acl_facade_delegates_locally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, bool, bool]] = []

    def restrict(path: Path, *, directory: bool, is_windows: bool) -> bool:
        calls.append((path, directory, is_windows))
        return True

    monkeypatch.setattr(configuration, "_IS_WINDOWS", True)
    monkeypatch.setattr(persistence, "restrict_windows_acl", restrict)

    assert configuration._restrict_windows_acl(tmp_path, directory=True) is True
    assert calls == [(tmp_path, True, True)]


def test_config_lock_accepts_binary_flag_without_global_os_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    operations: list[int] = []
    fake_fcntl = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda _descriptor, operation: operations.append(operation),
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setattr(
        persistence,
        "os",
        _OSFacade(persistence.os, O_BINARY=getattr(os, "O_BINARY", 0)),
    )

    with persistence.config_lock(
        tmp_path / "agency.yaml",
        ensure_parent=lambda _path: None,
        restrict=lambda *_args, **_kwargs: True,
        path_check=lambda _path: False,
        is_windows=False,
    ):
        pass

    assert operations == [fake_fcntl.LOCK_EX | fake_fcntl.LOCK_NB, fake_fcntl.LOCK_UN]


def _runtime_descriptor() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "pid": 1,
        "port": 7810,
        "token": "x" * 32,
        "started_at": "2026-07-13T00:00:00+00:00",
    }


def test_dashboard_publish_covers_windows_parent_policy_locally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        dashboard_runtime,
        "os",
        _OSFacade(dashboard_runtime.os, name="nt"),
    )
    target = tmp_path / "dashboard.json"

    dashboard_runtime._publish_dashboard_runtime(target, _runtime_descriptor())

    assert dashboard_runtime.read_dashboard_runtime(path=target) == _runtime_descriptor()


def test_manifest_reads_and_opens_without_nofollow_attribute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        manifest,
        "os",
        _OSFacade(manifest.os, missing=frozenset({"O_NOFOLLOW"})),
    )
    source = tmp_path / "source"
    source.write_bytes(b"value")

    assert manifest._read_bounded_file(source, limit=5, label="source") == b"value"
    lock = manifest._open_lock(tmp_path / "lock")
    lock.close()


def test_manifest_lock_rejects_changed_descriptor_and_closes_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_os = manifest.os

    def changed_fstat(descriptor: int) -> Any:
        observed = real_os.fstat(descriptor)
        return SimpleNamespace(
            st_dev=observed.st_dev,
            st_ino=observed.st_ino + 1,
            st_mode=observed.st_mode,
            st_file_attributes=0,
        )

    monkeypatch.setattr(manifest, "os", _OSFacade(real_os, fstat=changed_fstat))

    with pytest.raises(OSError, match="regular file"):
        manifest._open_lock(tmp_path / "lock")


def test_manifest_windows_parent_and_lock_paths_use_local_seam(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = dashboard_service_core._context(
        home_dir=tmp_path,
        platform_name="linux",
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert ctx is not None
    calls: list[int] = []
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=1,
        LK_UNLCK=2,
        locking=lambda _descriptor, operation, _size: calls.append(operation),
    )
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(manifest, "_IS_WINDOWS", True)

    with manifest._service_lock(ctx):
        pass

    assert calls == [fake_msvcrt.LK_NBLCK, fake_msvcrt.LK_UNLCK]


def test_backend_process_windows_only_branches_are_platform_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(backend_process, "_IS_WINDOWS", True)
    assert backend_process._posix_process_group_active(SimpleNamespace(pid=1)) is False

    kwargs = backend_process._owned_process_kwargs(platform_name="nt", suspended=True)
    expected_suspended = getattr(subprocess, "CREATE_SUSPENDED", 0x00000004)
    assert int(kwargs["creationflags"]) & expected_suspended

    process = SimpleNamespace(poll=lambda: 0)
    job = SimpleNamespace(terminate=lambda: True)
    monkeypatch.setattr(backend_process, "_wait_for_process", lambda *_args: True)
    monkeypatch.setattr(
        backend_process,
        "_kill_and_reap_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected kill")),
    )
    backend_process._terminate_windows_job(process, job)


class _NativeFunction:
    def __init__(self, callback: Callable[..., Any]) -> None:
        self.callback = callback
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.callback(*args)


class _JobKernel:
    def __init__(self) -> None:
        self.closed: list[int] = []
        self.CreateJobObjectW = _NativeFunction(lambda *_args: 123)
        self.SetInformationJobObject = _NativeFunction(lambda *_args: True)
        self.AssignProcessToJobObject = _NativeFunction(lambda *_args: True)

        def query(_handle: Any, _kind: int, accounting: Any, *_args: Any) -> bool:
            accounting._obj.ActiveProcesses = 2
            return True

        self.QueryInformationJobObject = _NativeFunction(query)
        self.TerminateJobObject = _NativeFunction(lambda *_args: True)
        self.CloseHandle = _NativeFunction(lambda handle: self.closed.append(int(handle)) or True)


class _ThreadKernel:
    def __init__(self, *, owner: int) -> None:
        self.owner = owner
        self.closed: list[int] = []
        self.CreateToolhelp32Snapshot = _NativeFunction(lambda *_args: 123)

        def first(_snapshot: Any, entry: Any) -> bool:
            entry._obj.th32OwnerProcessID = self.owner
            entry._obj.th32ThreadID = 7
            return True

        self.Thread32First = _NativeFunction(first)
        self.Thread32Next = _NativeFunction(lambda *_args: False)
        self.OpenThread = _NativeFunction(lambda *_args: 456)
        self.ResumeThread = _NativeFunction(lambda *_args: 0)
        self.CloseHandle = _NativeFunction(lambda handle: self.closed.append(int(handle)) or True)


def test_windows_job_success_contracts_run_on_every_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Accounting(ctypes.Structure):
        _fields_ = [("ActiveProcesses", ctypes.c_ulong)]

    kernel = _JobKernel()
    direct = backend_windows.WindowsJob(123, kernel, Accounting)
    assert direct.active_processes() == 2
    assert direct.terminate() is True

    monkeypatch.setattr(backend_windows, "_IS_WINDOWS", True)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    created = backend_windows.create_windows_job(SimpleNamespace(_handle=456))
    assert created is not None
    created.close()
    assert kernel.closed == [123]


@pytest.mark.parametrize(("owner", "expected"), [(10, True), (11, False)])
def test_windows_resume_success_and_nonmatching_thread_paths(
    monkeypatch: pytest.MonkeyPatch,
    owner: int,
    expected: bool,
) -> None:
    kernel = _ThreadKernel(owner=owner)
    monkeypatch.setattr(backend_windows, "_IS_WINDOWS", True)
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    assert backend_windows.resume_windows_process(10) is expected
    assert kernel.closed == ([456, 123] if expected else [123])


def test_windows_job_quiescence_waits_for_descendants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = iter([1, 0])
    clock = iter([0.0, 0.1])
    sleeps: list[float] = []
    job = SimpleNamespace(active_processes=lambda: next(active))
    monkeypatch.setattr(backends.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(backends.time, "sleep", sleeps.append)

    assert backends._windows_job_has_active_processes(job) is False
    assert sleeps == [0.02]


def test_adapter_checks_append_codex_hook_trust_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "_http_check", lambda *_args, **_kwargs: (False, "offline"))
    monkeypatch.setattr(
        doctor,
        "inspect_host_installations",
        lambda **_kwargs: [
            {
                "host": "codex",
                "discovered": True,
                "registered": True,
                "enabled": True,
                "hook_trust_status": "trusted",
            }
        ],
    )

    checks = doctor._adapter_checks(AgencyConfig())

    assert any(check.name == "adapter_codex_hook_trust" for check in checks)


def test_installer_and_process_argv_cover_windows_discovery_without_host_dependency(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert tmp_path / "hermes" in installer_native._host_evidence_paths("hermes")

    resolved = process_argv.prepare_process_argv(
        ["agent", "task"],
        platform_name="nt",
        resolver=lambda _name: str(tmp_path / "agent.exe"),
    )
    assert resolved == [str(tmp_path / "agent.exe"), "task"]


def test_roster_local_read_without_nofollow_attribute(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "agents.json"
    source.write_text('{"agents": []}', encoding="utf-8")
    monkeypatch.setattr(
        ingress,
        "os",
        _OSFacade(ingress.os, missing=frozenset({"O_NOFOLLOW"})),
    )

    text, size = ingress._read_local_file(source)

    assert text == '{"agents": []}'
    assert size == len(text.encode("utf-8"))


class _PermissionPath:
    def __init__(self, *, mode: int = stat.S_IFREG | 0o600, fingerprint: tuple[int, int]) -> None:
        self.mode = mode
        self.fingerprint = fingerprint

    def lstat(self) -> Any:
        return SimpleNamespace(
            st_mode=self.mode,
            st_dev=self.fingerprint[0],
            st_ino=self.fingerprint[1],
            st_file_attributes=0,
        )


def test_store_windows_security_facades_and_success_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, bool, bool]] = []

    def restrict(path: Path, *, directory: bool, is_windows: bool) -> bool:
        calls.append((path, directory, is_windows))
        return True

    monkeypatch.setattr(security, "_restrict_windows_acl", restrict)
    assert security.restrict_windows_acl(tmp_path, directory=True, is_windows=True) is True
    security.restrict_path_permissions(
        _PermissionPath(fingerprint=(1, 2)),  # type: ignore[arg-type]
        directory=False,
        is_windows=True,
        link_checker=lambda _path: False,
        windows_acl=lambda *_args, **_kwargs: True,
    )

    monkeypatch.setattr(sqlite_store, "restrict_windows_acl", restrict)
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    assert sqlite_store._restrict_windows_acl(tmp_path, directory=False) is True
    assert calls == [(tmp_path, True, True), (tmp_path, False, True)]


def test_store_private_file_creation_accepts_binary_flag_locally(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = Store.__new__(Store)
    store.db_path = tmp_path / "agency.db"
    store._harden_storage_parent = False
    monkeypatch.setattr(store, "_assert_storage_paths_safe", lambda: None)
    monkeypatch.setattr(sqlite_store, "_is_link_or_reparse_point", lambda _path: False)
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        sqlite_store,
        "os",
        _OSFacade(sqlite_store.os, O_BINARY=getattr(os, "O_BINARY", 0)),
    )

    store._ensure_private_storage_file()

    assert store.db_path.is_file()


def test_store_windows_permission_cache_skips_and_records_fingerprints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = _PermissionPath(fingerprint=(1, 2))
    repaired = _PermissionPath(mode=stat.S_IFREG | 0o644, fingerprint=(3, 4))
    store = Store.__new__(Store)
    store.db_path = Path("agency.db")
    store._harden_storage_parent = False
    store._permission_fingerprints = {cached: (1, 2)}  # type: ignore[dict-item]
    restricted: list[Any] = []
    monkeypatch.setattr(sqlite_store, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        sqlite_store,
        "_sqlite_storage_paths",
        lambda _path: (cached, repaired),
    )
    monkeypatch.setattr(
        sqlite_store,
        "_metadata_is_link_or_reparse_point",
        lambda _metadata: False,
    )
    monkeypatch.setattr(
        sqlite_store,
        "_restrict_path_permissions",
        lambda path, **_kwargs: restricted.append(path),
    )

    store._repair_storage_permissions()

    assert restricted == [repaired]
    assert store._permission_fingerprints[repaired] == (3, 4)
