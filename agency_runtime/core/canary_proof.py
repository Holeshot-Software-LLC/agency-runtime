"""Readiness, evidence correlation, and durable proof for host canaries."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.agent_activation import normalize_agent_slug
from agency_runtime.core.child_delivery_evidence import (
    HOST_CHILD_COLLECTION_REASONS,
    _consume_verified_host_child_delivery,
    _VerifiedHostChildDelivery,
)
from agency_runtime.core.codex_child_tool_evidence import (
    normalize_codex_child_tool_evidence,
)
from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
)
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.roster.revisions import content_digest_identity
from agency_runtime.core.specialist_contracts import MAX_SPECIALIST_PROMPT_CHARS
from agency_runtime.core.store.version_identity import normalize_version_identity

logger = logging.getLogger(__name__)

CANARY_INVOCATION_FAILURE_REASONS = frozenset(
    {
        "native_collaboration_full_history_parent_unavailable",
        "codex_result_projection_unavailable",
        "codex_output_projection_unavailable",
        "codex_collaboration_projection_unavailable",
        "codex_parent_spawn_missing",
        "codex_parent_wait_missing",
        "codex_native_tool_output_missing",
        "codex_native_child_start_missing",
        "codex_hook_trust_not_ready",
        "codex_exec_timed_out",
    }
)

_HOST_CHILD_DELIVERY_SCHEMA = "agency.host-child-delivery-proof.v1"
_HOST_CHILD_DELIVERY_FIELDS = frozenset(
    {
        "schema",
        "verified_delivery",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "child_id",
        "pre_speech",
        "cards",
        "artifact_digest",
        "decision_id",
        "provider_receipt_digest",
        "task_sha256",
        "team_digest",
        "candidate_digest",
        "runtime_digest",
        "install_id",
        "bundle_digest",
        "issued_at",
        "expires_at",
        "nonce",
        "binding_kind",
        "binding_id",
    }
)
_HOST_CHILD_CARD_FIELDS = frozenset(
    {
        "specialist_slug",
        "specialist_version",
        "specialist_prompt_hash",
        "body_character_length",
    }
)
_NATIVE_CHILD_DELIVERY_RECEIPT_FIELDS = frozenset(
    {
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
        "verified_at",
        "verified_delivery",
    }
)
_NATIVE_CHILD_ROUTE_FIELDS = frozenset(
    {
        "decision_id",
        "trace_id",
        "session_id",
        "query_hash",
        "context_fingerprint",
        "created_at",
        "schema",
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "binding_kind",
        "binding_id",
        "provider_attempts",
        "provider_receipt_digest",
        "task_sha256",
        "team_digest",
        "candidate_digest",
        "runtime_digest",
        "install_id",
        "bundle_digest",
        "issued_at",
        "expires_at",
        "nonce",
        "cards",
    }
)
_LOWER_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_CODEX_HOST_CHILD_CARDS = 3
_MAX_CODEX_HOST_IDENTITY_CHARS = 256
_MAX_CODEX_CARD_IDENTITY_CHARS = 128


def _facade():
    """Resolve canary dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import canary

    return canary


def ids(activity: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    return {
        name: {str(row.get("id")) for row in rows if row.get("id")}
        for name, rows in activity.items()
    }


def evidence_delta(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    previous = _facade()._ids(before)
    return {
        name: [row for row in rows if str(row.get("id")) not in previous.get(name, set())]
        for name, rows in after.items()
    }


def response_text(value: Any, *, _depth: int = 0) -> str:
    if _depth > 8:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "result", "message", "output"):
            text = response_text(value.get(key), _depth=_depth + 1)
            if text:
                return text
        return ""
    if isinstance(value, list):
        return "\n".join(
            filter(
                None,
                (response_text(item, _depth=_depth + 1) for item in value),
            )
        )
    return ""


def evidence_summary(
    delta: dict[str, list[dict[str, Any]]],
    host: str,
    *,
    expected_query_hash: str,
) -> dict[str, Any]:
    facade = _facade()
    routing = [
        row for row in delta.get("routing", []) if row.get("query_hash") == expected_query_hash
    ]
    finalizations = [row for row in delta.get("finalizations", []) if row.get("host") == host]
    receipts = [row for row in delta.get("receipts", []) if row.get("host") == host]
    specialists = list(delta.get("specialists", []))
    completed_runs = [
        row
        for row in delta.get("runs", [])
        if row.get("host") == host
        and row.get("status") == "completed"
        and bool(row.get("ended_at"))
    ]
    accepted_finalizations = [
        row
        for row in finalizations
        if row.get("action") == "accept" and row.get("terminal_status") == "completed"
    ]
    route_traces = {str(row.get("trace_id")) for row in routing if row.get("trace_id")}
    final_traces = {str(row.get("trace_id")) for row in finalizations if row.get("trace_id")}
    accepted_traces = {
        str(row.get("trace_id")) for row in accepted_finalizations if row.get("trace_id")
    }
    completed_traces = {str(row.get("trace_id")) for row in completed_runs if row.get("trace_id")}
    receipt_traces = {str(row.get("trace_id")) for row in receipts if row.get("trace_id")}
    expected_specialist = str(facade.CANARY_EXPECTED_SPECIALIST)
    routed_specialists = sorted(
        {
            str(agent_id)
            for row in routing
            for field in ("selected_ids", "companion_ids")
            for agent_id in row.get(field, [])
            if agent_id
        }
    )
    loaded_specialists = sorted(
        {
            str(row.get("slug"))
            for row in specialists
            if str(row.get("trace_id") or "") in route_traces and row.get("slug")
        }
    )
    correlated = sorted(route_traces & final_traces)
    accepted = sorted(route_traces & accepted_traces & completed_traces)
    receipt_correlated = sorted(set(correlated) & receipt_traces)
    receipt_required = host in facade.RECEIPT_CAPABLE_HOSTS
    return {
        "new_ids": {
            name: [str(row.get("id")) for row in rows if row.get("id")]
            for name, rows in delta.items()
        },
        "counts": {name: len(rows) for name, rows in delta.items()},
        "host_finalization_count": len(finalizations),
        "accepted_finalization_count": len(accepted_finalizations),
        "host_receipt_count": len(receipts),
        "correlated_trace_ids": correlated,
        "accepted_trace_ids": accepted,
        "completed_run_trace_ids": sorted(completed_traces),
        "receipt_correlated_trace_ids": receipt_correlated,
        "receipt_required": receipt_required,
        "receipt_proven": bool(receipt_correlated),
        "expected_specialist": expected_specialist,
        "routed_specialists": routed_specialists,
        "loaded_specialists": loaded_specialists,
        "expected_specialist_selected": expected_specialist in routed_specialists,
        "expected_specialist_loaded": expected_specialist in loaded_specialists,
        "query_hash": expected_query_hash,
    }


@dataclass(frozen=True)
class ReadinessAssessment:
    native: dict[str, Any]
    control: dict[str, Any]
    profile_scope: str
    platform: dict[str, str]
    unmet: tuple[str, ...]


@dataclass(frozen=True)
class LivePreparation:
    store: Any | None
    before: dict[str, list[dict[str, Any]]] | None
    backend: Any | None
    prompt: str | None
    expected_query_hash: str | None
    error: str | None = None


@dataclass(frozen=True)
class InvocationOutcome:
    result: dict[str, Any] | None
    evidence: dict[str, Any] | None
    host_child_delivery: _VerifiedHostChildDelivery | None = None
    error: str | None = None


@dataclass(frozen=True)
class CanaryProof:
    invocation: dict[str, Any]
    result_scope: str
    passed: bool
    failures: tuple[str, ...]


def assess_readiness(
    host: str,
    path: Path,
    inspector: Callable[[str], dict[str, Any]],
    *,
    profile_scope: str | None = None,
) -> ReadinessAssessment:
    facade = _facade()
    try:
        inspected = inspector(host)
    except Exception:
        inspected = None
    native = (
        inspected
        if isinstance(inspected, dict)
        else {"host": host, "inspection_error": "native inspection unavailable"}
    )
    profile_scope = profile_scope or (
        "isolated-profile" if host in facade.ISOLATED_CANARY_HOSTS else "current-profile"
    )
    control = facade._read_control_without_writes(path, host)
    unmet: list[str] = []
    if native.get("executable_discovered") is not True:
        unmet.append("host executable not discovered")
    if profile_scope == "current-profile":
        if native.get("registered") is not True:
            unmet.append("Agency Runtime plugin registration not proven")
        if native.get("enabled") is not True:
            unmet.append("native plugin enablement not proven")
    if not native.get("host_version"):
        unmet.append("native host version not proven")
    if not native.get("install_id") or not native.get("bundle_digest"):
        unmet.append("managed bundle identity not proven")
    if host not in facade.SAFE_CANARY_HOSTS:
        unmet.append(
            "host has no proven read-only, bounded native-child noninteractive canary mode"
        )
    if control.get("enabled") is not True:
        unmet.append("Agency Runtime soft control is disabled or unverified")
    return ReadinessAssessment(
        native=native,
        control=control,
        profile_scope=profile_scope,
        platform={
            "system": facade.platform.system(),
            "release": facade.platform.release(),
            "machine": facade.platform.machine(),
        },
        unmet=tuple(unmet),
    )


def readiness_report(
    host: str,
    assessment: ReadinessAssessment,
    *,
    mode: str = "agency",
    trust_mode: str = "attended",
) -> dict[str, Any]:
    confirmation = (
        f"RUN LIVE {host} CURRENT-PROFILE CANARY"
        if assessment.profile_scope == "current-profile"
        else f"RUN LIVE {host} CANARY"
        if mode == "agency"
        else f"RUN LIVE {host} NATIVE-ONLY CANARY"
    )
    return {
        "schema_version": "agency.host_canary.v1",
        "sampled_at": _facade()._utc_now(),
        "host": host,
        "mode": mode,
        "profile_scope": assessment.profile_scope,
        "trust_mode": trust_mode,
        "trust_bypass_used": False,
        "platform": assessment.platform,
        "native": assessment.native,
        "real_profile_native": assessment.native,
        "runtime_control": assessment.control,
        "ready": not assessment.unmet,
        "execute_confirmation": confirmation,
        "live_attempted": False,
        "canary_passed": False,
        "attestation_persisted": False,
        "unmet_prerequisites": list(assessment.unmet),
    }


def prepare_live_invocation(
    host: str,
    *,
    path: Path,
    timeout: float,
    native: Mapping[str, Any],
    backend_factory: Callable[..., Any],
    master_enabled: bool = True,
    mode: str = "agency",
    profile_scope: str = "isolated-profile",
    require_existing_store: bool = False,
    trust_mode: str = "attended",
) -> LivePreparation:
    facade = _facade()
    try:
        store = (
            facade.Store(path, require_existing_current=True)
            if require_existing_store
            else facade.Store(path)
        )
        before = store.recent_runtime_activity(limit=200)
    except Exception:
        return LivePreparation(
            store=None,
            before=None,
            backend=None,
            prompt=None,
            expected_query_hash=None,
            error="runtime evidence store is unavailable",
        )
    nonce = facade.secrets.token_hex(16)
    base_prompt = facade.CANARY_PROMPT if mode == "agency" else facade.NATIVE_ONLY_CANARY_PROMPT
    prompt = f"{base_prompt}\n\nCanary nonce: {nonce}"
    expected_query_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        if backend_factory is facade._backend:
            backend = backend_factory(
                host,
                db_path=path,
                timeout=timeout,
                native=native,
                master_enabled=master_enabled,
                profile_scope=profile_scope,
                require_existing_store=require_existing_store,
                require_exact_activation_rollout=host == "codex" and mode == "agency",
                trust_mode=trust_mode,
            )
        else:
            backend = backend_factory(host, db_path=path, timeout=timeout)
    except Exception:
        return LivePreparation(
            store=store,
            before=before,
            backend=None,
            prompt=prompt,
            expected_query_hash=expected_query_hash,
            error="safe noninteractive canary backend is unavailable",
        )
    return LivePreparation(
        store=store,
        before=before,
        backend=backend,
        prompt=prompt,
        expected_query_hash=expected_query_hash,
    )


def invoke_and_collect_evidence(
    preparation: LivePreparation,
    *,
    host: str,
    path: Path,
    prompt: str,
    expected_query_hash: str,
    mode: str = "agency",
) -> InvocationOutcome:
    if preparation.backend is None or preparation.store is None or preparation.before is None:
        return InvocationOutcome(
            result=None,
            evidence=None,
            error="safe canary invocation prerequisites are incomplete",
        )
    result: dict[str, Any] | None = None
    host_child_delivery: _VerifiedHostChildDelivery | None = None
    invocation_error: str | None = None
    facade = _facade()
    try:
        with private_temporary_directory(prefix="canary") as workdir:
            if host == "claude" and type(preparation.backend) is facade._SafeClaudeCanaryBackend:
                result, host_child_delivery = preparation.backend.execute_with_host_delivery(
                    task=prompt,
                    workdir=str(workdir),
                    store=preparation.store,
                    check=False,
                )
            else:
                result = preparation.backend.execute(
                    task=prompt,
                    workdir=str(workdir),
                    check=False,
                )
            if not isinstance(result, dict):
                raise RuntimeError("canary backend returned an invalid result")
    except Exception:
        # The reported error stays fixed and content-free: it travels into
        # evidence, and a formatted exception can carry prompt text. The real
        # traceback still has to reach whoever is diagnosing, or a precise
        # failure deep in the store arrives as an unattributed invocation
        # failure and costs a day to find again.
        logger.debug("safe host canary invocation raised", exc_info=True)
        invocation_error = "safe host invocation failed before evidence could be evaluated"
    if mode == "agency" and host == "codex":
        try:
            exact = preparation.store.get_canary_activation_snapshot(
                host=host,
                query_hash=expected_query_hash,
            )
        except Exception:
            return InvocationOutcome(
                result=result,
                evidence=None,
                error="exact activation evidence could not be read after host invocation",
            )
        return InvocationOutcome(
            result=result,
            evidence=exact,
            host_child_delivery=host_child_delivery,
            error=invocation_error,
        )
    try:
        after = preparation.store.recent_runtime_activity(limit=200)
    except Exception:
        return InvocationOutcome(
            result=result,
            evidence=None,
            host_child_delivery=host_child_delivery,
            error="runtime evidence could not be read after host invocation",
        )
    return InvocationOutcome(
        result=result,
        evidence=facade._evidence_summary(
            facade._evidence_delta(preparation.before, after),
            host,
            expected_query_hash=expected_query_hash,
        ),
        host_child_delivery=host_child_delivery,
        error=invocation_error,
    )


def _single_mapping(evidence: Mapping[str, Any], field: str) -> Mapping[str, Any] | None:
    values = evidence.get(field)
    if not isinstance(values, list) or len(values) != 1 or not isinstance(values[0], Mapping):
        return None
    return values[0]


def _codex_collaboration_chain(
    result: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str, tuple[str, ...]]:
    """Resolve one completed activation/execution protocol and receiver UUID."""

    collaboration = result.get("collaboration")
    calls = collaboration.get("calls") if isinstance(collaboration, Mapping) else None
    if isinstance(collaboration, Mapping) and (
        collaboration.get("unexpected_item_count", 0) != 0
        or collaboration.get("unexpected_item_types", []) not in ([], ())
    ):
        return None, "", ("Codex used a non-allowlisted tool during the activation canary",)
    if isinstance(calls, list) and len(calls) == 2:
        spawn, wait = calls
        if (
            not isinstance(spawn, Mapping)
            or not isinstance(wait, Mapping)
            or spawn.get("tool") != "spawn_agent"
            or wait.get("tool") != "wait"
            or spawn.get("status") != "completed"
            or wait.get("status") != "completed"
            or spawn.get("event_type") not in {"item.completed", "rollout_call_completed"}
            or wait.get("event_type") != spawn.get("event_type")
        ):
            return None, "", ("Codex did not prove one direct spawn and one completed wait",)
        sender_id = str(spawn.get("sender_thread_id") or "")
        receivers = spawn.get("receiver_thread_ids")
        if (
            not sender_id
            or wait.get("sender_thread_id") != sender_id
            or not isinstance(receivers, list)
            or len(receivers) != 1
            or wait.get("receiver_thread_ids") != receivers
        ):
            return None, "", ("Codex collaboration calls did not share one parent and child",)
        receiver_id = str(receivers[0])
        wait_states = wait.get("agents_states")
        if (
            not isinstance(wait_states, Mapping)
            or set(wait_states) != {receiver_id}
            or wait_states.get(receiver_id) != "completed"
        ):
            return spawn, receiver_id, ("the sole Codex child did not reach the completed state",)
        if not isinstance(spawn.get("execution_delivery"), Mapping):
            return (
                spawn,
                receiver_id,
                ("the sole Codex child did not receive its exact spawn turn",),
            )
        return spawn, receiver_id, ()
    if not isinstance(calls, list) or len(calls) != 4:
        return None, "", ("Codex did not prove one spawn, one followup, and two completed waits",)
    spawn_rows = [
        row for row in calls if isinstance(row, Mapping) and row.get("tool") == "spawn_agent"
    ]
    wait_rows = [row for row in calls if isinstance(row, Mapping) and row.get("tool") == "wait"]
    followup_rows = [
        row for row in calls if isinstance(row, Mapping) and row.get("tool") == "followup_task"
    ]
    if (
        len(spawn_rows) != 1
        or len(wait_rows) != 2
        or len(followup_rows) != 1
        or [row.get("tool") if isinstance(row, Mapping) else None for row in calls]
        != ["spawn_agent", "wait", "followup_task", "wait"]
        or spawn_rows[0].get("status") != "completed"
        or any(row.get("status") != "completed" for row in wait_rows)
        or followup_rows[0].get("status") != "completed"
        or spawn_rows[0].get("event_type") not in {"item.completed", "rollout_call_completed"}
        or any(
            row.get("event_type") != spawn_rows[0].get("event_type")
            for row in (*wait_rows, followup_rows[0])
        )
    ):
        return None, "", ("Codex did not prove one spawn, one followup, and two completed waits",)
    spawn = spawn_rows[0]
    followup = followup_rows[0]
    sender_id = str(spawn.get("sender_thread_id") or "")
    if not sender_id or any(
        row.get("sender_thread_id") != sender_id for row in (*wait_rows, followup)
    ):
        return None, "", ("Codex collaboration calls did not share one parent thread",)
    receivers = spawn.get("receiver_thread_ids")
    if (
        not isinstance(receivers, list)
        or len(receivers) != 1
        or any(row.get("receiver_thread_ids") != receivers for row in (*wait_rows, followup))
    ):
        return None, "", ("Codex collaboration calls did not identify the same sole child",)
    receiver_id = str(receivers[0])
    spawn_states = spawn.get("agents_states")
    if (
        not isinstance(spawn_states, Mapping)
        or set(spawn_states) != {receiver_id}
        or any(
            not isinstance(row.get("agents_states"), Mapping)
            or set(row["agents_states"]) != {receiver_id}
            or row["agents_states"].get(receiver_id) != "completed"
            for row in wait_rows
        )
    ):
        return spawn, receiver_id, ("the sole Codex child did not reach the completed state",)
    if not isinstance(spawn.get("execution_delivery"), Mapping) or spawn.get(
        "execution_delivery"
    ) != followup.get("execution_delivery"):
        return (
            spawn,
            receiver_id,
            ("the sole Codex child did not receive its exact execution turn",),
        )
    return spawn, receiver_id, ()


def _codex_receipt_link_failures(
    *,
    evidence: Mapping[str, Any],
    run: Mapping[str, Any],
    worker: Mapping[str, Any],
    finalization: Mapping[str, Any],
    receiver_id: str,
    response_hash: str,
) -> tuple[str, ...]:
    """Validate reciprocal Store links after the JSONL receiver alias is known."""

    failures: list[str] = []
    receiver_identity = (receiver_id, f"codex-agent:{receiver_id}")
    if (
        worker.get("worker_id") != receiver_identity[0]
        or worker.get("native_run_id") != receiver_identity[1]
        or worker.get("backend") != "spawn_agent"
        or worker.get("host") != "codex"
        or not worker.get("started_at")
        or not worker.get("ended_at")
    ):
        failures.append("SubagentStart and SubagentStop did not prove the Codex child lifecycle")
    if (
        run.get("status") != "completed"
        or not run.get("ended_at")
        or run.get("terminal_finalization_id") != finalization.get("id")
        or finalization.get("action") != "accept"
        or finalization.get("terminal_status") != "completed"
        or finalization.get("response_hash") != response_hash
    ):
        failures.append(
            "the returned response was not the exact authoritative accepted finalization"
        )
    return tuple(failures)


def _bounded_identity(value: object, *, maximum: int) -> str | None:
    """Return one nonempty, whitespace-stable bounded identity."""

    if not isinstance(value, str) or not value or value != value.strip() or not value.isprintable():
        return None
    try:
        if len(value.encode("utf-8")) > maximum:
            return None
    except UnicodeEncodeError:
        return None
    return value


def _sha256_identity(value: object) -> str | None:
    """Return one canonical lowercase SHA-256 identity."""

    if not isinstance(value, str) or _LOWER_SHA256.fullmatch(value) is None:
        return None
    return value


def _utc_timestamp(value: object) -> datetime | None:
    """Parse one canonical UTC timestamp carried by the verified envelope."""

    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(None):
        return None
    timespec = "microseconds" if parsed.microsecond else "seconds"
    canonical = parsed.isoformat(timespec=timespec).replace("+00:00", "Z")
    return parsed if value == canonical else None


def _ordered_route_slugs(route: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Return the inference-owned route order without repairing malformed rows."""

    ordered: list[str] = []
    for field in ("selected_ids", "companion_ids"):
        values = route.get(field)
        if not isinstance(values, list):
            return None
        for value in values:
            slug = _bounded_identity(value, maximum=_MAX_CODEX_CARD_IDENTITY_CHARS)
            if slug is None or slug in ordered:
                return None
            ordered.append(slug)
    return tuple(ordered) if ordered else None


def _native_child_route_projection_is_valid(route: Mapping[str, Any]) -> bool:
    """Revalidate one Store-projected inference route without trusting shape alone."""

    from agency_runtime.core.native_child_decision import (
        project_native_child_staffing_decision,
    )

    payload = {
        field: route.get(field)
        for field in _NATIVE_CHILD_ROUTE_FIELDS
        if field
        not in {
            "decision_id",
            "trace_id",
            "session_id",
            "query_hash",
            "context_fingerprint",
            "created_at",
        }
    }
    projected = project_native_child_staffing_decision(payload)
    return bool(
        projected is not None
        and payload == projected
        and _bounded_identity(route.get("decision_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
        is not None
        and _sha256_identity(route.get("context_fingerprint")) is not None
        and route.get("query_hash") == projected.get("task_sha256")
        and _bounded_identity(route.get("created_at"), maximum=128) is not None
    )


def _normalized_host_child_cards(value: object) -> list[dict[str, Any]] | None:
    """Validate the exact ordered generalized host-proof card descriptors."""

    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= _MAX_CODEX_HOST_CHILD_CARDS
        or any(not isinstance(card, Mapping) for card in value)
    ):
        return None
    normalized: list[dict[str, Any]] = []
    for card in value:
        assert isinstance(card, Mapping)
        if set(card) != _HOST_CHILD_CARD_FIELDS:
            return None
        slug = _bounded_identity(
            card.get("specialist_slug"), maximum=_MAX_CODEX_CARD_IDENTITY_CHARS
        )
        version = _bounded_identity(
            card.get("specialist_version"), maximum=_MAX_CODEX_CARD_IDENTITY_CHARS
        )
        prompt_hash = _sha256_identity(card.get("specialist_prompt_hash"))
        body_length = card.get("body_character_length")
        try:
            valid = bool(
                slug is not None
                and normalize_agent_slug(slug) == slug
                and version is not None
                and normalize_version_identity(version) == version
                and prompt_hash is not None
                and content_digest_identity(prompt_hash) == prompt_hash
                and type(body_length) is int
                and 1 <= body_length <= MAX_SPECIALIST_PROMPT_CHARS
            )
        except (TypeError, UnicodeEncodeError, ValueError):
            valid = False
        if not valid:
            return None
        normalized.append(
            {
                "specialist_slug": slug,
                "specialist_version": version,
                "specialist_prompt_hash": prompt_hash,
                "body_character_length": body_length,
            }
        )
    return normalized


def _claude_host_child_delivery_failures(
    *,
    proof: Mapping[str, Any] | None,
    evidence: Mapping[str, Any],
    collection_reason: str | None = None,
) -> tuple[str, ...]:
    """Validate the collector-minted Claude proof against the exact canary turn."""

    if not isinstance(proof, Mapping):
        stage = (
            collection_reason
            if collection_reason in HOST_CHILD_COLLECTION_REASONS
            and collection_reason != "collected"
            else None
        )
        return (
            (f"verified host-authored Claude child card delivery was not proven ({stage})")
            if stage is not None
            else "verified host-authored Claude child card delivery was not proven",
        )
    if set(proof) != _HOST_CHILD_DELIVERY_FIELDS:
        return ("host-authored Claude child delivery proof had an invalid contract",)
    if (
        proof.get("schema") != _HOST_CHILD_DELIVERY_SCHEMA
        or proof.get("verified_delivery") is not True
        or proof.get("host") != "claude"
        or proof.get("pre_speech") is not True
    ):
        return ("host-authored Claude child delivery proof was not verified",)
    cards = _normalized_host_child_cards(proof.get("cards"))
    if cards is None:
        return ("host-authored Claude child delivery did not contain a bounded card team",)
    slugs = tuple(card["specialist_slug"] for card in cards)
    routed = evidence.get("routed_specialists")
    expected = evidence.get("expected_specialist")
    if (
        not isinstance(routed, list)
        or any(not isinstance(value, str) for value in routed)
        or len(routed) != len(slugs)
        or set(routed) != set(slugs)
        or expected not in slugs
    ):
        return (
            "the inference-owned Claude canary route did not match the exact host child card team",
        )
    parent_trace_id = _bounded_identity(
        proof.get("parent_trace_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS
    )
    accepted = evidence.get("accepted_trace_ids")
    correlated = evidence.get("correlated_trace_ids")
    if (
        parent_trace_id is None
        or not isinstance(accepted, list)
        or not isinstance(correlated, list)
        or parent_trace_id not in accepted
        or parent_trace_id not in correlated
    ):
        return ("host-authored Claude child delivery did not match the accepted canary turn",)
    team_digest = hashlib.sha256(
        json.dumps(
            cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    issued_at = _utc_timestamp(proof.get("issued_at"))
    expires_at = _utc_timestamp(proof.get("expires_at"))
    binding_kind = proof.get("binding_kind")
    binding_id = proof.get("binding_id")
    child_id = _bounded_identity(proof.get("child_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
    launch_id = _bounded_identity(proof.get("launch_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
    if (
        _bounded_identity(proof.get("parent_session_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
        is None
        or child_id is None
        or launch_id is None
        or _bounded_identity(proof.get("decision_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
        is None
        or _sha256_identity(proof.get("provider_receipt_digest")) is None
        or _sha256_identity(proof.get("task_sha256")) is None
        or proof.get("team_digest") != team_digest
        or _sha256_identity(proof.get("candidate_digest")) is None
        or proof.get("candidate_digest") != proof.get("runtime_digest")
        or _bounded_identity(proof.get("install_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
        is None
        or _sha256_identity(proof.get("bundle_digest")) is None
        or _sha256_identity(proof.get("artifact_digest")) is None
        or _bounded_identity(proof.get("nonce"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS) is None
        or issued_at is None
        or expires_at is None
        or expires_at <= issued_at
        or binding_kind not in {"child_id", "launch_id"}
        or binding_id != (child_id if binding_kind == "child_id" else launch_id)
    ):
        return ("host-authored Claude child delivery identity bindings were invalid",)
    return ()


def _codex_host_child_delivery_failures(
    *,
    evidence: Mapping[str, Any],
    host_child_delivery: Mapping[str, Any] | None,
    parent_route: Mapping[str, Any],
    spawn: Mapping[str, Any],
    receiver_id: str,
) -> tuple[str, ...]:
    """Validate the sole authority that a card reached one Codex child.

    The mapping is a projection from a bounded verifier of the host-written
    child rollout. It is deliberately separate from Store specialist-load rows,
    stdout, and collaboration item projections, all of which Agency or the
    canary harness can originate.
    """

    proof = host_child_delivery
    native_route = evidence.get("native_child_route")
    receipt = evidence.get("native_child_delivery")
    if not all(isinstance(item, Mapping) for item in (proof, native_route, receipt)):
        return ("verified host-authored Codex child card delivery was not proven",)
    assert isinstance(proof, Mapping)
    assert isinstance(native_route, Mapping)
    assert isinstance(receipt, Mapping)
    if (
        set(proof) != _HOST_CHILD_DELIVERY_FIELDS
        or set(native_route) != _NATIVE_CHILD_ROUTE_FIELDS
        or set(receipt) != _NATIVE_CHILD_DELIVERY_RECEIPT_FIELDS
    ):
        return ("host-authored Codex child delivery proof had an invalid contract",)
    if (
        proof.get("schema") != _HOST_CHILD_DELIVERY_SCHEMA
        or proof.get("verified_delivery") is not True
        or proof.get("host") != "codex"
        or proof.get("pre_speech") is not True
        or receipt.get("verified_delivery") is not True
        or receipt.get("host") != "codex"
    ):
        return ("host-authored Codex child delivery proof was not verified",)

    if not _native_child_route_projection_is_valid(native_route):
        return ("the inference-owned Codex child route was invalid",)

    parent_session_id = _bounded_identity(
        proof.get("parent_session_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS
    )
    child_id = _bounded_identity(proof.get("child_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
    parent_trace_id = _bounded_identity(
        proof.get("parent_trace_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS
    )
    launch_id = _bounded_identity(proof.get("launch_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
    decision_id = _bounded_identity(
        proof.get("decision_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS
    )
    nonce = _bounded_identity(proof.get("nonce"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
    artifact_digest = _sha256_identity(proof.get("artifact_digest"))
    if (
        parent_session_id is None
        or parent_trace_id is None
        or child_id is None
        or parent_session_id != str(spawn.get("sender_thread_id") or "")
        or parent_session_id != evidence.get("session_id")
        or parent_session_id != parent_route.get("session_id")
        or parent_session_id != native_route.get("session_id")
        or parent_session_id != native_route.get("parent_session_id")
        or parent_trace_id != evidence.get("trace_id")
        or parent_trace_id != parent_route.get("trace_id")
        or parent_trace_id != native_route.get("trace_id")
        or parent_trace_id != native_route.get("parent_trace_id")
        or child_id != receiver_id
    ):
        return ("host-authored Codex child delivery did not match the exact parent and child",)
    if launch_id is None or decision_id is None or nonce is None or artifact_digest is None:
        return ("host-authored Codex child delivery identity bindings were invalid",)

    receipt_bindings = {
        "parent_session_id": parent_session_id,
        "parent_trace_id": parent_trace_id,
        "launch_id": launch_id,
        "child_id": child_id,
        "decision_id": decision_id,
        "nonce": nonce,
        "artifact_digest": artifact_digest,
    }
    if (
        any(receipt.get(field) != value for field, value in receipt_bindings.items())
        or receipt.get("launch_id") != native_route.get("launch_id")
        or receipt.get("decision_id") != native_route.get("decision_id")
        or receipt.get("nonce") != native_route.get("nonce")
        or _bounded_identity(receipt.get("verified_at"), maximum=128) is None
    ):
        return ("host-authored Codex child proof and receipt bindings did not match",)

    binding_kind = proof.get("binding_kind")
    binding_id = proof.get("binding_id")
    if (
        binding_kind not in {"child_id", "launch_id"}
        or binding_id != (child_id if binding_kind == "child_id" else launch_id)
        or receipt.get("binding_kind") != binding_kind
        or receipt.get("binding_id") != binding_id
        or native_route.get("binding_kind") != binding_kind
        or native_route.get("binding_id") != binding_id
    ):
        return ("host-authored Codex child delivery correlation bindings were invalid",)

    cards = proof.get("cards")
    normalized_cards = _normalized_host_child_cards(cards)
    if normalized_cards is None:
        return ("host-authored Codex child delivery did not contain a bounded card team",)

    if native_route.get("cards") != normalized_cards:
        return ("host-authored Codex child delivery did not match the exact ordered route",)

    parent_route_slugs = _ordered_route_slugs(parent_route)
    native_route_slugs = tuple(card["specialist_slug"] for card in normalized_cards)
    if parent_route_slugs is None or parent_route_slugs != native_route_slugs:
        return (
            "the inference-owned parent route did not match the exact ordered "
            "native child card team",
        )

    team_digest = hashlib.sha256(
        json.dumps(
            normalized_cards,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    issued_at = _utc_timestamp(proof.get("issued_at"))
    expires_at = _utc_timestamp(proof.get("expires_at"))
    candidate_digest = _sha256_identity(proof.get("candidate_digest"))
    runtime_digest = _sha256_identity(proof.get("runtime_digest"))
    route_bound_fields = {
        "host",
        "parent_session_id",
        "parent_trace_id",
        "launch_id",
        "decision_id",
        "provider_receipt_digest",
        "task_sha256",
        "team_digest",
        "candidate_digest",
        "runtime_digest",
        "install_id",
        "bundle_digest",
        "issued_at",
        "expires_at",
        "nonce",
        "binding_kind",
        "binding_id",
    }
    if (
        any(proof.get(field) != native_route.get(field) for field in route_bound_fields)
        or decision_id != receipt.get("decision_id")
        or _sha256_identity(proof.get("provider_receipt_digest")) is None
        or _sha256_identity(proof.get("task_sha256")) is None
        or proof.get("team_digest") != team_digest
        or candidate_digest is None
        or runtime_digest is None
        or candidate_digest != runtime_digest
        or _bounded_identity(proof.get("install_id"), maximum=_MAX_CODEX_HOST_IDENTITY_CHARS)
        is None
        or _sha256_identity(proof.get("bundle_digest")) is None
        or issued_at is None
        or expires_at is None
        or expires_at <= issued_at
    ):
        return ("host-authored Codex child delivery identity bindings were invalid",)
    return ()


def _codex_accepted_finalization(evidence: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """Return the sole first-pass authoritative accept without a correction."""

    raw_rows = evidence.get("finalizations")
    if not isinstance(raw_rows, list) or len(raw_rows) != 1:
        return None
    accepted = raw_rows[0]
    if not isinstance(accepted, Mapping):
        return None
    if accepted.get("action") != "accept" or accepted.get("terminal_status") != "completed":
        return None
    return accepted


def codex_activation_failures(
    *,
    result: Mapping[str, Any],
    evidence: Mapping[str, Any],
    response_hash: str,
    host_child_delivery: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    """Require one complete Codex activation graph, including the JSONL UUID alias."""

    failures: list[str] = []
    if evidence.get("schema") != "agency.canary-activation-evidence.v1":
        return ("exact Codex activation evidence contract was not available",)
    if evidence.get("proven") is not True:
        reason = str(evidence.get("reason") or "not_proven")
        return (f"exact Codex activation evidence was not proven ({reason})",)
    # Store rows prove the non-card activation graph. Card delivery itself is
    # established separately from a verified host-written child artifact below.
    cardinalities = evidence.get("cardinalities")
    expected_cardinalities = {
        "routes": 1,
        "native_child_routes": 1,
        "native_child_deliveries": 1,
        "runs": 1,
        "traces": 1,
        "worker_runs": 1,
    }
    if (
        not isinstance(cardinalities, Mapping)
        or any(cardinalities.get(field) != count for field, count in expected_cardinalities.items())
        or cardinalities.get("finalizations") != 1
    ):
        failures.append(
            "Codex canary required one complete first-pass card delivery without correction"
        )

    run = evidence.get("run") if isinstance(evidence.get("run"), Mapping) else None
    route = evidence.get("route") if isinstance(evidence.get("route"), Mapping) else None
    worker = _single_mapping(evidence, "worker_runs")
    finalization = _codex_accepted_finalization(evidence)
    if any(
        item is None
        for item in (
            run,
            route,
            worker,
            finalization,
        )
    ):
        failures.append("Codex canary evidence graph was incomplete")
        return tuple(failures)

    selected = _ordered_route_slugs(route)
    if selected != ("code-reviewer",) or route.get("query_hash") != evidence.get("query_hash"):
        failures.append("the sole routed canary unit was not the expected code-reviewer")

    spawn, receiver_id, collaboration_failures = _codex_collaboration_chain(result)
    failures.extend(collaboration_failures)
    if spawn is None or not receiver_id:
        return tuple(failures)
    failures.extend(
        _codex_host_child_delivery_failures(
            evidence=evidence,
            host_child_delivery=host_child_delivery,
            parent_route=route,
            spawn=spawn,
            receiver_id=receiver_id,
        )
    )
    # The JSONL assignment envelope, the native task label and the execution
    # dispatch receipt all described a planned unit. There is no plan to name,
    # so what the transcript has to show is simply that Codex spawned one child
    # and that child ran -- which _codex_collaboration_chain above established.
    failures.extend(
        _codex_receipt_link_failures(
            evidence=evidence,
            run=run,
            worker=worker,
            finalization=finalization,
            receiver_id=receiver_id,
            response_hash=response_hash,
        )
    )
    return tuple(dict.fromkeys(failures))


def _codex_product_child_tool_evidence_valid(value: object) -> bool:
    """Validate one fixed content-free child tool projection."""

    try:
        normalize_codex_child_tool_evidence(value)
    except ValueError:
        return False
    return True


def _merge_codex_product_child_tool_evidence(
    aggregate: dict[str, int],
    observed: Mapping[str, int],
) -> None:
    """Add one validated child projection to the product aggregate."""

    for field, value in observed.items():
        aggregate[field] += value


def _codex_product_child_tool_aggregate_matches(
    collaboration: Mapping[str, Any],
    aggregate: Mapping[str, int],
) -> bool:
    """Compare fixed reported tool counts with the sum of exact child rows."""

    return all(collaboration.get(field) == value for field, value in aggregate.items())


def profile_is_proven(
    host: str,
    result_scope: str,
    isolated_plugin: dict[str, Any] | None,
    *,
    plugin_invoked: bool,
) -> bool:
    if result_scope == "current-profile":
        return True
    if result_scope != "isolated-profile" or isolated_plugin is None:
        return False
    if host == "codex":
        return isolated_plugin.get("registered") is True and isolated_plugin.get("enabled") is True
    return bool(
        host == "claude" and isolated_plugin.get("load_requested") is True and plugin_invoked
    )


def render_isolated_plugin(
    host: str,
    isolated_plugin: dict[str, Any] | None,
    *,
    plugin_invoked: bool,
) -> dict[str, Any] | None:
    rendered = dict(isolated_plugin) if isolated_plugin is not None else None
    if host == "claude" and rendered is not None:
        rendered["loaded"] = True if plugin_invoked else None
        rendered["invoked"] = True if plugin_invoked else None
    return rendered


def proof_failures(
    *,
    process_ok: bool,
    profile_proven: bool,
    header_valid: bool,
    evidence: Mapping[str, Any],
    mode: str = "agency",
    response_nonempty: bool = True,
    activation_failures: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not process_ok:
        failures.append("host invocation did not complete successfully")
    if not profile_proven:
        failures.append("canary profile plugin registration and enablement were not proven")
    if not response_nonempty:
        failures.append("host invocation did not return a nonempty response")
    if mode == "native-only":
        if header_valid:
            failures.append("Agency response header was present in native-only mode")
        if any(int(count) for count in evidence["counts"].values()):
            failures.append("Agency runtime evidence was emitted in native-only mode")
    else:
        if not header_valid:
            failures.append("final response header was not proven")
        if activation_failures is not None:
            failures.extend(activation_failures)
        else:
            if not evidence["expected_specialist_selected"]:
                failures.append("expected canary specialist was not selected")
            elif not evidence["expected_specialist_loaded"]:
                failures.append("expected canary specialist activation was not proven")
            if not evidence["accepted_trace_ids"]:
                failures.append(
                    "correlated routing and an authoritative accepted terminal turn were not proven"
                )
            elif evidence["receipt_required"] and not evidence["receipt_proven"]:
                failures.append(
                    "the host exposes response telemetry but a correlated receipt was not proven"
                )
    return tuple(failures)


def evaluate_proof(
    host: str,
    *,
    result: dict[str, Any],
    evidence: dict[str, Any],
    default_profile_scope: str,
    mode: str = "agency",
    host_child_delivery: _VerifiedHostChildDelivery | None = None,
) -> CanaryProof:
    from agency_runtime.core.header.contract import parse_header, validate_header

    facade = _facade()
    response = facade._response_text(result.get("output"))
    response_nonempty = bool(response.strip())
    header_valid, header_missing = validate_header(response)
    process_ok = result.get("status") == "completed" and result.get("exit_code") == 0
    result_scope = str(result.get("profile_scope") or default_profile_scope)
    isolated_plugin = (
        result.get("isolated_plugin") if isinstance(result.get("isolated_plugin"), dict) else None
    )
    host_child_delivery_projection = _consume_verified_host_child_delivery(host_child_delivery)
    raw_collection_reason = result.get("host_child_collection_reason")
    collection_reason = (
        raw_collection_reason if raw_collection_reason in HOST_CHILD_COLLECTION_REASONS else None
    )
    plugin_invoked = bool(evidence.get("correlated_trace_ids"))
    activation_failures: tuple[str, ...] | None = None
    if mode == "agency" and host == "codex":
        activation_failures = codex_activation_failures(
            result=result,
            evidence=evidence,
            response_hash=hashlib.sha256(
                response.encode("utf-8", errors="surrogatepass")
            ).hexdigest(),
            host_child_delivery=host_child_delivery_projection,
        )
        plugin_invoked = evidence.get("proven") is True
    elif mode == "agency" and host == "claude":
        # The independently parsed, collector-sealed host artifact is Claude's
        # activation authority. A Store ``specialist_loaded`` row is only a
        # diagnostic projection and must not be required to make (or allowed to
        # replace) this proof.
        activation_failures = _claude_host_child_delivery_failures(
            proof=host_child_delivery_projection,
            evidence=evidence,
            collection_reason=collection_reason,
        )
    if mode == "native-only":
        profile_proven = bool(
            result_scope == "isolated-profile"
            and isolated_plugin is not None
            and (
                (
                    host == "codex"
                    and isolated_plugin.get("registered") is True
                    and isolated_plugin.get("enabled") is True
                )
                or (host == "claude" and isolated_plugin.get("load_requested") is True)
            )
        )
        evidence_passed = not any(int(count) for count in evidence["counts"].values())
        header_passed = not header_valid
    else:
        profile_proven = facade._profile_is_proven(
            host,
            result_scope,
            isolated_plugin,
            plugin_invoked=plugin_invoked,
        )
        evidence_passed = (
            not activation_failures
            if activation_failures is not None
            else bool(
                evidence["accepted_trace_ids"]
                and evidence["expected_specialist_selected"]
                and evidence["expected_specialist_loaded"]
                and (not evidence["receipt_required"] or evidence["receipt_proven"])
            )
        )
        header_passed = header_valid
    collaboration_projection = result.get("collaboration")
    invocation = {
        "backend": result.get("backend", host),
        "status": result.get("status"),
        "exit_code": result.get("exit_code"),
        "timed_out": result.get("status") == "timed_out",
        "stdout_truncated": bool(result.get("stdout_truncated")),
        "stderr_truncated": bool(result.get("stderr_truncated")),
        "header_valid": header_valid,
        "header_missing": header_missing,
        "profile_scope": result_scope,
        "isolated_plugin": facade._render_isolated_plugin(
            host,
            isolated_plugin,
            plugin_invoked=plugin_invoked,
        ),
        "collaboration": collaboration_projection,
    }
    if collection_reason is not None:
        invocation["host_child_collection_reason"] = collection_reason
    if host_child_delivery_projection is not None:
        invocation["host_child_delivery"] = host_child_delivery_projection
    if mode == "agency" and host == "codex":
        cardinalities = evidence.get("cardinalities")
        finalization_count = (
            cardinalities.get("finalizations") if isinstance(cardinalities, Mapping) else None
        )
        invocation["correction_count"] = (
            max(0, finalization_count - 1)
            if isinstance(finalization_count, int) and not isinstance(finalization_count, bool)
            else None
        )
        invocation["header"] = parse_header(response) if header_valid else {}
    if isinstance(result.get("hook_trust"), Mapping):
        from agency_runtime.core.codex_hook_trust import (
            sanitize_codex_hook_trust_report,
        )

        invocation["hook_trust"] = sanitize_codex_hook_trust_report(result["hook_trust"])
    if type(result.get("model_invocation_attempted")) is bool:
        invocation["model_invocation_attempted"] = result["model_invocation_attempted"]
    from agency_runtime.core.canary_backends import (
        sanitize_codex_collaboration_diagnostic,
    )

    if collaboration_diagnostic := sanitize_codex_collaboration_diagnostic(
        result.get("collaboration_diagnostic")
    ):
        invocation["collaboration_diagnostic"] = collaboration_diagnostic
    from agency_runtime.core.codex_activation_verification import (
        sanitize_codex_hook_event_diagnostics,
    )

    if hook_events := sanitize_codex_hook_event_diagnostics(result.get("hook_events")):
        invocation["hook_events"] = hook_events
    hook_diagnostic = result.get("hook_diagnostic") or evidence.get("hook_diagnostic")
    from agency_runtime.core.codex_activation_verification import (
        CODEX_RECONCILIATION_DIAGNOSTIC_REASONS,
    )

    if hook_diagnostic in CODEX_RECONCILIATION_DIAGNOSTIC_REASONS:
        invocation["hook_diagnostic"] = hook_diagnostic
    failure_reason = result.get("failure_reason")
    if isinstance(failure_reason, str) and failure_reason in CANARY_INVOCATION_FAILURE_REASONS:
        invocation["failure_reason"] = failure_reason
    failures = list(
        facade._proof_failures(
            process_ok=process_ok,
            profile_proven=profile_proven,
            header_valid=header_valid,
            evidence=evidence,
            mode=mode,
            response_nonempty=response_nonempty,
            activation_failures=activation_failures,
        )
    )
    if failure_reason == "codex_hook_trust_not_ready":
        failures.insert(
            0,
            "Codex does not report the settled Agency hook inventory as enabled and trusted",
        )
    return CanaryProof(
        invocation=invocation,
        result_scope=result_scope,
        passed=bool(
            process_ok
            and response_nonempty
            and header_passed
            and evidence_passed
            and profile_proven
        ),
        failures=tuple(dict.fromkeys(failures)),
    )


def attestation_payload(
    host: str,
    *,
    proof: CanaryProof,
    evidence: Mapping[str, Any],
    assessment: ReadinessAssessment,
    passed_at: str,
) -> dict[str, Any]:
    trace_id = str(evidence.get("trace_id") or evidence["accepted_trace_ids"][0])
    attestation_identity = {
        "host": host,
        "profile_scope": proof.result_scope,
        "platform_system": assessment.platform["system"],
        "platform_release": assessment.platform["release"],
        "platform_machine": assessment.platform["machine"],
        "host_version": str(assessment.native["host_version"]),
        "plugin_version": _facade().PLUGIN_VERSION,
        "install_id": str(assessment.native["install_id"]),
        "bundle_digest": str(assessment.native["bundle_digest"]),
        "trace_id": trace_id,
        "passed_at": passed_at,
    }
    proof_material = {
        "contract": CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        "attestation": attestation_identity,
        "invocation": proof.invocation,
        "evidence": evidence,
    }
    proof_digest = hashlib.sha256(
        json.dumps(
            proof_material,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        **attestation_identity,
        "proof_contract": CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
        "proof_digest": proof_digest,
    }


def attestation_identity_is_current(
    before: ReadinessAssessment,
    after: ReadinessAssessment,
) -> bool:
    """Require stable attested lineage across the complete live invocation."""
    if (
        after.unmet
        or before.profile_scope != after.profile_scope
        or before.platform != after.platform
    ):
        return False
    fields = ("host_version", "install_id", "bundle_digest")
    return all(
        str(before.native.get(field) or "") == str(after.native.get(field) or "")
        for field in fields
    )


def persist_attestation(
    store: Any,
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        attestation = store.record_host_canary_attestation(**payload)
    except Exception:
        return None, "successful canary evidence could not be durably attested"
    return attestation, None


__all__ = [
    "CanaryProof",
    "InvocationOutcome",
    "LivePreparation",
    "ReadinessAssessment",
    "assess_readiness",
    "attestation_identity_is_current",
    "attestation_payload",
    "evaluate_proof",
    "evidence_delta",
    "evidence_summary",
    "ids",
    "invoke_and_collect_evidence",
    "persist_attestation",
    "prepare_live_invocation",
    "profile_is_proven",
    "proof_failures",
    "readiness_report",
    "render_isolated_plugin",
    "response_text",
]
