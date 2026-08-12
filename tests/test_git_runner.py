"""Branch coverage for the bounded Git runner.

Moved out of `test_delegation_coverage_complete_git.py` when Job B's worktree
provisioning was deleted. The worktree cases went with the code they covered;
these cover the hardened runner in `core/git_runner.py`, which survived because
`core/update_service.py` and work-unit normalization both use it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from agency_runtime.core import git_runner as lifecycle_git


def _completed(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


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


# `_git_error` was covered here too. It formatted failures from worktree
# operations and went with them; nothing in the runner produces that shape.
