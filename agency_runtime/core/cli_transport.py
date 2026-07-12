"""Allowlisted, non-interactive CLI transports for routing judgments.

Only Codex and Claude are supported. Prompts are delivered over stdin, child
environments omit unrelated credentials, output is bounded, and invocations run
inside an empty temporary directory with host tools and project customizations
disabled.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.config import ProviderEntry, is_safe_cli_model_id
from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)


SUPPORTED_CLI_TRANSPORTS = frozenset({"codex", "claude"})
_MAX_CLI_OUTPUT_CHARS = 64 * 1024
_STATUS_OUTPUT_CHARS = 32 * 1024
_CLAUDE_MINIMUM_VERSION = (2, 1, 205)
_VERSION_PATTERN = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")
_SAFE_ENVIRONMENT_NAMES = frozenset(
    {
        "APPDATA",
        "CLAUDE_CONFIG_DIR",
        "CODEX_HOME",
        "COMSPEC",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LC_ALL",
        "LOCALAPPDATA",
        "LOGNAME",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USER",
        "USERPROFILE",
        "REQUESTS_CA_BUNDLE",
        "WINDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    }
)
_SELECTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["selected_ids", "confidence"],
    "properties": {
        "selected_ids": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 50,
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


@dataclass(frozen=True, slots=True)
class CLIProviderStatus:
    """Truthful local status without command output or account identifiers."""

    transport: str
    installed: bool
    authenticated: bool
    usable: bool
    executable: str | None = None
    version: str = ""
    reason: str = ""


ProcessRunner = Callable[..., BoundedProcessResult]
BinaryResolver = Callable[[str], str | None]


def safe_cli_environment(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return only platform, proxy, and CLI-home variables required to launch."""

    source = os.environ if environ is None else environ
    safe = {
        key: value
        for key, value in source.items()
        if key.upper() in _SAFE_ENVIRONMENT_NAMES and isinstance(value, str)
    }
    safe["NO_COLOR"] = "1"
    return safe


def _isolated_invocation_environment(
    transport: str,
    cwd: str,
    environ: Mapping[str, str] | None,
) -> dict[str, str]:
    """Keep auth roots while redirecting general user/config roots to temp."""

    source = os.environ if environ is None else environ
    safe = safe_cli_environment(source)
    original_home = source.get("USERPROFILE") or source.get("HOME") or str(Path.home())
    if transport == "codex":
        safe["CODEX_HOME"] = source.get(
            "CODEX_HOME", str(Path(original_home) / ".codex")
        )
    else:
        safe["CLAUDE_CONFIG_DIR"] = source.get(
            "CLAUDE_CONFIG_DIR", str(Path(original_home) / ".claude")
        )
    isolated_home = str(Path(cwd) / "home")
    isolated_temp = str(Path(cwd) / "tmp")
    Path(isolated_home).mkdir(parents=True, exist_ok=True)
    Path(isolated_temp).mkdir(parents=True, exist_ok=True)
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
        safe[name] = isolated_home
    for name in ("TEMP", "TMP", "TMPDIR"):
        safe[name] = isolated_temp
    safe.pop("HOMEDRIVE", None)
    safe.pop("HOMEPATH", None)
    return safe


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_PATTERN.search(value)
    if match is None:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def _run_status(
    runner: ProcessRunner,
    argv: list[str],
    *,
    timeout: float,
    environ: Mapping[str, str] | None,
) -> BoundedProcessResult:
    return runner(
        argv,
        timeout=timeout,
        env=safe_cli_environment(environ),
        max_output_chars=_STATUS_OUTPUT_CHARS,
    )


def inspect_cli_transport(
    transport: str,
    *,
    timeout: float = 3.0,
    resolver: BinaryResolver = shutil.which,
    runner: ProcessRunner = run_bounded_process,
    environ: Mapping[str, str] | None = None,
) -> CLIProviderStatus:
    """Distinguish executable discovery, authentication, and usable contract."""

    normalized = str(transport).strip().lower()
    if normalized not in SUPPORTED_CLI_TRANSPORTS:
        return CLIProviderStatus(
            transport=normalized,
            installed=False,
            authenticated=False,
            usable=False,
            reason="unsupported CLI transport",
        )
    try:
        executable = resolver(normalized)
    except Exception:
        executable = None
    if not executable:
        return CLIProviderStatus(
            transport=normalized,
            installed=False,
            authenticated=False,
            usable=False,
            reason="executable not found",
        )

    auth_argv = (
        [executable, "login", "status"]
        if normalized == "codex"
        else [executable, "auth", "status"]
    )
    try:
        auth = _run_status(
            runner,
            auth_argv,
            timeout=timeout,
            environ=environ,
        )
    except Exception:
        return CLIProviderStatus(
            transport=normalized,
            installed=True,
            authenticated=False,
            usable=False,
            executable=executable,
            reason="authentication status command failed",
        )
    if auth.timed_out:
        return CLIProviderStatus(
            transport=normalized,
            installed=True,
            authenticated=False,
            usable=False,
            executable=executable,
            reason="authentication status timed out",
        )
    authenticated = auth.returncode == 0
    if not authenticated:
        return CLIProviderStatus(
            transport=normalized,
            installed=True,
            authenticated=False,
            usable=False,
            executable=executable,
            reason="authenticated session not available",
        )

    if normalized == "codex":
        try:
            capability = _run_status(
                runner,
                [executable, "exec", "--help"],
                timeout=timeout,
                environ=environ,
            )
        except Exception:
            capability = BoundedProcessResult(1, "", "")
        required = (
            "--json",
            "--output-schema",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "--strict-config",
        )
        compatible = (
            not capability.timed_out
            and capability.returncode == 0
            and all(flag in capability.stdout for flag in required)
        )
        return CLIProviderStatus(
            transport=normalized,
            installed=True,
            authenticated=True,
            usable=compatible,
            executable=executable,
            reason=""
            if compatible
            else "installed Codex lacks required non-interactive controls",
        )

    try:
        version_result = _run_status(
            runner,
            [executable, "--version"],
            timeout=timeout,
            environ=environ,
        )
    except Exception:
        version_result = BoundedProcessResult(1, "", "")
    parsed_version = _version_tuple(version_result.stdout)
    compatible = (
        not version_result.timed_out
        and version_result.returncode == 0
        and parsed_version is not None
        and parsed_version >= _CLAUDE_MINIMUM_VERSION
    )
    rendered_version = (
        ".".join(str(item) for item in parsed_version) if parsed_version else ""
    )
    return CLIProviderStatus(
        transport=normalized,
        installed=True,
        authenticated=True,
        usable=compatible,
        executable=executable,
        version=rendered_version,
        reason=""
        if compatible
        else "installed Claude lacks required structured-output guarantees",
    )


def _parse_codex(stdout: str) -> dict[str, Any] | None:
    events: list[dict[str, Any]] = []
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                return None
            events.append(event)
    except (TypeError, ValueError):
        return None
    if not events or any(
        str(event.get("type") or "") in {"error", "turn.failed"} for event in events
    ):
        return None
    if not any(event.get("type") == "turn.completed" for event in events):
        return None
    messages = [
        str(item["text"])
        for event in events
        if event.get("type") == "item.completed"
        and isinstance((item := event.get("item")), dict)
        and item.get("type") == "agent_message"
        and item.get("text") is not None
    ]
    if not messages:
        return None
    try:
        parsed = json.loads(messages[-1])
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_claude(stdout: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("is_error") is True
        or payload.get("error")
    ):
        return None
    subtype = str(payload.get("subtype") or "").strip().lower()
    if subtype and subtype not in {"completed", "done", "success", "succeeded"}:
        return None
    result = payload.get("structured_output", payload.get("result"))
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return None
    return result if isinstance(result, dict) else None


def invoke_cli_judge(
    provider: ProviderEntry,
    prompt: str,
    *,
    timeout: float,
    resolver: BinaryResolver = shutil.which,
    runner: ProcessRunner = run_bounded_process,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Invoke one supported CLI judge; return only a parsed selection object."""

    transport = provider.transport.strip().lower()
    if (
        provider.type.strip().lower() != "cli"
        or transport not in SUPPORTED_CLI_TRANSPORTS
        or not is_safe_cli_model_id(provider.model)
    ):
        return None
    try:
        executable = resolver(transport)
    except Exception:
        executable = None
    if (
        not executable
        or not isinstance(prompt, str)
        or not prompt.strip()
        or "\x00" in prompt
    ):
        return None

    schema_json = json.dumps(_SELECTION_SCHEMA, separators=(",", ":"), sort_keys=True)
    try:
        with tempfile.TemporaryDirectory(prefix="agency-cli-judge-") as temporary:
            cwd = str(Path(temporary).resolve())
            if transport == "codex":
                schema_path = Path(temporary) / "selection.schema.json"
                schema_path.write_text(schema_json, encoding="utf-8")
                argv = [
                    executable,
                    "exec",
                    "--json",
                    "--color",
                    "never",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--strict-config",
                    "--sandbox",
                    "read-only",
                    "-c",
                    "features.shell_tool=false",
                    "-c",
                    "features.unified_exec=false",
                    "-c",
                    'web_search="disabled"',
                    "-c",
                    "tools.web_search=false",
                    "-c",
                    "apps._default.enabled=false",
                    "--skip-git-repo-check",
                    "--output-schema",
                    str(schema_path),
                ]
                if provider.model:
                    argv.extend(["--model", provider.model])
                argv.append("-")
            else:
                argv = [
                    executable,
                    "--safe-mode",
                    "-p",
                    "--output-format",
                    "json",
                    "--json-schema",
                    schema_json,
                    "--max-turns",
                    "1",
                    "--no-session-persistence",
                    "--tools",
                    "",
                    "--disallowedTools",
                    "mcp__*",
                    "--strict-mcp-config",
                    "--permission-mode",
                    "dontAsk",
                ]
                if provider.model:
                    argv.extend(["--model", provider.model])

            result = runner(
                argv,
                timeout=timeout,
                cwd=cwd,
                env=_isolated_invocation_environment(transport, cwd, environ),
                input_text=prompt,
                max_output_chars=_MAX_CLI_OUTPUT_CHARS,
            )
    except Exception:
        return None
    if (
        result.timed_out
        or result.returncode != 0
        or result.stdout_truncated
        or result.stderr_truncated
    ):
        return None
    return (
        _parse_codex(result.stdout)
        if transport == "codex"
        else _parse_claude(result.stdout)
    )


__all__ = [
    "CLIProviderStatus",
    "SUPPORTED_CLI_TRANSPORTS",
    "inspect_cli_transport",
    "invoke_cli_judge",
    "safe_cli_environment",
]
