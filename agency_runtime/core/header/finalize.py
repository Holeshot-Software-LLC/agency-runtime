"""Finalization gate for Agency Runtime responses."""

from __future__ import annotations

import warnings
from collections.abc import Mapping
from hashlib import sha256
from typing import Any, TypedDict

from .contract import (
    HEADER_FIELDS,
    EvidenceCorrelationError,
    fill_header_fields,
    format_header,
    parse_header,
    read_completion_evidence_snapshot,
    validate_completion_policy,
    validate_header,
)


class FinalizationResult(TypedDict):
    action: str
    text: str
    missing: list[str]


class FinalizationBatchResult(FinalizationResult):
    evidence_receipt: dict[str, Any] | None


TERMINAL_ACTION_STATUS = {
    "accept": "completed",
    "delegation_declined": "delegation_declined",
    "retry_exhausted": "retry_exhausted",
}
TERMINAL_OUTCOME_MESSAGES = {
    "delegation_declined": (
        "AGENCY DELEGATION DECLINED: The native host did not execute the strongly "
        "preferred delegation after Agency's single correction opportunity. The turn is "
        "terminal; no further correction is requested."
    ),
    "retry_exhausted": (
        "AGENCY RETRY EXHAUSTED: Agency used its single response-correction opportunity "
        "and recorded this exact response as terminal. No further correction is requested."
    ),
}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def response_hash(response_text: str) -> str:
    """Return a content-free fingerprint for exact final-response replay."""
    return sha256(str(response_text).encode("utf-8", errors="surrogatepass")).hexdigest()


def accepted_response_run(
    store: Any,
    session_id: str,
    trace_id: str,
    response_text: str,
) -> dict[str, Any] | None:
    """Return an authoritative terminal accept when its exact digest matches."""
    return terminal_response_run(
        store,
        session_id,
        trace_id,
        response_text,
        action="accept",
    )


def terminal_response_run(
    store: Any,
    session_id: str,
    trace_id: str,
    response_text: str,
    *,
    action: str = "",
) -> dict[str, Any] | None:
    """Return the authoritative terminal event for one exact response digest."""

    if not session_id or not trace_id or not response_text:
        return None
    getter = getattr(store, "get_authoritative_finalization", None)
    if not callable(getter):
        raise EvidenceCorrelationError("terminal response evidence could not be verified")
    try:
        finalization = getter(
            session_id,
            trace_id,
            action=action,
            response_hash=response_hash(response_text),
        )
    except Exception as exc:
        raise EvidenceCorrelationError("terminal response evidence could not be verified") from exc
    if finalization is None:
        return None
    if not isinstance(finalization, Mapping):
        raise EvidenceCorrelationError("terminal response correlation could not be verified")
    return dict(finalization)


def _metadata_value(metadata: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return _clean(value)
    return default


def _starts_with_header(text: str) -> bool:
    lines = text.splitlines()
    return len(lines) >= len(HEADER_FIELDS) and all(
        lines[index].startswith(f"{label}:") for index, (_key, label) in enumerate(HEADER_FIELDS)
    )


def _body_after_possible_header(text: str) -> str:
    if not _starts_with_header(text):
        return text.strip()
    return "\n".join(text.splitlines()[len(HEADER_FIELDS) :]).strip()


def _observation_action(action: str) -> str:
    """Keep public validation observations out of host retry receipts."""

    return "validation_continue" if action == "continue" else action


def _correlation_missing(
    store: Any,
    session_id: str,
    trace_id: str,
) -> list[str]:
    missing = [
        name for name, value in (("session_id", session_id), ("trace_id", trace_id)) if not value
    ]
    if missing:
        return missing
    if store is None:
        return ["evidence_store"]
    return []


def finalize_response(
    draft_text: str,
    trace_metadata: Mapping[str, Any] | None = None,
    store: Any | None = None,
    model: str = "",
) -> FinalizationResult:
    """Apply the Agency header finalization gate.

    Returns ``action='accept'`` when the response is finalizable, ``rewrite``
    when any of the six required header fields remain missing after attempted
    auto-fill, and ``continue`` when there is no substantive draft body yet.
    """
    metadata = dict(trace_metadata or {})
    session_id = metadata.get("session_id", metadata.get("session", ""))
    trace_id = metadata.get("trace_id", metadata.get("trace", ""))
    host = _metadata_value(metadata, "host", "runtime", default="unknown") or "unknown"
    requested_model = model or _metadata_value(metadata, "requested_model", "model", default="")

    correlation_missing = _correlation_missing(store, session_id, trace_id)
    if correlation_missing:
        # Never manufacture an authoritative-looking loaded:none header when
        # there is no deterministic turn to query.
        return {
            "action": "continue",
            "text": draft_text,
            "missing": correlation_missing,
        }
    try:
        replay = accepted_response_run(store, session_id, trace_id, draft_text)
    except EvidenceCorrelationError:
        return {
            "action": "continue",
            "text": draft_text,
            "missing": ["evidence_verification"],
        }
    if replay is not None:
        if (
            replay.get("authoritative") is not True
            or str(replay.get("action") or "") != "accept"
            or str(replay.get("terminal_status") or "") != "completed"
            or str(replay.get("status") or "") != "completed"
        ):
            return {
                "action": "continue",
                "text": draft_text,
                "missing": ["evidence_verification"],
            }
        return {"action": "accept", "text": draft_text, "missing": []}
    try:
        evidence_snapshot = read_completion_evidence_snapshot(
            store,
            session_id,
            trace_id,
        )
    except EvidenceCorrelationError as error:
        detail = _clean(error)
        if "specialist activation" in detail:
            return {
                "action": "continue",
                "text": draft_text,
                "missing": ["specialist_activation"],
            }
        correlation_failure = any(
            marker in detail
            for marker in (
                "session_id is required",
                "trace_id is required",
                "trace_id does not identify",
                "trace_id does not belong",
                "terminal Agency turn",
            )
        )
        return {
            "action": "continue",
            "text": draft_text,
            "missing": ["correlation" if correlation_failure else "evidence_verification"],
        }

    if not _clean(draft_text):
        result: FinalizationResult = {
            "action": "continue",
            "text": draft_text,
            "missing": ["draft_text"],
        }
        _record_finalization(
            store,
            trace_id,
            host,
            _observation_action(result["action"]),
            result["missing"],
        )
        return result

    parsed = parse_header(draft_text) if _starts_with_header(draft_text) else {}
    has_header = bool(parsed)
    body = _body_after_possible_header(draft_text)
    try:
        fields = fill_header_fields(
            parsed,
            session_id,
            store,
            requested_model,
            trace_id,
            evidence_snapshot=evidence_snapshot,
        )
    except EvidenceCorrelationError as error:
        result = {
            "action": "continue",
            "text": draft_text,
            "missing": (
                ["specialist_activation"]
                if "specialist activation" in _clean(error)
                else ["evidence_verification"]
            ),
        }
        _record_finalization(store, trace_id, host, result["action"], result["missing"])
        return result
    header = format_header(fields)
    text = f"{header}\n\n{body}" if body else header

    valid, missing = validate_header(text)
    action = "accept" if valid else "rewrite"
    if not body:
        action = "continue"
        missing = missing or ["response_body"]
    elif not has_header:
        # Missing header was fully auto-filled.  The returned text is the
        # rewrite the caller should emit, but no fields remain missing.
        action = "accept" if valid else "rewrite"

    if action == "accept":
        violation = validate_completion_policy(
            text,
            session_id=session_id,
            trace_id=trace_id,
            store=store,
            model=requested_model,
            evidence_snapshot=evidence_snapshot,
        )
        if violation is not None:
            action = "continue"
            missing = violation["missing"]

    result = {"action": action, "text": text, "missing": missing}
    if action == "accept":
        commit_failure = _commit_terminal_finalization(
            store,
            session_id=session_id,
            trace_id=trace_id,
            host=host,
            response_text=text,
            expected_evidence_revision=int(evidence_snapshot["evidence_revision"]),
        )
        if commit_failure:
            return {
                "action": "continue",
                "text": text,
                "missing": [commit_failure],
            }
    else:
        _record_finalization(
            store,
            trace_id,
            host,
            _observation_action(action),
            missing,
        )
    return result


def finalize_response_batch(
    draft_text: str,
    trace_metadata: Mapping[str, Any],
    store: Any,
    *,
    skills_loaded: object,
    delegations: object,
    model: str = "",
) -> FinalizationBatchResult:
    """Finalize caller evidence and the terminal response in one Store transaction."""

    metadata = dict(trace_metadata)
    session_id = _metadata_value(metadata, "session_id", "session", default="")
    trace_id = _metadata_value(metadata, "trace_id", "trace", default="")
    runner = getattr(store, "finalize_evidence_batch", None)
    if not callable(runner):
        return {
            "action": "continue",
            "text": draft_text,
            "missing": ["evidence_persistence"],
            "evidence_receipt": None,
        }

    def finalize_in_transaction(
        transaction_store: Any, authoritative_host: str
    ) -> FinalizationResult:
        return finalize_response(
            draft_text,
            trace_metadata={
                **metadata,
                "session_id": str(session_id),
                "trace_id": str(trace_id),
                "host": authoritative_host,
            },
            store=transaction_store,
            model=model,
        )

    envelope = runner(
        session_id=session_id,
        trace_id=trace_id,
        skills_loaded=skills_loaded,
        delegations=delegations,
        finalizer=finalize_in_transaction,
    )
    finalization = dict(envelope["finalization"])
    return {
        "action": finalization["action"],
        "text": finalization["text"],
        "missing": list(finalization["missing"]),
        "evidence_receipt": envelope["receipt"],
    }


def finalize(
    draft_text: str,
    trace_metadata: Mapping[str, Any] | None = None,
    store: Any | None = None,
    model: str = "",
) -> FinalizationResult:
    """Deprecated compatibility alias for :func:``finalize_response``."""

    warnings.warn(
        (
            "finalize() is deprecated; call finalize_response(). "
            "It will not be removed before agency-runtime 0.3.0."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return finalize_response(
        draft_text,
        trace_metadata=trace_metadata,
        store=store,
        model=model,
    )


def _record_finalization(
    store: Any,
    trace_id: str,
    host: str,
    action: str,
    missing: list[str],
    *,
    response_text: str = "",
) -> bool:
    recorder = getattr(store, "record_finalization", None)
    if not callable(recorder) or not trace_id:
        return False
    try:
        recorder(
            trace_id=trace_id,
            host=host,
            action=action,
            missing=missing,
            response_hash=response_hash(response_text) if response_text else "",
        )
    except Exception:
        return False
    return True


def _commit_terminal_finalization(
    store: Any,
    *,
    session_id: str,
    trace_id: str,
    host: str,
    response_text: str,
    expected_evidence_revision: int,
) -> str:
    """Atomically bind one exact accepted response and close its turn."""
    committer = getattr(store, "commit_terminal_finalization", None)
    if not callable(committer):
        return "evidence_persistence"
    digest = response_hash(response_text)
    from agency_runtime.core.turn_intent import classify_pending_interaction

    pending = classify_pending_interaction(response_text)
    try:
        result = committer(
            session_id=session_id,
            trace_id=trace_id,
            host=host,
            action="accept",
            response_hash=digest,
            status="completed",
            expected_evidence_revision=expected_evidence_revision,
            pending_interaction_kind=pending.kind,
            pending_interaction_fingerprint=pending.response_fingerprint,
        )
    except Exception:
        return "evidence_persistence"
    accepted = bool(
        isinstance(result, Mapping)
        and result.get("authoritative") is True
        and result.get("outcome") in {"committed", "replay"}
        and result.get("action") == "accept"
        and result.get("response_hash") == digest
        and result.get("status") == "completed"
    )
    if accepted:
        return ""
    if isinstance(result, Mapping) and result.get("outcome") == "stale_evidence":
        return "evidence_changed"
    return "evidence_persistence"


__all__ = [
    "FinalizationBatchResult",
    "FinalizationResult",
    "accepted_response_run",
    "finalize",
    "finalize_response",
    "finalize_response_batch",
    "response_hash",
    "terminal_response_run",
]
