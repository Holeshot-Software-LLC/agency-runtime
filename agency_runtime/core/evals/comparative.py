"""Bounded comparative outcome evidence for Agency-on/native-only trials.

The evaluator does not run a host or grade free-form model output. It validates
independently collected outcome observations, pairs identical scenario trials,
and prevents simulated or contract-only evidence from becoming a superiority
claim.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json

COMPARATIVE_SCHEMA_VERSION = 1
MAX_COMPARATIVE_FILE_BYTES = 4 * 1024 * 1024
MAX_COMPARATIVE_OBSERVATIONS = 4096
MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM = 20
_MAX_ID_CHARS = 128
_MAX_MODEL_CHARS = 256
_EVIDENCE_KINDS = frozenset(
    {
        "live_host",
        "installed_isolated",
        "contract_only",
        "simulated",
    }
)
_MODES = frozenset(
    {
        "native_only",
        "agency_observe",
        "agency_prefer",
        "agency_strong",
    }
)
_KNOWN_FIELDS = frozenset(
    {
        "schema_version",
        "scenario_id",
        "trial_id",
        "run_id",
        "host",
        "mode",
        "evidence_kind",
        "blinded_label",
        "completed",
        "quality_score",
        "tests_total",
        "tests_failed",
        "escaped_defects",
        "duration_ms",
        "cost_usd",
        "retries",
        "duplicate_work",
        "merge_conflicts",
        "synthesis_failures",
        "supervisor_interventions",
        "delegated_units",
        "requested_model",
        "actual_model",
        "router",
    }
)


def _bounded_text(value: Any, field: str, *, limit: int = _MAX_ID_CHARS) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > limit:
        raise ValueError(f"{field} must contain 1..{limit} characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError(f"{field} must not contain control characters")
    return normalized


def _optional_text(value: Any, field: str, *, limit: int) -> str:
    if value in (None, ""):
        return ""
    return _bounded_text(value, field, limit=limit)


def _bounded_int(value: Any, field: str, *, maximum: int = 1_000_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < 0 or value > maximum:
        raise ValueError(f"{field} must be between 0 and {maximum}")
    return value


def _bounded_float(value: Any, field: str, *, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0.0 or converted > maximum:
        raise ValueError(f"{field} is outside its supported range")
    return converted


@dataclass(frozen=True, slots=True)
class ComparativeObservation:
    """One independently measured variant of an exact scenario trial."""

    scenario_id: str
    trial_id: str
    run_id: str
    host: str
    mode: str
    evidence_kind: str
    blinded_label: str
    completed: bool
    quality_score: float
    tests_total: int
    tests_failed: int
    escaped_defects: int
    duration_ms: float
    cost_usd: float
    retries: int
    duplicate_work: int
    merge_conflicts: int
    synthesis_failures: int
    supervisor_interventions: int
    delegated_units: int
    requested_model: str = ""
    actual_model: str = ""
    router: str = ""

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ComparativeObservation:
        """Validate one strict, content-free comparative observation."""

        unknown = set(raw) - _KNOWN_FIELDS
        if unknown:
            raise ValueError("comparative observation contains unsupported fields")
        schema_version = raw.get("schema_version", COMPARATIVE_SCHEMA_VERSION)
        if schema_version != COMPARATIVE_SCHEMA_VERSION:
            raise ValueError("unsupported comparative observation schema version")
        mode = _bounded_text(raw.get("mode"), "mode")
        if mode not in _MODES:
            raise ValueError("mode is unsupported")
        evidence_kind = _bounded_text(raw.get("evidence_kind"), "evidence_kind")
        if evidence_kind not in _EVIDENCE_KINDS:
            raise ValueError("evidence_kind is unsupported")
        completed = raw.get("completed")
        if not isinstance(completed, bool):
            raise ValueError("completed must be a boolean")
        tests_total = _bounded_int(raw.get("tests_total"), "tests_total")
        tests_failed = _bounded_int(raw.get("tests_failed"), "tests_failed")
        if tests_failed > tests_total:
            raise ValueError("tests_failed must not exceed tests_total")
        return cls(
            scenario_id=_bounded_text(raw.get("scenario_id"), "scenario_id"),
            trial_id=_bounded_text(raw.get("trial_id"), "trial_id"),
            run_id=_bounded_text(raw.get("run_id"), "run_id"),
            host=_bounded_text(raw.get("host"), "host"),
            mode=mode,
            evidence_kind=evidence_kind,
            blinded_label=_bounded_text(raw.get("blinded_label"), "blinded_label"),
            completed=completed,
            quality_score=_bounded_float(
                raw.get("quality_score"),
                "quality_score",
                maximum=1.0,
            ),
            tests_total=tests_total,
            tests_failed=tests_failed,
            escaped_defects=_bounded_int(raw.get("escaped_defects"), "escaped_defects"),
            duration_ms=_bounded_float(raw.get("duration_ms"), "duration_ms", maximum=1e12),
            cost_usd=_bounded_float(raw.get("cost_usd"), "cost_usd", maximum=1e9),
            retries=_bounded_int(raw.get("retries"), "retries"),
            duplicate_work=_bounded_int(raw.get("duplicate_work"), "duplicate_work"),
            merge_conflicts=_bounded_int(raw.get("merge_conflicts"), "merge_conflicts"),
            synthesis_failures=_bounded_int(
                raw.get("synthesis_failures"),
                "synthesis_failures",
            ),
            supervisor_interventions=_bounded_int(
                raw.get("supervisor_interventions"),
                "supervisor_interventions",
            ),
            delegated_units=_bounded_int(raw.get("delegated_units"), "delegated_units"),
            requested_model=_optional_text(
                raw.get("requested_model"),
                "requested_model",
                limit=_MAX_MODEL_CHARS,
            ),
            actual_model=_optional_text(
                raw.get("actual_model"),
                "actual_model",
                limit=_MAX_MODEL_CHARS,
            ),
            router=_optional_text(raw.get("router"), "router", limit=_MAX_MODEL_CHARS),
        )

    def public_dict(self) -> dict[str, Any]:
        """Return the stable machine-readable schema without captured content."""

        return {"schema_version": COMPARATIVE_SCHEMA_VERSION, **asdict(self)}


def load_comparative_jsonl(path: Path) -> list[ComparativeObservation]:
    """Load a bounded UTF-8 JSONL evidence file without following unsafe input."""

    try:
        payload = read_bounded_regular_file(
            path,
            limit=MAX_COMPARATIVE_FILE_BYTES,
            label="comparative evidence file",
        )
    except FileSizeLimitError as exc:
        raise ValueError("comparative evidence file exceeds the 4 MiB limit") from exc
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("comparative evidence file must be UTF-8") from exc
    observations: list[ComparativeObservation] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        if len(observations) >= MAX_COMPARATIVE_OBSERVATIONS:
            raise ValueError("comparative evidence exceeds the observation limit")
        try:
            raw = safe_load_bounded_json(
                line,
                maximum_bytes=MAX_COMPARATIVE_FILE_BYTES,
                maximum_depth=8,
                maximum_nodes=256,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"comparative evidence line {line_number} is invalid JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"comparative evidence line {line_number} must be an object")
        try:
            observations.append(ComparativeObservation.from_mapping(raw))
        except ValueError as exc:
            raise ValueError(f"comparative evidence line {line_number}: {exc}") from exc
    if not observations:
        raise ValueError("comparative evidence file is empty")
    return observations


def _mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else 0.0


def _paired_metrics(
    pairs: list[tuple[ComparativeObservation, ComparativeObservation]],
) -> dict[str, Any]:
    def delta(field: str) -> float:
        return _mean(
            float(getattr(candidate, field)) - float(getattr(baseline, field))
            for baseline, candidate in pairs
        )

    regret = sum(
        1
        for baseline, candidate in pairs
        if candidate.delegated_units > 0
        and (
            candidate.quality_score < baseline.quality_score
            or (
                candidate.quality_score == baseline.quality_score
                and candidate.escaped_defects >= baseline.escaped_defects
                and (
                    candidate.duration_ms > baseline.duration_ms
                    or candidate.cost_usd > baseline.cost_usd
                )
            )
        )
    )
    blinded_pairs = sum(
        baseline.blinded_label != candidate.blinded_label for baseline, candidate in pairs
    )
    return {
        "pair_count": len(pairs),
        "blinded_pair_count": blinded_pairs,
        "completion_rate_delta": round(delta("completed"), 6),
        "quality_score_delta": round(delta("quality_score"), 6),
        "tests_failed_delta": round(delta("tests_failed"), 6),
        "escaped_defects_delta": round(delta("escaped_defects"), 6),
        "duration_ms_delta": round(delta("duration_ms"), 6),
        "cost_usd_delta": round(delta("cost_usd"), 6),
        "retries_delta": round(delta("retries"), 6),
        "duplicate_work_delta": round(delta("duplicate_work"), 6),
        "merge_conflicts_delta": round(delta("merge_conflicts"), 6),
        "synthesis_failures_delta": round(delta("synthesis_failures"), 6),
        "supervisor_interventions_delta": round(
            delta("supervisor_interventions"),
            6,
        ),
        "delegation_regret_count": regret,
        "delegation_regret_rate": round(regret / len(pairs), 6) if pairs else 0.0,
    }


def _claim_eligible(
    *,
    live_metrics: Mapping[str, Any],
    model_mismatch_count: int,
    route_identity_mismatch_count: int,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if live_metrics["pair_count"] < MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM:
        reasons.append(
            f"requires at least {MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM} paired live-host trials"
        )
    if model_mismatch_count:
        reasons.append("paired trials contain requested or actual model mismatches")
    if route_identity_mismatch_count:
        reasons.append("paired trials contain LiteLLM router identity mismatches")
    if live_metrics["blinded_pair_count"] != live_metrics["pair_count"]:
        reasons.append("every paired live-host trial requires distinct blinded labels")
    reasons.extend(
        f"{field} is negative"
        for field in (
            "completion_rate_delta",
            "quality_score_delta",
        )
        if live_metrics[field] < 0
    )
    reasons.extend(
        f"{field} is positive"
        for field in (
            "tests_failed_delta",
            "escaped_defects_delta",
            "duplicate_work_delta",
            "merge_conflicts_delta",
            "synthesis_failures_delta",
            "supervisor_interventions_delta",
        )
        if live_metrics[field] > 0
    )
    if (
        live_metrics["quality_score_delta"] <= 0
        and live_metrics["escaped_defects_delta"] >= 0
        and live_metrics["completion_rate_delta"] <= 0
    ):
        reasons.append("no measured quality, completion, or escaped-defect improvement")
    return not reasons, reasons


def evaluate_comparative_outcomes(
    observations: Iterable[ComparativeObservation | Mapping[str, Any]],
) -> dict[str, Any]:
    """Pair native-only baselines with Agency variants and report bounded deltas."""

    normalized: list[ComparativeObservation] = []
    for raw in observations:
        item = (
            raw
            if isinstance(raw, ComparativeObservation)
            else ComparativeObservation.from_mapping(raw)
        )
        normalized.append(item)
        if len(normalized) > MAX_COMPARATIVE_OBSERVATIONS:
            raise ValueError("comparative evidence exceeds the observation limit")
    if not normalized:
        raise ValueError("comparative evaluation requires observations")

    indexed: dict[tuple[str, str, str, str], ComparativeObservation] = {}
    run_ids: set[str] = set()
    for item in normalized:
        key = (item.scenario_id, item.trial_id, item.host, item.mode)
        if key in indexed:
            raise ValueError("comparative evidence contains a duplicate scenario trial mode")
        if item.run_id in run_ids:
            raise ValueError("comparative evidence contains a duplicate run id")
        indexed[key] = item
        run_ids.add(item.run_id)

    all_pairs: dict[str, list[tuple[ComparativeObservation, ComparativeObservation]]] = defaultdict(
        list
    )
    live_pairs: dict[str, list[tuple[ComparativeObservation, ComparativeObservation]]] = (
        defaultdict(list)
    )
    model_mismatches: Counter[str] = Counter()
    route_identity_mismatches: Counter[str] = Counter()
    for (scenario_id, trial_id, host, mode), candidate in indexed.items():
        if mode == "native_only":
            continue
        baseline = indexed.get((scenario_id, trial_id, host, "native_only"))
        if baseline is None or baseline.evidence_kind != candidate.evidence_kind:
            continue
        pair = (baseline, candidate)
        all_pairs[mode].append(pair)
        if candidate.evidence_kind == "live_host":
            live_pairs[mode].append(pair)
            if (
                baseline.requested_model != candidate.requested_model
                or baseline.actual_model != candidate.actual_model
            ):
                model_mismatches[mode] += 1
            if baseline.router != candidate.router:
                route_identity_mismatches[mode] += 1

    mode_reports: dict[str, Any] = {}
    for mode in sorted(_MODES - {"native_only"}):
        metrics = _paired_metrics(all_pairs[mode])
        live_metrics = _paired_metrics(live_pairs[mode])
        eligible, reasons = _claim_eligible(
            live_metrics=live_metrics,
            model_mismatch_count=model_mismatches[mode],
            route_identity_mismatch_count=route_identity_mismatches[mode],
        )
        mode_reports[mode] = {
            "all_evidence": metrics,
            "live_host": live_metrics,
            "live_model_mismatch_count": model_mismatches[mode],
            "live_route_identity_mismatch_count": route_identity_mismatches[mode],
            "directional_claim_eligible": eligible,
            "claim_limitations": reasons,
        }

    evidence_counts = Counter(item.evidence_kind for item in normalized)
    return {
        "schema_version": COMPARATIVE_SCHEMA_VERSION,
        "observation_count": len(normalized),
        "evidence_counts": {
            evidence_kind: evidence_counts[evidence_kind]
            for evidence_kind in sorted(_EVIDENCE_KINDS)
        },
        "modes": mode_reports,
        "superiority_claimed": False,
        "claim_policy": (
            "Directional claim eligibility is a minimum evidence gate, not a statistical "
            "superiority conclusion. Contract-only, isolated, and simulated observations "
            "never satisfy the live-host gate."
        ),
    }


__all__ = [
    "COMPARATIVE_SCHEMA_VERSION",
    "MAX_COMPARATIVE_FILE_BYTES",
    "MAX_COMPARATIVE_OBSERVATIONS",
    "MIN_LIVE_PAIRS_FOR_DIRECTIONAL_CLAIM",
    "ComparativeObservation",
    "evaluate_comparative_outcomes",
    "load_comparative_jsonl",
]
