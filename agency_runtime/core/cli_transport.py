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
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    CODEX_REASONING_EFFORTS,
    ProviderEntry,
    is_safe_cli_model_id,
)
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
from agency_runtime.core.process_argv import (
    repository_forbidden_roots as _repository_forbidden_roots,
)
from agency_runtime.core.provider_deadline import require_provider_time

SUPPORTED_CLI_TRANSPORTS = frozenset({"codex", "claude"})
_MAX_CLI_OUTPUT_CHARS = 64 * 1024
_MAX_CLI_PROMPT_BYTES = 1_280 * 1024
# AR-361: the only tools an isolated verifier may be granted. Each is read-only
# in Claude Code, and --restricted confines them to the private working
# directory plus the explicit read-only roots, so a verifier can inspect a
# candidate snapshot without any way to write, run, or fetch.
_READ_ONLY_CLI_TOOLS = frozenset({"Read", "Grep", "Glob"})
_MAX_CLI_TURNS = 32
_MAX_CLI_READ_ONLY_ROOTS = 4
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
_MAX_MODEL_CATALOG_OUTPUT_CHARS = 1_048_576
_MAX_MODEL_CATALOG_ENTRIES = 64
_MODEL_CATALOG_CACHE_SECONDS = 60.0
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


@dataclass(frozen=True, slots=True)
class CLIModelInfo:
    """Bounded public metadata for one account-visible CLI model."""

    slug: str
    display_name: str
    description: str
    priority: int
    default_reasoning_level: str
    supported_reasoning_levels: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "display_name": self.display_name,
            "description": self.description,
            "priority": self.priority,
            "default_reasoning_level": self.default_reasoning_level,
            "supported_reasoning_levels": list(self.supported_reasoning_levels),
        }


@dataclass(frozen=True, slots=True)
class CLIModelCatalog:
    """One projected model inventory without raw host instructions or account data."""

    transport: str
    models: tuple[CLIModelInfo, ...]
    source: str
    observed_at: str
    stale: bool = False
    error: str = ""
    cache_hit: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "models": [model.as_dict() for model in self.models],
            "source": self.source,
            "observed_at": self.observed_at,
            "stale": self.stale,
            "error": self.error,
            "cache_hit": self.cache_hit,
        }


_MODEL_CATALOG_CONDITION = threading.Condition()
_MODEL_CATALOG_CACHE: dict[str, tuple[float, CLIModelCatalog]] = {}
_MODEL_CATALOG_IN_FLIGHT: set[str] = set()


ProcessRunner = Callable[..., BoundedProcessResult]
BinaryResolver = Callable[..., str | None]


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
    command.persistent_artifact_identities = executable.persistent_artifact_identities
    command.frozen_launcher = executable.frozen_launcher
    command.frozen_platform = executable.frozen_platform
    return command


def _display_cli_executable(executable: PreparedProcessArgv | str) -> str:
    return (
        executable.artifact_paths[-1]
        if isinstance(executable, PreparedProcessArgv)
        else str(executable)
    )


@dataclass(frozen=True, slots=True)
class _ResolvedCLI:
    """One CLI executable, or the exact reason it is unusable.

    "Not found" and "found but refused" are different problems with different
    fixes, and collapsing them cost a day: both host CLIs resolve fine on a real
    box and are then rejected because npm's directory permits cross-account
    substitution. Reporting that as a missing binary sends the reader hunting
    through PATH for something that is already there.
    """

    executable: PreparedProcessArgv | None
    reason: str


def _unusable_executable_reason(error: BaseException) -> str:
    """Describe why an executable cannot be used, without leaking a stack.

    Classify the cause; never echo the exception's text. A status string is a
    public surface, and an arbitrary resolver message can carry a private path or
    an account identifier — `test_cli_transport_status_failure_table` pins that.
    Classification alone is what fixes the diagnosis: "refused as untrusted"
    sends the reader to directory permissions, "not found" sends them to PATH,
    and telling them apart is the whole point. The offending path is still
    available in `agency status --json` as `inventory_error`.
    """

    if isinstance(error, FileNotFoundError):
        return "executable not found"
    if isinstance(error, PermissionError):
        return "executable refused as untrusted: its parent namespace permits substitution"
    if isinstance(error, OSError):
        return "executable unusable: it could not be resolved or frozen"
    return f"executable could not be prepared: {type(error).__name__}"


def _resolve_cli(
    transport: str,
    resolver: BinaryResolver,
    *,
    environ: Mapping[str, str] | None,
) -> _ResolvedCLI:
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
        return _ResolvedCLI(
            executable=freeze_process_argv(prepared, forbidden_roots=forbidden_roots),
            reason="",
        )
    except Exception as error:
        # Broad on purpose: resolution, preparation and freezing each raise their
        # own types, and every one of them must arrive as a stated reason rather
        # than a silent None.
        return _ResolvedCLI(executable=None, reason=_unusable_executable_reason(error))


def _resolve_cli_executable(
    transport: str,
    resolver: BinaryResolver,
    *,
    environ: Mapping[str, str] | None,
) -> PreparedProcessArgv | None:
    return _resolve_cli(transport, resolver, environ=environ).executable


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
    resolved = _resolve_cli(
        normalized,
        resolver,
        environ=environ,
    )
    executable = resolved.executable
    if not executable:
        return _unusable_status(normalized, resolved.reason or "executable not found")
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


def _model_catalog_error(transport: str, reason: str) -> CLIModelCatalog:
    return CLIModelCatalog(
        transport=transport,
        models=(),
        source="unavailable",
        observed_at=datetime.now(timezone.utc).isoformat(),
        error=reason[:256],
    )


def _parse_codex_model_catalog(stdout: str) -> CLIModelCatalog:
    try:
        payload = safe_load_bounded_json(
            stdout,
            maximum_bytes=_MAX_MODEL_CATALOG_OUTPUT_CHARS,
            maximum_depth=48,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError):
        return _model_catalog_error("codex", "Codex returned an invalid model catalog")
    rows = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) > 512:
        return _model_catalog_error("codex", "Codex model catalog has an invalid shape")
    models: list[CLIModelInfo] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or str(row.get("visibility") or "") != "list":
            continue
        slug = str(row.get("slug") or "").strip()
        if not slug or slug in seen or not is_safe_cli_model_id(slug):
            continue
        priority = row.get("priority", 1_000)
        if isinstance(priority, bool) or not isinstance(priority, int):
            priority = 1_000
        reasoning_rows = row.get("supported_reasoning_levels")
        reasoning_levels: list[str] = []
        if isinstance(reasoning_rows, list) and len(reasoning_rows) <= 32:
            for reasoning_row in reasoning_rows:
                if not isinstance(reasoning_row, dict):
                    continue
                effort = str(reasoning_row.get("effort") or "").strip().lower()
                if effort in CODEX_REASONING_EFFORTS and effort not in reasoning_levels:
                    reasoning_levels.append(effort)
        models.append(
            CLIModelInfo(
                slug=slug,
                display_name=str(row.get("display_name") or slug).strip()[:128],
                description=str(row.get("description") or "").strip()[:256],
                priority=max(0, min(priority, 1_000_000)),
                default_reasoning_level=str(row.get("default_reasoning_level") or "").strip()[:32],
                supported_reasoning_levels=tuple(reasoning_levels),
            )
        )
        seen.add(slug)
        if len(models) >= _MAX_MODEL_CATALOG_ENTRIES:
            break
    models.sort(key=lambda item: (item.priority, item.slug))
    return CLIModelCatalog(
        transport="codex",
        models=tuple(models),
        source="codex-cli",
        observed_at=datetime.now(timezone.utc).isoformat(),
        error="" if models else "Codex reported no visible models",
    )


def _discover_cli_models_uncached(
    transport: str,
    *,
    timeout: float,
    resolver: BinaryResolver,
    runner: ProcessRunner,
    environ: Mapping[str, str] | None,
) -> CLIModelCatalog:
    if transport != "codex":
        return _model_catalog_error(
            transport,
            "account-aware model discovery is not available for this CLI transport",
        )
    resolved = _resolve_cli(transport, resolver, environ=environ)
    executable = resolved.executable
    if not executable:
        return _model_catalog_error(transport, resolved.reason or "Codex executable not found")
    try:
        with private_temporary_directory(prefix="cli-models") as temporary:
            cwd = str(temporary)
            result = runner(
                _prepared_cli_command(executable, "debug", "models"),
                timeout=timeout,
                cwd=cwd,
                env=_isolated_invocation_environment(transport, cwd, environ),
                max_output_chars=_MAX_MODEL_CATALOG_OUTPUT_CHARS,
            )
    except Exception:
        return _model_catalog_error(transport, "Codex model discovery failed")
    if result.timed_out:
        return _model_catalog_error(transport, "Codex model discovery timed out")
    if result.returncode != 0 or result.stdout_truncated or result.stderr_truncated:
        return _model_catalog_error(transport, "Codex model discovery was incomplete")
    return _parse_codex_model_catalog(result.stdout)


def discover_cli_models(
    transport: str,
    *,
    refresh: bool = False,
    timeout: float = 15.0,
    resolver: BinaryResolver = shutil.which,
    runner: ProcessRunner = run_bounded_process,
    environ: Mapping[str, str] | None = None,
) -> CLIModelCatalog:
    """Discover account-visible models with bounded cache and singleflight."""

    normalized = str(transport or "").strip().casefold()
    if normalized not in SUPPORTED_CLI_TRANSPORTS:
        return _model_catalog_error(normalized, "unsupported CLI transport")
    if not _valid_timeout(timeout):
        return _model_catalog_error(normalized, "model discovery timeout is invalid")
    now = time.monotonic()
    with _MODEL_CATALOG_CONDITION:
        cached = _MODEL_CATALOG_CACHE.get(normalized)
        if not refresh and cached is not None and cached[0] > now:
            value = cached[1]
            return CLIModelCatalog(
                transport=value.transport,
                models=value.models,
                source=value.source,
                observed_at=value.observed_at,
                stale=value.stale,
                error=value.error,
                cache_hit=True,
            )
        deadline = now + float(timeout)
        while normalized in _MODEL_CATALOG_IN_FLIGHT:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _model_catalog_error(normalized, "model discovery is already in progress")
            _MODEL_CATALOG_CONDITION.wait(timeout=remaining)
            cached = _MODEL_CATALOG_CACHE.get(normalized)
            if cached is not None and cached[0] > time.monotonic():
                value = cached[1]
                return CLIModelCatalog(
                    transport=value.transport,
                    models=value.models,
                    source=value.source,
                    observed_at=value.observed_at,
                    stale=value.stale,
                    error=value.error,
                    cache_hit=True,
                )
        _MODEL_CATALOG_IN_FLIGHT.add(normalized)
    try:
        catalog = _discover_cli_models_uncached(
            normalized,
            timeout=float(timeout),
            resolver=resolver,
            runner=runner,
            environ=environ,
        )
    finally:
        with _MODEL_CATALOG_CONDITION:
            if "catalog" in locals():
                _MODEL_CATALOG_CACHE[normalized] = (
                    time.monotonic() + _MODEL_CATALOG_CACHE_SECONDS,
                    catalog,
                )
            _MODEL_CATALOG_IN_FLIGHT.discard(normalized)
            _MODEL_CATALOG_CONDITION.notify_all()
    return catalog


def _parse_codex(
    stdout: str,
    *,
    allow_completed_item_without_turn: bool = False,
) -> dict[str, Any] | None:
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
    turn_completed = any(event.get("type") == "turn.completed" for event in events)
    last_item_completed = bool(
        events
        and events[-1].get("type") == "item.completed"
        and isinstance(events[-1].get("item"), dict)
        and events[-1]["item"].get("type") == "agent_message"
    )
    if not turn_completed and not (allow_completed_item_without_turn and last_item_completed):
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


def _cli_schema(value: object) -> object:
    """Project only the one assertion unsupported by Codex output schemas."""

    if isinstance(value, Mapping):
        return {str(key): _cli_schema(item) for key, item in value.items() if key != "uniqueItems"}
    if isinstance(value, list):
        return [_cli_schema(item) for item in value]
    return value


def _codex_reasoning_effort(provider: ProviderEntry, transport: str) -> str | None:
    """Return a normalized safe override, or None when the provider is invalid."""

    effort = provider.reasoning_effort.strip().lower()
    if not effort:
        return ""
    if transport != "codex" or effort not in CODEX_REASONING_EFFORTS:
        return None
    return effort


def _valid_structured_cli_request(
    provider: ProviderEntry,
    transport: str,
    reasoning_effort: str | None,
    timeout: float,
    schema: object,
) -> bool:
    """Keep transport validation out of the already branch-heavy invocation path."""

    return (
        provider.type.strip().lower() == "cli"
        and transport in SUPPORTED_CLI_TRANSPORTS
        and is_safe_cli_model_id(provider.model)
        and _valid_timeout(timeout)
        and isinstance(schema, Mapping)
        and reasoning_effort is not None
    )


def _codex_reasoning_arguments(effort: str | None) -> list[str]:
    """Project one already-validated effort into inert argv data."""

    if not effort:
        return []
    return ["-c", f'model_reasoning_effort="{effort}"']


def _valid_investigation_options(
    transport: str,
    tools: Sequence[str],
    max_turns: int | None,
    read_only_roots: Sequence[str | Path],
) -> bool:
    """Bound the AR-361 read-only investigation options before they reach argv.

    Only the three read-only Claude Code tools may be granted, every extra root
    must be an existing absolute directory, and Codex accepts neither: its
    shell tool stays off, so a Codex verifier judges inlined excerpts only
    instead of silently downgrading a tool request.
    """

    if isinstance(tools, str) or isinstance(read_only_roots, (str, Path)):
        return False
    tool_names = list(tools)
    roots = list(read_only_roots)
    if transport == "codex" and (tool_names or roots):
        return False
    if any(not isinstance(name, str) or name not in _READ_ONLY_CLI_TOOLS for name in tool_names):
        return False
    if len(set(tool_names)) != len(tool_names) or (roots and not tool_names):
        return False
    if max_turns is not None and (
        isinstance(max_turns, bool)
        or not isinstance(max_turns, int)
        or not 1 <= max_turns <= _MAX_CLI_TURNS
    ):
        return False
    if len(roots) > _MAX_CLI_READ_ONLY_ROOTS:
        return False
    for root in roots:
        try:
            candidate = Path(root)
        except TypeError:
            return False
        if not candidate.is_absolute() or "\x00" in str(candidate) or not candidate.is_dir():
            return False
    return True


def _codex_structured_arguments(
    schema_path: Path,
    provider: ProviderEntry,
    reasoning_effort: str | None,
) -> list[str]:
    """Build the ephemeral read-only Codex exec argv for one structured call."""

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
    arguments.extend(_codex_reasoning_arguments(reasoning_effort))
    arguments.append("-")
    return arguments


def _claude_structured_arguments(
    schema_json: str,
    provider: ProviderEntry,
    *,
    tools: Sequence[str],
    max_turns: int | None,
    read_only_roots: Sequence[str | Path],
) -> list[str]:
    """Build the safe-mode, session-free Claude argv for one structured call."""

    arguments = [
        "--safe-mode",
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
        # Structured output arrives via a forced tool call; models sometimes
        # emit one or two text turns first, which a hard 1-turn cap kills
        # mid-response (error_max_turns). Three turns tolerates the preamble
        # on large recruiter prompts while staying bounded and tool-free; an
        # investigating verifier (AR-361) asks for a bounded larger cap.
        "--max-turns",
        str(max_turns if max_turns is not None else 3),
        "--no-session-persistence",
    ]
    if tools:
        # AR-361: a read-only investigation toolset, confined by --restricted
        # to the private working directory and the explicit read-only roots.
        arguments.extend(["--tools=" + ",".join(tools), "--restricted"])
        for root in read_only_roots:
            arguments.extend(["--add-dir", str(root)])
    else:
        # "--tools ''" is the CLI's documented all-tools-off value, but the
        # owned-process runner rejects empty argv items; the =-joined spelling
        # parses identically and stays non-empty.
        arguments.append("--tools=")
    arguments.extend(
        [
            "--disallowedTools",
            "mcp__*",
            "--strict-mcp-config",
            "--permission-mode",
            "dontAsk",
        ]
    )
    if provider.model:
        arguments.extend(["--model", provider.model])
    return arguments


def invoke_cli_structured(
    provider: ProviderEntry,
    prompt: str,
    schema: Mapping[str, Any],
    *,
    timeout: float,
    system_prompt: str = "",
    resolver: BinaryResolver = shutil.which,
    runner: ProcessRunner = run_bounded_process,
    environ: Mapping[str, str] | None = None,
    tools: Sequence[str] = (),
    max_turns: int | None = None,
    read_only_roots: Sequence[str | Path] = (),
) -> dict[str, Any] | None:
    """Invoke one supported CLI provider with an explicit bounded JSON schema.

    ``tools``, ``max_turns``, and ``read_only_roots`` are the AR-361 verifier
    options: a read-only investigation toolset over explicit snapshot roots.
    The defaults keep every existing caller tool-free and byte-identical.
    """

    transport = provider.transport.strip().lower()
    reasoning_effort = _codex_reasoning_effort(provider, transport)
    if not _valid_structured_cli_request(
        provider,
        transport,
        reasoning_effort,
        timeout,
        schema,
    ) or not _valid_investigation_options(transport, tools, max_turns, read_only_roots):
        return None
    timeout = float(timeout)
    if not isinstance(prompt, str) or not isinstance(system_prompt, str):
        return None
    effective_prompt = (
        f"{system_prompt}\n\n[UNTRUSTED REQUEST DATA]\n{prompt}"
        if system_prompt.strip()
        else prompt
    )
    try:
        invalid_prompt = (
            not effective_prompt.strip()
            or "\x00" in effective_prompt
            or len(effective_prompt.encode("utf-8")) > _MAX_CLI_PROMPT_BYTES
        )
    except UnicodeError:
        return None
    if invalid_prompt:
        return None

    try:
        schema_json = json.dumps(
            _cli_schema(dict(schema)),
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
                arguments = _codex_structured_arguments(schema_path, provider, reasoning_effort)
            else:
                arguments = _claude_structured_arguments(
                    schema_json,
                    provider,
                    tools=tools,
                    max_turns=max_turns,
                    read_only_roots=read_only_roots,
                )

            argv = _prepared_cli_command(executable, *arguments)
            execution_env = _isolated_invocation_environment(transport, cwd, environ)
            timeout = require_provider_time(timeout)

            result = runner(
                argv,
                timeout=timeout,
                cwd=cwd,
                env=execution_env,
                input_text=effective_prompt,
                max_output_chars=_MAX_CLI_OUTPUT_CHARS,
            )
    except Exception:
        return None
    if result.stdout_truncated or result.stderr_truncated:
        return None
    if result.timed_out:
        return (
            _parse_codex(result.stdout, allow_completed_item_without_turn=True)
            if transport == "codex"
            else None
        )
    if result.returncode != 0:
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
    "CLIModelCatalog",
    "CLIModelInfo",
    "CLIProviderStatus",
    "discover_cli_models",
    "inspect_cli_transport",
    "invoke_cli_judge",
    "invoke_cli_structured",
    "safe_cli_environment",
]
