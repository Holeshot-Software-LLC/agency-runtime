"""Work-unit detection — identifies independent delegatable tasks in a message."""

from __future__ import annotations

import re
from typing import Any

_NUMBERED_ITEM_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+[.\)]\s+|[-*•]\s+)",
    re.MULTILINE,
)

_BOUNDARY_WORDS = frozenset({
    "also", "additionally", "separately", "then",
    "after that", "next,", "secondly", "finally",
    "one more thing", "another thing", "as well",
})

_IMPERATIVE_RE = re.compile(
    r"\b(?:add|fix|update|create|delete|remove|implement|deploy|"
    r"configure|install|write|build|test|debug|refactor|"
    r"change|move|rename|split|merge|migrate|set up|check|review)\b",
    re.IGNORECASE,
)

_PATH_RE = re.compile(r"(?:/[\w.-]+){2,}|~/[\w.-]+|\bread_file\b|\bwrite_file\b")

_PROJECT_REF_RE = re.compile(
    r"(?:repo|repository|project|workspace|directory|folder)\s+\w+",
    re.IGNORECASE,
)

_STATUS_REPORT_PATTERNS = re.compile(
    r"(?:what'?s next|status|report|give me (?:a |an )?(?:summary|update|status)|"
    r"how'?s it going|where are we|what.?s left|todo)",
    re.IGNORECASE,
)


def detect_work_units(message: str) -> dict[str, Any]:
    """Detect independent work units in a user message.

    Returns:
        {
            "count": int,
            "confidence": str,    # "high" | "medium" | "low"
            "source": str,        # "numbered_list" | "boundary_words" | ...
            "units": list[str],
            "delegate": bool,
        }

    Fix from v1: status reports/questions are NOT work units.
    """
    msg = message.strip()

    if _STATUS_REPORT_PATTERNS.search(msg):
        return {
            "count": 1,
            "confidence": "high",
            "source": "status_query",
            "units": [msg[:80]],
            "delegate": False,
        }

    # Signal 1: Numbered/bulleted lists
    numbered_matches = list(_NUMBERED_ITEM_RE.finditer(msg))
    if len(numbered_matches) >= 2:
        units: list[str] = []
        for i, match in enumerate(numbered_matches):
            start = match.end()
            end = numbered_matches[i + 1].start() if i + 1 < len(numbered_matches) else len(msg)
            item = msg[start:end].strip()
            item = item.split("\n")[0][:80]
            if item:
                units.append(item)
        if len(units) >= 2:
            return {
                "count": len(units),
                "confidence": "high",
                "source": "numbered_list",
                "units": units,
                "delegate": True,
            }

    # Signal 2: Boundary words
    msg_lower = msg.lower()
    boundary_positions: list[int] = []
    for bw in _BOUNDARY_WORDS:
        idx = 0
        while True:
            pos = msg_lower.find(bw, idx)
            if pos == -1:
                break
            boundary_positions.append(pos)
            idx = pos + len(bw)

    if len(boundary_positions) >= 1:
        boundary_positions.sort()
        segments: list[str] = []
        prev = 0
        for pos in boundary_positions:
            seg = msg[prev:pos].strip()
            if seg and len(seg) >= 20 and _IMPERATIVE_RE.search(seg):
                segments.append(seg[:80])
            prev = pos
        final_seg = msg[prev:].strip()
        if final_seg and len(final_seg) >= 20 and _IMPERATIVE_RE.search(final_seg):
            segments.append(final_seg[:80])
        if len(segments) >= 2:
            return {
                "count": len(segments),
                "confidence": "high",
                "source": "boundary_words",
                "units": segments,
                "delegate": True,
            }

    # Signal 3: Multiple imperatives with multiple paths
    imperatives = _IMPERATIVE_RE.findall(msg)
    paths = _PATH_RE.findall(msg)
    project_refs = _PROJECT_REF_RE.findall(msg)

    if len(imperatives) >= 2 and (len(paths) >= 2 or len(project_refs) >= 2):
        units: list[str] = []
        for match in _IMPERATIVE_RE.finditer(msg):
            start = match.start()
            unit = msg[start:start + 80].split("\n")[0]
            if unit:
                units.append(unit)
        seen: set[str] = set()
        unique_units = []
        for u in units:
            key = u[:30].lower()
            if key not in seen:
                seen.add(key)
                unique_units.append(u)
        if len(unique_units) >= 2:
            return {
                "count": len(unique_units),
                "confidence": "medium",
                "source": "imperatives_and_paths",
                "units": unique_units,
                "delegate": True,
            }

    # Signal 4: Multiple distinct imperatives
    if len(imperatives) >= 3:
        units: list[str] = []
        for match in _IMPERATIVE_RE.finditer(msg):
            start = match.start()
            unit = msg[start:start + 80].split("\n")[0]
            if unit:
                units.append(unit)
        seen: set[str] = set()
        unique_units = []
        for u in units:
            key = u[:30].lower()
            if key not in seen:
                seen.add(key)
                unique_units.append(u)
        if len(unique_units) >= 3:
            return {
                "count": len(unique_units),
                "confidence": "medium",
                "source": "multiple_imperatives",
                "units": unique_units,
                "delegate": True,
            }

    return {
        "count": 1,
        "confidence": "high",
        "source": "single",
        "units": [msg[:80]],
        "delegate": False,
    }
