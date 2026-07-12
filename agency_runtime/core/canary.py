"""Readiness and explicitly confirmed live canaries for native agent hosts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import secrets
import shutil
import sqlite3
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from agency_runtime.core.host_control import SUPPORTED_HOSTS
from agency_runtime.core.installer import PLUGIN_VERSION, inspect_host_installations
from agency_runtime.core.store.sqlite import Store, _default_db_path


CANARY_PROMPT = (
    "Agency Runtime live installation canary. Reply with a concise confirmation "
    "and obey the installed Agency Runtime routing and final-response contract. "
    "Do not modify files, call external services, or expose secrets."
)
RECEIPT_CAPABLE_HOSTS = frozenset({"hermes"})
SAFE_CANARY_HOSTS = frozenset({"codex", "claude"})
ISOLATED_CANARY_HOSTS = SAFE_CANARY_HOSTS
CODEX_CANARY_EXEC_OPTIONS = (
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
    "apps._default.enabled=false",
    "-c",
    "mcp_servers={}",
    "--skip-git-repo-check",
    "--dangerously-bypass-hook-trust",
    "-",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_control_without_writes(db_path: Path, host: str) -> dict[str, Any]:
    """Read soft control through SQLite read-only mode; absent state defaults on."""
    default = {
        "host": host,
        "enabled": True,
        "updated_at": None,
        "source": "default",
    }
    if not db_path.is_file():
        return default
    uri = db_path.resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'host_controls'"
            ).fetchone()
            if exists is None:
                return default
            row = conn.execute(
                "SELECT host, enabled, updated_at, source FROM host_controls WHERE host = ?",
                (host,),
            ).fetchone()
            if row is None:
                return default
            return {
                "host": str(row["host"]),
                "enabled": bool(row["enabled"]),
                "updated_at": str(row["updated_at"]),
                "source": str(row["source"]),
            }
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return {**default, "enabled": None, "source": "unverified"}


def _default_inspector(host: str) -> dict[str, Any]:
    return inspect_host_installations(hosts=[host])[0]


def _copy_bounded_auth(source: Path, destination: Path, *, host: str) -> None:
    """Copy one allowlisted bounded auth artifact into a private temp home."""
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"{host} auth artifact is unavailable or unsafe")
    if source.stat().st_size > 1024 * 1024:
        raise ValueError(f"{host} auth artifact exceeds the safety limit")
    payload = source.read_bytes()
    if len(payload) > 1024 * 1024:
        raise ValueError(f"{host} auth artifact exceeds the safety limit")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(
        destination,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    from agency_runtime.core.configuration import restrict_private_file

    restrict_private_file(destination)


def _codex_isolated_plugin_enabled(value: Any) -> bool:
    if isinstance(value, dict):
        identity = str(value.get("pluginId") or value.get("name") or "")
        if (
            identity.startswith("agency-preflight")
            and value.get("installed") is True
            and value.get("enabled") is True
        ):
            return True
        return any(_codex_isolated_plugin_enabled(child) for child in value.values())
    if isinstance(value, list):
        return any(_codex_isolated_plugin_enabled(child) for child in value)
    return False


def _backend(
    host: str,
    *,
    db_path: Path,
    timeout: float,
    native: Mapping[str, Any] | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] | None = None,
    environ: Mapping[str, str] | None = None,
):
    from agency_runtime.core.cli_transport import safe_cli_environment
    from agency_runtime.core.delegation.backends import run_bounded_process

    if host not in SAFE_CANARY_HOSTS:
        raise ValueError(f"{host} has no proven safe noninteractive canary mode")
    executable = resolver(host)
    if not executable:
        raise ValueError(f"{host} executable is unavailable")
    process_runner = runner or run_bounded_process
    source_env = os.environ if environ is None else environ

    def isolated_env(runtime_home: Path) -> dict[str, str]:
        env = safe_cli_environment(source_env)
        isolated_home = runtime_home / "home"
        isolated_temp = runtime_home / "tmp"
        isolated_home.mkdir(parents=True, exist_ok=True, mode=0o700)
        isolated_temp.mkdir(parents=True, exist_ok=True, mode=0o700)
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
            env[name] = str(isolated_home)
        for name in ("TEMP", "TMP", "TMPDIR"):
            env[name] = str(isolated_temp)
        env["AGENCY_DB_PATH"] = str(db_path.resolve())
        env["AGENCY_CANARY_MODE"] = "1"
        return env

    if host == "codex":
        marketplace = Path(str((native or {}).get("managed_target") or ""))
        marketplace_manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
        if not marketplace.is_dir() or not marketplace_manifest.is_file():
            raise ValueError("managed Codex marketplace is unavailable")
        source_home = Path(
            source_env.get("USERPROFILE")
            or source_env.get("HOME")
            or Path.home()
        ).expanduser()
        original_codex_home = Path(
            source_env.get("CODEX_HOME")
            or (source_home / ".codex")
        ).expanduser()
        auth_source = original_codex_home / "auth.json"

        class SafeCodexCanaryBackend:
            def execute(
                self,
                *,
                task: str,
                workdir: str,
                check: bool = False,
            ) -> dict[str, Any]:
                del check
                with tempfile.TemporaryDirectory(
                    prefix="codex-home-",
                    dir=str(db_path.parent),
                ) as runtime:
                    runtime_home = Path(runtime)
                    os.chmod(runtime_home, stat.S_IRWXU)
                    codex_home = runtime_home / "codex"
                    codex_home.mkdir(mode=0o700)
                    _copy_bounded_auth(
                        auth_source,
                        codex_home / "auth.json",
                        host="Codex",
                    )
                    env = isolated_env(runtime_home)
                    env["CODEX_HOME"] = str(codex_home)
                    setup_commands = (
                        [
                            executable,
                            "plugin",
                            "marketplace",
                            "add",
                            str(marketplace),
                            "--json",
                        ],
                        [
                            executable,
                            "plugin",
                            "add",
                            "agency-preflight@agency-runtime",
                            "--json",
                        ],
                    )
                    for argv in setup_commands:
                        setup = process_runner(
                            argv,
                            timeout=min(timeout, 30),
                            cwd=workdir,
                            env=env,
                            max_output_chars=64 * 1024,
                        )
                        if (
                            setup.returncode != 0
                            or setup.timed_out
                            or setup.stdout_truncated
                            or setup.stderr_truncated
                        ):
                            return {
                                "backend": "codex",
                                "status": "failed",
                                "exit_code": setup.returncode or 1,
                            }
                    inventory = process_runner(
                        [
                            executable,
                            "plugin",
                            "list",
                            "--marketplace",
                            "agency-runtime",
                            "--json",
                        ],
                        timeout=min(timeout, 30),
                        cwd=workdir,
                        env=env,
                        max_output_chars=64 * 1024,
                    )
                    try:
                        inventory_payload = json.loads(inventory.stdout)
                    except json.JSONDecodeError:
                        inventory_payload = None
                    isolated_enabled = (
                        inventory.returncode == 0
                        and not inventory.timed_out
                        and not inventory.stdout_truncated
                        and not inventory.stderr_truncated
                        and _codex_isolated_plugin_enabled(inventory_payload)
                    )
                    if not isolated_enabled:
                        return {
                            "backend": "codex",
                            "status": "failed",
                            "exit_code": inventory.returncode or 1,
                            "profile_scope": "isolated-profile",
                            "isolated_plugin": {
                                "registered": False,
                                "enabled": None,
                            },
                        }
                    argv = [executable, "exec", *CODEX_CANARY_EXEC_OPTIONS]
                    result = process_runner(
                        argv,
                        timeout=timeout,
                        cwd=workdir,
                        env=env,
                        input_text=task,
                        max_output_chars=256_000,
                    )
                record: dict[str, Any] = {
                    "backend": "codex",
                    "profile_scope": "isolated-profile",
                    "isolated_plugin": {
                        "registered": True,
                        "enabled": True,
                    },
                    "status": "completed"
                    if result.returncode == 0
                    and not result.timed_out
                    and not result.stdout_truncated
                    and not result.stderr_truncated
                    else "failed",
                    "exit_code": result.returncode,
                    "stdout_truncated": result.stdout_truncated,
                    "stderr_truncated": result.stderr_truncated,
                }
                if record["status"] == "completed":
                    events: list[dict[str, Any]] = []
                    try:
                        for line in result.stdout.splitlines():
                            if line.strip():
                                event = json.loads(line)
                                if isinstance(event, dict):
                                    events.append(event)
                    except json.JSONDecodeError:
                        record.update(status="failed", exit_code=1)
                    else:
                        completed = any(
                            event.get("type") == "turn.completed"
                            for event in events
                        )
                        messages = [
                            str(event["item"]["text"])
                            for event in events
                            if event.get("type") == "item.completed"
                            and isinstance(event.get("item"), dict)
                            and event["item"].get("type") == "agent_message"
                            and event["item"].get("text") is not None
                        ]
                        if completed and messages:
                            record["output"] = messages[-1]
                        else:
                            record.update(status="failed", exit_code=1)
                return record

        return SafeCodexCanaryBackend()

    marketplace = Path(str((native or {}).get("managed_target") or ""))
    plugin_dir = marketplace / "plugins" / "agency-preflight"
    plugin_manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_dir.is_dir() or not plugin_manifest.is_file():
        raise ValueError("managed Claude plugin is unavailable")
    original_home = Path(
        source_env.get("USERPROFILE")
        or source_env.get("HOME")
        or Path.home()
    ).expanduser()
    original_claude_home = Path(
        source_env.get("CLAUDE_CONFIG_DIR")
        or (original_home / ".claude")
    ).expanduser()
    auth_source = original_claude_home / ".credentials.json"

    class SafeClaudeCanaryBackend:
        def execute(
            self,
            *,
            task: str,
            workdir: str,
            check: bool = False,
        ) -> dict[str, Any]:
            del check
            with tempfile.TemporaryDirectory(
                prefix="claude-home-",
                dir=str(db_path.parent),
            ) as runtime:
                runtime_home = Path(runtime)
                os.chmod(runtime_home, stat.S_IRWXU)
                claude_home = runtime_home / "claude"
                claude_home.mkdir(mode=0o700)
                _copy_bounded_auth(
                    auth_source,
                    claude_home / ".credentials.json",
                    host="Claude",
                )
                env = isolated_env(runtime_home)
                env["CLAUDE_CONFIG_DIR"] = str(claude_home)
                argv = [
                    executable,
                    "-p",
                    "--output-format",
                    "json",
                    "--max-turns",
                    "1",
                    "--no-session-persistence",
                    "--setting-sources",
                    "",
                    "--plugin-dir",
                    str(plugin_dir),
                    "--tools",
                    "",
                    "--disallowedTools",
                    "mcp__*",
                    "--strict-mcp-config",
                    "--permission-mode",
                    "dontAsk",
                ]
                result = process_runner(
                    argv,
                    timeout=timeout,
                    cwd=workdir,
                    env=env,
                    input_text=task,
                    max_output_chars=256_000,
                )
            record: dict[str, Any] = {
                "backend": "claude",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {
                    "load_requested": True,
                    "registered": None,
                    "enabled": None,
                },
                "status": "completed"
                if result.returncode == 0
                and not result.timed_out
                and not result.stdout_truncated
                and not result.stderr_truncated
                else "failed",
                "exit_code": result.returncode,
                "stdout_truncated": result.stdout_truncated,
                "stderr_truncated": result.stderr_truncated,
            }
            if record["status"] == "completed":
                try:
                    payload = json.loads(result.stdout)
                except json.JSONDecodeError:
                    record.update(status="failed", exit_code=1)
                else:
                    if isinstance(payload, dict) and payload.get("result"):
                        record["output"] = payload["result"]
                    else:
                        record.update(status="failed", exit_code=1)
            return record

    return SafeClaudeCanaryBackend()


def _ids(activity: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    return {
        name: {str(row.get("id")) for row in rows if row.get("id")}
        for name, rows in activity.items()
    }


def _evidence_delta(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    previous = _ids(before)
    return {
        name: [row for row in rows if str(row.get("id")) not in previous.get(name, set())]
        for name, rows in after.items()
    }


def _response_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "result", "message", "output"):
            text = _response_text(value.get(key))
            if text:
                return text
        return ""
    if isinstance(value, list):
        return "\n".join(filter(None, (_response_text(item) for item in value)))
    return ""


def _evidence_summary(
    delta: dict[str, list[dict[str, Any]]],
    host: str,
    *,
    expected_query_hash: str,
) -> dict[str, Any]:
    routing = [
        row
        for row in delta.get("routing", [])
        if row.get("query_hash") == expected_query_hash
    ]
    finalizations = [
        row for row in delta.get("finalizations", []) if row.get("host") == host
    ]
    receipts = [row for row in delta.get("receipts", []) if row.get("host") == host]
    route_traces = {str(row.get("trace_id")) for row in routing if row.get("trace_id")}
    final_traces = {
        str(row.get("trace_id")) for row in finalizations if row.get("trace_id")
    }
    receipt_traces = {
        str(row.get("trace_id")) for row in receipts if row.get("trace_id")
    }
    correlated = sorted(route_traces & final_traces)
    receipt_correlated = sorted(set(correlated) & receipt_traces)
    receipt_required = host in RECEIPT_CAPABLE_HOSTS
    return {
        "new_ids": {
            name: [str(row.get("id")) for row in rows if row.get("id")]
            for name, rows in delta.items()
        },
        "counts": {name: len(rows) for name, rows in delta.items()},
        "host_finalization_count": len(finalizations),
        "host_receipt_count": len(receipts),
        "correlated_trace_ids": correlated,
        "receipt_correlated_trace_ids": receipt_correlated,
        "receipt_required": receipt_required,
        "receipt_proven": bool(receipt_correlated),
        "query_hash": expected_query_hash,
    }


def run_canary(
    host: str,
    *,
    execute: bool = False,
    confirm: str = "",
    db_path: str | Path | None = None,
    timeout: float = 120,
    inspector: Callable[[str], dict[str, Any]] = _default_inspector,
    backend_factory: Callable[..., Any] = _backend,
) -> dict[str, Any]:
    """Build a nonmutating readiness report or run an exact-confirmed canary."""
    if host not in SUPPORTED_HOSTS:
        raise ValueError(f"unsupported host: {host}")
    path = Path(db_path).expanduser() if db_path else _default_db_path()
    native = inspector(host)
    control = _read_control_without_writes(path, host)
    unmet: list[str] = []
    if native.get("executable_discovered") is not True:
        unmet.append("host executable not discovered")
    profile_scope = (
        "isolated-profile"
        if host in ISOLATED_CANARY_HOSTS
        else "current-profile"
    )
    if host not in ISOLATED_CANARY_HOSTS:
        if native.get("registered") is not True:
            unmet.append("Agency Runtime plugin registration not proven")
        if native.get("enabled") is not True:
            unmet.append("native plugin enablement not proven")
    if not native.get("host_version"):
        unmet.append("native host version not proven")
    if not native.get("install_id") or not native.get("bundle_digest"):
        unmet.append("managed bundle identity not proven")
    if host not in SAFE_CANARY_HOSTS:
        unmet.append("host has no proven read-only, no-tools noninteractive canary mode")
    if control.get("enabled") is not True:
        unmet.append("Agency Runtime soft control is disabled or unverified")

    platform_record = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
    }
    report: dict[str, Any] = {
        "schema_version": "agency.host_canary.v1",
        "sampled_at": _utc_now(),
        "host": host,
        "profile_scope": profile_scope,
        "platform": platform_record,
        "native": native,
        "real_profile_native": native,
        "runtime_control": control,
        "ready": not unmet,
        "live_attempted": False,
        "canary_passed": False,
        "unmet_prerequisites": unmet,
    }
    if not execute:
        return report

    expected = f"RUN LIVE {host} CANARY"
    if confirm != expected:
        report["unmet_prerequisites"].append(
            f"confirmation must exactly match: {expected}"
        )
        return report
    if unmet:
        return report

    store = Store(path)
    before = store.recent_runtime_activity(limit=200)
    nonce = secrets.token_hex(16)
    prompt = f"{CANARY_PROMPT}\n\nCanary nonce: {nonce}"
    expected_query_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        if backend_factory is _backend:
            backend = backend_factory(
                host,
                db_path=path,
                timeout=timeout,
                native=native,
            )
        else:
            backend = backend_factory(host, db_path=path, timeout=timeout)
    except Exception:
        report["unmet_prerequisites"].append(
            "safe noninteractive canary backend is unavailable"
        )
        return report
    report["live_attempted"] = True
    try:
        with tempfile.TemporaryDirectory(
            prefix="canary-",
            dir=str(path.parent),
        ) as workdir:
            result = backend.execute(
                task=prompt,
                workdir=workdir,
                check=False,
            )
    except Exception:
        report["unmet_prerequisites"].append(
            "safe host invocation failed before evidence could be evaluated"
        )
        return report
    after = store.recent_runtime_activity(limit=200)
    delta = _evidence_delta(before, after)
    evidence = _evidence_summary(
        delta,
        host,
        expected_query_hash=expected_query_hash,
    )
    from agency_runtime.core.header.contract import validate_header

    response = _response_text(result.get("output"))
    header_valid, header_missing = validate_header(response)
    process_ok = result.get("status") == "completed" and result.get("exit_code") == 0
    result_scope = str(result.get("profile_scope") or profile_scope)
    isolated_plugin = (
        result.get("isolated_plugin")
        if isinstance(result.get("isolated_plugin"), dict)
        else None
    )
    plugin_invoked = bool(evidence["correlated_trace_ids"])
    profile_proven = (
        result_scope == "current-profile"
        or (
            result_scope == "isolated-profile"
            and isolated_plugin is not None
            and (
                (
                    host == "codex"
                    and isolated_plugin.get("registered") is True
                    and isolated_plugin.get("enabled") is True
                )
                or (
                    host == "claude"
                    and isolated_plugin.get("load_requested") is True
                    and plugin_invoked
                )
            )
        )
    )
    rendered_isolated_plugin = (
        dict(isolated_plugin) if isolated_plugin is not None else None
    )
    if host == "claude" and rendered_isolated_plugin is not None:
        rendered_isolated_plugin["loaded"] = True if plugin_invoked else None
        rendered_isolated_plugin["invoked"] = True if plugin_invoked else None
    report.update(
        {
            "sampled_at": _utc_now(),
            "live_attempted": True,
            "invocation": {
                "backend": result.get("backend", host),
                "status": result.get("status"),
                "exit_code": result.get("exit_code"),
                "timed_out": result.get("status") == "timed_out",
                "stdout_truncated": bool(result.get("stdout_truncated")),
                "stderr_truncated": bool(result.get("stderr_truncated")),
                "header_valid": header_valid,
                "header_missing": header_missing,
                "profile_scope": result_scope,
                "isolated_plugin": rendered_isolated_plugin,
            },
            "evidence": evidence,
        }
    )
    evidence_passed = bool(
        evidence["correlated_trace_ids"]
        and (
            not evidence["receipt_required"]
            or evidence["receipt_proven"]
        )
    )
    candidate_passed = bool(
        process_ok and header_valid and evidence_passed and profile_proven
    )
    if not process_ok:
        report["unmet_prerequisites"].append("host invocation did not complete successfully")
    if not profile_proven:
        report["unmet_prerequisites"].append(
            "canary profile plugin registration and enablement were not proven"
        )
    if not header_valid:
        report["unmet_prerequisites"].append("final response header was not proven")
    if not evidence["correlated_trace_ids"]:
        report["unmet_prerequisites"].append(
            "correlated routing and finalization evidence was not proven"
        )
    elif evidence["receipt_required"] and not evidence["receipt_proven"]:
        report["unmet_prerequisites"].append(
            "the host exposes response telemetry but a correlated receipt was not proven"
        )
    if candidate_passed:
        try:
            attestation = store.record_host_canary_attestation(
                host=host,
                profile_scope=result_scope,
                platform_system=platform_record["system"],
                platform_release=platform_record["release"],
                platform_machine=platform_record["machine"],
                host_version=str(native["host_version"]),
                plugin_version=PLUGIN_VERSION,
                install_id=str(native["install_id"]),
                bundle_digest=str(native["bundle_digest"]),
                trace_id=evidence["correlated_trace_ids"][0],
                passed_at=report["sampled_at"],
            )
        except Exception:
            report["unmet_prerequisites"].append(
                "successful canary evidence could not be durably attested"
            )
            report["attestation_persisted"] = False
        else:
            report["attestation_persisted"] = True
            report["attestation"] = attestation
            report["canary_passed"] = True
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect or explicitly execute an Agency Runtime host canary"
    )
    parser.add_argument("host", choices=SUPPORTED_HOSTS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--db", default=None)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_canary(
        args.host,
        execute=args.execute,
        confirm=args.confirm,
        db_path=args.db,
        timeout=args.timeout,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if (report["canary_passed"] if args.execute else report["ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
