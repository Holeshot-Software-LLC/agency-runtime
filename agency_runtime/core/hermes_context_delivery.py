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
        "Selection is not loading. Subsequent native hook callbacks deliver each "
        "full card and then the current header snapshot, before the model runs. "
        "Use those delivered cards. If a card remains pending, the local "
        "agency_load_specialist tool can retrieve its exact slug below; native "
        "correlation binds retrieval to this active turn. Do not choose, substitute, "
        "or read files to obtain cards. Report only actual loads.",
    ]
    lines.extend(json.dumps({"slug": row["slug"]}, separators=(",", ":")) for row in references)
    return "\n".join(lines)
