"""State-aware classification for one external user turn.

Turn kind, specialist selection, and execution topology are deliberately
separate decisions.  This module classifies only the user-facing turn and emits
bounded, content-free state evidence for downstream routing.
"""

from __future__ import annotations

import hmac
import json
import math
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Final, Literal

from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.runtime_control_command import parse_runtime_control_command

TurnKind = Literal[
    "acknowledgement",
    "conversation",
    "control",
    "continuation",
    "new_intent",
    "revision",
]
TurnStateStatus = Literal["current", "missing", "stale", "ambiguous", "corrupt"]

TURN_CLASSIFIER_VERSION = 4
SUPPORTED_TURN_CLASSIFIER_VERSIONS: Final[frozenset[int]] = frozenset({1, 2, 3, 4})
MAX_TURN_SIGNAL_CHARS = 16_384
MAX_REASON_CODES = 8
MAX_REASON_CODE_CHARS = 64
TURN_KINDS = frozenset(
    {
        "acknowledgement",
        "conversation",
        "control",
        "continuation",
        "new_intent",
        "revision",
    }
)
TURN_STATE_STATUSES = frozenset({"current", "missing", "stale", "ambiguous", "corrupt"})

_TURN_CLASSIFICATION_KEY: Final[bytes] = secrets.token_bytes(32)
_PURE_ACKNOWLEDGEMENT = re.compile(
    r"^(?:ack|got\s+it|k|ok(?:ay)?|perfect|sounds\s+good|"
    r"thank\s+you|thanks|thx|ty|understood|👍|❤️|🙌|✅)\s*[!.]*$",
    re.IGNORECASE,
)
_PURE_CONVERSATION = re.compile(
    r"^(?:good\s+(?:morning|afternoon|evening)|"
    r"h(?:ello|ey|i)|how(?:'s|\s+is)\s+it\s+going|"
    r"nice\s+to\s+(?:meet|see)\s+you|sup|yo)\s*[!.?]*$",
    re.IGNORECASE,
)
_CONTEXTUAL_CONTINUATION = re.compile(
    r"^(?:continue|do\s+it|go|go\s+ahead|hold|no|nope|proceed|"
    r"retry|ship\s+it|skip|stop|sure|wait|yes|yep)\s*[!.]*$",
    re.IGNORECASE,
)
_REVISION_PREFIX = re.compile(
    r"^(?:actually|additionally|also|but|change|except|instead|"
    r"make\s+it|no,\s+|not\s+that|plus|remove|support|wait,\s+)",
    re.IGNORECASE,
)
_AUTHORIZATION_QUESTION = re.compile(
    r"(?:\b(?:approve|authorization|authorize|confirmation|confirm|"
    r"do you want me to|permission|would you like me to)\b|"
    r"(?:^|[.!?]\s+)(?:may|shall|should)\s+i\b)",
    re.IGNORECASE,
)
_AUTHORIZATION_REPLY = re.compile(
    r"\b(?:reply|respond)\s+(?:with\s+)?(?:yes|approve|approved|confirm|confirmed)\b",
    re.IGNORECASE,
)
_STATE_REVISION = re.compile(r"^[0-9a-f]{64}$")
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_.-]*$")
_STATE_BOOLEAN_FIELDS = (
    "active_plan",
    "unfinished_work",
    "pending_question",
    "pending_authorization",
    "retry_pending",
)
_STATE_LABEL_FIELDS = (
    "previous_trace_id",
    "previous_status",
    "previous_turn_kind",
    "configuration_revision",
    "roster_revision",
    "specialist_revision",
    "delegation_revision",
)


def _bounded_label(value: Any, maximum: int = 128) -> str:
    return " ".join(str(value or "").split())[: max(0, maximum)]


def _bounded_confidence(value: Any) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(normalized):
        return 0.0
    return max(0.0, min(normalized, 1.0))


def _bounded_reason_codes(values: tuple[Any, ...]) -> tuple[str, ...]:
    reasons: list[str] = []
    for value in values:
        reason = _bounded_label(value, MAX_REASON_CODE_CHARS).lower().replace(" ", "_")
        if not reason or _REASON_CODE.fullmatch(reason) is None or reason in reasons:
            continue
        reasons.append(reason)
        if len(reasons) == MAX_REASON_CODES:
            break
    return tuple(reasons)


def _state_status_from_mapping(raw: Mapping[str, Any]) -> TurnStateStatus:
    """Validate explicit state health without trusting truthy coercions."""

    if "state_known" not in raw:
        return "missing"
    if not isinstance(raw.get("state_known"), bool):
        return "corrupt"

    explicit = _bounded_label(raw.get("state_status"), 32).lower()
    if explicit and explicit not in TURN_STATE_STATUSES:
        return "corrupt"

    health_flags: list[TurnStateStatus] = []
    for field_name, status in (
        ("state_stale", "stale"),
        ("state_ambiguous", "ambiguous"),
        ("state_corrupt", "corrupt"),
    ):
        if field_name in raw and not isinstance(raw.get(field_name), bool):
            return "corrupt"
        if raw.get(field_name) is True:
            health_flags.append(status)
    if len(health_flags) > 1:
        return "corrupt"
    hinted = health_flags[0] if health_flags else ""
    if explicit and hinted and explicit != hinted:
        return "corrupt"

    status = explicit or hinted or ("current" if raw["state_known"] else "missing")
    if (status == "missing") != (raw["state_known"] is False):
        return "corrupt"
    return status  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class TurnState:
    """Bounded durable state that can change the meaning of a short reply."""

    previous_trace_id: str = ""
    state_known: bool = False
    state_status: str = ""
    previous_status: str = ""
    previous_turn_kind: str = ""
    active_plan: bool = False
    unfinished_work: bool = False
    pending_question: bool = False
    pending_authorization: bool = False
    retry_pending: bool = False
    configuration_revision: str = ""
    roster_revision: str = ""
    specialist_revision: str = ""
    delegation_revision: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> TurnState:
        if value is None:
            return cls(state_known=False, state_status="missing")
        if not isinstance(value, Mapping):
            return cls(state_known=False, state_status="corrupt")

        raw = value
        status = _state_status_from_mapping(raw)
        if any(
            field in raw and not isinstance(raw.get(field), bool) for field in _STATE_BOOLEAN_FIELDS
        ):
            status = "corrupt"
        if any(
            field in raw and raw.get(field) is not None and not isinstance(raw.get(field), str)
            for field in _STATE_LABEL_FIELDS
        ):
            status = "corrupt"

        previous_kind = _bounded_label(raw.get("previous_turn_kind"), 32)
        if previous_kind and previous_kind not in TURN_KINDS:
            status = "corrupt"
            previous_kind = ""

        fields: dict[str, Any] = {
            "previous_trace_id": _bounded_label(raw.get("previous_trace_id"), 128),
            "previous_status": _bounded_label(raw.get("previous_status"), 64),
            "previous_turn_kind": previous_kind,
            "active_plan": raw.get("active_plan") is True,
            "unfinished_work": raw.get("unfinished_work") is True,
            "pending_question": raw.get("pending_question") is True,
            "pending_authorization": raw.get("pending_authorization") is True,
            "retry_pending": raw.get("retry_pending") is True,
            "configuration_revision": _bounded_label(raw.get("configuration_revision"), 128),
            "roster_revision": _bounded_label(raw.get("roster_revision"), 128),
            "specialist_revision": _bounded_label(raw.get("specialist_revision"), 128),
            "delegation_revision": _bounded_label(raw.get("delegation_revision"), 128),
        }
        has_context = any(fields[field] for field in _STATE_BOOLEAN_FIELDS)
        if (fields["pending_question"] and fields["pending_authorization"]) or (
            has_context and not fields["previous_trace_id"]
        ):
            status = "ambiguous"
        elif (
            fields["previous_trace_id"]
            and (not fields["previous_status"] or not fields["previous_turn_kind"])
        ) or (
            not fields["previous_trace_id"]
            and (fields["previous_status"] or fields["previous_turn_kind"])
        ):
            status = "corrupt"

        def build(target_status: TurnStateStatus) -> TurnState:
            return cls(
                **fields,
                state_known=(
                    raw.get("state_known") is True and target_status not in {"missing", "corrupt"}
                ),
                state_status=target_status,
            )

        state = build(status)
        supplied_revision = raw.get("state_revision")
        if supplied_revision is not None:
            if (
                not isinstance(supplied_revision, str)
                or _STATE_REVISION.fullmatch(supplied_revision) is None
            ):
                status = "corrupt"
            elif status == "current" and supplied_revision != state.revision:
                status = "stale"
        return state if status == state.state_status else build(status)

    @property
    def effective_status(self) -> TurnStateStatus:
        status = _bounded_label(self.state_status, 32).lower()
        if status and status not in TURN_STATE_STATUSES:
            return "corrupt"
        declared = status or ("current" if self.state_known else "missing")
        if declared == "corrupt":
            return "corrupt"
        if (declared == "missing") != (self.state_known is False):
            return "corrupt"
        if self.pending_question and self.pending_authorization:
            return "ambiguous"
        if self.has_continuation_context and not self.previous_trace_id:
            return "ambiguous"
        if self.previous_trace_id and (not self.previous_status or not self.previous_turn_kind):
            return "corrupt"
        if not self.previous_trace_id and (self.previous_status or self.previous_turn_kind):
            return "corrupt"
        return declared  # type: ignore[return-value]

    @property
    def safe_for_bypass(self) -> bool:
        return self.state_known and self.effective_status == "current"

    @property
    def has_continuation_context(self) -> bool:
        return any(
            (
                self.active_plan,
                self.unfinished_work,
                self.pending_question,
                self.pending_authorization,
                self.retry_pending,
            )
        )

    @property
    def revision(self) -> str:
        payload = {
            "active_plan": self.active_plan,
            "configuration_revision": self.configuration_revision,
            "delegation_revision": self.delegation_revision,
            "pending_authorization": self.pending_authorization,
            "pending_question": self.pending_question,
            "previous_trace_id": self.previous_trace_id,
            "previous_status": self.previous_status,
            "state_known": self.state_known,
            "state_status": self.effective_status,
            "previous_turn_kind": self.previous_turn_kind,
            "retry_pending": self.retry_pending,
            "roster_revision": self.roster_revision,
            "specialist_revision": self.specialist_revision,
            "unfinished_work": self.unfinished_work,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()

    def as_dict(self) -> dict[str, bool | str]:
        return {
            "previous_trace_id": self.previous_trace_id,
            "state_known": self.state_known,
            "state_status": self.effective_status,
            "previous_status": self.previous_status,
            "previous_turn_kind": self.previous_turn_kind,
            "active_plan": self.active_plan,
            "unfinished_work": self.unfinished_work,
            "pending_question": self.pending_question,
            "pending_authorization": self.pending_authorization,
            "retry_pending": self.retry_pending,
            "configuration_revision": self.configuration_revision,
            "roster_revision": self.roster_revision,
            "specialist_revision": self.specialist_revision,
            "delegation_revision": self.delegation_revision,
            "state_revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class TurnClassification:
    """One deterministic, replayable turn-intent decision."""

    turn_kind: TurnKind
    selection_required: bool
    reroute_required: bool
    execution_decision_required: bool
    continuation_of: str
    confidence: float
    reason_codes: tuple[str, ...]
    state_revision: str
    classifier_version: int = TURN_CLASSIFIER_VERSION
    message_fingerprint: str = ""
    _attestation: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.turn_kind not in TURN_KINDS:
            raise ValueError("turn_kind is invalid")
        for field_name in (
            "selection_required",
            "reroute_required",
            "execution_decision_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be a boolean")
        if (
            isinstance(self.classifier_version, bool)
            or not isinstance(self.classifier_version, int)
            or self.classifier_version not in SUPPORTED_TURN_CLASSIFIER_VERSIONS
        ):
            raise ValueError("classifier_version is unsupported")

        continuation = validate_correlation_id(
            self.continuation_of,
            field="continuation_of",
            required=False,
        )
        decisions = (
            self.selection_required,
            self.reroute_required,
            self.execution_decision_required,
        )
        allowed = {
            "acknowledgement": {(False, False, False), (True, True, True)},
            "conversation": (
                {(True, True, True), (False, False, False)}
                if self.classifier_version >= 4
                else {(True, True, True)}
            ),
            "control": {(False, False, False)},
            "continuation": {(True, False, True), (True, True, True)},
            "new_intent": {(True, True, True)},
            "revision": {(True, True, True)},
        }
        if decisions not in allowed[self.turn_kind]:
            raise ValueError("turn classification decision combination is invalid")
        correlation_required = self.turn_kind in {"continuation", "revision"}
        if correlation_required != bool(continuation):
            raise ValueError("turn classification continuation correlation is invalid")

        state_revision = str(self.state_revision or "").strip()
        message_fingerprint = str(self.message_fingerprint or "").strip()
        if _STATE_REVISION.fullmatch(state_revision) is None:
            raise ValueError("state_revision must be a SHA-256 digest")
        if _STATE_REVISION.fullmatch(message_fingerprint) is None:
            raise ValueError("message_fingerprint must be a SHA-256 digest")
        object.__setattr__(self, "continuation_of", continuation)
        object.__setattr__(self, "confidence", _bounded_confidence(self.confidence))
        object.__setattr__(self, "reason_codes", _bounded_reason_codes(self.reason_codes))
        object.__setattr__(self, "state_revision", state_revision)
        object.__setattr__(self, "message_fingerprint", message_fingerprint)

    @property
    def legacy_request_kind(self) -> str:
        """Project the old completion-policy bit without granting it authority."""

        return "nontrivial" if self.selection_required else "trivial"

    @property
    def pure_acknowledgement(self) -> bool:
        return self.turn_kind == "acknowledgement" and not self.selection_required

    def as_dict(self) -> dict[str, Any]:
        return {
            "turn_kind": self.turn_kind,
            "selection_required": self.selection_required,
            "reroute_required": self.reroute_required,
            "execution_decision_required": self.execution_decision_required,
            "continuation_of": self.continuation_of,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "state_revision": self.state_revision,
            "classifier_version": self.classifier_version,
            "message_fingerprint": self.message_fingerprint,
            "legacy_request_kind": self.legacy_request_kind,
        }


@dataclass(frozen=True, slots=True)
class PendingInteraction:
    """Content-free state derived from a terminal assistant response."""

    kind: Literal["", "question", "authorization"] = ""
    response_fingerprint: str = ""

    @property
    def pending_question(self) -> bool:
        return self.kind == "question"

    @property
    def pending_authorization(self) -> bool:
        return self.kind == "authorization"

    def as_dict(self) -> dict[str, bool | str]:
        return {
            "kind": self.kind,
            "response_fingerprint": self.response_fingerprint,
            "pending_question": self.pending_question,
            "pending_authorization": self.pending_authorization,
        }


def _response_body(response_text: str) -> str:
    lines = str(response_text or "")[:MAX_TURN_SIGNAL_CHARS].splitlines()
    if len(lines) >= 6 and all(":" in line for line in lines[:6]):
        labels = tuple(line.split(":", 1)[0].strip() for line in lines[:6])
        if labels == (
            "Agency/Agencies loaded",
            "Agency/Agencies delegated",
            "Skills loaded",
            "Actual Model selected",
            "Why",
            "How it shaped outcome",
        ):
            lines = lines[6:]
    return "\n".join(lines).strip()


def classify_pending_interaction(response_text: str) -> PendingInteraction:
    """Project a direct terminal question into bounded continuation state."""

    body = _response_body(response_text)
    if not body:
        return PendingInteraction()
    digest = sha256(body.encode("utf-8", errors="surrogatepass")).hexdigest()
    tail = body[-4_096:].strip()
    authorization = bool(
        _AUTHORIZATION_REPLY.search(tail) or (_AUTHORIZATION_QUESTION.search(tail) and "?" in tail)
    )
    if authorization:
        return PendingInteraction("authorization", digest)
    if tail.endswith("?"):
        return PendingInteraction("question", digest)
    return PendingInteraction()


def _decision(
    kind: TurnKind,
    state: TurnState,
    message: str,
    *reasons: str,
    confidence: float,
    selection_required: bool,
    reroute_required: bool,
    execution_decision_required: bool,
    correlate: bool = True,
) -> TurnClassification:
    decision = TurnClassification(
        turn_kind=kind,
        selection_required=bool(selection_required),
        reroute_required=bool(reroute_required),
        execution_decision_required=bool(execution_decision_required),
        continuation_of=(
            state.previous_trace_id if correlate and kind in {"continuation", "revision"} else ""
        ),
        confidence=confidence,
        reason_codes=tuple(reasons),
        state_revision=state.revision,
        message_fingerprint=_message_fingerprint(message),
    )
    return _seal_turn_classification(decision)


def _message_fingerprint(message: str) -> str:
    return sha256(str(message).encode("utf-8", errors="surrogatepass")).hexdigest()


def _classification_payload(value: TurnClassification) -> bytes:
    return "\0".join(
        (
            value.turn_kind,
            str(int(value.selection_required)),
            str(int(value.reroute_required)),
            str(int(value.execution_decision_required)),
            value.continuation_of,
            format(value.confidence, ".17g"),
            *value.reason_codes,
            "--state--",
            value.state_revision,
            str(value.classifier_version),
            value.message_fingerprint,
        )
    ).encode("utf-8")


def _seal_turn_classification(value: TurnClassification) -> TurnClassification:
    signature = hmac.new(
        _TURN_CLASSIFICATION_KEY,
        _classification_payload(value),
        "sha256",
    ).hexdigest()
    return replace(value, _attestation=signature)


def _classification_attestation_valid(value: object) -> bool:
    if (
        not isinstance(value, TurnClassification)
        or value.classifier_version != TURN_CLASSIFIER_VERSION
        or not value._attestation
    ):
        return False
    expected = hmac.new(
        _TURN_CLASSIFICATION_KEY,
        _classification_payload(value),
        "sha256",
    ).hexdigest()
    return hmac.compare_digest(value._attestation, expected)


def authoritative_turn_classification(
    value: object,
    message: str,
) -> TurnClassification | None:
    """Return a current process-sealed decision bound to this exact message."""

    if not _classification_attestation_valid(
        value
    ) or value.message_fingerprint != _message_fingerprint(message):
        return None
    return value


def force_fresh_turn_reroute(
    value: TurnClassification,
    reason: str,
    *,
    untrusted_origin: bool = False,
) -> TurnClassification:
    """Derive a sealed fresh-route decision without retaining a bypass."""

    if not _classification_attestation_valid(value):
        raise ValueError("turn classification is not authoritative")
    kind: TurnKind = value.turn_kind
    continuation_of = value.continuation_of
    if kind == "control":
        kind = "new_intent"
        continuation_of = ""
    updated = TurnClassification(
        turn_kind=kind,
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        continuation_of=continuation_of,
        confidence=min(value.confidence, 0.5) if untrusted_origin else value.confidence,
        reason_codes=(*value.reason_codes, reason),
        state_revision=value.state_revision,
        classifier_version=TURN_CLASSIFIER_VERSION,
        message_fingerprint=value.message_fingerprint,
    )
    return _seal_turn_classification(updated)


def _untrusted_state_decision(
    text: str,
    state: TurnState,
    raw_message: str,
) -> TurnClassification:
    """Preserve a proven surface kind while refusing an unsafe selection bypass."""

    status_reason = f"turn_state_{state.effective_status}"
    if _PURE_ACKNOWLEDGEMENT.fullmatch(text):
        kind: TurnKind = "acknowledgement"
        signal_reason = "acknowledgement_state_untrusted"
        confidence = 0.5
    elif _PURE_CONVERSATION.fullmatch(text):
        kind = "conversation"
        signal_reason = "conversation_state_untrusted"
        confidence = 0.5
    elif _REVISION_PREFIX.match(text):
        kind = "new_intent"
        signal_reason = "revision_without_trusted_state"
        confidence = 0.5
    elif _CONTEXTUAL_CONTINUATION.fullmatch(text):
        kind = "new_intent"
        signal_reason = "continuation_without_trusted_state"
        confidence = 0.5
    else:
        kind = "new_intent"
        signal_reason = "requested_question_task_or_output"
        confidence = 0.85
    return _decision(
        kind,
        state,
        raw_message,
        status_reason,
        signal_reason,
        confidence=confidence,
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        correlate=False,
    )


def classify_turn_intent(
    message: str,
    state: TurnState | Mapping[str, Any] | None = None,
) -> TurnClassification:
    """Classify one external user turn without a length-based bypass."""

    current_state = state if isinstance(state, TurnState) else TurnState.from_mapping(state)
    raw_message = str(message or "")
    text = " ".join(raw_message[:MAX_TURN_SIGNAL_CHARS].split())
    if not text:
        raise ValueError("turn message is required")

    if parse_runtime_control_command(text) is not None:
        return _decision(
            "control",
            current_state,
            raw_message,
            "exact_runtime_control",
            confidence=1.0,
            selection_required=False,
            reroute_required=False,
            execution_decision_required=False,
        )

    if not current_state.safe_for_bypass:
        return _untrusted_state_decision(text, current_state, raw_message)

    if current_state.has_continuation_context:
        if _REVISION_PREFIX.match(text):
            return _decision(
                "revision",
                current_state,
                raw_message,
                "active_state",
                "requirements_changed",
                confidence=0.96,
                selection_required=True,
                reroute_required=True,
                execution_decision_required=True,
            )
        if current_state.pending_authorization:
            return _decision(
                "continuation",
                current_state,
                raw_message,
                "active_state",
                "pending_authorization",
                "authorization_response",
                "continuation_reply_requires_reroute",
                confidence=0.96,
                selection_required=True,
                reroute_required=True,
                execution_decision_required=True,
            )
        if current_state.pending_question:
            return _decision(
                "continuation",
                current_state,
                raw_message,
                "active_state",
                "pending_question",
                "question_response",
                "continuation_reply_requires_reroute",
                confidence=0.96,
                selection_required=True,
                reroute_required=True,
                execution_decision_required=True,
            )
        if _CONTEXTUAL_CONTINUATION.fullmatch(text):
            return _decision(
                "continuation",
                current_state,
                raw_message,
                "active_state",
                "contextual_reply",
                confidence=0.99,
                selection_required=True,
                reroute_required=False,
                execution_decision_required=True,
            )
        if _PURE_ACKNOWLEDGEMENT.fullmatch(text) or _PURE_CONVERSATION.fullmatch(text):
            return _decision(
                "continuation",
                current_state,
                raw_message,
                "unfinished_work",
                "acknowledgement_cannot_bypass_active_state",
                confidence=0.98,
                selection_required=True,
                reroute_required=False,
                execution_decision_required=True,
            )

    if _PURE_ACKNOWLEDGEMENT.fullmatch(text):
        return _decision(
            "acknowledgement",
            current_state,
            raw_message,
            "pure_acknowledgement",
            "no_pending_state",
            confidence=0.99,
            selection_required=False,
            reroute_required=False,
            execution_decision_required=False,
        )

    if _PURE_CONVERSATION.fullmatch(text):
        return _decision(
            "conversation",
            current_state,
            raw_message,
            "pure_social_conversation",
            "no_pending_state",
            confidence=0.99,
            selection_required=False,
            reroute_required=False,
            execution_decision_required=False,
        )

    if (
        _CONTEXTUAL_CONTINUATION.fullmatch(text)
        or _PURE_ACKNOWLEDGEMENT.fullmatch(text)
        or _PURE_CONVERSATION.fullmatch(text)
    ):
        return _decision(
            "new_intent",
            current_state,
            raw_message,
            "ambiguous_reply_without_valid_state",
            confidence=0.5,
            selection_required=True,
            reroute_required=True,
            execution_decision_required=True,
        )

    return _decision(
        "new_intent",
        current_state,
        raw_message,
        "requested_question_task_or_output",
        confidence=0.9,
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
    )


def is_pure_acknowledgement(
    message: str,
    state: TurnState | Mapping[str, Any] | None = None,
) -> bool:
    """Return whether this exact state proves the turn is only acknowledgement."""

    return classify_turn_intent(message, state).pure_acknowledgement


__all__ = [
    "MAX_REASON_CODES",
    "MAX_REASON_CODE_CHARS",
    "MAX_TURN_SIGNAL_CHARS",
    "SUPPORTED_TURN_CLASSIFIER_VERSIONS",
    "TURN_CLASSIFIER_VERSION",
    "TURN_KINDS",
    "TURN_STATE_STATUSES",
    "PendingInteraction",
    "TurnClassification",
    "TurnKind",
    "TurnState",
    "TurnStateStatus",
    "authoritative_turn_classification",
    "classify_pending_interaction",
    "classify_turn_intent",
    "force_fresh_turn_reroute",
    "is_pure_acknowledgement",
]
