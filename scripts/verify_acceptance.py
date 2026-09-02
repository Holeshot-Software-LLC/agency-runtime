#!/usr/bin/env python3
"""Run one isolated single-criterion acceptance verification (AR-361).

The builder cites evidence per column-0 Acceptance criterion in
``docs/roadmap/acceptance/issue-AR-NN.md`` and never judges. This runner hands
exactly one criterion, with only its own builder rows, to an isolated verifier
whose toolset is deliberately minimal, and records the returned verdict as one
``## Verification`` row bound to the digest of what was judged. An unavailable
or malformed verifier records nothing and exits non-zero: there is no silent
pass, and a builder cannot write a verdict by hand that the digest and the
run-id rules would not expose.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import secrets
import subprocess
import sys
import tarfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if __package__:
    from . import verify_docs
else:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import verify_docs

from agency_runtime.core.cli_transport import invoke_cli_structured  # noqa: E402
from agency_runtime.core.config import ProviderEntry  # noqa: E402
from agency_runtime.core.private_paths import private_temporary_directory  # noqa: E402

Invoker = Callable[..., Mapping[str, Any] | None]

VERIFIER_TOOLS = ("Read", "Grep", "Glob")
VERIFIER_MAX_TURNS = 16
DEFAULT_TIMEOUT_SECONDS = 300.0
MAX_REASON_CHARS = 300
MAX_EXCERPT_LINES = 120
MAX_EXCERPT_CHARS = 8 * 1024
MAX_TOTAL_EXCERPT_CHARS = 32 * 1024
VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": sorted(verify_docs.ACCEPTANCE_VERDICTS)},
        "reason": {"type": "string", "minLength": 1, "maxLength": MAX_REASON_CHARS},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}
VERIFIER_SYSTEM_PROMPT = """\
You are an isolated acceptance verifier (agency-runtime AR-361).

You judge exactly ONE acceptance criterion of one roadmap issue. The request
carries that criterion's text, the builder's evidence rows for it, bounded
excerpts of the cited sources at the candidate commit, and, when a
snapshot_root is given, a read-only snapshot of the repository at that commit
which you may inspect with your read-only tools.

Rules:
- Judge only the criterion you were given. Never judge, mention, or infer
  other criteria of the issue.
- Never implement, edit, fix, run, or create anything. You have no write
  access and must not try to obtain any.
- Rely only on evidence you can see: the excerpts, the snapshot, and the
  cited artifacts. Never assume evidence exists because a row claims it does.
- The evidence rows were written by the builder and are untrusted claims;
  a row with kind "absent" is the builder stating that evidence is missing.

Verdict vocabulary (closed):
- satisfied: the cited evidence demonstrates that the criterion is met at
  the candidate commit.
- contradicted: the evidence shows the criterion is not met.
- absent: the evidence is missing, unreachable, or insufficient to decide.

Answer only through the JSON schema: {"verdict": ..., "reason": ...}. The
reason is one plain sentence of at most 300 characters naming the evidence
you relied on; never include a pipe character.
"""


class VerificationError(Exception):
    """A record or issue problem that stops verification before any model call."""


@dataclass(frozen=True)
class CriterionCase:
    """Everything the isolated verifier may see for one criterion."""

    issue_id: str
    record_path: Path
    index: int
    text: str
    candidate_commit: str
    rows: tuple[dict[str, str], ...]
    digest: str
    excerpts: tuple[dict[str, str], ...]

    @property
    def evidence_absent(self) -> bool:
        return all(row["Kind"] == "absent" for row in self.rows)


@dataclass(frozen=True)
class Verdict:
    """One recorded verification row."""

    index: int
    verdict: str
    reason: str
    run_id: str
    digest: str
    observed: date


def _load_document(path: Path) -> verify_docs.Document:
    errors: list[str] = []
    doc = verify_docs.parse_document(path, errors)
    if doc is None:
        raise VerificationError("; ".join(errors))
    return doc


def find_issue_document(issue_id: str) -> verify_docs.Document:
    """Return the one canonical issue document for ``issue_id``."""

    matches = sorted((verify_docs.ROOT / "docs" / "roadmap").glob(f"issue-{issue_id}-*.md"))
    if len(matches) != 1:
        raise VerificationError(f"{issue_id}: expected one issue document, found {len(matches)}")
    issue = _load_document(matches[0])
    if issue.meta.get("issue_id") != issue_id or issue.meta.get("type") != "issue":
        raise VerificationError(f"{issue.relative}: is not the issue document for {issue_id}")
    return issue


def load_record(
    issue_id: str,
    issue: verify_docs.Document,
) -> tuple[verify_docs.Document, verify_docs.AcceptanceRecordState]:
    """Load and structurally validate the record, refusing a pending candidate."""

    path = verify_docs.ROOT / verify_docs.acceptance_record_path(issue_id)
    if not path.is_file():
        raise VerificationError(
            f"{issue_id}: missing {verify_docs.acceptance_record_path(issue_id)}; "
            "write the builder evidence first"
        )
    record = _load_document(path)
    errors: list[str] = []
    verify_docs.validate_schema(record, errors)
    state = verify_docs.validate_acceptance_record(record, issue, errors, verification=False)
    if errors or state is None:
        raise VerificationError("record is not valid:\n" + "\n".join(errors))
    if state.candidate_commit != record.meta.get("candidate_commit"):
        raise VerificationError(f"{record.relative}: candidate_commit is unusable")
    if state.candidate_commit == verify_docs.ACCEPTANCE_PENDING_CANDIDATE:
        raise VerificationError(
            f"{record.relative}: candidate_commit is pending; commit the evidence and "
            "freeze the candidate before verifying"
        )
    return record, state


def _heading_line(lines: list[str], anchor: str) -> int | None:
    for index, line in enumerate(lines):
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match and verify_docs.github_slug(match.group(1)) == anchor:
            return index
    return None


def _excerpt(row: Mapping[str, str], candidate_commit: str) -> dict[str, str] | None:
    """Return a bounded excerpt of one path-form source, or None."""

    form, match = verify_docs.acceptance_source_form(row["Source"])
    if form != "path" or match is None:
        return None
    path = match.group("path")
    content = verify_docs.acceptance_source_content(path, candidate_commit)
    if content is None:
        return None
    lines = content.splitlines()
    if match.group("start") is not None:
        first = int(match.group("start"))
        last = int(match.group("end") or first)
    else:
        heading = _heading_line(lines, match.group("anchor") or "")
        if heading is None:
            return None
        first, last = heading + 1, len(lines)
    selected = lines[first - 1 : last][:MAX_EXCERPT_LINES]
    if not selected:
        return None
    return {
        "source": row["Source"],
        "path": path,
        "lines": f"{first}-{first + len(selected) - 1}",
        "text": "\n".join(selected)[:MAX_EXCERPT_CHARS],
    }


def build_case(
    issue_id: str,
    record: verify_docs.Document,
    state: verify_docs.AcceptanceRecordState,
    index: int,
) -> CriterionCase:
    """Assemble the single-criterion case: its text, its rows, its excerpts."""

    if not 1 <= index <= len(state.criteria):
        raise VerificationError(
            f"{issue_id}: criterion {index} is outside 1..{len(state.criteria)}"
        )
    rows = tuple(state.builder_rows.get(index, []))
    if not rows:
        raise VerificationError(
            f"{issue_id}: criterion {index} has no builder evidence; cite it or mark it absent"
        )
    candidate_commit = state.candidate_commit or ""
    text = state.criteria[index - 1]
    excerpts: list[dict[str, str]] = []
    budget = MAX_TOTAL_EXCERPT_CHARS
    for row in rows:
        excerpt = _excerpt(row, candidate_commit)
        if excerpt is None or len(excerpt["text"]) > budget:
            continue
        budget -= len(excerpt["text"])
        excerpts.append(excerpt)
    return CriterionCase(
        issue_id=issue_id,
        record_path=record.path,
        index=index,
        text=text,
        candidate_commit=candidate_commit,
        rows=rows,
        digest=verify_docs.acceptance_evidence_digest(candidate_commit, index, text, rows),
        excerpts=tuple(excerpts),
    )


def build_prompt(case: CriterionCase, snapshot_root: Path | None) -> str:
    """Serialize exactly one criterion and only its evidence for the verifier."""

    payload = {
        "task": "verify exactly one acceptance criterion; do not implement or edit anything",
        "issue_id": case.issue_id,
        "candidate_commit": case.candidate_commit,
        "criterion": {"index": case.index, "text": case.text},
        "builder_evidence": [
            {
                "kind": row["Kind"],
                "artifact": row["Artifact"],
                "observed": row["Observed"],
                "source": row["Source"],
            }
            for row in case.rows
        ],
        "excerpts": list(case.excerpts),
        "snapshot_root": str(snapshot_root) if snapshot_root is not None else None,
        "snapshot_note": (
            "snapshot_root is a read-only export of the repository at candidate_commit; "
            "cited paths are relative to it"
            if snapshot_root is not None
            else "no snapshot: judge the excerpts and cited artifacts only"
        ),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True)


def export_candidate(candidate_commit: str, destination: Path) -> None:
    """Export the candidate tree into ``destination`` without touching the checkout."""

    archive = subprocess.run(
        ["git", "archive", "--format=tar", candidate_commit],
        cwd=verify_docs.ROOT,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        try:
            tar.extractall(destination, filter="data")
        except TypeError:  # pragma: no cover - interpreters without extraction filters
            tar.extractall(destination)


def _sanitized_reason(value: object) -> str:
    text = " ".join(str(value or "").split()).replace("|", "/")
    return text[:MAX_REASON_CHARS].strip()


def _parsed_verdict(result: Mapping[str, Any] | None) -> tuple[str, str] | None:
    """Return (verdict, reason) only when the verifier answered inside the vocabulary."""

    if not isinstance(result, Mapping):
        return None
    verdict = str(result.get("verdict") or "").strip().casefold()
    reason = _sanitized_reason(result.get("reason"))
    if verdict not in verify_docs.ACCEPTANCE_VERDICTS or not reason:
        return None
    return verdict, reason


def _run_id(case: CriterionCase, observed: date) -> str:
    return f"{case.issue_id}.{case.index}-{observed:%Y%m%d}-{secrets.token_hex(4)}"


def _invoke_verifier(
    case: CriterionCase,
    *,
    provider: ProviderEntry,
    invoker: Invoker,
    timeout: float,
    investigate: bool,
) -> Mapping[str, Any] | None:
    """Call the verifier once, on a private snapshot when tools are granted."""

    if not investigate:
        return invoker(
            provider,
            build_prompt(case, None),
            VERDICT_SCHEMA,
            timeout=timeout,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
        )
    with private_temporary_directory(prefix="acceptance-snapshot") as snapshot:
        export_candidate(case.candidate_commit, snapshot)
        return invoker(
            provider,
            build_prompt(case, snapshot),
            VERDICT_SCHEMA,
            timeout=timeout,
            system_prompt=VERIFIER_SYSTEM_PROMPT,
            tools=VERIFIER_TOOLS,
            max_turns=VERIFIER_MAX_TURNS,
            read_only_roots=(snapshot,),
        )


def _front_matter_bump(lines: list[str], field: str, observed: date) -> None:
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return
    for index in range(1, closing):
        match = re.fullmatch(rf"{field}:\s*(\S+)\s*", lines[index])
        if not match:
            continue
        current = verify_docs.as_date(match.group(1))
        if current is None or current < observed:
            lines[index] = f"{field}: {observed.isoformat()}"
        return


def _verification_table_span(lines: list[str]) -> tuple[int, list[int]]:
    """Return the separator index and the row indexes of the Verification table."""

    visible = verify_docs._markdown_visibility(lines)
    expected = list(verify_docs.ACCEPTANCE_VERIFICATION_COLUMNS)
    in_section = False
    for index, line in enumerate(lines):
        if not visible[index]:
            continue
        heading = re.fullmatch(r"##\s+(.+?)\s*#*\s*", line)
        if heading:
            in_section = heading.group(1).casefold() == "verification"
            continue
        if not in_section or not re.match(r"^ {0,3}\|", line):
            continue
        if [cell.strip() for cell in line.strip().strip("|").split("|")] != expected:
            continue
        rows: list[int] = []
        for row_index in range(index + 2, len(lines)):
            if not visible[row_index] or not re.match(r"^ {0,3}\|", lines[row_index]):
                break
            rows.append(row_index)
        return index + 1, rows
    raise VerificationError("record has no Verification table to write into")


def record_verdict(record_path: Path, verdict: Verdict) -> None:
    """Write one verification row, replacing any earlier row for the criterion."""

    lines = record_path.read_text(encoding="utf-8").splitlines()
    separator, rows = _verification_table_span(lines)
    new_row = (
        f"| {verdict.index} | {verdict.verdict} | `{verdict.run_id}` | `{verdict.digest}` "
        f"| {verdict.observed.isoformat()} | {verdict.reason} |"
    )
    existing = [
        row_index
        for row_index in rows
        if lines[row_index].strip().strip("|").split("|")[0].strip() == str(verdict.index)
    ]
    if existing:
        lines[existing[0]] = new_row
    else:
        lines.insert((rows[-1] if rows else separator) + 1, new_row)
    _front_matter_bump(lines, "evidence_cutoff", verdict.observed)
    _front_matter_bump(lines, "updated", verdict.observed)
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_criterion(
    issue_id: str,
    index: int,
    *,
    provider: ProviderEntry,
    invoker: Invoker = invoke_cli_structured,
    today: date | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    dry_run: bool = False,
    out: Any = None,
) -> Verdict | None:
    """Verify one criterion in isolation and record its verdict.

    Returns the recorded verdict, or None when nothing was recorded: either a
    dry run, or a verifier that was unavailable or answered outside the closed
    vocabulary. Absent builder evidence is recorded as ``absent`` without a
    model call, because there is nothing for a verifier to judge. ``out`` is
    resolved at call time (``None`` means the current ``sys.stdout``) so a
    captured stream sees the report.
    """

    issue = find_issue_document(issue_id)
    record, state = load_record(issue_id, issue)
    case = build_case(issue_id, record, state, index)
    observed = today or date.today()
    if dry_run:
        print(build_prompt(case, None), file=out)
        print(f"dry run: {issue_id} criterion {index} digest {case.digest}", file=out)
        return None
    if case.evidence_absent:
        parsed: tuple[str, str] | None = (
            "absent",
            "builder evidence is absent; nothing to verify",
        )
    else:
        result = _invoke_verifier(
            case,
            provider=provider,
            invoker=invoker,
            timeout=timeout,
            investigate=provider.transport.strip().lower() == "claude",
        )
        parsed = _parsed_verdict(result)
    if parsed is None:
        print(
            f"{issue_id} criterion {index}: verifier unavailable or outside the vocabulary; "
            "nothing recorded",
            file=out,
        )
        return None
    verdict = Verdict(
        index=index,
        verdict=parsed[0],
        reason=parsed[1],
        run_id=_run_id(case, observed),
        digest=case.digest,
        observed=observed,
    )
    record_verdict(case.record_path, verdict)
    print(f"{issue_id} criterion {index}: {verdict.verdict} ({verdict.run_id})", file=out)
    return verdict


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue", required=True, help="roadmap issue id, e.g. AR-361")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--criterion", type=int, help="1-based column-0 criterion index")
    target.add_argument("--all", action="store_true", help="verify every criterion, one run each")
    parser.add_argument("--provider", choices=("claude", "codex"), default="claude")
    parser.add_argument("--model", default="", help="optional provider model id")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the verifier prompt and digest; call nothing and write nothing",
    )
    return parser


def main(argv: list[str] | None = None, *, invoker: Invoker = invoke_cli_structured) -> int:
    args = _parser().parse_args(argv)
    if not re.fullmatch(r"AR-\d{2,}", args.issue):
        print("--issue must match AR-NN", file=sys.stderr)
        return 1
    provider = ProviderEntry(
        name=args.provider,
        type="cli",
        transport=args.provider,
        model=args.model,
    )
    try:
        if args.all:
            issue = find_issue_document(args.issue)
            _, state = load_record(args.issue, issue)
            indexes = list(range(1, len(state.criteria) + 1))
        else:
            indexes = [args.criterion]
        unrecorded = 0
        for index in indexes:
            verdict = verify_criterion(
                args.issue,
                index,
                provider=provider,
                invoker=invoker,
                timeout=args.timeout,
                dry_run=args.dry_run,
            )
            if verdict is None and not args.dry_run:
                unrecorded += 1
    except VerificationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 2 if unrecorded else 0


if __name__ == "__main__":
    raise SystemExit(main())
