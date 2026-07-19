"""Private runtime path allocation and identity-safe cleanup regressions."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from agency_runtime.core import private_paths
from agency_runtime.core.private_paths import (
    PrivateDirectoryCleanupError,
    PrivateDirectoryIdentity,
    allocate_private_directory,
    ensure_private_directory,
    private_temporary_directory,
    remove_private_directory,
    validate_private_directory,
)
from tests.runtime_support import ensure_private_test_directory


@pytest.mark.parametrize("value", ("", ".", "..", "bad/name", "bad name", "x" * 81))
def test_private_path_components_are_strict(value: str) -> None:
    with pytest.raises(ValueError, match="one safe filesystem component"):
        private_paths._validate_component(value, label="component")


def _windows_guard(
    path: Path,
    *,
    closed: list[int] | None = None,
) -> private_paths.WindowsDirectoryGuard:
    metadata = os.lstat(path)
    inode = int(metadata.st_ino)
    return private_paths.WindowsDirectoryGuard(
        path,
        int(metadata.st_dev),
        inode,
        73,
        lambda _handle: inode,
        (closed.append if closed is not None else lambda _handle: None),
    )


def test_bootstrap_private_directory_registers_a_guarded_windows_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    created: list[Path] = []
    parent_closed: list[int] = []
    parent_guard = _windows_guard(tmp_path, closed=parent_closed)

    def create(
        candidate: Path,
        **_kwargs: object,
    ) -> private_paths.WindowsDirectoryGuard:
        candidate.mkdir()
        created.append(candidate)
        return _windows_guard(candidate)

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        create,
    )
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: parent_guard,
    )
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: True)

    result = private_paths.bootstrap_private_directory(target)
    identity = private_paths._HOST_AUTHORITIES[result]
    try:
        assert result == target.resolve()
        assert created == [target.resolve()]
        assert parent_closed == [73]
        assert identity.path == result
        assert identity.guard is not None and identity.parent_guard is None
    finally:
        private_paths._discard_host_authority(identity)
        assert identity.guard is not None
        identity.guard.close()


@pytest.mark.parametrize("unsafe_parent", ["missing", "symlink"])
def test_bootstrap_private_directory_rejects_unsafe_windows_ancestor_chains(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unsafe_parent: str,
) -> None:
    parent = tmp_path / "parent"
    if unsafe_parent == "symlink":
        real = tmp_path / "real"
        real.mkdir()
        try:
            parent.symlink_to(real, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"directory symlinks are unavailable: {exc}")
    target = parent / "ci-root"
    native_calls: list[Path] = []
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        lambda path, **_kwargs: native_calls.append(path),
    )

    with pytest.raises(PermissionError, match="parent"):
        private_paths.bootstrap_private_directory(target)

    assert native_calls == []


def test_bootstrap_private_directory_does_not_bypass_non_windows_refusal(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    refusal = PermissionError("untrusted profile")
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", False)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(refusal),
    )

    with pytest.raises(PermissionError, match="untrusted profile") as caught:
        private_paths.bootstrap_private_directory(tmp_path / "ci-root")

    assert caught.value is refusal


@pytest.mark.parametrize("parent_guard_available", [False, True])
def test_bootstrap_private_directory_requires_trusted_and_pinned_windows_ancestors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parent_guard_available: bool,
) -> None:
    target = tmp_path / "ci-root"
    native_calls: list[Path] = []
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(
        private_paths,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: parent_guard_available,
    )
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        lambda path, **_kwargs: native_calls.append(path),
    )

    expected = "parent changed" if parent_guard_available else "parent is not trusted"
    with pytest.raises(PermissionError, match=expected):
        private_paths.bootstrap_private_directory(target)

    assert native_calls == []


def test_bootstrap_private_directory_rejects_an_untrusted_replaceable_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    trust_checks: list[Path] = []
    native_calls: list[Path] = []

    def trust(path: Path, **_kwargs: object) -> bool:
        trust_checks.append(path)
        return path == target.parent.parent

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", trust)
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        lambda path, **_kwargs: native_calls.append(path),
    )

    with pytest.raises(PermissionError, match="parent is not trusted"):
        private_paths.bootstrap_private_directory(target)

    assert trust_checks == [target.parent.resolve()]
    assert native_calls == []


@pytest.mark.parametrize("failure_stage", ["before-create", "after-create"])
def test_bootstrap_private_directory_rechecks_parent_trust_while_pinned(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure_stage: str,
) -> None:
    target = tmp_path / "ci-root"
    parent_closed: list[int] = []
    child_closed: list[int] = []
    parent_guard = _windows_guard(tmp_path, closed=parent_closed)
    trust_results = iter([True, False] if failure_stage == "before-create" else [True, True, False])
    native_calls: list[Path] = []

    def create(candidate: Path, **_kwargs: object) -> private_paths.WindowsDirectoryGuard:
        native_calls.append(candidate)
        candidate.mkdir()
        return _windows_guard(candidate, closed=child_closed)

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(
        private_paths,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: next(trust_results),
    )
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: parent_guard,
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        create,
    )

    with pytest.raises(PermissionError, match="parent changed"):
        private_paths.bootstrap_private_directory(target)

    expected_calls = [] if failure_stage == "before-create" else [target.resolve()]
    assert native_calls == expected_calls
    assert parent_closed == [73]
    assert child_closed == ([] if failure_stage == "before-create" else [73])
    assert target.resolve() not in private_paths._HOST_AUTHORITIES


def test_bootstrap_private_directory_closes_a_changed_windows_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    target.mkdir()
    closed: list[int] = []
    guard = _windows_guard(target, closed=closed)
    parent_guard = _windows_guard(tmp_path)
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        lambda *_args, **_kwargs: guard,
    )
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: parent_guard,
    )
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: False)

    with pytest.raises(PermissionError, match="protected Windows root changed"):
        private_paths.bootstrap_private_directory(target)

    assert closed == [73]
    assert target.resolve() not in private_paths._HOST_AUTHORITIES


def test_bootstrap_authority_reuses_a_live_concurrent_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    target.mkdir()
    original_guard = _windows_guard(target)
    duplicate_closed: list[int] = []
    duplicate_guard = _windows_guard(target, closed=duplicate_closed)
    original = PrivateDirectoryIdentity(
        target,
        original_guard.device,
        original_guard.inode,
        guard=original_guard,
    )
    duplicate = PrivateDirectoryIdentity(
        target,
        duplicate_guard.device,
        duplicate_guard.inode,
        guard=duplicate_guard,
    )
    private_paths._HOST_AUTHORITIES[target.resolve()] = original
    monkeypatch.setattr(private_paths, "_identity_is_current", lambda _identity: True)
    try:
        assert private_paths._install_windows_bootstrap_authority(duplicate) is original
        assert duplicate_closed == [73]
        assert private_paths._HOST_AUTHORITIES[target.resolve()] is original
    finally:
        private_paths._HOST_AUTHORITIES.pop(target.resolve(), None)
        original_guard.close()


def test_bootstrap_authority_requires_an_incoming_guard(tmp_path: Path) -> None:
    target = tmp_path / "ci-root"
    target.mkdir()
    metadata = os.lstat(target)
    identity = PrivateDirectoryIdentity(
        target,
        int(metadata.st_dev),
        int(metadata.st_ino),
    )

    with pytest.raises(PermissionError, match="guard is unavailable"):
        private_paths._install_windows_bootstrap_authority(identity)

    assert target.resolve() not in private_paths._HOST_AUTHORITIES


def test_bootstrap_authority_replaces_and_closes_a_stale_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    target.mkdir()
    stale_guard_closed: list[int] = []
    stale_parent_closed: list[int] = []
    replacement_guard = _windows_guard(target)
    stale = PrivateDirectoryIdentity(
        target,
        replacement_guard.device,
        replacement_guard.inode,
        guard=_windows_guard(target, closed=stale_guard_closed),
        parent_guard=_windows_guard(tmp_path, closed=stale_parent_closed),
    )
    replacement = PrivateDirectoryIdentity(
        target,
        replacement_guard.device,
        replacement_guard.inode,
        guard=replacement_guard,
    )
    private_paths._HOST_AUTHORITIES[target.resolve()] = stale
    monkeypatch.setattr(
        private_paths,
        "_identity_is_current",
        lambda identity: identity is not stale,
    )
    try:
        assert private_paths._install_windows_bootstrap_authority(replacement) is replacement
        assert stale_guard_closed == [73]
        assert stale_parent_closed == [73]
        assert private_paths._HOST_AUTHORITIES[target.resolve()] is replacement
    finally:
        private_paths._discard_host_authority(replacement)
        replacement_guard.close()


def test_bootstrap_private_directory_discards_post_install_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "ci-root"
    parent_closed: list[int] = []
    root_closed: list[int] = []
    parent_guard = _windows_guard(tmp_path, closed=parent_closed)

    def create(candidate: Path, **_kwargs: object) -> private_paths.WindowsDirectoryGuard:
        candidate.mkdir()
        return _windows_guard(candidate, closed=root_closed)

    identity_checks = iter([True, False])
    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        private_paths,
        "ensure_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("untrusted profile")),
    )
    monkeypatch.setattr(private_paths, "storage_parent_is_trusted", lambda *_a, **_k: True)
    monkeypatch.setattr(
        private_paths,
        "open_windows_directory_guard",
        lambda *_args, **_kwargs: parent_guard,
    )
    monkeypatch.setattr(
        private_paths,
        "create_or_validate_windows_owner_private_directory",
        create,
    )
    monkeypatch.setattr(
        private_paths,
        "_identity_is_current",
        lambda _identity: next(identity_checks),
    )

    with pytest.raises(PermissionError, match="protected Windows root changed"):
        private_paths.bootstrap_private_directory(target)

    assert parent_closed == [73]
    assert root_closed == [73]
    assert target.resolve() not in private_paths._HOST_AUTHORITIES


def test_allocate_validate_and_remove_private_directory(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    (identity.path / "result.txt").write_text("done", encoding="utf-8")

    assert validate_private_directory(identity.path) == identity.path

    remove_private_directory(identity)

    assert not identity.path.exists()
    remove_private_directory(identity)


@pytest.mark.skipif(os.name == "nt", reason="POSIX umask semantics")
def test_test_fixture_parent_creation_is_private_under_permissive_umask(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fixture-root"
    target = root / "nested" / "leaf"
    previous = os.umask(0)
    try:
        ensure_private_test_directory(target, parents=True)
    finally:
        os.umask(previous)

    for directory in (root, root / "nested", target):
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700


def test_remove_refuses_a_replaced_directory(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    replacement = tmp_path / "replacement"
    os.mkdir(replacement, 0o700)
    os.rmdir(identity.path)
    os.rename(replacement, identity.path)

    with pytest.raises(PermissionError, match="replaced"):
        remove_private_directory(identity)

    assert identity.path.is_dir()


def test_remove_revalidates_after_quarantine_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    original_rename = private_paths.os.rename
    replacement = ensure_private_test_directory(tmp_path / "replacement")
    tampered = False

    def replace_then_rename(source: Path, destination: Path) -> None:
        nonlocal tampered
        if tampered:
            original_rename(source, destination)
            return
        tampered = True
        os.rmdir(source)
        original_rename(replacement, source)
        original_rename(source, destination)

    monkeypatch.setattr(private_paths.os, "rename", replace_then_rename)

    with pytest.raises(PermissionError, match="replaced"):
        remove_private_directory(identity)

    assert identity.path.is_dir()


def test_remove_restores_original_receipt_after_rmtree_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    (identity.path / "sensitive.txt").write_text("state", encoding="utf-8")
    original_rmtree = private_paths.shutil.rmtree
    failures = 0

    def fail_once(path: Path, **kwargs: object) -> None:
        nonlocal failures
        failures += 1
        if failures == 1:
            raise OSError("injected cleanup failure")
        original_rmtree(path, **kwargs)

    monkeypatch.setattr(private_paths.shutil, "rmtree", fail_once)

    with pytest.raises(OSError, match="injected cleanup failure"):
        remove_private_directory(identity)

    assert identity.path.is_dir()
    assert (identity.path / "sensitive.txt").read_text(encoding="utf-8") == "state"
    remove_private_directory(identity)
    assert not identity.path.exists()


def test_private_temporary_directory_cleans_after_body_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ensure_private_directory(tmp_path / "ephemeral")
    monkeypatch.setattr(private_paths, "private_runtime_directory", lambda _category: root)
    observed: Path | None = None
    with (
        pytest.raises(RuntimeError, match="body failed"),
        private_temporary_directory(prefix="worker") as path,
    ):
        observed = path
        raise RuntimeError("body failed")

    assert observed is not None and not observed.exists()


def test_cleanup_failure_preserves_body_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ensure_private_directory(tmp_path / "ephemeral")
    monkeypatch.setattr(private_paths, "private_runtime_directory", lambda _category: root)
    monkeypatch.setattr(
        private_paths,
        "remove_private_directory",
        lambda _identity: (_ for _ in ()).throw(PermissionError("cleanup refused")),
    )

    with (
        pytest.raises(RuntimeError, match="body failed") as caught,
        private_temporary_directory(prefix="worker"),
    ):
        raise RuntimeError("body failed")

    assert any("cleanup failed" in note for note in caught.value.__notes__)


def test_cleanup_failure_after_success_is_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ensure_private_directory(tmp_path / "ephemeral")
    monkeypatch.setattr(private_paths, "private_runtime_directory", lambda _category: root)
    monkeypatch.setattr(
        private_paths,
        "remove_private_directory",
        lambda _identity: (_ for _ in ()).throw(PermissionError("cleanup refused")),
    )

    with (
        pytest.raises(PrivateDirectoryCleanupError, match="cleanup failed"),
        private_temporary_directory(prefix="worker"),
    ):
        pass


def test_remove_rejects_an_untrusted_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "worker"
    ensure_private_test_directory(path)
    metadata = os.lstat(path)
    identity = PrivateDirectoryIdentity(path, int(metadata.st_dev), int(metadata.st_ino))
    monkeypatch.setattr(
        private_paths,
        "validate_private_directory",
        lambda _path: (_ for _ in ()).throw(PermissionError("unsafe parent")),
    )

    with pytest.raises(PermissionError, match="unsafe parent"):
        remove_private_directory(identity)

    assert path.exists()


def test_remove_private_tree_retries_one_windows_readonly_descendant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "cleanup"
    root.mkdir()
    child = root / "readonly.txt"
    child.write_text("state", encoding="utf-8")
    chmod_calls: list[tuple[Path, int]] = []
    removal_calls: list[Path] = []

    def exercise_callback(path: Path, *, onerror: object) -> None:
        assert path == root
        callback = onerror
        assert callable(callback)
        callback(
            lambda candidate: removal_calls.append(Path(candidate)),
            str(child),
            (None, PermissionError("readonly"), None),
        )

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", True)
    monkeypatch.setattr(private_paths.shutil, "rmtree", exercise_callback)
    monkeypatch.setattr(
        private_paths.os,
        "chmod",
        lambda path, mode: chmod_calls.append((Path(path), mode)),
    )

    private_paths._remove_private_tree(root)

    assert chmod_calls == [(child, private_paths.stat.S_IWRITE)]
    assert removal_calls == [child]


@pytest.mark.parametrize(
    ("windows", "outside", "reparse", "error"),
    (
        (False, False, False, PermissionError("not windows")),
        (True, True, False, PermissionError("outside")),
        (True, False, True, PermissionError("reparse")),
        (True, False, False, OSError("not permission")),
    ),
)
def test_remove_private_tree_refuses_unsafe_readonly_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    windows: bool,
    outside: bool,
    reparse: bool,
    error: OSError,
) -> None:
    root = tmp_path / "cleanup"
    root.mkdir()
    child = (tmp_path / "outside.txt") if outside else (root / "child.txt")
    child.write_text("state", encoding="utf-8")

    def exercise_callback(_path: Path, *, onerror: object) -> None:
        callback = onerror
        assert callable(callback)
        callback(lambda _candidate: None, str(child), (None, error, None))

    monkeypatch.setattr(private_paths, "_IS_WINDOWS", windows)
    monkeypatch.setattr(private_paths.shutil, "rmtree", exercise_callback)
    monkeypatch.setattr(
        private_paths,
        "metadata_is_link_or_reparse_point",
        lambda _metadata: reparse,
    )

    with pytest.raises(type(error), match=str(error)) as caught:
        private_paths._remove_private_tree(root)

    assert caught.value is error
