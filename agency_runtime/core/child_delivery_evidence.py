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
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from hashlib import sha256
from heapq import heappush, heapreplace
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.bounded_io import read_bounded_regular_file_prefix
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
_V6_TEAM_TOKENS: Final[tuple[str, ...]] = (
    "[AGENCY INFERENCE TEAM v6]",
    "<!-- agency-native-child-team:v6:",
    "<!-- agency-native-child-team-end:v6:",
)
_CLAUDE_WORKFLOW_ID: Final[re.Pattern[str]] = re.compile(r"wf_[A-Za-z0-9_-]{1,124}\Z")


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


_PRIVATE_COLLECTION_SEAL = object()
_VERIFIED_DELIVERY_SEAL = object()
_VERIFIED_DELIVERY_IDENTITIES: dict[int, object] = {}
_HOST_INVOCATION_IDENTITIES: dict[int, object] = {}
_VERIFIED_DELIVERY_LOCK = threading.RLock()


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
class _VerifiedHostChildDelivery:
    """Sealed typed authority produced by the in-lifetime host collector.

    ``ChildDeliveryEvidence`` remains a useful diagnostic projection and can be
    reconstructed from public data.  Canary evaluation accepts this sealed type
    instead, so neither a plain mapping nor a freely constructed diagnostic can
    self-certify host authorship or pre-speech delivery.
    """

    evidence: ChildDeliveryEvidence
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _VERIFIED_DELIVERY_SEAL or not self.evidence.staffed:
            raise TypeError("verified host child delivery must come from the trusted collector")


def _consume_verified_host_child_delivery(
    value: object,
) -> dict[str, Any] | None:
    """Consume one collector-minted capability into its bounded proof once."""

    with _VERIFIED_DELIVERY_LOCK:
        if (
            type(value) is not _VerifiedHostChildDelivery
            or value._seal is not _VERIFIED_DELIVERY_SEAL
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


def _trusted_launch_prefix_bytes(path: Path, *, label: str) -> bytes | None:
    """Return the exact bounded bytes used to compute artifact identity."""

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
        return read_bounded_regular_file_prefix(
            path,
            limit=MAX_LAUNCH_PREFIX_BYTES,
            label=label,
        )
    except (OSError, ValueError):
        return None


def _trusted_launch_material(path: Path, *, label: str) -> tuple[str, str] | None:
    """Read and hash one exact trusted artifact window without a TOCTOU reread."""

    payload = _trusted_launch_prefix_bytes(path, label=label)
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
    if (
        metadata_is_link_or_reparse_point(root_before)
        or not stat.S_ISDIR(root_before.st_mode)
        or metadata_is_link_or_reparse_point(file_before)
        or not stat.S_ISREG(file_before.st_mode)
        or int(getattr(file_before, "st_nlink", 0) or 0) != 1
        or not storage_parent_is_trusted(canonical_root, is_windows=os.name == "nt")
        or not storage_parent_is_trusted(artifact.parent, is_windows=os.name == "nt")
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

    if host == "codex":
        # Codex 0.147 stores the delegated input as ordinary developer/user
        # records and carries the actual V2 inter-agent message opaquely. There
        # is no host-authored field identifying Agency's hook output.
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


def codex_child_delivery_evidence(
    path: Path,
    *,
    expected_deliveries: Mapping[str, _ExpectedChildDelivery] | None = None,
    verification_consumer: _NativeChildDeliveryVerificationConsumer | None = None,
) -> ChildDeliveryEvidence | None:
    """Read one Codex rollout, if it is a spawned child, for its launch cards.

    Codex writes one rollout per thread, so a child is identified by its own
    ``thread_spawn`` block rather than by the file's location.  Its launch input
    arrives as ordinary records ahead of anything the child said, so collection
    stops the moment the child speaks.
    """

    material = _trusted_launch_material(path, label="Codex child rollout")
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
    parts: list[str] = []
    input_timestamp = ""
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
                    if not input_timestamp:
                        input_timestamp = str(record.get("timestamp") or "")
    return _evidence(
        host="codex",
        path=path,
        child_id=child_id,
        host_parent_id=host_parent_id,
        launch_text="\n".join(parts),
        expected=expected,
        structural_hook_output=False,
        artifact_digest=artifact_digest,
        host_event_at=input_timestamp,
        verification_consumer=verification_consumer,
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
        # Codex 0.147's opaque inter-agent channel has no attributable hook
        # output. Preserve that explicit diagnostic and never consult the Store
        # in a way that could turn it green.
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


def _collect_private_host_child_delivery(
    collection: _PrivateHostArtifactCollection,
    *,
    invocation: _HostInvocationWindow,
    store: object,
) -> _VerifiedHostChildDelivery | None:
    """Consume one exact newly written host artifact while its home is alive.

    Exactly one bounded child artifact must have appeared in the previously
    empty namespace.  Discovery must be complete, the file must have the host's
    canonical child shape and private ownership, and the immutable inference
    decision plus one-use Store consumer must agree before the sealed proof is
    constructed.  No backend mapping participates in this transition.
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
    try:
        current_root = collection.root.lstat()
    except OSError:
        return None
    if (
        not same_file_identity(collection.root_metadata, current_root)
        or metadata_is_link_or_reparse_point(current_root)
        or not stat.S_ISDIR(current_root.st_mode)
        or not storage_parent_is_trusted(collection.root, is_windows=os.name == "nt")
    ):
        return None
    scan = scan_child_artifacts(collection.root, host=collection.host)
    if (
        not scan.root_present
        or scan.truncated
        or scan.candidate_count != 1
        or len(scan.artifacts) != 1
    ):
        return None
    artifact = scan.artifacts[0]
    try:
        metadata = artifact.lstat()
    except OSError:
        return None
    # The file timestamp and host-authored event must both fall inside the exact
    # real-process interval. Destination mtime alone would allow an old artifact
    # copied into a fresh directory to replay a still-unconsumed Store decision.
    modified_ns = int(getattr(metadata, "st_mtime_ns", 0) or 0)
    clock_skew_ns = 1_000_000_000
    if (
        modified_ns + clock_skew_ns < invocation.started_at_ns
        or modified_ns > invocation.finished_at_ns + clock_skew_ns
    ):
        return None
    diagnostic = child_delivery_evidence(artifact, host=collection.host)
    if (
        diagnostic is None
        or not diagnostic.v6_delivery
        or not _canonical_host_artifact_is_trusted(
            artifact,
            host=collection.host,
            root=collection.root,
            evidence=diagnostic,
        )
    ):
        return None
    observed = _utc_timestamp(diagnostic.host_event_at)
    if observed is None:
        return None
    observed_ns = int(observed.timestamp() * 1_000_000_000)
    if (
        observed_ns + clock_skew_ns < invocation.started_at_ns
        or observed_ns > invocation.finished_at_ns + clock_skew_ns
    ):
        return None
    verified = _verify_child_delivery_with_capability(
        artifact,
        collection=collection,
        store=store,
    )
    if verified is None or not verified.staffed:
        return None
    proof = _VerifiedHostChildDelivery(
        evidence=verified,
        _seal=_VERIFIED_DELIVERY_SEAL,
    )
    with _VERIFIED_DELIVERY_LOCK:
        _VERIFIED_DELIVERY_IDENTITIES[id(proof)] = proof
    return proof


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
