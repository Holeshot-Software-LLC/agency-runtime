"""Repository-scoped delegation worktree portability and identity tests."""

from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from agency_runtime.core.delegation import lifecycle_git
from agency_runtime.core.delegation.lifecycle_types import WorktreeInfo, WorkUnit
from agency_runtime.core.private_paths import (
    allocate_private_directory,
    ensure_private_directory,
)


def _git(repo: Path, args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return lifecycle_git.run_git(repo, args, timeout=timeout)


def _initialize_repository(repo: Path) -> None:
    repo.mkdir()
    initialized = _git(repo, ["init", "--shared=all", "--initial-branch=main"])
    assert initialized.returncode == 0, initialized.stderr
    committed = _git(
        repo,
        [
            "-c",
            "user.name=Agency Runtime",
            "-c",
            "user.email=agency-runtime@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--allow-empty",
            "-m",
            "initial",
        ],
    )
    assert committed.returncode == 0, committed.stderr


def _provision_default(units: list[WorkUnit]) -> dict[str, WorktreeInfo]:
    return lifecycle_git.provision_worktrees(
        units,
        base_branch=None,
        worktree_root=Path.home() / ".agency-runtime" / "worktrees",
        run_git_func=_git,
        git_root_func=lifecycle_git.git_root,
        current_branch_func=lambda repo: lifecycle_git.current_branch(
            repo,
            run_git_func=_git,
        ),
        head_sha_func=lambda repo, ref: lifecycle_git.head_sha(
            repo,
            ref,
            run_git_func=_git,
        ),
    )


def _cleanup(worktrees: dict[str, WorktreeInfo]) -> dict[str, lifecycle_git.CleanupRecord]:
    return lifecycle_git.cleanup_worktrees(
        worktrees,
        merge_back=True,
        create_pr_on_conflict=False,
        merge_unit_ids=set(worktrees),
        run_git_func=_git,
        current_branch_func=lambda repo: lifecycle_git.current_branch(
            repo,
            run_git_func=_git,
        ),
        head_sha_func=lambda repo, ref: lifecycle_git.head_sha(
            repo,
            ref,
            run_git_func=_git,
        ),
    )


@pytest.fixture
def trusted_repository_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the POSIX repository fallback below a simulated trusted parent."""

    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", False)
    monkeypatch.setattr(lifecycle_git, "_MAX_WINDOWS_WORKTREE_PATH_CHARS", 1000)
    monkeypatch.setattr(
        lifecycle_git,
        "config_namespace_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "restrict_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    original_mkdir = lifecycle_git.os.mkdir
    monkeypatch.setattr(
        lifecycle_git.os,
        "mkdir",
        lambda path, _mode=0o777: original_mkdir(path, 0o777),
    )


def test_default_root_falls_back_to_one_host_attested_root_without_gitignore_changes(
    git_integration_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path = git_integration_root
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", True)
    monkeypatch.setattr(lifecycle_git, "_MAX_WINDOWS_WORKTREE_PATH_CHARS", 1000)
    repositories = [tmp_path / "first", tmp_path / "second"]
    for repo in repositories:
        _initialize_repository(repo)
    host_root = ensure_private_directory(tmp_path / "host-attested")
    monkeypatch.setattr(
        lifecycle_git,
        "private_runtime_directory",
        lambda _name: (_ for _ in ()).throw(PermissionError("restricted token")),
    )

    def allocate_host_run_root(
        *,
        fallback_error: BaseException,
    ) -> lifecycle_git._AllocatedRunRoot:
        # Keep the mocked host allocation below Git's PATH_MAX - 40 GIT_DIR
        # guard while preserving the opaque host-style ``.a-`` namespace.
        identity = allocate_private_directory(host_root, prefix=".a")
        return lifecycle_git._AllocatedRunRoot(
            path=identity.path,
            token="f" * 32,
            root_identity=lifecycle_git._identity_from_private(identity),
            parent_identity=lifecycle_git._capture_directory_identity(host_root),
            private_identity=identity,
            warning=(
                "private runtime worktree storage was unavailable; using the exact "
                "host-attested Codex task root for this run "
                f"({type(fallback_error).__name__})"
            ),
        )

    monkeypatch.setattr(lifecycle_git, "_allocate_host_run_root", allocate_host_run_root)

    worktrees = _provision_default(
        [
            WorkUnit("one", "first task", repo_path=repositories[0]),
            WorkUnit("two", "second task", repo_path=repositories[1]),
        ]
    )

    assert all(info.created for info in worktrees.values()), {
        unit_id: info.errors for unit_id, info in worktrees.items()
    }
    assert all(not info.repo_scoped_root for info in worktrees.values())
    assert all(info.dirty_repo is False for info in worktrees.values())
    assert all("host-attested Codex" in info.warnings[0] for info in worktrees.values())
    roots = {info.run_root_identity.path for info in worktrees.values() if info.run_root_identity}
    assert len(roots) == 1
    assert all(root.parent not in repositories for root in roots)
    assert all(root.name.startswith(".a-") for root in roots)
    assert all(not (repo / ".gitignore").exists() for repo in repositories)

    cleanup = _cleanup(worktrees)

    assert all(record["merged"] and record["removed"] for record in cleanup.values()), cleanup
    assert all(not root.exists() for root in roots)
    assert all(_git(repo, ["status", "--porcelain"]).stdout == "" for repo in repositories)
    assert all(not (repo / ".gitignore").exists() for repo in repositories)


def test_repository_root_allocation_retries_an_exact_random_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    first_token = "a" * 32
    second_token = "b" * 32
    collision = tmp_path / f".agency-worktrees-{first_token}"
    collision.mkdir()
    tokens = iter([first_token, second_token])
    real_token_hex = lifecycle_git.secrets.token_hex
    monkeypatch.setattr(lifecycle_git.secrets, "token_hex", lambda _size: next(tokens))

    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )

    assert allocation.path.name == f".agency-worktrees-{second_token}"
    assert collision.exists()
    monkeypatch.setattr(lifecycle_git.secrets, "token_hex", real_token_hex)
    assert lifecycle_git._remove_empty_run_root(
        allocation.root_identity,
        allocation.parent_identity,
    )


def test_repository_fallback_rejects_untrusted_namespace_before_mkdir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lifecycle_git,
        "config_namespace_is_trusted",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        lifecycle_git.os,
        "mkdir",
        lambda *_args, **_kwargs: pytest.fail("untrusted namespace was mutated"),
    )

    with pytest.raises(PermissionError, match="cross-account worktree substitution"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("restricted token"),
        )


def test_repository_fallback_rolls_back_failed_privacy_verification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    monkeypatch.setattr(
        lifecycle_git,
        "config_namespace_is_trusted",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "restrict_path_permissions",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        lifecycle_git,
        "storage_parent_is_trusted",
        lambda *_args, **_kwargs: False,
    )

    with pytest.raises(PermissionError, match="worktree root is not private"):
        lifecycle_git._allocate_repository_run_root(
            tmp_path,
            fallback_error=PermissionError("restricted token"),
        )

    assert list(tmp_path.glob(".agency-worktrees-*")) == []


def test_replaced_run_root_is_preserved_and_cleanup_fails_closed(
    tmp_path: Path,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )
    original = tmp_path / "original-owned-root"
    os.rename(allocation.path, original)
    allocation.path.mkdir()

    with pytest.raises(PermissionError, match="was replaced"):
        lifecycle_git._remove_empty_run_root(
            allocation.root_identity,
            allocation.parent_identity,
        )

    assert original.exists()
    assert allocation.path.exists()


def test_replaced_worktree_identity_stops_commit_before_git(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    worktree = run_root / "worktree"
    worktree.mkdir(parents=True)
    run_identity = lifecycle_git._capture_directory_identity(run_root)
    parent_identity = lifecycle_git._capture_directory_identity(tmp_path)
    worktree_identity = lifecycle_git._capture_directory_identity(worktree)
    moved = run_root / "original-worktree"
    os.rename(worktree, moved)
    worktree.mkdir()
    info = WorktreeInfo(
        "unit",
        tmp_path,
        worktree,
        "delegation/unit",
        "main",
        "a" * 40,
        created=True,
        worktree_identity=worktree_identity,
        run_root_identity=run_identity,
        run_parent_identity=parent_identity,
        repo_scoped_root=True,
    )
    calls: list[list[str]] = []

    error = lifecycle_git.commit_successful_worktree(
        info,
        "unit",
        run_git_func=lambda _repo, args, **_kwargs: (
            calls.append(list(args)) or subprocess.CompletedProcess(["git"], 0, "", "")
        ),
    )

    assert error == "delegation worktree was replaced during delegation"
    assert calls == []


def test_windows_worktree_path_limit_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", True)
    path = Path("C:/") / ("x" * lifecycle_git._MAX_WINDOWS_WORKTREE_PATH_CHARS)

    error = lifecycle_git._windows_path_error(path)

    assert error is not None
    assert "too long for portable Git on Windows" in error
    assert "shorter explicit worktree_root" in error


def test_directory_identity_rejects_reparse_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        lifecycle_git,
        "metadata_is_link_or_reparse_point",
        lambda _metadata: True,
    )

    with pytest.raises(PermissionError, match="identity is unavailable"):
        lifecycle_git._capture_directory_identity(tmp_path)


def test_status_exclusion_is_identity_bound_and_cannot_escape_repository(
    tmp_path: Path,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )

    assert lifecycle_git._base_status_args(tmp_path, None) == ["status", "--porcelain"]
    with pytest.raises(PermissionError, match="escaped"):
        lifecycle_git._base_status_args(
            tmp_path,
            replace(allocation, path=tmp_path.parent / allocation.path.name),
        )
    with pytest.raises(PermissionError, match="direct child"):
        lifecycle_git._base_status_args(
            tmp_path,
            replace(allocation, path=allocation.path / "nested"),
        )

    assert lifecycle_git._remove_empty_run_root(
        allocation.root_identity,
        allocation.parent_identity,
    )


def test_provisioning_reports_long_path_and_replaced_root_before_git(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    unit = WorkUnit("unit", "work", repo_path=tmp_path)
    calls: list[list[str]] = []
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", True)
    too_long = lifecycle_git._provision_unit_worktree(
        unit,
        repo=tmp_path,
        run_root=Path("C:/") / ("x" * lifecycle_git._MAX_WINDOWS_WORKTREE_PATH_CHARS),
        run_token="token",
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda _repo, args, **_kwargs: (
            calls.append(list(args)) or subprocess.CompletedProcess(["git"], 0, "", "")
        ),
    )
    assert "too long" in too_long.errors[0]
    assert calls == []

    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", os.name == "nt")
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )
    original = tmp_path / "owned-run-root"
    os.rename(allocation.path, original)
    allocation.path.mkdir()
    replaced = lifecycle_git._provision_unit_worktree(
        unit,
        repo=tmp_path,
        run_root=allocation.path,
        run_token=allocation.token,
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda _repo, args, **_kwargs: (
            calls.append(list(args)) or subprocess.CompletedProcess(["git"], 0, "", "")
        ),
        allocation=allocation,
    )
    assert replaced.errors == ["delegation worktree root was replaced during delegation"]
    assert calls == []


def test_default_fallback_failure_is_reported_per_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle_git, "_IS_WINDOWS", True)
    monkeypatch.setattr(
        lifecycle_git,
        "private_runtime_directory",
        lambda _name: (_ for _ in ()).throw(PermissionError("restricted token")),
    )
    monkeypatch.setattr(
        lifecycle_git,
        "_allocate_host_run_root",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("host denied")),
    )
    unit = WorkUnit("unit", "work", repo_path=tmp_path)

    worktrees = lifecycle_git.provision_worktrees(
        [unit],
        base_branch=None,
        worktree_root=Path.home() / ".agency-runtime" / "worktrees",
        run_git_func=lambda *_args, **_kwargs: pytest.fail("Git must not run"),
        git_root_func=lambda _path: tmp_path,
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda _repo, _ref: "a" * 40,
    )

    assert worktrees["unit"].created is False
    assert "secondary secure fallback failed with PermissionError" in worktrees["unit"].errors[0]
    assert "host-attested Windows worktree root is unavailable" in worktrees["unit"].errors[0]


def test_cleanup_postconditions_refuse_existing_or_replaced_paths(tmp_path: Path) -> None:
    path = tmp_path / "worktree"
    path.mkdir()
    info = WorktreeInfo(
        "unit",
        tmp_path,
        path,
        "delegation/unit",
        "main",
        "a" * 40,
        created=True,
    )
    record = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._remove_clean_worktree(
        info,
        record,
        run_git_func=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["git"],
            0,
            "",
            "",
        ),
    )
    assert record["removed"] is False
    assert record["preserved"] is True
    assert "path still exists" in record["errors"][0]

    run_root = tmp_path / "run-root"
    exact_path = run_root / "worktree"
    exact_path.mkdir(parents=True)
    root_identity = lifecycle_git._capture_directory_identity(run_root)
    parent_identity = lifecycle_git._capture_directory_identity(tmp_path)
    exact_info = replace(
        info,
        path=exact_path,
        worktree_identity=lifecycle_git._capture_directory_identity(exact_path),
        run_root_identity=root_identity,
        run_parent_identity=parent_identity,
    )
    exact_record = lifecycle_git._new_cleanup_record(exact_info)

    def remove_then_replace_root(*_args: object, **_kwargs: object):
        exact_path.rmdir()
        moved = tmp_path / "original-run-root"
        os.rename(run_root, moved)
        run_root.mkdir()
        return subprocess.CompletedProcess(["git"], 0, "", "")

    lifecycle_git._remove_clean_worktree(
        exact_info,
        exact_record,
        run_git_func=remove_then_replace_root,
    )
    assert exact_record["removed"] is False
    assert "identity check failed" in exact_record["errors"][0]


def test_quarantine_restores_nonempty_root_and_surfaces_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )
    original_rename = lifecycle_git.os.rename
    injected = False

    def inject_after_quarantine(source: Path, destination: Path) -> None:
        nonlocal injected
        original_rename(source, destination)
        if not injected:
            injected = True
            (destination / "preserved.txt").touch()

    monkeypatch.setattr(lifecycle_git.os, "rename", inject_after_quarantine)

    assert (
        lifecycle_git._remove_empty_run_root(
            allocation.root_identity,
            allocation.parent_identity,
        )
        is False
    )
    assert (allocation.path / "preserved.txt").exists()

    original = tmp_path / "original-after-replacement"
    original_rename(allocation.path, original)
    allocation.path.mkdir()
    info = WorktreeInfo(
        "unit",
        tmp_path,
        allocation.path / "worktree",
        "delegation/unit",
        "main",
        "a" * 40,
        run_root_identity=allocation.root_identity,
        run_parent_identity=allocation.parent_identity,
        repo_scoped_root=True,
    )
    record = lifecycle_git._new_cleanup_record(info)

    lifecycle_git._remove_empty_run_roots({"unit": info}, {"unit": record})

    assert allocation.path.exists()
    assert "exact cleanup failed" in record["errors"][0]


def test_failed_repository_inspection_retains_receipt_for_empty_root_cleanup(
    tmp_path: Path,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )
    unit = WorkUnit("unit", "work", repo_path=tmp_path)

    worktrees = lifecycle_git._provision_repository_worktrees(
        tmp_path,
        [unit],
        base_branch="main",
        run_root=allocation.path,
        run_token=allocation.token,
        run_git_func=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            ["git"],
            0,
            "",
            "",
        ),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: (_ for _ in ()).throw(OSError("head failed")),
        allocation=allocation,
    )

    assert worktrees["unit"].created is False
    assert worktrees["unit"].run_root_identity == allocation.root_identity
    cleanup = _cleanup(worktrees)
    assert "worktree was not created" in cleanup["unit"]["warnings"][-1]
    assert not allocation.path.exists()


def test_quarantine_detects_replacement_created_after_exact_delete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trusted_repository_fallback: None,
) -> None:
    del trusted_repository_fallback
    allocation = lifecycle_git._allocate_repository_run_root(
        tmp_path,
        fallback_error=PermissionError("restricted token"),
    )
    original_rmdir = lifecycle_git.os.rmdir

    def delete_then_replace(path: Path) -> None:
        original_rmdir(path)
        allocation.path.mkdir()

    monkeypatch.setattr(lifecycle_git.os, "rmdir", delete_then_replace)

    with pytest.raises(PermissionError, match="replaced during quarantine cleanup"):
        lifecycle_git._remove_empty_run_root(
            allocation.root_identity,
            allocation.parent_identity,
        )

    assert allocation.path.exists()
