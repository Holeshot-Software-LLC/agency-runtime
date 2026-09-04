"""AR-395: the receipt's stage vocabulary names every stage the runtime runs.

``project_preflight_provider_attempts`` keeps an allowlisted stage label and
rewrites everything else to ``"unknown"``.  Three labels the runtime actually
passes -- ``subject``, ``security_review`` and ``safety_repair`` -- were absent
from the allowlist, so every call they spent was recorded as a stage nobody
could name.  These tests pin the allowlist to the labels found in the source,
so a stage added later fails here rather than degrading into ``unknown``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from agency_runtime.core.preflight_failure import (
    PREFLIGHT_PROVIDER_STAGES,
    project_preflight_provider_attempts,
)
from agency_runtime.core.reply_budget import STAGE_REPLY_BUDGET_TOKENS

ROOT = Path(__file__).resolve().parents[1]

# The two modules that invoke provider stages.  Every other ``stage=`` in the
# tree names a provider-configuration lookup, not an attempt a receipt records.
STAGE_SOURCES = (
    ROOT / "agency_runtime" / "core" / "workforce" / "inference.py",
    ROOT / "agency_runtime" / "core" / "workforce" / "hiring.py",
)

# Allowlist members that no call site in STAGE_SOURCES passes.  They are named
# here, with why they stay, so that the equality below is a real constraint: a
# label added to the runtime cannot be absorbed by a vague remainder.
NON_INVOCATION_STAGES = frozenset(
    {
        # The evals' provider-configuration stage (``eval_commands.py``), and
        # the planner's partner in ``_project_validation_reason_codes``.
        "combined",
        # No producer today; retained so an older receipt still projects.
        "selector",
        # The sentinel this projection writes when it cannot read a stage.
        "unknown",
    }
)

# Measured 2026-09-04: the labels whose attempts were written "unknown". The
# issue named the first three; the source scan below found the hiring critic
# and repair stages in the same condition.
STAGES_ADDED_BY_AR_395 = (
    "subject",
    "security_review",
    "safety_repair",
    "hiring-critic",
    "hiring-repair",
    "hiring-repair-critic",
)


def _stage_labels(path: Path) -> set[str]:
    """Every string literal the module passes as a ``stage=`` keyword."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "stage"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    }


def _runtime_stage_labels() -> set[str]:
    labels: set[str] = set()
    for path in STAGE_SOURCES:
        assert path.is_file(), path
        labels |= _stage_labels(path)
    return labels


def test_the_source_scan_finds_the_stage_labels_it_is_meant_to_find() -> None:
    """Guard the scan itself, so the equality below cannot pass vacuously."""

    labels = _runtime_stage_labels()
    assert {"planner", "recruiter", "critic"} <= labels
    assert set(STAGES_ADDED_BY_AR_395) <= labels


def test_the_receipt_vocabulary_equals_the_stages_the_runtime_runs() -> None:
    """Set equality against the labels found in the source (AR-395 c1, c2)."""

    assert _runtime_stage_labels() | NON_INVOCATION_STAGES == set(PREFLIGHT_PROVIDER_STAGES)


def test_every_stage_the_transport_budgets_can_name_itself_on_a_receipt() -> None:
    """A second, independent source of the same truth.

    ``STAGE_REPLY_BUDGET_TOKENS`` is the transport's own enumeration of the
    stages that run (AR-385). It is maintained beside the call sites rather
    than derived from them, so it catches a stage the source scan above could
    miss -- a label built from a variable, say. ``recall_embedding`` is the one
    direction that does not hold: an embedding call returns vectors and takes
    the fallback budget, so it is budgeted without being listed.
    """

    assert set(STAGE_REPLY_BUDGET_TOKENS) <= set(PREFLIGHT_PROVIDER_STAGES)
    assert set(STAGE_REPLY_BUDGET_TOKENS) <= _runtime_stage_labels()


@pytest.mark.parametrize("stage", STAGES_ADDED_BY_AR_395)
def test_a_stage_the_runtime_runs_names_itself_on_the_receipt(stage: str) -> None:
    """A projected attempt keeps the stage it was recorded with (AR-395 c3)."""

    projected = project_preflight_provider_attempts(
        [
            {
                "stage": stage,
                "provider_name": "agency-planner",
                "provider_type": "litellm",
                "requested_model": "task-agency-planner-v2",
                "model_group": "task-agency-planner-v2",
                "actual_model": "task-agency-planner-v2",
                "model_receipt_source": "response.body.model",
                "status": "applied",
                "reason_code": "structured_response_applied",
            }
        ]
    )
    assert projected is not None
    assert [entry["stage"] for entry in projected] == [stage]


def test_unknown_still_means_a_stage_the_projection_could_not_read() -> None:
    """An unreadable stage is still written ``unknown`` (AR-395 c4)."""

    projected = project_preflight_provider_attempts(
        [
            {
                "stage": "a stage nobody declared",
                "provider_name": "agency-planner",
                "provider_type": "litellm",
                "status": "applied",
                "reason_code": "structured_response_applied",
            }
        ]
    )
    assert projected is not None
    assert [entry["stage"] for entry in projected] == ["unknown"]
    assert "unknown" in PREFLIGHT_PROVIDER_STAGES
