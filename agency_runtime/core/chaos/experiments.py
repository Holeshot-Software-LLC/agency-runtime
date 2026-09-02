"""The two shipped chaos experiments (AR-362).

``staffing_window`` reproduces the AR-353 staffing-verdict window on demand:
the workforce structured-provider invoker is replaced, through its documented
module-global seam, by a stub that times out, returns a contract-invalid
completion, or rejects at the strict critic, and the oracle checks that the
turn fails open exactly as shipped (``preflight_failed`` run, content-free
failure receipt, ``no_specialist_fail_open`` result bound to the resident
kernel, Rule-8 pass-through). ``runner_hard_kill`` exercises the AR-297
review's recovery gap: an owned child process begins preflight attempts in
the dedicated store and is SIGKILLed mid-attempt; the oracle records what the
store does with the orphan and names the gap instead of hiding it.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.chaos.contracts import (
    VERDICT_FAIL,
    VERDICT_PASS,
    CaseParameters,
    Effect,
    EffectDetail,
    Experiment,
    Oracle,
    Safety,
    Verdict,
)
from agency_runtime.core.chaos.safety import ChaosEnvelope
from agency_runtime.core.installer_contracts import HOOK_TIMEOUT_BUFFER_SECONDS
from agency_runtime.core.rule8_evidence import (
    turn_closed_without_bound_response,
    turn_never_received_staffing_contract,
)
from agency_runtime.core.structured_provider import StructuredProviderResult

# --- staffing_window -------------------------------------------------------

_STAFFING_HOST = "codex"
_STAFFING_REQUEST = "Review the authentication security patch and report the findings."
_STAFFING_UNIT_ID = "unit-work"
_STAFFING_SLUG = "code-reviewer"
_INVOKER_SEAM = "agency_runtime.core.workforce.inference.invoke_structured_provider_result"
_CRITIC_REJECTION_CODE = "chaos-injected-rejection"

Invoker = Callable[..., StructuredProviderResult | None]


@dataclass(frozen=True)
class StaffingShape:
    """One injectable shape of the AR-353 window and its shipped outcome."""

    name: str
    description: str
    build_invoker: Callable[[EffectDetail], Invoker]
    expected_reason_code: str
    expected_staffing_codes: tuple[str, ...]
    expected_inference_mode: str
    expected_attempt_statuses: tuple[str, ...]


def _stage_for_schema(schema: object) -> str:
    properties = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
    if "approved" in properties:
        return "critic"
    if "request_summary" in properties and "units" in properties:
        return "planner"
    if "units" in properties:
        return "recruiter"
    return "unknown"


def _record_call(detail: EffectDetail, schema: object) -> str:
    stage = _stage_for_schema(schema)
    detail["invoker_calls"] = int(detail.get("invoker_calls", 0)) + 1
    stages = list(detail.get("stages", ()))
    if len(stages) < 16:
        stages.append(stage)
    detail["stages"] = stages
    return stage


def _structured(provider: Any, value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name=str(getattr(provider, "name", "chaos-stub")),
        provider_type=str(getattr(provider, "type", "litellm")),
        transport="",
        requested_model=str(getattr(provider, "model", "chaos-stub")),
        model_group=str(getattr(provider, "model", "chaos-stub")),
        actual_model="chaos-stub",
        model_receipt_source="response.body.model",
        latency_ms=1,
    )


def _provider_timeout_invoker(detail: EffectDetail) -> Invoker:
    def invoke(_provider: Any, _prompt: str, schema: Any, **_kwargs: Any) -> None:
        _record_call(detail, schema)
        return None

    return invoke


def _invalid_completion_invoker(detail: EffectDetail) -> Invoker:
    def invoke(
        provider: Any, _prompt: str, schema: Any, **_kwargs: Any
    ) -> StructuredProviderResult:
        _record_call(detail, schema)
        return _structured(provider, {"chaos": "contract-invalid"})

    return invoke


def _critic_rejected_invoker(detail: EffectDetail) -> Invoker:
    def invoke(
        provider: Any,
        _prompt: str,
        schema: Any,
        **_kwargs: Any,
    ) -> StructuredProviderResult | None:
        stage = _record_call(detail, schema)
        if stage == "critic":
            return _structured(
                provider,
                {"approved": False, "reason_codes": [_CRITIC_REJECTION_CODE]},
            )
        if stage == "planner":
            return _structured(
                provider,
                {
                    "request_summary": "Review one security patch.",
                    "units": [
                        {
                            "unit_id": _STAFFING_UNIT_ID,
                            "outcome": "Review the patch and report findings.",
                            "artifact_kind": "review-report",
                            "domains": ["software-engineering"],
                            "stacks": [],
                            "capability_ids": ["review"],
                            "novel_capability": "",
                            "depends_on": [],
                        }
                    ],
                },
            )
        if stage == "recruiter":
            return _structured(
                provider,
                {
                    "units": [
                        {
                            "unit_id": _STAFFING_UNIT_ID,
                            "decision": "staff",
                            "ranked_semantic": [
                                {
                                    "agent_id": _STAFFING_SLUG,
                                    "score": 0.99,
                                    "classification": "required",
                                    "positive_evidence": ["scope-match"],
                                    "negative_evidence": [],
                                }
                            ],
                        }
                    ]
                },
            )
        return None

    return invoke


_STAFFING_SHAPES: tuple[StaffingShape, ...] = (
    StaffingShape(
        name="provider_timeout",
        description="The provider never answers the planner: every call times out.",
        build_invoker=_provider_timeout_invoker,
        expected_reason_code="workforce_provider_unavailable",
        expected_staffing_codes=("inference_unavailable",),
        expected_inference_mode="unavailable",
        expected_attempt_statuses=("failed",),
    ),
    StaffingShape(
        name="invalid_completion",
        description="The provider answers the planner with a completion that fails its contract.",
        build_invoker=_invalid_completion_invoker,
        expected_reason_code="workforce_inference_failed",
        expected_staffing_codes=("inference_invalid",),
        expected_inference_mode="invalid",
        expected_attempt_statuses=("rejected", "rejected"),
    ),
    StaffingShape(
        name="critic_rejected",
        description="Planner and recruiter succeed; the strict critic rejects the staffing.",
        build_invoker=_critic_rejected_invoker,
        expected_reason_code="workforce_inference_failed",
        expected_staffing_codes=("staffing_critic_rejected",),
        expected_inference_mode="invalid",
        expected_attempt_statuses=("applied", "applied", "applied"),
    ),
)
_SHAPES_BY_NAME = {shape.name: shape for shape in _STAFFING_SHAPES}


def _staffing_shape(case: CaseParameters) -> StaffingShape:
    shape = _SHAPES_BY_NAME.get(str(case.get("case") or ""))
    if shape is None:
        raise ValueError("unknown staffing-window shape")
    return shape


def _staffing_config() -> Any:
    """Declare one provider so the workforce funnel runs; the stub owns transport."""

    from agency_runtime.core.config import AgencyConfig, OllamaConfig, ProviderEntry

    return AgencyConfig(
        ollama=OllamaConfig(enabled=False, model=""),
        providers=(
            ProviderEntry(
                name="chaos-stub-router",
                type="litellm",
                model="chaos-stub",
                base_url="https://chaos.invalid/v1",
                api_key="chaos-stub-transport-never-used",
            ),
        ),
    )


@contextmanager
def _forced_inference_failure(
    envelope: ChaosEnvelope, case: CaseParameters
) -> Iterator[EffectDetail]:
    """Install the shape's stub at the workforce invoker seam; always restore it.

    ``plan_and_staff_workforce`` resolves ``invoke_structured_provider_result``
    from its module globals at call time, so replacing that name drives every
    planner, recruiter, and critic call of the turn through the stub without
    any transport, provider, or network involvement.
    """

    envelope.require_armed()
    shape = _staffing_shape(case)
    from agency_runtime.core.workforce import inference as inference_module

    detail: EffectDetail = {
        "shape": shape.name,
        "seam": _INVOKER_SEAM,
        "invoker_calls": 0,
        "stages": [],
        "removed": False,
    }
    original = inference_module.invoke_structured_provider_result
    inference_module.invoke_structured_provider_result = shape.build_invoker(detail)
    try:
        yield detail
    finally:
        inference_module.invoke_structured_provider_result = original
        detail["removed"] = inference_module.invoke_structured_provider_result is original


def _staffing_action(
    envelope: ChaosEnvelope,
    case: CaseParameters,
    _detail: EffectDetail,
) -> Mapping[str, Any]:
    """Run one substantive preflight under the injected shape and read back."""

    from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
    from agency_runtime.core.preflight import run_preflight
    from agency_runtime.core.turn_origin import native_adapter_turn_origin
    from agency_runtime.core.workforce.cache import clear_workforce_caches

    shape = _staffing_shape(case)
    store = envelope.open_store()
    session_id = envelope.mint_session_id(shape.name)
    trace_id = envelope.mint_trace_id(shape.name)
    platform = "windows" if os.name == "nt" else "linux"
    clear_workforce_caches()
    result = run_preflight(
        store,
        session_id=envelope.require_session(session_id),
        user_message=_STAFFING_REQUEST,
        host=_STAFFING_HOST,
        trace_id=trace_id,
        config=_staffing_config(),
        capability_receipt=native_adapter_capability_receipt(
            _STAFFING_HOST,
            platform=platform,
            session_id=session_id,
            trace_id=trace_id,
        ),
        origin_receipt=native_adapter_turn_origin(
            "external_user",
            host=_STAFFING_HOST,
            event="adapter_preflight",
            session_id=session_id,
            trace_id=trace_id,
        ),
    )
    run = store.get_run(trace_id) or {}
    receipt = store.get_preflight_failure_receipt(session_id, trace_id)
    attempts = list(receipt.get("provider_attempts") or ()) if receipt else []
    routing = result.routing
    return {
        "run_status": str(run.get("status") or ""),
        "preflight_state": str(run.get("preflight_state") or ""),
        "failure_receipt_present": receipt is not None,
        "failure_stage": str(receipt.get("stage") or "") if receipt else "",
        "failure_reason_code": str(receipt.get("reason_code") or "") if receipt else "",
        "staffing_reason_codes": list(receipt.get("staffing_reason_codes") or ())
        if receipt
        else [],
        "provider_attempt_stages": [str(item.get("stage") or "") for item in attempts],
        "provider_attempt_statuses": [str(item.get("status") or "") for item in attempts],
        "provider_attempt_reason_codes": [str(item.get("reason_code") or "") for item in attempts],
        "routing_status": str(routing.get("status") or ""),
        "routing_source": str(routing.get("source") or ""),
        "inference_mode": str(routing.get("inference_mode") or ""),
        "inference_attempted": bool(routing.get("inference_attempted")),
        "selected_specialist_count": len(result.selected_specialists),
        "resident_manager_count": len(result.resident_managers),
        "resident_kernel_version": int(result.resident_manager_kernel_version),
        "resident_kernel_hash_present": bool(result.resident_manager_kernel_hash),
        "context_present": bool(result.context.strip()),
        "rule8_turn_closed_without_bound_response": turn_closed_without_bound_response(
            store, session_id, trace_id
        ),
        "identities": {
            "session_ids": [session_id],
            "trace_ids": [trace_id],
            "run_ids": [str(run.get("id"))] if run.get("id") else [],
            "failure_receipt_ids": [str(receipt.get("id"))]
            if receipt and receipt.get("id")
            else [],
        },
    }


def _staffing_findings(shape: StaffingShape, observed: Mapping[str, Any]) -> list[str]:
    effect = observed.get("effect") if isinstance(observed.get("effect"), Mapping) else {}
    checks = (
        ("run_not_preflight_failed", observed.get("run_status") == "preflight_failed"),
        ("failure_receipt_missing", observed.get("failure_receipt_present") is True),
        ("failure_stage_unexpected", observed.get("failure_stage") == "routing"),
        (
            "failure_reason_unexpected",
            observed.get("failure_reason_code") == shape.expected_reason_code,
        ),
        (
            "staffing_codes_unexpected",
            tuple(observed.get("staffing_reason_codes") or ()) == shape.expected_staffing_codes,
        ),
        (
            "provider_attempts_unexpected",
            tuple(observed.get("provider_attempt_statuses") or ())
            == shape.expected_attempt_statuses,
        ),
        ("routing_not_fail_open", observed.get("routing_status") == "no_specialist_fail_open"),
        (
            "inference_mode_unexpected",
            observed.get("inference_mode") == shape.expected_inference_mode,
        ),
        ("specialist_selected", observed.get("selected_specialist_count") == 0),
        (
            "resident_kernel_missing",
            int(observed.get("resident_manager_count") or 0) > 0
            and int(observed.get("resident_kernel_version") or 0) > 0
            and observed.get("resident_kernel_hash_present") is True
            and observed.get("context_present") is True,
        ),
        (
            "rule8_pass_through_missing",
            observed.get("rule8_turn_closed_without_bound_response") is True,
        ),
        ("invoker_not_reached", int(effect.get("invoker_calls") or 0) > 0),
        ("effect_not_removed", effect.get("removed") is True),
    )
    return [code for code, passed in checks if not passed]


def _staffing_judge(observations: Mapping[str, Mapping[str, Any]]) -> Verdict:
    codes: list[str] = []
    for shape in _STAFFING_SHAPES:
        observed = observations.get(shape.name)
        if not isinstance(observed, Mapping):
            codes.append(f"{shape.name}_not_observed")
            continue
        codes.extend(f"{shape.name}_{code}" for code in _staffing_findings(shape, observed))
    return Verdict(
        VERDICT_PASS if not codes else VERDICT_FAIL,
        reason_codes=tuple(codes),
        observations=observations,
    )


STAFFING_WINDOW = Experiment(
    name="staffing_window",
    description=(
        "AR-353 staffing-verdict window: workforce inference fails during staffing and "
        "the substantive turn must fail open with a content-free receipt, the resident "
        "kernel bound, and Rule-8 pass-through."
    ),
    effect=Effect(
        name="forced_inference_failure",
        description=(
            "Replace the workforce structured-provider invoker at its module-global seam "
            "with a stub that times out, returns a contract-invalid completion, or rejects "
            "at the strict critic; restored on exit."
        ),
        apply=_forced_inference_failure,
    ),
    safety=Safety(),
    oracle=Oracle(
        name="fail_open_with_receipt",
        description=(
            "The run closes preflight_failed with the expected reason and staffing codes, "
            "the fail-open result carries the resident kernel, and the Rule-8 gate passes "
            "the host's draft through."
        ),
        judge=_staffing_judge,
    ),
    action=_staffing_action,
    cases=tuple({"case": shape.name} for shape in _STAFFING_SHAPES),
)


# --- runner_hard_kill -------------------------------------------------------

_HARD_KILL_HOST = "chaos"
_HARD_KILL_FINGERPRINT = hashlib.sha256(b"agency chaos runner hard kill").hexdigest()
_HARD_KILL_REQUEST_KIND = "nontrivial"
_CHILD_START_TIMEOUT_SECONDS = 60.0
_CHILD_REAP_TIMEOUT_SECONDS = 10.0
_CHILD_LINE_LIMIT = 64 * 1024
_CHILD_STDERR_LIMIT = 8 * 1024
_LEASE_POLL_SECONDS = 0.25
_LEASE_GRACE_SECONDS = 5.0
_ATTEMPT_TOKEN = re.compile(r"^[0-9a-f-]{8,64}$")
_HARD_KILL_GAP_NOTES = (
    "Nothing reclaims a preflight attempt whose runner died: the run stays active with "
    "preflight_state in_progress under the dead attempt token until its lease lapses "
    "(minimum 6 s: lease_seconds=1 plus the 5 s hook buffer; host turns lease the full "
    "hook timeout).",
    "A same-trace retry inside the lease is told the attempt is still running "
    "(reused_in_progress) and would wait out the lease before it could recover.",
    "active is not a FAIL_OPEN_RUN_STATUSES member, so turn_closed_without_bound_response "
    "is False for the orphan; only the AR-366 gate turn_never_received_staffing_contract "
    "(active + in_progress) passes a same-trace host draft through during that window.",
    "The orphan closes only when a same-trace retry lands after lease expiry "
    "(recovered_started, orphan child evidence purged) or the session's next turn "
    "reserves itself (reserve_session_turn flips it to abandoned); interrupted is written "
    "only by the hermes bridge from a host payload.",
)

# The child program is argv-driven and prints exactly one JSON line. It opens
# the dedicated store the parent already initialized, begins one attempt per
# (session, trace) pair with the parent's fingerprint, then blocks until the
# parent SIGKILLs it: no atexit, no cleanup, exactly what a dead runner leaves.
_CHILD_PROGRAM = r"""
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
from agency_runtime.core.store.sqlite import Store
db_path, fingerprint, lease = sys.argv[2], sys.argv[3], int(sys.argv[4])
pairs = sys.argv[5:]
store = Store(db_path)
began = []
for index in range(0, len(pairs), 2):
    started = store.begin_preflight_attempt(
        session_id=pairs[index],
        trace_id=pairs[index + 1],
        request_fingerprint=fingerprint,
        request_kind="nontrivial",
        host="chaos",
        lease_seconds=lease,
    )
    began.append(
        {
            "session_id": pairs[index],
            "trace_id": pairs[index + 1],
            "outcome": started["outcome"],
            "attempt_token": started["attempt_token"],
        }
    )
sys.stdout.write(json.dumps({"pid": os.getpid(), "began": began}) + "\n")
sys.stdout.flush()
while True:
    time.sleep(60)
"""


def _lease_seconds(case: CaseParameters) -> int:
    value = case.get("lease_seconds", 1)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 60:
        raise ValueError("hard-kill lease_seconds must be an integer from 1 through 60")
    return value


def _package_root() -> str:
    import agency_runtime

    return str(Path(agency_runtime.__file__).resolve().parent.parent)


def _owned_child_kwargs() -> dict[str, Any]:
    """Mirror owned-process launch flags: a private session or process group."""

    if os.name == "nt":
        return {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        }
    return {"start_new_session": True}


def _expected_kill_exit_code() -> int | None:
    return None if os.name == "nt" else -int(signal.SIGKILL)


def _hard_kill(process: subprocess.Popen[str]) -> None:
    """SIGKILL only the child this effect created, then reap it boundedly."""

    if process.poll() is not None:
        return
    with suppress(OSError):
        if os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                process.kill()
        else:
            process.kill()
    try:
        process.wait(timeout=_CHILD_REAP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("chaos child survived SIGKILL") from error


def _read_first_line(stream: Any, sink: list[str]) -> None:
    try:
        sink.append(str(stream.readline(_CHILD_LINE_LIMIT)))
    except (OSError, ValueError):
        sink.append("")


def _drain_stderr(stream: Any, sink: list[str]) -> None:
    try:
        sink.append(str(stream.read(_CHILD_STDERR_LIMIT)))
    except (OSError, ValueError):
        sink.append("")


def _close_pipes(process: subprocess.Popen[str]) -> None:
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            with suppress(OSError, ValueError):
                stream.close()


def _stderr_tail(sink: list[str]) -> str:
    text = " ".join("".join(sink).split())
    return text[-500:]


def _await_child_report(
    process: subprocess.Popen[str], stderr_sink: list[str]
) -> Mapping[str, Any]:
    lines: list[str] = []
    reader = threading.Thread(target=_read_first_line, args=(process.stdout, lines), daemon=True)
    reader.start()
    reader.join(_CHILD_START_TIMEOUT_SECONDS)
    line = lines[0] if lines else ""
    if reader.is_alive() or not line.strip():
        _hard_kill(process)
        raise RuntimeError(
            "chaos child did not begin its preflight attempts: " + _stderr_tail(stderr_sink)
        )
    payload = safe_load_bounded_json(
        line,
        maximum_bytes=_CHILD_LINE_LIMIT,
        maximum_depth=6,
        maximum_nodes=256,
    )
    if not isinstance(payload, Mapping):
        raise RuntimeError("chaos child report is not an object")
    return payload


def _verify_child_attempts(
    store: Any,
    process: subprocess.Popen[str],
    payload: Mapping[str, Any],
    expected: tuple[dict[str, str], ...],
) -> list[dict[str, str]]:
    """Accept the child's report only when it names our pid and our live rows."""

    if payload.get("pid") != process.pid:
        raise RuntimeError("chaos child reported a foreign pid")
    rows = payload.get("began")
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise RuntimeError("chaos child reported an unexpected attempt set")
    verified: list[dict[str, str]] = []
    for row, want in zip(rows, expected, strict=True):
        if (
            not isinstance(row, Mapping)
            or row.get("session_id") != want["session_id"]
            or row.get("trace_id") != want["trace_id"]
            or row.get("outcome") != "started"
        ):
            raise RuntimeError("chaos child began an unexpected attempt")
        token = str(row.get("attempt_token") or "")
        if _ATTEMPT_TOKEN.fullmatch(token) is None:
            raise RuntimeError("chaos child attempt token is malformed")
        observed = store.observe_preflight_attempt(want["session_id"], want["trace_id"], token)
        if (
            observed is None
            or observed.get("run_status") != "active"
            or observed.get("preflight_state") != "in_progress"
            or observed.get("attempt_matches") is not True
        ):
            raise RuntimeError("chaos child attempt is not live in the dedicated store")
        verified.append(
            {"session_id": want["session_id"], "trace_id": want["trace_id"], "outcome": "started"}
        )
    return verified


@contextmanager
def _runner_hard_kill(envelope: ChaosEnvelope, case: CaseParameters) -> Iterator[EffectDetail]:
    """Spawn an owned child mid-preflight in the dedicated store and SIGKILL it."""

    envelope.require_armed()
    lease_seconds = _lease_seconds(case)
    store = envelope.open_store()
    expected = (
        {
            "session_id": envelope.mint_session_id("hard-kill-recovery"),
            "trace_id": envelope.mint_trace_id("hard-kill-recovery"),
        },
        {
            "session_id": envelope.mint_session_id("hard-kill-abandon"),
            "trace_id": envelope.mint_trace_id("hard-kill-abandon"),
        },
    )
    argv = [
        sys.executable,
        "-I",
        "-c",
        _CHILD_PROGRAM,
        _package_root(),
        str(envelope.db_path),
        _HARD_KILL_FINGERPRINT,
        str(lease_seconds),
    ]
    for attempt in expected:
        argv.extend((attempt["session_id"], attempt["trace_id"]))
    process = subprocess.Popen(
        argv,
        cwd=str(envelope.runtime_home),
        env=dict(envelope.child_environ),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        **_owned_child_kwargs(),
    )
    stderr_sink: list[str] = []
    threading.Thread(target=_drain_stderr, args=(process.stderr, stderr_sink), daemon=True).start()
    detail: EffectDetail = {
        "child_pid": process.pid,
        "kill_signal": "SIGKILL",
        "lease_seconds": lease_seconds,
        "attempts": [],
        "attempts_verified": False,
        "child_exited": False,
    }
    try:
        payload = _await_child_report(process, stderr_sink)
        detail["attempts"] = _verify_child_attempts(store, process, payload, expected)
        detail["attempts_verified"] = True
        _hard_kill(process)
        detail["child_exited"] = process.poll() is not None
        detail["child_exit_code"] = process.returncode
        yield detail
    finally:
        _hard_kill(process)
        _close_pipes(process)


def _same_trace_retry(store: Any, attempt: Mapping[str, str], lease_seconds: int) -> dict[str, str]:
    return store.begin_preflight_attempt(
        session_id=attempt["session_id"],
        trace_id=attempt["trace_id"],
        request_fingerprint=_HARD_KILL_FINGERPRINT,
        request_kind=_HARD_KILL_REQUEST_KIND,
        host=_HARD_KILL_HOST,
        lease_seconds=lease_seconds,
    )


def _wait_for_lease_expiry(
    store: Any,
    attempt: Mapping[str, str],
    lease_seconds: int,
) -> tuple[str, float]:
    """Retry the same trace until the orphan's lease lapses or the deadline passes."""

    deadline = lease_seconds + math.ceil(HOOK_TIMEOUT_BUFFER_SECONDS) + _LEASE_GRACE_SECONDS
    started = time.monotonic()
    while True:
        outcome = str(_same_trace_retry(store, attempt, lease_seconds).get("outcome") or "")
        elapsed = time.monotonic() - started
        if outcome != "reused_in_progress" or elapsed >= deadline:
            return outcome, elapsed
        time.sleep(_LEASE_POLL_SECONDS)


def _run_row(store: Any, attempt: Mapping[str, str]) -> dict[str, Any]:
    run = store.get_run(attempt["trace_id"])
    if not isinstance(run, Mapping) or run.get("session_id") != attempt["session_id"]:
        raise RuntimeError("chaos orphan run is missing from the dedicated store")
    return dict(run)


def _hard_kill_action(
    envelope: ChaosEnvelope,
    _case: CaseParameters,
    detail: EffectDetail,
) -> Mapping[str, Any]:
    """Observe what the store does with the orphan, without repairing anything."""

    store = envelope.open_store()
    lease_seconds = int(detail["lease_seconds"])
    recovery, abandonment = detail["attempts"]
    identities: dict[str, list[str]] = {
        "session_ids": [recovery["session_id"], abandonment["session_id"]],
        "trace_ids": [recovery["trace_id"], abandonment["trace_id"]],
        "run_ids": [],
        "failure_receipt_ids": [],
    }
    observations: dict[str, Any] = {}
    for label, attempt in (("recovery", recovery), ("abandonment", abandonment)):
        run = _run_row(store, attempt)
        observations[f"{label}_orphan_status"] = str(run.get("status") or "")
        observations[f"{label}_orphan_preflight_state"] = str(run.get("preflight_state") or "")
        identities["run_ids"].append(str(run.get("id") or ""))
    observations["orphan_rule8_turn_closed_without_bound_response"] = (
        turn_closed_without_bound_response(store, recovery["session_id"], recovery["trace_id"])
    )
    observations["orphan_rule8_turn_never_received_staffing_contract"] = (
        turn_never_received_staffing_contract(store, recovery["session_id"], recovery["trace_id"])
    )
    retry = _same_trace_retry(store, recovery, lease_seconds)
    observations["same_trace_retry_before_lease_expiry"] = str(retry.get("outcome") or "")
    outcome, waited = _wait_for_lease_expiry(store, recovery, lease_seconds)
    observations["same_trace_retry_after_lease_expiry"] = outcome
    observations["seconds_until_lease_recovery"] = round(waited, 1)
    recovered = _run_row(store, recovery)
    observations["recovered_status"] = str(recovered.get("status") or "")
    observations["recovered_preflight_state"] = str(recovered.get("preflight_state") or "")
    next_trace = envelope.mint_trace_id("hard-kill-next-turn")
    store.reserve_session_turn(
        session_id=abandonment["session_id"],
        trace_id=next_trace,
        host=_HARD_KILL_HOST,
    )
    identities["trace_ids"].append(next_trace)
    abandoned = _run_row(store, abandonment)
    observations["orphan_status_after_next_turn"] = str(abandoned.get("status") or "")
    observations["abandoned_rule8_turn_closed_without_bound_response"] = (
        turn_closed_without_bound_response(
            store, abandonment["session_id"], abandonment["trace_id"]
        )
    )
    observations["identities"] = identities
    return observations


def _hard_kill_findings(observed: Mapping[str, Any]) -> list[str]:
    effect = observed.get("effect") if isinstance(observed.get("effect"), Mapping) else {}
    expected_exit = _expected_kill_exit_code()
    checks = (
        ("child_attempts_unverified", effect.get("attempts_verified") is True),
        (
            "child_not_killed",
            effect.get("child_exited") is True
            and (expected_exit is None or effect.get("child_exit_code") == expected_exit),
        ),
        (
            "recovery_orphan_not_live",
            observed.get("recovery_orphan_status") == "active"
            and observed.get("recovery_orphan_preflight_state") == "in_progress",
        ),
        (
            "abandonment_orphan_not_live",
            observed.get("abandonment_orphan_status") == "active"
            and observed.get("abandonment_orphan_preflight_state") == "in_progress",
        ),
        (
            "orphan_rule8_gap_changed",
            observed.get("orphan_rule8_turn_closed_without_bound_response") is False,
        ),
        (
            "orphan_ar366_gate_missing",
            observed.get("orphan_rule8_turn_never_received_staffing_contract") is True,
        ),
        (
            "retry_before_expiry_unexpected",
            observed.get("same_trace_retry_before_lease_expiry") == "reused_in_progress",
        ),
        (
            "retry_after_expiry_unexpected",
            observed.get("same_trace_retry_after_lease_expiry") == "recovered_started",
        ),
        (
            "recovered_attempt_not_live",
            observed.get("recovered_status") == "active"
            and observed.get("recovered_preflight_state") == "in_progress",
        ),
        ("next_turn_did_not_abandon", observed.get("orphan_status_after_next_turn") == "abandoned"),
        (
            "abandoned_rule8_pass_through_missing",
            observed.get("abandoned_rule8_turn_closed_without_bound_response") is True,
        ),
    )
    return [code for code, passed in checks if not passed]


def _hard_kill_judge(observations: Mapping[str, Mapping[str, Any]]) -> Verdict:
    observed = observations.get("lease_1s")
    if not isinstance(observed, Mapping):
        return Verdict(
            VERDICT_FAIL, reason_codes=("hard_kill_not_observed",), observations=observations
        )
    codes = _hard_kill_findings(observed)
    return Verdict(
        VERDICT_PASS if not codes else VERDICT_FAIL,
        reason_codes=tuple(codes),
        observations=observations,
        gap_notes=_HARD_KILL_GAP_NOTES,
    )


RUNNER_HARD_KILL = Experiment(
    name="runner_hard_kill",
    description=(
        "AR-297 runner hard-kill recovery: an owned child begins preflight attempts in "
        "the dedicated store and is SIGKILLed mid-attempt; the oracle records how the "
        "orphan is (and is not) reclaimed."
    ),
    effect=Effect(
        name="sigkill_owned_child_mid_preflight",
        description=(
            "Spawn a python child that opens the dedicated store, begins two preflight "
            "attempts, reports them, and blocks; SIGKILL its private session once the "
            "attempts are verified live."
        ),
        apply=_runner_hard_kill,
    ),
    safety=Safety(),
    oracle=Oracle(
        name="orphan_reclaim_behavior",
        description=(
            "The orphan stays active/in_progress until lease expiry (same-trace retry then "
            "recovers) or the session's next turn abandons it; the Rule-8 gate outcomes "
            "for each state are recorded and the gap is named."
        ),
        judge=_hard_kill_judge,
    ),
    action=_hard_kill_action,
    cases=({"case": "lease_1s", "lease_seconds": 1},),
)


__all__ = [
    "RUNNER_HARD_KILL",
    "STAFFING_WINDOW",
    "StaffingShape",
    "staffing_shapes",
]


def staffing_shapes() -> tuple[StaffingShape, ...]:
    """Return the injectable AR-353 shapes in the order the oracle judges them."""

    return _STAFFING_SHAPES
