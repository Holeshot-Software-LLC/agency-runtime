"""Native host registration planning and lifecycle commands."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_contracts import (
    HOSTS,
    MARKETPLACE_ID,
    PLUGIN_ID,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
)


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _dispatch(name: str, *args: Any, **kwargs: Any) -> Any:
    return getattr(_facade(), name)(*args, **kwargs)


def _atomic_install_tree(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _dispatch("_atomic_install_tree", *args, **kwargs)


def _bool_field(*args: Any, **kwargs: Any) -> bool | None:
    return _dispatch("_bool_field", *args, **kwargs)


def _bundle_files(*args: Any, **kwargs: Any) -> tuple[dict[str, str], str]:
    return _dispatch("_bundle_files", *args, **kwargs)


def _can_execute_native(*args: Any, **kwargs: Any) -> bool:
    return _dispatch("_can_execute_native", *args, **kwargs)


def _hermes_text_plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _dispatch("_hermes_text_plugin_record", *args, **kwargs)


def _host_root(*args: Any, **kwargs: Any) -> Path:
    return _dispatch("_host_root", *args, **kwargs)


def _json_output(*args: Any, **kwargs: Any) -> Any:
    return _dispatch("_json_output", *args, **kwargs)


def _marketplace_registered(*args: Any, **kwargs: Any) -> bool:
    return _dispatch("_marketplace_registered", *args, **kwargs)


def _native_command_plan(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    return _dispatch("_native_command_plan", *args, **kwargs)


def _openclaw_gateway_live(*args: Any, **kwargs: Any) -> tuple[bool, NativeCommandResult]:
    return _dispatch("_openclaw_gateway_live", *args, **kwargs)


def _plugin_record(*args: Any, **kwargs: Any) -> dict[str, Any] | None:
    return _dispatch("_plugin_record", *args, **kwargs)


def _plugin_target(*args: Any, **kwargs: Any) -> Path:
    return _dispatch("_plugin_target", *args, **kwargs)


def _resolve_binary(*args: Any, **kwargs: Any) -> str | None:
    return _dispatch("_resolve_binary", *args, **kwargs)


def _resolve_install_config(*args: Any, **kwargs: Any) -> AgencyConfig:
    return _dispatch("_resolve_install_config", *args, **kwargs)


def _root_state(*args: Any, **kwargs: Any) -> tuple[bool, bool, list[str]]:
    return _dispatch("_root_state", *args, **kwargs)


def _run_native(*args: Any, **kwargs: Any) -> NativeCommandResult:
    return _dispatch("_run_native", *args, **kwargs)


def openclaw_gateway_live(
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
    if signals["running"] is False or status in {
        "stopped",
        "not-running",
        "not_running",
    }:
        return False, probe
    return None, probe


_RegistrationResult = tuple[list[dict[str, Any]], bool, str | None]


class _RegistrationSession:
    """Accumulate ordered native command evidence for one host registration."""

    def __init__(
        self,
        host: str,
        target: Path,
        *,
        home_dir: str | Path | None,
        command_runner: CommandRunner | None,
    ) -> None:
        self.host = host
        self.binary = str(HOSTS[host]["binary"])
        self.target = target
        self.home_dir = home_dir
        self.command_runner = command_runner
        self.steps: list[dict[str, Any]] = []

    def run(
        self,
        name: str,
        command: Sequence[str],
        *,
        timeout: float = 30,
    ) -> NativeCommandResult:
        result = _run_native(
            command,
            host=self.host,
            home_dir=self.home_dir,
            command_runner=self.command_runner,
            timeout=timeout,
        )
        self.steps.append({"name": name, **result.to_dict()})
        return result

    def result(
        self,
        proven: bool,
        failed_step: str | None = None,
    ) -> _RegistrationResult:
        return self.steps, proven, failed_step


def _register_hermes(
    session: _RegistrationSession,
    _force_refresh: bool,
) -> _RegistrationResult:
    enabled = session.run(
        "enable",
        [session.binary, "plugins", "enable", PLUGIN_ID],
    )
    verify = session.run("inventory", [session.binary, "plugins", "list"])
    if not enabled.ok:
        return session.result(False, "enable")
    record = _hermes_text_plugin_record(verify.stdout) if verify.ok else None
    proven = record is not None and _bool_field(record, "enabled") is not False
    return session.result(proven, None if proven else "inventory_unproven")


def _record_openclaw_gateway_state(
    session: _RegistrationSession,
) -> bool | None:
    live, probe = _openclaw_gateway_live(
        home_dir=session.home_dir,
        command_runner=session.command_runner,
    )
    state = "unknown" if live is None else "live" if live else "stopped"
    session.steps.append(
        {
            "name": "gateway_status",
            "gateway_state": state,
            **probe.to_dict(),
        }
    )
    return live


def _install_openclaw_plugin(
    session: _RegistrationSession,
    *,
    force_refresh: bool,
) -> str | None:
    existing = session.run(
        "inspect_existing",
        [session.binary, "plugins", "inspect", PLUGIN_ID, "--json"],
    )
    if not force_refresh and existing.ok:
        return None
    command = [session.binary, "plugins", "install", str(session.target)]
    if existing.ok:
        command.append("--force")
    installed = session.run("install", command, timeout=60)
    return None if installed.ok else "install"


def _verify_openclaw_runtime(session: _RegistrationSession) -> _RegistrationResult:
    verified = session.run(
        "runtime_inspect",
        [
            session.binary,
            "plugins",
            "inspect",
            PLUGIN_ID,
            "--runtime",
            "--json",
        ],
    )
    payload = _json_output(verified)
    record = _plugin_record(payload) or (payload if isinstance(payload, dict) else None)
    loaded = _bool_field(record, "loaded", "runtimeLoaded", "isLoaded") if verified.ok else None
    session.steps[-1]["loaded"] = loaded
    proven = verified.ok and isinstance(record, dict) and loaded is True
    return session.result(
        proven,
        None if proven else "runtime_inspect_unproven",
    )


def _register_openclaw(
    session: _RegistrationSession,
    force_refresh: bool,
) -> _RegistrationResult:
    live = _record_openclaw_gateway_state(session)
    if live is None:
        return session.result(False, "gateway_status_unproven")
    if live:
        return session.result(False, "host_restart_consent_required")
    if failed_step := _install_openclaw_plugin(
        session,
        force_refresh=force_refresh,
    ):
        return session.result(False, failed_step)

    enabled = session.run(
        "enable",
        [session.binary, "plugins", "enable", PLUGIN_ID],
    )
    if not enabled.ok:
        return session.result(False, "enable")
    access = session.run(
        "conversation_access",
        [
            session.binary,
            "config",
            "set",
            f"plugins.entries.{PLUGIN_ID}.hooks.allowConversationAccess",
            "true",
        ],
    )
    if not access.ok:
        return session.result(False, "conversation_access")
    return _verify_openclaw_runtime(session)


def _marketplace_state(session: _RegistrationSession) -> tuple[bool, bool]:
    inventory = session.run(
        "inventory_before",
        [session.binary, "plugin", "list", "--json"],
    )
    plugin_present = inventory.ok and _plugin_record(_json_output(inventory)) is not None
    marketplace = session.run(
        "marketplace_inventory",
        [session.binary, "plugin", "marketplace", "list", "--json"],
    )
    market_present = marketplace.ok and _marketplace_registered(_json_output(marketplace))
    return plugin_present, market_present


def _ensure_marketplace(
    session: _RegistrationSession,
    *,
    market_present: bool,
) -> str | None:
    if market_present:
        return None
    command = [
        session.binary,
        "plugin",
        "marketplace",
        "add",
        str(session.target),
    ]
    command.extend(["--json"] if session.host == "codex" else ["--scope", "user"])
    added = session.run("marketplace_add", command)
    return None if added.ok else "marketplace_add"


def _remove_plugin_for_refresh(
    session: _RegistrationSession,
    *,
    plugin_present: bool,
    force_refresh: bool,
) -> tuple[bool, str | None]:
    if not force_refresh or not plugin_present:
        return plugin_present, None
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    command = (
        [session.binary, "plugin", "remove", selector, "--json"]
        if session.host == "codex"
        else [
            session.binary,
            "plugin",
            "uninstall",
            selector,
            "--scope",
            "user",
        ]
    )
    removed = session.run("plugin_remove_for_refresh", command)
    return (False, None) if removed.ok else (True, "plugin_remove_for_refresh")


def _verify_plugin_inventory(session: _RegistrationSession) -> dict[str, Any] | None:
    verified = session.run(
        "inventory_after",
        [session.binary, "plugin", "list", "--json"],
    )
    return _plugin_record(_json_output(verified)) if verified.ok else None


def _register_codex(
    session: _RegistrationSession,
    *,
    plugin_present: bool,
) -> _RegistrationResult:
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    if not plugin_present:
        installed = session.run(
            "plugin_add",
            [session.binary, "plugin", "add", selector, "--json"],
            timeout=60,
        )
        if not installed.ok:
            return session.result(False, "plugin_add")
    record = _verify_plugin_inventory(session)
    proven = (
        record is not None
        and _bool_field(
            record,
            "enabled",
            "active",
            "isEnabled",
        )
        is True
    )
    return session.result(proven, None if proven else "inventory_after_unproven")


def _register_claude(
    session: _RegistrationSession,
    *,
    plugin_present: bool,
) -> _RegistrationResult:
    selector = f"{PLUGIN_ID}@{MARKETPLACE_ID}"
    if not plugin_present:
        installed = session.run(
            "plugin_install",
            [
                session.binary,
                "plugin",
                "install",
                selector,
                "--scope",
                "user",
            ],
            timeout=60,
        )
        if not installed.ok:
            return session.result(False, "plugin_install")
    enabled = session.run(
        "enable",
        [session.binary, "plugin", "enable", selector, "--scope", "user"],
    )
    if not enabled.ok:
        return session.result(False, "enable")
    record = _verify_plugin_inventory(session)
    proven = (
        record is not None
        and _bool_field(
            record,
            "enabled",
            "active",
            "isEnabled",
        )
        is not False
    )
    return session.result(proven, None if proven else "inventory_after_unproven")


def _register_marketplace_host(
    session: _RegistrationSession,
    force_refresh: bool,
) -> _RegistrationResult:
    plugin_present, market_present = _marketplace_state(session)
    if failed_step := _ensure_marketplace(
        session,
        market_present=market_present,
    ):
        return session.result(False, failed_step)
    plugin_present, failed_step = _remove_plugin_for_refresh(
        session,
        plugin_present=plugin_present,
        force_refresh=force_refresh,
    )
    if failed_step:
        return session.result(False, failed_step)
    register = _register_codex if session.host == "codex" else _register_claude
    return register(session, plugin_present=plugin_present)


_RegistrationHandler = Callable[[_RegistrationSession, bool], _RegistrationResult]
_REGISTRATION_HANDLERS: dict[str, _RegistrationHandler] = {
    "hermes": _register_hermes,
    "openclaw": _register_openclaw,
    "codex": _register_marketplace_host,
    "claude": _register_marketplace_host,
}


def native_registration_steps(
    host: str,
    target: Path,
    *,
    home_dir: str | Path | None,
    command_runner: CommandRunner | None,
    force_refresh: bool = False,
) -> tuple[list[dict[str, Any]], bool, str | None]:
    session = _RegistrationSession(
        host,
        target,
        home_dir=home_dir,
        command_runner=command_runner,
    )
    return _REGISTRATION_HANDLERS[host](session, force_refresh)


def native_command_plan(host: str, target: Path) -> list[dict[str, Any]]:
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
                "argv": [
                    binary,
                    "gateway",
                    "status",
                    "--deep",
                    "--require-rpc",
                    "--json",
                ],
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
                "argv": [
                    binary,
                    "plugins",
                    "inspect",
                    PLUGIN_ID,
                    "--runtime",
                    "--json",
                ],
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
