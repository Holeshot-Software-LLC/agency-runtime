"""Least-privilege environment construction for owned subprocesses."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from agency_runtime.core.process_argv import sanitized_executable_search_path

SAFE_SUBPROCESS_ENVIRONMENT_NAMES = frozenset(
    {
        "ALL_PROXY",
        "COMSPEC",
        "CURL_CA_BUNDLE",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PATH",
        "PATHEXT",
        "PROGRAMDATA",
        "REQUESTS_CA_BUNDLE",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USER",
        "USERNAME",
        "USERPROFILE",
        "WINDIR",
    }
)

INTEGRATION_HOME_BY_NAME = {
    "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
    "codex": ("CODEX_HOME", ".codex"),
    "hermes": ("HERMES_HOME", ".hermes"),
    # OPENCLAW_HOME is the user-home root. OpenClaw derives .openclaw below it.
    "openclaw": ("OPENCLAW_HOME", ""),
}
_INTEGRATION_HOME_NAMES = frozenset(
    variable for variable, _default_name in INTEGRATION_HOME_BY_NAME.values()
)


def _validated_existing_search_path(
    value: str,
    *,
    current_directory: str | Path | None,
    forbidden_roots: Sequence[str | Path],
    explicit: bool,
) -> str:
    """Canonicalize PATH to existing directories outside delegated roots."""

    if not isinstance(value, str) or "\x00" in value:
        raise ValueError("PATH must be text without NUL bytes")
    accepted: list[str] = []
    seen: set[str] = set()
    for raw_entry in value.split(os.pathsep):
        candidate = sanitized_executable_search_path(
            raw_entry,
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
        if not candidate:
            if explicit:
                raise ValueError("explicit PATH contains an unsafe entry")
            continue
        try:
            resolved = Path(candidate).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            if explicit:
                raise ValueError("explicit PATH contains a missing directory") from None
            continue
        if not resolved.is_dir():
            if explicit:
                raise ValueError("explicit PATH contains a non-directory entry")
            continue
        canonical = sanitized_executable_search_path(
            str(resolved),
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
        )
        if not canonical:
            if explicit:
                raise ValueError("explicit PATH resolves into an unsafe root")
            continue
        key = os.path.normcase(canonical)
        if key not in seen:
            accepted.append(canonical)
            seen.add(key)
    if explicit and not accepted:
        raise ValueError("explicit PATH contains no safe executable directory")
    return os.pathsep.join(accepted)


def least_privilege_subprocess_environment(
    integration: str,
    *,
    environ: Mapping[str, str] | None = None,
    home_dir: str | Path | None = None,
    extra_env: Mapping[str, str] | None = None,
    current_directory: str | Path | None = None,
    forbidden_roots: Sequence[str | Path] = (),
) -> dict[str, str]:
    """Build one child environment from platform and selected-host authority."""

    source = os.environ if environ is None else environ
    selected = integration.strip().lower()
    safe: dict[str, str] = {}
    for key, value in source.items():
        normalized = key.upper()
        if (
            normalized in SAFE_SUBPROCESS_ENVIRONMENT_NAMES
            and isinstance(value, str)
            and "\x00" not in value
        ):
            safe[normalized] = value

    if "PATH" in safe:
        safe["PATH"] = _validated_existing_search_path(
            safe["PATH"],
            current_directory=current_directory,
            forbidden_roots=forbidden_roots,
            explicit=False,
        )

    explicit_home = Path(home_dir).expanduser().resolve() if home_dir is not None else None
    source_home = (
        explicit_home
        if explicit_home is not None
        else Path(source.get("USERPROFILE") or source.get("HOME") or Path.home()).expanduser()
    )
    if explicit_home is not None:
        safe["HOME"] = str(explicit_home)
        safe["USERPROFILE"] = str(explicit_home)

    auth_home = INTEGRATION_HOME_BY_NAME.get(selected)
    selected_auth_variable: str | None = None
    if auth_home is not None:
        selected_auth_variable, default_name = auth_home
        default_path = source_home if not default_name else source_home / default_name
        if explicit_home is not None:
            safe[selected_auth_variable] = str(default_path)
        else:
            configured = source.get(selected_auth_variable)
            safe[selected_auth_variable] = (
                configured
                if isinstance(configured, str) and "\x00" not in configured
                else str(default_path)
            )

    for key, value in (extra_env or {}).items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("extra environment keys and values must be strings")
        normalized = key.upper()
        if not key or "\x00" in key or "=" in key or "\x00" in value:
            raise ValueError("extra environment contains an invalid key or value")
        if normalized in _INTEGRATION_HOME_NAMES and normalized != selected_auth_variable:
            raise ValueError("extra environment cannot add another integration's auth root")
        if normalized == "PATH":
            safe["PATH"] = _validated_existing_search_path(
                value,
                current_directory=current_directory,
                forbidden_roots=forbidden_roots,
                explicit=True,
            )
        else:
            safe[normalized if normalized in _INTEGRATION_HOME_NAMES else key] = value

    safe["NO_COLOR"] = "1"
    return safe


__all__ = [
    "INTEGRATION_HOME_BY_NAME",
    "SAFE_SUBPROCESS_ENVIRONMENT_NAMES",
    "least_privilege_subprocess_environment",
]
