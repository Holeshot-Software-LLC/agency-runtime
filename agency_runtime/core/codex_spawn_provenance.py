"""Authenticate one Codex plaintext collaboration spawn from its rollout.

Codex's hook envelope does not carry the host's plaintext-delivery marker.  A
bounded, version-pinned validation of the canonical rollout ancestry supplies
that missing provenance without treating model-authored tool input as authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import stat
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Final
from uuid import RFC_4122, UUID

from agency_runtime.core.filesystem_trust import (
    absolute_path,
    directory_chain,
    metadata_is_link_or_reparse_point,
    same_file_identity,
)
from agency_runtime.core.store.security import (
    storage_file_is_trusted,
    storage_parent_is_trusted,
)

_SCHEMA: Final = "agency.codex-plaintext-spawn-attestation.v2"
_SUPPORTED_CLI_VERSION: Final = "0.147.0"
_MAX_PATH_BYTES: Final = 4 * 1024
_MAX_TRANSCRIPT_BYTES: Final = 64 * 1024 * 1024
_MAX_EXTERNAL_ANCESTRY_BYTES: Final = 64 * 1024 * 1024
_MAX_LINE_BYTES: Final = 4 * 1024 * 1024
_MAX_LINES: Final = 100_000
_MAX_ARGUMENT_BYTES: Final = 1024 * 1024
_MAX_JSON_DEPTH: Final = 64
_MAX_JSON_NODES: Final = 200_000
_READ_CHUNK: Final = 64 * 1024
_SPAWN_KEYS: Final = frozenset({"task_name", "message", "fork_turns", "model", "reasoning_effort"})
_REQUIRED_SPAWN_KEYS: Final = frozenset({"task_name", "message"})
_REASONING_EFFORTS: Final = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
# Codex 0.147's observed response-item schema plus the host contract's sole
# plaintext-delivery marker.  Any additional field requires a new pin.
_FUNCTION_CALL_KEYS: Final = frozenset(
    {
        "type",
        "namespace",
        "name",
        "arguments",
        "call_id",
        "id",
        "internal_chat_message_metadata_passthrough",
        "encrypted_function_args",
    }
)
_TASK_NAME = re.compile(r"^[a-z0-9_]{1,128}$")
_POSITIVE_DECIMAL = re.compile(r"^[1-9][0-9]*$")
_FUNCTION_ITEM_ID = re.compile(r"^fc_[0-9a-f]{50}$")
_CALL_ID = re.compile(r"^call_[A-Za-z0-9]{24}$")
_CODEX_TIMESTAMP = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$")
_CODEX_THREAD_ID_PATTERN: Final = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CODEX_THREAD_ID = re.compile(rf"^{_CODEX_THREAD_ID_PATTERN}$")
_THREAD_UUID_VERSIONS: Final = frozenset({7})
_TURN_UUID_VERSIONS: Final = frozenset({4, 7})
_MAX_ANCESTRY_DEPTH: Final = 2
_MAX_METADATA_TEXT_BYTES: Final = 1024
_MAX_METADATA_INSTRUCTIONS_BYTES: Final = 1024 * 1024
_MAX_ROLLOUT_DIRECTORY_ENTRIES: Final = 4096
_MIN_UTC_OFFSET_MINUTES: Final = -12 * 60
_MAX_UTC_OFFSET_MINUTES: Final = 14 * 60
_TUI_LINEAGE: Final = ("cli", "paginated", "codex-tui")
_EXEC_LINEAGE: Final = ("exec", "legacy", "codex_exec")
_SUPPORTED_LINEAGES: Final = frozenset({_TUI_LINEAGE, _EXEC_LINEAGE})
_SESSION_ENVELOPE_KEYS: Final = frozenset({"ordinal", "payload", "timestamp", "type"})
_ROOT_METADATA_KEYS: Final = frozenset(
    {
        "base_instructions",
        "cli_version",
        "context_window",
        "cwd",
        "git",
        "history_mode",
        "id",
        "model_provider",
        "originator",
        "session_id",
        "source",
        "thread_source",
        "timestamp",
    }
)
_SUBAGENT_METADATA_KEYS: Final = frozenset(
    {
        "agent_nickname",
        "agent_path",
        "base_instructions",
        "cli_version",
        "context_window",
        "cwd",
        "git",
        "history_mode",
        "id",
        "model_provider",
        "multi_agent_version",
        "originator",
        "parent_thread_id",
        "session_id",
        "source",
        "thread_source",
        "timestamp",
    }
)
_INHERITED_SUBAGENT_KEYS: Final = _SUBAGENT_METADATA_KEYS | {
    "forked_from_id",
    "subagent_history_start_ordinal",
}
_CAUSAL_CALL_KEYS: Final = frozenset(
    {
        "arguments",
        "call_id",
        "id",
        "internal_chat_message_metadata_passthrough",
        "name",
        "namespace",
        "type",
    }
)
_MARKED_CAUSAL_CALL_KEYS: Final = _CAUSAL_CALL_KEYS | {"encrypted_function_args"}
_CAUSAL_ARGUMENT_KEYS: Final = frozenset({"fork_turns", "message", "task_name"})
_CAUSAL_EVENT_KEYS: Final = frozenset(
    {"completed_at_ms", "item", "started_at_ms", "thread_id", "turn_id", "type"}
)
_CAUSAL_ITEM_KEYS: Final = frozenset({"agent_path", "agent_thread_id", "id", "kind", "type"})
_SEAL_KEY = secrets.token_bytes(32)


class _InvalidTranscript(ValueError):
    """Internal fail-open signal; no transcript content belongs in the error."""


@dataclass(frozen=True, slots=True)
class CodexPlaintextSpawnAttestation:
    """Opaque, content-free identity for one authenticated host spawn."""

    schema: str
    transcript_path: str
    sessions_root: str
    thread_id: str
    root_session_id: str
    ancestry_thread_ids: tuple[str, ...]
    ancestry_file_indexes: tuple[int, ...]
    ancestry_offsets: tuple[int, ...]
    ancestry_lengths: tuple[int, ...]
    ancestry_sha256: tuple[str, ...]
    turn_id: str
    tool_use_id: str
    function_item_id: str
    cli_version: str
    arguments_sha256: str
    file_device: int
    file_inode: int
    snapshot_size: int
    external_file_paths: tuple[str, ...]
    external_file_thread_ids: tuple[str, ...]
    external_file_utc_offset_minutes: tuple[int, ...]
    external_file_devices: tuple[int, ...]
    external_file_inodes: tuple[int, ...]
    external_file_snapshot_sizes: tuple[int, ...]
    external_file_snapshot_sha256: tuple[str, ...]
    external_edge_call_ids: tuple[str, ...]
    external_edge_function_item_ids: tuple[str, ...]
    external_edge_child_thread_ids: tuple[str, ...]
    external_record_file_indexes: tuple[int, ...]
    external_record_offsets: tuple[int, ...]
    external_record_lengths: tuple[int, ...]
    external_record_sha256: tuple[str, ...]
    task_offset: int
    task_length: int
    task_sha256: str
    call_offset: int
    call_length: int
    call_sha256: str
    seal: str


@dataclass(frozen=True, slots=True)
class _RecordIdentity:
    offset: int
    length: int
    digest: str


@dataclass(frozen=True, slots=True)
class _SessionRecord:
    identity: _RecordIdentity
    envelope: dict[str, Any]
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _ExternalFileEvidence:
    path: Path
    thread_id: str
    utc_offset_minutes: int
    device: int
    inode: int
    snapshot_size: int
    snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class _ExternalRolloutScan:
    sessions: tuple[_SessionRecord, ...]
    call_record: _RecordIdentity
    start_record: _RecordIdentity
    call_id: str
    function_item_id: str
    snapshot_sha256: str


@dataclass(frozen=True, slots=True)
class _CrossFileAncestry:
    thread_ids: tuple[str, ...]
    file_indexes: tuple[int, ...]
    identities: tuple[_RecordIdentity, ...]
    external_files: tuple[_ExternalFileEvidence, ...]
    edge_call_ids: tuple[str, ...]
    edge_function_item_ids: tuple[str, ...]
    edge_child_thread_ids: tuple[str, ...]
    supplemental_file_indexes: tuple[int, ...]
    supplemental_records: tuple[_RecordIdentity, ...]


def _codex_uuid(value: object, *, versions: frozenset[int]) -> bool:
    """Validate one canonical non-nil RFC UUID from the observed Codex domains."""

    if not isinstance(value, str) or _CODEX_THREAD_ID.fullmatch(value) is None:
        return False
    try:
        parsed = UUID(value)
    except ValueError:
        return False
    return bool(
        parsed.int
        and str(parsed) == value
        and parsed.variant == RFC_4122
        and parsed.version in versions
    )


def _json_depth_is_bounded(raw: bytes) -> bool:
    depth = 0
    in_string = False
    escaped = False
    for value in raw:
        character = chr(value)
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_JSON_DEPTH:
                return False
        elif character in "]}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and not in_string


def _strict_json(raw: bytes) -> Any:
    if not raw or not _json_depth_is_bounded(raw):
        raise _InvalidTranscript("invalid JSON boundary")

    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise _InvalidTranscript("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                _InvalidTranscript("non-finite JSON value")
            ),
        )
    except (_InvalidTranscript, RecursionError, UnicodeError, json.JSONDecodeError) as exc:
        raise _InvalidTranscript("malformed JSON") from exc
    stack = [(value, 1)]
    nodes = 0
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > _MAX_JSON_NODES or depth > _MAX_JSON_DEPTH:
            raise _InvalidTranscript("JSON structure exceeds bounds")
        if isinstance(current, dict):
            stack.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
    return value


def _canonical_tool_input(value: object) -> tuple[dict[str, Any], str]:
    if not isinstance(value, dict) or not value.keys() >= _REQUIRED_SPAWN_KEYS:
        raise _InvalidTranscript("spawn arguments are incomplete")
    if not value.keys() <= _SPAWN_KEYS:
        raise _InvalidTranscript("spawn argument schema is unsupported")
    task_name = value.get("task_name")
    message = value.get("message")
    if not isinstance(task_name, str) or _TASK_NAME.fullmatch(task_name) is None:
        raise _InvalidTranscript("task name is invalid")
    if not isinstance(message, str) or not message or len(message) > _MAX_ARGUMENT_BYTES:
        raise _InvalidTranscript("message is invalid")
    fork_turns = value.get("fork_turns")
    if fork_turns is not None and not (
        isinstance(fork_turns, str)
        and len(fork_turns) <= 16
        and (fork_turns in {"all", "none"} or (fork_turns.isdigit() and int(fork_turns) > 0))
    ):
        raise _InvalidTranscript("fork_turns is invalid")
    model = value.get("model")
    if model is not None and not (
        isinstance(model, str) and model and len(model.encode("utf-8")) <= 256
    ):
        raise _InvalidTranscript("model is invalid")
    effort = value.get("reasoning_effort")
    if effort is not None and effort not in _REASONING_EFFORTS:
        raise _InvalidTranscript("reasoning effort is invalid")
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, UnicodeError, ValueError) as exc:
        raise _InvalidTranscript("spawn arguments are not canonical JSON") from exc
    if len(encoded) > _MAX_ARGUMENT_BYTES:
        raise _InvalidTranscript("spawn arguments exceed bounds")
    frozen = _strict_json(encoded)
    if not isinstance(frozen, dict):
        raise _InvalidTranscript("spawn arguments are not an object")
    return frozen, hashlib.sha256(encoded).hexdigest()


def _active_sessions_root(environ: Mapping[str, str] | None) -> Path:
    source = os.environ if environ is None else environ
    configured = str(source.get("CODEX_HOME") or "").strip()
    home = Path(configured) if configured else Path.home() / ".codex"
    if not home.is_absolute() or any(part in {".", ".."} for part in home.parts):
        raise _InvalidTranscript("Codex home is not canonical")
    normalized = absolute_path(home)
    if home != normalized:
        raise _InvalidTranscript("Codex home is not canonical")
    return normalized / "sessions"


def _canonical_rollout_path(
    transcript_path: object,
    *,
    root_session_id: str,
    environ: Mapping[str, str] | None,
) -> tuple[Path, Path, str]:
    if not isinstance(transcript_path, (str, os.PathLike)):
        raise _InvalidTranscript("transcript path is unavailable")
    raw = os.fspath(transcript_path)
    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > _MAX_PATH_BYTES:
        raise _InvalidTranscript("transcript path exceeds bounds")
    if not _codex_uuid(root_session_id, versions=_THREAD_UUID_VERSIONS):
        raise _InvalidTranscript("session identity is invalid")
    candidate = Path(raw)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
        raise _InvalidTranscript("transcript path is not canonical")
    canonical = absolute_path(candidate)
    if candidate != canonical:
        raise _InvalidTranscript("transcript path is not canonical")
    sessions_root = _active_sessions_root(environ)
    thread_id, _local_clock = _canonical_rollout_details(canonical, sessions_root)
    return canonical, sessions_root, thread_id


def _canonical_rollout_details(path: Path, sessions_root: Path) -> tuple[str, datetime]:
    """Return the UUID suffix and naive local clock from one canonical rollout path."""

    if not path.is_absolute() or not sessions_root.is_absolute():
        raise _InvalidTranscript("transcript path is not absolute")
    if absolute_path(path) != path or absolute_path(sessions_root) != sessions_root:
        raise _InvalidTranscript("transcript path is not canonical")
    try:
        relative = path.relative_to(sessions_root)
    except ValueError as exc:
        raise _InvalidTranscript("transcript path is outside the active sessions root") from exc
    if len(relative.parts) != 4:
        raise _InvalidTranscript("transcript path shape is unsupported")
    year, month, day_value, filename = relative.parts
    if (
        re.fullmatch(r"[0-9]{4}", year) is None
        or re.fullmatch(r"[0-9]{2}", month) is None
        or re.fullmatch(r"[0-9]{2}", day_value) is None
    ):
        raise _InvalidTranscript("transcript date is not canonical")
    try:
        date_value = date(int(year), int(month), int(day_value))
    except (TypeError, ValueError) as exc:
        raise _InvalidTranscript("transcript date is invalid") from exc
    pattern = re.compile(
        rf"^rollout-{re.escape(year)}-{re.escape(month)}-{re.escape(day_value)}"
        rf"T(?P<hour>\d{{2}})-(?P<minute>\d{{2}})-(?P<second>\d{{2}})-"
        rf"(?P<thread_id>{_CODEX_THREAD_ID_PATTERN})\.jsonl$"
    )
    match = pattern.fullmatch(filename)
    if match is None:
        raise _InvalidTranscript("transcript filename is invalid")
    thread_id = match.group("thread_id")
    if not _codex_uuid(thread_id, versions=_THREAD_UUID_VERSIONS):
        raise _InvalidTranscript("transcript thread identity is invalid")
    try:
        time_value = time(
            int(match.group("hour")),
            int(match.group("minute")),
            int(match.group("second")),
        )
    except (TypeError, ValueError) as exc:
        raise _InvalidTranscript("transcript time is invalid") from exc
    return thread_id, datetime.combine(date_value, time_value)


def _uuid7_milliseconds(thread_id: str) -> int:
    if not _codex_uuid(thread_id, versions=_THREAD_UUID_VERSIONS):
        raise _InvalidTranscript("thread identity is invalid")
    return UUID(thread_id).int >> 80


def _derive_rollout_offset_minutes(path: Path, sessions_root: Path, thread_id: str) -> int:
    parsed_thread_id, local_clock = _canonical_rollout_details(path, sessions_root)
    if parsed_thread_id != thread_id:
        raise _InvalidTranscript("rollout thread identity does not match")
    utc_clock = datetime.fromtimestamp(
        _uuid7_milliseconds(thread_id) / 1000,
        timezone.utc,
    ).replace(tzinfo=None, microsecond=0)
    difference = local_clock - utc_clock
    total_seconds = int(difference.total_seconds())
    if difference != timedelta(seconds=total_seconds) or total_seconds % 60:
        raise _InvalidTranscript("rollout clock offset is not an integral minute")
    offset_minutes = total_seconds // 60
    if not _MIN_UTC_OFFSET_MINUTES <= offset_minutes <= _MAX_UTC_OFFSET_MINUTES:
        raise _InvalidTranscript("rollout clock offset is invalid")
    return offset_minutes


def _rollout_search_directories(sessions_root: Path, thread_id: str) -> tuple[Path, ...]:
    utc_day = datetime.fromtimestamp(
        _uuid7_milliseconds(thread_id) / 1000,
        timezone.utc,
    ).date()
    return tuple(
        sessions_root / f"{candidate.year:04d}" / f"{candidate.month:02d}" / f"{candidate.day:02d}"
        for candidate in (utc_day - timedelta(days=1), utc_day, utc_day + timedelta(days=1))
    )


def _rollout_directory_is_trusted(directory: Path, sessions_root: Path) -> bool:
    if (
        not directory.is_absolute()
        or absolute_path(directory) != directory
        or not sessions_root.is_absolute()
        or absolute_path(sessions_root) != sessions_root
    ):
        return False
    try:
        relative = directory.relative_to(sessions_root)
        chain = tuple((item, os.lstat(item)) for item in directory_chain(directory))
    except (OSError, ValueError):
        return False
    if len(relative.parts) != 3 or any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _item, metadata in chain
    ):
        return False
    try:
        expected = date(*(int(part) for part in relative.parts))
    except (TypeError, ValueError):
        return False
    if relative.parts != (
        f"{expected.year:04d}",
        f"{expected.month:02d}",
        f"{expected.day:02d}",
    ):
        return False
    is_windows = os.name == "nt"
    return bool(
        storage_parent_is_trusted(sessions_root, is_windows=is_windows)
        and storage_parent_is_trusted(directory, is_windows=is_windows)
    )


def _find_unique_rollout_for_thread(
    sessions_root: Path,
    *,
    thread_id: str,
) -> tuple[Path, int]:
    suffix = f"-{thread_id}.jsonl"
    matches: list[tuple[Path, int]] = []
    for directory in _rollout_search_directories(sessions_root, thread_id):
        try:
            before = os.lstat(directory)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise _InvalidTranscript("rollout date directory is unavailable") from exc
        if (
            metadata_is_link_or_reparse_point(before)
            or not stat.S_ISDIR(before.st_mode)
            or not _rollout_directory_is_trusted(directory, sessions_root)
        ):
            raise _InvalidTranscript("rollout date directory is not trusted")
        entries_seen = 0
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    entries_seen += 1
                    if entries_seen > _MAX_ROLLOUT_DIRECTORY_ENTRIES:
                        raise _InvalidTranscript("rollout date directory exceeds bounds")
                    if not entry.name.endswith(suffix):
                        continue
                    candidate = directory / entry.name
                    if len(os.fspath(candidate).encode("utf-8")) > _MAX_PATH_BYTES:
                        raise _InvalidTranscript("external rollout path exceeds bounds")
                    parsed_thread_id, _local_clock = _canonical_rollout_details(
                        candidate,
                        sessions_root,
                    )
                    metadata = entry.stat(follow_symlinks=False)
                    if (
                        parsed_thread_id != thread_id
                        or metadata_is_link_or_reparse_point(metadata)
                        or not stat.S_ISREG(metadata.st_mode)
                    ):
                        raise _InvalidTranscript("external rollout candidate is invalid")
                    matches.append(
                        (
                            candidate,
                            _derive_rollout_offset_minutes(
                                candidate,
                                sessions_root,
                                thread_id,
                            ),
                        )
                    )
        except _InvalidTranscript:
            raise
        except OSError as exc:
            raise _InvalidTranscript("rollout date directory could not be read") from exc
        try:
            after = os.lstat(directory)
        except OSError as exc:
            raise _InvalidTranscript("rollout date directory changed") from exc
        if not same_file_identity(before, after) or not _rollout_directory_is_trusted(
            directory, sessions_root
        ):
            raise _InvalidTranscript("rollout date directory changed")
    if len(matches) != 1:
        raise _InvalidTranscript("external rollout lookup is missing or ambiguous")
    return matches[0]


def _path_is_trusted(path: Path, sessions_root: Path) -> bool:
    is_windows = os.name == "nt"
    try:
        chain = tuple((item, os.lstat(item)) for item in directory_chain(path.parent))
    except OSError:
        return False
    if any(
        metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode)
        for _item, metadata in chain
    ):
        return False
    return bool(
        storage_parent_is_trusted(sessions_root, is_windows=is_windows)
        and storage_parent_is_trusted(path.parent, is_windows=is_windows)
        and storage_file_is_trusted(path, is_windows=is_windows)
    )


def _open_rollout(path: Path, sessions_root: Path) -> tuple[int, os.stat_result]:
    if not _path_is_trusted(path, sessions_root):
        raise _InvalidTranscript("transcript storage is not trusted")
    before = os.lstat(path)
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOINHERIT", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise _InvalidTranscript("transcript could not be opened") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not same_file_identity(before, opened)
            or not stat.S_ISREG(opened.st_mode)
            or int(getattr(opened, "st_nlink", 0) or 0) != 1
            or opened.st_size <= 0
            or opened.st_size > _MAX_TRANSCRIPT_BYTES
        ):
            raise _InvalidTranscript("transcript identity is invalid")
    except Exception:
        os.close(descriptor)
        raise
    return descriptor, opened


def _snapshot_lines(descriptor: int, size: int, *, start: int = 0):
    if start < 0 or start > size:
        raise _InvalidTranscript("transcript range is invalid")
    os.lseek(descriptor, start, os.SEEK_SET)
    remaining = size - start
    buffer = b""
    offset = start
    lines = 0
    while remaining:
        chunk = os.read(descriptor, min(_READ_CHUNK, remaining))
        if not chunk:
            raise _InvalidTranscript("transcript was truncated")
        remaining -= len(chunk)
        buffer += chunk
        while True:
            newline = buffer.find(b"\n")
            if newline < 0:
                break
            raw = buffer[: newline + 1]
            buffer = buffer[newline + 1 :]
            lines += 1
            if lines > _MAX_LINES or len(raw) > _MAX_LINE_BYTES:
                raise _InvalidTranscript("transcript line bounds exceeded")
            yield offset, raw
            offset += len(raw)
        if len(buffer) > _MAX_LINE_BYTES:
            raise _InvalidTranscript("transcript line bounds exceeded")
    if buffer:
        raise _InvalidTranscript("transcript has an incomplete final record")


def _identity(offset: int, raw: bytes) -> _RecordIdentity:
    return _RecordIdentity(offset, len(raw), hashlib.sha256(raw).hexdigest())


def _payload(record: object) -> tuple[str, dict[str, Any]]:
    if not isinstance(record, dict):
        return "", {}
    payload = record.get("payload")
    return str(record.get("type") or ""), payload if isinstance(payload, dict) else {}


def _function_call_is_exact(
    payload: dict[str, Any],
    *,
    turn_id: str,
    expected_input: dict[str, Any],
) -> bool:
    if set(payload) != _FUNCTION_CALL_KEYS:
        return False
    item_id = payload.get("id")
    if not isinstance(item_id, str) or _FUNCTION_ITEM_ID.fullmatch(item_id) is None:
        return False
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if (
        not isinstance(metadata, dict)
        or set(metadata) != {"turn_id"}
        or metadata.get("turn_id") != turn_id
    ):
        return False
    if payload["encrypted_function_args"] != []:
        return False
    arguments = payload.get("arguments")
    if not isinstance(arguments, str) or len(arguments.encode("utf-8")) > _MAX_ARGUMENT_BYTES:
        return False
    parsed = _strict_json(arguments.encode("utf-8"))
    if not isinstance(parsed, dict):
        return False
    canonical, _digest_value = _canonical_tool_input(parsed)
    return canonical == expected_input


def _target_response_envelope_is_exact(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    keys = set(record)
    if keys not in (
        {"timestamp", "type", "payload"},
        {"timestamp", "type", "payload", "ordinal"},
    ):
        return False
    timestamp = record.get("timestamp")
    if not isinstance(timestamp, str) or _CODEX_TIMESTAMP.fullmatch(timestamp) is None:
        return False
    try:
        datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return False
    if "ordinal" in record:
        ordinal = record["ordinal"]
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            return False
    return True


def _function_item_is_unique(descriptor: int, size: int, *, item_id: str) -> bool:
    matches = 0
    for _offset, raw in _snapshot_lines(descriptor, size):
        outer_type, payload = _payload(_strict_json(raw))
        if outer_type == "response_item" and payload.get("id") == item_id:
            matches += 1
            if matches > 1:
                return False
    return matches == 1


def _bounded_metadata_text(value: object, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    return bool(
        isinstance(value, str) and value and len(value.encode("utf-8")) <= _MAX_METADATA_TEXT_BYTES
    )


def _agent_path_is_canonical(value: object) -> bool:
    if not _bounded_metadata_text(value) or not isinstance(value, str):
        return False
    parts = value.split("/")
    return bool(
        len(parts) >= 3
        and parts[:2] == ["", "root"]
        and all(_TASK_NAME.fullmatch(part) is not None for part in parts[2:])
    )


def _root_session_lineage(
    payload: dict[str, Any],
    *,
    root_session_id: str,
) -> tuple[str, str, str] | None:
    if (
        payload.get("id") != root_session_id
        or payload.get("session_id") != root_session_id
        or payload.get("cli_version") != _SUPPORTED_CLI_VERSION
        or payload.get("thread_source") != "user"
        or "forked_from_id" in payload
        or "parent_thread_id" in payload
    ):
        return None
    lineage = (
        payload.get("source"),
        payload.get("history_mode"),
        payload.get("originator"),
    )
    return lineage if lineage in _SUPPORTED_LINEAGES else None


def _subagent_session_depth(
    payload: dict[str, Any],
    *,
    thread_id: str,
    root_session_id: str,
    parent_thread_id: str,
    lineage: tuple[str, str, str],
    inherited: bool = True,
) -> int | None:
    if (
        not _codex_uuid(parent_thread_id, versions=_THREAD_UUID_VERSIONS)
        or not _codex_uuid(root_session_id, versions=_THREAD_UUID_VERSIONS)
        or payload.get("id") != thread_id
        or payload.get("session_id") != root_session_id
        or payload.get("cli_version") != _SUPPORTED_CLI_VERSION
        or payload.get("parent_thread_id") != parent_thread_id
        or payload.get("thread_source") != "subagent"
        or payload.get("history_mode") != lineage[1]
        or payload.get("originator") != lineage[2]
        or payload.get("multi_agent_version") != "v2"
    ):
        return None
    if inherited:
        if payload.get("forked_from_id") != parent_thread_id:
            return None
        history_start = payload.get("subagent_history_start_ordinal")
        if lineage == _TUI_LINEAGE and (
            isinstance(history_start, bool)
            or not isinstance(history_start, int)
            or history_start < 0
        ):
            return None
        if lineage == _EXEC_LINEAGE and history_start is not None:
            return None
    elif (
        lineage != _TUI_LINEAGE
        or "forked_from_id" in payload
        or "subagent_history_start_ordinal" in payload
    ):
        return None
    source = payload.get("source")
    if not isinstance(source, dict) or set(source) != {"subagent"}:
        return None
    subagent = source.get("subagent")
    if not isinstance(subagent, dict) or set(subagent) != {"thread_spawn"}:
        return None
    spawn = subagent.get("thread_spawn")
    if not isinstance(spawn, dict) or set(spawn) != {
        "parent_thread_id",
        "depth",
        "agent_path",
        "agent_nickname",
        "agent_role",
    }:
        return None
    depth = spawn.get("depth")
    if (
        spawn.get("parent_thread_id") != parent_thread_id
        or isinstance(depth, bool)
        or not isinstance(depth, int)
        or not 1 <= depth <= _MAX_ANCESTRY_DEPTH
        or not _agent_path_is_canonical(spawn.get("agent_path"))
        or not _bounded_metadata_text(spawn.get("agent_nickname"))
        or not _bounded_metadata_text(spawn.get("agent_role"), nullable=True)
        or payload.get("agent_path") != spawn.get("agent_path")
        or payload.get("agent_nickname") != spawn.get("agent_nickname")
    ):
        return None
    return depth


def _exact_codex_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or _CODEX_TIMESTAMP.fullmatch(value) is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _metadata_envelope_is_exact(record: _SessionRecord, *, ordinal: int) -> bool:
    envelope = record.envelope
    timestamp = envelope.get("timestamp")
    return bool(
        set(envelope) == _SESSION_ENVELOPE_KEYS
        and envelope.get("type") == "session_meta"
        and envelope.get("ordinal") == ordinal
        and not isinstance(envelope.get("ordinal"), bool)
        and _exact_codex_timestamp(timestamp) is not None
    )


def _metadata_common_payload_is_exact(payload: dict[str, Any]) -> bool:
    timestamp = payload.get("timestamp")
    base = payload.get("base_instructions")
    context = payload.get("context_window")
    git = payload.get("git")
    if (
        _exact_codex_timestamp(timestamp) is None
        or not _bounded_metadata_text(payload.get("cwd"))
        or not _bounded_metadata_text(payload.get("model_provider"))
        or not isinstance(base, dict)
        or set(base) != {"text"}
        or not isinstance(base.get("text"), str)
        or len(base["text"].encode("utf-8")) > _MAX_METADATA_INSTRUCTIONS_BYTES
        or not isinstance(context, dict)
        or set(context) != {"window_id"}
        or not _codex_uuid(context.get("window_id"), versions=_THREAD_UUID_VERSIONS)
        or not isinstance(git, dict)
        or set(git) != {"branch", "commit_hash", "repository_url"}
    ):
        return False
    return all(
        value is None or _bounded_metadata_text(value)
        for value in (git.get("branch"), git.get("commit_hash"), git.get("repository_url"))
    )


def _cross_file_root_metadata_is_exact(
    record: _SessionRecord,
    *,
    root_session_id: str,
    ordinal: int = 0,
) -> bool:
    return bool(
        _metadata_envelope_is_exact(record, ordinal=ordinal)
        and set(record.payload) == _ROOT_METADATA_KEYS
        and _metadata_common_payload_is_exact(record.payload)
        and _root_session_lineage(record.payload, root_session_id=root_session_id) == _TUI_LINEAGE
    )


def _cross_file_subagent_metadata(
    record: _SessionRecord,
    *,
    thread_id: str,
    root_session_id: str,
    parent_thread_id: str,
    expected_depth: int,
) -> tuple[bool, str] | None:
    payload = record.payload
    inherited = "forked_from_id" in payload or "subagent_history_start_ordinal" in payload
    expected_keys = _INHERITED_SUBAGENT_KEYS if inherited else _SUBAGENT_METADATA_KEYS
    source = payload.get("source")
    spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
    if (
        not _metadata_envelope_is_exact(record, ordinal=0)
        or set(payload) != expected_keys
        or not _metadata_common_payload_is_exact(payload)
        or _subagent_session_depth(
            payload,
            thread_id=thread_id,
            root_session_id=root_session_id,
            parent_thread_id=parent_thread_id,
            lineage=_TUI_LINEAGE,
            inherited=inherited,
        )
        != expected_depth
        or not isinstance(spawn, dict)
        or spawn.get("agent_role") is not None
    ):
        return None
    agent_path = payload.get("agent_path")
    if not isinstance(agent_path, str):
        return None
    return inherited, agent_path


def _validate_session_ancestry(
    sessions: list[_SessionRecord],
    *,
    thread_id: str,
    root_session_id: str,
) -> tuple[tuple[_RecordIdentity, ...], tuple[str, ...]]:
    # This compatibility path accepts one root metadata record, or exactly two
    # leading records for a fully materialized fork. Authentic one-record TUI
    # forks are handled by the separately pinned cross-file authority. A
    # supported in-file depth-two rollout contains its current and immediate-
    # parent records; the latter authenticates its own root link. Deeper forks
    # and one-record exec forks remain unsupported.
    if len(sessions) not in {1, 2}:
        raise _InvalidTranscript("session ancestry shape is unsupported")
    thread_ids = tuple(str(record.payload.get("id") or "") for record in sessions)
    if (
        thread_ids[0] != thread_id
        or len(set(thread_ids)) != len(thread_ids)
        or any(not _codex_uuid(value, versions=_THREAD_UUID_VERSIONS) for value in thread_ids)
    ):
        raise _InvalidTranscript("session ancestry identities do not match")
    if len(sessions) == 1:
        if (
            thread_id != root_session_id
            or _root_session_lineage(sessions[0].payload, root_session_id=root_session_id) is None
        ):
            raise _InvalidTranscript("root session metadata does not match")
        return (sessions[0].identity,), thread_ids

    if thread_id == root_session_id:
        raise _InvalidTranscript("forked session identity does not match")
    child_mode = (
        str(sessions[0].payload.get("history_mode") or ""),
        str(sessions[0].payload.get("originator") or ""),
    )
    # A child has a structured source record, so its root source is recovered
    # from the exact observed history/originator pair instead.
    lineage = next(
        (candidate for candidate in _SUPPORTED_LINEAGES if candidate[1:] == child_mode),
        None,
    )
    if lineage is None:
        raise _InvalidTranscript("child session lineage is unsupported")
    current_depth = _subagent_session_depth(
        sessions[0].payload,
        thread_id=thread_id,
        root_session_id=root_session_id,
        parent_thread_id=thread_ids[1],
        lineage=lineage,
    )
    if current_depth == 1:
        if (
            thread_ids[1] != root_session_id
            or _root_session_lineage(sessions[1].payload, root_session_id=root_session_id)
            != lineage
        ):
            raise _InvalidTranscript("root parent metadata does not match")
    elif current_depth == 2:
        if (
            lineage != _TUI_LINEAGE
            or thread_ids[1] == root_session_id
            or _subagent_session_depth(
                sessions[1].payload,
                thread_id=thread_ids[1],
                root_session_id=root_session_id,
                parent_thread_id=root_session_id,
                lineage=lineage,
            )
            != 1
        ):
            raise _InvalidTranscript("depth-two parent metadata does not match")
    else:
        raise _InvalidTranscript("fork depth is unsupported")
    return tuple(record.identity for record in sessions), thread_ids


def _causal_envelope_is_exact(record: object) -> bool:
    if not isinstance(record, dict) or set(record) != _SESSION_ENVELOPE_KEYS:
        return False
    ordinal = record.get("ordinal")
    return bool(
        _exact_codex_timestamp(record.get("timestamp")) is not None
        and not isinstance(ordinal, bool)
        and isinstance(ordinal, int)
        and ordinal >= 0
    )


def _causal_arguments(payload: dict[str, Any]) -> tuple[str, str] | None:
    keys = set(payload)
    if keys == _CAUSAL_CALL_KEYS:
        pass
    elif keys != _MARKED_CAUSAL_CALL_KEYS or payload.get("encrypted_function_args") != []:
        return None
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if (
        payload.get("type") != "function_call"
        or payload.get("namespace") != "collaboration"
        or payload.get("name") != "spawn_agent"
        or not isinstance(payload.get("call_id"), str)
        or _CALL_ID.fullmatch(payload["call_id"]) is None
        or not isinstance(payload.get("id"), str)
        or _FUNCTION_ITEM_ID.fullmatch(payload["id"]) is None
        or not isinstance(metadata, dict)
        or set(metadata) != {"turn_id"}
        or not _codex_uuid(metadata.get("turn_id"), versions=_TURN_UUID_VERSIONS)
    ):
        return None
    raw_arguments = payload.get("arguments")
    if (
        not isinstance(raw_arguments, str)
        or not raw_arguments
        or len(raw_arguments.encode("utf-8")) > _MAX_ARGUMENT_BYTES
    ):
        return None
    arguments = _strict_json(raw_arguments.encode("utf-8"))
    if not isinstance(arguments, dict) or set(arguments) != _CAUSAL_ARGUMENT_KEYS:
        return None
    task_name = arguments.get("task_name")
    message = arguments.get("message")
    fork_turns = arguments.get("fork_turns")
    if (
        not isinstance(task_name, str)
        or _TASK_NAME.fullmatch(task_name) is None
        or not isinstance(message, str)
        or not message
        or len(message.encode("utf-8")) > _MAX_ARGUMENT_BYTES
        or not isinstance(fork_turns, str)
        or not (fork_turns in {"all", "none"} or (fork_turns.isdigit() and int(fork_turns) > 0))
    ):
        return None
    return task_name, fork_turns


def _causal_pair_is_exact(
    call_record: object,
    start_record: object,
    *,
    parent_thread_id: str,
    child_thread_id: str,
    parent_agent_path: str | None,
    child_agent_path: str,
    inherited: bool,
) -> tuple[str, str, str] | None:
    if (
        not _causal_envelope_is_exact(call_record)
        or not _causal_envelope_is_exact(start_record)
        or call_record.get("type") != "response_item"
        or start_record.get("type") != "event_msg"
        or start_record.get("ordinal") != call_record.get("ordinal") + 1
    ):
        return None
    call_payload = call_record.get("payload")
    start_payload = start_record.get("payload")
    if not isinstance(call_payload, dict) or not isinstance(start_payload, dict):
        return None
    parsed_arguments = _causal_arguments(call_payload)
    item = start_payload.get("item")
    started = start_payload.get("started_at_ms")
    completed = start_payload.get("completed_at_ms")
    if (
        parsed_arguments is None
        or set(start_payload) != _CAUSAL_EVENT_KEYS
        or start_payload.get("type") != "item_completed"
        or start_payload.get("thread_id") != parent_thread_id
        or start_payload.get("turn_id")
        != call_payload["internal_chat_message_metadata_passthrough"]["turn_id"]
        or isinstance(started, bool)
        or not isinstance(started, int)
        or started < 0
        or isinstance(completed, bool)
        or not isinstance(completed, int)
        or completed < 0
        or completed != started
        or not isinstance(item, dict)
        or set(item) != _CAUSAL_ITEM_KEYS
        or item.get("type") != "SubAgentActivity"
        or item.get("kind") != "started"
        or item.get("id") != call_payload.get("call_id")
        or item.get("agent_thread_id") != child_thread_id
        or item.get("agent_path") != child_agent_path
    ):
        return None
    task_name, fork_turns = parsed_arguments
    expected_path = (
        f"{parent_agent_path}/{task_name}"
        if parent_agent_path is not None
        else f"/root/{task_name}"
    )
    if (
        child_agent_path != expected_path
        or (not inherited and fork_turns != "none")
        or (inherited and fork_turns != "all" and _POSITIVE_DECIMAL.fullmatch(fork_turns) is None)
    ):
        return None
    call_timestamp = _exact_codex_timestamp(call_record.get("timestamp"))
    start_timestamp = _exact_codex_timestamp(start_record.get("timestamp"))
    child_timestamp = datetime.fromtimestamp(
        _uuid7_milliseconds(child_thread_id) / 1000,
        timezone.utc,
    )
    if (
        call_timestamp is None
        or start_timestamp is None
        or int(start_timestamp.timestamp() * 1000) != started
        or not call_timestamp <= child_timestamp <= start_timestamp
    ):
        return None
    return str(call_payload["call_id"]), str(call_payload["id"]), fork_turns


def _scan_external_rollout(
    descriptor: int,
    size: int,
    *,
    parent_thread_id: str,
    child_thread_id: str,
    parent_agent_path: str | None,
    child_agent_path: str,
    inherited: bool,
) -> _ExternalRolloutScan:
    sessions: list[_SessionRecord] = []
    metadata_closed = False
    previous: tuple[int, bytes, object] | None = None
    matches: list[tuple[_RecordIdentity, _RecordIdentity, str, str]] = []
    child_mentions = 0
    call_id_counts: dict[str, int] = {}
    payload_id_counts: dict[str, int] = {}
    item_id_counts: dict[str, int] = {}
    digest = hashlib.sha256()
    for offset, raw in _snapshot_lines(descriptor, size):
        digest.update(raw)
        record = _strict_json(raw)
        outer_type, payload = _payload(record)
        if outer_type == "session_meta":
            if metadata_closed or len(sessions) >= 2 or not isinstance(record, dict):
                raise _InvalidTranscript("external session metadata ordering is unsupported")
            sessions.append(_SessionRecord(_identity(offset, raw), record, payload))
        else:
            metadata_closed = True
        call_id_value = payload.get("call_id")
        if payload.get("type") == "function_call" and isinstance(call_id_value, str):
            call_id_counts[call_id_value] = call_id_counts.get(call_id_value, 0) + 1
        payload_id = payload.get("id")
        if isinstance(payload_id, str):
            payload_id_counts[payload_id] = payload_id_counts.get(payload_id, 0) + 1
        item = payload.get("item")
        if isinstance(item, dict):
            item_id = item.get("id")
            if isinstance(item_id, str):
                item_id_counts[item_id] = item_id_counts.get(item_id, 0) + 1
        if (
            isinstance(item, dict)
            and item.get("agent_thread_id") == child_thread_id
            and item.get("kind") == "started"
        ):
            child_mentions += 1
            if previous is None:
                raise _InvalidTranscript("causal child event has no launch")
            call_offset, call_raw, call_record = previous
            pair = _causal_pair_is_exact(
                call_record,
                record,
                parent_thread_id=parent_thread_id,
                child_thread_id=child_thread_id,
                parent_agent_path=parent_agent_path,
                child_agent_path=child_agent_path,
                inherited=inherited,
            )
            if pair is None:
                raise _InvalidTranscript("causal child launch does not match")
            matches.append(
                (
                    _identity(call_offset, call_raw),
                    _identity(offset, raw),
                    pair[0],
                    pair[1],
                )
            )
        previous = (offset, raw, record)
    if not sessions:
        raise _InvalidTranscript("external session metadata is missing")
    if child_mentions != 1 or len(matches) != 1:
        raise _InvalidTranscript("causal child launch is ambiguous")
    call_identity, start_identity, call_id, function_item_id = matches[0]
    if (
        call_id_counts.get(call_id) != 1
        or payload_id_counts.get(function_item_id) != 1
        or item_id_counts.get(call_id) != 1
    ):
        raise _InvalidTranscript("causal launch identity is ambiguous")
    return _ExternalRolloutScan(
        sessions=tuple(sessions),
        call_record=call_identity,
        start_record=start_identity,
        call_id=call_id,
        function_item_id=function_item_id,
        snapshot_sha256=digest.hexdigest(),
    )


def _snapshot_is_still_exact(
    descriptor: int,
    *,
    path: Path,
    sessions_root: Path,
    opened: os.stat_result,
    snapshot_size: int,
    allow_append: bool = False,
) -> bool:
    after = os.fstat(descriptor)
    lexical = os.lstat(path)
    return bool(
        (
            int(after.st_size) >= snapshot_size
            if allow_append
            else int(after.st_size) == snapshot_size
        )
        and same_file_identity(opened, after)
        and same_file_identity(after, lexical)
        and _path_is_trusted(path, sessions_root)
    )


def _open_external_rollout(
    path: Path,
    *,
    sessions_root: Path,
    expected_thread_id: str,
    expected_utc_offset_minutes: int,
) -> tuple[int, os.stat_result]:
    parsed_thread_id, _clock = _canonical_rollout_details(path, sessions_root)
    if (
        parsed_thread_id != expected_thread_id
        or _derive_rollout_offset_minutes(path, sessions_root, expected_thread_id)
        != expected_utc_offset_minutes
    ):
        raise _InvalidTranscript("external rollout identity does not match")
    return _open_rollout(path, sessions_root)


def _snapshot_sha256(descriptor: int, size: int) -> str:
    if size <= 0 or size > _MAX_TRANSCRIPT_BYTES:
        raise _InvalidTranscript("transcript snapshot bounds are invalid")
    os.lseek(descriptor, 0, os.SEEK_SET)
    remaining = size
    digest = hashlib.sha256()
    while remaining:
        chunk = os.read(descriptor, min(_READ_CHUNK, remaining))
        if not chunk:
            raise _InvalidTranscript("transcript snapshot was truncated")
        digest.update(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def _resolve_cross_file_ancestry(  # noqa: C901 - one bounded ancestry transaction
    current: _SessionRecord,
    *,
    current_path: Path,
    sessions_root: Path,
    thread_id: str,
    root_session_id: str,
) -> _CrossFileAncestry:
    payload = current.payload
    parent_thread_id = payload.get("parent_thread_id")
    source = payload.get("source")
    spawn = source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
    depth = spawn.get("depth") if isinstance(spawn, dict) else None
    if (
        thread_id == root_session_id
        or not _codex_uuid(parent_thread_id, versions=_THREAD_UUID_VERSIONS)
        or isinstance(depth, bool)
        or depth not in {1, 2}
    ):
        raise _InvalidTranscript("cross-file ancestry shape is unsupported")
    current_metadata = _cross_file_subagent_metadata(
        current,
        thread_id=thread_id,
        root_session_id=root_session_id,
        parent_thread_id=parent_thread_id,
        expected_depth=depth,
    )
    if current_metadata is None:
        raise _InvalidTranscript("cross-file current metadata does not match")
    current_inherited, current_agent_path = current_metadata
    parent_agent_path_hint = current_agent_path.rsplit("/", 1)[0] if depth == 2 else None
    if (depth == 1 and parent_thread_id != root_session_id) or (
        depth == 2 and parent_thread_id == root_session_id
    ):
        raise _InvalidTranscript("cross-file parent identity does not match depth")
    identities = {thread_id, parent_thread_id, root_session_id}
    if len(identities) != (2 if depth == 1 else 3):
        raise _InvalidTranscript("cross-file ancestry contains a cycle")
    root_time = UUID(root_session_id).int
    parent_time = UUID(parent_thread_id).int
    child_time = UUID(thread_id).int
    if not root_time <= parent_time < child_time:
        raise _InvalidTranscript("cross-file ancestry time order is invalid")

    _derive_rollout_offset_minutes(current_path, sessions_root, thread_id)
    root_path, root_offset_minutes = _find_unique_rollout_for_thread(
        sessions_root,
        thread_id=root_session_id,
    )
    if depth == 1:
        parent_path = root_path
        parent_offset_minutes = root_offset_minutes
    else:
        parent_path, parent_offset_minutes = _find_unique_rollout_for_thread(
            sessions_root,
            thread_id=parent_thread_id,
        )
    if current_path in {root_path, parent_path} or (depth == 2 and root_path == parent_path):
        raise _InvalidTranscript("cross-file rollout paths are not unique")

    descriptors: list[int] = []
    try:
        root_descriptor, root_opened = _open_external_rollout(
            root_path,
            sessions_root=sessions_root,
            expected_thread_id=root_session_id,
            expected_utc_offset_minutes=root_offset_minutes,
        )
        descriptors.append(root_descriptor)
        root_size = int(root_opened.st_size)
        if root_size > _MAX_EXTERNAL_ANCESTRY_BYTES:
            raise _InvalidTranscript("external ancestry exceeds aggregate bounds")
        root_scan = _scan_external_rollout(
            root_descriptor,
            root_size,
            parent_thread_id=root_session_id,
            child_thread_id=thread_id if depth == 1 else parent_thread_id,
            parent_agent_path=None,
            child_agent_path=(current_agent_path if depth == 1 else str(parent_agent_path_hint)),
            inherited=current_inherited if depth == 1 else True,
        )
        root_prefix = root_scan.sessions
        root_evidence = _ExternalFileEvidence(
            path=root_path,
            thread_id=root_session_id,
            utc_offset_minutes=root_offset_minutes,
            device=int(root_opened.st_dev),
            inode=int(root_opened.st_ino),
            snapshot_size=root_size,
            snapshot_sha256=root_scan.snapshot_sha256,
        )
        if len(root_prefix) != 1 or not _cross_file_root_metadata_is_exact(
            root_prefix[0],
            root_session_id=root_session_id,
        ):
            raise _InvalidTranscript("canonical root metadata does not match")

        if depth == 1:
            if not _snapshot_is_still_exact(
                root_descriptor,
                path=root_path,
                sessions_root=sessions_root,
                opened=root_opened,
                snapshot_size=root_evidence.snapshot_size,
                allow_append=True,
            ):
                raise _InvalidTranscript("canonical root rollout changed")
            return _CrossFileAncestry(
                thread_ids=(thread_id, root_session_id),
                file_indexes=(0, 1),
                identities=(current.identity, root_prefix[0].identity),
                external_files=(root_evidence,),
                edge_call_ids=(root_scan.call_id,),
                edge_function_item_ids=(root_scan.function_item_id,),
                edge_child_thread_ids=(thread_id,),
                supplemental_file_indexes=(1, 1),
                supplemental_records=(root_scan.call_record, root_scan.start_record),
            )

        parent_descriptor, parent_opened = _open_external_rollout(
            parent_path,
            sessions_root=sessions_root,
            expected_thread_id=parent_thread_id,
            expected_utc_offset_minutes=parent_offset_minutes,
        )
        descriptors.append(parent_descriptor)
        parent_size = int(parent_opened.st_size)
        if root_size + parent_size > _MAX_EXTERNAL_ANCESTRY_BYTES:
            raise _InvalidTranscript("external ancestry exceeds aggregate bounds")
        parent_scan = _scan_external_rollout(
            parent_descriptor,
            parent_size,
            parent_thread_id=parent_thread_id,
            child_thread_id=thread_id,
            parent_agent_path=parent_agent_path_hint,
            child_agent_path=current_agent_path,
            inherited=current_inherited,
        )
        parent_prefix = parent_scan.sessions
        if len(parent_prefix) != 2:
            raise _InvalidTranscript("canonical parent metadata prefix does not match")
        parent_metadata = _cross_file_subagent_metadata(
            parent_prefix[0],
            thread_id=parent_thread_id,
            root_session_id=root_session_id,
            parent_thread_id=root_session_id,
            expected_depth=1,
        )
        if (
            parent_metadata is None
            or not parent_metadata[0]
            or parent_metadata[1] != parent_agent_path_hint
            or not _cross_file_root_metadata_is_exact(
                parent_prefix[1],
                root_session_id=root_session_id,
                ordinal=1,
            )
            or parent_prefix[1].payload != root_prefix[0].payload
        ):
            raise _InvalidTranscript("canonical parent/root lineage does not match")
        parent_evidence = _ExternalFileEvidence(
            path=parent_path,
            thread_id=parent_thread_id,
            utc_offset_minutes=parent_offset_minutes,
            device=int(parent_opened.st_dev),
            inode=int(parent_opened.st_ino),
            snapshot_size=parent_size,
            snapshot_sha256=parent_scan.snapshot_sha256,
        )
        if not _snapshot_is_still_exact(
            parent_descriptor,
            path=parent_path,
            sessions_root=sessions_root,
            opened=parent_opened,
            snapshot_size=parent_evidence.snapshot_size,
            allow_append=True,
        ) or not _snapshot_is_still_exact(
            root_descriptor,
            path=root_path,
            sessions_root=sessions_root,
            opened=root_opened,
            snapshot_size=root_evidence.snapshot_size,
            allow_append=True,
        ):
            raise _InvalidTranscript("cross-file ancestry changed during attestation")
        return _CrossFileAncestry(
            thread_ids=(thread_id, parent_thread_id, root_session_id),
            file_indexes=(0, 1, 2),
            identities=(
                current.identity,
                parent_prefix[0].identity,
                root_prefix[0].identity,
            ),
            external_files=(parent_evidence, root_evidence),
            edge_call_ids=(parent_scan.call_id, root_scan.call_id),
            edge_function_item_ids=(
                parent_scan.function_item_id,
                root_scan.function_item_id,
            ),
            edge_child_thread_ids=(thread_id, parent_thread_id),
            supplemental_file_indexes=(1, 1, 1, 2, 2),
            supplemental_records=(
                parent_prefix[1].identity,
                parent_scan.call_record,
                parent_scan.start_record,
                root_scan.call_record,
                root_scan.start_record,
            ),
        )
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


def _scan_initial(  # noqa: C901 - one bounded pass keeps record ordering explicit
    descriptor: int,
    size: int,
    *,
    thread_id: str,
    root_session_id: str,
    turn_id: str,
    tool_use_id: str,
    expected_input: dict[str, Any],
) -> tuple[
    tuple[_SessionRecord, ...],
    _RecordIdentity,
    _RecordIdentity,
    str,
]:
    session_records: list[_SessionRecord] = []
    task_record: _RecordIdentity | None = None
    call_record: _RecordIdentity | None = None
    function_item_id = ""
    task_count = 0
    same_call_count = 0
    first = True
    metadata_closed = False
    for offset, raw in _snapshot_lines(descriptor, size):
        record = _strict_json(raw)
        outer_type, payload = _payload(record)
        if first:
            first = False
            if outer_type != "session_meta":
                raise _InvalidTranscript("session metadata is not the first record")
        if outer_type == "session_meta":
            if metadata_closed or len(session_records) >= 2:
                raise _InvalidTranscript("session metadata ordering is unsupported")
            if not isinstance(record, dict):
                raise _InvalidTranscript("session metadata envelope is invalid")
            session_records.append(_SessionRecord(_identity(offset, raw), record, payload))
        else:
            metadata_closed = True
        if outer_type == "event_msg" and payload.get("turn_id") == turn_id:
            if payload.get("type") == "task_started":
                task_count += 1
                task_record = _identity(offset, raw)
            elif payload.get("type") == "task_complete":
                raise _InvalidTranscript("turn is already complete")
        if outer_type == "response_item" and payload.get("call_id") == tool_use_id:
            if not _target_response_envelope_is_exact(record):
                raise _InvalidTranscript("spawn response envelope does not match")
            if payload.get("type") != "function_call":
                raise _InvalidTranscript("spawn call has an unsupported response item")
            same_call_count += 1
            if (
                payload.get("namespace") != "collaboration"
                or payload.get("name") != "spawn_agent"
                or not _function_call_is_exact(
                    payload,
                    turn_id=turn_id,
                    expected_input=expected_input,
                )
            ):
                raise _InvalidTranscript("spawn call does not match")
            call_record = _identity(offset, raw)
            function_item_id = str(payload["id"])
    if task_count != 1 or same_call_count != 1:
        raise _InvalidTranscript("transcript correlation is ambiguous")
    if task_record is None or call_record is None:
        raise _InvalidTranscript("transcript correlation is incomplete")
    if not _function_item_is_unique(descriptor, size, item_id=function_item_id):
        raise _InvalidTranscript("spawn response item identity is ambiguous")
    if not session_records[-1].identity.offset < task_record.offset < call_record.offset:
        raise _InvalidTranscript("transcript correlation order is invalid")
    return tuple(session_records), task_record, call_record, function_item_id


def _seal_payload(attestation: CodexPlaintextSpawnAttestation) -> bytes:
    values = {
        field.name: getattr(attestation, field.name)
        for field in fields(attestation)
        if field.name != "seal"
    }
    return json.dumps(values, sort_keys=True, separators=(",", ":")).encode()


def _sealed(attestation: CodexPlaintextSpawnAttestation) -> str:
    return hmac.new(_SEAL_KEY, _seal_payload(attestation), hashlib.sha256).hexdigest()


def attest_codex_plaintext_spawn(
    transcript_path: object,
    *,
    session_id: str,
    turn_id: str,
    tool_use_id: str,
    tool_input: object,
    environ: Mapping[str, str] | None = None,
) -> CodexPlaintextSpawnAttestation | None:
    """Return a sealed attestation for one exact marked 0.147 spawn, or ``None``."""

    descriptor = -1
    try:
        if (
            not _codex_uuid(turn_id, versions=_TURN_UUID_VERSIONS)
            or _CALL_ID.fullmatch(tool_use_id) is None
        ):
            raise _InvalidTranscript("turn or tool identity is invalid")
        expected_input, arguments_digest = _canonical_tool_input(tool_input)
        path, sessions_root, thread_id = _canonical_rollout_path(
            transcript_path,
            root_session_id=session_id,
            environ=environ,
        )
        descriptor, opened = _open_rollout(path, sessions_root)
        snapshot_size = int(opened.st_size)
        session_records, task, call, function_item_id = _scan_initial(
            descriptor,
            snapshot_size,
            thread_id=thread_id,
            root_session_id=session_id,
            turn_id=turn_id,
            tool_use_id=tool_use_id,
            expected_input=expected_input,
        )
        if len(session_records) == 1 and thread_id != session_id:
            cross_file = _resolve_cross_file_ancestry(
                session_records[0],
                current_path=path,
                sessions_root=sessions_root,
                thread_id=thread_id,
                root_session_id=session_id,
            )
            ancestry = cross_file.identities
            ancestry_thread_ids = cross_file.thread_ids
            ancestry_file_indexes = cross_file.file_indexes
            external_files = cross_file.external_files
            external_edge_call_ids = cross_file.edge_call_ids
            external_edge_function_item_ids = cross_file.edge_function_item_ids
            external_edge_child_thread_ids = cross_file.edge_child_thread_ids
            external_record_file_indexes = cross_file.supplemental_file_indexes
            external_records = cross_file.supplemental_records
        else:
            ancestry, ancestry_thread_ids = _validate_session_ancestry(
                list(session_records),
                thread_id=thread_id,
                root_session_id=session_id,
            )
            ancestry_file_indexes = (0,) * len(ancestry)
            external_files = ()
            external_edge_call_ids = ()
            external_edge_function_item_ids = ()
            external_edge_child_thread_ids = ()
            external_record_file_indexes = ()
            external_records = ()
        if not _snapshot_is_still_exact(
            descriptor,
            path=path,
            sessions_root=sessions_root,
            opened=opened,
            snapshot_size=snapshot_size,
        ):
            raise _InvalidTranscript("transcript changed during attestation")
        unsigned = CodexPlaintextSpawnAttestation(
            schema=_SCHEMA,
            transcript_path=str(path),
            sessions_root=str(sessions_root),
            thread_id=thread_id,
            root_session_id=session_id,
            ancestry_thread_ids=ancestry_thread_ids,
            ancestry_file_indexes=ancestry_file_indexes,
            ancestry_offsets=tuple(record.offset for record in ancestry),
            ancestry_lengths=tuple(record.length for record in ancestry),
            ancestry_sha256=tuple(record.digest for record in ancestry),
            turn_id=turn_id,
            tool_use_id=tool_use_id,
            function_item_id=function_item_id,
            cli_version=_SUPPORTED_CLI_VERSION,
            arguments_sha256=arguments_digest,
            file_device=int(opened.st_dev),
            file_inode=int(opened.st_ino),
            snapshot_size=snapshot_size,
            external_file_paths=tuple(str(item.path) for item in external_files),
            external_file_thread_ids=tuple(item.thread_id for item in external_files),
            external_file_utc_offset_minutes=tuple(
                item.utc_offset_minutes for item in external_files
            ),
            external_file_devices=tuple(item.device for item in external_files),
            external_file_inodes=tuple(item.inode for item in external_files),
            external_file_snapshot_sizes=tuple(item.snapshot_size for item in external_files),
            external_file_snapshot_sha256=tuple(item.snapshot_sha256 for item in external_files),
            external_edge_call_ids=external_edge_call_ids,
            external_edge_function_item_ids=external_edge_function_item_ids,
            external_edge_child_thread_ids=external_edge_child_thread_ids,
            external_record_file_indexes=external_record_file_indexes,
            external_record_offsets=tuple(record.offset for record in external_records),
            external_record_lengths=tuple(record.length for record in external_records),
            external_record_sha256=tuple(record.digest for record in external_records),
            task_offset=task.offset,
            task_length=task.length,
            task_sha256=task.digest,
            call_offset=call.offset,
            call_length=call.length,
            call_sha256=call.digest,
            seal="",
        )
        signed = CodexPlaintextSpawnAttestation(
            **{
                field.name: getattr(unsigned, field.name)
                for field in fields(unsigned)
                if field.name != "seal"
            },
            seal=_sealed(unsigned),
        )
        if not codex_plaintext_spawn_attestation_is_current(signed, tool_input=expected_input):
            raise _InvalidTranscript("attestation changed before return")
        return signed
    except (KeyError, OSError, OverflowError, TypeError, ValueError):
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_exact_at(descriptor: int, offset: int, length: int) -> bytes:
    os.lseek(descriptor, offset, os.SEEK_SET)
    remaining = length
    parts: list[bytes] = []
    while remaining:
        chunk = os.read(descriptor, min(_READ_CHUNK, remaining))
        if not chunk:
            raise _InvalidTranscript("bound transcript record was truncated")
        parts.append(chunk)
        remaining -= len(chunk)
    return b"".join(parts)


def _suffix_is_current(
    descriptor: int,
    *,
    start: int,
    size: int,
    turn_id: str,
    tool_use_id: str,
    function_item_id: str,
) -> bool:
    for _offset, raw in _snapshot_lines(descriptor, size, start=start):
        outer_type, payload = _payload(_strict_json(raw))
        if outer_type == "session_meta":
            return False
        if (
            outer_type == "event_msg"
            and payload.get("turn_id") == turn_id
            and payload.get("type") in {"task_started", "task_complete"}
        ):
            return False
        if outer_type == "response_item" and (
            payload.get("call_id") == tool_use_id or payload.get("id") == function_item_id
        ):
            return False
    return True


def _attestation_array_shapes_are_valid(
    attestation: CodexPlaintextSpawnAttestation,
) -> bool:
    ancestry_count = len(attestation.ancestry_thread_ids)
    external_count = len(attestation.external_file_paths)
    edge_count = len(attestation.external_edge_call_ids)
    supplemental_count = len(attestation.external_record_file_indexes)
    if (
        ancestry_count not in {1, 2, 3}
        or len(attestation.ancestry_file_indexes) != ancestry_count
        or len(attestation.ancestry_offsets) != ancestry_count
        or len(attestation.ancestry_lengths) != ancestry_count
        or len(attestation.ancestry_sha256) != ancestry_count
        or len(attestation.external_file_thread_ids) != external_count
        or len(attestation.external_file_utc_offset_minutes) != external_count
        or len(attestation.external_file_devices) != external_count
        or len(attestation.external_file_inodes) != external_count
        or len(attestation.external_file_snapshot_sizes) != external_count
        or len(attestation.external_file_snapshot_sha256) != external_count
        or len(attestation.external_edge_function_item_ids) != edge_count
        or len(attestation.external_edge_child_thread_ids) != edge_count
        or len(attestation.external_record_offsets) != supplemental_count
        or len(attestation.external_record_lengths) != supplemental_count
        or len(attestation.external_record_sha256) != supplemental_count
        or external_count not in {0, 1, 2}
        or len(set(attestation.external_edge_call_ids)) != edge_count
        or len(set(attestation.external_edge_function_item_ids)) != edge_count
        or len(set(attestation.external_edge_child_thread_ids)) != edge_count
    ):
        return False
    if external_count == 0:
        return bool(
            ancestry_count in {1, 2}
            and attestation.ancestry_file_indexes == (0,) * ancestry_count
            and supplemental_count == 0
            and edge_count == 0
        )
    if any(
        isinstance(value, bool)
        or not isinstance(value, int)
        or not _MIN_UTC_OFFSET_MINUTES <= value <= _MAX_UTC_OFFSET_MINUTES
        for value in attestation.external_file_utc_offset_minutes
    ):
        return False
    if external_count == 1:
        return bool(
            ancestry_count == 2
            and attestation.ancestry_file_indexes == (0, 1)
            and supplemental_count == 2
            and attestation.external_record_file_indexes == (1, 1)
            and edge_count == 1
        )
    return bool(
        ancestry_count == 3
        and attestation.ancestry_file_indexes == (0, 1, 2)
        and supplemental_count == 5
        and attestation.external_record_file_indexes == (1, 1, 1, 2, 2)
        and edge_count == 2
    )


def _bound_record_digest_is_current(
    descriptor: int,
    *,
    offset: object,
    length: object,
    expected: object,
    snapshot_size: int,
) -> bool:
    if (
        isinstance(offset, bool)
        or not isinstance(offset, int)
        or offset < 0
        or isinstance(length, bool)
        or not isinstance(length, int)
        or length <= 0
        or length > _MAX_LINE_BYTES
        or offset + length > snapshot_size
        or not isinstance(expected, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected) is None
    ):
        return False
    return hmac.compare_digest(
        hashlib.sha256(_read_exact_at(descriptor, offset, length)).hexdigest(),
        expected,
    )


def _external_suffix_is_current(
    descriptor: int,
    *,
    start: int,
    size: int,
    call_ids: tuple[str, ...],
    function_item_ids: tuple[str, ...],
    child_thread_ids: tuple[str, ...],
) -> bool:
    for _offset, raw in _snapshot_lines(descriptor, size, start=start):
        outer_type, payload = _payload(_strict_json(raw))
        if outer_type == "session_meta":
            return False
        item = payload.get("item")
        if (
            payload.get("call_id") in call_ids
            or payload.get("id") in (*call_ids, *function_item_ids)
            or (
                isinstance(item, dict)
                and (
                    item.get("id") in (*call_ids, *function_item_ids)
                    or (
                        item.get("agent_thread_id") in child_thread_ids
                        and item.get("kind") == "started"
                    )
                )
            )
        ):
            return False
    return True


def codex_plaintext_spawn_attestation_is_current(  # noqa: C901
    attestation: object,
    *,
    tool_input: object,
) -> bool:
    """Revalidate the exact bound records and reject output, completion, or replay."""

    descriptors: list[int] = []
    try:
        if not isinstance(attestation, CodexPlaintextSpawnAttestation):
            return False
        if attestation.schema != _SCHEMA or not hmac.compare_digest(
            attestation.seal,
            _sealed(attestation),
        ):
            return False
        _frozen, digest = _canonical_tool_input(tool_input)
        if digest != attestation.arguments_sha256:
            return False
        path = Path(attestation.transcript_path)
        sessions_root = Path(attestation.sessions_root)
        if not _attestation_array_shapes_are_valid(attestation):
            return False
        parsed_thread_id, _clock = _canonical_rollout_details(path, sessions_root)
        if parsed_thread_id != attestation.thread_id:
            return False
        descriptor, opened = _open_rollout(path, sessions_root)
        descriptors.append(descriptor)
        if (
            int(opened.st_dev) != attestation.file_device
            or int(opened.st_ino) != attestation.file_inode
            or int(opened.st_size) < attestation.snapshot_size
        ):
            return False
        opened_metadata = [opened]
        snapshot_sizes = [attestation.snapshot_size]
        paths = [path]
        external_count = len(attestation.external_file_paths)
        if external_count:
            _derive_rollout_offset_minutes(path, sessions_root, attestation.thread_id)
            for index in range(external_count):
                resolved_path, resolved_offset = _find_unique_rollout_for_thread(
                    sessions_root,
                    thread_id=attestation.external_file_thread_ids[index],
                )
                if (
                    Path(attestation.external_file_paths[index]) != resolved_path
                    or attestation.external_file_utc_offset_minutes[index] != resolved_offset
                ):
                    return False
        for index in range(external_count):
            external_path = Path(attestation.external_file_paths[index])
            external_thread_id = attestation.external_file_thread_ids[index]
            parsed_external_id, _external_clock = _canonical_rollout_details(
                external_path,
                sessions_root,
            )
            if parsed_external_id != external_thread_id:
                return False
            external_descriptor, external_opened = _open_rollout(
                external_path,
                sessions_root,
            )
            descriptors.append(external_descriptor)
            if (
                int(external_opened.st_dev) != attestation.external_file_devices[index]
                or int(external_opened.st_ino) != attestation.external_file_inodes[index]
                or int(external_opened.st_size) < attestation.external_file_snapshot_sizes[index]
                or re.fullmatch(
                    r"[0-9a-f]{64}",
                    attestation.external_file_snapshot_sha256[index],
                )
                is None
            ):
                return False
            opened_metadata.append(external_opened)
            snapshot_sizes.append(attestation.external_file_snapshot_sizes[index])
            paths.append(external_path)
        if (
            sum(int(metadata.st_size) for metadata in opened_metadata[1:])
            > _MAX_EXTERNAL_ANCESTRY_BYTES
        ):
            return False
        for index in range(external_count):
            if not hmac.compare_digest(
                _snapshot_sha256(
                    descriptors[index + 1],
                    attestation.external_file_snapshot_sizes[index],
                ),
                attestation.external_file_snapshot_sha256[index],
            ):
                return False

        ancestry_count = len(attestation.ancestry_thread_ids)
        if (
            attestation.ancestry_thread_ids[0] != attestation.thread_id
            or (
                external_count
                and attestation.ancestry_thread_ids[-1] != attestation.root_session_id
            )
            or len(set(attestation.ancestry_thread_ids)) != ancestry_count
            or any(
                not _codex_uuid(value, versions=_THREAD_UUID_VERSIONS)
                for value in attestation.ancestry_thread_ids
            )
            or (
                external_count == 0
                and ancestry_count == 1
                and attestation.ancestry_thread_ids[0] != attestation.root_session_id
            )
        ):
            return False
        if external_count:
            times = tuple(UUID(value).int for value in attestation.ancestry_thread_ids)
            if (external_count == 1 and times[1] > times[0]) or (
                external_count == 2 and not times[2] <= times[1] < times[0]
            ):
                return False
            if attestation.external_file_thread_ids != attestation.ancestry_thread_ids[1:]:
                return False
        for file_index, offset, length, expected in zip(
            attestation.ancestry_file_indexes,
            attestation.ancestry_offsets,
            attestation.ancestry_lengths,
            attestation.ancestry_sha256,
            strict=True,
        ):
            if not _bound_record_digest_is_current(
                descriptors[file_index],
                offset=offset,
                length=length,
                expected=expected,
                snapshot_size=snapshot_sizes[file_index],
            ):
                return False
        for file_index, offset, length, expected in zip(
            attestation.external_record_file_indexes,
            attestation.external_record_offsets,
            attestation.external_record_lengths,
            attestation.external_record_sha256,
            strict=True,
        ):
            if not _bound_record_digest_is_current(
                descriptors[file_index],
                offset=offset,
                length=length,
                expected=expected,
                snapshot_size=snapshot_sizes[file_index],
            ):
                return False
        for offset, length, expected in (
            (attestation.task_offset, attestation.task_length, attestation.task_sha256),
            (attestation.call_offset, attestation.call_length, attestation.call_sha256),
        ):
            if not _bound_record_digest_is_current(
                descriptor,
                offset=offset,
                length=length,
                expected=expected,
                snapshot_size=attestation.snapshot_size,
            ):
                return False
        edge_file_indexes = () if external_count == 0 else (1,) if external_count == 1 else (1, 2)
        for call_id, function_item_id, child_thread_id in zip(
            attestation.external_edge_call_ids,
            attestation.external_edge_function_item_ids,
            attestation.external_edge_child_thread_ids,
            strict=True,
        ):
            if (
                _CALL_ID.fullmatch(call_id) is None
                or _FUNCTION_ITEM_ID.fullmatch(function_item_id) is None
                or not _codex_uuid(child_thread_id, versions=_THREAD_UUID_VERSIONS)
            ):
                return False
        for file_index in edge_file_indexes:
            if not _external_suffix_is_current(
                descriptors[file_index],
                start=snapshot_sizes[file_index],
                size=int(opened_metadata[file_index].st_size),
                call_ids=attestation.external_edge_call_ids,
                function_item_ids=attestation.external_edge_function_item_ids,
                child_thread_ids=attestation.external_edge_child_thread_ids,
            ):
                return False
        for file_index, child_thread_id in zip(
            edge_file_indexes,
            attestation.external_edge_child_thread_ids,
            strict=True,
        ):
            if child_thread_id != attestation.ancestry_thread_ids[file_index - 1]:
                return False
        current_size = int(opened.st_size)
        if not _suffix_is_current(
            descriptor,
            start=attestation.snapshot_size,
            size=current_size,
            turn_id=attestation.turn_id,
            tool_use_id=attestation.tool_use_id,
            function_item_id=attestation.function_item_id,
        ):
            return False
        for index, opened_value in enumerate(opened_metadata):
            after = os.fstat(descriptors[index])
            lexical = os.lstat(paths[index])
            if (
                int(after.st_size) != int(opened_value.st_size)
                or not same_file_identity(opened_value, after)
                or not same_file_identity(after, lexical)
                or not _path_is_trusted(paths[index], sessions_root)
            ):
                return False
        for index in range(external_count):
            resolved_path, resolved_offset = _find_unique_rollout_for_thread(
                sessions_root,
                thread_id=attestation.external_file_thread_ids[index],
            )
            if (
                resolved_path != Path(attestation.external_file_paths[index])
                or resolved_offset != attestation.external_file_utc_offset_minutes[index]
            ):
                return False
        return True
    except (KeyError, OSError, OverflowError, TypeError, ValueError):
        return False
    finally:
        for descriptor in descriptors:
            os.close(descriptor)


__all__ = [
    "CodexPlaintextSpawnAttestation",
    "attest_codex_plaintext_spawn",
    "codex_plaintext_spawn_attestation_is_current",
]
