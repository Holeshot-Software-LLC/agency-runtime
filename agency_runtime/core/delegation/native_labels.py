"""Lossless host-safe labels for Agency work-unit correlation."""

from __future__ import annotations

import re
from hashlib import sha256

CODEX_TASK_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
_PLANNED_WORK_UNIT_PATTERN = re.compile(r"^unit-([0-9a-f]{10})$")
_CODEX_PLANNED_TASK_PATTERN = re.compile(r"^unit_([0-9a-f]{10})$")


def codex_task_name_for_work_unit(work_unit_id: object) -> str:
    """Return a bounded Codex collaboration label for one internal work unit."""

    internal = str(work_unit_id or "").strip()
    if not internal:
        raise ValueError("work_unit_id is required for a Codex task name")
    planned = _PLANNED_WORK_UNIT_PATTERN.fullmatch(internal)
    if planned is not None:
        return f"unit_{planned.group(1)}"
    digest = sha256(internal.encode("utf-8", errors="surrogatepass")).hexdigest()[:20]
    return f"agency_{digest}"


def internal_work_unit_from_codex_task_name(task_name: object) -> str:
    """Reverse a deterministic planned-unit label without accepting lookalikes."""

    native = str(task_name or "").strip()
    if CODEX_TASK_NAME_PATTERN.fullmatch(native) is None:
        return ""
    planned = _CODEX_PLANNED_TASK_PATTERN.fullmatch(native)
    return f"unit-{planned.group(1)}" if planned is not None else ""


__all__ = [
    "CODEX_TASK_NAME_PATTERN",
    "codex_task_name_for_work_unit",
    "internal_work_unit_from_codex_task_name",
]
