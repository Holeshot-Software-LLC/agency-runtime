"""Closed-world task recognition for the Codex activation canary.

The activation verifier measures the installed hook and native-child lifecycle,
not the semantic workforce planner.  Only its exact current-profile child may
use the deterministic one-unit route assembled by the selector pipeline.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from agency_runtime.core.codex_activation_verification import (
    is_restricted_codex_activation_canary_environment,
)

CODEX_ACTIVATION_CANARY_WORK_UNIT = (
    "Identify the primary behavioral regression risk of replacing return value with "
    "return value.strip() in a Python text-normalization helper."
)
CODEX_ACTIVATION_CANARY_PROMPT = (
    "Treat this as exactly one indivisible code-review work unit. "
    "Delegate that complete work unit to exactly one sub-agent; do not subdivide it further: "
    f"{CODEX_ACTIVATION_CANARY_WORK_UNIT}"
)
CODEX_ACTIVATION_CANARY_SPECIALIST = "code-reviewer"
CODEX_ACTIVATION_CANARY_ROUTE_SOURCE = "codex_activation_canary_contract"
CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE = "activation-canary-contract"
_CODEX_ACTIVATION_CANARY_TASK = re.compile(
    re.escape(CODEX_ACTIVATION_CANARY_PROMPT) + r"\n\nCanary nonce: (?P<nonce>[0-9a-f]{32})\Z"
)


def is_exact_codex_activation_canary_task(
    task: object,
    *,
    host: object,
    capability_status: object,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Return whether this is the exact native-verified activation probe task."""

    return bool(
        type(task) is str
        and host == "codex"
        and capability_status == "native-contract-verified"
        and is_restricted_codex_activation_canary_environment(environ)
        and _CODEX_ACTIVATION_CANARY_TASK.fullmatch(task) is not None
    )


__all__ = [
    "CODEX_ACTIVATION_CANARY_PROMPT",
    "CODEX_ACTIVATION_CANARY_ROUTE_SOURCE",
    "CODEX_ACTIVATION_CANARY_SPECIALIST",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT",
    "CODEX_ACTIVATION_CANARY_WORK_UNIT_SOURCE",
    "is_exact_codex_activation_canary_task",
]
