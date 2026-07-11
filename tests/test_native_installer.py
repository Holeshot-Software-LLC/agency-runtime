"""Native host discovery and transactional installer contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    ProviderEntry,
)
from agency_runtime.core.installer import (
    INSTALL_MANIFEST,
    _bundle_files,
    _effective_judge_budget_seconds,
    _owned_process_kwargs,
    detect_installed_agents,
    inspect_host_installations,
    inspect_host_installation,
    install_agent_adapter,
    plan_agent_adapter,
    rollback_agent_adapter,
    toggle_agency,
    _prepare_process_argv,
    _run_native,
)


@pytest.fixture(autouse=True)
def _no_live_dashboard_service(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _resolver(*present: str):
    selected = set(present)
    return lambda name: (
        str(Path("C:/fake") / f"{name}.exe") if name in selected else None
    )


class FakeNativeRunner:
    def __init__(
        self,
        *,
        fail_token: str | None = None,
        gateway_live: bool = False,
        gateway_result: dict[str, Any] | None = None,
        runtime_payload: Any = None,
    ) -> None:
        self.commands: list[list[str]] = []
        self.fail_token = fail_token
        self.gateway_live = gateway_live
        self.gateway_result = gateway_result
        self.runtime_payload = runtime_payload
        self.installed: set[str] = set()
        self.marketplaces: set[str] = set()

    def __call__(self, command: list[str], **_kwargs: Any) -> dict[str, Any]:
        self.commands.append(command)
        joined = " ".join(command)
        if self.fail_token and self.fail_token in joined:
            return {"returncode": 9, "stderr": f"forced failure: {self.fail_token}"}

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
                "stdout": json.dumps(
                    [{"name": name} for name in sorted(self.marketplaces)]
                ),
            }
        if "marketplace add" in joined:
            self.marketplaces.add("agency-runtime")
            return {"returncode": 0, "stdout": "{}"}
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
            return {
                "returncode": 0,
                "stdout": json.dumps(
                    [{"name": name, "enabled": True} for name in sorted(self.installed)]
                ),
            }
        if "plugins inspect agency-preflight --runtime" in joined:
            payload = self.runtime_payload
            if payload is None:
                payload = {
                    "id": "agency-preflight",
                    "enabled": True,
                    "loaded": True,
                    "hooks": ["before_prompt_build"],
                }
            return {
                "returncode": 0,
                "stdout": json.dumps(payload),
            }
        if "plugins inspect agency-preflight" in joined:
            found = "agency-preflight" in self.installed
            return {
                "returncode": 0 if found else 1,
                "stdout": json.dumps({"id": "agency-preflight", "enabled": True})
                if found
                else "",
            }
        if "plugins install" in joined:
            self.installed.add("agency-preflight")
            return {"returncode": 0, "stdout": "installed"}
        if "plugins enable" in joined:
            self.installed.add("agency-preflight")
            return {"returncode": 0, "stdout": "enabled"}
        if "plugins disable" in joined:
            self.installed.discard("agency-preflight")
            return {"returncode": 0, "stdout": "disabled"}
        if "plugins list" in joined:
            if command[0] == "openclaw":
                return {
                    "returncode": 0,
                    "stdout": json.dumps(
                        {
                            "plugins": [
                                {"id": name, "enabled": True}
                                for name in sorted(self.installed)
                            ]
                        }
                    ),
                }
            text = "\n".join(f"{name} enabled" for name in sorted(self.installed))
            return {"returncode": 0, "stdout": text}
        if "config set" in joined:
            return {"returncode": 0, "stdout": "updated"}
        return {"returncode": 0, "stdout": "{}"}


def test_detection_separates_bare_stale_root_from_current_native_state(
    tmp_path: Path,
) -> None:
    (tmp_path / ".codex").mkdir()

    assert "codex" not in detect_installed_agents(
        home_dir=tmp_path, binary_resolver=_resolver()
    )
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
    assert "codex" in detect_installed_agents(
        home_dir=tmp_path, binary_resolver=_resolver()
    )


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

    assert "hermes" in detect_installed_agents(
        home_dir=tmp_path, binary_resolver=_resolver()
    )
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
    tmp_path: Path,
) -> None:
    shim_dir = tmp_path / "host & tools ^ 100%"
    shim_dir.mkdir()
    cmd_shim = shim_dir / "codex.cmd"
    ps1_shim = shim_dir / "codex.ps1"
    cmd_shim.write_text("@echo off\n", encoding="utf-8")
    ps1_shim.write_text("# safe companion\n", encoding="utf-8")
    special_path = str(tmp_path / "bundle & cache | stage ^ 50% <input>")

    def resolver(_name):
        return str(cmd_shim)

    windows = _prepare_process_argv(
        ["codex", "plugin", "marketplace", "add", special_path],
        platform_name="nt",
        resolver=resolver,
    )
    linux = _prepare_process_argv(
        ["codex", "plugin", "list", "--json"],
        platform_name="posix",
        resolver=lambda _name: "/usr/local/bin/codex",
    )

    assert windows[:7] == [
        "powershell.exe",
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
    tmp_path: Path,
) -> None:
    cmd_shim = tmp_path / "host.cmd"
    cmd_shim.write_text("@echo off\n", encoding="utf-8")

    with pytest.raises(OSError, match="refusing unsafe cmd.exe shim"):
        _prepare_process_argv(
            ["host", "plugin", "list"],
            platform_name="nt",
            resolver=lambda _name: str(cmd_shim),
        )


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
        [sys.executable, "-c", parent_code],
        host="codex",
        home_dir=tmp_path,
        timeout=0.2,
    )

    assert result.returncode == 124
    assert "terminated the owned process tree" in result.stderr
    time.sleep(1.2)
    assert not marker.exists()


def test_generated_hook_timeouts_exceed_the_configured_sequential_judge_budget() -> (
    None
):
    cfg = AgencyConfig(
        judge=JudgeConfig(
            model="legacy-model",
            base_url="http://legacy.invalid",
            timeout=17,
        ),
        ollama=OllamaConfig(enabled=True, model="fallback-model"),
        providers=(
            ProviderEntry(
                model="primary", base_url="http://primary.invalid", timeout=7
            ),
            ProviderEntry(
                model="secondary", base_url="http://secondary.invalid", timeout=11
            ),
        ),
    )
    judge_budget = _effective_judge_budget_seconds(cfg)

    codex_files, _ = _bundle_files("codex", cfg)
    codex_hooks = json.loads(codex_files["plugins/agency-preflight/hooks/hooks.json"])
    hook_timeout = codex_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"]
    assert hook_timeout > judge_budget

    claude_files, _ = _bundle_files("claude", cfg)
    claude_hooks = json.loads(claude_files["plugins/agency-preflight/hooks/hooks.json"])
    assert (
        claude_hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"]
        == hook_timeout
    )

    openclaw_files, _ = _bundle_files("openclaw", cfg)
    bridge = openclaw_files["index.js"]
    assert f"timeout: {hook_timeout * 1000}" in bridge
    assert f"timeoutMs: {(hook_timeout + 2) * 1000}" in bridge


def test_dry_run_is_a_write_free_complete_plan(tmp_path: Path) -> None:
    plan = plan_agent_adapter(
        "codex", home_dir=tmp_path, binary_resolver=_resolver("codex")
    )

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
        Path(plan["plugin_path"]).parent
        == (custom_home / "plugins" / "agency-preflight").resolve()
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
    if host == "openclaw":
        assert any("plugins install" in command for command in commands)
        assert any(
            "plugins inspect agency-preflight --runtime --json" in command
            for command in commands
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
    assert not any(
        "plugins install" in " ".join(command) for command in runner.commands
    )


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
    assert result["native_steps"][0]["gateway_state"] == "unknown"
    assert result["partial"] is False
    assert not Path(result["target"]).exists()
    assert not any(
        "plugins install" in " ".join(command) for command in runner.commands
    )


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
    assert result["enabled"] is True
    assert result["loaded"] is None
    assert result["canary"] is None
    assert result["maturity"] == "enabled-runtime-unverified"

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
    assert record["enabled"] is True
    assert record["loaded"] is None
    assert record["canary"] is None
    assert record["maturity"] == "enabled-runtime-unverified"


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

    rolled_back = rollback_agent_adapter(
        "hermes", home_dir=tmp_path, backup_path=backup
    )
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
    install_agent_adapter("hermes", home_dir=tmp_path)
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


def test_rollback_accepts_and_reports_a_well_formed_prior_plugin_version(
    tmp_path: Path,
) -> None:
    (tmp_path / ".hermes").mkdir()
    install_agent_adapter("hermes", home_dir=tmp_path)
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
    manifest.write_text(
        '{"name":"agency-preflight","version":"prior"}\n', encoding="utf-8"
    )
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
    install_agent_adapter(
        "openclaw",
        home_dir=tmp_path,
        binary_resolver=_resolver("openclaw"),
        command_runner=runner,
    )
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
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must not install")
        ),
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
    assert " ".join(runner.commands[-1]) == expected


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
