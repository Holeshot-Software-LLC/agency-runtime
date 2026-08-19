"""Inference-owned, all-or-nothing staffing for host-initiated native children.

This service may exclude hard-ineligible specialists and reject an unsafe model
decision.  It never chooses, repairs, truncates, activates, or hires a worker.
When any boundary cannot be proven, it returns the original host task unchanged
with a content-free diagnostic and lets the native child proceed unstaffed.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
from collections.abc import Callable, Container, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.canary_judge_provider import (
    CanaryChildJudgeProviderError,
    canary_child_judge_config,
)
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.content_redaction import redact_content
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.host_capabilities import (
    EXECUTION_HOSTS,
    native_adapter_capability_receipt,
)
from agency_runtime.core.native_child_decision import (
    MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS,
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
    project_native_child_staffing_decision,
)
from agency_runtime.core.native_child_install_identity import NativeChildInstallIdentity
from agency_runtime.core.native_child_prompt_delivery import (
    MAX_INFERENCE_TEAM_CARDS,
    InferenceTeamCard,
    inference_team_digest,
    parse_inference_team_delivery,
    render_inference_team_context_segment,
    render_inference_team_delivery,
)
from agency_runtime.core.roster.revisions import content_digest_identity, content_identity_matches
from agency_runtime.core.routing_snapshot import capture_routing_snapshot
from agency_runtime.core.selector.compatibility import (
    compile_compatibility_catalog,
    enforce_compatible_set,
    filter_eligible_catalog,
)
from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.selector.receipt_projection import project_model_receipt_attempts
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.version_identity import normalize_version_identity

MAX_NATIVE_CHILD_STAFFING_DELIVERY_BYTES: Final[int] = 48_000
NATIVE_CHILD_STAFFING_TTL_SECONDS: Final[int] = 60

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ROUTE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_REASON_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_BINDING_KIND = re.compile(r"[a-z][a-z0-9_]{1,31}\Z")
_SUPPORTED_BINDING_KINDS = frozenset({"child_id", "launch_id"})
_SUCCESS_SOURCE = "native_child_inference"
_FAILURE_SOURCE = "native_child_inference_failure"
# A solicited decline is not a failure, and the sibling `status` field was
# corrected to `inference_abstained` without this one following. Both must be
# allowlisted in store.queries.project_routing_decision; an unlisted source
# falls through to "computed", which reads as a deterministic decision.
_ABSTAINED_SOURCE = "native_child_inference_abstained"
_UNAVAILABLE_REASONS = frozenset(
    {
        "native_child_catalog_unavailable",
        "native_child_eligible_catalog_empty",
        "native_child_inference_unavailable",
        "unsupported_opaque_interagent_channel",
    }
)
_INVALID_PERSISTENCE_REASONS = frozenset(
    {
        "native_child_routing_decision_unavailable",
        "native_child_routing_projection_invalid",
    }
)
# The judge prompt asks for zero to MAX_INFERENCE_TEAM_CARDS specialists and
# tells the model to return an empty list when none fits, so an empty selection
# is a decision this runtime solicited, not a malformed one. Record it under its
# own reason and status; the child still proceeds unstaffed either way.
#
# AR-255 P2 splits the abstention outcome into two reasons so a series can tell
# whether the funded repair call did anything. The legacy reason now means the
# first-pass abstention stood because the repair could not produce a valid
# answer; the confirmed reason means the judge tested its own abstention on the
# repair call and reaffirmed it. They must never collapse into one code.
NATIVE_CHILD_ABSTAINED_REASON = "native_child_no_specialist_needed"
NATIVE_CHILD_ABSTENTION_CONFIRMED_REASON = "native_child_abstention_confirmed"
_ABSTAINED_REASONS = frozenset(
    {NATIVE_CHILD_ABSTAINED_REASON, NATIVE_CHILD_ABSTENTION_CONFIRMED_REASON}
)

# The judge's own universe, recorded so a decline can be read from the receipt
# instead of reconstructed offline. `candidate_count: 65` cannot answer the only
# question a decline raises -- whether anyone who could do the work was in front
# of it -- which is the gap `ranked_agent_ids` closed for the parent recruiter
# after it had already cost two days of reconstruction there.
MAX_RECORDED_OFFERED_AGENT_CHARS: Final[int] = 16_384


@dataclass(frozen=True, slots=True)
class NativeChildStaffingResult:
    """One staffed envelope or an explicit fail-open unstaffed diagnostic."""

    staffed: bool
    reason_code: str
    rewritten_task: str
    context_segment: str = ""
    decision_id: str = ""
    diagnostic_decision_id: str = ""
    task_sha256: str = ""
    provider_receipt_digest: str = ""
    team_digest: str = ""
    selected_ids: tuple[str, ...] = ()
    provider_attempts: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False)
    native_child_delivery: Mapping[str, Any] = field(default_factory=dict, repr=False)
    routing_decision: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @property
    def status(self) -> str:
        """Return the stable two-state integration status."""

        return "staffed" if self.staffed else "unstaffed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _nonce() -> str:
    return secrets.token_urlsafe(24)


def _decision_id() -> str:
    return f"native-child-{secrets.token_hex(16)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json_digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("staffing clock must return a timezone-aware datetime")
    utc = value.astimezone(timezone.utc)
    timespec = "microseconds" if utc.microsecond else "seconds"
    return utc.isoformat(timespec=timespec).replace("+00:00", "Z")


def _default_platform() -> str:
    return "windows" if sys.platform == "win32" else "linux"


def _valid_install_identity(
    value: object,
    *,
    host: str,
) -> NativeChildInstallIdentity | None:
    if not isinstance(value, NativeChildInstallIdentity) or value.host != host:
        return None
    try:
        install_id = validate_correlation_id(value.install_id, field="install_id")
        plugin_version_bytes = value.plugin_version.encode("utf-8")
    except (AttributeError, TypeError, UnicodeError, ValueError):
        return None
    digests = (
        value.bundle_digest,
        value.running_runtime_digest,
        value.candidate_digest,
    )
    if (
        not isinstance(value.plugin_version, str)
        or not value.plugin_version
        or len(plugin_version_bytes) > 128
        or install_id != value.install_id
        or any(not isinstance(item, str) or _DIGEST.fullmatch(item) is None for item in digests)
        or value.candidate_digest != value.running_runtime_digest
    ):
        return None
    return value


def _context_fingerprint(
    *,
    host: str,
    platform: str,
    available_tools: Container[str] | None,
    capability_status: str,
    disabled_agents: frozenset[str],
    roster_generation: int,
    catalog: list[dict[str, Any]],
    install: NativeChildInstallIdentity,
) -> str:
    tools = None if available_tools is None else sorted(str(item) for item in available_tools)
    return _canonical_json_digest(
        {
            "host": host,
            "platform": platform,
            "available_tools": tools,
            "capability_status": capability_status,
            "disabled_agents": sorted(disabled_agents),
            "roster_generation": roster_generation,
            "catalog": catalog,
            "install_id": install.install_id,
            "bundle_digest": install.bundle_digest,
            "candidate_digest": install.candidate_digest,
            "runtime_digest": install.running_runtime_digest,
        }
    )


def _routing_state_matches(
    store: Any,
    *,
    config_authority: AgencyConfig | None,
    expected_config: AgencyConfig,
    host: str,
    platform: str,
    available_tools: Container[str] | None,
    capability_status: str,
    context_fingerprint: str,
    install: NativeChildInstallIdentity,
    install_identity_reader: Callable[[str], object],
) -> bool:
    """Re-read live routing authority and compare it to the frozen decision input."""

    try:
        current_snapshot = capture_routing_snapshot(store, config_authority)
        current_eligibility = filter_eligible_catalog(
            current_snapshot.catalog,
            host=host,
            platform=platform,
            available_tools=available_tools,
            capability_status=capability_status,
        )
        current_install = _valid_install_identity(
            install_identity_reader(host),
            host=host,
        )
        return bool(
            current_snapshot.config == expected_config
            and current_install == install
            and _context_fingerprint(
                host=host,
                platform=platform,
                available_tools=available_tools,
                capability_status=capability_status,
                disabled_agents=frozenset(current_snapshot.config.agents.disabled),
                roster_generation=current_snapshot.roster_generation,
                catalog=list(current_eligibility.eligible),
                install=install,
            )
            == context_fingerprint
        )
    except Exception:
        return False


def _native_child_config_read_lock(store: Any) -> Any:
    """Return the exact canonical Store config lock, or a deterministic test seam."""

    config_path = getattr(store, "_configured_config_path", None)
    if config_path is None:
        return nullcontext()
    from agency_runtime.core.configuration import config_read_lock

    return config_read_lock(config_path)


def _provider_name(value: Mapping[str, Any] | None) -> str:
    if value is None:
        return ""
    try:
        name = str(value.get("provider_name") or value.get("provider") or "").strip()
    except Exception:
        return ""
    return name if len(name) <= 128 else ""


def _requested_provider_name(value: Mapping[str, Any] | None) -> str:
    if value is None:
        return ""
    try:
        name = str(value.get("requested_provider") or "").strip()
    except Exception:
        return ""
    return name if len(name) <= 128 else ""


def _route_provider_name(
    value: Mapping[str, Any] | None,
    delivery: Mapping[str, Any] | None,
) -> str:
    """Use the same content-free provider identity sealed into the delivery."""

    fallback = _provider_name(value)
    if delivery is None:
        return fallback
    attempts = delivery.get("provider_attempts")
    if not isinstance(attempts, (list, tuple)):
        return fallback
    applied = [
        str(attempt.get("provider_name") or "")
        for attempt in attempts
        if isinstance(attempt, Mapping) and attempt.get("status") == "applied"
    ]
    return applied[0] if len(applied) == 1 and len(applied[0]) <= 128 else fallback


def _failure_status(reason_code: str) -> str:
    if reason_code in _INVALID_PERSISTENCE_REASONS:
        return "inference_invalid"
    if reason_code in _ABSTAINED_REASONS:
        return "inference_abstained"
    if (
        reason_code in _UNAVAILABLE_REASONS
        or ("provider" in reason_code and reason_code.endswith("_unavailable"))
        or reason_code.endswith("_no_provider")
        or reason_code.endswith("_unsupported")
    ):
        return "inference_unavailable"
    return "inference_invalid"


def _failure_source(status: str) -> str:
    return _ABSTAINED_SOURCE if status == "inference_abstained" else _FAILURE_SOURCE


def _task_shape(task: object) -> dict[str, Any]:
    """Project the child assignment's size, never its content.

    `offered_agent_ids` answered "was anyone capable in front of the judge" --
    yes, `code-reviewer` was, and it declined anyway. The question that replaced
    it is what the child was *asked*, and the receipt is content-free by policy,
    so the strongest honest answer available without inference or a content
    capture is how much assignment there was.

    This is deliberately a weak signal. It separates a one-line errand, for which
    `native_child_no_specialist_needed` is the correct answer, from a substantial
    brief, for which it is not. It cannot distinguish a code review from a
    summary of the same length, and nothing content-free can.
    """

    if not isinstance(task, str) or not task:
        return {}
    return {"task_chars": len(task), "task_lines": task.count("\n") + 1}


def _offered_projection(offered_ids: Sequence[str] | None) -> dict[str, Any]:
    """Project the eligible universe the judge was shown, flat and bounded."""

    if offered_ids is None:
        return {}
    ordered = sorted({item for item in offered_ids if type(item) is str and item})
    joined = "~".join(ordered)
    projection: dict[str, Any] = {
        # Over the complete set, always. A set too large to record must still be
        # comparable across runs, and must never read as a smaller universe.
        "offered_agent_digest": sha256(joined.encode("utf-8")).hexdigest(),
    }
    if ordered and len(joined) <= MAX_RECORDED_OFFERED_AGENT_CHARS:
        projection["offered_agent_ids"] = joined
    return projection


def repair_abstention_task(task: str) -> str:
    """Frame AR-255 P2's one funded repair without directing the outcome.

    The repair asks the judge to test its own abstention against the same
    concrete candidate set. It must never instruct the model to pick something:
    a repair that says "choose one" converts honest abstentions into forced
    selections and puts deterministic code back in charge of staffing. An empty
    selection therefore remains an explicitly valid answer.
    """

    return (
        "A previous evaluation of the assignment below against this exact "
        "candidate set selected no one. Test that abstention rather than "
        "repeating it: re-read each candidate's declared capabilities and "
        "answer from that reading alone. If no candidate's declared "
        "capabilities cover any part of the assignment, an empty selection is "
        "the correct answer again. If one or more candidates' declared "
        "capabilities do cover parts of the assignment, select exactly those "
        "candidates.\n\nASSIGNMENT:\n" + task
    )


def _inference_signal(
    result: Mapping[str, Any],
    field: str,
    *,
    default: bool,
) -> bool:
    value = result.get(field)
    return value if type(value) is bool else default


def _routing_projection(
    *,
    result: Mapping[str, Any] | None,
    task_sha256: str,
    context_fingerprint: str,
    selected_ids: list[str],
    status: str,
    source: str,
    reason_code: str = "",
    native_child_delivery: Mapping[str, Any] | None = None,
    offered_ids: Sequence[str] | None = None,
    task: object = None,
) -> dict[str, Any]:
    raw = result or {}
    inferred_success = status == "applied"
    default_inference_signal = inferred_success or status in {
        "inference_invalid",
        "inference_abstained",
    }
    decision: dict[str, Any] = {
        "status": status,
        "semantic_status": status,
        "source": source,
        "native_child_reason": "applied" if inferred_success else reason_code,
        "inference_configured": _inference_signal(
            raw,
            "inference_configured",
            default=default_inference_signal,
        ),
        "inference_required": True,
        "inference_attempted": _inference_signal(
            raw,
            "inference_attempted",
            default=default_inference_signal,
        ),
        "inference_mode": "inferred" if inferred_success else status.removeprefix("inference_"),
        "selected_ids": list(selected_ids),
        "semantic_ids": list(selected_ids),
        "companion_ids": [],
        "available_companion_ids": [],
        "unavailable_companion_ids": [],
        "confidence": raw.get("confidence", 0.0),
        "latency_ms": raw.get("latency_ms", 0),
        "provider": _route_provider_name(raw, native_child_delivery),
        "candidate_count": raw.get("candidate_count", 0),
        "top_score": raw.get("top_score", 0.0),
        "source_message_hash": task_sha256,
        "query_hash": task_sha256,
        "context_fingerprint": context_fingerprint,
        **_offered_projection(offered_ids),
        **_task_shape(task),
    }
    requested_provider = _requested_provider_name(raw)
    if requested_provider:
        decision["requested_provider"] = requested_provider
    if native_child_delivery is not None:
        decision["native_child_delivery"] = dict(native_child_delivery)
    return decision


def _parent_scope_is_current(
    store: Any,
    *,
    host: str,
    parent_session_id: str,
    parent_trace_id: str,
) -> bool:
    getter = getattr(store, "get_run", None)
    if not callable(getter):
        return False
    try:
        run = getter(parent_trace_id)
    except Exception:
        return False
    return bool(
        isinstance(run, Mapping)
        and run.get("trace_id") == parent_trace_id
        and run.get("session_id") == parent_session_id
        and str(run.get("host") or "").strip().casefold() == host
        and run.get("status") in {"active", "evidence_only"}
    )


def _failure_context_fingerprint(
    *,
    host: str,
    parent_session_id: str,
    parent_trace_id: str,
    launch_id: str,
    task_sha256: str,
) -> str:
    return _canonical_json_digest(
        {
            "schema": "agency.native-child-staffing-failure-context.v1",
            "host": host,
            "parent_session_id": parent_session_id,
            "parent_trace_id": parent_trace_id,
            "launch_id": launch_id,
            "task_sha256": task_sha256,
        }
    )


def _record_decision(
    store: Any,
    *,
    host: str,
    parent_session_id: str,
    parent_trace_id: str,
    task_sha256: str,
    context_fingerprint: str,
    decision: Mapping[str, Any],
    decision_id: str = "",
    expected_roster_generation: int | None = None,
    expected_disabled_agents: tuple[str, ...] | None = None,
    final_delivery_validator: Callable[[], bool] | None = None,
) -> str:
    recorder = getattr(store, "record_routing_decision", None)
    if not callable(recorder) or not _parent_scope_is_current(
        store,
        host=host,
        parent_session_id=parent_session_id,
        parent_trace_id=parent_trace_id,
    ):
        return ""
    try:
        arguments = {
            "trace_id": parent_trace_id,
            "session_id": parent_session_id,
            "query_hash": task_sha256,
            "context_fingerprint": context_fingerprint,
            "decision": dict(decision),
        }
        if decision_id:
            arguments["decision_id"] = decision_id
        arguments["require_open_run"] = True
        if expected_roster_generation is not None:
            arguments["expected_roster_generation"] = expected_roster_generation
        if expected_disabled_agents is not None:
            arguments["expected_disabled_agents"] = expected_disabled_agents
        if final_delivery_validator is not None:
            arguments["final_delivery_validator"] = final_delivery_validator
        recorded_id = recorder(
            **arguments,
        )
    except Exception:
        return ""
    normalized = str(recorded_id or "").strip()
    if _ROUTE_ID.fullmatch(normalized) is None or (decision_id and normalized != decision_id):
        return ""
    return normalized


def record_native_child_staffing_failure(
    store: Any,
    *,
    host: object,
    task: object,
    parent_session_id: object,
    parent_trace_id: object,
    launch_id: object,
    reason_code: object,
    inference_configured: bool | None = None,
    inference_attempted: bool | None = None,
) -> str:
    """Persist one content-free native-child failure, or return an empty ID.

    This is the shared HookBridge/Codex overflow path.  It never creates a run:
    the exact parent trace must already be live for the same host and session.
    Optional inference flags let a caller preserve whether inference was actually
    configured and attempted; when omitted they are derived conservatively from
    the canonical failure class.
    """

    try:
        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in EXECUTION_HOSTS:
            raise ValueError("unsupported host")
        if not isinstance(task, str) or not task:
            raise ValueError("task is required")
        task.encode("utf-8")
        session_id = validate_correlation_id(parent_session_id, field="parent_session_id")
        trace_id = validate_correlation_id(parent_trace_id, field="parent_trace_id")
        normalized_launch_id = validate_correlation_id(launch_id, field="launch_id")
        if not isinstance(reason_code, str) or _REASON_CODE.fullmatch(reason_code) is None:
            raise ValueError("reason_code is invalid")
        if inference_configured is not None and type(inference_configured) is not bool:
            raise TypeError("inference_configured must be boolean")
        if inference_attempted is not None and type(inference_attempted) is not bool:
            raise TypeError("inference_attempted must be boolean")
    except Exception:
        return ""
    if not _parent_scope_is_current(
        store,
        host=normalized_host,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
    ):
        return ""

    task_hash = _digest(task)
    status = _failure_status(reason_code)
    default_signal = status == "inference_invalid"
    signals = {
        "inference_configured": (
            default_signal if inference_configured is None else inference_configured
        ),
        "inference_attempted": (
            default_signal if inference_attempted is None else inference_attempted
        ),
    }
    context_fingerprint = _failure_context_fingerprint(
        host=normalized_host,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        launch_id=normalized_launch_id,
        task_sha256=task_hash,
    )
    decision = _routing_projection(
        result=signals,
        task_sha256=task_hash,
        context_fingerprint=context_fingerprint,
        selected_ids=[],
        status=status,
        source=_failure_source(status),
        reason_code=reason_code,
        task=task,
    )
    return _record_decision(
        store,
        host=normalized_host,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        task_sha256=task_hash,
        context_fingerprint=context_fingerprint,
        decision=decision,
    )


def _unstaffed(
    *,
    store: Any,
    reason_code: str,
    task: str,
    host: str = "",
    parent_session_id: str = "",
    parent_trace_id: str = "",
    task_sha256: str = "",
    context_fingerprint: str = "",
    judge_result: Mapping[str, Any] | None = None,
    provider_attempts: list[dict[str, Any]] | None = None,
    offered_ids: Sequence[str] | None = None,
    captured_task: str = "",
) -> NativeChildStaffingResult:
    decision: dict[str, Any] = {}
    diagnostic_id = ""
    if all((parent_session_id, parent_trace_id, task_sha256, context_fingerprint)):
        status = _failure_status(reason_code)
        decision = _routing_projection(
            result=judge_result,
            task_sha256=task_sha256,
            context_fingerprint=context_fingerprint,
            selected_ids=[],
            status=status,
            source=_failure_source(status),
            reason_code=reason_code,
            offered_ids=offered_ids,
            task=task,
        )
        diagnostic_id = _record_decision(
            store,
            host=host,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            task_sha256=task_sha256,
            context_fingerprint=context_fingerprint,
            decision=decision,
        )
        _record_captured_assignment(
            store,
            diagnostic_id=diagnostic_id,
            host=host,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            task_sha256=task_sha256,
            captured_task=captured_task,
        )
    return NativeChildStaffingResult(
        staffed=False,
        reason_code=reason_code,
        rewritten_task=task,
        diagnostic_decision_id=diagnostic_id,
        task_sha256=task_sha256,
        provider_attempts=tuple(dict(item) for item in (provider_attempts or [])),
        routing_decision=decision,
    )


def _record_captured_assignment(
    store: Any,
    *,
    diagnostic_id: str,
    host: str,
    parent_session_id: str,
    parent_trace_id: str,
    task_sha256: str,
    captured_task: str,
) -> None:
    """Persist the redacted assignment in its own content lane, fail-open.

    The routing-decision projection is content-free by design, so the capture
    never rides the decision dict; it is a separate store write keyed to the
    recorded decision, skipped whenever the flag left ``captured_task`` empty
    or the decision itself was not persisted.
    """

    if not captured_task or not diagnostic_id:
        return
    recorder = getattr(store, "record_native_child_captured_assignment", None)
    if not callable(recorder):
        return
    try:
        recorder(
            diagnostic_id=diagnostic_id,
            host=host,
            parent_session_id=parent_session_id,
            parent_trace_id=parent_trace_id,
            task_sha256=task_sha256,
            captured_task=captured_task,
        )
    except Exception:
        return


def _exact_compatible_team(
    selected_ids: list[str],
    catalog: list[dict[str, Any]],
) -> bool:
    try:
        compiled = compile_compatibility_catalog(catalog)
        receipt = enforce_compatible_set(
            selected_ids,
            compiled,
            limit=MAX_INFERENCE_TEAM_CARDS,
        )
    except Exception:
        return False
    return bool(
        receipt.get("compatible") is True
        and receipt.get("requested_ids") == selected_ids
        and receipt.get("selected_ids") == selected_ids
        and receipt.get("selected_root_ids") == selected_ids
        and receipt.get("added_requirements") == []
        and receipt.get("overflow_review_ids") == []
        and receipt.get("rejected") == []
        and receipt.get("separate_context_pairs") == []
    )


def _hydrate_team(
    store: Any,
    *,
    selected_ids: list[str],
    catalog: list[dict[str, Any]],
    disabled_agents: frozenset[str],
) -> tuple[InferenceTeamCard, ...] | None:
    prompt_reader = getattr(store, "get_versioned_specialist_prompt", None)
    if not callable(prompt_reader):
        return None
    by_slug = {agent_identity(item): item for item in catalog if agent_identity(item)}
    if len(by_slug) != len(catalog):
        return None
    cards: list[InferenceTeamCard] = []
    for slug in selected_ids:
        agent = by_slug.get(slug)
        if agent is None:
            return None
        version = str(agent.get("version") or "").strip()
        stored_prompt_hash = str(agent.get("hash") or "").strip().casefold()
        # Store keys retain both supported SHA-256 forms. Read the exact key,
        # then bind v6 delivery and durable evidence to the canonical bare digest.
        delivery_prompt_hash = content_digest_identity(stored_prompt_hash)
        if (
            not version
            or normalize_version_identity(version) != version
            or delivery_prompt_hash is None
        ):
            return None
        try:
            prompt = prompt_reader(
                slug,
                version,
                stored_prompt_hash,
                max_chars=MAX_SPECIALIST_PROMPT_CHARS + 1,
                disabled_agents=disabled_agents,
            )
        except Exception:
            return None
        if not isinstance(prompt, Mapping):
            return None
        body = prompt.get("prompt_body")
        if (
            prompt.get("prompt_truncated") is not False
            or prompt.get("slug") != slug
            or prompt.get("version") != version
            or str(prompt.get("hash") or "").strip().casefold() != stored_prompt_hash
            or not isinstance(body, str)
            or not body
            or len(body) > MAX_SPECIALIST_PROMPT_CHARS
        ):
            return None
        try:
            if not content_identity_matches(body, stored_prompt_hash):
                return None
        except UnicodeEncodeError:
            return None
        cards.append(
            InferenceTeamCard(
                specialist_slug=slug,
                specialist_version=version,
                specialist_prompt_hash=delivery_prompt_hash,
                prompt_body=body,
            )
        )
    return tuple(cards)


def staff_native_child(  # noqa: C901 - one ordered fail-open native-child boundary
    store: Any,
    *,
    host: str,
    task: object,
    parent_session_id: object,
    parent_trace_id: object,
    launch_id: object,
    binding_kind: object,
    binding_id: object,
    install_identity: object,
    install_identity_reader: Callable[[str], object],
    config: AgencyConfig | None = None,
    platform: str | None = None,
    available_tools: Container[str] | None = None,
    capability_status: str = "",
    capabilities_restricted: bool = False,
    maximum_delivery_bytes: int = MAX_NATIVE_CHILD_STAFFING_DELIVERY_BYTES,
    ttl_seconds: int = NATIVE_CHILD_STAFFING_TTL_SECONDS,
    delivery_validator: Callable[[str], bool] | None = None,
    final_delivery_validator: Callable[[], bool] | None = None,
) -> NativeChildStaffingResult:
    """Return one exact inference-selected v6 team or an unstaffed diagnostic.

    ``binding_kind`` and ``binding_id`` are the host-authenticated child
    correlation (for example ``child_session`` or ``native_run``). ``launch_id``
    is the host-neutral launch identity: Claude/ZCode use their tool-use ID,
    Hermes/OpenClaw use a native-run ID, and Codex must supply an authenticated
    plaintext launch/input identity before this service can staff it.
    ``final_delivery_validator`` is passed to the Store for the last guarded
    pre-commit check; it must not persist state or re-enter the Store.
    """

    original_task = task if isinstance(task, str) else ""
    config_was_explicit = config is not None
    config_authority = config if config_was_explicit else None
    try:
        normalized_host = str(host or "").strip().casefold()
        if normalized_host not in EXECUTION_HOSTS:
            raise ValueError("unsupported host")
        if not isinstance(task, str) or not task:
            raise ValueError("task is required")
        task.encode("utf-8")
        session_id = validate_correlation_id(parent_session_id, field="parent_session_id")
        trace_id = validate_correlation_id(parent_trace_id, field="parent_trace_id")
        normalized_launch_id = validate_correlation_id(launch_id, field="launch_id")
        normalized_binding_kind = str(binding_kind or "").strip().casefold()
        normalized_binding_id = validate_correlation_id(binding_id, field="binding_id")
        if (
            _BINDING_KIND.fullmatch(normalized_binding_kind) is None
            or normalized_binding_kind not in _SUPPORTED_BINDING_KINDS
            or isinstance(maximum_delivery_bytes, bool)
            or not isinstance(maximum_delivery_bytes, int)
            or not 1 <= maximum_delivery_bytes <= MAX_NATIVE_CHILD_STAFFING_DELIVERY_BYTES
            or isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or not 1 <= ttl_seconds <= MAX_NATIVE_CHILD_DELIVERY_TTL_SECONDS
            or (delivery_validator is not None and not callable(delivery_validator))
            or (final_delivery_validator is not None and not callable(final_delivery_validator))
            or not callable(install_identity_reader)
        ):
            raise ValueError("staffing budget is invalid")
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_request_invalid",
            task=original_task,
        )

    task_hash = _digest(original_task)
    if not _parent_scope_is_current(
        store,
        host=normalized_host,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
    ):
        return _unstaffed(
            store=store,
            reason_code="native_child_parent_scope_invalid",
            task=original_task,
        )
    failure_context_fingerprint = _failure_context_fingerprint(
        host=normalized_host,
        parent_session_id=session_id,
        parent_trace_id=trace_id,
        launch_id=normalized_launch_id,
        task_sha256=task_hash,
    )
    install = _valid_install_identity(install_identity, host=normalized_host)
    if install is None:
        return _unstaffed(
            store=store,
            reason_code="native_child_install_identity_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=failure_context_fingerprint,
            judge_result={
                "inference_configured": False,
                "inference_attempted": False,
            },
        )

    try:
        current_install = _valid_install_identity(
            install_identity_reader(normalized_host),
            host=normalized_host,
        )
    except Exception:
        current_install = None
    if current_install != install:
        return _unstaffed(
            store=store,
            reason_code="native_child_install_identity_changed",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=failure_context_fingerprint,
            judge_result={
                "inference_configured": False,
                "inference_attempted": False,
            },
        )

    normalized_platform = str(platform or _default_platform()).strip().casefold()
    resolved_tools = available_tools
    resolved_capability_status = capability_status
    if available_tools is None and not str(capability_status or "").strip():
        # Rule 4 needs the child judge to see the same complete universe the
        # parent recruiter sees. Leaving capability unproven is not a hard
        # eligibility ground: it hard-filters every tool-declaring card before
        # inference runs, which erases the staffing decision rather than
        # enforcing it. Prove this host's capability the way the parent adapter
        # already does, and keep failing closed when it cannot be proven.
        try:
            capability = native_adapter_capability_receipt(
                normalized_host,
                platform=normalized_platform,
                session_id=session_id,
                trace_id=trace_id,
                restricted=capabilities_restricted,
            )
        except Exception:
            capability = None
        if capability is not None and capability.execution_host == normalized_host:
            normalized_platform = capability.platform
            resolved_tools = capability.capabilities
            resolved_capability_status = capability.status
    try:
        snapshot = capture_routing_snapshot(store, config_authority)
        eligibility = filter_eligible_catalog(
            snapshot.catalog,
            host=normalized_host,
            platform=normalized_platform,
            available_tools=resolved_tools,
            capability_status=resolved_capability_status,
        )
        eligible_catalog = list(eligibility.eligible)
        context_fingerprint = _context_fingerprint(
            host=normalized_host,
            platform=normalized_platform,
            available_tools=resolved_tools,
            capability_status=resolved_capability_status,
            disabled_agents=frozenset(snapshot.config.agents.disabled),
            roster_generation=snapshot.roster_generation,
            catalog=eligible_catalog,
            install=install,
        )
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_catalog_unavailable",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=failure_context_fingerprint,
            judge_result={
                "inference_configured": False,
                "inference_attempted": False,
            },
        )
    try:
        captured_task = (
            redact_content(original_task) if snapshot.config.observability.capture_content else ""
        )
    except Exception:
        captured_task = ""
    if not eligible_catalog:
        return _unstaffed(
            store=store,
            reason_code="native_child_eligible_catalog_empty",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
        )

    try:
        judge_config, requested_provider = canary_child_judge_config(
            snapshot.config,
            normalized_host,
            os.environ,
        )
    except CanaryChildJudgeProviderError:
        return _unstaffed(
            store=store,
            reason_code="native_child_canary_provider_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result={
                "inference_configured": False,
                "inference_attempted": False,
            },
        )

    try:
        judge_result = query_judge(
            original_task,
            eligible_catalog,
            config=judge_config,
            max_selected=MAX_INFERENCE_TEAM_CARDS,
            candidate_scope="complete",
        )
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_inference_unavailable",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
        )
    if not isinstance(judge_result, Mapping):
        return _unstaffed(
            store=store,
            reason_code="native_child_inference_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
        )
    try:
        judge_result = dict(judge_result)
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_inference_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
        )
    if requested_provider:
        judge_result["requested_provider"] = requested_provider

    state_unchanged = _routing_state_matches(
        store,
        config_authority=config_authority,
        expected_config=snapshot.config,
        host=normalized_host,
        platform=normalized_platform,
        available_tools=resolved_tools,
        capability_status=resolved_capability_status,
        context_fingerprint=context_fingerprint,
        install=install,
        install_identity_reader=install_identity_reader,
    )
    if not state_unchanged:
        return _unstaffed(
            store=store,
            reason_code="native_child_routing_state_changed",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
        )

    try:
        projected_attempts = project_model_receipt_attempts(judge_result.get("provider_attempts"))
    except Exception:
        projected_attempts = None
    if judge_result.get("status") != "applied" or judge_result.get("inference_mode") != "inferred":
        reason = (
            "native_child_inference_unavailable"
            if judge_result.get("status") == "inference_unavailable"
            or judge_result.get("inference_mode") == "unavailable"
            else "native_child_inference_invalid"
        )
        return _unstaffed(
            store=store,
            reason_code=reason,
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=[] if projected_attempts is None else projected_attempts,
        )
    receipt_digest = canonical_native_child_provider_receipt_digest(projected_attempts)
    if (
        projected_attempts is None
        or receipt_digest is None
        or sum(item.get("status") == "applied" for item in projected_attempts) != 1
    ):
        return _unstaffed(
            store=store,
            reason_code="native_child_provider_receipt_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=[] if projected_attempts is None else projected_attempts,
        )

    # Computed before the decline branches, not after: what the judge was shown
    # is the evidence a decline turns on, and it was previously only in scope
    # for the paths that did not need it.
    eligible_ids = {agent_identity(item) for item in eligible_catalog}
    offered_ids = sorted(eligible_ids)
    selected = judge_result.get("selected_ids")
    if type(selected) is list and not selected:
        # Solicited abstention: the judge was offered the complete eligible
        # universe and answered that none of it fits. AR-255 P2 funds exactly
        # one repair call before that answer is final: the judge is asked to
        # test its own abstention against the same concrete candidate set. The
        # repair never instructs a selection -- an empty answer remains valid
        # -- so inference keeps the decision either way (ADR-0118).
        try:
            repair_result: Any = query_judge(
                repair_abstention_task(original_task),
                eligible_catalog,
                config=judge_config,
                max_selected=MAX_INFERENCE_TEAM_CARDS,
                candidate_scope="complete",
            )
        except Exception:
            repair_result = None
        if isinstance(repair_result, Mapping):
            try:
                repair_result = dict(repair_result)
                if requested_provider:
                    repair_result["requested_provider"] = requested_provider
            except Exception:
                repair_result = None
        else:
            repair_result = None
        repair_attempts: list[dict[str, Any]] | None = None
        repair_digest: str | None = None
        repair_selected: Any = None
        if (
            repair_result is not None
            and repair_result.get("status") == "applied"
            and repair_result.get("inference_mode") == "inferred"
        ):
            try:
                repair_attempts = project_model_receipt_attempts(
                    repair_result.get("provider_attempts")
                )
            except Exception:
                repair_attempts = None
            repair_digest = canonical_native_child_provider_receipt_digest(repair_attempts)
            repair_selected = repair_result.get("selected_ids")
        diagnostic_attempts = list(projected_attempts or [])
        if repair_attempts is not None:
            diagnostic_attempts.extend(repair_attempts)
        if (
            repair_result is None
            or type(repair_selected) is not list
            or (
                repair_selected
                and (
                    repair_attempts is None
                    or repair_digest is None
                    or sum(item.get("status") == "applied" for item in repair_attempts) != 1
                )
            )
        ):
            # The repair could not produce a valid answer, so the first-pass
            # abstention stands unconfirmed under the legacy reason.
            return _unstaffed(
                store=store,
                reason_code=NATIVE_CHILD_ABSTAINED_REASON,
                task=original_task,
                host=normalized_host,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                task_sha256=task_hash,
                context_fingerprint=context_fingerprint,
                judge_result=judge_result,
                provider_attempts=diagnostic_attempts,
                offered_ids=offered_ids,
                captured_task=captured_task,
            )
        if not repair_selected:
            # The judge tested its own abstention and reaffirmed it.
            return _unstaffed(
                store=store,
                reason_code=NATIVE_CHILD_ABSTENTION_CONFIRMED_REASON,
                task=original_task,
                host=normalized_host,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                task_sha256=task_hash,
                context_fingerprint=context_fingerprint,
                judge_result=repair_result,
                provider_attempts=diagnostic_attempts,
                offered_ids=offered_ids,
                captured_task=captured_task,
            )
        # The repair produced a selection. Adopt the repair call wholesale --
        # its receipt is the one applied provider response the decision binds
        # -- and re-verify the routing state the extra call may have outlived.
        if not _routing_state_matches(
            store,
            config_authority=config_authority,
            expected_config=snapshot.config,
            host=normalized_host,
            platform=normalized_platform,
            available_tools=resolved_tools,
            capability_status=resolved_capability_status,
            context_fingerprint=context_fingerprint,
            install=install,
            install_identity_reader=install_identity_reader,
        ):
            return _unstaffed(
                store=store,
                reason_code="native_child_routing_state_changed",
                task=original_task,
                host=normalized_host,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                task_sha256=task_hash,
                context_fingerprint=context_fingerprint,
                judge_result=repair_result,
            )
        judge_result = repair_result
        projected_attempts = repair_attempts
        receipt_digest = repair_digest
        selected = repair_selected
    if (
        type(selected) is not list
        or not 1 <= len(selected) <= MAX_INFERENCE_TEAM_CARDS
        or any(type(item) is not str or item not in eligible_ids for item in selected)
        or len(set(selected)) != len(selected)
    ):
        return _unstaffed(
            store=store,
            reason_code="native_child_inference_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
            # A selection naming an agent outside the offered set is the one
            # invalid response the offered set explains directly.
            offered_ids=offered_ids,
        )
    selected_ids = list(selected)
    if not _exact_compatible_team(selected_ids, eligible_catalog):
        return _unstaffed(
            store=store,
            reason_code="native_child_compatibility_mutated",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )

    try:
        cards = _hydrate_team(
            store,
            selected_ids=selected_ids,
            catalog=eligible_catalog,
            disabled_agents=frozenset(snapshot.config.agents.disabled),
        )
    except Exception:
        cards = None
    if cards is None or len(cards) != len(selected_ids):
        return _unstaffed(
            store=store,
            reason_code="native_child_prompt_hydration_failed",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )

    try:
        issued = _utc_now()
        issued_at = _timestamp(issued)
        expires_at = _timestamp(issued + timedelta(seconds=ttl_seconds))
        nonce = validate_correlation_id(_nonce(), field="nonce")
        proposed_decision_id = validate_correlation_id(_decision_id(), field="decision_id")
        if _ROUTE_ID.fullmatch(proposed_decision_id) is None:
            raise ValueError("generated decision ID is invalid")
        team_digest = inference_team_digest(cards)
        card_descriptors = [
            {
                "specialist_slug": card.specialist_slug,
                "specialist_version": card.specialist_version,
                "specialist_prompt_hash": card.specialist_prompt_hash,
                "body_character_length": card.body_character_length,
            }
            for card in cards
        ]
        delivery_input = {
            "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
            "host": normalized_host,
            "parent_session_id": session_id,
            "parent_trace_id": trace_id,
            "launch_id": normalized_launch_id,
            "binding_kind": normalized_binding_kind,
            "binding_id": normalized_binding_id,
            "provider_attempts": projected_attempts,
            "provider_receipt_digest": receipt_digest,
            "task_sha256": task_hash,
            "team_digest": team_digest,
            "candidate_digest": install.candidate_digest,
            "runtime_digest": install.running_runtime_digest,
            "install_id": install.install_id,
            "bundle_digest": install.bundle_digest,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "nonce": nonce,
            "cards": card_descriptors,
        }
        delivery_projection = project_native_child_staffing_decision(delivery_input)
        if delivery_projection is None:
            raise ValueError("native child delivery projection was rejected")
        exact_identity = {
            "host": normalized_host,
            "parent_session_id": session_id,
            "parent_trace_id": trace_id,
            "launch_id": normalized_launch_id,
            "decision_id": proposed_decision_id,
            "provider_receipt_digest": receipt_digest,
            "candidate_digest": install.candidate_digest,
            "install_id": install.install_id,
            "bundle_digest": install.bundle_digest,
            "runtime_digest": install.running_runtime_digest,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "nonce": nonce,
            "binding_kind": normalized_binding_kind,
            "binding_id": normalized_binding_id,
        }
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_delivery_binding_invalid",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )

    try:
        rewritten_task = render_inference_team_delivery(original_task, cards, **exact_identity)
        context_segment = render_inference_team_context_segment(
            original_task,
            cards,
            **exact_identity,
        )
        parsed = parse_inference_team_delivery(rewritten_task)
        if (
            rewritten_task != original_task + context_segment
            or parsed is None
            or parsed.original_task != original_task
            or parsed.host != normalized_host
            or parsed.parent_session_id != session_id
            or parsed.parent_trace_id != trace_id
            or parsed.decision_id != proposed_decision_id
            or parsed.launch_id != normalized_launch_id
            or parsed.provider_receipt_digest != receipt_digest
            or parsed.task_sha256 != task_hash
            or parsed.candidate_digest != install.candidate_digest
            or parsed.install_id != install.install_id
            or parsed.bundle_digest != install.bundle_digest
            or parsed.runtime_digest != install.running_runtime_digest
            or parsed.issued_at != issued_at
            or parsed.expires_at != expires_at
            or parsed.nonce != nonce
            or parsed.binding_kind != normalized_binding_kind
            or parsed.binding_id != normalized_binding_id
            or parsed.team_digest != team_digest
            or tuple(
                (
                    card.specialist_slug,
                    card.specialist_version,
                    card.specialist_prompt_hash,
                    card.body_character_length,
                )
                for card in parsed.cards
            )
            != tuple(
                (
                    card["specialist_slug"],
                    card["specialist_version"],
                    card["specialist_prompt_hash"],
                    card["body_character_length"],
                )
                for card in delivery_projection["cards"]
            )
        ):
            raise ValueError("rendered native child delivery failed self-verification")
    except Exception:
        return _unstaffed(
            store=store,
            reason_code="native_child_delivery_render_failed",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )

    try:
        over_budget = len(rewritten_task.encode("utf-8")) > maximum_delivery_bytes
    except UnicodeError:
        over_budget = True
    if over_budget:
        return _unstaffed(
            store=store,
            reason_code="native_child_delivery_over_budget",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )
    if delivery_validator is not None:
        try:
            delivery_valid = delivery_validator(rewritten_task) is True
        except Exception:
            delivery_valid = False
        if not delivery_valid:
            return _unstaffed(
                store=store,
                reason_code="native_child_delivery_validation_failed",
                task=original_task,
                host=normalized_host,
                parent_session_id=session_id,
                parent_trace_id=trace_id,
                task_sha256=task_hash,
                context_fingerprint=context_fingerprint,
                judge_result=judge_result,
                provider_attempts=projected_attempts,
            )

    routing_decision = _routing_projection(
        result=judge_result,
        task_sha256=task_hash,
        context_fingerprint=context_fingerprint,
        selected_ids=selected_ids,
        status="applied",
        source=_SUCCESS_SOURCE,
        native_child_delivery=delivery_projection,
    )
    state_unchanged = False
    decision_id = ""
    try:
        # Cooperative config writers acquire this same lock before consulting
        # Store.  Keep the global order config lock -> SQLite BEGIN IMMEDIATE:
        # the final live reload and exact route insert are one guarded slice.
        with _native_child_config_read_lock(store):
            state_unchanged = _routing_state_matches(
                store,
                config_authority=config_authority,
                expected_config=snapshot.config,
                host=normalized_host,
                platform=normalized_platform,
                available_tools=resolved_tools,
                capability_status=resolved_capability_status,
                context_fingerprint=context_fingerprint,
                install=install,
                install_identity_reader=install_identity_reader,
            )
            decision_id = (
                _record_decision(
                    store,
                    host=normalized_host,
                    parent_session_id=session_id,
                    parent_trace_id=trace_id,
                    task_sha256=task_hash,
                    context_fingerprint=context_fingerprint,
                    decision=routing_decision,
                    decision_id=proposed_decision_id,
                    expected_roster_generation=snapshot.roster_generation,
                    expected_disabled_agents=tuple(snapshot.config.agents.disabled),
                    final_delivery_validator=final_delivery_validator,
                )
                if state_unchanged
                else ""
            )
    except Exception:
        # A config-lock release can fail after ``record_routing_decision`` has
        # already committed.  Preserve that exact success so the caller emits
        # the matching staffed output; converting it to an unstaffed result
        # would leave a successful route that poisons an otherwise safe retry.
        if not decision_id:
            state_unchanged = False
    if not state_unchanged:
        return _unstaffed(
            store=store,
            reason_code="native_child_routing_state_changed",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )
    if decision_id:
        _record_captured_assignment(
            store,
            diagnostic_id=decision_id,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            captured_task=captured_task,
        )
    if not decision_id:
        return _unstaffed(
            store=store,
            reason_code="native_child_routing_decision_unavailable",
            task=original_task,
            host=normalized_host,
            parent_session_id=session_id,
            parent_trace_id=trace_id,
            task_sha256=task_hash,
            context_fingerprint=context_fingerprint,
            judge_result=judge_result,
            provider_attempts=projected_attempts,
        )
    return NativeChildStaffingResult(
        staffed=True,
        reason_code="staffed",
        rewritten_task=rewritten_task,
        context_segment=context_segment,
        decision_id=decision_id,
        task_sha256=task_hash,
        provider_receipt_digest=receipt_digest,
        team_digest=team_digest,
        selected_ids=tuple(selected_ids),
        provider_attempts=tuple(dict(item) for item in projected_attempts),
        native_child_delivery=delivery_projection,
        routing_decision={**routing_decision, "decision_id": decision_id},
    )


__all__ = [
    "MAX_NATIVE_CHILD_STAFFING_DELIVERY_BYTES",
    "NATIVE_CHILD_STAFFING_TTL_SECONDS",
    "NativeChildStaffingResult",
    "record_native_child_staffing_failure",
    "staff_native_child",
]
