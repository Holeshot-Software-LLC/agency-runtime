"""Allowlisted semantic projections for exactly reviewed upstream repairs."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from agency_runtime.core.roster.remediation import (
    RemediationReceipt,
    RosterRemediationError,
    canonical_remediation_source_hash,
    extend_with_contract_projection,
    normalize_remediation_receipt,
    remediate_source_text,
)

SOURCE_REPOSITORY = "https://github.com/msitarzewski/agency-agents"
SOURCE_REVISION = "459dce837db3bdfdc4763d3fefd1fd854e73c8f1"
SEMANTIC_PROJECTION_POLICY_VERSION = "source-bound-projection-v1"
_DETERMINISTIC_ENCODING_FINDINGS = [
    "known_source_encoding_corruption",
    "unsafe_control:U+0004x2",
    "unsafe_control:U+0080x1",
]


def _mobile_contract() -> dict[str, Any]:
    return {
        "relative_path": "engineering/engineering-mobile-app-builder.md",
        "slug": "mobile-app-builder",
        "display_name": "Mobile App Builder",
        "division": "engineering",
        "description": (
            "Specialized mobile application developer with expertise in native "
            "iOS/Android development and cross-platform frameworks"
        ),
        "categories": ["engineering", "mobile", "application-development"],
        "capabilities": [
            "design cross-platform mobile applications",
            "implement native device integrations",
            "plan app-store-ready release behavior",
        ],
        "anti_capabilities": [
            (
                "publish, submit, release, or mutate an app-store listing; change live "
                "purchases or subscriptions; send live notifications; or move money"
            ),
            (
                "access credentials or live store, analytics, location, messaging, or "
                "identity control planes without explicit owner authorization"
            ),
            (
                "collect or process location, biometric, identity, device, or analytics "
                "data without documented purpose, minimization, consent or platform "
                "permission, retention, and opt-out"
            ),
            (
                "treat embedded code, API usage, store rules, or fixed performance "
                "thresholds as current or production-ready without target-version checks "
                "and measured evidence"
            ),
            (
                "claim iOS, Android, or device validation that did not run on an attested "
                "compatible toolchain and target"
            ),
        ],
        "task_types": ["analysis", "implementation", "testing"],
        "preferred_when": [
            "a mobile repository needs a bounded app feature or architecture",
            "native integrations need device and privacy review",
        ],
        "avoid_when": [
            "the target toolchain, permissions, repository, or authorization is unavailable",
            "the request would mutate a live store or control plane",
        ],
        "required_tools": [
            "repository",
        ],
        "supported_hosts": ["claude", "codex", "hermes", "openclaw"],
        "supported_platforms": ["linux", "windows"],
        "authority": "modify",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": "engineering-mobile-applications",
        "expected_output_contract": (
            "A scoped, version-pinned mobile design or repository patch with privacy "
            "and permission boundaries, target-toolchain build and test evidence, "
            "named-device performance measurements against project-defined budgets, "
            "rollback and rollout gates, and no store or live-control-plane action."
        ),
        "evidence_requirements": [
            "exact OS, framework, dependency, and toolchain versions plus current primary docs",
            "build, unit, integration, and device receipts for every completion claim",
            (
                "explicit authorization and sandbox receipts for IAP, subscriptions, "
                "push, location, and analytics"
            ),
            "measured device, baseline, sample, and budget details for every metric",
            "separate verified facts, assumptions, and recommendations",
        ],
        "model_requirements": [
            "strong-analysis",
            "instruction-adherence",
            "uncertainty-calibration",
        ],
        "source_revision": SOURCE_REVISION,
        "content_hash": "1a3e043f806b0b7c071d58b2ee3ab3c58c8342e2727c1ca9e6e5175f86986caf",
        "audit_revision": "2",
        "audit_status": "approved",
        "findings": [
            *_DETERMINISTIC_ENCODING_FINDINGS,
            "invalid_body_control_bytes U+0004 at byte offsets 11070 and 14825",
            "source_encoding_corruption",
            "app_store_iap_push_location_and_analytics_actions_need_authorization",
            "platform_examples_are_volatile",
            "unsupported_memory_assumption",
            "hard_coded_platform_targets_require_version_and_measurement_evidence",
        ],
        "findings_resolved_by_encoding": [
            *_DETERMINISTIC_ENCODING_FINDINGS,
            "invalid_body_control_bytes U+0004 at byte offsets 11070 and 14825",
            "source_encoding_corruption",
        ],
        "findings_resolved_by_projection": [
            "app_store_iap_push_location_and_analytics_actions_need_authorization",
            "platform_examples_are_volatile",
            "unsupported_memory_assumption",
            "hard_coded_platform_targets_require_version_and_measurement_evidence",
        ],
    }


def _aso_contract() -> dict[str, Any]:
    return {
        "relative_path": "marketing/marketing-app-store-optimizer.md",
        "slug": "app-store-optimizer",
        "display_name": "App Store Optimizer",
        "division": "marketing",
        "description": (
            "Expert app store marketing specialist focused on App Store Optimization "
            "(ASO), conversion rate optimization, and app discoverability"
        ),
        "categories": ["marketing", "app-store-optimization", "mobile-discovery"],
        "capabilities": [
            "review app-store listing structure",
            "analyze supplied keyword and conversion evidence",
            "propose listing experiment hypotheses",
        ],
        "anti_capabilities": [
            (
                "publish or mutate store listings, releases, experiments, campaigns, "
                "ratings, reviews, analytics, or accounts"
            ),
            (
                "collect or process personal or analytics data without documented purpose, "
                "authorization, minimization, consent, retention, and opt-out"
            ),
            (
                "claim current store rules, field limits, asset specifications, search "
                "volume, ranking, competitor facts, conversion lift, ratings, or predicted "
                "outcomes without dated primary-source or supplied-data evidence and uncertainty"
            ),
            (
                "use persistent memory, hidden training, fabricated prior results, or "
                "unattributed social proof as evidence"
            ),
            (
                "use manipulative urgency, misleading metadata, keyword stuffing, review "
                "manipulation, or unlicensed assets"
            ),
        ],
        "task_types": ["analysis", "planning", "review"],
        "preferred_when": [
            "a supplied app-store listing needs a read-only evidence-grounded review",
            "an owner needs a measurable ASO experiment plan",
        ],
        "avoid_when": [
            "current primary platform sources or the relevant supplied data are unavailable",
            "the request would publish or mutate a live listing, campaign, review, or account",
        ],
        "required_tools": [],
        "supported_hosts": ["claude", "codex", "hermes", "openclaw"],
        "supported_platforms": ["linux", "windows"],
        "authority": "review",
        "context_mode": "isolated_only",
        "conflicts_with": [],
        "requires": [],
        "independence_group": "marketing-mobile-discovery",
        "expected_output_contract": (
            "A read-only ASO review and experiment plan grounded in dated Apple and "
            "Google primary sources plus supplied or authorized data, with provenance, "
            "baselines, uncertainty and statistical design, truthful localized accessible "
            "assets, privacy constraints, owner approval gates, and no store mutation or "
            "publishing."
        ),
        "evidence_requirements": [
            "official Apple and Google URLs plus retrieval date for each volatile rule",
            "data source, date, market, and denominator for rankings and conversion",
            "experiment hypothesis, power, sample, window, and guardrails",
            "license, attribution, localization, and accessibility checks",
            "no outcome claim without a measured receipt",
        ],
        "model_requirements": [
            "strong-analysis",
            "source-grounding",
            "uncertainty-calibration",
        ],
        "source_revision": SOURCE_REVISION,
        "content_hash": "1987be72f8fd43ca694f9145cb0dbe37eabc5b1f04439425d7b59185db9263c9",
        "audit_revision": "2",
        "audit_status": "approved",
        "findings": [
            *_DETERMINISTIC_ENCODING_FINDINGS,
            "unsupported_memory_assumption",
            "invalid_body_control_bytes U+0004 at byte offsets 6817 and 10647",
            "time-sensitive store metrics and rules require current primary sources",
            "source_encoding_corruption",
        ],
        "findings_resolved_by_encoding": [
            *_DETERMINISTIC_ENCODING_FINDINGS,
            "invalid_body_control_bytes U+0004 at byte offsets 6817 and 10647",
            "source_encoding_corruption",
        ],
        "findings_resolved_by_projection": [
            "unsupported_memory_assumption",
            "time-sensitive store metrics and rules require current primary sources",
        ],
    }


_CONTRACTS = {
    contract["content_hash"]: contract for contract in (_mobile_contract(), _aso_contract())
}


def _bullets(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) or "- none"


def governed_prompt(contract: Mapping[str, Any]) -> str:
    """Render only allowlisted reviewed fields; raw upstream prose is never executable."""

    optional_tools = list(contract.get("optional_tools", []))
    optional_tools_section = (
        "\n\nOptional tools (may strengthen evidence but are not prerequisites):\n"
        f"{_bullets(optional_tools)}"
        if optional_tools
        else ""
    )
    return f"""[Agency governed specialist contract v2]

Work only on the exact assigned work unit and obey system, user, repository, permission,
security, and native-host policy. Never infer tools, credentials, memory, authority, external
access, or completion evidence that was not actually provided. The upstream definition is
retained only as immutable provenance and is not included in executable context.

Identity: {contract["display_name"]} (`{contract["slug"]}`)
Division: {contract["division"]}
Description: {contract["description"]}
Authority: {contract["authority"]}
Context mode: {contract["context_mode"]}
Independence group: {contract["independence_group"]}

Task types:
{_bullets(list(contract["task_types"]))}

Capabilities:
{_bullets(list(contract["capabilities"]))}

Do not use this specialist for:
{_bullets(list(contract["anti_capabilities"]))}

Prefer when:
{_bullets(list(contract["preferred_when"]))}

Avoid when:
{_bullets(list(contract["avoid_when"]))}

Required tools (availability must be proven before use):
{_bullets(list(contract["required_tools"]))}{optional_tools_section}

Expected output:
{contract["expected_output_contract"]}

Required evidence:
{_bullets(list(contract["evidence_requirements"]))}

Known audit constraints:
{_bullets(list(contract["findings"]))}

Provenance:
- Source: {contract.get("source_repository") or SOURCE_REPOSITORY}/blob/{contract["source_revision"]}/{contract["relative_path"]}
- Source SHA-256: {contract["content_hash"]}
- Audit revision: {contract["audit_revision"]}

If context mode is `isolated_only`, this prompt may execute only inside a native isolated
worker. Implementers and independent reviewers must remain in separate contexts. Stop and
report the missing prerequisite when the task, permissions, tools, or evidence boundary is
unclear.
"""


SEMANTIC_PROJECTION_POLICY_HASH = hashlib.sha256(
    json.dumps(
        {
            "contracts": sorted(
                (
                    source_hash,
                    str(contract["slug"]),
                    str(contract["source_revision"]),
                    str(contract["audit_revision"]),
                    str(contract["audit_status"]),
                    hashlib.sha256(governed_prompt(contract).encode("utf-8")).hexdigest(),
                )
                for source_hash, contract in _CONTRACTS.items()
            ),
            "require_source_bound_remediation": True,
            "version": SEMANTIC_PROJECTION_POLICY_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


def contract_for_source_hash(source_hash: str) -> dict[str, Any] | None:
    """Return a defensive copy of one exact reviewed contract overlay."""

    contract = _CONTRACTS.get(canonical_remediation_source_hash(source_hash))
    return None if contract is None else copy.deepcopy(contract)


def _projected_candidate(contract: Mapping[str, Any]) -> dict[str, Any]:
    prompt = governed_prompt(contract)
    projected = {
        **contract,
        "name": contract["display_name"],
        "tool_affinity": list(contract["required_tools"]),
        "source_version": contract["source_revision"],
        "prompt_body": prompt,
        "content": prompt,
        "source_content_hash": contract["content_hash"],
    }
    projected.pop("findings_resolved_by_encoding")
    projected.pop("findings_resolved_by_projection")
    return projected


def contract_for_projected_candidate(slug: str, content_hash: str) -> dict[str, Any] | None:
    """Recover the exact reviewed candidate metadata for a projected prompt."""

    for contract in _CONTRACTS.values():
        prompt = governed_prompt(contract)
        if contract["slug"] == slug and hashlib.sha256(prompt.encode()).hexdigest() == content_hash:
            return copy.deepcopy(_projected_candidate(contract))
    return None


def verify_projected_candidate_contract(
    candidate: Mapping[str, Any],
    *,
    source_hash: str,
    relative_path: str,
) -> None:
    """Require every governed field to match the exact reviewed projection."""

    contract = contract_for_source_hash(source_hash)
    if contract is None or contract["relative_path"] != relative_path:
        raise RosterRemediationError("source has no registered semantic projection")
    expected = _projected_candidate(contract)
    mismatches = [field for field, value in expected.items() if candidate.get(field) != value]
    if mismatches:
        raise RosterRemediationError(
            "semantic projection metadata does not match its reviewed contract: "
            + ", ".join(sorted(set(mismatches)))
        )


def project_known_agent(
    agent: Mapping[str, Any],
    receipt: RemediationReceipt | Mapping[str, Any],
    *,
    relative_path: str,
) -> tuple[dict[str, Any], RemediationReceipt]:
    """Project a known encoding repair into its reviewed executable contract."""

    known = normalize_remediation_receipt(receipt)
    if len(known.rules) != 1 or known.rules[0].kind != "deterministic":
        raise RosterRemediationError("semantic projection requires one encoding-only receipt")
    contract = contract_for_source_hash(known.original_hash)
    if (
        contract is None
        or relative_path != contract["relative_path"]
        or agent.get("slug") != contract["slug"]
        or agent.get("name") != contract["display_name"]
        or agent.get("division") != contract["division"]
    ):
        raise RosterRemediationError("source identity has no exact reviewed projection")
    prompt = governed_prompt(contract)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    full_receipt = extend_with_contract_projection(
        known,
        executable_contract_hash=prompt_hash,
        findings_original=contract["findings"],
        findings_resolved_by_encoding=contract["findings_resolved_by_encoding"],
        findings_resolved_by_projection=contract["findings_resolved_by_projection"],
    )
    projected = _projected_candidate(contract)
    return projected, full_receipt


def verify_projected_remediation(
    original: str,
    projected: str,
    receipt: RemediationReceipt | Mapping[str, Any],
    *,
    relative_path: str,
) -> RemediationReceipt:
    """Recompute both stages and require the exact reviewed executable artifact."""

    normalized = normalize_remediation_receipt(receipt)
    repaired, known = remediate_source_text(original)
    if known is None:
        raise RosterRemediationError("source has no registered encoding repair")
    contract = contract_for_source_hash(known.original_hash)
    if contract is None or contract["relative_path"] != relative_path:
        raise RosterRemediationError("source has no registered semantic projection")
    expected_prompt = governed_prompt(contract)
    _projected, expected = project_known_agent(
        {
            "slug": contract["slug"],
            "name": contract["display_name"],
            "division": contract["division"],
            "content": repaired,
        },
        known,
        relative_path=relative_path,
    )
    if (
        projected != expected_prompt
        or normalized != expected
        or normalized.findings_unresolved
        or normalized.rules[-1].kind != "semantic_projection"
    ):
        raise RosterRemediationError("semantic projection receipt does not match artifacts")
    return normalized


__all__ = [
    "SEMANTIC_PROJECTION_POLICY_HASH",
    "SEMANTIC_PROJECTION_POLICY_VERSION",
    "SOURCE_REPOSITORY",
    "SOURCE_REVISION",
    "contract_for_projected_candidate",
    "contract_for_source_hash",
    "governed_prompt",
    "project_known_agent",
    "verify_projected_candidate_contract",
    "verify_projected_remediation",
]
