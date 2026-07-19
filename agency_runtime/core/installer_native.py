"""Host discovery, native process execution, and installation inspection."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.installer_contracts import (
    HOSTS,
    MARKETPLACE_ID,
    MAX_NATIVE_OUTPUT_CHARS,
    PLUGIN_ID,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
)


def _facade():
    """Resolve the facade lazily so invocation-time monkeypatches stay effective."""

    from agency_runtime.core import installer

    return installer


def _home_path(*args: Any, **kwargs: Any) -> Path:
    return _facade()._home_path(*args, **kwargs)


def _host_root(*args: Any, **kwargs: Any) -> Path:
    return _facade()._host_root(*args, **kwargs)


def _resolve_binary(*args: Any, **kwargs: Any) -> str | None:
    return _facade()._resolve_binary(*args, **kwargs)


def _root_state(*args: Any, **kwargs: Any) -> tuple[bool, bool, list[str]]:
    return _facade()._root_state(*args, **kwargs)


def _is_host_installed(*args: Any, **kwargs: Any) -> bool:
    return _facade()._is_host_installed(*args, **kwargs)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _explicit_home(home_dir: str | Path | None) -> Path | None:
    return Path(home_dir).expanduser().resolve() if home_dir is not None else None


def home_path(path_template: str, *, home_dir: str | Path | None = None) -> Path:
    """Resolve ``~`` while enforcing an explicit test/operator home boundary."""
    home = _explicit_home(home_dir)
    if home is None:
        return Path(os.path.expanduser(path_template)).resolve()
    if path_template == "~":
        return home
    if path_template.startswith(("~/", "~\\")):
        candidate = (home / path_template[2:]).resolve()
        if not candidate.is_relative_to(home):
            raise ValueError(f"host path escapes explicit home boundary: {path_template}")
        return candidate
    candidate = Path(path_template).expanduser().resolve()
    if not candidate.is_relative_to(home):
        raise ValueError(f"absolute path escapes explicit home boundary: {path_template}")
    return candidate


def host_root(host: str, *, home_dir: str | Path | None = None) -> Path:
    explicit = _explicit_home(home_dir)
    if explicit is None:
        override = {
            "hermes": "HERMES_HOME",
            "openclaw": "OPENCLAW_HOME",
            "codex": "CODEX_HOME",
            "claude": "CLAUDE_CONFIG_DIR",
        }.get(host)
        if override and os.environ.get(override):
            return Path(os.environ[override]).expanduser().resolve()
    return _home_path(str(HOSTS[host]["root"]), home_dir=home_dir)


def runtime_home(*, home_dir: str | Path | None = None) -> Path:
    if home_dir is None and os.environ.get("AGENCY_HOME"):
        return Path(os.environ["AGENCY_HOME"]).expanduser().resolve()
    return _home_path("~/.agency-runtime", home_dir=home_dir)


def plugin_target(host: str, *, home_dir: str | Path | None = None) -> Path:
    # Hermes defines HERMES_HOME as the authoritative configuration/plugin
    # root.  Resolving its plugin target through ``~`` would silently ignore a
    # custom HERMES_HOME while discovery and command execution used it.
    if host == "hermes":
        return (_host_root(host, home_dir=home_dir) / "plugins" / PLUGIN_ID).resolve()
    return _home_path(str(HOSTS[host]["plugin_dir"]), home_dir=home_dir)


def _host_evidence_paths(host: str, *, home_dir: str | Path | None = None) -> list[Path]:
    root = _host_root(host, home_dir=home_dir)
    paths = [root]
    paths.extend(root / marker for marker in HOSTS[host].get("current_markers", []))
    if host == "hermes":
        # Native Windows installs place their executable/runtime payload here,
        # while user configuration and plugins remain under ~/.hermes.
        if home_dir is not None:
            paths.append(_explicit_home(home_dir) / "AppData" / "Local" / "hermes")  # type: ignore[operator]
        elif os.environ.get("LOCALAPPDATA"):
            paths.append(Path(os.environ["LOCALAPPDATA"]) / "hermes")
    return paths


def resolve_binary(host: str, resolver: BinaryResolver | None = None) -> str | None:
    return (resolver or shutil.which)(str(HOSTS[host]["binary"]))


def root_state(host: str, *, home_dir: str | Path | None = None) -> tuple[bool, bool, list[str]]:
    root = _host_root(host, home_dir=home_dir)
    # The first evidence path is the config root itself; remaining paths are
    # current-state markers, including Hermes' native Windows payload root.
    markers = _host_evidence_paths(host, home_dir=home_dir)[1:]
    marker_hits = [str(path) for path in markers if path.exists()]
    return root.exists(), bool(marker_hits), marker_hits


def is_host_installed(
    host_name: str,
    host_info: Mapping[str, Any] | None = None,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
) -> bool:
    """Return true for an executable or a current native state marker.

    A bare historical config directory is deliberately not enough.  Explicit
    installation still allows staging against a bare root, but ``--all`` uses
    this conservative predicate so stale directories are not mutated.
    """
    del host_info
    executable = _resolve_binary(host_name, binary_resolver)
    _root_exists, current_root, _markers = _root_state(host_name, home_dir=home_dir)
    return bool(executable or current_root)


def detect_installed_agents(
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
) -> list[str]:
    """Detect hosts safe for automatic installation.

    The result is derived from executable discovery or current native state
    markers.  Bare/stale directories remain visible through
    :func:`inspect_host_installations` but are excluded here.
    """
    return [
        host
        for host in HOSTS
        if _is_host_installed(host, home_dir=home_dir, binary_resolver=binary_resolver)
    ]


def _command_environment(host: str, *, home_dir: str | Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    explicit = _explicit_home(home_dir)
    if explicit is not None:
        env["HOME"] = str(explicit)
        env["USERPROFILE"] = str(explicit)
        env["HERMES_HOME"] = str(explicit / ".hermes")
        # OpenClaw treats OPENCLAW_HOME as the user-home root and derives its
        # default state directory as <OPENCLAW_HOME>/.openclaw.
        env["OPENCLAW_HOME"] = str(explicit)
        env["CODEX_HOME"] = str(explicit / ".codex")
        env["CLAUDE_CONFIG_DIR"] = str(explicit / ".claude")
    return env


def prepare_native_argv(
    argv: Sequence[str],
    *,
    platform_name: str | None = None,
    resolver: BinaryResolver | None = None,
    system_resolver: BinaryResolver | None = None,
) -> list[str]:
    """Compatibility wrapper around the shared fail-closed resolver."""

    return _facade().prepare_process_argv(
        argv,
        platform_name=platform_name,
        resolver=resolver,
        system_resolver=system_resolver,
    )


def owned_process_kwargs(*, platform_name: str | None = None) -> dict[str, Any]:
    """Return Popen flags that give Agency Runtime a killable process group."""
    if (platform_name or os.name) == "nt":
        return {
            "creationflags": (
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
                | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            )
        }
    return {"start_new_session": True}


def _bounded_native_text(value: Any) -> tuple[str, bool]:
    text = str(value or "")
    if len(text) <= MAX_NATIVE_OUTPUT_CHARS:
        return text, False
    return text[:MAX_NATIVE_OUTPUT_CHARS], True


def run_native(
    command: Sequence[str],
    *,
    host: str,
    home_dir: str | Path | None = None,
    command_runner: CommandRunner | None = None,
    timeout: float = 30.0,
) -> NativeCommandResult:
    argv = tuple(str(part) for part in command)
    env = _command_environment(host, home_dir=home_dir)
    try:
        if command_runner is None:
            from agency_runtime.core.delegation.backends import run_bounded_process

            bounded = run_bounded_process(
                argv,
                timeout=timeout,
                env=env,
                max_output_chars=MAX_NATIVE_OUTPUT_CHARS,
            )
            stderr = bounded.stderr
            if bounded.timed_out:
                stderr = "\n".join(
                    part
                    for part in (
                        stderr.strip(),
                        f"timed out after {timeout:g}s and terminated the owned process tree",
                    )
                    if part
                )
            elif bounded.stdout_truncated or bounded.stderr_truncated:
                stderr = "\n".join(
                    part
                    for part in (
                        stderr.strip(),
                        "native command output exceeded the capture limit",
                    )
                    if part
                )
            raw = NativeCommandResult(
                argv,
                bounded.returncode,
                bounded.stdout,
                stderr,
                bounded.stdout_truncated,
                bounded.stderr_truncated,
            )
        else:
            try:
                raw = command_runner(list(argv), env=env, timeout=timeout)
            except TypeError:
                raw = command_runner(list(argv))
    except OSError as exc:
        return NativeCommandResult(argv, 127, "", f"{type(exc).__name__}: {exc}")

    if isinstance(raw, NativeCommandResult):
        stdout, stdout_truncated = _bounded_native_text(raw.stdout)
        stderr, stderr_truncated = _bounded_native_text(raw.stderr)
        return NativeCommandResult(
            argv,
            raw.returncode,
            stdout,
            stderr,
            raw.stdout_truncated or stdout_truncated,
            raw.stderr_truncated or stderr_truncated,
        )
    if isinstance(raw, Mapping):
        stdout, stdout_truncated = _bounded_native_text(raw.get("stdout", ""))
        stderr, stderr_truncated = _bounded_native_text(raw.get("stderr", raw.get("error", "")))
        return NativeCommandResult(
            argv,
            int(raw.get("returncode", raw.get("exit_code", 0))),
            stdout,
            stderr,
            bool(raw.get("stdout_truncated")) or stdout_truncated,
            bool(raw.get("stderr_truncated")) or stderr_truncated,
        )
    stdout, stdout_truncated = _bounded_native_text(getattr(raw, "stdout", ""))
    stderr, stderr_truncated = _bounded_native_text(getattr(raw, "stderr", ""))
    return NativeCommandResult(
        argv,
        int(getattr(raw, "returncode", 0)),
        stdout,
        stderr,
        bool(getattr(raw, "stdout_truncated", False)) or stdout_truncated,
        bool(getattr(raw, "stderr_truncated", False)) or stderr_truncated,
    )


def _json_output(result: NativeCommandResult) -> Any:
    if not result.stdout.strip():
        return None
    try:
        return safe_load_bounded_json(
            result.stdout,
            maximum_bytes=MAX_NATIVE_OUTPUT_CHARS,
            maximum_depth=64,
            maximum_nodes=50_000,
        )
    except (TypeError, ValueError):
        return None


def _walk_objects(value: Any) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if isinstance(value, dict):
        objects.append(value)
        for child in value.values():
            objects.extend(_walk_objects(child))
    elif isinstance(value, list):
        for child in value:
            objects.extend(_walk_objects(child))
    return objects


def _plugin_record(value: Any) -> dict[str, Any] | None:
    for item in _walk_objects(value):
        identity = str(
            item.get("pluginId")
            or item.get("id")
            or item.get("name")
            or item.get("plugin")
            or item.get("pluginName")
            or ""
        ).lower()
        if identity == PLUGIN_ID or identity.startswith(f"{PLUGIN_ID}@"):
            return item
    return None


def _hermes_text_plugin_record(text: str) -> dict[str, Any] | None:
    """Parse only Hermes' Agency Runtime inventory row.

    Hermes' human-readable inventory can contain status words for many
    plugins.  Looking for ``enabled`` in the complete output lets an unrelated
    plugin manufacture Agency Runtime's enabled state, so status is derived
    exclusively from the line containing the exact plugin id.
    """
    identity = re.compile(
        rf"(?<![A-Za-z0-9_-]){re.escape(PLUGIN_ID)}(?![A-Za-z0-9_-])", re.IGNORECASE
    )
    for raw_line in text.splitlines():
        if not identity.search(raw_line):
            continue
        line = raw_line.casefold()
        record: dict[str, Any] = {"id": PLUGIN_ID}
        if re.search(r"\bdisabled\b", line):
            record["enabled"] = False
        elif re.search(r"\benabled\b", line):
            record["enabled"] = True
        return record
    return None


def _marketplace_registered(value: Any) -> bool:
    for item in _walk_objects(value):
        name = str(item.get("name") or item.get("marketplace") or item.get("id") or "").lower()
        if name == MARKETPLACE_ID:
            return True
    return False


def _bool_field(record: Mapping[str, Any] | None, *keys: str) -> bool | None:
    if record is None:
        return None
    for key in keys:
        if key in record:
            value = record[key]
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "yes", "enabled", "active", "loaded", "ok"}:
                    return True
                if lowered in {
                    "false",
                    "no",
                    "disabled",
                    "inactive",
                    "unloaded",
                    "error",
                }:
                    return False
    return None


def _can_execute_native(
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> bool:
    # An explicit home without an injected runner is a fixture/smoke boundary.
    return home_dir is None or command_runner is not None
