"""Delegation execution and subprocess compatibility commands."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import uuid
from typing import Any

from agency_runtime.core.display import safe_display_token
from agency_runtime.core.windows_acl import require_restricted_windows_token

from ._common import print_json as _print_json
from ._common import store as _store


def _completed_execution_identity(
    result: dict[str, Any],
    *,
    backend: str,
) -> tuple[str, str, str]:
    """Return only process-backed identity for one completed CLI invocation."""

    executable = result.get("executable")
    worker_id = executable.strip() if isinstance(executable, str) else ""
    raw_process_id = result.get("process_id")
    if (
        not worker_id
        or isinstance(raw_process_id, bool)
        or not isinstance(raw_process_id, int)
        or raw_process_id <= 0
    ):
        return "", "", ""
    return "cli-process", worker_id, f"{backend}:process:{raw_process_id}"


def _delegation_candidate_and_store(
    backend_name: str,
    factories: dict[str, Any],
) -> tuple[Any, Any]:
    """Construct execution and evidence boundaries before any backend runs."""

    candidate = factories[backend_name]()
    try:
        evidence_store = _store()
    except Exception as exc:
        require_restricted_windows_token(exc)
        raise ValueError(
            "delegation evidence Store is unavailable from this restricted process; "
            "execution was not started and is never proxied through the dashboard"
        ) from exc
    return candidate, evidence_store


def _complete_cli_evidence_run(
    store: Any,
    *,
    trace_id: str,
    session_id: str,
    status: str,
) -> None:
    """Close and verify the exact synthetic run owned by one CLI invocation."""

    run = store.get_run(trace_id)
    if (
        not isinstance(run, dict)
        or str(run.get("session_id") or "") != session_id
        or not str(run.get("id") or "").strip()
    ):
        raise RuntimeError("CLI delegation parent run correlation could not be verified")
    store.complete_run(str(run["id"]), status=status)
    closed = store.get_run(trace_id)
    if (
        not isinstance(closed, dict)
        or str(closed.get("session_id") or "") != session_id
        or str(closed.get("status") or "") != status
    ):
        raise RuntimeError("CLI delegation parent run did not reach terminal state")


def _persist_cli_terminal_evidence(
    store: Any,
    *,
    event_id: str,
    trace_id: str,
    session_id: str,
    evidence_status: str,
    run_status: str,
    backend: str,
    error: str = "",
    skip_reason: str = "",
    executed_worker_kind: str = "",
    executed_worker_id: str = "",
    native_run_id: str = "",
) -> None:
    """Persist one terminal event and close its exact parent, even if either write fails."""

    update_error: BaseException | None = None
    try:
        store.update_delegation(
            event_id,
            status=evidence_status,
            backend=backend,
            error=error,
            skip_reason=skip_reason,
            executed_worker_kind=executed_worker_kind,
            executed_worker_id=executed_worker_id,
            native_run_id=native_run_id,
        )
    except BaseException as exc:
        update_error = exc
    try:
        _complete_cli_evidence_run(
            store,
            trace_id=trace_id,
            session_id=session_id,
            status=run_status,
        )
    except BaseException as close_error:
        if update_error is not None:
            raise update_error from close_error
        raise
    if update_error is not None:
        raise update_error


def _run_command(
    command: list[str],
    *,
    timeout: float | None = None,
    secure_executable: bool = False,
) -> int:
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
        launch_command = command
        if secure_executable:
            from agency_runtime.core.process_argv import (
                freeze_process_argv,
                prepare_process_argv,
                revalidate_process_argv,
            )

            launch_command = freeze_process_argv(prepare_process_argv(command))
            revalidate_process_argv(launch_command)
        proc = subprocess.run(launch_command, text=True, timeout=timeout)
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
    except (TypeError, ValueError) as exc:
        print(f"Command arguments are invalid ({type(exc).__name__})", file=sys.stderr)
        return 2
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
    elif payload.get("bypassed") is True:
        print("Agency Runtime is globally disabled; delegation was bypassed.")
    elif payload.get("status") == "completed":
        output = payload.get("output")
        if isinstance(output, str) and output:
            print(output)
        elif output is not None:
            _print_json(output)
        print(f"Delegation completed via {payload.get('backend', 'unknown')}.")
    return int(payload.get("exit_code", 1))


def _delegate_argument_error(args: argparse.Namespace, agent: object) -> str:
    from agency_runtime.core.resident_managers import resident_manager_boundary_error

    if error := resident_manager_boundary_error(
        agent,
        operation="be delegated as a CLI worker",
    ):
        return error
    if args.timeout is not None and (not math.isfinite(args.timeout) or args.timeout <= 0):
        return "--timeout must be a finite value greater than 0"
    return ""


def cmd_delegate(args: argparse.Namespace) -> int:
    from agency_runtime.core.runtime_control import master_enabled

    if not master_enabled():
        return _emit_delegate_result(
            args,
            {
                "status": "bypassed",
                "runtime_enabled": False,
                "bypassed": True,
                "exit_code": 0,
            },
        )
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
    if error := _delegate_argument_error(args, agent):
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
        candidate, store = _delegation_candidate_and_store(backend_name, factories)
    except (KeyError, TypeError, ValueError) as exc:
        error = str(exc) or f"invalid backend configuration: {backend_name}"
        return _emit_delegate_result(
            args,
            {"status": "error", "error": error, "exit_code": 2},
            stderr=error,
        )

    from agency_runtime.core.delegation.events import work_unit_id_from_text

    session_id = f"cli-delegate-session-{uuid.uuid4()}"
    trace_id = f"cli-delegate-{uuid.uuid4()}"
    work_unit_id = work_unit_id_from_text(task)
    event_id = store.record_delegation(
        trace_id=trace_id,
        session_id=session_id,
        host="cli",
        work_unit_id=work_unit_id,
        recommended_agent=agent or "",
        status="suggested",
        backend=backend_name,
    )
    payload = {
        "session_id": session_id,
        "trace_id": trace_id,
        "work_unit_id": work_unit_id,
        "event_id": event_id,
        "backend": backend_name,
        "agent": agent,
        "timeout_seconds": timeout,
        "executed_worker_kind": "",
        "executed_worker_id": "",
        "native_run_id": "",
    }

    try:
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
        if not isinstance(result, dict):
            raise TypeError("delegation backend returned a non-object result")
        result = dict(result)
        status = str(result.get("status") or "failed")
        error = str(result.get("error") or "")
        worker_kind, worker_id, native_run_id = _completed_execution_identity(
            result,
            backend=backend_name,
        )
        if status == "completed" and not native_run_id:
            status = "failed"
            error = "backend completed without verifiable CLI process correlation"
            result = {
                **result,
                "status": status,
                "process_exit_code": int(result.get("exit_code", 0) or 0),
                "exit_code": 1,
                "error": error,
            }
    except (KeyboardInterrupt, SystemExit) as interrupt:
        reason = f"delegation interrupted ({type(interrupt).__name__})"
        try:
            _persist_cli_terminal_evidence(
                store,
                event_id=event_id,
                trace_id=trace_id,
                session_id=session_id,
                evidence_status="skipped",
                run_status="interrupted",
                backend=backend_name,
                error=reason,
                skip_reason=reason,
            )
        except BaseException as terminalization_error:
            raise interrupt from terminalization_error
        raise
    except Exception as exc:
        error = f"backend raised unexpected {safe_display_token(type(exc).__name__, limit=80)}"
        result = {
            "backend": backend_name,
            "status": "failed",
            "exit_code": 1,
            "error": error,
        }
        status = "failed"
        worker_kind = ""
        worker_id = ""
        native_run_id = ""
    if status == "completed":
        evidence_status = "completed"
        skip_reason = ""
    elif status in {"unavailable", "timed_out"}:
        evidence_status = "skipped"
        skip_reason = error or status
    else:
        evidence_status = "failed"
        skip_reason = ""
    _persist_cli_terminal_evidence(
        store,
        event_id=event_id,
        trace_id=trace_id,
        session_id=session_id,
        evidence_status=evidence_status,
        run_status=evidence_status,
        backend=backend_name,
        error=error,
        skip_reason=skip_reason,
        executed_worker_kind=worker_kind,
        executed_worker_id=worker_id,
        native_run_id=native_run_id,
    )
    payload.update(
        {
            "executed_worker_kind": worker_kind,
            "executed_worker_id": worker_id,
            "native_run_id": native_run_id,
        }
    )
    normalized = {**result, **payload, "status": evidence_status}
    if skip_reason:
        normalized["skip_reason"] = skip_reason
    return _emit_delegate_result(
        args, normalized, stderr=error if evidence_status != "completed" else ""
    )


def cmd_codex_exec(args: argparse.Namespace) -> int:
    return _run_command(["codex", "exec", *args.args], secure_executable=True)


def cmd_run(args: argparse.Namespace) -> int:
    """Run the exact argv explicitly supplied by the caller as a compatibility passthrough."""

    return _run_command(args.args)
