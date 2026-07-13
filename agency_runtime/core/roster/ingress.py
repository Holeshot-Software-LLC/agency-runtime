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
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.http_safety import open_no_redirect

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#_-]*", re.IGNORECASE)
_LIST_FIELDS = ("categories", "capabilities", "tool_affinity")
_METADATA_FIELDS = (
    "name",
    "division",
    "description",
    "source",
    "version",
    "prompt_path",
    "capabilities",
    "tool_affinity",
)

# Roster definitions are executable instructions. Keep every ingress and
# persistence boundary explicitly bounded so a trusted source cannot exhaust a
# host before quarantine/review has a chance to run.
MAX_HTTP_SOURCE_BYTES = 8 * 1024 * 1024
MAX_LOCAL_FILE_BYTES = 8 * 1024 * 1024
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
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_UNSAFE_TEXT_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
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
    if _UNSAFE_TEXT_CONTROL_RE.search(text):
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


def _normalize_agent(agent: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(agent, dict):
        raise RosterSyncError("agent must be a mapping")
    _validate_structure(agent, "agent")
    normalized = dict(agent)
    raw_slug = _require_bounded_text(
        normalized.get("slug") or normalized.get("id") or "",
        MAX_SHORT_TEXT_BYTES,
        "agent slug",
    )
    slug = raw_slug.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug).strip("-._")
    normalized["slug"] = slug
    normalized["name"] = _require_bounded_text(
        normalized.get("name") or (slug.replace("-", " ").title() if slug else ""),
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
    normalized["version"] = _require_bounded_text(
        normalized.get("version") or "1.0.0",
        MAX_SHORT_TEXT_BYTES,
        f"agent {slug or '<missing>'} version",
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
    for field in ("id", "download_id", "status"):
        if field in normalized:
            normalized[field] = _require_bounded_text(
                normalized[field], MAX_SHORT_TEXT_BYTES, f"agent {field}"
            )
    return normalized


def parse_agent_file(content: str) -> dict[str, Any]:
    """Parse a JSON/YAML/Markdown agent file into a normalized dict."""

    _require_bounded_text(content, MAX_AGENT_CONTENT_BYTES, "agent file")
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
        loaded = _load_yaml(match.group(1), "agent YAML front matter") or {}
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
    data["content"] = content
    data.setdefault("prompt_body", body)
    return _normalize_agent(data)


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
    local_value = urllib.request.url2pathname(unquote(parsed.path))
    if not local_value:
        raise RosterSyncError("file roster source must include a path")
    if local_value.startswith(("\\\\", "//")):
        raise RosterSyncError("remote file URL paths are not supported")
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


def _directory_files(
    root: Path,
) -> list[tuple[Path, tuple[int, int, int, int, int, int]]]:
    root = _assert_real_path_chain(root)
    root_metadata = os.lstat(root)
    if _metadata_is_link_or_reparse(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise RosterSyncError(f"roster directory must be a real directory: {root}")
    root_fingerprint = _directory_fingerprint(root_metadata)
    files: list[tuple[Path, tuple[int, int, int, int, int, int]]] = []
    entries_seen = 0
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
            entries_seen += 1
            if entries_seen > MAX_DIRECTORY_ENTRIES:
                raise RosterSyncError(
                    f"roster directory exceeds {MAX_DIRECTORY_ENTRIES} entries: {root}"
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
                if len(files) > MAX_SOURCE_FILES:
                    raise RosterSyncError(
                        f"roster source contains more than {MAX_SOURCE_FILES} agent files: {root}"
                    )
            elif child.suffix.lower() in _AGENT_FILE_SUFFIXES:
                raise RosterSyncError(f"roster source contains a non-regular agent file: {child}")
        # Reverse push preserves the case-insensitive sorted walk with a LIFO stack.
        pending.extend(reversed(child_directories))
    if _directory_fingerprint(os.lstat(root)) != root_fingerprint:
        raise RosterSyncError(f"roster directory changed during discovery: {root}")
    return files


def _read_url(url: str) -> Iterator[tuple[str, str]]:
    kind, target = _validate_source_spec(url)
    if kind == "http":
        target_url = str(target)
        data = _read_http_source(target_url)
        if data.lstrip().lower().startswith(("<!doctype html", "<html")):
            raise RosterSyncError(
                "roster source returned HTML; use a raw file, local directory, or generated agents.json"
            )
        yield _source_label(target_url), data
        return

    path = _assert_real_path_chain(Path(target))
    metadata = os.lstat(path)
    if stat.S_ISDIR(metadata.st_mode):
        total = 0
        for child, fingerprint in _directory_files(path):
            content, size = _read_local_file(child, expected_fingerprint=fingerprint)
            total += size
            if total > MAX_TOTAL_SOURCE_BYTES:
                raise RosterSyncError(
                    f"roster source exceeds total limit of {MAX_TOTAL_SOURCE_BYTES} bytes: {path}"
                )
            yield str(child), content
        return
    if stat.S_ISREG(metadata.st_mode):
        content, _ = _read_local_file(path)
        yield str(path), content
        return
    raise RosterSyncError(f"roster source must be a regular file or directory: {path}")


def download_from_source(url: str) -> list[dict[str, Any]]:
    """Download and parse candidates from an HTTP(S), file, or directory source."""

    if isinstance(url, str) and url.casefold().startswith(("http://", "https://")):
        source_reference = _source_label(url)
    else:
        source_reference = url
    candidates: list[dict[str, Any]] = []
    for origin, content in _read_url(url):
        stripped = content.strip()
        if stripped.startswith("["):
            loaded = _load_json(stripped, f"JSON roster at {origin}")
            if not isinstance(loaded, list):
                raise ValueError(f"JSON roster at {origin} must be a list")
            if len(candidates) + len(loaded) > MAX_SOURCE_CANDIDATES:
                raise RosterSyncError(
                    f"roster source contains more than {MAX_SOURCE_CANDIDATES} candidates: {source_reference}"
                )
            for raw_item in loaded:
                if not isinstance(raw_item, dict):
                    raise ValueError(f"JSON roster item at {origin} is not an object")
                item = dict(raw_item)
                item.setdefault(
                    "content",
                    _require_bounded_text(
                        json.dumps(item, sort_keys=True, separators=(",", ":")),
                        MAX_AGENT_CONTENT_BYTES,
                        f"agent content at {origin}",
                    ),
                )
                item["source"] = source_reference
                item["prompt_path"] = origin
                candidates.append(_normalize_agent(item))
        else:
            if len(candidates) >= MAX_SOURCE_CANDIDATES:
                raise RosterSyncError(
                    f"roster source contains more than {MAX_SOURCE_CANDIDATES} candidates: {source_reference}"
                )
            agent = parse_agent_file(content)
            agent["source"] = source_reference
            agent["prompt_path"] = origin
            candidates.append(_normalize_agent(agent))
    return candidates


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
