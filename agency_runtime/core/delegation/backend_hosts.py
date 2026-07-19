"""Documented host-specific delegation backend definitions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from agency_runtime.core.delegation.backend_command import CommandBackend


def _specialist_prompt(task: str, recommended_agent: str | None) -> str:
    """Resolve through the facade so historical monkeypatches remain effective."""
    from agency_runtime.core.delegation import backends as compatibility

    return compatibility._specialist_prompt(task, recommended_agent)


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
        payload, _ = CommandBackend.parse_stdout(self, stdout)
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
        del task, recommended_agent
        return [
            *self.command,
            "--json",
            "--color",
            "never",
        ]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str:
        return _specialist_prompt(task, recommended_agent)

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        events, metadata = CommandBackend.parse_stdout(self, stdout)
        if not isinstance(events, list):
            raise ValueError("Codex JSONL parser returned an invalid event stream")
        event_types = {str(event.get("type") or "") for event in events if isinstance(event, dict)}
        failure = next(
            (
                event
                for event in events
                if isinstance(event, dict)
                and str(event.get("type") or "") in {"error", "turn.failed"}
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
            if isinstance(item, dict) and item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    messages.append(text)
        metadata["events"] = events
        if not messages:
            raise ValueError("Codex completed without a final agent message")
        return messages[-1], metadata


@dataclass(slots=True)
class ClaudeExecBackend(CommandBackend):
    """Claude Code backend using documented print-mode JSON output."""

    command: Sequence[str] = ("claude", "-p", "--output-format", "json")
    name: str = "claude"
    output_format: Literal["text", "json", "jsonl"] = "json"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        del task, recommended_agent
        return [*self.command]

    def build_input(
        self,
        task: str,
        recommended_agent: str | None = None,
    ) -> str:
        return _specialist_prompt(task, recommended_agent)

    def parse_stdout(self, stdout: str) -> tuple[Any, dict[str, Any]]:
        payload, _ = CommandBackend.parse_stdout(self, stdout)
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
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Claude returned no terminal result")
        return result, {"response": payload}


@dataclass(slots=True)
class GenericCLIBackend(CommandBackend):
    """Explicitly configured fallback for an otherwise unsupported agent CLI."""

    command: Sequence[str] = ()
    name: str = "generic"

    def build_command(self, task: str, recommended_agent: str | None = None) -> list[str]:
        return [*self.command, _specialist_prompt(task, recommended_agent)]
