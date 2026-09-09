"""Bound selected-card delivery below Hermes native hook and tool spill floors."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

HERMES_INLINE_CONTEXT_CHARS = 6_000
HERMES_RETRIEVAL_CONTEXT_CHARS = 7_000
HERMES_NATIVE_HOOK_CHARS = 10_000
HERMES_CARD_RESULT_CHARS = 7_000


def hermes_context_enabled(recipe: Mapping[str, Any]) -> bool:
    value = recipe.get("specialist_context_via_hermes_tool", False)
    if not isinstance(value, bool) or (
        value and (recipe.get("host") != "hermes" or recipe.get("recipe_version", 0) < 17)
    ):
        raise ValueError("invalid Hermes specialist context delivery surface")
    return value


def selected_card_requests(references: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "[AGENCY SELECTED SPECIALIST CONTEXT]",
        "This turn's workforce inference selected the following immutable cards. "
        "Selection is not loading. Before doing the task, retrieve each card with "
        "the local agency_load_specialist tool using only its exact slug below. "
        "If needed, discover it once with tool_search query=agency_load_specialist "
        "or call tool_call name=agency_load_specialist. Native correlation binds "
        "the tool to this active turn. Use every returned full card; do not choose, "
        "substitute, or read files to obtain cards. Report only actual loads.",
    ]
    lines.extend(json.dumps({"slug": row["slug"]}, separators=(",", ":")) for row in references)
    return "\n".join(lines)
