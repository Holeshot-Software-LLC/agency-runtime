"""Classify whether a CI event requires code and release verification.

Only pull requests whose complete base-to-head delta consists of Markdown
documents under ``docs/`` may use the documentation-only lane.  Every error,
empty delta, unsupported event, and non-documentation path fails closed into
the full verification lane.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
_COMMIT_SHA = re.compile(r"[0-9a-fA-F]{40}")
_FULL_EVENTS = frozenset({"push", "workflow_dispatch"})
_REGULAR_MARKDOWN_MODES = frozenset({"000000", "100644"})
_MAX_DIFF_BYTES = 1024 * 1024


def _commit_sha(value: str, *, name: str) -> str:
    candidate = value.strip()
    if not _COMMIT_SHA.fullmatch(candidate):
        raise ValueError(f"{name} must be a full hexadecimal commit SHA")
    return candidate.lower()


def _git_status(
    *arguments: str,
    root: Path,
    accepted: frozenset[int],
) -> int:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if completed.returncode not in accepted:
        raise RuntimeError("Git change classification failed without a governed result")
    return completed.returncode


def _require_commit(root: Path, commit: str) -> None:
    _git_status(
        "cat-file",
        "-e",
        f"{commit}^{{commit}}",
        root=root,
        accepted=frozenset({0}),
    )


def _changed_entries(root: Path, comparison: str) -> tuple[tuple[str, str, str], ...]:
    completed = subprocess.run(
        (
            "git",
            "diff",
            "--raw",
            "-z",
            "--no-abbrev",
            "--no-renames",
            comparison,
            "--",
        ),
        cwd=root,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError("Git change classification failed without a governed result")
    if len(completed.stdout) > _MAX_DIFF_BYTES:
        raise RuntimeError("Git change classification exceeded its evidence bound")

    records = completed.stdout.split(b"\0")
    if records and not records[-1]:
        records.pop()
    if len(records) % 2:
        raise RuntimeError("Git change classification returned malformed raw records")

    entries: list[tuple[str, str, str]] = []
    for offset in range(0, len(records), 2):
        header = records[offset].split()
        if (
            len(header) != 5
            or not header[0].startswith(b":")
            or header[4] not in {b"A", b"D", b"M"}
        ):
            raise RuntimeError("Git change classification returned an unsupported record")
        try:
            path = records[offset + 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError("Git change path is not valid UTF-8") from exc
        entries.append(
            (
                header[0].removeprefix(b":").decode("ascii"),
                header[1].decode("ascii"),
                path,
            )
        )
    return tuple(entries)


def _is_regular_docs_markdown(old_mode: str, new_mode: str, path: str) -> bool:
    candidate = PurePosixPath(path)
    valid_path = bool(
        not candidate.is_absolute()
        and len(candidate.parts) >= 2
        and candidate.parts[0] == "docs"
        and all(part not in {"", ".", ".."} for part in candidate.parts)
        and candidate.suffix == ".md"
    )
    valid_modes = bool(
        old_mode in _REGULAR_MARKDOWN_MODES
        and new_mode in _REGULAR_MARKDOWN_MODES
        and (old_mode != "000000" or new_mode != "000000")
    )
    return valid_path and valid_modes


def classify_change(
    *,
    event_name: str,
    base_sha: str = "",
    head_sha: str = "",
    root: Path = ROOT,
) -> tuple[bool, str]:
    """Return ``(code_required, reason)`` for one checked-out workflow event."""

    if event_name in _FULL_EVENTS:
        return True, "event_requires_full_verification"
    if event_name != "pull_request":
        raise ValueError("unsupported CI event")

    base = _commit_sha(base_sha, name="base SHA")
    head = _commit_sha(head_sha, name="head SHA")
    resolved_root = root.resolve(strict=True)
    _require_commit(resolved_root, base)
    _require_commit(resolved_root, head)

    entries = _changed_entries(resolved_root, f"{base}...{head}")
    if not entries:
        return True, "empty_delta_requires_full_verification"
    if all(_is_regular_docs_markdown(*entry) for entry in entries):
        return False, "docs_markdown_only"
    return True, "code_or_governance_change"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--head-sha", default="")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    code_required, reason = classify_change(
        event_name=args.event,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        root=args.root,
    )
    output = args.output
    if output is None:
        raw_output = os.environ.get("GITHUB_OUTPUT", "")
        if not raw_output:
            raise RuntimeError("GITHUB_OUTPUT is required")
        output = Path(raw_output)
    with output.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"code_required={str(code_required).lower()}\n")
        stream.write(f"scope_reason={reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
