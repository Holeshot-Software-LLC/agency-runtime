"""Resident-manager kernel and parent-only boundary contracts."""

from __future__ import annotations

import builtins
import hashlib
import importlib
from typing import Any

import pytest

import agency_runtime.core.resident_managers as resident_managers
from agency_runtime import AgencyRuntime
from agency_runtime.core.agent_activation import PROTECTED_AGENT_SLUGS
from agency_runtime.core.delegation.events import mark_delegation_executed
from agency_runtime.core.policy.defaults import NO_MATCH_FALLBACK_SLUGS
from agency_runtime.core.resident_managers import (
    MAX_RESIDENT_MANAGER_KERNEL_CHARS,
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_HASH,
    RESIDENT_MANAGER_KERNEL_REFERENCE,
    RESIDENT_MANAGER_KERNEL_VERSION,
    RESIDENT_MANAGER_SLUG_SET,
    RESIDENT_MANAGER_SLUGS,
    is_resident_manager_slug,
    reject_resident_manager,
    resident_manager_boundary_error,
)
from agency_runtime.core.specialist_context import (
    hydrate_selected_specialist_context,
    rebuild_versioned_specialist_context,
)
from agency_runtime.core.unit_assignment import (
    assignment_agents_from_catalog,
    build_unit_agent_plan,
    project_unit_assignment_agents,
)
from agency_runtime.server.mcp_tools import dispatch_tool_call


class _BoundaryStore:
    def __init__(self) -> None:
        self.mutations: list[str] = []

    @staticmethod
    def get_run(_trace_id: str) -> dict[str, Any]:
        return {
            "session_id": "session",
            "status": "active",
            "ended_at": None,
            "preflight_state": "ready",
        }

    @staticmethod
    def get_delegations(_trace_id: str) -> list[dict[str, Any]]:
        return []

    def _unexpected(self, operation: str) -> None:
        self.mutations.append(operation)
        raise AssertionError(f"resident manager crossed ordinary boundary: {operation}")

    def consume_delegation_activation(self, **_kwargs: Any) -> dict[str, Any]:
        self._unexpected("consume_delegation_activation")

    def get_specialist_prompt(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self._unexpected("get_specialist_prompt")

    def get_versioned_specialist_prompt(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self._unexpected("get_versioned_specialist_prompt")

    def prepare_delegation_activation(self, **_kwargs: Any) -> dict[str, Any]:
        self._unexpected("prepare_delegation_activation")

    def record_specialist_loaded(self, *_args: Any, **_kwargs: Any) -> None:
        self._unexpected("record_specialist_loaded")

    def record_delegation(self, **_kwargs: Any) -> str:
        self._unexpected("record_delegation")


def test_resident_kernel_is_compact_versioned_and_content_addressed() -> None:
    assert RESIDENT_MANAGER_KERNEL_VERSION == 1
    assert len(RESIDENT_MANAGER_KERNEL) <= MAX_RESIDENT_MANAGER_KERNEL_CHARS
    assert (
        hashlib.sha256(RESIDENT_MANAGER_KERNEL.encode("utf-8")).hexdigest()
        == RESIDENT_MANAGER_KERNEL_HASH
    )
    assert RESIDENT_MANAGER_KERNEL_REFERENCE.version == RESIDENT_MANAGER_KERNEL_VERSION
    assert RESIDENT_MANAGER_KERNEL_REFERENCE.content_hash == RESIDENT_MANAGER_KERNEL_HASH
    assert RESIDENT_MANAGER_KERNEL_REFERENCE.slugs == RESIDENT_MANAGER_SLUGS
    assert not hasattr(RESIDENT_MANAGER_KERNEL_REFERENCE, "content")
    assert "Chief of Staff owns the requested outcome" in RESIDENT_MANAGER_KERNEL
    assert "Agents Orchestrator owns decomposition" in RESIDENT_MANAGER_KERNEL
    assert "native host alone spawns" in RESIDENT_MANAGER_KERNEL
    assert "parent-only" in RESIDENT_MANAGER_KERNEL


def test_resident_kernel_import_fails_when_the_budget_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_len = builtins.len

    def _over_budget_len(value: Any) -> int:
        if isinstance(value, str) and value.startswith("[Agency resident-manager kernel"):
            return MAX_RESIDENT_MANAGER_KERNEL_CHARS + 1
        return real_len(value)

    try:
        monkeypatch.setattr(builtins, "len", _over_budget_len)
        with pytest.raises(RuntimeError, match="exceeds its context budget"):
            importlib.reload(resident_managers)
    finally:
        monkeypatch.setattr(builtins, "len", real_len)
        importlib.reload(resident_managers)


def test_resident_identity_is_canonical_and_compatibility_aliases_share_it() -> None:
    assert RESIDENT_MANAGER_SLUGS == ("agents-orchestrator", "chief-of-staff")
    assert RESIDENT_MANAGER_SLUG_SET == PROTECTED_AGENT_SLUGS
    assert NO_MATCH_FALLBACK_SLUGS is RESIDENT_MANAGER_SLUGS
    assert is_resident_manager_slug("  CHIEF-OF-STAFF ") is True
    assert is_resident_manager_slug("code-reviewer") is False
    assert resident_managers.is_current_resident_manager_kernel_reference(None) is False
    assert reject_resident_manager("code-reviewer", operation="be loaded") is None
    assert (
        resident_manager_boundary_error(
            "code-reviewer",
            operation="be loaded",
        )
        == ""
    )
    with pytest.raises(ValueError, match="parent-only"):
        reject_resident_manager(
            "agents-orchestrator",
            operation="be loaded as an ordinary specialist",
        )
    assert (
        resident_manager_boundary_error(
            "chief-of-staff",
            operation="",
        )
        == "resident manager 'chief-of-staff' is parent-only and cannot "
        "be used as an ordinary specialist"
    )


def test_resident_managers_are_rejected_from_assignment_metadata_and_plans() -> None:
    resident = {
        "slug": "agents-orchestrator",
        "name": "Agents Orchestrator",
        "description": "Coordinates specialists.",
    }
    specialist = {
        "slug": "technical-writer",
        "name": "Technical Writer",
        "description": "Writes documentation.",
    }
    assert project_unit_assignment_agents([resident]) == []
    assert project_unit_assignment_agents([resident], strict=True) is None
    assert project_unit_assignment_agents([resident, specialist]) == [
        {
            "slug": "technical-writer",
            "name": "Technical Writer",
            "description": "Writes documentation.",
            "capabilities": [],
            "tags": [],
        }
    ]

    manager_only = {
        "selected_ids": list(RESIDENT_MANAGER_SLUGS),
        "unit_assignment_agents": [resident],
        "work_units": {
            "delegate": True,
            "count": 2,
            "units": ["Analyze lunar telemetry", "Coordinate the release"],
        },
    }
    assert assignment_agents_from_catalog([resident], manager_only) == []
    assert build_unit_agent_plan(manager_only) == []

    specialist_route = {
        **manager_only,
        "selected_ids": ["agents-orchestrator", "technical-writer"],
        "unit_assignment_agents": [resident, specialist],
        "work_units": {
            "delegate": True,
            "count": 2,
            "units": ["Write installation documentation", "Update the README"],
        },
    }
    assert {row["recommended_agent"] for row in build_unit_agent_plan(specialist_route)} == {
        "technical-writer"
    }


def test_ordinary_specialist_hydration_omits_resident_manager_prompts() -> None:
    store = _BoundaryStore()
    loaded = hydrate_selected_specialist_context(
        store,  # type: ignore[arg-type]
        [{"slug": "agents-orchestrator"}],
        {"selected_ids": ["agents-orchestrator"]},
        session_id="session",
        trace_id="trace",
    )

    assert loaded.context == ""
    assert loaded.slugs == ()
    assert loaded.references == ()
    assert store.mutations == []

    with pytest.raises(RuntimeError, match="resident manager"):
        rebuild_versioned_specialist_context(
            store,  # type: ignore[arg-type]
            [
                {
                    "slug": "chief-of-staff",
                    "version": "1.0.0",
                    "hash": "a" * 64,
                }
            ],
        )
    assert store.mutations == []


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            "agency.load_specialist",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": "agents-orchestrator",
            },
        ),
        (
            "agency.prepare_delegation",
            {
                "session_id": "session",
                "trace_id": "trace",
                "slug": "chief-of-staff",
                "work_unit_id": "unit-0123456789",
            },
        ),
        (
            "agency.delegate",
            {
                "session_id": "session",
                "trace_id": "trace",
                "agent": "agents-orchestrator",
                "task": "Execute work",
                "backend": "spawn_agent",
                "work_unit_id": "unit-0123456789",
                "worker_kind": "native-agent",
                "worker_id": "worker-1",
                "native_run_id": "run-1",
            },
        ),
    ],
)
def test_mcp_ordinary_specialist_boundaries_reject_resident_managers(
    tool_name: str,
    arguments: dict[str, str],
) -> None:
    store = _BoundaryStore()

    result = dispatch_tool_call(tool_name, arguments, store)

    assert "parent-only" in result["error"]
    assert store.mutations == []


def test_public_evidence_boundaries_reject_resident_managers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = _BoundaryStore()
    runtime = AgencyRuntime()
    runtime._store = store
    monkeypatch.setattr(runtime, "_runtime_enabled", lambda: True)
    monkeypatch.setattr(runtime, "_require_active_turn", lambda *_args: None)

    with pytest.raises(ValueError, match="parent-only"):
        runtime.record_specialist("session", "chief-of-staff", trace_id="trace")
    with pytest.raises(ValueError, match="parent-only"):
        runtime.record_delegation(
            trace_id="trace",
            session_id="session",
            work_unit_id="unit-0123456789",
            recommended_agent="agents-orchestrator",
            status="suggested",
        )
    assert store.mutations == []


def test_native_delegation_execution_does_not_promote_a_resident_manager() -> None:
    store = _BoundaryStore()

    recorded = mark_delegation_executed(
        store,  # type: ignore[arg-type]
        session_id="session",
        trace_id="trace",
        host="codex",
        backend="spawn_agent",
        agent="chief-of-staff",
        goal="Implement the change",
        work_unit_id="unit-0123456789",
        executed_worker_kind="native-agent",
        executed_worker_id="worker-1",
        native_run_id="run-1",
    )

    assert recorded == 0
    assert store.mutations == []
