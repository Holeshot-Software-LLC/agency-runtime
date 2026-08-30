"""One bounded, non-interactive Git runner with hostile configuration disabled.

Extracted from `core/delegation/lifecycle_git.py` when the Job B worktree
provisioning around it was deleted. The Git plumbing was never delegation
machinery -- it is a hardened `subprocess` wrapper that happened to live next to
a worker pool. `core/update_service.py` uses `run_git`, and work-unit
normalization uses `git_root`.

The hardening is the reason this is one function and not a `subprocess.run` call
at each site: system and global config are neutered, credential and editor
prompts cannot open, hooks and external diff/merge drivers cannot execute, and
per-command `-c` overrides are checked against a closed allowlist. A repository
is untrusted input; running Git in one is running whatever its config says.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)
from agency_runtime.core.process_argv import (
    repository_forbidden_roots,
    resolve_executable_path,
    sanitized_executable_search_path,
)

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


__all__ = [
    "RunGitFunc",
    "current_branch",
    "git_root",
    "head_sha",
    "run_git",
]
