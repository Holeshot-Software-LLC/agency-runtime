#!/usr/bin/env python3
"""Validate documentation metadata, indexes, links, and repository boundaries."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
CORE_FIELDS = {
    "title",
    "status",
    "category",
    "created",
    "updated",
    "tags",
    "related",
    "supersedes",
    "superseded_by",
}
GENERAL_STATUSES = {"active", "draft", "retired"}
ISSUE_STATUSES = {"open", "in_progress", "blocked", "done", "wont_do"}
DECISION_STATUSES = {
    "proposed",
    "accepted",
    "superseded",
    "deprecated",
    "rejected",
}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
GITHUB_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s)#\"']+)", re.I)
WORKLOG_LEDGER_PREFIX = "docs(worklog):"
# Two ledger commits predate enforcement of the narrow worklog exemption and
# also touched one unrelated doc each. Both are recorded in the Notes section of
# `docs/worklog/README.md`, which states the resolution explicitly: "Retained
# as-is; no history rewrite." Rewriting published history to satisfy a linter
# would be the more destructive fix, so they are grandfathered by exact full
# SHA. Do not add to this set -- a new violation means the commit should be
# split before it lands.
GRANDFATHERED_LEDGER_COMMITS = frozenset(
    {
        "0e9410b3e818680d507a639e4b5cf7bef8bce41f",
        "a1835947d15e089e235081630b5cc070bd7ecff3",
    }
)
LEGAL_PROVENANCE_NAME_EXEMPTIONS = frozenset({"THIRD_PARTY_NOTICES.md"})
HANDOFF_MAX_BYTES = 12 * 1024
HANDOFF_MAX_LINES = 180
HANDOFF_HARD_CHECKPOINT_PERCENT = 50
HANDOFF_REQUIRED_HEADINGS = frozenset(
    {
        "checkpoint",
        "completed-evidence",
        "exact-blocker",
        "same-task-continuity",
        "next-bounded-work-package",
        "verification",
        "constraints",
    }
)


@dataclass
class Document:
    path: Path
    meta: dict[str, object]
    body: str

    @property
    def relative(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


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


def parse_document(path: Path, errors: list[str]) -> Document | None:
    text = path.read_text(encoding="utf-8")
    relative = path.relative_to(ROOT).as_posix()
    if not (text.startswith("---\n") or text.startswith("---\r\n")):
        errors.append(f"{relative}: missing YAML front matter")
        return None
    lines = text.splitlines()
    try:
        closing = lines.index("---", 1)
    except ValueError:
        errors.append(f"{relative}: front matter has no closing delimiter")
        return None
    try:
        meta = yaml.safe_load("\n".join(lines[1:closing])) or {}
    except yaml.YAMLError as exc:
        errors.append(f"{relative}: invalid YAML: {exc}")
        return None
    if not isinstance(meta, dict):
        errors.append(f"{relative}: front matter must be a mapping")
        return None
    return Document(path=path, meta=meta, body="\n".join(lines[closing + 1 :]))


def is_date(value: object) -> bool:
    if isinstance(value, date):
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and is_date(value):
        return date.fromisoformat(value)
    return None


def _missing_field_errors(doc: Document, names: set[str]) -> list[str]:
    return [
        f"{doc.relative}: missing front-matter field {name!r}"
        for name in sorted(names - set(doc.meta))
    ]


def _common_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(doc, CORE_FIELDS)
    meta = doc.meta
    if not isinstance(meta.get("title"), str) or not meta.get("title"):
        errors.append(f"{doc.relative}: title must be a non-empty string")
    if not isinstance(meta.get("category"), str) or not meta.get("category"):
        errors.append(f"{doc.relative}: category must be a non-empty string")
    for field in ("created", "updated"):
        if not is_date(meta.get(field)):
            errors.append(f"{doc.relative}: {field} must be YYYY-MM-DD")
    created = as_date(meta.get("created"))
    updated = as_date(meta.get("updated"))
    if created and updated and updated < created:
        errors.append(f"{doc.relative}: updated precedes created")
    for field in ("tags", "related", "supersedes"):
        if not isinstance(meta.get(field), list):
            errors.append(f"{doc.relative}: {field} must be a list")
    if meta.get("superseded_by") is not None and not isinstance(meta.get("superseded_by"), str):
        errors.append(f"{doc.relative}: superseded_by must be a string or null")
    return errors


def _issue_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(
        doc,
        {
            "type",
            "epic",
            "issue_id",
            "priority",
            "tracker_url",
            "depends_on",
            "blocks",
        },
    )
    meta = doc.meta
    status = meta.get("status")
    if status not in ISSUE_STATUSES:
        errors.append(f"{doc.relative}: invalid issue status {status!r}")
    if not re.fullmatch(r"AR-\d{2,}", str(meta.get("issue_id", ""))):
        errors.append(f"{doc.relative}: issue_id must match AR-NN")
    if meta.get("priority") not in {"p0", "p1", "p2", "p3"}:
        errors.append(f"{doc.relative}: priority must be p0, p1, p2, or p3")
    for field in ("depends_on", "blocks"):
        if not isinstance(meta.get(field), list):
            errors.append(f"{doc.relative}: {field} must be a list")
    return errors


def _worklog_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(
        doc,
        {"type", "commit", "short", "date", "pr", "related_issues"},
    )
    meta = doc.meta
    status = meta.get("status")
    if status not in GENERAL_STATUSES:
        errors.append(f"{doc.relative}: invalid worklog status {status!r}")
    if not isinstance(meta.get("related_issues"), list):
        errors.append(f"{doc.relative}: related_issues must be a list")
    return errors


def _decision_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(doc, {"id", "type", "deciders"})
    meta = doc.meta
    status = meta.get("status")
    if status not in DECISION_STATUSES:
        errors.append(f"{doc.relative}: invalid decision status {status!r}")
    if not re.fullmatch(r"ADR-\d{4}", str(meta.get("id", ""))):
        errors.append(f"{doc.relative}: decision id must match ADR-NNNN")
    if not isinstance(meta.get("deciders"), list):
        errors.append(f"{doc.relative}: deciders must be a list")
    return errors


def _handoff_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(
        doc,
        {
            "issue_id",
            "branch",
            "evidence_commit",
            "hard_checkpoint_percent",
            "minimum_ledger_commit",
            "tracker_url",
        },
    )
    meta = doc.meta
    issue_id = str(meta.get("issue_id", ""))
    if meta.get("status") != "active":
        errors.append(f"{doc.relative}: active handoff status must be 'active'")
    if not re.fullmatch(r"AR-\d{2,}", issue_id):
        errors.append(f"{doc.relative}: handoff issue_id must match AR-NN")
    branch = meta.get("branch")
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        errors.append(f"{doc.relative}: branch must be a non-empty Git ref name")
    for field in ("evidence_commit", "minimum_ledger_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(meta.get(field, ""))):
            errors.append(f"{doc.relative}: {field} must be a full lowercase Git SHA")
    tracker_url = meta.get("tracker_url")
    if tracker_url is not None and not isinstance(tracker_url, str):
        errors.append(f"{doc.relative}: tracker_url must be a string or null")
    hard_checkpoint = meta.get("hard_checkpoint_percent")
    if isinstance(hard_checkpoint, bool) or hard_checkpoint != HANDOFF_HARD_CHECKPOINT_PERCENT:
        errors.append(
            f"{doc.relative}: hard_checkpoint_percent must be {HANDOFF_HARD_CHECKPOINT_PERCENT}"
        )
    if "live_evaluation_admission_percent" in meta:
        errors.append(
            f"{doc.relative}: live_evaluation_admission_percent was removed; "
            "only hard_checkpoint_percent is allowed"
        )
    return errors


def _variant_schema_errors(doc: Document) -> list[str]:
    doc_type = doc.meta.get("type")
    if doc_type == "issue":
        return _issue_schema_errors(doc)
    if doc_type == "worklog":
        return _worklog_schema_errors(doc)
    if doc_type == "decision":
        return _decision_schema_errors(doc)
    if doc_type == "handoff":
        return _handoff_schema_errors(doc)
    status = doc.meta.get("status")
    if status not in GENERAL_STATUSES:
        return [f"{doc.relative}: invalid general-document status {status!r}"]
    return []


def _retired_schema_errors(doc: Document) -> list[str]:
    errors = _missing_field_errors(doc, {"retired", "retired_reason"})
    meta = doc.meta
    if "/archive/" not in f"/{doc.relative}":
        errors.append(f"{doc.relative}: retired document must live in category archive/")
    if not is_date(meta.get("retired")):
        errors.append(f"{doc.relative}: retired must be YYYY-MM-DD")
    if not meta.get("superseded_by"):
        errors.append(f"{doc.relative}: retired document needs superseded_by")
    return errors


def validate_schema(doc: Document, errors: list[str]) -> None:
    errors.extend(_common_schema_errors(doc))
    errors.extend(_variant_schema_errors(doc))
    if doc.meta.get("status") == "retired":
        errors.extend(_retired_schema_errors(doc))


def validate_metadata_references(doc: Document, errors: list[str]) -> None:
    values: list[tuple[str, object]] = []
    for field in ("related", "supersedes"):
        values.extend((field, value) for value in doc.meta.get(field, []))
    if doc.meta.get("superseded_by"):
        values.append(("superseded_by", doc.meta["superseded_by"]))

    for field, value in values:
        if not isinstance(value, str) or not value:
            errors.append(f"{doc.relative}: {field} entries must be non-empty strings")
            continue
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            if not re.fullmatch(
                r"https://github\.com/Holeshot-Software-LLC/agency-runtime(?:/.*)?",
                value,
                re.I,
            ):
                errors.append(
                    f"{doc.relative}: {field} URL must belong to this repository: {value}"
                )
            continue
        if parsed.scheme:
            errors.append(f"{doc.relative}: unsupported {field} reference {value!r}")
            continue
        destination = (ROOT / value.split("#", 1)[0]).resolve()
        try:
            destination.relative_to(ROOT)
        except ValueError:
            errors.append(f"{doc.relative}: {field} reference escapes repository: {value}")
            continue
        if not destination.exists():
            errors.append(f"{doc.relative}: dangling {field} reference: {value}")


def github_slug(text: str) -> str:
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


def headings(body: str) -> set[str]:
    result: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = github_slug(match.group(1))
        count = counts.get(base, 0)
        counts[base] = count + 1
        result.add(base if count == 0 else f"{base}-{count}")
    return result


def validate_link(doc: Document, raw_target: str, errors: list[str]) -> None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split(maxsplit=1)[0]
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https", "mailto"}:
        return
    if parsed.scheme or target.startswith("//"):
        errors.append(f"{doc.relative}: unsupported link target {raw_target!r}")
        return
    path_part, _, fragment = target.partition("#")
    destination = doc.path if not path_part else (doc.path.parent / unquote(path_part)).resolve()
    try:
        destination.relative_to(ROOT)
    except ValueError:
        errors.append(f"{doc.relative}: link escapes repository: {raw_target!r}")
        return
    if not destination.exists():
        errors.append(f"{doc.relative}: dangling link {raw_target!r}")
        return
    if fragment and destination.suffix.lower() == ".md":
        target_text = destination.read_text(encoding="utf-8")
        target_doc = parse_document(destination, [])
        target_body = target_doc.body if target_doc else target_text
        if unquote(fragment).lower() not in headings(target_body):
            errors.append(f"{doc.relative}: missing anchor in {raw_target!r}")


def validate_links_and_boundaries(doc: Document, errors: list[str]) -> None:
    full_text = doc.path.read_text(encoding="utf-8")
    for raw_target in LINK_RE.findall(doc.body):
        validate_link(doc, raw_target, errors)

    for owner, repository in GITHUB_RE.findall(full_text):
        repo = repository.rstrip(".,;:").removesuffix(".git").lower()
        if (owner.lower(), repo) != ("holeshot-software-llc", "agency-runtime"):
            errors.append(
                f"{doc.relative}: cross-repository GitHub URL is not allowed ({owner}/{repository})"
            )
    forbidden = {
        "legacy sibling repository name": re.compile(r"agency-agents", re.I),
        "legacy sibling owner": re.compile(r"msitarzewski", re.I),
        "placeholder absolute path": re.compile(r"/path/to/", re.I),
        "file URI": re.compile(r"file://", re.I),
        "Windows absolute path": re.compile(r"(?<![\w-])[A-Za-z]:\\\\"),
    }
    for label, pattern in forbidden.items():
        if label.startswith("legacy sibling") and doc.relative in LEGAL_PROVENANCE_NAME_EXEMPTIONS:
            continue
        if pattern.search(full_text):
            errors.append(f"{doc.relative}: contains {label}")


def validate_roadmap(docs: list[Document], require_tracker: bool, errors: list[str]) -> None:
    registry = next((doc for doc in docs if doc.relative == "docs/roadmap/README.md"), None)
    issues = [doc for doc in docs if doc.meta.get("type") == "issue"]
    if not registry:
        errors.append("docs/roadmap/README.md: missing roadmap registry")
        return
    ids = [str(doc.meta.get("issue_id")) for doc in issues]
    if len(ids) != len(set(ids)):
        errors.append("docs/roadmap: duplicate issue_id values")
    registry_ids = set(re.findall(r"\bAR-\d{2,}\b", registry.body))
    if set(ids) != registry_ids:
        errors.append(
            "docs/roadmap/README.md: registry IDs do not match issue files "
            f"(registry={sorted(registry_ids)}, files={sorted(set(ids))})"
        )
    tracker_urls = [doc.meta.get("tracker_url") for doc in issues]
    present_urls = [url for url in tracker_urls if url]
    if len(present_urls) != len(set(present_urls)):
        errors.append("docs/roadmap: tracker URLs must be unique")
    if require_tracker:
        missing = [ids[index] for index, value in enumerate(tracker_urls) if not value]
        if missing:
            errors.append(f"docs/roadmap: items missing tracker URLs: {', '.join(missing)}")

    by_id = {str(doc.meta.get("issue_id")): doc for doc in issues}
    for issue_id, doc in by_id.items():
        for dependency in doc.meta.get("depends_on", []):
            if dependency not in by_id:
                errors.append(f"{doc.relative}: unknown depends_on ID {dependency!r}")
            elif issue_id not in by_id[dependency].meta.get("blocks", []):
                errors.append(
                    f"{doc.relative}: {dependency} does not reciprocate blocks={issue_id}"
                )
        for blocked in doc.meta.get("blocks", []):
            if blocked not in by_id:
                errors.append(f"{doc.relative}: unknown blocks ID {blocked!r}")
            elif issue_id not in by_id[blocked].meta.get("depends_on", []):
                errors.append(
                    f"{doc.relative}: {blocked} does not reciprocate depends_on={issue_id}"
                )


def validate_handoffs(docs: list[Document], errors: list[str]) -> None:
    handoffs = [doc for doc in docs if doc.meta.get("type") == "handoff"]
    issues = {str(doc.meta.get("issue_id")): doc for doc in docs if doc.meta.get("type") == "issue"}
    issue_capsules: dict[str, list[Document]] = {}
    for doc in handoffs:
        issue_id = str(doc.meta.get("issue_id", ""))
        issue_capsules.setdefault(issue_id, []).append(doc)

        expected_prefix = f"docs/roadmap/handoffs/issue-{issue_id}"
        if not (
            doc.relative == f"{expected_prefix}.md"
            or doc.relative.startswith(f"{expected_prefix}-")
        ):
            errors.append(
                f"{doc.relative}: active handoff filename must start with issue-{issue_id}"
            )
        try:
            byte_count = len(doc.path.read_bytes())
        except OSError as error:
            errors.append(f"{doc.relative}: cannot read handoff bytes: {error}")
            byte_count = 0
        if byte_count > HANDOFF_MAX_BYTES:
            errors.append(
                f"{doc.relative}: active handoff is {byte_count} bytes; "
                f"maximum is {HANDOFF_MAX_BYTES}"
            )
        line_count = len(doc.path.read_text(encoding="utf-8").splitlines())
        if line_count > HANDOFF_MAX_LINES:
            errors.append(
                f"{doc.relative}: active handoff is {line_count} lines; "
                f"maximum is {HANDOFF_MAX_LINES}"
            )
        missing_headings = sorted(HANDOFF_REQUIRED_HEADINGS - headings(doc.body))
        if missing_headings:
            errors.append(
                f"{doc.relative}: missing handoff sections: " + ", ".join(missing_headings)
            )

        issue = issues.get(issue_id)
        if issue is None:
            errors.append(f"{doc.relative}: unknown handoff issue_id {issue_id!r}")
            continue
        if issue.relative not in doc.meta.get("related", []):
            errors.append(f"{doc.relative}: related must include canonical issue {issue.relative}")
        if doc.meta.get("tracker_url") != issue.meta.get("tracker_url"):
            errors.append(f"{doc.relative}: tracker_url must match {issue.relative}")

    for issue_id, matches in sorted(issue_capsules.items()):
        if issue_id and len(matches) > 1:
            errors.append(f"docs/roadmap/handoffs: multiple active capsules for {issue_id}")


def validate_worklog(docs: list[Document], errors: list[str]) -> None:
    registry = next((doc for doc in docs if doc.relative == "docs/worklog/README.md"), None)
    if not registry:
        errors.append("docs/worklog/README.md: missing worklog registry")
        return
    output = git("log", "--reverse", "--date=short", "--format=%h%x09%ad%x09%s")
    expected: dict[str, tuple[str, str]] = {}
    for line in output.splitlines():
        short, commit_date, subject = line.split("\t", 2)
        if subject.startswith(WORKLOG_LEDGER_PREFIX):
            continue
        expected[short] = (commit_date, subject)
    # Read the commit index rows, not the whole body. The previous pattern
    # demanded exactly seven hex characters, but `git log --format=%h`
    # auto-widens the abbreviation as history grows and now yields eight here.
    # The effect was total: every table row became "missing" while the only
    # matches were the deliberately seven-character SHAs in the Notes prose,
    # which then reported as "extra". `update_worklog.py` writes `%h` and was
    # reporting the index current at the same moment -- the two scripts
    # disagreeing about one file. Anchoring to the row shape keeps this
    # independent of abbreviation width and immune to prose.
    found = {
        match
        for line in registry.body.splitlines()
        if line.lstrip().startswith("|")
        for match in re.findall(r"`([0-9a-f]{7,40})`", line)
    }
    if set(expected) != found:
        errors.append(
            "docs/worklog/README.md: indexed commits do not match history "
            f"(missing={sorted(set(expected) - found)}, extra={sorted(found - set(expected))})"
        )
    for short, (commit_date, subject) in expected.items():
        row = next((line for line in registry.body.splitlines() if short in line), "")
        if commit_date not in row or subject not in row:
            errors.append(f"docs/worklog/README.md: inaccurate row for {short}")

    ledger_output = git("log", "--format=%H%x09%s")
    for line in ledger_output.splitlines():
        commit, subject = line.split("\t", 1)
        if not subject.startswith(WORKLOG_LEDGER_PREFIX):
            continue
        if commit in GRANDFATHERED_LEDGER_COMMITS:
            continue
        changed_paths = git(
            "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        disallowed = [
            path
            for path in changed_paths
            if not path.startswith("docs/worklog/") and path != "docs/roadmap/README.md"
        ]
        if disallowed:
            errors.append(
                f"worklog ledger commit {commit[:7]} changes disallowed paths: "
                + ", ".join(disallowed)
            )


def normalized_adr_ref(value: str, by_path: dict[str, str]) -> str:
    if re.fullmatch(r"ADR-\d{4}", value):
        return value
    cleaned = value.split("#", 1)[0].replace("\\", "/")
    return by_path.get(Path(cleaned).name, value)


def _decision_relation_errors(
    decision_id: str,
    doc: Document,
    by_id: dict[str, Document],
    by_path: dict[str, str],
    graph: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    for raw in doc.meta.get("supersedes", []):
        target = normalized_adr_ref(str(raw), by_path)
        if target not in by_id:
            errors.append(f"{doc.relative}: unknown supersedes reference {raw!r}")
            continue
        graph[decision_id].add(target)
        reverse = by_id[target].meta.get("superseded_by")
        if reverse is None or normalized_adr_ref(str(reverse), by_path) != decision_id:
            errors.append(
                f"{doc.relative}: {target} does not reciprocate superseded_by={decision_id}"
            )
    raw_successor = doc.meta.get("superseded_by")
    if not raw_successor:
        return errors
    successor = normalized_adr_ref(str(raw_successor), by_path)
    if successor not in by_id:
        errors.append(f"{doc.relative}: unknown superseded_by reference {raw_successor!r}")
    elif decision_id not in {
        normalized_adr_ref(str(item), by_path)
        for item in by_id[successor].meta.get("supersedes", [])
    }:
        errors.append(f"{doc.relative}: {successor} does not reciprocate supersedes={decision_id}")
    return errors


def validate_decisions(docs: list[Document], errors: list[str]) -> None:
    registry = next((doc for doc in docs if doc.relative == "docs/decisions/README.md"), None)
    decisions = [doc for doc in docs if doc.meta.get("type") == "decision"]
    if not registry:
        errors.append("docs/decisions/README.md: missing decision registry")
        return
    by_id = {str(doc.meta.get("id")): doc for doc in decisions}
    if len(by_id) != len(decisions):
        errors.append("docs/decisions: duplicate decision IDs")
    registry_ids = set(re.findall(r"\bADR-\d{4}\b", registry.body))
    if set(by_id) != registry_ids:
        errors.append(
            "docs/decisions/README.md: registry IDs do not match ADR files "
            f"(registry={sorted(registry_ids)}, files={sorted(by_id)})"
        )
    by_path = {doc.path.name: decision_id for decision_id, doc in by_id.items()}
    graph: dict[str, set[str]] = {decision_id: set() for decision_id in by_id}
    for decision_id, doc in by_id.items():
        errors.extend(_decision_relation_errors(decision_id, doc, by_id, by_path, graph))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            errors.append(f"docs/decisions: superseding cycle includes {node}")
            return
        if node in visited:
            return
        visiting.add(node)
        for target in graph[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for decision_id in graph:
        visit(decision_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-tracker",
        action="store_true",
        help="require every roadmap item to have a tracker URL",
    )
    args = parser.parse_args()

    errors: list[str] = []
    docs = [doc for path in markdown_files() if (doc := parse_document(path, errors))]
    for doc in docs:
        validate_schema(doc, errors)
        validate_metadata_references(doc, errors)
        validate_links_and_boundaries(doc, errors)
    validate_roadmap(docs, args.require_tracker, errors)
    validate_handoffs(docs, errors)
    validate_worklog(docs, errors)
    validate_decisions(docs, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"documentation validation failed with {len(errors)} error(s)",
            file=sys.stderr,
        )
        return 1
    print(f"documentation validation passed for {len(docs)} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
