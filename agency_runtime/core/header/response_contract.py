"""The one per-turn statement of what Agency's finalizer checks (AR-357).

A turn used to learn its finalization requirements from a stream of
superseding header snapshots, each carrying its own wording, plus a routing
instruction that still described a seven-line header the verifier had stopped
checking. When one snapshot failed to render, the model was told nothing at
all, reused an earlier turn's header, and lost the turn to ``response_invalid``
(measured 2026-09-01 on the claude host, trace ``9ff53c55``).

This module owns the single canonical statement. It is delivered once, at turn
start, next to the INITIAL header snapshot on every host; later snapshots
refresh header *values* only and say so. The text is hash-pinned by
``tests/test_response_contract.py`` so it cannot drift without a deliberate
change, and it states exactly what ``validate_completion_policy`` verifies --
nothing more, nothing less.
"""

from __future__ import annotations

from hashlib import sha256

from agency_runtime.core.header.contract import HEADER_FIELDS

RESPONSE_CONTRACT_MARKER = "[AGENCY RESPONSE CONTRACT v1]"

_HEADER_LABELS = "; ".join(label for _key, label in HEADER_FIELDS)

# Every sentence here is a claim about the verifier. Claim 1 is
# ``_starts_with_header`` and ``validate_header``; claim 2 is the
# ``fill_header_fields`` comparison in ``validate_completion_policy`` (values
# compared after ``str.strip``, one line each, placeholder values rejected by
# ``_is_present``); claim 3 is the ``response_body`` check that only the public
# ``finalize_response`` performs. The closing sentences are the AR-357 Stop-path
# rule: an unreadable turn publishes unverified instead of being rejected.
RESPONSE_CONTRACT_TEXT = (
    f"{RESPONSE_CONTRACT_MARKER}\n"
    "Agency checks only this turn's final response, once, for exactly this:\n"
    f"1. It begins with these {len(HEADER_FIELDS)} lines in this order, each `Label: value`, "
    f"nothing before them: {_HEADER_LABELS}.\n"
    "2. Each value equals the current-turn Store evidence (outer whitespace ignored; one line "
    "each; a placeholder like `<none>` is not a value).\n"
    "3. `agency_finalize` additionally requires a non-empty body after the header.\n"
    "Later snapshots in this turn refresh these values only; use the newest. No snapshot "
    "changes a requirement. If Agency cannot read this turn's evidence, the response "
    "publishes unverified; you are never asked to fix that."
)

RESPONSE_CONTRACT_SHA256 = sha256(RESPONSE_CONTRACT_TEXT.encode("utf-8")).hexdigest()

# Wording every host's refreshed snapshot carries so no snapshot can read as a
# second contract.
SNAPSHOT_VALUES_ONLY_NOTE = (
    "Values only; the contract stated at turn start is unchanged. Use these newest values."
)

_UNAVAILABLE_LINE = (
    "No header snapshot is available for this turn: Agency could not read this turn's "
    "evidence. Do not reuse header values from an earlier turn; use the newest snapshot "
    "delivered later in this turn. If none arrives, Agency checks the header against "
    "whatever evidence it can read at the end of the turn, and if it can read none the "
    "response publishes unverified."
)


def response_contract_context() -> str:
    """Return the canonical contract block delivered once per turn."""

    return RESPONSE_CONTRACT_TEXT


def header_snapshot_unavailable_context(marker: str, *, version: str = "v1") -> str:
    """Return the honest replacement for a snapshot that could not be rendered.

    Silence was the second measured AR-357 failure: a turn whose snapshot did
    not render received nothing, so the model had no way to know this turn's
    values were never shown to it. The line says so instead.
    """

    return f"[AGENCY {marker} HEADER SNAPSHOT {version}]\n{_UNAVAILABLE_LINE}"


__all__ = [
    "RESPONSE_CONTRACT_MARKER",
    "RESPONSE_CONTRACT_SHA256",
    "RESPONSE_CONTRACT_TEXT",
    "SNAPSHOT_VALUES_ONLY_NOTE",
    "header_snapshot_unavailable_context",
    "response_contract_context",
]
