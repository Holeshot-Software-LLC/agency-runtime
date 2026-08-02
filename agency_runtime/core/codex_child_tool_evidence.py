"""Fixed, content-free Codex child tool evidence shared by rollout and Store paths."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_SCHEMA = "agency.codex-product-child-tool-evidence.v1"
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA = "agency.codex-product-child-tool-evidence.v2"
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE = "persisted_rollout"
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_COUNT = 5_000
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_EXEC_INPUT_CHARS = 1_000_000
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_FIELDS = (
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
CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS = (
    *CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_FIELDS,
    "child_exec_input_classified_count",
    "child_exec_input_unclassified_count",
    "child_exec_nested_tool_call_count",
    "child_exec_nested_apply_patch_tool_call_count",
    "child_exec_nested_shell_command_tool_call_count",
    "child_exec_nested_other_tool_call_count",
    "child_exec_wrapper_completed_count",
    "child_exec_wrapper_failed_count",
    "child_exec_wrapper_yielded_count",
    "child_exec_wrapper_unknown_count",
)

_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_EXEC_NESTED_COUNT_FIELDS = {
    "apply_patch": "child_exec_nested_apply_patch_tool_call_count",
    "shell_command": "child_exec_nested_shell_command_tool_call_count",
}


def _skip_quoted(source: str, index: int, quote: str) -> int | None:
    """Skip one quoted JavaScript literal without interpreting its content."""

    index += 1
    while index < len(source):
        current = source[index]
        if current == "\\":
            index += 2
            continue
        if current == quote:
            return index + 1
        if quote == "`" and current == "$" and index + 1 < len(source) and source[index + 1] == "{":
            return None
        index += 1
    return None


def _content_free_javascript_tokens(source: str) -> list[str] | None:
    """Return only identifiers and relevant punctuation from an unambiguous script."""

    tokens: list[str] = []
    index = 0
    while index < len(source):
        current = source[index]
        if current.isspace():
            index += 1
            continue
        if current in {"'", '"', "`"}:
            skipped = _skip_quoted(source, index, current)
            if skipped is None:
                return None
            index = skipped
            continue
        if current == "/" and index + 1 < len(source):
            following = source[index + 1]
            if following == "/":
                newline = source.find("\n", index + 2)
                index = len(source) if newline < 0 else newline + 1
                continue
            if following == "*":
                end = source.find("*/", index + 2)
                if end < 0:
                    return None
                index = end + 2
                continue
            return None
        match = _IDENTIFIER.match(source, index)
        if match is not None:
            tokens.append(match.group(0))
            index = match.end()
            continue
        if current in {".", "("}:
            tokens.append(current)
        index += 1
    return tokens


def classify_codex_exec_nested_tools(value: object) -> dict[str, int] | None:
    """Classify direct ``tools.<name>(`` calls without retaining JavaScript input."""

    if (
        not isinstance(value, str)
        or not value
        or len(value) > CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_EXEC_INPUT_CHARS
    ):
        return None
    tokens = _content_free_javascript_tokens(value)
    if tokens is None:
        return None
    counts = {
        "child_exec_nested_tool_call_count": 0,
        "child_exec_nested_apply_patch_tool_call_count": 0,
        "child_exec_nested_shell_command_tool_call_count": 0,
        "child_exec_nested_other_tool_call_count": 0,
    }
    for index in range(max(0, len(tokens) - 3)):
        if not (
            tokens[index] == "tools"
            and tokens[index + 1] == "."
            and _IDENTIFIER.fullmatch(tokens[index + 2])
            and tokens[index + 3] == "("
        ):
            continue
        counts["child_exec_nested_tool_call_count"] += 1
        field = _EXEC_NESTED_COUNT_FIELDS.get(
            tokens[index + 2],
            "child_exec_nested_other_tool_call_count",
        )
        counts[field] += 1
        if counts["child_exec_nested_tool_call_count"] > (
            CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_MAX_COUNT
        ):
            return None
    return counts


def classify_codex_exec_wrapper_output(value: object) -> str:
    """Classify only the fixed first-line wrapper envelope from one exec output."""

    text = value if isinstance(value, str) else None
    if isinstance(value, list) and value:
        first = value[0]
        if (
            isinstance(first, Mapping)
            and first.get("type") == "input_text"
            and isinstance(first.get("text"), str)
        ):
            text = first["text"]
    if not isinstance(text, str):
        return "unknown"
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if first_line == "Script completed":
        return "completed"
    if first_line == "Script failed":
        return "failed"
    if first_line.startswith("Script running with cell ID "):
        return "yielded"
    return "unknown"


def _normalize_codex_child_tool_evidence(
    value: object,
    *,
    fields: tuple[str, ...],
) -> dict[str, int]:
    """Return one bounded exact projection or reject malformed evidence."""

    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise ValueError("Codex child tool evidence fields were invalid")
    normalized: dict[str, int] = {}
    for field in fields:
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
    if fields == CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS:
        exec_total = normalized["child_exec_tool_call_count"]
        nested_total = normalized["child_exec_nested_tool_call_count"]
        if not (
            normalized["child_exec_input_classified_count"]
            + normalized["child_exec_input_unclassified_count"]
            == exec_total
            and normalized["child_exec_nested_apply_patch_tool_call_count"]
            + normalized["child_exec_nested_shell_command_tool_call_count"]
            + normalized["child_exec_nested_other_tool_call_count"]
            == nested_total
            and normalized["child_exec_wrapper_completed_count"]
            + normalized["child_exec_wrapper_failed_count"]
            + normalized["child_exec_wrapper_yielded_count"]
            + normalized["child_exec_wrapper_unknown_count"]
            == exec_total
        ):
            raise ValueError("Codex nested exec evidence relationships were invalid")
    return normalized


def normalize_codex_child_tool_evidence(value: object) -> dict[str, int]:
    """Return one current bounded exact projection or reject malformed evidence."""

    return _normalize_codex_child_tool_evidence(
        value,
        fields=CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS,
    )


def _encode_normalized_codex_child_tool_evidence(value: Mapping[str, int]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"))


def encode_codex_child_tool_evidence(value: object) -> str:
    """Encode only the normalized fixed-count projection."""

    return _encode_normalized_codex_child_tool_evidence(normalize_codex_child_tool_evidence(value))


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
    schema_fields = {
        CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_SCHEMA: (CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_V1_FIELDS),
        CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA: CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS,
    }
    fields = schema_fields.get(values[0])
    if (
        fields is None
        or values[1] != CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SOURCE
        or not values[2]
        or not values[3]
    ):
        raise ValueError("stored Codex child tool evidence metadata was invalid")
    try:
        decoded = json.loads(values[3])
    except (TypeError, ValueError) as exc:
        raise ValueError("stored Codex child tool evidence payload was invalid") from exc
    normalized = _normalize_codex_child_tool_evidence(decoded, fields=fields)
    if _encode_normalized_codex_child_tool_evidence(normalized) != values[3]:
        raise ValueError("stored Codex child tool evidence was not canonical")
    return normalized
