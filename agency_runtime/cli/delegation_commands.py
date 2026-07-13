"""Delegation execution and subprocess compatibility commands."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import uuid
from typing import Any

from agency_runtime.core.display import safe_display_token

from ._common import print_json as _print_json
from ._common import store as _store


def _run_command(command: list[str], *, timeout: float | None = None) -> int:
    if not command:
        print("No command supplied", file=sys.stderr)
        return 2
    if any(not isinstance(argument, str) for argument in command):
        print("Command arguments must be strings", file=sys.stderr)
        return 2
    if any("\x00" in argument for argument in command):
        print("Command arguments must not contain NUL bytes", file=sys.stderr)
        return 2
    try:
        proc = subprocess.run(command, text=True, timeout=timeout)
    except FileNotFoundError:
        print(
            f"Command not found: {safe_display_token(command[0])}",
            file=sys.stderr,
        )
        return 127
    except PermissionError:
        print(
            f"Command is not executable: {safe_display_token(command[0])}",
            file=sys.stderr,
        )
        return 126
    except subprocess.TimeoutExpired:
        print("Command timed out", file=sys.stderr)
        return 124
    except OSError as exc:
        print(f"Command failed to start ({type(exc).__name__})", file=sys.stderr)
        return 1
    return int(proc.returncode)


def _emit_delegate_result(
    args: argparse.Namespace, payload: dict[str, Any], *, stderr: str = ""
) -> int:
    if args.json:
        _print_json(payload)
    elif stderr:
        print(stderr, file=sys.stderr)
    elif payload.get("status") == "completed":
        output = payload.get("output")
        if isinstance(output, str) and output:
            print(output)
        elif output is not None:
            _print_json(output)
        print(f"Delegation completed via {payload.get('backend', 'unknown')}.")
    return int(payload.get("exit_code", 1))


def cmd_delegate(args: argparse.Namespace) -> int:
    from agency_runtime.core.delegation.backends import (
        BackendError,
        BackendRegistry,
        ClaudeExecBackend,
        CodexExecBackend,
        GenericCLIBackend,
        HermesDelegateBackend,
        OpenClawAgentBackend,
    )

    backend_name = args.backend
    task = args.task
    agent = args.agent
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        error = "--timeout must be a finite value greater than 0"
        return _emit_delegate_result(
            args,
            {"status": "error", "error": error, "exit_code": 2},
            stderr=error,
        )
    timeout = args.timeout if args.timeout is not None else 3600.0
    factories = {
        "codex": lambda: CodexExecBackend(timeout=timeout),
        "claude": lambda: ClaudeExecBackend(timeout=timeout),
        "hermes": lambda: HermesDelegateBackend(timeout=timeout),
        "openclaw": lambda: OpenClawAgentBackend(timeout=timeout),
        "generic": lambda: GenericCLIBackend(
            command=tuple(args.command or ()),
            timeout=timeout,
        ),
    }
    try:
        candidate = factories[backend_name]()
    except (KeyError, TypeError, ValueError) as exc:
        error = str(exc) or f"invalid backend configuration: {backend_name}"
        return _emit_delegate_result(
            args,
            {"status": "error", "error": error, "exit_code": 2},
            stderr=error,
        )

    store = _store()
    trace_id = f"cli-delegate-{uuid.uuid4()}"
    event_id = store.record_delegation(
        trace_id=trace_id,
        recommended_agent=agent or "",
        status="started",
        backend=backend_name,
    )
    payload = {
        "trace_id": trace_id,
        "event_id": event_id,
        "backend": backend_name,
        "agent": agent,
        "timeout_seconds": timeout,
    }

    try:
        selected = BackendRegistry([candidate]).select_backend(preferred=backend_name)
        result = selected.delegate(
            task=task,
            workdir=args.workdir,
            recommended_agent=agent or None,
        )
    except BackendError as exc:
        result = dict(exc.result)
        if not result:
            result = {
                "backend": backend_name,
                "status": "unavailable",
                "exit_code": 127,
                "error": str(exc),
            }
    except (TypeError, ValueError) as exc:
        result = {
            "backend": backend_name,
            "status": "error",
            "exit_code": 2,
            "error": str(exc),
        }

    status = str(result.get("status") or "failed")
    error = str(result.get("error") or "")
    if status == "completed":
        evidence_status = "completed"
        skip_reason = ""
    elif status in {"unavailable", "timed_out"}:
        evidence_status = "skipped"
        skip_reason = error or status
    else:
        evidence_status = "failed"
        skip_reason = ""
    store.update_delegation(
        event_id,
        status=evidence_status,
        backend=backend_name,
        error=error,
        skip_reason=skip_reason,
    )
    normalized = {**result, **payload, "status": evidence_status}
    if skip_reason:
        normalized["skip_reason"] = skip_reason
    return _emit_delegate_result(
        args, normalized, stderr=error if evidence_status != "completed" else ""
    )


def cmd_codex_exec(args: argparse.Namespace) -> int:
    return _run_command(["codex", "exec", *args.args])


def cmd_run(args: argparse.Namespace) -> int:
    return _run_command(args.args)
