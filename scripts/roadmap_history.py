"""Shared pre-tracker allow-list semantics for the two tracker-parity gates.

`verify_docs.py --require-tracker` and `verify_tracker.py` must agree on which
roadmap IDs are exempt as pre-tracker history and on when an exemption is
invalid (AR-347). Keeping the parser and the entry rules here removes the
drift channel between the gates.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

PRE_TRACKER_FILENAME = "pre-tracker-history.txt"
# Tracker discipline (one same-repository tracker per roadmap item) has held
# since AR-331; only strictly older IDs may be exempted as pre-tracker
# history. This bound is what stops a new item from smuggling itself onto the
# allow-list to dodge --require-tracker.
PRE_TRACKER_MAX_ID = 330
# Two historical items are tracked by merged pull requests instead of issues;
# `gh issue list` can never match them. The set is closed: any other doc with
# a pull-request tracker_url is an error, not an exemption.
PR_TRACKED_HISTORY = frozenset({"AR-227", "AR-228"})
_ENTRY_RE = re.compile(r"^AR-(\d{2,})$")


def load_pre_tracker_history(roadmap_dir: Path) -> set[str]:
    """Return roadmap IDs exempt from tracker requirements (AR-347)."""

    path = roadmap_dir / PRE_TRACKER_FILENAME
    if not path.is_file():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            entries.add(entry)
    return entries


def pre_tracker_entry_errors(
    exemptions: set[str],
    known_ids: set[str],
    tracker_urls_by_id: Mapping[str, object],
) -> list[str]:
    """Return the shared allow-list violations, one message per entry.

    Stale entries (the doc now carries a tracker URL), orphan entries (no
    matching roadmap doc), and out-of-range entries (IDs newer than the
    pre-tracker era) must fail both gates so the allow-list can only shrink.
    """

    errors: list[str] = []
    for entry in sorted(exemptions):
        match = _ENTRY_RE.fullmatch(entry)
        if match is None or int(match.group(1)) > PRE_TRACKER_MAX_ID:
            errors.append(
                f"{PRE_TRACKER_FILENAME}: entry {entry} is outside pre-tracker "
                f"history (must be AR-01..AR-{PRE_TRACKER_MAX_ID})"
            )
        elif entry not in known_ids:
            errors.append(f"{PRE_TRACKER_FILENAME}: entry {entry} matches no roadmap issue doc")
        elif tracker_urls_by_id.get(entry):
            errors.append(
                f"{PRE_TRACKER_FILENAME}: entry {entry} now carries a tracker URL "
                "and must be removed"
            )
    return errors
