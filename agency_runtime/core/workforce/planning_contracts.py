"""Bounded contracts for inference planning and whole-workforce recruitment."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

PLAN_SCHEMA_VERSION = 2
RECRUITMENT_SCHEMA_VERSION = 2
MAX_WORK_UNITS = 16
MAX_ITEMS = 16
MAX_TEXT_CHARS = 2_048
MAX_LABEL_CHARS = 128

_UNIT_ID_RE = re.compile(r"unit-[a-z0-9][a-z0-9-]{0,62}")
_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
_DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
_AUTHORITIES = frozenset({"advise", "plan", "modify", "review"})
_ARTIFACTS = frozenset(
    {
        "analysis",
        "architecture-record",
        "documentation",
        "implementation-change",
        "plan",
        "review-report",
        "test-code",
        "test-evidence",
    }
)
_LIFECYCLES = frozenset(
    {
        "coordination",
        "discovery",
        "documentation",
        "design",
        "implementation",
        "planning",
        "release",
        "review",
        "testing",
    }
)
_MUTATIONS = frozenset({"read_only", "workspace_write", "external_write"})
_PARALLELIZATION = frozenset({"parallel", "sequential", "unspecified"})
_DELIVERY = frozenset({"load", "delegate"})
_TIMING = frozenset({"immediate", "after_dependencies", "after_artifact"})


def _mapping(value: object, *, label: str, fields: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} must contain exactly: {', '.join(sorted(fields))}")
    return value


def _text(value: object, *, label: str, maximum: int = MAX_TEXT_CHARS) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    text = " ".join(value.split())
    if not text or len(text) > maximum or any(ord(character) < 32 for character in text):
        raise ValueError(f"{label} must contain 1..{maximum} printable characters")
    return text


def _items(
    value: object,
    *,
    label: str,
    identifiers: bool = False,
    required: bool = False,
) -> tuple[str, ...]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
        or len(value) > MAX_ITEMS
    ):
        raise ValueError(f"{label} must be a bounded list")
    result: list[str] = []
    for raw in value:
        item = _text(raw, label=f"{label} item", maximum=MAX_LABEL_CHARS)
        if identifiers:
            item = item.casefold()
            if _IDENTIFIER_RE.fullmatch(item) is None:
                raise ValueError(f"{label} contains an invalid identifier")
        if item in result:
            raise ValueError(f"{label} contains duplicate values")
        result.append(item)
    if required and not result:
        raise ValueError(f"{label} must not be empty")
    return tuple(result)


def _identifier(value: object, *, label: str) -> str:
    item = _text(value, label=label, maximum=MAX_LABEL_CHARS).casefold()
    if _IDENTIFIER_RE.fullmatch(item) is None:
        raise ValueError(f"{label} is invalid")
    return item


def _probability(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{label} must be between zero and one")
    return round(number, 6)


@dataclass(frozen=True, slots=True)
class WorkUnit:
    unit_id: str
    outcome: str
    artifact_kind: str
    lifecycle_phase: str
    domains: tuple[str, ...]
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    authority: str
    mutation_scope: str
    risks: tuple[str, ...]
    trust_boundaries: tuple[str, ...]
    claims: tuple[str, ...]
    depends_on: tuple[str, ...]
    resources: tuple[str, ...]
    required_tools: tuple[str, ...]
    platforms: tuple[str, ...]
    acceptance_evidence: tuple[str, ...]
    parallelization: str


@dataclass(frozen=True, slots=True)
class WorkUnitPlan:
    schema_version: int
    request_summary: str
    units: tuple[WorkUnit, ...]
    plan_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateRank:
    agent_id: str
    rank: int
    score: float


@dataclass(frozen=True, slots=True)
class CoverageClaim:
    requirement: str
    agent_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SelectionEvidence:
    agent_id: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextBinding:
    agent_id: str
    context_id: str


@dataclass(frozen=True, slots=True)
class ShadowEvidence:
    agent_id: str
    rank: int
    reason_codes: tuple[str, ...]
    fallback_agent_id: str
    tradeoff: str


@dataclass(frozen=True, slots=True)
class UnitRecruitment:
    unit_id: str
    required: tuple[str, ...]
    acceptable: tuple[str, ...]
    forbidden: tuple[str, ...]
    selected: tuple[str, ...]
    runner_up: tuple[str, ...]
    ranked_semantic: tuple[CandidateRank, ...]
    ranked_enabled: tuple[CandidateRank, ...]
    ranked_executable: tuple[CandidateRank, ...]
    disabled_shadows: tuple[ShadowEvidence, ...]
    unavailable_shadows: tuple[ShadowEvidence, ...]
    coverage: tuple[CoverageClaim, ...]
    positive_evidence: tuple[SelectionEvidence, ...]
    negative_evidence: tuple[SelectionEvidence, ...]
    contexts: tuple[ContextBinding, ...]
    confidence: float
    margin: float
    delivery: str
    timing: str
    abstention_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecruiterProposal:
    schema_version: int
    plan_hash: str
    roster_fingerprint: str
    roster_count: int
    roster_generation: int
    units: tuple[UnitRecruitment, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_PLAN_FIELDS = frozenset({"schema_version", "request_summary", "units"})
_UNIT_FIELDS = frozenset(
    {
        "unit_id",
        "outcome",
        "artifact_kind",
        "lifecycle_phase",
        "domains",
        "languages",
        "frameworks",
        "required_capabilities",
        "authority",
        "mutation_scope",
        "risks",
        "trust_boundaries",
        "claims",
        "depends_on",
        "resources",
        "required_tools",
        "platforms",
        "acceptance_evidence",
        "parallelization",
    }
)
_PROPOSAL_FIELDS = frozenset(
    {
        "schema_version",
        "plan_hash",
        "roster_fingerprint",
        "roster_count",
        "roster_generation",
        "units",
    }
)
_ROW_FIELDS = frozenset(
    {
        "unit_id",
        "required",
        "acceptable",
        "forbidden",
        "selected",
        "runner_up",
        "ranked_semantic",
        "ranked_enabled",
        "ranked_executable",
        "disabled_shadows",
        "unavailable_shadows",
        "coverage",
        "positive_evidence",
        "negative_evidence",
        "contexts",
        "confidence",
        "margin",
        "delivery",
        "timing",
        "abstention_reasons",
    }
)


def _parse_unit(value: object) -> WorkUnit:
    raw = _mapping(value, label="work unit", fields=_UNIT_FIELDS)
    unit_id = _identifier(raw["unit_id"], label="unit_id")
    if _UNIT_ID_RE.fullmatch(unit_id) is None:
        raise ValueError("unit_id is invalid")
    artifact = _identifier(raw["artifact_kind"], label="artifact_kind")
    lifecycle = _identifier(raw["lifecycle_phase"], label="lifecycle_phase")
    authority = _identifier(raw["authority"], label="authority")
    mutation = _identifier(raw["mutation_scope"], label="mutation_scope")
    parallelization = _identifier(raw["parallelization"], label="parallelization")
    if (
        artifact not in _ARTIFACTS
        or lifecycle not in _LIFECYCLES
        or authority not in _AUTHORITIES
        or mutation not in _MUTATIONS
        or parallelization not in _PARALLELIZATION
    ):
        raise ValueError("work unit enum is invalid")
    return WorkUnit(
        unit_id=unit_id,
        outcome=_text(raw["outcome"], label="outcome"),
        artifact_kind=artifact,
        lifecycle_phase=lifecycle,
        domains=_items(raw["domains"], label="domains", identifiers=True, required=True),
        languages=_items(raw["languages"], label="languages", identifiers=True),
        frameworks=_items(raw["frameworks"], label="frameworks", identifiers=True),
        required_capabilities=_items(
            raw["required_capabilities"],
            label="required_capabilities",
            identifiers=True,
            required=True,
        ),
        authority=authority,
        mutation_scope=mutation,
        risks=_items(raw["risks"], label="risks", identifiers=True),
        trust_boundaries=_items(
            raw["trust_boundaries"], label="trust_boundaries", identifiers=True
        ),
        claims=_items(raw["claims"], label="claims", identifiers=True),
        depends_on=_items(raw["depends_on"], label="depends_on", identifiers=True),
        resources=_items(raw["resources"], label="resources", required=True),
        required_tools=_items(raw["required_tools"], label="required_tools", identifiers=True),
        platforms=_items(raw["platforms"], label="platforms", identifiers=True, required=True),
        acceptance_evidence=_items(
            raw["acceptance_evidence"], label="acceptance_evidence", required=True
        ),
        parallelization=parallelization,
    )


def _plan_digest(request_summary: str, units: tuple[WorkUnit, ...]) -> str:
    payload = json.dumps(
        {
            "schema_version": PLAN_SCHEMA_VERSION,
            "request_summary": request_summary,
            "units": [asdict(unit) for unit in units],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_work_unit_plan(value: object) -> WorkUnitPlan:
    raw = _mapping(value, label="work-unit plan", fields=_PLAN_FIELDS)
    if raw["schema_version"] != PLAN_SCHEMA_VERSION:
        raise ValueError("work-unit plan schema_version is unsupported")
    raw_units = raw["units"]
    if (
        not isinstance(raw_units, Sequence)
        or isinstance(raw_units, (str, bytes, bytearray))
        or not raw_units
        or len(raw_units) > MAX_WORK_UNITS
    ):
        raise ValueError("work-unit plan units must be a nonempty bounded list")
    summary = _text(raw["request_summary"], label="request_summary")
    units = tuple(_parse_unit(item) for item in raw_units)
    ids = [unit.unit_id for unit in units]
    if len(set(ids)) != len(ids):
        raise ValueError("work-unit plan contains duplicate unit ids")
    known: set[str] = set()
    for unit in units:
        if unit.unit_id in unit.depends_on or not set(unit.depends_on).issubset(known):
            raise ValueError("work-unit dependencies must reference earlier units")
        known.add(unit.unit_id)
    return WorkUnitPlan(PLAN_SCHEMA_VERSION, summary, units, _plan_digest(summary, units))


def _parse_rank(value: object, *, expected_rank: int) -> CandidateRank:
    raw = _mapping(value, label="candidate rank", fields=frozenset({"agent_id", "rank", "score"}))
    if raw["rank"] != expected_rank:
        raise ValueError("candidate ranks must be consecutive and ordered")
    return CandidateRank(
        _identifier(raw["agent_id"], label="rank agent_id"),
        expected_rank,
        _probability(raw["score"], label="rank score"),
    )


def _ranks(value: object, *, label: str) -> tuple[CandidateRank, ...]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ValueError(f"{label} must be a bounded list")
    result = tuple(_parse_rank(item, expected_rank=index) for index, item in enumerate(value, 1))
    if len({item.agent_id for item in result}) != len(result):
        raise ValueError(f"{label} contains duplicate agents")
    if any(left.score < right.score for left, right in itertools.pairwise(result)):
        raise ValueError(f"{label} scores must be descending")
    return result


def _parse_coverage(value: object) -> CoverageClaim:
    raw = _mapping(value, label="coverage", fields=frozenset({"requirement", "agent_ids"}))
    return CoverageClaim(
        _text(raw["requirement"], label="coverage requirement", maximum=MAX_LABEL_CHARS),
        _items(raw["agent_ids"], label="coverage agent_ids", identifiers=True, required=True),
    )


def _parse_evidence(value: object) -> SelectionEvidence:
    raw = _mapping(
        value, label="selection evidence", fields=frozenset({"agent_id", "reason_codes"})
    )
    return SelectionEvidence(
        _identifier(raw["agent_id"], label="evidence agent_id"),
        _items(raw["reason_codes"], label="reason_codes", identifiers=True, required=True),
    )


def _parse_context(value: object) -> ContextBinding:
    raw = _mapping(value, label="context binding", fields=frozenset({"agent_id", "context_id"}))
    return ContextBinding(
        _identifier(raw["agent_id"], label="context agent_id"),
        _identifier(raw["context_id"], label="context_id"),
    )


def _parse_shadow(value: object) -> ShadowEvidence:
    raw = _mapping(
        value,
        label="shadow evidence",
        fields=frozenset({"agent_id", "rank", "reason_codes", "fallback_agent_id", "tradeoff"}),
    )
    if isinstance(raw["rank"], bool) or not isinstance(raw["rank"], int) or raw["rank"] < 1:
        raise ValueError("shadow rank is invalid")
    fallback = str(raw["fallback_agent_id"] or "").strip().casefold()
    if fallback and _IDENTIFIER_RE.fullmatch(fallback) is None:
        raise ValueError("shadow fallback agent is invalid")
    return ShadowEvidence(
        _identifier(raw["agent_id"], label="shadow agent_id"),
        raw["rank"],
        _items(raw["reason_codes"], label="shadow reason_codes", identifiers=True, required=True),
        fallback,
        _text(raw["tradeoff"], label="shadow tradeoff", maximum=256),
    )


def _objects(value: object, parser: Any, *, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ValueError(f"{label} must be a bounded list")
    return tuple(parser(item) for item in value)


def _parse_row(value: object) -> UnitRecruitment:
    raw = _mapping(value, label="unit recruitment", fields=_ROW_FIELDS)
    unit_id = _identifier(raw["unit_id"], label="unit_id")
    delivery = _identifier(raw["delivery"], label="delivery")
    timing = _identifier(raw["timing"], label="timing")
    if delivery not in _DELIVERY or timing not in _TIMING:
        raise ValueError("delivery or timing is invalid")
    return UnitRecruitment(
        unit_id=unit_id,
        required=_items(raw["required"], label="required", identifiers=True),
        acceptable=_items(raw["acceptable"], label="acceptable", identifiers=True),
        forbidden=_items(raw["forbidden"], label="forbidden", identifiers=True),
        selected=_items(raw["selected"], label="selected", identifiers=True),
        runner_up=_items(raw["runner_up"], label="runner_up", identifiers=True),
        ranked_semantic=_ranks(raw["ranked_semantic"], label="ranked_semantic"),
        ranked_enabled=_ranks(raw["ranked_enabled"], label="ranked_enabled"),
        ranked_executable=_ranks(raw["ranked_executable"], label="ranked_executable"),
        disabled_shadows=_objects(raw["disabled_shadows"], _parse_shadow, label="disabled_shadows"),
        unavailable_shadows=_objects(
            raw["unavailable_shadows"], _parse_shadow, label="unavailable_shadows"
        ),
        coverage=_objects(raw["coverage"], _parse_coverage, label="coverage"),
        positive_evidence=_objects(
            raw["positive_evidence"], _parse_evidence, label="positive_evidence"
        ),
        negative_evidence=_objects(
            raw["negative_evidence"], _parse_evidence, label="negative_evidence"
        ),
        contexts=_objects(raw["contexts"], _parse_context, label="contexts"),
        confidence=_probability(raw["confidence"], label="confidence"),
        margin=_probability(raw["margin"], label="margin"),
        delivery=delivery,
        timing=timing,
        abstention_reasons=_items(
            raw["abstention_reasons"], label="abstention_reasons", identifiers=True
        ),
    )


def parse_recruiter_proposal(value: object, plan: WorkUnitPlan) -> RecruiterProposal:
    raw = _mapping(value, label="recruiter proposal", fields=_PROPOSAL_FIELDS)
    if raw["schema_version"] != RECRUITMENT_SCHEMA_VERSION:
        raise ValueError("recruiter proposal schema_version is unsupported")
    if raw["plan_hash"] != plan.plan_hash:
        raise ValueError("recruiter proposal plan hash does not match")
    fingerprint = str(raw["roster_fingerprint"] or "").strip().casefold()
    if _DIGEST_RE.fullmatch(fingerprint) is None:
        raise ValueError("recruiter roster fingerprint is invalid")
    count = raw["roster_count"]
    generation = raw["roster_generation"]
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count < 0
        or isinstance(generation, bool)
        or not isinstance(generation, int)
        or generation < 0
    ):
        raise ValueError("recruiter roster count or generation is invalid")
    raw_units = raw["units"]
    if not isinstance(raw_units, list) or len(raw_units) != len(plan.units):
        raise ValueError("recruiter proposal must contain one row per work unit")
    units = tuple(_parse_row(item) for item in raw_units)
    if tuple(item.unit_id for item in units) != tuple(item.unit_id for item in plan.units):
        raise ValueError("recruiter proposal unit order does not match plan")
    return RecruiterProposal(
        RECRUITMENT_SCHEMA_VERSION,
        plan.plan_hash,
        fingerprint,
        count,
        generation,
        units,
    )


__all__ = [
    "PLAN_SCHEMA_VERSION",
    "RECRUITMENT_SCHEMA_VERSION",
    "CandidateRank",
    "ContextBinding",
    "CoverageClaim",
    "RecruiterProposal",
    "SelectionEvidence",
    "ShadowEvidence",
    "UnitRecruitment",
    "WorkUnit",
    "WorkUnitPlan",
    "parse_recruiter_proposal",
    "parse_work_unit_plan",
]
