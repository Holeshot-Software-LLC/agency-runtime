"""Native host discovery and transactional installer contracts."""

from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core import installer_payloads, process_argv
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.installer import (
    INSTALL_MANIFEST,
    MAX_NATIVE_OUTPUT_CHARS,
    NativeCommandResult,
    _bundle_digest,
    _bundle_files,
    _command_environment,
    _effective_judge_budget_seconds,
    _managed_bundle_identity,
    _owned_process_kwargs,
    _plugin_record,
    _prepare_process_argv,
    _run_native,
    detect_installed_agents,
    inspect_host_installation,
    inspect_host_installations,
    install_agent_adapter,
    plan_agent_adapter,
    rollback_agent_adapter,
    toggle_agency,
)
from agency_runtime.core.installer_contracts import (
    ADAPTER_LAUNCHER_MANIFEST,
    OPENCLAW_REQUIRED_HOOKS,
    openclaw_version_supported,
)


@pytest.fixture(autouse=True)
def _no_live_dashboard_service(
    monkeypatch: pytest.MonkeyPatch,
    private_installer_launcher: tuple[Path, Path],
) -> tuple[Path, Path]:
    """Installer tests must never touch the developer's real user services."""

    import agency_runtime.core.dashboard_service as dashboard_service

    monkeypatch.setattr(
        dashboard_service,
        "plan_dashboard_service",
        lambda **_kwargs: {
            "ok": True,
            "exit_code": 0,
            "dry_run": True,
            "manager": "fake",
            "registration_path": "fake-dashboard-service",
        },
    )
    monkeypatch.setattr(
        dashboard_service,
        "install_dashboard_service",
        lambda **_kwargs: {
            "ok": True,
            "exit_code": 0,
            "changed": True,
            "status": "installed",
        },
    )
    return private_installer_launcher


def test_explicit_home_uses_openclaw_home_root_without_double_state_directory(
    tmp_path: Path,
) -> None:
    environment = _command_environment("openclaw", home_dir=tmp_path)

    assert environment["OPENCLAW_HOME"] == str(tmp_path.resolve())
    assert Path(environment["OPENCLAW_HOME"], ".openclaw") == tmp_path / ".openclaw"


def _resolver(*present: str):
    selected = set(present)
    return lambda name: str(Path("C:/fake") / f"{name}.exe") if name in selected else None


class FakeNativeRunner:
    def __init__(
        self,
        *,
        fail_token: str | None = None,
        gateway_live: bool = False,
        gateway_result: dict[str, Any] | None = None,
        runtime_payload: Any = None,
        openclaw_version: str = "OpenClaw 2026.7.1",
    ) -> None:
        self.commands: list[list[str]] = []
        self.fail_token = fail_token
        self.gateway_live = gateway_live
        self.gateway_result = gateway_result
        self.runtime_payload = runtime_payload
        self.openclaw_version = openclaw_version
        self.installed: set[str] = set()
        self.openclaw_disabled: set[str] = set()
        self.marketplaces: set[str] = set()
        self.openclaw_agents: dict[str, Any] = {}
        self.openclaw_channels: dict[str, Any] = {}

    def _gateway_or_marketplace_result(self, joined: str) -> dict[str, Any] | None:
        if "gateway status" in joined:
            if self.gateway_result is not None:
                return dict(self.gateway_result)
            return {
                "returncode": 0,
                "stdout": json.dumps({"running": self.gateway_live}),
            }
        if "marketplace list" in joined:
            return {
                "returncode": 0,
                "stdout": json.dumps([{"name": name} for name in sorted(self.marketplaces)]),
            }
        if "marketplace add" in joined:
            self.marketplaces.add("agency-runtime")
            return {"returncode": 0, "stdout": "{}"}
        return None

    def _plugin_result(self, command: list[str], joined: str) -> dict[str, Any] | None:
        if "plugin add" in joined or "plugin install" in joined:
            self.installed.add("agency-preflight")
            return {"returncode": 0, "stdout": "{}"}
        if "plugin enable" in joined:
            self.installed.add("agency-preflight")
            return {"returncode": 0, "stdout": "enabled"}
        if "plugin disable" in joined or "plugin remove" in joined:
            self.installed.discard("agency-preflight")
            return {"returncode": 0, "stdout": "disabled"}
        if "plugin list" in joined:
            identity_key = "pluginId" if command[0] == "codex" else "name"
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [{identity_key: name, "enabled": True} for name in sorted(self.installed)]
                ),
            }
        return None

    def _plugins_result(self, command: list[str], joined: str) -> dict[str, Any] | None:
        if "plugins inspect agency-preflight --runtime" in joined:
            payload = self.runtime_payload
            if payload is None:
                payload = {
                    "id": "agency-preflight",
                    "enabled": True,
                    "loaded": True,
                    "hooks": sorted(OPENCLAW_REQUIRED_HOOKS),
                }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
            }
        if "plugins inspect agency-preflight" in joined:
            found = "agency-preflight" in self.installed
            return {
                "returncode": 0 if found else 1,
                "stdout": (
                    json.dumps(
                        {
                            "id": "agency-preflight",
                            "enabled": "agency-preflight" not in self.openclaw_disabled,
                        }
                    )
                    if found
                    else ""
                ),
            }
        if "plugins install" in joined:
            self.installed.add("agency-preflight")
            self.openclaw_disabled.discard("agency-preflight")
            return {"returncode": 0, "stdout": "installed"}
        if "plugins enable" in joined:
            self.installed.add("agency-preflight")
            self.openclaw_disabled.discard("agency-preflight")
            return {"returncode": 0, "stdout": "enabled"}
        if "plugins disable" in joined:
            if command[0] == "openclaw":
                self.openclaw_disabled.add("agency-preflight")
            else:
                self.installed.discard("agency-preflight")
            return {"returncode": 0, "stdout": "disabled"}
        if "plugins list" in joined:
            if command[0] == "openclaw":
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "plugins": [
                                {
                                    "id": name,
                                    "enabled": name not in self.openclaw_disabled,
                                }
                                for name in sorted(self.installed)
                            ]
                        }
                    ),
                }
            text = "\n".join(f"{name} enabled" for name in sorted(self.installed))
            return {"returncode": 0, "stdout": text}
        if "config set" in joined:
            return {"returncode": 0, "stdout": "updated"}
        return None

    def _openclaw_config_result(self, command: list[str]) -> dict[str, Any] | None:
        if command[:4] == ["openclaw", "config", "get", "agents.defaults"]:
            return {"returncode": 0, "stdout": json.dumps(self.openclaw_agents)}
        if command[:4] == ["openclaw", "config", "get", "channels"]:
            return {"returncode": 0, "stdout": json.dumps(self.openclaw_channels)}
        if command[:4] == [
            "openclaw",
            "config",
            "set",
            "agents.defaults.blockStreamingDefault",
        ]:
            self.openclaw_agents["blockStreamingDefault"] = json.loads(command[4])
            return {"returncode": 0, "stdout": "updated"}
        return None

    def __call__(self, command: list[str], **_kwargs: Any) -> dict[str, Any]:
        self.commands.append(command)
        joined = " ".join(command)
        if self.fail_token and self.fail_token in joined:
            return {"returncode": 9, "stderr": f"forced failure: {self.fail_token}"}
        if command == ["openclaw", "--version"]:
            return {"returncode": 0, "stdout": self.openclaw_version}
        result = self._openclaw_config_result(command)
        if result is not None:
            return result
        result = self._gateway_or_marketplace_result(joined)
        if result is not None:
            return result
        result = self._plugin_result(command, joined)
        if result is not None:
            return result
        result = self._plugins_result(command, joined)
        if result is not None:
            return result
        return {"returncode": 0, "stdout": "{}"}


def test_detection_separates_bare_stale_root_from_current_native_state(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex").mkdir()

    assert "codex" not in detect_installed_agents(home_dir=tmp_path, binary_resolver=_resolver())
    codex = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver(),
        )
    }["codex"]
    assert codex["native_root_exists"] is True
    assert codex["stale_config"] is True
    assert codex["discovered"] is False

    (tmp_path / ".codex" / "config.toml").write_text("", encoding="utf-8")
    assert "codex" in detect_installed_agents(home_dir=tmp_path, binary_resolver=_resolver())


def test_codex_current_plugin_id_inventory_shape_is_recognized() -> None:
    record = _plugin_record({"plugins": [{"pluginId": "agency-preflight", "enabled": True}]})

    assert record == {"pluginId": "agency-preflight", "enabled": True}


def test_executable_discovery_is_independent_from_config_state(tmp_path: Path) -> None:
    records = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver("claude"),
        )
    }
    assert records["claude"]["executable_discovered"] is True
    assert records["claude"]["native_root_exists"] is False
    assert records["claude"]["discovered"] is True
    assert records["claude"]["stale_config"] is False


def test_native_windows_hermes_payload_is_current_install_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "AppData" / "Local" / "hermes").mkdir(parents=True)

    assert "hermes" in detect_installed_agents(home_dir=tmp_path, binary_resolver=_resolver())
    hermes = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver(),
        )
    }["hermes"]
    assert hermes["current_native_root"] is True
    assert hermes["native_root_exists"] is False
    assert any(
        "AppData" in evidence and "Local" in evidence and evidence.endswith("hermes")
        for evidence in hermes["evidence"]
    )


def test_windows_command_shims_preserve_metacharacter_arguments_without_cmd_interpolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shim_dir = tmp_path / "host & tools ^ 100%"
    shim_dir.mkdir()
    cmd_shim = shim_dir / "codex.cmd"
    ps1_shim = shim_dir / "codex.ps1"
    cmd_shim.write_text("@echo off\n", encoding="utf-8")
    ps1_shim.write_text("# safe companion\n", encoding="utf-8")
    special_path = str(tmp_path / "bundle & cache | stage ^ 50% <input>")
    powershell = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

    def resolver(_name):
        return str(cmd_shim)

    monkeypatch.setattr(
        process_argv,
        "resolve_executable_path",
        lambda _name, *, platform_name=None, **_kwargs: (
            str(cmd_shim) if platform_name == "nt" else "/usr/local/bin/codex"
        ),
    )

    windows = _prepare_process_argv(
        ["codex", "plugin", "marketplace", "add", special_path],
        platform_name="nt",
        resolver=resolver,
        system_resolver=lambda _name: powershell,
    )
    linux = _prepare_process_argv(
        ["codex", "plugin", "list", "--json"],
        platform_name="posix",
        resolver=lambda _name: "/usr/local/bin/codex",
    )

    assert windows[:7] == [
        powershell,
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
    ]
    assert windows[7] == str(ps1_shim)
    assert windows[8:] == ["plugin", "marketplace", "add", special_path]
    assert all("cmd.exe" not in item.casefold() for item in windows)
    assert linux == ["/usr/local/bin/codex", "plugin", "list", "--json"]


def test_windows_command_shim_without_safe_companion_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cmd_shim = tmp_path / "host.cmd"
    cmd_shim.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(
        process_argv,
        "resolve_executable_path",
        lambda *_args, **_kwargs: str(cmd_shim),
    )

    with pytest.raises(OSError, match=r"refusing unsafe cmd\.exe shim"):
        _prepare_process_argv(
            ["host", "plugin", "list"],
            platform_name="nt",
            resolver=lambda _name: str(cmd_shim),
        )


@pytest.mark.parametrize(
    ("command", "script_parts"),
    [
        ("codex", ("@openai", "codex", "bin", "codex.js")),
        ("claude", ("@anthropic-ai", "claude-code", "cli.js")),
    ],
)
def test_windows_npm_cli_uses_allowlisted_node_entry_instead_of_powershell_stdin(
    command: str,
    script_parts: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shim = tmp_path / f"{command}.cmd"
    shim.write_text("@echo off\n", encoding="utf-8")
    shim.with_suffix(".ps1").write_text("throw 'must not run'\n", encoding="utf-8")
    node = tmp_path / "node.exe"
    node.write_bytes(b"fake")
    script = tmp_path / "node_modules"
    for part in script_parts:
        script /= part
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text("// fake\n", encoding="utf-8")
    monkeypatch.setattr(
        process_argv,
        "resolve_executable_path",
        lambda *_args, **_kwargs: str(shim),
    )

    prepared = _prepare_process_argv(
        [command, "exec", "-"],
        platform_name="nt",
        resolver=lambda _name: str(shim),
    )

    assert prepared == [str(node), str(script), "exec", "-"]


def test_native_process_group_flags_cover_windows_and_posix() -> None:
    windows = _owned_process_kwargs(platform_name="nt")
    posix = _owned_process_kwargs(platform_name="posix")

    assert windows["creationflags"] & getattr(
        subprocess,
        "CREATE_NEW_PROCESS_GROUP",
        0x00000200,
    )
    assert posix == {"start_new_session": True}


def test_native_timeout_terminates_descendant_process_tree(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _no_live_dashboard_service: tuple[Path, Path],
) -> None:
    marker = tmp_path / "orphan-child-ran.txt"
    monkeypatch.setenv("AGENCY_INSTALLER_TREE_MARKER", str(marker))
    child_code = (
        "import os, time; from pathlib import Path; time.sleep(1.0); "
        "Path(os.environ['AGENCY_INSTALLER_TREE_MARKER']).write_text('orphan', encoding='utf-8')"
    )
    parent_code = (
        "import subprocess, sys, time; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}]); "
        "time.sleep(5)"
    )

    result = _run_native(
        [str(_no_live_dashboard_service[0]), "-c", parent_code],
        host="codex",
        home_dir=tmp_path,
        timeout=0.2,
    )

    assert result.returncode == 124
    assert "terminated the owned process tree" in result.stderr
    time.sleep(1.2)
    assert not marker.exists()


def test_native_command_output_is_bounded_and_truncation_fails_closed(
    _no_live_dashboard_service: tuple[Path, Path],
) -> None:
    result = _run_native(
        [
            str(_no_live_dashboard_service[0]),
            "-c",
            f"import sys;sys.stdout.write('x'*{MAX_NATIVE_OUTPUT_CHARS * 4})",
        ],
        host="codex",
        timeout=30,
    )

    assert result.returncode == 0
    assert result.ok is False
    assert result.stdout_truncated is True
    assert len(result.stdout) == MAX_NATIVE_OUTPUT_CHARS
    assert "capture limit" in result.stderr
    assert result.to_dict()["stdout_truncated"] is True


def test_generated_hook_timeouts_exceed_the_configured_sequential_judge_budget() -> None:
    cfg = AgencyConfig(
        judge=JudgeConfig(
            model="legacy-model",
            base_url="http://legacy.invalid",
            timeout=17,
        ),
        ollama=OllamaConfig(enabled=True, model="fallback-model"),
        providers=(
            ProviderEntry(model="primary", base_url="http://primary.invalid", timeout=7),
            ProviderEntry(model="secondary", base_url="http://secondary.invalid", timeout=11),
            ProviderEntry(
                name="codex-cli",
                type="cli",
                transport="codex",
                timeout=13,
            ),
        ),
    )
    judge_budget = _effective_judge_budget_seconds(cfg)
    assert judge_budget >= 65

    codex_files, _ = _bundle_files("codex", cfg)
    codex_hooks = json.loads(codex_files["plugins/agency-preflight/hooks/hooks.json"])
    codex_handler = codex_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    hook_timeout = codex_handler["timeout"]
    assert codex_handler["async"] is False
    assert "timeoutSec" not in codex_handler
    assert hook_timeout > judge_budget
    assert {
        "SessionStart",
        "UserPromptSubmit",
        "PostToolUse",
        "SubagentStart",
        "SubagentStop",
        "PostCompact",
        "Stop",
    }.issubset(codex_hooks["hooks"])

    claude_files, _ = _bundle_files("claude", cfg)
    claude_hooks = json.loads(claude_files["plugins/agency-preflight/hooks/hooks.json"])
    assert claude_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"] == hook_timeout
    assert {
        "SessionStart",
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "SubagentStart",
        "SubagentStop",
        "PostCompact",
        "Stop",
        "SessionEnd",
    }.issubset(claude_hooks["hooks"])
    assert claude_hooks["hooks"]["PreToolUse"][0]["matcher"] == "Agent"

    openclaw_files, _ = _bundle_files("openclaw", cfg)
    bridge = openclaw_files["index.js"]
    assert f"function invokeAgency(payload, processTimeoutMs = {hook_timeout * 1000})" in bridge
    assert f"timeoutMs: {(hook_timeout + 2) * 1000}" in bridge
    assert f"timeoutMs: {(hook_timeout + 2) * 1000}" in bridge


def test_codex_windows_hook_command_is_inert_powershell_argv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        installer_payloads.sys,
        "executable",
        r"C:\Program Files\O'Brien & Sons\python.exe",
    )
    monkeypatch.setattr(
        installer_payloads,
        "launcher_artifact_paths",
        lambda: (
            process_argv.absolute_executable_path(installer_payloads.sys.executable),
            installer_payloads.agency_bootstrap_path(),
        ),
    )

    _posix, windows = installer_payloads.python_commands(
        "agency_runtime.cli",
        "hook",
        "codex; Write-Output injected",
        "$HOME",
        "O'Brien",
    )

    bootstrap = installer_payloads.agency_bootstrap_path().replace("'", "''")
    assert windows == (
        "& 'C:\\Program Files\\O''Brien & Sons\\python.exe' '-I' "
        f"'{bootstrap}' 'agency_runtime.cli' 'hook' 'codex; Write-Output injected' "
        "'$HOME' 'O''Brien'"
    )


def test_generated_hook_timeout_is_capped_below_host_maximum() -> None:
    cfg = AgencyConfig(
        judge=JudgeConfig(timeout=600),
        providers=tuple(
            ProviderEntry(
                name=f"provider-{index}",
                model="model",
                base_url="https://provider.invalid/v1",
                timeout=600,
            )
            for index in range(20)
        ),
    )

    codex_files, _ = _bundle_files("codex", cfg)
    codex_hooks = json.loads(codex_files["plugins/agency-preflight/hooks/hooks.json"])
    handler = codex_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    timeout = handler["timeout"]
    openclaw_files, _ = _bundle_files("openclaw", cfg)

    assert timeout == 595
    assert "timeoutSec" not in handler
    assert "timeoutMs: 597000" in openclaw_files["index.js"]


def test_codex_bundle_uses_a_deterministic_content_cachebuster() -> None:
    first, _ = _bundle_files("codex", AgencyConfig())
    second, _ = _bundle_files("codex", AgencyConfig())
    slower, _ = _bundle_files(
        "codex",
        AgencyConfig(judge=JudgeConfig(timeout=31)),
    )

    manifest_path = "plugins/agency-preflight/.codex-plugin/plugin.json"
    first_version = json.loads(first[manifest_path])["version"]
    second_version = json.loads(second[manifest_path])["version"]
    slower_version = json.loads(slower[manifest_path])["version"]

    assert first_version == second_version
    assert first_version.startswith("0.1.0+codex.")
    assert len(first_version.rsplit(".", 1)[-1]) == 12
    assert slower_version != first_version


def test_host_bundles_embed_one_absolute_config_identity_with_spaces(tmp_path: Path) -> None:
    config_path = tmp_path / "operator config" / "agency runtime.yaml"
    config_path.parent.mkdir()
    config_path.write_text("{}\n", encoding="utf-8")
    cfg = AgencyConfig(config_path=str(config_path))

    codex_files, _ = _bundle_files("codex", cfg)
    codex_hooks = json.loads(codex_files["plugins/agency-preflight/hooks/hooks.json"])
    codex_handler = codex_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert shlex.split(codex_handler["command"])[-2:] == ["--config", str(config_path)]
    assert codex_handler["commandWindows"].endswith(f" '--config' '{config_path}'")
    codex_mcp = json.loads(codex_files["plugins/agency-preflight/.mcp.json"])
    assert codex_mcp["mcpServers"]["agency-runtime"]["args"][-2:] == [
        "--config",
        str(config_path),
    ]

    claude_files, _ = _bundle_files("claude", cfg)
    claude_hooks = json.loads(claude_files["plugins/agency-preflight/hooks/hooks.json"])
    claude_handler = claude_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert claude_handler["args"][-2:] == ["--config", str(config_path)]
    claude_mcp = json.loads(claude_files["plugins/agency-preflight/.mcp.json"])
    assert claude_mcp["mcpServers"]["agency-runtime"]["args"][-2:] == [
        "--config",
        str(config_path),
    ]

    hermes_files, _ = _bundle_files("hermes", cfg)
    assert f"_CONFIG_PATH = {str(config_path)!r}" in hermes_files["__init__.py"]

    openclaw_files, _ = _bundle_files("openclaw", cfg)
    expected_openclaw_args = (
        '"agency_runtime.adapters.openclaw.node_bridge", '
        f'"--config", {json.dumps(str(config_path))}]'
    )
    assert expected_openclaw_args in openclaw_files["index.js"]


@pytest.mark.parametrize("host", ["codex", "claude", "hermes", "openclaw"])
def test_host_bundle_fingerprint_includes_config_identity(host: str, tmp_path: Path) -> None:
    first_path = tmp_path / "first config" / "agency.yaml"
    second_path = tmp_path / "second config" / "agency.yaml"
    first_path.parent.mkdir()
    second_path.parent.mkdir()
    first_path.write_text("{}\n", encoding="utf-8")
    second_path.write_text("{}\n", encoding="utf-8")

    first, _ = _bundle_files(host, AgencyConfig(config_path=str(first_path)))
    repeated, _ = _bundle_files(host, AgencyConfig(config_path=str(first_path)))
    second, _ = _bundle_files(host, AgencyConfig(config_path=str(second_path)))

    assert _bundle_digest(first) == _bundle_digest(repeated)
    assert _bundle_digest(first) != _bundle_digest(second)


def test_programmatic_config_without_identity_omits_host_config_argument() -> None:
    codex_files, _ = _bundle_files("codex", AgencyConfig())
    codex_hooks = json.loads(codex_files["plugins/agency-preflight/hooks/hooks.json"])
    codex_handler = codex_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    codex_mcp = json.loads(codex_files["plugins/agency-preflight/.mcp.json"])
    assert "--config" not in shlex.split(codex_handler["command"])
    assert "--config" not in codex_mcp["mcpServers"]["agency-runtime"]["args"]

    claude_files, _ = _bundle_files("claude", AgencyConfig())
    claude_hooks = json.loads(claude_files["plugins/agency-preflight/hooks/hooks.json"])
    claude_handler = claude_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    claude_mcp = json.loads(claude_files["plugins/agency-preflight/.mcp.json"])
    assert "--config" not in claude_handler["args"]
    assert "--config" not in claude_mcp["mcpServers"]["agency-runtime"]["args"]

    hermes_files, _ = _bundle_files("hermes", AgencyConfig())
    assert "_CONFIG_PATH = ''" in hermes_files["__init__.py"]

    openclaw_files, _ = _bundle_files("openclaw", AgencyConfig())
    module_args = next(
        line for line in openclaw_files["index.js"].splitlines() if "const MODULE_ARGS" in line
    )
    assert "--config" not in module_args


def test_unchanged_codex_reinstall_is_idempotent(tmp_path: Path) -> None:
    runner = FakeNativeRunner()
    first = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )
    command_count = len(runner.commands)
    first_manifest = json.loads(Path(first["target"], INSTALL_MANIFEST).read_text(encoding="utf-8"))

    second = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )
    second_commands = [" ".join(command) for command in runner.commands[command_count:]]
    second_manifest = json.loads(
        Path(second["target"], INSTALL_MANIFEST).read_text(encoding="utf-8")
    )

    assert second["ok"] is True
    assert second["filesystem"]["unchanged"] is True
    assert second["backup_path"] is None
    assert second["restart_required"] is False
    assert first_manifest["install_id"] == second_manifest["install_id"]
    assert not any("plugin remove" in command for command in second_commands)
    assert not any("plugin add" in command for command in second_commands)


def test_adapter_manifest_binds_launcher_artifacts_and_inspection_rejects_drift(
    tmp_path: Path,
    _no_live_dashboard_service: tuple[Path, Path],
) -> None:
    runner = FakeNativeRunner()
    common = {
        "home_dir": tmp_path,
        "binary_resolver": _resolver("codex"),
        "command_runner": runner,
    }
    installed = install_agent_adapter("codex", **common)
    manifest = json.loads(Path(installed["target"], INSTALL_MANIFEST).read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 2
    assert len(manifest["launcher_artifacts"]) == 2
    assert ADAPTER_LAUNCHER_MANIFEST in manifest["owned_files"]
    assert inspect_host_installation("codex", **common)["launcher_artifacts_current"] is True

    bootstrap = _no_live_dashboard_service[1]
    original = bootstrap.read_bytes()
    try:
        bootstrap.write_text("# changed after registration\n", encoding="utf-8")
        drifted = inspect_host_installation("codex", **common)
    finally:
        bootstrap.write_bytes(original)

    assert drifted["launcher_artifacts_current"] is False
    assert drifted["maturity"] == "launcher-artifact-drift"
    assert drifted["canary"] is None
    assert drifted["canary_attestation_status"] == "stale"
    assert "launcher_artifacts" in drifted["canary_stale_reasons"]


def test_changed_codex_bundle_forces_native_cache_refresh(tmp_path: Path) -> None:
    runner = FakeNativeRunner()
    first = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )
    Path(first["target"], "unexpected.js").write_text(
        "throw new Error('must not load');\n",
        encoding="utf-8",
    )
    command_count = len(runner.commands)

    second = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )
    commands = [" ".join(command) for command in runner.commands[command_count:]]

    assert second["ok"] is True
    assert second["filesystem"]["unchanged"] is False
    assert Path(second["backup_path"], "unexpected.js").is_file()
    assert not Path(second["target"], "unexpected.js").exists()
    assert any("plugin remove" in command for command in commands)
    assert any("plugin add" in command for command in commands)


def test_dry_run_is_a_write_free_complete_plan(tmp_path: Path) -> None:
    plan = plan_agent_adapter("codex", home_dir=tmp_path, binary_resolver=_resolver("codex"))

    assert plan["ok"] is True
    assert plan["dry_run"] is True
    assert plan["commands_will_run"] is True
    assert ".agents/plugins/marketplace.json" in plan["filesystem"]["owned_files"]
    assert not (tmp_path / ".agency-runtime").exists()


def test_openclaw_dry_run_reports_exact_argv_and_gateway_gate_without_writes(
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(gateway_live=False)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))

    plan = plan_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert plan["ok"] is True
    assert plan["gateway_safety_gate"]["state"] == "stopped"
    assert plan["gateway_safety_gate"]["safe_to_mutate"] is True
    planned = plan["native_command_plan"]
    assert planned[0]["argv"] == [
        "openclaw",
        "gateway",
        "status",
        "--deep",
        "--require-rpc",
        "--json",
    ]
    assert any(step["argv"][-1:] == ["--force"] for step in planned)
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*")) == before


def test_custom_hermes_home_controls_plugin_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom_home = tmp_path / "custom-hermes"
    monkeypatch.setenv("HERMES_HOME", str(custom_home))

    plan = plan_agent_adapter("hermes", binary_resolver=_resolver())

    assert Path(plan["native_root"]) == custom_home.resolve()
    assert (
        Path(plan["plugin_path"]).parent == (custom_home / "plugins" / "agency-preflight").resolve()
    )


@pytest.mark.parametrize(
    ("inventory", "expected_enabled"),
    [
        ("unrelated-plugin enabled\nagency-preflight disabled\n", False),
        ("unrelated-plugin disabled\nagency-preflight enabled\n", True),
        ("unrelated-plugin enabled\nagency-preflight\n", None),
    ],
)
def test_hermes_enabled_state_comes_only_from_agency_preflight_row(
    inventory: str,
    expected_enabled: bool | None,
    tmp_path: Path,
) -> None:
    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if command == ["hermes", "--version"]:
            return {"returncode": 0, "stdout": "hermes 1.0.0"}
        assert command == ["hermes", "plugins", "list"]
        return {"returncode": 0, "stdout": inventory}

    record = inspect_host_installation(
        "hermes",
        home_dir=tmp_path,
        binary_resolver=_resolver("hermes"),
        command_runner=runner,
    )

    assert record["registered"] is True
    assert record["enabled"] is expected_enabled


def test_codex_inventory_surfaces_manual_hook_trust_boundary(tmp_path: Path) -> None:
    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if command == ["codex", "--version"]:
            return {"returncode": 0, "stdout": "codex-cli 0.144.1"}
        if command == ["codex", "plugin", "list", "--json"]:
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [{"pluginId": "agency-preflight@agency-runtime", "enabled": True}]
                ),
            }
        assert command == ["codex", "plugin", "marketplace", "list", "--json"]
        return {"returncode": 0, "stdout": json.dumps([{"name": "agency-runtime"}])}

    record = inspect_host_installation(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    assert record["registered"] is True
    assert record["enabled"] is True
    assert record["hook_trust_status"] == "unverified"
    assert "`/hooks`" in record["hook_trust_action"]


def test_filtered_host_inspection_validates_names_and_preserves_canonical_order(
    tmp_path: Path,
) -> None:
    records = inspect_host_installations(
        home_dir=tmp_path,
        binary_resolver=_resolver(),
        hosts=("claude", "hermes"),
    )
    assert [record["host"] for record in records] == ["hermes", "claude"]

    with pytest.raises(ValueError, match="Unknown host"):
        inspect_host_installations(home_dir=tmp_path, hosts=("missing",))


def test_bulk_host_inspection_fans_out_and_preserves_canonical_order(
    tmp_path: Path,
) -> None:
    version_barrier = threading.Barrier(4)
    version_hosts: set[str] = set()
    lock = threading.Lock()

    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if command[1:] == ["--version"]:
            with lock:
                version_hosts.add(command[0])
            version_barrier.wait(timeout=5)
            return {"returncode": 0, "stdout": f"{command[0]} 1.0.0"}
        return {"returncode": 0, "stdout": json.dumps({"plugins": []})}

    records = inspect_host_installations(
        home_dir=tmp_path,
        binary_resolver=_resolver("claude", "codex", "openclaw", "hermes"),
        command_runner=runner,
        hosts=("claude", "codex", "openclaw", "hermes"),
    )

    assert [record["host"] for record in records] == [
        "hermes",
        "openclaw",
        "codex",
        "claude",
    ]
    assert version_hosts == {"hermes", "openclaw", "codex", "claude"}


def test_bulk_host_inspection_preserves_native_probe_deadlines() -> None:
    deadlines: dict[tuple[str, ...], float] = {}
    lock = threading.Lock()

    def runner(command: list[str], **kwargs: Any) -> dict[str, Any]:
        with lock:
            deadlines[tuple(command)] = kwargs["timeout"]
        if command[1:] == ["--version"]:
            return {"returncode": 0, "stdout": f"{command[0]} 1.0.0"}
        if "marketplace" in command:
            return {"returncode": 0, "stdout": "[]"}
        if "inspect" in command:
            payload = {"id": "agency-preflight", "loaded": True}
            return {"returncode": 0, "stdout": json.dumps(payload)}
        payload = {"plugins": [{"id": "agency-preflight", "enabled": True}]}
        return {"returncode": 0, "stdout": json.dumps(payload)}

    records = inspect_host_installations(
        home_dir=Path("__agency_missing_profile_for_deadline_test__"),
        binary_resolver=_resolver("codex", "openclaw"),
        command_runner=runner,
        probe_runtime=True,
        hosts=("codex", "openclaw"),
    )

    assert [record["host"] for record in records] == ["openclaw", "codex"]
    assert deadlines[("openclaw", "--version")] == 8
    assert deadlines[("openclaw", "plugins", "list", "--json")] == 12
    assert (
        deadlines[
            (
                "openclaw",
                "plugins",
                "inspect",
                "agency-preflight",
                "--runtime",
                "--json",
            )
        ]
        == 20
    )
    assert deadlines[("codex", "--version")] == 8
    assert deadlines[("codex", "plugin", "list", "--json")] == 12
    assert deadlines[("codex", "plugin", "marketplace", "list", "--json")] == 12


@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (RuntimeError("inventory exploded"), "RuntimeError: inventory exploded"),
        (
            TimeoutError("inventory deadline elapsed"),
            "TimeoutError: inventory deadline elapsed",
        ),
    ],
)
def test_bulk_host_inspection_isolates_native_runner_failures(
    failure: Exception,
    expected_code: str,
    tmp_path: Path,
) -> None:
    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if command == ["hermes", "plugins", "list"]:
            raise failure
        if command[1:] == ["--version"]:
            return {"returncode": 0, "stdout": f"{command[0]} 1.0.0"}
        return {"returncode": 0, "stdout": json.dumps({"plugins": []})}

    records = inspect_host_installations(
        home_dir=tmp_path,
        binary_resolver=_resolver("codex", "hermes"),
        command_runner=runner,
        hosts=("codex", "hermes"),
    )

    assert [record["host"] for record in records] == ["hermes", "codex"]
    hermes, codex = records
    assert hermes["registered"] is None
    assert hermes["inventory_error"] == expected_code
    assert "native-inventory:error" in hermes["evidence"]
    assert codex["inventory_error"] is None
    assert codex["registered"] is False


def test_bulk_host_inspection_isolates_filesystem_probe_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.installer as installer

    real_host_root = installer._host_root

    def host_root(host: str, **kwargs: Any) -> Path:
        if host == "hermes":
            raise OSError("hermes root unavailable")
        return real_host_root(host, **kwargs)

    monkeypatch.setattr(installer, "_host_root", host_root)

    records = installer.inspect_host_installations(
        home_dir=tmp_path,
        binary_resolver=_resolver(),
        hosts=("codex", "hermes"),
    )

    assert [record["host"] for record in records] == ["hermes", "codex"]
    hermes, codex = records
    assert hermes["inventory_error"] == "OSError: hermes root unavailable"
    assert hermes["evidence"] == ["inspection:error:OSError"]
    assert codex["inventory_error"] is None
    assert codex["maturity"] == "absent"


def test_managed_bundle_identity_rejects_oversized_manifest(tmp_path: Path) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    (target / INSTALL_MANIFEST).write_bytes(b"{" + b" " * (64 * 1024))

    assert _managed_bundle_identity(target, "codex") == (None, None, None)


def test_managed_bundle_identity_reads_a_valid_bounded_bundle(tmp_path: Path) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    files = {"nested/payload.js": "export default true;\n"}
    (target / "nested").mkdir()
    (target / "nested" / "payload.js").write_text(
        files["nested/payload.js"],
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": "agency-preflight",
        "plugin_version": "0.1.0",
        "install_id": "valid-bounded-read",
        "owned_files": list(files),
    }
    (target / INSTALL_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    assert _managed_bundle_identity(target, "codex") == (
        "0.1.0",
        "valid-bounded-read",
        _bundle_digest(files),
    )


@pytest.mark.parametrize(
    "owned_files",
    [[], ["../outside.js"], ["C:/outside.js"], ["payload.js", "payload.js"], [{}]],
)
def test_managed_bundle_identity_rejects_malformed_owned_files(
    owned_files: list[Any],
    tmp_path: Path,
) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    manifest = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": "agency-preflight",
        "plugin_version": "0.1.0",
        "install_id": "malformed-owned-files",
        "owned_files": owned_files,
    }
    (target / INSTALL_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    assert _managed_bundle_identity(target, "codex") == (None, None, None)


def test_managed_bundle_identity_rejects_oversized_owned_file(tmp_path: Path) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    (target / "payload.bin").write_bytes(b"x" * (8 * 1024 * 1024 + 1))
    manifest = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": "agency-preflight",
        "plugin_version": "0.1.0",
        "install_id": "bounded-read-test",
        "owned_files": ["payload.bin"],
    }
    (target / INSTALL_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    assert _managed_bundle_identity(target, "codex") == (None, None, None)


def test_managed_bundle_identity_rejects_linked_owned_file(tmp_path: Path) -> None:
    target = tmp_path / "plugin"
    target.mkdir()
    outside = tmp_path / "outside.js"
    outside.write_text("export default 'outside';\n", encoding="utf-8")
    try:
        (target / "payload.js").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable on this host: {exc}")
    manifest = {
        "owner": "agency-runtime",
        "host": "codex",
        "plugin_id": "agency-preflight",
        "plugin_version": "0.1.0",
        "install_id": "link-test",
        "owned_files": ["payload.js"],
    }
    (target / INSTALL_MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    assert _managed_bundle_identity(target, "codex") == (None, None, None)


def test_explicit_home_suppresses_real_host_commands_without_injected_runner(
    tmp_path: Path,
) -> None:
    result = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
    )

    assert result["ok"] is True
    assert result["status"] == "staged_test_boundary"
    assert result["registered"] is False
    assert result["maturity"] == "staged-not-registered"
    assert Path(result["target"], INSTALL_MANIFEST).exists()


@pytest.mark.parametrize("host", ["codex", "claude", "hermes", "openclaw"])
def test_native_installers_register_and_enable_with_host_lifecycle(
    host: str, tmp_path: Path
) -> None:
    runner = FakeNativeRunner()
    result = install_agent_adapter(
        host,
        home_dir=tmp_path,
        binary_resolver=_resolver(host),
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["registered"] is True
    assert result["enabled"] is True
    assert result["native_steps"]
    commands = [" ".join(command) for command in runner.commands]
    if host in {"codex", "claude"}:
        assert any("plugin marketplace add" in command for command in commands)
    if host == "codex":
        assert result["hook_trust_status"] == "unverified"
        assert "`/hooks`" in result["hook_trust_action"]
    if host == "openclaw":
        assert any("plugins install" in command for command in commands)
        assert any(
            "plugins inspect agency-preflight --runtime --json" in command for command in commands
        )
    if host == "hermes":
        assert (
            Path(result["plugin_path"]).parent
            == tmp_path / ".hermes" / "plugins" / "agency-preflight"
        )


def test_native_failure_returns_partial_nonzero_evidence(tmp_path: Path) -> None:
    runner = FakeNativeRunner(fail_token="plugin add")
    result = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["exit_code"] != 0
    assert result["partial"] is True
    assert result["failed_step"] == "plugin_add"
    assert Path(result["target"], INSTALL_MANIFEST).exists()


def test_openclaw_refuses_install_that_would_silently_restart_live_gateway(
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(gateway_live=True)
    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "host_restart_consent_required"
    assert result["partial"] is False
    assert not Path(result["target"]).exists()
    assert not any("plugins install" in " ".join(command) for command in runner.commands)


@pytest.mark.parametrize(
    ("version", "supported"),
    [
        ("OpenClaw 2026.7.1", True),
        ("openclaw v2026.7.2+build.9", True),
        ("OpenClaw 2026.7.999", True),
        ("OpenClaw 2026.8.0", False),
        ("2027.1.0", False),
        ("OpenClaw 2026.7.1-rc.1", False),
        ("OpenClaw 2026.7.1rc1", False),
        ("OpenClaw 2026.7.1.1", False),
        ("OpenClaw 2026.6.9", False),
        ("unknown", False),
    ],
)
def test_openclaw_minimum_hook_version_contract(version: str, supported: bool) -> None:
    assert openclaw_version_supported(version) is supported


@pytest.mark.parametrize(
    "version",
    [
        "OpenClaw 2026.6.9",
        "OpenClaw 2026.7.1-rc.1",
        "OpenClaw 2026.8.0",
        "OpenClaw 2027.1.0",
        "unknown",
    ],
)
def test_openclaw_unsupported_version_blocks_before_mutation(
    version: str,
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(openclaw_version=version)

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "host_capability_unproven"
    assert result["partial"] is False
    assert not Path(result["target"]).exists()
    assert runner.commands == [["openclaw", "--version"]]


@pytest.mark.parametrize(
    "gateway_result",
    [
        {"returncode": 7, "stderr": "gateway probe failed"},
        {"returncode": 0, "stdout": "not-json"},
        {"returncode": 0, "stdout": json.dumps({"unexpected": "shape"})},
        {"returncode": 0, "stdout": json.dumps({"healthy": False})},
    ],
)
def test_openclaw_unknown_gateway_status_fails_closed_without_mutation(
    gateway_result: dict[str, Any],
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(gateway_result=gateway_result)

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "gateway_status_unproven"
    gateway_step = next(step for step in result["native_steps"] if step["name"] == "gateway_status")
    assert gateway_step["gateway_state"] == "unknown"
    assert result["partial"] is False
    assert not Path(result["target"]).exists()
    assert not any("plugins install" in " ".join(command) for command in runner.commands)


def test_openclaw_streaming_policy_failure_stops_before_plugin_mutation(
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(fail_token="config get agents.defaults")

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "final_only_delivery_policy"
    assert result["streaming_policy"]["ok"] is False
    assert result["streaming_policy"]["rollback_attempted"] is False
    assert "restoration" not in result["streaming_policy"]
    assert not any("plugins install" in " ".join(command) for command in runner.commands)


def test_openclaw_runtime_metadata_without_loaded_fact_stays_unverified(
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(
        runtime_payload={
            "id": "agency-preflight",
            "enabled": True,
            "hooks": ["before_prompt_build"],
        }
    )

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "runtime_inspect_unproven"
    assert result["registered"] is True
    assert result["enabled"] is False
    assert result["loaded"] is False
    assert result["canary"] is None
    assert result["maturity"] == "registered-disabled"

    record = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver("openclaw"),
            command_runner=runner,
            probe_runtime=True,
        )
    }["openclaw"]
    assert record["registered"] is True
    assert record["enabled"] is False
    assert record["loaded"] is None
    assert record["canary"] is None
    assert record["maturity"] == "registered-disabled"


def test_openclaw_runtime_contract_accepts_official_typed_hook_report(tmp_path: Path) -> None:
    runner = FakeNativeRunner(
        runtime_payload={
            "plugin": {"id": "agency-preflight", "status": "loaded"},
            "typedHooks": [{"name": name} for name in sorted(OPENCLAW_REQUIRED_HOOKS)],
        }
    )

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is True
    runtime_step = next(
        step for step in result["native_steps"] if step["name"] == "runtime_inspect"
    )
    assert runtime_step["loaded"] is True
    assert runtime_step["missing_required_hooks"] == []
    assert runtime_step["registration_contract_proven"] is True
    assert runtime_step["delivery_behavior_proven"] is False
    assert runtime_step["runtime_contract_scope"] == "registration_only"
    assert runtime_step["terminal_hook_priority_status"] == {
        "message_sending": "unavailable",
        "reply_payload_sending": "unavailable",
    }


def test_openclaw_runtime_contract_fails_closed_when_one_hook_is_missing(
    tmp_path: Path,
) -> None:
    hooks = sorted(OPENCLAW_REQUIRED_HOOKS - {"message_sending"})
    runner = FakeNativeRunner(
        runtime_payload={
            "plugin": {"id": "agency-preflight", "status": "loaded"},
            "typedHooks": [{"name": name} for name in hooks],
        }
    )

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "runtime_inspect_unproven"
    runtime_step = next(
        step for step in result["native_steps"] if step["name"] == "runtime_inspect"
    )
    assert runtime_step["missing_required_hooks"] == ["message_sending"]
    assert "agency-preflight" in runner.openclaw_disabled


def test_openclaw_runtime_contract_rejects_explicit_nonterminal_priority(
    tmp_path: Path,
) -> None:
    typed_hooks = [{"name": name} for name in sorted(OPENCLAW_REQUIRED_HOOKS)]
    for hook in typed_hooks:
        if hook["name"] == "message_sending":
            hook["priority"] = -1000
    runner = FakeNativeRunner(
        runtime_payload={
            "plugin": {"id": "agency-preflight", "status": "loaded"},
            "typedHooks": typed_hooks,
        }
    )

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["failed_step"] == "runtime_inspect_unproven"
    runtime_step = next(
        step for step in result["native_steps"] if step["name"] == "runtime_inspect"
    )
    assert runtime_step["registration_contract_proven"] is True
    assert runtime_step["terminal_hook_priority_mismatches"] == ["message_sending"]
    assert runtime_step["terminal_hook_priority_status"]["message_sending"] == "mismatch"
    assert "agency-preflight" in runner.openclaw_disabled


@pytest.mark.parametrize(
    ("priority", "expected_status", "expected_value", "expected_ok"),
    [
        ("-Infinity", "mismatch", "-Infinity", False),
        ({"value": "lowest"}, "mismatch", "dict", False),
    ],
)
def test_openclaw_runtime_priority_metadata_is_not_guessed(
    priority: object,
    expected_status: str,
    expected_value: object,
    expected_ok: bool,
    tmp_path: Path,
) -> None:
    typed_hooks = [{"name": name} for name in sorted(OPENCLAW_REQUIRED_HOOKS)]
    for hook in typed_hooks:
        if hook["name"] == "message_sending":
            hook["priority"] = priority
    runner = FakeNativeRunner(
        runtime_payload={
            "plugin": {"id": "agency-preflight", "status": "loaded"},
            "typedHooks": typed_hooks,
        }
    )

    result = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is expected_ok
    runtime_step = next(
        step for step in result["native_steps"] if step["name"] == "runtime_inspect"
    )
    assert runtime_step["terminal_hook_priority_status"]["message_sending"] == expected_status
    assert runtime_step["terminal_hook_priorities"]["message_sending"] == expected_value


def test_reinstall_keeps_timestamped_backup_and_rollback_restores_it(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    first = install_agent_adapter("hermes", home_dir=tmp_path)
    plugin = Path(first["plugin_path"])
    plugin.write_text("# prior managed version\n", encoding="utf-8")

    second = install_agent_adapter("hermes", home_dir=tmp_path)
    backup = Path(second["backup_path"])
    assert backup.exists()
    assert "prior managed version" not in plugin.read_text(encoding="utf-8")

    rolled_back = rollback_agent_adapter("hermes", home_dir=tmp_path, backup_path=backup)
    assert rolled_back["ok"] is True
    assert "prior managed version" in plugin.read_text(encoding="utf-8")


def test_rollback_rejects_arbitrary_user_folder_without_moving_either_tree(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    installed = install_agent_adapter("hermes", home_dir=tmp_path)
    target = Path(installed["target"])
    target_marker = target / "target-marker.txt"
    target_marker.write_text("keep target", encoding="utf-8")
    arbitrary = tmp_path / "unrelated-user-folder"
    arbitrary.mkdir()
    arbitrary_marker = arbitrary / "user-data.txt"
    arbitrary_marker.write_text("keep user data", encoding="utf-8")

    result = rollback_agent_adapter("hermes", home_dir=tmp_path, backup_path=arbitrary)

    assert result["ok"] is False
    assert "managed backup root" in result["error"]
    assert target_marker.read_text(encoding="utf-8") == "keep target"
    assert arbitrary_marker.read_text(encoding="utf-8") == "keep user data"


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("host", "codex"),
        ("plugin_version", "different-version"),
        ("target", "unrelated-target"),
    ],
)
def test_rollback_rejects_managed_root_backup_with_mismatched_ownership_manifest(
    field: str,
    invalid_value: str,
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    first = install_agent_adapter("hermes", home_dir=tmp_path)
    Path(first["target"], "force-refresh.txt").write_text("changed\n", encoding="utf-8")
    second = install_agent_adapter("hermes", home_dir=tmp_path)
    backup = Path(second["backup_path"])
    manifest_path = backup / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = invalid_value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    target_marker = Path(second["target"]) / "current-target.txt"
    target_marker.write_text("current", encoding="utf-8")

    result = rollback_agent_adapter("hermes", home_dir=tmp_path, backup_path=backup)

    assert result["ok"] is False
    assert backup.exists()
    assert target_marker.read_text(encoding="utf-8") == "current"


def test_rollback_rejects_oversized_ownership_manifest_without_moving_state(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    first = install_agent_adapter("hermes", home_dir=tmp_path)
    Path(first["target"], "force-refresh.txt").write_text(
        "changed\n",
        encoding="utf-8",
    )
    second = install_agent_adapter("hermes", home_dir=tmp_path)
    backup = Path(second["backup_path"])
    (backup / INSTALL_MANIFEST).write_bytes(b"{" + b" " * (64 * 1024))
    target_marker = Path(second["target"]) / "current-target.txt"
    target_marker.write_text("current", encoding="utf-8")

    result = rollback_agent_adapter("hermes", home_dir=tmp_path, backup_path=backup)

    assert result["ok"] is False
    assert "unreadable or invalid" in result["error"]
    assert backup.exists()
    assert target_marker.read_text(encoding="utf-8") == "current"


def test_rollback_accepts_and_reports_a_well_formed_prior_plugin_version(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    first = install_agent_adapter("hermes", home_dir=tmp_path)
    Path(first["target"], "force-refresh.txt").write_text("changed\n", encoding="utf-8")
    second = install_agent_adapter("hermes", home_dir=tmp_path)
    backup = Path(second["backup_path"])
    manifest_path = backup / INSTALL_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["plugin_version"] = "0.0.9"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = rollback_agent_adapter("hermes", home_dir=tmp_path, backup_path=backup)

    assert result["ok"] is True
    assert result["restored_version"] == "0.0.9"


def test_rollback_refreshes_codex_native_cache_when_runner_is_available(
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner()
    first = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )
    manifest = Path(first["plugin_path"])
    manifest.write_text('{"name":"agency-preflight","version":"prior"}\n', encoding="utf-8")
    second = install_agent_adapter(
        "codex",
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    result = rollback_agent_adapter(
        "codex",
        home_dir=tmp_path,
        backup_path=second["backup_path"],
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    assert result["ok"] is True
    assert result["native_refreshed"] is True
    step_names = [step["name"] for step in result["native_steps"]]
    assert "plugin_remove_for_refresh" in step_names
    assert "plugin_add" in step_names
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == "prior"


@pytest.mark.parametrize(
    ("gateway_result", "failed_step"),
    [
        (
            {"returncode": 0, "stdout": json.dumps({"running": True})},
            "host_restart_consent_required",
        ),
        ({"returncode": 9, "stderr": "status unavailable"}, "gateway_status_unproven"),
    ],
)
def test_openclaw_rollback_fails_closed_before_moving_files(
    gateway_result: dict[str, Any],
    failed_step: str,
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner(gateway_live=False)
    first = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )
    Path(first["target"], "force-refresh.txt").write_text("changed\n", encoding="utf-8")
    current = install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )
    target = Path(current["target"])
    backup = Path(current["backup_path"])
    target_marker = target / "current.txt"
    backup_marker = backup / "retained.txt"
    target_marker.write_text("current", encoding="utf-8")
    backup_marker.write_text("retained", encoding="utf-8")
    runner.gateway_result = gateway_result
    command_count = len(runner.commands)

    result = rollback_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        backup_path=backup,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["partial"] is False
    assert result["failed_step"] == failed_step
    assert target_marker.read_text(encoding="utf-8") == "current"
    assert backup_marker.read_text(encoding="utf-8") == "retained"
    assert len(runner.commands) == command_count + 1
    assert "gateway status" in " ".join(runner.commands[-1])


def test_install_cli_rejects_rollback_dry_run_and_unscoped_backup() -> None:
    from agency_runtime.cli.main import cmd_install

    base = {
        "agent": "hermes",
        "all": False,
        "profile": None,
        "json": False,
    }
    with pytest.raises(ValueError, match="mutually exclusive"):
        cmd_install(Namespace(**base, rollback=True, dry_run=True, backup=None))
    with pytest.raises(ValueError, match="requires --rollback"):
        cmd_install(Namespace(**base, rollback=False, dry_run=False, backup="retained"))


def test_install_all_marker_only_host_reports_incomplete_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.installer as installer
    from agency_runtime.cli import main as cli

    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())
    monkeypatch.setattr(cli, "_store", lambda _cfg: object())
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: ["hermes"])
    monkeypatch.setattr(
        installer,
        "install_agent_adapter",
        lambda _host, _cfg: {
            "ok": True,
            "exit_code": 0,
            "host": "hermes",
            "status": "staged_unverified",
            "maturity": "staged-not-registered",
            "registered": False,
            "plugin_path": "managed/hermes",
        },
    )

    exit_code = cli.cmd_install(
        Namespace(
            agent=None,
            all=True,
            profile=None,
            json=True,
            rollback=False,
            dry_run=False,
            backup=None,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["complete"] is False
    assert report["hosts"][0]["complete"] is False


def test_install_defaults_to_user_dashboard_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer
    from agency_runtime.cli import main as cli

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())
    monkeypatch.setattr(cli, "_store", lambda _cfg: object())
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(
        dashboard_service,
        "install_dashboard_service",
        lambda **kwargs: (
            calls.append(kwargs)
            or {
                "ok": True,
                "exit_code": 0,
                "status": "installed",
            }
        ),
    )

    exit_code = cli.cmd_install(
        Namespace(
            agent=None,
            all=False,
            profile=None,
            json=True,
            rollback=False,
            dry_run=False,
            backup=None,
            no_dashboard=False,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["dashboard"]["status"] == "installed"
    assert len(calls) == 1
    assert callable(calls[0]["reachability_probe"])
    assert callable(calls[0]["readiness_probe"])


def test_install_blocks_environment_only_dashboard_settings_before_local_mutation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer
    from agency_runtime.cli import main as cli

    secret = "never-render-this-secret"
    monkeypatch.setenv("AGENCY_DB_PATH", "process-only.db")
    monkeypatch.setenv("AGENCY_JUDGE_API_KEY", secret)
    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())

    def unexpected(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("install must fail before local mutation")

    monkeypatch.setattr(cli, "_store", unexpected)
    monkeypatch.setattr(installer, "seed_starter_roster", unexpected)
    monkeypatch.setattr(installer, "install_agent_adapter", unexpected)
    monkeypatch.setattr(
        dashboard_service,
        "plan_dashboard_service",
        lambda **_kwargs: {
            "ok": False,
            "exit_code": 1,
            "changed": False,
            "error": "non-durable: AGENCY_DB_PATH, AGENCY_JUDGE_API_KEY",
            "non_durable_environment_overrides": [
                "AGENCY_DB_PATH",
                "AGENCY_JUDGE_API_KEY",
            ],
        },
    )

    exit_code = cli.cmd_install(
        Namespace(
            agent="codex",
            all=False,
            profile=None,
            json=True,
            rollback=False,
            dry_run=False,
            backup=None,
            no_dashboard=False,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["roster_added"] == 0
    assert report["hosts"] == []
    assert report["dashboard"]["non_durable_environment_overrides"] == [
        "AGENCY_DB_PATH",
        "AGENCY_JUDGE_API_KEY",
    ]
    assert secret not in json.dumps(report)


def test_install_no_dashboard_never_queries_or_mutates_service_manager(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer
    from agency_runtime.cli import main as cli

    def unexpected(**_kwargs):
        raise AssertionError("dashboard service manager must not be called")

    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())
    monkeypatch.setattr(cli, "_store", lambda _cfg: object())
    monkeypatch.setattr(installer, "seed_starter_roster", lambda _store: 0)
    monkeypatch.setattr(dashboard_service, "install_dashboard_service", unexpected)
    monkeypatch.setattr(dashboard_service, "plan_dashboard_service", unexpected)

    exit_code = cli.cmd_install(
        Namespace(
            agent=None,
            all=False,
            profile=None,
            json=True,
            rollback=False,
            dry_run=False,
            backup=None,
            no_dashboard=True,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["dashboard"] == {
        "changed": False,
        "exit_code": 0,
        "ok": True,
        "status": "opted_out",
    }


def test_install_all_with_no_detected_hosts_changes_no_local_state(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    import agency_runtime.core.installer as installer
    from agency_runtime.cli import main as cli

    def unexpected(*_args, **_kwargs):
        raise AssertionError("no-host install must not mutate local state")

    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())
    monkeypatch.setattr(installer, "detect_installed_agents", lambda: [])
    monkeypatch.setattr(installer, "seed_starter_roster", unexpected)
    monkeypatch.setattr(dashboard_service, "install_dashboard_service", unexpected)

    exit_code = cli.cmd_install(
        Namespace(
            agent=None,
            all=True,
            profile=None,
            json=True,
            rollback=False,
            dry_run=False,
            backup=None,
            no_dashboard=False,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["roster_added"] == 0
    assert report["hosts"] == []
    assert report["dashboard"] == {
        "changed": False,
        "exit_code": 1,
        "ok": False,
        "reason": "no supported hosts detected",
        "status": "not_attempted",
    }


def test_install_dry_run_includes_dashboard_plan_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import agency_runtime.core.dashboard_service as dashboard_service
    from agency_runtime.cli import main as cli

    planned: list[dict[str, Any]] = []
    monkeypatch.setattr(cli, "load_config", lambda: AgencyConfig())
    monkeypatch.setattr(
        dashboard_service,
        "plan_dashboard_service",
        lambda **kwargs: (
            planned.append(kwargs)
            or {
                "ok": True,
                "exit_code": 0,
                "dry_run": True,
                "manager": "fake",
                "registration_path": "fake-dashboard-service",
            }
        ),
    )
    monkeypatch.setattr(
        dashboard_service,
        "install_dashboard_service",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("dry-run must not install")),
    )

    exit_code = cli.cmd_install(
        Namespace(
            agent=None,
            all=False,
            profile=None,
            json=True,
            rollback=False,
            dry_run=True,
            backup=None,
            no_dashboard=False,
        )
    )
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert report["dashboard"]["dry_run"] is True
    assert len(planned) == 1


@pytest.mark.parametrize(
    ("host", "enabled", "expected"),
    [
        ("hermes", False, "hermes plugins disable agency-preflight"),
        ("openclaw", True, "openclaw plugins enable agency-preflight"),
        (
            "claude",
            False,
            "claude plugin disable agency-preflight@agency-runtime --scope user",
        ),
        ("codex", False, "codex plugin remove agency-preflight@agency-runtime --json"),
    ],
)
def test_toggle_uses_only_native_host_lifecycle(
    host: str,
    enabled: bool,
    expected: str,
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner()
    result = toggle_agency(
        host,
        enabled,
        home_dir=tmp_path,
        binary_resolver=_resolver(host),
        command_runner=runner,
    )

    assert result["ok"] is True
    assert " ".join(runner.commands[0]) == expected
    assert result["postcondition_verified"] is True
    assert result["verification_state"] == "verified"
    assert runner.commands[-1] != runner.commands[0]


@pytest.mark.parametrize("host", ["hermes", "openclaw", "codex", "claude"])
def test_native_toggle_verifies_both_directions(
    host: str,
    tmp_path: Path,
) -> None:
    runner = FakeNativeRunner()

    enabled = toggle_agency(
        host,
        True,
        home_dir=tmp_path,
        binary_resolver=_resolver(host),
        command_runner=runner,
    )
    disabled = toggle_agency(
        host,
        False,
        home_dir=tmp_path,
        binary_resolver=_resolver(host),
        command_runner=runner,
    )

    assert enabled["ok"] is True
    assert enabled["enabled"] is True
    assert disabled["ok"] is True
    assert disabled["enabled"] is False


def test_native_enablement_unknown_is_never_promoted_to_success(
    tmp_path: Path,
) -> None:
    def runner(command: list[str], **_kwargs: Any) -> dict[str, Any]:
        if "plugin list" in " ".join(command):
            return {
                "returncode": 0,
                "stdout": json.dumps([{"pluginId": "agency-preflight"}]),
            }
        return {"returncode": 0, "stdout": "{}"}

    result = toggle_agency(
        "codex",
        True,
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=runner,
    )

    assert result["ok"] is False
    assert result["enabled"] is None
    assert result["postcondition_verified"] is False
    assert result["verification_state"] == "enablement_unverified"
    assert result["partial"] is True


def test_inspection_never_promotes_staged_bundle_to_registered(tmp_path: Path) -> None:
    (tmp_path / ".claude").mkdir()
    staged = install_agent_adapter("claude", home_dir=tmp_path)
    assert staged["ok"] is True

    record = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver(),
        )
    }["claude"]
    assert record["staged"] is True
    assert record["registered"] is False
    assert record["maturity"] == "staged-not-registered"


def test_hermes_staged_files_without_executable_are_not_native_registration(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    staged = install_agent_adapter("hermes", home_dir=tmp_path)
    assert staged["ok"] is True

    record = {
        item["host"]: item
        for item in inspect_host_installations(
            home_dir=tmp_path,
            binary_resolver=_resolver(),
        )
    }["hermes"]
    assert record["staged"] is True
    assert record["registered"] is False
    assert record["enabled"] is None
    assert record["loaded"] is None
    assert record["canary"] is None
    assert record["maturity"] == "staged-not-registered"


def test_split_installer_resolves_facade_dependencies_at_invocation_time(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.installer as installer

    target = tmp_path / "managed-plugin"
    host_root = tmp_path / "host-root"
    config = AgencyConfig()
    calls: list[str] = []

    monkeypatch.setattr(
        installer,
        "_plugin_target",
        lambda *_args, **_kwargs: target,
    )
    monkeypatch.setattr(
        installer,
        "_host_root",
        lambda *_args, **_kwargs: host_root,
    )
    monkeypatch.setattr(
        installer,
        "_resolve_install_config",
        lambda *_args, **_kwargs: config,
    )
    monkeypatch.setattr(
        installer,
        "_bundle_files",
        lambda *_args, **_kwargs: ({"plugin.json": "{}\n"}, "plugin.json"),
    )
    monkeypatch.setattr(installer, "_resolve_binary", lambda *_args: None)
    monkeypatch.setattr(
        installer,
        "_root_state",
        lambda *_args, **_kwargs: (False, False, []),
    )

    def filesystem_plan(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("filesystem")
        return {"changed": True, "dry_run": True}

    monkeypatch.setattr(installer, "_atomic_install_tree", filesystem_plan)

    result = installer.plan_agent_adapter("hermes", home_dir=tmp_path)

    assert calls == ["filesystem"]
    assert result["plugin_path"] == str(target / "plugin.json")
    assert result["native_root"] == str(host_root)
    assert result["filesystem"] == {"changed": True, "dry_run": True}


def test_split_installer_preserves_config_and_argv_monkeypatches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer

    config = AgencyConfig()
    monkeypatch.setattr(installer, "load_config", lambda **_kwargs: config)
    monkeypatch.setattr(
        installer,
        "prepare_process_argv",
        lambda *_args, **_kwargs: ["patched", "argv"],
    )

    assert installer._resolve_install_config(None, home_dir=None) is config
    assert installer._prepare_process_argv(["ignored"]) == ["patched", "argv"]


def test_split_bundle_generation_resolves_facade_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer

    monkeypatch.setattr(installer, "_hook_timeout_seconds", lambda _cfg: 17)
    monkeypatch.setattr(
        installer,
        "_codex_hooks",
        lambda timeout: {"marker": f"hooks-{timeout}"},
    )
    monkeypatch.setattr(installer, "_mcp_config", lambda: {"marker": "mcp"})
    monkeypatch.setattr(
        installer,
        "_agency_control_skill",
        lambda host: f"skill-{host}",
    )
    monkeypatch.setattr(
        installer,
        "_codex_plugin_version",
        lambda _manifest, _files: "9.9.9+patched",
    )

    files, _primary = installer._bundle_files("codex", AgencyConfig())

    prefix = "plugins/agency-preflight"
    assert json.loads(files[f"{prefix}/hooks/hooks.json"]) == {"marker": "hooks-17"}
    assert json.loads(files[f"{prefix}/.mcp.json"]) == {"marker": "mcp"}
    assert files[f"{prefix}/skills/agency/SKILL.md"] == "skill-codex"
    assert json.loads(files[f"{prefix}/.codex-plugin/plugin.json"])["version"] == "9.9.9+patched"


def test_split_detection_resolves_facade_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import agency_runtime.core.installer as installer

    monkeypatch.setattr(
        installer,
        "_is_host_installed",
        lambda host, **_kwargs: host == "codex",
    )

    assert installer.detect_installed_agents() == ["codex"]


def test_split_inspection_uses_monkeypatched_native_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import agency_runtime.core.installer as installer

    calls: list[tuple[str, ...]] = []

    def run_native(command: list[str], **_kwargs: Any) -> NativeCommandResult:
        calls.append(tuple(command))
        if command[1:] == ["--version"]:
            return NativeCommandResult(tuple(command), 0, "codex-cli 1.0")
        return NativeCommandResult(tuple(command), 0, "[]")

    monkeypatch.setattr(installer, "_run_native", run_native)

    installer.inspect_host_installations(
        hosts=["codex"],
        home_dir=tmp_path,
        binary_resolver=_resolver("codex"),
        command_runner=lambda *_args, **_kwargs: None,
    )

    assert calls
    assert calls[0][1:] == ("--version",)
