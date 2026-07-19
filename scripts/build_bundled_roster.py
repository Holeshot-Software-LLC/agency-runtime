#!/usr/bin/env python3
"""Build or verify the self-contained roster from reviewed upstream definitions."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import unicodedata
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.roster.bundled import (
    BUNDLED_ROSTER_SCHEMA,
    MAX_BUNDLED_AGENTS,
    MAX_LICENSE_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_PROMPT_BYTES,
    SOURCE_LICENSE,
    SOURCE_LICENSE_FILE,
    SOURCE_REPOSITORY,
)
from agency_runtime.core.roster.ingress import download_from_source, parse_agent_file
from agency_runtime.core.roster.remediation import (
    CONTRACT_PROJECTION_RULE_ID,
    CONTRACT_PROJECTION_RULE_REVISION,
    KNOWN_ENCODING_RULE_ID,
    KNOWN_ENCODING_RULE_REVISION,
    RosterRemediationError,
)
from agency_runtime.core.roster.revisions import immutable_revision_version
from agency_runtime.core.roster.semantic_projection import (
    contract_for_source_hash,
    governed_prompt,
    verify_projected_remediation,
)
from agency_runtime.core.roster.source_safety import (
    SUSPICIOUS_ENCODING_FINDING,
    UNSAFE_TEXT_CONTROL_RE,
    scan_source_text,
)

SOURCE_ID = "agency-agents"
OFFICIAL_SOURCE_ORIGIN = f"{SOURCE_REPOSITORY}.git"
DEFAULT_AUDIT_DIR = Path("docs/roster-audit")
AUDIT_MANIFEST_NAME = "audit-manifest.json"
AUDIT_MANIFEST_SCHEMA = 2
MAX_AUDIT_BYTES = 4 * 1024 * 1024
MAX_AUDIT_REVIEW_BYTES = 128 * 1024
MAX_SOURCE_METADATA_BYTES = 64 * 1024
MAX_SOURCE_FILE_BYTES = 512 * 1024
MAX_GIT_OUTPUT_BYTES = 64 * 1024
MAX_CONTRACT_LIST_ITEMS = 32
MAX_CONTRACT_TEXT_BYTES = 4 * 1024
_HEX_40 = re.compile(r"\A[0-9a-f]{40}\Z")
_HEX_64 = re.compile(r"\A[0-9a-f]{64}\Z")
_SAFE_SLUG = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_WINDOWS_DEVICE_STEMS = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{index}" for index in range(1, 10)),
        *(f"lpt{index}" for index in range(1, 10)),
    }
)
_FORBIDDEN_METADATA_MARKERS = (
    "[agency governed specialist contract",
    "[begin ",
    "[end ",
    "system:",
    "assistant:",
    "user:",
)
CONTRACT_LIST_FIELDS = (
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
CONTRACT_TEXT_FIELDS = (
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
    "content_hash",
    "audit_revision",
    "audit_status",
)
CONTRACT_FIELDS = (
    "relative_path",
    "slug",
    "display_name",
    "division",
    "description",
    "categories",
    "capabilities",
    "anti_capabilities",
    "task_types",
    "preferred_when",
    "avoid_when",
    "required_tools",
    "supported_hosts",
    "supported_platforms",
    "authority",
    "context_mode",
    "conflicts_with",
    "requires",
    "independence_group",
    "expected_output_contract",
    "evidence_requirements",
    "model_requirements",
    "source_revision",
    "content_hash",
    "audit_revision",
    "audit_status",
    "findings",
)
_AUDIT_MANIFEST_FIELDS = (
    "schema_version",
    "audit_revision",
    "source",
    "expected",
    "enums",
    "nonempty_list_fields",
    "quarantines",
    "remediations",
)


class BundleBuildError(RuntimeError):
    """Raised when source, audit, or generated roster evidence is incomplete."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _metadata_is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _real_directory_chain(path: Path, *, label: str, create: bool = False) -> Path:
    """Validate every ancestor and optionally create missing directories safely."""

    absolute = Path(os.path.abspath(path))
    chain: list[Path] = []
    current = absolute
    while True:
        chain.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent
    for directory in reversed(chain):
        try:
            metadata = os.lstat(directory)
        except FileNotFoundError:
            if not create:
                raise BundleBuildError(f"{label} is unavailable: {directory}") from None
            try:
                directory.mkdir()
                metadata = os.lstat(directory)
            except OSError as exc:
                raise BundleBuildError(f"{label} could not be created: {directory}") from exc
        except OSError as exc:
            raise BundleBuildError(f"{label} could not be inspected: {directory}") from exc
        if _metadata_is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise BundleBuildError(
                f"{label} must not traverse a symlink, junction, or reparse point: {directory}"
            )
    return absolute


def _require_single_link(
    metadata: os.stat_result,
    *,
    label: str,
    path: Path,
    unavailable_ok: bool = False,
) -> None:
    count = int(getattr(metadata, "st_nlink", 0) or 0)
    if count == 0 and unavailable_ok:
        return
    if count != 1:
        raise BundleBuildError(f"{label} must have exactly one hard link: {path}")


def _require_path_single_link(path: Path, *, label: str) -> None:
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BundleBuildError(f"{label} cannot be opened safely: {path}") from exc
    try:
        _require_single_link(os.fstat(descriptor), label=label, path=path)
    finally:
        os.close(descriptor)


def _file_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
    )


def _read_regular_bytes(path: Path, *, maximum_bytes: int, label: str) -> bytes:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise BundleBuildError(f"{label} is unavailable: {path}") from exc
    if _metadata_is_link_or_reparse(before) or not stat.S_ISREG(before.st_mode):
        raise BundleBuildError(f"{label} must be a real regular file: {path}")
    _require_single_link(before, label=label, path=path, unavailable_ok=True)
    if before.st_size > maximum_bytes:
        raise BundleBuildError(f"{label} exceeds {maximum_bytes} bytes: {path}")

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BundleBuildError(f"{label} cannot be opened safely: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if _metadata_is_link_or_reparse(opened) or not stat.S_ISREG(opened.st_mode):
            raise BundleBuildError(f"{label} changed identity before read: {path}")
        _require_single_link(opened, label=label, path=path)
        if _file_fingerprint(opened) != _file_fingerprint(before):
            raise BundleBuildError(f"{label} changed identity before read: {path}")
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(data) > maximum_bytes:
        raise BundleBuildError(f"{label} exceeds {maximum_bytes} bytes: {path}")
    try:
        after = os.lstat(path)
    except OSError as exc:
        raise BundleBuildError(f"{label} changed identity after read: {path}") from exc
    if _file_fingerprint(after) != _file_fingerprint(before):
        raise BundleBuildError(f"{label} changed identity during read: {path}")
    _require_single_link(after, label=label, path=path, unavailable_ok=True)
    return data


def _parse_json(data: bytes, *, path: Path, maximum_bytes: int = MAX_AUDIT_BYTES) -> Any:
    try:
        return safe_load_bounded_json(
            data,
            maximum_bytes=maximum_bytes,
            maximum_depth=16,
            maximum_nodes=150_000,
        )
    except (TypeError, ValueError) as exc:
        raise BundleBuildError(f"audit artifact is invalid JSON: {path}") from exc


def _read_json(path: Path, *, maximum_bytes: int = MAX_AUDIT_BYTES) -> Any:
    data = _read_regular_bytes(path, maximum_bytes=maximum_bytes, label="audit artifact")
    return _parse_json(data, path=path, maximum_bytes=maximum_bytes)


def _require_exact_fields(value: Mapping[str, Any], fields: Sequence[str], *, label: str) -> None:
    actual = tuple(value)
    expected = tuple(fields)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise BundleBuildError(
            f"{label} fields must match the canonical order; missing={missing} extra={extra}"
        )


def _string(
    value: object,
    *,
    label: str,
    maximum_bytes: int = MAX_CONTRACT_TEXT_BYTES,
) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise BundleBuildError(f"{label} must be a non-empty canonical string")
    if len(value.encode("utf-8")) > maximum_bytes:
        raise BundleBuildError(f"{label} exceeds {maximum_bytes} bytes")
    if any(
        char in "\r\n"
        or unicodedata.category(char).startswith("C")
        or unicodedata.category(char) in {"Zl", "Zp"}
        for char in value
    ):
        raise BundleBuildError(f"{label} contains a control or line-separator character")
    lowered = value.casefold()
    if any(marker in lowered for marker in _FORBIDDEN_METADATA_MARKERS):
        raise BundleBuildError(f"{label} contains a reserved prompt section marker")
    return value


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise BundleBuildError(f"{label} must be a list")
    if len(value) > MAX_CONTRACT_LIST_ITEMS:
        raise BundleBuildError(f"{label} exceeds {MAX_CONTRACT_LIST_ITEMS} items")
    result = [_string(item, label=label) for item in value]
    if len(result) != len({item.casefold() for item in result}):
        raise BundleBuildError(f"{label} contains duplicates")
    return result


def _integer(value: object, *, label: str, maximum: int = MAX_BUNDLED_AGENTS) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise BundleBuildError(f"{label} must be an integer from 0 through {maximum}")
    return value


def _count_mapping(value: object, *, label: str) -> dict[str, int]:
    if not isinstance(value, dict) or not value:
        raise BundleBuildError(f"{label} must be a non-empty object")
    result: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        key = _string(raw_key, label=f"{label} key")
        if not _SAFE_SLUG.fullmatch(key):
            raise BundleBuildError(f"{label} contains an invalid key: {key}")
        result[key] = _integer(raw_count, label=f"{label}:{key}")
    return result


def _hex_digest(value: object, *, label: str, pattern: re.Pattern[str]) -> str:
    text = _string(value, label=label)
    if not pattern.fullmatch(text):
        raise BundleBuildError(f"{label} must be a lowercase hexadecimal digest")
    return text


def _normalize_manifest_source(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise BundleBuildError("audit manifest source must be an object")
    _require_exact_fields(
        raw,
        (
            "repository",
            "origin",
            "revision",
            "division_manifest",
            "division_manifest_sha256",
        ),
        label="audit manifest source",
    )
    repository = _string(raw["repository"], label="source repository")
    origin = _string(raw["origin"], label="source origin")
    if repository != SOURCE_REPOSITORY or origin != OFFICIAL_SOURCE_ORIGIN:
        raise BundleBuildError("audit manifest must bind the official agency-agents origin")
    division_manifest = _safe_source_path(raw["division_manifest"])
    if division_manifest != "divisions.json":
        raise BundleBuildError("audit manifest must bind source divisions.json")
    return {
        "repository": repository,
        "origin": origin,
        "revision": _hex_digest(raw["revision"], label="source revision", pattern=_HEX_40),
        "division_manifest": division_manifest,
        "division_manifest_sha256": _hex_digest(
            raw["division_manifest_sha256"],
            label="division manifest hash",
            pattern=_HEX_64,
        ),
    }


def _normalize_manifest_batch(filename: str, raw: object) -> dict[str, Any]:
    if not re.fullmatch(r"batch-[a-z0-9-]+\.json", filename):
        raise BundleBuildError(f"invalid audit batch filename: {filename}")
    if not isinstance(raw, dict):
        raise BundleBuildError(f"audit batch descriptor must be an object: {filename}")
    _require_exact_fields(
        raw,
        ("count", "division_counts", "review", "artifact_sha256", "review_sha256"),
        label=f"audit batch {filename}",
    )
    count = _integer(raw["count"], label=f"{filename} count")
    divisions = _count_mapping(raw["division_counts"], label=f"{filename} division counts")
    if count == 0 or sum(divisions.values()) != count:
        raise BundleBuildError(f"audit batch count does not match divisions: {filename}")
    review = _string(raw["review"], label=f"{filename} review")
    if review != f"{filename.removesuffix('.json')}-review.md":
        raise BundleBuildError(f"audit batch review filename is not canonical: {filename}")
    return {
        "count": count,
        "division_counts": divisions,
        "review": review,
        "artifact_sha256": _hex_digest(
            raw["artifact_sha256"], label=f"{filename} artifact hash", pattern=_HEX_64
        ),
        "review_sha256": _hex_digest(
            raw["review_sha256"], label=f"{filename} review hash", pattern=_HEX_64
        ),
    }


def _normalize_manifest_expected(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BundleBuildError("audit manifest expected contract must be an object")
    _require_exact_fields(
        raw,
        ("total_agents", "status_counts", "division_counts", "batches"),
        label="audit manifest expected contract",
    )
    total = _integer(raw["total_agents"], label="expected agent total")
    if total == 0:
        raise BundleBuildError("expected agent total must be positive")
    statuses = _count_mapping(raw["status_counts"], label="expected status counts")
    divisions = _count_mapping(raw["division_counts"], label="expected division counts")
    raw_batches = raw["batches"]
    if not isinstance(raw_batches, dict) or not 1 <= len(raw_batches) <= 16:
        raise BundleBuildError("audit manifest batches must be a bounded non-empty object")
    batches = {
        _string(filename, label="audit batch filename"): _normalize_manifest_batch(
            _string(filename, label="audit batch filename"), descriptor
        )
        for filename, descriptor in raw_batches.items()
    }
    aggregate: Counter[str] = Counter()
    for batch in batches.values():
        aggregate.update(batch["division_counts"])
    if sum(batch["count"] for batch in batches.values()) != total:
        raise BundleBuildError("audit batch totals do not match expected agent total")
    if dict(sorted(aggregate.items())) != divisions:
        raise BundleBuildError("audit batch divisions do not match expected division counts")
    if sum(statuses.values()) != total:
        raise BundleBuildError("expected status counts do not match expected agent total")
    return {
        "total_agents": total,
        "status_counts": statuses,
        "division_counts": divisions,
        "batches": batches,
    }


def _normalize_manifest_enums(raw: object, statuses: Mapping[str, int]) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        raise BundleBuildError("audit manifest enums must be an object")
    _require_exact_fields(
        raw,
        ("authority", "context_mode", "audit_status", "supported_hosts", "supported_platforms"),
        label="audit manifest enums",
    )
    enums = {key: _strings(value, label=f"audit enum {key}") for key, value in raw.items()}
    required = {
        "authority": {"advise", "plan", "modify", "review", "approve"},
        "context_mode": {"direct_safe", "isolated_only"},
        "audit_status": {"approved", "quarantined", "retired"},
        "supported_hosts": {"codex", "claude", "openclaw", "hermes"},
        "supported_platforms": {"windows", "linux"},
    }
    for field, values in required.items():
        if set(enums[field]) != values:
            raise BundleBuildError(f"audit {field} enum does not match the runtime contract")
    if not set(statuses).issubset(enums["audit_status"]):
        raise BundleBuildError("expected status counts contain an unsupported status")
    return enums


def _normalize_manifest_control(relative_path: str, index: int, raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise BundleBuildError(f"{relative_path}:unsafe control must be an object")
    _require_exact_fields(
        raw,
        ("codepoint", "byte_offsets"),
        label=f"{relative_path}:unsafe control {index}",
    )
    codepoint = _string(raw["codepoint"], label=f"{relative_path}:codepoint")
    if not re.fullmatch(r"U\+[0-9A-F]{4,6}", codepoint):
        raise BundleBuildError(f"{relative_path}:invalid unsafe-control codepoint")
    raw_offsets = raw["byte_offsets"]
    if not isinstance(raw_offsets, list) or not raw_offsets:
        raise BundleBuildError(f"{relative_path}:byte_offsets must be non-empty")
    offsets = [
        _integer(item, label=f"{relative_path}:byte offset", maximum=MAX_SOURCE_FILE_BYTES)
        for item in raw_offsets
    ]
    if offsets != sorted(set(offsets)):
        raise BundleBuildError(f"{relative_path}:byte offsets must be unique and sorted")
    return {"codepoint": codepoint, "byte_offsets": offsets}


def _normalize_manifest_quarantines(raw: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > MAX_BUNDLED_AGENTS:
        raise BundleBuildError("audit quarantines must be a bounded list")
    quarantines: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BundleBuildError(f"audit quarantine {index} must be an object")
        _require_exact_fields(
            item,
            ("relative_path", "findings", "unsafe_controls", "ingress_finding"),
            label=f"audit quarantine {index}",
        )
        relative_path = _safe_source_path(item["relative_path"])
        if relative_path in quarantines:
            raise BundleBuildError(f"duplicate audit quarantine path: {relative_path}")
        ingress_finding = _string(item["ingress_finding"], label=f"{relative_path}:ingress finding")
        raw_controls = item["unsafe_controls"]
        if (
            not isinstance(raw_controls, list)
            or len(raw_controls) > 16
            or (not raw_controls and ingress_finding != SUSPICIOUS_ENCODING_FINDING)
        ):
            raise BundleBuildError(f"{relative_path}:unsafe_controls must be a bounded list")
        quarantines[relative_path] = {
            "relative_path": relative_path,
            "findings": _strings(item["findings"], label=f"{relative_path}:findings"),
            "unsafe_controls": [
                _normalize_manifest_control(relative_path, control_index, control)
                for control_index, control in enumerate(raw_controls)
            ],
            "ingress_finding": ingress_finding,
        }
    return quarantines


def _normalize_manifest_remediations(raw: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > MAX_BUNDLED_AGENTS:
        raise BundleBuildError("audit remediations must be a bounded list")
    remediations: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BundleBuildError(f"audit remediation {index} must be an object")
        _require_exact_fields(
            item,
            (
                "relative_path",
                "original_hash",
                "encoding_repaired_hash",
                "encoding_rule",
                "projection_rule",
                "findings_original",
                "findings_resolved_by_encoding",
                "findings_resolved_by_projection",
                "findings_unresolved",
            ),
            label=f"audit remediation {index}",
        )
        relative_path = _safe_source_path(item["relative_path"])
        if relative_path in remediations:
            raise BundleBuildError(f"duplicate audit remediation path: {relative_path}")
        encoding_rule = _strings(item["encoding_rule"], label=f"{relative_path}:encoding rule")
        projection_rule = _strings(
            item["projection_rule"], label=f"{relative_path}:projection rule"
        )
        if encoding_rule != [KNOWN_ENCODING_RULE_ID, KNOWN_ENCODING_RULE_REVISION]:
            raise BundleBuildError(f"{relative_path}:encoding remediation rule is unsupported")
        if projection_rule != [
            CONTRACT_PROJECTION_RULE_ID,
            CONTRACT_PROJECTION_RULE_REVISION,
        ]:
            raise BundleBuildError(f"{relative_path}:projection remediation rule is unsupported")
        findings_original = _strings(
            item["findings_original"], label=f"{relative_path}:original findings"
        )
        encoding_resolved = _strings(
            item["findings_resolved_by_encoding"],
            label=f"{relative_path}:encoding-resolved findings",
        )
        projection_resolved = _strings(
            item["findings_resolved_by_projection"],
            label=f"{relative_path}:projection-resolved findings",
        )
        unresolved = _strings(
            item["findings_unresolved"], label=f"{relative_path}:unresolved findings"
        )
        if (
            set(encoding_resolved) & set(projection_resolved)
            or (set(encoding_resolved) | set(projection_resolved) | set(unresolved))
            != set(findings_original)
            or set(unresolved) & (set(encoding_resolved) | set(projection_resolved))
        ):
            raise BundleBuildError(f"{relative_path}:remediation findings are inconsistent")
        remediations[relative_path] = {
            "relative_path": relative_path,
            "original_hash": _hex_digest(
                item["original_hash"], label=f"{relative_path}:original hash", pattern=_HEX_64
            ),
            "encoding_repaired_hash": _hex_digest(
                item["encoding_repaired_hash"],
                label=f"{relative_path}:encoding-repaired hash",
                pattern=_HEX_64,
            ),
            "encoding_rule": encoding_rule,
            "projection_rule": projection_rule,
            "findings_original": findings_original,
            "findings_resolved_by_encoding": encoding_resolved,
            "findings_resolved_by_projection": projection_resolved,
            "findings_unresolved": unresolved,
        }
    return remediations


def _load_audit_manifest(audit_dir: Path) -> dict[str, Any]:
    path = audit_dir / AUDIT_MANIFEST_NAME
    parsed = _read_json(path)
    if not isinstance(parsed, dict):
        raise BundleBuildError(f"audit manifest must be an object: {path}")
    _require_exact_fields(parsed, _AUDIT_MANIFEST_FIELDS, label="audit manifest")
    schema = _integer(parsed["schema_version"], label="audit manifest schema", maximum=100)
    if schema != AUDIT_MANIFEST_SCHEMA:
        raise BundleBuildError(f"unsupported audit manifest schema: {schema}")
    expected = _normalize_manifest_expected(parsed["expected"])
    enums = _normalize_manifest_enums(parsed["enums"], expected["status_counts"])
    nonempty = _strings(parsed["nonempty_list_fields"], label="nonempty list fields")
    optional = {
        "required_tools",
        "supported_hosts",
        "supported_platforms",
        "conflicts_with",
        "requires",
    }
    if nonempty != [field for field in CONTRACT_LIST_FIELDS if field not in optional]:
        raise BundleBuildError("nonempty list fields do not match the routing contract")
    return {
        "schema_version": schema,
        "audit_revision": _string(parsed["audit_revision"], label="audit revision"),
        "source": _normalize_manifest_source(parsed["source"]),
        "expected": expected,
        "enums": enums,
        "nonempty_list_fields": nonempty,
        "quarantines": _normalize_manifest_quarantines(parsed["quarantines"]),
        "remediations": _normalize_manifest_remediations(parsed["remediations"]),
    }


def _run_git(source: Path, arguments: Sequence[str], *, label: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(source), *arguments],
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BundleBuildError(f"cannot inspect source Git {label}") from exc
    if len(completed.stdout) > MAX_GIT_OUTPUT_BYTES or len(completed.stderr) > MAX_GIT_OUTPUT_BYTES:
        raise BundleBuildError(f"source Git {label} output exceeds the safety bound")
    if completed.returncode != 0:
        raise BundleBuildError(f"source Git {label} inspection failed")
    return completed.stdout


def _single_git_line(source: Path, arguments: Sequence[str], *, label: str) -> str:
    try:
        text = _run_git(source, arguments, label=label).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleBuildError(f"source Git {label} is not UTF-8") from exc
    lines = text.splitlines()
    if len(lines) != 1 or text not in {lines[0], f"{lines[0]}\n", f"{lines[0]}\r\n"}:
        raise BundleBuildError(f"source Git {label} must be one canonical line")
    return _string(lines[0], label=f"source Git {label}")


def _canonical_lf_text_bytes(
    data: bytes,
    *,
    label: str,
    maximum_bytes: int = MAX_LICENSE_BYTES,
) -> bytes:
    """Return deterministic UTF-8/LF package bytes for a tracked text artifact."""

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleBuildError(f"{label} is not UTF-8") from exc
    if "\x00" in text:
        raise BundleBuildError(f"{label} contains a NUL byte")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    if not canonical or len(canonical) > maximum_bytes:
        raise BundleBuildError(f"{label} is empty or exceeds the package limit")
    return canonical


def _audit_text_sha256(data: bytes, *, label: str, maximum_bytes: int) -> str:
    """Hash one reviewed audit text artifact after canonical LF normalization."""

    return _sha256(
        _canonical_lf_text_bytes(
            data,
            label=label,
            maximum_bytes=maximum_bytes,
        )
    )


def _canonical_upstream_license(source: Path, revision: str) -> bytes:
    """Read the immutable Git blob and canonicalize package line endings."""

    license_path = source / "LICENSE"
    try:
        license_path.relative_to(source)
    except ValueError as exc:
        raise BundleBuildError("upstream license escaped the pinned checkout") from exc
    _real_directory_chain(license_path.parent, label="upstream license parent")
    _read_regular_bytes(
        license_path,
        maximum_bytes=MAX_LICENSE_BYTES,
        label="upstream license",
    )
    blob = _run_git(
        source,
        ("cat-file", "blob", f"{revision}:LICENSE"),
        label="license blob",
    )
    return _canonical_lf_text_bytes(blob, label="upstream license blob")


def _validate_source_checkout(source: Path, audit: Mapping[str, Any]) -> str:
    source = _real_directory_chain(source, label="source checkout")
    revision = _single_git_line(
        source,
        ("rev-parse", "--verify", "HEAD^{commit}"),
        label="revision",
    ).casefold()
    if not _HEX_40.fullmatch(revision) or revision != audit["source"]["revision"]:
        raise BundleBuildError("source checkout revision does not match the tracked audit")
    origin = _single_git_line(
        source,
        ("config", "--get", "remote.origin.url"),
        label="origin",
    )
    if origin != audit["source"]["origin"] or origin != OFFICIAL_SOURCE_ORIGIN:
        raise BundleBuildError("source checkout origin does not match the official audited remote")
    status = _run_git(
        source,
        ("status", "--porcelain=v1", "--untracked-files=all"),
        label="cleanliness",
    )
    if status:
        raise BundleBuildError("source checkout must be clean at the audited revision")
    return revision


def _safe_source_path(value: object) -> str:
    text = _string(value, label="audit relative_path")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or "\\" in text
        or any(
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_STEMS
            for part in path.parts
        )
    ):
        raise BundleBuildError(f"unsafe audit relative_path: {text!r}")
    return path.as_posix()


def _resolve_audit_directory(audit_dir: Path) -> Path:
    return _real_directory_chain(audit_dir, label="audit directory")


def _validate_audit_file_set(audit_dir: Path, batches: Mapping[str, Mapping[str, Any]]) -> None:
    expected_artifacts = set(batches)
    expected_reviews = {batch["review"] for batch in batches.values()}
    actual_artifacts = {path.name for path in audit_dir.glob("batch-*.json")}
    actual_reviews = {path.name for path in audit_dir.glob("batch-*-review.md")}
    for label, actual, expected in (
        ("batch", actual_artifacts, expected_artifacts),
        ("review", actual_reviews, expected_reviews),
    ):
        if actual != expected:
            raise BundleBuildError(
                f"audit {label} files do not match the tracked manifest; "
                f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
            )


def _read_audit_batch(
    audit_dir: Path,
    filename: str,
    batch: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    artifact = audit_dir / filename
    artifact_bytes = _read_regular_bytes(
        artifact,
        maximum_bytes=MAX_AUDIT_BYTES,
        label="audit batch",
    )
    if (
        _audit_text_sha256(
            artifact_bytes,
            label="audit batch",
            maximum_bytes=MAX_AUDIT_BYTES,
        )
        != batch["artifact_sha256"]
    ):
        raise BundleBuildError(f"audit batch hash does not match manifest: {filename}")
    review_bytes = _read_regular_bytes(
        audit_dir / batch["review"],
        maximum_bytes=MAX_AUDIT_REVIEW_BYTES,
        label="audit review",
    )
    if (
        _audit_text_sha256(
            review_bytes,
            label="audit review",
            maximum_bytes=MAX_AUDIT_REVIEW_BYTES,
        )
        != batch["review_sha256"]
    ):
        raise BundleBuildError(f"audit review hash does not match manifest: {batch['review']}")
    parsed = _parse_json(artifact_bytes, path=artifact)
    if not isinstance(parsed, list) or not parsed:
        raise BundleBuildError(f"audit artifact must be a non-empty list: {artifact}")
    if len(parsed) != batch["count"] or any(not isinstance(item, dict) for item in parsed):
        raise BundleBuildError(f"audit batch shape or count does not match manifest: {filename}")
    return parsed


def _validate_contract_identity(contract: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    relative_path = contract["relative_path"]
    for field in ("slug", "division"):
        if not _SAFE_SLUG.fullmatch(contract[field]):
            raise BundleBuildError(f"audit {field} is not canonical: {contract[field]}")
    if PurePosixPath(relative_path).parts[0] != contract["division"]:
        raise BundleBuildError(f"audit path and division disagree: {relative_path}")
    if contract["source_revision"] != manifest["source"]["revision"]:
        raise BundleBuildError(f"source revision does not match manifest: {relative_path}")
    if not _HEX_64.fullmatch(contract["content_hash"]):
        raise BundleBuildError(f"source hash is not canonical: {relative_path}")
    if not re.fullmatch(r"[1-9][0-9]{0,5}", contract["audit_revision"]):
        raise BundleBuildError(f"audit revision is invalid: {relative_path}")
    if int(contract["audit_revision"]) > int(manifest["audit_revision"]):
        raise BundleBuildError(f"audit revision exceeds the manifest: {relative_path}")


def _validate_contract_values(contract: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    relative_path = contract["relative_path"]
    for field in ("authority", "context_mode", "audit_status"):
        if contract[field] not in manifest["enums"][field]:
            raise BundleBuildError(f"unsupported {field} for {relative_path}")
    for field in ("supported_hosts", "supported_platforms"):
        unsupported = set(contract[field]) - set(manifest["enums"][field])
        if unsupported:
            raise BundleBuildError(
                f"unsupported {field} for {relative_path}: {sorted(unsupported)}"
            )
    slug_lists = (
        "categories",
        "required_tools",
        "supported_hosts",
        "supported_platforms",
        "conflicts_with",
        "requires",
        "model_requirements",
    )
    for field in slug_lists:
        if any(not _SAFE_SLUG.fullmatch(item) for item in contract[field]):
            raise BundleBuildError(f"{relative_path}:{field} contains a noncanonical value")
    for field in manifest["nonempty_list_fields"]:
        if not contract[field]:
            raise BundleBuildError(f"{relative_path}:{field} must be semantically non-empty")


def _validate_contract_execution(contract: Mapping[str, Any]) -> None:
    relative_path = contract["relative_path"]
    if contract["context_mode"] == "direct_safe" and (
        contract["required_tools"] or contract["authority"] in {"modify", "approve"}
    ):
        raise BundleBuildError(
            f"direct-safe agent requires tools or mutating authority: {relative_path}"
        )
    if contract["audit_status"] == "approved":
        if not contract["supported_hosts"] or not contract["supported_platforms"]:
            raise BundleBuildError(
                f"approved agent has no execution compatibility: {relative_path}"
            )
    elif (
        contract["supported_hosts"]
        or contract["supported_platforms"]
        or contract["context_mode"] != "isolated_only"
    ):
        raise BundleBuildError(f"inactive agent must be isolated and unroutable: {relative_path}")


def _normalize_audit_contract(
    raw: Mapping[str, Any],
    *,
    filename: str,
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    _require_exact_fields(raw, CONTRACT_FIELDS, label=f"audit entry in {filename}")
    contract = {
        field: _string(raw[field], label=f"{filename}:{field}") for field in CONTRACT_TEXT_FIELDS
    }
    contract["relative_path"] = _safe_source_path(contract["relative_path"])
    for field in CONTRACT_LIST_FIELDS:
        contract[field] = _strings(raw[field], label=f"{contract['relative_path']}:{field}")
    _validate_contract_identity(contract, manifest)
    _validate_contract_values(contract, manifest)
    _validate_contract_execution(contract)
    return contract


def _validate_audit_totals(
    contracts: Mapping[str, Mapping[str, Any]],
    divisions: Counter[str],
    statuses: Counter[str],
    manifest: Mapping[str, Any],
) -> None:
    expected = manifest["expected"]
    if len(contracts) != expected["total_agents"]:
        raise BundleBuildError("audit entries do not match expected agent total")
    if dict(sorted(divisions.items())) != expected["division_counts"]:
        raise BundleBuildError("audit divisions do not match the tracked manifest")
    if dict(sorted(statuses.items())) != expected["status_counts"]:
        raise BundleBuildError("audit statuses do not match the tracked manifest")
    quarantined = {
        path for path, contract in contracts.items() if contract["audit_status"] == "quarantined"
    }
    if quarantined != set(manifest["quarantines"]):
        raise BundleBuildError("quarantined audit entries do not match the tracked manifest")
    for relative_path in quarantined:
        if (
            contracts[relative_path]["findings"]
            != manifest["quarantines"][relative_path]["findings"]
        ):
            raise BundleBuildError(f"quarantine findings do not match manifest: {relative_path}")
    remediated = set(manifest["remediations"])
    if remediated & quarantined or not remediated.issubset(contracts):
        raise BundleBuildError("remediated audit entries have invalid lifecycle status")
    for relative_path in remediated:
        contract = contracts[relative_path]
        remediation = manifest["remediations"][relative_path]
        if (
            contract["audit_status"] != "approved"
            or contract["audit_revision"] != manifest["audit_revision"]
            or contract["content_hash"] != remediation["original_hash"]
            or contract["findings"] != remediation["findings_original"]
        ):
            raise BundleBuildError(
                f"remediated audit contract does not match its evidence: {relative_path}"
            )


def _load_audits(
    audit_dir: Path,
    audit: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    audit_dir = _resolve_audit_directory(audit_dir)
    manifest = dict(audit or _load_audit_manifest(audit_dir))
    batches = manifest["expected"]["batches"]
    _validate_audit_file_set(audit_dir, batches)
    contracts: dict[str, dict[str, Any]] = {}
    slugs: set[str] = set()
    divisions: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for filename, batch in batches.items():
        batch_divisions: Counter[str] = Counter()
        for raw in _read_audit_batch(audit_dir, filename, batch):
            contract = _normalize_audit_contract(raw, filename=filename, manifest=manifest)
            relative_path = contract["relative_path"]
            if relative_path in contracts or contract["slug"] in slugs:
                raise BundleBuildError(f"duplicate audited path or slug: {relative_path}")
            contracts[relative_path] = contract
            slugs.add(contract["slug"])
            batch_divisions[contract["division"]] += 1
            divisions[contract["division"]] += 1
            statuses[contract["audit_status"]] += 1
            if len(contracts) > MAX_BUNDLED_AGENTS:
                raise BundleBuildError(
                    f"audited roster exceeds the {MAX_BUNDLED_AGENTS}-agent package limit"
                )
        if dict(sorted(batch_divisions.items())) != batch["division_counts"]:
            raise BundleBuildError(f"audit batch divisions do not match manifest: {filename}")
    _validate_audit_totals(contracts, divisions, statuses, manifest)
    return contracts


def _source_inventory(source: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    downloaded = download_from_source(str(source))
    candidates: dict[str, dict[str, Any]] = {}
    for candidate in downloaded:
        prompt_path = Path(str(candidate["prompt_path"])).resolve(strict=True)
        try:
            relative_path = prompt_path.relative_to(source).as_posix()
        except ValueError as exc:
            raise BundleBuildError("parsed source prompt escaped the pinned checkout") from exc
        if relative_path in candidates:
            raise BundleBuildError(
                f"source inventory contains duplicate candidate: {relative_path}"
            )
        candidates[relative_path] = dict(candidate)
    outcomes = {outcome.relative_path: outcome for outcome in downloaded.outcomes}
    if len(outcomes) != len(downloaded.outcomes):
        raise BundleBuildError("source inventory contains duplicate relative paths")
    return candidates, outcomes


def _tracked_source_paths(source: Path) -> set[str]:
    data = _run_git(source, ("ls-files", "-z"), label="tracked-file inventory")
    try:
        paths = data.decode("utf-8").split("\0")
    except UnicodeDecodeError as exc:
        raise BundleBuildError("source tracked-file inventory is not UTF-8") from exc
    if paths and paths[-1] == "":
        paths.pop()
    if not paths or len(paths) != len(set(paths)):
        raise BundleBuildError("source tracked-file inventory is empty or contains duplicates")
    return {_safe_source_path(path) for path in paths}


def _validate_division_manifest(source: Path, audit: Mapping[str, Any]) -> None:
    relative_path = audit["source"]["division_manifest"]
    data = _read_regular_bytes(
        source / PurePosixPath(relative_path),
        maximum_bytes=MAX_SOURCE_METADATA_BYTES,
        label="source division manifest",
    )
    if _sha256(data) != audit["source"]["division_manifest_sha256"]:
        raise BundleBuildError("source division manifest hash does not match the tracked audit")
    parsed = _parse_json(
        data,
        path=source / PurePosixPath(relative_path),
        maximum_bytes=MAX_SOURCE_METADATA_BYTES,
    )
    if not isinstance(parsed, dict) or not isinstance(parsed.get("divisions"), dict):
        raise BundleBuildError("source division manifest must declare a divisions object")
    actual_divisions = set(parsed["divisions"])
    expected_divisions = set(audit["expected"]["division_counts"])
    if actual_divisions != expected_divisions:
        raise BundleBuildError(
            "source manifest divisions do not match the tracked audit; "
            f"missing={sorted(expected_divisions - actual_divisions)} "
            f"extra={sorted(actual_divisions - expected_divisions)}"
        )


def _unsafe_source_controls(data: bytes, *, relative_path: str) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BundleBuildError(f"source definition is not UTF-8: {relative_path}") from exc
    return [control.public_dict() for control in scan_source_text(text).controls]


def _source_identity(
    raw: bytes,
    *,
    relative_path: str,
    candidate: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if candidate is not None:
        return candidate
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - checked by control scanner
        raise BundleBuildError(f"source definition is not UTF-8: {relative_path}") from exc
    cleaned = UNSAFE_TEXT_CONTROL_RE.sub("", text)
    try:
        return parse_agent_file(
            cleaned,
            inferred_division=PurePosixPath(relative_path).parts[0],
        )
    except (TypeError, ValueError) as exc:
        raise BundleBuildError(
            f"cannot verify quarantined source identity: {relative_path}"
        ) from exc


def _validate_inventory_sets(
    source: Path,
    audit: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Any],
) -> None:
    if set(contracts) != set(outcomes):
        missing = sorted(set(outcomes) - set(contracts))
        extra = sorted(set(contracts) - set(outcomes))
        raise BundleBuildError(
            "audit/source path mismatch; "
            f"missing_count={len(missing)} missing_sample={missing[:20]}; "
            f"extra_count={len(extra)} extra_sample={extra[:20]}"
        )
    _validate_division_manifest(source, audit)
    tracked = _tracked_source_paths(source)
    required = {"LICENSE", audit["source"]["division_manifest"], *contracts}
    if not required.issubset(tracked):
        raise BundleBuildError(
            f"audited source contains untracked evidence: {sorted(required - tracked)[:20]}"
        )


def _read_source_definition(source: Path, relative_path: str) -> bytes:
    root = Path(os.path.abspath(source))
    candidate_path = root.joinpath(*PurePosixPath(relative_path).parts)
    try:
        candidate_path.relative_to(root)
    except ValueError as exc:
        raise BundleBuildError(f"audited source escaped checkout: {relative_path}") from exc
    _real_directory_chain(candidate_path.parent, label="audited source parent")
    return _read_regular_bytes(
        candidate_path,
        maximum_bytes=MAX_SOURCE_FILE_BYTES,
        label="audited source definition",
    )


def _validate_quarantine_evidence(
    raw: bytes,
    *,
    relative_path: str,
    contract: Mapping[str, Any],
    outcome: Any,
    expected: Mapping[str, Any] | None,
) -> None:
    controls = _unsafe_source_controls(raw, relative_path=relative_path)
    try:
        scan = scan_source_text(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:  # pragma: no cover - control helper fails first
        raise BundleBuildError(f"source definition is not UTF-8: {relative_path}") from exc
    if expected is None:
        if controls or scan.suspicious_encoding:
            raise BundleBuildError(
                f"source contains unaudited encoding evidence: {relative_path} {controls}"
            )
        return
    if contract["audit_status"] != "quarantined":
        raise BundleBuildError(f"unsafe-control source is not quarantined: {relative_path}")
    if controls != expected["unsafe_controls"]:
        raise BundleBuildError(
            f"unsafe-control byte evidence does not match audit: {relative_path}"
        )
    if not controls and (
        expected["ingress_finding"] != SUSPICIOUS_ENCODING_FINDING or not scan.suspicious_encoding
    ):
        raise BundleBuildError(
            f"suspicious-encoding evidence does not match audit: {relative_path}"
        )
    if outcome.status != "quarantined" or outcome.finding != expected["ingress_finding"]:
        raise BundleBuildError(f"ingress quarantine evidence does not match audit: {relative_path}")


def _validate_remediation_evidence(
    raw: bytes,
    *,
    relative_path: str,
    contract: dict[str, Any],
    candidate: Mapping[str, Any] | None,
    outcome: Any,
    expected: Mapping[str, Any],
) -> None:
    if candidate is None or outcome.status != "candidate" or outcome.remediation is None:
        raise BundleBuildError(f"remediated source did not produce a candidate: {relative_path}")
    try:
        original = raw.decode("utf-8")
        receipt = verify_projected_remediation(
            original,
            str(candidate.get("content") or ""),
            outcome.remediation,
            relative_path=relative_path,
        )
    except (UnicodeDecodeError, RosterRemediationError) as exc:
        raise BundleBuildError(f"remediated source evidence is invalid: {relative_path}") from exc
    registered = contract_for_source_hash(contract["content_hash"])
    if registered is None:
        raise BundleBuildError(f"remediated source has no contract registry entry: {relative_path}")
    comparable_fields = (*CONTRACT_FIELDS,)
    if any(registered.get(field) != contract.get(field) for field in comparable_fields):
        raise BundleBuildError(f"remediated audit and runtime contract disagree: {relative_path}")
    if (
        expected["original_hash"] != receipt.original_hash
        or expected["encoding_repaired_hash"] != receipt.rules[0].after_hash
        or expected["encoding_rule"] != [receipt.rules[0].rule_id, receipt.rules[0].rule_revision]
        or expected["projection_rule"]
        != [receipt.rules[-1].rule_id, receipt.rules[-1].rule_revision]
        or expected["findings_original"] != list(receipt.findings_original)
        or expected["findings_resolved_by_encoding"] != list(receipt.rules[0].findings_resolved)
        or expected["findings_resolved_by_projection"] != list(receipt.rules[-1].findings_resolved)
        or expected["findings_unresolved"] != list(receipt.findings_unresolved)
        or receipt.transformed_hash != _sha256(governed_prompt(contract).encode("utf-8"))
    ):
        raise BundleBuildError(f"remediation receipt does not match audit: {relative_path}")
    contract["remediation"] = receipt.public_dict()


def _validate_source_identity(
    raw: bytes,
    *,
    relative_path: str,
    contract: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
) -> None:
    identity = _source_identity(raw, relative_path=relative_path, candidate=candidate)
    comparisons = {
        "display name": (identity.get("name"), contract["display_name"]),
        "division": (identity.get("division"), contract["division"]),
        "identity slug": (identity.get("slug"), contract["slug"]),
    }
    for label, (actual, expected) in comparisons.items():
        if actual != expected:
            raise BundleBuildError(f"source {label} does not match audit: {relative_path}")


def _validate_source_entry(
    source: Path,
    revision: str,
    audit: Mapping[str, Any],
    relative_path: str,
    contract: Mapping[str, Any],
    candidate: Mapping[str, Any] | None,
    outcome: Any,
) -> None:
    raw = _read_source_definition(source, relative_path)
    if _sha256(raw) != contract["content_hash"]:
        raise BundleBuildError(f"source hash does not match audit for {relative_path}")
    if contract["source_revision"] != revision or outcome.slug != contract["slug"]:
        raise BundleBuildError(f"source revision or slug does not match audit for {relative_path}")
    remediation = audit["remediations"].get(relative_path)
    if remediation is not None:
        _validate_remediation_evidence(
            raw,
            relative_path=relative_path,
            contract=contract,
            candidate=candidate,
            outcome=outcome,
            expected=remediation,
        )
    else:
        _validate_quarantine_evidence(
            raw,
            relative_path=relative_path,
            contract=contract,
            outcome=outcome,
            expected=audit["quarantines"].get(relative_path),
        )
    _validate_source_identity(
        raw,
        relative_path=relative_path,
        contract=contract,
        candidate=candidate,
    )
    if contract["audit_status"] == "approved" and (
        candidate is None or outcome.status != "candidate"
    ):
        raise BundleBuildError(f"approved source did not produce a candidate: {relative_path}")


def _validate_inventory(
    source: Path,
    revision: str,
    audit: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, Any]],
    outcomes: Mapping[str, Any],
) -> None:
    _validate_inventory_sets(source, audit, contracts, outcomes)
    for relative_path, contract in contracts.items():
        _validate_source_entry(
            source,
            revision,
            audit,
            relative_path,
            contract,
            candidates.get(relative_path),
            outcomes[relative_path],
        )


def _governed_prompt(contract: Mapping[str, Any]) -> str:
    """Render only the audited allowlisted specialist contract fields."""

    return governed_prompt(contract)


def _manifest_entry(
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes | None]:
    entry: dict[str, Any] = {
        "relative_path": contract["relative_path"],
        "slug": contract["slug"],
        "display_name": contract["display_name"],
        "division": contract["division"],
        "description": contract["description"],
        **{field: list(contract[field]) for field in CONTRACT_LIST_FIELDS},
        "authority": contract["authority"],
        "context_mode": contract["context_mode"],
        "independence_group": contract["independence_group"],
        "expected_output_contract": contract["expected_output_contract"],
        "source_revision": contract["source_revision"],
        "source_content_hash": contract["content_hash"],
        "audit_revision": contract["audit_revision"],
        "audit_status": contract["audit_status"],
    }
    if "remediation" in contract:
        entry["remediation"] = copy.deepcopy(contract["remediation"])
    if contract["audit_status"] != "approved":
        revision_input = {
            **entry,
            "name": entry["display_name"],
            "source": SOURCE_REPOSITORY,
            "prompt_path": "",
            "source_version": entry["source_revision"],
            "tool_affinity": entry["required_tools"],
            "hash": entry["source_content_hash"],
            "content": "",
        }
        entry.update(
            version=immutable_revision_version(revision_input),
            prompt_file=None,
            prompt_hash=None,
        )
        return entry, None
    prompt = _governed_prompt(contract).encode("utf-8")
    if len(prompt) > MAX_PROMPT_BYTES:
        raise BundleBuildError(f"governed prompt exceeds package limit: {entry['slug']}")
    prompt_hash = _sha256(prompt)
    revision_input = {
        **entry,
        "name": entry["display_name"],
        "source": SOURCE_REPOSITORY,
        "prompt_path": f"bundled://agency-agents/{entry['slug']}",
        "source_version": entry["source_revision"],
        "tool_affinity": entry["required_tools"],
        "hash": prompt_hash,
        "content": prompt.decode("utf-8"),
    }
    entry.update(
        version=immutable_revision_version(revision_input),
        prompt_file=f"prompts/{entry['slug']}.txt",
        prompt_hash=prompt_hash,
    )
    return entry, prompt


def _validate_relationships(entries: Sequence[Mapping[str, Any]]) -> None:
    by_slug = {str(entry["slug"]): entry for entry in entries}
    for slug, entry in by_slug.items():
        for dependency in (*entry["conflicts_with"], *entry["requires"]):
            if dependency == slug or dependency not in by_slug:
                raise BundleBuildError(f"invalid relationship {slug} -> {dependency}")
        for conflict in entry["conflicts_with"]:
            if slug not in by_slug[conflict]["conflicts_with"]:
                raise BundleBuildError(f"conflict must be symmetric: {slug} <-> {conflict}")
        if entry["audit_status"] == "approved" and any(
            by_slug[required]["audit_status"] != "approved" for required in entry["requires"]
        ):
            raise BundleBuildError(f"approved agent requires inactive agent: {slug}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(slug: str) -> None:
        if slug in visited or by_slug[slug]["audit_status"] != "approved":
            return
        if slug in visiting:
            raise BundleBuildError(f"agent requirement cycle includes: {slug}")
        visiting.add(slug)
        for required in by_slug[slug]["requires"]:
            visit(required)
        visiting.remove(slug)
        visited.add(slug)

    for slug in by_slug:
        visit(slug)


def build_bundle(
    source: Path,
    audit_dir: Path = DEFAULT_AUDIT_DIR,
    expected_revision: str = "",
) -> dict[str, bytes]:
    source = source.absolute()
    audit_dir = _resolve_audit_directory(audit_dir)
    audit = _load_audit_manifest(audit_dir)
    revision = _validate_source_checkout(source, audit)
    if expected_revision and expected_revision.casefold() != revision:
        raise BundleBuildError(
            f"source revision {revision} does not match expected {expected_revision}"
        )
    contracts = _load_audits(audit_dir, audit)
    candidates, outcomes = _source_inventory(source)
    _validate_inventory(source, revision, audit, contracts, candidates, outcomes)

    entries: list[dict[str, Any]] = []
    files: dict[str, bytes] = {}
    for _relative_path, contract in sorted(contracts.items(), key=lambda item: item[1]["slug"]):
        entry, prompt = _manifest_entry(contract)
        entries.append(entry)
        if prompt is not None:
            files[str(entry["prompt_file"])] = prompt
    _validate_relationships(entries)

    license_bytes = _canonical_upstream_license(source, revision)
    files[SOURCE_LICENSE_FILE] = license_bytes
    counts = {
        "total": len(entries),
        "approved": sum(entry["audit_status"] == "approved" for entry in entries),
        "quarantined": sum(entry["audit_status"] == "quarantined" for entry in entries),
        "retired": sum(entry["audit_status"] == "retired" for entry in entries),
    }
    expected_counts = {
        "total": audit["expected"]["total_agents"],
        "approved": audit["expected"]["status_counts"].get("approved", 0),
        "quarantined": audit["expected"]["status_counts"].get("quarantined", 0),
        "retired": audit["expected"]["status_counts"].get("retired", 0),
    }
    if counts != expected_counts:
        raise BundleBuildError("generated roster counts do not match the tracked audit")
    manifest = {
        "schema_version": BUNDLED_ROSTER_SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "revision": revision,
            "license": SOURCE_LICENSE,
            "license_file": SOURCE_LICENSE_FILE,
            "license_hash": _sha256(license_bytes),
        },
        "counts": counts,
        "agents": entries,
    }
    manifest_bytes = _canonical_json(manifest)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise BundleBuildError("generated manifest exceeds the package limit")
    files["manifest.json"] = manifest_bytes
    files["manifest.sha256"] = (_sha256(manifest_bytes) + "\n").encode("ascii")
    if _validate_source_checkout(source, audit) != revision:
        raise BundleBuildError("source checkout changed during bundle generation")
    return files


def _output_root(output: Path) -> Path:
    root = Path(os.path.abspath(output))
    try:
        metadata = os.lstat(root)
    except FileNotFoundError:
        return root
    except OSError as exc:
        raise BundleBuildError(f"output directory could not be inspected: {output}") from exc
    if _metadata_is_link_or_reparse(metadata):
        raise BundleBuildError(f"output directory must not be a link or reparse point: {output}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise BundleBuildError(f"output must be a directory: {output}")
    return _real_directory_chain(root, label="output directory")


def _ensure_real_directory(path: Path) -> Path:
    """Create one directory chain without traversing a link or reparse point."""

    return _real_directory_chain(path, label="output parent", create=True)


def _generated_relative_path(value: str) -> PurePosixPath:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or ":" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise BundleBuildError(f"generated output path is unsafe: {value!r}")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or not relative.parts
        or any(
            part in {"", ".", ".."}
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].casefold() in _WINDOWS_DEVICE_STEMS
            for part in relative.parts
        )
    ):
        raise BundleBuildError(f"generated output path is unsafe: {value!r}")
    return relative


def _output_file(output: Path, relative_path: str) -> Path:
    root = _output_root(output)
    relative = _generated_relative_path(relative_path)
    path = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts[:-1]:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            break
        except OSError as exc:
            raise BundleBuildError(
                f"generated output parent could not be inspected: {relative_path}"
            ) from exc
        if _metadata_is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
            raise BundleBuildError(
                f"generated output parent is not a real directory: {relative_path}"
            )
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return path
    except OSError as exc:
        raise BundleBuildError(f"generated output could not be inspected: {relative_path}") from exc
    if _metadata_is_link_or_reparse(metadata):
        raise BundleBuildError(
            f"generated output file must not be a link or reparse point: {relative_path}"
        )
    return path


def _actual_files(output: Path) -> set[str]:
    root = _output_root(output)
    try:
        os.lstat(root)
    except FileNotFoundError:
        return set()
    files: set[str] = set()

    def walk(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise BundleBuildError(
                f"generated output could not be enumerated: {directory}"
            ) from exc
        for entry in entries:
            path = Path(entry.path)
            relative_path = path.relative_to(root).as_posix()
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise BundleBuildError(
                    f"generated output could not be inspected: {relative_path}"
                ) from exc
            if _metadata_is_link_or_reparse(metadata):
                raise BundleBuildError(
                    f"generated output contains a symlink or reparse point: {relative_path}"
                )
            if stat.S_ISDIR(metadata.st_mode):
                walk(path)
            elif stat.S_ISREG(metadata.st_mode):
                _require_path_single_link(path, label="generated output")
                _output_file(root, relative_path)
                files.add(relative_path)
            else:
                raise BundleBuildError(
                    f"generated output contains a non-regular entry: {relative_path}"
                )

    walk(root)
    return files


def _check_bundle(output: Path, files: Mapping[str, bytes]) -> list[str]:
    failures: list[str] = []
    expected = set(files)
    actual = _actual_files(output)
    for relative_path in sorted(expected | actual):
        path = _output_file(output, relative_path)
        if relative_path not in expected:
            failures.append(f"unexpected generated file: {relative_path}")
        elif relative_path not in actual:
            failures.append(f"missing generated file: {relative_path}")
        else:
            try:
                actual_bytes = _read_regular_bytes(
                    path,
                    maximum_bytes=max(1, len(files[relative_path])),
                    label="generated output",
                )
            except BundleBuildError:
                actual_bytes = None
            if actual_bytes != files[relative_path]:
                failures.append(f"stale generated file: {relative_path}")
    return failures


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_staged_bundle(output: Path, files: Mapping[str, bytes]) -> None:
    for relative_path, data in sorted(files.items()):
        if not isinstance(data, bytes):
            raise BundleBuildError(f"generated output must be bytes: {relative_path}")
        path = _output_file(output, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        _output_file(output, relative_path)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            raise BundleBuildError(
                f"generated output could not be created: {relative_path}"
            ) from exc
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            path.unlink(missing_ok=True)
            raise
    _fsync_directory(output)


def _remove_generated_tree(path: Path) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise BundleBuildError(f"temporary generation could not be inspected: {path}") from exc
    if _metadata_is_link_or_reparse(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise BundleBuildError(f"temporary generation has an unsafe identity: {path}")
    try:
        entries = list(os.scandir(path))
    except OSError as exc:
        raise BundleBuildError(f"temporary generation could not be enumerated: {path}") from exc
    for entry in entries:
        child = Path(entry.path)
        try:
            child_metadata = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise BundleBuildError(
                f"temporary generation entry could not be inspected: {child}"
            ) from exc
        if _metadata_is_link_or_reparse(child_metadata):
            raise BundleBuildError(f"temporary generation contains a reparse point: {child}")
        if stat.S_ISDIR(child_metadata.st_mode):
            _remove_generated_tree(child)
        elif stat.S_ISREG(child_metadata.st_mode):
            _require_path_single_link(child, label="temporary generation")
            child.unlink()
        else:
            raise BundleBuildError(f"temporary generation contains a non-regular entry: {child}")
    path.rmdir()


def _publish_staged_bundle(output: Path, staging: Path) -> None:
    backup = output.parent / f".{output.name}.backup-{uuid.uuid4().hex}"
    moved_previous = False
    try:
        try:
            os.lstat(output)
        except FileNotFoundError:
            pass
        else:
            os.replace(output, backup)
            moved_previous = True
        try:
            os.replace(staging, output)
        except OSError as publish_error:
            if moved_previous:
                try:
                    os.replace(backup, output)
                except OSError as rollback_error:
                    raise BundleBuildError(
                        "generated roster publication and rollback both failed; "
                        f"previous generation remains at {backup}"
                    ) from rollback_error
            raise BundleBuildError(
                "generated roster publication failed and was rolled back"
            ) from publish_error
        _fsync_directory(output.parent)
        if moved_previous:
            _remove_generated_tree(backup)
    except BundleBuildError:
        raise
    except OSError as exc:
        raise BundleBuildError("generated roster publication failed") from exc


def _create_staging_directory(parent: Path, name: str) -> Path:
    """Create an atomic-publication directory without Windows' private temp ACL."""

    for _attempt in range(32):
        candidate = parent / f".{name}.staging-{uuid.uuid4().hex}"
        try:
            os.mkdir(candidate, 0o755)
        except FileExistsError:
            continue
        except OSError as exc:
            raise BundleBuildError("temporary generation could not be created") from exc
        return candidate
    raise BundleBuildError("temporary generation name collisions exceeded retry limit")


def _write_bundle(output: Path, files: Mapping[str, bytes]) -> None:
    root = _output_root(output)
    parent = _ensure_real_directory(root.parent)
    if root.exists() and not _check_bundle(root, files):
        return
    staging = _create_staging_directory(parent, root.name)
    try:
        _output_root(staging)
        _write_staged_bundle(staging, files)
        failures = _check_bundle(staging, files)
        if failures:
            raise BundleBuildError("staged roster verification failed: " + "; ".join(failures))
        _publish_staged_bundle(root, staging)
    finally:
        try:
            os.lstat(staging)
        except FileNotFoundError:
            pass
        else:
            _remove_generated_tree(staging)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="pinned agency-agents checkout")
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("agency_runtime/core/roster/data"),
    )
    parser.add_argument("--expected-revision", default="")
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    files = build_bundle(args.source, args.audit_dir, str(args.expected_revision))
    if args.check:
        failures = _check_bundle(args.output, files)
        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1
    else:
        _write_bundle(args.output, files)
    manifest = safe_load_bounded_json(
        files["manifest.json"],
        maximum_bytes=MAX_MANIFEST_BYTES,
        maximum_depth=12,
        maximum_nodes=100_000,
    )
    counts = manifest["counts"]
    revision = manifest["source"]["revision"]
    print(
        "bundled roster "
        f"revision={revision} total={counts['total']} approved={counts['approved']} "
        f"quarantined={counts['quarantined']} retired={counts['retired']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BundleBuildError, OSError) as exc:
        print(f"bundled roster build failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
