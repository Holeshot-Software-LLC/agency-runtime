"""Final low-level dashboard service branch and portability regressions."""

from __future__ import annotations

import base64
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


@pytest.mark.parametrize("observed", [None, "S-1-5-test"])
def test_windows_sid_probe_delegates_to_shared_token_boundary(monkeypatch, observed):
    calls = []

    def probe(*, is_windows):
        calls.append(is_windows)
        return observed

    monkeypatch.setattr(core, "_IS_WINDOWS", True)
    monkeypatch.setattr(core, "current_process_user_sid", probe)

    assert core._windows_current_user_sid() == observed
    assert calls == [True]


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("convert-fail", None),
        ("size-zero", None),
        ("lookup-fail", None),
        ("success", "DOMAIN\\user"),
        ("success-no-domain", "user"),
    ],
)
def test_windows_sid_account_resolution_paths(monkeypatch, scenario, expected):
    import ctypes

    freed = []

    def convert_sid(_sid, sid_pointer):
        if scenario == "convert-fail":
            return 0
        sid_pointer._obj.value = 7
        return 1

    def lookup_account(
        _system,
        _sid,
        account,
        account_size,
        domain,
        domain_size,
        _sid_type,
    ):
        if account is None:
            if scenario == "size-zero":
                return 0
            account_size._obj.value = 8
            domain_size._obj.value = 1 if scenario == "success-no-domain" else 7
            return 0
        if scenario == "lookup-fail":
            return 0
        account.value = "user"
        domain.value = "" if scenario == "success-no-domain" else "DOMAIN"
        return 1

    advapi = SimpleNamespace(
        ConvertStringSidToSidW=_Function(convert_sid),
        LookupAccountSidW=_Function(lookup_account),
    )
    kernel = SimpleNamespace(LocalFree=_Function(lambda value: freed.append(value) or None))
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kw: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(core, "_IS_WINDOWS", True)

    assert core._windows_account_for_sid("S-1-5-test") == expected
    assert bool(freed) is (scenario != "convert-fail")


def test_windows_sid_account_resolution_non_windows_and_invalid(monkeypatch):
    monkeypatch.setattr(core, "_IS_WINDOWS", False)
    assert core._windows_account_for_sid("S-1-5-test") is None
    monkeypatch.setattr(core, "_IS_WINDOWS", True)
    assert core._windows_account_for_sid("bad\x00sid") is None


def test_windows_xml_transport_is_bounded_utf8_base64(monkeypatch):
    content = '<?xml version="1.0"?><Task><Description>smart “quote”</Description></Task>'

    def result(stdout="", *, returncode=0, stderr=""):
        return core._CommandResult(("powershell.exe",), returncode, stdout, stderr)

    monkeypatch.setattr(windows, "windows_system_command", lambda *args, **_kw: list(args))
    monkeypatch.setattr(
        windows,
        "_run",
        lambda *_a, **_kw: result(base64.b64encode(content.encode()).decode()),
    )
    decoded = windows._query_windows_xml(command_runner=None)
    assert decoded.ok and decoded.stdout == content
    assert "ToBase64String" in windows._WINDOWS_TASK_XML_SCRIPT

    failures = [
        result(returncode=1, stderr="denied"),
        result(""),
        result("é"),
        result("not-base64"),
        result("A" * (windows._MAX_TASK_XML_BASE64_BYTES + 1)),
        result(base64.b64encode(b"x" * (windows._MAX_TASK_XML_BYTES + 1)).decode()),
        result(base64.b64encode(b"\xff").decode()),
    ]
    expected_codes = [1, 125, 125, 125, 125, 125, 125]
    for failure, expected_code in zip(failures, expected_codes, strict=True):
        monkeypatch.setattr(windows, "_run", lambda *_a, value=failure, **_kw: value)
        assert windows._query_windows_xml(command_runner=None).returncode == expected_code


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
    monkeypatch.setattr(manifest, "_IS_WINDOWS", False)
    modes = []
    monkeypatch.setattr(
        manifest,
        "restrict_posix_path_permissions",
        lambda target, *, directory: modes.append((target, directory)),
    )
    manifest._prepare_private_parent(path)
    assert modes == [(path.parent, True)]


def test_sync_parent_posix_and_windows_paths(tmp_path, monkeypatch):
    path = tmp_path / "parent" / "value"
    path.parent.mkdir()
    monkeypatch.setattr(manifest, "_IS_WINDOWS", True)
    manifest._sync_parent(path)
    calls = []
    monkeypatch.setattr(manifest, "_IS_WINDOWS", False)
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
    monkeypatch.setattr(manifest, "_IS_WINDOWS", False)
    monkeypatch.setattr(manifest.os, "O_NOFOLLOW", 0, raising=False)
    monkeypatch.setattr(
        manifest,
        "restrict_posix_path_permissions",
        lambda *_args, **_kwargs: None,
    )
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
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("cleanup failed")),
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
