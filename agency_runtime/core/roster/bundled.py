"""Fail-closed access to the audited, self-contained specialist roster."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Iterator, Mapping, Sequence
from functools import lru_cache
from importlib import resources
from pathlib import PurePosixPath
from typing import Any, Final, overload

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.remediation import (
    RosterRemediationError,
    verify_packaged_remediation,
)
from agency_runtime.core.roster.revisions import immutable_revision_version
from agency_runtime.core.roster.semantic_projection import (
    contract_for_source_hash,
    governed_prompt,
)
from agency_runtime.core.roster.source_safety import scan_source_text

BUNDLED_ROSTER_SCHEMA: Final[int] = 2
MAX_BUNDLED_AGENTS: Final[int] = 512
MAX_MANIFEST_BYTES: Final[int] = 4 * 1024 * 1024
MAX_PROMPT_BYTES: Final[int] = 256 * 1024
MAX_LICENSE_BYTES: Final[int] = 64 * 1024
SOURCE_REPOSITORY: Final[str] = "https://github.com/msitarzewski/agency-agents"
SOURCE_LICENSE: Final[str] = "MIT"
SOURCE_LICENSE_FILE: Final[str] = "LICENSE.agency-agents.txt"

_DATA_DIRECTORY = "data"
_MANIFEST_FILE = "manifest.json"
_MANIFEST_DIGEST_FILE = "manifest.sha256"
_SLUG = re.compile(r"[a-z0-9][a-z0-9._-]{1,127}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_SOURCE_REVISION = re.compile(r"[a-f0-9]{40,64}\Z")
_MANIFEST_LAYOUT_CONTROL = re.compile(r"[\t\n\r]")
_STATUS = frozenset({"approved", "quarantined", "retired"})
_AUTHORITY = frozenset({"advise", "plan", "modify", "review", "approve"})
_CONTEXT_MODE = frozenset({"direct_safe", "isolated_only"})
_WINDOWS_DEVICE_STEMS = frozenset(
    {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)
_LIST_FIELDS = (
    "categories",
    "capabilities",
    "anti_capabilities",
    "task_types",
    "preferred_when",
    "avoid_when",
    "required_tools",
    "supported_hosts",
    "supported_platforms",
    "conflicts_with",
    "requires",
    "evidence_requirements",
    "model_requirements",
    "findings",
)
_TEXT_FIELDS = (
    "relative_path",
    "slug",
    "display_name",
    "division",
    "description",
    "authority",
    "context_mode",
    "independence_group",
    "expected_output_contract",
    "source_revision",
    "source_content_hash",
    "audit_revision",
    "audit_status",
    "version",
)
_AGENT_FIELDS = frozenset((*_TEXT_FIELDS, *_LIST_FIELDS, "prompt_file", "prompt_hash"))
_AGENT_OPTIONAL_FIELDS = frozenset({"optional_tools", "remediation"})
_SOURCE_FIELDS = frozenset({"repository", "revision", "license", "license_file", "license_hash"})
_MANIFEST_FIELDS = frozenset({"schema_version", "source", "counts", "agents"})
_COUNT_FIELDS = frozenset({"total", "approved", "quarantined", "retired"})


class BundledRosterError(RuntimeError):
    """Raised when packaged roster provenance or content cannot be trusted."""


def _has_unsafe_text(value: str, *, allow_prompt_layout: bool = False) -> bool:
    """Apply the shared source-safety policy at every packaged text boundary."""

    scan = scan_source_text(value)
    return bool(
        scan.controls
        or scan.suspicious_encoding
        or (not allow_prompt_layout and _MANIFEST_LAYOUT_CONTROL.search(value))
    )


def _safe_relative_path(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise BundledRosterError(f"{label} is not a safe package-relative path")
    text = value
    candidate = PurePosixPath(text)
    if (
        not text
        or candidate.is_absolute()
        or "\\" in text
        or _has_unsafe_text(text)
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or any(
            part.endswith((" ", "."))
            or ":" in part
            or part.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_STEMS
            for part in candidate.parts
        )
    ):
        raise BundledRosterError(f"{label} is not a safe package-relative path")
    return candidate.as_posix()


def _resource(relative_path: str, *, limit: int, label: str) -> bytes:
    safe_path = _safe_relative_path(relative_path, label=label)
    node = resources.files("agency_runtime.core.roster").joinpath(_DATA_DIRECTORY)
    for part in PurePosixPath(safe_path).parts:
        node = node.joinpath(part)
    try:
        with node.open("rb") as stream:
            data = stream.read(limit + 1)
    except (FileNotFoundError, IsADirectoryError, OSError) as exc:
        raise BundledRosterError(f"{label} is unavailable") from exc
    if len(data) > limit:
        raise BundledRosterError(f"{label} exceeds its packaged size limit")
    return data


def _decode_utf8(data: bytes, *, label: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundledRosterError(f"{label} is not valid UTF-8") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _required_text(entry: Mapping[str, Any], field: str) -> str:
    value = entry.get(field)
    if (
        not isinstance(value, str)
        or not value.strip()
        or _has_unsafe_text(value)
        or len(value.encode("utf-8")) > 16_384
    ):
        raise BundledRosterError(f"bundled roster field {field!r} is invalid")
    return value


def _string_list(entry: Mapping[str, Any], field: str) -> list[str]:
    raw = entry.get(field)
    if (
        not isinstance(raw, list)
        or len(raw) > 128
        or any(
            not isinstance(item, str)
            or not item.strip()
            or _has_unsafe_text(item)
            or len(item.encode("utf-8")) > 2_048
            for item in raw
        )
    ):
        raise BundledRosterError(f"bundled roster list {field!r} is invalid")
    if len(raw) != len(dict.fromkeys(raw)):
        raise BundledRosterError(f"bundled roster list {field!r} contains duplicates")
    return list(raw)


def _validate_routing_contract(result: Mapping[str, Any]) -> None:
    slug = str(result["slug"])
    semantically_required = (
        "categories",
        "capabilities",
        "anti_capabilities",
        "task_types",
        "preferred_when",
        "avoid_when",
        "evidence_requirements",
    )
    if any(not result[field] for field in semantically_required):
        raise BundledRosterError(f"bundled roster routing contract is incomplete for {slug}")
    if result["audit_status"] == "approved" and (
        not result["supported_hosts"] or not result["supported_platforms"]
    ):
        raise BundledRosterError(f"approved bundled agent has no execution target: {slug}")
    if result["context_mode"] == "direct_safe" and result["authority"] in {
        "modify",
        "approve",
    }:
        raise BundledRosterError(f"direct-safe authority is invalid for {slug}")


def _validate_source(source: object) -> dict[str, str]:
    if not isinstance(source, dict) or set(source) != _SOURCE_FIELDS:
        raise BundledRosterError("bundled roster source provenance is invalid")
    required = ("repository", "revision", "license", "license_file", "license_hash")
    result = {field: _required_text(source, field) for field in required}
    if not _SOURCE_REVISION.fullmatch(result["revision"]):
        raise BundledRosterError("bundled roster source revision is invalid")
    if not _SHA256.fullmatch(result["license_hash"]):
        raise BundledRosterError("bundled roster license hash is invalid")
    if result["repository"] != SOURCE_REPOSITORY or result["license"] != SOURCE_LICENSE:
        raise BundledRosterError("bundled roster source provenance is unexpected")
    license_path = _safe_relative_path(result["license_file"], label="bundled roster license")
    if license_path != SOURCE_LICENSE_FILE:
        raise BundledRosterError("bundled roster license path is not canonical")
    license_bytes = _resource(license_path, limit=MAX_LICENSE_BYTES, label="bundled roster license")
    if _sha256(license_bytes) != result["license_hash"]:
        raise BundledRosterError("bundled roster license hash does not match")
    result["license_file"] = license_path
    return result


def _revision_input(
    entry: Mapping[str, Any],
    source: Mapping[str, str],
    *,
    prompt_body: str,
    content_hash: str,
) -> dict[str, Any]:
    return {
        **entry,
        "name": entry["display_name"],
        "source": source["repository"],
        "prompt_path": (
            f"bundled://agency-agents/{entry['slug']}"
            if entry["audit_status"] == "approved"
            else ""
        ),
        "source_version": entry["source_revision"],
        "tool_affinity": [
            *entry["required_tools"],
            *entry.get("optional_tools", []),
        ],
        "hash": content_hash,
        "content": prompt_body,
    }


def _validate_remediation(entry: Mapping[str, Any], result: dict[str, Any]) -> None:
    raw_receipt = entry.get("remediation")
    if raw_receipt is None:
        return
    slug = str(result["slug"])
    if result["audit_status"] != "approved":
        raise BundledRosterError(f"inactive bundled entry carries remediation: {slug}")
    contract = contract_for_source_hash(str(result["source_content_hash"]))
    if contract is None:
        raise BundledRosterError(f"remediation source profile is unknown for {slug}")
    comparisons = {
        "relative_path": contract["relative_path"],
        "slug": contract["slug"],
        "display_name": contract["display_name"],
        "division": contract["division"],
        "description": contract["description"],
        **{field: contract[field] for field in _LIST_FIELDS},
        "authority": contract["authority"],
        "context_mode": contract["context_mode"],
        "independence_group": contract["independence_group"],
        "expected_output_contract": contract["expected_output_contract"],
        "source_revision": contract["source_revision"],
        "audit_revision": contract["audit_revision"],
        "audit_status": contract["audit_status"],
    }
    if any(result[field] != expected for field, expected in comparisons.items()):
        raise BundledRosterError(f"remediated contract does not match its registry: {slug}")
    expected_prompt_hash = _sha256(governed_prompt(contract).encode("utf-8"))
    if result["prompt_hash"] != expected_prompt_hash:
        raise BundledRosterError(f"remediated contract prompt does not match for {slug}")
    try:
        receipt = verify_packaged_remediation(
            raw_receipt,
            source_content_hash=result["source_content_hash"],
            executable_contract_hash=result["prompt_hash"],
        )
    except RosterRemediationError as exc:
        raise BundledRosterError(f"remediation receipt is invalid for {slug}") from exc
    if (
        receipt.findings_original != tuple(contract["findings"])
        or receipt.rules[0].findings_resolved != tuple(contract["findings_resolved_by_encoding"])
        or receipt.rules[0].findings_unresolved
        != tuple(contract["findings_resolved_by_projection"])
        or receipt.rules[1].findings_resolved != tuple(contract["findings_resolved_by_projection"])
        or receipt.findings_resolved
        != (
            *contract["findings_resolved_by_encoding"],
            *contract["findings_resolved_by_projection"],
        )
    ):
        raise BundledRosterError(f"remediation findings do not match for {slug}")
    result["remediation"] = receipt.public_dict()


def _optional_tools(entry: Mapping[str, Any], required_tools: list[str]) -> list[str]:
    optional_tools = _string_list(entry, "optional_tools") if "optional_tools" in entry else []
    if set(required_tools) & set(optional_tools):
        raise BundledRosterError("bundled roster required and optional tools overlap")
    return optional_tools


def _validate_agent(entry: object, *, source: Mapping[str, str]) -> dict[str, Any]:
    if (
        not isinstance(entry, dict)
        or not set(entry) >= _AGENT_FIELDS
        or not set(entry) <= _AGENT_FIELDS | _AGENT_OPTIONAL_FIELDS
    ):
        raise BundledRosterError("bundled roster agent entry is invalid")
    result: dict[str, Any] = {field: _required_text(entry, field) for field in _TEXT_FIELDS}
    for field in _LIST_FIELDS:
        result[field] = _string_list(entry, field)
    result["optional_tools"] = _optional_tools(entry, result["required_tools"])

    slug = result["slug"]
    if not _SLUG.fullmatch(slug):
        raise BundledRosterError(f"bundled roster slug is invalid: {slug!r}")
    result["relative_path"] = _safe_relative_path(
        result["relative_path"], label=f"source path for {slug}"
    )
    if result["source_revision"] != source["revision"]:
        raise BundledRosterError(f"source revision does not match for {slug}")
    if not _SHA256.fullmatch(result["source_content_hash"]):
        raise BundledRosterError(f"source content hash is invalid for {slug}")
    if result["audit_status"] not in _STATUS:
        raise BundledRosterError(f"audit status is invalid for {slug}")
    if result["authority"] not in _AUTHORITY:
        raise BundledRosterError(f"authority is invalid for {slug}")
    if result["context_mode"] not in _CONTEXT_MODE:
        raise BundledRosterError(f"context mode is invalid for {slug}")
    if not result["version"].startswith("sha256:") or not _SHA256.fullmatch(
        result["version"].removeprefix("sha256:")
    ):
        raise BundledRosterError(f"immutable version is invalid for {slug}")

    prompt_file = entry.get("prompt_file")
    prompt_hash = entry.get("prompt_hash")
    if result["audit_status"] == "approved":
        if not isinstance(prompt_hash, str) or not _SHA256.fullmatch(prompt_hash):
            raise BundledRosterError(f"prompt hash is invalid for {slug}")
        safe_prompt = _safe_relative_path(prompt_file, label=f"prompt path for {slug}")
        if safe_prompt != f"prompts/{slug}.txt":
            raise BundledRosterError(f"prompt path is not canonical for {slug}")
        result["prompt_file"] = safe_prompt
        result["prompt_hash"] = prompt_hash
    elif prompt_file is not None or prompt_hash is not None:
        raise BundledRosterError(f"inactive bundled entry carries a prompt for {slug}")
    else:
        result["prompt_file"] = None
        result["prompt_hash"] = None
        expected_version = immutable_revision_version(
            _revision_input(
                result,
                source,
                prompt_body="",
                content_hash=result["source_content_hash"],
            )
        )
        if result["version"] != expected_version:
            raise BundledRosterError(f"immutable version does not match for {slug}")
    _validate_remediation(entry, result)
    _validate_routing_contract(result)
    return result


def _validate_relationships(agents: Sequence[Mapping[str, Any]]) -> None:
    by_slug = {str(agent["slug"]): agent for agent in agents}
    for slug, agent in by_slug.items():
        for dependency in (*agent["conflicts_with"], *agent["requires"]):
            if dependency == slug or dependency not in by_slug:
                raise BundledRosterError(f"bundled roster relationship is invalid: {slug}")
        for conflict in agent["conflicts_with"]:
            if slug not in by_slug[conflict]["conflicts_with"]:
                raise BundledRosterError(
                    f"bundled roster conflict is not symmetric: {slug}, {conflict}"
                )
        if agent["audit_status"] == "approved" and any(
            by_slug[required]["audit_status"] != "approved" for required in agent["requires"]
        ):
            raise BundledRosterError(f"approved agent requires an inactive agent: {slug}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(slug: str) -> None:
        if slug in visited or by_slug[slug]["audit_status"] != "approved":
            return
        if slug in visiting:
            raise BundledRosterError(f"bundled roster requirement cycle includes: {slug}")
        visiting.add(slug)
        for required in by_slug[slug]["requires"]:
            visit(required)
        visiting.remove(slug)
        visited.add(slug)

    for slug in by_slug:
        visit(slug)


@lru_cache(maxsize=1)
def _validated_manifest() -> dict[str, Any]:
    manifest_bytes = _resource(_MANIFEST_FILE, limit=MAX_MANIFEST_BYTES, label="roster manifest")
    digest_text = _decode_utf8(
        _resource(_MANIFEST_DIGEST_FILE, limit=128, label="roster manifest digest"),
        label="roster manifest digest",
    ).strip()
    if not _SHA256.fullmatch(digest_text) or _sha256(manifest_bytes) != digest_text:
        raise BundledRosterError("bundled roster manifest digest does not match")
    try:
        manifest = safe_load_bounded_json(
            manifest_bytes,
            maximum_bytes=MAX_MANIFEST_BYTES,
            maximum_depth=12,
            maximum_nodes=100_000,
        )
    except (TypeError, ValueError) as exc:
        raise BundledRosterError("bundled roster manifest is invalid JSON") from exc
    if (
        not isinstance(manifest, dict)
        or set(manifest) != _MANIFEST_FIELDS
        or type(manifest.get("schema_version")) is not int
        or manifest.get("schema_version") != BUNDLED_ROSTER_SCHEMA
    ):
        raise BundledRosterError("bundled roster manifest schema is unsupported")
    source = _validate_source(manifest.get("source"))
    raw_agents = manifest.get("agents")
    if not isinstance(raw_agents, list) or not 1 <= len(raw_agents) <= MAX_BUNDLED_AGENTS:
        raise BundledRosterError("bundled roster agent inventory is invalid")
    agents = [_validate_agent(item, source=source) for item in raw_agents]
    slugs = [item["slug"] for item in agents]
    paths = [item["relative_path"] for item in agents]
    if slugs != sorted(slugs) or len(slugs) != len(set(slugs)):
        raise BundledRosterError("bundled roster slugs must be unique and sorted")
    if len(paths) != len(set(paths)):
        raise BundledRosterError("bundled roster source paths must be unique")
    _validate_relationships(agents)
    counts = manifest.get("counts")
    expected_counts = {
        "total": len(agents),
        "approved": sum(item["audit_status"] == "approved" for item in agents),
        "quarantined": sum(item["audit_status"] == "quarantined" for item in agents),
        "retired": sum(item["audit_status"] == "retired" for item in agents),
    }
    if (
        not isinstance(counts, dict)
        or set(counts) != _COUNT_FIELDS
        or any(type(value) is not int or value < 0 for value in counts.values())
        or counts != expected_counts
    ):
        raise BundledRosterError("bundled roster status counts do not match its inventory")
    for entry in agents:
        if entry["audit_status"] != "approved":
            continue
        prompt_body = _prompt_text(entry["prompt_file"], entry["prompt_hash"])
        if (
            immutable_revision_version(
                _revision_input(
                    entry,
                    source,
                    prompt_body=prompt_body,
                    content_hash=entry["prompt_hash"],
                )
            )
            != entry["version"]
        ):
            raise BundledRosterError(f"immutable version does not match for {entry['slug']}")
    return {**manifest, "source": source, "agents": agents, "counts": expected_counts}


@lru_cache(maxsize=MAX_BUNDLED_AGENTS)
def _prompt_text(relative_path: str, expected_hash: str) -> str:
    data = _resource(relative_path, limit=MAX_PROMPT_BYTES, label="bundled specialist prompt")
    if _sha256(data) != expected_hash:
        raise BundledRosterError("bundled specialist prompt hash does not match")
    prompt = _decode_utf8(data, label="bundled specialist prompt")
    if _has_unsafe_text(prompt, allow_prompt_layout=True):
        raise BundledRosterError(
            "bundled specialist prompt contains unsafe controls or suspicious encoding"
        )
    return prompt


def bundled_manifest() -> dict[str, Any]:
    """Return a defensive copy of the complete approved/quarantined inventory."""

    return copy.deepcopy(_validated_manifest())


def bundled_roster() -> list[dict[str, Any]]:
    """Return every approved specialist with its governed prompt body."""

    manifest = _validated_manifest()
    source = manifest["source"]
    result: list[dict[str, Any]] = []
    for entry in manifest["agents"]:
        if entry["audit_status"] != "approved":
            continue
        prompt_body = _prompt_text(entry["prompt_file"], entry["prompt_hash"])
        agent = {
            "slug": entry["slug"],
            "name": entry["display_name"],
            "division": entry["division"],
            "description": entry["description"],
            "categories": list(entry["categories"]),
            "capabilities": list(entry["capabilities"]),
            "anti_capabilities": list(entry["anti_capabilities"]),
            "task_types": list(entry["task_types"]),
            "preferred_when": list(entry["preferred_when"]),
            "avoid_when": list(entry["avoid_when"]),
            "required_tools": list(entry["required_tools"]),
            "optional_tools": list(entry.get("optional_tools", [])),
            "supported_hosts": list(entry["supported_hosts"]),
            "supported_platforms": list(entry["supported_platforms"]),
            "authority": entry["authority"],
            "context_mode": entry["context_mode"],
            "conflicts_with": list(entry["conflicts_with"]),
            "requires": list(entry["requires"]),
            "independence_group": entry["independence_group"],
            "expected_output_contract": entry["expected_output_contract"],
            "evidence_requirements": list(entry["evidence_requirements"]),
            "model_requirements": list(entry["model_requirements"]),
            "source_revision": entry["source_revision"],
            "source_content_hash": entry["source_content_hash"],
            "audit_revision": entry["audit_revision"],
            "audit_status": entry["audit_status"],
            "findings": list(entry["findings"]),
            "tool_affinity": [
                *entry["required_tools"],
                *entry.get("optional_tools", []),
            ],
            "source": source["repository"],
            "source_id": "agency-agents",
            "source_version": source["revision"],
            "version": entry["version"],
            "hash": entry["prompt_hash"],
            "prompt_path": f"bundled://agency-agents/{entry['slug']}",
            "prompt_body": prompt_body,
        }
        if "remediation" in entry:
            agent["remediation"] = copy.deepcopy(entry["remediation"])
        if (
            immutable_revision_version(
                _revision_input(
                    entry,
                    source,
                    prompt_body=prompt_body,
                    content_hash=entry["prompt_hash"],
                )
            )
            != entry["version"]
        ):
            raise BundledRosterError(f"immutable version does not match for {entry['slug']}")
        result.append(agent)
    return result


@lru_cache(maxsize=1)
def _bundled_contract_index() -> dict[str, tuple[str, dict[str, Any] | None]]:
    approved = {agent["slug"]: agent for agent in bundled_roster()}
    return {
        entry["slug"]: (entry["audit_status"], approved.get(entry["slug"]))
        for entry in _validated_manifest()["agents"]
    }


def verify_bundled_agent_contract(agent: Mapping[str, Any], prompt_body: str) -> bool:
    """Bind a recognized packaged slug to its exact audited prompt and metadata."""

    record = _bundled_contract_index().get(str(agent.get("slug") or ""))
    if record is None:
        return False
    status, canonical = record
    if status != "approved" or canonical is None:
        raise BundledRosterError("inactive bundled specialist cannot be activated directly")
    mismatches = [
        field
        for field, value in canonical.items()
        if field != "prompt_body" and agent.get(field) != value
    ]
    allowed_fields = set(canonical) | {"content"}
    mismatches.extend(
        f"unexpected:{field}"
        for field in sorted(str(field) for field in agent if field not in allowed_fields)
    )
    if prompt_body != canonical["prompt_body"]:
        mismatches.append("prompt_body")
    supplied_content = agent.get("content")
    if supplied_content not in (None, "", canonical["prompt_body"]):
        mismatches.append("content")
    if mismatches:
        raise BundledRosterError(
            "recognized bundled specialist does not match its audited contract: "
            + ", ".join(sorted(set(mismatches)))
        )
    return True


class BundledRoster(Sequence[dict[str, Any]]):
    """List-compatible lazy view used by legacy ``STARTER_ROSTER`` callers."""

    def __len__(self) -> int:
        return int(_validated_manifest()["counts"]["approved"])

    @overload
    def __getitem__(self, index: int) -> dict[str, Any]: ...

    @overload
    def __getitem__(self, index: slice) -> list[dict[str, Any]]: ...

    def __getitem__(self, index: int | slice) -> dict[str, Any] | list[dict[str, Any]]:
        return bundled_roster()[index]

    def __iter__(self) -> Iterator[dict[str, Any]]:
        yield from bundled_roster()


def clear_bundled_roster_cache() -> None:
    """Clear package-resource caches for tests and integrity revalidation."""

    _validated_manifest.cache_clear()
    _prompt_text.cache_clear()
    _bundled_contract_index.cache_clear()


__all__ = [
    "BUNDLED_ROSTER_SCHEMA",
    "MAX_BUNDLED_AGENTS",
    "MAX_LICENSE_BYTES",
    "MAX_MANIFEST_BYTES",
    "MAX_PROMPT_BYTES",
    "SOURCE_LICENSE",
    "SOURCE_LICENSE_FILE",
    "SOURCE_REPOSITORY",
    "BundledRoster",
    "BundledRosterError",
    "bundled_manifest",
    "bundled_roster",
    "clear_bundled_roster_cache",
    "verify_bundled_agent_contract",
]
