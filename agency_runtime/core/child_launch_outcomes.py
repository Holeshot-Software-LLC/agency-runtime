"""Resolve what happened to every harness-spawned child launch.

`child_delivery_projection` answers "which children provably received a card",
so it only reports artifacts that carry delivery evidence. That leaves the more
basic question unanswered: of the children the host actually spawned, how many
were staffed, how many were declined for a recorded reason, and how many left no
record at all. Only the last group is a real evidence gap, and before this module
it was indistinguishable from the other two.

Three join keys already exist in the Store and they are complementary -- each one
resolves launches the others miss, which is why any single key looks like a 50%
gap when measured alone:

1. the delivered v6 envelope's own ``decision_id`` (staffed children),
2. the SHA-256 of the child's assignment against ``routing_decisions.query_hash``,
3. the recomputed native-child failure ``context_fingerprint``.

This module reads. It never writes, never consumes a delivery capability, and
never mints a receipt: an outcome here is a diagnostic, not proof of delivery,
which remains the in-lifetime collector's alone under ADR-0156.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from collections.abc import Callable, Iterator, Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

MAX_CHILD_LAUNCHES: Final[int] = 500
MAX_PARENT_TRANSCRIPT_RECORDS: Final[int] = 100_000
MAX_ASSIGNMENT_BYTES: Final[int] = 262_144
MAX_ENVELOPE_BYTES: Final[int] = 65_536

STAFFED: Final[str] = "staffed"
DECLINED: Final[str] = "declined"
UNRECORDED: Final[str] = "unrecorded"

_ENVELOPE = re.compile(r"agency-native-child-team:v6:([A-Za-z0-9+/=]+)")
_DELIVERY_MARKERS: Final[tuple[str, ...]] = (
    "\n\n[AGENCY INFERENCE TEAM v6]",
    "[AGENCY INFERENCE TEAM v6]",
    "<!-- agency-native-child-team:v6:",
)


def original_assignment(text: str) -> str:
    """Return the host's assignment with a genuinely delivered v6 envelope removed.

    The envelope is appended after the host records its own launch input, so the
    hash Agency stored is of the text *before* delivery, and stripping is what
    lets the query-hash join land on a staffed child.

    Stripping keys off a **decodable** envelope, never a bare marker. An
    assignment may legitimately quote these markers -- a review task that talks
    about delivery does exactly that -- and cutting on the mention silently
    truncates the assignment, which produces a hash that matches nothing and
    reports a recorded launch as unrecorded. That is not a hypothetical: it is
    how this function shipped on 2026-08-18, and it cost a child that had a
    receipt all along.
    """

    if not isinstance(text, str):
        return ""
    match = _ENVELOPE.search(text)
    if match is None or _decoded_envelope(text) is None:
        return text
    cuts = [
        position
        for marker in _DELIVERY_MARKERS
        if (position := text.rfind(marker, 0, match.start())) >= 0
    ]
    return text[: min(cuts)].rstrip() if cuts else text[: match.start()].rstrip()


def _decoded_envelope(text: str) -> Mapping[str, Any] | None:
    match = _ENVELOPE.search(text)
    if match is None or len(match.group(1)) > MAX_ENVELOPE_BYTES:
        return None
    try:
        payload = json.loads(base64.b64decode(match.group(1), validate=True))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def read_child_launch(artifact: Path) -> dict[str, Any] | None:
    """Read one child artifact's launch identity and assignment, or None.

    Record zero is the host's own first record for the child. A launch whose
    record zero cannot be read is reported as unreadable rather than skipped,
    because a silently dropped artifact is the same failure this module exists
    to end.
    """

    meta = artifact.with_name(artifact.name.replace(".jsonl", ".meta.json"))
    launch_id = ""
    if meta.is_file():
        try:
            parsed = json.loads(meta.read_text(encoding="utf-8")[:MAX_ASSIGNMENT_BYTES])
        except (OSError, ValueError, UnicodeDecodeError):
            parsed = {}
        if isinstance(parsed, Mapping):
            launch_id = str(parsed.get("toolUseId") or "").strip()
    try:
        with artifact.open(encoding="utf-8") as handle:
            first = handle.readline(MAX_ASSIGNMENT_BYTES)
    except (OSError, UnicodeDecodeError):
        return None
    try:
        record = json.loads(first)
    except ValueError:
        return None
    if not isinstance(record, Mapping):
        return None
    message = record.get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    if not isinstance(content, str):
        return None
    envelope = _decoded_envelope(content)
    return {
        "child_id": artifact.stem.removeprefix("agent-"),
        "launch_id": launch_id,
        "parent_session_id": str(record.get("sessionId") or "").strip(),
        "assignment_sha256": sha256(original_assignment(content).encode("utf-8")).hexdigest(),
        "envelope_decision_id": str(envelope.get("decision_id") or "").strip() if envelope else "",
        # The host's own timestamp for its first child record. Scoping on it is
        # what keeps a delivery rate honest: an artifact root holds children
        # from every runtime that ever ran here, and counting them all against
        # today's install reports a rate for a runtime that never saw them.
        "launched_at": str(record.get("timestamp") or "").strip(),
    }


def parent_recorded_assignments(session_transcript: Path) -> dict[str, str]:
    """Index a parent transcript's launch inputs by the host's own launch id.

    The child artifact is not a faithful copy of the assignment: measured
    2026-08-18, a 3,184-character launch input appears in the child's record
    zero as 867 characters. Agency hashed what the *parent* recorded, so an
    artifact-only hash cannot match for any assignment the host shortened, and
    a resolver that only reads artifacts reports those launches as unrecorded
    however carefully it strips.
    """

    prompts: dict[str, str] = {}
    if not session_transcript.is_file():
        return prompts
    try:
        with session_transcript.open(encoding="utf-8") as handle:
            for index, line in enumerate(handle):
                if index >= MAX_PARENT_TRANSCRIPT_RECORDS:
                    break
                if "tool_use" not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                message = record.get("message") if isinstance(record, Mapping) else None
                blocks = message.get("content") if isinstance(message, Mapping) else None
                if not isinstance(blocks, list):
                    continue
                for block in blocks:
                    if not isinstance(block, Mapping) or block.get("type") != "tool_use":
                        continue
                    payload = block.get("input")
                    prompt = payload.get("prompt") if isinstance(payload, Mapping) else None
                    identity = str(block.get("id") or "").strip()
                    if identity and isinstance(prompt, str) and prompt:
                        prompts[identity] = prompt
    except (OSError, UnicodeDecodeError):
        return prompts
    return prompts


def iter_child_artifacts(root: Path, *, limit: int = MAX_CHILD_LAUNCHES) -> Iterator[Path]:
    """Yield child transcripts under a host artifact root, bounded.

    Both shapes the callers use are accepted: the host's whole projects root,
    where a child sits at ``<project>/<session>/subagents/``, and a single
    project directory, where it sits one level higher. Globbing only one depth
    silently reports zero launches against the other, which reads exactly like
    a host that never spawned anything.
    """

    if not root.is_dir():
        return
    found = sorted(
        set(root.glob("*/subagents/agent-*.jsonl")) | set(root.glob("*/*/subagents/agent-*.jsonl"))
    )
    for seen, artifact in enumerate(found):
        if seen >= limit:
            return
        yield artifact


def resolve_child_launch_outcomes(
    root: Path,
    *,
    host: str,
    decision_by_id: Callable[[str], Mapping[str, Any] | None],
    decision_by_query_hash: Callable[[str, str], Mapping[str, Any] | None],
    decision_by_fingerprint: Callable[[str, str, str], Mapping[str, Any] | None] | None = None,
    since: str = "",
    limit: int = MAX_CHILD_LAUNCHES,
) -> dict[str, Any]:
    """Report one outcome per harness-spawned child launch.

    Each lookup is injected so this stays a pure projection over whatever the
    caller is willing to read. A launch resolves under the first key that
    answers; the keys are tried cheapest-first, and their disagreement is the
    point -- one key alone leaves resolvable launches looking unrecorded.
    """

    launches: list[dict[str, Any]] = []
    unreadable = 0
    out_of_window = 0
    parent_prompts: dict[Path, dict[str, str]] = {}
    for artifact in iter_child_artifacts(root, limit=limit):
        session_dir = artifact.parent.parent
        transcript = session_dir.with_name(session_dir.name + ".jsonl")
        if transcript not in parent_prompts:
            parent_prompts[transcript] = parent_recorded_assignments(transcript)
        launch = read_child_launch(artifact)
        if launch is None:
            unreadable += 1
            continue
        if since and launch["launched_at"] < since:
            # Reported, never silently dropped: a scoped-out launch is a fact
            # about the window, not an artifact that failed to read.
            out_of_window += 1
            continue
        decision = None
        matched_by = ""
        if launch["envelope_decision_id"]:
            decision = decision_by_id(launch["envelope_decision_id"])
            if decision is not None:
                matched_by = "envelope_decision_id"
        # The parent's own record of the launch input is what Agency hashed, so
        # it is tried alongside the artifact's shortened copy rather than
        # instead of it: some hosts record the assignment whole in the child.
        recorded = parent_prompts[transcript].get(launch["launch_id"], "")
        recorded_sha256 = (
            sha256(original_assignment(recorded).encode("utf-8")).hexdigest() if recorded else ""
        )
        for digest in (launch["assignment_sha256"], recorded_sha256):
            if decision is not None or not digest:
                continue
            decision = decision_by_query_hash(launch["parent_session_id"], digest)
            if decision is not None:
                matched_by = "assignment_query_hash"
        if decision is None and decision_by_fingerprint is not None and launch["launch_id"]:
            for digest in (launch["assignment_sha256"], recorded_sha256):
                if decision is not None or not digest:
                    continue
                decision = decision_by_fingerprint(
                    launch["parent_session_id"],
                    launch["launch_id"],
                    digest,
                )
                if decision is not None:
                    matched_by = "context_fingerprint"
        if decision is None:
            outcome = UNRECORDED
        elif str(decision.get("status") or "") == "applied":
            outcome = STAFFED
        else:
            outcome = DECLINED
        launches.append(
            {
                "child_id": launch["child_id"],
                "launch_id": launch["launch_id"],
                "parent_session_id": launch["parent_session_id"],
                "launched_at": launch["launched_at"],
                "outcome": outcome,
                "matched_by": matched_by,
                "decision_id": str((decision or {}).get("id") or ""),
                "status": str((decision or {}).get("status") or ""),
                "source": str((decision or {}).get("source") or ""),
            }
        )
    counts = {
        STAFFED: sum(1 for item in launches if item["outcome"] == STAFFED),
        DECLINED: sum(1 for item in launches if item["outcome"] == DECLINED),
        UNRECORDED: sum(1 for item in launches if item["outcome"] == UNRECORDED),
    }
    return {
        "host": host,
        "root": str(root),
        "root_present": root.is_dir(),
        "launches_seen": len(launches),
        "artifacts_unreadable": unreadable,
        "launches_out_of_window": out_of_window,
        "since": since,
        "scan_limit": limit,
        "scan_truncated": len(launches) + unreadable >= limit,
        "counts": counts,
        # A rate, not a verdict. Delivery proof stays with the in-lifetime
        # collector; this only says whether an outcome was recorded at all.
        "recorded_rate": (
            None if not launches else round((counts[STAFFED] + counts[DECLINED]) / len(launches), 4)
        ),
        "launches": launches,
    }


__all__ = [
    "DECLINED",
    "MAX_CHILD_LAUNCHES",
    "STAFFED",
    "UNRECORDED",
    "iter_child_artifacts",
    "original_assignment",
    "read_child_launch",
    "resolve_child_launch_outcomes",
]
