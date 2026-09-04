"""AR-383 / ADR-0208: the inferred subject rides beside the turn context, and a refused projection says why.

ADR-0197 supplied a typed work subject on turns whose wording retrieval could
not read, and merged it into the projected turn context. On a fresh turn that
context is empty, so the merge produced a single-key mapping that the
context projection refuses; every turn that ran the subject stage lost dense
recall as ``dense_recall_projection_invalid`` with the exception discarded
(17 of 17 on the 2026-09-03 smoke). These cases pin the replacement: the
context stays the empty projection, the subject reaches the planner document,
the per-unit recall query and the recruiter document beside it, and a refused
projection names the validation that refused it with a closed code that the
receipts keep.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from agency_runtime.core.preflight_failure import _project_validation_reason_codes
from agency_runtime.core.turn_routing_context import (
    TURN_ROUTING_CONTEXT_REJECTION_CODES,
    project_turn_routing_context,
    turn_routing_context_rejection,
)
from agency_runtime.core.workforce import inference as workforce_inference
from agency_runtime.core.workforce.hybrid_recall import (
    RecallProjectionError,
    clear_hybrid_recall_cache,
    project_unit_query,
)
from agency_runtime.core.workforce.inference import _RECRUITER_SYSTEM, plan_and_staff_workforce
from agency_runtime.core.workforce.intent import COMPACT_INTENT_SYSTEM
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan
from tests.test_workforce_inference import (
    _compact_plan_document,
    _context,
    _hybrid_config,
    _hybrid_recall_snapshot,
    _nomination_document,
    _plan_document,
    _result,
    _semantic_embedding_response,
)

_HINTS = {
    "domains": ["software-engineering"],
    "languages": ["python"],
    "frameworks": [],
    "capability_ids": ["analysis"],
    "platforms": ["linux"],
}


def test_a_fresh_turn_s_context_stays_projectable_and_the_subject_rides_beside() -> None:
    # The captured shape: the hints alone, in the context's place, are refused.
    merged = {"workforce_subject_hints": _HINTS}
    assert project_turn_routing_context(merged) is None
    assert turn_routing_context_rejection(merged) == "turn_routing_context_shape_invalid"
    # The fresh turn's context is the empty projection, which projects.
    assert project_turn_routing_context({}) == {}
    assert turn_routing_context_rejection({}) == ""


def test_every_refusal_has_a_closed_code() -> None:
    valid = {
        "context_version": 1,
        "source_trace_id": "trace-1",
        "source_status": "completed",
        "source_turn_kind": "new_intent",
        "specialists": [],
        "workforce_unit_descriptors": [],
        "workforce_subject_hints": {},
    }
    assert project_turn_routing_context(valid) is not None
    assert turn_routing_context_rejection(valid) == ""
    cases = {
        "turn_routing_context_shape_invalid": {**valid, "extra": 1},
        "turn_routing_context_version_invalid": {**valid, "context_version": 99},
        "turn_routing_context_source_trace_invalid": {**valid, "source_trace_id": ""},
        "turn_routing_context_source_status_invalid": {**valid, "source_status": "Not Valid!"},
        "turn_routing_context_source_turn_kind_invalid": {**valid, "source_turn_kind": "nope"},
        "turn_routing_context_subject_hints_invalid": {**valid, "workforce_subject_hints": ["x"]},
    }
    for code, value in cases.items():
        assert project_turn_routing_context(value) is None, code
        assert turn_routing_context_rejection(value) == code
        assert code in TURN_ROUTING_CONTEXT_REJECTION_CODES


def test_the_typed_subject_reaches_the_per_unit_recall_query() -> None:
    plan = parse_work_unit_plan(_plan_document())
    unit = plan.units[0]
    bare = project_unit_query(plan, unit, {})
    with_subject = project_unit_query(plan, unit, {}, inferred_subject=_HINTS)
    assert "context subject domains: software-engineering" in with_subject.text
    assert "context subject languages: python" in with_subject.text
    assert "software-engineering" not in bare.text or bare.text != with_subject.text
    assert with_subject.context_revision != bare.context_revision
    assert bare.context_revision == ""
    # A prior turn's own subject is never overwritten by the inferred one.
    prior = {
        "context_version": 1,
        "source_trace_id": "trace-1",
        "source_status": "completed",
        "source_turn_kind": "new_intent",
        "specialists": [],
        "workforce_unit_descriptors": [],
        "workforce_subject_hints": {**_HINTS, "domains": ["data"]},
    }
    kept = project_unit_query(plan, unit, prior, inferred_subject=_HINTS)
    assert "context subject domains: data" in kept.text


def test_a_refused_projection_names_the_validation_on_the_attempt_and_the_receipt() -> None:
    plan = parse_work_unit_plan(_plan_document())
    with pytest.raises(RecallProjectionError) as caught:
        project_unit_query(plan, plan.units[0], {"workforce_subject_hints": _HINTS})
    assert caught.value.reason_code == "turn_routing_context_shape_invalid"

    clear_hybrid_recall_cache()
    snapshot = _hybrid_recall_snapshot()
    _recall, _reranked, attempts = workforce_inference._run_hybrid_recall(
        plan=plan,
        typed_recall=[{"unit_id": plan.units[0].unit_id, "candidates": []}],
        snapshot=snapshot,
        config=_hybrid_config(),
        context=_context(),
        invoker=lambda *_a, **_k: None,
        embedding_invoker=_semantic_embedding_response,
        turn_routing_context={"workforce_subject_hints": _HINTS},
    )
    assert [attempt.stage for attempt in attempts] == ["recall_embedding"]
    assert attempts[0].status == "skipped"
    assert attempts[0].reason_code == "dense_recall_projection_invalid"
    assert attempts[0].validation_reason_codes == ("turn_routing_context_shape_invalid",)
    # The receipt keeps the closed code for a recall stage and drops anything else.
    assert _project_validation_reason_codes(
        ["turn_routing_context_shape_invalid"], stage="recall_embedding"
    ) == ["turn_routing_context_shape_invalid"]
    assert _project_validation_reason_codes(["made-up"], stage="recall_embedding") == []


def test_an_unreadable_request_keeps_dense_recall_and_both_documents_carry_the_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_hybrid_recall_cache()
    monkeypatch.setattr(
        workforce_inference,
        "infer_work_subject_hints",
        lambda *_args, **_kwargs: (dict(_HINTS), []),
    )
    snapshot = _hybrid_recall_snapshot()
    documents: list[dict[str, Any]] = []
    query_texts: list[str] = []

    def embed(texts: tuple[str, ...]):
        query_texts.extend(text for text in texts if text.startswith("unit identity:"))
        return _semantic_embedding_response(texts)

    def invoke(_provider, prompt, _schema, **_kwargs):
        payload = json.loads(prompt)
        documents.append(payload)
        if "planning_taxonomy" in payload:
            return _result(_compact_plan_document())
        if payload.get("recall_policy") == "deterministic_candidate_recall_only":
            candidate_ids = [item["agent_id"] for item in payload["units"][0]["candidates"]]
            return _result(
                {"units": [{"unit_id": "unit-analyze", "ranked_candidate_ids": candidate_ids}]}
            )
        return _result(_nomination_document("zz-vector-specialist"))

    outcome = plan_and_staff_workforce(
        "install this: https://example.test/tool",
        snapshot,
        config=_hybrid_config(),
        context=_context(),
        invoker=invoke,
        embedding_invoker=embed,
        subject_inference_required=True,
    )

    assert outcome.accepted
    stages = [(attempt.stage, attempt.status, attempt.reason_code) for attempt in outcome.attempts]
    assert ("recall_embedding", "skipped", "dense_recall_projection_invalid") not in stages
    assert any(stage == "recall_embedding" and status == "applied" for stage, status, _ in stages)
    planner = next(document for document in documents if "planning_taxonomy" in document)
    recruiter = next(document for document in documents if "detail_cards" in document)
    assert planner["inferred_work_subject"] == _HINTS
    assert recruiter["inferred_work_subject"] == _HINTS
    assert "correlated_turn_context" not in planner
    assert "correlated_turn_context" not in recruiter
    assert query_texts and all(
        "context subject domains: software-engineering" in t for t in query_texts
    )


def test_both_prompts_read_the_inferred_subject_as_evidence_only() -> None:
    for prompt in (_RECRUITER_SYSTEM, COMPACT_INTENT_SYSTEM):
        assert "inferred_work_subject" in prompt
        assert "typed subject the runtime classified for this request" in prompt
