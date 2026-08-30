"""Exact fail-closed coverage for post-audit remediation reconciliation."""

from __future__ import annotations

import json

import pytest

from agency_runtime.core.roster.ingress import ManifestImportOutcome, RosterSyncError, _hash_text
from agency_runtime.core.roster.sync import (
    quarantine_manifest_import,
    reconcile_manifest_remediation_resolutions,
)
from agency_runtime.core.store.sqlite import Store


def _agent() -> dict[str, object]:
    agent: dict[str, object] = {
        "slug": "reconciliation-agent",
        "name": "Reconciliation Agent",
        "description": "Exercise bounded remediation reconciliation.",
        "division": "engineering",
        "categories": ["engineering"],
        "capabilities": ["review"],
        "anti_capabilities": ["claim unverified completion"],
        "task_types": ["review"],
        "preferred_when": ["reconciliation evidence is required"],
        "avoid_when": ["evidence is unavailable"],
        "required_tools": [],
        "tool_affinity": [],
        "supported_hosts": ["codex"],
        "supported_platforms": ["linux", "windows"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": "fixture-reconciliation",
        "expected_output_contract": "Return bounded reconciliation evidence.",
        "evidence_requirements": ["cite the reconciliation receipt"],
        "model_requirements": ["instruction-adherence"],
        "source_revision": "fixture-revision",
        "audit_revision": "test",
        "audit_status": "approved",
        "findings": [],
        "source": "fixture://roster",
        "source_version": "fixture-revision",
        "prompt_path": "fixture://engineering/reconciliation-agent.md",
        "prompt_body": "Perform bounded reconciliation review.",
    }
    agent["content"] = json.dumps(agent, sort_keys=True, separators=(",", ":"))
    return agent


def _outcome(agent: dict[str, object]) -> ManifestImportOutcome:
    return ManifestImportOutcome(
        status="candidate",
        origin="fixture://engineering/reconciliation-agent.md",
        relative_path="engineering/reconciliation-agent.md",
        slug=str(agent["slug"]),
        content_hash=_hash_text(str(agent["content"])),
        finding="ready",
    )


def test_reconciliation_rejects_candidate_count_mismatch(tmp_path) -> None:
    agent = _agent()
    with pytest.raises(RosterSyncError, match="candidate ids do not match"):
        reconcile_manifest_remediation_resolutions(
            [agent],
            [_outcome(agent)],
            "source",
            Store(tmp_path / "agency.db"),
            candidate_ids=[],
            audits=[],
            scan_id="scan",
        )


def test_reconciliation_rejects_audit_count_mismatch(tmp_path) -> None:
    agent = _agent()
    with pytest.raises(RosterSyncError, match="audit batch does not match"):
        reconcile_manifest_remediation_resolutions(
            [agent],
            [_outcome(agent)],
            "source",
            Store(tmp_path / "agency.db"),
            candidate_ids=["candidate"],
            audits=[],
            scan_id="scan",
        )


def test_reconciliation_rejects_unbound_audit(tmp_path) -> None:
    agent = _agent()
    with pytest.raises(RosterSyncError, match="audit is not candidate-bound"):
        reconcile_manifest_remediation_resolutions(
            [agent],
            [_outcome(agent)],
            "source",
            Store(tmp_path / "agency.db"),
            candidate_ids=["candidate"],
            audits=[{"candidate_id": "different"}],
            scan_id="scan",
        )


def test_reconciliation_rolls_back_when_scan_is_missing(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    with pytest.raises(RosterSyncError, match="scan does not match"):
        reconcile_manifest_remediation_resolutions(
            [],
            [],
            "source",
            store,
            candidate_ids=[],
            audits=[],
            scan_id="missing-scan",
        )


def test_reconciliation_rejects_candidates_not_bound_to_scan(tmp_path) -> None:
    store = Store(tmp_path / "agency.db")
    source_id = store.add_agent_source("fixtures/upstream", "upstream")
    agent = _agent()
    outcome = _outcome(agent)
    _candidate_ids, persisted = quarantine_manifest_import(
        [agent],
        [outcome],
        source_id,
        store,
    )

    with pytest.raises(RosterSyncError, match="candidates do not match the scan"):
        reconcile_manifest_remediation_resolutions(
            [agent],
            [outcome],
            source_id,
            store,
            candidate_ids=["different-candidate"],
            audits=[{"candidate_id": "different-candidate"}],
            scan_id=str(persisted[0]["scan_id"]),
        )
