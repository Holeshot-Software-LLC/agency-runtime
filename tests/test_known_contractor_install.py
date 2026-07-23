"""Package authority and idempotent installation for known contractors."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import closing
from pathlib import Path

import pytest

from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.selector.compatibility import filter_eligible_catalog
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.hiring_contract import CONTRACTOR_PROMPT_TEMPLATE_HASH
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG
from agency_runtime.core.workforce.known_installer import (
    PACKAGED_CONTRACTOR_AUTHORITY,
    install_known_contractors,
    known_contractor_package,
    packaged_hiring_evidence,
)


def _contract_hash(value: dict[str, object]) -> str:
    document = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def test_known_contractors_install_atomically_with_truthful_package_evidence(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")

    first = install_known_contractors(store)
    second = install_known_contractors(store)

    expected = tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG))
    assert first.installed == expected
    assert first.existing == ()
    assert second.installed == ()
    assert second.existing == expected
    assert store.count_active_roster() == len(expected)
    workers = store.list_workforce_workers(state="contractor", limit=20, disabled_agents=())
    assert {item["agent_slug"] for item in workers} == set(expected)
    assert all(item["display_label"].startswith("Contractor · ") for item in workers)
    assert all(item["origin"] == "agency" and item["enabled"] for item in workers)
    snapshot = workforce_index_snapshot(store, disabled_agents=())
    assert snapshot.worker_count == len(expected)
    assert {item.agent_id for item in snapshot.contracts} == set(expected)

    with closing(store._connect()) as conn:
        cases = conn.execute("SELECT * FROM agent_hiring_cases ORDER BY proposed_slug").fetchall()
    assert len(cases) == len(expected)
    for case in cases:
        critic = json.loads(case["critic_evidence"])
        model = json.loads(case["model_evidence"])
        assert case["status"] == "applied"
        assert critic["authority"] == PACKAGED_CONTRACTOR_AUTHORITY
        assert critic["compiler_template_hash"] == CONTRACTOR_PROMPT_TEMPLATE_HASH
        assert model == {
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "inference_required": False,
            "reason": "maintainer-reviewed packaged contractor; no inference call was made",
            "receipts": [],
        }


def test_packaged_contractor_prompt_and_workforce_contract_are_exact_and_routable(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)

    for slug in sorted(KNOWN_CONTRACTORS_BY_SLUG):
        package = known_contractor_package(slug)
        prompt = store.get_specialist_prompt(slug, disabled_agents=())
        worker = store.get_workforce_worker(slug, disabled_agents=())
        assert prompt is not None
        assert prompt["prompt_body"] == package.compiled.prompt
        assert prompt["hash"] == package.compiled.prompt_hash
        assert worker["current_hash"] == package.compiled.prompt_hash
        assert worker["worker_id"] == package.compiled.worker_id


def test_integration_verifier_does_not_require_its_optional_browser_surface() -> None:
    package = known_contractor_package("application-integration-verifier")
    agent = selector_roster_projection(package.agent)

    result = filter_eligible_catalog(
        [agent],
        host="codex",
        platform="windows",
        available_tools={"repository-read", "test-execution"},
        capability_status="native-installation-verified",
    )

    assert [item["agent_slug"] for item in result.eligible] == ["application-integration-verifier"]
    assert "browser" in package.employment_contract.tools
    assert "browser" not in package.agent["required_tools"]
    assert "browser-interaction" in package.agent["tool_affinity"]
    assert "browser-interaction" not in package.workforce_contract.tool_classes
    assert package.workforce_contract.tool_classes == (
        "repository-read",
        "test-execution",
    )


def test_selection_safety_critic_uses_native_runtime_evidence_capability() -> None:
    package = known_contractor_package("selection-safety-critic")

    assert package.agent["required_tools"] == ["workforce-index", "staffing-plan-reader"]
    assert package.workforce_contract.tool_classes == ("runtime-evidence",)


def test_installed_legacy_optional_tool_metadata_is_reconciled_for_routing(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    install_known_contractors(store)
    package = known_contractor_package("application-integration-verifier")
    legacy_agent = {
        **package.agent,
        "required_tools": list(package.employment_contract.tools),
    }
    stale_contract = package.workforce_contract.to_dict()
    stale_contract["tool_classes"] = [
        "browser-interaction",
        "repository-read",
        "test-execution",
    ]
    stale_document = json.dumps(
        stale_contract,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    worker = store.get_workforce_worker(package.employment_contract.slug, disabled_agents=())
    with closing(store._connect()) as conn:
        sequence = int(
            conn.execute(
                "SELECT COALESCE(MAX(projection_sequence), 0) "
                "FROM agent_recruitment_contract_projections"
            ).fetchone()[0]
        )
        conn.execute(
            "UPDATE agent_versions SET metadata = ? WHERE id = ?",
            (
                serialized_revision_metadata(legacy_agent),
                worker["current_agent_version_id"],
            ),
        )
        conn.execute(
            "INSERT INTO agent_recruitment_contract_projections "
            "(id, projection_sequence, worker_id, agent_version_id, "
            "parent_contract_hash, recruitment_contract, recruitment_contract_hash, "
            "projection_authority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, "
            "'test-legacy-package', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (
                str(uuid.uuid4()),
                sequence + 1,
                worker["worker_id"],
                worker["current_agent_version_id"],
                _contract_hash(package.workforce_contract.to_dict()),
                stale_document,
                hashlib.sha256(stale_document.encode("utf-8")).hexdigest(),
            ),
        )
        conn.commit()

    before = next(
        item
        for item in store.get_active_roster_as_catalog(disabled_agents=())
        if item["agent_slug"] == package.employment_contract.slug
    )
    assert "browser-interaction" in before["required_tools"]

    repaired = store.reconcile_packaged_workforce_contracts()

    assert repaired.inspected == len(KNOWN_CONTRACTORS_BY_SLUG)
    assert repaired.updated == 1
    after = next(
        item
        for item in store.get_active_roster_as_catalog(disabled_agents=())
        if item["agent_slug"] == package.employment_contract.slug
    )
    assert after["required_tools"] == ["repository-read", "test-execution"]
    eligible = filter_eligible_catalog(
        [after],
        host="codex",
        platform="windows",
        available_tools={"repository-read", "test-execution"},
        capability_status="native-installation-verified",
    )
    assert [item["agent_slug"] for item in eligible.eligible] == [
        "application-integration-verifier"
    ]


def test_packaged_authority_rejects_tampered_or_unknown_evidence(tmp_path: Path) -> None:
    store = Store(tmp_path / "agency.db")
    package = known_contractor_package("python-application-engineer")
    evidence = packaged_hiring_evidence(package)
    evidence["model_evidence"]["reason"] = "pretend model evidence"
    contract = package.workforce_contract.to_dict()
    case = store.create_hiring_case(
        case_type="hire",
        proposed_slug=package.employment_contract.slug,
        work_unit_id=str(uuid.uuid4()),
        request_hash="a" * 64,
        contract_evidence=contract,
        contract_hash=_contract_hash(contract),
        **evidence,
    )

    with pytest.raises(ValueError, match="validated critic and model evidence"):
        store.transition_hiring_case(case["id"], status="audited")

    unknown_contract = {**contract, "agent_id": "unknown-contractor"}
    unknown_contract["worker_id"] = "unknown-worker"
    with pytest.raises(ValueError, match="validated critic and model evidence"):
        unknown = store.create_hiring_case(
            case_type="hire",
            proposed_slug="unknown-contractor",
            work_unit_id=str(uuid.uuid4()),
            request_hash="b" * 64,
            contract_evidence=unknown_contract,
            contract_hash=_contract_hash(unknown_contract),
            **packaged_hiring_evidence(package),
        )
        store.transition_hiring_case(unknown["id"], status="audited")
