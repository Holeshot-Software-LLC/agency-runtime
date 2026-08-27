"""Independent proof that a harness-spawned child actually received its card.

A ``specialists_loaded`` row proves only that Agency *tried*: the same code under
test writes it.  The one artifact Agency never touches is the transcript the host
itself wrote for the child — the Claude sub-agent JSONL, the Codex child rollout.
Reading that back is the only evidence that the card arrived.

Artifact parsing in this module is a pure read path: it never writes, calls the
network, or treats Agency state as delivery proof.  The explicit verification
entry point can pass a content-free, exact correlation request to an injected
atomic consumer.  The Store adapter persists only that independently verified
projection and consumes the decision once; parsing itself remains Store-free.

The distinction that makes this evidence rather than an echo: a marker is counted
only when it reached the child **before the child first spoke**.  A marker later
in the transcript is the child *reading about* Agency — grep output, a file it
opened — not Agency staffing it.  In this repository that false positive is not
hypothetical; agents here read these literals out of the source all day.
"""

from __future__ import annotations

import json
import os
import re
import stat
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatchcase
from hashlib import sha256
from heapq import heappush, heapreplace
from pathlib import Path
from typing import Any, Final
from uuid import RFC_4122, UUID

from agency_runtime.core.bounded_io import read_bounded_regular_file_prefix
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.filesystem_trust import (
    absolute_path,
    metadata_is_link_or_reparse_point,
    same_file_identity,
)
from agency_runtime.core.native_child_prompt_delivery import (
    parse_all_jit_specialist_deliveries,
    parse_inference_team_delivery,
    parse_native_child_prompt_delivery,
)
from agency_runtime.core.private_paths import (
    _private_temporary_lease_is_current,
    _PrivateTemporaryDirectoryLease,
)
from agency_runtime.core.store.security import (
    assert_storage_parent_chain,
    storage_artifact_parent_is_trusted,
    storage_file_is_trusted,
    storage_parent_is_trusted,
)
from agency_runtime.core.workforce.acceptance import (
    ACCEPTANCE_ENVELOPE_SCHEMA,
    ACCEPTANCE_REASONS,
    AcceptanceOutcome,
    evaluate_acceptance,
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
_V6_TEAM_TOKENS: Final[tuple[str, ...]] = (
    "[AGENCY INFERENCE TEAM v6]",
    "<!-- agency-native-child-team:v6:",
    "<!-- agency-native-child-team-end:v6:",
)
_CLAUDE_WORKFLOW_ID: Final[re.Pattern[str]] = re.compile(r"wf_[A-Za-z0-9_-]{1,124}\Z")
_OUTCOME_PAIR_ID: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{32}\Z")
_OUTCOME_PAIR_ROLE_MARKER: Final[re.Pattern[str]] = re.compile(
    r"<!-- agency-accepted-outcome-pair:v1:"
    r"(?P<pair_id>[0-9a-f]{32}):(?P<role>producer|verifier) -->"
)
_OUTCOME_PAIR_MARKER_TOKEN: Final[str] = "agency-accepted-outcome-pair:v1:"
_VERIFIER_SEMANTIC_SCHEMA: Final[str] = "agency.verifier-semantic.v1"
_VERIFIER_SEMANTIC_DECISIONS: Final[frozenset[str]] = frozenset({"accepted", "rejected"})
_CODEX_V1491_META_MAX_BYTES: Final[int] = 128 * 1024
_CODEX_V1491_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "agent_nickname",
        "agent_path",
        "base_instructions",
        "cli_version",
        "context_window",
        "cwd",
        "history_mode",
        "id",
        "model_provider",
        "multi_agent_version",
        "originator",
        "parent_thread_id",
        "session_id",
        "source",
        "thread_source",
        "timestamp",
    }
)
_CODEX_V1491_ROLLOUT: Final[re.Pattern[str]] = re.compile(
    r"rollout-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2})-(?P<minute>\d{2})-(?P<second>\d{2})-"
    r"(?P<child>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12})\.jsonl\Z"
)
_CODEX_V1491_TIMESTAMP: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z"
)


@dataclass(frozen=True, slots=True)
class DeliveredCard:
    """One card whose body hash-verified against its own pinned identity."""

    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    body_character_length: int | None = None


@dataclass(frozen=True, slots=True)
class _ExpectedChildDelivery:
    """External expected decision used only to verify one host artifact.

    The expectation is not proof. It supplies identities that the independently
    host-written artifact must match exactly. Only a separately injected atomic
    verification consumer may authorize the final verified transition.
    """

    host: str
    parent_session_id: str
    parent_trace_id: str
    launch_id: str
    child_id: str
    decision_id: str
    provider_receipt_digest: str
    task_sha256: str
    team_digest: str
    candidate_digest: str
    install_id: str
    bundle_digest: str
    runtime_digest: str
    issued_at: str
    expires_at: str
    nonce: str
    binding_kind: str
    binding_id: str
    cards: tuple[DeliveredCard, ...]
    artifact_digest: str


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
    v6_delivery: bool = False
    verified_delivery: bool = False
    verification_reason: str = "diagnostic_only"
    artifact_digest: str = ""
    decision_id: str = ""
    team_digest: str = ""
    candidate_digest: str = ""
    runtime_digest: str = ""
    install_id: str = ""
    bundle_digest: str = ""
    pre_speech: bool = False
    parent_trace_id: str = ""
    launch_id: str = ""
    provider_receipt_digest: str = ""
    task_sha256: str = ""
    issued_at: str = ""
    expires_at: str = ""
    nonce: str = ""
    binding_kind: str = ""
    binding_id: str = ""
    host_event_at: str = ""

    @property
    def staffed(self) -> bool:
        """Whether this child provably received at least one just-in-time card."""

        return self.verified_delivery and bool(self.cards)


def _host_child_delivery_projection(
    evidence: ChildDeliveryEvidence,
) -> dict[str, Any] | None:
    """Project verified evidence only for the sealed capability consumer."""

    if not evidence.staffed:
        return None
    return {
        "schema": "agency.host-child-delivery-proof.v1",
        "verified_delivery": True,
        "host": evidence.host,
        "parent_session_id": evidence.envelope_parent_id,
        "parent_trace_id": evidence.parent_trace_id,
        "launch_id": evidence.launch_id,
        "child_id": evidence.child_id,
        "pre_speech": evidence.pre_speech,
        "cards": [
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": card.body_character_length,
            }
            for card in evidence.cards
        ],
        "artifact_digest": evidence.artifact_digest,
        "decision_id": evidence.decision_id,
        "provider_receipt_digest": evidence.provider_receipt_digest,
        "task_sha256": evidence.task_sha256,
        "team_digest": evidence.team_digest,
        "candidate_digest": evidence.candidate_digest,
        "runtime_digest": evidence.runtime_digest,
        "install_id": evidence.install_id,
        "bundle_digest": evidence.bundle_digest,
        "issued_at": evidence.issued_at,
        "expires_at": evidence.expires_at,
        "nonce": evidence.nonce,
        "binding_kind": evidence.binding_kind,
        "binding_id": evidence.binding_id,
    }


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


#: Every answer the in-lifetime collector may give. A silent ``None`` cost a day
#: of diagnosis on 2026-08-14: four host-written child artifacts existed, none
#: carried a card, and the canary reported only that delivery "was not proven".
#: Each stage below now names itself, so the next failure is read rather than
#: re-derived. These strings are evidence, so the vocabulary is closed.
HOST_CHILD_COLLECTION_REASONS: Final[frozenset[str]] = frozenset(
    {
        "collected",
        "collector_raised",
        "host_root_changed",
        "artifact_scan_incomplete",
        "no_child_artifact",
        "multiple_child_artifacts",
        "artifact_unreadable",
        "artifact_changed_after_verification",
        "artifact_outside_invocation_window",
        "artifact_not_trusted",
        "delivery_marker_absent",
        "legacy_delivery_not_authoritative",
        "artifact_origin_not_canonical",
        "child_event_timestamp_invalid",
        "child_event_outside_invocation_window",
        "artifact_not_in_bounded_host_scan",
        "expected_decision_not_found_or_invalid",
        "persisted_decision_invalid",
        "verification_refused",
    }
)

#: Verification reasons that already name their own stage precisely enough to
#: travel unchanged. Anything else collapses to ``verification_refused`` rather
#: than widening evidence with an unbounded string.
_PROMOTED_VERIFICATION_REASONS: Final[frozenset[str]] = frozenset(
    {
        "artifact_not_in_bounded_host_scan",
        "artifact_origin_not_canonical",
        "expected_decision_not_found_or_invalid",
        "persisted_decision_invalid",
    }
)

_PRIVATE_COLLECTION_SEAL = object()
_VERIFIED_DELIVERY_SEAL = object()
_VERIFIED_DELIVERY_IDENTITIES: dict[int, object] = {}
_HOST_INVOCATION_IDENTITIES: dict[int, object] = {}
_VERIFIED_DELIVERY_LOCK = threading.RLock()


def _outcome_pair_role_marker(*, pair_id: str, role: str) -> str:
    """Render the exact host-child role marker used by the outcome canary."""

    if not isinstance(pair_id, str) or _OUTCOME_PAIR_ID.fullmatch(pair_id) is None:
        raise ValueError("accepted outcome pair id must be 32 lowercase hex characters")
    if role not in {"producer", "verifier"}:
        raise ValueError("accepted outcome pair role must be producer or verifier")
    return f"<!-- agency-accepted-outcome-pair:v1:{pair_id}:{role} -->"


def _verifier_semantic_marker(*, pair_id: str, decision: str) -> str:
    """Render the one exact JSON line a verifier writes in its own artifact."""

    if not isinstance(pair_id, str) or _OUTCOME_PAIR_ID.fullmatch(pair_id) is None:
        raise ValueError("accepted outcome pair id must be 32 lowercase hex characters")
    normalized = str(decision or "").strip().casefold()
    if normalized not in _VERIFIER_SEMANTIC_DECISIONS:
        raise ValueError("verifier semantic decision must be accepted or rejected")
    return json.dumps(
        {
            "schema": _VERIFIER_SEMANTIC_SCHEMA,
            "pair_id": pair_id,
            "decision": normalized,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


@dataclass(frozen=True, slots=True)
class _PrivateHostArtifactCollection:
    """One fresh, private host root captured before a native invocation.

    The constructor is sealed deliberately.  A caller-selected path, an
    environment override, or a backend result mapping is not an artifact-origin
    capability.  The safe backend obtains this value only after creating and
    validating an empty isolated host namespace, then retains it in memory until
    the host process exits and collection finishes.
    """

    host: str
    lease: _PrivateTemporaryDirectoryLease = field(repr=False, compare=False)
    root: Path
    root_metadata: os.stat_result = field(repr=False, compare=False)
    started_at_ns: int
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _PRIVATE_COLLECTION_SEAL or not _private_temporary_lease_is_current(
            self.lease
        ):
            raise TypeError("private host artifact collections are created by the safe backend")


@dataclass(frozen=True, slots=True)
class _HostInvocationWindow:
    """One sealed monotonic/wall-clock window around a real host process."""

    collection: _PrivateHostArtifactCollection = field(repr=False, compare=False)
    started_at_ns: int
    finished_at_ns: int
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._seal is not _PRIVATE_COLLECTION_SEAL
            or not _private_temporary_lease_is_current(self.collection.lease)
            or self.started_at_ns <= 0
            or self.finished_at_ns < self.started_at_ns
        ):
            raise TypeError("host invocation windows are created by the safe backend")


@dataclass(frozen=True, slots=True)
class _HostInvocationStart:
    """One sealed one-use start boundary immediately before process launch."""

    collection: _PrivateHostArtifactCollection = field(repr=False, compare=False)
    started_at_ns: int
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            self._seal is not _PRIVATE_COLLECTION_SEAL
            or not _private_temporary_lease_is_current(self.collection.lease)
            or self.started_at_ns <= 0
        ):
            raise TypeError("host invocation starts are created by the safe backend")


@dataclass(frozen=True, slots=True)
class HostChildCollection:
    """One collection attempt: the sealed proof when it exists, and why not.

    The reason is reported whether or not a proof was minted, so a passing run
    says ``collected`` and every refusal names the stage that refused. It never
    carries host text, a path, or an exception message: it travels into evidence
    and into the canary report.
    """

    proof: _VerifiedHostChildDelivery | None
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in HOST_CHILD_COLLECTION_REASONS:
            raise ValueError("host child collection reason is outside the bounded vocabulary")
        if (self.proof is not None) != (self.reason == "collected"):
            raise ValueError("host child collection reason does not agree with the proof")


def _uncollected(reason: str) -> HostChildCollection:
    return HostChildCollection(proof=None, reason=reason)


@dataclass(frozen=True, slots=True)
class _VerifierSemanticVerdict:
    """One decision located in the verifier's own host-written artifact."""

    pair_id: str
    decision: str
    artifact_digest: str
    record_index: int

    def __post_init__(self) -> None:
        if (
            _OUTCOME_PAIR_ID.fullmatch(self.pair_id) is None
            or self.decision not in _VERIFIER_SEMANTIC_DECISIONS
            or re.fullmatch(r"[0-9a-f]{64}", self.artifact_digest) is None
            or isinstance(self.record_index, bool)
            or not 1 <= self.record_index < MAX_LAUNCH_RECORDS
        ):
            raise TypeError("verifier semantic verdict is invalid")


@dataclass(frozen=True, slots=True)
class _VerifiedHostChildDelivery:
    """Sealed typed authority produced by the in-lifetime host collector.

    ``ChildDeliveryEvidence`` remains a useful diagnostic projection and can be
    reconstructed from public data.  Canary evaluation accepts this sealed type
    instead, so neither a plain mapping nor a freely constructed diagnostic can
    self-certify host authorship or pre-speech delivery.
    """

    evidence: ChildDeliveryEvidence
    _consumption_scope: str = field(repr=False, compare=False)
    _seal: object = field(repr=False, compare=False)
    _pair_id: str = field(repr=False, compare=False, default="")
    _pair_role: str = field(repr=False, compare=False, default="")
    _semantic: _VerifierSemanticVerdict | None = field(
        repr=False,
        compare=False,
        default=None,
    )

    def __post_init__(self) -> None:
        if self._seal is not _VERIFIED_DELIVERY_SEAL or not self.evidence.staffed:
            raise TypeError("verified host child delivery must come from the trusted collector")
        if self._consumption_scope == "single":
            if self._pair_id or self._pair_role or self._semantic is not None:
                raise TypeError("single-delivery capabilities cannot carry outcome pairing")
            return
        if self._consumption_scope != "pair":
            raise TypeError("verified host child delivery scope is invalid")
        if _OUTCOME_PAIR_ID.fullmatch(self._pair_id) is None or self._pair_role not in {
            "producer",
            "verifier",
        }:
            raise TypeError("paired delivery capability has an invalid role identity")
        if self._pair_role == "producer" and self._semantic is not None:
            raise TypeError("producer delivery capability cannot carry verifier semantics")
        if self._pair_role == "verifier" and (
            self._semantic is None
            or self._semantic.pair_id != self._pair_id
            or self._semantic.artifact_digest != self.evidence.artifact_digest
        ):
            raise TypeError("verifier delivery capability lacks bound host semantics")


def _consume_verified_host_child_delivery(
    value: object,
) -> dict[str, Any] | None:
    """Consume one collector-minted capability into its bounded proof once."""

    with _VERIFIED_DELIVERY_LOCK:
        if (
            type(value) is not _VerifiedHostChildDelivery
            or value._seal is not _VERIFIED_DELIVERY_SEAL
            or value._consumption_scope != "single"
            or _VERIFIED_DELIVERY_IDENTITIES.get(id(value)) is not value
        ):
            return None
        _VERIFIED_DELIVERY_IDENTITIES.pop(id(value), None)
    return _host_child_delivery_projection(value.evidence)


def _discard_verified_host_child_delivery(value: object) -> None:
    """Invalidate an unconsumed capability when orchestration exits early."""

    with _VERIFIED_DELIVERY_LOCK:
        if (
            type(value) is _VerifiedHostChildDelivery
            and value._seal is _VERIFIED_DELIVERY_SEAL
            and _VERIFIED_DELIVERY_IDENTITIES.get(id(value)) is value
        ):
            _VERIFIED_DELIVERY_IDENTITIES.pop(id(value), None)


HOST_ACCEPTED_OUTCOME_REASONS: Final[frozenset[str]] = frozenset(
    ACCEPTANCE_REASONS
    | {
        "host_root_changed",
        "artifact_scan_incomplete",
        "expected_two_child_artifacts",
        "artifact_unreadable",
        "artifact_outside_invocation_window",
        "artifact_not_trusted",
        "delivery_marker_absent",
        "legacy_delivery_not_authoritative",
        "artifact_origin_not_canonical",
        "child_event_timestamp_invalid",
        "child_event_outside_invocation_window",
        "artifact_not_in_bounded_host_scan",
        "expected_decision_not_found_or_invalid",
        "persisted_decision_invalid",
        "verification_refused",
        "pair_role_missing",
        "pair_role_invalid",
        "pair_role_ambiguous",
        "pair_identity_mismatch",
        "verifier_semantic_missing",
        "verifier_semantic_invalid",
        "verifier_semantic_ambiguous",
        "verifier_semantic_outside_invocation_window",
        "producer_semantic_present",
        "producer_output_missing",
        "producer_output_outside_invocation_window",
        "producer_cardinality_invalid",
        "provider_pin_mismatch",
        "contractor_worker_missing",
        "outcome_store_unavailable",
        "outcome_store_failed",
        "outcome_store_invalid",
        "capability_pair_invalid",
    }
)


@dataclass(frozen=True, slots=True)
class _HostAcceptedOutcomeCollection:
    """One bounded producer/verifier collection and Store outcome."""

    result: Mapping[str, Any] | None
    reason: str
    pair_id: str = ""
    producer_decision_id: str = ""
    verifier_decision_id: str = ""

    def __post_init__(self) -> None:
        if self.reason not in HOST_ACCEPTED_OUTCOME_REASONS:
            raise ValueError("host accepted outcome reason is outside the bounded vocabulary")
        if self.pair_id and _OUTCOME_PAIR_ID.fullmatch(self.pair_id) is None:
            raise ValueError("host accepted outcome pair identity is invalid")
        if self.result is not None and self.result.get("reason") != self.reason:
            raise ValueError("host accepted outcome result does not agree with its reason")


def _uncollected_outcome(reason: str) -> _HostAcceptedOutcomeCollection:
    return _HostAcceptedOutcomeCollection(result=None, reason=reason)


def _trusted_launch_prefix_bytes(
    path: Path,
    *,
    label: str,
    artifact_parent: bool = False,
) -> bytes | None:
    """Return the exact bounded bytes used to compute artifact identity."""

    is_windows = os.name == "nt"
    try:
        assert_storage_parent_chain(path.parent, allow_missing=False)
    except (OSError, ValueError):
        return None
    parent_is_trusted = (
        storage_artifact_parent_is_trusted if artifact_parent else storage_parent_is_trusted
    )
    if not parent_is_trusted(
        path.parent,
        is_windows=is_windows,
    ) or not storage_file_is_trusted(path, is_windows=is_windows):
        return None
    try:
        return read_bounded_regular_file_prefix(
            path,
            limit=MAX_LAUNCH_PREFIX_BYTES,
            label=label,
        )
    except (OSError, ValueError):
        return None


def _trusted_launch_material(
    path: Path,
    *,
    label: str,
    artifact_parent: bool = False,
) -> tuple[str, str] | None:
    """Read and hash one exact trusted artifact window without a TOCTOU reread."""

    payload = _trusted_launch_prefix_bytes(
        path,
        label=label,
        artifact_parent=artifact_parent,
    )
    if payload is None:
        return None
    # Prefix reads may end in the middle of a later UTF-8 code point. Only
    # complete JSONL records are evidence; trim the incomplete suffix before
    # strict decoding and use those exact bytes as the artifact identity.
    if not payload.endswith(b"\n"):
        _separator, found, _tail = payload.rpartition(b"\n")
        if not found:
            return None
        payload = _separator + b"\n"
    try:
        text = payload.decode("utf-8")
    except UnicodeError:
        # A lossy decode could erase tampering around an otherwise parseable
        # envelope. Host evidence is authority, so malformed bytes fail closed.
        return None
    return text, sha256(payload).hexdigest()


def _path_beneath_root(path: Path, root: Path) -> tuple[Path, tuple[str, ...]] | None:
    """Return a lexical canonical-root join without resolving attacker links."""

    artifact = absolute_path(path)
    canonical_root = absolute_path(root)
    try:
        relative = artifact.relative_to(canonical_root)
    except ValueError:
        return None
    parts = relative.parts
    return (
        (artifact, parts) if parts and all(part not in {"", ".", ".."} for part in parts) else None
    )


def _canonical_codex_uuid7(value: object) -> UUID | None:
    """Return one lowercase canonical RFC UUIDv7, never a loose identifier."""

    if type(value) is not str or not value or value != value.strip():
        return None
    try:
        parsed = UUID(value)
    except (AttributeError, TypeError, ValueError):
        return None
    if str(parsed) != value or parsed.version != 7 or parsed.variant != RFC_4122:
        return None
    return parsed


def _canonical_absolute_path_text(value: object) -> str:
    """Return an already-canonical absolute path spelling or an empty string."""

    if not isinstance(value, (str, os.PathLike)):
        return ""
    try:
        candidate = Path(value)
        normalized = absolute_path(candidate)
    except (OSError, TypeError, ValueError):
        return ""
    return str(candidate) if candidate.is_absolute() and candidate == normalized else ""


def _codex_v1491_utc_timestamp(value: object) -> datetime | None:
    """Parse the millisecond UTC timestamp spelling emitted by Codex 0.149.1."""

    if type(value) is not str or _CODEX_V1491_TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _codex_v1491_rollout_identity(
    path: object,
    *,
    child: UUID,
    root: Path,
) -> tuple[Path, datetime] | None:
    """Bind one canonical rollout path to its date partition and child UUID."""

    if not isinstance(path, (str, os.PathLike)):
        return None
    try:
        supplied = Path(path)
        artifact = absolute_path(supplied)
    except (OSError, TypeError, ValueError):
        return None
    if not supplied.is_absolute() or supplied != artifact:
        return None
    joined = _path_beneath_root(artifact, root)
    if joined is None:
        return None
    _artifact, parts = joined
    if len(parts) != 4:
        return None
    match = _CODEX_V1491_ROLLOUT.fullmatch(parts[3])
    if match is None or match.group("child") != str(child):
        return None
    if parts[:3] != (
        match.group("year"),
        match.group("month"),
        match.group("day"),
    ):
        return None
    try:
        rollout_at = datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            int(match.group("hour")),
            int(match.group("minute")),
            int(match.group("second")),
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
    return artifact, rollout_at


def _codex_v1491_first_record(path: Path) -> Mapping[str, Any] | None:
    """Read exactly one bounded, duplicate-free, trusted host metadata record."""

    prefix = _trusted_launch_prefix_bytes(
        path,
        label="Codex 0.149.1 child session metadata",
        artifact_parent=True,
    )
    if prefix is None:
        return None
    newline = prefix.find(b"\n")
    if (
        newline <= 0
        or newline > _CODEX_V1491_META_MAX_BYTES
        or prefix[newline - 1 : newline] == b"\r"
    ):
        return None
    try:
        record = safe_load_bounded_json(
            prefix[:newline],
            maximum_bytes=_CODEX_V1491_META_MAX_BYTES,
            maximum_depth=12,
            maximum_nodes=256,
        )
    except (TypeError, ValueError):
        return None
    return record if isinstance(record, Mapping) else None


def _codex_v1491_parent_from_record(  # noqa: C901 - exact closed host schema
    record: Mapping[str, Any],
    *,
    child: UUID,
    expected_cwd: str,
    rollout_at: datetime,
) -> str:
    """Validate the closed Codex 0.149.1 child metadata contract."""

    if set(record) != {"timestamp", "type", "payload", "ordinal"}:
        return ""
    if record.get("type") != "session_meta" or type(record.get("ordinal")) is not int:
        return ""
    if record.get("ordinal") != 0:
        return ""
    payload = record.get("payload")
    if not isinstance(payload, Mapping) or set(payload) != _CODEX_V1491_PAYLOAD_KEYS:
        return ""
    if (
        payload.get("cli_version") != "0.149.1"
        or payload.get("originator") != "codex_exec"
        or payload.get("history_mode") != "paginated"
        or payload.get("thread_source") != "subagent"
        or payload.get("multi_agent_version") != "v2"
        or payload.get("model_provider") != "openai"
        or payload.get("cwd") != expected_cwd
    ):
        return ""

    record_child = _canonical_codex_uuid7(payload.get("id"))
    parent_session = _canonical_codex_uuid7(payload.get("session_id"))
    parent_thread = _canonical_codex_uuid7(payload.get("parent_thread_id"))
    if (
        record_child != child
        or parent_session is None
        or parent_thread != parent_session
        or parent_session == child
        or (parent_session.int >> 80) >= (child.int >> 80)
    ):
        return ""

    source = payload.get("source")
    if not isinstance(source, Mapping) or set(source) != {"subagent"}:
        return ""
    subagent = source.get("subagent")
    if not isinstance(subagent, Mapping) or set(subagent) != {"thread_spawn"}:
        return ""
    spawn = subagent.get("thread_spawn")
    expected_spawn_keys = {
        "parent_thread_id",
        "depth",
        "agent_path",
        "agent_nickname",
        "agent_role",
    }
    if not isinstance(spawn, Mapping) or set(spawn) != expected_spawn_keys:
        return ""
    spawn_parent = _canonical_codex_uuid7(spawn.get("parent_thread_id"))
    agent_path = payload.get("agent_path")
    agent_nickname = payload.get("agent_nickname")
    if (
        spawn_parent != parent_session
        or type(spawn.get("depth")) is not int
        or spawn.get("depth") != 1
        or spawn.get("agent_role") is not None
        or type(agent_path) is not str
        or not agent_path
        or type(agent_nickname) is not str
        or not agent_nickname
        or spawn.get("agent_path") != agent_path
        or spawn.get("agent_nickname") != agent_nickname
    ):
        return ""

    base = payload.get("base_instructions")
    if not isinstance(base, Mapping) or set(base) != {"provenance", "text"}:
        return ""
    provenance = base.get("provenance")
    if (
        type(base.get("text")) is not str
        or not base.get("text")
        or not isinstance(provenance, Mapping)
        or set(provenance) != {"type", "model"}
        or provenance.get("type") != "model"
        or type(provenance.get("model")) is not str
        or not provenance.get("model")
    ):
        return ""
    context_window = payload.get("context_window")
    if not isinstance(context_window, Mapping) or set(context_window) != {"window_id"}:
        return ""
    window_id = _canonical_codex_uuid7(context_window.get("window_id"))
    if window_id is None or (window_id.int >> 80) != (child.int >> 80):
        return ""

    outer_at = _codex_v1491_utc_timestamp(record.get("timestamp"))
    payload_at = _codex_v1491_utc_timestamp(payload.get("timestamp"))
    child_at = datetime.fromtimestamp((child.int >> 80) / 1000, tz=timezone.utc)
    if (
        outer_at is None
        or payload_at is None
        or not payload_at <= outer_at <= payload_at + timedelta(seconds=5)
        or payload_at.replace(microsecond=0) != rollout_at
        or abs(payload_at - child_at) > timedelta(seconds=1)
    ):
        return ""
    return str(parent_session)


def codex_v1491_child_parent_session(
    path: object,
    *,
    child_id: object,
    cwd: object,
    root: Path | None = None,
) -> str:
    """Resolve one exact Codex 0.149.1 child to its host-authored parent.

    This is a pure, fail-closed artifact read. It confers no staffing or Store
    authority by itself; the caller must still resolve and validate one exact
    live parent route.
    """

    child = _canonical_codex_uuid7(child_id)
    expected_cwd = _canonical_absolute_path_text(cwd)
    if child is None or not expected_cwd:
        return ""
    try:
        canonical_root = absolute_path(
            default_child_artifact_root("codex") if root is None else Path(root)
        )
    except (OSError, TypeError, ValueError):
        return ""
    identity = _codex_v1491_rollout_identity(
        path,
        child=child,
        root=canonical_root,
    )
    if identity is None:
        return ""
    artifact, rollout_at = identity
    record = _codex_v1491_first_record(artifact)
    if record is None:
        return ""
    return _codex_v1491_parent_from_record(
        record,
        child=child,
        expected_cwd=expected_cwd,
        rollout_at=rollout_at,
    )


def _canonical_host_artifact_shape(
    path: Path,
    *,
    host: str,
    root: Path,
    evidence: ChildDeliveryEvidence,
) -> bool:
    """Bind a verified artifact to one observed host-owned namespace shape."""

    joined = _path_beneath_root(path, root)
    if joined is None:
        return False
    _artifact, parts = joined
    if host == "claude":
        direct = len(parts) == 4 and parts[2] == "subagents"
        workflow = (
            len(parts) == 6
            and parts[2:4] == ("subagents", "workflows")
            and _CLAUDE_WORKFLOW_ID.fullmatch(parts[4]) is not None
        )
        return bool(
            (direct or workflow)
            and parts[1] == evidence.host_parent_id
            and parts[-1] == f"agent-{evidence.child_id}.jsonl"
        )
    if host == "codex":
        # The rollout timestamp may differ from the current wall clock, but its
        # partition and exact session suffix are host-owned structural joins.
        return bool(
            len(parts) == 4
            and re.fullmatch(r"\d{4}", parts[0])
            and re.fullmatch(r"(?:0[1-9]|1[0-2])", parts[1])
            and re.fullmatch(r"(?:0[1-9]|[12]\d|3[01])", parts[2])
            and parts[3].startswith("rollout-")
            and parts[3].endswith(f"-{evidence.child_id}.jsonl")
        )
    return False


def _canonical_host_artifact_is_trusted(
    path: Path,
    *,
    host: str,
    root: Path,
    evidence: ChildDeliveryEvidence,
) -> bool:
    """Revalidate namespace, privacy, and exact file identity before Store use.

    This blocks caller-selected files outside the host namespace. It cannot
    distinguish a transcript forged by the same account or a compromised host;
    that remains an explicit residual until the host signs its artifacts.
    """

    if not _canonical_host_artifact_shape(path, host=host, root=root, evidence=evidence):
        return False
    artifact = absolute_path(path)
    canonical_root = absolute_path(root)
    try:
        assert_storage_parent_chain(canonical_root, allow_missing=False)
        assert_storage_parent_chain(artifact.parent, allow_missing=False)
        root_before = canonical_root.lstat()
        file_before = artifact.lstat()
    except (OSError, ValueError):
        return False
    parent_is_trusted = (
        storage_artifact_parent_is_trusted if host == "codex" else storage_parent_is_trusted
    )
    if (
        metadata_is_link_or_reparse_point(root_before)
        or not stat.S_ISDIR(root_before.st_mode)
        or metadata_is_link_or_reparse_point(file_before)
        or not stat.S_ISREG(file_before.st_mode)
        or int(getattr(file_before, "st_nlink", 0) or 0) != 1
        or not parent_is_trusted(canonical_root, is_windows=os.name == "nt")
        or not parent_is_trusted(artifact.parent, is_windows=os.name == "nt")
        or not storage_file_is_trusted(artifact, is_windows=os.name == "nt")
    ):
        return False
    try:
        return same_file_identity(root_before, canonical_root.lstat()) and same_file_identity(
            file_before,
            artifact.lstat(),
        )
    except OSError:
        return False


def _artifact_is_in_bounded_scan(path: Path, *, host: str, root: Path) -> bool:
    """Require one exact file identity inside the bounded host discovery window."""

    target = absolute_path(path)
    scan = scan_child_artifacts(root, host=host)
    return any(absolute_path(candidate) == target for candidate in scan.artifacts)


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


@dataclass(frozen=True, slots=True)
class _OutcomePairArtifact:
    pair_id: str
    role: str
    semantic: _VerifierSemanticVerdict | None


def _semantic_marker_payload(line: str) -> Mapping[str, Any] | None:
    try:
        payload = json.loads(line.strip())
    except ValueError:
        return None
    if not isinstance(payload, Mapping) or payload.get("schema") != _VERIFIER_SEMANTIC_SCHEMA:
        return None
    return payload


def _outcome_pair_role(launch_text: str) -> tuple[str, str, str]:
    """Return one exact producer/verifier role marker from the launch text."""

    role_matches = list(_OUTCOME_PAIR_ROLE_MARKER.finditer(launch_text))
    marker_literals = launch_text.count(_OUTCOME_PAIR_MARKER_TOKEN)
    if not role_matches:
        reason = "pair_role_invalid" if marker_literals else "pair_role_missing"
        return reason, "", ""
    if len(role_matches) != 1 or marker_literals != 1:
        return "pair_role_ambiguous", "", ""
    return "", role_matches[0].group("pair_id"), role_matches[0].group("role")


def _scan_verifier_semantics(
    records: Sequence[Mapping[str, Any]],
    *,
    pair_id: str,
    artifact_digest: str,
    invocation: _HostInvocationWindow,
) -> tuple[str, tuple[_VerifierSemanticVerdict, ...], int, bool]:
    """Locate exact semantic JSON lines in assistant-authored records."""

    markers: list[_VerifierSemanticVerdict] = []
    literals = 0
    invalid = False
    for record_index, record in enumerate(records[1:], start=1):
        record_message = record.get("message")
        if (
            record.get("type") != "assistant"
            or not isinstance(record_message, Mapping)
            or record_message.get("role") != "assistant"
        ):
            continue
        record_text = _claude_message_text(record_message)
        literals += record_text.count(_VERIFIER_SEMANTIC_SCHEMA)
        for line in record_text.splitlines():
            payload = _semantic_marker_payload(line)
            if payload is None:
                continue
            decision = payload.get("decision")
            if (
                set(payload) != {"schema", "pair_id", "decision"}
                or payload.get("pair_id") != pair_id
                or not isinstance(decision, str)
                or decision not in _VERIFIER_SEMANTIC_DECISIONS
            ):
                invalid = True
                continue
            observed = _utc_timestamp(str(record.get("timestamp") or ""))
            if observed is None or not _within_invocation(
                int(observed.timestamp() * 1_000_000_000),
                invocation,
            ):
                return "verifier_semantic_outside_invocation_window", (), 0, False
            markers.append(
                _VerifierSemanticVerdict(
                    pair_id=pair_id,
                    decision=decision,
                    artifact_digest=artifact_digest,
                    record_index=record_index,
                )
            )
    return "", tuple(markers), literals, invalid


def _producer_output_reason(
    records: Sequence[Mapping[str, Any]],
    *,
    invocation: _HostInvocationWindow,
) -> str:
    """Require at least one in-window assistant record in the producer artifact."""

    output_found = False
    for record in records[1:]:
        record_message = record.get("message")
        if (
            record.get("type") != "assistant"
            or not isinstance(record_message, Mapping)
            or record_message.get("role") != "assistant"
            or not _claude_message_text(record_message).strip()
        ):
            continue
        observed = _utc_timestamp(str(record.get("timestamp") or ""))
        if observed is None or not _within_invocation(
            int(observed.timestamp() * 1_000_000_000),
            invocation,
        ):
            return "producer_output_outside_invocation_window"
        output_found = True
    return "" if output_found else "producer_output_missing"


def _outcome_pair_artifact(
    path: Path,
    *,
    evidence: ChildDeliveryEvidence,
    invocation: _HostInvocationWindow,
) -> tuple[str, _OutcomePairArtifact | None]:
    """Read role and verifier semantics from the same verified Claude artifact."""

    material = _trusted_launch_material(path, label="Claude accepted outcome child transcript")
    if material is None:
        return "artifact_unreadable", None
    text, artifact_digest = material
    if artifact_digest != evidence.artifact_digest:
        return "artifact_changed_after_verification", None
    records = list(_records(text))
    first = records[0] if records else None
    message = first.get("message") if isinstance(first, Mapping) else None
    if (
        first is None
        or first.get("type") != "user"
        or first.get("isSidechain") is not True
        or not isinstance(message, Mapping)
        or message.get("role") != "user"
    ):
        return "pair_role_invalid", None
    reason, pair_id, role = _outcome_pair_role(_claude_message_text(message))
    if reason:
        return reason, None

    reason, semantic_markers, semantic_literals, invalid_semantic = _scan_verifier_semantics(
        records,
        pair_id=pair_id,
        artifact_digest=artifact_digest,
        invocation=invocation,
    )
    if reason:
        return reason, None
    if role == "producer":
        if semantic_literals or semantic_markers or invalid_semantic:
            return "producer_semantic_present", None
        reason = _producer_output_reason(records, invocation=invocation)
        if reason:
            return reason, None
        return "", _OutcomePairArtifact(pair_id=pair_id, role=role, semantic=None)
    if len(semantic_markers) > 1 or (
        semantic_markers and (invalid_semantic or semantic_literals > 1)
    ):
        return "verifier_semantic_ambiguous", None
    if invalid_semantic:
        return "verifier_semantic_invalid", None
    if not semantic_markers:
        return (
            "verifier_semantic_invalid" if semantic_literals else "verifier_semantic_missing"
        ), None
    return "", _OutcomePairArtifact(
        pair_id=pair_id,
        role=role,
        semantic=semantic_markers[0],
    )


def _v6_cards(delivery: Any) -> tuple[DeliveredCard, ...]:
    return tuple(
        DeliveredCard(
            specialist_slug=card.specialist_slug,
            specialist_version=card.specialist_version,
            specialist_prompt_hash=card.specialist_prompt_hash,
            body_character_length=card.body_character_length,
        )
        for card in delivery.cards
    )


def _utc_timestamp(value: str) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.utcoffset() != timezone.utc.utcoffset(None):
        return None
    return parsed


def _expected_v6_reason(
    delivery: Any,
    expected: _ExpectedChildDelivery | None,
    *,
    host: str,
    child_id: str,
    host_parent_id: str,
    structural_hook_output: bool,
    artifact_digest: str,
    host_event_at: str,
) -> str:
    """Return ``verified`` only for an exact, independently consumed decision."""

    if host == "codex" and not structural_hook_output:
        # Supported Codex transcripts store the delegated input as ordinary
        # developer/user records and carry the actual inter-agent message
        # opaquely. Public diagnostics cannot attribute one such record to an
        # Agency hook. The restricted current-profile canary has a narrower
        # structural contract: its sole complete v6 record is the exact
        # ``SubagentStart.additionalContext`` output and enters only through a
        # sealed internal collector.
        return "unsupported_opaque_interagent_channel"
    if expected is None:
        return (
            "expected_decision_not_supplied"
            if structural_hook_output
            else "host_hook_output_origin_not_proven"
        )
    if expected.host != host:
        return "host_mismatch"
    actual = {
        "parent_session_id": delivery.parent_session_id,
        "parent_trace_id": delivery.parent_trace_id,
        "launch_id": delivery.launch_id,
        "decision_id": delivery.decision_id,
        "provider_receipt_digest": delivery.provider_receipt_digest,
        "task_sha256": delivery.task_sha256,
        "team_digest": delivery.team_digest,
        "candidate_digest": delivery.candidate_digest,
        "install_id": delivery.install_id,
        "bundle_digest": delivery.bundle_digest,
        "runtime_digest": delivery.runtime_digest,
        "issued_at": delivery.issued_at,
        "expires_at": delivery.expires_at,
        "nonce": delivery.nonce,
        "binding_kind": delivery.binding_kind,
        "binding_id": delivery.binding_id,
    }
    wanted = {field: getattr(expected, field) for field in actual}
    if actual != wanted:
        return "expected_decision_mismatch"
    if expected.parent_session_id != host_parent_id or expected.child_id != child_id:
        return "host_parent_child_mismatch"
    if expected.artifact_digest != artifact_digest:
        return "artifact_digest_mismatch"
    if expected.candidate_digest != expected.runtime_digest:
        return "installed_runtime_candidate_mismatch"
    issued = _utc_timestamp(delivery.issued_at)
    expires = _utc_timestamp(delivery.expires_at)
    observed = _utc_timestamp(host_event_at)
    if (
        issued is None
        or expires is None
        or observed is None
        or expires <= issued
        or not issued <= observed <= expires
    ):
        return "decision_time_window_invalid"
    if _v6_cards(delivery) != expected.cards:
        return "expected_team_mismatch"
    binding_matches = (delivery.binding_kind == "child_id" and delivery.binding_id == child_id) or (
        delivery.binding_kind == "launch_id" and delivery.binding_id == delivery.launch_id
    )
    if not binding_matches:
        return "child_or_launch_binding_invalid"
    return "exact_expected_delivery"


_VERIFICATION_CONSUMER_SEAL = object()


class _NativeChildDeliveryVerificationConsumer:
    """Sealed adapter for the Store's atomic or read-only exact consumer."""

    __slots__ = ("_callback", "_seal")

    def __init__(
        self,
        callback: Callable[[Mapping[str, Any]], object],
        *,
        _seal: object,
    ) -> None:
        if _seal is not _VERIFICATION_CONSUMER_SEAL:
            raise TypeError("native child verification consumers are internal")
        self._callback = callback
        self._seal = _seal

    def __call__(self, request: Mapping[str, Any]) -> object:
        if self._seal is not _VERIFICATION_CONSUMER_SEAL:
            return False
        return self._callback(request)


def _verification_request(
    delivery: Any,
    *,
    host: str,
    child_id: str,
    artifact_digest: str,
    host_event_at: str,
    structural_hook_output: bool,
) -> dict[str, Any]:
    """Build the closed content-free input for one atomic Store consumer.

    ``artifact_digest`` is the SHA-256 of the exact bounded trusted read window,
    not a claim that bytes after the evidence window were read or hashed.
    """

    return {
        "schema": "agency.native-child-delivery-verification.v1",
        "host": host,
        "parent_session_id": delivery.parent_session_id,
        "parent_trace_id": delivery.parent_trace_id,
        "launch_id": delivery.launch_id,
        "child_id": child_id,
        "pre_speech": True,
        "structural_hook_output": structural_hook_output,
        "cards": [
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": card.body_character_length,
            }
            for card in delivery.cards
        ],
        "artifact_digest": artifact_digest,
        "decision_id": delivery.decision_id,
        "provider_receipt_digest": delivery.provider_receipt_digest,
        "task_sha256": delivery.task_sha256,
        "team_digest": delivery.team_digest,
        "candidate_digest": delivery.candidate_digest,
        "runtime_digest": delivery.runtime_digest,
        "install_id": delivery.install_id,
        "bundle_digest": delivery.bundle_digest,
        "issued_at": delivery.issued_at,
        "expires_at": delivery.expires_at,
        "host_event_at": host_event_at,
        "nonce": delivery.nonce,
        "binding_kind": delivery.binding_kind,
        "binding_id": delivery.binding_id,
    }


def _consume_exact_verification(
    consumer: _NativeChildDeliveryVerificationConsumer | None,
    request: Mapping[str, Any],
) -> str:
    """Require one sealed Store consumer; caller callbacks do not count."""

    if not isinstance(consumer, _NativeChildDeliveryVerificationConsumer):
        return "atomic_verification_consumer_not_supplied"
    try:
        consumed = consumer(request)
    except Exception:
        return "atomic_verification_consumer_failed"
    if not (
        isinstance(consumed, Mapping)
        and consumed.get("verified_delivery") is True
        and consumed.get("decision_id") == request.get("decision_id")
        and consumed.get("nonce") == request.get("nonce")
        and consumed.get("artifact_digest") == request.get("artifact_digest")
    ):
        return (
            "atomic_verification_consumer_rejected"
            if consumed is False
            else "atomic_verification_consumer_invalid_result"
        )
    return "verified"


def _store_native_child_delivery_consumer(
    store: object,
) -> _NativeChildDeliveryVerificationConsumer:
    """Adapt the Store's keyword-only atomic consumer without importing Store."""

    method = getattr(store, "_record_native_child_delivery_verification", None)
    if not callable(method):
        raise TypeError("Store does not expose the internal native child delivery consumer")

    def consume(request: Mapping[str, Any]) -> object:
        try:
            return method(
                decision_id=request["decision_id"],
                nonce=request["nonce"],
                artifact_digest=request["artifact_digest"],
                host=request["host"],
                parent_session_id=request["parent_session_id"],
                parent_trace_id=request["parent_trace_id"],
                launch_id=request["launch_id"],
                binding_kind=request["binding_kind"],
                binding_id=request["binding_id"],
                child_id=request["child_id"],
                cards=request["cards"],
            )
        except ValueError:
            # Exact durable-identity mismatches and one-use conflicts are normal
            # proof rejections, not verifier outages.
            return False

    return _NativeChildDeliveryVerificationConsumer(
        consume,
        _seal=_VERIFICATION_CONSUMER_SEAL,
    )


def _expected_delivery_from_store_decision(
    decision: object,
    *,
    decision_id: str,
    child_id: str,
    artifact_digest: str,
) -> _ExpectedChildDelivery | None:
    """Bind one Store decision to identities learned only from the host artifact."""

    if not isinstance(decision, Mapping) or decision.get("decision_id") != decision_id:
        return None
    raw_cards = decision.get("cards")
    if (
        not isinstance(raw_cards, Sequence)
        or isinstance(raw_cards, (str, bytes, bytearray))
        or not raw_cards
    ):
        return None
    cards: list[DeliveredCard] = []
    for item in raw_cards:
        if not isinstance(item, Mapping):
            return None
        slug = item.get("specialist_slug")
        version = item.get("specialist_version")
        prompt_hash = item.get("specialist_prompt_hash")
        body_length = item.get("body_character_length")
        if (
            not isinstance(slug, str)
            or not slug
            or not isinstance(version, str)
            or not version
            or not isinstance(prompt_hash, str)
            or not prompt_hash
            or type(body_length) is not int
        ):
            return None
        cards.append(
            DeliveredCard(
                specialist_slug=slug,
                specialist_version=version,
                specialist_prompt_hash=prompt_hash,
                body_character_length=body_length,
            )
        )
    fields = {
        name: decision.get(name)
        for name in (
            "host",
            "parent_session_id",
            "parent_trace_id",
            "launch_id",
            "provider_receipt_digest",
            "task_sha256",
            "team_digest",
            "candidate_digest",
            "install_id",
            "bundle_digest",
            "runtime_digest",
            "issued_at",
            "expires_at",
            "nonce",
            "binding_kind",
            "binding_id",
        )
    }
    if any(not isinstance(value, str) or not value for value in fields.values()):
        return None
    return _ExpectedChildDelivery(
        host=fields["host"],
        parent_session_id=fields["parent_session_id"],
        parent_trace_id=fields["parent_trace_id"],
        launch_id=fields["launch_id"],
        child_id=child_id,
        decision_id=decision_id,
        provider_receipt_digest=fields["provider_receipt_digest"],
        task_sha256=fields["task_sha256"],
        team_digest=fields["team_digest"],
        candidate_digest=fields["candidate_digest"],
        install_id=fields["install_id"],
        bundle_digest=fields["bundle_digest"],
        runtime_digest=fields["runtime_digest"],
        issued_at=fields["issued_at"],
        expires_at=fields["expires_at"],
        nonce=fields["nonce"],
        binding_kind=fields["binding_kind"],
        binding_id=fields["binding_id"],
        cards=tuple(cards),
        artifact_digest=artifact_digest,
    )


_PERSISTED_RECEIPT_REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "decision_id",
    "nonce",
    "artifact_digest",
    "host",
    "parent_session_id",
    "parent_trace_id",
    "launch_id",
    "binding_kind",
    "binding_id",
    "child_id",
)


def _persisted_receipt_consumer(
    receipt: Mapping[str, Any],
) -> _NativeChildDeliveryVerificationConsumer:
    """Adapt one immutable receipt into a read-only exact verification consumer."""

    def consume(request: Mapping[str, Any]) -> object:
        if receipt.get("verified_delivery") is not True or any(
            receipt.get(field) != request.get(field) for field in _PERSISTED_RECEIPT_REQUEST_FIELDS
        ):
            return False
        return receipt

    return _NativeChildDeliveryVerificationConsumer(
        consume,
        _seal=_VERIFICATION_CONSUMER_SEAL,
    )


def _store_delivery_methods(
    store: object,
) -> tuple[Callable[[str], object], Callable[[str], object]]:
    decision_getter = getattr(store, "get_native_child_staffing_decision", None)
    receipt_getter = getattr(store, "get_native_child_delivery_verification", None)
    if not callable(decision_getter) or not callable(receipt_getter):
        raise TypeError("Store does not expose native child delivery decision and receipt reads")
    return decision_getter, receipt_getter


def _verify_against_persisted_receipt(
    path: Path,
    *,
    host: str,
    diagnostic: ChildDeliveryEvidence,
    store: object,
    structural_hook_output: bool = False,
) -> ChildDeliveryEvidence:
    """Re-project one exact immutable receipt without writing or consuming again."""

    decision_getter, receipt_getter = _store_delivery_methods(store)
    receipt = receipt_getter(diagnostic.decision_id)
    if not isinstance(receipt, Mapping):
        return diagnostic
    expected = _expected_delivery_from_store_decision(
        decision_getter(diagnostic.decision_id),
        decision_id=diagnostic.decision_id,
        child_id=diagnostic.child_id,
        artifact_digest=diagnostic.artifact_digest,
    )
    if expected is None:
        return replace(diagnostic, verification_reason="persisted_decision_invalid")
    verified = _verify_child_delivery_evidence(
        path,
        host=host,
        expected=expected,
        verification_consumer=_persisted_receipt_consumer(receipt),
        structural_hook_output=structural_hook_output,
    )
    if verified is None:
        return diagnostic
    return (
        replace(verified, verification_reason="verified_existing_receipt")
        if verified.staffed
        else verified
    )


def _evidence(
    *,
    host: str,
    path: Path,
    child_id: str,
    host_parent_id: str,
    launch_text: str,
    expected: _ExpectedChildDelivery | None = None,
    structural_hook_output: bool = False,
    artifact_digest: str = "",
    host_event_at: str = "",
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
) -> ChildDeliveryEvidence | None:
    """Recover every hash-verified card from one child's pre-speech input."""

    team = parse_inference_team_delivery(launch_text)
    if team is not None:
        reason = _expected_v6_reason(
            team,
            expected,
            host=host,
            child_id=child_id,
            host_parent_id=host_parent_id,
            structural_hook_output=structural_hook_output,
            artifact_digest=artifact_digest,
            host_event_at=host_event_at,
        )
        if reason == "exact_expected_delivery":
            reason = _consume_exact_verification(
                verification_consumer,
                _verification_request(
                    team,
                    host=host,
                    child_id=child_id,
                    artifact_digest=artifact_digest,
                    host_event_at=host_event_at,
                    structural_hook_output=structural_hook_output,
                ),
            )
        return ChildDeliveryEvidence(
            host=host,
            artifact=str(path),
            child_id=child_id,
            host_parent_id=host_parent_id,
            envelope_parent_id=team.parent_session_id,
            correlated=bool(host_parent_id) and team.parent_session_id == host_parent_id,
            cards=_v6_cards(team),
            legacy_delivery=False,
            v6_delivery=True,
            verified_delivery=reason == "verified",
            verification_reason=reason,
            artifact_digest=artifact_digest,
            decision_id=team.decision_id,
            team_digest=team.team_digest,
            candidate_digest=team.candidate_digest,
            runtime_digest=team.runtime_digest,
            install_id=team.install_id,
            bundle_digest=team.bundle_digest,
            pre_speech=True,
            parent_trace_id=team.parent_trace_id,
            launch_id=team.launch_id,
            provider_receipt_digest=team.provider_receipt_digest,
            task_sha256=team.task_sha256,
            issued_at=team.issued_at,
            expires_at=team.expires_at,
            nonce=team.nonce,
            binding_kind=team.binding_kind,
            binding_id=team.binding_id,
            host_event_at=host_event_at,
        )
    if any(token in launch_text for token in _V6_TEAM_TOKENS):
        # A partial, spliced, mixed-version, or tampered v6 team is one failed
        # atomic delivery. Never fall through and salvage an older marker.
        return None
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
        legacy_delivery=bool(deliveries or legacy is not None),
        verification_reason="legacy_delivery_non_authoritative",
        artifact_digest=artifact_digest,
        pre_speech=True,
        host_event_at=host_event_at,
    )


def claude_child_delivery_evidence(
    path: Path,
    *,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
) -> ChildDeliveryEvidence | None:
    """Read one Claude sub-agent transcript for the card it was launched with.

    Claude writes the child's own file, so the launch input is record zero.  It
    must be a side-chain user record: anything else is the parent's transcript,
    or a child turn that already ran.
    """

    material = _trusted_launch_material(path, label="Claude sub-agent transcript")
    if material is None:
        return None
    text, artifact_digest = material
    first = next(_records(text), None)
    message = first.get("message") if isinstance(first, Mapping) else None
    if (
        first is None
        or first.get("type") != "user"
        or first.get("isSidechain") is not True
        or not isinstance(message, Mapping)
        or message.get("role") != "user"
    ):
        return None
    child_id = str(first.get("agentId") or "").strip()
    host_parent_id = str(first.get("sessionId") or "").strip()
    if not child_id:
        return None
    candidate = expected_deliveries.get(child_id) if expected_deliveries is not None else None
    expected = candidate if isinstance(candidate, _ExpectedChildDelivery) else None
    return _evidence(
        host="claude",
        path=path,
        child_id=child_id,
        host_parent_id=host_parent_id,
        launch_text=_claude_message_text(message),
        expected=expected,
        # Claude identifies record zero as side-chain child input but does not
        # tag any substring as hook-authored. Exact one-use expected-decision
        # correlation is therefore required before this can verify.
        structural_hook_output=False,
        artifact_digest=artifact_digest,
        host_event_at=str(first.get("timestamp") or ""),
        verification_consumer=verification_consumer,
    )


def _codex_child_delivery_evidence(  # noqa: C901 - one pre-speech artifact boundary
    path: Path,
    *,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
    structural_hook_output: bool = False,
) -> ChildDeliveryEvidence | None:
    """Read one Codex rollout, if it is a spawned child, for its launch cards.

    Codex writes one rollout per thread, so a child is identified by its own
    ``thread_spawn`` block rather than by the file's location.  Its launch input
    arrives as ordinary records ahead of anything the child said, so collection
    stops the moment the child speaks.
    """

    material = _trusted_launch_material(
        path,
        label="Codex child rollout",
        artifact_parent=True,
    )
    if material is None:
        return None
    text, artifact_digest = material
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
    candidate = expected_deliveries.get(child_id) if expected_deliveries is not None else None
    expected = candidate if isinstance(candidate, _ExpectedChildDelivery) else None
    messages: list[tuple[str, str]] = []
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
        parts: list[str] = []
        for block in content:
            if isinstance(block, Mapping) and block.get("type") in _CODEX_TEXT_TYPES:
                value = block.get("text")
                if isinstance(value, str):
                    parts.append(value)
        if parts:
            messages.append(("\n".join(parts), str(record.get("timestamp") or "")))
    v6_messages = [
        (text, timestamp)
        for text, timestamp in messages
        if any(token in text for token in _V6_TEAM_TOKENS)
    ]
    if v6_messages:
        # SubagentStart.additionalContext is one distinct input record on the
        # supported Codex profile. Never splice model-authored developer/user
        # records around it into an otherwise valid atomic envelope.
        if len(v6_messages) != 1:
            return None
        launch_text, input_timestamp = v6_messages[0]
    else:
        launch_text = "\n".join(text for text, _timestamp in messages)
        input_timestamp = next((timestamp for _text, timestamp in messages if timestamp), "")
    return _evidence(
        host="codex",
        path=path,
        child_id=child_id,
        host_parent_id=host_parent_id,
        launch_text=launch_text,
        expected=expected,
        structural_hook_output=structural_hook_output,
        artifact_digest=artifact_digest,
        host_event_at=input_timestamp,
        verification_consumer=verification_consumer,
    )


def codex_child_delivery_evidence(
    path: Path,
    *,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
) -> ChildDeliveryEvidence | None:
    """Public Codex artifact diagnostic; it can never attribute hook output."""

    return _codex_child_delivery_evidence(
        path,
        expected_deliveries=expected_deliveries,
        verification_consumer=verification_consumer,
        structural_hook_output=False,
    )


def _restricted_codex_canary_route(
    store: object,
    *,
    parent_session_id: str,
    parent_trace_id: str,
    accepted_terminal_parent: bool = False,
) -> Mapping[str, Any] | None:
    """Return the sole child-bound route under one lifecycle-exact parent."""

    if type(accepted_terminal_parent) is not bool:
        return None
    parent_getter = getattr(store, "get_codex_activation_canary_parent_snapshot", None)
    routes_getter = getattr(store, "get_native_child_staffing_decisions_for_parent", None)
    if not callable(parent_getter) or not callable(routes_getter):
        return None
    try:
        if accepted_terminal_parent:
            parent = parent_getter(
                session_id=parent_session_id,
                trace_id=parent_trace_id,
                accepted_terminal=True,
            )
        else:
            parent = parent_getter(
                session_id=parent_session_id,
                trace_id=parent_trace_id,
            )
        routes = routes_getter(
            session_id=parent_session_id,
            trace_id=parent_trace_id,
            host="codex",
            limit=2,
        )
    except Exception:
        return None
    if not isinstance(parent, Mapping) or not isinstance(routes, list) or len(routes) != 1:
        return None
    parent_route = parent.get("route")
    route = routes[0]
    if not isinstance(parent_route, Mapping) or not isinstance(route, Mapping):
        return None
    from agency_runtime.core.activation_canary_contract import (
        CODEX_ACTIVATION_CANARY_ROUTE_SOURCE,
        CODEX_ACTIVATION_CANARY_WORK_UNIT,
        CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
    )

    expected_task_sha256 = sha256(CODEX_ACTIVATION_CANARY_WORK_UNIT.encode("utf-8")).hexdigest()
    cards = route.get("cards")
    return (
        route
        if (
            parent.get("proven") is True
            and parent.get("session_id") == parent_session_id
            and parent.get("trace_id") == parent_trace_id
            and parent_route.get("status") == "accepted"
            and parent_route.get("source") == CODEX_ACTIVATION_CANARY_ROUTE_SOURCE
            and parent_route.get("selected_ids") == ["code-reviewer"]
            and parent_route.get("semantic_ids") == ["code-reviewer"]
            and parent_route.get("companion_ids") == []
            and parent_route.get("work_units")
            == {
                "delegate": True,
                "count": 1,
                "confidence": "high",
                "source": CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE,
            }
            and route.get("host") == "codex"
            and route.get("parent_session_id") == parent_session_id
            and route.get("parent_trace_id") == parent_trace_id
            and route.get("task_sha256") == expected_task_sha256
            and route.get("query_hash") == expected_task_sha256
            and route.get("binding_kind") == "child_id"
            and route.get("binding_id") == route.get("launch_id")
            and isinstance(cards, list)
            and len(cards) == 1
            and isinstance(cards[0], Mapping)
            and cards[0].get("specialist_slug") == "code-reviewer"
        )
        else None
    )


def _restricted_codex_canary_artifact(
    root: Path,
    *,
    child_id: str,
) -> Path | None:
    """Resolve one canonical child rollout by its host-authenticated UUID."""

    try:
        canonical_root = absolute_path(root)
        assert_storage_parent_chain(canonical_root, allow_missing=False)
        if not storage_artifact_parent_is_trusted(
            canonical_root,
            is_windows=os.name == "nt",
        ):
            return None
        matches = list(canonical_root.glob(f"*/*/*/rollout-*-{child_id}.jsonl"))
    except (OSError, RuntimeError, ValueError):
        return None
    return matches[0] if len(matches) == 1 else None


def _verify_restricted_codex_canary_child_delivery(
    store: object,
    *,
    parent_session_id: str,
    parent_trace_id: str,
    accepted_terminal_parent: bool = False,
    started_at_ns: int | None = None,
    finished_at_ns: int | None = None,
    root: Path | None = None,
) -> ChildDeliveryEvidence | None:
    """Verify the sole current-profile canary child rollout and persist receipt."""

    route = _restricted_codex_canary_route(
        store,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        accepted_terminal_parent=accepted_terminal_parent,
    )
    if route is None:
        return None
    child_id = str(route.get("binding_id") or "")
    try:
        # Codex thread UUIDs are the host-owned identity joined by the rollout
        # filename and session_meta record. Correlation IDs alone are broader.
        from uuid import UUID

        if str(UUID(child_id)) != child_id:
            return None
    except (AttributeError, TypeError, ValueError):
        return None
    root = default_child_artifact_root("codex") if root is None else absolute_path(root)
    artifact = _restricted_codex_canary_artifact(root, child_id=child_id)
    if artifact is None:
        return None
    try:
        metadata = artifact.lstat()
    except OSError:
        return None
    if (started_at_ns is not None or finished_at_ns is not None) and (
        type(started_at_ns) is not int
        or type(finished_at_ns) is not int
        or started_at_ns <= 0
        or finished_at_ns < started_at_ns
        or int(getattr(metadata, "st_mtime_ns", 0) or 0) + 1_000_000_000 < started_at_ns
        or int(getattr(metadata, "st_mtime_ns", 0) or 0) > finished_at_ns + 1_000_000_000
    ):
        return None
    diagnostic = _codex_child_delivery_evidence(
        artifact,
        structural_hook_output=True,
    )
    if not (
        diagnostic is not None
        and diagnostic.v6_delivery
        and diagnostic.child_id == child_id
        and diagnostic.host_parent_id == parent_session_id
        and diagnostic.parent_trace_id == parent_trace_id
        and diagnostic.decision_id == route.get("decision_id")
        and diagnostic.launch_id == child_id
        and diagnostic.binding_kind == "child_id"
        and diagnostic.binding_id == child_id
        and diagnostic.task_sha256 == route.get("task_sha256")
        and _canonical_host_artifact_is_trusted(
            artifact,
            host="codex",
            root=root,
            evidence=diagnostic,
        )
    ):
        return None
    if started_at_ns is not None and finished_at_ns is not None:
        observed = _utc_timestamp(diagnostic.host_event_at)
        if observed is None:
            return None
        observed_ns = int(observed.timestamp() * 1_000_000_000)
        if not (
            observed_ns + 1_000_000_000 >= started_at_ns
            and observed_ns <= finished_at_ns + 1_000_000_000
        ):
            return None
    expected = _expected_delivery_from_store_decision(
        route,
        decision_id=diagnostic.decision_id,
        child_id=child_id,
        artifact_digest=diagnostic.artifact_digest,
    )
    if expected is None:
        return None
    _decision_getter, receipt_getter = _store_delivery_methods(store)
    if isinstance(receipt_getter(diagnostic.decision_id), Mapping):
        verified = _verify_against_persisted_receipt(
            artifact,
            host="codex",
            diagnostic=diagnostic,
            store=store,
            structural_hook_output=True,
        )
    else:
        verified = _verify_child_delivery_evidence(
            artifact,
            host="codex",
            expected=expected,
            verification_consumer=_store_native_child_delivery_consumer(store),
            structural_hook_output=True,
        )
        if (verified is None or not verified.staffed) and isinstance(
            receipt_getter(diagnostic.decision_id), Mapping
        ):
            verified = _verify_against_persisted_receipt(
                artifact,
                host="codex",
                diagnostic=diagnostic,
                store=store,
                structural_hook_output=True,
            )
    return verified if verified is not None and verified.staffed else None


def _collect_restricted_codex_canary_child_delivery(
    store: object,
    *,
    parent_session_id: str,
    parent_trace_id: str,
) -> ChildDeliveryEvidence | None:
    """Hook-only current-profile verifier for the exact restricted canary."""

    from agency_runtime.core.codex_activation_verification import (
        is_restricted_codex_activation_canary_environment,
    )

    if not is_restricted_codex_activation_canary_environment(os.environ):
        return None
    return _verify_restricted_codex_canary_child_delivery(
        store,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
    )


def _collect_restricted_codex_canary_host_delivery(
    store: object,
    *,
    parent_session_id: str,
    parent_trace_id: str,
    started_at_ns: int,
    finished_at_ns: int,
    root: Path,
) -> HostChildCollection:
    """Backend-only sealed proof for one exact current-profile invocation."""

    verified = _verify_restricted_codex_canary_child_delivery(
        store,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        accepted_terminal_parent=True,
        started_at_ns=started_at_ns,
        finished_at_ns=finished_at_ns,
        root=root,
    )
    if verified is None:
        return _uncollected("verification_refused")
    proof = _VerifiedHostChildDelivery(
        evidence=verified,
        _consumption_scope="single",
        _seal=_VERIFIED_DELIVERY_SEAL,
    )
    with _VERIFIED_DELIVERY_LOCK:
        _VERIFIED_DELIVERY_IDENTITIES[id(proof)] = proof
    return HostChildCollection(proof=proof, reason="collected")


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


def child_delivery_evidence(
    path: Path,
    *,
    host: str,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
) -> ChildDeliveryEvidence | None:
    """Read one child artifact for the exact host that wrote it."""

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        return claude_child_delivery_evidence(
            Path(path),
            expected_deliveries=expected_deliveries,
            verification_consumer=verification_consumer,
        )
    if normalized == "codex":
        return codex_child_delivery_evidence(
            Path(path),
            expected_deliveries=expected_deliveries,
            verification_consumer=verification_consumer,
        )
    raise ValueError("child delivery evidence host is unsupported")


def _verify_child_delivery_evidence(
    path: Path,
    *,
    host: str,
    expected: _ExpectedChildDelivery,
    verification_consumer: _NativeChildDeliveryVerificationConsumer,
    structural_hook_output: bool = False,
) -> ChildDeliveryEvidence | None:
    """Verify one exact artifact through an injected atomic persistence seam.

    Merely constructing ``_ExpectedChildDelivery`` cannot green evidence. The
    consumer must independently validate and atomically consume the exact
    decision, nonce, launch, child, and bounded artifact-window identity.
    """

    if not isinstance(expected, _ExpectedChildDelivery):
        raise TypeError("expected child delivery must use the exact contract")
    if not callable(verification_consumer):
        raise TypeError("native child delivery verification consumer is required")
    if host == "codex":
        return _codex_child_delivery_evidence(
            path,
            expected_deliveries={expected.child_id: expected},
            verification_consumer=verification_consumer,
            structural_hook_output=structural_hook_output,
        )
    return child_delivery_evidence(
        path,
        host=host,
        expected_deliveries={expected.child_id: expected},
        verification_consumer=verification_consumer,
    )


def _verify_child_delivery_with_capability(
    path: Path,
    *,
    collection: _PrivateHostArtifactCollection,
    store: object,
) -> ChildDeliveryEvidence | None:
    """Verify under the fresh-root capability held by the safe backend.

    The first read derives the child, artifact digest, and decision identity only
    from the host-written artifact. The Store supplies the immutable expectation.
    A second trusted read must still match before the Store consumer can persist
    the one-use receipt. An exact receipt already present is re-projected through
    a read-only consumer; it is never inserted again.
    """

    if not isinstance(collection, _PrivateHostArtifactCollection):
        raise TypeError("private host artifact collection capability is required")
    if collection._seal is not _PRIVATE_COLLECTION_SEAL:
        raise TypeError("private host artifact collection capability is invalid")
    artifact = Path(path)
    normalized = collection.host
    canonical_root = collection.root
    try:
        if not same_file_identity(collection.root_metadata, canonical_root.lstat()):
            return None
    except OSError:
        return None
    diagnostic = child_delivery_evidence(artifact, host=normalized)
    if diagnostic is None or not diagnostic.v6_delivery:
        return diagnostic
    if not _artifact_is_in_bounded_scan(
        artifact,
        host=normalized,
        root=canonical_root,
    ):
        return replace(diagnostic, verification_reason="artifact_not_in_bounded_host_scan")
    if not _canonical_host_artifact_is_trusted(
        artifact,
        host=normalized,
        root=canonical_root,
        evidence=diagnostic,
    ):
        return replace(diagnostic, verification_reason="artifact_origin_not_canonical")
    if normalized == "codex":
        # The authenticated Codex profiles' opaque inter-agent channel has no
        # attributable hook output. Preserve that explicit diagnostic and never
        # consult the Store in a way that could turn it green.
        return diagnostic
    decision_getter, receipt_getter = _store_delivery_methods(store)
    expected = _expected_delivery_from_store_decision(
        decision_getter(diagnostic.decision_id),
        decision_id=diagnostic.decision_id,
        child_id=diagnostic.child_id,
        artifact_digest=diagnostic.artifact_digest,
    )
    if expected is None:
        return replace(diagnostic, verification_reason="expected_decision_not_found_or_invalid")
    receipt = receipt_getter(diagnostic.decision_id)
    if isinstance(receipt, Mapping):
        return _verify_against_persisted_receipt(
            artifact,
            host=normalized,
            diagnostic=diagnostic,
            store=store,
        )

    verified = _verify_child_delivery_evidence(
        artifact,
        host=normalized,
        expected=expected,
        verification_consumer=_store_native_child_delivery_consumer(store),
    )
    if verified is not None and verified.staffed:
        return verified

    # A concurrent exact verifier may have inserted between the read and the
    # attempted consume. Re-read once and accept only the same immutable receipt.
    if isinstance(receipt_getter(diagnostic.decision_id), Mapping):
        return _verify_against_persisted_receipt(
            artifact,
            host=normalized,
            diagnostic=diagnostic,
            store=store,
        )
    return verified


def _reject_duplicate_verified_deliveries(
    findings: list[ChildDeliveryEvidence],
) -> list[ChildDeliveryEvidence]:
    """Demote every repeated nonce or artifact identity in the bounded window."""

    nonces: dict[str, int] = {}
    artifacts: dict[str, int] = {}
    for finding in findings:
        if not finding.v6_delivery:
            continue
        nonces[finding.nonce] = nonces.get(finding.nonce, 0) + 1
        artifacts[finding.artifact_digest] = artifacts.get(finding.artifact_digest, 0) + 1
    return [
        replace(
            finding,
            verified_delivery=False,
            verification_reason="replayed_nonce_or_artifact",
        )
        if finding.verified_delivery
        and (nonces.get(finding.nonce, 0) != 1 or artifacts.get(finding.artifact_digest, 0) != 1)
        else finding
        for finding in findings
    ]


def scan_child_delivery_evidence(
    root: Path,
    *,
    host: str,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
) -> list[ChildDeliveryEvidence]:
    """Read every child artifact one host wrote beneath *root*."""

    scan = scan_child_artifacts(root, host=host)
    findings = []
    for artifact in scan.artifacts:
        evidence = child_delivery_evidence(
            artifact,
            host=host,
            expected_deliveries=expected_deliveries,
        )
        if evidence is not None:
            findings.append(evidence)
    return _reject_duplicate_verified_deliveries(findings)


def scan_child_artifacts(root: Path, *, host: str) -> ChildArtifactScan:
    """Return one host's bounded newest candidate window without reading bodies."""

    normalized = str(host or "").strip().casefold()
    if normalized == "claude":
        return _bounded_matches(Path(root), "claude")
    elif normalized == "codex":
        return _bounded_matches(Path(root), "codex")
    else:
        raise ValueError("child delivery evidence host is unsupported")


def _begin_private_host_artifact_collection(
    lease: _PrivateTemporaryDirectoryLease,
    *,
    host: str,
) -> _PrivateHostArtifactCollection:
    """Capture one empty private host namespace immediately before invocation.

    This is an internal safe-backend capability, not a general path verifier.
    The real-profile roots selected by environment variables and the CLI's
    caller-selected read roots deliberately cannot enter this write boundary.
    """

    normalized = str(host or "").strip().casefold()
    if normalized != "claude":
        raise ValueError("private host artifact collection currently supports Claude only")
    if not _private_temporary_lease_is_current(lease):
        raise ValueError("active private temporary lease is required")
    canonical_root = absolute_path(lease.path / "claude" / "projects")
    try:
        canonical_root.parent.mkdir(mode=0o700, exist_ok=True)
        canonical_root.mkdir(mode=0o700)
        assert_storage_parent_chain(canonical_root, allow_missing=False)
        metadata = canonical_root.lstat()
    except (OSError, ValueError) as exc:
        raise ValueError("private host artifact root is unavailable") from exc
    if (
        metadata_is_link_or_reparse_point(metadata)
        or not stat.S_ISDIR(metadata.st_mode)
        or not storage_parent_is_trusted(canonical_root, is_windows=os.name == "nt")
    ):
        raise ValueError("private host artifact root is not trusted")
    scan = scan_child_artifacts(canonical_root, host=normalized)
    if not scan.root_present or scan.truncated or scan.candidate_count != 0 or scan.artifacts:
        raise ValueError("private host artifact root was not fresh and empty")
    return _PrivateHostArtifactCollection(
        host=normalized,
        lease=lease,
        root=canonical_root,
        root_metadata=metadata,
        started_at_ns=time.time_ns(),
        _seal=_PRIVATE_COLLECTION_SEAL,
    )


def _start_private_host_invocation(
    collection: _PrivateHostArtifactCollection,
) -> _HostInvocationStart:
    """Capture an empty namespace immediately before the real process call."""

    if not isinstance(collection, _PrivateHostArtifactCollection):
        raise TypeError("private host artifact collection capability is required")
    if collection._seal is not _PRIVATE_COLLECTION_SEAL or not _private_temporary_lease_is_current(
        collection.lease
    ):
        raise TypeError("private host artifact collection capability is invalid")
    scan = scan_child_artifacts(collection.root, host=collection.host)
    if not scan.root_present or scan.truncated or scan.candidate_count != 0 or scan.artifacts:
        raise ValueError("private host artifact root changed before invocation")
    start = _HostInvocationStart(
        collection=collection,
        started_at_ns=time.time_ns(),
        _seal=_PRIVATE_COLLECTION_SEAL,
    )
    with _VERIFIED_DELIVERY_LOCK:
        _HOST_INVOCATION_IDENTITIES[id(start)] = start
    return start


def _finish_private_host_invocation(
    start: _HostInvocationStart,
) -> _HostInvocationWindow:
    """Close one exact, one-use real-process interval retained by the backend."""

    with _VERIFIED_DELIVERY_LOCK:
        if (
            type(start) is not _HostInvocationStart
            or start._seal is not _PRIVATE_COLLECTION_SEAL
            or _HOST_INVOCATION_IDENTITIES.get(id(start)) is not start
        ):
            raise TypeError("matching live host invocation start is required")
        _HOST_INVOCATION_IDENTITIES.pop(id(start), None)
    return _HostInvocationWindow(
        collection=start.collection,
        started_at_ns=start.started_at_ns,
        finished_at_ns=time.time_ns(),
        _seal=_PRIVATE_COLLECTION_SEAL,
    )


def _collected_host_root(
    collection: _PrivateHostArtifactCollection,
) -> str:
    """Confirm the private namespace is still the one that was captured."""

    try:
        current_root = collection.root.lstat()
    except OSError:
        return "host_root_changed"
    if (
        not same_file_identity(collection.root_metadata, current_root)
        or metadata_is_link_or_reparse_point(current_root)
        or not stat.S_ISDIR(current_root.st_mode)
        or not storage_parent_is_trusted(collection.root, is_windows=os.name == "nt")
    ):
        return "host_root_changed"
    return ""


def _sole_window_artifact(
    collection: _PrivateHostArtifactCollection,
    *,
    invocation: _HostInvocationWindow,
) -> tuple[str, Path | None]:
    """Return the one artifact this invocation wrote, or why there is not one.

    ``multiple_child_artifacts`` is a real and expected outcome, not a corrupt
    namespace: a host that fans a task out to several children writes one
    transcript each. Collection still refuses, because "the artifact this
    invocation produced" has no answer then -- but it now says so.
    """

    scan = scan_child_artifacts(collection.root, host=collection.host)
    if not scan.root_present or scan.truncated:
        return "artifact_scan_incomplete", None
    if scan.candidate_count == 0:
        return "no_child_artifact", None
    if scan.candidate_count != 1 or len(scan.artifacts) != 1:
        return "multiple_child_artifacts", None
    artifact = scan.artifacts[0]
    try:
        metadata = artifact.lstat()
    except OSError:
        return "artifact_unreadable", None
    # The file timestamp and host-authored event must both fall inside the exact
    # real-process interval. Destination mtime alone would allow an old artifact
    # copied into a fresh directory to replay a still-unconsumed Store decision.
    modified_ns = int(getattr(metadata, "st_mtime_ns", 0) or 0)
    if not _within_invocation(modified_ns, invocation):
        return "artifact_outside_invocation_window", None
    return "", artifact


def _window_pair_artifacts(
    collection: _PrivateHostArtifactCollection,
    *,
    invocation: _HostInvocationWindow,
) -> tuple[str, tuple[Path, ...]]:
    """Return exactly two artifacts created inside one host invocation."""

    scan = scan_child_artifacts(collection.root, host=collection.host)
    if not scan.root_present or scan.truncated:
        return "artifact_scan_incomplete", ()
    if scan.candidate_count != 2 or len(scan.artifacts) != 2:
        return "expected_two_child_artifacts", ()
    for artifact in scan.artifacts:
        try:
            metadata = artifact.lstat()
        except OSError:
            return "artifact_unreadable", ()
        modified_ns = int(getattr(metadata, "st_mtime_ns", 0) or 0)
        if not _within_invocation(modified_ns, invocation):
            return "artifact_outside_invocation_window", ()
    return "", scan.artifacts


def _within_invocation(moment_ns: int, invocation: _HostInvocationWindow) -> bool:
    clock_skew_ns = 1_000_000_000
    return (
        moment_ns + clock_skew_ns >= invocation.started_at_ns
        and moment_ns <= invocation.finished_at_ns + clock_skew_ns
    )


def _readable_v6_delivery(
    artifact: Path,
    *,
    collection: _PrivateHostArtifactCollection,
    invocation: _HostInvocationWindow,
) -> tuple[str, ChildDeliveryEvidence | None]:
    """Read one artifact for a current, canonical, pre-speech v6 delivery."""

    if _trusted_launch_prefix_bytes(artifact, label="host child artifact") is None:
        # Classification only: these bytes are discarded, and the authoritative
        # read still happens inside ``child_delivery_evidence`` below, so this
        # adds no new trust surface. It only separates "the guard refused the
        # file" -- ownership, link shape, parent chain -- from "the file was
        # read and carried no card", which have opposite fixes.
        return "artifact_not_trusted", None
    diagnostic = child_delivery_evidence(artifact, host=collection.host)
    if diagnostic is None:
        return "delivery_marker_absent", None
    if not diagnostic.v6_delivery:
        return (
            "legacy_delivery_not_authoritative"
            if diagnostic.legacy_delivery
            else "delivery_marker_absent"
        ), None
    if not _canonical_host_artifact_is_trusted(
        artifact,
        host=collection.host,
        root=collection.root,
        evidence=diagnostic,
    ):
        return "artifact_origin_not_canonical", None
    observed = _utc_timestamp(diagnostic.host_event_at)
    if observed is None:
        return "child_event_timestamp_invalid", None
    if not _within_invocation(int(observed.timestamp() * 1_000_000_000), invocation):
        return "child_event_outside_invocation_window", None
    return "", diagnostic


_ACCEPTED_OUTCOME_RESULT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "recorded",
        "promoted",
        "reason",
        "event_id",
        "worker_id",
        "accepted_outcome_key",
        "artifact_digest",
    }
)


def _accepted_outcome_result_is_valid(result: object) -> bool:
    if not isinstance(result, Mapping) or set(result) != _ACCEPTED_OUTCOME_RESULT_FIELDS:
        return False
    reason = result.get("reason")
    recorded = result.get("recorded")
    promoted = result.get("promoted")
    if (
        reason not in ACCEPTANCE_REASONS
        or type(recorded) is not bool
        or type(promoted) is not bool
        or any(
            not isinstance(result.get(field), str)
            for field in (
                "event_id",
                "worker_id",
                "accepted_outcome_key",
                "artifact_digest",
            )
        )
    ):
        return False
    if reason in {"accepted", "replayed"}:
        return bool(
            recorded is (reason == "accepted")
            and (reason == "accepted" or promoted is False)
            and result.get("event_id")
            and result.get("worker_id")
            and re.fullmatch(r"[0-9a-f]{64}", result["accepted_outcome_key"])
            and re.fullmatch(r"[0-9a-f]{64}", result["artifact_digest"])
        )
    return bool(
        recorded is False
        and promoted is False
        and not result["event_id"]
        and not result["accepted_outcome_key"]
        and not result["artifact_digest"]
    )


def _accepted_outcome_result_matches_evaluation(
    result: object,
    evaluated: AcceptanceOutcome,
) -> bool:
    """Bind the Store's terminal projection back to this exact envelope."""

    if not _accepted_outcome_result_is_valid(result) or not isinstance(result, Mapping):
        return False
    expected_reasons = (
        {"accepted", "replayed", "contractor_identity_mismatch"}
        if evaluated.accepted
        else {evaluated.reason}
    )
    if result["reason"] not in expected_reasons:
        return False
    if result["reason"] == "contractor_identity_mismatch":
        return result["worker_id"] == evaluated.contractor_worker_id
    return not evaluated.accepted or (
        result["worker_id"] == evaluated.contractor_worker_id
        and result["accepted_outcome_key"] == evaluated.outcome_key
        and result["artifact_digest"] == evaluated.artifact_digest
    )


def _verdict_identity(
    *,
    pair_id: str,
    verifier: _VerifiedHostChildDelivery,
) -> str:
    semantic = verifier._semantic
    if semantic is None:  # pragma: no cover - enforced by the sealed capability
        return ""
    material = "\0".join(
        (
            _VERIFIER_SEMANTIC_SCHEMA,
            pair_id,
            verifier.evidence.child_id,
            semantic.artifact_digest,
            str(semantic.record_index),
            semantic.decision,
        )
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _record_verified_host_child_pair_outcome(
    capabilities: tuple[_VerifiedHostChildDelivery, _VerifiedHostChildDelivery],
    *,
    store: object,
    auto_promote_successes: int | None,
    disabled_agents: frozenset[str] | None,
) -> _HostAcceptedOutcomeCollection:
    """Consume exactly two pair-scoped capabilities around one Store call.

    The shared lock is the in-memory transaction boundary: neither member can
    be singly consumed, a concurrent pair consumer cannot split them, and both
    identities are removed only after the Store returns its bounded terminal
    result. No mapping or general callback can enter this path.
    """

    if type(capabilities) is not tuple or len(capabilities) != 2:
        return _uncollected_outcome("capability_pair_invalid")
    with _VERIFIED_DELIVERY_LOCK:
        if capabilities[0] is capabilities[1] or any(
            type(value) is not _VerifiedHostChildDelivery
            or value._seal is not _VERIFIED_DELIVERY_SEAL
            or value._consumption_scope != "pair"
            or _VERIFIED_DELIVERY_IDENTITIES.get(id(value)) is not value
            for value in capabilities
        ):
            return _uncollected_outcome("capability_pair_invalid")
        by_role = {value._pair_role: value for value in capabilities}
        if set(by_role) != {"producer", "verifier"}:
            return _uncollected_outcome("capability_pair_invalid")
        producer = by_role["producer"]
        verifier = by_role["verifier"]
        pair_id = producer._pair_id
        if not pair_id or pair_id != verifier._pair_id:
            return _uncollected_outcome("pair_identity_mismatch")
        producer_proof = _host_child_delivery_projection(producer.evidence)
        verifier_proof = _host_child_delivery_projection(verifier.evidence)
        if producer_proof is None or verifier_proof is None:
            return _uncollected_outcome("capability_pair_invalid")
        cards = producer_proof.get("cards")
        if not isinstance(cards, list) or len(cards) != 1 or not isinstance(cards[0], Mapping):
            return _uncollected_outcome("producer_cardinality_invalid")
        contractor_card = dict(cards[0])
        contractor_slug = contractor_card.get("specialist_slug")
        worker_getter = getattr(store, "get_workforce_worker", None)
        recorder = getattr(store, "record_accepted_outcome", None)
        if not callable(worker_getter) or not callable(recorder):
            return _uncollected_outcome("outcome_store_unavailable")
        try:
            worker = worker_getter(contractor_slug, disabled_agents=disabled_agents)
        except KeyError:
            return _uncollected_outcome("contractor_worker_missing")
        except Exception:
            return _uncollected_outcome("outcome_store_failed")
        if not isinstance(worker, Mapping) or not isinstance(worker.get("worker_id"), str):
            return _uncollected_outcome("outcome_store_invalid")
        semantic = verifier._semantic
        if semantic is None:
            return _uncollected_outcome("capability_pair_invalid")
        envelope = {
            "schema": ACCEPTANCE_ENVELOPE_SCHEMA,
            "contractor_worker_id": worker["worker_id"],
            "contractor_card": contractor_card,
            "producer": producer_proof,
            "verifier": verifier_proof,
            "verdict": {
                "verdict_id": _verdict_identity(pair_id=pair_id, verifier=verifier),
                "semantic": {
                    "authority": "verifier-host-artifact",
                    "artifact_digest": semantic.artifact_digest,
                    "record_index": semantic.record_index,
                    "pair_id": pair_id,
                    "decision": semantic.decision,
                },
                "binding": {
                    "authority": "collector",
                    "producer_artifact_digest": producer.evidence.artifact_digest,
                    "verifier_child_id": verifier.evidence.child_id,
                    "pair_id": pair_id,
                },
            },
        }
        evaluated = evaluate_acceptance(envelope)
        try:
            result = recorder(
                envelope=envelope,
                auto_promote_successes=auto_promote_successes,
                disabled_agents=disabled_agents,
            )
        except Exception:
            return _uncollected_outcome("outcome_store_failed")
        if not _accepted_outcome_result_matches_evaluation(result, evaluated):
            return _uncollected_outcome("outcome_store_invalid")
        for value in capabilities:
            _VERIFIED_DELIVERY_IDENTITIES.pop(id(value), None)
        return _HostAcceptedOutcomeCollection(
            result=dict(result),
            reason=str(result["reason"]),
            pair_id=pair_id,
            producer_decision_id=producer.evidence.decision_id,
            verifier_decision_id=verifier.evidence.decision_id,
        )


def _collect_private_host_accepted_outcome(  # noqa: C901 - one fail-closed evidence boundary
    collection: _PrivateHostArtifactCollection,
    *,
    invocation: _HostInvocationWindow,
    store: object,
    auto_promote_successes: int | None = None,
    disabled_agents: frozenset[str] | None = None,
    expected_provider: str | None = None,
) -> _HostAcceptedOutcomeCollection:
    """Collect exactly one producer/verifier pair from an isolated Claude run."""

    if not isinstance(collection, _PrivateHostArtifactCollection):
        raise TypeError("private host artifact collection capability is required")
    if collection._seal is not _PRIVATE_COLLECTION_SEAL:
        raise TypeError("private host artifact collection capability is invalid")
    if expected_provider is not None and (
        type(expected_provider) is not str
        or not expected_provider
        or len(expected_provider) > 128
        or any(ord(character) < 32 or ord(character) == 127 for character in expected_provider)
    ):
        raise ValueError("expected child judge provider is invalid")
    if (
        not isinstance(invocation, _HostInvocationWindow)
        or invocation._seal is not _PRIVATE_COLLECTION_SEAL
        or invocation.collection is not collection
        or not _private_temporary_lease_is_current(collection.lease)
    ):
        raise TypeError("matching host invocation window is required")
    reason = _collected_host_root(collection)
    if reason:
        return _uncollected_outcome(reason)
    reason, artifacts = _window_pair_artifacts(collection, invocation=invocation)
    if reason:
        return _uncollected_outcome(reason)

    pair_members: list[tuple[ChildDeliveryEvidence, _OutcomePairArtifact]] = []
    for artifact in artifacts:
        reason, diagnostic = _readable_v6_delivery(
            artifact,
            collection=collection,
            invocation=invocation,
        )
        if diagnostic is None:
            return _uncollected_outcome(reason)
        verified = _verify_child_delivery_with_capability(
            artifact,
            collection=collection,
            store=store,
        )
        if verified is None or not verified.staffed:
            refusal = verified.verification_reason if verified is not None else ""
            return _uncollected_outcome(
                refusal if refusal in _PROMOTED_VERIFICATION_REASONS else "verification_refused"
            )
        reason, pair_artifact = _outcome_pair_artifact(
            artifact,
            evidence=verified,
            invocation=invocation,
        )
        if pair_artifact is None:
            return _uncollected_outcome(reason)
        pair_members.append((verified, pair_artifact))

    roles = {member.role for _evidence, member in pair_members}
    pair_ids = {member.pair_id for _evidence, member in pair_members}
    if roles != {"producer", "verifier"} or len(pair_ids) != 1:
        return _uncollected_outcome("pair_identity_mismatch")
    producer_evidence = next(
        evidence for evidence, member in pair_members if member.role == "producer"
    )
    if len(producer_evidence.cards) != 1:
        return _uncollected_outcome("producer_cardinality_invalid")
    if expected_provider is not None:
        getter = getattr(store, "get_native_child_staffing_decision", None)
        if not callable(getter):
            return _uncollected_outcome("provider_pin_mismatch")
        for evidence, _member in pair_members:
            route = getter(evidence.decision_id)
            attempts = route.get("provider_attempts") if isinstance(route, Mapping) else None
            applied = (
                [
                    attempt.get("provider_name")
                    for attempt in attempts
                    if isinstance(attempt, Mapping) and attempt.get("status") == "applied"
                ]
                if isinstance(attempts, list)
                else []
            )
            if applied != [expected_provider]:
                return _uncollected_outcome("provider_pin_mismatch")

    capabilities = tuple(
        _VerifiedHostChildDelivery(
            evidence=evidence,
            _consumption_scope="pair",
            _seal=_VERIFIED_DELIVERY_SEAL,
            _pair_id=member.pair_id,
            _pair_role=member.role,
            _semantic=member.semantic,
        )
        for evidence, member in pair_members
    )
    assert len(capabilities) == 2
    typed_capabilities = (capabilities[0], capabilities[1])
    with _VERIFIED_DELIVERY_LOCK:
        for capability in typed_capabilities:
            _VERIFIED_DELIVERY_IDENTITIES[id(capability)] = capability
    try:
        return _record_verified_host_child_pair_outcome(
            typed_capabilities,
            store=store,
            auto_promote_successes=auto_promote_successes,
            disabled_agents=disabled_agents,
        )
    finally:
        for capability in typed_capabilities:
            _discard_verified_host_child_delivery(capability)


def _collect_private_host_child_delivery(
    collection: _PrivateHostArtifactCollection,
    *,
    invocation: _HostInvocationWindow,
    store: object,
) -> HostChildCollection:
    """Consume one exact newly written host artifact while its home is alive.

    Exactly one bounded child artifact must have appeared in the previously
    empty namespace.  Discovery must be complete, the file must have the host's
    canonical child shape and private ownership, and the immutable inference
    decision plus one-use Store consumer must agree before the sealed proof is
    constructed.  No backend mapping participates in this transition.

    Every refusal returns a bounded reason naming the stage that refused.
    """

    if not isinstance(collection, _PrivateHostArtifactCollection):
        raise TypeError("private host artifact collection capability is required")
    if collection._seal is not _PRIVATE_COLLECTION_SEAL:
        raise TypeError("private host artifact collection capability is invalid")
    if (
        not isinstance(invocation, _HostInvocationWindow)
        or invocation._seal is not _PRIVATE_COLLECTION_SEAL
        or invocation.collection is not collection
        or not _private_temporary_lease_is_current(collection.lease)
    ):
        raise TypeError("matching host invocation window is required")
    reason = _collected_host_root(collection)
    if reason:
        return _uncollected(reason)
    reason, artifact = _sole_window_artifact(collection, invocation=invocation)
    if artifact is None:
        return _uncollected(reason)
    reason, diagnostic = _readable_v6_delivery(
        artifact,
        collection=collection,
        invocation=invocation,
    )
    if diagnostic is None:
        return _uncollected(reason)
    verified = _verify_child_delivery_with_capability(
        artifact,
        collection=collection,
        store=store,
    )
    if verified is None or not verified.staffed:
        refusal = verified.verification_reason if verified is not None else ""
        return _uncollected(
            refusal if refusal in _PROMOTED_VERIFICATION_REASONS else "verification_refused"
        )
    proof = _VerifiedHostChildDelivery(
        evidence=verified,
        _consumption_scope="single",
        _seal=_VERIFIED_DELIVERY_SEAL,
    )
    with _VERIFIED_DELIVERY_LOCK:
        _VERIFIED_DELIVERY_IDENTITIES[id(proof)] = proof
    return HostChildCollection(proof=proof, reason="collected")


def child_delivery_projection(
    root: Path,
    *,
    host: str,
    limit: int = 50,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    store: object | None = None,
) -> dict[str, Any]:
    """Project bounded, newest independent child-delivery proof for one host.

    An empty ``children`` list means no verified card-delivery proof was found
    in the bounded artifact window. It never means the host spawned no children.
    """

    normalized = str(host or "").strip().casefold()
    if expected_deliveries is not None and store is not None:
        raise ValueError("expected deliveries and Store receipt projection are mutually exclusive")
    if store is not None:
        _store_delivery_methods(store)
        if absolute_path(Path(root)) != absolute_path(default_child_artifact_root(normalized)):
            raise ValueError("Store-backed child projection requires the canonical host root")
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
        evidence = child_delivery_evidence(
            artifact,
            host=normalized,
            expected_deliveries=expected_deliveries,
        )
        if evidence is not None and evidence.v6_delivery and store is not None:
            if _canonical_host_artifact_is_trusted(
                artifact,
                host=normalized,
                root=Path(root),
                evidence=evidence,
            ):
                evidence = _verify_against_persisted_receipt(
                    artifact,
                    host=normalized,
                    diagnostic=evidence,
                    store=store,
                )
            else:
                evidence = replace(evidence, verification_reason="artifact_origin_not_canonical")
        if evidence is not None:
            findings.append(evidence)
    findings = _reject_duplicate_verified_deliveries(findings)
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
        "legacy_deliveries": sum(1 for item in findings if item.legacy_delivery),
        "verified_deliveries": len(staffed),
        "unverified_deliveries": sum(1 for item in findings if not item.staffed),
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
                "v6": finding.v6_delivery,
                "verified_delivery": finding.verified_delivery,
                "verification_reason": finding.verification_reason,
                "pre_speech": finding.pre_speech,
                "artifact_digest": finding.artifact_digest,
                "decision_id": finding.decision_id,
                "team_digest": finding.team_digest,
                "candidate_digest": finding.candidate_digest,
                "runtime_digest": finding.runtime_digest,
                "install_id": finding.install_id,
                "bundle_digest": finding.bundle_digest,
                "cards": [
                    {
                        "slug": card.specialist_slug,
                        "version": card.specialist_version,
                        "prompt_hash": card.specialist_prompt_hash,
                    }
                    for card in (finding.cards if finding.staffed else ())
                ],
                "diagnostic_cards": [
                    {
                        "slug": card.specialist_slug,
                        "version": card.specialist_version,
                        "prompt_hash": card.specialist_prompt_hash,
                        "body_character_length": card.body_character_length,
                    }
                    for card in finding.cards
                ],
            }
            for finding in details
        ],
    }


__all__ = [
    "HOST_CHILD_COLLECTION_REASONS",
    "MAX_CHILD_ARTIFACTS",
    "MAX_CHILD_DETAIL_RESULTS",
    "MAX_CHILD_FILESYSTEM_ENTRIES",
    "MAX_LAUNCH_PREFIX_BYTES",
    "MAX_LAUNCH_RECORDS",
    "ChildArtifactScan",
    "ChildDeliveryEvidence",
    "DeliveredCard",
    "HostChildCollection",
    "child_delivery_evidence",
    "child_delivery_projection",
    "claude_child_artifacts",
    "claude_child_delivery_evidence",
    "codex_child_artifacts",
    "codex_child_delivery_evidence",
    "codex_v1491_child_parent_session",
    "default_child_artifact_root",
    "scan_child_artifacts",
    "scan_child_delivery_evidence",
]
