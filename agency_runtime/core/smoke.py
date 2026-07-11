"""Deterministic Agency Runtime smoke checks.

The smoke suite intentionally avoids network calls and live host mutation. It
verifies the local SQLite store, delegation eval contract, and generated host
plugin templates in a temporary HOME.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from agency_runtime.core.evals.delegation import run_delegation_eval
from agency_runtime.core.installer import HOSTS, detect_installed_agents, install_agent_adapter
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.store.sqlite import Store


class _FakeHookContext:
    def __init__(self) -> None:
        self.hooks: dict[str, Any] = {}

    def register_hook(self, name: str, fn: Any) -> None:
        self.hooks[name] = fn


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
    except Exception as exc:  # pragma: no cover - smoke boundary
        return {"name": name, "status": "fail", "error": f"{type(exc).__name__}: {exc}"}


def _prepare_fake_host_home(home: Path, host: str) -> None:
    if host == "hermes":
        (home / ".hermes" / "plugins").mkdir(parents=True, exist_ok=True)
    elif host == "openclaw":
        (home / ".openclaw").mkdir(parents=True, exist_ok=True)
    elif host == "codex":
        (home / ".codex").mkdir(parents=True, exist_ok=True)
    elif host == "claude":
        (home / ".claude").mkdir(parents=True, exist_ok=True)


def _smoke_openclaw_plugin(host: str, plugin_path: Path) -> dict[str, Any]:
    """Validate OpenClaw's native JS plugin package without importing it in Python."""
    manifest_path = plugin_path.parent / "openclaw.plugin.json"
    package_path = plugin_path.parent / "package.json"
    if not manifest_path.exists() or not package_path.exists():
        raise RuntimeError("missing OpenClaw plugin manifest or package.json")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package = json.loads(package_path.read_text(encoding="utf-8"))
    code = plugin_path.read_text(encoding="utf-8")
    if manifest.get("id") != "agency-preflight":
        raise RuntimeError("invalid OpenClaw plugin manifest id")
    if package.get("openclaw", {}).get("extensions") != ["./index.js"]:
        raise RuntimeError("invalid OpenClaw package extension entry")
    required_tokens = {
        "before_prompt_build",
        "before_agent_finalize",
        "agency_runtime.adapters.openclaw.node_bridge",
        "execFile",
    }
    missing_tokens = sorted(token for token in required_tokens if token not in code)
    if missing_tokens:
        raise RuntimeError(f"OpenClaw plugin missing tokens: {', '.join(missing_tokens)}")
    # The generated bridge intentionally embeds the interpreter that installed
    # Agency Runtime as its fallback. On a system Python installation that may
    # truthfully be /usr/bin/python3; AGENCY_RUNTIME_PYTHON remains the explicit
    # relocation override. Synchronous child execution is the unsafe contract.
    forbidden_tokens = {"spawnSync"}
    present_forbidden = sorted(token for token in forbidden_tokens if token in code)
    if present_forbidden:
        raise RuntimeError(f"OpenClaw plugin contains forbidden bridge tokens: {', '.join(present_forbidden)}")

    syntax_check = "skipped: node unavailable"
    node = shutil.which("node")
    if node:
        try:
            check = subprocess.run(
                [node, "--check", str(plugin_path)],
                text=True,
                capture_output=True,
                timeout=15,
            )
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


def _smoke_marketplace_bundle(host: str, plugin_path: Path) -> dict[str, Any]:
    """Validate native Codex/Claude plugin layout and executable MCP wiring."""
    manifest = json.loads(plugin_path.read_text(encoding="utf-8"))
    plugin_root = plugin_path.parents[1]
    hooks_path = plugin_root / "hooks" / "hooks.json"
    mcp_path = plugin_root / ".mcp.json"
    if manifest.get("name") != "agency-preflight":
        raise RuntimeError(f"invalid {host} plugin manifest name")
    if not hooks_path.exists() or not mcp_path.exists():
        raise RuntimeError(f"{host} bundle missing hooks or MCP config")
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
    if "UserPromptSubmit" not in hooks.get("hooks", {}):
        raise RuntimeError(f"{host} bundle missing UserPromptSubmit hook")
    server = mcp.get("mcpServers", {}).get("agency-runtime", {})
    if server.get("args") != ["-m", "agency_runtime.server.mcp", "--stdio"]:
        raise RuntimeError(f"{host} bundle has invalid Agency Runtime MCP command")
    command = Path(str(server.get("command") or ""))
    if not command.is_absolute():
        raise RuntimeError(f"{host} MCP command is not an absolute interpreter path")
    return {
        "host": host,
        "plugin_path": str(plugin_path),
        "format": f"{host}-plugin-bundle",
        "hooks": sorted(hooks["hooks"]),
        "mcp_server": "agency-runtime",
    }


def _smoke_generated_plugin(host: str, tmp_home: Path) -> dict[str, Any]:
    _prepare_fake_host_home(tmp_home, host)
    result = install_agent_adapter(host, home_dir=tmp_home)
    if not result.get("ok"):
        raise RuntimeError(str(result.get("error") or result))

    plugin_path = Path(str(result["plugin_path"]))
    if host == "openclaw":
        return _smoke_openclaw_plugin(host, plugin_path)

    if host in {"codex", "claude"}:
        return _smoke_marketplace_bundle(host, plugin_path)

    spec = importlib.util.spec_from_file_location(f"agency_runtime_smoke_{host}", plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import generated plugin: {plugin_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ctx = _FakeHookContext()
    module.register(ctx)
    required = {"pre_llm_call", "post_tool_call", "post_api_request", "transform_llm_output"}
    missing = sorted(required - set(ctx.hooks))
    if missing:
        raise RuntimeError(f"missing hooks: {', '.join(missing)}")
    ctx.hooks["post_api_request"](response={}, model="task-general", session_id=f"smoke-{host}")
    adapter = module._get_adapter()
    return {"host": host, "plugin_path": str(plugin_path), "adapter": adapter.__class__.__name__}


def run_smoke(*, all_hosts: bool = False) -> dict[str, Any]:
    """Run local deterministic smoke checks and return a JSON-safe report."""
    hosts = sorted(HOSTS) if all_hosts else detect_installed_agents()
    checks: list[dict[str, Any]] = []
    from agency_runtime.core.config import reset_config_cache

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_home = Path(tmpdir)
        smoke_db = tmp_home / "agency.db"
        smoke_config = tmp_home / "missing-agency.yaml"
        with _temporary_env(
            AGENCY_DB_PATH=str(smoke_db),
            AGENCY_CONFIG_PATH=str(smoke_config),
            HOME=str(tmp_home),
            USERPROFILE=str(tmp_home),
        ):
            # Config is process-global. Reset on both sides so a caller that
            # previously loaded its real profile cannot leak that Store path
            # into generated adapters, and the smoke profile cannot leak out.
            reset_config_cache()
            try:
                store = Store(smoke_db)
                checks.append(_check("sqlite_store", lambda: store.database_stats()))

                def _active_or_starter_roster() -> dict[str, Any]:
                    active_count = len(store.get_active_roster())
                    if active_count > 0:
                        return {"agent_count": active_count, "source": "active"}
                    return {"agent_count": len(STARTER_ROSTER), "source": "starter_roster"}

                checks.append(_check("routing_roster_available", _active_or_starter_roster))

                def _delegation_eval() -> dict[str, Any]:
                    report = run_delegation_eval()
                    if not report["passed"]:
                        raise RuntimeError(f"delegation eval failed: {report['failed_count']} failed")
                    return {"passed_count": report["passed_count"], "failed_count": report["failed_count"]}

                checks.append(_check("delegation_eval", _delegation_eval))

                if not hosts:
                    checks.append({"name": "host_plugins", "status": "skip", "detail": {"reason": "no installed hosts detected"}})
                else:
                    for host in hosts:
                        checks.append(_check(f"plugin_{host}", lambda host=host: _smoke_generated_plugin(host, tmp_home)))
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
