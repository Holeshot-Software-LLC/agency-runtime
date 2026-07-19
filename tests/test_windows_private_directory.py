"""Fail-closed coverage for handle-bound Windows private directories."""

from __future__ import annotations

import ctypes
import os
import stat
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import windows_private_directory as private
from agency_runtime.core.windows_acl import (
    RestrictedWindowsTokenError,
    WindowsACLSafetyError,
    WindowsTokenProbeError,
)


class _Function:
    def __init__(self, callback: Any) -> None:
        self.callback = callback
        self.argtypes = None
        self.restype = None

    def __call__(self, *args: Any) -> Any:
        return self.callback(*args)


def _guard(
    path: Path,
    *,
    current: bool = True,
    closer: Any | None = None,
) -> private.WindowsDirectoryGuard:
    metadata = os.lstat(path)
    inode = int(metadata.st_ino)
    return private.WindowsDirectoryGuard(
        path,
        int(metadata.st_dev),
        inode,
        41,
        lambda _handle: inode if current else inode + 1,
        closer or (lambda _handle: None),
    )


def test_directory_guard_tracks_path_handle_and_close_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    closed: list[int] = []
    guard = _guard(path, closer=closed.append)

    assert guard.is_current()
    guard.close()
    guard.close()
    assert guard.closed
    assert not guard.is_current()
    assert closed == [41]

    missing = _guard(path)
    monkeypatch.setattr(private.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError()))
    assert not missing.is_current()


@pytest.mark.parametrize("change", ["reparse", "device", "inode", "handle"])
def test_directory_guard_rejects_each_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    change: str,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    metadata = os.lstat(path)
    inode = int(metadata.st_ino)
    attributes = 0x400 if change == "reparse" else 0
    fake = SimpleNamespace(
        st_file_attributes=attributes,
        st_dev=int(metadata.st_dev) + (change == "device"),
        st_ino=inode + (change == "inode"),
    )
    monkeypatch.setattr(private.os, "lstat", lambda _path: fake)
    guard = private.WindowsDirectoryGuard(
        path,
        int(metadata.st_dev),
        inode,
        41,
        lambda _handle: inode + (change == "handle"),
        lambda _handle: None,
    )

    assert not guard.is_current()


@pytest.mark.parametrize("result", ["success", "failure", "exception"])
def test_windows_handle_identity_native_paths(
    monkeypatch: pytest.MonkeyPatch,
    result: str,
) -> None:
    expected = (7 << 32) | 11

    def get_information(_handle: int, pointer: Any) -> bool:
        if result == "exception":
            raise TypeError("bad handle")
        pointer._obj.index_high = 7
        pointer._obj.index_low = 11
        return result == "success"

    kernel = SimpleNamespace(GetFileInformationByHandle=_Function(get_information))
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)

    actual = private._windows_directory_handle_identity(41)

    assert actual == (expected if result == "success" else None)


def test_close_windows_handle_native_and_failure_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    closed: list[int] = []
    kernel = SimpleNamespace(CloseHandle=_Function(lambda handle: closed.append(handle) or True))
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    private._close_windows_handle(41)
    assert closed == [41]

    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
        raising=False,
    )
    private._close_windows_handle(42)


def _patch_create_file(monkeypatch: pytest.MonkeyPatch, result: int | None) -> list[int]:
    calls: list[int] = []
    kernel = SimpleNamespace(
        CreateFileW=_Function(lambda *_args: calls.append(1) or result),
    )
    monkeypatch.setattr(ctypes, "WinDLL", lambda *_args, **_kwargs: kernel, raising=False)
    return calls


def test_open_directory_guard_non_windows_and_invalid_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    assert private.open_windows_directory_guard(path, is_windows=False) is None

    monkeypatch.setattr(private.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError()))
    assert private.open_windows_directory_guard(path, is_windows=True) is None

    for metadata in (
        SimpleNamespace(st_file_attributes=0x400, st_mode=stat.S_IFDIR, st_ino=1),
        SimpleNamespace(st_file_attributes=0, st_mode=stat.S_IFREG, st_ino=1),
        SimpleNamespace(st_file_attributes=0, st_mode=stat.S_IFDIR, st_ino=0),
    ):
        monkeypatch.setattr(private.os, "lstat", lambda _path, value=metadata: value)
        assert private.open_windows_directory_guard(path, is_windows=True) is None


@pytest.mark.parametrize("native_result", [None, ctypes.c_void_p(-1).value])
def test_open_directory_guard_rejects_invalid_native_handle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    native_result: int | None,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    _patch_create_file(monkeypatch, native_result)

    assert private.open_windows_directory_guard(path, is_windows=True) is None


def test_open_directory_guard_returns_current_guard_or_closes_stale_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    inode = int(os.lstat(path).st_ino)
    closed: list[int] = []
    _patch_create_file(monkeypatch, 41)
    monkeypatch.setattr(private, "_close_windows_handle", closed.append)
    monkeypatch.setattr(private, "_windows_directory_handle_identity", lambda _handle: inode)
    guard = private.open_windows_directory_guard(path, is_windows=True)
    assert guard is not None and guard.is_current()
    guard.close()
    assert closed == [41]

    _patch_create_file(monkeypatch, 42)
    monkeypatch.setattr(private, "_windows_directory_handle_identity", lambda _handle: inode + 1)
    assert private.open_windows_directory_guard(path, is_windows=True) is None
    assert closed == [41, 42]


def test_open_directory_guard_native_exception_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("unavailable")),
        raising=False,
    )
    assert private.open_windows_directory_guard(path, is_windows=True) is None


def _patch_security_libraries(
    monkeypatch: pytest.MonkeyPatch,
    *,
    convert: bool = True,
    operation: bool = True,
    create: bool = False,
    last_error: int = 0,
) -> list[Any]:
    freed: list[Any] = []

    def convert_descriptor(_sddl: str, _revision: int, pointer: Any, _length: Any) -> bool:
        if convert:
            pointer._obj.value = 123
        return convert

    advapi = SimpleNamespace(
        ConvertStringSecurityDescriptorToSecurityDescriptorW=_Function(convert_descriptor),
        SetFileSecurityW=_Function(lambda *_args: operation),
    )
    kernel = SimpleNamespace(
        LocalFree=_Function(lambda value: freed.append(value) or None),
        CreateDirectoryW=_Function(lambda *_args: create),
    )
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda name, **_kwargs: advapi if name.startswith("Advapi") else kernel,
        raising=False,
    )
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)
    monkeypatch.setattr(ctypes, "set_last_error", lambda _value: None, raising=False)
    return freed


@pytest.mark.parametrize(
    ("convert", "operation", "expected", "free_count"),
    [(False, True, False, 0), (True, False, False, 1), (True, True, True, 1)],
)
def test_set_windows_file_security_result_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    convert: bool,
    operation: bool,
    expected: bool,
    free_count: int,
) -> None:
    freed = _patch_security_libraries(monkeypatch, convert=convert, operation=operation)
    assert private._set_windows_file_security(tmp_path, "D:P") is expected
    assert len(freed) == free_count


def test_set_windows_file_security_native_exception_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        ctypes,
        "WinDLL",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad descriptor")),
        raising=False,
    )
    assert not private._set_windows_file_security(tmp_path, "D:P")


@pytest.mark.parametrize(
    ("convert", "created", "last_error", "expected"),
    [
        (True, True, 0, True),
        (True, False, private._ERROR_ALREADY_EXISTS, None),
    ],
)
def test_create_windows_directory_result_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    convert: bool,
    created: bool,
    last_error: int,
    expected: bool | None,
) -> None:
    freed = _patch_security_libraries(
        monkeypatch,
        convert=convert,
        create=created,
        last_error=last_error,
    )
    assert private._create_windows_directory_with_sddl(tmp_path / "child", "D:P") is expected
    assert len(freed) == 1


@pytest.mark.parametrize("scenario", ["convert", "create", "native"])
def test_create_windows_directory_errors_are_normalized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scenario: str,
) -> None:
    if scenario == "native":
        monkeypatch.setattr(
            ctypes,
            "WinDLL",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("missing")),
            raising=False,
        )
    else:
        _patch_security_libraries(
            monkeypatch,
            convert=scenario != "convert",
            create=False,
            last_error=5,
        )
    with pytest.raises(
        WindowsACLSafetyError,
        match=r"could not be created|descriptor is invalid",
    ):
        private._create_windows_directory_with_sddl(tmp_path / "child", "D:P")


def test_sddl_and_exact_acl_receipt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    assert private._logon_private_sddl("USER", "LOGON", deny_delete=True) == (
        "O:USERD:P(D;;SD;;;AU)(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)(A;OICI;FA;;;LOGON)"
    )
    without_deny = private._logon_private_sddl("USER", "LOGON", deny_delete=False)
    assert without_deny == "O:USERD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)(A;OICI;FA;;;LOGON)"
    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: without_deny)
    assert private._logon_private_acl_is_present(tmp_path, "USER", "LOGON", deny_delete=False)
    assert not private._logon_private_acl_is_present(tmp_path, "USER", "LOGON", deny_delete=True)

    sealed_owner = private._owner_private_sddl("USER")
    assert sealed_owner == "O:USERD:P(D;;SD;;;AU)(A;OICI;FA;;;USER)"
    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: sealed_owner)
    assert private._owner_private_acl_is_present(tmp_path, "USER")
    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: "O:USERD:P")
    assert not private._owner_private_acl_is_present(tmp_path, "USER")


def test_persistent_root_acl_accepts_exact_or_canonical_private_form(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    exact = private._owner_private_sddl("USER")
    canonical = "O:USERD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)(D;;SD;;;AU)"
    semantic_calls: list[tuple[Path, str, str]] = []

    def semantic(path: Path, **kwargs: object) -> bool:
        sid_reader = kwargs["current_sid_reader"]
        sddl_reader = kwargs["sddl_reader"]
        assert callable(sid_reader)
        assert callable(sddl_reader)
        semantic_calls.append((path, sid_reader(), sddl_reader(path)))
        assert kwargs["final_parent"] is True
        assert kwargs["private_access"] is True
        return True

    monkeypatch.setattr(private, "windows_directory_prevents_untrusted_writes", semantic)
    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: exact)
    assert private._persistent_root_acl_is_present(tmp_path, "USER")
    assert semantic_calls == []

    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: canonical)
    assert private._persistent_root_acl_is_present(tmp_path, "USER")
    assert semantic_calls == [(tmp_path, "USER", canonical)]

    monkeypatch.setattr(
        private,
        "windows_directory_prevents_untrusted_writes",
        lambda *_args, **_kwargs: False,
    )
    assert not private._persistent_root_acl_is_present(tmp_path, "USER")


@pytest.mark.parametrize(
    ("sddl", "expected", "failure"),
    [
        (
            "O:USERD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;USER)",
            True,
            None,
        ),
        ("O:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)", False, "owner mismatch"),
        (
            "O:S-1-5-18D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)",
            False,
            "owner mismatch",
        ),
        (
            "O:S-1-5-32-544D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)",
            False,
            "owner mismatch",
        ),
        ("O:OTHERD:P(A;OICI;FA;;;USER)", False, "owner mismatch"),
        ("O:COD:P(A;OICI;FA;;;USER)", False, "owner mismatch"),
        ("O:OWD:P(A;OICI;FA;;;USER)", False, "owner mismatch"),
        ("D:P(A;OICI;FA;;;USER)", False, "owner missing"),
        ("O:USER", False, "DACL missing"),
        ("O:USERD:AI(A;OICI;FA;;;USER)", False, "DACL not protected"),
        (
            "O:USERD:P(A;;GR;;;BU)(A;OICI;FA;;;USER)",
            False,
            "DACL not private or malformed",
        ),
        (
            "O:USERD:P(A;;GW;;;BU)(A;OICI;FA;;;USER)",
            False,
            "DACL not private or malformed",
        ),
        (
            "O:USERD:P(A;CIIO;GW;;;BU)(A;OICI;FA;;;USER)",
            False,
            "DACL not private or malformed",
        ),
        (
            "O:USERD:P(X;;GR;;;BU)(A;OICI;FA;;;USER)",
            False,
            "DACL not private or malformed",
        ),
        ("", False, "receipt unavailable"),
    ],
)
def test_persistent_root_acl_rejects_nonprivate_canonical_forms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sddl: str,
    expected: bool,
    failure: str | None,
) -> None:
    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: sddl)

    assert private._persistent_root_acl_is_present(tmp_path, "USER") is expected
    assert private._persistent_root_acl_failure(tmp_path, "USER") == failure


def test_aliased_current_user_root_uses_strict_private_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sddl = "O:LAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;USER)"
    semantic_calls: list[dict[str, object]] = []

    def semantic(_path: Path, **kwargs: object) -> bool:
        semantic_calls.append(kwargs)
        return True

    monkeypatch.setattr(private, "read_windows_sddl", lambda _path: sddl)
    monkeypatch.setattr(
        private,
        "windows_sddl_owner_matches_sid",
        lambda value, sid, **_kwargs: value == sddl and sid == "USER",
    )
    monkeypatch.setattr(private, "windows_directory_prevents_untrusted_writes", semantic)

    assert private._persistent_root_acl_failure(tmp_path, "USER") is None
    assert len(semantic_calls) == 1
    assert semantic_calls[0]["final_parent"] is True
    assert "prospective_child" not in semantic_calls[0]
    assert semantic_calls[0]["private_access"] is True


def test_owner_private_root_requires_windows_location_and_unrestricted_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "private"
    parent = _guard(tmp_path)
    with pytest.raises(WindowsACLSafetyError, match="parent identity"):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=False,
        )

    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: None)
    with pytest.raises(WindowsTokenProbeError, match="owner identity"):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )

    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_token_is_restricted", lambda **_kwargs: True)
    with pytest.raises(RestrictedWindowsTokenError, match="restricted process token"):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )


@pytest.mark.parametrize("failure", ["stale", "relationship"])
def test_owner_private_root_requires_an_exact_live_parent_guard(
    tmp_path: Path,
    failure: str,
) -> None:
    target = tmp_path / "private"
    parent = _guard(tmp_path, current=failure != "stale")
    if failure == "relationship":
        target = tmp_path.parent / "private"

    with pytest.raises(WindowsACLSafetyError, match="parent identity"):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )


@pytest.mark.parametrize("created", [True, None])
def test_owner_private_root_creates_or_reuses_only_an_exact_sealed_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    created: bool | None,
) -> None:
    target = tmp_path / "private"
    target.mkdir()
    parent = _guard(tmp_path)
    guard = _guard(target)
    descriptors: list[str] = []
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_token_is_restricted", lambda **_kwargs: False)
    monkeypatch.setattr(
        private,
        "_create_windows_directory_with_sddl",
        lambda _path, sddl: descriptors.append(sddl) or created,
    )
    monkeypatch.setattr(
        private,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: guard,
    )
    monkeypatch.setattr(private, "_persistent_root_acl_failure", lambda *_a, **_k: None)
    monkeypatch.setattr(private, "current_process_can_mutate_path", lambda *_a, **_k: True)

    assert (
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )
        is guard
    )
    assert descriptors == ["O:USERD:P(D;;SD;;;AU)(A;OICI;FA;;;USER)"]
    assert not guard.closed


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        ("reparse", "root handle unavailable"),
        ("permissive", "durable ACL receipt mismatch"),
        ("unusable", "current token cannot use protected root"),
        ("changed", "root identity changed before verification"),
    ],
)
def test_owner_private_root_rejects_unsafe_collisions_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
    reason: str,
) -> None:
    target = tmp_path / "private"
    target.mkdir()
    parent = _guard(tmp_path)
    guard = None if failure == "reparse" else _guard(target, current=failure != "changed")
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_token_is_restricted", lambda **_kwargs: False)
    monkeypatch.setattr(private, "_create_windows_directory_with_sddl", lambda *_args: None)
    monkeypatch.setattr(
        private,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: guard,
    )
    monkeypatch.setattr(
        private,
        "_persistent_root_acl_failure",
        lambda *_args, **_kwargs: "unsafe test ACL" if failure == "permissive" else None,
    )
    monkeypatch.setattr(
        private,
        "current_process_can_mutate_path",
        lambda *_args, **_kwargs: failure != "unusable",
    )
    security: list[tuple[Path, str]] = []
    removed: list[Path] = []
    monkeypatch.setattr(
        private,
        "_set_windows_file_security",
        lambda path, sddl: security.append((path, sddl)) or True,
    )
    monkeypatch.setattr(private.os, "rmdir", removed.append)

    with pytest.raises(WindowsACLSafetyError, match=reason):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )

    assert target.is_dir()
    assert security == []
    assert removed == []
    if guard is not None:
        assert guard.closed


@pytest.mark.parametrize(
    ("parent_states", "root_states", "remaining_root_states", "reason"),
    [
        (
            [True, False],
            [True],
            [True],
            "parent identity changed before verification",
        ),
        (
            [True, True],
            [True, False],
            [],
            "root identity changed after verification",
        ),
        (
            [True, True, False],
            [True, True],
            [],
            "parent identity changed after verification",
        ),
    ],
)
def test_owner_private_root_reports_identity_drift_stage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parent_states: list[bool],
    root_states: list[bool],
    remaining_root_states: list[bool],
    reason: str,
) -> None:
    class SequencedGuard:
        def __init__(self, path: Path, states: list[bool]) -> None:
            self.path = path
            self.states = states
            self.closed = False

        def is_current(self) -> bool:
            return self.states.pop(0)

        def close(self) -> None:
            self.closed = True

    target = tmp_path / "private"
    target.mkdir()
    parent = SequencedGuard(tmp_path, parent_states)
    root = SequencedGuard(target, root_states)
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_token_is_restricted", lambda **_kwargs: False)
    monkeypatch.setattr(private, "_create_windows_directory_with_sddl", lambda *_args: None)
    monkeypatch.setattr(private, "open_windows_directory_guard", lambda *_args, **_kwargs: root)
    monkeypatch.setattr(private, "_persistent_root_acl_failure", lambda *_args: None)
    monkeypatch.setattr(private, "current_process_can_mutate_path", lambda *_args, **_kwargs: True)

    with pytest.raises(WindowsACLSafetyError, match=reason):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )
    assert root.closed
    assert not parent_states
    assert root_states == remaining_root_states


@pytest.mark.parametrize("exact_acl", [False, True])
def test_owner_private_root_never_mutates_a_failed_fresh_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exact_acl: bool,
) -> None:
    target = tmp_path / "private"
    target.mkdir()
    parent = _guard(tmp_path)
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_token_is_restricted", lambda **_kwargs: False)
    monkeypatch.setattr(private, "_create_windows_directory_with_sddl", lambda *_args: True)
    monkeypatch.setattr(
        private,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        private,
        "_persistent_root_acl_failure",
        lambda *_args, **_kwargs: None if exact_acl else "unsafe test ACL",
    )
    security: list[tuple[Path, str]] = []
    removed: list[Path] = []
    monkeypatch.setattr(
        private,
        "_set_windows_file_security",
        lambda path, sddl: security.append((path, sddl)) or True,
    )
    monkeypatch.setattr(private.os, "rmdir", removed.append)

    with pytest.raises(WindowsACLSafetyError, match="identity verification"):
        private.create_or_validate_windows_owner_private_directory(
            target,
            parent_guard=parent,
            is_windows=True,
        )

    assert security == []
    assert removed == []


@pytest.mark.parametrize("failure", ["platform", "parent", "relationship"])
def test_create_private_directory_requires_exact_live_parent(
    tmp_path: Path,
    failure: str,
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    guard = _guard(parent, current=failure != "parent")
    child = (parent if failure != "relationship" else tmp_path) / "child"

    with pytest.raises(WindowsACLSafetyError, match="parent identity"):
        private.create_windows_logon_private_directory(
            child,
            parent_guard=guard,
            is_windows=failure != "platform",
        )


@pytest.mark.parametrize(("user", "logon"), [(None, "LOGON"), ("USER", None)])
def test_create_private_directory_requires_both_token_identities(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    user: str | None,
    logon: str | None,
) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: user)
    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: logon)
    with pytest.raises(WindowsTokenProbeError, match="logon identity"):
        private.create_windows_logon_private_directory(
            parent / "child", parent_guard=_guard(parent), is_windows=True
        )


def _patch_private_creation(
    monkeypatch: pytest.MonkeyPatch,
    *,
    parent: private.WindowsDirectoryGuard,
    child_guard: private.WindowsDirectoryGuard | None,
    created: bool | None = True,
    acl: bool = True,
) -> list[tuple[Path, str]]:
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: "LOGON")
    monkeypatch.setattr(private, "_create_windows_directory_with_sddl", lambda *_args: created)
    monkeypatch.setattr(
        private, "open_windows_directory_guard", lambda *_args, **_kwargs: child_guard
    )
    monkeypatch.setattr(private, "_logon_private_acl_is_present", lambda *_args, **_kwargs: acl)
    security: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        private,
        "_set_windows_file_security",
        lambda path, sddl: security.append((path, sddl)) or True,
    )
    return security


def test_create_private_directory_collision_and_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent_path = tmp_path / "parent"
    child_path = parent_path / "child"
    parent_path.mkdir()
    child_path.mkdir()
    parent = _guard(parent_path)
    child = _guard(child_path)

    _patch_private_creation(monkeypatch, parent=parent, child_guard=child, created=None)
    assert (
        private.create_windows_logon_private_directory(
            child_path, parent_guard=parent, is_windows=True
        )
        is None
    )

    _patch_private_creation(monkeypatch, parent=parent, child_guard=child)
    assert (
        private.create_windows_logon_private_directory(
            child_path, parent_guard=parent, is_windows=True
        )
        is child
    )


@pytest.mark.parametrize("failure", ["missing-guard", "parent-changed", "child-changed", "acl"])
def test_create_private_directory_verification_failure_cleans_only_exact_acl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
) -> None:
    parent_path = tmp_path / "parent"
    child_path = parent_path / "child"
    parent_path.mkdir()
    child_path.mkdir()
    closed: list[int] = []
    if failure == "parent-changed":
        parent_metadata = os.lstat(parent_path)
        parent_inode = int(parent_metadata.st_ino)
        identities = iter([parent_inode, parent_inode + 1])
        parent = private.WindowsDirectoryGuard(
            parent_path,
            int(parent_metadata.st_dev),
            parent_inode,
            40,
            lambda _handle: next(identities),
            lambda _handle: None,
        )
    else:
        parent = _guard(parent_path)
    child = (
        None
        if failure == "missing-guard"
        else _guard(
            child_path,
            current=failure != "child-changed",
            closer=closed.append,
        )
    )
    security = _patch_private_creation(
        monkeypatch,
        parent=parent,
        child_guard=child,
        acl=failure != "acl",
    )
    removed: list[Path] = []
    monkeypatch.setattr(private.os, "rmdir", removed.append)

    with pytest.raises(WindowsACLSafetyError, match="identity verification"):
        private.create_windows_logon_private_directory(
            child_path, parent_guard=parent, is_windows=True
        )

    assert bool(closed) is (child is not None)
    assert bool(security) is (failure != "acl")
    assert bool(removed) is (failure != "acl")


def test_create_private_directory_suppresses_cleanup_remove_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parent_path = tmp_path / "parent"
    child_path = parent_path / "child"
    parent_path.mkdir()
    child_path.mkdir()
    parent = _guard(parent_path)
    _patch_private_creation(monkeypatch, parent=parent, child_guard=None, acl=True)
    monkeypatch.setattr(
        private.os,
        "rmdir",
        lambda _path: (_ for _ in ()).throw(OSError("busy")),
    )
    with pytest.raises(WindowsACLSafetyError):
        private.create_windows_logon_private_directory(
            child_path, parent_guard=parent, is_windows=True
        )


def test_cleanup_requires_current_guard_token_acl_and_security_update(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    current = _guard(path)
    stale = _guard(path, current=False)
    assert not private.prepare_windows_logon_private_directory_cleanup(stale)

    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: None)
    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: "LOGON")
    assert not private.prepare_windows_logon_private_directory_cleanup(current)

    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: None)
    assert not private.prepare_windows_logon_private_directory_cleanup(current)

    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: "LOGON")
    monkeypatch.setattr(private, "_logon_private_acl_is_present", lambda *_args, **_kwargs: False)
    assert not private.prepare_windows_logon_private_directory_cleanup(current)

    monkeypatch.setattr(private, "_logon_private_acl_is_present", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(private, "_set_windows_file_security", lambda *_args: False)
    assert not private.prepare_windows_logon_private_directory_cleanup(current)


@pytest.mark.parametrize(
    ("current_after", "acl_after", "expected"),
    [(False, True, False), (True, False, False), (True, True, True)],
)
def test_cleanup_revalidates_identity_and_replacement_acl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    current_after: bool,
    acl_after: bool,
    expected: bool,
) -> None:
    path = tmp_path / "private"
    path.mkdir()
    metadata = os.lstat(path)
    checks = iter([True, current_after])
    guard = private.WindowsDirectoryGuard(
        path,
        int(metadata.st_dev),
        int(metadata.st_ino),
        41,
        lambda _handle: int(metadata.st_ino) if next(checks) else int(metadata.st_ino) + 1,
        lambda _handle: None,
    )
    monkeypatch.setattr(private, "current_process_user_sid", lambda **_kwargs: "USER")
    monkeypatch.setattr(private, "current_process_logon_sid", lambda **_kwargs: "LOGON")
    acl_checks = iter([True, acl_after])
    monkeypatch.setattr(
        private,
        "_logon_private_acl_is_present",
        lambda *_args, **_kwargs: next(acl_checks),
    )
    monkeypatch.setattr(private, "_set_windows_file_security", lambda *_args: True)

    assert private.prepare_windows_logon_private_directory_cleanup(guard) is expected
