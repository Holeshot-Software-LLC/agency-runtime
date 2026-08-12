"""Deterministic Agency Runtime smoke checks.

The smoke suite intentionally avoids network calls and live host mutation. It
verifies the local SQLite store, host-parity eval contract, and generated host
plugin templates in a temporary HOME.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.evals.host_parity import run_host_parity_eval
from agency_runtime.core.installer import (
    HOSTS,
    detect_installed_agents,
    install_agent_adapter,
    toggle_agency,
)
from agency_runtime.core.installer_contracts import (
    ADAPTER_LAUNCHER_MANIFEST,
    CODEX_HOOK_EVENTS,
)
from agency_runtime.core.installer_payloads import bind_launcher_artifact_paths
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.private_paths import ensure_private_directory, private_temporary_directory
from agency_runtime.core.process_argv import (
    freeze_process_argv,
    persistent_artifacts_from_manifest,
    prepare_process_argv,
    repository_forbidden_roots,
    revalidate_process_argv,
    snapshot_persistent_artifacts,
)
from agency_runtime.core.store.sqlite import Store


class _FakeHookContext:
    def __init__(self) -> None:
        self.hooks: dict[str, Any] = {}
        self.commands: dict[str, Any] = {}
        self.command_options: dict[str, dict[str, Any]] = {}

    def register_hook(self, name: str, fn: Any) -> None:
        self.hooks[name] = fn

    def register_command(self, name: str, fn: Any, **kwargs: Any) -> None:
        self.commands[name] = fn
        self.command_options[name] = dict(kwargs)


def _load_plugin_json(path: Path, *, label: str) -> Any:
    payload = read_bounded_regular_file(path, limit=1024 * 1024, label=label)
    return safe_load_bounded_json(
        payload,
        maximum_bytes=1024 * 1024,
        maximum_depth=32,
        maximum_nodes=10_000,
    )


@contextmanager
def _temporary_env(**values: str) -> Iterator[None]:
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _check(name: str, fn: Any) -> dict[str, Any]:
    try:
        detail = fn() or {}
        return {"name": name, "status": "pass", "detail": detail}
    except _SkipHost as exc:
        # A host whose CLI/native state is absent (e.g. zcode on a runner that
        # can't install it) is skipped, not failed. --all means "every host this
        # machine could actually exercise"; an un-installable host is truthful as
        # a skip and must not block the smoke.
        return {"name": name, "status": "skip", "detail": {"reason": str(exc)}}
    except Exception as exc:
        return {"name": name, "status": "fail", "error": f"{type(exc).__name__}: {exc}"}


class _SkipHost(Exception):
    """Signal that a host cannot be exercised on this machine (skip, not fail)."""


def _prepare_smoke_launcher_paths() -> tuple[str, str]:
    """Prepare one shared launcher after installer test bindings are active."""

    from agency_runtime.core.installer_orchestration import _prepare_adapter_launcher_paths

    return _prepare_adapter_launcher_paths()


def _prepare_fake_host_home(home: Path, host: str) -> None:
    if host == "hermes":
        ensure_private_directory(home / ".hermes" / "plugins")
    elif host == "openclaw":
        ensure_private_directory(home / ".openclaw")
    elif host == "codex":
        ensure_private_directory(home / ".codex")
    elif host == "claude":
        ensure_private_directory(home / ".claude")
    elif host == "zcode":
        config_dir = ensure_private_directory(home / ".zcode" / "cli", product_owned=False)
        (config_dir / "config.json").write_text(
            json.dumps(
                {
                    "theme": "preserved-by-agency-smoke",
                    "hooks": {
                        "enabled": True,
                        "timeoutMs": 30_000,
                        "events": {
                            "SessionStart": [
                                {
                                    "hooks": [
                                        {
                                            "type": "process",
                                            "command": str(Path(sys.executable).resolve()),
                                            "args": ["-c", "pass"],
                                            "enabled": True,
                                            "timeoutMs": 1_000,
                                        }
                                    ]
                                }
                            ]
                        },
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )


def _validate_bridge_mcp(plugin_root: Path, *, host: str) -> None:
    """Validate the MCP config shipped with a bridge-host (Hermes/OpenClaw) bundle."""
    mcp_path = plugin_root / ".mcp.json"
    if not mcp_path.exists():
        raise RuntimeError(f"{host} bundle missing its Agency Runtime MCP config")
    mcp = _load_plugin_json(mcp_path, label=f"{host} MCP manifest")
    server = mcp.get("mcpServers", {}).get("agency-runtime", {})
    args = server.get("args")
    if (
        not isinstance(args, list)
        or "agency_runtime.server.mcp" not in args
        or "--stdio" not in args
    ):
        raise RuntimeError(f"{host} bundle has invalid Agency Runtime MCP command")
    if not str(server.get("command") or "").strip():
        raise RuntimeError(f"{host} MCP config lacks an interpreter command")


def _smoke_openclaw_plugin(host: str, plugin_path: Path) -> dict[str, Any]:
    """Validate OpenClaw's native JS plugin package without importing it in Python."""
    manifest_path = plugin_path.parent / "openclaw.plugin.json"
    package_path = plugin_path.parent / "package.json"
    if not manifest_path.exists() or not package_path.exists():
        raise RuntimeError("missing OpenClaw plugin manifest or package.json")

    manifest = _load_plugin_json(manifest_path, label="OpenClaw plugin manifest")
    package = _load_plugin_json(package_path, label="OpenClaw package manifest")
    code = plugin_path.read_text(encoding="utf-8")
    if manifest.get("id") != "agency-preflight":
        raise RuntimeError("invalid OpenClaw plugin manifest id")
    if manifest.get("mcpServers") != "./.mcp.json":
        raise RuntimeError("OpenClaw manifest does not declare its MCP component")
    if package.get("openclaw", {}).get("extensions") != ["./index.js"]:
        raise RuntimeError("invalid OpenClaw package extension entry")
    _validate_bridge_mcp(plugin_path.parent, host=host)
    required_tokens = {
        "before_prompt_build",
        "before_agent_finalize",
        "api.registerCommand",
        'name: "agency"',
        'description: "Agency Runtime read-only status; persistent on/off commands are denied"',
        "agency_runtime.adapters.openclaw.node_bridge",
        "execFile",
    }
    missing_tokens = sorted(token for token in required_tokens if token not in code)
    if missing_tokens:
        raise RuntimeError(f"OpenClaw plugin missing tokens: {', '.join(missing_tokens)}")
    # The generated bridge is bound to the installer interpreter and package
    # bootstrap. Runtime environment substitution and synchronous child
    # execution are both forbidden contracts.
    forbidden_tokens = {"spawnSync", "AGENCY_RUNTIME_PYTHON"}
    present_forbidden = sorted(token for token in forbidden_tokens if token in code)
    if present_forbidden:
        raise RuntimeError(
            f"OpenClaw plugin contains forbidden bridge tokens: {', '.join(present_forbidden)}"
        )

    syntax_check = "skipped: node unavailable"
    node = os.environ.get("AGENCY_CI_NODE") or "node"
    current_directory = Path.cwd()
    forbidden_roots = repository_forbidden_roots(current_directory)
    try:
        prepared = freeze_process_argv(
            prepare_process_argv(
                [node, "--check", str(plugin_path)],
                resolver=shutil.which,
                current_directory=current_directory,
                forbidden_roots=forbidden_roots,
            ),
            forbidden_roots=forbidden_roots,
        )
        revalidate_process_argv(prepared)
        check = subprocess.run(
            prepared,
            text=True,
            capture_output=True,
            timeout=15,
        )
    except FileNotFoundError:
        pass
    except OSError as exc:
        syntax_check = f"skipped: node not runnable ({type(exc).__name__})"
    else:
        if check.returncode != 0:
            raise RuntimeError((check.stderr or check.stdout or "node --check failed").strip())
        syntax_check = "passed"
    return {
        "host": host,
        "plugin_path": str(plugin_path),
        "format": "openclaw-js",
        "syntax_check": syntax_check,
    }


def _validate_codex_hooks(hooks: Any) -> list[str]:
    """Validate the exact command-hook contract consumed by current Codex."""
    hook_map = hooks.get("hooks") if isinstance(hooks, dict) else None
    if not isinstance(hook_map, dict) or tuple(hook_map) != CODEX_HOOK_EVENTS:
        raise RuntimeError("Codex bundle has an invalid hook event set")
    for event in CODEX_HOOK_EVENTS:
        registrations = hook_map[event]
        if (
            not isinstance(registrations, list)
            or len(registrations) != 1
            or not isinstance(registrations[0], dict)
        ):
            raise RuntimeError(f"Codex {event} hook registration is invalid")
        registration = registrations[0]
        handlers = registration.get("hooks")
        if (
            not isinstance(handlers, list)
            or len(handlers) != 1
            or not isinstance(handlers[0], dict)
        ):
            raise RuntimeError(f"Codex {event} command handler is invalid")
        handler = handlers[0]
        if "timeoutSec" in handler:
            raise RuntimeError("Codex hook uses unsupported input key timeoutSec; use timeout")
        timeout = handler.get("timeout")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout <= 0:
            raise RuntimeError(f"Codex {event} hook timeout is invalid")
        if handler.get("type") != "command" or handler.get("async") is not False:
            raise RuntimeError(f"Codex {event} hook must be a synchronous command handler")
        if event == "UserPromptSubmit" and handler.get("additionalContextLimit") != 0:
            raise RuntimeError("Codex UserPromptSubmit hook must preserve the complete plan")
        command = handler.get("command")
        command_windows = handler.get("commandWindows")
        if not (
            isinstance(command, str)
            and "agency_runtime.cli" in command
            and "hook codex" in command
            and isinstance(command_windows, str)
            and all(
                token in command_windows for token in ("'agency_runtime.cli'", "'hook'", "'codex'")
            )
        ):
            raise RuntimeError(f"Codex {event} hook command is invalid")
        if not command_windows.startswith("& "):
            raise RuntimeError(f"Codex {event} Windows hook must use the PowerShell call operator")
        if event == "PostToolUse" and registration.get("matcher") != "*":
            raise RuntimeError("Codex PostToolUse hook must match every tool")
    return list(CODEX_HOOK_EVENTS)


def _installed_launcher_paths(plugin_root: Path) -> tuple[str, str]:
    """Return one content-current launcher pair bound by the install manifest."""

    manifest = _load_plugin_json(
        plugin_root / ADAPTER_LAUNCHER_MANIFEST,
        label="Agency Runtime launcher manifest",
    )
    if not isinstance(manifest, dict):
        raise RuntimeError("Agency Runtime install manifest is invalid")
    try:
        frozen = persistent_artifacts_from_manifest(manifest.get("artifacts"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Agency Runtime launcher identity is invalid") from exc
    if len(frozen) != 2:
        raise RuntimeError("Agency Runtime launcher identity must bind two artifacts")
    observed = snapshot_persistent_artifacts([item.lexical_path for item in frozen])
    if observed != frozen:
        raise RuntimeError("Agency Runtime launcher artifacts changed after installation")
    return frozen[0].lexical_path, frozen[1].lexical_path


def _smoke_marketplace_bundle(host: str, plugin_path: Path) -> dict[str, Any]:
    """Validate native Codex/Claude plugin layout and executable MCP wiring."""
    manifest = _load_plugin_json(plugin_path, label=f"{host} plugin manifest")
    plugin_root = plugin_path.parents[1]
    hooks_path = plugin_root / "hooks" / "hooks.json"
    mcp_path = plugin_root / ".mcp.json"
    skill_path = plugin_root / "skills" / "agency" / "SKILL.md"
    if manifest.get("name") != "agency-preflight":
        raise RuntimeError(f"invalid {host} plugin manifest name")
    if not hooks_path.exists() or not mcp_path.exists() or not skill_path.exists():
        raise RuntimeError(f"{host} bundle missing hooks, MCP config, or control skill")
    hooks = _load_plugin_json(hooks_path, label=f"{host} hooks manifest")
    mcp = _load_plugin_json(mcp_path, label=f"{host} MCP manifest")
    if "UserPromptSubmit" not in hooks.get("hooks", {}):
        raise RuntimeError(f"{host} bundle missing UserPromptSubmit hook")
    if host == "codex" and manifest.get("hooks") != "./hooks/hooks.json":
        raise RuntimeError("Codex manifest does not declare its hooks component")
    validated_hooks = _validate_codex_hooks(hooks) if host == "codex" else sorted(hooks["hooks"])
    skill = skill_path.read_text(encoding="utf-8")
    control_tokens = {"agency.host_status", "owner-authenticated dashboard UI", "normal user shell"}
    if any(token not in skill for token in control_tokens):
        raise RuntimeError(f"{host} control skill is incomplete")
    if "agency.host_control" in skill:
        raise RuntimeError(f"{host} control skill exposes model-facing mutation authority")
    server = mcp.get("mcpServers", {}).get("agency-runtime", {})
    args = server.get("args")
    try:
        install_root = plugin_path.parents[3]
    except IndexError as exc:
        raise RuntimeError(f"{host} plugin path is outside its marketplace layout") from exc
    interpreter, bootstrap = _installed_launcher_paths(install_root)
    expected_prefix = [
        "-I",
        "-S",
        bootstrap,
        "agency_runtime.server.mcp",
        "--stdio",
    ]
    if not isinstance(args, list) or args[:5] != expected_prefix:
        raise RuntimeError(f"{host} bundle has invalid Agency Runtime MCP command")
    if len(args) not in {5, 7} or (
        len(args) == 7 and (args[5] != "--config" or not Path(str(args[6])).is_absolute())
    ):
        raise RuntimeError(f"{host} bundle has invalid Agency Runtime config binding")
    command = Path(str(server.get("command") or ""))
    if not command.is_absolute():
        raise RuntimeError(f"{host} MCP command is not an absolute interpreter path")
    if str(command) != interpreter:
        raise RuntimeError(f"{host} MCP command does not match its installed launcher identity")
    return {
        "host": host,
        "plugin_path": str(plugin_path),
        "format": f"{host}-plugin-bundle",
        "hooks": validated_hooks,
        "mcp_server": "agency-runtime",
    }


def _smoke_zcode_bundle(host: str, plugin_path: Path, tmp_home: Path) -> dict[str, Any]:
    """Exercise the generated ZCode fragment and direct config lifecycle."""

    from agency_runtime.core.installer_zcode import ZCODE_EVENTS, zcode_config_path

    fragment = _load_plugin_json(plugin_path, label="ZCode hook fragment")
    hooks = fragment.get("hooks")
    if not isinstance(hooks, dict) or set(hooks.get("events", {})) != set(ZCODE_EVENTS):
        raise RuntimeError("ZCode bundle has an invalid hooks.events contract")
    if hooks.get("enabled") is not True:
        raise RuntimeError("ZCode bundle must declare hooks enabled")
    plugin_root = plugin_path.parent
    interpreter, bootstrap = _installed_launcher_paths(plugin_root)
    config_path = zcode_config_path(home_dir=tmp_home)
    before_repeat = read_bounded_regular_file(
        config_path,
        limit=1024 * 1024,
        label="installed ZCode config",
    )
    config = safe_load_bounded_json(before_repeat)
    if config.get("theme") != "preserved-by-agency-smoke":
        raise RuntimeError("ZCode install did not preserve unrelated config")
    configured_hooks = config.get("hooks", {})
    configured_events = configured_hooks.get("events", {})
    for event in ZCODE_EVENTS:
        registrations = configured_events.get(event)
        if not isinstance(registrations, list):
            raise RuntimeError(f"ZCode config is missing {event}")
        agency_handlers = [
            handler
            for registration in registrations
            if isinstance(registration, dict)
            for handler in registration.get("hooks", [])
            if isinstance(handler, dict)
            and handler.get("type") == "process"
            and "agency_runtime.cli" in handler.get("args", [])
        ]
        if len(agency_handlers) != 1:
            raise RuntimeError(f"ZCode {event} does not have one Agency process handler")
        handler = agency_handlers[0]
        args = handler.get("args")
        expected_prefix = ["-I", "-S", bootstrap, "agency_runtime.cli", "hook", "zcode"]
        if handler.get("command") != interpreter or args[:6] != expected_prefix:
            raise RuntimeError(f"ZCode {event} is not bound to the installed launcher")
        event_index = args.index("--event")
        if args[event_index + 1] != event:
            raise RuntimeError(f"ZCode {event} handler argv is not event-bound")

    repeated = install_agent_adapter(host, home_dir=tmp_home)
    after_repeat = read_bounded_regular_file(
        config_path,
        limit=1024 * 1024,
        label="repeated ZCode config",
    )
    if not repeated.get("ok") or not repeated.get("filesystem", {}).get("unchanged"):
        raise RuntimeError("repeated ZCode install was not idempotent")
    if after_repeat != before_repeat:
        raise RuntimeError("repeated ZCode install rewrote unchanged config")

    disabled = toggle_agency(host, False, home_dir=tmp_home)
    enabled = toggle_agency(host, True, home_dir=tmp_home)
    if not disabled.get("ok") or disabled.get("enabled") is not False:
        raise RuntimeError("ZCode per-handler disable postcondition failed")
    if not enabled.get("ok") or enabled.get("enabled") is not True:
        raise RuntimeError("ZCode per-handler enable postcondition failed")

    session_handler = next(
        handler
        for registration in configured_events["SessionStart"]
        for handler in registration.get("hooks", [])
        if "agency_runtime.cli" in handler.get("args", [])
    )
    prepared = freeze_process_argv(
        prepare_process_argv([session_handler["command"], *session_handler["args"]])
    )
    revalidate_process_argv(prepared)
    invocation = subprocess.run(
        prepared,
        input=json.dumps(
            {
                "hookEventName": "SessionStart",
                "sessionId": "zcode-smoke",
                "cwd": str(tmp_home),
            }
        ),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if invocation.returncode != 0:
        raise RuntimeError(
            (invocation.stderr or invocation.stdout or "ZCode hook invocation failed").strip()
        )
    if invocation.stdout.strip():
        safe_load_bounded_json(invocation.stdout.strip())
    return {
        "host": host,
        "plugin_path": str(plugin_path),
        "format": "zcode-config-hooks",
        "hooks": list(ZCODE_EVENTS),
        "preserved_existing_config": True,
        "idempotent": True,
        "toggle_verified": True,
        "process_hook_invoked": True,
    }


def _smoke_generated_plugin(host: str, tmp_home: Path) -> dict[str, Any]:
    _prepare_fake_host_home(tmp_home, host)
    result = install_agent_adapter(host, home_dir=tmp_home)
    if not result.get("ok"):
        error = str(result.get("error") or result)
        # A host whose CLI/native state is absent cannot be exercised on this
        # machine (e.g. zcode on a GitHub runner). Skip it truthfully rather
        # than fail the whole smoke.
        if "is not installed on this machine" in error:
            raise _SkipHost(error)
        raise RuntimeError(error)

    plugin_path = Path(str(result["plugin_path"]))
    if host == "openclaw":
        return _smoke_openclaw_plugin(host, plugin_path)

    if host == "zcode":
        return _smoke_zcode_bundle(host, plugin_path, tmp_home)

    if host in {"codex", "claude"}:
        return _smoke_marketplace_bundle(host, plugin_path)

    spec = importlib.util.spec_from_file_location(f"agency_runtime_smoke_{host}", plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import generated plugin: {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ctx = _FakeHookContext()
    module.register(ctx)
    required = {
        "pre_llm_call",
        "post_tool_call",
        "post_api_request",
        "pre_verify",
        "transform_llm_output",
        "on_session_end",
    }
    missing = sorted(required - set(ctx.hooks))
    if missing:
        raise RuntimeError(f"missing hooks: {', '.join(missing)}")
    if set(ctx.commands) != {"agency"}:
        raise RuntimeError("missing Hermes agency control command")
    description = str(ctx.command_options["agency"].get("description") or "")
    if "read-only status" not in description or "on/off commands are denied" not in description:
        raise RuntimeError("Hermes agency command does not declare its read-only authority")
    status = ctx.commands["agency"]("status")
    if "Agency Runtime is enabled for hermes." not in status:
        raise RuntimeError(f"Hermes agency status command returned an invalid response: {status!r}")
    denied = ctx.commands["agency"]("off")
    if "remains enabled" not in denied or "was denied" not in denied:
        raise RuntimeError(f"Hermes agency mutation command did not fail closed: {denied!r}")
    repeated_status = ctx.commands["agency"]("status")
    if "Agency Runtime is enabled for hermes." not in repeated_status:
        raise RuntimeError("Hermes agency mutation command changed persistent state")
    ctx.hooks["post_api_request"](response={}, model="task-general", session_id=f"smoke-{host}")
    plugin_yaml = plugin_path.parent / "plugin.yaml"
    if not plugin_yaml.exists() or "mcp_servers: ./.mcp.json" not in plugin_yaml.read_text(
        encoding="utf-8"
    ):
        raise RuntimeError("Hermes plugin.yaml does not declare its MCP component")
    _validate_bridge_mcp(plugin_path.parent, host=host)
    return {"host": host, "plugin_path": str(plugin_path), "adapter": "HermesBridge"}


def run_smoke(*, all_hosts: bool = False, host: str | None = None) -> dict[str, Any]:
    """Run local deterministic smoke checks and return a JSON-safe report."""
    # --all means "every host this machine could actually exercise", not "every
    # known host including ones whose CLI/native state is absent". A host that
    # install_agent_adapter reports as not installed (e.g. zcode on a runner that
    # cannot install it) is skipped via _SkipHost in _smoke_generated_plugin,
    # never failed. --agent narrows to one host's generated plugin.
    if host is not None:
        if host not in HOSTS:
            raise ValueError(f"unsupported smoke host: {host}")
        hosts = [host]
    else:
        hosts = sorted(HOSTS) if all_hosts else detect_installed_agents()
    checks: list[dict[str, Any]] = []
    prepared_launcher: tuple[str, str] | None = None
    launcher_error: Exception | None = None
    launcher_prepared = False

    def _smoke_host(host: str, tmp_home: Path) -> dict[str, Any]:
        nonlocal prepared_launcher, launcher_error, launcher_prepared
        if len(hosts) < 2:
            return _smoke_generated_plugin(host, tmp_home)
        if not launcher_prepared:
            launcher_prepared = True
            try:
                prepared_launcher = _prepare_smoke_launcher_paths()
            except Exception as exc:  # surfaced through the typed smoke result
                launcher_error = exc
        if launcher_error is not None:
            raise RuntimeError(
                "shared smoke launcher preparation failed: "
                f"{type(launcher_error).__name__}: {launcher_error}"
            ) from launcher_error
        if prepared_launcher is None:  # pragma: no cover - guarded state invariant
            raise RuntimeError("shared smoke launcher preparation returned no identity")
        with bind_launcher_artifact_paths(prepared_launcher):
            return _smoke_generated_plugin(host, tmp_home)

    from agency_runtime.core.config import (
        AgencyConfig,
        StoreConfig,
        config_to_yaml,
        reset_config_cache,
    )

    with private_temporary_directory(prefix="smoke") as tmp_home:
        smoke_db = tmp_home / "agency.db"
        smoke_config = tmp_home / ".agency-runtime" / "agency.yaml"
        smoke_config.parent.mkdir(mode=0o700)
        smoke_config.write_text(
            config_to_yaml(
                AgencyConfig(store=StoreConfig(db_path=str(smoke_db))),
                redact=False,
            ),
            encoding="utf-8",
            newline="\n",
        )
        smoke_config.chmod(0o600)
        with _temporary_env(
            AGENCY_DB_PATH=str(smoke_db),
            AGENCY_CONFIG_PATH=str(smoke_config),
        ):
            # Config is process-global. Reset on both sides so a caller that
            # previously loaded its real profile cannot leak that Store path
            # into generated adapters, and the smoke profile cannot leak out.
            reset_config_cache()
            try:
                store = Store(smoke_db)
                checks.append(_check("sqlite_store", lambda: store.database_stats()))

                def _active_or_starter_roster() -> dict[str, Any]:
                    active_count = len(store.get_enabled_roster())
                    if active_count > 0:
                        return {"agent_count": active_count, "source": "active"}
                    return {"agent_count": len(STARTER_ROSTER), "source": "starter_roster"}

                checks.append(_check("routing_roster_available", _active_or_starter_roster))

                def _host_parity_eval() -> dict[str, Any]:
                    report = run_host_parity_eval()
                    if not report["passed"]:
                        failures = [
                            f"{case.get('name')}: {case.get('error')}"
                            for case in report.get("cases", [])
                            if not case.get("passed")
                        ]
                        raise RuntimeError(
                            f"host-parity eval failed: {report['failed_count']} failed; "
                            + "; ".join(failures[:3])
                        )
                    return {
                        "passed_count": report["passed_count"],
                        "failed_count": report["failed_count"],
                    }

                checks.append(_check("host_parity_eval", _host_parity_eval))

                if not hosts:
                    checks.append(
                        {
                            "name": "host_plugins",
                            "status": "skip",
                            "detail": {"reason": "no installed hosts detected"},
                        }
                    )
                else:
                    checks.extend(
                        _check(
                            f"plugin_{host}",
                            lambda host=host: _smoke_host(host, tmp_home),
                        )
                        for host in hosts
                    )
            finally:
                reset_config_cache()

    passed = all(check["status"] in {"pass", "skip"} for check in checks)
    failed_count = sum(1 for check in checks if check["status"] == "fail")
    skipped_count = sum(1 for check in checks if check["status"] == "skip")
    return {
        "passed": passed,
        "passed_count": sum(1 for check in checks if check["status"] == "pass"),
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "checks": checks,
    }


__all__ = ["run_smoke"]
