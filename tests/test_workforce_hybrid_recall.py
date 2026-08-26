"""Focused correctness tests for additive learned workforce recall."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace

import pytest

from agency_runtime.core.workforce import hybrid_recall as hybrid_recall_module
from agency_runtime.core.workforce.contract import (
    WORKFORCE_CONTRACT_SCHEMA_VERSION,
    AuditContract,
    CompositionContract,
    WorkforceContract,
)
from agency_runtime.core.workforce.embedding_provider import (
    EmbeddingProviderResponse,
    validate_and_normalize_vectors,
)
from agency_runtime.core.workforce.hybrid_recall import (
    clear_hybrid_recall_cache,
    discover_hybrid_recall,
    hybrid_recall_cache_size,
    project_contract_document,
    project_unit_query,
    reciprocal_rank_fusion,
)
from agency_runtime.core.workforce.planning_contracts import parse_work_unit_plan

_HASH = "sha256:" + "a" * 64


@pytest.fixture(autouse=True)
def _isolated_catalog_cache():
    clear_hybrid_recall_cache()
    yield
    clear_hybrid_recall_cache()


def _contract(
    agent_id: str,
    *,
    outcome: str,
    capability: str = "analysis",
    domain: str = "software-engineering",
    not_for: tuple[str, ...] = (),
    composition: CompositionContract | None = None,
) -> WorkforceContract:
    return WorkforceContract(
        schema_version=WORKFORCE_CONTRACT_SCHEMA_VERSION,
        worker_id=f"worker:{agent_id}",
        agent_id=agent_id,
        display_name=agent_id.replace("-", " ").title(),
        archetype="positive-archetype",
        outcomes=(outcome,),
        capability_ids=(capability,),
        artifact_kinds=("analysis",),
        lifecycle_phases=("discovery",),
        domains=(domain,),
        stacks=("python",),
        scope_qualifiers=(f"{domain} evidence",),
        not_for=not_for,
        authority="private-authority",
        context_mode="private-context-mode",
        tool_classes=("private-tool-class",),
        hosts=("private-host",),
        platforms=("private-platform",),
        composition=composition or CompositionContract(independence_class=agent_id),
        audit=AuditContract(
            status="approved",
            revision="private-audit-revision",
            contract_valid=True,
        ),
        version="private-version",
        version_hash=_HASH,
        enabled=True,
        employment="employee",
        origin="private-origin",
    )


def _plan(*, two_units: bool = False):
    units = [
        {
            "unit_id": "unit-primary",
            "outcome": "Assess the primary subsystem",
            "artifact_kind": "analysis",
            "lifecycle_phase": "discovery",
            "domains": ["primary-domain"],
            "languages": ["python"],
            "frameworks": [],
            "required_capabilities": ["primary-analysis"],
            "authority": "advise",
            "mutation_scope": "read_only",
            "risks": ["regression"],
            "trust_boundaries": ["repository"],
            "claims": [],
            "depends_on": [],
            "resources": ["repository"],
            "required_tools": ["repository-read"],
            "platforms": ["windows"],
            "acceptance_evidence": ["evidence-backed findings"],
            "parallelization": "unspecified",
        }
    ]
    if two_units:
        units.append(
            {
                **units[0],
                "unit_id": "unit-secondary",
                "outcome": "Assess the secondary subsystem",
                "domains": ["secondary-domain"],
                "required_capabilities": ["secondary-analysis"],
            }
        )
    return parse_work_unit_plan(
        {
            "schema_version": 2,
            "request_summary": "Assess two independent subsystems.",
            "units": units,
        }
    )


def _turn_context(framework: str) -> dict[str, object]:
    return {
        "context_version": 1,
        "source_trace_id": "private-source-trace",
        "source_status": "completed",
        "source_turn_kind": "new_intent",
        "specialists": [
            {
                "slug": "private-prior-specialist",
                "description": "Prior database reliability analysis",
                "capabilities": ["schema analysis"],
            }
        ],
        "workforce_unit_descriptors": [
            {
                "ordinal": 1,
                "artifact_kind": "documentation",
                "lifecycle_phase": "release",
                "authority": "modify",
                "mutation_scope": "workspace_write",
            }
        ],
        "workforce_subject_hints": {
            "domains": ["software-engineering"],
            "languages": ["python"],
            "frameworks": [framework],
            "capability_ids": ["technical-analysis"],
            "platforms": ["windows"],
        },
    }


def test_positive_projection_excludes_negative_governance_and_identity_fields() -> None:
    contract = _contract(
        "positive-specialist",
        outcome="Inspect durable database recovery",
        capability="recovery-analysis",
        domain="database-reliability",
        not_for=("PRIVATE-NEGATIVE-SENTINEL",),
        composition=CompositionContract(
            same_context_conflicts=("private-conflicting-worker",),
            independence_class="private-independence-class",
        ),
    )

    document = project_contract_document(contract)

    assert document.agent_id == "positive-specialist"
    assert "positive-specialist" in document.text
    assert "positive-archetype" in document.text
    assert "Inspect durable database recovery" in document.text
    assert "recovery-analysis" in document.text
    assert "database-reliability" in document.text
    for excluded in (
        "PRIVATE-NEGATIVE-SENTINEL",
        "worker:positive-specialist",
        "private-conflicting-worker",
        "private-independence-class",
        "private-audit-revision",
        "private-version",
        "private-origin",
        "private-authority",
        "private-context-mode",
        "private-tool-class",
        "private-host",
        "private-platform",
        _HASH,
    ):
        assert excluded not in document.text
    assert document.projection_hash.startswith("sha256:")
    assert len(document.projection_hash) == 71


def test_context_query_changes_by_subject_without_trace_or_specialist_identity() -> None:
    plan = _plan()
    unit = plan.units[0]

    sqlite = project_unit_query(plan, unit, _turn_context("sqlite"))
    fastapi = project_unit_query(plan, unit, _turn_context("fastapi"))

    assert sqlite.unit_id == unit.unit_id
    assert "sqlite" in sqlite.text
    assert "fastapi" not in sqlite.text
    assert "fastapi" in fastapi.text
    assert sqlite.text != fastapi.text
    assert sqlite.query_hash != fastapi.query_hash
    assert sqlite.context_revision != fastapi.context_revision
    for excluded in (
        "private-source-trace",
        "private-prior-specialist",
        "Prior database reliability analysis",
        "schema analysis",
        "documentation",
        "release",
        "workspace_write",
        "source_trace_id",
        "source_status",
        "prior_user_message",
    ):
        assert excluded not in sqlite.text


@pytest.mark.parametrize(
    ("vectors", "expected_count"),
    [
        (((math.nan, 1.0),), 1),
        (((0.0, 0.0),), 1),
        (((1.0, 0.0), (1.0, 0.0, 0.0)), 2),
    ],
    ids=("nan", "zero", "mixed-dimensions"),
)
def test_vector_validation_rejects_invalid_matrices(
    vectors: object,
    expected_count: int,
) -> None:
    with pytest.raises(ValueError):
        validate_and_normalize_vectors(vectors, expected_count=expected_count)


def test_vector_validation_unit_normalizes_valid_rows() -> None:
    vectors = validate_and_normalize_vectors(
        ((3.0, 4.0), (0.0, 2.0)),
        expected_count=2,
    )

    assert vectors[0] == pytest.approx((0.6, 0.8))
    assert vectors[1] == pytest.approx((0.0, 1.0))


def test_reciprocal_rank_fusion_is_deterministic_and_identity_tiebroken() -> None:
    first = reciprocal_rank_fusion(
        (("beta", "alpha"), ("alpha", "beta")),
        rank_constant=60,
    )
    second = reciprocal_rank_fusion(
        (("beta", "alpha"), ("alpha", "beta")),
        rank_constant=60,
    )

    assert first == second
    assert [agent_id for agent_id, _score in first] == ["alpha", "beta"]
    assert first[0][1] == pytest.approx(first[1][1])


def test_discovery_is_add_only_and_obeys_per_unit_and_plan_bounds() -> None:
    plan = _plan(two_units=True)
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("baseline-secondary", outcome="Existing secondary baseline"),
        _contract("dense-primary", outcome="Novel primary semantic expertise"),
        _contract("dense-secondary", outcome="Novel secondary semantic expertise"),
        _contract("dense-shared", outcome="Novel shared semantic expertise"),
    )
    calls: list[tuple[str, ...]] = []

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        calls.append(texts)
        vectors: list[Sequence[float]] = []
        for text in texts:
            if "dense-primary" in text or "unit-primary" in text:
                vectors.append((1.0, 0.0, 0.0))
            elif "dense-secondary" in text or "unit-secondary" in text:
                vectors.append((0.0, 1.0, 0.0))
            elif "dense-shared" in text:
                vectors.append((1.0, 1.0, 0.0))
            else:
                vectors.append((0.0, 0.0, 1.0))
        return EmbeddingProviderResponse(
            vectors,
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model="fixture-model-v1",
            latency_ms=7,
        )

    baselines = {
        "unit-primary": ("baseline-primary",),
        "unit-secondary": ("baseline-secondary",),
    }
    result = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids=baselines,
        catalog_identity="fixture-catalog-add-only",
        embedding_invoker=invoke,
        per_unit_limit=2,
        per_plan_limit=3,
        retrieval_limit=5,
        provider_name="fixture-provider",
        requested_model="fixture-model",
    )

    assert len(calls) == 1
    assert result.receipt.catalog_cache_hit is False
    assert result.receipt.provider_call_count == 1
    assert sum(len(unit.additions) for unit in result.units) <= 3
    for unit in result.units:
        assert unit.baseline_ids == baselines[unit.unit_id]
        assert len(unit.additions) <= 2
        addition_ids = {candidate.agent_id for candidate in unit.additions}
        assert addition_ids.isdisjoint(unit.baseline_ids)
        assert all(agent_id.startswith("dense-") for agent_id in addition_ids)
    assert result.receipt.status == "applied"
    assert result.receipt.addition_count == sum(len(unit.additions) for unit in result.units)
    assert result.receipt.embedding.input_count == len(contracts) + len(plan.units)
    assert result.receipt.embedding.dimensions == 3


def test_catalog_cache_is_identity_bound_bounded_and_warm_calls_queries_only() -> None:
    plan = _plan()
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("dense-primary", outcome="Novel primary semantic expertise"),
    )
    calls: list[tuple[str, ...]] = []

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        calls.append(texts)
        return EmbeddingProviderResponse(
            tuple((1.0, 0.0) if "primary" in text else (0.0, 1.0) for text in texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model="fixture-model-v1",
        )

    def discover(identity: str, roster=contracts):
        return discover_hybrid_recall(
            plan,
            roster,
            typed_candidate_ids={"unit-primary": ("baseline-primary",)},
            catalog_identity=identity,
            embedding_invoker=invoke,
            provider_name="fixture-provider",
            requested_model="fixture-model",
        )

    cold = discover("catalog-a")
    warm = discover("catalog-a")

    assert [len(texts) for texts in calls] == [len(contracts) + 1, 1]
    assert cold.receipt.catalog_cache_hit is False
    assert warm.receipt.catalog_cache_hit is True
    assert cold.receipt.provider_call_count == warm.receipt.provider_call_count == 1
    assert hybrid_recall_cache_size() == 1

    changed_roster = (
        contracts[0],
        _contract("dense-primary", outcome="Changed semantic expertise"),
    )
    with pytest.raises(ValueError, match="catalog"):
        discover("catalog-a", changed_roster)

    discover("catalog-b")
    discover("catalog-c")
    assert hybrid_recall_cache_size() == 2


def test_provider_failure_returns_unchanged_baseline_and_content_free_evidence() -> None:
    plan = _plan(two_units=True)
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("baseline-secondary", outcome="Existing secondary baseline"),
        _contract("dense-candidate", outcome="Novel semantic expertise"),
    )
    baselines = {
        "unit-primary": ("baseline-primary",),
        "unit-secondary": ("baseline-secondary",),
    }

    def fail(_texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        raise RuntimeError("PRIVATE PROVIDER FAILURE")

    result = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids=baselines,
        catalog_identity="fixture-catalog-failure",
        embedding_invoker=fail,
        provider_name="fixture-provider",
        requested_model="fixture-model",
    )

    assert [unit.baseline_ids for unit in result.units] == list(baselines.values())
    assert all(unit.additions == () for unit in result.units)
    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_provider_failed"
    assert result.receipt.addition_count == 0
    assert result.receipt.catalog_cache_hit is False
    assert result.receipt.provider_call_count == 1
    assert result.receipt.embedding.status == "failed"
    assert result.receipt.embedding.reason_code == "embedding_provider_failed"
    assert "PRIVATE PROVIDER FAILURE" not in repr(result.receipt)


def test_configured_dimension_mismatch_stays_typed_only_and_uncached() -> None:
    plan = _plan()
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("dense-primary", outcome="Novel primary semantic expertise"),
    )
    baseline = {"unit-primary": ("baseline-primary",)}

    def mismatched(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        return EmbeddingProviderResponse(
            tuple((1.0, 0.0) for _text in texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model="fixture-model-v1",
        )

    result = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids=baseline,
        catalog_identity="fixture-catalog-dimension-mismatch",
        embedding_invoker=mismatched,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=3,
    )

    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_response_invalid"
    assert result.units[0].baseline_ids == baseline["unit-primary"]
    assert result.units[0].additions == ()
    assert hybrid_recall_cache_size() == 0


def test_missing_actual_model_identity_never_populates_or_reuses_catalog_cache() -> None:
    plan = _plan()
    contracts = (
        _contract("baseline-primary", outcome="Existing primary baseline"),
        _contract("dense-primary", outcome="Novel primary semantic expertise"),
    )

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        return EmbeddingProviderResponse(
            tuple((1.0, 0.0) for _text in texts),
            provider_name="fixture-provider",
            requested_model="moving-alias",
            actual_model="",
        )

    result = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids={"unit-primary": ("baseline-primary",)},
        catalog_identity="fixture-catalog-missing-model",
        embedding_invoker=invoke,
        provider_name="fixture-provider",
        requested_model="moving-alias",
    )

    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_model_identity_missing"
    assert result.units[0].additions == ()
    assert hybrid_recall_cache_size() == 0


def test_ar303_full_roster_4096_embeddings_use_two_ordered_bounded_batches() -> None:
    plan = _plan()
    base = _contract("worker-000", outcome="Bounded workforce recall")
    contracts = tuple(
        replace(
            base,
            worker_id=f"worker:worker-{index:03d}",
            agent_id=f"worker-{index:03d}",
            display_name=f"Worker {index:03d}",
            version_hash="sha256:" + f"{index + 1:064x}",
        )
        for index in range(263)
    )
    vector = (1.0, *(0.0 for _ in range(4_095)))
    calls: list[tuple[str, ...]] = []

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        calls.append(texts)
        return EmbeddingProviderResponse(
            vectors=(vector,) * len(texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model="fixture-model-v1",
            latency_ms=7,
        )

    cold = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids={"unit-primary": ("worker-000",)},
        catalog_identity="fixture-catalog-4096",
        embedding_invoker=invoke,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=4_096,
    )
    warm = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids={"unit-primary": ("worker-000",)},
        catalog_identity="fixture-catalog-4096",
        embedding_invoker=invoke,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=4_096,
    )

    assert [len(batch) for batch in calls] == [244, 20, 1]
    assert cold.receipt.status == "applied"
    assert cold.receipt.provider_call_count == 2
    assert cold.receipt.embedding.input_count == 264
    assert cold.receipt.embedding.dimensions == 4_096
    assert cold.receipt.embedding.latency_ms == 14
    assert cold.receipt.catalog_cache_hit is False
    assert warm.receipt.status == "applied"
    assert warm.receipt.provider_call_count == 1
    assert warm.receipt.catalog_cache_hit is True
    assert hybrid_recall_cache_size() == 1


def test_ar303_second_embedding_batch_failure_is_atomic_and_uncached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hybrid_recall_module, "MAX_EMBEDDING_VECTOR_VALUES", 6)
    plan = _plan()
    contracts = tuple(
        _contract(f"worker-{index}", outcome="Bounded workforce recall") for index in range(3)
    )
    calls: list[tuple[str, ...]] = []

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        calls.append(texts)
        if len(calls) == 2:
            raise RuntimeError("PRIVATE SECOND BATCH FAILURE")
        return EmbeddingProviderResponse(
            vectors=((1.0, 0.0, 0.0),) * len(texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model="fixture-model-v1",
        )

    result = discover_hybrid_recall(
        plan,
        contracts,
        typed_candidate_ids={"unit-primary": ("worker-0",)},
        catalog_identity="fixture-catalog-partial-failure",
        embedding_invoker=invoke,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=3,
    )

    assert [len(batch) for batch in calls] == [2, 2]
    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_provider_failed"
    assert result.receipt.provider_call_count == 2
    assert result.receipt.embedding.input_count == 4
    assert hybrid_recall_cache_size() == 0
    assert "PRIVATE SECOND BATCH FAILURE" not in repr(result.receipt)


def test_ar303_cross_batch_model_drift_is_atomic_and_uncached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hybrid_recall_module, "MAX_EMBEDDING_VECTOR_VALUES", 6)
    calls = 0

    def invoke(texts: tuple[str, ...]) -> EmbeddingProviderResponse:
        nonlocal calls
        calls += 1
        return EmbeddingProviderResponse(
            vectors=((1.0, 0.0, 0.0),) * len(texts),
            provider_name="fixture-provider",
            requested_model="fixture-model",
            actual_model=f"fixture-model-v{calls}",
        )

    result = discover_hybrid_recall(
        _plan(),
        tuple(
            _contract(f"worker-{index}", outcome="Bounded workforce recall") for index in range(3)
        ),
        typed_candidate_ids={"unit-primary": ("worker-0",)},
        catalog_identity="fixture-catalog-model-drift",
        embedding_invoker=invoke,
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=3,
    )

    assert calls == 2
    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_model_mismatch"
    assert result.receipt.provider_call_count == 2
    assert result.receipt.embedding.actual_model == ""
    assert hybrid_recall_cache_size() == 0


def test_ar303_more_than_two_embedding_batches_fail_before_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hybrid_recall_module, "MAX_EMBEDDING_VECTOR_VALUES", 3)
    calls: list[tuple[str, ...]] = []

    result = discover_hybrid_recall(
        _plan(),
        tuple(
            _contract(f"worker-{index}", outcome="Bounded workforce recall") for index in range(3)
        ),
        typed_candidate_ids={"unit-primary": ("worker-0",)},
        catalog_identity="fixture-catalog-too-many-batches",
        embedding_invoker=lambda texts: calls.append(texts),
        provider_name="fixture-provider",
        requested_model="fixture-model",
        embedding_dimensions=3,
    )

    assert calls == []
    assert result.receipt.status == "typed_only"
    assert result.receipt.reason_code == "embedding_inputs_invalid"
    assert result.receipt.provider_call_count == 0
    assert result.receipt.embedding.input_count == 4
