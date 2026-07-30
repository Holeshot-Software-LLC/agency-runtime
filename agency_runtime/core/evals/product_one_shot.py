"""One-shot host execution joined to independent product acceptance evidence."""

from __future__ import annotations

import hashlib
import math
import os
import re
import stat
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.evals.product_scenarios import ProductScenario
from agency_runtime.core.evals.product_validation import (
    PRODUCT_VALIDATION_SCHEMA_VERSION,
    validate_product_workspace,
)
from agency_runtime.core.store.security import metadata_is_link_or_reparse_point

PRODUCT_TRIAL_SCHEMA_VERSION: Final[int] = 1
PRODUCT_TRIAL_MODES: Final[tuple[str, ...]] = ("agency", "native-only")
PRODUCT_TRIAL_HOSTS: Final[tuple[str, ...]] = ("codex", "claude", "openclaw", "hermes", "zcode")
MAX_PRODUCT_TRIAL_TIMEOUT_SECONDS: Final[float] = 3600.0
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class ProductHostExecution:
    host: str
    mode: str
    status: str
    exit_code: int
    duration_ms: float
    profile_scope: str
    runtime_contract_passed: bool
    agency_evidence: Mapping[str, Any]
    requested_model: str = ""
    actual_model: str = ""
    router: str = ""
    response_summary: str = ""
    error: str = ""
    workspace_write_proven: bool | None = None


@dataclass(frozen=True, slots=True)
class ProductTrialReport:
    scenario_id: str
    trial_id: str
    host: str
    mode: str
    prompt_hash: str
    host_execution: ProductHostExecution
    validation: Mapping[str, Any]

    @property
    def passed(self) -> bool:
        return bool(
            self.host_execution.status == "completed"
            and self.host_execution.exit_code == 0
            and self.host_execution.runtime_contract_passed
            and self.validation.get("passed") is True
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PRODUCT_TRIAL_SCHEMA_VERSION,
            "scenario_id": self.scenario_id,
            "trial_id": self.trial_id,
            "host": self.host,
            "mode": self.mode,
            "prompt_hash": self.prompt_hash,
            "host_execution": asdict(self.host_execution),
            "validation": dict(self.validation),
            "passed": self.passed,
            "claim_boundary": (
                "This report proves one exact host, mode, scenario, platform, and artifact set. "
                "It does not establish cross-host, cross-platform, or comparative superiority."
            ),
        }


HostExecutor = Callable[..., ProductHostExecution]


def product_trial_confirmation(scenario_id: str, host: str, mode: str) -> str:
    return f"RUN LIVE PRODUCT EVAL {scenario_id} {host} {mode}"


def _identifier(value: str, *, field: str) -> str:
    normalized = str(value or "").strip().casefold()
    if _ID.fullmatch(normalized) is None:
        raise ValueError(f"{field} is invalid")
    return normalized


def _timeout(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 1 <= float(value) <= MAX_PRODUCT_TRIAL_TIMEOUT_SECONDS
    ):
        raise ValueError(
            f"timeout must be between 1 and {MAX_PRODUCT_TRIAL_TIMEOUT_SECONDS:g} seconds"
        )
    return float(value)


def _empty_workspace(path: Path) -> Path:
    try:
        workspace = path.expanduser().resolve(strict=True)
        metadata = os.lstat(workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("product trial workspace must already exist") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("product trial workspace must be a real directory")
    try:
        populated = next(workspace.iterdir(), None)
    except OSError as exc:
        raise ValueError("product trial workspace cannot be inspected") from exc
    if populated is not None:
        raise ValueError("product trial workspace must be empty")
    return workspace


def _default_executor(**kwargs: Any) -> ProductHostExecution:
    from agency_runtime.core.evals.product_host import execute_product_host

    return execute_product_host(**kwargs)


def run_product_trial(
    scenario: ProductScenario,
    *,
    trial_id: str,
    host: str,
    mode: str,
    workspace: Path,
    timeout: float,
    confirm: str,
    model: str = "",
    executor: HostExecutor = _default_executor,
) -> ProductTrialReport:
    """Execute one explicit live build and grade its resulting artifacts."""

    normalized_trial = _identifier(trial_id, field="trial_id")
    normalized_host = _identifier(host, field="host")
    normalized_mode = _identifier(mode, field="mode")
    if normalized_host not in PRODUCT_TRIAL_HOSTS:
        raise ValueError("product trial host is unsupported")
    if normalized_mode not in PRODUCT_TRIAL_MODES:
        raise ValueError("product trial mode is unsupported")
    bounded_timeout = _timeout(timeout)
    expected = product_trial_confirmation(scenario.scenario_id, normalized_host, normalized_mode)
    if confirm != expected:
        raise ValueError(f"confirmation must exactly match: {expected}")
    target = _empty_workspace(workspace)
    prompt = scenario.prompt(trial_id=normalized_trial)
    prompt_hash = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    started = time.monotonic()
    execution = executor(
        prompt=prompt,
        prompt_hash=prompt_hash,
        host=normalized_host,
        mode=normalized_mode,
        workspace=target,
        timeout=bounded_timeout,
        model=str(model or "").strip(),
    )
    elapsed_ms = (time.monotonic() - started) * 1000
    if not isinstance(execution, ProductHostExecution):
        raise RuntimeError("product host executor returned an invalid result")
    if execution.host != normalized_host or execution.mode != normalized_mode:
        raise RuntimeError("product host executor returned mismatched identity evidence")
    if not math.isfinite(execution.duration_ms) or execution.duration_ms < 0:
        raise RuntimeError("product host executor returned invalid duration evidence")
    if execution.duration_ms > (bounded_timeout * 1000) + 1000:
        raise RuntimeError("product host executor exceeded its bounded duration evidence")
    validation = (
        {
            "schema_version": PRODUCT_VALIDATION_SCHEMA_VERSION,
            "scenario_id": scenario.scenario_id,
            "workspace_digest": "",
            "artifacts": [],
            "checks": [],
            "passed": False,
            "status": "skipped",
            "reason": "workspace_write_not_proven",
        }
        if execution.workspace_write_proven is not True
        else validate_product_workspace(target, scenario).as_dict()
    )
    projected = execution
    if execution.duration_ms == 0 and elapsed_ms > 0:
        projected = ProductHostExecution(
            **{**asdict(execution), "duration_ms": round(elapsed_ms, 3)}
        )
    return ProductTrialReport(
        scenario.scenario_id,
        normalized_trial,
        normalized_host,
        normalized_mode,
        prompt_hash,
        projected,
        validation,
    )


__all__ = [
    "MAX_PRODUCT_TRIAL_TIMEOUT_SECONDS",
    "PRODUCT_TRIAL_HOSTS",
    "PRODUCT_TRIAL_MODES",
    "PRODUCT_TRIAL_SCHEMA_VERSION",
    "ProductHostExecution",
    "ProductTrialReport",
    "product_trial_confirmation",
    "run_product_trial",
]
