"""Audited roster contracts survive immutable storage and selector projection."""

from __future__ import annotations

import json
from pathlib import Path

from agency_runtime.core.roster.revisions import decode_revision_metadata
from agency_runtime.core.store.sqlite import Store


def _audited_agent() -> dict[str, object]:
    return {
        "slug": "secure-reviewer",
        "name": "Secure Reviewer",
        "division": "security",
        "description": "Reviews bounded authentication changes.",
        "categories": ["security", "review"],
        "capabilities": ["authentication review", "threat analysis"],
        "tool_affinity": ["source", "tests"],
        "anti_capabilities": ["credential access", "production approval"],
        "task_types": ["review"],
        "preferred_when": ["authentication code needs independent review"],
        "avoid_when": ["the task requests secrets or production access"],
        "required_tools": ["source"],
        "supported_hosts": ["codex", "claude"],
        "supported_platforms": ["windows", "linux"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": ["credential-operator"],
        "requires": [],
        "independence_group": "security-review",
        "expected_output_contract": "Findings with evidence and severity.",
        "evidence_requirements": ["cite exact files and lines"],
        "model_requirements": ["strong-analysis"],
        "source_revision": "a" * 40,
        "source_content_hash": "c" * 64,
        "audit_revision": "1",
        "audit_status": "approved",
        "findings": ["raw mutation authority reduced to review"],
        "source": "bundled-audited",
        "source_version": "upstream-a",
        "prompt_path": "bundled://secure-reviewer",
        "prompt_body": "Review authentication changes within the bounded contract.",
        "version": "sha256:" + "b" * 64,
    }


def test_rich_contract_round_trips_to_every_selector_snapshot(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    store._activate_prevalidated_agent(_audited_agent())

    [active] = store.get_active_roster()
    [catalog] = store.get_active_roster_as_catalog()
    [snapshot] = store.get_routing_roster_snapshot()["catalog"]

    for row in (active, catalog, snapshot):
        assert row["routing_contract_valid"] is True
        assert row["authority"] == "review"
        assert row["context_mode"] == "isolated_only"
        assert row["anti_capabilities"] == ["credential access", "production approval"]
        assert row["supported_hosts"] == ["codex", "claude"]
        assert row["conflicts_with"] == ["credential-operator"]
        assert row["expected_output_contract"] == "Findings with evidence and severity."
        assert row["source_content_hash"] == "c" * 64
        assert row["audit_status"] == "approved"


def test_legacy_revision_metadata_gets_safe_empty_routing_defaults() -> None:
    legacy = {
        "name": "Legacy",
        "division": "testing",
        "description": "Legacy metadata",
        "source": "bundled",
        "prompt_path": "bundled://legacy",
        "source_version": "1.0.0",
        "categories": ["testing"],
        "capabilities": ["review"],
        "tool_affinity": [],
    }

    decoded = decode_revision_metadata(json.dumps(legacy))

    assert decoded is not None
    assert decoded["authority"] == ""
    assert decoded["anti_capabilities"] == []
    assert decoded["supported_hosts"] == []
