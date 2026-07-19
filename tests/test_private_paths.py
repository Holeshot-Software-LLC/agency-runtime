"""Private runtime path allocation and identity-safe cleanup regressions."""

from __future__ import annotations

import os
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


@pytest.mark.parametrize("value", ("", ".", "..", "bad/name", "bad name", "x" * 81))
def test_private_path_components_are_strict(value: str) -> None:
    with pytest.raises(ValueError, match="one safe filesystem component"):
        private_paths._validate_component(value, label="component")


def test_allocate_validate_and_remove_private_directory(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    (identity.path / "result.txt").write_text("done", encoding="utf-8")

    assert validate_private_directory(identity.path) == identity.path

    remove_private_directory(identity)

    assert not identity.path.exists()
    remove_private_directory(identity)


def test_remove_refuses_a_replaced_directory(tmp_path: Path) -> None:
    root = ensure_private_directory(tmp_path / "root")
    identity = allocate_private_directory(root, prefix="worker")
    os.rmdir(identity.path)
    os.mkdir(identity.path, 0o700)

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

    def replace_then_rename(source: Path, destination: Path) -> None:
        os.rmdir(source)
        os.mkdir(source, 0o700)
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
    path.mkdir()
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
