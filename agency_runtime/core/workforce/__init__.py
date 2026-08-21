"""Versioned workforce contracts used by inference-first recruitment."""

from agency_runtime.core.workforce.comparison import (
    WorkforceComparison,
    compare_workers,
    consolidation_candidates,
    nearest_workers,
)
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    CompositionContract,
    WorkforceContract,
    parse_workforce_contract,
    project_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.hiring_contract import (
    CONTRACTOR_PROMPT_TEMPLATE_HASH,
    CONTRACTOR_PROMPT_TEMPLATE_VERSION,
    HIRING_CONTRACT_SCHEMA_VERSION,
    LEGACY_CONTRACTOR_PROMPT_TEMPLATE_HASH,
    LEGACY_CONTRACTOR_PROMPT_TEMPLATE_VERSION,
    LEGACY_HIRING_CONTRACT_SCHEMA_VERSION,
    ClosestWorker,
    CompiledContractor,
    ContractorEvalCase,
    EmploymentContract,
    ExecutionProfile,
    TypedRelationship,
    classify_contractor_risk,
    compile_contractor,
    parse_employment_contract,
)
from agency_runtime.core.workforce.identity import stable_worker_id
from agency_runtime.core.workforce.known_contractors import (
    KNOWN_CONTRACTOR_CONTRACTS,
    KNOWN_CONTRACTORS_BY_SLUG,
)
from agency_runtime.core.workforce.planning_contracts import (
    RecruiterProposal,
    WorkUnitPlan,
    parse_recruiter_proposal,
    parse_work_unit_plan,
)
from agency_runtime.core.workforce.promotion import promotion_readiness
from agency_runtime.core.workforce.recruiter_index import (
    RECRUITER_INDEX_SCHEMA_VERSION,
    RecruiterIndexRecord,
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)
from agency_runtime.core.workforce.staffing_verifier import (
    StaffingBudget,
    StaffingContext,
    StaffingDecision,
    build_verified_proposal,
    verify_staffing,
)

__all__ = [
    "CONTRACTOR_PROMPT_TEMPLATE_HASH",
    "CONTRACTOR_PROMPT_TEMPLATE_VERSION",
    "HIRING_CONTRACT_SCHEMA_VERSION",
    "LEGACY_CONTRACTOR_PROMPT_TEMPLATE_HASH",
    "LEGACY_CONTRACTOR_PROMPT_TEMPLATE_VERSION",
    "LEGACY_HIRING_CONTRACT_SCHEMA_VERSION",
    "KNOWN_CONTRACTORS_BY_SLUG",
    "KNOWN_CONTRACTOR_CONTRACTS",
    "RECRUITER_INDEX_SCHEMA_VERSION",
    "WORKFORCE_CONTRACT_SCHEMA_VERSION",
    "ClosestWorker",
    "CompiledContractor",
    "CompositionContract",
    "ContractorEvalCase",
    "EmploymentContract",
    "ExecutionProfile",
    "RecruiterIndexRecord",
    "RecruiterProposal",
    "StaffingBudget",
    "StaffingContext",
    "StaffingDecision",
    "TypedRelationship",
    "WorkUnitPlan",
    "WorkforceComparison",
    "WorkforceContract",
    "build_verified_proposal",
    "classify_contractor_risk",
    "compare_workers",
    "compile_contractor",
    "consolidation_candidates",
    "nearest_workers",
    "parse_employment_contract",
    "parse_recruiter_proposal",
    "parse_work_unit_plan",
    "parse_workforce_contract",
    "project_recruiter_index_record",
    "project_workforce_contract",
    "promotion_readiness",
    "recruiter_index_fingerprint",
    "serialize_recruiter_index",
    "stable_worker_id",
    "verify_staffing",
    "workforce_index_fingerprint",
]
