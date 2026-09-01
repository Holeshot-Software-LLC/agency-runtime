from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from agency_runtime.core.workforce import contract as workforce_contract
from agency_runtime.core.workforce.capability_ontology import CORE_CAPABILITY_IDS
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    project_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.recruiter_index import (
    COMPOSITION_INDEX_FIELDS,
    RECRUITER_INDEX_FIELDS,
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)


def _manifest_agents() -> list[dict[str, object]]:
    path = (
        Path(__file__).parents[1] / "agency_runtime" / "core" / "roster" / "data" / "manifest.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))["agents"]


def test_every_bundled_agent_projects_to_an_immutable_compact_contract() -> None:
    contracts = [project_workforce_contract(agent) for agent in _manifest_agents()]

    assert len(contracts) == 263
    assert {item.schema_version for item in contracts} == {WORKFORCE_CONTRACT_SCHEMA_VERSION}
    assert len({item.agent_id for item in contracts}) == 263
    assert len({item.worker_id for item in contracts}) == 263
    assert all(item.outcomes and item.capability_ids and item.artifact_kinds for item in contracts)
    observed_capabilities = {item for contract in contracts for item in contract.capability_ids}
    assert observed_capabilities <= CORE_CAPABILITY_IDS
    assert len(observed_capabilities) >= 20
    assert all(item.hosts and item.platforms for item in contracts)
    assert workforce_index_fingerprint(contracts).startswith("sha256:")
    with pytest.raises(FrozenInstanceError):
        contracts[0].enabled = False  # type: ignore[misc]


def test_projection_excludes_source_prompt_and_provenance() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "senior-developer")
    payload = project_workforce_contract(source).to_dict()
    rendered = json.dumps(payload, sort_keys=True)

    assert payload["archetype"] == "implementer"
    assert "implementation" in payload["capability_ids"]
    assert payload["domains"] == ("software-engineering",)
    assert "prompt_file" not in rendered
    assert "relative_path" not in rendered
    assert "source_content_hash" not in rendered
    assert "source_revision" not in rendered
    assert "findings" not in rendered


def test_security_review_outcome_adds_audited_secondary_domain() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "code-reviewer")

    assert project_workforce_contract(source).domains == (
        "software-engineering",
        "security",
        "quality-assurance",
    )


def test_application_security_code_review_owns_security_and_software_domains() -> None:
    source = next(
        agent
        for agent in _manifest_agents()
        if agent["slug"] == "ai-generated-code-security-auditor"
    )

    assert project_workforce_contract(source).domains == (
        "security",
        "software-engineering",
    )


def test_code_review_contract_owns_software_and_quality_domains() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "code-reviewer")

    contract = project_workforce_contract(source)

    assert contract.domains == (
        "software-engineering",
        "security",
        "quality-assurance",
    )


def test_lsp_contract_owns_its_software_engineering_domain() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "lsp-index-engineer")

    contract = project_workforce_contract(source)

    assert contract.domains == ("specialist-services", "software-engineering")


def test_accessibility_auditor_owns_its_explicit_domain() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "accessibility-auditor")

    contract = project_workforce_contract(source)

    assert contract.domains == ("quality-assurance", "accessibility")


@pytest.mark.parametrize("agent_id", ["accounts-payable-agent", "chief-financial-officer"])
def test_specialized_finance_contracts_own_their_explicit_domain(agent_id: str) -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == agent_id)

    contract = project_workforce_contract(source)

    assert contract.domains == ("specialist-services", "finance")


def test_incident_contracts_project_their_audited_controlled_capabilities() -> None:
    sources = {agent["slug"]: agent for agent in _manifest_agents()}

    responder = project_workforce_contract(sources["incident-responder"])
    commander = project_workforce_contract(sources["incident-response-commander"])

    assert {
        "analysis",
        "audit",
        "coordination",
        "governance",
        "investigation",
        "operations",
        "planning",
        "review",
        "risk-analysis",
    } <= set(responder.capability_ids)
    assert {
        "analysis",
        "coordination",
        "investigation",
        "operations",
        "planning",
        "risk-analysis",
        "review",
    } <= set(commander.capability_ids)
    # 2026-08-11: gained "operations" from its own `operations` category. The
    # commander was previously indistinguishable from every other engineering
    # worker on domain, and was selected for a dashboard planning task on the
    # strength of the verb "come up with a plan" alone. Naming its actual
    # subject matter is the point; it will now match operations work rather
    # than any software unit.
    assert commander.domains == ("software-engineering", "operations")


def test_discovery_worker_accepts_analysis_artifacts_from_inference_plans() -> None:
    source = next(
        agent for agent in _manifest_agents() if agent["slug"] == "codebase-onboarding-engineer"
    )
    contract = project_workforce_contract(source)

    assert contract.lifecycle_phases == ("discovery", "review")
    assert contract.artifact_kinds == ("documentation", "analysis", "review-report")


def test_review_report_task_type_grants_review_artifact_and_lifecycle() -> None:
    # Synced rosters (not the bundled manifest) declare the artifact itself as a
    # task type: 11 active contracts carry "review-report" and nothing else
    # review-flavored. They must cover artifact:review-report and the review
    # lifecycle, or the recruiter reports staff_without_safe_team on the
    # artifact axis for every review-flavored unit that ranks them first.
    source = dict(next(agent for agent in _manifest_agents() if agent["slug"] == "code-reviewer"))
    source["task_types"] = ["review-report"]
    contract = project_workforce_contract(source)

    assert "review-report" in contract.artifact_kinds
    assert "review" in contract.lifecycle_phases


def test_projection_preserves_typed_relationships_without_promoting_conflicts() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "reality-checker")
    contract = project_workforce_contract(source)

    assert contract.composition.same_context_conflicts == (
        "evidence-collector",
        "test-results-analyzer",
    )
    assert contract.composition.selection_exclusive == ()
    assert contract.composition.requires == ()


def test_disabled_imported_manager_remains_visible_but_is_not_forced_employed() -> None:
    agents = _manifest_agents()
    writer = next(agent for agent in agents if agent["slug"] == "technical-writer")
    manager = next(agent for agent in agents if agent["slug"] == "chief-of-staff")

    disabled = project_workforce_contract(writer, disabled={"technical-writer"})
    imported_manager = project_workforce_contract(manager, disabled={"chief-of-staff"})

    assert disabled.enabled is False
    assert disabled.employment == "disabled"
    assert imported_manager.enabled is False
    assert imported_manager.employment == "disabled"


def test_full_index_fingerprint_is_order_independent_and_content_sensitive() -> None:
    first, second = [project_workforce_contract(agent) for agent in _manifest_agents()[:2]]

    baseline = workforce_index_fingerprint([first, second])
    assert workforce_index_fingerprint([second, first]) == baseline
    changed = project_workforce_contract(
        {**_manifest_agents()[1], "outcomes": ["a deliberately changed outcome"]}
    )
    assert workforce_index_fingerprint([first, changed]) != baseline
    with pytest.raises(ValueError, match="duplicate agent ids"):
        workforce_index_fingerprint(
            [first, project_workforce_contract({**_manifest_agents()[0], "worker_id": "other"})]
        )
    with pytest.raises(ValueError, match="duplicate worker ids"):
        workforce_index_fingerprint([first, first])


def test_canonical_contract_cache_is_bounded_and_does_not_mask_mutation() -> None:
    first = project_workforce_contract(_manifest_agents()[0])
    canonical = workforce_contract._canonical_json
    canonical.cache_clear()
    try:
        baseline = canonical(first)
        assert canonical(first) == baseline
        assert canonical.cache_info().hits == 1

        changed = replace(first, enabled=False, employment="disabled")
        assert canonical(changed) != baseline

        for index in range(512):
            canonical(replace(first, display_name=f"cache-entry-{index}"))

        bounded = canonical.cache_info()
        assert bounded.maxsize == 512
        assert bounded.currsize == 512
        misses_before_evicted_read = bounded.misses
        assert canonical(first) == baseline
        assert canonical.cache_info().misses == misses_before_evicted_read + 1
    finally:
        canonical.cache_clear()


def test_full_index_fingerprint_rejects_dangling_relationships() -> None:
    source = _manifest_agents()[0]
    dangling = project_workforce_contract(
        {
            **source,
            "composition": {"complements": ["missing-agent"]},
        }
    )

    with pytest.raises(ValueError, match="targets unknown agents"):
        workforce_index_fingerprint([dangling])


def test_projection_rejects_unbounded_or_invalid_contracts() -> None:
    source = _manifest_agents()[0]

    with pytest.raises(ValueError, match="outcomes exceeds 8 items"):
        project_workforce_contract({**source, "outcomes": [str(i) for i in range(9)]})
    with pytest.raises(ValueError, match="display_name exceeds 128 bytes"):
        project_workforce_contract({**source, "display_name": "x" * 129})
    with pytest.raises(ValueError, match="unsupported workforce authority"):
        project_workforce_contract({**source, "authority": "approve"})
    with pytest.raises(ValueError, match="employment must agree"):
        project_workforce_contract({**source, "employment": "disabled"})
    with pytest.raises(ValueError, match="supported host identifiers"):
        project_workforce_contract({**source, "supported_hosts": ["imaginary-host"]})
    with pytest.raises(ValueError, match="require ontology review"):
        project_workforce_contract({**source, "capability_ids": ["unreviewed-upstream-skill"]})


def test_explicitly_empty_artifact_kinds_is_rejected_not_wildcarded() -> None:
    source = _manifest_agents()[0]

    with pytest.raises(ValueError, match="must not be explicitly empty"):
        project_workforce_contract({**source, "artifact_kinds": []})
    with pytest.raises(ValueError, match="must not be explicitly empty"):
        project_workforce_contract({**source, "artifact_kinds": None})


def test_explicit_artifact_kinds_need_at_least_one_vocabulary_member() -> None:
    source = _manifest_agents()[0]

    with pytest.raises(ValueError, match="at least one artifact-vocabulary kind"):
        project_workforce_contract({**source, "artifact_kinds": ["scene-change"]})

    mixed = project_workforce_contract(
        {**source, "artifact_kinds": ["implementation-change", "scene-change"]}
    )
    assert mixed.artifact_kinds == ("implementation-change", "scene-change")


def test_agency_contractor_can_extend_the_versioned_capability_ontology() -> None:
    source = _manifest_agents()[0]
    contractor = project_workforce_contract(
        {
            **source,
            "origin": "agency",
            "employment": "contractor",
            "capability_ids": ["novel-reviewed-specialty"],
        },
        origin="agency",
    )

    assert contractor.capability_ids[0] == "novel-reviewed-specialty"
    assert set(contractor.capability_ids[1:]) <= CORE_CAPABILITY_IDS


def test_explicit_normalized_fields_override_conservative_derivation() -> None:
    source = _manifest_agents()[0]
    contract = project_workforce_contract(
        {
            **source,
            "archetype": "spatial-implementer",
            "artifact_kinds": ["implementation-change", "scene-change"],
            "lifecycle_phases": ["implementation", "verification"],
            "domains": ["geospatial"],
            "stacks": ["cesium"],
            "scope_qualifiers": ["Browser-based 3D scene"],
            "not_for": ["2D static cartography"],
            "tool_classes": ["geospatial", "browser"],
            "composition": {
                "substitution_group": "gis-scene-builders",
                "complements": ["gis-qa-engineer"],
                "must_follow": ["solution-engineer"],
                "must_review_independently": ["accessibility-auditor"],
                "independence_class": "gis-3d-scenes",
            },
        }
    )

    assert contract.archetype == "spatial-implementer"
    assert contract.stacks == ("cesium",)
    assert contract.composition.substitution_group == "gis-scene-builders"
    assert contract.composition.complements == ("gis-qa-engineer",)
    assert contract.composition.must_review_independently == ("accessibility-auditor",)
    assert contract.composition.same_context_conflicts == ()


def test_testing_archetype_always_has_testing_lifecycle() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "test-results-analyzer")

    contract = project_workforce_contract(source)

    assert contract.archetype == "tester"
    assert "test-evidence" in contract.artifact_kinds
    assert "testing" in contract.lifecycle_phases


def test_writer_archetype_always_has_documentation_lifecycle() -> None:
    source = next(agent for agent in _manifest_agents() if agent["slug"] == "technical-writer")

    contract = project_workforce_contract(source)

    assert contract.archetype == "writer"
    assert "documentation" in contract.artifact_kinds
    assert contract.lifecycle_phases[0] == "documentation"


def test_terse_recruiter_index_contains_every_bundled_worker_and_required_field() -> None:
    contracts = [project_workforce_contract(agent) for agent in _manifest_agents()]
    records = [project_recruiter_index_record(contract) for contract in contracts]
    serialized = serialize_recruiter_index(records)
    payload = json.loads(serialized)

    assert len(payload["workers"]) == 263
    assert tuple(payload["fields"]) == RECRUITER_INDEX_FIELDS
    assert tuple(payload["composition_fields"]) == COMPOSITION_INDEX_FIELDS
    assert all(len(row) == len(RECRUITER_INDEX_FIELDS) for row in payload["workers"])
    assert all(
        len(row[RECRUITER_INDEX_FIELDS.index("composition")]) == len(COMPOSITION_INDEX_FIELDS)
        for row in payload["workers"]
    )
    assert recruiter_index_fingerprint(records) == recruiter_index_fingerprint(
        list(reversed(records))
    )


def test_terse_recruiter_index_is_materially_smaller_than_full_contracts() -> None:
    contracts = [project_workforce_contract(agent) for agent in _manifest_agents()]
    full = json.dumps(
        [contract.to_dict() for contract in contracts],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    terse = serialize_recruiter_index(
        [project_recruiter_index_record(contract) for contract in contracts]
    ).encode("utf-8")

    assert len(terse) < len(full) * 0.75


def test_terse_recruiter_index_keeps_disabled_workers_visible() -> None:
    writer = next(agent for agent in _manifest_agents() if agent["slug"] == "technical-writer")
    record = project_recruiter_index_record(
        project_workforce_contract(writer, disabled={"technical-writer"})
    )
    payload = json.loads(serialize_recruiter_index([record]))
    row = dict(zip(payload["fields"], payload["workers"][0], strict=True))

    assert row["slug"] == "technical-writer"
    assert row["employment_status"] == "disabled"
    assert row["enabled"] is False


def test_terse_recruiter_index_rejects_duplicate_identities() -> None:
    contract = project_workforce_contract(_manifest_agents()[0])
    record = project_recruiter_index_record(contract)

    with pytest.raises(ValueError, match="duplicate worker ids"):
        serialize_recruiter_index([record, record])
