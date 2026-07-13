"""Fail-closed Git worktree isolation for delegated work."""

from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol, TypedDict

from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)
from agency_runtime.core.delegation.lifecycle_graph import validate_unique_unit_ids
from agency_runtime.core.delegation.lifecycle_types import WorktreeInfo, WorkUnit

_MAX_GIT_OUTPUT_CHARS = 64 * 1024
_SAFE_CALLER_CONFIG = {
    "commit.gpgsign": {"false"},
    "core.hookspath": {""},
    "user.email": {"agency-runtime@localhost"},
    "user.name": {"Agency Runtime"},
}
_SAFE_GIT_CONFIG = (
    "core.hooksPath=",
    "core.fsmonitor=false",
    "core.attributesFile=",
    "core.pager=",
    "credential.interactive=never",
    "user.name=Agency Runtime",
    "user.email=agency-runtime@localhost",
    "commit.gpgSign=false",
    "merge.gpgSign=false",
    "tag.gpgSign=false",
    "diff.external=",
    "submodule.recurse=false",
)
_SAFE_GIT_ENVIRONMENT = {
    "GIT_ASKPASS": "",
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_EDITOR": "",
    "GIT_MERGE_AUTOEDIT": "no",
    "GIT_PAGER": "",
    "GIT_SEQUENCE_EDITOR": "",
    "GIT_TERMINAL_PROMPT": "0",
}
_CONFIG_SENSITIVE_COMMANDS = {
    "add",
    "am",
    "checkout",
    "checkout-index",
    "cherry-pick",
    "merge",
    "read-tree",
    "rebase",
    "reset",
    "restore",
    "switch",
}


class RunGitFunc(Protocol):
    """Git invocation seam used by lifecycle tests and host integrations."""

    def __call__(
        self, repo: Path, args: Sequence[str], *, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]: ...


GitRootFunc = Callable[[Path], Path | None]
CurrentBranchFunc = Callable[[Path], str | None]
HeadShaFunc = Callable[[Path, str], str]


def run_git(
    repo: Path, args: Sequence[str], *, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    """Run one bounded, non-interactive Git command with hostile config disabled."""
    normalized = _normalize_git_args(args)
    refusal = _executable_config_refusal(repo, normalized)
    if refusal is not None:
        return refusal
    return _invoke_git(repo, normalized, timeout=timeout)


def _normalize_git_args(args: Sequence[str]) -> list[str]:
    if isinstance(args, (str, bytes)) or not args:
        raise TypeError("Git args must be a non-empty sequence of strings")
    normalized = list(args)
    if any(not isinstance(item, str) or not item or "\x00" in item for item in normalized):
        raise ValueError("Git args contain an invalid item")
    _validate_caller_config(normalized)
    return normalized


def _validate_caller_config(args: Sequence[str]) -> None:
    index = 0
    while index < len(args) and args[index] == "-c":
        if index + 1 >= len(args):
            raise ValueError("Git -c requires a key=value argument")
        key, separator, value = args[index + 1].partition("=")
        allowed = _SAFE_CALLER_CONFIG.get(key.casefold())
        if separator != "=" or allowed is None or value not in allowed:
            raise ValueError("unsupported per-command Git configuration")
        index += 2
    if index >= len(args) or args[index].startswith("-"):
        raise ValueError("Git command must be an explicit non-option name")


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")
    }
    environment.update(_SAFE_GIT_ENVIRONMENT)
    return environment


def _safe_git_argv(args: Sequence[str]) -> list[str]:
    index = 0
    while index < len(args) and args[index] == "-c":
        index += 2
    caller_config = list(args[:index])
    command = list(args[index:])
    safe_config = [item for value in _SAFE_GIT_CONFIG for item in ("-c", value)]
    return ["git", "--no-pager", *caller_config, *safe_config, *command]


def _invoke_git(
    repo: Path,
    args: Sequence[str],
    *,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    argv = _safe_git_argv(args)
    result = run_bounded_process(
        argv,
        cwd=str(repo),
        env=_git_environment(),
        timeout=timeout,
        max_output_chars=_MAX_GIT_OUTPUT_CHARS,
    )
    return _completed_git_result(argv, result)


def _completed_git_result(
    argv: Sequence[str],
    result: BoundedProcessResult,
) -> subprocess.CompletedProcess[str]:
    if result.timed_out:
        return subprocess.CompletedProcess(
            list(argv), 124, "", "Git command exceeded its time limit"
        )
    if result.stdout_truncated or result.stderr_truncated:
        return subprocess.CompletedProcess(
            list(argv), 125, "", "Git command output exceeded its safety limit"
        )
    return subprocess.CompletedProcess(list(argv), result.returncode, result.stdout, result.stderr)


def _git_command(args: Sequence[str]) -> tuple[str, Sequence[str]]:
    index = 0
    while index < len(args) and args[index] == "-c":
        index += 2
    if index >= len(args):
        return "", ()
    return args[index].casefold(), args[index + 1 :]


def _requires_executable_config_scan(args: Sequence[str]) -> bool:
    command, command_args = _git_command(args)
    if command in _CONFIG_SENSITIVE_COMMANDS:
        return True
    return command == "worktree" and bool(command_args) and command_args[0] == "add"


def _dangerous_config_classes(names: str) -> set[str]:
    classes: set[str] = set()
    for raw_name in names.splitlines():
        name = raw_name.strip().casefold()
        if name.startswith("filter.") and name.endswith((".clean", ".smudge", ".process")):
            classes.add("filter")
        elif name.startswith("merge.") and name.endswith(".driver"):
            classes.add("merge driver")
        elif name.startswith("diff.") and name.endswith((".command", ".textconv")):
            classes.add("diff command")
    return classes


def _git_refusal(message: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        ["git"],
        126,
        "",
        message,
    )


def _executable_config_refusal(
    repo: Path,
    args: Sequence[str],
) -> subprocess.CompletedProcess[str] | None:
    if not _requires_executable_config_scan(args):
        return None
    inspection = _invoke_git(
        repo,
        ["config", "--local", "--includes", "--name-only", "--list"],
        timeout=10,
    )
    if inspection.returncode != 0:
        return _git_refusal(
            "Git operation refused: repository configuration could not be inspected safely"
        )
    dangerous = _dangerous_config_classes(inspection.stdout)
    if not dangerous:
        return None
    kinds = ", ".join(sorted(dangerous))
    return _git_refusal(f"Git operation refused: executable {kinds} configuration is unsupported")


def git_root(path: Path) -> Path | None:
    """Return the containing Git root, or ``None`` for a non-repository path."""
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    if candidate.is_file():
        candidate = candidate.parent
    if not candidate.exists():
        candidate = next((parent for parent in candidate.parents if parent.exists()), candidate)
    result = run_git(candidate, ["rev-parse", "--show-toplevel"], timeout=10)
    roots = result.stdout.splitlines()
    if result.returncode != 0 or len(roots) != 1 or not roots[0].strip():
        return None
    root = Path(roots[0].strip()).resolve()
    return root if root.is_dir() else None


def _validate_git_ref(ref: str) -> str:
    """Reject refs that could be parsed as options or terminal control data."""
    if (
        not ref
        or ref != ref.strip()
        or ref.startswith("-")
        or len(ref) > 1024
        or any(ord(character) < 32 or ord(character) == 127 for character in ref)
    ):
        raise ValueError("base_branch must be a non-option Git ref without controls")
    return ref


def current_branch(repo: Path, *, run_git_func: RunGitFunc = run_git) -> str | None:
    """Return the checked-out branch, excluding detached HEAD."""
    result = run_git_func(repo, ["rev-parse", "--abbrev-ref", "HEAD"], timeout=10)
    branch = result.stdout.strip()
    return branch if result.returncode == 0 and branch and branch != "HEAD" else None


def head_sha(
    repo: Path,
    ref: str = "HEAD",
    *,
    run_git_func: RunGitFunc = run_git,
) -> str:
    """Resolve a validated ref to a commit SHA."""
    validated_ref = _validate_git_ref(ref)
    result = run_git_func(
        repo,
        ["rev-parse", "--verify", f"{validated_ref}^{{commit}}"],
        timeout=10,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _unavailable_worktree(
    unit: WorkUnit,
    repo: Path,
    path: Path,
    error: str,
) -> WorktreeInfo:
    info = WorktreeInfo(unit.id, repo, path, "", "", "")
    info.errors.append(error)
    return info


def _group_units_by_repository(
    units: Sequence[WorkUnit],
    *,
    worktree_root: Path,
    git_root_func: GitRootFunc,
) -> tuple[dict[Path, list[WorkUnit]], dict[str, WorktreeInfo]]:
    by_repo: dict[Path, list[WorkUnit]] = defaultdict(list)
    resolved_roots: dict[Path, Path | None] = {}
    unavailable: dict[str, WorktreeInfo] = {}
    for unit in units:
        if not unit.repo_path:
            continue
        try:
            candidate = unit.repo_path.resolve()
            if candidate not in resolved_roots:
                resolved_roots[candidate] = git_root_func(candidate)
        except Exception as exc:
            candidate = unit.repo_path
            error = f"could not determine Git repository: {type(exc).__name__}: {exc}"
            unavailable[unit.id] = _unavailable_worktree(
                unit,
                candidate,
                worktree_root / f"unavailable-{unit.id}",
                error,
            )
            continue
        repo = resolved_roots[candidate]
        if repo is not None:
            by_repo[repo].append(unit)
    return dict(by_repo), unavailable


def _inspect_repository_for_provisioning(
    repo: Path,
    *,
    base_branch: str | None,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> tuple[str, str, bool, list[str]]:
    base = base_branch or current_branch_func(repo) or "HEAD"
    _validate_git_ref(base)
    base_sha = head_sha_func(repo, base)
    if not base_sha:
        raise RuntimeError(f"could not resolve base ref {base!r} to a commit")
    status = run_git_func(repo, ["status", "--porcelain"], timeout=30)
    dirty = status.returncode != 0 or bool(status.stdout.strip())
    warnings = ["could not prove that the base worktree is clean"] if status.returncode != 0 else []
    return base, base_sha, dirty, warnings


def _provision_unit_worktree(
    unit: WorkUnit,
    *,
    repo: Path,
    run_root: Path,
    run_token: str,
    base: str,
    base_sha: str,
    dirty: bool,
    warnings: Sequence[str],
    run_git_func: RunGitFunc,
) -> WorktreeInfo:
    branch = f"delegation/{unit.id}-{run_token[:12]}"
    path = run_root / unit.id
    info = WorktreeInfo(
        unit.id,
        repo,
        path,
        branch,
        base,
        base_sha,
        dirty_repo=dirty,
        warnings=list(warnings),
    )
    if path.exists():
        info.errors.append(f"unique worktree path unexpectedly exists: {path}")
        return info
    try:
        # Pin allocation to the inspected commit and suppress checkout hooks.
        result = run_git_func(
            repo,
            [
                "-c",
                "core.hooksPath=",
                "worktree",
                "add",
                str(path),
                "-b",
                branch,
                base_sha,
            ],
        )
        if result.returncode == 0:
            info.created = True
        else:
            info.errors.append(_git_error(result, "git worktree add failed"))
    except Exception as exc:
        info.errors.append(f"git worktree add failed: {type(exc).__name__}: {exc}")
    return info


def _provision_repository_worktrees(
    repo: Path,
    repo_units: Sequence[WorkUnit],
    *,
    base_branch: str | None,
    run_root: Path,
    run_token: str,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> dict[str, WorktreeInfo]:
    try:
        base, base_sha, dirty, warnings = _inspect_repository_for_provisioning(
            repo,
            base_branch=base_branch,
            run_git_func=run_git_func,
            current_branch_func=current_branch_func,
            head_sha_func=head_sha_func,
        )
    except Exception as exc:
        error = f"could not inspect Git repository: {type(exc).__name__}: {exc}"
        return {
            unit.id: _unavailable_worktree(unit, repo, run_root / unit.id, error)
            for unit in repo_units
        }
    return {
        unit.id: _provision_unit_worktree(
            unit,
            repo=repo,
            run_root=run_root,
            run_token=run_token,
            base=base,
            base_sha=base_sha,
            dirty=dirty,
            warnings=warnings,
            run_git_func=run_git_func,
        )
        for unit in repo_units
    }


def provision_worktrees(
    units: Sequence[WorkUnit],
    *,
    base_branch: str | None,
    worktree_root: Path,
    run_git_func: RunGitFunc,
    git_root_func: GitRootFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> dict[str, WorktreeInfo]:
    """Create one isolated worktree for every unit targeting a Git repository."""
    validate_unique_unit_ids(units)
    if base_branch is not None:
        _validate_git_ref(base_branch)
    by_repo, worktrees = _group_units_by_repository(
        units,
        worktree_root=worktree_root,
        git_root_func=git_root_func,
    )
    if not by_repo:
        return worktrees

    worktree_root.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="run-", dir=str(worktree_root)))
    run_token = run_root.name.removeprefix("run-").replace("-", "")
    run_token = run_token or uuid.uuid4().hex

    for repo, repo_units in by_repo.items():
        worktrees.update(
            _provision_repository_worktrees(
                repo,
                repo_units,
                base_branch=base_branch,
                run_root=run_root,
                run_token=run_token,
                run_git_func=run_git_func,
                current_branch_func=current_branch_func,
                head_sha_func=head_sha_func,
            )
        )
    return worktrees


def _git_error(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    return result.stderr.strip() or result.stdout.strip() or fallback


def merge_predecessor_work(
    unit_id: str,
    predecessor_ids: Sequence[str] | set[str],
    worktrees: Mapping[str, WorktreeInfo],
    *,
    run_git_func: RunGitFunc,
) -> str | None:
    """Merge successful same-repository predecessor branches before dispatch."""
    target = worktrees.get(unit_id)
    if target is None or not target.created:
        return None
    for predecessor_id in sorted(predecessor_ids):
        predecessor = worktrees.get(predecessor_id)
        if predecessor is None or not predecessor.created:
            continue
        if predecessor.repo_path.resolve() != target.repo_path.resolve():
            continue
        merge = run_git_func(
            target.path,
            [
                "-c",
                "core.hooksPath=",
                "merge",
                "--no-ff",
                "--no-edit",
                "--",
                predecessor.branch,
            ],
        )
        if merge.returncode == 0:
            continue
        run_git_func(target.path, ["merge", "--abort"])
        detail = _git_error(merge, "git merge failed")
        return f"could not apply predecessor {predecessor_id!r}: {detail}"
    return None


def commit_successful_worktree(
    info: WorktreeInfo,
    unit_id: str,
    *,
    run_git_func: RunGitFunc,
) -> str | None:
    """Commit successful uncommitted worker edits so they cannot be discarded."""
    status = run_git_func(info.path, ["status", "--porcelain"], timeout=30)
    if status.returncode != 0:
        return _git_error(status, "could not inspect worktree changes")
    if not status.stdout.strip():
        return None
    staged = run_git_func(info.path, ["add", "--all"], timeout=60)
    if staged.returncode != 0:
        return _git_error(staged, "could not stage worker changes")
    committed = run_git_func(
        info.path,
        [
            "-c",
            "user.name=Agency Runtime",
            "-c",
            "user.email=agency-runtime@localhost",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=",
            "commit",
            "-m",
            f"agency(delegate): complete {unit_id}",
        ],
        timeout=60,
    )
    if committed.returncode != 0:
        return _git_error(committed, "could not commit worker changes")
    return None


class CleanupRecord(TypedDict):
    branch: str
    worktree: str
    merged: bool
    removed: bool
    preserved: bool
    branch_deleted: bool
    conflict: bool
    warnings: list[str]
    errors: list[str]


def _new_cleanup_record(info: WorktreeInfo) -> CleanupRecord:
    return {
        "branch": info.branch,
        "worktree": str(info.path),
        "merged": False,
        "removed": False,
        "preserved": False,
        "branch_deleted": False,
        "conflict": False,
        "warnings": list(info.warnings),
        "errors": list(info.errors),
    }


def _merge_safety(
    info: WorktreeInfo,
    *,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> tuple[bool, str]:
    try:
        current = current_branch_func(info.repo_path)
        current_head = head_sha_func(info.repo_path, "HEAD")
        status = run_git_func(info.repo_path, ["status", "--porcelain"], timeout=30)
    except Exception as exc:
        return False, f"could not inspect base worktree: {type(exc).__name__}: {exc}"

    reasons: list[str] = []
    if info.dirty_repo:
        reasons.append("base worktree was dirty before delegation")
    if status.returncode != 0:
        reasons.append("could not prove that the base worktree is clean")
    elif status.stdout.strip():
        reasons.append("base worktree is dirty")
    if current != info.base_branch:
        reasons.append(f"base worktree switched from {info.base_branch!r} to {current!r}")
    if not info.base_sha or current_head != info.base_sha:
        reasons.append("base branch head changed during delegation")
    return not reasons, "; ".join(reasons)


def _merge_permission(
    info: WorktreeInfo,
    cache: dict[tuple[Path, str, str], tuple[bool, str]],
    *,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> tuple[bool, str]:
    try:
        key = (info.repo_path.resolve(), info.base_branch, info.base_sha)
    except Exception as exc:
        return False, f"could not resolve base worktree: {type(exc).__name__}: {exc}"
    if key not in cache:
        cache[key] = _merge_safety(
            info,
            run_git_func=run_git_func,
            current_branch_func=current_branch_func,
            head_sha_func=head_sha_func,
        )
    return cache[key]


def _attempt_merge_back(
    info: WorktreeInfo,
    record: CleanupRecord,
    cache: dict[tuple[Path, str, str], tuple[bool, str]],
    *,
    create_pr_on_conflict: bool,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> None:
    allowed, reason = _merge_permission(
        info,
        cache,
        run_git_func=run_git_func,
        current_branch_func=current_branch_func,
        head_sha_func=head_sha_func,
    )
    if not allowed:
        record["warnings"].append(f"branch preserved instead of merging: {reason}")
        return
    try:
        merge = run_git_func(
            info.repo_path,
            [
                "-c",
                "core.hooksPath=",
                "merge",
                "--no-ff",
                "--no-edit",
                "--",
                info.branch,
            ],
        )
        if merge.returncode == 0:
            record["merged"] = True
            return
        record["conflict"] = True
        record["errors"].append(_git_error(merge, "merge failed"))
        run_git_func(info.repo_path, ["merge", "--abort"])
        if create_pr_on_conflict:
            record["warnings"].append(
                "merge conflict encountered; branch left for PR/manual resolution"
            )
    except Exception as exc:
        record["errors"].append(f"merge failed: {type(exc).__name__}: {exc}")
        record["warnings"].append("branch preserved because merge safety failed")


def _preserve_worktree(record: CleanupRecord, warning: str) -> None:
    record["preserved"] = True
    record["warnings"].append(warning)


def _worktree_is_clean_for_removal(
    info: WorktreeInfo,
    record: CleanupRecord,
    *,
    run_git_func: RunGitFunc,
) -> bool:
    try:
        dirty = run_git_func(info.path, ["status", "--porcelain"], timeout=30)
    except Exception as exc:
        record["errors"].append(
            f"could not inspect worktree before removal: {type(exc).__name__}: {exc}"
        )
        _preserve_worktree(
            record,
            "worktree preserved because cleanliness could not be proven",
        )
        return False
    if dirty.returncode != 0:
        record["errors"].append(_git_error(dirty, "could not inspect worktree before removal"))
        _preserve_worktree(
            record,
            "worktree preserved because cleanliness could not be proven",
        )
        return False
    if dirty.stdout.strip():
        _preserve_worktree(
            record,
            "uncommitted worker changes preserved for manual recovery",
        )
        return False
    return True


def _delete_merged_branch(
    info: WorktreeInfo,
    record: CleanupRecord,
    *,
    run_git_func: RunGitFunc,
) -> None:
    try:
        deleted = run_git_func(
            info.repo_path,
            ["branch", "--delete", "--", info.branch],
            timeout=30,
        )
    except Exception as exc:
        record["warnings"].append(
            f"merged branch could not be deleted: {type(exc).__name__}: {exc}"
        )
        return
    if deleted.returncode == 0:
        record["branch_deleted"] = True
    else:
        record["warnings"].append(_git_error(deleted, "merged branch could not be deleted"))


def _remove_clean_worktree(
    info: WorktreeInfo,
    record: CleanupRecord,
    *,
    run_git_func: RunGitFunc,
) -> None:
    try:
        remove = run_git_func(info.repo_path, ["worktree", "remove", str(info.path)])
    except Exception as exc:
        record["errors"].append(f"worktree remove failed: {type(exc).__name__}: {exc}")
        _preserve_worktree(
            record,
            "worktree removal failed; path preserved for manual recovery",
        )
        return
    if remove.returncode != 0:
        record["errors"].append(_git_error(remove, "worktree remove failed"))
        _preserve_worktree(
            record,
            "worktree removal failed; path preserved for manual recovery",
        )
        return
    record["removed"] = True
    if record["merged"]:
        _delete_merged_branch(info, record, run_git_func=run_git_func)


def _cleanup_one_worktree(
    unit_id: str,
    info: WorktreeInfo,
    merge_allowed: dict[tuple[Path, str, str], tuple[bool, str]],
    *,
    merge_back: bool,
    create_pr_on_conflict: bool,
    merge_unit_ids: set[str] | None,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> CleanupRecord:
    record = _new_cleanup_record(info)
    if not info.created:
        record["warnings"].append("worktree was not created; skipping cleanup")
        return record
    should_merge = merge_back and (merge_unit_ids is None or unit_id in merge_unit_ids)
    if merge_back and not should_merge:
        record["warnings"].append("work unit did not complete successfully; branch was not merged")
    if should_merge:
        _attempt_merge_back(
            info,
            record,
            merge_allowed,
            create_pr_on_conflict=create_pr_on_conflict,
            run_git_func=run_git_func,
            current_branch_func=current_branch_func,
            head_sha_func=head_sha_func,
        )
    if _worktree_is_clean_for_removal(info, record, run_git_func=run_git_func):
        _remove_clean_worktree(info, record, run_git_func=run_git_func)
    return record


def cleanup_worktrees(
    worktrees: Mapping[str, WorktreeInfo],
    *,
    merge_back: bool,
    create_pr_on_conflict: bool,
    merge_unit_ids: set[str] | None,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> dict[str, CleanupRecord]:
    """Merge completed branches and remove only provably clean worktrees."""
    cleanup: dict[str, CleanupRecord] = {}
    merge_allowed: dict[tuple[Path, str, str], tuple[bool, str]] = {}
    for unit_id, info in worktrees.items():
        cleanup[unit_id] = _cleanup_one_worktree(
            unit_id,
            info,
            merge_allowed,
            merge_back=merge_back,
            create_pr_on_conflict=create_pr_on_conflict,
            merge_unit_ids=merge_unit_ids,
            run_git_func=run_git_func,
            current_branch_func=current_branch_func,
            head_sha_func=head_sha_func,
        )
    _remove_empty_run_roots(worktrees)
    return cleanup


def _remove_empty_run_roots(worktrees: Mapping[str, WorktreeInfo]) -> None:
    """Remove only empty lifecycle-owned run directories after cleanup."""
    candidates = {
        info.path.parent
        for info in worktrees.values()
        if info.created and info.path.parent.name.startswith("run-")
    }
    for candidate in candidates:
        try:
            candidate.rmdir()
        except OSError:
            # A preserved/foreign path or concurrent run still owns content.
            continue


__all__ = [
    "cleanup_worktrees",
    "commit_successful_worktree",
    "current_branch",
    "git_root",
    "head_sha",
    "merge_predecessor_work",
    "provision_worktrees",
    "run_git",
]
