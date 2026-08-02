"""Fixed, content-free Codex child tool evidence shared by rollout and Store paths."""

from __future__ import annotations

import json
from collections.abc import Mapping

CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA = "agency.codex-product-child-tool-evidence.v1"
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE = "persisted_rollout"
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_COUNT = 5_000
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS = (
    "child_tool_call_count",
    "child_function_tool_call_count",
    "child_custom_tool_call_count",
    "child_exec_tool_call_count",
    "child_apply_patch_tool_call_count",
    "child_shell_command_tool_call_count",
    "child_other_tool_call_count",
    "child_completed_tool_call_count",
    "child_failed_tool_call_count",
    "child_unknown_tool_call_count",
    "child_tool_output_count",
    "child_tool_output_missing_count",
    "child_patch_apply_success_count",
    "child_patch_apply_failure_count",
    "child_patch_apply_unknown_count",
)


def normalize_codex_child_tool_evidence(value: object) -> dict[str, int]:
    """Return one bounded exact projection or reject malformed evidence."""

    if not isinstance(value, Mapping) or set(value) != set(
        CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS
    ):
        raise ValueError("Codex child tool evidence fields were invalid")
    normalized: dict[str, int] = {}
    for field in CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS:
        observed = value.get(field)
        if (
            not isinstance(observed, int)
            or isinstance(observed, bool)
            or not 0 <= observed <= CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_COUNT
        ):
            raise ValueError("Codex child tool evidence counts were invalid")
        normalized[field] = observed
    total = normalized["child_tool_call_count"]
    if not (
        normalized["child_function_tool_call_count"] + normalized["child_custom_tool_call_count"]
        == total
        and normalized["child_exec_tool_call_count"]
        + normalized["child_apply_patch_tool_call_count"]
        + normalized["child_shell_command_tool_call_count"]
        + normalized["child_other_tool_call_count"]
        == total
        and normalized["child_completed_tool_call_count"]
        + normalized["child_failed_tool_call_count"]
        + normalized["child_unknown_tool_call_count"]
        == total
        and normalized["child_tool_output_count"] <= total
        and normalized["child_tool_output_missing_count"]
        == total - normalized["child_tool_output_count"]
    ):
        raise ValueError("Codex child tool evidence relationships were invalid")
    return normalized


def encode_codex_child_tool_evidence(value: object) -> str:
    """Encode only the normalized fixed-count projection."""

    return json.dumps(
        normalize_codex_child_tool_evidence(value),
        sort_keys=True,
        separators=(",", ":"),
    )


def decode_stored_codex_child_tool_evidence(
    *,
    schema: object,
    source: object,
    recorded_at: object,
    payload: object,
) -> dict[str, int] | None:
    """Decode one Store projection, rejecting partial or contradictory rows."""

    values = (str(schema or ""), str(source or ""), str(recorded_at or ""), str(payload or ""))
    if not any(values):
        return None
    if (
        values[0] != CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA
        or values[1] != CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE
        or not values[2]
        or not values[3]
    ):
        raise ValueError("stored Codex child tool evidence metadata was invalid")
    try:
        decoded = json.loads(values[3])
    except (TypeError, ValueError) as exc:
        raise ValueError("stored Codex child tool evidence payload was invalid") from exc
    normalized = normalize_codex_child_tool_evidence(decoded)
    if encode_codex_child_tool_evidence(normalized) != values[3]:
        raise ValueError("stored Codex child tool evidence was not canonical")
    return normalized
