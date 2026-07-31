"""Proof that a live ZCode turn receives the Agency header.

Drives the real HookBridge entry point a ZCode UserPromptSubmit hook calls,
with the true host=zcode identity. Before the WP11 fixes this path raised
``ValueError("isolated specialist delivery is unsupported for host: zcode")``;
these tests prove it now returns the Agency banner and a routed specialist team.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.core.roster.bundled import BundledRoster
from agency_runtime.core.selector import pipeline
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.unit_assignment import work_unit_id_from_text
from agency_runtime.core.workforce.routing_projection import (
    workforce_work_units_from_descriptors,
)


def test_zcode_adapter_carries_its_own_host_identity(tmp_path: Path) -> None:
    # The ZCode adapter must keep its own identity so runtime-control and
    # evidence are attributed to zcode, not masqueraded as claude.
    store = Store(tmp_path / "agency.db")
    bridge = HookBridge("zcode", store=store)

    assert bridge.host == "zcode"
    assert bridge.adapter.host_name == "zcode"


def test_zcode_usersubmit_emits_agency_header_and_routed_team(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = Store(tmp_path / "agency.db")
    for agent in BundledRoster():
        store._activate_prevalidated_agent(dict(agent))

    def route(
        _session_id: str,
        user_message: str,
        _catalog: list[dict[str, object]] | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        descriptors = [
            {
                "ordinal": 1,
                "artifact_kind": "review-report",
                "lifecycle_phase": "review",
                "authority": "review",
            },
            {
                "ordinal": 2,
                "artifact_kind": "review-report",
                "lifecycle_phase": "review",
                "authority": "review",
            },
        ]
        units = workforce_work_units_from_descriptors(user_message, descriptors)
        unit_ids = [work_unit_id_from_text(unit) for unit in units]
        return {
            "trace_id": str(kwargs.get("trace_id") or "proof-turn"),
            "selected_ids": [
                "code-reviewer",
                "ai-generated-code-security-auditor",
            ],
            "confidence": 0.99,
            "status": "applied",
            "source": "test",
            "query_hash": hashlib.sha256(user_message.encode()).hexdigest(),
            "context_fingerprint": "c" * 64,
            "work_units": {
                "delegate": True,
                "count": 2,
                "units": units,
                "source": "verified-workforce-plan",
                "confidence": "high",
            },
            "workforce_unit_descriptors": descriptors,
            "workforce_unit_bindings": [
                {
                    "source_unit_id": "unit-correctness",
                    "work_unit_id": unit_ids[0],
                    "selected": ["code-reviewer"],
                    "delivery": "delegate",
                    "timing": "immediate",
                    "depends_on": [],
                    "parallelization": "parallel",
                    "mutation_scope": "read_only",
                    "artifact_kind": "review-report",
                    "required_tools": [],
                    "required_evidence": ["review findings"],
                    "confidence": 0.99,
                },
                {
                    "source_unit_id": "unit-security",
                    "work_unit_id": unit_ids[1],
                    "selected": ["ai-generated-code-security-auditor"],
                    "delivery": "delegate",
                    "timing": "immediate",
                    "depends_on": [],
                    "parallelization": "parallel",
                    "mutation_scope": "read_only",
                    "artifact_kind": "review-report",
                    "required_tools": [],
                    "required_evidence": ["security findings"],
                    "confidence": 0.99,
                },
            ],
            "unit_assignment_agents": [
                {
                    "slug": "code-reviewer",
                    "name": "Code Reviewer",
                    "description": "Reviews authentication code for correctness.",
                    "capabilities": ["code review"],
                    "tags": ["review"],
                    "required_tools": [],
                    "evidence_requirements": ["review findings"],
                    "matched_work_unit_ids": [unit_ids[0]],
                    "primary_work_unit_ids": [unit_ids[0]],
                },
                {
                    "slug": "ai-generated-code-security-auditor",
                    "name": "AI-Generated Code Security Auditor",
                    "description": "Audits authentication code for security defects.",
                    "capabilities": ["security audit"],
                    "tags": ["security"],
                    "required_tools": [],
                    "evidence_requirements": ["security findings"],
                    "matched_work_unit_ids": [unit_ids[1]],
                    "primary_work_unit_ids": [unit_ids[1]],
                },
            ],
        }

    monkeypatch.setattr(pipeline, "route", route)
    bridge = HookBridge("zcode", store=store)

    result = bridge.handle(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "proof-session",
            "turn_id": "proof-turn",
            "prompt": "Review this authentication code for correctness and security.",
        }
    )

    context = result["hookSpecificOutput"]["additionalContext"]

    # The resident-steward kernel header is the visible Agency banner.
    assert "resident-steward kernel" in context, context[:300]
    assert "[AGENCY PREFLIGHT]" in context, context[:300]
    # Isolated preflight preserves the routed team as durable evidence without
    # falsely claiming either specialist was already loaded in the parent.
    [routing] = store.recent_runtime_activity(limit=10)["routing"]
    assert routing["selected_ids"] == [
        "code-reviewer",
        "ai-generated-code-security-auditor",
    ]
    # ZCode-correct native-delegation guidance (Agent tool, not spawn_agent).
    assert "`Agent`" in context, context[:600]
