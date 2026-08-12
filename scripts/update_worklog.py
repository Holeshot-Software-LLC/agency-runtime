#!/usr/bin/env python3
"""Idempotently rebuild the tracked Git commit table in the worklog registry."""

from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

if __package__:
    from .worklog_history import stable_short_shas
else:
    from worklog_history import stable_short_shas

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "worklog" / "README.md"
START = "<!-- worklog:start -->"
END = "<!-- worklog:end -->"
LEDGER_PREFIX = "docs(worklog):"
ROW_RE = re.compile(
    r"^\| `(?P<sha>[0-9a-f]{8})` \| .*? \| (?P<issue>[^|]+?) \| "
    r"(?P<detail>[^|]+?) \|$"
)


def git_log() -> list[tuple[str, str, str]]:
    result = subprocess.run(
        [
            "git",
            "log",
            "--reverse",
            "--date=short",
            "--format=%H%x1f%ad%x1f%s",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    history: list[tuple[str, str, str]] = []
    for line in result.stdout.splitlines():
        full_sha, commit_date, subject = line.split("\x1f", 2)
        if subject.startswith(LEDGER_PREFIX):
            continue
        history.append((full_sha, commit_date, subject))
    shortened = stable_short_shas(item[0] for item in history)
    return [
        (short, commit_date, subject)
        for short, (_, commit_date, subject) in zip(shortened, history, strict=True)
    ]


def existing_annotations(text: str) -> dict[str, tuple[str, str]]:
    annotations: dict[str, tuple[str, str]] = {}
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if match:
            annotations[match.group("sha")] = (
                match.group("issue").strip(),
                match.group("detail").strip(),
            )
    return annotations


def generated_table(text: str) -> str:
    annotations = existing_annotations(text)
    lines = [
        START,
        "| Short SHA | Date | Subject | Related issue | Detail |",
        "|---|---|---|---|---|",
    ]
    for short, commit_date, raw_subject in git_log():
        related, detail = annotations.get(short, ("null", "null"))
        subject = raw_subject.replace("|", "\\|")
        lines.append(f"| `{short}` | {commit_date} | {subject} | {related} | {detail} |")
    lines.append(END)
    return "\n".join(lines)


def rebuilt(text: str) -> str:
    if START not in text or END not in text:
        raise ValueError(f"{REGISTRY.relative_to(ROOT)} is missing worklog markers")
    prefix, remainder = text.split(START, 1)
    _, suffix = remainder.split(END, 1)
    result = prefix + generated_table(text) + suffix
    if result != text:
        result = re.sub(
            r"(?m)^updated:\s+\d{4}-\d{2}-\d{2}$",
            f"updated: {date.today().isoformat()}",
            result,
            count=1,
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="make no changes")
    args = parser.parse_args()
    original = REGISTRY.read_text(encoding="utf-8")
    updated = rebuilt(original)
    if args.check:
        if updated != original:
            print("worklog index is stale")
            return 1
        print(f"worklog index is current ({len(git_log())} commits)")
        return 0
    if updated != original:
        REGISTRY.write_text(updated, encoding="utf-8")
        print(f"updated worklog index ({len(git_log())} commits)")
    else:
        print(f"worklog index already current ({len(git_log())} commits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
