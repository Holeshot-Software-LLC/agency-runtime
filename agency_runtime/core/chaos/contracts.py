"""Portable contracts for the agent-chaos harness (AR-362).

Five frozen records describe one chaos run end to end. An ``Experiment``
names a scenario and its cases; its ``Effect`` injects exactly one fault
through an adapter Agency owns and always removes it; ``Safety`` keeps the
run inside a dedicated, rolled-back runtime so it can never touch a live
user turn; the ``Oracle`` turns observations into a bounded, content-free
``Verdict``; and the ``Receipt`` seals the whole run as evidence. The
concept is lifted from LobeHub's achaos packages (owner-approved
2026-09-01); the records here are deliberately small so a scenario is a
few named callables rather than a framework.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agency_runtime.core.chaos.safety import ChaosEnvelope

CHAOS_RECEIPT_SCHEMA = "agency.chaos-receipt.v1"
CHAOS_REPORT_SCHEMA = "agency.chaos-report.v1"
CHAOS_SUMMARY_SCHEMA = "agency.chaos-summary.v1"
CHAOS_SESSION_PREFIX = "chaos-"
CHAOS_GATE_VARIABLE = "AGENCY_CHAOS_MODE"
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICTS = frozenset({VERDICT_PASS, VERDICT_FAIL})
MAX_CHAOS_REASON_CODES = 32
MAX_CHAOS_GAP_NOTES = 16
MAX_CHAOS_NOTE_CHARS = 400
MAX_CHAOS_DESCRIPTION_CHARS = 400
# Six levels: report -> case -> effect/observed -> attempt -> row -> scalar list.
MAX_CHAOS_OBSERVATION_DEPTH = 6
MAX_CHAOS_OBSERVATION_NODES = 512
MAX_CHAOS_OBSERVATION_CHARS = 200
MAX_CHAOS_OBSERVATION_KEY_CHARS = 64
MAX_CHAOS_CASES = 16
MAX_CHAOS_IDENTITIES = 64
_REASON_CODE = re.compile(r"^[a-z][a-z0-9_]{1,95}$")
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

CaseParameters = Mapping[str, Any]
EffectDetail = dict[str, Any]
EffectApplier = Callable[["ChaosEnvelope", CaseParameters], AbstractContextManager[EffectDetail]]
ExperimentAction = Callable[["ChaosEnvelope", CaseParameters, EffectDetail], Mapping[str, Any]]
OracleJudge = Callable[[Mapping[str, Mapping[str, Any]]], "Verdict"]


class ChaosSafetyError(RuntimeError):
    """Refuse a chaos step that would leave its dedicated envelope."""


def chaos_name(value: object, *, label: str) -> str:
    """Return one lowercase identifier token or raise ``ValueError``."""

    normalized = str(value or "").strip()
    if _NAME.fullmatch(normalized) is None:
        raise ValueError(f"chaos {label} must match {_NAME.pattern}")
    return normalized


def chaos_description(value: object) -> str:
    """Return one bounded printable description or raise ``ValueError``."""

    normalized = " ".join(str(value or "").split())
    if not normalized or len(normalized) > MAX_CHAOS_DESCRIPTION_CHARS:
        raise ValueError("chaos description must be 1 to 400 printable characters")
    return normalized


def project_chaos_reason_codes(value: object) -> tuple[str, ...]:
    """Validate one bounded, content-free reason-code sequence or raise."""

    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("chaos reason codes must be a sequence")
    if len(value) > MAX_CHAOS_REASON_CODES:
        raise ValueError("chaos reason codes exceed the bound")
    codes: list[str] = []
    for item in value:
        if not isinstance(item, str) or _REASON_CODE.fullmatch(item) is None:
            raise ValueError("chaos reason code is not an allowlisted token")
        if item not in codes:
            codes.append(item)
    return tuple(codes)


def project_chaos_notes(value: object) -> tuple[str, ...]:
    """Validate one bounded sequence of printable gap notes or raise."""

    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("chaos notes must be a sequence")
    if len(value) > MAX_CHAOS_GAP_NOTES:
        raise ValueError("chaos notes exceed the bound")
    notes: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("chaos note must be a string")
        normalized = " ".join(item.split())
        if not normalized or len(normalized) > MAX_CHAOS_NOTE_CHARS or not normalized.isprintable():
            raise ValueError("chaos note must be 1 to 400 printable characters")
        notes.append(normalized)
    return tuple(notes)


def _project_scalar(item: object) -> Any:
    if item is None or isinstance(item, bool):
        return item
    if isinstance(item, int):
        return item
    if isinstance(item, float):
        if not math.isfinite(item):
            raise ValueError("chaos observations allow only finite numbers")
        return item
    if isinstance(item, str):
        if len(item) > MAX_CHAOS_OBSERVATION_CHARS or not item.isprintable():
            raise ValueError("chaos observation strings must be short and printable")
        return item
    raise ValueError("chaos observations allow only scalars, lists, and mappings")


def project_chaos_observations(value: object) -> dict[str, Any]:
    """Copy observations into plain bounded scalars, lists, and mappings.

    The bound is structural: only short printable strings, numbers, booleans,
    lists, and string-keyed mappings survive, to a fixed depth and node count.
    Oracles record statuses, codes, and counts; the projection makes sure a
    receipt can never grow into a transcript.
    """

    budget = [MAX_CHAOS_OBSERVATION_NODES]

    def visit(item: object, depth: int) -> Any:
        budget[0] -= 1
        if budget[0] < 0:
            raise ValueError("chaos observations exceed the node bound")
        if isinstance(item, (Mapping, list, tuple)):
            if depth >= MAX_CHAOS_OBSERVATION_DEPTH:
                raise ValueError("chaos observations exceed the depth bound")
            if isinstance(item, Mapping):
                projected: dict[str, Any] = {}
                for key, child in item.items():
                    if (
                        not isinstance(key, str)
                        or not key
                        or len(key) > MAX_CHAOS_OBSERVATION_KEY_CHARS
                    ):
                        raise ValueError("chaos observation keys must be short strings")
                    projected[key] = visit(child, depth + 1)
                return projected
            return [visit(child, depth + 1) for child in item]
        return _project_scalar(item)

    if not isinstance(value, Mapping):
        raise ValueError("chaos observations must be a mapping")
    return visit(value, 0)


def project_chaos_identities(value: object) -> tuple[str, ...]:
    """Validate one bounded sequence of observed correlation or row ids."""

    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        raise ValueError("chaos identities must be a sequence")
    if len(value) > MAX_CHAOS_IDENTITIES:
        raise ValueError("chaos identities exceed the bound")
    identities: list[str] = []
    for item in value:
        if (
            not isinstance(item, str)
            or not item
            or len(item) > MAX_CHAOS_OBSERVATION_CHARS
            or not item.isprintable()
        ):
            raise ValueError("chaos identity must be a short printable string")
        if item not in identities:
            identities.append(item)
    return tuple(identities)


def case_label(case: CaseParameters) -> str:
    """Return the label naming one experiment case inside receipts."""

    if not isinstance(case, Mapping):
        raise ValueError("chaos case parameters must be a mapping")
    if not case:
        return "default"
    return chaos_name(case.get("case"), label="case label")


@dataclass(frozen=True)
class Verdict:
    """Explicit pass/fail judgment with only allowlisted codes and notes."""

    outcome: str
    reason_codes: tuple[str, ...] = ()
    observations: Mapping[str, Any] = field(default_factory=dict)
    gap_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.outcome not in VERDICTS:
            raise ValueError("chaos verdict outcome must be pass or fail")
        object.__setattr__(self, "reason_codes", project_chaos_reason_codes(self.reason_codes))
        object.__setattr__(self, "observations", project_chaos_observations(self.observations))
        object.__setattr__(self, "gap_notes", project_chaos_notes(self.gap_notes))

    @property
    def passed(self) -> bool:
        return self.outcome == VERDICT_PASS

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "reason_codes": list(self.reason_codes),
            "observations": project_chaos_observations(self.observations),
            "gap_notes": list(self.gap_notes),
        }


@dataclass(frozen=True)
class Effect:
    """One injected fault, applied through an owned adapter and always removed.

    ``apply`` returns a context manager: entering it installs the fault for
    one case and yields a mutable bounded detail mapping the effect may keep
    updating while the action runs (call counts, kill receipts); leaving it
    removes the fault even when the action raised.
    """

    name: str
    description: str
    apply: EffectApplier

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", chaos_name(self.name, label="effect name"))
        object.__setattr__(self, "description", chaos_description(self.description))
        if not callable(self.apply):
            raise ValueError("chaos effect apply must be callable")


@dataclass(frozen=True)
class Oracle:
    """The explicit judgment turning per-case observations into a verdict."""

    name: str
    description: str
    judge: OracleJudge

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", chaos_name(self.name, label="oracle name"))
        object.__setattr__(self, "description", chaos_description(self.description))
        if not callable(self.judge):
            raise ValueError("chaos oracle judge must be callable")


@dataclass(frozen=True)
class Safety:
    """Bounds that keep every experiment off live user turns.

    A run is armed only inside a dedicated owner-private runtime home with
    its own Store, synthetic ``session_prefix`` sessions, and a process-wide
    ``gate_variable`` that effects check before injecting anything. The
    envelope is rolled back on exit even when the experiment raises.
    """

    session_prefix: str = CHAOS_SESSION_PREFIX
    gate_variable: str = CHAOS_GATE_VARIABLE

    def __post_init__(self) -> None:
        prefix = str(self.session_prefix or "")
        if (
            not prefix.endswith("-")
            or chaos_name(prefix[:-1], label="session prefix") != prefix[:-1]
        ):
            raise ValueError("chaos session prefix must be one identifier token ending in '-'")
        gate = str(self.gate_variable or "")
        if re.fullmatch(r"^AGENCY_[A-Z0-9_]{1,40}$", gate) is None:
            raise ValueError("chaos gate variable must be one AGENCY_ environment name")

    def arm(
        self,
        experiment: str,
        *,
        environ: Mapping[str, str] | None = None,
        runtime_root: Path | None = None,
    ) -> AbstractContextManager[ChaosEnvelope]:
        """Return the armed-envelope context manager for one experiment run."""

        from agency_runtime.core.chaos.safety import arm_safety

        return arm_safety(self, experiment, environ=environ, runtime_root=runtime_root)


@dataclass(frozen=True)
class Experiment:
    """A named scenario: cases, the fault, the bounds, the driver, the judge."""

    name: str
    description: str
    effect: Effect
    safety: Safety
    oracle: Oracle
    action: ExperimentAction
    cases: tuple[CaseParameters, ...] = ({},)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", chaos_name(self.name, label="experiment name"))
        object.__setattr__(self, "description", chaos_description(self.description))
        if not callable(self.action):
            raise ValueError("chaos experiment action must be callable")
        cases = tuple(self.cases)
        if not 1 <= len(cases) <= MAX_CHAOS_CASES:
            raise ValueError("chaos experiment must declare 1 to 16 cases")
        labels = [case_label(case) for case in cases]
        if len(set(labels)) != len(labels):
            raise ValueError("chaos experiment case labels must be unique")
        for case in cases:
            project_chaos_observations(case)
        object.__setattr__(self, "cases", cases)

    def case_labels(self) -> Iterator[str]:
        for case in self.cases:
            yield case_label(case)


@dataclass(frozen=True)
class Receipt:
    """Sealed evidence for one experiment run under ``CHAOS_RECEIPT_SCHEMA``."""

    experiment: str
    description: str
    started_at: str
    finished_at: str
    effect_name: str
    effect_applied: bool
    effect_detail: Mapping[str, Mapping[str, Any]]
    safety: Mapping[str, Any]
    oracle_name: str
    verdict: Verdict
    session_ids: tuple[str, ...] = ()
    trace_ids: tuple[str, ...] = ()
    run_ids: tuple[str, ...] = ()
    failure_receipt_ids: tuple[str, ...] = ()
    schema: str = CHAOS_RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CHAOS_RECEIPT_SCHEMA:
            raise ValueError("chaos receipt schema is not supported")
        object.__setattr__(self, "experiment", chaos_name(self.experiment, label="experiment name"))
        object.__setattr__(self, "effect_detail", project_chaos_observations(self.effect_detail))
        object.__setattr__(self, "safety", project_chaos_observations(self.safety))
        for name in ("session_ids", "trace_ids", "run_ids", "failure_receipt_ids"):
            object.__setattr__(self, name, project_chaos_identities(getattr(self, name)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "experiment": self.experiment,
            "description": self.description,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "effect": {
                "name": self.effect_name,
                "applied": bool(self.effect_applied),
                "detail": project_chaos_observations(self.effect_detail),
            },
            "safety": project_chaos_observations(self.safety),
            "oracle": {"name": self.oracle_name, **self.verdict.as_dict()},
            "gap_notes": list(self.verdict.gap_notes),
            "session_ids": list(self.session_ids),
            "trace_ids": list(self.trace_ids),
            "run_ids": list(self.run_ids),
            "failure_receipt_ids": list(self.failure_receipt_ids),
        }


def project_chaos_receipt(value: object) -> dict[str, Any] | None:
    """Validate one stored chaos receipt document without trusting its author."""

    if not isinstance(value, Mapping) or value.get("schema") != CHAOS_RECEIPT_SCHEMA:
        return None
    effect = value.get("effect")
    oracle = value.get("oracle")
    if not isinstance(effect, Mapping) or not isinstance(oracle, Mapping):
        return None
    try:
        verdict = Verdict(
            str(oracle.get("outcome") or ""),
            reason_codes=tuple(oracle.get("reason_codes") or ()),
            observations=oracle.get("observations") or {},
            gap_notes=tuple(value.get("gap_notes") or ()),
        )
        receipt = Receipt(
            experiment=str(value.get("experiment") or ""),
            description=chaos_description(value.get("description")),
            started_at=str(value.get("started_at") or ""),
            finished_at=str(value.get("finished_at") or ""),
            effect_name=chaos_name(effect.get("name"), label="effect name"),
            effect_applied=bool(effect.get("applied")),
            effect_detail=effect.get("detail") or {},
            safety=value.get("safety") or {},
            oracle_name=chaos_name(oracle.get("name"), label="oracle name"),
            verdict=verdict,
            session_ids=tuple(value.get("session_ids") or ()),
            trace_ids=tuple(value.get("trace_ids") or ()),
            run_ids=tuple(value.get("run_ids") or ()),
            failure_receipt_ids=tuple(value.get("failure_receipt_ids") or ()),
        )
    except (TypeError, ValueError):
        return None
    return receipt.as_dict()


__all__ = [
    "CHAOS_GATE_VARIABLE",
    "CHAOS_RECEIPT_SCHEMA",
    "CHAOS_REPORT_SCHEMA",
    "CHAOS_SESSION_PREFIX",
    "CHAOS_SUMMARY_SCHEMA",
    "MAX_CHAOS_CASES",
    "MAX_CHAOS_GAP_NOTES",
    "MAX_CHAOS_REASON_CODES",
    "VERDICT_FAIL",
    "VERDICT_PASS",
    "ChaosSafetyError",
    "Effect",
    "Experiment",
    "Oracle",
    "Receipt",
    "Safety",
    "Verdict",
    "case_label",
    "chaos_description",
    "chaos_name",
    "project_chaos_identities",
    "project_chaos_notes",
    "project_chaos_observations",
    "project_chaos_reason_codes",
    "project_chaos_receipt",
]
