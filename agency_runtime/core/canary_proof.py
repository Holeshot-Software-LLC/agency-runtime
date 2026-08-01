"""Readiness, evidence correlation, and durable proof for host canaries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.installer_contracts import (
    CODEX_ACTIVATION_CANARY_PROOF_CONTRACT,
)
from agency_runtime.core.private_paths import private_temporary_directory

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
        unmet.append("host has no proven read-only, no-tools noninteractive canary mode")
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
    invocation_error: str | None = None
    try:
        with private_temporary_directory(prefix="canary") as workdir:
            result = preparation.backend.execute(
                task=prompt,
                workdir=str(workdir),
                check=False,
            )
            if not isinstance(result, dict):
                raise RuntimeError("canary backend returned an invalid result")
    except Exception:
        invocation_error = "safe host invocation failed before evidence could be evaluated"
    facade = _facade()
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
        return InvocationOutcome(result=result, evidence=exact, error=invocation_error)
    try:
        after = preparation.store.recent_runtime_activity(limit=200)
    except Exception:
        return InvocationOutcome(
            result=result,
            evidence=None,
            error="runtime evidence could not be read after host invocation",
        )
    return InvocationOutcome(
        result=result,
        evidence=facade._evidence_summary(
            facade._evidence_delta(preparation.before, after),
            host,
            expected_query_hash=expected_query_hash,
        ),
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
    plan: Mapping[str, Any],
    delegation: Mapping[str, Any],
    grant: Mapping[str, Any],
    consumption: Mapping[str, Any],
    worker: Mapping[str, Any],
    specialist_load: Mapping[str, Any],
    finalization: Mapping[str, Any],
    receiver_id: str,
    consumed_identity: tuple[str, str],
    response_hash: str,
    accepted_specialist_load_receipt_ids: frozenset[str] | None = None,
) -> tuple[str, ...]:
    """Validate reciprocal Store links after the JSONL receiver alias is known."""

    failures: list[str] = []
    session_id = str(evidence.get("session_id") or "")
    trace_id = str(evidence.get("trace_id") or "")
    work_unit_id = str(plan.get("work_unit_id") or "")
    specialist_slug = str(plan.get("recommended_agent") or "")
    specialist_version = str(grant.get("specialist_version") or "")
    specialist_prompt_hash = str(grant.get("specialist_prompt_hash") or "")
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
    shared_identity = {
        "session_id": session_id,
        "trace_id": trace_id,
        "work_unit_id": work_unit_id,
        "specialist_slug": specialist_slug,
        "specialist_version": specialist_version,
        "specialist_prompt_hash": specialist_prompt_hash,
    }
    if any(grant.get(field) != expected for field, expected in shared_identity.items()):
        failures.append("activation grant did not match the exact planned specialist unit")
    if any(consumption.get(field) != expected for field, expected in shared_identity.items()):
        failures.append("activation consumption did not match the exact planned specialist unit")
    if (
        not grant.get("consumed_at")
        or consumption.get("grant_id") != grant.get("grant_id")
        or consumption.get("legacy_activation_receipt_id") != grant.get("id")
    ):
        failures.append("the one-use activation grant was not consumed exactly once")
    load_receipt_id = str(specialist_load.get("activation_receipt_id") or "")
    load_receipt_matches = (
        load_receipt_id == str(grant.get("id") or "")
        if accepted_specialist_load_receipt_ids is None
        else load_receipt_id in accepted_specialist_load_receipt_ids
    )
    if specialist_load.get("agent_slug") != specialist_slug or not load_receipt_matches:
        failures.append("specialist load was not backed by the consumed activation grant")
    if (
        delegation.get("host") != "codex"
        or delegation.get("backend") != "spawn_agent"
        or delegation.get("work_unit_id") != work_unit_id
        or delegation.get("recommended_agent") != specialist_slug
        or delegation.get("status") not in {"delegated", "completed"}
        or delegation.get("activation_receipt_id") != grant.get("id")
        or delegation.get("retrieved_specialist_slug") != specialist_slug
        or delegation.get("retrieved_specialist_version") != specialist_version
        or delegation.get("retrieved_specialist_prompt_hash") != specialist_prompt_hash
        or (
            delegation.get("executed_worker_id"),
            delegation.get("native_run_id"),
        )
        != consumed_identity
    ):
        failures.append("delegation was not reciprocally linked to the activation consumption")
    if worker.get("delegation_event_id") not in {None, "", delegation.get("id")}:
        failures.append("Codex lifecycle was attached to a different delegation")
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
) -> tuple[str, ...]:
    """Require one complete Codex activation graph, including the JSONL UUID alias."""

    failures: list[str] = []
    if evidence.get("schema") != "agency.canary-activation-evidence.v1":
        return ("exact Codex activation evidence contract was not available",)
    if evidence.get("proven") is not True:
        reason = str(evidence.get("reason") or "not_proven")
        return (f"exact Codex activation evidence was not proven ({reason})",)
    cardinalities = evidence.get("cardinalities")
    expected_cardinalities = {
        "routes": 1,
        "runs": 1,
        "traces": 1,
        "unit_agent_plan": 1,
        "delegations": 1,
        "activation_grants": 1,
        "activation_consumptions": 1,
        "worker_runs": 1,
        "specialist_loads": 1,
    }
    if (
        not isinstance(cardinalities, Mapping)
        or any(cardinalities.get(field) != count for field, count in expected_cardinalities.items())
        or cardinalities.get("finalizations") != 1
    ):
        failures.append(
            "Codex canary required one complete first-pass activation chain without correction"
        )

    run = evidence.get("run") if isinstance(evidence.get("run"), Mapping) else None
    route = evidence.get("route") if isinstance(evidence.get("route"), Mapping) else None
    plan = _single_mapping(evidence, "unit_agent_plan")
    delegation = _single_mapping(evidence, "delegations")
    grant = _single_mapping(evidence, "activation_grants")
    consumption = _single_mapping(evidence, "activation_consumptions")
    worker = _single_mapping(evidence, "worker_runs")
    specialist_load = _single_mapping(evidence, "specialist_loads")
    finalization = _codex_accepted_finalization(evidence)
    if any(
        item is None
        for item in (
            run,
            route,
            plan,
            delegation,
            grant,
            consumption,
            worker,
            specialist_load,
            finalization,
        )
    ):
        failures.append("Codex canary evidence graph was incomplete")
        return tuple(failures)

    session_id = str(evidence.get("session_id") or "")
    trace_id = str(evidence.get("trace_id") or "")
    work_unit_id = str(plan.get("work_unit_id") or "")
    specialist_slug = str(plan.get("recommended_agent") or "")
    specialist_version = str(grant.get("specialist_version") or "")
    specialist_prompt_hash = str(grant.get("specialist_prompt_hash") or "")
    goal_hash = str(plan.get("goal_hash") or "")
    selected = {
        str(value)
        for field in ("selected_ids", "companion_ids")
        for value in (route.get(field) if isinstance(route.get(field), list) else [])
    }
    if (
        specialist_slug != "code-reviewer"
        or selected != {"code-reviewer"}
        or route.get("query_hash") != evidence.get("query_hash")
    ):
        failures.append("the sole routed canary unit was not the expected code-reviewer")

    spawn, receiver_id, collaboration_failures = _codex_collaboration_chain(result)
    failures.extend(collaboration_failures)
    if spawn is None or not receiver_id:
        return tuple(failures)
    delivery = spawn.get("prompt_delivery")
    if not isinstance(delivery, Mapping) or any(
        delivery.get(field) != expected
        for field, expected in {
            "host": "codex",
            "parent_session_id": session_id,
            "parent_trace_id": trace_id,
            "work_unit_id": work_unit_id,
            "specialist_slug": specialist_slug,
            "specialist_version": specialist_version,
            "specialist_prompt_hash": specialist_prompt_hash,
            "goal_hash": goal_hash,
        }.items()
    ):
        failures.append("Codex JSONL did not carry the exact hook-injected child assignment")
    elif grant.get("grant_origin") != "native_hook" or grant.get("tool_use_id") != delivery.get(
        "tool_use_id"
    ):
        failures.append(
            "activation grant was not issued by the native hook for the exact Codex tool call"
        )

    expected_task_name = ""
    if work_unit_id:
        from agency_runtime.core.delegation.native_labels import (
            codex_task_name_for_work_unit,
        )

        expected_task_name = codex_task_name_for_work_unit(work_unit_id)
    if spawn.get("native_task_name") not in {None, expected_task_name}:
        failures.append("Codex spawned a different native task than the exact planned unit")
    execution_delivery = spawn.get("execution_delivery")
    if not isinstance(execution_delivery, Mapping) or any(
        execution_delivery.get(field) != expected
        for field, expected in {
            "work_unit_id": work_unit_id,
            "native_task_name": expected_task_name,
            "goal_hash": goal_hash,
        }.items()
    ):
        failures.append("Codex did not execute the exact activated canary work unit")
    if not worker.get("execution_dispatched_at") or worker.get(
        "execution_tool_use_id"
    ) != spawn.get("followup_tool_use_id"):
        failures.append("Codex execution turn lacked its one-use Store dispatch receipt")
    synthetic_identity = (
        f"task:{expected_task_name}",
        f"codex-task:{expected_task_name}",
    )
    receiver_identity = (receiver_id, f"codex-agent:{receiver_id}")
    consumed_identity = (
        str(consumption.get("worker_id") or ""),
        str(consumption.get("native_run_id") or ""),
    )
    if consumed_identity not in {synthetic_identity, receiver_identity}:
        failures.append("activation consumption did not match the Codex child alias contract")
    failures.extend(
        _codex_receipt_link_failures(
            evidence=evidence,
            run=run,
            plan=plan,
            delegation=delegation,
            grant=grant,
            consumption=consumption,
            worker=worker,
            specialist_load=specialist_load,
            finalization=finalization,
            receiver_id=receiver_id,
            consumed_identity=consumed_identity,
            response_hash=response_hash,
        )
    )
    return tuple(dict.fromkeys(failures))


def _codex_product_collaboration_spawns(
    result: Mapping[str, Any],
    *,
    expected_parent_thread_id: str,
) -> tuple[dict[str, tuple[Mapping[str, Any], str]], tuple[str, ...]]:
    """Resolve exact completed product children by persisted work-unit identity."""

    collaboration = result.get("collaboration")
    if (
        not isinstance(collaboration, Mapping)
        or collaboration.get("schema") != "agency.codex-product-collaboration.v1"
        or collaboration.get("evidence_source") != "persisted_rollout"
    ):
        return {}, ("Codex product collaboration evidence was not available",)
    counts = {
        name: collaboration.get(name)
        for name in (
            "spawn_count",
            "followup_count",
            "wait_count",
            "completed_wait_count",
            "timed_out_wait_count",
            "completed_child_count",
            "failed_child_count",
            "child_tool_call_count",
            "parent_agent_message_count",
            "unexpected_item_count",
        )
    }
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0
        for value in counts.values()
    ):
        return {}, ("Codex product collaboration counts were invalid",)
    spawn_count = counts["spawn_count"]
    if counts["unexpected_item_count"] != 0:
        return {}, ("Codex product parent performed a non-collaboration tool call",)
    if (
        not 1 <= spawn_count <= 16
        or counts["followup_count"] != spawn_count
        or counts["wait_count"] != spawn_count * 2
        or counts["completed_wait_count"] != counts["wait_count"]
        or counts["timed_out_wait_count"] != 0
        or counts["completed_child_count"] != spawn_count
        or counts["failed_child_count"] != 0
    ):
        return {}, ("Codex product collaboration topology was incomplete",)
    raw_calls = collaboration.get("calls")
    if not isinstance(raw_calls, list) or len(raw_calls) != spawn_count:
        return {}, ("Codex product spawn evidence did not match its child count",)
    by_unit: dict[str, tuple[Mapping[str, Any], str]] = {}
    receivers: set[str] = set()
    parent_thread_id = ""
    for row in raw_calls:
        if (
            not isinstance(row, Mapping)
            or row.get("event_type") != "rollout_call_completed"
            or row.get("tool") != "spawn_agent"
            or row.get("status") != "completed"
            or row.get("child_status") != "completed"
            or row.get("activation_completion_count") != 1
            or row.get("execution_completion_count") != 1
            or row.get("evidence_source") != "persisted_rollout"
        ):
            return {}, ("Codex product spawn evidence was malformed",)
        sender = str(row.get("sender_thread_id") or "")
        if sender != expected_parent_thread_id:
            return {}, ("Codex product child did not belong to the exact parent session",)
        if parent_thread_id and sender != parent_thread_id:
            return {}, ("Codex product spawns did not share one parent thread",)
        parent_thread_id = sender
        receiver_values = row.get("receiver_thread_ids")
        if not isinstance(receiver_values, list) or len(receiver_values) != 1:
            return {}, ("Codex product spawn did not identify one child",)
        receiver = str(receiver_values[0] or "")
        delivery = row.get("prompt_delivery")
        if not receiver or receiver in receivers or not isinstance(delivery, Mapping):
            return {}, ("Codex product child identity was missing or duplicated",)
        work_unit_id = str(delivery.get("work_unit_id") or "")
        if not work_unit_id or work_unit_id in by_unit:
            return {}, ("Codex product work-unit delivery was missing or duplicated",)
        receivers.add(receiver)
        by_unit[work_unit_id] = (row, receiver)
    return by_unit, ()


def _codex_product_collaboration_projection(
    result: Mapping[str, Any],
    *,
    expected_parent_thread_id: str,
) -> dict[str, Any] | None:
    """Return only the fixed content-free product collaboration report shape."""

    collaboration = result.get("collaboration")
    spawns, failures = _codex_product_collaboration_spawns(
        result,
        expected_parent_thread_id=expected_parent_thread_id,
    )
    if failures or not isinstance(collaboration, Mapping):
        return None
    from agency_runtime.core.canary_backends import (
        CODEX_STDOUT_HOST_NOTICE_COUNT_MAX,
        CODEX_STDOUT_HOST_NOTICE_TYPES,
    )

    aggregate_fields = (
        "spawn_count",
        "followup_count",
        "wait_count",
        "completed_wait_count",
        "timed_out_wait_count",
        "completed_child_count",
        "failed_child_count",
        "child_tool_call_count",
        "parent_agent_message_count",
        "unexpected_item_count",
        "host_notice_count",
    )
    if any(
        not isinstance(collaboration.get(field), int)
        or isinstance(collaboration.get(field), bool)
        or collaboration.get(field, -1) < 0
        for field in aggregate_fields
    ):
        return None
    host_notice_types = collaboration.get("host_notice_types")
    host_notice_count = collaboration.get("host_notice_count")
    if (
        not isinstance(host_notice_types, list)
        or any(type(item) is not str for item in host_notice_types)
        or host_notice_types != sorted(set(host_notice_types))
        or any(item not in CODEX_STDOUT_HOST_NOTICE_TYPES for item in host_notice_types)
        or host_notice_count > CODEX_STDOUT_HOST_NOTICE_COUNT_MAX
        or host_notice_count < len(host_notice_types)
        or bool(host_notice_count) != bool(host_notice_types)
    ):
        return None
    calls = [
        {
            "id": row.get("id"),
            "event_type": row.get("event_type"),
            "tool": row.get("tool"),
            "sender_thread_id": row.get("sender_thread_id"),
            "receiver_thread_ids": list(row.get("receiver_thread_ids", [])),
            "status": row.get("status"),
            "prompt_delivery": {
                field: delivery.get(field)
                for field in (
                    "host",
                    "parent_session_id",
                    "parent_trace_id",
                    "tool_use_id",
                    "work_unit_id",
                    "specialist_slug",
                    "specialist_version",
                    "specialist_prompt_hash",
                    "goal_hash",
                )
            },
            "execution_delivery": {
                field: execution.get(field)
                for field in ("work_unit_id", "native_task_name", "goal_hash")
            },
            "followup_id": row.get("followup_id"),
            "followup_tool_use_id": row.get("followup_tool_use_id"),
            "native_task_name": row.get("native_task_name"),
            "child_status": row.get("child_status"),
            "activation_completion_count": row.get("activation_completion_count"),
            "execution_completion_count": row.get("execution_completion_count"),
            "evidence_source": row.get("evidence_source"),
        }
        for row, _receiver in sorted(
            spawns.values(),
            key=lambda item: str(item[0].get("id") or ""),
        )
        for delivery in (
            row.get("prompt_delivery") if isinstance(row.get("prompt_delivery"), Mapping) else {},
        )
        for execution in (
            row.get("execution_delivery")
            if isinstance(row.get("execution_delivery"), Mapping)
            else {},
        )
    ]
    return {
        "schema": "agency.codex-product-collaboration.v1",
        "calls": calls,
        **{field: collaboration.get(field) for field in aggregate_fields},
        "host_notice_types": list(host_notice_types),
        "evidence_source": "persisted_rollout",
    }


def _product_rows_by_unit(
    evidence: Mapping[str, Any],
    field: str,
    *,
    expected_count: int,
) -> dict[str, Mapping[str, Any]] | None:
    values = evidence.get(field)
    if not isinstance(values, list) or len(values) != expected_count:
        return None
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            return None
        work_unit_id = str(value.get("work_unit_id") or "")
        if not work_unit_id or work_unit_id in result:
            return None
        result[work_unit_id] = value
    return result


def _codex_product_loads_by_specialist(
    values: object,
    grants: Mapping[str, Mapping[str, Any]],
) -> tuple[
    dict[str, tuple[Mapping[str, Any], frozenset[str]]],
    tuple[str, ...],
]:
    if not isinstance(values, list):
        return {}, ("Codex product specialist load evidence was unavailable",)
    grants_by_receipt: dict[str, Mapping[str, Any]] = {}
    receipts_by_identity: dict[tuple[str, str, str], set[str]] = {}
    failures: list[str] = []
    for grant in grants.values():
        receipt_id = str(grant.get("id") or "")
        identity = (
            str(grant.get("specialist_slug") or ""),
            str(grant.get("specialist_version") or ""),
            str(grant.get("specialist_prompt_hash") or ""),
        )
        if not receipt_id or receipt_id in grants_by_receipt or not all(identity):
            failures.append("Codex product activation grant identities were missing or duplicated")
            continue
        grants_by_receipt[receipt_id] = grant
        receipts_by_identity.setdefault(identity, set()).add(receipt_id)

    result: dict[str, tuple[Mapping[str, Any], frozenset[str]]] = {}
    load_receipt_ids: set[str] = set()
    for value in values:
        if not isinstance(value, Mapping):
            failures.append("Codex product specialist load evidence was malformed")
            continue
        specialist_slug = str(value.get("agent_slug") or "")
        receipt_id = str(value.get("activation_receipt_id") or "")
        anchor = grants_by_receipt.get(receipt_id)
        if (
            not specialist_slug
            or specialist_slug in result
            or not receipt_id
            or receipt_id in load_receipt_ids
            or anchor is None
            or str(anchor.get("specialist_slug") or "") != specialist_slug
        ):
            failures.append("Codex product specialist loads were missing or duplicated")
            continue
        identity = (
            specialist_slug,
            str(anchor.get("specialist_version") or ""),
            str(anchor.get("specialist_prompt_hash") or ""),
        )
        eligible_receipts = frozenset(receipts_by_identity.get(identity, set()))
        if not eligible_receipts:
            failures.append("Codex product specialist load identity was not selected")
            continue
        load_receipt_ids.add(receipt_id)
        result[specialist_slug] = (value, eligible_receipts)
    return result, tuple(dict.fromkeys(failures))


def _codex_product_unit_failures(
    *,
    evidence: Mapping[str, Any],
    plan: Mapping[str, Any],
    delegation: Mapping[str, Any],
    grant: Mapping[str, Any],
    consumption: Mapping[str, Any],
    worker: Mapping[str, Any],
    spawn: Mapping[str, Any],
    receiver_id: str,
    specialist_load: Mapping[str, Any] | None,
    accepted_specialist_load_receipt_ids: frozenset[str],
    run: Mapping[str, Any],
    finalization: Mapping[str, Any],
    response_hash: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    work_unit_id = str(plan.get("work_unit_id") or "")
    specialist_slug = str(plan.get("recommended_agent") or "")
    specialist_version = str(grant.get("specialist_version") or "")
    specialist_prompt_hash = str(grant.get("specialist_prompt_hash") or "")
    delivery = spawn.get("prompt_delivery")
    expected_delivery = {
        "host": "codex",
        "parent_session_id": str(evidence.get("session_id") or ""),
        "parent_trace_id": str(evidence.get("trace_id") or ""),
        "work_unit_id": work_unit_id,
        "specialist_slug": specialist_slug,
        "specialist_version": specialist_version,
        "specialist_prompt_hash": specialist_prompt_hash,
        "goal_hash": str(plan.get("goal_hash") or ""),
    }
    if not isinstance(delivery, Mapping) or any(
        delivery.get(field) != expected for field, expected in expected_delivery.items()
    ):
        return (f"Codex product unit {work_unit_id} had mismatched child delivery",)
    from agency_runtime.core.delegation.native_labels import (
        codex_task_name_for_work_unit,
    )

    expected_task_name = codex_task_name_for_work_unit(work_unit_id)
    if spawn.get("native_task_name") != expected_task_name:
        failures.append(f"Codex product unit {work_unit_id} used a different native task")
    execution_delivery = spawn.get("execution_delivery")
    if not isinstance(execution_delivery, Mapping) or any(
        execution_delivery.get(field) != expected
        for field, expected in {
            "work_unit_id": work_unit_id,
            "native_task_name": expected_task_name,
            "goal_hash": str(plan.get("goal_hash") or ""),
        }.items()
    ):
        failures.append(f"Codex product unit {work_unit_id} lacked its exact execution turn")
    if not worker.get("execution_dispatched_at") or worker.get(
        "execution_tool_use_id"
    ) != spawn.get("followup_tool_use_id"):
        failures.append(
            f"Codex product unit {work_unit_id} lacked its one-use execution dispatch receipt"
        )
    if grant.get("grant_origin") != "native_hook" or grant.get("tool_use_id") != delivery.get(
        "tool_use_id"
    ):
        failures.append(f"Codex product unit {work_unit_id} lacked its native-hook grant")
    consumed_identity = (
        str(consumption.get("worker_id") or ""),
        str(consumption.get("native_run_id") or ""),
    )
    allowed_identities = {
        (f"task:{expected_task_name}", f"codex-task:{expected_task_name}"),
        (receiver_id, f"codex-agent:{receiver_id}"),
    }
    if consumed_identity not in allowed_identities:
        failures.append(f"Codex product unit {work_unit_id} had mismatched child identity")
    if specialist_load is None:
        failures.append(f"Codex product unit {work_unit_id} lacked its specialist load")
        return tuple(failures)
    failures.extend(
        _codex_receipt_link_failures(
            evidence=evidence,
            run=run,
            plan=plan,
            delegation=delegation,
            grant=grant,
            consumption=consumption,
            worker=worker,
            specialist_load=specialist_load,
            finalization=finalization,
            receiver_id=receiver_id,
            consumed_identity=consumed_identity,
            response_hash=response_hash,
            accepted_specialist_load_receipt_ids=accepted_specialist_load_receipt_ids,
        )
    )
    if delegation.get("status") != "completed" or not delegation.get("completed_at"):
        failures.append(f"Codex product unit {work_unit_id} did not complete delegation")
    return tuple(failures)


def codex_product_activation_failures(
    *,
    result: Mapping[str, Any],
    evidence: Mapping[str, Any],
    response_hash: str,
) -> tuple[str, ...]:
    """Require every exact product work unit to complete through one native child."""

    if evidence.get("schema") != "agency.canary-activation-evidence.v1":
        return ("exact Codex product activation evidence contract was not available",)
    if evidence.get("proven") is not True:
        reason = str(evidence.get("reason") or "not_proven")
        return (f"exact Codex product activation evidence was not proven ({reason})",)
    raw_plans = evidence.get("unit_agent_plan")
    if (
        not isinstance(raw_plans, list)
        or not 1 <= len(raw_plans) <= 16
        or any(not isinstance(item, Mapping) for item in raw_plans)
    ):
        return ("Codex product unit-agent plan was missing or invalid",)
    plans: dict[str, Mapping[str, Any]] = {}
    for raw in raw_plans:
        work_unit_id = str(raw.get("work_unit_id") or "")
        if not work_unit_id or work_unit_id in plans:
            return ("Codex product unit-agent plan identities were missing or duplicated",)
        plans[work_unit_id] = raw
    unit_count = len(plans)
    planned_slugs = {str(plan.get("recommended_agent") or "") for plan in plans.values()}
    specialist_count = len(planned_slugs)
    cardinalities = evidence.get("cardinalities")
    expected_cardinalities = {
        "routes": 1,
        "runs": 1,
        "traces": 1,
        "unit_agent_plan": unit_count,
        "delegations": unit_count,
        "activation_grants": unit_count,
        "activation_consumptions": unit_count,
        "worker_runs": unit_count,
        "specialist_loads": specialist_count,
        "finalizations": 1,
        "preflight_failures": 0,
    }
    failures: list[str] = []
    if not isinstance(cardinalities, Mapping) or any(
        cardinalities.get(field) != count for field, count in expected_cardinalities.items()
    ):
        failures.append("Codex product did not prove one complete activation per planned unit")
    run = evidence.get("run") if isinstance(evidence.get("run"), Mapping) else None
    route = evidence.get("route") if isinstance(evidence.get("route"), Mapping) else None
    finalization = _codex_accepted_finalization(evidence)
    delegations = _product_rows_by_unit(evidence, "delegations", expected_count=unit_count)
    grants = _product_rows_by_unit(evidence, "activation_grants", expected_count=unit_count)
    consumptions = _product_rows_by_unit(
        evidence,
        "activation_consumptions",
        expected_count=unit_count,
    )
    workers = _product_rows_by_unit(evidence, "worker_runs", expected_count=unit_count)
    collaboration, collaboration_failures = _codex_product_collaboration_spawns(
        result,
        expected_parent_thread_id=str(evidence.get("session_id") or ""),
    )
    failures.extend(collaboration_failures)
    if any(
        item is None
        for item in (run, route, finalization, delegations, grants, consumptions, workers)
    ):
        failures.append("Codex product evidence graph was incomplete")
        return tuple(dict.fromkeys(failures))
    specialist_loads, load_failures = _codex_product_loads_by_specialist(
        evidence.get("specialist_loads"),
        grants,
    )
    failures.extend(load_failures)
    if len(collaboration) != unit_count:
        failures.append("Codex product native child count did not match its planned units")
    selected = {
        str(value)
        for field in ("selected_ids", "companion_ids")
        for value in (route.get(field) if isinstance(route.get(field), list) else [])
    }
    if (
        route.get("status") != "accepted"
        or route.get("query_hash") != evidence.get("query_hash")
        or not planned_slugs
        or "" in planned_slugs
        or not planned_slugs.issubset(selected)
    ):
        failures.append("Codex product route did not contain every planned specialist")
    for work_unit_id, plan in plans.items():
        delegation = delegations.get(work_unit_id)
        grant = grants.get(work_unit_id)
        consumption = consumptions.get(work_unit_id)
        worker = workers.get(work_unit_id)
        spawn_entry = collaboration.get(work_unit_id)
        if any(item is None for item in (delegation, grant, consumption, worker, spawn_entry)):
            failures.append(f"Codex product unit {work_unit_id} lacked exact execution evidence")
            continue
        spawn, receiver_id = spawn_entry
        specialist_load_entry = specialist_loads.get(str(plan.get("recommended_agent") or ""))
        specialist_load = specialist_load_entry[0] if specialist_load_entry is not None else None
        accepted_load_receipts = (
            specialist_load_entry[1] if specialist_load_entry is not None else frozenset()
        )
        if str(grant.get("id") or "") not in accepted_load_receipts:
            accepted_load_receipts = frozenset()
        failures.extend(
            _codex_product_unit_failures(
                evidence=evidence,
                plan=plan,
                delegation=delegation,
                grant=grant,
                consumption=consumption,
                worker=worker,
                spawn=spawn,
                receiver_id=receiver_id,
                specialist_load=specialist_load,
                accepted_specialist_load_receipt_ids=accepted_load_receipts,
                run=run,
                finalization=finalization,
                response_hash=response_hash,
            )
        )
    if len(specialist_loads) != specialist_count:
        failures.append("Codex product specialist load count did not match its planned specialists")
    return tuple(dict.fromkeys(failures))


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
    activation_contract: str = "canary",
) -> CanaryProof:
    from agency_runtime.core.header.contract import parse_header, validate_header

    facade = _facade()
    if activation_contract not in {"canary", "product"}:
        raise ValueError("unsupported Codex activation proof contract")
    response = facade._response_text(result.get("output"))
    response_nonempty = bool(response.strip())
    header_valid, header_missing = validate_header(response)
    process_ok = result.get("status") == "completed" and result.get("exit_code") == 0
    result_scope = str(result.get("profile_scope") or default_profile_scope)
    isolated_plugin = (
        result.get("isolated_plugin") if isinstance(result.get("isolated_plugin"), dict) else None
    )
    plugin_invoked = bool(evidence.get("correlated_trace_ids"))
    activation_failures: tuple[str, ...] | None = None
    if mode == "agency" and host == "codex":
        activation_validator = (
            codex_product_activation_failures
            if activation_contract == "product"
            else codex_activation_failures
        )
        activation_failures = activation_validator(
            result=result,
            evidence=evidence,
            response_hash=hashlib.sha256(
                response.encode("utf-8", errors="surrogatepass")
            ).hexdigest(),
        )
        plugin_invoked = evidence.get("proven") is True
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
    if activation_contract == "product":
        collaboration_projection = _codex_product_collaboration_projection(
            result,
            expected_parent_thread_id=str(evidence.get("session_id") or ""),
        )
    product_collaboration_proven = not (
        activation_contract == "product"
        and mode == "agency"
        and host == "codex"
        and collaboration_projection is None
    )
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
    if activation_contract == "product":
        invocation["activation_contract"] = "product"
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
    if not product_collaboration_proven:
        failures.append("Codex product collaboration projection was missing or invalid")
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
            and product_collaboration_proven
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
