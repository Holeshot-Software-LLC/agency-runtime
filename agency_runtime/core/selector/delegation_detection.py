"""Deterministically identify independent work that is worth delegating."""

from __future__ import annotations

import re
from typing import Any

from agency_runtime.core.selector.intent_text import mask_excluded_intent

_LIST_ITEM_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>(?:\d+[.)]|[-*+•]|[a-zA-Z][.)]))[ \t]+(?P<body>.+?)\s*$",
    re.MULTILINE,
)

_PARALLEL_BOUNDARY_RE = re.compile(
    r"\b(?:also|additionally|separately|meanwhile|in\s+parallel|"
    r"one\s+more\s+thing|another\s+thing|as\s+well)\b[,:;]?",
    re.IGNORECASE,
)

_DEPENDENCY_RE = re.compile(
    r"\b(?:after(?:wards|\s+that)?|before|once|then|depends?\s+on)\b",
    re.IGNORECASE,
)

_FORWARD_SEQUENCE_SUFFIX_RE = re.compile(
    r"\b(?:then|after\s+that|afterwards)\b[\s,:;-]*$",
    re.IGNORECASE,
)

_CHOICE_RE = re.compile(
    r"\b(?:choose|pick|select)\s+(?:only\s+)?one\b|"
    r"\bwhich\s+(?:option|approach|database|provider)\b",
    re.IGNORECASE,
)

_IMPERATIVE_RE = re.compile(
    r"\b(?:add|analy[sz]e|audit|benchmark|build|change|check|configure|create|"
    r"debug|delete|deploy|document|evaluate|fix|implement|inspect|install|"
    r"measure|merge|migrate|move|optimi[sz]e|profile|refactor|remove|rename|"
    r"review|run|set\s+up|split|test|update|validate|verify|write)\b",
    re.IGNORECASE,
)

# Both slash conventions are recognized regardless of the current host OS.
_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/](?:[^\\/\s:*?\"<>|]+[\\/])*[^\\/\s:*?\"<>|]+)"
    r"|(?:~?[\\/](?:[\w.-]+[\\/])+[\w.-]+)",
)

_PROJECT_REF_RE = re.compile(
    r"\b(?:repo|repository|project|workspace|directory|folder)\s+[\w.-]+",
    re.IGNORECASE,
)

_STATUS_REPORT_PATTERNS = re.compile(
    r"(?:what'?s\s+next|\bstatus\b|\breport\b|"
    r"give\s+me\s+(?:a\s+|an\s+)?(?:summary|update|status)|"
    r"how'?s\s+it\s+going|where\s+are\s+we|what.?s\s+left|\btodo\b)",
    re.IGNORECASE,
)


def _unit(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" \t\r\n,;:-")[:160]


def _without_status_language(text: str) -> str:
    # Preserve offsets so imperative spans can safely slice the original text.
    return _STATUS_REPORT_PATTERNS.sub(lambda match: " " * len(match.group(0)), text)


def _is_actionable(text: str) -> bool:
    """Choices and status labels are not work merely because they are listed."""
    affirmative = mask_excluded_intent(text)
    if not _IMPERATIVE_RE.search(affirmative):
        return False
    return bool(_IMPERATIVE_RE.search(_without_status_language(affirmative)))


def _list_units(message: str) -> list[str]:
    entries: list[tuple[int, str, bool]] = []
    for match in _LIST_ITEM_RE.finditer(message):
        indent_text = match.group("indent").replace("\t", "    ")
        body = match.group("body")
        entries.append((len(indent_text), body, _is_actionable(body)))

    leaves: list[str] = []
    for index, (indent, body, actionable) in enumerate(entries):
        if not actionable:
            continue
        has_actionable_child = False
        for child_indent, _child_body, child_actionable in entries[index + 1 :]:
            if child_indent <= indent:
                break
            if child_actionable:
                has_actionable_child = True
                break
        if not has_actionable_child:
            leaves.append(_unit(body))
    return leaves


def _imperative_units(message: str) -> list[str]:
    signal_text = _without_status_language(mask_excluded_intent(message))
    matches = list(_IMPERATIVE_RE.finditer(signal_text))
    if not matches:
        return []
    starts = [match.start() for match in matches]
    ends = [*starts[1:], len(message)]
    for index in range(1, len(matches)):
        previous_start = starts[index - 1]
        separator = _FORWARD_SEQUENCE_SUFFIX_RE.search(message[previous_start : starts[index]])
        if separator is not None:
            boundary = previous_start + separator.start()
            ends[index - 1] = boundary
            starts[index] = boundary

    units: list[str] = []
    seen: set[str] = set()
    for start, end in zip(starts, ends, strict=True):
        value = _unit(message[start:end])
        key = value[:48].lower()
        if value and key not in seen:
            seen.add(key)
            units.append(value)
    return units


def _result(
    units: list[str],
    *,
    source: str,
    confidence: str = "high",
    delegate: bool,
) -> dict[str, Any]:
    return {
        "count": max(1, len(units)),
        "confidence": confidence,
        "source": source,
        "units": units or [""],
        "delegate": delegate,
    }


def detect_work_units(message: str) -> dict[str, Any]:
    """Detect independent work units without treating options as tasks.

    The detector deliberately favors precision over recall: sequential steps
    are work units, but are not advertised as parallel delegation opportunities.
    """
    msg = message.strip()
    fallback = [_unit(msg)] if msg else [""]

    list_units = _list_units(msg)
    if _LIST_ITEM_RE.search(msg) and _CHOICE_RE.search(msg):
        return _result(fallback, source="choice_list", delegate=False)
    if len(list_units) >= 2:
        # Explicit dependency language means the items may be sequential.  Keep
        # their decomposition visible while avoiding a parallel-work nudge.
        independent = not bool(_DEPENDENCY_RE.search(msg))
        return _result(
            list_units,
            source="numbered_list",
            confidence="high" if independent else "medium",
            delegate=independent,
        )

    # Split only on boundaries that communicate parallel or unrelated work.
    segments = [
        _unit(segment) for segment in _PARALLEL_BOUNDARY_RE.split(msg) if _is_actionable(segment)
    ]
    if len(segments) >= 2:
        return _result(segments, source="boundary_words", delegate=True)

    status_without_work = bool(_STATUS_REPORT_PATTERNS.search(msg)) and not _is_actionable(msg)
    if status_without_work:
        return _result(fallback, source="status_query", delegate=False)

    imperative_units = _imperative_units(msg)
    if len(imperative_units) >= 2 and _DEPENDENCY_RE.search(msg):
        return _result(
            imperative_units,
            source="sequential_steps",
            confidence="high",
            delegate=False,
        )

    paths = _PATH_RE.findall(msg)
    project_refs = _PROJECT_REF_RE.findall(msg)
    if len(imperative_units) >= 2 and (len(paths) >= 2 or len(project_refs) >= 2):
        return _result(
            imperative_units,
            source="imperatives_and_paths",
            confidence="medium",
            delegate=True,
        )

    if len(imperative_units) >= 3:
        return _result(
            imperative_units,
            source="multiple_imperatives",
            confidence="medium",
            delegate=True,
        )

    return _result(fallback, source="single", delegate=False)
