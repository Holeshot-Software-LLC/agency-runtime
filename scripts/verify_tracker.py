#!/usr/bin/env python3
"""Compare roadmap front matter with same-repository GitHub tracker issues.

This is a read-only check. It requires an authenticated ``gh`` CLI session and
never creates, edits, closes, or labels an issue.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs" / "roadmap"


def _shared_history():
    """Load the gate-shared allow-list semantics by file path.

    Works identically whether this script runs as a file, a module, or is
    loaded by tests through importlib.
    """

    import importlib.util

    path = Path(__file__).resolve().with_name("roadmap_history.py")
    spec = importlib.util.spec_from_file_location("roadmap_history", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Trackers carry the historical "[AR-NNN] Title" style, the current
# "AR-NNN: Title" style (most filings since AR-337), or the hybrid
# "[AR-NNN]: Title"; all identify the issue. A bare "AR-NNN Title" with no
# separator is not an ID claim.
ID_RE = re.compile(r"^\[?(AR-\d{2,})(?:\]:?|:)\s+.+")


def gh(*args: str) -> object:
    result = subprocess.run(
        ["gh", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def front_matter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path.relative_to(ROOT)} has no front matter")
    closing = lines.index("---", 1)
    value = yaml.safe_load("\n".join(lines[1:closing])) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} front matter is not a mapping")
    return value


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare roadmap front matter with same-repository GitHub issues."
    )
    parser.add_argument(
        "--allow-open-complete",
        action="store_true",
        help=(
            "Warn instead of failing when a locally done/wont_do item remains "
            "open; all identity, URL, label, count, and other state checks stay strict."
        ),
    )
    return parser.parse_args(argv)


def _remote_issue_objects(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise RuntimeError("tracker issue listing did not return a JSON array")
    issues: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise RuntimeError("tracker issue listing contains a non-object item")
        issues.append(item)
    return issues


def _local_issue_metadata(
    errors: list[str],
    pr_tracked_history: frozenset[str],
) -> tuple[dict[str, dict[str, object]], set[str]]:
    """Collect all roadmap metadata plus the PR-tracked historical IDs.

    Every doc lands in the returned mapping so duplicate-ID detection sees
    the complete set. Only the closed historical set may carry a pull-request
    tracker_url; those IDs are returned separately so the caller can exclude
    them from issue-parity joins (`gh issue list` can never match them).
    """

    local: dict[str, dict[str, object]] = {}
    seen: set[str] = set()
    pr_tracked: set[str] = set()
    for path in sorted(ROADMAP.glob("issue-*.md")):
        meta = front_matter(path)
        issue_id = str(meta.get("issue_id", ""))
        if issue_id in seen:
            errors.append(f"duplicate local issue ID {issue_id}")
        seen.add(issue_id)
        if "/pull/" in str(meta.get("tracker_url") or ""):
            if issue_id in pr_tracked_history:
                pr_tracked.add(issue_id)
            else:
                errors.append(
                    f"{issue_id}: tracker_url must reference an issue, not a pull request"
                )
        local[issue_id] = meta
    return local, pr_tracked


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    history = _shared_history()
    errors: list[str] = []
    warnings: list[str] = []
    local, pr_tracked = _local_issue_metadata(errors, history.PR_TRACKED_HISTORY)
    exemptions = history.load_pre_tracker_history(ROADMAP)
    errors.extend(
        history.pre_tracker_entry_errors(
            exemptions,
            set(local),
            {issue_id: meta.get("tracker_url") for issue_id, meta in local.items()},
        )
    )

    remote_items = _remote_issue_objects(
        gh(
            "issue",
            "list",
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            "number,title,state,url,labels",
        )
    )
    remote: dict[str, dict[str, object]] = {}
    for item in remote_items:
        match = ID_RE.match(str(item.get("title", "")))
        if not match:
            continue
        issue_id = match.group(1)
        if issue_id in remote:
            errors.append(f"tracker has duplicate issues for {issue_id}")
        remote[issue_id] = item

    missing_remote = sorted(set(local) - set(remote) - exemptions - pr_tracked)
    missing_local = sorted(set(remote) - set(local))
    if missing_remote or missing_local:
        errors.append(
            "roadmap/tracker ID mismatch: "
            f"missing_remote={missing_remote}, "
            f"missing_local={missing_local}"
        )

    for issue_id in sorted((set(local) - pr_tracked) & set(remote)):
        meta = local[issue_id]
        item = remote[issue_id]
        if meta.get("tracker_url") != item.get("url"):
            errors.append(f"{issue_id}: tracker_url does not match issue URL")
        expected_label = f"epic:{meta.get('epic')}"
        labels = {
            str(label.get("name")) for label in item.get("labels", []) if isinstance(label, dict)
        }
        if expected_label not in labels:
            errors.append(f"{issue_id}: missing tracker label {expected_label}")
        expected_state = "CLOSED" if meta.get("status") in {"done", "wont_do"} else "OPEN"
        if item.get("state") != expected_state:
            allow_open_complete = (
                args.allow_open_complete
                and expected_state == "CLOSED"
                and item.get("state") == "OPEN"
            )
            message = f"{issue_id}: tracker state {item.get('state')} != {expected_state}"
            if allow_open_complete:
                warnings.append(f"{message} (closure pending authorization)")
            else:
                errors.append(message)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    suffix = f" ({len(warnings)} open complete item(s) allowed)" if warnings else ""
    if pr_tracked:
        suffix += f" ({len(pr_tracked)} PR-tracked historical item(s) skipped)"
    print(f"tracker validation passed for {len(local) - len(pr_tracked)} roadmap items{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
