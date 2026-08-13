"""Authenticate one Codex plaintext collaboration spawn from its rollout.

Codex's hook envelope does not carry the host's plaintext-delivery marker.  A
bounded, version-pinned scan of the canonical parent rollout supplies that
missing provenance without treating model-authored tool input as authority.
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
from datetime import date
from pathlib import Path
from typing import Any, Final

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

_SCHEMA: Final = "agency.codex-plaintext-spawn-attestation.v1"
_SUPPORTED_CLI_VERSION: Final = "0.147.0"
_MAX_PATH_BYTES: Final = 4 * 1024
_MAX_TRANSCRIPT_BYTES: Final = 64 * 1024 * 1024
_MAX_LINE_BYTES: Final = 4 * 1024 * 1024
_MAX_LINES: Final = 100_000
_MAX_ARGUMENT_BYTES: Final = 1024 * 1024
_MAX_JSON_DEPTH: Final = 64
_MAX_JSON_NODES: Final = 200_000
_READ_CHUNK: Final = 64 * 1024
_SPAWN_KEYS: Final = frozenset({"task_name", "message", "fork_turns", "model", "reasoning_effort"})
_REQUIRED_SPAWN_KEYS: Final = frozenset({"task_name", "message"})
_REASONING_EFFORTS: Final = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
_TASK_NAME = re.compile(r"^[a-z0-9_]{1,128}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,511}$")
_CODEX_THREAD_ID_PATTERN: Final = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CODEX_THREAD_ID = re.compile(rf"^{_CODEX_THREAD_ID_PATTERN}$")
_MAX_ANCESTRY_DEPTH: Final = 2
_MAX_METADATA_TEXT_BYTES: Final = 1024
_TUI_LINEAGE: Final = ("cli", "paginated", "codex-tui")
_EXEC_LINEAGE: Final = ("exec", "legacy", "codex_exec")
_SUPPORTED_LINEAGES: Final = frozenset({_TUI_LINEAGE, _EXEC_LINEAGE})
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
    ancestry_offsets: tuple[int, ...]
    ancestry_lengths: tuple[int, ...]
    ancestry_sha256: tuple[str, ...]
    turn_id: str
    tool_use_id: str
    cli_version: str
    arguments_sha256: str
    file_device: int
    file_inode: int
    snapshot_size: int
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
    if _CODEX_THREAD_ID.fullmatch(root_session_id) is None:
        raise _InvalidTranscript("session identity is invalid")
    candidate = Path(raw)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
        raise _InvalidTranscript("transcript path is not canonical")
    canonical = absolute_path(candidate)
    if candidate != canonical:
        raise _InvalidTranscript("transcript path is not canonical")
    sessions_root = _active_sessions_root(environ)
    try:
        relative = canonical.relative_to(sessions_root)
    except ValueError as exc:
        raise _InvalidTranscript("transcript path is outside the active sessions root") from exc
    if len(relative.parts) != 4:
        raise _InvalidTranscript("transcript path shape is unsupported")
    year, month, day_value, filename = relative.parts
    try:
        date(int(year), int(month), int(day_value))
    except (TypeError, ValueError) as exc:
        raise _InvalidTranscript("transcript date is invalid") from exc
    pattern = re.compile(
        rf"^rollout-{re.escape(year)}-{re.escape(month)}-{re.escape(day_value)}"
        rf"T\d{{2}}-\d{{2}}-\d{{2}}-(?P<thread_id>{_CODEX_THREAD_ID_PATTERN})\.jsonl$"
    )
    match = pattern.fullmatch(filename)
    if match is None:
        raise _InvalidTranscript("transcript filename is invalid")
    return canonical, sessions_root, match.group("thread_id")


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
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    if not isinstance(metadata, dict) or metadata.get("turn_id") != turn_id:
        return False
    if "encrypted_function_args" not in payload or payload["encrypted_function_args"] != []:
        return False
    arguments = payload.get("arguments")
    if not isinstance(arguments, str) or len(arguments.encode("utf-8")) > _MAX_ARGUMENT_BYTES:
        return False
    parsed = _strict_json(arguments.encode("utf-8"))
    if not isinstance(parsed, dict):
        return False
    canonical, _digest_value = _canonical_tool_input(parsed)
    return canonical == expected_input


def _bounded_metadata_text(value: object, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    return bool(
        isinstance(value, str) and value and len(value.encode("utf-8")) <= _MAX_METADATA_TEXT_BYTES
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
) -> int | None:
    if (
        payload.get("id") != thread_id
        or payload.get("session_id") != root_session_id
        or payload.get("cli_version") != _SUPPORTED_CLI_VERSION
        or payload.get("forked_from_id") != parent_thread_id
        or payload.get("parent_thread_id") != parent_thread_id
        or payload.get("thread_source") != "subagent"
        or payload.get("history_mode") != lineage[1]
        or payload.get("originator") != lineage[2]
        or payload.get("multi_agent_version") != "v2"
    ):
        return None
    history_start = payload.get("subagent_history_start_ordinal")
    if lineage == _TUI_LINEAGE and (
        isinstance(history_start, bool) or not isinstance(history_start, int) or history_start < 0
    ):
        return None
    if lineage == _EXEC_LINEAGE and history_start is not None:
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
        or not _bounded_metadata_text(spawn.get("agent_path"))
        or not _bounded_metadata_text(spawn.get("agent_nickname"))
        or not _bounded_metadata_text(spawn.get("agent_role"), nullable=True)
        or payload.get("agent_path") != spawn.get("agent_path")
        or payload.get("agent_nickname") != spawn.get("agent_nickname")
    ):
        return None
    return depth


def _validate_session_ancestry(
    sessions: list[tuple[_RecordIdentity, dict[str, Any]]],
    *,
    thread_id: str,
    root_session_id: str,
) -> tuple[tuple[_RecordIdentity, ...], tuple[str, ...]]:
    # Codex 0.147 serializes one root metadata record, or exactly two leading
    # records for a fork.  A depth-two rollout still contains only its current
    # and immediate-parent records; the latter authenticates its own root link.
    # Deeper forks are rejected until a canonical host shape is observed.
    if len(sessions) not in {1, 2}:
        raise _InvalidTranscript("session ancestry shape is unsupported")
    thread_ids = tuple(str(payload.get("id") or "") for _identity_value, payload in sessions)
    if (
        thread_ids[0] != thread_id
        or len(set(thread_ids)) != len(thread_ids)
        or any(_CODEX_THREAD_ID.fullmatch(value) is None for value in thread_ids)
    ):
        raise _InvalidTranscript("session ancestry identities do not match")
    if len(sessions) == 1:
        if (
            thread_id != root_session_id
            or _root_session_lineage(sessions[0][1], root_session_id=root_session_id) is None
        ):
            raise _InvalidTranscript("root session metadata does not match")
        return (sessions[0][0],), thread_ids

    if thread_id == root_session_id:
        raise _InvalidTranscript("forked session identity does not match")
    child_mode = (
        str(sessions[0][1].get("history_mode") or ""),
        str(sessions[0][1].get("originator") or ""),
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
        sessions[0][1],
        thread_id=thread_id,
        root_session_id=root_session_id,
        parent_thread_id=thread_ids[1],
        lineage=lineage,
    )
    if current_depth == 1:
        if (
            thread_ids[1] != root_session_id
            or _root_session_lineage(sessions[1][1], root_session_id=root_session_id) != lineage
        ):
            raise _InvalidTranscript("root parent metadata does not match")
    elif current_depth == 2:
        if (
            lineage != _TUI_LINEAGE
            or thread_ids[1] == root_session_id
            or _subagent_session_depth(
                sessions[1][1],
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
    return tuple(identity for identity, _payload_value in sessions), thread_ids


def _scan_initial(  # noqa: C901 - one bounded pass keeps record ordering explicit
    descriptor: int,
    size: int,
    *,
    thread_id: str,
    root_session_id: str,
    turn_id: str,
    tool_use_id: str,
    expected_input: dict[str, Any],
) -> tuple[tuple[_RecordIdentity, ...], tuple[str, ...], _RecordIdentity, _RecordIdentity]:
    session_records: list[tuple[_RecordIdentity, dict[str, Any]]] = []
    task_record: _RecordIdentity | None = None
    call_record: _RecordIdentity | None = None
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
            session_records.append((_identity(offset, raw), payload))
        else:
            metadata_closed = True
        if outer_type == "event_msg" and payload.get("turn_id") == turn_id:
            if payload.get("type") == "task_started":
                task_count += 1
                task_record = _identity(offset, raw)
            elif payload.get("type") == "task_complete":
                raise _InvalidTranscript("turn is already complete")
        if outer_type == "response_item" and payload.get("call_id") == tool_use_id:
            if payload.get("type") == "function_call_output":
                raise _InvalidTranscript("spawn call already has an output")
            if payload.get("type") == "function_call":
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
    if task_count != 1 or same_call_count != 1:
        raise _InvalidTranscript("transcript correlation is ambiguous")
    if task_record is None or call_record is None:
        raise _InvalidTranscript("transcript correlation is incomplete")
    ancestry_records, ancestry_thread_ids = _validate_session_ancestry(
        session_records,
        thread_id=thread_id,
        root_session_id=root_session_id,
    )
    if not ancestry_records[-1].offset < task_record.offset < call_record.offset:
        raise _InvalidTranscript("transcript correlation order is invalid")
    return ancestry_records, ancestry_thread_ids, task_record, call_record


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
        if _SAFE_ID.fullmatch(turn_id) is None or _SAFE_ID.fullmatch(tool_use_id) is None:
            raise _InvalidTranscript("turn or tool identity is invalid")
        expected_input, arguments_digest = _canonical_tool_input(tool_input)
        path, sessions_root, thread_id = _canonical_rollout_path(
            transcript_path,
            root_session_id=session_id,
            environ=environ,
        )
        descriptor, opened = _open_rollout(path, sessions_root)
        snapshot_size = int(opened.st_size)
        ancestry, ancestry_thread_ids, task, call = _scan_initial(
            descriptor,
            snapshot_size,
            thread_id=thread_id,
            root_session_id=session_id,
            turn_id=turn_id,
            tool_use_id=tool_use_id,
            expected_input=expected_input,
        )
        after = os.fstat(descriptor)
        current = os.lstat(path)
        if (
            int(after.st_size) != snapshot_size
            or not same_file_identity(opened, after)
            or not same_file_identity(after, current)
            or not _path_is_trusted(path, sessions_root)
        ):
            raise _InvalidTranscript("transcript changed during attestation")
        unsigned = CodexPlaintextSpawnAttestation(
            schema=_SCHEMA,
            transcript_path=str(path),
            sessions_root=str(sessions_root),
            thread_id=thread_id,
            root_session_id=session_id,
            ancestry_thread_ids=ancestry_thread_ids,
            ancestry_offsets=tuple(record.offset for record in ancestry),
            ancestry_lengths=tuple(record.length for record in ancestry),
            ancestry_sha256=tuple(record.digest for record in ancestry),
            turn_id=turn_id,
            tool_use_id=tool_use_id,
            cli_version=_SUPPORTED_CLI_VERSION,
            arguments_sha256=arguments_digest,
            file_device=int(opened.st_dev),
            file_inode=int(opened.st_ino),
            snapshot_size=snapshot_size,
            task_offset=task.offset,
            task_length=task.length,
            task_sha256=task.digest,
            call_offset=call.offset,
            call_length=call.length,
            call_sha256=call.digest,
            seal="",
        )
        return CodexPlaintextSpawnAttestation(
            **{
                field.name: getattr(unsigned, field.name)
                for field in fields(unsigned)
                if field.name != "seal"
            },
            seal=_sealed(unsigned),
        )
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
        if (
            outer_type == "response_item"
            and payload.get("call_id") == tool_use_id
            and payload.get("type") in {"function_call", "function_call_output"}
        ):
            return False
    return True


def codex_plaintext_spawn_attestation_is_current(
    attestation: object,
    *,
    tool_input: object,
) -> bool:
    """Revalidate the exact bound records and reject output, completion, or replay."""

    descriptor = -1
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
        if not path.is_absolute() or not sessions_root.is_absolute():
            return False
        descriptor, opened = _open_rollout(path, sessions_root)
        if (
            int(opened.st_dev) != attestation.file_device
            or int(opened.st_ino) != attestation.file_inode
            or int(opened.st_size) < attestation.snapshot_size
        ):
            return False
        ancestry_count = len(attestation.ancestry_thread_ids)
        if (
            ancestry_count not in {1, 2}
            or len(attestation.ancestry_offsets) != ancestry_count
            or len(attestation.ancestry_lengths) != ancestry_count
            or len(attestation.ancestry_sha256) != ancestry_count
            or attestation.ancestry_thread_ids[0] != attestation.thread_id
            or (
                ancestry_count == 1
                and attestation.ancestry_thread_ids[0] != attestation.root_session_id
            )
        ):
            return False
        bound_records = [
            *zip(
                attestation.ancestry_offsets,
                attestation.ancestry_lengths,
                attestation.ancestry_sha256,
                strict=True,
            ),
            (attestation.task_offset, attestation.task_length, attestation.task_sha256),
            (attestation.call_offset, attestation.call_length, attestation.call_sha256),
        ]
        for offset, length, expected in bound_records:
            if hashlib.sha256(_read_exact_at(descriptor, offset, length)).hexdigest() != expected:
                return False
        current_size = int(opened.st_size)
        if not _suffix_is_current(
            descriptor,
            start=attestation.snapshot_size,
            size=current_size,
            turn_id=attestation.turn_id,
            tool_use_id=attestation.tool_use_id,
        ):
            return False
        after = os.fstat(descriptor)
        lexical = os.lstat(path)
        return bool(
            int(after.st_size) == current_size
            and same_file_identity(opened, after)
            and same_file_identity(after, lexical)
            and _path_is_trusted(path, sessions_root)
        )
    except (KeyError, OSError, OverflowError, TypeError, ValueError):
        return False
    finally:
        if descriptor >= 0:
            os.close(descriptor)


__all__ = [
    "CodexPlaintextSpawnAttestation",
    "attest_codex_plaintext_spawn",
    "codex_plaintext_spawn_attestation_is_current",
]
