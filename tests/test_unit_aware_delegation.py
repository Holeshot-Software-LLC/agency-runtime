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
    codex_task_name_for_work_unit,
    internal_work_unit_from_codex_task_name,
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


def test_hydration_never_truncates_the_selected_team() -> None:
    routing = {"selected_ids": ["code-reviewer", "technical-writer", "security-engineer"]}

    hydrated = preflight_module._specialist_hydration_routing(routing)

    # A job may need more than one specialist. How many may be selected is the
    # staffing budget's decision and is not re-imposed at hydration.
    assert routing["selected_ids"] == [
        "code-reviewer",
        "technical-writer",
        "security-engineer",
    ]
    assert hydrated["selected_ids"] == [
        "code-reviewer",
        "technical-writer",
        "security-engineer",
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
            "inference_configured": True,
            "inference_mode": "inferred",
        }

    monkeypatch.setattr(pipeline, "route", fake_route)


def test_mixed_dependency_route_without_an_exact_plan_fails_open(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from agency_runtime.adapters.hooks import HookBridge

    # ADR-0122 update: a multi-specialist plan whose dependencies cannot be
    # resolved no longer blocks the parent model. The turn fails open so the
    # host answers as a generalist, and no delegations are recorded.
    prompt = "1 Implement API\n2 After that test\n3 Document"
    _install_exact_route(
        monkeypatch,
        prompt=prompt,
        selected_ids=["code-reviewer", "technical-writer"],
    )
    store = Store(tmp_path / "mixed-dependency.db")
    HookBridge("codex", store=store).handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "session",
            "turn_id": "trace",
            "prompt": prompt,
        }
    )

    # No delegations are recorded because the plan could not produce a valid
    # unit assignment, but the turn was allowed to proceed.
    assert store.get_delegations("trace") == []


def test_selected_team_is_not_reinterpreted_as_per_unit_assignments() -> None:
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

    assert plan == []
    assert preflight_recipe._suggestion_recipe(routing) == plan


def test_unconfigured_metadata_routing_fails_closed() -> None:
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

    assert routing["unit_assignment_agents"] == []
    assert plan == []


def test_exact_inference_assignment_can_select_a_specialist_outside_global_team() -> None:
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

    database_unit_id = work_unit_id_from_text("Migrate the PostgreSQL database schema")
    documentation_unit_id = work_unit_id_from_text("Write installation documentation in the README")
    snapshot = project_unit_assignment_agents(
        [
            {
                **catalog[3],
                "tags": catalog[3]["categories"],
                "matched_work_unit_ids": [database_unit_id],
                "primary_work_unit_ids": [database_unit_id],
            },
            {
                **catalog[1],
                "tags": catalog[1]["categories"],
                "matched_work_unit_ids": [documentation_unit_id],
                "primary_work_unit_ids": [documentation_unit_id],
            },
        ],
        strict=True,
    )
    assert snapshot is not None
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


def test_missing_unit_evidence_does_not_create_a_legacy_slug_assignment() -> None:
    routing = _routing(
        selected_ids=["technical-writer", "code-reviewer"],
        units=["Document the README", "Review the tests"],
    )

    plan = build_unit_agent_plan(routing)

    assert plan == []


def test_selected_only_metadata_does_not_create_a_new_unit_assignment() -> None:
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

    assert plan == []


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
    units = detect_work_units(prompt)["units"]
    plan = [
        {
            "assignment_version": "2",
            "work_unit_id": work_unit_id_from_text(unit),
            "recommended_agent": agent,
        }
        for unit, agent in zip(units, ("opaque-a", "opaque-b"), strict=True)
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


def test_sole_domain_specialist_still_requires_exact_unit_evidence() -> None:
    plan = build_unit_agent_plan(
        _routing(
            selected_ids=["payments-billing-engineer"],
            units=["Verify Stripe webhook signatures"],
        )
    )

    assert plan == []


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


def _verified_binding(delivery: str) -> dict[str, Any]:
    """One verifier-approved unit binding differing only in delivery."""

    goal = "Review the authentication code"
    return {
        "work_units": {
            "count": 1,
            "confidence": "high",
            "source": "verified-workforce-plan",
            "units": [goal],
            "delegate": True,
        },
        "workforce_unit_bindings": [
            {
                "source_unit_id": "unit-work",
                "work_unit_id": work_unit_id_from_text(goal),
                "selected": ["code-reviewer"],
                "delivery": delivery,
                "timing": "immediate",
                "depends_on": [],
                "parallelization": "sequential",
                "mutation_scope": "read_only",
                "artifact_kind": "review-report",
                "required_tools": [],
                "required_evidence": [],
                "confidence": 1.0,
            }
        ],
    }


def test_a_loaded_unit_produces_no_delegation_plan() -> None:
    """`load` is the deterministic default, and it must not plan a spawn.

    This is rule 2 -- the specialist works inside the existing conversation --
    expressed where it is actually decided. Before Job B was removed the
    default was `delegate`, so every staffed unit produced a plan row telling
    the host to dispatch a child. Nothing may reintroduce that silently.
    """

    assert build_unit_agent_plan(_verified_binding("load")) == []


def test_a_verified_workforce_route_plans_no_delegation_at_all() -> None:
    """Corrects this test's earlier claim, which was measured and found false.

    It used to assert that `delivery="delegate"` still produced a plan, and read
    as proof that inference could ask for delegation. It could not: the only
    schema carrying `delivery` had no caller, so the staffing verifier's "load"
    default always stood. A hand-built binding reached a branch no real turn
    could. The branch is retired, so the delivery value is now irrelevant --
    a verified workforce route plans nothing either way.
    """

    assert build_unit_agent_plan(_verified_binding("delegate")) == []
    assert build_unit_agent_plan(_verified_binding("load")) == []
