#!/usr/bin/env python3
"""Validate documentation metadata, indexes, links, and repository boundaries."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import yaml

if __package__:
    from .worklog_history import stable_short_shas
else:
    from worklog_history import stable_short_shas

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
# Published ledger commits that predate or violated enforcement of the narrow
# worklog exemption also touched one unrelated doc each. They are recorded in
# the Notes section of
# `docs/worklog/README.md`, which states the resolution explicitly: "Retained
# as-is; no history rewrite." Rewriting published history to satisfy a linter
# would be the more destructive fix, so they are grandfathered by exact full
# SHA. A new violation must be split before it lands; this set changes only to
# preserve already-shared immutable history through an explicit governed repair.
GRANDFATHERED_LEDGER_COMMITS = frozenset(
    {
        "0e9410b3e818680d507a639e4b5cf7bef8bce41f",
        "a1835947d15e089e235081630b5cc070bd7ecff3",
        "56e7dee0e1b239b585f2f1d5a82cd02eafddceaf",
        "410c1d1d4bbe56857417539344a4e9e027d02b5a",
        "66f62b900031ea19140d7195ed44c2052bf13949",
        "d38e08b50176bb8d859d7a1ea80010fb148a47a0",
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
AR119_AUTHORITY_PATHS = {
    "vision-wording": "docs/roadmap/AR-119-founding-vision.md",
    "completion-evidence": "docs/roadmap/AR-119-rule-host-evidence-matrix.md",
}
AR119_VISION_START = "## Canonical card metaphor\n"
AR119_VISION_END = "## Differentiator\n"
AR119_SUPPORTED_HOSTS = frozenset({"claude", "codex", "zcode", "hermes", "openclaw"})
AR119_RULES = frozenset({f"R{number}" for number in range(1, 10)})
AR119_EVIDENCE_STATES = frozenset({"proven", "negative", "unproven", "not-applicable"})
AR119_MATRIX_COLUMNS = (
    "Rule",
    "Host",
    "State",
    "Implementation",
    "Simulation",
    "Installed",
    "Live",
    "Proof authority",
    "Artifact",
    "Observed",
    "Source",
    "Limitation",
)
AR119_LAYER_EVIDENCE_COLUMNS = (
    "Rule",
    "Host",
    "Layer",
    "State",
    "Authority kind",
    "Artifact",
    "Observed",
    "Source",
)
AR119_LAYER_AUTHORITY_KINDS = {
    "Implementation": "source",
    "Simulation": "test",
    "Installed": "installed-host",
    "Live": "live-host",
}
# This is intentionally code-bound rather than a front-matter escape hatch.
# AR-161's delivery surface was removed by AR-197 before the remaining gates
# could apply. Any change to its preserved Acceptance section invalidates the
# exception and forces a fresh review.
DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS = {
    "docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md": {
        "acceptance_sha256": ("e36df0a5baca59c9f9b057e1a03081f5154ad4ea19acb3512353f90c0841da36"),
        "superseded_by": "docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md",
        "provenance_commit": "f5ca1729915b7dfb8385774412a9e923ab41c404",
        "reason": "AR-197 retired the helper before public delivery",
    }
}


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
        encoding="utf-8",
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


def _markdown_body(text: str) -> str | None:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0] != "---":
        return None
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None
    return "\n".join(lines[closing + 1 :])


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


def _fence_run(line: str) -> tuple[str, str] | None:
    """Return a CommonMark-style fence run and suffix (at most 3-space indent)."""

    match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
    return (match.group(1), match.group(2)) if match else None


def _opening_fence(line: str) -> str | None:
    """Return a valid CommonMark opening fence delimiter, if present."""

    run = _fence_run(line)
    if run is None:
        return None
    delimiter, suffix = run
    if delimiter[0] == "`" and "`" in suffix:
        return None
    return delimiter


def _markdown_visibility(lines: list[str]) -> list[bool]:
    """Mark lines visible to the narrow authority parser.

    Fenced code and multi-line HTML comments are never documentation authority.
    The parser is intentionally conservative: a line containing an HTML comment
    marker is excluded in full rather than trying to interpret inline Markdown.
    """

    visible: list[bool] = []
    fence: str | None = None
    in_comment = False
    for line in lines:
        run = _fence_run(line)
        if fence is not None:
            visible.append(False)
            if run and run[0][0] == fence[0] and len(run[0]) >= len(fence) and not run[1].strip():
                fence = None
            continue
        if in_comment:
            visible.append(False)
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line:
            visible.append(False)
            start = line.index("<!--") + 4
            if "-->" not in line[start:]:
                in_comment = True
            continue
        opening = _opening_fence(line)
        if opening:
            visible.append(False)
            fence = opening
            continue
        visible.append(True)
    return visible


def _contains_visible_raw_html(body: str) -> bool:
    """Return whether active Markdown contains a raw HTML tag outside examples."""

    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    active_lines: list[str] = []
    fence: str | None = None
    in_comment = False
    for line in lines:
        run = _fence_run(line)
        if fence is not None:
            active_lines.append("")
            if run and run[0][0] == fence[0] and len(run[0]) >= len(fence) and not run[1].strip():
                fence = None
            continue
        cleaned: list[str] = []
        cursor = 0
        while cursor < len(line):
            if in_comment:
                end = line.find("-->", cursor)
                if end < 0:
                    cursor = len(line)
                    break
                in_comment = False
                cursor = end + 3
                continue
            start = line.find("<!--", cursor)
            if start < 0:
                cleaned.append(line[cursor:])
                break
            cleaned.append(line[cursor:start])
            in_comment = True
            cursor = start + 4
        active_line = "".join(cleaned)
        opening = _opening_fence(active_line)
        if opening:
            active_lines.append("")
            fence = opening
            continue
        active_lines.append(active_line)
    active = "\n".join(active_lines)
    return bool(re.search(r"<\s*/?\s*[A-Za-z][A-Za-z0-9-]*(?=[\s/>])", active))


def _level_two_sections(body: str, heading: str) -> list[str]:
    """Return every real matching H2 section, ignoring fenced examples."""

    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    visible = _markdown_visibility(lines)
    sections: list[str] = []
    start: int | None = None
    expected = heading.casefold()
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        match = re.fullmatch(r"##\s+(.+?)\s*#*\s*", line)
        if not match:
            continue
        if start is not None:
            sections.append("\n".join(lines[start:index]).rstrip("\n") + "\n")
            start = None
        if match.group(1).casefold() == expected:
            start = index
    if start is not None:
        sections.append("\n".join(lines[start:]).rstrip("\n") + "\n")
    return sections


def _level_two_section(body: str, heading: str) -> str | None:
    """Return exactly one real H2 section with normalized LF and terminal LF."""

    sections = _level_two_sections(body, heading)
    return sections[0] if len(sections) == 1 else None


def _task_markers(section: str) -> list[str]:
    markers: list[str] = []
    active_indents: list[int] = []
    lines = section.splitlines()
    visible = _markdown_visibility(lines)
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        expanded = line.expandtabs(4)
        task_candidates = list(re.finditer(r"(?:[-*+]|\d+[.)])\s+\[([ xX])\](?:\s+|$)", expanded))
        if any(">" in expanded[: match.start()] for match in task_candidates):
            markers.append("quoted")
            continue
        indent = len(expanded) - len(expanded.lstrip(" "))
        match = re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)\[([ xX])\](?:\s+|$)", expanded)
        if match:
            has_parent = any(parent_indent < indent for parent_indent in active_indents)
            markers.append(match.group(1) if indent < 4 or has_parent else " ")
            active_indents = [value for value in active_indents if value < indent]
            active_indents.append(indent)
        elif expanded.strip() and indent == 0:
            active_indents.clear()
    return markers


def _validate_done_acceptance_exception(
    doc: Document,
    section: str,
    exception: dict[str, str],
    issues_by_path: dict[str, Document],
    errors: list[str],
) -> None:
    """Validate one exact code-bound historical Acceptance exception."""

    digest = hashlib.sha256(section.encode("utf-8")).hexdigest()
    if digest != exception["acceptance_sha256"]:
        errors.append(
            f"{doc.relative}: historical Acceptance digest changed "
            f"(expected {exception['acceptance_sha256']}, got {digest})"
        )
    if doc.meta.get("superseded_by") != exception["superseded_by"]:
        errors.append(
            f"{doc.relative}: historical Acceptance exception requires "
            f"superseded_by={exception['superseded_by']}"
        )
    provenance_commit = exception.get("provenance_commit")
    if not isinstance(provenance_commit, str) or not re.fullmatch(
        r"[0-9a-f]{40}", provenance_commit
    ):
        errors.append(
            f"{doc.relative}: historical Acceptance exception needs a full provenance commit"
        )
    else:
        try:
            historical_text = git("show", f"{provenance_commit}:{doc.relative}")
        except subprocess.CalledProcessError:
            errors.append(
                f"{doc.relative}: historical Acceptance provenance commit/path is unavailable"
            )
        else:
            historical_body = _markdown_body(historical_text)
            historical_section = (
                _level_two_section(historical_body, "Acceptance")
                if historical_body is not None
                else None
            )
            historical_digest = (
                hashlib.sha256(historical_section.encode("utf-8")).hexdigest()
                if historical_section is not None
                else None
            )
            if historical_digest != exception["acceptance_sha256"]:
                errors.append(
                    f"{doc.relative}: provenance commit does not contain the bound "
                    "historical Acceptance section"
                )
    if not isinstance(exception.get("reason"), str) or not exception["reason"].strip():
        errors.append(f"{doc.relative}: historical Acceptance exception needs a non-empty reason")
    successor = issues_by_path.get(exception["superseded_by"])
    if successor is None:
        errors.append(f"{doc.relative}: historical Acceptance successor is not an issue document")


def validate_issue_acceptance(docs: list[Document], errors: list[str]) -> None:
    issues = [doc for doc in docs if doc.meta.get("type") == "issue"]
    issues_by_path = {doc.relative: doc for doc in issues}
    exception_paths = set(DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS)
    seen_exception_paths: set[str] = set()
    for doc in issues:
        if doc.meta.get("status") != "done":
            continue
        sections = _level_two_sections(doc.body, "Acceptance")
        if len(sections) != 1:
            errors.append(
                f"{doc.relative}: done issue requires exactly one real ## Acceptance "
                f"section; found {len(sections)}"
            )
            continue
        section = sections[0]
        markers = _task_markers(section)
        if not markers:
            errors.append(f"{doc.relative}: done issue Acceptance has no task markers")
            continue
        quoted = sum(marker == "quoted" for marker in markers)
        if quoted:
            errors.append(
                f"{doc.relative}: done issue Acceptance contains {quoted} blockquoted "
                "task marker(s); quoted examples cannot satisfy acceptance"
            )
            continue
        unchecked = sum(marker == " " for marker in markers)
        exception = DONE_ACCEPTANCE_PROVENANCE_EXCEPTIONS.get(doc.relative)
        if not unchecked:
            if exception:
                errors.append(
                    f"{doc.relative}: stale done-acceptance provenance exception; "
                    "all Acceptance tasks are checked"
                )
            continue
        if not exception:
            errors.append(
                f"{doc.relative}: done issue has {unchecked} unchecked Acceptance task(s)"
            )
            continue
        seen_exception_paths.add(doc.relative)
        _validate_done_acceptance_exception(
            doc,
            section,
            exception,
            issues_by_path,
            errors,
        )
    missing = sorted(exception_paths - seen_exception_paths)
    errors.extend(
        f"{path}: configured done-acceptance exception is not in use"
        for path in missing
        if path in issues_by_path
    )
    errors.extend(
        f"{path}: configured done-acceptance exception document is missing"
        for path in sorted(exception_paths - set(issues_by_path))
    )


def _canonical_vision_block(body: str) -> str | None:
    if _contains_visible_raw_html(body):
        return None
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    visible = _markdown_visibility(lines)
    starts = [
        index
        for index, line in enumerate(lines)
        if visible[index] and line + "\n" == AR119_VISION_START
    ]
    ends = [
        index
        for index, line in enumerate(lines)
        if visible[index] and line + "\n" == AR119_VISION_END
    ]
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        return None
    return "\n".join(lines[starts[0] : ends[0]]) + "\n"


def _matrix_rows(body: str) -> list[dict[str, str]] | None:
    section = _level_two_section(body, "Canonical matrix")
    if section is None:
        return None
    lines = section.splitlines()
    visible = _markdown_visibility(lines)
    expected_header = list(AR119_MATRIX_COLUMNS)
    header_indexes: list[int] = []
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        if not re.match(r"^ {0,3}\|", line):
            continue
        header = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header == expected_header:
            header_indexes.append(index)
    if len(header_indexes) != 1:
        return None
    index = header_indexes[0]
    if (
        index + 1 >= len(lines)
        or not visible[index + 1]
        or not re.fullmatch(
            r"\s*\|(?:\s*:?-+:?\s*\|){11}\s*:?-+:?\s*\|?\s*",
            lines[index + 1],
        )
    ):
        return None
    rows: list[dict[str, str]] = []
    for row_index in range(index + 2, len(lines)):
        row_line = lines[row_index]
        if not visible[row_index] or not re.match(r"^ {0,3}\|", row_line):
            break
        cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
        if len(cells) != len(expected_header):
            return None
        rows.append(dict(zip(expected_header, cells, strict=True)))
    return rows


def _layer_evidence_rows(body: str) -> list[dict[str, str]] | None:
    section = _level_two_section(body, "Layer evidence")
    if section is None:
        return None
    lines = section.splitlines()
    visible = _markdown_visibility(lines)
    expected_header = list(AR119_LAYER_EVIDENCE_COLUMNS)
    header_indexes: list[int] = []
    for index, line in enumerate(lines):
        if not visible[index] or not re.match(r"^ {0,3}\|", line):
            continue
        header = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header == expected_header:
            header_indexes.append(index)
    if len(header_indexes) != 1:
        return None
    index = header_indexes[0]
    if (
        index + 1 >= len(lines)
        or not visible[index + 1]
        or not re.fullmatch(
            r"\s*\|(?:\s*:?-+:?\s*\|){7}\s*:?-+:?\s*\|?\s*",
            lines[index + 1],
        )
    ):
        return None
    rows: list[dict[str, str]] = []
    for row_index in range(index + 2, len(lines)):
        row_line = lines[row_index]
        if not visible[row_index] or not re.match(r"^ {0,3}\|", row_line):
            break
        cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
        if len(cells) != len(expected_header):
            return None
        rows.append(dict(zip(expected_header, cells, strict=True)))
    return rows


def _aggregate_evidence_states(states: list[str]) -> str:
    if "negative" in states:
        return "negative"
    if states and all(state == "proven" for state in states):
        return "proven"
    return "unproven"


def _ar119_matrix_row_errors(relative: str, row: dict[str, str]) -> list[str]:
    key = (row["Rule"], row["Host"])
    errors: list[str] = []
    if row["Rule"] not in AR119_RULES:
        errors.append(f"{relative}: unknown matrix rule {row['Rule']!r}")
    if row["Host"] not in AR119_SUPPORTED_HOSTS:
        errors.append(f"{relative}: unknown matrix host {row['Host']!r}")
    state_columns = ("State", "Implementation", "Simulation", "Installed", "Live")
    errors.extend(
        f"{relative}: {key[0]}/{key[1]} has invalid {column} state {row[column]!r}"
        for column in state_columns
        if row[column] not in AR119_EVIDENCE_STATES
    )
    if "not-applicable" in {row[column] for column in state_columns}:
        errors.append(
            f"{relative}: {key[0]}/{key[1]} cannot be not-applicable for a supported host"
        )
    layer_columns = ("Implementation", "Simulation", "Installed", "Live")
    if all(row[column] in AR119_EVIDENCE_STATES for column in state_columns):
        expected_state = _aggregate_evidence_states([row[column] for column in layer_columns])
        if row["State"] != expected_state:
            errors.append(
                f"{relative}: {key[0]}/{key[1]} State must derive from its evidence "
                f"layers as {expected_state!r}"
            )
    evidence_columns = ("Proof authority", "Artifact", "Observed", "Source", "Limitation")
    errors.extend(
        f"{relative}: {key[0]}/{key[1]} has empty {column}"
        for column in evidence_columns
        if not row[column]
    )
    if row["Observed"] != "unobserved" and not is_date(row["Observed"]):
        errors.append(f"{relative}: {key[0]}/{key[1]} Observed must be YYYY-MM-DD or unobserved")
    asserted_evidence = any(row[column] in {"proven", "negative"} for column in state_columns)
    if asserted_evidence:
        if row["Source"].strip("`").casefold() == "none":
            errors.append(f"{relative}: {key[0]}/{key[1]} asserted evidence needs a source")
        if row["Artifact"].strip("`").casefold() == "none":
            errors.append(f"{relative}: {key[0]}/{key[1]} asserted evidence needs an artifact")
        if row["Observed"] == "unobserved":
            errors.append(
                f"{relative}: {key[0]}/{key[1]} asserted evidence needs an observation date"
            )
    return errors


def _ar119_rule_nine_errors(relative: str, rows: list[dict[str, str]]) -> list[str]:
    by_key = {(row["Rule"], row["Host"]): row for row in rows}
    expected_keys = {(rule, host) for rule in AR119_RULES for host in AR119_SUPPORTED_HOSTS}
    if set(by_key) != expected_keys:
        return []
    errors: list[str] = []
    columns = ("State", "Implementation", "Simulation", "Installed", "Live")
    for host in sorted(AR119_SUPPORTED_HOSTS):
        parity = by_key[("R9", host)]
        for column in columns:
            expected = _aggregate_evidence_states(
                [by_key[(f"R{number}", host)][column] for number in range(1, 9)]
            )
            if parity[column] != expected:
                errors.append(
                    f"{relative}: R9/{host} {column} must derive from R1-R8 as {expected!r}"
                )
    return errors


def _validate_layer_source(
    relative: str,
    key: tuple[str, str, str],
    source: str,
    candidate_commit: str,
) -> list[str]:
    errors: list[str] = []
    normalized = source.strip().strip("`")
    match = re.fullmatch(
        r"(?P<path>[A-Za-z0-9_./-]+)"
        r"(?::(?P<start>\d+)(?:-(?P<end>\d+))?|#(?P<anchor>[a-z0-9][a-z0-9-]*))",
        normalized,
    )
    label = f"{key[0]}/{key[1]}/{key[2]}"
    if not match:
        return [
            f"{relative}: {label} layer evidence Source must be an exact "
            "repository path:line[-line] or path#heading"
        ]
    path = match.group("path")
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in path:
        return [f"{relative}: {label} layer evidence Source escapes the repository"]
    try:
        content = git("show", f"{candidate_commit}:{path}")
    except subprocess.CalledProcessError:
        return [f"{relative}: {label} layer evidence Source is absent from candidate_commit"]
    authority_kind = AR119_LAYER_AUTHORITY_KINDS.get(key[2])
    if authority_kind == "source" and not path.startswith("agency_runtime/"):
        errors.append(
            f"{relative}: {label} source authority must cite agency_runtime/ implementation"
        )
    elif authority_kind == "test" and not path.startswith("tests/"):
        errors.append(f"{relative}: {label} test authority must cite tests/")
    elif authority_kind in {"installed-host", "live-host"} and not (
        path.startswith("docs/roadmap/") and match.group("anchor")
    ):
        errors.append(
            f"{relative}: {label} host authority must cite a docs/roadmap/ evidence heading"
        )
    start = match.group("start")
    if start is not None:
        first = int(start)
        last = int(match.group("end") or start)
        line_count = len(content.splitlines())
        if first < 1 or last < first or last > line_count:
            errors.append(
                f"{relative}: {label} layer evidence Source has an invalid candidate line range"
            )
    else:
        anchor = match.group("anchor")
        body = _markdown_body(content) if path.casefold().endswith(".md") else content
        if body is None or anchor not in headings(body):
            errors.append(
                f"{relative}: {label} layer evidence Source heading is absent from candidate"
            )
    return errors


def _ar119_layer_evidence_errors(
    relative: str,
    matrix_rows: list[dict[str, str]],
    layer_rows: list[dict[str, str]],
    candidate_commit: str,
    evidence_cutoff: date | None,
) -> list[str]:
    errors: list[str] = []
    expected = {
        (row["Rule"], row["Host"], layer): row[layer]
        for row in matrix_rows
        if row["Rule"] != "R9"
        for layer in AR119_LAYER_AUTHORITY_KINDS
        if row[layer] in {"proven", "negative"}
    }
    observed: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in layer_rows:
        key = (row["Rule"], row["Host"], row["Layer"])
        label = f"{key[0]}/{key[1]}/{key[2]}"
        if key in observed:
            errors.append(f"{relative}: duplicate layer evidence {label}")
            continue
        observed[key] = row
        if row["Rule"] == "R9":
            errors.append(f"{relative}: R9 must not have direct layer evidence")
        if row["Rule"] not in AR119_RULES or row["Host"] not in AR119_SUPPORTED_HOSTS:
            errors.append(f"{relative}: {label} is not a supported matrix layer")
            continue
        expected_kind = AR119_LAYER_AUTHORITY_KINDS.get(row["Layer"])
        if expected_kind is None:
            errors.append(f"{relative}: {label} has an unknown evidence layer")
            continue
        expected_state = expected.get(key)
        if expected_state is None:
            errors.append(f"{relative}: {label} supplies evidence for an unasserted layer")
        elif row["State"] != expected_state:
            errors.append(
                f"{relative}: {label} evidence State must match the matrix as {expected_state!r}"
            )
        if row["State"] not in {"proven", "negative"}:
            errors.append(f"{relative}: {label} evidence State must be proven or negative")
        if row["Authority kind"] != expected_kind:
            errors.append(f"{relative}: {label} Authority kind must be {expected_kind!r}")
        if not row["Artifact"] or row["Artifact"].strip("`").casefold() == "none":
            errors.append(f"{relative}: {label} needs a non-none layer Artifact")
        observed_at = as_date(row["Observed"])
        if observed_at is None:
            errors.append(f"{relative}: {label} layer Observed must be YYYY-MM-DD")
        elif evidence_cutoff and observed_at > evidence_cutoff:
            errors.append(f"{relative}: {label} layer observation exceeds evidence_cutoff")
        errors.extend(_validate_layer_source(relative, key, row["Source"], candidate_commit))
    missing = sorted(set(expected) - set(observed))
    if missing:
        errors.append(
            f"{relative}: missing layer evidence "
            + ", ".join(f"{rule}/{host}/{layer}" for rule, host, layer in missing)
        )
    return errors


def _validate_ar119_matrix(doc: Document, vision_digest: str, errors: list[str]) -> None:
    if doc.meta.get("vision_block_sha256") != vision_digest:
        errors.append(f"{doc.relative}: vision_block_sha256 must equal the founding vision digest")
    candidate_commit = doc.meta.get("candidate_commit")
    if not isinstance(candidate_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", candidate_commit):
        errors.append(f"{doc.relative}: candidate_commit must be a full lowercase Git SHA")
    else:
        try:
            git("cat-file", "-e", f"{candidate_commit}^{{commit}}")
        except subprocess.CalledProcessError:
            errors.append(f"{doc.relative}: candidate_commit does not identify a Git commit")
        else:
            try:
                git("merge-base", "--is-ancestor", candidate_commit, "HEAD")
            except subprocess.CalledProcessError:
                errors.append(f"{doc.relative}: candidate_commit must be an ancestor of HEAD")
    evidence_cutoff = as_date(doc.meta.get("evidence_cutoff"))
    if evidence_cutoff is None:
        errors.append(f"{doc.relative}: evidence_cutoff must be YYYY-MM-DD")
    rows = _matrix_rows(doc.body)
    if rows is None:
        errors.append(f"{doc.relative}: missing or malformed canonical evidence matrix table")
        return
    expected = {(rule, host) for rule in AR119_RULES for host in AR119_SUPPORTED_HOSTS}
    observed: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["Rule"], row["Host"])
        if key in observed:
            errors.append(f"{doc.relative}: duplicate matrix cell {key[0]}/{key[1]}")
        observed.add(key)
        errors.extend(_ar119_matrix_row_errors(doc.relative, row))
        observed_at = as_date(row["Observed"])
        if evidence_cutoff and observed_at and observed_at > evidence_cutoff:
            errors.append(f"{doc.relative}: {key[0]}/{key[1]} observation exceeds evidence_cutoff")
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    if missing:
        errors.append(
            f"{doc.relative}: matrix is missing cells "
            + ", ".join(f"{rule}/{host}" for rule, host in missing)
        )
    if unexpected:
        errors.append(
            f"{doc.relative}: matrix has unexpected cells "
            + ", ".join(f"{rule}/{host}" for rule, host in unexpected)
        )
    errors.extend(_ar119_rule_nine_errors(doc.relative, rows))
    layer_rows = _layer_evidence_rows(doc.body)
    if layer_rows is None:
        errors.append(f"{doc.relative}: missing or malformed layer evidence table")
    elif isinstance(candidate_commit, str) and re.fullmatch(r"[0-9a-f]{40}", candidate_commit):
        errors.extend(
            _ar119_layer_evidence_errors(
                doc.relative,
                rows,
                layer_rows,
                candidate_commit,
                evidence_cutoff,
            )
        )


def validate_ar119_authorities(docs: list[Document], errors: list[str]) -> None:
    marked = [doc for doc in docs if "ar119_authority" in doc.meta]
    by_role: dict[str, list[Document]] = {}
    for doc in marked:
        role = str(doc.meta.get("ar119_authority"))
        if role not in AR119_AUTHORITY_PATHS:
            errors.append(f"{doc.relative}: unknown ar119_authority role {role!r}")
            continue
        by_role.setdefault(role, []).append(doc)
        expected_path = AR119_AUTHORITY_PATHS[role]
        if doc.relative != expected_path:
            errors.append(
                f"{doc.relative}: ar119_authority {role!r} is reserved for {expected_path}"
            )
        if doc.meta.get("status") != "active":
            errors.append(f"{doc.relative}: AR-119 authority must have status 'active'")
    for role, expected_path in AR119_AUTHORITY_PATHS.items():
        current = by_role.get(role, [])
        if len(current) != 1:
            errors.append(
                f"AR-119 authority role {role!r} requires exactly one document at "
                f"{expected_path}; found {len(current)}"
            )

    vision = next(
        (doc for doc in marked if doc.relative == AR119_AUTHORITY_PATHS["vision-wording"]),
        None,
    )
    matrix = next(
        (doc for doc in marked if doc.relative == AR119_AUTHORITY_PATHS["completion-evidence"]),
        None,
    )
    if vision is None:
        return
    recorded_digest = vision.meta.get("canonical_block_sha256")
    if not isinstance(recorded_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", recorded_digest):
        errors.append(f"{vision.relative}: canonical_block_sha256 must be 64 lowercase hex chars")
        return
    block = _canonical_vision_block(vision.body)
    if block is None:
        errors.append(f"{vision.relative}: canonical vision boundaries are missing or ambiguous")
        return
    computed_digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
    if computed_digest != recorded_digest:
        errors.append(
            f"{vision.relative}: canonical vision digest mismatch "
            f"(expected {recorded_digest}, got {computed_digest})"
        )
        return
    if matrix is not None:
        _validate_ar119_matrix(matrix, recorded_digest, errors)


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


def load_pre_tracker_history(root: Path) -> set[str]:
    """Return roadmap IDs exempt from tracker requirements (AR-347)."""

    path = root / "docs" / "roadmap" / "pre-tracker-history.txt"
    if not path.is_file():
        return set()
    entries = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            entries.add(entry)
    return entries


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
    pre_tracker = load_pre_tracker_history(ROOT)
    stale_exemptions = sorted(
        issue_id
        for index, issue_id in enumerate(ids)
        if issue_id in pre_tracker and tracker_urls[index]
    )
    if stale_exemptions:
        errors.append(
            "docs/roadmap/pre-tracker-history.txt: entries now carry tracker URLs "
            f"and must be removed: {', '.join(stale_exemptions)}"
        )
    if require_tracker:
        missing = [
            ids[index]
            for index, value in enumerate(tracker_urls)
            if not value and ids[index] not in pre_tracker
        ]
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
    output = git("log", "--reverse", "--date=short", "--format=%H%x09%ad%x09%s")
    history: list[tuple[str, str, str]] = []
    for line in output.splitlines():
        full_sha, commit_date, subject = line.split("\t", 2)
        if not subject.startswith(WORKLOG_LEDGER_PREFIX):
            history.append((full_sha, commit_date, subject))
    try:
        shortened = stable_short_shas(item[0] for item in history)
    except ValueError as exc:
        errors.append(f"docs/worklog/README.md: {exc}")
        return
    expected: dict[str, tuple[str, str]] = {}
    for short, (_, commit_date, subject) in zip(shortened, history, strict=True):
        expected[short] = (commit_date, subject)
    # Read commit index rows, not provenance prose. Both worklog tools derive a
    # fixed collision-checked prefix from full history SHAs, so clone-local
    # object databases cannot change the generated width.
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
    validate_issue_acceptance(docs, errors)
    validate_ar119_authorities(docs, errors)
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
