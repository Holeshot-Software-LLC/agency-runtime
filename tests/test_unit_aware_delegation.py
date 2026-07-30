"""Focused coverage for unit-aware delegation planning."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core import preflight as preflight_module
from agency_runtime.core import preflight_recipe
from agency_runtime.core.delegation.events import (
    MAX_SUGGESTED_WORK_UNITS,
    UNIT_AGENT_ASSIGNMENT_VERSION,
    build_unit_agent_plan,
    record_suggested_delegations,
    work_unit_id_from_text,
)
from agency_runtime.core.delegation.native_labels import (
    CODEX_TASK_NAME_PATTERN,
    codex_task_name_for_work_unit,
    internal_work_unit_from_codex_task_name,
)
from agency_runtime.core.header.contract import (
    fill_header_fields,
    format_header,
    validate_completion_policy,
)
from agency_runtime.core.resident_manager_binding import build_resident_manager_binding
from agency_runtime.core.selector.delegation_detection import (
    WORK_UNIT_DETECTION_VERSION,
    _imperative_units,
    detect_work_units,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
    assignment_agents_from_catalog,
    project_unit_assignment_agents,
)
from agency_runtime.server.mcp import handle_tool_call


@pytest.mark.parametrize("verb", ["improve", "redesign", "harden", "enhance", "secure"])
def test_action_verbs_remain_visible_to_work_unit_detection(verb: str) -> None:
    result = detect_work_units(f"1. {verb} the API\n2. update the README")

    assert result["version"] == WORK_UNIT_DETECTION_VERSION
    assert result["units"][0] == f"{verb} the API"
    assert result["delegate"] is True


def test_dependency_language_is_scoped_to_the_unit_that_contains_it() -> None:
    internal_dependency = detect_work_units(
        "1. Migrate the database after taking a backup\n2. Improve the dashboard\n3. Secure the API"
    )
    mixed_dependency = detect_work_units(
        "1. Build the API\n2. Then test the API\n3. Document the API"
    )
    fully_sequential = detect_work_units(
        "1. Build the API\n2. Then test the API\n3. After that deploy the API"
    )

    assert internal_dependency["delegate"] is True
    assert internal_dependency["confidence"] == "high"
    assert mixed_dependency["delegate"] is False
    assert mixed_dependency["confidence"] == "medium"
    assert fully_sequential["delegate"] is False
    assert fully_sequential["confidence"] == "medium"


def test_mixed_numbered_dependencies_are_not_advertised_as_parallel() -> None:
    result = detect_work_units("1 Implement API\n2 After that test\n3 Document")

    assert result["units"] == ["Implement API", "After that test", "Document"]
    assert result["delegate"] is False
    assert result["confidence"] == "medium"


def test_long_imperatives_with_the_same_prefix_remain_distinct() -> None:
    shared = (
        "review the generated cross-platform compatibility matrix for every "
        "supported native host and report "
    )

    units = _imperative_units(f"{shared}Windows-specific failures; {shared}Linux-specific failures")

    assert len(units) == 2
    assert units[0].endswith("Windows-specific failures")
    assert units[1].endswith("Linux-specific failures")


def test_isolated_hydration_uses_every_unique_planned_agent() -> None:
    routing = {"selected_ids": ["original"]}
    suggestions = [
        {
            "work_unit_id": "unit-a",
            "recommended_agent": "writer",
            "recommended_agents": ["writer", "reviewer"],
        },
        {"work_unit_id": "unit-b", "recommended_agent": "writer"},
        {"work_unit_id": "unit-c", "recommended_agent": "orchestrator"},
    ]

    assert (
        preflight_module._specialist_hydration_routing(
            routing,
            delivery_mode="direct",
            suggestions=suggestions,
        )
        is routing
    )
    assert (
        preflight_module._specialist_hydration_routing(
            routing,
            delivery_mode="isolated",
            suggestions=[],
        )
        is routing
    )
    assert preflight_module._specialist_hydration_routing(
        routing,
        delivery_mode="isolated",
        suggestions=suggestions,
    )["selected_ids"] == ["writer", "reviewer", "orchestrator"]
    preflight_module._require_available_unit_plan_agents(
        delivery_mode="direct",
        suggestions=suggestions,
        loaded_slugs=(),
    )
    preflight_module._require_available_unit_plan_agents(
        delivery_mode="isolated",
        suggestions=[],
        loaded_slugs=(),
    )
    with pytest.raises(RuntimeError, match="lacks an exact unit-agent plan"):
        preflight_module._require_available_unit_plan_agents(
            delivery_mode="isolated",
            suggestions=[],
            loaded_slugs=("writer",),
        )
    preflight_module._require_available_unit_plan_agents(
        delivery_mode="isolated",
        suggestions=suggestions,
        loaded_slugs=("writer", "reviewer", "orchestrator"),
    )
    with pytest.raises(
        RuntimeError,
        match="unavailable specialist prompts: orchestrator",
    ):
        preflight_module._require_available_unit_plan_agents(
            delivery_mode="isolated",
            suggestions=suggestions,
            loaded_slugs=("writer", "reviewer"),
        )


def test_full_catalog_unit_winners_do_not_expand_a_direct_prompt_context() -> None:
    routing = {"selected_ids": ["code-reviewer", "technical-writer", "security-engineer"]}
    suggestions = [
        {
            "work_unit_id": "unit-0000000001",
            "recommended_agent": "database-migration-specialist",
        },
        {
            "work_unit_id": "unit-0000000002",
            "recommended_agent": "technical-writer",
        },
    ]

    direct = preflight_module._specialist_hydration_routing(
        routing,
        delivery_mode="direct",
        suggestions=suggestions,
    )
    isolated = preflight_module._specialist_hydration_routing(
        routing,
        delivery_mode="isolated",
        suggestions=suggestions,
    )

    assert routing["selected_ids"] == [
        "code-reviewer",
        "technical-writer",
        "security-engineer",
    ]
    assert direct["selected_ids"] == ["code-reviewer"]
    assert isolated["selected_ids"] == [
        "database-migration-specialist",
        "technical-writer",
    ]


def test_codex_native_labels_reject_invalid_or_missing_identifiers() -> None:
    with pytest.raises(ValueError, match="work_unit_id is required"):
        codex_task_name_for_work_unit("")

    assert internal_work_unit_from_codex_task_name("unit-not-legal") == ""
    assert internal_work_unit_from_codex_task_name("agency_deadbeef") == ""


def _routing(*, selected_ids: list[str], units: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "selected_ids": selected_ids,
        "work_units": {
            "delegate": True,
            "count": len(units),
            "units": units,
        },
        **extra,
    }


def _install_exact_route(
    monkeypatch: pytest.MonkeyPatch,
    *,
    prompt: str,
    selected_ids: list[str],
    unit_routes: dict[str, list[str]] | None = None,
) -> None:
    from agency_runtime.core.selector import pipeline

    def fake_route(
        session_id: str,
        user_message: str,
        catalog: list[dict[str, Any]],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        assert catalog
        is_parent = user_message == prompt
        assert session_id == (
            "session" if is_parent else f"session:unit:{work_unit_id_from_text(user_message)}"
        )
        routed_ids = (
            selected_ids
            if is_parent
            else (unit_routes or {}).get(
                user_message,
                selected_ids[:1],
            )
        )
        return {
            "selected_ids": routed_ids,
            "confidence": 0.99,
            "latency_ms": 0,
            "status": "applied",
            "source": "test",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "source_message_hash": "c" * 64,
            "work_units": detect_work_units(user_message),
            "inference_configured": False,
            "inference_mode": "heuristic",
        }

    monkeypatch.setattr(pipeline, "route", fake_route)


def test_mixed_dependency_route_never_emits_an_independent_delegation_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from agency_runtime.adapters.hooks import HookBridge

    prompt = "1 Implement API\n2 After that test\n3 Document"
    _install_exact_route(
        monkeypatch,
        prompt=prompt,
        selected_ids=["code-reviewer", "technical-writer"],
    )
    store = Store(tmp_path / "mixed-dependency.db")
    result = HookBridge("codex", store=store).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session",
            "turn_id": "trace",
            "prompt": prompt,
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "[AGENCY DELEGATION PLAN]" not in context
    assert "No specialist assignment was accepted" in context
    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    assert snapshot["selected_specialists"] == []
    receipt = store.get_ready_routing_receipt(
        "session",
        "trace",
        evidence_revision=snapshot["evidence_revision"],
    )
    assert receipt is not None
    assert "routing_status:abstained" in receipt["reason_codes"]
    assert "selection_abstained" in receipt["effect_codes"]
    assert store.get_delegations("trace") == []


def test_each_work_unit_gets_its_best_selected_specialist() -> None:
    routing = _routing(
        selected_ids=[
            "technical-writer",
            "security-engineer",
            "workflow-architect",
            "code-reviewer",
        ],
        units=[
            "Review the authentication code",
            "Document the public API in the README",
            "Harden authentication against vulnerabilities",
            "Redesign the release workflow",
        ],
    )

    plan = build_unit_agent_plan(routing)

    assert [item["recommended_agent"] for item in plan] == [
        "code-reviewer",
        "technical-writer",
        "security-engineer",
        "workflow-architect",
    ]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}
    assert preflight_recipe._suggestion_recipe(routing) == plan


def test_metadata_disambiguates_opaque_agent_slugs() -> None:
    routing = _routing(
        selected_ids=["agent-01", "agent-02"],
        units=[
            "Audit OAuth authentication security controls",
            "Write installation documentation for the README",
        ],
    )
    routing["unit_assignment_agents"] = assignment_agents_from_catalog(
        [
            {
                "slug": "agent-01",
                "name": "Guardian",
                "description": "Reviews trust boundaries.",
                "capabilities": ["OAuth threat modeling", "security review"],
                "categories": ["security"],
                "authority": "review",
                "task_types": ["analysis", "review"],
            },
            {
                "slug": "agent-02",
                "name": "Scribe",
                "description": "Maintains public guidance.",
                "capabilities": ["installation documentation", "README writing"],
                "categories": ["documentation"],
                "authority": "modify",
                "task_types": ["analysis", "implementation", "review"],
            },
        ],
        routing,
    )

    plan = build_unit_agent_plan(routing)

    assert [item["recommended_agent"] for item in plan] == ["agent-01", "agent-02"]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}


def test_each_delegated_unit_can_select_a_specialist_outside_global_top_three() -> None:
    catalog = [
        {
            "slug": "code-reviewer",
            "name": "Code Reviewer",
            "capabilities": ["code review", "test validation"],
            "categories": ["quality"],
            "authority": "review",
            "task_types": ["analysis", "review"],
        },
        {
            "slug": "technical-writer",
            "name": "Technical Writer",
            "capabilities": ["README writing", "installation documentation"],
            "categories": ["documentation"],
            "authority": "modify",
            "task_types": ["analysis", "implementation", "review"],
        },
        {
            "slug": "security-engineer",
            "name": "Security Engineer",
            "capabilities": ["authentication security", "threat modeling"],
            "categories": ["security"],
            "authority": "review",
            "task_types": ["analysis", "review"],
        },
        {
            "slug": "database-migration-specialist",
            "name": "Database Migration Specialist",
            "capabilities": ["PostgreSQL schema migration", "database migration"],
            "categories": ["database"],
            "authority": "modify",
            "task_types": ["analysis", "implementation"],
        },
    ]
    routing = _routing(
        selected_ids=["code-reviewer", "technical-writer", "security-engineer"],
        units=[
            "Migrate the PostgreSQL database schema",
            "Write installation documentation in the README",
        ],
    )

    snapshot = assignment_agents_from_catalog(catalog, routing)
    assignment_routing = {**routing, "unit_assignment_agents": snapshot}
    plan = build_unit_agent_plan(assignment_routing)

    assert "database-migration-specialist" not in routing["selected_ids"]
    assert [item["slug"] for item in snapshot] == [
        "database-migration-specialist",
        "technical-writer",
    ]
    assert [item["recommended_agent"] for item in plan] == [
        "database-migration-specialist",
        "technical-writer",
    ]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}
    assert project_unit_assignment_agents(snapshot, strict=True) == snapshot
    assert (
        build_unit_agent_plan(
            {
                **routing,
                "unit_assignment_agents": project_unit_assignment_agents(snapshot, strict=True),
            }
        )
        == plan
    )


@pytest.mark.parametrize(
    "work_units",
    [
        None,
        {
            "delegate": False,
            "count": 1,
            "units": ["Write installation documentation in the README"],
        },
    ],
)
def test_non_delegated_routes_keep_selected_only_assignment_behavior(
    work_units: dict[str, Any] | None,
) -> None:
    catalog = [
        {
            "slug": "technical-writer",
            "name": "Technical Writer",
            "capabilities": ["installation documentation"],
        },
        {
            "slug": "database-migration-specialist",
            "name": "Database Migration Specialist",
            "capabilities": ["database migration"],
        },
    ]
    routing: dict[str, Any] = {"selected_ids": ["technical-writer"]}
    if work_units is not None:
        routing["work_units"] = work_units

    snapshot = assignment_agents_from_catalog(catalog, routing)

    assert [item["slug"] for item in snapshot] == ["technical-writer"]
    assert all("matched_work_unit_ids" not in item for item in snapshot)
    assert build_unit_agent_plan({**routing, "unit_assignment_agents": snapshot}) == []


def test_missing_metadata_preserves_the_legacy_slug_only_assignment() -> None:
    routing = _routing(
        selected_ids=["technical-writer", "code-reviewer"],
        units=["Document the README", "Review the tests"],
    )

    plan = build_unit_agent_plan(routing)

    assert [item["recommended_agent"] for item in plan] == [
        "technical-writer",
        "code-reviewer",
    ]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}


def test_selected_only_metadata_recipe_remains_v2_compatible() -> None:
    routing = _routing(
        selected_ids=["opaque-a", "opaque-b"],
        units=["Audit OAuth authentication", "Write installation documentation"],
        unit_assignment_agents=[
            {
                "slug": "opaque-a",
                "name": "Guardian",
                "description": "Reviews trust boundaries and authentication.",
                "capabilities": ["OAuth security audit"],
                "tags": ["security"],
            },
            {
                "slug": "opaque-b",
                "name": "Scribe",
                "description": "Maintains installation guidance.",
                "capabilities": ["documentation writing"],
                "tags": ["writer"],
            },
        ],
    )

    plan = build_unit_agent_plan(routing)

    assert [item["recommended_agent"] for item in plan] == ["opaque-a", "opaque-b"]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}


def test_persisted_v2_assignment_recipe_remains_replayable(tmp_path) -> None:
    from agency_runtime.core.config import AgencyConfig
    from agency_runtime.core.selector import pipeline

    prompt = "1. Audit OAuth authentication\n2. Write installation documentation"
    metadata = [
        {
            "slug": "opaque-a",
            "name": "Guardian",
            "description": "Reviews trust boundaries and authentication.",
            "capabilities": ["OAuth security audit"],
            "tags": ["security"],
        },
        {
            "slug": "opaque-b",
            "name": "Scribe",
            "description": "Maintains installation guidance.",
            "capabilities": ["documentation writing"],
            "tags": ["writer"],
        },
    ]
    routing = {
        "selected_ids": ["opaque-a", "opaque-b"],
        "work_units": detect_work_units(prompt),
        "unit_assignment_agents": metadata,
    }
    current_plan = build_unit_agent_plan(routing)
    plan = [
        {
            "assignment_version": "2",
            "work_unit_id": item["work_unit_id"],
            "recommended_agent": item["recommended_agent"],
        }
        for item in current_plan
    ]
    config = AgencyConfig()
    recipe = {
        "recipe_version": 9,
        "policy_fingerprint": preflight_recipe._context_policy_fingerprint(
            config,
            pipeline,
            delivery_mode="direct",
            context_limit=preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS,
            recipe_version=9,
            context_policy_version=9,
        ),
        "session_id": "session",
        "trace_id": "trace",
        "host": "generic",
        "delivery_mode": "direct",
        "context_limit": preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS,
        "routing": preflight_recipe._content_free_routing_recipe(
            routing,
            trace_id="trace",
        ),
        "specialist_refs": [],
        "unit_assignment_agents": metadata,
        "unit_agent_plan": plan,
        "trivial": False,
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test_fixture"],
            "state_revision": "f" * 64,
            "classifier_version": 1,
        },
        "resident_manager_binding": build_resident_manager_binding(
            session_id="session",
            host="generic",
            delivery_mode="request",
        ).as_dict(),
        "roster_size": 2,
    }

    replayed = preflight_recipe._result_from_recipe(
        Store(tmp_path / "v2-replay.db"),
        recipe,
        session_id="session",
        trace_id="trace",
        user_message=prompt,
        config=config,
        pipeline=pipeline,
    )

    assert {item["assignment_version"] for item in plan} == {"2"}
    assert list(replayed.delegation_plan) == plan


def test_assignment_metadata_projection_is_bounded_and_fail_closed() -> None:
    assert project_unit_assignment_agents(None) == []
    assert project_unit_assignment_agents(None, strict=True) is None
    assert project_unit_assignment_agents([None]) == []
    assert project_unit_assignment_agents([None], strict=True) is None
    assert project_unit_assignment_agents([{"slug": ""}], strict=True) is None
    assert project_unit_assignment_agents([{"slug": "agent"}]) == []
    assert (
        project_unit_assignment_agents(
            [
                {"slug": f"agent-{index}", "name": "Named"}
                for index in range(MAX_SUGGESTED_WORK_UNITS + 1)
            ],
            strict=True,
        )
        is None
    )

    raw = [
        {
            "agent_slug": "Agent",
            "name": None,
            "description": " Bounded description ",
            "capabilities": [None, "review", "REVIEW", ""],
            "tags": ["security", "SECURITY", ""],
        },
        {"slug": "agent", "name": "duplicate"},
        {"slug": "", "name": "missing identity"},
    ]
    projected = project_unit_assignment_agents(raw)

    assert projected == [
        {
            "slug": "agent",
            "name": "",
            "description": "Bounded description",
            "capabilities": ["review"],
            "tags": ["security"],
        }
    ]
    assert project_unit_assignment_agents(raw[:2], strict=True) is None

    unit_id = work_unit_id_from_text("first")
    assert (
        project_unit_assignment_agents(
            [{"slug": "agent", "matched_work_unit_ids": "malformed"}],
            strict=True,
        )
        is None
    )
    assert (
        project_unit_assignment_agents([{"slug": "agent", "matched_work_unit_ids": "malformed"}])
        == []
    )
    assert (
        project_unit_assignment_agents(
            [
                {
                    "slug": "agent",
                    "matched_work_unit_ids": [unit_id] * (MAX_SUGGESTED_WORK_UNITS + 1),
                }
            ],
            strict=True,
        )
        is None
    )
    assert (
        project_unit_assignment_agents(
            [{"slug": "agent", "matched_work_unit_ids": ["invalid"]}],
            strict=True,
        )
        is None
    )
    assert project_unit_assignment_agents(
        [{"slug": "agent", "name": "Agent", "matched_work_unit_ids": ["invalid"]}]
    ) == [
        {
            "slug": "agent",
            "name": "Agent",
            "description": "",
            "capabilities": [],
            "tags": [],
        }
    ]
    overlapping = project_unit_assignment_agents(
        [
            {"slug": "first", "matched_work_unit_ids": [unit_id]},
            {"slug": "second", "matched_work_unit_ids": [unit_id]},
        ],
        strict=True,
    )
    assert overlapping is not None
    assert [item["slug"] for item in overlapping] == ["first", "second"]
    assert (
        project_unit_assignment_agents(
            [
                {
                    "slug": "first",
                    "matched_work_unit_ids": [unit_id],
                    "primary_work_unit_ids": [unit_id],
                },
                {
                    "slug": "second",
                    "matched_work_unit_ids": [unit_id],
                    "primary_work_unit_ids": [unit_id],
                },
            ],
            strict=True,
        )
        is None
    )


def test_assignment_catalog_and_work_unit_bounds_are_deterministic() -> None:
    assert assignment_agents_from_catalog([], {"selected_ids": "agent"}) == []
    catalog = [
        {"slug": "", "name": "invalid"},
        {"slug": "agent", "name": "First"},
        {"slug": "agent", "name": "Ignored duplicate"},
    ]
    assert assignment_agents_from_catalog(
        catalog,
        {"selected_ids": ["", "agent", "missing", "agent"]},
    ) == [
        {
            "slug": "agent",
            "name": "First",
            "description": "",
            "capabilities": [],
            "tags": [],
        }
    ]
    assert build_unit_agent_plan({"work_units": []}) == []
    assert (
        build_unit_agent_plan({"work_units": {"delegate": True, "count": 2, "units": "not-a-list"}})
        == []
    )

    plan = build_unit_agent_plan(
        _routing(
            selected_ids=["", "opaque-a", "opaque-a", "opaque-b"],
            units=["", "the and", "the and"],
        )
    )

    assert plan == []
    selected_only = assignment_agents_from_catalog(
        catalog,
        {
            "selected_ids": ["agent"],
            "work_units": {"delegate": True, "count": 2, "units": "malformed"},
        },
    )
    deduplicated = assignment_agents_from_catalog(
        catalog,
        {
            "selected_ids": ["agent"],
            "work_units": {
                "delegate": True,
                "count": 3,
                "units": ["", "same unit", "same unit"],
            },
        },
    )
    assert (
        selected_only
        == deduplicated
        == [
            {
                "slug": "agent",
                "name": "First",
                "description": "",
                "capabilities": [],
                "tags": [],
            }
        ]
    )


def test_preflight_replay_preserves_the_metadata_assignment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    prompt = (
        "1. Audit OAuth authentication security controls\n"
        "2. Write installation documentation for the README"
    )
    _install_exact_route(
        monkeypatch,
        prompt=prompt,
        selected_ids=["agent-01", "agent-02"],
        unit_routes={
            "Audit OAuth authentication security controls": ["agent-01"],
            "Write installation documentation for the README": ["agent-02"],
        },
    )
    store = Store(tmp_path / "metadata-assignment.db")
    for agent in (
        {
            "slug": "agent-01",
            "name": "Guardian",
            "division": "specialized",
            "description": "Reviews trust boundaries.",
            "capabilities": ["OAuth threat modeling", "security review"],
            "categories": ["security"],
            "prompt_body": "Audit authentication and security boundaries.",
            "version": "1.0.0",
            "authority": "review",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "test-audit-v1",
            "routing_contract_valid": True,
            "task_types": ["analysis", "review"],
        },
        {
            "slug": "agent-02",
            "name": "Scribe",
            "division": "specialized",
            "description": "Maintains public guidance.",
            "capabilities": ["installation documentation", "README writing"],
            "categories": ["documentation"],
            "prompt_body": "Write accurate installation documentation.",
            "version": "1.0.0",
            "authority": "modify",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "approved",
            "audit_revision": "test-audit-v1",
            "routing_contract_valid": True,
            "task_types": ["analysis", "implementation", "review"],
        },
    ):
        store._activate_prevalidated_agent(agent)

    first = preflight_module.run_preflight(
        store,
        session_id="session",
        trace_id="trace",
        host="codex",
        user_message=prompt,
    )
    replay = preflight_module.run_preflight(
        store,
        session_id="session",
        trace_id="trace",
        host="codex",
        user_message=prompt,
    )
    plan = store.get_completion_evidence_snapshot("session", "trace")["unit_agent_plan"]

    assert first.context == replay.context
    assert first.routing["unit_assignment_agents"] == replay.routing["unit_assignment_agents"]
    assert [item["recommended_agent"] for item in plan] == ["agent-01", "agent-02"]
    assert {item["assignment_version"] for item in plan} == {str(UNIT_AGENT_ASSIGNMENT_VERSION)}


def test_unmatched_units_do_not_fall_back_to_resident_managers() -> None:
    routing = _routing(
        selected_ids=["code-reviewer", "technical-writer"],
        units=["Reconcile lunar telemetry"],
    )
    orchestrated = build_unit_agent_plan(routing)
    chief_led = build_unit_agent_plan(
        {
            **routing,
            "unavailable_fallback_companion_ids": ["agents-orchestrator"],
        }
    )
    unavailable = build_unit_agent_plan(
        {
            **routing,
            "unavailable_fallback_companion_ids": [
                "agents-orchestrator",
                "chief-of-staff",
            ],
        }
    )

    assert orchestrated == chief_led == unavailable == []


def test_sole_domain_specialist_retains_the_stronger_route_evidence() -> None:
    plan = build_unit_agent_plan(
        _routing(
            selected_ids=["payments-billing-engineer"],
            units=["Verify Stripe webhook signatures"],
        )
    )

    assert plan[0]["recommended_agent"] == "payments-billing-engineer"


class _BatchStore:
    def __init__(self) -> None:
        self.suggestions: list[dict[str, str]] = []

    def record_suggested_delegations_batch(self, **kwargs: Any) -> int:
        self.suggestions = list(kwargs["suggestions"])
        return len(self.suggestions)


def test_event_recording_refuses_an_overflowing_unit_plan() -> None:
    units = [f"Document component {index}" for index in range(100)]
    routing = {
        **_routing(
            selected_ids=["code-reviewer", "technical-writer"],
            units=units,
        ),
        "trace_id": "turn",
    }
    store = _BatchStore()

    recorded = record_suggested_delegations(
        store,  # type: ignore[arg-type]
        session_id="session",
        host="codex",
        routing=routing,
    )

    assert recorded == 0
    assert store.suggestions == []
    assert build_unit_agent_plan(routing) == []


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_isolated_native_hook_receives_exact_unit_agent_plan(
    host: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from agency_runtime.adapters.hooks import HookBridge
    from agency_runtime.core.selector import pipeline

    prompt = "1. Review the authentication code\n2. Document the public API"

    def fake_route(
        session_id: str,
        user_message: str,
        catalog: list[dict[str, Any]],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        assert catalog
        is_parent = user_message == prompt
        assert session_id == (
            "session" if is_parent else f"session:unit:{work_unit_id_from_text(user_message)}"
        )
        selected_ids = (
            ["code-reviewer", "technical-writer"]
            if is_parent
            else {
                "Review the authentication code": ["code-reviewer"],
                "Document the public API": ["technical-writer"],
            }[user_message]
        )
        return {
            "selected_ids": selected_ids,
            "confidence": 0.99,
            "latency_ms": 0,
            "status": "applied",
            "source": "test",
            "query_hash": "a" * 64,
            "context_fingerprint": "b" * 64,
            "source_message_hash": "c" * 64,
            "work_units": detect_work_units(user_message),
            "inference_configured": False,
            "inference_mode": "heuristic",
        }

    monkeypatch.setattr(pipeline, "route", fake_route)
    store = Store(tmp_path / f"{host}.db")
    result = HookBridge(host, store=store).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session",
            "turn_id": "turn",
            "prompt": prompt,
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    assert "[AGENCY DELEGATION PLAN]" in context
    assert 'goal="Review the authentication code"' in context
    assert 'goal="Document the public API"' in context
    assert "agent=code-reviewer" in context
    assert "agent=technical-writer" in context
    for unit in detect_work_units(prompt)["units"]:
        work_unit_id = work_unit_id_from_text(unit)
        assert work_unit_id in context
        if host == "codex":
            native_task_name = codex_task_name_for_work_unit(work_unit_id)
            assert CODEX_TASK_NAME_PATTERN.fullmatch(native_task_name)
            assert internal_work_unit_from_codex_task_name(native_task_name) == work_unit_id
            assert f"native_task_name={native_task_name}" in context
            assert "set `fork_turns` to `none`" in context
    assert len(context) <= preflight_recipe.PERSISTENT_HOST_CONTEXT_CHARS


@pytest.mark.parametrize(
    ("host", "tool_name", "native_label", "backend"),
    [
        (
            "codex",
            "functions.collaboration.spawn_agent",
            "task_name",
            "spawn_agent",
        ),
        ("claude", "Agent", "description", "delegate_task"),
    ],
)
def test_same_specialist_can_activate_for_two_out_of_order_native_work_units(
    host: str,
    tool_name: str,
    native_label: str,
    backend: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from agency_runtime.adapters.hooks import HookBridge

    prompt = "1. Write the README\n2. Write contributor documentation"
    _install_exact_route(
        monkeypatch,
        prompt=prompt,
        selected_ids=["technical-writer"],
    )
    store = Store(tmp_path / f"same-agent-{host}.db")
    bridge = HookBridge(host, store=store)
    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session",
            "turn_id": "trace",
            "prompt": prompt,
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    rows = store.get_delegations("trace")
    assert len(rows) == 2
    assert {row["recommended_agent"] for row in rows} == {"technical-writer"}
    assert "unit-plan specialists: technical-writer" in context
    assert "technical-writer => work_unit_id=specialist:technical-writer" not in context

    for index, row in enumerate(reversed(rows)):
        work_unit_id = str(row["work_unit_id"])
        native_work_unit = (
            codex_task_name_for_work_unit(work_unit_id) if host == "codex" else work_unit_id
        )
        if host == "codex":
            assert CODEX_TASK_NAME_PATTERN.fullmatch(native_work_unit)
        worker_id = f"{host}-worker-{index}"
        native_run_id = (
            f"codex-agent:{worker_id}" if host == "codex" else f"claude-agent:{worker_id}"
        )
        if host == "claude":
            start = bridge.handle(
                {
                    "hook_event_name": "SubagentStart",
                    "session_id": "session",
                    "agent_id": worker_id,
                    "agent_type": "general-purpose",
                }
            )
            assert start["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
        prepared = handle_tool_call(
            "agency.prepare_delegation",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": "technical-writer",
                "work_unit_id": work_unit_id,
            },
            store,
        )
        assert "error" not in prepared
        loaded = handle_tool_call(
            "agency.load_specialist",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": "technical-writer",
                "work_unit_id": work_unit_id,
                "activation_token": prepared["activation_token"],
                "worker_id": worker_id,
                "native_run_id": native_run_id,
            },
            store,
        )
        assert "error" not in loaded
        if host == "claude":
            assert (
                bridge.handle(
                    {
                        "hook_event_name": "SubagentStop",
                        "session_id": "session",
                        "agent_id": worker_id,
                        "agent_type": "general-purpose",
                    }
                )
                == {}
            )
        bridge.handle(
            {
                "hook_event_name": "PostToolUse",
                "session_id": "session",
                "turn_id": "trace",
                "tool_use_id": native_run_id,
                "tool_name": tool_name,
                "tool_input": {
                    native_label: native_work_unit,
                    "message" if host == "codex" else "prompt": "apply the assigned unit",
                },
                "tool_response": {
                    "agent_id": worker_id,
                    "status": "completed",
                },
            }
        )

    snapshot = store.get_completion_evidence_snapshot("session", "trace")
    activation_identities = {
        (
            row["work_unit_id"],
            row["specialist_slug"],
            row["specialist_version"],
            row["specialist_prompt_hash"],
        )
        for row in snapshot["specialist_activations"]
    }
    assert len(activation_identities) == 2
    assert {identity[0] for identity in activation_identities} == {
        row["work_unit_id"] for row in rows
    }
    fields = fill_header_fields(
        {},
        "session",
        store,
        "",
        "trace",
        evidence_snapshot=snapshot,
    )
    assert fields["agencies_delegated"] == (f"technical-writer via generic-worker/{backend}")
    assert fields["actual_model_selected"] == (
        "parent task: host-selected (not observable to Agency); "
        "specialist: launch model not evidenced by this receipt"
    )
    assert fields["why"].endswith(".")
    assert "specialist instructions were loaded" in fields["how_it_shaped_outcome"]
    draft = (
        "Agency/Agencies loaded: agents-orchestrator, chief-of-staff, technical-writer\n"
        f"Agency/Agencies delegated: generic-worker via {backend}\n"
        "Skills loaded: none\n"
        "Actual Model selected: unknown -> unavailable - no model receipt recorded\n"
        f"Recruited via: {fields['recruited_via']}\n"
        "Why: Both documentation units required specialist context.\n"
        "How it shaped outcome: Each isolated unit used its exact activation grant.\n\n"
        "Done."
    )
    stale = validate_completion_policy(
        draft,
        session_id="session",
        trace_id="trace",
        store=store,
        evidence_snapshot=snapshot,
    )
    assert stale is not None
    assert stale["missing"] == [
        "agencies_delegated",
        "actual_model_selected",
        "why",
        "how_it_shaped_outcome",
    ]

    authoritative_draft = format_header(fields) + "\n\nDone."
    assert (
        validate_completion_policy(
            authoritative_draft,
            session_id="session",
            trace_id="trace",
            store=store,
            evidence_snapshot=snapshot,
        )
        is None
    )


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_unmatched_unit_is_omitted_without_assigning_a_resident_manager(
    host: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from agency_runtime.adapters.hooks import HookBridge

    prompt = "1. Analyze lunar telemetry\n2. Document the public API"
    _install_exact_route(
        monkeypatch,
        prompt=prompt,
        selected_ids=["technical-writer", "code-reviewer"],
        unit_routes={
            "Analyze lunar telemetry": [],
            "Document the public API": ["technical-writer"],
        },
    )
    store = Store(tmp_path / f"fallback-plan-{host}.db")
    result = HookBridge(host, store=store).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session",
            "turn_id": "trace",
            "prompt": prompt,
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]
    rows = store.get_delegations("trace")
    assert [row["recommended_agent"] for row in rows] == ["technical-writer"]
    assert "unit-plan specialists: technical-writer" in context
    assert "work_unit_id=specialist:" not in context
    if host == "codex":
        for row in rows:
            native_task_name = codex_task_name_for_work_unit(row["work_unit_id"])
            assert CODEX_TASK_NAME_PATTERN.fullmatch(native_task_name)
            assert f"native_task_name={native_task_name}" in context
    mismatched = handle_tool_call(
        "agency.prepare_delegation",
        {
            "session_id": "session",
            "trace_id": "trace",
            "slug": "code-reviewer",
            "work_unit_id": rows[0]["work_unit_id"],
        },
        store,
    )
    assert "not selected by this turn's ready recipe" in mismatched["error"]
    for row in rows:
        prepared = handle_tool_call(
            "agency.prepare_delegation",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": row["recommended_agent"],
                "work_unit_id": row["work_unit_id"],
            },
            store,
        )
        assert "error" not in prepared
