"""Active-roster and immutable specialist-version persistence methods."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Container, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.agent_activation import agent_is_enabled, normalize_agent_slug
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import load_config
from agency_runtime.core.roster.bundled import (
    SOURCE_REPOSITORY,
    BundledRosterError,
    verify_bundled_agent_contract,
)
from agency_runtime.core.roster.limits import (
    MAX_ACTIVE_ROSTER_CURSOR_BYTES,
    MAX_ACTIVE_ROSTER_SIZE,
)
from agency_runtime.core.roster.remediation import is_registered_encoding_intermediate
from agency_runtime.core.roster.revisions import (
    ROUTING_LIST_METADATA_FIELDS,
    ROUTING_SCALAR_METADATA_FIELDS,
    content_identity_matches,
    decode_revision_metadata,
    immutable_revision_version,
    serialized_revision_metadata,
    source_version,
)
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.roster.source_identity import (
    MAX_DURABLE_SOURCE_COUNT,
    SourceIdentityError,
    canonical_source_display_name,
    canonical_source_identity,
)
from agency_runtime.core.roster.source_safety import scan_source_text
from agency_runtime.core.store.projections import project_snapshot_summary
from agency_runtime.core.store.roster_authority import (
    assert_active_revision_projection,
    assert_revision_activation_authority,
)
from agency_runtime.core.store.version_identity import normalize_version_identity
from agency_runtime.core.store.workforce import synchronize_active_workforce_worker
from agency_runtime.core.workforce.contract import (
    parse_workforce_contract,
    project_workforce_contract,
)

_JSON_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")
_MAX_ACTIVE_ROSTER_LIMIT = MAX_ACTIVE_ROSTER_SIZE
_MAX_ACTIVE_ROSTER_CURSOR_BYTES = MAX_ACTIVE_ROSTER_CURSOR_BYTES
_SQLITE_PARAMETER_CHUNK = 900
_UI_CAPABILITY_COLUMNS = tuple(f"capability_{index}" for index in range(4))
_UI_ROSTER_PROJECTION = ", ".join(
    (
        "agent_slug",
        "name",
        "division",
        *(
            "CASE WHEN json_valid(capabilities) "
            f"THEN json_extract(capabilities, '$[{index}]') ELSE NULL END "
            f"AS {column}"
            for index, column in enumerate(_UI_CAPABILITY_COLUMNS)
        ),
    )
)
_ACTIVE_ROSTER_JOIN = (
    "agent_active AS a JOIN agent_versions AS v "
    "ON v.agent_slug = a.agent_slug AND v.version = a.version "
    "JOIN agent_workers AS w ON w.agent_slug = a.agent_slug "
    "AND w.current_agent_version_id = v.id AND w.standing = 'active' "
    "JOIN agent_version_lineage AS wl ON wl.worker_id = w.worker_id "
    "AND wl.agent_version_id = w.current_agent_version_id "
    "LEFT JOIN agent_recruitment_contract_projections AS wp ON wp.id = ("
    "SELECT candidate.id FROM agent_recruitment_contract_projections AS candidate "
    "WHERE candidate.worker_id = w.worker_id "
    "AND candidate.agent_version_id = w.current_agent_version_id "
    "ORDER BY candidate.projection_sequence DESC LIMIT 1)"
)
_ACTIVE_WORKFORCE_CONTRACT = (
    "COALESCE(wp.recruitment_contract, wl.recruitment_contract) AS workforce_recruitment_contract"
)
_ACTIVE_ROSTER_ROUTING_PROJECTION = (
    f"a.*, v.metadata AS revision_metadata, {_ACTIVE_WORKFORCE_CONTRACT}"
)
_LEGACY_BUNDLED_VERSION = "1.0.0"
_LEGACY_BUNDLED_SOURCE = "bundled"
_MANAGED_BUNDLED_SOURCE_ID = "agency-agents"
_LEGACY_BUNDLED_IDENTITIES: Mapping[str, tuple[str, str]] = {
    # Exact prompt and active-projection SHA-256 identities from the released
    # seven-agent inline starter roster. They are intentionally immutable:
    # changing this allowlist would expand migration authority.
    "workflow-architect": (
        "3b5261b6b5ef770f1466be9eb688c011f7a756fc45258e1fba17f98ab13b0f3f",
        "2c8f20df8c326100f0a157705ee943e867236b977a13a8388edba41d052f6210",
    ),
    "code-reviewer": (
        "cdc08a324947021899e903944337d3767b6b24aa187997fb56260960a5f0fcfe",
        "152f2cc9ea95efc7033e39d28181a27b5ddb7f0da0e4246e5c66168d24890677",
    ),
    "senior-developer": (
        "f43616c7d37d27d1cbd6fb86843218899d571082a2e09627583b7f2eaf64c32a",
        "e2187a941bb8951e85b473e9a6fe959674111a71e081a7f159aac47035dc9c51",
    ),
    "technical-writer": (
        "dbe2342d2a447665feb4c0cf287b793c599af30a49a49b509a7f96963a3f30ac",
        "81fa9c04f8bb3cbfd861824fbae928f0ced079f6d4770cc005d462d538f933ae",
    ),
    "internationalization-engineer": (
        "8cc757d3593283efec8aa41e308e090ec36f2d783f5dd1d425b212cce3d153c5",
        "b006bbd8d7f0cd2fad3f869f36577a74a1785f2981b9f16572b76420d0b8c878",
    ),
    "payments-billing-engineer": (
        "2467cc54b843124978e8e14bc13895a10864f7ae3b7fc6ef458ed2fd42bc1654",
        "3240bd865350d93aa2ff9dd7ecf4a921792d0b5ecf334624b397c7afe4a7d672",
    ),
    "test-automation-engineer": (
        "a56f5e9977f853be39a7ff797ed4d008b19e2b35baf915cd680dd36f3d86b27a",
        "6dc0ef4b95280ed9ea6b8e8648a2f6cb44c2994f6572cb7e0d31df9131bf949c",
    ),
}


@dataclass(frozen=True, slots=True)
class BundledRosterReconciliation:
    """Cardinality-preserving result for install-time bundled reconciliation."""

    added: int
    upgraded: int


def _legacy_active_projection_hash(row: Mapping[str, Any]) -> str:
    projection = {
        "name": str(row.get("name") or ""),
        "division": str(row.get("division") or ""),
        "description": str(row.get("description") or ""),
        "categories": _decode_json_list(row.get("categories")),
        "capabilities": _decode_json_list(row.get("capabilities")),
        "tool_affinity": _decode_json_list(row.get("tool_affinity")),
    }
    serialized = json.dumps(
        projection,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _validate_roster_page(
    limit: int | None,
    after: str | None,
) -> tuple[int | None, str | None]:
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("limit must be an integer or None")
        if not 1 <= limit <= _MAX_ACTIVE_ROSTER_LIMIT:
            raise ValueError(f"limit must be between 1 and {_MAX_ACTIVE_ROSTER_LIMIT}")
    if after is not None:
        if not isinstance(after, str):
            raise TypeError("after must be a string or None")
        if not after or len(after.encode("utf-8")) > _MAX_ACTIVE_ROSTER_CURSOR_BYTES:
            raise ValueError(
                f"after must be between 1 and {_MAX_ACTIVE_ROSTER_CURSOR_BYTES} UTF-8 bytes"
            )
    return limit, after


def _decoded_roster_rows(rows: list[Any]) -> list[dict[str, Any]]:
    agents: list[dict[str, Any]] = []
    for row in rows:
        agent = dict(row)
        for field in _JSON_LIST_FIELDS:
            agent[field] = _decode_json_list(agent.get(field))
        raw_metadata = agent.pop("revision_metadata", None)
        if raw_metadata is not None:
            metadata = decode_revision_metadata(raw_metadata)
            agent["routing_contract_valid"] = metadata is not None
            for field in ROUTING_SCALAR_METADATA_FIELDS:
                agent[field] = str(metadata.get(field) or "") if metadata else ""
            for field in ROUTING_LIST_METADATA_FIELDS:
                value = metadata.get(field) if metadata else []
                agent[field] = list(value) if isinstance(value, list) else []
        raw_contract = agent.pop("workforce_recruitment_contract", None)
        if raw_contract is not None:
            try:
                contract_document = safe_load_bounded_json(
                    raw_contract,
                    maximum_bytes=256 * 1024,
                    maximum_depth=16,
                    maximum_nodes=2_000,
                )
                contract = parse_workforce_contract(contract_document)
            except (TypeError, ValueError) as exc:
                raise RuntimeError("stored workforce recruitment contract is invalid") from exc
            if (
                contract.agent_id != str(agent.get("agent_slug") or "")
                or contract.version != str(agent.get("version") or "")
                or contract.version_hash.removeprefix("sha256:")
                != str(agent.get("hash") or "").removeprefix("sha256:")
            ):
                raise RuntimeError("stored workforce recruitment contract identity is invalid")
            agent.update(
                {
                    "authority": contract.authority,
                    "context_mode": contract.context_mode,
                    "required_tools": list(contract.tool_classes),
                    "supported_hosts": list(contract.hosts),
                    "supported_platforms": list(contract.platforms),
                    "conflicts_with": list(
                        dict.fromkeys(
                            (
                                *contract.composition.same_context_conflicts,
                                *contract.composition.selection_exclusive,
                            )
                        )
                    ),
                    "requires": list(contract.composition.requires),
                    "audit_status": contract.audit.status,
                    "audit_revision": contract.audit.revision,
                    "routing_contract_valid": contract.audit.contract_valid,
                }
            )
        agents.append(agent)
    return agents


def _decoded_ui_roster_rows(rows: list[Any]) -> list[dict[str, Any]]:
    """Materialize only fixed-width fields rendered by dashboard roster cards."""

    agents: list[dict[str, Any]] = []
    for row in rows:
        agent = dict(row)
        capabilities = [
            value
            for column in _UI_CAPABILITY_COLUMNS
            if isinstance((value := agent.pop(column, None)), str) and value
        ]
        agent["capabilities"] = capabilities
        agents.append(agent)
    return agents


def _count_present_slugs(conn: Any, slugs: Container[str]) -> int:
    values = sorted(set(slugs))
    count = 0
    for offset in range(0, len(values), _SQLITE_PARAMETER_CHUNK):
        chunk = values[offset : offset + _SQLITE_PARAMETER_CHUNK]
        placeholders = ",".join("?" for _item in chunk)
        row = conn.execute(
            f"SELECT COUNT(*) AS count FROM agent_active "  # nosec B608
            f"WHERE agent_slug IN ({placeholders})",
            chunk,
        ).fetchone()
        count += int(row["count"])
    return count


def _is_legacy_bundled_active(row: Mapping[str, Any], slug: str) -> bool:
    """Recognize only the package-owned starter shape used before audited revisions."""

    legacy_identity = _LEGACY_BUNDLED_IDENTITIES.get(slug)
    if legacy_identity is None:
        return False
    expected_content_hash, expected_projection_hash = legacy_identity
    content = str(row.get("revision_content") or "")
    content_hash = str(row.get("revision_hash") or "")
    return bool(
        str(row.get("agent_slug") or "") == slug
        and str(row.get("version") or "") == _LEGACY_BUNDLED_VERSION
        and str(row.get("source") or "") == _LEGACY_BUNDLED_SOURCE
        and not str(row.get("source_id") or "")
        and not str(row.get("source_version") or "")
        and str(row.get("prompt_path") or "") == f"bundled://{slug}"
        and str(row.get("revision_source_id") or "") == ""
        and str(row.get("revision_source_version") or "") == ""
        and str(row.get("revision_metadata") or "{}") == "{}"
        and content
        and content_identity_matches(content, content_hash)
        and content_hash == expected_content_hash
        and str(row.get("hash") or "") == expected_content_hash
        and _legacy_active_projection_hash(row) == expected_projection_hash
    )


def _is_managed_bundled_active(row: Mapping[str, Any], slug: str) -> bool:
    """Recognize an older audited revision previously activated from this package."""

    metadata = decode_revision_metadata(row.get("revision_metadata"))
    source_version_value = str(row.get("source_version") or "")
    revision_source_version = str(row.get("revision_source_version") or "")
    content = str(row.get("revision_content") or "")
    content_hash = str(row.get("revision_hash") or "")
    return bool(
        metadata is not None
        and str(row.get("agent_slug") or "") == slug
        and str(row.get("version") or "").startswith("sha256:")
        and str(row.get("source") or "") == SOURCE_REPOSITORY
        and str(row.get("source_id") or "") == _MANAGED_BUNDLED_SOURCE_ID
        and str(row.get("prompt_path") or "") == f"bundled://{_MANAGED_BUNDLED_SOURCE_ID}/{slug}"
        and str(row.get("revision_source_id") or "") == _MANAGED_BUNDLED_SOURCE_ID
        and source_version_value
        and revision_source_version == source_version_value
        and str(metadata.get("source_revision") or "") == revision_source_version
        and str(metadata.get("audit_status") or "") == "approved"
        and re.fullmatch(r"[a-f0-9]{64}", str(metadata.get("source_content_hash") or ""))
        is not None
        and content
        and content_identity_matches(content, content_hash)
        and str(row.get("hash") or "") == content_hash
        and str(row.get("version") or "")
        == immutable_revision_version({**metadata, "hash": content_hash})
    )


def _disabled_agent_slugs(config_path: str | Path | None = None) -> frozenset[str]:
    """Resolve file-aware policy so external writes take effect without reparsing."""

    return frozenset(load_config(config_path).agents.disabled)


def _validated_source_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Project stored sources only after proving their display-safe identity."""

    validated: list[dict[str, Any]] = []
    for raw_row in rows:
        row = dict(raw_row)
        stored_url = row.get("url")
        stored_name = row.get("name")
        try:
            source_identity = canonical_source_identity(stored_url)
            source_name = canonical_source_display_name(
                stored_name,
                source_identity=source_identity,
                source_input=stored_url,
            )
        except SourceIdentityError:
            raise SourceIdentityError("stored roster source identity is invalid") from None
        if source_identity != stored_url or source_name != stored_name:
            raise SourceIdentityError("stored roster source identity is invalid")
        validated.append(row)
    return validated


def _decode_json_list(value: object) -> list[Any]:
    """Normalize one SQLite JSON projection without trusting legacy data."""

    try:
        parsed = safe_load_bounded_json(
            value or "[]",
            maximum_bytes=1024 * 1024,
            maximum_depth=16,
            maximum_nodes=1_000,
        )
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


@dataclass(frozen=True, slots=True)
class _PreparedRosterAgent:
    slug: str
    name: str
    division: str
    description: str
    source: str
    source_id: str
    source_version: str
    version: str
    content_hash: str
    content: str
    metadata: str
    categories: tuple[str, ...]
    capabilities: tuple[str, ...]
    tool_affinity: tuple[str, ...]
    prompt_path: str
    workforce_contract: str
    workforce_origin: str
    workforce_employment: str


def _prepared_roster_agent(
    agent: Mapping[str, Any],
    *,
    require_exact_bundled: bool = False,
    allow_agency_amendment: bool = False,
) -> _PreparedRosterAgent:
    """Validate behavior-bearing fields before opening a write transaction."""

    raw_content = agent.get("prompt_body") or agent.get("content") or agent.get("body")
    if not isinstance(raw_content, str) or not raw_content.strip():
        raise ValueError("roster agent requires explicit behavior content")
    content = raw_content
    original_slug = str(agent.get("slug") or "")
    normalized_slug = normalize_agent_slug(original_slug)
    try:
        exact_bundled = verify_bundled_agent_contract(agent, content)
        bundled_alias_slug = re.sub(r"[._]+", "-", normalized_slug)
        if not exact_bundled and (
            normalized_slug != original_slug or bundled_alias_slug != normalized_slug
        ):
            aliased = {**agent, "slug": bundled_alias_slug}
            if verify_bundled_agent_contract(aliased, content):
                raise BundledRosterError(
                    "recognized bundled specialist must use its canonical slug"
                )
    except BundledRosterError as exc:
        if not (allow_agency_amendment and str(agent.get("origin") or "") == "agency"):
            raise ValueError("recognized bundled roster contract is invalid") from exc
        exact_bundled = False
    if require_exact_bundled and not exact_bundled:
        raise ValueError("public activation requires an exact approved bundled agent")
    agent = {**agent, "slug": normalized_slug}
    if is_registered_encoding_intermediate(content):
        raise ValueError("registered encoding repair requires a verified semantic projection")
    safety = scan_source_text(content)
    if safety.controls or safety.suspicious_encoding:
        raise ValueError("roster content contains unsafe controls or suspicious encoding")
    version = str(agent.get("version") or "1.0.0")
    upstream_version = source_version(agent)
    content_hash = normalize_version_identity(agent.get("hash"), fallback_content=content)
    if not content_identity_matches(content, content_hash):
        raise ValueError("digest-shaped specialist hash does not match prompt content")
    metadata = serialized_revision_metadata(agent)
    decoded_metadata = decode_revision_metadata(metadata)
    if decoded_metadata is None:  # pragma: no cover - serializer contract
        raise ValueError("agent revision metadata could not be serialized")
    workforce_origin = str(agent.get("origin") or "upstream").strip().casefold()
    workforce_employment = str(agent.get("employment") or "employee").strip().casefold()
    workforce_source = dict(agent)
    if not all(
        workforce_source.get(field)
        for field in (
            "authority",
            "context_mode",
            "supported_hosts",
            "supported_platforms",
            "audit_status",
            "audit_revision",
        )
    ):
        # Preserve import compatibility without making an incomplete legacy
        # record recruitable. The whole-workforce index keeps it visible as a
        # quarantined semantic candidate until governed ingestion enriches it.
        # The primary roster row preserves the imported metadata exactly.  Its
        # compatibility projection must not reinterpret unreviewed strings as
        # a recruitment contract or let oversized legacy metadata block
        # activation.  Use a deliberately generic, quarantined contract until
        # governed ingestion produces a complete audited projection.
        workforce_source = {
            "slug": normalized_slug,
            "name": normalized_slug,
            "division": "specialized",
            "authority": "advise",
            "context_mode": "isolated_only",
            "supported_hosts": ["codex", "claude", "openclaw", "hermes"],
            "supported_platforms": ["windows", "linux"],
            "audit_status": "quarantined",
            "audit_revision": "legacy-unclassified",
            "routing_contract_valid": False,
            "capabilities": ["legacy unclassified role"],
            "task_types": [],
            "required_tools": [],
            "preferred_when": [],
            "avoid_when": [],
            "composition": {},
        }
    workforce_contract = project_workforce_contract(
        {
            **workforce_source,
            "slug": normalized_slug,
            "version": version,
            "version_hash": content_hash,
            "origin": workforce_origin,
            "employment": workforce_employment,
            "enabled": workforce_employment in {"contractor", "employee"},
        },
        origin=workforce_origin,
    )
    return _PreparedRosterAgent(
        slug=str(agent["slug"]),
        name=str(agent.get("name") or ""),
        division=str(agent.get("division") or ""),
        description=str(agent.get("description") or ""),
        source=str(agent.get("source") or ""),
        source_id=str(agent.get("source_id") or ""),
        source_version=upstream_version,
        version=version,
        content_hash=content_hash,
        content=content,
        metadata=metadata,
        categories=tuple(decoded_metadata["categories"]),
        capabilities=tuple(decoded_metadata["capabilities"]),
        tool_affinity=tuple(decoded_metadata["tool_affinity"]),
        prompt_path=str(agent.get("prompt_path") or ""),
        workforce_contract=json.dumps(
            workforce_contract.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        workforce_origin=workforce_origin,
        workforce_employment=workforce_employment,
    )


def _stage_workforce_version(
    conn: Any,
    agent: _PreparedRosterAgent,
    *,
    version_id: str,
    created_at: str,
) -> str:
    """Idempotently persist one validated but inactive workforce version."""

    existing = conn.execute(
        "SELECT id, hash, content, metadata FROM agent_versions "
        "WHERE agent_slug = ? AND version = ?",
        (agent.slug, agent.version),
    ).fetchone()
    if existing is not None:
        if (
            str(existing["hash"]) != agent.content_hash
            or str(existing["content"]) != agent.content
            or str(existing["metadata"]) != agent.metadata
        ):
            raise ValueError(f"immutable agent version conflict for {agent.slug}@{agent.version}")
        return str(existing["id"])
    conn.execute(
        "INSERT INTO agent_versions "
        "(id, agent_slug, version, source_version, source_id, hash, content, "
        "metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            version_id,
            agent.slug,
            agent.version,
            agent.source_version,
            agent.source_id,
            agent.content_hash,
            agent.content,
            agent.metadata,
            created_at,
        ),
    )
    return version_id


class RosterStoreMixin:
    """Roster-domain behavior composed into the canonical SQLite store."""

    # ── Roster ─────────────────────────────────────────────────────

    def add_agent_source(
        self, url: str, name: str = "", *, trusted_for_auto_approve: bool = False
    ) -> str:
        source_identity = canonical_source_identity(url)
        source_name = canonical_source_display_name(
            name,
            source_identity=source_identity,
            source_input=url,
        )
        source_id = self._uuid()
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT id FROM agent_sources WHERE url = ?",
                (source_identity,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE agent_sources "
                    "SET name = COALESCE(NULLIF(?, ''), name), enabled = 1, "
                    "trusted_for_auto_approve = CASE WHEN ? THEN 1 ELSE trusted_for_auto_approve END "
                    "WHERE url = ?",
                    (
                        source_name,
                        1 if trusted_for_auto_approve else 0,
                        source_identity,
                    ),
                )
                source_id = existing["id"]
            else:
                source_count = int(conn.execute("SELECT COUNT(*) FROM agent_sources").fetchone()[0])
                if source_count >= MAX_DURABLE_SOURCE_COUNT:
                    raise SourceIdentityError(
                        f"roster source count may not exceed {MAX_DURABLE_SOURCE_COUNT}"
                    )
                conn.execute(
                    "INSERT INTO agent_sources (id, url, name, added_at, trusted_for_auto_approve) VALUES (?, ?, ?, ?, ?)",
                    (
                        source_id,
                        source_identity,
                        source_name,
                        self._now(),
                        1 if trusted_for_auto_approve else 0,
                    ),
                )
            conn.commit()
            return source_id
        finally:
            conn.close()

    def list_agent_sources(self) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT * FROM agent_sources WHERE enabled = 1 ORDER BY added_at DESC"
            )
            return _validated_source_rows(cur.fetchall())
        finally:
            conn.close()

    def activate_agent(self, agent: dict[str, Any]) -> None:
        """Install one exact bundled fallback without replacing active state."""

        self._activate_agent(
            agent,
            replace=False,
            require_exact_bundled=True,
        )

    def activate_agent_if_missing(self, agent: dict[str, Any]) -> bool:
        """Activate a bundled fallback only when its slug is wholly absent."""

        return self._activate_agent(
            agent,
            replace=False,
            require_exact_bundled=True,
        )

    def activate_agents_if_missing(self, agents: Sequence[Mapping[str, Any]]) -> int:
        """Atomically seed exact bundled fallbacks without replacing entries."""

        return self._activate_agents_if_missing(
            agents,
            require_exact_bundled=True,
        )

    def reconcile_bundled_agents(
        self,
        agents: Sequence[Mapping[str, Any]],
    ) -> BundledRosterReconciliation:
        """Seed current contracts and refresh only provable package-owned bundled rows.

        Synced, operator-owned, and already-current active revisions are never
        replaced. Historical inline starters use an immutable allowlist. Newer
        package revisions must retain the audited repository, source ID, prompt
        URI, revision metadata, and content identity before an update may become
        active. Every replaced revision remains in immutable history.
        """

        if isinstance(agents, (str, bytes, bytearray)) or not isinstance(agents, Sequence):
            raise TypeError("agents must be a sequence of mappings")
        if len(agents) > _MAX_ACTIVE_ROSTER_LIMIT:
            raise ValueError(f"agents must contain at most {_MAX_ACTIVE_ROSTER_LIMIT} entries")
        prepared: list[_PreparedRosterAgent] = []
        seen_slugs: set[str] = set()
        for agent in agents:
            if not isinstance(agent, Mapping):
                raise TypeError("every roster entry must be a mapping")
            item = _prepared_roster_agent(agent, require_exact_bundled=True)
            if item.slug in seen_slugs:
                raise ValueError(f"duplicate roster slug in batch: {item.slug}")
            seen_slugs.add(item.slug)
            prepared.append(item)
        if not prepared:
            return BundledRosterReconciliation(added=0, upgraded=0)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            active_count = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_active").fetchone()["count"]
            )
            missing_count = len(prepared) - _count_present_slugs(
                conn, (item.slug for item in prepared)
            )
            if active_count + missing_count > _MAX_ACTIVE_ROSTER_LIMIT:
                raise ValueError(f"active roster cannot exceed {_MAX_ACTIVE_ROSTER_LIMIT} entries")

            added = 0
            upgraded = 0
            for item in prepared:
                current = conn.execute(
                    "SELECT a.*, v.source_id AS revision_source_id, "
                    "v.source_version AS revision_source_version, "
                    "v.hash AS revision_hash, v.content AS revision_content, "
                    "v.metadata AS revision_metadata "
                    "FROM agent_active AS a JOIN agent_versions AS v "
                    "ON v.agent_slug = a.agent_slug AND v.version = a.version "
                    "WHERE a.agent_slug = ? LIMIT 1",
                    (item.slug,),
                ).fetchone()
                if current is None:
                    added += self._activate_prepared_agent(conn, item, replace=False)
                    continue
                current_row = dict(current)
                package_update = str(
                    current_row.get("version") or ""
                ) != item.version and _is_managed_bundled_active(current_row, item.slug)
                if _is_legacy_bundled_active(current_row, item.slug) or package_update:
                    upgraded += self._activate_prepared_agent(conn, item, replace=True)
            changed = added + upgraded
            if changed:
                conn.execute(
                    "UPDATE store_counters SET value = value + ? WHERE name = 'roster-generation'",
                    (changed,),
                )
            conn.commit()
            return BundledRosterReconciliation(added=added, upgraded=upgraded)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _activate_prevalidated_agents_if_missing(
        self,
        agents: Sequence[Mapping[str, Any]],
    ) -> int:
        """Trusted internal batch seam for already-governed revisions."""

        return self._activate_agents_if_missing(
            agents,
            require_exact_bundled=False,
        )

    def _activate_agents_if_missing(
        self,
        agents: Sequence[Mapping[str, Any]],
        *,
        require_exact_bundled: bool,
    ) -> int:
        """Atomically activate a bounded roster batch without replacing entries.

        Every behavior-bearing field is validated before a connection or write
        transaction is opened.  A conflict in any immutable revision rolls the
        complete batch back, so installation cannot expose a partial roster.
        """

        if isinstance(agents, (str, bytes, bytearray)) or not isinstance(agents, Sequence):
            raise TypeError("agents must be a sequence of mappings")
        if len(agents) > _MAX_ACTIVE_ROSTER_LIMIT:
            raise ValueError(f"agents must contain at most {_MAX_ACTIVE_ROSTER_LIMIT} entries")
        prepared: list[_PreparedRosterAgent] = []
        seen_slugs: set[str] = set()
        for agent in agents:
            if not isinstance(agent, Mapping):
                raise TypeError("every roster entry must be a mapping")
            item = _prepared_roster_agent(
                agent,
                require_exact_bundled=require_exact_bundled,
            )
            if item.slug in seen_slugs:
                raise ValueError(f"duplicate roster slug in batch: {item.slug}")
            seen_slugs.add(item.slug)
            prepared.append(item)
        if not prepared:
            return 0

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            active_count = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_active").fetchone()["count"]
            )
            missing_count = len(prepared) - _count_present_slugs(
                conn, (item.slug for item in prepared)
            )
            if active_count + missing_count > _MAX_ACTIVE_ROSTER_LIMIT:
                raise ValueError(f"active roster cannot exceed {_MAX_ACTIVE_ROSTER_LIMIT} entries")
            inserted = sum(
                self._activate_prepared_agent(conn, item, replace=False) for item in prepared
            )
            if inserted:
                conn.execute(
                    "UPDATE store_counters SET value = value + ? WHERE name = 'roster-generation'",
                    (inserted,),
                )
            conn.commit()
            return inserted
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _activate_agent(
        self,
        agent: Mapping[str, Any],
        *,
        replace: bool,
        require_exact_bundled: bool,
    ) -> bool:
        prepared = _prepared_roster_agent(
            agent,
            require_exact_bundled=require_exact_bundled,
        )
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            changed = self._activate_prepared_agent(conn, prepared, replace=replace)
            if changed:
                conn.execute(
                    "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
                )
            conn.commit()
            return changed
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _activate_prevalidated_agent(self, agent: Mapping[str, Any]) -> bool:
        """Trusted internal seam for already-governed candidate/test revisions."""

        return self._activate_agent(
            agent,
            replace=True,
            require_exact_bundled=False,
        )

    def _activate_prevalidated_agent_if_missing(self, agent: Mapping[str, Any]) -> bool:
        """Trusted internal non-replacing seam for already-governed revisions."""

        return self._activate_agent(
            agent,
            replace=False,
            require_exact_bundled=False,
        )

    def stage_agency_workforce_agent(self, agent: Mapping[str, Any]) -> str:
        """Persist one validated Agency-owned prompt version without activating it."""

        prepared = _prepared_roster_agent(agent, require_exact_bundled=False)
        if prepared.workforce_origin != "agency" or prepared.workforce_employment != "contractor":
            raise ValueError("staged workforce hires must be Agency-owned contractors")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM agent_active WHERE agent_slug = ?",
                (prepared.slug,),
            ).fetchone():
                raise ValueError("staged contractor slug is already active")
            if conn.execute(
                "SELECT 1 FROM agent_workers WHERE agent_slug = ?",
                (prepared.slug,),
            ).fetchone():
                raise ValueError("staged contractor slug already has a workforce identity")
            existing = conn.execute(
                "SELECT version.id FROM agent_versions AS version "
                "LEFT JOIN agent_version_lineage AS lineage "
                "ON lineage.agent_version_id = version.id "
                "WHERE version.agent_slug = ? AND version.version = ? AND version.hash = ? "
                "AND lineage.agent_version_id IS NULL ORDER BY version.created_at LIMIT 1",
                (prepared.slug, prepared.version, prepared.content_hash),
            ).fetchone()
            if existing is not None:
                conn.commit()
                return str(existing["id"])
            version_id = _stage_workforce_version(
                conn,
                prepared,
                version_id=self._uuid(),
                created_at=self._now(),
            )
            conn.commit()
            return version_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def stage_agency_workforce_amendment(
        self,
        agent: Mapping[str, Any],
        *,
        expected_revision: int,
    ) -> str:
        """Persist an Agency-owned amendment version without activating it."""

        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise TypeError("expected_revision must be an integer")
        if expected_revision < 0:
            raise ValueError("expected_revision is invalid")
        prepared = _prepared_roster_agent(
            agent,
            require_exact_bundled=False,
            allow_agency_amendment=True,
        )
        if prepared.workforce_origin != "agency":
            raise ValueError("workforce amendments must be Agency-owned")
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            worker = conn.execute(
                "SELECT worker.revision, worker.standing, version.content AS parent_content "
                "FROM agent_workers AS worker JOIN agent_versions AS version "
                "ON version.id = worker.current_agent_version_id WHERE worker.agent_slug = ?",
                (prepared.slug,),
            ).fetchone()
            if worker is None:
                raise KeyError("workforce worker not found")
            if int(worker["revision"]) != expected_revision:
                raise RuntimeError("workforce revision conflict")
            if str(worker["standing"]) in {"retired", "merged"}:
                raise ValueError("terminal workforce state cannot be amended")
            parent_content = str(worker["parent_content"] or "")
            if not parent_content or not prepared.content.startswith(parent_content):
                raise ValueError("Agency amendment must preserve the complete upstream prompt")
            if prepared.content == parent_content:
                raise ValueError("Agency amendment must add a bounded capability extension")
            version_id = _stage_workforce_version(
                conn,
                prepared,
                version_id=self._uuid(),
                created_at=self._now(),
            )
            conn.commit()
            return version_id
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _activate_prepared_agent(
        self,
        conn: Any,
        agent: _PreparedRosterAgent,
        *,
        replace: bool,
    ) -> bool:
        """Apply one validated roster entry inside the caller's transaction."""

        if (
            agent.workforce_origin == "agency"
            and not conn.execute(
                "SELECT 1 FROM agent_workers WHERE agent_slug = ?",
                (agent.slug,),
            ).fetchone()
        ):
            raise ValueError("Agency-owned contractors must use audited workforce hiring")

        if not replace:
            existing_active = conn.execute(
                "SELECT 1 FROM agent_active WHERE agent_slug = ? LIMIT 1",
                (agent.slug,),
            ).fetchone()
            if existing_active is not None:
                return False
        existing_version = conn.execute(
            "SELECT id, hash, content, metadata FROM agent_versions "
            "WHERE agent_slug = ? AND version = ?",
            (agent.slug, agent.version),
        ).fetchone()
        if existing_version is not None and (
            str(existing_version["hash"] or "") != agent.content_hash
            or str(existing_version["content"] or "") != agent.content
            or not content_identity_matches(existing_version["content"], existing_version["hash"])
            or (
                str(existing_version["metadata"] or "{}") != "{}"
                and str(existing_version["metadata"]) != agent.metadata
            )
        ):
            raise ValueError(f"immutable agent version conflict for {agent.slug}@{agent.version}")
        if existing_version is None:
            agent_version_id = self._uuid()
            conn.execute(
                "INSERT INTO agent_versions "
                "(id, agent_slug, version, source_version, source_id, hash, content, "
                "metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_version_id,
                    agent.slug,
                    agent.version,
                    agent.source_version,
                    agent.source_id,
                    agent.content_hash,
                    agent.content,
                    agent.metadata,
                    self._now(),
                ),
            )
        else:
            agent_version_id = str(existing_version["id"])
        statement = (
            "INSERT OR REPLACE INTO agent_active " if replace else "INSERT INTO agent_active "
        )
        conn.execute(
            statement + "(id, agent_slug, name, division, description, source, version, hash, "
            "source_id, source_version, categories, capabilities, tool_affinity, "
            "prompt_path, activated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self._uuid(),
                agent.slug,
                agent.name,
                agent.division,
                agent.description,
                agent.source,
                agent.version,
                agent.content_hash,
                agent.source_id,
                agent.source_version,
                json.dumps(agent.categories),
                json.dumps(agent.capabilities),
                json.dumps(agent.tool_affinity),
                agent.prompt_path,
                self._now(),
            ),
        )
        conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (agent.slug,))
        conn.executemany(
            "INSERT INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
            (
                (self._uuid(), agent.slug, category)
                for category in dict.fromkeys(agent.categories)
                if category
            ),
        )
        synchronize_active_workforce_worker(
            conn,
            agent_slug=agent.slug,
            display_name=agent.name or agent.slug,
            origin=agent.workforce_origin,
            employment_class=agent.workforce_employment,
            agent_version_id=agent_version_id,
            version=agent.version,
            version_hash=agent.content_hash,
            recruitment_contract=agent.workforce_contract,
        )
        return True

    def upsert_roster_entry(self, agent: dict[str, Any]) -> None:
        """Persist one active roster entry through the immutable-version boundary."""

        self.activate_agent(agent)

    def get_active_roster(
        self,
        *,
        limit: int | None = None,
        after: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return a stable active-roster page ordered after an optional slug cursor."""
        limit, after = _validate_roster_page(limit, after)
        conn = self._connect()
        try:
            if after is None and limit is None:
                cur = conn.execute(
                    f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                    f"FROM {_ACTIVE_ROSTER_JOIN} ORDER BY a.agent_slug"  # nosec B608
                )
            elif after is None:
                cur = conn.execute(
                    f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                    f"FROM {_ACTIVE_ROSTER_JOIN} "  # nosec B608
                    "ORDER BY a.agent_slug LIMIT ?",
                    (limit,),
                )
            elif limit is None:
                cur = conn.execute(
                    f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                    f"FROM {_ACTIVE_ROSTER_JOIN} "  # nosec B608
                    "WHERE a.agent_slug > ? ORDER BY a.agent_slug",
                    (after,),
                )
            else:
                cur = conn.execute(
                    f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                    f"FROM {_ACTIVE_ROSTER_JOIN} "  # nosec B608
                    "WHERE a.agent_slug > ? ORDER BY a.agent_slug LIMIT ?",
                    (after, limit),
                )
            return _decoded_roster_rows(cur.fetchall())
        finally:
            conn.close()

    def get_active_roster_page_snapshot(
        self,
        *,
        limit: int,
        after: str | None = None,
        disabled_agents: Container[str] = (),
    ) -> dict[str, Any]:
        """Read one internally consistent roster page and monotonic revision."""

        return self._get_active_roster_page_snapshot(
            limit=limit,
            after=after,
            disabled_agents=disabled_agents,
            projection="*",
            decode_rows=_decoded_roster_rows,
        )

    def get_active_roster_ui_page_snapshot(
        self,
        *,
        limit: int,
        after: str | None = None,
        disabled_agents: Container[str] = (),
    ) -> dict[str, Any]:
        """Read a card-only roster page without materializing routing metadata."""

        return self._get_active_roster_page_snapshot(
            limit=limit,
            after=after,
            disabled_agents=disabled_agents,
            projection=_UI_ROSTER_PROJECTION,
            decode_rows=_decoded_ui_roster_rows,
        )

    def get_active_roster_activation_page_snapshot(
        self,
        *,
        limit: int,
        after: str | None = None,
        disabled_agents: Container[str] = (),
    ) -> dict[str, Any]:
        """Read activation-list labels without taxonomy or routing metadata."""

        return self._get_active_roster_page_snapshot(
            limit=limit,
            after=after,
            disabled_agents=disabled_agents,
            projection="agent_slug, name, division",
            decode_rows=lambda rows: [dict(row) for row in rows],
        )

    def _get_active_roster_page_snapshot(
        self,
        *,
        limit: int,
        after: str | None,
        disabled_agents: Container[str],
        projection: str,
        decode_rows: Callable[[list[Any]], list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Read one projection, counts, and generation in a single transaction."""

        validated_limit, validated_after = _validate_roster_page(limit, after)
        if validated_limit is None:
            raise ValueError("limit is required for roster page snapshots")
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            counter = conn.execute(
                "SELECT value FROM store_counters WHERE name = 'roster-generation'"
            ).fetchone()
            if counter is None or isinstance(counter["value"], bool):
                raise RuntimeError("roster generation counter is unavailable")
            total = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_active").fetchone()["count"]
            )
            disabled_count = _count_present_slugs(conn, disabled_agents)
            if validated_after is None:
                rows = conn.execute(
                    f"SELECT {projection} FROM agent_active "  # nosec B608
                    "ORDER BY agent_slug LIMIT ?",
                    (validated_limit + 1,),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT {projection} FROM agent_active "  # nosec B608
                    "WHERE agent_slug > ? "
                    "ORDER BY agent_slug LIMIT ?",
                    (validated_after, validated_limit + 1),
                ).fetchall()
            result = {
                "generation": int(counter["value"]),
                "total_count": total,
                "enabled_count": total - disabled_count,
                "rows": decode_rows(rows),
            }
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_active_roster_entry_snapshot(
        self,
        slug: str,
        *,
        disabled_agents: Container[str] = (),
    ) -> dict[str, Any]:
        """Read one exact entry and global roster counters from one snapshot."""

        normalized = normalize_agent_slug(slug)
        conn = self._connect()
        try:
            conn.execute("BEGIN")
            counter = conn.execute(
                "SELECT value FROM store_counters WHERE name = 'roster-generation'"
            ).fetchone()
            if counter is None or isinstance(counter["value"], bool):
                raise RuntimeError("roster generation counter is unavailable")
            total = int(
                conn.execute("SELECT COUNT(*) AS count FROM agent_active").fetchone()["count"]
            )
            disabled_count = _count_present_slugs(conn, disabled_agents)
            row = conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = ? LIMIT 1",
                (normalized,),
            ).fetchone()
            result = {
                "generation": int(counter["value"]),
                "total_count": total,
                "enabled_count": total - disabled_count,
                "rows": _decoded_roster_rows([row]) if row is not None else [],
            }
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def count_active_roster(self) -> int:
        """Return the active roster cardinality without materializing its rows."""
        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT COUNT(*) AS count FROM {_ACTIVE_ROSTER_JOIN}"  # nosec B608
            ).fetchone()
            return int(row["count"])
        finally:
            conn.close()

    def has_active_roster_definition(self, slug: str) -> bool:
        """Return whether one immutable active definition exists.

        Activation policy also applies to legacy definitions that predate the
        normalized workforce projection. Those definitions remain excluded
        from routing until reconciliation, but operators must still be able to
        disable them immediately.
        """

        normalized = normalize_agent_slug(slug)
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM agent_active AS a JOIN agent_versions AS v "
                "ON v.agent_slug = a.agent_slug AND v.version = a.version "
                "WHERE a.agent_slug = ? LIMIT 1",
                (normalized,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_enabled_roster(
        self,
        *,
        limit: int | None = None,
        after: str | None = None,
        disabled_agents: Container[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return enabled active definitions without deleting disabled rows."""

        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int):
                raise TypeError("limit must be an integer or None")
            if not 1 <= limit <= _MAX_ACTIVE_ROSTER_LIMIT:
                raise ValueError(f"limit must be between 1 and {_MAX_ACTIVE_ROSTER_LIMIT}")
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        agents = self.get_active_roster(after=after)
        enabled = [agent for agent in agents if agent_is_enabled(agent["agent_slug"], disabled)]
        return enabled if limit is None else enabled[:limit]

    def count_enabled_roster(
        self,
        *,
        disabled_agents: Container[str] | None = None,
    ) -> int:
        """Return the effective routing-roster cardinality."""

        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        conn = self._connect()
        try:
            rows = conn.execute(
                f"SELECT a.agent_slug FROM {_ACTIVE_ROSTER_JOIN}"  # nosec B608
            ).fetchall()
            return sum(agent_is_enabled(row["agent_slug"], disabled) for row in rows)
        finally:
            conn.close()

    def get_disabled_agent_slugs(self) -> frozenset[str]:
        """Return one fresh immutable activation-policy snapshot."""

        from agency_runtime.core.config_binding import config_for_store

        return frozenset(config_for_store(self).agents.disabled)

    def get_roster_entry(self, slug: str) -> dict[str, Any] | None:
        """Return one active roster entry without exposing versioned prompt content."""

        conn = self._connect()
        try:
            row = conn.execute(
                f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                f"FROM {_ACTIVE_ROSTER_JOIN} "
                "WHERE a.agent_slug = ? LIMIT 1",
                (slug,),
            ).fetchone()
            if row is None:
                return None
            return _decoded_roster_rows([row])[0]
        finally:
            conn.close()

    def get_active_roster_as_catalog(
        self,
        *,
        disabled_agents: Container[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return enabled active roster in selector-compatible format."""
        agents = self.get_enabled_roster(disabled_agents=disabled_agents)
        projected = [selector_roster_projection(agent) for agent in agents]
        return [
            {
                **agent,
                "slug": agent["agent_slug"],
                **(
                    {
                        "version": str(source.get("version") or ""),
                        "hash": str(source.get("hash") or ""),
                    }
                    if source.get("version") and source.get("hash")
                    else {}
                ),
            }
            for source, agent in zip(agents, projected, strict=True)
        ]

    def get_routing_roster_snapshot(
        self,
        *,
        disabled_agents: Container[str] = (),
    ) -> dict[str, Any]:
        """Read the complete enabled selector catalog and generation atomically."""

        conn = self._connect()
        try:
            conn.execute("BEGIN")
            counter = conn.execute(
                "SELECT value FROM store_counters WHERE name = 'roster-generation'"
            ).fetchone()
            if counter is None or isinstance(counter["value"], bool):
                raise RuntimeError("roster generation counter is unavailable")
            rows = conn.execute(
                f"SELECT {_ACTIVE_ROSTER_ROUTING_PROJECTION} "  # nosec B608
                f"FROM {_ACTIVE_ROSTER_JOIN} ORDER BY a.agent_slug"  # nosec B608
            ).fetchall()
            enabled_agents = [
                agent
                for agent in _decoded_roster_rows(rows)
                if agent_is_enabled(str(agent["agent_slug"]), disabled_agents)
            ]
            agents = [selector_roster_projection(agent) for agent in enabled_agents]
            result = {
                "generation": int(counter["value"]),
                "catalog": [
                    {
                        **agent,
                        "slug": agent["agent_slug"],
                        "version": str(source.get("version") or ""),
                        "hash": str(source.get("hash") or ""),
                    }
                    for source, agent in zip(enabled_agents, agents, strict=True)
                ],
            }
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_specialist_prompt(
        self,
        slug: str,
        *,
        max_chars: int = 65_536,
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any] | None:
        """Return one active specialist with its versioned bounded prompt."""
        try:
            normalized_slug = normalize_agent_slug(slug)
        except ValueError:
            return None
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        if not agent_is_enabled(normalized_slug, disabled):
            return None
        bounded = max(1, min(int(max_chars), 262_144))
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT a.*, v.content AS prompt_body, v.hash AS prompt_hash "
                "FROM agent_active AS a "
                "JOIN agent_versions AS v "
                "ON v.agent_slug = a.agent_slug AND v.version = a.version "
                "JOIN agent_workers AS w ON w.agent_slug = a.agent_slug "
                "AND w.current_agent_version_id = v.id AND w.standing = 'active' "
                "WHERE a.agent_slug = ? LIMIT 1",
                (normalized_slug,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            for field in _JSON_LIST_FIELDS:
                result[field] = _decode_json_list(result.get(field))
            content = str(result.get("prompt_body") or "")
            prompt_hash = str(result.get("prompt_hash") or "")
            if (
                not content
                or prompt_hash != str(result.get("hash") or "")
                or not content_identity_matches(content, prompt_hash)
            ):
                return None
            result["prompt_body"] = content[:bounded]
            result["prompt_truncated"] = len(content) > bounded
            return result
        finally:
            conn.close()

    def get_versioned_specialist_prompt(
        self,
        slug: str,
        version: str,
        content_hash: str,
        *,
        max_chars: int = 65_536,
        disabled_agents: Container[str] | None = None,
    ) -> dict[str, Any] | None:
        """Read one exact immutable prompt version for side-effect-free replay."""

        try:
            normalized_slug = normalize_agent_slug(slug)
        except ValueError:
            return None
        disabled = self.get_disabled_agent_slugs() if disabled_agents is None else disabled_agents
        if not agent_is_enabled(normalized_slug, disabled):
            return None
        normalized_version = str(version or "").strip()
        try:
            normalized_hash = normalize_version_identity(content_hash)
        except ValueError:
            return None
        if not normalized_version:
            return None
        bounded = max(1, min(int(max_chars), 262_144))
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT v.agent_slug, v.version, v.hash, v.content FROM agent_versions AS v "
                "JOIN agent_workers AS w ON w.agent_slug = v.agent_slug "
                "AND w.standing = 'active' "
                "WHERE v.agent_slug = ? AND v.version = ? AND v.hash = ? LIMIT 1",
                (normalized_slug, normalized_version, normalized_hash),
            ).fetchone()
            if row is None:
                return None
            content = str(row["content"] or "")
            if not content or not content_identity_matches(content, row["hash"]):
                return None
            return {
                "slug": str(row["agent_slug"]),
                "version": str(row["version"]),
                "hash": str(row["hash"]),
                "prompt_body": content[:bounded],
                "prompt_truncated": len(content) > bounded,
            }
        finally:
            conn.close()

    def rollback_agent_revision(
        self,
        slug: str,
        target_version: str,
        *,
        expected_current_version: str,
        expected_current_hash: str,
    ) -> dict[str, Any]:
        """Restore one immutable revision under an exact current-revision CAS."""

        normalized_slug = normalize_agent_slug(slug)
        target = str(target_version or "").strip()
        expected_version = str(expected_current_version or "").strip()
        if not target or not expected_version:
            raise ValueError("target and expected current versions are required")
        expected_hash = normalize_version_identity(expected_current_hash)
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = ? LIMIT 1",
                (normalized_slug,),
            ).fetchone()
            if current is None:
                raise ValueError(f"active agent not found: {normalized_slug}")
            current_revision = conn.execute(
                "SELECT id, agent_slug, version, source_version, source_id, hash, content, metadata "
                "FROM agent_versions WHERE agent_slug = ? AND version = ? LIMIT 1",
                (normalized_slug, str(current["version"] or "")),
            ).fetchone()
            if current_revision is None:
                raise ValueError(
                    f"active revision is missing: {normalized_slug}@{current['version']!s}"
                )
            assert_active_revision_projection(
                dict(current),
                dict(current_revision),
            )
            if (
                str(current["version"] or "") != expected_version
                or str(current["hash"] or "") != expected_hash
            ):
                raise ValueError(
                    f"active revision changed for {normalized_slug}; refresh and retry rollback"
                )
            revision = conn.execute(
                "SELECT id, agent_slug, version, source_version, source_id, hash, content, metadata "
                "FROM agent_versions WHERE agent_slug = ? AND version = ? LIMIT 1",
                (normalized_slug, target),
            ).fetchone()
            if revision is None:
                raise ValueError(f"revision not found: {normalized_slug}@{target}")
            revision_record = dict(revision)
            content = str(revision_record["content"] or "")
            revision_hash = str(revision_record["hash"] or "")
            if not content or not content_identity_matches(content, revision_hash):
                raise ValueError(f"revision integrity failed: {normalized_slug}@{target}")
            assert_revision_activation_authority(
                conn,
                slug=normalized_slug,
                revision=revision_record,
            )
            metadata = decode_revision_metadata(revision_record["metadata"])
            if metadata is None:
                raise ValueError(f"revision {normalized_slug}@{target} predates rollback metadata")
            if target == expected_version and revision_hash == expected_hash:
                conn.commit()
                result = dict(current)
                for field in _JSON_LIST_FIELDS:
                    result[field] = _decode_json_list(result.get(field))
                return result

            activated_at = self._now()
            conn.execute(
                "INSERT OR REPLACE INTO agent_active "
                "(id, agent_slug, name, division, description, source, source_id, "
                "source_version, version, hash, categories, capabilities, tool_affinity, "
                "prompt_path, activated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    normalized_slug,
                    metadata["name"],
                    metadata["division"],
                    metadata["description"],
                    metadata["source"],
                    str(revision_record["source_id"] or ""),
                    str(revision_record["source_version"] or metadata["source_version"]),
                    target,
                    revision_hash,
                    json.dumps(metadata["categories"]),
                    json.dumps(metadata["capabilities"]),
                    json.dumps(metadata["tool_affinity"]),
                    metadata["prompt_path"],
                    activated_at,
                ),
            )
            conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (normalized_slug,))
            conn.executemany(
                "INSERT INTO agent_categories (id, agent_slug, category) VALUES (?, ?, ?)",
                ((self._uuid(), normalized_slug, category) for category in metadata["categories"]),
            )
            worker = conn.execute(
                "SELECT origin, employment_class FROM agent_workers WHERE agent_slug = ?",
                (normalized_slug,),
            ).fetchone()
            if worker is None:
                raise ValueError(f"workforce identity is missing: {normalized_slug}")
            rollback_contract = project_workforce_contract(
                {
                    **metadata,
                    "slug": normalized_slug,
                    "version": target,
                    "version_hash": revision_hash,
                    "origin": str(worker["origin"]),
                    "employment": str(worker["employment_class"]),
                    "enabled": True,
                },
                origin=str(worker["origin"]),
            )
            synchronize_active_workforce_worker(
                conn,
                agent_slug=normalized_slug,
                display_name=str(metadata["name"] or normalized_slug),
                origin=str(worker["origin"]),
                employment_class=str(worker["employment_class"]),
                agent_version_id=str(revision_record["id"]),
                version=target,
                version_hash=revision_hash,
                recruitment_contract=json.dumps(
                    rollback_contract.to_dict(),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
            conn.execute(
                "INSERT INTO agent_import_events "
                "(id, event_type, agent_slug, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    "agent_revision_rolled_back",
                    normalized_slug,
                    json.dumps(
                        {
                            "from_hash": expected_hash,
                            "from_version": expected_version,
                            "to_hash": revision_hash,
                            "to_version": target,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    activated_at,
                ),
            )
            conn.execute(
                "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
            )
            row = conn.execute(
                "SELECT * FROM agent_active WHERE agent_slug = ?",
                (normalized_slug,),
            ).fetchone()
            conn.commit()
            result = dict(row)
            for field in _JSON_LIST_FIELDS:
                result[field] = _decode_json_list(result.get(field))
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def deactivate_agent(self, slug: str) -> None:
        conn = self._connect()
        try:
            deleted = conn.execute("DELETE FROM agent_active WHERE agent_slug = ?", (slug,))
            if deleted.rowcount:
                conn.execute("DELETE FROM agent_categories WHERE agent_slug = ?", (slug,))
                conn.execute(
                    "UPDATE store_counters SET value = value + 1 WHERE name = 'roster-generation'"
                )
            conn.commit()
        finally:
            conn.close()

    def create_snapshot(self, snapshot_id: str, manifest: dict[str, Any]) -> None:
        snapshot_agent_count = len(manifest.get("candidates", []))
        summary = project_snapshot_summary(manifest)
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_snapshots "
                "(id, snapshot_id, created_at, agent_count, manifest, activated, "
                "approved, added_count, changed_count, removed_count) "
                "VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                (
                    self._uuid(),
                    snapshot_id,
                    self._now(),
                    snapshot_agent_count,
                    json.dumps(manifest),
                    int(bool(summary["approved"])),
                    int(summary["added"]),
                    int(summary["changed"]),
                    int(summary["removed"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def record_import_event(self, event_type: str, agent_slug: str = "", detail: str = "") -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO agent_import_events (id, event_type, agent_slug, detail, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self._uuid(), event_type, agent_slug, detail, self._now()),
            )
            conn.commit()
        finally:
            conn.close()
