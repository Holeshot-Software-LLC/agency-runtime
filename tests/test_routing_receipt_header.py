"""Durable routing-receipt and evidence-faithful header regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config import AgencyConfig, OllamaConfig
from agency_runtime.core.header.contract import (
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
) -> tuple[Store, dict[str, Any]]:
    store = Store(tmp_path / f"{trace_id}.db")
    message = "Audit the routing evidence boundary."
    routing = _routing(message, trace_id)
    monkeypatch.setattr(pipeline, "route", lambda *_args, **_kwargs: routing)
    run_preflight(
        store,
        session_id="session",
        user_message=message,
        host="codex",
        trace_id=trace_id,
        config=AgencyConfig(ollama=OllamaConfig(enabled=False, model="")),
    )
    return store, routing


def test_routing_receipt_is_bounded_content_free_and_idempotent() -> None:
    routing = _routing("Audit evidence.", "trace")
    secret = "TOP-SECRET-PROMPT-BODY"
    routing["provider_attempts"].append(
        {
            "provider_name": secret,
            "provider_type": "openai-compatible",
            "requested_model": f"sk-{secret}",
            "status": "failed\nINJECT",
            "reason": f"credential={secret}",
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
    assert "INJECT" not in json.dumps(receipt)
    assert normalize_durable_routing_receipt({"receipt_version": 999}) is None


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


def test_ready_receipt_persists_once_and_drives_all_six_header_fields(
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
    assert "substantive answer or action" in fields["why"]
    assert "required capabilities" in fields["why"]
    assert "Agency attempted inference" in fields["how_it_shaped_outcome"]
    assert "eligibility exclusions were applied" in fields["how_it_shaped_outcome"]
    assert fields["actual_model_selected"].startswith(
        "parent task: host-selected (not observable to Agency); workforce inference:"
    )
    assert fields["actual_model_selected"].endswith("specialist: not launched")

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
    forged = dict(fields, why="a plausible but unrecorded explanation")
    violation = validate_completion_policy(
        format_header(forged) + "\n\nBody",
        session_id="session",
        trace_id="ready-receipt",
        store=store,
        model="task-general",
    )
    assert violation is not None
    assert violation["missing"] == ["why"]


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
    assert "substantive answer or action" in fields["why"]
    assert fields["how_it_shaped_outcome"] == (
        "Unavailable - no authoritative routing effect was recorded for this turn."
    )


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
