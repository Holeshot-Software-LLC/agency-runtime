"""Read-only, fail-closed inspection of Codex hook trust state.

The Codex app-server protocol is interactive.  The public inspector therefore
starts a tiny isolated worker under the runtime's owned-process boundary.  The
worker keeps app-server stdin open through ``initialize`` and ``hooks/list``,
then projects the response down to non-secret trust metadata before returning
anything to the parent process.
"""

from __future__ import annotations

import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, BinaryIO

_AGENCY_CODEX_PLUGIN_ID = "agency-preflight@agency-runtime"
_MAX_INSPECTION_SECONDS = 30.0
_MAX_WORKER_PAYLOAD_BYTES = 16 * 1024
_MAX_WORKER_OUTPUT_CHARS = 64 * 1024
_MAX_SERVER_LINE_CHARS = 1024 * 1024
_MAX_SERVER_OUTPUT_CHARS = 2 * 1024 * 1024
_MAX_SERVER_LINES = 5_000
_MAX_HOOK_ENTRIES = 256
_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_EVENT_PATTERN = re.compile(r"[a-z][A-Za-z0-9]{0,63}\Z")
_TRUST_STATUSES = frozenset({"managed", "modified", "trusted", "untrusted"})
_REPORT_STATUSES = frozenset({"disabled", "error", "missing", "modified", "trusted", "untrusted"})
_COUNT_FIELDS = (
    "expected_count",
    "observed_count",
    "trusted_count",
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
_ERROR_CODES = frozenset(
    {
        "app_server_error",
        "app_server_exited",
        "app_server_launch_failed",
        "app_server_output_invalid",
        "app_server_output_limit",
        "app_server_timeout",
        "cwd_mismatch",
        "hook_metadata_invalid",
        "inspection_failed",
        "inspection_output_invalid",
        "inspection_output_truncated",
        "inspection_timed_out",
        "response_scope_invalid",
        "worker_input_invalid",
    }
)


def _base_report(expected_count: int, *, error: str | None = None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "error" if error else "missing",
        "expected_count": expected_count,
        "observed_count": 0,
        "trusted_count": 0,
        "managed_count": 0,
        "modified_count": 0,
        "untrusted_count": 0,
        "disabled_count": 0,
        "missing_count": expected_count,
        "unexpected_count": 0,
        "duplicate_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "events": {},
    }
    if error:
        report["error"] = error
    return report


def _same_path(left: str, right: str) -> bool:
    try:
        left_path = str(Path(left).resolve(strict=False))
        right_path = str(Path(right).resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return False
    if os.name == "nt":
        return left_path.casefold() == right_path.casefold()
    return left_path == right_path


def _response_scope(
    result: object,
    *,
    cwd: str,
    expected_count: int,
) -> tuple[dict[str, Any], list[object]] | dict[str, Any]:
    if not isinstance(result, Mapping):
        return _base_report(expected_count, error="response_scope_invalid")
    data = result.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], Mapping):
        return _base_report(expected_count, error="response_scope_invalid")
    entry = data[0]
    observed_cwd = entry.get("cwd")
    if not isinstance(observed_cwd, str) or not _same_path(observed_cwd, cwd):
        return _base_report(expected_count, error="cwd_mismatch")
    warnings = entry.get("warnings")
    errors = entry.get("errors")
    hooks = entry.get("hooks")
    if (
        not isinstance(warnings, list)
        or not isinstance(errors, list)
        or not isinstance(hooks, list)
    ):
        return _base_report(expected_count, error="response_scope_invalid")
    if len(hooks) > _MAX_HOOK_ENTRIES:
        return _base_report(expected_count, error="app_server_output_limit")
    report = _base_report(expected_count)
    report["warning_count"] = len(warnings)
    report["error_count"] = len(errors)
    return report, hooks


def _select_plugin_hooks(
    hooks: Sequence[object],
    *,
    plugin_id: str,
) -> list[Mapping[str, Any]] | None:
    selected: list[Mapping[str, Any]] = []
    for hook in hooks:
        if not isinstance(hook, Mapping):
            return None
        candidate_plugin = hook.get("pluginId")
        if candidate_plugin is not None and not isinstance(candidate_plugin, str):
            return None
        if candidate_plugin == plugin_id:
            selected.append(hook)
    return selected


def _project_hook_metadata(
    selected: Sequence[Mapping[str, Any]],
    *,
    expected: tuple[str, ...],
    report: dict[str, Any],
) -> tuple[dict[str, int], dict[str, dict[str, Any]]] | None:
    counts: dict[str, int] = {}
    projected: dict[str, dict[str, Any]] = {}
    expected_set = frozenset(expected)
    for hook in selected:
        event = hook.get("eventName")
        enabled = hook.get("enabled")
        trust = hook.get("trustStatus")
        current_hash = hook.get("currentHash")
        if (
            not isinstance(event, str)
            or not _EVENT_PATTERN.fullmatch(event)
            or not isinstance(enabled, bool)
            or not isinstance(trust, str)
            or trust not in _TRUST_STATUSES
            or not isinstance(current_hash, str)
            or not _HASH_PATTERN.fullmatch(current_hash)
            or hook.get("source") != "plugin"
            or hook.get("handlerType") != "command"
            or hook.get("isManaged") is not False
        ):
            return None
        counts[event] = counts.get(event, 0) + 1
        if event in expected_set and event not in projected:
            projected[event] = {
                "enabled": enabled,
                "trustStatus": trust,
                "currentHash": current_hash,
            }
        report[f"{trust}_count"] += 1
        if not enabled:
            report["disabled_count"] += 1
    return counts, projected


def _project_hooks_response(
    result: object,
    *,
    cwd: str,
    expected_events: Sequence[str],
    plugin_id: str,
) -> dict[str, Any]:
    """Project one app-server response to bounded, non-command evidence."""

    expected = tuple(expected_events)
    scope = _response_scope(result, cwd=cwd, expected_count=len(expected))
    if isinstance(scope, dict):
        return scope
    report, hooks = scope
    selected = _select_plugin_hooks(hooks, plugin_id=plugin_id)
    if selected is None:
        return _base_report(len(expected), error="hook_metadata_invalid")

    report["observed_count"] = len(selected)
    metadata = _project_hook_metadata(selected, expected=expected, report=report)
    if metadata is None:
        return _base_report(len(expected), error="hook_metadata_invalid")
    counts, projected = metadata
    expected_set = frozenset(expected)

    report["events"] = {event: projected[event] for event in expected if event in projected}
    report["missing_count"] = sum(1 for event in expected if counts.get(event, 0) == 0)
    report["unexpected_count"] = sum(
        count for event, count in counts.items() if event not in expected_set
    )
    report["duplicate_count"] = sum(max(0, counts.get(event, 0) - 1) for event in expected)

    if (
        report["warning_count"]
        or report["error_count"]
        or report["unexpected_count"]
        or report["duplicate_count"]
    ):
        report["status"] = "error"
        report["error"] = "hook_metadata_invalid"
    elif report["missing_count"]:
        report["status"] = "missing"
    elif report["disabled_count"]:
        report["status"] = "disabled"
    elif report["modified_count"]:
        report["status"] = "modified"
    elif report["untrusted_count"]:
        report["status"] = "untrusted"
    elif report["managed_count"]:
        report["status"] = "error"
        report["error"] = "hook_metadata_invalid"
    elif report["trusted_count"] == len(expected):
        report["status"] = "trusted"
    else:
        report["status"] = "error"
        report["error"] = "hook_metadata_invalid"
    return report


def _validate_report_shape(
    value: object,
    expected_events: Sequence[str],
) -> tuple[Mapping[str, Any], Mapping[str, Mapping[str, Any]]] | None:
    if not isinstance(value, Mapping):
        return None
    allowed = {"status", "events", "error", *_COUNT_FIELDS}
    if set(value) - allowed:
        return None
    status_value = value.get("status")
    if not isinstance(status_value, str) or status_value not in _REPORT_STATUSES:
        return None
    for field in _COUNT_FIELDS:
        count = value.get(field)
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or not 0 <= count <= _MAX_HOOK_ENTRIES
        ):
            return None
    if value.get("expected_count") != len(expected_events):
        return None
    error = value.get("error")
    if error is not None and (not isinstance(error, str) or error not in _ERROR_CODES):
        return None
    events = value.get("events")
    if not isinstance(events, Mapping) or set(events) - set(expected_events):
        return None
    for event, metadata in events.items():
        if not isinstance(event, str) or not isinstance(metadata, Mapping):
            return None
        if set(metadata) != {"enabled", "trustStatus", "currentHash"}:
            return None
        if not isinstance(metadata.get("enabled"), bool):
            return None
        trust_status = metadata.get("trustStatus")
        if not isinstance(trust_status, str) or trust_status not in _TRUST_STATUSES:
            return None
        current_hash = metadata.get("currentHash")
        if not isinstance(current_hash, str) or not _HASH_PATTERN.fullmatch(current_hash):
            return None
    return value, events


def _report_counts_are_consistent(
    value: Mapping[str, Any],
    events: Mapping[str, Mapping[str, Any]],
    expected_events: Sequence[str],
) -> bool:
    observed_count = value["observed_count"]
    if (
        value["trusted_count"]
        + value["managed_count"]
        + value["modified_count"]
        + value["untrusted_count"]
        != observed_count
    ):
        return False
    if value["missing_count"] != len(expected_events) - len(events):
        return False
    if observed_count != len(events) + value["unexpected_count"] + value["duplicate_count"]:
        return False
    return value["disabled_count"] <= observed_count


def _report_status_is_consistent(
    value: Mapping[str, Any],
    events: Mapping[str, Mapping[str, Any]],
    expected_events: Sequence[str],
) -> bool:
    error = value.get("error")
    status = value["status"]
    observed_count = value["observed_count"]
    structural_error = bool(
        value["warning_count"]
        or value["error_count"]
        or value["unexpected_count"]
        or value["duplicate_count"]
        or value["managed_count"]
    )
    if status == "error":
        if error is None:
            return False
    elif error is not None or structural_error:
        return False
    if status != "error":
        event_values = tuple(events.values())
        if value["trusted_count"] != sum(
            metadata["trustStatus"] == "trusted" for metadata in event_values
        ):
            return False
        if value["modified_count"] != sum(
            metadata["trustStatus"] == "modified" for metadata in event_values
        ):
            return False
        if value["untrusted_count"] != sum(
            metadata["trustStatus"] == "untrusted" for metadata in event_values
        ):
            return False
        if value["disabled_count"] != sum(not metadata["enabled"] for metadata in event_values):
            return False
    if status == "trusted" and not (
        set(events) == set(expected_events)
        and observed_count == len(expected_events)
        and value["trusted_count"] == len(expected_events)
        and all(metadata["enabled"] for metadata in events.values())
        and not any(value[field] for field in _COUNT_FIELDS[3:])
    ):
        return False
    if status == "missing" and not value["missing_count"]:
        return False
    if status == "disabled" and (value["missing_count"] or not value["disabled_count"]):
        return False
    if status == "modified" and (
        value["missing_count"] or value["disabled_count"] or not value["modified_count"]
    ):
        return False
    return status != "untrusted" or not (
        value["missing_count"]
        or value["disabled_count"]
        or value["modified_count"]
        or not value["untrusted_count"]
    )


def _validate_report(value: object, expected_events: Sequence[str]) -> dict[str, Any] | None:
    shaped = _validate_report_shape(value, expected_events)
    if shaped is None:
        return None
    report, events = shaped
    if not _report_counts_are_consistent(report, events, expected_events):
        return None
    if not _report_status_is_consistent(report, events, expected_events):
        return None
    return dict(report)


def _read_stdout(stream: BinaryIO, messages: queue.Queue[tuple[str, bytes]]) -> None:
    total = 0
    lines = 0
    try:
        while True:
            line = stream.readline(_MAX_SERVER_LINE_CHARS + 1)
            if line == b"":
                messages.put(("eof", b""))
                return
            lines += 1
            total += len(line)
            if (
                len(line) > _MAX_SERVER_LINE_CHARS
                or total > _MAX_SERVER_OUTPUT_CHARS
                or lines > _MAX_SERVER_LINES
            ):
                messages.put(("limit", b""))
                return
            messages.put(("line", line))
    except Exception:
        messages.put(("error", b""))


def _discard_stream(stream: BinaryIO) -> None:
    try:
        while stream.read(8192):
            pass
    except Exception:
        return


def _send_message(stream: BinaryIO, value: Mapping[str, Any]) -> None:
    stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    stream.write(b"\n")
    stream.flush()


def _await_response(
    messages: queue.Queue[tuple[str, bytes]],
    *,
    request_id: int,
    deadline: float,
) -> Mapping[str, Any]:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        try:
            kind, content = messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise TimeoutError from exc
        if kind == "limit":
            raise OverflowError
        if kind in {"eof", "error"}:
            raise EOFError
        from agency_runtime.core.bounded_json import safe_load_bounded_json

        try:
            message = safe_load_bounded_json(
                content,
                maximum_bytes=_MAX_SERVER_LINE_CHARS,
                maximum_depth=16,
                maximum_nodes=2_048,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid app-server output") from exc
        if not isinstance(message, Mapping):
            raise ValueError("invalid app-server output")
        if "id" not in message:
            continue
        message_id = message["id"]
        if isinstance(message_id, bool) or not isinstance(message_id, int):
            raise ValueError("invalid app-server response id")
        if message_id != request_id:
            raise ValueError("unexpected app-server response id")
        if "error" in message:
            raise RuntimeError("app-server request failed")
        result = message.get("result")
        if not isinstance(result, Mapping):
            raise ValueError("invalid app-server response")
        return result


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.stdin is not None:
        with suppress(OSError):
            process.stdin.close()
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=0.5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                pass
    for stream in (process.stdout, process.stderr):
        if stream is not None:
            with suppress(OSError):
                stream.close()


def _run_worker(payload: Mapping[str, Any]) -> dict[str, Any]:
    executable = payload.get("executable")
    cwd = payload.get("cwd")
    expected = payload.get("expected_events")
    plugin_id = payload.get("plugin_id")
    timeout = payload.get("timeout")
    if (
        not isinstance(executable, str)
        or not executable
        or "\x00" in executable
        or not isinstance(cwd, str)
        or not Path(cwd).is_absolute()
        or not isinstance(expected, list)
        or not expected
        or len(expected) > 32
        or len(set(expected)) != len(expected)
        or any(
            not isinstance(event, str) or not _EVENT_PATTERN.fullmatch(event) for event in expected
        )
        or plugin_id != _AGENCY_CODEX_PLUGIN_ID
        or isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or not 0 < timeout <= _MAX_INSPECTION_SECONDS
    ):
        return _base_report(
            len(expected) if isinstance(expected, list) else 0, error="worker_input_invalid"
        )

    from agency_runtime.core.process_argv import (
        freeze_process_argv,
        prepare_process_argv,
        repository_forbidden_roots,
    )

    try:
        forbidden_roots = repository_forbidden_roots(Path(cwd))
        argv = freeze_process_argv(
            prepare_process_argv(
                [executable, "app-server", "--stdio"],
                current_directory=cwd,
                forbidden_roots=forbidden_roots,
            ),
            forbidden_roots=forbidden_roots,
        )
        argv.revalidate()
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=dict(os.environ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            shell=False,
        )
    except (OSError, ValueError):
        return _base_report(len(expected), error="app_server_launch_failed")
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    messages: queue.Queue[tuple[str, bytes]] = queue.Queue(maxsize=128)
    stdout_thread = threading.Thread(
        target=_read_stdout,
        args=(process.stdout, messages),
        daemon=True,
    )
    stderr_thread = threading.Thread(target=_discard_stream, args=(process.stderr,), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    deadline = time.monotonic() + float(timeout)
    try:
        _send_message(
            process.stdin,
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "agency-runtime-hook-trust",
                        "title": "Agency Runtime hook trust inspector",
                        "version": "1",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            },
        )
        _await_response(messages, request_id=1, deadline=deadline)
        _send_message(process.stdin, {"method": "initialized"})
        _send_message(
            process.stdin,
            {"id": 2, "method": "hooks/list", "params": {"cwds": [cwd]}},
        )
        result = _await_response(messages, request_id=2, deadline=deadline)
        return _project_hooks_response(
            result,
            cwd=cwd,
            expected_events=expected,
            plugin_id=plugin_id,
        )
    except TimeoutError:
        return _base_report(len(expected), error="app_server_timeout")
    except OverflowError:
        return _base_report(len(expected), error="app_server_output_limit")
    except EOFError:
        return _base_report(len(expected), error="app_server_exited")
    except RuntimeError:
        return _base_report(len(expected), error="app_server_error")
    except (OSError, TypeError, ValueError):
        return _base_report(len(expected), error="app_server_output_invalid")
    finally:
        _stop_process(process)
        stdout_thread.join(timeout=0.5)
        stderr_thread.join(timeout=0.5)


def _worker_entry() -> int:
    try:
        from agency_runtime.core.bounded_json import safe_load_bounded_json

        encoded = sys.stdin.buffer.read(_MAX_WORKER_PAYLOAD_BYTES + 1)
        payload = safe_load_bounded_json(
            encoded,
            maximum_bytes=_MAX_WORKER_PAYLOAD_BYTES,
            maximum_depth=8,
            maximum_nodes=256,
        )
        if not isinstance(payload, Mapping):
            raise ValueError("invalid worker payload")
        report = _run_worker(payload)
    except Exception:
        report = _base_report(0, error="worker_input_invalid")
    sys.stdout.write(json.dumps(report, separators=(",", ":"), ensure_ascii=True))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def _validated_inspection_target(
    cwd: Path,
    *,
    executable: str,
    timeout: float,
) -> tuple[Path, float]:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a finite value greater than zero and at most 30 seconds")
    timeout_value = float(timeout)
    if not math.isfinite(timeout_value) or not 0 < timeout_value <= _MAX_INSPECTION_SECONDS:
        raise ValueError("timeout must be a finite value greater than zero and at most 30 seconds")
    if not isinstance(executable, str) or not executable or "\x00" in executable:
        raise ValueError("executable must be non-empty text without NUL bytes")
    if not isinstance(cwd, Path):
        raise TypeError("cwd must be a pathlib.Path")
    try:
        resolved_cwd = cwd.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("cwd must be an existing directory") from exc
    if not resolved_cwd.is_dir():
        raise ValueError("cwd must be an existing directory")
    return resolved_cwd, timeout_value


def inspect_codex_hook_trust(
    cwd: Path,
    *,
    executable: str = "codex",
    timeout: float = 10.0,
    environ: Mapping[str, str] | None = None,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Return sanitized trust evidence for the canonical Agency Codex hooks."""

    resolved_cwd, timeout_value = _validated_inspection_target(
        cwd,
        executable=executable,
        timeout=timeout,
    )

    from agency_runtime.core.bounded_json import safe_load_bounded_json
    from agency_runtime.core.cli_transport import safe_cli_environment
    from agency_runtime.core.delegation.backends import run_bounded_process
    from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
    from agency_runtime.core.process_argv import (
        PreparedProcessArgv,
        freeze_persistent_process_argv,
        isolated_python_argv,
    )

    expected_events = tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)
    safe_environment = safe_cli_environment(environ, current_directory=resolved_cwd)
    inner_timeout = max(0.1, timeout_value - min(1.0, timeout_value / 5.0))
    input_text = json.dumps(
        {
            "executable": executable,
            "cwd": str(resolved_cwd),
            "expected_events": list(expected_events),
            "plugin_id": _AGENCY_CODEX_PLUGIN_ID,
            "timeout": inner_timeout,
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if len(input_text.encode("utf-8")) > _MAX_WORKER_PAYLOAD_BYTES:
        raise ValueError("worker payload exceeds the safety limit")
    worker_values = isolated_python_argv(
        sys.executable,
        "agency_runtime.core.codex_hook_trust",
        "--worker",
    )
    worker_argv = PreparedProcessArgv(
        worker_values,
        artifact_paths=(worker_values[0], worker_values[3]),
    )
    try:
        freeze_persistent_process_argv(worker_argv)
    except (OSError, TypeError, ValueError):
        return _base_report(len(expected_events), error="inspection_failed")
    process_runner = runner or run_bounded_process
    try:
        completed = process_runner(
            worker_argv,
            timeout=timeout_value,
            cwd=str(resolved_cwd),
            env=safe_environment,
            input_text=input_text,
            max_input_bytes=_MAX_WORKER_PAYLOAD_BYTES,
            max_output_chars=_MAX_WORKER_OUTPUT_CHARS,
        )
    except Exception:
        return _base_report(len(expected_events), error="inspection_failed")
    if getattr(completed, "timed_out", False):
        return _base_report(len(expected_events), error="inspection_timed_out")
    if getattr(completed, "stdout_truncated", False) or getattr(
        completed, "stderr_truncated", False
    ):
        return _base_report(len(expected_events), error="inspection_output_truncated")
    if getattr(completed, "returncode", 1) != 0:
        return _base_report(len(expected_events), error="inspection_failed")
    stdout = getattr(completed, "stdout", None)
    if not isinstance(stdout, str):
        return _base_report(len(expected_events), error="inspection_output_invalid")
    try:
        decoded = safe_load_bounded_json(
            stdout,
            maximum_bytes=_MAX_WORKER_OUTPUT_CHARS,
            maximum_depth=8,
            maximum_nodes=512,
        )
    except (TypeError, ValueError):
        return _base_report(len(expected_events), error="inspection_output_invalid")
    validated = _validate_report(decoded, expected_events)
    if validated is None:
        return _base_report(len(expected_events), error="inspection_output_invalid")
    return validated


def sanitize_codex_hook_trust_report(value: object) -> dict[str, Any]:
    """Allowlist a trust report before it crosses the canary evidence boundary."""

    from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS

    expected_events = tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)
    validated = _validate_report(value, expected_events)
    if validated is None:
        return _base_report(len(expected_events), error="inspection_output_invalid")
    return validated


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        raise SystemExit(_worker_entry())
    raise SystemExit(2)


__all__ = ["inspect_codex_hook_trust", "sanitize_codex_hook_trust_report"]
