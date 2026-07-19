"""Bounded, operator-controlled roster source ingestion."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.roster.remediation import (
    RemediationAttemptReceipt,
    RemediationReceipt,
    RosterRemediationError,
    is_registered_encoding_intermediate,
    remediate_source_text,
    remediation_attempt,
)
from agency_runtime.core.roster.revisions import (
    immutable_revision_version,
    source_version,
)
from agency_runtime.core.roster.semantic_projection import project_known_agent
from agency_runtime.core.roster.source_safety import (
    SUSPICIOUS_ENCODING_FINDING,
    SourceSafetyScan,
    contains_unsafe_source_control,
    format_unsafe_control_finding,
    scan_source_text,
)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#_-]*", re.IGNORECASE)
_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")
_METADATA_FIELDS = (
    "name",
    "division",
    "description",
    "source",
    "source_version",
    "prompt_path",
    "capabilities",
    "tool_affinity",
)

# Roster definitions are executable instructions. Keep every ingress and
# persistence boundary explicitly bounded so a trusted source cannot exhaust a
# host before quarantine/review has a chance to run.
MAX_HTTP_SOURCE_BYTES = 8 * 1024 * 1024
MAX_LOCAL_FILE_BYTES = 8 * 1024 * 1024
MAX_DIVISION_MANIFEST_BYTES = 256 * 1024
MAX_TOTAL_SOURCE_BYTES = 16 * 1024 * 1024
MAX_AGENT_CONTENT_BYTES = 512 * 1024
MAX_AGENT_PROMPT_BYTES = 256 * 1024
MAX_SOURCE_FILES = 512
MAX_SOURCE_CANDIDATES = 1_000
MAX_DIRECTORY_DEPTH = 16
MAX_DIRECTORY_ENTRIES = 4_096
MAX_SNAPSHOT_MANIFEST_BYTES = 32 * 1024 * 1024
MAX_SOURCE_URL_BYTES = 16 * 1024
MAX_METADATA_TEXT_BYTES = 16 * 1024
MAX_PATH_TEXT_BYTES = 16 * 1024
MAX_SHORT_TEXT_BYTES = 512
MAX_LIST_ITEMS = 256
MAX_LIST_ITEM_BYTES = 512
MAX_DOCUMENT_DEPTH = 64
MAX_DOCUMENT_NODES = 50_000
HTTP_READ_CHUNK_BYTES = 64 * 1024
HTTP_TIMEOUT_SECONDS = 30
HTTP_TOTAL_DEADLINE_SECONDS = 60
_AGENT_FILE_SUFFIXES = frozenset({".md", ".json", ".yaml", ".yml"})
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
_FLAT_FRONT_MATTER_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_HTTP_MEDIA_TYPES = frozenset(
    {
        "application/json",
        "application/octet-stream",
        "application/x-yaml",
        "application/yaml",
    }
)


class RosterSyncError(RuntimeError):
    """Raised when roster sync cannot safely continue."""


@dataclass(frozen=True, slots=True)
class _SourceDocument:
    origin: str
    content: str
    inferred_division: str | None = None
    relative_path: str | None = None

    def __iter__(self) -> Iterator[str]:
        # Preserve the historical two-item internal iteration contract.
        yield self.origin
        yield self.content


@dataclass(frozen=True, slots=True)
class _DivisionRoot:
    name: str
    path: Path
    fingerprint: tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class _DivisionManifest:
    path: Path
    fingerprint: tuple[int, int, int, int, int, int]
    root_fingerprint: tuple[int, int, int, int, int]
    divisions: tuple[_DivisionRoot, ...]


@dataclass(slots=True)
class _DiscoveryBudget:
    entries_seen: int = 0
    files_seen: int = 0


@dataclass(frozen=True, slots=True)
class ManifestImportOutcome:
    """One deterministic result for a manifest-backed source entry."""

    status: str
    origin: str
    relative_path: str
    slug: str
    content_hash: str
    finding: str
    content: str = ""
    source_content: str = ""
    remediation: RemediationReceipt | None = None
    remediation_attempt: RemediationAttemptReceipt | None = None

    def public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "origin": self.origin,
            "relative_path": self.relative_path,
            "slug": self.slug,
            "hash": self.content_hash,
            "finding": self.finding,
        }
        if self.remediation is not None:
            result["remediation"] = self.remediation.public_dict()
        if self.remediation_attempt is not None:
            result["remediation_attempt"] = self.remediation_attempt.public_dict()
        return result


class RosterDownload(list[dict[str, Any]]):
    """List-compatible candidate result with explicit manifest entry outcomes."""

    def __init__(
        self,
        candidates: list[dict[str, Any]],
        outcomes: list[ManifestImportOutcome],
    ) -> None:
        super().__init__(candidates)
        self.outcomes = tuple(outcomes)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _utf8_size(text: str) -> int:
    return len(text.encode("utf-8"))


def _require_bounded_text(value: Any, limit: int, label: str) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, (bool, int, float)):
        text = str(value)
    else:
        raise RosterSyncError(f"{label} must be text")
    size = _utf8_size(text)
    if size > limit:
        raise RosterSyncError(f"{label} is {size} bytes; limit is {limit} bytes")
    if contains_unsafe_source_control(text):
        raise RosterSyncError(f"{label} contains an unsafe control character")
    return text


def _validate_structure(value: Any, label: str) -> None:
    pending: list[tuple[Any, int]] = [(value, 0)]
    containers_seen: set[int] = set()
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_DOCUMENT_NODES:
            raise RosterSyncError(f"{label} exceeds structural node limit {MAX_DOCUMENT_NODES}")
        if depth > MAX_DOCUMENT_DEPTH:
            raise RosterSyncError(f"{label} exceeds nesting depth {MAX_DOCUMENT_DEPTH}")
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in containers_seen:
                raise RosterSyncError(f"{label} contains a cycle or shared alias")
            containers_seen.add(identity)
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise RosterSyncError(f"{label} mapping keys must be text")
                pending.append((nested, depth + 1))
        elif isinstance(item, (list, tuple)):
            identity = id(item)
            if identity in containers_seen:
                raise RosterSyncError(f"{label} contains a cycle or shared alias")
            containers_seen.add(identity)
            pending.extend((nested, depth + 1) for nested in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise RosterSyncError(f"{label} contains a non-finite number")
        elif item is not None and not isinstance(item, (str, bool, int, float)):
            raise RosterSyncError(f"{label} contains unsupported value type {type(item).__name__}")


def _load_json(text: str, label: str) -> Any:
    try:
        value = safe_load_bounded_json(
            text,
            maximum_bytes=MAX_LOCAL_FILE_BYTES,
            maximum_depth=MAX_DOCUMENT_DEPTH,
            maximum_nodes=MAX_DOCUMENT_NODES,
        )
    except BoundedJSONError as exc:
        detail = str(exc)
        detail = detail.replace(
            "JSON contains a duplicate object key", "contains duplicate key"
        ).replace(
            "JSON exceeds the nesting-depth limit",
            f"exceeds nesting depth {MAX_DOCUMENT_DEPTH}",
        )
        if detail.startswith("JSON "):
            detail = detail[5:]
        raise RosterSyncError(f"{label} {detail}") from exc
    _validate_structure(value, label)
    return value


def _load_yaml(text: str, label: str) -> Any:
    try:
        value = safe_load_bounded(
            text,
            maximum_depth=MAX_DOCUMENT_DEPTH,
            maximum_nodes=MAX_DOCUMENT_NODES,
        )
    except BoundedYAMLError as exc:
        raise RosterSyncError(f"{label}: {exc}") from exc
    except RecursionError as exc:
        raise RosterSyncError(f"{label} is not valid bounded YAML") from exc
    _validate_structure(value, label)
    return value


def _load_flat_front_matter(text: str, label: str) -> dict[str, str]:
    """Parse the bounded flat scalar format used by manifest-backed catalogs."""

    lines = text.splitlines()
    if len(lines) > MAX_LIST_ITEMS:
        raise RosterSyncError(f"{label} contains more than {MAX_LIST_ITEMS} fields")
    loaded: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        key, separator, raw_value = line.partition(":")
        value = raw_value.strip()
        if (
            not separator
            or line != line.lstrip()
            or not _FLAT_FRONT_MATTER_KEY_RE.fullmatch(key)
            or not value
            or value.startswith(("&", "*", "!", "[", "{", "|", ">"))
        ):
            raise RosterSyncError(f"{label} is not a bounded flat mapping")
        if key in loaded:
            raise RosterSyncError(f"{label} contains duplicate key {key!r}")
        loaded[key] = _require_bounded_text(
            value,
            MAX_METADATA_TEXT_BYTES,
            f"{label} field {key}",
        )
    if not loaded:
        raise RosterSyncError(f"{label} must not be empty")
    return loaded


def _json_list(value: Any, *, label: str = "list field") -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = _require_bounded_text(value, MAX_METADATA_TEXT_BYTES, label)
        try:
            loaded = _load_json(value, label)
            if isinstance(loaded, list):
                value = loaded
            else:
                value = [part.strip() for part in value.split(",") if part.strip()]
        except RosterSyncError:
            if value.lstrip().startswith(("[", "{")):
                raise
            value = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, set):
        value = sorted(value, key=str)
    elif not isinstance(value, (list, tuple)):
        value = [value]
    if len(value) > MAX_LIST_ITEMS:
        raise RosterSyncError(f"{label} contains more than {MAX_LIST_ITEMS} items")
    result: list[str] = []
    for item in value:
        text = _require_bounded_text(item, MAX_LIST_ITEM_BYTES, f"{label} item").strip()
        if text and text not in result:
            result.append(text)
    return result


def _slugify_name(name: str) -> str:
    """Match the upstream roster convention for name-derived agent slugs."""

    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", name.lower())).strip("-")


def _manifest_slug_hint(content: str, relative_path: str) -> str:
    match = re.match(
        r"\A---(?:\r?\n)(.*?)(?:\r?\n)---(?:\r?\n|\Z)",
        content,
        re.DOTALL,
    )
    name = ""
    if match is not None:
        for line in match.group(1).splitlines():
            key, separator, value = line.partition(":")
            if separator and key == "name":
                name = value.strip().strip("'\"")
                break
    slug = _slugify_name(name)
    if slug:
        return slug
    fallback = _slugify_name(Path(relative_path).stem)
    return fallback or f"invalid-agent-{_hash_text(relative_path)[:12]}"


def _manifest_finding(
    content: str,
    error: Exception,
    *,
    safety_scan: SourceSafetyScan | None = None,
) -> str:
    if is_registered_encoding_intermediate(content) or "registered encoding repair" in str(error):
        return "unreceipted_known_encoding_repair"
    scan = safety_scan if safety_scan is not None else scan_source_text(content)
    if scan.controls:
        return format_unsafe_control_finding(scan)
    if scan.suspicious_encoding:
        return SUSPICIOUS_ENCODING_FINDING
    message = _require_bounded_text(
        str(error),
        MAX_METADATA_TEXT_BYTES,
        "manifest import finding",
    )
    return f"invalid_agent:{type(error).__name__}:{message}"


def _manifest_outcome(
    document: _SourceDocument,
    *,
    status: str,
    slug: str,
    finding: str,
    preserve_content: bool = False,
) -> ManifestImportOutcome:
    relative_path = document.relative_path or Path(document.origin).name
    attempt = remediation_attempt(document.content, finding) if status == "quarantined" else None
    return ManifestImportOutcome(
        status=status,
        origin=document.origin,
        relative_path=relative_path,
        slug=slug,
        content_hash=_hash_text(document.content),
        finding=finding,
        content=document.content if preserve_content else "",
        remediation_attempt=attempt,
    )


@dataclass(slots=True)
class _DownloadAccumulator:
    source_reference: str
    candidates: list[dict[str, Any]] = dataclass_field(default_factory=list)
    outcomes: list[ManifestImportOutcome] = dataclass_field(default_factory=list)
    slug_origins: dict[str, str] = dataclass_field(default_factory=dict)

    @staticmethod
    def _is_manifest_document(document: _SourceDocument) -> bool:
        return document.inferred_division is not None

    def _quarantine(
        self,
        document: _SourceDocument,
        error: Exception,
        *,
        safety_scan: SourceSafetyScan | None = None,
    ) -> None:
        relative_path = document.relative_path or Path(document.origin).name
        identity = (relative_path, _hash_text(document.content))
        if any(
            outcome.status == "quarantined"
            and (outcome.relative_path, outcome.content_hash) == identity
            for outcome in self.outcomes
        ):
            return
        self.outcomes.append(
            _manifest_outcome(
                document,
                status="quarantined",
                slug=_manifest_slug_hint(document.content, relative_path),
                finding=_manifest_finding(
                    document.content,
                    error,
                    safety_scan=safety_scan,
                ),
                preserve_content=True,
            )
        )

    def _append(
        self,
        candidate: dict[str, Any],
        document: _SourceDocument,
        *,
        remediation: RemediationReceipt | None = None,
    ) -> None:
        slug = str(candidate.get("slug") or "").casefold()
        previous_origin = self.slug_origins.get(slug)
        if previous_origin is not None:
            raise RosterSyncError(
                f"roster source contains duplicate agent slug {slug!r}: "
                f"{previous_origin} and {document.origin}"
            )
        if self._is_manifest_document(document):
            ok, reason = validate_agent(candidate)
            if not ok:
                self.outcomes.append(
                    _manifest_outcome(
                        document,
                        status="quarantined",
                        slug=slug
                        or _manifest_slug_hint(
                            document.content,
                            document.relative_path or Path(document.origin).name,
                        ),
                        finding=f"invalid_agent:{reason}",
                        preserve_content=True,
                    )
                )
                return
        self.slug_origins[slug] = document.origin
        if remediation is not None:
            candidate["source_content_hash"] = remediation.original_hash
        self.candidates.append(candidate)
        if self._is_manifest_document(document):
            outcome = _manifest_outcome(
                document,
                status="candidate",
                slug=slug,
                finding=(
                    "candidate_ready_after_remediation"
                    if remediation is not None
                    else "candidate_ready"
                ),
            )
            if remediation is not None:
                outcome = ManifestImportOutcome(
                    status=outcome.status,
                    origin=outcome.origin,
                    relative_path=outcome.relative_path,
                    slug=outcome.slug,
                    content_hash=outcome.content_hash,
                    finding=outcome.finding,
                    source_content=document.content,
                    remediation=remediation,
                )
            self.outcomes.append(outcome)

    def _json_item(
        self,
        raw_item: Any,
        document: _SourceDocument,
    ) -> dict[str, Any]:
        if not isinstance(raw_item, dict):
            raise ValueError(f"JSON roster item at {document.origin} is not an object")
        item = dict(raw_item)
        item.setdefault(
            "content",
            _require_bounded_text(
                json.dumps(item, sort_keys=True, separators=(",", ":")),
                MAX_AGENT_CONTENT_BYTES,
                f"agent content at {document.origin}",
            ),
        )
        item["source"] = self.source_reference
        item["prompt_path"] = document.origin
        if document.inferred_division and not str(item.get("division") or "").strip():
            item["division"] = document.inferred_division
        return _normalize_agent(item)

    def _ingest_json(
        self,
        document: _SourceDocument,
        stripped: str,
        *,
        safety_scan: SourceSafetyScan | None = None,
    ) -> None:
        try:
            loaded = _load_json(stripped, f"JSON roster at {document.origin}")
            if not isinstance(loaded, list):
                raise ValueError(f"JSON roster at {document.origin} must be a list")
        except (RosterSyncError, ValueError) as exc:
            if not self._is_manifest_document(document):
                raise
            self._quarantine(document, exc, safety_scan=safety_scan)
            return
        if len(self.candidates) + len(loaded) > MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(
                f"roster source contains more than {MAX_SOURCE_CANDIDATES} candidates: "
                f"{self.source_reference}"
            )
        for raw_item in loaded:
            try:
                candidate = self._json_item(raw_item, document)
            except (RosterSyncError, ValueError) as exc:
                if not self._is_manifest_document(document):
                    raise
                self._quarantine(document, exc, safety_scan=safety_scan)
                continue
            self._append(candidate, document)

    def _ingest_agent(
        self,
        document: _SourceDocument,
        *,
        source_document: _SourceDocument | None = None,
        remediation: RemediationReceipt | None = None,
        safety_scan: SourceSafetyScan | None = None,
    ) -> None:
        if len(self.candidates) >= MAX_SOURCE_CANDIDATES:
            raise RosterSyncError(
                f"roster source contains more than {MAX_SOURCE_CANDIDATES} candidates: "
                f"{self.source_reference}"
            )
        try:
            agent = parse_agent_file(
                document.content,
                inferred_division=document.inferred_division,
                _remediation_receipt_present=remediation is not None,
            )
        except (RosterSyncError, ValueError) as exc:
            if not self._is_manifest_document(document):
                raise
            self._quarantine(
                source_document or document,
                exc,
                safety_scan=safety_scan,
            )
            return
        if remediation is not None:
            try:
                agent, remediation = project_known_agent(
                    agent,
                    remediation,
                    relative_path=document.relative_path or Path(document.origin).name,
                )
            except RosterRemediationError as exc:
                self._quarantine(
                    source_document or document,
                    exc,
                    safety_scan=safety_scan,
                )
                return
        agent["source"] = self.source_reference
        agent["prompt_path"] = document.origin
        self._append(
            _normalize_agent(agent),
            source_document or document,
            remediation=remediation,
        )

    def ingest(self, document: _SourceDocument) -> None:
        safety_scan = scan_source_text(document.content)
        stripped = document.content.strip()
        if (
            self._is_manifest_document(document)
            and Path(document.origin).suffix.casefold() == ".md"
            and not stripped.startswith("---")
        ):
            self.outcomes.append(
                _manifest_outcome(
                    document,
                    status="ignored",
                    slug="",
                    finding="not_agent_definition:missing_front_matter",
                )
            )
            return
        remediated_content, remediation = remediate_source_text(document.content)
        if remediation is None and is_registered_encoding_intermediate(document.content):
            error = RosterSyncError(
                "registered encoding repair requires its original-source receipt"
            )
            if not self._is_manifest_document(document):
                raise error
            self._quarantine(document, error, safety_scan=safety_scan)
            return
        if remediation is None and safety_scan.controls:
            error = RosterSyncError("source contains an unsafe control character")
            if not self._is_manifest_document(document):
                raise error
            self._quarantine(document, error, safety_scan=safety_scan)
            return
        if remediation is None and safety_scan.suspicious_encoding:
            self._quarantine(
                document,
                RosterSyncError("source contains suspicious Markdown heading encoding"),
                safety_scan=safety_scan,
            )
            return
        effective = document
        if remediation is not None:
            effective = _SourceDocument(
                document.origin,
                remediated_content,
                document.inferred_division,
                document.relative_path,
            )
            stripped = remediated_content.strip()
        if stripped.startswith("["):
            if remediation is not None:
                # A remediated manifest file must map to one source identity so
                # its immutable raw-byte receipt cannot ambiguously cover
                # several candidates.
                try:
                    loaded = _load_json(stripped, f"JSON roster at {document.origin}")
                except RosterSyncError as exc:
                    self._quarantine(document, exc, safety_scan=safety_scan)
                    return
                if not isinstance(loaded, list) or len(loaded) != 1:
                    self._quarantine(
                        document,
                        RosterSyncError(
                            "remediated JSON roster must contain exactly one candidate"
                        ),
                        safety_scan=safety_scan,
                    )
                    return
                try:
                    candidate = self._json_item(loaded[0], effective)
                    candidate, remediation = project_known_agent(
                        candidate,
                        remediation,
                        relative_path=document.relative_path or Path(document.origin).name,
                    )
                    candidate["source"] = self.source_reference
                    candidate["prompt_path"] = document.origin
                    candidate = _normalize_agent(
                        candidate,
                        _remediation_receipt_present=True,
                    )
                except (RosterRemediationError, RosterSyncError, ValueError) as exc:
                    self._quarantine(document, exc, safety_scan=safety_scan)
                    return
                self._append(candidate, document, remediation=remediation)
                return
            self._ingest_json(document, stripped, safety_scan=safety_scan)
        else:
            self._ingest_agent(
                effective,
                source_document=document,
                remediation=remediation,
                safety_scan=safety_scan,
            )


def _normalize_agent(
    agent: dict[str, Any],
    *,
    _remediation_receipt_present: bool = False,
) -> dict[str, Any]:
    if not isinstance(agent, dict):
        raise RosterSyncError("agent must be a mapping")
    _validate_structure(agent, "agent")
    if not _remediation_receipt_present and any(
        isinstance(agent.get(field), str) and is_registered_encoding_intermediate(str(agent[field]))
        for field in ("prompt_body", "prompt", "body", "content")
    ):
        raise RosterSyncError(
            "registered encoding repair requires semantic projection from original evidence"
        )
    normalized = dict(agent)
    raw_name = _require_bounded_text(
        normalized.get("name") or "",
        MAX_SHORT_TEXT_BYTES,
        "agent name",
    )
    raw_slug = _require_bounded_text(
        normalized.get("slug") or normalized.get("id") or "",
        MAX_SHORT_TEXT_BYTES,
        "agent slug",
    )
    if raw_slug.strip():
        slug = re.sub(r"[^a-z0-9._-]+", "-", raw_slug.strip().lower()).strip("-._")
    else:
        slug = _slugify_name(raw_name)
    normalized["slug"] = slug
    normalized["name"] = _require_bounded_text(
        raw_name or (slug.replace("-", " ").title() if slug else ""),
        MAX_SHORT_TEXT_BYTES,
        f"agent {slug or '<missing>'} name",
    )
    normalized["description"] = _require_bounded_text(
        normalized.get("description") or "",
        MAX_METADATA_TEXT_BYTES,
        f"agent {slug or '<missing>'} description",
    )
    normalized["division"] = _require_bounded_text(
        normalized.get("division") or "general",
        MAX_SHORT_TEXT_BYTES,
        f"agent {slug or '<missing>'} division",
    )
    normalized["source_version"] = _require_bounded_text(
        source_version(normalized),
        MAX_SHORT_TEXT_BYTES,
        f"agent {slug or '<missing>'} source version",
    )
    normalized["source"] = _require_bounded_text(
        normalized.get("source") or "",
        MAX_PATH_TEXT_BYTES,
        f"agent {slug or '<missing>'} source",
    )
    normalized["prompt_path"] = _require_bounded_text(
        normalized.get("prompt_path") or "",
        MAX_PATH_TEXT_BYTES,
        f"agent {slug or '<missing>'} prompt path",
    )
    body = _require_bounded_text(
        normalized.get("prompt_body")
        or normalized.get("prompt")
        or normalized.get("body")
        or normalized.get("content")
        or "",
        MAX_AGENT_PROMPT_BYTES,
        f"agent {slug or '<missing>'} prompt",
    )
    normalized["prompt_body"] = body
    for field in _LIST_FIELDS:
        normalized[field] = _json_list(
            normalized.get(field), label=f"agent {slug or '<missing>'} {field}"
        )
    if not normalized.get("categories"):
        normalized["categories"] = categorize_agent(normalized)
    content = normalized.get("content") or body
    if not content:
        try:
            content = json.dumps(normalized, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise RosterSyncError(f"agent {slug or '<missing>'} is not JSON serializable") from exc
    normalized["content"] = _require_bounded_text(
        content,
        MAX_AGENT_CONTENT_BYTES,
        f"agent {slug or '<missing>'} content",
    )
    normalized["hash"] = _hash_text(normalized["content"])
    normalized["version"] = immutable_revision_version(normalized)
    for field in ("id", "download_id", "source_id", "status"):
        if field in normalized:
            normalized[field] = _require_bounded_text(
                normalized[field], MAX_SHORT_TEXT_BYTES, f"agent {field}"
            )
    return normalized


def parse_agent_file(
    content: str,
    *,
    inferred_division: str | None = None,
    _remediation_receipt_present: bool = False,
) -> dict[str, Any]:
    """Parse a JSON/YAML/Markdown agent file into a normalized dict."""

    _require_bounded_text(content, MAX_AGENT_CONTENT_BYTES, "agent file")
    if is_registered_encoding_intermediate(content) and not _remediation_receipt_present:
        raise RosterSyncError(
            "registered encoding repair requires semantic projection from original evidence"
        )
    text = content.strip()
    if not text:
        raise ValueError("empty agent file")

    data: dict[str, Any]
    body = text
    if text.startswith("{"):
        loaded = _load_json(text, "agent JSON")
        if not isinstance(loaded, dict):
            raise ValueError("agent JSON must be an object")
        data = loaded
        body = loaded.get("prompt_body") or loaded.get("prompt") or loaded.get("content") or text
    elif text.startswith("---"):
        match = re.match(r"\A---(?:\r?\n)(.*?)(?:\r?\n)---(?:\r?\n|\Z)(.*)\Z", text, re.DOTALL)
        if match is None:
            raise ValueError("unterminated YAML front matter")
        try:
            loaded = _load_yaml(match.group(1), "agent YAML front matter") or {}
        except RosterSyncError as yaml_error:
            if inferred_division is None:
                raise
            try:
                loaded = _load_flat_front_matter(
                    match.group(1),
                    "agent front matter",
                )
            except RosterSyncError:
                raise yaml_error from None
        if not isinstance(loaded, dict):
            raise ValueError("front matter must be a mapping")
        data = loaded
        body = match.group(2).strip()
    elif re.match(r"^[\w-]+:\s", text):
        loaded = _load_yaml(text, "agent YAML")
        if not isinstance(loaded, dict):
            raise ValueError("YAML agent file must be a mapping")
        data = loaded
        body = loaded.get("prompt_body") or loaded.get("prompt") or loaded.get("content") or text
    else:
        heading = next(
            (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")),
            "",
        )
        slug = re.sub(r"[^a-z0-9._-]+", "-", heading.lower()).strip("-._") if heading else ""
        data = {
            "slug": slug,
            "name": heading or "Imported Agent",
            "description": "Imported Markdown agent",
        }
        body = text

    data = dict(data)
    if inferred_division and not str(data.get("division") or "").strip():
        data["division"] = inferred_division
    data["content"] = content
    data.setdefault("prompt_body", body)
    return _normalize_agent(
        data,
        _remediation_receipt_present=_remediation_receipt_present,
    )


def _decode_source(data: bytes, origin: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RosterSyncError(f"roster source is not valid UTF-8: {origin}") from exc


def _source_label(value: str) -> str:
    """Return a log-safe source identity without credentials, query, or fragment."""

    try:
        parsed = urlsplit(value)
        if parsed.scheme.casefold() not in {"http", "https"}:
            return value
        host = parsed.hostname or "<invalid-host>"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        try:
            port = parsed.port
        except ValueError:
            port = None
        authority = f"{host}:{port}" if port is not None else host
        return urlunsplit((parsed.scheme.casefold(), authority, parsed.path, "", ""))
    except (TypeError, ValueError):
        return "<invalid-source>"


def _validated_http_source(value: str, parsed: Any) -> tuple[str, str]:
    if any(character.isspace() for character in value) or "\\" in value:
        raise RosterSyncError("HTTP roster source contains whitespace or a backslash")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RosterSyncError(
            "HTTP roster source must percent-encode non-ASCII characters"
        ) from exc
    if not parsed.netloc or not parsed.hostname:
        raise RosterSyncError("HTTP roster source must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise RosterSyncError("HTTP roster source may not contain credentials")
    try:
        _port = parsed.port
    except ValueError as exc:
        raise RosterSyncError("HTTP roster source has an invalid port") from exc
    if parsed.fragment:
        raise RosterSyncError("HTTP roster source may not contain a fragment")
    return "http", value


def _file_source_path(parsed: Any) -> tuple[str, Path]:
    if parsed.query or parsed.fragment:
        raise RosterSyncError("file roster source may not contain query or fragment data")
    if parsed.username is not None or parsed.password is not None:
        raise RosterSyncError("file roster source may not contain credentials")
    if parsed.netloc and parsed.netloc.casefold() != "localhost":
        raise RosterSyncError("remote file URL authorities are not supported")
    decoded_path = unquote(parsed.path)
    if not decoded_path:
        raise RosterSyncError("file roster source must include a path")
    if len(decoded_path) >= 2 and all(character in "/\\\\" for character in decoded_path[:2]):
        raise RosterSyncError("remote file URL paths are not supported")
    local_value = urllib.request.url2pathname(decoded_path)
    return "path", Path(local_value).expanduser()


def _existing_local_source(value: str, scheme: str) -> tuple[str, Path]:
    local_path = Path(value).expanduser()
    try:
        os.lstat(local_path)
    except OSError:
        raise RosterSyncError(f"unsupported roster source scheme: {scheme}") from None
    return "path", local_path


def _validate_source_spec(value: str) -> tuple[str, str | Path]:
    if not isinstance(value, str):
        raise RosterSyncError("roster source must be text")
    value = _require_bounded_text(value, MAX_SOURCE_URL_BYTES, "roster source")
    if not value.strip():
        raise RosterSyncError("roster source may not be empty")
    if _CONTROL_RE.search(value):
        raise RosterSyncError("roster source may not contain control characters")
    if value.startswith(("\\\\", "//")):
        raise RosterSyncError(
            "remote filesystem roster paths are not supported; use an explicit HTTP(S) source"
        )
    if _WINDOWS_DRIVE_RE.match(value):
        return "path", Path(value).expanduser()

    try:
        parsed = urlsplit(value)
    except ValueError:
        raise RosterSyncError("roster source URL is malformed") from None
    scheme = parsed.scheme.casefold()
    if scheme in {"http", "https"}:
        return _validated_http_source(value, parsed)

    if scheme == "file":
        return _file_source_path(parsed)

    if not scheme:
        return "path", Path(value).expanduser()

    # A colon is legal in a POSIX filename. Preserve such an explicitly chosen
    # local source when it exists, while never treating an unknown URL scheme as
    # a network request.
    return _existing_local_source(value, scheme)


def _response_status(response: Any) -> int:
    status = getattr(response, "status", None)
    if status is None and hasattr(response, "getcode"):
        status = response.getcode()
    if isinstance(status, bool) or not isinstance(status, int):
        raise RosterSyncError("HTTP roster source did not provide a valid status")
    if not 200 <= status < 300:
        raise RosterSyncError(f"HTTP roster source returned status {status}")
    return status


def _validate_response_headers(response: Any) -> None:
    headers = response.headers
    content_encoding = str(headers.get("Content-Encoding") or "identity").strip().casefold()
    if content_encoding != "identity":
        raise RosterSyncError("HTTP roster source uses unsupported content encoding")
    raw_media_type = str(headers.get("Content-Type") or "").split(";", 1)[0]
    media_type = raw_media_type.strip().casefold()
    if media_type:
        allowed = (
            media_type in _HTTP_MEDIA_TYPES
            or (media_type.startswith("text/") and media_type not in {"text/html"})
            or media_type.endswith("+json")
            or media_type.endswith("+yaml")
        )
        if not allowed:
            raise RosterSyncError("HTTP roster source returned unsupported media type")


def _read_http_source(url: str) -> str:
    label = _source_label(url)
    deadline = monotonic() + HTTP_TOTAL_DEADLINE_SECONDS
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/yaml, text/yaml, text/markdown, text/plain, application/octet-stream",
            "Accept-Encoding": "identity",
            "User-Agent": "agency-runtime-roster-sync/1",
        },
        method="GET",
    )
    try:
        with open_no_redirect(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            if monotonic() >= deadline:
                raise RosterSyncError("HTTP roster source exceeded its total deadline")
            _response_status(response)
            final_url = response.geturl() if hasattr(response, "geturl") else url
            if final_url != url:
                raise RosterSyncError("HTTP roster source changed URL unexpectedly")
            _validate_response_headers(response)
            raw_length = response.headers.get("Content-Length")
            if raw_length not in (None, ""):
                raw_length = str(raw_length)
                if len(raw_length) > 20 or not raw_length.isascii() or not raw_length.isdecimal():
                    raise RosterSyncError("invalid Content-Length from HTTP roster source")
                content_length = int(raw_length)
                if content_length > MAX_HTTP_SOURCE_BYTES:
                    raise RosterSyncError(
                        f"HTTP roster source declares {content_length} bytes; "
                        f"limit is {MAX_HTTP_SOURCE_BYTES} bytes"
                    )

            chunks: list[bytes] = []
            total = 0
            while True:
                if monotonic() >= deadline:
                    raise RosterSyncError("HTTP roster source exceeded its total deadline")
                chunk = response.read(min(HTTP_READ_CHUNK_BYTES, MAX_HTTP_SOURCE_BYTES - total + 1))
                if monotonic() >= deadline:
                    raise RosterSyncError("HTTP roster source exceeded its total deadline")
                if not chunk:
                    break
                if not isinstance(chunk, bytes):
                    raise RosterSyncError("HTTP roster source returned non-byte content")
                total += len(chunk)
                if total > MAX_HTTP_SOURCE_BYTES:
                    raise RosterSyncError(
                        f"HTTP roster source exceeds {MAX_HTTP_SOURCE_BYTES} bytes"
                    )
                chunks.append(chunk)
    except RosterSyncError:
        raise
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise RosterSyncError(
            f"unable to read HTTP roster source {label}: {type(exc).__name__}"
        ) from None
    return _decode_source(b"".join(chunks), label)


def _metadata_is_link_or_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _stable_identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(stat.S_IFMT(metadata.st_mode)),
        int(getattr(metadata, "st_file_attributes", 0) or 0),
    )


def _file_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        *_stable_identity(metadata),
        int(metadata.st_size),
        int(getattr(metadata, "st_mtime_ns", None) or int(metadata.st_mtime * 1_000_000_000)),
    )


def _directory_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        *_stable_identity(metadata),
        int(getattr(metadata, "st_mtime_ns", None) or int(metadata.st_mtime * 1_000_000_000)),
    )


def _assert_real_path_chain(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    current = Path(parts[0])
    for part in parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise RosterSyncError(f"roster source path is unavailable: {current}") from exc
        if _metadata_is_link_or_reparse(metadata):
            raise RosterSyncError(
                f"roster sources may not use symbolic links or reparse points: {current}"
            )
    return absolute


def _read_local_file(
    path: Path,
    *,
    expected_fingerprint: tuple[int, int, int, int, int, int] | None = None,
) -> tuple[str, int]:
    path = _assert_real_path_chain(path)
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise RosterSyncError(f"local roster file is unavailable: {path}") from exc
    if _metadata_is_link_or_reparse(before) or not stat.S_ISREG(before.st_mode):
        raise RosterSyncError(f"roster source must be a regular file: {path}")
    if expected_fingerprint is not None and _file_fingerprint(before) != expected_fingerprint:
        raise RosterSyncError(f"local roster file changed during discovery: {path}")
    if before.st_size > MAX_LOCAL_FILE_BYTES:
        raise RosterSyncError(
            f"local roster file is {before.st_size} bytes; limit is {MAX_LOCAL_FILE_BYTES} bytes: {path}"
        )
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if (
            _metadata_is_link_or_reparse(opened)
            or not stat.S_ISREG(opened.st_mode)
            or _stable_identity(before) != _stable_identity(opened)
        ):
            raise RosterSyncError(f"local roster file changed while being opened: {path}")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            data = handle.read(MAX_LOCAL_FILE_BYTES + 1)
            opened_after = os.fstat(handle.fileno())
        if _file_fingerprint(opened) != _file_fingerprint(opened_after):
            raise RosterSyncError(f"local roster file changed while being read: {path}")
        after = os.lstat(path)
        if _file_fingerprint(before) != _file_fingerprint(after) or _metadata_is_link_or_reparse(
            after
        ):
            raise RosterSyncError(f"local roster file changed while being read: {path}")
    except RosterSyncError:
        raise
    except OSError as exc:
        raise RosterSyncError(f"unable to read local roster file: {path}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_LOCAL_FILE_BYTES:
        raise RosterSyncError(f"local roster file exceeds {MAX_LOCAL_FILE_BYTES} bytes: {path}")
    return _decode_source(data, str(path)), len(data)


def _assert_expected_directory_fingerprint(
    root: Path,
    actual: tuple[int, int, int, int, int],
    expected: tuple[int, int, int, int, int] | None,
) -> None:
    if expected is not None and actual != expected:
        raise RosterSyncError(f"roster directory changed during discovery: {root}")


def _directory_files(
    root: Path,
    *,
    expected_root_fingerprint: tuple[int, int, int, int, int] | None = None,
    budget: _DiscoveryBudget | None = None,
    source_root: Path | None = None,
) -> list[tuple[Path, tuple[int, int, int, int, int, int]]]:
    root = _assert_real_path_chain(root)
    root_metadata = os.lstat(root)
    if _metadata_is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise RosterSyncError(f"roster directory must be a real directory: {root}")
    root_fingerprint = _directory_fingerprint(root_metadata)
    _assert_expected_directory_fingerprint(
        root,
        root_fingerprint,
        expected_root_fingerprint,
    )
    files: list[tuple[Path, tuple[int, int, int, int, int, int]]] = []
    discovery_budget = budget or _DiscoveryBudget()
    error_root = source_root or root
    pending: list[tuple[Path, int, tuple[int, int, int, int, int]]] = [(root, 0, root_fingerprint)]
    while pending:
        directory, depth, expected_fingerprint = pending.pop()
        directory = _assert_real_path_chain(directory)
        before = os.lstat(directory)
        if (
            _metadata_is_link_or_reparse(before)
            or not stat.S_ISDIR(before.st_mode)
            or _directory_fingerprint(before) != expected_fingerprint
        ):
            raise RosterSyncError(f"roster directory changed during discovery: {directory}")
        entries: list[tuple[Path, os.stat_result]] = []
        for child in directory.iterdir():
            discovery_budget.entries_seen += 1
            if discovery_budget.entries_seen > MAX_DIRECTORY_ENTRIES:
                raise RosterSyncError(
                    f"roster directory exceeds {MAX_DIRECTORY_ENTRIES} entries: {error_root}"
                )
            metadata = os.lstat(child)
            if _metadata_is_link_or_reparse(metadata):
                raise RosterSyncError(
                    f"roster sources may not use symbolic links or reparse points: {child}"
                )
            entries.append((child, metadata))
        if _directory_fingerprint(os.lstat(directory)) != expected_fingerprint:
            raise RosterSyncError(f"roster directory changed during discovery: {directory}")
        entries.sort(key=lambda item: item[0].name.casefold())
        child_directories: list[tuple[Path, int, tuple[int, int, int, int, int]]] = []
        for child, metadata in entries:
            if stat.S_ISDIR(metadata.st_mode):
                if depth >= MAX_DIRECTORY_DEPTH:
                    raise RosterSyncError(
                        f"roster directory exceeds recursion depth {MAX_DIRECTORY_DEPTH}: {child}"
                    )
                child_directories.append((child, depth + 1, _directory_fingerprint(metadata)))
            elif stat.S_ISREG(metadata.st_mode) and child.suffix.lower() in _AGENT_FILE_SUFFIXES:
                files.append((child, _file_fingerprint(metadata)))
                discovery_budget.files_seen += 1
                if discovery_budget.files_seen > MAX_SOURCE_FILES:
                    raise RosterSyncError(
                        f"roster source contains more than {MAX_SOURCE_FILES} agent files: "
                        f"{error_root}"
                    )
            elif child.suffix.lower() in _AGENT_FILE_SUFFIXES:
                raise RosterSyncError(f"roster source contains a non-regular agent file: {child}")
        # Reverse push preserves the case-insensitive sorted walk with a LIFO stack.
        pending.extend(reversed(child_directories))
    if _directory_fingerprint(os.lstat(root)) != root_fingerprint:
        raise RosterSyncError(f"roster directory changed during discovery: {root}")
    return files


def _load_division_manifest(
    root: Path,
    root_fingerprint: tuple[int, int, int, int, int],
) -> _DivisionManifest | None:
    manifest_path = root / "divisions.json"
    try:
        manifest_metadata = os.lstat(manifest_path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RosterSyncError(f"division manifest is unavailable: {manifest_path}") from exc
    if _metadata_is_link_or_reparse(manifest_metadata) or not stat.S_ISREG(
        manifest_metadata.st_mode
    ):
        raise RosterSyncError(f"division manifest must be a regular file: {manifest_path}")
    if manifest_metadata.st_size > MAX_DIVISION_MANIFEST_BYTES:
        raise RosterSyncError(
            f"division manifest is {manifest_metadata.st_size} bytes; "
            f"limit is {MAX_DIVISION_MANIFEST_BYTES} bytes: {manifest_path}"
        )
    manifest_fingerprint = _file_fingerprint(manifest_metadata)
    content, _ = _read_local_file(
        manifest_path,
        expected_fingerprint=manifest_fingerprint,
    )
    loaded = _load_json(content, f"division manifest at {manifest_path}")
    if not isinstance(loaded, dict):
        raise RosterSyncError(f"division manifest must be an object: {manifest_path}")
    raw_divisions = loaded.get("divisions")
    if not isinstance(raw_divisions, dict) or not raw_divisions:
        raise RosterSyncError(
            f"division manifest must declare a non-empty divisions object: {manifest_path}"
        )
    if len(raw_divisions) > MAX_LIST_ITEMS:
        raise RosterSyncError(
            f"division manifest declares more than {MAX_LIST_ITEMS} divisions: {manifest_path}"
        )

    divisions: list[_DivisionRoot] = []
    for raw_name, descriptor in raw_divisions.items():
        name = _require_bounded_text(
            raw_name,
            MAX_SHORT_TEXT_BYTES,
            "division manifest name",
        )
        if not name or name != name.strip() or _slugify_name(name) != name:
            raise RosterSyncError(
                f"division manifest contains an unsafe division name: {manifest_path}"
            )
        if not isinstance(descriptor, dict):
            raise RosterSyncError(f"division manifest entry must be an object: {name}")
        division_path = _assert_real_path_chain(root / name)
        division_metadata = os.lstat(division_path)
        if _metadata_is_link_or_reparse(division_metadata) or not stat.S_ISDIR(
            division_metadata.st_mode
        ):
            raise RosterSyncError(f"declared division must be a real directory: {division_path}")
        divisions.append(
            _DivisionRoot(
                name=name,
                path=division_path,
                fingerprint=_directory_fingerprint(division_metadata),
            )
        )

    if _directory_fingerprint(os.lstat(root)) != root_fingerprint:
        raise RosterSyncError(f"roster directory changed during manifest discovery: {root}")
    if _file_fingerprint(os.lstat(manifest_path)) != manifest_fingerprint:
        raise RosterSyncError(f"division manifest changed during discovery: {manifest_path}")
    return _DivisionManifest(
        path=manifest_path,
        fingerprint=manifest_fingerprint,
        root_fingerprint=root_fingerprint,
        divisions=tuple(sorted(divisions, key=lambda division: division.name.casefold())),
    )


def _assert_division_manifest_unchanged(root: Path, manifest: _DivisionManifest) -> None:
    try:
        root_metadata = os.lstat(root)
        manifest_metadata = os.lstat(manifest.path)
    except OSError as exc:
        raise RosterSyncError("division manifest source changed during discovery") from exc
    if _directory_fingerprint(root_metadata) != manifest.root_fingerprint:
        raise RosterSyncError(f"roster directory changed during discovery: {root}")
    if (
        _metadata_is_link_or_reparse(manifest_metadata)
        or _file_fingerprint(manifest_metadata) != manifest.fingerprint
    ):
        raise RosterSyncError(f"division manifest changed during discovery: {manifest.path}")


def _directory_source_files(
    root: Path,
) -> list[
    tuple[
        Path,
        tuple[int, int, int, int, int, int],
        str | None,
    ]
]:
    root = _assert_real_path_chain(root)
    root_metadata = os.lstat(root)
    if _metadata_is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise RosterSyncError(f"roster directory must be a real directory: {root}")
    root_fingerprint = _directory_fingerprint(root_metadata)
    manifest = _load_division_manifest(root, root_fingerprint)
    if manifest is None:
        return [
            (path, fingerprint, None)
            for path, fingerprint in _directory_files(
                root,
                expected_root_fingerprint=root_fingerprint,
            )
        ]

    budget = _DiscoveryBudget()
    files: list[
        tuple[
            Path,
            tuple[int, int, int, int, int, int],
            str | None,
        ]
    ] = []
    for division in manifest.divisions:
        files.extend(
            (path, fingerprint, division.name)
            for path, fingerprint in _directory_files(
                division.path,
                expected_root_fingerprint=division.fingerprint,
                budget=budget,
                source_root=root,
            )
        )
    _assert_division_manifest_unchanged(root, manifest)
    return files


def _read_url(url: str) -> Iterator[_SourceDocument]:
    kind, target = _validate_source_spec(url)
    if kind == "http":
        target_url = str(target)
        data = _read_http_source(target_url)
        if data.lstrip().lower().startswith(("<!doctype html", "<html")):
            raise RosterSyncError(
                "roster source returned HTML; use a raw file, local directory, or generated agents.json"
            )
        yield _SourceDocument(_source_label(target_url), data)
        return

    path = _assert_real_path_chain(Path(target))
    metadata = os.lstat(path)
    if stat.S_ISDIR(metadata.st_mode):
        total = 0
        for child, fingerprint, inferred_division in _directory_source_files(path):
            content, size = _read_local_file(child, expected_fingerprint=fingerprint)
            total += size
            if total > MAX_TOTAL_SOURCE_BYTES:
                raise RosterSyncError(
                    f"roster source exceeds total limit of {MAX_TOTAL_SOURCE_BYTES} bytes: {path}"
                )
            yield _SourceDocument(
                str(child),
                content,
                inferred_division,
                child.relative_to(path).as_posix() if inferred_division is not None else None,
            )
        return
    if stat.S_ISREG(metadata.st_mode):
        content, _ = _read_local_file(path)
        yield _SourceDocument(str(path), content)
        return
    raise RosterSyncError(f"roster source must be a regular file or directory: {path}")


def download_from_source(url: str) -> RosterDownload:
    """Download and parse candidates from an HTTP(S), file, or directory source."""

    if isinstance(url, str) and url.casefold().startswith(("http://", "https://")):
        source_reference = _source_label(url)
    else:
        source_reference = url
    accumulator = _DownloadAccumulator(source_reference=source_reference)
    for raw_document in _read_url(url):
        if isinstance(raw_document, _SourceDocument):
            document = raw_document
        else:
            origin, content = raw_document
            document = _SourceDocument(origin, content)
        accumulator.ingest(document)
    return RosterDownload(accumulator.candidates, accumulator.outcomes)


def validate_agent(agent_dict: dict[str, Any]) -> tuple[bool, str]:
    """Validate an agent candidate shape and return ``(ok, reason)``."""

    agent = _normalize_agent(agent_dict)
    if not agent.get("slug") or not _SLUG_RE.match(agent["slug"]):
        return (
            False,
            "slug must be 2-128 lowercase letters/digits plus dot, underscore, or dash",
        )
    if not str(agent.get("name", "")).strip():
        return False, "name is required"
    if not str(agent.get("description", "")).strip():
        return False, "description is required"
    if not str(agent.get("prompt_body", "")).strip():
        return False, "prompt_body/content is required"
    return True, "ok"


def categorize_agent(agent: dict[str, Any]) -> list[str]:
    """Infer broad categories from an agent's metadata and prompt."""

    explicit = _json_list(agent.get("categories"))
    if explicit:
        return sorted(dict.fromkeys(item.lower() for item in explicit))

    text = " ".join(
        str(agent.get(key, ""))
        for key in ("slug", "name", "division", "description", "prompt_body")
    )
    tokens = set(_WORD_RE.findall(text.lower()))
    buckets = {
        "code": {
            "code",
            "developer",
            "engineering",
            "python",
            "javascript",
            "bug",
            "debug",
            "review",
        },
        "documentation": {
            "docs",
            "documentation",
            "writer",
            "writing",
            "readme",
            "runbook",
        },
        "planning": {
            "plan",
            "planning",
            "architect",
            "workflow",
            "orchestration",
            "strategy",
        },
        "research": {"research", "analysis", "market", "paper", "literature"},
        "operations": {"ops", "devops", "deploy", "runtime", "incident", "monitor"},
        "design": {"design", "ux", "ui", "visual", "frontend"},
    }
    categories = [name for name, words in buckets.items() if tokens & words]
    return categories or [str(agent.get("division") or "general").lower()]
