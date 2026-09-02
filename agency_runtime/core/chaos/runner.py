"""Run chaos experiments, seal their receipts, and summarize them (AR-362).

A run is a receipt, not a log line: every experiment writes one sealed
owner-private ``receipt.json`` under the chaos evidence root, mirroring the
harness battery's receipt trail, so chaos results are evidence that survives
the rolled-back runtime they ran in. ``chaos_report_summary`` is the small
projection the battery report can embed later without importing anything
else from this package.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.chaos.contracts import (
    CHAOS_REPORT_SCHEMA,
    CHAOS_SUMMARY_SCHEMA,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICTS,
    ChaosSafetyError,
    Experiment,
    Receipt,
    Verdict,
    case_label,
    chaos_name,
    project_chaos_observations,
    project_chaos_reason_codes,
)
from agency_runtime.core.chaos.experiments import RUNNER_HARD_KILL, STAFFING_WINDOW
from agency_runtime.core.chaos.safety import ChaosEnvelope
from agency_runtime.core.preflight_failure import preflight_exception_category
from agency_runtime.core.private_paths import ensure_private_directory

CHAOS_EXPERIMENTS: tuple[Experiment, ...] = (STAFFING_WINDOW, RUNNER_HARD_KILL)
CHAOS_EXPERIMENT_NAMES: tuple[str, ...] = tuple(item.name for item in CHAOS_EXPERIMENTS)
MAX_CHAOS_SUMMARY_RECEIPTS = 64
_IDENTITY_KEYS = ("session_ids", "trace_ids", "run_ids", "failure_receipt_ids")


def default_receipt_root() -> Path:
    return Path("~/.agency-runtime/evidence/chaos").expanduser()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_experiments(names: Sequence[str] | None) -> tuple[Experiment, ...]:
    """Return the named experiments in declaration order, or every experiment."""

    if names is None:
        return CHAOS_EXPERIMENTS
    if isinstance(names, str) or not isinstance(names, Sequence) or not names:
        raise ValueError("chaos experiment names must be a non-empty sequence")
    requested = {str(item) for item in names}
    unknown = requested - set(CHAOS_EXPERIMENT_NAMES)
    if unknown:
        raise ValueError(
            "unknown chaos experiment; choose from " + ", ".join(CHAOS_EXPERIMENT_NAMES)
        )
    return tuple(item for item in CHAOS_EXPERIMENTS if item.name in requested)


def _collect_identities(target: dict[str, list[str]], value: object) -> None:
    if not isinstance(value, Mapping):
        return
    for key in _IDENTITY_KEYS:
        items = value.get(key)
        if isinstance(items, (list, tuple)):
            target[key].extend(str(item) for item in items if str(item))


def _run_cases(
    experiment: Experiment,
    envelope: ChaosEnvelope,
    observations: dict[str, Any],
    effect_details: dict[str, Any],
    identities: dict[str, list[str]],
) -> None:
    """Apply the effect and drive the action once per case, in declaration order.

    The effect's detail is snapshotted after the action so counters it kept
    updating (invoker calls, kill receipts, removal) are visible, and the
    snapshot is folded into that case's observations under ``effect`` so the
    oracle can judge the injection alongside the system's response.
    """

    for case in experiment.cases:
        label = case_label(case)
        with experiment.effect.apply(envelope, case) as detail:
            observed = dict(experiment.action(envelope, case, detail))
        snapshot = project_chaos_observations(detail)
        _collect_identities(identities, observed.pop("identities", None))
        observed["effect"] = snapshot
        observations[label] = project_chaos_observations(observed)
        effect_details[label] = snapshot


def run_experiment(
    experiment: Experiment,
    *,
    environ: Mapping[str, str] | None = None,
    runtime_root: Path | None = None,
) -> Receipt:
    """Run one experiment inside an armed envelope and return its receipt.

    An experiment that raises is a failed experiment, not a crashed harness:
    the receipt records the exception category (never its text) and whatever
    observations were gathered, and the envelope is still rolled back.
    """

    started = _now()
    observations: dict[str, Any] = {}
    effect_details: dict[str, Any] = {}
    identities: dict[str, list[str]] = {key: [] for key in _IDENTITY_KEYS}
    envelope: ChaosEnvelope | None = None
    error_code = ""
    try:
        with experiment.safety.arm(
            experiment.name,
            environ=environ,
            runtime_root=runtime_root,
        ) as envelope:
            _run_cases(experiment, envelope, observations, effect_details, identities)
    except ChaosSafetyError:
        error_code = "safety_refused"
    except Exception as error:
        error_code = f"experiment_raised_{preflight_exception_category(error)}"
    if error_code:
        verdict = Verdict(VERDICT_FAIL, reason_codes=(error_code,), observations=observations)
    else:
        try:
            verdict = experiment.oracle.judge(observations)
        except Exception as error:
            # A judge that cannot read its own observations is a failed
            # experiment with a receipt, never a crashed harness.
            verdict = Verdict(
                VERDICT_FAIL,
                reason_codes=(f"oracle_raised_{preflight_exception_category(error)}",),
            )
    safety = envelope.receipt() if envelope is not None else {"armed": False}
    return Receipt(
        experiment=experiment.name,
        description=experiment.description,
        started_at=started,
        finished_at=_now(),
        effect_name=experiment.effect.name,
        effect_applied=len(effect_details) == len(experiment.cases),
        effect_detail=effect_details,
        safety=safety,
        oracle_name=experiment.oracle.name,
        verdict=verdict,
        session_ids=tuple(identities["session_ids"]),
        trace_ids=tuple(identities["trace_ids"]),
        run_ids=tuple(identities["run_ids"]),
        failure_receipt_ids=tuple(identities["failure_receipt_ids"]),
    )


def write_chaos_receipt(root: Path, receipt: Receipt) -> Path:
    """Seal one receipt as a fresh owner-private file under ``root``."""

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = ensure_private_directory(Path(root) / f"{stamp}-{receipt.experiment}")
    target = directory / "receipt.json"
    serialized = json.dumps(receipt.as_dict(), indent=1, sort_keys=True) + "\n"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, serialized.encode("utf-8"))
    finally:
        os.close(descriptor)
    return target


def run_chaos_experiments(
    names: Sequence[str] | None = None,
    *,
    receipt_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
    runtime_root: Path | None = None,
) -> dict[str, Any]:
    """Run the selected experiments, seal a receipt each, and report verdicts."""

    selected = resolve_experiments(names)
    root = Path(receipt_root) if receipt_root is not None else default_receipt_root()
    results: dict[str, Any] = {}
    for experiment in selected:
        receipt = run_experiment(experiment, environ=environ, runtime_root=runtime_root)
        path = write_chaos_receipt(root, receipt)
        results[experiment.name] = {
            "verdict": receipt.verdict.outcome,
            "reason_codes": list(receipt.verdict.reason_codes),
            "gap_notes": list(receipt.verdict.gap_notes),
            "cases": list(experiment.case_labels()),
            "effect_applied": receipt.effect_applied,
            "receipt_path": str(path),
            "started_at": receipt.started_at,
            "finished_at": receipt.finished_at,
        }
    return {
        "schema": CHAOS_REPORT_SCHEMA,
        "receipt_root": str(root),
        "experiments": results,
        "passed": bool(results)
        and all(item["verdict"] == VERDICT_PASS for item in results.values()),
    }


def chaos_report_summary(report: Mapping[str, Any]) -> dict[str, Any]:
    """Project one chaos report into the bounded shape a battery report can embed."""

    if not isinstance(report, Mapping) or report.get("schema") != CHAOS_REPORT_SCHEMA:
        raise ValueError("chaos report schema is not supported")
    experiments = report.get("experiments")
    if not isinstance(experiments, Mapping):
        raise ValueError("chaos report experiments must be a mapping")
    verdicts: dict[str, str] = {}
    reason_codes: dict[str, list[str]] = {}
    receipts: list[str] = []
    failed: list[str] = []
    for raw_name, detail in sorted(experiments.items(), key=lambda item: str(item[0])):
        name = chaos_name(raw_name, label="experiment name")
        if not isinstance(detail, Mapping):
            raise ValueError("chaos report experiment entry must be a mapping")
        outcome = str(detail.get("verdict") or "")
        if outcome not in VERDICTS:
            raise ValueError("chaos report verdict must be pass or fail")
        verdicts[name] = outcome
        reason_codes[name] = list(
            project_chaos_reason_codes(tuple(detail.get("reason_codes") or ()))
        )
        if outcome != VERDICT_PASS:
            failed.append(name)
        path = str(detail.get("receipt_path") or "")
        if path and len(receipts) < MAX_CHAOS_SUMMARY_RECEIPTS:
            receipts.append(path)
    return {
        "schema": CHAOS_SUMMARY_SCHEMA,
        "passed": bool(verdicts) and not failed,
        "experiments": verdicts,
        "failed": failed,
        "reason_codes": reason_codes,
        "receipts": receipts,
    }


def run_chaos_cli(args: Any) -> int:
    """CLI adapter for ``agency chaos run``."""

    requested = getattr(args, "experiment", None)
    names = tuple(str(item) for item in requested) if requested else None
    report = run_chaos_experiments(names=names)
    if getattr(args, "json", False):
        print(json.dumps(report, indent=1, sort_keys=True))
    else:
        for name, detail in sorted(report["experiments"].items()):
            codes = ", ".join(detail["reason_codes"]) or "no findings"
            print(f"{name}: {detail['verdict']} ({codes})")
            for note in detail["gap_notes"]:
                print(f"  gap: {note}")
            print(f"  receipt: {detail['receipt_path']}")
    return 0 if report["passed"] else 1


__all__ = [
    "CHAOS_EXPERIMENTS",
    "CHAOS_EXPERIMENT_NAMES",
    "chaos_report_summary",
    "default_receipt_root",
    "resolve_experiments",
    "run_chaos_cli",
    "run_chaos_experiments",
    "run_experiment",
    "write_chaos_receipt",
]
