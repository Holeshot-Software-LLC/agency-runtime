"""Production-safe subprocess delegation backends.

Each backend uses a documented, non-interactive host CLI surface.  Commands are
always executed as argv (never through a shell), successful structured output is
validated, and process failures remain failures instead of becoming synthetic
delegation evidence.
"""

from __future__ import annotations

import json
import math
import os
import signal
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal, Protocol, Sequence, runtime_checkable


_ERROR_PREVIEW_CHARS = 2_000


def _owned_process_kwargs(*, platform_name: str | None = None) -> dict[str, Any]:
    """Return launch flags for a process tree owned by Agency Runtime."""
    if (platform_name or os.name) == "nt":
        return {
            "creationflags": (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            )
        }
    return {"start_new_session": True}


def _terminate_owned_process_tree(
    process: subprocess.Popen[str],
    *,
    platform_name: str | None = None,
) -> None:
    """Terminate the complete process tree started for one delegation."""
    platform = platform_name or os.name
    if platform == "nt":
        try:
            killer = subprocess.Popen(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_owned_process_kwargs(platform_name="nt"),
            )
            killer.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
            except OSError:
                pass
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                try:
                    process.kill()
                except OSError:
                    pass

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _run_owned_process(
    argv: list[str],
    *,
    cwd: str | None,
    env: dict[str, str],
    stdout: Any,
    stderr: Any,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    """Run argv in a killable process group, including all descendants."""
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=stdout,
        stderr=stderr,
        env=env,
        **_owned_process_kwargs(),
    )
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_owned_process_tree(process)
        raise subprocess.TimeoutExpired(argv, timeout) from exc
    return subprocess.CompletedProcess(argv, int(process.returncode or 0))


def _stream_text(value: Any) -> str:
    """Normalize real and mocked subprocess stream values to UTF-8 text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    marker = "\n...[truncated by output limit]"
    keep = max(0, limit - len(marker))
    return text[:keep] + marker, True


def _read_process_stream(handle: Any, fallback: Any, limit: int) -> str:
    """Read at most one character beyond a process stream's configured cap."""
    if fallback is not None:
        return _stream_text(fallback)
    handle.flush()
    handle.seek(0)
    return _stream_text(handle.read(limit + 1))


def _specialist_prompt(task: str, recommended_agent: str | None) -> str:
    """Add Agency expertise context without treating a roster slug as a host id."""
    if not recommended_agent:
        return task
    specialist = recommended_agent.strip()
    if not specialist:
        return task
    if "\x00" in specialist:
        raise ValueError("recommended_agent must not contain NUL bytes")
    return (
        f"Agency specialist perspective requested: {specialist}\n\n"
        f"Delegated task:\n{task}"
    )


class BackendError(RuntimeError):
    """Base error carrying the normalized process result, when available."""

    def __init__(self, message: str, *, result: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.result = result or {}


class BackendUnavailableError(BackendError):
    """The configured executable cannot be launched on this host."""


class BackendTimeoutError(BackendError):
    """The host process exceeded the configured delegation deadline."""


class BackendExecutionError(BackendError):
    """The host process exited unsuccessfully."""


class BackendProtocolError(BackendError):
    """The host claimed process success but emitted an invalid response."""


@runtime_checkable
class DelegateBackend(Protocol):
    """Protocol implemented by delegation runtime adapters."""

    name: str

    def is_available(self) -> bool:
        """Return True when this backend can run on the current host."""

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Dispatch one work unit and return backend-specific result data."""


@dataclass(slots=True)
class CommandBackend:
    """Generic subprocess-backed delegation backend.

    ``command`` is an argv prefix, not a shell command string.  This distinction
    is intentional: shell parsing differs between Windows and POSIX and would
    make task text executable.
    """

    command: Sequence[str]
    name: str = "command"
    timeout: float = 3600
    extra_env: dict[str, str] = field(default_factory=dict)
    output_format: Literal["text", "json", "jsonl"] = "text"
    max_output_chars: int = 2_000_000

    def __post_init__(self) -> None:
        if isinstance(self.command, (str, bytes)):
            raise TypeError("command must be an argv sequence, not a shell command string")
        self.command = tuple(self.command)
        if not isinstance(self.name, str) or not self.name.strip() or "\x00" in self.name:
            raise ValueError("backend name must be a non-empty string")
        if self.output_format not in {"text", "json", "jsonl"}:
            raise ValueError("output_format must be text, json, or jsonl")
        if (
            isinstance(self.timeout, bool)
            or not isinstance(self.timeout, (int, float))
            or not math.isfinite(self.timeout)
            or self.timeout <= 0
        ):
            raise ValueError("timeout must be a finite value greater than zero")
        if (
            isinstance(self.max_output_chars, bool)
            or not isinstance(self.max_output_chars, int)
            or self.max_output_chars <= 0
        ):
            raise ValueError("max_output_chars must be a positive integer")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self.extra_env.items()):
            raise TypeError("extra_env keys and values must be strings")
        if any("\x00" in key or "=" in key or "\x00" in value for key, value in self.extra_env.items()):
            raise ValueError("extra_env contains an invalid environment key or value")
        for value in self.command:
            if not isinstance(value, str) or not value:
                raise ValueError("every command argv item must be a non-empty string")
            if "\x00" in value:
                raise ValueError("command argv must not contain NUL bytes")

    def executable_path(self) -> str | None:
        """Resolve the configured executable without spawning a process."""
        if not self.command:
            return None
        try:
            search_path = self.extra_env.get("PATH") or self.extra_env.get("Path")
            if search_path is None:
                return shutil.which(self.command[0])
            return shutil.which(self.command[0], path=search_path)
        except (OSError, TypeError, ValueError):
            return None

    def availability(self) -> dict[str, Any]:
        """Return a truthful, diagnostic availability record."""
        if not self.command:
            return {
                "backend": self.name,
                "available": False,
                "executable": None,
                "reason": "no command configured",
            }
        executable = self.executable_path()
        return {
            "backend": self.name,
            "available": bool(executable),
            "executable": executable,
            "reason": "" if executable else f"executable not found: {self.command[0]}",
        }

    def is_available(self) -> bool:
        return bool(self.executable_path())

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        """Return argv for a task. Subclasses override for native CLIs."""
        del recommended_agent
        return [*self.command, task]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        """Parse successful output according to the configured wire format."""
        if self.output_format == "text":
            return stdout, {}
        if self.output_format == "json":
            try:
                return json.loads(stdout), {}
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON output at character {exc.pos}") from exc

        events: list[Any] = []
        for line_number, line in enumerate(stdout.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL output on line {line_number}") from exc
        if not events:
            raise ValueError("JSONL output contained no events")
        return events, {"events": events}

    def _validate_task(self, task: str) -> str:
        if not isinstance(task, str):
            raise TypeError("task must be a string")
        if not task.strip():
            raise ValueError("task must not be empty")
        if "\x00" in task:
            raise ValueError("task must not contain NUL bytes")
        return task

    def _resolve_workdir(self, workdir: str | None) -> str | None:
        if workdir is None:
            return None
        path = Path(workdir).expanduser()
        if not path.exists():
            raise ValueError(f"workdir does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"workdir is not a directory: {path}")
        return str(path.resolve())

    def _result(
        self,
        *,
        argv: list[str],
        executable: str | None,
        workdir: str | None,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        status: str,
        error: str = "",
    ) -> dict[str, Any]:
        bounded_stdout, stdout_truncated = _bounded(stdout, self.max_output_chars)
        bounded_stderr, stderr_truncated = _bounded(stderr, self.max_output_chars)
        result: dict[str, Any] = {
            "backend": self.name,
            "status": status,
            "exit_code": exit_code,
            "stdout": bounded_stdout,
            "stderr": bounded_stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "command": argv,
            "executable": executable,
            "workdir": workdir or "",
        }
        if error:
            result["error"] = error
        return result

    def execute(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        check: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run and normalize a host process.

        With ``check=True`` (the delegation default), unavailable, timed-out,
        non-zero, and malformed-success responses raise ``BackendError``.
        Wrappers that historically return records can use ``check=False``.
        """
        del kwargs
        task = self._validate_task(task)
        cwd = self._resolve_workdir(workdir)
        if not self.command:
            result = self._result(
                argv=[],
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error="no command configured",
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: no command configured",
                result=result,
            )
            if check:
                raise error
            return result
        argv = self.build_command(task, recommended_agent=recommended_agent)
        if not argv:
            raise BackendUnavailableError(f"backend {self.name} has no command configured")
        if any(not isinstance(value, str) or not value or "\x00" in value for value in argv):
            raise ValueError("built command contains an invalid argv item")

        executable = self.executable_path()
        if not executable:
            result = self._result(
                argv=argv,
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error=f"executable not found: {self.command[0] if self.command else '<unconfigured>'}",
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: {result['error']}",
                result=result,
            )
            if check:
                raise error
            return result
        argv[0] = executable

        env = os.environ.copy()
        env.update(self.extra_env)
        # File-backed capture avoids unbounded PIPE buffering when an agent or
        # tool emits a very large transcript. Only max_output_chars + 1 is read
        # back into memory after the process exits.
        with (
            tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as stdout_file,
            tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as stderr_file,
        ):
            try:
                completed = _run_owned_process(
                    argv,
                    cwd=cwd,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=self.timeout,
                    env=env,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = _read_process_stream(
                    stdout_file,
                    exc.stdout if exc.stdout is not None else exc.output,
                    self.max_output_chars,
                )
                stderr = _read_process_stream(stderr_file, exc.stderr, self.max_output_chars)
                result = self._result(
                    argv=argv,
                    executable=executable,
                    workdir=cwd,
                    exit_code=124,
                    stdout=stdout,
                    stderr=stderr,
                    status="timed_out",
                    error=f"backend command timed out after {self.timeout:g}s",
                )
                error = BackendTimeoutError(result["error"], result=result)
                if check:
                    raise error
                return result
            except FileNotFoundError:
                result = self._result(
                    argv=argv,
                    executable=executable,
                    workdir=cwd,
                    exit_code=127,
                    status="unavailable",
                    error=f"resolved executable disappeared before launch: {executable}",
                )
                error = BackendUnavailableError(result["error"], result=result)
                if check:
                    raise error
                return result
            except PermissionError as exc:
                result = self._result(
                    argv=argv,
                    executable=executable,
                    workdir=cwd,
                    exit_code=126,
                    status="failed",
                    error=f"executable permission denied: {exc}",
                )
                error = BackendExecutionError(result["error"], result=result)
                if check:
                    raise error
                return result
            except OSError as exc:
                result = self._result(
                    argv=argv,
                    executable=executable,
                    workdir=cwd,
                    exit_code=1,
                    status="failed",
                    error=f"could not launch backend {self.name}: {exc}",
                )
                error = BackendExecutionError(result["error"], result=result)
                if check:
                    raise error
                return result

            stdout = _read_process_stream(stdout_file, completed.stdout, self.max_output_chars)
            stderr = _read_process_stream(stderr_file, completed.stderr, self.max_output_chars)
        result = self._result(
            argv=argv,
            executable=executable,
            workdir=cwd,
            exit_code=int(completed.returncode),
            stdout=stdout,
            stderr=stderr,
            status="completed" if completed.returncode == 0 else "failed",
        )
        if completed.returncode != 0:
            preview = (stderr.strip() or stdout.strip() or "no process output")
            preview, _ = _bounded(preview, _ERROR_PREVIEW_CHARS)
            result["error"] = f"backend {self.name} exited with {completed.returncode}: {preview}"
            error = BackendExecutionError(result["error"], result=result)
            if check:
                raise error
            return result

        try:
            if self.output_format != "text" and len(stdout) > self.max_output_chars:
                raise ValueError(
                    f"structured output exceeded the {self.max_output_chars}-character limit"
                )
            output, metadata = self.parse_stdout(stdout)
        except ValueError as exc:
            result["status"] = "failed"
            result["process_exit_code"] = 0
            result["exit_code"] = 1
            result["error"] = f"backend {self.name} returned an invalid success response: {exc}"
            error = BackendProtocolError(result["error"], result=result)
            if check:
                raise error
            return result
        # Do not return a second unbounded copy of text output. Structured
        # responses were size-checked before parsing above.
        result["output"] = result["stdout"] if self.output_format == "text" else output
        result.update(metadata)
        return result

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the backend and require both process and protocol success."""
        return self.execute(
            task=task,
            workdir=workdir,
            recommended_agent=recommended_agent,
            check=True,
            **kwargs,
        )


@dataclass(slots=True)
class HermesDelegateBackend(CommandBackend):
    """Hermes' documented, plain-text scripted one-shot interface."""

    command: Sequence[str] = ("hermes", "-z")
    name: str = "hermes"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        if not stdout.strip():
            raise ValueError("Hermes produced no final response text")
        return stdout, {}


@dataclass(slots=True)
class OpenClawSessionsBackend(CommandBackend):
    """OpenClaw agent-turn backend (legacy class name kept for API compatibility).

    ``sessions_spawn`` is an in-agent tool, not an OpenClaw CLI command.  The
    supported subprocess contract is ``openclaw agent``.  Agency roster slugs
    are prompt context; ``agent_id`` is the configured OpenClaw runtime id.
    """

    command: Sequence[str] = ("openclaw", "agent")
    name: str = "openclaw"
    output_format: Literal["text", "json", "jsonl"] = "json"
    agent_id: str = "main"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        agent_id = self.agent_id.strip()
        if not agent_id or "\x00" in agent_id:
            raise ValueError("OpenClaw agent_id must be a non-empty value without NUL bytes")
        return [
            *self.command,
            "--agent",
            agent_id,
            "--message",
            _specialist_prompt(task, recommended_agent),
            "--json",
        ]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        payload, _ = super().parse_stdout(stdout)
        if not isinstance(payload, dict):
            raise ValueError("OpenClaw JSON response must be an object")
        if payload.get("error"):
            raise ValueError(f"OpenClaw reported an error: {payload['error']}")
        status = str(payload.get("status") or "").strip().lower()
        if status and status not in {"completed", "done", "ok", "succeeded", "success"}:
            raise ValueError(f"OpenClaw reported non-terminal status {status!r}")
        texts = [
            str(item.get("text"))
            for item in payload.get("payloads", [])
            if isinstance(item, dict) and item.get("text") is not None
        ]
        if not any(text.strip() for text in texts):
            raise ValueError("OpenClaw returned no terminal response payload")
        return "\n".join(texts), {"response": payload}


# Preferred truthful name; the legacy import remains supported above.
OpenClawAgentBackend = OpenClawSessionsBackend


@dataclass(slots=True)
class CodexExecBackend(CommandBackend):
    """OpenAI Codex CLI backend using stable non-interactive JSONL exec mode."""

    command: Sequence[str] = ("codex", "exec")
    name: str = "codex"
    output_format: Literal["text", "json", "jsonl"] = "jsonl"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [
            *self.command,
            "--json",
            "--color",
            "never",
            _specialist_prompt(task, recommended_agent),
        ]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        events, metadata = super().parse_stdout(stdout)
        assert isinstance(events, list)
        event_types = {
            str(event.get("type") or "")
            for event in events
            if isinstance(event, dict)
        }
        failure = next(
            (
                event
                for event in events
                if isinstance(event, dict) and str(event.get("type") or "") in {"error", "turn.failed"}
            ),
            None,
        )
        if failure is not None:
            raise ValueError(f"Codex emitted a failure event: {failure.get('type')}")
        if "turn.completed" not in event_types:
            raise ValueError("Codex JSONL stream ended without turn.completed")

        messages: list[str] = []
        for event in events:
            if not isinstance(event, dict) or event.get("type") != "item.completed":
                continue
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "agent_message" and item.get("text") is not None:
                messages.append(str(item["text"]))
        metadata["events"] = events
        return messages[-1] if messages else events, metadata


@dataclass(slots=True)
class ClaudeExecBackend(CommandBackend):
    """Claude Code backend using documented print-mode JSON output."""

    command: Sequence[str] = ("claude", "-p", "--output-format", "json")
    name: str = "claude"
    output_format: Literal["text", "json", "jsonl"] = "json"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        payload, _ = super().parse_stdout(stdout)
        if not isinstance(payload, dict):
            raise ValueError("Claude JSON response must be an object")
        if payload.get("error"):
            raise ValueError(f"Claude reported an error: {payload['error']}")
        if payload.get("is_error") is True:
            raise ValueError("Claude reported is_error=true")
        subtype = str(payload.get("subtype") or "").strip().lower()
        if subtype and subtype not in {"completed", "done", "success", "succeeded"}:
            raise ValueError(f"Claude reported non-terminal subtype {subtype!r}")
        result = payload.get("result")
        if not isinstance(result, (str, list, dict)) or not result:
            raise ValueError("Claude returned no terminal result")
        return result, {"response": payload}


@dataclass(slots=True)
class GenericCLIBackend(CommandBackend):
    """Explicitly configured fallback for an otherwise unsupported agent CLI."""

    command: Sequence[str] = ()
    name: str = "generic"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]


class BackendRegistry:
    """Ordered registry of pluggable delegation backends."""

    def __init__(self, backends: Iterable[DelegateBackend] | None = None) -> None:
        self._backends: list[DelegateBackend] = list(backends or [])

    def register(self, backend: DelegateBackend) -> DelegateBackend:
        """Register a backend and return it for decorator-style use."""
        self._backends.append(backend)
        return backend

    def unregister(self, name: str) -> None:
        """Remove all backends with the given name."""
        self._backends = [backend for backend in self._backends if backend.name != name]

    def available_backends(self) -> list[DelegateBackend]:
        """Return currently available backends in selection order."""
        return [backend for backend in self._backends if backend.is_available()]

    def select_backend(self, *, preferred: str | None = None) -> DelegateBackend:
        """Select the first available backend, optionally constrained by name."""
        candidates = self._backends
        if preferred:
            candidates = [backend for backend in candidates if backend.name == preferred]
        for backend in candidates:
            if backend.is_available():
                return backend
        requested = f" named {preferred!r}" if preferred else ""
        details: list[str] = []
        for backend in candidates:
            availability = getattr(backend, "availability", None)
            if callable(availability):
                record = availability()
                details.append(f"{backend.name}: {record.get('reason') or 'unavailable'}")
            else:
                details.append(f"{backend.name}: unavailable")
        suffix = f" ({'; '.join(details)})" if details else ""
        raise BackendUnavailableError(f"No available delegation backend{requested}{suffix}")

    def delegate_func(self, *, preferred: str | None = None):
        """Return a delegate_func-compatible callable for lifecycle dispatch."""
        backend = self.select_backend(preferred=preferred)

        def _delegate(**kwargs: Any) -> Any:
            return backend.delegate(**kwargs)

        setattr(_delegate, "backend_name", backend.name)
        return _delegate


DEFAULT_REGISTRY = BackendRegistry(
    [
        HermesDelegateBackend(),
        OpenClawSessionsBackend(),
        CodexExecBackend(),
        ClaudeExecBackend(),
        GenericCLIBackend(),
    ]
)


def register_backend(backend: DelegateBackend) -> DelegateBackend:
    """Register a backend in the process-wide default registry."""
    return DEFAULT_REGISTRY.register(backend)


def get_delegate_func(*, preferred: str | None = None, registry: BackendRegistry | None = None):
    """Return a lifecycle-compatible delegate callable from a registry."""
    return (registry or DEFAULT_REGISTRY).delegate_func(preferred=preferred)


__all__ = [
    "BackendError",
    "BackendExecutionError",
    "BackendProtocolError",
    "BackendRegistry",
    "BackendTimeoutError",
    "BackendUnavailableError",
    "ClaudeExecBackend",
    "CodexExecBackend",
    "CommandBackend",
    "DEFAULT_REGISTRY",
    "DelegateBackend",
    "GenericCLIBackend",
    "HermesDelegateBackend",
    "OpenClawAgentBackend",
    "OpenClawSessionsBackend",
    "get_delegate_func",
    "register_backend",
]
