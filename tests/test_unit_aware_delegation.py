"""Focused coverage for unit-aware delegation planning."""

from __future__ import annotations

from typing import Any

import pytest

from agency_runtime.core import preflight as preflight_module
from agency_runtime.core.delegation.events import (
    MAX_SUGGESTED_WORK_UNITS,
    work_unit_id_from_text,
)
from agency_runtime.core.delegation.native_labels import (
    codex_task_name_for_work_unit,
    internal_work_unit_from_codex_task_name,
)
from agency_runtime.core.selector.delegation_detection import (
    WORK_UNIT_DETECTION_VERSION,
    _imperative_units,
    detect_work_units,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import (
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
    assert first.context == replay.context
    assert first.routing["unit_assignment_agents"] == replay.routing["unit_assignment_agents"]
    # The assignment metadata is what replay has to preserve. The unit-agent plan
    # that used to be asserted here is Job B and no longer exists at all.
    assert "unit_agent_plan" not in store.get_completion_evidence_snapshot("session", "trace")


class _BatchStore:
    def __init__(self) -> None:
        self.suggestions: list[dict[str, str]] = []

    def record_suggested_delegations_batch(self, **kwargs: Any) -> int:
        self.suggestions = list(kwargs["suggestions"])
        return len(self.suggestions)


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


