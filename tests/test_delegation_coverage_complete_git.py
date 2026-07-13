"""Fail-closed Git lifecycle error and recovery contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.delegation import lifecycle_git
from agency_runtime.core.delegation.lifecycle_types import WorktreeInfo, WorkUnit


def _completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


def _info(tmp_path: Path, *, created: bool = True) -> WorktreeInfo:
    return WorktreeInfo(
        "unit",
        tmp_path,
        tmp_path / "worktree",
        "delegation/unit",
        "main",
        "a" * 40,
        created=created,
    )


def test_git_argument_helpers_reject_incomplete_config_and_empty_command() -> None:
    with pytest.raises(ValueError, match="requires a key=value"):
        lifecycle_git._validate_caller_config(["-c"])
    assert lifecycle_git._git_command(["-c", "core.hooksPath="]) == ("", ())


def test_git_root_normalizes_relative_missing_candidate_and_failed_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[Path] = []

    def fail(repo: Path, _args: list[str], *, timeout: int = 120):
        del timeout
        observed.append(repo)
        return _completed(128)

    monkeypatch.setattr(lifecycle_git, "run_git", fail)

    assert lifecycle_git.git_root(Path("missing-parent") / "child") is None
    assert observed[0].is_absolute()
    assert observed[0].exists()


def test_repository_inspection_rejects_unresolvable_base(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="could not resolve base ref"):
        lifecycle_git._inspect_repository_for_provisioning(
            tmp_path,
            base_branch="main",
            run_git_func=lambda *_args, **_kwargs: _completed(),
            current_branch_func=lambda _repo: "main",
            head_sha_func=lambda _repo, _ref: "",
        )


def test_unit_provisioning_handles_collision_nonzero_and_exception(tmp_path: Path) -> None:
    unit = WorkUnit("unit", "work", repo_path=tmp_path)
    run_root = tmp_path / "runs"
    collision = run_root / "unit"
    collision.mkdir(parents=True)
    collided = lifecycle_git._provision_unit_worktree(
        unit,
        repo=tmp_path,
        run_root=run_root,
        run_token="token",
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda *_args, **_kwargs: _completed(),
    )
    assert "unexpectedly exists" in collided.errors[0]

    collision.rmdir()
    failed = lifecycle_git._provision_unit_worktree(
        unit,
        repo=tmp_path,
        run_root=run_root,
        run_token="token",
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda *_args, **_kwargs: _completed(1, stderr="add failed"),
    )
    assert failed.errors == ["add failed"]

    raised = lifecycle_git._provision_unit_worktree(
        unit,
        repo=tmp_path,
        run_root=run_root,
        run_token="token",
        base="main",
        base_sha="a" * 40,
        dirty=False,
        warnings=[],
        run_git_func=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("git unavailable")),
    )
    assert "OSError: git unavailable" in raised.errors[0]


def test_repository_provisioning_converts_inspection_exception_per_unit(
    tmp_path: Path,
) -> None:
    unit = WorkUnit("unit", "work", repo_path=tmp_path)
    result = lifecycle_git._provision_repository_worktrees(
        tmp_path,
        [unit],
        base_branch="main",
        run_root=tmp_path / "runs",
        run_token="token",
        run_git_func=lambda *_args, **_kwargs: _completed(),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: (_ for _ in ()).throw(OSError("head failed")),
    )
    assert "could not inspect Git repository" in result["unit"].errors[0]


def test_git_error_falls_back_from_stderr_to_stdout_to_default() -> None:
    assert lifecycle_git._git_error(_completed(1, stderr="stderr"), "fallback") == "stderr"
    assert lifecycle_git._git_error(_completed(1, stdout="stdout"), "fallback") == "stdout"
    assert lifecycle_git._git_error(_completed(1), "fallback") == "fallback"


def test_predecessor_merge_skips_missing_cross_repo_and_aborts_failure(
    tmp_path: Path,
) -> None:
    target = _info(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    missing = _info(tmp_path)
    missing.created = False
    cross_repo = _info(other_root)
    calls: list[list[str]] = []

    def fail_merge(_repo: Path, args: list[str], **_kwargs: Any):
        calls.append(args)
        return _completed(1, stderr="merge conflict") if "--no-ff" in args else _completed()

    error = lifecycle_git.merge_predecessor_work(
        "unit",
        {"missing", "cross", "producer"},
        {
            "unit": target,
            "missing": missing,
            "cross": cross_repo,
            "producer": WorktreeInfo(
                "producer",
                tmp_path,
                tmp_path / "producer",
                "delegation/producer",
                "main",
                "a" * 40,
                created=True,
            ),
        },
        run_git_func=fail_merge,
    )

    assert error == "could not apply predecessor 'producer': merge conflict"
    assert calls[-1] == ["merge", "--abort"]


@pytest.mark.parametrize("failure_stage", ["status", "add", "commit"])
def test_commit_successful_worktree_returns_each_git_failure(
    tmp_path: Path,
    failure_stage: str,
) -> None:
    info = _info(tmp_path)
    calls: list[str] = []

    def git(_repo: Path, args: list[str], **_kwargs: Any):
        command = "status" if "status" in args else "add" if "add" in args else "commit"
        calls.append(command)
        if command == failure_stage:
            return _completed(1, stderr=f"{command} failed")
        return _completed(0, stdout=" M file.py" if command == "status" else "")

    assert (
        lifecycle_git.commit_successful_worktree(info, "unit", run_git_func=git)
        == f"{failure_stage} failed"
    )
    assert failure_stage in calls


def test_merge_safety_reports_exception_and_every_changed_base_reason(tmp_path: Path) -> None:
    info = _info(tmp_path)
    failed = lifecycle_git._merge_safety(
        info,
        run_git_func=lambda *_args, **_kwargs: _completed(),
        current_branch_func=lambda _repo: (_ for _ in ()).throw(OSError("inspect failed")),
        head_sha_func=lambda *_args: "",
    )
    assert failed == (False, "could not inspect base worktree: OSError: inspect failed")

    info.dirty_repo = True
    info.base_sha = ""
    allowed, reason = lifecycle_git._merge_safety(
        info,
        run_git_func=lambda *_args, **_kwargs: _completed(1),
        current_branch_func=lambda _repo: "other",
        head_sha_func=lambda *_args: "changed",
    )
    assert allowed is False
    assert "was dirty before" in reason
    assert "could not prove" in reason
    assert "switched" in reason
    assert "head changed" in reason

    info.dirty_repo = False
    info.base_sha = "a" * 40
    _, dirty_reason = lifecycle_git._merge_safety(
        info,
        run_git_func=lambda *_args, **_kwargs: _completed(0, stdout=" M file.py"),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: "a" * 40,
    )
    assert dirty_reason == "base worktree is dirty"


def test_merge_permission_handles_unresolvable_repository_path() -> None:
    class BrokenPath:
        def resolve(self) -> Path:
            raise OSError("cannot resolve")

    info = SimpleNamespace(repo_path=BrokenPath(), base_branch="main", base_sha="a" * 40)
    allowed, reason = lifecycle_git._merge_permission(
        info,  # type: ignore[arg-type]
        {},
        run_git_func=lambda *_args, **_kwargs: _completed(),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: "a" * 40,
    )
    assert allowed is False
    assert "could not resolve base worktree" in reason


def test_merge_back_records_conflict_pr_guidance_and_exception(tmp_path: Path) -> None:
    info = _info(tmp_path)
    key = (tmp_path.resolve(), info.base_branch, info.base_sha)
    record = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._attempt_merge_back(
        info,
        record,
        {key: (True, "")},
        create_pr_on_conflict=True,
        run_git_func=lambda _repo, args, **_kwargs: (
            _completed(1, stderr="conflict") if "--no-ff" in args else _completed()
        ),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: info.base_sha,
    )
    assert record["conflict"] is True
    assert "branch left for PR" in record["warnings"][0]

    no_guidance = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._attempt_merge_back(
        info,
        no_guidance,
        {key: (True, "")},
        create_pr_on_conflict=False,
        run_git_func=lambda _repo, args, **_kwargs: (
            _completed(1, stderr="conflict") if "--no-ff" in args else _completed()
        ),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: info.base_sha,
    )
    assert no_guidance["conflict"] is True
    assert no_guidance["warnings"] == []

    raised = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._attempt_merge_back(
        info,
        raised,
        {key: (True, "")},
        create_pr_on_conflict=False,
        run_git_func=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("merge unavailable")),
        current_branch_func=lambda _repo: "main",
        head_sha_func=lambda *_args: info.base_sha,
    )
    assert "merge failed: OSError" in raised["errors"][0]
    assert "merge safety failed" in raised["warnings"][0]


def test_cleanup_helpers_fail_closed_on_git_errors(tmp_path: Path) -> None:
    info = _info(tmp_path)
    record = lifecycle_git._new_cleanup_record(info)
    assert (
        lifecycle_git._worktree_is_clean_for_removal(
            info,
            record,
            run_git_func=lambda *_args, **_kwargs: _completed(1, stderr="status failed"),
        )
        is False
    )
    assert record["preserved"] is True

    record = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._delete_merged_branch(
        info,
        record,
        run_git_func=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("delete unavailable")),
    )
    assert "could not be deleted" in record["warnings"][0]

    record = lifecycle_git._new_cleanup_record(info)
    lifecycle_git._delete_merged_branch(
        info,
        record,
        run_git_func=lambda *_args, **_kwargs: _completed(1, stderr="delete failed"),
    )
    assert record["warnings"] == ["delete failed"]

    for result in (
        OSError("remove unavailable"),
        _completed(1, stderr="remove failed"),
    ):
        record = lifecycle_git._new_cleanup_record(info)

        def remove(*_args: Any, outcome: Any = result, **_kwargs: Any):
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        lifecycle_git._remove_clean_worktree(info, record, run_git_func=remove)
        assert record["preserved"] is True
        assert record["removed"] is False
