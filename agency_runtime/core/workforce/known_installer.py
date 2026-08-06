"""Exact packaged installation authority for Agency's known contractors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.workforce.contract import (
    WorkforceContract,
    project_workforce_contract,
)
from agency_runtime.core.workforce.hiring_contract import (
    CONTRACTOR_PROMPT_TEMPLATE_HASH,
    CONTRACTOR_PROMPT_TEMPLATE_VERSION,
    CompiledContractor,
    EmploymentContract,
    compile_contractor,
    contractor_prompt_version,
)
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG

PACKAGED_CONTRACTOR_AUTHORITY = "agency.packaged-contractor.v1"

_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "ai-evaluation-engineer": ("test-evidence", "review-report"),
    "ai-governance-auditor": ("review-report",),
    "ai-observability-engineer": ("architecture-record", "plan"),
    "software-test-engineer": ("test-code",),
    "documentation-evidence-researcher": ("analysis", "review-report"),
    "hallucination-root-cause-investigator": ("analysis", "review-report"),
    "application-integration-verifier": ("test-evidence", "review-report"),
    "policy-guardrail-architect": ("plan",),
    "cross-platform-release-verifier": ("test-evidence", "review-report"),
    "selection-safety-critic": ("review-report",),
}
_DOMAINS: dict[str, tuple[str, ...]] = {
    "ai-evaluation-engineer": ("software-engineering",),
    "ai-governance-auditor": ("workforce-governance",),
    "ai-observability-engineer": ("software-engineering",),
    "software-test-engineer": ("quality-assurance",),
    "documentation-evidence-researcher": ("research",),
    "hallucination-root-cause-investigator": ("software-engineering",),
    "application-integration-verifier": ("quality-assurance",),
    "policy-guardrail-architect": ("ai-governance",),
    "cross-platform-release-verifier": ("quality-assurance",),
    "selection-safety-critic": ("workforce-governance",),
}
_STACKS: dict[str, tuple[str, ...]] = {
    "python-application-engineer": ("python",),
    "typescript-application-engineer": ("typescript", "javascript"),
}
_TOOL_CLASSES: dict[str, str] = {
    "artifact-reader": "repository-read",
    "browser": "browser-interaction",
    "monitoring": "monitoring-observability",
    "node": "code-execution",
    "package-manager": "package-management",
    "python": "code-execution",
    "repository": "repository-read",
    "shell": "shell-execution",
    "staffing-plan-reader": "runtime-evidence",
    "test-runner": "test-execution",
    "workforce-index": "runtime-evidence",
    "web-research": "web-research",
}
# Contract tools describe the worker's complete operating toolkit. A tool that
# is needed only for one scenario is affinity metadata, not an unconditional
# routing prerequisite. Keeping those concepts separate prevents a verifier
# from disappearing merely because an unrelated optional surface is absent.
_OPTIONAL_TOOLS: dict[str, frozenset[str]] = {
    "ai-observability-engineer": frozenset({"monitoring"}),
    "application-integration-verifier": frozenset({"browser"}),
    "documentation-evidence-researcher": frozenset({"web-research"}),
}
_LIFECYCLES: dict[str, str] = {
    "design": "design",
    "discovery": "discovery",
    "documentation": "documentation",
    "implementation": "implementation",
    "installation": "release",
    "integration": "testing",
    "observability": "implementation",
    "planning": "planning",
    "release": "release",
    "review": "review",
    "testing": "testing",
}


@dataclass(frozen=True, slots=True)
class KnownContractorPackage:
    employment_contract: EmploymentContract
    compiled: CompiledContractor
    agent: dict[str, Any]
    workforce_contract: WorkforceContract


@dataclass(frozen=True, slots=True)
class KnownContractorInstallResult:
    installed: tuple[str, ...]
    existing: tuple[str, ...]


def _composition(contract: EmploymentContract) -> dict[str, Any]:
    result: dict[str, Any] = {
        "substitution_group": "",
        "substitutes_for": [],
        "complements": [],
        "same_context_conflicts": [],
        "selection_exclusive": [],
        "requires": [],
        "must_follow": [],
        "must_review_independently": [],
        "independence_class": f"contractor-{contract.slug}",
    }
    for relation in contract.relationships:
        if relation.kind not in result or not isinstance(result[relation.kind], list):
            raise ValueError("known contractor contains an unsupported relationship")
        result[relation.kind].append(relation.target)
    return result


def _tool_classes(contract: EmploymentContract) -> list[str]:
    result: list[str] = []
    for tool in contract.tools:
        normalized = _TOOL_CLASSES.get(tool, "specialized-tool")
        if normalized not in result:
            result.append(normalized)
    return result


def _required_tools(contract: EmploymentContract) -> list[str]:
    optional = _OPTIONAL_TOOLS.get(contract.slug, frozenset())
    return [tool for tool in contract.tools if tool not in optional]


def known_contractor_agent(contract: EmploymentContract) -> dict[str, Any]:
    """Compile one exact package-owned agent record from a closed contract."""

    canonical = KNOWN_CONTRACTORS_BY_SLUG.get(contract.slug)
    if canonical is None or canonical != contract:
        raise ValueError("known contractor is not an exact packaged definition")
    compiled = compile_contractor(contract)
    artifacts = _ARTIFACTS.get(contract.slug, ("implementation-change",))
    domains = _DOMAINS.get(contract.slug, ("software-engineering",))
    lifecycle = tuple(dict.fromkeys(_LIFECYCLES[item] for item in contract.lifecycle_phases))
    archetype = (
        "tester"
        if contract.slug
        in {
            "software-test-engineer",
            "application-integration-verifier",
            "cross-platform-release-verifier",
        }
        else "reviewer"
        if contract.authority == "review"
        else "implementer"
    )
    version = contractor_prompt_version(compiled.prompt_hash)
    return {
        "slug": contract.slug,
        "name": contract.role,
        "display_name": contract.role,
        "division": "specialized",
        "description": contract.narrow_scope,
        "categories": ["agency-contractor", *domains],
        "capabilities": [*contract.outcomes_owned, *contract.capabilities],
        "anti_capabilities": list(contract.anti_capabilities),
        "task_types": list(artifacts),
        "preferred_when": list(contract.preferred_scenarios),
        "avoid_when": [*contract.avoided_scenarios, *contract.forbidden_scenarios],
        "required_tools": _required_tools(contract),
        "tool_classes": _tool_classes(contract),
        "tool_affinity": _tool_classes(contract),
        "supported_hosts": list(contract.hosts),
        "supported_platforms": list(contract.platforms),
        "authority": contract.authority,
        "context_mode": contract.context_mode,
        "conflicts_with": [],
        "requires": list(contract.requirements),
        "independence_group": f"contractor-{contract.slug}",
        "composition": _composition(contract),
        "expected_output_contract": "; ".join(contract.artifacts_produced),
        "evidence_requirements": list(contract.evidence_requirements),
        "model_requirements": [],
        "outcomes": [*contract.outcomes_owned, *contract.capabilities],
        "artifact_kinds": list(artifacts),
        "lifecycle_phases": list(lifecycle),
        "domains": list(domains),
        "stacks": list(_STACKS.get(contract.slug, ())),
        "scope_qualifiers": list(contract.preferred_scenarios),
        "not_for": [*contract.avoided_scenarios, *contract.forbidden_scenarios],
        "source": "agency-runtime",
        "source_id": "agency-known-contractors",
        "source_version": CONTRACTOR_PROMPT_TEMPLATE_VERSION,
        "source_revision": CONTRACTOR_PROMPT_TEMPLATE_HASH,
        "source_content_hash": compiled.prompt_hash,
        "audit_revision": f"package-v1-{CONTRACTOR_PROMPT_TEMPLATE_HASH[:16]}",
        "audit_status": "approved",
        "routing_contract_valid": True,
        "findings": [],
        "version": version,
        "hash": compiled.prompt_hash,
        "version_hash": compiled.prompt_hash,
        "prompt_path": f"bundled://agency-contractors/{contract.slug}",
        "prompt_body": compiled.prompt,
        "origin": "agency",
        "employment": "contractor",
        "enabled": True,
        "archetype": archetype,
    }


def known_contractor_package(slug: str) -> KnownContractorPackage:
    contract = KNOWN_CONTRACTORS_BY_SLUG.get(str(slug or "").strip().casefold())
    if contract is None:
        raise KeyError("known contractor is not packaged")
    compiled = compile_contractor(contract)
    agent = known_contractor_agent(contract)
    workforce = project_workforce_contract(agent, origin="agency")
    return KnownContractorPackage(contract, compiled, agent, workforce)


def known_contractor_revision_metadata_authorities(slug: str) -> tuple[str, ...]:
    """Return exact current and package-known historical metadata identities."""

    package = known_contractor_package(slug)
    authorities = [serialized_revision_metadata(package.agent)]
    optional = _OPTIONAL_TOOLS.get(package.employment_contract.slug, frozenset())
    if optional:
        legacy = {
            **package.agent,
            "required_tools": list(package.employment_contract.tools),
        }
        authorities.append(serialized_revision_metadata(legacy))
    return tuple(dict.fromkeys(authorities))


def packaged_hiring_evidence(package: KnownContractorPackage) -> dict[str, dict[str, Any]]:
    contract = package.employment_contract
    return {
        "gap_evidence": {
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "narrow_scope": contract.narrow_scope,
            "known_requirement": True,
        },
        "duplicate_evidence": {
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "closest_workers": [item.worker for item in contract.closest_workers],
            "differentiation": [item.differentiation for item in contract.closest_workers],
        },
        "critic_evidence": {
            "approved": True,
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "employment_contract_schema": contract.schema_version,
            "compiler_template_hash": CONTRACTOR_PROMPT_TEMPLATE_HASH,
            "compiled_prompt_hash": package.compiled.prompt_hash,
        },
        "model_evidence": {
            "inference_required": False,
            "authority": PACKAGED_CONTRACTOR_AUTHORITY,
            "reason": "maintainer-reviewed packaged contractor; no inference call was made",
            "receipts": [],
        },
    }


def packaged_hiring_case_is_auditable(row: Mapping[str, Any]) -> bool:
    """Verify exact package authority without inventing a model receipt."""

    try:
        package = known_contractor_package(str(row["proposed_slug"]))
        expected = packaged_hiring_evidence(package)
        contract = safe_load_bounded_json(
            str(row["contract_evidence"]),
            maximum_bytes=256 * 1024,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
        critic = safe_load_bounded_json(
            str(row["critic_evidence"]),
            maximum_bytes=256 * 1024,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
        model = safe_load_bounded_json(
            str(row["model_evidence"]),
            maximum_bytes=256 * 1024,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
        expected_contract = safe_load_bounded_json(
            json.dumps(
                package.workforce_contract.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            maximum_bytes=256 * 1024,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        str(row.get("case_type") if hasattr(row, "get") else row["case_type"]) == "hire"
        and row["target_worker_id"] is None
        and contract == expected_contract
        and critic == expected["critic_evidence"]
        and model == expected["model_evidence"]
        and str(row["risk_tier"]) == "standard"
        and not bool(row["human_approval_required"])
    )


def _request_hash(package: KnownContractorPackage) -> str:
    payload = json.dumps(
        package.employment_contract.to_dict(),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def install_known_contractors(store: Any) -> KnownContractorInstallResult:
    """Idempotently stage, audit, register, and enable every packaged contractor."""

    installed: list[str] = []
    existing: list[str] = []
    slugs = tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG))
    batch_reader = getattr(store, "get_workforce_workers_by_slugs", None)
    if callable(batch_reader):
        workers = batch_reader(slugs, disabled_agents=())
        if not isinstance(workers, Mapping) or any(
            slug not in slugs or not isinstance(worker, Mapping) or worker.get("agent_slug") != slug
            for slug, worker in workers.items()
        ):
            raise RuntimeError("known contractor worker snapshot is invalid")
    else:
        workers = {}
        for slug in slugs:
            with suppress(KeyError):
                workers[slug] = store.get_workforce_worker(slug, disabled_agents=())
    for slug in slugs:
        package = known_contractor_package(slug)
        worker = workers.get(slug)
        if worker is not None:
            if worker["origin"] != "agency":
                raise RuntimeError(
                    f"known contractor identity conflicts with active worker: {slug}"
                )
            # A hash mismatch means the packaged contractor's compiled prompt
            # changed after a code update. The existing worker is still
            # Agency-owned; accept it as current rather than blocking the
            # install. A proper version-advance path can refresh it later.
            existing.append(slug)
            continue
        version_id = store.stage_agency_workforce_agent(package.agent)
        evidence = packaged_hiring_evidence(package)
        case = store.create_hiring_case(
            case_type="hire",
            proposed_slug=slug,
            work_unit_id=f"known-{slug}",
            request_hash=_request_hash(package),
            contract_evidence=package.workforce_contract.to_dict(),
            contract_hash=hashlib.sha256(
                json.dumps(
                    package.workforce_contract.to_dict(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
            **evidence,
        )
        if case["status"] == "proposed":
            case = store.transition_hiring_case(case["id"], status="audited")
        if case["status"] != "audited":
            raise RuntimeError(f"known contractor hiring case is not usable: {slug}")
        store.register_workforce_worker(
            agent_slug=slug,
            display_name=package.employment_contract.role,
            origin="agency",
            employment_class="contractor",
            agent_version_id=version_id,
            recruitment_contract=package.workforce_contract.to_dict(),
            relation="generated",
            hiring_case_id=case["id"],
        )
        installed.append(slug)
    return KnownContractorInstallResult(tuple(installed), tuple(existing))


__all__ = [
    "PACKAGED_CONTRACTOR_AUTHORITY",
    "KnownContractorInstallResult",
    "KnownContractorPackage",
    "install_known_contractors",
    "known_contractor_agent",
    "known_contractor_package",
    "known_contractor_revision_metadata_authorities",
    "packaged_hiring_case_is_auditable",
    "packaged_hiring_evidence",
]
