"""Bounded transient envelopes for hook-owned native-child prompt delivery.

The envelope travels only in a host-native child launch input.  Durable evidence
stores immutable prompt identities and one-use receipts, never prompt bodies or
bearer tokens.  Post-tool hooks re-parse the exact rewritten input and consume
the grant only after the native host proves that it executed the launch.
"""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.native_child_decision import MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS
from agency_runtime.core.roster.revisions import content_digest_identity, content_identity_matches
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.version_identity import normalize_version_identity

NATIVE_CHILD_PROMPT_DELIVERY_VERSION: Final[int] = 1
CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION: Final[int] = 2
CODEX_DIRECT_NATIVE_CHILD_PROMPT_DELIVERY_VERSION: Final[int] = 4
CODEX_NATIVE_CHILD_EXECUTION_VERSION: Final[int] = 1
# Just-in-time staffing of a child the host spawned on its own. Deliberately its own
# marker namespace so the planned-delivery parser can never match it and send an
# unplanned child down the plan-verification path.
JIT_SPECIALIST_DELIVERY_VERSION: Final[int] = 5
INFERENCE_TEAM_DELIVERY_VERSION: Final[int] = 6
MAX_INFERENCE_TEAM_CARDS: Final[int] = 3
MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES: Final[int] = 2_048
MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS: Final[int] = 256

_SECTION = (
    "\n\n[AGENCY EXACT SPECIALIST ACTIVATION v1]\n"
    "The host hook assigned the exact audited specialist below to this child only. "
    "Treat it as turn-scoped specialist instructions; do not copy it into the parent, "
    "another worker, status text, or the final response.\n"
)
_MARKER_PREFIX = "<!-- agency-native-child-delivery:v1:"
_MARKER_SUFFIX = " -->"
_MARKER_PATTERN = re.compile(
    re.escape(_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_CODEX_OPAQUE_SECTION = (
    "[AGENCY EXACT SPECIALIST ACTIVATION v2]\n"
    "The decrypted native child message is the exact work-unit goal, but this first "
    "spawn turn establishes specialist context only. Do not execute, analyze, or modify "
    "the workspace during this activation turn; return one bounded readiness "
    "acknowledgement. Execute the goal exactly once only when a later newest inter-agent "
    "task contains a valid [AGENCY EXACT TASK EXECUTION v1] envelope with the exact "
    "hash-bound goal matching this work-unit. Never recover an actionable goal from prior "
    "turn memory. Do not answer the specialist prompt as a standalone "
    "request. The host "
    "hook bound the exact audited specialist below and Store-backed mutation authority "
    "to that persisted work-unit row. Use workspace tools when the goal requires them; "
    "hook policy will enforce the exact scope. Treat the text below as turn-scoped "
    "specialist instructions; do not copy it into the parent, another worker, status "
    "text, or the final response.\n"
)
_CODEX_OPAQUE_MARKER_PREFIX = "<!-- agency-native-child-delivery:v2:"
_CODEX_OPAQUE_MARKER_PATTERN = re.compile(
    re.escape(_CODEX_OPAQUE_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_CODEX_DIRECT_SECTION = (
    "[AGENCY EXACT SPECIALIST ACTIVATION v4]\n"
    "The host hook bound the exact audited specialist below and Store-backed authority to "
    "this persisted work-unit row. Treat the text below as turn-scoped specialist expertise. "
    "Do not copy it into the parent, another worker, status text, or the final response.\n"
)
_CODEX_DIRECT_EXECUTION_SECTION = "[AGENCY EXACT WORK-UNIT EXECUTION CONTRACT v4]\n"
_CODEX_DIRECT_EXECUTION_INSTRUCTION = (
    "The decrypted native child message is the exact work-unit goal. Execute that goal "
    "exactly once now using the specialist expertise above. This current work-unit contract "
    "governs execution when a generic specialist preference conflicts with the exact accepted "
    "assignment. Use workspace tools when the goal requires them; the accepted plan and "
    "current native activation already prove the required host tools and exact isolated "
    "working directory. Report a missing prerequisite only after an actual required tool is "
    "absent or denied. Hook policy enforces the persisted mutation scope. A goal ending in "
    "`mutation_scope=workspace_write` is an action contract: before any final response, use "
    "`apply_patch` for the first required workspace mutation and require a successful "
    "workspace-local patch receipt. An exact proof-only named-file change is legitimate; do "
    "not reject it as arbitrary text or expand it into unrequested root-cause analysis, tests, "
    "or refactoring. Do not re-delegate, broaden, postpone, or convert this turn into a "
    "readiness ceremony. Return one bounded evidence-backed result."
)
_CODEX_DIRECT_EXECUTION_SUFFIX = (
    f"\n\n{_CODEX_DIRECT_EXECUTION_SECTION}{_CODEX_DIRECT_EXECUTION_INSTRUCTION}"
)
_CODEX_DIRECT_MARKER_PREFIX = "<!-- agency-native-child-delivery:v4:"
_CODEX_DIRECT_MARKER_PATTERN = re.compile(
    re.escape(_CODEX_DIRECT_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_CODEX_EXECUTION_SECTION = "[AGENCY EXACT TASK EXECUTION v1]\n"
_CODEX_EXECUTION_INSTRUCTION = (
    "Execute the exact work-unit goal included in this execution turn now. Do not "
    "re-delegate, broaden, or repeat it. Return one bounded evidence-backed result."
)
_CODEX_EXECUTION_GOAL_SECTION = "\n[AGENCY EXACT WORK-UNIT GOAL]\n"
_CODEX_EXECUTION_MARKER_PREFIX = "<!-- agency-native-child-execution:v1:"
_CODEX_EXECUTION_MARKER_PATTERN = re.compile(
    re.escape(_CODEX_EXECUTION_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_CODEX_OPAQUE_COLLABORATION_MESSAGE_PATTERN = re.compile(r"gAAAAA[A-Za-z0-9_-]{24,}={0,2}")
_V1_FIELDS = frozenset(
    {
        "version",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "tool_use_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "activation_token",
    }
)
_V2_FIELDS = frozenset(
    {
        "version",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "tool_use_id",
        "work_unit_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "goal_hash",
    }
)
_JIT_SECTION = (
    "\n\n[AGENCY JIT SPECIALIST v5]\n"
    "The host spawned this child on its own initiative, so Agency staffed it just in time. "
    "The audited specialist below was selected from the current assignment text and applies "
    "to this child only, for this turn only. Treat it as turn-scoped expertise, not as an "
    "instruction to re-delegate or to produce a lifecycle ceremony. There is no Agency "
    "activation grant and none is required: make no Agency delegation claim, consume no "
    "receipt, and do not copy this text into the parent, another worker, status text, or the "
    "final response. If it does not fit the work, ignore it and proceed normally.\n"
)
_JIT_MARKER_PREFIX = "<!-- agency-native-child-jit:v5:"
_JIT_MARKER_PATTERN = re.compile(
    re.escape(_JIT_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_JIT_FIELDS = frozenset(
    {
        "version",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "tool_use_id",
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
    }
)
_INFERENCE_TEAM_SECTION = (
    "\n\n[AGENCY INFERENCE TEAM v6]\n"
    "Inference selected the exact ordered specialist team below for this native child. "
    "The cards are one atomic, turn-scoped team: use all of them in order or none of "
    "them. Do not copy this context into the parent, another worker, status text, or "
    "the final response.\n"
)
_INFERENCE_TEAM_MARKER_PREFIX = "<!-- agency-native-child-team:v6:"
_INFERENCE_TEAM_MARKER_PATTERN = re.compile(
    re.escape(_INFERENCE_TEAM_MARKER_PREFIX) + r"([A-Za-z0-9_-]+)" + re.escape(_MARKER_SUFFIX)
)
_INFERENCE_TEAM_END_PREFIX = "<!-- agency-native-child-team-end:v6:"
_INFERENCE_TEAM_FIELDS = frozenset(
    {
        "version",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "decision_id",
        "provider_receipt_digest",
        "task_sha256",
        "candidate_digest",
        "install_id",
        "bundle_digest",
        "runtime_digest",
        "issued_at",
        "expires_at",
        "nonce",
        "binding_kind",
        "binding_id",
        "cards",
        "team_digest",
    }
)
_INFERENCE_TEAM_CARD_FIELDS = frozenset(
    {
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "body_character_length",
    }
)
_MIXED_NATIVE_CHILD_MARKER_PREFIXES = (
    _MARKER_PREFIX,
    _CODEX_OPAQUE_MARKER_PREFIX,
    _CODEX_DIRECT_MARKER_PREFIX,
    _CODEX_EXECUTION_MARKER_PREFIX,
    _JIT_MARKER_PREFIX,
)
_BINDING_KIND_PATTERN = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_CODEX_EXECUTION_FIELDS = frozenset({"version", "work_unit_id", "native_task_name", "goal_hash"})


@dataclass(frozen=True, slots=True)
class NativeChildPromptDelivery:
    """One exact hook-delivered specialist and its original native assignment."""

    host: str
    parent_session_id: str
    parent_trace_id: str
    tool_use_id: str
    work_unit_id: str
    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    activation_token: str
    goal_hash: str
    original_task: str
    prompt_body: str


@dataclass(frozen=True, slots=True)
class JitSpecialistDelivery:
    """One just-in-time specialist bound to a host-initiated child, with no grant."""

    host: str
    parent_session_id: str
    parent_trace_id: str
    tool_use_id: str
    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    original_task: str
    prompt_body: str


@dataclass(frozen=True, slots=True)
class InferenceTeamCard:
    """One exact immutable specialist card in an inference-selected team."""

    specialist_slug: str
    specialist_version: str
    specialist_prompt_hash: str
    prompt_body: str = field(repr=False)

    @property
    def body_character_length(self) -> int:
        """Return the exact Unicode character count bound into the envelope."""

        return len(self.prompt_body)


@dataclass(frozen=True, slots=True)
class InferenceTeamDelivery:
    """One integrity-bound, all-or-nothing inference staffing decision."""

    host: str
    parent_session_id: str
    parent_trace_id: str
    launch_id: str
    decision_id: str
    provider_receipt_digest: str
    task_sha256: str
    candidate_digest: str
    install_id: str
    bundle_digest: str
    runtime_digest: str
    issued_at: str
    expires_at: str
    nonce: str
    binding_kind: str
    binding_id: str
    team_digest: str
    original_task: str = field(compare=False, repr=False)
    cards: tuple[InferenceTeamCard, ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class CodexNativeChildExecutionDelivery:
    """One hash-bound second-turn authorization for an exact Codex child."""

    work_unit_id: str
    native_task_name: str
    goal_hash: str
    goal: str = field(default="", compare=False, repr=False)


def _encoded_metadata(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(payload) > MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES:
        raise ValueError("native-child delivery metadata exceeds its byte ceiling")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decoded_metadata(
    value: str,
    *,
    expected_fields: frozenset[str],
) -> dict[str, Any] | None:
    try:
        padding = "=" * (-len(value) % 4)
        payload = base64.b64decode(value + padding, altchars=b"-_", validate=True)
        if not payload or len(payload) > MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES:
            return None
        result = safe_load_bounded_json(
            payload,
            maximum_bytes=MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES,
            maximum_depth=4,
            maximum_nodes=64,
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(result, dict) or frozenset(result) != expected_fields:
        return None
    return result


def _sha256_text(value: str, *, field: str) -> str:
    try:
        return sha256(value.encode("utf-8")).hexdigest()
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be valid UTF-8 text") from exc


def _normalized_sha256(value: object, *, field: str) -> str:
    normalized = str(value or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return normalized


def _canonical_timestamp(value: object, *, field: str) -> tuple[str, datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.endswith("Z") else raw)
        except ValueError as exc:
            raise ValueError(f"{field} must be an RFC 3339 timestamp") from exc
    else:
        raise ValueError(f"{field} must be an RFC 3339 timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a UTC offset")
    utc = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if utc.microsecond else "seconds"
    return utc.isoformat(timespec=timespec).replace("+00:00", "Z"), utc


def _normalized_inference_team_card_metadata(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or frozenset(value) != _INFERENCE_TEAM_CARD_FIELDS:
        raise ValueError("inference team card metadata is malformed")
    slug = normalize_agent_slug(value.get("specialist_slug"))
    version = str(value.get("specialist_version") or "").strip()
    if not version or normalize_version_identity(version) != version:
        raise ValueError("specialist_version is invalid")
    prompt_hash = str(value.get("specialist_prompt_hash") or "").strip().casefold()
    if content_digest_identity(prompt_hash) is None:
        raise ValueError("specialist_prompt_hash must be a SHA-256 identity")
    body_length = value.get("body_character_length")
    if type(body_length) is not int or not 1 <= body_length <= MAX_SPECIALIST_PROMPT_CHARS:
        raise ValueError("specialist prompt body character length is invalid")
    return {
        "specialist_slug": slug,
        "specialist_version": version,
        "specialist_prompt_hash": prompt_hash,
        "body_character_length": body_length,
    }


def _normalized_inference_team_cards(
    cards: object,
) -> tuple[tuple[InferenceTeamCard, ...], list[dict[str, Any]]]:
    if (
        not isinstance(cards, Sequence)
        or isinstance(cards, (str, bytes, bytearray))
        or not 1 <= len(cards) <= MAX_INFERENCE_TEAM_CARDS
    ):
        raise ValueError(f"inference team must contain 1-{MAX_INFERENCE_TEAM_CARDS} cards")
    normalized_cards: list[InferenceTeamCard] = []
    metadata_cards: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    for card in cards:
        if not isinstance(card, InferenceTeamCard):
            raise ValueError("inference team cards must be InferenceTeamCard values")
        if not isinstance(card.prompt_body, str) or not card.prompt_body:
            raise ValueError("specialist prompt body must be a non-empty string")
        descriptor = _normalized_inference_team_card_metadata(
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": len(card.prompt_body),
            }
        )
        if descriptor["specialist_slug"] in seen_slugs:
            raise ValueError("inference team cannot contain a duplicate specialist")
        seen_slugs.add(str(descriptor["specialist_slug"]))
        try:
            matches = content_identity_matches(
                card.prompt_body,
                descriptor["specialist_prompt_hash"],
            )
        except UnicodeEncodeError as exc:
            raise ValueError("specialist prompt body must be valid UTF-8 text") from exc
        if not matches:
            raise ValueError("specialist prompt body failed exact identity verification")
        normalized_cards.append(
            InferenceTeamCard(
                specialist_slug=str(descriptor["specialist_slug"]),
                specialist_version=str(descriptor["specialist_version"]),
                specialist_prompt_hash=str(descriptor["specialist_prompt_hash"]),
                prompt_body=card.prompt_body,
            )
        )
        metadata_cards.append(descriptor)
    return tuple(normalized_cards), metadata_cards


def _inference_team_descriptor_digest(cards: list[dict[str, Any]]) -> str:
    return sha256(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def inference_team_digest(cards: object) -> str:
    """Return the canonical identity of one exact ordered multi-card team."""

    _normalized_cards, metadata_cards = _normalized_inference_team_cards(cards)
    return _inference_team_descriptor_digest(metadata_cards)


def _inference_team_metadata(
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    launch_id: object,
    decision_id: object,
    provider_receipt_digest: object,
    task_sha256: object,
    candidate_digest: object,
    install_id: object,
    bundle_digest: object,
    runtime_digest: object,
    issued_at: object,
    expires_at: object,
    nonce: object,
    binding_kind: object,
    binding_id: object,
    cards: object,
) -> dict[str, Any]:
    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in {"codex", "claude", "zcode", "hermes", "openclaw"}:
        raise ValueError("native-child prompt delivery host is unsupported")
    canonical_issued_at, issued = _canonical_timestamp(issued_at, field="issued_at")
    canonical_expires_at, expires = _canonical_timestamp(expires_at, field="expires_at")
    if expires <= issued:
        raise ValueError("expires_at must be later than issued_at")
    if (expires - issued).total_seconds() > MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS:
        raise ValueError("native-child delivery lifetime exceeds its maximum")
    kind = str(binding_kind or "").strip().casefold()
    if _BINDING_KIND_PATTERN.fullmatch(kind) is None:
        raise ValueError("binding_kind is invalid")
    if not isinstance(cards, list) or not 1 <= len(cards) <= MAX_INFERENCE_TEAM_CARDS:
        raise ValueError(f"inference team must contain 1-{MAX_INFERENCE_TEAM_CARDS} cards")
    normalized_cards = [_normalized_inference_team_card_metadata(card) for card in cards]
    slugs = [str(card["specialist_slug"]) for card in normalized_cards]
    if len(slugs) != len(set(slugs)):
        raise ValueError("inference team cannot contain a duplicate specialist")
    candidate = _normalized_sha256(candidate_digest, field="candidate_digest")
    runtime = _normalized_sha256(runtime_digest, field="runtime_digest")
    if candidate != runtime:
        raise ValueError("candidate_digest must match runtime_digest")
    metadata: dict[str, Any] = {
        "version": INFERENCE_TEAM_DELIVERY_VERSION,
        "host": normalized_host,
        "parent_session_id": validate_correlation_id(
            parent_session_id,
            field="parent_session_id",
        ),
        "parent_trace_id": validate_correlation_id(parent_trace_id, field="parent_trace_id"),
        "launch_id": validate_correlation_id(launch_id, field="launch_id"),
        "decision_id": validate_correlation_id(decision_id, field="decision_id"),
        "provider_receipt_digest": _normalized_sha256(
            provider_receipt_digest,
            field="provider_receipt_digest",
        ),
        "task_sha256": _normalized_sha256(task_sha256, field="task_sha256"),
        "candidate_digest": candidate,
        "install_id": validate_correlation_id(install_id, field="install_id"),
        "bundle_digest": _normalized_sha256(bundle_digest, field="bundle_digest"),
        "runtime_digest": runtime,
        "issued_at": canonical_issued_at,
        "expires_at": canonical_expires_at,
        "nonce": validate_correlation_id(nonce, field="nonce"),
        "binding_kind": kind,
        "binding_id": validate_correlation_id(binding_id, field="binding_id"),
        "cards": normalized_cards,
    }
    metadata["team_digest"] = _inference_team_descriptor_digest(normalized_cards)
    return metadata


def _identity_metadata(
    *,
    envelope_version: int,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
) -> dict[str, Any]:
    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in {"codex", "claude", "zcode"}:
        raise ValueError("native-child prompt delivery host is unsupported")
    session_id = validate_correlation_id(parent_session_id, field="parent_session_id")
    trace_id = validate_correlation_id(parent_trace_id, field="parent_trace_id")
    use_id = validate_correlation_id(tool_use_id, field="tool_use_id")
    unit_id = validate_correlation_id(work_unit_id, field="work_unit_id")
    slug = normalize_agent_slug(specialist_slug)
    normalized_specialist_version = str(specialist_version or "").strip()
    if (
        not normalized_specialist_version
        or normalize_version_identity(normalized_specialist_version)
        != normalized_specialist_version
    ):
        raise ValueError("specialist_version is invalid")
    content_hash = str(specialist_prompt_hash or "").strip().casefold()
    if content_digest_identity(content_hash) is None:
        raise ValueError("specialist_prompt_hash is invalid")
    return {
        "version": envelope_version,
        "host": normalized_host,
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "tool_use_id": use_id,
        "work_unit_id": unit_id,
        "specialist_slug": slug,
        "specialist_version": normalized_specialist_version,
        "specialist_prompt_hash": content_hash,
    }


def _metadata(
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    activation_token: object,
) -> dict[str, Any]:
    metadata = _identity_metadata(
        envelope_version=NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    token = str(activation_token or "").strip()
    if not token or len(token) > MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS:
        raise ValueError("activation_token is invalid")
    metadata["activation_token"] = token
    return metadata


def _codex_opaque_metadata(
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> dict[str, Any]:
    metadata = _identity_metadata(
        envelope_version=CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        host="codex",
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    digest = str(goal_hash or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("goal_hash is invalid")
    metadata["goal_hash"] = digest
    return metadata


def _codex_direct_metadata(
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> dict[str, Any]:
    metadata = _identity_metadata(
        envelope_version=CODEX_DIRECT_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
        host="codex",
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    digest = str(goal_hash or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("goal_hash is invalid")
    metadata["goal_hash"] = digest
    return metadata


def _codex_execution_metadata(
    *,
    work_unit_id: object,
    goal_hash: object,
) -> dict[str, Any]:
    from agency_runtime.core.delegation.native_labels import (
        codex_task_name_for_work_unit,
    )

    unit_id = validate_correlation_id(work_unit_id, field="work_unit_id")
    digest = str(goal_hash or "").strip().casefold()
    if _DIGEST_PATTERN.fullmatch(digest) is None:
        raise ValueError("goal_hash is invalid")
    return {
        "version": CODEX_NATIVE_CHILD_EXECUTION_VERSION,
        "work_unit_id": unit_id,
        "native_task_name": codex_task_name_for_work_unit(unit_id),
        "goal_hash": digest,
    }


def render_codex_native_child_execution_message(
    *,
    work_unit_id: object,
    goal_hash: object,
    goal: object = "",
) -> str:
    """Render one exact execution turn, optionally with its hash-bound goal."""

    metadata = _codex_execution_metadata(
        work_unit_id=work_unit_id,
        goal_hash=goal_hash,
    )
    marker = f"{_CODEX_EXECUTION_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    identity_message = f"{_CODEX_EXECUTION_SECTION}{marker}\n{_CODEX_EXECUTION_INSTRUCTION}"
    if goal is None or goal == "":
        return identity_message
    if not isinstance(goal, str) or not goal:
        raise ValueError("execution goal must be a non-empty string")
    from agency_runtime.core.unit_assignment import work_unit_goal_hash

    if work_unit_goal_hash(goal) != metadata["goal_hash"]:
        raise ValueError("execution goal does not match goal_hash")
    return f"{identity_message}{_CODEX_EXECUTION_GOAL_SECTION}{goal}"


def render_codex_native_child_execution_prefix(
    *,
    work_unit_id: object,
    goal_hash: object,
) -> str:
    """Render the bounded prefix that must be concatenated with one exact goal."""

    return (
        render_codex_native_child_execution_message(
            work_unit_id=work_unit_id,
            goal_hash=goal_hash,
        )
        + _CODEX_EXECUTION_GOAL_SECTION
    )


def is_codex_opaque_collaboration_message(value: object) -> bool:
    """Return whether Codex exposed only its bounded encrypted message shape."""

    return (
        isinstance(value, str)
        and _CODEX_OPAQUE_COLLABORATION_MESSAGE_PATTERN.fullmatch(value) is not None
    )


def codex_opaque_child_message_ciphertext(
    value: object,
    *,
    native_task_name: object,
    turn_id: object,
) -> str | None:
    """Return one exact root-to-child ciphertext from current Codex evidence."""

    task_name = str(native_task_name or "").strip()
    normalized_turn = str(turn_id or "").strip()
    if not task_name or len(task_name) > 128 or not normalized_turn:
        return None
    if not isinstance(value, Mapping) or set(value) != {
        "type",
        "id",
        "author",
        "recipient",
        "internal_chat_message_metadata_passthrough",
        "content",
    }:
        return None
    item_id = value.get("id")
    metadata = value.get("internal_chat_message_metadata_passthrough")
    content = value.get("content")
    expected_path = f"/root/{task_name}"
    expected_text = f"Message Type: NEW_TASK\nTask name: {expected_path}\nSender: /root\nPayload:\n"
    if (
        value.get("type") != "agent_message"
        or not isinstance(item_id, str)
        or not item_id
        or len(item_id) > 256
        or value.get("author") != "/root"
        or value.get("recipient") != expected_path
        or not isinstance(metadata, Mapping)
        or set(metadata) != {"turn_id"}
        or metadata.get("turn_id") != normalized_turn
        or not isinstance(content, list)
        or len(content) != 2
    ):
        return None
    visible, encrypted = content
    if (
        not isinstance(visible, Mapping)
        or set(visible) != {"type", "text"}
        or visible.get("type") != "input_text"
        or visible.get("text") != expected_text
        or not isinstance(encrypted, Mapping)
        or set(encrypted) != {"type", "encrypted_content"}
        or encrypted.get("type") != "encrypted_content"
    ):
        return None
    ciphertext = encrypted.get("encrypted_content")
    return str(ciphertext) if is_codex_opaque_collaboration_message(ciphertext) else None


def parse_codex_native_child_execution_message(
    value: object,
) -> CodexNativeChildExecutionDelivery | None:
    """Recover one canonical execution envelope from a host message or transcript item."""

    if not isinstance(value, str) or not value:
        return None
    for match in reversed(list(_CODEX_EXECUTION_MARKER_PATTERN.finditer(value))):
        metadata = _decoded_metadata(
            match.group(1),
            expected_fields=_CODEX_EXECUTION_FIELDS,
        )
        if metadata is None:
            continue
        try:
            normalized = _codex_execution_metadata(
                work_unit_id=metadata.get("work_unit_id"),
                goal_hash=metadata.get("goal_hash"),
            )
        except ValueError:
            continue
        if metadata != normalized:
            continue
        section_start = value.rfind(_CODEX_EXECUTION_SECTION, 0, match.start())
        if section_start < 0 or section_start + len(_CODEX_EXECUTION_SECTION) != match.start():
            continue
        instruction_end = match.end() + 1 + len(_CODEX_EXECUTION_INSTRUCTION)
        if value[match.end() : instruction_end] != f"\n{_CODEX_EXECUTION_INSTRUCTION}":
            continue
        remainder = value[instruction_end:]
        goal = ""
        if remainder:
            if not remainder.startswith(_CODEX_EXECUTION_GOAL_SECTION):
                continue
            goal = remainder[len(_CODEX_EXECUTION_GOAL_SECTION) :]
            if not goal:
                continue
            from agency_runtime.core.unit_assignment import work_unit_goal_hash

            if work_unit_goal_hash(goal) != normalized["goal_hash"]:
                continue
        return CodexNativeChildExecutionDelivery(
            work_unit_id=normalized["work_unit_id"],
            native_task_name=normalized["native_task_name"],
            goal_hash=normalized["goal_hash"],
            goal=goal,
        )
    return None


def render_native_child_prompt_delivery(
    original_task: object,
    prompt_body: object,
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    activation_token: object,
) -> str:
    """Append one exact prompt body and a self-verifying delivery marker."""

    if not isinstance(original_task, str) or not original_task:
        raise ValueError("native child task must be a non-empty string")
    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _metadata(
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
        activation_token=activation_token,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{original_task}{_SECTION}{marker}\n{prompt_body}"


def _jit_metadata(
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
) -> dict[str, Any]:
    """Validate one grant-free just-in-time identity. No work unit exists to bind."""

    normalized_host = str(host or "").strip().casefold()
    if normalized_host not in {"codex", "claude", "zcode"}:
        raise ValueError("native-child prompt delivery host is unsupported")
    normalized_specialist_version = str(specialist_version or "").strip()
    if (
        not normalized_specialist_version
        or normalize_version_identity(normalized_specialist_version)
        != normalized_specialist_version
    ):
        raise ValueError("specialist_version is invalid")
    content_hash = str(specialist_prompt_hash or "").strip().casefold()
    if content_digest_identity(content_hash) is None:
        raise ValueError("specialist_prompt_hash is invalid")
    return {
        "version": JIT_SPECIALIST_DELIVERY_VERSION,
        "host": normalized_host,
        "parent_session_id": validate_correlation_id(parent_session_id, field="parent_session_id"),
        "parent_trace_id": validate_correlation_id(parent_trace_id, field="parent_trace_id"),
        "tool_use_id": validate_correlation_id(tool_use_id, field="tool_use_id"),
        "specialist_slug": normalize_agent_slug(specialist_slug),
        "specialist_version": normalized_specialist_version,
        "specialist_prompt_hash": content_hash,
    }


def render_jit_specialist_delivery(
    original_task: object,
    prompt_body: object,
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
) -> str:
    """Append one just-in-time specialist and a self-verifying marker to a child task."""

    if not isinstance(original_task, str) or not original_task:
        raise ValueError("native child task must be a non-empty string")
    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _jit_metadata(
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_JIT_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{original_task}{_JIT_SECTION}{marker}\n{prompt_body}"


def parse_jit_specialist_delivery(value: object) -> JitSpecialistDelivery | None:
    """Recover the last valid just-in-time envelope so restaffing stays idempotent."""

    if not isinstance(value, str) or not value:
        return None
    for match in sorted(_JIT_MARKER_PATTERN.finditer(value), key=lambda item: -item.start()):
        metadata = _decoded_metadata(match.group(1), expected_fields=_JIT_FIELDS)
        if metadata is None:
            continue
        try:
            normalized = _jit_metadata(
                host=metadata.get("host"),
                parent_session_id=metadata.get("parent_session_id"),
                parent_trace_id=metadata.get("parent_trace_id"),
                tool_use_id=metadata.get("tool_use_id"),
                specialist_slug=metadata.get("specialist_slug"),
                specialist_version=metadata.get("specialist_version"),
                specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
            )
        except (TypeError, ValueError):
            continue
        if normalized != metadata:
            continue
        prompt_body = value[match.end() :].lstrip("\n")
        original_task = value[: match.start()]
        # The FIRST section, not the last: a child may carry several cards, and
        # anything from the first marker onward is delivered context rather than
        # the task the host actually wrote.
        section = original_task.find(_JIT_SECTION)
        if section != -1:
            original_task = original_task[:section]
        if not prompt_body or not content_identity_matches(
            prompt_body,
            normalized["specialist_prompt_hash"],
        ):
            continue
        return JitSpecialistDelivery(
            host=str(normalized["host"]),
            parent_session_id=str(normalized["parent_session_id"]),
            parent_trace_id=str(normalized["parent_trace_id"]),
            tool_use_id=str(normalized["tool_use_id"]),
            specialist_slug=str(normalized["specialist_slug"]),
            specialist_version=str(normalized["specialist_version"]),
            specialist_prompt_hash=str(normalized["specialist_prompt_hash"]),
            original_task=original_task,
            prompt_body=prompt_body,
        )
    return None


def parse_all_jit_specialist_deliveries(value: object) -> list[JitSpecialistDelivery]:
    """Recover every just-in-time card delivered to one child, in delivery order.

    A host-initiated child may be handed more than one card. Each is rendered as
    its own self-verifying envelope, so every prompt body is still checked
    against its own pinned version hash rather than a combined digest that could
    not attribute a mismatch.
    """

    if not isinstance(value, str) or not value:
        return []
    matches = list(_JIT_MARKER_PATTERN.finditer(value))
    if not matches:
        return []
    first_section = value.find(_JIT_SECTION)
    original_task = value[:first_section] if first_section != -1 else ""
    deliveries: list[JitSpecialistDelivery] = []
    for index, match in enumerate(matches):
        metadata = _decoded_metadata(match.group(1), expected_fields=_JIT_FIELDS)
        if metadata is None:
            continue
        try:
            normalized = _jit_metadata(
                host=metadata.get("host"),
                parent_session_id=metadata.get("parent_session_id"),
                parent_trace_id=metadata.get("parent_trace_id"),
                tool_use_id=metadata.get("tool_use_id"),
                specialist_slug=metadata.get("specialist_slug"),
                specialist_version=metadata.get("specialist_version"),
                specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
            )
        except (TypeError, ValueError):
            continue
        if normalized != metadata:
            continue
        end = value.find(_JIT_SECTION, match.end()) if index + 1 < len(matches) else len(value)
        prompt_body = value[match.end() : end if end != -1 else len(value)].lstrip("\n")
        if not prompt_body or not content_identity_matches(
            prompt_body,
            normalized["specialist_prompt_hash"],
        ):
            continue
        deliveries.append(
            JitSpecialistDelivery(
                host=str(normalized["host"]),
                parent_session_id=str(normalized["parent_session_id"]),
                parent_trace_id=str(normalized["parent_trace_id"]),
                tool_use_id=str(normalized["tool_use_id"]),
                specialist_slug=str(normalized["specialist_slug"]),
                specialist_version=str(normalized["specialist_version"]),
                specialist_prompt_hash=str(normalized["specialist_prompt_hash"]),
                original_task=original_task,
                prompt_body=prompt_body,
            )
        )
    return deliveries


def _inference_team_card_header(
    index: int,
    count: int,
    card: Mapping[str, Any],
) -> str:
    return (
        f"\n[AGENCY INFERENCE TEAM CARD {index}/{count}]\n"
        f"Specialist: {card['specialist_slug']}\n"
        f"Version: {card['specialist_version']}\n"
    )


def render_inference_team_context_segment(
    original_task: object,
    cards: object,
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    launch_id: object,
    decision_id: object,
    provider_receipt_digest: object,
    candidate_digest: object,
    install_id: object,
    bundle_digest: object,
    runtime_digest: object,
    issued_at: object,
    expires_at: object,
    nonce: object,
    binding_kind: object,
    binding_id: object,
) -> str:
    """Render only the exact v6 context segment bound to ``original_task``.

    Append-only hosts may add the returned segment to the same byte-for-byte task.
    Parsing and evidence validation still consume the resulting full task plus segment.
    """

    if not isinstance(original_task, str) or not original_task:
        raise ValueError("native child task must be a non-empty string")
    if any(
        token in original_task
        for token in (
            _INFERENCE_TEAM_SECTION,
            _INFERENCE_TEAM_MARKER_PREFIX,
            _INFERENCE_TEAM_END_PREFIX,
            *_MIXED_NATIVE_CHILD_MARKER_PREFIXES,
        )
    ):
        raise ValueError("native child task contains a reserved inference-team marker")
    normalized_cards, card_metadata = _normalized_inference_team_cards(cards)
    for card in normalized_cards:
        if any(
            token in card.prompt_body
            for token in (
                _INFERENCE_TEAM_SECTION,
                _INFERENCE_TEAM_MARKER_PREFIX,
                _INFERENCE_TEAM_END_PREFIX,
                *_MIXED_NATIVE_CHILD_MARKER_PREFIXES,
            )
        ):
            raise ValueError("specialist prompt body contains a reserved inference-team marker")
    metadata = _inference_team_metadata(
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        launch_id=launch_id,
        decision_id=decision_id,
        provider_receipt_digest=provider_receipt_digest,
        task_sha256=_sha256_text(original_task, field="native child task"),
        candidate_digest=candidate_digest,
        install_id=install_id,
        bundle_digest=bundle_digest,
        runtime_digest=runtime_digest,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
        binding_kind=binding_kind,
        binding_id=binding_id,
        cards=card_metadata,
    )
    marker = f"{_INFERENCE_TEAM_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    payload = "".join(
        _inference_team_card_header(index, len(normalized_cards), descriptor) + card.prompt_body
        for index, (card, descriptor) in enumerate(
            zip(normalized_cards, card_metadata, strict=True),
            start=1,
        )
    )
    end_marker = f"\n{_INFERENCE_TEAM_END_PREFIX}{metadata['team_digest']}{_MARKER_SUFFIX}"
    return f"{_INFERENCE_TEAM_SECTION}{marker}{payload}{end_marker}"


def render_inference_team_delivery(
    original_task: object,
    cards: object,
    *,
    host: object,
    parent_session_id: object,
    parent_trace_id: object,
    launch_id: object,
    decision_id: object,
    provider_receipt_digest: object,
    candidate_digest: object,
    install_id: object,
    bundle_digest: object,
    runtime_digest: object,
    issued_at: object,
    expires_at: object,
    nonce: object,
    binding_kind: object,
    binding_id: object,
) -> str:
    """Append one exact ordered inference-selected team to a native child task."""

    if not isinstance(original_task, str) or not original_task:
        raise ValueError("native child task must be a non-empty string")
    return original_task + render_inference_team_context_segment(
        original_task,
        cards,
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        launch_id=launch_id,
        decision_id=decision_id,
        provider_receipt_digest=provider_receipt_digest,
        candidate_digest=candidate_digest,
        install_id=install_id,
        bundle_digest=bundle_digest,
        runtime_digest=runtime_digest,
        issued_at=issued_at,
        expires_at=expires_at,
        nonce=nonce,
        binding_kind=binding_kind,
        binding_id=binding_id,
    )


def parse_inference_team_delivery(value: object) -> InferenceTeamDelivery | None:
    """Recover one complete v6 team, rejecting any invalid member atomically."""

    if not isinstance(value, str) or not value:
        return None
    if (
        value.count(_INFERENCE_TEAM_SECTION) != 1
        or value.count(_INFERENCE_TEAM_MARKER_PREFIX) != 1
        or value.count(_INFERENCE_TEAM_END_PREFIX) != 1
    ):
        return None
    matches = list(_INFERENCE_TEAM_MARKER_PATTERN.finditer(value))
    if len(matches) != 1:
        return None
    match = matches[0]
    section_start = value.rfind(_INFERENCE_TEAM_SECTION, 0, match.start())
    if section_start < 0 or section_start + len(_INFERENCE_TEAM_SECTION) != match.start():
        return None
    original_task = value[:section_start]
    if not original_task or any(
        marker in original_task for marker in _MIXED_NATIVE_CHILD_MARKER_PREFIXES
    ):
        return None
    metadata = _decoded_metadata(
        match.group(1),
        expected_fields=_INFERENCE_TEAM_FIELDS,
    )
    if metadata is None:
        return None
    try:
        normalized = _inference_team_metadata(
            host=metadata.get("host"),
            parent_session_id=metadata.get("parent_session_id"),
            parent_trace_id=metadata.get("parent_trace_id"),
            launch_id=metadata.get("launch_id"),
            decision_id=metadata.get("decision_id"),
            provider_receipt_digest=metadata.get("provider_receipt_digest"),
            task_sha256=metadata.get("task_sha256"),
            candidate_digest=metadata.get("candidate_digest"),
            install_id=metadata.get("install_id"),
            bundle_digest=metadata.get("bundle_digest"),
            runtime_digest=metadata.get("runtime_digest"),
            issued_at=metadata.get("issued_at"),
            expires_at=metadata.get("expires_at"),
            nonce=metadata.get("nonce"),
            binding_kind=metadata.get("binding_kind"),
            binding_id=metadata.get("binding_id"),
            cards=metadata.get("cards"),
        )
        if (
            metadata != normalized
            or _sha256_text(
                original_task,
                field="native child task",
            )
            != normalized["task_sha256"]
        ):
            return None
    except (TypeError, ValueError):
        return None

    cursor = match.end()
    parsed_cards: list[InferenceTeamCard] = []
    card_metadata = normalized["cards"]
    for index, descriptor in enumerate(card_metadata, start=1):
        header = _inference_team_card_header(index, len(card_metadata), descriptor)
        if not value.startswith(header, cursor):
            return None
        cursor += len(header)
        body_length = int(descriptor["body_character_length"])
        prompt_body = value[cursor : cursor + body_length]
        if len(prompt_body) != body_length or any(
            marker in prompt_body for marker in _MIXED_NATIVE_CHILD_MARKER_PREFIXES
        ):
            return None
        try:
            if not content_identity_matches(
                prompt_body,
                descriptor["specialist_prompt_hash"],
            ):
                return None
        except UnicodeEncodeError:
            return None
        parsed_cards.append(
            InferenceTeamCard(
                specialist_slug=str(descriptor["specialist_slug"]),
                specialist_version=str(descriptor["specialist_version"]),
                specialist_prompt_hash=str(descriptor["specialist_prompt_hash"]),
                prompt_body=prompt_body,
            )
        )
        cursor += body_length
    expected_end = f"\n{_INFERENCE_TEAM_END_PREFIX}{normalized['team_digest']}{_MARKER_SUFFIX}"
    if value[cursor:] != expected_end:
        return None
    return InferenceTeamDelivery(
        host=str(normalized["host"]),
        parent_session_id=str(normalized["parent_session_id"]),
        parent_trace_id=str(normalized["parent_trace_id"]),
        launch_id=str(normalized["launch_id"]),
        decision_id=str(normalized["decision_id"]),
        provider_receipt_digest=str(normalized["provider_receipt_digest"]),
        task_sha256=str(normalized["task_sha256"]),
        candidate_digest=str(normalized["candidate_digest"]),
        install_id=str(normalized["install_id"]),
        bundle_digest=str(normalized["bundle_digest"]),
        runtime_digest=str(normalized["runtime_digest"]),
        issued_at=str(normalized["issued_at"]),
        expires_at=str(normalized["expires_at"]),
        nonce=str(normalized["nonce"]),
        binding_kind=str(normalized["binding_kind"]),
        binding_id=str(normalized["binding_id"]),
        team_digest=str(normalized["team_digest"]),
        original_task=original_task,
        cards=tuple(parsed_cards),
    )


def render_codex_opaque_native_child_prompt_delivery(
    prompt_body: object,
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> str:
    """Render content-free Codex child context bound to one persisted goal hash."""

    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _codex_opaque_metadata(
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
        goal_hash=goal_hash,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_CODEX_OPAQUE_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{_CODEX_OPAQUE_SECTION}{marker}\n{prompt_body}"


def render_codex_direct_native_child_prompt_delivery(
    prompt_body: object,
    *,
    parent_session_id: object,
    parent_trace_id: object,
    tool_use_id: object,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
) -> str:
    """Render specialist context that executes the exact Codex spawn goal immediately."""

    if not isinstance(prompt_body, str) or not prompt_body:
        raise ValueError("specialist prompt body must be a non-empty string")
    metadata = _codex_direct_metadata(
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
        tool_use_id=tool_use_id,
        work_unit_id=work_unit_id,
        specialist_slug=specialist_slug,
        specialist_version=specialist_version,
        specialist_prompt_hash=specialist_prompt_hash,
        goal_hash=goal_hash,
    )
    if not content_identity_matches(prompt_body, metadata["specialist_prompt_hash"]):
        raise ValueError("specialist prompt body failed exact identity verification")
    marker = f"{_CODEX_DIRECT_MARKER_PREFIX}{_encoded_metadata(metadata)}{_MARKER_SUFFIX}"
    return f"{_CODEX_DIRECT_SECTION}{marker}\n{prompt_body}{_CODEX_DIRECT_EXECUTION_SUFFIX}"


def _prompt_body_for_delivery(
    value: str,
    *,
    prompt_start: int,
    envelope_version: int,
) -> str | None:
    """Return only the immutable specialist body from an exact delivery envelope."""

    prompt_end = len(value)
    if envelope_version == CODEX_DIRECT_NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
        if not value.endswith(_CODEX_DIRECT_EXECUTION_SUFFIX):
            return None
        prompt_end -= len(_CODEX_DIRECT_EXECUTION_SUFFIX)
    prompt_body = value[prompt_start:prompt_end]
    return prompt_body or None


def parse_native_child_prompt_delivery(value: object) -> NativeChildPromptDelivery | None:
    """Recover the last valid exact envelope from a rewritten native child task."""

    if not isinstance(value, str) or not value:
        return None
    matches = [
        (match.start(), NATIVE_CHILD_PROMPT_DELIVERY_VERSION, match)
        for match in _MARKER_PATTERN.finditer(value)
    ]
    matches.extend(
        (
            match.start(),
            CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
            match,
        )
        for match in _CODEX_OPAQUE_MARKER_PATTERN.finditer(value)
    )
    matches.extend(
        (
            match.start(),
            CODEX_DIRECT_NATIVE_CHILD_PROMPT_DELIVERY_VERSION,
            match,
        )
        for match in _CODEX_DIRECT_MARKER_PATTERN.finditer(value)
    )
    for _start, envelope_version, match in sorted(matches, reverse=True):
        fields = _V1_FIELDS if envelope_version == 1 else _V2_FIELDS
        metadata = _decoded_metadata(match.group(1), expected_fields=fields)
        if metadata is None:
            continue
        try:
            if envelope_version == NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
                normalized = _metadata(
                    host=metadata.get("host"),
                    parent_session_id=metadata.get("parent_session_id"),
                    parent_trace_id=metadata.get("parent_trace_id"),
                    tool_use_id=metadata.get("tool_use_id"),
                    work_unit_id=metadata.get("work_unit_id"),
                    specialist_slug=metadata.get("specialist_slug"),
                    specialist_version=metadata.get("specialist_version"),
                    specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
                    activation_token=metadata.get("activation_token"),
                )
            elif envelope_version == CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
                normalized = _codex_opaque_metadata(
                    parent_session_id=metadata.get("parent_session_id"),
                    parent_trace_id=metadata.get("parent_trace_id"),
                    tool_use_id=metadata.get("tool_use_id"),
                    work_unit_id=metadata.get("work_unit_id"),
                    specialist_slug=metadata.get("specialist_slug"),
                    specialist_version=metadata.get("specialist_version"),
                    specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
                    goal_hash=metadata.get("goal_hash"),
                )
            else:
                normalized = _codex_direct_metadata(
                    parent_session_id=metadata.get("parent_session_id"),
                    parent_trace_id=metadata.get("parent_trace_id"),
                    tool_use_id=metadata.get("tool_use_id"),
                    work_unit_id=metadata.get("work_unit_id"),
                    specialist_slug=metadata.get("specialist_slug"),
                    specialist_version=metadata.get("specialist_version"),
                    specialist_prompt_hash=metadata.get("specialist_prompt_hash"),
                    goal_hash=metadata.get("goal_hash"),
                )
        except ValueError:
            continue
        if metadata != normalized:
            continue
        prompt_start = match.end()
        if value.startswith("\r\n", prompt_start):
            prompt_start += 2
        elif value.startswith("\n", prompt_start):
            prompt_start += 1
        else:
            continue
        prompt_body = _prompt_body_for_delivery(
            value,
            prompt_start=prompt_start,
            envelope_version=envelope_version,
        )
        if prompt_body is None or not content_identity_matches(
            prompt_body,
            normalized["specialist_prompt_hash"],
        ):
            continue
        if envelope_version == NATIVE_CHILD_PROMPT_DELIVERY_VERSION:
            section_start = value.rfind(_SECTION, 0, match.start())
            if section_start < 0 or section_start + len(_SECTION) != match.start():
                continue
            original_task = value[:section_start]
            from agency_runtime.core.unit_assignment import work_unit_goal_hash

            goal_hash = work_unit_goal_hash(original_task)
            activation_token = normalized["activation_token"]
        else:
            section = (
                _CODEX_OPAQUE_SECTION
                if envelope_version == CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION
                else _CODEX_DIRECT_SECTION
            )
            section_start = value.rfind(section, 0, match.start())
            if section_start != 0 or len(section) != match.start():
                continue
            original_task = ""
            goal_hash = normalized["goal_hash"]
            activation_token = ""
        return NativeChildPromptDelivery(
            host=normalized["host"],
            parent_session_id=normalized["parent_session_id"],
            parent_trace_id=normalized["parent_trace_id"],
            tool_use_id=normalized["tool_use_id"],
            work_unit_id=normalized["work_unit_id"],
            specialist_slug=normalized["specialist_slug"],
            specialist_version=normalized["specialist_version"],
            specialist_prompt_hash=normalized["specialist_prompt_hash"],
            activation_token=activation_token,
            goal_hash=goal_hash,
            original_task=original_task,
            prompt_body=prompt_body,
        )
    return None


__all__ = [
    "CODEX_DIRECT_NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "CODEX_NATIVE_CHILD_EXECUTION_VERSION",
    "CODEX_OPAQUE_NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "INFERENCE_TEAM_DELIVERY_VERSION",
    "MAX_INFERENCE_TEAM_CARDS",
    "MAX_NATIVE_CHILD_ACTIVATION_TOKEN_CHARS",
    "MAX_NATIVE_CHILD_DELIVERY_METADATA_BYTES",
    "NATIVE_CHILD_PROMPT_DELIVERY_VERSION",
    "CodexNativeChildExecutionDelivery",
    "InferenceTeamCard",
    "InferenceTeamDelivery",
    "NativeChildPromptDelivery",
    "codex_opaque_child_message_ciphertext",
    "inference_team_digest",
    "is_codex_opaque_collaboration_message",
    "parse_all_jit_specialist_deliveries",
    "parse_codex_native_child_execution_message",
    "parse_inference_team_delivery",
    "parse_native_child_prompt_delivery",
    "render_codex_direct_native_child_prompt_delivery",
    "render_codex_native_child_execution_message",
    "render_codex_native_child_execution_prefix",
    "render_codex_opaque_native_child_prompt_delivery",
    "render_inference_team_context_segment",
    "render_inference_team_delivery",
    "render_native_child_prompt_delivery",
]
