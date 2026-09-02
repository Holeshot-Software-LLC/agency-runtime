"""Shared allow-list semantics for the tracker-parity and done-flip gates.

`verify_docs.py --require-tracker` and `verify_tracker.py` must agree on which
roadmap IDs are exempt as pre-tracker history and on when an exemption is
invalid (AR-347). `verify_docs.py` also needs the frozen set of issues that
were already done before AR-361 required builder-evidence records and
isolated single-check verdicts for done flips. Keeping the parsers and the
entry rules here removes the drift channel between the gates.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
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
PRE_VERIFICATION_FILENAME = "pre-verification-history.txt"
# AR-361 made every done flip require a docs/roadmap/acceptance/ record with
# builder evidence and isolated single-check verdicts. The issues that were
# already done or wont_do when that gate landed are grandfathered by exact ID.
# AR-346 was the newest of them, so no later ID can ever be exempted, and the
# frozen set is pinned by digest: the list can only shrink, and only through a
# visible change to this constant alongside the file.
PRE_VERIFICATION_MAX_ID = 346
PRE_VERIFICATION_HISTORY_SHA256 = "96ce27f14516251c3f9c0b52440ccfdaeec0e2266ac88ce22be88b6f59205697"
GRANDFATHERED_ISSUE_STATUSES = frozenset({"done", "wont_do"})
_ENTRY_RE = re.compile(r"^AR-(\d{2,})$")


def _allow_list_entries(path: Path) -> set[str]:
    """Return the non-comment entries of one allow-list file (empty if absent)."""

    if not path.is_file():
        return set()
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#"):
            entries.add(entry)
    return entries


def load_pre_tracker_history(roadmap_dir: Path) -> set[str]:
    """Return roadmap IDs exempt from tracker requirements (AR-347)."""

    return _allow_list_entries(roadmap_dir / PRE_TRACKER_FILENAME)


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


def load_pre_verification_history(roadmap_dir: Path) -> set[str]:
    """Return roadmap IDs whose done status predates AR-361 verification."""

    return _allow_list_entries(roadmap_dir / PRE_VERIFICATION_FILENAME)


def verification_history_digest(entries: Iterable[str]) -> str:
    """Digest the entry set independent of file order and comment lines."""

    return hashlib.sha256("\n".join(sorted(entries)).encode("utf-8")).hexdigest()


def pre_verification_entry_errors(
    exemptions: set[str],
    statuses_by_id: Mapping[str, object],
    *,
    expected_digest: str = PRE_VERIFICATION_HISTORY_SHA256,
) -> list[str]:
    """Return the frozen-list violations, one message per entry plus the pin.

    Stale entries (the issue is no longer done or wont_do), orphan entries, and
    out-of-range entries fail the gate, and so does any drift from the pinned
    digest, so the grandfather list cannot be widened without a visible code
    change (AR-361). An ID newer than the newest grandfathered item is out of
    range even when its issue is done: every later done flip needs a record.
    """

    errors: list[str] = []
    for entry in sorted(exemptions):
        match = _ENTRY_RE.fullmatch(entry)
        if match is None or int(match.group(1)) > PRE_VERIFICATION_MAX_ID:
            errors.append(
                f"{PRE_VERIFICATION_FILENAME}: entry {entry} is outside pre-verification "
                f"history (must be AR-01..AR-{PRE_VERIFICATION_MAX_ID})"
            )
        elif entry not in statuses_by_id:
            errors.append(
                f"{PRE_VERIFICATION_FILENAME}: entry {entry} matches no roadmap issue doc"
            )
        elif statuses_by_id.get(entry) not in GRANDFATHERED_ISSUE_STATUSES:
            errors.append(
                f"{PRE_VERIFICATION_FILENAME}: entry {entry} is no longer done or wont_do "
                "and must be removed"
            )
    digest = verification_history_digest(exemptions)
    if digest != expected_digest:
        errors.append(
            f"{PRE_VERIFICATION_FILENAME}: frozen entry set digest is {digest}, expected "
            f"{expected_digest}; the list changes only together with "
            "PRE_VERIFICATION_HISTORY_SHA256"
        )
    return errors
