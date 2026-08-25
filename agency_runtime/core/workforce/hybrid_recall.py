"""Add-only learned-dense and lexical recall for workforce recruitment.

The typed shortlist remains outside this module and is never modified here.
Callers provide its exact candidate IDs; this module returns only bounded novel
discoveries. Learned similarity and reciprocal-rank fusion are recall evidence,
not staffing authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from threading import RLock
from typing import Any

from agency_runtime.core.roster.limits import MAX_ACTIVE_ROSTER_SIZE
from agency_runtime.core.roster.source_safety import scan_source_text
from agency_runtime.core.turn_routing_context import (
    project_turn_routing_context,
)
from agency_runtime.core.workforce.contract import WorkforceContract
from agency_runtime.core.workforce.embedding_provider import (
    EmbeddingInvoker,
    EmbeddingReceipt,
    embed_texts,
)
from agency_runtime.core.workforce.planning_contracts import (
    WorkUnit,
    WorkUnitPlan,
)

MAX_RECALL_PROJECTION_BYTES = 16 * 1_024
MAX_HYBRID_RETRIEVAL_LIMIT = 80
MAX_HYBRID_ADDITIONS_PER_UNIT = 16
MAX_HYBRID_ADDITIONS_PER_PLAN = 64
DEFAULT_HYBRID_ADDITIONS_PER_UNIT = 16
DEFAULT_HYBRID_ADDITIONS_PER_PLAN = 64
DEFAULT_HYBRID_RETRIEVAL_LIMIT = 32
DEFAULT_RRF_RANK_CONSTANT = 60
HYBRID_RECALL_PROJECTION_VERSION = "1"
MAX_HYBRID_CATALOG_CACHE_ENTRIES = 2

_AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,127}$")
_CATALOG_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_WORD_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
        "work",
    }
)
_SUBJECT_FIELDS = (
    "domains",
    "languages",
    "frameworks",
    "capability_ids",
    "platforms",
)


@dataclass(frozen=True, slots=True)
class RecallDocument:
    """Positive-only worker projection suitable for learned retrieval."""

    agent_id: str
    text: str
    projection_hash: str


@dataclass(frozen=True, slots=True)
class RecallQuery:
    """Bounded unit query with a transcript-free AR-265 context binding."""

    unit_id: str
    text: str
    query_hash: str
    context_revision: str


@dataclass(frozen=True, slots=True)
class HybridRecallCandidate:
    """One novel discovery and its non-calibrated retrieval ranks."""

    agent_id: str
    rank: int
    rrf_score: float
    lexical_rank: int | None
    dense_rank: int | None


@dataclass(frozen=True, slots=True)
class UnitHybridRecall:
    """An unchanged typed baseline plus additive discoveries for one unit."""

    unit_id: str
    baseline_ids: tuple[str, ...]
    additions: tuple[HybridRecallCandidate, ...]
    lexical_count: int
    dense_count: int


@dataclass(frozen=True, slots=True)
class HybridRecallReceipt:
    """Bounded evidence for a complete hybrid-recall attempt."""

    status: str
    reason_code: str
    roster_count: int
    unit_count: int
    addition_count: int
    catalog_identity: str
    projection_version: str
    catalog_cache_hit: bool
    provider_call_count: int
    embedding: EmbeddingReceipt


@dataclass(frozen=True, slots=True)
class HybridRecallResult:
    """All unit discoveries and one content-free attempt receipt."""

    units: tuple[UnitHybridRecall, ...]
    receipt: HybridRecallReceipt


@dataclass(frozen=True, slots=True)
class _CatalogVectorEntry:
    catalog_fingerprint: str
    document_vectors: tuple[tuple[float, ...], ...]
    provider_name: str
    requested_model: str
    actual_model: str
    dimensions: int


_CatalogCacheKey = tuple[str, str, str, str]
_CATALOG_VECTOR_CACHE: OrderedDict[_CatalogCacheKey, _CatalogVectorEntry] = OrderedDict()
_CATALOG_VECTOR_CACHE_LOCK = RLock()


def _text(value: object) -> str:
    return " ".join(str(value or "").split())


def _values(values: Sequence[object]) -> str:
    return ", ".join(item for value in values if (item := _text(value)))


def _render(fields: Sequence[tuple[str, object]]) -> str:
    parts: list[str] = []
    for label, raw_value in fields:
        value = _text(raw_value)
        if value:
            parts.append(f"{label}: {value}")
    text = " | ".join(parts)
    if not text or len(text.encode("utf-8")) > MAX_RECALL_PROJECTION_BYTES:
        raise ValueError("hybrid recall projection is empty or exceeds its size bound")
    safety = scan_source_text(text)
    if safety.controls or safety.suspicious_encoding:
        raise ValueError("hybrid recall projection failed its source-safety scan")
    return text


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_contract_document(contract: WorkforceContract) -> RecallDocument:
    """Project only affirmative recruitment facts from one audited contract.

    Negative, governance, and lifecycle-control fields such as ``not_for``,
    composition, audit state, source origin, and employment state are omitted.
    They remain available to the recruiter and deterministic verifier through
    their existing authoritative paths.
    """

    if not isinstance(contract, WorkforceContract):
        raise TypeError("hybrid recall document requires a workforce contract")
    if (
        not contract.enabled
        or contract.audit.status != "approved"
        or not contract.audit.contract_valid
    ):
        raise ValueError("hybrid recall documents require enabled approved contracts")
    text = _render(
        (
            ("agent identity", contract.agent_id),
            ("display name", contract.display_name),
            ("archetype", contract.archetype),
            ("owned outcomes", _values(contract.outcomes)),
            ("capability ids", _values(contract.capability_ids)),
            ("artifact kinds", _values(contract.artifact_kinds)),
            ("lifecycle phases", _values(contract.lifecycle_phases)),
            ("domains", _values(contract.domains)),
            ("stacks", _values(contract.stacks)),
            ("scope qualifiers", _values(contract.scope_qualifiers)),
        )
    )
    return RecallDocument(contract.agent_id, text, _hash(text))


def _context_fields(context: Mapping[str, Any]) -> list[tuple[str, object]]:
    fields: list[tuple[str, object]] = []
    subject = context.get("workforce_subject_hints")
    if isinstance(subject, Mapping):
        for name in _SUBJECT_FIELDS:
            values = subject.get(name, [])
            if isinstance(values, Sequence) and not isinstance(values, (str, bytes, bytearray)):
                fields.append((f"context subject {name}", _values(values)))
    return fields


def _subject_context_revision(context: Mapping[str, Any]) -> str:
    subject = context.get("workforce_subject_hints")
    if not isinstance(subject, Mapping) or not subject:
        return ""
    encoded = json.dumps(
        {name: subject.get(name, []) for name in _SUBJECT_FIELDS},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def project_unit_query(
    plan: WorkUnitPlan,
    unit: WorkUnit,
    turn_routing_context: Mapping[str, Any] | None = None,
) -> RecallQuery:
    """Project one planned unit plus safe same-session subject context."""

    if not isinstance(plan, WorkUnitPlan) or not isinstance(unit, WorkUnit):
        raise TypeError("hybrid recall query requires a work-unit plan and unit")
    if unit.unit_id not in {item.unit_id for item in plan.units}:
        raise ValueError("hybrid recall query unit is absent from its plan")
    projected_context = project_turn_routing_context(turn_routing_context)
    if projected_context is None:
        raise ValueError("turn_routing_context is malformed or unbounded")
    context_revision = _subject_context_revision(projected_context)
    fields: list[tuple[str, object]] = [
        ("unit identity", unit.unit_id),
        ("request summary", plan.request_summary),
        ("unit outcome", unit.outcome),
        ("artifact kind", unit.artifact_kind),
        ("lifecycle phase", unit.lifecycle_phase),
        ("domains", _values(unit.domains)),
        ("languages", _values(unit.languages)),
        ("frameworks", _values(unit.frameworks)),
        ("required capabilities", _values(unit.required_capabilities)),
        ("authority", unit.authority),
        ("mutation scope", unit.mutation_scope),
        ("required tools", _values(unit.required_tools)),
        ("platforms", _values(unit.platforms)),
    ]
    fields.extend(_context_fields(projected_context))
    text = _render(fields)
    return RecallQuery(unit.unit_id, text, _hash(text), context_revision)


def _agent_id(value: object) -> str:
    agent_id = _text(value).casefold()
    if _AGENT_ID.fullmatch(agent_id) is None:
        raise ValueError("hybrid recall candidate identity is invalid")
    return agent_id


def _baseline_ids(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise TypeError("typed candidate ids must be a sequence")
    result: list[str] = []
    for value in values:
        agent_id = _agent_id(value)
        if agent_id not in result:
            result.append(agent_id)
    return tuple(result)


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]],
    *,
    rank_constant: int = DEFAULT_RRF_RANK_CONSTANT,
) -> tuple[tuple[str, float], ...]:
    """Fuse bounded identity rankings without calibrating their source scores."""

    if (
        isinstance(rank_constant, bool)
        or not isinstance(rank_constant, int)
        or not 1 <= rank_constant <= 1_000
    ):
        raise ValueError("RRF rank constant is outside the supported range")
    if isinstance(rankings, (str, bytes, bytearray)) or len(rankings) > 16:
        raise ValueError("RRF rankings are outside the supported range")
    scores: dict[str, float] = {}
    for ranking in rankings:
        if isinstance(ranking, (str, bytes, bytearray)) or len(ranking) > MAX_ACTIVE_ROSTER_SIZE:
            raise ValueError("RRF ranking is outside the supported range")
        seen: set[str] = set()
        rank = 0
        for raw_agent_id in ranking:
            agent_id = _agent_id(raw_agent_id)
            if agent_id in seen:
                continue
            seen.add(agent_id)
            rank += 1
            scores[agent_id] = scores.get(agent_id, 0.0) + (1.0 / (rank_constant + rank))
    return tuple(
        (agent_id, round(score, 12))
        for agent_id, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    )


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _WORD_RE.findall(text.casefold().replace("_", " ").replace("-", " "))
        if len(token) >= 2 and token not in _STOPWORDS
    )


def _lexical_ranking(
    query: RecallQuery,
    documents: Sequence[RecallDocument],
    *,
    limit: int,
) -> tuple[str, ...]:
    query_tokens = _tokens(query.text)
    if not query_tokens:
        return ()
    document_tokens = tuple(_tokens(document.text) for document in documents)
    frequencies = Counter(token for tokens in document_tokens for token in tokens)
    population = len(documents)
    scored: list[tuple[float, str]] = []
    for document, tokens in zip(documents, document_tokens, strict=True):
        matched = query_tokens.intersection(tokens)
        if not matched:
            continue
        score = math.fsum(
            math.log1p((population + 1.0) / (frequencies[token] + 1.0)) for token in matched
        ) / math.sqrt(max(1, len(tokens)))
        if score > 0.0 and math.isfinite(score):
            scored.append((score, document.agent_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(agent_id for _score, agent_id in scored[:limit])


def _dense_ranking(
    query_vector: Sequence[float],
    documents: Sequence[RecallDocument],
    document_vectors: Sequence[Sequence[float]],
    *,
    limit: int,
) -> tuple[str, ...]:
    scored: list[tuple[float, str]] = []
    for document, vector in zip(documents, document_vectors, strict=True):
        score = math.fsum(left * right for left, right in zip(query_vector, vector, strict=True))
        if math.isfinite(score) and score > 0.0:
            scored.append((score, document.agent_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(agent_id for _score, agent_id in scored[:limit])


def _embedding_skip(
    reason_code: str,
    *,
    input_count: int = 0,
    provider_name: str = "",
    requested_model: str = "",
) -> EmbeddingReceipt:
    return EmbeddingReceipt(
        status="skipped",
        reason_code=reason_code,
        provider_name=provider_name,
        requested_model=requested_model,
        actual_model="",
        input_count=input_count,
        dimensions=0,
        latency_ms=0,
    )


def _request_identity(value: object, *, label: str, maximum: int = 512) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be text")
    identity = _text(value)
    if not identity or len(identity) > maximum:
        raise ValueError(f"{label} is empty or exceeds its size bound")
    safety = scan_source_text(identity)
    if safety.controls or safety.suspicious_encoding:
        raise ValueError(f"{label} failed its source-safety scan")
    return identity


def _catalog_id(value: object) -> str:
    identity = _request_identity(value, label="catalog_identity", maximum=256)
    if _CATALOG_IDENTITY.fullmatch(identity) is None:
        raise ValueError("catalog_identity must be an opaque normalized identifier")
    return identity.casefold()


def _catalog_fingerprint(documents: Sequence[RecallDocument]) -> str:
    digest = hashlib.sha256()
    digest.update(b"agency.workforce.hybrid-recall.catalog.v1\0")
    for document in documents:
        digest.update(document.agent_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(document.projection_hash.encode("ascii"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _catalog_cache_key(
    *,
    catalog_identity: str,
    provider_name: str,
    requested_model: str,
) -> _CatalogCacheKey:
    return (
        catalog_identity,
        HYBRID_RECALL_PROJECTION_VERSION,
        provider_name.casefold(),
        requested_model.casefold(),
    )


def _cached_catalog(
    key: _CatalogCacheKey,
    *,
    fingerprint: str,
) -> _CatalogVectorEntry | None:
    with _CATALOG_VECTOR_CACHE_LOCK:
        entry = _CATALOG_VECTOR_CACHE.get(key)
        if entry is None:
            return None
        if entry.catalog_fingerprint != fingerprint:
            raise ValueError("catalog_identity was reused for a different recall projection")
        _CATALOG_VECTOR_CACHE.move_to_end(key)
        return entry


def _store_cached_catalog(key: _CatalogCacheKey, entry: _CatalogVectorEntry) -> None:
    with _CATALOG_VECTOR_CACHE_LOCK:
        existing = _CATALOG_VECTOR_CACHE.get(key)
        if existing is not None and existing.catalog_fingerprint != entry.catalog_fingerprint:
            raise ValueError("catalog_identity was reused for a different recall projection")
        _CATALOG_VECTOR_CACHE[key] = entry
        _CATALOG_VECTOR_CACHE.move_to_end(key)
        while len(_CATALOG_VECTOR_CACHE) > MAX_HYBRID_CATALOG_CACHE_ENTRIES:
            _CATALOG_VECTOR_CACHE.popitem(last=False)


def _evict_cached_catalog(key: _CatalogCacheKey, entry: _CatalogVectorEntry) -> None:
    with _CATALOG_VECTOR_CACHE_LOCK:
        if _CATALOG_VECTOR_CACHE.get(key) is entry:
            del _CATALOG_VECTOR_CACHE[key]


def clear_hybrid_recall_cache() -> None:
    """Clear the process-local two-entry catalog-vector cache (test seam)."""

    with _CATALOG_VECTOR_CACHE_LOCK:
        _CATALOG_VECTOR_CACHE.clear()


def hybrid_recall_cache_size() -> int:
    """Return the process-local catalog-vector entry count without content."""

    with _CATALOG_VECTOR_CACHE_LOCK:
        return len(_CATALOG_VECTOR_CACHE)


def _effective_model(receipt: EmbeddingReceipt) -> str:
    return (receipt.actual_model or receipt.requested_model).casefold()


def _failed_embedding(receipt: EmbeddingReceipt, reason_code: str) -> EmbeddingReceipt:
    return EmbeddingReceipt(
        status="failed",
        reason_code=reason_code,
        provider_name=receipt.provider_name,
        requested_model=receipt.requested_model,
        actual_model=receipt.actual_model,
        input_count=receipt.input_count,
        dimensions=receipt.dimensions,
        latency_ms=receipt.latency_ms,
    )


def _typed_only_result(
    plan: WorkUnitPlan,
    baselines: Mapping[str, tuple[str, ...]],
    *,
    roster_count: int,
    reason_code: str,
    embedding: EmbeddingReceipt,
    catalog_identity: str,
    catalog_cache_hit: bool,
    provider_call_count: int,
) -> HybridRecallResult:
    units = tuple(
        UnitHybridRecall(unit.unit_id, baselines[unit.unit_id], (), 0, 0) for unit in plan.units
    )
    return HybridRecallResult(
        units,
        HybridRecallReceipt(
            status="typed_only",
            reason_code=reason_code,
            roster_count=roster_count,
            unit_count=len(plan.units),
            addition_count=0,
            catalog_identity=catalog_identity,
            projection_version=HYBRID_RECALL_PROJECTION_VERSION,
            catalog_cache_hit=catalog_cache_hit,
            provider_call_count=provider_call_count,
            embedding=embedding,
        ),
    )


def _bound(
    value: object,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{label} is outside the supported range")
    return value


def discover_hybrid_recall(  # noqa: C901 - one bounded fail-open recall transaction
    plan: WorkUnitPlan,
    contracts: Sequence[WorkforceContract],
    *,
    typed_candidate_ids: Mapping[str, Sequence[str]],
    catalog_identity: str,
    provider_name: str,
    requested_model: str,
    turn_routing_context: Mapping[str, Any] | None = None,
    embedding_invoker: EmbeddingInvoker | None = None,
    per_unit_limit: int = DEFAULT_HYBRID_ADDITIONS_PER_UNIT,
    per_plan_limit: int = DEFAULT_HYBRID_ADDITIONS_PER_PLAN,
    retrieval_limit: int = DEFAULT_HYBRID_RETRIEVAL_LIMIT,
) -> HybridRecallResult:
    """Return bounded learned/lexical discoveries without changing typed recall.

    A cold-cache injected call receives positive worker documents in agent-ID
    order followed by unit queries in plan order. A warm-cache call receives
    only the unit queries. Any provider absence, failure, or invalid matrix
    returns the normalized typed baselines and no additions.
    """

    if not isinstance(plan, WorkUnitPlan):
        raise TypeError("hybrid recall requires a work-unit plan")
    if not isinstance(typed_candidate_ids, Mapping):
        raise TypeError("typed_candidate_ids must be a mapping")
    catalog_identity = _catalog_id(catalog_identity)
    provider_name = _request_identity(provider_name, label="provider_name")
    requested_model = _request_identity(requested_model, label="requested_model")
    per_unit_limit = _bound(
        per_unit_limit,
        label="per_unit_limit",
        minimum=0,
        maximum=MAX_HYBRID_ADDITIONS_PER_UNIT,
    )
    per_plan_limit = _bound(
        per_plan_limit,
        label="per_plan_limit",
        minimum=0,
        maximum=MAX_HYBRID_ADDITIONS_PER_PLAN,
    )
    retrieval_limit = _bound(
        retrieval_limit,
        label="retrieval_limit",
        minimum=1,
        maximum=MAX_HYBRID_RETRIEVAL_LIMIT,
    )
    if isinstance(contracts, (str, bytes, bytearray)) or len(contracts) > MAX_ACTIVE_ROSTER_SIZE:
        raise ValueError("hybrid recall roster is outside the supported range")

    unit_ids = tuple(unit.unit_id for unit in plan.units)
    unknown_units = set(typed_candidate_ids) - set(unit_ids)
    if unknown_units:
        raise ValueError("typed_candidate_ids contains a unit absent from the plan")
    baselines = {
        unit_id: _baseline_ids(typed_candidate_ids.get(unit_id, ())) for unit_id in unit_ids
    }

    documents_by_id: dict[str, RecallDocument] = {}
    seen_contract_ids: set[str] = set()
    for contract in contracts:
        if not isinstance(contract, WorkforceContract):
            raise TypeError("hybrid recall roster must contain workforce contracts")
        if contract.agent_id in seen_contract_ids:
            raise ValueError("hybrid recall roster contains duplicate agent identities")
        seen_contract_ids.add(contract.agent_id)
        if (
            contract.enabled
            and contract.audit.status == "approved"
            and contract.audit.contract_valid
        ):
            documents_by_id[contract.agent_id] = project_contract_document(contract)
    documents = tuple(documents_by_id[agent_id] for agent_id in sorted(documents_by_id))

    if not documents:
        return _typed_only_result(
            plan,
            baselines,
            roster_count=0,
            reason_code="embedding_catalog_empty",
            embedding=_embedding_skip(
                "embedding_catalog_empty",
                provider_name=provider_name,
                requested_model=requested_model,
            ),
            catalog_identity=catalog_identity,
            catalog_cache_hit=False,
            provider_call_count=0,
        )
    if per_unit_limit == 0 or per_plan_limit == 0:
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code="hybrid_recall_disabled_by_bound",
            embedding=_embedding_skip(
                "hybrid_recall_disabled_by_bound",
                provider_name=provider_name,
                requested_model=requested_model,
            ),
            catalog_identity=catalog_identity,
            catalog_cache_hit=False,
            provider_call_count=0,
        )

    queries = tuple(project_unit_query(plan, unit, turn_routing_context) for unit in plan.units)
    if not queries:
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code="hybrid_recall_units_empty",
            embedding=_embedding_skip(
                "hybrid_recall_units_empty",
                provider_name=provider_name,
                requested_model=requested_model,
            ),
            catalog_identity=catalog_identity,
            catalog_cache_hit=False,
            provider_call_count=0,
        )

    fingerprint = _catalog_fingerprint(documents)
    cache_key = _catalog_cache_key(
        catalog_identity=catalog_identity,
        provider_name=provider_name,
        requested_model=requested_model,
    )
    cached = _cached_catalog(cache_key, fingerprint=fingerprint)
    cache_hit = cached is not None
    document_texts = tuple(document.text for document in documents)
    query_texts = tuple(query.text for query in queries)
    inputs = query_texts if cache_hit else document_texts + query_texts
    try:
        embedding = embed_texts(
            inputs,
            invoker=embedding_invoker,
            provider_name=provider_name,
            requested_model=requested_model,
        )
    except (TypeError, ValueError):
        invalid_input = _failed_embedding(
            _embedding_skip(
                "embedding_inputs_invalid",
                input_count=len(inputs),
                provider_name=provider_name,
                requested_model=requested_model,
            ),
            "embedding_inputs_invalid",
        )
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code=invalid_input.reason_code,
            embedding=invalid_input,
            catalog_identity=catalog_identity,
            catalog_cache_hit=cache_hit,
            provider_call_count=0,
        )
    provider_call_count = int(embedding_invoker is not None)
    if embedding.receipt.status != "applied":
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code=embedding.receipt.reason_code,
            embedding=embedding.receipt,
            catalog_identity=catalog_identity,
            catalog_cache_hit=cache_hit,
            provider_call_count=provider_call_count,
        )
    if not embedding.receipt.actual_model:
        if cached is not None:
            _evict_cached_catalog(cache_key, cached)
        failed = _failed_embedding(embedding.receipt, "embedding_model_identity_missing")
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code=failed.reason_code,
            embedding=failed,
            catalog_identity=catalog_identity,
            catalog_cache_hit=cache_hit,
            provider_call_count=provider_call_count,
        )

    if cached is None:
        document_count = len(documents)
        document_vectors = embedding.vectors[:document_count]
        query_vectors = embedding.vectors[document_count:]
        _store_cached_catalog(
            cache_key,
            _CatalogVectorEntry(
                catalog_fingerprint=fingerprint,
                document_vectors=document_vectors,
                provider_name=embedding.receipt.provider_name,
                requested_model=embedding.receipt.requested_model,
                actual_model=embedding.receipt.actual_model,
                dimensions=embedding.receipt.dimensions,
            ),
        )
    else:
        document_vectors = cached.document_vectors
        query_vectors = embedding.vectors
        if embedding.receipt.dimensions != cached.dimensions:
            _evict_cached_catalog(cache_key, cached)
            failed = _failed_embedding(embedding.receipt, "embedding_dimension_mismatch")
            return _typed_only_result(
                plan,
                baselines,
                roster_count=len(documents),
                reason_code=failed.reason_code,
                embedding=failed,
                catalog_identity=catalog_identity,
                catalog_cache_hit=True,
                provider_call_count=provider_call_count,
            )
        cached_model = (cached.actual_model or cached.requested_model).casefold()
        if _effective_model(embedding.receipt) != cached_model:
            _evict_cached_catalog(cache_key, cached)
            failed = _failed_embedding(embedding.receipt, "embedding_model_mismatch")
            return _typed_only_result(
                plan,
                baselines,
                roster_count=len(documents),
                reason_code=failed.reason_code,
                embedding=failed,
                catalog_identity=catalog_identity,
                catalog_cache_hit=True,
                provider_call_count=provider_call_count,
            )
    if len(query_vectors) != len(queries):
        # ``embed_texts`` already proves the matrix count. Keep this guard local
        # so future changes cannot turn a split error into mismatched retrieval.
        return _typed_only_result(
            plan,
            baselines,
            roster_count=len(documents),
            reason_code="embedding_response_invalid",
            embedding=_failed_embedding(embedding.receipt, "embedding_response_invalid"),
            catalog_identity=catalog_identity,
            catalog_cache_hit=cache_hit,
            provider_call_count=provider_call_count,
        )

    remaining = per_plan_limit
    unit_results: list[UnitHybridRecall] = []
    total_additions = 0
    for query, query_vector in zip(queries, query_vectors, strict=True):
        lexical = _lexical_ranking(query, documents, limit=retrieval_limit)
        dense = _dense_ranking(
            query_vector,
            documents,
            document_vectors,
            limit=retrieval_limit,
        )
        fused = reciprocal_rank_fusion((lexical, dense))
        lexical_ranks = {agent_id: rank for rank, agent_id in enumerate(lexical, start=1)}
        dense_ranks = {agent_id: rank for rank, agent_id in enumerate(dense, start=1)}
        baseline = baselines[query.unit_id]
        baseline_set = set(baseline)
        additions: list[HybridRecallCandidate] = []
        for agent_id, rrf_score in fused:
            if agent_id in baseline_set:
                continue
            if len(additions) >= per_unit_limit or remaining <= 0:
                break
            additions.append(
                HybridRecallCandidate(
                    agent_id=agent_id,
                    rank=len(additions) + 1,
                    rrf_score=rrf_score,
                    lexical_rank=lexical_ranks.get(agent_id),
                    dense_rank=dense_ranks.get(agent_id),
                )
            )
            remaining -= 1
        total_additions += len(additions)
        unit_results.append(
            UnitHybridRecall(
                unit_id=query.unit_id,
                baseline_ids=baseline,
                additions=tuple(additions),
                lexical_count=len(lexical),
                dense_count=len(dense),
            )
        )

    return HybridRecallResult(
        tuple(unit_results),
        HybridRecallReceipt(
            status="applied",
            reason_code="",
            roster_count=len(documents),
            unit_count=len(unit_results),
            addition_count=total_additions,
            catalog_identity=catalog_identity,
            projection_version=HYBRID_RECALL_PROJECTION_VERSION,
            catalog_cache_hit=cache_hit,
            provider_call_count=provider_call_count,
            embedding=embedding.receipt,
        ),
    )


__all__ = [
    "DEFAULT_HYBRID_ADDITIONS_PER_PLAN",
    "DEFAULT_HYBRID_ADDITIONS_PER_UNIT",
    "DEFAULT_HYBRID_RETRIEVAL_LIMIT",
    "DEFAULT_RRF_RANK_CONSTANT",
    "HYBRID_RECALL_PROJECTION_VERSION",
    "MAX_HYBRID_ADDITIONS_PER_PLAN",
    "MAX_HYBRID_ADDITIONS_PER_UNIT",
    "HybridRecallCandidate",
    "HybridRecallReceipt",
    "HybridRecallResult",
    "RecallDocument",
    "RecallQuery",
    "UnitHybridRecall",
    "clear_hybrid_recall_cache",
    "discover_hybrid_recall",
    "hybrid_recall_cache_size",
    "project_contract_document",
    "project_unit_query",
    "reciprocal_rank_fusion",
]
