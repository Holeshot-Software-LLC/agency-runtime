"""Exact packaged installation authority for Agency's known contractors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.revisions import serialized_revision_metadata
from agency_runtime.core.workforce.contract import (
    WorkforceContract,
    project_workforce_contract,
)
from agency_runtime.core.workforce.hiring_contract import (
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

# These are the exact prompt identities emitted by the package-v1 definitions
# that preceded executable contractor profiles. Reconstructing v1 only by
# deleting today's execution profile is unsafe: a later edit to any other
# contract field would silently redefine which stored worker is eligible for a
# package-owned advance. The digest manifest makes that drift fail closed.
_LEGACY_KNOWN_CONTRACTOR_PROMPT_HASHES: dict[str, str] = {
    "ai-evaluation-engineer": "sha256:ccb4d23ca5be91e422f804dbf6871896d364d3344a59f5d03a7828d4e5d8ac2e",
    "ai-governance-auditor": "sha256:2311a03f3050c1f0e4b999e9e14a573ea2bf24d53aa65e1c45506c5d0bb019f7",
    "ai-observability-engineer": "sha256:52e7b9c5133eb1ef895f0278664e09b396393dda95758170ee73d5bdca8d67a2",
    "application-integration-verifier": "sha256:37ce9785a65d96e6351b7004fb67460e31848d49811a620983d9bd4f37417f4f",
    "application-observability-engineer": "sha256:2ab966106f90e29494b80471ae6885720abb5b40f111943434f8f04a00cbc4a6",
    "backend-service-engineer": "sha256:725012e8efadfc90f1b87c141001e3cb6d52b6889aff828f792343a97dbd80f5",
    "cross-platform-installer-engineer": "sha256:4c4121a5228884acf808960a914744cbe12b95c594aca7e6dccebc2fe9669d20",
    "cross-platform-release-verifier": "sha256:5b41b516cc1bea8d2109c92649800e769f24058c44db1ae388243fc088596820",
    "documentation-evidence-researcher": "sha256:68c8bcde8d696cca4175679029c2e2d4b05d73373bb56e1e2cf4d2b0db72adba",
    "hallucination-root-cause-investigator": "sha256:ee6a95ad85cf8035970c560c50241b2756c1d923e2589dfa9b1899f6b98a99a0",
    "policy-guardrail-architect": "sha256:41bb27e28ae72ed0144810b13d165d2915c1720f8233d5203a318085e6d59a7d",
    "python-application-engineer": "sha256:27736661ee05c968bbfb41e782aed925b5c556c1d6baf83f624f8f7e50254308",
    "selection-safety-critic": "sha256:5357971f306118e9b34efaefb6b4c0df8a0c369b2c0ac9ce371f42bcfef3669a",
    "software-test-engineer": "sha256:2b141081edc3394581aa5cf2241c8a76c938f46253855b504216de80f3970c34",
    "typescript-application-engineer": "sha256:5e6a02cdaaf0bfdea4dcb4e8ec9c5a493ada09258a47554a0f7aa917344cd412",
}

_LEGACY_BACKEND_CAPABILITIES = (
    "api execution paths",
    "persistence integration",
    "concurrency and failure handling",
)
_LEGACY_BACKEND_EVIDENCE_REQUIREMENTS = ("changed artifacts and focused verification results",)


@dataclass(frozen=True, slots=True)
class KnownContractorPackage:
    employment_contract: EmploymentContract
    compiled: CompiledContractor
    agent: dict[str, Any]
    workforce_contract: WorkforceContract


@dataclass(frozen=True, slots=True)
class KnownContractorInstallResult:
    installed: tuple[str, ...]
    upgraded: tuple[str, ...]
    existing: tuple[str, ...]
    preserved: tuple[str, ...]


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


def _known_contractor_agent(contract: EmploymentContract) -> dict[str, Any]:
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
    version = contractor_prompt_version(
        compiled.prompt_hash,
        template_version=compiled.template_version,
    )
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
        "source_version": compiled.template_version,
        "source_revision": compiled.template_hash,
        "source_content_hash": compiled.prompt_hash,
        "audit_revision": f"package-v{compiled.template_version}-{compiled.template_hash[7:23]}",
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


def known_contractor_agent(contract: EmploymentContract) -> dict[str, Any]:
    """Compile one exact current package-owned agent record from a closed contract."""

    canonical = KNOWN_CONTRACTORS_BY_SLUG.get(contract.slug)
    if canonical is None or canonical != contract:
        raise ValueError("known contractor is not an exact packaged definition")
    return _known_contractor_agent(contract)


def known_contractor_package(slug: str) -> KnownContractorPackage:
    contract = KNOWN_CONTRACTORS_BY_SLUG.get(str(slug or "").strip().casefold())
    if contract is None:
        raise KeyError("known contractor is not packaged")
    compiled = compile_contractor(contract)
    agent = known_contractor_agent(contract)
    workforce = project_workforce_contract(agent, origin="agency")
    return KnownContractorPackage(contract, compiled, agent, workforce)


def _legacy_known_contractor_package(slug: str) -> KnownContractorPackage:
    """Reconstruct the exact v1 package predecessor eligible for a governed advance."""

    normalized = str(slug or "").strip().casefold()
    current = KNOWN_CONTRACTORS_BY_SLUG.get(normalized)
    if current is None:
        raise KeyError("known contractor is not packaged")
    changes: dict[str, Any] = {"schema_version": 1, "execution_profile": None}
    if normalized == "backend-service-engineer":
        # This contract gained additional non-profile guidance before AR-264
        # merged. Preserve the package-v1 fields instead of back-projecting
        # those newer values into historical evidence.
        changes.update(
            capabilities=_LEGACY_BACKEND_CAPABILITIES,
            evidence_requirements=_LEGACY_BACKEND_EVIDENCE_REQUIREMENTS,
        )
    contract = replace(current, **changes)
    compiled = compile_contractor(contract)
    expected_hash = _LEGACY_KNOWN_CONTRACTOR_PROMPT_HASHES.get(normalized)
    if compiled.prompt_hash != expected_hash:
        raise RuntimeError(f"legacy known contractor snapshot drifted: {normalized}")
    # AR-264 normalized audit-revision spelling for new packages. The v1
    # predecessor retained the template hash's ``sha256:`` prefix here.
    agent = {
        **_known_contractor_agent(contract),
        "audit_revision": (f"package-v{compiled.template_version}-{compiled.template_hash[:16]}"),
    }
    workforce = project_workforce_contract(agent, origin="agency")
    return KnownContractorPackage(contract, compiled, agent, workforce)


def _malformed_legacy_known_contractor_package(slug: str) -> KnownContractorPackage:
    """Reconstruct package v1 before the August 6 version-identity repair."""

    package = _legacy_known_contractor_package(slug)
    agent = {
        **package.agent,
        "version": (
            f"contractor-{package.compiled.template_version}-{package.compiled.prompt_hash[:16]}"
        ),
    }
    workforce = project_workforce_contract(agent, origin="agency")
    return KnownContractorPackage(
        package.employment_contract,
        package.compiled,
        agent,
        workforce,
    )


def _known_contractor_predecessor_packages(slug: str) -> tuple[KnownContractorPackage, ...]:
    """Return the two exact package-v1 identities that shipped before v2."""

    normalized = str(slug or "").strip().casefold()
    if normalized not in _LEGACY_KNOWN_CONTRACTOR_PROMPT_HASHES:
        return ()
    return (
        _legacy_known_contractor_package(normalized),
        _malformed_legacy_known_contractor_package(normalized),
    )


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
            "compiler_template_hash": package.compiled.template_hash,
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
        slug = str(row["proposed_slug"])
        packages = (
            known_contractor_package(slug),
            *_known_contractor_predecessor_packages(slug),
        )
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
    except (KeyError, TypeError, ValueError):
        return False
    case_type = str(row.get("case_type") if hasattr(row, "get") else row["case_type"])
    for index, package in enumerate(packages):
        allowed_types = {"hire", "amend"} if index == 0 else {"hire"}
        expected_target = None if case_type == "hire" else package.compiled.worker_id
        expected = packaged_hiring_evidence(package)
        expected_contract = json.loads(
            json.dumps(
                package.workforce_contract.to_dict(),
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        if bool(
            case_type in allowed_types
            and row["target_worker_id"] == expected_target
            and contract == expected_contract
            and critic == expected["critic_evidence"]
            and model == expected["model_evidence"]
            and str(row["risk_tier"]) == "standard"
            and not bool(row["human_approval_required"])
        ):
            return True
    return False


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
    upgraded: list[str] = []
    existing: list[str] = []
    preserved: list[str] = []
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
            if (
                worker["current_hash"] == package.compiled.prompt_hash
                and worker.get("current_version") == package.agent["version"]
            ):
                existing.append(slug)
                continue
            predecessors = _known_contractor_predecessor_packages(slug)
            prompt_reader = getattr(store, "get_specialist_prompt", None)
            prior_prompt = (
                prompt_reader(slug, max_chars=262_144, disabled_agents=())
                if callable(prompt_reader)
                else None
            )
            detail_reader = getattr(store, "get_workforce_worker_detail", None)
            prior_detail = (
                detail_reader(
                    slug,
                    evidence_limit=1,
                    disabled_agents=(),
                    include_history_documents=False,
                )
                if callable(detail_reader)
                else None
            )
            exact_predecessor = any(
                worker.get("current_hash") == candidate.compiled.prompt_hash
                and worker.get("current_version") == candidate.agent["version"]
                and isinstance(prior_prompt, Mapping)
                and prior_prompt.get("hash") == candidate.compiled.prompt_hash
                and prior_prompt.get("version") == candidate.agent["version"]
                and prior_prompt.get("prompt_body") == candidate.compiled.prompt
                and prior_prompt.get("prompt_truncated") is False
                and isinstance(prior_detail, Mapping)
                and prior_detail.get("recruitment_contract")
                == json.loads(
                    json.dumps(
                        candidate.workforce_contract.to_dict(),
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                )
                for candidate in predecessors
            )
            if not exact_predecessor:
                # Never overwrite an owner or inference-authored amendment just
                # because its active identity differs from today's package.
                preserved.append(slug)
                continue
            version_id = store.stage_agency_packaged_workforce_revision(
                package.agent,
                expected_revision=int(worker["revision"]),
            )
            evidence = packaged_hiring_evidence(package)
            contract_document = package.workforce_contract.to_dict()
            case = store.create_hiring_case(
                case_type="amend",
                proposed_slug=slug,
                target_worker_id=str(worker["worker_id"]),
                work_unit_id=f"known-{slug}-package-v{package.compiled.template_version}",
                request_hash=_request_hash(package),
                contract_evidence=contract_document,
                contract_hash=hashlib.sha256(
                    json.dumps(
                        contract_document,
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
                raise RuntimeError(f"known contractor amendment case is not usable: {slug}")
            store.apply_workforce_amendment(
                slug,
                expected_revision=int(worker["revision"]),
                agent_version_id=version_id,
                recruitment_contract=contract_document,
                hiring_case_id=case["id"],
                event_actor="agency-runtime",
                event_surface="package-upgrade",
                event_reason="exact packaged contractor revision advance",
            )
            upgraded.append(slug)
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
    return KnownContractorInstallResult(
        tuple(installed),
        tuple(upgraded),
        tuple(existing),
        tuple(preserved),
    )


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
