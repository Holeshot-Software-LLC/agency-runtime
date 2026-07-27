"""Fail-closed Git worktree isolation for delegated work."""

from __future__ import annotations

import os
import secrets
import stat
import subprocess
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypedDict

from agency_runtime.core.configuration_persistence import config_namespace_is_trusted
from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)
from agency_runtime.core.delegation.lifecycle_graph import validate_unique_unit_ids
from agency_runtime.core.delegation.lifecycle_types import (
    WorktreeInfo,
    WorktreePathIdentity,
    WorkUnit,
)
from agency_runtime.core.exception_notes import add_exception_note
from agency_runtime.core.filesystem_trust import absolute_path as _absolute
from agency_runtime.core.private_paths import (
    PrivateDirectoryIdentity,
    allocate_host_private_directory,
    allocate_private_directory,
    ensure_private_directory,
    private_runtime_directory,
    remove_private_directory,
    validate_private_directory,
)
from agency_runtime.core.process_argv import (
    repository_forbidden_roots,
    resolve_executable_path,
    sanitized_executable_search_path,
)
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    is_link_or_reparse_point,
    metadata_is_link_or_reparse_point,
    restrict_path_permissions,
    restrict_windows_acl,
    storage_parent_is_trusted,
)

_MAX_GIT_OUTPUT_CHARS = 64 * 1024
_MAX_WINDOWS_WORKTREE_PATH_CHARS = 240
_IS_WINDOWS = os.name == "nt"
_SAFE_CALLER_CONFIG = {
    "commit.gpgsign": {"false"},
    "core.hookspath": {""},
    "user.email": {"agency-runtime@localhost"},
    "user.name": {"Agency Runtime"},
}
_SAFE_GIT_CONFIG = (
    "core.hooksPath=",
    "core.fsmonitor=false",
    "core.longpaths=true",
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


@dataclass(frozen=True, slots=True)
class _AllocatedRunRoot:
    path: Path
    token: str
    root_identity: WorktreePathIdentity
    parent_identity: WorktreePathIdentity
    private_identity: PrivateDirectoryIdentity | None = None
    repo_scoped: bool = False
    warning: str = ""


def _capture_directory_identity(path: Path) -> WorktreePathIdentity:
    target = _absolute(path)
    metadata = os.lstat(target)
    inode = int(getattr(metadata, "st_ino", 0) or 0)
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or inode <= 0
    ):
        raise PermissionError("delegation directory identity is unavailable")
    return WorktreePathIdentity(target, int(metadata.st_dev), inode)


def _directory_identity_is_current(identity: WorktreePathIdentity) -> bool:
    try:
        metadata = os.lstat(identity.path)
    except OSError:
        return False
    return bool(
        not metadata_is_link_or_reparse_point(metadata)
        and stat.S_ISDIR(metadata.st_mode)
        and int(metadata.st_dev) == identity.device
        and int(getattr(metadata, "st_ino", 0) or 0) == identity.inode
    )


def _require_directory_identity(
    identity: WorktreePathIdentity,
    *,
    label: str,
) -> None:
    if not _directory_identity_is_current(identity):
        raise PermissionError(f"{label} was replaced during delegation")


def _require_private_identity(identity: PrivateDirectoryIdentity | None) -> None:
    if identity is None:
        return
    if identity.guard is None and identity.parent_guard is None:
        validate_private_directory(identity.path)
        if not _directory_identity_is_current(_identity_from_private(identity)):
            raise PermissionError("private delegation worktree root was replaced")
        return
    if identity.guard is None or identity.parent_guard is None:
        raise PermissionError("delegation worktree root guard receipt is incomplete")
    if not identity.guard.is_current():
        raise PermissionError("host-attested delegation worktree root was replaced")
    if not identity.parent_guard.is_current():
        raise PermissionError("host-attested Codex task root was replaced")


def _windows_path_error(path: Path) -> str | None:
    if not _IS_WINDOWS:
        return None
    length = len(str(_absolute(path)))
    if length < _MAX_WINDOWS_WORKTREE_PATH_CHARS:
        return None
    return (
        "worktree path is too long for portable Git on Windows "
        f"({length} characters; limit {_MAX_WINDOWS_WORKTREE_PATH_CHARS - 1}); "
        "configure a shorter explicit worktree_root"
    )


def _identity_from_private(identity: PrivateDirectoryIdentity) -> WorktreePathIdentity:
    return WorktreePathIdentity(
        _absolute(identity.path),
        int(identity.device),
        int(identity.inode),
    )


def _allocate_private_run_root(private_root: Path) -> _AllocatedRunRoot:
    parent_identity = _capture_directory_identity(private_root)
    private_identity = allocate_private_directory(private_root, prefix="run")
    root_identity = _identity_from_private(private_identity)
    try:
        _require_directory_identity(parent_identity, label="private worktree parent")
        _require_directory_identity(root_identity, label="private worktree root")
    except BaseException as exc:
        try:
            remove_private_directory(private_identity)
        except Exception as cleanup_error:
            add_exception_note(
                exc,
                f"private worktree root rollback failed: {cleanup_error}",
            )
        raise
    token = root_identity.path.name.removeprefix("run-").replace("-", "")
    return _AllocatedRunRoot(
        path=root_identity.path,
        token=token,
        root_identity=root_identity,
        parent_identity=parent_identity,
        private_identity=private_identity,
    )


def _allocate_host_run_root(*, fallback_error: BaseException) -> _AllocatedRunRoot:
    """Allocate one Codex-attested Windows run root outside the repository."""

    private_identity = allocate_host_private_directory(prefix="worktrees")
    if private_identity.parent_guard is None:
        if private_identity.guard is not None:
            private_identity.guard.close()
        raise PermissionError("host-attested worktree root receipt is incomplete")
    root_identity = _identity_from_private(private_identity)
    parent_identity = _capture_directory_identity(private_identity.parent_guard.path)
    return _AllocatedRunRoot(
        path=root_identity.path,
        token=secrets.token_hex(16),
        root_identity=root_identity,
        parent_identity=parent_identity,
        private_identity=private_identity,
        warning=(
            "private runtime worktree storage was unavailable; using the exact "
            "host-attested Codex task root for this run "
            f"({type(fallback_error).__name__})"
        ),
    )


def _allocate_repository_run_root(
    repo: Path,
    *,
    fallback_error: BaseException,
) -> _AllocatedRunRoot:
    """Allocate one unpredictable run root inside an explicitly scoped repository."""

    repository = _absolute(repo)
    assert_storage_parent_chain(repository, allow_missing=False)
    if not config_namespace_is_trusted(
        repository / ".agency-worktree-namespace-probe",
        is_windows=_IS_WINDOWS,
    ):
        raise PermissionError(
            "repository namespace permits cross-account worktree substitution; "
            "configure an owner-controlled explicit worktree_root"
        )
    parent_identity = _capture_directory_identity(repository)
    for _attempt in range(100):
        token = secrets.token_hex(16)
        candidate = repository / f".agency-worktrees-{token}"
        _require_directory_identity(parent_identity, label="delegation repository")
        length_error = _windows_path_error(candidate / f"w-{'0' * 24}")
        if length_error is not None:
            raise OSError(length_error)
        try:
            os.mkdir(candidate, 0o777 if _IS_WINDOWS else stat.S_IRWXU)
        except FileExistsError:
            continue
        except OSError as exc:
            raise PermissionError(
                "could not allocate a repository-scoped delegation worktree root"
            ) from exc

        root_identity: WorktreePathIdentity | None = None
        try:
            root_identity = _capture_directory_identity(candidate)
            restrict_path_permissions(
                candidate,
                directory=True,
                is_windows=_IS_WINDOWS,
                link_checker=is_link_or_reparse_point,
                windows_acl=lambda path, *, directory: restrict_windows_acl(
                    path,
                    directory=directory,
                    is_windows=_IS_WINDOWS,
                ),
            )
            if not storage_parent_is_trusted(
                candidate,
                is_windows=_IS_WINDOWS,
                final_parent=True,
            ):
                raise PermissionError("repository-scoped delegation worktree root is not private")
            _require_directory_identity(parent_identity, label="delegation repository")
            _require_directory_identity(root_identity, label="delegation worktree root")
        except BaseException as exc:
            if (
                root_identity is not None
                and _directory_identity_is_current(parent_identity)
                and _directory_identity_is_current(root_identity)
            ):
                try:
                    os.rmdir(root_identity.path)
                except OSError as cleanup_error:
                    add_exception_note(
                        exc,
                        f"delegation root rollback failed: {cleanup_error}",
                    )
            raise
        return _AllocatedRunRoot(
            path=root_identity.path,
            token=token,
            root_identity=root_identity,
            parent_identity=parent_identity,
            repo_scoped=True,
            warning=(
                "private runtime worktree storage was unavailable; using an exclusive "
                "repository-scoped worktree root for this run "
                f"({type(fallback_error).__name__})"
            ),
        )
    raise RuntimeError("could not allocate a unique repository-scoped worktree root")


def _worktree_component(allocation: _AllocatedRunRoot, unit: WorkUnit) -> str:
    if not allocation.repo_scoped:
        return unit.id
    return f"w-{secrets.token_hex(12)}"


def _base_status_args(
    repo: Path,
    allocation: _AllocatedRunRoot | None,
) -> list[str]:
    if allocation is None or not allocation.repo_scoped:
        return ["status", "--porcelain"]
    _require_directory_identity(allocation.parent_identity, label="delegation repository")
    _require_directory_identity(allocation.root_identity, label="delegation worktree root")
    try:
        relative = allocation.path.relative_to(_absolute(repo))
    except ValueError as exc:
        raise PermissionError("repository-scoped worktree root escaped its repository") from exc
    if len(relative.parts) != 1 or relative.name != allocation.path.name:
        raise PermissionError("repository-scoped worktree root is not a direct child")
    return [
        "status",
        "--porcelain",
        "--untracked-files=normal",
        "--",
        ".",
        f":(exclude){relative.as_posix()}",
    ]


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
    try:
        forbidden_roots = repository_forbidden_roots(repo)
        search_path = sanitized_executable_search_path(
            os.environ.get("PATH", ""),
            current_directory=repo,
            forbidden_roots=forbidden_roots,
        )
        argv[0] = resolve_executable_path(
            "git",
            search_path=search_path,
            current_directory=repo,
            forbidden_roots=forbidden_roots,
        )
    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
        return _git_refusal(f"Git operation refused: trusted executable is unavailable: {exc}")
    try:
        executable = Path(argv[0]).resolve(strict=True)
        inside_forbidden_root = any(
            executable.is_relative_to(Path(root).resolve(strict=True)) for root in forbidden_roots
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return _git_refusal(f"Git operation refused: executable identity failed: {exc}")
    if inside_forbidden_root:
        return _git_refusal(
            "Git operation refused: executable resolved inside the target repository"
        )
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
    *,
    allocation: _AllocatedRunRoot | None = None,
) -> WorktreeInfo:
    info = WorktreeInfo(
        unit.id,
        repo,
        path,
        "",
        "",
        "",
        run_root_identity=allocation.root_identity if allocation else None,
        run_parent_identity=allocation.parent_identity if allocation else None,
        run_private_identity=allocation.private_identity if allocation else None,
        repo_scoped_root=bool(allocation and allocation.repo_scoped),
    )
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
    allocation: _AllocatedRunRoot | None = None,
    run_git_func: RunGitFunc,
    current_branch_func: CurrentBranchFunc,
    head_sha_func: HeadShaFunc,
) -> tuple[str, str, bool, list[str]]:
    base = base_branch or current_branch_func(repo) or "HEAD"
    _validate_git_ref(base)
    base_sha = head_sha_func(repo, base)
    if not base_sha:
        raise RuntimeError(f"could not resolve base ref {base!r} to a commit")
    status = run_git_func(
        repo,
        _base_status_args(repo, allocation),
        timeout=30,
    )
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
    allocation: _AllocatedRunRoot | None = None,
    path_component: str | None = None,
) -> WorktreeInfo:
    branch = f"delegation/{unit.id}-{run_token[:12]}"
    path = run_root / (path_component or unit.id)
    info = WorktreeInfo(
        unit.id,
        repo,
        path,
        branch,
        base,
        base_sha,
        dirty_repo=dirty,
        warnings=list(warnings),
        run_root_identity=allocation.root_identity if allocation else None,
        run_parent_identity=allocation.parent_identity if allocation else None,
        run_private_identity=allocation.private_identity if allocation else None,
        repo_scoped_root=bool(allocation and allocation.repo_scoped),
    )
    if allocation and allocation.warning:
        info.warnings.append(allocation.warning)
    length_error = _windows_path_error(path)
    if length_error is not None:
        info.errors.append(length_error)
        return info
    if allocation is not None:
        try:
            _require_private_identity(allocation.private_identity)
            _require_directory_identity(
                allocation.parent_identity,
                label="delegation worktree parent",
            )
            _require_directory_identity(
                allocation.root_identity,
                label="delegation worktree root",
            )
        except PermissionError as exc:
            info.errors.append(str(exc))
            return info
    try:
        os.lstat(path)
    except FileNotFoundError:
        pass
    else:
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
            if allocation is None:
                info.created = True
            else:
                _require_private_identity(allocation.private_identity)
                _require_directory_identity(
                    allocation.parent_identity,
                    label="delegation worktree parent",
                )
                _require_directory_identity(
                    allocation.root_identity,
                    label="delegation worktree root",
                )
                info.worktree_identity = _capture_directory_identity(path)
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
    allocation: _AllocatedRunRoot | None = None,
) -> dict[str, WorktreeInfo]:
    try:
        base, base_sha, dirty, warnings = _inspect_repository_for_provisioning(
            repo,
            base_branch=base_branch,
            allocation=allocation,
            run_git_func=run_git_func,
            current_branch_func=current_branch_func,
            head_sha_func=head_sha_func,
        )
    except Exception as exc:
        error = f"could not inspect Git repository: {type(exc).__name__}: {exc}"
        return {
            unit.id: _unavailable_worktree(
                unit,
                repo,
                run_root / unit.id,
                error,
                allocation=allocation,
            )
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
            allocation=allocation,
            path_component=(
                _worktree_component(allocation, unit) if allocation is not None else None
            ),
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

    default_root = _absolute(Path.home() / ".agency-runtime" / "worktrees")
    lexical_root = _absolute(worktree_root)
    shared_allocation: _AllocatedRunRoot | None = None
    fallback_error: BaseException | None = None
    host_fallback_error: BaseException | None = None
    if lexical_root == default_root:
        try:
            shared_allocation = _allocate_private_run_root(private_runtime_directory("worktrees"))
        except (OSError, PermissionError) as exc:
            fallback_error = exc
            if _IS_WINDOWS:
                try:
                    shared_allocation = _allocate_host_run_root(fallback_error=exc)
                except (OSError, PermissionError, RuntimeError) as host_exc:
                    # A restricted Windows host must use an exact host-attested
                    # scratch root. Never fall through to an AU-writable repo.
                    host_fallback_error = host_exc
                    shared_allocation = None
    else:
        try:
            os.lstat(lexical_root)
        except FileNotFoundError:
            private_root = ensure_private_directory(
                lexical_root,
                product_owned=False,
            )
        else:
            private_root = validate_private_directory(lexical_root)
        shared_allocation = _allocate_private_run_root(private_root)

    for repo, repo_units in by_repo.items():
        allocation = shared_allocation
        if allocation is None:
            if fallback_error is None:
                raise RuntimeError("private worktree allocation returned no receipt")
            try:
                if _IS_WINDOWS:
                    raise PermissionError(
                        "an exact host-attested Windows worktree root is unavailable"
                        + (
                            "; host allocation failed with "
                            f"{type(host_fallback_error).__name__}: {host_fallback_error}"
                            if host_fallback_error is not None
                            else ""
                        )
                    )
                allocation = _allocate_repository_run_root(
                    repo,
                    fallback_error=fallback_error,
                )
            except (OSError, PermissionError, RuntimeError) as exc:
                error = (
                    "secure worktree storage is unavailable: private runtime root failed "
                    f"with {type(fallback_error).__name__}; secondary secure fallback "
                    f"failed with {type(exc).__name__}: {exc}"
                )
                worktrees.update(
                    {
                        unit.id: _unavailable_worktree(
                            unit,
                            repo,
                            repo / f"unavailable-{unit.id}",
                            error,
                        )
                        for unit in repo_units
                    }
                )
                continue
        worktrees.update(
            _provision_repository_worktrees(
                repo,
                repo_units,
                base_branch=base_branch,
                run_root=allocation.path,
                run_token=allocation.token,
                run_git_func=run_git_func,
                current_branch_func=current_branch_func,
                head_sha_func=head_sha_func,
                allocation=allocation,
            )
        )
    return worktrees


def _git_error(result: subprocess.CompletedProcess[str], fallback: str) -> str:
    return result.stderr.strip() or result.stdout.strip() or fallback


def _allocation_for_info(info: WorktreeInfo) -> _AllocatedRunRoot | None:
    if info.run_root_identity is None or info.run_parent_identity is None:
        return None
    return _AllocatedRunRoot(
        path=info.run_root_identity.path,
        token="",
        root_identity=info.run_root_identity,
        parent_identity=info.run_parent_identity,
        private_identity=info.run_private_identity,
        repo_scoped=info.repo_scoped_root,
    )


def _require_run_root_identity(info: WorktreeInfo) -> None:
    allocation = _allocation_for_info(info)
    if allocation is None:
        return
    _require_private_identity(allocation.private_identity)
    _require_directory_identity(
        allocation.parent_identity,
        label="delegation worktree parent",
    )
    _require_directory_identity(
        allocation.root_identity,
        label="delegation worktree root",
    )


def _require_worktree_info_identity(info: WorktreeInfo) -> None:
    _require_run_root_identity(info)
    if info.worktree_identity is not None:
        _require_directory_identity(
            info.worktree_identity,
            label="delegation worktree",
        )


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
    try:
        _require_worktree_info_identity(target)
    except PermissionError as exc:
        return str(exc)
    for predecessor_id in sorted(predecessor_ids):
        predecessor = worktrees.get(predecessor_id)
        if predecessor is None or not predecessor.created:
            continue
        if predecessor.repo_path.resolve() != target.repo_path.resolve():
            continue
        try:
            _require_worktree_info_identity(predecessor)
        except PermissionError as exc:
            return f"could not apply predecessor {predecessor_id!r}: {exc}"
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
    try:
        _require_worktree_info_identity(info)
    except PermissionError as exc:
        return str(exc)
    status = run_git_func(info.path, ["status", "--porcelain"], timeout=30)
    if status.returncode != 0:
        return _git_error(status, "could not inspect worktree changes")
    if not status.stdout.strip():
        return None
    try:
        _require_worktree_info_identity(info)
    except PermissionError as exc:
        return str(exc)
    staged = run_git_func(info.path, ["add", "--all"], timeout=60)
    if staged.returncode != 0:
        return _git_error(staged, "could not stage worker changes")
    try:
        _require_worktree_info_identity(info)
    except PermissionError as exc:
        return str(exc)
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
        _require_worktree_info_identity(info)
        current = current_branch_func(info.repo_path)
        current_head = head_sha_func(info.repo_path, "HEAD")
        status = run_git_func(
            info.repo_path,
            _base_status_args(info.repo_path, _allocation_for_info(info)),
            timeout=30,
        )
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
        _require_worktree_info_identity(info)
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
        _require_worktree_info_identity(info)
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
    try:
        _require_run_root_identity(info)
        os.lstat(info.path)
    except FileNotFoundError:
        pass
    except Exception as exc:
        record["errors"].append(
            f"worktree removal identity check failed: {type(exc).__name__}: {exc}"
        )
        _preserve_worktree(
            record,
            "worktree cleanup could not prove the exact path was removed",
        )
        return
    else:
        record["errors"].append("worktree remove reported success but the path still exists")
        _preserve_worktree(
            record,
            "worktree cleanup could not prove the exact path was removed",
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
    _remove_empty_run_roots(worktrees, cleanup)
    return cleanup


def _directory_is_empty(path: Path) -> bool:
    with os.scandir(path) as entries:
        return next(entries, None) is None


def _restore_quarantined_run_root(
    quarantine: WorktreePathIdentity,
    original: WorktreePathIdentity,
    parent: WorktreePathIdentity,
) -> None:
    _require_directory_identity(parent, label="delegation worktree parent")
    _require_directory_identity(quarantine, label="quarantined delegation worktree root")
    try:
        os.lstat(original.path)
    except FileNotFoundError:
        os.rename(quarantine.path, original.path)
    else:
        raise PermissionError("refusing to restore a replaced delegation worktree root")
    _require_directory_identity(original, label="restored delegation worktree root")


def _remove_empty_run_root(
    root: WorktreePathIdentity,
    parent: WorktreePathIdentity,
) -> bool:
    """Quarantine and remove one unchanged, empty run root."""

    _require_directory_identity(parent, label="delegation worktree parent")
    _require_directory_identity(root, label="delegation worktree root")
    if not _directory_is_empty(root.path):
        return False
    for _attempt in range(100):
        quarantine_path = parent.path / f".agency-cleanup-{secrets.token_hex(16)}"
        try:
            os.lstat(quarantine_path)
        except FileNotFoundError:
            pass
        else:
            continue
        try:
            os.rename(root.path, quarantine_path)
        except FileExistsError:
            continue
        break
    else:
        raise RuntimeError("could not allocate a delegation cleanup quarantine")

    quarantine = WorktreePathIdentity(
        quarantine_path,
        root.device,
        root.inode,
    )
    try:
        _require_directory_identity(parent, label="delegation worktree parent")
        _require_directory_identity(
            quarantine,
            label="quarantined delegation worktree root",
        )
        if not _directory_is_empty(quarantine.path):
            _restore_quarantined_run_root(quarantine, root, parent)
            return False
        os.rmdir(quarantine.path)
        try:
            os.lstat(root.path)
        except FileNotFoundError:
            pass
        else:
            raise PermissionError("delegation worktree root was replaced during quarantine cleanup")
    except BaseException as exc:
        try:
            if _directory_identity_is_current(quarantine):
                _restore_quarantined_run_root(quarantine, root, parent)
        except Exception as restore_error:
            add_exception_note(
                exc,
                f"delegation quarantine restore failed: {restore_error}",
            )
        raise
    return True


def _record_run_root_cleanup_error(
    run_path: Path,
    worktrees: Mapping[str, WorktreeInfo],
    cleanup: dict[str, CleanupRecord],
    error: BaseException,
) -> None:
    message = (
        "delegation run root was preserved because exact cleanup failed: "
        f"{type(error).__name__}: {error}"
    )
    for unit_id, info in worktrees.items():
        if info.run_root_identity is None or info.run_root_identity.path != run_path:
            continue
        record = cleanup.get(unit_id)
        if record is not None:
            record["errors"].append(message)


def _remove_empty_run_roots(
    worktrees: Mapping[str, WorktreeInfo],
    cleanup: dict[str, CleanupRecord] | None = None,
) -> None:
    """Remove only empty lifecycle-owned run directories after cleanup."""
    cleanup_records = cleanup or {}
    identities = {
        info.run_root_identity.path: (
            info.run_root_identity,
            info.run_parent_identity,
            info.run_private_identity,
        )
        for info in worktrees.values()
        if info.run_root_identity is not None and info.run_parent_identity is not None
    }
    for run_path, (root, parent, private_identity) in identities.items():
        try:
            if private_identity is not None:
                if _directory_is_empty(root.path):
                    remove_private_directory(private_identity)
            else:
                _remove_empty_run_root(root, parent)
        except (OSError, PermissionError, RuntimeError) as exc:
            _record_run_root_cleanup_error(
                run_path,
                worktrees,
                cleanup_records,
                exc,
            )

    legacy_candidates = {
        info.path.parent
        for info in worktrees.values()
        if info.run_root_identity is None
        and info.created
        and info.path.parent.name.startswith("run-")
    }
    for candidate in legacy_candidates:
        try:
            validate_private_directory(candidate)
            candidate.rmdir()
        except OSError:
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
