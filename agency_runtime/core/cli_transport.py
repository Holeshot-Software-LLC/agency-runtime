"""Allowlisted, non-interactive CLI transports for routing judgments.

Only Codex and Claude are supported. Prompts are delivered over stdin, child
environments omit unrelated credentials, output is bounded, and invocations run
inside an empty temporary directory with host tools and project customizations
disabled.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import ProviderEntry, is_safe_cli_model_id
from agency_runtime.core.delegation.backends import (
    BoundedProcessResult,
    run_bounded_process,
)
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.process_argv import (
    PreparedProcessArgv,
    freeze_process_argv,
    prepare_process_argv,
    resolve_executable_path,
    sanitized_executable_search_path,
)

SUPPORTED_CLI_TRANSPORTS = frozenset({"codex", "claude"})
_MAX_CLI_OUTPUT_CHARS = 64 * 1024
_MAX_CLI_PROMPT_BYTES = 1_280 * 1024
_STATUS_OUTPUT_CHARS = 32 * 1024
_CLAUDE_MINIMUM_VERSION = (2, 1, 205)
_CODEX_REQUIRED_FLAGS = (
    "--json",
    "--output-schema",
    "--ephemeral",
    "--ignore-user-config",
    "--ignore-rules",
    "--sandbox",
    "--strict-config",
)
_MAX_CLI_TIMEOUT_SECONDS = 600.0
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
BinaryResolver = Callable[..., str | None]
_REPOSITORY_MARKERS = (".git", ".hg", ".svn")


def _repository_forbidden_roots(current_directory: Path) -> tuple[Path, ...]:
    """Discover workspace ancestors without importing or executing repository code."""

    current = current_directory.resolve(strict=True)
    roots = [current]
    for candidate in (current, *current.parents):
        marker_found = False
        for marker_name in _REPOSITORY_MARKERS:
            try:
                (candidate / marker_name).lstat()
            except (FileNotFoundError, NotADirectoryError):
                continue
            except OSError:
                # An unreadable marker cannot be safely disproved.
                marker_found = True
                break
            else:
                marker_found = True
                break
        if marker_found:
            roots.append(candidate)
    return tuple(dict.fromkeys(roots))


def _valid_timeout(value: float) -> bool:
    if isinstance(value, bool):
        return False
    try:
        timeout = float(value)
    except (TypeError, ValueError, OverflowError):
        return False
    return math.isfinite(timeout) and 0 < timeout <= _MAX_CLI_TIMEOUT_SECONDS


def safe_cli_environment(
    environ: Mapping[str, str] | None = None,
    *,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> dict[str, str]:
    """Return only platform, proxy, and CLI-home variables required to launch."""

    source = os.environ if environ is None else environ
    safe = {
        key: value
        for key, value in source.items()
        if key.upper() in _SAFE_ENVIRONMENT_NAMES and isinstance(value, str)
    }
    if "PATH" in safe:
        safe["PATH"] = sanitized_executable_search_path(
            safe["PATH"],
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
    safe["NO_COLOR"] = "1"
    return safe


def _isolated_invocation_environment(
    transport: str,
    cwd: str,
    environ: Mapping[str, str] | None,
) -> dict[str, str]:
    """Keep auth roots while redirecting general user/config roots to temp."""

    source = os.environ if environ is None else environ
    current_directory = Path.cwd()
    safe = safe_cli_environment(
        source,
        current_directory=current_directory,
        forbidden_roots=_repository_forbidden_roots(current_directory),
    )
    original_home = source.get("USERPROFILE") or source.get("HOME") or str(Path.home())
    if transport == "codex":
        safe["CODEX_HOME"] = source.get("CODEX_HOME", str(Path(original_home) / ".codex"))
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
    argv: Sequence[str],
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


def _unusable_status(
    transport: str,
    reason: str,
    *,
    installed: bool = False,
    authenticated: bool = False,
    executable: str | None = None,
    version: str = "",
) -> CLIProviderStatus:
    return CLIProviderStatus(
        transport=transport,
        installed=installed,
        authenticated=authenticated,
        usable=False,
        executable=executable,
        version=version,
        reason=reason,
    )


def _prepared_cli_command(
    executable: PreparedProcessArgv,
    *arguments: str,
) -> PreparedProcessArgv:
    command = PreparedProcessArgv(
        [*executable, *arguments],
        artifact_paths=executable.artifact_paths,
    )
    command.executable_identities = executable.executable_identities
    command.frozen_platform = executable.frozen_platform
    return command


def _display_cli_executable(executable: PreparedProcessArgv | str) -> str:
    return (
        executable.artifact_paths[-1]
        if isinstance(executable, PreparedProcessArgv)
        else str(executable)
    )


def _resolve_cli_executable(
    transport: str,
    resolver: BinaryResolver,
    *,
    environ: Mapping[str, str] | None,
) -> PreparedProcessArgv | None:
    source = os.environ if environ is None else environ
    current_directory = Path.cwd()
    try:
        forbidden_roots = _repository_forbidden_roots(current_directory)
        safe_path = sanitized_executable_search_path(
            source.get("PATH", ""),
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
        resolved = resolve_executable_path(
            transport,
            search_path=safe_path,
            resolver=resolver,
            current_directory=current_directory,
        )
        prepared = prepare_process_argv(
            [resolved],
            resolver=lambda name: shutil.which(name, path=safe_path),
        )
        return freeze_process_argv(
            prepared,
            forbidden_roots=forbidden_roots,
        )
    except Exception:
        return None


def _authentication_failure(
    transport: str,
    executable: PreparedProcessArgv,
    *,
    timeout: float,
    runner: ProcessRunner,
    environ: Mapping[str, str] | None,
) -> CLIProviderStatus | None:
    command = (
        _prepared_cli_command(executable, "login", "status")
        if transport == "codex"
        else _prepared_cli_command(executable, "auth", "status")
    )
    try:
        result = _run_status(runner, command, timeout=timeout, environ=environ)
    except Exception:
        return _unusable_status(
            transport,
            "authentication status command failed",
            installed=True,
            executable=_display_cli_executable(executable),
        )
    if result.timed_out:
        return _unusable_status(
            transport,
            "authentication status timed out",
            installed=True,
            executable=_display_cli_executable(executable),
        )
    if result.returncode != 0:
        return _unusable_status(
            transport,
            "authenticated session not available",
            installed=True,
            executable=_display_cli_executable(executable),
        )
    return None


def _inspect_codex_capability(
    executable: PreparedProcessArgv,
    *,
    timeout: float,
    runner: ProcessRunner,
    environ: Mapping[str, str] | None,
) -> CLIProviderStatus:
    try:
        result = _run_status(
            runner,
            _prepared_cli_command(executable, "exec", "--help"),
            timeout=timeout,
            environ=environ,
        )
    except Exception:
        result = BoundedProcessResult(1, "", "")
    compatible = (
        not result.timed_out
        and result.returncode == 0
        and all(flag in result.stdout for flag in _CODEX_REQUIRED_FLAGS)
    )
    if not compatible:
        return _unusable_status(
            "codex",
            "installed Codex lacks required non-interactive controls",
            installed=True,
            authenticated=True,
            executable=_display_cli_executable(executable),
        )
    return CLIProviderStatus(
        transport="codex",
        installed=True,
        authenticated=True,
        usable=True,
        executable=_display_cli_executable(executable),
    )


def _inspect_claude_capability(
    executable: PreparedProcessArgv,
    *,
    timeout: float,
    runner: ProcessRunner,
    environ: Mapping[str, str] | None,
) -> CLIProviderStatus:
    try:
        result = _run_status(
            runner,
            _prepared_cli_command(executable, "--version"),
            timeout=timeout,
            environ=environ,
        )
    except Exception:
        result = BoundedProcessResult(1, "", "")
    parsed_version = _version_tuple(result.stdout)
    rendered_version = ".".join(str(item) for item in parsed_version) if parsed_version else ""
    compatible = (
        not result.timed_out
        and result.returncode == 0
        and parsed_version is not None
        and parsed_version >= _CLAUDE_MINIMUM_VERSION
    )
    if not compatible:
        return _unusable_status(
            "claude",
            "installed Claude lacks required structured-output guarantees",
            installed=True,
            authenticated=True,
            executable=_display_cli_executable(executable),
            version=rendered_version,
        )
    return CLIProviderStatus(
        transport="claude",
        installed=True,
        authenticated=True,
        usable=True,
        executable=_display_cli_executable(executable),
        version=rendered_version,
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
        return _unusable_status(normalized, "unsupported CLI transport")
    if not _valid_timeout(timeout):
        return _unusable_status(
            normalized,
            "CLI inspection timeout is outside the supported range",
        )
    timeout = float(timeout)
    executable = _resolve_cli_executable(
        normalized,
        resolver,
        environ=environ,
    )
    if not executable:
        return _unusable_status(
            normalized,
            "executable not found",
        )
    auth_failure = _authentication_failure(
        normalized,
        executable,
        timeout=timeout,
        runner=runner,
        environ=environ,
    )
    if auth_failure is not None:
        return auth_failure
    inspector = _inspect_codex_capability if normalized == "codex" else _inspect_claude_capability
    return inspector(
        executable,
        timeout=timeout,
        runner=runner,
        environ=environ,
    )


def _parse_codex(stdout: str) -> dict[str, Any] | None:
    if not isinstance(stdout, str) or len(stdout) > _MAX_CLI_OUTPUT_CHARS:
        return None
    events: list[dict[str, Any]] = []
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = safe_load_bounded_json(
                line,
                maximum_bytes=_MAX_CLI_OUTPUT_CHARS,
                maximum_depth=32,
                maximum_nodes=5_000,
            )
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
        parsed = safe_load_bounded_json(
            messages[-1],
            maximum_bytes=_MAX_CLI_OUTPUT_CHARS,
            maximum_depth=32,
            maximum_nodes=5_000,
        )
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_claude(stdout: str) -> dict[str, Any] | None:
    try:
        payload = safe_load_bounded_json(
            stdout,
            maximum_bytes=_MAX_CLI_OUTPUT_CHARS,
            maximum_depth=32,
            maximum_nodes=5_000,
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("is_error") is True or payload.get("error"):
        return None
    subtype = str(payload.get("subtype") or "").strip().lower()
    if subtype and subtype not in {"completed", "done", "success", "succeeded"}:
        return None
    result = payload.get("structured_output", payload.get("result"))
    if isinstance(result, str):
        try:
            result = safe_load_bounded_json(
                result,
                maximum_bytes=_MAX_CLI_OUTPUT_CHARS,
                maximum_depth=32,
                maximum_nodes=5_000,
            )
        except ValueError:
            return None
    return result if isinstance(result, dict) else None


def invoke_cli_structured(
    provider: ProviderEntry,
    prompt: str,
    schema: Mapping[str, Any],
    *,
    timeout: float,
    resolver: BinaryResolver = shutil.which,
    runner: ProcessRunner = run_bounded_process,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any] | None:
    """Invoke one supported CLI provider with an explicit bounded JSON schema."""

    transport = provider.transport.strip().lower()
    if (
        provider.type.strip().lower() != "cli"
        or transport not in SUPPORTED_CLI_TRANSPORTS
        or not is_safe_cli_model_id(provider.model)
        or not _valid_timeout(timeout)
        or not isinstance(schema, Mapping)
    ):
        return None
    timeout = float(timeout)
    if not isinstance(prompt, str):
        return None
    try:
        invalid_prompt = (
            not prompt.strip()
            or "\x00" in prompt
            or len(prompt.encode("utf-8")) > _MAX_CLI_PROMPT_BYTES
        )
    except UnicodeError:
        return None
    if invalid_prompt:
        return None

    try:
        schema_json = json.dumps(
            dict(schema),
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError, UnicodeError):
        return None
    if len(schema_json.encode("utf-8")) > 64 * 1024:
        return None
    executable = _resolve_cli_executable(
        transport,
        resolver,
        environ=environ,
    )
    if not executable:
        return None
    try:
        with private_temporary_directory(prefix="cli-judge") as temporary:
            cwd = str(temporary)
            if transport == "codex":
                schema_path = Path(temporary) / "selection.schema.json"
                schema_path.write_text(schema_json, encoding="utf-8")
                arguments = [
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
                    arguments.extend(["--model", provider.model])
                arguments.append("-")
            else:
                arguments = [
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
                    arguments.extend(["--model", provider.model])

            argv = _prepared_cli_command(executable, *arguments)

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
    return _parse_codex(result.stdout) if transport == "codex" else _parse_claude(result.stdout)


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

    return invoke_cli_structured(
        provider,
        prompt,
        _SELECTION_SCHEMA,
        timeout=timeout,
        resolver=resolver,
        runner=runner,
        environ=environ,
    )


__all__ = [
    "SUPPORTED_CLI_TRANSPORTS",
    "CLIProviderStatus",
    "inspect_cli_transport",
    "invoke_cli_judge",
    "invoke_cli_structured",
    "safe_cli_environment",
]
