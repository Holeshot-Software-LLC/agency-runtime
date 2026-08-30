"""Delta-only upstream roster inspection and quarantine import."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.roster.bundled import bundled_manifest
from agency_runtime.core.roster.inference import (
    audit_candidates_with_policy,
    resolve_inference_audit_policy,
)
from agency_runtime.core.roster.ingress import (
    MAX_SHORT_TEXT_BYTES,
    ManifestImportOutcome,
    RosterDownload,
    RosterSyncError,
    _require_bounded_text,
    download_from_source,
)
from agency_runtime.core.roster.review import list_candidate_audits
from agency_runtime.core.roster.sync import (
    quarantine_manifest_import,
    reconcile_manifest_remediation_resolutions,
)
from agency_runtime.core.store.sqlite import Store


@dataclass(frozen=True, slots=True)
class UpstreamDelta:
    """One bounded comparison against the packaged audited source baseline."""

    source_revision: str
    agents: tuple[dict[str, Any], ...]
    outcomes: tuple[ManifestImportOutcome, ...]
    entries: tuple[dict[str, str], ...]
    removed: tuple[dict[str, str], ...]

    @property
    def delta_count(self) -> int:
        return sum(
            entry["status"] != "ignored" and entry["change"] in {"new", "changed"}
            for entry in self.entries
        ) + len(self.removed)

    def public_dict(self) -> dict[str, Any]:
        counts = {
            state: sum(
                entry["status"] != "ignored" and entry["change"] == state for entry in self.entries
            )
            for state in ("new", "changed", "unchanged")
        }
        counts["removed"] = len(self.removed)
        counts["quarantined"] = sum(outcome.status == "quarantined" for outcome in self.outcomes)
        return {
            "source_revision": self.source_revision,
            "delta_count": self.delta_count,
            "counts": counts,
            "entries": list(self.entries),
            "removed": list(self.removed),
        }


def _baseline(manifest: Mapping[str, Any] | None) -> tuple[str, dict[str, dict[str, Any]]]:
    resolved = bundled_manifest() if manifest is None else dict(manifest)
    source = resolved.get("source")
    agents = resolved.get("agents")
    if not isinstance(source, Mapping) or not isinstance(agents, list):
        raise RosterSyncError("bundled upstream baseline is invalid")
    revision = _require_bounded_text(
        source.get("revision") or "",
        MAX_SHORT_TEXT_BYTES,
        "bundled source revision",
    )
    by_path: dict[str, dict[str, Any]] = {}
    for item in agents:
        if not isinstance(item, Mapping):
            raise RosterSyncError("bundled upstream baseline agent is invalid")
        relative_path = str(item.get("relative_path") or "")
        source_hash = str(item.get("source_content_hash") or "")
        if not relative_path or len(source_hash) != 64 or relative_path in by_path:
            raise RosterSyncError("bundled upstream baseline identity is invalid")
        by_path[relative_path] = dict(item)
    return revision, by_path


def plan_upstream_delta(
    download: Sequence[dict[str, Any]],
    outcomes: Sequence[ManifestImportOutcome] | None = None,
    *,
    baseline_manifest: Mapping[str, Any] | None = None,
    source_revision: str = "",
) -> UpstreamDelta:
    """Select only new/content-changed definitions while retaining scan evidence."""

    if outcomes is None:
        outcomes = tuple(getattr(download, "outcomes", ()))
    if not outcomes:
        raise RosterSyncError("upstream delta inspection requires manifest outcomes")
    baseline_revision, baseline = _baseline(baseline_manifest)
    declared_revision = _require_bounded_text(
        source_revision or baseline_revision,
        MAX_SHORT_TEXT_BYTES,
        "upstream source revision",
    )
    agents_by_slug = {str(agent.get("slug") or ""): dict(agent) for agent in download}
    if len(agents_by_slug) != len(download):
        raise RosterSyncError("upstream download contains duplicate candidate slugs")

    selected_agents: list[dict[str, Any]] = []
    persisted_outcomes: list[ManifestImportOutcome] = []
    entries: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for outcome in outcomes:
        if not isinstance(outcome, ManifestImportOutcome):
            raise RosterSyncError("upstream outcome has an invalid type")
        if outcome.relative_path in seen_paths:
            raise RosterSyncError("upstream outcomes contain duplicate relative paths")
        seen_paths.add(outcome.relative_path)
        previous = baseline.get(outcome.relative_path)
        if previous is None:
            change = "new"
        elif previous["source_content_hash"] == outcome.content_hash:
            change = "unchanged"
        else:
            change = "changed"
        entries.append(
            {
                "change": change,
                "hash": outcome.content_hash,
                "relative_path": outcome.relative_path,
                "slug": outcome.slug,
                "status": outcome.status,
            }
        )
        if outcome.status == "candidate" and change == "unchanged":
            persisted_outcomes.append(
                ManifestImportOutcome(
                    status="ignored",
                    origin=outcome.origin,
                    relative_path=outcome.relative_path,
                    slug=outcome.slug,
                    content_hash=outcome.content_hash,
                    finding="unchanged_bundled_revision",
                )
            )
            continue
        persisted_outcomes.append(outcome)
        if outcome.status == "candidate":
            agent = agents_by_slug.get(outcome.slug)
            if agent is None:
                raise RosterSyncError("upstream candidate outcome has no parsed agent")
            agent["source_version"] = declared_revision
            selected_agents.append(agent)

    removed = tuple(
        {
            "change": "removed",
            "hash": str(item["source_content_hash"]),
            "relative_path": relative_path,
            "slug": str(item.get("slug") or ""),
            "status": str(item.get("audit_status") or ""),
        }
        for relative_path, item in sorted(baseline.items())
        if relative_path not in seen_paths
    )
    return UpstreamDelta(
        source_revision=declared_revision,
        agents=tuple(selected_agents),
        outcomes=tuple(persisted_outcomes),
        entries=tuple(sorted(entries, key=lambda item: item["relative_path"])),
        removed=removed,
    )


def inspect_upstream_source(
    source_url: str,
    *,
    source_revision: str = "",
) -> UpstreamDelta:
    """Fetch and compare an operator-configured source without persistence."""

    download: RosterDownload = download_from_source(source_url)
    return plan_upstream_delta(
        download,
        download.outcomes,
        source_revision=source_revision,
    )


def import_upstream_source(
    store: Store,
    *,
    config: AgencyConfig,
    source_id: str,
    source_url: str,
    source_revision: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Quarantine a delta and its scan receipt; never approve or activate it."""

    plan = inspect_upstream_source(source_url, source_revision=source_revision)
    policy = resolve_inference_audit_policy(config)
    result = {
        **plan.public_dict(),
        "dry_run": bool(dry_run),
        "candidate_ids": [],
        "inference_policy": policy.public_dict(),
    }
    if dry_run:
        return result
    candidate_ids, outcomes = quarantine_manifest_import(
        plan.agents,
        plan.outcomes,
        source_id,
        store,
        require_inference=policy.required,
    )
    result["candidate_ids"] = candidate_ids
    result["outcomes"] = outcomes
    audits = audit_candidates_with_policy(store, candidate_ids, policy)
    scan_ids = {str(outcome.get("scan_id") or "") for outcome in outcomes}
    if len(scan_ids) != 1 or not next(iter(scan_ids)):
        raise RosterSyncError("manifest import did not return one source scan receipt")
    reconcile_manifest_remediation_resolutions(
        plan.agents,
        plan.outcomes,
        source_id,
        store,
        candidate_ids=candidate_ids,
        audits=audits,
        scan_id=next(iter(scan_ids)),
    )
    result["audits"] = [
        list_candidate_audits(store, candidate_id, limit=1)[0] for candidate_id in candidate_ids
    ]
    result["audit_ready"] = all(
        audit["verdict"] == "passed"
        and (not policy.required or audit["inference_status"] == "passed")
        for audit in result["audits"]
    )
    result["active_roster_changed"] = False
    return result


__all__ = [
    "UpstreamDelta",
    "import_upstream_source",
    "inspect_upstream_source",
    "plan_upstream_delta",
]
