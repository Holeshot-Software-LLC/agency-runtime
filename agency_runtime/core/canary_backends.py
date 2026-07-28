"""Credential-isolated, bounded subprocess backends for live host canaries."""

from __future__ import annotations

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
    from agency_runtime.core.unit_assignment import work_unit_goal_hash

    deliveries: dict[tuple[str, ...], dict[str, Any]] = {}
    for event in events:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        texts: list[str] = []
        if event.get("type") == "response_item" and payload.get("type") == "message":
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
                "goal_hash": work_unit_goal_hash(delivery.original_task),
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
    dict[str, dict[str, Any]],
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
            if name not in {"spawn_agent", "wait_agent"}:
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


def _codex_exact_rollout_calls(
    calls: list[dict[str, Any]],
    outputs: dict[str, dict[str, Any]],
    activities: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    """Validate the one-spawn/one-wait native topology."""

    spawn_calls = [call for call in calls if call["name"] == "spawn_agent"]
    wait_calls = [call for call in calls if call["name"] == "wait_agent"]
    if len(spawn_calls) != 1 or len(wait_calls) != 1:
        raise ValueError("Codex rollout did not contain exactly one spawn and one wait")
    spawn = spawn_calls[0]
    wait = wait_calls[0]
    if set(outputs) != {spawn["call_id"], wait["call_id"]}:
        raise ValueError("Codex rollout tool outputs did not match the exact native calls")
    if spawn["index"] >= wait["index"]:
        raise ValueError("Codex wait preceded its spawn")
    spawn_args = spawn["arguments"]
    wait_args = wait["arguments"]
    if (
        set(spawn_args) != {"fork_turns", "message", "task_name"}
        or spawn_args.get("fork_turns") != "none"
        or not isinstance(spawn_args.get("message"), str)
        or not isinstance(spawn_args.get("task_name"), str)
    ):
        raise ValueError("Codex spawn arguments exceeded the canary contract")
    if set(wait_args) != {"timeout_ms"} or wait_args.get("timeout_ms") != 60_000:
        raise ValueError("Codex wait arguments exceeded the canary contract")
    spawn_output = outputs.get(spawn["call_id"])
    wait_output = outputs.get(wait["call_id"])
    if (
        not isinstance(spawn_output, dict)
        or set(spawn_output) != {"task_name"}
        or not isinstance(spawn_output.get("task_name"), str)
        or not isinstance(wait_output, dict)
        or wait_output.get("message") != "Wait completed."
        or wait_output.get("timed_out") is not False
    ):
        raise ValueError("Codex rollout did not prove completed native calls")
    matching_activities = [
        activity
        for activity in activities
        if activity.get("event_id") == spawn["call_id"] and activity.get("kind") == "started"
    ]
    if len(activities) != 1 or len(matching_activities) != 1:
        raise ValueError("Codex rollout did not identify one native child start")
    activity = matching_activities[0]
    receiver_id = _codex_thread_id(activity.get("agent_thread_id"))
    native_task_name = str(spawn_args["task_name"]).strip()
    if (
        not native_task_name
        or len(native_task_name) > 128
        or activity.get("agent_path") != spawn_output["task_name"]
        or not str(spawn_output["task_name"]).endswith(f"/{native_task_name}")
    ):
        raise ValueError("Codex child path did not match the requested native task")
    return spawn, wait, receiver_id, native_task_name


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
    spawn, wait, receiver_id, native_task_name = _codex_exact_rollout_calls(
        calls,
        outputs,
        activities,
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
    if (
        sum(
            event.get("type") == "event_msg"
            and isinstance(event.get("payload"), dict)
            and event["payload"].get("type") == "task_complete"
            for event in child_events
        )
        != 1
    ):
        raise ValueError("Codex child rollout did not prove one completion")
    prompt_delivery = _codex_child_prompt_delivery(
        child_events,
        parent_thread_id=parent_thread_id,
        tool_use_id=spawn["call_id"],
    )
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
            "evidence_source": "persisted_rollout",
        },
        {
            "id": wait["id"],
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
        "wait_count": 1,
        "unexpected_item_types": sorted(set(unexpected.values())),
        "unexpected_item_count": len(unexpected),
        "evidence_source": "persisted_rollout",
    }


def _codex_collaboration_call_projection(
    event: dict[str, Any],
    item: dict[str, Any],
) -> dict[str, Any]:
    """Validate and project one content-free collaboration event."""

    from agency_runtime.core.native_child_prompt_delivery import (
        parse_native_child_prompt_delivery,
    )
    from agency_runtime.core.unit_assignment import work_unit_goal_hash

    item_id = str(item.get("id") or "").strip()
    tool = str(item.get("tool") or "").strip()
    if not item_id or len(item_id) > 256 or tool not in {"spawn_agent", "wait"}:
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
            "goal_hash": work_unit_goal_hash(delivery.original_task),
        }
        if delivery is not None
        else None
    )
    return {
        "id": item_id,
        "event_type": str(event["type"]),
        "tool": tool,
        "sender_thread_id": sender_thread_id,
        "receiver_thread_ids": list(receivers),
        "agents_states": projected_states,
        "status": str(item.get("status") or ""),
        "prompt_delivery": prompt_projection,
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
    return projection


def _merge_codex_rollout_evidence(
    stdout_projection: dict[str, Any],
    rollout_projection: dict[str, Any],
) -> dict[str, Any] | None:
    """Cross-check the lossy JSONL projection against persisted native calls."""

    if (
        stdout_projection["spawn_count"] > rollout_projection["spawn_count"]
        or stdout_projection["wait_count"] > rollout_projection["wait_count"]
    ):
        return None
    ordered = stdout_projection["calls"]
    parent_id = rollout_projection["calls"][0]["sender_thread_id"]
    if any(row.get("sender_thread_id") != parent_id for row in ordered):
        return None
    rollout_calls = {row["tool"]: row for row in rollout_projection["calls"]}
    for row in ordered:
        persisted = rollout_calls.get(row["tool"])
        if persisted is None:
            return None
        if row["receiver_thread_ids"] and (
            row["receiver_thread_ids"] != persisted["receiver_thread_ids"]
        ):
            return None
        if row.get("prompt_delivery") is not None and (
            row["prompt_delivery"] != persisted["prompt_delivery"]
        ):
            return None
    rollout_projection["unexpected_item_types"] = sorted(
        set(stdout_projection["unexpected_item_types"])
        | set(rollout_projection["unexpected_item_types"])
    )
    rollout_projection["unexpected_item_count"] = (
        stdout_projection["unexpected_item_count"] + rollout_projection["unexpected_item_count"]
    )
    return rollout_projection


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
        "wait_count": sum(row["tool"] == "wait" for row in ordered),
        "unexpected_item_types": sorted(set(unexpected_items.values())),
        "unexpected_item_count": len(unexpected_items),
    }
    if rollout_root is None:
        return stdout_projection
    if (
        stdout_projection["spawn_count"] not in {0, 1}
        or stdout_projection["wait_count"] not in {0, 1}
        or len(stdout_projection["calls"])
        != stdout_projection["spawn_count"] + stdout_projection["wait_count"]
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


def _codex_failure_reason(stderr: object) -> str | None:
    """Classify allowlisted Codex failures without retaining raw stderr."""

    if isinstance(stderr, str) and "collab spawn failed: no thread with id:" in stderr:
        return "native_collaboration_full_history_parent_unavailable"
    return None


def codex_canary_record(
    result: Any,
    *,
    profile_scope: str = "isolated-profile",
    rollout_root: Path | None = None,
    rollout_not_before: float | None = None,
    rollout_not_after: float | None = None,
) -> dict[str, Any]:
    facade = _facade()
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
    if failure_reason := _codex_failure_reason(getattr(result, "stderr", "")):
        record["failure_reason"] = failure_reason
    collaboration = codex_collaboration_evidence(
        result.stdout,
        rollout_root=rollout_root,
        rollout_not_before=rollout_not_before,
        rollout_not_after=rollout_not_after,
    )
    output = facade._codex_output(result.stdout) if completed else None
    if completed and output is not None and collaboration is not None:
        record.update(output=output, collaboration=collaboration)
    elif completed:
        record["status"] = "failed"
        if output is None and collaboration is None:
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
    hook_trust_inspector: Callable[..., Mapping[str, Any]] | None = None

    def _exec_options(self) -> tuple[str, ...]:
        if self.exec_options is not None:
            return self.exec_options
        facade = _facade()
        if self.require_exact_activation_rollout:
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

    def _verify_current_profile_hook_trust(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float,
    ) -> dict[str, Any] | None:
        """Fail before a model call unless Codex trusts the exact Agency hooks."""

        if self.profile_scope != "current-profile" or not self.require_exact_activation_rollout:
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
        deadline = facade.time.monotonic() + self.timeout
        if self.profile_scope == "current-profile":
            from agency_runtime.core.cli_transport import safe_cli_environment

            env = safe_cli_environment(self.source_env)
            env["AGENCY_DB_PATH"] = str(self.db_path.resolve())
            env["AGENCY_CANARY_MODE"] = "1"
            env["AGENCY_CANARY_MASTER_ENABLED"] = "1" if self.master_enabled else "0"
            if self.require_existing_store:
                from agency_runtime.core.codex_activation_verification import (
                    CODEX_ACTIVATION_EXISTING_STORE_ENV,
                )

                env[CODEX_ACTIVATION_EXISTING_STORE_ENV] = "1"
            trust_failure = self._verify_current_profile_hook_trust(
                workdir=workdir,
                env=env,
                deadline=deadline,
            )
            if trust_failure is not None:
                return trust_failure
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return _timeout_record("codex", profile_scope=self.profile_scope)
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
            return facade._codex_canary_record(
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
            )
        with private_temporary_directory(prefix="codex-home") as runtime_home:
            codex_home = facade._prepare_private_host_home(
                runtime_home,
                directory_name="codex",
                auth_source=self.auth_source,
                auth_name="auth.json",
                host="Codex",
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
            env["CODEX_HOME"] = str(codex_home)
            failure = self._install_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is None:
                failure = self._verify_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is not None:
                return failure
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return _timeout_record("codex")
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
            return facade._codex_canary_record(
                result,
                rollout_root=(
                    codex_home / "sessions" if self.require_exact_activation_rollout else None
                ),
                rollout_not_before=rollout_not_before,
                rollout_not_after=(
                    facade.time.time() if self.require_exact_activation_rollout else None
                ),
            )


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
    "project_isolated_runtime_control",
    "remaining_timeout",
    "source_home",
]
