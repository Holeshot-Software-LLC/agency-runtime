"""Final low-level dashboard service branch and portability regressions."""

from __future__ import annotations

import stat
import sys
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

from agency_runtime.core import dashboard_service as facade
from agency_runtime.core import dashboard_service_core as core
from agency_runtime.core import dashboard_service_manifest as manifest
from agency_runtime.core import dashboard_service_systemd as systemd
from agency_runtime.core import dashboard_service_windows as windows


def context(tmp_path, platform="linux"):
    result = core._context(
        home_dir=tmp_path,
        platform_name=platform,
        config_path=tmp_path / "agency.yaml",
        python_executable=tmp_path / "python",
    )
    assert result is not None
    if platform == "windows":
        result = core._Context(
            **{
                name: getattr(result, name)
                for name in result.__dataclass_fields__
                if name != "windows_user"
            },
            windows_user="S-1-5-test",
        )
    return result


class _Function:
    def __init__(self, callback):
        self.callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.callback(*args)


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("open-fail", None),
        ("required-zero", None),
        ("get-fail", None),
        ("convert-fail", None),
        ("success", "S-1-5-test"),
    ],
)
def test_windows_sid_api_failure_and_success_paths(monkeypatch, scenario, expected):
    import ctypes

    closed = []
    freed = []

    def open_token(_process, _access, token_pointer):
        if scenario == "open-fail":
            return 0
        token_pointer._obj.value = 1
        return 1

    def get_token(_token, _kind, buffer, _size, required_pointer):
        if scenario == "required-zero":
            return 0
        required_pointer._obj.value = 64
        if buffer is None:
            return 0
        return 0 if scenario == "get-fail" else 1

    def convert_sid(_sid, sid_pointer):
        if scenario == "convert-fail":
            return 0
        sid_pointer._obj.value = "S-1-5-test"
        return 1

    advapi = SimpleNamespace(
        OpenProcessToken=_Function(open_token),
        GetTokenInformation=_Function(get_token),
        ConvertSidToStringSidW=_Function(convert_sid),
    )
    kernel = SimpleNamespace(
        GetCurrentProcess=_Function(lambda: 1),
        CloseHandle=_Function(lambda token: closed.append(token) or 1),
        LocalFree=_Function(lambda value: freed.append(value) or None),
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kw: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(core.os, "name", "nt")
    assert core._windows_current_user_sid() == expected
    if scenario != "open-fail":
        assert closed
    assert bool(freed) is (scenario == "success")


def test_noncoroutine_awaitable_runner_is_rejected():
    class Awaitable:
        def __await__(self):
            yield

    result = core._run(["manager"], command_runner=lambda *_a, **_kw: Awaitable())
    assert result.returncode == 125


def test_manifest_follow_flags_missing_file_and_special_replaceable(tmp_path, monkeypatch):
    monkeypatch.setattr(manifest.os, "O_NOFOLLOW", 0, raising=False)
    path = tmp_path / "value"
    path.write_bytes(b"value")
    assert manifest._read_bounded_file(path, limit=5, label="value") == b"value"
    assert not manifest._file_matches(tmp_path / "missing", b"value")
    monkeypatch.setattr(
        manifest.os,
        "lstat",
        lambda _path: SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=0,
        ),
    )
    with pytest.raises(OSError, match="regular file"):
        manifest._assert_replaceable(path, label="value")


def test_prepare_parent_rejects_special_and_posix_chmods(tmp_path, monkeypatch):
    path = tmp_path / "parent" / "value"
    path.parent.mkdir()
    real_lstat = manifest.os.lstat
    monkeypatch.setattr(
        manifest.os,
        "lstat",
        lambda _path: SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0),
    )
    with pytest.raises(OSError, match="real directory"):
        manifest._prepare_private_parent(path)
    monkeypatch.setattr(manifest.os, "lstat", real_lstat)
    monkeypatch.setattr(manifest.os, "name", "posix")
    modes = []
    monkeypatch.setattr(
        type(path.parent),
        "chmod",
        lambda self, mode: modes.append((self, mode)),
    )
    manifest._prepare_private_parent(path)
    assert modes == [(path.parent, 0o700)]


def test_sync_parent_posix_and_windows_paths(tmp_path, monkeypatch):
    path = tmp_path / "parent" / "value"
    path.parent.mkdir()
    monkeypatch.setattr(manifest.os, "name", "nt")
    manifest._sync_parent(path)
    calls = []
    monkeypatch.setattr(manifest.os, "name", "posix")
    monkeypatch.setattr(manifest.os, "open", lambda *_a, **_kw: 7)
    monkeypatch.setattr(manifest.os, "fsync", lambda fd: calls.append(("fsync", fd)))
    monkeypatch.setattr(manifest.os, "close", lambda fd: calls.append(("close", fd)))
    manifest._sync_parent(path)
    assert calls == [("fsync", 7), ("close", 7)]


def test_atomic_and_restore_cleanup_open_handle_on_early_acl_error(tmp_path, monkeypatch):
    path = tmp_path / "state"
    monkeypatch.setattr(
        manifest,
        "restrict_private_file",
        lambda _path: (_ for _ in ()).throw(OSError("ACL failed")),
    )
    with pytest.raises(OSError, match="ACL failed"):
        manifest._atomic_write(path, "value")
    with pytest.raises(OSError, match="ACL failed"):
        manifest._restore_file(path, b"value")


def test_atomic_and_restore_without_fchmod(tmp_path, monkeypatch):
    path = tmp_path / "state"
    monkeypatch.delattr(manifest.os, "fchmod", raising=False)
    manifest._atomic_write(path, "value")
    assert path.read_text(encoding="utf-8") == "value"
    manifest._restore_file(path, b"restored")
    assert path.read_bytes() == b"restored"


def test_service_lock_posix_success_and_busy(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    calls = []
    fake = SimpleNamespace(
        LOCK_EX=1,
        LOCK_NB=2,
        LOCK_UN=4,
        flock=lambda _fd, operation: calls.append(operation),
    )
    monkeypatch.setitem(sys.modules, "fcntl", fake)
    monkeypatch.setattr(manifest.os, "name", "posix")
    monkeypatch.setattr(manifest.os, "O_NOFOLLOW", 0, raising=False)
    with manifest._service_lock(ctx, timeout=1):
        pass
    assert calls == [3, 4]

    fake.flock = lambda *_a: (_ for _ in ()).throw(OSError("busy"))
    with (
        pytest.raises(RuntimeError, match="busy"),
        manifest._service_lock(ctx, timeout=0),
    ):
        pass

    attempts = iter([OSError("contended"), None, None])

    def retry_then_lock(_fd, _operation):
        outcome = next(attempts)
        if outcome is not None:
            raise outcome

    fake.flock = retry_then_lock
    monkeypatch.setattr(manifest.time, "sleep", lambda _delay: None)
    with manifest._service_lock(ctx, timeout=1):
        pass


def test_systemd_unsafe_cleanup_failure_is_reported(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    monkeypatch.setattr(
        systemd,
        "_assert_systemd_files",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            RuntimeError("systemd service files changed before mutation")
        ),
    )
    monkeypatch.setattr(
        systemd,
        "_file_matches",
        lambda path, _expected: path == ctx.manifest_path,
    )
    monkeypatch.setattr(
        systemd,
        "_restore_file",
        lambda *_a: (_ for _ in ()).throw(OSError("cleanup failed")),
    )
    results = iter(
        [
            core._CommandResult(("enabled",), 0, "disabled"),
            core._CommandResult(("active",), 0, "inactive"),
        ]
    )
    monkeypatch.setattr(systemd, "_run", lambda *_a, **_kw: next(results))
    outcome = systemd._restore_systemd_state(
        ctx,
        prior_unit=None,
        prior_manifest=None,
        expected_unit=b"current",
        expected_manifest=b"manifest",
        prior_enabled=False,
        prior_active=False,
        command_runner=None,
    )
    assert "service files and ownership manifest changed" in outcome.error


def test_systemd_other_restore_error_skips_unsafe_cleanup(tmp_path, monkeypatch):
    ctx = context(tmp_path)
    monkeypatch.setattr(
        systemd,
        "_assert_systemd_files",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("other restore error")),
    )
    results = iter(
        [
            core._CommandResult(("enabled",), 0, "disabled"),
            core._CommandResult(("active",), 0, "inactive"),
        ]
    )
    monkeypatch.setattr(systemd, "_run", lambda *_a, **_kw: next(results))
    outcome = systemd._restore_systemd_state(
        ctx,
        prior_unit=None,
        prior_manifest=None,
        expected_unit=b"current",
        expected_manifest=b"manifest",
        prior_enabled=False,
        prior_active=False,
        command_runner=None,
    )
    assert outcome.error == "other restore error"


def test_windows_xml_missing_element_nested_optional_and_no_fchmod(tmp_path, monkeypatch):
    ctx = context(tmp_path, "windows")
    content = windows._windows_task_content(ctx)
    root = ET.fromstring(content)
    namespace = {"t": core.WINDOWS_TASK_XML_NAMESPACE}
    actions = root.find("t:Actions", namespace)
    assert actions is not None
    execute = actions.find("t:Exec", namespace)
    assert execute is not None
    actions.remove(execute)
    assert windows._windows_task_properties(ET.tostring(root, encoding="unicode")) is None

    root = ET.fromstring(content)
    registration = root.find("t:RegistrationInfo", namespace)
    assert registration is not None
    author = ET.SubElement(
        registration,
        f"{{{core.WINDOWS_TASK_XML_NAMESPACE}}}Author",
    )
    ET.SubElement(author, f"{{{core.WINDOWS_TASK_XML_NAMESPACE}}}Nested")
    assert windows._windows_task_properties(ET.tostring(root, encoding="unicode")) is None

    monkeypatch.delattr(windows.os, "fchmod", raising=False)
    result = windows._register_windows_xml(
        ctx,
        content,
        force=False,
        command_runner=lambda *_a, **_kw: {"returncode": 0},
    )
    assert result.ok


def test_facade_exports_public_contract():
    assert facade.OWNER_ID == core.OWNER_ID
    assert callable(facade.install_dashboard_service)
