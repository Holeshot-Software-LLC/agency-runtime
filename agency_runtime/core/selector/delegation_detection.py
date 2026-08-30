"""Deterministically identify independent work that is worth delegating."""

from __future__ import annotations

import re
from itertools import islice
from typing import Any

from agency_runtime.core.selector.intent_text import mask_excluded_intent
from agency_runtime.core.unit_assignment import (
    MAX_SUGGESTED_WORK_UNITS,
    MAX_WORK_UNIT_CHARS,
    MAX_WORK_UNIT_PREVIEW_CHARS,
    MAX_WORK_UNIT_TRANSPORT_CHARS,
)

MAX_WORK_UNIT_INPUT_CHARS = MAX_WORK_UNIT_TRANSPORT_CHARS
MAX_WORK_UNIT_CANDIDATES = 64
WORK_UNIT_DETECTION_VERSION = 3

_LIST_ITEM_RE = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>(?:\d{1,3}(?:[.)])?|[-*+•]|[a-zA-Z][.)]))"
    r"[ \t]+(?P<body>.+?)\s*$",
    re.MULTILINE,
)

_PARALLEL_BOUNDARY_RE = re.compile(
    r"\b(?:also|additionally|separately|meanwhile|in\s+parallel|"
    r"one\s+more\s+thing|another\s+thing|as\s+well)\b[,:;]?",
    re.IGNORECASE,
)

_CROSS_UNIT_DEPENDENCY_RE = re.compile(
    r"^\s*(?:after(?:wards|\s+that)?|before|once|then|depends?\s+on)\b|"
    r"\b(?:after|before|depends?\s+on)\s+(?:task|step|item)\s+\d+\b",
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
    r"debug|delete|deploy|design|document|evaluate|fix|implement|inspect|install|"
    r"enhance|harden|improve|measure|merge|migrate|move|optimi[sz]e|profile|"
    r"redesign|refactor|remove|rename|review|run|secure|set\s+up|split|test|"
    r"update|validate|verify|write)\b",
    re.IGNORECASE,
)

_FOLLOWING_IMPERATIVE_BOUNDARY_RE = re.compile(
    r"(?:[,;.!?]\s*|\b(?:and|then|also|additionally|separately|meanwhile)\s+)$",
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
    return re.sub(r"\s+", " ", text).strip(" \t\r\n,;:-")[:MAX_WORK_UNIT_CHARS]


def _preview(text: str) -> str:
    return text[:MAX_WORK_UNIT_PREVIEW_CHARS]


def _collapse_exact_duplicate_unit(text: str) -> str:
    """Collapse an accidentally repeated unit without reopening noun splitting."""

    words = text.split()
    midpoint, remainder = divmod(len(words), 2)
    if remainder or midpoint < 2:
        return text
    first = words[:midpoint]
    second = words[midpoint:]
    if [word.casefold() for word in first] != [word.casefold() for word in second]:
        return text
    return " ".join(first)


def _without_status_language(text: str) -> str:
    # Preserve offsets so imperative spans can safely slice the original text.
    return _STATUS_REPORT_PATTERNS.sub(lambda match: " " * len(match.group(0)), text)


def _is_actionable(text: str) -> bool:
    """Choices and status labels are not work merely because they are listed."""
    affirmative = mask_excluded_intent(text)
    if not _IMPERATIVE_RE.search(affirmative):
        return False
    return bool(_IMPERATIVE_RE.search(_without_status_language(affirmative)))


def _cross_unit_dependency_flags(units: list[str]) -> list[bool]:
    """Return explicit dependency flags without leaking one clause across a message.

    Dependency words inside the first unit describe that unit only. A later
    unit is considered cross-unit dependent when it starts with sequencing
    language or explicitly names a numbered task, step, or item.
    """

    return [
        bool(index and _CROSS_UNIT_DEPENDENCY_RE.search(unit)) for index, unit in enumerate(units)
    ]


def _all_followups_are_dependent(units: list[str]) -> bool:
    flags = _cross_unit_dependency_flags(units)
    return len(flags) >= 2 and all(flags[1:])


def _list_unit_candidates(message: str) -> tuple[list[str], bool]:
    entries: list[tuple[int, str, bool]] = []
    matches = list(islice(_LIST_ITEM_RE.finditer(message), MAX_WORK_UNIT_CANDIDATES + 1))
    scan_truncated = len(matches) > MAX_WORK_UNIT_CANDIDATES
    for match in matches[:MAX_WORK_UNIT_CANDIDATES]:
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
    return leaves, scan_truncated


def _list_units(message: str) -> list[str]:
    """Compatibility projection of the bounded list candidates."""

    units, _scan_truncated = _list_unit_candidates(message)
    return units[:MAX_SUGGESTED_WORK_UNITS]


def _imperative_unit_candidates(message: str) -> tuple[list[str], bool]:
    signal_text = _without_status_language(mask_excluded_intent(message))
    candidates = list(islice(_IMPERATIVE_RE.finditer(signal_text), MAX_WORK_UNIT_CANDIDATES + 1))
    scan_truncated = len(candidates) > MAX_WORK_UNIT_CANDIDATES
    matches = []
    for match in candidates[:MAX_WORK_UNIT_CANDIDATES]:
        # Words such as ``design`` and ``review`` can be nouns inside the first
        # work unit (for example, "review the authentication design").  Only
        # treat a later verb-shaped token as a new imperative when clause
        # punctuation or an explicit conjunction introduces it.  The first
        # match remains intentionally permissive so polite prefixes such as
        # "please" and "can you" do not hide the actual request.
        if matches and not _FOLLOWING_IMPERATIVE_BOUNDARY_RE.search(signal_text[: match.start()]):
            continue
        matches.append(match)
    if not matches:
        return [], scan_truncated
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
        value = _collapse_exact_duplicate_unit(_unit(message[start:end]))
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            units.append(value)
    return units, scan_truncated


def _imperative_units(message: str) -> list[str]:
    """Compatibility projection of the bounded imperative candidates."""

    units, _scan_truncated = _imperative_unit_candidates(message)
    return units[:MAX_SUGGESTED_WORK_UNITS]


def _result(
    units: list[str],
    *,
    source: str,
    confidence: str = "high",
    delegate: bool,
    scan_truncated: bool = False,
) -> dict[str, Any]:
    normalized_units: list[str] = []
    seen: set[str] = set()
    for unit in units[:MAX_WORK_UNIT_CANDIDATES]:
        value = _unit(unit)
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        normalized_units.append(value)
    overflow = scan_truncated or len(normalized_units) > MAX_SUGGESTED_WORK_UNITS
    bounded_units = normalized_units[:MAX_SUGGESTED_WORK_UNITS]
    overflow_count = max(0, len(normalized_units) - len(bounded_units))
    if scan_truncated:
        overflow_count = max(1, overflow_count)
    result_source = f"{source}_overflow" if overflow else source
    return {
        "version": WORK_UNIT_DETECTION_VERSION,
        "count": max(1, len(bounded_units)),
        "confidence": "low" if overflow else confidence,
        "source": result_source,
        "units": bounded_units or [""],
        "previews": [_preview(unit) for unit in bounded_units] or [""],
        "preview_truncated": [len(unit) > MAX_WORK_UNIT_PREVIEW_CHARS for unit in bounded_units]
        or [False],
        "truncated": overflow,
        "overflow_count": overflow_count,
        "overflow_count_exact": not scan_truncated,
        "abstention_reason": "work_unit_limit_exceeded" if overflow else "",
        "delegate": bool(not overflow and delegate and len(bounded_units) >= 2),
    }


def detect_work_units(message: str) -> dict[str, Any]:
    """Detect independent work units without treating options as tasks.

    The detector deliberately favors precision over recall: sequential steps
    are work units, but are not advertised as parallel delegation opportunities.
    """
    msg = str(message or "")[:MAX_WORK_UNIT_INPUT_CHARS].strip()
    fallback = [_unit(msg)] if msg else [""]

    list_units, list_scan_truncated = _list_unit_candidates(msg)
    if _LIST_ITEM_RE.search(msg) and _CHOICE_RE.search(msg):
        return _result(fallback, source="choice_list", delegate=False)
    if len(list_units) >= 2 or list_scan_truncated:
        # Scope dependency evidence to the unit that carries it. A phrase such
        # as "back up before migrating" inside the first item does not describe
        # a cross-unit edge. Once any follow-up carries a sequencing marker,
        # however, the current unit plan cannot faithfully encode the mixed
        # dependency graph, so fail closed instead of advertising every item as
        # safe to run in parallel.
        dependency_flags = _cross_unit_dependency_flags(list_units)
        return _result(
            list_units,
            source="numbered_list",
            confidence="medium" if any(dependency_flags) else "high",
            delegate=not any(dependency_flags),
            scan_truncated=list_scan_truncated,
        )

    # Split only on boundaries that communicate parallel or unrelated work.
    raw_segments = _PARALLEL_BOUNDARY_RE.split(msg)
    segment_scan_truncated = len(raw_segments) > MAX_WORK_UNIT_CANDIDATES
    segments = [
        _unit(segment)
        for segment in raw_segments[:MAX_WORK_UNIT_CANDIDATES]
        if _is_actionable(segment)
    ]
    if len(segments) >= 2 or segment_scan_truncated:
        return _result(
            segments,
            source="boundary_words",
            delegate=True,
            scan_truncated=segment_scan_truncated,
        )

    status_without_work = bool(_STATUS_REPORT_PATTERNS.search(msg)) and not _is_actionable(msg)
    if status_without_work:
        return _result(fallback, source="status_query", delegate=False)

    imperative_units, imperative_scan_truncated = _imperative_unit_candidates(msg)
    if _all_followups_are_dependent(imperative_units):
        return _result(
            imperative_units,
            source="sequential_steps",
            confidence="high",
            delegate=False,
            scan_truncated=imperative_scan_truncated,
        )

    path_count = sum(1 for _ in islice(_PATH_RE.finditer(msg), 2))
    project_ref_count = sum(1 for _ in islice(_PROJECT_REF_RE.finditer(msg), 2))
    if len(imperative_units) >= 2 and (path_count >= 2 or project_ref_count >= 2):
        return _result(
            imperative_units,
            source="imperatives_and_paths",
            confidence="medium",
            delegate=True,
            scan_truncated=imperative_scan_truncated,
        )

    if len(imperative_units) >= 3 or imperative_scan_truncated:
        return _result(
            imperative_units,
            source="multiple_imperatives",
            confidence="medium",
            delegate=True,
            scan_truncated=imperative_scan_truncated,
        )

    return _result(fallback, source="single", delegate=False)
