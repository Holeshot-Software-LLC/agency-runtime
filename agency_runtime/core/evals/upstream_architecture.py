"""Pinned, source-visible architecture comparison with upstream Agency Agents.

Upstream does not ship an executable selector at the pinned revision.  Its
selection behavior is expressed as instructions inside one orchestrator prompt.
This module therefore compares explicit architecture contracts only.  It must
never be used as evidence that Agency Runtime produces better completed work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final

SCHEMA: Final[str] = "agency-runtime.upstream-architecture-comparison"
VERSION: Final[str] = "1.0.0"

UPSTREAM_REPOSITORY: Final[str] = "https://github.com/msitarzewski/agency-agents"
UPSTREAM_REVISION: Final[str] = "ee5e758c10b412cf905f8984a02c5c016315e1ec"
UPSTREAM_ORCHESTRATOR_PATH: Final[str] = "specialized/agents-orchestrator.md"
UPSTREAM_ORCHESTRATOR_BLOB: Final[str] = "9d62d814d3c5153ef7b403bb4ecba2e9dc21f8ae"
UPSTREAM_SOURCE_URL: Final[str] = (
    f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_REVISION}/{UPSTREAM_ORCHESTRATOR_PATH}"
)
UPSTREAM_FIXED_PIPELINE: Final[tuple[str, ...]] = (
    "project-manager-senior",
    "architect-ux",
    "appropriate-developer",
    "evidence-qa",
    "testing-reality-checker",
)


@dataclass(frozen=True, slots=True)
class ArchitectureCapability:
    """One source-auditable distinction without a subjective numeric weight."""

    capability_id: str
    upstream_contract: str
    agency_contract: str
    agency_evidence: tuple[str, ...]


CAPABILITIES: Final[tuple[ArchitectureCapability, ...]] = (
    ArchitectureCapability(
        "per-ask-dynamic-planning",
        "A fixed PM-to-architecture-to-developer/QA-to-integration pipeline is prescribed.",
        "Each new intent is compiled into bounded typed work units before recruitment.",
        (
            "agency_runtime.core.workforce.intent:COMPACT_INTENT_RESPONSE_SCHEMA",
            "agency_runtime.core.workforce.inference:plan_and_staff_workforce",
        ),
    ),
    ArchitectureCapability(
        "whole-roster-capability-recall",
        "The prompt lists example specialists and asks the model to choose an appropriate one.",
        "Every audited worker is projected into a versioned capability index before recall.",
        (
            "agency_runtime.core.workforce.recruiter_index:RECRUITER_INDEX_SCHEMA_VERSION",
            "agency_runtime.core.roster.workforce:workforce_index_snapshot",
        ),
    ),
    ArchitectureCapability(
        "typed-composition-and-eligibility",
        "No machine-enforced conflict, dependency, host, platform, tool, or authority schema is specified.",
        "A deterministic verifier enforces eligibility, dependencies, isolation, and bounded staffing.",
        (
            "agency_runtime.core.workforce.contract:WorkforceContract",
            "agency_runtime.core.workforce.staffing_verifier:verify_staffing",
        ),
    ),
    ArchitectureCapability(
        "bounded-inference",
        "The native model interprets a free-form orchestrator prompt without a routing-call budget.",
        "Structured planning is bounded; recruitment and criticism run only when policy requires them.",
        (
            "agency_runtime.core.config:WorkforceConfig",
            "agency_runtime.core.workforce.inference:_CallBudget",
        ),
    ),
    ArchitectureCapability(
        "exact-version-activation",
        "The prompt requests agent spawning but defines no one-use, exact-version activation proof.",
        "Selection, assignment, activation, and consumption are separate receipt-backed states.",
        (
            "agency_runtime.core.preflight:_assignment_recipe",
            "agency_runtime.core.store.native_child:NativeChildStoreMixin.record_native_child_started",
        ),
    ),
    ArchitectureCapability(
        "native-child-reuse-and-budgets",
        "No parent/child correlation, shared inference budget, or singleflight contract is specified.",
        "Native children reuse parent-approved recipes and share bounded routing coordination.",
        (
            "agency_runtime.core.preflight:_resolve_preflight_routing",
            "agency_runtime.core.store.child_routing:ChildRoutingStoreMixin.reserve_child_routing",
        ),
    ),
    ArchitectureCapability(
        "version-complete-caching",
        "No plan, candidate, recruitment, or parent-unit cache identity is specified.",
        "Opaque cache keys bind request, roster, policy, provider, host, eligibility, and schema versions.",
        (
            "agency_runtime.core.workforce.cache:workforce_cache_identity",
            "agency_runtime.core.preflight:_CHILD_ROUTE_BUNDLE_VERSION",
        ),
    ),
    ArchitectureCapability(
        "governed-workforce-lifecycle",
        "Agent files are installed and invoked; no contractor admission or employment lifecycle is specified.",
        "Contractors use audited contracts, duplicate checks, probation, promotion, merge, and retirement states.",
        (
            "agency_runtime.core.workforce.hiring:hire_contractor_for_gap",
            "agency_runtime.core.store.workforce:WorkforceStoreMixin.transition_workforce_worker",
        ),
    ),
    ArchitectureCapability(
        "disabled-shadow-visibility",
        "The prompt does not distinguish semantic-best, enabled-best, and executable-best workers.",
        "Disabled semantic winners remain inactive and are reported as bounded shadow evidence.",
        (
            "agency_runtime.core.workforce.staffing_verifier:StaffingDecision",
            "agency_runtime.core.workforce.routing_projection:project_workforce_routing",
        ),
    ),
    ArchitectureCapability(
        "truthful-provider-and-model-evidence",
        "No requested, routed, and actual model reconciliation contract is specified.",
        "Provider attempts record requested model, router alias, actual model, source, latency, and status.",
        (
            "agency_runtime.core.structured_provider:StructuredProviderResult",
            "agency_runtime.core.workforce.inference:WorkforceInferenceAttempt",
        ),
    ),
)


def run_upstream_architecture_comparison() -> dict[str, object]:
    """Return a reproducible architecture report with an explicit claim boundary."""

    capability_ids = [item.capability_id for item in CAPABILITIES]
    if len(capability_ids) != len(set(capability_ids)):
        raise RuntimeError("upstream architecture comparison contains duplicate capabilities")
    if len(UPSTREAM_REVISION) != 40 or len(UPSTREAM_ORCHESTRATOR_BLOB) != 40:
        raise RuntimeError("upstream architecture comparison is not pinned to Git objects")
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "revision": UPSTREAM_REVISION,
            "orchestrator_path": UPSTREAM_ORCHESTRATOR_PATH,
            "orchestrator_blob": UPSTREAM_ORCHESTRATOR_BLOB,
            "source_url": UPSTREAM_SOURCE_URL,
            "executable_router_present": False,
            "selection_mechanism": "native-model interpretation of a free-form orchestrator prompt",
            "fixed_pipeline": list(UPSTREAM_FIXED_PIPELINE),
        },
        "comparison": [asdict(item) for item in CAPABILITIES],
        "result": {
            "evaluated_capability_count": len(CAPABILITIES),
            "agency_has_stronger_explicit_contract": True,
            "reason": (
                "Agency Runtime machine-enforces all evaluated routing and workforce contracts; "
                "the pinned upstream source leaves them unspecified or prompt-enforced."
            ),
        },
        "evidence": {
            "kind": "source_visible_architecture_contract",
            "network_used_by_report": False,
            "upstream_runtime_executed": False,
            "selection_outcomes_measured": False,
            "task_outcomes_measured": False,
            "superiority_claimed": False,
            "limitation": (
                "This establishes an explicit architecture-contract advantage only. A held-out "
                "matched selection corpus and independently graded product trials are still "
                "required before claiming better routing or completed outcomes."
            ),
        },
    }


__all__ = [
    "CAPABILITIES",
    "SCHEMA",
    "UPSTREAM_ORCHESTRATOR_BLOB",
    "UPSTREAM_ORCHESTRATOR_PATH",
    "UPSTREAM_REPOSITORY",
    "UPSTREAM_REVISION",
    "UPSTREAM_SOURCE_URL",
    "VERSION",
    "ArchitectureCapability",
    "run_upstream_architecture_comparison",
]
