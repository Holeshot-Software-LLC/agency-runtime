"""JSON bridge used by the OpenClaw JavaScript plugin.

OpenClaw plugins run in Node, while Agency Runtime routing lives in Python. Keep
this bridge tiny: stdin JSON in, stdout JSON out, shared SQLite store for state.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.header.finalize import (
    TERMINAL_ACTION_STATUS,
    TERMINAL_OUTCOME_MESSAGES,
    response_hash,
)

MAX_INPUT_BYTES = 1_048_576
MAX_MODEL_CHARS = 512
MAX_TOOL_NAME_CHARS = 512
MAX_BRIDGE_OUTPUT_BYTES = 65_536
MAX_VISIBLE_MESSAGE_JSON_BYTES = 40_000
MAX_PREFLIGHT_CONTEXT_CHARS = 48_000
_VERIFICATION_UNAVAILABLE = (
    "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Turn-scoped evidence could not be "
    "verified or persisted. Do not finalize this response; restore the evidence "
    "store and start a new turn."
)
_TERMINAL_REJECTION_MESSAGE = (
    "Agency Runtime blocked this response because its required evidence contract "
    "was invalid. No correction was requested or accepted; start a new turn after "
    "restoring the runtime or fixing first-pass header generation."
)
_TERMINAL_MISMATCH_MESSAGE = (
    "AGENCY TURN TERMINAL: The submitted response does not match the exact response "
    "bound to this terminal trace. It cannot be revised or published; begin a new user turn."
)
_REPLY_DIRECTIVE = re.compile(
    r"\A\s*\[\[\s*(?:reply_to_current|reply_to\s*:\s*[^\]\r\n]{1,256})\s*\]\]\s*",
    re.IGNORECASE,
)
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]\r\n]{0,1024}\]\([^\)\r\n]{1,4096}\)")


def _normalized_pre_finalize_text(value: str) -> str:
    """Mirror bounded OpenClaw reply-directive and image extraction for policy."""

    without_directive = _REPLY_DIRECTIVE.sub("", value, count=1)
    return _MARKDOWN_IMAGE.sub("", without_directive).strip()


def _bounded_string(
    payload: dict[str, Any],
    key: str,
    *,
    limit: int,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or "\x00" in value:
        return ""
    return value[:limit]


def _attempt_number(payload: dict[str, Any]) -> int:
    value = payload.get("attempt", 0)
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    return parsed if 0 <= parsed <= 100 else 0


def _read_payload() -> dict[str, Any]:
    try:
        stream = getattr(sys.stdin, "buffer", sys.stdin)
        raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            return {"action": "", "error": "hook payload exceeds 1 MiB"}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = safe_load_bounded_json(raw)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return {"action": "", "error": f"invalid json: {exc}"}
    return (
        payload
        if isinstance(payload, dict)
        else {"action": "", "error": "payload must be an object"}
    )


def _is_authenticated_retry(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    message: str,
) -> bool:
    """Suppress only an exact durable retry; prompt content has no authority."""

    del message
    resolver = getattr(adapter.store, "resolve_pending_internal_retry", None)
    if not callable(resolver) or not session_id or not trace_id:
        return False
    try:
        resolved = resolver(session_id, trace_id)
    except Exception:
        return False
    return resolved == trace_id


def _preflight_origin(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    message: str,
) -> Any:
    """Seal one OpenClaw prompt-build origin from durable lifecycle state."""

    from agency_runtime.core.turn_origin import native_adapter_turn_origin

    internal = _is_authenticated_retry(
        adapter,
        session_id=session_id,
        trace_id=trace_id,
        message=message,
    )
    return native_adapter_turn_origin(
        "internal_retry" if internal else "external_user",
        host="openclaw",
        event="before_prompt_build_retry" if internal else "before_prompt_build",
        session_id=session_id,
        trace_id=trace_id,
    )


def _resolve_turn_trace(adapter: Any, session_id: str, trace_id: str) -> str:
    """Preserve explicit correlation for minimal or older adapter surfaces."""
    resolver = getattr(adapter, "resolve_turn_trace", None)
    return resolver(session_id, trace_id) if callable(resolver) else trace_id


def _bounded_visible_message(message: object) -> str:
    """Return text whose ASCII-safe JSON representation fits the bridge budget."""

    value = str(message or _VERIFICATION_UNAVAILABLE)
    encoded = json.dumps(value, ensure_ascii=True).encode("ascii")
    if len(encoded) > MAX_VISIBLE_MESSAGE_JSON_BYTES:
        return _VERIFICATION_UNAVAILABLE
    return value


def _revision(message: str = _VERIFICATION_UNAVAILABLE) -> dict[str, Any]:
    """Return a legacy-callable, non-corrective verification failure envelope."""
    return _terminal_rejection_result(
        status="verification_failed",
        message=_bounded_visible_message(message),
        final_response="",
        trace_id="",
    )


def _header_snapshot_context(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    model: str,
) -> str:
    """Render exact first-pass header guidance from current-turn Store evidence."""

    if not session_id or not trace_id:
        return ""
    from agency_runtime.core.header.contract import (
        EvidenceCorrelationError,
        fill_header_fields,
        format_header,
    )

    try:
        header = format_header(
            fill_header_fields(
                {},
                session_id,
                adapter.store,
                model,
                trace_id,
            )
        )
    except (EvidenceCorrelationError, KeyError, RuntimeError, TypeError, ValueError):
        return ""
    return (
        "[AGENCY FIRST-PASS FINALIZATION CONTRACT]\n"
        "MANDATORY: this turn remains incomplete until the Store-backed native "
        "finalizer has constructed the first visible response.\n"
        "[AGENCY INITIAL HEADER SNAPSHOT v1]\n"
        "Use these exact seven lines for substantive progress until Agency evidence "
        "changes. Immediately before the natural final response, call the OpenClaw-native "
        "`agency_finalize` tool (backed by Agency `agency.finalize`) exactly once with "
        f"session_id `{session_id}`, trace_id `{trace_id}`, and the "
        "response body as draft_text; emit its returned text byte-for-byte. That local "
        "tool constructs the first visible header from current Store evidence. Never "
        "guess changed values and never wait for a host correction.\n"
        f"{header}\n"
        "[AGENCY FINALIZATION GATE]\n"
        "After every other tool call, call `agency_finalize` exactly once as the final "
        "tool before emitting any natural final response. There is no correction pass."
    )


def _append_header_snapshot(
    result: dict[str, Any],
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    model: str,
) -> dict[str, Any]:
    """Append an exact snapshot without exceeding the bridge context budget."""

    snapshot = _header_snapshot_context(
        adapter,
        session_id=session_id,
        trace_id=trace_id,
        model=model,
    )
    if not snapshot:
        return result
    current = result.get("context")
    base = current.rstrip() if isinstance(current, str) else ""
    combined = f"{base}\n\n{snapshot}" if base else snapshot
    if len(combined.encode("utf-8")) > MAX_PREFLIGHT_CONTEXT_CHARS:
        return result
    return {**result, "context": combined}


def _recover_exact_terminal_trace(
    adapter: Any,
    session_id: str,
    final_response: str,
    *,
    response_digest: str = "",
) -> str:
    """Recover public-finalization correlation only when no turn is open."""
    if not session_id or not final_response:
        return ""
    open_trace_getter = getattr(adapter.store, "get_open_traces_for_session", None)
    finder_name = (
        "find_authoritative_trace" if response_digest else "find_authoritative_trace_by_policy_hash"
    )
    if not callable(open_trace_getter):
        raise RuntimeError("terminal turn correlation cannot be verified")
    open_traces = [str(value) for value in open_trace_getter(session_id) if str(value)]
    if open_traces:
        return ""
    finder = getattr(adapter.store, finder_name, None)
    if not callable(finder):
        raise RuntimeError("terminal turn correlation cannot be verified")

    digest = response_digest or response_hash(final_response)
    hash_argument = (
        {"response_hash": digest} if response_digest else {"policy_response_hash": digest}
    )
    resolved: set[str] = set()
    legacy_finder = getattr(adapter.store, "find_authoritative_trace", None)
    getter = getattr(adapter.store, "get_authoritative_finalization", None)
    for action in TERMINAL_ACTION_STATUS:
        candidate = finder(session_id, action=action, **hash_argument)
        if candidate is not None:
            if not isinstance(candidate, str) or not candidate.strip():
                raise RuntimeError("terminal response correlation is invalid")
            resolved.add(candidate.strip())
            continue
        if response_digest or not callable(legacy_finder) or not callable(getter):
            continue
        legacy_trace = legacy_finder(
            session_id,
            action=action,
            response_hash=digest,
        )
        legacy = (
            getter(
                session_id,
                legacy_trace,
                action=action,
                response_hash=digest,
            )
            if legacy_trace
            else None
        )
        if isinstance(legacy, dict) and not str(legacy.get("policy_response_hash") or ""):
            if not isinstance(legacy_trace, str) or not legacy_trace.strip():
                raise RuntimeError("terminal response correlation is invalid")
            resolved.add(legacy_trace.strip())
    if not resolved:
        return ""
    if len(resolved) != 1:
        raise RuntimeError("terminal response correlation is invalid")
    return resolved.pop()


def _effective_pre_verify_trace(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    final_response: str,
) -> str:
    """Resolve an open turn or recover an exact public-finalization digest."""
    effective_trace = _resolve_turn_trace(adapter, session_id, trace_id)
    if trace_id or effective_trace:
        return effective_trace
    return _recover_exact_terminal_trace(adapter, session_id, final_response)


def _accept_exact_finalized_response(
    adapter: Any,
    session_id: str,
    trace_id: str,
    final_response: str,
) -> bool:
    """Idempotently accept an exact response finalized before this callback."""
    return (
        _exact_policy_terminal_state(
            adapter,
            session_id=session_id,
            trace_id=trace_id,
            final_response=final_response,
        )
        == "completed"
    )


def _exact_policy_terminal_state(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    final_response: str,
) -> str:
    """Return the exact policy-text terminal state for any final action."""

    if not session_id or not trace_id:
        return ""
    getter = getattr(adapter.store, "get_authoritative_finalization", None)
    if not callable(getter):
        raise RuntimeError("terminal response evidence could not be verified")
    digest = response_hash(final_response)
    matches: list[str] = []
    for action, status in TERMINAL_ACTION_STATUS.items():
        run = getter(
            session_id,
            trace_id,
            action=action,
            policy_response_hash=digest,
        )
        if run is None:
            legacy = getter(
                session_id,
                trace_id,
                action=action,
                response_hash=digest,
            )
            if isinstance(legacy, dict) and not str(legacy.get("policy_response_hash") or ""):
                run = legacy
        if run is None:
            continue
        policy_digest = str(run.get("policy_response_hash") or "") if isinstance(run, dict) else ""
        stored_digest = policy_digest or (
            str(run.get("response_hash") or "") if isinstance(run, dict) else ""
        )
        if (
            not isinstance(run, dict)
            or run.get("authoritative") is not True
            or str(run.get("action") or "") != action
            or str(run.get("terminal_status") or "") != status
            or str(run.get("status") or "") != status
            or stored_digest != digest
        ):
            raise RuntimeError("terminal response evidence is inconsistent")
        matches.append(status)
    if len(matches) > 1:
        raise RuntimeError("terminal response evidence is ambiguous")
    return matches[0] if matches else ""


def _terminal_pre_verify_result(action: str, final_response: str, trace_id: str) -> dict[str, Any]:
    """Return a non-corrective exact terminal result for OpenClaw."""

    message = TERMINAL_OUTCOME_MESSAGES.get(action)
    if message is None:
        raise RuntimeError("terminal rejection action is invalid")
    return _terminal_rejection_result(
        status=action,
        message=message,
        final_response=final_response,
        trace_id=trace_id,
    )


def _terminal_rejection_result(
    *,
    status: str,
    message: str,
    final_response: str,
    trace_id: str,
) -> dict[str, Any]:
    """Return one bounded local terminal envelope without requesting revision."""

    return {
        "action": "terminal",
        "message": message,
        "terminalRejected": True,
        "terminalStatus": status,
        "responseHash": response_hash(final_response),
        "turnId": trace_id,
    }


def _terminal_turn_status(adapter: Any, session_id: str, trace_id: str) -> str:
    """Return a terminal run status while rejecting cross-session correlation."""

    if not session_id or not trace_id:
        return ""
    getter = getattr(adapter.store, "get_run", None)
    if not callable(getter):
        raise RuntimeError("terminal turn state could not be verified")
    run = getter(trace_id)
    if run is None:
        return ""
    if not isinstance(run, dict) or str(run.get("session_id") or "") != session_id:
        raise RuntimeError("terminal turn correlation is invalid")
    status = str(run.get("status") or "")
    return "" if status in {"", "active"} else status


def _publish_unverified(
    *,
    attempt: int,
    final_response: str,
    trace_id: str,
) -> dict[str, Any]:
    """Let the turn publish when Agency could not verify or persist its evidence.

    Rule 8: Agency never withholds a turn because Agency is unavailable. This
    used to emit a terminal rejection, which made OpenClaw the one host that
    still converted Agency's own failure into the user losing a finished
    response -- the exact drift the native `Stop` path stopped doing, kept alive
    here because the policy lived in two files (see the handoff's
    two-sources-of-truth thread).

    Every caller is an unavailability: `runtime_enabled` raised, the trace could
    not be resolved, correlation was absent, the terminal state or turn status
    could not be read, or the policy decision could not be evaluated. A verifier
    that actually evaluated and rejected does NOT come here -- those keep
    blocking through `_terminal_pre_verify_result`, `_TERMINAL_MISMATCH_MESSAGE`
    and `_finish_policy_rejection`, because a real finding is Agency working.

    The empty envelope is not a new contract for the external Node consumer:
    it is the same shape this function's own success path already returns when
    the terminal state is `completed`.
    """

    del attempt, final_response, trace_id
    return {}


def _evidence_revision(decision: dict[str, Any]) -> int | None:
    """Return a positive, non-boolean evidence revision or None."""
    revision = decision.get("evidence_revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
        return None
    return revision


def _commit_terminal_outcome(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    final_response: str,
    action: str,
    status: str,
    evidence_revision: int,
    missing: list[str] | None = None,
    response_binding: str = "",
) -> str:
    """Atomically bind one response to the evidence revision that validated it.

    Returns `committed` on success, `unavailable` when the store could not be
    reached at all, and `conflict` when the store answered but the binding did
    not hold.  The two failures are not interchangeable: an unreachable store
    is Agency being blind, while a revision or digest mismatch means the
    evidence that validated this response no longer stands.
    """
    try:
        from agency_runtime.core.header.finalize import response_hash

        digest = response_hash(response_binding or final_response)
        policy_digest = response_hash(final_response)
        committed = adapter.store.commit_terminal_finalization(
            session_id=session_id,
            trace_id=trace_id,
            host="openclaw",
            action=action,
            response_hash=digest,
            policy_response_hash=policy_digest,
            status=status,
            expected_evidence_revision=evidence_revision,
            missing=missing,
        )
    except Exception:
        return "unavailable"
    bound = bool(
        isinstance(committed, dict)
        and committed.get("authoritative") is True
        and committed.get("outcome") in {"committed", "replay"}
        and committed.get("action") == action
        and committed.get("response_hash") == digest
        and committed.get("policy_response_hash") == policy_digest
        and committed.get("status") == status
    )
    return "committed" if bound else "conflict"


def _evaluate_pre_verify_policy(
    adapter: Any,
    *,
    final_response: str,
    session_id: str,
    model: str,
    attempt: int,
    trace_id: str,
) -> dict[str, Any] | None:
    """Evaluate revision-bound policy, with an explicit test-double fallback."""
    evaluator = getattr(adapter, "evaluate_completion_policy", None)
    if callable(evaluator):
        value = evaluator(
            final_response,
            session_id=session_id,
            model=model,
            trace_id=trace_id,
        )
        if not isinstance(value, dict) or value.get("action") not in {
            "accept",
            "continue",
        }:
            return None
        if value.get("runtime_disabled") is True:
            return dict(value) if value.get("action") == "accept" else None
        if _evidence_revision(value) is None:
            return None
        return dict(value)
    else:
        verifier = getattr(adapter, "pre_verify_handler", None)
        if not callable(verifier):
            return None
        value = verifier(
            final_response=final_response,
            session_id=session_id,
            model=model,
            attempt=attempt,
            trace_id=trace_id,
        )

    if value is None:
        return {"action": "accept"}
    if not isinstance(value, dict) or value.get("action") not in {None, "continue"}:
        return None
    decision = dict(value)
    decision["action"] = "continue" if value.get("action") == "continue" else "accept"
    return decision


def _missing_fields(decision: dict[str, Any]) -> list[str]:
    """Return bounded string field names for durable diagnostics."""
    value = decision.get("missing")
    if not isinstance(value, list):
        return []
    return [item[:128] for item in value if isinstance(item, str) and item][:100]


def _safe_policy_decision(
    adapter: Any,
    *,
    final_response: str,
    session_id: str,
    model: str,
    attempt: int,
    trace_id: str,
) -> dict[str, Any] | None:
    try:
        return _evaluate_pre_verify_policy(
            adapter,
            final_response=final_response,
            session_id=session_id,
            model=model,
            attempt=attempt,
            trace_id=trace_id,
        )
    except Exception:
        return None


def _finish_policy_rejection(
    adapter: Any,
    *,
    decision: dict[str, Any],
    policy_response: str,
    response_binding: str,
    session_id: str,
    trace_id: str,
) -> dict[str, Any]:
    """Bind the first verified policy violation to one terminal outcome."""

    if decision.get("runtime_disabled") is True:
        return {}
    if decision.get("action") != "continue":
        return _revision()
    revision = _evidence_revision(decision)
    if revision is None:
        return _revision()
    rejection_action = (
        "delegation_declined"
        if decision.get("delegation_strength") == "strongly_preferred"
        else "response_invalid"
    )
    committed = _commit_terminal_outcome(
        adapter,
        session_id=session_id,
        trace_id=trace_id,
        final_response=policy_response,
        action=rejection_action,
        status=rejection_action,
        evidence_revision=revision,
        missing=_missing_fields(decision),
        response_binding=response_binding,
    )
    if committed != "committed":
        return _revision()
    return _terminal_pre_verify_result(rejection_action, response_binding, trace_id)


def _outbound_denial(
    digest: str,
    message: str = _TERMINAL_REJECTION_MESSAGE,
) -> dict[str, Any]:
    """Return one exact-digest fail-closed outbound decision."""

    return {
        "action": "replace",
        "message": message,
        "responseHash": digest,
        "runtimeEnabled": True,
    }


def _outbound_allowance(
    digest: str,
    *,
    trace_id: str = "",
    runtime_disabled: bool = False,
) -> dict[str, Any]:
    """Return a positive decision with the correlation Python actually used."""

    result: dict[str, Any] = {"action": "allow", "responseHash": digest}
    if trace_id:
        result["turnId"] = trace_id
    if runtime_disabled:
        result["runtimeDisabled"] = True
    else:
        result["runtimeEnabled"] = True
    return result


def _matches_exact_terminal(
    value: object,
    *,
    action: str,
    status: str,
    digest: str,
) -> bool:
    """Check every authoritative terminal field, including the exact digest."""

    if not isinstance(value, dict):
        return False
    return (
        value.get("authoritative"),
        value.get("action"),
        value.get("terminal_status"),
        value.get("status"),
        value.get("response_hash"),
    ) == (True, action, status, status, digest)


def _exact_outbound_terminal_state(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    digest: str,
) -> str:
    """Read an exact authoritative terminal or report an unavailable store."""

    getter = getattr(adapter.store, "get_authoritative_finalization", None)
    if not callable(getter):
        return ""
    try:
        legacy_rejected = getter(
            session_id,
            trace_id,
            action="retry_exhausted",
            response_hash=digest,
        )
        response_invalid = getter(
            session_id,
            trace_id,
            action="response_invalid",
            response_hash=digest,
        )
        delegation_declined = getter(
            session_id,
            trace_id,
            action="delegation_declined",
            response_hash=digest,
        )
        accepted = getter(
            session_id,
            trace_id,
            action="accept",
            response_hash=digest,
        )
    except Exception:
        return "unavailable"
    if _matches_exact_terminal(
        legacy_rejected,
        action="retry_exhausted",
        status="retry_exhausted",
        digest=digest,
    ):
        return "retry_exhausted"
    if _matches_exact_terminal(
        response_invalid,
        action="response_invalid",
        status="response_invalid",
        digest=digest,
    ):
        return "response_invalid"
    if _matches_exact_terminal(
        delegation_declined,
        action="delegation_declined",
        status="delegation_declined",
        digest=digest,
    ):
        return "delegation_declined"
    if _matches_exact_terminal(
        accepted,
        action="accept",
        status="completed",
        digest=digest,
    ):
        return "completed"
    return ""


def _conflicting_terminal_action(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    digest: str,
) -> str:
    """Name the terminal already bound to this trace when it is not this response.

    `_exact_outbound_terminal_state` filters on the presented digest, so it
    answers "" both when the trace has no terminal at all and when it has one
    that committed a *different* response. Those are opposites. The first is
    Agency being blind, which Rule 8 says must not withhold a turn. The second
    is a readable verdict that this envelope is not the one Agency bound, and
    allowing it would let any later payload overwrite a committed response by
    simply not matching it.

    Returns the committed terminal's action when it disagrees with `digest`,
    and "" whenever the store is unreadable, silent, or in agreement -- so a
    genuine fault still falls through to the fail-open path.
    """

    getter = getattr(adapter.store, "get_authoritative_finalization", None)
    if not callable(getter):
        return ""
    try:
        terminal = getter(session_id, trace_id)
    except Exception:
        return ""
    if not isinstance(terminal, dict):
        return ""
    committed = str(terminal.get("response_hash") or "")
    if not committed or committed == digest:
        return ""
    return str(terminal.get("action") or "")


def _outbound_binding_matches_policy_text(
    outbound_payload: str,
    final_response: str,
) -> bool:
    """Bind canonical payload evidence to the exact text policy evaluated."""

    if not outbound_payload:
        return True
    try:
        payload = safe_load_bounded_json(
            outbound_payload,
            maximum_bytes=MAX_INPUT_BYTES,
            maximum_depth=8,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    supplement = payload.get("ttsSupplement")
    supplement_text = supplement.get("spokenText") if isinstance(supplement, dict) else None
    surfaces = [
        candidate
        for candidate in (payload.get("text"), payload.get("spokenText"), supplement_text)
        if isinstance(candidate, str) and candidate.strip()
    ]
    return bool(surfaces) and all(candidate == final_response for candidate in surfaces)


def _handle_outbound_gate(
    adapter: Any,
    *,
    session_id: str,
    trace_id: str,
    final_response: str,
    outbound_payload: str = "",
    model: str = "",
) -> dict[str, Any]:
    """Deny an evaluated negative or a broken envelope; never deny for blindness.

    Rule 8 permits withholding a turn only when Agency evaluated the response
    and rejected it.  Agency's own faults -- unreadable evidence, a policy call
    that raised, unbindable revision, a failed commit -- allow the turn instead.
    Envelope integrity is separate: a payload that does not bind to the policy
    text, or a missing session or response, is still denied, because failing
    open there would make the contract bypassable by a malformed payload.
    """

    binding = outbound_payload or final_response
    digest = response_hash(binding)

    try:
        if not bool(adapter.runtime_enabled()):
            return _outbound_allowance(digest, runtime_disabled=True)
    except Exception:
        # Blind is not the same as off: the soft control could not be read, so
        # the turn proceeds while the runtime still reports itself enabled.
        return _outbound_allowance(digest)

    if not _outbound_binding_matches_policy_text(outbound_payload, final_response):
        return _outbound_denial(
            digest,
            "Agency Runtime could not bind the outbound payload to policy text.",
        )

    if not session_id or not final_response:
        return _outbound_denial(
            digest,
            "Agency Runtime could not correlate this outbound response.",
        )
    try:
        effective_trace = trace_id or _recover_exact_terminal_trace(
            adapter,
            session_id,
            final_response,
            response_digest=digest,
        )
    except Exception:
        effective_trace = ""
    if not effective_trace:
        # The envelope is well formed and Agency simply could not find its own
        # record for it.  That is Agency being blind, not a verdict.
        return _outbound_allowance(digest)

    terminal_state = _exact_outbound_terminal_state(
        adapter,
        session_id=session_id,
        trace_id=effective_trace,
        digest=digest,
    )
    if terminal_state in {"response_invalid", "retry_exhausted", "delegation_declined"}:
        return _outbound_denial(
            digest,
            TERMINAL_OUTCOME_MESSAGES[terminal_state],
        )
    if terminal_state == "completed":
        return _outbound_allowance(digest, trace_id=effective_trace)
    if terminal_state == "unavailable":
        # Agency could not read its own evidence.  Rule 8 permits withholding
        # only for an evaluated negative, so a blind gate allows the turn.
        return _outbound_allowance(digest, trace_id=effective_trace)

    conflicting_action = _conflicting_terminal_action(
        adapter,
        session_id=session_id,
        trace_id=effective_trace,
        digest=digest,
    )
    if conflicting_action:
        # This trace is already terminal against a different response, which is
        # evidence Agency read rather than a fault it suffered.  Denying here
        # keeps the exact-digest binding from being bypassed by any payload
        # that simply fails to match the committed one.
        return _outbound_denial(
            digest,
            TERMINAL_OUTCOME_MESSAGES.get(conflicting_action, _TERMINAL_REJECTION_MESSAGE),
        )

    decision = _safe_policy_decision(
        adapter,
        final_response=final_response,
        session_id=session_id,
        model=model,
        attempt=1,
        trace_id=effective_trace,
    )
    if decision is None:
        return _outbound_allowance(digest, trace_id=effective_trace)
    if decision.get("runtime_disabled") is True:
        return _outbound_allowance(digest, runtime_disabled=True)
    return _outbound_evaluated_decision(
        adapter,
        decision=decision,
        digest=digest,
        session_id=session_id,
        effective_trace=effective_trace,
        final_response=final_response,
        binding=binding,
        revision=_evidence_revision(decision),
    )


def _outbound_evaluated_decision(
    adapter: Any,
    *,
    decision: dict[str, Any],
    digest: str,
    session_id: str,
    effective_trace: str,
    final_response: str,
    binding: str,
    revision: int | None,
) -> dict[str, Any]:
    """Bind one evaluated decision, separating a blind commit from a refused one."""

    accepted = decision.get("action") == "accept"
    if revision is None:
        # Agency evaluated the response but cannot bind its own evidence.  An
        # acceptance proceeds, because the verdict was positive and only the
        # receipt is missing.  An evaluated negative still withholds: the
        # verdict stands even when Agency cannot write down why.
        if accepted:
            return _outbound_allowance(digest, trace_id=effective_trace)
        return _outbound_denial(digest)
    rejection_action = (
        "delegation_declined"
        if decision.get("delegation_strength") == "strongly_preferred"
        else "response_invalid"
    )
    committed = _commit_terminal_outcome(
        adapter,
        session_id=session_id,
        trace_id=effective_trace,
        final_response=final_response,
        action="accept" if accepted else rejection_action,
        status="completed" if accepted else rejection_action,
        evidence_revision=revision,
        missing=_missing_fields(decision),
        response_binding=binding,
    )
    if committed == "unavailable":
        # A persistence failure deliberately leaves the correlated turn open
        # rather than withholding a completed turn to report an Agency fault.
        return _outbound_allowance(digest, trace_id=effective_trace)
    if committed != "committed":
        # The store answered and refused the binding, so the evidence that
        # validated this response no longer stands.  That is a verdict about
        # the turn, and stale evidence must not terminalize it.
        return _outbound_denial(
            digest,
            "Agency Runtime could not commit outbound evidence.",
        )
    if accepted:
        return _outbound_allowance(digest, trace_id=effective_trace)
    return _outbound_denial(digest)


def _handle_pre_verify(
    adapter: Any,
    payload: dict[str, Any],
    *,
    session_id: str,
    trace_id: str,
    model: str,
) -> dict[str, Any]:
    """Revalidate one OpenClaw response without allowing exceptions to accept it."""
    final_response = _bounded_string(
        payload,
        "finalResponse",
        limit=MAX_INPUT_BYTES,
    )
    policy_response = _normalized_pre_finalize_text(final_response)
    attempt = _attempt_number(payload)
    try:
        if not bool(adapter.runtime_enabled()):
            return {"runtimeDisabled": True}
    except Exception:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=trace_id,
        )
    try:
        effective_trace = _effective_pre_verify_trace(
            adapter,
            session_id=session_id,
            trace_id=trace_id,
            final_response=policy_response,
        )
    except Exception:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=trace_id,
        )
    if not session_id or not effective_trace:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=effective_trace or trace_id,
        )

    try:
        terminal_state = _exact_policy_terminal_state(
            adapter,
            session_id=session_id,
            trace_id=effective_trace,
            final_response=policy_response,
        )
    except Exception:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=effective_trace,
        )
    if terminal_state == "completed":
        return {}
    if terminal_state in {"response_invalid", "retry_exhausted", "delegation_declined"}:
        return _terminal_pre_verify_result(
            terminal_state,
            final_response,
            effective_trace,
        )

    try:
        closed_status = _terminal_turn_status(adapter, session_id, effective_trace)
    except Exception:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=effective_trace,
        )
    if closed_status:
        return _terminal_rejection_result(
            status=closed_status,
            message=_TERMINAL_MISMATCH_MESSAGE,
            final_response=policy_response,
            trace_id=effective_trace,
        )

    decision = _safe_policy_decision(
        adapter,
        final_response=policy_response,
        session_id=session_id,
        model=model,
        attempt=attempt,
        trace_id=effective_trace,
    )
    if decision is None:
        return _publish_unverified(
            attempt=attempt,
            final_response=policy_response,
            trace_id=effective_trace,
        )
    if decision.get("runtime_disabled") is True:
        return {"runtimeDisabled": True}
    if decision.get("action") == "accept":
        revision = _evidence_revision(decision)
        return (
            {"action": "allow_pending", "evidenceRevision": revision}
            if revision is not None
            else _revision()
        )
    return _finish_policy_rejection(
        adapter,
        decision=decision,
        policy_response=policy_response,
        response_binding=final_response,
        session_id=session_id,
        trace_id=effective_trace,
    )


def _handle_finalize_tool(
    adapter: Any,
    payload: dict[str, Any],
    *,
    session_id: str,
    trace_id: str,
) -> dict[str, Any]:
    """Dispatch the OpenClaw-native tool through the canonical Agency finalizer."""

    draft_text = _bounded_string(payload, "draftText", limit=MAX_INPUT_BYTES)
    if not session_id or not trace_id or not draft_text:
        return {"error": "finalization requires draftText, sessionId, and traceId"}
    if not adapter.runtime_enabled():
        return {
            "action": "bypass",
            "text": draft_text,
            "runtimeEnabled": False,
            "runtimeDisabled": True,
            "bypassed": True,
        }
    from agency_runtime.core.header.finalize import finalize_response

    result = finalize_response(
        draft_text,
        trace_metadata={
            "trace_id": trace_id,
            "session_id": session_id,
            "host": "openclaw",
        },
        store=adapter.store,
        model="",
        commit_terminal=False,
    )
    if not isinstance(result, dict):
        return {"error": "finalization returned an invalid result"}
    return {**dict(result), "runtimeEnabled": True}


def _runtime_disabled_result(payload: dict[str, Any], action: str) -> dict[str, Any]:
    """Return the exact no-side-effect contract for one disabled host action."""

    disabled = {"runtimeEnabled": False, "runtimeDisabled": True, "bypassed": True}
    if action == "finalize":
        return {
            "action": "bypass",
            "text": _bounded_string(payload, "draftText", limit=MAX_INPUT_BYTES),
            "runtimeEnabled": False,
            "runtimeDisabled": True,
            "bypassed": True,
        }
    if action == "outbound_gate":
        binding = _bounded_string(payload, "outboundPayload", limit=MAX_INPUT_BYTES)
        if not binding:
            binding = _bounded_string(payload, "finalResponse", limit=MAX_INPUT_BYTES)
        return {
            **_outbound_allowance(response_hash(binding), runtime_disabled=True),
            "bypassed": True,
        }
    if action in {"preflight", "pre_verify"}:
        return disabled
    if action in {
        "post_tool_call",
        "post_api_request",
        "native_child_started",
        "native_child_ended",
        "on_session_end",
    }:
        return {}
    return {"error": f"unknown action: {action}"}


def _handle_observation_action(
    adapter: OpenClawAdapter,
    payload: dict[str, Any],
    *,
    action: str,
    session_id: str,
    trace_id: str,
) -> dict[str, Any] | None:
    """Persist one fail-open host observation, or decline the action."""

    if action == "post_tool_call":
        tool_input = payload.get("toolInput")
        effective_trace = _resolve_turn_trace(adapter, session_id, trace_id)
        adapter.post_tool_call_handler(
            tool_name=_bounded_string(
                payload,
                "toolName",
                limit=MAX_TOOL_NAME_CHARS,
            ),
            args=tool_input if isinstance(tool_input, dict) else {},
            result=payload.get("toolResult"),
            error=payload.get("error"),
            session_id=session_id,
            trace_id=effective_trace,
        )
        return {}

    if action == "post_api_request":
        requested_model = _bounded_string(payload, "requestedModel", limit=MAX_MODEL_CHARS)
        model_group = _bounded_string(payload, "modelGroup", limit=MAX_MODEL_CHARS)
        resolved_provider = _bounded_string(
            payload,
            "resolvedProvider",
            limit=MAX_MODEL_CHARS,
        )
        resolved_model = _bounded_string(payload, "resolvedModel", limit=MAX_MODEL_CHARS)
        adapter.post_api_request_handler(
            requested_model=requested_model,
            model=requested_model,
            model_group=model_group or requested_model,
            response_model=resolved_model,
            resolved_model=resolved_model,
            resolved_provider=resolved_provider,
            model_id=_bounded_string(payload, "modelId", limit=MAX_MODEL_CHARS),
            source=_bounded_string(payload, "source", limit=128) or "openclaw-model-call",
            status=_bounded_string(payload, "status", limit=64) or "success",
            session_id=session_id,
            trace_id=trace_id,
        )
        return {}

    if action == "native_child_started":
        if not session_id or not trace_id:
            return {}
        worker_id = _bounded_string(payload, "workerId", limit=256)
        native_run_id = _bounded_string(payload, "nativeRunId", limit=256)
        work_unit_id = _bounded_string(payload, "workUnitId", limit=160)
        goal = _bounded_string(payload, "goal", limit=MAX_INPUT_BYTES)
        if not worker_id or not native_run_id:
            return {}
        if work_unit_id or goal:
            adapter.post_tool_call_handler(
                tool_name="sessions_spawn",
                args={"prompt": goal, "work_unit_id": work_unit_id},
                result={
                    "childSessionKey": worker_id,
                    "native_run_id": native_run_id,
                },
                session_id=session_id,
                trace_id=trace_id,
            )
            return {}
        adapter.store.record_native_child_started(
            host="openclaw",
            backend="sessions_spawn",
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=work_unit_id,
            worker_id=worker_id,
            native_run_id=native_run_id,
        )
        return {}

    if action == "native_child_ended":
        if not session_id or not trace_id:
            return {}
        adapter.store.record_native_child_ended(
            host="openclaw",
            backend="sessions_spawn",
            session_id=session_id,
            trace_id=trace_id,
            work_unit_id=_bounded_string(payload, "workUnitId", limit=160),
            worker_id=payload.get("workerId"),
            native_run_id=payload.get("nativeRunId"),
            outcome=_bounded_string(payload, "outcome", limit=32) or "unknown",
            error=payload.get("error"),
        )
        return {}

    return None


def handle(
    payload: dict[str, Any],
    *,
    adapter: OpenClawAdapter | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"error": "payload must be an object"}
    action = _bounded_string(payload, "action", limit=32).strip()
    from agency_runtime.core.runtime_control import master_enabled

    if action != "control" and not master_enabled():
        return _runtime_disabled_result(payload, action)
    session_id = validate_correlation_id(
        payload.get("sessionId"),
        field="session_id",
        required=False,
    )
    trace_id = validate_correlation_id(
        payload.get("traceId"),
        field="trace_id",
        required=False,
    )
    model = _bounded_string(payload, "model", limit=MAX_MODEL_CHARS)
    if adapter is None:
        try:
            adapter = OpenClawAdapter()
        except Exception:
            if action == "pre_verify":
                return _revision()
            raise

    if action == "control":
        from agency_runtime.core.host_control import handle_host_control_command

        return handle_host_control_command(
            "openclaw",
            _bounded_string(payload, "command", limit=64) or "status",
            store=adapter.store,
            source="openclaw-command",
        )

    if action == "preflight":
        if not adapter.runtime_enabled():
            return {"runtimeEnabled": False}
        user_message = _bounded_string(
            payload,
            "userMessage",
            limit=MAX_INPUT_BYTES,
        )
        if not user_message.strip():
            return {}
        trace_id = trace_id or str(uuid4())
        origin_receipt = _preflight_origin(
            adapter,
            session_id=session_id,
            trace_id=trace_id,
            message=user_message,
        )
        if origin_receipt.origin == "internal_retry":
            return {}
        result = (
            adapter.pre_llm_call_handler(
                session_id=session_id,
                user_message=user_message,
                model=model,
                trace_id=trace_id,
                origin_receipt=origin_receipt,
                parent_session_id=_bounded_string(payload, "parentSessionId", limit=512),
                parent_trace_id=_bounded_string(payload, "parentTraceId", limit=512),
                native_worker_id=_bounded_string(payload, "workerId", limit=256),
                native_run_id=_bounded_string(payload, "nativeRunId", limit=256),
            )
            or {}
        )
        result = _append_header_snapshot(
            dict(result),
            adapter,
            session_id=session_id,
            trace_id=trace_id,
            model=model,
        )
        return {**result, "runtimeEnabled": True}

    if action == "finalize":
        return _handle_finalize_tool(
            adapter,
            payload,
            session_id=session_id,
            trace_id=trace_id,
        )

    if action == "pre_verify":
        return _handle_pre_verify(
            adapter,
            payload,
            session_id=session_id,
            trace_id=trace_id,
            model=model,
        )

    if action == "outbound_gate":
        return _handle_outbound_gate(
            adapter,
            session_id=session_id,
            trace_id=trace_id,
            final_response=_bounded_string(
                payload,
                "finalResponse",
                limit=MAX_INPUT_BYTES,
            ),
            outbound_payload=_bounded_string(
                payload,
                "outboundPayload",
                limit=MAX_INPUT_BYTES,
            ),
            model=model,
        )

    observation = _handle_observation_action(
        adapter,
        payload,
        action=action,
        session_id=session_id,
        trace_id=trace_id,
    )
    if observation is not None:
        return observation

    return {"error": f"unknown action: {action}"}


def _config_path(arguments: Sequence[str]) -> Path | None:
    if not arguments:
        return None
    if len(arguments) != 2 or arguments[0] != "--config":
        raise ValueError("OpenClaw bridge accepts only --config <absolute-path>")
    value = Path(arguments[1]).expanduser()
    if not value.is_absolute():
        raise ValueError("OpenClaw bridge config path must be absolute")

    from agency_runtime.core.configuration_persistence import resolve_config_path

    return resolve_config_path(value, use_environment=False)


def _configured_adapter(config_path: Path | None) -> OpenClawAdapter | None:
    if config_path is None:
        return None
    from agency_runtime.core.store.sqlite import Store

    return OpenClawAdapter(Store(config_path=config_path))


def main(argv: Sequence[str] | None = None) -> int:
    payload = _read_payload()
    action = _bounded_string(payload, "action", limit=32).strip()
    from agency_runtime.core.runtime_control import master_enabled

    if payload.get("error"):
        result = {"error": payload["error"]}
    elif action != "control" and not master_enabled():
        # The installed bridge carries --config. Global off must remain a true
        # no-work bypass even when that config is missing, malformed, or points
        # at an unavailable Store.
        result = _runtime_disabled_result(payload, action)
    else:
        try:
            configured_adapter = _configured_adapter(_config_path(argv or ()))
        except Exception as exc:
            print(
                f"agency openclaw bridge: {type(exc).__name__}; configured runtime unavailable",
                file=sys.stderr,
            )
            result = {"error": "configured runtime unavailable"}
        else:
            try:
                if configured_adapter is None:
                    result = handle(payload)
                else:
                    result = handle(payload, adapter=configured_adapter)
            except Exception as exc:  # Defensive host boundary.
                print(
                    (
                        f"agency openclaw bridge: {type(exc).__name__}; "
                        + (
                            "response publication blocked"
                            if action == "pre_verify"
                            else "host operation continues"
                        )
                    ),
                    file=sys.stderr,
                )
                result = _revision() if action == "pre_verify" else {}
    try:
        encoded = json.dumps(result, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError):
        result = _revision() if action == "pre_verify" else {}
        encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
    if len(encoded.encode("ascii")) > MAX_BRIDGE_OUTPUT_BYTES:
        result = _revision() if action == "pre_verify" else {}
        encoded = json.dumps(result, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write(encoded)
    sys.stdout.write("\n")
    return 2 if result.get("error") else 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main(sys.argv[1:]))
