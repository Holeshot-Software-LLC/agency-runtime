"""Check committed CI inputs for whitespace errors over an exact revision range."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
_COMMIT_SHA = re.compile(r"[0-9a-fA-F]{40}")
_ZERO_SHA = "0" * 40
_MAX_DIAGNOSTIC_BYTES = 1024 * 1024


def _commit_sha(value: str, *, name: str, allow_zero: bool = False) -> str:
    candidate = value.strip().lower()
    if not _COMMIT_SHA.fullmatch(candidate) or (candidate == _ZERO_SHA and not allow_zero):
        raise ValueError(f"{name} must be a full nonzero hexadecimal commit SHA")
    return candidate


def _require_commit(root: Path, commit: str) -> None:
    completed = subprocess.run(
        ("git", "cat-file", "-e", f"{commit}^{{commit}}"),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("whitespace range commit is unavailable")


def whitespace_comparison(
    *,
    event_name: str,
    head_sha: str,
    base_sha: str = "",
    before_sha: str = "",
    root: Path = ROOT,
) -> str:
    """Return the exact Git comparison whose committed payload must be clean."""

    resolved_root = root.resolve(strict=True)
    head = _commit_sha(head_sha, name="head SHA")
    _require_commit(resolved_root, head)
    if event_name == "pull_request":
        base = _commit_sha(base_sha, name="base SHA")
        _require_commit(resolved_root, base)
        return f"{base}...{head}"
    if event_name == "push":
        before = _commit_sha(before_sha, name="before SHA", allow_zero=True)
        if before == _ZERO_SHA:
            return f"{EMPTY_TREE_SHA}..{head}"
        _require_commit(resolved_root, before)
        return f"{before}..{head}"
    if event_name == "workflow_dispatch":
        return f"{EMPTY_TREE_SHA}..{head}"
    raise ValueError("unsupported CI event")


def check_whitespace(
    *,
    event_name: str,
    head_sha: str,
    base_sha: str = "",
    before_sha: str = "",
    root: Path = ROOT,
) -> bytes:
    """Return bounded ``git diff --check`` diagnostics for the governed range."""

    resolved_root = root.resolve(strict=True)
    comparison = whitespace_comparison(
        event_name=event_name,
        head_sha=head_sha,
        base_sha=base_sha,
        before_sha=before_sha,
        root=resolved_root,
    )
    completed = subprocess.run(
        ("git", "diff", "--check", comparison, "--"),
        cwd=resolved_root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if len(completed.stdout) > _MAX_DIAGNOSTIC_BYTES:
        raise RuntimeError("whitespace diagnostics exceeded their evidence bound")
    if completed.returncode == 0 and not completed.stdout:
        return b""
    if completed.returncode == 2 and completed.stdout and not completed.stderr:
        return completed.stdout
    raise RuntimeError("whitespace verification failed without a governed result")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--before-sha", default="")
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    diagnostics = check_whitespace(
        event_name=args.event,
        head_sha=args.head_sha,
        base_sha=args.base_sha,
        before_sha=args.before_sha,
        root=args.root,
    )
    if diagnostics:
        print("Committed whitespace check failed.", file=sys.stderr)
        return 1
    print("Committed whitespace check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
