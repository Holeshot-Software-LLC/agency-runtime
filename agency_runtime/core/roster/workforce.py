"""Atomic whole-workforce recruitment snapshots."""

from __future__ import annotations

import hashlib
from collections.abc import Container
from contextlib import closing
from dataclasses import dataclass, replace
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.workforce.contract import (
    WorkforceContract,
    parse_workforce_contract,
    workforce_index_fingerprint,
)
from agency_runtime.core.workforce.recruiter_index import (
    project_recruiter_index_record,
    recruiter_index_fingerprint,
    serialize_recruiter_index,
)


@dataclass(frozen=True, slots=True)
class WorkforceIndexSnapshot:
    """One complete, version-bound input for inference recruitment."""

    generation: int
    worker_count: int
    contracts: tuple[WorkforceContract, ...]
    contract_fingerprint: str
    recruiter_fingerprint: str
    recruiter_index: str


def _stored_contract(document: object, expected_hash: object) -> WorkforceContract:
    text = str(document or "")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != str(expected_hash or ""):
        raise RuntimeError("stored workforce recruitment contract hash is invalid")
    try:
        value = safe_load_bounded_json(
            text,
            maximum_bytes=256 * 1024,
            maximum_depth=16,
            maximum_nodes=10_000,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeError("stored workforce recruitment contract is invalid") from exc
    try:
        return parse_workforce_contract(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("stored workforce recruitment contract is invalid") from exc


def workforce_index_snapshot(
    store: Any,
    *,
    disabled_agents: Container[str] | None = None,
) -> WorkforceIndexSnapshot:
    """Read every worker, lifecycle overlay, and exact contract atomically."""

    disabled = store.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
    with closing(store._connect()) as conn:
        conn.execute("BEGIN")
        counter = conn.execute(
            "SELECT value FROM store_counters WHERE name = 'roster-generation'"
        ).fetchone()
        if counter is None or isinstance(counter["value"], bool):
            raise RuntimeError("roster generation counter is unavailable")
        total = int(conn.execute("SELECT COUNT(*) FROM agent_workers").fetchone()[0])
        rows = conn.execute(
            "SELECT worker.*, "
            "COALESCE(projection.recruitment_contract, "
            "lineage.recruitment_contract) AS recruitment_contract, "
            "COALESCE(projection.recruitment_contract_hash, "
            "lineage.recruitment_contract_hash) AS recruitment_contract_hash "
            "FROM agent_workers AS worker JOIN agent_version_lineage AS lineage "
            "ON lineage.worker_id = worker.worker_id "
            "AND lineage.agent_version_id = worker.current_agent_version_id "
            "LEFT JOIN agent_recruitment_contract_projections AS projection "
            "ON projection.id = ("
            "SELECT candidate.id FROM agent_recruitment_contract_projections AS candidate "
            "WHERE candidate.worker_id = worker.worker_id "
            "AND candidate.agent_version_id = worker.current_agent_version_id "
            "ORDER BY candidate.projection_sequence DESC LIMIT 1"
            ") "
            "ORDER BY worker.worker_id, worker.agent_slug"
        ).fetchall()
        if len(rows) != total:
            raise RuntimeError("workforce current-version lineage is incomplete")
        contracts: list[WorkforceContract] = []
        for row in rows:
            contract = _stored_contract(
                row["recruitment_contract"],
                row["recruitment_contract_hash"],
            )
            if contract.worker_id != str(row["worker_id"]) or contract.agent_id != str(
                row["agent_slug"]
            ):
                raise RuntimeError("stored workforce contract identity does not match its worker")
            standing = str(row["standing"])
            available = standing == "active" and agent_is_enabled(row["agent_slug"], disabled)
            employment = (
                str(row["employment_class"])
                if available
                else "disabled"
                if standing == "active"
                else standing
            )
            enriched_contract = replace(
                contract,
                display_name=str(row["display_name"]),
                employment=employment,
                version=str(row["current_version"]),
                version_hash=str(row["current_hash"]),
                enabled=available,
            )
            # ADR-0087 / AR-119: apply the enrichment overlay at read time so the
            # live route sees enriched capability_ids/stacks/domains/scope_qualifiers
            # without mutating the durable stored contract. Lazy import avoids a
            # module-load cycle (enrichment reads bundled._resource).
            from agency_runtime.core.roster.enrichment import apply_enrichment_to_contract

            enriched_contract = apply_enrichment_to_contract(enriched_contract)
            contracts.append(enriched_contract)
        conn.commit()
    canonical = tuple(contracts)
    records = tuple(project_recruiter_index_record(item) for item in canonical)
    index = serialize_recruiter_index(records)
    return WorkforceIndexSnapshot(
        generation=int(counter["value"]),
        worker_count=len(canonical),
        contracts=canonical,
        contract_fingerprint=workforce_index_fingerprint(canonical),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=index,
    )


def workforce_snapshot_with_contract(
    snapshot: WorkforceIndexSnapshot,
    contract: WorkforceContract,
) -> WorkforceIndexSnapshot:
    """Project one validated pending hire/amendment without persisting it."""

    replaced = False
    contracts: list[WorkforceContract] = []
    for current in snapshot.contracts:
        if current.agent_id == contract.agent_id:
            contracts.append(contract)
            replaced = True
        else:
            contracts.append(current)
    if not replaced:
        contracts.append(contract)
    canonical = tuple(contracts)
    records = tuple(project_recruiter_index_record(item) for item in canonical)
    return WorkforceIndexSnapshot(
        generation=snapshot.generation + 1,
        worker_count=snapshot.worker_count if replaced else snapshot.worker_count + 1,
        contracts=canonical,
        contract_fingerprint=workforce_index_fingerprint(canonical),
        recruiter_fingerprint=recruiter_index_fingerprint(records),
        recruiter_index=serialize_recruiter_index(records),
    )


__all__ = [
    "WorkforceIndexSnapshot",
    "workforce_index_snapshot",
    "workforce_snapshot_with_contract",
]
