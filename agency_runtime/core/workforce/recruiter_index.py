"""Terse, deterministic whole-workforce index for inference recruitment."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.workforce.contract import WorkforceContract

RECRUITER_INDEX_SCHEMA_VERSION = "1"
MAX_RECRUITER_INDEX_BYTES = 256 * 1024

# These legends make positional rows self-describing once per complete index,
# instead of repeating long object keys for every worker.
RECRUITER_INDEX_FIELDS = (
    "worker_id",
    "slug",
    "display_name",
    "employment_status",
    "origin",
    "archetype",
    "owned_outcomes",
    "artifact_kinds",
    "lifecycle_phases",
    "domains",
    "stacks",
    "scope_qualifiers",
    "not_for",
    "authority",
    "context_mode",
    "tool_classes",
    "hosts",
    "platforms",
    "composition",
    "audit_status",
    "exact_version",
    "exact_hash",
    "enabled",
)
COMPOSITION_INDEX_FIELDS = (
    "substitution_group",
    "substitutes_for",
    "complements",
    "same_context_conflicts",
    "selection_exclusive",
    "requires",
    "must_follow",
    "must_review_independently",
    "independence_class",
)


@dataclass(frozen=True, slots=True)
class RecruiterIndexRecord:
    """Every tracker-required global-index fact for one worker."""

    worker_id: str
    slug: str
    display_name: str
    employment_status: str
    origin: str
    archetype: str
    owned_outcomes: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    lifecycle_phases: tuple[str, ...]
    domains: tuple[str, ...]
    stacks: tuple[str, ...]
    scope_qualifiers: tuple[str, ...]
    not_for: tuple[str, ...]
    authority: str
    context_mode: str
    tool_classes: tuple[str, ...]
    hosts: tuple[str, ...]
    platforms: tuple[str, ...]
    composition: tuple[Any, ...]
    audit_status: str
    exact_version: str
    exact_hash: str
    enabled: bool

    def to_wire_row(self) -> tuple[Any, ...]:
        """Return a positional row governed by ``RECRUITER_INDEX_FIELDS``."""

        return (
            self.worker_id,
            self.slug,
            self.display_name,
            self.employment_status,
            self.origin,
            self.archetype,
            self.owned_outcomes,
            self.artifact_kinds,
            self.lifecycle_phases,
            self.domains,
            self.stacks,
            self.scope_qualifiers,
            self.not_for,
            self.authority,
            self.context_mode,
            self.tool_classes,
            self.hosts,
            self.platforms,
            self.composition,
            self.audit_status,
            self.exact_version,
            self.exact_hash,
            self.enabled,
        )


def project_recruiter_index_record(contract: WorkforceContract) -> RecruiterIndexRecord:
    """Derive one terse record without weakening its authoritative contract."""

    composition = contract.composition
    return RecruiterIndexRecord(
        worker_id=contract.worker_id,
        slug=contract.agent_id,
        display_name=contract.display_name,
        employment_status=contract.employment,
        origin=contract.origin,
        archetype=contract.archetype,
        owned_outcomes=contract.outcomes,
        artifact_kinds=contract.artifact_kinds,
        lifecycle_phases=contract.lifecycle_phases,
        domains=contract.domains,
        stacks=contract.stacks,
        scope_qualifiers=contract.scope_qualifiers,
        not_for=contract.not_for,
        authority=contract.authority,
        context_mode=contract.context_mode,
        tool_classes=contract.tool_classes,
        hosts=contract.hosts,
        platforms=contract.platforms,
        composition=(
            composition.substitution_group,
            composition.substitutes_for,
            composition.complements,
            composition.same_context_conflicts,
            composition.selection_exclusive,
            composition.requires,
            composition.must_follow,
            composition.must_review_independently,
            composition.independence_class,
        ),
        audit_status=contract.audit.status,
        exact_version=contract.version,
        exact_hash=contract.version_hash,
        enabled=contract.enabled,
    )


def _ordered_records(records: Sequence[RecruiterIndexRecord]) -> list[RecruiterIndexRecord]:
    ordered = sorted(records, key=lambda item: (item.worker_id, item.slug))
    worker_ids = [item.worker_id for item in ordered]
    slugs = [item.slug for item in ordered]
    if len(worker_ids) != len(set(worker_ids)):
        raise ValueError("recruiter index contains duplicate worker ids")
    if len(slugs) != len(set(slugs)):
        raise ValueError("recruiter index contains duplicate slugs")
    if any(len(item.to_wire_row()) != len(RECRUITER_INDEX_FIELDS) for item in ordered):
        raise ValueError("recruiter index row does not match its field legend")
    if any(len(item.composition) != len(COMPOSITION_INDEX_FIELDS) for item in ordered):
        raise ValueError("recruiter composition does not match its field legend")
    return ordered


def serialize_recruiter_index(records: Sequence[RecruiterIndexRecord]) -> str:
    """Serialize a stable, self-describing index for inference and cache keys."""

    ordered = _ordered_records(records)
    payload = json.dumps(
        {
            "schema_version": RECRUITER_INDEX_SCHEMA_VERSION,
            "fields": RECRUITER_INDEX_FIELDS,
            "composition_fields": COMPOSITION_INDEX_FIELDS,
            "workers": [item.to_wire_row() for item in ordered],
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(payload.encode("utf-8")) > MAX_RECRUITER_INDEX_BYTES:
        raise ValueError(f"recruiter index exceeds {MAX_RECRUITER_INDEX_BYTES} bytes")
    return payload


def recruiter_index_fingerprint(records: Sequence[RecruiterIndexRecord]) -> str:
    """Hash the exact stable inference serialization."""

    payload = serialize_recruiter_index(records).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


__all__ = [
    "COMPOSITION_INDEX_FIELDS",
    "MAX_RECRUITER_INDEX_BYTES",
    "RECRUITER_INDEX_FIELDS",
    "RECRUITER_INDEX_SCHEMA_VERSION",
    "RecruiterIndexRecord",
    "project_recruiter_index_record",
    "recruiter_index_fingerprint",
    "serialize_recruiter_index",
]
