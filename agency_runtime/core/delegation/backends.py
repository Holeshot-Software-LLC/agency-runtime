"""Pluggable delegation backends for Agency Runtime.

Backends expose a small callable interface and self-report availability.  The
registry selects by iterating registered backends, so new runtimes can be added
without changing selector conditionals.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Iterable, Protocol, Sequence, runtime_checkable


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
    """Generic subprocess-backed delegation backend."""

    command: Sequence[str]
    name: str = "command"
    timeout: int = 3600
    extra_env: dict[str, str] = field(default_factory=dict)

    def is_available(self) -> bool:
        executable = self.command[0] if self.command else ""
        return bool(executable and shutil.which(executable))

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        """Return argv for a task. Subclasses override for native CLIs."""
        argv = list(self.command)
        argv.append(task)
        return argv

    def delegate(
        self,
        *,
        task: str,
        workdir: str | None = None,
        recommended_agent: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run the command backend and return a normalized process record."""
        argv = self.build_command(task, recommended_agent=recommended_agent)
        env = os.environ.copy()
        env.update(self.extra_env)
        completed = subprocess.run(
            argv,
            cwd=workdir or None,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            env=env,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"backend {self.name} failed with exit {completed.returncode}: "
                f"{completed.stderr.strip() or completed.stdout.strip()}"
            )
        return {
            "backend": self.name,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "command": argv,
        }


@dataclass(slots=True)
class HermesDelegateBackend(CommandBackend):
    """Hermes CLI backend using delegate-task style dispatch when installed."""

    command: Sequence[str] = ("hermes", "-z")
    name: str = "hermes"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        prompt = task
        if recommended_agent:
            prompt = f"Use Agency specialist {recommended_agent} when relevant.\n\n{task}"
        return [*self.command, prompt]


@dataclass(slots=True)
class OpenClawSessionsBackend(CommandBackend):
    """OpenClaw session-spawn backend when an OpenClaw CLI is available."""

    command: Sequence[str] = ("openclaw", "sessions_spawn")
    name: str = "openclaw"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        argv = list(self.command)
        if recommended_agent:
            argv.extend(["--agent", recommended_agent])
        argv.extend(["--task", task])
        return argv


@dataclass(slots=True)
class CodexExecBackend(CommandBackend):
    """OpenAI Codex CLI backend using non-interactive exec mode."""

    command: Sequence[str] = ("codex", "exec")
    name: str = "codex"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, task]


@dataclass(slots=True)
class ClaudeExecBackend(CommandBackend):
    """Claude Code CLI backend using non-interactive print mode."""

    command: Sequence[str] = ("claude", "-p", "--output-format", "json")
    name: str = "claude"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        prompt = task
        if recommended_agent:
            prompt = f"Use Agency specialist {recommended_agent} when relevant.\n\n{task}"
        return [*self.command, prompt]


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
        raise RuntimeError(f"No available delegation backend{requested}")

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
    ]
)


def register_backend(backend: DelegateBackend) -> DelegateBackend:
    """Register a backend in the process-wide default registry."""
    return DEFAULT_REGISTRY.register(backend)


def get_delegate_func(*, preferred: str | None = None, registry: BackendRegistry | None = None):
    """Return a lifecycle-compatible delegate callable from a registry."""
    return (registry or DEFAULT_REGISTRY).delegate_func(preferred=preferred)


__all__ = [
    "BackendRegistry",
    "ClaudeExecBackend",
    "CodexExecBackend",
    "CommandBackend",
    "DEFAULT_REGISTRY",
    "DelegateBackend",
    "HermesDelegateBackend",
    "OpenClawSessionsBackend",
    "get_delegate_func",
    "register_backend",
]
