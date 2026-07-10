#!/usr/bin/env python3
"""Add conservative YAML front matter to repository Markdown documents.

The writer is intentionally idempotent: a file whose first line is ``---`` is
never changed. Existing-file dates come from ``git log --follow``; untracked
files use the current date. Run ``python scripts/docs_metadata.py --check`` to
list documents that still need metadata without modifying them.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def markdown_files() -> list[Path]:
    output = git(
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        "*.md",
    )
    return sorted(ROOT / line for line in output.splitlines() if line.strip())


def history_dates(path: Path) -> tuple[str, str]:
    relative = path.relative_to(ROOT).as_posix()
    output = git("log", "--follow", "--reverse", "--format=%aI", "--", relative)
    values = [line[:10] for line in output.splitlines() if line]
    if not values:
        today = date.today().isoformat()
        return today, today
    return values[0], values[-1]


def document_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def classification(path: Path) -> tuple[str, str]:
    relative = path.relative_to(ROOT).as_posix()
    if relative == "README.md":
        return "overview", "active"
    if relative == "AGENTS.md":
        return "governance", "active"
    if relative.startswith("docs/roadmap/"):
        status = "open" if path.name.startswith("issue-") else "active"
        return "roadmap", status
    if relative.startswith("docs/worklog/"):
        return "worklog", "draft" if path.name == "TEMPLATE.md" else "active"
    if relative.startswith("docs/decisions/"):
        status = "proposed" if re.match(r"\d{4}-", path.name) else "active"
        return "decisions", status
    return "documentation", "active"


def variant_fields(path: Path) -> list[str]:
    relative = path.relative_to(ROOT).as_posix()
    issue = re.fullmatch(r"docs/roadmap/issue-(AR-\d+)-(.+)\.md", relative)
    if issue:
        return [
            "type: issue",
            "epic: unassigned",
            f"issue_id: {issue.group(1)}",
            "priority: p2",
            "tracker_url: null",
            "depends_on: []",
            "blocks: []",
        ]
    decision = re.fullmatch(r"docs/decisions/(\d{4})-(.+)\.md", relative)
    if decision:
        return [
            f"id: ADR-{decision.group(1)}",
            "type: decision",
            "deciders: []",
        ]
    if relative.startswith("docs/worklog/") and path.name not in {"README.md", "TEMPLATE.md"}:
        match = re.match(r"(\d{4}-\d{2}-\d{2})-([0-9a-f]{7,40})-", path.name)
        commit = match.group(2) if match else "unresolved"
        commit_date = match.group(1) if match else date.today().isoformat()
        return [
            "type: worklog",
            f"commit: {commit}",
            f"short: {commit[:7]}",
            f"date: {commit_date}",
            "pr: null",
            "related_issues: []",
        ]
    return []


def front_matter(path: Path, text: str) -> str:
    created, updated = history_dates(path)
    category, status = classification(path)
    fields = [
        "---",
        f"title: {yaml_string(document_title(text, path))}",
        f"status: {status}",
        f"category: {category}",
        f"created: {created}",
        f"updated: {updated}",
        "tags: []",
        "related: []",
        "supersedes: []",
        "superseded_by: null",
        *variant_fields(path),
        "---",
        "",
    ]
    return "\n".join(fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report files without front matter and make no changes",
    )
    args = parser.parse_args()

    missing: list[Path] = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        if text.startswith("---\n") or text.startswith("---\r\n"):
            continue
        missing.append(path)
        if not args.check:
            path.write_text(front_matter(path, text) + text, encoding="utf-8")

    verb = "need" if args.check else "received"
    for path in missing:
        print(f"{path.relative_to(ROOT).as_posix()} {verb} front matter")
    if args.check and missing:
        return 1
    print(f"checked {len(markdown_files())} Markdown documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
