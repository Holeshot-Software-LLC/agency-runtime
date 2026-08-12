"""Independent proof that a harness-spawned child actually received its card.

A ``specialists_loaded`` row proves only that Agency *tried*: the same code under
test writes it.  The one artifact Agency never touches is the transcript the host
itself wrote for the child — the Claude sub-agent JSONL, the Codex child rollout.
Reading that back is the only evidence that the card arrived.

This module is a pure read path.  It opens host artifacts, verifies them, and
returns findings; it never writes, never calls the network, and never consults
the Store.  That is deliberate: a read path needs no rewritable launch seam, so
it is the only rule-4 evidence obtainable on hosts where the launch input cannot
be rewritten at all.

The distinction that makes this evidence rather than an echo: a marker is counted
only when it reached the child **before the child first spoke**.  A marker later
in the transcript is the child *reading about* Agency — grep output, a file it
opened — not Agency staffing it.  In this repository that false positive is not
hypothetical; agents here read these literals out of the source all day.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from heapq import heappush, heapreplace
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import read_bounded_regular_file_prefix
from agency_runtime.core.native_child_prompt_delivery import (
    parse_all_jit_specialist_deliveries,
    parse_native_child_prompt_delivery,
)
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    storage_file_is_trusted,
    storage_parent_is_trusted,
)

# A launch record is small: Claude first lines measure 2-5 KB and the Codex
# child's delivery lands within the first handful of records, behind a
# ~15 KB session_meta.  The ceiling bounds a hostile artifact, not a real one.
MAX_LAUNCH_PREFIX_BYTES: Final[int] = 512 * 1024
MAX_LAUNCH_RECORDS: Final[int] = 64
MAX_CHILD_ARTIFACTS: Final[int] = 4096
MAX_CHILD_FILESYSTEM_ENTRIES: Final[int] = 16_384
MAX_CHILD_DETAIL_RESULTS: Final[int] = 200

_CLAUDE_CHILD_GLOB: Final[str] = "*/*/subagents/**/agent-*.jsonl"
_CODEX_CHILD_GLOB: Final[str] = "*/*/*/rollout-*.jsonl"
_CODEX_INPUT_ROLES: Final[frozenset[str]] = frozenset({"developer", "user"})
_CODEX_TEXT_TYPES: Final[frozenset[str]] = frozenset({"input_text", "text"})


@dataclass(frozen=True, slots=True)
class DeliveredCard:
    """One card whose body hash-verified against its own pinned identity."""

    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str


@dataclass(frozen=True, slots=True)
class ChildDeliveryEvidence:
    """What one host-written child artifact proves about card delivery.

    ``envelope_parent_id`` is what Agency wrote into the envelope;
    ``host_parent_id`` is what the host wrote into its own transcript.  Nothing
    coordinates the two, so their agreement is the independence — that is what
    ``correlated`` records.
    """

    host: str
    artifact: str
    child_id: str
    host_parent_id: str
    envelope_parent_id: str
    correlated: bool
    cards: tuple[DeliveredCard, ...]
    legacy_delivery: bool

    @property
    def staffed(self) -> bool:
        """Whether this child provably received at least one just-in-time card."""

        return bool(self.cards)


@dataclass(frozen=True, slots=True)
class ChildArtifactScan:
    """Bounded newest candidates plus truthful host-tree traversal metadata."""

    root_present: bool
    candidate_count: int
    candidate_count_complete: bool
    filesystem_entries_visited: int
    artifacts: tuple[Path, ...]

    @property
    def truncated(self) -> bool:
        return not self.candidate_count_complete or self.candidate_count > len(self.artifacts)


def _trusted_launch_prefix(path: Path, *, label: str) -> str | None:
    """Return the bounded head of one private, unmodified host artifact."""

    is_windows = os.name == "nt"
    try:
        assert_storage_parent_chain(path.parent, allow_missing=False)
    except (OSError, ValueError):
        return None
    if not storage_parent_is_trusted(
        path.parent,
        is_windows=is_windows,
    ) or not storage_file_is_trusted(path, is_windows=is_windows):
        return None
    try:
        payload = read_bounded_regular_file_prefix(
            path,
            limit=MAX_LAUNCH_PREFIX_BYTES,
            label=label,
        )
    except (OSError, ValueError):
        return None
    try:
        return payload.decode("utf-8")
    except UnicodeError:
        # A truncated prefix can split a multi-byte character; the launch record
        # is long finished by then, so drop the tail rather than the artifact.
        return payload.decode("utf-8", errors="ignore")


def _records(text: str) -> Iterator[Mapping[str, Any]]:
    """Yield bounded leading JSON records, stopping at the first unreadable one.

    The prefix read can cut the final line in half.  A parse failure therefore
    means "the bounded window ended here", not "the artifact is corrupt".
    """

    for index, line in enumerate(text.splitlines()):
        if index >= MAX_LAUNCH_RECORDS:
            return
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except ValueError:
            return
        if not isinstance(record, dict):
            return
        yield record


def _claude_message_text(message: object) -> str:
    """Flatten one Claude message body to the text the child actually received."""

    if isinstance(message, str):
        return message
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, Sequence):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, Mapping) and block.get("type") == "text":
            value = block.get("text")
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def _evidence(
    *,
    host: str,
    path: Path,
    child_id: str,
    host_parent_id: str,
    launch_text: str,
) -> ChildDeliveryEvidence | None:
    """Recover every hash-verified card from one child's pre-speech input."""

    deliveries = parse_all_jit_specialist_deliveries(launch_text)
    legacy = parse_native_child_prompt_delivery(launch_text)
    if not deliveries and legacy is None:
        return None
    envelope_parent_id = (
        deliveries[0].parent_session_id if deliveries else str(legacy.parent_session_id)
    )
    return ChildDeliveryEvidence(
        host=host,
        artifact=str(path),
        child_id=child_id,
        host_parent_id=host_parent_id,
        envelope_parent_id=envelope_parent_id,
        correlated=bool(host_parent_id) and envelope_parent_id == host_parent_id,
        cards=tuple(
            DeliveredCard(
                specialist_slug=delivery.specialist_slug,
                specialist_version=delivery.specialist_version,
                specialist_prompt_hash=delivery.specialist_prompt_hash,
            )
            for delivery in deliveries
        ),
        legacy_delivery=legacy is not None,
    )


def claude_child_delivery_evidence(path: Path) -> ChildDeliveryEvidence | None:
    """Read one Claude sub-agent transcript for the card it was launched with.

    Claude writes the child's own file, so the launch input is record zero.  It
    must be a side-chain user record: anything else is the parent's transcript,
    or a child turn that already ran.
    """

    text = _trusted_launch_prefix(path, label="Claude sub-agent transcript")
    if text is None:
        return None
    first = next(_records(text), None)
    if first is None or first.get("type") != "user" or first.get("isSidechain") is not True:
        return None
    child_id = str(first.get("agentId") or "").strip()
    host_parent_id = str(first.get("sessionId") or "").strip()
    if not child_id:
        return None
    return _evidence(
        host="claude",
        path=path,
        child_id=child_id,
        host_parent_id=host_parent_id,
        launch_text=_claude_message_text(first.get("message")),
    )


def codex_child_delivery_evidence(path: Path) -> ChildDeliveryEvidence | None:
    """Read one Codex rollout, if it is a spawned child, for its launch cards.

    Codex writes one rollout per thread, so a child is identified by its own
    ``thread_spawn`` block rather than by the file's location.  Its launch input
    arrives as ordinary records ahead of anything the child said, so collection
    stops the moment the child speaks.
    """

    text = _trusted_launch_prefix(path, label="Codex child rollout")
    if text is None:
        return None
    records = _records(text)
    meta = next(records, None)
    if meta is None or meta.get("type") != "session_meta":
        return None
    payload = meta.get("payload")
    if not isinstance(payload, Mapping):
        return None
    source = payload.get("source")
    subagent = source.get("subagent") if isinstance(source, Mapping) else None
    spawn = subagent.get("thread_spawn") if isinstance(subagent, Mapping) else None
    if not isinstance(spawn, Mapping):
        # A root thread, not a child the host spawned. Rule 4 says nothing here.
        return None
    child_id = str(payload.get("id") or "").strip()
    host_parent_id = str(spawn.get("parent_thread_id") or "").strip()
    if not child_id:
        return None
    parts: list[str] = []
    for record in records:
        if record.get("type") != "response_item":
            continue
        item = record.get("payload")
        if not isinstance(item, Mapping):
            continue
        # Reasoning, a tool call, or a message in any role but an input role all
        # mean the child has started working. A verifier may miss evidence
        # safely; it may never invent it, so stop rather than keep reading.
        role = str(item.get("role") or "").strip().casefold()
        if item.get("type") != "message" or role not in _CODEX_INPUT_ROLES:
            break
        content = item.get("content")
        if not isinstance(content, Sequence) or isinstance(content, str):
            continue
        for block in content:
            if isinstance(block, Mapping) and block.get("type") in _CODEX_TEXT_TYPES:
                value = block.get("text")
                if isinstance(value, str):
                    parts.append(value)
    return _evidence(
        host="codex",
        path=path,
        child_id=child_id,
        host_parent_id=host_parent_id,
        launch_text="\n".join(parts),
    )


def default_child_artifact_root(host: str) -> Path:
    """Where one host writes its children, honouring that host's home override.

    ``CLAUDE_CONFIG_DIR`` and ``CODEX_HOME`` are the same overrides the installer
    and the canary already respect, so an ephemeral host home is inspectable
    without a second notion of where a host lives.
    """

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        base = os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
        return Path(base).expanduser() / "projects"
    if normalized == "codex":
        base = os.environ.get("CODEX_HOME") or Path.home() / ".codex"
        return Path(base).expanduser() / "sessions"
    raise ValueError("child delivery evidence host is unsupported")


def _artifact_path_matches(host: str, parts: tuple[str, ...]) -> bool:
    """Whether one relative path has the host's child-artifact shape."""

    if host == "claude":
        return (
            len(parts) >= 4 and parts[2] == "subagents" and fnmatchcase(parts[-1], "agent-*.jsonl")
        )
    return len(parts) == 4 and fnmatchcase(parts[-1], "rollout-*.jsonl")


def _artifact_directory_can_match(host: str, parts: tuple[str, ...]) -> bool:
    """Prune traversal to directories that can satisfy the host layout."""

    if host == "claude":
        if len(parts) <= 2:
            return True
        return parts[2] == "subagents"
    return len(parts) < 4


def _bounded_matches(root: Path, host: str) -> ChildArtifactScan:
    """Return newest candidates from one strictly bounded host-tree visit.

    ``Path.glob`` is lazy but can still recursively enumerate and ``stat`` an
    unbounded host history before returning. This walker counts every directory
    entry it examines and stops at ``MAX_CHILD_FILESYSTEM_ENTRIES``. It keeps
    only the newest ``MAX_CHILD_ARTIFACTS`` candidates while continuing the
    bounded visit, so a later, newer artifact can still replace an older one.
    When the visit stops early, ``candidate_count`` is explicitly a lower bound.
    """

    try:
        root_present = root.is_dir()
    except OSError:
        root_present = False
    if not root_present:
        return ChildArtifactScan(False, 0, True, 0, ())
    newest: list[tuple[int, str]] = []
    candidate_count = 0
    entries_visited = 0
    candidate_count_complete = True
    pending: list[tuple[Path, tuple[str, ...]]] = [(root, ())]
    stop = False
    while pending and not stop:
        directory, prefix = pending.pop()
        try:
            entries = os.scandir(directory)
        except OSError:
            candidate_count_complete = False
            continue
        with entries:
            for entry in entries:
                if entries_visited >= MAX_CHILD_FILESYSTEM_ENTRIES:
                    candidate_count_complete = False
                    stop = True
                    break
                entries_visited += 1
                parts = (*prefix, entry.name)
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if _artifact_directory_can_match(host, parts):
                            pending.append((Path(entry.path), parts))
                        continue
                    if not _artifact_path_matches(host, parts) or not entry.is_file(
                        follow_symlinks=False
                    ):
                        continue
                    metadata = entry.stat(follow_symlinks=False)
                except OSError:
                    candidate_count_complete = False
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    continue
                candidate_count += 1
                item = (int(metadata.st_mtime_ns), str(entry.path))
                if len(newest) < MAX_CHILD_ARTIFACTS:
                    heappush(newest, item)
                elif item > newest[0]:
                    heapreplace(newest, item)
    artifacts = tuple(Path(path) for _mtime, path in sorted(newest, reverse=True))
    return ChildArtifactScan(
        True,
        candidate_count,
        candidate_count_complete,
        entries_visited,
        artifacts,
    )


def claude_child_artifacts(projects_root: Path) -> list[Path]:
    """Every Claude sub-agent transcript under one projects root."""

    return list(_bounded_matches(Path(projects_root), "claude").artifacts)


def codex_child_artifacts(sessions_root: Path) -> list[Path]:
    """Every Codex rollout under one date-partitioned sessions root."""

    return list(_bounded_matches(Path(sessions_root), "codex").artifacts)


def child_delivery_evidence(path: Path, *, host: str) -> ChildDeliveryEvidence | None:
    """Read one child artifact for the exact host that wrote it."""

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        return claude_child_delivery_evidence(Path(path))
    if normalized == "codex":
        return codex_child_delivery_evidence(Path(path))
    raise ValueError("child delivery evidence host is unsupported")


def scan_child_delivery_evidence(root: Path, *, host: str) -> list[ChildDeliveryEvidence]:
    """Read every child artifact one host wrote beneath *root*."""

    scan = scan_child_artifacts(root, host=host)
    findings = []
    for artifact in scan.artifacts:
        evidence = child_delivery_evidence(artifact, host=host)
        if evidence is not None:
            findings.append(evidence)
    return findings


def scan_child_artifacts(root: Path, *, host: str) -> ChildArtifactScan:
    """Return one host's bounded newest candidate window without reading bodies."""

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        return _bounded_matches(Path(root), "claude")
    elif normalized == "codex":
        return _bounded_matches(Path(root), "codex")
    else:
        raise ValueError("child delivery evidence host is unsupported")


def child_delivery_projection(
    root: Path,
    *,
    host: str,
    limit: int = 50,
) -> dict[str, Any]:
    """Project bounded, newest independent child-delivery proof for one host.

    An empty ``children`` list means no verified card-delivery proof was found
    in the bounded artifact window. It never means the host spawned no children.
    """

    normalized = str(host or "").strip().casefold()
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_CHILD_DETAIL_RESULTS
    ):
        raise ValueError(
            f"child evidence detail limit must be between 1 and {MAX_CHILD_DETAIL_RESULTS}"
        )
    scan = scan_child_artifacts(Path(root), host=normalized)
    findings: list[ChildDeliveryEvidence] = []
    for artifact in scan.artifacts:
        evidence = child_delivery_evidence(artifact, host=normalized)
        if evidence is not None:
            findings.append(evidence)
    staffed = [finding for finding in findings if finding.staffed]
    details = findings[:limit]
    return {
        "host": normalized,
        "root": str(root),
        "root_present": scan.root_present,
        "artifact_candidates": scan.candidate_count,
        "artifact_candidate_count_complete": scan.candidate_count_complete,
        "artifacts_scanned": len(scan.artifacts),
        "artifact_scan_truncated": scan.truncated,
        "filesystem_entries_visited": scan.filesystem_entries_visited,
        "evidence_count": len(findings),
        "staffed_children": len(staffed),
        "correlated_staffed_children": sum(1 for item in staffed if item.correlated),
        "uncorrelated_staffed_children": sum(1 for item in staffed if not item.correlated),
        "legacy_deliveries": sum(
            1 for item in findings if item.legacy_delivery and not item.staffed
        ),
        "detail_limit": limit,
        "detail_truncated": len(findings) > limit,
        "children": [
            {
                "child_id": finding.child_id,
                "artifact": finding.artifact,
                "parent_id": finding.host_parent_id,
                "envelope_parent_id": finding.envelope_parent_id,
                "correlated": finding.correlated,
                "legacy": finding.legacy_delivery,
                "cards": [
                    {
                        "slug": card.specialist_slug,
                        "version": card.specialist_version,
                        "prompt_hash": card.specialist_prompt_hash,
                    }
                    for card in finding.cards
                ],
            }
            for finding in details
        ],
    }


__all__ = [
    "MAX_CHILD_ARTIFACTS",
    "MAX_CHILD_DETAIL_RESULTS",
    "MAX_CHILD_FILESYSTEM_ENTRIES",
    "MAX_LAUNCH_PREFIX_BYTES",
    "MAX_LAUNCH_RECORDS",
    "ChildArtifactScan",
    "ChildDeliveryEvidence",
    "DeliveredCard",
    "child_delivery_evidence",
    "child_delivery_projection",
    "claude_child_artifacts",
    "claude_child_delivery_evidence",
    "codex_child_artifacts",
    "codex_child_delivery_evidence",
    "default_child_artifact_root",
    "scan_child_artifacts",
    "scan_child_delivery_evidence",
]
