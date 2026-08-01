"""Credential-isolated, bounded subprocess backends for live host canaries."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import FileSizeLimitError
from agency_runtime.core.private_paths import private_temporary_directory

_CODEX_ROLLOUT_MAX_BYTES = 1024 * 1024
_CODEX_ROLLOUT_MAX_LINES = 5_000
_CODEX_ROLLOUT_CLOCK_SKEW_SECONDS = 2.0
_CODEX_HOOK_TRUST_PREFLIGHT_TIMEOUT_SECONDS = 10.0
_CODEX_THREAD_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
_CODEX_ROLLOUT_RESPONSE_TYPES = frozenset(
    {"agent_message", "function_call", "function_call_output", "message", "reasoning"}
)
CODEX_STDOUT_HOST_NOTICE_TYPES = frozenset(
    {
        "hook_trust_bypass",
        "skill_catalog_descriptions_shortened",
    }
)
CODEX_STDOUT_HOST_NOTICE_COUNT_MAX = _CODEX_ROLLOUT_MAX_LINES
_CODEX_STDOUT_HOST_NOTICE_BY_MESSAGE = {
    "`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run "
    "without review for this invocation.": "hook_trust_bypass",
    "Skill descriptions were shortened to fit the 2% skills context budget. Codex can still "
    "see every skill, but some descriptions are shorter. Disable unused skills or plugins "
    "to leave more room for the rest.": "skill_catalog_descriptions_shortened",
    "Skill descriptions were shortened to fit the skills context budget. Codex can still "
    "see every skill, but some descriptions are shorter. Disable unused skills or plugins "
    "to leave more room for the rest.": "skill_catalog_descriptions_shortened",
}
_CODEX_ROLLOUT_CONTRACTS = frozenset({"canary", "product"})
_CODEX_PRODUCT_COLLABORATION_SCHEMA = "agency.codex-product-collaboration.v1"
_CODEX_PRODUCT_MAX_SPAWNS = 16
_CODEX_PRODUCT_MAX_WAITS = 64
# Current Codex wait_agent schema ceiling; the activation canary separately requires 60 seconds.
_CODEX_PRODUCT_MAX_WAIT_TIMEOUT_MS = 3_600_000
CODEX_COLLABORATION_DIAGNOSTIC_SCHEMA = "agency.codex-collaboration-diagnostic.v1"
CODEX_COLLABORATION_DIAGNOSTIC_REASONS = frozenset(
    {
        "parent_rollout_unavailable",
        "parent_spawn_missing",
        "parent_spawn_ambiguous",
        "parent_followup_missing",
        "parent_followup_ambiguous",
        "parent_wait_missing",
        "parent_wait_ambiguous",
        "native_tool_output_missing",
        "native_child_start_missing",
        "native_child_interaction_missing",
        "native_collaboration_topology_invalid",
        "product_parent_thread_missing",
        "product_rollout_invalid",
        "product_call_identity_invalid",
        "product_tool_output_duplicate",
        "product_tool_output_invalid",
        "product_spawn_arguments_invalid",
        "product_spawn_task_invalid",
        "product_spawn_output_invalid",
        "product_child_start_invalid",
        "product_child_path_invalid",
        "product_child_completion_missing",
        "product_child_failed",
        "product_child_delivery_invalid",
        "product_child_work_unit_mismatch",
        "product_wait_arguments_invalid",
        "product_wait_output_invalid",
        "product_final_wait_missing",
        "product_spawn_cardinality_invalid",
        "product_wait_cardinality_invalid",
        "product_followup_cardinality_invalid",
        "product_call_output_mismatch",
        "product_child_identity_duplicate",
        "product_child_activity_invalid",
        "product_collaboration_order_invalid",
        "product_followup_output_invalid",
        "product_followup_invalid",
        "product_child_execution_invalid",
        "product_wait_incomplete",
        "product_stdout_projection_invalid",
        "product_stdout_child_mismatch",
    }
)
_CODEX_COLLABORATION_DIAGNOSTIC_COUNT_MAX = _CODEX_ROLLOUT_MAX_LINES
_CODEX_COLLABORATION_FAILURE_REASON_BY_DIAGNOSTIC = {
    "parent_spawn_missing": "codex_parent_spawn_missing",
    "parent_wait_missing": "codex_parent_wait_missing",
    "parent_followup_missing": "codex_parent_followup_missing",
    "native_tool_output_missing": "codex_native_tool_output_missing",
    "native_child_start_missing": "codex_native_child_start_missing",
}

_CODEX_PRODUCT_TOPOLOGY_REASON_BY_MESSAGE = {
    "Codex product stdout omitted its parent thread": "product_parent_thread_missing",
    "invalid Codex product collaboration identity": "product_call_identity_invalid",
    "duplicate Codex product collaboration output": "product_tool_output_duplicate",
    "Codex product spawn arguments exceeded the exact contract": (
        "product_spawn_arguments_invalid"
    ),
    "Codex product spawn task name was invalid": "product_spawn_task_invalid",
    "Codex product spawn output did not match its native task": "product_spawn_output_invalid",
    "Codex product spawn did not identify one native child start": "product_child_start_invalid",
    "Codex product child path did not match its native task": "product_child_path_invalid",
    "Codex product child did not prove one completion": "product_child_completion_missing",
    "Codex product child did not complete successfully": "product_child_failed",
    "Codex product child task did not match its delivered work unit": (
        "product_child_work_unit_mismatch"
    ),
    "Codex product wait arguments exceeded the bounded contract": (
        "product_wait_arguments_invalid"
    ),
    "Codex product wait output was invalid": "product_wait_output_invalid",
    "Codex product parent did not complete a wait after its final spawn": (
        "product_final_wait_missing"
    ),
    "Codex product spawn cardinality was invalid": "product_spawn_cardinality_invalid",
    "Codex product wait cardinality was invalid": "product_wait_cardinality_invalid",
    "Codex product followup cardinality was invalid": "product_followup_cardinality_invalid",
    "Codex product child activity cardinality was invalid": "product_child_activity_invalid",
    "Codex product collaboration calls were not causally ordered": (
        "product_collaboration_order_invalid"
    ),
    "Codex product followup output was not empty": "product_followup_output_invalid",
    "Codex product followup did not match its activated child": "product_followup_invalid",
    "Codex product child execution did not match its followup": ("product_child_execution_invalid"),
    "Codex product execution did not match its activation delivery": (
        "product_child_execution_invalid"
    ),
    "Codex product collaboration waits did not all complete": "product_wait_incomplete",
    "Codex product collaboration outputs did not match its calls": ("product_call_output_mismatch"),
    "Codex product children were not distinct": "product_child_identity_duplicate",
    "Codex product stdout contradicted its persisted rollout": (
        "product_stdout_projection_invalid"
    ),
    "Codex product stdout identified a different child": "product_stdout_child_mismatch",
}


def _codex_product_topology_reason(exc: BaseException) -> str:
    """Map one private validator exception to an allowlisted content-free invariant."""

    message = str(exc)
    exact = _CODEX_PRODUCT_TOPOLOGY_REASON_BY_MESSAGE.get(message)
    if exact is not None:
        return exact
    prefix_reasons = (
        ("Codex product spawn_agent arguments", "product_spawn_arguments_invalid"),
        ("Codex product wait_agent arguments", "product_wait_arguments_invalid"),
        ("Codex product collaboration output", "product_tool_output_invalid"),
        ("Codex child prompt delivery", "product_child_delivery_invalid"),
        ("Codex child rollout", "product_child_delivery_invalid"),
        ("Codex rollout", "product_rollout_invalid"),
    )
    for prefix, reason in prefix_reasons:
        if message.startswith(prefix):
            return reason
    return "native_collaboration_topology_invalid"


def _facade():
    """Resolve canary dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import canary

    return canary


def copy_bounded_auth(source: Path, destination: Path, *, host: str) -> None:
    """Copy one allowlisted bounded auth artifact into a private temp home."""
    facade = _facade()
    try:
        payload = facade.read_bounded_regular_file(
            source,
            limit=1024 * 1024,
            label=f"{host} auth artifact",
        )
    except FileSizeLimitError:
        raise ValueError(f"{host} auth artifact exceeds the safety limit") from None
    except OSError:
        raise ValueError(f"{host} auth artifact is unavailable or unsafe") from None
    from agency_runtime.core.configuration import (
        restrict_private_directory,
        restrict_private_file,
    )

    os_module = facade.os
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
        mode=0o777 if os_module.name == "nt" else 0o700,
    )
    restrict_private_directory(destination.parent)
    fd = os_module.open(
        destination,
        os_module.O_CREAT
        | os_module.O_EXCL
        | os_module.O_WRONLY
        | getattr(os_module, "O_BINARY", 0),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        restrict_private_file(destination)
        with os_module.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(payload)
            stream.flush()
            os_module.fsync(stream.fileno())
        restrict_private_file(destination)
    except BaseException:
        if fd >= 0:
            os_module.close(fd)
        destination.unlink(missing_ok=True)
        raise


def codex_isolated_plugin_enabled(value: Any) -> bool:
    if isinstance(value, dict):
        identity = str(value.get("pluginId") or value.get("name") or "").casefold()
        if (
            identity
            in {
                "agency-preflight",
                "agency-preflight@agency-runtime",
            }
            and value.get("installed") is True
            and value.get("enabled") is True
        ):
            return True
        return any(codex_isolated_plugin_enabled(child) for child in value.values())
    if isinstance(value, list):
        return any(codex_isolated_plugin_enabled(child) for child in value)
    return False


def isolated_canary_environment(
    source_env: Mapping[str, str],
    runtime_home: Path,
    db_path: Path,
) -> dict[str, str]:
    from agency_runtime.core.cli_transport import safe_cli_environment
    from agency_runtime.core.runtime_control import runtime_control_path

    env = safe_cli_environment(source_env)
    isolated_home = runtime_home / "home"
    isolated_temp = runtime_home / "tmp"
    isolated_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    isolated_temp.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in (
        "APPDATA",
        "HOME",
        "LOCALAPPDATA",
        "USERPROFILE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    ):
        env[name] = str(isolated_home)
    for name in ("TEMP", "TMP", "TMPDIR"):
        env[name] = str(isolated_temp)
    env["AGENCY_DB_PATH"] = str(db_path.resolve())
    env["AGENCY_CANARY_MODE"] = "1"
    env["AGENCY_CANARY_CONTROL_PATH"] = str(runtime_control_path(home_dir=isolated_home))
    return env


def project_isolated_runtime_control(
    runtime_home: Path,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Materialize and verify one explicit master state in the isolated home."""
    from agency_runtime.core.runtime_control import (
        ensure_runtime_control_materialized,
        read_authoritative_runtime_control,
        set_master_enabled,
    )

    isolated_home = runtime_home / "home"
    current = ensure_runtime_control_materialized(
        source="canary",
        home_dir=isolated_home,
    )
    if bool(current["enabled"]) is not enabled:
        current = set_master_enabled(
            enabled,
            expected_generation=int(current["generation"]),
            source="canary",
            home_dir=isolated_home,
        )
    verified, transport = read_authoritative_runtime_control(
        home_dir=isolated_home,
        use_cache=False,
    )
    if transport != "direct" or bool(verified["enabled"]) is not enabled:
        raise RuntimeError("isolated canary runtime control projection failed")
    return verified


def prepare_private_host_home(
    runtime_home: Path,
    *,
    directory_name: str,
    auth_source: Path,
    auth_name: str,
    host: str,
) -> Path:
    from agency_runtime.core.configuration import restrict_private_directory

    restrict_private_directory(runtime_home)
    host_home = runtime_home / directory_name
    host_home.mkdir(mode=0o700)
    restrict_private_directory(host_home)
    _facade()._copy_bounded_auth(auth_source, host_home / auth_name, host=host)
    return host_home


def project_isolated_codex_workspace_trust(
    codex_home: Path,
    *,
    workdir: str,
) -> dict[str, Any]:
    """Trust one real workspace only inside one disposable Codex home."""

    from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file
    from agency_runtime.core.configuration import restrict_private_file
    from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point

    try:
        workspace = Path(workdir).expanduser().resolve(strict=True)
        metadata = os.lstat(workspace)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("isolated Codex workspace is unavailable") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("isolated Codex workspace must be a real directory")
    normalized = str(workspace)
    if os.name == "nt":
        normalized = normalized.casefold()
    config = codex_home / "config.toml"
    if config.exists():
        raise ValueError("isolated Codex config must not preexist workspace trust projection")
    document = f'[projects.{json.dumps(normalized, ensure_ascii=False)}]\ntrust_level = "trusted"\n'
    atomic_write_text(config, document)
    restrict_private_file(config)
    if (
        read_bounded_regular_file(
            config,
            limit=16 * 1024,
            label="isolated Codex config",
        ).decode("utf-8")
        != document
    ):
        raise RuntimeError("isolated Codex workspace trust projection changed during verification")
    return {
        "schema": "agency.codex-isolated-workspace-trust.v1",
        "status": "trusted",
        "scope": "exact-workspace",
        "workspace_hash": "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "persistent_profile_changed": False,
    }


def process_succeeded(result: Any) -> bool:
    return (
        result.returncode == 0
        and not result.timed_out
        and not result.stdout_truncated
        and not result.stderr_truncated
    )


def codex_output(stdout: str) -> str | None:
    events: list[dict[str, Any]] = []
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = _facade()._load_canary_json(line, maximum_bytes=256_000)
            if isinstance(event, dict):
                events.append(event)
    except (TypeError, ValueError):
        return None
    completed = any(event.get("type") == "turn.completed" for event in events)
    messages = [
        str(event["item"]["text"])
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
        and event["item"].get("type") == "agent_message"
        and event["item"].get("text") is not None
    ]
    return messages[-1] if completed and messages else None


def _codex_thread_id(value: object) -> str:
    thread_id = str(value or "").strip()
    if _CODEX_THREAD_ID.fullmatch(thread_id) is None:
        raise ValueError("invalid Codex thread identity")
    return thread_id


def _codex_stdout_thread_id(stdout: str) -> str | None:
    """Return the sole parent thread UUID announced by Codex JSONL."""

    thread_ids: set[str] = set()
    for line in stdout.splitlines():
        if not line.strip():
            continue
        event = _facade()._load_canary_json(line, maximum_bytes=256_000)
        if isinstance(event, dict) and event.get("type") == "thread.started":
            thread_ids.add(_codex_thread_id(event.get("thread_id")))
    if not thread_ids:
        return None
    if len(thread_ids) != 1:
        raise ValueError("Codex announced multiple parent thread identities")
    return next(iter(thread_ids))


def _codex_rollout_events(
    rollout_root: Path,
    thread_id: str,
    *,
    parent_thread_id: str | None,
    expected_agent_path: str | None,
    not_before: float | None,
    not_after: float | None,
) -> list[dict[str, Any]]:
    """Read one exact link-resistant bounded Codex rollout."""

    facade = _facade()
    from agency_runtime.core.filesystem_trust import same_file_identity
    from agency_runtime.core.store.security import (
        assert_storage_parent_chain,
        storage_file_is_trusted,
        storage_parent_is_trusted,
    )

    root = Path(rollout_root)
    assert_storage_parent_chain(root, allow_missing=False)
    if not storage_parent_is_trusted(root, is_windows=facade.os.name == "nt"):
        raise ValueError("Codex rollout root was not private")
    matches = list(root.glob(f"*/*/*/rollout-*-{thread_id}.jsonl")) if root.is_dir() else []
    if len(matches) != 1:
        raise ValueError("Codex rollout identity was missing or ambiguous")
    path = matches[0]
    assert_storage_parent_chain(path.parent, allow_missing=False)
    if not storage_parent_is_trusted(
        path.parent,
        is_windows=facade.os.name == "nt",
    ) or not storage_file_is_trusted(path, is_windows=facade.os.name == "nt"):
        raise ValueError("Codex rollout path was not private")
    metadata = path.lstat()
    if not_before is not None and (
        metadata.st_mtime + _CODEX_ROLLOUT_CLOCK_SKEW_SECONDS < not_before
    ):
        raise ValueError("Codex rollout predates the canary invocation")
    if not_after is not None and (
        metadata.st_mtime - _CODEX_ROLLOUT_CLOCK_SKEW_SECONDS > not_after
    ):
        raise ValueError("Codex rollout postdates the canary invocation")
    try:
        payload = facade.read_bounded_regular_file(
            path,
            limit=_CODEX_ROLLOUT_MAX_BYTES,
            label="Codex canary rollout",
        ).decode("utf-8")
    except (OSError, UnicodeError):
        raise ValueError("Codex rollout was unavailable or unsafe") from None
    current = path.lstat()
    if (
        not same_file_identity(metadata, current)
        or current.st_size != metadata.st_size
        or current.st_mtime_ns != metadata.st_mtime_ns
        or not storage_parent_is_trusted(path.parent, is_windows=facade.os.name == "nt")
    ):
        raise ValueError("Codex rollout changed during evidence collection")
    lines = payload.splitlines()
    if not lines or len(lines) > _CODEX_ROLLOUT_MAX_LINES:
        raise ValueError("Codex rollout exceeded its line ceiling")
    events: list[dict[str, Any]] = []
    for line in lines:
        event = facade._load_canary_json(line, maximum_bytes=256_000)
        if not isinstance(event, dict):
            raise ValueError("Codex rollout contained a non-object event")
        events.append(event)
    first = events[0]
    first_payload = first.get("payload")
    if (
        first.get("type") != "session_meta"
        or not isinstance(first_payload, dict)
        or _codex_thread_id(first_payload.get("id")) != thread_id
    ):
        raise ValueError("Codex rollout session identity did not match its filename")
    if parent_thread_id is None:
        if first_payload.get("source") != "exec":
            raise ValueError("Codex parent rollout was not created by exec")
    else:
        source = first_payload.get("source")
        spawn = (
            source.get("subagent", {}).get("thread_spawn", {}) if isinstance(source, dict) else {}
        )
        if (
            not isinstance(spawn, dict)
            or spawn.get("parent_thread_id") != parent_thread_id
            or spawn.get("depth") != 1
            or spawn.get("agent_path") != expected_agent_path
        ):
            raise ValueError("Codex child rollout did not identify the exact parent")
    return events


def _codex_rollout_mapping(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ValueError(f"Codex {label} was not JSON text")
    parsed = _facade()._load_canary_json(value, maximum_bytes=64 * 1024)
    if not isinstance(parsed, dict):
        raise ValueError(f"Codex {label} was not a JSON object")
    return parsed


def _codex_child_prompt_delivery(
    events: list[dict[str, Any]],
    *,
    parent_thread_id: str,
    tool_use_id: str,
) -> dict[str, Any]:
    """Project one exact child envelope without retaining its token or prompt."""

    from agency_runtime.core.native_child_prompt_delivery import (
        parse_native_child_prompt_delivery,
    )

    deliveries: dict[tuple[str, ...], dict[str, Any]] = {}
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        texts: list[str] = []
        if event.get("type") == "response_item" and payload.get("type") in {
            "agent_message",
            "message",
        }:
            content = payload.get("content")
            if isinstance(content, list):
                texts.extend(
                    str(item.get("text"))
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") == "input_text"
                    and isinstance(item.get("text"), str)
                )
        elif event.get("type") == "event_msg" and payload.get("type") == "user_message":
            if isinstance(payload.get("message"), str):
                texts.append(payload["message"])
        for text in texts:
            delivery = parse_native_child_prompt_delivery(text)
            if delivery is None:
                continue
            if (
                delivery.host != "codex"
                or delivery.tool_use_id != tool_use_id
                or delivery.parent_session_id != parent_thread_id
            ):
                raise ValueError("Codex child prompt delivery did not match the native call")
            projection = {
                "host": delivery.host,
                "parent_session_id": delivery.parent_session_id,
                "parent_trace_id": delivery.parent_trace_id,
                "tool_use_id": delivery.tool_use_id,
                "work_unit_id": delivery.work_unit_id,
                "specialist_slug": delivery.specialist_slug,
                "specialist_version": delivery.specialist_version,
                "specialist_prompt_hash": delivery.specialist_prompt_hash,
                "goal_hash": delivery.goal_hash,
            }
            identity = tuple(str(projection[key]) for key in sorted(projection))
            deliveries[identity] = projection
    if len(deliveries) != 1:
        raise ValueError("Codex child rollout did not carry one exact prompt delivery")
    return next(iter(deliveries.values()))


def _codex_rollout_call_data(
    events: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, str],
]:
    """Collect only bounded tool identities and lifecycle metadata."""

    calls: list[dict[str, Any]] = []
    outputs: dict[str, dict[str, Any]] = {}
    activities: list[dict[str, Any]] = []
    unexpected: dict[str, str] = {}
    for index, event in enumerate(events):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "event_msg" and payload.get("type") == "sub_agent_activity":
            activities.append(payload)
            continue
        if event.get("type") != "response_item":
            continue
        item_type = str(payload.get("type") or "").strip()
        if item_type not in _CODEX_ROLLOUT_RESPONSE_TYPES:
            unexpected[f"response-{index}"] = item_type or "unknown"
            continue
        if item_type == "function_call":
            item_id = str(payload.get("id") or "").strip()
            call_id = str(payload.get("call_id") or "").strip()
            name = str(payload.get("name") or "").strip()
            namespace = str(payload.get("namespace") or "").strip()
            if (
                not item_id
                or len(item_id) > 256
                or not call_id
                or len(call_id) > 256
                or not name
                or len(name) > 128
            ):
                raise ValueError("invalid Codex rollout tool identity")
            if name not in {"spawn_agent", "followup_task", "wait_agent"}:
                unexpected[call_id] = name
                continue
            if namespace != "collaboration":
                raise ValueError("Codex rollout native tool namespace was invalid")
            calls.append(
                {
                    "id": item_id,
                    "call_id": call_id,
                    "name": name,
                    "arguments": _codex_rollout_mapping(
                        payload.get("arguments"),
                        label=f"{name} arguments",
                    ),
                    "index": index,
                }
            )
        elif item_type == "function_call_output":
            call_id = str(payload.get("call_id") or "").strip()
            if not call_id or len(call_id) > 256 or call_id in outputs:
                raise ValueError("invalid Codex rollout tool output identity")
            call = next((item for item in calls if item["call_id"] == call_id), None)
            if call is not None and call["name"] == "followup_task":
                if payload.get("output") != "":
                    raise ValueError("Codex followup output was not empty")
                outputs[call_id] = None
            else:
                outputs[call_id] = _codex_rollout_mapping(
                    payload.get("output"),
                    label="tool output",
                )
    return calls, outputs, activities, unexpected


def _assert_codex_child_rollout_is_tool_free(events: list[dict[str, Any]]) -> None:
    """Reject every child-side tool event; the canary child is response-only."""

    for event in events:
        payload = event.get("payload")
        if (
            event.get("type") == "event_msg"
            and isinstance(payload, dict)
            and payload.get("type") == "sub_agent_activity"
        ):
            raise ValueError("Codex canary child started another native child")
        if (
            event.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") not in {"agent_message", "message", "reasoning"}
        ):
            raise ValueError("Codex canary child used a tool")


def _codex_rollout_nested_strings(value: Any) -> list[str]:
    """Return bounded nested strings from an already bounded rollout value."""

    if isinstance(value, str):
        result = [value]
        if value.lstrip().startswith(("{", "[")):
            try:
                nested = _facade()._load_canary_json(value, maximum_bytes=64 * 1024)
            except (TypeError, ValueError):
                nested = None
            if nested is not None:
                result.extend(_codex_rollout_nested_strings(nested))
        return result
    if isinstance(value, Mapping):
        return [text for item in value.values() for text in _codex_rollout_nested_strings(item)]
    if isinstance(value, (list, tuple)):
        return [text for item in value for text in _codex_rollout_nested_strings(item)]
    return []


def _codex_child_turn_windows(
    events: list[dict[str, Any]],
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Return exact activation and execution windows after two causal turns."""

    starts: list[tuple[int, str]] = []
    completions: list[tuple[int, str, dict[str, Any]]] = []
    for index, event in enumerate(events):
        payload = event.get("payload")
        if event.get("type") != "event_msg" or not isinstance(payload, dict):
            continue
        event_type = payload.get("type")
        turn_id = str(payload.get("turn_id") or "").strip()
        if event_type == "task_started" and turn_id:
            starts.append((index, turn_id))
        elif event_type == "task_complete" and turn_id:
            completions.append((index, turn_id, payload))
    if (
        len(starts) != 2
        or len(completions) != 2
        or starts[0][1] != completions[0][1]
        or starts[1][1] != completions[1][1]
        or not starts[0][0] < completions[0][0] < starts[1][0] < completions[1][0]
    ):
        raise ValueError("Codex child rollout did not prove two causal turns")
    if any(
        completion.get("error") not in {None, ""}
        or not isinstance(completion.get("last_agent_message"), str)
        for _index, _turn_id, completion in completions
    ):
        raise ValueError("Codex child rollout completed without a successful message")
    return (
        (starts[0][0], completions[0][0] + 1),
        (completions[0][0] + 1, completions[1][0] + 1),
    )


def _assert_codex_child_activation_is_tool_free(events: list[dict[str, Any]]) -> None:
    """Reject product work or tool activity during the readiness-only turn."""

    activation_window, _execution_window = _codex_child_turn_windows(events)
    for event in events[slice(*activation_window)]:
        payload = event.get("payload")
        if (
            event.get("type") == "event_msg"
            and isinstance(payload, dict)
            and payload.get("type") == "sub_agent_activity"
        ):
            raise ValueError("Codex product child delegated during its activation turn")
        if (
            event.get("type") == "response_item"
            and isinstance(payload, dict)
            and payload.get("type") not in {"agent_message", "message", "reasoning"}
        ):
            raise ValueError("Codex product child used a tool during its activation turn")


def _codex_child_execution_projection(
    events: list[dict[str, Any]],
) -> dict[str, str]:
    """Project one execution envelope between two exact child completions."""

    from agency_runtime.core.native_child_prompt_delivery import (
        parse_codex_native_child_execution_message,
    )

    _activation_window, (window_start, window_end) = _codex_child_turn_windows(events)
    deliveries = [
        delivery
        for event in events[window_start:window_end]
        for text in _codex_rollout_nested_strings(event.get("payload"))
        for delivery in (parse_codex_native_child_execution_message(text),)
        if delivery is not None
    ]
    if len(deliveries) != 1:
        raise ValueError("Codex child rollout did not carry one exact execution envelope")
    delivery = deliveries[0]
    return {
        "work_unit_id": delivery.work_unit_id,
        "native_task_name": delivery.native_task_name,
        "goal_hash": delivery.goal_hash,
    }


def _codex_exact_rollout_calls(
    calls: list[dict[str, Any]],
    outputs: dict[str, Any],
    activities: list[dict[str, Any]],
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], dict[str, Any]],
    dict[str, Any],
    str,
    str,
    dict[str, str] | None,
]:
    """Validate one spawn, activation wait, execution trigger, and execution wait."""

    spawn_calls = [call for call in calls if call["name"] == "spawn_agent"]
    followup_calls = [call for call in calls if call["name"] == "followup_task"]
    wait_calls = [call for call in calls if call["name"] == "wait_agent"]
    if len(spawn_calls) != 1 or len(followup_calls) != 1 or len(wait_calls) != 2:
        raise ValueError("Codex rollout did not contain one spawn, one followup, and two waits")
    spawn = spawn_calls[0]
    followup = followup_calls[0]
    waits = tuple(sorted(wait_calls, key=lambda call: call["index"]))
    if set(outputs) != {call["call_id"] for call in calls}:
        raise ValueError("Codex rollout tool outputs did not match the exact native calls")
    if [call["name"] for call in sorted(calls, key=lambda call: call["index"])] != [
        "spawn_agent",
        "wait_agent",
        "followup_task",
        "wait_agent",
    ]:
        raise ValueError("Codex collaboration calls were not causally ordered")
    spawn_args = spawn["arguments"]
    followup_args = followup["arguments"]
    if (
        set(spawn_args) != {"fork_turns", "message", "task_name"}
        or spawn_args.get("fork_turns") != "none"
        or not isinstance(spawn_args.get("message"), str)
        or not isinstance(spawn_args.get("task_name"), str)
    ):
        raise ValueError("Codex spawn arguments exceeded the canary contract")
    if any(
        set(wait["arguments"]) != {"timeout_ms"} or wait["arguments"].get("timeout_ms") != 60_000
        for wait in waits
    ):
        raise ValueError("Codex wait arguments exceeded the canary contract")
    spawn_output = outputs.get(spawn["call_id"])
    if (
        not isinstance(spawn_output, dict)
        or set(spawn_output) != {"task_name"}
        or not isinstance(spawn_output.get("task_name"), str)
        or outputs.get(followup["call_id"], "not-empty") is not None
        or any(
            not isinstance(outputs.get(wait["call_id"]), dict)
            or outputs[wait["call_id"]].get("message") != "Wait completed."
            or outputs[wait["call_id"]].get("timed_out") is not False
            for wait in waits
        )
    ):
        raise ValueError("Codex rollout did not prove completed native calls")
    start_activities = [
        activity
        for activity in activities
        if activity.get("event_id") == spawn["call_id"] and activity.get("kind") == "started"
    ]
    followup_activities = [
        activity
        for activity in activities
        if activity.get("event_id") == followup["call_id"] and activity.get("kind") == "interacted"
    ]
    if len(activities) != 2 or len(start_activities) != 1 or len(followup_activities) != 1:
        raise ValueError("Codex rollout did not identify one child start and interaction")
    activity = start_activities[0]
    followup_activity = followup_activities[0]
    receiver_id = _codex_thread_id(activity.get("agent_thread_id"))
    native_task_name = str(spawn_args["task_name"]).strip()
    from agency_runtime.core.native_child_prompt_delivery import (
        is_codex_opaque_collaboration_message,
        parse_codex_native_child_execution_message,
        render_codex_native_child_execution_message,
    )

    followup_message = followup_args.get("message")
    execution = parse_codex_native_child_execution_message(followup_message)
    opaque_followup = is_codex_opaque_collaboration_message(followup_message)
    if (
        not native_task_name
        or len(native_task_name) > 128
        or activity.get("agent_path") != spawn_output["task_name"]
        or not str(spawn_output["task_name"]).endswith(f"/{native_task_name}")
        or set(followup_args) != {"message", "target"}
        or followup_args.get("target") != spawn_output["task_name"]
        or (execution is None and not opaque_followup)
        or (
            execution is not None
            and (
                execution.native_task_name != native_task_name
                or followup_message
                != render_codex_native_child_execution_message(
                    work_unit_id=execution.work_unit_id,
                    goal_hash=execution.goal_hash,
                )
            )
        )
        or followup_activity.get("agent_thread_id") != receiver_id
        or followup_activity.get("agent_path") != spawn_output["task_name"]
    ):
        raise ValueError("Codex child execution trigger did not match its native task")
    return (
        spawn,
        waits,
        followup,
        receiver_id,
        native_task_name,
        (
            {
                "work_unit_id": execution.work_unit_id,
                "native_task_name": execution.native_task_name,
                "goal_hash": execution.goal_hash,
            }
            if execution is not None
            else None
        ),
    )


def _codex_rollout_collaboration_evidence(
    stdout: str,
    rollout_root: Path,
    *,
    not_before: float | None,
    not_after: float | None,
) -> dict[str, Any] | None:
    """Project the native V2 lifecycle omitted by Codex 0.145 stdout JSONL."""

    parent_thread_id = _codex_stdout_thread_id(stdout)
    if parent_thread_id is None:
        return None
    events = _codex_rollout_events(
        rollout_root,
        parent_thread_id,
        parent_thread_id=None,
        expected_agent_path=None,
        not_before=not_before,
        not_after=not_after,
    )
    calls, outputs, activities, unexpected = _codex_rollout_call_data(events)
    spawn, waits, followup, receiver_id, native_task_name, declared_execution = (
        _codex_exact_rollout_calls(
            calls,
            outputs,
            activities,
        )
    )
    child_events = _codex_rollout_events(
        rollout_root,
        receiver_id,
        parent_thread_id=parent_thread_id,
        expected_agent_path=f"/root/{native_task_name}",
        not_before=not_before,
        not_after=not_after,
    )
    _assert_codex_child_rollout_is_tool_free(child_events)
    execution_delivery = _codex_child_execution_projection(child_events)
    if declared_execution is not None and execution_delivery != declared_execution:
        raise ValueError("Codex child rollout execution did not match its followup")
    prompt_delivery = _codex_child_prompt_delivery(
        child_events,
        parent_thread_id=parent_thread_id,
        tool_use_id=spawn["call_id"],
    )
    if any(
        prompt_delivery.get(field) != execution_delivery.get(field)
        for field in ("work_unit_id", "goal_hash")
    ):
        raise ValueError("Codex child execution did not match its activation delivery")
    projected_calls = [
        {
            "id": spawn["id"],
            "event_type": "rollout_call_completed",
            "tool": "spawn_agent",
            "sender_thread_id": parent_thread_id,
            "receiver_thread_ids": [receiver_id],
            "agents_states": {receiver_id: "running"},
            "status": "completed",
            "prompt_delivery": prompt_delivery,
            "native_task_name": native_task_name,
            "execution_delivery": execution_delivery,
            "followup_tool_use_id": followup["call_id"],
            "evidence_source": "persisted_rollout",
        },
        {
            "id": waits[0]["id"],
            "event_type": "rollout_call_completed",
            "tool": "wait",
            "sender_thread_id": parent_thread_id,
            "receiver_thread_ids": [receiver_id],
            "agents_states": {receiver_id: "completed"},
            "status": "completed",
            "prompt_delivery": None,
            "evidence_source": "persisted_rollout",
        },
        {
            "id": followup["id"],
            "event_type": "rollout_call_completed",
            "tool": "followup_task",
            "sender_thread_id": parent_thread_id,
            "receiver_thread_ids": [receiver_id],
            "agents_states": {receiver_id: "running"},
            "status": "completed",
            "prompt_delivery": None,
            "execution_delivery": execution_delivery,
            "followup_tool_use_id": followup["call_id"],
            "evidence_source": "persisted_rollout",
        },
        {
            "id": waits[1]["id"],
            "event_type": "rollout_call_completed",
            "tool": "wait",
            "sender_thread_id": parent_thread_id,
            "receiver_thread_ids": [receiver_id],
            "agents_states": {receiver_id: "completed"},
            "status": "completed",
            "prompt_delivery": None,
            "evidence_source": "persisted_rollout",
        },
    ]
    return {
        "calls": projected_calls,
        "spawn_count": 1,
        "followup_count": 1,
        "wait_count": 2,
        "unexpected_item_types": sorted(set(unexpected.values())),
        "unexpected_item_count": len(unexpected),
        "evidence_source": "persisted_rollout",
    }


def _codex_product_rollout_call_data(
    events: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    list[dict[str, Any]],
    int,
    int,
]:
    """Collect product collaboration calls while ignoring product tool content."""

    calls: list[dict[str, Any]] = []
    raw_outputs: list[tuple[str, object]] = []
    activities: list[dict[str, Any]] = []
    unexpected_item_count = 0
    agent_message_count = 0
    call_ids: set[str] = set()
    for index, event in enumerate(events):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "event_msg" and payload.get("type") == "sub_agent_activity":
            activities.append(payload)
            continue
        if event.get("type") != "response_item":
            continue
        item_type = str(payload.get("type") or "").strip()
        if item_type in {"agent_message", "message"}:
            agent_message_count += 1
            continue
        if item_type == "reasoning":
            continue
        if item_type == "function_call":
            item_id = str(payload.get("id") or "").strip()
            call_id = str(payload.get("call_id") or "").strip()
            name = str(payload.get("name") or "").strip()
            namespace = str(payload.get("namespace") or "").strip()
            if namespace != "collaboration" or name not in {
                "spawn_agent",
                "followup_task",
                "wait_agent",
            }:
                unexpected_item_count += 1
                continue
            if (
                not item_id
                or len(item_id) > 256
                or not call_id
                or len(call_id) > 256
                or call_id in call_ids
            ):
                raise ValueError("invalid Codex product collaboration identity")
            call_ids.add(call_id)
            calls.append(
                {
                    "id": item_id,
                    "call_id": call_id,
                    "name": name,
                    "arguments": _codex_rollout_mapping(
                        payload.get("arguments"),
                        label=f"product {name} arguments",
                    ),
                    "index": index,
                }
            )
            continue
        if item_type == "function_call_output":
            call_id = str(payload.get("call_id") or "").strip()
            if call_id:
                raw_outputs.append((call_id, payload.get("output")))
            continue
        unexpected_item_count += 1
    outputs: dict[str, Any] = {}
    for call_id, output in raw_outputs:
        if call_id not in call_ids:
            continue
        if call_id in outputs:
            raise ValueError("duplicate Codex product collaboration output")
        call = next(item for item in calls if item["call_id"] == call_id)
        outputs[call_id] = _codex_product_rollout_output(call, output)
    return calls, outputs, activities, unexpected_item_count, agent_message_count


def _codex_product_rollout_output(call: Mapping[str, Any], output: object) -> Any:
    """Validate one native product collaboration output by exact call type."""

    if call.get("name") == "followup_task":
        if output != "":
            raise ValueError("Codex product followup output was not empty")
        return None
    return _codex_rollout_mapping(
        output,
        label="product collaboration output",
    )


def _codex_product_spawn_projection(
    spawn: dict[str, Any],
    followup: dict[str, Any],
    *,
    outputs: Mapping[str, Any],
    activities: list[dict[str, Any]],
    rollout_root: Path,
    parent_thread_id: str,
    not_before: float | None,
    not_after: float | None,
) -> tuple[dict[str, Any], int]:
    """Prove one activated and explicitly executed product child."""

    arguments = spawn["arguments"]
    if (
        set(arguments) != {"fork_turns", "message", "task_name"}
        or arguments.get("fork_turns") != "none"
        or not isinstance(arguments.get("message"), str)
        or not isinstance(arguments.get("task_name"), str)
    ):
        raise ValueError("Codex product spawn arguments exceeded the exact contract")
    native_task_name = str(arguments["task_name"]).strip()
    if not native_task_name or len(native_task_name) > 128:
        raise ValueError("Codex product spawn task name was invalid")
    output = outputs.get(spawn["call_id"])
    if (
        not isinstance(output, dict)
        or set(output) not in ({"task_name"}, {"task_name", "nickname"})
        or not isinstance(output.get("task_name"), str)
        or not str(output["task_name"]).endswith(f"/{native_task_name}")
        or (
            "nickname" in output
            and (not isinstance(output.get("nickname"), str) or len(str(output["nickname"])) > 128)
        )
    ):
        raise ValueError("Codex product spawn output did not match its native task")
    matching_activities = [
        activity
        for activity in activities
        if activity.get("event_id") == spawn["call_id"] and activity.get("kind") == "started"
    ]
    if len(matching_activities) != 1:
        raise ValueError("Codex product spawn did not identify one native child start")
    activity = matching_activities[0]
    receiver_id = _codex_thread_id(activity.get("agent_thread_id"))
    expected_path = f"/root/{native_task_name}"
    if activity.get("agent_path") != expected_path or output["task_name"] != expected_path:
        raise ValueError("Codex product child path did not match its native task")
    followup_arguments = followup["arguments"]
    from agency_runtime.core.native_child_prompt_delivery import (
        is_codex_opaque_collaboration_message,
        parse_codex_native_child_execution_message,
        render_codex_native_child_execution_message,
    )

    followup_message = (
        followup_arguments.get("message") if isinstance(followup_arguments, dict) else None
    )
    execution = parse_codex_native_child_execution_message(followup_message)
    opaque_followup = is_codex_opaque_collaboration_message(followup_message)
    followup_activities = [
        candidate
        for candidate in activities
        if candidate.get("event_id") == followup["call_id"]
        and candidate.get("kind") == "interacted"
    ]
    if (
        set(followup_arguments) != {"message", "target"}
        or followup_arguments.get("target") != expected_path
        or outputs.get(followup["call_id"], "not-empty") is not None
        or (execution is None and not opaque_followup)
        or (
            execution is not None
            and (
                execution.native_task_name != native_task_name
                or followup_message
                != render_codex_native_child_execution_message(
                    work_unit_id=execution.work_unit_id,
                    goal_hash=execution.goal_hash,
                )
            )
        )
        or len(followup_activities) != 1
        or followup_activities[0].get("agent_thread_id") != receiver_id
        or followup_activities[0].get("agent_path") != expected_path
    ):
        raise ValueError("Codex product followup did not match its activated child")
    child_events = _codex_rollout_events(
        rollout_root,
        receiver_id,
        parent_thread_id=parent_thread_id,
        expected_agent_path=expected_path,
        not_before=not_before,
        not_after=not_after,
    )
    _assert_codex_child_activation_is_tool_free(child_events)
    execution_delivery = _codex_child_execution_projection(child_events)
    declared_execution = (
        {
            "work_unit_id": execution.work_unit_id,
            "native_task_name": execution.native_task_name,
            "goal_hash": execution.goal_hash,
        }
        if execution is not None
        else None
    )
    if declared_execution is not None and execution_delivery != declared_execution:
        raise ValueError("Codex product child execution did not match its followup")
    prompt_delivery = _codex_child_prompt_delivery(
        child_events,
        parent_thread_id=parent_thread_id,
        tool_use_id=spawn["call_id"],
    )
    from agency_runtime.core.delegation.native_labels import (
        codex_task_name_for_work_unit,
    )

    if native_task_name != codex_task_name_for_work_unit(prompt_delivery["work_unit_id"]):
        raise ValueError("Codex product child task did not match its delivered work unit")
    if any(
        prompt_delivery.get(field) != execution_delivery.get(field)
        for field in ("work_unit_id", "goal_hash")
    ):
        raise ValueError("Codex product execution did not match its activation delivery")
    child_tool_call_count = sum(
        event.get("type") == "response_item"
        and isinstance(event.get("payload"), dict)
        and event["payload"].get("type") in {"function_call", "custom_tool_call"}
        for event in child_events
    )
    return (
        {
            "id": spawn["id"],
            "event_type": "rollout_call_completed",
            "tool": "spawn_agent",
            "sender_thread_id": parent_thread_id,
            "receiver_thread_ids": [receiver_id],
            "status": "completed",
            "prompt_delivery": prompt_delivery,
            "execution_delivery": execution_delivery,
            "followup_id": followup["id"],
            "followup_tool_use_id": followup["call_id"],
            "native_task_name": native_task_name,
            "child_status": "completed",
            "activation_completion_count": 1,
            "execution_completion_count": 1,
            "evidence_source": "persisted_rollout",
        },
        child_tool_call_count,
    )


def _codex_product_wait_counts(
    waits: list[dict[str, Any]],
    *,
    outputs: Mapping[str, dict[str, Any]],
    last_spawn_index: int,
) -> tuple[int, int]:
    completed = 0
    timed_out = 0
    completed_after_last_spawn = False
    for wait in waits:
        arguments = wait["arguments"]
        timeout_ms = arguments.get("timeout_ms") if isinstance(arguments, dict) else None
        if set(arguments) not in (set(), {"timeout_ms"}) or (
            "timeout_ms" in arguments
            and (
                not isinstance(timeout_ms, int)
                or isinstance(timeout_ms, bool)
                or not 1 <= timeout_ms <= _CODEX_PRODUCT_MAX_WAIT_TIMEOUT_MS
            )
        ):
            raise ValueError("Codex product wait arguments exceeded the bounded contract")
        output = outputs.get(wait["call_id"])
        if (
            not isinstance(output, dict)
            or set(output) != {"message", "timed_out"}
            or not isinstance(output.get("message"), str)
            or len(str(output["message"])) > 256
            or type(output.get("timed_out")) is not bool
        ):
            raise ValueError("Codex product wait output was invalid")
        if output["timed_out"]:
            timed_out += 1
        else:
            completed += 1
            completed_after_last_spawn = (
                completed_after_last_spawn or wait["index"] > last_spawn_index
            )
    if completed == 0 or not completed_after_last_spawn:
        raise ValueError("Codex product parent did not complete a wait after its final spawn")
    return completed, timed_out


def _codex_product_rollout_collaboration_evidence(
    stdout: str,
    rollout_root: Path,
    *,
    not_before: float | None,
    not_after: float | None,
) -> dict[str, Any]:
    """Project a bounded exact multi-unit product collaboration topology."""

    parent_thread_id = _codex_stdout_thread_id(stdout)
    if parent_thread_id is None:
        raise ValueError("Codex product stdout omitted its parent thread")
    events = _codex_rollout_events(
        rollout_root,
        parent_thread_id,
        parent_thread_id=None,
        expected_agent_path=None,
        not_before=not_before,
        not_after=not_after,
    )
    calls, outputs, activities, unexpected_count, agent_message_count = (
        _codex_product_rollout_call_data(events)
    )
    spawns = [call for call in calls if call["name"] == "spawn_agent"]
    followups = [call for call in calls if call["name"] == "followup_task"]
    waits = [call for call in calls if call["name"] == "wait_agent"]
    if not 1 <= len(spawns) <= _CODEX_PRODUCT_MAX_SPAWNS:
        raise ValueError("Codex product spawn cardinality was invalid")
    if len(followups) != len(spawns):
        raise ValueError("Codex product followup cardinality was invalid")
    if len(waits) != len(spawns) * 2 or len(waits) > _CODEX_PRODUCT_MAX_WAITS:
        raise ValueError("Codex product wait cardinality was invalid")
    if set(outputs) != {call["call_id"] for call in calls}:
        raise ValueError("Codex product collaboration outputs did not match its calls")
    ordered = sorted(calls, key=lambda call: call["index"])
    expected_names = [
        name
        for _spawn in spawns
        for name in ("spawn_agent", "wait_agent", "followup_task", "wait_agent")
    ]
    if [call["name"] for call in ordered] != expected_names:
        raise ValueError("Codex product collaboration calls were not causally ordered")
    projected_spawns: list[dict[str, Any]] = []
    child_tool_call_count = 0
    for index in range(len(spawns)):
        spawn, _activation_wait, followup, _execution_wait = ordered[index * 4 : index * 4 + 4]
        projected, tool_count = _codex_product_spawn_projection(
            spawn,
            followup,
            outputs=outputs,
            activities=activities,
            rollout_root=rollout_root,
            parent_thread_id=parent_thread_id,
            not_before=not_before,
            not_after=not_after,
        )
        projected_spawns.append(projected)
        child_tool_call_count += tool_count
    if len(activities) != len(spawns) * 2:
        raise ValueError("Codex product child activity cardinality was invalid")
    receiver_ids = [row["receiver_thread_ids"][0] for row in projected_spawns]
    task_names = [row["native_task_name"] for row in projected_spawns]
    if len(set(receiver_ids)) != len(receiver_ids) or len(set(task_names)) != len(task_names):
        raise ValueError("Codex product children were not distinct")
    completed_waits, timed_out_waits = _codex_product_wait_counts(
        waits,
        outputs=outputs,
        last_spawn_index=max(spawn["index"] for spawn in spawns),
    )
    if completed_waits != len(waits) or timed_out_waits != 0:
        raise ValueError("Codex product collaboration waits did not all complete")
    stdout_projection = codex_collaboration_evidence(stdout)
    if stdout_projection is None or (
        stdout_projection["spawn_count"] > len(spawns)
        or stdout_projection["followup_count"] > len(followups)
        or stdout_projection["wait_count"] > len(waits)
    ):
        raise ValueError("Codex product stdout contradicted its persisted rollout")
    observed_receivers = {
        str(receiver)
        for row in stdout_projection["calls"]
        for receiver in row.get("receiver_thread_ids", [])
    }
    if not observed_receivers.issubset(set(receiver_ids)):
        raise ValueError("Codex product stdout identified a different child")
    return {
        "schema": _CODEX_PRODUCT_COLLABORATION_SCHEMA,
        "calls": projected_spawns,
        "spawn_count": len(projected_spawns),
        "followup_count": len(followups),
        "wait_count": len(waits),
        "completed_wait_count": completed_waits,
        "timed_out_wait_count": timed_out_waits,
        "completed_child_count": len(projected_spawns),
        "failed_child_count": 0,
        "child_tool_call_count": child_tool_call_count,
        "parent_agent_message_count": agent_message_count,
        "unexpected_item_count": (
            unexpected_count + int(stdout_projection.get("unexpected_item_count") or 0)
        ),
        "host_notice_types": list(stdout_projection.get("host_notice_types") or []),
        "host_notice_count": int(stdout_projection.get("host_notice_count") or 0),
        "evidence_source": "persisted_rollout",
    }


def _codex_collaboration_call_projection(
    event: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    """Validate and project one content-free collaboration event."""

    from agency_runtime.core.native_child_prompt_delivery import (
        parse_codex_native_child_execution_message,
        parse_native_child_prompt_delivery,
    )

    item_id = str(item.get("id") or "").strip()
    tool = str(item.get("tool") or "").strip()
    if (
        not item_id
        or len(item_id) > 256
        or tool
        not in {
            "spawn_agent",
            "followup_task",
            "wait",
        }
    ):
        raise ValueError("invalid Codex collaboration event identity")
    receivers = item.get("receiver_thread_ids")
    if not isinstance(receivers, list) or any(
        not isinstance(value, str) or not value or len(value) > 256 for value in receivers
    ):
        raise ValueError("invalid Codex collaboration receiver identity")
    states = item.get("agents_states")
    if not isinstance(states, dict) or any(
        not isinstance(key, str) or not key or len(key) > 256 or not isinstance(value, dict)
        for key, value in states.items()
    ):
        raise ValueError("invalid Codex collaboration state projection")
    projected_states = {key: str(value.get("status") or "") for key, value in states.items()}
    if set(projected_states) != set(receivers):
        raise ValueError("Codex collaboration states do not match receiver identities")
    valid_states = {
        "pending_init",
        "running",
        "interrupted",
        "completed",
        "errored",
        "shutdown",
        "not_found",
    }
    if any(status not in valid_states for status in projected_states.values()):
        raise ValueError("invalid Codex collaboration agent state")
    prompt = item.get("prompt")
    if prompt is not None and not isinstance(prompt, str):
        raise ValueError("invalid Codex collaboration prompt")
    sender_thread_id = str(item.get("sender_thread_id") or "").strip()
    if not sender_thread_id or len(sender_thread_id) > 256:
        raise ValueError("invalid Codex collaboration sender identity")
    delivery = parse_native_child_prompt_delivery(prompt) if prompt else None
    execution = parse_codex_native_child_execution_message(prompt) if prompt else None
    prompt_projection = (
        {
            "host": delivery.host,
            "parent_session_id": delivery.parent_session_id,
            "parent_trace_id": delivery.parent_trace_id,
            "tool_use_id": delivery.tool_use_id,
            "work_unit_id": delivery.work_unit_id,
            "specialist_slug": delivery.specialist_slug,
            "specialist_version": delivery.specialist_version,
            "specialist_prompt_hash": delivery.specialist_prompt_hash,
            "goal_hash": delivery.goal_hash,
        }
        if delivery is not None
        else None
    )
    execution_projection = (
        {
            "work_unit_id": execution.work_unit_id,
            "native_task_name": execution.native_task_name,
            "goal_hash": execution.goal_hash,
        }
        if execution is not None
        else None
    )
    if tool == "followup_task" and execution_projection is None:
        raise ValueError("Codex followup collaboration prompt was not an execution delivery")
    return {
        "id": item_id,
        "event_type": str(event["type"]),
        "tool": tool,
        "sender_thread_id": sender_thread_id,
        "receiver_thread_ids": list(receivers),
        "agents_states": projected_states,
        "status": str(item.get("status") or ""),
        "prompt_delivery": prompt_projection,
        "execution_delivery": execution_projection,
    }


def _merge_codex_collaboration_call(
    prior: dict[str, Any] | None,
    projection: dict[str, Any],
) -> dict[str, Any]:
    """Allow only monotonic started-to-completed collaboration evolution."""

    if prior is None:
        return projection
    if any(prior[field] != projection[field] for field in ("tool", "sender_thread_id")):
        raise ValueError("conflicting Codex collaboration event")
    prior_receivers = prior["receiver_thread_ids"]
    receivers = projection["receiver_thread_ids"]
    if prior_receivers and receivers and prior_receivers != receivers:
        raise ValueError("conflicting Codex collaboration receiver identity")
    prior_delivery = prior.get("prompt_delivery")
    projected_delivery = projection.get("prompt_delivery")
    if (
        prior_delivery is not None
        and projected_delivery is not None
        and prior_delivery != projected_delivery
    ):
        raise ValueError("conflicting Codex collaboration prompt identity")
    if not receivers:
        projection["receiver_thread_ids"] = prior_receivers
        projection["agents_states"] = prior["agents_states"]
    if projected_delivery is None:
        projection["prompt_delivery"] = prior_delivery
    prior_execution = prior.get("execution_delivery")
    projected_execution = projection.get("execution_delivery")
    if (
        prior_execution is not None
        and projected_execution is not None
        and prior_execution != projected_execution
    ):
        raise ValueError("conflicting Codex collaboration execution identity")
    if projected_execution is None:
        projection["execution_delivery"] = prior_execution
    return projection


def _merge_codex_rollout_evidence(
    stdout_projection: dict[str, Any],
    rollout_projection: dict[str, Any],
) -> dict[str, Any] | None:
    """Cross-check the lossy JSONL projection against persisted native calls."""

    if (
        stdout_projection["spawn_count"] > rollout_projection["spawn_count"]
        or stdout_projection["followup_count"] > rollout_projection["followup_count"]
        or stdout_projection["wait_count"] > rollout_projection["wait_count"]
    ):
        return None
    ordered = stdout_projection["calls"]
    parent_id = rollout_projection["calls"][0]["sender_thread_id"]
    if any(row.get("sender_thread_id") != parent_id for row in ordered):
        return None
    for row in ordered:
        candidates = [
            candidate
            for candidate in rollout_projection["calls"]
            if candidate["tool"] == row["tool"]
        ]
        if not candidates:
            return None
        if row["receiver_thread_ids"] and not any(
            row["receiver_thread_ids"] == candidate["receiver_thread_ids"]
            for candidate in candidates
        ):
            return None
        if row.get("prompt_delivery") is not None and not any(
            row["prompt_delivery"] == candidate.get("prompt_delivery") for candidate in candidates
        ):
            return None
        if row.get("execution_delivery") is not None and not any(
            row["execution_delivery"] == candidate.get("execution_delivery")
            for candidate in candidates
        ):
            return None
    rollout_projection["unexpected_item_types"] = sorted(
        set(stdout_projection["unexpected_item_types"])
        | set(rollout_projection["unexpected_item_types"])
    )
    rollout_projection["unexpected_item_count"] = (
        stdout_projection["unexpected_item_count"] + rollout_projection["unexpected_item_count"]
    )
    rollout_projection["host_notice_types"] = list(stdout_projection["host_notice_types"])
    rollout_projection["host_notice_count"] = stdout_projection["host_notice_count"]
    return rollout_projection


def _codex_stdout_host_notice(event: Mapping[str, Any], item: Mapping[str, Any]) -> str | None:
    """Classify one exact non-critical Codex JSONL notice without retaining its message."""

    if event.get("type") != "item.completed" or item.get("type") != "error":
        return None
    message = item.get("message")
    return _CODEX_STDOUT_HOST_NOTICE_BY_MESSAGE.get(message) if isinstance(message, str) else None


def codex_collaboration_evidence(
    stdout: str,
    *,
    rollout_root: Path | None = None,
    rollout_not_before: float | None = None,
    rollout_not_after: float | None = None,
) -> dict[str, Any] | None:
    """Project bounded content-free native-child evidence from Codex JSONL."""

    calls: dict[str, dict[str, Any]] = {}
    unexpected_items: dict[str, str] = {}
    host_notices: list[str] = []
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = _facade()._load_canary_json(line, maximum_bytes=256_000)
            if not isinstance(event, dict) or event.get("type") not in {
                "item.started",
                "item.completed",
            }:
                continue
            item = event.get("item")
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").strip()
            if item_type != "collab_tool_call":
                notice_type = _codex_stdout_host_notice(event, item)
                if notice_type in CODEX_STDOUT_HOST_NOTICE_TYPES:
                    host_notices.append(notice_type)
                    continue
                if item_type not in {"agent_message", "reasoning"}:
                    item_id = str(item.get("id") or "").strip()
                    unexpected_items[item_id or f"anonymous-{len(unexpected_items)}"] = (
                        item_type or "unknown"
                    )
                continue
            projection = _codex_collaboration_call_projection(event, item)
            item_id = str(projection["id"])
            prior = calls.get(item_id)
            if event.get("type") == "item.completed" or prior is None:
                calls[item_id] = _merge_codex_collaboration_call(prior, projection)
    except (TypeError, ValueError):
        return None
    ordered = sorted(calls.values(), key=lambda row: row["id"])
    stdout_projection = {
        "calls": ordered,
        "spawn_count": sum(row["tool"] == "spawn_agent" for row in ordered),
        "followup_count": sum(row["tool"] == "followup_task" for row in ordered),
        "wait_count": sum(row["tool"] == "wait" for row in ordered),
        "unexpected_item_types": sorted(set(unexpected_items.values())),
        "unexpected_item_count": len(unexpected_items),
        "host_notice_types": sorted(set(host_notices)),
        "host_notice_count": len(host_notices),
    }
    if rollout_root is None:
        return stdout_projection
    if (
        stdout_projection["spawn_count"] not in {0, 1}
        or stdout_projection["followup_count"] not in {0, 1}
        or stdout_projection["wait_count"] not in {0, 1, 2}
        or len(stdout_projection["calls"])
        != stdout_projection["spawn_count"]
        + stdout_projection["followup_count"]
        + stdout_projection["wait_count"]
    ):
        return None
    try:
        thread_id = _codex_stdout_thread_id(stdout)
        if thread_id is None:
            return stdout_projection
        rollout_projection = _codex_rollout_collaboration_evidence(
            stdout,
            rollout_root,
            not_before=rollout_not_before,
            not_after=rollout_not_after,
        )
        if rollout_projection is None:
            return None
        return _merge_codex_rollout_evidence(stdout_projection, rollout_projection)
    except (OSError, TypeError, ValueError):
        return None


def _codex_rollout_content_free_counts(
    events: list[dict[str, Any]],
) -> dict[str, int]:
    """Count native lifecycle shapes without retaining rollout content."""

    counts = {
        "spawn_count": 0,
        "followup_count": 0,
        "wait_count": 0,
        "tool_output_count": 0,
        "child_start_count": 0,
        "child_interaction_count": 0,
        "agent_message_count": 0,
        "unexpected_item_count": 0,
    }
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "event_msg":
            if payload.get("type") == "sub_agent_activity":
                if payload.get("kind") == "started":
                    counts["child_start_count"] += 1
                elif payload.get("kind") == "interacted":
                    counts["child_interaction_count"] += 1
            continue
        if event.get("type") != "response_item":
            continue
        item_type = str(payload.get("type") or "").strip()
        if item_type == "function_call":
            name = str(payload.get("name") or "").strip()
            namespace = str(payload.get("namespace") or "").strip()
            if namespace == "collaboration" and name == "spawn_agent":
                counts["spawn_count"] += 1
            elif namespace == "collaboration" and name == "followup_task":
                counts["followup_count"] += 1
            elif namespace == "collaboration" and name == "wait_agent":
                counts["wait_count"] += 1
            else:
                counts["unexpected_item_count"] += 1
        elif item_type == "function_call_output":
            counts["tool_output_count"] += 1
        elif item_type in {"agent_message", "message"}:
            counts["agent_message_count"] += 1
        elif item_type != "reasoning":
            counts["unexpected_item_count"] += 1
    return counts


def _codex_collaboration_diagnostic_reason(
    counts: Mapping[str, int],
    *,
    rollout_contract: str,
) -> str:
    if counts["spawn_count"] == 0:
        return "parent_spawn_missing"
    if rollout_contract == "canary" and counts["spawn_count"] != 1:
        return "parent_spawn_ambiguous"
    if counts["followup_count"] == 0:
        return "parent_followup_missing"
    if rollout_contract == "canary" and counts["followup_count"] != 1:
        return "parent_followup_ambiguous"
    if counts["wait_count"] == 0:
        return "parent_wait_missing"
    if rollout_contract == "canary" and counts["wait_count"] != 2:
        return "parent_wait_ambiguous"
    if counts["tool_output_count"] < (
        counts["spawn_count"] + counts["followup_count"] + counts["wait_count"]
    ):
        return "native_tool_output_missing"
    if counts["child_start_count"] < counts["spawn_count"]:
        return "native_child_start_missing"
    if counts["child_interaction_count"] < counts["followup_count"]:
        return "native_child_interaction_missing"
    return "native_collaboration_topology_invalid"


def _codex_rollout_collaboration_diagnostic(
    stdout: str,
    rollout_root: Path,
    *,
    not_before: float | None,
    not_after: float | None,
    rollout_contract: str,
    reason_override: str | None = None,
) -> dict[str, Any]:
    """Explain one failed exact projection using only bounded safe counts."""

    empty_counts = {
        "spawn_count": 0,
        "followup_count": 0,
        "wait_count": 0,
        "tool_output_count": 0,
        "child_start_count": 0,
        "child_interaction_count": 0,
        "agent_message_count": 0,
        "unexpected_item_count": 0,
    }
    try:
        parent_thread_id = _codex_stdout_thread_id(stdout)
        if parent_thread_id is None:
            raise ValueError("Codex did not announce a parent rollout")
        events = _codex_rollout_events(
            rollout_root,
            parent_thread_id,
            parent_thread_id=None,
            expected_agent_path=None,
            not_before=not_before,
            not_after=not_after,
        )
    except (OSError, TypeError, ValueError):
        return {
            "schema": CODEX_COLLABORATION_DIAGNOSTIC_SCHEMA,
            "proven": False,
            "reason": "parent_rollout_unavailable",
            "parent_rollout_observed": False,
            **empty_counts,
        }
    counts = _codex_rollout_content_free_counts(events)
    reason = _codex_collaboration_diagnostic_reason(
        counts,
        rollout_contract=rollout_contract,
    )
    if reason_override in CODEX_COLLABORATION_DIAGNOSTIC_REASONS and (
        reason == "native_collaboration_topology_invalid"
        or (str(reason_override).startswith("product_") and counts["spawn_count"] > 0)
    ):
        reason = str(reason_override)
    return {
        "schema": CODEX_COLLABORATION_DIAGNOSTIC_SCHEMA,
        "proven": False,
        "reason": reason,
        "parent_rollout_observed": True,
        **counts,
    }


def sanitize_codex_collaboration_diagnostic(value: object) -> dict[str, Any] | None:
    """Strictly project the content-free collaboration failure contract."""

    expected = {
        "schema",
        "proven",
        "reason",
        "parent_rollout_observed",
        "spawn_count",
        "followup_count",
        "wait_count",
        "tool_output_count",
        "child_start_count",
        "child_interaction_count",
        "agent_message_count",
        "unexpected_item_count",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        return None
    if (
        value.get("schema") != CODEX_COLLABORATION_DIAGNOSTIC_SCHEMA
        or value.get("proven") is not False
        or value.get("reason") not in CODEX_COLLABORATION_DIAGNOSTIC_REASONS
        or type(value.get("parent_rollout_observed")) is not bool
    ):
        return None
    for name in expected - {"schema", "proven", "reason", "parent_rollout_observed"}:
        count = value.get(name)
        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or not 0 <= count <= _CODEX_COLLABORATION_DIAGNOSTIC_COUNT_MAX
        ):
            return None
    return {name: value[name] for name in expected}


def _codex_failure_reason(stderr: object) -> str | None:
    """Classify allowlisted Codex failures without retaining raw stderr."""

    if isinstance(stderr, str) and "collab spawn failed: no thread with id:" in stderr:
        return "native_collaboration_full_history_parent_unavailable"
    return None


_CODEX_HOOK_DIAGNOSTIC_PATTERN = re.compile(
    r"agency_hook_diagnostic codex_post_tool_reconcile="
    r"(?P<reason>[a-z][a-z0-9_]{0,63})"
)
_CODEX_HOOK_EVENT_DIAGNOSTIC_PATTERN = re.compile(
    r"^agency_hook_diagnostic codex_hook_event=(?P<event>[A-Za-z]+) "
    r"stage=(?P<stage>accepted|completed|failed)[ \t]*\r?$",
    re.MULTILINE,
)


def _codex_hook_diagnostic(stderr: object) -> str | None:
    """Project one fixed canary hook diagnostic without retaining raw stderr."""

    if not isinstance(stderr, str):
        return None
    from agency_runtime.core.codex_activation_verification import (
        CODEX_RECONCILIATION_DIAGNOSTIC_REASONS,
    )

    reasons = {match.group("reason") for match in _CODEX_HOOK_DIAGNOSTIC_PATTERN.finditer(stderr)}
    reasons.intersection_update(CODEX_RECONCILIATION_DIAGNOSTIC_REASONS)
    return next(iter(reasons)) if len(reasons) == 1 else None


def _codex_hook_events(stderr: object) -> dict[str, dict[str, int]]:
    """Project bounded, allowlisted hook-stage counts without retaining stderr."""

    if not isinstance(stderr, str):
        return {}
    from agency_runtime.core.codex_activation_verification import (
        CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES,
        MAX_CODEX_HOOK_EVENT_DIAGNOSTIC_COUNT,
        sanitize_codex_hook_event_diagnostics,
    )
    from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS

    allowed_events = frozenset(CODEX_HOOK_EVENTS)
    counts: dict[str, dict[str, int]] = {}
    for match in _CODEX_HOOK_EVENT_DIAGNOSTIC_PATTERN.finditer(stderr):
        event = match.group("event")
        stage = match.group("stage")
        if event not in allowed_events:
            continue
        event_counts = counts.setdefault(
            event,
            dict.fromkeys(CODEX_HOOK_EVENT_DIAGNOSTIC_STAGES, 0),
        )
        event_counts[stage] = min(
            MAX_CODEX_HOOK_EVENT_DIAGNOSTIC_COUNT,
            event_counts[stage] + 1,
        )
    return sanitize_codex_hook_event_diagnostics(counts)


def codex_canary_record(
    result: Any,
    *,
    profile_scope: str = "isolated-profile",
    rollout_root: Path | None = None,
    rollout_not_before: float | None = None,
    rollout_not_after: float | None = None,
    rollout_contract: str = "canary",
) -> dict[str, Any]:
    facade = _facade()
    if rollout_contract not in _CODEX_ROLLOUT_CONTRACTS:
        raise ValueError("unsupported Codex rollout contract")
    completed = facade._process_succeeded(result)
    timed_out = bool(result.timed_out)
    record: dict[str, Any] = {
        "backend": "codex",
        "profile_scope": profile_scope,
        "status": "completed" if completed else "timed_out" if timed_out else "failed",
        "exit_code": 124 if timed_out else result.returncode,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }
    if profile_scope == "isolated-profile":
        record["isolated_plugin"] = {
            "registered": True,
            "enabled": True,
        }
    if timed_out:
        record["failure_reason"] = "codex_exec_timed_out"
    elif failure_reason := _codex_failure_reason(getattr(result, "stderr", "")):
        record["failure_reason"] = failure_reason
    if hook_diagnostic := _codex_hook_diagnostic(getattr(result, "stderr", "")):
        record["hook_diagnostic"] = hook_diagnostic
    if hook_events := _codex_hook_events(getattr(result, "stderr", "")):
        record["hook_events"] = hook_events
    product_topology_reason = None
    if rollout_root is not None and rollout_contract == "product":
        try:
            collaboration = _codex_product_rollout_collaboration_evidence(
                result.stdout,
                rollout_root,
                not_before=rollout_not_before,
                not_after=rollout_not_after,
            )
        except (OSError, TypeError, ValueError) as exc:
            collaboration = None
            product_topology_reason = _codex_product_topology_reason(exc)
    else:
        collaboration = codex_collaboration_evidence(
            result.stdout,
            rollout_root=rollout_root,
            rollout_not_before=rollout_not_before,
            rollout_not_after=rollout_not_after,
        )
    collaboration_diagnostic = None
    if completed and collaboration is None and rollout_root is not None:
        collaboration_diagnostic = _codex_rollout_collaboration_diagnostic(
            result.stdout,
            rollout_root,
            not_before=rollout_not_before,
            not_after=rollout_not_after,
            rollout_contract=rollout_contract,
            reason_override=product_topology_reason,
        )
        record["collaboration_diagnostic"] = collaboration_diagnostic
    output = facade._codex_output(result.stdout) if completed else None
    if completed and output is not None and collaboration is not None:
        record.update(output=output, collaboration=collaboration)
    elif completed:
        record["status"] = "failed"
        diagnostic_reason = (
            _CODEX_COLLABORATION_FAILURE_REASON_BY_DIAGNOSTIC.get(
                collaboration_diagnostic["reason"]
            )
            if collaboration_diagnostic is not None
            else None
        )
        if diagnostic_reason is not None:
            record["failure_reason"] = diagnostic_reason
        elif output is None and collaboration is None:
            record["failure_reason"] = "codex_result_projection_unavailable"
        elif output is None:
            record["failure_reason"] = "codex_output_projection_unavailable"
        else:
            record["failure_reason"] = "codex_collaboration_projection_unavailable"
    return record


def claude_canary_record(result: Any) -> dict[str, Any]:
    facade = _facade()
    completed = facade._process_succeeded(result)
    record: dict[str, Any] = {
        "backend": "claude",
        "profile_scope": "isolated-profile",
        "isolated_plugin": {
            "load_requested": True,
            "registered": None,
            "enabled": None,
        },
        "status": "completed" if completed else "failed",
        "exit_code": result.returncode,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }
    if not completed:
        return record
    try:
        payload = facade._load_canary_json(result.stdout, maximum_bytes=256_000)
    except (TypeError, ValueError):
        payload = None
    if isinstance(payload, dict) and payload.get("result"):
        record["output"] = payload["result"]
    else:
        record.update(status="failed", exit_code=1)
    return record


def remaining_timeout(deadline: float, *, maximum: float | None = None) -> float:
    """Return the positive remainder of one end-to-end canary deadline."""
    remaining = deadline - _facade().time.monotonic()
    if maximum is not None:
        remaining = min(remaining, maximum)
    return max(0.0, remaining)


def _timeout_record(host: str, *, profile_scope: str = "isolated-profile") -> dict[str, Any]:
    return {
        "backend": host,
        "profile_scope": profile_scope,
        "status": "timed_out",
        "exit_code": 124,
        "stdout_truncated": False,
        "stderr_truncated": False,
    }


@dataclass(frozen=True, slots=True)
class SafeCodexCanaryBackend:
    executable: str
    db_path: Path
    timeout: float
    marketplace: Path
    auth_source: Path
    process_runner: Callable[..., Any]
    source_env: Mapping[str, str]
    master_enabled: bool = True
    profile_scope: str = "isolated-profile"
    require_existing_store: bool = False
    exec_options: tuple[str, ...] | None = None
    require_exact_activation_rollout: bool = False
    rollout_contract: str = "canary"
    hook_event_diagnostics: bool = False
    hook_trust_inspector: Callable[..., Mapping[str, Any]] | None = None
    trusted_workdir: str = ""
    trust_mode: str = "attended"

    def _exec_options(self) -> tuple[str, ...]:
        if not isinstance(self.trust_mode, str) or self.trust_mode not in {
            "attended",
            "autonomous_bypass",
        }:
            raise ValueError("unsupported Codex hook trust mode")
        if self.exec_options is not None:
            return self.exec_options
        facade = _facade()
        if self.require_exact_activation_rollout:
            if self.profile_scope == "current-profile" and self.trust_mode == "autonomous_bypass":
                return facade.CODEX_CANARY_EXEC_OPTIONS
            return (
                facade.CODEX_CURRENT_PROFILE_EXEC_OPTIONS
                if self.profile_scope == "current-profile"
                else facade.CODEX_CANARY_EXEC_OPTIONS
            )
        return (
            facade.CODEX_NATIVE_ONLY_CURRENT_PROFILE_EXEC_OPTIONS
            if self.profile_scope == "current-profile"
            else facade.CODEX_NATIVE_ONLY_CANARY_EXEC_OPTIONS
        )

    def _configure_canary_environment(self, env: dict[str, str]) -> None:
        from agency_runtime.core.codex_activation_verification import (
            CODEX_ACTIVATION_EXISTING_STORE_ENV,
            CODEX_HOOK_EVENT_DIAGNOSTICS_ENV,
        )

        if self.require_existing_store or self.require_exact_activation_rollout:
            env[CODEX_ACTIVATION_EXISTING_STORE_ENV] = "1"
        if self.hook_event_diagnostics:
            if not self.require_existing_store:
                raise ValueError("hook event diagnostics require the existing Agency store")
            env[CODEX_HOOK_EVENT_DIAGNOSTICS_ENV] = "1"

    def _verify_current_profile_hook_trust(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float,
    ) -> dict[str, Any] | None:
        """Fail before a model call unless Codex trusts the exact Agency hooks."""

        if (
            self.profile_scope != "current-profile"
            or not self.require_exact_activation_rollout
            or self.trust_mode == "autonomous_bypass"
        ):
            return None
        facade = _facade()
        timeout = facade._remaining_canary_timeout(
            deadline,
            maximum=_CODEX_HOOK_TRUST_PREFLIGHT_TIMEOUT_SECONDS,
        )
        from agency_runtime.core.codex_hook_trust import (
            sanitize_codex_hook_trust_report,
        )

        if timeout <= 0:
            trust = sanitize_codex_hook_trust_report(None)
        else:
            inspector = self.hook_trust_inspector
            if inspector is None:
                from agency_runtime.core.codex_hook_trust import inspect_codex_hook_trust

                inspector = inspect_codex_hook_trust
            try:
                candidate = inspector(
                    Path(workdir),
                    executable=self.executable,
                    timeout=timeout,
                    environ=env,
                )
                trust = sanitize_codex_hook_trust_report(candidate)
            except Exception:
                trust = sanitize_codex_hook_trust_report(None)
        from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS

        expected_count = len(CODEX_HOOK_EVENTS)
        trust_ready = (
            trust.get("status") == "trusted"
            and trust.get("expected_count") == expected_count
            and trust.get("observed_count") == expected_count
            and trust.get("trusted_count") == expected_count
            and isinstance(trust.get("events"), Mapping)
            and len(trust["events"]) == expected_count
            and all(
                trust.get(field) == 0
                for field in (
                    "managed_count",
                    "modified_count",
                    "untrusted_count",
                    "disabled_count",
                    "missing_count",
                    "unexpected_count",
                    "duplicate_count",
                    "warning_count",
                    "error_count",
                )
            )
        )
        if trust_ready:
            return None
        return {
            "backend": "codex",
            "profile_scope": self.profile_scope,
            "status": "failed",
            "exit_code": 1,
            "stdout_truncated": False,
            "stderr_truncated": False,
            "failure_reason": "codex_hook_trust_not_ready",
            "hook_trust": trust,
            "model_invocation_attempted": False,
        }

    def _record_trust_mode(
        self,
        record: dict[str, Any],
        *,
        invocation_attempted: bool,
    ) -> dict[str, Any]:
        """Record the authority actually carried by the Codex exec invocation."""

        options = self._exec_options()
        bypass_configured = "--dangerously-bypass-hook-trust" in options
        if self.trust_mode == "autonomous_bypass" and not bypass_configured:
            raise ValueError("autonomous Codex hook bypass is missing from the invocation")
        bypass_used = bool(invocation_attempted and bypass_configured)
        record.update(
            trust_mode="autonomous_bypass" if bypass_used else self.trust_mode,
            trust_bypass_used=bypass_used,
            persistent_trust_changed=False,
        )
        return record

    def _install_plugin(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float | None = None,
    ) -> dict[str, Any] | None:
        facade = _facade()
        if deadline is None:
            deadline = facade.time.monotonic() + self.timeout
        setup_commands = (
            [
                self.executable,
                "plugin",
                "marketplace",
                "add",
                str(self.marketplace),
                "--json",
            ],
            [
                self.executable,
                "plugin",
                "add",
                "agency-preflight@agency-runtime",
                "--json",
            ],
        )
        for argv in setup_commands:
            timeout = facade._remaining_canary_timeout(deadline, maximum=30.0)
            if timeout <= 0:
                return _timeout_record("codex")
            setup = self.process_runner(
                argv,
                timeout=timeout,
                cwd=workdir,
                env=env,
                max_output_chars=64 * 1024,
            )
            if not facade._process_succeeded(setup):
                return {
                    "backend": "codex",
                    "status": "failed",
                    "exit_code": setup.returncode or 1,
                }
        return None

    def _verify_plugin(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float | None = None,
    ) -> dict[str, Any] | None:
        facade = _facade()
        if deadline is None:
            deadline = facade.time.monotonic() + self.timeout
        timeout = facade._remaining_canary_timeout(deadline, maximum=30.0)
        if timeout <= 0:
            return _timeout_record("codex")
        inventory = self.process_runner(
            [
                self.executable,
                "plugin",
                "list",
                "--marketplace",
                "agency-runtime",
                "--json",
            ],
            timeout=timeout,
            cwd=workdir,
            env=env,
            max_output_chars=64 * 1024,
        )
        try:
            payload = facade._load_canary_json(
                inventory.stdout,
                maximum_bytes=64 * 1024,
            )
        except (TypeError, ValueError):
            payload = None
        if facade._process_succeeded(inventory) and facade._codex_isolated_plugin_enabled(payload):
            return None
        return {
            "backend": "codex",
            "status": "failed",
            "exit_code": inventory.returncode or 1,
            "profile_scope": "isolated-profile",
            "isolated_plugin": {
                "registered": False,
                "enabled": None,
            },
        }

    def execute(
        self,
        *,
        task: str,
        workdir: str,
        check: bool = False,
    ) -> dict[str, Any]:
        del check
        facade = _facade()
        if self.rollout_contract not in _CODEX_ROLLOUT_CONTRACTS:
            raise ValueError("unsupported Codex rollout contract")
        if self.rollout_contract == "product" and not self.require_exact_activation_rollout:
            raise ValueError("product rollout contract requires exact rollout evidence")
        deadline = facade.time.monotonic() + self.timeout
        if self.profile_scope == "current-profile":
            from agency_runtime.core.cli_transport import safe_cli_environment

            env = safe_cli_environment(self.source_env)
            env["AGENCY_DB_PATH"] = str(self.db_path.resolve())
            env["AGENCY_CANARY_MODE"] = "1"
            env["AGENCY_CANARY_MASTER_ENABLED"] = "1" if self.master_enabled else "0"
            self._configure_canary_environment(env)
            trust_failure = self._verify_current_profile_hook_trust(
                workdir=workdir,
                env=env,
                deadline=deadline,
            )
            if trust_failure is not None:
                return self._record_trust_mode(trust_failure, invocation_attempted=False)
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return self._record_trust_mode(
                    _timeout_record("codex", profile_scope=self.profile_scope),
                    invocation_attempted=False,
                )
            rollout_not_before = (
                facade.time.time() if self.require_exact_activation_rollout else None
            )
            result = self.process_runner(
                [
                    self.executable,
                    "exec",
                    *self._exec_options(),
                ],
                timeout=timeout,
                cwd=workdir,
                env=env,
                input_text=task,
                max_output_chars=256_000,
            )
            return self._record_trust_mode(
                facade._codex_canary_record(
                    result,
                    profile_scope=self.profile_scope,
                    rollout_root=(
                        self.auth_source.parent / "sessions"
                        if self.require_exact_activation_rollout
                        else None
                    ),
                    rollout_not_before=rollout_not_before,
                    rollout_not_after=(
                        facade.time.time() if self.require_exact_activation_rollout else None
                    ),
                    rollout_contract=self.rollout_contract,
                ),
                invocation_attempted=True,
            )
        with private_temporary_directory(prefix="codex-home") as runtime_home:
            codex_home = facade._prepare_private_host_home(
                runtime_home,
                directory_name="codex",
                auth_source=self.auth_source,
                auth_name="auth.json",
                host="Codex",
            )
            workspace_trust: dict[str, Any] | None = None
            if self.trusted_workdir:
                expected_workdir = Path(self.trusted_workdir).expanduser().resolve(strict=True)
                actual_workdir = Path(workdir).expanduser().resolve(strict=True)
                if expected_workdir != actual_workdir:
                    raise ValueError("isolated Codex invocation changed its trusted workspace")
                workspace_trust = facade._project_isolated_codex_workspace_trust(
                    codex_home,
                    workdir=str(actual_workdir),
                )
            env = facade._isolated_canary_environment(
                self.source_env,
                runtime_home,
                self.db_path,
            )
            self._configure_canary_environment(env)
            projected = facade._project_isolated_runtime_control(
                runtime_home,
                enabled=self.master_enabled,
            )
            env["AGENCY_CANARY_MASTER_ENABLED"] = "1" if projected["enabled"] else "0"
            env["CODEX_HOME"] = str(codex_home)
            failure = self._install_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is None:
                failure = self._verify_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is not None:
                if workspace_trust is not None:
                    failure["workspace_trust"] = workspace_trust
                return self._record_trust_mode(failure, invocation_attempted=False)
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return self._record_trust_mode(
                    _timeout_record("codex"),
                    invocation_attempted=False,
                )
            rollout_not_before = (
                facade.time.time() if self.require_exact_activation_rollout else None
            )
            result = self.process_runner(
                [
                    self.executable,
                    "exec",
                    *self._exec_options(),
                ],
                timeout=timeout,
                cwd=workdir,
                env=env,
                input_text=task,
                max_output_chars=256_000,
            )
            record = facade._codex_canary_record(
                result,
                rollout_root=(
                    codex_home / "sessions" if self.require_exact_activation_rollout else None
                ),
                rollout_not_before=rollout_not_before,
                rollout_not_after=(
                    facade.time.time() if self.require_exact_activation_rollout else None
                ),
                rollout_contract=self.rollout_contract,
            )
            if workspace_trust is not None:
                record["workspace_trust"] = workspace_trust
            return self._record_trust_mode(record, invocation_attempted=True)


@dataclass(frozen=True, slots=True)
class SafeClaudeCanaryBackend:
    executable: str
    db_path: Path
    timeout: float
    plugin_dir: Path
    auth_source: Path
    process_runner: Callable[..., Any]
    source_env: Mapping[str, str]
    master_enabled: bool = True

    def execute(
        self,
        *,
        task: str,
        workdir: str,
        check: bool = False,
    ) -> dict[str, Any]:
        del check
        facade = _facade()
        deadline = facade.time.monotonic() + self.timeout
        with private_temporary_directory(prefix="claude-home") as runtime_home:
            claude_home = facade._prepare_private_host_home(
                runtime_home,
                directory_name="claude",
                auth_source=self.auth_source,
                auth_name=".credentials.json",
                host="Claude",
            )
            env = facade._isolated_canary_environment(
                self.source_env,
                runtime_home,
                self.db_path,
            )
            projected = facade._project_isolated_runtime_control(
                runtime_home,
                enabled=self.master_enabled,
            )
            env["AGENCY_CANARY_MASTER_ENABLED"] = "1" if projected["enabled"] else "0"
            env["CLAUDE_CONFIG_DIR"] = str(claude_home)
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return _timeout_record("claude")
            result = self.process_runner(
                [
                    self.executable,
                    "-p",
                    "--output-format",
                    "json",
                    "--max-turns",
                    "1",
                    "--no-session-persistence",
                    "--setting-sources",
                    "",
                    "--plugin-dir",
                    str(self.plugin_dir),
                    "--tools",
                    "",
                    "--disallowedTools",
                    "mcp__*",
                    "--strict-mcp-config",
                    "--permission-mode",
                    "dontAsk",
                ],
                timeout=timeout,
                cwd=workdir,
                env=env,
                input_text=task,
                max_output_chars=256_000,
            )
        return facade._claude_canary_record(result)


def managed_target(native: Mapping[str, Any] | None, *, error: str) -> Path:
    target = str((native or {}).get("managed_target") or "").strip()
    if not target:
        raise ValueError(error)
    return Path(target)


def codex_marketplace(native: Mapping[str, Any] | None) -> Path:
    error = "managed Codex marketplace is unavailable"
    marketplace = _facade()._managed_target(native, error=error)
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    if not marketplace.is_dir() or not manifest.is_file():
        raise ValueError(error)
    return marketplace


def claude_plugin_dir(native: Mapping[str, Any] | None) -> Path:
    error = "managed Claude plugin is unavailable"
    marketplace = _facade()._managed_target(native, error=error)
    plugin_dir = marketplace / "plugins" / "agency-preflight"
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_dir.is_dir() or not manifest.is_file():
        raise ValueError(error)
    return plugin_dir


def source_home(source_env: Mapping[str, str]) -> Path:
    return Path(source_env.get("USERPROFILE") or source_env.get("HOME") or Path.home()).expanduser()


def backend(
    host: str,
    *,
    db_path: Path,
    timeout: float,
    native: Mapping[str, Any] | None,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any] | None,
    environ: Mapping[str, str] | None,
    master_enabled: bool = True,
    profile_scope: str = "isolated-profile",
    require_existing_store: bool = False,
    require_exact_activation_rollout: bool = False,
    hook_trust_inspector: Callable[..., Mapping[str, Any]] | None = None,
    trust_mode: str = "attended",
) -> SafeCodexCanaryBackend | SafeClaudeCanaryBackend:
    from agency_runtime.core.delegation.backends import run_bounded_process

    facade = _facade()
    if host not in facade.SAFE_CANARY_HOSTS:
        raise ValueError(f"{host} has no proven safe noninteractive canary mode")
    timeout = facade._validated_timeout(timeout)
    executable = resolver(host)
    if not executable:
        raise ValueError(f"{host} executable is unavailable")
    if profile_scope not in {"isolated-profile", "current-profile"}:
        raise ValueError(f"unsupported canary profile scope: {profile_scope}")
    if profile_scope == "current-profile" and host != "codex":
        raise ValueError("current-profile canaries support Codex only")
    if not isinstance(trust_mode, str) or trust_mode not in facade.CANARY_TRUST_MODES:
        raise ValueError(f"unsupported canary trust mode: {trust_mode}")
    if trust_mode == "autonomous_bypass" and (
        host != "codex" or profile_scope != "current-profile"
    ):
        raise ValueError("autonomous bypass canaries support Codex current-profile only")
    if type(require_existing_store) is not bool:
        raise TypeError("require_existing_store must be a boolean")
    if require_existing_store and (host != "codex" or profile_scope != "current-profile"):
        raise ValueError("existing-store canaries support Codex current-profile only")
    if type(require_exact_activation_rollout) is not bool:
        raise TypeError("require_exact_activation_rollout must be a boolean")
    if require_exact_activation_rollout and host != "codex":
        raise ValueError("exact activation rollouts support Codex only")
    process_runner = runner or run_bounded_process
    source_env = facade.os.environ if environ is None else environ
    home = facade._source_home(source_env)
    if host == "codex":
        original_home = Path(source_env.get("CODEX_HOME") or (home / ".codex")).expanduser()
        return SafeCodexCanaryBackend(
            executable=executable,
            db_path=db_path,
            timeout=timeout,
            marketplace=facade._codex_marketplace(native),
            auth_source=original_home / "auth.json",
            process_runner=process_runner,
            source_env=source_env,
            master_enabled=master_enabled,
            profile_scope=profile_scope,
            require_existing_store=require_existing_store,
            require_exact_activation_rollout=require_exact_activation_rollout,
            hook_trust_inspector=hook_trust_inspector,
            trust_mode=trust_mode,
        )

    original_home = Path(source_env.get("CLAUDE_CONFIG_DIR") or (home / ".claude")).expanduser()
    return SafeClaudeCanaryBackend(
        executable=executable,
        db_path=db_path,
        timeout=timeout,
        plugin_dir=facade._claude_plugin_dir(native),
        auth_source=original_home / ".credentials.json",
        process_runner=process_runner,
        source_env=source_env,
        master_enabled=master_enabled,
    )


__all__ = [
    "SafeClaudeCanaryBackend",
    "SafeCodexCanaryBackend",
    "backend",
    "claude_canary_record",
    "claude_plugin_dir",
    "codex_canary_record",
    "codex_collaboration_evidence",
    "codex_isolated_plugin_enabled",
    "codex_marketplace",
    "codex_output",
    "copy_bounded_auth",
    "isolated_canary_environment",
    "managed_target",
    "prepare_private_host_home",
    "process_succeeded",
    "project_isolated_codex_workspace_trust",
    "project_isolated_runtime_control",
    "remaining_timeout",
    "source_home",
]
