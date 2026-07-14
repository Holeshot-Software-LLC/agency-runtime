"""Generic command-backed delegation execution and response normalization."""

from __future__ import annotations

import math
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.delegation.backend_contracts import (
    BackendExecutionError,
    BackendProtocolError,
    BackendTimeoutError,
    BackendUnavailableError,
)
from agency_runtime.core.delegation.backend_process import (
    _BoundedTextCapture as _BoundedTextCaptureImpl,
)
from agency_runtime.core.delegation.backend_security import (
    ERROR_PREVIEW_CHARS as _ERROR_PREVIEW_CHARS,
)
from agency_runtime.core.delegation.backend_security import (
    MAX_TASK_CHARS as _MAX_TASK_CHARS,
)


def _compatibility():
    """Load the stable facade lazily to avoid an import cycle at module load."""
    from agency_runtime.core.delegation import backends as compatibility

    return compatibility


def prepare_process_argv(argv: list[str]) -> list[str]:
    """Resolve through the compatibility facade so existing patches stay effective."""
    return _compatibility().prepare_process_argv(argv)


def _run_owned_process(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run through the compatibility facade so existing patches stay effective."""
    return _compatibility()._run_owned_process(*args, **kwargs)


def _delegation_environment(
    backend_name: str,
    extra_env: dict[str, str],
) -> dict[str, str]:
    return _compatibility()._delegation_environment(backend_name, extra_env)


def _sensitive_variants(values: Iterable[str]) -> tuple[str, ...]:
    return _compatibility()._sensitive_variants(values)


def _specialist_prompt(task: str, recommended_agent: str | None) -> str:
    return _compatibility()._specialist_prompt(task, recommended_agent)


def _redact_text(value: str, variants: Iterable[str]) -> str:
    return _compatibility()._redact_text(value, variants)


def _redact_value(value: Any, variants: Iterable[str]) -> Any:
    return _compatibility()._redact_value(value, variants)


def _bounded(text: str, limit: int) -> tuple[str, bool]:
    return _compatibility()._bounded(text, limit)


def _BoundedTextCapture(limit: int) -> _BoundedTextCaptureImpl:
    return _compatibility()._BoundedTextCapture(limit)


def _raise_or_result(error: Any, *, check: bool) -> dict[str, Any]:
    if check:
        raise error
    return error.result


def _read_process_stream(handle: Any, fallback: Any, limit: int) -> str:
    return _compatibility()._read_process_stream(handle, fallback, limit)


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
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.extra_env.items()
        ):
            raise TypeError("extra_env keys and values must be strings")
        if any(
            "\x00" in key or "=" in key or "\x00" in value for key, value in self.extra_env.items()
        ):
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
            search_path = next(
                (value for key, value in self.extra_env.items() if key.upper() == "PATH"),
                None,
            )
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
        reason = "" if executable else f"executable not found: {self.command[0]}"
        if executable:
            try:
                prepared = prepare_process_argv([executable, *self.command[1:]])
                launch_executable = prepared[0]
                if not shutil.which(launch_executable):
                    raise FileNotFoundError(f"launch executable not found: {launch_executable}")
            except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
                executable = None
                reason = f"command cannot be launched safely: {exc}"
        return {
            "backend": self.name,
            "available": bool(executable),
            "executable": executable,
            "reason": reason,
        }

    def is_available(self) -> bool:
        return bool(self.availability()["available"])

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        """Return argv for a task. Subclasses override for native CLIs."""
        del recommended_agent
        return [*self.command, task]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str | None:
        """Return optional stdin for a task. CLI-specific backends may override."""
        del task, recommended_agent
        return None

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        """Parse successful output according to the configured wire format."""
        if self.output_format == "text":
            return stdout, {}
        if not isinstance(stdout, str) or len(stdout) > self.max_output_chars:
            raise ValueError("structured output exceeded the configured limit")
        maximum_bytes = min(self.max_output_chars, 64 * 1024 * 1024)
        if self.output_format == "json":
            try:
                return (
                    safe_load_bounded_json(
                        stdout,
                        maximum_bytes=maximum_bytes,
                        maximum_depth=64,
                        maximum_nodes=100_000,
                    ),
                    {},
                )
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid bounded JSON output") from exc

        events: list[Any] = []
        for line_number, line in enumerate(stdout.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                events.append(
                    safe_load_bounded_json(
                        line,
                        maximum_bytes=maximum_bytes,
                        maximum_depth=64,
                        maximum_nodes=100_000,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid bounded JSONL output on line {line_number}") from exc
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
        if len(task) > _MAX_TASK_CHARS:
            raise ValueError(f"task exceeds the {_MAX_TASK_CHARS}-character delegation limit")
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
        sensitive: Iterable[str] = (),
    ) -> dict[str, Any]:
        bounded_stdout, stdout_truncated = _bounded(
            _redact_text(stdout, sensitive),
            self.max_output_chars,
        )
        bounded_stderr, stderr_truncated = _bounded(
            _redact_text(stderr, sensitive),
            self.max_output_chars,
        )
        result: dict[str, Any] = {
            "backend": self.name,
            "status": status,
            "exit_code": exit_code,
            "stdout": bounded_stdout,
            "stderr": bounded_stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "command": _redact_value(argv, sensitive),
            "executable": executable,
            "workdir": workdir or "",
        }
        if error:
            result["error"] = _redact_text(error, sensitive)
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
        delegation_prompt = _specialist_prompt(task, recommended_agent)
        sensitive = _sensitive_variants((delegation_prompt, task))
        cwd = self._resolve_workdir(workdir)
        if not self.command:
            result = self._result(
                argv=[],
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error="no command configured",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: no command configured",
                result=result,
            )
            return _raise_or_result(error, check=check)
        argv = self.build_command(task, recommended_agent=recommended_agent)
        input_text = self.build_input(task, recommended_agent=recommended_agent)
        if not argv:
            raise BackendUnavailableError(f"backend {self.name} has no command configured")
        if any(not isinstance(value, str) or not value or "\x00" in value for value in argv):
            raise ValueError("built command contains an invalid argv item")
        if input_text is not None and (not isinstance(input_text, str) or "\x00" in input_text):
            raise ValueError("built input must be text without NUL bytes")

        executable = self.executable_path()
        if not executable:
            result = self._result(
                argv=argv,
                executable=None,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error=f"executable not found: {self.command[0] if self.command else '<unconfigured>'}",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(
                f"backend {self.name} is unavailable: {result['error']}",
                result=result,
            )
            return _raise_or_result(error, check=check)
        argv[0] = executable

        env = _delegation_environment(self.name, self.extra_env)
        stdout_capture = _BoundedTextCapture(self.max_output_chars)
        stderr_capture = _BoundedTextCapture(self.max_output_chars)
        try:
            completed = _run_owned_process(
                argv,
                cwd=cwd,
                stdout=stdout_capture,
                stderr=stderr_capture,
                timeout=self.timeout,
                env=env,
                input_text=input_text,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _read_process_stream(
                stdout_capture,
                exc.stdout if exc.stdout is not None else exc.output,
                self.max_output_chars,
            )
            stderr = _read_process_stream(
                stderr_capture,
                exc.stderr,
                self.max_output_chars,
            )
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                status="timed_out",
                error=f"backend command timed out after {self.timeout:g}s",
                sensitive=sensitive,
            )
            error = BackendTimeoutError(result["error"], result=result)
            return _raise_or_result(error, check=check)
        except FileNotFoundError:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=127,
                status="unavailable",
                error=f"resolved executable disappeared before launch: {executable}",
                sensitive=sensitive,
            )
            error = BackendUnavailableError(result["error"], result=result)
            return _raise_or_result(error, check=check)
        except PermissionError as exc:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=126,
                status="failed",
                error=f"executable permission denied: {exc}",
                sensitive=sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            return _raise_or_result(error, check=check)
        except OSError as exc:
            result = self._result(
                argv=argv,
                executable=executable,
                workdir=cwd,
                exit_code=1,
                status="failed",
                error=f"could not launch backend {self.name}: {exc}",
                sensitive=sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            return _raise_or_result(error, check=check)

        stdout = _read_process_stream(
            stdout_capture,
            completed.stdout,
            self.max_output_chars,
        )
        stderr = _read_process_stream(
            stderr_capture,
            completed.stderr,
            self.max_output_chars,
        )
        result = self._result(
            argv=argv,
            executable=executable,
            workdir=cwd,
            exit_code=int(completed.returncode),
            stdout=stdout,
            stderr=stderr,
            status="completed" if completed.returncode == 0 else "failed",
            sensitive=sensitive,
        )
        if completed.returncode != 0:
            preview = result["stderr"].strip() or result["stdout"].strip() or "no process output"
            preview, _ = _bounded(preview, _ERROR_PREVIEW_CHARS)
            result["error"] = _redact_text(
                f"backend {self.name} exited with {completed.returncode}: {preview}",
                sensitive,
            )
            error = BackendExecutionError(result["error"], result=result)
            return _raise_or_result(error, check=check)

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
            result["error"] = _redact_text(
                f"backend {self.name} returned an invalid success response: {exc}",
                sensitive,
            )
            error = BackendProtocolError(result["error"], result=result)
            return _raise_or_result(error, check=check)
        # Do not return a second unbounded copy of text output. Structured
        # responses were size-checked before parsing above.
        result["output"] = (
            result["stdout"] if self.output_format == "text" else _redact_value(output, sensitive)
        )
        result.update(_redact_value(metadata, sensitive))
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
