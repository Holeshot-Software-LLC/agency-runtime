"""Dedicated-container Codex managed-hook policy installation.

This surface is intentionally system-scoped and opt-in. It owns one exact
``requirements.toml`` and relay script, refuses foreign files, and leaves the
ordinary per-user plugin installation in place for Agency's skill and MCP
surfaces. Managed-only hook policy is suitable for disposable production
containers, not general developer workstations where it would suppress other
unmanaged hooks.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import shlex
import stat
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib

from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file
from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
from agency_runtime.core.installer_payloads import codex_hooks, hook_timeout_seconds
from agency_runtime.core.runtime_control import runtime_control_path

MANAGED_POLICY_SCHEMA = "agency.codex.managed_hooks.v1"
MANAGED_POLICY_INSPECTION_SCHEMA = "agency.codex.managed_hooks.inspection.v1"
MANAGED_TRUST_MODE = "managed_policy"
_MAX_OWNED_FILE_BYTES = 1024 * 1024
_RELAY_NAME = "agency-runtime-hook.py"
_OWNED_PREFIX = "# agency-runtime-owned"


def managed_codex_policy_paths(
    *,
    platform_system: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, Path, Path]:
    """Return requirements, POSIX hook, and Windows hook directories."""

    system = str(platform_system or platform.system()).casefold()
    environment = os.environ if environ is None else environ
    program_data = Path(environment.get("ProgramData") or r"C:\ProgramData")
    windows_root = program_data / "OpenAI" / "Codex"
    requirements = (
        windows_root / "requirements.toml"
        if system == "windows"
        else Path("/etc/codex/requirements.toml")
    )
    return (
        requirements,
        Path("/etc/codex/agency-runtime-hooks"),
        windows_root / "agency-runtime-hooks",
    )


def _owned_document(kind: str, payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{_OWNED_PREFIX}:{kind}:v1\n# payload-sha256:{digest}\n{payload}"


def _owned_payload(document: str, *, kind: str) -> str | None:
    expected = f"{_OWNED_PREFIX}:{kind}:v1\n# payload-sha256:"
    if not document.startswith(expected):
        return None
    first_newline = document.find("\n")
    second_newline = document.find("\n", first_newline + 1)
    if first_newline < 0 or second_newline < 0:
        return None
    digest = document[first_newline + len("\n# payload-sha256:") : second_newline]
    payload = document[second_newline + 1 :]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        return None
    if hashlib.sha256(payload.encode("utf-8")).hexdigest() != digest:
        return None
    return payload


def _read_owned(path: Path, *, kind: str) -> str | None:
    if not _path_present(path):
        return None
    raw = read_bounded_regular_file(path, limit=_MAX_OWNED_FILE_BYTES, label=kind)
    try:
        document = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"existing {kind} is not valid UTF-8") from exc
    if _owned_payload(document, kind=kind) is None:
        raise ValueError(f"existing {kind} is not owned by Agency Runtime")
    return document


def _ensure_real_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    metadata = path.lstat()
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise OSError("managed Codex policy directory is not a real directory")


def _path_present(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _relay_commands(
    python_executable: str,
    posix_script: Path,
    windows_script: Path,
    event: str,
) -> tuple[str, str]:
    posix_argv = (python_executable, "-I", "-S", str(posix_script), event)
    windows_argv = (python_executable, "-I", "-S", str(windows_script), event)
    return (
        shlex.join(posix_argv),
        "& " + " ".join(_powershell_literal(item) for item in windows_argv),
    )


def _relay_payload(
    *,
    python_executable: str,
    bootstrap_path: str,
    config_path: Path,
    control_path: Path,
) -> str:
    values = {
        "python": python_executable,
        "bootstrap": bootstrap_path,
        "config": str(config_path),
        "control": str(control_path),
        "events": list(CODEX_HOOK_EVENTS),
    }
    encoded = json.dumps(values, ensure_ascii=True, sort_keys=True)
    return (
        "from __future__ import annotations\n\n"
        "import json\n"
        "import os\n"
        "import sys\n\n"
        f"_BINDING = json.loads({encoded!r})\n\n"
        "def main() -> int:\n"
        "    if len(sys.argv) != 2 or sys.argv[1] not in _BINDING['events']:\n"
        "        return 2\n"
        "    argv = [\n"
        "        _BINDING['python'], '-I', '-S', _BINDING['bootstrap'],\n"
        "        'agency_runtime.cli', 'hook', 'codex', '--event', sys.argv[1],\n"
        "        '--config', _BINDING['config'],\n"
        "        '--runtime-control', _BINDING['control'],\n"
        "    ]\n"
        "    os.execv(_BINDING['python'], argv)\n"
        "    return 1\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )


def _toml_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def _requirements_payload(
    cfg: AgencyConfig,
    *,
    python_executable: str,
    posix_managed_dir: Path,
    windows_managed_dir: Path,
) -> str:
    timeout = hook_timeout_seconds(cfg, harness="codex")
    canonical = codex_hooks(timeout)
    lines = [
        "allow_managed_hooks_only = true",
        "",
        "[features]",
        "hooks = true",
        "",
        "[hooks]",
        f"managed_dir = {_toml_string(posix_managed_dir)}",
        f"windows_managed_dir = {_toml_string(windows_managed_dir)}",
    ]
    groups = canonical["hooks"]
    for event in CODEX_HOOK_EVENTS:
        registration = groups[event][0]
        handler = registration["hooks"][0]
        lines.extend(("", f"[[hooks.{event}]]"))
        matcher = registration.get("matcher")
        if isinstance(matcher, str) and matcher:
            lines.append(f"matcher = {_toml_string(matcher)}")
        lines.extend(("", f"[[hooks.{event}.hooks]]", 'type = "command"'))
        command, command_windows = _relay_commands(
            python_executable,
            posix_managed_dir / _RELAY_NAME,
            windows_managed_dir / _RELAY_NAME,
            event,
        )
        lines.extend(
            (
                f"command = {_toml_string(command)}",
                f"command_windows = {_toml_string(command_windows)}",
                "async = false",
                f"timeout = {int(handler['timeout'])}",
                f"statusMessage = {_toml_string(handler['statusMessage'])}",
            )
        )
        if event == "UserPromptSubmit":
            lines.append("additionalContextLimit = 0")
    return "\n".join(lines) + "\n"


def _policy_documents(
    cfg: AgencyConfig,
    *,
    launcher_paths: tuple[str, str],
    config_path: Path,
    control_path: Path,
    posix_managed_dir: Path,
    windows_managed_dir: Path,
) -> tuple[str, str]:
    python_executable, bootstrap_path = launcher_paths
    relay = _owned_document(
        "codex-managed-relay",
        _relay_payload(
            python_executable=python_executable,
            bootstrap_path=bootstrap_path,
            config_path=config_path,
            control_path=control_path,
        ),
    )
    requirements = _owned_document(
        "codex-requirements",
        _requirements_payload(
            cfg,
            python_executable=python_executable,
            posix_managed_dir=posix_managed_dir,
            windows_managed_dir=windows_managed_dir,
        ),
    )
    return requirements, relay


def _relay_binding(document: str) -> dict[str, Any]:
    payload = _owned_payload(document, kind="codex-managed-relay")
    if payload is None:
        raise ValueError("managed relay ownership digest is invalid")
    tree = ast.parse(payload, mode="exec")
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        value = statement.value
        if (
            not isinstance(target, ast.Name)
            or target.id != "_BINDING"
            or not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Attribute)
            or not isinstance(value.func.value, ast.Name)
            or value.func.value.id != "json"
            or value.func.attr != "loads"
            or len(value.args) != 1
            or not isinstance(value.args[0], ast.Constant)
            or not isinstance(value.args[0].value, str)
        ):
            continue
        decoded = json.loads(value.args[0].value)
        if not isinstance(decoded, dict):
            break
        return decoded
    raise ValueError("managed relay binding is invalid")


def _hook_registration_drift(
    event: str,
    groups: object,
    *,
    posix_relay: str,
    windows_relay: str,
) -> list[str]:
    if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict):
        return [f"hook:{event}"]
    handlers = groups[0].get("hooks")
    if not isinstance(handlers, list) or len(handlers) != 1 or not isinstance(handlers[0], dict):
        return [f"handler:{event}"]
    handler = handlers[0]
    reasons: list[str] = []
    if handler.get("type") != "command":
        reasons.append(f"handler_type:{event}")
    if posix_relay not in str(handler.get("command") or ""):
        reasons.append(f"command:{event}")
    if windows_relay not in str(handler.get("command_windows") or ""):
        reasons.append(f"command_windows:{event}")
    return reasons


def _managed_policy_drift_reasons(
    requirements_document: str,
    relay_document: str,
    *,
    posix_managed_dir: Path,
    windows_managed_dir: Path,
) -> tuple[list[str], dict[str, Any]]:
    reasons: list[str] = []
    payload = _owned_payload(requirements_document, kind="codex-requirements")
    if payload is None:
        return ["requirements_identity"], {}
    try:
        parsed = tomllib.loads(payload)
    except (tomllib.TOMLDecodeError, UnicodeError):
        return ["requirements_toml"], {}
    hooks = parsed.get("hooks")
    features = parsed.get("features")
    if parsed.get("allow_managed_hooks_only") is not True:
        reasons.append("managed_only")
    if not isinstance(features, dict) or features.get("hooks") is not True:
        reasons.append("hooks_feature")
    if not isinstance(hooks, dict):
        return [*reasons, "hooks_table"], {}
    if hooks.get("managed_dir") != str(posix_managed_dir):
        reasons.append("managed_dir")
    if hooks.get("windows_managed_dir") != str(windows_managed_dir):
        reasons.append("windows_managed_dir")
    event_keys = set(hooks).difference({"managed_dir", "windows_managed_dir"})
    if event_keys != set(CODEX_HOOK_EVENTS):
        reasons.append("hook_events")
    posix_relay = str(posix_managed_dir / _RELAY_NAME)
    windows_relay = str(windows_managed_dir / _RELAY_NAME)
    for event in CODEX_HOOK_EVENTS:
        reasons.extend(
            _hook_registration_drift(
                event,
                hooks.get(event),
                posix_relay=posix_relay,
                windows_relay=windows_relay,
            )
        )
    try:
        binding = _relay_binding(relay_document)
    except (RecursionError, SyntaxError, TypeError, ValueError, json.JSONDecodeError):
        return [*reasons, "relay_binding"], {}
    if binding.get("events") != list(CODEX_HOOK_EVENTS):
        reasons.append("relay_events")
    for field in ("python", "bootstrap", "config", "control"):
        value = binding.get(field)
        if not isinstance(value, str) or not value or len(value) > 4096 or "\x00" in value:
            reasons.append(f"relay_{field}")
    return reasons, binding


def inspect_managed_codex_policy(
    *,
    requirements_path: Path | None = None,
    posix_managed_dir: Path | None = None,
    windows_managed_dir: Path | None = None,
    platform_system: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Inspect Agency's system-managed Codex policy without mutating it."""

    system = str(platform_system or platform.system()).casefold()
    defaults = managed_codex_policy_paths(platform_system=system, environ=environ)
    requirements = requirements_path or defaults[0]
    posix_dir = posix_managed_dir or defaults[1]
    windows_dir = windows_managed_dir or defaults[2]
    active_dir = windows_dir if system == "windows" else posix_dir
    relay_path = active_dir / _RELAY_NAME
    report: dict[str, Any] = {
        "schema_version": MANAGED_POLICY_INSPECTION_SCHEMA,
        "status": "absent",
        "current": False,
        "trust_mode": None,
        "requirements_path": str(requirements),
        "managed_dir": str(active_dir),
        "relay_path": str(relay_path),
        "config_path": None,
        "allow_managed_hooks_only": None,
        "hook_events": [],
        "drift_reasons": [],
    }
    requirements_present = _path_present(requirements)
    relay_present = _path_present(relay_path)
    if not requirements_present and not relay_present:
        return report
    try:
        requirements_document = (
            _read_owned(requirements, kind="codex-requirements") if requirements_present else None
        )
        relay_document = (
            _read_owned(relay_path, kind="codex-managed-relay") if relay_present else None
        )
    except (OSError, ValueError):
        report.update(
            status="foreign_or_modified",
            drift_reasons=["ownership_or_file_trust"],
        )
        return report
    if requirements_document is None or relay_document is None:
        report.update(
            status="orphaned",
            drift_reasons=[
                "requirements_missing" if requirements_document is None else "relay_missing"
            ],
        )
        return report
    reasons, binding = _managed_policy_drift_reasons(
        requirements_document,
        relay_document,
        posix_managed_dir=posix_dir,
        windows_managed_dir=windows_dir,
    )
    report.update(
        requirements_digest=hashlib.sha256(requirements_document.encode("utf-8")).hexdigest(),
        relay_digest=hashlib.sha256(relay_document.encode("utf-8")).hexdigest(),
        config_path=(str(binding.get("config")) if not reasons else None),
        allow_managed_hooks_only=True if not reasons else None,
        hook_events=list(CODEX_HOOK_EVENTS) if not reasons else [],
        drift_reasons=reasons,
    )
    if reasons:
        report["status"] = "drifted"
        return report
    report.update(status="current", current=True, trust_mode=MANAGED_TRUST_MODE)
    return report


def _base_report(
    *,
    requirements_path: Path,
    active_managed_dir: Path,
    config_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": MANAGED_POLICY_SCHEMA,
        "trust_mode": MANAGED_TRUST_MODE,
        "requirements_path": str(requirements_path),
        "managed_dir": str(active_managed_dir),
        "relay_path": str(active_managed_dir / _RELAY_NAME),
        "config_path": str(config_path),
        "allow_managed_hooks_only": True,
        "hook_events": list(CODEX_HOOK_EVENTS),
    }


def plan_managed_codex_policy(
    cfg: AgencyConfig,
    *,
    config_path: str | Path,
    requirements_path: Path | None = None,
    posix_managed_dir: Path | None = None,
    windows_managed_dir: Path | None = None,
    platform_system: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a write-free managed-policy plan and refuse foreign targets."""

    system = str(platform_system or platform.system()).casefold()
    defaults = managed_codex_policy_paths(platform_system=system, environ=environ)
    requirements = requirements_path or defaults[0]
    posix_dir = posix_managed_dir or defaults[1]
    windows_dir = windows_managed_dir or defaults[2]
    active_dir = windows_dir if system == "windows" else posix_dir
    config = Path(config_path).expanduser().resolve(strict=True)
    report = _base_report(
        requirements_path=requirements,
        active_managed_dir=active_dir,
        config_path=config,
    )
    try:
        existing_requirements = _read_owned(requirements, kind="codex-requirements")
        existing_relay = _read_owned(
            active_dir / _RELAY_NAME,
            kind="codex-managed-relay",
        )
    except (OSError, ValueError) as exc:
        report.update(ok=False, complete=False, changed=False, status="refused", error=str(exc))
        return report
    report.update(
        ok=True,
        complete=True,
        changed=False,
        status="planned",
        requirements_owned=existing_requirements is not None,
        relay_owned=existing_relay is not None,
    )
    return report


def install_managed_codex_policy(
    cfg: AgencyConfig,
    *,
    config_path: str | Path,
    requirements_path: Path | None = None,
    posix_managed_dir: Path | None = None,
    windows_managed_dir: Path | None = None,
    platform_system: str | None = None,
    environ: Mapping[str, str] | None = None,
    launcher_preparer: Callable[[], tuple[str, str]] | None = None,
    control_path: Path | None = None,
) -> dict[str, Any]:
    """Install one exact system-managed Codex hook policy, fail closed on drift."""

    system = str(platform_system or platform.system()).casefold()
    defaults = managed_codex_policy_paths(platform_system=system, environ=environ)
    requirements = requirements_path or defaults[0]
    posix_dir = posix_managed_dir or defaults[1]
    windows_dir = windows_managed_dir or defaults[2]
    active_dir = windows_dir if system == "windows" else posix_dir
    config = Path(config_path).expanduser().resolve(strict=True)
    report = plan_managed_codex_policy(
        cfg,
        config_path=config,
        requirements_path=requirements,
        posix_managed_dir=posix_dir,
        windows_managed_dir=windows_dir,
        platform_system=system,
        environ=environ,
    )
    if report.get("ok") is not True:
        return report
    relay_changed = False
    requirements_changed = False
    try:
        if launcher_preparer is None:
            from agency_runtime.core.installer_orchestration import (
                _prepare_adapter_launcher_paths,
            )

            launcher_preparer = _prepare_adapter_launcher_paths
        launcher_paths = launcher_preparer()
        requirements_document, relay_document = _policy_documents(
            cfg,
            launcher_paths=launcher_paths,
            config_path=config,
            control_path=control_path or runtime_control_path(),
            posix_managed_dir=posix_dir,
            windows_managed_dir=windows_dir,
        )
        _ensure_real_directory(active_dir)
        _ensure_real_directory(requirements.parent)
        relay_path = active_dir / _RELAY_NAME
        old_relay = _read_owned(relay_path, kind="codex-managed-relay")
        old_requirements = _read_owned(requirements, kind="codex-requirements")
        if old_relay != relay_document:
            atomic_write_text(relay_path, relay_document)
            relay_changed = True
            if os.name != "nt":
                os.chmod(relay_path, 0o700)
        if old_requirements != requirements_document:
            atomic_write_text(requirements, requirements_document)
            requirements_changed = True
            if os.name != "nt":
                os.chmod(requirements, 0o600)
        if (
            _read_owned(relay_path, kind="codex-managed-relay") != relay_document
            or _read_owned(requirements, kind="codex-requirements") != requirements_document
        ):
            raise OSError("managed Codex policy verification failed after write")
    except (OSError, ValueError) as exc:
        report.update(
            ok=False,
            complete=False,
            changed=relay_changed or requirements_changed,
            status="failed",
            error=str(exc),
        )
        return report
    changed = relay_changed or requirements_changed
    report.update(
        ok=True,
        complete=True,
        changed=changed,
        status="installed" if changed else "current",
        requirements_owned=True,
        relay_owned=True,
    )
    return report


__all__ = [
    "MANAGED_POLICY_INSPECTION_SCHEMA",
    "MANAGED_POLICY_SCHEMA",
    "MANAGED_TRUST_MODE",
    "inspect_managed_codex_policy",
    "install_managed_codex_policy",
    "managed_codex_policy_paths",
    "plan_managed_codex_policy",
]
