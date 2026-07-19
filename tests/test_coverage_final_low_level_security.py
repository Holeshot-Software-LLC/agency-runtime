"""Exact fail-closed coverage for low-level process and filesystem boundaries."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import private_paths, process_argv, windows_acl


def _directory_identity(path: Path) -> private_paths.PrivateDirectoryIdentity:
    return private_paths.PrivateDirectoryIdentity(path=path, device=1, inode=1)


def _status(
    *,
    inode: int = 2,
    mode: int = stat.S_IFREG | 0o700,
    size: int = 4,
    owner: int = 1000,
    file_attributes: int = 0,
) -> SimpleNamespace:
    return SimpleNamespace(
        st_dev=1,
        st_ino=inode,
        st_mode=mode,
        st_size=size,
        st_mtime_ns=5,
        st_uid=owner,
        st_file_attributes=file_attributes,
    )


def _artifact_identity(
    *, lexical_path: str = "/trusted/tool"
) -> process_argv.PersistentArtifactIdentity:
    return process_argv.PersistentArtifactIdentity(
        lexical_path=lexical_path,
        lexical_device=1,
        lexical_inode=2,
        lexical_mode=stat.S_IFREG | 0o700,
        lexical_size=4,
        lexical_modified_ns=5,
        lexical_file_attributes=0,
        link_target=None,
        resolved_path=lexical_path,
        resolved_device=1,
        resolved_inode=2,
        resolved_mode=stat.S_IFREG | 0o700,
        resolved_size=4,
        resolved_modified_ns=5,
        resolved_file_attributes=0,
        sha256="0" * 64,
    )


def test_host_descendant_accepts_each_trusted_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    child = root / "first" / "second"
    child.mkdir(parents=True)
    observed: list[Path] = []
    monkeypatch.setattr(private_paths, "metadata_is_link_or_reparse_point", lambda _meta: False)
    monkeypatch.setattr(
        private_paths,
        "windows_directory_prevents_untrusted_writes",
        lambda path, **_kwargs: observed.append(path) or True,
    )

    assert private_paths._host_descendant_is_private(child, _directory_identity(root))
    assert observed == [root / "first", child]


def test_host_descendant_namespace_fails_closed_for_each_invalid_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    authority = _directory_identity(root)
    target = root / "child"

    assert not private_paths._host_descendant_namespace_is_private(tmp_path / "escape", authority)

    monkeypatch.setattr(
        private_paths.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    assert not private_paths._host_descendant_namespace_is_private(target, authority)

    monkeypatch.setattr(private_paths.os, "lstat", lambda _path: _status())
    monkeypatch.setattr(private_paths, "metadata_is_link_or_reparse_point", lambda _meta: False)
    assert not private_paths._host_descendant_namespace_is_private(target, authority)

    monkeypatch.setattr(
        private_paths.os,
        "lstat",
        lambda _path: _status(mode=stat.S_IFDIR | 0o700),
    )
    monkeypatch.setattr(
        private_paths,
        "windows_directory_prevents_untrusted_writes",
        lambda *_args, **_kwargs: False,
    )
    assert not private_paths._host_descendant_namespace_is_private(target, authority)


class _CurrentGuard:
    def __init__(self) -> None:
        self.closed = False

    def is_current(self) -> bool:
        return True

    def close(self) -> None:
        self.closed = True


def test_codex_parent_pinning_returns_a_current_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visualizations = tmp_path / "visualizations"
    candidate = visualizations / "2026" / "07" / "16" / "019f4c7c-64ea-7650-a414-2680b0efabc6"
    candidate.mkdir(parents=True)
    guard = _CurrentGuard()
    monkeypatch.setattr(private_paths, "validate_private_directory", lambda path: path)
    monkeypatch.setattr(
        private_paths,
        "windows_restricted_host_boundary_is_trusted",
        lambda _path: True,
    )
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: guard,
    )

    assert private_paths._pin_codex_host_private_parent(candidate, visualizations) is guard
    assert guard.closed is False


def test_persistent_artifact_manifest_rejects_each_invalid_value_class() -> None:
    with pytest.raises(ValueError, match="must be an object"):
        process_argv.PersistentArtifactIdentity.from_manifest(None)
    with pytest.raises(ValueError, match="incomplete"):
        process_argv.PersistentArtifactIdentity.from_manifest({})

    manifest = _artifact_identity().manifest()
    manifest["lexical_path"] = ""
    with pytest.raises(ValueError, match="lexical_path"):
        process_argv.PersistentArtifactIdentity.from_manifest(manifest)

    manifest = _artifact_identity().manifest()
    manifest["link_target"] = 1
    with pytest.raises(ValueError, match="link_target"):
        process_argv.PersistentArtifactIdentity.from_manifest(manifest)

    manifest = _artifact_identity().manifest()
    manifest["lexical_device"] = True
    with pytest.raises(ValueError, match="lexical_device"):
        process_argv.PersistentArtifactIdentity.from_manifest(manifest)


def test_posix_access_acl_probe_distinguishes_absence_from_probe_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_argv.os, "getxattr", None, raising=False)
    assert not process_argv._posix_file_has_access_acl(Path("tool"))

    monkeypatch.setattr(process_argv.os, "getxattr", lambda *_args, **_kwargs: b"acl")
    assert process_argv._posix_file_has_access_acl(Path("tool"))

    def unavailable(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.ENODATA, "not present")

    monkeypatch.setattr(process_argv.os, "getxattr", unavailable)
    assert not process_argv._posix_file_has_access_acl(Path("tool"))

    def denied(*_args: Any, **_kwargs: Any) -> bytes:
        raise OSError(errno.EACCES, "denied")

    monkeypatch.setattr(process_argv.os, "getxattr", denied)
    assert process_argv._posix_file_has_access_acl(Path("tool"))


def test_posix_artifact_trust_requires_verifiable_owner_and_private_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(process_argv.os, "geteuid", None, raising=False)
    with pytest.raises(PermissionError, match="ownership cannot be verified"):
        process_argv._assert_executable_artifact_trusted(
            "/trusted/tool",
            _status(),
            platform_name="posix",
        )

    monkeypatch.setattr(process_argv.os, "geteuid", lambda: 1000, raising=False)
    with pytest.raises(PermissionError, match="untrusted owner"):
        process_argv._assert_executable_artifact_trusted(
            "/trusted/tool",
            _status(owner=2000),
            platform_name="posix",
        )

    monkeypatch.setattr(process_argv, "_posix_file_has_access_acl", lambda _path: False)
    process_argv._assert_executable_artifact_trusted(
        "/trusted/tool",
        _status(),
        platform_name="posix",
    )


def test_opened_metadata_identity_uses_full_posix_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = _status()
    monkeypatch.setattr(process_argv.os, "name", "posix")

    assert process_argv._opened_metadata_identity(observed) == process_argv._metadata_identity(
        observed
    )


def _patch_hash_io(
    monkeypatch: pytest.MonkeyPatch,
    *,
    statuses: list[SimpleNamespace],
    chunks: list[bytes],
    path_status: SimpleNamespace,
) -> tuple[list[int], list[int]]:
    flags: list[int] = []
    closed: list[int] = []
    status_values = iter(statuses)
    chunk_values = iter(chunks)
    monkeypatch.setattr(
        process_argv.os,
        "open",
        lambda _path, value: flags.append(value) or 7,
    )
    monkeypatch.setattr(process_argv.os, "fstat", lambda _descriptor: next(status_values))
    monkeypatch.setattr(process_argv.os, "read", lambda _descriptor, _size: next(chunk_values))
    monkeypatch.setattr(process_argv.os, "close", closed.append)
    monkeypatch.setattr(process_argv.os, "lstat", lambda _path: path_status)
    return flags, closed


def test_stable_hash_applies_no_follow_and_accepts_a_stable_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _status()
    monkeypatch.setattr(process_argv.os, "O_NOFOLLOW", 0x100, raising=False)
    monkeypatch.setattr(process_argv.os, "O_BINARY", 0x200, raising=False)
    monkeypatch.setattr(process_argv.os, "O_RDONLY", 0)
    flags, closed = _patch_hash_io(
        monkeypatch,
        statuses=[expected, expected],
        chunks=[b"data", b""],
        path_status=expected,
    )

    assert process_argv._stable_file_sha256("tool", expected) == hashlib.sha256(b"data").hexdigest()
    assert flags == [0x300]
    assert closed == [7]


def test_stable_hash_rejects_size_and_identity_races(monkeypatch: pytest.MonkeyPatch) -> None:
    oversized = _status(size=4)
    monkeypatch.setattr(process_argv, "_MAX_PERSISTENT_ARTIFACT_BYTES", 3)
    with pytest.raises(OSError, match="size limit"):
        process_argv._stable_file_sha256("tool", oversized)

    expected = _status(size=3)
    opened_elsewhere = _status(inode=9, size=3)
    _patch_hash_io(
        monkeypatch,
        statuses=[opened_elsewhere],
        chunks=[],
        path_status=expected,
    )
    with pytest.raises(OSError, match="changed while opening"):
        process_argv._stable_file_sha256("tool", expected)

    _patch_hash_io(
        monkeypatch,
        statuses=[expected],
        chunks=[b"four"],
        path_status=expected,
    )
    with pytest.raises(OSError, match="size limit"):
        process_argv._stable_file_sha256("tool", expected)

    changed = _status(inode=10, size=3)
    _patch_hash_io(
        monkeypatch,
        statuses=[expected, changed],
        chunks=[b""],
        path_status=expected,
    )
    with pytest.raises(OSError, match="changed while hashing"):
        process_argv._stable_file_sha256("tool", expected)


def test_snapshot_rejects_unavailable_reparse_and_non_regular_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "tool"
    monkeypatch.setattr(
        process_argv.os,
        "lstat",
        lambda _path: (_ for _ in ()).throw(ValueError("invalid")),
    )
    with pytest.raises(FileNotFoundError, match="unavailable"):
        process_argv.snapshot_persistent_artifact(path, platform_name="nt")

    monkeypatch.setattr(
        process_argv.os,
        "lstat",
        lambda _path: _status(file_attributes=process_argv._WINDOWS_REPARSE_POINT),
    )
    with pytest.raises(OSError, match="Windows link or reparse point"):
        process_argv.snapshot_persistent_artifact(path, platform_name="nt")

    monkeypatch.setattr(
        process_argv.os,
        "lstat",
        lambda _path: _status(mode=stat.S_IFDIR | 0o700),
    )
    with pytest.raises(OSError, match="regular file"):
        process_argv.snapshot_persistent_artifact(path, platform_name="posix")


def test_snapshot_posix_symlink_requires_owner_and_preserves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "tool"
    lexical = _status(mode=stat.S_IFLNK | 0o700)
    monkeypatch.setattr(process_argv.os, "lstat", lambda _path: lexical)
    monkeypatch.setattr(process_argv.os, "geteuid", None, raising=False)
    with pytest.raises(PermissionError, match="untrusted owner"):
        process_argv.snapshot_persistent_artifact(path, platform_name="posix")

    monkeypatch.setattr(process_argv.os, "geteuid", lambda: 2000, raising=False)
    with pytest.raises(PermissionError, match="untrusted owner"):
        process_argv.snapshot_persistent_artifact(path, platform_name="posix")

    monkeypatch.setattr(process_argv.os, "geteuid", lambda: 1000, raising=False)
    monkeypatch.setattr(process_argv.os, "readlink", lambda _path: "target")
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_args, **_kwargs: None)
    canonical = str(tmp_path / "resolved")
    resolved = _status()
    monkeypatch.setattr(
        process_argv,
        "_canonical_regular_file",
        lambda *_args, **_kwargs: (canonical, resolved),
    )
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(process_argv, "_stable_file_sha256", lambda *_args: "a" * 64)

    assert (
        process_argv.snapshot_persistent_artifact(path, platform_name="posix").link_target
        == "target"
    )


def test_revalidation_requires_identity_and_rejects_resolved_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(OSError, match="no frozen artifact identity"):
        process_argv.revalidate_persistent_artifacts((), platform_name="posix")

    frozen = _artifact_identity()
    observed = _status()
    monkeypatch.setattr(process_argv.os, "lstat", lambda _path: observed)
    monkeypatch.setattr(process_argv, "assert_executable_namespace", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        process_argv,
        "_canonical_regular_file",
        lambda *_args, **_kwargs: ("/trusted/replaced", observed),
    )
    monkeypatch.setattr(
        process_argv,
        "_assert_executable_artifact_trusted",
        lambda *_args, **_kwargs: None,
    )

    with pytest.raises(OSError, match="drifted"):
        process_argv.revalidate_persistent_artifacts((frozen,), platform_name="posix")


class _Api:
    def __init__(self, function: Any) -> None:
        self.function = function
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.function(*args)


class _SidAndAttributes(ctypes.Structure):
    _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", ctypes.wintypes.DWORD)]


class _TokenGroups(ctypes.Structure):
    _fields_ = [("GroupCount", ctypes.wintypes.DWORD), ("Groups", _SidAndAttributes * 1)]


def _install_native_sid_apis(
    monkeypatch: pytest.MonkeyPatch,
    *,
    sid: str,
    attributes: int,
) -> tuple[list[Any], list[Any]]:
    rendered = ctypes.create_unicode_buffer(sid)
    freed: list[Any] = []
    closed: list[Any] = []

    def get_token(
        _token: Any,
        _kind: int,
        output: Any,
        _size: Any,
        required: Any,
    ) -> bool:
        if output is None:
            required._obj.value = ctypes.sizeof(_TokenGroups)
            return True
        groups = ctypes.cast(output, ctypes.POINTER(_TokenGroups)).contents
        groups.GroupCount = 1
        groups.Groups[0].Sid = 101
        groups.Groups[0].Attributes = attributes
        return True

    def convert_sid(_sid: Any, output: Any) -> bool:
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.addressof(rendered)
        return True

    advapi = SimpleNamespace(
        GetTokenInformation=_Api(get_token),
        ConvertSidToStringSidW=_Api(convert_sid),
    )
    kernel = SimpleNamespace(
        GetCurrentProcess=_Api(lambda: 1),
        CloseHandle=_Api(lambda handle: closed.append(handle) or True),
        LocalFree=_Api(lambda value: freed.append(value)),
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(windows_acl, "_open_effective_token", lambda *_args: 7)
    return freed, closed


def test_native_restricted_sid_readers_return_and_release_rendered_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freed, closed = _install_native_sid_apis(
        monkeypatch,
        sid="S-1-5-5-1-2",
        attributes=4,
    )
    assert windows_acl.current_process_restricted_sids(is_windows=True) == frozenset(
        {"S-1-5-5-1-2"}
    )
    assert len(freed) == 1
    assert closed == [7]

    freed, closed = _install_native_sid_apis(
        monkeypatch,
        sid="S-1-5-5-1-2",
        attributes=4,
    )
    assert windows_acl._current_process_token_sid_entries(11, is_windows=True) == (
        ("S-1-5-5-1-2", 4),
    )
    assert len(freed) == 1
    assert closed == [7]


def test_windows_file_acl_probe_fails_closed_for_unavailable_or_malformed_state() -> None:
    path = Path("tool.exe")
    sid = "S-1-5-21-42"
    assert not windows_acl.windows_file_prevents_untrusted_mutation(path, is_windows=False)
    assert not windows_acl.windows_file_prevents_untrusted_mutation(
        path,
        is_windows=True,
        sddl_reader=lambda _path: (_ for _ in ()).throw(OSError("unavailable")),
        current_sid_reader=lambda: sid,
        trusted_sid_reader=frozenset,
    )
    assert not windows_acl.windows_file_prevents_untrusted_mutation(
        path,
        is_windows=True,
        sddl_reader=lambda _path: f"O:{sid}D:NO_ACCESS_CONTROL",
        current_sid_reader=lambda: sid,
        trusted_sid_reader=frozenset,
    )
    assert not windows_acl.windows_file_prevents_untrusted_mutation(
        path,
        is_windows=True,
        sddl_reader=lambda _path: f"O:{sid}D:P(A;broken)",
        current_sid_reader=lambda: sid,
        trusted_sid_reader=frozenset,
    )
