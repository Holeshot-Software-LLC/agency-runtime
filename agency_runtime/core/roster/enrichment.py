"""Bounded enrichment overlay for bundled workforce contracts.

ADR-0087 / AR-119: the deterministic verifier scores typed coverage from
contract fields (``domains``, ``stacks``). Many bundled specialists declare
neither, relying on division/domain fallbacks that leave stack coverage empty
even when the specialist clearly owns a stack (e.g. ``senior-developer`` owns
FluxUI/Livewire through its prose but has ``stacks = ()``). Enrichment fills
those typed gaps so deterministic validation can score coverage positively
instead of leaning entirely on the model's semantic read.

The overlay is a separately versioned, auditable JSON file shipped as package
data (``roster/data/scope_qualifiers.json``): ``{ "<slug>": { "scope_qualifiers":
[...], "stacks": [...], "domains": [...] } }``. It is merged into each agent
dict in :func:`bundled_roster` *before* ``project_workforce_contract`` runs.
The governed prompt manifest is never modified; enrichment stays a clean,
removable layer.

Model output is never trusted blindly: the overlay is constrained to the same
identifier vocabulary the contract projector already enforces, and any field
that fails validation is dropped (never raised) so a bad enrichment row cannot
block roster load.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.bundled import BundledRosterError, _resource

_OVERLAY_RELATIVE_PATH = "scope_qualifiers.json"
_OVERLAY_BYTE_LIMIT = 1_048_576  # 1 MiB: a full 263-agent overlay is well under this.
_TOKEN = __import__("re").compile(r"[a-z0-9][a-z0-9._+-]{0,63}\Z")


def _valid_identifier(value: object) -> bool:
    return isinstance(value, str) and bool(_TOKEN.fullmatch(value.casefold()))


def _bounded_phrases(values: Any, *, maximum: int, minimum_length: int) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        if (
            not isinstance(item, str)
            or len(item) < minimum_length
            or len(item) > 120
            or item in seen
        ):
            continue
        seen.add(item)
        result.append(item.strip())
        if len(result) >= maximum:
            break
    return result


def _identifiers(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not _valid_identifier(item):
            continue
        normalized = item.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


@lru_cache(maxsize=1)
def enrichment_overlay() -> dict[str, dict[str, list[str]]]:
    """Return the validated slug -> enrichment overlay, or {} when absent.

    A missing file is the normal state before the first batch enrichment run;
    it is not an error. Malformed JSON or schema violations raise
    ``BundledRosterError`` because a corrupt shipped overlay is a packaging
    defect, not a runtime grace case.
    """

    try:
        data = _resource(
            _OVERLAY_RELATIVE_PATH, limit=_OVERLAY_BYTE_LIMIT, label="enrichment overlay"
        )
    except BundledRosterError:
        return {}
    try:
        parsed = safe_load_bounded_json(
            data,
            maximum_bytes=_OVERLAY_BYTE_LIMIT,
            maximum_depth=8,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError) as exc:
        raise BundledRosterError("enrichment overlay is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise BundledRosterError("enrichment overlay must be a slug-keyed object")
    overlay: dict[str, dict[str, list[str]]] = {}
    for slug, entry in parsed.items():
        if not isinstance(slug, str) or not isinstance(entry, dict):
            continue
        row = {
            "scope_qualifiers": _bounded_phrases(
                entry.get("scope_qualifiers"), maximum=4, minimum_length=3
            ),
            "stacks": _identifiers(entry.get("stacks")),
            "domains": _identifiers(entry.get("domains")),
            # task_types feeds capability_ids in project_workforce_contract; it
            # must be governed ontology identifiers so enriched capabilities are
            # valid CORE_CAPABILITY_IDS (e.g. threat-modeling for security specs).
            "task_types": _identifiers(entry.get("task_types")),
        }
        if any(row.values()):
            overlay[slug] = row
    return overlay


def apply_enrichment(agent: dict[str, Any]) -> dict[str, Any]:
    """Return ``agent`` with its enrichment overlay merged in (non-destructive).

    Enrichment only supplements; it never overrides a value the roster already
    declares, so an upstream update to a specialist's typed metadata always
    wins over a stale overlay entry. Empty overlay values are skipped.
    """

    overlay = enrichment_overlay()
    row = overlay.get(str(agent.get("slug", "")))
    if not row:
        return agent
    for field, values in row.items():
        if not values:
            continue
        # Supplement only: keep existing declared values ahead of the overlay.
        existing = agent.get(field)
        combined: list[str] = list(existing) if isinstance(existing, list) else []
        for item in values:
            if item not in combined:
                combined.append(item)
        agent[field] = combined
    return agent


def apply_enrichment_to_contract(contract: Any) -> Any:
    """Return an enriched copy of a WorkforceContract (read-time overlay).

    The durable stored workforce contract is immutable; enrichment is applied at
    read time (in workforce_index_snapshot) so the live route sees enriched
    capability_ids/stacks/domains/scope_qualifiers without mutating the stored
    version. Enrichment only supplements existing declared values. ``contract``
    is a frozen dataclass; use ``dataclasses.replace`` to produce the overlay.
    """

    from dataclasses import replace

    overlay = enrichment_overlay()
    row = overlay.get(str(getattr(contract, "agent_id", "")))
    if not row:
        return contract
    updates: dict[str, Any] = {}
    for field, attr in (
        ("stacks", "stacks"),
        ("domains", "domains"),
        ("scope_qualifiers", "scope_qualifiers"),
        ("task_types", "capability_ids"),
    ):
        values = row.get(field)
        if not values:
            continue
        existing = tuple(getattr(contract, attr, ()))
        combined = tuple(dict.fromkeys((*existing, *values)))
        if combined != existing:
            updates[attr] = combined
    return replace(contract, **updates) if updates else contract
