"""Durable routing-receipt and evidence-faithful header regressions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core import preflight as preflight_module
from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.header.contract import (
    HEADER_FIELDS,
    EvidenceCorrelationError,
    _delegation_line,
    fill_header_fields,
    finalize_header,
    format_header,
    validate_completion_policy,
)
from agency_runtime.core.header.explanations import (
    humanize_effect_codes,
    humanize_reason_codes,
)
from agency_runtime.core.native_child_decision import (
    NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
    canonical_native_child_provider_receipt_digest,
)
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.selector import pipeline
from agency_runtime.core.selector import receipt_projection as receipts
from agency_runtime.core.selector.delegation_detection import detect_work_units
from agency_runtime.core.selector.receipt_projection import (
    normalize_durable_routing_receipt,
    project_durable_routing_receipt,
)
from agency_runtime.core.store.sqlite import Store


def _routing(message: str, trace_id: str) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "query_hash": hashlib.sha256(message.encode()).hexdigest(),
        "context_fingerprint": "c" * 64,
        "selected_ids": [],
        "semantic_ids": [],
        "confidence": 0.0,
        "top_score": 0.25,
        "latency_ms": 17,
        "candidate_count": 3,
        "status": "degraded",
        "source": "degraded_inference",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "degraded",
        "provider_attempts": [
            {
                "provider_name": "primary-router",
                "provider_type": "litellm",
                "requested_model": "task-agency-router",
                "model_group": "task-agency-router",
                "status": "failed",
                "reason": "provider_call_failed",
                "validation_detail": (
                    "workforce nomination failures: "
                    "unit-api=invalid_candidate,unit-docs=missing_work_unit"
                ),
            },
            {
                "provider_name": "fallback-local",
                "provider_type": "ollama",
                "requested_model": "qwen3",
                "model_group": "",
                "status": "applied",
                "reason": "",
            },
        ],
        "retrieval": {
            "mode": "lexical+deterministic-metadata-embedding+hard-negatives",
            "full_roster_count": 261,
            "candidate_union_count": 17,
            "lexical_count": 8,
            "semantic_count": 12,
            "hard_negative_count": 3,
        },
        "compatibility": {
            "contract_version": 1,
            "selection_limit": 3,
            "requested_ids": ["builder", "reviewer"],
            "selected_ids": ["builder"],
            "selected_root_ids": ["builder"],
            "added_requirements": [],
            "overflow_review_ids": [],
            "rejected": [{"slug": "reviewer", "reason": "conflicts_with:builder"}],
            "separate_context_pairs": [],
            "compatible": False,
        },
        "eligibility_rejections": [
            {"slug": "linux-only", "reason": "unsupported_tool_platform:windows"},
            {"slug": "browser-worker", "reason": "missing_capabilities:browser-automation"},
        ],
        "work_units": detect_work_units(message),
        "fallback_applied": False,
    }


def _ready_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    trace_id: str,
    routing_value: dict[str, Any] | None = None,
    host: str = "codex",
) -> tuple[Store, dict[str, Any]]:
    store = Store(tmp_path / f"{trace_id}.db")
    message = "Audit the routing evidence boundary."
    routing = routing_value or _routing(message, trace_id)
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: routing)
    monkeypatch.setattr(
        preflight_module,
        "_require_substantive_specialist",
        lambda *_args, **_kwargs: None,
    )
    run_preflight(
        store,
        session_id="session",
        user_message=message,
        host=host,
        trace_id=trace_id,
        config=AgencyConfig(ollama=OllamaConfig(enabled=False, model="")),
    )
    return store, routing


def _append_valid_openclaw_native_child_route(
    store: Store,
    *,
    trace_id: str,
    child_key: str = "completion",
) -> dict[str, str]:
    """Append the exact success projection emitted by native-child staffing."""

    session_id = "session"
    launch_id = f"{child_key}-launch"
    worker_id = f"agent:main:subagent:{child_key}-child"
    native_run_id = f"{child_key}-child-run"
    work_unit_id = f"{child_key}-review"
    task_sha256 = hashlib.sha256(f"Review the {child_key} boundary.".encode()).hexdigest()
    context_fingerprint = hashlib.sha256(f"{child_key}-context".encode()).hexdigest()
    issued = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    attempts = [
        {
            "provider_name": "linux-task-agency-router",
            "provider_type": "litellm",
            "requested_model": "task-agency-router",
            "model_group": "task-agency-router",
            "actual_model": "",
            "model_receipt_source": "unavailable",
            "status": "applied",
            "reason_code": "",
        }
    ]
    cards = [
        {
            "specialist_slug": "code-reviewer",
            "specialist_version": "revision-code-reviewer",
            "specialist_prompt_hash": hashlib.sha256(b"review prompt").hexdigest(),
            "body_character_length": 13,
        }
    ]
    delivery = {
        "schema": NATIVE_CHILD_STAFFING_DECISION_SCHEMA,
        "host": "openclaw",
        "parent_session_id": session_id,
        "parent_trace_id": trace_id,
        "launch_id": launch_id,
        "binding_kind": "launch_id",
        "binding_id": launch_id,
        "provider_attempts": attempts,
        "provider_receipt_digest": canonical_native_child_provider_receipt_digest(attempts),
        "task_sha256": task_sha256,
        "team_digest": hashlib.sha256(
            json.dumps(
                cards,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        "candidate_digest": hashlib.sha256(b"runtime").hexdigest(),
        "runtime_digest": hashlib.sha256(b"runtime").hexdigest(),
        "install_id": "install-openclaw-test",
        "bundle_digest": hashlib.sha256(b"bundle").hexdigest(),
        "issued_at": issued.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": (issued + timedelta(seconds=60))
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "nonce": f"{child_key}-nonce",
        "cards": cards,
    }
    decision = {
        "status": "applied",
        "semantic_status": "applied",
        "source": "native_child_inference",
        "selected_ids": ["code-reviewer"],
        "semantic_ids": ["code-reviewer"],
        "companion_ids": [],
        "available_companion_ids": [],
        "unavailable_companion_ids": [],
        "confidence": 0.9,
        "latency_ms": 12,
        "provider": "linux-task-agency-router",
        "candidate_count": 1,
        "top_score": 0.0,
        "native_child_reason": "applied",
        "inference_configured": True,
        "inference_required": True,
        "inference_attempted": True,
        "inference_mode": "inferred",
        "source_message_hash": task_sha256,
        "query_hash": task_sha256,
        "context_fingerprint": context_fingerprint,
        "native_child_delivery": delivery,
    }
    store.record_routing_decision(
        trace_id=trace_id,
        session_id=session_id,
        query_hash=task_sha256,
        context_fingerprint=context_fingerprint,
        decision=decision,
        require_open_run=True,
        final_delivery_validator=lambda: True,
    )
    store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host="openclaw",
        work_unit_id=work_unit_id,
        recommended_agent="code-reviewer",
        status="delegated",
        backend="sessions_spawn",
        executed_worker_kind="generic-worker",
        executed_worker_id=worker_id,
        native_run_id=native_run_id,
    )
    store.record_native_child_started(
        host="openclaw",
        backend="sessions_spawn",
        session_id=session_id,
        trace_id=trace_id,
        work_unit_id=work_unit_id,
        worker_id=worker_id,
        native_run_id=native_run_id,
    )
    assert store.bind_native_child_launch(
        host="openclaw",
        session_id=session_id,
        trace_id=trace_id,
        worker_id=worker_id,
        native_run_id=native_run_id,
        launch_id=launch_id,
    )
    return {
        "sessionId": session_id,
        "traceId": f"announce:v1:{worker_id}:{native_run_id}",
        "parentSessionId": session_id,
        "parentTraceId": trace_id,
        "workerId": worker_id,
        "nativeRunId": native_run_id,
        "launchId": launch_id,
        "workUnitId": work_unit_id,
        "model": "litellm/task-general",
    }


def test_ready_receipt_accepts_valid_routing_above_legacy_node_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "wide-ready-receipt"
    message = "Audit the routing evidence boundary."
    routing = _routing(message, trace_id)
    routing["eligibility_rejections"] = [
        {
            "slug": f"agent-{index}",
            "reason": "missing_capabilities:browser-automation",
        }
        for index in range(96)
    ]
    routing["provider_attempts"] = [
        {
            "provider_name": f"router-{attempt}",
            "provider_type": "litellm",
            "requested_model": "task-agency-router",
            "model_group": "task-agency-router",
            "status": "failed",
            "reason": "provider_response_contract_invalid",
            "validation_failures": [
                {
                    "unit_id": f"unit-{unit}",
                    "reason_code": "invalid_candidate",
                }
                for unit in range(16)
            ],
        }
        for attempt in range(8)
    ]
    routing["routing_receipt"] = project_durable_routing_receipt(routing)
    store, routing = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        routing_value=routing,
    )

    snapshot = store.get_completion_evidence_snapshot("session", trace_id)
    receipt = store.get_ready_routing_receipt(
        "session",
        trace_id,
        evidence_revision=snapshot["evidence_revision"],
    )

    assert receipt == project_durable_routing_receipt(routing)


def test_openclaw_completion_header_keeps_canonical_preflight_route_with_child_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "openclaw-completion-parent"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    completion = _append_valid_openclaw_native_child_route(store, trace_id=trace_id)

    prepared = node_bridge.handle(
        {"action": "native_child_completion_prepare", **completion},
        adapter=OpenClawAdapter(store=store),
    )

    assert prepared["prepared"] is True
    assert prepared["completion"] is True
    assert prepared["completionRunId"] == completion["traceId"]
    assert prepared["parentTraceId"] == trace_id
    assert prepared["context"].startswith("[AGENCY NATIVE CHILD COMPLETION CONTRACT]")
    assert "Agency/Agencies loaded: agency-steward" in prepared["context"]
    assert store.get_run(completion["traceId"]) is None


@pytest.mark.parametrize(
    ("extra_source", "extra_decision"),
    [
        ("computed", {"source": "unexpected_auxiliary_route"}),
        ("native_child_inference", {"source": "native_child_inference"}),
    ],
)
def test_ready_receipt_rejects_unrecognized_or_malformed_auxiliary_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_source: str,
    extra_decision: dict[str, Any],
) -> None:
    trace_id = f"invalid-auxiliary-{extra_source}"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
    )
    conn = store._connect()
    try:
        conn.execute(
            "INSERT INTO routing_decisions "
            "(id, trace_id, session_id, query_hash, context_fingerprint, status, "
            "source, selected_ids, semantic_ids, companion_ids, confidence, "
            "latency_ms, provider, work_units, decision, created_at) "
            "VALUES (?, ?, 'session', ?, ?, 'applied', ?, '[]', '[]', '[]', "
            "0, 0, '', '{}', ?, ?)",
            (
                f"extra-{extra_source}",
                trace_id,
                "d" * 64,
                "e" * 64,
                extra_source,
                json.dumps(extra_decision, sort_keys=True),
                store._now(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


def test_ready_receipt_rejects_duplicate_canonical_preflight_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "duplicate-canonical-route"
    store, _routing_value = _ready_store(tmp_path, monkeypatch, trace_id=trace_id)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT * FROM routing_decisions WHERE trace_id = ?",
            (trace_id,),
        ).fetchone()
        assert row is not None
        fields = (
            "trace_id",
            "session_id",
            "query_hash",
            "context_fingerprint",
            "status",
            "source",
            "selected_ids",
            "semantic_ids",
            "companion_ids",
            "confidence",
            "latency_ms",
            "provider",
            "work_units",
            "decision",
            "created_at",
        )
        conn.execute(
            "INSERT INTO routing_decisions "
            "(id, trace_id, session_id, query_hash, context_fingerprint, status, "
            "source, selected_ids, semantic_ids, companion_ids, confidence, "
            "latency_ms, provider, work_units, decision, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("duplicate-canonical", *(row[field] for field in fields)),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


def test_ready_receipt_rejects_duplicate_valid_native_child_launch_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "duplicate-native-child-launch-route"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT * FROM routing_decisions WHERE trace_id = ? "
            "AND source = 'native_child_inference'",
            (trace_id,),
        ).fetchone()
        assert row is not None
        fields = (
            "trace_id",
            "session_id",
            "query_hash",
            "context_fingerprint",
            "status",
            "source",
            "selected_ids",
            "semantic_ids",
            "companion_ids",
            "confidence",
            "latency_ms",
            "provider",
            "work_units",
            "decision",
            "created_at",
        )
        conn.execute(
            "INSERT INTO routing_decisions "
            "(id, trace_id, session_id, query_hash, context_fingerprint, status, "
            "source, selected_ids, semantic_ids, companion_ids, confidence, "
            "latency_ms, provider, work_units, decision, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("duplicate-native-child-launch", *(row[field] for field in fields)),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


def test_ready_receipt_accepts_distinct_native_child_launch_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "distinct-native-child-launch-routes"
    store, routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    _append_valid_openclaw_native_child_route(
        store,
        trace_id=trace_id,
        child_key="second",
    )
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    receipt = store.get_ready_routing_receipt(
        "session",
        trace_id,
        evidence_revision=snapshot["evidence_revision"],
    )

    assert receipt == project_durable_routing_receipt(routing_value)


def test_ready_receipt_rejects_noncanonical_native_child_route_timestamp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "noncanonical-native-child-created-at"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        conn.execute(
            "UPDATE routing_decisions SET created_at = 'not-a-store-clock' "
            "WHERE trace_id = ? AND source = 'native_child_inference'",
            (trace_id,),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


@pytest.mark.parametrize("tamper", ["whitespace_text", "blob"])
def test_ready_receipt_rejects_noncanonical_native_child_route_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    trace_id = f"noncanonical-native-child-route-id-{tamper}"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        if tamper == "whitespace_text":
            conn.execute(
                "UPDATE routing_decisions SET id = ' padded-native-child-route ' "
                "WHERE trace_id = ? AND source = 'native_child_inference'",
                (trace_id,),
            )
        else:
            conn.execute(
                "UPDATE routing_decisions SET id = CAST('blob-native-child-route' AS BLOB) "
                "WHERE trace_id = ? AND source = 'native_child_inference'",
                (trace_id,),
            )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ("selected_ids", '["code-reviewer" ]'),
        ("semantic_ids", '[ "code-reviewer"]'),
        ("companion_ids", "[ ]"),
        ("work_units", "{ }"),
    ],
)
def test_ready_receipt_rejects_noncanonical_native_child_json_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    column: str,
    replacement: str,
) -> None:
    trace_id = f"noncanonical-native-child-{column}"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        conn.execute(
            f"UPDATE routing_decisions SET {column} = ? "  # nosec B608 - test allowlist
            "WHERE trace_id = ? AND source = 'native_child_inference'",
            (replacement, trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


def test_ready_receipt_rejects_non_digest_native_child_context_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_id = "non-digest-native-child-context"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        row = conn.execute(
            "SELECT decision FROM routing_decisions WHERE trace_id = ? "
            "AND source = 'native_child_inference'",
            (trace_id,),
        ).fetchone()
        assert row is not None
        decision = json.loads(row["decision"])
        decision["context_fingerprint"] = "opaque-context"
        conn.execute(
            "UPDATE routing_decisions SET context_fingerprint = ?, decision = ? "
            "WHERE trace_id = ? AND source = 'native_child_inference'",
            ("opaque-context", json.dumps(decision, sort_keys=True), trace_id),
        )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


@pytest.mark.parametrize("tamper", ["fractional_latency", "blob_confidence"])
def test_ready_receipt_rejects_coercible_native_child_numeric_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    trace_id = f"coercible-native-child-{tamper}"
    store, _routing_value = _ready_store(
        tmp_path,
        monkeypatch,
        trace_id=trace_id,
        host="openclaw",
    )
    _append_valid_openclaw_native_child_route(store, trace_id=trace_id)
    conn = store._connect()
    try:
        if tamper == "fractional_latency":
            conn.execute(
                "UPDATE routing_decisions SET latency_ms = 12.9 "
                "WHERE trace_id = ? AND source = 'native_child_inference'",
                (trace_id,),
            )
        else:
            conn.execute(
                "UPDATE routing_decisions SET confidence = CAST('0.9' AS BLOB) "
                "WHERE trace_id = ? AND source = 'native_child_inference'",
                (trace_id,),
            )
        conn.commit()
    finally:
        conn.close()
    snapshot = store.get_completion_evidence_snapshot("session", trace_id)

    with pytest.raises(RuntimeError, match="routing receipt failed integrity"):
        store.get_ready_routing_receipt(
            "session",
            trace_id,
            evidence_revision=snapshot["evidence_revision"],
        )


def test_routing_receipt_is_bounded_content_free_and_idempotent() -> None:
    routing = _routing("Audit evidence.", "trace")
    secret = "TOP-SECRET-PROMPT-BODY"
    sensitive_unit_id = "unit-password-hunter2"
    routing["provider_attempts"][0]["validation_detail"] += f",{sensitive_unit_id}=invalid_ranking"
    routing["provider_attempts"].append(
        {
            "provider_name": secret,
            "provider_type": "openai-compatible",
            "requested_model": f"sk-{secret}",
            "status": "failed\nINJECT",
            "reason": f"credential={secret}",
            "validation_detail": (f"workforce nomination failures: unit-api={secret}"),
        }
    )
    routing["eligibility_rejections"] = [
        {"slug": f"agent-{index}", "reason": "missing_capabilities:browser"} for index in range(40)
    ]

    receipt = project_durable_routing_receipt(routing)
    normalized = normalize_durable_routing_receipt(receipt)

    assert normalized == receipt
    assert receipt["inference"]["provider_attempts"][0] == {
        "ordinal": 1,
        "provider_name": "primary-router",
        "provider_type": "litellm",
        "requested_model": "task-agency-router",
        "model_group": "task-agency-router",
        "status": "failed",
        "reason_code": "provider_call_failed",
        "validation_failures": [
            {"unit_id": "unit-api", "reason_code": "invalid_candidate"},
            {"unit_id": "unit-docs", "reason_code": "missing_work_unit"},
            {
                "unit_id": "sha256:" + hashlib.sha256(sensitive_unit_id.encode()).hexdigest(),
                "reason_code": "invalid_ranking",
            },
        ],
    }
    assert receipt["retrieval"]["full_roster_count"] == 261
    assert receipt["compatibility"]["rejections"] == [
        {"slug": "reviewer", "reason_code": "conflicts_with:builder"}
    ]
    assert receipt["eligibility"]["rejected_count"] == 40
    assert len(receipt["eligibility"]["rejections"]) == 32
    assert receipt["eligibility"]["sample_truncated"] is True
    assert receipt["hiring"] == {
        "outcome": "no_attempt",
        "events": [],
        "attempted_count": 0,
        "workforce_changes": 0,
        "calls_used": 0,
        "truncated": False,
    }
    assert "hiring_not_attempted" in receipt["effect_codes"]
    assert secret not in json.dumps(receipt)
    assert sensitive_unit_id not in json.dumps(receipt)
    assert "INJECT" not in json.dumps(receipt)
    assert normalize_durable_routing_receipt({"receipt_version": 999}) is None


def test_workforce_receipt_uses_explicit_eligible_catalog_count() -> None:
    routing = _routing("Build and review a local page.", "trace-workforce")
    routing["retrieval"] = {"mode": "unavailable", "full_roster_count": 0}
    routing["eligible_catalog_count"] = 192

    receipt = project_durable_routing_receipt(routing)

    assert receipt["retrieval"]["full_roster_count"] == 0
    assert receipt["eligibility"] == {
        "eligible_count": 192,
        "rejected_count": 2,
        "evaluated_count": 194,
        "rejections": [
            {
                "slug": "linux-only",
                "reason_code": "unsupported_tool_platform:windows",
            },
            {
                "slug": "browser-worker",
                "reason_code": "missing_capabilities:browser-automation",
            },
        ],
        "rejection_reason_counts": [
            {"reason_code": "missing_capabilities", "count": 1},
            {"reason_code": "unsupported_tool_platform", "count": 1},
        ],
        "sample_truncated": False,
    }


def test_routing_receipt_projects_changed_declined_and_mixed_hiring_outcomes() -> None:
    routing = _routing("Implement and review the change.", "trace-hiring")

    routing["hiring_events"] = [
        {
            "unit_id": "unit-build",
            "status": "hired",
            "reason_codes": ["safe_gap_hired"],
            "calls_used": 1,
        }
    ]
    assert project_durable_routing_receipt(routing)["hiring"]["outcome"] == "changed"

    routing["hiring_events"] = [
        {
            "unit_id": "unit-build",
            "status": "declined",
            "reason_codes": ["policy_denied"],
            "calls_used": 0,
        }
    ]
    assert project_durable_routing_receipt(routing)["hiring"]["outcome"] == "declined"

    routing["hiring_events"].append(
        {
            "unit_id": "unit-review",
            "status": "amended",
            "reason_codes": ["safe_gap_amended"],
            "calls_used": 1,
        }
    )
    assert project_durable_routing_receipt(routing)["hiring"]["outcome"] == "mixed"


def test_routing_receipt_preserves_content_free_staffing_gap_evidence() -> None:
    routing = _routing("Design, build, document, and review the change.", "trace-staffing")
    secret = "TOP-SECRET-STAFFING-DETAIL"
    routing["workforce_proposal"] = {
        "units": [
            {
                "unit_id": "unit-architecture",
                "required": ["software-architect"],
                "acceptable": ["backend-service-engineer"],
                "selected": [],
                "abstention_reasons": ["no_safe_deterministic_team"],
                "positive_evidence": [{"detail": secret}],
            },
            {
                "unit_id": "unit-documentation",
                "required": ["technical-writer"],
                "acceptable": [],
                "selected": ["technical-writer"],
                "abstention_reasons": [],
            },
        ]
    }
    routing["workforce_staffing"] = {
        "status": "abstained",
        "units": [],
        "abstention_reasons": [
            {
                "code": "no_safe_sufficient_team",
                "unit_id": "unit-architecture",
                "detail": secret,
            },
            {"code": "independent_assurance_missing", "detail": secret},
        ],
    }

    receipt = project_durable_routing_receipt(routing)

    assert receipt["staffing"] == {
        "status": "abstained",
        "units": [
            {
                "unit_id": "unit-architecture",
                "nominated_ids": ["software-architect", "backend-service-engineer"],
                "proposed_ids": [],
                "reason_codes": [
                    "no_safe_deterministic_team",
                    "no_safe_sufficient_team",
                ],
            },
            {
                "unit_id": "unit-documentation",
                "nominated_ids": ["technical-writer"],
                "proposed_ids": ["technical-writer"],
                "reason_codes": [],
            },
        ],
        "global_reason_codes": ["independent_assurance_missing"],
        "gap_count": 1,
        "truncated": False,
    }
    assert "staffing:no_safe_deterministic_team" in receipt["reason_codes"]
    assert "staffing:independent_assurance_missing" in receipt["reason_codes"]
    assert normalize_durable_routing_receipt(receipt) == receipt
    assert secret not in json.dumps(receipt)


def test_disabled_higher_ranked_specialist_is_visible_in_header_evidence() -> None:
    routing = _routing("Implement the TypeScript change.", "trace-disabled")
    routing["disabled_candidate_shadows"] = [
        {
            "agent_id": "typescript-application-engineer",
            "rank": 1,
            "reason_codes": ["agent_disabled"],
            "fallback_agent_id": "backend-service-engineer",
            "tradeoff": "The higher deterministic match is unavailable under current policy.",
        }
    ]

    receipt = project_durable_routing_receipt(routing)

    assert "disabled_candidate:typescript-application-engineer" in receipt["reason_codes"]
    assert "disabled_specialist_left_unselected" in receipt["effect_codes"]
    assert (
        "typescript application engineer would have ranked higher"
        in humanize_reason_codes(receipt["reason_codes"]).casefold()
    )
    assert (
        "stronger disabled specialist was left out"
        in humanize_effect_codes(receipt["effect_codes"]).casefold()
    )


def test_routing_receipt_projection_rejects_malformed_and_bounds_every_collection() -> None:
    assert receipts.bounded_receipt_text(None, maximum_bytes=4) == ""
    assert receipts.bounded_receipt_text("ok", maximum_bytes=4) == "ok"
    assert receipts.bounded_receipt_text("ééé", maximum_bytes=5) == "éé"
    assert receipts._bounded_count(True) == 0
    assert receipts._bounded_count(object()) == 0
    assert receipts._bounded_count(-1) == 0
    assert receipts._bounded_count(2_000_000) == 1_000_000

    assert receipts._ids("agent") == []
    assert receipts._ids(["", "agent", "agent", "agent-2"], limit=2) == [
        "agent",
        "agent-2",
    ]
    assert receipts._codes("reason") == []
    assert receipts._codes(["", "valid", "valid", "next"], limit=2) == [
        "valid",
        "next",
    ]
    assert receipts._provider_attempts("attempt") == []
    assert receipts._provider_attempts(
        [None, {"provider_name": "", "provider_type": "bad value", "status": ""}]
    ) == [
        {
            "ordinal": 2,
            "provider_name": "unavailable",
            "provider_type": "unknown",
            "requested_model": "",
            "model_group": "",
            "status": "unknown",
            "reason_code": "",
        }
    ]

    assert receipts._rejections("rejection") == []
    assert receipts._rejections([None, {"slug": ""}, {"slug": "agent", "reason": "no"}]) == [
        {"slug": "agent", "reason_code": "no"}
    ]
    assert (
        len(
            receipts._rejections(
                [{"slug": f"agent-{index}", "reason": "excluded"} for index in range(40)]
            )
        )
        == 32
    )
    assert receipts._reason_counts("rejection") == []
    assert receipts._reason_counts(
        [None, {"reason": ""}, {"reason": "conflict:a"}, {"reason_code": "conflict:b"}]
    ) == [{"reason_code": "conflict", "count": 2}]
    assert receipts._normalize_reason_counts("counts") == []
    assert receipts._normalize_reason_counts(
        [
            None,
            {"reason_code": "", "count": 1},
            {"reason_code": "conflict:a", "count": 0},
            {"reason_code": "conflict:b", "count": 2},
            {"reason_code": "conflict", "count": 3},
        ]
    ) == [{"reason_code": "conflict", "count": 5}]

    assert receipts._compatibility("invalid")["requested_ids"] == []
    pairs = [[f"left-{index}", f"right-{index}"] for index in range(35)]
    compatibility = receipts._compatibility(
        {
            "separate_context_pairs": [None, ["only-one"], ["a", "b"], ["a", "b"], *pairs],
            "rejected": "invalid",
            "compatible": True,
        }
    )
    assert compatibility["separate_context_pairs"][0] == ["a", "b"]
    assert len(compatibility["separate_context_pairs"]) == 32
    assert compatibility["compatible"] is True
    assert receipts._eligibility("invalid", {}) == {
        "eligible_count": 0,
        "rejected_count": 0,
        "evaluated_count": 0,
        "rejections": [],
        "rejection_reason_counts": [],
        "sample_truncated": False,
    }
    normalized_staffing = receipts._normalize_staffing(
        {
            "status": "bad value",
            "units": [
                None,
                {
                    "unit_id": "unit-build",
                    "nominated_ids": [f"candidate-{index}" for index in range(8)],
                    "proposed_ids": "invalid",
                    "reason_codes": [f"reason-{index}" for index in range(12)],
                },
            ],
            "global_reason_codes": [f"global-{index}" for index in range(12)],
            "truncated": True,
        }
    )
    assert normalized_staffing["status"] == "unavailable"
    assert len(normalized_staffing["units"][0]["nominated_ids"]) == 4
    assert len(normalized_staffing["units"][0]["reason_codes"]) == 8
    assert len(normalized_staffing["global_reason_codes"]) == 8
    assert normalized_staffing["gap_count"] == 1
    assert normalized_staffing["truncated"] is True
    assert (
        receipts._routing_reason_codes(
            {},
            inference_mode="",
            compatibility={"rejection_reason_counts": [None]},
            eligibility={"rejection_reason_counts": [None]},
        )
        == []
    )


def test_routing_receipt_continuation_and_normalization_fail_closed() -> None:
    source = project_durable_routing_receipt({})
    continuation = project_durable_routing_receipt(
        {
            "continuation_reused": True,
            "routing_receipt": source,
            "provider_attempts": [{"provider_name": "must-not-survive"}],
            "inference_required": True,
            "inference_attempted": True,
        }
    )
    assert continuation["inference"] == {
        "configured": False,
        "required": False,
        "attempted": False,
        "mode": "durable_reuse",
        "provider_attempts": [],
    }
    assert len(continuation["origin_receipt_digest"]) == 64
    assert normalize_durable_routing_receipt(continuation) == continuation
    continuation_without_origin = project_durable_routing_receipt(
        {"continuation_reused": True, "routing_receipt": {"receipt_version": 999}}
    )
    assert "origin_receipt_digest" not in continuation_without_origin

    assert normalize_durable_routing_receipt(None) is None
    assert (
        normalize_durable_routing_receipt(
            {
                "receipt_version": 1,
                "inference": [],
                "retrieval": {},
                "compatibility": {},
                "eligibility": {},
            }
        )
        is None
    )
    malformed = {
        **source,
        "origin_receipt_digest": "not-a-digest",
        "compatibility": {
            **source["compatibility"],
            "rejection_reason_counts": [
                {"reason_code": "conflict:a", "count": 2},
            ],
        },
        "eligibility": {
            **source["eligibility"],
            "rejections": [{"slug": "agent", "reason_code": "excluded"}],
            "rejection_reason_counts": [],
        },
    }
    normalized = normalize_durable_routing_receipt(malformed)
    assert normalized is not None
    assert "origin_receipt_digest" not in normalized
    assert normalized["compatibility"]["rejection_reason_counts"] == [
        {"reason_code": "conflict", "count": 2}
    ]
    assert normalized["eligibility"]["rejection_reason_counts"] == [
        {"reason_code": "excluded", "count": 1}
    ]


def test_ready_receipt_persists_once_and_drives_the_five_header_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, routing = _ready_store(tmp_path, monkeypatch, trace_id="ready-receipt")
    snapshot = store.get_completion_evidence_snapshot("session", "ready-receipt")
    receipt = store.get_ready_routing_receipt(
        "session",
        "ready-receipt",
        evidence_revision=snapshot["evidence_revision"],
    )
    assert receipt == project_durable_routing_receipt(routing)

    connection = store._connect()
    try:
        stored = json.loads(
            connection.execute(
                "SELECT decision FROM routing_decisions WHERE trace_id = ?",
                ("ready-receipt",),
            ).fetchone()["decision"]
        )["routing_receipt"]
    finally:
        connection.close()
    assert stored == receipt

    fields = fill_header_fields(
        {"why": "invented", "how_it_shaped_outcome": "invented"},
        "session",
        store,
        "task-general",
        "ready-receipt",
        evidence_snapshot=snapshot,
    )
    # AR-224 reduced the header to five factual fields; a caller-supplied
    # narrative is dropped rather than carried into the turn.
    assert set(fields) == {name for name, _label in HEADER_FIELDS}
    assert "why" not in fields
    assert "how_it_shaped_outcome" not in fields
    assert fields["agencies_loaded"] == "agency-steward"
    assert fields["recruited_via"] == "none (declined)"
    # The workforce planner's own receipt is the one model identity a hook can
    # actually observe, so it is the whole line when no launch requested one.
    assert fields["actual_model_selected"].startswith("workforce inference:")
    assert "not observable to Agency" not in fields["actual_model_selected"]

    first = finalize_header(
        "Body",
        "session",
        store,
        "task-general",
        "ready-receipt",
    )
    assert (
        finalize_header(
            first,
            "session",
            store,
            "task-general",
            "ready-receipt",
        )
        == first
    )
    forged = dict(fields, recruited_via="a plausible but unrecorded receipt")
    violation = validate_completion_policy(
        format_header(forged) + "\n\nBody",
        session_id="session",
        trace_id="ready-receipt",
        store=store,
        model="task-general",
    )
    assert violation is not None
    assert violation["missing"] == ["recruited_via"]


def test_ready_receipt_fails_closed_when_its_persisted_twin_is_tampered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _routing_value = _ready_store(tmp_path, monkeypatch, trace_id="tampered-receipt")
    snapshot = store.get_completion_evidence_snapshot("session", "tampered-receipt")
    connection = store._connect()
    try:
        row = connection.execute(
            "SELECT id, decision FROM routing_decisions WHERE trace_id = ?",
            ("tampered-receipt",),
        ).fetchone()
        decision = json.loads(row["decision"])
        decision["routing_receipt"]["effect_codes"] = ["unrecorded_effect"]
        connection.execute(
            "UPDATE routing_decisions SET decision = ? WHERE id = ?",
            (json.dumps(decision, sort_keys=True), row["id"]),
        )
        connection.commit()
    finally:
        connection.close()

    assert (
        store.get_ready_routing_receipt(
            "session",
            "tampered-receipt",
            evidence_revision=snapshot["evidence_revision"],
        )
        is None
    )
    current = store.get_completion_evidence_snapshot("session", "tampered-receipt")
    with pytest.raises(RuntimeError, match="integrity"):
        store.get_ready_routing_receipt(
            "session",
            "tampered-receipt",
            evidence_revision=current["evidence_revision"],
        )
    with pytest.raises(EvidenceCorrelationError, match="routing receipt evidence"):
        fill_header_fields(
            {},
            "session",
            store,
            "task-general",
            "tampered-receipt",
            evidence_snapshot=current,
        )


def test_legacy_ready_recipe_without_receipt_remains_readable_but_reports_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, _routing_value = _ready_store(tmp_path, monkeypatch, trace_id="legacy-receipt")
    connection = store._connect()
    try:
        run = connection.execute(
            "SELECT preflight_result FROM runs WHERE trace_id = ?",
            ("legacy-receipt",),
        ).fetchone()
        recipe = json.loads(run["preflight_result"])
        recipe["routing"].pop("routing_receipt")
        decision_row = connection.execute(
            "SELECT id, decision FROM routing_decisions WHERE trace_id = ?",
            ("legacy-receipt",),
        ).fetchone()
        decision = json.loads(decision_row["decision"])
        decision.pop("routing_receipt")
        connection.execute(
            "UPDATE runs SET preflight_result = ? WHERE trace_id = ?",
            (json.dumps(recipe, sort_keys=True), "legacy-receipt"),
        )
        connection.execute(
            "UPDATE routing_decisions SET decision = ? WHERE id = ?",
            (json.dumps(decision, sort_keys=True), decision_row["id"]),
        )
        connection.execute(
            "DELETE FROM model_receipts WHERE trace_id = ?",
            ("legacy-receipt",),
        )
        connection.commit()
    finally:
        connection.close()

    snapshot = store.get_completion_evidence_snapshot("session", "legacy-receipt")
    assert (
        store.get_ready_routing_receipt(
            "session",
            "legacy-receipt",
            evidence_revision=snapshot["evidence_revision"],
        )
        is None
    )
    fields = fill_header_fields(
        {},
        "session",
        store,
        "task-general",
        "legacy-receipt",
        evidence_snapshot=snapshot,
    )
    assert fields["recruited_via"] == "none (no routing receipt)"
    assert fields["actual_model_selected"] == "requested execution alias: task-general"


def test_delegated_header_names_only_the_validated_specialist() -> None:
    assert (
        _delegation_line(
            [
                {
                    "recommended_agent": "recommended-only",
                    "retrieved_specialist_slug": "validated-reviewer",
                    "executed_worker_kind": "subagent",
                    "backend": "codex-native",
                    "status": "completed",
                }
            ]
        )
        == "validated-reviewer via subagent/codex-native"
    )
    assert (
        _delegation_line(
            [
                {
                    "recommended_agent": "recommended-only",
                    "executed_worker_kind": "subagent",
                    "backend": "codex-native",
                    "status": "completed",
                }
            ]
        )
        == "none - executed worker has no validated Agency specialist"
    )
