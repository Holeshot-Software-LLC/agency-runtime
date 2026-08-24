"""State-aware external-turn classification contracts."""

from __future__ import annotations

import json
from hashlib import sha256

import pytest

from agency_runtime.core import preflight as preflight_module
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.preflight import run_preflight
from agency_runtime.core.selector import pipeline as selector_pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.turn_intent import (
    MAX_REASON_CODE_CHARS,
    MAX_REASON_CODES,
    TURN_CLASSIFIER_VERSION,
    TURN_KINDS,
    TurnClassification,
    TurnState,
    authoritative_turn_classification,
    classify_pending_interaction,
    classify_turn_intent,
    force_fresh_turn_reroute,
    is_pure_acknowledgement,
)
from agency_runtime.core.turn_routing_context import (
    turn_routing_context_from_recipe,
    turn_routing_context_revision,
    workforce_subject_hints_from_plan,
)


def _active_state(**overrides: object) -> TurnState:
    values: dict[str, object] = {
        "previous_trace_id": "turn-42",
        "state_known": True,
        "previous_status": "abandoned",
        "previous_turn_kind": "new_intent",
        "active_plan": True,
        "unfinished_work": True,
        "configuration_revision": "config-7",
        "roster_revision": "roster-12",
    }
    values.update(overrides)
    return TurnState.from_mapping(values)


def _empty_state() -> TurnState:
    return TurnState.from_mapping({"state_known": True, "roster_revision": "roster-12"})


def test_short_real_intent_never_uses_a_character_count_bypass() -> None:
    decision = classify_turn_intent("fix auth")

    assert decision.turn_kind == "new_intent"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.legacy_request_kind == "nontrivial"


def test_contextual_yes_is_a_correlated_continuation() -> None:
    state = _active_state(
        active_plan=False,
        unfinished_work=False,
        pending_authorization=True,
    )

    decision = classify_turn_intent("yes", state)

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "turn-42"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert "continuation_reply_requires_reroute" in decision.reason_codes
    assert "pending_authorization" in state.as_dict()


def test_detailed_authorization_response_is_a_correlated_continuation() -> None:
    state = _active_state(
        active_plan=False,
        unfinished_work=False,
        pending_authorization=True,
    )

    decision = classify_turn_intent("I approve the release.", state)

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "turn-42"
    assert decision.reroute_required is True
    assert "authorization_response" in decision.reason_codes
    assert "continuation_reply_requires_reroute" in decision.reason_codes


def test_continue_with_active_work_cannot_be_downgraded_to_acknowledgement() -> None:
    decision = classify_turn_intent("continue", _active_state())

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "turn-42"
    assert is_pure_acknowledgement("continue", _active_state()) is False


def test_acknowledgement_during_unfinished_work_is_a_continuation() -> None:
    decision = classify_turn_intent("thanks", _active_state())

    assert decision.turn_kind == "continuation"
    assert decision.selection_required is True
    assert "acknowledgement_cannot_bypass_active_state" in decision.reason_codes


def test_ambiguous_short_reply_without_state_routes_conservatively() -> None:
    for message in ("yes", "continue", "go", "ship it", "review it"):
        decision = classify_turn_intent(message)
        assert decision.turn_kind == "new_intent"
        assert decision.selection_required is True
        assert decision.reroute_required is True


def test_only_a_pure_ack_without_pending_state_bypasses_selection() -> None:
    decision = classify_turn_intent("thanks", _empty_state())

    assert decision.turn_kind == "acknowledgement"
    assert decision.selection_required is False
    assert decision.execution_decision_required is False
    assert decision.legacy_request_kind == "trivial"
    assert is_pure_acknowledgement("thanks", _empty_state()) is True
    assert is_pure_acknowledgement("thanks") is False

    pending = classify_turn_intent("thanks", _active_state(pending_question=True))
    assert pending.turn_kind == "continuation"
    assert pending.selection_required is True


def test_social_conversation_is_distinct_from_acknowledgement_and_real_questions() -> None:
    social = classify_turn_intent("hello", _empty_state())
    question = classify_turn_intent("what do you think about auth?", _empty_state())

    assert social.turn_kind == "conversation"
    assert social.selection_required is False
    assert social.reroute_required is False
    assert social.execution_decision_required is False
    assert "no_pending_state" in social.reason_codes
    assert question.turn_kind == "new_intent"
    assert question.selection_required is True


@pytest.mark.parametrize(
    "message",
    (
        "what's next?",
        "what's the status?",
        "where do we stand?",
        "anything else?",
        "ok so what now?",
        "what should we focus on next?",
        "what should happen next?",
        "what do you recommend next?",
        "what is the next best step?",
        "where should we go from here?",
        "what is the plan?",
        "what remains?",
        "what are our options?",
        "how should we proceed?",
        "what do you think?",
        "any recommendations?",
        "next steps?",
        "options?",
        "priorities?",
        "where are we at?",
        "where do things stand?",
        "what do you suggest?",
        "any suggestions?",
    ),
)
def test_contextual_work_inquiries_select_fresh_read_only_expertise(message: str) -> None:
    decision = classify_turn_intent(message, _empty_state())

    assert decision.turn_kind == "conversation"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is False
    assert decision.legacy_request_kind == "nontrivial"
    assert "contextual_work_inquiry" in decision.reason_codes
    assert "fresh_read_only_expertise" in decision.reason_codes


def test_contextual_work_inquiry_correlates_active_work_but_routes_fresh() -> None:
    decision = classify_turn_intent("what should happen next?", _active_state())

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "turn-42"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is False
    assert "active_state" in decision.reason_codes

    for pending_state in (
        _active_state(
            active_plan=False,
            unfinished_work=False,
            pending_question=True,
        ),
        _active_state(
            active_plan=False,
            unfinished_work=False,
            pending_authorization=True,
        ),
    ):
        pending_inquiry = classify_turn_intent("where do we go from here?", pending_state)
        assert pending_inquiry.turn_kind == "continuation"
        assert pending_inquiry.reroute_required is True
        assert pending_inquiry.execution_decision_required is False


def test_contextual_work_inquiry_without_trusted_state_stays_read_only() -> None:
    decision = classify_turn_intent("status", TurnState(state_known=False))

    assert decision.turn_kind == "conversation"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is False
    assert decision.continuation_of == ""
    assert "turn_state_missing" in decision.reason_codes
    assert "contextual_work_inquiry_state_untrusted" in decision.reason_codes


@pytest.mark.parametrize(
    "message",
    (
        "what is the plan?",
        "what remains?",
        "what are our options?",
        "how should we proceed?",
        "what do you think?",
        "any recommendations?",
        "next steps?",
        "options?",
        "priorities?",
        "where are we at?",
        "where do things stand?",
        "what do you suggest?",
        "any suggestions?",
    ),
)
def test_structural_advisory_forms_stay_read_only_in_every_state(message: str) -> None:
    current = classify_turn_intent(message, _empty_state())
    active = classify_turn_intent(message, _active_state())
    missing = classify_turn_intent(message, TurnState(state_known=False))

    assert current.turn_kind == "conversation"
    assert current.selection_required is True
    assert current.reroute_required is True
    assert current.execution_decision_required is False
    assert active.turn_kind == "continuation"
    assert active.continuation_of == "turn-42"
    assert active.selection_required is True
    assert active.reroute_required is True
    assert active.execution_decision_required is False
    assert missing.turn_kind == "conversation"
    assert missing.selection_required is True
    assert missing.reroute_required is True
    assert missing.execution_decision_required is False


@pytest.mark.parametrize(
    "message",
    (
        "what's next in pipeline.py that needs changing?",
        "can you fix pipeline.py?",
        "please change the configuration",
        "run the tests now",
        "could you deploy the service?",
        "review this diff",
        "do that next",
        "do the next step",
        "would you do that next?",
        "could you work on that next?",
        "can you proceed with the plan?",
        "can you go on?",
    ),
)
def test_action_bearing_requests_keep_execution_authority(message: str) -> None:
    decision = classify_turn_intent(message, _empty_state())

    assert decision.turn_kind == "new_intent"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is True


@pytest.mark.parametrize(
    "message",
    (
        "do that next",
        "would you do that next?",
        "could you work on that next?",
        "can you proceed with the plan?",
        "can you go on?",
    ),
)
def test_contextual_action_requests_stay_executable_in_every_state(message: str) -> None:
    for state in (_empty_state(), _active_state(), TurnState(state_known=False)):
        decision = classify_turn_intent(message, state)
        assert decision.selection_required is True
        assert decision.reroute_required is True
        assert decision.execution_decision_required is True


def test_exact_runtime_control_is_not_confused_with_general_control_language() -> None:
    for command in (
        "agency status",
        "/agency on",
        "agency runtime off",
    ):
        decision = classify_turn_intent(command)
        assert decision.turn_kind == "control"
        assert decision.selection_required is False
        assert decision.confidence == 1.0

    for unmatched in (
        "stop",
        "ping",
        "heartbeat",
        "agency ping",
        "agency status!",
        "agency on.",
        "/agency runtime off!",
        "please check agency status",
    ):
        decision = classify_turn_intent(unmatched)
        assert decision.turn_kind == "new_intent"
        assert decision.selection_required is True


def test_requirement_change_during_active_work_is_a_revision() -> None:
    decision = classify_turn_intent("actually, support Linux too", _active_state())

    assert decision.turn_kind == "revision"
    assert decision.continuation_of == "turn-42"
    assert decision.selection_required is True
    assert decision.reroute_required is True


def test_pending_question_accepts_a_detailed_answer_as_continuation() -> None:
    state = _active_state(
        active_plan=False,
        unfinished_work=False,
        pending_question=True,
    )

    decision = classify_turn_intent("Use PostgreSQL with the existing schema.", state)

    assert decision.turn_kind == "continuation"
    assert decision.continuation_of == "turn-42"
    assert decision.reroute_required is True
    assert "question_response" in decision.reason_codes
    assert "continuation_reply_requires_reroute" in decision.reason_codes


def test_detailed_continuation_routes_fresh_instead_of_reusing_prior_selection() -> None:
    state = _active_state(
        active_plan=False,
        unfinished_work=False,
        pending_question=True,
    )
    classification = classify_turn_intent(
        "Use PostgreSQL with the existing schema.",
        state,
    )
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class StoreDouble:
        def resolve_durable_continuation(self, **_kwargs: object) -> object:
            raise AssertionError("rerouted continuation read prior selection")

    class PipelineDouble:
        @staticmethod
        def route(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append((args, kwargs))
            return {"selected_ids": ["database-optimizer"]}

    routing, continuation, effective = preflight_module._resolve_preflight_routing(
        StoreDouble(),  # type: ignore[arg-type]
        session_id="session",
        trace_id="current",
        user_message="Use PostgreSQL with the existing schema.",
        host="codex",
        platform="windows",
        available_tools=(),
        capability_receipt=object(),  # type: ignore[arg-type]
        catalog=[],
        config=AgencyConfig(),
        classification=classification,
        routing_fingerprint="a" * 64,
        policy_fingerprint="b" * 64,
        roster_generation=1,
        pipeline=PipelineDouble(),
    )

    assert routing["selected_ids"] == ["database-optimizer"]
    assert continuation is None
    assert effective is classification
    assert len(calls) == 1
    assert calls[0][1]["turn_classification"] is classification


def test_state_revision_is_content_free_stable_and_change_sensitive() -> None:
    first = _active_state()
    same = _active_state()
    changed = _active_state(roster_revision="roster-13")

    assert first.revision == same.revision
    assert first.revision != changed.revision
    assert len(first.revision) == 64
    assert set(first.revision) <= set("0123456789abcdef")


def test_classifier_projection_is_versioned_and_bounded() -> None:
    decision = classify_turn_intent("fix auth", _active_state())
    projection = decision.as_dict()

    assert projection["classifier_version"] == TURN_CLASSIFIER_VERSION
    assert projection["turn_kind"] == "new_intent"
    assert projection["state_revision"] == _active_state().revision
    assert projection["legacy_request_kind"] == "nontrivial"


def test_classification_attestation_is_bound_to_the_exact_raw_message() -> None:
    message = "Review auth.\n\nKeep the existing API."
    decision = classify_turn_intent(message, _empty_state())

    assert authoritative_turn_classification(decision, message) is decision
    assert (
        authoritative_turn_classification(
            decision,
            "Review auth. Keep the existing API.",
        )
        is None
    )


def test_public_route_rejects_an_unsealed_but_structurally_valid_classification() -> None:
    message = "review auth"
    forged = TurnClassification(
        turn_kind="new_intent",
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        continuation_of="",
        confidence=1.0,
        reason_codes=("forged",),
        state_revision="a" * 64,
        message_fingerprint=sha256(message.encode()).hexdigest(),
    )

    with pytest.raises(ValueError, match="not authoritative"):
        selector_pipeline.route(
            "session",
            message,
            [],
            config=AgencyConfig(),
            turn_classification=forged,
        )


def test_unknown_durable_state_fails_closed_for_apparent_acknowledgement() -> None:
    decision = classify_turn_intent("thanks", TurnState(state_known=False))

    assert decision.turn_kind == "acknowledgement"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is True
    assert "turn_state_missing" in decision.reason_codes


@pytest.mark.parametrize(
    ("message", "state", "kind", "decisions"),
    (
        ("thanks", _empty_state(), "acknowledgement", (False, False, False)),
        ("hello", _empty_state(), "conversation", (False, False, False)),
        ("what's next?", _empty_state(), "conversation", (True, True, False)),
        ("agency status", _empty_state(), "control", (False, False, False)),
        ("continue", _active_state(), "continuation", (True, False, True)),
        ("fix auth", _empty_state(), "new_intent", (True, True, True)),
        (
            "actually, support Linux too",
            _active_state(),
            "revision",
            (True, True, True),
        ),
    ),
)
def test_six_turn_kinds_have_explicit_independent_decisions(
    message: str,
    state: TurnState,
    kind: str,
    decisions: tuple[bool, bool, bool],
) -> None:
    decision = classify_turn_intent(message, state)

    assert decision.turn_kind == kind
    assert (
        decision.selection_required,
        decision.reroute_required,
        decision.execution_decision_required,
    ) == decisions


def test_turn_kind_vocabulary_is_closed_and_complete() -> None:
    assert {
        "acknowledgement",
        "conversation",
        "control",
        "continuation",
        "new_intent",
        "revision",
    } == TURN_KINDS


@pytest.mark.parametrize(
    ("state", "reason"),
    (
        (None, "turn_state_missing"),
        ({}, "turn_state_missing"),
        ({"state_known": True, "state_stale": True}, "turn_state_stale"),
        (
            {
                "state_known": True,
                "previous_trace_id": "prior",
                "previous_status": "completed",
                "previous_turn_kind": "new_intent",
                "pending_question": True,
                "pending_authorization": True,
            },
            "turn_state_ambiguous",
        ),
        ({"state_known": "yes"}, "turn_state_corrupt"),
    ),
)
def test_untrusted_state_always_fails_toward_selection(
    state: dict[str, object] | None,
    reason: str,
) -> None:
    decision = classify_turn_intent("thanks", state)

    assert decision.turn_kind == "acknowledgement"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert decision.execution_decision_required is True
    assert decision.continuation_of == ""
    assert reason in decision.reason_codes
    assert is_pure_acknowledgement("thanks", state) is False


@pytest.mark.parametrize(
    ("message", "signal_reason"),
    (
        ("continue", "continuation_without_trusted_state"),
        ("actually, use SQLite", "revision_without_trusted_state"),
        ("fix auth", "requested_question_task_or_output"),
    ),
)
def test_untrusted_state_never_fabricates_continuation_correlation(
    message: str,
    signal_reason: str,
) -> None:
    decision = classify_turn_intent(message)

    assert decision.turn_kind == "new_intent"
    assert decision.continuation_of == ""
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert signal_reason in decision.reason_codes


def test_state_revision_mismatch_is_stale_not_current() -> None:
    original = _empty_state()
    persisted = original.as_dict()
    persisted["roster_revision"] = "roster-13"

    stale = TurnState.from_mapping(persisted)
    decision = classify_turn_intent("thanks", stale)

    assert stale.effective_status == "stale"
    assert stale.safe_for_bypass is False
    assert decision.selection_required is True
    assert "turn_state_stale" in decision.reason_codes


def test_state_projection_round_trips_without_becoming_stale() -> None:
    original = _active_state()
    restored = TurnState.from_mapping(original.as_dict())

    assert restored == original
    assert restored.effective_status == "current"
    assert restored.revision == original.revision


@pytest.mark.parametrize(
    "state",
    (
        {"state_known": True, "active_plan": "true"},
        {"state_known": True, "state_status": "invented"},
        {"state_known": True, "state_stale": "true"},
        {"state_known": True, "state_stale": True, "state_ambiguous": True},
        {"state_known": False, "state_status": "stale"},
        {"state_known": True, "previous_trace_id": 7},
        {
            "state_known": True,
            "previous_trace_id": "prior",
            "previous_status": "active",
            "previous_turn_kind": "invented",
        },
        {"state_known": True, "previous_status": "active"},
        {"state_known": True, "state_status": "current", "state_stale": True},
        {"state_known": True, "state_revision": "not-a-digest"},
    ),
)
def test_corrupt_state_shapes_are_not_coerced_into_current_state(
    state: dict[str, object],
) -> None:
    parsed = TurnState.from_mapping(state)
    decision = classify_turn_intent("hello", parsed)

    assert parsed.effective_status == "corrupt"
    assert parsed.safe_for_bypass is False
    assert decision.turn_kind == "conversation"
    assert decision.selection_required is True
    assert "turn_state_corrupt" in decision.reason_codes


def test_non_mapping_state_is_corrupt() -> None:
    state = TurnState.from_mapping([])  # type: ignore[arg-type]

    assert state.effective_status == "corrupt"
    assert classify_turn_intent("hello", state).selection_required is True


@pytest.mark.parametrize(
    ("state", "status"),
    (
        (TurnState(state_known=True, state_status="invented"), "corrupt"),
        (TurnState(state_known=False, state_status="current"), "corrupt"),
        (TurnState(state_known=True, pending_question=True), "ambiguous"),
        (TurnState(state_known=True, previous_trace_id="prior"), "corrupt"),
        (TurnState(state_known=True, previous_status="active"), "corrupt"),
    ),
)
def test_direct_state_construction_cannot_bypass_structural_validation(
    state: TurnState,
    status: str,
) -> None:
    assert state.effective_status == status
    assert state.safe_for_bypass is False
    assert classify_turn_intent("thanks", state).selection_required is True


def test_reason_codes_and_confidence_are_bounded_at_the_value_object_boundary() -> None:
    decision = TurnClassification(
        turn_kind="new_intent",
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        continuation_of="",
        confidence=float("inf"),
        reason_codes=tuple(f"reason_{index}_{'x' * 100}" for index in range(20)),
        state_revision="a" * 64,
        message_fingerprint="b" * 64,
    )

    assert decision.confidence == 0.0
    assert len(decision.reason_codes) == MAX_REASON_CODES
    assert all(len(reason) <= MAX_REASON_CODE_CHARS for reason in decision.reason_codes)
    assert decision.continuation_of == ""
    assert decision.state_revision == "a" * 64

    invalid = TurnClassification(
        turn_kind="new_intent",
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        continuation_of="",
        confidence="not-a-number",  # type: ignore[arg-type]
        reason_codes=("", "invalid reason!", "valid_reason", "valid_reason"),
        state_revision="a" * 64,
        message_fingerprint="b" * 64,
    )
    assert invalid.confidence == 0.0
    assert invalid.reason_codes == ("valid_reason",)


def test_invalid_turn_kind_is_rejected_at_the_value_object_boundary() -> None:
    with pytest.raises(ValueError, match="turn_kind is invalid"):
        TurnClassification(
            turn_kind="generic",  # type: ignore[arg-type]
            selection_required=True,
            reroute_required=True,
            execution_decision_required=True,
            continuation_of="",
            confidence=1.0,
            reason_codes=("test",),
            state_revision="a" * 64,
            message_fingerprint="b" * 64,
        )


@pytest.mark.parametrize(
    "overrides",
    (
        {"selection_required": 1},
        {"reroute_required": 1},
        {"execution_decision_required": 1},
        {"classifier_version": 999},
        {"state_revision": "invalid"},
        {"message_fingerprint": "invalid"},
        {"turn_kind": "control"},
        {"turn_kind": "continuation"},
    ),
)
def test_turn_classification_rejects_forged_semantic_combinations(
    overrides: dict[str, object],
) -> None:
    values: dict[str, object] = {
        "turn_kind": "new_intent",
        "selection_required": True,
        "reroute_required": True,
        "execution_decision_required": True,
        "continuation_of": "",
        "confidence": 1.0,
        "reason_codes": ("test",),
        "state_revision": "a" * 64,
        "classifier_version": TURN_CLASSIFIER_VERSION,
        "message_fingerprint": "b" * 64,
    }
    values.update(overrides)

    with pytest.raises(ValueError):
        TurnClassification(**values)  # type: ignore[arg-type]


def test_only_a_sealed_classification_can_be_forced_to_fresh_routing() -> None:
    forged = TurnClassification(
        turn_kind="new_intent",
        selection_required=True,
        reroute_required=True,
        execution_decision_required=True,
        continuation_of="",
        confidence=1.0,
        reason_codes=("forged",),
        state_revision="a" * 64,
        message_fingerprint="b" * 64,
    )
    with pytest.raises(ValueError, match="not authoritative"):
        force_fresh_turn_reroute(forged, "test")

    control = classify_turn_intent("agency off")
    fresh = force_fresh_turn_reroute(
        control,
        "adapter_origin_untrusted",
        untrusted_origin=True,
    )
    assert fresh.turn_kind == "new_intent"
    assert fresh.continuation_of == ""
    assert fresh.selection_required is True
    assert fresh.reroute_required is True
    assert fresh.confidence == 0.5

    for bypass in (
        classify_turn_intent("thanks", _empty_state()),
        classify_turn_intent("hello", _empty_state()),
    ):
        forced = force_fresh_turn_reroute(
            bypass,
            "adapter_origin_untrusted",
            untrusted_origin=True,
        )
        assert forced.selection_required is True
        assert forced.reroute_required is True
        assert forced.execution_decision_required is True

    inquiry = classify_turn_intent("what's next?", _empty_state())
    fresh_inquiry = force_fresh_turn_reroute(
        inquiry,
        "adapter_origin_untrusted",
        untrusted_origin=True,
    )
    assert fresh_inquiry.turn_kind == "conversation"
    assert fresh_inquiry.selection_required is True
    assert fresh_inquiry.reroute_required is True
    assert fresh_inquiry.execution_decision_required is False


def test_classifier_v5_adds_advisory_selection_without_rewriting_v4() -> None:
    values = {
        "turn_kind": "conversation",
        "selection_required": True,
        "reroute_required": True,
        "execution_decision_required": False,
        "continuation_of": "",
        "confidence": 1.0,
        "reason_codes": ("test",),
        "state_revision": "a" * 64,
        "message_fingerprint": "b" * 64,
    }

    with pytest.raises(ValueError, match="decision combination"):
        TurnClassification(**values, classifier_version=4)

    projected = TurnClassification(**values, classifier_version=5)
    assert projected.execution_decision_required is False


def test_turn_state_rejects_unknown_previous_kind_and_bounds_labels() -> None:
    state = TurnState.from_mapping(
        {
            "previous_trace_id": "x" * 500,
            "previous_status": "y" * 500,
            "previous_turn_kind": "invented",
            "configuration_revision": "z" * 500,
        }
    )

    assert len(state.previous_trace_id) == 128
    assert len(state.previous_status) == 64
    assert state.previous_turn_kind == ""
    assert len(state.configuration_revision) == 128
    assert state.effective_status == "corrupt"


def test_pending_interaction_projects_questions_without_storing_response_content() -> None:
    question = classify_pending_interaction("Which database should I use?")
    authorization = classify_pending_interaction(
        "I can push the release now. Do you want me to proceed?"
    )
    statement = classify_pending_interaction("The implementation is complete.")

    assert question.kind == "question"
    assert question.pending_question is True
    assert len(question.response_fingerprint) == 64
    assert authorization.kind == "authorization"
    assert authorization.pending_authorization is True
    assert statement.as_dict() == {
        "kind": "",
        "response_fingerprint": "",
        "pending_question": False,
        "pending_authorization": False,
    }


def test_pending_interaction_ignores_the_agency_header() -> None:
    response = "\n".join(
        (
            "Agency/Agencies loaded: agents-orchestrator",
            "Agency/Agencies delegated: none",
            "Skills loaded: none",
            "Actual Model selected: unavailable",
            "Recruited via: inference",
            "Why: routing evidence",
            "How it shaped outcome: bounded",
            "",
            "May I push this change?",
        )
    )

    assert classify_pending_interaction(response).kind == "authorization"


@pytest.mark.parametrize(
    "response",
    (
        "",
        "One line only",
        "a\nb\nc\nd\ne\nQuestion?",
        "a: 1\nb: 2\nc: 3\nd: 4\ne: 5\nf: 6\nQuestion?",
    ),
)
def test_pending_interaction_handles_empty_partial_and_non_header_responses(
    response: str,
) -> None:
    result = classify_pending_interaction(response)

    assert result.kind == ("question" if response.endswith("?") else "")


def test_empty_turn_message_is_rejected() -> None:
    with pytest.raises(ValueError, match="turn message is required"):
        classify_turn_intent("   ", _empty_state())


def test_contextual_reply_without_continuation_state_requires_fresh_routing() -> None:
    decision = classify_turn_intent("yes", _empty_state())

    assert decision.turn_kind == "new_intent"
    assert decision.selection_required is True
    assert decision.reroute_required is True
    assert "ambiguous_reply_without_valid_state" in decision.reason_codes


def test_store_turn_state_tracks_abandoned_active_work_without_prompt_content(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    reservation = store.reserve_session_turn(
        session_id="session",
        trace_id="previous",
        host="codex",
    )
    classification = classify_turn_intent("fix auth")
    store.begin_preflight_attempt(
        session_id="session",
        trace_id="previous",
        reservation_token=reservation["reservation_token"],
        request_fingerprint="a" * 64,
        request_kind=classification.legacy_request_kind,
        host="codex",
        turn_classification=classification.as_dict(),
    )
    store.reserve_session_turn(
        session_id="session",
        trace_id="current",
        host="codex",
    )

    state = store.get_turn_state_context("session", before_trace_id="current")

    assert state["state_known"] is True
    assert state["previous_trace_id"] == "previous"
    assert state["previous_status"] == "abandoned"
    assert state["previous_turn_kind"] == "new_intent"
    assert state["active_plan"] is True
    assert state["unfinished_work"] is True

    connection = store._connect()
    try:
        metadata = connection.execute(
            "SELECT metadata FROM runs WHERE trace_id = 'previous'"
        ).fetchone()["metadata"]
    finally:
        connection.close()
    assert "fix auth" not in str(metadata)


def test_completed_advisory_turn_does_not_mask_older_unfinished_work(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="unfinished",
        session_id="session",
        host="codex",
        metadata={
            "request_kind": "nontrivial",
            "turn_kind": "new_intent",
            "selection_required": True,
            "execution_decision_required": True,
        },
    )
    store.create_run(
        trace_id="advisory",
        session_id="session",
        host="codex",
        metadata={
            "request_kind": "nontrivial",
            "turn_kind": "conversation",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": False,
        },
    )
    connection = store._connect()
    try:
        connection.execute("UPDATE runs SET status = 'completed' WHERE trace_id = 'advisory'")
        connection.commit()
    finally:
        connection.close()

    state = store.get_turn_state_context("session")

    assert state["previous_trace_id"] == "unfinished"
    assert state["active_plan"] is True
    assert state["unfinished_work"] is True
    next_inquiry = classify_turn_intent("what should happen next?", state)
    assert next_inquiry.turn_kind == "continuation"
    assert next_inquiry.continuation_of == "unfinished"
    assert next_inquiry.reroute_required is True
    assert next_inquiry.execution_decision_required is False


def test_context_projection_uses_typed_subject_and_never_prior_request_prose() -> None:
    prior_plan = {
        "request_summary": "SECRET prior user request text",
        "units": [
            {
                "domains": ["software-engineering"],
                "languages": ["python"],
                "frameworks": ["sqlite"],
                "required_capabilities": ["technical-analysis"],
                "platforms": ["windows"],
                "outcome": "Do not retain this prose",
                "resources": ["C:/private/repository/path"],
                "acceptance_evidence": ["hidden acceptance prose"],
            }
        ],
    }

    hints = workforce_subject_hints_from_plan(prior_plan)

    assert hints == {
        "domains": ["software-engineering"],
        "languages": ["python"],
        "frameworks": ["sqlite"],
        "capability_ids": ["technical-analysis"],
        "platforms": ["windows"],
    }
    encoded = json.dumps(hints, sort_keys=True)
    assert "SECRET" not in encoded
    assert "private/repository" not in encoded
    assert "acceptance prose" not in encoded


def test_context_projection_reranks_historical_specialists_without_copying_plan_text() -> None:
    recipe = {
        "selection_refs": [
            {
                "slug": "database-reliability-engineer",
                "description": "Audited database reliability specialist",
                "capabilities": ["sqlite", "recovery"],
            },
            {
                "slug": "unselected-specialist",
                "description": "Must not be projected",
                "capabilities": [],
            },
        ],
        "routing": {
            "selected_ids": ["database-reliability-engineer"],
            "workforce_unit_descriptors": [],
            "workforce_subject_hints": {
                "domains": ["software-engineering"],
                "languages": ["python"],
                "frameworks": ["sqlite"],
                "capability_ids": ["technical-analysis"],
                "platforms": ["windows"],
            },
            "workforce_plan": {"request_summary": "SECRET prior prompt"},
        },
    }

    context = turn_routing_context_from_recipe(
        recipe,
        source_trace_id="prior-turn",
        source_status="completed",
        source_turn_kind="new_intent",
    )

    assert [item["slug"] for item in context["specialists"]] == ["database-reliability-engineer"]
    assert context["workforce_subject_hints"]["frameworks"] == ["sqlite"]
    assert "SECRET prior prompt" not in json.dumps(context)
    assert len(turn_routing_context_revision(context)) == 64


def test_turn_context_is_scoped_to_the_exact_session_and_host(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="codex-subject",
        session_id="session",
        host="codex",
        metadata={"turn_kind": "new_intent", "selection_required": True},
    )
    store.create_run(
        trace_id="other-host-subject",
        session_id="session",
        host="openclaw",
        metadata={"turn_kind": "new_intent", "selection_required": True},
    )
    store.create_run(
        trace_id="other-session-subject",
        session_id="other-session",
        host="codex",
        metadata={"turn_kind": "new_intent", "selection_required": True},
    )

    codex = store.get_turn_state_context("session", host="codex")
    openclaw = store.get_turn_state_context("session", host="openclaw")

    assert codex["previous_trace_id"] == "codex-subject"
    assert codex["turn_routing_context"]["source_trace_id"] == "codex-subject"
    assert openclaw["previous_trace_id"] == "other-host-subject"
    assert openclaw["turn_routing_context"]["source_trace_id"] == "other-host-subject"


def test_pending_authorization_survives_terminal_finalization_and_routes_yes(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(
        trace_id="previous",
        session_id="session",
        host="codex",
        metadata={
            "request_kind": "nontrivial",
            "turn_kind": "new_intent",
            "selection_required": True,
        },
    )
    connection = store._connect()
    try:
        revision = int(
            connection.execute(
                "SELECT evidence_revision FROM runs WHERE trace_id = 'previous'"
            ).fetchone()["evidence_revision"]
        )
    finally:
        connection.close()

    committed = store.commit_terminal_finalization(
        session_id="session",
        trace_id="previous",
        host="codex",
        action="accept",
        response_hash="a" * 64,
        status="completed",
        expected_evidence_revision=revision,
        pending_interaction_kind="authorization",
        pending_interaction_fingerprint="b" * 64,
    )
    assert committed["outcome"] == "committed"

    result = run_preflight(
        store,
        session_id="session",
        user_message="yes",
        host="codex",
        trace_id="current",
    )

    assert result.turn_kind == "continuation"
    assert result.continuation_of == "previous"
    assert result.selection_required is True
    assert result.trivial is False
    assert store.get_turn_request_kind("session", "current") == "nontrivial"

    connection = store._connect()
    try:
        metadata = json.loads(
            connection.execute("SELECT metadata FROM runs WHERE trace_id = 'previous'").fetchone()[
                "metadata"
            ]
        )
    finally:
        connection.close()
    assert metadata["pending_interaction"] == "authorization"
    assert metadata["pending_interaction_fingerprint"] == "b" * 64
