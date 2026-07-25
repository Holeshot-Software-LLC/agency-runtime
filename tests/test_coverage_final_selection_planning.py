"""Close adversarial branch coverage for routing and delegation planning."""

from __future__ import annotations

import io
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import installer_inventory, routing_snapshot, unit_assignment
from agency_runtime.core.config import (
    AgencyConfig,
    DelegationConfig,
    JudgeConfig,
    OllamaConfig,
)
from agency_runtime.core.delegation import backends, events
from agency_runtime.core.installer_contracts import INSTALL_MANIFEST, PLUGIN_ID
from agency_runtime.core.process_argv import PreparedProcessArgv
from agency_runtime.core.selector import (
    explain,
    judge_protocol,
    pipeline,
)
from agency_runtime.core.turn_intent import TurnState, classify_turn_intent


def _offline_config(*, delegation: DelegationConfig | None = None) -> AgencyConfig:
    return AgencyConfig(
        judge=JudgeConfig(model="", base_url=""),
        ollama=OllamaConfig(enabled=False, model=""),
        delegation=delegation or DelegationConfig(),
    )


def _simple_routing() -> dict[str, Any]:
    return {
        "selected_ids": ["technical-writer"],
        "work_units": {
            "delegate": True,
            "count": 1,
            "units": ["Write docs/README.md"],
            "confidence": "high",
            "source": "numbered",
        },
    }


def _legacy_plan() -> dict[str, Any]:
    return {
        "assignment_version": "1",
        "work_unit_id": "unit-1234567890",
        "recommended_agent": "technical-writer",
    }


def test_assignment_candidate_rejects_unknown_and_capacity_overflow() -> None:
    candidates: dict[str, dict[str, Any]] = {}
    unit_assignment._add_assignment_candidate(
        candidates,
        {},
        "missing",
        "unit-1234567890",
        primary=True,
    )
    assert candidates == {}

    candidates.update(
        {
            f"agent-{index}": {"matched_work_unit_ids": [], "primary_work_unit_ids": []}
            for index in range(unit_assignment.MAX_SUGGESTED_WORK_UNITS)
        }
    )
    unit_assignment._add_assignment_candidate(
        candidates,
        {"overflow": {"slug": "overflow"}},
        "overflow",
        "unit-1234567890",
        primary=True,
    )
    assert "overflow" not in candidates


def test_delegation_strength_covers_every_policy_mode() -> None:
    assert (
        unit_assignment._delegation_strength(
            policy=DelegationConfig(mode="observe"),
            unit_count=8,
            confidence=1.0,
        )
        == "optional"
    )
    assert (
        unit_assignment._delegation_strength(
            policy=DelegationConfig(mode="strong"),
            unit_count=1,
            confidence=0.0,
        )
        == "strongly_preferred"
    )
    assert (
        unit_assignment._delegation_strength(
            policy=DelegationConfig(
                mode="prefer",
                strongly_preferred_min_units=2,
                strongly_preferred_min_confidence=0.8,
            ),
            unit_count=2,
            confidence=0.9,
        )
        == "strongly_preferred"
    )


def test_metadata_union_deduplicates_and_stops_at_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = {
        "first": {"required_tools": ["shared"]},
        "second": {
            "required_tools": [
                "SHARED",
                "two",
                "three",
                "four",
                "five",
                "six",
                "seven",
                "eight",
            ]
        },
    }
    monkeypatch.setattr(
        unit_assignment,
        "_metadata_for_agent",
        lambda _routing, slug: metadata[slug],
    )

    result = unit_assignment._metadata_union({}, ["first", "second"], "required_tools")

    assert result == ["shared", "two", "three", "four", "five", "six", "seven", "eight"]


@pytest.mark.parametrize(
    ("value", "digests"),
    [
        ("not-a-list", False),
        ([""], False),
        (["line\nbreak"], False),
        (["not-a-digest"], True),
        (["same", "same"], False),
    ],
)
def test_bounded_plan_strings_rejects_invalid_or_duplicate_values(
    value: Any,
    digests: bool,
) -> None:
    assert unit_assignment._bounded_plan_strings(value, digests=digests) is None


def test_unit_plan_projection_rejects_every_version_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert unit_assignment.project_unit_agent_plan("not-a-plan") is None
    assert unit_assignment.project_unit_agent_plan(["not-a-row"]) is None
    assert (
        unit_assignment.project_unit_agent_plan(
            [{**_legacy_plan(), "assignment_version": "invalid"}]
        )
        is None
    )
    assert unit_assignment.project_unit_agent_plan([_legacy_plan()]) == [_legacy_plan()]
    assert unit_assignment.project_unit_agent_plan([_legacy_plan()], allow_legacy=False) is None

    current = unit_assignment.build_unit_agent_plan(_simple_routing())
    assert len(current) == 1
    missing_field = deepcopy(current[0])
    missing_field.pop("goal_hash")
    assert unit_assignment.project_unit_agent_plan([missing_field]) is None

    invalid_confidence = deepcopy(current[0])
    invalid_confidence["selection_confidence"] = True
    assert unit_assignment.project_unit_agent_plan([invalid_confidence]) is None

    future = deepcopy(current[0])
    future["assignment_version"] = str(unit_assignment.UNIT_AGENT_ASSIGNMENT_VERSION + 1)
    assert unit_assignment.project_unit_agent_plan([future]) is None
    assert unit_assignment.project_unit_agent_plan([_legacy_plan(), current[0]]) is None

    monkeypatch.setattr(unit_assignment, "project_unit_agent_plan", lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError, match="generated unit-agent plan is invalid"):
        unit_assignment.build_unit_agent_plan(_simple_routing())


def test_pipeline_reuse_guards_and_compatibility_abstention() -> None:
    kwargs = {
        "active_ids": {"active"},
        "matched_actions": [],
        "companion_ids": [],
        "available_companion_ids": [],
        "unavailable_companion_ids": [],
        "work_units": {"delegate": False},
    }
    assert (
        pipeline._refresh_reused_routing(
            {"semantic_ids": ["removed"], "selected_ids": ["removed"]},
            **kwargs,
        )
        is None
    )

    result = pipeline._apply_compatible_selection(
        {"selected_ids": ["missing"]},
        [],
    )
    assert result["status"] == "abstained"
    assert result["error"] == "selected specialists failed compatibility constraints"


def test_pipeline_reuses_session_selection_for_a_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _offline_config()
    request = pipeline._RouteRequest(
        session_id="session",
        trace_id="trace",
        user_message="continue",
        catalog=[{"slug": "active"}],
        workforce_catalog=[{"slug": "active"}],
        config=config,
        policy={},
        context_fingerprint="fingerprint",
        routing_query="continue",
        cache_key="key",
        source_message_hash="current",
        active_ids=frozenset({"active"}),
    )
    signals = pipeline._RouteSignals(
        policy_validation={"valid": True, "errors": [], "enabled_slugs": [], "disabled_count": 0},
        matched_actions=[],
        companion_ids=[],
        available_companion_ids=[],
        unavailable_companion_ids=[],
        work_units={"delegate": False},
    )
    continuation = classify_turn_intent(
        "continue",
        TurnState(
            previous_trace_id="prior-trace",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=True,
        ),
    )
    monkeypatch.setattr(pipeline, "_route_request", lambda *_args, **_kwargs: request)
    monkeypatch.setattr(pipeline, "_route_signals", lambda _request: signals)
    monkeypatch.setattr(pipeline, "cache_get", lambda _key: None)
    monkeypatch.setattr(
        pipeline,
        "session_check",
        lambda *_args, **_kwargs: {
            "selected_ids": ["active"],
            "semantic_ids": ["active"],
            "session_reused": True,
        },
    )

    result = pipeline.route(
        "session",
        "continue",
        request.catalog,
        config=config,
        turn_classification=continuation,
    )

    assert result["selected_ids"] == ["active"]
    assert result["session_reused"] is True


def test_pipeline_discards_an_exact_but_nonreusable_cache_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _offline_config()
    request = pipeline._RouteRequest(
        session_id="session",
        trace_id="trace",
        user_message="continue",
        catalog=[{"slug": "active"}],
        workforce_catalog=[{"slug": "active"}],
        config=config,
        policy={},
        context_fingerprint="fingerprint",
        routing_query="continue",
        cache_key="key",
        source_message_hash="current",
        active_ids=frozenset({"active"}),
    )
    signals = pipeline._RouteSignals(
        policy_validation={"valid": True, "errors": [], "enabled_slugs": [], "disabled_count": 0},
        matched_actions=[],
        companion_ids=[],
        available_companion_ids=[],
        unavailable_companion_ids=[],
        work_units={"delegate": False},
    )
    continuation = classify_turn_intent(
        "continue",
        TurnState(
            previous_trace_id="prior-trace",
            state_known=True,
            state_status="current",
            previous_status="active",
            previous_turn_kind="new_intent",
            active_plan=True,
        ),
    )
    stale_fallback = {
        "source_message_hash": "current",
        "selected_ids": ["active"],
        "semantic_ids": ["active"],
        "fallback_applied": True,
    }
    monkeypatch.setattr(pipeline, "_route_request", lambda *_args, **_kwargs: request)
    monkeypatch.setattr(pipeline, "_route_signals", lambda _request: signals)
    monkeypatch.setattr(pipeline, "cache_get", lambda _key: stale_fallback)
    monkeypatch.setattr(pipeline, "session_check", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        pipeline,
        "query_judge",
        lambda *_args, **_kwargs: {
            "selected_ids": ["active"],
            "confidence": 1.0,
            "status": "selected",
        },
    )
    monkeypatch.setattr(pipeline, "_remember_routing", lambda *_args, **_kwargs: None)

    result = pipeline.route(
        "session",
        "continue",
        request.catalog,
        config=config,
        turn_classification=continuation,
    )

    assert result["selected_ids"] == ["active"]
    assert result["status"] == "selected"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("observe", "OBSERVE ONLY"),
        ("strong", "STRONGLY PREFER"),
    ],
)
def test_routing_context_exposes_delegation_policy(mode: str, expected: str) -> None:
    context = pipeline.build_routing_context(
        {
            "selected_ids": ["reviewer"],
            "confidence": 1.0,
            "status": "selected",
            "work_units": {
                "delegate": True,
                "count": 2,
                "units": ["Review API", "Review UI"],
                "confidence": "high",
                "source": "numbered",
            },
        },
        _offline_config(delegation=DelegationConfig(mode=mode)),
    )

    assert expected in context


def test_judge_candidate_bounds_cover_zero_duplicate_and_overflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert judge_protocol._bounded_card_text("value", 0) == ""
    assert judge_protocol._bounded_card_list(
        ["", "same", "same", "other"],
        maximum_items=4,
        item_bytes=16,
    ) == ["same", "other"]

    monkeypatch.setattr(judge_protocol, "_MAX_CANDIDATE_CARD_BYTES", 1)
    with pytest.raises(ValueError, match="candidate card exceeded"):
        judge_protocol._candidate_card_json({"slug": "reviewer"})


def test_explain_handles_no_selection_and_invalid_diagnostic_receipt() -> None:
    explanation = explain.explain_route(
        "session",
        "agency off",
        [],
        config=_offline_config(),
        trace_id="trace",
    )
    assert explanation["considered_candidates"] == []

    with pytest.raises(ValueError, match="capability receipt is invalid"):
        explain.explain_route(
            "session",
            "review the API",
            [],
            config=_offline_config(),
            capability_receipt={},
        )


def _frozen_argv(identity: object) -> PreparedProcessArgv:
    argv = PreparedProcessArgv(["agent", "--one-shot"], artifact_paths=("agent",))
    argv.executable_identities = (identity,)  # type: ignore[assignment]
    return argv


def test_owned_process_revalidates_prefrozen_identity_and_rejects_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_identity = object()
    argv = _frozen_argv(original_identity)
    observed: list[PreparedProcessArgv] = []
    monkeypatch.setattr(backends, "revalidate_process_argv", observed.append)

    changed = _frozen_argv(object())
    monkeypatch.setattr(backends, "freeze_process_argv", lambda *_args, **_kwargs: changed)
    with pytest.raises(OSError, match="identity changed"):
        backends._run_owned_process(
            argv,
            cwd=None,
            env={},
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
            forbidden_roots=("workspace",),
        )
    assert observed == [argv]

    verified = _frozen_argv(original_identity)
    monkeypatch.setattr(backends, "freeze_process_argv", lambda *_args, **_kwargs: verified)
    monkeypatch.setattr(
        backends,
        "_spawn_owned_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("stop after freeze")),
    )
    with pytest.raises(RuntimeError, match="stop after freeze"):
        backends._run_owned_process(
            argv,
            cwd=None,
            env={},
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
            forbidden_roots=("workspace",),
        )

    monkeypatch.setattr(
        backends,
        "freeze_process_argv",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected refreeze")),
    )
    with pytest.raises(RuntimeError, match="stop after freeze"):
        backends._run_owned_process(
            argv,
            cwd=None,
            env={},
            stdout=io.StringIO(),
            stderr=io.StringIO(),
            timeout=1,
        )


def test_delegation_identity_prefers_explicit_work_unit() -> None:
    rows = [
        {"work_unit_id": "unit-1234567890"},
        {"work_unit_id": "unit-abcdefghij"},
    ]
    assert events._matching_work_unit_identity(
        rows,
        work_unit_id="unit-abcdefghij",
        goal="",
        count=1,
    ) == [rows[1]]

    goal = "Review the dashboard"
    goal_row = {"work_unit_id": unit_assignment.work_unit_id_from_text(goal)}
    assert events._matching_work_unit_identity(
        [goal_row],
        work_unit_id="unit-doesnotmatch",
        goal=goal,
        count=1,
    ) == [goal_row]


@pytest.mark.parametrize(
    "snapshot",
    [
        {"catalog": {}, "generation": 0},
        {"catalog": [], "generation": True},
        {"catalog": [], "generation": -1},
    ],
)
def test_routing_snapshot_rejects_malformed_atomic_store_values(snapshot: dict[str, Any]) -> None:
    store = SimpleNamespace(
        get_routing_roster_snapshot=lambda **_kwargs: snapshot,
    )
    with pytest.raises(RuntimeError, match="snapshot is malformed"):
        routing_snapshot.capture_routing_snapshot(store, _offline_config())


def test_launcher_inventory_requires_artifact_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": PLUGIN_ID,
    }
    monkeypatch.setattr(
        installer_inventory,
        "_read_regular_file_bounded",
        lambda path, **_kwargs: (
            json.dumps(manifest).encode("utf-8") if Path(path).name == INSTALL_MANIFEST else b""
        ),
    )

    assert installer_inventory._managed_launcher_artifacts_current(tmp_path, "codex") is None
