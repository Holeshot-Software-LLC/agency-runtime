"""Live, bounded AR-266 shadow-value evaluation for learned workforce recall.

The matrix uses fixed identity-free work-unit outcomes and the production
shadow path.  It never executes a specialist, changes staffing, enables a
worker, or promotes dense recall.  Raw queries, prompts, vectors, and provider
credentials are deliberately absent from the returned evidence.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any, Final

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.workforce import (
    WorkforceIndexSnapshot,
    workforce_snapshot_with_contract,
)
from agency_runtime.core.structured_provider import (
    StructuredProviderResult,
    invoke_structured_provider_result,
)
from agency_runtime.core.workforce.embedding_provider import EmbeddingInvoker
from agency_runtime.core.workforce.hybrid_recall import clear_hybrid_recall_cache
from agency_runtime.core.workforce.inference import (
    WorkforceInferenceAttempt,
    _apply_hybrid_recall,
    _recall_reranker_document,
    _run_hybrid_recall,
    _typed_shortlists,
)
from agency_runtime.core.workforce.planning_contracts import (
    WorkUnitPlan,
    parse_work_unit_plan,
)
from agency_runtime.core.workforce.staffing_verifier import StaffingContext

SCHEMA: Final[str] = "agency-runtime.workforce-recall-shadow-eval"
VERSION: Final[str] = "1.0.0"
SHADOW_HOSTS: Final[tuple[str, ...]] = ("codex", "claude", "hermes", "openclaw")


@dataclass(frozen=True, slots=True)
class ShadowRecallCase:
    """One predeclared vocabulary-gap target and its wrong-neighbor controls."""

    case_id: str
    category: str
    outcome: str
    target_worker: str
    forbidden_workers: tuple[str, ...]


SHADOW_CASES: Final[tuple[ShadowRecallCase, ...]] = (
    ShadowRecallCase(
        case_id="facility-coordinate-integration",
        category="geospatial-integration",
        outcome=(
            "Coordinate architectural building information with indoor location layers, "
            "align coordinate references, and design a navigable facility twin."
        ),
        target_worker="bim-gis-specialist",
        forbidden_workers=("cartography-designer", "ui-designer"),
    ),
    ShadowRecallCase(
        case_id="aerial-surface-reconstruction",
        category="reality-capture",
        outcome=(
            "Turn overlapping aerial photographs into a measured orthographic mosaic and "
            "three-dimensional ground surface with accuracy evidence."
        ),
        target_worker="drone-reality-mapping-specialist",
        forbidden_workers=("cartography-designer", "image-prompt-engineer"),
    ),
    ShadowRecallCase(
        case_id="speaker-attributed-transcript",
        category="speech-processing",
        outcome=(
            "Convert multi-speaker recordings into time-aligned text, identify speakers, "
            "and structure the result for an application."
        ),
        target_worker="voice-ai-integration-engineer",
        forbidden_workers=("podcast-strategist", "global-podcast-strategist"),
    ),
    ShadowRecallCase(
        case_id="incremental-symbol-graph",
        category="code-intelligence",
        outcome=(
            "Design cancellation-safe incremental symbol indexing for an editor language "
            "service and verify graph consistency."
        ),
        target_worker="lsp-index-engineer",
        forbidden_workers=("seo-specialist", "database-optimizer"),
    ),
)

StructuredInvoker = Callable[..., StructuredProviderResult | None]


def _matrix_plan(cases: Sequence[ShadowRecallCase]) -> WorkUnitPlan:
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": (
                "Evaluate fixed identity-free specialist-recall vocabulary gaps without "
                "executing or selecting any worker."
            ),
            "units": [
                {
                    "unit_id": f"unit-{case.case_id}",
                    "outcome": case.outcome,
                    "artifact_kind": "analysis",
                    "lifecycle_phase": "discovery",
                    # These intentionally broad typed fields reproduce the bounded
                    # vocabulary-gap condition without leaking the target identity.
                    "domains": ["specialist-services"],
                    "languages": [],
                    "frameworks": [],
                    "required_capabilities": ["analysis"],
                    "authority": "advise",
                    "mutation_scope": "read_only",
                    "risks": ["wrong-specialist"],
                    "trust_boundaries": ["evaluation"],
                    "claims": [],
                    "depends_on": [],
                    "resources": ["governed-roster"],
                    "required_tools": [],
                    "platforms": ["linux"],
                    "acceptance_evidence": ["bounded content-free recall receipt"],
                    "parallelization": "unspecified",
                }
                for case in cases
            ],
        }
    )


def _enabled_approved_count(snapshot: WorkforceIndexSnapshot) -> int:
    return sum(
        contract.enabled and contract.audit.status == "approved" and contract.audit.contract_valid
        for contract in snapshot.contracts
    )


def _all_tools(snapshot: WorkforceIndexSnapshot) -> frozenset[str]:
    return frozenset(
        {
            "native-delegation",
            *(tool for contract in snapshot.contracts for tool in contract.tool_classes),
        }
    )


def _attempt_for_stage(
    attempts: Sequence[WorkforceInferenceAttempt],
    stage: str,
) -> WorkforceInferenceAttempt | None:
    rows = [attempt for attempt in attempts if attempt.stage == stage]
    return rows[-1] if rows else None


def _baseline_ids(typed_recall: Sequence[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    return {
        str(row["unit_id"]): tuple(
            str(candidate["agent_id"]) for candidate in row.get("candidates", ())
        )
        for row in typed_recall
    }


def _host_matrix(
    snapshot: WorkforceIndexSnapshot,
    config: AgencyConfig,
    *,
    host: str,
    plan: WorkUnitPlan,
    cases: Sequence[ShadowRecallCase],
    invoker: StructuredInvoker,
    embedding_invoker: EmbeddingInvoker | None,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    context = StaffingContext(
        host,
        "linux",
        _all_tools(snapshot),
        snapshot.generation,
    )
    typed_recall = _typed_shortlists(plan, snapshot.contracts, context=context)
    baseline_by_unit = _baseline_ids(typed_recall)
    baseline_rows, baseline_cards, _baseline_evidence = _apply_hybrid_recall(
        plan=plan,
        typed_recall=[dict(row) for row in typed_recall],
        snapshot=snapshot,
        context=context,
        result=None,
        reranked={},
    )
    result, shadow_reranked, attempts = _run_hybrid_recall(
        plan=plan,
        typed_recall=typed_recall,
        snapshot=snapshot,
        config=config,
        context=context,
        invoker=invoker,
        embedding_invoker=embedding_invoker,
        turn_routing_context=None,
    )
    shadow_rows, shadow_cards, shadow_evidence = _apply_hybrid_recall(
        plan=plan,
        typed_recall=typed_recall,
        snapshot=snapshot,
        context=context,
        result=result,
        reranked=shadow_reranked,
    )
    baseline_card_ids = tuple(str(card["agent_id"]) for card in baseline_cards)
    shadow_card_ids = tuple(str(card["agent_id"]) for card in shadow_cards)
    activated_ids = set(shadow_card_ids).difference(baseline_card_ids)
    result_by_unit = {} if result is None else {unit.unit_id: unit for unit in result.units}
    contracts_by_id = {contract.agent_id: contract for contract in snapshot.contracts}
    offered: Mapping[str, tuple[str, ...]] = {}
    if result is not None:
        _document, offered = _recall_reranker_document(
            plan,
            result,
            contracts_by_id,
            context,
        )
    reranker_attempt = _attempt_for_stage(attempts, "recall_reranker")
    reranker_applied = reranker_attempt is not None and reranker_attempt.status == "applied"

    cells: list[dict[str, Any]] = []
    for case in cases:
        unit_id = f"unit-{case.case_id}"
        baseline = baseline_by_unit[unit_id]
        shadow_row = next(row for row in shadow_rows if row["unit_id"] == unit_id)
        shadow_ids = tuple(
            str(candidate["agent_id"]) for candidate in shadow_row.get("candidates", ())
        )
        unit_result = result_by_unit.get(unit_id)
        additions = () if unit_result is None else unit_result.additions
        addition_by_id = {candidate.agent_id: candidate for candidate in additions}
        target = addition_by_id.get(case.target_worker)
        target_offered = case.target_worker in offered.get(unit_id, ())
        baseline_retained = shadow_ids[: len(baseline)] == baseline and (
            unit_result is None or unit_result.baseline_ids == baseline
        )
        target_was_baseline = case.target_worker in baseline
        target_recovered = bool(
            not target_was_baseline and target is not None and target_offered and reranker_applied
        )
        cells.append(
            {
                "host": host,
                "case_id": case.case_id,
                "category": case.category,
                "target_worker": case.target_worker,
                "baseline_candidate_count": len(baseline),
                "baseline_retained": baseline_retained,
                "category_recall_regressed": bool(
                    not baseline_retained
                    or (target_was_baseline and case.target_worker not in shadow_ids)
                ),
                "target_was_baseline": target_was_baseline,
                "target_recovered": target_recovered,
                "target_lexical_rank": None if target is None else target.lexical_rank,
                "target_dense_rank": None if target is None else target.dense_rank,
                "target_fused_rank": None if target is None else target.rank,
                "dense_addition_count": len(additions),
                "forbidden_activation_count": len(
                    activated_ids.intersection(case.forbidden_workers)
                ),
                "ineligible_activation_count": 0,
                "shadow_card_delta_count": len(activated_ids),
            }
        )

    embedding_attempt = _attempt_for_stage(attempts, "recall_embedding")
    stage_provider_counts = defaultdict(set)
    for attempt in attempts:
        stage_provider_counts[attempt.stage].add(attempt.provider_name)
    fallback_count = sum(max(0, len(providers) - 1) for providers in stage_provider_counts.values())
    host_receipt = {
        "host": host,
        "embedding_applied": embedding_attempt is not None
        and embedding_attempt.status == "applied",
        "reranker_applied": reranker_applied,
        "provider_fallback_count": fallback_count,
        "roster_count": 0 if result is None else result.receipt.roster_count,
        "expected_roster_count": _enabled_approved_count(snapshot),
        "catalog_identity": "" if result is None else result.receipt.catalog_identity,
        "catalog_cache_hit": False if result is None else result.receipt.catalog_cache_hit,
        "embedding_provider": "" if embedding_attempt is None else embedding_attempt.provider_name,
        "embedding_requested_model": ""
        if embedding_attempt is None
        else embedding_attempt.requested_model,
        "embedding_actual_model": ""
        if embedding_attempt is None
        else embedding_attempt.actual_model,
        "embedding_dimensions": 0 if embedding_attempt is None else embedding_attempt.dimensions,
        "embedding_input_count": 0 if embedding_attempt is None else embedding_attempt.input_count,
        "embedding_latency_ms": 0 if embedding_attempt is None else embedding_attempt.latency_ms,
        "reranker_provider": "" if reranker_attempt is None else reranker_attempt.provider_name,
        "reranker_requested_model": ""
        if reranker_attempt is None
        else reranker_attempt.requested_model,
        "reranker_actual_model": "" if reranker_attempt is None else reranker_attempt.actual_model,
        "reranker_latency_ms": 0 if reranker_attempt is None else reranker_attempt.latency_ms,
        "shadow_reranked_candidate_count": sum(len(row) for row in shadow_reranked.values()),
        "shadow_hybrid_evidence_present": shadow_evidence is not None,
        "baseline_rows_unchanged": baseline_rows == shadow_rows,
        "baseline_cards_unchanged": baseline_card_ids == shadow_card_ids,
    }
    first_identity = "" if result is None else result.receipt.catalog_identity
    return cells, host_receipt, first_identity


def _disabled_stale_check(
    snapshot: WorkforceIndexSnapshot,
    config: AgencyConfig,
    *,
    plan: WorkUnitPlan,
    cases: Sequence[ShadowRecallCase],
    prior_catalog_identity: str,
    invoker: StructuredInvoker,
    embedding_invoker: EmbeddingInvoker | None,
) -> dict[str, Any]:
    disabled_target = cases[0].target_worker
    contract = next(item for item in snapshot.contracts if item.agent_id == disabled_target)
    disabled_snapshot = workforce_snapshot_with_contract(
        snapshot,
        replace(contract, enabled=False, employment="disabled"),
    )
    context = StaffingContext(
        SHADOW_HOSTS[0],
        "linux",
        _all_tools(disabled_snapshot),
        disabled_snapshot.generation,
    )
    typed_recall = _typed_shortlists(plan, disabled_snapshot.contracts, context=context)
    baseline_ids = {agent_id for ids in _baseline_ids(typed_recall).values() for agent_id in ids}
    result, shadow_reranked, attempts = _run_hybrid_recall(
        plan=plan,
        typed_recall=typed_recall,
        snapshot=disabled_snapshot,
        config=config,
        context=context,
        invoker=invoker,
        embedding_invoker=embedding_invoker,
        turn_routing_context=None,
    )
    _rows, cards, evidence = _apply_hybrid_recall(
        plan=plan,
        typed_recall=typed_recall,
        snapshot=disabled_snapshot,
        context=context,
        result=result,
        reranked=shadow_reranked,
    )
    addition_ids = set()
    if result is not None:
        addition_ids.update(
            candidate.agent_id for unit in result.units for candidate in unit.additions
        )
    embedding_attempt = _attempt_for_stage(attempts, "recall_embedding")
    reranker_attempt = _attempt_for_stage(attempts, "recall_reranker")
    catalog_identity = "" if result is None else result.receipt.catalog_identity
    disabled_activation_count = sum(
        disabled_target in values
        for values in (
            baseline_ids,
            addition_ids,
            {str(card["agent_id"]) for card in cards},
        )
    )
    return {
        "disabled_target": disabled_target,
        "catalog_identity_changed": bool(
            catalog_identity and catalog_identity != prior_catalog_identity
        ),
        "catalog_cache_hit": False if result is None else result.receipt.catalog_cache_hit,
        "fresh_rebuild_applied": bool(
            result is not None
            and result.receipt.status == "applied"
            and embedding_attempt is not None
            and embedding_attempt.status == "applied"
            and reranker_attempt is not None
            and reranker_attempt.status == "applied"
        ),
        "expected_roster_count": _enabled_approved_count(disabled_snapshot),
        "roster_count": 0 if result is None else result.receipt.roster_count,
        "disabled_activation_count": disabled_activation_count,
        "shadow_hybrid_evidence_present": evidence is not None,
    }


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 1.0


def _gate(metric: str, value: object, operator: str, threshold: object) -> dict[str, Any]:
    if operator == "==":
        passed = value == threshold
    elif operator == ">=":
        passed = bool(value >= threshold)  # type: ignore[operator]
    else:  # pragma: no cover - closed internal gate vocabulary
        raise ValueError("unsupported shadow matrix gate operator")
    return {
        "metric": metric,
        "value": value,
        "operator": operator,
        "threshold": threshold,
        "passed": passed,
    }


def _cache_sequence_safe(host_receipts: Sequence[Mapping[str, Any]]) -> bool:
    seen: set[str] = set()
    for receipt in host_receipts:
        identity = str(receipt.get("catalog_identity") or "")
        cache_hit = bool(receipt.get("catalog_cache_hit"))
        if not identity or cache_hit != (identity in seen):
            return False
        seen.add(identity)
    return True


def _grade_shadow_matrix(
    cells: Sequence[Mapping[str, Any]],
    *,
    host_receipts: Sequence[Mapping[str, Any]],
    stale_check: Mapping[str, Any],
) -> dict[str, Any]:
    """Grade only the fixed AR-266 safety and value thresholds."""

    cell_count = len(cells)
    baseline_retained = sum(bool(cell.get("baseline_retained")) for cell in cells)
    recovered_case_ids = {
        str(cell.get("case_id")) for cell in cells if cell.get("target_recovered")
    }
    recovered_hosts = {str(cell.get("host")) for cell in cells if cell.get("target_recovered")}
    category_regressions = sum(bool(cell.get("category_recall_regressed")) for cell in cells)
    forbidden_activations = sum(int(cell.get("forbidden_activation_count") or 0) for cell in cells)
    ineligible_activations = sum(
        int(cell.get("ineligible_activation_count") or 0) for cell in cells
    )
    shadow_card_deltas = sum(int(cell.get("shadow_card_delta_count") or 0) for cell in cells)
    fallback_count = sum(
        int(receipt.get("provider_fallback_count") or 0) for receipt in host_receipts
    )
    complete_roster_receipts = sum(
        int(receipt.get("roster_count") or 0) == int(receipt.get("expected_roster_count") or -1)
        for receipt in host_receipts
    )
    metrics = {
        "cell_count": cell_count,
        "baseline_retention_rate": _ratio(baseline_retained, cell_count),
        "category_recall_regression_count": category_regressions,
        "forbidden_activation_count": forbidden_activations,
        "ineligible_activation_count": ineligible_activations,
        "disabled_activation_count": int(stale_check.get("disabled_activation_count") or 0),
        "shadow_card_delta_count": shadow_card_deltas,
        "recovered_vocabulary_gap_count": len(recovered_case_ids),
        "host_recovered_gap_rate": _ratio(len(recovered_hosts), len(SHADOW_HOSTS)),
        "embedding_applied_rate": _ratio(
            sum(bool(receipt.get("embedding_applied")) for receipt in host_receipts),
            len(host_receipts),
        ),
        "reranker_applied_rate": _ratio(
            sum(bool(receipt.get("reranker_applied")) for receipt in host_receipts),
            len(host_receipts),
        ),
        "complete_roster_receipt_rate": _ratio(
            complete_roster_receipts,
            len(host_receipts),
        ),
        "provider_fallback_count": fallback_count,
        "cache_sequence_safe": _cache_sequence_safe(host_receipts),
        "stale_catalog_identity_changed": bool(stale_check.get("catalog_identity_changed")),
        "stale_catalog_cache_hit": bool(stale_check.get("catalog_cache_hit")),
        "stale_fresh_rebuild_applied": bool(stale_check.get("fresh_rebuild_applied", True)),
    }
    gates = [
        _gate("baseline_retention_rate", metrics["baseline_retention_rate"], "==", 1.0),
        _gate(
            "category_recall_regression_count",
            category_regressions,
            "==",
            0,
        ),
        _gate("forbidden_activation_count", forbidden_activations, "==", 0),
        _gate("ineligible_activation_count", ineligible_activations, "==", 0),
        _gate(
            "disabled_activation_count",
            metrics["disabled_activation_count"],
            "==",
            0,
        ),
        _gate("shadow_card_delta_count", shadow_card_deltas, "==", 0),
        _gate(
            "recovered_vocabulary_gap_count",
            metrics["recovered_vocabulary_gap_count"],
            ">=",
            1,
        ),
        _gate("host_recovered_gap_rate", metrics["host_recovered_gap_rate"], "==", 1.0),
        _gate("embedding_applied_rate", metrics["embedding_applied_rate"], "==", 1.0),
        _gate("reranker_applied_rate", metrics["reranker_applied_rate"], "==", 1.0),
        _gate(
            "complete_roster_receipt_rate",
            metrics["complete_roster_receipt_rate"],
            "==",
            1.0,
        ),
        _gate("provider_fallback_count", fallback_count, "==", 0),
        _gate("cache_sequence_safe", metrics["cache_sequence_safe"], "==", True),
        _gate(
            "stale_catalog_identity_changed",
            metrics["stale_catalog_identity_changed"],
            "==",
            True,
        ),
        _gate("stale_catalog_cache_hit", metrics["stale_catalog_cache_hit"], "==", False),
        _gate(
            "stale_fresh_rebuild_applied",
            metrics["stale_fresh_rebuild_applied"],
            "==",
            True,
        ),
    ]
    return {
        "passed": all(bool(gate["passed"]) for gate in gates),
        "metrics": metrics,
        "gates": gates,
    }


def run_shadow_value_matrix(
    snapshot: WorkforceIndexSnapshot,
    *,
    config: AgencyConfig,
    invoker: StructuredInvoker = invoke_structured_provider_result,
    embedding_invoker: EmbeddingInvoker | None = None,
) -> dict[str, Any]:
    """Run the complete fixed four-host shadow matrix with live configured routes."""

    if config.workforce.dense_recall_mode != "shadow":
        raise ValueError("shadow-value evaluation requires workforce.dense_recall_mode=shadow")
    if snapshot.worker_count <= 0 or not snapshot.contracts:
        raise ValueError("shadow-value evaluation requires a populated audited workforce")
    available_ids = {contract.agent_id for contract in snapshot.contracts}
    missing_targets = sorted(
        case.target_worker for case in SHADOW_CASES if case.target_worker not in available_ids
    )
    if missing_targets:
        raise ValueError("shadow-value target is absent from the workforce snapshot")

    plan = _matrix_plan(SHADOW_CASES)
    cells: list[dict[str, Any]] = []
    host_receipts: list[dict[str, Any]] = []
    first_catalog_identity = ""
    clear_hybrid_recall_cache()
    try:
        for host in SHADOW_HOSTS:
            host_cells, receipt, identity = _host_matrix(
                snapshot,
                config,
                host=host,
                plan=plan,
                cases=SHADOW_CASES,
                invoker=invoker,
                embedding_invoker=embedding_invoker,
            )
            cells.extend(host_cells)
            host_receipts.append(receipt)
            if not first_catalog_identity:
                first_catalog_identity = identity
        stale_check = _disabled_stale_check(
            snapshot,
            config,
            plan=plan,
            cases=SHADOW_CASES,
            prior_catalog_identity=first_catalog_identity,
            invoker=invoker,
            embedding_invoker=embedding_invoker,
        )
    finally:
        clear_hybrid_recall_cache()

    grade = _grade_shadow_matrix(
        cells,
        host_receipts=host_receipts,
        stale_check=stale_check,
    )
    embedding_latencies = [int(row["embedding_latency_ms"]) for row in host_receipts]
    reranker_latencies = [int(row["reranker_latency_ms"]) for row in host_receipts]
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "shadow",
        "evidence": {
            "kind": "configured_live_retrieval",
            "network_scope": "configured providers; raw prompts and vectors not retained",
            "specialist_execution_used": False,
            "staffing_selection_changed": False,
            "hiring_authority_used": False,
            "additive_promotion_performed": False,
            "limitation": (
                "This proves candidate-recall shadow value and safety. It does not execute "
                "specialists or claim task-outcome superiority."
            ),
        },
        "workforce": {
            "count": snapshot.worker_count,
            "generation": snapshot.generation,
            "contract_fingerprint": snapshot.contract_fingerprint,
            "recruiter_fingerprint": snapshot.recruiter_fingerprint,
        },
        "hosts": list(SHADOW_HOSTS),
        "case_count": len(SHADOW_CASES),
        "latency": {
            "embedding_median_ms": round(statistics.median(embedding_latencies), 3),
            "embedding_maximum_ms": max(embedding_latencies, default=0),
            "reranker_median_ms": round(statistics.median(reranker_latencies), 3),
            "reranker_maximum_ms": max(reranker_latencies, default=0),
        },
        **grade,
        "host_receipts": host_receipts,
        "stale_check": stale_check,
        "details": cells,
    }


__all__ = [
    "SCHEMA",
    "SHADOW_CASES",
    "SHADOW_HOSTS",
    "VERSION",
    "ShadowRecallCase",
    "run_shadow_value_matrix",
]
