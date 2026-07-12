"""Native host discovery, installation, inspection, and rollback.

Agency Runtime integrates with each supported host through that host's public
plugin lifecycle.  Files are staged atomically and owned by a small manifest;
registration, enablement, and runtime loading are reported as separate facts.

All mutating entry points accept ``home_dir``.  Passing an explicit home pins
every write below that directory and suppresses real host commands unless a
``command_runner`` is also injected.  This is the safety boundary used by the
test and smoke suites.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import platform
import re
import shlex
import shutil
import subprocess
import sqlite3
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.process_argv import prepare_process_argv
from agency_runtime.core.store.sqlite import Store, _default_db_path


PLUGIN_ID = "agency-preflight"
MARKETPLACE_ID = "agency-runtime"
INSTALL_MANIFEST = ".agency-runtime-install.json"
PLUGIN_VERSION = "0.1.0"
HOOK_TIMEOUT_BUFFER_SECONDS = 5.0
MAX_NATIVE_OUTPUT_CHARS = 256 * 1024


# ``HOSTS`` intentionally stays JSON-like because the dashboard and downstream
# callers treat it as public inventory metadata.
HOSTS: dict[str, dict[str, Any]] = {
    "hermes": {
        "binary": "hermes",
        "root": "~/.hermes",
        "current_markers": ["config.yaml", "config.yml"],
        "plugin_dir": "~/.hermes/plugins/agency-preflight",
        "native_lifecycle": "hermes plugins",
    },
    "openclaw": {
        "binary": "openclaw",
        "root": "~/.openclaw",
        "current_markers": ["openclaw.json", "state.db", "state.sqlite"],
        "plugin_dir": "~/.agency-runtime/host-plugins/openclaw/agency-preflight",
        "native_lifecycle": "openclaw plugins",
    },
    "codex": {
        "binary": "codex",
        "root": "~/.codex",
        "current_markers": ["config.toml", "auth.json", "state_5.sqlite"],
        "plugin_dir": "~/.agency-runtime/marketplaces/codex",
        "native_lifecycle": "codex plugin",
    },
    "claude": {
        "binary": "claude",
        "root": "~/.claude",
        "current_markers": ["settings.json", ".credentials.json", "plugins/known_marketplaces.json"],
        "plugin_dir": "~/.agency-runtime/marketplaces/claude",
        "native_lifecycle": "claude plugin",
    },
}


BinaryResolver = Callable[[str], str | None]
CommandRunner = Callable[..., Any]


@dataclass(frozen=True)
class NativeCommandResult:
    """Normalized result from an injected or real native host command."""

    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def ok(self) -> bool:
        return (
            self.returncode == 0
            and not self.stdout_truncated
            and not self.stderr_truncated
        )

    def to_dict(self, *, expose_output: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "command": list(self.command),
            "returncode": self.returncode,
            "ok": self.ok,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
        }
        if expose_output:
            result["stdout"] = self.stdout
            result["stderr"] = self.stderr
        elif not self.ok:
            result["error"] = (self.stderr or self.stdout or "native command failed").strip()[:500]
        return result


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def _explicit_home(home_dir: str | Path | None) -> Path | None:
    return Path(home_dir).expanduser().resolve() if home_dir is not None else None


def _home_path(path_template: str, *, home_dir: str | Path | None = None) -> Path:
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


# Backward-compatible private name used by earlier tests and callers.
_host_path = _home_path


def _host_root(host: str, *, home_dir: str | Path | None = None) -> Path:
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


def _runtime_home(*, home_dir: str | Path | None = None) -> Path:
    if home_dir is None and os.environ.get("AGENCY_HOME"):
        return Path(os.environ["AGENCY_HOME"]).expanduser().resolve()
    return _home_path("~/.agency-runtime", home_dir=home_dir)


def _plugin_target(host: str, *, home_dir: str | Path | None = None) -> Path:
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


def _resolve_binary(host: str, resolver: BinaryResolver | None = None) -> str | None:
    return (resolver or shutil.which)(str(HOSTS[host]["binary"]))


def _root_state(host: str, *, home_dir: str | Path | None = None) -> tuple[bool, bool, list[str]]:
    root = _host_root(host, home_dir=home_dir)
    # The first evidence path is the config root itself; remaining paths are
    # current-state markers, including Hermes' native Windows payload root.
    markers = _host_evidence_paths(host, home_dir=home_dir)[1:]
    marker_hits = [str(path) for path in markers if path.exists()]
    return root.exists(), bool(marker_hits), marker_hits


def _is_host_installed(
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
        env["OPENCLAW_HOME"] = str(explicit / ".openclaw")
        env["CODEX_HOME"] = str(explicit / ".codex")
        env["CLAUDE_CONFIG_DIR"] = str(explicit / ".claude")
    return env


def _prepare_process_argv(
    argv: Sequence[str],
    *,
    platform_name: str | None = None,
    resolver: BinaryResolver | None = None,
) -> list[str]:
    """Compatibility wrapper around the shared fail-closed resolver."""

    return prepare_process_argv(
        argv,
        platform_name=platform_name,
        resolver=resolver,
    )


def _owned_process_kwargs(*, platform_name: str | None = None) -> dict[str, Any]:
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


def _run_native(
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
                        f"timed out after {timeout:g}s and terminated "
                        "the owned process tree",
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
        stderr, stderr_truncated = _bounded_native_text(
            raw.get("stderr", raw.get("error", ""))
        )
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
        return json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
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
    identity = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(PLUGIN_ID)}(?![A-Za-z0-9_-])", re.IGNORECASE)
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
                if lowered in {"false", "no", "disabled", "inactive", "unloaded", "error"}:
                    return False
    return None


def _can_execute_native(
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> bool:
    # An explicit home without an injected runner is a fixture/smoke boundary.
    return home_dir is None or command_runner is not None


def _inventory_command(host: str) -> list[str]:
    binary = str(HOSTS[host]["binary"])
    if host == "hermes":
        return [binary, "plugins", "list"]
    if host == "openclaw":
        return [binary, "plugins", "list", "--json"]
    return [binary, "plugin", "list", "--json"]


def _read_canary_attestation(host: str) -> dict[str, Any] | None:
    """Read a canary attestation without creating or migrating the database."""
    path = _default_db_path()
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'host_canary_attestations'"
            ).fetchone()
            if table is None:
                return None
            row = conn.execute(
                "SELECT host, profile_scope, platform_system, platform_release, platform_machine, "
                "host_version, plugin_version, install_id, bundle_digest, "
                "passed_at, trace_id "
                "FROM host_canary_attestations WHERE host = ?",
                (host,),
            ).fetchone()
            return dict(row) if row is not None else None
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None


def _invalidate_canary_attestation(
    host: str,
    *,
    home_dir: str | Path | None,
) -> bool:
    """Invalidate durable proof after a rollback changes the install lineage."""
    if home_dir is not None and "AGENCY_DB_PATH" not in os.environ:
        return False
    path = _default_db_path()
    if not path.is_file():
        return False
    try:
        return Store(path).clear_host_canary_attestation(host)
    except Exception:
        return False


def _managed_bundle_identity(
    target: Path,
    host: str,
) -> tuple[str | None, str | None, str | None]:
    try:
        manifest = json.loads((target / INSTALL_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, None, None
    if not isinstance(manifest, dict):
        return None, None, None
    if (
        manifest.get("owner") != "agency-runtime"
        or manifest.get("host") != host
        or manifest.get("plugin_id") != PLUGIN_ID
    ):
        return None, None, None
    version = manifest.get("plugin_version")
    install_id = manifest.get("install_id")
    owned_files = manifest.get("owned_files")
    if not isinstance(owned_files, list) or not all(
        isinstance(item, str) for item in owned_files
    ):
        return (
            str(version) if isinstance(version, str) and version else None,
            str(install_id) if isinstance(install_id, str) and install_id else None,
            None,
        )
    digest = hashlib.sha256()
    total_bytes = 0
    try:
        for relative in sorted(owned_files):
            candidate = Path(relative)
            if candidate.is_absolute() or ".." in candidate.parts:
                return None, None, None
            payload = (target / candidate).read_bytes()
            total_bytes += len(payload)
            if total_bytes > 8 * 1024 * 1024:
                return None, None, None
            digest.update(relative.replace("\\", "/").encode("utf-8"))
            digest.update(b"\0")
            digest.update(payload)
            digest.update(b"\0")
    except OSError:
        return None, None, None
    return (
        str(version) if isinstance(version, str) and version else None,
        str(install_id) if isinstance(install_id, str) and install_id else None,
        digest.hexdigest(),
    )


def _sanitize_host_version(result: NativeCommandResult) -> str | None:
    """Return one bounded printable version line from an allowlisted probe."""
    if not result.ok:
        return None
    raw = result.stdout.strip() or result.stderr.strip()
    line = next((part.strip() for part in raw.splitlines() if part.strip()), "")
    if not line or not re.search(r"\d", line):
        return None
    printable = re.sub(r"[^A-Za-z0-9 ._+:/()\[\]-]", "?", line)
    return printable[:256] or None


def _canary_attestation_state(
    host: str,
    *,
    target: Path,
    registered: bool | None,
    enabled: bool | None,
    native_record: dict[str, Any] | None,
    host_version: str | None,
    managed_version: str | None,
    install_id: str | None,
    bundle_digest: str | None,
    allow_read: bool,
) -> tuple[bool | None, str, list[str], dict[str, Any] | None]:
    attestation = _read_canary_attestation(host) if allow_read else None
    if attestation is None:
        return None, "absent", [], None
    expected_platform = {
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
    }
    stale: list[str] = []
    if attestation.get("profile_scope") != "current-profile":
        stale.append("profile_scope")
    for field, expected in expected_platform.items():
        if attestation.get(field) != expected:
            stale.append(field)
    if not host_version or attestation.get("host_version") != host_version:
        stale.append("host_version")
    if attestation.get("plugin_version") != PLUGIN_VERSION:
        stale.append("plugin_version")
    if managed_version != PLUGIN_VERSION:
        stale.append("managed_plugin_version")
    if not install_id or attestation.get("install_id") != install_id:
        stale.append("install_id")
    if not bundle_digest or attestation.get("bundle_digest") != bundle_digest:
        stale.append("bundle_digest")
    native_version = (
        str(native_record.get("version") or native_record.get("pluginVersion") or "")
        if native_record
        else ""
    )
    if native_version and native_version != PLUGIN_VERSION:
        stale.append("native_plugin_version")
    if registered is not True or enabled is not True:
        stale.append("native_state")
    if stale:
        return None, "stale", sorted(set(stale)), attestation
    return True, "verified", [], attestation


def inspect_host_installations(
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    probe_runtime: bool = False,
    hosts: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return evidence-separated installation status for every host.

    ``loaded`` and ``canary`` are ``None`` unless a native runtime surface can
    prove them.  Staged files never count as native registration.
    """
    requested = set(HOSTS) if hosts is None else {str(host) for host in hosts}
    unknown = sorted(requested.difference(HOSTS))
    if unknown:
        raise ValueError(f"Unknown host(s): {', '.join(unknown)}")
    # Preserve the canonical HOSTS order even when callers provide a set or a
    # differently ordered iterable.  This makes parallel fan-out deterministic.
    selected_hosts = [host for host in HOSTS if host in requested]

    inspections: list[dict[str, Any]] = []
    can_execute = _can_execute_native(home_dir=home_dir, command_runner=command_runner)

    for host in selected_hosts:
        root = _host_root(host, home_dir=home_dir)
        target = _plugin_target(host, home_dir=home_dir)
        executable = _resolve_binary(host, binary_resolver)
        root_exists, current_root, marker_hits = _root_state(host, home_dir=home_dir)
        stale_config = bool(root_exists and not executable and not current_root)
        owned_manifest = target / INSTALL_MANIFEST
        staged = owned_manifest.exists()
        managed_version, install_id, bundle_digest = _managed_bundle_identity(
            target,
            host,
        )
        native_record: dict[str, Any] | None = None
        inventory_result: NativeCommandResult | None = None
        registered: bool | None = None
        enabled: bool | None = None
        loaded: bool | None = None
        canary: bool | None = None
        marketplace_registered: bool | None = None
        evidence: list[str] = []
        host_version: str | None = None

        if executable:
            evidence.append(f"executable:{executable}")
        evidence.extend(f"native-marker:{path}" for path in marker_hits)
        if stale_config:
            evidence.append(f"stale-root:{root}")
        if staged:
            evidence.append(f"owned-stage:{owned_manifest}")

        if executable and can_execute:
            version_result = _run_native(
                [str(HOSTS[host]["binary"]), "--version"],
                host=host,
                home_dir=home_dir,
                command_runner=command_runner,
                timeout=8,
            )
            host_version = _sanitize_host_version(version_result)
            evidence.append(
                f"host-version:{'proven' if host_version else 'unproven'}"
            )
            inventory_result = _run_native(
                _inventory_command(host),
                host=host,
                home_dir=home_dir,
                command_runner=command_runner,
                timeout=12,
            )
            if inventory_result.ok:
                payload = _json_output(inventory_result)
                native_record = _plugin_record(payload)
                if host == "hermes" and payload is None:
                    native_record = _hermes_text_plugin_record(inventory_result.stdout)
                    registered = native_record is not None
                    enabled = _bool_field(native_record, "enabled")
                else:
                    registered = native_record is not None
                    enabled = _bool_field(native_record, "enabled", "active", "isEnabled")
                    loaded = _bool_field(native_record, "loaded", "runtimeLoaded", "isLoaded")
                evidence.append(f"native-inventory:{'registered' if registered else 'absent'}")
            else:
                evidence.append("native-inventory:error")

            if host in {"codex", "claude"}:
                market = _run_native(
                    [str(HOSTS[host]["binary"]), "plugin", "marketplace", "list", "--json"],
                    host=host,
                    home_dir=home_dir,
                    command_runner=command_runner,
                    timeout=12,
                )
                marketplace_registered = _marketplace_registered(_json_output(market)) if market.ok else None

            if host == "openclaw" and registered and probe_runtime:
                runtime = _run_native(
                    ["openclaw", "plugins", "inspect", PLUGIN_ID, "--runtime", "--json"],
                    host=host,
                    home_dir=home_dir,
                    command_runner=command_runner,
                    timeout=20,
                )
                runtime_payload = _json_output(runtime)
                runtime_record = _plugin_record(runtime_payload) or (
                    runtime_payload if isinstance(runtime_payload, dict) else None
                )
                loaded = (
                    _bool_field(runtime_record, "loaded", "runtimeLoaded", "isLoaded")
                    if runtime.ok
                    else None
                )
                runtime_state = "loaded" if loaded is True else "not-loaded" if loaded is False else "unproven"
                evidence.append(f"runtime-inspect:{runtime_state}")

        # A staged bundle is filesystem evidence only.  When no native
        # inventory could run, registration is known false for this install
        # surface; when inventory itself failed, retain unknown rather than
        # manufacturing either success or absence.
        if registered is None and not (executable and can_execute and inventory_result is not None):
            registered = False

        canary, canary_attestation_status, canary_stale_reasons, canary_attestation = (
            _canary_attestation_state(
                host,
                target=target,
                registered=registered,
                enabled=enabled,
                native_record=native_record,
                host_version=host_version,
                managed_version=managed_version,
                install_id=install_id,
                bundle_digest=bundle_digest,
                allow_read=home_dir is None or "AGENCY_DB_PATH" in os.environ,
            )
        )
        if canary_attestation_status != "absent":
            evidence.append(f"canary-attestation:{canary_attestation_status}")

        if registered is True and enabled is True and loaded is True:
            maturity = "runtime-verified"
        elif registered is True and enabled is True:
            maturity = "enabled-runtime-unverified"
        elif registered is True:
            maturity = "registered-enablement-unverified" if enabled is None else "registered-disabled"
        elif registered is None:
            maturity = "staged-registration-unverified" if staged else "host-registration-unverified"
        elif staged:
            maturity = "staged-not-registered"
        elif executable or current_root:
            maturity = "host-discovered"
        elif stale_config:
            maturity = "stale-config"
        else:
            maturity = "absent"

        inspections.append(
            {
                "host": host,
                "executable": executable,
                "executable_discovered": bool(executable),
                "native_root": str(root),
                "managed_target": str(target),
                "native_root_exists": root_exists,
                "current_native_root": current_root,
                "stale_config": stale_config,
                "discovered": bool(executable or current_root),
                "staged": staged,
                "registered": registered,
                "enabled": enabled,
                "loaded": loaded,
                "canary": canary,
                "canary_attestation_status": canary_attestation_status,
                "canary_stale_reasons": canary_stale_reasons,
                "canary_attestation": canary_attestation,
                "host_version": host_version,
                "managed_plugin_version": managed_version,
                "install_id": install_id,
                "bundle_digest": bundle_digest,
                "marketplace_registered": marketplace_registered,
                "maturity": maturity,
                "native_lifecycle": HOSTS[host]["native_lifecycle"],
                "evidence": evidence,
                "inventory_error": (
                    (inventory_result.stderr or inventory_result.stdout).strip()[:500]
                    if inventory_result is not None and not inventory_result.ok
                    else None
                ),
            }
        )
    return inspections


def inspect_host_installation(
    host: str,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    probe_runtime: bool = False,
) -> dict[str, Any]:
    """Inspect one host with the same evidence semantics as the bulk API."""
    return inspect_host_installations(
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
        probe_runtime=probe_runtime,
        hosts=(host,),
    )[0]


def _python_commands(module: str, *args: str) -> tuple[str, str]:
    executable = str(Path(sys.executable).resolve())
    posix = " ".join(shlex.quote(part) for part in (executable, "-m", module, *args))
    windows = subprocess.list2cmdline([executable, "-m", module, *args])
    return posix, windows


def _resolve_install_config(
    cfg: AgencyConfig | None,
    *,
    home_dir: str | Path | None,
) -> AgencyConfig:
    if cfg is not None:
        return cfg
    if home_dir is not None:
        return load_config(_runtime_home(home_dir=home_dir) / "agency.yaml", reload=True)
    return load_config(reload=True)


def _effective_judge_budget_seconds(cfg: AgencyConfig) -> float:
    """Conservatively bound the selector's sequential provider attempts."""
    budgets = [
        max(0.0, float(provider.timeout))
        for provider in cfg.providers
        if (
            provider.model
            and provider.base_url
            or (
                provider.type.strip().lower() == "cli"
                and provider.transport.strip().lower() in {"codex", "claude"}
            )
        )
    ]
    if cfg.judge.model and cfg.judge.base_url:
        budgets.append(max(0.0, float(cfg.judge.timeout)))
    if cfg.ollama.enabled and cfg.ollama.model:
        budgets.append(max(0.0, float(cfg.judge.timeout)))
    return max(max(0.0, float(cfg.judge.timeout)), sum(budgets))


def _hook_timeout_seconds(cfg: AgencyConfig) -> int:
    return max(1, math.ceil(_effective_judge_budget_seconds(cfg) + HOOK_TIMEOUT_BUFFER_SECONDS))


def _mcp_config() -> dict[str, Any]:
    return {
        "mcpServers": {
            "agency-runtime": {
                "command": str(Path(sys.executable).resolve()),
                "args": ["-m", "agency_runtime.server.mcp", "--stdio"],
            }
        }
    }


def _codex_hooks(timeout_seconds: int) -> dict[str, Any]:
    command, command_windows = _python_commands("agency_runtime.cli", "hook", "codex")
    handler = {
        "type": "command",
        "command": command,
        "commandWindows": command_windows,
        "timeout": timeout_seconds,
        "statusMessage": "Routing with Agency Runtime",
    }
    observer = {**handler, "statusMessage": "Recording Agency Runtime evidence"}
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [handler]}],
            "PostToolUse": [{"matcher": "*", "hooks": [observer]}],
            "Stop": [{"hooks": [{**handler, "statusMessage": "Checking Agency Runtime response contract"}]}],
        }
    }


def _claude_hooks(timeout_seconds: int) -> dict[str, Any]:
    executable = str(Path(sys.executable).resolve())
    base = {
        "type": "command",
        "command": executable,
        "args": ["-m", "agency_runtime.cli", "hook", "claude"],
        "timeout": timeout_seconds,
    }
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [base]}],
            "PostToolUse": [{"matcher": "*", "hooks": [base]}],
            "PostToolUseFailure": [{"matcher": "*", "hooks": [base]}],
            "Stop": [{"hooks": [base]}],
        }
    }


def _agency_control_skill(host: str) -> str:
    """Build the host-aware conversation control skill for Codex and Claude."""
    return f"""---
name: agency
description: Inspect, enable, or disable Agency Runtime for this host.
---

# Agency Runtime control

Handle the conversation forms `agency status`, `agency on`, and `agency off`.
Some clients may present the same text with a leading slash; treat it as the
same request when the host routes it through this skill.

- For status, call `agency.host_status` with `host` set to `{host}`.
- For on, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `true`, and `confirm` set exactly to `ENABLE {host}`.
- For off, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `false`, and `confirm` set exactly to `DISABLE {host}`.

Report the returned soft-control state. Do not claim that native plugin
registration changed, and do not claim a live canary unless the returned
evidence explicitly proves one.
"""


_HERMES_PLUGIN = '''"""Agency Runtime native Hermes plugin (managed file)."""

from agency_runtime.adapters.hermes.plugin import HermesAdapter

_adapter = None


def _get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = HermesAdapter()
    return _adapter


def _pre_llm_call(**kwargs):
    trace_id = str(
        kwargs.get("turn_id")
        or kwargs.get("trace_id")
        or kwargs.get("task_id")
        or ""
    )
    return _get_adapter().pre_llm_call_handler(
        session_id=str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        user_message=str(kwargs.get("user_message") or ""),
        model=str(kwargs.get("model") or ""),
        trace_id=trace_id,
    )


def _post_tool_call(tool_name="", args=None, result=None, **kwargs):
    _get_adapter().post_tool_call_handler(
        tool_name=tool_name,
        args=args or {},
        result=result,
        session_id=str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        **{key: value for key, value in kwargs.items() if key not in {"session_id", "task_id"}},
    )


def _post_api_request(**kwargs):
    _get_adapter().post_api_request_handler(**kwargs)


def _transform_llm_output(response_text="", **kwargs):
    return _get_adapter().apply_finalization(
        response_text,
        str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        str(kwargs.get("model") or ""),
    )


def _agency_command(*args, **kwargs):
    raw_args = kwargs.get("args") or kwargs.get("raw_args") or ""
    if not raw_args:
        raw_args = next(
            (value for value in reversed(args) if isinstance(value, str)),
            "",
        )
    from agency_runtime.core.host_control import handle_host_control_command

    result = handle_host_control_command(
        "hermes",
        str(raw_args),
        store=_get_adapter().store,
        source="hermes-command",
    )
    return result["message"]


def register(ctx):
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("post_api_request", _post_api_request)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
    ctx.register_command("agency", _agency_command, description="Agency Runtime status, on, or off")
'''


def _openclaw_index(timeout_seconds: int) -> str:
    python = json.dumps(str(Path(sys.executable).resolve()))
    timeout_ms = timeout_seconds * 1000
    host_timeout_ms = (timeout_seconds + 2) * 1000
    return f'''import {{ definePluginEntry }} from "openclaw/plugin-sdk/plugin-entry";
import {{ execFile }} from "node:child_process";

const PYTHON = process.env.AGENCY_RUNTIME_PYTHON || {python};
const MODULE_ARGS = ["-m", "agency_runtime.adapters.openclaw.node_bridge"];

function invokeAgency(payload) {{
  return new Promise((resolve, reject) => {{
    const child = execFile(PYTHON, MODULE_ARGS, {{ timeout: {timeout_ms}, maxBuffer: 1024 * 1024 }}, (error, stdout, stderr) => {{
      if (error) {{
        reject(new Error((stderr || error.message || "Agency Runtime hook failed").trim()));
        return;
      }}
      try {{ resolve(JSON.parse(stdout || "{{}}")); }}
      catch (parseError) {{ reject(parseError); }}
    }});
    child.stdin.end(JSON.stringify(payload));
  }});
}}

function sessionId(event, ctx) {{
  return String(ctx?.sessionKey || ctx?.sessionId || event?.sessionKey || event?.sessionId || "");
}}

function traceId(event, ctx) {{
  return String(ctx?.turnId || event?.turnId || ctx?.runId || event?.runId || "");
}}

function modelId(ctx) {{
  return String(ctx?.modelId || ctx?.activeModel?.modelId || ctx?.model || "");
}}

function finalAssistantText(event) {{
  return String(event?.lastAssistantMessage || event?.finalAssistantText || event?.assistantText || event?.text || "");
}}

export default definePluginEntry({{
  id: "agency-preflight",
  name: "Agency Preflight",
  description: "Agency Runtime routing, evidence, and final-response enforcement.",
  register(api) {{
    api.registerCommand({{
      name: "agency",
      description: "Agency Runtime status, on, or off",
      acceptsArgs: true,
      requireAuth: true,
      handler: async (ctx) => {{
        const result = await invokeAgency({{
          action: "control",
          command: String(ctx?.args || "status"),
        }});
        return {{ text: String(result?.message || "Agency Runtime control completed.") }};
      }},
    }});

    api.on("before_prompt_build", async (event, ctx) => {{
      const result = await invokeAgency({{
        action: "preflight",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        userMessage: String(event?.prompt || ""),
        model: modelId(ctx),
      }});
      return result.context ? {{ appendContext: result.context }} : undefined;
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("after_tool_call", async (event, ctx) => {{
      await invokeAgency({{
        action: "post_tool_call",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        toolName: String(event?.toolName || ""),
        toolInput: event?.params || {{}},
        toolResult: event?.result,
        error: String(event?.error?.message || event?.error || ""),
      }});
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("before_agent_finalize", async (event, ctx) => {{
      const decision = await invokeAgency({{
        action: "pre_verify",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        finalResponse: finalAssistantText(event),
        model: modelId(ctx),
        attempt: Number(event?.attempt || 0),
      }});
      if (decision.action !== "continue") return undefined;
      return {{
        action: "revise",
        reason: String(decision.message || "Agency Runtime response contract is incomplete."),
        retry: {{
          instruction: String(decision.message || "Repair the Agency Runtime response contract."),
          idempotencyKey: "agency-preflight-header",
          maxAttempts: 2,
        }},
      }};
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});
  }},
}});
'''


def _bundle_files(host: str, cfg: AgencyConfig | None = None) -> tuple[dict[str, str], str]:
    description = "Agency Runtime specialist routing, delegation evidence, and operational tools."
    timeout_seconds = _hook_timeout_seconds(cfg or AgencyConfig())
    if host == "hermes":
        files = {
            "__init__.py": _HERMES_PLUGIN,
            "plugin.yaml": (
                f"name: {PLUGIN_ID}\n"
                f"version: \"{PLUGIN_VERSION}\"\n"
                f"description: {description}\n"
                "provides_hooks:\n"
                "  - pre_llm_call\n"
                "  - post_tool_call\n"
                "  - post_api_request\n"
                "  - transform_llm_output\n"
            ),
        }
        return files, "__init__.py"

    if host == "openclaw":
        files = {
            "index.js": _openclaw_index(timeout_seconds),
            "openclaw.plugin.json": json.dumps(
                {
                    "id": PLUGIN_ID,
                    "name": "Agency Preflight",
                    "description": description,
                    "activation": {"onStartup": True, "onCapabilities": ["hook"]},
                    "configSchema": {"type": "object", "additionalProperties": False, "properties": {}},
                },
                indent=2,
            )
            + "\n",
            "package.json": json.dumps(
                {
                    "name": "agency-preflight-openclaw",
                    "version": PLUGIN_VERSION,
                    "type": "module",
                    "private": True,
                    "openclaw": {"extensions": ["./index.js"]},
                },
                indent=2,
            )
            + "\n",
        }
        return files, "index.js"

    if host == "codex":
        plugin_prefix = f"plugins/{PLUGIN_ID}"
        manifest = {
            "name": PLUGIN_ID,
            "version": PLUGIN_VERSION,
            "description": description,
            "author": {"name": "Agency Runtime Contributors"},
            "license": "MIT",
            "keywords": ["routing", "delegation", "observability"],
            "mcpServers": "./.mcp.json",
            "interface": {
                "displayName": "Agency Runtime",
                "shortDescription": "Specialist routing and delegation evidence",
                "longDescription": description,
                "developerName": "Agency Runtime Contributors",
                "category": "Developer Tools",
                "capabilities": ["Read", "Write"],
                "defaultPrompt": (
                    "Use Agency Runtime for specialist routing, delegation evidence, "
                    "and auditable response finalization."
                ),
            },
        }
        marketplace = {
            "name": MARKETPLACE_ID,
            "interface": {"displayName": "Agency Runtime"},
            "plugins": [
                {
                    "name": PLUGIN_ID,
                    "source": {"source": "local", "path": f"./plugins/{PLUGIN_ID}"},
                    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                    "category": "Developer Tools",
                }
            ],
        }
        files = {
            ".agents/plugins/marketplace.json": json.dumps(marketplace, indent=2) + "\n",
            f"{plugin_prefix}/.codex-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
            f"{plugin_prefix}/hooks/hooks.json": json.dumps(_codex_hooks(timeout_seconds), indent=2) + "\n",
            f"{plugin_prefix}/.mcp.json": json.dumps(_mcp_config(), indent=2) + "\n",
            f"{plugin_prefix}/skills/agency/SKILL.md": _agency_control_skill("codex"),
        }
        return files, f"{plugin_prefix}/.codex-plugin/plugin.json"

    plugin_prefix = f"plugins/{PLUGIN_ID}"
    manifest = {
        "name": PLUGIN_ID,
        "displayName": "Agency Runtime",
        "version": PLUGIN_VERSION,
        "description": description,
        "author": {"name": "Agency Runtime Contributors"},
        "license": "MIT",
        "hooks": "./hooks/hooks.json",
        "mcpServers": "./.mcp.json",
    }
    marketplace = {
        "name": MARKETPLACE_ID,
        "owner": {"name": "Agency Runtime Contributors"},
        "plugins": [
            {
                "name": PLUGIN_ID,
                "source": f"./plugins/{PLUGIN_ID}",
                "description": description,
                "version": PLUGIN_VERSION,
            }
        ],
    }
    files = {
        ".claude-plugin/marketplace.json": json.dumps(marketplace, indent=2) + "\n",
        f"{plugin_prefix}/.claude-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
        f"{plugin_prefix}/hooks/hooks.json": json.dumps(_claude_hooks(timeout_seconds), indent=2) + "\n",
        f"{plugin_prefix}/.mcp.json": json.dumps(_mcp_config(), indent=2) + "\n",
        f"{plugin_prefix}/skills/agency/SKILL.md": _agency_control_skill("claude"),
    }
    return files, f"{plugin_prefix}/.claude-plugin/plugin.json"


def _safe_relative(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe generated file path: {path}")
    return candidate


def _atomic_install_tree(
    target: Path,
    files: Mapping[str, str],
    *,
    host: str,
    dry_run: bool,
    home_dir: str | Path | None,
) -> dict[str, Any]:
    owned_files = sorted(files)
    backup_path: Path | None = None
    plan = {
        "target": str(target),
        "owned_files": owned_files + [INSTALL_MANIFEST],
        "would_backup": target.exists(),
    }
    if dry_run:
        return plan

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=str(target.parent)))
    stamp = _utc_stamp()
    try:
        for relative, content in files.items():
            destination = stage / _safe_relative(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")

        if target.exists():
            backup_path = _runtime_home(home_dir=home_dir) / "backups" / host / stamp
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, backup_path)

        manifest = {
            "schema_version": 1,
            "owner": "agency-runtime",
            "host": host,
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "install_id": str(uuid.uuid4()),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "target": str(target),
            "owned_files": owned_files,
            "backup_path": str(backup_path) if backup_path else None,
        }
        (stage / INSTALL_MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(stage, target)
    except Exception:
        if target.exists() and not (target / INSTALL_MANIFEST).exists():
            shutil.rmtree(target, ignore_errors=True)
        if backup_path is not None and backup_path.exists() and not target.exists():
            os.replace(backup_path, target)
        shutil.rmtree(stage, ignore_errors=True)
        raise

    return {**plan, "backup_path": str(backup_path) if backup_path else None}


def _validate_owned_backup(
    path: Path,
    *,
    host: str,
    target: Path,
) -> tuple[bool, str | None, str | None]:
    """Validate that ``path`` is an Agency Runtime bundle for this target."""
    if not path.is_dir():
        return False, "Backup source is not a directory", None
    manifest_path = path / INSTALL_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False, "Backup does not contain an Agency Runtime ownership manifest", None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "Backup ownership manifest is unreadable or invalid", None
    if not isinstance(manifest, dict):
        return False, "Backup ownership manifest must be a JSON object", None

    expected = {
        "schema_version": 1,
        "owner": "agency-runtime",
        "host": host,
        "plugin_id": PLUGIN_ID,
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            return False, f"Backup ownership manifest has an unexpected {field}", None

    plugin_version = manifest.get("plugin_version")
    if not isinstance(plugin_version, str) or not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?",
        plugin_version,
    ):
        return False, "Backup ownership manifest has an invalid plugin_version", None

    manifest_target = manifest.get("target")
    if not isinstance(manifest_target, str) or not manifest_target.strip():
        return False, "Backup ownership manifest has no target", None
    try:
        recorded_target = Path(manifest_target).expanduser().resolve()
    except (OSError, RuntimeError):
        return False, "Backup ownership manifest target is invalid", None
    if recorded_target != target.resolve():
        return False, "Backup ownership manifest target does not match this host", None

    owned_files = manifest.get("owned_files")
    if not isinstance(owned_files, list) or not all(isinstance(item, str) for item in owned_files):
        return False, "Backup ownership manifest has an invalid owned_files list", None
    return True, None, plugin_version


def _openclaw_gateway_live(
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
) -> tuple[bool | None, NativeCommandResult]:
    """Return proven live/stopped state, or ``None`` when status is ambiguous."""
    probe = _run_native(
        ["openclaw", "gateway", "status", "--deep", "--require-rpc", "--json"],
        host="openclaw",
        home_dir=home_dir,
        command_runner=command_runner,
        timeout=12,
    )
    payload = _json_output(probe)
    if not probe.ok or not isinstance(payload, dict):
        return None, probe

    status = str(payload.get("status", "")).strip().lower()
    signals = {
        key: _bool_field(payload, key)
        for key in ("running", "reachable", "healthy", "rpcHealthy", "active")
    }
    if any(value is True for value in signals.values()) or status in {
        "running",
        "healthy",
        "ready",
        "online",
    }:
        return True, probe
    # Only an explicit process-state signal can prove the gateway stopped.
    # An unreachable or unhealthy gateway may still be a live process that a
    # plugin install would reload.
    if signals["running"] is False or status in {"stopped", "not-running", "not_running"}:
        return False, probe
    return None, probe


def _native_registration_steps(
    host: str,
    target: Path,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    force_refresh: bool = False,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    steps: list[dict[str, Any]] = []
    binary = str(HOSTS[host]["binary"])

    def run(name: str, command: Sequence[str], *, timeout: float = 30) -> NativeCommandResult:
        result = _run_native(
            command,
            host=host,
            home_dir=home_dir,
            command_runner=command_runner,
            timeout=timeout,
        )
        steps.append({"name": name, **result.to_dict()})
        return result

    if host == "hermes":
        enabled = run("enable", [binary, "plugins", "enable", PLUGIN_ID])
        verify = run("inventory", [binary, "plugins", "list"])
        if not enabled.ok:
            return steps, False, "enable"
        record = _hermes_text_plugin_record(verify.stdout) if verify.ok else None
        proven = record is not None and _bool_field(record, "enabled") is not False
        return steps, proven, None if proven else "inventory_unproven"

    if host == "openclaw":
        live, probe = _openclaw_gateway_live(home_dir=home_dir, command_runner=command_runner)
        gateway_state = "unknown" if live is None else "live" if live else "stopped"
        steps.append({"name": "gateway_status", "gateway_state": gateway_state, **probe.to_dict()})
        if live is None:
            return steps, False, "gateway_status_unproven"
        if live is True:
            return steps, False, "host_restart_consent_required"

        existing = run("inspect_existing", [binary, "plugins", "inspect", PLUGIN_ID, "--json"])
        install_command = [binary, "plugins", "install", str(target)]
        if existing.ok:
            install_command.append("--force")
        installed = run("install", install_command, timeout=60)
        if not installed.ok:
            return steps, False, "install"
        enabled = run("enable", [binary, "plugins", "enable", PLUGIN_ID])
        if not enabled.ok:
            return steps, False, "enable"
        access = run(
            "conversation_access",
            [
                binary,
                "config",
                "set",
                f"plugins.entries.{PLUGIN_ID}.hooks.allowConversationAccess",
                "true",
            ],
        )
        if not access.ok:
            return steps, False, "conversation_access"
        verified = run(
            "runtime_inspect",
            [binary, "plugins", "inspect", PLUGIN_ID, "--runtime", "--json"],
            timeout=30,
        )
        runtime_payload = _json_output(verified)
        runtime_record = _plugin_record(runtime_payload) or (
            runtime_payload if isinstance(runtime_payload, dict) else None
        )
        runtime_loaded = (
            _bool_field(runtime_record, "loaded", "runtimeLoaded", "isLoaded")
            if verified.ok
            else None
        )
        steps[-1]["loaded"] = runtime_loaded
        proven = (
            verified.ok
            and isinstance(runtime_record, dict)
            and runtime_loaded is True
        )
        return steps, proven, None if proven else "runtime_inspect_unproven"

    inventory = run("inventory_before", [binary, "plugin", "list", "--json"])
    plugin_present = _plugin_record(_json_output(inventory)) is not None if inventory.ok else False
    market = run("marketplace_inventory", [binary, "plugin", "marketplace", "list", "--json"])
    market_present = _marketplace_registered(_json_output(market)) if market.ok else False

    if not market_present:
        add_command = [binary, "plugin", "marketplace", "add", str(target)]
        if host == "codex":
            add_command.append("--json")
        else:
            add_command.extend(["--scope", "user"])
        added = run("marketplace_add", add_command)
        if not added.ok:
            return steps, False, "marketplace_add"

    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    if force_refresh and plugin_present:
        remove_command = (
            [binary, "plugin", "remove", selector, "--json"]
            if host == "codex"
            else [binary, "plugin", "uninstall", selector, "--scope", "user"]
        )
        removed = run("plugin_remove_for_refresh", remove_command)
        if not removed.ok:
            return steps, False, "plugin_remove_for_refresh"
        plugin_present = False
    if host == "codex":
        if not plugin_present:
            installed = run("plugin_add", [binary, "plugin", "add", selector, "--json"], timeout=60)
            if not installed.ok:
                return steps, False, "plugin_add"
        verified = run("inventory_after", [binary, "plugin", "list", "--json"])
        proven = verified.ok and _plugin_record(_json_output(verified)) is not None
        return steps, proven, None if proven else "inventory_after_unproven"

    if not plugin_present:
        installed = run("plugin_install", [binary, "plugin", "install", selector, "--scope", "user"], timeout=60)
        if not installed.ok:
            return steps, False, "plugin_install"
    enabled = run("enable", [binary, "plugin", "enable", selector, "--scope", "user"])
    if not enabled.ok:
        return steps, False, "enable"
    verified = run("inventory_after", [binary, "plugin", "list", "--json"])
    record = _plugin_record(_json_output(verified)) if verified.ok else None
    proven = record is not None and _bool_field(record, "enabled", "active", "isEnabled") is not False
    return steps, proven, None if proven else "inventory_after_unproven"


def _native_command_plan(host: str, target: Path) -> list[dict[str, Any]]:
    """Return the exact argv variants an install may execute, in order."""
    binary = str(HOSTS[host]["binary"])
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    if host == "hermes":
        return [
            {"name": "enable", "argv": [binary, "plugins", "enable", PLUGIN_ID]},
            {"name": "inventory", "argv": [binary, "plugins", "list"]},
        ]
    if host == "openclaw":
        install_argv = [binary, "plugins", "install", str(target)]
        return [
            {
                "name": "gateway_status",
                "argv": [binary, "gateway", "status", "--deep", "--require-rpc", "--json"],
                "kind": "safety_gate",
            },
            {
                "name": "inspect_existing",
                "argv": [binary, "plugins", "inspect", PLUGIN_ID, "--json"],
            },
            {
                "name": "install",
                "argv": install_argv,
                "condition": "inspect_existing reports absent",
            },
            {
                "name": "install",
                "argv": [*install_argv, "--force"],
                "condition": "inspect_existing reports present",
            },
            {"name": "enable", "argv": [binary, "plugins", "enable", PLUGIN_ID]},
            {
                "name": "conversation_access",
                "argv": [
                    binary,
                    "config",
                    "set",
                    f"plugins.entries.{PLUGIN_ID}.hooks.allowConversationAccess",
                    "true",
                ],
            },
            {
                "name": "runtime_inspect",
                "argv": [binary, "plugins", "inspect", PLUGIN_ID, "--runtime", "--json"],
            },
        ]

    commands: list[dict[str, Any]] = [
        {"name": "inventory_before", "argv": [binary, "plugin", "list", "--json"]},
        {
            "name": "marketplace_inventory",
            "argv": [binary, "plugin", "marketplace", "list", "--json"],
        },
    ]
    marketplace_add = [binary, "plugin", "marketplace", "add", str(target)]
    if host == "codex":
        marketplace_add.append("--json")
        plugin_install = [binary, "plugin", "add", selector, "--json"]
    else:
        marketplace_add.extend(["--scope", "user"])
        plugin_install = [binary, "plugin", "install", selector, "--scope", "user"]
    commands.extend(
        [
            {
                "name": "marketplace_add",
                "argv": marketplace_add,
                "condition": "marketplace inventory reports absent",
            },
            {
                "name": "plugin_add" if host == "codex" else "plugin_install",
                "argv": plugin_install,
                "condition": "plugin inventory reports absent",
            },
        ]
    )
    if host == "claude":
        commands.append(
            {
                "name": "enable",
                "argv": [binary, "plugin", "enable", selector, "--scope", "user"],
            }
        )
    commands.append({"name": "inventory_after", "argv": [binary, "plugin", "list", "--json"]})
    return commands


def plan_agent_adapter(
    host: str,
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Return an idempotent, JSON-safe install plan without writing."""
    if host not in HOSTS:
        return {"ok": False, "exit_code": 2, "error": f"Unknown host: {host}"}
    target = _plugin_target(host, home_dir=home_dir)
    effective_cfg = _resolve_install_config(cfg, home_dir=home_dir)
    files, primary = _bundle_files(host, effective_cfg)
    executable = _resolve_binary(host, binary_resolver)
    root_exists, current_root, markers = _root_state(host, home_dir=home_dir)
    fs_plan = _atomic_install_tree(target, files, host=host, dry_run=True, home_dir=home_dir)
    command_plan = _native_command_plan(host, target) if executable else []
    gateway_gate: dict[str, Any] | None = None
    plan_ok = True
    exit_code = 0
    if host == "openclaw" and executable:
        if _can_execute_native(home_dir=home_dir, command_runner=command_runner):
            live, probe = _openclaw_gateway_live(
                home_dir=home_dir,
                command_runner=command_runner,
            )
            state = "unknown" if live is None else "live" if live else "stopped"
            gateway_gate = {
                "state": state,
                "safe_to_mutate": live is False,
                "probe": probe.to_dict(),
            }
            if live is not False:
                plan_ok = False
                exit_code = 1
        else:
            gateway_gate = {
                "state": "unprobed",
                "safe_to_mutate": None,
                "reason": "explicit home boundary suppresses real native commands",
            }
    return {
        "ok": plan_ok,
        "exit_code": exit_code,
        "dry_run": True,
        "host": host,
        "host_discovered": bool(executable or current_root),
        "executable": executable,
        "native_root": str(_host_root(host, home_dir=home_dir)),
        "current_markers": markers,
        "stale_config": bool(root_exists and not executable and not current_root),
        "plugin_path": str(target / primary),
        "filesystem": fs_plan,
        "native_lifecycle": HOSTS[host]["native_lifecycle"],
        "commands_will_run": bool(executable),
        "native_command_plan": command_plan,
        "gateway_safety_gate": gateway_gate,
        "restart_policy": "never automatic; OpenClaw install pauses when a live gateway is proven",
    }


def install_agent_adapter(
    host: str,
    cfg: AgencyConfig | None = None,
    *,
    home_dir: str | Path | None = None,
    dry_run: bool = False,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Stage and natively register Agency Runtime for one host.

    A config-only/bare explicit host root may be staged, but only a discovered
    executable is allowed to perform native registration.  Native step failures
    return ``ok=False``, ``exit_code=1``, ``partial=True``, and the exact failed
    step instead of overstating maturity.
    """
    if host not in HOSTS:
        return {
            "ok": False,
            "exit_code": 2,
            "error": f"Unknown host: {host}. Supported: {', '.join(HOSTS)}",
        }
    if dry_run:
        return plan_agent_adapter(
            host,
            cfg,
            home_dir=home_dir,
            binary_resolver=binary_resolver,
            command_runner=command_runner,
        )

    target = _plugin_target(host, home_dir=home_dir)
    effective_cfg = _resolve_install_config(cfg, home_dir=home_dir)
    files, primary = _bundle_files(host, effective_cfg)
    executable = _resolve_binary(host, binary_resolver)
    root_exists, current_root, _markers = _root_state(host, home_dir=home_dir)
    if not (executable or root_exists or current_root):
        return {
            "ok": False,
            "exit_code": 2,
            "error": f"{host} is not installed on this machine",
            "host": host,
        }

    # OpenClaw plugin installation may restart or reload its gateway.  Prove
    # that the gateway is stopped before changing even the staged filesystem;
    # a command error or an unrecognized payload is not safe consent.
    if host == "openclaw" and executable and _can_execute_native(
        home_dir=home_dir,
        command_runner=command_runner,
    ):
        gateway_live, gateway_probe = _openclaw_gateway_live(
            home_dir=home_dir,
            command_runner=command_runner,
        )
        if gateway_live is not False:
            failed_step = (
                "host_restart_consent_required"
                if gateway_live is True
                else "gateway_status_unproven"
            )
            gateway_state = "live" if gateway_live is True else "unknown"
            return {
                "ok": False,
                "exit_code": 1,
                "host": host,
                "plugin_path": str(target / primary),
                "target": str(target),
                "backup_path": None,
                "native_steps": [
                    {
                        "name": "gateway_status",
                        "gateway_state": gateway_state,
                        **gateway_probe.to_dict(),
                    }
                ],
                "registered": None,
                "enabled": None,
                "loaded": None,
                "canary": None,
                "partial": False,
                "status": "blocked",
                "maturity": (
                    "staged-registration-unverified"
                    if (target / INSTALL_MANIFEST).exists()
                    else "host-discovered"
                ),
                "failed_step": failed_step,
                "error": (
                    "OpenClaw gateway is live; stop it before native installation."
                    if gateway_live is True
                    else "OpenClaw gateway status could not be proven safe; no installation changes were made."
                ),
                "recovery": "Establish a parseable, successful gateway status showing it is stopped, then rerun.",
                "restart_required": gateway_live is True,
            }

    try:
        filesystem = _atomic_install_tree(
            target,
            files,
            host=host,
            dry_run=False,
            home_dir=home_dir,
        )
    except Exception as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "host": host,
            "partial": False,
            "failed_step": "filesystem",
            "error": f"{type(exc).__name__}: {exc}",
        }

    result: dict[str, Any] = {
        "ok": True,
        "exit_code": 0,
        "host": host,
        "plugin_path": str(target / primary),
        "target": str(target),
        "filesystem": filesystem,
        "backup_path": filesystem.get("backup_path"),
        "native_steps": [],
        "registered": False,
        "enabled": None,
        "loaded": None,
        "canary": None,
        "restart_required": True,
    }

    if not executable:
        result.update(
            {
                "status": "staged_unverified",
                "maturity": "staged-not-registered",
                "warning": "Host state exists but no executable was discovered; native registration was not attempted.",
            }
        )
        return result

    if not _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        result.update(
            {
                "status": "staged_test_boundary",
                "maturity": "staged-not-registered",
                "warning": "Explicit home boundary suppressed real native commands; inject command_runner to exercise registration.",
            }
        )
        return result

    steps, native_ok, failed_step = _native_registration_steps(
        host,
        target,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    result["native_steps"] = steps
    if not native_ok:
        failure_status = "partial_failure"
        failure_maturity = "staged-registration-incomplete"
        failure_registered: bool | None = False
        failure_enabled: bool | None = None
        failure_loaded: bool | None = None
        if host == "openclaw":
            if failed_step in {"enable", "conversation_access", "runtime_inspect_unproven"}:
                failure_registered = True
            elif failed_step == "install":
                existing_step = next(
                    (step for step in steps if step.get("name") == "inspect_existing"),
                    None,
                )
                failure_registered = True if existing_step and existing_step.get("ok") is True else None
            else:
                failure_registered = None
            if failed_step in {"conversation_access", "runtime_inspect_unproven"}:
                failure_enabled = True
            if failed_step == "runtime_inspect_unproven":
                runtime_step = next(
                    (step for step in steps if step.get("name") == "runtime_inspect"),
                    None,
                )
                failure_loaded = runtime_step.get("loaded") if runtime_step else None
                failure_status = "verification_incomplete"
                failure_maturity = "enabled-runtime-unverified"
        result.update(
            {
                "ok": False,
                "exit_code": 1,
                "partial": True,
                "status": failure_status,
                "maturity": failure_maturity,
                "registered": failure_registered,
                "enabled": failure_enabled,
                "loaded": failure_loaded,
                "canary": None,
                "failed_step": failed_step,
                "error": (
                    "OpenClaw gateway is live; stop it before native installation."
                    if failed_step == "host_restart_consent_required"
                    else "OpenClaw gateway status could not be proven safe; native installation was not attempted."
                    if failed_step == "gateway_status_unproven"
                    else f"Native {host} registration failed at step: {failed_step}"
                ),
                "recovery": "Fix the failed native step and rerun; filesystem staging is idempotent and the backup is retained.",
            }
        )
        return result

    result.update(
        {
            "status": "registered",
            "maturity": "runtime-verified" if host == "openclaw" else "enabled-runtime-unverified",
            "registered": True,
            "enabled": True,
            "loaded": True if host == "openclaw" else None,
            # Runtime inspection proves loading only.  No supported native
            # installer command currently exercises an end-to-end canary.
            "canary": None,
            "partial": False,
        }
    )
    return result


def rollback_agent_adapter(
    host: str,
    *,
    home_dir: str | Path | None = None,
    backup_path: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
) -> dict[str, Any]:
    """Restore a retained bundle and refresh its native host registration.

    With an explicit ``home_dir`` and no injected runner, only the owned source
    tree is restored.  The result reports that native state as unverified rather
    than calling a real host outside the fixture boundary.
    """
    if host not in HOSTS:
        return {"ok": False, "exit_code": 2, "error": f"Unknown host: {host}"}
    target = _plugin_target(host, home_dir=home_dir)
    backup_root = (_runtime_home(home_dir=home_dir) / "backups" / host).resolve()
    selected: Path | None
    if backup_path is not None:
        selected = Path(backup_path).expanduser().resolve()
    else:
        candidates = (
            sorted((path.resolve() for path in backup_root.iterdir() if path.is_dir()), reverse=True)
            if backup_root.exists()
            else []
        )
        selected = next(
            (
                candidate
                for candidate in candidates
                if _validate_owned_backup(candidate, host=host, target=target)[0]
            ),
            None,
        )
    if selected is None or not selected.exists():
        return {"ok": False, "exit_code": 2, "error": f"No valid retained backup found for {host}"}
    if selected == backup_root or not selected.is_relative_to(backup_root):
        return {
            "ok": False,
            "exit_code": 2,
            "error": f"Backup must be inside the managed backup root: {backup_root}",
        }
    valid, validation_error, restored_version = _validate_owned_backup(
        selected,
        host=host,
        target=target,
    )
    if not valid:
        return {"ok": False, "exit_code": 2, "error": validation_error}

    # A rollback replaces the plugin tree just as an install does.  OpenClaw
    # may reload that tree through its gateway, so prove the gateway stopped
    # before moving either the current target or the retained backup.  Missing
    # executables and explicit-home test boundaries are unknown, not evidence
    # of a stopped process.
    executable = _resolve_binary(host, binary_resolver)
    if host == "openclaw":
        gateway_live: bool | None = None
        gateway_probe: NativeCommandResult | None = None
        if executable and _can_execute_native(home_dir=home_dir, command_runner=command_runner):
            gateway_live, gateway_probe = _openclaw_gateway_live(
                home_dir=home_dir,
                command_runner=command_runner,
            )
        if gateway_live is not False:
            gateway_state = "live" if gateway_live is True else "unknown"
            step: dict[str, Any] = {
                "name": "gateway_status",
                "gateway_state": gateway_state,
                "ok": gateway_live is False,
            }
            if gateway_probe is not None:
                step.update(gateway_probe.to_dict())
            elif not executable:
                step["error"] = "openclaw executable is unavailable; gateway state cannot be proven"
            else:
                step["error"] = "explicit home boundary suppresses the gateway status probe"
            return {
                "ok": False,
                "exit_code": 1,
                "host": host,
                "action": "rollback_blocked",
                "target": str(target),
                "restored_from": str(selected),
                "native_steps": [step],
                "partial": False,
                "failed_step": (
                    "host_restart_consent_required"
                    if gateway_live is True
                    else "gateway_status_unproven"
                ),
                "maturity": "rollback-not-started",
                "error": (
                    "OpenClaw gateway is live; stop it before rollback."
                    if gateway_live is True
                    else "OpenClaw gateway status could not be proven safe; no rollback changes were made."
                ),
            }

    displaced: Path | None = None
    try:
        if target.exists():
            displaced = _runtime_home(home_dir=home_dir) / "backups" / host / f"rollback-displaced-{_utc_stamp()}"
            displaced.parent.mkdir(parents=True, exist_ok=True)
            os.replace(target, displaced)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(selected, target)
    except Exception as exc:
        if displaced is not None and displaced.exists() and not target.exists():
            os.replace(displaced, target)
        return {"ok": False, "exit_code": 1, "error": f"{type(exc).__name__}: {exc}"}
    attestation_invalidated = _invalidate_canary_attestation(
        host,
        home_dir=home_dir,
    )
    result: dict[str, Any] = {
        "ok": True,
        "exit_code": 0,
        "host": host,
        "action": "rolled_back",
        "restored_from": str(selected),
        "restored_version": restored_version,
        "displaced_path": str(displaced) if displaced else None,
        "restart_required": True,
        "native_steps": [],
        "native_refreshed": False,
        "canary_attestation_invalidated": attestation_invalidated,
    }
    if not executable or not _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        result["maturity"] = "filesystem-restored-native-unverified"
        return result

    steps, native_ok, failed_step = _native_registration_steps(
        host,
        target,
        home_dir=home_dir,
        command_runner=command_runner,
        force_refresh=True,
    )
    result["native_steps"] = steps
    result["native_refreshed"] = native_ok
    if not native_ok:
        result.update(
            {
                "ok": False,
                "exit_code": 1,
                "partial": True,
                "failed_step": failed_step,
                "maturity": "filesystem-restored-native-refresh-incomplete",
                "error": f"Filesystem rollback succeeded but native {host} refresh failed at {failed_step}",
            }
        )
    else:
        result["maturity"] = "runtime-verified" if host == "openclaw" else "enabled-runtime-unverified"
    return result


def toggle_agency(
    host: str,
    enabled: bool,
    *,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Toggle Agency Runtime using only the host's native lifecycle."""
    if host not in HOSTS:
        return {"ok": False, "exit_code": 2, "error": f"Unknown host: {host}"}
    binary_path = _resolve_binary(host, binary_resolver)
    if not binary_path:
        return {"ok": False, "exit_code": 2, "error": f"{host} executable is not available"}

    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    binary = str(HOSTS[host]["binary"])
    if host == "hermes":
        command = [binary, "plugins", "enable" if enabled else "disable", PLUGIN_ID]
    elif host == "openclaw":
        command = [binary, "plugins", "enable" if enabled else "disable", PLUGIN_ID]
    elif host == "claude":
        command = [binary, "plugin", "enable" if enabled else "disable", selector, "--scope", "user"]
    elif enabled:
        command = [binary, "plugin", "add", selector, "--json"]
    else:
        command = [binary, "plugin", "remove", selector, "--json"]

    if dry_run:
        return {
            "ok": True,
            "exit_code": 0,
            "dry_run": True,
            "host": host,
            "enabled": enabled,
            "command": command,
            "native_lifecycle": HOSTS[host]["native_lifecycle"],
        }
    if not _can_execute_native(home_dir=home_dir, command_runner=command_runner):
        return {
            "ok": False,
            "exit_code": 2,
            "error": "Explicit home boundary requires an injected command_runner for native toggles",
        }
    result = _run_native(
        command,
        host=host,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    verification: NativeCommandResult | None = None
    record: dict[str, Any] | None = None
    native_flag: bool | None = None
    postcondition = False
    observed_enabled: bool | None = None
    if result.ok:
        verification = _run_native(
            _inventory_command(host),
            host=host,
            home_dir=home_dir,
            command_runner=command_runner,
        )
        if verification.ok:
            record = (
                _hermes_text_plugin_record(verification.stdout)
                if host == "hermes"
                else _plugin_record(_json_output(verification))
            )
            native_flag = _bool_field(record, "enabled", "active", "isEnabled")
            if enabled:
                postcondition = record is not None and native_flag is True
                observed_enabled = native_flag
            else:
                postcondition = record is None or native_flag is False
                observed_enabled = False if postcondition else native_flag
    ok = result.ok and verification is not None and verification.ok and postcondition
    verification_state = "verified" if ok else "command_failed"
    if result.ok and (verification is None or not verification.ok):
        verification_state = "inventory_failed"
    elif result.ok and verification is not None and verification.ok and not postcondition:
        verification_state = (
            "enablement_unverified"
            if enabled and record is not None and native_flag is None
            else "postcondition_mismatch"
        )
    error = None
    if not result.ok:
        error = (result.stderr or result.stdout or "native toggle failed").strip()[:500]
    elif verification is None or not verification.ok:
        detail = (
            (verification.stderr or verification.stdout).strip()
            if verification is not None
            else ""
        )
        error = (detail or "native toggle inventory verification failed")[:500]
    elif not postcondition:
        error = (
            f"native toggle postcondition was not proven for {host}: "
            f"wanted enabled={enabled}, inventory={record!r}"
        )[:500]
    return {
        "ok": ok,
        "exit_code": 0 if ok else (result.returncode or 1),
        "host": host,
        "enabled": observed_enabled if ok else None,
        "action": ("enabled" if enabled else "disabled") if ok else verification_state,
        "native_step": result.to_dict(),
        "verification_step": verification.to_dict() if verification is not None else None,
        "postcondition_verified": postcondition,
        "verification_state": verification_state,
        "partial": bool(result.ok and not ok),
        "error": error,
        "restart_required": True,
    }


def seed_starter_roster(store: Store) -> int:
    """Seed bundled starter agents without overwriting a synced active roster."""
    existing_slugs = {agent.get("agent_slug") for agent in store.get_active_roster()}
    count = 0
    for agent in STARTER_ROSTER:
        if agent["slug"] in existing_slugs:
            continue
        store.activate_agent(dict(agent))
        count += 1
    store.record_import_event("starter_roster_installed", "", f"count={count}")
    return count


__all__ = [
    "HOSTS",
    "INSTALL_MANIFEST",
    "MARKETPLACE_ID",
    "PLUGIN_ID",
    "NativeCommandResult",
    "detect_installed_agents",
    "inspect_host_installations",
    "install_agent_adapter",
    "plan_agent_adapter",
    "rollback_agent_adapter",
    "seed_starter_roster",
    "toggle_agency",
]
